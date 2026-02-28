# Architecture

## Overview

Smelt is a CLI tool that manages a development roadmap and drives AI coding agents step by step. It reads a SQLite-backed ordered list of tasks, hands each one to an agent, and tracks completion.

---

## Source layout

```
src/smelt/
├── cli.py               # Typer CLI entry point — all commands live here
├── config.py            # pydantic-settings config, reads from .env
├── exceptions.py        # All custom exception types
├── context.py           # Context file loading for agents
├── agents/
│   ├── base.py          # Abstract Agent interface
│   ├── aider.py         # Aider implementation of Agent
│   └── plan_parser.py   # LLM-powered plan-to-steps parser (uses litellm)
└── roadmap/
    ├── base.py          # Abstract RoadmapStorage interface + Step dataclass
    └── sqlite.py        # SQLite implementation of RoadmapStorage
```

---

## Components

### CLI (`cli.py`)
Entry point for all user interaction. Each command is a standalone Typer function. The CLI wires together config, storage, and agents — it owns no logic of its own.

Commands: `load`, `add`, `next`, `done`, `reset`, `remove`, `status`

### Config (`config.py`)
Single `Settings` object instantiated at module load. Reads from environment variables (`SMELT_` prefix) or a `.env` file in the current working directory. `db_path` is a derived `@property` (not directly configurable).

### Roadmap storage (`roadmap/`)
Abstract base class `RoadmapStorage` implements the context manager protocol (`__enter__`/`__exit__`). `SQLiteRoadmapStorage` is the only concrete implementation. Steps are ordered by insertion (SQLite `AUTOINCREMENT` id). `next_step()` returns the lowest-id undone step.

**Schema:**
```sql
CREATE TABLE steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    done        BOOLEAN NOT NULL DEFAULT 0
)
```

### Agents (`agents/`)
Abstract `Agent` interface with a single method: `run(message, context_files) -> bool`. Returns `True` on success, `False` on failure. `AiderAgent` is the default implementation — it shells out to the `aider` CLI.

### Plan parser (`agents/plan_parser.py`)
`PlanParserAgent` uses litellm to call any LLM and extract a structured list of `ParsedStep(description, done)` objects from freeform plan text. litellm is imported lazily (inside `parse()`) to avoid slow startup on commands that don't need it.

---

## Data flow

```
smelt load plan.md
  → read file
  → PlanParserAgent.parse() → litellm → LLM → list[ParsedStep]
  → SQLiteRoadmapStorage.add_step() for each step

smelt next
  → SQLiteRoadmapStorage.next_step() → Step
  → confirm with user
  → AiderAgent.run(step.description, context_files) → bool
  → SQLiteRoadmapStorage.mark_done() on success
```

---

## Key constraints

- All storage is local SQLite — no network, no server.
- Agent interface is intentionally minimal: one method, bool return.
- litellm is a lazy import; only `smelt load` pays the startup cost.
- Config is read once at process start from CWD `.env`.
