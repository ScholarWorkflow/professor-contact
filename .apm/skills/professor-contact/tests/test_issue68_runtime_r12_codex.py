"""Gate-2 r12 codex-only entrypoint regressions.

Per the authoritative record `issue-68-gate2-r12-2026-10-04` (2026-10-04
scope adjustment), the current formal `PC68-R1` keeps only the Codex host:
no multi-host execution, no combined verdict, and the generic runner
commands are no longer execution instructions. Synthetic evidence here
characterizes the entrypoint wiring; it is not host acceptance PASS.
"""
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

FIXTURE_SHA = "cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04"
CONTRACT_REVISION = "issue-68-runtime-evidence-r12-2026-10-04"
ENTRY_NAME = "run_issue68_stage5_routing_r12_codex.py"
GENERIC_RUNNER_NAME = "run_issue68_stage5_routing_r12.py"


def load(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, RUNTIME / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestIssue68RuntimeR12CodexEntrypoint(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        owners = [{"professor": name, "professor_dir": str(self.root / name),
                   "email_pack": str(self.root / name / "邮件输入.json"), "email_ids": ["X"],
                   "expected_result": {"status": "needs_refresh", "reason_code": "verify_missing"}}
                  for name in ("A", "B")]
        self.manifest = {"owners": owners, "program_root": str(self.root),
                         "invalid_pack": str(self.root / "C" / "邮件输入.json"),
                         "expected_choices": [{"email_id": "X", "professor_dir": owner["professor_dir"],
                                               "sentinel": owner["professor"]} for owner in owners],
                         "expected_scope": {owner["professor_dir"]: ["X"] for owner in owners}}

    def rebind_base_runner(self):
        """Hand out the base runner module with the pinned bindings restorable."""
        import run_issue68_stage5_routing as base
        names = ("FIXTURE_SHA", "run", "build_request", "verify_codex", "verify_opencode",
                 "prepare", "clean_revision", "codex_host", "opencode_host", "combine")
        originals = {name: getattr(base, name) for name in names}
        self.addCleanup(lambda: [setattr(base, name, originals[name]) for name in names])
        return base

    # -- synthetic Codex evidence, same shape as test_issue68_runtime_r12 ----

    def payload(self, owner):
        return json.dumps({"email_pack": owner["email_pack"], "choices": self.manifest["expected_choices"],
                           "choices_scope": self.manifest["expected_scope"]})

    def root_rows(self):
        return [dict(owner["expected_result"], professor_dir=owner["professor_dir"])
                for owner in self.manifest["owners"]]

    def root_result(self):
        return json.dumps(self.root_rows())

    def discovery(self):
        return json.dumps({"status": "ok", "inputs": [
            *[{"email_pack": owner["email_pack"], "status": "ok"} for owner in self.manifest["owners"]],
            {"email_pack": self.manifest["invalid_pack"], "status": "error"}]})

    def command(self, action):
        return shlex.join(["python3", "/installed/contact_state.py", action,
                           "--program-root", str(self.root)])

    def codex_evidence(self):
        relations = []

        def event(events, seq, method, thread, item):
            events.append({"runtime_seq": seq, "runtime_generation": "g", "direction": "notification",
                           "message": {"method": method, "params": {"threadId": thread, "item": item}}})

        events = []
        event(events, 1, "item/started", "root", {"type": "commandExecution", "id": "discovery"})
        event(events, 2, "item/completed", "root", {"type": "commandExecution", "id": "discovery",
              "command": self.command("stage5-list-inputs"), "aggregatedOutput": self.discovery()})
        for index, owner in enumerate(self.manifest["owners"]):
            child, seq = f"child-{index}", 3 + index * 3
            relations.append({"tool": "spawnAgent", "sender_thread_id": "root", "receiver_thread_ids": [child]})
            event(events, seq, "rawResponseItem/completed", child, {"type": "message", "role": "user",
                  "content": [{"type": "input_text", "text": self.payload(owner)}]})
            event(events, seq + 1, "item/completed", "root", {"type": "collabAgentToolCall", "tool": "wait",
                  "status": "completed", "senderThreadId": "root", "receiverThreadIds": [child],
                  "agentsStates": {child: {"status": "completed", "message": json.dumps(
                      dict(owner["expected_result"], professor_dir=owner["professor_dir"]))}}})
        event(events, 9, "rawResponseItem/completed", "root", {"type": "message", "role": "assistant",
              "content": [{"type": "output_text", "text": self.root_result()}]})
        response = {"output": {"thread_id": "root", "runtime_generation": "g",
                               "termination_reason": "completed", "app_server_events": events,
                               "root_thread_read": {"thread_id": "root", "runtime_generation": "g",
                   "request": {"method": "thread/read", "params": {"threadId": "root", "includeTurns": True}},
                   "error": None, "result": {"thread": {"id": "root", "turns": [{"items": [
                       {"type": "agentMessage", "id": "final", "text": self.root_result(),
                        "phase": "final_answer"}]}]}}}}}
        adapter = {"fixture_status": "HARNESS_DISPATCH_UNCONFIRMED",
                   "dispatch": {"thread_relations": relations, "agent_identity": {}}}
        return response, adapter

    # -- entrypoint bootstrap bindings --------------------------------------

    def test_entry_contract_binds_the_unique_codex_only_runner(self):
        entry = load(ENTRY_NAME[:-3])
        contract = entry.load_contract()
        self.assertEqual(contract["revision"], CONTRACT_REVISION)
        self.assertEqual(contract["fixture_sha"], FIXTURE_SHA)
        self.assertEqual(contract["runner"],
                         ".apm/skills/professor-contact/tests/runtime/" + ENTRY_NAME)
        self.assertEqual(contract["manual_patch"], "no")
        self.assertTrue(entry.check_entry_uniqueness(str(entry.HERE / ENTRY_NAME)))
        with self.assertRaises(ValueError):
            entry.check_entry_uniqueness(str(entry.HERE / GENERIC_RUNNER_NAME))

    def test_pin_rebinds_base_pipeline_to_r12_assets_only(self):
        base = self.rebind_base_runner()
        import build_issue68_codex_request_r12
        import verify_issue68_stage5_routing_r12
        import run_issue68_stage5_routing_r12 as bridge
        entry = load(ENTRY_NAME[:-3])
        entry.pin()
        self.assertEqual(base.FIXTURE_SHA, FIXTURE_SHA)
        self.assertIs(base.run, bridge.run)
        self.assertIs(base.build_request, build_issue68_codex_request_r12.build_request)
        self.assertIs(base.verify_codex, verify_issue68_stage5_routing_r12.verify_codex)
        request = base.build_request(self.root, "固定业务输入")
        tokens = shlex.split(request["command"])
        self.assertIn("gpt-6-luna", tokens)
        self.assertIn('model_reasoning_effort="low"', tokens)

    # -- formal codex-only execution flow -----------------------------------

    def main_entry(self):
        entry = load(ENTRY_NAME[:-3])
        self.rebind_base_runner()
        real_argv = sys.argv
        sys.argv = [str(entry.HERE / ENTRY_NAME)]
        self.addCleanup(setattr, sys, "argv", real_argv)
        return entry

    def run_codex_only(self, output, fixture_sha=FIXTURE_SHA):
        """Drive entry.main() with only subprocess/network/git edges faked.

        Everything between them stays real: install_host archive wiring,
        codex_host request build + evidence parsing dispatch, the r12 final
        source verifier, config snapshots, provenance and verdict writes.
        """
        entry = self.main_entry()
        import run_issue68_stage5_routing as base
        import run_issue68_stage5_routing_r12 as bridge
        producer_root = self.root / "producer"
        producer_root.mkdir()
        fixture_root = self.root / "fixture"
        fixture_root.mkdir()
        eval_root = self.root / "eval"
        eval_root.mkdir()
        response, adapter = self.codex_evidence()
        subprocess_invocations, revisions, urls = [], [], []

        def fake_original_run(argv, cwd, prefix, *, env=None, timeout=180):
            command = [str(part) for part in argv]
            subprocess_invocations.append(command)
            prefix = Path(prefix)
            prefix.with_suffix(".stdout.txt").write_text("", encoding="utf-8")
            prefix.with_suffix(".stderr.txt").write_text("", encoding="utf-8")
            prefix.with_suffix(".exit-code.txt").write_text("0\n", encoding="utf-8")
            if command[0] == "apm":
                consumer = Path(cwd)
                (consumer / "apm.lock.yaml").write_text("lock: synthetic\n", encoding="utf-8")
                config = consumer / ".codex" / "config.toml"
                config.parent.mkdir(parents=True, exist_ok=True)
                config.write_text('model = "gpt-6-luna"\n', encoding="utf-8")
                script = consumer / ".codex" / "skills" / "professor-contact" / "scripts" / "contact_state.py"
                script.parent.mkdir(parents=True, exist_ok=True)
                script.write_text("# installed producer script\n", encoding="utf-8")
                return 0
            if any(Path(part).name == "parse_codex_eval_evidence_with_root_history.py"
                   for part in command):
                target = Path(command[command.index("--output") + 1])
                target.write_text(json.dumps(adapter), encoding="utf-8")
                return 0
            raise AssertionError("unexpected subprocess: " + repr(command))

        def fake_clean_revision(root_path, expected):
            revisions.append((str(Path(root_path)), expected))
            return {"sha": expected, "dirty": "no"}

        def fake_prepare(program_root, installed_script, output_dir):
            directory = Path(output_dir)
            (directory / "root-prompt.txt").write_text("根提示词\n", encoding="utf-8")
            for name in ("fixture-manifest.json", "canonical-choices.json", "expected-scope.json"):
                (directory / name).write_text("{}", encoding="utf-8")
            return self.manifest

        class FakeHTTPResponse:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return self.body

        def fake_urlopen(request, timeout=None):
            urls.append(request.full_url)
            return FakeHTTPResponse(json.dumps(response).encode())

        def forbidden(*args, **kwargs):
            raise AssertionError("codex-only entry must not touch the OpenCode path or combine")

        old_check_output = subprocess.check_output
        old_urlopen = urllib.request.urlopen

        def fake_check_output(argv, **kwargs):
            if argv[0] == "direnv":
                return "8765\n"
            raise AssertionError("unexpected check_output: " + repr(argv))

        bridge._ORIGINAL_RUN = fake_original_run
        self.addCleanup(setattr, bridge, "_ORIGINAL_RUN", getattr(bridge, "_ORIGINAL_RUN"))
        base.prepare = fake_prepare
        base.clean_revision = fake_clean_revision
        base.opencode_host = forbidden
        base.combine = forbidden
        subprocess.check_output = fake_check_output
        urllib.request.urlopen = fake_urlopen
        self.addCleanup(setattr, subprocess, "check_output", old_check_output)
        self.addCleanup(setattr, urllib.request, "urlopen", old_urlopen)
        rc = entry.main([
            "--producer-root", str(producer_root),
            "--producer-sha", "826dfa1d1757ad1dae26c1d1152c167758250c5c",
            "--fixture-root", str(fixture_root),
            "--fixture-sha", fixture_sha,
            "--eval-direnv-root", str(eval_root),
            "--output-dir", str(output)])
        return {"rc": rc, "entry": entry, "producer_root": producer_root,
                "fixture_root": fixture_root, "fixture_sha": fixture_sha,
                "invocations": subprocess_invocations, "revisions": revisions, "urls": urls}

    def test_entry_runs_codex_once_passes_verdict_through_and_archives_contract_evidence(self):
        output = self.root / "run-output"
        outcome = self.run_codex_only(output)
        self.assertEqual(outcome["rc"], 0, output)
        final = json.loads((output / "final-verdict.json").read_text(encoding="utf-8"))
        codex = json.loads((output / "codex-verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(final, codex)
        self.assertEqual(final["verdict"], "PASS")
        self.assertNotIn("hosts", final)
        # No OpenCode execution path and no multi-host combination.
        self.assertFalse((output / "opencode").exists())
        self.assertFalse((output / "opencode-verdict.json").exists())
        self.assertEqual(len(outcome["urls"]), 1)
        # Contract-frozen archive manifest, aligned with the r12 contract.
        archived = ("provenance.json", "final-verdict.json", "codex-verdict.json",
                    "codex/install.json", "codex/install.exit-code.txt", "codex/apm.lock.yaml",
                    "codex/installed-entrypoint.json", "codex/fixture-manifest.json",
                    "codex/canonical-choices.json", "codex/expected-scope.json",
                    "codex/root-prompt.txt", "codex/codex-request.json", "codex/case-started.json",
                    "codex/codex-response.json", "codex/codex-adapter.json",
                    "codex/shared-parser.exit-code.txt", "codex/config.toml.before",
                    "codex/config.toml.after")
        for relative in archived:
            self.assertTrue((output / relative).is_file(), relative)
        request = json.loads((output / "codex" / "codex-request.json").read_text(encoding="utf-8"))
        tokens = shlex.split(request["command"])
        self.assertIn("gpt-6-luna", tokens)
        self.assertIn('model_reasoning_effort="low"', tokens)
        install = json.loads((output / "codex" / "install.json").read_text(encoding="utf-8"))
        self.assertIn("https://github.com/ScholarWorkflow/professor-contact.git#"
                      "826dfa1d1757ad1dae26c1d1152c167758250c5c", install["command"])
        provenance = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["execution_kind"], "acceptance")
        self.assertEqual(provenance["host"], "codex")
        self.assertEqual(provenance["single_request_no_retry"], "yes")
        self.assertEqual(provenance["manual_patch"], "no")
        # Producer and fixture revisions verified clean before and after the run.
        producer, fixture = str(outcome["producer_root"]), str(outcome["fixture_root"])
        self.assertEqual(outcome["revisions"],
                         [(producer, "826dfa1d1757ad1dae26c1d1152c167758250c5c"),
                          (fixture, FIXTURE_SHA), (producer, "826dfa1d1757ad1dae26c1d1152c167758250c5c"),
                          (fixture, FIXTURE_SHA)])
        # The only subprocess judging dependency stays the root-history wrapper.
        parser = [command for command in outcome["invocations"]
                  if any(Path(part).name.startswith("parse_codex_eval_evidence") for part in command)]
        self.assertEqual(len(parser), 1)
        self.assertIn("parse_codex_eval_evidence_with_root_history.py", parser[0][1])
        contract_flag = parser[0][parser[0].index("--root-history-contract") + 1]
        self.assertEqual(Path(contract_flag).name, "codex-root-thread-read-contract.json")

    def test_entry_passes_fail_product_verdict_through_without_combining(self):
        import run_issue68_stage5_routing as base
        outcome = self.run_codex_only(self.root / "first-output")
        entry = outcome["entry"]
        output = self.root / "second-output"
        base.codex_host = lambda args, out: {"state": "CASE_STARTED", "verdict": "FAIL_PRODUCT",
                                             "reason_code": "root_consumed_results_conflict"}
        base.clean_revision = lambda root_path, expected: {"sha": expected, "dirty": "no"}
        rc = entry.main([
            "--producer-root", str(outcome["producer_root"]),
            "--producer-sha", "826dfa1d1757ad1dae26c1d1152c167758250c5c",
            "--fixture-root", str(outcome["fixture_root"]),
            "--fixture-sha", FIXTURE_SHA,
            "--eval-direnv-root", str(self.root / "eval"),
            "--output-dir", str(output)])
        self.assertEqual(rc, 1)
        final = json.loads((output / "final-verdict.json").read_text(encoding="utf-8"))
        codex = json.loads((output / "codex-verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(final, codex)
        self.assertEqual((final["verdict"], final["reason_code"]),
                         ("FAIL_PRODUCT", "root_consumed_results_conflict"))
        self.assertNotIn("hosts", final)

    def test_entry_rejects_nonempty_output_directory_before_any_host(self):
        output = self.root / "run-output"
        output.mkdir()
        (output / "stale.txt").write_text("旧产物\n", encoding="utf-8")
        outcome = self.run_codex_only(output)
        self.assertEqual(outcome["rc"], 2)
        self.assertFalse((output / "final-verdict.json").exists())
        self.assertFalse((output / "codex").exists())

    def test_entry_rejects_any_fixture_other_than_the_contract_frozen_one(self):
        output = self.root / "run-output"
        outcome = self.run_codex_only(output, fixture_sha="a96c239cca0e1e07eb142089e4d379baf4072277")
        self.assertEqual(outcome["rc"], 1)
        final = json.loads((output / "final-verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(final, {"state": "CASE_NOT_STARTED",
                                 "reason_code": "missing_or_wrong_frozen_fixture_arguments"})
        self.assertFalse((output / "codex").exists())
        self.assertFalse((output / "codex-verdict.json").exists())

    def test_entry_rejects_invocation_through_any_other_entrypoint(self):
        entry = self.main_entry()
        sys.argv[0] = str(entry.HERE / GENERIC_RUNNER_NAME)
        output = self.root / "run-output"
        rc = entry.main([
            "--producer-root", str(self.root / "producer"),
            "--producer-sha", "826dfa1d1757ad1dae26c1d1152c167758250c5c",
            "--fixture-root", str(self.root / "fixture"),
            "--fixture-sha", FIXTURE_SHA,
            "--eval-direnv-root", str(self.root / "eval"),
            "--output-dir", str(output)])
        self.assertEqual(rc, 1)
        final = json.loads((output / "final-verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(final, {"state": "CASE_NOT_STARTED",
                                 "reason_code": "entrypoint_uniqueness_violated"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
