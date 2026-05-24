from paper_toolkit.checkers.logic_consistency import check_logic_consistency
from paper_toolkit.models.evidence import EvidenceGraph, GraphEdge, GraphNode
from paper_toolkit.state import evidence_graph


def test_logic_checker_reports_declared_contradiction_same_section(tmp_path) -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(id="c1", kind="claim", label="Policy increases trust", section="results"),
            GraphNode(id="c2", kind="claim", label="Policy decreases trust", section="results"),
        ],
        edges=[GraphEdge(src="c1", dst="c2", kind="contradicts")],
    )
    evidence_graph.save(workspace=tmp_path, graph=graph)

    report = check_logic_consistency(workspace=tmp_path)

    assert report.ok is False
    assert report.issues[0].code == "LOGIC_DECLARED_CONTRADICTION"


def test_logic_checker_warns_opposite_sign_heuristic(tmp_path) -> None:
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(
                id="c1",
                kind="claim",
                label="Intervention increases welfare",
                section="results",
            ),
            GraphNode(
                id="c2",
                kind="claim",
                label="Intervention decreases welfare",
                section="results",
            ),
        ],
    )
    evidence_graph.save(workspace=tmp_path, graph=graph)

    report = check_logic_consistency(workspace=tmp_path)

    assert report.ok is True
    assert report.issues[0].severity == "warning"
    assert report.issues[0].code == "LOGIC_OPPOSITE_SIGN_HEURISTIC"
