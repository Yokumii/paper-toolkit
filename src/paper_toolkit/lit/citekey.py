"""Deterministic BibTeX cite-key generation.

A cite key is `<lastname><year>_<title-hash4>` — lowercase, ASCII only.
The trailing 4-char title hash disambiguates same-author-same-year
collisions (a very common case once a workspace has 30+ refs). Both
arguments are required; if year or last name is missing, fall back to
`anon` / `nd` so we still emit *some* key (callers can override later).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata


def _strip_diacritics(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _slug_token(text: str) -> str:
    """Lowercase ASCII alphanumeric only — empty string if nothing survives."""
    ascii_text = _strip_diacritics(text).lower()
    return re.sub(r"[^a-z0-9]+", "", ascii_text)


def _last_name(author: str) -> str:
    """Return a token for the last name. Handles 'Last, First' and 'First Last'."""
    text = author.strip()
    if not text:
        return ""
    if "," in text:
        last = text.split(",", 1)[0]
    else:
        # Drop common particles ("van", "de", "der") that hug the family name.
        parts = text.split()
        last = parts[-1] if parts else text
    return _slug_token(last)


def make_cite_key(*, authors: list[str], year: int | None, title: str) -> str:
    last = _last_name(authors[0]) if authors else ""
    last = last or "anon"
    year_token = str(year) if year is not None else "nd"
    title_hash = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()[:4]
    return f"{last}{year_token}_{title_hash}"
