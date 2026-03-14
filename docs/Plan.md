# Smelt Pipeline — Issues & Improvements Checklist (v5)

## Architecture Summary
- Goose is the coding agent, Smelt is the orchestrator
- Six stages: Decomposer → Architect → Coder ↔ Reviewer → QA → QC → PR
- Decomposer runs once per task creation (splits work, sets dependencies)
- Architect runs every task (plans the work)
- Reviewer: code quality, security, standards (read-only Goose)
- QA: always deterministic, always runs, free
- QC: cheap intent check (Haiku default), did we build the right thing?
- All models configurable per stage
- Token tracking is logging only (dashboard later)
- Each task gets its own branch from develop
- Parallel agents pick different tasks via atomic SQLite
- Sanity check runs pytest on develop before any LLM calls
- Infra errors auto-retry, task errors need human attention

## Pipeline Flow
```
Task created → Decomposer (split if needed, set dependencies)
  → Tasks in roadmap DB

Pipeline picks next ready task (dependencies met)
  → Sanity check: pytest on develop
    → FAIL → bug ticket, stop
    → PASS → continue
  → Branch from develop
  → Repo context (tree-sitter, all languages)
  → Architect: plan the work
  → Coder (Goose): implement
    ↔ Reviewer (read-only Goose): code quality + security
      → FAIL (code) → Coder
      → FAIL (plan problem) → Architect (always allowed)
    → QA (deterministic): pytest, ruff, mypy
      → FAIL → Coder with failure data
    → QC (cheap): does output match task + plan?
      → FAIL → Coder or Architect (configurable escalation)
    → PASS → lint + commit + PR
  → Log everything
```

## Original Issues

1. [x] No repo context on start
   **Fix:** tree-sitter repo map, all languages, token-budgeted.

2. [x] "done" tool is trust-based
   **Fix:** `code_complete` signal. Pipeline controls transitions.
   Deterministic QA is the real gate.

3. [x] Retry loop feeds garbage context
   **Fix:** Only last failure passed to Coder. Architect escalation
   via Reviewer (plan quality) or QC (intent mismatch), configurable.

4. [x] No diff awareness
   **Fix:** Diff captured for Reviewer, QC, and PR description.
   QA is deterministic, doesn't need diff.

5. [x] ~~Security: run_command blocklist~~ — REMOVED
   Goose handles execution. Docker is the boundary.

6. [x] Git isolation
   **Fix:** Smelt owns all git. Agents have no git tools.

7. [x] ~~Token budget limits~~ — CHANGED TO LOGGING
   Log everything, no limits. Dashboard later.

8. [x] Test failures not fed back
   **Fix:** QA captures output, truncated intelligently
   (test names + assertions), injected into Coder retry prompt.

9. [x] ~~write_file/edit_file~~ — REMOVED
   Goose handles file ops.

10. [x] No rollback on failure
    **Fix:** Branch-based isolation. Failure = branch kept + task "failed".

11. [x] QA wastes tokens
    **Fix:** QA is pure Python, no LLM. QC is separate cheap intent check.

12. [x] ~~Concurrency lock~~ — REMOVED
    Atomic SQLite. Separate branches.

13. [x] Config has no validation
    **Fix:** Validate in `from_toml`. Types, ranges, unknown key warnings.

14. [x] No observability
    **Fix:** Structured JSON per run. Events + conversations + results.
    Retention policy. Future: CLI + web dashboard.

## Items Added During Design

15. [x] Decomposer agent — splits big tasks, sets dependencies + complexity
16. [x] Task dependencies — `depends_on` in DB, topological validation
17. [x] External context — text blob + file paths on tasks
18. [x] Sanity check — pytest on develop before any LLM calls
19. [x] Infra vs task error distinction — infra auto-retries, tasks fail
20. [x] Reviewer escalation — always allowed to flag plan-level problems
21. [x] QC escalation modes — never / auto / last_attempt
22. [x] Architect re-plan context — tagged as "quality concern" or "intent mismatch"
23. [x] All models configurable per stage

## Implementation Order (suggested)

### Phase 1: Foundation
- [x] SQLite schema: tasks table with status, priority, complexity,
      context, context_files fields
- [x] SQLite schema: task_dependencies table (many-to-many)
- [x] Task picker query with dependency resolution
- [x] Config: smelt.toml loading + validation
- [x] CLI skeleton: `smelt run`, `smelt add`, `smelt status`, `smelt lint`
- [x] Git operations module (branch, commit, push — used by pipeline only)

### Phase 2: Core Pipeline
- [ ] Sanity check (pytest on develop, bug ticket creation)
- [ ] Repo context builder (tree-sitter, multi-language)
- [ ] Goose integration: figure out how to invoke programmatically
      (headless sessions, prompt injection, result capture)
- [ ] Architect stage (Goose session with planning prompt)
- [ ] Coder stage (Goose session with coding prompt)
- [ ] QA stage (deterministic: pytest, ruff, mypy, structured results)

### Phase 3: Review & Verification
- [ ] Reviewer stage (read-only Goose, code quality prompt)
- [ ] Coder ↔ Reviewer retry loop
- [ ] Reviewer → Architect escalation
- [ ] QC stage (cheap model, intent verification prompt)
- [ ] QC escalation modes (never / auto / last_attempt)
- [ ] Architect re-plan with tagged context

### Phase 4: Decomposer & Dependencies
- [ ] Decomposer stage (split tasks, set dependencies)
- [ ] Cycle detection on dependency creation
- [ ] `smelt decompose` CLI command
- [ ] Dependency-aware task picker
- [ ] `smelt add` with --depends-on and --context flags

### Phase 5: Observability & Polish
- [ ] Structured JSON logging per run
- [ ] Conversation history persistence per stage
- [ ] Token tracking per stage/call
- [ ] Run result summary
- [ ] Retention policy
- [ ] `smelt history` and `smelt replay` CLI commands
- [ ] `smelt cleanup` for stale branches
- [ ] Infra error auto-retry logic

### Phase 6: Dashboard (future)
- [ ] Web interface
- [ ] Cost/token charts
- [ ] Task boards
- [ ] Dependency graph visualization
- [ ] Retry/escalation pattern analysis
