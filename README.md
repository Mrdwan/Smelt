<p align="center">
  <h1 align="center">🔥 Smelt</h1>
  <p align="center">
    <strong>Orchestrate AI coding agents to ship code autonomously.</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/smelt-cli/"><img src="https://img.shields.io/pypi/v/smelt-cli?style=flat-square&color=blue" alt="PyPI"></a>
    <a href="https://pypi.org/project/smelt-cli/"><img src="https://img.shields.io/pypi/pyversions/smelt-cli?style=flat-square" alt="Python"></a>
    <a href="https://github.com/Mrdwan/Smelt/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Mrdwan/Smelt?style=flat-square" alt="License"></a>
  </p>
</p>

---

Smelt is a CLI tool that manages the full lifecycle of AI-driven development tasks:
**decompose work → plan → code → review → verify → create a PR.** You review the
PR and merge. It's designed to run unattended — if a task takes hours, that's fine.

> **Smelt is not a coding agent.** It's the pipeline — the orchestrator that tells
> your coding agent what to do, verifies the output, and manages the workflow.

## ✨ Features

| Stage         | Model (default) | What it does                                      |
|---------------|-----------------|---------------------------------------------------|
| **Decomposer**| Opus            | Splits big tasks into sub-tasks with dependencies |
| **Architect** | Opus            | Plans the implementation for a single task        |
| **Coder**     | Sonnet (Goose)  | Writes code via a full coding agent session       |
| **Reviewer**  | Sonnet (Goose)  | Reviews code quality, security, standards         |
| **QA**        | None (free)     | Deterministic checks: pytest, ruff, mypy          |
| **QC**        | Haiku           | Cheap intent check: did we build the right thing? |

- 🔁 **Smart retries** — Reviewer ↔ Coder loop, QA → Coder, QC → Architect escalation
- 🌳 **Repo context** — tree-sitter powered, multi-language, token-budgeted
- 🗄️ **Task management** — SQLite with dependency tracking and priority queues
- 🔀 **Git isolation** — every task gets its own branch, agents never touch main
- 📊 **Observability** — structured JSON logs, token tracking, cost per run
- ⚙️ **Fully configurable** — models, retries, timeouts, and QA thresholds via `smelt.toml`

## 📦 Installation

```bash
# With pip
pip install smelt-cli

# With uv (recommended)
uv add smelt-cli

# From source
git clone https://github.com/Mrdwan/Smelt.git
cd Smelt
uv sync
```

## 🚀 Quick Start

```bash
# Add a task to the roadmap
smelt add "implement user authentication with JWT"

# Run the pipeline (picks the next ready task)
smelt run

# Run a specific task
smelt run --task <task-id>

# Check the task board
smelt status
```

## 🛠️ CLI Commands

```
smelt run                         Pick next task and execute pipeline
smelt run --task ID               Execute a specific task
smelt add "description"           Add a task to the roadmap
smelt add "desc" --context "..."  Add task with external context
smelt add "desc" --depends-on ID  Add task with dependencies
smelt decompose TASK_ID           Run decomposer on an existing task
smelt lint                        Lint and format (ruff fix + format)
smelt lint --check                Check only (CI mode)
smelt status                      Show current task board
smelt history                     Browse past runs
smelt replay RUN_ID               Replay a run's conversation
smelt cleanup                     Delete stale failed branches
```

## ⚙️ Configuration

Create a `smelt.toml` in your project root:

```toml
[models]
decomposer = "claude-opus-4-20250514"
architect = "claude-opus-4-20250514"
coder = "claude-sonnet-4-20250514"
reviewer = "claude-sonnet-4-20250514"
qc = "claude-haiku-4-5-20251001"

[context]
max_tokens = 4000

[coding]
max_retries = 3
timeout_seconds = 600

[reviewer]
max_retries = 2

[qa]
run_tests = true
run_linter = true
run_type_checker = true
require_coverage = false
min_coverage_percent = 80.0

[qc]
escalation_mode = "last_attempt"  # never | auto | last_attempt

[git]
base_branch = "develop"
branch_prefix = "smelt/"
lint_before_commit = true
```

## 🏗️ Architecture

```
Task created
  → Decomposer (split if needed, set dependencies)
  → Tasks land in roadmap DB

Pipeline picks next ready task
  → Sanity check: pytest on develop
  → Branch from develop
  → Repo context (tree-sitter)
  → Architect: plan the work
  → Coder (Goose): implement
    ↔ Reviewer: code quality + security
    → QA (deterministic): pytest, ruff, mypy
    → QC (cheap): does output match intent?
  → Lint + commit + PR
  → Log everything
```

See [`docs/Architecture.md`](docs/Architecture.md) for the full design document.

## 🧑‍💻 Development

```bash
# Clone and install
git clone https://github.com/Mrdwan/Smelt.git
cd Smelt
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov --cov-report=term-missing

# Lint and format
uv run ruff check . --fix
uv run ruff format .

# Install pre-commit hooks
uv run pre-commit install
```

## 📜 License

[MIT](LICENSE) — Mohamed Radwan
