"""Database schema and initialization for the Smelt roadmap."""

from __future__ import annotations

import sqlite3


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize the SQLite database schema if it doesn't already exist.

    Args:
        conn: The database connection to initialize.
    """
    # Enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")

    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id            TEXT PRIMARY KEY,
            description   TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'ready',
            priority      INTEGER NOT NULL DEFAULT 0,
            complexity    INTEGER,
            context       TEXT,
            context_files TEXT,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS task_dependencies (
            task_id    TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            depends_on TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            PRIMARY KEY (task_id, depends_on)
        );
        """)
