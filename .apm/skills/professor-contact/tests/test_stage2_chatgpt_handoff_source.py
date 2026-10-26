"""Future-work evidence taken from the read source text of a text-only handoff.

Covers T1-T4 of ``plan/handoff-source-evidence/test-plan.md`` against the real
Stage-2 handoff entrypoints and the installed paper-analysis helpers.  The
prepare/validate/finalize semantics are therefore the installed helper's, not a
test double.

The module runs only when the paper-analysis install is wired through the
environment variables below; without them every case is skipped and recorded as
not tested, never as passed.  Temporary inputs use ``CONTACT_SOURCE_TEST_RUN_ROOT``
when it is set, so one execution run keeps its disposable files together.

  CONTACT_PAPER_ANALYSIS_SKILL   installed skill dir (SKILL.md + scripts/)
  CONTACT_PAPER_ANALYSIS_AGENT   its paper-analysis.agent.md / paper-analysis.toml
  CONTACT_PAPER_ANALYSIS_PYTHON  interpreter that imports pdfx and pymupdf
  CONTACT_SOURCE_TEST_RUN_ROOT   optional run root for disposable files
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import _stage2_handoff_test_support as support

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_chatgpt_handoff.py"
SPEC = importlib.util.spec_from_file_location("stage2_chatgpt_handoff", SCRIPT)
handoff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(handoff)

PAPER_SKILL_ENV = "CONTACT_PAPER_ANALYSIS_SKILL"
PAPER_AGENT_ENV = "CONTACT_PAPER_ANALYSIS_AGENT"
PAPER_PYTHON_ENV = "CONTACT_PAPER_ANALYSIS_PYTHON"
HELPER_PYTHON_ENV = "CONTACT_PAPER_PYTHON"
RUN_ROOT_ENV = "CONTACT_SOURCE_TEST_RUN_ROOT"

# The quote below sits on a page outside the trailing candidate pages, so it is
# never in candidates.json: only prepared source text can prove it.
NON_CANDIDATE_QUOTE = "The framework also supports multilingual documents."
CANDIDATE_QUOTE = "We will share code after publication."
OCR_PAGE_TEXT = "Exact OCR text for the blank final page."

PAGES_WITH_FUTURE_WORK = (
    ("Title Page", "A Study of Contact Workflows", "Author A, Author B"),
    ("Method", "We describe the pipeline.", NON_CANDIDATE_QUOTE),
    ("Results", "The method improves accuracy.", "Results hold across three benchmarks."),
    ("Discussion", "The results are consistent.", "We discuss practical deployment."),
    ("Conclusion", "Our future work will extend the method to longer documents.", CANDIDATE_QUOTE),
)

PAGES_WITH_BLANK_LAST_PAGE = (
    ("Title Page", "A Study of Contact Workflows", "Author A, Author B"),
    ("Method", "We describe the pipeline.", NON_CANDIDATE_QUOTE),
    ("Results", "The method improves accuracy.", "Results hold across three benchmarks."),
    ("Discussion", "The results are consistent.", "We discuss practical deployment."),
    (),
)


def _wiring():
    skill = os.environ.get(PAPER_SKILL_ENV, "").strip()
    agent = os.environ.get(PAPER_AGENT_ENV, "").strip()
    python = (
        os.environ.get(PAPER_PYTHON_ENV, "").strip()
        or os.environ.get(HELPER_PYTHON_ENV, "").strip()
    )
    missing = [
        name
        for name, value in (
            (PAPER_SKILL_ENV, skill),
            (PAPER_AGENT_ENV, agent),
            (PAPER_PYTHON_ENV + "/" + HELPER_PYTHON_ENV, python),
        )
        if not value
    ]
    if missing:
        raise unittest.SkipTest(
            "未接线已安装的 paper-analysis helper（需要 "
            + "、".join(missing)
            + "）：本项未执行，不记通过"
        )
    return Path(skill).expanduser(), Path(agent).expanduser(), Path(python).expanduser()


def _check_wiring(skill, agent, python):
    for name in ("future_work.py", "facts.py", "pdf_runtime.py"):
        if not (skill / "scripts" / name).is_file():
            raise RuntimeError(f"paper-analysis install missing scripts/{name}: {skill}")
    if not (skill / "SKILL.md").is_file():
        raise RuntimeError(f"paper-analysis install missing SKILL.md: {skill}")
    if agent.name not in {"paper-analysis.agent.md", "paper-analysis.toml"} or not agent.is_file():
        raise RuntimeError(f"paper-analysis agent is not an installed agent file: {agent}")
    if not python.is_file():
        raise RuntimeError(f"paper-analysis helper interpreter missing: {python}")


def _write_pdf(pymupdf, path, pages):
    document = pymupdf.open()
    try:
        for lines in pages:
            page = document.new_page()
            y = 72
            for line in lines:
                page.insert_text((72, y), line)
                y += 18
        document.save(path)
    finally:
        document.close()


class SourceHandoffTestCase(unittest.TestCase):
    """One synthetic paper, one installed-helper prepare, disposable professor."""

    PAGES = ()
    ITEM_KEY = "T1"
    ANALYSIS_NAME = "T1.md"
    OLD_PREPARE = False
    PAGE_CACHE = None
    OCR_PAGE = None

    @classmethod
    def setUpClass(cls):
        cls.skill_dir, cls.agent_file, cls.helper_python = _wiring()
        _check_wiring(cls.skill_dir, cls.agent_file, cls.helper_python)
        try:
            import pymupdf
        except ImportError as error:  # pragma: no cover - unavailable install
            raise unittest.SkipTest(f"需要 pymupdf 生成合成 PDF：{error}")
        cls.pymupdf = pymupdf
        cls.future_work_script = cls.skill_dir / "scripts" / "future_work.py"
        cls._saved_helper_python = os.environ.get(HELPER_PYTHON_ENV)
        # The product's fixed-interpreter switch must select this same install.
        os.environ[HELPER_PYTHON_ENV] = str(cls.helper_python)

    @classmethod
    def tearDownClass(cls):
        if cls._saved_helper_python is None:
            os.environ.pop(HELPER_PYTHON_ENV, None)
        else:
            os.environ[HELPER_PYTHON_ENV] = cls._saved_helper_python

    def setUp(self):
        run_root = os.environ.get(RUN_ROOT_ENV, "").strip() or None
        if run_root:
            Path(run_root).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="contact-source-", dir=run_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.professor = self.root / "Professor"
        (self.professor / "论文分析").mkdir(parents=True)
        self.handoff_dir = self.professor / "论文分析" / "_chatgpt_handoff"
        self.pdf = self.root / "paper.pdf"
        _write_pdf(self.pymupdf, self.pdf, self.PAGES)
        self.pdf_bytes = self.pdf.read_bytes()
        self.pdf_sha256 = hashlib.sha256(self.pdf_bytes).hexdigest()
        self.prepare_dir = self.root / "prepare"
        self.prepare_dir.mkdir()
        self.run_helper("prepare", self.pdf, "--debug-dir", self.prepare_dir)
        self.prepare = self.prepare_dir / "prepare.json"
        self.candidates = self.prepare_dir / "candidates.json"
        self.prepare_payload = json.loads(self.prepare.read_text(encoding="utf-8"))
        self.candidates_payload = json.loads(self.candidates.read_text(encoding="utf-8"))["candidates"]
        if self.OLD_PREPARE:
            self.downgrade_prepare()
        self.prepare_bytes = self.prepare.read_bytes()
        self.candidates_bytes = self.candidates.read_bytes()
        if self.PAGE_CACHE:
            self.write_page_cache(self.PAGE_CACHE)
        self.target = self.professor / "论文分析" / "A" / self.ANALYSIS_NAME

    # -- fixture construction -------------------------------------------------
    def run_helper(self, *arguments):
        process = subprocess.run(
            [str(self.helper_python), str(self.future_work_script)]
            + [str(argument) for argument in arguments],
            text=True,
            capture_output=True,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(
                "paper-analysis helper failed: "
                + (process.stderr.strip() or process.stdout.strip())[:600]
            )
        return process

    def downgrade_prepare(self):
        """Strip the fields a pre-source-pages prepare did not carry."""
        payload = json.loads(self.prepare.read_text(encoding="utf-8"))
        payload.pop("source_pages", None)
        payload.pop("ocr_resolved_pages", None)
        self.prepare.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        self.prepare_payload = payload

    def write_page_cache(self, pages):
        path = Path(str(self.pdf) + ".llm_ocr.pages.json")
        payload = {
            "schema": 1,
            "pdf_sha256": self.pdf_sha256,
            "pages": {str(page): text for page, text in pages.items()},
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def page_of(self, needle):
        for page in self.prepare_payload.get("source_pages") or []:
            if needle in page["text"]:
                return page["page"]
        raise AssertionError(f"fixture text not found in prepared source: {needle}")

    def candidate_for(self, needle):
        matches = [item for item in self.candidates_payload if needle in item["quote"]]
        self.assertEqual(len(matches), 1, matches)
        return matches[0]

    # -- product entrypoints --------------------------------------------------
    def build_args(self):
        jobs_file = self.root / "jobs.json"
        jobs_file.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "professor": "Professor",
                    "jobs": [
                        {
                            "item_key": self.ITEM_KEY,
                            "carrier": "pdf",
                            "level": "fulltext",
                            "input_path": str(self.pdf),
                            "analysis_relpath": f"论文分析/A/{self.ANALYSIS_NAME}",
                            "research_direction": {},
                            "future_work_prepare": str(self.prepare),
                            "future_work_candidates": str(self.candidates),
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        args = support.Args()
        args.professor_dir = self.professor
        args.jobs = jobs_file
        args.professor = None
        args.paper_analysis_skill_dir = self.skill_dir
        args.paper_analysis_agent = self.agent_file
        return args

    def build(self):
        return handoff.build_bundle(self.build_args())

    def build_legacy(self, selection_contract="exact-items-v1"):
        return support.legacy_embedded_bundle(
            self.build_args(), handoff, selection_contract=selection_contract
        )

    def manifest_of(self, bundle_path):
        with zipfile.ZipFile(bundle_path) as archive:
            return json.loads(archive.read("manifest.json"))

    def result_zip(self, bundle_path, items, *, facts=None, analysis=support.ANALYSIS):
        manifest = self.manifest_of(bundle_path)
        job = manifest["jobs"][0]
        safe = handoff._safe_component(job["job_id"])
        path = self.root / f"result-{manifest['handoff_id']}.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                "result_manifest.json",
                json.dumps(
                    {
                        "schema": 1,
                        "kind": handoff.RESULT_KIND,
                        "handoff_id": manifest["handoff_id"],
                        "source_fingerprint": manifest["source_fingerprint"],
                        "results": [
                            {
                                "job_id": job["job_id"],
                                "item_key": job["item_key"],
                                "input_sha256": job["input_sha256"],
                                "status": "ok",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
            archive.writestr(f"results/{safe}/analysis.md", analysis)
            if items is not None:
                archive.writestr(
                    f"results/{safe}/future_work_items.json",
                    json.dumps({"items": items}, ensure_ascii=False),
                )
            if facts is not None:
                archive.writestr(
                    f"results/{safe}/facts.json",
                    json.dumps(facts, ensure_ascii=False),
                )
        return path

    def import_result(self, bundle_path, result_path):
        args = support.Args()
        args.professor_dir = self.professor
        args.bundle = Path(bundle_path)
        args.result = result_path
        args.future_work_script = self.future_work_script
        return handoff.import_result(args)

    # -- shared expectations --------------------------------------------------
    def assert_no_pdf_copies(self):
        self.assertFalse(list(self.handoff_dir.rglob("*.pdf")))

    def assert_not_installed(self, output, reason_code, *, pdf_unchanged=True):
        self.assertEqual(output["status"], "needs_external_result", output)
        self.assertEqual(output["reason_code"], reason_code, output)
        self.assertFalse(self.target.exists())
        self.assertFalse(Path(str(self.target) + ".future_work.json").exists())
        self.assertFalse(Path(str(self.target) + ".facts.json").exists())
        self.assertFalse((self.professor / "论文分析" / "_index.json").exists())
        self.assert_no_pdf_copies()
        if pdf_unchanged:
            self.assertEqual(self.pdf.read_bytes(), self.pdf_bytes)


class SourceItemsCase(SourceHandoffTestCase):
    """Fixture shared by T1 and T3: one candidate plus one outside-candidate quote."""

    PAGES = PAGES_WITH_FUTURE_WORK
    ITEM_KEY = "T1"
    ANALYSIS_NAME = "T1.md"

    def setUp(self):
        super().setUp()
        self.non_candidate_page = self.page_of(NON_CANDIDATE_QUOTE)
        self.assertFalse(
            [item for item in self.candidates_payload if NON_CANDIDATE_QUOTE in item["quote"]],
            "fixture quote must stay outside candidates.json",
        )
        self.candidate = self.candidate_for(CANDIDATE_QUOTE)

    def items(self):
        return [
            {
                "quote": NON_CANDIDATE_QUOTE,
                "translation_zh": "该框架也支持多语言文档。",
                "source": "Method",
                "page": self.non_candidate_page,
            },
            {
                "id": self.candidate["id"],
                "quote": self.candidate["quote"],
                "translation_zh": "我们将在论文发表后公开代码。",
                "source": "Conclusion",
                "page": self.candidate["page"],
            },
        ]


class SourceItemsTests(SourceItemsCase):
    def test_build_keeps_text_and_evidence_on_one_prepared_page_source(self):
        bundle = self.build()
        self.assertTrue(bundle["upload_ready"], bundle.get("text_preparation"))
        job = self.manifest_of(bundle["bundle_path"])["jobs"][0]
        self.assertEqual(job["source_mode"], "local")
        self.assertEqual(job["future_work"]["selection_contract"], "source-items-v1")
        self.assertEqual(job["future_work"]["ocr_required_pages"], [])
        transport = job["text_transport"]
        self.assertEqual(transport["page_count"], len(self.PAGES))
        self.assertEqual(transport["missing_text_pages"], [])
        with zipfile.ZipFile(bundle["bundle_path"]) as archive:
            names = archive.namelist()
            text = archive.read(transport["path"]).decode("utf-8")
            prepare_bytes = archive.read(job["future_work"]["prepare_path"])
            candidates_bytes = archive.read(job["future_work"]["candidates_path"])
        self.assertFalse([name for name in names if name.lower().endswith(".pdf")], names)
        self.assertEqual(
            hashlib.sha256(prepare_bytes).hexdigest(), job["future_work"]["prepare_sha256"]
        )
        self.assertEqual(
            hashlib.sha256(candidates_bytes).hexdigest(),
            job["future_work"]["candidates_sha256"],
        )
        prepared = json.loads(prepare_bytes)
        self.assertEqual(prepared["pdf_sha256"], job["input_sha256"])
        prepared_pages = {page["page"]: page["text"] for page in prepared["source_pages"]}
        transport_pages = handoff._impl._text.page_texts(text, len(self.PAGES))
        self.assertEqual(sorted(transport_pages), sorted(prepared_pages))
        for page, prepared_text in prepared_pages.items():
            self.assertEqual(transport_pages[page].strip(), prepared_text.strip())
        self.assertIn(NON_CANDIDATE_QUOTE, transport_pages[self.non_candidate_page])
        self.assert_no_pdf_copies()
        self.assertEqual(self.pdf.read_bytes(), self.pdf_bytes)

    def test_import_accepts_quote_outside_candidates_and_joins_facts(self):
        bundle = self.build()
        job = self.manifest_of(bundle["bundle_path"])["jobs"][0]
        result = self.result_zip(bundle["bundle_path"], self.items(), facts=support.FACTS_DRAFT)
        output = self.import_result(bundle["bundle_path"], result)
        self.assertEqual(output["status"], "imported", output)

        sidecar = json.loads(
            Path(str(self.target) + ".future_work.json").read_text(encoding="utf-8")
        )
        self.assertEqual(sidecar["status"], "ok")
        self.assertEqual(
            sidecar["source_pdf_fingerprint"], "sha256:" + job["input_sha256"]
        )
        self.assertEqual(
            [item["quote"] for item in sidecar["items"]],
            [NON_CANDIDATE_QUOTE, self.candidate["quote"]],
        )
        self.assertEqual(
            [item["page"] for item in sidecar["items"]],
            [self.non_candidate_page, self.candidate["page"]],
        )
        self.assertEqual(sidecar["items"][1]["id"], self.candidate["id"])
        self.assertEqual(
            sidecar["items"][0]["id"],
            hashlib.sha256(NON_CANDIDATE_QUOTE.encode("utf-8")).hexdigest(),
        )

        facts = json.loads(Path(str(self.target) + ".facts.json").read_text(encoding="utf-8"))
        self.assertEqual(facts["analysis"], self.ANALYSIS_NAME)
        self.assertEqual(facts["future_work_ids"], [item["id"] for item in sidecar["items"]])
        self.assertEqual(facts["input_fingerprint"], "sha256:" + job["input_sha256"])

        index = json.loads((self.professor / "论文分析" / "_index.json").read_text(encoding="utf-8"))
        entry = index["papers"][self.ITEM_KEY]
        self.assertEqual(entry["future_work_state"], "valid")
        self.assertEqual(entry["facts_state"], "valid")
        self.assertTrue(Path(entry["future_work_sidecar"]).is_file())
        self.assertTrue(Path(entry["facts_sidecar"]).is_file())
        self.assert_no_pdf_copies()
        self.assertEqual(self.pdf.read_bytes(), self.pdf_bytes)


class RejectedSourceItemsTests(SourceItemsCase):
    def test_wrong_physical_page_is_rejected(self):
        items = self.items()
        items[0]["page"] = 1 if self.non_candidate_page != 1 else 2
        bundle = self.build()
        result = self.result_zip(bundle["bundle_path"], items, facts=support.FACTS_DRAFT)
        self.assert_not_installed(
            self.import_result(bundle["bundle_path"], result),
            "external_future_work_invalid",
        )

    def test_rewritten_quote_is_rejected(self):
        items = self.items()
        items[0]["quote"] = NON_CANDIDATE_QUOTE.replace("documents", "papers")
        bundle = self.build()
        result = self.result_zip(bundle["bundle_path"], items, facts=support.FACTS_DRAFT)
        self.assert_not_installed(
            self.import_result(bundle["bundle_path"], result),
            "external_future_work_invalid",
        )

    def test_changed_source_pdf_is_rejected(self):
        bundle = self.build()
        result = self.result_zip(bundle["bundle_path"], self.items(), facts=support.FACTS_DRAFT)
        self.pdf.write_bytes(b"%PDF-1.4\nchanged after build\n")
        self.assert_not_installed(
            self.import_result(bundle["bundle_path"], result),
            "external_result_hash_mismatch",
            pdf_unchanged=False,
        )


class OldPrepareWithCacheTests(SourceHandoffTestCase):
    PAGES = PAGES_WITH_BLANK_LAST_PAGE
    ITEM_KEY = "T2"
    ANALYSIS_NAME = "T2.md"
    OLD_PREPARE = True
    OCR_PAGE = 5
    PAGE_CACHE = {OCR_PAGE: OCR_PAGE_TEXT}

    def test_required_page_cache_reaches_prepare_and_transport(self):
        bundle = self.build()
        self.assertTrue(bundle["upload_ready"], bundle.get("text_preparation"))
        job = self.manifest_of(bundle["bundle_path"])["jobs"][0]
        self.assertEqual(job["future_work"]["selection_contract"], "source-items-v1")
        self.assertEqual(job["future_work"]["ocr_required_pages"], [])
        transport = job["text_transport"]
        self.assertEqual(transport["missing_text_pages"], [])
        with zipfile.ZipFile(bundle["bundle_path"]) as archive:
            names = archive.namelist()
            prepared = json.loads(archive.read(job["future_work"]["prepare_path"]))
            text = archive.read(transport["path"]).decode("utf-8")
        prepared_pages = {page["page"]: page["text"] for page in prepared["source_pages"]}
        self.assertEqual(prepared["ocr_required_pages"], [])
        self.assertIn(self.OCR_PAGE, prepared.get("ocr_resolved_pages") or [])
        self.assertEqual(prepared_pages[self.OCR_PAGE].strip(), OCR_PAGE_TEXT)
        transport_pages = handoff._impl._text.page_texts(text, len(self.PAGES))
        self.assertEqual(transport_pages[self.OCR_PAGE].strip(), OCR_PAGE_TEXT)
        for page, prepared_text in prepared_pages.items():
            self.assertEqual(transport_pages[page].strip(), prepared_text.strip())
        self.assertFalse([name for name in names if name.lower().endswith(".pdf")], names)
        self.assertEqual(self.prepare.read_bytes(), self.prepare_bytes)
        self.assertEqual(self.candidates.read_bytes(), self.candidates_bytes)
        self.assert_no_pdf_copies()


class OldPrepareWithoutCacheTests(SourceHandoffTestCase):
    PAGES = PAGES_WITH_BLANK_LAST_PAGE
    ITEM_KEY = "T2"
    ANALYSIS_NAME = "T2.md"
    OLD_PREPARE = True
    OCR_PAGE = 5
    PAGE_CACHE = None

    def test_missing_required_cache_blocks_upload_without_pdf_fallback(self):
        bundle = self.build()
        self.assertFalse(bundle["upload_ready"])
        self.assertIsNone(bundle["bundle_path"])
        self.assertIsNone(bundle["bundle_dir"])
        preparation = bundle["text_preparation"]
        self.assertEqual(len(preparation), 1, preparation)
        self.assertEqual(preparation[0]["item_key"], self.ITEM_KEY)
        self.assertEqual(preparation[0]["pages"], [self.OCR_PAGE])
        self.assertFalse(list(self.handoff_dir.glob("stage2-*.zip")))
        self.assert_no_pdf_copies()
        self.assertEqual(self.prepare.read_bytes(), self.prepare_bytes)
        self.assertEqual(self.candidates.read_bytes(), self.candidates_bytes)


class LegacyExactContractTests(SourceItemsCase):
    PAGES = PAGES_WITH_FUTURE_WORK
    ITEM_KEY = "T4"
    ANALYSIS_NAME = "T4.md"

    def test_legacy_exact_bundle_keeps_candidate_only_scope(self):
        legacy = self.build_legacy()
        job = self.manifest_of(legacy["bundle_path"])["jobs"][0]
        self.assertEqual(job["future_work"]["selection_contract"], "exact-items-v1")
        self.assertNotIn("text_transport", job)
        self.assertNotIn("source_mode", job)
        with zipfile.ZipFile(legacy["bundle_path"]) as archive:
            self.assertIn(job["input_path"], archive.namelist())
            self.assertEqual(
                hashlib.sha256(archive.read(job["input_path"])).hexdigest(),
                job["input_sha256"],
            )
        result = self.result_zip(
            legacy["bundle_path"],
            [
                {
                    "quote": self.candidate["quote"],
                    "translation_zh": "我们将在论文发表后公开代码。",
                    "source": "Conclusion",
                    "page": self.candidate["page"],
                }
            ],
            facts=support.FACTS_DRAFT,
        )
        output = self.import_result(legacy["bundle_path"], result)
        self.assertEqual(output["status"], "imported", output)
        sidecar = json.loads(
            Path(str(self.target) + ".future_work.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(sidecar["items"]), 1)
        self.assertEqual(sidecar["items"][0]["quote"], self.candidate["quote"])
        self.assertEqual(sidecar["items"][0]["page"], self.candidate["page"])
        self.assertEqual(sidecar["items"][0]["id"], self.candidate["id"])
        facts = json.loads(Path(str(self.target) + ".facts.json").read_text(encoding="utf-8"))
        self.assertEqual(facts["future_work_ids"], [self.candidate["id"]])

    def test_legacy_exact_bundle_rejects_quote_outside_candidates(self):
        legacy = self.build_legacy()
        result = self.result_zip(
            legacy["bundle_path"],
            [
                {
                    "quote": NON_CANDIDATE_QUOTE,
                    "translation_zh": "该框架也支持多语言文档。",
                    "source": "Method",
                    "page": self.non_candidate_page,
                }
            ],
            facts=support.FACTS_DRAFT,
        )
        self.assert_not_installed(
            self.import_result(legacy["bundle_path"], result),
            "external_future_work_invalid",
        )


if __name__ == "__main__":
    unittest.main()
