---
name: sean
description: "Self-contained harness development workflow. Activates on any 'sean' prefix command. Zero external dependencies."
version: 2.0.0
trigger: sean
---

# Sean — Harness Development Workflow Skill

## Trigger

Activated when user input starts with `sean ` (case-insensitive).

Parse the command and arguments, then execute the matching workflow below.

## Global Rules

- **Self-contained**: Do NOT call any external skill (no superpowers). All logic is defined here.
- **Project-aware**: Read `AGENTS.md` if it exists and obey its constraints.
- **Test-first**: Always write the failing test BEFORE implementation code.
- **Never modify tests to pass**: Tests are the spec. If a test fails, fix the implementation.
- **State tracking**: Maintain `docs/.sean/state.json` for all progress tracking.
- **History tracking**: Save a snapshot to `docs/.sean/history/` before any mutating operation.

## Path Conventions

```
<project>/
├── docs/
│   ├── requirements/
│   │   └── <YYYY-MM-DD>-<feature>.md
│   ├── plans/
│   │   └── <YYYY-MM-DD>-<feature>.md
│   ├── test-reports/
│   │   └── <YYYY-MM-DD>-<feature>/
│   │       ├── task-N-<name>.md
│   │       └── summary.md
│   └── .sean/
│       ├── state.json
│       ├── active
│       └── history/
│           └── <timestamp>-<action>.json
```

All dates use local timezone. Filenames use kebab-case.

---

## Command: `sean start <name> [description...]`

### Steps

1. **Validate name**: Must be lowercase kebab-case (e.g., `comments`, `advanced-search`).
2. **Check existence**: If `docs/requirements/<date>-<name>.md` exists, ask before overwriting.
3. **Gather requirements**:
   - If `[description...]` provided: use it as the problem statement.
   - If no description: ask 3 questions:
     - "这个功能解决什么问题？（一句话）"
     - "关键行为是什么？（逗号分隔）"
     - "验收标准是什么？（逗号分隔）"
4. **Create requirement file** from `templates/requirement.md` template.
5. **Update state**:
   - Create entry in `state.json` → `features.<name>` with `status: "DRAFT"`.
   - Set `active` to `<name>`.
6. **Save history**: Record `start` action snapshot.
7. **Output**: File path, status, next step (`sean plan <name>`).

---

## Command: `sean plan <name>`

### Steps

1. **Load requirement**: Read `docs/requirements/<date>-<name>.md`. If not found, error.
2. **Analyze**: Extract functional points and acceptance criteria.
3. **Decompose** into TDD tasks following this architecture order:
   - Database: schema, migration, entity
   - Service: business logic, validation
   - Controller: API endpoints, DTOs
   - Permissions: authorization, guards
   - Integration: external services, WebSocket, etc.
   - Frontend: UI components, pages
4. **For each task**, define:
   - `id`: sequential number
   - `name`: short kebab-case identifier
   - `files_create`: exact file paths to create
   - `files_modify`: existing files to modify
   - `test_file`: exact test file path
   - `steps`: ordered TDD steps (red → green → commit)
   - `acceptance`: how to verify
   - `depends_on`: list of task ids (or empty)
5. **Validate**: no circular dependencies, all tasks have unique names.
6. **Write plan** to `docs/plans/<date>-<name>.md` using `templates/plan.md`.
7. **Update state**: `status: "PLANNED"`, `tasks_total`, initialize `tasks[]`.
8. **Save history**: Record `plan` action.
9. **Output**: Task list summary, estimated test count, next step (`sean run <name> --dry-run`).

---

## Command: `sean run <name> [start_n] [--dry-run] [--no-fix]`

### Pre-flight

1. Load plan from `docs/plans/<date>-<name>.md`. Error if missing.
2. Load state, resolve feature entry.
3. Determine start task index (default 1, or `start_n` if provided).

### If `--dry-run`

Do NOT execute any code. Only:
1. Parse all tasks from plan.
2. Print table: `# | Task | Tests | Dependencies`.
3. Validate dependencies (no cycles).
4. Estimate total tests and time.
5. Output: `sean run <name>` to execute.

### If executing (no `--dry-run`)

**Save history snapshot before starting** (for undo).

For each task from `start_n` to end:

#### Task Execution Loop

1. **Check dependencies**: Verify all `depends_on` tasks have `status: "done"`. If not, warn and offer to skip/run dependency first.
2. **Mark task**: `status: "in_progress"` in state.
3. **Write failing test** in `test_file` path.
4. **Run test**: Execute the test file. Expected: FAIL/RED.
   - If test PASSES immediately → the test is wrong (tests existing behavior). Fix the test.
   - If test ERRORS (not fails) → fix the test setup.
5. **Write minimal implementation** to make the test pass.
6. **Run test** again. Expected: PASS/GREEN.
7. **If GREEN**:
   - Write test report to `docs/test-reports/<date>-<name>/task-<N>-<name>.md`.
   - Mark task `status: "done"` in state.
   - Continue to next task.
8. **If RED** (implementation fails):
   - **If `--no-fix`**: Mark task `status: "failed"`, STOP. Output failure details.
   - **If default (auto-fix)**: Enter Fix Loop:
     ```
     for attempt in 1..3:
       a. Read error output
       b. Analyze root cause (check stack trace, error message, context)
       c. Modify implementation code (NEVER modify the test)
       d. Re-run test
       e. If GREEN: break, write report (marked as "fixed"), continue
       f. If still RED: continue loop
     ```
   - After 3 attempts still RED: Mark task `status: "failed"`, STOP.
