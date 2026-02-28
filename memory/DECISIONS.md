# Decisions

## SQLite for roadmap storage

**Decision:** Use SQLite via the stdlib `sqlite3` module.

**Rationale:** No server, no dependencies, no setup. The roadmap is a simple ordered list that lives alongside the project. A file is enough. Switching to a different backend is easy through the `RoadmapStorage` abstract base.

---

## Abstract base classes for storage and agents

**Decision:** `RoadmapStorage` and `Agent` are abstract base classes, not concrete singletons.

**Rationale:** Keeps the CLI decoupled from any specific implementation. SQLite can be swapped for another storage engine; Aider can be swapped for another agent — without touching CLI code. Also makes unit testing straightforward with mocks.

---

## litellm for plan parsing

**Decision:** Use litellm instead of a provider-specific SDK (e.g. `anthropic`, `openai`).

**Rationale:** The loader model is intentionally cheap and interchangeable — users may want Deepseek, Groq, Ollama, or anything else. litellm gives a single uniform API over all providers. A cheap/fast model is sufficient for extracting structured steps from text.

---

## Lazy import of litellm

**Decision:** `import litellm` lives inside `PlanParserAgent.parse()`, not at the top of the module.

**Rationale:** litellm has a very slow import time (it loads dozens of provider SDKs at startup). Importing it at module level caused every `smelt` invocation — including instant commands like `smelt status` — to pay a multi-second startup cost. Lazy import means only `smelt load` pays that cost.

---

## Config from CWD `.env`

**Decision:** Settings are read from a `.env` file in the current working directory, not from a fixed global path like `~/.config/smelt/.env`.

**Rationale:** Smelt is used from a project directory. Each project can have its own `.env` with its own model, memory path, and API key. This is consistent with how most CLI dev tools handle project-local config (e.g. `.env` for Docker Compose, dotenv for Node projects).

---

## `db_path` as a derived property

**Decision:** `db_path` is a `@property` on `Settings` computed from `memory / roadmap_db`, not a separate env var.

**Rationale:** It's a derived value, not an independent configuration knob. Adding a `SMELT_DB_PATH` env var would be redundant — users control the path through `SMELT_MEMORY` and `SMELT_ROADMAP_DB` separately. Keeping it as a property avoids surprises from partially-configured combinations.

---

## `num_retries` delegated to litellm

**Decision:** Retry logic for the LLM call is handled by passing `num_retries` to `litellm.completion()`, not by a custom retry loop in our code.

**Rationale:** litellm already implements retry logic with appropriate backoff. Reimplementing it would duplicate behavior and make it harder to benefit from litellm improvements. The retry count is configurable via `SMELT_LOADER_RETRIES`.

---

## `ParsedStep` includes `done` status

**Decision:** `PlanParserAgent.parse()` returns `list[ParsedStep]` where each step has both `description` and `done` fields.

**Rationale:** Plans often include already-completed work (e.g. `[x]` checkboxes in markdown). Preserving completion state when loading lets users import a partially-done roadmap without manually marking steps done afterward.

---

## Context manager protocol on RoadmapStorage

**Decision:** `RoadmapStorage` implements `__enter__`/`__exit__` so it's used with `with` blocks in the CLI.

**Rationale:** Guarantees the database connection is always closed, even on errors. Eliminates a class of resource leak bugs without requiring try/finally in every CLI command.
