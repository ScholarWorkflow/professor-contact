"""Deterministic contract tests for the issue #29 Stage 2 runtime fixture builder.

The builder (``tests/runtime/build_issue29_stage2_fixture.py``) is a
producer-owned test asset: it must reproduce the same machine structure for
the same mode, run every accepted/proof/fingerprint step through the repo's
deterministic runner, and validate the fixture with that same runner before
returning. Wall-clock timestamps, artifact-guard ``mtime_ns``/``ctime_ns``
stat values and the absolute program-root path are the only fields expected
to differ between two builds; everything else must be identical.
"""
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"
BUILDER_PATH = RUNTIME_DIR / "build_issue29_stage2_fixture.py"
CONTACT_STATE = TESTS_DIR.parent / "scripts" / "contact_state.py"

_spec = importlib.util.spec_from_file_location("build_issue29_stage2_fixture", BUILDER_PATH)
builder = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = builder
_spec.loader.exec_module(builder)

PROFESSOR = "試験 教授"
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
HEX64_RE = re.compile(r"\b[0-9a-f]{64}\b")
STAT_KEYS = ("mtime_ns", "ctime_ns")


def _normalize(value, root: Path):
    """Neutralize the only build-volatile fields.

    Fingerprints (sha256 hex) derive from content that embeds the absolute
    program root and wall-clock stamps by design, so every hex64 value is
    treated as volatile; wall-clock timestamps, artifact-guard stat
    nanoseconds, absolute paths and manifest hash rows follow the same rule.
    """
    if isinstance(value, dict):
        return {key: ("<stat-ns>" if key in STAT_KEYS else
                      "<sha>" if key == "sha256" else _normalize(value[key], root))
                for key in value}
    if isinstance(value, list):
        return [_normalize(item, root) for item in value]
    if isinstance(value, str):
        replaced = HEX64_RE.sub("<FP64>", TS_RE.sub("<UTC-TS>", value.replace(str(root), "<ROOT>")))
        return replaced
    return value


def _normalized_tree(root: Path) -> dict:
    tree = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if path.suffix == ".pdf":
            tree[relative] = path.read_bytes()
        elif path.suffix == ".json":
            payload = _normalize(json.loads(path.read_text(encoding="utf-8")), root)
            tree[relative] = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
        else:
            text = path.read_text(encoding="utf-8").replace(str(root), "<ROOT>")
            tree[relative] = HEX64_RE.sub("<FP64>", TS_RE.sub("<UTC-TS>", text))
    return tree


def _run_runner(*arguments):
    return subprocess.run([sys.executable, str(CONTACT_STATE), *map(str, arguments)],
                          text=True, capture_output=True, check=False, timeout=300)


def _runner_json(result):
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise AssertionError(
            f"runner stdout not JSON: {result.stdout!r}\nstderr: {result.stderr!r}")


def assert_minimal_pdf_structure(testcase: unittest.TestCase, pdf_bytes: bytes, title: str):
    text = pdf_bytes.decode("latin-1")
    testcase.assertTrue(pdf_bytes.startswith(b"%PDF-1.4\n"), "missing PDF header")
    startxref = int(text.rsplit("startxref", 1)[1].split()[0])
    xref_lines = text[startxref:].splitlines()
    testcase.assertEqual(xref_lines[0], "xref")
    object_count = int(xref_lines[1].split()[1])
    for number in range(1, object_count):
        offset = int(xref_lines[2 + number][:10])
        testcase.assertTrue(
            text[offset:].startswith(f"{number} 0 obj"),
            f"xref entry for object {number} does not resolve: offset {offset}")
    testcase.assertIn(title, text, "title text is not extractable stream content")
    testcase.assertIn("%%EOF", text)


