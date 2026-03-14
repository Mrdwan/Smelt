"""Tests for the Stage ABC and StageInput/StageOutput dataclasses."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from smelt.pipeline.stages import Stage, StageInput, StageOutput


class _ConcreteStage(Stage):
    """Minimal concrete stage for testing the ABC."""

    @property
    def name(self) -> str:
        return "test"

    def execute(self, stage_input: StageInput) -> StageOutput:
        return StageOutput(passed=True, output="done", escalate_to=None)


def test_stage_name() -> None:
    stage = _ConcreteStage()
    assert stage.name == "test"


def test_stage_execute_returns_output() -> None:
    stage = _ConcreteStage()
    si = StageInput(
        task_description="desc",
        task_context=None,
        repo_context="ctx",
        plan=None,
        last_failure=None,
    )
    result = stage.execute(si)
    assert result.passed is True
    assert result.output == "done"
    assert result.escalate_to is None


def test_stage_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        Stage()  # type: ignore[abstract]


def test_stage_input_is_frozen() -> None:
    si = StageInput(
        task_description="x",
        task_context="ctx",
        repo_context="r",
        plan="p",
        last_failure="fail",
    )
    with pytest.raises(FrozenInstanceError):
        si.task_description = "y"  # type: ignore[misc]


def test_stage_output_is_frozen() -> None:
    so = StageOutput(passed=False, output="err", escalate_to="coder")
    with pytest.raises(FrozenInstanceError):
        so.passed = True  # type: ignore[misc]
