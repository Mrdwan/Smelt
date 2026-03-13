# Smelt — Architectural Plan (v5)

## What Smelt Is
Smelt is a CLI tool that orchestrates AI coding agents to execute development
tasks autonomously in the background. It manages the full lifecycle: decompose
work, plan, code, review, verify, create a PR. The human reviews the PR and
merges. It's designed to run unattended — if a task takes hours, that's fine.

## What Smelt Is NOT
Smelt is not a coding agent. It does not read files, write code, or run
commands directly. That's Goose's job. Smelt is the pipeline — the harness
that tells Goose what to do, verifies the output, and manages the workflow.

## Core Architecture

### Two layers
- **Smelt (orchestrator):** Task management, decomposition, git branching,
  pipeline stages, deterministic QA, retry logic, observability.
- **Goose (coding agent):** File reading/writing/editing, shell commands,
  code search, test execution. Invoked programmatically by Smelt.

### Stages
| Stage       | Default Model | Purpose                                            | Goose Access  |
|-------------|---------------|----------------------------------------------------|---------------|
| Decomposer  | Opus          | Splits big tasks into sub-tasks with dependencies  | None          |
| Architect    | Opus          | Plans the implementation for a single task         | None          |
| Coder        | Sonnet        | Writes code via Goose                              | Full          |
| Reviewer     | Sonnet        | Reviews code quality, security, standards          | Read-only     |
| QA           | None (no LLM) | Deterministic: pytest, ruff, mypy                  | None          |
| QC           | Haiku         | Cheap intent check: does output match task + plan? | None          |

All models are configurable per stage. If someone wants Opus everywhere,
that's their choice and their money.

### Storage
- **Task/roadmap data:** SQLite with dependency tracking
- **Run logs:** `.smelt/runs/{run_id}/` — structured event logs + conversations
- **Config:** `smelt.toml` in project root

## Pipeline Flow

### Phase 1: Task Preparation (runs once per task creation)

```
DECOMPOSER (Opus)
  Input: task description + repo context + external context (if any)
  Decision: is this one task or several?
    → Single task: pass through, assign complexity estimate
    → Multiple tasks: create sub-tasks in roadmap DB
      - Each sub-task gets: description, complexity, depends_on
      - Dependencies are validated (no cycles, topological sort)
      - Sub-tasks land in DB with status "ready" (or "blocked" if dependencies)
```

### Phase 2: Pipeline Execution (runs per task)

```
1. PICK TASK
   Query roadmap DB for next task where:
     - status = "ready"
     - all depends_on tasks have status = "merged"
   Mark it "in-progress" (atomic SQLite update)

2. SANITY CHECK (no LLM)
   git checkout develop && git pull
   Run pytest on clean develop
     → ANY FAILURE: create bug ticket (highest priority, no dependencies),
       mark current task back to "ready", stop pipeline.
       Bug ticket description includes: failing test names + assertion errors.
     → ALL PASS: continue

3. CREATE BRANCH
   git checkout -b smelt/{task-slug}

4. BUILD REPO CONTEXT
   tree-sitter scan: file tree + function/class signatures (all languages)
   Token-budgeted via context_max_tokens config
   Shared across all stages for this run

5. ARCHITECT (configurable model, default Opus)
   Input: repo context + task description + external context
   Output: implementation plan
     - Which files to create or modify
     - What the changes are (plain English)
     - What tests to write or update
     - Risks and edge cases
   The plan is stored as a run artifact.

6. CODER (configurable model, default Sonnet, via Goose)
   Input: repo context + plan + last failure (if retrying)
   Full Goose session: reads files, writes code, edits, runs tests
   Signals completion → pipeline moves to Reviewer

7. REVIEWER (configurable model, default Sonnet, read-only Goose)
   Input: repo context + plan + diff + ability to read any file
   Single job: is this code good?
     - Security holes?
     - Edge cases missed?
     - Naming and patterns consistent with codebase?
     - Test quality sufficient?
   Does NOT check intent (that's QC's job).
   PASS → QA
   FAIL (code quality issue) → back to Coder with feedback
   FAIL (plan-level problem detected) → escalate to Architect
     Reviewer always has the option to escalate plan problems.
     "Your plan works but creates a security issue in the approach"
     → Architect re-plans with Reviewer's feedback.

8. QA (deterministic, no LLM) — ALWAYS RUNS
   Run pytest --tb=short -q (capture output)
   Run ruff check . (capture output)
   Run mypy . (capture output)
   Optional: pytest --cov --cov-fail-under=N
   All pass → QC
   Any fail → back to Coder with last failure output
     (only the last failure, no history pile-up)

9. QC (configurable model, default Haiku)
   Input: original task description + architect plan + diff + QA results
   Single job: did we build what was asked?
     - Does implementation match the task?
     - Does implementation match the plan?
     - Do tests cover what the task required?
     - Was anything missed or misinterpreted?
   PASS → Create PR
   FAIL → escalation logic (configurable, see Retry Logic)
     Escalation context includes: "intent mismatch" vs "incomplete implementation"

10. CREATE PR
    Run ruff check --fix . (auto-fix)
    Run ruff format . (auto-format)
    git add .
    git commit -m "smelt: {task description}"
    Push branch / create PR via API
    Mark task "in-review" in DB

11. LOG
    Write full run data to .smelt/runs/{run_id}/
    Token usage per stage, per API call, with timestamps
    Stage durations, pass/fail results
    Goose session IDs
    Full conversation history per stage
```

