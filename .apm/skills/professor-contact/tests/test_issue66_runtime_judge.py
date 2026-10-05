"""Channel validation for the S3-RT-CODEX-1 runtime judge (issue #66).

The judge is the frozen parsing/decision program for the runtime evidence;
per the Test Engineer Rule §3.2.2 it must distinguish — with minimal known
fixtures — legal success (PASS), legal product violation (FAIL), and
missing/unsupported evidence (INVALID_TEST_EXECUTION), and it must not
classify a machine-level spawn failure with an honored stop as a product
failure (BLOCKED).  Each test below builds one synthetic evidence set whose
expected verdict is fixed by the frozen contract, never by the judge itself.
"""
import json
import sys
import tempfile
import hashlib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import judge_issue66_stage3_runtime as judge  # noqa: E402

ROOT, G1, V1, G2, V2 = ("root-thread-0001", "gen-thread-0001",
                        "val-thread-0001", "gen-thread-0002",
                        "val-thread-0002")
MD_NAME = judge.CANDIDATES_MD_NAME
OUTPUT_FILE = "/tmp/fixture/validator-output.json"


def msg_json(verdict="pass"):
    return json.dumps({"result": "ok", "files": [{
        "file": "/tmp/fixture/套磁想法候选.md", "artifact": "candidates",
        "verdict": verdict, "blocking": 0, "minor": 0, "issues": []}],
        "notes": ""}, ensure_ascii=False)


def exec_item(index, command, output_json=None, truncate=False):
    output = None
    if output_json is not None:
        output = "Script completed\nOutput:\n" + output_json
        if truncate:
            output = "Warning: truncated output (original 9999 lines)\n" + output
    return {"message": {"method": "item/completed", "params": {
        "threadId": ROOT, "item": {"type": "commandExecution",
        "id": f"ce-{index}", "command": command, "aggregatedOutput": output,
        "exitCode": 0, "status": "completed"}}}}


def child_exec(thread, command, output=None):
    return {"message": {"method": "item/completed", "params": {
        "threadId": thread, "item": {"type": "commandExecution",
        "id": f"ce-child-{command[:12]}", "command": command,
        "aggregatedOutput": output, "exitCode": 0,
        "status": "completed"}}}}


def spawn(index, call_id, agent_type, thread, machine_fail=False):
    events = [{"message": {"method": "rawResponseItem/completed", "params": {
        "threadId": ROOT, "item": {"type": "function_call",
        "name": "spawn_agent", "call_id": call_id,
        "arguments": json.dumps({"task_name": f"t{index}",
                                 "agent_type": agent_type,
                                 "fork_turns": "all",
                                 "message": "gAAAAAB-payload"})}}}}]
    if machine_fail:
        events.append({"message": {"method": "rawResponseItem/completed",
            "params": {"threadId": ROOT, "item": {"type":
            "function_call_output", "call_id": call_id, "output": [
                {"type": "input_text", "text": "collab spawn failed: "
                 "no thread with id"}]}}}})
    else:
        events.append({"message": {"method": "item/started", "params": {
            "threadId": ROOT, "item": {"type": "subAgentActivity",
            "id": call_id, "kind": "started", "agentThreadId": thread}}}})
        events.append({"message": {"method": "item/started", "params": {
            "threadId": thread, "item": {"type": "userMessage",
            "text": "folder_path: /tmp/fixture\n"
                    f"套磁想法候选.md 绝对路径 + artifact: candidates "
                    f"+ output_file: {OUTPUT_FILE}"}}}})
    return events


def final_message(thread, text):
    return {"message": {"method": "rawResponseItem/completed", "params": {
        "threadId": thread, "item": {"type": "message", "role": "assistant",
        "content": [{"type": "output_text", "text": text}]}}}}


def adapter(state="confirmed", children=()):
    return {"dispatch": {"thread_relations": [
        {"call_id": f"call-{n}", "sender_thread_id": ROOT,
         "receiver_thread_ids": [child], "status": "completed",
         "tool": "spawnAgent"}
        for n, child in enumerate(children)],
        "agent_identity": []},
        "delegation": {"state": state,
                       "child_thread_ids": list(children),
                       "formal_child_count": len(children),
                       "basis": ["formal_spawn_relation"]}}


