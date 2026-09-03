import importlib.util
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_chatgpt_handoff.py"
SPEC = importlib.util.spec_from_file_location("stage2_chatgpt_handoff", SCRIPT)
handoff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(handoff)

ANALYSIS = """# Paper

## 总结
summary
## 问题是什么
q
## 挑战是什么
c
## Solution 是什么
s
## 研究方法是什么
m
## 贡献是什么
x
## 局限性与批判性评价
l
## 作者明说的未来工作（Future Work）
—（论文未明示 future work）
## 对自身研究的帮助评估
h
"""


class Args:
    pass


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof = self.root / "Professor"
        (self.prof / "论文分析").mkdir(parents=True)
        self.pdf = self.root / "paper.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nbody")
        self.abstract = self.root / "input.json"
        self.abstract.write_text(
            json.dumps({"schema": 1, "kind": "paper-analysis-input", "level": "abstract", "abstract": "secret"}),
            encoding="utf-8",
        )
        self.future = self.root / "future-work"
        self.future.write_text(
            "#!/usr/bin/env python3\n"
            "import json,pathlib,sys\n"
            "cmd=sys.argv[1]\n"
            "def arg(n): return pathlib.Path(sys.argv[sys.argv.index(n)+1])\n"
            "if cmd=='validate': print(json.dumps({'result':'ok'}))\n"
            "elif cmd=='merge-ocr':\n"
            " p=json.loads(arg('--prepared').read_text()); p['ocr_required_pages']=[]; print(json.dumps(p))\n"
            "elif cmd=='finalize':\n"
            " a=arg('--analysis'); side=pathlib.Path(str(a)+'.future_work.json'); side.write_text(json.dumps({'schema':1,'status':'ok','analysis':a.name,'items':[]}),encoding='utf-8'); print(json.dumps({'result':'ok'}))\n",
            encoding="utf-8",
        )
        self.future.chmod(self.future.stat().st_mode | stat.S_IEXEC)

    def tearDown(self):
        self.temp.cleanup()

    def _build(self, jobs):
        jobs_file = self.root / "jobs.json"
        jobs_file.write_text(json.dumps({"schema": 1, "professor": "Professor", "jobs": jobs}), encoding="utf-8")
        args = Args()
        args.professor_dir = self.prof
        args.jobs = jobs_file
        args.professor = None
        return handoff.build_bundle(args)

    def _result_zip(self, bundle, rows, analyses=True):
        bundle_path = Path(bundle["bundle_path"])
        with zipfile.ZipFile(bundle_path) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        result = self.root / "result.zip"
        with zipfile.ZipFile(result, "w") as zf:
            result_manifest = {
                "schema": 1,
                "kind": handoff.RESULT_KIND,
                "handoff_id": manifest["handoff_id"],
                "source_fingerprint": manifest["source_fingerprint"],
                "results": rows,
            }
            zf.writestr("result_manifest.json", json.dumps(result_manifest))
            if analyses:
                for row in rows:
                    safe = handoff._safe_component(row["job_id"])
                    zf.writestr(f"results/{safe}/analysis.md", ANALYSIS)
        return result, manifest

    def test_pdf_bundle_is_deterministic_and_portable(self):
        job = {
            "item_key": "ABC",
            "carrier": "pdf",
            "level": "fulltext",
            "input_path": str(self.pdf.resolve()),
            "analysis_relpath": "论文分析/A/T.md",
            "research_direction": {"collection_key": "C", "name_ja": "ja", "name_zh": "zh", "user_note": "note"},
        }
        first = self._build([job])
        second = self._build([job])
        self.assertEqual(first["handoff_id"], second["handoff_id"])
        with zipfile.ZipFile(first["bundle_path"]) as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
        self.assertIn("papers/ABC/paper.pdf", names)
        self.assertFalse(any(str(self.root) in name for name in names))
        self.assertEqual(manifest["jobs"][0]["input_sha256"], handoff._sha256_file(self.pdf))

    def test_abstract_bundle_has_no_fake_pdf(self):
        job = {
            "item_key": "ABS",
            "carrier": "abstract_json",
            "level": "abstract",
            "input_path": str(self.abstract.resolve()),
            "analysis_relpath": "论文分析/A/Abs.md",
            "research_direction": {},
        }
        bundle = self._build([job])
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            names = zf.namelist()
        self.assertIn("papers/ABS/paper-analysis-input.json", names)
        self.assertFalse(any(name.endswith("paper.pdf") for name in names))

    def test_valid_result_installs_analysis_and_index(self):
        job = {
            "item_key": "ABC",
            "carrier": "pdf",
            "level": "fulltext",
            "input_path": str(self.pdf.resolve()),
            "analysis_relpath": "论文分析/A/T.md",
            "research_direction": {},
            "authorship": "corresponding",
            "relevance_reason": "relevant",
        }
        bundle = self._build([job])
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        mjob = manifest["jobs"][0]
        row = {"job_id": mjob["job_id"], "item_key": "ABC", "input_sha256": mjob["input_sha256"], "status": "ok"}
        result, _ = self._result_zip(bundle, [row])
        args = Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle["bundle_path"])
        args.result = result
        args.future_work_script = self.future
        out = handoff.import_result(args)
        self.assertEqual(out["status"], "imported")
        target = self.prof / "论文分析/A/T.md"
        self.assertTrue(target.is_file())
        index = json.loads((self.prof / "论文分析/_index.json").read_text())
        self.assertEqual(index["papers"]["ABC"]["analysis_executor"], "chatgpt_handoff")
        self.assertEqual(index["papers"]["ABC"]["level"], "fulltext")

    def test_future_work_selection_is_finalized_locally(self):
        prepared = self.root / "prepare.json"
        candidates = self.root / "candidates.json"
        prepared.write_text(json.dumps({"pdf_sha256": "abc", "ocr_required_pages": [], "candidates": []}), encoding="utf-8")
        candidates.write_text(json.dumps({"candidates": []}), encoding="utf-8")
        job = {
            "item_key": "FW",
            "carrier": "pdf",
            "level": "fulltext",
            "input_path": str(self.pdf.resolve()),
            "analysis_relpath": "论文分析/A/FW.md",
            "research_direction": {},
            "future_work_prepare": str(prepared.resolve()),
            "future_work_candidates": str(candidates.resolve()),
        }
        bundle = self._build([job])
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        mjob = manifest["jobs"][0]
        row = {"job_id": mjob["job_id"], "item_key": "FW", "input_sha256": mjob["input_sha256"], "status": "ok"}
        result = self.root / "fw-result.zip"
        safe = handoff._safe_component(mjob["job_id"])
        with zipfile.ZipFile(result, "w") as zf:
            zf.writestr(
                "result_manifest.json",
                json.dumps({
                    "schema": 1,
                    "kind": handoff.RESULT_KIND,
                    "handoff_id": manifest["handoff_id"],
                    "source_fingerprint": manifest["source_fingerprint"],
                    "results": [row],
                }),
            )
            zf.writestr(f"results/{safe}/analysis.md", ANALYSIS)
            zf.writestr(f"results/{safe}/future_work_items.json", json.dumps({"items": []}))
        args = Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle["bundle_path"])
        args.result = result
        args.future_work_script = self.future
        out = handoff.import_result(args)
        self.assertEqual(out["status"], "imported")
        side = Path(str(self.prof / "论文分析/A/FW.md") + ".future_work.json")
        self.assertTrue(side.is_file())
        index = json.loads((self.prof / "论文分析/_index.json").read_text())
        self.assertEqual(index["papers"]["FW"]["future_work_state"], "valid")

    def test_unknown_job_rejected(self):
        job = {
            "item_key": "ABC",
            "carrier": "pdf",
            "level": "fulltext",
            "input_path": str(self.pdf.resolve()),
            "analysis_relpath": "论文分析/A/T.md",
            "research_direction": {},
        }
        bundle = self._build([job])
        row = {"job_id": "unknown", "item_key": "ABC", "input_sha256": "x", "status": "ok"}
        result, _ = self._result_zip(bundle, [row], analyses=False)
        args = Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle["bundle_path"])
        args.result = result
        args.future_work_script = self.future
        with self.assertRaisesRegex(ValueError, "external_result_unknown_job"):
            handoff.import_result(args)

    def test_unsafe_zip_path_rejected(self):
        bad = self.root / "bad.zip"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("../escape", "x")
        with self.assertRaisesRegex(ValueError, "unsafe_zip_entry"):
            handoff._extract_checked(bad, self.root / "extract")

    def test_newer_bundle_makes_old_bundle_stale(self):
        base = {
            "item_key": "ABC",
            "carrier": "pdf",
            "level": "fulltext",
            "input_path": str(self.pdf.resolve()),
            "analysis_relpath": "论文分析/A/T.md",
            "research_direction": {"user_note": "one"},
        }
        old = self._build([base])
        with zipfile.ZipFile(old["bundle_path"]) as zf:
            old_manifest = json.loads(zf.read("manifest.json"))
        oldjob = old_manifest["jobs"][0]
        row = {"job_id": oldjob["job_id"], "item_key": "ABC", "input_sha256": oldjob["input_sha256"], "status": "ok"}
        result, _ = self._result_zip(old, [row])
        changed = dict(base)
        changed["research_direction"] = {"user_note": "two"}
        self._build([changed])
        args = Args()
        args.professor_dir = self.prof
        args.bundle = Path(old["bundle_path"])
        args.result = result
        args.future_work_script = self.future
        out = handoff.import_result(args)
        self.assertEqual(out["reason_code"], "handoff_stale")


if __name__ == "__main__":
    unittest.main()
