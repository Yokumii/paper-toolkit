"""`paper scan` command logic."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.envelope import Envelope, ErrorEntry, build_envelope
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.scanner.agentsociety import AgentSocietyScanner
from paper_toolkit.state import research_pack as research_pack_state
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
    refresh_artifact_ref,
    write_state,
)


def run(*, workspace: Path, scanner: str) -> Envelope:
    paths = WorkspacePaths(workspace=workspace)
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        from paper_toolkit.cli.status import _zero_summary

        return build_envelope(
            action="scan",
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

    if scanner != "agentsociety":
        return build_envelope(
            action="scan",
            result={"workspace": str(paths.workspace), "scanner": scanner},
            state_summary=compute_state_summary(workspace=workspace, state=state),
            errors=[
                ErrorEntry(
                    code="SCAN_UNKNOWN_SCANNER",
                    message=f"unknown scanner {scanner!r}",
                    fixup_hint="Use --scanner agentsociety.",
                )
            ],
        )

    pack = AgentSocietyScanner().scan(paths.workspace)
    research_pack_state.save(workspace=workspace, pack=pack)
    refresh_artifact_ref(workspace=workspace, state=state, artifact="research_pack")
    write_state(workspace=workspace, state=state)
    summary = compute_state_summary(workspace=workspace, state=state)
    return build_envelope(
        action="scan",
        result={
            "workspace": str(paths.workspace),
            "scanner": scanner,
            "research_pack_path": str(paths.research_pack),
            "hypothesis_count": len(pack.hypotheses),
            "analysis_report_count": len(pack.analysis_reports),
            "candidate_figure_count": len(pack.candidate_figures),
            "candidate_table_count": len(pack.candidate_tables),
            "replay_db_count": len(pack.replay_dbs),
        },
        state_summary=summary,
        warnings=pack.notes,
    )
