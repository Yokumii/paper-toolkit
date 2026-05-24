"""Figure reference and caption checker."""

from __future__ import annotations

import re
from pathlib import Path

from paper_toolkit.checkers.base import issue, read_sections, word_count
from paper_toolkit.models.check_report import CheckReport
from paper_toolkit.models.venue import VenueConfig
from paper_toolkit.state.workspace import read_state

_FIG_REF_RE = re.compile(r"\\ref\{fig:([^}]+)\}")

# Redundant numbering inside \caption{...}: LaTeX already renders "Figure N:";
# leaving "Figure N." inside the caption body yields "Figure 1: Figure 1. ...".
_REDUNDANT_CAPTION_PREFIX_RE = re.compile(
    r"\\caption(?:\[[^\]]*\])?\{\s*(Figure|Table)\s*\d+\s*[\.:]\s",
    flags=re.IGNORECASE,
)

# figure / figure* environment with its options block.
_FIGURE_ENV_RE = re.compile(
    r"\\begin\{(figure\*?)\}(?:\[([^\]]*)\])?(.*?)\\end\{\1\}",
    flags=re.DOTALL,
)
_LABEL_INSIDE_RE = re.compile(r"\\label\{([^}]+)\}")

# Float placement specifiers that pdflatex tends to ignore or that make floats
# crash into surrounding text. EasyPaper rewrites these to [tbp]/[htbp].
_BAD_FLOAT_PLACEMENT_RE = re.compile(r"^(?:h!?|t|b|h)$")


def check_figures(*, workspace: Path, venue: VenueConfig) -> CheckReport:
    state = read_state(workspace=workspace)
    sections = read_sections(workspace=workspace)
    referenced = {
        match.group(1) for text in sections.values() for match in _FIG_REF_RE.finditer(text)
    }
    known = {figure.id for figure in state.artifacts.figures}
    issues = []
    min_caption, max_caption = venue.figure_constraints.caption_words

    if len(state.artifacts.figures) > venue.figure_constraints.max_figures:
        issues.append(
            issue(
                severity="warning",
                code="FIGURE_TOO_MANY",
                message=(
                    f"{len(state.artifacts.figures)} figures exceeds "
                    f"venue max {venue.figure_constraints.max_figures}"
                ),
                location="paper/paper.json",
            )
        )

    for figure in state.artifacts.figures:
        if not (workspace / figure.packed).exists():
            issues.append(
                issue(
                    severity="error",
                    code="FIGURE_MISSING_FILE",
                    message=f"packed figure file does not exist: {figure.packed}",
                    location=figure.packed,
                    fixup_hint="Run paper compose pack-figures or fix paper.json figure metadata.",
                )
            )
        if figure.id not in referenced:
            issues.append(
                issue(
                    severity="error",
                    code="FIGURE_UNREFERENCED",
                    message=f"figure {figure.id!r} is packed but not referenced by any section",
                    location=figure.packed,
                    fixup_hint=f"Add a \\ref{{fig:{figure.id}}} reference or remove the figure.",
                )
            )
        caption_words = word_count(figure.caption or "")
        if caption_words < min_caption or caption_words > max_caption:
            issues.append(
                issue(
                    severity="warning",
                    code="FIGURE_CAPTION_LENGTH",
                    message=(
                        f"figure {figure.id!r} caption has {caption_words} words; "
                        f"expected {min_caption}-{max_caption}"
                    ),
                    location=figure.packed,
                )
            )

    for ref in sorted(referenced - known):
        issues.append(
            issue(
                severity="error",
                code="FIGURE_UNRESOLVED_REF",
                message=f"section references unknown figure {ref!r}",
                location="paper/sections",
                fixup_hint="Pack the referenced figure or fix the label.",
            )
        )

    # Per-section LaTeX heuristics: redundant caption prefix, bad float
    # placement, and duplicate figure labels across sections.
    label_to_sections: dict[str, list[str]] = {}
    for section_name, text in sections.items():
        location = f"paper/sections/{section_name}.tex"

        if _REDUNDANT_CAPTION_PREFIX_RE.search(text):
            issues.append(
                issue(
                    severity="warning",
                    code="FIGURE_REDUNDANT_CAPTION_PREFIX",
                    message=(
                        f"section {section_name!r} has a \\caption that starts with "
                        "'Figure N.' or 'Table N.'; LaTeX adds this automatically."
                    ),
                    location=location,
                    fixup_hint=(
                        "Drop the leading 'Figure N.' / 'Table N.' from inside \\caption{...}."
                    ),
                )
            )

        for match in _FIGURE_ENV_RE.finditer(text):
            placement = match.group(2)
            if placement is not None and _BAD_FLOAT_PLACEMENT_RE.fullmatch(placement.strip()):
                issues.append(
                    issue(
                        severity="warning",
                        code="FIGURE_BAD_FLOAT_PLACEMENT",
                        message=(
                            f"section {section_name!r} uses [{placement}] which pdflatex "
                            "often demotes; prefer [tbp] or [htbp]."
                        ),
                        location=location,
                        fixup_hint="Replace [h!]/[t]/[b]/[h] with [tbp] or [htbp].",
                    )
                )
            inner_labels = _LABEL_INSIDE_RE.findall(match.group(3))
            if inner_labels:
                # Take the first label as the canonical id for the env.
                label_to_sections.setdefault(inner_labels[0], []).append(section_name)

    for label, owners in sorted(label_to_sections.items()):
        if len(owners) > 1:
            issues.append(
                issue(
                    severity="warning",
                    code="FIGURE_DUPLICATE_ENV",
                    message=(
                        f"figure environment with \\label{{{label}}} appears in multiple "
                        f"sections: {', '.join(owners)}"
                    ),
                    location=f"paper/sections/{owners[0]}.tex",
                    fixup_hint=(
                        "Keep one figure environment per label and delete the duplicates "
                        "in the other sections."
                    ),
                )
            )

    return CheckReport(
        checker="figures",
        issues=issues,
        result={"known_figures": sorted(known), "referenced_figures": sorted(referenced)},
    )
