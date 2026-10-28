# `sean run` 并行执行

> 仅在 Pre-flight 询问「是否启用子智能体并行执行」且用户选「是」时读本文件。
> 成本提醒：每个子智能体都要重建上下文，**并行一定比串行更贵**，只在大 task（预计 >10 分钟）时才值得。

## 分组与分发

1. **分组 wave**：无未满足依赖的为 Wave 1；依赖全在 Wave 1 的为 Wave 2；依此类推。
2. **wave 内**区分 `parallel_safe: true`（并发）与其余（串行）。
3. **分发子智能体**，每个收到精简的 Task Context Package（见下）。
4. 子智能体**不写 state**，只返回结构化结果；由主 agent 统一落盘。
5. 任一子 agent 返回 `failed` → 该 task 标 `failed`，走 Fix Loop 策略。
6. 当前 wave 全部解决后进入下一 wave。

可用 `scripts/sean_dispatch.py <plan> --format json [--feature <name>]` 自动分组 wave 并生成 context package。

## Task Context Package（精简版）

```yaml
task_id: <number>
task_name: "<kebab-case>"
project_root: "<absolute path>"
conventions_path: "docs/team/conventions.md"   # 传路径，不传全文
conventions_digest: |                          # ≤10 行关键约束，主 agent 分发时补
  - 函数 ≤40 行；文件 ≤400 行
  - 禁用 any/object；错误必须显式处理
  - 测试必须验证行为，禁止 assert True
files_create: ["<path>", ...]
files_modify: ["<path>", ...]
test_file: "<path>"
test_pattern_path: "<one existing test file>"  # 传路径，让子 agent 自己按需读
tdd_contract:
  - 先写失败测试并确认 RED
  - 写最小实现使 GREEN
  - 禁止修改测试文件
  - Fix Loop 最多 3 次
  - 测试输出用 -q --tb=short，只读首个 failure 尾部 30 行
output_format:
  status: "done|failed"
  tests_total: <n>
  tests_passed: <n>
  fixes: <n>
  files_modified: ["<path>"]
  report: "<path>"
  error_message: "<if failed>"
```

**关键差异**：`conventions` 与 `test_pattern` 传**路径**而非全文内容，子 agent 按需读取——避免每个子 agent 重复吞下同样的几 KB。

## 子智能体返回契约

结束时必须输出一个 JSON 块：

```json
{"task_id": 3, "status": "done", "tests_total": 4, "tests_passed": 4, "fixes": 1,
 "files_modified": ["src/service.py"],
 "report": "docs/test-reports/2026-09-29-myfeature/task-3-service.md",
 "error_message": null}
```

失败时 `status: "failed"`，`report: null`，`error_message` 写根因。
