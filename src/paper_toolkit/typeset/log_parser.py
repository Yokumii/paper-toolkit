"""Parse TeX logs into structured compile issues.

pdflatex wraps long messages at column 79 by default. The compiler invocation
sets `max_print_line=200` to suppress wrapping, but as defence-in-depth this
parser also un-wraps lines before matching.

File attribution: pdflatex marks file opens as `(/path/to/file.ext` and closes
with `)`. We track a paren stack of every opened path (any extension) so the
balance stays right when sty/cls files open and close mid-log, then resolve the
"current section file" as the nearest `.tex` entry on the stack at error time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from paper_toolkit.models.compile_run import LatexError, LatexIssueCode, LatexWarning

_WARNING_PREFIX = r"(?:LaTeX|Package \S+) Warning:"
_CITATION_RE = re.compile(rf"{_WARNING_PREFIX} Citation `([^']+)'(?:.*?input line (\d+))?")
_REF_RE = re.compile(rf"{_WARNING_PREFIX} Reference `([^']+)'(?:.*?input line (\d+))?")
_UNDEFINED_CITATIONS_SUMMARY_RE = re.compile(
    rf"{_WARNING_PREFIX} There were undefined citations\.?"
)
_OVERFULL_RE = re.compile(r"Overfull \\hbox .*? at lines? (\d+)")
_UNDERFULL_RE = re.compile(r"Underfull \\vbox .*? at lines? (\d+)")
_MISSING_FILE_RE = re.compile(r"! LaTeX Error: File `([^']+)' not found")
_MISSING_BBL_RE = re.compile(r"No file (\S+\.bbl)\.")
_PACKAGE_ERR_RE = re.compile(r"! Package (\S+) Error:")
_LATEX_ERR_RE = re.compile(r"! LaTeX Error:")
_GENERIC_ERR_RE = re.compile(r"^! (.+)$")

# Matches either `(<path>` (file open, capture path) or `)` (close). Processed
# in left-to-right order so interleaved opens/closes on the same line stay
# balanced.
_PAREN_EVENT_RE = re.compile(r"\(((?:/|\./|\.\.\/)[^()\s]+)|(\))")

_NEW_LINE_MARKERS: tuple[str, ...] = (
    "!",
    "(",
    "[",
    "<",
    "Overfull",
    "Underfull",
    "LaTeX Warning",
    "LaTeX Error",
    "Package",
    "Runaway",
    "l.",
)

# Specific (substring/regex, code, hint) triples for common TeX failure modes.
# Ported from EasyPaper conflict_resolver.LATEX_ERROR_FIXES and reframed as
# actionable hints. Checked before the generic-keyword fallback.
_FIXUP_HINTS: list[tuple[re.Pattern[str], LatexIssueCode, str]] = [
    (
        re.compile(r"misplaced alignment tab character &", re.I),
        "syntax",
        "Escape literal '&' as '\\&' in text; bare '&' only inside tabular/align.",
    ),
    (
        re.compile(r"unicode character", re.I),
        "syntax",
        "Replace Unicode characters with LaTeX equivalents "
        "(e.g., \\textendash for \\u2013, $-$ for \\u2212, "
        "\\% for %, \\& for &).",
    ),
    (
        re.compile(r"missing \$ inserted", re.I),
        "syntax",
        "Wrap math symbols (_, ^, \\alpha, \\beta) in $...$ outside math environments.",
    ),
    (
        re.compile(r"undefined control sequence", re.I),
        "syntax",
        "Undefined LaTeX command; check for typos or load the providing package.",
    ),
    (
        re.compile(r"not in outer par mode", re.I),
        "other",
        "Float environments (figure/table) cannot appear inside minipage, parbox, or other floats.",
    ),
    (
        re.compile(r"ended by", re.I),
        "syntax",
        "Unclosed environment; ensure every \\begin{...} has a matching \\end{...}.",
    ),
    (
        re.compile(r"file .+ not found", re.I),
        "missing-file",
        "Remove or comment out the \\includegraphics/\\input for the missing file.",
    ),
    (
        re.compile(r"no output pdf file produced", re.I),
        "other",
        "Critical errors prevented PDF generation;"
        " check unclosed envs, invalid commands, encoding.",
    ),
    (
        re.compile(r"runaway argument", re.I),
        "syntax",
        "Runaway argument; a brace, environment,"
        " or math delimiter is unclosed earlier in the file.",
    ),
]


@dataclass(frozen=True)
class ParsedLatexLog:
    errors: list[LatexError] = field(default_factory=list)
    warnings: list[LatexWarning] = field(default_factory=list)


def _unwrap_lines(text: str) -> list[str]:
    """Collapse pdflatex hard-wrapped lines.

    Join a line with the next when the current line is long (≥ 78 chars), does
    not end with terminal punctuation, and the next line does not start a new
    known marker (`!`, `(`, `Overfull`, etc.). This recovers complete
    messages even when `max_print_line` is not honoured by the engine.
    """
    raw = text.splitlines()
    if not raw:
        return []
    out: list[str] = []
    for line in raw:
        if (
            out
            and len(out[-1]) >= 78
            and not out[-1].rstrip().endswith((".", ":", "?", "!"))
            and line
            and not line.startswith(_NEW_LINE_MARKERS)
        ):
            out[-1] = out[-1].rstrip() + " " + line.lstrip()
        else:
            out.append(line)
    return out


def _update_paren_stack(line: str, stack: list[str]) -> None:
    """Update the paren stack in left-to-right order across `line`."""
    for match in _PAREN_EVENT_RE.finditer(line):
        if match.group(1):  # file open
            stack.append(match.group(1))
        else:  # `)` close
            if stack:
                stack.pop()


def _current_tex_file(stack: list[str]) -> str | None:
    """Return the nearest open .tex file on the stack, if any."""
    for path in reversed(stack):
        if path.endswith(".tex"):
            return path
    return None


def _classify_generic(msg: str) -> tuple[LatexIssueCode, str]:
    """Classify a generic `! ...` error line into (code, fixup_hint).

    Order: specific fixup table first, then keyword-based fallback, then `other`.
    """
    for pattern, code, hint in _FIXUP_HINTS:
        if pattern.search(msg):
            return code, hint
    lower = msg.lower()
    if any(k in lower for k in ("missing", "extra")):
        return "syntax", "Inspect the surrounding TeX source line for an unclosed or stray token."
    return "other", "Inspect the surrounding TeX source for the cause."


def parse_latex_log(log_text: str) -> ParsedLatexLog:
    errors: list[LatexError] = []
    warnings: list[LatexWarning] = []
    paren_stack: list[str] = []
    for line in _unwrap_lines(log_text):
        # Update file context BEFORE inspecting this line's content so the
        # current_file we attach reflects what pdflatex is parsing here.
        _update_paren_stack(line, paren_stack)
        current_file = _current_tex_file(paren_stack)

        stripped = line.strip()
        if not stripped:
            continue

        if m := _CITATION_RE.search(stripped):
            errors.append(
                LatexError(
                    code="missing-citation",
                    message=stripped,
                    file=current_file,
                    line=int(m.group(2)) if m.group(2) else None,
                    fixup_hint="Add the BibTeX entry or fix the citation key.",
                )
            )
            continue
        if _UNDEFINED_CITATIONS_SUMMARY_RE.search(stripped):
            # Aggregate summary emitted at end of run; per-citation entries above
            # already cover each missing key, so skip to avoid duplicate errors.
            continue
        if m := _REF_RE.search(stripped):
            errors.append(
                LatexError(
                    code="undefined-ref",
                    message=stripped,
                    file=current_file,
                    line=int(m.group(2)) if m.group(2) else None,
                    fixup_hint="Add the referenced label or fix the reference key.",
                )
            )
            continue
        if m := _MISSING_BBL_RE.search(stripped):
            errors.append(
                LatexError(
                    code="missing-file",
                    message=stripped,
                    file=current_file,
                    fixup_hint=(
                        "bibtex did not produce the .bbl file. Ensure refs.bib exists, "
                        "has the cited keys, and that bibtex ran successfully (check .blg)."
                    ),
                )
            )
            continue
        if _MISSING_FILE_RE.search(stripped):
            errors.append(
                LatexError(
                    code="missing-file",
                    message=stripped,
                    file=current_file,
                    fixup_hint="Install the missing package or remove the package dependency.",
                )
            )
            continue
        if m := _PACKAGE_ERR_RE.search(stripped):
            errors.append(
                LatexError(
                    code="package",
                    message=stripped,
                    file=current_file,
                    fixup_hint=(
                        f"Check the {m.group(1)} package usage; ensure required args are present."
                    ),
                )
            )
            continue
        if m := _OVERFULL_RE.search(stripped):
            warnings.append(
                LatexWarning(
                    code="overfull-hbox",
                    message=stripped,
                    file=current_file,
                    line=int(m.group(1)),
                )
            )
            continue
        if m := _UNDERFULL_RE.search(stripped):
            warnings.append(
                LatexWarning(
                    code="underfull-vbox",
                    message=stripped,
                    file=current_file,
                    line=int(m.group(1)),
                )
            )
            continue
        # `! LaTeX Error:` subtype not caught by missing-file above — use the
        # fixup table to give an actionable hint when possible.
        if _LATEX_ERR_RE.search(stripped):
            code, hint = _classify_generic(stripped)
            errors.append(
                LatexError(
                    code=code,
                    message=stripped,
                    file=current_file,
                    fixup_hint=hint,
                )
            )
            continue
        if m := _GENERIC_ERR_RE.match(stripped):
            code, hint = _classify_generic(m.group(1))
            errors.append(
                LatexError(
                    code=code,
                    message=stripped,
                    file=current_file,
                    fixup_hint=hint,
                )
            )
    return ParsedLatexLog(errors=errors, warnings=warnings)
