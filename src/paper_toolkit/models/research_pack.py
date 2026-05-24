"""Schemas for paper/research_pack.json.

The scanner records what source materials exist. It does not decide which
materials become claims, evidence, or citations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HypothesisEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    path: str
    text: str = ""
    experiments: list[str] = Field(default_factory=list)


class ReportEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    path: str
    title: str | None = None
    summary: str = ""


class CandidateFigure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    src: str
    suggested_id: str
    suggested_caption: str | None = None
    width_hint: float | None = None
    referenced_in_reports: list[str] = Field(default_factory=list)


class CandidateTable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    src: str
    suggested_id: str
    suggested_caption: str | None = None
    referenced_in_reports: list[str] = Field(default_factory=list)


class ReplayDbEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    experiment_id: str | None = None


class ResearchPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    workspace_root: str
    scanned_at: datetime
    hypotheses: list[HypothesisEntry] = Field(default_factory=list)
    analysis_reports: list[ReportEntry] = Field(default_factory=list)
    candidate_figures: list[CandidateFigure] = Field(default_factory=list)
    candidate_tables: list[CandidateTable] = Field(default_factory=list)
    replay_dbs: list[ReplayDbEntry] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
