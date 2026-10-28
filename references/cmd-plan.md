# `sean plan <name>`

把需求拆解为可执行的 TDD 任务序列。

---

## 前置：多端 feature 必须先有契约

若 state 中该 feature 有 `targets` 键（`sean_state.py targets list <name>` 可确认）：

1. 确认 `docs/contracts/<date>-<name>/contract.md` 存在且 `status: locked`。缺失则 STOP，先补契约（流程见 `references/multi-target.md`）。
2. 每个 task 必须关联契约条款：详情块加 `**Target**: <端>` 与 `**Contract**: C-NN`，登记 state 时带 `target` / `contract_ref` 字段。
3. **任务矩阵写在契约文件里，不要做成 plan 的表格**——`sean_dispatch.py` 的正则会误把 5 列表格识别为 task。

单端 feature 跳过本节。

---

## Steps

1. **加载需求**：`docs/requirements/<date>-<name>.md`。缺失则报错并提示 `sean start`。
2. **加载规范**：`docs/team/conventions.md`（缺失则用 `templates/team/conventions.md` 的默认值）。
3. **分析**：从需求提取功能点 + 验收标准（一条验收标准通常对应 1-2 个 task）。
4. **按架构分层拆解**（顺序即依赖顺序）：
   - Database：schema、migration、entity
   - Service：业务逻辑、校验
   - Controller：API endpoint、DTO
   - Permissions：鉴权、guard
   - Integration：外部服务、WebSocket、后台任务
   - Frontend：UI 组件、页面

5. **每个 task 定义**：
   - `id`：顺序数字
   - `name`：短 kebab-case
   - `files_create`：精确新建路径
   - `artifacts`：本 task 产出的非代码产物（type + path + purpose）
   - `files_modify`：要改的既有文件
   - `test_file`：精确测试路径
   - `steps`：有序 TDD 步骤（red → green → verify）
   - `acceptance`：如何验证
   - `depends_on`：依赖的 task id（或空）
   - `estimated_complexity`：`low` | `medium` | `high`
   - `parallel_safe`：能否与其他 task 并发

6. **推断产物**（AI 自行决定，**不要问用户**）：
   - 依据：需求的 `Behaviors` + `Acceptance Criteria` + `Problem`。
   - 推断规则：

     | 需求中的信号 | 推断产物 |
     |---|---|
     | 存储 / 表 / 字段 / 关联 / 索引 / 迁移 | `database` |
     | 初始化数据 / 种子数据 / 迁移历史数据 / 定时任务 / 批量处理 | `batch` |
     | 密钥 / 配置项 / 环境变量 / 连接串 / 模板 | `config` |

   - 按项目自身约定赋具体路径（先看 `AGENTS.md` 与既有目录）：
     - `database` → `migrations/<NNN>_<slug>.sql`
     - `batch` → `scripts/<slug>.sh`
     - `config` → `config/<slug>.template`
   - **无信号就不声明产物**，不要为"显得周全"硬造。
   - 项目没有既有约定时，放在最可能的路径，并在 plan 输出里标注该假设，等用户 review 时纠正。

7. **校验**：无循环依赖，task 名唯一。

8. **写计划** `docs/plans/<YYYY-MM-DD>-<name>.md`
   模板：`templates/plan.md`。必含：`Task Summary` 表、`Dependency Graph`、`Artifact Inference` 表、`Task Details`。

9. **落状态**
   ```bash
   S=<sean-root>/scripts/sean_state.py
   # 逐个登记 task（含 artifacts）
   python3 $S add-task <name> --json '{"id":1,"name":"db-schema","status":"pending",
     "files_create":["migrations/001_x.sql"],"test_file":"tests/test_schema.py",
     "complexity":"low","parallel_safe":false,"depends_on":[],
     "artifacts":[{"path":"migrations/001_x.sql","type":"database","purpose":"用户表",
                   "status":"declared","executed":false,"verified":false}]}'
   python3 $S feature-status <name> PLANNED
   python3 $S snapshot plan <name>
   ```

10. **输出**：task 列表摘要 + 产物推断表 + 下一步 `sean run <name> --dry-run`。

---

## Token 提示

- 拆解时**不要**为每个 task 预设大段代码片段或伪代码——plan 是索引，不是实现。plan 越长，后续 `sean run` 读它的成本越高。
- `Task Details` 每项控制在 5-8 行。
- 产物推断表只列真正需要的，宁缺勿滥。
