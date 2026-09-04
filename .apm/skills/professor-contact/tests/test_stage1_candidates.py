import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_stage1.py"
SPEC = importlib.util.spec_from_file_location("contact_stage1", SCRIPT)
stage1 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = stage1
assert SPEC.loader is not None
SPEC.loader.exec_module(stage1)

TARGETS_PATH = ROOT / "scripts" / "contact_targets.py"
TSPEC = importlib.util.spec_from_file_location("contact_targets_stage1_tests", TARGETS_PATH)
targets = importlib.util.module_from_spec(TSPEC)
sys.modules[TSPEC.name] = targets
assert TSPEC.loader is not None
TSPEC.loader.exec_module(targets)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def paper(item_key, title, status, year=2024):
    return {"item_key": item_key, "title": title, "year": year, "pdf_status": status}


def papers_payload():
    return {
        "professor": {"name": "教授A"},
        "papers": [
            paper("P1", "Adaptive Signal Processing for Sensor Networks", "downloaded"),
            paper("P2", "Sparse Sensing Networks", "no_env"),
            paper("P3", "Networked Estimation over Graphs", "pending"),
            paper("P4", "Kitchen Chemistry Experiments", "downloaded"),
            paper("P5", "Signal Processing for Underwater Sensor Arrays", "deferred", year=2025),
            paper("P6", "Deep Tank Aquaculture Systems", "pending"),
            paper("P8", "Robust Signal Processing for Wearable Sensor Networks", "failed", year=2023),
        ],
    }


def preview_payload(professor="教授A", fp="fp-a"):
    return {
        "schema_version": 1,
        "professor": professor,
        "direction_id_version": "members-v1",
        "membership_mode": "overlap_allowed",
        "membership_coverage": {
            "assigned_unique_members": 5,
            "membership_edges": 6,
            "overlap_member_count": 1,
            "overlap_members": ["P2"],
            "unassigned_mountable_count": 0,
        },
        "preview_fingerprint": fp,
        "preview_fingerprint_version": "preview-v1",
        "coverage": 0.8,
        "data_confidence": "high",
        "directions": [
            {
                "direction_id": "dir_A",
                "name_ja": "方向A",
                "name_zh": "方向甲",
                "summary_zh": "自适应信号处理与传感网络研究",
                "member_fingerprint": "mf-a",
                "members": [
                    {"item_key": "P1", "preview_confidence": "high"},
                    {"item_key": "P2", "preview_confidence": "low"},
                ],
                "low_confidence_count": 1,
                "coverage_share": 0.4,
                "representatives": [
                    {"item_key": "P1", "title": "Adaptive Signal Processing for Sensor Networks",
                     "title_zh": "传感器网络自适应信号处理", "year": 2024},
                ],
            },
            {
                "direction_id": "dir_B",
                "name_ja": "方向B",
                "name_zh": "方向乙",
                "summary_zh": "网络化估计与图上推断",
                "member_fingerprint": "mf-b",
                "members": [
                    {"item_key": "P2", "preview_confidence": "high"},
                    {"item_key": "P3", "preview_confidence": "high"},
                ],
                "low_confidence_count": 0,
                "coverage_share": 0.5,
                "representatives": [
                    {"item_key": "P3", "title": "Networked Estimation over Graphs", "year": 2025},
                ],
            },
            {
                "direction_id": "dir_C",
                "name_ja": "方向C",
                "name_zh": "方向丙",
                "summary_zh": "食品科学与厨房化学实验",
                "member_fingerprint": "mf-c",
                "members": [
                    {"item_key": "P4", "preview_confidence": "high"},
                    {"item_key": "P8", "preview_confidence": "high"},
                ],
                "low_confidence_count": 0,
                "coverage_share": 0.3,
                "representatives": [
                    {"item_key": "P8", "title": "Robust Signal Processing for Wearable Sensor Networks",
                     "year": 2023},
                ],
            },
        ],
    }


def snapshot_path(root: Path) -> Path:
    return root / "教授研究" / "套磁阶段1候选.json"


