"""Tests for the Smelt CLI — 100% coverage of all commands."""

from __future__ import annotations

from click.testing import CliRunner

from smelt import __version__
from smelt.cli import cli


class TestCLIGroup:
    """Tests for the top-level CLI group."""

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
    """Tests for `smelt run`."""

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

    def test_run_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0


class TestAddCommand:
    """Tests for `smelt add`."""

    def test_add_basic(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["add", "implement user auth"])
        assert result.exit_code == 0
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
        result = runner.invoke(
            cli, ["add", "implement user auth", "--depends-on", "task-1,task-2"]
        )
        assert result.exit_code == 0
        assert "task-1,task-2" in result.output

    def test_add_with_all_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "add",
                "build API",
                "--context",
                "REST API spec",
                "--depends-on",
                "task-0",
            ],
        )
        assert result.exit_code == 0
        assert "build API" in result.output
        assert "REST API spec" in result.output
        assert "task-0" in result.output

    def test_add_missing_description_fails(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["add"])
        assert result.exit_code != 0

    def test_add_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["add", "--help"])
        assert result.exit_code == 0


class TestStatusCommand:
    """Tests for `smelt status`."""

    def test_status(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "task board" in result.output

    def test_status_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0


class TestLintCommand:
    """Tests for `smelt lint`."""

    def test_lint_default(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["lint"])
        assert result.exit_code == 0
        assert "fixing lint" in result.output

    def test_lint_check_mode(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["lint", "--check"])
        assert result.exit_code == 0
        assert "checking lint" in result.output

    def test_lint_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["lint", "--help"])
        assert result.exit_code == 0


class TestHistoryCommand:
    """Tests for `smelt history`."""

    def test_history(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["history"])
        assert result.exit_code == 0
        assert "run history" in result.output

    def test_history_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["history", "--help"])
        assert result.exit_code == 0


class TestReplayCommand:
    """Tests for `smelt replay`."""

    def test_replay(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["replay", "run-42"])
        assert result.exit_code == 0
        assert "run-42" in result.output

    def test_replay_missing_id_fails(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["replay"])
        assert result.exit_code != 0

    def test_replay_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["replay", "--help"])
        assert result.exit_code == 0


class TestCleanupCommand:
    """Tests for `smelt cleanup`."""

    def test_cleanup(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup"])
        assert result.exit_code == 0
        assert "cleaning up" in result.output

    def test_cleanup_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup", "--help"])
        assert result.exit_code == 0


class TestDecomposeCommand:
    """Tests for `smelt decompose`."""

    def test_decompose(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decompose", "task-99"])
        assert result.exit_code == 0
        assert "task-99" in result.output

    def test_decompose_missing_id_fails(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decompose"])
        assert result.exit_code != 0

    def test_decompose_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decompose", "--help"])
        assert result.exit_code == 0


class TestPackageMetadata:
    """Tests for package-level metadata."""

    def test_version_is_string(self) -> None:
        assert isinstance(__version__, str)

    def test_version_format(self) -> None:
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_package_docstring(self) -> None:
        import smelt

        assert smelt.__doc__ is not None
        assert "Smelt" in smelt.__doc__
