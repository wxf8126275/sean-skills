# 需求：{{feature_name}}

> **状态**：DRAFT | PLANNED | IN_PROGRESS | DONE | BLOCKED
> **创建日期**：{{date}}

---

## Problem

{{one_sentence_problem_statement}}

## Behaviors

- {{behavior_1}}
- {{behavior_2}}

## Acceptance Criteria

- [ ] {{criterion_1}} → verifiable by {{test_or_demo}}
- [ ] {{criterion_2}} → verifiable by {{test_or_demo}}

## Artifacts (expected)

> 需求文档只声明**需要什么类型**的产物，不声明具体路径。
> 具体路径由 `sean plan` 决定，索引写入 `docs/artifacts/<date>-<feature>.md`。

- **Database**: {{db_scripts}} — e.g. 用户表结构（建表 SQL）
- **Batch**: {{batch_scripts}} — e.g. 管理员账号初始化脚本
- **Config**: {{config_files}} — e.g. JWT 密钥配置模板

## Context

- **Tech stack**: {{tech_stack}}
- **Related features**: {{dependencies}}
- **Constraints**: {{performance_security_compat}}
- **Non-goals**: {{what_this_does_not_do}}
