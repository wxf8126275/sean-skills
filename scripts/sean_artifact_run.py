#!/usr/bin/env python3
"""
sean_artifact_run.py — 产物脚本执行器（默认 dry-run，--execute 才真跑）。

这是 `sean artifact run` 的机械实现：把「默认 dry-run」从提示变成强制。
即使调用方忘了传 --execute，本脚本也只会打印将要执行的命令，绝不碰真实环境。

用法:
  # dry-run（默认）
  python3 sean_artifact_run.py --project <root> --feature auth --artifact migrations/001_create_users.sql

  # 真正执行
  python3 sean_artifact_run.py --project <root> --feature auth --artifact migrations/001_create_users.sql --execute

退出码:
  0  dry-run 完成 / 执行成功 / config 类不可执行（设计如此）
  2  缺少 --execute（被护栏拦下）—— 保留位，当前 dry-run 返回 0
  3  产物未声明 / catalog 缺失
  4  项目无对应执行工具
  N  执行命令自身的退出码

存储兼容：v5 明细在 docs/.sean/features/<name>.json；v4 全量在 docs/.sean/state.json。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def load_feature(root: Path, name: str) -> dict | None:
    detail = root / "docs" / ".sean" / "features" / f"{name}.json"
    if detail.exists():
        try:
            return json.loads(detail.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"ERROR: {detail} 解析失败: {exc}", file=sys.stderr)
            raise SystemExit(3)
    state_path = root / "docs" / ".sean" / "state.json"
    if not state_path.exists():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: state.json 解析失败: {exc}", file=sys.stderr)
        raise SystemExit(3)
    return (state.get("features") or {}).get(name)


def find_artifact(feature: dict, artifact_path: str):
    for task in feature.get("tasks") or []:
        for art in task.get("artifacts") or []:
            if art.get("path") == artifact_path:
                return task, art
    return None, None


def find_catalog(root: Path, feature: str) -> Path | None:
    d = root / "docs" / "artifacts"
    if not d.is_dir():
        return None
    exact = sorted(d.glob(f"*-{feature}.md"))
    if exact:
        return exact[-1]
    loose = [f for f in sorted(d.glob("*.md")) if feature in f.stem]
    return loose[-1] if loose else None


def detect_tool(artifact_type: str, root: Path, artifact_path: str):
    """返回 (tool, argv, dryrun_argv)。dryrun_argv 保证不产生副作用。"""
    if artifact_type == "database":
        if (root / "alembic.ini").exists():
            return ("alembic", ["alembic", "upgrade", "head"],
                    ["alembic", "upgrade", "head", "--sql"])
        if artifact_path.endswith(".sql"):
            return ("psql", ["psql", "-f", artifact_path], None)
        return (None, None, None)
    if artifact_type == "batch":
        # 注意 `bash -n <file>` 才是语法检查；`bash <file> -n` 会把 -n 当参数真执行
        return ("bash", ["bash", artifact_path], ["bash", "-n", artifact_path])
    if artifact_type == "config":
        return ("none", None, None)
    return (None, None, None)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="执行产物（默认 dry-run）")
    ap.add_argument("--project", required=True, help="项目根目录")
    ap.add_argument("--feature", required=True, help="feature 名")
    ap.add_argument("--artifact", required=True, help="产物路径（须与 plan 声明一致）")
    ap.add_argument("--execute", action="store_true", help="真正执行；不加则只 dry-run")
    args = ap.parse_args(argv)

    root = Path(args.project).resolve()

    feature = load_feature(root, args.feature)
    if feature is None:
        print(f"ERROR: feature '{args.feature}' 不在 state 中（docs/.sean/）", file=sys.stderr)
        return 3

    task, art = find_artifact(feature, args.artifact)
    if art is None:
        print(f"ERROR: 产物 '{args.artifact}' 未在 plan 中声明（feature: {args.feature}）", file=sys.stderr)
        declared = [a.get("path") for t in (feature.get("tasks") or [])
                    for a in (t.get("artifacts") or [])]
        print(f"       已声明: {declared or '(无)'}", file=sys.stderr)
        print("       先运行 'sean plan <name>' 声明产物。", file=sys.stderr)
        return 3

    catalog = find_catalog(root, args.feature)
    art_type = art.get("type", "")
    tool, cmd, dryrun_cmd = detect_tool(art_type, root, args.artifact)

    if tool == "none":
        print("CONFIG 产物 — 设计上不可执行，无需操作。")
        print(f"  Path    : {args.artifact}")
        print(f"  Catalog : {catalog.relative_to(root) if catalog else '(missing)'}")
        print("  若已在项目外应用，用 'sean artifact <name> mark <path> --executed --verified' 记录。")
        return 0

    if tool is None or cmd is None:
        print(f"ERROR: 未探测到 {art_type} 类型的执行工具", file=sys.stderr)
        print("       项目缺少 alembic.ini / .sql 文件 / shell 支持。", file=sys.stderr)
        print(f"       修复工具链，或用 'sean artifact {args.feature} mark {args.artifact} --executed'。",
              file=sys.stderr)
        return 4

    if not args.execute:
        print("=" * 60)
        print("DRY-RUN — 未执行任何操作")
        print("=" * 60)
        print(f"  Feature : {args.feature}")
        print(f"  Artifact: {args.artifact}")
        print(f"  Type    : {art_type}")
        print(f"  Task    : {task.get('id')} ({task.get('name', '')})")
        print(f"  Tool    : {tool}")
        print(f"  Command : {' '.join(cmd)}")
        if catalog is None:
            print("  ⚠ catalog 缺失：执行后无法回写执行记录")
        print()
        if dryrun_cmd:
            print(f"  Probe   : {' '.join(dryrun_cmd)}")
            print("-" * 60)
            probe = subprocess.run(dryrun_cmd, cwd=root, capture_output=True, text=True)
            if probe.stdout:
                print(probe.stdout[:2000])
            if probe.stderr:
                print("[stderr]", probe.stderr[:1000])
            print("-" * 60)
            print(f"  Probe exit code: {probe.returncode}")
            if probe.returncode != 0:
                print("  ⚠ 探测失败 —— 真正执行很可能也会失败，先修脚本")
        else:
            print("  (该工具无安全 dry-run 模式，仅显示命令)")
        print()
        print("确认无误后加 --execute 真正执行：")
        print(f"  sean artifact {args.feature} run {args.artifact} --execute")
        return 0

    print("=" * 60)
    print("EXECUTE — 将改变外部状态")
    print("=" * 60)
    print(f"  Command: {' '.join(cmd)}")
    print("-" * 60)
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout[:4000])
    if result.stderr:
        print("[stderr]", result.stderr[:2000])
    print("-" * 60)
    print(f"Exit code: {result.returncode}")
    if result.returncode == 0:
        print()
        print("下一步：回写状态（catalog + state 两处都要）：")
        print("  catalog: 该产物 Executed 列改 ✅，并在 Execution Log 追加一行")
        print(f"  state  : sean_state.py set {args.feature} ...（或 add-task 时带 executed:true）")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
