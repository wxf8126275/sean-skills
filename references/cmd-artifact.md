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

| Action | 行为 | 底层实现 |
|---|---|---|
| `list` / `check` | 列出产物并校验 catalog ↔ state ↔ 磁盘三者一致、反向引用头、三维对齐 | `sean_artifact_check.py` |
| `run <path> [--execute]` | dry-run（默认）或执行单个产物 | `sean_artifact_run.py` |
| `verify <path> [--execute]` | 验证执行结果（检查预期副作用） | prompt（无通用实现） |
| `mark <path> --executed --verified` | 手动标记状态（产物已在 sean 之外执行过） | `sean_state.py set` |

> **机械判断交给脚本，解读与落盘交给 AI。** 尤其 `run`：dry-run 的强制性由脚本保证（不加 `--execute` 绝不可能执行），不依赖 AI 自觉。

---

## Steps

1. 取状态：`python3 <sean-root>/scripts/sean_state.py get <name> --full`。不存在则报错。

2. **`list` / `check`**（同一个脚本，`check` 信息更全）：
   ```bash
   python3 <sean-root>/scripts/sean_artifact_check.py . <name>          # 人读
   python3 <sean-root>/scripts/sean_artifact_check.py . <name> --json   # AI 消费
   ```
   退出码 0 = 一致（可能含 warning），1 = 有 error。把 error 逐条报告给用户，**不要**自行修改产物或 state 来"消除" error。

   > `--lite` 模式下不生成 catalog，此时 check 会报「catalog 缺失」，属预期，不是故障。

3. **`run <path>`**：
   ```bash
   # dry-run（默认，安全）
   python3 <sean-root>/scripts/sean_artifact_run.py --project . --feature <name> --artifact <path>

   # 真正执行（必须由用户显式要求）
   python3 <sean-root>/scripts/sean_artifact_run.py --project . --feature <name> --artifact <path> --execute
   ```
   脚本已负责：产物是否在 plan 中声明（退出码 3）、工具探测（alembic / psql / bash，退出码 4）、配置类不执行、dry-run 探测（`alembic --sql`、`bash -n`）。

   **你不需要再手工拼执行命令，也不要绕过脚本直接跑 shell。** 脚本输出 exit≠0 时如实上报，STOP。

4. **执行成功后回写两处**（脚本只打印提示，不做写入）：
   - catalog `docs/artifacts/<date>-<name>.md`：该产物 `Executed` 列改 ✅，`Execution Log` 追加一行（时间 + 命令 + 结果）。
   - state：把该产物的 `executed` 置 true（`sean_state.py set` 或重建 task 时带该字段）。

5. **`verify <path>`**：
   - **同样默认 dry-run**：说明将检查什么，不对线上库发探测。
   - `--execute` 时才检查预期副作用（表是否存在、行是否插入）。
   - 更新 `verified: true`（catalog + state 两处）。

6. **`mark`**：按参数改字段，不执行。这是"已在 sean 之外执行过"的逃生口。

7. `snapshot artifact <name>`。

8. 输出：产物路径 + action + dry-run 计划 或 执行结果。**不要**回显脚本的完整 dry-run 输出，只摘关键几行。

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
