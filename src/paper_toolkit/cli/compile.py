"""`paper compile-once` command logic."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from paper_toolkit.envelope import Envelope, ErrorEntry, build_envelope
from paper_toolkit.models.paper_state import CompileRunRef
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    append_compile_run_ref,
    compute_state_summary,
    read_state,
    write_state,
)
from paper_toolkit.typeset.compiler import compile_once


def run(*, workspace: Path, engine: str, max_attempts: int | None) -> Envelope:
    paths = WorkspacePaths(workspace=workspace)
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        from paper_toolkit.cli.status import _zero_summary

        return build_envelope(
            action="compile-once",
            result={"workspace": str(paths.workspace)},
            state_summary=_zero_summary(),
            errors=[
                ErrorEntry(
                    code="WS_NOT_INITIALIZED",
                    message=f"no paper.json found at {paths.paper_state}",
                )
            ],
        )

    started_at = datetime.now(UTC)
    result = compile_once(workspace=workspace, engine=engine, max_attempts=max_attempts)
    finished_at = datetime.now(UTC)
    append_compile_run_ref(
        state=state,
        compile_run=CompileRunRef(
            id=result.id,
            ok=result.ok,
            error_count=len(result.errors),
            warning_count=len(result.warnings),
            pdf=result.pdf_path,
            started_at=started_at,
            finished_at=finished_at,
        ),
    )
    write_state(workspace=workspace, state=state)
    summary = compute_state_summary(workspace=workspace, state=state)
    warnings = [warning.message for warning in result.warnings]
    if max_attempts is not None and result.attempt_index > max_attempts:
        warnings.append(
            f"attempt_index {result.attempt_index} exceeds advisory max_attempts {max_attempts}"
        )
    return build_envelope(
        action="compile-once",
        result=result.model_dump(mode="json"),
        state_summary=summary,
        errors=[
            ErrorEntry(
                code=error.code,
                message=error.message,
                location=error.file,
                fixup_hint=error.fixup_hint,
            )
            for error in result.errors
        ],
        warnings=warnings,
    )
