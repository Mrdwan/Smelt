from unittest.mock import MagicMock, patch

import pytest

from smelt.agents.aider import AiderAgent
from smelt.exceptions import AgentNotFoundError


@patch("shutil.which", return_value=None)
def test_raises_when_aider_not_installed(mock_h: MagicMock) -> None:
    with pytest.raises(AgentNotFoundError):
        AiderAgent(model="test-model")


@patch("shutil.which", return_value="/usr/bin/aider")
@patch("subprocess.run", return_value=MagicMock(returncode=0))
def test_run_returns_true_on_success(
    mock_subprocess: MagicMock,
    mock_which: MagicMock,
) -> None:
    assert AiderAgent(model="test-model").run("Test message", []) is True


@patch("shutil.which", return_value="/usr/bin/aider")
@patch("subprocess.run", return_value=MagicMock(returncode=1))
def test_run_returns_false_on_failure(
    mock_subprocess: MagicMock, mock_which: MagicMock
) -> None:
    assert AiderAgent(model="test-model").run("Test message", []) is False


@patch("shutil.which", return_value="/usr/bin/aider")
@patch("subprocess.run", return_value=MagicMock(returncode=0))
def test_context_files_are_passed_correctly(
    mock_subprocess: MagicMock, mock_which: MagicMock
) -> None:
    AiderAgent(model="test-model").run(
        message="Test message", context_files=["memory/ARCHITECTURE.md"]
    )

    expected_cmd = [
        "aider",
        "--model",
        "test-model",
        "--message",
        "Test message",
        "--yes-always",
        "--no-auto-commits",
        "--no-stream",
        "--no-suggest-shell-commands",
        "--read",
        "memory/ARCHITECTURE.md",
    ]

    mock_subprocess.assert_called_with(expected_cmd, cwd=".")
