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


class AgentError(SmeltError):
    """Raised when a coding agent fails (crash, unexpected exit, etc.)."""


class AgentTimeoutError(AgentError):
    """Raised when a coding agent session exceeds its timeout."""


class LLMError(SmeltError):
    """Raised when a direct LLM API call fails."""


class InfraError(SmeltError):
    """Raised for infrastructure errors (rate limit, API down). Auto-retryable."""


class SanityCheckError(SmeltError):
    """Raised when the sanity check (pytest on develop) fails."""


class PipelineError(SmeltError):
    """Raised when the pipeline encounters an unrecoverable error."""
