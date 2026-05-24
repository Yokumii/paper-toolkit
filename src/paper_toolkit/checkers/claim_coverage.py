"""Claim coverage checker wrapping evidence graph validation."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.models.check_report import CheckIssue, CheckReport
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state import evidence_graph


def check_claim_coverage(*, workspace: Path) -> CheckReport:
    paths = WorkspacePaths(workspace=workspace)
    graph = evidence_graph.load_or_empty(workspace=workspace)
    refs_text = paths.refs_bib.read_text(encoding="utf-8") if paths.refs_bib.exists() else None
    errors, warnings = evidence_graph.validate_graph(graph=graph, refs_bib_text=refs_text)
    issues = [
        CheckIssue(
            severity="error",
            code=error.code,
            message=error.message,
            location=error.location,
            fixup_hint=error.fixup_hint,
        )
        for error in errors
    ]
    issues.extend(
        CheckIssue(severity="warning", code="EVD_WARNING", message=warning) for warning in warnings
    )
    return CheckReport(checker="claim-coverage", issues=issues)
