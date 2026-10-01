import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from issue64_test_support import observe_target_access, path_set

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "contact_targets.py"
spec = importlib.util.spec_from_file_location("contact_targets", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

RESEARCH_DIR = Path("教授研究")
PREVIEW_NAME = "方向预筛.json"
TARGET_NAME = "套磁目标.json"
PROFESSOR_A_DIR = RESEARCH_DIR / "lab" / "教授A"
PROFESSOR_B_DIR = RESEARCH_DIR / "lab" / "教授B"
# Same display name as professor A, different canonical directory: R64-17 identity.
PROFESSOR_A2_DIR = RESEARCH_DIR / "other-lab" / "教授A"
LEGACY_TABLE = RESEARCH_DIR / TARGET_NAME
BOOTSTRAP_AT = "2026-09-03T12:00:00Z"
REVISION_AT = "2026-09-03T12:01:00Z"


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


def legacy_entry(target, professor_dir, preview_rel):
    """Rebuild the retired program-level entry shape from a local v2 target."""
    entry = {key: copy.deepcopy(value) for key, value in target.items()
             if key not in ("schema_version", "kind", "professor_dir", "preview_path")}
    entry["professor_dir"] = professor_dir
    entry["preview_path"] = preview_rel
    return entry


class ContactTargetsTests(unittest.TestCase):
    """Stage-0 authority is one professor-local file: <professor_dir>/套磁目标.json.

    r25 §5.1 keeps ``select``/``resolve`` on the existing local file only; r25
    §5.2 makes ``bootstrap`` the single path allowed to establish a first local
    target and to read the retired program-level table.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.preview_path = self.root / PROFESSOR_A_DIR / PREVIEW_NAME
        self.target_path = self.root / PROFESSOR_A_DIR / TARGET_NAME
        self.legacy_path = self.root / LEGACY_TABLE
        write_json(self.preview_path, preview())

    def tearDown(self):
        self.tmp.cleanup()

    # --- fixtures ----------------------------------------------------------

    def bootstrap(self, direction_ids=("dir_A",), notes=None, selected_at=BOOTSTRAP_AT,
                  preview_path=None):
        return mod.bootstrap_target(
            self.root,
            preview_path or self.preview_path,
            {"direction_ids": list(direction_ids), "notes": notes or {}},
            selected_at=selected_at,
        )

    def select(self, direction_ids=("dir_A",), notes=None, selected_at=REVISION_AT,
               preview_path=None):
        return mod.select_target(
            self.root,
            preview_path or self.preview_path,
            {"direction_ids": list(direction_ids), "notes": notes or {}},
            selected_at=selected_at,
        )

    def read_target(self, path=None):
        return json.loads((path or self.target_path).read_text(encoding="utf-8"))

    def resolve(self, path=None, professors=None):
        return mod.resolve_target(path or self.target_path, self.root, professors)

    def b_target_path(self):
        return self.root / PROFESSOR_B_DIR / TARGET_NAME

    def write_b_preview(self, **kwargs):
        path = self.root / PROFESSOR_B_DIR / PREVIEW_NAME
        write_json(path, preview(professor="教授B", **kwargs))
        return path

    def write_legacy(self, *entries):
        write_json(self.legacy_path, {
            "schema_version": 1, "kind": "professor-contact-targets", "updated_at": None,
            "targets": list(entries)})
        return self.legacy_path

    def a_entry(self, target=None, **overrides):
        entry = legacy_entry(target if target is not None else self.read_target(),
                             str(PROFESSOR_A_DIR), str(PROFESSOR_A_DIR / PREVIEW_NAME))
        entry.update(overrides)
        return entry

    def business_result(self, resolution):
        """The mechanical projection compared across legacy mutations."""
        return {"status": resolution["status"],
                "professors": resolution.get("professors"),
                "targets": resolution.get("targets")}

    # --- G64-T1: local authority, sibling isolation, legacy inertness ------

    def test_issue64_t1_authority_is_one_professor_local_file(self):
        before_paths = path_set(self.root / RESEARCH_DIR)
        result = self.bootstrap(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})
        self.assertEqual(path_set(self.root / RESEARCH_DIR),
                         before_paths | {str(Path('lab') / '教授A' / TARGET_NAME)})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(Path(result["state_path"]).resolve(), self.target_path.resolve())
        self.assertFalse(self.legacy_path.exists())
        self.assertFalse(self.b_target_path().exists())
        state = self.read_target()
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["kind"], "professor-contact-target")
        self.assertNotIn("targets", state)
        self.assertEqual(state["selected_direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual(len(state["directions"]), 2)
        self.assertEqual(state["professor_dir"], str(PROFESSOR_A_DIR))
        self.assertEqual(state["preview_path"], str(PROFESSOR_A_DIR / PREVIEW_NAME))
        self.assertEqual(state["directions"][0]["user_note"], "note A")
        self.assertEqual(state["directions"][1]["user_note"], "note B")

    def test_issue64_t1_malformed_sibling_target_does_not_block_or_change_a(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        b_preview = self.write_b_preview(fp="fp-b")
        mod.bootstrap_target(self.root, b_preview, {"direction_ids": ["dir_A"], "notes": {}},
                             selected_at=REVISION_AT)
        self.b_target_path().write_text("{ this is not json", encoding="utf-8")
        b_before = self.b_target_path().read_bytes()
        a_before = self.target_path.read_bytes()

        reselected = self.select(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"},
                                 selected_at="2026-09-03T12:02:00Z")
        self.assertEqual(reselected["status"], "ok")
        self.assertEqual(reselected["professor"], "教授A")
        resolved = self.resolve()
        self.assertEqual(resolved["status"], "ok")
        self.assertEqual([t["professor"] for t in resolved["targets"]], ["教授A"])
        self.assertEqual([t["professor_dir"] for t in resolved["targets"]], [str(PROFESSOR_A_DIR)])
        self.assertEqual(resolved["professors"], ["教授A"])

        self.assertEqual(self.b_target_path().read_bytes(), b_before)
        self.assertNotEqual(self.target_path.read_bytes(), a_before)
        self.assertFalse(self.legacy_path.exists())

    def test_issue64_t1_reselection_reads_only_its_own_professor(self):
        self.bootstrap(["dir_A", "dir_B"], {"dir_A": "old A", "dir_B": "old B"})
        b_preview = self.write_b_preview(fp="fp-b")
        mod.bootstrap_target(self.root, b_preview,
                             {"direction_ids": ["dir_A"], "notes": {"dir_A": "prof B"}},
                             selected_at=REVISION_AT)
        self.b_target_path().write_text("nope", encoding="utf-8")

        before_paths = path_set(self.root / RESEARCH_DIR)
        with observe_target_access(self.b_target_path()) as accesses:
            result = self.select(["dir_B"], selected_at="2026-09-03T12:02:00Z")
            self.assertEqual(self.resolve()['status'], 'ok')
        self.assertEqual(accesses, [], 'A accessed the sibling target')
        self.assertEqual(path_set(self.root / RESEARCH_DIR), before_paths)

        self.assertEqual(result["status"], "ok")
        target = self.read_target()
        self.assertEqual(target["selected_direction_ids"], ["dir_B"])
        self.assertEqual(target["directions"][0]["user_note"], "old B")
        self.assertEqual(len(target["selection_history"]), 1)
        self.assertEqual(target["selection_history"][0]["selected_direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual(self.b_target_path().read_text(encoding="utf-8"), "nope")

    def test_issue64_t1_existing_local_select_ignores_malformed_legacy_bytes(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        self.write_legacy(self.a_entry())
        self.legacy_path.write_text("{ broken legacy", encoding="utf-8")
        legacy_before = self.legacy_path.read_bytes()

        result = self.select(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "revised")
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)
        target = self.read_target()
        self.assertEqual(target["directions"][1]["user_note"], "note B")
        self.assertEqual(len(target["selection_history"]), 1)

    def test_issue64_t1_legacy_change_delete_or_corrupt_never_alters_a_resolve(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        baseline = self.business_result(self.resolve())
        self.assertEqual(baseline["status"], "ok")
        b_entry = self.a_entry(professor="教授B", professor_dir=str(PROFESSOR_B_DIR),
                               preview_path=str(PROFESSOR_B_DIR / PREVIEW_NAME))
        cases = {
            "foreign-owner legacy entry": lambda: self.write_legacy(b_entry),
            "malformed legacy document": lambda: self.legacy_path.write_text(
                "{ corrupt on purpose", encoding="utf-8"),
            "deleted legacy document": lambda: self.legacy_path.unlink(missing_ok=True),
        }
        for label, mutate in cases.items():
            with self.subTest(label):
                mutate()
                self.assertEqual(self.business_result(self.resolve()), baseline)
        self.assertFalse(self.legacy_path.exists())

    # --- G64-T2: current professor fails closed, single-professor semantics --

    def test_issue64_t2_overlap_members_are_projected_per_direction(self):
        result = self.bootstrap(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})
        self.assertEqual(result["selected_count"], 2)
        target = self.read_target()
        members_a = {m["item_key"] for m in target["directions"][0]["members"]}
        members_b = {m["item_key"] for m in target["directions"][1]["members"]}
        self.assertIn("P2", members_a & members_b)

    def test_issue64_t2_revision_empty_string_note_clears_but_omitted_key_keeps_old_note(self):
        self.bootstrap(["dir_A", "dir_B"], {"dir_A": "old A", "dir_B": "old B"})
        self.select(["dir_A", "dir_B"], {"dir_A": ""})
        notes = {d["direction_id"]: d["user_note"] for d in self.read_target()["directions"]}
        self.assertEqual(notes["dir_A"], "")
        self.assertEqual(notes["dir_B"], "old B")
        self.select(["dir_A", "dir_B"], {"dir_B": "updated B"})
        notes = {d["direction_id"]: d["user_note"] for d in self.read_target()["directions"]}
        self.assertEqual(notes, {'dir_A': '', 'dir_B': 'updated B'})

    def test_issue64_t2_resolve_tolerates_preview_fingerprint_only_change(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        write_json(self.preview_path, preview(fp="fp-new"))
        result = self.resolve()
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("stale_targets", result)
        target = self.read_target()
        self.assertEqual(target["preview_fingerprint"], "fp-a")
        self.assertEqual(target["directions"][0]["user_note"], "note A")

    def test_issue64_t2_resolve_ignores_unselected_direction_changes(self):
        base = preview()
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
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
        result = self.resolve()
        self.assertEqual(result["status"], "ok")
        target = self.read_target()
        self.assertEqual(target["preview_fingerprint"], "fp-a")
        self.assertEqual(target["directions"][0]["user_note"], "note A")
        self.assertEqual(target["directions"][0]["member_fingerprint"],
                         base["directions"][0]["member_fingerprint"])

    def test_issue64_t2_resolve_flags_only_materially_changed_selected_directions(self):
        base = preview()
        self.bootstrap(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})
        data = copy.deepcopy(base)
        data["directions"][0]["members"].append({"item_key": "P9", "preview_confidence": "low"})
        data["directions"][0]["member_fingerprint"] = member_fingerprint(data["directions"][0]["members"])
        write_json(self.preview_path, data)
        before = self.target_path.read_bytes()
        result = self.resolve()
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
        self.assertEqual(self.target_path.read_bytes(), before)

    def test_issue64_t2_resolve_flags_removed_selected_direction(self):
        base = preview()
        self.bootstrap(["dir_A", "dir_B"])
        data = copy.deepcopy(base)
        data["directions"] = [data["directions"][0]]
        write_json(self.preview_path, data)
        before = self.target_path.read_bytes()
        result = self.resolve()
        self.assertEqual(result["status"], "needs_refresh")
        self.assertEqual(result["reason_code"], "preview_changed")
        stale = result["stale_targets"]
        self.assertEqual(stale[0]["direction_ids"], ["dir_B"])
        entry = stale[0]["directions"][0]
        self.assertEqual(entry["reason"], "selected_direction_removed")
        self.assertEqual(entry["stored_member_fingerprint"], base["directions"][1]["member_fingerprint"])
        self.assertEqual(entry["stored_member_keys"], ["P2", "P3"])
        self.assertEqual(self.target_path.read_bytes(), before)

    def test_issue64_t2_resolve_refreshes_display_only_selected_direction_changes(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
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
        result = self.resolve()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["projection_refreshed"], [{"professor": "教授A", "direction_ids": ["dir_A"]}])
        target = self.read_target()
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

    def test_issue64_t2_resolve_filters_selected_professor(self):
        self.bootstrap(["dir_A"])
        ok = self.resolve(professors=["教授A"])
        self.assertEqual(ok["status"], "ok")
        self.assertEqual(ok["professors"], ["教授A"])
        missing = self.resolve(professors=["教授B"])
        self.assertEqual(missing["status"], "needs_input")
        self.assertEqual(missing["reason_code"], "professor_not_selected")

    def test_issue64_t2_resolve_reports_needs_input_for_the_current_professor_only(self):
        self.bootstrap(["dir_A"])
        self.target_path.unlink()
        result = self.resolve()
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(result["reason_code"], "missing_target_state")
        self.assertEqual(Path(result["state_path"]).resolve(), self.target_path.resolve())
        self.assertEqual(result["targets"], [])

    def test_issue64_t2_invalid_local_target_state_fails_closed(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        cases = {
            "legacy program envelope kept in a local file": {
                "schema_version": 1, "kind": "professor-contact-targets",
                "targets": [self.read_target()]},
            "schema version drift": {**self.read_target(), "schema_version": 99},
            "kind drift": {**self.read_target(), "kind": "professor-contact-targets"},
            "professor_dir mismatch": {**self.read_target(), "professor_dir": "教授研究/lab/其他教授"},
            "preview outside its professor_dir": {
                **self.read_target(), "preview_path": "教授研究/lab/教授B/方向预筛.json"},
            "selected direction without projection": {
                **self.read_target(), "selected_direction_ids": ["dir_A", "dir_Z"]},
            "empty members": {
                **self.read_target(), "directions": [{**self.read_target()["directions"][0], "members": []}]},
            "multi-professor envelope": {**self.read_target(), "targets": [self.read_target()]},
        }
        for label, payload in cases.items():
            with self.subTest(label):
                write_json(self.target_path, payload)
                before = self.target_path.read_bytes()
                with self.assertRaises(ValueError):
                    self.resolve()
                with self.assertRaises(ValueError):
                    self.select(["dir_A"], {"dir_A": "note A"})
                with self.assertRaises(ValueError):
                    self.bootstrap(["dir_A"], {"dir_A": "note A"})
                self.assertEqual(self.target_path.read_bytes(), before)
        self.assertFalse(self.legacy_path.exists())

    def test_issue64_t2_stored_professor_must_match_its_own_preview(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        write_json(self.target_path, {**self.read_target(), "professor": "教授C"})
        before = self.target_path.read_bytes()
        result = self.resolve()
        self.assertEqual(result["status"], "needs_refresh")
        self.assertEqual(result["stale_targets"][0]["reason"], "professor_changed")
        for operation in (self.select, self.bootstrap):
            with self.assertRaises(ValueError):
                operation()
        self.assertEqual(self.target_path.read_bytes(), before)

    def test_issue64_atomic_real_revision_and_first_establishment_preserve_bytes_on_commit_failure(self):
        # P64-ATOMIC: two distinct initial states; no low-level-only oracle.
        self.bootstrap()
        self.write_legacy(self.a_entry())
        target_before = self.target_path.read_bytes()
        preview_before = self.preview_path.read_bytes()
        legacy_before = self.legacy_path.read_bytes()
        before_paths = path_set(self.root)
        with mock.patch.object(mod.os, 'replace', side_effect=OSError('commit failure')):
            with self.assertRaises(OSError):
                self.select(['dir_B'])
        self.assertEqual(self.target_path.read_bytes(), target_before)
        self.assertEqual(path_set(self.root), before_paths)
        self.target_path.unlink()
        before_paths = path_set(self.root)
        with mock.patch.object(mod.os, 'replace', side_effect=OSError('commit failure')):
            with self.assertRaises(OSError):
                self.bootstrap()
        self.assertFalse(self.target_path.exists())
        self.assertEqual(self.preview_path.read_bytes(), preview_before)
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)
        self.assertEqual(path_set(self.root), before_paths)

    def test_issue64_t2_local_target_outside_the_research_directory_fails_closed(self):
        self.bootstrap(["dir_A"])
        stray_dir = self.root / "其他目录" / "教授A"
        write_json(stray_dir / TARGET_NAME, self.read_target())
        with self.assertRaises(ValueError):
            mod.resolve_target(stray_dir / TARGET_NAME, self.root)

    def test_issue64_t2_preview_summary_surfaces_ids_representatives_and_warnings(self):
        result = mod.preview_options(self.preview_path)
        self.assertEqual(result["professor"], "教授A")
        self.assertEqual([o["direction_id"] for o in result["options"]], ["dir_A", "dir_B"])
        self.assertEqual(result["options"][0]["representatives"][0]["item_key"], "P1")
        self.assertIn("1 member papers are low-confidence", result["options"][0]["warnings"])
        self.assertTrue(any("abstract coverage" in w for w in result["options"][0]["warnings"]))

    # --- G64-T3: first-local bootstrap, recovery, conflict preflight -------

    def test_issue64_t3_select_without_local_target_returns_bootstrap_required(self):
        result = self.select(["dir_A"], {"dir_A": "note A"})
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(result["reason_code"], "bootstrap_required")
        self.assertFalse(self.target_path.exists())
        self.assertFalse(self.legacy_path.exists())
        self.assertEqual(Path(result["state_path"]).resolve(), self.target_path.resolve())
        self.assertEqual(result["transaction"]["target_state"], str(self.target_path.resolve()))

    def test_issue64_t3_bootstrap_never_establishes_for_an_invalid_preview(self):
        write_json(self.preview_path, {"professor": "教授A", "directions": []})
        with self.assertRaises(ValueError):
            self.bootstrap(["dir_A"])
        self.assertFalse(self.target_path.exists())

    def test_issue64_t3_reliable_legacy_entry_carries_note_and_history(self):
        self.bootstrap(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})
        entry = self.a_entry(selection_history=[{"marker": "pre-issue64"}])
        self.target_path.unlink()
        self.write_legacy(entry)
        legacy_before = self.legacy_path.read_bytes()

        result = self.bootstrap(["dir_A"], {"dir_A": ""})

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "migrated_revised")
        self.assertEqual(result["legacy_candidates"], 1)
        target = self.read_target()
        self.assertEqual(target["selected_direction_ids"], ["dir_A"])
        self.assertEqual(target["directions"][0]["user_note"], "")
        self.assertEqual(target["selection_history"][0]["marker"], "pre-issue64")
        self.assertEqual(target["selection_history"][1]["selected_direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual(target["selection_history"][1]["directions"][1]["user_note"], "note B")
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_preview_stale_legacy_revises_in_one_write(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        self.write_legacy(self.a_entry())
        self.target_path.unlink()
        legacy_before = self.legacy_path.read_bytes()

        data = copy.deepcopy(preview(fp="fp-stale"))
        data["directions"][0]["members"].append({"item_key": "P9", "preview_confidence": "high"})
        data["directions"][0]["member_fingerprint"] = member_fingerprint(data["directions"][0]["members"])
        write_json(self.preview_path, data)

        result = self.bootstrap(["dir_A"], {"dir_A": "note A"})

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "migrated_revised")
        target = self.read_target()
        self.assertEqual(target["preview_fingerprint"], "fp-stale")
        self.assertEqual([m["item_key"] for m in target["directions"][0]["members"]], ["P1", "P2", "P9"])
        self.assertEqual(target["directions"][0]["member_fingerprint"],
                         data["directions"][0]["member_fingerprint"])
        self.assertEqual(target["directions"][0]["user_note"], "note A")
        self.assertEqual(len(target["selection_history"]), 1)
        self.assertEqual(target["selection_history"][0]["preview_fingerprint"], "fp-a")
        self.assertEqual(target["selection_history"][0]["selected_direction_ids"], ["dir_A"])
        self.assertEqual(self.resolve()["status"], "ok")
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_malformed_legacy_document_still_establishes_fresh_local(self):
        self.legacy_path.write_text("{[ not json at all", encoding="utf-8")
        legacy_before = self.legacy_path.read_bytes()

        result = self.bootstrap(["dir_A"], {"dir_A": "note A"})

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "fresh")
        self.assertEqual(result["legacy_recovery"], "legacy_recovery_unavailable")
        self.assertEqual(result["legacy_candidates"], 0)
        target = self.read_target()
        self.assertEqual(target["schema_version"], 2)
        self.assertEqual(target["selection_history"], [])
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_unattributable_legacy_entries_are_never_imported(self):
        b_preview = self.write_b_preview(fp="fp-b")
        identity_only = {"professor": "教授B", "selected_direction_ids": ["dir_A"],
                         "preview_fingerprint": "fp-b", "preview_fingerprint_version": "preview-v1",
                         "selected_at": BOOTSTRAP_AT, "selection_history": [], "directions": []}
        cases = {
            "other_professor": {**identity_only,
                                "professor_dir": str(PROFESSOR_B_DIR),
                                "preview_path": str(PROFESSOR_B_DIR / PREVIEW_NAME)},
            "same_name_other_dir": {**identity_only, "professor": "教授A",
                                    "professor_dir": str(PROFESSOR_A2_DIR),
                                    "preview_path": str(PROFESSOR_A2_DIR / PREVIEW_NAME)},
            "path_conflicting": {**identity_only, "professor": "教授A",
                                 "professor_dir": str(PROFESSOR_A_DIR),
                                 "preview_path": str(PROFESSOR_B_DIR / PREVIEW_NAME)},
            "no_dir": {**identity_only, "professor": "教授A", "professor_dir": "",
                       "preview_path": str(PROFESSOR_A_DIR / PREVIEW_NAME)},
            "absolute_preview": {**identity_only, "professor": "教授A",
                                 "professor_dir": str(PROFESSOR_A_DIR),
                                 "preview_path": "/tmp/方向预筛.json"},
        }
        self.write_legacy(*cases.values())
        legacy_before = self.legacy_path.read_bytes()

        result = self.bootstrap(["dir_A"], {"dir_A": "note A"})

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "fresh")
        self.assertEqual(result["legacy_candidates"], 0)
        self.assertEqual(result["legacy_recovery"], "legacy_recovery_ambiguous")
        self.assertEqual(sorted(item["reason"] for item in result["legacy_skipped"]),
                         ["identity_unreliable", "identity_unreliable", "other_professor",
                          "same_name_other_dir", "same_name_other_dir"])
        target = self.read_target()
        self.assertEqual(target["selection_history"], [])
        self.assertEqual(target["directions"][0]["user_note"], "note A")
        self.assertFalse(self.b_target_path().exists())
        self.assertFalse((self.root / PROFESSOR_A2_DIR / TARGET_NAME).exists())
        self.assertFalse((self.root / PROFESSOR_A2_DIR / PREVIEW_NAME).exists())
        self.assertTrue(b_preview.is_file())
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_conflicting_candidates_fail_before_the_first_write(self):
        self.bootstrap(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})
        entry_a = self.a_entry()
        conflicting = self.a_entry(selected_direction_ids=["dir_B"],
                                   directions=[copy.deepcopy(self.read_target()["directions"][1])])
        self.target_path.unlink()
        self.write_legacy(entry_a, conflicting)
        legacy_before = self.legacy_path.read_bytes()

        result = self.bootstrap(["dir_A"], {"dir_A": "note A"})

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason_code"], "legacy_candidates_conflict")
        self.assertFalse(self.target_path.exists())
        self.assertFalse(self.b_target_path().exists())
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)
        self.assertEqual(result["transaction"]["professor_dir"], str(PROFESSOR_A_DIR))

    def test_issue64_t3_defective_own_legacy_candidate_fails_closed(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        self.write_legacy(self.a_entry(directions=[]))
        self.target_path.unlink()
        legacy_before = self.legacy_path.read_bytes()

        result = self.bootstrap(["dir_A"], {"dir_A": "note A"})

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason_code"], "invalid_legacy_candidate_state")
        self.assertFalse(self.target_path.exists())
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_identical_candidates_migrate_once(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        entry = self.a_entry(selection_history=[{"marker": "pre-issue64"}])
        self.target_path.unlink()
        self.write_legacy(copy.deepcopy(entry), copy.deepcopy(entry))

        result = self.bootstrap(["dir_A"], {"dir_A": "note A"})

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "migrated")
        self.assertEqual(result["legacy_candidates"], 2)
        target = self.read_target()
        self.assertEqual(target["selection_history"], [{"marker": "pre-issue64"}])
        self.assertEqual(target["directions"][0]["user_note"], "note A")
        self.assertEqual(target["selected_at"], BOOTSTRAP_AT)
        self.assertEqual(target["preview_fingerprint"], "fp-a")

    def test_issue64_t3_bootstrap_is_a_no_op_once_local_exists(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        before = self.target_path.read_bytes()

        result = self.bootstrap(["dir_A", "dir_B"], {"dir_B": "ignored"})

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "already_established")
        self.assertEqual(result["selected_direction_ids"], ["dir_A"])
        self.assertEqual(self.target_path.read_bytes(), before)
        self.assertFalse(self.legacy_path.exists())

    def test_issue64_t3_a_bootstrap_survives_b_bootstrap_failure(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        a_before = self.target_path.read_bytes()
        b_preview = self.write_b_preview(fp="fp-b")
        b_entry = self.a_entry(professor="教授B", professor_dir=str(PROFESSOR_B_DIR),
                               preview_path=str(PROFESSOR_B_DIR / PREVIEW_NAME))
        wide = {**copy.deepcopy(b_entry), "selected_direction_ids": ["dir_A", "dir_B"],
                "directions": [*copy.deepcopy(b_entry["directions"]),
                               {**copy.deepcopy(b_entry["directions"][0]),
                                "direction_id": "dir_B", "user_note": "note B2"}]}
        self.write_legacy(b_entry, wide)

        conflicted = mod.bootstrap_target(self.root, b_preview,
                                          {"direction_ids": ["dir_A"], "notes": {}},
                                          selected_at=REVISION_AT)

        self.assertEqual(conflicted["status"], "error")
        self.assertEqual(conflicted["reason_code"], "legacy_candidates_conflict")
        self.assertFalse(self.b_target_path().exists())
        self.assertEqual(self.target_path.read_bytes(), a_before)
        self.assertEqual(self.resolve()["status"], "ok")

    # --- G64-T3: explicit bulk migration reuses the same per-professor rules -

    def _legacy_fixture(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        a_target = self.read_target()
        b_preview = self.write_b_preview(fp="fp-b")
        mod.bootstrap_target(self.root, b_preview,
                             {"direction_ids": ["dir_A"], "notes": {"dir_A": "note B"}},
                             selected_at=BOOTSTRAP_AT)
        b_target = self.read_target(self.b_target_path())
        self.target_path.unlink()
        self.b_target_path().unlink()
        bad_b = legacy_entry(copy.deepcopy(b_target), str(PROFESSOR_B_DIR),
                             str(PROFESSOR_B_DIR / PREVIEW_NAME))
        bad_b["directions"] = []
        self.write_legacy(legacy_entry(a_target, str(PROFESSOR_A_DIR),
                                       str(PROFESSOR_A_DIR / PREVIEW_NAME)), bad_b)

    def test_issue64_t3_bulk_migration_reports_each_professor_separately(self):
        self._legacy_fixture()
        result = mod.migrate_legacy_targets(self.root)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["migrated"], ["教授A"])
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["failures"][0]["professor"], "教授B")
        a_target = self.read_target()
        self.assertEqual(a_target["schema_version"], 2)
        self.assertEqual(a_target["kind"], "professor-contact-target")
        self.assertEqual(a_target["directions"][0]["user_note"], "note A")
        self.assertFalse(self.b_target_path().exists())
        self.assertEqual(self.resolve()["status"], "ok")

    def test_issue64_t3_bulk_migration_keeps_later_professor_when_first_group_fails(self):
        self._legacy_fixture()
        entries = json.loads(self.legacy_path.read_text())['targets']
        # Swap which group is defective while retaining valid upstream entries.
        good_a = copy.deepcopy(entries[0])
        good_b = copy.deepcopy(good_a)
        good_b.update(professor='教授B', professor_dir=str(PROFESSOR_B_DIR),
                      preview_path=str(PROFESSOR_B_DIR / PREVIEW_NAME),
                      preview_fingerprint='fp-b')
        bad_a = copy.deepcopy(good_a)
        bad_a['directions'] = []
        self.write_legacy(bad_a, good_b)
        legacy_before = self.legacy_path.read_bytes()
        result = mod.migrate_legacy_targets(self.root)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['migrated'], ['教授B'])
        self.assertEqual(result['failures'][0]['professor'], '教授A')
        self.assertFalse(self.target_path.exists())
        self.assertEqual(self.read_target(self.b_target_path())['professor'], '教授B')
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_bulk_migration_own_invalid_candidate_blocks_its_group(self):
        """An identity-reliable record whose content fails validation keeps its
        professor and blocks that professor's bulk write, exactly like first
        establishment: zero write for the professor, one failed outcome — never
        migrated and failed at once — while other professors continue."""
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        a_target = self.read_target()
        b_preview = self.write_b_preview(fp="fp-b")
        mod.bootstrap_target(self.root, b_preview,
                             {"direction_ids": ["dir_A"], "notes": {"dir_A": "note B"}},
                             selected_at=BOOTSTRAP_AT)
        b_target = self.read_target(self.b_target_path())
        self.target_path.unlink()
        self.b_target_path().unlink()
        self.write_legacy(
            self.a_entry(a_target, selection_history="not-an-array"),
            self.a_entry(a_target),
            legacy_entry(b_target, str(PROFESSOR_B_DIR), str(PROFESSOR_B_DIR / PREVIEW_NAME)))
        legacy_before = self.legacy_path.read_bytes()
        result = mod.migrate_legacy_targets(self.root)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["migrated"], ["教授B"])
        self.assertEqual([item["professor"] for item in result["failures"]], ["教授A"])
        self.assertFalse(self.target_path.exists())
        self.assertEqual(self.read_target(self.b_target_path())["professor"], "教授B")
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_bootstrap_and_bulk_agree_on_invalid_own_candidate(self):
        """One migration semantics (r25 §5.2): the same legacy input reaches the
        same fail-closed verdict under the single-professor establishment entry
        and the bulk entry — the invalid own candidate is never demoted to an
        unattributable record that the remaining subset could migrate around."""
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        invalid_a = self.a_entry(selection_history="not-an-array")
        self.target_path.unlink()
        self.write_legacy(invalid_a)
        bootstrapped = self.bootstrap(["dir_A"], {"dir_A": "note A"}, selected_at=REVISION_AT)
        self.assertEqual(bootstrapped["status"], "error")
        self.assertEqual(bootstrapped["reason_code"], "invalid_legacy_candidate_state")
        self.assertFalse(self.target_path.exists())
        legacy_before = self.legacy_path.read_bytes()
        result = mod.migrate_legacy_targets(self.root)
        self.assertEqual(result["migrated"], [])
        self.assertEqual([item["professor"] for item in result["failures"]], ["教授A"])
        self.assertFalse(self.target_path.exists())
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_standalone_migration_never_publishes_materially_stale_selection(self):
        self.bootstrap()
        self.write_legacy(self.a_entry())
        self.target_path.unlink()
        changed = preview(fp='fp-new')
        changed['directions'][0]['members'] = [{'item_key': 'P9', 'preview_confidence': 'high'}]
        changed['directions'][0]['member_fingerprint'] = member_fingerprint(changed['directions'][0]['members'])
        write_json(self.preview_path, changed)
        before_paths = path_set(self.root)
        legacy_before = self.legacy_path.read_bytes()
        result = mod.migrate_legacy_targets(self.root)
        self.assertEqual(result['status'], 'partial')
        self.assertFalse(self.target_path.exists())
        self.assertEqual(path_set(self.root), before_paths)
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_bulk_migration_is_idempotent_and_keeps_legacy_untouched(self):
        self._legacy_fixture()
        first = mod.migrate_legacy_targets(self.root)
        legacy_before = self.legacy_path.read_bytes()
        a_before = self.target_path.read_bytes()
        second = mod.migrate_legacy_targets(self.root)
        self.assertEqual(second["already_migrated"], ["教授A"])
        self.assertEqual(second["migrated"], [])
        self.assertEqual(self.target_path.read_bytes(), a_before)
        self.assertEqual(self.legacy_path.read_bytes(), legacy_before)
        self.assertEqual(first["status"], second["status"])

    def test_issue64_t3_bulk_migration_merges_identical_entries_once(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        entry = self.a_entry()
        self.target_path.unlink()
        self.write_legacy(copy.deepcopy(entry), copy.deepcopy(entry))

        result = mod.migrate_legacy_targets(self.root)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["migrated"], ["教授A"])
        self.assertEqual([item["status"] for item in result["entries"]], ["migrated", "migrated"])
        self.assertEqual(self.read_target()["selection_history"], [])

    def test_issue64_t3_bulk_migration_never_overwrites_existing_local(self):
        self._legacy_fixture()
        mod.migrate_legacy_targets(self.root)
        different = self.read_target()
        different["directions"][0]["user_note"] = "本地已修订"
        write_json(self.target_path, different)
        before = self.target_path.read_bytes()

        result = mod.migrate_legacy_targets(self.root)

        self.assertEqual(result["status"], "partial")
        self.assertEqual([item["status"] for item in result["entries"]], ["conflict", "failed"])
        self.assertEqual(self.target_path.read_bytes(), before)
        self.assertEqual(self.resolve()["targets"][0]["directions"][0]["user_note"], "本地已修订")

    def test_issue64_t3_bulk_migration_conflicting_group_writes_nothing(self):
        self.bootstrap(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})
        entry_a = self.a_entry()
        conflicting = self.a_entry(selected_direction_ids=["dir_B"],
                                   directions=[copy.deepcopy(self.read_target()["directions"][1])])
        self.target_path.unlink()
        self.write_legacy(entry_a, conflicting)

        result = mod.migrate_legacy_targets(self.root)

        self.assertEqual(result["status"], "partial")
        self.assertEqual([item["status"] for item in result["entries"]], ["conflict", "conflict"])
        self.assertEqual(len(result["failures"]), 1)
        self.assertFalse(self.target_path.exists())

    def test_issue64_t3_bulk_migration_conflicting_carry_forward_state_writes_nothing(self):
        self.bootstrap(["dir_A"], {"dir_A": "note A"})
        entry = self.a_entry()
        self.target_path.unlink()

        variants = (
            ("selection_history", [{"marker": "different-history"}]),
            ("selected_at", "2025-12-31T23:59:59Z"),
        )
        for field, value in variants:
            with self.subTest(field=field):
                self.target_path.unlink(missing_ok=True)
                conflicting = copy.deepcopy(entry)
                conflicting[field] = value
                self.write_legacy(copy.deepcopy(entry), conflicting)
                legacy_before = self.legacy_path.read_bytes()

                result = mod.migrate_legacy_targets(self.root)

                self.assertEqual(result["status"], "partial")
                self.assertEqual([item["status"] for item in result["entries"]],
                                 ["conflict", "conflict"])
                self.assertFalse(self.target_path.exists())
                self.assertEqual(self.legacy_path.read_bytes(), legacy_before)

    def test_issue64_t3_bulk_migration_writes_nothing_for_unparseable_legacy(self):
        self.bootstrap(["dir_A"])
        entry = self.a_entry()
        self.target_path.unlink()
        legacy = json.dumps({"schema_version": 1, "kind": "professor-contact-targets",
                             "updated_at": None, "targets": [entry]},
                            ensure_ascii=False, indent=1)
        truncated = legacy[: len(legacy) // 2]
        self.legacy_path.write_text(truncated, encoding="utf-8")

        result = mod.migrate_legacy_targets(self.root)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason_code"], "legacy_unreadable")
        self.assertEqual(result["entries"], [])
        self.assertFalse(self.target_path.exists())
        self.assertEqual(self.legacy_path.read_text(encoding="utf-8"), truncated)

    def test_issue64_t3_bulk_migration_without_legacy_state_is_a_no_op(self):
        self.bootstrap(["dir_A"])
        before = self.target_path.read_bytes()
        result = mod.migrate_legacy_targets(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["reason_code"], "no_legacy_state")
        self.assertEqual(self.target_path.read_bytes(), before)

    # --- G64-T4: same display name, different canonical identity -----------

    def test_issue64_t4_same_display_name_professors_keep_separate_local_targets(self):
        first = self.bootstrap(["dir_A"], {"dir_A": "note A"})
        a2_preview = self.root / PROFESSOR_A2_DIR / PREVIEW_NAME
        write_json(a2_preview, preview(professor="教授A", fp="fp-a2"))
        second = mod.bootstrap_target(self.root, a2_preview,
                                      {"direction_ids": ["dir_B"], "notes": {"dir_B": "note A2"}},
                                      selected_at=REVISION_AT)

        self.assertEqual(second["status"], "ok")
        self.assertEqual(first["professor"], "教授A")
        self.assertEqual(second["professor"], "教授A")
        self.assertNotEqual(Path(first["state_path"]).resolve(),
                            Path(second["state_path"]).resolve())
        other_path = a2_preview.parent / TARGET_NAME
        other = self.read_target(other_path)
        self.assertEqual(self.read_target()["selected_direction_ids"], ["dir_A"])
        self.assertEqual(other["selected_direction_ids"], ["dir_B"])
        self.assertEqual(self.read_target()["professor_dir"], str(PROFESSOR_A_DIR))
        self.assertEqual(other["professor_dir"], str(PROFESSOR_A2_DIR))
        self.assertEqual(self.read_target()["directions"][0]["user_note"], "note A")
        self.assertEqual(other["directions"][0]["user_note"], "note A2")

        self.assertEqual([t["professor_dir"] for t in self.resolve()["targets"]],
                         [str(PROFESSOR_A_DIR)])
        self.assertEqual([t["professor_dir"] for t in self.resolve(other_path)["targets"]],
                         [str(PROFESSOR_A2_DIR)])

    def test_issue64_t4_transaction_records_carry_canonical_identity(self):
        first = self.bootstrap(["dir_A"], {"dir_A": "note A"})
        a2_preview = self.root / PROFESSOR_A2_DIR / PREVIEW_NAME
        write_json(a2_preview, preview(professor="教授A", fp="fp-a2"))
        second = mod.bootstrap_target(self.root, a2_preview, {"direction_ids": ["dir_B"]},
                                      selected_at=REVISION_AT)

        for record in (first["transaction"], second["transaction"]):
            self.assertEqual(sorted(record), ["preview_path", "professor", "professor_dir",
                                              "target_state"])
        transaction_a = self.resolve()["transaction"]
        transaction_other = self.resolve(a2_preview.parent / TARGET_NAME)["transaction"]
        self.assertEqual(len({first["transaction"]["target_state"],
                              second["transaction"]["target_state"]}), 2)
        self.assertEqual(transaction_a, first["transaction"])
        self.assertEqual(transaction_other["target_state"], second["transaction"]["target_state"])
        self.assertEqual({transaction_a["professor"], transaction_other["professor"]}, {"教授A"})
        self.assertNotEqual(transaction_a["professor_dir"], transaction_other["professor_dir"])
        self.assertNotEqual(transaction_a["preview_path"], transaction_other["preview_path"])

        revised = self.select(["dir_A", "dir_B"], {"dir_A": "note A"})
        self.assertEqual(revised["transaction"], transaction_a)


if __name__ == "__main__":
    unittest.main()
