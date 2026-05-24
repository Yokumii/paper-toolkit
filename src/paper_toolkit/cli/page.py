"""`paper page ...` command logic."""

from __future__ import annotations

from pathlib import Path

from paper_toolkit.envelope import Envelope, ErrorEntry, build_envelope
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
)
from paper_toolkit.typeset.page_inspector import (
    count_pages,
    load_page_elements,
    load_pages,
    overflow_elements,
    parse_page_range,
    render_compile_pages,
)


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
                fixup_hint="Run: paper init --title ... --venue nature --language en",
            )
        ],
    )


def count_cmd(*, workspace: Path, run_id: str) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="page.count")
    return build_envelope(
        action="page.count",
        result={"run": run_id, "page_count": count_pages(workspace=workspace, run_id=run_id)},
        state_summary=compute_state_summary(workspace=workspace, state=state),
    )


def elements_cmd(*, workspace: Path, run_id: str, page: int) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="page.elements")
    elements = load_page_elements(workspace=workspace, run_id=run_id, page=page)
    return build_envelope(
        action="page.elements",
        result={
            "run": run_id,
            "page_number": page,
            "elements": [e.model_dump(mode="json") for e in elements],
        },
        state_summary=compute_state_summary(workspace=workspace, state=state),
    )


def overflow_cmd(*, workspace: Path, run_id: str) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="page.overflow")
    elements = overflow_elements(workspace=workspace, run_id=run_id)
    return build_envelope(
        action="page.overflow",
        result={"run": run_id, "elements": [e.model_dump(mode="json") for e in elements]},
        state_summary=compute_state_summary(workspace=workspace, state=state),
    )


def render_cmd(
    *,
    workspace: Path,
    run_id: str,
    pages: str | None,
    dpi: int,
) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="page.render")
    paths = WorkspacePaths(workspace=workspace)
    run_dir = paths.compile_run_dir(run_id)
    if not run_dir.exists():
        return build_envelope(
            action="page.render",
            result={"run": run_id},
            state_summary=compute_state_summary(workspace=workspace, state=state),
            errors=[
                ErrorEntry(
                    code="PAGE_RUN_NOT_FOUND",
                    message=f"compile run {run_id!r} not found at {run_dir}",
                    fixup_hint="Pass --run rN where N matches an entry in paper/compile_runs/.",
                )
            ],
        )

    pdf_path = run_dir / "main.pdf"
    rendered = render_compile_pages(
        run_id=run_id,
        run_dir=run_dir,
        pdf_path=pdf_path if pdf_path.exists() else None,
        dpi=dpi,
    )
    selected = parse_page_range(pages, total=len(rendered))
    selected_pages = [p for p in rendered if p.page_number in selected]
    warnings: list[str] = []
    if pdf_path.exists() and not rendered:
        warnings.append("PDF found but no pages were rendered — is pdf2image / poppler installed?")

    return build_envelope(
        action="page.render",
        result={
            "run": run_id,
            "dpi": dpi,
            "selected_pages": selected,
            "total_pages": len(rendered),
            "pages": [p.model_dump(mode="json") for p in selected_pages],
        },
        state_summary=compute_state_summary(workspace=workspace, state=state),
        warnings=warnings,
    )


__all__ = [
    "count_cmd",
    "elements_cmd",
    "load_pages",
    "overflow_cmd",
    "render_cmd",
]
