import contextlib
import importlib.util
import io
import json
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module(
    "issue67_runtime_config_builder",
    RUNTIME_DIR / "build_issue67_eval_request.py",
)
riso = load_module(
    "issue67_runtime_config_verifier",
    RUNTIME_DIR / "verify_issue67_riso.py",
)


class Issue67RuntimeConfigTests(unittest.TestCase):
    def test_builder_uses_recipe_supplied_model_and_reasoning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "consumer"
            root.mkdir()
            prompt = Path(temp) / "prompt.txt"
            prompt.write_text("run stage 4\n", encoding="utf-8")
            output = Path(temp) / "request.json"

            request = builder.build_request(
                consumer_root=root,
                prompt_file=prompt,
                output=output,
                model="gpt-6-luna",
                reasoning="low",
            )

            argv = shlex.split(request["command"])
            self.assertEqual(argv[argv.index("--model") + 1], "gpt-6-luna")
            configs = [argv[index + 1] for index, value in enumerate(argv)
                       if value == "--config"]
            self.assertIn('model_reasoning_effort="low"', configs)
            self.assertIn('features.multi_agent_v2.enabled=true', configs)
            self.assertIn('projects={' + json.dumps(str(root.resolve()))
                          + '={trust_level="trusted"}}', configs)
            self.assertNotIn("--ephemeral", argv)
            self.assertNotIn("resume", argv)
            self.assertNotIn("gpt-5.6-luna", request["command"])
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), request)

    def test_builder_does_not_own_a_project_wide_model_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "consumer"
            root.mkdir()
            prompt = Path(temp) / "prompt.txt"
            prompt.write_text("run stage 4\n", encoding="utf-8")
            output = Path(temp) / "request.json"

            request = builder.build_request(
                consumer_root=root,
                prompt_file=prompt,
                output=output,
                model="future-approved-model",
                reasoning="medium",
            )

            argv = shlex.split(request["command"])
            self.assertEqual(argv[argv.index("--model") + 1], "future-approved-model")
            self.assertIn('model_reasoning_effort="medium"', argv)

    def test_riso_wrapper_binds_recipe_config_before_base_verifier(self):
        old_model = riso.verifier.ISSUE67_REQUEST_MODEL
        old_reasoning = riso.verifier.ISSUE67_REQUEST_REASONING
        observed = {}

        def fake_main(argv):
            observed["argv"] = list(argv)
            observed["model"] = riso.verifier.ISSUE67_REQUEST_MODEL
            observed["reasoning"] = riso.verifier.ISSUE67_REQUEST_REASONING
            return 0

        try:
            with mock.patch.object(riso.verifier, "main", side_effect=fake_main):
                result = riso.main([
                    "stage4-professor-isolation",
                    "--expected-model", "gpt-6-luna",
                    "--expected-reasoning", "low",
                    "--program-root", "/tmp/program",
                ])
        finally:
            riso.verifier.ISSUE67_REQUEST_MODEL = old_model
            riso.verifier.ISSUE67_REQUEST_REASONING = old_reasoning

        self.assertEqual(result, 0)
        self.assertEqual(observed["model"], "gpt-6-luna")
        self.assertEqual(observed["reasoning"], "low")
        self.assertEqual(observed["argv"], [
            "stage4-professor-isolation", "--program-root", "/tmp/program",
        ])

    def test_riso_wrapper_rejects_other_checkpoints(self):
        with mock.patch.object(riso.verifier, "main") as base_main:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = riso.main([
                    "stage4-final",
                    "--expected-model", "gpt-6-luna",
                    "--expected-reasoning", "low",
                ])
        self.assertEqual(result, 1)
        base_main.assert_not_called()
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "invalid")
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")


if __name__ == "__main__":
    unittest.main()
