"""Data models for the Smelt orchestrator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    """A single development task in the Smelt roadmap.

    Attributes:
        id: Unique identifier for the task.
        description: Plain text explanation of what the task entails.
        status: Current state ('ready', 'blocked', 'in-progress', 'in-review',
            'merged', 'failed', 'infra-error').
        priority: Execution priority (higher executes earlier).
        complexity: Estimated complexity (1-10) for logging/observability.
        context: Optional external text context (e.g. API spec).
        context_files: Comma-separated paths to relevant files.
        created_at: ISO8601 timestamp of creation.
        updated_at: ISO8601 timestamp of last update.
    """

    id: str
    description: str
    status: str
    priority: int
    complexity: int | None
    context: str | None
    context_files: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class TaskDependency:
    """A direct dependency edge between two tasks.

    Attributes:
        task_id: The ID of the task that has the dependency.
        depends_on: The ID of the task that must be completed first.
    """

    task_id: str
    depends_on: str


@dataclass(frozen=True)
class ToolResult:
    """Result from a single deterministic tool run.

    Attributes:
        tool_name: Name of the tool run (e.g. 'pytest', 'ruff', 'mypy').
        passed: True if the tool exited with return code 0.
        stdout: Captured standard output.
        stderr: Captured standard error.
        return_code: The process exit code.
    """

    tool_name: str
    passed: bool
    stdout: str
    stderr: str
    return_code: int


@dataclass(frozen=True)
class QAResult:
    """Aggregated result from the QA stage.

    Attributes:
        passed: True if all tools passed.
        tool_results: Results from each individual tool.
        summary: Human-readable summary of failures (or success message).
    """

    passed: bool
    tool_results: tuple[ToolResult, ...]
    summary: str


@dataclass(frozen=True)
class AgentResult:
    """Result from a coding agent session.

    Attributes:
        success: True if the agent completed without error.
        session_id: Unique identifier for this agent session.
        output: The agent's final output text.
        duration_seconds: Wall-clock time the session took.
    """

    success: bool
    session_id: str
    output: str
    duration_seconds: float


@dataclass(frozen=True)
class RepoContext:
    """Repository context built from tree-sitter analysis.

    Attributes:
        file_tree: Indented file listing with sizes.
        signatures: Extracted function/class signatures from all source files.
        config_files: Contents of key config files (filename -> content).
        token_count: Estimated token count of the full rendered context.
    """

    file_tree: str
    signatures: str
    config_files: dict[str, str]
    token_count: int

    def render(self, max_tokens: int) -> str:
        """Render context within a token budget.

        Includes file tree and config files always, then signatures up to budget.

        Args:
            max_tokens: Maximum estimated tokens for the rendered output.

        Returns:
            A string containing the repository context within the budget.
        """
        config_section = "\n".join(
            f"### {name}\n```\n{content}\n```"
            for name, content in self.config_files.items()
        )
        header = (
            f"## File Tree\n{self.file_tree}\n\n## Key Config Files\n{config_section}"
        )

        # Budget signatures
        header_tokens = len(header) // 4
        remaining = max_tokens - header_tokens
        if remaining <= 0:
            return header

        sig_chars = remaining * 4
        signatures = (
            self.signatures[:sig_chars] + "\n... (truncated)"
            if len(self.signatures) > sig_chars
            else self.signatures
        )
        return f"{header}\n\n## Code Signatures\n{signatures}"
