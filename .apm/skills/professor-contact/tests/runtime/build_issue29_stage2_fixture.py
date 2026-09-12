#!/usr/bin/env python3
"""Build deterministic Stage 2 program-root fixtures for the issue #29 smoke runs.

Producer-owned test asset: it only constructs test inputs. Every accepted
pack / proof / fingerprint inside the fixture is produced by the repo's own
deterministic runner through the shared test templates — never hand-written
or copied — and every build step runs at the fixture's final location so all
recorded paths and fingerprints match the persisted tree.

Fixed modes (issue #29 Test Recipe §B):

- ``reuse_all``  — the ``test_stage2_preflight.PreflightBase`` accepted-state
  contract (two selected directions, accepted pack, preflight cache seeded).
- ``single_paper`` — one selected direction with one unique candidate whose
  PDF is a real, parseable text PDF (the title never embeds an item key) and
  which has no full analysis / sidecar yet, so a smoke run must enter
  ``paper-analysis`` once.
- ``material_pending`` — the canonical data of
  ``test_stage2_resolved_direction_acceptance_boundary.py::
  test_stage2_finalize_rejects_unaccepted_material_proposal`` (``dir_A``,
  ``P1=Signal Paper``, ``P2=Chemistry Paper``, refined + remove ``P2``,
  sidecar left at ``acceptance: proposed``).

The ``single_paper`` and ``material_pending`` modes build their Stage 1
snapshot with the repo's own ``contact_stage1.py build`` and require
``contact_stage1.py verify`` to pass before the fixture is returned: the
Stage 2 caller contract runs that verify first, so a runtime fixture must
carry a product-built snapshot — a hand-forged one always fails the entry
gate with ``stale_stage1_snapshot``.

Fixed invocation:

    python .apm/skills/professor-contact/tests/runtime/build_issue29_stage2_fixture.py \
        --mode single_paper --output "$CASE_ROOT"

The output directory must live outside the producer checkout/worktree and
outside any clean consumer. Each build writes ``fixture-manifest.json`` with
the mode, program root, professor, direction ids, item keys and the SHA256
of every protected file in the built tree.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

import test_stage2_preflight as preflight_templates  # noqa: E402
import test_stage2_resolved_direction_acceptance_boundary as acceptance_boundary  # noqa: E402
from test_stage2_resolved_direction import ResolvedPipelineMixin  # noqa: E402

MANIFEST_NAME = "fixture-manifest.json"
MANIFEST_ID = "tests/runtime/build_issue29_stage2_fixture.py"
MODES = ("reuse_all", "single_paper", "material_pending")
PROFESSOR = preflight_templates.PROFESSOR


class FixtureBuildError(RuntimeError):
    """Raised when the fixture cannot be built or fails its runner checks."""


def _write_stage0_state(root: Path, prof_dir: Path, *, direction_id: str,
                        direction: dict, papers: list, seed_count: int) -> None:
    """Write the Stage 0 program state the analyzer gates require.

    Single-direction canonical shapes mirroring ``PreflightBase``: target
    state, per-professor ``papers.json``, authorship ledger, preview file,
    program ``info.json``. ``contact_targets.py resolve`` then runs at the
    final location so the stored projection is runner-stamped, never
    hand-forged. The Stage 1 snapshot itself is NOT written here: it must be
    produced by the product's own ``contact_stage1.py build`` (see
    ``_build_and_verify_stage1_snapshot``) or the mandatory entry verify
    rejects the fixture.
    """
    professor = PROFESSOR
    preview_relative = Path("教授研究") / "X分野" / professor / "方向预筛.json"
    preview = {
        "professor": professor,
        "preview_fingerprint": "pv-1",
        "preview_fingerprint_version": "v1",
        "direction_id_version": "v1",
        "membership_mode": "overlap_allowed",
        "directions": [{
            "direction_id": direction_id,
            "member_fingerprint": f"{direction_id}-mf-1",
            "name_ja": direction["name_ja"],
            "name_zh": direction["name_zh"],
            "summary_zh": direction["summary_zh"],
            "user_note": direction["user_note"],
            "members": [{"item_key": key, "preview_confidence": "high"}
                        for key in direction["member_keys"]],
            "representatives": [{"item_key": direction["member_keys"][0]}],
        }],
    }
    (root / preview_relative).write_text(
        json.dumps(preview, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    target = {
        "schema_version": 1, "kind": "professor-contact-targets",
        "updated_at": "2026-01-01T00:00:00Z",
        "targets": [{
            "professor": professor,
            "professor_dir": str(Path("教授研究") / "X分野" / professor),
            "preview_path": str(preview_relative),
            "preview_fingerprint": "pv-1", "preview_fingerprint_version": "v1",
            "direction_id_version": "v1",
            "selected_direction_ids": [direction_id],
            "directions": [{
                "direction_id": direction_id,
                "name_ja": direction["name_ja"], "name_zh": direction["name_zh"],
                "summary_zh": direction["summary_zh"],
                "members": [{"item_key": key, "preview_confidence": "high"}
                            for key in direction["member_keys"]],
                "user_note": direction["user_note"],
            }],
        }],
    }
    (root / "教授研究" / "套磁目标.json").write_text(
        json.dumps(target, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    (prof_dir / "papers.json").write_text(
        json.dumps({"papers": papers}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")

    ledger = {
        "updated_at": "2026-01-01T00:00:00Z", "overrides": {},
        "professors": {
            professor: {"books": [{"prof_name_tokens": ["試験", "教授"],
                                   "seed_count": seed_count, "auto": [],
                                   "conflicted": [], "offenders": [],
                                   "typos": [], "mashes": []}],
                        "seed_count": seed_count},
        }}
    (root / "教授研究" / "_署名对照.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    (root / "info.json").write_text(json.dumps({
        "program": "issue29-runtime-fixture",
        "notes": "synthetic Stage 2 smoke program root",
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _run_contact_script(script: Path, arguments: list) -> dict:
    result = subprocess.run(
        [sys.executable, str(script), *map(str, arguments)],
        text=True, capture_output=True, check=False, timeout=300)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise FixtureBuildError(
            f"{script.name} {' '.join(arguments[:1])} did not return JSON: "
            f"{result.stdout!r} {result.stderr!r}") from exc
    return payload


def _build_and_verify_stage1_snapshot(root: Path) -> None:
    """Produce the Stage 1 snapshot with the product's own builder, then verify.

    The Stage 2 caller contract runs ``contact_stage1.py verify`` before any
    Stage 2 gate, so a runtime fixture must carry a snapshot whose
    ``input_fingerprint`` the product computed itself over the persisted
    papers/preview/target state. ``build`` and ``verify`` are both read-mostly
    and deterministic here: ``resolve_targets`` only writes while projections
    change, so the verified fingerprint stays valid at runtime.
    """
    stage1 = TESTS_DIR.parent / "scripts" / "contact_stage1.py"
    built = _run_contact_script(
        stage1, ["build", "--program-root", root, "--professors", PROFESSOR])
    if built.get("status") != "ok" or built.get("action") != "noop":
        raise FixtureBuildError(
            "contact_stage1 build rejected the fixture state: "
            + json.dumps(built, ensure_ascii=False))
    verified = _run_contact_script(
        stage1, ["verify", "--program-root", root, "--professors", PROFESSOR])
    if verified.get("status") != "ok":
        raise FixtureBuildError(
            "contact_stage1 verify rejected the freshly built snapshot: "
            + json.dumps(verified, ensure_ascii=False))


def _resolve_targets(root: Path) -> dict:
    """Run the deterministic target resolver at the final location."""
    script = TESTS_DIR.parent / "scripts" / "contact_targets.py"
    payload = _run_contact_script(
        script, ["resolve", "--program-root", root])
    if payload.get("status") != "ok":
        raise FixtureBuildError(
            "contact_targets resolve rejected the Stage 0 state: "
            + json.dumps(payload, ensure_ascii=False))
    return payload


@contextmanager
def _pinned_temporary_directory(final_root: Path):
    """Make the shared test templates build directly at ``final_root``.

    The shared templates start from ``tempfile.TemporaryDirectory()``; for a
    runtime fixture the state must be produced at its final location so every
    recorded path and fingerprint describes the persisted tree without any
    post-hoc rewriting. The pinned root's cleanup is a no-op: the fixture
    output must survive the build, and deletion is owned by the CLI guards.
    """
    real_temporary_directory = tempfile.TemporaryDirectory

    class _PinnedRoot:
        name = str(final_root)

        @staticmethod
        def cleanup():
            pass

    tempfile.TemporaryDirectory = _PinnedRoot
    try:
        yield
    finally:
        tempfile.TemporaryDirectory = real_temporary_directory


class ReuseAllBuilder(preflight_templates.PreflightBase):
    """PreflightBase accepted state, built at the final fixture location.

    This mode models the runner-level accepted/reuse contract only: it keeps
    the shared template's synthetic Stage 1 fingerprints, so — unlike
    ``single_paper``/``material_pending`` — it is not expected to pass the
    ``contact_stage1.py verify`` entry gate (whose check would otherwise
    invalidate the seeded preflight reuse cache this mode exists to assert).
    """

    def __init__(self, final_root: Path):
        super().__init__("test_build_fixture")
        self._final_root = Path(final_root)

    def test_build_fixture(self):
        pass  # never collected: this module is not matched by the test pattern

    def setUp(self):
        with _pinned_temporary_directory(self._final_root):
            super().setUp()

    def build(self):
        self.setUp()
        self.build_accepted_state()
        payload = self.preflight()
        if payload.get("status") != "ok" or payload.get("action") != "reuse_all" \
                or payload.get("reason_codes") != []:
            raise FixtureBuildError(
                "reuse_all fixture did not pass the preflight reuse contract: "
                + json.dumps(payload, ensure_ascii=False))
        pack = self._read_pack()
        cache = pack.get("cache") or {}
        if "preflight" not in cache or "validator" not in pack:
            raise FixtureBuildError("accepted pack is missing preflight cache or validator state")


class SinglePaperBuilder(preflight_templates.PreflightBase):
    """PreflightBase schema shapes reduced to one direction / one candidate.

    Initial state has no accepted pack and no analysis / sidecar for the
    candidate, so a smoke run must enter ``paper-analysis`` once. The title
    never embeds the item key (that fixture artefact polluted the old H3
    style-validator evidence).
    """

    ITEM_KEY = "AAAA1111"
    TITLE = "A Synthetic Comparison Framework for Input Pattern Processing"
    PDF_LINES = (
        "A Synthetic Comparison Framework for Input Pattern Processing",
        "Example Professor",
        "2023",
        "",
        "Abstract",
        "We study a synthetic comparison of input patterns and give a",
        "framework that measures how two fixed input families behave under",
        "one shared processing path.",
        "",
        "1. Method",
        "We fix two input families, run both through the same processing",
        "path, and record the paired outputs for statistical comparison.",
        "",
        "2. Results",
        "The paired outputs show a stable difference across the two input",
        "families under the shared processing path.",
        "",
        "3. Conclusion",
        "The comparison framework separates input effects from processing",
        "effects for synthetic input patterns.",
        "",
        "Future work",
        "We plan to apply the framework to adaptive and nonlinear",
        "processing paths, and to study how the two input families scale.",
    )

    def __init__(self, final_root: Path):
        super().__init__("test_build_fixture")
        self._final_root = Path(final_root)

    def test_build_fixture(self):
        pass  # never collected: this module is not matched by the test pattern

    def setUp(self):
        with _pinned_temporary_directory(self._final_root):
            super().setUp()
        self._reduce_to_single_candidate()
        _write_stage0_state(
            self.root, self.prof_dir, direction_id="DIR00001",
            direction={"name_ja": "合成输入比较", "name_zh": "合成输入比较",
                       "summary_zh": "比较合成输入",
                       "user_note": "我想比较两种合成输入的处理结果。",
                       "member_keys": [self.ITEM_KEY]},
            papers=[{"item_key": self.ITEM_KEY, "title": self.TITLE,
                     "title_zh": None, "pdf_status": "downloaded"}],
            seed_count=1)
        _resolve_targets(self.root)
        _build_and_verify_stage1_snapshot(self.root)
        self._write_parseable_pdf()

    def _reduce_to_single_candidate(self):
        key = self.ITEM_KEY
        paper = next(p for p in self.facts["papers"] if p["item_key"] == key)
        paper["title"] = self.TITLE
        for dropped in ("analysis_file", "sidecar_file"):
            paper.pop(dropped, None)
        self.facts["papers"] = [paper]
        direction = self.facts["directions"][0]
        direction["member_keys"] = [key]
        direction["relevant_keys"] = [key]
        direction["named_keys"] = [key]
        self.facts["directions"] = [direction]
        self.facts_path.write_text(
            json.dumps(self.facts, ensure_ascii=False, indent=1), encoding="utf-8")

        analysis_dir = self.prof_dir / "论文分析"
        for stale in list(analysis_dir.glob("*.md")) + \
                list(analysis_dir.glob("*.future_work.json")):
            stale.unlink()

    def _write_parseable_pdf(self):
        item_key = self.ITEM_KEY
        extension_pattern = preflight_templates.contact_state.EXT_EVIDENCE_RE
        for line in self.PDF_LINES:
            if item_key in line:
                raise FixtureBuildError(f"PDF text embeds the fixture item key: {line!r}")
            if extension_pattern.search(line):
                raise FixtureBuildError(f"PDF text matches the extension-evidence pattern: {line!r}")
        self.pdf_path.write_bytes(render_text_pdf(self.PDF_LINES))

    def build(self):
        self.setUp()
        payload = self.preflight()
        if payload.get("status") != "ok" or payload.get("action") != "process" \
                or "missing_input_pack" not in payload.get("reason_codes", []):
            raise FixtureBuildError(
                "single_paper fixture is not in the fresh-process initial state: "
                + json.dumps(payload, ensure_ascii=False))
        if (self.prof_dir / "套磁候选输入.json").exists():
            raise FixtureBuildError("single_paper fixture must not contain an accepted pack")


class MaterialPendingBuilder(ResolvedPipelineMixin, unittest.TestCase):
    """The canonical proposed-material state, built at the final fixture location."""

    def __init__(self, final_root: Path):
        super().__init__("test_build_fixture")
        self._final_root = Path(final_root)

    def test_build_fixture(self):
        pass  # never collected: this module is not matched by the test pattern

    def setUp(self):
        with _pinned_temporary_directory(self._final_root):
            self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / self.professor
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def build(self):
        self.setUp()
        canonical = acceptance_boundary.ResolvedDirectionAcceptanceBoundaryTests(
            "test_stage2_finalize_rejects_unaccepted_material_proposal")
        papers = [
            self.make_paper("P1", "Signal Paper", ["signal", "processing"], ["Future A."]),
            self.make_paper("P2", "Chemistry Paper", ["chemistry", "catalyst"], ["Future B."]),
        ]
        facts_path = self.write_facts(
            papers,
            [self.make_direction(
                "dir_A", ["P1", "P2"], name_ja="Signal Processing",
                name_zh="信号处理", summary="signal processing")],
        )
        _, resolve_finalize = self.run_resolve(
            facts_path, {"dir_A": canonical._refined("dir_A", "P2")})
        if not resolve_finalize.get("needs_user_choice"):
            raise FixtureBuildError(
                "material_pending fixture must stop at the user-choice boundary: "
                + json.dumps(resolve_finalize, ensure_ascii=False))
        sidecar = json.loads(
            (self.prof_dir / "论文分析" / "_resolved_directions.json").read_text(encoding="utf-8"))
        if sidecar["directions"][0]["acceptance"] != "proposed":
            raise FixtureBuildError(
                "material_pending sidecar must stay proposed: "
                + json.dumps(sidecar, ensure_ascii=False))
        _write_stage0_state(
            self.root, self.prof_dir, direction_id="dir_A",
            direction={"name_ja": "Signal Processing", "name_zh": "信号处理",
                       "summary_zh": "signal processing", "user_note": "",
                       "member_keys": ["P1", "P2"]},
            papers=[{"item_key": "P1", "title": "Signal Paper",
                     "title_zh": None, "pdf_status": "downloaded"},
                    {"item_key": "P2", "title": "Chemistry Paper",
                     "title_zh": None, "pdf_status": "downloaded"}],
            seed_count=2)
        _resolve_targets(self.root)
        _build_and_verify_stage1_snapshot(self.root)
        if (self.prof_dir / "套磁候选输入.json").exists():
            raise FixtureBuildError("material_pending fixture must not contain an accepted pack")


def render_text_pdf(lines) -> bytes:
    """Render a minimal, deterministic, parseable one-page text PDF.

    No third-party dependency and no timestamp: identical input lines always
    produce identical bytes. Text is drawn as plain Helvetica/WinAnsi strings
    so ordinary PDF text extractors can read it.
    """
    def escape(text: str) -> str:
        return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    content_parts = ["BT", "/F1 11 Tf", "14 TL", "1 0 0 1 72 720 Tm"]
    content_parts.extend(f"({escape(line)}) Tj T*" for line in lines)
    content_parts.append("ET")
    stream = "\n".join(content_parts).encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
    ]
    out = bytearray(b"%PDF-1.4\n%\xc7\xec\x8f\xa2\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
    xref_position = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_position}\n").encode("ascii")
    out += b"%%EOF\n"
    return bytes(out)


def _producer_repo_root():
    for candidate in [TESTS_DIR, *TESTS_DIR.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _prepare_output_directory(output: Path) -> Path:
    output = Path(output).resolve()
    repo_root = _producer_repo_root()
    if repo_root is not None and (output == repo_root or repo_root in output.parents):
        raise FixtureBuildError(
            f"fixture output must be outside the producer checkout/worktree: {output}")
    if output.exists():
        if not output.is_dir():
            raise FixtureBuildError(f"fixture output is not a directory: {output}")
        entries = list(output.iterdir())
        if entries:
            manifest_path = output / MANIFEST_NAME
            previous_is_ours = False
            if manifest_path.is_file():
                try:
                    previous = json.loads(manifest_path.read_text(encoding="utf-8"))
                    previous_is_ours = previous.get("builder") == MANIFEST_ID
                except (json.JSONDecodeError, OSError):
                    previous_is_ours = False
            if not previous_is_ours:
                raise FixtureBuildError(
                    f"refusing to overwrite a directory that is not a previous "
                    f"fixture build: {output}")
            shutil.rmtree(output)
        output.mkdir(parents=True, exist_ok=True)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.mkdir()
    return output


def _tree_hashes(root: Path) -> list:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == MANIFEST_NAME:
            continue
        rows.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return rows


def _manifest_for(mode: str, output: Path) -> dict:
    canonical_sources = {
        "reuse_all": "tests/test_stage2_preflight.py::PreflightBase.build_accepted_state",
        "single_paper": ("tests/test_stage2_preflight.py::PreflightBase.setUp, reduced per "
                         "issue #29 Test Recipe §B (one direction, one unique candidate, "
                         "real text PDF, no prior analysis)"),
        "material_pending": ("tests/test_stage2_resolved_direction_acceptance_boundary.py::"
                             "test_stage2_finalize_rejects_unaccepted_material_proposal"),
    }
    expected = {
        "reuse_all": {"direction_ids": ["DIR00001", "DIR00002"],
                      "item_keys": ["AAAA1111", "BBBB2222", "CCCC3333"],
                      "expected_preflight_action": "reuse_all"},
        "single_paper": {"direction_ids": ["DIR00001"],
                         "item_keys": ["AAAA1111"],
                         "expected_preflight_action": "process"},
        "material_pending": {"direction_ids": ["dir_A"],
                             "item_keys": ["P1", "P2"],
                             "expected_preflight_action": None},
    }
    return {
        "schema": 1,
        "builder": MANIFEST_ID,
        "builder_sha256": hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest(),
        "mode": mode,
        "program_root": str(output),
        "professor": PROFESSOR,
        **expected[mode],
        "canonical_source": canonical_sources[mode],
        "protected_files": _tree_hashes(output),
    }


def build_fixture(mode: str, output: Path) -> dict:
    """Build one fixture and return the written manifest payload."""
    if mode not in MODES:
        raise FixtureBuildError(f"unknown mode: {mode!r}; expected one of {MODES}")
    output = _prepare_output_directory(output)
    builders = {
        "reuse_all": ReuseAllBuilder,
        "single_paper": SinglePaperBuilder,
        "material_pending": MaterialPendingBuilder,
    }
    builders[mode](output).build()
    manifest = _manifest_for(mode, output)
    manifest_path = output / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic issue #29 Stage 2 smoke fixture.")
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("--output", required=True, type=Path,
                        help="fixture output directory; must be outside the producer "
                             "checkout/worktree and outside any clean consumer")
    arguments = parser.parse_args(argv)
    manifest = build_fixture(arguments.mode, arguments.output)
    summary = {key: manifest[key] for key in (
        "mode", "program_root", "professor", "direction_ids", "item_keys",
        "expected_preflight_action")}
    print(json.dumps(summary, ensure_ascii=False))
    print(f"protected files: {len(manifest['protected_files'])}")
    print(f"manifest: {Path(manifest['program_root']) / MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
