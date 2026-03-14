"""Protocol definitions for coding agents and LLM clients.

All pipeline stages depend on these protocols, never on concrete implementations.
Swapping coding agents (e.g. Goose → Aider) requires only a new adapter file
and a one-line change at the CLI wiring point.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from smelt.db.models import AgentResult


@runtime_checkable
class CodingAgent(Protocol):
    """Protocol for coding agents that can read/write files and execute code.

    Implementations: GooseAdapter, and any future adapters.
    The pipeline stages depend on this protocol, never on a concrete agent.
    """

    def run_session(
        self,
        *,
        prompt: str,
        working_dir: str,
        timeout_seconds: int,
        read_only: bool = False,
    ) -> AgentResult:
        """Run a headless coding agent session.

        Args:
            prompt: The full prompt/instructions for the agent.
            working_dir: The directory the agent should operate in.
            timeout_seconds: Maximum seconds before the session is killed.
            read_only: If True, the agent must not modify any files.

        Returns:
            AgentResult with the session outcome.

        Raises:
            AgentError: If the agent crashes or fails to start.
            AgentTimeoutError: If the session exceeds timeout_seconds.
        """
        ...  # pragma: no cover


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for direct LLM calls (chat completion, no coding agent).

    Implementations: LiteLLMClient, and any future adapters.
    Used by Architect, QC, and Decomposer stages.
    """

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """Send a chat completion request and return the response text.

        Args:
            model: The model identifier (e.g. 'claude-opus-4-20250514').
            system_prompt: The system message.
            user_prompt: The user message.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 = deterministic).

        Returns:
            The model's response as a plain string.

        Raises:
            LLMError: If the API call fails.
            InfraError: If the failure is transient (rate limit, API down).
        """
        ...  # pragma: no cover
