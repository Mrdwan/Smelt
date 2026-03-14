"""Tests for the Architect stage."""

from __future__ import annotations

from smelt.config import ModelsConfig
from smelt.pipeline.architect import ArchitectStage
from smelt.pipeline.stages import StageInput


class _FakeLLM:
    """Fake LLMClient that records calls and returns a canned plan."""

    def __init__(self, response: str = "## Plan\nModify foo.py") -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        self.calls.append(
            {
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return self.response


def _make_input(
    task: str = "Add login endpoint",
    context: str | None = None,
    repo: str = "## File Tree\nsrc/",
    plan: str | None = None,
    last_failure: str | None = None,
) -> StageInput:
    return StageInput(
        task_description=task,
        task_context=context,
        repo_context=repo,
        plan=plan,
        last_failure=last_failure,
    )


def test_architect_returns_passed_true() -> None:
    llm = _FakeLLM()
    stage = ArchitectStage(llm=llm, models=ModelsConfig())
    output = stage.execute(_make_input())
    assert output.passed is True
    assert output.escalate_to is None


def test_architect_uses_configured_model() -> None:
    llm = _FakeLLM()
    models = ModelsConfig(architect="claude-opus-4-20250514")
    stage = ArchitectStage(llm=llm, models=models)
    stage.execute(_make_input())
    assert llm.calls[0]["model"] == "claude-opus-4-20250514"


def test_architect_includes_task_in_prompt() -> None:
    llm = _FakeLLM()
    stage = ArchitectStage(llm=llm, models=ModelsConfig())
    stage.execute(_make_input(task="Build the auth system"))
    assert "Build the auth system" in str(llm.calls[0]["user_prompt"])


def test_architect_includes_external_context() -> None:
    llm = _FakeLLM()
    stage = ArchitectStage(llm=llm, models=ModelsConfig())
    stage.execute(_make_input(context="API spec: POST /login"))
    assert "API spec: POST /login" in str(llm.calls[0]["user_prompt"])


def test_architect_uses_none_provided_when_no_context() -> None:
    llm = _FakeLLM()
    stage = ArchitectStage(llm=llm, models=ModelsConfig())
    stage.execute(_make_input(context=None))
    assert "None provided." in str(llm.calls[0]["user_prompt"])


def test_architect_injects_feedback_when_last_failure_set() -> None:
    llm = _FakeLLM()
    stage = ArchitectStage(llm=llm, models=ModelsConfig())
    stage.execute(_make_input(last_failure="Reviewer: approach has a security flaw"))
    prompt = str(llm.calls[0]["user_prompt"])
    assert "Reviewer: approach has a security flaw" in prompt
    assert "Previous Attempt Feedback" in prompt


def test_architect_no_feedback_section_when_no_failure() -> None:
    llm = _FakeLLM()
    stage = ArchitectStage(llm=llm, models=ModelsConfig())
    stage.execute(_make_input(last_failure=None))
    prompt = str(llm.calls[0]["user_prompt"])
    assert "Previous Attempt Feedback" not in prompt


def test_architect_output_is_llm_response() -> None:
    llm = _FakeLLM(response="## Implementation Plan\n1. Modify auth.py")
    stage = ArchitectStage(llm=llm, models=ModelsConfig())
    output = stage.execute(_make_input())
    assert output.output == "## Implementation Plan\n1. Modify auth.py"


def test_architect_name() -> None:
    llm = _FakeLLM()
    stage = ArchitectStage(llm=llm, models=ModelsConfig())
    assert stage.name == "architect"
