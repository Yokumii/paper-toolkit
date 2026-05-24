"""Response envelope returned by every CLI subcommand.

Contract: every CLI call prints exactly one `Envelope` as JSON to stdout
(or a short human-readable summary if `--human` was passed). On `ok=false`,
exit code is 1 but the envelope is still printed to stdout. Stderr is
reserved for crashes/unhandled exceptions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from paper_toolkit.models.paper_state import CompileSummary


class ErrorEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Stable machine code, e.g. EVD_DAG_CYCLE.")
    message: str
    location: str | None = None
    fixup_hint: str | None = None


class StateSummary(BaseModel):
    """Compact view of paper.json + derived counters. Returned in every envelope."""

    model_config = ConfigDict(extra="forbid")

    section_count: int = Field(..., ge=0)
    claim_count: int = Field(..., ge=0)
    evidence_count: int = Field(..., ge=0)
    citation_count: int = Field(..., ge=0)
    figure_count: int = Field(..., ge=0)
    packed_figure_count: int = Field(..., ge=0)
    graph_valid: bool
    graph_issue_count: int = Field(..., ge=0)
    last_compile: CompileSummary | None = None
    last_updated_artifact: str | None = None
    paper_json_checksum: str = Field(..., min_length=64, max_length=64)


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    action: str
    result: dict[str, Any] = Field(default_factory=dict)
    state_summary: StateSummary
    errors: list[ErrorEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def build_envelope(
    *,
    action: str,
    result: dict[str, Any],
    state_summary: StateSummary,
    errors: list[ErrorEntry] | None = None,
    warnings: list[str] | None = None,
) -> Envelope:
    """Construct an envelope. `ok` is auto-derived: false iff any errors."""
    errs = list(errors or [])
    return Envelope(
        ok=len(errs) == 0,
        action=action,
        result=result,
        state_summary=state_summary,
        errors=errs,
        warnings=list(warnings or []),
    )
