"""Custom exceptions for the Smelt orchestrator."""

from __future__ import annotations


class SmeltError(Exception):
    """Base exception for all Smelt-specific errors."""


class ConfigError(SmeltError):
    """Raised when there is an error in the configuraton file."""


class GitError(SmeltError):
    """Raised when a Git operation fails."""


class TaskNotFoundError(SmeltError):
    """Raised when attempting to access a task ID that does not exist."""


class CircularDependencyError(SmeltError):
    """Raised when a task dependency would create a cycle."""


class InvalidStatusTransitionError(SmeltError):
    """Raised when attempting an invalid task status transition."""
