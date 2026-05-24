"""`paper table ...` command logic."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from paper_toolkit.envelope import Envelope, ErrorEntry, StateSummary, build_envelope
from paper_toolkit.models.table_spec import TableSpec
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
)
from paper_toolkit.tables.renderer import TableRenderResult, render_table


def _zero_summary() -> StateSummary:
    from paper_toolkit.cli.main import _zero_summary as zero

    return zero()


def _state_summary(workspace: Path) -> StateSummary:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _zero_summary()
    return compute_state_summary(workspace=workspace, state=state)


def _missing_workspace_envelope(*, workspace: Path, action: str) -> Envelope:
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


def _load_spec(spec_path: Path) -> TableSpec:
    raw = json.loads(spec_path.read_text(encoding="utf-8"))
    return TableSpec.model_validate(raw)


def _result_payload(result: TableRenderResult) -> dict[str, str]:
    return {"table_id": result.table_id, "tex_path": str(result.tex_path)}


def render_cmd(*, workspace: Path, spec_path: Path) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="table.render")

    if not spec_path.is_file():
        return build_envelope(
            action="table.render",
            result={"spec_path": str(spec_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="TABLE_SPEC_NOT_FOUND",
                    message=f"table spec not found: {spec_path}",
                )
            ],
        )

    try:
        spec = _load_spec(spec_path)
    except json.JSONDecodeError as exc:
        return build_envelope(
            action="table.render",
            result={"spec_path": str(spec_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="TABLE_SPEC_INVALID",
                    message=f"could not parse JSON: {exc.msg} (line {exc.lineno})",
                )
            ],
        )
    except ValidationError as exc:
        return build_envelope(
            action="table.render",
            result={"spec_path": str(spec_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="TABLE_SPEC_INVALID", message=str(exc))],
        )

    result = render_table(spec=spec, workspace=workspace)
    return build_envelope(
        action="table.render",
        result=_result_payload(result),
        state_summary=_state_summary(workspace),
    )


def render_all_cmd(*, workspace: Path) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="table.render-all")

    paths = WorkspacePaths(workspace=workspace)
    spec_dir = paths.table_specs_dir
    rendered: list[dict[str, str]] = []
    warnings: list[str] = []

    if not spec_dir.exists():
        return build_envelope(
            action="table.render-all",
            result={"rendered": rendered, "spec_dir": str(spec_dir)},
            state_summary=_state_summary(workspace),
            warnings=[f"table_specs/ does not exist at {spec_dir}"],
        )

    for spec_path in sorted(spec_dir.glob("*.json")):
        env = render_cmd(workspace=workspace, spec_path=spec_path)
        if env.ok:
            rendered.append(env.result)
        else:
            err = env.errors[0] if env.errors else None
            label = err.code if err else "UNKNOWN"
            message = err.message if err else "(no message)"
            warnings.append(f"{spec_path.name}: {label}: {message}")

    return build_envelope(
        action="table.render-all",
        result={"rendered": rendered, "spec_dir": str(spec_dir)},
        state_summary=_state_summary(workspace),
        warnings=warnings,
    )
