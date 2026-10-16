# Artifacts: {{feature_name}}

> **Requirement**: ../requirements/{{date}}-{{feature}}.md
> **Plan**: ../plans/{{date}}-{{feature}}.md
> **Generated**: {{ISO8601}}

<!-- 本文件是索引，不是容器。产物文件留在项目标准位置（migrations/、scripts/、config/）。 -->
<!-- 每个产物文件头部应有反向引用注释，指向本文件。 -->

## Database

| Path | Task | Purpose | Status | Executed | Verified |
|------|------|---------|--------|----------|----------|
| `{{path}}` | {{task_id}} | {{purpose}} | created | ⬜ | ⬜ |

## Batch

| Path | Task | Purpose | Status | Executed |
|------|------|---------|--------|----------|
| `{{path}}` | {{task_id}} | {{purpose}} | created | ⬜ |

## Config

| Path | Task | Purpose | Status |
|------|------|---------|--------|
| `{{path}}` | {{task_id}} | {{purpose}} | created |

## Execution Log

<!-- 产物被真实执行时追加记录：时间 + 命令 + 结果 -->
- {{timestamp}} `{{path}}` → {{result}}
