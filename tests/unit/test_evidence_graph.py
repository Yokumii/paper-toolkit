from pathlib import Path

from paper_toolkit.models.evidence import EvidenceGraph, EvidenceSource, GraphEdge, GraphNode
from paper_toolkit.state import evidence_graph

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_save_load_and_exists(tmp_path: Path) -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[GraphNode(id="c1", kind="claim", label="Claim", section="results")],
        edges=[],
    )
    assert evidence_graph.exists(workspace=tmp_path) is False
    evidence_graph.save(workspace=tmp_path, graph=graph)
    assert evidence_graph.exists(workspace=tmp_path) is True
    loaded = evidence_graph.load(workspace=tmp_path)
    assert loaded.nodes[0].id == "c1"


def test_load_returns_empty_graph_when_missing(tmp_path: Path) -> None:
    graph = evidence_graph.load_or_empty(workspace=tmp_path)
    assert graph.schema_version == "1.0"
    assert graph.nodes == []
    assert graph.edges == []


def test_validate_accepts_supported_claim() -> None:
    graph = EvidenceGraph.model_validate_json((FIXTURES / "evidence_graph_valid.json").read_text())
    errors, warnings = evidence_graph.validate_graph(graph=graph, refs_bib_text=None)
    assert errors == []
    assert warnings == []


def test_validate_reports_unsupported_claim() -> None:
    graph = EvidenceGraph.model_validate_json((FIXTURES / "evidence_graph_orphan.json").read_text())
    errors, warnings = evidence_graph.validate_graph(graph=graph, refs_bib_text=None)
    assert warnings == []
    assert [e.code for e in errors] == ["EVD_UNSUPPORTED_CLAIM"]
    assert errors[0].location == "node:c1"


def test_validate_reports_duplicate_node_and_missing_edge_endpoint() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(id="c1", kind="claim", label="Claim"),
            GraphNode(id="c1", kind="claim", label="Duplicate"),
        ],
        edges=[GraphEdge(src="e404", dst="c1", kind="supports")],
    )
    errors, _ = evidence_graph.validate_graph(graph=graph, refs_bib_text=None)
    assert {e.code for e in errors} == {
        "EVD_DUPLICATE_NODE",
        "EVD_EDGE_MISSING_SRC",
        "EVD_UNSUPPORTED_CLAIM",
    }


def test_validate_reports_derives_from_cycle() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(id="c1", kind="claim", label="Claim 1"),
            GraphNode(id="c2", kind="claim", label="Claim 2"),
        ],
        edges=[
            GraphEdge(src="c1", dst="c2", kind="derives_from"),
            GraphEdge(src="c2", dst="c1", kind="derives_from"),
        ],
    )
    errors, _ = evidence_graph.validate_graph(graph=graph, refs_bib_text=None)
    assert "EVD_DERIVES_CYCLE" in {e.code for e in errors}


def test_validate_citation_with_missing_refs_bib_is_warning() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[GraphNode(id="ref1", kind="citation", label="Smith", cite_key="smith2020")],
        edges=[],
    )
    errors, warnings = evidence_graph.validate_graph(graph=graph, refs_bib_text=None)
    assert errors == []
    assert warnings == ["refs.bib is missing; citation resolvability deferred."]


def test_validate_citation_missing_from_refs_bib_is_error() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[GraphNode(id="ref1", kind="citation", label="Smith", cite_key="smith2020")],
        edges=[],
    )
    errors, warnings = evidence_graph.validate_graph(
        graph=graph, refs_bib_text="@article{doe2020,\n}"
    )
    assert warnings == []
    assert [e.code for e in errors] == ["EVD_CITATION_MISSING"]


def test_topo_order_puts_derived_claim_after_base_claim() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(id="c1", kind="claim", label="Base", section="intro"),
            GraphNode(id="c2", kind="claim", label="Derived", section="results"),
            GraphNode(
                id="e1",
                kind="evidence",
                label="Evidence",
                source=EvidenceSource(kind="stat", ref="s1"),
            ),
        ],
        edges=[
            GraphEdge(src="e1", dst="c1", kind="supports"),
            GraphEdge(src="c2", dst="c1", kind="derives_from"),
        ],
    )
    assert evidence_graph.topo_order(graph=graph) == ["c1", "c2"]


def test_render_mermaid_contains_nodes_and_edges() -> None:
    graph = EvidenceGraph.model_validate_json((FIXTURES / "evidence_graph_valid.json").read_text())
    mermaid = evidence_graph.render_mermaid(graph=graph)
    assert "graph TD" in mermaid
    assert 'c1["claim: Heterogeneity improves adaptation."]' in mermaid
    assert "e1 -->|supports| c1" in mermaid


def test_add_node_rejects_duplicate_id() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[GraphNode(id="c1", kind="claim", label="Claim")],
    )
    updated, error = evidence_graph.add_node(
        graph=graph, node=GraphNode(id="c1", kind="claim", label="Again")
    )
    assert updated == graph
    assert error is not None
    assert error.code == "EVD_NODE_EXISTS"


def test_add_edge_rejects_duplicate_edge() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(id="c1", kind="claim", label="Claim"),
            GraphNode(
                id="e1",
                kind="evidence",
                label="Evidence",
                source=EvidenceSource(kind="stat", ref="s1"),
            ),
        ],
        edges=[GraphEdge(src="e1", dst="c1", kind="supports")],
    )
    updated, error = evidence_graph.add_edge(
        graph=graph, edge=GraphEdge(src="e1", dst="c1", kind="supports")
    )
    assert updated == graph
    assert error is not None
    assert error.code == "EVD_EDGE_EXISTS"


def test_remove_node_removes_attached_edges() -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(id="c1", kind="claim", label="Claim"),
            GraphNode(
                id="e1",
                kind="evidence",
                label="Evidence",
                source=EvidenceSource(kind="stat", ref="s1"),
            ),
        ],
        edges=[GraphEdge(src="e1", dst="c1", kind="supports")],
    )
    updated, removed = evidence_graph.remove_node(graph=graph, node_id="e1")
    assert removed is True
    assert [node.id for node in updated.nodes] == ["c1"]
    assert updated.edges == []


def test_remove_edge_reports_missing_edge() -> None:
    graph = EvidenceGraph(schema_version="1.0")
    updated, removed = evidence_graph.remove_edge(graph=graph, src="e1", dst="c1", kind="supports")
    assert updated == graph
    assert removed is False
