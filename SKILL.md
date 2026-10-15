---
name: sean
description: "AI-Native Team Development Workflow: standardizes how AI agents produce transferable knowledge — any AI can take over any other AI's work, even across context resets or model changes. Zero external dependencies."
version: 3.4.0
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
4. **Parallel Detection**: Scan all tasks from `start_n` to end. If 2+ tasks have `parallel_safe: true` AND their `depends_on` are all `done` (or they have no unmet dependencies), present the user with a choice:
   ```
   ⚡ 检测到 N 个可并行任务: Task 2, 3, 5

   是否启用子智能体并行执行？
     是 — 并行分发，总耗时缩短，需额外上下文传递
     否 — 串行执行（默认）
   ```
   - If user chooses **Yes** → proceed to Parallel Execution Protocol (see below).
   - If user chooses **No** → proceed with serial execution (default behavior).
   - If only 1 task is parallel_safe → skip the prompt, proceed serial.

### Parallel Execution Protocol

When user opts into parallel execution:

1. **Group tasks** by dependency waves:
   - Wave 1: Tasks with no unmet dependencies (all `depends_on` are `done` or empty).
   - Wave 2: Tasks whose dependencies are all in Wave 1.
   - Continue until all tasks are assigned to a wave.
2. **Within each wave**, identify tasks with `parallel_safe: true` that can run concurrently.
3. **Dispatch sub-agents** for concurrent tasks:
   - Each sub-agent receives a **Task Context Package** (see below).
   - Sub-agents run independently in isolated contexts.
   - Sub-agents do NOT write `state.json` directly — they return structured results.
4. **Collect results** from all sub-agents in the wave:
   - Parse each sub-agent's output for the structured result.
   - Update `state.json` with task status, tests passed/fixed, and report path.
   - If any sub-agent reports `failed` → mark task as `failed`, apply Fix Loop policy.
5. **Proceed to next wave** only after all tasks in current wave are resolved.
6. **After all waves complete** → run Post-execution (regression, handoff, etc.).

#### Task Context Package (for sub-agents)

Each sub-agent MUST receive:

```yaml
task_id: <number>
task_name: "<kebab-case-name>"
project_root: "<absolute path>"
conventions: "<full content of docs/team/conventions.md>"
test_pattern: "<content of an existing test file for reference>"
files_create: ["<path>", ...]
files_modify: ["<path>", ...]
test_file: "<path>"
tdd_contract:
  - "先写失败测试，确认 RED"
  - "写最小实现使测试 GREEN"
  - "禁止修改测试文件"
  - "Fix Loop 最多 3 次"
  - "如果 3 次后仍 RED → 返回 status: failed"
output_format:
  status: "done|failed"
  tests_total: <number>
  tests_passed: <number>
  fixes: <number>
  files_modified: ["<path>", ...]
  report: "<path to test report>"
  error_message: "<if failed>"
```

#### Sub-agent Result Contract

Each sub-agent MUST return a JSON block at the end of its output:

```json
{
  "task_id": 3,
  "status": "done",
  "tests_total": 4,
  "tests_passed": 4,
  "fixes": 1,
  "files_modified": ["src/service.py"],
  "report": "docs/test-reports/2026-09-29-myfeature/task-3-service.md",
  "error_message": null
}
```

If the sub-agent cannot complete the task, it returns:
```json
{
  "task_id": 3,
  "status": "failed",
  "tests_total": 4,
  "tests_passed": 2,
  "fixes": 3,
  "files_modified": ["src/service.py"],
  "report": null,
  "error_message": "ImportError: cannot import name 'foo' from 'bar'"
}
```

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

## Command: `sean dispatch <plan_path> [--start N] [--format json|yaml|text]`

**解析 plan，分组 dependency waves，生成子智能体任务描述。**

用于并行执行前的规划阶段。输出每个 wave 中哪些 task 可以并行、哪些必须串行。

### Steps

1. Parse plan markdown → Task objects (id, name, depends_on, parallel_safe, files, test_file).
2. Group tasks into dependency waves:
   - Wave 1: tasks with no unmet dependencies.
   - Wave 2: tasks whose dependencies are all in Wave 1.
   - Continue until all tasks assigned.
3. Within each wave, split into `parallel_safe_tasks` and `serial_tasks`.
4. For each parallel_safe task, generate a **Task Context Package** (YAML/JSON).
5. Output in specified format (default: text).

