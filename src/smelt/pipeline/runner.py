"""Pipeline runner: orchestrates the full task execution pipeline.

The PipelineRunner ties together all stages: sanity check, repo context,
architect, coder, and QA. It manages status transitions, retry loops,
and error classification (task error vs infra error).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from smelt.agents.protocols import CodingAgent, LLMClient
from smelt.config import SmeltConfig
from smelt.db.models import Task
from smelt.db.store import TaskStore
from smelt.exceptions import AgentError, InfraError, LLMError, SanityCheckError
from smelt.git import GitOps
from smelt.pipeline.architect import ArchitectStage
from smelt.pipeline.coder import CoderStage
from smelt.pipeline.context import RepoContextBuilder
from smelt.pipeline.qa import QAStage
from smelt.pipeline.sanity import SanityChecker
from smelt.pipeline.stages import StageInput

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    """Final result of a pipeline run.

    Attributes:
        task_id: The ID of the task that was run (empty if no task found).
        success: True if the pipeline completed all stages successfully.
        stage_reached: The last stage that ran (for debugging).
        message: Human-readable outcome message.
    """

    task_id: str
    success: bool
    stage_reached: str
    message: str


class PipelineRunner:
    """Executes the full pipeline for a single task.

    All dependencies are injected. The runner has no knowledge of which
    concrete LLM provider or coding agent is in use.
    """

    def __init__(
        self,
        *,
        config: SmeltConfig,
        store: TaskStore,
        git: GitOps,
        llm: LLMClient,
        agent: CodingAgent,
        repo_path: Path,
    ) -> None:
        """Initialize the pipeline runner.

        Args:
            config: Full Smelt configuration.
            store: Task store for status updates and bug ticket creation.
            git: Git operations wrapper.
            llm: LLM client for Architect and future LLM stages.
            agent: Coding agent for Coder and future agent stages.
            repo_path: Absolute path to the repository root.
        """
        self._config = config
        self._store = store
        self._git = git
        self._llm = llm
        self._agent = agent
        self._repo_path = repo_path

    def run(self, task: Task | None = None) -> PipelineResult:
        """Execute the pipeline for a task.

        If no task is provided, picks the next ready task from the store.
        Handles all error classification and status transitions.

        Args:
            task: Optional specific task to run. If None, picks the next ready one.

        Returns:
            PipelineResult describing the outcome.
        """
        # 1. Pick task
        if task is None:
            task = self._store.pick_next_task()
            if task is None:
                return PipelineResult(
                    task_id="",
                    success=False,
                    stage_reached="pick",
                    message="No ready tasks found.",
                )

        # 2. Mark in-progress atomically
        self._store.update_status(task.id, "in-progress")

        try:
            return self._execute(task)
        except SanityCheckError as e:
            # Sanity check failed: revert task to ready, a bug ticket was created
            self._store.update_status(task.id, "ready")
            logger.warning("Sanity check failed for task %s: %s", task.id, e)
            return PipelineResult(
                task_id=task.id,
                success=False,
                stage_reached="sanity",
                message=str(e),
            )
        except InfraError as e:
            # Transient infra error: mark infra-error for auto-retry
            self._store.update_status(task.id, "infra-error")
            logger.error("Infra error for task %s: %s", task.id, e)
            return PipelineResult(
                task_id=task.id,
                success=False,
                stage_reached="pipeline",
                message=str(e),
            )
        except (AgentError, LLMError) as e:
            # Task-level error: needs human attention
            self._store.update_status(task.id, "failed")
            logger.error("Task error for task %s: %s", task.id, e)
            return PipelineResult(
                task_id=task.id,
                success=False,
                stage_reached="pipeline",
                message=str(e),
            )

    def _execute(self, task: Task) -> PipelineResult:
        """Run the pipeline stages for a task.

        Args:
            task: The task to execute.

        Returns:
            PipelineResult from the final stage outcome.
        """
        # 3. Sanity check on the base branch
        self._run_sanity_check(task)

        # 4. Create task branch
        self._git.create_branch(task.id)
        logger.info("Created branch for task %s", task.id)

        # 5. Build repo context (shared across all stages in this run)
        context_builder = RepoContextBuilder(config=self._config.context)
        repo_context = context_builder.build(self._repo_path)
        rendered = repo_context.render(self._config.context.max_tokens)

        # 6. Architect: plan the implementation
        architect = ArchitectStage(llm=self._llm, models=self._config.models)
        arch_input = StageInput(
            task_description=task.description,
            task_context=task.context,
            repo_context=rendered,
            plan=None,
            last_failure=None,
        )
        arch_output = architect.execute(arch_input)
        plan = arch_output.output
        logger.info("Architect produced plan for task %s", task.id)

        # 7. Coder + QA retry loop
        coder = CoderStage(
            agent=self._agent,
            config=self._config.coding,
            working_dir=str(self._repo_path),
        )
        qa = QAStage(config=self._config.qa, repo_path=self._repo_path)

        last_failure: str | None = None
        max_attempts = self._config.coding.max_retries + 1

        for attempt in range(max_attempts):
            logger.info(
                "Coder attempt %d/%d for task %s", attempt + 1, max_attempts, task.id
            )
            coder_input = StageInput(
                task_description=task.description,
                task_context=task.context,
                repo_context=rendered,
                plan=plan,
                last_failure=last_failure,
            )
            coder.execute(coder_input)

            qa_input = StageInput(
                task_description=task.description,
                task_context=task.context,
                repo_context=rendered,
                plan=plan,
                last_failure=None,
            )
            qa_output = qa.execute(qa_input)

            if qa_output.passed:
                logger.info("QA passed for task %s", task.id)
                return PipelineResult(
                    task_id=task.id,
                    success=True,
                    stage_reached="qa",
                    message="All QA checks passed. Ready for review.",
                )

            last_failure = qa_output.output
            logger.info(
                "QA failed (attempt %d/%d) for task %s",
                attempt + 1,
                max_attempts,
                task.id,
            )

        # All retries exhausted
        self._store.update_status(task.id, "failed")
        return PipelineResult(
            task_id=task.id,
            success=False,
            stage_reached="qa",
            message=f"QA failed after {max_attempts} attempt(s). Task marked failed.",
        )

    def _run_sanity_check(self, task: Task) -> None:
        """Checkout the base branch, pull, and run the sanity check.

        Args:
            task: The task being processed (used for log context only).

        Raises:
            SanityCheckError: If tests on the base branch are failing.
        """
        logger.info(
            "Running sanity check on %s for task %s",
            self._config.git.base_branch,
            task.id,
        )
        self._git.checkout_branch(self._config.git.base_branch)
        self._git.pull(self._config.git.base_branch)

        checker = SanityChecker(
            store=self._store,
            config=self._config.sanity,
            repo_path=self._repo_path,
        )
        checker.check()
