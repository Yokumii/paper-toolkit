"""IO helpers for AnalysisPlan, AnalysisState, AnalysisConfig.

YAML is used for `analysis_plan.yaml`, `state.yaml`, `config.yaml`. JSON
goes through the existing `paper_toolkit.io.write_atomic_text` helper
elsewhere; YAML is written the same way (atomic temp + rename) so a crash
mid-write never truncates an artifact.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from paper_toolkit.io import write_atomic_text
from paper_toolkit.models.analysis import (
    AnalysisConfig,
    AnalysisPlan,
    AnalysisState,
    Language,
)
from paper_toolkit.paths import WorkspacePaths


class AnalysisPlanNotFound(FileNotFoundError):
    """Raised when analysis_plan.yaml is expected but missing."""


class AnalysisStateNotFound(FileNotFoundError):
    """Raised when state.yaml is expected but missing."""


class AnalysisConfigNotFound(FileNotFoundError):
    """Raised when config.yaml is expected but missing."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _dump_yaml(model: AnalysisPlan | AnalysisState | AnalysisConfig) -> str:
    return yaml.safe_dump(
        model.model_dump(mode="json"),
        sort_keys=True,
        allow_unicode=True,
    )


def write_state(
    *,
    workspace: Path,
    state: AnalysisState,
) -> None:
    paths = WorkspacePaths(workspace=workspace)
    out = paths.analysis_state(hypothesis_id=state.hypothesis_id, experiment_id=state.experiment_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(out, _dump_yaml(state))


def read_state(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> AnalysisState:
    paths = WorkspacePaths(workspace=workspace)
    path = paths.analysis_state(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    if not path.exists():
        raise AnalysisStateNotFound(str(path))
    return AnalysisState.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def write_config(
    *,
    workspace: Path,
    config: AnalysisConfig,
) -> None:
    paths = WorkspacePaths(workspace=workspace)
    out = paths.analysis_config(
        hypothesis_id=config.hypothesis_id, experiment_id=config.experiment_id
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(out, _dump_yaml(config))


def read_config(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> AnalysisConfig:
    paths = WorkspacePaths(workspace=workspace)
    path = paths.analysis_config(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    if not path.exists():
        raise AnalysisConfigNotFound(str(path))
    return AnalysisConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def write_plan(
    *,
    workspace: Path,
    plan: AnalysisPlan,
) -> None:
    paths = WorkspacePaths(workspace=workspace)
    out = paths.analysis_plan(hypothesis_id=plan.hypothesis_id, experiment_id=plan.experiment_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_text(out, _dump_yaml(plan))


def read_plan(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> AnalysisPlan:
    paths = WorkspacePaths(workspace=workspace)
    path = paths.analysis_plan(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    if not path.exists():
        raise AnalysisPlanNotFound(str(path))
    return AnalysisPlan.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def plan_exists(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
) -> bool:
    paths = WorkspacePaths(workspace=workspace)
    return paths.analysis_plan(hypothesis_id=hypothesis_id, experiment_id=experiment_id).exists()


def init_experiment(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
    db_path: Path,
    language: Language,
) -> tuple[AnalysisState, AnalysisConfig]:
    """Create the per-experiment tree + write fresh state.yaml and config.yaml."""
    paths = WorkspacePaths(workspace=workspace)
    base = paths.experiment_dir(hypothesis_id=hypothesis_id, experiment_id=experiment_id)
    base.mkdir(parents=True, exist_ok=True)
    (base / "eda").mkdir(parents=True, exist_ok=True)
    (base / "eda" / "queries").mkdir(parents=True, exist_ok=True)
    state = AnalysisState(
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
        db_path=str(db_path.resolve()),
        created_at=_utcnow(),
    )
    config = AnalysisConfig(
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
        language=language,
    )
    write_state(workspace=workspace, state=state)
    write_config(workspace=workspace, config=config)
    return state, config


def touch_state(
    *,
    workspace: Path,
    hypothesis_id: str,
    experiment_id: str,
    profiled_table: str | None = None,
    last_query_slug: str | None = None,
    claim_count: int | None = None,
) -> AnalysisState:
    """Update facts on the state file; never invents new fields."""
    state = read_state(
        workspace=workspace,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
    )
    if profiled_table is not None and profiled_table not in state.profiled_tables:
        state.profiled_tables = [*state.profiled_tables, profiled_table]
    if last_query_slug is not None:
        state.last_query_slug = last_query_slug
    if claim_count is not None:
        state.claim_count = claim_count
    state.last_updated = _utcnow()
    write_state(workspace=workspace, state=state)
    return state
