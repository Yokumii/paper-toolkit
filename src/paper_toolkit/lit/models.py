"""Unified literature-entry model shared across all source adapters.

Each LiteratureEntry produced by an arXiv / CrossRef / OpenAlex query is
self-describing: `source` plus `source_id` together identify the upstream
record, and the remaining fields normalize the metadata into a shape the
BibTeX emitter and the merge step can both consume without dispatching on
source.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["arxiv", "crossref", "openalex"]
EntryType = Literal[
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


class LiteratureEntry(BaseModel):
    """Normalized metadata for one paper, regardless of upstream source."""

    model_config = ConfigDict(extra="forbid")

    source: Source
    source_id: str = Field(
        ..., description="arxiv id / DOI / OpenAlex id (whichever the source uses)."
    )
    title: str
    authors: list[str] = Field(
        default_factory=list, description="Each author rendered as 'First Last'."
    )
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    entry_type: EntryType = "misc"
    cite_key: str = Field(..., description="Stable BibTeX key, lowercase ASCII.")
