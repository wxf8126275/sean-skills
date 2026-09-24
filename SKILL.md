---
name: sean
description: "AI-Native Team Development Workflow: standardizes how AI agents produce transferable knowledge — any AI can take over any other AI's work, even across context resets or model changes. Zero external dependencies."
version: 3.1.0
trigger: sean
---

# Sean — AI-Native Team Development Workflow

## 定位

规范 AI Agent 在团队中的开发行为。**核心目标：知识可传承**——任何 AI 接手其他 AI 的产出时，不需要问"这个功能怎么做的、文件在哪、下一步是什么"；甚至同一个 AI 在上下文丢失后，也能从文档中无缝恢复现场。

## Trigger

Activated when user input starts with `sean ` (case-insensitive).

## Global Rules

- **Self-contained**: Do NOT call any external skill. All logic is defined here.
- **AI-Native**: 定义 AI Agent 在团队中如何工作——不是定义人如何工作。
- **Knowledge-First**: 交接文档和项目知识比任务状态更重要——AI 可以换，项目不能丢。
- **Project-aware**: Read `AGENTS.md` if it exists and obey its constraints.
- **State tracking**: Maintain `docs/.sean/state.json` for progress tracking.
- **History tracking**: Save a snapshot to `docs/.sean/history/` before any mutating operation.
- **Test-first**: Always write the failing test BEFORE implementation code.
- **Never modify tests to pass**: Tests are the spec. Fix the implementation.

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
│   │       ├── summary.md
│   │       ├── handoff.md
│   │       └── review.md
│   ├── team/
│   │   ├── conventions.md
│   │   └── onboarding.md
│   └── .sean/
│       ├── state.json
│       ├── active
│       └── history/
│           └── <timestamp>-<action>.json
```

---

## Command: `sean init <project-name>`

**One-time setup for a new project.**

### Steps

1. Create `docs/team/conventions.md` (template embedded below).
2. Create `docs/team/onboarding.md` — AI-readable project primer (tech stack, directory layout, key patterns).
3. Initialize `docs/.sean/state.json` with empty features.
4. Output: list of created files.

### `conventions.md` Template (embedded)

```markdown
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
```

---

## Command: `sean start <name> [description...]`

### Steps

1. **Validate name**: Must be lowercase kebab-case (regex: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`).
2. **Check existence**: If requirement exists, ask before overwriting.
3. **Gather requirements**:
   - If `[description...]` provided: use as problem statement.
   - If no description: ask 3 questions:
     - "这个功能解决什么问题？（一句话）"
     - "关键行为是什么？（逗号分隔）"
     - "验收标准是什么？（逗号分隔）"
4. **Create requirement file** at `docs/requirements/<date>-<name>.md`:
   ```markdown
   # <Feature Name>

   ## Problem
   <one sentence — what user/business pain does this solve?>

   ## Behaviors
   - <behavior 1>
   - <behavior 2>

   ## Acceptance Criteria
   - <criterion 1> → verifiable by <test/manual/demo>
   - <criterion 2> → verifiable by <test/manual/demo>

   ## Context
   - Tech stack: <inferred or stated>
   - Related features: <list known dependencies>
   - Constraints: <performance/security/compat constraints>
   - Non-goals: <what this feature explicitly does NOT do>
   ```
5. **Update state**: create entry in `state.json` → `features.<name>` with `status: "DRAFT"`. Set `active`.
6. **Save history**: Record `start` action snapshot.
7. **Output**: file path, status, next step (`sean plan <name>`).

---

## Command: `sean plan <name>`

### Steps

1. **Load requirement**. Error if missing.
2. **Load conventions** from `docs/team/conventions.md` (or use embedded default).
3. **Analyze**: Extract functional points + acceptance criteria from requirement.
4. **Decompose** into TDD tasks following this architecture order:
   - Database: schema, migration, entity
   - Service: business logic, validation
   - Controller: API endpoints, DTOs
   - Permissions: authorization, guards
   - Integration: external services, WebSocket, background jobs
   - Frontend: UI components, pages
5. **For each task**, define:
   - `id`: sequential number
   - `name`: short kebab-case identifier
   - `files_create`: exact file paths to create
   - `files_modify`: existing files to modify
   - `test_file`: exact test file path
   - `steps`: ordered TDD steps (red → green → verify)
   - `acceptance`: how to verify
   - `depends_on`: list of task ids (or empty)
   - `estimated_complexity`: `low` | `medium` | `high`
   - `parallel_safe`: boolean (can run concurrently with other tasks?)
