# Smelt — Coding Standards

This document defines the mandatory coding standards for Smelt. Every contributor (human or AI) must follow these rules. Violations must be caught by pre-commit hooks or CI before code is merged.

## Core Principles

### 1. 100% Test Coverage — Non-Negotiable

- Every module must have **100% line coverage** and **100% branch coverage**.
- `pytest --cov --cov-branch` is enforced via pre-commit. **Commits are rejected if either metric drops below 100%.**
- Branch coverage catches untested `if/else` paths that line coverage misses. Both are required.
- The only exceptions are in `[tool.coverage.run] omit` (e.g., CLI entry points that are trivial wrappers).
- If you add code, you add tests. No exceptions.

### 2. Tests Must Be Meaningful

Tests must validate **actual behavior**, not just confirm that mocks return what you told them to return.

**❌ BAD — Tests nothing, always passes even if function is broken:**
```python
def test_parse_dependencies(mocker):
    fake_deps = ["task-1", "task-2"]
    mocker.patch("smelt.roadmap.db.get_dependencies", return_value=fake_deps)
    result = db.get_dependencies("task-3")
    # This just checks that the mock returned what we told it to — useless
    assert result == fake_deps
```

**✅ GOOD — Tests that the function actually transforms/validates/processes correctly:**
```python
def test_parse_dependencies_from_prompt_output(mocker):
    # Mock returns RAW LLM response (not the expected parsed output)
    raw_llm_response = 'Decomposed tasks:\n- [ID: sub-1] Setup DB\n- [ID: sub-2, Dep: sub-1] Add schema'
    mocker.patch("smelt.agents.llm.invoke", return_value=raw_llm_response)

    result = decomposer.extract_tasks("Build feature X")

    # Tests that the function ACTUALLY parses the text structure into domain objects correctly
    assert len(result) == 2
    assert result[0].task_id == "sub-1"
    assert result[0].depends_on == []
    assert result[1].task_id == "sub-2"
    assert result[1].depends_on == ["sub-1"]
```

**The rule:** Mock the **input** (raw LLM response, raw subprocess stdout, raw file content). Assert the **output** (what the function actually produces from that input). The test should **fail if the function's logic is broken**, even though the mocks are perfect.

### 3. All External Calls Must Be Mocked

- No real LLM API calls in tests. Ever.
- No real Git shell executions targeting remote repos in tests.
- Mock at the boundary: `litellm.completion`, `subprocess.run`, file I/O.
- Use `pytest-mock` (`mocker` fixture) or `unittest.mock.patch`.
- Integration tests mock at a higher level (e.g., mock the `LLMClient` interface, not `litellm.completion`), but still no real network calls.

### 4. Two Test Layers

| Layer | What It Tests | Mocking Level |
|-------|--------------|---------------|
| **Unit tests** | Individual functions/methods in isolation | Mock all dependencies at the boundary |
| **Integration tests** | Multi-component flows (e.g., Parse Tree-sitter → Inject to Architect → Store Plan) | Mock external services (LLM, Goose), use real internal SQLite logic |

Both layers are required for every feature. Unit tests go in `tests/unit/`, integration tests in `tests/integration/`.

---

## Type Safety

### 5. Strict Type Checking (mypy --strict)

- Every function must have full type annotations (parameters and return type).
- No `Any` types unless absolutely necessary (and documented why).
- `mypy --strict` is enforced via pre-commit. Commits are rejected on type errors.

### 6. Use Dataclasses for All Domain Objects

Never pass raw dicts or tuples for structured data. Define a dataclass (or `NamedTuple` for immutable data).

**❌ BAD:**
```python
def create_run_record(task_id: str) -> dict:
    return {"status": "passed", "stage": "QC", "tokens": 450}
```

**✅ GOOD:**
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RunResult:
    status: str
    stage: str
    tokens_used: int

def create_run_record(task_id: str) -> RunResult:
    return RunResult(status="passed", stage="QC", tokens_used=450)