### Usage

```bash
# 查看 wave 分组（文本格式）
python3 scripts/sean_dispatch.py docs/plans/2026-09-29-myfeature.md

# JSON 格式（供程序消费）
python3 scripts/sean_dispatch.py docs/plans/2026-09-29-myfeature.md --format json

# 从 task 3 开始
python3 scripts/sean_dispatch.py docs/plans/2026-09-29-myfeature.md --start 3

# 带 conventions 和 test pattern
python3 scripts/sean_dispatch.py docs/plans/2026-09-29-myfeature.md \
  --conventions docs/team/conventions.md \
  --test-pattern tests/test_existing.py
```

### Output Example (text)

```
=== Wave 1 ===
  All tasks: [1]
  Parallel safe: [1]
  Serial: []

  --- Task 1: db-schema ---
  Creates: ['src/db/schema.py']
  Modifies: []
  Test: tests/test_schema.py
  Acceptance: Schema creates table with correct columns

=== Wave 2 ===
  All tasks: [2, 3]
  Parallel safe: [3]
  Serial: [2]

  --- Task 3: api-endpoints ---
  Creates: ['src/api.py']
  Modifies: []
  Test: tests/test_api.py
  Acceptance: API returns correct responses
```

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

   ## Reliability
   - Implemented by: <model-id> (<provider>)
   - Task first-pass rate: N/M (tasks that passed without fix loop)
   - Post-run bugs: N (found by: user-manual | production)
   - Trust level: HIGH | MEDIUM | LOW
     - HIGH: all bugs caught by task tests or regression
     - MEDIUM: 1-2 bugs found by user-manual, all fixed with regression tests
     - LOW: 3+ bugs or any production-found bug — recommend independent verification

   ## What Was Done
   | Task | Status | Summary | Implemented By |
   |------|--------|---------|----------------|
   | 1    | done   | <what it does> | <model-id> |
   | 2    | failed | <what it does> | <model-id> |

   ## File Inventory (verified on disk)

   ### Created
   - `<path>` — <purpose>

   ### Modified
   - `<path>` — <what changed>

   ### Tests
   - `<path>` — <behavior covered>

   ## Post-Run Bugs (if any)
   | ID | Symptom | Classification | Found By | Status | Regression Test |
   |----|---------|----------------|----------|--------|-----------------|
   | B001 | <symptom> | implementation | user-manual | fixed | `test_name` |

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
   sean bug <name> "desc"    # record a post-run bug
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

**AI self-review pass after all tasks pass.** Evaluates output quality against conventions AND assesses the Agent Work Loop across five dimensions.

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
4. **Five-Dimension Agent Work Loop Assessment**:

   For each dimension, assign evidence state and score (0-100):

   | Dimension | Question | Evidence States |
   |-----------|----------|-----------------|
   | **Task Understanding** | Did the agent understand the goal and "done" meaning? | `present` (requirement exists) → `wired` (acceptance criteria clear) → `exercised` (tasks map to criteria) → `outcome-supported` (regression proves it) |
   | **Controlled Execution** | Did work follow a supported, repeatable path? | `present` (plan exists) → `wired` (dependencies declared) → `exercised` (tasks executed in order) → `outcome-supported` (no circular deps) |
   | **Change Validation** | Is there evidence the change works? | `present` (test files exist) → `wired` (tests run) → `exercised` (RED→GREEN observed) → `outcome-supported` (regression passes) |
   | **Reliable Delivery** | Was the result accepted at the delivery boundary? | `present` (handoff exists) → `wired` (commit message ready) → `exercised` (human/CI accepted) → `outcome-supported` (deployed/merged) |
   | **Learning Capture** | Can the next task benefit from this one? | `present` (handoff exists) → `wired` (sync works) → `exercised` (next agent used handoff) → `outcome-supported` (later task faster) |

   **Score ceilings by evidence state:**
   - `missing` / `unobserved` / `not-applicable` → max 59
   - `present` → max 74
   - `wired` → max 84
   - `exercised` → max 94
   - `outcome-supported` → max 100

5. **Generate Findings** — for each dimension with evidence < `exercised`, create a finding:
   ```json
   {
     "id": "F001",
     "dimension": "change-validation",
     "severity": "high|medium|low",
     "evidence": "<what was observed>",
     "impact": "<consequence>",
     "repair": "<proposed fix>",
     "verifier": "<how to verify>",
     "status": "open"
   }
   ```
   - Only emit findings for inspected gaps with bounded impact and repair route.
   - Do NOT emit findings for `unobserved` external boundaries.
   - Severity: `high` = blocks delivery, `medium` = degrades quality, `low` = improvement opportunity.

