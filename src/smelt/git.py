"""Git operations wrapper for the Smelt orchestrator."""

from __future__ import annotations

import subprocess
from pathlib import Path

from smelt.config import GitConfig
from smelt.exceptions import GitError


class GitOps:
    """Wrapper for git commands executed via subprocess."""

    def __init__(self, repo_path: Path, config: GitConfig) -> None:
        """Initialize GitOps with a repository path and configuration."""
        self.repo_path = repo_path
        self.config = config

    def _run(self, *args: str) -> str:
        """Run a git command safely and return stripped stdout."""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else e.stdout.strip()
            raise GitError(f"Git command failed: {' '.join(args)}\n{error_msg}") from e

    def checkout_branch(self, branch_name: str) -> None:
        """Checkout an existing branch."""
        self._run("checkout", branch_name)

    def create_branch(self, task_slug: str) -> str:
        """Create a new task branch from the base branch.

        Args:
            task_slug: The unique slug for the task (e.g., '1a2b3c4d').

        Returns:
            The full name of the created branch.
        """
        branch_name = f"{self.config.branch_prefix}{task_slug}"
        self._run("checkout", "-b", branch_name, self.config.base_branch)
        return branch_name

    def pull(self, branch: str | None = None) -> None:
        """Pull the latest changes from origin for the given branch (or current)."""
        if branch:
            self._run("pull", "origin", branch)
        else:
            self._run("pull")

    def add_all(self) -> None:
        """Stage all modifications."""
        self._run("add", ".")

    def commit(self, message: str) -> None:
        """Commit staged changes with a message."""
        self._run("commit", "-m", message)

    def push(self, branch: str) -> None:
        """Push a branch to origin and set upstream."""
        self._run("push", "-u", "origin", branch)

    def current_branch(self) -> str:
        """Get the name of the currently checked out branch."""
        return self._run("branch", "--show-current")

    def branch_exists(self, name: str) -> bool:
        """Check whether a branch exists locally."""
        try:
            self._run("show-ref", "--verify", "--quiet", f"refs/heads/{name}")
            return True
        except GitError:
            return False

    def delete_branch(self, name: str) -> None:
        """Delete a local branch."""
        self._run("branch", "-D", name)
