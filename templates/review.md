# Review: {{feature_name}}

> Generated: {{ISO8601}} · 基于 `git diff` + 机械检查 + state，**不重读全量源文件**

## File Quality

| File | File Len (>400?) | Weak Types | Error Handling | Leftovers (TODO/FIXME) | Clean |
|------|------------------|------------|----------------|------------------------|-------|
| {{path}} | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ |

> 函数长度检查为抽样（挑 diff 中最长的新增函数块），不做 AST 全量分析。

## Test Quality

| Test File | Meaningful | No Trivial Assert | RED Observed | Clean |
|-----------|------------|-------------------|--------------|-------|
| {{path}} | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ |

## Agent Work Loop Assessment

| Dimension | Evidence | Score | Finding |
|-----------|----------|-------|---------|
| Task Understanding | {{evidence}} | {{score}} | — |
| Controlled Execution | {{evidence}} | {{score}} | — |
| Change Validation | {{evidence}} | {{score}} | — |
| Reliable Delivery | {{evidence}} | {{score}} | — |
| Learning Capture | {{evidence}} | {{score}} | — |

<!-- 证据状态上限：missing/unobserved=59, present=74, wired=84, exercised=94, outcome-supported=100 -->
<!-- 只用已有信息评估；缺证据记 unobserved，不额外扫描文件或跑新命令 -->

## Findings

| ID | Dimension | Severity | Evidence | Repair |
|----|-----------|----------|----------|--------|
| F001 | {{dimension}} | {{severity}} | {{evidence}} | {{repair}} |

## Verdict

**PASS | FAIL** — {{n}} issues, {{m}} findings
