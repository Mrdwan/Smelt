from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from smelt.cli import app
from smelt.config import Settings
from smelt.exceptions import AgentNotFoundError, StorageError
from smelt.roadmap.base import Step

runner = CliRunner()


@pytest.fixture(autouse=True)
def use_tmp_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_settings = Settings(_env_file=None, memory=tmp_path / "memory")
    monkeypatch.setattr("smelt.cli.settings", fake_settings)


@pytest.fixture
def mock_roadmap() -> MagicMock:
    roadmap = MagicMock()
    roadmap.next_step.return_value = Step(id="1", description="Add login page", done=False)
    return roadmap


@pytest.fixture
def mock_agent() -> MagicMock:
    agent = MagicMock()
    agent.run.return_value = True
    return agent


def test_no_steps_remaining(mock_roadmap: MagicMock) -> None:
    mock_roadmap.next_step.return_value = None

    with patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap):
        result = runner.invoke(app, ["next"])

    assert result.exit_code == 0
    assert "No steps remaining" in result.output


def test_prints_next_step(mock_roadmap: MagicMock) -> None:
    with patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap):
        result = runner.invoke(app, ["next"], input="n\n")

    assert "Add login page" in result.output


def test_user_declines_does_not_run_agent(mock_roadmap: MagicMock) -> None:
    with (
        patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap),
        patch("smelt.cli.AiderAgent") as MockAgent,
    ):
        runner.invoke(app, ["next"], input="n\n")

    MockAgent.assert_not_called()


def test_user_confirms_runs_agent(mock_roadmap: MagicMock, mock_agent: MagicMock) -> None:
    with (
        patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap),
        patch("smelt.cli.AiderAgent", return_value=mock_agent),
    ):
        runner.invoke(app, ["next"], input="y\n")

    mock_agent.run.assert_called_once_with(
        message="Add login page", context_files=[]
    )


def test_agent_success_marks_step_done(mock_roadmap: MagicMock, mock_agent: MagicMock) -> None:
    with (
        patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap),
        patch("smelt.cli.AiderAgent", return_value=mock_agent),
    ):
        result = runner.invoke(app, ["next"], input="y\n")

    mock_roadmap.mark_done.assert_called_once_with("1")
    assert result.exit_code == 0
    assert "marked as done" in result.output


def test_agent_failure_does_not_mark_done(mock_roadmap: MagicMock, mock_agent: MagicMock) -> None:
    mock_agent.run.return_value = False

    with (
        patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap),
        patch("smelt.cli.AiderAgent", return_value=mock_agent),
    ):
        result = runner.invoke(app, ["next"], input="y\n")

    mock_roadmap.mark_done.assert_not_called()
    assert result.exit_code == 1
    assert "Agent failed" in result.output


def test_agent_not_found_exits_with_error(mock_roadmap: MagicMock) -> None:
    with (
        patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap),
        patch("smelt.cli.AiderAgent", side_effect=AgentNotFoundError("aider not found")),
    ):
        result = runner.invoke(app, ["next"], input="y\n")

    assert result.exit_code == 1
    assert "aider not found" in result.output


def test_storage_error_on_next_step_exits(mock_roadmap: MagicMock) -> None:
    mock_roadmap.next_step.side_effect = StorageError("DB corrupt")

    with patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap):
        result = runner.invoke(app, ["next"])

    assert result.exit_code == 1
    assert "Error reading roadmap" in result.output


def test_storage_error_on_mark_done_exits(mock_roadmap: MagicMock, mock_agent: MagicMock) -> None:
    mock_roadmap.mark_done.side_effect = StorageError("write failed")

    with (
        patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap),
        patch("smelt.cli.AiderAgent", return_value=mock_agent),
    ):
        result = runner.invoke(app, ["next"], input="y\n")

    assert result.exit_code == 1
    assert "failed to mark step as done" in result.output


def test_context_files_passed_when_memory_files_exist(
    mock_roadmap: MagicMock, mock_agent: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memory_dir = tmp_path / "memory_with_files"
    memory_dir.mkdir()
    (memory_dir / "ARCHITECTURE.md").write_text("Layered arch")
    (memory_dir / "DECISIONS.md").write_text("Use SQLite")

    fake_settings = Settings(_env_file=None, memory=memory_dir)
    monkeypatch.setattr("smelt.cli.settings", fake_settings)

    with (
        patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap),
        patch("smelt.cli.AiderAgent", return_value=mock_agent),
    ):
        runner.invoke(app, ["next"], input="y\n")

    _, call_kwargs = mock_agent.run.call_args
    assert str(memory_dir / "ARCHITECTURE.md") in call_kwargs["context_files"]
    assert str(memory_dir / "DECISIONS.md") in call_kwargs["context_files"]


def test_roadmap_closed_on_no_steps(mock_roadmap: MagicMock) -> None:
    mock_roadmap.next_step.return_value = None

    with patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap):
        runner.invoke(app, ["next"])

    mock_roadmap.close.assert_called_once()


def test_roadmap_closed_on_success(mock_roadmap: MagicMock, mock_agent: MagicMock) -> None:
    with (
        patch("smelt.cli.SQLiteRoadmapStorage", return_value=mock_roadmap),
        patch("smelt.cli.AiderAgent", return_value=mock_agent),
    ):
        runner.invoke(app, ["next"], input="y\n")

    mock_roadmap.close.assert_called_once()
