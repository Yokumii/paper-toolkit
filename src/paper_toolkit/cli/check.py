"""`paper check ...` command logic."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.checkers.citations import check_citations
from paper_toolkit.checkers.claim_coverage import check_claim_coverage
from paper_toolkit.checkers.figure_qa import check_figure_qa
from paper_toolkit.checkers.figures import check_figures
from paper_toolkit.checkers.logic_consistency import check_logic_consistency
from paper_toolkit.checkers.runner import run_all_checks
from paper_toolkit.checkers.style import check_style
from paper_toolkit.checkers.word_count import check_word_count
from paper_toolkit.envelope import Envelope, ErrorEntry, build_envelope
from paper_toolkit.models.check_report import CheckIssue, CheckReport
from paper_toolkit.models.venue import load_venue
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import WorkspaceNotInitialized, compute_state_summary, read_state


def _missing_workspace_envelope(*, workspace: Path, action: str) -> Envelope:
    from paper_toolkit.cli.status import _zero_summary

    paths = WorkspacePaths(workspace=workspace)
    return build_envelope(
        action=action,
        result={"workspace": str(paths.workspace)},
        state_summary=_zero_summary(),
        errors=[
            ErrorEntry(
                code="WS_NOT_INITIALIZED",
                message=f"no paper.json found at {paths.paper_state}",
            )
        ],
    )


def _issue_to_error(issue: CheckIssue) -> ErrorEntry:
    return ErrorEntry(
        code=issue.code,
        message=issue.message,
        location=issue.location,
        fixup_hint=issue.fixup_hint,
    )


def _envelope(*, workspace: Path, action: str, report: CheckReport) -> Envelope:
    state = read_state(workspace=workspace)
    errors = [_issue_to_error(issue) for issue in report.issues if issue.severity == "error"]
    warnings = [
        f"{issue.code}: {issue.message}" for issue in report.issues if issue.severity == "warning"
    ]
    return build_envelope(
        action=action,
        result=report.model_dump(mode="json"),
        state_summary=compute_state_summary(workspace=workspace, state=state),
        errors=errors,
        warnings=warnings,
    )


def run_style(*, workspace: Path, section: str | None) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="check.style")
    venue = load_venue(workspace=workspace, venue_name=state.meta.venue)
    return _envelope(
        workspace=workspace,
        action="check.style",
        report=check_style(workspace=workspace, venue=venue, section=section),
    )


def run_citations(*, workspace: Path) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="check.citations")
    return _envelope(
        workspace=workspace,
        action="check.citations",
        report=check_citations(workspace=workspace),
    )


def run_figures(*, workspace: Path) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="check.figures")
    venue = load_venue(workspace=workspace, venue_name=state.meta.venue)
    return _envelope(
        workspace=workspace,
        action="check.figures",
        report=check_figures(workspace=workspace, venue=venue),
    )


def run_figure_qa(*, workspace: Path) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="check.figure-qa")
    return _envelope(
        workspace=workspace,
        action="check.figure-qa",
        report=check_figure_qa(workspace=workspace),
    )


def run_claim_coverage(*, workspace: Path) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="check.claim-coverage")
    return _envelope(
        workspace=workspace,
        action="check.claim-coverage",
        report=check_claim_coverage(workspace=workspace),
    )


def run_word_count(*, workspace: Path, section: str | None) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="check.word-count")
    venue = load_venue(workspace=workspace, venue_name=state.meta.venue)
    return _envelope(
        workspace=workspace,
        action="check.word-count",
        report=check_word_count(workspace=workspace, venue=venue, section=section),
    )


def run_logic_consistency(*, workspace: Path) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="check.logic-consistency")
    return _envelope(
        workspace=workspace,
        action="check.logic-consistency",
        report=check_logic_consistency(workspace=workspace),
    )


def run_all(*, workspace: Path, section: str | None) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="check.all")
    return _envelope(
        workspace=workspace,
        action="check.all",
        report=run_all_checks(workspace=workspace, section=section),
    )
