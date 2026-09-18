"""Issue #51 review follow-up: standalone Stage 2 runtime recipe contract.

The #52 review decoupled this PR from the unmerged #40/#45 runtime assets:
the runtime hard gate becomes one standalone Stage 2 direct-delegation case
(``root -> professor-contact-analyzer -> the analyzer's own child``) built
from producer-owned assets already on main (the #39 seed/prepare/request
helpers) plus this branch's fixed prompt and verifier.  These tests lock the
recipe pieces:

* the fixed first-hop prompt may carry a route token as case input, but that
  token is never runtime identity evidence or a PASS/FAIL assertion; the
  prompt must never hint the nested child, depth, or discovery surface;
* the reused #39 helpers accept an explicit ``--expected-fixture-revision``
  so the #51 recipe can pin ``88d2056…`` without touching the fixture repo;
* the #39 default pin stays exactly where #39 left it, so the old contract
  cannot drift.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"
PROMPT_PATH = RUNTIME_DIR / "prompts" / "issue51-r2.txt"
ISSUE39_FIXTURE_REVISION = "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972"
ISSUE51_FIXTURE_REVISION = "88d2056f35a6f7e114b6070adbbeeeb355fd4b7f"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed_helper = _load("seed_issue39_zotero", RUNTIME_DIR / "seed_issue39_zotero.py")
prepare_helper = _load(
    "prepare_issue39_stage2_fixture",
    RUNTIME_DIR / "prepare_issue39_stage2_fixture.py")
request_helper = _load(
    "build_issue39_eval_request",
    RUNTIME_DIR / "build_issue39_eval_request.py")


class FakeMcpTransport:
    """Minimal Streamable-HTTP MCP server returning scripted item keys."""

    def __init__(self, item_keys):
        self.item_keys = list(item_keys)
        self.created = 0

    def __call__(self, url, payload_bytes, headers):
        payload = json.loads(payload_bytes)
        if payload.get("method") == "initialize":
            return 200, {"mcp-session-id": "sess-pc51"}, json.dumps({
                "jsonrpc": "2.0", "id": payload["id"],
                "result": {"protocolVersion": "2025-06-18",
                           "serverInfo": {"name": "zotero-mcp", "version": "1"}}})
        if payload.get("method") == "notifications/initialized":
            return 202, {}, ""
        key = self.item_keys[self.created]
        self.created += 1
        return 200, {}, json.dumps({
            "jsonrpc": "2.0", "id": payload["id"],
            "result": {"content": [{"type": "text",
                                    "text": json.dumps({"itemKey": key})}]}})


def evidence(revision=ISSUE51_FIXTURE_REVISION,
             run_id="zotero-20260918T000000Z-00051"):
    return {
        "fixture_kind": "zotero",
        "fixture_repo_sha": revision,
        "fixture_repo_dirty": "no",
        "fixture_run_id": run_id,
        "manual_patch": "no",
    }


def items_config(revision=ISSUE51_FIXTURE_REVISION):
    return {
        "schema_version": 1,
        "fixture_repository": "skills-test-fixtures",
        "fixture_revision": revision,
        "fixture_run_id": "run-issue51-standalone",
        "item_keys": ["ZK51AAAA", "ZK51BBBB"],
        "ready_item_keys": ["ZK51AAAA"],
        "fill_target_item_key": "ZK51BBBB",
        "fill_target_pdf_status": "pending",
    }


class Issue51FixedPromptTests(unittest.TestCase):
    def test_prompt_carries_fixed_stage2_business_input(self):
        text = PROMPT_PATH.read_text(encoding="utf-8")
        self.assertTrue(text.strip())
        self.assertIn("`folder_path: ${PROGRAM_ROOT}`", text)
        self.assertIn("`paper_analysis: all`", text)
        self.assertIn("只负责一次 Stage 2 入口", text)
        self.assertIn("不得自己执行 Stage 2", text)
        self.assertIn("不要进入 Stage 3", text)

    def test_prompt_defers_the_delegation_mechanism_to_production_source(self):
        """Issue #51 §F: a stronger prompt must never stand in for the product
        fix, so the prompt states the entry only and names production
        instructions as the single source of how delegation is discovered."""
        text = PROMPT_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "内部如何发现并调用 native delegation capability，必须完全来自安装后的",
            text)

    def test_prompt_does_not_hint_children_depth_or_discovery(self):
        text = PROMPT_PATH.read_text(encoding="utf-8")
        for child in ("paper-analysis", "professor-collector",
                      "professor-contact-style-validator",
                      "professor-contact-email-validator"):
            self.assertNotIn(child, text)
        for literal in ("Code Mode", "ALL_TOOLS", "tool catalog",
                        "discovery surface", "spawn_agent", "agent_type",
                        "agent_role", "max_depth", "nested", "嵌套", "深度",
                        "两层", "profile_path", "递归", "self-delegation",
                        "自身机器名", "同一委派链"):
            self.assertNotIn(literal, text)


class SeedExpectedRevisionTests(unittest.TestCase):
    def test_default_pin_stays_on_issue39_revision(self):
        self.assertEqual(seed_helper.FIXTURE_REVISION, ISSUE39_FIXTURE_REVISION)
        self.assertEqual(
            seed_helper._parser().get_default("expected_fixture_revision"),
            ISSUE39_FIXTURE_REVISION)

    def test_default_rejects_issue51_revision(self):
        with self.assertRaises(seed_helper.SeedError):
            seed_helper.validate_fixture_evidence(evidence())

    def test_explicit_revision_accepts_issue51_evidence(self):
        validated = seed_helper.validate_fixture_evidence(
            evidence(), expected_revision=ISSUE51_FIXTURE_REVISION)
        self.assertEqual(validated["revision"], ISSUE51_FIXTURE_REVISION)

    def test_explicit_revision_seeds_and_records_issue51_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence_path = Path(directory) / "fixture-evidence.json"
            evidence_path.write_text(
                json.dumps(evidence()), encoding="utf-8")
            output = Path(directory) / "zotero-items.json"
            status = seed_helper.seed_zotero_items(
                zotero_mcp_url="http://127.0.0.1:24122/mcp",
                fixture_evidence=evidence_path,
                output=output,
                expected_revision=ISSUE51_FIXTURE_REVISION,
                http_post=FakeMcpTransport(["ZK51AAAA", "ZK51BBBB"]))
            self.assertEqual(status["status"], "ok")
            config = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(config["fixture_revision"],
                             ISSUE51_FIXTURE_REVISION)

    def test_malformed_expected_revision_fails_closed(self):
        for bad in ("main", "88d2056", ISSUE51_FIXTURE_REVISION.upper(), ""):
            with self.assertRaises(seed_helper.SeedError):
                seed_helper.validate_fixture_evidence(
                    evidence(revision=bad), expected_revision=bad)

    def test_cli_parses_expected_revision_flag(self):
        args = seed_helper._parser().parse_args([
            "--zotero-mcp-url", "http://127.0.0.1:24122/mcp",
            "--fixture-evidence", "evidence.json",
            "--output", "items.json",
            "--expected-fixture-revision", ISSUE51_FIXTURE_REVISION,
        ])
        self.assertEqual(args.expected_fixture_revision, ISSUE51_FIXTURE_REVISION)


class PrepareExpectedRevisionTests(unittest.TestCase):
    def test_default_pin_stays_on_issue39_revision(self):
        self.assertEqual(prepare_helper.FIXTURE_REVISION, ISSUE39_FIXTURE_REVISION)
        self.assertEqual(
            prepare_helper._parser().get_default("expected_fixture_revision"),
            ISSUE39_FIXTURE_REVISION)

    def test_default_rejects_issue51_revision(self):
        with self.assertRaises(prepare_helper.SetupError):
            prepare_helper.validate_items_config(items_config())

    def test_explicit_revision_accepts_and_normalizes(self):
        validated = prepare_helper.validate_items_config(
            items_config(), expected_revision=ISSUE51_FIXTURE_REVISION)
        self.assertEqual(validated["fixture_revision"], ISSUE51_FIXTURE_REVISION)

    def test_explicit_revision_still_rejects_foreign_revision(self):
        with self.assertRaises(prepare_helper.SetupError):
            prepare_helper.validate_items_config(
                items_config(revision=ISSUE39_FIXTURE_REVISION),
                expected_revision=ISSUE51_FIXTURE_REVISION)

    def test_malformed_expected_revision_fails_closed(self):
        for bad in ("main", "88d2056", ISSUE51_FIXTURE_REVISION.upper(), ""):
            with self.assertRaises(prepare_helper.SetupError):
                prepare_helper.validate_items_config(
                    items_config(revision=bad), expected_revision=bad)

    def test_cli_parses_expected_revision_flag(self):
        args = prepare_helper._parser().parse_args([
            "--program-root", "program",
            "--professor-contact-skill-dir", "skill",
            "--zotero-items-config", "items.json",
            "--zotero-http-url", "http://127.0.0.1:24121",
            "--zotero-mcp-url", "http://127.0.0.1:24122/mcp",
            "--output", "manifest.json",
            "--expected-fixture-revision", ISSUE51_FIXTURE_REVISION,
        ])
        self.assertEqual(args.expected_fixture_revision, ISSUE51_FIXTURE_REVISION)


class Issue51EvalRequestTests(unittest.TestCase):
    def test_request_builder_accepts_issue51_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            request = request_helper.build_request(
                consumer_root=Path(directory),
                prompt_file=PROMPT_PATH,
                output=Path(directory) / "request.json",
                zotero_http_url="http://127.0.0.1:24121",
                zotero_mcp_url="http://127.0.0.1:24122/mcp")
        self.assertIn("--sandbox workspace-write", request["command"])
        self.assertIn("`paper_analysis: all`", request["command"])
        self.assertIn("`folder_path: ${PROGRAM_ROOT}`", request["command"])


if __name__ == "__main__":
    unittest.main()
