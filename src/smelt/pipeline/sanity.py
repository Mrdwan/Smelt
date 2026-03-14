"""Sanity check: run pytest on the develop branch before any LLM calls.

If any tests fail and configuration says so, a highest-priority bug ticket
is automatically created in the task store, and the pipeline is halted.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from smelt.config import SanityConfig
from smelt.db.models import ToolResult
from smelt.db.store import TaskStore
from smelt.exceptions import SanityCheckError


class SanityChecker:
    """Runs pytest on the current branch and creates a bug ticket on failure.

    This check runs before any LLM calls to ensure that the codebase
    is in a known-good state before Smelt begins work on a task.
    """

    def __init__(
        self,
        *,
        store: TaskStore,
        config: SanityConfig,
        repo_path: Path,
    ) -> None:
        """Initialize the SanityChecker.

        Args:
            store: TaskStore used to create bug tickets on failure.
            config: Sanity check configuration.
            repo_path: Root directory of the repository to test.
        """
        self._store = store
        self._config = config
        self._repo_path = repo_path

    def check(self) -> ToolResult:
        """Run pytest on the current branch.

        Returns:
            ToolResult with the pytest outcome.

        Raises:
            SanityCheckError: If tests fail (and bug ticket is created
                when create_bug_ticket_on_failure is True).
        """
        result = self._run_pytest()

        if not result.passed:
            if self._config.create_bug_ticket_on_failure:
                summary = _extract_failure_summary(result.stdout)
                self._create_bug_ticket(summary)
            raise SanityCheckError(
                "Sanity check failed: tests are failing on the current branch."
            )

        return result

    def _run_pytest(self) -> ToolResult:
        """Execute pytest and capture results."""
        try:
            proc = subprocess.run(
                ["pytest", "--tb=short", "-q"],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return ToolResult(
                tool_name="pytest",
                passed=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                return_code=proc.returncode,
            )
        except FileNotFoundError as e:
            raise SanityCheckError("pytest not found in PATH") from e

    def _create_bug_ticket(self, summary: str) -> None:
        """Create a highest-priority bug ticket in the task store.

        Args:
            summary: Extracted failure summary to attach to the ticket.
        """
        self._store.add_task(
            description=f"[BUG] Sanity check failure:\n{summary}",
            priority=self._config.bug_ticket_priority,
        )


def _extract_failure_summary(stdout: str) -> str:
    """Extract the most relevant failure lines from pytest output.

    Keeps lines containing FAILED, AssertionError, or ERROR keywords.

    Args:
        stdout: Raw pytest stdout.

    Returns:
        Condensed failure summary string.
    """
    lines = stdout.splitlines()
    failures = [
        line.strip()
        for line in lines
        if any(kw in line for kw in ("FAILED", "AssertionError", "ERROR"))
    ]
    return "\n".join(failures) if failures else "Tests failed (see full output)"
