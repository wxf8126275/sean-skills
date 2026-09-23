# 测试报告：Task {{task_id}} — {{task_name}}

> **所属功能**：{{feature_name}}
> **执行时间**：{{timestamp}}
> **执行者**：agent

## 结果摘要

| 指标 | 数值 |
|------|------|
| ✅ 通过 | {{tests_passed}} |
| ❌ 失败 | {{tests_failed}} |
| ⏭️ 跳过 | {{tests_skipped}} |
| 🔧 自动修复 | {{tests_fixed}} |

## 失败详情

{{#each failures}}
### ❌ {{test_name}}
```
{{error_output}}
```

**根因**：{{root_cause}}
**修复方式**：{{fix_action}}

{{/each}}

## 结论

**状态**：{{final_status}}
