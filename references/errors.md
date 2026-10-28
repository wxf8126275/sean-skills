# 错误速查

`sean` 命令遇到下述情形时的处理方式（仅需要时读）。

| 情形 | 处理 |
|------|------|
| 功能不存在 | 跑 `sean list`；新建走 `sean start` |
| 需求/计划缺失 | 依次补 `sean start` / `sean plan` |
| 依赖未完成 | 先跑依赖，或跳过该 task |
| 单测超时 (>60s) | 缩小测试范围或跳过 |
| 连续 2 个 task 失败 | STOP，输出 blocker，`sean undo` 回退 |
| 产物需执行确认 | 显式加 `--execute`（默认 dry-run） |
| 产物未声明 | 回 `sean plan` 补声明 |
