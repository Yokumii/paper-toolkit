from datetime import UTC, datetime
from pathlib import Path

import pytest

from paper_toolkit.models.evidence import EvidenceGraph, EvidenceSource, GraphEdge, GraphNode
from paper_toolkit.models.paper_state import CompileRunRef
from paper_toolkit.models.research_pack import ResearchPack
from paper_toolkit.paths import WorkspacePaths
from paper_toolkit.state import evidence_graph, research_pack
from paper_toolkit.state.workspace import (
    WorkspaceAlreadyInitialized,
    WorkspaceNotInitialized,
    compute_state_summary,
    init_workspace,
    read_state,
    refresh_artifact_ref,
    write_state,
)


def test_init_workspace_creates_paper_json_and_dirs(tmp_workspace: Path) -> None:
    state = init_workspace(
        workspace=tmp_workspace,
        title="Demo",
        venue="nature",
        language="en",
    )
    paths = WorkspacePaths(workspace=tmp_workspace)
    assert paths.paper_dir.is_dir()
    assert paths.paper_state.is_file()
    assert paths.sections_dir.is_dir()
    assert paths.figures_dir.is_dir()
    assert paths.reviews_dir.is_dir()
    assert paths.compile_runs_dir.is_dir()
    assert state.meta.title == "Demo"
    assert state.meta.venue == "nature"
    assert state.meta.language == "en"
    assert state.meta.workspace_root == str(tmp_workspace.resolve())


def test_init_workspace_refuses_when_already_initialized(tmp_workspace: Path) -> None:
    init_workspace(workspace=tmp_workspace, title="Demo", venue="nature", language="en")
    with pytest.raises(WorkspaceAlreadyInitialized):
        init_workspace(workspace=tmp_workspace, title="Demo", venue="nature", language="en")


def test_read_state_after_init_roundtrips(tmp_workspace: Path) -> None:
    init_workspace(workspace=tmp_workspace, title="Demo", venue="nature", language="en")
    state = read_state(workspace=tmp_workspace)
    assert state.meta.title == "Demo"
    assert state.schema_version == "1.0"


def test_read_state_raises_when_not_initialized(tmp_workspace: Path) -> None:
    with pytest.raises(WorkspaceNotInitialized):
        read_state(workspace=tmp_workspace)


def test_write_state_persists_changes(tmp_workspace: Path) -> None:
    state = init_workspace(workspace=tmp_workspace, title="Demo", venue="nature", language="en")
    new_state = state.model_copy(
        update={"meta": state.meta.model_copy(update={"title": "Updated"})}
    )
    write_state(workspace=tmp_workspace, state=new_state)
    reloaded = read_state(workspace=tmp_workspace)
    assert reloaded.meta.title == "Updated"


def test_compute_state_summary_empty_workspace(tmp_workspace: Path) -> None:
    state = init_workspace(workspace=tmp_workspace, title="Demo", venue="nature", language="en")
    summary = compute_state_summary(workspace=tmp_workspace, state=state)
    assert summary.section_count == 0
    assert summary.claim_count == 0
    assert summary.evidence_count == 0
    assert summary.citation_count == 0
    assert summary.figure_count == 0
    assert summary.packed_figure_count == 0
    assert summary.graph_valid is True  # vacuous truth until graph exists
    assert summary.graph_issue_count == 0
    assert summary.last_compile is None
    assert summary.last_updated_artifact is None
    assert len(summary.paper_json_checksum) == 64


def _now() -> datetime:
    return datetime.now(UTC)


def test_refresh_artifact_ref_sets_research_pack_and_evidence_graph(tmp_workspace: Path) -> None:
    state = init_workspace(workspace=tmp_workspace, title="Demo", venue="nature", language="en")
    pack = ResearchPack(schema_version="1.0", workspace_root=str(tmp_workspace), scanned_at=_now())
    research_pack.save(workspace=tmp_workspace, pack=pack)
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
    evidence_graph.save(workspace=tmp_workspace, graph=graph)

    refresh_artifact_ref(workspace=tmp_workspace, state=state, artifact="research_pack")
    refresh_artifact_ref(workspace=tmp_workspace, state=state, artifact="evidence_graph")

    assert state.artifacts.research_pack is not None
    assert state.artifacts.research_pack.path == "paper/research_pack.json"
    assert state.artifacts.evidence_graph is not None
    assert state.artifacts.evidence_graph.path == "paper/evidence_graph.json"


def test_compute_state_summary_counts_evidence_graph(tmp_workspace: Path) -> None:
    state = init_workspace(workspace=tmp_workspace, title="Demo", venue="nature", language="en")
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
            GraphNode(id="ref1", kind="citation", label="Smith", cite_key="smith2020"),
        ],
        edges=[GraphEdge(src="e1", dst="c1", kind="supports")],
    )
    evidence_graph.save(workspace=tmp_workspace, graph=graph)
    write_state(workspace=tmp_workspace, state=state)

    summary = compute_state_summary(workspace=tmp_workspace, state=state)

    assert summary.claim_count == 1
    assert summary.evidence_count == 1
    assert summary.citation_count == 1
    assert summary.graph_valid is True
    assert summary.graph_issue_count == 0
    assert summary.last_updated_artifact == "paper/evidence_graph.json"


def test_refresh_artifact_ref_sets_bib_and_main_tex(tmp_workspace: Path) -> None:
    state = init_workspace(workspace=tmp_workspace, title="Demo", venue="nature", language="en")
    paths = WorkspacePaths(workspace=tmp_workspace)
    paths.refs_bib.write_text("@article{smith2020,\n  title = {Smith}\n}\n", encoding="utf-8")
    paths.main_tex.write_text(
        "\\documentclass{article}\\begin{document}Hi\\end{document}\n", encoding="utf-8"
    )

    refresh_artifact_ref(workspace=tmp_workspace, state=state, artifact="bib")
    refresh_artifact_ref(workspace=tmp_workspace, state=state, artifact="main_tex")

    assert state.artifacts.bib is not None
    assert state.artifacts.bib.path == "paper/refs.bib"
    assert state.artifacts.main_tex is not None
    assert state.artifacts.main_tex.path == "paper/main.tex"


def test_compute_state_summary_reports_last_compile(tmp_workspace: Path) -> None:
    state = init_workspace(workspace=tmp_workspace, title="Demo", venue="nature", language="en")
    ts = _now()
    state.artifacts.compile_runs.append(
        CompileRunRef(
            id="r1",
            ok=False,
            error_count=2,
            warning_count=1,
            pdf=None,
            started_at=ts,
            finished_at=ts,
        )
    )
    write_state(workspace=tmp_workspace, state=state)

    summary = compute_state_summary(workspace=tmp_workspace, state=state)

    assert summary.last_compile is not None
    assert summary.last_compile.id == "r1"
    assert summary.last_compile.ok is False
    assert summary.last_compile.error_count == 2
