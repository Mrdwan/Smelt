"""Tests for the GooseAdapter."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from smelt.agents.goose_adapter import GooseAdapter
from smelt.exceptions import AgentError, AgentTimeoutError


def _make_proc(stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = 0
    return proc


def test_successful_session(mocker: MagicMock) -> None:
    mocker.patch("subprocess.run", return_value=_make_proc(stdout="  done\n"))
    adapter = GooseAdapter()
    result = adapter.run_session(
        prompt="implement feature X",
        working_dir="/tmp",
        timeout_seconds=60,
    )
    assert result.success is True
    assert result.output == "done"
    assert result.duration_seconds >= 0.0
    assert len(result.session_id) == 8


def test_read_only_flag_passed_in_command(mocker: MagicMock) -> None:
    mock_run = mocker.patch("subprocess.run", return_value=_make_proc())
    adapter = GooseAdapter()
    adapter.run_session(
        prompt="review code",
        working_dir="/tmp",
        timeout_seconds=30,
        read_only=True,
    )
    cmd = mock_run.call_args[0][0]
    assert "--no-write" in cmd


def test_read_only_false_does_not_add_flag(mocker: MagicMock) -> None:
    mock_run = mocker.patch("subprocess.run", return_value=_make_proc())
    adapter = GooseAdapter()
    adapter.run_session(
        prompt="code",
        working_dir="/tmp",
        timeout_seconds=30,
        read_only=False,
    )
    cmd = mock_run.call_args[0][0]
    assert "--no-write" not in cmd


def test_timeout_raises_agent_timeout_error(mocker: MagicMock) -> None:
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="goose", timeout=30),
    )
    adapter = GooseAdapter()
    with pytest.raises(AgentTimeoutError, match="timed out"):
        adapter.run_session(prompt="x", working_dir="/tmp", timeout_seconds=30)


def test_non_zero_exit_raises_agent_error(mocker: MagicMock) -> None:
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(
            returncode=1, cmd="goose", stderr="crashed"
        ),
    )
    adapter = GooseAdapter()
    with pytest.raises(AgentError, match="crashed"):
        adapter.run_session(prompt="x", working_dir="/tmp", timeout_seconds=60)


def test_non_zero_exit_uses_stdout_when_no_stderr(mocker: MagicMock) -> None:
    err = subprocess.CalledProcessError(returncode=1, cmd="goose")
    err.stdout = "stdout error"
    err.stderr = ""
    mocker.patch("subprocess.run", side_effect=err)
    adapter = GooseAdapter()
    with pytest.raises(AgentError, match="stdout error"):
        adapter.run_session(prompt="x", working_dir="/tmp", timeout_seconds=60)


def test_custom_executable(mocker: MagicMock) -> None:
    mock_run = mocker.patch("subprocess.run", return_value=_make_proc())
    adapter = GooseAdapter(executable="/usr/local/bin/goose")
    adapter.run_session(prompt="x", working_dir="/tmp", timeout_seconds=30)
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "/usr/local/bin/goose"


def test_prompt_passed_via_text_flag(mocker: MagicMock) -> None:
    mock_run = mocker.patch("subprocess.run", return_value=_make_proc())
    adapter = GooseAdapter()
    adapter.run_session(prompt="my prompt", working_dir="/tmp", timeout_seconds=30)
    cmd = mock_run.call_args[0][0]
    assert "--text" in cmd
    assert "my prompt" in cmd
