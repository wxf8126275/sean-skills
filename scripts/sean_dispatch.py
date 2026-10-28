#!/usr/bin/env python3
"""
sean_dispatch.py — 解析 sean plan，分组 dependency waves，生成子智能体任务描述。

用法:
  python sean_dispatch.py <plan_path> [--start N] [--format json|yaml|text]

输出:
  JSON/YAML/Text 格式的 wave 分组 + 每个 task 的 Task Context Package。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Task:
    id: int
    name: str
    depends_on: list[int] = field(default_factory=list)
    parallel_safe: bool = False
    files_create: list[str] = field(default_factory=list)
    files_modify: list[str] = field(default_factory=list)
    test_file: str = ""
    complexity: str = "low"
    acceptance: str = ""
    steps: list[str] = field(default_factory=list)


@dataclass
class Wave:
    number: int
    tasks: list[Task] = field(default_factory=list)
    parallel_safe_tasks: list[Task] = field(default_factory=list)
    serial_tasks: list[Task] = field(default_factory=list)


def parse_plan(plan_path: str) -> list[Task]:
    """Parse sean plan markdown into Task objects."""
    content = Path(plan_path).read_text(encoding="utf-8")
    tasks = {}

    # Parse Task Summary table for depends_on, complexity, parallel_safe
    # Format: | # | Task | Depends On | Complexity | Parallel Safe |
    summary_pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|"
    )
    for match in summary_pattern.finditer(content):
        task_id = int(match.group(1))
        task_name = match.group(2)
        dep_str = match.group(3).strip()
        complexity = match.group(4).strip().lower()
        parallel_safe = match.group(5).strip().lower() == "yes"

        depends_on = []
        if dep_str and dep_str != "—" and dep_str != "-":
            depends_on = [int(x.strip()) for x in dep_str.split(",") if x.strip().isdigit()]

        tasks[task_id] = Task(
            id=task_id,
            name=task_name,
            depends_on=depends_on,
            parallel_safe=parallel_safe,
            complexity=complexity,
        )

    # Parse Task Details sections for files, test, acceptance
    # Format: ### Task N: <name>
    detail_pattern = re.compile(
        r"###\s+Task\s+(\d+):\s*(\S+)\s*\n(.*?)(?=###\s+Task\s+\d+:|\Z)",
        re.DOTALL,
    )
    for match in detail_pattern.finditer(content):
        task_id = int(match.group(1))
        body = match.group(3)

        if task_id not in tasks:
            continue

        # Parse files_create
        fc_match = re.search(r"\*\*Creates\*\*:\s*(.+)", body)
        if fc_match:
            files_str = fc_match.group(1).strip()
            if files_str and files_str != "—":
                tasks[task_id].files_create = [f.strip().strip("`") for f in files_str.split(",")]

        # Parse files_modify
        fm_match = re.search(r"\*\*Modifies\*\*:\s*(.+)", body)
        if fm_match:
            files_str = fm_match.group(1).strip()
            if files_str and files_str != "—":
                tasks[task_id].files_modify = [f.strip().strip("`") for f in files_str.split(",")]

        # Parse test_file
        tf_match = re.search(r"\*\*Test\*\*:\s*(.+)", body)
        if tf_match:
            tasks[task_id].test_file = tf_match.group(1).strip().strip("`")

        # Parse acceptance
        ac_match = re.search(r"\*\*Acceptance\*\*:\s*(.+)", body)
        if ac_match:
            tasks[task_id].acceptance = ac_match.group(1).strip()

    return [tasks[k] for k in sorted(tasks.keys())]


def load_tasks_from_state(root: Path, feature: str) -> list[Task] | None:
    """从 state 的 features/<name>.json 读取结构化 tasks（优先于解析 plan.md）。"""
    f = root / "docs" / ".sean" / "features" / f"{feature}.json"
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    tasks = []
    for t in data.get("tasks") or []:
        if not isinstance(t, dict) or "id" not in t:
            continue
        try:
            task_id = int(t["id"])
        except (ValueError, TypeError):
            continue  # 非数字 id 无法参与 wave 分组，跳过
        depends = t.get("depends_on") or []
        if not isinstance(depends, (list, tuple)):
            depends = [depends] if depends else []
        tasks.append(Task(
            id=task_id,
            name=t.get("name", ""),
            depends_on=[int(x) for x in depends if str(x).isdigit()],
            parallel_safe=bool(t.get("parallel_safe")),
            files_create=list(t.get("files_create") or []),
            files_modify=list(t.get("files_modify") or []),
            test_file=t.get("test_file", "") or "",
            complexity=t.get("complexity", "low") or "low",
            acceptance=t.get("acceptance", "") or "",
        ))
    return tasks or None


def group_waves(tasks: list[Task], start_n: int = 1) -> list[Wave]:
    """Group tasks into dependency waves."""
    # Filter tasks from start_n onwards
    remaining = [t for t in tasks if t.id >= start_n]
    completed = {t.id for t in tasks if t.id < start_n}
    waves = []

    while remaining:
        # Find tasks whose dependencies are all satisfied
        wave_tasks = []
        for task in remaining:
            if all(dep in completed for dep in task.depends_on):
                wave_tasks.append(task)

        if not wave_tasks:
            # Circular dependency or missing dependency
            print(f"ERROR: Cannot resolve dependencies for tasks: {[t.id for t in remaining]}", file=sys.stderr)
            sys.exit(1)

        # Split into parallel_safe and serial
        parallel = [t for t in wave_tasks if t.parallel_safe]
        serial = [t for t in wave_tasks if not t.parallel_safe]

        wave = Wave(
            number=len(waves) + 1,
            tasks=wave_tasks,
            parallel_safe_tasks=parallel,
            serial_tasks=serial,
        )
        waves.append(wave)

        # Mark as completed
        for t in wave_tasks:
            completed.add(t.id)
        remaining = [t for t in remaining if t.id not in completed]

    return waves


def generate_context_package(task: Task, project_root: str, conventions_path: str, test_pattern_path: str) -> dict:
    """Generate Task Context Package for a sub-agent.

    conventions_path / test_pattern_path 只传路径不传全文——子智能体自行按需读取，
    避免每个子 agent 重复吞下同样的几 KB（与 cmd-run.md 的精简契约一致）。
    """
    return {
        "task_id": task.id,
        "task_name": task.name,
        "project_root": project_root,
        "conventions_path": conventions_path,
        "conventions_digest": "",   # ≤10 行关键约束，由主 agent 分发时补充
        "test_pattern_path": test_pattern_path,
        "files_create": task.files_create,
        "files_modify": task.files_modify,
        "test_file": task.test_file,
        "tdd_contract": [
            "先写失败测试，确认 RED",
            "写最小实现使测试 GREEN",
            "禁止修改测试文件",
            "Fix Loop 最多 3 次",
            "如果 3 次后仍 RED → 返回 status: failed",
        ],
        "output_format": {
            "status": "done|failed",
            "tests_total": 0,
            "tests_passed": 0,
            "fixes": 0,
            "files_modified": [],
            "report": "",
            "error_message": "",
        },
    }


def format_output(waves: list[Wave], project_root: str, conventions_path: str, test_pattern_path: str, fmt: str) -> str:
    """Format waves output."""
    if fmt == "json":
        output = []
        for wave in waves:
            wave_data = {
                "wave": wave.number,
                "tasks": [asdict(t) for t in wave.tasks],
                "parallel_safe_tasks": [t.id for t in wave.parallel_safe_tasks],
                "serial_tasks": [t.id for t in wave.serial_tasks],
                "context_packages": [
                    generate_context_package(t, project_root, conventions_path, test_pattern_path)
                    for t in wave.parallel_safe_tasks
                ],
            }
            output.append(wave_data)
        return json.dumps(output, indent=2, ensure_ascii=False)

    elif fmt == "yaml":
        lines = []
        for wave in waves:
            lines.append(f"wave {wave.number}:")
            lines.append(f"  tasks: {[t.id for t in wave.tasks]}")
            lines.append(f"  parallel_safe: {[t.id for t in wave.parallel_safe_tasks]}")
            lines.append(f"  serial: {[t.id for t in wave.serial_tasks]}")
            for t in wave.parallel_safe_tasks:
                lines.append(f"  task_{t.id}_context:")
                lines.append(f"    task_name: {t.name}")
                lines.append(f"    files_create: {t.files_create}")
                lines.append(f"    files_modify: {t.files_modify}")
                lines.append(f"    test_file: {t.test_file}")
        return "\n".join(lines)

    else:  # text
        lines = []
        for wave in waves:
            lines.append(f"=== Wave {wave.number} ===")
            lines.append(f"  All tasks: {[t.id for t in wave.tasks]}")
            lines.append(f"  Parallel safe: {[t.id for t in wave.parallel_safe_tasks]}")
            lines.append(f"  Serial: {[t.id for t in wave.serial_tasks]}")
            for t in wave.parallel_safe_tasks:
                lines.append(f"\n  --- Task {t.id}: {t.name} ---")
                lines.append(f"  Creates: {t.files_create}")
                lines.append(f"  Modifies: {t.files_modify}")
                lines.append(f"  Test: {t.test_file}")
                lines.append(f"  Acceptance: {t.acceptance}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sean plan dispatcher")
    parser.add_argument("plan_path", help="Path to plan markdown file")
    parser.add_argument("--start", type=int, default=1, help="Start task index")
    parser.add_argument("--format", choices=["json", "yaml", "text"], default="text", help="Output format")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--conventions", default="", help="Path to conventions.md")
    parser.add_argument("--test-pattern", default="", help="Path to existing test file for reference")
    parser.add_argument("--feature", default="", help="Feature 名；提供时优先读 state 结构化 tasks，plan 作 fallback")
    args = parser.parse_args()

    # conventions / test-pattern 只传路径，不读全文（子智能体按需读取）
    conventions_path = args.conventions or ""
    test_pattern_path = args.test_pattern or ""

    # 优先读 state 的结构化 tasks（权威数据源），缺失或解析失败才回退解析 plan.md
    tasks = load_tasks_from_state(Path(args.project_root).resolve(), args.feature) if args.feature else None
    if tasks is None:
        tasks = parse_plan(args.plan_path)
    if not tasks:
        print("ERROR: No tasks found in plan or state", file=sys.stderr)
        sys.exit(1)

    # Group waves
    waves = group_waves(tasks, args.start)

    # Output
    print(format_output(waves, args.project_root, conventions_path, test_pattern_path, args.format))


if __name__ == "__main__":
    main()
