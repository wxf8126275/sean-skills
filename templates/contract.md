# Contract: {{feature_name}}

> contract_id: {{contract_id}}
> status: draft
> targets: android, ios, harmony
> 可选状态：draft（草稿）/ locked（锁定后修改需 owner + 各端确认）
> requirement: ../requirements/{{date}}-{{feature}}.md
> owner: {{owner}}
> generated: {{ISO8601}}

<!-- 契约是差异的唯一裁决依据。锁定（status: locked）后的修改需 owner + 各端确认。 -->
<!-- 本文档由 sean_parity.py 解析，请保持表格列顺序与 ID 格式。 -->

## Clauses

<!--
  ID 必须是 C-NN（两位数字）。验证方式：
    golden-case  — 各端跑 cases/ 下的共享用例
    contract-test— 各端对 API 契约写测试
    manual       — 人工确认，results 里记 "manual-ok"
-->

| ID | 类别 | 规则 | 验证方式 | Cases |
|----|------|------|----------|-------|
| C-01 | state-machine | 登录状态：idle→loading→authed/error，error 可重新 submit | golden-case | cases/state-machine.json |
| C-02 | api | POST /auth/login 返回 200/401/429 及对应错误码 | golden-case | cases/error-map.json |
| C-03 | validation | 密码为空时提交按钮禁用且不发请求 | manual | — |

## Boundary Conditions

<!-- 差异高发区。每条都应有对应的 golden case 或明确的平台差异声明。 -->

| # | 场景 | 期望行为 |
|---|------|----------|
| B-01 | 断网提交 | 提示可重试，不进入 loading 常驻态 |
| B-02 | token 过期 | 跳转登录页，清空本地凭证 |
| B-03 | 连续点击提交 | 只发一次请求 |

## Platform Delta

<!--
  显式批准的平台差异白名单。表里没有的差异一律视为缺陷。
  列顺序固定：ID | Target | 规则 | 批准人
-->

| ID | Target | 规则 | 批准人 |
|----|--------|------|--------|
| D-01 | ios | 使用系统 Face ID；其他端使用各自生物识别能力 | {{owner}} |

## 用例与结果约定

```
docs/contracts/{{date}}-{{feature}}/
├── contract.md          # 本文件
├── cases/               # 共享 golden cases（各端读同一批文件）
│   ├── state-machine.json
│   └── error-map.json
└── results/             # 各端结果（sean 产出或外部注入）
    ├── android.json
    ├── ios.json
    └── harmony.json
```

`results/<target>.json`：

```json
{
  "target": "android",
  "contract_id": "{{contract_id}}",
  "cases_hash": "<python3 scripts/sean_parity.py --cases-hash cases>",
  "cases": {"C-01-01": "pass", "C-01-02": "pass", "C-02-01": "pass"},
  "deltas": []
}
```

`cases_hash` 必须与当前用例集一致，否则 parity 会判定"用例集版本不一致"——这能防止某端用了过期的用例文件。

## 变更记录

| 日期 | 变更 | 影响端 | 确认人 |
|------|------|--------|--------|
| {{date}} | 初版 | all | {{owner}} |
