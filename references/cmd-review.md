# `sean review <name>`

代码质量自审 + Agent Work Loop 五维评估。

**核心原则：只审 diff，不审全库。** 旧版本要求"读所有创建/修改的文件"，等于把 feature 的代码再读一遍——这是 review 环节最大的成本来源，已废弃。

---

## Steps

### 1. 取变更集（不读文件全文）

```bash
git diff --stat HEAD~1                    # 若整个 feature 在最近一次提交
# 或按 plan 的文件清单取 diff
git diff --unified=1 HEAD~1 -- <changed files>
```

`--unified=1` 是关键：上下文压缩到 1 行，token 消耗约为默认 `-U3` 的一半。

### 2. 机械检查（用命令，不靠逐文件阅读）

```bash
# 遗留标记
grep -nE 'TODO|FIXME|HACK|XXX' <changed files>

# 弱类型
grep -nE ':\s*(any|object)\b|<any>' <changed files>

# 空 catch / 裸露 except
grep -nE 'except\s*:|catch\s*\([^)]*\)\s*\{\s*\}' <changed files>

# 文件体量
wc -l <changed non-test files>
```

阈值：单文件 >400 行（不含测试）→ 记 finding。

**函数长度**：不为此引入 AST 分析。改为抽样——在 diff 中挑最长的新增函数块，目测行数；超 40 行记 finding。抽样即可，不必穷举。

### 3. 测试质量（只读测试文件的断言部分）

```bash
grep -nE 'assert|expect\(' <test files>
```

检查：是否有 `assert True` / `assert 1 == 1` / 断言实现细节 / 空测试。

### 4. 五维评估（只评有证据的，不额外扫描）

| Dimension | Question | Evidence States |
|---|---|---|
| **Task Understanding** | 是否理解目标与"完成"的定义？ | `present`（有需求）→ `wired`（验收标准清晰）→ `exercised`（task 映射到验收项）→ `outcome-supported`（回归证明） |
| **Controlled Execution** | 是否走了可复现的路径？ | `present`（有计划）→ `wired`（依赖已声明）→ `exercised`（按序执行）→ `outcome-supported`（无环依赖） |
| **Change Validation** | 有证据表明改动有效？ | `present`（有测试文件）→ `wired`（测试运行过）→ `exercised`（观察到 RED→GREEN）→ `outcome-supported`（回归通过） |
| **Reliable Delivery** | 交付边界处被接受了吗？ | `present`（有 handoff）→ `wired`（commit message 就绪）→ `exercised`（人/CI 接受）→ `outcome-supported`（已合入/部署） |
| **Learning Capture** | 下一个任务能受益吗？ | `present`（有 handoff）→ `wired`（sync 可用）→ `exercised`（下个 agent 用了 handoff）→ `outcome-supported`（后续任务更快） |

**评分上限由证据状态决定：**

| 证据状态 | 分数上限 |
|---|---|
| `missing` / `unobserved` / `not-applicable` | 59 |
| `present` | 74 |
| `wired` | 84 |
| `exercised` | 94 |
| `outcome-supported` | 100 |

**证据来源只用前三步已获得的信息**（state、diff、grep 结果、测试报告）。**不要**为了给某个维度找证据去额外读文件或跑新命令。找不到证据 → 记 `unobserved`，分数上限 59，这本身就是有效结论。

### 5. 生成 findings

只为证据状态 < `exercised` **且**已被检查到的缺口生成 finding：

```json
{
  "id": "F001",
  "dimension": "change-validation",
  "severity": "high|medium|low",
  "evidence": "<观察到了什么>",
  "impact": "<后果>",
  "repair": "<修复方案>",
  "verifier": "<如何验证修复>",
  "status": "open"
}
```

- 不为 `unobserved` 的外部边界生成 finding（无法验证的东西不构成缺口）。
- Severity：`high` = 阻断交付；`medium` = 降低质量；`low` = 改进机会。

### 6. 落盘

```bash
python3 <sean-root>/scripts/sean_state.py set <name> review='{...五维分数...}'
python3 <sean-root>/scripts/sean_state.py add-finding <name> --json '{...}'
python3 <sean-root>/scripts/sean_state.py snapshot review <name>
```

`review.md` 用 `templates/review.md`，只写三张表 + 结论。

### 7. 输出 verdict

`PASS` / `FAIL (N issues, M findings)`。

---

## Token 提示

- diff 优先用 `--stat` 先看规模，超过 800 行的 diff 分批审（按文件分组），不要一次塞进上下文。
- 已在本会话实现过这些代码时，第 2 步的机械检查仍然值得跑（命令便宜），但第 3 步的测试阅读可跳过——你对断言质量已有判断。
- **不要**把 review 做成"再实现一遍"。发现问题的落点是 findings 列表，不是当场改代码。
