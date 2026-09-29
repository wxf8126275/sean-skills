# sean 设计文档

> 最后更新：2026-09-23

## 设计动机

传统的 AI agent 开发依赖模型能力。Harness Engineering 的核心思想是：**不换模型，改工作流**。

`sean` 是一个实验：能否用纯 prompt（不写代码、不改框架源码、不依赖外部 skill）把一套工程化的开发流程注入 AI agent？

## 设计决策

### 为什么不用代码，用纯 prompt？

| 方案 | 优点 | 缺点 |
|------|------|------|
| 纯 prompt（现方案） | 零代码侵入、跨平台、可热更新 | 依赖 agent 理解力 |
| Hermes 源码扩展 | 原生体验、可精确控制 | 绑定 Hermes、更新会丢 |
| Python plugin | 可执行精确逻辑 | 需部署、有状态管理复杂 |

选择 prompt 方案的**核心理由**：sean 的价值在于流程设计本身，不在于代码执行。如果流程值得保留，未来可以迁移为代码；如果流程本身有缺陷，改 prompt 比改代码便宜得多。

### 为什么状态存在项目里而非 skill 目录？

- 多项目共存时状态隔离
- 项目迁移时状态随项目走
- skill 只定义"怎么做"，不存"做了什么"

### 为什么 undo 不存文件内容只存 hash？

- 文件内容可能很大，history 目录会膨胀
- git 已有完整历史，可直接 `git checkout` 恢复
- hash 用于检测外部修改（undo 时校验）

### 为什么不依赖 superpowers？

- 减少外部耦合，sean 自身可独立运行
- superpowers 的 plan/execute 流程与 sean 不完全匹配
- 自建逻辑更灵活（支持 undo、--no-fix、--dry-run 等自定义 flag）

---

## 状态机

```
                  sean start
                     │
                     ▼
                   DRAFT
                     │
                sean plan
                     │
                     ▼
                  PLANNED
                     │
            sean run / sean task
                     │
                     ▼
               IN_PROGRESS  ◄──────┐
                     │             │
          ┌──────────┼──────────┐  │
          │          │          │  │
   所有 task    有 task    连续 2  │ sean undo
   完成        失败停      task  │
          │          │       失败 │
          ▼          ▼          │  │
        DONE     BLOCKED ◄──────┘  │
                     │             │
                sean fix ──────────┘
                sean undo
                sean task N
                     │
                     ▼
               IN_PROGRESS / DONE
```

---

## 错误恢复策略

| 故障类型 | sean 行为 |
|---------|-----------|
| 单个测试失败 | 自动修复 3 次 → 仍红则暂停 |
| 单个 task 失败 | 暂停，等 `fix` 或 `undo` |
| 连续 2 个 task 失败 | 中止，避免雪崩 |
| 状态文件损坏 | 从 test-reports/ 重建 |
| 测试运行超时 | 提示重试或跳过 |
| 文件被外部修改 | undo 时警告确认 |

---

## 与 AGENTS.md 的关系

sean 依赖项目中的 `AGENTS.md` 获取：
- 技术栈约定
- 编码规范
- 构建命令
- 红线规则

`AGENTS.md` 是项目的事实源，sean 只负责流程编排。

如果项目没有 `AGENTS.md`，sean 会基于项目文件结构推断，但精度会降低。

---

## 架构决策记录 (ADR)

### ADR-0001: 为什么用纯 prompt 而非代码？

**状态**: 已接受
**日期**: 2026-09-23

**背景**: Sean 需要选择实现方式。

**决策**: 使用纯 prompt（SKILL.md），不写代码。

**理由**:
- 零代码侵入，跨平台
- 可热更新，改 prompt 比改代码便宜
- 如果流程值得保留，未来可迁移为代码

**后果**: 依赖 agent 理解力，但换取了灵活性和零部署成本。

---

### ADR-0002: 为什么状态存在项目里而非 skill 目录？

**状态**: 已接受
**日期**: 2026-09-23

**背景**: 多项目共存时需要状态隔离。

**决策**: 状态存在 `<project>/docs/.sean/state.json`。

**理由**:
- 项目迁移时状态随项目走
- skill 只定义"怎么做"，不存"做了什么"
- 多项目互不干扰

**后果**: 每个项目需要独立 init，但换来了隔离性。

---

### ADR-0003: 为什么引入五维评估模型？

**状态**: 已接受
**日期**: 2026-09-29

**背景**: 原 `sean review` 只检查代码规范，不评估工作流本身。

**决策**: 引入 Agent Work Loop 五维模型（Task Understanding, Controlled Execution, Change Validation, Reliable Delivery, Learning Capture）。

**理由**:
- 代码质量 ≠ 工作流质量
- 五维模型提供系统化的评估框架
- 证据状态机制消除"配置了但没跑"的模糊

**后果**: Review 从代码审查升级到工作流审查，能发现系统性问题。

---

### ADR-0004: 为什么引入证据状态机制？

**状态**: 已接受
**日期**: 2026-09-29

**背景**: 原 state.json 只有 `pending|in_progress|done|failed`，无法区分"配置了但没跑"和"跑了且通过"。

**决策**: 引入六态证据模型（Present, Wired, Exercised, Outcome-supported, Missing, Unobserved）。

**理由**:
- 区分"机制存在"和"机制被使用"
- 为评分提供客观依据
- 避免将"未观察"误判为"缺失"

**后果**: 状态更精确，但需要更多上下文来判定。

---

### ADR-0005: 为什么引入学习沉淀闭环？

**状态**: 已接受
**日期**: 2026-09-29

**背景**: 原 handoff 是静态文档，不会从多次运行中学习。

**决策**: 新增 `sean learn` 命令，从历史 test-reports 提取可复用模式。

**理由**:
- 重复出现的失败模式可以预防
- 重复出现的结构可以抽象为模板
- 经验沉淀是知识传承的核心

**后果**: 需要维护 lessons.md，但持续降低团队学习成本。

---

## 扩展点

未来可以扩展：

1. **sean template** — 从模板创建完整功能骨架（如 `sean template comments --framework nestjs`）
2. **sean ci** — 生成 GitHub Actions 配置，自动跑 sean 流程
3. **sean sync** — 与 Linear/Jira/TAPD 同步状态
4. **sean review** — 生成 PR 描述 + 变更摘要

但这些都是 v3+ 的事。v3 先把核心跑通。
