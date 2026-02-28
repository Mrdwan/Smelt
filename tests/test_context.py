from pathlib import Path

import pytest

from smelt.config import Settings
from smelt.context import build_context


@pytest.fixture
def memory_dir(tmp_path: Path) -> Path:
    return tmp_path / "memory"


@pytest.fixture(autouse=True)
def use_tmp_memory(memory_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_settings = Settings(_env_file=None, memory=memory_dir)
    monkeypatch.setattr("smelt.context.settings", fake_settings)


def test_returns_empty_string_when_no_memory_files_exist() -> None:
    result = build_context()

    assert result == ""


def test_architecture_included_when_present(memory_dir: Path) -> None:
    memory_dir.mkdir(parents=True)
    (memory_dir / "ARCHITECTURE.md").write_text("Monolith service")

    result = build_context()

    assert "## ARCHITECTURE.md" in result
    assert "Monolith service" in result


def test_decisions_included_when_present(memory_dir: Path) -> None:
    memory_dir.mkdir(parents=True)
    (memory_dir / "DECISIONS.md").write_text("Use SQLite for storage")

    result = build_context()

    assert "## DECISIONS.md" in result
    assert "Use SQLite for storage" in result


def test_only_existing_files_are_included(memory_dir: Path) -> None:
    memory_dir.mkdir(parents=True)
    (memory_dir / "DECISIONS.md").write_text("Postgres over MySQL")

    result = build_context()

    assert "## DECISIONS.md" in result
    assert "## ARCHITECTURE.md" not in result


def test_all_memory_files_included(memory_dir: Path) -> None:
    memory_dir.mkdir(parents=True)
    (memory_dir / "ARCHITECTURE.md").write_text("Layered architecture")
    (memory_dir / "DECISIONS.md").write_text("Postgres over MySQL")

    result = build_context()

    assert "## ARCHITECTURE.md" in result
    assert "## DECISIONS.md" in result


def test_sections_separated_by_divider(memory_dir: Path) -> None:
    memory_dir.mkdir(parents=True)
    (memory_dir / "ARCHITECTURE.md").write_text("Microservices")
    (memory_dir / "DECISIONS.md").write_text("Event sourcing")

    result = build_context()

    assert "\n\n---\n\n" in result


def test_file_content_is_stripped(memory_dir: Path) -> None:
    memory_dir.mkdir(parents=True)
    (memory_dir / "DECISIONS.md").write_text("\n\n  Use SQLite  \n\n")

    result = build_context()

    assert "  Use SQLite  " not in result
    assert "Use SQLite" in result


def test_custom_context_files_from_settings(
    memory_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memory_dir.mkdir(parents=True)
    (memory_dir / "CUSTOM.md").write_text("Custom content")

    fake_settings = Settings(_env_file=None, memory=memory_dir, context_files=["CUSTOM.md"])
    monkeypatch.setattr("smelt.context.settings", fake_settings)

    result = build_context()

    assert "## CUSTOM.md" in result
    assert "Custom content" in result
    assert "## ARCHITECTURE.md" not in result
    assert "## DECISIONS.md" not in result
