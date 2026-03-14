"""Tests for the Coder stage."""

from __future__ import annotations

from smelt.config import CodingConfig
from smelt.db.models import AgentResult
from smelt.pipeline.coder import CoderStage
from smelt.pipeline.stages import StageInput


class _FakeAgent:
    """Fake CodingAgent that records prompts and returns a canned result."""

    def __init__(self, success: bool = True, output: str = "code written") -> None:
        self._success = success
        self._output = output
        self.calls: list[dict[str, object]] = []

    def run_session(
        self,
        *,
        prompt: str,
        working_dir: str,
        timeout_seconds: int,
        read_only: bool = False,
    ) -> AgentResult:
        self.calls.append(
            {
                "prompt": prompt,
                "working_dir": working_dir,
                "timeout_seconds": timeout_seconds,
                "read_only": read_only,
            }
        )
        return AgentResult(
            success=self._success,
            session_id="fake-session",
            output=self._output,
            duration_seconds=1.0,
        )


def _make_input(
    task: str = "Implement login",
    plan: str | None = "1. Modify auth.py",
    repo: str = "## File Tree\nsrc/",
    last_failure: str | None = None,
) -> StageInput:
    return StageInput(
        task_description=task,
        task_context=None,
        repo_context=repo,
        plan=plan,
        last_failure=last_failure,
    )


def test_coder_runs_agent_with_full_access() -> None:
    agent = _FakeAgent()
    config = CodingConfig(timeout_seconds=300)
    stage = CoderStage(agent=agent, config=config, working_dir="/repo")
    stage.execute(_make_input())

    assert agent.calls[0]["read_only"] is False


def test_coder_uses_configured_timeout() -> None:
    agent = _FakeAgent()
    config = CodingConfig(timeout_seconds=999)
    stage = CoderStage(agent=agent, config=config, working_dir="/repo")
    stage.execute(_make_input())

    assert agent.calls[0]["timeout_seconds"] == 999


def test_coder_passes_working_dir() -> None:
    agent = _FakeAgent()
    config = CodingConfig()
    stage = CoderStage(agent=agent, config=config, working_dir="/my/repo")
    stage.execute(_make_input())

    assert agent.calls[0]["working_dir"] == "/my/repo"


def test_coder_prompt_contains_task_description() -> None:
    agent = _FakeAgent()
    stage = CoderStage(agent=agent, config=CodingConfig(), working_dir="/repo")
    stage.execute(_make_input(task="Build the auth system"))

    assert "Build the auth system" in str(agent.calls[0]["prompt"])


def test_coder_prompt_contains_plan() -> None:
    agent = _FakeAgent()
    stage = CoderStage(agent=agent, config=CodingConfig(), working_dir="/repo")
    stage.execute(_make_input(plan="Step 1: Add function foo()"))

    assert "Step 1: Add function foo()" in str(agent.calls[0]["prompt"])


def test_coder_prompt_uses_fallback_when_no_plan() -> None:
    agent = _FakeAgent()
    stage = CoderStage(agent=agent, config=CodingConfig(), working_dir="/repo")
    stage.execute(_make_input(plan=None))

    assert "No plan provided." in str(agent.calls[0]["prompt"])


def test_coder_injects_failure_into_prompt() -> None:
    agent = _FakeAgent()
    stage = CoderStage(agent=agent, config=CodingConfig(), working_dir="/repo")
    stage.execute(_make_input(last_failure="FAILED test_foo.py::test_bar"))

    prompt = str(agent.calls[0]["prompt"])
    assert "FAILED test_foo.py::test_bar" in prompt
    assert "Previous QA Failure" in prompt


def test_coder_no_failure_section_when_no_last_failure() -> None:
    agent = _FakeAgent()
    stage = CoderStage(agent=agent, config=CodingConfig(), working_dir="/repo")
    stage.execute(_make_input(last_failure=None))

    assert "Previous QA Failure" not in str(agent.calls[0]["prompt"])


def test_coder_returns_passed_on_success() -> None:
    agent = _FakeAgent(success=True, output="all done")
    stage = CoderStage(agent=agent, config=CodingConfig(), working_dir="/repo")
    output = stage.execute(_make_input())

    assert output.passed is True
    assert output.output == "all done"
    assert output.escalate_to is None


def test_coder_returns_not_passed_on_failure() -> None:
    agent = _FakeAgent(success=False, output="agent crashed")
    stage = CoderStage(agent=agent, config=CodingConfig(), working_dir="/repo")
    output = stage.execute(_make_input())

    assert output.passed is False


def test_coder_name() -> None:
    agent = _FakeAgent()
    stage = CoderStage(agent=agent, config=CodingConfig(), working_dir="/repo")
    assert stage.name == "coder"
