from pathlib import Path

from pytest import MonkeyPatch

from smelt.config import Settings


def test_defaults(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SMELT_MODEL", raising=False)
    monkeypatch.delenv("SMELT_LOADER_MODEL", raising=False)
    monkeypatch.delenv("SMELT_LOADER_API_KEY", raising=False)
    monkeypatch.delenv("SMELT_PROJECT", raising=False)
    monkeypatch.delenv("SMELT_MEMORY", raising=False)
    monkeypatch.delenv("SMELT_CONTEXT_FILES", raising=False)
    monkeypatch.delenv("SMELT_ROADMAP_DB", raising=False)

    s = Settings(_env_file=None)

    assert s.model == "anthropic/claude-sonnet-4-6"
    assert s.loader_model == "anthropic/claude-haiku-4-5-20251001"
    assert s.loader_api_key is None
    assert s.project == Path(".")
    assert s.memory == Path("memory")
    assert s.context_files == ["ARCHITECTURE.md", "DECISIONS.md"]
    assert s.roadmap_db == "roadmap.db"


def test_model_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_MODEL", "openai/gpt-4o")
    monkeypatch.delenv("SMELT_PROJECT", raising=False)
    monkeypatch.delenv("SMELT_MEMORY", raising=False)

    s = Settings(_env_file=None)

    assert s.model == "openai/gpt-4o"


def test_project_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SMELT_MODEL", raising=False)
    monkeypatch.setenv("SMELT_PROJECT", "/home/user/myproject")
    monkeypatch.delenv("SMELT_MEMORY", raising=False)

    s = Settings(_env_file=None)

    assert s.project == Path("/home/user/myproject")


def test_memory_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SMELT_MODEL", raising=False)
    monkeypatch.delenv("SMELT_PROJECT", raising=False)
    monkeypatch.setenv("SMELT_MEMORY", "custom_memory")

    s = Settings(_env_file=None)

    assert s.memory == Path("custom_memory")


def test_all_fields_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_MODEL", "openai/gpt-4o")
    monkeypatch.setenv("SMELT_PROJECT", "/tmp/project")
    monkeypatch.setenv("SMELT_MEMORY", "my_memory")

    s = Settings(_env_file=None)

    assert s.model == "openai/gpt-4o"
    assert s.project == Path("/tmp/project")
    assert s.memory == Path("my_memory")


def test_project_and_memory_are_path_types_by_default(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SMELT_MODEL", raising=False)
    monkeypatch.delenv("SMELT_PROJECT", raising=False)
    monkeypatch.delenv("SMELT_MEMORY", raising=False)

    s = Settings(_env_file=None)

    assert isinstance(s.project, Path)
    assert isinstance(s.memory, Path)


def test_project_string_is_coerced_to_path(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_PROJECT", "/some/path")

    s = Settings(_env_file=None)

    assert isinstance(s.project, Path)


def test_memory_string_is_coerced_to_path(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_MEMORY", "some/relative/path")

    s = Settings(_env_file=None)

    assert isinstance(s.memory, Path)


def test_relative_paths_remain_relative(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_PROJECT", "relative/project")
    monkeypatch.setenv("SMELT_MEMORY", "relative/memory")

    s = Settings(_env_file=None)

    assert not s.project.is_absolute()
    assert not s.memory.is_absolute()


def test_env_file_loading(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SMELT_MODEL", raising=False)
    monkeypatch.delenv("SMELT_PROJECT", raising=False)
    monkeypatch.delenv("SMELT_MEMORY", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "SMELT_MODEL=anthropic/claude-opus-4-6\n"
        "SMELT_PROJECT=/tmp/test_project\n"
        "SMELT_MEMORY=test_memory\n"
    )

    s = Settings(_env_file=env_file)

    assert s.model == "anthropic/claude-opus-4-6"
    assert s.project == Path("/tmp/test_project")
    assert s.memory == Path("test_memory")


def test_env_var_overrides_env_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("SMELT_MODEL=anthropic/claude-opus-4-6\n")

    monkeypatch.setenv("SMELT_MODEL", "openai/gpt-4o")

    s = Settings(_env_file=env_file)

    assert s.model == "openai/gpt-4o"


def test_missing_env_file_falls_back_to_defaults(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SMELT_MODEL", raising=False)
    monkeypatch.delenv("SMELT_PROJECT", raising=False)
    monkeypatch.delenv("SMELT_MEMORY", raising=False)

    s = Settings(_env_file=tmp_path / "nonexistent.env")

    assert s.model == "anthropic/claude-sonnet-4-6"
    assert s.project == Path(".")
    assert s.memory == Path("memory")


def test_extra_env_vars_are_ignored(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_UNKNOWN_FIELD", "some_value")

    s = Settings(_env_file=None)

    assert not hasattr(s, "unknown_field")


def test_non_prefixed_vars_do_not_affect_model(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SMELT_MODEL", raising=False)
    monkeypatch.setenv("MODEL", "should-be-ignored")

    s = Settings(_env_file=None)

    assert s.model == "anthropic/claude-sonnet-4-6"


def test_non_prefixed_vars_do_not_affect_project(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SMELT_PROJECT", raising=False)
    monkeypatch.setenv("PROJECT", "/should/be/ignored")

    s = Settings(_env_file=None)

    assert s.project == Path(".")


def test_context_files_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_CONTEXT_FILES", '["CUSTOM.md","NOTES.md"]')

    s = Settings(_env_file=None)

    assert s.context_files == ["CUSTOM.md", "NOTES.md"]


def test_context_files_is_a_list(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SMELT_CONTEXT_FILES", raising=False)

    s = Settings(_env_file=None)

    assert isinstance(s.context_files, list)


def test_roadmap_db_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_ROADMAP_DB", "custom.db")

    s = Settings(_env_file=None)

    assert s.roadmap_db == "custom.db"


def test_loader_model_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_LOADER_MODEL", "deepseek/deepseek-chat")

    s = Settings(_env_file=None)

    assert s.loader_model == "deepseek/deepseek-chat"


def test_loader_api_key_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SMELT_LOADER_API_KEY", "sk-test-key")

    s = Settings(_env_file=None)

    assert s.loader_api_key == "sk-test-key"


def test_loader_api_key_defaults_to_none(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SMELT_LOADER_API_KEY", raising=False)

    s = Settings(_env_file=None)

    assert s.loader_api_key is None
