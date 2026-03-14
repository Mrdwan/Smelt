"""Tests for the QA stage (deterministic: pytest, ruff, mypy)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from smelt.config import QAConfig
from smelt.pipeline.qa import QAStage, _truncate_output
from smelt.pipeline.stages import StageInput


@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def default_config() -> QAConfig:
    return QAConfig(run_tests=True, run_linter=True, run_type_checker=True)


@pytest.fixture
def stage_input() -> StageInput:
    return StageInput(
        task_description="task",
        task_context=None,
        repo_context="ctx",
        plan=None,
        last_failure=None,
    )


def _make_proc(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def test_all_tools_pass(
    repo_path: Path,
    default_config: QAConfig,
    stage_input: StageInput,
    mocker: MagicMock,
) -> None:
    mocker.patch("subprocess.run", return_value=_make_proc(0, "passed"))
    stage = QAStage(config=default_config, repo_path=repo_path)
    output = stage.execute(stage_input)
    assert output.passed is True
    assert output.escalate_to is None
    assert "All QA checks passed" in output.output


def test_pytest_fails_escalates_to_coder(
    repo_path: Path,
    stage_input: StageInput,
    mocker: MagicMock,
) -> None:
    call_count = 0

    def side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if "pytest" in cmd:
            return _make_proc(1, "FAILED test_foo.py::test_bar")
        return _make_proc(0, "ok")

    mocker.patch("subprocess.run", side_effect=side_effect)
    config = QAConfig(run_tests=True, run_linter=True, run_type_checker=True)
    stage = QAStage(config=config, repo_path=repo_path)
    output = stage.execute(stage_input)

    assert output.passed is False
    assert output.escalate_to == "coder"
    assert "pytest FAILED" in output.output


def test_ruff_fails(
    repo_path: Path,
    stage_input: StageInput,
    mocker: MagicMock,
) -> None:
    def side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
        if "ruff" in cmd:
            return _make_proc(1, "lint error here")
        return _make_proc(0, "ok")

    mocker.patch("subprocess.run", side_effect=side_effect)
    config = QAConfig(run_tests=True, run_linter=True, run_type_checker=False)
    stage = QAStage(config=config, repo_path=repo_path)
    output = stage.execute(stage_input)

    assert output.passed is False
    assert "ruff FAILED" in output.output


def test_mypy_fails(
    repo_path: Path,
    stage_input: StageInput,
    mocker: MagicMock,
) -> None:
    def side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
        if "mypy" in cmd:
            return _make_proc(1, "type error")
        return _make_proc(0, "ok")

    mocker.patch("subprocess.run", side_effect=side_effect)
    config = QAConfig(run_tests=False, run_linter=False, run_type_checker=True)
    stage = QAStage(config=config, repo_path=repo_path)
    output = stage.execute(stage_input)

    assert output.passed is False
    assert "mypy FAILED" in output.output


def test_run_tests_false_skips_pytest(
    repo_path: Path,
    stage_input: StageInput,
    mocker: MagicMock,
) -> None:
    mock_run = mocker.patch("subprocess.run", return_value=_make_proc(0))
    config = QAConfig(run_tests=False, run_linter=True, run_type_checker=False)
    stage = QAStage(config=config, repo_path=repo_path)
    stage.execute(stage_input)

    calls = [call[0][0] for call in mock_run.call_args_list]
    assert not any("pytest" in cmd for cmd in calls)


def test_coverage_flags_added_when_required(
    repo_path: Path,
    stage_input: StageInput,
    mocker: MagicMock,
) -> None:
    captured_cmds: list[list[str]] = []

    def side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
        captured_cmds.append(cmd)
        return _make_proc(0, "ok")

    mocker.patch("subprocess.run", side_effect=side_effect)
    config = QAConfig(
        run_tests=True,
        run_linter=False,
        run_type_checker=False,
        require_coverage=True,
        min_coverage_percent=90.0,
    )
    stage = QAStage(config=config, repo_path=repo_path)
    stage.execute(stage_input)

    pytest_cmd = next(c for c in captured_cmds if "pytest" in c)
    assert "--cov" in pytest_cmd
    assert "--cov-branch" in pytest_cmd
    assert "--cov-fail-under=90.0" in pytest_cmd


def test_no_tools_run_passes(
    repo_path: Path,
    stage_input: StageInput,
    mocker: MagicMock,
) -> None:
    mock_run = mocker.patch("subprocess.run")
    config = QAConfig(run_tests=False, run_linter=False, run_type_checker=False)
    stage = QAStage(config=config, repo_path=repo_path)
    output = stage.execute(stage_input)

    assert output.passed is True
    mock_run.assert_not_called()


def test_truncate_output_short() -> None:
    text = "line1\nline2\nline3"
    result = _truncate_output(text, max_lines=10)
    assert result == text


def test_qa_stage_name(repo_path: Path, default_config: QAConfig) -> None:
    stage = QAStage(config=default_config, repo_path=repo_path)
    assert stage.name == "qa"


def test_truncate_output_long() -> None:
    lines = [f"line{i}" for i in range(100)]
    text = "\n".join(lines)
    result = _truncate_output(text, max_lines=20)
    assert "... (truncated) ..." in result
    # Should have 10 lines from each end plus the marker
    result_lines = result.splitlines()
    assert len(result_lines) == 21  # 10 + 1 marker + 10
