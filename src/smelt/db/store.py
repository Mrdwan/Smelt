"""Data store implementation for Smelt tasks."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Sequence

from smelt.db.models import Task
from smelt.exceptions import (
    CircularDependencyError,
    InvalidStatusTransitionError,
    TaskNotFoundError,
)


class TaskStore:
    """SQLite-backed storage for tasks and their dependencies."""

    VALID_STATUSES = frozenset(
        {
            "ready",
            "blocked",
            "in-progress",
            "in-review",
            "merged",
            "failed",
            "infra-error",
        }
    )

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize the store with a database connection.

        Args:
            conn: An open SQLite connection. Note: `init_db` should have
                  been called on this connection already.
        """
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def _generate_id(self) -> str:
        """Generate a short unique ID for a task."""
        return str(uuid.uuid4())[:8]

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert a database row to a Task object."""
        return Task(
            id=row["id"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            complexity=row["complexity"],
            context=row["context"],
            context_files=row["context_files"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def add_task(
        self,
        description: str,
        priority: int = 0,
        complexity: int | None = None,
        context: str | None = None,
        context_files: str | None = None,
        depends_on: Sequence[str] | None = None,
    ) -> Task:
        """Add a new task to the roadmap.

        Args:
            description: Task description.
            priority: Execution priority (default 0).
            complexity: Estimated complexity (1-10).
            context: Optional external context text.
            context_files: Optional comma-separated file paths.
            depends_on: Optional list of task IDs this task depends on.

        Returns:
            The created Task object.

        Raises:
            TaskNotFoundError: If a dependency ID does not exist.
            CircularDependencyError: If a dependency would create a cycle.
        """
        task_id = self._generate_id()

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO tasks
                (id, description, priority, complexity, context, context_files)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, description, priority, complexity, context, context_files),
            )

            if depends_on:
                for dep_id in depends_on:
                    self.add_dependency(task_id, dep_id)

        return self.get_task(task_id)  # type: ignore[return-value] # We know it exists

    def get_task(self, task_id: str) -> Task | None:
        """Retrieve a single task by ID."""
        cursor = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_task(row)

    def list_tasks(self, status: str | None = None) -> list[Task]:
        """List tasks, optionally filtered by status.

        Results are ordered by priority (descending) and creation date.
        """
        query = "SELECT * FROM tasks"
        params: list[str] = []

        if status:
            query += " WHERE status = ?"
            params.append(status)

        query += " ORDER BY priority DESC, created_at ASC"

        cursor = self._conn.execute(query, params)
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def update_status(self, task_id: str, new_status: str) -> None:
        """Update a task's status.

        Raises:
            TaskNotFoundError: If the task does not exist.
            InvalidStatusTransitionError: If the new status is not valid.
        """
        if new_status not in self.VALID_STATUSES:
            raise InvalidStatusTransitionError(f"Invalid status: {new_status}")

        with self._conn:
            cursor = self._conn.execute(
                "UPDATE tasks SET status = ?, updated_at = datetime('now') "
                "WHERE id = ?",
                (new_status, task_id),
            )
            if cursor.rowcount == 0:
                raise TaskNotFoundError(f"Task '{task_id}' not found")

    def pick_next_task(self) -> Task | None:
        """Pick the next executable task.

        A task is executable if:
        - It is 'ready'
        - ALL of its dependencies have status 'merged'

        Ordered by priority (highest first) then creation time (oldest first).
        """
        query = """
        SELECT * FROM tasks
        WHERE status = 'ready'
          AND id NOT IN (
            SELECT task_id FROM task_dependencies
            WHERE depends_on NOT IN (
              SELECT id FROM tasks WHERE status = 'merged'
            )
          )
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
        """
        cursor = self._conn.execute(query)
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_task(row)

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency relationship between two tasks.

        Args:
            task_id: The ID of the task that depends on another.
            depends_on: The ID of the task that must be completed first.

        Raises:
            TaskNotFoundError: If either task does not exist.
            CircularDependencyError: If this relationship creates a cycle.
        """
        if not self.get_task(task_id):
            raise TaskNotFoundError(f"Task '{task_id}' not found")
        if not self.get_task(depends_on):
            raise TaskNotFoundError(f"Dependency task '{depends_on}' not found")

        if task_id == depends_on:
            raise CircularDependencyError("A task cannot depend on itself")

        # Cycle detection: check if `depends_on` ultimately depends on `task_id`
        if self._path_exists(depends_on, task_id):
            raise CircularDependencyError(
                f"Adding dependency {task_id} -> {depends_on} creates a cycle"
            )

        with self._conn:
            # Ignore if dependency already exists
            self._conn.execute(
                "INSERT OR IGNORE INTO task_dependencies (task_id, depends_on) "
                "VALUES (?, ?)",
                (task_id, depends_on),
            )

    def get_dependencies(self, task_id: str) -> list[Task]:
        """Get all tasks that the given task depends on."""
        query = """
        SELECT t.* FROM tasks t
        JOIN task_dependencies td ON t.id = td.depends_on
        WHERE td.task_id = ?
        """
        cursor = self._conn.execute(query, (task_id,))
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def _path_exists(self, start_id: str, target_id: str) -> bool:
        """BFS to check if there is a dependency path from start_id to target_id."""
        visited = set()
        queue = [start_id]

        while queue:
            current = queue.pop(0)
            if current == target_id:
                return True

            if current not in visited:
                visited.add(current)
                # Next nodes are what `current` depends on
                cursor = self._conn.execute(
                    "SELECT depends_on FROM task_dependencies WHERE task_id = ?",
                    (current,),
                )
                neighbors = [row[0] for row in cursor.fetchall()]
                queue.extend(neighbors)

        return False
