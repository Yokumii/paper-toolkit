"""SQLite introspection used by `paper analysis list-tables / profile-table / query`.

Hard rules baked into this module (mirror the plan's "DB introspection rules"):

- Connection is always read-only via `file:<path>?mode=ro` URI form.
- `list_tables` caps at 200 tables to avoid runaway payloads.
- `profile_table` samples `--sample-rows` rows (default 5_000) ordered by `rowid`.
  For numeric columns it returns min/max plus mean (computed in Python on the
  sample so we don't depend on SQLite's `AVG` for JSON-blob TEXT columns).
- JSON-column detection: TEXT columns whose sampled values parse as JSON ≥80%
  of the time switch to a JSON summary (top-level keys + type frequencies)
  instead of numeric stats — JSON-encoded TEXT routinely lives in
  agentsociety SQLite tables and `AVG` on it returns 0 silently.
- `query` refuses `SELECT *` unless `allow_select_all=True`, injects a
  `LIMIT 1000` (or the caller-supplied limit) when one is absent, and returns
  rows as a `{columns, rows}` envelope (columnar form keeps payloads small).

No LLM in the toolkit — these helpers are pure mechanism.
"""

from __future__ import annotations

import json
import re
import sqlite3
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_TABLES = 200
DEFAULT_SAMPLE_ROWS = 5_000
DEFAULT_QUERY_LIMIT = 1_000
DISTINCT_CAP = 1_000
JSON_DETECTION_RATIO = 0.8
_SELECT_STAR_RE = re.compile(r"^\s*select\s+\*", re.IGNORECASE)
_LIMIT_PRESENT_RE = re.compile(r"\blimit\s+\d+", re.IGNORECASE)


class DBPathNotFound(FileNotFoundError):
    """Raised when the requested SQLite path does not exist."""


class DBQueryRefused(ValueError):
    """Raised when a query is rejected by the safety rules (SELECT * without override)."""


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    declared_type: str
    nullable: bool
    is_primary_key: bool


@dataclass(frozen=True)
class TableSummary:
    name: str
    row_count: int
    columns: list[ColumnInfo]


@dataclass(frozen=True)
class ColumnProfile:
    """Per-column profile. `kind` is the wire shape consumers expect."""

    name: str
    declared_type: str
    kind: str  # "numeric" | "text" | "json" | "other"
    sampled: int
    null_count: int
    distinct_count: int | None
    min: float | int | str | None = None
    max: float | int | str | None = None
    mean: float | None = None
    json_keys: dict[str, dict[str, int]] | None = None


@dataclass(frozen=True)
class TableProfile:
    table: str
    row_count: int
    sampled_rows: int
    columns: list[ColumnProfile]


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    truncated: bool


def _ensure_path(db_path: Path) -> Path:
    path = db_path.expanduser().resolve()
    if not path.is_file():
        raise DBPathNotFound(f"sqlite database not found: {path}")
    return path


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    path = _ensure_path(db_path)
    # `uri=True` lets us use the `mode=ro` query parameter so a corrupt write
    # path can never silently mutate the experiment artifact.
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def list_tables(*, db_path: Path) -> list[TableSummary]:
    conn = _open_readonly(db_path)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        names = [row[0] for row in cur.fetchall()][:MAX_TABLES]
        summaries: list[TableSummary] = []
        for name in names:
            row_count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            cols = _table_columns(conn, name)
            summaries.append(TableSummary(name=name, row_count=row_count, columns=cols))
        return summaries
    finally:
        conn.close()


def _table_columns(conn: sqlite3.Connection, table: str) -> list[ColumnInfo]:
    cur = conn.execute(f'PRAGMA table_info("{table}")')
    columns: list[ColumnInfo] = []
    for _, name, declared_type, notnull, _, pk in cur.fetchall():
        columns.append(
            ColumnInfo(
                name=name,
                declared_type=(declared_type or "").upper(),
                nullable=not bool(notnull),
                is_primary_key=bool(pk),
            )
        )
    return columns


def profile_table(
    *,
    db_path: Path,
    table: str,
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
) -> TableProfile:
    if sample_rows < 1:
        raise ValueError("sample_rows must be >= 1")
    conn = _open_readonly(db_path)
    try:
        # Validate table exists. Quoted identifier — the caller-supplied name is
        # treated as data (we never interpolate user values into SQL keywords).
        existing = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
                (table,),
            )
        }
        if table not in existing:
            raise ValueError(f"table not found: {table}")

        row_count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        columns = _table_columns(conn, table)
        col_names = [c.name for c in columns]
        col_quoted = ", ".join(f'"{c}"' for c in col_names) or "*"
        sample = conn.execute(
            f'SELECT {col_quoted} FROM "{table}" ORDER BY rowid LIMIT ?',
            (sample_rows,),
        ).fetchall()

        sampled_rows = len(sample)
        profiles: list[ColumnProfile] = []
        for idx, column in enumerate(columns):
            values = [row[idx] for row in sample]
            profiles.append(_profile_column(column=column, values=values))
        return TableProfile(
            table=table,
            row_count=row_count,
            sampled_rows=sampled_rows,
            columns=profiles,
        )
    finally:
        conn.close()


