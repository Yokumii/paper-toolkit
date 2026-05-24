"""Unit tests for paper_toolkit.analysis.checkers."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.analysis import checkers
from paper_toolkit.analysis import claims as claims_state
from paper_toolkit.analysis import state as state_io
from paper_toolkit.cli.main import app
from paper_toolkit.models.analysis import AnalysisPlan, Claim


def _init_paper_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["init", "--title", "Demo", "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout


def _seed_experiment(tmp_path: Path) -> None:
    db = tmp_path / "demo.db"
    db.touch()
    state_io.init_experiment(
        workspace=tmp_path,
        hypothesis_id="h",
        experiment_id="e",
        db_path=db,
        language="bilingual",
    )


def _write_plan(tmp_path: Path, must_inspect: list[str], expected: int = 1) -> None:
    plan = AnalysisPlan(
        hypothesis_id="h",
        experiment_id="e",
        research_question="?",
        must_inspect=must_inspect,
        expected_claim_count=expected,
    )
    state_io.write_plan(workspace=tmp_path, plan=plan)


def test_check_plan_missing(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed_experiment(tmp_path)
    errors, _ = checkers.check_plan(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    assert any(e.code == "ANL_PLAN_MISSING" for e in errors)


def test_check_explore_missing_profile(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed_experiment(tmp_path)
    _write_plan(tmp_path, must_inspect=["agent_profile"])
    errors, _ = checkers.check_explore(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    assert any(e.code == "ANL_EDA_TABLE_MISSING" for e in errors)


def test_check_explore_passes_when_profile_present(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed_experiment(tmp_path)
    _write_plan(tmp_path, must_inspect=["agent_profile"])
    eda = tmp_path / "analysis" / "h" / "e" / "eda"
    eda.mkdir(parents=True, exist_ok=True)
    (eda / "agent_profile_profile.json").write_text("{}", encoding="utf-8")
    errors, _ = checkers.check_explore(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    assert errors == []


def test_check_claims_flags_empty(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed_experiment(tmp_path)
    claims_state.write_claims(
        workspace=tmp_path,
        claims_file=claims_state.ClaimsFile(hypothesis_id="h", experiment_id="e"),
    )
    errors, _ = checkers.check_claims(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    assert any(e.code == "ANL_CLAIMS_EMPTY" for e in errors)


def test_check_claims_passes_when_present(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed_experiment(tmp_path)
    _write_plan(tmp_path, must_inspect=["x"])
    claims_state.upsert_claim(
        workspace=tmp_path,
        hypothesis_id="h",
        experiment_id="e",
        claim=Claim(claim_id="c1", text="t", kind="quantitative", evidence="ev"),
    )
    errors, _ = checkers.check_claims(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    assert errors == []


def test_check_refine_flags_missing_contract_and_pdf(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed_experiment(tmp_path)
    claims_state.upsert_claim(
        workspace=tmp_path,
        hypothesis_id="h",
        experiment_id="e",
        claim=Claim(claim_id="c1", text="t", kind="quantitative", evidence="ev"),
    )
    errors, _ = checkers.check_refine(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    assert any(e.code == "ANL_REFINE_NO_CONTRACT" for e in errors)


def test_check_release_demands_bilingual_files(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed_experiment(tmp_path)
    errors, _ = checkers.check_release(
        workspace=tmp_path, hypothesis_id="h", experiment_id="e", language="bilingual"
    )
    codes = {e.code for e in errors}
    assert "ANL_REPORT_MISSING" in codes


def test_check_release_passes_when_both_languages_present(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed_experiment(tmp_path)
    base = tmp_path / "analysis" / "h" / "e"
    (base / "report_zh.md").write_text("zh\n", encoding="utf-8")
    (base / "report_en.md").write_text("en\n", encoding="utf-8")
    errors, _ = checkers.check_release(
        workspace=tmp_path, hypothesis_id="h", experiment_id="e", language="bilingual"
    )
    assert errors == []
