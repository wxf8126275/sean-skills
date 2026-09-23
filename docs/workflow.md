# sean 工作流详解

## 需求阶段：`sean start`

### 交互模式

当没有提供描述时，sean 会问 3 个问题：

```
? 这个功能解决什么问题？（一句话）
? 关键行为是什么？（逗号分隔）
? 验收标准是什么？（逗号分隔）
```

### 产出的需求文档

```markdown
# 需求：comments
## 背景与目标
用户需要在文档中添加评论
## 功能点
### F1: 添加评论
- 在文档下方显示评论输入框
- 提交评论后实时显示
## 验收标准
- [ ] 能成功提交评论
- [ ] 评论显示在文档下方
- [ ] 空评论提交被拒绝
```

---

## 计划阶段：`sean plan`

### 拆解原则

1. **按架构层级**：schema → service → controller → permissions → integration → frontend
2. **按依赖顺序**：前置任务先完成
3. **粒度均匀**：每个 task 预期 1-5 个测试
4. **独立可验证**：每个 task 完成后有明确通过/失败

### 产出的计划文档

```markdown
# 实现计划：comments
## Task 1: 数据库 schema
**Files**: apps/server/src/core/comment/comment.entity.ts
**Tests**: apps/server/src/core/comment/comment.entity.spec.ts
**Steps**:
- [ ] Step 1: 写失败测试 should define comment table
- [ ] Step 2: 运行确认 RED
- [ ] Step 3: 写 entity 定义
- [ ] Step 4: 运行确认 GREEN
```

---

## 执行阶段：`sean run`

### TDD 严格顺序

```
RED → GREEN → REFACTOR
  ↑                │
  └────────────────┘
      循环
```

**绝对不允许**：
- 先写实现再写测试
- 修改测试以匹配实现
- 跳过 RED 阶段直接写 GREEN

### 修复循环

```
测试失败
  → 读取错误输出
  → 分析根因（类型不匹配？逻辑错误？边界未处理？）
  → 修改代码
  → 重跑测试
  → 最多 3 轮
  → 仍红 → 暂停，等 sean fix 或 sean undo
```

### 报告格式

每个 task 完成后生成独立报告：

```markdown
# 测试报告：Task 1 — schema
## 结果
✅ 通过: 1 | ❌ 失败: 0 | 🔧 修复: 0
## 结论
PASS
```

---

## 失败恢复

### 场景 1：单个测试失败

```bash
sean run comments
# ... Task 3 测试失败 ...
# 自动修复中... 1/3
# 自动修复中... 2/3
# 修复成功，继续
```

### 场景 2：需要手动介入

```bash
sean run comments --no-fix
# ... Task 3 测试失败 ...
# 已暂停。手动修复后运行：
#   sean task comments 3
```

### 场景 3：撤销重做

```bash
sean run comments
# ... 跑完但结果不如预期 ...
sean undo comments  # 撤销整个 run
sean run comments --dry-run  # 重新预览
sean run comments             # 重新执行
```

### 场景 4：从失败处继续

```bash
sean run comments
# ... Task 5 连续失败 ...
sean undo comments 1   # 撤销 Task 5
# ... 检查计划，发现需要调整 ...
sean plan comments     # 重新生成计划
sean run comments 5    # 从 Task 5 继续
```

---

## 多项目工作

```bash
# 项目 A
cd ~/repos/docmost
sean list                # 查看 docmost 的功能

# 项目 B
cd ~/repos/stock-analysis
sean switch performance  # 切换到 stock-analysis 的功能
sean status              # 查看该功能状态
```

每个项目的 `docs/.sean/` 独立，互不影响。
