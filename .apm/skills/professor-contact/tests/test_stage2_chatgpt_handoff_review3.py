import importlib.util
import json
import os
import stat
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_chatgpt_handoff.py"
AGENT = ROOT.parents[1] / "agents" / "professor-contact-analyzer.agent.md"
SPEC = importlib.util.spec_from_file_location("stage2_chatgpt_handoff_review3", SCRIPT)
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

FACTS_DRAFT = {
    "paper": {"title": "Paper", "authors": ["Author A"], "year": 2024, "venue": "Venue", "doi": None},
    "research_problem": "problem",
    "research_object": "object",
    "approach": "approach",
    "findings": ["finding"],
    "contributions": ["contribution"],
    "topic_terms": ["topic"],
    "limitations": ["limitation"],
    "confidence": 0.8,
}

FAKE_FACTS_SCRIPT = (
    "#!/usr/bin/env python3\n"
    "import hashlib,json,pathlib,sys\n"
    "cmd=sys.argv[1]\n"
    "def arg(n): return pathlib.Path(sys.argv[sys.argv.index(n)+1])\n"
    "if cmd=='validate':\n"
    " d=json.loads(arg('--draft').read_text()); print(json.dumps({'ok':True,'facts':d}))\n"
    "elif cmd=='finalize':\n"
    " a=arg('--analysis'); draft=json.loads(arg('--draft').read_text());\n"
    " side=json.loads(arg('--future-work').read_text());\n"
    " assert side.get('status')=='ok' and side.get('analysis')==a.name, 'sidecar mismatch';\n"
    " fp='sha256:'+hashlib.sha256(arg('--input').read_bytes()).hexdigest();\n"
    " ids=[i.get('id') for i in side.get('items',[]) if i.get('id')];\n"
    " out={'schema':1,'kind':'paper-analysis-facts','generator_version':'facts-v1','analysis':a.name,'input_fingerprint':fp,'evidence_level':'fulltext','status':'ok'};\n"
    " out.update(draft); out['future_work_ids']=ids;\n"
    " pathlib.Path(str(a)+'.facts.json').write_text(json.dumps(out),encoding='utf-8');\n"
    " print(json.dumps({'ok':True}))\n"
)


class Args:
    pass