6. **Validate**: no circular dependencies, all tasks have unique names.
7. **Write plan** to `docs/plans/<date>-<name>.md`:
   ```markdown
   # Plan: <Feature Name>

   Generated: <ISO8601>
   Requirement: ../requirements/<date>-<feature>.md

   ## Task Summary

   | # | Task | Depends On | Complexity | Parallel Safe |
   |---|------|-----------|------------|---------------|
   | 1 | ...  | —         | low        | yes           |
   | 2 | ...  | 1         | medium     | no            |
   | 3 | ...  | 1         | low        | yes           |

   ## Dependency Graph
   Task 1 → Task 2
   Task 1 → Task 3

   ## Task Details

   ### Task 1: <name>
   - **Creates**: `<files>`
   - **Modifies**: `<files>`
   - **Test**: `<path>`
   - **Acceptance**: <criteria>
   ```
8. **Update state**: `status: "PLANNED"`, `tasks_total`, initialize `tasks[]` with complexity and parallel_safe fields.
9. **Save history**: Record `plan` action.
10. **Output**: task list summary, next step (`sean run <name> --dry-run`).

---

## Command: `sean run <name> [start_n] [--dry-run] [--no-fix]`

### Pre-flight

1. Load plan from `docs/plans/<date>-<name>.md`. Error if missing.
2. Load state, resolve feature entry.
3. Determine start task index (default 1, or `start_n`).

### If `--dry-run`

Do NOT execute any code. Only:
1. Parse all tasks from plan.
2. Print table: `# | Task | Complexity | Depends On | Parallel Safe`.
3. Validate dependencies (no cycles).
4. Estimate total tests and time.
5. Output: `sean run <name>` to execute.

### If executing (no `--dry-run`)

**Save history snapshot before starting** (for undo).

For each task from `start_n` to end:

#### Task Execution Loop (AI Agent Contract)

1. **Check dependencies**: Verify all `depends_on` tasks have `status: "done"`. If not, warn and offer to skip/run dependency first.
2. **Mark task**: `status: "in_progress"` in state.
3. **Context Loading** — Before writing ANY code, the agent MUST:
   - Read the test file path's directory to understand existing test patterns and conventions.
   - Read all files in `files_modify` to understand current implementation and avoid breaking changes.
   - Read `docs/team/conventions.md` (or embedded default) for style/structure rules.
   - Read any files in `files_create`'s parent directory to match existing code style.
4. **Write failing test** in `test_file`:
   - **Test Quality Gate**: MUST contain at least one meaningful assertion that verifies the BEHAVIOR described in the task.
   - INVALID tests: `assert True`, `assert 1 == 1`, empty test body, no assertions, testing implementation details instead of behavior.
   - If the test is invalid → rewrite before proceeding.
   - Test must be specific enough that RED actually means "feature not yet implemented" not "typo in test".
5. **Run test**: Execute the test file. Expected FAIL/RED.
   - If test PASSES immediately → the test is wrong (tests existing behavior). Fix the test.
   - If test ERRORS (not fails) → fix the test setup.
   - **RED Confirmation**: Log the exact assertion that failed and WHY (this proves the test exercises new behavior).
   - If the test file is empty or doesn't exist → write it properly before re-running.
6. **Write minimal implementation** to make the test pass.
7. **Run test** again. Expected PASS/GREEN.
8. **If GREEN**:
   - **Verify test actually exercised the behavior**: Re-read the test file and confirm assertions are meaningful (not trivially passing).
   - **Re-run from scratch** (fresh process): Confirm it still passes cleanly (no warnings-as-errors, no skipped tests).
   - **Self-review** the implementation against conventions:
     - Function length ≤ 40 lines?
     - No `any` types?
     - Error handling explicit?
     - No TODO/FIXME?
   - Write test report.
   - Mark task `status: "done"`.
   - Continue to next task.
9. **If RED** (implementation fails):
   - **`--no-fix`**: Mark task `status: "failed"`, STOP. Output failure details.
   - **Default (auto-fix)**: Enter Fix Loop:
     ```
     for attempt in 1..3:
       a. Read FULL error output (not just last line)
       b. Analyze root cause (import? logic? missing dep? type mismatch? wrong API?)
       c. Read the relevant source file for context — understand WHY it failed
       d. Modify implementation (NEVER the test)
       e. Re-run test
       f. If GREEN: break, continue
       g. If still RED AND root cause unchanged: break early (don't waste attempts)
       h. If still RED: continue loop
     ```
   - After 3 attempts (or early break on same root cause) still RED: Mark task `status: "failed"`, STOP.
   - **Fix quality gate**: After fix, re-read the diff and confirm the fix addresses the root cause (not just silencing the error).
10. **Check consecutive failures**: If 2 consecutive tasks failed, ABORT entire run. Output blocker report.

#### Post-execution (Knowledge Handoff)

1. **End-to-end regression**: Run ALL test files for this feature in one command (e.g. `pytest <test_dir>/ -v`).
   - If any test fails despite individual task GREEN → mark overall `INTEGRATION_FAIL` and list conflicts.
