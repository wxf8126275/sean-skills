# sean-skills

> A self-contained, zero-dependency harness development workflow for AI agents.

## 什么是 sean？

`sean` 是一套以前缀 `sean` 触发的 AI agent 开发工作流，遵循 **Harness Engineering** 思想——不改模型，改工作流。

它不依赖任何外部 skill（如 superpowers），所有逻辑内化在自身。你说 `sean start`、`sean run`，agent 就会按 TDD 流程推进。

## 特性

- **零外部依赖**：不依赖 superpowers、Claude Code 或其他框架
- **TDD 驱动**：红 → 绿 → 重构，严格保证先写失败测试
- **自动修复**：测试失败自动分析根因、修复、重测（最多 3 轮）
- **可撤销**：每次操作有快照，`sean undo` 即可回退
- **预览模式**：`--dry-run` 只看不改
- **手动模式**：`--no-fix` 失败即停，自己改
- **多项目独立**：状态存在项目的 `docs/.sean/`，切换自如

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
# 1. 创建需求
sean start comments

# 2. 生成 TDD 计划
sean plan comments

# 3. 预览（不执行）
sean run comments --dry-run

# 4. 执行（自动修复）
sean run comments

# 5. 查看测试汇总
sean report comments --summary
```

## 命令速查

| 命令 | 作用 |
|------|------|
| `sean start <name> [desc...]` | 创建需求文档 |
| `sean plan <name>` | 生成 TDD 实现计划 |
| `sean run <name> [N] [--dry-run] [--no-fix]` | 执行全部计划 |
| `sean task <name> <N> [--dry-run] [--no-fix]` | 执行单个 task |
| `sean fix [name]` | 修复最近失败的测试 |
| `sean undo [name] [steps]` | 撤销最近 N 步操作 |
| `sean retry <name>` | 从失败处重试 |
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
├── test-reports/          # 测试报告
└── .sean/                 # sean 私有状态
    ├── state.json
    ├── active
    └── history/
```

## 与 Hermes 的关系

sean 是 Hermes 的 skill，但**零代码侵入**——不改 Hermes 源码，纯 prompt 驱动。
任何支持 skill 加载的 agent 平台（未来）都可以适配。

## License

MIT
