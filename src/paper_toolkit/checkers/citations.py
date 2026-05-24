"""Citation consistency checker."""

from __future__ import annotations

import re
from pathlib import Path

from paper_toolkit.checkers.base import issue, read_sections
from paper_toolkit.models.check_report import CheckReport
from paper_toolkit.paths import WorkspacePaths

_CITE_RE = re.compile(r"\\(?:cite|citep|citet|citealt|citealp|citeauthor|citeyear)\*?\{([^}]+)\}")
_BIB_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)")


def _section_cite_keys(sections: dict[str, str]) -> set[str]:
    keys: set[str] = set()
    for text in sections.values():
        for match in _CITE_RE.finditer(text):
            keys.update(key.strip() for key in match.group(1).split(",") if key.strip())
    return keys


def _bib_keys(text: str) -> set[str]:
    return set(_BIB_RE.findall(text))


def check_citations(*, workspace: Path) -> CheckReport:
    paths = WorkspacePaths(workspace=workspace)
    sections = read_sections(workspace=workspace)
    cited = _section_cite_keys(sections)
    bib_text = paths.refs_bib.read_text(encoding="utf-8") if paths.refs_bib.exists() else ""
    bib = _bib_keys(bib_text)
    issues = []
    for key in sorted(cited - bib):
        issues.append(
            issue(
                severity="error",
                code="CITE_MISSING_BIB_ENTRY",
                message=f"citation key {key!r} is used in sections but missing from refs.bib",
                location="paper/refs.bib",
                fixup_hint="Add the BibTeX entry or fix the citation key.",
            )
        )
    for key in sorted(bib - cited):
        issues.append(
            issue(
                severity="warning",
                code="CITE_UNUSED_BIB_ENTRY",
                message=f"BibTeX key {key!r} is not cited by any section",
                location="paper/refs.bib",
                fixup_hint="Remove unused references or cite them in a section.",
            )
        )
    return CheckReport(
        checker="citations",
        issues=issues,
        result={"cited_keys": sorted(cited), "bib_keys": sorted(bib)},
    )
