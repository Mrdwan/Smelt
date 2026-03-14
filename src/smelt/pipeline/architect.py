"""Architect stage: LLM-based implementation planning.

The Architect receives the task description, external context, and repository
context, then produces a detailed implementation plan. No coding agent is used;
this is a direct LLM call only.
"""

from __future__ import annotations

from smelt.agents.protocols import LLMClient
from smelt.config import ModelsConfig
from smelt.pipeline.stages import Stage, StageInput, StageOutput

_ARCHITECT_SYSTEM_PROMPT: str = """\
You are an expert software architect planning the implementation of a development task.

You will be given:
- The task description
- External context (API specs, design docs, requirements)
- Repository context (file tree, key configs, code signatures)
- Optional feedback from a previous attempt (if retrying)

Produce a clear, specific implementation plan that a coder can follow. Include:
1. Which files to create or modify (exact paths)
2. What changes to make in plain English (no code)
3. What tests to write or update
4. Risks, edge cases, and things to watch out for

Be specific and actionable. Avoid vague statements like "update the relevant files".
"""

_ARCHITECT_USER_TEMPLATE: str = """\
## Task
{task_description}

## External Context
{task_context}

## Repository Context
{repo_context}
{feedback_section}"""

_FEEDBACK_SECTION_TEMPLATE: str = """\

## Previous Attempt Feedback
{feedback}

Address the feedback above in your revised plan.\
"""


class ArchitectStage(Stage):
    """Plans the implementation for a task using a direct LLM call.

    No coding agent is involved. The output is a plain-text implementation
    plan stored as a run artifact and passed to the Coder.
    """

    def __init__(self, *, llm: LLMClient, models: ModelsConfig) -> None:
        """Initialize the Architect stage.

        Args:
            llm: LLM client satisfying the LLMClient protocol.
            models: Model configuration specifying which model to use.
        """
        self._llm = llm
        self._models = models

    @property
    def name(self) -> str:
        """Human-readable stage name."""
        return "architect"

    def execute(self, stage_input: StageInput) -> StageOutput:
        """Generate an implementation plan for the task.

        Args:
            stage_input: Pipeline stage input with task description and context.

        Returns:
            StageOutput with passed=True and the plan in output.
            The Architect always produces a plan; it never returns passed=False.
        """
        feedback_section = ""
        if stage_input.last_failure:
            feedback_section = _FEEDBACK_SECTION_TEMPLATE.format(
                feedback=stage_input.last_failure
            )

        user_prompt = _ARCHITECT_USER_TEMPLATE.format(
            task_description=stage_input.task_description,
            task_context=stage_input.task_context or "None provided.",
            repo_context=stage_input.repo_context,
            feedback_section=feedback_section,
        )

        plan = self._llm.complete(
            model=self._models.architect,
            system_prompt=_ARCHITECT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return StageOutput(
            passed=True,
            output=plan,
            escalate_to=None,
        )
