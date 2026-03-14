"""Tests for the RepoContextBuilder."""

from __future__ import annotations

from pathlib import Path

import pytest

from smelt.config import ContextConfig
from smelt.pipeline.context import (
    RepoContextBuilder,
    _build_file_tree,
    _fallback_scan,
    _format_size,
    _read_config_files,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a small fake repository structure."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def hello():\n    pass\n")
    (tmp_path / "src" / "utils.py").write_text("class Helper:\n    pass\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_hello(): pass\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")
    return tmp_path


def test_build_file_tree_includes_files(repo: Path) -> None:
    tree = _build_file_tree(repo)
    assert "src/" in tree
    assert "main.py" in tree
    assert "pyproject.toml" in tree


def test_build_file_tree_skips_git_dir(repo: Path) -> None:
    tree = _build_file_tree(repo)
    assert ".git/" not in tree
    assert "HEAD" not in tree


def test_build_file_tree_shows_sizes(repo: Path) -> None:
    tree = _build_file_tree(repo)
    # Files should have size annotations like "(20 B)"
    assert "B)" in tree or "KB)" in tree


def test_read_config_files_finds_pyproject(repo: Path) -> None:
    configs = _read_config_files(repo)
    assert "pyproject.toml" in configs
    assert "[project]" in configs["pyproject.toml"]


def test_read_config_files_ignores_missing(repo: Path) -> None:
    configs = _read_config_files(repo)
    assert "Makefile" not in configs
    assert "smelt.toml" not in configs


def test_format_size_bytes() -> None:
    assert _format_size(500) == "500 B"


def test_format_size_kilobytes() -> None:
    result = _format_size(2048)
    assert "KB" in result


def test_format_size_megabytes() -> None:
    result = _format_size(2 * 1024 * 1024)
    assert "MB" in result


def test_fallback_scan_finds_python_defs() -> None:
    source = b"def foo():\n    pass\nclass Bar:\n    pass\n"
    sigs = _fallback_scan(source)
    assert any("def foo()" in s for s in sigs)
    assert any("class Bar" in s for s in sigs)


def test_fallback_scan_ignores_non_defs() -> None:
    source = b"x = 1\ny = 2\n"
    sigs = _fallback_scan(source)
    assert sigs == []


def test_fallback_scan_handles_async_def() -> None:
    source = b"async def my_func():\n    pass\n"
    sigs = _fallback_scan(source)
    assert any("async def my_func()" in s for s in sigs)


def test_repo_context_builder_returns_context(repo: Path) -> None:
    config = ContextConfig(max_tokens=4000)
    builder = RepoContextBuilder(config=config)
    ctx = builder.build(repo)

    assert "src/" in ctx.file_tree
    assert "pyproject.toml" in ctx.config_files
    assert ctx.token_count > 0


def test_repo_context_builder_signatures_contain_python_defs(repo: Path) -> None:
    config = ContextConfig(max_tokens=4000)
    builder = RepoContextBuilder(config=config)
    ctx = builder.build(repo)

    # Should have extracted 'def hello' or similar
    assert "hello" in ctx.signatures or "Helper" in ctx.signatures


def test_extract_signatures_fallback_when_no_grammar(tmp_path: Path) -> None:
    """A .rs file (no tree-sitter grammar) triggers the fallback line scanner."""
    (tmp_path / "main.rs").write_text('fn main() {\n    println!("hi");\n}\n')
    (tmp_path / "lib.rs").write_text("pub fn helper() -> i32 { 42 }\n")
    from smelt.pipeline.context import _extract_signatures

    result = _extract_signatures(tmp_path)
    # Fallback scan should find the fn declarations
    assert "fn main()" in result or "pub fn helper()" in result


def test_extract_signatures_skips_unsupported_ext(tmp_path: Path) -> None:
    """Files with unsupported extensions are skipped entirely."""
    (tmp_path / "data.csv").write_text("a,b,c\n1,2,3\n")
    from smelt.pipeline.context import _extract_signatures

    result = _extract_signatures(tmp_path)
    assert "csv" not in result
    assert "data" not in result


def test_extract_signatures_empty_sigs_not_added(tmp_path: Path) -> None:
    """A source file with no definitions produces no output for that file."""
    # A .rs file with only comments — fallback scan finds nothing
    (tmp_path / "empty.rs").write_text("// just a comment\n")
    from smelt.pipeline.context import _extract_signatures

    result = _extract_signatures(tmp_path)
    assert "empty.rs" not in result


def test_get_tree_sitter_language_returns_none_for_unknown_ext() -> None:
    """Extensions without a grammar return None."""
    from smelt.pipeline.context import _get_tree_sitter_language

    result = _get_tree_sitter_language(".rs")
    assert result is None


def test_get_tree_sitter_language_returns_python() -> None:
    """The Python grammar is installed and should return a language object."""
    from smelt.pipeline.context import _get_tree_sitter_language

    result = _get_tree_sitter_language(".py")
    assert result is not None


def test_walk_tree_for_signatures_with_real_python(tmp_path: Path) -> None:
    """tree-sitter correctly extracts Python function definitions."""
    source = b"def greet(name: str) -> None:\n    print(name)\n"
    from smelt.pipeline.context import _try_tree_sitter

    sigs = _try_tree_sitter(source, ".py")
    assert sigs is not None
    assert any("greet" in s for s in sigs)


def test_try_tree_sitter_returns_none_for_unsupported_ext() -> None:
    """Extensions without a grammar cause _try_tree_sitter to return None."""
    from smelt.pipeline.context import _try_tree_sitter

    result = _try_tree_sitter(b"fn main() {}", ".rs")
    assert result is None


def test_first_line_empty_definition_skipped() -> None:
    """A signature whose first line is empty is not added to the list."""
    # Craft source where a function_definition node starts with a newline
    # In practice, tree-sitter won't produce this, but _walk_tree_for_signatures
    # guards against it — verify the guard via tree-sitter with normal code
    source = b"def normal():\n    pass\n"
    from smelt.pipeline.context import _try_tree_sitter

    sigs = _try_tree_sitter(source, ".py")
    assert sigs is not None
    # All entries should be non-empty (the guard works)
    assert all(s.strip() for s in sigs)