## Retry Logic

### Coder ↔ Reviewer loop
- Reviewer rejects (code quality) → Coder gets specific feedback
- Max retries: max_review_retries (default 2)
- Exhausted → move to QA anyway (deterministic checks catch the rest)

### Reviewer → Architect escalation
- Reviewer detects plan-level problem → Architect re-plans
- Architect gets: original task + Reviewer's feedback
- Feedback tagged as "quality concern" (approach creates problems)
- This can happen at any time, not just on the last attempt.
- Architect re-plan happens ONCE. If the new plan also triggers
  Reviewer escalation, the task fails.

### QA failure → Coder
- Last failure output passed to Coder (only the most recent)
- "QA found these issues: [output]. Fix them."
- Truncated intelligently: test names + assertion errors, not full traces
- Max retries: max_coding_retries (default 3)

### QC failure → Coder or Architect
Configurable via qc_escalation_mode:

| Mode             | Behavior                                            |
|------------------|-----------------------------------------------------|
| `never`          | QC failures always go back to Coder.                |
| `auto`           | QC decides: is this a code fix or a plan problem?   |
|                  | Prompt includes: "Reply CODER or ARCHITECT."        |
|                  | If ARCHITECT: feedback tagged as "intent mismatch"  |
| `last_attempt`   | Normal retries go to Coder. On the final attempt,   |
|                  | QC gets the escalation prompt.                      |

Default: `last_attempt`

### Architect re-plan (from QC)
- Gets: original task + QC feedback (tagged as "intent mismatch")
- Produces new plan → Coder starts fresh (retry counter resets)
- Happens ONCE. If the new plan also fails QC, task fails.

### Pipeline errors vs task errors
- **Task error** (code is wrong, retries exhausted): task marked "failed",
  branch kept for debugging. Needs human attention.
- **Infra error** (Goose crash, API down, rate limit): task marked
  "infra-error", automatically retryable with configurable delay.
  Does NOT count against retry limits.

### Total failure
- Task marked "failed" in DB
- Branch kept for debugging / post-mortem
- Full run log available via `smelt replay`

## Decomposer

Runs once when a task is created (not per pipeline run).

Input: task description + repo context + external context
Output: either the original task (if atomic) or multiple sub-tasks

For each sub-task, the Decomposer produces:
- Description (specific, actionable)
- Complexity estimate (used for logging/dashboard, not routing)
- depends_on (list of other sub-task IDs)

Dependency validation:
- Topological sort on creation — reject cycles immediately
- Task picker query: only pick tasks where ALL dependencies
  have status "merged" (not just "in-review")
- A slow PR review blocks downstream tasks. This is correct behavior.

The Decomposer should be Opus (or the configured decomposer model)
because bad decomposition cascades into every downstream task.

## Git Workflow

- Agent NEVER touches main or develop directly
- Agent NEVER has merge access
- Smelt handles ALL git operations, agents have no git tools
- Every task → new branch from develop: `smelt/{task-slug}`
- On success: PR created for human review
- On failure: branch kept, task marked "failed"
- Parallel agents work on different tasks/branches
- Merge conflicts resolved manually via `smelt resolve` (future)

## Task Dependencies

Stored in a separate `task_dependencies` table (many-to-many):

```
task_dependencies:
  task_id      → references tasks.id
  depends_on   → references tasks.id
```

Task picker query (pseudo-SQL):
```sql
SELECT * FROM tasks
WHERE status = 'ready'
  AND id NOT IN (
    SELECT task_id FROM task_dependencies
    WHERE depends_on NOT IN (
      SELECT id FROM tasks WHERE status = 'merged'
    )
  )
ORDER BY priority DESC, created_at ASC
LIMIT 1
```

