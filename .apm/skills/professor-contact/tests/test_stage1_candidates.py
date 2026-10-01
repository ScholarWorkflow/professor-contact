import contextlib
import importlib.util
import io
import json
import os
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from issue64_test_support import path_set

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


def snapshot_path(root: Path, professor: str = "教授A") -> Path:
    """One professor's own authoritative Stage-1 state file."""
    return root / "教授研究" / "lab" / professor / "套磁阶段1候选.json"


def legacy_table_path(root: Path) -> Path:
    return root / "教授研究" / "套磁目标.json"


def legacy_aggregate_path(root: Path) -> Path:
    """The retired program-level Stage-1 aggregate, only reachable by migrate-legacy."""
    return root / "教授研究" / "套磁阶段1候选.json"


def legacy_entry(state: dict) -> dict:
    """One v1 aggregate entry rebuilt from the professor-local v2 file it produced."""
    return {key: value for key, value in state.items()
            if key not in {"schema_version", "kind", "expansion_policy"}}


def target_file(root: Path, professor: str = "教授A") -> Path:
    """Authoritative professor-local Stage-0 target used by the Stage-1 caller."""
    return root / "教授研究" / "lab" / professor / "套磁目标.json"


def build(root: Path, target: Path | None = None, named=None):
    named_path = None
    if named is not None:
        named_path = root / "教授研究" / "_named_input.json"
        write_json(named_path, named)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = stage1.build_command(root, target or target_file(root), named_path)
    # build_command only emits to stdout on the resolve-failure soft-exit path.
    emitted = json.loads(out.getvalue()) if out.getvalue().strip() else result
    return result, emitted


class ForbiddenAuthorityGuard:
    """Record filesystem access to state that must stay foreign to one professor.

    Existence checks, metadata, content and mutation access all count, plus any
    directory enumeration that actually yields one of the forbidden entries.
    Building a path string is not an access: only the syscall layer is wrapped.
    """

    _PATH_ARGS = {
        "stat": (0,), "lstat": (0,), "open": (0,), "remove": (0,), "unlink": (0,),
        "rename": (0, 1), "replace": (0, 1), "mkdir": (0,), "makedirs": (0,),
        "rmdir": (0,), "utime": (0,), "chmod": (0,), "link": (0, 1),
        "symlink": (0, 1), "readlink": (0,), "access": (0,),
    }

    def __init__(self, forbidden):
        self.targets = set()
        for path in forbidden:
            literal = os.path.abspath(os.fspath(path))
            self.targets.add(literal)
            self.targets.add(os.path.realpath(literal))
        self.accesses: list[str] = []
        self._restore = []

    def _spellings(self, value):
        try:
            text = os.fspath(value)
        except TypeError:
            return ()
        if isinstance(text, bytes):
            text = os.fsdecode(text)
        if not isinstance(text, str) or not text:
            return ()
        literal = os.path.abspath(text)
        return (literal,) if literal in self.targets else ()

    def _record(self, operation, value):
        if self._spellings(value):
            self.accesses.append(f"{operation} {value}")

    def __enter__(self):
        import builtins

        for name, indexes in self._PATH_ARGS.items():
            original = getattr(os, name)
            setattr(os, name, self._path_proxy(original, name, indexes))
            self._restore.append((os, name, original))
        for name in ("listdir", "scandir"):
            original = getattr(os, name)
            setattr(os, name, self._enum_proxy(original, name))
            self._restore.append((os, name, original))
        for module, label in ((io, "io.open"), (builtins, "open")):
            original = module.open
            setattr(module, "open", self._path_proxy(original, label, (0,)))
            self._restore.append((module, "open", original))
        self._restore.append((Path, "open", Path.open))
        Path.open = self._path_proxy(Path.open, "Path.open", (0,))
        return self

    def __exit__(self, exc_type, exc, tb):
        for module, name, original in reversed(self._restore):
            setattr(module, name, original)
        self._restore = []
        return False

    def _path_proxy(self, original, operation, indexes):
        def proxy(*args, **kwargs):
            for index in indexes:
                if index < len(args):
                    self._record(operation, args[index])
            for name in ("src", "dst", "path", "file", "filename"):
                if name in kwargs:
                    self._record(operation, kwargs[name])
            return original(*args, **kwargs)
        return proxy

    def _enum_proxy(self, original, operation):
        recorded = self._record

        def hits(base, name):
            return recorded(f"{operation}:{base}", f"{base}/{name}")

        def proxy(path, *args, **kwargs):
            base = os.path.abspath(os.fspath(path))
            result = original(path, *args, **kwargs)
            if operation == "listdir":
                names = list(result)
                for name in names:
                    hits(base, name)
                return names

            def yielded():
                with result as iterator:
                    for entry in iterator:
                        hits(base, entry.name)
                        yield entry
            return yielded()
        return proxy


