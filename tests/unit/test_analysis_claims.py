"""Unit tests for paper_toolkit.analysis.claims IO."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from paper_toolkit.analysis import claims as claims_state
from paper_toolkit.models.analysis import Claim, FigureContract


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    return tmp_path


def _claim(claim_id: str = "c1") -> Claim:
    return Claim(
        claim_id=claim_id,
        text="Some claim text",
        kind="quantitative",
        evidence="agent_profile_profile",
    )


def test_upsert_claim_creates_file_when_missing(workspace: Path) -> None:
    claims = claims_state.upsert_claim(
        workspace=workspace,
        hypothesis_id="h",
        experiment_id="e",
        claim=_claim(),
    )
    assert len(claims.claims) == 1
    assert (workspace / "analysis" / "h" / "e" / "claims.json").exists()


def test_upsert_claim_replaces_in_place_when_id_matches(workspace: Path) -> None:
    claims_state.upsert_claim(
        workspace=workspace, hypothesis_id="h", experiment_id="e", claim=_claim("c1")
    )
    refreshed = _claim("c1")
    refreshed.text = "Updated text"
    claims = claims_state.upsert_claim(
        workspace=workspace, hypothesis_id="h", experiment_id="e", claim=refreshed
    )
    assert len(claims.claims) == 1
    assert claims.claims[0].text == "Updated text"


def test_attach_figure_contract_binds_existing_claim(workspace: Path) -> None:
    claims_state.upsert_claim(
        workspace=workspace, hypothesis_id="h", experiment_id="e", claim=_claim("c1")
    )
    claims = claims_state.attach_figure_contract(
        workspace=workspace,
        hypothesis_id="h",
        experiment_id="e",
        claim_id="c1",
        figure_id="fig1",
        rationale="bar chart compares arms",
    )
    assert claims.claims[0].figure_contract == FigureContract(
        figure_id="fig1", rationale="bar chart compares arms"
    )


def test_attach_figure_contract_raises_when_claim_missing(workspace: Path) -> None:
    claims_state.upsert_claim(
        workspace=workspace, hypothesis_id="h", experiment_id="e", claim=_claim("c1")
    )
    with pytest.raises(ValueError):
        claims_state.attach_figure_contract(
            workspace=workspace,
            hypothesis_id="h",
            experiment_id="e",
            claim_id="missing",
            figure_id="figX",
            rationale="...",
        )


def test_load_or_empty_returns_empty_when_no_file(workspace: Path) -> None:
    claims = claims_state.load_or_empty(workspace=workspace, hypothesis_id="h", experiment_id="e")
    assert claims.claims == []


def test_claim_id_must_match_pattern() -> None:
    with pytest.raises(ValidationError):
        Claim(
            claim_id="C1-with-dash",  # uppercase + dash both invalid
            text="x",
            kind="quantitative",
            evidence="x",
        )
