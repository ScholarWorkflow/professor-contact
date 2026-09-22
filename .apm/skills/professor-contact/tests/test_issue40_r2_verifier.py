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

    def _continuity_fixture(self, base: Path) -> dict[str, Path]:
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
            "print(json.dumps({'status': 'ok', 'jobs': []}))\n",
            encoding="utf-8",
        )
        return {
            "program": program,
            "consumer": consumer,
            "eval_response": base / "r2-response.json",
            "adapter_output": base / "r2-adapter.json",
            "identity_adapter_output": base / "r2-identity-adapter.json",
        }

    def test_named_identity_contradiction_is_diagnostics_only_and_never_gates(self):
        """The identity-diagnostics behavior introduced at fixtures@9 and preserved by the current @13 contract fail-closes on the observed
        R2 contradiction (persisted role 'default' vs developer definition
        'paper-analysis').  That surface must be recorded verbatim without
        downgrading the formal delegation verdict or triggering a retry."""
        with tempfile.TemporaryDirectory() as directory:
            paths = self._continuity_fixture(Path(directory))
            paths["eval_response"].write_text("{}\n", encoding="utf-8")
            paths["adapter_output"].write_text("{}\n", encoding="utf-8")
            paths["identity_adapter_output"].write_text(json.dumps({
                "fixture_status": "INVALID_EVIDENCE",
                "problems": [
                    "contradictory identity evidence for child thread "
                    "01a0b55f-6083-7923-a9ce-efdc1df5596d: persisted role "
                    "confirms 'default' but child developer evidence matches "
                    "'paper-analysis'",
                ],
            }), encoding="utf-8")

            with mock.patch.object(
                module.verifier, "_checkpoint_runtime_graph",
                return_value={"status": "pass", "checks": [], "observed": {}},
            ):
                payload = module.verify(
                    program_root=paths["program"],
                    consumer_root=paths["consumer"],
                    eval_response=paths["eval_response"],
                    adapter_output=paths["adapter_output"],
                    identity_adapter_output=paths["identity_adapter_output"],
                )

            self.assertEqual(payload["status"], "pass", payload)
            diagnostics = payload["observed"]["identity_diagnostics"]
            self.assertFalse(diagnostics["gating"])
            self.assertEqual(diagnostics["fixture_status"], "INVALID_EVIDENCE")
            self.assertIn("paper-analysis", diagnostics["problems"][0])

    def test_identity_diagnostics_cannot_rescue_a_failed_formal_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self._continuity_fixture(Path(directory))
            paths["eval_response"].write_text("{}\n", encoding="utf-8")
            paths["adapter_output"].write_text("{}\n", encoding="utf-8")
            paths["identity_adapter_output"].write_text(json.dumps({
                "fixture_status": "FIXTURE_READY",
                "problems": [],
            }), encoding="utf-8")

            with mock.patch.object(
                module.verifier, "_checkpoint_runtime_graph",
                return_value={"status": "fail", "checks": [], "observed": {}},
            ):
                payload = module.verify(
                    program_root=paths["program"],
                    consumer_root=paths["consumer"],
                    eval_response=paths["eval_response"],
                    adapter_output=paths["adapter_output"],
                    identity_adapter_output=paths["identity_adapter_output"],
                )

            self.assertEqual(payload["status"], "fail", payload)
            self.assertEqual(
                payload["observed"]["identity_diagnostics"]["fixture_status"],
                "FIXTURE_READY",
            )

    def test_identity_surface_defaults_to_absent_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self._continuity_fixture(Path(directory))
            paths["eval_response"].write_text("{}\n", encoding="utf-8")
            paths["adapter_output"].write_text("{}\n", encoding="utf-8")

            with mock.patch.object(
                module.verifier, "_checkpoint_runtime_graph",
                return_value={"status": "pass", "checks": [], "observed": {}},
            ):
                payload = module.verify(
                    program_root=paths["program"],
                    consumer_root=paths["consumer"],
                    eval_response=paths["eval_response"],
                    adapter_output=paths["adapter_output"],
                )

            self.assertNotIn("identity_diagnostics", payload["observed"])


if __name__ == "__main__":
    unittest.main()
