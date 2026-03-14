"""Tests for the Smelt CLI — 100% coverage of all commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from smelt import __version__
from smelt.cli import _get_config, _get_db, cli


def test_get_db_default_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SMELT_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    store = _get_db()
    assert store is not None
    assert (tmp_path / ".smelt" / "roadmap.db").exists()


def test_get_config_returns_defaults_when_no_toml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    config = _get_config()
    from smelt.config import SmeltConfig

    assert isinstance(config, SmeltConfig)


def test_get_config_loads_toml_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "smelt.toml").write_text("[context]\nmax_tokens = 1234\n")
    monkeypatch.chdir(tmp_path)
    config = _get_config()
    assert config.context.max_tokens == 1234


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


def _mock_runner(
    mocker: MagicMock, success: bool, stage: str, message: str, task_id: str = ""
) -> None:
    """Patch PipelineRunner so the run command doesn't actually run anything."""
    from smelt.pipeline.runner import PipelineResult

    mock_runner_instance = MagicMock()
    mock_runner_instance.run.return_value = PipelineResult(
        task_id=task_id, success=success, stage_reached=stage, message=message
    )
    mocker.patch(
        "smelt.pipeline.runner.PipelineRunner", return_value=mock_runner_instance
    )
    mocker.patch("smelt.cli.GitOps")


class TestRunCommand:
    def test_run_no_args_no_tasks(self, mocker: MagicMock) -> None:
        _mock_runner(mocker, False, "pick", "No ready tasks found.")
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])
        assert result.exit_code == 0
        assert "picking next ready task" in result.output

    def test_run_pipeline_success(self, mocker: MagicMock) -> None:
        _mock_runner(mocker, True, "qa", "All QA checks passed.", task_id="abc123")
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])
        assert result.exit_code == 0
        assert "Pipeline passed!" in result.output

    def test_run_pipeline_failure(self, mocker: MagicMock) -> None:
        _mock_runner(mocker, False, "qa", "QA failed.", task_id="abc123")
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])
        assert result.exit_code == 0
        assert "Pipeline failed" in result.output

    def test_run_with_task_id_not_found(self, mocker: MagicMock) -> None:
        mocker.patch("smelt.cli.GitOps")
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--task", "nonexistent-id"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_run_with_valid_task_id(self, mocker: MagicMock) -> None:
        _mock_runner(mocker, True, "qa", "Done.", task_id="abc123")
        store = _get_db()
        task = store.add_task("my task")

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--task", task.id])
        assert result.exit_code == 0
        assert task.id in result.output


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
