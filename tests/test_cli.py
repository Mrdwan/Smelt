"""Tests for the Smelt CLI — 100% coverage of all commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from smelt import __version__
from smelt.cli import _get_db, cli


def test_get_db_default_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SMELT_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    store = _get_db()
    assert store is not None
    assert (tmp_path / ".smelt" / "roadmap.db").exists()


class TestCLIGroup:
    def test_help_exits_zero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Smelt" in result.output

    def test_version_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "smelt" in result.output

    def test_no_args_shows_usage(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, [])
        assert result.exit_code == 2
        assert "Usage" in result.output


class TestRunCommand:
    def test_run_no_args(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])
        assert result.exit_code == 0
        assert "picking next ready task" in result.output

    def test_run_with_task_id(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--task", "abc-123"])
        assert result.exit_code == 0
        assert "abc-123" in result.output


class TestAddCommand:
    def test_add_basic(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["add", "implement user auth"])
        assert result.exit_code == 0
        assert "added task" in result.output
        assert "implement user auth" in result.output

    def test_add_with_context(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["add", "implement user auth", "--context", "use JWT tokens"]
        )
        assert result.exit_code == 0
        assert "JWT tokens" in result.output

    def test_add_with_depends_on(self) -> None:
        runner = CliRunner()
        # Create dependencies first otherwise add will fail due to TaskNotFoundError
        store = _get_db()
        t1 = store.add_task("task 1")
        t2 = store.add_task("task 2")

        result = runner.invoke(
            cli, ["add", "implement user auth", "--depends-on", f"{t1.id},{t2.id}"]
        )
        assert result.exit_code == 0
        assert t1.id in result.output
        assert t2.id in result.output

    def test_add_fails_missing_dependency(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["add", "implement user auth", "--depends-on", "fake-id"]
        )
        assert result.exit_code != 0
        assert "Error:" in result.output
        assert "not found" in result.output

    def test_add_missing_description_fails(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["add"])
        assert result.exit_code != 0


class TestStatusCommand:
    def test_status_empty(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "task board is empty" in result.output

    def test_status_with_tasks(self) -> None:
        runner = CliRunner()
        store = _get_db()
        store.add_task("test task alpha")

        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "Smelt Task Board" in result.output
        assert "test task alpha" in result.output


class TestLintCommand:
    def test_lint_default_success(self, mocker: MagicMock) -> None:
        mock_run = mocker.patch("subprocess.run")
        runner = CliRunner()
        result = runner.invoke(cli, ["lint"])
        assert result.exit_code == 0
        assert "fixing lint + formatting" in result.output
        assert "Linting and formatting complete!" in result.output
        assert mock_run.call_count == 2

    def test_lint_default_fails(self, mocker: MagicMock) -> None:
        mock_run = mocker.patch("subprocess.run")
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, ["ruff"])

        runner = CliRunner()
        result = runner.invoke(cli, ["lint"])
        assert result.exit_code != 0
        assert "Linting failed." in result.output

    def test_lint_check_mode_success(self, mocker: MagicMock) -> None:
        mock_run = mocker.patch("subprocess.run")
        runner = CliRunner()
        result = runner.invoke(cli, ["lint", "--check"])
        assert result.exit_code == 0
        assert "checking lint (CI mode)" in result.output
        assert "All checks passed!" in result.output
        assert mock_run.call_count == 2

    def test_lint_check_mode_fails(self, mocker: MagicMock) -> None:
        mock_run = mocker.patch("subprocess.run")
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, ["ruff"])

        runner = CliRunner()
        result = runner.invoke(cli, ["lint", "--check"])
        assert result.exit_code != 0
        assert "Linting failed." in result.output


class TestReplayCommand:
    def test_replay(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["replay", "run-42"])
        assert result.exit_code == 0
        assert "run-42" in result.output

    def test_replay_missing_id_fails(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["replay"])
        assert result.exit_code != 0


class TestStubs:
    def test_history(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["history"])
        assert result.exit_code == 0

    def test_cleanup(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup"])
        assert result.exit_code == 0

    def test_decompose(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decompose", "task-99"])
        assert result.exit_code == 0


class TestPackageMetadata:
    def test_version_is_string(self) -> None:
        assert isinstance(__version__, str)

    def test_package_docstring(self) -> None:
        import smelt

        assert smelt.__doc__ is not None
        assert "Smelt" in smelt.__doc__