6. Output review report:
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

   ### Agent Work Loop Assessment
   | Dimension | Evidence | Score | Finding |
   |-----------|----------|-------|---------|
   | Task Understanding | exercised | 85 | — |
   | Controlled Execution | wired | 70 | F001 |
   | Change Validation | outcome-supported | 95 | — |
   | Reliable Delivery | present | 60 | F002 |
   | Learning Capture | unobserved | 40 | — |

   ### Findings
   | ID | Dimension | Severity | Evidence | Repair |
   |----|-----------|----------|----------|--------|
   | F001 | controlled-execution | medium | Task 3 ran before Task 2 | Add dependency check |
   | F002 | reliable-delivery | high | No commit message generated | Add commit step |

   ### Verdict
   PASS / FAIL (N issues, M findings)
   ```
7. Write to `docs/test-reports/<date>-<name>/review.md`.
8. Update `state.json` with review scores and findings.

---

## Command: `sean learn <name>`

**Analyze historical test-reports to extract reusable patterns and lessons.**

This command closes the Learning Capture loop by turning repeated observations into durable improvements.

### Steps

1. Scan all `docs/test-reports/<date>-<name>/` directories for this project.
2. For each historical feature, extract:
   - **Repeated failure patterns**: Same root cause appearing in 2+ features (e.g., "type mismatch in DTO", "missing import in test setup")
   - **Repeated structural patterns**: Similar task decompositions that could become templates
   - **Repeated decisions**: Same architectural choices made independently (e.g., "always use repository pattern for DB access")
3. Generate `docs/team/lessons.md`:
   ```markdown
   # Lessons Learned

   ## Recurring Failure Patterns
   | Pattern | Features Affected | Root Cause | Prevention |
   |---------|------------------|------------|------------|
   | Type mismatch in DTO | comments, auth | Generated DTO doesn't match entity | Add DTO validation test |

   ## Reusable Templates
   | Template | Source Features | Applicability |
   |----------|----------------|---------------|
   | CRUD service pattern | comments, auth, audit | Any entity with standard CRUD |

   ## Architectural Decisions
   | Decision | Rationale | Applied In |
   |----------|-----------|------------|
   | Repository pattern for DB | Testability, swap implementations | comments, auth |

   ## Suggested Convention Updates
   - <convention 1>: <rationale>
   - <convention 2>: <rationale>
   ```
4. If patterns suggest convention updates, propose them (do NOT auto-apply).
5. Output: lessons file path + count of patterns found.

---

## Command: `sean findings [name]`

**List and manage findings from the Agent Work Loop assessment.**

### Steps

1. If `[name]` not provided, read `active` from state.
2. Read findings from `state.json` → `features.<name>.findings[]`.
3. Output table:
   ```
   | ID | Dimension | Severity | Status | Evidence |
   |----|-----------|----------|--------|----------|
   | F001 | change-validation | high | open | Test 3 has assert True |
   | F002 | reliable-delivery | medium | verified | No commit message |
   ```
4. If `--fix <id>` provided: mark finding as `verified` after confirming the repair.
5. If `--detail <id>` provided: show full finding with repair and verifier.

---

## Command: `sean export <name> --format <format>`

**Export sean workflow to other coding agent formats.**

### Supported Formats

| Format | Target | Output |
|--------|--------|--------|
| `claude-code` | Claude Code | `.claude/commands/sean.md` |
| `cursor` | Cursor | `.cursorrules` |
| `copilot` | GitHub Copilot | `.github/copilot-instructions.md` |
| `codex` | Codex | `.codex/config.toml` |

### Steps

1. Read the sean SKILL.md content.
2. Transform for target format:
   - **claude-code**: Wrap in `/sean` slash command format
   - **cursor**: Convert to rules format with frontmatter
   - **copilot**: Convert to instructions format
   - **codex**: Convert to TOML config with prompt
3. Write to appropriate location in target project.
4. Output: exported file path + format.

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

## Command: `sean bug <name> [description...] [--task N] [--already-fixed --files <f1,f2>]`

**记录并修复 `sean run` 完成后用户实测发现的 bug。**

这是 sean 的知识传承链中**唯一能捕获「测试没拦住、用户实测才发现」的缺陷**的入口。不记录的话，`sean sync`/`sean learn` 会把状态「恢复」成干净的 DONE，下一个 AI 完全不知道这个 bug 曾经存在。

### 两种模式

| 模式 | 触发 | 行为 |
|------|------|------|
| **主动式**（默认） | `sean bug <name> "描述"` | sean 驱动 TDD 修复：写复现测试→RED→修实现→GREEN→记录 |
| **追溯式** | `sean bug <name> "描述" --already-fixed --files src/foo.py` | 用户已在对话里修好了，sean 只补记录+补回归测试+强制跑一遍 |

### 设计原则

- **不重开 task**：task 确实完成了它声明的行为。bug 作为 feature 级独立条目挂在 `bugs[]`，用 `task_id` 反向关联。重开会让「已完成」的历史变模糊。
- **回归测试落点**：追加到原 `test_file`（同模块测试放一起）。
- **test-first 铁律**：bug 修复也必须先写复现测试。没有复现测试就不许标记修复完成。

### Steps

1. **Parse arguments**:
   - `<name>`: feature name.
   - `[description...]`: bug 症状描述（一句话）。
   - `--task N`: 关联的 task id（可选，用于反向定位）。
   - `--already-fixed`: 追溯模式标志。
   - `--files <f1,f2>`: 追溯模式下，用户已修改的文件列表。
2. **Load state**, find feature. Error if not found.
3. **Classify bug**:
   - **implementation**: 代码没做到 task 的 `acceptance` 说的 → 实现缺陷。
   - **spec-gap**: 代码做到了 AI 理解的，但用户要的是别的 → 需求文档修正。
   - 如果 `--task N` 提供，读该 task 的 `acceptance` 帮助分类。
4. **Record bug** in `state.json` → `features.<name>.bugs[]`:
   ```json
   {
     "id": "B001",
     "task_id": 3,
     "classification": "implementation|spec-gap",
     "symptom": "<user description>",
     "root_cause": null,
     "found_by": "user-manual|production",
     "status": "open|fixing|fixed|wontfix",
     "regression_test": null,
     "fixed_by": null,
     "files_modified": [],
     "created_at": "<ISO8601>",
     "resolved_at": null
   }
   ```
5. **Write bug report** to `docs/test-reports/<date>-<name>/bugs.md`:
   ```markdown
   # Bugs: <Feature Name>

   ## B001: <symptom>

   - **Classification**: implementation | spec-gap
   - **Task**: 3 (api-endpoints)
   - **Found by**: user-manual
   - **Status**: open

   ### Symptom
   <user description>

   ### Reproduction
   1. <step 1>
   2. <step 2>

   ### Root Cause
   <to be filled during fixing>

   ### Fix
   <to be filled during fixing>

   ### Regression Test
   <to be filled during fixing — test name + file>
   ```
6. **If 追溯模式** (`--already-fixed`):
   - Verify the fix: run the feature's full test suite.
   - **Write regression test**: append to the task's `test_file`. The test MUST reproduce the original bug (verify it would have failed before the fix).
   - Run the regression test → must PASS.
   - Update bug entry: `status: "fixed"`, `regression_test: "<test name>"`, `files_modified: [--files]`, `fixed_by: "<agent model>"`.
   - Update `bugs.md` with root cause + fix + regression test.
   - Save history snapshot (`action: "bug"`).
   - Output: bug recorded + regression test added.
7. **If 主动模式** (default):
   - **Write reproducing test**: append to the task's `test_file`. Test MUST FAIL (RED) — this proves it reproduces the bug.
   - Run test → confirm RED.
   - **Fix implementation** (NEVER the test).
   - Run test → must PASS (GREEN).
   - Run full feature regression → must PASS.
   - Update bug entry: `status: "fixed"`, `regression_test`, `root_cause`, `fixed_by`, `files_modified`.
   - Update `bugs.md` with all sections filled.
   - Save history snapshot (`action: "bug"`).
   - Output: bug fixed + regression test added.
8. **If spec-gap classification**:
   - Also update `docs/requirements/<date>-<name>.md` — correct the requirement so the next AI doesn't repeat the same misunderstanding.
   - Flag the requirement diff in `bugs.md`.
9. **Update feature status**:
   - If any bug `status: "open"` or `"fixing"` → feature `status` must NOT be `DONE`. Set to `IN_PROGRESS` or add `post_done_bugs` count.
   - Only when all bugs are `fixed` or `wontfix` → feature can return to `DONE`.
10. **Update handoff.md** — add Reliability section (see `sean handoff`).
11. **Output**: bug id, classification, status, regression test path, next step.

### Usage

```bash
# 主动式：描述 bug，sean 驱动 TDD 修复
sean bug auth "登录后刷新页面跳回登录页" --task 3

