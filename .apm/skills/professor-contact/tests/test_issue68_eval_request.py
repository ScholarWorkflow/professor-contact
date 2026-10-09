import hashlib
import importlib.util
import json
import shlex
import socket
import tempfile
import tomllib
import unittest
import urllib.request
import uuid
from contextlib import ExitStack
from pathlib import Path
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = TESTS_DIR.parents[3]
MODULE_PATH = TESTS_DIR / "runtime" / "build_issue68_eval_request.py"
spec = importlib.util.spec_from_file_location("issue68_eval_request", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PROGRAM_TOKEN = "<PC68_PROGRAM>"
NETWORK_ENTRY_POINTS = (
    "socket.socket.connect",
    "socket.socket.connect_ex",
    "socket.create_connection",
    "urllib.request.urlopen",
)


class Issue68EvalRequestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.temp_root = Path(self.temporary.name)
        self.consumer_root = self.temp_root / "consumer project with spaces"
        self.consumer_root.mkdir()
        self.program_root = self.consumer_root / "applicant program with spaces"
        self.program_root.mkdir()
        self.outside_program = self.temp_root / "program outside consumer"
        self.outside_program.mkdir()
        self.targets = {
            "template_copy": self.temp_root / "frozen template.txt",
            "rendered_prompt": self.temp_root / "rendered prompt.txt",
            "hash_file": self.temp_root / "prompt hashes.txt",
            "output": self.temp_root / "eval request.json",
        }

    def build(self, **overrides):
        arguments = {
            "consumer_root": self.consumer_root,
            "program_root": self.program_root,
            **self.targets,
        }
        arguments.update(overrides)
        return module.build_request(**arguments)

    def assert_rejected_without_network(self, **overrides):
        with ExitStack() as stack:
            network_mocks = [stack.enter_context(mock.patch(target))
                             for target in NETWORK_ENTRY_POINTS]
            with self.assertRaises(module.RequestBuildError):
                self.build(**overrides)
            for network_mock in network_mocks:
                network_mock.assert_not_called()

    def test_builds_space_bearing_prompt_and_exact_minimal_request(self):
        result = self.build()
        request = result["request"]
        template = Path(module.DEFAULT_PROMPT_TEMPLATE).read_text(encoding="utf-8")
        self.assertEqual(template.count(PROGRAM_TOKEN), 1)
        rendered = template.replace(PROGRAM_TOKEN, str(self.program_root.resolve()))

        argv = shlex.split(request["command"])
        expected_prefix = [
            "--json", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "workspace-write", "--cd", str(self.consumer_root.resolve()),
        ]
        self.assertEqual(argv[:len(expected_prefix)], expected_prefix)
        config_index = len(expected_prefix)
        self.assertEqual(argv[config_index], "--config")
        self.assertEqual(argv[config_index + 2], "--")
        self.assertEqual(argv[config_index + 3:], [rendered])
        config_assignments = [
            argv[index + 1]
            for index, value in enumerate(argv[:-1])
            if value == "--config"
        ]
        self.assertEqual(len(config_assignments), 1)
        self.assertEqual(
            tomllib.loads(config_assignments[0]),
            {"projects": {
                str(self.consumer_root.resolve()): {"trust_level": "trusted"},
            }},
        )
        self.assertNotIn("--model", argv)
        self.assertNotIn("--reasoning", argv)
        self.assertNotIn("model_reasoning_effort", config_assignments[0])
        self.assertEqual(request["timeout"], 900)
        self.assertEqual(request["timeout"], module.TIMEOUT)
        self.assertIn(str(self.program_root.resolve()), argv[-1])
        self.assertEqual(json.loads(self.targets["output"].read_text(encoding="utf-8")), request)

    def test_persists_template_prompt_hashes_and_request_outside_repository(self):
        result = self.build()
        request = result["request"]
        template_path = Path(module.DEFAULT_PROMPT_TEMPLATE)
        template_bytes = template_path.read_bytes()
        rendered_bytes = self.targets["rendered_prompt"].read_bytes()
        expected_rendered = template_bytes.replace(
            PROGRAM_TOKEN.encode("utf-8"), str(self.program_root.resolve()).encode("utf-8"))
        template_sha256 = hashlib.sha256(template_bytes).hexdigest()
        rendered_sha256 = hashlib.sha256(expected_rendered).hexdigest()

        self.assertEqual(module.PROMPT_TEMPLATE_SHA256, template_sha256)
        self.assertEqual(result["template_sha256"], template_sha256)
        self.assertEqual(result["rendered_sha256"], rendered_sha256)
        self.assertEqual(self.targets["template_copy"].read_bytes(), template_bytes)
        self.assertEqual(rendered_bytes, expected_rendered)
        hash_text = self.targets["hash_file"].read_text(encoding="utf-8")
        self.assertIn(template_sha256, hash_text)
        self.assertIn(rendered_sha256, hash_text)
        self.assertEqual(json.loads(self.targets["output"].read_text(encoding="utf-8")), request)
        self.assertEqual(result["outputs"], {
            "template": str(self.targets["template_copy"].resolve()),
            "prompt": str(self.targets["rendered_prompt"].resolve()),
            "hashes": str(self.targets["hash_file"].resolve()),
            "request": str(self.targets["output"].resolve()),
        })

        for path in (*self.targets.values(),):
            self.assertTrue(path.is_file(), path)
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    path.resolve().relative_to(REPOSITORY_ROOT.resolve())

    def test_rejects_a_template_whose_frozen_digest_changed_without_network(self):
        source = Path(module.DEFAULT_PROMPT_TEMPLATE).read_text(encoding="utf-8")
        tampered = self.temp_root / "tampered prompt template.txt"
        tampered.write_text(source + "\nModified for this test.\n", encoding="utf-8")
        self.assert_rejected_without_network(prompt_template=tampered)
        for path in self.targets.values():
            self.assertFalse(path.exists(), path)

    def test_rejects_missing_or_duplicate_program_token(self):
        source = Path(module.DEFAULT_PROMPT_TEMPLATE).read_text(encoding="utf-8")
        malformed_templates = {
            "missing": source.replace(PROGRAM_TOKEN, "", 1),
            "duplicate": source.replace(PROGRAM_TOKEN, PROGRAM_TOKEN + "\n" + PROGRAM_TOKEN, 1),
        }
        for label, contents in malformed_templates.items():
            with self.subTest(token_count=label):
                path = self.temp_root / f"{label} token template.txt"
                path.write_text(contents, encoding="utf-8")
                digest = hashlib.sha256(contents.encode("utf-8")).hexdigest()
                with mock.patch.object(module, "PROMPT_TEMPLATE_SHA256", digest):
                    self.assert_rejected_without_network(prompt_template=path)
                for output_path in self.targets.values():
                    self.assertFalse(output_path.exists(), output_path)

    def test_rejects_program_directory_outside_consumer_without_network(self):
        self.assert_rejected_without_network(program_root=self.outside_program)
        for path in self.targets.values():
            self.assertFalse(path.exists(), path)

    def test_rejects_every_generated_file_path_inside_repository_without_network(self):
        for artifact_name in self.targets:
            with self.subTest(artifact=artifact_name):
                forbidden_path = REPOSITORY_ROOT / (
                    f".issue68-forbidden-{artifact_name}-{uuid.uuid4().hex}.tmp")
                self.assertFalse(forbidden_path.exists())
                try:
                    self.assert_rejected_without_network(**{artifact_name: forbidden_path})
                    self.assertFalse(forbidden_path.exists())
                    for other_path in self.targets.values():
                        if other_path != forbidden_path:
                            self.assertFalse(other_path.exists(), other_path)
                finally:
                    forbidden_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
