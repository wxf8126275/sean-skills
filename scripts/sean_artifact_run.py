#!/usr/bin/env python3
"""
sean_artifact_run.py — 产物脚本执行器（dry-run 默认，--execute 才真跑）。

这是 sean artifact run 的机械实现：把「默认 dry-run」从提示变成强制。
即使调用方忘了传 --execute，这个脚本也只会打印将要执行的命令，不会碰真实环境。

用法:
  # dry-run（默认）
  python sean_artifact_run.py --project <root> --artifact migrations/001_create_users.sql

  # 真正执行
  python sean_artifact_run.py --project <root> --artifact migrations/001_create_users.sql --execute

退出码:
  0  成功（dry-run 或执行成功）
  2  缺少 --execute（被护栏拦下）
  3  产物未声明 / catalog 缺失
  4  项目无对应执行工具
  N  执行命令自身的退出码
"""

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path


# 每种产物类型的执行工具探测规则
# 注意: dry-run 命令必须用 (文件, 标志) 顺序 —— `bash -n <file>` 才是语法检查，
# 而 `bash <file> -n` 会把 -n 当成位置参数并真的执行脚本。
TOOL_RULES = [
    # (type, 探测条件, 命令模板, dry-run 参数)
    ("database", "alembic", "alembic upgrade head", ["--sql"]),
    ("database", "psql", "psql -f {path}", []),
    ("batch", "bash", "bash {path}", ["-n"]),          # -n = 语法检查，不执行
]


def load_state(project_root: Path) -> dict:
    p = project_root / "docs" / ".sean" / "state.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def find_artifact(state: dict, feature: str, artifact_path: str):
    """Find the artifact record in state.json."""
    feat = state.get("features", {}).get(feature)
    if not feat:
        return None, None
    for task in feat.get("tasks", []):
        for art in task.get("artifacts", []) or []:
            if art["path"] == artifact_path:
                return task, art
    return None, None


def find_catalog(project_root: Path, feature: str):
    d = project_root / "docs" / "artifacts"
    if not d.exists():
        return None
    for f in sorted(d.glob("*.md")):
        if feature in f.name:
            return f
    return None


def detect_tool(artifact_type: str, project_root: Path, artifact_path: str):
    """Detect the right execution tool for this artifact type.

    Returns (tool, cmd, dryrun_cmd) where dryrun_cmd is a list of argv
    guaranteed not to execute anything.
    """
    # 1. 项目是否有 alembic（database 类型首选）
    if artifact_type == "database":
        if (project_root / "alembic.ini").exists():
            # alembic upgrade --sql 只生成 SQL 不执行
            return ("alembic", ["alembic", "upgrade", "head"],
                    ["alembic", "upgrade", "head", "--sql"])
        if (project_root / "migrations").exists():
            # 没有 dry-run 支持，返回 None 让调用方只显示命令
            return ("psql", ["psql", "-f", artifact_path], None)

    # 2. shell 脚本 —— bash -n <file> 才是语法检查
    if artifact_type == "batch":
        return ("bash", ["bash", artifact_path], ["bash", "-n", artifact_path])

    # 3. 配置模板：只校验语法，不执行
    if artifact_type == "config":
        return ("none", None, None)

    return (None, None, None)


def main():
    ap = argparse.ArgumentParser(description="Run an artifact (dry-run by default)")
    ap.add_argument("--project", required=True, help="project root")
    ap.add_argument("--feature", required=True, help="feature name")
    ap.add_argument("--artifact", required=True, help="artifact path (as declared in plan)")
    ap.add_argument("--execute", action="store_true",
                    help="actually execute; without this the tool only dry-runs")
    args = ap.parse_args()

    root = Path(args.project).resolve()

    # --- 校验 1: 产物必须在 plan 中声明 ---
    state = load_state(root)
    task, art = find_artifact(state, args.feature, args.artifact)
    if art is None:
        print(f"ERROR: artifact '{args.artifact}' is not declared in state.json for feature '{args.feature}'")
        print("       Run 'sean plan <name>' to declare artifacts.")
        sys.exit(3)

    catalog = find_catalog(root, args.feature)
    if catalog is None:
        print(f"ERROR: artifact catalog missing at docs/artifacts/ for '{args.feature}'")
        print("       Run 'sean run <name>' first.")
        sys.exit(3)

    art_type = art["type"]
    tool, cmd, dryrun_cmd = detect_tool(art_type, root, args.artifact)

    # --- 配置模板：不是"没有工具"，是"设计上不可执行" ---
    if tool == "none":
        print("CONFIG artifact — not executable by design, no action taken.")
        print(f"  Path: {args.artifact}")
        print(f"  Catalog: {catalog.relative_to(root)}")
        print("  Use 'sean artifact <name> mark <path> --executed --verified' if it was applied elsewhere.")
        sys.exit(0)

    # --- 校验 2: 项目是否有执行工具 ---
    if tool is None or cmd is None:
        print(f"ERROR: no execution tooling detected for artifact type '{art_type}'")
        print(f"       Project has no alembic.ini, migrations/, or shell available.")
        print("       Fix the tooling, or use 'sean artifact <name> mark <path> --executed'.")
        sys.exit(4)

    # --- 护栏：没有 --execute 就只 dry-run ---
    if not args.execute:
        print("=" * 60)
        print("DRY-RUN — nothing was executed")
        print("=" * 60)
        print(f"  Feature : {args.feature}")
        print(f"  Artifact: {args.artifact}")
        print(f"  Type    : {art_type}")
        print(f"  Task    : {task['id']} ({task['name']})")
        print(f"  Tool    : {tool}")
        print(f"  Command : {' '.join(cmd)}")
        print()

        # 尝试跑真正的 dry-run（语法检查 / --sql / EXPLAIN）
        if dryrun_cmd:
            print(f"  Probe   : {' '.join(dryrun_cmd)}")
            print("-" * 60)
            r = subprocess.run(dryrun_cmd, cwd=root, capture_output=True, text=True)
            if r.stdout:
                print(r.stdout[:2000])
            if r.stderr:
                print("[stderr]", r.stderr[:1000])
            print("-" * 60)
            print(f"  Probe exit code: {r.returncode}")
        else:
            print("  (this tool has no safe dry-run mode — showing the command only)")

        print()
        print("To actually execute, re-run with --execute:")
        print(f"  sean artifact {args.feature} run {args.artifact} --execute")
        sys.exit(0)

    # --- 真正执行 ---
    print("=" * 60)
    print("EXECUTE — mutating external state")
    print("=" * 60)
    print(f"  Command: {' '.join(cmd)}")
    print("-" * 60)

    r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if r.stdout:
        print(r.stdout[:4000])
    if r.stderr:
        print("[stderr]", r.stderr[:2000])
    print("-" * 60)
    print(f"Exit code: {r.returncode}")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