def base_run(*, rounds=1, drift=False, replay=False,
             dispatch_after=False, truncate_save=False, rebuild_before=False,
             machine_fail=False, bad_shape=False, protected_write=False,
             validator_writes_output=True):
    # The digests cited by save/record are the SHA-256 of the honest
    # message bytes; the drift case changes the message afterwards, so the
    # captured digests no longer match what the validator finally said.
    msg_sha = hashlib.sha256(msg_json().encode("utf-8")).hexdigest()
    events = []
    counter = iter(range(1000))

    # G1 spawn; the generator child runs plan/finalize inside its own
    # thread (r13 §7: the root never inlines stage3-plan/finalize).
    if not machine_fail:
        plan_cmd = ("contact_state.py stage3-plan --professor-dir "
                    "/tmp/fixture --program-root /tmp/fixture "
                    "--capture-invocation /tmp/cap")
        events.append(child_exec(G1, plan_cmd,
                                 '{"status": "ok", "invocation_file": '
                                 '"/tmp/cap/x", "invocation_sha256": "abc"}'))
        events.append(child_exec(
            G1, "contact_state.py stage3-plan --invocation-file /tmp/cap/x "
                "--invocation-sha256 abc",
            '{"status": "ok"}'))
        events.append(child_exec(
            G1, "contact_state.py stage3-finalize --invocation-file "
                "/tmp/cap/x --invocation-sha256 abc --results /tmp/results",
            '{"status": "ok", "state_path": "/tmp/fixture/state"}'))
        events.append(final_message(G1, msg_json()))
    events += spawn(next(counter), "call-0", judge.GENERATOR_AGENT, G1,
                    machine_fail=machine_fail)
    if machine_fail:
        # The machine-level spawn failure stops the run: no prepare, no
        # validator, no business exec anywhere.
        return events
    # Root prepares the round-1 handoff, then dispatches the validator.
    events.append(exec_item(
        next(counter),
        "contact_state.py stage3-prepare-validation --invocation-file "
        "/tmp/cap/x --invocation-sha256 abc --round 1",
        '{"status": "ok", "round": 1, "output_file": "%s"}' % OUTPUT_FILE))
    events += spawn(next(counter), "call-1", judge.VALIDATOR_AGENT, V1)
    if validator_writes_output:
        events.append(child_exec(V1, f"cat > {OUTPUT_FILE}"))
    if protected_write:
        events.append(child_exec(
            V1, "cat > /tmp/fixture/套磁候选状态.json <<EOF x"))
    if bad_shape:
        events.append({"message": {"method": "rawResponseItem/completed",
            "params": {"threadId": V1, "item": {"type": "message",
            "role": "assistant", "content": [{"type": "input_image"}]}}}})
    else:
        shown = msg_json()
        if drift:
            shown = msg_json() + " "
        events.append(final_message(V1, shown))
    events.append(exec_item(
        next(counter),
        "contact_state.py stage3-save-validation --handoff-file "
        "/tmp/h --handoff-sha256 def",
        ("{" + f'"status": "ok", "validation_sha256": "{msg_sha}", '
         f'"validation_file": "/tmp/v.json"' + "}"),
        truncate=truncate_save))
    record_extra = '"needs_correction": false, "round": 1' \
        if rounds == 1 else '"needs_correction": true, "round": 1'
    events.append(exec_item(
        next(counter),
        "contact_state.py stage3-record-validation --handoff-file /tmp/h "
        "--handoff-sha256 def --expected-validation-sha256 " + msg_sha,
        "{" + f'"status": "ok", "validation_input_sha256": "{msg_sha}", '
        + record_extra + "}"))
    if rounds == 2:
        # The correction generator consumes the same credential plus the
        # recorded validation file; then the round-2 handoff chain runs.
        events += spawn(next(counter), "call-2", judge.GENERATOR_AGENT, G2)
        events.append(child_exec(
            G2, corr_plan_cmd(replay),
            '{"status": "ok", "correction_scopes": ["direction:dir_A"]}'))
        events.append(child_exec(
            G2, "contact_state.py stage3-finalize --invocation-file "
                "/tmp/cap/x --invocation-sha256 abc --results /tmp/results2 "
                "--validation-file /tmp/recorded.json",
            '{"status": "ok", "corrected": ["dir_A"]}'))
        events.append(final_message(G2, msg_json()))
        events.append(exec_item(
            next(counter),
            "contact_state.py stage3-prepare-validation --invocation-file "
            "/tmp/cap/x --invocation-sha256 abc --round 2",
            '{"status": "ok", "round": 2}'))
        events += spawn(next(counter), "call-3", judge.VALIDATOR_AGENT, V2)
        events.append(final_message(V2, msg_json()))
        events.append(exec_item(
            next(counter),
            "contact_state.py stage3-save-validation --handoff-file /tmp/h2 "
            "--handoff-sha256 def",
            "{" + f'"status": "ok", "validation_sha256": "{msg_sha}"' + "}"))
        events.append(exec_item(
            next(counter),
            "contact_state.py stage3-record-validation --handoff-file /tmp/h2 "
            "--handoff-sha256 def --expected-validation-sha256 " + msg_sha,
            '{"status": "ok", "validation_input_sha256": "%s", '
            '"needs_correction": false, "round": 2}' % msg_sha))
    if dispatch_after:
        events += spawn(next(counter), "call-9", judge.GENERATOR_AGENT,
                        "gen-thread-0003")
    if rebuild_before:
        events.append(exec_item(
            next(counter),
            "contact_state.py stage3-rebuild-overview --program-root "
            "/tmp/fixture", '{"status": "ok"}'))
    events.append(exec_item(
        next(counter),
        "contact_state.py stage3-rebuild-overview --program-root "
        "/tmp/fixture", '{"status": "ok"}'))
    return events


