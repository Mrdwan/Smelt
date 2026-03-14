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
