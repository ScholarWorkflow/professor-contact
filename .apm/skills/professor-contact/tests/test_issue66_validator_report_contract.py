"""Installed style-validator completion-report contract for issue #66."""

import json
import os
import re
import tomllib
import unittest
from pathlib import Path


AGENT_PATH_ENV = "PROFESSOR_CONTACT_VALIDATOR_AGENT"
DEFAULT_AGENT_PATH = (
    Path(__file__).resolve().parents[4]
    / ".apm"
    / "agents"
    / "professor-contact-style-validator.agent.md"
)
FORBIDDEN_COMPLETION_KEYS = {"files", "verdict", "issues", "notes", "blocking", "minor"}


def read_agent_path():
    configured_path = os.environ.get(AGENT_PATH_ENV)
    return Path(configured_path).expanduser() if configured_path else DEFAULT_AGENT_PATH


def read_agent_instructions(agent_path):
    if agent_path.suffix.lower() == ".toml":
        with agent_path.open("rb") as handle:
            installed_agent = tomllib.load(handle)
        instructions = installed_agent.get("developer_instructions")
        if not isinstance(instructions, str):
            raise AssertionError(
                f"installed agent has no developer_instructions: {agent_path}"
            )
        return instructions
    return agent_path.read_text(encoding="utf-8")


def json_examples(agent_text):
    return [
        json.loads(match.group(1))
        for match in re.finditer(r"```json\s*(.*?)\s*```", agent_text, re.DOTALL | re.IGNORECASE)
    ]


class Issue66ValidatorReportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent_path = read_agent_path()
        if not cls.agent_path.is_file():
            raise AssertionError(
                f"style-validator instructions not found: {cls.agent_path}; "
                f"set {AGENT_PATH_ENV} to the installed agent file"
            )
        cls.agent_text = read_agent_instructions(cls.agent_path)
        cls.examples = json_examples(cls.agent_text)

    def test_output_file_completion_reports_have_exact_fields_and_no_validation_body(self):
        reports = [
            example for example in self.examples
            if isinstance(example, dict) and "write_status" in example
        ]
        self.assertEqual(len(reports), 2, reports)
        by_status = {report.get("write_status"): report for report in reports}
        self.assertEqual(set(by_status), {"written", "failed"})

        success = by_status["written"]
        self.assertEqual(
            set(success), {"result", "write_status", "output_files"}, success,
        )
        self.assertEqual(success["result"], "ok")
        self.assertIsInstance(success["output_files"], list)
        self.assertTrue(success["output_files"])
        self.assertTrue(all(
            isinstance(path, str) and path for path in success["output_files"]
        ))

        failure = by_status["failed"]
        self.assertEqual(
            set(failure), {"result", "write_status", "output_files", "reason_code"},
            failure,
        )
        self.assertEqual(failure["result"], "error")
        self.assertIsInstance(failure["output_files"], list)
        self.assertTrue(failure["output_files"])
        self.assertTrue(all(
            isinstance(path, str) and path for path in failure["output_files"]
        ))
        self.assertIsInstance(failure["reason_code"], str)

        for report in reports:
            self.assertFalse(
                FORBIDDEN_COMPLETION_KEYS.intersection(report), report,
            )

    def test_missing_writer_reason_code_defaults_to_validation_write_failed(self):
        self.assertTrue(
            "validation_write_failed" in self.agent_text,
            f"{self.agent_path} does not define the fallback reason code",
        )
        self.assertTrue(
            re.search(
                r"(?:没有|无|缺少|未提供|未返回).{0,40}(?:原因码|reason_code)"
                r".{0,80}validation_write_failed",
                self.agent_text,
                re.DOTALL,
            ),
            f"{self.agent_path} does not tie the fallback code to a missing writer reason code",
        )

    def test_calls_without_output_file_keep_the_full_read_only_return_contract(self):
        self.assertIn("未传时保持既有只读行为与原返回方式不变", self.agent_text)
        legacy = [
            example for example in self.examples
            if isinstance(example, dict)
            and set(example) == {"result", "files", "notes"}
        ]
        self.assertEqual(len(legacy), 1, legacy)
        returned = legacy[0]
        self.assertEqual(returned["result"], "ok")
        self.assertIsInstance(returned["files"], list)
        self.assertEqual(len(returned["files"]), 1)

        file_result = returned["files"][0]
        self.assertEqual(
            set(file_result),
            {"file", "artifact", "verdict", "blocking", "minor", "issues"},
        )
        self.assertEqual(
            set(file_result["issues"][0]),
            {"rule", "severity", "location", "quote", "suggestion"},
        )


if __name__ == "__main__":
    unittest.main()
