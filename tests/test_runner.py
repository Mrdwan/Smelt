"""Tests for the PipelineRunner orchestrator."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from smelt.agents.protocols import CodingAgent, LLMClient
from smelt.config import CodingConfig, SmeltConfig
from smelt.db.models import AgentResult, ToolResult
from smelt.db.schema import init_db
from smelt.db.store import TaskStore
from smelt.exceptions import AgentError, InfraError, LLMError
from smelt.pipeline.runner import PipelineRunner
from smelt.pipeline.sanity import SanityChecker

# ---------------------------------------------------------------------------
# Fakes satisfying the protocols
# ---------------------------------------------------------------------------


class _FakeLLM:
    """Fake LLMClient: always returns a canned plan."""

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        return "## Plan\nModify the file."


class _FailingLLM:
    """Fake LLMClient that raises on complete."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        raise self._exc


class _FakeAgent:
    """Fake CodingAgent: always succeeds."""

    def __init__(self, success: bool = True) -> None:
        self._success = success

    def run_session(
        self,
        *,
        prompt: str,
        working_dir: str,
        timeout_seconds: int,
        read_only: bool = False,
    ) -> AgentResult:
        return AgentResult(
            success=self._success,
            session_id="fake",
            output="done",
            duration_seconds=0.1,
        )


