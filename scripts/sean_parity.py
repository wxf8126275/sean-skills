#!/usr/bin/env python3
"""
sean_parity.py — 跨端一致性校验（可选能力，单端项目不会用到）。

只读 + 判定，不写 state。判定结果由 AI 决定如何落盘
（通常在执行 `sean_state.py set <feature> parity='{...}'`）。

契约约定：
  docs/contracts/<date>-<feature>/
  ├── contract.md            # 条款表：| C-01 | 类别 | 规则 | 验证方式 | cases 文件 |
  ├── cases/                 # 共享 golden cases（各端读同一批文件）
  │   └── state-machine.json
  └── results/               # 各端结果，格式统一
      ├── android.json
      └── ios.json

results/<target>.json 格式：
  {
    "target": "ios",
    "contract_id": "login-v2",
    "cases_hash": "<sha256 of cases 目录内容>",
    "cases": {"C-01-01": "pass", "C-01-02": "fail", "C-03": "manual-ok"}
  }

用法：
  python3 sean_parity.py --feature login
  python3 sean_parity.py --contract docs/contracts/2026-11-05-login/contract.md
  python3 sean_parity.py --feature login --json
  python3 sean_parity.py --cases-hash docs/contracts/2026-11-05-login/cases   # 生成 cases_hash 供 results 引用
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CLAUSE_ROW = re.compile(r"^\|\s*(C-\d+)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|", re.MULTILINE)
DELTA_ROW = re.compile(r"^\|\s*(D-\d+)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|", re.MULTILINE)


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def cases_hash(cases_dir: Path) -> str:
    """对 cases 目录下所有 .json 的内容做稳定排序后取 sha256。"""
    if not cases_dir.is_dir():
        return ""
    digest = hashlib.sha256()
    for path in sorted(cases_dir.glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def parse_contract(path: Path) -> tuple[list[dict], list[dict], dict]:
    text = path.read_text(encoding="utf-8")
    meta = {}
    for key in ("contract_id", "status", "targets"):
        match = re.search(rf"^\s*>?\s*{key}\s*:\s*(.+)$", text, re.MULTILINE)
        if match:
            meta[key] = match.group(1).strip()
    clauses = []
    for match in CLAUSE_ROW.finditer(text):
        clauses.append({
            "id": match.group(1).strip(),
            "kind": match.group(2).strip(),
            "rule": match.group(3).strip(),
            "verify": match.group(4).strip() or "golden-case",
            "cases": match.group(5).strip(),
        })
    deltas = []
    for match in DELTA_ROW.finditer(text):
        deltas.append({
            "id": match.group(1).strip(),
            "target": match.group(2).strip(),
            "rule": match.group(3).strip(),
            "approved_by": match.group(4).strip(),
        })
    return clauses, deltas, meta


def load_results(results_dir: Path) -> dict:
    out = {}
    if not results_dir.is_dir():
        return out
    for path in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"{path} 解析失败: {exc}")
        target = data.get("target") or path.stem
        out[target] = data
    return out


def check(clauses: list[dict], deltas: list[dict], meta: dict, results: dict,
          expected_targets: list[str], current_hash: str) -> dict:
    findings = []
    per_clause = []

    for clause in clauses:
        cid = clause["id"]
        manual = "manual" in clause["verify"].lower()
        row = {"id": cid, "kind": clause["kind"], "verify": clause["verify"], "targets": {}}
        for target in expected_targets:
            data = results.get(target)
            if data is None:
                row["targets"][target] = "no-result"
                continue
            cases = data.get("cases") or {}
            related = {k: v for k, v in cases.items() if k == cid or k.startswith(cid + "-")}
            if not related:
                row["targets"][target] = "missing"
            elif any(str(v).lower() in ("fail", "failed", "error") for v in related.values()):
                row["targets"][target] = "fail"
            elif any(str(v).lower() in ("skip", "skipped", "pending") for v in related.values()):
                row["targets"][target] = "skipped"
            else:
                row["targets"][target] = "pass"
        per_clause.append(row)

        for target, state in row["targets"].items():
            if state == "no-result":
                # manual 条款无法自动验证，缺结果只算改进项，不阻塞交付
                findings.append({"clause": cid, "target": target,
                                 "severity": "low" if manual else "high",
                                 "issue": "缺少 results 文件"})
            elif state == "missing":
                if manual:
                    findings.append({"clause": cid, "target": target, "severity": "low",
                                     "issue": "manual 条款未记录人工确认结果"})
                else:
                    findings.append({"clause": cid, "target": target, "severity": "high",
                                     "issue": "该条款在此端无用例结果"})
            elif state == "fail":
                findings.append({"clause": cid, "target": target, "severity": "high",
                                 "issue": "用例未通过"})
            elif state == "skipped":
                findings.append({"clause": cid, "target": target, "severity": "medium",
                                 "issue": "用例被跳过"})

    # 用例集一致性：各端是否读同一批 golden cases
    for target, data in results.items():
        recorded = data.get("cases_hash")
        if current_hash and recorded and recorded != current_hash:
            findings.append({"clause": "*", "target": target, "severity": "high",
                             "issue": f"用例集版本不一致（记录 {recorded} ≠ 当前 {current_hash}）"})

    # 未申报的平台差异：results 里出现了不在白名单的 target 差异声明
    approved = {(d["target"], d["rule"]) for d in deltas}
    for target, data in results.items():
        for item in data.get("deltas") or []:
            if (target, item) not in approved:
                findings.append({"clause": "*", "target": target, "severity": "medium",
                                 "issue": f"未申报的平台差异: {item}"})

    high = [f for f in findings if f["severity"] == "high"]
    medium = [f for f in findings if f["severity"] == "medium"]
    return {
        "contract_id": meta.get("contract_id"),
        "contract_status": meta.get("status"),
        "targets": expected_targets,
        "clauses": per_clause,
        "findings": findings,
        "status": "fail" if high else ("warn" if medium else "pass"),
        "summary": {"clauses": len(clauses), "deltas": len(deltas),
                    "high": len(high), "medium": len(medium)},
    }


def resolve_contract(args) -> Path:
    if args.contract:
        return Path(args.contract)
    root = Path(args.project_root).resolve()
    found = sorted((root / "docs" / "contracts").glob(f"*-{args.feature}*/contract.md")) if args.feature else []
    if not found:
        fail("未找到契约。用 --contract 指定，或确认 docs/contracts/<date>-<feature>/contract.md 存在")
    return found[-1]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sean_parity.py", description="跨端一致性校验")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--feature", help="feature 名（用于定位契约与读取 targets）")
    parser.add_argument("--contract", help="契约文件路径")
    parser.add_argument("--targets", help="逗号分隔，覆盖自动推断")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--cases-hash", help="只计算并打印 cases 目录 hash 后退出")
    args = parser.parse_args(argv)

    if args.cases_hash:
        print(cases_hash(Path(args.cases_hash)))
        return 0

    contract_path = resolve_contract(args)
    if not contract_path.exists():
        fail(f"契约不存在: {contract_path}")
    clauses, deltas, meta = parse_contract(contract_path)
    if not clauses:
        fail(f"契约里未解析到任何条款（格式：| C-01 | 类别 | 规则 | 验证方式 | cases |）：{contract_path}")

    base = contract_path.parent
    current_hash = cases_hash(base / "cases")
    results = load_results(base / "results")

    if args.targets:
        expected = [t.strip() for t in args.targets.split(",") if t.strip()]
    elif meta.get("targets"):
        expected = [t.strip() for t in meta["targets"].split(",") if t.strip()]
    else:
        expected = list(results.keys())
    if not expected:
        fail("无法确定 targets：契约未声明、results 目录为空、也未传 --targets")

    report = check(clauses, deltas, meta, results, expected, current_hash)
    report["contract_path"] = str(contract_path)
    report["cases_hash"] = current_hash

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "pass" else 1

    print(f"# parity: {report['contract_id']}  ({contract_path})")
    print(f"  targets: {', '.join(expected)}   cases_hash: {current_hash or '—'}")
    print()
    width = max((len(c["id"]) for c in clauses), default=4)
    for row in report["clauses"]:
        cells = "  ".join(f"{t}={row['targets'][t]}" for t in expected)
        print(f"  {row['id']:<{width}}  {row['kind']:<14} {cells}")
    if deltas:
        print()
        for delta in deltas:
            print(f"  {delta['id']}  delta:{delta['target']:<10} 已批准({delta['approved_by'] or '未署名'}) — {delta['rule']}")
    print()
    for item in report["findings"]:
        print(f"  [{item['severity']}] {item['clause']}/{item['target']}: {item['issue']}")
    print()
    print(f"Verdict: {report['status'].upper()}  "
          f"({report['summary']['high']} high, {report['summary']['medium']} medium)")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
