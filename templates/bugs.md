# Bugs: {{feature_name}}

> 只记录 `sean run` 完成后由 task 测试之外途径发现的缺陷。
> 状态与 `features/{{feature}}.json` 的 `bugs[]` 保持同步。

---

## B001: {{symptom}}

- **Classification**: implementation | spec-gap
- **Task**: {{task_id}} ({{task_name}})
- **Found by**: user-manual | production
- **Status**: open | fixing | fixed | wontfix
- **Created**: {{ISO8601}}

### Symptom

{{user_description}}

### Reproduction

1. {{step_1}}
2. {{step_2}}

### Root Cause

{{root_cause}}

### Fix

{{what_changed — 文件 + 关键改动行}}

### Regression Test

{{test_name}} in `{{test_file}}`

<!-- 该测试必须在修复前为 RED，否则不构成回归保护 -->

---

<!-- 追加新 bug 时复制上面的块，编号递增 -->
