# 实现计划：{{feature_name}}

> **来源需求**：{{requirement_path}}
> **执行者**：agent
> **创建日期**：{{date}}

## Goal

{{one_sentence_goal}}

## Architecture

{{two_three_sentences}}

## Tech Stack

{{tech_stack}}

---

{{#each tasks}}

## Task {{id}}: {{name}}

**Files**:
- Create: `{{files_create}}`
- Modify: `{{files_modify}}`
- Test: `{{test_file}}`

**Steps**:
{{#each steps}}
- [ ] {{this}}
{{/each}}

**Acceptance**: {{acceptance}}

{{#if depends_on}}
**Depends on**: {{depends_on}}
{{/if}}

---

{{/each}}
