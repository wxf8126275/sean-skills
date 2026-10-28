# sean-skills

> AI-Native Team Development Workflow — standardizes how AI agents produce transferable knowledge. Any AI can take over any other AI's work, even across context resets or model changes.

## 什么是 sean？

`sean` 是一套以前缀 `sean` 触发的 AI agent 开发工作流。它不约束人，而是约束 **AI Agent 在团队中的交付行为**——确保每个 Agent 产出可拼接、可审查、可传承。

核心目标：**知识可传承**——换模型、换 Agent、清空上下文，都能从文档无缝恢复现场。

## 设计取舍：可传承 ≠ 都要写进上下文

v4 把整套流程塞进单个 52KB 的 `SKILL.md`，导致每次调用都重复吞下约 13k token 的说明书；`state.json` 每次全量重写，`history` 存两份完整快照。v5 重新平衡了"可传承"与"成本"：

| 维度 | v4 | v5 |
|---|---|---|
| 技能常驻 | 单文件 1297 行 / 52KB / ≈13k tok | 路由主文件 ≈200 行 / ≈2k tok |
| 命令细节 | 全部常驻 | `references/` 按需加载 |
| state 存储 | 单文件全量，随 feature 线性膨胀 | `state.json` 摘要 + `features/<name>.json` 明细 |
| history | `before` + `after` 两份完整快照 | 仅存被改动字段的旧值，单条 <1KB |
| 状态写入 | AI 手写整个 JSON | `sean_state.py` 增量写入 |
| 上下文读取 | "读所有 files_modify" | grep 定位 + 定向读片段 |
| 失败输出 | 读完整错误输出 | 首个 failure 尾部 30 行 |
| review | 重读全部源码 | 基于 `git diff` + 机械检查 |
| 文档 | 固定全量产出 | `--lite` 可按需裁剪 |

重点：**砍掉的是重复读取与机器可生成的内容，不是交接信息本身。** `handoff.md`、`bugs.md`、`review.md` 一个都没少。

## 特性

- **零外部依赖**：不依赖 superpowers、Claude Code 或其他框架；state 引擎只用 Python 标准库
- **渐进披露**：主文件只留路由与铁律，命令流程按需加载，支持降级（Quick Path）
- **知识驱动**：`handoff.md` + `sync` + `review` 形成知识传承闭环
- **TDD 硬约束**：每个编码任务必须 RED→GREEN，禁止假测试
- **自动修复**：测试失败自动分析根因、修复、重测（最多 3 轮，同因早停）
- **可撤销**：state 走最小逆向补丁，文件走 git
- **五维评估**：基于已有证据评分，缺证据记 `unobserved`，不为凑分额外扫描
- **产物索引**：`docs/artifacts/` 索引数据库脚本/批处理命令，产物文件留项目标准位置；`sean artifact check` 校验 catalog ↔ state ↔ 磁盘一致，`run` 由脚本强制 dry-run
- **状态恢复**：进程被杀后 `sean sync` 从测试报告重建
- **旧版兼容**：v4 全量 `state.json` 首次读取时自动迁移，无需手工处理

## 安装

```bash
git clone <repo-url> ~/repos/sean-skills
bash ~/repos/sean-skills/install.sh

# 自定义安装位置
bash ~/repos/sean-skills/install.sh /path/to/skills/sean

# 建议加别名（省去拼脚本路径）
alias sean-state='python3 ~/.hermes/skills/your-skills/sean/scripts/sean_state.py'
```

安装内容：`SKILL.md`（唯一常驻）、`references/`（按需加载）、`templates/`、`scripts/`。

## 快速开始

```bash
# 1. 初始化项目（一次性）
sean init my-project

# 2. 创建需求
sean start comments "文档评论功能"

# 3. 生成 TDD 计划
sean plan comments

# 4. 预览
sean run comments --dry-run

# 5. 执行
sean run comments              # 完整模式：TDD + 回归 + handoff + artifacts
sean run comments --lite       # 轻量模式：TDD + 回归 + 一行 handoff

# 6. 交接与自审
sean handoff comments
sean review comments
```

## 多端一致（可选，默认关闭）

同一需求由 Android / iOS / HarmonyOS 等多端分别实现时，常规做法会产生「三份需求、三份计划、三套测试」的结构性漂移。sean 提供**可选**的多端对齐能力，**单端项目不会接触任何相关内容**。

```bash
# 1. 探测（脚本完成，不扫全仓）
python3 <sean-root>/scripts/sean_state.py detect-targets
#   → multi_target: detected [android, ios, harmony]，询问一次是否启用
#   → 用户选"否"后写 conventions.md: multi_target: off，永不再问

# 2. 启用
sean start login-v2 "登录重构" --targets android,ios,harmony

# 3. 先契约，后计划
#    docs/contracts/<date>-login-v2/contract.md   （模板 templates/contract.md）
#    docs/contracts/<date>-login-v2/cases/*.json  （共享 golden cases）

# 4. 各端只跑自己的 task
sean task login-v2 4        # iOS 工程师

# 5. 一致性闸门
python3 <sean-root>/scripts/sean_parity.py --feature login-v2
#   Verdict: PASS → 才允许 feature 置 DONE
```