class BuildIssue29Stage2FixtureTests(unittest.TestCase):
    maxDiff = None

    def build(self, mode):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = (Path(holder.name) / "case").resolve()
        manifest = builder.build_fixture(mode, root)
        return manifest, root

    # -- per-mode runner-validated contracts ---------------------------------

    def test_reuse_all_builds_the_accepted_state_contract(self):
        manifest, root = self.build("reuse_all")
        self.assertEqual(manifest["mode"], "reuse_all")
        self.assertEqual(manifest["expected_preflight_action"], "reuse_all")

        payload = _runner_json(_run_runner(
            "stage2-preflight", "--program-root", root, "--professor", PROFESSOR))
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["action"], "reuse_all", payload)
        self.assertEqual(payload["reason_codes"], [])

        prof_dir = root / "教授研究" / "X分野" / PROFESSOR
        pack = json.loads((prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        self.assertIn("preflight", pack["cache"])
        self.assertIn("validator", pack)

    def test_single_paper_builds_a_fresh_single_candidate_root(self):
        manifest, root = self.build("single_paper")
        self.assertEqual(manifest["expected_preflight_action"], "process")

        prof_dir = root / "教授研究" / "X分野" / PROFESSOR
        self.assertFalse((prof_dir / "套磁候选输入.json").exists())
        analysis_dir = prof_dir / "论文分析"
        self.assertEqual(list(analysis_dir.glob("*.md")), [])
        self.assertEqual(list(analysis_dir.glob("*.future_work.json")), [])

        facts = json.loads((root / "facts.json").read_text(encoding="utf-8"))
        self.assertEqual([p["item_key"] for p in facts["papers"]], ["AAAA1111"])
        paper = facts["papers"][0]
        self.assertNotIn("analysis_file", paper)
        self.assertNotIn("sidecar_file", paper)
        self.assertIn("pdf_file", paper)
        self.assertNotIn("AAAA1111", paper["title"])
        self.assertEqual(facts["directions"][0]["member_keys"], ["AAAA1111"])

        payload = _runner_json(_run_runner(
            "stage2-preflight", "--program-root", root, "--professor", PROFESSOR))
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("missing_input_pack", payload["reason_codes"])

        pdf_bytes = (analysis_dir / "AAAA1111.pdf").read_bytes()
        assert_minimal_pdf_structure(self, pdf_bytes, paper["title"])

    def test_material_pending_builds_the_canonical_proposed_state(self):
        manifest, root = self.build("material_pending")
        self.assertIsNone(manifest["expected_preflight_action"])

        prof_dir = root / "教授研究" / "X分野" / PROFESSOR
        self.assertFalse((prof_dir / "套磁候选输入.json").exists())
        sidecar = json.loads(
            (prof_dir / "论文分析" / "_resolved_directions.json").read_text(encoding="utf-8"))
        self.assertEqual(sidecar["directions"][0]["acceptance"], "proposed")
        self.assertEqual(sidecar["directions"][0]["provisional_direction_id"], "dir_A")

        payload = _runner_json(_run_runner(
            "stage2-resolve-plan", "--facts", root / "facts.json"))
        self.assertEqual(payload["status"], "ok", payload)
        # A pending material proposal stays unaccepted, so the resolve job
        # keeps being re-planned until the explicit user decision lands.
        self.assertEqual(payload["directions"][0]["action"], "process", payload)
        self.assertEqual(payload["directions"][0]["direction_id"], "dir_A")

    # -- builder obligations ---------------------------------------------------

    def test_same_mode_reproduces_the_same_machine_structure(self):
        for mode in builder.MODES:
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory() as holder:
                    root = (Path(holder) / "case").resolve()
                    first_manifest = builder.build_fixture(mode, root)
                    first_tree = _normalized_tree(root)
                    shutil.rmtree(root)
                    second_manifest = builder.build_fixture(mode, root)
                    second_tree = _normalized_tree(root)
                self.assertEqual(first_tree, second_tree)
                self.assertEqual(_normalize(first_manifest, root),
                                 _normalize(second_manifest, root))

    def test_manifest_records_mode_professor_directions_and_file_hashes(self):
        manifest, root = self.build("single_paper")
        self.assertEqual(manifest["professor"], PROFESSOR)
        self.assertEqual(manifest["direction_ids"], ["DIR00001"])
        self.assertEqual(manifest["item_keys"], ["AAAA1111"])
        protected = {row["path"]: row["sha256"] for row in manifest["protected_files"]}
        for relative in ("facts.json", "info.json", "教授研究/套磁目标.json",
                         "教授研究/X分野/試験 教授/方向预筛.json",
                         "教授研究/X分野/試験 教授/papers.json",
                         "教授研究/X分野/試験 教授/论文分析/AAAA1111.pdf"):
            self.assertIn(relative, protected)
        for relative, digest in protected.items():
            path = root / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_rebuild_over_own_previous_manifest_is_allowed(self):
        with tempfile.TemporaryDirectory() as holder:
            root = (Path(holder) / "case").resolve()
            builder.build_fixture("reuse_all", root)
            second = builder.build_fixture("reuse_all", root)
            self.assertEqual(second["mode"], "reuse_all")
            self.assertTrue((root / "fixture-manifest.json").is_file())

    def test_refuses_output_inside_the_producer_checkout(self):
        repo_root = builder._producer_repo_root()
        if repo_root is None:  # pragma: no cover - builder always lives in a checkout
            self.skipTest("producer repo root not detectable")
        inside = repo_root / "worktrees" / "issue29-fixture-guard-selftest"
        with self.assertRaises(builder.FixtureBuildError):
            builder.build_fixture("single_paper", inside)
        self.assertFalse(inside.exists())

    def test_refuses_to_overwrite_a_foreign_directory(self):
        with tempfile.TemporaryDirectory() as holder:
            root = (Path(holder) / "case").resolve()
            root.mkdir()
            (root / "unrelated.txt").write_text("keep out", encoding="utf-8")
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture("single_paper", root)
            self.assertEqual((root / "unrelated.txt").read_text(encoding="utf-8"),
                             "keep out")

    def test_cli_fixed_interface_invocation(self):
        with tempfile.TemporaryDirectory() as holder:
            case_root = (Path(holder) / "case_root").resolve()
            result = subprocess.run(
                [sys.executable, str(BUILDER_PATH),
                 "--mode", "single_paper", "--output", str(case_root)],
                text=True, capture_output=True, check=False, timeout=300)
            self.assertEqual(result.returncode, 0,
                             f"stdout: {result.stdout}\nstderr: {result.stderr}")
            manifest = json.loads(
                (case_root / "fixture-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["mode"], "single_paper")
        self.assertEqual(manifest["program_root"], str(case_root))


if __name__ == "__main__":
    unittest.main()
