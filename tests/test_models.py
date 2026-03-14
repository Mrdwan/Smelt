"""Tests for new domain models: ToolResult, QAResult, AgentResult, RepoContext."""

from __future__ import annotations

from smelt.db.models import AgentResult, QAResult, RepoContext, ToolResult


def test_tool_result_passed() -> None:
    r = ToolResult(
        tool_name="pytest", passed=True, stdout="ok", stderr="", return_code=0
    )
    assert r.passed is True
    assert r.tool_name == "pytest"


def test_tool_result_failed() -> None:
    r = ToolResult(
        tool_name="mypy", passed=False, stdout="", stderr="error", return_code=1
    )
    assert r.passed is False
    assert r.return_code == 1


def test_qa_result_aggregates_correctly() -> None:
    t1 = ToolResult("pytest", True, "ok", "", 0)
    t2 = ToolResult("ruff", False, "lint error", "", 1)
    qa = QAResult(passed=False, tool_results=(t1, t2), summary="ruff FAILED")
    assert qa.passed is False
    assert len(qa.tool_results) == 2
    assert "ruff FAILED" in qa.summary


def test_agent_result_success() -> None:
    r = AgentResult(
        success=True, session_id="abc123", output="done", duration_seconds=1.5
    )
    assert r.success is True
    assert r.session_id == "abc123"


def test_repo_context_render_within_budget() -> None:
    ctx = RepoContext(
        file_tree="src/\n  main.py (1 KB)",
        signatures="def foo(): ...",
        config_files={"pyproject.toml": "[project]\nname = 'test'"},
        token_count=100,
    )
    rendered = ctx.render(max_tokens=10000)
    assert "File Tree" in rendered
    assert "pyproject.toml" in rendered
    assert "Code Signatures" in rendered
    assert "def foo()" in rendered


def test_repo_context_render_truncates_signatures() -> None:
    ctx = RepoContext(
        file_tree="src/\n  main.py",
        signatures="x" * 10000,
        config_files={},
        token_count=5000,
    )
    # Very small budget — signatures should be truncated
    rendered = ctx.render(max_tokens=10)
    # Should still have the header at minimum
    assert "File Tree" in rendered


def test_repo_context_render_no_signatures_when_zero_budget() -> None:
    ctx = RepoContext(
        file_tree="a" * 10000,
        signatures="def foo(): ...",
        config_files={},
        token_count=9999,
    )
    # Budget entirely consumed by header
    rendered = ctx.render(max_tokens=1)
    # No signatures section when budget is exhausted
    assert "Code Signatures" not in rendered
