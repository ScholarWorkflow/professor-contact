import importlib.util
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_chatgpt_handoff.py"
SKILL = ROOT / "SKILL.md"
AGENT = ROOT.parents[1] / "agents" / "professor-contact-analyzer.agent.md"
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
        self.ocr = self.prof / "论文分析/_ocr/T.txt"
        self.ocr.parent.mkdir(parents=True)
        self.ocr.write_text("existing OCR", encoding="utf-8")
        self.prepared = self.root / "prepare.json"
        self.candidates = self.root / "candidates.json"
        self._write_future_inputs()

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

    def _write_future_inputs(self, *, ocr_required_pages=None):
        self.prepared.write_text(
            json.dumps({
                "schema": 1,
                "pdf_sha256": handoff._sha256_file(self.pdf),
                "ocr_required_pages": list(ocr_required_pages or []),
                "candidates": [],
            }),
            encoding="utf-8",
        )
        self.candidates.write_text(json.dumps({"candidates": []}), encoding="utf-8")

    def _build(self, jobs):
        jobs_file = self.root / "jobs.json"
        jobs_file.write_text(json.dumps({"schema": 1, "professor": "Professor", "jobs": jobs}), encoding="utf-8")
        args = Args()
        args.professor_dir = self.prof
        args.jobs = jobs_file
        args.professor = None
        return handoff.build_bundle(args)

    def _manifest(self, bundle):
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            return json.loads(zf.read("manifest.json"))

    def _result_zip(self, bundle, rows, extra=None, *, include_future_work=True, analysis_text=ANALYSIS):
        manifest = self._manifest(bundle)
        result = self.root / f"result-{manifest['handoff_id']}.zip"
        jobs = {job["job_id"]: job for job in manifest["jobs"]}
        with zipfile.ZipFile(result, "w") as zf:
            zf.writestr(
                "result_manifest.json",
                json.dumps({
                    "schema": 1,
                    "kind": handoff.RESULT_KIND,
                    "handoff_id": manifest["handoff_id"],
                    "source_fingerprint": manifest["source_fingerprint"],
                    "results": rows,
                }),
            )
            for row in rows:
                job = jobs.get(row["job_id"])
                if not job:
                    continue
                safe = handoff._safe_component(row["job_id"])
                zf.writestr(f"results/{safe}/analysis.md", analysis_text)
                if include_future_work and (job.get("expected") or {}).get("future_work"):
                    zf.writestr(f"results/{safe}/future_work_items.json", json.dumps({"items": []}))
                if extra:
                    for name, data in extra.items():
                        zf.writestr(f"results/{safe}/{name}", data)
        return result

    def _import(self, bundle, result):
        args = Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle["bundle_path"])
        args.result = result
        args.future_work_script = self.future
        return handoff.import_result(args)

    def _pdf_job(self, key="ABC", rel="论文分析/A/T.md", with_future_work=True, **extra):
        job = {
            "item_key": key,
            "carrier": "pdf",
            "level": "fulltext",
            "input_path": str(self.pdf.resolve()),
            "analysis_relpath": rel,
            "research_direction": {},
        }
        if with_future_work:
            job.update({
                "future_work_prepare": str(self.prepared.resolve()),
                "future_work_candidates": str(self.candidates.resolve()),
            })
        job.update(extra)
        return job

    def test_pdf_bundle_is_deterministic_and_portable(self):
        job = self._pdf_job(
            research_direction={"collection_key": "C", "name_ja": "ja", "name_zh": "zh", "user_note": "note"},
            ocr_file=str(self.ocr.resolve()),
        )
        first = self._build([job])
        second = self._build([job])
        self.assertEqual(first["handoff_id"], second["handoff_id"])
        with zipfile.ZipFile(first["bundle_path"]) as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
        self.assertIn("papers/ABC/paper.pdf", names)
        self.assertEqual(manifest["jobs"][0]["input_sha256"], handoff._sha256_file(self.pdf))
        metadata = manifest["jobs"][0]["index_metadata"]
        self.assertNotIn("ocr_file", metadata)
        self.assertEqual(metadata["ocr_relpath"], "论文分析/_ocr/T.txt")
        serialized = json.dumps(manifest, ensure_ascii=False)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn(str(self.prof), serialized)
        self.assertFalse(any(str(self.root) in name for name in names))

    def test_fulltext_bundle_requires_future_work_contract(self):
        with self.assertRaisesRegex(ValueError, "fulltext handoff requires future_work_prepare"):
            self._build([self._pdf_job(with_future_work=False)])

    def test_abstract_bundle_has_no_fake_pdf(self):
        bundle = self._build([{
            "item_key": "ABS",
            "carrier": "abstract_json",
            "level": "abstract",
            "input_path": str(self.abstract.resolve()),
            "analysis_relpath": "论文分析/A/Abs.md",
            "research_direction": {},
        }])
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
        self.assertIn("papers/ABS/paper-analysis-input.json", names)
        self.assertFalse(any(name.endswith("paper.pdf") for name in names))
        self.assertFalse(manifest["jobs"][0]["expected"]["future_work"])

    def test_valid_result_installs_analysis_sidecar_and_index(self):
        bundle = self._build([self._pdf_job(authorship="corresponding", relevance_reason="relevant")])
        job = self._manifest(bundle)["jobs"][0]
        result = self._result_zip(bundle, [{
            "job_id": job["job_id"], "item_key": "ABC", "input_sha256": job["input_sha256"], "status": "ok"
        }])
        out = self._import(bundle, result)
        self.assertEqual(out["status"], "imported")
        index = json.loads((self.prof / "论文分析/_index.json").read_text())
        entry = index["papers"]["ABC"]
        self.assertEqual(entry["analysis_executor"], "chatgpt_handoff")
        self.assertEqual(entry["level"], "fulltext")
        self.assertEqual(entry["future_work_state"], "valid")
        self.assertTrue(Path(entry["future_work_sidecar"]).is_file())

    def test_future_work_selection_is_finalized_locally(self):
        bundle = self._build([self._pdf_job(key="FW", rel="论文分析/A/FW.md")])
        job = self._manifest(bundle)["jobs"][0]
        result = self._result_zip(
            bundle,
            [{"job_id": job["job_id"], "item_key": "FW", "input_sha256": job["input_sha256"], "status": "ok"}],
        )
        out = self._import(bundle, result)
        self.assertEqual(out["status"], "imported")
        sidecar = Path(str(self.prof / "论文分析/A/FW.md") + ".future_work.json")
        self.assertTrue(sidecar.is_file())
        self.assertEqual(json.loads(sidecar.read_text())["analysis"], "FW.md")

    def test_wait_pdf_missing_future_work_payload_is_not_fully_imported(self):
        bundle = self._build([self._pdf_job()])
        job = self._manifest(bundle)["jobs"][0]
        result = self._result_zip(
            bundle,
            [{"job_id": job["job_id"], "item_key": "ABC", "input_sha256": job["input_sha256"], "status": "ok"}],
            include_future_work=False,
        )
        out = self._import(bundle, result)
        self.assertEqual(out["status"], "needs_external_result")
        self.assertEqual(out["reason_code"], "external_result_incomplete")
        self.assertIn(job["job_id"], out["missing"])
        self.assertFalse((self.prof / "论文分析/A/T.md").exists())
        self.assertFalse((self.prof / "论文分析/_index.json").exists())

    def test_abstract_import_neutralizes_unvalidated_future_work(self):
        bundle = self._build([{
            "item_key": "ABS",
            "carrier": "abstract_json",
            "level": "abstract",
            "input_path": str(self.abstract.resolve()),
            "analysis_relpath": "论文分析/A/Abs.md",
            "research_direction": {},
        }])
        job = self._manifest(bundle)["jobs"][0]
        malicious = ANALYSIS.replace("—（论文未明示 future work）", "外部声称：下一步一定做 SECRET FUTURE WORK")
        result = self._result_zip(bundle, [{
            "job_id": job["job_id"], "item_key": "ABS", "input_sha256": job["input_sha256"], "status": "ok"
        }], analysis_text=malicious)
        out = self._import(bundle, result)
        self.assertEqual(out["status"], "imported")
        target = self.prof / "论文分析/A/Abs.md"
        self.assertNotIn("SECRET FUTURE WORK", target.read_text())
        index = json.loads((self.prof / "论文分析/_index.json").read_text())
        self.assertEqual(index["papers"]["ABS"]["future_work_state"], "failed")
        self.assertIsNone(index["papers"]["ABS"]["future_work_sidecar"])

    def test_unknown_job_rejected(self):
        bundle = self._build([self._pdf_job()])
        result = self._result_zip(bundle, [{"job_id": "unknown", "item_key": "ABC", "input_sha256": "x", "status": "ok"}])
        with self.assertRaisesRegex(ValueError, "external_result_unknown_job"):
            self._import(bundle, result)

    def test_unsafe_zip_path_rejected(self):
        bad = self.root / "bad.zip"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("../escape", "x")
        with self.assertRaisesRegex(ValueError, "unsafe_zip_entry"):
            handoff._extract_checked(bad, self.root / "extract")

    def test_newer_bundle_makes_old_bundle_stale(self):
        base = self._pdf_job(research_direction={"user_note": "one"})
        old = self._build([base])
        job = self._manifest(old)["jobs"][0]
        result = self._result_zip(old, [{
            "job_id": job["job_id"], "item_key": "ABC", "input_sha256": job["input_sha256"], "status": "ok"
        }])
        changed = dict(base)
        changed["research_direction"] = {"user_note": "two"}
        self._build([changed])
        self.assertEqual(self._import(old, result)["reason_code"], "handoff_stale")

    def test_changed_pdf_creates_new_handoff_and_rejects_old_result(self):
        job = self._pdf_job()
        old = self._build([job])
        old_job = self._manifest(old)["jobs"][0]
        result = self._result_zip(old, [{
            "job_id": old_job["job_id"], "item_key": "ABC", "input_sha256": old_job["input_sha256"], "status": "ok"
        }])
        self.pdf.write_bytes(b"%PDF-1.4\nchanged-body")
        self._write_future_inputs()
        new = self._build([job])
        self.assertNotEqual(old["handoff_id"], new["handoff_id"])
        self.assertEqual(self._import(old, result)["reason_code"], "handoff_stale")

    def test_existing_abstract_analysis_can_be_upgraded_when_baseline_unchanged(self):
        target = self.prof / "论文分析/A/T.md"
        target.parent.mkdir(parents=True)
        target.write_text("old abstract analysis", encoding="utf-8")
        index = {
            "schema": 2,
            "future_work_schema": 1,
            "professor": "Professor",
            "papers": {"ABC": {"file": str(target), "level": "abstract", "generated_at": "old"}},
        }
        (self.prof / "论文分析/_index.json").write_text(json.dumps(index), encoding="utf-8")
        bundle = self._build([self._pdf_job()])
        job = self._manifest(bundle)["jobs"][0]
        self.assertTrue(job["local_baseline"]["analysis_exists"])
        self.assertEqual(job["local_baseline"]["index_level"], "abstract")
        result = self._result_zip(bundle, [{
            "job_id": job["job_id"], "item_key": "ABC", "input_sha256": job["input_sha256"], "status": "ok"
        }])
        out = self._import(bundle, result)
        self.assertEqual(out["status"], "imported")
        self.assertIn("## 总结", target.read_text())
        upgraded = json.loads((self.prof / "论文分析/_index.json").read_text())
        self.assertEqual(upgraded["papers"]["ABC"]["level"], "fulltext")
        self.assertEqual(upgraded["papers"]["ABC"]["future_work_state"], "valid")

    def test_newer_local_analysis_after_bundle_is_rejected(self):
        target = self.prof / "论文分析/A/T.md"
        target.parent.mkdir(parents=True)
        target.write_text("old abstract analysis", encoding="utf-8")
        index = {
            "schema": 2,
            "future_work_schema": 1,
            "professor": "Professor",
            "papers": {"ABC": {"file": str(target), "level": "abstract"}},
        }
        (self.prof / "论文分析/_index.json").write_text(json.dumps(index), encoding="utf-8")
        bundle = self._build([self._pdf_job()])
        job = self._manifest(bundle)["jobs"][0]
        result = self._result_zip(bundle, [{
            "job_id": job["job_id"], "item_key": "ABC", "input_sha256": job["input_sha256"], "status": "ok"
        }])
        target.write_text("newer local fulltext analysis", encoding="utf-8")
        index["papers"]["ABC"]["level"] = "fulltext"
        (self.prof / "论文分析/_index.json").write_text(json.dumps(index), encoding="utf-8")
        out = self._import(bundle, result)
        self.assertEqual(out["reason_code"], "handoff_stale")
        self.assertEqual(target.read_text(), "newer local fulltext analysis")

    def test_workflow_contract_wires_continue_wait_and_resume(self):
        skill = SKILL.read_text(encoding="utf-8")
        agent = AGENT.read_text(encoding="utf-8")
        self.assertIn("chatgpt_handoff=continue", skill)
        self.assertIn("chatgpt_handoff=wait", skill)
        self.assertIn("非交互/旧自动化没有该字段时固定按 `continue`", skill)
        self.assertIn("chatgpt_result", skill)
        self.assertIn("stage2_chatgpt_handoff.py build", agent)
        self.assertIn("stage2_chatgpt_handoff.py import", agent)
        self.assertIn("本轮刚 build 的 current `bundle_path`", agent)
        self.assertIn("needs_external_result", agent)
        self.assertIn("任何新 vision OCR/`paper-analysis full|gap-only` 前停止", agent)
        self.assertIn("字段缺失按非交互/向后兼容语义固定为 `continue`", agent)
        self.assertIn("Stage 3 仍只读 `套磁候选输入.json`", agent)


if __name__ == "__main__":
    unittest.main()
