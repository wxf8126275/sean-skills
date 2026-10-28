# 维护类命令

`dispatch` / `sync` / `fix` / `undo` / `retry` / `list` / `status` / `report` / `switch` / `clean` / `learn` / `findings` / `export`

> 通用前提：`S=<sean-root>/scripts/sean_state.py`。所有状态读写都通过脚本，禁止手写 JSON。

---

## `sean dispatch <plan_path> [--start N] [--format json|yaml|text]`

解析 plan，按依赖分组 wave，生成子智能体任务描述。用于并行执行前的规划。

1. 解析 plan → Task 对象（id/name/depends_on/parallel_safe/files/test_file）。
2. 分组 wave：Wave 1 = 无未满足依赖；Wave N = 依赖全在更早 wave。
3. wave 内区分 `parallel_safe` 与串行。
4. 为每个 parallel_safe task 生成 Task Context Package（格式见 `cmd-run.md` 的精简版）。
5. 按 `--format` 输出（默认 text）。

```bash
python3 <sean-root>/scripts/sean_dispatch.py docs/plans/2026-09-29-myfeature.md
python3 <sean-root>/scripts/sean_dispatch.py docs/plans/2026-09-29-myfeature.md --format json
python3 <sean-root>/scripts/sean_dispatch.py docs/plans/2026-09-29-myfeature.md --start 3
```

---

## `sean sync <name>`

**状态恢复**：从测试报告重建 state。用于 state.json 与真实测试结果脱钩时（例如进程被杀）。

1. 扫描 `docs/test-reports/*-<name>/task-*.md`。
2. 扫描 `docs/artifacts/*-<name>.md` catalog。
3. 从报告内容推导 task 状态（PASS → done；FAIL → failed；无报告 → pending）。
4. 从 catalog 推导产物状态（created / executed / verified / declared）。
5. 重建 state，输出 diff，覆盖前询问。

一条命令完成：

```bash
python3 $S sync <name>
```

> 该命令本身**不读源码**，只读报告文本里的一行 `Status`。

---

## `sean fix [name]`

1. 未给 `[name]` → 读 `active`。
2. 取状态，找最近一个 `status: failed` 的 task。
3. 读对应测试报告（只读 Verdict 与错误摘要）。
4. 跑测试复现（`-q --tb=short`，只读首个 failure 尾部 30 行）。
5. 定根因 → 改代码（不改测试）→ 重跑。
6. GREEN → `task-status <name> <n> done --fixes <n>`。
7. 仍 RED → 输出失败详情，建议 `sean undo` 或人工介入。

---

## `sean undo [name] [steps]`

撤销操作，state 与文件分离处理。

```bash
python3 $S undo [steps]            # 只回退 state
python3 $S undo [steps] --with-files   # 同时删除新建文件、git 还原修改文件
```

内部行为：

- 最近的 `undone: false` history 条目逐个反向应用（只回退被改动的顶层键）。
- `files_created` → 列出 `rm` 指令；`files_modified` → 列出 `git checkout --` 指令。
- 默认只打印文件指令，加 `--with-files` 才真正动文件（安全默认）。
- **产物安全检查**：`executed: true` 的产物不静默删除，提示用户并说明 DB 状态未回滚。

`steps > 1` 时重复。

---

## `sean retry <name>`

1. 找最近 `status: failed` 的 task。
2. 执行 `sean task <name> <n> --no-fix`。

---

## `sean list`

```bash
python3 $S list
```

输出每个 feature 一行摘要（状态 / 进度 / 测试数 / 未决 bug 与 finding），按更新时间倒序，`*` 标记 active。

---

## `sean status <name>`

```bash
python3 $S get <name> --full
```

输出：需求/计划路径、状态、进度、逐 task 状态（`+` done / `x` failed / `~` in_progress / `.` pending）、未决 bug。
`BLOCKED` 时附带 `blocked_reason`；`INTEGRATION_FAIL` 时列出冲突 task。

---

## `sean report [name] [--summary]`

1. 未给 `[name]` → 读 `active`。
2. 扫描测试报告目录，聚合计 total / passed / failed / fixed。
3. 打印表格。
4. `--summary` 时写 `summary.md`（≤20 行）。

> 汇总优先复用 `sean_state.py` 的 task 计数，避免逐份报告解析。

---

## `sean switch <name>`

1. 校验 feature 存在（脚本内完成，不存在会列出可选值）。
2. 切换 active 并同步 `docs/.sean/active`：
   ```bash
   python3 $S switch <name>
   ```
3. 输出切换结果（含该 feature 的一行摘要）。

---

## `sean clean [--keep-reports]`

1. 二次确认。
2. 删除 `docs/.sean/`。
3. `--keep-reports` 时保留 `docs/test-reports/`。
4. 输出「已清理」。

---

## `sean learn <name>`

从历史报告提取可复用模式，沉淀到 `docs/team/lessons.md`。

1. 扫描本项目所有 `docs/test-reports/*/` 目录（**只读 `summary.md`、`bugs.md`、`review.md` 的结论段**，不要通读 task 报告）。
2. 扫描所有 `docs/artifacts/*.md` catalog。
3. 提取：
   - **重复失败模式**：同一根因出现在 2+ feature
   - **重复结构模式**：相似的 task 拆解可模板化
   - **重复决策**：独立做出的相同架构选择
   - **产物模式**：哪类 feature 反复需要哪类产物，哪类经常 executed-but-not-verified
4. 写 `docs/team/lessons.md`（四张表 + 建议）。
5. 如模式指向规范更新，**只提议不自动改** `conventions.md`。
6. 输出：文件路径 + 模式数量。

---

## `sean findings [name]`

1. 未给 `[name]` → 读 `active`。
2. 从 state 的 `findings[]` 读取。
3. 输出表格：`ID | Dimension | Severity | Status | Evidence`。
4. `--fix <id>`：确认修复后置 `verified`。
5. `--detail <id>`：显示完整 finding（含 repair 与 verifier）。

---

## `sean export <name> --format <format>`

导出 sean 工作流到其他 agent 格式。

| Format | 目标 | 输出 |
|---|---|---|
| `claude-code` | Claude Code | `.claude/commands/sean.md` |
| `cursor` | Cursor | `.cursorrules` |
| `copilot` | GitHub Copilot | `.github/copilot-instructions.md` |
| `codex` | Codex | `.codex/config.toml` |

1. 读本 skill 的 `SKILL.md` **主文件**（路由层）。
2. 按目标格式转换（不要把 `references/` 全部内联——导出产物应保留按需加载结构，或明确标注细节需查阅源文件）。
3. 写入目标位置。
4. 输出：导出路径 + 格式。

> 交接状态用 `sean_state.py export [feature]`，它与本命令不同：前者导出**数据**，本命令导出**工作流定义**。