def professor_local_state(professor_dir: Path) -> Path:
    return Path(professor_dir) / "套磁阶段1候选.json"


def same_name_professor(
    root: Path, group: str, fingerprint: str, *, professor: str | None = None
) -> Path:
    """Build one professor; preserve the same-name fixture when no name is supplied."""
    display = professor if professor is not None else "教授同名"
    professor_dir = root / "教授研究" / group / display
    preview = professor_dir / "方向预筛.json"
    write_json(preview, preview_payload(professor=display, fp=fingerprint))
    catalog = papers_payload()
    if professor is not None:
        catalog["professor"]["name"] = display
    write_json(professor_dir / "papers.json", catalog)
    targets.select_target(
        root, preview, {"direction_ids": ["dir_A"], "notes": {}},
        selected_at="2026-09-29T00:00:00Z",
    )
    return professor_dir


class Stage1CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.preview_path = self.root / "教授研究" / "lab" / "教授A" / "方向预筛.json"
        self.papers_path = self.root / "教授研究" / "lab" / "教授A" / "papers.json"
        self.target_file = target_file(self.root)
        write_json(self.preview_path, preview_payload())
        write_json(self.papers_path, papers_payload())
        targets.bootstrap_target(
            self.root,
            self.preview_path,
            {"direction_ids": ["dir_A", "dir_B"], "notes": {}},
            selected_at="2026-09-04T00:00:00Z",
        )
        self.guarded = [
            self.target_file,
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
        entry = snap
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
        entry = snap
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
        target_state = read_json(self.target_file)
        selected_ids = target_state["selected_direction_ids"]
        self.assertEqual(selected_ids, ["dir_A", "dir_B"])
        self.assert_guards_untouched()

    def test_unplaced_paper_with_overlap_joins_and_unrelated_one_stays_out(self):
        result, _ = build(self.root)
        snap = read_json(snapshot_path(self.root))
        by_dir = {d["direction_id"]: d for d in snap["directions"]}
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
        by_dir = {d["direction_id"]: d for d in snap["directions"]}
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
        by_dir = {d["direction_id"]: d for d in snap["directions"]}
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
        self.assertEqual(snap["action"], "noop")

    def test_only_missing_keys_are_queued_for_targeted_fill(self):
        result, _ = build(self.root)
        snap = read_json(snapshot_path(self.root))
        entry = snap
        downloaded = set(entry["work_queue_item_keys"]) - set(entry["missing_item_keys"])
        self.assertEqual(downloaded, {"P1"})
        # The work queue is the union/dedup of candidate keys; the fill list is its
        # not-yet-usable subset — exactly what goes to the item-scoped pdf_only call.
        self.assertEqual(
            sorted(set(entry["work_queue_item_keys"]) & set(entry["missing_item_keys"])),
            entry["missing_item_keys"],
        )

    def test_named_papers_join_candidates_and_unmatched_are_reported(self):
        # The input fingerprint binds the dependency inputs (preview/papers/
        # targets); the named overlay itself must never enter it, while the
        # named papers still land in the candidate sets and reasons.
        build(self.root)
        plain_fingerprint = read_json(snapshot_path(self.root))["input_fingerprint"]
        named = {"directions": {"dir_B": ["P5"], "dir_A": ["Sparse Sensing Networks", "No Such Paper Anywhere"]}}
        result, _ = build(self.root, named=named)
        self.assertEqual(
            read_json(snapshot_path(self.root))["input_fingerprint"],
            plain_fingerprint,
        )
        by_dir = {d["direction_id"]: d for d in read_json(snapshot_path(self.root))["directions"]}
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
        fingerprint = snap["input_fingerprint"]
        second, _ = build(self.root)
        snap2 = read_json(snapshot_path(self.root))
        self.assertEqual(snap2["input_fingerprint"], fingerprint)
        self.assertEqual(snap2["missing_item_keys"], ["P2", "P3", "P5", "P8"])

        data = read_json(self.papers_path)
        for p in data["papers"]:
            if p["item_key"] == "P2":
                p["pdf_status"] = "downloaded"
        write_json(self.papers_path, data)
        third, payload = build(self.root)
        self.assertNotIn("P2", payload["missing_item_keys"])
        snap3 = read_json(snapshot_path(self.root))
        self.assertNotEqual(snap3["input_fingerprint"], fingerprint)

    def test_selected_membership_change_blocks_stage1(self):
        preview = preview_payload(fp="fp-new")
        preview["directions"][0]["members"].append({"item_key": "P9", "preview_confidence": "low"})
        write_json(self.preview_path, preview)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.build_command(self.root, self.target_file, None)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"], "needs_refresh")
        self.assertEqual(payload["reason_code"], "preview_changed")

    def test_snapshot_marks_membership_non_final_and_leaves_other_professors_alone(self):
        preview_b_path = self.root / "教授研究" / "lab" / "教授B" / "方向预筛.json"
        write_json(preview_b_path, preview_payload(professor="教授B", fp="fp-b"))
        papers_b_path = self.root / "教授研究" / "lab" / "教授B" / "papers.json"
        payload_b = papers_payload()
        payload_b["professor"] = {"name": "教授B"}
        write_json(papers_b_path, payload_b)
        targets.bootstrap_target(
            self.root,
            preview_b_path,
            {"direction_ids": ["dir_B"], "notes": {}},
            selected_at="2026-09-04T00:00:02Z",
        )
        build(self.root)
        build(self.root, target_file(self.root, "教授B"))
        snap = read_json(snapshot_path(self.root))
        self.assertEqual(snap["kind"], "professor-contact-stage1")
        self.assertEqual(snap["membership_claim"], "non_final_candidates_only")
        self.assertNotIn("professors", snap)
        self.assertEqual(snap["professor"], "教授A")
        self.assertEqual(read_json(snapshot_path(self.root, "教授B"))["professor"], "教授B")
        b_before = snapshot_path(self.root, "教授B").read_bytes()
        rebuilt_a, _ = build(self.root)
        self.assertEqual(rebuilt_a["professors"], ["教授A"])
        self.assertEqual(snapshot_path(self.root, "教授B").read_bytes(), b_before)
        self.assertEqual(read_json(snapshot_path(self.root))["professor"], "教授A")

    def test_issue64_t5_same_display_name_professors_keep_separate_snapshot_entries(self):
        """G64-T5: Stage 1 merges and verifies by canonical local identity only."""
        a2_dir = self.root / "教授研究" / "other-lab" / "教授A"
        a2_preview = a2_dir / "方向预筛.json"
        write_json(a2_preview, preview_payload(fp="fp-a2"))
        a2_papers = a2_dir / "papers.json"
        write_json(a2_papers, papers_payload())
        a2_target = a2_dir / "套磁目标.json"
        targets.bootstrap_target(
            self.root, a2_preview, {"direction_ids": ["dir_C"], "notes": {}},
            selected_at="2026-09-04T00:00:05Z")

        first, _ = build(self.root)
        self.assertEqual(first["professors"], ["教授A"])
        build(self.root, a2_target)
        snap = read_json(snapshot_path(self.root))
        self.assertEqual([item["professor"] for item in snap["professors"]], ["教授A", "教授A"])
        self.assertEqual(
            [item["professor_dir"] for item in snap["professors"]],
            ["教授研究/lab/教授A", "教授研究/other-lab/教授A"])

        rebuilt, _ = build(self.root)
        self.assertEqual(rebuilt["per_target"][0]["preview_path"], "教授研究/lab/教授A/方向预筛.json")
        snap2 = read_json(snapshot_path(self.root))
        self.assertEqual(len(snap2["professors"]), 2)
        self.assertEqual(snap2["professors"][1], snap["professors"][1])
        self.assertEqual(snap2["professors"][0]["input_fingerprint"],
                         snap["professors"][0]["input_fingerprint"])

        # Only the sibling's own inputs drift: verifying A must still hit A's entry.
        data = read_json(a2_papers)
        for item in data["papers"]:
            item["pdf_status"] = "downloaded"
        write_json(a2_papers, data)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, self.target_file)["status"], "ok")

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, a2_target)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["reason_code"], "stale_stage1_snapshot")
        self.assertEqual(
            payload["stale_professors"],
            [{"professor": "教授A", "professor_dir": "教授研究/other-lab/教授A",
              "preview_path": "教授研究/other-lab/教授A/方向预筛.json",
              "problems": ["input_fingerprint_mismatch"]}])

    def test_issue64_t5_same_display_name_missing_entry_names_its_own_professor_dir(self):
        a2_dir = self.root / "教授研究" / "other-lab" / "教授A"
        a2_preview = a2_dir / "方向预筛.json"
        write_json(a2_preview, preview_payload(fp="fp-a2"))
        write_json(a2_dir / "papers.json", papers_payload())
        a2_target = a2_dir / "套磁目标.json"
        targets.bootstrap_target(
            self.root, a2_preview, {"direction_ids": ["dir_C"], "notes": {}},
            selected_at="2026-09-04T00:00:06Z")
        build(self.root)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, a2_target)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["reason_code"], "professor_missing_from_snapshot")
        self.assertEqual(payload["professor_dir"], "教授研究/other-lab/教授A")

    def test_cli_build_writes_snapshot_and_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "build", "--program-root", str(self.root),
             "--target-file", str(self.target_file)],
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
        self.assertEqual(snap["action"], "needs_resolution")

    def test_verify_accepts_a_fresh_snapshot_without_writing(self):
        build(self.root)
        before = snapshot_path(self.root).read_bytes()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = stage1.verify_command(self.root, self.target_file)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["professors"], ["教授A"])
        self.assertEqual(snapshot_path(self.root).read_bytes(), before)

    def test_verify_reports_missing_snapshot_and_stale_states(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, self.target_file)
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
                stage1.verify_command(self.root, self.target_file)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["reason_code"], "stale_stage1_snapshot")
        self.assertEqual(
            payload["stale_professors"],
            [{"professor": "教授A", "professor_dir": "教授研究/lab/教授A",
              "preview_path": "教授研究/lab/教授A/方向预筛.json",
              "problems": ["input_fingerprint_mismatch"]}],
        )

    def test_verify_forwards_preview_refresh_and_missing_local_state(self):
        build(self.root)
        preview = preview_payload(fp="fp-new")
        preview["directions"][0]["members"].append({"item_key": "P9", "preview_confidence": "low"})
        write_json(self.preview_path, preview)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, self.target_file)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(json.loads(out.getvalue())["reason_code"], "preview_changed")

        write_json(self.preview_path, preview_payload())
        preview_b_path = self.root / "教授研究" / "lab" / "教授B" / "方向预筛.json"
        write_json(preview_b_path, preview_payload(professor="教授B", fp="fp-b"))
        papers_b_path = self.root / "教授研究" / "lab" / "教授B" / "papers.json"
        payload_b = papers_payload()
        payload_b["professor"] = {"name": "教授B"}
        write_json(papers_b_path, payload_b)
        targets.bootstrap_target(
            self.root,
            preview_b_path,
            {"direction_ids": ["dir_B"], "notes": {}},
            selected_at="2026-09-04T00:00:04Z",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, target_file(self.root, "教授B"))
        self.assertEqual(ctx.exception.code, 2)
        # A's own build left no state for B and B has none: a missing local state is
        # reported as missing, never as a lookup failure inside another professor's file.
        rejected = json.loads(out.getvalue())
        self.assertEqual(rejected["reason_code"], "missing_stage1_snapshot")
        self.assertTrue(
            rejected["snapshot_path"].endswith(
                str(Path("教授研究") / "lab" / "教授B" / "套磁阶段1候选.json")),
            rejected["snapshot_path"],
        )
        self.assertFalse(snapshot_path(self.root, "教授B").exists())

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
        self.assertEqual(snap["action"], "noop")
        self.assertEqual(snap["missing_item_keys"], [])

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            verified = stage1.verify_command(self.root, self.target_file)
        self.assertEqual(verified["status"], "ok")

    def test_unselected_direction_change_stales_the_candidate_snapshot(self):
        # Stage 1 expansion consumes ALL preview directions (cross-direction gates,
        # low-confidence reasons, unplaced detection), while target freshness
        # deliberately tolerates unselected-direction changes. The snapshot's
        # preview_digest must catch exactly that drift: resolve stays ok, verify
        # must demand a rebuild, and the rebuilt candidate set must reflect the
        # new preview reality. Covers the review scenario where an unselected
        # direction gains a new high-confidence member (membership/confidence
        # change): the member becomes "placed elsewhere" for the selected
        # direction and must clear the strict cross-direction gate.
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
        self.assertIn("input_fingerprint", snap)
        self.assertNotIn("preview_digest", snap)
        by_dir = {d["direction_id"]: d for d in snap["directions"]}
        self.assertIn("P7", by_dir["dir_A"]["candidate_keys"])
        self.assertEqual(
            by_dir["dir_A"]["expansion_reasons"]["P7"],
            ["unclassified_or_new_since_preview"],
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, self.target_file)["status"], "ok")

        # P7 joins UNSELECTED dir_B as a high-confidence member: for dir_A it is now
        # placed elsewhere and must clear the strict gate, which 0.4 coverage fails.
        preview = preview_payload()
        preview["directions"][1]["members"].append({"item_key": "P7", "preview_confidence": "high"})
        write_json(self.preview_path, preview)

        resolution = targets.resolve_target(self.target_file, self.root)
        self.assertEqual(resolution["status"], "ok")  # target freshness intentionally passes

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.verify_command(self.root, self.target_file)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["reason_code"], "stale_stage1_snapshot")
        self.assertEqual(
            payload["stale_professors"],
            [{"professor": "教授A", "professor_dir": "教授研究/lab/教授A",
              "preview_path": "教授研究/lab/教授A/方向预筛.json",
              "problems": ["input_fingerprint_mismatch"]}],
        )

        build(self.root)
        snap = read_json(snapshot_path(self.root))
        by_dir = {d["direction_id"]: d for d in snap["directions"]}
        self.assertNotIn("P7", by_dir["dir_A"]["candidate_keys"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, self.target_file)["status"], "ok")

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
            self.assertEqual(stage1.verify_command(self.root, self.target_file)["status"], "ok")
        before = read_json(snapshot_path(self.root))["input_fingerprint"]

        preview = preview_payload()
        # dir_B is unselected: change its display-only fields (name/summary/representative title).
        preview["directions"][1]["name_zh"] = "方向乙（已改名）"
        preview["directions"][1]["summary_zh"] = "乙方向简介（已改摘要）"
        for rep in preview["directions"][1].get("representatives", []):
            rep["title"] = rep.get("title", "") + " (renamed)"
        write_json(self.preview_path, preview)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, self.target_file)["status"], "ok")
        # Exact dependency fingerprint is unchanged → no rebuild needed.
        self.assertEqual(
            read_json(snapshot_path(self.root))["input_fingerprint"],
            before,
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
                stage1.verify_command(self.root, self.target_file)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(
            json.loads(out.getvalue())["stale_professors"],
            [{"professor": "教授A", "professor_dir": "教授研究/lab/教授A",
              "preview_path": "教授研究/lab/教授A/方向预筛.json",
              "problems": ["input_fingerprint_mismatch"]}],
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
                stage1.verify_command(self.root, self.target_file)
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(
            json.loads(out.getvalue())["stale_professors"],
            [{"professor": "教授A", "professor_dir": "教授研究/lab/教授A",
              "preview_path": "教授研究/lab/教授A/方向预筛.json",
              "problems": ["input_fingerprint_mismatch"]}],
        )

    def test_non_candidate_pdf_status_change_keeps_snapshot_valid(self):
        # Review follow-up 1: pdf_status is only fingerprinted for the candidate
        # union. P6 is unrelated to selected dir_A and never enters the candidate
        # set, so flipping only P6 pdf_status cannot change candidate membership,
        # work_queue_item_keys, missing/usable readiness, or any Stage-2 input.
        self._build_selected_a()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, self.target_file)["status"], "ok")
        before = read_json(snapshot_path(self.root))["input_fingerprint"]

        data = read_json(self.papers_path)
        for p in data["papers"]:
            if p["item_key"] == "P6":
                p["pdf_status"] = "downloaded"
        write_json(self.papers_path, data)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, self.target_file)["status"], "ok")
        self.assertEqual(
            read_json(snapshot_path(self.root))["input_fingerprint"],
            before,
        )

    def test_whole_preview_fingerprint_change_without_dependency_drift_keeps_valid(self):
        # Review follow-up 2 (corrected): the old gate became harmful when
        # contact_targets.resolve_targets() refreshed the selected target projection
        # (e.g. selected direction coverage_share) and therefore rewrote
        # target.preview_fingerprint, even though Stage 1 does not consume that
        # display-only field. This test exercises that exact regression: change a
        # selected direction's non-Stage-1 projection field (coverage_share) AND the
        # top-level preview_fingerprint, assert resolve refreshes the projection, then
        # assert Stage-1 verify still stays ok.
        self._build_selected_a()
        before = read_json(snapshot_path(self.root))["input_fingerprint"]
        preview = preview_payload(fp="fp-new")
        # coverage_share is part of the selected-direction projection that resolve
        # refreshes in place; it is NOT consumed by Stage 1.
        preview["directions"][0]["coverage_share"] = 0.99
        write_json(self.preview_path, preview)

        resolution = targets.resolve_target(self.target_file, self.root)
        self.assertEqual(resolution["status"], "ok")
        # resolve refreshed the projection in place (target preview_fingerprint updated).
        self.assertEqual(
            read_json(self.target_file)["preview_fingerprint"],
            "fp-new",
        )

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, self.target_file)["status"], "ok")
        self.assertEqual(
            read_json(snapshot_path(self.root))["input_fingerprint"],
            before,
        )
        # Display-only preview drift must not block a fresh Stage-1 build either:
        # the rebuild proceeds against the same selected membership, with the
        # same dependency fingerprint and the same fill list.
        # The test itself rewrote the preview and resolve refreshed the target
        # projection, so re-baseline the guards here; the post-build check
        # below asserts build() never rewrites the upstream inputs itself.
        self.guarded_before = {p: p.read_bytes() for p in self.guarded}
        result, payload = build(self.root)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(result["action"], "pdf_fill_needed")
        self.assertEqual(result["missing_item_keys"], ["P2", "P5", "P8"])
        self.assertEqual(
            read_json(snapshot_path(self.root))["input_fingerprint"],
            before,
        )
        self.assert_guards_untouched()

    def test_issue64_t5_stage1_builds_and_verifies_from_the_local_target(self):
        """G64-T5: Stage 1 needs only A's professor-local Stage-0 target."""
        self.assertFalse(legacy_table_path(self.root).exists())
        before_paths = path_set(self.root / '教授研究')
        result, payload = build(self.root)
        self.assertEqual(path_set(self.root / '教授研究'),
                         before_paths | {'套磁阶段1候选.json'})
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(result["professors"], ["教授A"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            verified = stage1.verify_command(self.root, self.target_file)
        self.assertEqual(verified["status"], "ok")
        self.assertEqual(verified["professors"], ["教授A"])
        self.assertFalse(legacy_table_path(self.root).exists())
        self.assertEqual(path_set(self.root / '教授研究'), before_paths | {'套磁阶段1候选.json'})

    def test_issue64_t5_corrupt_legacy_table_is_not_a_stage1_input(self):
        build(self.root)
        legacy_table_path(self.root).write_text("{ corrupt legacy table", encoding="utf-8")
        before_paths = path_set(self.root / '教授研究')
        legacy_before = legacy_table_path(self.root).read_bytes()

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stage1.verify_command(self.root, self.target_file)["status"], "ok")
        result, payload = build(self.root)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(result["action"], "pdf_fill_needed")
        self.assertEqual(
            legacy_table_path(self.root).read_text(encoding="utf-8"), "{ corrupt legacy table")
        self.assertEqual(legacy_table_path(self.root).read_bytes(), legacy_before)
        self.assertEqual(path_set(self.root / '教授研究'), before_paths)

    def test_issue64_t5_stage1_never_falls_back_to_the_legacy_table(self):
        """Counterexample 6: a valid legacy table must not substitute for local state."""
        legacy_table_path(self.root).write_text(json.dumps({
            "schema_version": 1, "kind": "professor-contact-targets", "updated_at": None,
            "targets": [read_json(self.target_file)]}, ensure_ascii=False), encoding="utf-8")
        self.target_file.unlink()

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                stage1.build_command(self.root, self.target_file, None)
        self.assertEqual(ctx.exception.code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"], "needs_input")
        self.assertEqual(payload["reason_code"], "missing_target_state")

    def test_issue65_stage1_professor_local_authority_and_isolation(self):
        # C65-01: A's four formal Stage-1 operations never observe B's authority.
        # A and B share one display ``professor`` value on purpose: only the
        # canonical professor-local identity may separate their formal state.
        legacy_snapshot = self.root / "教授研究" / "套磁阶段1候选.json"
        a_dir = same_name_professor(self.root, "labA", "fp-a")
        b_dir = same_name_professor(self.root, "labB", "fp-b")
        a_state = professor_local_state(a_dir)
        b_state = professor_local_state(b_dir)
        a_target = a_dir / "套磁目标.json"
        b_target = b_dir / "套磁目标.json"
        self.assertNotEqual(a_target.resolve(), b_target.resolve())
        self.assertEqual(read_json(a_target)["professor"], read_json(b_target)["professor"])
        self.assertFalse(a_state.exists())

        build(self.root, b_target)
        self.assertTrue(
            b_state.is_file(),
            "B's own professor-local Stage-1 state is the required isolation input",
        )
        legacy_snapshot.write_text(
            json.dumps({"schema_version": 1, "kind": "professor-contact-stage1",
                        "updated_at": None, "professors": [],
                        "sentinel": "issue-65-legacy-aggregate-sentinel"},
                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

        def fingerprint(path: Path):
            raw = path.read_bytes() if path.is_file() else None
            return (path.is_file(), raw, hashlib.sha256(raw or b"").hexdigest())

        b_before = fingerprint(b_state)
        legacy_before = fingerprint(legacy_snapshot)
        self.assertNotEqual(b_before[1], legacy_before[1])
        a_directory = a_state.resolve().parent
        b_directory = b_state.resolve().parent

        guard = ForbiddenAuthorityGuard([b_state, legacy_snapshot])
        with guard:
            first, first_payload = build(self.root, a_target)
            self.assertEqual(first_payload["status"], "ok")
            self.assertEqual(first["action"], "pdf_fill_needed")
            self.assertEqual(first["professors"], ["教授同名"])
            self.assertTrue(a_state.is_file())
            a_reference = Path(first_payload["snapshot_path"])
            self.assertEqual(a_reference.parent, a_directory)
            # Lexical comparison against identities resolved before the guard opened:
            # touching B's path here would itself be a forbidden metadata access.
            self.assertNotEqual(a_reference.parent, b_directory)

            state = read_json(a_state)
            self.assertEqual(state["schema_version"], 2)
            self.assertEqual(state["kind"], "professor-contact-stage1")
            self.assertNotIn("professors", state)
            self.assertEqual(state["professor"], "教授同名")
            self.assertEqual(state["professor_dir"], str(Path("教授研究") / "labA" / "教授同名"))
            self.assertEqual(str(Path(state["preview_path"]).parent), state["professor_dir"])
            self.assertEqual(state["membership_claim"], "non_final_candidates_only")

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                verified = stage1.verify_command(self.root, a_target)
            self.assertEqual(verified["status"], "ok")

            again, again_payload = build(self.root, a_target)
            self.assertEqual(again_payload["status"], "ok")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                reverified = stage1.verify_command(self.root, a_target)
            self.assertEqual(reverified["status"], "ok")
        self.assertEqual(
            guard.accesses, [], f"forbidden Stage-1 authority accessed: {guard.accesses}")

        self.assertEqual(fingerprint(b_state), b_before)
        self.assertEqual(fingerprint(legacy_snapshot), legacy_before)
        self.assertEqual(read_json(a_state)["input_fingerprint"], state["input_fingerprint"])

    def test_migrate_legacy_lands_valid_entries_while_keeping_a_bad_entry_local(self):
        build(self.root)
        state_path = snapshot_path(self.root)
        original = read_json(state_path)
        state_path.unlink()
        aggregate = legacy_aggregate_path(self.root)
        write_json(aggregate, {
            "schema_version": 1, "kind": "professor-contact-stage1", "updated_at": None,
            "professors": [legacy_entry(original), {"professor": "教授B", "directions": []}],
        })
        aggregate_before = aggregate.read_bytes()

        result = stage1.migrate_legacy_command(self.root)

        self.assertEqual(result["status"], "partial", result)
        self.assertEqual([row["professor"] for row in result["migrated"]], ["教授A"])
        self.assertEqual(read_json(state_path), original)
        self.assertEqual([row["professor"] for row in result["errors"]], ["教授B"])
        self.assertTrue(result["errors"][0]["reason"])
        self.assertEqual(aggregate.read_bytes(), aggregate_before)

    def test_migrate_legacy_writes_nothing_when_the_legacy_root_is_not_a_v1_aggregate(self):
        build(self.root)
        state_path = snapshot_path(self.root)
        state_path.unlink()
        aggregate = legacy_aggregate_path(self.root)
        write_json(aggregate, {
            "schema_version": 1, "kind": "professor-contact-stage1",
            "professors": {"教授A": {}},
        })
        aggregate_before = aggregate.read_bytes()

        with self.assertRaises(ValueError):
            stage1.migrate_legacy_command(self.root)

        self.assertFalse(state_path.exists())
        self.assertEqual(aggregate.read_bytes(), aggregate_before)

    def test_migrate_legacy_never_overwrites_an_existing_professor_state(self):
        build(self.root)
        state_path = snapshot_path(self.root)
        before = state_path.read_bytes()
        entry = legacy_entry(read_json(state_path))
        entry["input_fingerprint"] = "0" * 64
        write_json(legacy_aggregate_path(self.root), {
            "schema_version": 1, "kind": "professor-contact-stage1", "updated_at": None,
            "professors": [entry],
        })

        result = stage1.migrate_legacy_command(self.root)

        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["migrated"], [])
        self.assertEqual([row["professor"] for row in result["skipped_existing"]], ["教授A"])
        self.assertEqual(state_path.read_bytes(), before)

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
