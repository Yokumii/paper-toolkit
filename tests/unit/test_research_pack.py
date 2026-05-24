from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from paper_toolkit.models.research_pack import (
    CandidateFigure,
    CandidateTable,
    HypothesisEntry,
    ReplayDbEntry,
    ReportEntry,
    ResearchPack,
)
from paper_toolkit.state import research_pack


def _now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _sample_pack(tmp_path: Path) -> ResearchPack:
    return ResearchPack(
        schema_version="1.0",
        workspace_root=str(tmp_path),
        scanned_at=_now(),
        hypotheses=[
            HypothesisEntry(
                id="hypothesis_1",
                path=str(tmp_path / "hypothesis_1" / "HYPOTHESIS.md"),
                text="Agent heterogeneity increases adaptation.",
                experiments=["experiment_1"],
            )
        ],
        analysis_reports=[
            ReportEntry(
                id="report_hypothesis_1",
                path=str(tmp_path / "presentation" / "hypothesis_1" / "report.md"),
                title="Hypothesis 1 report",
                summary="Observed improved adaptation.",
            )
        ],
        candidate_figures=[
            CandidateFigure(
                src=str(tmp_path / "presentation" / "hypothesis_1" / "assets" / "figure_alpha.png"),
                suggested_id="fig1",
                suggested_caption="Figure alpha.",
                width_hint=None,
                referenced_in_reports=["report_hypothesis_1"],
            )
        ],
        candidate_tables=[
            CandidateTable(
                src=str(tmp_path / "presentation" / "hypothesis_1" / "data" / "table.csv"),
                suggested_id="tab1",
                suggested_caption="Table one.",
                referenced_in_reports=["report_hypothesis_1"],
            )
        ],
        replay_dbs=[
            ReplayDbEntry(
                path=str(tmp_path / "hypothesis_1" / "experiment_1" / "run" / "replay.sqlite"),
                experiment_id="experiment_1",
            )
        ],
        notes=["sample note"],
    )


def test_research_pack_roundtrip(tmp_path: Path) -> None:
    pack = _sample_pack(tmp_path)
    data = pack.model_dump(mode="json")
    restored = ResearchPack.model_validate(data)
    assert restored == pack
    assert restored.hypotheses[0].experiments == ["experiment_1"]
    assert restored.candidate_figures[0].suggested_id == "fig1"


def test_research_pack_rejects_bad_schema_version(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        ResearchPack(
            schema_version="2.0",  # type: ignore[arg-type]
            workspace_root=str(tmp_path),
            scanned_at=_now(),
        )


def test_save_load_exists_and_low_signal_notes(tmp_path: Path) -> None:
    pack = _sample_pack(tmp_path)
    assert research_pack.exists(workspace=tmp_path) is False
    research_pack.save(workspace=tmp_path, pack=pack)
    assert research_pack.exists(workspace=tmp_path) is True
    loaded = research_pack.load(workspace=tmp_path)
    assert loaded.hypotheses[0].id == "hypothesis_1"
    assert loaded.notes == ["sample note"]


def test_load_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        research_pack.load(workspace=tmp_path)
