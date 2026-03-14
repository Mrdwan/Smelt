from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _enforce_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure every single test uses an isolated tmp database.

    Using a temporary file instead of :memory: allows multiple CLI commands
    in the same test to share the same database state.
    """
    db_path = tmp_path / "test_roadmap.db"
    monkeypatch.setenv("SMELT_DB_PATH", str(db_path))