```

Use `frozen=True` for immutable value objects. Use `@dataclass` (mutable) only when state genuinely needs to change.

---

## Design Principles

### 7. SRP, Open/Closed, DIP

| Principle | What It Means Here |
|-----------|-------------------|
| **SRP** | Each module/class does one thing. `git.py` manages branching. `runner.py` invokes Goose. They don't do both. |
| **Open/Closed** | New pipeline stages (e.g., SecurityReviewer) are added by implementing an Abstract Stage Class — not by modifying a giant switch statement in the runner. |
| **DIP** | Depend on abstractions, not concretions. `TaskPicker` receives a `StorageBackend` interface, not a hardcoded `SqliteConnection`. |

### 8. Dependency Injection

All dependencies are injected via constructor or function parameters. No module-level singletons, no global state, no `import SqliteConnection` deep inside business logic.

**❌ BAD:**
```python
class TaskPicker:
    def __init__(self):
        self.db = SqliteDB()  # Hard-coded dependency
```

**✅ GOOD:**
```python
class TaskPicker:
    def __init__(self, db: StorageBackend) -> None:
        self._db = db
```

This makes testing trivial (inject an in-memory test DB) and keeps logic decoupled.

### 9. DRY — Don't Repeat Yourself

- Extract shared logic into helper functions or base classes.
- If you copy-paste the exact same mock setup or subprocess parsing code twice, you're doing it wrong.

---

## Code Style

### 10. Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Modules | `snake_case` | `task_picker.py` |
| Classes | `PascalCase` | `TaskPicker` |
| Functions/methods | `snake_case` | `fetch_next_ready` |
| Constants | `UPPER_SNAKE` | `DEFAULT_TIMEOUT_SECONDS` |
| Private | `_leading_underscore` | `_parse_goose_output` |
| Type aliases | `PascalCase` | `DependencyList` |

### 11. Docstrings

Every public function, class, and module must have a docstring. Use Google style:

```python
def validate_roadmap_dependencies(task_id: str, deps: list[str]) -> bool:
    """Validate that dependencies for a task form a valid directed acyclic graph.

    Checks:
        - None of the dependencies are the task itself
        - No circular dependency chains exist
        - All referenced dependency IDs exist in the database

    Args:
        task_id: The ID of the task being created or modified.
        deps: A list of task IDs that this task depends on.

    Returns:
        True if the dependencies are valid.

    Raises:
        CircularDependencyError: If a cycle is detected.
        MissingTaskError: If a dependency ID does not exist.
    """
```

### 12. Module Structure

Every Python module follows this order:
1. Module docstring
2. `from __future__ import annotations`
3. Standard library imports
4. Third-party imports
5. Local imports
6. Constants
7. Type aliases
8. Classes/functions
9. No code at module level (no side effects on import)

### 13. Error Handling

- Use specific exception types, never bare `except:`.
- Define custom exceptions in an `exceptions.py` module when needed (`TaskNotFoundError`, `GooseTimeoutError`).
- Distinguish between **Pipeline/Infra Errors** (auto-retryable) and **Task Errors** (bad code/plan, needs human).

---

## Tooling Enforcement

### Pre-commit Pipeline (must all pass to commit)

| Step | Tool | What It Catches |
|------|------|----------------|
| 1 | `ruff check --fix` | Lint errors, import sorting, dead code |
| 2 | `ruff format` | Code formatting |
| 3 | `mypy --strict` | Type errors |
| 4 | `pytest --cov --cov-branch` | Test failures, line or branch coverage below 100% |

### CI Pipeline (GitHub Actions)

Same as pre-commit, plus:
- Runs on every PR
- Matrix testing on Python 3.12+
- Coverage report uploaded as artifact

---

## Summary

> **If it's not typed, not tested, and not clean — it doesn't get committed.**
>
> Smelt is an orchestrator that runs **unattended** for hours while writing code against your own repo. If there is a bug here, it cascades into every codebase Smelt touches. Every shortcut is a future disaster. Write code like your entire development pipeline depends on it — because it will.