class Review3RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof = self.root / "Professor"
        (self.prof / "论文分析").mkdir(parents=True)
        self.abstract = self.root / "input.json"
        self.abstract.write_text(
            json.dumps({"schema": 1, "kind": "paper-analysis-input", "level": "abstract", "abstract": "x"}),
            encoding="utf-8",
        )
        self.pdf = self.root / "paper.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nbody")
        self.prepare = self.root / "prepare.json"
        self.candidates = self.root / "candidates.json"

        self.future = self.root / "future-work"
        self.future.write_text(
            "#!/usr/bin/env python3\n"
            "import hashlib,json,pathlib,re,sys,unicodedata\n"
            "cmd=sys.argv[1]\n"
            "def arg(n): return pathlib.Path(sys.argv[sys.argv.index(n)+1])\n"
            "def norm(s): return re.sub(r'\\s+',' ',unicodedata.normalize('NFKC',s).strip())\n"
            "if cmd=='merge-ocr':\n"
            " p=json.loads(arg('--prepared').read_text()); o=json.loads(arg('--ocr').read_text());\n"
            " page=int(next(iter(o['pages']))); quote=norm(o['pages'][str(page)]);\n"
            " p['ocr_required_pages']=[]; p['ocr_resolved_pages']=[page];\n"
            " p['candidates']=[{'id':hashlib.sha256(quote.encode()).hexdigest(),'quote':quote,'page':page}];\n"
            " print(json.dumps(p))\n"
            "elif cmd=='validate':\n"
            " items=json.loads(arg('--items').read_text()).get('items',[]); c=json.loads(arg('--candidates').read_text()).get('candidates',[]);\n"
            " loc={(norm(x['quote']),x['page']) for x in c};\n"
            " assert all((norm(x['quote']),x['page']) in loc for x in items); print(json.dumps({'result':'ok'}))\n"
            "elif cmd=='finalize':\n"
            " a=arg('--analysis'); items=json.loads(arg('--items').read_text()).get('items',[]);\n"
            " side=pathlib.Path(str(a)+'.future_work.json');\n"
            " side.write_text(json.dumps({'schema':1,'status':'ok','analysis':a.name,'items':items}),encoding='utf-8');\n"
            " print(json.dumps({'result':'ok'}))\n",
            encoding="utf-8",
        )
        self.future.chmod(0o644)
        self.facts_script = self.root / "facts.py"
        self.facts_script.write_text(FAKE_FACTS_SCRIPT, encoding="utf-8")
        self.facts_script.chmod(0o644)
        self.old_path = os.environ.get("PATH", "")
        self.old_uv_test_log = os.environ.get("UV_TEST_LOG")
        self.uv_log = self.root / "uv.log"
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        fake_uv = fake_bin / "uv"
        fake_uv.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"$UV_TEST_LOG\"\n"
            "[ \"$1\" = \"run\" ] || exit 2\n"
            "shift\n"
            "exec python3 \"$@\"\n",
            encoding="utf-8",
        )
        fake_uv.chmod(fake_uv.stat().st_mode | stat.S_IEXEC)
        os.environ["PATH"] = str(fake_bin) + os.pathsep + self.old_path
        os.environ["UV_TEST_LOG"] = str(self.uv_log)

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        if self.old_uv_test_log is None:
            os.environ.pop("UV_TEST_LOG", None)
        else:
            os.environ["UV_TEST_LOG"] = self.old_uv_test_log
        self.temp.cleanup()

    def _build_abstract(self):
        jobs = self.root / "jobs-abstract.json"
        jobs.write_text(
            json.dumps({
                "schema": 1,
                "professor": "Professor",
                "jobs": [{
                    "item_key": "ABS",
                    "carrier": "abstract_json",
                    "level": "abstract",
                    "input_path": str(self.abstract.resolve()),
                    "analysis_relpath": "论文分析/A/Abs.md",
                    "research_direction": {"collection_key": "C", "user_note": "note"},
                }],
            }),
            encoding="utf-8",
        )
        args = Args()
        args.professor_dir = self.prof
        args.jobs = jobs
        args.professor = None
        return handoff.build_bundle(args)

    def _write_future_inputs(self, required_pages):
        self.prepare.write_text(
            json.dumps({
                "schema": 1,
                "pdf_sha256": handoff._sha256_file(self.pdf),
                "ocr_required_pages": list(required_pages),
                "selection": {"pages": list(required_pages)},
                "candidates": [{"id": "old", "quote": "garbled old extraction", "page": 2}],
            }),
            encoding="utf-8",
        )
        self.candidates.write_text(
            json.dumps({"candidates": [{"id": "old", "quote": "garbled old extraction", "page": 2}]}),
            encoding="utf-8",
        )

    def _build_pdf(self, *, required_pages=(), key="ABC", rel="论文分析/A/T.md"):
        self._write_future_inputs(required_pages)
        jobs = self.root / "jobs-pdf.json"
        jobs.write_text(
            json.dumps({
                "schema": 1,
                "professor": "Professor",
                "jobs": [{
                    "item_key": key,
                    "carrier": "pdf",
                    "level": "fulltext",
                    "input_path": str(self.pdf.resolve()),
                    "analysis_relpath": rel,
                    "research_direction": {},
                    "future_work_prepare": str(self.prepare.resolve()),
                    "future_work_candidates": str(self.candidates.resolve()),
                }],
            }),
            encoding="utf-8",
        )
        args = Args()
        args.professor_dir = self.prof
        args.jobs = jobs
        args.professor = None
        return handoff.build_bundle(args)

    def _manifest(self, bundle):
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            return json.loads(zf.read("manifest.json"))

    def _abstract_result(self, bundle):
        manifest = self._manifest(bundle)
        job = manifest["jobs"][0]
        result = self.root / "result-abstract.zip"
        with zipfile.ZipFile(result, "w") as zf:
            zf.writestr(
                "result_manifest.json",
                json.dumps({
                    "schema": 1,
                    "kind": handoff.RESULT_KIND,
                    "handoff_id": manifest["handoff_id"],
                    "source_fingerprint": manifest["source_fingerprint"],
                    "results": [{
                        "job_id": job["job_id"],
                        "item_key": job["item_key"],
                        "input_sha256": job["input_sha256"],
                        "status": "ok",
                    }],
                }),
            )
            zf.writestr(
                f"results/{handoff._safe_component(job['job_id'])}/analysis.md",
                ANALYSIS,
            )
        return result

    def _pdf_result(self, bundle, *, ocr=False, selections=False):
        manifest = self._manifest(bundle)
        job = manifest["jobs"][0]
        result = self.root / "result-pdf.zip"
        safe = handoff._safe_component(job["job_id"])
        with zipfile.ZipFile(result, "w") as zf:
            zf.writestr("result_manifest.json", json.dumps({
                "schema": 1,
                "kind": handoff.RESULT_KIND,
                "handoff_id": manifest["handoff_id"],
                "source_fingerprint": manifest["source_fingerprint"],
                "results": [{
                    "job_id": job["job_id"],
                    "item_key": job["item_key"],
                    "input_sha256": job["input_sha256"],
                    "status": "ok",
                }],
            }))
            zf.writestr(f"results/{safe}/analysis.md", ANALYSIS)
            if ocr:
                zf.writestr(
                    f"results/{safe}/future_work_ocr.json",
                    json.dumps({"pages": {"2": "We will extend the method to multilingual settings."}}),
                )
            if selections:
                zf.writestr(
                    f"results/{safe}/future_work_selections.json",
                    json.dumps({"items": [{
                        "page": 2,
                        "quote_excerpt": "extend the method to multilingual",
                        "translation_zh": "我们将把该方法扩展到多语言场景。",
                        "source": "Conclusion",
                    }]}),
                )
            if not ocr:
                zf.writestr(f"results/{safe}/future_work_items.json", json.dumps({"items": []}))
            zf.writestr(f"results/{safe}/facts.json", json.dumps(FACTS_DRAFT))
        return result

    def _import(self, bundle_path, result, *, future_script=None):
        args = Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle_path)
        args.result = result
        args.future_work_script = future_script or self.future
        return handoff.import_result(args)

    def test_manifest_target_and_baseline_tamper_rejected_with_old_ids(self):
        bundle = self._build_abstract()
        result = self._abstract_result(bundle)
        tampered = self.root / "tampered-bundle.zip"
        with zipfile.ZipFile(bundle["bundle_path"]) as source, zipfile.ZipFile(tampered, "w") as sink:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "manifest.json":
                    manifest = json.loads(data)
                    manifest["jobs"][0]["analysis_relpath"] = "论文分析/A/redirected.md"
                    manifest["jobs"][0]["local_baseline"]["analysis_exists"] = True
                    data = json.dumps(manifest).encode("utf-8")
                sink.writestr(info, data)

        out = self._import(tampered, result)
        self.assertEqual(out["status"], "needs_external_result")
        self.assertEqual(out["reason_code"], "external_result_hash_mismatch")
        self.assertFalse((self.prof / "论文分析/A/redirected.md").exists())
        self.assertFalse((self.prof / "论文分析/A/Abs.md").exists())
        self.assertFalse((self.prof / "论文分析/_index.json").exists())

    def test_professor_lock_serializes_final_guard_and_preserves_fresh_other_entry(self):
        bundle = self._build_abstract()
        manifest = self._manifest(bundle)
        job = manifest["jobs"][0]
        staged = self.root / "staged.md"
        staged.write_text(ANALYSIS, encoding="utf-8")
        index_path = self.prof / "论文分析/_index.json"

        started = threading.Event()
        done = threading.Event()
        errors = []

        def installer():
            started.set()
            try:
                handoff._install_job(self.prof, manifest, job, staged, None)
            except BaseException as error:
                errors.append(error)
            finally:
                done.set()

        with handoff._professor_lock(self.prof):
            thread = threading.Thread(target=installer, daemon=True)
            thread.start()
            self.assertTrue(started.wait(1.0))
            self.assertFalse(done.wait(0.1))
            index_path.write_text(
                json.dumps({
                    "schema": 2,
                    "future_work_schema": 1,
                    "professor": "Professor",
                    "papers": {"OTHER": {"generated_at": "newer-concurrent"}},
                }),
                encoding="utf-8",
            )

        thread.join(2.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(index["papers"]["OTHER"]["generated_at"], "newer-concurrent")
        self.assertIn("ABS", index["papers"])

    def test_ocr_required_selection_rebinds_after_merge_without_external_candidate_id(self):
        bundle = self._build_pdf(required_pages=[2], key="OCRFW", rel="论文分析/A/OCRFW.md")
        manifest = self._manifest(bundle)
        job = manifest["jobs"][0]
        self.assertEqual(job["future_work"]["selection_contract"], "ocr-excerpt-v1")
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            instructions = zf.read("instructions.md").decode("utf-8")
        self.assertIn("future_work_selections.json", instructions)
        self.assertIn("Do NOT guess candidate ids", instructions)

        out = self._import(bundle["bundle_path"], self._pdf_result(bundle, ocr=True, selections=True))
        self.assertEqual(out["status"], "imported")
        sidecar = Path(str(self.prof / "论文分析/A/OCRFW.md") + ".future_work.json")
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        self.assertEqual(payload["items"][0]["quote"], "We will extend the method to multilingual settings.")
        self.assertEqual(payload["items"][0]["page"], 2)
        calls = self.uv_log.read_text(encoding="utf-8")
        self.assertIn("merge-ocr", calls)
        self.assertIn("validate", calls)
        self.assertIn("finalize", calls)

    def test_ocr_required_old_premerge_items_without_selection_hint_is_incomplete(self):
        bundle = self._build_pdf(required_pages=[2])
        result = self._pdf_result(bundle, ocr=True, selections=False)
        # Add the old/pre-merge payload explicitly; the new contract must not
        # accept it as a substitute for post-merge candidate binding.
        rewritten = self.root / "result-old-contract.zip"
        with zipfile.ZipFile(result) as source, zipfile.ZipFile(rewritten, "w") as sink:
            for info in source.infolist():
                sink.writestr(info, source.read(info.filename))
            job = self._manifest(bundle)["jobs"][0]
            safe = handoff._safe_component(job["job_id"])
            sink.writestr(f"results/{safe}/future_work_items.json", json.dumps({"items": []}))
        out = self._import(bundle["bundle_path"], rewritten)
        self.assertEqual(out["status"], "needs_external_result")
        self.assertEqual(out["reason_code"], "external_result_incomplete")
        self.assertFalse((self.prof / "论文分析/A/T.md").exists())

    def test_local_writer_lease_blocks_import_even_when_writer_never_takes_professor_lock(self):
        bundle = self._build_pdf(required_pages=[])
        result = self._pdf_result(bundle)
        token = "local-stage2-run"
        handoff.acquire_local_lease(self.prof, token)
        index_path = self.prof / "论文分析/_index.json"

        # Simulate the actual legacy writer: direct write, deliberately without
        # `_professor_lock`. The registered lease is the coordination boundary.
        unrelated = {
            "schema": 2,
            "future_work_schema": 1,
            "professor": "Professor",
            "papers": {"OTHER": {"file": "new-local.md", "level": "fulltext", "generated_at": "newer"}},
        }
        index_path.write_text(json.dumps(unrelated), encoding="utf-8")
        blocked = self._import(bundle["bundle_path"], result)
        self.assertEqual(blocked["status"], "needs_external_result")
        self.assertEqual(blocked["reason_code"], "stage2_writer_busy")
        self.assertFalse((self.prof / "论文分析/A/T.md").exists())
        self.assertEqual(json.loads(index_path.read_text())["papers"]["OTHER"]["generated_at"], "newer")

        handoff.release_local_lease(self.prof, token)
        imported = self._import(bundle["bundle_path"], result)
        self.assertEqual(imported["status"], "imported")
        merged = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertIn("OTHER", merged["papers"])
        self.assertIn("ABC", merged["papers"])
        self.assertEqual(merged["papers"]["OTHER"]["generated_at"], "newer")

    def test_agent_contract_registers_and_releases_local_writer_lease(self):
        agent = AGENT.read_text(encoding="utf-8")
        self.assertIn("local-lease-acquire", agent)
        self.assertIn("local-lease-release", agent)
        self.assertIn("stage2_writer_busy", agent)
        self.assertIn("finally", agent)
        self.assertIn("future_work_selections.json", agent)
        self.assertIn("quote_excerpt", agent)


if __name__ == "__main__":
    unittest.main()
