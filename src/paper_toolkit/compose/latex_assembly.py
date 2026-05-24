"""Assemble paper/main.tex using the bundled Springer Nature class."""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.paths import WorkspacePaths

_SECTION_ORDER = ["abstract", "intro", "introduction", "results", "discussion", "methods"]
# Sections rendered into the preamble (\abstract{...}) instead of \input'd.
_PREAMBLE_SECTIONS = frozenset({"abstract"})
# Files copied alongside main.tex so pdflatex/bibtex can resolve them.
_TEMPLATE_ASSETS: tuple[str, ...] = ("sn-jnl.cls", "sn-nature.bst")

_ABSTRACT_ENV_RE = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.DOTALL)


def latex_escape(value: str) -> str:
    """Escape a plain string so it can appear inside a LaTeX command argument.

    Public helper — other render paths (figure captions, table cells) reuse it
    so we have one source of truth for which characters need replacing.
    """
    return (
        value.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("~", "\\textasciitilde{}")
        .replace("^", "\\textasciicircum{}")
    )


# Backwards-compat alias for the original module-private name.
_latex_escape = latex_escape


def discover_sections(*, workspace: Path) -> list[str]:
    paths = WorkspacePaths(workspace=workspace)
    if not paths.sections_dir.exists():
        return []
    names = [path.stem for path in paths.sections_dir.glob("*.tex") if path.is_file()]
    order = {name: idx for idx, name in enumerate(_SECTION_ORDER)}
    return sorted(names, key=lambda name: (order.get(name, len(order)), name))


def _read_abstract_body(workspace: Path) -> str | None:
    paths = WorkspacePaths(workspace=workspace)
    abstract_path = paths.sections_dir / "abstract.tex"
    if not abstract_path.exists():
        return None
    text = abstract_path.read_text(encoding="utf-8", errors="replace")
    m = _ABSTRACT_ENV_RE.search(text)
    body = (m.group(1) if m else text).strip()
    return body or None


def render_main_tex(
    *,
    title: str,
    sections: list[str],
    include_bib: bool,
    abstract_body: str | None = None,
) -> str:
    lines: list[str] = [
        "\\documentclass[pdflatex,sn-nature]{sn-jnl}",
        "\\usepackage{graphicx}",
        "\\usepackage{multirow}",
        "\\usepackage{amsmath,amssymb,amsfonts}",
        "\\usepackage{amsthm}",
        "\\usepackage{mathrsfs}",
        "\\usepackage[title]{appendix}",
        "\\usepackage{xcolor}",
        "\\usepackage{textcomp}",
        "\\usepackage{manyfoot}",
        "\\usepackage{booktabs}",
        "\\usepackage{algorithm}",
        "\\usepackage{algorithmicx}",
        "\\usepackage{algpseudocode}",
        "\\usepackage{listings}",
        "\\raggedbottom",
        "\\begin{document}",
        f"\\title{{{_latex_escape(title)}}}",
        "\\author*[1]{\\fnm{Author} \\sur{Name}}\\email{author@example.org}",
        "\\affil*[1]{\\orgname{Organization}, \\orgaddress{\\country{Country}}}",
    ]
    if abstract_body:
        lines.append(f"\\abstract{{{abstract_body}}}")
    lines.append("\\maketitle")
    for section in sections:
        if section in _PREAMBLE_SECTIONS:
            continue
        lines.append(f"\\input{{sections/{section}.tex}}")
    if include_bib:
        lines.append("\\bibliography{refs}")
    lines.append("\\end{document}")
    lines.append("")
    return "\n".join(lines)


def copy_template_assets(*, workspace: Path) -> list[Path]:
    """Copy bundled sn-jnl.cls + sn-nature.bst into <workspace>/paper/.

    Idempotent: the bundled bytes are written every call, so re-running
    `paper compose assemble-latex` keeps the workspace assets in sync with
    the installed package version.
    """
    paths = WorkspacePaths(workspace=workspace)
    paths.paper_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for asset_name in _TEMPLATE_ASSETS:
        src = files("paper_toolkit.templates").joinpath("nature", "assets", asset_name)
        dst = paths.paper_dir / asset_name
        dst.write_bytes(src.read_bytes())
        written.append(dst.resolve())
    return written


def write_main_tex(*, workspace: Path, title: str) -> Path:
    paths = WorkspacePaths(workspace=workspace)
    sections = discover_sections(workspace=workspace)
    include_bib = paths.refs_bib.exists()
    abstract_body = _read_abstract_body(workspace=workspace)
    rendered = render_main_tex(
        title=title,
        sections=sections,
        include_bib=include_bib,
        abstract_body=abstract_body,
    )
    paths.main_tex.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(paths.main_tex, rendered)
    copy_template_assets(workspace=workspace)
    return paths.main_tex
