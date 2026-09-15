"""Issue #39: machine verdict for the PC39-R1 endpoint runtime evidence.

The verifier must decide from structured evidence only: the fixture adapter's
formal child thread, that child's ``item/completed`` command events, and a
second JSON parse of the JSON-RPC payloads inside their command output.
Assistant prose, named identity, paper-analysis completion, or ``stage2-final``
state must never influence the verdict.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
HELPER_PATH = TESTS_DIR / "runtime" / "verify_issue39_endpoint_runtime.py"
spec = importlib.util.spec_from_file_location("verify_issue39_endpoint_runtime", HELPER_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

ITEM_KEYS = ["ZK9QA2XA", "ZK8PB4YB"]
RUN_ID = "zotero-20260915T000000Z-00001"
CHILD = "child-thread-1"
PARENT = "root-thread-1"


def items_config():
    return {
        "schema_version": 1,
        "fixture_repository": "skills-test-fixtures",
        "fixture_revision": "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972",
        "fixture_run_id": RUN_ID,
        "item_keys": ITEM_KEYS,
        "ready_item_keys": [ITEM_KEYS[0]],
        "fill_target_item_key": ITEM_KEYS[1],
        "fill_target_pdf_status": "pending",
    }


def fixture_evidence():
    return {
        "fixture_kind": "zotero",
        "fixture_repo_sha": "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972",
        "fixture_repo_dirty": "no",
        "fixture_run_id": RUN_ID,
        "manual_patch": "no",
    }


def adapter(state="confirmed", children=(CHILD,)):
    return {"delegation": {"state": state, "formal_child_count": len(children),
                           "child_thread_ids": list(children)}}


def command_event(command, aggregated_output, thread=CHILD, seq=10):
    return {"direction": "out", "runtime_seq": seq, "message": {
        "method": "item/completed",
        "params": {"threadId": thread, "item": {
            "type": "commandExecution", "id": f"exec-{seq}",
            "command": command, "exitCode": 0, "status": "completed",
            "aggregatedOutput": aggregated_output}}}}


def details_command(item_key, url="http://127.0.0.1:24122/mcp", rpc_id=11):
    body = json.dumps({"jsonrpc": "2.0", "id": rpc_id, "method": "tools/call",
                       "params": {"name": "get_item_details",
                                  "arguments": {"itemKey": item_key}}})
    return f"curl -s {url} -H 'Content-Type: application/json' -d '{body}'"


def details_response(item_key, rpc_id=11):
    inner = json.dumps({"itemKey": item_key,
                        "title": "Adaptive Processing in Synthetic Systems"})
    return json.dumps({"jsonrpc": "2.0", "id": rpc_id,
                       "result": {"content": [{"type": "text", "text": inner}]}})


def sse_response(payload):
    return "event: message\ndata: " + payload + "\n"


def build_request_json(**config_overrides):
    # encode argv the way the builder does: shlex-joined
    import shlex
    values = [
        'model_reasoning_effort="low"',
        'projects={"' + "/clean/consumer" + '"={trust_level="trusted"}}',
        "sandbox_workspace_write.network_access=true",
        'shell_environment_policy.set.ZOTERO_HTTP_URL="http://127.0.0.1:24119"',
        'shell_environment_policy.set.ZOTERO_MCP_URL="http://127.0.0.1:24122/mcp"',
    ]
    for name, value in config_overrides.items():
        values.append(value)
    argv = ["--json", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "workspace-write", "--cd", "/clean/consumer",
            "--model", "gpt-5.6-luna"]
    for value in values:
        argv.extend(["--config", value])
    argv.extend(["--", "Delegate this task to the installed custom agent."])
    return {"command": shlex.join(argv), "timeout": 1800}


def run(tmp, *, eval_response, adapter_payload, request, items=None,
        evidence=None, expected_http="http://127.0.0.1:24119",
        expected_mcp="http://127.0.0.1:24122/mcp",
        consumer_root="/clean/consumer", write=False):
    arguments = dict(
        eval_response=eval_response,
        adapter=adapter_payload,
        request=request,
        zotero_items_config=items if items is not None else items_config(),
        fixture_evidence=evidence if evidence is not None else fixture_evidence(),
        expected_http_url=expected_http,
        expected_mcp_url=expected_mcp,
        consumer_root=consumer_root,
    )
    if write:
        output = Path(tmp) / "verdict.json"
        arguments["output"] = output
    verdict = helper.run_verification(**arguments)
    if write:
        return verdict, json.loads(output.read_text())
    return verdict, None


class VerifyIssue39EndpointRuntimeTests(unittest.TestCase):
    def test_pass_when_formal_child_reads_a_seeded_item(self):
        with tempfile.TemporaryDirectory() as directory:
            events = [command_event(details_command(ITEM_KEYS[0]),
                                    details_response(ITEM_KEYS[0]))]
            verdict, written = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(),
                request=build_request_json(),
                write=True)
            self.assertEqual(verdict["status"], "PASS")
            self.assertEqual(verdict["observed_item_keys"], [ITEM_KEYS[0]])
            self.assertEqual(written["status"], "PASS")
            self.assertEqual(written["formal_child_thread_ids"], [CHILD])
            self.assertEqual(written["seeded_item_keys"], ITEM_KEYS)

    def test_pass_parses_sse_framed_json_rpc_output(self):
        with tempfile.TemporaryDirectory() as directory:
            events = [command_event(details_command(ITEM_KEYS[1]),
                                    sse_response(details_response(ITEM_KEYS[1])))]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "PASS")
            self.assertEqual(verdict["observed_item_keys"], [ITEM_KEYS[1]])

    def test_ignores_events_outside_the_formal_child_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            events = [command_event(details_command(ITEM_KEYS[0]),
                                    details_response(ITEM_KEYS[0]), thread=PARENT)]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "BLOCKED_OBSERVABILITY")
            self.assertEqual(verdict["observed_item_keys"], [])

    def test_blocked_when_delegation_not_confirmed(self):
        with tempfile.TemporaryDirectory() as directory:
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": []}},
                adapter_payload=adapter(state="missing", children=()),
                request=build_request_json())
            self.assertEqual(verdict["status"], "BLOCKED_TEST_CONFIGURATION")

    def test_blocked_when_request_carries_chrome_or_mcp_config(self):
        request = build_request_json()
        request["command"] += (
            " --config "
            "'mcp_servers.pdf-chrome.env.CHROME_PROFILE_DIR=\"/tmp/p\"'")
        with tempfile.TemporaryDirectory() as directory:
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": []}},
                adapter_payload=adapter(), request=request)
            self.assertEqual(verdict["status"], "BLOCKED_TEST_CONFIGURATION")
            names = [check["name"] for check in verdict["checks"]]
            self.assertIn("request_free_of_chrome_mcp_npm", names)

    def test_blocked_when_request_endpoints_do_not_match_this_run(self):
        with tempfile.TemporaryDirectory() as directory:
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": []}},
                adapter_payload=adapter(), request=build_request_json(),
                expected_http="http://127.0.0.1:25119")
            self.assertEqual(verdict["status"], "BLOCKED_TEST_CONFIGURATION")

    def test_blocked_when_request_lacks_consumer_trust(self):
        with tempfile.TemporaryDirectory() as directory:
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": []}},
                adapter_payload=adapter(), request=build_request_json(),
                consumer_root="/another/consumer")
            self.assertEqual(verdict["status"], "BLOCKED_TEST_CONFIGURATION")

    def test_blocked_when_fixture_and_seed_run_ids_disagree(self):
        with tempfile.TemporaryDirectory() as directory:
            items = items_config()
            items["fixture_run_id"] = "another-run"
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": []}},
                adapter_payload=adapter(), request=build_request_json(),
                items=items)
            self.assertEqual(verdict["status"], "BLOCKED_TEST_CONFIGURATION")

    def test_blocked_observability_when_child_never_reads_a_seeded_item(self):
        with tempfile.TemporaryDirectory() as directory:
            events = [command_event("echo waiting", "no zotero traffic here")]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "BLOCKED_OBSERVABILITY")

    def test_fail_producer_when_child_accesses_production_default_port(self):
        with tempfile.TemporaryDirectory() as directory:
            events = [command_event(
                details_command(ITEM_KEYS[0],
                                url="http://127.0.0.1:23120/mcp"),
                details_response(ITEM_KEYS[0]))]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "FAIL_PRODUCER")

    def test_fail_producer_when_child_builds_mcp_mcp_path(self):
        with tempfile.TemporaryDirectory() as directory:
            events = [command_event(
                details_command(ITEM_KEYS[0],
                                url="http://127.0.0.1:24122/mcp/mcp"),
                details_response(ITEM_KEYS[0]))]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "FAIL_PRODUCER")

    def test_blocked_when_json_rpc_call_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            error_response = json.dumps({
                "jsonrpc": "2.0", "id": 11,
                "error": {"code": -32000, "message": "not found"}})
            events = [command_event(details_command(ITEM_KEYS[0]), error_response)]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "BLOCKED_OBSERVABILITY")

    def test_pass_when_reads_use_shell_escaped_bodies_and_transformed_output(self):
        """Real analyzer children run inside quoted zsh: the JSON-RPC request is
        shell-escaped in the command line, and successful reads surface as
        jq-transformed objects, not raw JSON-RPC frames."""
        with tempfile.TemporaryDirectory() as directory:
            body = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                               "params": {"name": "get_item_abstract",
                                          "arguments": {"itemKey": ITEM_KEYS[0]}}})
            command = (
                'ZOTERO_MCP_URL="${ZOTERO_MCP_URL:-http://127.0.0.1:23120/mcp}"; '
                'ZOTERO_MCP_URL="${ZOTERO_MCP_URL%/}"; '
                f'curl -sS -X POST "$ZOTERO_MCP_URL" -d "{body}" | '
                "jq -r '...' ")
            # the command text contains shell-escaped quotes, exactly as the
            # app-server serializes it
            command = command.replace('"', '\\"')
            transformed = json.dumps({
                "item_key": ITEM_KEYS[0], "op": "get_item_abstract",
                "data": {"itemKey": ITEM_KEYS[0], "title": "Adaptive Processing"}})
            events = [command_event(command, transformed)]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "PASS")
            self.assertEqual(verdict["observed_item_keys"], [ITEM_KEYS[0]])
            self.assertEqual(verdict["production_endpoint_attempts"], [])

    def test_default_endpoint_literals_in_fallback_expansions_are_not_violations(self):
        with tempfile.TemporaryDirectory() as directory:
            body = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                               "params": {"name": "get_item_details",
                                          "arguments": {"itemKey": ITEM_KEYS[0]}}})
            command = (
                'ZOTERO_HTTP_URL="${ZOTERO_HTTP_URL:-http://127.0.0.1:23119}"; '
                'ZOTERO_MCP_URL="${ZOTERO_MCP_URL:-http://127.0.0.1:23120/mcp}"; '
                f'curl -fsS "$ZOTERO_HTTP_URL/connector/ping"; '
                f'curl -sS -X POST "$ZOTERO_MCP_URL" -d "{body}"')
            transformed = json.dumps({
                "item_key": ITEM_KEYS[0], "op": "get_item_details",
                "data": {"itemKey": ITEM_KEYS[0]}})
            events = [command_event(command, transformed)]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "PASS")
            self.assertEqual(verdict["production_endpoint_attempts"], [])

    def test_records_failed_production_endpoint_attempt_while_reads_succeed(self):
        with tempfile.TemporaryDirectory() as directory:
            violation = (
                "SID=mcp-x; END=http://127.0.0.1:23120/mcp; "
                'curl -sS -X POST "$END" -d '
                "'"
                + json.dumps({"itemKey": ITEM_KEYS[0]})
                + "'")
            resolved = details_command(ITEM_KEYS[0])
            transformed = json.dumps({
                "item_key": ITEM_KEYS[0], "op": "get_item_details",
                "data": {"itemKey": ITEM_KEYS[0]}})
            events = [
                command_event(violation, "curl: (7) Failed to connect", seq=10),
                command_event(resolved, details_response(ITEM_KEYS[0]), seq=20),
            ]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "PASS")
            self.assertEqual(len(verdict["production_endpoint_attempts"]), 1)
            self.assertEqual(verdict["observed_item_keys"], [ITEM_KEYS[0]])

    def test_scripted_reads_pair_tool_key_lists_with_result_frames(self):
        """Real children sometimes move the JSON-RPC bodies into a helper
        script: the command only names tool+key pairs and the output carries
        the raw result frames."""
        with tempfile.TemporaryDirectory() as directory:
            planner = (
                'SID=$(bash new-session.sh); for spec in '
                "'get_item_details " + ITEM_KEYS[0] + "'"
                " 'get_item_abstract " + ITEM_KEYS[1] + "'; do "
                'curl -sS -X POST "$ZOTERO_MCP_URL" -d "$(jq -nc ...)" ; done')
            runner = "sh /tmp/pc_mcp.sh"

            def result_frame(key):
                inner = json.dumps({"itemKey": key, "title": "T"})
                return json.dumps({"jsonrpc": "2.0", "id": 2,
                                   "result": {"content": [
                                       {"type": "text", "text": inner}]}})

            output = "\n".join(result_frame(key) for key in ITEM_KEYS)
            events = [
                command_event(planner, "session ok", seq=10),
                command_event(runner, output, seq=20),
            ]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "PASS")
            self.assertEqual(sorted(verdict["observed_item_keys"]),
                             sorted(ITEM_KEYS))

    def test_result_frames_without_read_tool_reference_stay_unobserved(self):
        with tempfile.TemporaryDirectory() as directory:
            command, _ = details_command(ITEM_KEYS[0]), 11
            frames = "\n".join(
                json.dumps({"jsonrpc": "2.0", "id": 2,
                            "result": {"content": [{"type": "text",
                                                    "text": json.dumps({"itemKey": key})}]}})
                for key in ITEM_KEYS)
            events = [command_event("bash helper.sh", frames)]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "BLOCKED_OBSERVABILITY")

    def test_templated_loop_reads_count_when_payloads_print(self):
        """A real child loops seeded keys over a case-templated JSON-RPC body
        (itemKey bound to a shell variable) and prints pretty item payloads."""
        with tempfile.TemporaryDirectory() as directory:
            command = (
                "set -e\n"
                "MCP='http://127.0.0.1:24122/mcp'\n"
                f"for K in {ITEM_KEYS[0]} {ITEM_KEYS[1]}; do\n"
                '  case "$pair" in details) body=\'{"jsonrpc":"2.0","id":1,'
                '"method":"tools/call","params":{"name":"get_item_details",'
                '"arguments":{"itemKey":"$K"}}}\';; esac\n'
                '  curl -sS -X POST "$MCP" -d "$body" | jq .\n'
                "done")
            payload = json.dumps({
                "key": ITEM_KEYS[0], "itemType": "journalArticle",
                "title": "Adaptive Processing in Synthetic Systems",
                "abstractNote": "A deterministic synthetic paper.",
            }, indent=1)
            events = [command_event(command, payload)]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "PASS")
            self.assertIn(ITEM_KEYS[0], verdict["observed_item_keys"])

    def test_item_payload_without_read_tool_reference_stays_unobserved(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = json.dumps({
                "key": ITEM_KEYS[0], "itemType": "journalArticle",
                "title": "Adaptive Processing in Synthetic Systems",
            })
            events = [command_event("jq . papers.json", payload)]
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": events}},
                adapter_payload=adapter(), request=build_request_json())
            self.assertEqual(verdict["status"], "BLOCKED_OBSERVABILITY")

    def test_trust_check_resolves_symlinked_consumer_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            real = base / "real-consumer"
            link = base / "link-consumer"
            real.mkdir()
            link.symlink_to(real)
            request = build_request_json()
            request["command"] = request["command"].replace(
                "/clean/consumer", str(real))
            verdict, _ = run(
                directory,
                eval_response={"output": {"app_server_events": []}},
                adapter_payload=adapter(), request=request,
                consumer_root=str(link))
            trust = [check for check in verdict["checks"]
                     if check["name"] == "request_trusts_exact_clean_consumer"]
            self.assertEqual(trust[0]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
