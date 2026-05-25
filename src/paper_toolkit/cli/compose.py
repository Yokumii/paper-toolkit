"""`paper compose ...` command logic."""

from __future__ import annotations

import re
from pathlib import Path

from paper_toolkit.compose.bib_writer import write_bib
from paper_toolkit.compose.figure_packer import FigurePackItem, pack_figures
from paper_toolkit.compose.latex_assembly import write_main_tex
from paper_toolkit.envelope import Envelope, ErrorEntry, build_envelope
from paper_toolkit.models.paper_state import FigureArtifact
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state import evidence_graph as graph_state
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
    refresh_artifact_ref,
    write_state,
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
            )
        ],
    )


_REF_RE = re.compile(r"\\ref\{([^}]+)\}")


def _key_variants(figure_id: str) -> set[str]:
    """Generate the LaTeX label variants that a packed figure id may appear as.

    `fig1`, `fig:1`, and the bare digit form are all treated as equivalent.
    """
    keys = {figure_id, figure_id.removeprefix("fig:"), f"fig:{figure_id.removeprefix('fig:')}"}
    m = re.search(r"(\d+)$", figure_id)
    if m:
        n = m.group(1)
        keys.update({f"fig{n}", f"fig:{n}", n})
    return keys


def _populate_referenced_by(
    *, workspace: Path, figures: list[FigureArtifact]
) -> list[FigureArtifact]:
    """Scan each section .tex for `\\ref{figure_id}` and record where each figure is used."""
    paths = WorkspacePaths(workspace=workspace)
    if not paths.sections_dir.exists() or not figures:
        return figures
    section_refs: dict[str, set[str]] = {}
    for tex in paths.sections_dir.glob("*.tex"):
        try:
            text = tex.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ref in _REF_RE.findall(text):
            section_refs.setdefault(ref, set()).add(tex.stem)
    updated: list[FigureArtifact] = []
    for fig in figures:
        sections = sorted(
            {s for key in _key_variants(fig.id) for s in section_refs.get(key, set())}
        )
        updated.append(fig.model_copy(update={"referenced_by": sections}))
    return updated


def pack_figures_cmd(*, workspace: Path) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="compose.pack-figures")

    paths = WorkspacePaths(workspace=workspace)
    paths.figures_dir.mkdir(parents=True, exist_ok=True)

    if state.artifacts.figures:
        missing: list[str] = []
        kept: list[FigureArtifact] = []
        for fig in state.artifacts.figures:
            packed_abs = (paths.workspace / fig.packed).resolve()
            if not packed_abs.is_file():
                missing.append(fig.id)
                continue
            kept.append(fig)
        if missing:
            summary = compute_state_summary(workspace=workspace, state=state)
            return build_envelope(
                action="compose.pack-figures",
                result={"packed_figure_count": len(kept)},
                state_summary=summary,
                errors=[
                    ErrorEntry(
                        code="FIGURE_PACKED_MISSING",
                        message=(
                            f"registered figure '{fid}' has no packed PDF "
                            f"at paper/figures/{fid}.pdf"
                        ),
                        fixup_hint=f"Run: paper figure render --spec paper/figure_specs/{fid}.json",
                    )
                    for fid in missing
                ],
            )
        state.artifacts.figures = _populate_referenced_by(workspace=workspace, figures=kept)
        write_state(workspace=workspace, state=state)
        summary = compute_state_summary(workspace=workspace, state=state)
        return build_envelope(
            action="compose.pack-figures",
            result={
                "packed_figure_count": len(state.artifacts.figures),
                "referenced_by": {fig.id: fig.referenced_by for fig in state.artifacts.figures},
            },
            state_summary=summary,
        )

    graph = graph_state.load_or_empty(workspace=workspace)
    figure_nodes = [
        node
        for node in graph.nodes
        if node.kind == "evidence" and node.source and node.source.kind == "figure"
    ]
    items = [
        FigurePackItem(
            figure_id=f"fig{idx}",
            src=Path(node.source.ref),  # type: ignore[union-attr]
            caption=node.label,
        )
        for idx, node in enumerate(figure_nodes, start=1)
    ]
    try:
        figures = pack_figures(workspace=workspace, items=items)
    except FileNotFoundError as exc:
        summary = compute_state_summary(workspace=workspace, state=state)
        return build_envelope(
            action="compose.pack-figures",
            result={"packed_figure_count": 0},
            state_summary=summary,
            errors=[ErrorEntry(code="FIGURE_SOURCE_MISSING", message=str(exc))],
        )
    state.artifacts.figures = _populate_referenced_by(workspace=workspace, figures=figures)
    write_state(workspace=workspace, state=state)
    summary = compute_state_summary(workspace=workspace, state=state)
    return build_envelope(
        action="compose.pack-figures",
        result={
            "packed_figure_count": len(state.artifacts.figures),
            "referenced_by": {fig.id: fig.referenced_by for fig in state.artifacts.figures},
        },
        state_summary=summary,
    )


def write_bib_cmd(*, workspace: Path) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="compose.write-bib")
    graph = graph_state.load_or_empty(workspace=workspace)
    path = write_bib(workspace=workspace, graph=graph)
    refresh_artifact_ref(workspace=workspace, state=state, artifact="bib")
    write_state(workspace=workspace, state=state)
    summary = compute_state_summary(workspace=workspace, state=state)
    return build_envelope(
        action="compose.write-bib",
        result={
            "bib_path": str(path),
            "citation_count": sum(1 for node in graph.nodes if node.kind == "citation"),
        },
        state_summary=summary,
    )


def assemble_latex_cmd(*, workspace: Path) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="compose.assemble-latex")
    path = write_main_tex(workspace=workspace, title=state.meta.title)
    refresh_artifact_ref(workspace=workspace, state=state, artifact="main_tex")
    write_state(workspace=workspace, state=state)
    summary = compute_state_summary(workspace=workspace, state=state)
    return build_envelope(
        action="compose.assemble-latex",
        result={"main_tex_path": str(path)},
        state_summary=summary,
    )
