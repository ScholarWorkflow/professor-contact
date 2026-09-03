import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_chatgpt_handoff.py"
SPEC = importlib.util.spec_from_file_location("stage2_chatgpt_handoff_review5", SCRIPT)
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


class PostBuildLeaseGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof = self.root / "Professor"
        (self.prof / "论文分析").mkdir(parents=True)
        self.abstract = self.root / "paper-analysis-input.json"
        self.abstract.write_text(
            json.dumps({
                "schema": 1,
                "kind": "paper-analysis-input",
                "level": "abstract",
                "title": "Paper",
                "abstract": "body",
            }),
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
                    "research_direction": {},
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
        with zipfile.ZipFile(bundle["bundle_path"]) as archive:
            return json.loads(archive.read("manifest.json"))

    def _result_zip(self, bundle):
        manifest = self._manifest(bundle)
        job = manifest["jobs"][0]
        result = self.root / "result.zip"
        safe = handoff._safe_component(job["job_id"])
        with zipfile.ZipFile(result, "w") as archive:
            archive.writestr(
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
            archive.writestr(f"results/{safe}/analysis.md", ANALYSIS)
        return result

    def _import(self, bundle, result):
        args = Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle["bundle_path"])
        args.result = result
        args.future_work_script = self.root / "unused-future-work.py"
        return handoff.import_result(args)

    def _lease_cli(self, command, token):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                command,
                "--professor-dir",
                str(self.prof),
                "--token",
                token,
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def test_import_between_build_and_acquire_makes_local_plan_stale(self):
        bundle = self._build()
        target = self.prof / "论文分析/A/Abs.md"
        self.assertFalse(target.exists())

        imported = self._import(bundle, self._result_zip(bundle))
        self.assertEqual(imported["status"], "imported")
        imported_bytes = target.read_bytes()

        acquire = self._lease_cli("local-lease-acquire", "run-a")
        self.assertEqual(acquire.returncode, 2, acquire.stdout + acquire.stderr)
        payload = json.loads(acquire.stdout)
        self.assertEqual(payload["reason_code"], "stage2_plan_stale")
        self.assertFalse((self.prof / "论文分析/.stage2-local-writer.json").exists())
        self.assertEqual(target.read_bytes(), imported_bytes)

    def test_unchanged_post_build_plan_can_acquire_guarded_lease(self):
        bundle = self._build()
        manifest = self._manifest(bundle)

        acquire = self._lease_cli("local-lease-acquire", "run-b")
        self.assertEqual(acquire.returncode, 0, acquire.stdout + acquire.stderr)
        payload = json.loads(acquire.stdout)
        self.assertEqual(payload["status"], "acquired")
        self.assertEqual(payload["handoff_id"], manifest["handoff_id"])
        self.assertTrue((self.prof / "论文分析/.stage2-local-writer.json").exists())

        release = self._lease_cli("local-lease-release", "run-b")
        self.assertEqual(release.returncode, 0, release.stdout + release.stderr)
        self.assertFalse((self.prof / "论文分析/.stage2-local-writer.json").exists())


if __name__ == "__main__":
    unittest.main()
