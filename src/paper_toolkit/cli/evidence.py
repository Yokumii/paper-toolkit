"""`paper evidence ...` command logic."""

from __future__ import annotations

from pathlib import Path
from typing import get_args

from paper_toolkit.envelope import Envelope, ErrorEntry, build_envelope
from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.evidence import (
    ClaimStrength,
    EdgeKind,
    EvidenceGraph,
    EvidenceSource,
    EvidenceSourceKind,
    GraphEdge,
    GraphNode,
)
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state import evidence_graph as graph_state
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    compute_state_summary,
    read_state,
    refresh_artifact_ref,
    write_state,
)

_STRENGTHS: tuple[str, ...] = get_args(ClaimStrength)
_SOURCE_KINDS: tuple[str, ...] = get_args(EvidenceSourceKind)
_EDGE_KINDS: tuple[str, ...] = get_args(EdgeKind)


def _bad_choice_envelope(*, action: str, code: str, message: str, fixup_hint: str) -> Envelope:
    from paper_toolkit.cli.status import _zero_summary

    return build_envelope(
        action=action,
        result={},
        state_summary=_zero_summary(),
        errors=[ErrorEntry(code=code, message=message, fixup_hint=fixup_hint)],
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


def _save_graph_and_envelope(
    *,
    workspace: Path,
    action: str,
    result: dict[str, object],
    graph: EvidenceGraph,
    errors: list[ErrorEntry] | None = None,
    warnings: list[str] | None = None,
) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action=action)
    if not errors:
        graph_state.save(workspace=workspace, graph=graph)
        refresh_artifact_ref(workspace=workspace, state=state, artifact="evidence_graph")
        write_state(workspace=workspace, state=state)
    summary = compute_state_summary(workspace=workspace, state=state)
    return build_envelope(
        action=action,
        result=result,
        state_summary=summary,
        errors=errors,
        warnings=warnings,
    )


def add_claim(
    *,
    workspace: Path,
    node_id: str,
    label: str,
    body: str | None,
    section: str | None,
    strength: str | None,
) -> Envelope:
    if strength is not None and strength not in _STRENGTHS:
        return _bad_choice_envelope(
            action="evidence.add-claim",
            code="EVD_BAD_STRENGTH",
            message=f"strength must be one of {list(_STRENGTHS)}; got {strength!r}",
            fixup_hint="Pass --strength primary | supporting | minor (or omit).",
        )
    graph = graph_state.load_or_empty(workspace=workspace)
    node = GraphNode(
        id=node_id,
        kind="claim",
        label=label,
        body=body,
        section=section,
        strength=strength,  # type: ignore[arg-type]
    )
    graph, error = graph_state.add_node(graph=graph, node=node)
    return _save_graph_and_envelope(
        workspace=workspace,
        action="evidence.add-claim",
        result={"node_id": node_id},
        graph=graph,
        errors=[error] if error else None,
    )


def add_evidence(
    *,
    workspace: Path,
    node_id: str,
    label: str,
    source_kind: str,
    source_ref: str,
    source_detail: str | None,
    body: str | None,
) -> Envelope:
    if source_kind not in _SOURCE_KINDS:
        return _bad_choice_envelope(
            action="evidence.add-evidence",
            code="EVD_BAD_SOURCE_KIND",
            message=f"source-kind must be one of {list(_SOURCE_KINDS)}; got {source_kind!r}",
            fixup_hint="Pass --source-kind figure | table | stat | qual | external.",
        )
    graph = graph_state.load_or_empty(workspace=workspace)
    node = GraphNode(
        id=node_id,
        kind="evidence",
        label=label,
        body=body,
        source=EvidenceSource(kind=source_kind, ref=source_ref, detail=source_detail),  # type: ignore[arg-type]
    )
    graph, error = graph_state.add_node(graph=graph, node=node)
    return _save_graph_and_envelope(
        workspace=workspace,
        action="evidence.add-evidence",
        result={"node_id": node_id},
        graph=graph,
        errors=[error] if error else None,
    )


