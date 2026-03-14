"""Tests for the extended exception hierarchy."""

from __future__ import annotations

from smelt.exceptions import (
    AgentError,
    AgentTimeoutError,
    InfraError,
    LLMError,
    PipelineError,
    SanityCheckError,
    SmeltError,
)


def test_agent_error_is_smelt_error() -> None:
    err = AgentError("boom")
    assert isinstance(err, SmeltError)
    assert str(err) == "boom"


def test_agent_timeout_error_is_agent_error() -> None:
    err = AgentTimeoutError("timed out")
    assert isinstance(err, AgentError)
    assert isinstance(err, SmeltError)


def test_llm_error_is_smelt_error() -> None:
    err = LLMError("api fail")
    assert isinstance(err, SmeltError)


def test_infra_error_is_smelt_error() -> None:
    err = InfraError("rate limited")
    assert isinstance(err, SmeltError)


def test_sanity_check_error_is_smelt_error() -> None:
    err = SanityCheckError("tests failing")
    assert isinstance(err, SmeltError)


def test_pipeline_error_is_smelt_error() -> None:
    err = PipelineError("unrecoverable")
    assert isinstance(err, SmeltError)
