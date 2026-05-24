from pathlib import Path

from paper_toolkit.paths import WorkspacePaths


def test_workspace_paths_resolves_under_workspace(tmp_path: Path) -> None:
    paths = WorkspacePaths(workspace=tmp_path)
    assert paths.workspace == tmp_path.resolve()
    assert paths.paper_dir == (tmp_path / "paper").resolve()
    assert paths.paper_state == (tmp_path / "paper" / "paper.json").resolve()
    assert paths.sections_dir == (tmp_path / "paper" / "sections").resolve()
    assert paths.figures_dir == (tmp_path / "paper" / "figures").resolve()
    assert paths.figure_specs_dir == (tmp_path / "paper" / "figure_specs").resolve()
    assert paths.tables_dir == (tmp_path / "paper" / "tables").resolve()
    assert paths.table_specs_dir == (tmp_path / "paper" / "table_specs").resolve()
    assert paths.lit_dir == (tmp_path / "paper" / "lit").resolve()
    assert paths.refs_bib == (tmp_path / "paper" / "refs.bib").resolve()
    assert paths.main_tex == (tmp_path / "paper" / "main.tex").resolve()
    assert paths.reviews_dir == (tmp_path / "paper" / "reviews").resolve()
    assert paths.compile_runs_dir == (tmp_path / "paper" / "compile_runs").resolve()
    assert paths.evidence_graph == (tmp_path / "paper" / "evidence_graph.json").resolve()
    assert paths.research_pack == (tmp_path / "paper" / "research_pack.json").resolve()
    assert paths.venue_yaml == (tmp_path / "paper" / "venue.yaml").resolve()


def test_workspace_paths_relative_to_helper(tmp_path: Path) -> None:
    paths = WorkspacePaths(workspace=tmp_path)
    abs_path = (tmp_path / "paper" / "sections" / "intro.tex").resolve()
    rel = paths.relative_to_workspace(abs_path)
    assert rel == "paper/sections/intro.tex"


def test_workspace_paths_compile_run_helpers(tmp_path: Path) -> None:
    paths = WorkspacePaths(workspace=tmp_path)
    run_dir = paths.compile_run_dir("r3")
    assert run_dir == (tmp_path / "paper" / "compile_runs" / "r3").resolve()
    assert paths.compile_run_json("r3") == (run_dir / "run.json").resolve()
    assert paths.compile_run_elements("r3") == (run_dir / "pages" / "elements.json").resolve()
