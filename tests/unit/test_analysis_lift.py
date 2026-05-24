"""Unit tests for the analysis→paper lift bridge."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from paper_toolkit.analysis import claims as claims_state
from paper_toolkit.analysis import lift
from paper_toolkit.analysis import state as state_io
from paper_toolkit.cli.main import app
from paper_toolkit.models.analysis import Claim, FigureContract
from paper_toolkit.state import evidence_graph as graph_state


def _init_paper_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--title", "Demo", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.stdout


def _seed(tmp_path: Path) -> None:
    db = tmp_path / "demo.db"
    db.touch()
    state_io.init_experiment(
        workspace=tmp_path,
        hypothesis_id="h",
        experiment_id="e",
        db_path=db,
        language="bilingual",
    )


def test_lift_adds_claim_and_evidence_nodes_when_contract_present(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed(tmp_path)
    claims_state.upsert_claim(
        workspace=tmp_path,
        hypothesis_id="h",
        experiment_id="e",
        claim=Claim(
            claim_id="growth",
            text="Engagement grows with treatment dose",
            kind="quantitative",
            evidence="dose_response_query",
            figure_contract=FigureContract(figure_id="fig_dose", rationale="line plot"),
        ),
    )
    result = lift.lift_claims_to_evidence(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    assert "claim_growth" in result.added_claims
    assert "ev_fig_dose" in result.added_evidence
    assert ("ev_fig_dose", "claim_growth") in result.added_edges

    graph = graph_state.load(workspace=tmp_path)
    node_ids = {n.id for n in graph.nodes}
    assert "claim_growth" in node_ids
    assert "ev_fig_dose" in node_ids
    assert any(
        e.src == "ev_fig_dose" and e.dst == "claim_growth" and e.kind == "supports"
        for e in graph.edges
    )


def test_lift_is_idempotent(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed(tmp_path)
    claims_state.upsert_claim(
        workspace=tmp_path,
        hypothesis_id="h",
        experiment_id="e",
        claim=Claim(
            claim_id="c1",
            text="x",
            kind="quantitative",
            evidence="q",
            figure_contract=FigureContract(figure_id="fig1", rationale="r"),
        ),
    )
    first = lift.lift_claims_to_evidence(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    second = lift.lift_claims_to_evidence(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    assert first.added_claims and not second.added_claims
    assert not second.added_evidence
    assert not second.added_edges


def test_lift_handles_claim_without_contract(tmp_path: Path) -> None:
    _init_paper_workspace(tmp_path)
    _seed(tmp_path)
    claims_state.upsert_claim(
        workspace=tmp_path,
        hypothesis_id="h",
        experiment_id="e",
        claim=Claim(claim_id="c1", text="t", kind="qualitative", evidence="q"),
    )
    result = lift.lift_claims_to_evidence(workspace=tmp_path, hypothesis_id="h", experiment_id="e")
    assert "claim_c1" in result.added_claims
    assert result.added_evidence == []