def build(root: Path, professors=None, named=None):
    named_path = None
    if named is not None:
        named_path = root / "教授研究" / "_named_input.json"
        write_json(named_path, named)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = stage1.build_command(root, professors, named_path)
    # build_command only emits to stdout on the resolve-failure soft-exit path.
    emitted = json.loads(out.getvalue()) if out.getvalue().strip() else result
    return result, emitted


class Stage1CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.preview_path = self.root / "教授研究" / "lab" / "教授A" / "方向预筛.json"
        self.papers_path = self.root / "教授研究" / "lab" / "教授A" / "papers.json"
        write_json(self.preview_path, preview_payload())
        write_json(self.papers_path, papers_payload())
        targets.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {}},
            selected_at="2026-09-04T00:00:00Z",
        )
        self.guarded = [
            self.root / "教授研究" / "套磁目标.json",
            self.preview_path,
            self.papers_path,
        ]
        self.guarded_before = {p: p.read_bytes() for p in self.guarded}

    def tearDown(self):
        self.tmp.cleanup()

    def assert_guards_untouched(self):
        for path, before in self.guarded_before.items():
            self.assertEqual(path.read_bytes(), before, f"{path.name} must not be modified by Stage 1")

    def test_selected_directions_keep_separate_candidate_sets_with_shared_paper_once(self):
        build(self.root)
        snap = read_json(snapshot_path(self.root))
        entry = snap["professors"][0]
        by_dir = {d["direction_id"]: d for d in entry["directions"]}
        self.assertEqual(set(by_dir), {"dir_A", "dir_B"})
        self.assertEqual(by_dir["dir_A"]["candidate_keys"], ["P1", "P2", "P5", "P8"])
        self.assertEqual(by_dir["dir_B"]["candidate_keys"], ["P2", "P3"])
        # Shared paper P2 stays in both per-direction sets but the physical work queue has it once.
        self.assertEqual(entry["work_queue_item_keys"], ["P1", "P2", "P3", "P5", "P8"])
        self.assertEqual(entry["work_queue_item_keys"].count("P2"), 1)
        self.assert_guards_untouched()

    def test_cross_direction_overlap_adds_paper_without_moving_membership(self):
        result, _ = build(self.root)
        snap = read_json(snapshot_path(self.root))
        entry = snap["professors"][0]
        by_dir = {d["direction_id"]: d for d in entry["directions"]}
        # P8 sits in preview direction C but strongly overlaps dir_A's cheap-evidence profile.
        self.assertIn("P8", by_dir["dir_A"]["candidate_keys"])
        self.assertIn("cross_direction_overlap", by_dir["dir_A"]["expansion_reasons"]["P8"])
        self.assertIn("matched_tokens", by_dir["dir_A"]["expansion_evidence"]["P8"])
        # P4 also lives in C but shows no overlap with A, so it stays out.
        self.assertNotIn("P4", by_dir["dir_A"]["candidate_keys"])
        # P3 (dir_B member, no overlap with A) must not leak into A.
        self.assertNotIn("P3", by_dir["dir_A"]["candidate_keys"])
        # Expansion never rewrites the preview or target state: C's membership is untouched.
        target_state = read_json(self.root / "教授研究" / "套磁目标.json")
        selected_ids = target_state["targets"][0]["selected_direction_ids"]
        self.assertEqual(selected_ids, ["dir_A", "dir_B"])
        self.assert_guards_untouched()

    def test_unplaced_paper_with_overlap_joins_and_unrelated_one_stays_out(self):
        result, _ = build(self.root)
        snap = read_json(snapshot_path(self.root))
        by_dir = {d["direction_id"]: d for d in snap["professors"][0]["directions"]}
        self.assertIn("P5", by_dir["dir_A"]["candidate_keys"])
        self.assertEqual(
            by_dir["dir_A"]["expansion_reasons"]["P5"],
            ["unclassified_or_new_since_preview"],
        )
        self.assertNotIn("P6", by_dir["dir_A"]["candidate_keys"])
        self.assertNotIn("P6", by_dir["dir_B"]["candidate_keys"])

    def test_low_confidence_own_member_records_evidence_reason(self):
        result, _ = build(self.root)
        snap = read_json(snapshot_path(self.root))
        by_dir = {d["direction_id"]: d for d in snap["professors"][0]["directions"]}
        self.assertEqual(
            by_dir["dir_A"]["expansion_reasons"]["P2"],
            ["provisional_member", "low_confidence_preview"],
        )
        self.assertEqual(by_dir["dir_B"]["expansion_reasons"]["P2"], ["provisional_member"])

    def test_downloaded_candidates_are_not_refilled(self):
        result, payload = build(self.root)
        self.assertEqual(result["action"], "pdf_fill_needed")
        self.assertEqual(result["missing_item_keys"], ["P2", "P3", "P5", "P8"])
        snap = read_json(snapshot_path(self.root))
        by_dir = {d["direction_id"]: d for d in snap["professors"][0]["directions"]}
        readiness_a = by_dir["dir_A"]["pdf_readiness"]
        self.assertEqual(readiness_a["usable_item_keys"], ["P1"])
        self.assertNotIn("P1", readiness_a["missing_item_keys"])
        self.assertEqual(readiness_a["status_counts"]["downloaded"], 1)
        self.assertEqual(readiness_a["status_counts"]["deferred"], 1)
        self.assert_guards_untouched()

    def test_all_candidates_downloaded_makes_stage1_a_noop(self):
        data = read_json(self.papers_path)
        statuses = {"P1": "downloaded", "P2": "downloaded", "P3": "downloaded",
                    "P4": "downloaded", "P5": "downloaded", "P6": "pending", "P8": "downloaded"}
        for p in data["papers"]:
            p["pdf_status"] = statuses[p["item_key"]]
        write_json(self.papers_path, data)
        result, _ = build(self.root)
        self.assertEqual(result["action"], "noop")
        self.assertEqual(result["missing_item_keys"], [])
        snap = read_json(snapshot_path(self.root))
        self.assertEqual(snap["professors"][0]["action"], "noop")

    def test_only_missing_keys_are_queued_for_targeted_fill(self):
        result, _ = build(self.root)
        snap = read_json(snapshot_path(self.root))
        entry = snap["professors"][0]
        downloaded = set(entry["work_queue_item_keys"]) - set(entry["missing_item_keys"])
        self.assertEqual(downloaded, {"P1"})
        # The work queue is the union/dedup of candidate keys; the fill list is its
        # not-yet-usable subset — exactly what goes to the item-scoped pdf_only call.
        self.assertEqual(
            sorted(set(entry["work_queue_item_keys"]) & set(entry["missing_item_keys"])),
            entry["missing_item_keys"],
        )

    def test_named_papers_join_candidates_and_unmatched_are_reported(self):
        named = {"directions": {"dir_B": ["P5"], "dir_A": ["Sparse Sensing Networks", "No Such Paper Anywhere"]}}
        result, _ = build(self.root, named=named)
        snap = read_json(snapshot_path(self.root))
        by_dir = {d["direction_id"]: d for d in snap["professors"][0]["directions"]}
        self.assertIn("P5", by_dir["dir_B"]["candidate_keys"])
        self.assertIn("user_named", by_dir["dir_B"]["expansion_reasons"]["P5"])
        self.assertIn("user_named", by_dir["dir_A"]["expansion_reasons"]["P2"])
        self.assertEqual(
            result["unmatched_named_entries"],
            [{"direction_id": "dir_A", "entry": "No Such Paper Anywhere"}],
        )

    def test_named_file_with_unknown_direction_id_is_rejected(self):
        named = {"directions": {"dir_Z": ["P1"]}}
        with self.assertRaises(ValueError):
            build(self.root, named=named)

    def test_missing_papers_json_is_an_error(self):
        self.papers_path.unlink()
        with self.assertRaises(FileNotFoundError):
            build(self.root)

    def test_candidate_missing_from_papers_json_is_unresolved_not_missing(self):
        preview = preview_payload()
        preview["directions"][0]["members"].append({"item_key": "P9", "preview_confidence": "high"})
        write_json(self.preview_path, preview)
        targets.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {}},
            selected_at="2026-09-04T00:00:01Z",
        )
        result, _ = build(self.root)
        self.assertIn("P9", result["unresolved_item_keys"])
        self.assertNotIn("P9", result["missing_item_keys"])

    def test_rebuild_is_stable_and_status_change_retries_fill(self):
        first, _ = build(self.root)
        snap = read_json(snapshot_path(self.root))
        fingerprint = snap["professors"][0]["input_fingerprint"]
        second, _ = build(self.root)
        snap2 = read_json(snapshot_path(self.root))
        self.assertEqual(snap2["professors"][0]["input_fingerprint"], fingerprint)
        self.assertEqual(snap2["professors"][0]["missing_item_keys"], ["P2", "P3", "P5", "P8"])

        data = read_json(self.papers_path)
        for p in data["papers"]:
            if p["item_key"] == "P2":
                p["pdf_status"] = "downloaded"
        write_json(self.papers_path, data)
        third, payload = build(self.root)
        self.assertNotIn("P2", payload["missing_item_keys"])
        snap3 = read_json(snapshot_path(self.root))
        self.assertNotEqual(snap3["professors"][0]["input_fingerprint"], fingerprint)

    def test_selected_membership_change_blocks_stage1(self):
        preview = preview_payload(fp="fp-new")
        preview["directions"][0]["members"].append({"item_key": "P9", "preview_confidence": "low"})
        write_json(self.preview_path, preview)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.build_command(self.root, None, None)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"], "needs_refresh")
        self.assertEqual(payload["reason_code"], "preview_changed")

    def test_display_only_preview_change_does_not_block_stage1(self):
        # Under the freshness contract a fingerprint/display-only preview change is
        # not a membership change: resolve refreshes projections in place and Stage 1
        # proceeds against the same selected membership.
        write_json(self.preview_path, preview_payload(fp="fp-new"))
        # The test itself rewrites the preview; guard against further build-time edits.
        self.guarded_before[self.preview_path] = self.preview_path.read_bytes()
        result, payload = build(self.root)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(result["action"], "pdf_fill_needed")
        self.assertEqual(result["missing_item_keys"], ["P2", "P3", "P5", "P8"])
        self.assert_guards_untouched()

    def test_snapshot_marks_membership_non_final_and_preserves_other_professors(self):
        preview_b_path = self.root / "教授研究" / "lab" / "教授B" / "方向预筛.json"
        write_json(preview_b_path, preview_payload(professor="教授B", fp="fp-b"))
        papers_b_path = self.root / "教授研究" / "lab" / "教授B" / "papers.json"
        payload_b = papers_payload()
        payload_b["professor"] = {"name": "教授B"}
        write_json(papers_b_path, payload_b)
        targets.select_target(
            self.root,
            preview_b_path,
            {"direction_ids": ["dir_B"], "notes": {}},
            selected_at="2026-09-04T00:00:02Z",
        )
        build(self.root)
        snap = read_json(snapshot_path(self.root))
        self.assertEqual(snap["kind"], "professor-contact-stage1")
        self.assertEqual(snap["membership_claim"], "non_final_candidates_only")
        self.assertEqual(
            [item["professor"] for item in snap["professors"]], ["教授A", "教授B"]
        )
        filtered, _ = build(self.root, professors=["教授A"])
        snap2 = read_json(snapshot_path(self.root))
        self.assertEqual(
            [item["professor"] for item in snap2["professors"]], ["教授A", "教授B"]
        )
        self.assertEqual(
            snap2["professors"][1]["input_fingerprint"],
            snap["professors"][1]["input_fingerprint"],
        )

    def test_cli_build_writes_snapshot_and_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "build", "--program-root", str(self.root)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["action"], "pdf_fill_needed")
        self.assertEqual(payload["missing_item_keys"], ["P2", "P3", "P5", "P8"])
        self.assertTrue(snapshot_path(self.root).is_file())

    def test_unresolved_candidates_block_the_noop_verdict(self):
        # Everything resolvable is downloaded; one provisional candidate (P9) is
        # absent from papers.json. "Every candidate has usable full text" is false,
        # so the action must not be noop.
        preview = preview_payload()
        preview["directions"][0]["members"].append({"item_key": "P9", "preview_confidence": "high"})
        write_json(self.preview_path, preview)
        targets.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {}},
            selected_at="2026-09-04T00:00:03Z",
        )
        data = read_json(self.papers_path)
        for p in data["papers"]:
            p["pdf_status"] = "downloaded"
        write_json(self.papers_path, data)
        result, _ = build(self.root)
        self.assertEqual(result["action"], "needs_resolution")
        self.assertEqual(result["missing_item_keys"], [])
        self.assertEqual(result["unresolved_item_keys"], ["P9"])
        snap = read_json(snapshot_path(self.root))
        self.assertEqual(snap["professors"][0]["action"], "needs_resolution")

    def test_named_input_does_not_change_the_input_fingerprint(self):
        _, _ = build(self.root)
        plain = read_json(snapshot_path(self.root))["professors"][0]["input_fingerprint"]
        build(self.root, named={"directions": {"dir_B": ["P5"]}})
        with_named = read_json(snapshot_path(self.root))["professors"][0]["input_fingerprint"]
        self.assertEqual(plain, with_named)
        # The named paper still lands in the candidate set and reasons.
        by_dir = {d["direction_id"]: d for d in read_json(snapshot_path(self.root))["professors"][0]["directions"]}
        self.assertIn("P5", by_dir["dir_B"]["candidate_keys"])
        self.assertIn("user_named", by_dir["dir_B"]["expansion_reasons"]["P5"])

    def test_verify_accepts_a_fresh_snapshot_without_writing(self):
        build(self.root)
        before = snapshot_path(self.root).read_bytes()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = stage1.verify_command(self.root, None)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["professors"], ["教授A"])
        self.assertEqual(snapshot_path(self.root).read_bytes(), before)

    def test_verify_reports_missing_snapshot_and_stale_states(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, None)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["reason_code"], "missing_stage1_snapshot")

        build(self.root)
        data = read_json(self.papers_path)
        for p in data["papers"]:
            if p["item_key"] == "P2":
                p["pdf_status"] = "downloaded"
        write_json(self.papers_path, data)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, None)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["reason_code"], "stale_stage1_snapshot")
        self.assertEqual(
            payload["stale_professors"],
            [{"professor": "教授A", "problems": ["input_fingerprint_mismatch"]}],
        )

    def test_verify_forwards_preview_refresh_and_missing_professor(self):
        build(self.root)
        preview = preview_payload(fp="fp-new")
        preview["directions"][0]["members"].append({"item_key": "P9", "preview_confidence": "low"})
        write_json(self.preview_path, preview)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, None)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(json.loads(out.getvalue())["reason_code"], "preview_changed")

        write_json(self.preview_path, preview_payload())
        preview_b_path = self.root / "教授研究" / "lab" / "教授B" / "方向预筛.json"
        write_json(preview_b_path, preview_payload(professor="教授B", fp="fp-b"))
        papers_b_path = self.root / "教授研究" / "lab" / "教授B" / "papers.json"
        payload_b = papers_payload()
        payload_b["professor"] = {"name": "教授B"}
        write_json(papers_b_path, payload_b)
        targets.select_target(
            self.root,
            preview_b_path,
            {"direction_ids": ["dir_B"], "notes": {}},
            selected_at="2026-09-04T00:00:04Z",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, None)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(json.loads(out.getvalue())["reason_code"], "professor_missing_from_snapshot")

    def test_fill_then_rebuild_then_verify_chain(self):
        # Simulates the Stage 1 → collector → snapshot refresh → Stage 2 verify chain:
        # build reports the missing keys, the fill flips papers.json, the rebuild
        # persists the post-fill readiness, and verify accepts the fresh snapshot.
        result, _ = build(self.root)
        self.assertEqual(result["action"], "pdf_fill_needed")
        self.assertEqual(result["missing_item_keys"], ["P2", "P3", "P5", "P8"])

        data = read_json(self.papers_path)
        for p in data["papers"]:
            if p["item_key"] in {"P2", "P3", "P5", "P8"}:
                p["pdf_status"] = "downloaded"
        write_json(self.papers_path, data)
        result, _ = build(self.root)
        self.assertEqual(result["action"], "noop")
        snap = read_json(snapshot_path(self.root))
        self.assertEqual(snap["professors"][0]["action"], "noop")
        self.assertEqual(snap["professors"][0]["missing_item_keys"], [])

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            verified = stage1.verify_command(self.root, None)
        self.assertEqual(verified["status"], "ok")

    def test_unselected_direction_change_stales_the_candidate_snapshot(self):
        # Stage 1 expansion consumes ALL preview directions (cross-direction gates,
        # low-confidence reasons, unplaced detection), while target freshness
        # deliberately tolerates unselected-direction changes. The snapshot's
        # preview_digest must catch exactly that drift: resolve stays ok, verify
        # must demand a rebuild, and the rebuilt candidate set must reflect the
        # new preview reality.
        targets.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A"], "notes": {}},
            selected_at="2026-09-04T00:05:00Z",
        )
        # P7 "Robust Sensor Array Calibration Networks": tokens {robust, sensor,
        # array, calibration, networks} → 2 matched vs dir_A, coverage 0.4 → passes
        # the relaxed unplaced gate but fails the strict cross-direction gate.
        data = read_json(self.papers_path)
        data["papers"].append(paper("P7", "Robust Sensor Array Calibration Networks", "pending"))
        write_json(self.papers_path, data)
        self.guarded_before[self.papers_path] = self.papers_path.read_bytes()

        build(self.root)
        snap = read_json(snapshot_path(self.root))
        self.assertIn("input_fingerprint", snap["professors"][0])
        self.assertNotIn("preview_digest", snap["professors"][0])
        by_dir = {d["direction_id"]: d for d in snap["professors"][0]["directions"]}
        self.assertIn("P7", by_dir["dir_A"]["candidate_keys"])
        self.assertEqual(
            by_dir["dir_A"]["expansion_reasons"]["P7"],
            ["unclassified_or_new_since_preview"],
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, None)["status"], "ok")

        # P7 joins UNSELECTED dir_B as a high-confidence member: for dir_A it is now
        # placed elsewhere and must clear the strict gate, which 0.4 coverage fails.
        preview = preview_payload()
        preview["directions"][1]["members"].append({"item_key": "P7", "preview_confidence": "high"})
        write_json(self.preview_path, preview)

        resolution = targets.resolve_targets(self.root)
        self.assertEqual(resolution["status"], "ok")  # target freshness intentionally passes

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, None)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["reason_code"], "stale_stage1_snapshot")
        self.assertEqual(
            payload["stale_professors"],
            [{"professor": "教授A", "problems": ["input_fingerprint_mismatch"]}],
        )

        build(self.root)
        snap = read_json(snapshot_path(self.root))
        by_dir = {d["direction_id"]: d for d in snap["professors"][0]["directions"]}
        self.assertNotIn("P7", by_dir["dir_A"]["candidate_keys"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, None)["status"], "ok")

    # --- Exact dependency fingerprint regression tests (issue #6 follow-up) ---

    def _build_selected_a(self):
        targets.select_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A"], "notes": {}},
            selected_at="2026-09-04T00:06:00Z",
        )
        build(self.root)

    def test_unselected_display_only_change_keeps_snapshot_valid(self):
        # Review scenario 1: an unselected direction rename/summary/representative-only
        # change that does NOT feed the selected direction's profile must keep verify ok.
        self._build_selected_a()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, None)["status"], "ok")
        before = read_json(snapshot_path(self.root))["professors"][0]["input_fingerprint"]

        preview = preview_payload()
        # dir_B is unselected: change its display-only fields (name/summary/representative title).
        preview["directions"][1]["name_zh"] = "方向乙（已改名）"
        preview["directions"][1]["summary_zh"] = "乙方向简介（已改摘要）"
        for rep in preview["directions"][1].get("representatives", []):
            rep["title"] = rep.get("title", "") + " (renamed)"
        write_json(self.preview_path, preview)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, None)["status"], "ok")
        # Exact dependency fingerprint is unchanged → no rebuild needed.
        self.assertEqual(
            read_json(snapshot_path(self.root))["professors"][0]["input_fingerprint"],
            before,
        )

    def test_unselected_membership_change_stales_snapshot(self):
        # Review scenario 2: unselected direction membership/confidence change that
        # affects Stage-1 placement/expansion inputs must invalidate.
        self._build_selected_a()
        preview = preview_payload()
        # Move P5 into unselected dir_B as a high-confidence member: for dir_A it is now
        # placed elsewhere and must clear the strict cross-direction gate.
        preview["directions"][1]["members"].append({"item_key": "P5", "preview_confidence": "high"})
        write_json(self.preview_path, preview)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, None)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(
            json.loads(out.getvalue())["stale_professors"],
            [{"professor": "教授A", "problems": ["input_fingerprint_mismatch"]}],
        )

    def test_selected_lexical_profile_change_stales_snapshot(self):
        # Review scenario 3: selected direction name/summary/representative title change
        # that can change overlap decisions must invalidate.
        self._build_selected_a()
        preview = preview_payload()
        preview["directions"][0]["summary_zh"] = "自适应信号处理与传感网络研究（已改）"
        write_json(self.preview_path, preview)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, None)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(
            json.loads(out.getvalue())["stale_professors"],
            [{"professor": "教授A", "problems": ["input_fingerprint_mismatch"]}],
        )

    def test_paper_title_zh_change_stales_snapshot(self):
        # Review scenario 4: paper title_zh change must invalidate when it can change
        # paper_tokens() (title_zh is consumed by Stage 1).
        self._build_selected_a()
        data = read_json(self.papers_path)
        for p in data["papers"]:
            if p["item_key"] == "P5":
                p["title_zh"] = "水下传感器阵列信号处理（已改）"
        write_json(self.papers_path, data)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, None)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(
            json.loads(out.getvalue())["stale_professors"],
            [{"professor": "教授A", "problems": ["input_fingerprint_mismatch"]}],
        )

    def test_whole_preview_fingerprint_change_without_dependency_drift_keeps_valid(self):
        # Review scenario 5: whole preview_fingerprint changes for unrelated
        # provenance/global fields (e.g. coverage) while exact Stage-1 dependencies are
        # unchanged → verify stays ok. This is the core improvement over the old
        # whole-preview gate.
        self._build_selected_a()
        before = read_json(snapshot_path(self.root))["professors"][0]["input_fingerprint"]
        preview = preview_payload()
        # coverage is part of upstream preview_fingerprint but NOT consumed by Stage 1.
        preview["coverage"] = 0.12
        write_json(self.preview_path, preview)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, None)["status"], "ok")
        self.assertEqual(
            read_json(snapshot_path(self.root))["professors"][0]["input_fingerprint"],
            before,
        )

    def test_pdf_readiness_change_still_invalidates(self):
        # Review scenario 6: existing PDF readiness change still invalidates/rebuilds.
        self._build_selected_a()
        data = read_json(self.papers_path)
        for p in data["papers"]:
            if p["item_key"] == "P2":
                p["pdf_status"] = "downloaded"
        write_json(self.papers_path, data)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, None)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(
            json.loads(out.getvalue())["stale_professors"],
            [{"professor": "教授A", "problems": ["input_fingerprint_mismatch"]}],
        )

    def test_agent_contract_delegates_only_item_scoped_fast_path(self):
        agent = (ROOT.parents[1] / "agents" / "professor-contact-downloader.agent.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("contact_stage1.py", agent)
        self.assertIn("item_keys", agent)
        self.assertIn("pdf_only: true", agent)
        self.assertIn("noop", agent)
        self.assertIn("套磁阶段1候选.json", agent)
        self.assertIn("non_final_candidates_only", agent)
        self.assertIn("never claims final direction membership", agent)
        # The old professor-level keep-list download call must be gone; the item-scoped
        # fast path is the only collector invocation Stage 1 may make.
        self.assertNotIn("professors: <comma-separated selected professor names>", agent)
        # Review fix: unresolved candidate keys must never yield a clean no-op.
        self.assertIn("needs_resolution", agent)
        self.assertIn("Never report a clean `ok` while unresolved keys remain", agent)
        # Review fix: the snapshot must be refreshed after the collector returns.
        self.assertIn("Refresh the snapshot after the collector returns", agent)
        self.assertIn("post-fill", agent)


if __name__ == "__main__":
    unittest.main()
