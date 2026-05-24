"""Schemas for paper/evidence_graph.json."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NodeKind = Literal["claim", "evidence", "citation"]
EvidenceSourceKind = Literal["figure", "table", "stat", "qual", "external"]
ClaimStrength = Literal["primary", "supporting", "minor"]
EdgeKind = Literal["supports", "derives_from", "cites", "contradicts"]
CitationEntryType = Literal[
    "article",
    "inproceedings",
    "incollection",
    "book",
    "techreport",
    "phdthesis",
    "mastersthesis",
    "unpublished",
    "misc",
]

# BibTeX key shape: starts with a letter, then letters/digits/_/-/:.  Mirrors
# EasyPaper typesetter_helpers extraction rule. Used to reject LLM placeholders.
_CITE_KEY_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-:]*$")
_PLACEHOLDER_CITE_KEYS: frozenset[str] = frozenset({"ref_id", "id", "key", "citation", "reference"})


class EvidenceSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EvidenceSourceKind
    ref: str
    detail: str | None = None


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    kind: NodeKind
    label: str = Field(..., min_length=1)
    body: str | None = None
    section: str | None = None
    strength: ClaimStrength | None = None
    source: EvidenceSource | None = None
    cite_key: str | None = None
    # Citation-only fields (all optional; bib_writer falls back to @misc if
    # entry_type is None and downgrades fields it cannot fill).
    entry_type: CitationEntryType | None = None
    authors: str | None = None
    year: str | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None

    @model_validator(mode="after")
    def validate_kind_fields(self) -> GraphNode:
        if self.kind == "evidence" and self.source is None:
            raise ValueError("evidence nodes require source")
        if self.kind != "evidence" and self.source is not None:
            raise ValueError("source is only valid for evidence nodes")
        if self.kind == "citation" and not self.cite_key:
            raise ValueError("citation nodes require cite_key")
        if self.kind != "citation" and self.cite_key is not None:
            raise ValueError("cite_key is only valid for citation nodes")
        if self.kind != "claim" and (self.section is not None or self.strength is not None):
            raise ValueError("section and strength are only valid for claim nodes")
        citation_fields = {
            "entry_type": self.entry_type,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "doi": self.doi,
            "url": self.url,
        }
        if self.kind != "citation":
            for name, value in citation_fields.items():
                if value is not None:
                    raise ValueError(f"{name} is only valid for citation nodes")
        else:
            assert self.cite_key is not None  # narrowed by check above
            if self.cite_key.lower() in _PLACEHOLDER_CITE_KEYS:
                raise ValueError(
                    f"cite_key {self.cite_key!r} is a placeholder; provide a real BibTeX key"
                )
            if not _CITE_KEY_RE.match(self.cite_key):
                raise ValueError(f"cite_key {self.cite_key!r} must match {_CITE_KEY_RE.pattern}")
        return self


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    src: str = Field(..., min_length=1)
    dst: str = Field(..., min_length=1)
    kind: EdgeKind


class EvidenceGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
