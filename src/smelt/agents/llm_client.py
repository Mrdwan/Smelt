"""LiteLLM-based implementation of the LLMClient protocol.

Uses litellm for multi-provider support: swapping between Anthropic, OpenAI,
and other providers is a model string change, not a code change.
"""

from __future__ import annotations

import litellm
import litellm.exceptions

from smelt.exceptions import InfraError, LLMError


class LiteLLMClient:
    """LLM client that uses litellm for chat completions.

    Satisfies the LLMClient protocol. All pipeline stages that need an LLM
    (Architect, QC, Decomposer) accept the protocol — this is one implementation.
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
        """Send a chat completion request via litellm.

        Args:
            model: The model identifier (e.g. 'claude-opus-4-20250514').
            system_prompt: The system message.
            user_prompt: The user message.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 = most deterministic).

        Returns:
            The model's response as a plain string.

        Raises:
            InfraError: For transient failures (rate limit, API unavailable).
            LLMError: For all other API failures or empty responses.
        """
        try:
            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except litellm.exceptions.RateLimitError as e:
            raise InfraError(f"LLM rate limited: {e}") from e
        except litellm.exceptions.APIConnectionError as e:
            raise InfraError(f"LLM API connection error: {e}") from e
        except litellm.exceptions.AuthenticationError as e:
            raise LLMError(f"LLM authentication failed: {e}") from e
        except Exception as e:
            raise LLMError(f"LLM call failed: {e}") from e

        raw = response.choices[0].message.content
        content: str = raw if isinstance(raw, str) else ""
        if not content:
            raise LLMError("LLM returned an empty response")
        return content
