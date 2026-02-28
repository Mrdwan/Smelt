# Smelt

> Raw task in, refined code out.

Smelt is a CLI tool that drives AI coding agents through your project roadmap step by step. Define your steps, run `smelt next`, and let your agent do the work.

---

## How it works

Smelt reads your roadmap from a local SQLite database, picks the next uncompleted step, builds context from your architecture and decision docs, and hands it off to an AI agent. When the agent finishes, you mark the step done and move on.

```
smelt next          # run the next uncompleted step
smelt status        # show all steps and their state
smelt add "..."     # add a new step to the roadmap
smelt done <id>     # manually mark a step as complete
```

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
uv tool install smelt
```

Or if you prefer pip:

```bash
pip install smelt
```

---

## Getting started

Initialize a roadmap in your project:

```bash
cd your-project
smelt init
```

Add your first steps:

```bash
smelt add "Set up database models"
smelt add "Implement authentication"
smelt add "Write API endpoints"
```

Run the next step:

```bash
smelt next
```

Smelt will pass the step to Aider along with any context files it finds in your `memory/` directory. Review the changes, then mark it done when you're happy:

```bash
smelt done
```

---

## Context files

Smelt looks for the following files in a `memory/` directory at your project root and passes them to the agent as read-only context:

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | High-level system design |
| `DECISIONS.md` | Key decisions and their rationale |
| `PROGRESS.md` | Current state of the project |

None of these are required. Smelt works without them, but the agent produces better output when it has context.

---

## Configuration

Smelt is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SMELT_MODEL` | `anthropic/claude-sonnet-4-5` | Model passed to Aider |
| `SMELT_PROJECT` | `.` | Path to your project root |

Copy `.env.example` to `.env` and adjust as needed.

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
git clone https://github.com/yourname/smelt
cd smelt
uv sync
uv run pytest
```

```bash
make lint      # ruff check + fix
make format    # ruff format
make test      # pytest
make check     # all of the above
```

---

## License

MIT
