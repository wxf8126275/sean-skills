# sean-skills

> AI-Native Team Development Workflow — standardizes how AI agents produce transferable knowledge. Any AI can take over any other AI's work, even across context resets or model changes.

## 什么是 sean？

`sean` 是一套以前缀 `sean` 触发的 AI agent 开发工作流。它不约束人，而是约束 **AI Agent 在团队中的交付行为**——确保每个 Agent 产出可拼接、可审查、可传承。

核心目标：**知识可传承**——换模型、换 Agent、清空上下文，都能从文档无缝恢复现场。

## 特性

- **零外部依赖**：不依赖 superpowers、Claude Code 或其他框架
- **知识驱动**：`handoff.md` + `sync` + `review` 形成知识传承闭环
- **TDD 硬约束**：每个编码任务必须 RED→GREEN，禁止假测试
- **自动修复**：测试失败自动分析根因、修复、重测（最多 3 轮）
- **可撤销**：每次操作有快照，`sean undo` 即可回退
- **自审**：`sean review` 检查代码质量是否符合团队规范
- **状态恢复**：进程被杀后 `sean sync` 从测试报告重建状态
- **多项目独立**：状态存在项目的 `docs/.sean/`，切换自如

## 适用场景

- 团队全面使用 AI 写代码
- 多人多 Agent 协作开发同一项目
- 需要换模型但不想丢失开发进度
- 新人/新 Agent 接手已有项目

## 安装

```bash
# 克隆
git clone <repo-url> ~/repos/sean-skills

# 安装到 Hermes
bash ~/repos/sean-skills/install.sh

# 或手动链接
ln -s ~/repos/sean-skills/SKILL.md ~/.hermes/skills/your-skills/sean/SKILL.md
```

## 快速开始

```bash
# 1. 初始化项目（一次性）
sean init my-project

# 2. 创建需求
sean start comments "文档评论功能"

# 3. 生成 TDD 计划
sean plan comments

# 4. 预览（不执行）
sean run comments --dry-run

# 5. 执行（自动修复 + 回归 + 生成交接文档）
sean run comments

# 6. 查看交接文档
sean handoff comments

# 7. 代码质量自审
sean review comments

# 8. 测试汇总
sean report comments --summary
```

## 换 Agent / 换模型时的流程

```bash
# 上一个 Agent 完成后，生成 handoff
sean handoff comments

# 新 Agent 接手，先看 handoff 恢复上下文
sean sync comments        # 从测试报告恢复状态（如果 state 丢失）
sean status comments      # 查看当前状态
sean run comments         # 继续执行
```

## 命令速查

| 命令 | 作用 |
|------|------|
| `sean init <project>` | 初始化项目（生成 conventions.md + onboarding.md） |
| `sean start <name> [desc...]` | 创建需求文档 |
| `sean plan <name>` | 生成 TDD 实现计划 |
| `sean run <name> [N] [--dry-run] [--no-fix]` | 执行计划（含回归验证 + 交接文档） |
| `sean task <name> <N>` | 执行单个 task |
| `sean handoff <name>` | 生成交接文档（另一 AI 接手用） |
| `sean sync <name>` | 从测试报告恢复状态（上下文丢失时用） |
| `sean review <name>` | 代码质量自审 |
| `sean fix [name]` | 修复最近失败的任务 |
| `sean undo [name] [steps]` | 撤销操作 |
| `sean retry <name>` | 重试最近失败的任务 |
| `sean list` | 列出所有功能状态 |
| `sean status <name>` | 查看功能详情 |
| `sean report [name] [--summary]` | 测试汇总 |
| `sean switch <name>` | 切换激活功能 |
| `sean clean [--keep-reports]` | 清理状态 |

## 目录结构（项目中）

```
docs/
├── requirements/          # 需求文档
├── plans/                 # 实现计划
├── test-reports/          # 测试报告 + 交接文档 + 自审报告
│   └── <date>-<feature>/
│       ├── task-N-<name>.md
│       ├── summary.md
│       ├── handoff.md
│       └── review.md
├── team/
│   ├── conventions.md     # 团队开发规范
│   └── onboarding.md      # 项目知识手册（AI 可读）
└── .sean/                 # sean 私有状态
    ├── state.json
    ├── active
    └── history/
```

## 核心流程

```
需求文档 → TDD 任务拆解 → 逐个执行（RED→GREEN）
    ↓
端到端回归 → 交接文档 → 提交信息建议
    ↓
换 Agent / 换模型 → handoff.md + sync → 无缝恢复
```

## 与 Hermes 的关系

sean 是 Hermes 的 skill，但**零代码侵入**——不改 Hermes 源码，纯 prompt 驱动。
任何支持 skill 加载的 agent 平台都可以适配。

## License

MIT
