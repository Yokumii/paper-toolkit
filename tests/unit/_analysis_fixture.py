"""Shared fixture helpers for analysis tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def build_tiny_sqlite(path: Path, *, row_count: int = 50) -> Path:
    """Create a tiny sqlite database mimicking the agentsociety schema.

    Three tables:
    - `agent_profile`: id (int PK), name (TEXT), profile (TEXT-as-JSON)
    - `agent_status`: id (int PK), agent_id (int), tick (int), x (REAL), y (REAL)
    - `agent_dialog`: id (int PK), agent_id (int), tick (int), text (TEXT)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE agent_profile ("
            " id INTEGER PRIMARY KEY,"
            " name TEXT NOT NULL,"
            " profile TEXT NOT NULL)"
        )
        cur.execute(
            "CREATE TABLE agent_status ("
            " id INTEGER PRIMARY KEY,"
            " agent_id INTEGER NOT NULL,"
            " tick INTEGER NOT NULL,"
            " x REAL,"
            " y REAL)"
        )
        cur.execute(
            "CREATE TABLE agent_dialog ("
            " id INTEGER PRIMARY KEY,"
            " agent_id INTEGER NOT NULL,"
            " tick INTEGER NOT NULL,"
            " text TEXT NOT NULL)"
        )
        profiles = [
            (
                i,
                f"Agent {i}",
                json.dumps(
                    {
                        "age": 20 + (i % 60),
                        "trait": "curious" if i % 2 == 0 else "shy",
                        "metadata": {"source": "demo"},
                    }
                ),
            )
            for i in range(row_count)
        ]
        cur.executemany("INSERT INTO agent_profile VALUES (?, ?, ?)", profiles)
        cur.executemany(
            "INSERT INTO agent_status (agent_id, tick, x, y) VALUES (?, ?, ?, ?)",
            [(i % row_count, i // 10, float(i), float(i * 2)) for i in range(row_count * 2)],
        )
        cur.executemany(
            "INSERT INTO agent_dialog (agent_id, tick, text) VALUES (?, ?, ?)",
            [(i % row_count, i // 5, f"hello from agent {i}") for i in range(row_count)],
        )
        conn.commit()
    finally:
        conn.close()
    return path
