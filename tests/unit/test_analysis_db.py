"""Unit tests for paper_toolkit.analysis.db."""

from __future__ import annotations

from pathlib import Path

import pytest

from paper_toolkit.analysis.db import (
    DBPathNotFound,
    DBQueryRefused,
    list_tables,
    profile_table,
    query,
)
from tests.unit._analysis_fixture import build_tiny_sqlite


@pytest.fixture()
def tiny_db(tmp_path: Path) -> Path:
    return build_tiny_sqlite(tmp_path / "tiny.db")


def test_list_tables_returns_three_tables_with_row_counts(tiny_db: Path) -> None:
    summaries = list_tables(db_path=tiny_db)
    by_name = {s.name: s for s in summaries}
    assert set(by_name) == {"agent_profile", "agent_status", "agent_dialog"}
    assert by_name["agent_profile"].row_count == 50
    # column metadata is captured
    profile_cols = {c.name for c in by_name["agent_profile"].columns}
    assert profile_cols == {"id", "name", "profile"}


def test_list_tables_raises_when_path_missing(tmp_path: Path) -> None:
    with pytest.raises(DBPathNotFound):
        list_tables(db_path=tmp_path / "missing.db")


def test_profile_table_detects_json_column(tiny_db: Path) -> None:
    profile = profile_table(db_path=tiny_db, table="agent_profile", sample_rows=10)
    by_name = {c.name: c for c in profile.columns}
    assert by_name["profile"].kind == "json"
    # The JSON has top-level keys age + trait + metadata
    keys = by_name["profile"].json_keys
    assert keys is not None
    assert {"age", "trait", "metadata"}.issubset(keys.keys())


def test_profile_table_numeric_returns_min_max_mean(tiny_db: Path) -> None:
    profile = profile_table(db_path=tiny_db, table="agent_status", sample_rows=20)
    by_name = {c.name: c for c in profile.columns}
    assert by_name["x"].kind == "numeric"
    assert by_name["x"].min == 0.0
    # 20 sampled rows -> x ∈ {0..19}; max is 19
    assert by_name["x"].max == 19.0
    assert by_name["x"].mean == pytest.approx(9.5)


def test_profile_table_raises_for_unknown_table(tiny_db: Path) -> None:
    with pytest.raises(ValueError):
        profile_table(db_path=tiny_db, table="nope", sample_rows=10)


def test_query_refuses_select_star_without_override(tiny_db: Path) -> None:
    with pytest.raises(DBQueryRefused):
        query(db_path=tiny_db, sql="SELECT * FROM agent_profile")


def test_query_allows_select_star_when_opted_in(tiny_db: Path) -> None:
    result = query(
        db_path=tiny_db,
        sql="SELECT * FROM agent_profile",
        allow_select_all=True,
        limit=5,
    )
    assert result.columns == ["id", "name", "profile"]
    assert len(result.rows) == 5


def test_query_injects_limit_when_missing(tiny_db: Path) -> None:
    result = query(db_path=tiny_db, sql="SELECT id FROM agent_profile", limit=3)
    assert len(result.rows) == 3
    assert result.truncated is True  # limit injected, hit the cap


def test_query_respects_existing_limit_clause(tiny_db: Path) -> None:
    result = query(db_path=tiny_db, sql="SELECT id FROM agent_profile LIMIT 4")
    assert len(result.rows) == 4
    assert result.truncated is False


def test_profile_table_detects_json_declared_type(tmp_path: Path) -> None:
    """A column whose declared type is literally `JSON` should be treated as text/json."""
    import sqlite3

    path = tmp_path / "json_decl.db"
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE rec (id INTEGER PRIMARY KEY, payload JSON NOT NULL)")
        conn.executemany(
            "INSERT INTO rec (payload) VALUES (?)",
            [(f'{{"k": {i}, "label": "row-{i}"}}',) for i in range(10)],
        )
        conn.commit()
    finally:
        conn.close()
    profile = profile_table(db_path=path, table="rec", sample_rows=10)
    payload = next(c for c in profile.columns if c.name == "payload")
    assert payload.kind == "json"
    assert payload.json_keys is not None
    assert {"k", "label"}.issubset(payload.json_keys.keys())
