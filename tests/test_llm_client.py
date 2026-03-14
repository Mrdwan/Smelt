"""Tests for the LiteLLMClient."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from smelt.agents.llm_client import LiteLLMClient
from smelt.exceptions import InfraError, LLMError


def _make_response(content: str | None) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_successful_completion(mocker: MagicMock) -> None:
    mocker.patch("litellm.completion", return_value=_make_response("the plan is: ..."))
    client = LiteLLMClient()
    result = client.complete(
        model="claude-opus-4-20250514",
        system_prompt="you are an architect",
        user_prompt="plan this task",
    )
    assert result == "the plan is: ..."


def test_empty_response_raises_llm_error_when_none(mocker: MagicMock) -> None:
    mocker.patch("litellm.completion", return_value=_make_response(None))
    client = LiteLLMClient()
    with pytest.raises(LLMError, match="empty response"):
        client.complete(
            model="claude-opus-4-20250514",
            system_prompt="sys",
            user_prompt="user",
        )


def test_empty_response_raises_llm_error_when_empty_string(mocker: MagicMock) -> None:
    mocker.patch("litellm.completion", return_value=_make_response(""))
    client = LiteLLMClient()
    with pytest.raises(LLMError, match="empty response"):
        client.complete(
            model="claude-opus-4-20250514",
            system_prompt="sys",
            user_prompt="user",
        )


def test_rate_limit_raises_infra_error(mocker: MagicMock) -> None:
    import litellm.exceptions

    mocker.patch(
        "litellm.completion",
        side_effect=litellm.exceptions.RateLimitError(
            "limit", llm_provider="anthropic", model="claude"
        ),
    )
    client = LiteLLMClient()
    with pytest.raises(InfraError, match="rate limited"):
        client.complete(model="m", system_prompt="s", user_prompt="u")


def test_api_connection_error_raises_infra_error(mocker: MagicMock) -> None:
    import litellm.exceptions

    mocker.patch(
        "litellm.completion",
        side_effect=litellm.exceptions.APIConnectionError(
            "conn", llm_provider="anthropic", model="claude"
        ),
    )
    client = LiteLLMClient()
    with pytest.raises(InfraError, match="connection error"):
        client.complete(model="m", system_prompt="s", user_prompt="u")


def test_authentication_error_raises_llm_error(mocker: MagicMock) -> None:
    import litellm.exceptions

    mocker.patch(
        "litellm.completion",
        side_effect=litellm.exceptions.AuthenticationError(
            "auth", llm_provider="anthropic", model="claude"
        ),
    )
    client = LiteLLMClient()
    with pytest.raises(LLMError, match="authentication"):
        client.complete(model="m", system_prompt="s", user_prompt="u")


def test_generic_exception_raises_llm_error(mocker: MagicMock) -> None:
    mocker.patch("litellm.completion", side_effect=RuntimeError("unexpected"))
    client = LiteLLMClient()
    with pytest.raises(LLMError, match="LLM call failed"):
        client.complete(model="m", system_prompt="s", user_prompt="u")


def test_correct_messages_passed_to_litellm(mocker: MagicMock) -> None:
    mock_completion = mocker.patch(
        "litellm.completion", return_value=_make_response("ok")
    )
    client = LiteLLMClient()
    client.complete(
        model="claude-sonnet-4-20250514",
        system_prompt="be helpful",
        user_prompt="do work",
        max_tokens=2048,
        temperature=0.5,
    )
    mock_completion.assert_called_once_with(
        model="claude-sonnet-4-20250514",
        messages=[
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "do work"},
        ],
        max_tokens=2048,
        temperature=0.5,
    )
