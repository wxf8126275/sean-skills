#!/usr/bin/env python3
"""
sean_state.py — sean 状态存储引擎（增量写入 + 最小化 history）。

设计目标（Token 经济性）：
  1. AI 不写全量 JSON，只发 delta 指令，脚本负责合并落盘。
  2. state.json 只存摘要（<2KB），单个 feature 全量放 features/<name>.json，按需读取。
  3. history 只存「被改动顶层键的旧值」，不存 before/after 全量快照。
  4. 所有 get 默认输出摘要（≤30 行），禁止把整个 state 灌进上下文。

目录布局：
  docs/.sean/
  ├── state.json            # 摘要：active + 每个 feature 一行
  ├── features/<name>.json  # 完整 feature（tasks/findings/bugs/review）
  ├── active
  ├── .pending.json         # 累积的逆向补丁（snapshot 时转 history）
  └── history/
      ├── index.jsonl       # 一行一条事件
      └── <id>.json         # 该事件的逆向补丁（最小集）

用法：
  python3 sean_state.py init
  python3 sean_state.py get [feature] [--full] [--json]
  python3 sean_state.py active
  python3 sean_state.py list
  python3 sean_state.py set <feature> <key>=<json> [key2=...]
  python3 sean_state.py task-status <feature> <id> <status> [--tests-total N] [--tests-passed N] [--fixes N] [--report P]
  python3 sean_state.py feature-status <feature> <status> [--blocker TEXT]
  python3 sean_state.py add-task <feature> --json '<obj>'
  python3 sean_state.py add-bug <feature> --json '<obj>'
  python3 sean_state.py add-finding <feature> --json '<obj>'
  python3 sean_state.py snapshot <action> [feature] [--files-created a,b] [--files-modified c,d]
  python3 sean_state.py undo [n] [--with-files]
  python3 sean_state.py sync <feature>
  python3 sean_state.py export [feature]
  python3 sean_state.py migrate
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_VERSION = 5


# ---------------------------------------------------------------- 基础设施

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def find_root(start: Path) -> Path:
    """向上查找已有 docs/.sean，找不到则用 start。"""
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "docs" / ".sean").is_dir():
            return candidate
    return cur


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.dir = root / "docs" / ".sean"
        self.features_dir = self.dir / "features"
        self.history_dir = self.dir / "history"
        self.state_file = self.dir / "state.json"
        self.pending_file = self.dir / ".pending.json"
        self.index_file = self.history_dir / "index.jsonl"

    # -- state（摘要）

    def ensure(self, create: bool = True) -> None:
        if not self.dir.is_dir():
            if not create:
                fail("未找到 docs/.sean。请先运行: python3 sean_state.py init")
            self.features_dir.mkdir(parents=True, exist_ok=True)
            self.history_dir.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict:
        self.ensure(create=False)
        if not self.state_file.exists():
            return {"version": STATE_VERSION, "active": None, "features": {}}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"state.json 解析失败（可能写入中断）：{exc}。可运行 sync 或从 history 恢复。")
        if self._needs_migration(data):
            data = self.migrate(data)
            self.save_state(data)
        data.setdefault("version", STATE_VERSION)
        data.setdefault("features", {})
        data.setdefault("active", None)
        return data

    def save_state(self, state: dict) -> None:
        self.ensure()
        write_json(self.state_file, state)

    # -- feature（明细）

    def feature_file(self, name: str) -> Path:
        return self.features_dir / f"{name}.json"

    def load_feature(self, name: str) -> dict:
        path = self.feature_file(name)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        state = self.load_state()
        summary = state["features"].get(name)
        if summary is None:
            fail(f"功能 {name} 不存在。现有: {', '.join(state['features']) or '(空)'}")
        # 兼容：早期版本把 feature 明细直接写在 state.json 里
        if any(k in summary for k in ("tasks", "findings", "bugs", "status")):
            detail = {k: v for k, v in summary.items() if k in DETAIL_KEYS}
            if detail:
                write_json(path, detail)
                return detail
        return {"name": name}

    def save_feature(self, name: str, feature: dict, state: dict) -> None:
        """写盘并累积逆向补丁（只记被改动顶层键的旧值）。"""
        path = self.feature_file(name)
        old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

        feature.setdefault("name", name)
        feature["updated_at"] = now_iso()
        # 先做派生字段计算（targets 状态、tests 汇总），再 diff，保证补丁完整
        self.touch_summary(state, name, feature)

        restore, absent, lists_patch = diff_top_level(old, feature)
        if restore or absent or lists_patch:
            # 对变化的列表字段，传本次 save 前的完整旧列表；pending 用 setdefault 保留操作开始前的那份
            old_lists = {k: old[k] for k in lists_patch}
            self.pending_add(name, restore, absent, old_lists, existed=path.exists())

        write_json(path, feature)
        self.save_state(state)

    def touch_summary(self, state: dict, name: str, feature: dict) -> None:
        tasks = feature.get("tasks") or []
        done = sum(1 for t in tasks if t.get("status") == "done")
        # 直接求和/计数，不做 or 回退——否则值归零（如 undo 清空 tasks）时不会更新
        feature["tests_passed"] = sum(t.get("tests_passed") or 0 for t in tasks)
        feature["tasks_total"] = len(tasks)
        summary = {
            "name": name,
            "status": feature.get("status", "DRAFT"),
            "current_task": feature.get("current_task", 0),
            "tasks_total": feature["tasks_total"],
            "tasks_done": done,
            "tests_passed": feature["tests_passed"],
            "open_bugs": sum(1 for b in (feature.get("bugs") or []) if b.get("status") in ("open", "fixing")),
            "open_findings": sum(1 for f in (feature.get("findings") or []) if f.get("status") == "open"),
            "blocked_reason": feature.get("blocked_reason"),
            "updated_at": feature.get("updated_at"),
        }
        # 多端模式（可选）：targets 状态由其 tasks 自动推导，避免人工不一致
        if feature.get("targets"):
            feature["targets"] = derive_target_states(feature)
            summary["targets"] = feature["targets"]
            summary["primary_target"] = feature.get("primary_target")
            summary["targets_done"] = sum(1 for v in feature["targets"].values() if v == "done")
            summary["targets_total"] = len(feature["targets"])
        state["features"][name] = summary

    # -- pending 逆向补丁

    def load_pending(self) -> dict:
        if self.pending_file.exists():
            return json.loads(self.pending_file.read_text(encoding="utf-8"))
        return {"entries": []}

    def pending_add(self, name: str, restore: dict, absent: list, lists: dict, existed: bool) -> None:
        pending = self.load_pending()
        entry = next((e for e in pending["entries"] if e["feature"] == name), None)
        if entry is None:
            entry = {"feature": name, "existed": existed, "keys": {}, "absent": [], "lists": {}}
            pending["entries"].append(entry)
        # 保留最早的旧值，不被后续操作覆盖
        for k, v in restore.items():
            entry["keys"].setdefault(k, v)
        for k in absent:
            if k not in entry["absent"]:
                entry["absent"].append(k)
        # 列表字段：保留操作开始前的完整旧列表（history_add 时再转成元素级 diff）
        for k, old_list in lists.items():
            entry["lists"].setdefault(k, old_list)
        write_json(self.pending_file, pending)

    def pending_clear(self) -> None:
        if self.pending_file.exists():
            self.pending_file.unlink()

    # -- history

    def history_add(self, action: str, feature: str | None, files_created: list,
                    files_modified: list) -> str:
        pending = self.load_pending()
        entries = pending.get("entries", [])
        if not entries and not files_created and not files_modified:
            return ""
        # 列表字段：把 pending 里的「操作开始前完整旧列表」转成元素级 diff（相对操作结束后的当前状态）
        for entry in entries:
            if entry.get("lists"):
                current = self._load_feature_current(entry["feature"])
                patches = {}
                for key, old_list in entry["lists"].items():
                    patch = diff_list(old_list, current.get(key) or [])
                    if patch:
                        patches[key] = patch
                if patches:
                    entry["lists"] = patches
                else:
                    entry.pop("lists", None)
        event_id = f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{action}"
        record = {
            "id": event_id,
            "timestamp": now_iso(),
            "action": action,
            "feature": feature,
            "git_head": git_head(self.root),
            "restore": entries,
            "files_created": files_created,
            "files_modified": files_modified,
            "undone": False,
        }
        self.ensure()
        write_json(self.history_dir / f"{event_id}.json", record)
        with self.index_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "id": event_id,
                "ts": record["timestamp"],
                "action": action,
                "feature": feature,
                "undone": False,
            }, ensure_ascii=False) + "\n")
        self.pending_clear()
        prune_history(self)
        return event_id

    def _load_feature_current(self, name: str) -> dict:
        """读取 feature 当前磁盘状态（history 落盘时用于把旧列表 diff 成元素级补丁）。"""
        path = self.feature_file(name)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def history_index(self) -> list:
        if not self.index_file.exists():
            return []
        rows = []
        for line in self.index_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    # -- 迁移

    @staticmethod
    def _needs_migration(state: dict) -> bool:
        for feat in (state.get("features") or {}).values():
            if isinstance(feat, dict) and any(k in feat for k in ("tasks", "findings", "bugs")):
                return True
        return False

    def migrate(self, state: dict) -> dict:
        self.ensure()
        for name, feat in list((state.get("features") or {}).items()):
            if not isinstance(feat, dict):
                continue
            if not any(k in feat for k in ("tasks", "findings", "bugs", "review")):
                continue
            detail = {k: v for k, v in feat.items() if k in DETAIL_KEYS or k in SUMMARY_KEYS}
            self.features_dir.mkdir(parents=True, exist_ok=True)
            write_json(self.feature_file(name), detail)
            self.touch_summary(state, name, detail)
        state["version"] = STATE_VERSION
        info("已迁移：feature 明细拆分到 docs/.sean/features/")
        return state


DETAIL_KEYS = {
    "name", "requirement", "plan", "status", "current_task", "tasks_total", "tasks",
    "tests_passed", "tests_failed", "tests_fixed", "started_at", "completed_at",
    "blocked_reason", "review", "findings", "bugs", "artifacts", "updated_at",
}
SUMMARY_KEYS = {"name", "status", "updated_at"}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def task_target(feature: dict, task: dict) -> str:
    """未标 target 的 task 归属于 primary_target（单端项目无该键 → None）。"""
    return task.get("target") or feature.get("primary_target") or ""


def derive_target_states(feature: dict) -> dict:
    """{target: done|failed|in_progress|pending}，由 tasks 推导。"""
    declared = feature.get("targets") or {}
    if isinstance(declared, list):
        declared = {t: "pending" for t in declared}
    states = {}
    for target in declared:
        owned = [t for t in (feature.get("tasks") or []) if task_target(feature, t) == target]
        if not owned:
            states[target] = "pending"
        elif any(t.get("status") == "failed" for t in owned):
            states[target] = "failed"
        elif all(t.get("status") == "done" for t in owned):
            states[target] = "done"
        elif any(t.get("status") == "in_progress" for t in owned):
            states[target] = "in_progress"
        else:
            states[target] = "pending"
    return states


# 按元素 id 做增量 diff 的列表字段（tasks / findings / bugs）
LIST_KEYS = {"tasks", "findings", "bugs"}


def diff_list(old_items: list, new_items: list) -> dict:
    """按元素 id 做增量 diff，返回 {changed, added, removed}（无差异返回 {}）。

    changed / removed 存旧元素，added 存 id。undo 时据此还原，避免整列快照。
    所有 id 统一转字符串作为 dict key——JSON 序列化会把 int key 转字符串，保持一致。
    """
    old_by_id = {str(i.get("id")): i for i in old_items if isinstance(i, dict)}
    new_by_id = {str(i.get("id")): i for i in new_items if isinstance(i, dict)}
    changed = {k: old_by_id[k] for k in set(old_by_id) & set(new_by_id)
               if old_by_id[k] != new_by_id[k]}
    added = [k for k in new_by_id if k not in old_by_id]
    removed = [old_by_id[k] for k in old_by_id if k not in new_by_id]
    if not changed and not added and not removed:
        return {}
    return {"changed": changed, "added": added, "removed": removed}


def diff_top_level(old: dict, new: dict) -> tuple[dict, list, dict]:
    """返回 (restore, absent, lists)。

    restore/absent：标量与非列表顶层键的旧值 / 新增键。
    lists：列表字段（LIST_KEYS）的元素级 diff，形如 {key: {changed, added, removed}}。
    """
    restore, absent, lists = {}, [], {}
    for key in set(old) | set(new):
        if key == "updated_at":
            # 派生字段：每次 save 必更新，记入逆向补丁只是噪音，且 undo 后会被重新写入
            continue
        if key in LIST_KEYS and isinstance(old.get(key), list) and isinstance(new.get(key), list):
            patch = diff_list(old[key], new[key])
            if patch:
                lists[key] = patch
            continue
        if key in old and key in new:
            if old[key] != new[key]:
                restore[key] = old[key]
        elif key in old:
            restore[key] = old[key]
        else:
            absent.append(key)
    return restore, absent, lists


def restore_list_patch(items: list, patch: dict) -> list:
    """按元素级补丁还原列表（changed/added/removed）。id 统一按字符串键处理。"""
    by_id = {str(i.get("id")): i for i in items if isinstance(i, dict)}
    for k, old_item in patch.get("changed", {}).items():
        by_id[str(k)] = old_item
    for k in patch.get("added", []):
        by_id.pop(str(k), None)
    for old_item in patch.get("removed", []):
        by_id[str(old_item.get("id"))] = old_item
    return list(by_id.values())


def git_head(root: Path) -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                             capture_output=True, text=True, timeout=5)
        if out.returncode != 0:
            return None
        return out.stdout.strip() or None
    except Exception:
        return None


def prune_history(store: Store, keep: int = 200) -> None:
    """history 只保留最近 N 条，避免无限增长。"""
    rows = store.history_index()
    if len(rows) <= keep:
        return
    drop = rows[: len(rows) - keep]
    for row in drop:
        f = store.history_dir / f"{row['id']}.json"
        if f.exists():
            f.unlink()
    keep_rows = rows[len(rows) - keep:]
    store.index_file.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in keep_rows) + "\n",
        encoding="utf-8",
    )


def info(msg: str) -> None:
    print(msg)


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


# ---------------------------------------------------------------- 命令

def cmd_init(store: Store, args) -> None:
    store.ensure()
    state = {"version": STATE_VERSION, "active": None, "features": {}}
    if store.state_file.exists():
        state = store.load_state()
    store.save_state(state)
    store.history_dir.mkdir(parents=True, exist_ok=True)
    info(f"initialized {store.dir} (schema v{STATE_VERSION})")


def cmd_get(store: Store, args) -> None:
    state = store.load_state()
    name = args.feature or state.get("active")
    if not name:
        fail("未指定 feature，且没有 active。")
    if args.full:
        feature = store.load_feature(name)
        if args.json:
            print(json.dumps(feature, ensure_ascii=False, indent=2))
            return
        summary = state["features"].get(name, {})
        head = (f"# {name}  {feature.get('status','?')}  "
                f"{summary.get('tasks_done',0)}/{summary.get('tasks_total',0)} tasks")
        targets = feature.get("targets") or {}
        if targets:
            head += "  [" + " · ".join(f"{t} {s}" for t, s in targets.items()) + "]"
        print(head)

        def render(task: dict, indent: str) -> None:
            mark = {"done": "+", "failed": "x", "in_progress": "~", "pending": "."}.get(task.get("status"), "?")
            print(f"{indent}[{mark}] {task.get('id')} {task.get('name','')} "
                  f"tests {task.get('tests_passed',0)}/{task.get('tests_total',0)}")

        if targets:
            for target in targets:
                mine = [t for t in (feature.get("tasks") or []) if task_target(feature, t) == target]
                if not mine:
                    print(f"  {target}: (尚未拆解 task)")
                    continue
                print(f"  {target}")
                for task in mine:
                    render(task, "    ")
        else:
            for task in feature.get("tasks") or []:
                render(task, "  ")
        for bug in feature.get("bugs") or []:
            affected = bug.get("affected_targets")
            scope = f" [{','.join(affected)}]" if affected else ""
            print(f"  bug {bug.get('id')} {bug.get('status')}{scope} {bug.get('symptom','')[:40]}")
        parity = feature.get("parity")
        if parity:
            print(f"  parity: {parity.get('status')} {parity.get('gaps') or ''}".rstrip())
        return
    # 默认摘要：单行
    print(summary_line(name, state["features"].get(name, {})))


def summary_line(name: str, s: dict) -> str:
    if not s:
        return f"{name}  (无摘要)"
    done = s.get("tasks_done", 0)
    total = s.get("tasks_total", 0)
    extra = []
    if s.get("open_bugs"):
        extra.append(f"{s['open_bugs']} bug open")
    if s.get("open_findings"):
        extra.append(f"{s['open_findings']} finding open")
    tail = ("  " + ", ".join(extra)) if extra else ""
    return f"{name}  {s.get('status')}  {done}/{total} tasks  tests:{s.get('tests_passed',0)}{tail}"


def cmd_active(store: Store, args) -> None:
    state = store.load_state()
    print(state.get("active") or "")


def cmd_list(store: Store, args) -> None:
    state = store.load_state()
    feats = state.get("features") or {}
    if not feats:
        info("(无 feature)")
        return
    rows = sorted(feats.values(), key=lambda x: x.get("updated_at") or "", reverse=True)
    for row in rows:
        mark = "*" if row["name"] == state.get("active") else " "
        print(f"{mark} {summary_line(row['name'], row)}")


def _apply_set(feature: dict, assignments: list) -> None:
    for item in assignments:
        if "=" not in item:
            fail(f"无法解析赋值 '{item}'，应为 key=<json>")
        key, raw = item.split("=", 1)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        feature[key] = value


def new_feature(name: str, requirement: str | None = None, plan: str | None = None) -> dict:
    return {
        "name": name,
        "requirement": requirement,
        "plan": plan,
        "status": "DRAFT",
        "current_task": 0,
        "tasks_total": 0,
        "tasks": [],
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_fixed": 0,
        "started_at": now_iso(),
        "completed_at": None,
        "blocked_reason": None,
        "review": {},
        "findings": [],
        "bugs": [],
    }


def set_active(store: Store, state: dict, name: str) -> None:
    state["active"] = name
    store.save_state(state)
    (store.dir / "active").write_text(name + "\n", encoding="utf-8")


def cmd_create(store: Store, args) -> None:
    state = store.load_state()
    if args.feature in state["features"] and not args.force:
        fail(f"功能 {args.feature} 已存在（加 --force 覆盖）")
    feature = new_feature(args.feature, args.requirement, args.plan)
    if args.status:
        feature["status"] = args.status
    store.save_feature(args.feature, feature, state)
    if args.set_active or state.get("active") is None:
        set_active(store, state, args.feature)
    info(f"created {args.feature}")


MARKERS = {
    "android": ["android", "app/src/main", "build.gradle", "build.gradle.kts", "settings.gradle",
                "settings.gradle.kts", "AndroidManifest.xml"],
    "ios": ["ios", "Podfile", "*.xcodeproj", "*.xcworkspace", "Package.swift"],
    "harmony": ["harmony", "harmonyos", "oh-package.json5", "build-profile.json5", "module.json5",
                "entry/src/main"],
}


def _has_marker(root: Path, patterns: list) -> bool:
    for pat in patterns:
        candidate = root / pat
        if candidate.exists():
            return True
        if "*" in pat and any(root.glob(pat)):
            return True
    return False


def cmd_detect_targets(store: Store, args) -> None:
    """探测项目是否为多端结构；尊重 conventions.md 中已记录的 multi_target: off。"""
    conventions = store.root / "docs" / "team" / "conventions.md"
    if conventions.exists():
        text = conventions.read_text(encoding="utf-8", errors="replace")
        if re.search(r"multi_target\s*:\s*off", text, re.IGNORECASE):
            info("multi_target: off  已记录在 conventions.md，不再询问")
            return
    found = [name for name, pats in MARKERS.items() if _has_marker(store.root, pats)]
    if len(found) >= 2:
        info(f"multi_target: detected [{', '.join(found)}]  → 建议询问是否需要多端对齐")
        if args.json:
            print(json.dumps({"detected": found, "suggest_ask": True}, ensure_ascii=False))
    else:
        info(f"multi_target: none  (检出: {', '.join(found) or '—'}) → 按单端处理，无需询问")


def cmd_targets(store: Store, args) -> None:
    state = store.load_state()
    feature = store.load_feature(args.feature)
    if args.action == "list" or not args.action:
        targets = feature.get("targets") or {}
        if not targets:
            info(f"{args.feature}: 单端模式（未声明 targets）")
            return
        print(f"{args.feature}  primary={feature.get('primary_target') or '-'}")
        for target, status in targets.items():
            count = sum(1 for t in (feature.get("tasks") or []) if task_target(feature, t) == target)
            print(f"  {target:10s} {status:12s} {count} task(s)")
        return
    if args.action != "add":
        fail(f"未知 action: {args.action}（支持 add|list）")
    names = [t.strip() for t in (args.target_list or "").split(",") if t.strip()]
    if not names:
        fail("请给出 targets，例如: targets add <feature> android,ios,harmony")
    primary = args.primary or feature.get("primary_target") or (feature.get("targets") and next(iter(feature["targets"]))) or names[0]
    if primary not in names:
        names.insert(0, primary)
    existing = set((feature.get("targets") or {}).keys())
    added = [n for n in names if n not in existing]
    # 已有 tasks 未标 target → 归到 primary，保持历史不变
    for task in feature.get("tasks") or []:
        if not task.get("target"):
            task["target"] = primary
    feature["primary_target"] = primary
    feature["targets"] = derive_target_states({**feature, "targets": {n: "pending" for n in names}})
    if args.contract:
        feature["contract"] = args.contract
    store.save_feature(args.feature, feature, state)
    info(f"targets -> {', '.join(feature['targets'])} (primary={primary})")
    if added:
        info(f"新增: {', '.join(added)}；为这些端拆解 task 后状态会自动更新")


def cmd_switch(store: Store, args) -> None:
    state = store.load_state()
    if args.feature not in state["features"]:
        fail(f"功能 {args.feature} 不存在。现有: {', '.join(state['features']) or '(空)'}")
    set_active(store, state, args.feature)
    info(f"active -> {args.feature} ({summary_line(args.feature, state['features'][args.feature])})")


def cmd_set(store: Store, args) -> None:
    state = store.load_state()
    feature = store.load_feature(args.feature)
    _apply_set(feature, args.assignments)
    store.save_feature(args.feature, feature, state)
    info(summary_line(args.feature, state["features"][args.feature]))


def cmd_task_status(store: Store, args) -> None:
    state = store.load_state()
    feature = store.load_feature(args.feature)
    tasks = feature.setdefault("tasks", [])
    target = next((t for t in tasks if str(t.get("id")) == str(args.task_id)), None)
    if target is None:
        fail(f"task {args.task_id} 不存在（现有: {[t.get('id') for t in tasks]}）")
    target["status"] = args.status
    if args.tests_total is not None:
        target["tests_total"] = args.tests_total
    if args.tests_passed is not None:
        target["tests_passed"] = args.tests_passed
    if args.fixes is not None:
        target["fixes"] = args.fixes
    if args.report:
        target["report"] = args.report
    if args.evidence:
        target["evidence"] = args.evidence
    if args.status == "in_progress":
        feature["current_task"] = target.get("id")
    if args.model:
        target["implemented_by"] = args.model
    if args.status == "done":
        feature["tasks_total"] = len(tasks)
        if feature.get("targets"):
            # 多端：所有 target 都完成才算整体进入收尾（DONE 仍需显式设置）
            all_done = all(s == "done" for s in derive_target_states(feature).values())
        else:
            all_done = all(t.get("status") == "done" for t in tasks)
        if all_done and feature.get("status") not in ("DONE",):
            feature["status"] = "IN_PROGRESS"
    store.save_feature(args.feature, feature, state)
    info(summary_line(args.feature, state["features"][args.feature]))


def cmd_feature_status(store: Store, args) -> None:
    state = store.load_state()
    feature = store.load_feature(args.feature)
    feature["status"] = args.status
    if args.status == "DONE":
        feature["completed_at"] = now_iso()
        feature["blocked_reason"] = None
    if args.blocker is not None:
        feature["blocked_reason"] = args.blocker
    store.save_feature(args.feature, feature, state)
    info(summary_line(args.feature, state["features"][args.feature]))


def _add_item(store: Store, name: str, key: str, payload: str, id_prefix: str) -> None:
    state = store.load_state()
    if store.feature_file(name).exists() or name in state["features"]:
        feature = store.load_feature(name)
    else:
        feature = new_feature(name)
    items = feature.setdefault(key, [])
    try:
        item = json.loads(payload)
    except json.JSONDecodeError as exc:
        fail(f"--json 解析失败: {exc}")
    if "id" not in item:
        item["id"] = f"{id_prefix}{len(items) + 1:03d}"
    item.setdefault("created_at", now_iso())
    items.append(item)
    store.save_feature(name, feature, state)
    info(f"{key[:-1]} {item['id']} added ({summary_line(name, state['features'][name])})")


def cmd_add_task(store: Store, args) -> None:
    _add_item(store, args.feature, "tasks", args.json, "T")


def cmd_add_bug(store: Store, args) -> None:
    _add_item(store, args.feature, "bugs", args.json, "B")


def cmd_add_finding(store: Store, args) -> None:
    _add_item(store, args.feature, "findings", args.json, "F")


def cmd_snapshot(store: Store, args) -> None:
    created = split_csv(args.files_created)
    modified = split_csv(args.files_modified)
    pending = store.load_pending()
    scope = []
    for entry in pending.get("entries", []):
        changed = list(entry.get("keys", {})) + entry.get("absent", [])
        scope.append(f"{entry['feature']}({len(changed)} keys)")
    event = store.history_add(args.action, args.feature or None, created, modified)
    if not event:
        info("history: (无变更，跳过)")
        return
    detail = f" [{', '.join(scope)}]" if scope else ""
    info(f"history: {event}{detail}")
    if len(scope) > 1:
        info("提示：本次事件跨越多个 feature，建议每个命令结束各 snapshot 一次，以便 undo 精确回退。")


def split_csv(raw: str | None) -> list:
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def cmd_undo(store: Store, args) -> None:
    rows = store.history_index()
    live = [r for r in rows if not r.get("undone")]
    if not live:
        fail("没有可撤销的操作")
    targets = live[-args.steps:] if args.steps > 0 else live[-1:]
    state = store.load_state()
    file_actions = []
    for row in reversed(targets):
        record_path = store.history_dir / f"{row['id']}.json"
        if not record_path.exists():
            fail(f"history 记录缺失: {record_path}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        for entry in record.get("restore", []):
            name = entry["feature"]
            feature = store.load_feature(name) if store.feature_file(name).exists() else {}
            for key, value in entry.get("keys", {}).items():
                feature[key] = value
            for key in entry.get("absent", []):
                feature.pop(key, None)
            # 列表字段：按元素级补丁还原（新格式）；旧记录里 keys 中仍是整列快照，走上面的整体赋值
            for key, patch in entry.get("lists", {}).items():
                feature[key] = restore_list_patch(feature.get(key) or [], patch)
            # updated_at / name 由 save_feature 自动维护，不参与「是否已清空」判定
            meaningful = {k: v for k, v in feature.items() if k not in ("updated_at", "name")}
            if not meaningful and not entry.get("existed"):
                fp = store.feature_file(name)
                if fp.exists():
                    fp.unlink()
                state["features"].pop(name, None)
                store.save_state(state)
            else:
                store.save_feature(name, feature, state)
                # undo 本身不应产生新的逆向补丁
                store.pending_clear()
        for path in record.get("files_created", []):
            file_actions.append(("delete", path))
        for path in record.get("files_modified", []):
            file_actions.append(("git-restore", path))
        record["undone"] = True
        write_json(record_path, record)
        row["undone"] = True
    store.index_file.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    info(f"已撤销 {len(targets)} 步: state 已还原")
    if file_actions:
        if args.with_files:
            for kind, path in file_actions:
                resolve = (store.root / path).resolve()
                # 防路径穿越：目标必须仍在项目根内
                if store.root.resolve() not in resolve.parents:
                    print(f"  跳过项目外路径: {path}")
                    continue
                if kind == "delete":
                    if resolve.exists():
                        resolve.unlink()
                        info(f"  deleted {path}")
                else:  # git-restore
                    subprocess.run(["git", "checkout", "--", path], cwd=store.root,
                                   capture_output=True, text=True)
                    info(f"  git restored {path}")
        else:
            print("文件操作（如需执行加 --with-files）：")
            for kind, path in file_actions:
                cmd = f"rm {path}" if kind == "delete" else f"git checkout -- {path}"
                print(f"  {cmd}")


def cmd_sync(store: Store, args) -> None:
    """从 test-reports 重建 task 状态（不重建产物状态，产物一致性用 sean artifact check）。"""
    state = store.load_state()
    name = args.feature
    feature = store.load_feature(name)
    reports_root = store.root / "docs" / "test-reports"
    changed = []
    if reports_root.is_dir():
        for feat_dir in reports_root.iterdir():
            if not feat_dir.is_dir() or not feat_dir.name.endswith(f"-{name}"):
                continue
            for report in sorted(feat_dir.glob("task-*.md")):
                text = report.read_text(encoding="utf-8", errors="replace")
                match = re.search(r"\*\*Status\*\*:\s*(\w+)", text) or re.search(r"Status:\s*(\w+)", text)
                if not match:
                    continue
                verdict = match.group(1).lower()
                num = re.search(r"task-(\d+)", report.name)
                if not num:
                    continue
                task_id = int(num.group(1))
                task = next((t for t in feature.get("tasks", []) if t.get("id") == task_id), None)
                if task is None:
                    task = {"id": task_id, "name": report.stem}
                    feature.setdefault("tasks", []).append(task)
                new_status = "done" if verdict in ("pass", "fixed", "green") else "failed"
                if task.get("status") != new_status:
                    task["status"] = new_status
                    changed.append(f"task {task_id} -> {new_status}")
                task["report"] = str(report.relative_to(store.root))
    if changed:
        statuses = {t.get("status") for t in feature.get("tasks", [])}
        if "failed" in statuses:
            feature["status"] = "BLOCKED" if feature.get("status") != "DONE" else "IN_PROGRESS"
        elif statuses == {"done"} and feature.get("status") not in ("DONE",):
            feature["status"] = "IN_PROGRESS"
        store.save_feature(name, feature, state)
        info("rebuild:")
        for line in changed:
            print(f"  {line}")
    else:
        info("状态已一致，无改动")
    info(summary_line(name, state["features"][name]))


def cmd_export(store: Store, args) -> None:
    state = store.load_state()
    if args.feature:
        payload = store.load_feature(args.feature)
    else:
        payload = {"active": state.get("active"), "features": {}}
        for name in state.get("features", {}):
            payload["features"][name] = store.load_feature(name)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_migrate(store: Store, args) -> None:
    store.ensure()
    state = store.load_state()
    store.save_state(state)
    info("migrate done")


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sean_state.py", description="sean 状态存储引擎")
    p.add_argument("--project-root", default=".", help="项目根目录（默认 cwd，自动向上查找 docs/.sean）")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="初始化 docs/.sean")
    sub.add_parser("migrate", help="把旧版全量 state.json 拆分为 features/")
    sub.add_parser("list", help="列出所有 feature 摘要")
    sub.add_parser("active", help="打印 active feature")

    c = sub.add_parser("create", help="创建 feature 条目")
    c.add_argument("feature")
    c.add_argument("--requirement")
    c.add_argument("--plan")
    c.add_argument("--status")
    c.add_argument("--set-active", action="store_true")
    c.add_argument("--force", action="store_true")

    sw = sub.add_parser("switch", help="切换 active feature")
    sw.add_argument("feature")

    # 多端支持（可选，单端项目不使用）
    tg = sub.add_parser("targets", help="多端 targets 管理（add|list）")
    tg.add_argument("action", choices=["add", "list"])
    tg.add_argument("feature")
    tg.add_argument("target_list", nargs="?", help="逗号分隔，如 android,ios,harmony")
    tg.add_argument("--primary", help="主端（未标 target 的 task 归属）")
    tg.add_argument("--contract", help="契约文件路径")

    dt = sub.add_parser("detect-targets", help="探测项目是否为多端结构")
    dt.add_argument("--json", action="store_true")

    g = sub.add_parser("get", help="读取 feature（默认单行摘要）")
    g.add_argument("feature", nargs="?")
    g.add_argument("--full", action="store_true", help="输出任务级明细（仍不含完整 JSON）")
    g.add_argument("--json", action="store_true", help="与 --full 联用时输出完整 JSON")

    s = sub.add_parser("set", help="设置顶层字段（值按 JSON 解析）")
    s.add_argument("feature")
    s.add_argument("assignments", nargs="+", metavar="key=value")

    t = sub.add_parser("task-status", help="更新任务状态")
    t.add_argument("feature")
    t.add_argument("task_id")
    t.add_argument("status", choices=["pending", "in_progress", "done", "failed"])
    t.add_argument("--tests-total", type=int)
    t.add_argument("--tests-passed", type=int)
    t.add_argument("--fixes", type=int)
    t.add_argument("--report")
    t.add_argument("--evidence")
    t.add_argument("--model")

    f = sub.add_parser("feature-status", help="更新 feature 状态")
    f.add_argument("feature")
    f.add_argument("status", choices=["DRAFT", "PLANNED", "IN_PROGRESS", "DONE", "BLOCKED", "INTEGRATION_FAIL"])
    f.add_argument("--blocker")

    for name, prefix in (("add-task", "T"), ("add-bug", "B"), ("add-finding", "F")):
        a = sub.add_parser(name, help=f"追加 {name.split('-')[1]}")
        a.add_argument("feature")
        a.add_argument("--json", required=True)

    sn = sub.add_parser("snapshot", help="把累积变更写成 history 事件")
    sn.add_argument("action", choices=["start", "plan", "run", "task", "fix", "bug", "artifact", "review", "handoff"])
    sn.add_argument("feature", nargs="?")
    sn.add_argument("--files-created")
    sn.add_argument("--files-modified")

    u = sub.add_parser("undo", help="撤销最近 N 步")
    u.add_argument("steps", nargs="?", type=int, default=1)
    u.add_argument("--with-files", action="store_true", help="同时删除/还原文件")

    sy = sub.add_parser("sync", help="从 test-reports 重建状态")
    sy.add_argument("feature")

    e = sub.add_parser("export", help="导出可读 JSON（交接/人类审查用）")
    e.add_argument("feature", nargs="?")

    return p


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    store = Store(find_root(Path(args.project_root)))
    handlers = {
        "init": cmd_init,
        "migrate": cmd_migrate,
        "list": cmd_list,
        "active": cmd_active,
        "create": cmd_create,
        "switch": cmd_switch,
        "targets": cmd_targets,
        "detect-targets": cmd_detect_targets,
        "get": cmd_get,
        "set": cmd_set,
        "task-status": cmd_task_status,
        "feature-status": cmd_feature_status,
        "add-task": cmd_add_task,
        "add-bug": cmd_add_bug,
        "add-finding": cmd_add_finding,
        "snapshot": cmd_snapshot,
        "undo": cmd_undo,
        "sync": cmd_sync,
        "export": cmd_export,
    }
    handlers[args.command](store, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
