# Smelt

> Raw task in, refined code out.

Smelt is a CLI tool that drives AI coding agents through your project roadmap step by step. Define your steps, run `smelt next`, and let your agent do the work.

---

## How it works

Smelt reads your roadmap from a local SQLite database, picks the next uncompleted step, builds context from your architecture and decision docs, and hands it off to an AI agent. When the agent finishes successfully, the step is automatically marked as done.

---

## Requirements

- Python 3.12+
- [Aider](https://aider.chat) installed and available in PATH

```bash
pip install aider-chat
```

---

## Installation

```bash
uv tool install SmeltWorkflow
```

Or with pip:

```bash
pip install SmeltWorkflow
```

---

## Commands

```
smelt add       # add a new step to the roadmap
smelt next      # run the next uncompleted step
smelt done      # manually mark a step as done
smelt reset     # reopen a completed step
smelt status    # show all steps and their state
```

### `smelt add`

Appends a new step to the roadmap:

```bash
smelt add "Implement authentication"
# Step added (id=1): Implement authentication
```

### `smelt next`

Fetches the next pending step from the roadmap, shows it, and asks for confirmation before running the agent. On success the step is marked done. On failure it stays pending so you can retry or skip.

### `smelt done`

Manually marks a step as done by its ID — useful when you've handled a step outside of Smelt:

```bash
smelt done 2
# Step 2 marked as done.
```

### `smelt reset`

Reopens a completed step so it will be picked up by `smelt next` again — useful when the agent's output was wrong and you want to retry:

```bash
smelt reset 2
# Step 2 reopened.
```

### `smelt status`

Lists every step in the roadmap with its completion state:

```
Roadmap: 1/3 done

  [x] Set up database models
  [ ] Implement authentication
  [ ] Write API endpoints
```

---

## Getting started

Create a `.env` file in your project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Add steps to your roadmap, then start working through them:

```bash
smelt add "Set up database models"
smelt add "Implement authentication"
smelt add "Write API endpoints"

smelt next
```

Smelt will show the next step, ask if you want to proceed, run Aider with any context files it finds, and mark the step done on success.

---

## Context files

Smelt looks for the following files in the `memory/` directory and passes them to the agent as read-only context:

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | High-level system design |
| `DECISIONS.md` | Key decisions and their rationale |

None of these are required. Smelt works without them, but the agent produces better output when it has context.

---

## Configuration

All settings are read from environment variables (with `SMELT_` prefix) or a `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `SMELT_MODEL` | `anthropic/claude-sonnet-4-6` | Model passed to Aider |
| `SMELT_PROJECT` | `.` | Path to your project root |
| `SMELT_MEMORY` | `memory` | Directory for context files and the roadmap DB |
| `SMELT_CONTEXT_FILES` | `["ARCHITECTURE.md","DECISIONS.md"]` | Files passed to the agent as read-only context |
| `SMELT_ROADMAP_DB` | `roadmap.db` | Filename of the SQLite roadmap database |

---

## Using a different agent

Aider is the default agent but Smelt is built with an adapter interface. You can implement your own:

```python
from smelt.agents.base import Agent

class MyAgent(Agent):
    def run(self, message: str, context_files: list[str]) -> bool:
        # your implementation
        ...
```

---

## Development

```bash
git clone https://github.com/MrDwarf7/Smelt
cd Smelt
uv sync
uv run pytest
```

Pre-commit hooks run automatically on every commit (ruff lint, ruff format, pytest). To install them after cloning:

```bash
uv run pre-commit install
```

To run manually:

```bash
uv run pre-commit run --all-files
```

---

## License

MIT
