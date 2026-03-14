"""QA stage: deterministic quality checks with no LLM involvement.

Runs pytest, ruff, and mypy based on configuration. Aggregates results
and produces a human-readable summary truncated for Coder retry prompts.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from smelt.config import QAConfig
from smelt.db.models import QAResult, ToolResult
from smelt.pipeline.stages import Stage, StageInput, StageOutput

_TRUNCATE_MAX_LINES: int = 50
_TRUNCATE_HALF: int = _TRUNCATE_MAX_LINES // 2


class QAStage(Stage):
    """Runs deterministic QA tools: pytest, ruff check, mypy.

    This stage never calls an LLM. Every check is a subprocess invocation
    with captured output. All results are aggregated into a QAResult.
    """

    def __init__(self, *, config: QAConfig, repo_path: Path) -> None:
        """Initialize the QA stage.

        Args:
            config: QA configuration controlling which tools run.
            repo_path: Root directory of the repository to check.
        """
        self._config = config
        self._repo_path = repo_path

    @property
    def name(self) -> str:
        """Human-readable stage name."""
        return "qa"

    def execute(self, stage_input: StageInput) -> StageOutput:
        """Run all configured QA tools and return aggregated results.

        Args:
            stage_input: Pipeline stage input (repo context used for context only).

        Returns:
            StageOutput with passed=True if all tools pass, escalate_to='coder'
            if any tool fails.
        """
        tool_results: list[ToolResult] = []

        if self._config.run_tests:
            tool_results.append(self._run_pytest())
        if self._config.run_linter:
            tool_results.append(self._run_ruff())
        if self._config.run_type_checker:
            tool_results.append(self._run_mypy())

        all_passed = all(r.passed for r in tool_results)
        qa_result = QAResult(
            passed=all_passed,
            tool_results=tuple(tool_results),
            summary=self._build_summary(tool_results),
        )

        return StageOutput(
            passed=qa_result.passed,
            output=qa_result.summary,
            escalate_to=None if qa_result.passed else "coder",
        )

    def _run_tool(self, cmd: list[str], tool_name: str) -> ToolResult:
        """Run a subprocess tool and capture output as a ToolResult.

        Args:
            cmd: The command and arguments to run.
            tool_name: Human-readable name for logging.

        Returns:
            ToolResult capturing stdout, stderr, and return code.
        """
        proc = subprocess.run(
            cmd,
            cwd=self._repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        return ToolResult(
            tool_name=tool_name,
            passed=proc.returncode == 0,
            stdout=proc.stdout,
            stderr=proc.stderr,
            return_code=proc.returncode,
        )

    def _run_pytest(self) -> ToolResult:
        """Run pytest with optional coverage flags."""
        cmd = ["pytest", "--tb=short", "-q"]
        if self._config.require_coverage:
            cmd.extend(
                [
                    "--cov",
                    "--cov-branch",
                    f"--cov-fail-under={self._config.min_coverage_percent}",
                ]
            )
        return self._run_tool(cmd, "pytest")

    def _run_ruff(self) -> ToolResult:
        """Run ruff check."""
        return self._run_tool(["ruff", "check", "."], "ruff")

    def _run_mypy(self) -> ToolResult:
        """Run mypy."""
        return self._run_tool(["mypy", "."], "mypy")

    def _build_summary(self, results: list[ToolResult]) -> str:
        """Build a human-readable summary of all tool results.

        Args:
            results: Results from all tools that ran.

        Returns:
            A summary string — 'All QA checks passed.' on success, or
            per-tool failure details on failure.
        """
        failures = [r for r in results if not r.passed]
        if not failures:
            passed_names = ", ".join(r.tool_name for r in results)
            return f"All QA checks passed. ({passed_names})"

        parts: list[str] = []
        for f in failures:
            truncated = _truncate_output(f.stdout, max_lines=_TRUNCATE_MAX_LINES)
            parts.append(f"## {f.tool_name} FAILED (exit {f.return_code})\n{truncated}")
        return "\n\n".join(parts)


def _truncate_output(output: str, *, max_lines: int) -> str:
    """Truncate tool output to the most relevant lines.

    Keeps the first half and last half of the output, inserting a marker
    in the middle. If output is within the limit, returns it unchanged.

    Args:
        output: Raw tool stdout.
        max_lines: Maximum lines to keep.

    Returns:
        Truncated output string.
    """
    lines = output.splitlines()
    if len(lines) <= max_lines:
        return output
    half = max_lines // 2
    return "\n".join([*lines[:half], "... (truncated) ...", *lines[-half:]])
