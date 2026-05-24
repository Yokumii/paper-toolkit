from paper_toolkit.checkers.runner import run_all_checks
from paper_toolkit.models.evidence import EvidenceGraph, EvidenceSource, GraphEdge, GraphNode
from paper_toolkit.models.paper_state import FigureArtifact
from paper_toolkit.state import evidence_graph
from paper_toolkit.state.workspace import init_workspace, write_state


def test_run_all_checks_returns_merged_report(tmp_path) -> None:
    state = init_workspace(workspace=tmp_path, title="Demo", venue="nature", language="en")
    fig = tmp_path / "paper" / "figures" / "fig1.png"
    fig.parent.mkdir(parents=True, exist_ok=True)
    fig.write_text("fake", encoding="utf-8")
    state.artifacts.figures = [
        FigureArtifact(
            id="fig1",
            src=str(tmp_path / "source.png"),
            packed="paper/figures/fig1.png",
            caption=(
                "This caption has enough words to satisfy the lower bound for the "
                "configured Nature venue caption checker."
            ),
            referenced_by=["intro"],
        )
    ]
    write_state(workspace=tmp_path, state=state)
    sections = tmp_path / "paper" / "sections"
    sections.mkdir(parents=True, exist_ok=True)
    (sections / "intro.tex").write_text(
        "Text \\cite{smith2020}. See \\ref{fig:fig1}.\n", encoding="utf-8"
    )
    (tmp_path / "paper" / "refs.bib").write_text(
        "@misc{smith2020,\n  title={Smith}\n}\n", encoding="utf-8"
    )
    graph = EvidenceGraph(
        schema_version="1.0",
        nodes=[
            GraphNode(id="c1", kind="claim", label="Supported", section="intro"),
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

    report = run_all_checks(workspace=tmp_path, section="intro")

    assert report.checker == "all"
    assert set(report.result["checkers"]) == {
        "style",
        "citations",
        "figures",
        "figure-qa",
        "claim-coverage",
        "word-count",
        "logic-consistency",
    }