Status lifecycle:
```
ready → in-progress → in-review → merged
                    → failed (task error, needs human)
                    → infra-error (auto-retryable)
         blocked (dependencies not met, implicit from query)
```

## External Context

Tasks can have external context attached: API specs, design docs,
reference material, requirements. Stored as a text blob on the task
in the roadmap DB (`context` field). Can also reference files in the
repo via a `context_files` field (comma-separated paths).

Context is injected into the Architect's prompt and the QC's prompt
(Architect needs it to plan, QC needs it to verify intent).

No automatic URL fetching or Figma parsing. The human pastes
whatever context is needed when creating the task.

## Sanity Check (pre-pipeline)

Before any LLM calls, on a clean develop branch:
1. Run `pytest --tb=short -q`
2. If ANY test fails:
   - Create a bug ticket in roadmap DB (highest priority, no dependencies)
   - Bug description: failing test names + assertion error messages
   - Mark the original task back to "ready" (it didn't start)
   - Stop the pipeline
3. If all tests pass: proceed with pipeline

No LLM involved. Just subprocess + SQLite insert.
The bug ticket gets picked up on the next pipeline run (it's highest priority).
Once the fix is merged, the original task becomes eligible again.

## Repo Context (tree-sitter)

Built once per pipeline run, shared across all stages. Contains:
1. File tree with sizes (always included, cheap)
2. Key config files in full (pyproject.toml, smelt.toml, Makefile, etc.)
3. Function/class signatures via tree-sitter (all languages from day one)

Token-budgeted via `context_max_tokens`. Prioritizes smaller files first
(usually interfaces/models). Language-agnostic. This is the equivalent
of Aider's repo map.

## Observability

Every run writes to `.smelt/runs/{run_id}/`:
- `events.jsonl` — structured log: stage transitions, tool calls,
  token counts, timestamps, Goose session IDs, pass/fail, models used
- `{stage}.messages.json` — full conversation history per stage
- `result.json` — outcome, tokens per stage, total cost, duration,
  retry counts, escalation events

Retention: configurable, default keep last 50 runs.

Future CLI:
- `smelt history` — browse past runs
- `smelt replay {run_id}` — step through conversations

Future web dashboard:
- Token usage / cost charts over time, per stage, per model
- Pass/fail rates by stage
- Retry frequency and escalation patterns
- Task throughput and cycle times
- Decomposition stats (tasks split vs pass-through)
- Active / blocked / in-review / failed / merged task boards
- Dependency graph visualization

## CLI Commands (planned)

```
smelt run                    Pick next task and execute pipeline
smelt run --task ID          Execute a specific task
smelt add "description"      Add a task to the roadmap
smelt add "desc" --context "..." --depends-on ID
smelt decompose --task ID    Run decomposer on an existing task
smelt lint                   Lint and format (ruff fix + format)
smelt lint --check           Check only (CI mode)
smelt status                 Show current task board
smelt history                Browse past runs
smelt replay ID              Replay a run's conversation
smelt cleanup                Delete stale failed branches
smelt resolve BRANCH         (future) Fix merge conflicts
```

## Config (smelt.toml)

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
max_retries = 3                       # QA fail → coder retries
timeout_seconds = 600

[reviewer]
max_retries = 2                       # reviewer ↔ coder loop
timeout_seconds = 300

[qa]
run_tests = true
run_linter = true
run_type_checker = true
require_coverage = false
min_coverage_percent = 80.0

[qc]
escalation_mode = "last_attempt"      # never | auto | last_attempt
timeout_seconds = 300

[git]
base_branch = "develop"
branch_prefix = "smelt/"
lint_before_commit = true

[infra]
retry_delay_seconds = 60              # delay before retrying infra errors
max_infra_retries = 3                 # max infra error retries per task

[observability]
log_dir = ".smelt/runs"
max_runs_retained = 50

[sanity]
create_bug_ticket_on_failure = true   # auto-create bug ticket if develop is broken
bug_ticket_priority = 1               # highest priority
```

## Tech Stack
- Python 3.12+
- uv (package manager)
- click (CLI framework)
- SQLite (task/dependency storage)
- Goose (coding agent, invoked programmatically)
- tree-sitter + language grammars (repo context, multi-language)
- ruff (linting/formatting)
- pytest (testing)
- mypy (type checking)
- hatchling (build backend)
