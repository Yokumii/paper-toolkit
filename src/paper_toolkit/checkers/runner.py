"""Run checker sets."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.checkers.citations import check_citations
from paper_toolkit.checkers.claim_coverage import check_claim_coverage
from paper_toolkit.checkers.figure_qa import check_figure_qa
from paper_toolkit.checkers.figures import check_figures
from paper_toolkit.checkers.logic_consistency import check_logic_consistency
from paper_toolkit.checkers.style import check_style
from paper_toolkit.checkers.word_count import check_word_count
from paper_toolkit.models.check_report import CheckReport, merge_reports
from paper_toolkit.models.venue import load_venue
from paper_toolkit.state.workspace import read_state


def run_all_checks(*, workspace: Path, section: str | None = None) -> CheckReport:
    state = read_state(workspace=workspace)
    venue = load_venue(workspace=workspace, venue_name=state.meta.venue)
    reports = [
        check_style(workspace=workspace, venue=venue, section=section),
        check_citations(workspace=workspace),
        check_figures(workspace=workspace, venue=venue),
        check_figure_qa(workspace=workspace),
        check_claim_coverage(workspace=workspace),
        check_word_count(workspace=workspace, venue=venue, section=section),
        check_logic_consistency(workspace=workspace),
    ]
    return merge_reports(checker="all", reports=reports)
