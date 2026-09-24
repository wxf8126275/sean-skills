# Handoff: {{feature_name}}

> **Generated**: {{ISO8601}}
> **Source**: sean run / sean handoff

## Status

- **Overall**: DONE | BLOCKED | INTEGRATION_FAIL
- **Tasks completed**: N / Total
- **Last updated**: {{ISO8601}}

## What Was Done

| Task | Status | Summary |
|------|--------|---------|
| 1    | done   | {{summary}} |
| 2    | done   | {{summary}} |
| 3    | failed | {{summary}} |

## File Inventory (verified on disk)

### Created

- `{{path}}` — {{purpose}}

### Modified

- `{{path}}` — {{what_changed}}

### Tests

- `{{path}}` — {{behavior_covered}}

## Current Blocker (if any)

- **Issue**: {{description}}
- **What was tried**: {{attempts}}
- **Suggested direction**: {{next_attempt}}

## Next Steps (for whoever takes over)

1. {{specific_action_1}}
2. {{specific_action_2}}

## Known Risks / TODOs

- {{risk_1}}

## How to Resume

```bash
cd {{project_root}}
sean status {{feature_name}}        # check current state
sean run {{feature_name}}           # resume full run (if BLOCKED)
sean task {{feature_name}} N        # run specific task
{{test_command}}                     # e.g. pytest tests/ -v
```
