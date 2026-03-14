"""Unit tests for the SQLite schema definition."""

import sqlite3

import pytest

from smelt.db.schema import init_db


def test_init_db_creates_tables() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "tasks" in tables
    assert "task_dependencies" in tables


def test_init_db_is_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    init_db(conn)  # Should not raise anything


def test_foreign_keys_enforced() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO task_dependencies (task_id, depends_on) VALUES ('a', 'b')"
        )
