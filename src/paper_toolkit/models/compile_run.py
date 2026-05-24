"""Schemas for paper/compile_runs/rN/run.json."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LatexIssueCode = Literal[
    "missing-citation",
    "undefined-ref",
    "overfull-hbox",
    "underfull-vbox",
    "missing-file",
    "syntax",
    "package",
    "missing-engine",
    "other",
]

PageElementKind = Literal["figure", "table", "equation", "heading", "paragraph_start", "caption"]


class LatexError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: LatexIssueCode
    message: str
    file: str | None = None
    line: int | None = None
    fixup_hint: str | None = None


class LatexWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: LatexIssueCode
    message: str
    file: str | None = None
    line: int | None = None


class PageElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: PageElementKind
    label: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    text_preview: str | None = None
    overflow: bool = False


class PageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(..., ge=1)
    png_path: str
    elements: list[PageElement] = Field(default_factory=list)


class CompileRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    ok: bool
    pdf_path: str | None
    log_path: str
    errors: list[LatexError] = Field(default_factory=list)
    warnings: list[LatexWarning] = Field(default_factory=list)
    pages: list[PageInfo] = Field(default_factory=list)
    attempt_index: int = Field(..., ge=1)
    duration_seconds: float = Field(..., ge=0)
