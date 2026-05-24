"""Unit tests for the analysis state / config / plan IO module."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from paper_toolkit.analysis import state as state_io
from paper_toolkit.models.analysis import (
    AnalysisConfig,
    AnalysisPlan,
    AnalysisState,
)


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    return tmp_path


def test_init_experiment_creates_tree_and_files(workspace: Path) -> None:
    db_path = workspace / "demo.db"
    db_path.touch()
    state, config = state_io.init_experiment(
        workspace=workspace,
        hypothesis_id="h1",
        experiment_id="e1",
        db_path=db_path,
        language="bilingual",
    )
    assert state.hypothesis_id == "h1"
    assert config.language == "bilingual"
    assert (workspace / "analysis" / "h1" / "e1" / "state.yaml").exists()
    assert (workspace / "analysis" / "h1" / "e1" / "config.yaml").exists()
    assert (workspace / "analysis" / "h1" / "e1" / "eda" / "queries").is_dir()


def test_state_round_trip(workspace: Path) -> None:
    db_path = workspace / "demo.db"
    db_path.touch()
    state_io.init_experiment(
        workspace=workspace,
        hypothesis_id="h1",
        experiment_id="e1",
        db_path=db_path,
        language="en",
    )
    state_io.touch_state(
        workspace=workspace,
        hypothesis_id="h1",
        experiment_id="e1",
        profiled_table="agent_profile",
        claim_count=3,
    )
    state = state_io.read_state(workspace=workspace, hypothesis_id="h1", experiment_id="e1")
    assert "agent_profile" in state.profiled_tables
    assert state.claim_count == 3
    assert state.last_updated is not None


def test_state_file_rejects_extra_keys(workspace: Path) -> None:
    db_path = workspace / "demo.db"
    db_path.touch()
    state = AnalysisState(
        hypothesis_id="h1",
        experiment_id="e1",
        db_path=str(db_path),
        created_at=datetime.now(UTC),
    )
    state_io.write_state(workspace=workspace, state=state)
    # Tamper with the file to add an extra key, then re-read should raise.
    path = workspace / "analysis" / "h1" / "e1" / "state.yaml"
    path.write_text(path.read_text() + "phantom_field: bad\n", encoding="utf-8")
    with pytest.raises(ValueError):
        state_io.read_state(workspace=workspace, hypothesis_id="h1", experiment_id="e1")


def test_plan_round_trip(workspace: Path) -> None:
    db_path = workspace / "demo.db"
    db_path.touch()
    state_io.init_experiment(
        workspace=workspace,
        hypothesis_id="h1",
        experiment_id="e1",
        db_path=db_path,
        language="bilingual",
    )
    plan = AnalysisPlan(
        hypothesis_id="h1",
        experiment_id="e1",
        research_question="Does X affect Y?",
        must_inspect=["agent_profile"],
        expected_claim_count=2,
    )
    state_io.write_plan(workspace=workspace, plan=plan)
    loaded = state_io.read_plan(workspace=workspace, hypothesis_id="h1", experiment_id="e1")
    assert loaded == plan


def test_read_plan_raises_when_missing(workspace: Path) -> None:
    with pytest.raises(state_io.AnalysisPlanNotFound):
        state_io.read_plan(workspace=workspace, hypothesis_id="h", experiment_id="e")


def test_config_round_trip(workspace: Path) -> None:
    db_path = workspace / "demo.db"
    db_path.touch()
    state_io.init_experiment(
        workspace=workspace,
        hypothesis_id="h1",
        experiment_id="e1",
        db_path=db_path,
        language="zh",
    )
    cfg = state_io.read_config(workspace=workspace, hypothesis_id="h1", experiment_id="e1")
    assert cfg == AnalysisConfig(hypothesis_id="h1", experiment_id="e1", language="zh")
