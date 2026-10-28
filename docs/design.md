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

> **2026-10-28 修订**：该 ADR 已被部分推翻。见 ADR-0006——确定性产物（state / history 落盘）改由 Python 脚本执行，流程编排仍为 prompt。理由：让 LLM 手写 JSON 是纯粹的 token 浪费，且会产生半写损坏。

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

### ADR-0006: 为什么引入 state 引擎脚本（v5）

**状态**: 已接受
**日期**: 2026-10-28

**背景**: v4 由 AI 手写 `state.json` 全量 JSON，并每次操作写入 `before` + `after` 两份完整快照到 history。实测问题：

- 输出 token 贵：一次操作要写两份完整 state。
- 复杂度随项目老化恶化：state 大小随 feature 数 O(n) 增长，history 总量 O(n²)。20 个 feature 时单次快照约 200KB（≈50k token 输出）。
- 可靠性：进程被杀会留下半个 JSON（`sean sync` 的存在本身就是这个问题的证据）。

**决策**: 新增 `scripts/sean_state.py`，由脚本承担所有 state / history 落盘。

**理由**:
- 增量写：AI 只发 delta 指令，脚本负责合并。输出 token 降 80-95%。
- history 只存**被改动顶层键的旧值**（`restore.keys` + `absent`），单条 <1KB，且不随项目 feature 总数增长。
- 原子写（`tmp` + `os.replace`）根除半写损坏。
- 只用 Python 标准库，不破坏"零外部依赖"。

**后果**: 流程编排仍是 prompt，但状态管理成为代码。这提高了可靠性，也意味着 state 格式变更需要改脚本。

---

### ADR-0007: 为什么拆分 SKILL.md 为路由 + references（v5）

**状态**: 已接受
**日期**: 2026-10-28

**背景**: v4 单文件 1297 行 / 52KB / ≈13k token，每次触发全量注入。一个 feature 的完整流程涉及 8+ 次命令调用，这份说明书被重复计费 8+ 次，与业务复杂度无关。

**决策**: `SKILL.md` 只保留触发、公共铁律、命令路由表、Quick Path；命令流程拆分到 `references/cmd-*.md`，执行前按需读取。

**理由**:
- 常驻成本从 ≈13k 降到 ≈2.5k token（实测降幅 81%）。
- 高频规则（Token 纪律、读取三原则、TDD 铁律）保留常驻；低频细节（state schema、错误表、单命令流程）按需加载。
- 保留 Quick Path 作为降级路径：即使平台不支持读取附属文件，核心 TDD 闭环仍可执行。

**后果**: 引入了"按需加载是否真的生效"的平台依赖。通过 Quick Path 兜底，但完整功能需要平台支持读取同目录文件。

---

### ADR-0008: 为什么不用 SQLite 存 state（v5）

**状态**: 已接受
**日期**: 2026-10-28

**背景**: 评估用 SQLite 替代 JSON 存储 state / history 是否更省 token。

**决策**: 不采用。使用"JSON 摘要 + 明细分文件 + 脚本增量写"。

**理由**:
- 省 token 的来源是**增量写 + 精确读**，不是存储格式。脚本化 JSON 已拿到约 90% 的收益。
- SQLite 是二进制：人类无法在 PR 里 review，`git diff` 不可读，下一个 AI 必须先知道 schema 才能查询——这与"知识可传承"的第一原则冲突。
- AI 不可见会带来查询试错成本（`.schema` → 试 `SELECT` → 猜字段 → 再查），可能比读一份 JSON 更贵。
- `sqlite3` CLI 并非系统自带（常随 IDE/SDK 附带），跨机器不可靠。

**后果**: 当 history 记录量达到万级或出现并发写需求时，可重新评估。届时调用点已收敛在 `sean_state.py` 内，迁移成本较低。

---

## 扩展点

未来可以扩展：

1. **sean template** — 从模板创建完整功能骨架（如 `sean template comments --framework nestjs`）
2. **sean ci** — 生成 GitHub Actions 配置，自动跑 sean 流程
3. **sean sync** — 与 Linear/Jira/TAPD 同步状态
4. **sean review** — 生成 PR 描述 + 变更摘要

但这些都是 v3+ 的事。v3 先把核心跑通。
