---
name: sean
description: "AI-Native Team Development Workflow: standardizes how AI agents produce transferable knowledge — any AI can take over any other AI's work, even across context resets or model changes. Zero external dependencies."
version: 4.0.0
trigger: sean
---

# Sean — AI-Native Team Development Workflow

## 定位

规范 AI Agent 在团队中的开发行为。**核心目标：知识可传承**——任何 AI 接手其他 AI 的产出时，不需要问"这个功能怎么做的、文件在哪、下一步是什么"；甚至同一个 AI 在上下文丢失后，也能从文档中无缝恢复现场。

## Trigger

用户输入以 `sean ` 开头（大小写不敏感）时激活。

---

## Token 纪律（优先级高于任何流程完整性）

sean 的价值在"知识可传承"，但**传承的载体是可读的结论，不是冗长的过程**。以下 7 条为硬约束，与 TDD 铁律同级：

1. **按需加载**：只读当前命令对应的 reference，不预读其他命令的流程。
2. **不重复读**：本会话已读过的文件不再读；`conventions.md` 每会话读一次即缓存。
3. **定位读**：>200 行的文件先 `grep -n` 定位符号，再 `offset+limit` 读片段。**禁止**"读所有 files_modify"这类无条件全量读取。
4. **测试输出降噪**：测试命令固定带 `-q --tb=short`（或等价最小输出）；失败只取**首个** failure 的尾部 30 行，**禁止**回显整个测试会话或完整 traceback。
5. **状态走脚本**：`state.json` / `history` 一律通过 `scripts/sean_state.py` 读写。**禁止**手写或全量重写 state JSON。
6. **汇报 3 行**：完成即输出「做了什么 / 验证了什么 / 下一步」，不逐项打勾自证清单。
7. **能省则省**：`--lite` 下不生成 artifacts catalog / review / findings。

> 违反 Token 纪律不算"更严谨"，而是**流程执行错误**。

## 上下文读取三原则（写代码前）

替代旧版"Read all files in files_modify"：

- **定点**：只读本 task 要改的函数/类所在区域，不读整个文件。
- **建索引**：需跨文件理解时，先 `grep -n "<symbol>\|<import>"` 列行号，再定向读命中片段。
- **复用**：同会话内已读内容直接引用；跨 session 靠 `handoff.md` 恢复。

## TDD 铁律（不可绕过）

- 先写失败测试，**确认 RED**，再写最小实现使其 GREEN。
- **永不修改测试让它变绿**。测试是规格，修实现。
- RED 未实际观察到 → 该 task 不算完成。

---

## 命令路由（按需加载 command reference）

本文件 = 触发入口 + 公共铁律 + 路由。**执行某命令前，先读其 reference**（位于 skill 根目录的 `references/`）：

| 命令 | 作用 | 必读 |
|---|---|---|
| `init <project>` | 初始化（conventions + onboarding） | `cmd-init.md` |
| `start <name> [desc...]` | 创建需求文档 | `cmd-start.md` |
| `plan <name>` | 拆解 TDD 任务 + 推断产物 | `cmd-plan.md` |
| `run <name> [N] [--dry-run] [--no-fix] [--lite]` | 执行任务（TDD + 回归 + 交接） | `cmd-run.md` |
| `task <name> <N> [--lite]` | 执行单个任务 | `cmd-run.md` |
| `handoff <name> [--lite]` | 生成交接文档 | `cmd-handoff.md` |
| `review <name>` | diff 级自审 + 五维评估 | `cmd-review.md` |
| `bug <name> [desc] [--task N] [--already-fixed --files f]` | 记录/修复实测 bug（test-first） | `cmd-bug.md` |
| `artifact <name> <action> [path] [--execute]` | 执行/验证产物（默认 dry-run） | `cmd-artifact.md` |
| `dispatch / sync / fix / undo / retry / list / status / report / switch / clean / learn / findings / export` | 维护类命令 | `cmd-maintenance.md` |
| 需要 state 字段定义时 | — | `state-schema.md` |
| **多端需求**（可选，仅同需求多端实现时） | 契约 + 一致性校验 | `multi-target.md` |
| 报错 / 异常处理 | 错误速查 | `errors.md` |

**skill 根目录** = 本 `SKILL.md` 所在目录（`install.sh` 默认装到 `~/.hermes/skills/your-skills/sean/`）。不确定时先 `ls` 确认 `references/` 存在，再拼绝对路径读取。

**降级**：若环境无法读取同目录附属文件，直接走下方 **Quick Path**，不要凭记忆编造 reference 内容。

---

## Quick Path（零 reference 依赖）

小任务，或 reference 不可用时的降级路径：

1. **取状态**（一行摘要，不要导出全量）：
   ```bash
   python3 <sean-root>/scripts/sean_state.py get <feature>
   ```
2. **执行当前 task**：定位读代码 → 写失败测试 → 跑（RED）→ 写最小实现 → 跑（GREEN）。
3. **落状态**：
   ```bash
   python3 <sean-root>/scripts/sean_state.py task-status <feature> <n> done \
     --tests-total <N> --tests-passed <N> --report docs/test-reports/<date>-<feature>/task-<n>-<name>.md
   ```
4. **写 task 报告**（≤15 行，见 `templates/test-report.md`）。
5. **记 history**：
   ```bash
   python3 <sean-root>/scripts/sean_state.py snapshot run <feature> \
     --files-created a.py,b.py --files-modified c.py
   ```
6. **汇报 3 行**：做了什么 / 验证了什么 / 下一步。

Quick Path **不生成**：artifacts catalog、review 五维评估、findings、完整 handoff。

---

## 路径约定

文档在 `docs/`（`requirements/` `plans/` `test-reports/` `team/` `artifacts/`），状态在 `docs/.sean/`（`state.json` 摘要 + `features/<name>.json` 明细 + `history/`）。完整目录树见 `README.md`。

**产物目录是索引，不是容器。** DB 脚本 / 批处理 / 配置留在项目标准位置（`migrations/` `scripts/` `config/`），`docs/artifacts/` 只索引。产物由 AI 在 `sean plan` 阶段自行推断，分 database/batch/config 三类，各有 status/executed/verified 三维。规则见 `references/cmd-plan.md`。

---

## 状态存储契约

**唯一入口：`scripts/sean_state.py`，禁止手写 `docs/.sean/` 下的 JSON。**

高频命令（`get` / `task-status` / `feature-status` / `snapshot` / `undo`）见上方 Quick Path；完整命令与字段定义见 `references/state-schema.md`（仅需要时读）。

---

## 何时不要用 sean

sean 有固定开销（路由 + reference 加载 + 状态落盘）。以下情形**直接干活**：

- 改动 ≤2 个文件且 ≤1 个 task 的小修（改配置、改文案、单点 bug）。
- 纯问答、代码解释、一次性脚本。
- 探索性原型（还没形成需求）。

**判据**：如果"写需求 + 拆任务 + 落状态"的总工作量超过实现本身，就不该用 sean。

## 全局规则

- **Self-contained**：不调用任何外部 skill，逻辑都在本 skill 目录内。
- **Project-aware**：若项目有 `AGENTS.md`，读取并遵守其约束。
- **Knowledge-First**：交接文档和项目知识比任务状态更重要——AI 可以换，项目不能丢。
- **AI-Native**：定义 AI Agent 如何在团队中工作，不是定义人如何工作。
