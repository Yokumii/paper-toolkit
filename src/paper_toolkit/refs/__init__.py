"""Public surface for the `paper refs ...` command family."""

from __future__ import annotations

from paper_toolkit.refs.bib_reader import BibEntry, parse_bibtex
from paper_toolkit.refs.dedup import (
    DuplicateGroup,
    apply_dedup,
    find_duplicates,
    first_author_surname,
    jaccard,
    normalize_doi,
    normalize_title,
    serialize_entries,
    title_tokens,
)

__all__ = [
    "BibEntry",
    "DuplicateGroup",
    "apply_dedup",
    "find_duplicates",
    "first_author_surname",
    "jaccard",
    "normalize_doi",
    "normalize_title",
    "parse_bibtex",
    "serialize_entries",
    "title_tokens",
]
