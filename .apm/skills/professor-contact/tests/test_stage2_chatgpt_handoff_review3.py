import importlib.util
import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_chatgpt_handoff.py"
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

    def tearDown(self):
        self.temp.cleanup()

    def _build(self):
        jobs = self.root / "jobs.json"
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

    def _manifest(self, bundle):
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            return json.loads(zf.read("manifest.json"))

    def _result(self, bundle):
        manifest = self._manifest(bundle)
        job = manifest["jobs"][0]
        result = self.root / "result.zip"
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

    def _import(self, bundle_path, result):
        args = Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle_path)
        args.result = result
        args.future_work_script = self.root / "unused-future-work.py"
        return handoff.import_result(args)

    def test_manifest_target_and_baseline_tamper_rejected_with_old_ids(self):
        bundle = self._build()
        result = self._result(bundle)
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
        bundle = self._build()
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
            except BaseException as error:  # surfaced after join below
                errors.append(error)
            finally:
                done.set()

        # Hold the same professor-scoped lock while a concurrent installer
        # reaches the final install boundary. The installer must wait; the
        # unrelated index update made here must then be observed by its fresh
        # read/merge after the lock is released, rather than overwritten by a
        # stale whole-index snapshot.
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


if __name__ == "__main__":
    unittest.main()
