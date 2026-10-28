# Handoff: {{feature_name}}

> Generated: {{ISO8601}} · From `sean_state.py get {{feature}} --full`

## Status

- Overall: DONE | BLOCKED | INTEGRATION_FAIL
- Tasks completed: {{done}} / {{total}}
- Tests: {{tests_passed}} passed
- Last updated: {{ISO8601}}

## Reliability

- Implemented by: {{model_id}} ({{provider}})
- Task first-pass rate: {{first_pass}}/{{total}} (no fix-loop)
- Post-run bugs: {{post_run_bugs}} (found by: user-manual | production)
- Trust level: HIGH | MEDIUM | LOW
  - HIGH: all bugs caught by task tests or regression
  - MEDIUM: 1-2 user-manual bugs, fixed with regression tests
  - LOW: 3+ bugs or any production-found bug — recommend independent verification

## What Was Done

| Task | Status | Summary | Implemented By |
|------|--------|---------|----------------|
| 1 | done | {{summary}} | {{model_id}} |

## File Inventory (verified by existence, not content)

### Created
- `{{path}}` — {{purpose}}

### Modified
- `{{path}}` — {{what changed}}

### Tests
- `{{path}}` — {{behavior covered}}

## Artifacts

- Catalog: `docs/artifacts/{{date}}-{{feature}}.md`

| Path | Type | Task | Status | Executed | Verified |
|------|------|------|--------|----------|----------|
| `{{path}}` | database | 1 | created | ⬜ | ⬜ |

> 产物留在项目标准位置（`migrations/`、`scripts/`、`config/`），本表是索引。

## Post-Run Bugs

| ID | Symptom | Classification | Found By | Status | Regression Test |
|----|---------|----------------|----------|--------|-----------------|
| B001 | {{symptom}} | implementation | user-manual | fixed | `{{test_name}}` |

<!-- 无 bug 时写：None -->

## Current Blocker

<!-- 无则写 None；有则写：为什么阻塞 + 已试过什么 -->

## Next Steps

1. {{specific_action_1}}
2. {{specific_action_2}}

## Known Risks / TODOs

- {{risk}}

## How to Resume

```bash
cd {{project_root}}
python3 {{sean_root}}/scripts/sean_state.py get {{feature}} --full   # 当前状态
python3 {{sean_root}}/scripts/sean_state.py list                     # 所有 feature
{{test_command}}                                                     # 如 pytest tests/ -q
```

<!-- 恢复顺序：先 get --full 取状态 → 需要细节再读 plan → 只读相关源码片段，不要全量扫描 -->