9. **Check consecutive failures**: If 2 consecutive tasks failed, ABORT entire run. Output blocker report.

#### Post-execution

1. Update state: `current_task`, overall status (`DONE` if all passed, `BLOCKED` if failed).
2. Generate `docs/test-reports/<date>-<name>/summary.md`.
3. Output final report.

---

## Command: `sean task <name> <n> [--dry-run] [--no-fix]`

Same as `sean run` but only executes task `<n>`. Does not check dependencies (user's responsibility).

---

## Command: `sean fix [name]`

### Steps

1. If `[name]` not provided, read `active` from state.
2. Find the most recent task with `status: "failed"` in the feature.
3. Read the corresponding test report for failure details.
4. Run tests to reproduce the failure.
5. Analyze root cause → fix code (not tests) → re-run tests.
6. If GREEN: Update task `status: "done"`, update report.
7. If still RED: Output failure, suggest `sean undo` or manual fix.

---

## Command: `sean undo [name] [steps]`

### Steps

1. If `[name]` not provided, read `active` from state.
2. `steps` default = 1.
3. Read `docs/.sean/history/` and find the most recent entry where `undone: false` for this feature.
4. **Restore files**:
   - For each path in `files_created`: delete the file.
   - For each entry in `files_modify`: restore content from snapshot or `git checkout <path>` if in git.
5. **Restore state**: Replace `state.json` with the `before` snapshot from history.
6. Mark history entry `undone: true`.
7. Output what was undone, current status.
8. If `steps > 1`: repeat for next history entry.

---

## Command: `sean retry <name>`

### Steps

1. Find the most recent `status: "failed"` task in the feature.
2. Execute `sean task <name> <n> --no-fix` for that task.

---

## Command: `sean list`

### Steps

1. Read `state.json`.
2. For each feature, print: `name`, `status`, `tasks_done/tasks_total`, `tests_passed`, `report_exists`.
3. Sort by `started_at` descending.
4. Highlight the `active` feature.

---

## Command: `sean status <name>`

### Steps

1. Read state, find feature.
2. Print: requirement path, plan path, status, progress bar, task list with per-task status and test counts.
3. If `BLOCKED`: print `blocked_reason`.

---

## Command: `sean report [name] [--summary]`

### Steps

1. If `[name]` not provided, read `active`.
2. Scan `docs/test-reports/<date>-<name>/` for all `task-*.md` files.
3. Aggregate: total tests, passed, failed, fixed.
4. Print table report to terminal.
5. If `--summary`: also write `docs/test-reports/<date>-<name>/summary.md`.

---

## Command: `sean switch <name>`

### Steps

1. Verify feature exists in state.
2. Update `active` to `<name>`.
3. Print switched status and feature info.

---

## Command: `sean clean [--keep-reports]`

### Steps

1. Ask for confirmation.
2. Delete `docs/.sean/` directory.
3. If `--keep-reports`: preserve `docs/test-reports/`, only remove state.
4. Output: "已清理".

---

## Error Handling

| Error | Message | Action |
|-------|---------|--------|
| Feature not found | `功能 <name> 不存在。现有: <list>` | Suggest `sean list` |
| Plan not found | `计划不存在。运行: sean plan <name>` | - |
| Requirement not found | `需求不存在。运行: sean start <name>` | - |
| Dependency not met | `Task N 依赖 Task M (未完成)` | Offer to run dependency |
| Test timeout (>60s) | `测试运行超时` | Offer skip/retry |
| 2 consecutive failures | `连续失败，中止。查看报告: sean report <name>` | STOP |
| No failed report | `没有失败的测试报告` | - |
| Nothing to undo | `没有可撤销的操作` | - |
| File modified externally | `警告: 文件在操作后被外部修改，确认撤销？(y/n)` | Confirm before undo |

---

## State Schema

```jsonc
{
  "version": 1,
  "active": "<feature-name>",
  "features": {
    "<feature-name>": {
      "name": "<feature-name>",
      "requirement": "<path>",
      "plan": "<path>",
      "status": "DRAFT|PLANNED|IN_PROGRESS|DONE|BLOCKED",
      "current_task": 0,
      "tasks_total": 0,
      "tasks": [
        {
          "id": 1,
          "name": "<task-name>",
          "status": "pending|in_progress|done|failed",
          "tests_total": 0,
          "tests_passed": 0,
          "fixes": 0,
          "report": "<path>"
        }
      ],
      "tests_passed": 0,
      "tests_failed": 0,
      "tests_fixed": 0,
      "started_at": "<ISO8601>",
      "completed_at": null,
      "blocked_reason": null,
      "last_undo": null
    }
  }
}
```

---

## History Schema

```jsonc
{
  "timestamp": "<ISO8601>",
  "action": "start|plan|run|task|fix",
  "feature": "<name>",
  "before": { /* complete state.json snapshot */ },
  "after": { /* complete state.json snapshot */ },
  "files_created": ["<path>", "..."],
  "files_modified": [
    { "path": "<path>", "before_hash": "<sha256>" }
  ],
  "undone": false
}
```
