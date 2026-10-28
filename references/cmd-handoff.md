# `sean handoff <name> [--lite]`

生成交接文档——让另一个 AI 或人类能无缝接手。

这是本技能最核心的协作命令。触发场景：

- Agent-A 完成了，换 Agent-B 继续开发
- 同一个 Agent 但会话被清空（上下文丢失），需要恢复现场
- 人类想检查 AI 做了什么

---

## Steps

1. **取状态**（唯一权威来源）：
   ```bash
   python3 <sean-root>/scripts/sean_state.py get <name> --full
   ```
2. **读最近一份 task 报告**：只读 `Status` / `Result` / `Verdict` 三处（`grep -n` 定位后读片段），不要通读全部报告。
3. **文件清单校验**（**不读文件内容**）：
   - 路径来源：plan 的 `files_create` / `files_modify` + state 的 `artifacts[]`。
   - 只用 `ls -1 <path>` 或 `test -f <path>` 确认存在性。
   - ⚠️ 旧版本要求"读所有创建/修改的文件并与 plan 比对"，这会把整个 feature 的代码重新读一遍。**现在禁止**——文件确实存在即可，内容正确性由测试与 review 保证。
4. **生成** `docs/test-reports/<date>-<name>/handoff.md`
   模板：`templates/handoff.md`。必含章节：
   `Status` / `Reliability` / `What Was Done` / `File Inventory` / `Artifacts` / `Post-Run Bugs` / `Current Blocker` / `Next Steps` / `Known Risks` / `How to Resume`
5. **输出**：handoff 路径 + 终端打印精简摘要（≤10 行）。

---

## Reliability 段的判定

| 字段 | 取值依据 |
|---|---|
| Implemented by | state 中各 task 的 `implemented_by`（模型 id） |
| Task first-pass rate | 通过时 `fixes == 0` 的 task 数 / 总 task 数 |
| Post-run bugs | `bugs[]` 中 `found_by` 为 `user-manual` / `production` 的条数 |
| Trust level | HIGH：所有 bug 都被 task 测试或回归捕获<br>MEDIUM：1-2 个 user-manual bug，已修复且补了回归测试<br>LOW：3+ bug，或任何 production 发现的 bug → 建议独立复核 |

---

## `--lite`

只输出 5 行摘要，追加到该 feature 的 `summary.md` 末尾，不生成 `handoff.md`：

```
## Handoff (lite) <ISO8601>
- Status: DONE | 4/4 tasks | tests: 12/12
- Files: 3 created, 2 modified
- Artifacts: 1 database (created, not executed)
- Bugs: 0 open
- Next: <one concrete action>
```

适用：单 Agent 短期任务、内部工具。跨 Agent 接力或需要审计时不要用 lite。

---

## 反模式

- ❌ 把整个 feature 的源码再读一遍来"验证"交接文档 —— 这是最贵的做法，且不产生新信息。
- ❌ 复制粘贴完整测试输出到 handoff —— 只写结论与数字。
- ❌ 写「Next Steps」时含糊（"继续完善"）—— 必须是可执行动作。
