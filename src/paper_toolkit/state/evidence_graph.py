"""Persistence, validation, and read-only transforms for evidence graphs."""

from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from pathlib import Path

from paper_toolkit.envelope import ErrorEntry
from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.evidence import EvidenceGraph, GraphEdge, GraphNode
from paper_toolkit.paths import WorkspacePaths


def exists(*, workspace: Path) -> bool:
    return WorkspacePaths(workspace=workspace).evidence_graph.exists()


def load(*, workspace: Path) -> EvidenceGraph:
    path = WorkspacePaths(workspace=workspace).evidence_graph
    if not path.exists():
        raise FileNotFoundError(f"evidence_graph.json not found at {path}")
    return EvidenceGraph.model_validate_json(path.read_text(encoding="utf-8"))


def load_or_empty(*, workspace: Path) -> EvidenceGraph:
    if not exists(workspace=workspace):
        return EvidenceGraph(schema_version="1.0")
    return load(workspace=workspace)


def save(*, workspace: Path, graph: EvidenceGraph) -> None:
    path = WorkspacePaths(workspace=workspace).evidence_graph
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(
        path,
        json.dumps(graph.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
    )


def _node_map(graph: EvidenceGraph) -> dict[str, GraphNode]:
    return {node.id: node for node in graph.nodes}


def _duplicate_node_errors(graph: EvidenceGraph) -> list[ErrorEntry]:
    seen: set[str] = set()
    errors: list[ErrorEntry] = []
    for node in graph.nodes:
        if node.id in seen:
            errors.append(
                ErrorEntry(
                    code="EVD_DUPLICATE_NODE",
                    message=f"duplicate node id {node.id!r}",
                    location=f"node:{node.id}",
                    fixup_hint="Use unique node ids.",
                )
            )
        seen.add(node.id)
    return errors


def _edge_endpoint_errors(graph: EvidenceGraph, nodes: dict[str, GraphNode]) -> list[ErrorEntry]:
    errors: list[ErrorEntry] = []
    for edge in graph.edges:
        if edge.src not in nodes:
            errors.append(
                ErrorEntry(
                    code="EVD_EDGE_MISSING_SRC",
                    message=f"edge source {edge.src!r} does not exist",
                    location=f"edge:{edge.src}->{edge.dst}",
                    fixup_hint="Add the source node or remove the edge.",
                )
            )
        if edge.dst not in nodes:
            errors.append(
                ErrorEntry(
                    code="EVD_EDGE_MISSING_DST",
                    message=f"edge destination {edge.dst!r} does not exist",
                    location=f"edge:{edge.src}->{edge.dst}",
                    fixup_hint="Add the destination node or remove the edge.",
                )
            )
    return errors


def _derive_dependencies(graph: EvidenceGraph) -> dict[str, set[str]]:
    deps: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge.kind == "derives_from":
            deps[edge.src].add(edge.dst)
    return deps


def _has_derive_cycle(deps: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        for dep in deps.get(node_id, set()):
            if visit(dep):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return any(visit(node_id) for node_id in deps)


def _supported_claim_ids(graph: EvidenceGraph, nodes: dict[str, GraphNode]) -> set[str]:
    supported = {
        edge.dst
        for edge in graph.edges
        if edge.kind == "supports"
        and (src := nodes.get(edge.src)) is not None
        and src.kind == "evidence"
        and (dst := nodes.get(edge.dst)) is not None
        and dst.kind == "claim"
    }
    deps = _derive_dependencies(graph)
    changed = True
    while changed:
        changed = False
        for claim_id, dep_ids in deps.items():
            if claim_id in supported or not dep_ids:
                continue
            if all(dep_id in supported for dep_id in dep_ids):
                supported.add(claim_id)
                changed = True
    return supported


def _citation_keys(refs_bib_text: str) -> set[str]:
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", refs_bib_text))


def validate_graph(
    *,
    graph: EvidenceGraph,
    refs_bib_text: str | None,
) -> tuple[list[ErrorEntry], list[str]]:
    nodes = _node_map(graph)
    errors = _duplicate_node_errors(graph)
    errors.extend(_edge_endpoint_errors(graph, nodes))

    deps = _derive_dependencies(graph)
    if _has_derive_cycle(deps):
        errors.append(
            ErrorEntry(
                code="EVD_DERIVES_CYCLE",
                message="derives_from subgraph contains a cycle",
                location="edges:derives_from",
                fixup_hint="Remove at least one derives_from edge in the cycle.",
            )
        )

    supported = _supported_claim_ids(graph, nodes)
    for node in graph.nodes:
        if node.kind == "claim" and node.id not in supported:
            errors.append(
                ErrorEntry(
                    code="EVD_UNSUPPORTED_CLAIM",
                    message=f"claim {node.id!r} has no evidence support",
                    location=f"node:{node.id}",
                    fixup_hint=(
                        "Add an evidence node and supports edge, or derive from supported claims."
                    ),
                )
            )

    for edge in graph.edges:
        if edge.kind == "contradicts":
            src = nodes.get(edge.src)
            dst = nodes.get(edge.dst)
            if src is not None and dst is not None and src.label == dst.label:
                errors.append(
                    ErrorEntry(
                        code="EVD_CONTRADICTS_IDENTICAL",
                        message="contradicts edge connects claims with identical labels",
                        location=f"edge:{edge.src}->{edge.dst}",
                        fixup_hint="Remove the edge or change one claim label.",
                    )
                )

    warnings: list[str] = []
    citation_nodes = [node for node in graph.nodes if node.kind == "citation"]
    if citation_nodes and refs_bib_text is None:
        warnings.append("refs.bib is missing; citation resolvability deferred.")
    if refs_bib_text is not None:
        keys = _citation_keys(refs_bib_text)
        for node in citation_nodes:
            if node.cite_key not in keys:
                errors.append(
                    ErrorEntry(
                        code="EVD_CITATION_MISSING",
                        message=f"cite_key {node.cite_key!r} not found in refs.bib",
                        location=f"node:{node.id}",
                        fixup_hint="Add the BibTeX entry or fix the citation node cite_key.",
                    )
                )

    return errors, warnings


def topo_order(*, graph: EvidenceGraph) -> list[str]:
    claims = {node.id for node in graph.nodes if node.kind == "claim"}
    indegree = {node_id: 0 for node_id in claims}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.kind == "derives_from" and edge.src in claims and edge.dst in claims:
            outgoing[edge.dst].append(edge.src)
            indegree[edge.src] += 1

    queue = deque(sorted(node_id for node_id, count in indegree.items() if count == 0))
    ordered: list[str] = []
    while queue:
        node_id = queue.popleft()
        ordered.append(node_id)
        for child in sorted(outgoing[node_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    return ordered


def render_mermaid(*, graph: EvidenceGraph) -> str:
    lines = ["graph TD"]
    for node in graph.nodes:
        label = node.label.replace('"', "'")
        lines.append(f'  {node.id}["{node.kind}: {label}"]')
    for edge in graph.edges:
        lines.append(f"  {edge.src} -->|{edge.kind}| {edge.dst}")
    return "\n".join(lines) + "\n"


def add_node(*, graph: EvidenceGraph, node: GraphNode) -> tuple[EvidenceGraph, ErrorEntry | None]:
    if any(existing.id == node.id for existing in graph.nodes):
        return graph, ErrorEntry(
            code="EVD_NODE_EXISTS",
            message=f"node {node.id!r} already exists",
            location=f"node:{node.id}",
            fixup_hint="Use a unique node id.",
        )
    updated = graph.model_copy(deep=True)
    updated.nodes.append(node)
    return updated, None


def add_edge(*, graph: EvidenceGraph, edge: GraphEdge) -> tuple[EvidenceGraph, ErrorEntry | None]:
    if any(existing == edge for existing in graph.edges):
        return graph, ErrorEntry(
            code="EVD_EDGE_EXISTS",
            message=f"edge {edge.src}->{edge.dst} ({edge.kind}) already exists",
            location=f"edge:{edge.src}->{edge.dst}",
            fixup_hint="Skip duplicate links.",
        )
    updated = graph.model_copy(deep=True)
    updated.edges.append(edge)
    return updated, None


def remove_node(*, graph: EvidenceGraph, node_id: str) -> tuple[EvidenceGraph, bool]:
    if not any(node.id == node_id for node in graph.nodes):
        return graph, False
    updated = graph.model_copy(deep=True)
    updated.nodes = [node for node in updated.nodes if node.id != node_id]
    updated.edges = [edge for edge in updated.edges if edge.src != node_id and edge.dst != node_id]
    return updated, True


def remove_edge(
    *, graph: EvidenceGraph, src: str, dst: str, kind: str | None
) -> tuple[EvidenceGraph, bool]:
    def matches(edge: GraphEdge) -> bool:
        return edge.src == src and edge.dst == dst and (kind is None or edge.kind == kind)

    if not any(matches(edge) for edge in graph.edges):
        return graph, False
    updated = graph.model_copy(deep=True)
    updated.edges = [edge for edge in updated.edges if not matches(edge)]
    return updated, True