2. **Handoff Summary** — generate `docs/test-reports/<date>-<feature>/handoff.md` (see `sean handoff` for format).
3. **Suggested Commit Message** (conventional format):
   ```
   feat(<scope>): implement <feature-name>

   - <task 1 summary>
   - <task 2 summary>

   Tests: N passed
   Regression: passed
   ```
4. **Update state**: `current_task`, overall status (`DONE` only if all individual + regression pass, `BLOCKED` or `INTEGRATION_FAIL` if failed).
5. **Output final report**: per-task status + regression status + commit suggestion + handoff path.

---

## Command: `sean task <name> <n> [--dry-run] [--no-fix]`

Same as `sean run` but only executes task `<n>`. Does not check dependencies (user's responsibility).

---

## Command: `sean handoff <name>`

**生成交接文档——让另一个 AI 或人类能无缝接手。**

这是本技能最核心的协作命令。触发场景：

- Agent-A 完成了，换 Agent-B 继续开发
- 同一个 Agent 但会话被清空（上下文丢失），需要恢复现场
- 人类想检查 AI 做了什么

### Steps

1. Read state, find feature.
2. Read latest test report.
3. Read all `files_create` and `files_modify` from plan.
4. Read the actual source files that were created/modified (verify disk vs plan).
5. Generate handoff document at `docs/test-reports/<date>-<name>/handoff.md`:
   ```markdown
   # Handoff: <Feature Name>

   ## Status
   - Overall: DONE | BLOCKED | INTEGRATION_FAIL
   - Tasks completed: N / Total
   - Last updated: <ISO8601>

   ## What Was Done
   | Task | Status | Summary |
   |------|--------|---------|
   | 1    | done   | <what it does> |
   | 2    | failed | <what it does> |

   ## File Inventory (verified on disk)

   ### Created
   - `<path>` — <purpose>

   ### Modified
   - `<path>` — <what changed>

   ### Tests
   - `<path>` — <behavior covered>

   ## Current Blocker (if any)
   - <why blocked + what was tried>

   ## Next Steps (for whoever takes over)
   1. <specific action 1>
   2. <specific action 2>

   ## Known Risks / TODOs
   - <risk 1>

   ## How to Resume
   ```bash
   cd <project>
   sean status <name>        # check current state
   sean run <name>           # resume full run (if BLOCKED)
   sean task <name> N        # run specific task
   <test command>             # e.g. pytest tests/ -v
   ```
   ```
6. Output handoff path + print condensed summary to terminal.

---

## Command: `sean sync <name>`

**Recovery command: sync state from test reports back to state.json.**

Use when state.json gets out of sync with actual test results (e.g., process killed mid-run).

### Steps

1. Scan `docs/test-reports/<date>-<name>/` for all `task-*.md` files.
2. Re-derive each task's status from report content:
   - Report exists and says "PASS" → `done`
   - Report exists and says "FAIL" → `failed`
   - No report → `pending`
3. Rebuild state from reports.
4. Output diff between old state and new state.
5. Ask before overwriting.

---

## Command: `sean review <name>`

**AI self-review pass after all tasks pass.** Checks output quality against conventions.

### Steps

1. Read all created/modified files from plan.
2. For each file, check against conventions:
   - Function length ≤ 40 lines?
   - File length ≤ 400 lines?
   - No `any` / `object` types?
   - Error handling present (no bare `except:` or empty catch)?
   - No `TODO` / `FIXME` / `HACK` / `XXX` comments left?
3. Check test quality:
   - All tests have meaningful assertions?
   - No `assert True` or trivially passing tests?
   - Tests don't depend on implementation details?
   - RED was actually observed (test reports mention red phase)?
4. Output review report:
   ```
   ## Review: <Feature Name>

   ### File Quality
   | File | Func Len | File Len | Any Types | Error Handling | Clean |
   |------|----------|----------|-----------|----------------|-------|
   | ...  | ✓/✗     | ✓/✗     | ✓/✗      | ✓/✗           | ✓/✗  |

   ### Test Quality
   | Test File | Meaningful | No TrivDeps | RED Observed | Clean |
   |-----------|------------|-------------|--------------|-------|
   | ...       | ✓/✗       | ✓/✗        | ✓/✗         | ✓/✗  |

   ### Verdict
   PASS / FAIL (N issues)
   ```
5. Write to `docs/test-reports/<date>-<name>/review.md`.

---

## Command: `sean fix [name]`

1. If `[name]` not provided, read `active` from state.
2. Find the most recent task with `status: "failed"`.
3. Read the corresponding test report.
4. Run tests to reproduce.
5. Analyze root cause → fix code (not tests) → re-run.
6. If GREEN: update task `status: "done"`.
7. If still RED: output failure + suggest `sean undo` or manual fix.

---

## Command: `sean undo [name] [steps]`

1. If `[name]` not provided, read `active`.
2. `steps` default = 1.
3. Find most recent `undone: false` history entry.
4. **Restore**: delete `files_created`, restore `files_modified` from snapshot or git.
5. **Restore state** from snapshot.
6. Mark history entry `undone: true`.
7. If `steps > 1`: repeat.

---

## Command: `sean retry <name>`

1. Find most recent `status: "failed"` task.
2. Execute `sean task <name> <n> --no-fix`.

---

## Command: `sean list`

1. Read `state.json`.
2. For each feature: `name`, `status`, `tasks_done/total`, `tests_passed`, `report_exists`.
3. Sort by `started_at` descending.
4. Highlight `active`.

---

## Command: `sean status <name>`

1. Read state, find feature.
2. Print: requirement path, plan path, status, progress bar, task list with per-task status.
3. If `BLOCKED`: print `blocked_reason`.
4. If `INTEGRATION_FAIL`: print which tasks conflict.

---

## Command: `sean report [name] [--summary]`

1. If `[name]` not provided, read `active`.
2. Scan test reports directory.
3. Aggregate: total tests, passed, failed, fixed.
4. Print table.
5. If `--summary`: also write `summary.md`.

---

## Command: `sean switch <name>`

1. Verify feature exists.
2. Update `active`.
3. Print switched status.

---

## Command: `sean clean [--keep-reports]`

1. Confirm.
2. Delete `docs/.sean/`.
3. If `--keep-reports`: preserve `docs/test-reports/`.
4. Output: "已清理".

---

## Command Quick Reference

```
sean init <project>              # 首次初始化项目（生成规范+onboarding）
sean start <name> [desc...]      # 创建需求文档
sean plan <name>                 # 拆解为 TDD 任务
sean run <name> [--dry-run]      # 执行任务（TDD + 回归 + 交接文档）
sean task <name> <n>             # 执行单个任务
sean handoff <name>              # 生成交接文档（另一 AI 接手用）
sean sync <name>                 # 从测试报告恢复状态（上下文丢失时用）
sean review <name>               # 代码质量自审
sean fix [name]                  # 修复最近失败的任务
sean undo [name] [steps]         # 撤销操作（文件+状态）
sean retry <name>                # 重试最近失败的任务
sean list                        # 列出所有功能
sean status <name>               # 查看单个功能状态
sean report [name] [--summary]   # 测试报告汇总
sean switch <name>               # 切换当前活跃功能
sean clean [--keep-reports]      # 清理所有 sean 状态
```

---

## Error Handling

| Error | Message | Action |
|-------|---------|--------|
| Feature not found | `功能 <name> 不存在。现有: <list>` | Suggest `sean list` |
| Plan not found | `计划不存在。运行: sean plan <name>` | — |
| Requirement not found | `需求不存在。运行: sean start <name>` | — |
| Dependency not met | `Task N 依赖 Task M (未完成)` | Offer to run dependency |
| Test timeout (>60s) | `测试运行超时` | Offer skip/retry |
| 2 consecutive failures | `连续失败，中止。查看报告: sean report <name>` | STOP |
| No failed report | `没有失败的测试报告` | — |
| Nothing to undo | `没有可撤销的操作` | — |
| Invalid name | `名称非法: 仅小写字母/数字/连字符` | — |

---

## State Schema

```jsonc
{
  "version": 2,
  "active": "<feature-name>",
  "features": {
    "<feature-name>": {
      "name": "<feature-name>",
      "requirement": "<path>",
      "plan": "<path>",
      "status": "DRAFT|PLANNED|IN_PROGRESS|DONE|BLOCKED|INTEGRATION_FAIL",
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
          "complexity": "low|medium|high",
          "parallel_safe": true,
          "report": "<path>"
        }
      ],
      "tests_passed": 0,
      "tests_failed": 0,
      "tests_fixed": 0,
      "started_at": "<ISO8601>",
      "completed_at": null,
      "blocked_reason": null
    }
  }
}
```

## History Schema

```jsonc
{
  "timestamp": "<ISO8601>",
  "action": "start|plan|run|task|fix|review",
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

---

## AI Agent Output Checklist

Every time an AI agent finishes a `sean run`, it MUST self-certify:

```
□ Tests: ALL passing (verified by re-run from scratch)
□ Regression: full feature test suite passes
□ Conventions: code style complies with team/conventions.md
□ No trivia: no `assert True`, no empty tests, no skipped tests
□ Handoff: handoff.md generated with status + next steps
□ Commit: conventional commit message suggested
□ State: state.json updated correctly
```

If any checkbox cannot be ticked → do NOT mark as DONE. Mark as BLOCKED with reason.
