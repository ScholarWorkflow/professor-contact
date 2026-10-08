import importlib.util
import json
import shlex
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
RECORDER_PATH = TESTS_DIR / "runtime" / "record_issue67_runtime_evidence.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


recorder = load_module("issue67_runtime_evidence_recorder_test", RECORDER_PATH)


class Issue67RuntimeEvidenceTests(unittest.TestCase):
    def _artifacts(self, root: Path, *, model="gpt-6-luna", reasoning="low"):
        request = root / "eval-request.json"
        response = root / "eval-response.json"
        output = root / "runtime-evidence.json"
        command = shlex.join([
            "--json", "--skip-git-repo-check",
            "--sandbox", "workspace-write", "--cd", str(root / "consumer"),
            "--model", model,
            "--config", 'features.multi_agent_v2.enabled=true',
            "--config", f'model_reasoning_effort="{reasoning}"',
            "--config", 'projects={' + json.dumps(str(root / "consumer"))
            + '={trust_level="trusted"}}',
            "--", "fixture prompt",
        ])
        request.write_text(json.dumps({"command": command, "timeout": 900}), encoding="utf-8")
        response.write_text(json.dumps({
            "version": "codex-cli 0.157.0",
            "passed": True,
            "output": {
                "backend": "app-server",
                "runtime_generation": 7,
                "exit_code": 0,
                "termination_reason": "completed",
                "thread_id": "thread-1",
                "app_server_events": [],
            },
        }), encoding="utf-8")
        return request, response, output

    def test_records_posted_invocation_and_actual_runtime_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "consumer").mkdir()
            request, response, output = self._artifacts(root)

            evidence = recorder.record(
                eval_request=request,
                eval_response=response,
                expected_model="gpt-6-luna",
                expected_reasoning="low",
                output=output,
            )

            self.assertEqual(evidence["status"], "ok")
            self.assertEqual(evidence["invocation"]["model"], "gpt-6-luna")
            self.assertEqual(evidence["invocation"]["reasoning"], "low")
            self.assertEqual(evidence["invocation"]["sandbox"], "workspace-write")
            self.assertEqual(evidence["invocation"]["session_mode"], "default_persistent")
            self.assertFalse(evidence["invocation"]["ephemeral"])
            self.assertTrue(evidence["invocation"]["multi_agent_v2_enabled"])
            self.assertEqual(evidence["runtime"], {
                "codex_version": "codex-cli 0.157.0",
                "backend": "app-server",
                "runtime_generation": 7,
            })
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), evidence)

    def test_rejects_request_model_different_from_gate2(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "consumer").mkdir()
            request, response, output = self._artifacts(root, model="gpt-5.6-luna")

            with self.assertRaisesRegex(recorder.EvidenceError, "does not match Gate-2 model"):
                recorder.record(
                    eval_request=request,
                    eval_response=response,
                    expected_model="gpt-6-luna",
                    expected_reasoning="low",
                    output=output,
                )
            self.assertFalse(output.exists())

    def test_rejects_missing_actual_runtime_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "consumer").mkdir()
            request, response, output = self._artifacts(root)
            data = json.loads(response.read_text(encoding="utf-8"))
            data["version"] = None
            response.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(recorder.EvidenceError, "no Codex version"):
                recorder.record(
                    eval_request=request,
                    eval_response=response,
                    expected_model="gpt-6-luna",
                    expected_reasoning="low",
                    output=output,
                )
            self.assertFalse(output.exists())

    def test_rejects_ephemeral_resume_and_missing_v2_before_recording(self):
        for mutation in ("ephemeral", "resume", "missing_v2"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                request, response, output = self._artifacts(root)
                data = json.loads(request.read_text(encoding="utf-8"))
                argv = shlex.split(data["command"])
                if mutation == "ephemeral":
                    argv.insert(1, "--ephemeral")
                elif mutation == "resume":
                    argv.insert(0, "resume")
                else:
                    index = argv.index('features.multi_agent_v2.enabled=true')
                    del argv[index - 1:index + 1]
                data["command"] = shlex.join(argv)
                request.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(recorder.EvidenceError):
                    recorder.record(eval_request=request, eval_response=response,
                                    expected_model="gpt-6-luna", expected_reasoning="low",
                                    output=output)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
