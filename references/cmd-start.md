# `sean start <name> [description...]`

创建需求文档。

---

## Steps

1. **校验名称**：必须小写 kebab-case，正则 `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`。
   非法 → `名称非法：仅小写字母/数字/连字符`。

2. **检查是否存在**：若 `docs/requirements/<date>-<name>.md` 已存在，先问是否覆盖。

3. **收集需求**：
   - 给了 `[description...]` → 直接作为 problem statement。
   - 没给 → 问 3 个问题（一次问完，不要逐条往返）：
     - 这个功能解决什么问题？（一句话）
     - 关键行为是什么？（逗号分隔）
     - 验收标准是什么？（逗号分隔）

4. **写需求文档** `docs/requirements/<YYYY-MM-DD>-<name>.md`
   模板：`templates/requirement.md`。必含四节：`Problem` / `Behaviors` / `Acceptance Criteria` / `Context`。
   - `Acceptance Criteria` 每条必须标注验证方式（`→ verifiable by <test/manual/demo>`）。
   - `Context.Non-goals` 明确写出「本功能不做什么」，这是后续防范围蔓延的依据。

   > **非代码产物（数据库脚本 / 批处理 / 配置文件）不在本阶段声明。**
   > `sean plan` 会从 Behaviors + Acceptance Criteria 自行推断，写入 task 的 `artifacts` 字段。
   > 需求方如需强制某个产物，可在 Behaviors 里明写（例如"需要建表 SQL"），plan 阶段会据此推断。

5. **落状态**（`create` 已内置 `status: DRAFT`，无需再设）
   ```bash
   python3 <sean-root>/scripts/sean_state.py create <name> \
     --requirement docs/requirements/<date>-<name>.md --set-active
   python3 <sean-root>/scripts/sean_state.py snapshot start <name>
   ```

6. **输出**：需求文件路径 + 状态 `DRAFT` + 下一步 `sean plan <name>`。

---

## 多端需求（可选，默认不启用）

仅当同一需求要由多个端（Android / iOS / HarmonyOS 等）分别实现时：

1. **先探测，避免遗漏**（脚本完成，不要自己 `ls` 全仓）：
   ```bash
   python3 <sean-root>/scripts/sean_state.py detect-targets
   ```
   返回 `detected [...]` 时问用户一次是否多端对齐；返回 `off` 则永不再问。

2. **声明确认启用**：
   ```bash
   python3 <sean-root>/scripts/sean_state.py targets add <name> android,ios,harmony --primary android
   ```

3. 用户选「否」时，在 `docs/team/conventions.md` 追加 `multi_target: off`，后续不再询问。

启用后 `sean plan` 之前必须先产出契约。完整流程见 `references/multi-target.md`。

> 不启用时本步骤完全跳过，需求文档与单端流程一字不差。
