# Test Report: Task {{task_id}} — {{task_name}}

> **Feature**: {{feature_name}}
> **Timestamp**: {{ISO8601}}
> **Status**: {{PASS | FAIL | FIXED}}

## Result

| Metric | Count |
|--------|-------|
| ✅ Passed | {{tests_passed}} |
| ❌ Failed | {{tests_failed}} |
| 🔧 Auto-fixed | {{tests_fixed}} |

## RED Phase

```
{{red_observation}}
```

## GREEN Phase

```
{{green_observation}}
```

## Self-Review Checklist

- [ ] Function length ≤ 40 lines
- [ ] File length ≤ 400 lines
- [ ] No `any` / `object` types
- [ ] Error handling explicit
- [ ] No TODO/FIXME/HACK

## Verdict

**{{PASS | FAIL | BLOCKED}}** — {{summary}}