# 追溯式：已在对话里修好了，补记录+补回归测试
sean bug auth "登录后刷新页面跳回登录页" --already-fixed --files src/auth.py

# 多文件修改
sean bug api "分页参数不生效" --already-fixed --files src/api.py,src/service.py
```

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
                                 # 有可并行 task 时会询问是否启用子智能体
sean dispatch <plan> [--format]  # 解析 plan，分组 waves，生成子智能体任务描述
sean task <name> <n>             # 执行单个任务
sean handoff <name>              # 生成交接文档（另一 AI 接手用）
sean sync <name>                 # 从测试报告恢复状态（上下文丢失时用）
sean review <name>               # 五维评估 + 代码质量自审 + 发现生成
sean learn <name>                # 从历史报告提取可复用模式（学习沉淀）
sean findings [name]             # 查看/管理 Agent Work Loop 发现
sean fix [name]                  # 修复最近失败的任务
sean bug <name> [desc] [--task N] [--already-fixed --files f1,f2]
                                 # 记录/修复 run 后实测发现的 bug（test-first）
sean undo [name] [steps]         # 撤销操作（文件+状态）
sean retry <name>                # 重试最近失败的任务
sean list                        # 列出所有功能
sean status <name>               # 查看单个功能状态
sean report [name] [--summary]   # 测试报告汇总
sean switch <name>               # 切换当前活跃功能
sean export <name> --format <f>  # 导出到其他 agent 格式
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
| Bug already fixed | `bug <id> 已修复，无需重复操作` | — |
| Bug not found | `bug <id> 不存在。现有: <list>` | — |

---

## State Schema

```jsonc
{
  "version": 4,
  "active": "<feature-name>",
  "agent": {
    "model": "<model-id>",
    "provider": "<provider>"
  },
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
          "evidence": "present|wired|exercised|outcome-supported|missing|unobserved",
          "tests_total": 0,
          "tests_passed": 0,
          "fixes": 0,
          "complexity": "low|medium|high",
          "parallel_safe": true,
          "report": "<path>",
          "implemented_by": "<model-id>"
        }
      ],
      "tests_passed": 0,
      "tests_failed": 0,
      "tests_fixed": 0,
      "started_at": "<ISO8601>",
      "completed_at": null,
      "blocked_reason": null,
      "review": {
        "task-understanding": { "score": 0, "evidence": "unobserved" },
        "controlled-execution": { "score": 0, "evidence": "unobserved" },
        "change-validation": { "score": 0, "evidence": "unobserved" },
        "reliable-delivery": { "score": 0, "evidence": "unobserved" },
        "learning-capture": { "score": 0, "evidence": "unobserved" }
      },
      "findings": [
        {
          "id": "F001",
          "dimension": "change-validation",
          "severity": "high|medium|low",
          "evidence": "<what was observed>",
          "impact": "<consequence>",
          "repair": "<proposed fix>",
          "verifier": "<how to verify>",
          "status": "open|verified|partial|blocked"
        }
      ],
      "bugs": [
        {
          "id": "B001",
          "task_id": 3,
          "classification": "implementation|spec-gap",
          "symptom": "<user description>",
          "root_cause": "<root cause>",
          "found_by": "task-test|regression|review|user-manual|production",
          "status": "open|fixing|fixed|wontfix",
          "regression_test": "<test name>",
          "fixed_by": "<model-id>",
          "files_modified": ["<path>"],
          "created_at": "<ISO8601>",
          "resolved_at": "<ISO8601>"
        }
      ]
    }
  }
}
```

## History Schema

```jsonc
{
  "timestamp": "<ISO8601>",
  "action": "start|plan|run|task|fix|bug|review",
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
□ Review: five-dimension assessment completed with evidence states
□ Findings: all high-severity findings have repair plans
□ Bugs: post-run bugs recorded with regression tests (bugs.md + state.json bugs[])
```

If any checkbox cannot be ticked → do NOT mark as DONE. Mark as BLOCKED with reason.
