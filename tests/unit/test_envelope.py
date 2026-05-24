from datetime import UTC, datetime

from paper_toolkit.envelope import (
    Envelope,
    ErrorEntry,
    StateSummary,
    build_envelope,
)
from paper_toolkit.models.paper_state import CompileSummary


def _summary() -> StateSummary:
    return StateSummary(
        section_count=0,
        claim_count=0,
        evidence_count=0,
        citation_count=0,
        figure_count=0,
        packed_figure_count=0,
        graph_valid=True,
        graph_issue_count=0,
        last_compile=None,
        last_updated_artifact=None,
        paper_json_checksum="0" * 64,
    )


def test_envelope_minimal_serializes() -> None:
    env = build_envelope(action="status", result={"hello": "world"}, state_summary=_summary())
    assert env.ok is True
    assert env.action == "status"
    assert env.result == {"hello": "world"}
    assert env.errors == []
    assert env.warnings == []
    data = env.model_dump(mode="json")
    restored = Envelope.model_validate(data)
    assert restored == env


def test_envelope_with_errors_sets_ok_false() -> None:
    env = build_envelope(
        action="init",
        result={},
        state_summary=_summary(),
        errors=[ErrorEntry(code="WS_ALREADY_INITIALIZED", message="paper.json exists")],
    )
    assert env.ok is False
    assert env.errors[0].code == "WS_ALREADY_INITIALIZED"


def test_envelope_explicit_ok_true_with_warnings_only() -> None:
    env = build_envelope(
        action="compile-once",
        result={},
        state_summary=_summary(),
        warnings=["max-attempts exceeded; CC should consider stopping"],
    )
    assert env.ok is True
    assert env.warnings == ["max-attempts exceeded; CC should consider stopping"]


def test_state_summary_with_compile() -> None:
    summary = StateSummary(
        section_count=2,
        claim_count=5,
        evidence_count=4,
        citation_count=3,
        figure_count=2,
        packed_figure_count=2,
        graph_valid=True,
        graph_issue_count=0,
        last_compile=CompileSummary(
            id="r2",
            ok=False,
            error_count=2,
            ts=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        ),
        last_updated_artifact="evidence_graph",
        paper_json_checksum="a" * 64,
    )
    data = summary.model_dump(mode="json")
    restored = StateSummary.model_validate(data)
    assert restored == summary
