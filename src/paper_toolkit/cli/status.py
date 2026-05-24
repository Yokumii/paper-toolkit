"""`paper status` command logic."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.envelope import Envelope, ErrorEntry, StateSummary, build_envelope
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
)


def _zero_summary() -> StateSummary:
    return StateSummary(
        section_count=0,
        claim_count=0,
        evidence_count=0,
        citation_count=0,
        figure_count=0,
        packed_figure_count=0,
        graph_valid=True,
        graph_issue_count=0,
        last_compile=None,
        last_updated_artifact=None,
        paper_json_checksum="0" * 64,
    )


def run(*, workspace: Path) -> Envelope:
    paths = WorkspacePaths(workspace=workspace)
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return build_envelope(
            action="status",
            result={"workspace": str(paths.workspace)},
            state_summary=_zero_summary(),
            errors=[
                ErrorEntry(
                    code="WS_NOT_INITIALIZED",
                    message=f"no paper.json found at {paths.paper_state}",
                    fixup_hint="Run: paper init --title ... --venue nature --language en",
                )
            ],
        )

    summary = compute_state_summary(workspace=workspace, state=state)
    return build_envelope(
        action="status",
        result={
            "workspace": str(paths.workspace),
            "paper_state_path": str(paths.paper_state),
            "title": state.meta.title,
            "venue": state.meta.venue,
            "language": state.meta.language,
            "created_at": state.meta.created_at.isoformat(),
        },
        state_summary=summary,
    )
