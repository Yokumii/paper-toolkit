"""Shared helpers for checker implementations."""

from __future__ import annotations

import re
from pathlib import Path

from paper_toolkit.models.check_report import CheckIssue
from paper_toolkit.paths import WorkspacePaths


def section_paths(*, workspace: Path, section: str | None = None) -> list[Path]:
    paths = WorkspacePaths(workspace=workspace)
    if section is not None:
        target = paths.sections_dir / f"{section}.tex"
        return [target] if target.exists() else []
    if not paths.sections_dir.exists():
        return []
    return sorted(path for path in paths.sections_dir.glob("*.tex") if path.is_file())


def read_sections(*, workspace: Path, section: str | None = None) -> dict[str, str]:
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in section_paths(workspace=workspace, section=section)
    }


def word_count(text: str) -> int:
    stripped = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", text)
    stripped = re.sub(r"[%].*", " ", stripped)
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", stripped))


def issue(
    *,
    severity: str,
    code: str,
    message: str,
    location: str | None = None,
    fixup_hint: str | None = None,
) -> CheckIssue:
    return CheckIssue(
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
        location=location,
        fixup_hint=fixup_hint,
    )
