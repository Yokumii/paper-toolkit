"""Promote analysis-side claims into the paper-side evidence graph.

`lift_claims_to_evidence` walks `claims.json` and, for every claim:

1. Adds a claim node `claim_<claim_id>` if one is not already present
   (label = claim.text, body = full text, strength derived from `kind`,
   section = `results`).
2. If the claim has a `figure_contract`, adds:
   - evidence node `ev_<figure_id>` with `source.kind="figure"`,
     `source.ref=figure_id`;
   - edge `ev_<figure_id> --supports--> claim_<claim_id>`.

Idempotent — re-running the lift skips nodes/edges that already exist.

The bridge does NOT touch citations or external references; those still
go through `paper evidence add-citation` so the agent is forced to think
about each cited source individually.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from paper_toolkit.analysis import claims as claims_state
from paper_toolkit.analysis.synthesis import (
    SynthesisBriefNotFound,
    read_brief,
    write_brief,
)
from paper_toolkit.models.analysis import ClaimKind, ClaimsFile
from paper_toolkit.models.evidence import (
    ClaimStrength,
    EdgeKind,
    EvidenceSource,
    GraphEdge,
    GraphNode,
)
from paper_toolkit.state import evidence_graph as graph_state
from paper_toolkit.state.workspace import (
    WorkspaceNotInitialized,
    read_state,
    refresh_artifact_ref,
    write_state,
)

_KIND_TO_STRENGTH: dict[ClaimKind, ClaimStrength] = {
    "quantitative": "primary",
    "comparative": "primary",
    "qualitative": "supporting",
}


@dataclass(frozen=True)
class LiftResult:
    added_claims: list[str]
    added_evidence: list[str]
    added_edges: list[tuple[str, str]]
    skipped_claims: list[str]


def _paper_claim_id(claim_id: str) -> str:
    return f"claim_{claim_id}"


def _paper_evidence_id(figure_id: str) -> str:
    return f"ev_{figure_id}"


def lift_claims_to_evidence(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> LiftResult:
    """Walk `claims.json` and promote each claim into the paper evidence graph."""
    paper_state = read_state(workspace=workspace)  # raises WorkspaceNotInitialized
    claims_file: ClaimsFile = claims_state.read_claims(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )
    graph = graph_state.load_or_empty(workspace=workspace)
    existing_node_ids = {n.id for n in graph.nodes}
    existing_edges = {(e.src, e.dst, e.kind) for e in graph.edges}

    added_claims: list[str] = []
    added_evidence: list[str] = []
    added_edges: list[tuple[str, str]] = []
    skipped_claims: list[str] = []

    for claim in claims_file.claims:
        paper_claim_id = _paper_claim_id(claim.claim_id)
        if paper_claim_id not in existing_node_ids:
            strength = _KIND_TO_STRENGTH.get(claim.kind, "supporting")
            graph.nodes.append(
                GraphNode(
                    id=paper_claim_id,
                    kind="claim",
                    label=claim.text[:80],
                    body=claim.text,
                    section="results",
                    strength=strength,
                )
            )
            existing_node_ids.add(paper_claim_id)
            added_claims.append(paper_claim_id)
        else:
            skipped_claims.append(paper_claim_id)

        if claim.figure_contract is None:
            continue
        figure_id = claim.figure_contract.figure_id
        ev_id = _paper_evidence_id(figure_id)
        if ev_id not in existing_node_ids:
            graph.nodes.append(
                GraphNode(
                    id=ev_id,
                    kind="evidence",
                    label=f"figure: {figure_id}",
                    body=claim.figure_contract.rationale,
                    source=EvidenceSource(kind="figure", ref=figure_id),
                )
            )
            existing_node_ids.add(ev_id)
            added_evidence.append(ev_id)
        edge_key: tuple[str, str, EdgeKind] = (ev_id, paper_claim_id, "supports")
        if edge_key not in existing_edges:
            graph.edges.append(GraphEdge(src=ev_id, dst=paper_claim_id, kind="supports"))
            existing_edges.add(edge_key)
            added_edges.append((ev_id, paper_claim_id))

    graph_state.save(workspace=workspace, graph=graph)
    refresh_artifact_ref(workspace=workspace, state=paper_state, artifact="evidence_graph")
    write_state(workspace=workspace, state=paper_state)

    # Reflect lift in synthesis brief, if one exists for this hypothesis.
    try:
        brief = read_brief(workspace=workspace, hypothesis_id=hypothesis_id)
    except SynthesisBriefNotFound:
        brief = None
    if brief is not None:
        touched = False
        for syn_claim in brief.claims:
            if syn_claim.claim_id in {c.claim_id for c in claims_file.claims}:
                expected = _paper_claim_id(syn_claim.claim_id)
                if syn_claim.lifted_to != expected or syn_claim.lifted_to_status != "lifted":
                    syn_claim.lifted_to = expected
                    syn_claim.lifted_to_status = "lifted"
                    touched = True
        if touched:
            write_brief(workspace=workspace, brief=brief)

    return LiftResult(
        added_claims=added_claims,
        added_evidence=added_evidence,
        added_edges=added_edges,
        skipped_claims=skipped_claims,
    )


__all__ = ["LiftResult", "WorkspaceNotInitialized", "lift_claims_to_evidence"]
