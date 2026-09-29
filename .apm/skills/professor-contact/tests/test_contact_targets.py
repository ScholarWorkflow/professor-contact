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

PROFESSOR_A_DIR = Path("教授研究") / "lab" / "教授A"
PROFESSOR_B_DIR = Path("教授研究") / "lab" / "教授B"
LEGACY_TABLE = Path("教授研究") / "套磁目标.json"


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
    """Stage-0 authority is one professor-local file: <professor_dir>/套磁目标.json."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.preview_path = self.root / PROFESSOR_A_DIR / "方向预筛.json"
        self.target_path = self.root / PROFESSOR_A_DIR / "套磁目标.json"
        write_json(self.preview_path, preview())

    def tearDown(self):
        self.tmp.cleanup()

    def select(self, direction_ids=("dir_A",), notes=None, selected_at="2026-09-03T12:00:00Z",
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

    def write_b_preview(self, **kwargs):
        path = self.root / PROFESSOR_B_DIR / "方向预筛.json"
        write_json(path, preview(professor="教授B", **kwargs))
        return path

    # --- R64-1: per-professor authority ------------------------------------

    def test_select_writes_one_professor_local_file(self):
        result = self.select(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})
        self.assertEqual(Path(result["state_path"]).resolve(),
                         (self.preview_path.parent / "套磁目标.json").resolve())
        self.assertFalse((self.root / LEGACY_TABLE).exists())
        state = self.read_target()
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["kind"], "professor-contact-target")
        self.assertNotIn("targets", state)
        self.assertEqual(state["selected_direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual(len(state["directions"]), 2)
        self.assertFalse((self.root / PROFESSOR_B_DIR / "套磁目标.json").exists())

    def test_selecting_a_and_b_keeps_separate_directions_with_overlap(self):
        result = self.select(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})
        self.assertEqual(result["selected_count"], 2)
        target = self.read_target()
        self.assertEqual(target["selected_direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual(len(target["directions"]), 2)
        members_a = {m["item_key"] for m in target["directions"][0]["members"]}
        members_b = {m["item_key"] for m in target["directions"][1]["members"]}
        self.assertIn("P2", members_a & members_b)
        self.assertEqual(target["directions"][0]["user_note"], "note A")
        self.assertEqual(target["directions"][1]["user_note"], "note B")

    # --- R64-2 / S0-ISO-1: A/B isolation -----------------------------------

    def test_s0_iso_1_malformed_sibling_target_does_not_block_or_change_a(self):
        """S0-ISO-1: B's malformed local state cannot touch A's select or resolve."""
        self.select(["dir_A"], {"dir_A": "note A"})
        b_preview = self.write_b_preview(fp="fp-b")
        mod.select_target(self.root, b_preview, {"direction_ids": ["dir_A"], "notes": {}},
                          selected_at="2026-09-03T12:01:00Z")
        b_target = self.root / PROFESSOR_B_DIR / "套磁目标.json"
        b_target.write_text("{ this is not json", encoding="utf-8")
        b_before = b_target.read_bytes()
        a_before = self.target_path.read_bytes()

        reselected = self.select(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"},
                                 selected_at="2026-09-03T12:02:00Z")
        self.assertEqual(reselected["status"], "ok")
        self.assertEqual(reselected["professor"], "教授A")
        resolved = self.resolve()
        self.assertEqual(resolved["status"], "ok")
        self.assertEqual([t["professor"] for t in resolved["targets"]], ["教授A"])
        self.assertEqual(resolved["professors"], ["教授A"])

        self.assertEqual(b_target.read_bytes(), b_before)
        self.assertNotEqual(self.target_path.read_bytes(), a_before)
        self.assertFalse((self.root / LEGACY_TABLE).exists())

    def test_reselection_reads_only_its_own_professor(self):
        """S0-ISO-1: A's history/notes come from A's own local file, never from B."""
        self.select(["dir_A", "dir_B"], {"dir_A": "old A", "dir_B": "old B"})
        self.write_b_preview(fp="fp-b")
        mod.select_target(self.root, self.root / PROFESSOR_B_DIR / "方向预筛.json",
                          {"direction_ids": ["dir_A"], "notes": {"dir_A": "prof B"}},
                          selected_at="2026-09-03T12:01:00Z")
        (self.root / PROFESSOR_B_DIR / "套磁目标.json").write_text("nope", encoding="utf-8")

        result = self.select(["dir_B"], selected_at="2026-09-03T12:02:00Z")

        self.assertEqual(result["status"], "ok")
        target = self.read_target()
        self.assertEqual(target["selected_direction_ids"], ["dir_B"])
        self.assertEqual(target["directions"][0]["user_note"], "old B")
        self.assertEqual(len(target["selection_history"]), 1)
        self.assertEqual(target["selection_history"][0]["selected_direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual((self.root / PROFESSOR_B_DIR / "套磁目标.json").read_text(encoding="utf-8"), "nope")

    def test_a_b_stage0_transactions_commit_independently(self):
        """S0-ISO-1 / R64-2: A succeeds and stays committed while B's own select fails."""
        self.select(["dir_A"], {"dir_A": "note A"})
        b_dir = self.root / PROFESSOR_B_DIR
        b_dir.mkdir(parents=True)
        (b_dir / "套磁目标.json").write_text("{ broken", encoding="utf-8")
        b_preview = self.write_b_preview(fp="fp-b")

        with self.assertRaises(ValueError):
            mod.select_target(self.root, b_preview, {"direction_ids": ["dir_A"], "notes": {}},
                              selected_at="2026-09-03T12:01:00Z")
        self.assertEqual(self.resolve()["status"], "ok")
        self.assertEqual(self.read_target()["directions"][0]["user_note"], "note A")
        self.assertEqual((b_dir / "套磁目标.json").read_text(encoding="utf-8"), "{ broken")

    # --- R64-7 / S0-ISO-7: preserved single-professor semantics ------------

    def test_revision_empty_string_note_clears_but_omitted_key_keeps_old_note(self):
        self.select(["dir_A", "dir_B"], {"dir_A": "old A", "dir_B": "old B"})
        self.select(["dir_A", "dir_B"], {"dir_A": ""}, selected_at="2026-09-03T12:01:00Z")
        notes = {d["direction_id"]: d["user_note"] for d in self.read_target()["directions"]}
        self.assertEqual(notes["dir_A"], "")
        self.assertEqual(notes["dir_B"], "old B")

    def test_resolve_tolerates_preview_fingerprint_only_change(self):
        """S0-ISO-2 positive regression: fingerprint-only drift stays resolvable."""
        self.select(["dir_A"], {"dir_A": "note A"})
        write_json(self.preview_path, preview(fp="fp-new"))
        result = self.resolve()
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("stale_targets", result)
        target = self.read_target()
        self.assertEqual(target["preview_fingerprint"], "fp-a")
        self.assertEqual(target["directions"][0]["user_note"], "note A")

    def test_resolve_ignores_unselected_direction_changes(self):
        base = preview()
        self.select(["dir_A"], {"dir_A": "note A"})
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
        self.assertEqual(target["directions"][0]["member_fingerprint"], base["directions"][0]["member_fingerprint"])

    def test_resolve_flags_only_materially_changed_selected_directions(self):
        base = preview()
        self.select(["dir_A", "dir_B"], {"dir_A": "note A", "dir_B": "note B"})
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

    def test_resolve_flags_removed_selected_direction(self):
        base = preview()
        self.select(["dir_A", "dir_B"])
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

    def test_resolve_refreshes_display_only_selected_direction_changes(self):
        self.select(["dir_A"], {"dir_A": "note A"})
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

    def test_resolve_filters_selected_professor(self):
        self.select(["dir_A"])
        ok = self.resolve(professors=["教授A"])
        self.assertEqual(ok["status"], "ok")
        self.assertEqual(ok["professors"], ["教授A"])
        missing = self.resolve(professors=["教授B"])
        self.assertEqual(missing["status"], "needs_input")
        self.assertEqual(missing["reason_code"], "professor_not_selected")

    def test_resolve_reports_needs_input_for_the_current_professor_only(self):
        self.select(["dir_A"])
        self.target_path.unlink()
        result = self.resolve()
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(result["reason_code"], "missing_target_state")
        self.assertEqual(Path(result["state_path"]).resolve(), self.target_path.resolve())
        self.assertEqual(result["targets"], [])

    def test_preview_summary_surfaces_ids_representatives_and_warnings(self):
        result = mod.preview_options(self.preview_path)
        self.assertEqual(result["professor"], "教授A")
        self.assertEqual([o["direction_id"] for o in result["options"]], ["dir_A", "dir_B"])
        self.assertEqual(result["options"][0]["representatives"][0]["item_key"], "P1")
        self.assertIn("1 member papers are low-confidence", result["options"][0]["warnings"])
        self.assertTrue(any("abstract coverage" in w for w in result["options"][0]["warnings"]))

    # --- R64-3 / S0-ISO-2: the selected professor still fails closed --------

    def test_s0_iso_2_invalid_local_target_state_fails_closed(self):
        """S0-ISO-2: A's own invalid state blocks A and never rewrites A."""
        self.select(["dir_A"], {"dir_A": "note A"})
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
                self.assertEqual(self.target_path.read_bytes(), before)
        self.assertFalse((self.root / LEGACY_TABLE).exists())

    def test_s0_iso_2_stored_professor_must_match_its_own_preview(self):
        """S0-ISO-2: identity drift against A's preview is the existing needs_refresh."""
        self.select(["dir_A"], {"dir_A": "note A"})
        write_json(self.target_path, {**self.read_target(), "professor": "教授C"})
        before = self.target_path.read_bytes()
        result = self.resolve()
        self.assertEqual(result["status"], "needs_refresh")
        self.assertEqual(result["stale_targets"][0]["reason"], "professor_changed")
        self.assertEqual(self.target_path.read_bytes(), before)

    def test_local_target_outside_the_research_directory_fails_closed(self):
        self.select(["dir_A"])
        stray_dir = self.root / "其他目录" / "教授A"
        write_json(stray_dir / "套磁目标.json", self.read_target())
        with self.assertRaises(ValueError):
            mod.resolve_target(stray_dir / "套磁目标.json", self.root)

    # --- R64-5 / S0-ISO-4: legacy is migration input only ------------------

    def test_s0_iso_4_legacy_table_changes_never_affect_local_runtime(self):
        """S0-ISO-4: after A has local state the legacy table is inert."""
        self.select(["dir_A"], {"dir_A": "note A"})
        write_json(self.root / LEGACY_TABLE, {
            "schema_version": 1, "kind": "professor-contact-targets", "updated_at": None,
            "targets": [legacy_entry(self.read_target(), "教授研究/lab/教授B",
                                     "教授研究/lab/教授B/方向预筛.json")]})
        resolved = self.resolve()
        self.assertEqual(resolved["status"], "ok")
        self.assertEqual(resolved["professors"], ["教授A"])
        self.assertEqual(resolved["targets"][0]["directions"][0]["user_note"], "note A")

        (self.root / LEGACY_TABLE).write_text("{ corrupt on purpose", encoding="utf-8")
        self.assertEqual(self.resolve()["professors"], ["教授A"])
        self.assertEqual((self.root / LEGACY_TABLE).read_text(encoding="utf-8"), "{ corrupt on purpose")

        (self.root / LEGACY_TABLE).unlink()
        self.assertEqual(self.resolve()["status"], "ok")
        self.assertFalse((self.root / LEGACY_TABLE).exists())

    # --- R64-4 / S0-ISO-3: independent legacy fan-out ----------------------

    def _legacy_fixture(self):
        self.select(["dir_A"], {"dir_A": "note A"})
        a_target = self.read_target()
        b_preview = self.write_b_preview(fp="fp-b")
        mod.select_target(self.root, b_preview, {"direction_ids": ["dir_A"], "notes": {"dir_A": "note B"}},
                          selected_at="2026-09-03T12:01:00Z")
        b_target = json.loads((self.root / PROFESSOR_B_DIR / "套磁目标.json").read_text(encoding="utf-8"))
        self.target_path.unlink()
        (self.root / PROFESSOR_B_DIR / "套磁目标.json").unlink()
        bad_b = legacy_entry(copy.deepcopy(b_target), "教授研究/lab/教授B", "教授研究/lab/教授B/方向预筛.json")
        bad_b["directions"] = []
        write_json(self.root / LEGACY_TABLE, {
            "schema_version": 1, "kind": "professor-contact-targets", "updated_at": None,
            "targets": [legacy_entry(a_target, "教授研究/lab/教授A", "教授研究/lab/教授A/方向预筛.json"),
                        bad_b]})

    def test_s0_iso_3_valid_entry_migrates_while_invalid_entry_fails(self):
        """S0-ISO-3: one parseable legacy table migrates A and reports B separately."""
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
        self.assertFalse((self.root / PROFESSOR_B_DIR / "套磁目标.json").exists())
        self.assertEqual(self.resolve()["status"], "ok")

    def test_s0_iso_3_migration_is_idempotent_and_keeps_legacy_untouched(self):
        self._legacy_fixture()
        first = mod.migrate_legacy_targets(self.root)
        legacy_before = (self.root / LEGACY_TABLE).read_bytes()
        a_before = self.target_path.read_bytes()
        second = mod.migrate_legacy_targets(self.root)
        self.assertEqual(second["already_migrated"], ["教授A"])
        self.assertEqual(second["migrated"], [])
        self.assertEqual(self.target_path.read_bytes(), a_before)
        self.assertEqual((self.root / LEGACY_TABLE).read_bytes(), legacy_before)
        self.assertEqual(first["status"], second["status"])

    def test_s0_iso_3_existing_local_target_is_never_overwritten_by_legacy(self):
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

    def test_unparseable_legacy_document_writes_nothing(self):
        """S0-ISO-3 boundary: without entry boundaries the whole document is rejected."""
        self.select(["dir_A"])
        entry = legacy_entry(self.read_target(), "教授研究/lab/教授A",
                             "教授研究/lab/教授A/方向预筛.json")
        self.target_path.unlink()
        legacy = json.dumps({"schema_version": 1, "kind": "professor-contact-targets",
                             "updated_at": None, "targets": [entry]},
                            ensure_ascii=False, indent=1)
        truncated = legacy[: len(legacy) // 2]
        (self.root / LEGACY_TABLE).write_text(truncated, encoding="utf-8")

        result = mod.migrate_legacy_targets(self.root)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason_code"], "legacy_unreadable")
        self.assertEqual(result["entries"], [])
        self.assertFalse(self.target_path.exists())
        self.assertEqual((self.root / LEGACY_TABLE).read_text(encoding="utf-8"), truncated)

    def test_migration_without_legacy_state_is_a_no_op(self):
        self.select(["dir_A"])
        before = self.target_path.read_bytes()
        result = mod.migrate_legacy_targets(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["reason_code"], "no_legacy_state")
        self.assertEqual(self.target_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
