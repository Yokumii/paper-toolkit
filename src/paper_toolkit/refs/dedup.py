"""Duplicate detection for BibTeX entries.

Two-stage matching:

1. Normalize DOIs (lowercase, strip `https?://doi.org/` prefix); any pair of
   entries with the same normalized DOI is a duplicate.
2. For entries missing a DOI, fall back to first-author surname + title
   Jaccard >= 0.90 over tokenized, stopword-filtered titles.

Output is a list of `DuplicateGroup`s, each holding a chosen "keeper" cite
key and the cite keys it absorbs. The keeper picks the entry with the most
filled fields (DOI, title, author, year, venue) — ties broken by
first-cited ordering so the result is deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from paper_toolkit.refs.bib_reader import BibEntry

_DOI_PREFIX_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)
_TITLE_PUNCT_RE = re.compile(r"[.,;:!?()\[\]\"\'`{}*\-\u2013\u2014]")
_TITLE_STOPWORDS: frozenset[str] = frozenset(
    {"a", "an", "the", "in", "of", "for", "on", "to", "and", "with", "by", "et", "al"}
)
JACCARD_THRESHOLD = 0.90


@dataclass(frozen=True)
class DuplicateGroup:
    """A keeper plus the cite keys it absorbs."""

    reason: str  # "doi" | "title-author"
    keeper_cite_key: str
    absorbed_cite_keys: list[str]


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    text = _DOI_PREFIX_RE.sub("", text)
    return text.lower()


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    # Lowercase, drop punctuation, then collapse whitespace.
    lowered = value.lower()
    no_punct = _TITLE_PUNCT_RE.sub(" ", lowered)
    return " ".join(no_punct.split())


def title_tokens(value: str | None) -> set[str]:
    """Tokenize and drop stopwords from a title for Jaccard comparison."""
    normalized = normalize_title(value)
    return {tok for tok in normalized.split() if tok and tok not in _TITLE_STOPWORDS}


def first_author_surname(author_field: str | None) -> str:
    """Extract the first author's surname (lowercase) from a BibTeX `author` field."""
    if not author_field:
        return ""
    # Authors are split by ` and ` (case-insensitive).
    first = re.split(r"\s+and\s+", author_field, maxsplit=1, flags=re.IGNORECASE)[0]
    first = first.strip()
    if not first:
        return ""
    # "Family, Given" vs "Given Family" — split on comma first.
    if "," in first:
        surname = first.split(",", 1)[0]
    else:
        parts = first.split()
        surname = parts[-1] if parts else first
    return surname.strip().lower()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _completeness_score(entry: BibEntry) -> int:
    """Higher = more complete. Used to choose a keeper inside a group."""
    score = 0
    for field in ("doi", "title", "author", "year", "journal", "booktitle", "url", "abstract"):
        if entry.fields.get(field):
            score += 1
    return score


def _choose_keeper(entries: list[BibEntry], index_of: dict[str, int]) -> BibEntry:
    """Pick the most complete entry; ties broken by earliest position."""
    return min(
        entries,
        key=lambda e: (-_completeness_score(e), index_of[e.cite_key]),
    )


def find_duplicates(entries: list[BibEntry]) -> list[DuplicateGroup]:
    """Return one `DuplicateGroup` per detected duplicate cluster."""
    index_of = {entry.cite_key: idx for idx, entry in enumerate(entries)}
    groups: list[DuplicateGroup] = []
    assigned: set[str] = set()

    # Stage 1 — DOI clusters.
    doi_buckets: dict[str, list[BibEntry]] = {}
    for entry in entries:
        doi = normalize_doi(entry.doi)
        if not doi:
            continue
        doi_buckets.setdefault(doi, []).append(entry)
    for _doi, bucket in doi_buckets.items():
        if len(bucket) < 2:
            continue
        keeper = _choose_keeper(bucket, index_of)
        absorbed = sorted(
            (e.cite_key for e in bucket if e.cite_key != keeper.cite_key),
            key=lambda key: index_of[key],
        )
        groups.append(
            DuplicateGroup(
                reason="doi",
                keeper_cite_key=keeper.cite_key,
                absorbed_cite_keys=absorbed,
            )
        )
        for e in bucket:
            assigned.add(e.cite_key)

    # Stage 2 — title + first-author surname for the DOI-less remainder.
    remaining = [e for e in entries if e.cite_key not in assigned and not normalize_doi(e.doi)]
    used: set[str] = set()
    for idx, anchor in enumerate(remaining):
        if anchor.cite_key in used:
            continue
        surname = first_author_surname(anchor.author)
        if not surname:
            continue
        tokens = title_tokens(anchor.title)
        if not tokens:
            continue
        bucket = [anchor]
        for candidate in remaining[idx + 1 :]:
            if candidate.cite_key in used:
                continue
            if first_author_surname(candidate.author) != surname:
                continue
            cand_tokens = title_tokens(candidate.title)
            if not cand_tokens:
                continue
            if jaccard(tokens, cand_tokens) >= JACCARD_THRESHOLD:
                bucket.append(candidate)
        if len(bucket) < 2:
            continue
        keeper = _choose_keeper(bucket, index_of)
        absorbed = sorted(
            (e.cite_key for e in bucket if e.cite_key != keeper.cite_key),
            key=lambda key: index_of[key],
        )
        groups.append(
            DuplicateGroup(
                reason="title-author",
                keeper_cite_key=keeper.cite_key,
                absorbed_cite_keys=absorbed,
            )
        )
        for e in bucket:
            used.add(e.cite_key)

    return groups


def apply_dedup(entries: list[BibEntry], groups: list[DuplicateGroup]) -> list[BibEntry]:
    """Return a new list with absorbed entries removed (keepers preserved)."""
    removed: set[str] = set()
    for group in groups:
        removed.update(group.absorbed_cite_keys)
    return [entry for entry in entries if entry.cite_key not in removed]


def serialize_entries(entries: list[BibEntry]) -> str:
    """Re-emit entries by concatenating their stored `source_text`.

    Because we preserve the original bytes, dedup never corrupts a hand-
    edited refs.bib — we only drop whole entries; we never reformat the
    survivors.
    """
    if not entries:
        return ""
    return "\n\n".join(entry.source_text for entry in entries) + "\n"
