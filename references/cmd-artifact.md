# `sean artifact <name> <action> [path] [--execute]`

执行或验证产物脚本，并把结果写回 catalog。

产物（迁移脚本、批处理命令）在 `sean run` 时只被**创建**，不被执行。执行是独立动作——因为执行可能改变外部状态，需要人确认。

---

## 安全闸门：默认 dry-run

**不传 `--execute` 就绝不碰真实环境。**

```bash
sean artifact auth run migrations/001_create_users.sql
  → DRY-RUN: 只显示将要执行什么

sean artifact auth run migrations/001_create_users.sql --execute
  → 真正执行，需要显式确认
```

理由：数据库脚本执行后可能不可逆（DROP TABLE、DELETE）。一个 `--execute` 漏传，代价远高于多敲一次参数。

---

## Actions

| Action | 行为 |
|---|---|
| `list` | 按类型分组列出该 feature 的所有产物，显示 status / executed / verified |
| `run <path> [--execute]` | dry-run（默认）或执行单个产物，结果写入 catalog 的 Execution Log |
| `verify <path> [--execute]` | 验证执行结果（检查预期副作用） |
| `mark <path> --executed --verified` | 手动标记状态（脚本已在别处执行过时） |

---

## Steps

1. 取状态：`python3 <sean-root>/scripts/sean_state.py get <name> --full`。不存在则报错。
2. 读 catalog `docs/artifacts/<date>-<name>.md`。缺失 → 提示先跑 `sean run`（或 `--lite` 下不存在，属正常）。
3. **`list`**：打印 catalog 表格（按类型分组）。
4. **`run <path>`**：
   - 在 state 的 `tasks[].artifacts[]` 中查找。未声明 → `产物 <path> 未在 plan 中声明`。
   - 从项目自身工具链确定执行命令（查 `AGENTS.md`；如 `alembic upgrade head`、`psql -f <path>`、`bash <path>`）。
   - **先 dry-run**：
     - 工具支持则真跑 dry-run（alembic `--sql`、SQL `EXPLAIN`、`bash -n`）并展示计划。
     - 否则只显示将要执行的完整命令。
     - **没有 `--execute` 就到此为止。**
   - **有 `--execute`**：
     - 用项目自身工具链执行，捕获 stdout/stderr + exit code。
     - 更新 catalog：`executed: true` + 追加 Execution Log。
     - 更新 state：`artifacts[].executed = true`。
     - exit code ≠ 0 → `status: failed`，STOP 并上报。
5. **`verify <path>`**：
   - **同样默认 dry-run**：说明将检查什么，不对线上库发探测。
   - `--execute` 时才检查预期副作用（表是否存在、行是否插入）。
   - 更新 `verified: true`。
6. **`mark`**：按参数改字段，不执行。这是"已在 sean 之外执行过"的逃生口。
7. `snapshot artifact <name>`。
8. 输出：产物路径 + action + dry-run 计划 或 执行结果。

---

## Safety Rules

- 任何修改外部状态（DB、项目外文件、网络）的动作，`--execute` **必填**。
- **绝不从上下文推断 `--execute`**。该 flag 必须显式出现。
- `mark` 是记录"sean 之外执行"的唯一途径。
- 项目没有该类型的既有工具（无 alembic、无 psql 配置）→ **不要执行**，上报缺口并询问用户。
- 已执行（`executed: true`）的产物，`sean undo` 时不静默删除；提示用户，并说明 DB 状态未被回滚。

---

## Usage

```bash
sean artifact auth list
sean artifact auth run migrations/001_create_users.sql          # dry-run
sean artifact auth run migrations/001_create_users.sql --execute
sean artifact auth verify migrations/001_create_users.sql --execute
sean artifact auth mark scripts/init_admin.sh --executed --verified
```