class _FailingAgent:
    """Fake CodingAgent that raises on run_session."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def run_session(
        self,
        *,
        prompt: str,
        working_dir: str,
        timeout_seconds: int,
        read_only: bool = False,
    ) -> AgentResult:
        raise self._exc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> TaskStore:
    conn = sqlite3.connect(str(tmp_path / "runner.db"))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return TaskStore(conn)


@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def mock_git(mocker: MagicMock) -> MagicMock:
    git = MagicMock()
    git.create_branch.return_value = "smelt/task-abc"
    return git


def _make_runner(
    store: TaskStore,
    repo_path: Path,
    mock_git: MagicMock,
    llm: LLMClient | None = None,
    agent: CodingAgent | None = None,
    config: SmeltConfig | None = None,
) -> PipelineRunner:
    return PipelineRunner(
        config=config or SmeltConfig.default(),
        store=store,
        git=mock_git,
        llm=llm or _FakeLLM(),
        agent=agent or _FakeAgent(),
        repo_path=repo_path,
    )


def _patch_sanity_pass(mocker: MagicMock) -> None:
    """Patch SanityChecker.check to always pass without running pytest."""
    mocker.patch.object(
        SanityChecker,
        "check",
        return_value=ToolResult(
            tool_name="pytest", passed=True, stdout="ok", stderr="", return_code=0
        ),
    )


def _patch_qa(mocker: MagicMock, returncode: int = 0, stdout: str = "ok") -> MagicMock:
    """Patch subprocess in the QA module."""
    return mocker.patch(
        "subprocess.run",
        return_value=_proc(returncode, stdout),
    )


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ---------------------------------------------------------------------------
# Tests: No ready tasks
# ---------------------------------------------------------------------------


def test_no_ready_tasks_returns_failure(
    store: TaskStore, repo_path: Path, mock_git: MagicMock
) -> None:
    runner = _make_runner(store, repo_path, mock_git)
    result = runner.run()

    assert result.success is False
    assert result.stage_reached == "pick"
    assert result.task_id == ""


# ---------------------------------------------------------------------------
# Tests: Happy path
# ---------------------------------------------------------------------------


def test_happy_path_returns_success(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    _patch_sanity_pass(mocker)
    _patch_qa(mocker, returncode=0)

    task = store.add_task(description="Build feature X")
    runner = _make_runner(store, repo_path, mock_git)
    result = runner.run()

    assert result.success is True
    assert result.task_id == task.id
    assert result.stage_reached == "qa"


def test_happy_path_creates_branch(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    _patch_sanity_pass(mocker)
    _patch_qa(mocker, returncode=0)
    task = store.add_task(description="task")
    runner = _make_runner(store, repo_path, mock_git)
    runner.run()

    mock_git.create_branch.assert_called_once_with(task.id)


def test_happy_path_runs_sanity_check(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    _patch_sanity_pass(mocker)
    _patch_qa(mocker, returncode=0)
    store.add_task(description="task")
    runner = _make_runner(store, repo_path, mock_git)
    runner.run()

    mock_git.checkout_branch.assert_called_once()
    mock_git.pull.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: QA retry loop
# ---------------------------------------------------------------------------


def test_qa_fails_then_passes_on_retry(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    _patch_sanity_pass(mocker)
    call_count = 0

    def qa_side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        # First 3 calls (one full QA run: pytest+ruff+mypy) fail
        if call_count <= 3:
            return _proc(1, "FAILED test_foo")
        return _proc(0, "ok")

    mocker.patch("subprocess.run", side_effect=qa_side_effect)
    store.add_task(description="task")
    config = SmeltConfig(coding=CodingConfig(max_retries=2))
    runner = _make_runner(store, repo_path, mock_git, config=config)
    result = runner.run()

    assert result.success is True


def test_qa_fails_all_retries_marks_task_failed(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    _patch_sanity_pass(mocker)
    _patch_qa(mocker, returncode=1, stdout="FAILED test_foo")

    task = store.add_task(description="task")
    config = SmeltConfig(coding=CodingConfig(max_retries=0))
    runner = _make_runner(store, repo_path, mock_git, config=config)
    result = runner.run()

    assert result.success is False
    assert result.stage_reached == "qa"
    refreshed = store.get_task(task.id)
    assert refreshed is not None
    assert refreshed.status == "failed"


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------


def test_sanity_check_failure_reverts_task_to_ready(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    from smelt.exceptions import SanityCheckError

    mocker.patch.object(
        SanityChecker,
        "check",
        side_effect=SanityCheckError("tests failing on develop"),
    )
    task = store.add_task(description="task")
    runner = _make_runner(store, repo_path, mock_git)
    result = runner.run()

    assert result.success is False
    assert result.stage_reached == "sanity"
    refreshed = store.get_task(task.id)
    assert refreshed is not None
    assert refreshed.status == "ready"


def test_infra_error_from_llm_marks_infra_error(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    _patch_sanity_pass(mocker)
    task = store.add_task(description="task")
    runner = _make_runner(
        store, repo_path, mock_git, llm=_FailingLLM(InfraError("rate limited"))
    )
    result = runner.run()

    assert result.success is False
    refreshed = store.get_task(task.id)
    assert refreshed is not None
    assert refreshed.status == "infra-error"


def test_llm_error_marks_task_failed(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    _patch_sanity_pass(mocker)
    task = store.add_task(description="task")
    runner = _make_runner(
        store, repo_path, mock_git, llm=_FailingLLM(LLMError("bad api"))
    )
    result = runner.run()

    assert result.success is False
    refreshed = store.get_task(task.id)
    assert refreshed is not None
    assert refreshed.status == "failed"


def test_agent_error_marks_task_failed(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    _patch_sanity_pass(mocker)
    task = store.add_task(description="task")
    runner = _make_runner(
        store, repo_path, mock_git, agent=_FailingAgent(AgentError("crash"))
    )
    result = runner.run()

    assert result.success is False
    refreshed = store.get_task(task.id)
    assert refreshed is not None
    assert refreshed.status == "failed"


# ---------------------------------------------------------------------------
# Tests: Explicit task provided
# ---------------------------------------------------------------------------


def test_run_with_explicit_task(
    store: TaskStore, repo_path: Path, mock_git: MagicMock, mocker: MagicMock
) -> None:
    _patch_sanity_pass(mocker)
    _patch_qa(mocker, returncode=0)
    task = store.add_task(description="specific task")
    runner = _make_runner(store, repo_path, mock_git)
    result = runner.run(task=task)

    assert result.success is True
    assert result.task_id == task.id