设计要点：

- **目标不是代码一致，而是行为等价**。平台差异走 `Platform Delta` 白名单，其余差异视为缺陷。
- **共享 golden cases** 是消除逻辑漂移的关键：三端跑同一批 JSON 用例，而不是各写各的断言。
- **不要求三端都装 sean**：`results/<target>.json` 支持外部注入（手工填或 CI 产出）。
- **零默认成本**：不启用时 state 无 `targets` 键、无契约文件、不加载 `references/multi-target.md`。
- 事后再启用也可行：`sean targets add <name> android,ios,harmony` 会把已有 task 归入主端，历史与 undo 全部保留。

完整流程与检查清单见 `references/multi-target.md`。

## 成本控制：什么时候不要用 sean

sean 有固定开销（路由加载 + 状态落盘）。以下情形**直接干活**：

- 改动 ≤2 个文件且 ≤1 个 task 的小修（改配置、改文案、单点 bug）
- 纯问答、代码解释、一次性脚本
- 探索性原型（还没形成需求）

**判据**：如果"写需求 + 拆任务 + 落状态"的工作量超过实现本身，就不该用 sean。

### 使用姿势建议

1. **一个 feature 一次会话**，不要在同一会话里串 `start → plan → run → review` 多个 feature。
2. **优先 `sean task <name> N`** 而非 `sean run` 全量跑——按需触发，不重复加载上下文。
3. **并行只在长任务开**：每个子智能体都要重建上下文，短任务并行净亏。
4. **小需求用 `--lite`**：省掉 artifacts catalog / review findings / 完整 handoff。
5. **汇报带数据**：优化前先记录 token 用量与调用轮次，否则没有基准。

## 命令速查

| 命令 | 作用 |
|------|------|
| `sean init <project>` | 初始化项目（conventions.md + onboarding.md） |
| `sean start <name> [desc...]` | 创建需求文档 |
| `sean plan <name>` | 生成 TDD 实现计划（含产物推断） |
| `sean run <name> [N] [--dry-run] [--no-fix] [--lite]` | 执行计划 |
| `sean task <name> <N> [--lite]` | 执行单个 task |
| `sean dispatch <plan> [--format json\|yaml\|text]` | 按依赖 wave 分组，输出子智能体任务描述 |
| `sean handoff <name> [--lite]` | 生成交接文档 |
| `sean sync <name>` | 从测试报告重建状态 |
| `sean review <name>` | diff 级自审 + 五维评估 + findings |
| `sean learn <name>` | 从历史报告提取可复用模式 |
| `sean findings [name]` | 查看/管理 findings |
| `sean fix [name]` | 修复最近失败的任务 |
| `sean bug <name> [desc] [--task N] [--already-fixed --files f1,f2]` | 记录/修复 run 后发现的 bug |
| `sean artifact <name> <action> [path] [--execute]` | 执行/验证产物（默认 dry-run） |
| `sean undo [name] [steps] [--with-files]` | 撤销（state 走补丁，文件走 git） |
| `sean retry <name>` | 重试最近失败的任务 |
| `sean list` / `status` / `report` / `switch` / `export` / `clean` | 状态维护 |

## 目录结构（项目中）

```
docs/
├── requirements/          # 需求文档
├── plans/                 # 实现计划
├── artifacts/             # 产物索引（非容器）
├── test-reports/<date>-<feature>/
│   ├── task-N-<name>.md   # 每 task ≤15 行
│   ├── bugs.md
│   ├── summary.md
│   ├── handoff.md
│   └── review.md
├── team/
│   ├── conventions.md
│   ├── onboarding.md      # 建议 ≤100 行，它会被反复读取
│   └── lessons.md
└── .sean/                 # sean 私有状态
    ├── state.json         # 摘要（<2KB）
    ├── features/<name>.json
    ├── active
    └── history/           # index.jsonl + 最小逆向补丁
```

## 核心流程

```
需求文档 → TDD 任务拆解 → 逐个执行（RED→GREEN）
    ↓
端到端回归（一次）→ 交接文档 → 提交信息建议
    ↓
换 Agent / 换模型 → handoff.md + sync → 无缝恢复
```

## 与 Hermes 的关系

sean 是 Hermes 的 skill，但**零代码侵入**——不改 Hermes 源码，纯 prompt 驱动。任何支持 skill 加载（且能读取同目录附属文件）的 agent 平台都可以适配；不支持时退化为 Quick Path。

## License

MIT
