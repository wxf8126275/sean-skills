# 多端一致（可选能力）

> **只在需要时读本文件。** 单端项目不需要它，默认流程完全不涉及。
> 多端模式是现有 `start / plan / run` 的**字段扩展**，不是第二套流程。

适用：同一个需求要由 Android / iOS / HarmonyOS（或任意多个端）分别实现，且要求**行为等价**。

**目标不是代码一致，而是「行为等价 + 差异有据可查」。**

---

## 何时启用

- 需求涉及跨端共享的业务逻辑（状态机、校验、错误码、格式化、权限判定）
- 需求涉及同一后端 API 的多端接入
- 历史上同一需求在三端出现过不一致

**不要启用**：纯平台特有功能（如某端的系统集成）、单端独有的 UI 改版。

---

## 启用方式（二选一）

### 显式

```bash
sean start login-v2 "登录重构" --targets android,ios,harmony
```

### 探测后询问（推荐）

```bash
python3 <sean-root>/scripts/sean_state.py detect-targets
```

输出 `multi_target: detected [android, ios, harmony]` 时，问用户一次：

```
检测到多端项目结构。本需求需要多端对齐吗？
  否 — 各端独立实现（默认）
  是 — 启用契约 + 一致性校验
  ⚠️ 选"否"后写入 conventions.md，后续不再询问
```

用户选"否" → 在 `docs/team/conventions.md` 追加一行：

```markdown
multi_target: off
```

此后 `detect-targets` 直接返回已关闭，**永不再问**。

> 探测只做一次目录匹配，不递归扫描。`detect-targets` 由脚本完成，AI 不自己 `ls` 全仓。

---

## 三个载体（都不影响单端）

| 载体 | 位置 | 单端时 |
|---|---|---|
| 契约 | `docs/contracts/<date>-<feature>/` | 文件不存在 |
| state 键 | `features/<name>.json` 的 `targets` / `primary_target` | 键不存在 |
| plan 可选行 | `### Task N:` 内 `**Target**:` / `**Contract**:` | 不写 |

> ⚠️ **不要把任务矩阵做成 plan 里的 markdown 表格**：`sean_dispatch.py` 的正则 `\|\s*(\d+)\s*\|...` 会全文匹配任意 5 列表格行，首列为纯数字时会被误识别成 task。矩阵放契约文件里。

---

## 流程

### 1. `sean start` → 声明 targets

```bash
python3 <sean-root>/scripts/sean_state.py create <name> --requirement <path> --set-active
python3 <sean-root>/scripts/sean_state.py targets add <name> android,ios,harmony --primary android
python3 <sean-root>/scripts/sean_state.py snapshot start <name>
```

`--primary` 是"未标 target 的 task 归属端"。已存在的 task 会被自动打上 primary 标记，历史数据不变。

### 2. 先写契约，再 `sean plan`

契约模板：`templates/contract.md`。产出到 `docs/contracts/<date>-<feature>/contract.md`。

必须覆盖六类内容（缺一类就是一类将来的差异）：

1. 业务状态机（状态、事件、转换）
2. API 契约（路径、入参出参、错误码）
3. UI 行为规则（流转、必填校验、空态/错误态/加载态）
4. 文案与多语言 key
5. **边界条件表**（空值、超长、并发、断网、权限拒绝、时区）
6. 平台差异白名单（`## Platform Delta`）

条款 ID 格式必须为 `C-NN`，差异 ID 为 `D-NN`。`status: locked` 表示锁定，改动需 owner + 各端确认。

### 3. 共享 golden cases

把可移植的业务逻辑做成**数据驱动用例**，各端读**同一批 JSON**：

```
docs/contracts/<date>-<feature>/cases/state-machine.json
[{"id": "C-01-01", "in": {"state": "idle", "event": "submit"}, "out": "loading"}]
```

- 用例 id 必须带条款前缀（`C-01-01`），parity 靠前缀归属
- 各端测试从该目录加载用例，**不要各写各的断言**
- 逻辑漂移在这一层被物理消除——不是靠人对齐

适用优先级：状态机 > 错误码映射 > 输入校验 > 格式化 > 权限判定。
不适用：UI 布局、动画、平台控件 → 归 `Platform Delta`。

### 4. `sean plan` → 拆解时标注 target

每个 task 在 plan 的详情块追加两行（`parse_plan` 不识别也报错，安全）：

```markdown
### Task 4: ios-login-state
- **Target**: ios
- **Contract**: C-01
- **Creates**: `ios/Auth/LoginState.swift`
- **Test**: `iosTests/LoginStateTests.swift`
- **Acceptance**: C-01-01..03 全部通过
```

登记到 state 时 task 也带 `target`：

