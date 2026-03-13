import os

import pytest

# Ensure tests always use an isolated, in-memory SQLite database
# by setting an environment variable that the app will read.
os.environ["SMELT_DB_PATH"] = ":memory:"


@pytest.fixture(autouse=True)
def _enforce_test_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure every single test uses an isolated in-memory database."""
    monkeypatch.setenv("SMELT_DB_PATH", ":memory:")