def add_citation(
    *, workspace: Path, node_id: str, cite_key: str, label: str, body: str | None
) -> Envelope:
    graph = graph_state.load_or_empty(workspace=workspace)
    node = GraphNode(id=node_id, kind="citation", label=label, body=body, cite_key=cite_key)
    graph, error = graph_state.add_node(graph=graph, node=node)
    return _save_graph_and_envelope(
        workspace=workspace,
        action="evidence.add-citation",
        result={"node_id": node_id, "cite_key": cite_key},
        graph=graph,
        errors=[error] if error else None,
    )


def link(*, workspace: Path, src: str, dst: str, kind: str) -> Envelope:
    if kind not in _EDGE_KINDS:
        return _bad_choice_envelope(
            action="evidence.link",
            code="EVD_BAD_EDGE_KIND",
            message=f"edge kind must be one of {list(_EDGE_KINDS)}; got {kind!r}",
            fixup_hint="Pass --kind supports | derives_from | cites | contradicts.",
        )
    graph = graph_state.load_or_empty(workspace=workspace)
    graph, error = graph_state.add_edge(graph=graph, edge=GraphEdge(src=src, dst=dst, kind=kind))  # type: ignore[arg-type]
    return _save_graph_and_envelope(
        workspace=workspace,
        action="evidence.link",
        result={"src": src, "dst": dst, "kind": kind},
        graph=graph,
        errors=[error] if error else None,
    )


def rm_node(*, workspace: Path, node_id: str) -> Envelope:
    graph = graph_state.load_or_empty(workspace=workspace)
    graph, removed = graph_state.remove_node(graph=graph, node_id=node_id)
    return _save_graph_and_envelope(
        workspace=workspace,
        action="evidence.rm-node",
        result={"node_id": node_id, "removed": removed},
        graph=graph,
    )


def rm_edge(*, workspace: Path, src: str, dst: str, kind: str | None) -> Envelope:
    graph = graph_state.load_or_empty(workspace=workspace)
    graph, removed = graph_state.remove_edge(graph=graph, src=src, dst=dst, kind=kind)
    return _save_graph_and_envelope(
        workspace=workspace,
        action="evidence.rm-edge",
        result={"src": src, "dst": dst, "kind": kind, "removed": removed},
        graph=graph,
    )


def validate(*, workspace: Path) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="evidence.validate")
    paths = WorkspacePaths(workspace=workspace)
    graph = graph_state.load_or_empty(workspace=workspace)
    refs_text = paths.refs_bib.read_text(encoding="utf-8") if paths.refs_bib.exists() else None
    errors, warnings = graph_state.validate_graph(graph=graph, refs_bib_text=refs_text)
    summary = compute_state_summary(workspace=workspace, state=state)
    return build_envelope(
        action="evidence.validate",
        result={"error_count": len(errors), "warning_count": len(warnings)},
        state_summary=summary,
        errors=errors,
        warnings=warnings,
    )


def topo_order(*, workspace: Path) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="evidence.topo-order")
    graph = graph_state.load_or_empty(workspace=workspace)
    summary = compute_state_summary(workspace=workspace, state=state)
    return build_envelope(
        action="evidence.topo-order",
        result={"order": graph_state.topo_order(graph=graph)},
        state_summary=summary,
    )


def render_mermaid(*, workspace: Path, out: Path | None) -> Envelope:
    try:
        state = read_state(workspace=workspace)
    except WorkspaceNotInitialized:
        return _missing_workspace_envelope(workspace=workspace, action="evidence.render-mermaid")
    graph = graph_state.load_or_empty(workspace=workspace)
    mermaid_text = graph_state.render_mermaid(graph=graph)
    out_path = None
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        write_atomic_text(out, mermaid_text)
        out_path = str(out)
    summary = compute_state_summary(workspace=workspace, state=state)
    return build_envelope(
        action="evidence.render-mermaid",
        result={"mermaid_text": mermaid_text, "out": out_path},
        state_summary=summary,
    )
