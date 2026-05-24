"""Persist/load LiteratureEntry batches as JSONL under `paper/lit/`."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from paper_toolkit.io import write_atomic_text
from paper_toolkit.lit.models import LiteratureEntry
from paper_toolkit.paths import WorkspacePaths


def slugify_query(query: str, *, max_length: int = 50) -> str:
    """Turn a free-form query into a filesystem-safe slug."""
    normalized = unicodedata.normalize("NFKD", query)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    lowered = ascii_text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not slug:
        slug = "query"
    return slug[:max_length]


def entries_to_jsonl(entries: list[LiteratureEntry]) -> str:
    return "".join(
        json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
        for entry in entries
    )


def parse_jsonl(text: str) -> list[LiteratureEntry]:
    rows: list[LiteratureEntry] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_no}: invalid JSON ({exc.msg})") from exc
        rows.append(LiteratureEntry.model_validate(payload))
    return rows


def write_index(*, workspace: Path, slug: str, entries: list[LiteratureEntry]) -> Path:
    paths = WorkspacePaths(workspace=workspace)
    paths.lit_dir.mkdir(parents=True, exist_ok=True)
    out_path = (paths.lit_dir / f"{slug}.jsonl").resolve()
    write_atomic_text(out_path, entries_to_jsonl(entries))
    return out_path


def read_index(path: Path) -> list[LiteratureEntry]:
    return parse_jsonl(path.read_text(encoding="utf-8"))