def _profile_column(*, column: ColumnInfo, values: list[Any]) -> ColumnProfile:
    sampled = len(values)
    null_count = sum(1 for v in values if v is None)
    non_null = [v for v in values if v is not None]
    distinct_count: int | None
    try:
        distinct_count = min(len({_freeze(v) for v in non_null}), DISTINCT_CAP)
    except TypeError:
        distinct_count = None

    declared = column.declared_type.upper()
    numeric_decl = any(tag in declared for tag in ("INT", "REAL", "FLOAT", "DOUBLE", "NUMERIC"))
    text_decl = (
        "TEXT" in declared
        or "CHAR" in declared
        or "CLOB" in declared
        or "JSON" in declared
        or declared == ""
    )

    if numeric_decl and non_null:
        nums = [v for v in non_null if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if nums:
            return ColumnProfile(
                name=column.name,
                declared_type=column.declared_type,
                kind="numeric",
                sampled=sampled,
                null_count=null_count,
                distinct_count=distinct_count,
                min=min(nums),
                max=max(nums),
                mean=statistics.fmean(nums),
            )

    if text_decl and non_null:
        json_summary = _maybe_summarize_json(non_null)
        if json_summary is not None:
            return ColumnProfile(
                name=column.name,
                declared_type=column.declared_type or "TEXT",
                kind="json",
                sampled=sampled,
                null_count=null_count,
                distinct_count=distinct_count,
                json_keys=json_summary,
            )
        text_vals = [v for v in non_null if isinstance(v, str)]
        if text_vals:
            return ColumnProfile(
                name=column.name,
                declared_type=column.declared_type or "TEXT",
                kind="text",
                sampled=sampled,
                null_count=null_count,
                distinct_count=distinct_count,
                min=min(text_vals, key=len) if text_vals else None,
                max=max(text_vals, key=len) if text_vals else None,
            )

    return ColumnProfile(
        name=column.name,
        declared_type=column.declared_type or "BLOB",
        kind="other",
        sampled=sampled,
        null_count=null_count,
        distinct_count=distinct_count,
    )


def _freeze(value: Any) -> Any:
    """Make values hashable for the distinct-count set.

    Bytes pass through; lists/dicts are stringified (we only count distinct
    *shapes*, not nuanced equality).
    """
    if isinstance(value, (str, int, float, bytes, bool)) or value is None:
        return value
    return repr(value)


def _maybe_summarize_json(values: list[Any]) -> dict[str, dict[str, int]] | None:
    """Return a key→type-frequency map if ≥ JSON_DETECTION_RATIO of values parse as JSON dicts."""
    parsed_objects: list[dict[str, Any]] = []
    parseable = 0
    candidates = [v for v in values if isinstance(v, str)]
    if not candidates:
        return None
    for value in candidates:
        try:
            obj = json.loads(value)
        except (TypeError, ValueError):
            continue
        parseable += 1
        if isinstance(obj, dict):
            parsed_objects.append(obj)
    if parseable / len(candidates) < JSON_DETECTION_RATIO:
        return None
    if not parsed_objects:
        return None
    key_types: dict[str, dict[str, int]] = {}
    for obj in parsed_objects:
        for key, raw_val in obj.items():
            tname = type(raw_val).__name__
            bucket = key_types.setdefault(key, {})
            bucket[tname] = bucket.get(tname, 0) + 1
    return key_types


def query(
    *,
    db_path: Path,
    sql: str,
    limit: int = DEFAULT_QUERY_LIMIT,
    allow_select_all: bool = False,
) -> QueryResult:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise DBQueryRefused("empty SQL")
    if not allow_select_all and _SELECT_STAR_RE.match(cleaned):
        raise DBQueryRefused(
            "SELECT * refused; name columns explicitly or pass allow_select_all=True."
        )
    has_limit = bool(_LIMIT_PRESENT_RE.search(cleaned))
    final_sql = cleaned if has_limit else f"{cleaned} LIMIT {limit}"
    conn = _open_readonly(db_path)
    try:
        cursor = conn.execute(final_sql)
        columns = [d[0] for d in cursor.description or []]
        rows_raw = cursor.fetchall()
        rows = [list(row) for row in rows_raw]
        truncated = (not has_limit) and len(rows) == limit
        return QueryResult(columns=columns, rows=rows, truncated=truncated)
    finally:
        conn.close()
