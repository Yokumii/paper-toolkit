"""`paper figure ...` command logic."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from paper_toolkit.envelope import Envelope, ErrorEntry, StateSummary, build_envelope
from paper_toolkit.figures.data_loader import FigureDataMalformed, FigureDataNotFound
from paper_toolkit.figures.palettes import list_palette_names
from paper_toolkit.figures.renderer import RenderResult, render_figure, render_script_figure
from paper_toolkit.models.figure_spec import FigureSpec, ScriptFigureSpec
from paper_toolkit.models.paper_state import FigureArtifact
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
    write_state,
)

_FIGURE_SPEC_ADAPTER: TypeAdapter[FigureSpec] = TypeAdapter(FigureSpec)


def _zero_summary() -> StateSummary:
    from paper_toolkit.cli.main import _zero_summary as zero

    return zero()


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


def _state_summary(workspace: Path) -> StateSummary:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _zero_summary()
    return compute_state_summary(workspace=workspace, state=state)


def _load_spec(spec_path: Path) -> FigureSpec:
    raw = json.loads(spec_path.read_text(encoding="utf-8"))
    return _FIGURE_SPEC_ADAPTER.validate_python(raw)


def _render_result_payload(result: RenderResult) -> dict[str, str]:
    return {
        "figure_id": result.figure_id,
        "pdf_path": str(result.pdf_path),
        "svg_path": str(result.svg_path),
        "tex_path": str(result.tex_path),
    }


def render_cmd(*, workspace: Path, spec_path: Path) -> Envelope:
    try:
        # Workspace must be initialized so figures land in the canonical paper/figures dir.
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="figure.render")

    if not spec_path.is_file():
        return build_envelope(
            action="figure.render",
            result={"spec_path": str(spec_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="FIG_SPEC_NOT_FOUND",
                    message=f"figure spec not found: {spec_path}",
                    fixup_hint="Pass --spec pointing to an existing JSON spec.",
                )
            ],
        )

    try:
        spec = _load_spec(spec_path)
    except json.JSONDecodeError as exc:
        return build_envelope(
            action="figure.render",
            result={"spec_path": str(spec_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="FIG_SPEC_INVALID",
                    message=f"could not parse JSON: {exc.msg} (line {exc.lineno})",
                )
            ],
        )
    except ValidationError as exc:
        return build_envelope(
            action="figure.render",
            result={"spec_path": str(spec_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="FIG_SPEC_INVALID",
                    message=str(exc),
                )
            ],
        )

    try:
        if isinstance(spec, ScriptFigureSpec):
            result = render_script_figure(spec=spec, workspace=workspace, spec_dir=spec_path.parent)
        else:
            result = render_figure(spec=spec, workspace=workspace, spec_dir=spec_path.parent)
    except FigureDataNotFound as exc:
        return build_envelope(
            action="figure.render",
            result={"figure_id": spec.id},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="FIG_DATA_NOT_FOUND", message=str(exc))],
        )
    except FigureDataMalformed as exc:
        return build_envelope(
            action="figure.render",
            result={"figure_id": spec.id},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="FIG_DATA_MALFORMED", message=str(exc))],
        )

    return build_envelope(
        action="figure.render",
        result=_render_result_payload(result),
        state_summary=_state_summary(workspace),
    )


def render_all_cmd(*, workspace: Path) -> Envelope:
    try:
        read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="figure.render-all")

    paths = WorkspacePaths(workspace=workspace)
    spec_dir = paths.figure_specs_dir
    rendered: list[dict[str, str]] = []
    warnings: list[str] = []

    if not spec_dir.exists():
        return build_envelope(
            action="figure.render-all",
            result={"rendered": rendered, "spec_dir": str(spec_dir)},
            state_summary=_state_summary(workspace),
            warnings=[f"figure_specs/ does not exist at {spec_dir}"],
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
        action="figure.render-all",
        result={"rendered": rendered, "spec_dir": str(spec_dir)},
        state_summary=_state_summary(workspace),
        warnings=warnings,
    )


def list_palettes_cmd() -> Envelope:
    return build_envelope(
        action="figure.list-palettes",
        result={"palettes": list_palette_names()},
        state_summary=_zero_summary(),
    )


def register_cmd(*, workspace: Path, spec_path: Path) -> Envelope:
    """Register a rendered figure in `paper.json:artifacts.figures[]`.

    Idempotent: an existing FigureArtifact with the same `id` is replaced
    in place (caption + paths refreshed; `referenced_by` is preserved).
    """
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="figure.register")

    if not spec_path.is_file():
        return build_envelope(
            action="figure.register",
            result={"spec_path": str(spec_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="FIG_SPEC_NOT_FOUND",
                    message=f"figure spec not found: {spec_path}",
                )
            ],
        )

    try:
        spec = _load_spec(spec_path)
    except json.JSONDecodeError as exc:
        return build_envelope(
            action="figure.register",
            result={"spec_path": str(spec_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="FIG_SPEC_INVALID",
                    message=f"could not parse JSON: {exc.msg} (line {exc.lineno})",
                )
            ],
        )
    except ValidationError as exc:
        return build_envelope(
            action="figure.register",
            result={"spec_path": str(spec_path)},
            state_summary=_state_summary(workspace),
            errors=[ErrorEntry(code="FIG_SPEC_INVALID", message=str(exc))],
        )

    paths = WorkspacePaths(workspace=workspace)
    packed_path = paths.figures_dir / f"{spec.id}.pdf"
    if not packed_path.exists():
        return build_envelope(
            action="figure.register",
            result={"figure_id": spec.id, "packed": str(packed_path)},
            state_summary=_state_summary(workspace),
            errors=[
                ErrorEntry(
                    code="FIG_PDF_MISSING",
                    message=f"rendered figure not found at {packed_path}",
                    fixup_hint=f"Run: paper figure render --spec {spec_path}",
                )
            ],
        )

    src_rel = paths.relative_to_workspace(spec_path)
    packed_rel = paths.relative_to_workspace(packed_path)

    existing_idx = next((i for i, f in enumerate(state.artifacts.figures) if f.id == spec.id), None)
    if existing_idx is not None:
        existing = state.artifacts.figures[existing_idx]
        artifact = FigureArtifact(
            id=spec.id,
            src=src_rel,
            packed=packed_rel,
            caption=spec.caption,
            referenced_by=existing.referenced_by,
        )
        state.artifacts.figures[existing_idx] = artifact
        action_taken = "updated"
    else:
        artifact = FigureArtifact(
            id=spec.id,
            src=src_rel,
            packed=packed_rel,
            caption=spec.caption,
            referenced_by=[],
        )
        state.artifacts.figures.append(artifact)
        action_taken = "inserted"

    # Touch `updated_at` on paper.json by re-writing it. write_state is atomic.
    _ = datetime.now(UTC)  # not stored on Artifacts; helper kept for symmetry
    write_state(workspace=workspace, state=state)

    return build_envelope(
        action="figure.register",
        result={
            "figure_id": spec.id,
            "action": action_taken,
            "src": src_rel,
            "packed": packed_rel,
            "caption": spec.caption,
        },
        state_summary=compute_state_summary(workspace=workspace, state=state),
    )
