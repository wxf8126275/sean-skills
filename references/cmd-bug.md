# `sean bug <name> [description...] [--task N] [--already-fixed --files <f1,f2>]`

记录并修复 `sean run` 完成后用户实测发现的 bug。

这是 sean 知识传承链中**唯一能捕获「测试没拦住、用户实测才发现」的缺陷**的入口。不记录的话，`sean sync` / `sean learn` 会把状态"恢复"成干净的 DONE，下一个 AI 完全不知道这个 bug 曾经存在。

---

## 两种模式

| 模式 | 触发 | 行为 |
|---|---|---|
| **主动式**（默认） | `sean bug <name> "描述"` | 驱动 TDD 修复：写复现测试 → RED → 修实现 → GREEN → 记录 |
| **追溯式** | `sean bug <name> "描述" --already-fixed --files src/foo.py` | 用户已在对话里修好，sean 只补记录 + 补回归测试 + 强制跑一遍 |

## 设计原则

- **不重开 task**：task 确实完成了它声明的行为。bug 作为 feature 级独立条目挂在 `bugs[]`，用 `task_id` 反向关联。重开会让"已完成"的历史变模糊。
- **回归测试落点**：追加到原 `test_file`（同模块测试放一起）。
- **test-first 铁律**：bug 修复也必须先写复现测试。没有复现测试就不许标记修复完成。

---

## Steps

1. **解析参数**：`<name>`、`[description...]`（一句话症状）、`--task N`、`--already-fixed`、`--files f1,f2`。

2. **取状态**：`python3 <sean-root>/scripts/sean_state.py get <name> --full`。不存在则报错。

3. **分类**：
   - **implementation**：代码没做到 task 的 `acceptance` → 实现缺陷。
   - **spec-gap**：代码做到了 AI 理解的，但用户要的是别的 → 需求文档修正。
   - 给了 `--task N` 时，读该 task 的 `acceptance` 辅助判断。

4. **记录 bug**
   ```bash
   python3 <sean-root>/scripts/sean_state.py add-bug <name> --json '{
     "task_id": 3,
     "classification": "implementation",
     "symptom": "<用户描述>",
     "root_cause": null,
     "found_by": "user-manual",
     "status": "open",
     "regression_test": null,
     "fixed_by": null,
     "files_modified": []
   }'
   ```

5. **写 bug 报告** `docs/test-reports/<date>-<name>/bugs.md`
   模板：`templates/bugs.md`。每条必含：Classification / Task / Found by / Status / Symptom / Reproduction / Root Cause / Fix / Regression Test。

6. **追溯模式**（`--already-fixed`）：
   - 跑该 feature 的完整测试套件，确认现状 GREEN。
   - **补回归测试**：追加到该 task 的 `test_file`，且必须能复现原 bug（说明它在修复前会失败）。
   - 跑该回归测试 → PASS。
   - 更新 bug：`status: fixed`、`regression_test`、`files_modified`、`fixed_by`。
   - 补全 `bugs.md`。
   - `snapshot bug <name>`。

7. **主动模式**（默认）：
   - **写复现测试**：追加到该 task 的 `test_file`，必须先看到 RED。
   - 跑 → 确认 RED（只读首个 failure 尾部 30 行）。
   - **修实现**（绝不改测试）。
   - 跑 → GREEN。
   - 跑该 feature 回归 → PASS。
   - 更新 bug：`status: fixed` + `root_cause` + `regression_test` + `files_modified` + `fixed_by`。
   - 补全 `bugs.md`。
   - `snapshot bug <name>`。

8. **spec-gap 额外处理**：
   - 同时更新 `docs/requirements/<date>-<name>.md`，纠正需求，避免下一个 AI 重复同样的误解。
   - 在 `bugs.md` 里标注需求 diff。

9. **feature 状态规则**：
   - 存在 `open` / `fixing` 的 bug → feature **不得**为 `DONE`，置 `IN_PROGRESS` 或计入 `post_done_bugs`。
   - 全部为 `fixed` / `wontfix` → 可回到 `DONE`。

10. **更新 handoff.md** 的 Reliability 段（追加一行，不重写全文）。

11. **输出**：bug id、分类、状态、回归测试路径、下一步。

---

## Usage

```bash
# 主动式
sean bug auth "登录后刷新页面跳回登录页" --task 3

# 追溯式
sean bug auth "登录后刷新页面跳回登录页" --already-fixed --files src/auth.py

# 多文件
sean bug api "分页参数不生效" --already-fixed --files src/api.py,src/service.py
```
