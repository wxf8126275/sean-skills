# State / History Schema (v5)

只在需要确认字段名时读本文件。**日常操作一律通过 `scripts/sean_state.py`，不手写 JSON。**

---

## 存储布局

```
docs/.sean/
├── state.json            # 摘要（目标 <2KB，不随 feature 数量膨胀过快）
├── features/<name>.json  # 单个 feature 的完整明细，按需读取
├── active                # 当前 feature 名（纯文本）
├── .pending.json         # 累积的逆向补丁，snapshot 时转为 history
└── history/
    ├── index.jsonl       # 一行一条事件（列表用，不读详情）
    └── <id>.json         # 单条事件的逆向补丁
```

---

## `state.json`（摘要）

```jsonc
{
  "version": 5,
  "active": "<feature-name>",
  "features": {
    "<feature-name>": {
      "name": "<feature-name>",
      "status": "DRAFT|PLANNED|IN_PROGRESS|DONE|BLOCKED|INTEGRATION_FAIL",
      "current_task": 0,
      "tasks_total": 0,
      "tasks_done": 0,
      "tests_passed": 0,
      "open_bugs": 0,
      "open_findings": 0,
      "blocked_reason": null,
      "updated_at": "<ISO8601>"
    }
  }
}
```

`sean list` / `sean status` 只读这一层，不碰 `features/` 下的明细。

---

## `features/<name>.json`（明细）

```jsonc
{
  "name": "<feature-name>",
  "requirement": "docs/requirements/<date>-<name>.md",
  "plan": "docs/plans/<date>-<name>.md",
  "status": "DRAFT|PLANNED|IN_PROGRESS|DONE|BLOCKED|INTEGRATION_FAIL",
  "current_task": 0,
  "tasks_total": 0,
  "tasks": [
    {
      "id": 1,
      "name": "<task-name>",
      "status": "pending|in_progress|done|failed",
      "evidence": "present|wired|exercised|outcome-supported|missing|unobserved",
      "tests_total": 0,
      "tests_passed": 0,
      "fixes": 0,
      "complexity": "low|medium|high",
      "parallel_safe": true,
      "depends_on": [],
      "files_create": ["<path>"],
      "files_modify": ["<path>"],
      "test_file": "<path>",
      "acceptance": "<criteria>",
      "report": "<path>",
      "implemented_by": "<model-id>",
      "artifacts": [
        {
          "path": "migrations/001_create_users.sql",
          "type": "database|batch|config",
          "purpose": "<一句话>",
          "status": "declared|created|failed",
          "executed": false,
          "verified": false,
          "catalog": "docs/artifacts/<date>-<name>.md"
        }
      ]
    }
  ],
  "tests_passed": 0,
  "tests_failed": 0,
  "tests_fixed": 0,
  "started_at": "<ISO8601>",
  "completed_at": null,
  "blocked_reason": null,
  "updated_at": "<ISO8601>",
  "review": {
    "task-understanding":   { "score": 0, "evidence": "unobserved" },
    "controlled-execution": { "score": 0, "evidence": "unobserved" },
    "change-validation":    { "score": 0, "evidence": "unobserved" },
    "reliable-delivery":    { "score": 0, "evidence": "unobserved" },
    "learning-capture":     { "score": 0, "evidence": "unobserved" }
  },
  "findings": [
    {
      "id": "F001",
      "dimension": "change-validation",
      "severity": "high|medium|low",
      "evidence": "<观察到的现象>",
      "impact": "<后果>",
      "repair": "<修复方案>",
      "verifier": "<如何验证>",
      "status": "open|verified|partial|blocked",
      "created_at": "<ISO8601>"
    }
  ],
  "bugs": [
    {
      "id": "B001",
      "task_id": 3,
      "classification": "implementation|spec-gap",
      "symptom": "<用户描述>",
      "root_cause": "<根因>",
      "found_by": "task-test|regression|review|user-manual|production",
      "status": "open|fixing|fixed|wontfix",
      "regression_test": "<test name>",
      "fixed_by": "<model-id>",
      "files_modified": ["<path>"],
      "created_at": "<ISO8601>",
      "resolved_at": "<ISO8601>"
    }
  ]
}
```

---

## 多端可选键（单端 feature 不存在这些键）

```jsonc
{
  "primary_target": "android",        // 未标 target 的 task 归属；缺失 = 单端
  "targets": {                        // 缺失 = 单端
    "android": "done",                // 由该端 tasks 自动推导，勿手工设置
    "ios": "in_progress",
    "harmony": "pending"
  },
  "contract": "docs/contracts/<date>-<name>/contract.md",
  "parity": { "status": "fail", "gaps": ["C-01/ios"] }
}
```

`tasks[]` 中每个 task 可带 `target` 与 `contract_ref`。**tasks 保持平铺**（不嵌套进 `targets`），因此 `task-status` / `undo` / `sync` / `list` 无需感知多端。

## history 事件

### `history/index.jsonl`（每行一条）

```json
{"id": "20261028T112233-run", "ts": "<ISO8601>", "action": "run", "feature": "auth", "undone": false}
```

`action` 取值：`start|plan|run|task|fix|bug|artifact|review|handoff`

### `history/<id>.json`（单条详情）

```jsonc
{
  "id": "20261028T112233-run",
  "timestamp": "<ISO8601>",
  "action": "run",
  "feature": "auth",
  "git_head": "<short sha>",
  "restore": [
    {
      "feature": "auth",
      "existed": true,
      "keys": { "status": "PLANNED", "tasks": [ /* 变更前的旧值 */ ] },
      "absent": ["blocked_reason"]
    }
  ],
  "files_created": ["src/a.py"],
  "files_modified": ["src/b.py"],
  "undone": false
}
```

**关键设计**：`restore.keys` 只保存**被改动顶层键的旧值**，`absent` 列出本次新增的键（undo 时删除）。
不再保存 `before` / `after` 两份完整 state 快照——单条记录因此从「2 × 全量 state」降到通常 <1KB，且**不随项目内 feature 总数增长**。

文件内容不做内联备份：`files_modified` 依靠 git 还原（`git checkout -- <path>`），`files_created` 直接删除。

---

## 迁移与容错

- 旧版（v4）把 feature 明细直接写在 `state.json.features.<name>` 里。首次读取时自动拆分到 `features/<name>.json` 并把 `state.json` 改成摘要，**无需手工操作**。
- `state.json` 写入采用 `tmp + os.replace`，避免进程被杀留下半个文件。
- 写入损坏时：`sean_state.py sync <name>` 从测试报告重建 task 状态。
- `history` 保留最近 200 条，超出自动裁剪。
