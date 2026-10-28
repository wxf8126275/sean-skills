#!/usr/bin/env python3
"""sean_state.py 的元素级 diff 与 undo 还原逻辑单测。

运行：python3 tests/test_sean_state.py
"""

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sean_state  # noqa: E402


class TestDiffList(unittest.TestCase):
    def test_changed(self):
        old = [{"id": 1, "status": "pending"}, {"id": 2, "status": "done"}]
        new = [{"id": 1, "status": "done"}, {"id": 2, "status": "done"}]
        patch = sean_state.diff_list(old, new)
        self.assertEqual(patch["changed"], {"1": {"id": 1, "status": "pending"}})
        self.assertEqual(patch["added"], [])
        self.assertEqual(patch["removed"], [])

    def test_added_and_removed(self):
        old = [{"id": 1, "status": "done"}]
        new = [{"id": 2, "status": "done"}]
        patch = sean_state.diff_list(old, new)
        self.assertEqual(patch["changed"], {})
        self.assertEqual(patch["added"], ["2"])
        self.assertEqual(patch["removed"], [{"id": 1, "status": "done"}])

    def test_no_diff(self):
        old = [{"id": 1, "status": "done"}]
        new = [{"id": 1, "status": "done"}]
        self.assertEqual(sean_state.diff_list(old, new), {})


class TestDiffTopLevel(unittest.TestCase):
    def test_tasks_go_to_lists_not_restore(self):
        old = {"tasks": [{"id": 1, "status": "pending"}], "status": "PLANNED"}
        new = {"tasks": [{"id": 1, "status": "done"}], "status": "IN_PROGRESS"}
        restore, absent, lists = sean_state.diff_top_level(old, new)
        self.assertNotIn("tasks", restore)
        self.assertIn("tasks", lists)
        self.assertEqual(restore["status"], "PLANNED")

    def test_updated_at_excluded(self):
        old = {"tasks": [], "updated_at": "2026-01-01T00:00:00"}
        new = {"tasks": [], "updated_at": "2026-01-02T00:00:00"}
        restore, absent, lists = sean_state.diff_top_level(old, new)
        self.assertNotIn("updated_at", restore)
        self.assertNotIn("updated_at", absent)


class TestRestoreListPatch(unittest.TestCase):
    def test_restore_changed(self):
        items = [{"id": 1, "status": "done"}]
        patch = {"changed": {1: {"id": 1, "status": "pending"}}, "added": [], "removed": []}
        result = sean_state.restore_list_patch(items, patch)
        self.assertEqual(result, [{"id": 1, "status": "pending"}])

    def test_restore_added_and_removed(self):
        items = [{"id": 2, "status": "done"}]
        patch = {"changed": {}, "added": [2], "removed": [{"id": 1, "status": "done"}]}
        result = sean_state.restore_list_patch(items, patch)
        self.assertEqual(result, [{"id": 1, "status": "done"}])


class TestUndoEndToEnd(unittest.TestCase):
    @staticmethod
    def _args(**kw):
        ns = argparse.Namespace(steps=1, with_files=False)
        for k, v in kw.items():
            setattr(ns, k, v)
        return ns

    def test_undo_restores_added_tasks(self):
        """一次操作内多次 add-task，history 存元素级 diff，undo 精确还原为空。"""
        with tempfile.TemporaryDirectory() as tmp:
            store = sean_state.Store(Path(tmp))
            store.ensure()
            state = store.load_state()
            feature = sean_state.new_feature("demo")
            store.save_feature("demo", feature, state)
            feature = store.load_feature("demo")
            feature.setdefault("tasks", []).append({"id": 1, "name": "a", "status": "pending"})
            store.save_feature("demo", feature, state)
            feature = store.load_feature("demo")
            feature["tasks"].append({"id": 2, "name": "b", "status": "pending"})
            store.save_feature("demo", feature, state)
            store.history_add("plan", "demo", [], [])

            # history 记录应为元素级 diff（added=[1,2]），而非整列快照
            rows = store.history_index()
            record = json.loads((store.history_dir / f"{rows[0]['id']}.json").read_text(encoding="utf-8"))
            entry = record["restore"][0]
            self.assertEqual(set(entry["lists"]["tasks"]["added"]), {"1", "2"})
            self.assertNotIn("tasks", entry["keys"])

            sean_state.cmd_undo(store, self._args())
            feature = store.load_feature("demo")
            self.assertEqual(feature.get("tasks"), [])

    def test_undo_restores_changed_task(self):
        """task-status 改状态后 undo，元素级还原为原状态。"""
        with tempfile.TemporaryDirectory() as tmp:
            store = sean_state.Store(Path(tmp))
            store.ensure()
            state = store.load_state()
            feature = sean_state.new_feature("demo")
            feature["tasks"] = [{"id": 1, "name": "a", "status": "pending"}]
            store.save_feature("demo", feature, state)
            feature = store.load_feature("demo")
            feature["tasks"][0]["status"] = "done"
            store.save_feature("demo", feature, state)
            store.history_add("task", "demo", [], [])

            record = json.loads(
                (store.history_dir / f"{store.history_index()[0]['id']}.json").read_text(encoding="utf-8"))
            entry = record["restore"][0]
            self.assertEqual(entry["lists"]["tasks"]["changed"]["1"]["status"], "pending")

            sean_state.cmd_undo(store, self._args())
            feature = store.load_feature("demo")
            self.assertEqual(feature["tasks"][0]["status"], "pending")


if __name__ == "__main__":
    unittest.main(verbosity=2)
