"""Tests for the CodingAgent and LLMClient protocol definitions."""

from __future__ import annotations

from smelt.agents.protocols import CodingAgent, LLMClient
from smelt.db.models import AgentResult


class _FakeCodingAgent:
    """Minimal implementation satisfying CodingAgent protocol."""

    def run_session(
        self,
        *,
        prompt: str,
        working_dir: str,
        timeout_seconds: int,
        read_only: bool = False,
    ) -> AgentResult:
        return AgentResult(
            success=True, session_id="fake", output=prompt, duration_seconds=0.0
        )


class _FakeLLMClient:
    """Minimal implementation satisfying LLMClient protocol."""

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        return f"response:{user_prompt}"


def test_coding_agent_protocol_satisfied() -> None:
    agent: CodingAgent = _FakeCodingAgent()
    result = agent.run_session(
        prompt="do work",
        working_dir="/tmp",
        timeout_seconds=60,
    )
    assert result.success is True
    assert result.output == "do work"


def test_coding_agent_read_only_flag() -> None:
    agent: CodingAgent = _FakeCodingAgent()
    result = agent.run_session(
        prompt="read only",
        working_dir="/tmp",
        timeout_seconds=30,
        read_only=True,
    )
    assert result.success is True


def test_llm_client_protocol_satisfied() -> None:
    llm: LLMClient = _FakeLLMClient()
    result = llm.complete(
        model="claude-opus-4-20250514",
        system_prompt="you are helpful",
        user_prompt="plan this",
    )
    assert result == "response:plan this"


def test_coding_agent_isinstance_check() -> None:
    assert isinstance(_FakeCodingAgent(), CodingAgent)


def test_llm_client_isinstance_check() -> None:
    assert isinstance(_FakeLLMClient(), LLMClient)
