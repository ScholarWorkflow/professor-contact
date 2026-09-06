import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import _stage2_handoff_test_support as support

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_chatgpt_handoff.py"
SPEC = importlib.util.spec_from_file_location("stage2_chatgpt_handoff_review", SCRIPT)
handoff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(handoff)

ANALYSIS_A = """# Paper A

## 总结
A summary
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
external text A
## 对自身研究的帮助评估
h
"""

ANALYSIS_B = ANALYSIS_A.replace("# Paper A", "# Paper B").replace("A summary", "B summary").replace("external text A", "external text B")


class Args:
    pass


class ReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof = self.root / "Professor"
        (self.prof / "论文分析").mkdir(parents=True)
        self.input_a = self.root / "A.json"
        self.input_b = self.root / "B.json"
        self.input_a.write_text(json.dumps({"schema": 1, "kind": "paper-analysis-input", "abstract": "A"}), encoding="utf-8")
        self.input_b.write_text(json.dumps({"schema": 1, "kind": "paper-analysis-input", "abstract": "B"}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _job(self, key: str, input_path: Path) -> dict:
        return {
            "item_key": key,
            "carrier": "abstract_json",
            "level": "abstract",
            "input_path": str(input_path.resolve()),
            "analysis_relpath": f"论文分析/A/{key}.md",
            "research_direction": {"collection_key": "C", "user_note": "same"},
        }

    def _build(self, jobs: list[dict]) -> dict:
        jobs_path = self.root / "jobs.json"
        jobs_path.write_text(json.dumps({"schema": 1, "professor": "Professor", "jobs": jobs}), encoding="utf-8")
        args = support.Args()
        args.professor_dir = self.prof
        args.jobs = jobs_path
        args.professor = None
        return handoff.build_bundle(args)

    def _manifest(self, bundle: dict) -> dict:
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            return json.loads(zf.read("manifest.json"))

    def _import(self, bundle: dict, result: Path) -> dict:
        args = support.Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle["bundle_path"])
        args.result = result
        args.future_work_script = self.root / "unused-future-work.py"
        return handoff.import_result(args)

    def test_job_order_does_not_change_handoff_or_zip_bytes(self):
        job_a = self._job("A", self.input_a)
        job_b = self._job("B", self.input_b)

        first = self._build([job_a, job_b])
        first_bytes = Path(first["bundle_path"]).read_bytes()
        first_manifest = self._manifest(first)

        second = self._build([job_b, job_a])
        second_bytes = Path(second["bundle_path"]).read_bytes()
        second_manifest = self._manifest(second)

        self.assertEqual(first["handoff_id"], second["handoff_id"])
        self.assertEqual(first["source_fingerprint"], second["source_fingerprint"])
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual([job["item_key"] for job in second_manifest["jobs"]], ["A", "B"])
        self.assertEqual(first_bytes, second_bytes)

    def test_result_dir_cross_wire_is_rejected_instead_of_installing_other_job(self):
        bundle = self._build([
            self._job("A", self.input_a),
            self._job("B", self.input_b),
        ])
        manifest = self._manifest(bundle)
        jobs = {job["item_key"]: job for job in manifest["jobs"]}
        safe_a = handoff._safe_component(jobs["A"]["job_id"])
        safe_b = handoff._safe_component(jobs["B"]["job_id"])

        result = self.root / "cross-wire.zip"
        with zipfile.ZipFile(result, "w") as zf:
            zf.writestr(
                "result_manifest.json",
                json.dumps({
                    "schema": 1,
                    "kind": handoff.RESULT_KIND,
                    "handoff_id": manifest["handoff_id"],
                    "source_fingerprint": manifest["source_fingerprint"],
                    "results": [
                        {
                            "job_id": jobs["A"]["job_id"],
                            "item_key": "A",
                            "input_sha256": jobs["A"]["input_sha256"],
                            "status": "ok",
                            "result_dir": safe_b,
                        },
                        {
                            "job_id": jobs["B"]["job_id"],
                            "item_key": "B",
                            "input_sha256": jobs["B"]["input_sha256"],
                            "status": "ok",
                            "result_dir": safe_a,
                        },
                    ],
                }),
            )
            # With the old importer, the row-level overrides above would cause
            # these two valid analyses to be silently installed into each other's targets.
            zf.writestr(f"results/{safe_a}/analysis.md", ANALYSIS_A)
            zf.writestr(f"results/{safe_b}/analysis.md", ANALYSIS_B)

        out = self._import(bundle, result)
        self.assertEqual(out["status"], "needs_external_result")
        self.assertEqual(out["reason_code"], "external_result_hash_mismatch")
        self.assertEqual(out["imported"], [])
        self.assertEqual(len(out["invalid"]), 2)
        self.assertFalse((self.prof / "论文分析/A/A.md").exists())
        self.assertFalse((self.prof / "论文分析/A/B.md").exists())
        self.assertFalse((self.prof / "论文分析/_index.json").exists())


if __name__ == "__main__":
    unittest.main()
