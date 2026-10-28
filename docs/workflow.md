# sean 工作流详解

> v5 说明：precise 流程定义在 `references/cmd-*.md`，本文是概览。状态读写一律通过 `scripts/sean_state.py`。

## 需求阶段：`sean start`

### 交互模式

未提供描述时，一次问完 3 个问题（不要逐条往返）：

```
? 这个功能解决什么问题？（一句话）
? 关键行为是什么？（逗号分隔）
? 验收标准是什么？（逗号分隔）
```

### 产出的需求文档

模板：`templates/requirement.md`

```markdown
# 需求：comments

## Problem
用户需要在文档中添加评论

## Behaviors
- 在文档下方显示评论输入框
- 提交评论后实时显示

## Acceptance Criteria
- 能成功提交评论 → verifiable by test
- 评论显示在文档下方 → verifiable by demo
- 空评论提交被拒绝 → verifiable by test

## Context
- Tech stack: NestJS + Postgres
- Related features: documents
- Constraints: 实时性 <1s
- Non-goals: 不做评论点赞、不做嵌套回复
```

`Non-goals` 是防范围蔓延的依据，不要省。

---

## 计划阶段：`sean plan`

### 拆解原则

1. **按架构层级**：schema → service → controller → permissions → integration → frontend
2. **按依赖顺序**：前置任务先完成
3. **粒度均匀**：每个 task 预期 1-5 个测试
4. **独立可验证**：每个 task 完成后有明确通过/失败

### 产出的计划文档

模板：`templates/plan.md`

```markdown
# Plan: comments

## Task Summary
| # | Task | Depends On | Complexity | Parallel Safe |
|---|------|-----------|------------|---------------|
| 1 | schema  | — | low    | no |
| 2 | service | 1 | medium | yes |

## Artifact Inference
| Type | Path | Inferred From |
|------|------|---------------|
| database | `migrations/001_comments.sql` | Behavior "评论需持久化" |

## Task Details

### Task 1: schema
- **Creates**: `src/comment/comment.entity.ts`
- **Test**: `tests/comment/entity.spec.ts`
- **Acceptance**: 表结构与字段类型符合需求
- **Steps**: 写失败测试 → RED → 写 entity → GREEN
```

**plan 是索引，不是实现**：不要塞大段伪代码或实现片段，否则后续 `sean run` 读它的成本变高。

---

## 执行阶段：`sean run`

### TDD 严格顺序

```
RED → GREEN → REFACTOR
  ↑                │
  └────────────────┘
```

**绝对不允许**：
- 先写实现再写测试
- 修改测试以匹配实现
- 跳过 RED 直接写 GREEN

### 上下文加载（v5 变更）

旧版要求"读所有 files_modify"，这会把整个 feature 的代码重复读进上下文。v5 改为：

- 只读本 task 要改的函数/类所在区域（先 `grep -n` 定位，再 `offset+limit`）
- 同会话已读内容直接复用
- `conventions.md` 每会话读一次即缓存

### 修复循环（v5 变更）

```
测试失败
  → 只读首个 failure 的尾部 30 行（不是完整输出）
  → 分析根因（类型不匹配？逻辑错误？边界未处理？）
  → 定向读相关源码片段
  → 修改实现（绝不改测试）
  → 重跑测试
  → 最多 3 轮；根因未变则早停
  → 仍红 → 标记 failed，等 sean fix 或 sean undo
```

### 验证（v5 变更）

- 单 task：RED 一次 + GREEN 一次。**不再要求**"重新从零启动进程再跑一遍"。
- 整体：全部 task 完成后跑**一次** feature 级回归。

旧版每个 task 要跑 3 次（RED / GREEN / fresh re-run）+ 一次全量回归，2/3 是重复验证。

### 报告格式

每个 task 一份报告，**≤15 行**（`templates/test-report.md`）：

```markdown
# Test Report: Task 1 — schema

> **Status**: PASS

## Result
| Metric | Count |
|--------|-------|
| ✅ Passed | 3 |
| ❌ Failed | 0 |
| 🔧 Auto-fixed | 0 |

## RED Phase
`AttributeError: Comment has no attribute 'table'`

## GREEN Phase
`3 passed in 0.42s`

## Verdict
**PASS** — 表结构与字段类型符合需求
```

---

## 轻量模式：`--lite`

跳过 artifacts catalog、review 五维评估、findings、完整 handoff，只保留 TDD 闭环 + 单次回归 + state 落盘 + 一行 handoff。

适用：内部工具、脚手架、试验性 feature。
不适用：需要跨 Agent 接力交付的功能。

---

## 失败恢复

### 场景 1：单个测试失败

```bash
sean run comments
# ... Task 3 测试失败 ...
# 自动修复中... 1/3
# 自动修复中... 2/3
# 修复成功，继续
```

### 场景 2：需要手动介入

```bash
sean run comments --no-fix
# ... Task 3 测试失败 ...
# 已暂停。手动修复后运行：
#   sean task comments 3
```

### 场景 3：撤销重做

```bash
sean run comments
# ... 跑完但结果不如预期 ...
sean undo comments              # 回退 state（一条 patch 即可）
sean undo comments 1 --with-files  # 同时删除新建文件、git 还原修改
sean run comments --dry-run
sean run comments
```

### 场景 4：从失败处继续

```bash
sean run comments
# ... Task 5 连续失败 ...
sean undo comments 1   # 撤销 Task 5
sean plan comments     # 调整计划
sean run comments 5    # 从 Task 5 继续
```

### 场景 5：状态与报告脱钩

```bash
# 进程被杀、state 与测试报告不一致
sean sync comments     # 从 test-reports 重建 task 状态
```

---

## 成本控制

一个 feature 的完整流程涉及 8+ 次命令调用。以下做法能显著降低消耗：

1. **一个 feature 一次会话**，不要串多个 feature。
2. **优先 `sean task <name> N`**，而非 `sean run` 全量跑。
3. **并行只在长任务开**：每个子智能体都要重建上下文，短期 task 并行净亏。
4. **小需求用 `--lite`**。
5. **验收时看 payload，不看过程**：`sean_state.py get <feature>` 一行摘要足够判断进度。

---

## 多项目工作

```bash
# 项目 A
cd ~/repos/docmost
sean list

# 项目 B
cd ~/repos/stock-analysis
sean switch performance
sean status performance
```

每个项目的 `docs/.sean/` 独立，互不影响。
