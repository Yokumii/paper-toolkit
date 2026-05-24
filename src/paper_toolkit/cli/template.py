"""`paper template ...` command logic."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.envelope import Envelope, ErrorEntry, build_envelope
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
    refresh_artifact_ref,
    write_state,
)
from paper_toolkit.template import expand_template, list_templates


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


def list_cmd(*, workspace: Path) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="template.list")
    return build_envelope(
        action="template.list",
        result={"templates": list_templates(workspace=workspace)},
        state_summary=compute_state_summary(workspace=workspace, state=state),
    )


def expand_cmd(*, workspace: Path, section: str, target: Path | None) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="template.expand")
    try:
        result = expand_template(workspace=workspace, section=section, target=target)
    except FileNotFoundError as exc:
        return build_envelope(
            action="template.expand",
            result={"section": section},
            state_summary=compute_state_summary(workspace=workspace, state=state),
            errors=[ErrorEntry(code="TEMPLATE_NOT_FOUND", message=str(exc))],
        )
    default_section_path = (
        WorkspacePaths(workspace=workspace).sections_dir / f"{section}.tex"
    ).resolve()
    if result.path == default_section_path:
        refresh_artifact_ref(workspace=workspace, state=state, artifact_section=section)
        write_state(workspace=workspace, state=state)
    return build_envelope(
        action="template.expand",
        result={"section": section, "section_path": str(result.path), "source": result.source},
        state_summary=compute_state_summary(workspace=workspace, state=state),
    )
