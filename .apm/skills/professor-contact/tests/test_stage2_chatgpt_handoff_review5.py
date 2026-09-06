import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import _stage2_handoff_test_support as support

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_chatgpt_handoff.py"
SPEC = importlib.util.spec_from_file_location("stage2_chatgpt_handoff_review5", SCRIPT)
handoff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(handoff)

ANALYSIS = support.ANALYSIS


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
        self.abstract_other = self.root / "paper-analysis-input-other.json"
        self.abstract_other.write_text(
            json.dumps({
                "schema": 1,
                "kind": "paper-analysis-input",
                "level": "abstract",
                "title": "Other Paper",
                "abstract": "other body",
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def _build(self, *, item_key="ABS", analysis_relpath="论文分析/A/Abs.md", input_path=None):
        jobs = self.root / f"jobs-{item_key}.json"
        jobs.write_text(
            json.dumps({
                "schema": 1,
                "professor": "Professor",
                "jobs": [{
                    "item_key": item_key,
                    "carrier": "abstract_json",
                    "level": "abstract",
                    "input_path": str((input_path or self.abstract).resolve()),
                    "analysis_relpath": analysis_relpath,
                    "research_direction": {},
                }],
            }),
            encoding="utf-8",
        )
        args = support.Args()
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
        result = self.root / f"result-{job['item_key']}.zip"
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
        args = support.Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle["bundle_path"])
        args.result = result
        args.future_work_script = self.root / "unused-future-work.py"
        return handoff.import_result(args)

    def _lease_cli(self, command, token, *, bundle=None):
        argv = [
            sys.executable,
            str(SCRIPT),
            command,
            "--professor-dir",
            str(self.prof),
            "--token",
            token,
        ]
        if command == "local-lease-acquire":
            if bundle is None:
                raise AssertionError("bundle is required for guarded lease acquisition")
            argv.extend([
                "--handoff-id",
                bundle["handoff_id"],
                "--source-fingerprint",
                bundle["source_fingerprint"],
            ])
        return subprocess.run(
            argv,
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

        acquire = self._lease_cli("local-lease-acquire", "run-a", bundle=bundle)
        self.assertEqual(acquire.returncode, 2, acquire.stdout + acquire.stderr)
        payload = json.loads(acquire.stdout)
        self.assertEqual(payload["reason_code"], "stage2_plan_stale")
        self.assertFalse((self.prof / "论文分析/.stage2-local-writer.json").exists())
        self.assertEqual(target.read_bytes(), imported_bytes)

    def test_unchanged_post_build_plan_can_acquire_guarded_lease(self):
        bundle = self._build()
        manifest = self._manifest(bundle)

        acquire = self._lease_cli("local-lease-acquire", "run-b", bundle=bundle)
        self.assertEqual(acquire.returncode, 0, acquire.stdout + acquire.stderr)
        payload = json.loads(acquire.stdout)
        self.assertEqual(payload["status"], "acquired")
        self.assertEqual(payload["handoff_id"], manifest["handoff_id"])
        self.assertEqual(payload["source_fingerprint"], manifest["source_fingerprint"])
        lease_payload = json.loads(
            (self.prof / "论文分析/.stage2-local-writer.json").read_text(encoding="utf-8")
        )
        self.assertEqual(lease_payload["handoff_id"], manifest["handoff_id"])
        self.assertEqual(lease_payload["source_fingerprint"], manifest["source_fingerprint"])

        release = self._lease_cli("local-lease-release", "run-b")
        self.assertEqual(release.returncode, 0, release.stdout + release.stderr)
        self.assertFalse((self.prof / "论文分析/.stage2-local-writer.json").exists())

    def test_competing_build_cannot_make_stale_run_validate_wrong_latest_plan(self):
        h1 = self._build()
        h1_target = self.prof / "论文分析/A/Abs.md"

        imported = self._import(h1, self._result_zip(h1))
        self.assertEqual(imported["status"], "imported")
        imported_bytes = h1_target.read_bytes()

        h2 = self._build(
            item_key="OTHER",
            analysis_relpath="论文分析/B/Other.md",
            input_path=self.abstract_other,
        )
        self.assertNotEqual(h1["handoff_id"], h2["handoff_id"])
        self.assertNotEqual(h1["source_fingerprint"], h2["source_fingerprint"])

        stale_acquire = self._lease_cli("local-lease-acquire", "run-h1", bundle=h1)
        self.assertEqual(stale_acquire.returncode, 2, stale_acquire.stdout + stale_acquire.stderr)
        stale_payload = json.loads(stale_acquire.stdout)
        self.assertEqual(stale_payload["reason_code"], "stage2_plan_stale")
        self.assertFalse((self.prof / "论文分析/.stage2-local-writer.json").exists())
        self.assertEqual(h1_target.read_bytes(), imported_bytes)

        current_acquire = self._lease_cli("local-lease-acquire", "run-h2", bundle=h2)
        self.assertEqual(current_acquire.returncode, 0, current_acquire.stdout + current_acquire.stderr)
        current_payload = json.loads(current_acquire.stdout)
        self.assertEqual(current_payload["handoff_id"], h2["handoff_id"])
        self.assertEqual(current_payload["source_fingerprint"], h2["source_fingerprint"])
        release = self._lease_cli("local-lease-release", "run-h2")
        self.assertEqual(release.returncode, 0, release.stdout + release.stderr)


if __name__ == "__main__":
    unittest.main()
