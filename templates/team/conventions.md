# Team Development Conventions

## Commit Format (Conventional Commits)

```
<type>(<scope>): <description>

[optional body]

[optional footer: refs|breaking|co-authored-by]
```

Types: `feat` `fix` `docs` `refactor` `test` `chore` `perf` `ci` `revert`

## Branch Naming

```
feat/<task-id>-<slug>
fix/<task-id>-<slug>
chore/<task-id>-<slug>
```

## Code Style

- Max function length: 40 lines
- Max file length: 400 lines (excluding tests)
- No `any` / `object` types — use precise types
- No silent catch — all errors must be handled explicitly
- Public functions must have docstrings/comments explaining WHY, not WHAT

## Test Requirements

- Every public function has at least one test
- Tests verify behavior, not implementation
- No `assert True`, no empty tests, no TODO tests
- RED must be observed before GREEN

## AI Agent Output Contract

When finishing a feature, the agent MUST produce:

1. Code + tests passing locally (verified by re-run)
2. Updated plan/state
3. Handoff document (what was done, how to continue, known risks)
4. Commit message ready (conventional format)
5. Self-review report (conventions compliance)

## Handoff Document Structure

Every `handoff.md` must include:

- Current status (DONE/BLOCKED/INTEGRATION_FAIL)
- What was done (task-by-task)
- File inventory (verified on disk)
- Current blocker (if any)
- Next steps (actionable, specific)
- How to resume (exact commands)
