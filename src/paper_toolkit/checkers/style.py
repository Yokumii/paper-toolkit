"""Style checks driven by venue config."""

from __future__ import annotations

import re
from pathlib import Path

from paper_toolkit.checkers.base import issue, read_sections
from paper_toolkit.models.check_report import CheckReport
from paper_toolkit.models.venue import VenueConfig


def check_style(*, workspace: Path, venue: VenueConfig, section: str | None = None) -> CheckReport:
    issues = []
    for section_name, text in read_sections(workspace=workspace, section=section).items():
        location = f"paper/sections/{section_name}.tex"
        for rule in venue.style_rules.banned_punct:
            if rule.pattern in text:
                issues.append(
                    issue(
                        severity=rule.severity,
                        code="STYLE_BANNED_PUNCT",
                        message=f"banned punctuation pattern {rule.pattern!r} found",
                        location=location,
                        fixup_hint=rule.reason,
                    )
                )
        for rule in venue.style_rules.banned_phrases:
            if re.search(rule.pattern, text, flags=re.IGNORECASE):
                issues.append(
                    issue(
                        severity=rule.severity,
                        code="STYLE_BANNED_PHRASE",
                        message=f"banned phrase pattern {rule.pattern!r} found",
                        location=location,
                        fixup_hint=rule.reason,
                    )
                )
    return CheckReport(checker="style", issues=issues, result={"section": section})
