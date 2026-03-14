"""Base stage abstraction for the Smelt pipeline.

Every pipeline stage receives a StageInput and returns a StageOutput.
New stages are added by implementing the Stage ABC — no switch statements.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StageInput:
    """Data passed into a pipeline stage.

    Attributes:
        task_description: Plain text description of the task.
        task_context: Optional external context (API spec, design doc, etc.).
        repo_context: Rendered repository context string from tree-sitter.
        plan: Architect's implementation plan (None for the Architect itself).
        last_failure: Last failure output from a prior stage (for retry loops).
    """

    task_description: str
    task_context: str | None
    repo_context: str
    plan: str | None
    last_failure: str | None


@dataclass(frozen=True)
class StageOutput:
    """Data returned from a pipeline stage.

    Attributes:
        passed: True if the stage succeeded.
        output: Stage-specific output (plan text, QA summary, agent output, etc.).
        escalate_to: If set, the pipeline should escalate to 'coder' or 'architect'.
    """

    passed: bool
    output: str
    escalate_to: str | None


class Stage(ABC):
    """Abstract base class for all Smelt pipeline stages.

    Every stage receives a StageInput and returns a StageOutput.
    Dependencies (LLMClient, CodingAgent, config) are injected via __init__.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable stage name for logging."""
        ...  # pragma: no cover

    @abstractmethod
    def execute(self, stage_input: StageInput) -> StageOutput:
        """Run the stage logic.

        Args:
            stage_input: All data needed by this stage.

        Returns:
            StageOutput indicating pass/fail and any produced output.
        """
        ...  # pragma: no cover
