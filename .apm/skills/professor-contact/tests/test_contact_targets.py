import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "contact_targets.py"
spec = importlib.util.spec_from_file_location("contact_targets", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def member_fingerprint(members, schema_version="1"):
    """Mirror professor-research's preview_contract._member_fingerprint: the
    normalized members[] (item_key + preview_confidence) are hashed whole, so
    confidence-only changes move the fingerprint while membership does not."""
    return hashlib.sha256(
        json.dumps({"version": schema_version, "members": members}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def preview(professor="教授A", fp="fp-a"):
    directions = [
        {
            "direction_id": "dir_A",
            "name_ja": "方向A",
            "name_zh": "方向甲",
            "summary_zh": "甲方向简介",
            "members": [
                {"item_key": "P1", "preview_confidence": "high"},
                {"item_key": "P2", "preview_confidence": "low"},
            ],
            "low_confidence_count": 1,
            "coverage_share": 0.4,
            "representatives": [
                {"item_key": "P1", "title": "Paper One", "title_zh": "论文一", "year": 2025}
            ],
        },
        {
            "direction_id": "dir_B",
            "name_ja": "方向B",
            "name_zh": "方向乙",
            "summary_zh": "乙方向简介",
            "members": [
                {"item_key": "P2", "preview_confidence": "high"},
                {"item_key": "P3", "preview_confidence": "high"},
            ],
            "low_confidence_count": 0,
            "coverage_share": 0.6,
            "representatives": [
                {"item_key": "P3", "title": "Paper Three", "year": 2026}
            ],
        },
    ]
    for direction in directions:
        direction["member_fingerprint"] = member_fingerprint(direction["members"])
    return {
        "schema_version": 1,
        "professor": professor,
        "direction_id_version": "members-v1",
        "membership_mode": "overlap_allowed",
        "membership_coverage": {
            "assigned_unique_members": 3,
            "membership_edges": 4,
            "overlap_member_count": 1,
            "overlap_members": ["P2"],
            "unassigned_mountable_count": 0,
        },
        "preview_fingerprint": fp,
        "preview_fingerprint_version": "preview-v1",
        "coverage": 0.5,
        "data_confidence": "medium",
        "directions": directions,
    }


class ContactTargetsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.preview_path = self.root / "教授研究" / "lab" / "教授A" / "方向预筛.json"
        write_json(self.preview_path, preview())

    def tearDown(self):
        self.tmp.cleanup()

    def test_preview_summary_surfaces_ids_representatives_and_warnings(self):
        result = mod.preview_options(self.preview_path)
        self.assertEqual(result["professor"], "教授A")
        self.assertEqual([o["direction_id"] for o in result["options"]], ["dir_A", "dir_B"])
        self.assertEqual(result["options"][0]["representatives"][0]["item_key"], "P1")
        self.assertIn("1 member papers are low-confidence", result["options"][0]["warnings"])
        self.assertTrue(any("abstract coverage" in w for w in result["options"][0]["warnings"]))

    def test_selecting_a_and_b_keeps_separate_directions_with_overlap(self):
        result = mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {"dir_A": "note A", "dir_B": "note B"}},
            selected_at="2026-09-03T12:00:00Z",
        )
        self.assertEqual(result["selected_count"], 2)
        state = json.loads((self.root / "教授研究" / "套磁目标.json").read_text(encoding="utf-8"))
        target = state["targets"][0]
        self.assertEqual(target["selected_direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual(len(target["directions"]), 2)
        members_a = {m["item_key"] for m in target["directions"][0]["members"]}
        members_b = {m["item_key"] for m in target["directions"][1]["members"]}
        self.assertIn("P2", members_a & members_b)
        self.assertEqual(target["directions"][0]["user_note"], "note A")
        self.assertEqual(target["directions"][1]["user_note"], "note B")

    def test_reselection_preserves_other_professors_and_history(self):
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {"dir_A": "old A", "dir_B": "old B"}},
            selected_at="2026-09-03T12:00:00Z",
        )
        preview_b_path = self.root / "教授研究" / "lab" / "教授B" / "方向预筛.json"
        write_json(preview_b_path, preview(professor="教授B", fp="fp-b"))
        mod.select_target(
            self.root,
            preview_b_path,
            {"direction_ids": ["dir_A"], "notes": {"dir_A": "prof B"}},
            selected_at="2026-09-03T12:01:00Z",
        )
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_B"], "notes": {}},
            selected_at="2026-09-03T12:02:00Z",
        )
        state = json.loads((self.root / "教授研究" / "套磁目标.json").read_text(encoding="utf-8"))
        self.assertEqual([t["professor"] for t in state["targets"]], ["教授A", "教授B"])
        a = state["targets"][0]
        self.assertEqual(a["selected_direction_ids"], ["dir_B"])
        self.assertEqual(a["directions"][0]["user_note"], "old B")
        self.assertEqual(len(a["selection_history"]), 1)
        self.assertEqual(a["selection_history"][0]["selected_direction_ids"], ["dir_A", "dir_B"])

    def test_revision_empty_string_note_clears_but_omitted_key_keeps_old_note(self):
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {"dir_A": "old A", "dir_B": "old B"}},
            selected_at="2026-09-03T12:00:00Z",
        )
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {"dir_A": ""}},
            selected_at="2026-09-03T12:01:00Z",
        )
        state = json.loads((self.root / "教授研究" / "套磁目标.json").read_text(encoding="utf-8"))
        notes = {d["direction_id"]: d["user_note"] for d in state["targets"][0]["directions"]}
        self.assertEqual(notes["dir_A"], "")
        self.assertEqual(notes["dir_B"], "old B")

    def test_resolve_tolerates_preview_fingerprint_only_change(self):
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A"], "notes": {"dir_A": "note A"}},
            selected_at="2026-09-03T12:00:00Z",
        )
        write_json(self.preview_path, preview(fp="fp-new"))
        result = mod.resolve_targets(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("stale_targets", result)
        state = json.loads((self.root / "教授研究" / "套磁目标.json").read_text(encoding="utf-8"))
        target = state["targets"][0]
        self.assertEqual(target["preview_fingerprint"], "fp-a")
        self.assertEqual(target["directions"][0]["user_note"], "note A")

    def test_resolve_ignores_unselected_direction_changes(self):
        base = preview()
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A"], "notes": {"dir_A": "note A"}},
            selected_at="2026-09-03T12:00:00Z",
        )
        data = copy.deepcopy(base)
        data["preview_fingerprint"] = "fp-unrelated"
        data["directions"][1]["name_ja"] = "方向B改"
        data["directions"][1]["name_zh"] = "方向乙改"
        data["directions"][1]["members"] = [{"item_key": "P4", "preview_confidence": "high"}]
        data["directions"][1]["member_fingerprint"] = member_fingerprint(data["directions"][1]["members"])
        data["directions"][1]["representatives"] = [{"item_key": "P4", "title_zh": "论文四"}]
        dir_c_members = [{"item_key": "P5", "preview_confidence": "high"}]
        data["directions"].append({
            "direction_id": "dir_C",
            "name_ja": "方向C",
            "name_zh": "方向丙",
            "summary_zh": "丙方向简介",
            "member_fingerprint": member_fingerprint(dir_c_members),
            "members": dir_c_members,
            "low_confidence_count": 0,
            "coverage_share": 0.2,
            "representatives": [],
        })
        write_json(self.preview_path, data)
        result = mod.resolve_targets(self.root)
        self.assertEqual(result["status"], "ok")
        state = json.loads((self.root / "教授研究" / "套磁目标.json").read_text(encoding="utf-8"))
        target = state["targets"][0]
        self.assertEqual(target["preview_fingerprint"], "fp-a")
        self.assertEqual(target["directions"][0]["user_note"], "note A")
        self.assertEqual(target["directions"][0]["member_fingerprint"], base["directions"][0]["member_fingerprint"])

    def test_resolve_flags_only_materially_changed_selected_directions(self):
        base = preview()
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {"dir_A": "note A", "dir_B": "note B"}},
            selected_at="2026-09-03T12:00:00Z",
        )
        data = copy.deepcopy(base)
        data["directions"][0]["members"].append({"item_key": "P9", "preview_confidence": "low"})
        data["directions"][0]["member_fingerprint"] = member_fingerprint(data["directions"][0]["members"])
        write_json(self.preview_path, data)
        result = mod.resolve_targets(self.root)
        self.assertEqual(result["status"], "needs_refresh")
        self.assertEqual(result["reason_code"], "preview_changed")
        stale = result["stale_targets"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["professor"], "教授A")
        self.assertEqual(stale[0]["direction_ids"], ["dir_A"])
        entry = stale[0]["directions"][0]
        self.assertEqual(entry["reason"], "selected_direction_changed")
        self.assertEqual(entry["stored_member_fingerprint"], base["directions"][0]["member_fingerprint"])
        self.assertEqual(entry["current_member_fingerprint"], data["directions"][0]["member_fingerprint"])
        self.assertEqual(entry["stored_member_keys"], ["P1", "P2"])
        self.assertEqual(entry["current_member_keys"], ["P1", "P2", "P9"])
        state = json.loads((self.root / "教授研究" / "套磁目标.json").read_text(encoding="utf-8"))
        target = state["targets"][0]
        self.assertEqual(target["directions"][0]["user_note"], "note A")
        self.assertEqual(target["directions"][0]["member_fingerprint"], base["directions"][0]["member_fingerprint"])

    def test_resolve_flags_removed_selected_direction(self):
        base = preview()
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {}},
            selected_at="2026-09-03T12:00:00Z",
        )
        data = copy.deepcopy(base)
        data["directions"] = [data["directions"][0]]
        write_json(self.preview_path, data)
        result = mod.resolve_targets(self.root)
        self.assertEqual(result["status"], "needs_refresh")
        self.assertEqual(result["reason_code"], "preview_changed")
        stale = result["stale_targets"]
        self.assertEqual(stale[0]["direction_ids"], ["dir_B"])
        entry = stale[0]["directions"][0]
        self.assertEqual(entry["reason"], "selected_direction_removed")
        self.assertEqual(entry["stored_member_fingerprint"], base["directions"][1]["member_fingerprint"])
        self.assertEqual(entry["stored_member_keys"], ["P2", "P3"])

    def test_resolve_refreshes_display_only_selected_direction_changes(self):
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A"], "notes": {"dir_A": "note A"}},
            selected_at="2026-09-03T12:00:00Z",
        )
        data = copy.deepcopy(preview(fp="fp-display"))
        direction = data["directions"][0]
        direction["name_ja"] = "方向A改"
        direction["name_zh"] = "方向甲改"
        direction["summary_zh"] = "甲方向新简介"
        direction["representatives"] = [{"item_key": "P2", "title_zh": "论文二"}]
        # Confidence-only drift moves the real upstream member_fingerprint while
        # the item_key membership (and therefore direction_id) stays the same.
        direction["members"][1]["preview_confidence"] = "high"
        direction["member_fingerprint"] = member_fingerprint(direction["members"])
        write_json(self.preview_path, data)
        result = mod.resolve_targets(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["projection_refreshed"], [{"professor": "教授A", "direction_ids": ["dir_A"]}])
        state = json.loads((self.root / "教授研究" / "套磁目标.json").read_text(encoding="utf-8"))
        target = state["targets"][0]
        self.assertEqual(target["preview_fingerprint"], "fp-display")
        self.assertEqual(target["selected_direction_ids"], ["dir_A"])
        self.assertEqual(target["selection_history"], [])
        self.assertIsNotNone(target["projection_refreshed_at"])
        refreshed = target["directions"][0]
        self.assertEqual(refreshed["direction_id"], "dir_A")
        self.assertEqual(refreshed["name_ja"], "方向A改")
        self.assertEqual(refreshed["name_zh"], "方向甲改")
        self.assertEqual(refreshed["summary_zh"], "甲方向新简介")
        self.assertEqual(refreshed["representatives"], [{"item_key": "P2", "title_zh": "论文二"}])
        self.assertEqual(refreshed["members"][1]["preview_confidence"], "high")
        self.assertEqual(refreshed["member_fingerprint"], direction["member_fingerprint"])
        self.assertEqual(refreshed["user_note"], "note A")

    def test_resolve_filters_selected_professor(self):
        mod.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A"], "notes": {}},
            selected_at="2026-09-03T12:00:00Z",
        )
        ok = mod.resolve_targets(self.root, ["教授A"])
        self.assertEqual(ok["status"], "ok")
        self.assertEqual(ok["professors"], ["教授A"])
        missing = mod.resolve_targets(self.root, ["教授B"])
        self.assertEqual(missing["status"], "needs_input")
        self.assertEqual(missing["reason_code"], "professor_not_selected")


if __name__ == "__main__":
    unittest.main()
