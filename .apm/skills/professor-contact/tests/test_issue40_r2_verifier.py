import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
MODULE_PATH = TESTS_DIR / "runtime/verify_issue40_r2.py"
spec = importlib.util.spec_from_file_location("issue40_r2_verifier", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Issue40R2VerifierTests(unittest.TestCase):
    def test_r2_thresholds_are_frozen_at_three_edges_and_depth_three(self):
        self.assertEqual(module.R2_MIN_EDGES, 3)
        self.assertEqual(module.R2_REQUIRED_DEPTH, 3)

    def test_r2_continuity_uses_clean_consumer_stage3_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            program = base / "program"
            consumer = base / "consumer"
            profile_root = base / "profile"
            professor = program / module.PROFESSOR_RELATIVE
            professor.mkdir(parents=True)
            (professor / module.INPUT_PACK).write_text("{}\n", encoding="utf-8")
            (profile_root / module.PROFILE_RELATIVE).parent.mkdir(parents=True)
            (profile_root / module.PROFILE_RELATIVE).write_text("# profile\n", encoding="utf-8")
            (program / module.verifier.MANIFEST_NAME).write_text(json.dumps({
                "profile_root": str(profile_root),
            }), encoding="utf-8")

            runner = consumer / module.INSTALLED_RUNNER_RELATIVE
            runner.parent.mkdir(parents=True)
            runner.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "assert sys.argv[1] == 'stage3-plan'\n"
                "assert '--professor-dir' in sys.argv\n"
                "assert '--profile' in sys.argv\n"
                "assert '--refresh-scope' in sys.argv\n"
                "assert sys.argv[sys.argv.index('--refresh-scope') + 1] == 'flagged'\n"
                "assert '--program-root' in sys.argv\n"
                "print(json.dumps({'status': 'ok', 'jobs': []}))\n",
                encoding="utf-8",
            )

            eval_response = base / "r2-response.json"
            adapter_output = base / "r2-adapter.json"
            eval_response.write_text("{}\n", encoding="utf-8")
            adapter_output.write_text("{}\n", encoding="utf-8")

            observed = {}

            def fake_graph(args):
                observed["min_edges"] = args.min_edges
                observed["required_depth"] = args.required_depth
                return {"status": "pass", "checks": [], "observed": {}}

            with mock.patch.object(module.verifier, "_checkpoint_runtime_graph", side_effect=fake_graph):
                payload = module.verify(
                    program_root=program,
                    consumer_root=consumer,
                    eval_response=eval_response,
                    adapter_output=adapter_output,
                )

            self.assertEqual(payload["status"], "pass", payload)
            self.assertEqual(observed, {"min_edges": 3, "required_depth": 3})
            names = {row["name"]: row["status"] for row in payload["checks"]}
            self.assertEqual(names["formal_root_l1_l2_l3"], "pass")
            self.assertEqual(names["canonical_stage2_input_exists"], "pass")
            self.assertEqual(names["stage3_plan_consumes_stage2_input"], "pass")


if __name__ == "__main__":
    unittest.main()
