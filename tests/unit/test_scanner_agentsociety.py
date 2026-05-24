from pathlib import Path

from paper_toolkit.scanner.agentsociety import AgentSocietyScanner

FIXTURE = Path(__file__).parents[1] / "fixtures" / "as_workspace"


def test_agentsociety_scanner_finds_hypotheses() -> None:
    pack = AgentSocietyScanner().scan(FIXTURE)
    assert pack.workspace_root == str(FIXTURE.resolve())
    assert len(pack.hypotheses) == 1
    assert pack.hypotheses[0].id == "hypothesis_1"
    assert "5%" in pack.hypotheses[0].text
    assert pack.hypotheses[0].experiments == ["experiment_1"]


def test_agentsociety_scanner_finds_reports_figures_tables_and_replay_dbs() -> None:
    pack = AgentSocietyScanner().scan(FIXTURE)
    assert [r.id for r in pack.analysis_reports] == ["report_hypothesis_1"]
    assert pack.analysis_reports[0].title == "Hypothesis 1 Report"
    assert "heterogeneous condition" in pack.analysis_reports[0].summary
    assert [f.suggested_id for f in pack.candidate_figures] == ["fig1"]
    assert pack.candidate_figures[0].referenced_in_reports == ["report_hypothesis_1"]
    assert [t.suggested_id for t in pack.candidate_tables] == ["tab1"]
    assert [db.experiment_id for db in pack.replay_dbs] == ["experiment_1"]


def test_agentsociety_scanner_handles_empty_workspace(tmp_path: Path) -> None:
    pack = AgentSocietyScanner().scan(tmp_path)
    assert pack.hypotheses == []
    assert pack.analysis_reports == []
    assert pack.candidate_figures == []
    assert "No hypothesis_* directories found." in pack.notes
