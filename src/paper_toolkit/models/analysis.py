"""Pydantic models for the analysis pipeline.

`AnalysisPlan` is the Frame-stage artifact (research question + the tables
the Explore stage must profile). `ClaimsFile` is the canonical Claims +
Refine record per experiment. `SynthesisBrief` aggregates across
experiments under a single hypothesis.

All models use `extra="forbid"` so typos fail loud rather than silently
losing fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ClaimKind = Literal["quantitative", "qualitative", "comparative"]
Language = Literal["en", "zh", "bilingual"]
LiftStatus = Literal["pending", "lifted", "deferred"]


class AnalysisConfig(BaseModel):
    """`analysis/<H>/<E>/config.yaml`: per-experiment static config."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str = Field(..., min_length=1)
    experiment_id: str = Field(..., min_length=1)
    language: Language = "bilingual"


class AnalysisState(BaseModel):
    """`analysis/<H>/<E>/state.yaml`: FACTS ONLY (mirrors paper_state.py)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    hypothesis_id: str
    experiment_id: str
    db_path: str = Field(..., description="Absolute path to the experiment's sqlite.db.")
    created_at: datetime
    last_updated: datetime | None = None
    profiled_tables: list[str] = Field(default_factory=list)
    last_query_slug: str | None = None
    claim_count: int = Field(default=0, ge=0)


class AnalysisPlan(BaseModel):
    """`analysis/<H>/<E>/analysis_plan.yaml`: the Frame-stage contract."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    hypothesis_id: str = Field(..., min_length=1)
    experiment_id: str = Field(..., min_length=1)
    research_question: str = Field(..., min_length=1)
    must_inspect: list[str] = Field(
        ...,
        min_length=1,
        description="Table names the Explore stage must produce profiles for.",
    )
    expected_claim_count: int = Field(..., ge=1)
    notes: str | None = None


class FigureContract(BaseModel):
    """Binding from a Claim to a figure spec authored under `paper/figure_specs/`."""

    model_config = ConfigDict(extra="forbid")

    figure_id: str = Field(..., pattern=r"^[A-Za-z0-9_-]+$")
    rationale: str = Field(..., min_length=1)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    text: str = Field(..., min_length=1)
    kind: ClaimKind
    evidence: str = Field(
        ...,
        min_length=1,
        description="Which query slug or profile-table key supports this claim.",
    )
    figure_contract: FigureContract | None = None


class ClaimsFile(BaseModel):
    """`analysis/<H>/<E>/claims.json`."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    hypothesis_id: str
    experiment_id: str
    claims: list[Claim] = Field(default_factory=list)


class SynthesisClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    text: str = Field(..., min_length=1)
    source_experiments: list[str] = Field(..., min_length=1)
    lifted_to: str | None = Field(
        default=None,
        description="If set, the paper-side claim node id this synthesis claim was lifted to.",
    )
    lifted_to_status: LiftStatus = "pending"


class SynthesisBrief(BaseModel):
    """`analysis/synthesis/synthesis_brief.json`."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    hypothesis_id: str
    experiments: list[str] = Field(..., min_length=1)
    claims: list[SynthesisClaim] = Field(default_factory=list)
