"""Coder stage: coding agent writes the implementation based on the architect plan.

The coder invokes a CodingAgent (e.g. Goose) with full file access. It
receives the architect plan and any failure feedback from a prior QA run.
"""

from __future__ import annotations

from smelt.agents.protocols import CodingAgent
from smelt.config import CodingConfig
from smelt.pipeline.stages import Stage, StageInput, StageOutput

_CODER_PROMPT_TEMPLATE: str = """\
## Task
{task_description}

## Implementation Plan
{plan}

## Repository Context
{repo_context}
{failure_section}
## Instructions
Implement the plan above. Follow it precisely. Write all code, tests, and
any configuration changes described. When done, signal completion by stopping.
Do not summarise or explain — just implement.
"""

_FAILURE_SECTION_TEMPLATE: str = """\

## Previous QA Failure — Fix These Issues
{failure}

"""


class CoderStage(Stage):
    """Writes code via a coding agent following the architect's plan.

    The stage is agnostic to the underlying coding agent — it depends on
    the CodingAgent protocol only. Swapping Goose for another agent requires
    no changes here.
    """

    def __init__(
        self,
        *,
        agent: CodingAgent,
        config: CodingConfig,
        working_dir: str,
    ) -> None:
        """Initialize the Coder stage.

        Args:
            agent: Coding agent satisfying the CodingAgent protocol.
            config: Coding configuration (timeout, retries).
            working_dir: Directory the agent should operate in (repo root).
        """
        self._agent = agent
        self._config = config
        self._working_dir = working_dir

    @property
    def name(self) -> str:
        """Human-readable stage name."""
        return "coder"

    def execute(self, stage_input: StageInput) -> StageOutput:
        """Run the coding agent to implement the plan.

        Args:
            stage_input: Pipeline stage input with task, plan, and prior failures.

        Returns:
            StageOutput with the agent's output and pass/fail status.
        """
        failure_section = ""
        if stage_input.last_failure:
            failure_section = _FAILURE_SECTION_TEMPLATE.format(
                failure=stage_input.last_failure
            )

        prompt = _CODER_PROMPT_TEMPLATE.format(
            task_description=stage_input.task_description,
            plan=stage_input.plan or "No plan provided.",
            repo_context=stage_input.repo_context,
            failure_section=failure_section,
        )

        result = self._agent.run_session(
            prompt=prompt,
            working_dir=self._working_dir,
            timeout_seconds=self._config.timeout_seconds,
            read_only=False,
        )

        return StageOutput(
            passed=result.success,
            output=result.output,
            escalate_to=None,
        )
