"""Pydantic models for paper.json — the artifact registry.

`PaperState` records FACTS ONLY (what artifacts exist, when they were updated).
No phase machine, no judgment fields (no `current_phase`, `review_passed`, etc.).
All judgments are Claude Code's.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Language = Literal["en", "zh", "bilingual"]
ClaimStrength = Literal["primary", "supporting", "minor"]


class ArtifactRef(BaseModel):
    """Reference to a workspace-relative artifact file."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Workspace-relative path, e.g. 'paper/sections/intro.tex'.")
    updated_at: datetime
    checksum: str = Field(..., min_length=64, max_length=64, description="sha256 hex.")


class FigureArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Stable id like 'fig1'.")
    src: str = Field(..., description="Absolute or workspace-relative source path.")
    packed: str = Field(..., description="Workspace-relative path under paper/figures/.")
    caption: str | None = None
    referenced_by: list[str] = Field(default_factory=list, description="Section names citing this.")


class CompileRunRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Sequential id: r1, r2, ...")
    ok: bool
    error_count: int = Field(..., ge=0)
    warning_count: int = Field(..., ge=0)
    pdf: str | None = None
    started_at: datetime
    finished_at: datetime


class Artifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_pack: ArtifactRef | None = None
    evidence_graph: ArtifactRef | None = None
    sections: dict[str, ArtifactRef] = Field(default_factory=dict)
    figures: list[FigureArtifact] = Field(default_factory=list)
    bib: ArtifactRef | None = None
    main_tex: ArtifactRef | None = None
    compile_runs: list[CompileRunRef] = Field(default_factory=list)


class PaperMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1)
    venue: str = Field(..., min_length=1)
    language: Language
    created_at: datetime
    workspace_root: str = Field(..., description="Absolute path at init time.")


class PaperState(BaseModel):
    """Top-level `paper.json` contents."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    meta: PaperMeta
    artifacts: Artifacts


class CompileSummary(BaseModel):
    """Compact compile-run summary used in StateSummary (defined in envelope.py)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    ok: bool
    error_count: int
    ts: datetime
