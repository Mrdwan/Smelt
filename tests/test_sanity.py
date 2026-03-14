"""Tests for the SanityChecker and _extract_failure_summary."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from smelt.config import SanityConfig
from smelt.db.schema import init_db
from smelt.db.store import TaskStore
from smelt.exceptions import SanityCheckError
from smelt.pipeline.sanity import SanityChecker, _extract_failure_summary


@pytest.fixture
def store(tmp_path: Path) -> TaskStore:
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return TaskStore(conn)


@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    return tmp_path


def _make_proc(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def test_sanity_passes_when_all_tests_pass(
    store: TaskStore, repo_path: Path, mocker: MagicMock
) -> None:
    mocker.patch("subprocess.run", return_value=_make_proc(0, "5 passed"))
    config = SanityConfig(create_bug_ticket_on_failure=True, bug_ticket_priority=1)
    checker = SanityChecker(store=store, config=config, repo_path=repo_path)

    result = checker.check()

    assert result.passed is True
    assert store.list_tasks() == []


def test_sanity_fails_creates_bug_ticket(
    store: TaskStore, repo_path: Path, mocker: MagicMock
) -> None:
    failure_output = "FAILED test_foo.py::test_bar - AssertionError: expected 1"
    mocker.patch("subprocess.run", return_value=_make_proc(1, failure_output))
    config = SanityConfig(create_bug_ticket_on_failure=True, bug_ticket_priority=1)
    checker = SanityChecker(store=store, config=config, repo_path=repo_path)

    with pytest.raises(SanityCheckError, match="Sanity check failed"):
        checker.check()

    tasks = store.list_tasks()
    assert len(tasks) == 1
    assert "[BUG]" in tasks[0].description
    assert tasks[0].priority == 1


def test_sanity_fails_no_bug_ticket_when_disabled(
    store: TaskStore, repo_path: Path, mocker: MagicMock
) -> None:
    mocker.patch("subprocess.run", return_value=_make_proc(1, "FAILED tests"))
    config = SanityConfig(create_bug_ticket_on_failure=False, bug_ticket_priority=1)
    checker = SanityChecker(store=store, config=config, repo_path=repo_path)

    with pytest.raises(SanityCheckError):
        checker.check()

    assert store.list_tasks() == []


def test_sanity_raises_when_pytest_not_found(
    store: TaskStore, repo_path: Path, mocker: MagicMock
) -> None:
    mocker.patch("subprocess.run", side_effect=FileNotFoundError)
    config = SanityConfig()
    checker = SanityChecker(store=store, config=config, repo_path=repo_path)

    with pytest.raises(SanityCheckError, match="pytest not found"):
        checker.check()


def test_extract_failure_summary_finds_failed_lines() -> None:
    stdout = (
        "collecting ...\n"
        "FAILED test_foo.py::test_bar - AssertionError: expected 1\n"
        "passed test_baz.py::test_ok\n"
        "ERROR test_qux.py::test_setup\n"
    )
    summary = _extract_failure_summary(stdout)
    assert "FAILED test_foo.py::test_bar" in summary
    assert "ERROR test_qux.py::test_setup" in summary
    assert "passed" not in summary


def test_extract_failure_summary_fallback_when_no_matches() -> None:
    summary = _extract_failure_summary("some random output with no keywords")
    assert summary == "Tests failed (see full output)"


def test_extract_failure_summary_assertion_error_line() -> None:
    stdout = "AssertionError: 1 != 2"
    summary = _extract_failure_summary(stdout)
    assert "AssertionError" in summary
