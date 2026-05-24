"""Merge new `LiteratureEntry` records into `paper/refs.bib`.

The merge is append-only: we never rewrite or reorder existing entries.
Dedup is done by cite key; an incoming entry whose key already appears
in `refs.bib` is reported as skipped (caller can choose to surface or
swallow). Keys present in incoming entries but not yet in `refs.bib`
are added in the order they were supplied.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.lit.bibtex_emit import entry_to_bibtex
from paper_toolkit.lit.models import LiteratureEntry
from paper_toolkit.paths import WorkspacePaths

_CITE_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)")


@dataclass(frozen=True)
class MergeReport:
    added: list[str]
    skipped: list[str]
    bib_path: Path


def existing_cite_keys(text: str) -> set[str]:
    return set(_CITE_KEY_RE.findall(text))


def merge_into_bib(*, workspace: Path, entries: list[LiteratureEntry]) -> MergeReport:
    paths = WorkspacePaths(workspace=workspace)
    paths.paper_dir.mkdir(parents=True, exist_ok=True)
    bib_path = paths.refs_bib
    existing_text = bib_path.read_text(encoding="utf-8") if bib_path.exists() else ""
    known = existing_cite_keys(existing_text)
    added: list[str] = []
    skipped: list[str] = []
    new_blocks: list[str] = []
    for entry in entries:
        if entry.cite_key in known:
            skipped.append(entry.cite_key)
            continue
        new_blocks.append(entry_to_bibtex(entry))
        known.add(entry.cite_key)
        added.append(entry.cite_key)
    if not new_blocks:
        return MergeReport(added=added, skipped=skipped, bib_path=bib_path.resolve())
    separator = "\n\n" if existing_text and not existing_text.endswith("\n\n") else ""
    body = existing_text + separator + "\n\n".join(new_blocks) + "\n"
    write_atomic_text(bib_path, body)
    return MergeReport(added=added, skipped=skipped, bib_path=bib_path.resolve())
