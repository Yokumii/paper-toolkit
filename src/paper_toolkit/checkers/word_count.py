"""Per-section word count checker."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.checkers.base import issue, read_sections, word_count
from paper_toolkit.models.check_report import CheckReport
from paper_toolkit.models.venue import VenueConfig


def check_word_count(
    *, workspace: Path, venue: VenueConfig, section: str | None = None
) -> CheckReport:
    issues = []
    counts: dict[str, int] = {}
    for section_name, text in read_sections(workspace=workspace, section=section).items():
        count = word_count(text)
        counts[section_name] = count
        expected = venue.word_range_for(section_name)
        if expected is None:
            continue
        low, high = expected
        if count < low:
            issues.append(
                issue(
                    severity="warning",
                    code="WORD_COUNT_LOW",
                    message=f"section {section_name!r} has {count} words; expected at least {low}",
                    location=f"paper/sections/{section_name}.tex",
                )
            )
        elif count > high:
            issues.append(
                issue(
                    severity="warning",
                    code="WORD_COUNT_HIGH",
                    message=f"section {section_name!r} has {count} words; expected at most {high}",
                    location=f"paper/sections/{section_name}.tex",
                )
            )
    return CheckReport(checker="word-count", issues=issues, result={"counts": counts})