def corr_plan_cmd(replay):
    if replay:
        return ("contact_state.py stage3-plan --professor-dir /tmp/fixture "
                "--validation-file /tmp/recorded.json")
    return ("contact_state.py stage3-plan --invocation-file /tmp/cap/x "
            "--invocation-sha256 abc --validation-file /tmp/recorded.json")


def run_judge(events=None, *, state=None, delegation_children=(),
              delegation_state="confirmed", tmp=None, **fixture):
    if events is None:
        events = base_run(**fixture)
    response = {"output": {"thread_id": ROOT,
                           "app_server_events": events}}
    tmp = tmp or Path(tempfile.mkdtemp())
    response_path = tmp / "response.json"
    adapter_path = tmp / "adapter.json"
    state_path = tmp / "套磁候选状态.json"
    output_path = tmp / "verdict.json"
    response_path.write_text(json.dumps(response, ensure_ascii=False),
                             encoding="utf-8")
    adapter_path.write_text(json.dumps(adapter(
        delegation_state, delegation_children), ensure_ascii=False),
        encoding="utf-8")
    if state is not None:
        state_path.write_text(json.dumps(state, ensure_ascii=False),
                              encoding="utf-8")
    judge.main(["--eval-response", str(response_path),
                "--adapter-output", str(adapter_path),
                "--candidate-state", str(state_path),
                "--output", str(output_path)])
    return json.loads(output_path.read_text(encoding="utf-8"))


PASS_STATE = {"validator": {"results": {
    "dir_A": {"result": "pass", "rounds": 1}}}}
TERMINAL2_STATE = {"validator": {"results": {
    "dir_A": {"result": "pass", "rounds": 2}}}}


class RuntimeJudgeChannelTests(unittest.TestCase):
    def verdict_of(self, **kwargs):
        state = kwargs.pop("state", PASS_STATE)
        return run_judge(state=state, **kwargs)

    def facts(self, verdict):
        return {row["fact"]: row["verdict"] for row in verdict["facts"]}

    def test_legal_two_child_run_passes(self):
        verdict = self.verdict_of(rounds=1)
        self.assertEqual(verdict["classification"], "PASS", verdict)

    def test_legal_four_child_correction_run_passes(self):
        verdict = self.verdict_of(rounds=2, state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)

    def test_byte_drift_fails(self):
        verdict = self.verdict_of(rounds=1, drift=True)
        self.assertEqual(verdict["classification"], "FAIL")
        self.assertEqual(self.facts(verdict)["F-four-point-identity"], "fail")

    def test_validator_write_outside_scope_fails(self):
        verdict = self.verdict_of(rounds=1, protected_write=True)
        self.assertEqual(verdict["classification"], "FAIL")
        self.assertEqual(self.facts(verdict)["F-validator-write-scope"],
                         "fail")

    def test_source_replay_fails(self):
        verdict = self.verdict_of(rounds=2, replay=True,
                                  state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "FAIL")
        self.assertEqual(self.facts(verdict)["F-credential-chain"], "fail")

    def test_dispatch_after_record_fails(self):
        verdict = self.verdict_of(rounds=2, dispatch_after=True,
                                  state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "FAIL")
        self.assertEqual(self.facts(verdict)["F-stop-order"], "fail")

    def test_truncated_save_output_is_invalid(self):
        verdict = self.verdict_of(rounds=1, truncate_save=True)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION")

    def test_unsupported_message_shape_is_invalid(self):
        verdict = self.verdict_of(rounds=1, bad_shape=True)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION")

    def test_machine_spawn_failure_blocks(self):
        verdict = run_judge(rounds=1, machine_fail=True, state=None,
                            delegation_children=(),
                            delegation_state="unconfirmed")
        self.assertEqual(verdict["classification"], "BLOCKED", verdict)

    def test_rebuild_before_record_fails(self):
        verdict = self.verdict_of(rounds=1, rebuild_before=True)
        self.assertEqual(verdict["classification"], "FAIL")
        self.assertEqual(self.facts(verdict)["F-rebuild-stage4"], "fail")

    def test_missing_validator_record_fails(self):
        verdict = self.verdict_of(rounds=1, state={"validator": None})
        self.assertEqual(verdict["classification"], "FAIL")
        self.assertEqual(self.facts(verdict)["F-terminal-state"], "fail")

    def test_zero_spawns_fails(self):
        verdict = run_judge(events=[], state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL")


if __name__ == "__main__":
    unittest.main()
