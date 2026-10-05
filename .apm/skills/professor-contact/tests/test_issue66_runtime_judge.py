"""Channel validation for the S3-RT-CODEX-1 runtime judge (issue #66).

The judge is the frozen parsing/decision program for the runtime evidence
(``issue-66-test-plan-r19-clarification-r2-2026-10-05`` §五).  Each test
builds ONE synthetic evidence set whose expected verdict is fixed by the
frozen contract — never by the judge.  Sample families:

- three legal completions (one-round pass, corrected two-round pass,
  two-round exhaustion);
- credential / handoff value drift; missing first commit;
- formal relations (legal chain, zero spawns, nested violation, attribution
  conflict, child without a formal relation);
- raw production (legal whitespace message, root reconstruction, second
  business message, no validator production);
- file permissions (real read + one exclusive write pass; protected-file
  write and outside-output write fail) via real ``commandActions``;
- order and stops (rebuild before record, correction spawned before the
  round-1 record completed, dispatch after the terminal record, machine
  failure prefix honored → BLOCKED);
- evidence channels (unsupported message shape, truncated save output,
  version-less credential → INVALID).
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import judge_issue66_stage3_runtime as judge  # noqa: E402

ROOT = "root-thread-0001"
G1, V1, G2, V2 = ("gen-thread-0001", "val-thread-0001",
                  "gen-thread-0002", "val-thread-0002")
MD_NAME = judge.CANDIDATES_MD_NAME
STATE_NAME = judge.CANDIDATE_STATE_NAME
PACK_NAME = judge.INPUT_PACK_NAME
OUTPUT_FILE = "/tmp/fixture/validator-output.json"
HANDOFF_FILE = "/tmp/fixture/handoff.json"
HANDOFF_SHA = hashlib.sha256(b"handoff-bytes").hexdigest()
RECORDED_FILE = "/tmp/fixture/recorded.json"

PASS_STATE = {"validator": {"results": {
    "dir_A": {"result": "pass", "rounds": 1}}}}
TERMINAL2_STATE = {"validator": {"results": {
    "dir_A": {"result": "pass", "rounds": 2}}}}
EXHAUSTED_STATE = {"validator": {"results": {
    "dir_A": {"result": "fail_after_2_rounds", "rounds": 2}}}}


def msg_text(title="候选 dir_A_1", verdict="pass"):
    return json.dumps({"result": "ok", "files": [{
        "file": "/tmp/fixture/套磁想法候选.md", "artifact": "candidates",
        "verdict": verdict, "blocking": 0 if verdict == "pass" else 1,
        "minor": 0, "issues": [] if verdict == "pass" else
        [{"rule": "B5", "severity": "blocking",
          "location": "validator 自报位置", "quote": title,
          "suggestion": "首次出现时用日常语言解释。"}]}],
        "notes": "  非规范空白保留  "}, ensure_ascii=False, indent=2)


def msg_sha(text=None):
    return hashlib.sha256((text or msg_text()).encode("utf-8")).hexdigest()


def action(atype, path):
    return {"type": atype, "path": path,
            "command": f"demo {atype} {path}"}


def exec_item(index, thread, command, output=None, actions=None,
              truncate=False, status="completed"):
    if output is not None and truncate:
        output = "Warning: truncated output (original 9999 lines)\n" + output
    return {"message": {"method": "item/completed", "params": {
        "threadId": thread, "item": {"type": "commandExecution",
        "id": f"ce-{index}", "command": command,
        "aggregatedOutput": output, "exitCode": 0, "status": status,
        "commandActions": actions or []}}}}


def child_message(thread, text):
    return {"message": {"method": "rawResponseItem/completed", "params": {
        "threadId": thread, "item": {"type": "message", "role": "assistant",
        "content": [{"type": "output_text", "text": text}]}}}}


def spawn_events(index, call_id, agent_type, thread=None, machine_fail=False):
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
        return events
    events.append({"message": {"method": "item/started", "params": {
        "threadId": ROOT, "item": {"type": "subAgentActivity",
        "id": call_id, "kind": "started", "agentThreadId": thread}}}})
    events.append({"message": {"method": "item/completed", "params": {
        "threadId": ROOT, "item": {"type": "subAgentActivity",
        "id": call_id, "kind": "started", "agentThreadId": thread}}}})
    return events


class Fixture:
    """One synthetic run: ordered events + adapter relations + state."""

    def __init__(self):
        self.events = []
        self.children = []           # formal child thread ids, spawn order
        self.relations = []          # adapter formal relations
        self.spawn_specs = []        # (call_id, agent_type, thread|None)
        self._counter = iter(range(1, 1000))
        self.state = PASS_STATE

    # -- low-level builders -------------------------------------------------

    def _next(self):
        return next(self._counter)

    def root_exec(self, command, output=None, actions=None, truncate=False):
        self.events.append(exec_item(self._next(), ROOT, command, output,
                                     actions, truncate))

    def child_exec(self, thread, command, output=None, actions=None):
        self.events.append(exec_item(self._next(), thread, command, output,
                                     actions))

    def child_message(self, thread, text):
        self.events.append(child_message(thread, text))

    def spawn(self, agent_type, thread=None, machine_fail=False,
              call_id=None, reported_thread=None):
        index = self._next()
        call_id = call_id or f"call-{index}"
        shown = reported_thread or thread
        self.events += spawn_events(index, call_id, agent_type, shown,
                                    machine_fail=machine_fail)
        self.spawn_specs.append((call_id, agent_type, thread))
        if thread and not machine_fail:
            self.children.append(thread)
            self.relations.append({
                "call_id": call_id, "sender_thread_id": ROOT,
                "receiver_thread_ids": [thread], "status": "completed",
                "tool": "spawnAgent"})

    # -- business steps ------------------------------------------------------

    def generator_round(self, thread, *, with_capture=True, with_plan=True,
                        with_finalize=True, credential_drift=False,
                        round_no=None):
        if with_capture:
            self.child_exec(
                thread,
                "contact_state.py stage3-plan --professor-dir /tmp/fixture "
                "--program-root /tmp/fixture --capture-invocation /tmp/cap",
                json.dumps({"status": "ok",
                            "invocation_file": "/tmp/cap/x",
                            "invocation_sha256": "abc"}),
                actions=[action("read", f"/tmp/fixture/{PACK_NAME}")])
        if with_plan:
            drift = "999" if credential_drift else "abc"
            extra = (f" --validation-file {RECORDED_FILE}"
                     if round_no == 2 else "")
            self.child_exec(
                thread,
                "contact_state.py stage3-plan --invocation-file /tmp/cap/x "
                f"--invocation-sha256 {drift}{extra}",
                '{"status": "ok"}',
                actions=[action("read", f"/tmp/fixture/{PACK_NAME}")])
        if with_finalize:
            self.child_exec(
                thread,
                "contact_state.py stage3-finalize --invocation-file "
                "/tmp/cap/x --invocation-sha256 abc --results /tmp/results"
                + (f" --validation-file {RECORDED_FILE}"
                   if round_no == 2 else ""),
                '{"status": "ok", "state_path": "/tmp/fixture/state"}',
                actions=[action("read", f"/tmp/fixture/{PACK_NAME}")])

    def prepare(self, round_no, *, handoff_drift=False):
        sha = "drifted" if handoff_drift else HANDOFF_SHA
        self.root_exec(
            "contact_state.py stage3-prepare-validation --invocation-file "
            "/tmp/cap/x --invocation-sha256 abc "
            f"--round {round_no}",
            json.dumps({"status": "ok", "round": round_no,
                        "handoff_file": HANDOFF_FILE,
                        "handoff_sha256": sha,
                        "output_file": OUTPUT_FILE}),
            actions=[action("read", f"/tmp/fixture/{STATE_NAME}")])

    def validator_round(self, thread, *, text=None, no_write=False,
                        protected_write=False, outside_write=False,
                        double_message=False):
        actions = [action("read", f"/tmp/fixture/{MD_NAME}")]
        if not no_write:
            actions.append(action("write", OUTPUT_FILE))
        if protected_write:
            actions.append(action("write", f"/tmp/fixture/{STATE_NAME}"))
        if outside_write:
            actions.append(action("write", "/tmp/fixture/别的文件.json"))
        self.child_exec(thread, f"validator writes {OUTPUT_FILE}",
                        actions=actions)
        self.child_message(thread, text or msg_text())
        if double_message:
            self.child_message(thread, "第二条业务消息")

    def save(self, *, sha=None, handoff_drift=False, truncate=False,
             validation_file="/tmp/fixture/recorded.json"):
        sha = sha or msg_sha()
        used_sha = "drifted" if handoff_drift else HANDOFF_SHA
        self.root_exec(
            "contact_state.py stage3-save-validation --handoff-file "
            f"{HANDOFF_FILE} --handoff-sha256 {used_sha}",
            json.dumps({"status": "ok", "validation_sha256": sha,
                        "validation_file": validation_file}),
            actions=[action("read", OUTPUT_FILE),
                     action("write", validation_file)],
            truncate=truncate)

    def record(self, round_no, sha=None, needs_correction=False,
               handoff_drift=False, digest_drift=False):
        sha = sha or msg_sha()
        validation_file = RECORDED_FILE
        file_used = "/tmp/fixture/别的文件.json" if handoff_drift \
            else HANDOFF_FILE
        expected = "drifted" if digest_drift else sha
        extra = '"needs_correction": true, ' if needs_correction else ""
        self.root_exec(
            "contact_state.py stage3-record-validation --handoff-file "
            f"{file_used} --handoff-sha256 {HANDOFF_SHA} "
            f"--expected-validation-sha256 {expected}",
            json.dumps({"status": "ok",
                        "validation_input_sha256": sha,
                        "needs_correction": needs_correction,
                        "round": round_no}),
            actions=[action("read", validation_file if not handoff_drift
                            else OUTPUT_FILE)])

    def rebuild(self):
        self.root_exec(
            "contact_state.py stage3-rebuild-overview --program-root "
            "/tmp/fixture", '{"status": "ok"}')

    # -- standard chains ------------------------------------------------------

    def root_reconstruction(self):
        """The root rebuilds the source itself: a root exec writes the
        output file inside the round window; the validator never writes."""
        self.events.append(exec_item(
            self._next(), ROOT,
            "python3 -c 'open(\"" + OUTPUT_FILE + "\", \"w\")'",
            actions=[action("write", OUTPUT_FILE)]))

    def adapter(self):
        return {"dispatch": {"thread_relations": self.relations,
                             "agent_identity": []},
                "delegation": {"state": "confirmed",
                               "child_thread_ids": list(self.children),
                               "formal_child_count": len(self.children),
                               "basis": ["formal_spawn_relation"]},
                "child_thread_reads": {"entries": [
                    {"thread_id": thread,
                     "effective_role": agent,
                     "identity_eligible": True,
                     "parent_thread_id": ROOT,
                     "outcome": "success",
                     "relation_kind": "subAgentActivity.agentThreadId"}
                    for call_id, agent, thread in self.spawn_specs
                    if thread],
                    "entry_count": len(self.children),
                    "identity_eligible_thread_ids": list(self.children)}}

    def response(self):
        return {"output": {"thread_id": ROOT,
                           "app_server_events": self.events}}


def legal_two_child(fx: Fixture, *, whitespace=False):
    fx.spawn(judge.GENERATOR_AGENT, G1)
    fx.generator_round(G1)
    text = msg_text() + ("\n" if whitespace else "")
    fx.prepare(1)
    fx.spawn(judge.VALIDATOR_AGENT, V1)
    fx.validator_round(V1, text=text)
    fx.save(sha=msg_sha(text))
    fx.record(1, sha=msg_sha(text))
    fx.rebuild()


def legal_four_child(fx: Fixture, *, second_fails=False):
    legal_two_child_spine(fx)
    fx.spawn(judge.GENERATOR_AGENT, G2)
    fx.generator_round(G2, with_capture=False, round_no=2)
    fx.prepare(2)
    fx.spawn(judge.VALIDATOR_AGENT, V2)
    fail_text = msg_text("候选 dir_A_1 修正版", verdict="fail")
    if second_fails:
        fx.validator_round(V2, text=fail_text)
        fx.save(sha=msg_sha(fail_text))
        fx.record(2, sha=msg_sha(fail_text))
    else:
        fx.validator_round(V2, text=msg_text())
        fx.save(sha=msg_sha())
        fx.record(2, sha=msg_sha())
    fx.rebuild()


def legal_two_child_spine(fx: Fixture):
    fx.spawn(judge.GENERATOR_AGENT, G1)
    fx.generator_round(G1)
    fail_text = msg_text("候选 dir_A_1", verdict="fail")
    fx.prepare(1)
    fx.spawn(judge.VALIDATOR_AGENT, V1)
    fx.validator_round(V1, text=fail_text)
    fx.save(sha=msg_sha(fail_text))
    fx.record(1, sha=msg_sha(fail_text), needs_correction=True)


def run(fx: Fixture, *, state="default", delegation_override=None,
        delegation_state="confirmed"):
    tmp = Path(tempfile.mkdtemp())
    response_path = tmp / "response.json"
    adapter_path = tmp / "adapter.json"
    state_path = tmp / STATE_NAME
    output_path = tmp / "verdict.json"
    response_path.write_text(json.dumps(fx.response(), ensure_ascii=False),
                             encoding="utf-8")
    adapter = fx.adapter()
    if delegation_override is not None:
        delegation_children, relations = delegation_override
        adapter["delegation"]["child_thread_ids"] = list(delegation_children)
        adapter["delegation"]["formal_child_count"] = len(delegation_children)
        adapter["dispatch"]["thread_relations"] = relations
    adapter_path.write_text(json.dumps(adapter, ensure_ascii=False),
                            encoding="utf-8")
    if isinstance(state, dict) or state is None:
        if state is not None:
            state_path.write_text(json.dumps(state, ensure_ascii=False),
                                  encoding="utf-8")
    judge.main(["--eval-response", str(response_path),
                "--adapter-output", str(adapter_path),
                "--candidate-state", str(state_path),
                "--output", str(output_path)])
    return json.loads(output_path.read_text(encoding="utf-8"))


def facts(verdict):
    return {row["fact"]: row["verdict"] for row in verdict["facts"]}


class LegalCompletionTests(unittest.TestCase):
    def test_one_round_pass(self):
        fx = Fixture()
        legal_two_child(fx)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)

    def test_corrected_two_round_pass(self):
        fx = Fixture()
        legal_four_child(fx)
        verdict = run(fx, state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)

    def test_two_round_exhaustion_is_a_legal_pass(self):
        fx = Fixture()
        legal_four_child(fx, second_fails=True)
        verdict = run(fx, state=EXHAUSTED_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)

    def test_legal_whitespace_message_passes(self):
        fx = Fixture()
        legal_two_child(fx, whitespace=True)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)


class AttributionTests(unittest.TestCase):
    def test_zero_real_delegation_is_a_product_failure(self):
        fx = Fixture()
        fx.root_exec("cat plan", '{"status": "ok"}')
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-attribution"], "fail")

    def test_machine_failure_prefix_blocks(self):
        fx = Fixture()
        fx.generator_round(G1)
        fx.spawn(judge.GENERATOR_AGENT, G1)
        fx.spawn(judge.VALIDATOR_AGENT, None, machine_fail=True)
        verdict = run(fx, state=None,
                      delegation_override=([G1], fx.relations),
                      delegation_state="unconfirmed")
        self.assertEqual(verdict["classification"], "BLOCKED", verdict)

    def test_nested_foreign_relation_is_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.relations.append({"call_id": "call-foreign",
                             "sender_thread_id": V1,
                             "receiver_thread_ids": ["nested-thread"],
                             "status": "completed",
                             "tool": "spawnAgent"})
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)

    def test_child_without_formal_relation_is_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.relations = fx.relations[:-1]     # V1 loses its relation
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)


class CredentialValueTests(unittest.TestCase):
    def test_credential_value_drift_fails(self):
        fx = Fixture()
        legal_four_child(fx, second_fails=True)
        fx.events = [e for e in fx.events]      # keep
        # replay: swap the correction plan's credential digest to a wrong one
        for event in fx.events:
            item = event.get("message", {}).get("params", {}).get("item", {})
            if item.get("type") == "commandExecution" \
                    and "--validation-file" in item.get("command", "") \
                    and G2 in event["message"]["params"].get("threadId", ""):
                item["command"] = item["command"].replace(
                    "--invocation-sha256 abc", "--invocation-sha256 999")
        verdict = run(fx, state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")

    def test_missing_first_commit_fails(self):
        fx = Fixture()
        fx.prepare(1)
        fx.spawn(judge.GENERATOR_AGENT, G1)
        fx.generator_round(G1, with_finalize=False)
        fx.spawn(judge.VALIDATOR_AGENT, V1)
        fx.validator_round(V1)
        fx.save(sha=msg_sha())
        fx.record(1, sha=msg_sha())
        fx.rebuild()
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")


class RawOriginalTests(unittest.TestCase):
    def test_root_reconstruction_fails(self):
        fx = Fixture()
        legal_two_child_spine(fx)
        # validator produced nothing; the root rebuilt the same bytes itself
        fx.events = [e for e in fx.events
                     if not (e["message"]["params"]["item"].get("type")
                             == "commandExecution"
                             and e["message"]["params"].get("threadId")
                             == V1)]
        fx.root_reconstruction()
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_second_business_message_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.child_message(V1, "第二条业务消息")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_missing_production_is_a_gap(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            item = event["message"]["params"]["item"]
            if item.get("type") == "commandExecution" \
                    and event["message"]["params"].get("threadId") == V1:
                item["commandActions"] = [
                    action("read", f"/tmp/fixture/{MD_NAME}")]
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)


class WriteScopeTests(unittest.TestCase):
    def test_protected_file_write_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            item = event["message"]["params"]["item"]
            if item.get("type") == "commandExecution" \
                    and event["message"]["params"].get("threadId") == V1:
                item["commandActions"].append(
                    action("write", f"/tmp/fixture/{STATE_NAME}"))
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-validator-write-scope"], "fail")

    def test_outside_output_write_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            item = event["message"]["params"]["item"]
            if item.get("type") == "commandExecution" \
                    and event["message"]["params"].get("threadId") == V1:
                item["commandActions"].append(
                    action("write", "/tmp/fixture/别的文件.json"))
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)


class OrderAndStopTests(unittest.TestCase):
    def test_correction_spawned_before_record_completes_fails(self):
        fx = Fixture()
        fx.generator_round(G1)
        fx.prepare(1)
        fx.spawn(judge.GENERATOR_AGENT, G1)
        fx.spawn(judge.VALIDATOR_AGENT, V1)
        fx.validator_round(V1, text=msg_text("候选 dir_A_1", verdict="fail"))
        fx.save(sha=msg_sha(msg_text("候选 dir_A_1", verdict="fail")))
        fx.spawn(judge.GENERATOR_AGENT, G2)
        fx.record(1, sha=msg_sha(msg_text("候选 dir_A_1", verdict="fail")),
                  needs_correction=True)
        fx.generator_round(G2, with_capture=False, round_no=2)
        fx.prepare(2)
        fx.spawn(judge.VALIDATOR_AGENT, V2)
        fx.validator_round(V2)
        fx.save(sha=msg_sha())
        fx.record(2, sha=msg_sha())
        fx.rebuild()
        verdict = run(fx, state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-stop-order"], "fail")

    def test_dispatch_after_terminal_record_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.spawn(judge.GENERATOR_AGENT, G2)
        fx.generator_round(G2, with_capture=False, with_plan=False,
                           with_finalize=False)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-stop-order"], "fail")

    def test_rebuild_before_record_fails(self):
        fx = Fixture()
        legal_two_child_spine(fx)
        # move the rebuild before the round-1 record by appending a new
        # rebuild after the save but re-running with an earlier one is the
        # same violation; here the extra rebuild after the record is legal,
        # so instead place a rebuild directly after the save.
        fx.events = fx.events[:-1]
        fx.rebuild()
        fx.record(1, sha=msg_sha(msg_text("候选 dir_A_1", verdict="fail")),
                  needs_correction=True)
        fx.rebuild()
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-rebuild"], "fail")

    def test_terminal_round_bookkeeping_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        verdict = run(fx, state={"validator": {"results": {
            "dir_A": {"result": "fail_after_2_rounds", "rounds": 1}}}})
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-terminal-state"], "fail")


class EvidenceChannelTests(unittest.TestCase):
    def test_truncated_record_output_is_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            item = event["message"]["params"]["item"]
            params = event["message"].get("params", {})
            if item.get("type") == "commandExecution" \
                    and "stage3-record-validation" in item.get("command", "") \
                    and params.get("threadId") == ROOT:
                item["aggregatedOutput"] = (
                    "Warning: truncated output\n"
                    + (item.get("aggregatedOutput") or ""))
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)

    def test_unsupported_message_shape_is_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            item = event["message"]["params"]["item"]
            if item.get("type") == "message" \
                    and event["message"]["params"].get("threadId") == V1:
                item["content"] = [{"type": "input_image"}]
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)

    def test_handoff_value_drift_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            item = event["message"]["params"]["item"]
            params = event["message"].get("params", {})
            if item.get("type") == "commandExecution" \
                    and "stage3-record-validation" in item.get("command", "") \
                    and params.get("threadId") == ROOT:
                item["command"] = item["command"].replace(
                    f"--handoff-file {HANDOFF_FILE}",
                    "--handoff-file /tmp/fixture/别的handoff.json")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-handoff-chain"], "fail")


if __name__ == "__main__":
    unittest.main()
