# `sean init <project-name>`

一次性初始化项目脚手架。

---

## Steps

1. **建 `docs/team/conventions.md`**
   以 `templates/team/conventions.md` 为模板写入。若已存在，先问是否覆盖。

2. **建 `docs/team/onboarding.md`**
   AI 可读的项目入门手册，以 `templates/team/onboarding.md` 为模板。内容必须**从代码库实际探测得出**，不要编造：
   - 技术栈（读 `package.json` / `pyproject.toml` / `go.mod` 等）
   - 目录布局（`ls` 顶层 + 主要源码目录，不要递归全量扫描）
   - 关键模式（路由注册方式、DI 容器、测试框架与命名约定）
   - 常用命令（dev / test / lint / build）
   - 禁止事项（从 `AGENTS.md` 继承）

   > Token 纪律：探测时用 `ls` + `grep -n` 定位关键配置，不要 `cat` 整个 lockfile 或大目录。

3. **初始化状态存储**
   ```bash
   python3 <sean-root>/scripts/sean_state.py init
   ```

4. **输出**：创建的文件清单 + 下一步提示（`sean start <feature>`）。

---

## 说明

- `conventions.md` 是后续所有 task 的代码风格基准，`sean run` 会在会话内读一次并复用。
- `onboarding.md` 是新人（人或 AI）接手的入口，应保持 ≤100 行——它会被反复读取，越长越贵。
- 本命令幂等：重复执行不破坏已有文件（除显式确认覆盖）。
