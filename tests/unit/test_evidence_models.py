import pytest
from pydantic import ValidationError

from paper_toolkit.models.evidence import EvidenceGraph, EvidenceSource, GraphEdge, GraphNode


def test_evidence_graph_roundtrip() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(
                id="c1",
                kind="claim",
                label="Heterogeneity improves adaptation.",
                body="Detailed claim text.",
                section="results",
                strength="primary",
            ),
            GraphNode(
                id="e1",
                kind="evidence",
                label="Figure 1 adaptation gap.",
                source=EvidenceSource(kind="figure", ref="fig1", detail="delta=0.08"),
            ),
            GraphNode(id="ref1", kind="citation", label="Smith 2020", cite_key="smith2020"),
        ],
        edges=[
            GraphEdge(src="e1", dst="c1", kind="supports"),
            GraphEdge(src="c1", dst="ref1", kind="cites"),
        ],
    )
    restored = EvidenceGraph.model_validate(graph.model_dump(mode="json"))
    assert restored == graph
    assert restored.nodes[1].source is not None
    assert restored.edges[0].kind == "supports"


def test_graph_node_rejects_bad_kind() -> None:
    with pytest.raises(ValidationError):
        GraphNode(id="x", kind="note", label="Bad")  # type: ignore[arg-type]


def test_edge_rejects_bad_kind() -> None:
    with pytest.raises(ValidationError):
        GraphEdge(src="a", dst="b", kind="relates")  # type: ignore[arg-type]