```bash
python3 $S add-task <name> --json '{"id":4,"name":"ios-login-state","target":"ios",
  "contract_ref":"C-01","status":"pending","test_file":"iosTests/LoginStateTests.swift"}'
```

### 5. `sean run` / `sean task` → 各端只跑自己

各端工程师只认领自己 `target` 的 task 编号：

```bash
sean task login-v2 4     # iOS 工程师
sean task login-v2 1     # Android 工程师
```

现有 `sean task` 机制直接复用，不需要改动。各端在自己的仓库/目录里跑，共享 `docs/`。

### 6. 落结果

每端跑完 golden case 后写一份 `results/<target>.json`（5 行）：

```bash
H=$(python3 <sean-root>/scripts/sean_parity.py --cases-hash docs/contracts/<date>-<feature>/cases)
cat > docs/contracts/<date>-<feature>/results/android.json <<EOF
{"target": "android", "contract_id": "<id>", "cases_hash": "$H",
 "cases": {"C-01-01": "pass", "C-01-02": "pass", "C-02-01": "pass"}}
EOF
```

**外部注入**：不用 sean 的端可以手工填这份 JSON（或由 CI 产出）。格式相同即可，**不要求三端都装 sean**。

`cases_hash` 用于检测某端是否用了过期的用例文件。

### 7. 一致性校验

```bash
python3 <sean-root>/scripts/sean_parity.py --feature <name>
```

输出：

```
# parity: login-v2
  targets: android, ios, harmony   cases_hash: 28f7440025b00566

  C-01  state-machine  android=pass  ios=fail  harmony=no-result
  C-02  api            android=pass  ios=pass  harmony=no-result
  C-03  validation     android=pass  ios=missing  harmony=no-result

  D-01  delta:ios  已批准(arch) — 使用系统 Face ID

  [high] C-01/ios: 用例未通过
  [high] C-02/harmony: 缺少 results 文件

Verdict: FAIL  (2 high, 0 medium)
```

判定规则：

| 情况 | 严重度 |
|---|---|
| 条款在某端无任何用例结果（非 manual） | high |
| 用例 fail | high |
| `cases_hash` 与当前用例集不一致 | high |
| 用例被 skip | medium |
| 出现未在 `Platform Delta` 声明的差异 | medium |
| manual 条款缺人工确认 | low |

**`Verdict: PASS` 才允许 feature 置 `DONE`。**

落盘：

```bash
python3 <sean-root>/scripts/sean_state.py set <name> parity='{"status":"fail","high":2}'
```

---

## 状态语义（不新增状态值）

`targets` 状态由 tasks **自动推导**，不需要手工维护：

| 该端 tasks 情况 | target 状态 |
|---|---|
| 无 task / 全 pending | `pending` |
| 有 in_progress | `in_progress` |
| 任一 failed | `failed` |
| 全部 done | `done` |

feature 级 `status` 仍用现有值，语义映射：

| 实际 | `status` |
|---|---|
| 任一 target failed | `BLOCKED` |
| 全部 done 但 parity 未过 | `INTEGRATION_FAIL` |
| 部分进行中 | `IN_PROGRESS` |
| 全部 done + parity pass | `DONE` |

> 因此 `sean list` / `status` / `handoff` / `review` 无需任何改动。

---

## 事后升级（已经各跑各的了）

```bash
python3 $S targets add <name> android,ios,harmony --primary android
```

- 现有 `tasks` 自动标记为 `primary` 端
- 另两端的 task **追加**进同一 `tasks` 数组（各带 `target`），不迁移、不重排
- 既有 history / undo 全部继续有效
- 另两端的旧需求文档不删除，在契约里登记为「已归档的独立实现」，作为差异比对输入

---

## 跨端 bug 传播

一端发现的 bug，另两端必须检查。给 bug 加 `affected_targets`：

```bash
python3 $S add-bug <name> --json '{"task_id":1,"classification":"implementation",
  "symptom":"断网时进入 loading 常驻","found_by":"user-manual",
  "affected_targets":["android","ios","harmony"],"status":"open"}'
```

`sean bug` 流程追加一步：**修复前先确认该 bug 是否存在于 `affected_targets` 的每一端**，各端分别补回归测试。

---

## 检查清单

启用多端前逐条确认：

- [ ] 需求文档只有一份（三端不各自 `sean start`）
- [ ] 契约已写且 `status: locked`，有 owner
- [ ] 每条 `C-NN` 都有 `verify` 方式，golden-case 条款有对应 cases 文件
- [ ] `Platform Delta` 已列出所有允许的差异，其余视为缺陷
- [ ] plan 里没有把任务矩阵做成表格（避免解析器误判）
- [ ] 各端 task 都带 `target` 字段
- [ ] `results/*.json` 的 `cases_hash` 与当前 cases 一致
- [ ] `sean_parity.py` 返回 `PASS` 后才置 `DONE`
