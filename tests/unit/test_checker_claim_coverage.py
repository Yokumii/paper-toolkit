from paper_toolkit.checkers.claim_coverage import check_claim_coverage
from paper_toolkit.models.evidence import EvidenceGraph, EvidenceSource, GraphEdge, GraphNode
from paper_toolkit.state import evidence_graph


def test_claim_coverage_wraps_evidence_validate(tmp_path) -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[GraphNode(id="c1", kind="claim", label="Unsupported", section="results")],
        edges=[],
    )
    evidence_graph.save(workspace=tmp_path, graph=graph)

    report = check_claim_coverage(workspace=tmp_path)

    assert report.ok is False
    assert report.issues[0].code == "EVD_UNSUPPORTED_CLAIM"


def test_claim_coverage_passes_supported_claim(tmp_path) -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(id="c1", kind="claim", label="Supported", section="results"),
            GraphNode(
                id="e1",
                kind="evidence",
                label="Evidence",
                source=EvidenceSource(kind="stat", ref="s1"),
            ),
        ],
        edges=[GraphEdge(src="e1", dst="c1", kind="supports")],
    )
    evidence_graph.save(workspace=tmp_path, graph=graph)

    report = check_claim_coverage(workspace=tmp_path)

    assert report.ok is True
    assert report.issues == []
