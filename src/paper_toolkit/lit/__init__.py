"""Public surface for the `paper lit ...` command family."""

from __future__ import annotations

from paper_toolkit.lit.bibtex_emit import entries_to_bibtex, entry_to_bibtex
from paper_toolkit.lit.citekey import make_cite_key
from paper_toolkit.lit.index import (
    entries_to_jsonl,
    parse_jsonl,
    read_index,
    slugify_query,
    write_index,
)
from paper_toolkit.lit.merge import MergeReport, merge_into_bib
from paper_toolkit.lit.models import LiteratureEntry

__all__ = [
    "LiteratureEntry",
    "MergeReport",
    "entries_to_bibtex",
    "entries_to_jsonl",
    "entry_to_bibtex",
    "make_cite_key",
    "merge_into_bib",
    "parse_jsonl",
    "read_index",
    "slugify_query",
    "write_index",
]
