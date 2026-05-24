"""Load a FigureSpec's `data` field into a uniform list-of-dicts shape.

Two modes:
- Inline: `data` is already a list of dicts; pass through after light type
  coercion (numbers stay numbers; strings stay strings).
- Path: `data` is a string. We resolve it spec-dir-first, then workspace-
  relative, then accept it as an absolute path. Dispatch on suffix:
  `.csv` → `csv.DictReader`; `.json` → `json.loads` (must be a list).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from paper_toolkit.paths import WorkspacePaths


class FigureDataNotFound(FileNotFoundError):
    """Raised when a path-form `data` field cannot be resolved on disk."""


class FigureDataMalformed(ValueError):
    """Raised when a path-form `data` file is unreadable or wrong-shaped."""


def _coerce_value(value: Any) -> Any:
    """Promote CSV strings to int/float when they parse cleanly."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped == "":
        return None
    try:
        if "." in stripped or "e" in stripped.lower():
            return float(stripped)
        return int(stripped)
    except ValueError:
        return value


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: _coerce_value(value) for key, value in row.items()} for row in reader]


def _read_json(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise FigureDataMalformed(
            f"{path} must contain a JSON list of row objects (got {type(raw).__name__})."
        )
    for idx, row in enumerate(raw):
        if not isinstance(row, dict):
            raise FigureDataMalformed(
                f"{path} row {idx} must be a JSON object, got {type(row).__name__}."
            )
    return raw


def _resolve_data_path(*, raw: str, spec_dir: Path, workspace: Path) -> Path:
    candidates = [
        spec_dir / raw,
        workspace / raw,
        Path(raw),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FigureDataNotFound(
        f"data path {raw!r} not found relative to spec dir, workspace, or as absolute."
    )


def load_data(
    *,
    data: list[dict[str, Any]] | str,
    spec_dir: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    path = _resolve_data_path(raw=data, spec_dir=spec_dir, workspace=workspace)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv(path)
    if suffix == ".json":
        return _read_json(path)
    raise FigureDataMalformed(f"unsupported data file extension {suffix!r}; use .csv or .json")


__all__ = [
    "FigureDataMalformed",
    "FigureDataNotFound",
    "WorkspacePaths",
    "load_data",
]
