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
  write and outside-output write fail) via command behavior and file changes;
- order and stops (rebuild before record, correction spawned before the
  round-1 record completed, dispatch after the terminal record, machine
  failure prefix honored → BLOCKED);
- evidence channels (unsupported message shape, truncated save output,
  version-less credential → INVALID).
"""
import ast
import hashlib
import inspect
import json
import os
import shlex
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
CREDENTIAL_FILE = "/tmp/cap/x"
CREDENTIAL_SHA = hashlib.sha256(b"fixture invocation credential").hexdigest()
PROFESSOR_NAME = "fixture professor"

PASS_STATE = {"validator": {"results": {
    "dir_A": {"result": "pass", "rounds": 1}}},
    "profile_fingerprint": None}
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
              truncate=False, status="completed", turn_id=None,
              cwd="/tmp/fixture"):
    if output is not None and truncate:
        output = "Warning: truncated output (original 9999 lines)\n" + output
    params = {"threadId": thread, "turnId": turn_id,
              "item": {"type": "commandExecution", "id": f"ce-{index}",
                       "command": command, "cwd": cwd}}
    started = {"message": {"method": "item/started", "params": {
        **params, "item": {**params["item"], "status": "inProgress"}}}}
    completed = {"message": {"method": "item/completed", "params": {
        **params, "item": {**params["item"], "aggregatedOutput": output,
                            "exitCode": 0 if status == "completed" else 1,
                            "status": status, "commandActions": actions or []}}}}
    return [started, completed]


def child_message(thread, text, turn_id=None):
    return {"message": {"method": "rawResponseItem/completed", "params": {
        "threadId": thread, "turnId": turn_id,
        "item": {"type": "message", "id": f"msg-{thread}",
        "role": "assistant",
        "content": [{"type": "output_text", "text": text}]}}}}


def file_change_event(thread, path, operation="created", turn_id=None,
                      content=None, status="completed"):
    change = {"path": path, "kind": operation}
    if content is not None:
        raw = content if isinstance(content, bytes) else content.encode("utf-8")
        text = raw.decode("utf-8")
        lines = text.split("\n")
        if raw.endswith(b"\n"):
            lines = lines[:-1]
        diff = (f"--- /dev/null\n+++ b/{Path(path).name}\n"
                f"@@ -0,0 +1,{len(lines)} @@\n"
                + "\n".join("+" + line for line in lines))
        if raw.endswith(b"\n"):
            diff += "\n"
        change["diff"] = diff
    params = {"threadId": thread, "turnId": turn_id, "item": {
        "type": "fileChange", "id": f"fc-{thread}-{Path(path).name}",
        "status": status, "changes": [change]}}
    if turn_id is not None:
        params["turnId"] = turn_id
    return {"message": {"method": "item/completed", "params": params}}


def add_validator_file_change(fx, path, operation="created", content=None,
                              status="completed"):
    finish = next(index for index, event in enumerate(fx.events)
                  if event.get("message", {}).get("method") == "item/completed"
                  and event.get("message", {}).get("params", {}).get("item", {}).get("type")
                  == "subAgentActivity"
                  and event["message"]["params"]["item"].get("kind") == "completed"
                  and event["message"]["params"]["item"].get("agentThreadId") == V1)
    fx.events.insert(finish, file_change_event(
        V1, path, operation=operation, turn_id=fx.turn_id(V1),
        content=content, status=status))


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
        self.include_turn_completed = True
        self.profile_fingerprint = None

    @staticmethod
    def turn_id(thread):
        return {G1: "turn-gen-1", V1: "turn-val-1",
                G2: "turn-gen-2", V2: "turn-val-2"}.get(thread,
                                                             "root-turn-1")

    # -- low-level builders -------------------------------------------------

    def _next(self):
        return next(self._counter)

    def root_exec(self, command, output=None, actions=None, truncate=False):
        self.events.extend(exec_item(self._next(), ROOT, command, output,
                                     actions, truncate,
                                     turn_id=self.turn_id(ROOT)))

    def child_exec(self, thread, command, output=None, actions=None):
        self.events.extend(exec_item(self._next(), thread, command, output,
                                     actions, turn_id=self.turn_id(thread)))

    def child_message(self, thread, text):
        self.events.append(child_message(thread, text, self.turn_id(thread)))

    def complete_child(self, thread):
        spec = next((row for row in reversed(self.spawn_specs)
                     if row[2] == thread), None)
        if spec is None:
            return
        call_id, _agent_type, _thread = spec
        self.events.append({"message": {"method": "item/completed", "params": {
            "threadId": ROOT, "turnId": self.turn_id(ROOT),
            "item": {"type": "subAgentActivity", "id": call_id,
                     "kind": "completed", "agentThreadId": thread}}}})
        self.events.append({"message": {"method": "item/completed", "params": {
            "threadId": ROOT, "turnId": self.turn_id(ROOT),
            "item": {"type": "function_call_output", "call_id": call_id,
                     "output": [{"type": "input_text", "text": "completed"}]}}}})

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
        profile_arg = (f" --profile {shlex.quote(self.profile_path)}"
                       if getattr(self, "profile_path", None) else "")
        if with_capture:
            self.child_exec(
                thread,
                "contact_state.py stage3-plan --professor-dir /tmp/fixture "
                "--program-root /tmp/fixture" + profile_arg
                + " --capture-invocation /tmp/cap",
                json.dumps({"status": "ok",
                            "invocation_file": CREDENTIAL_FILE,
                            "invocation_sha256": CREDENTIAL_SHA,
                            "professor": PROFESSOR_NAME,
                            "professor_dir": "/tmp/fixture",
                            "refresh_scope": "flagged",
                            "direction_id": None,
                            "profile_fingerprint": self.profile_fingerprint}),
                actions=[action("read", f"/tmp/fixture/{PACK_NAME}")])
        if with_plan:
            drift = "f" * 64 if credential_drift else CREDENTIAL_SHA
            extra = (f" --validation-file {RECORDED_FILE}"
                     if round_no == 2 else "")
            self.child_exec(
                thread,
                f"contact_state.py stage3-plan --invocation-file {CREDENTIAL_FILE} "
                f"--invocation-sha256 {drift}{extra}",
                json.dumps({"status": "ok", "professor": PROFESSOR_NAME,
                            "professor_dir": "/tmp/fixture",
                            "refresh_scope": "flagged", "direction_id": None,
                            "profile_fingerprint": self.profile_fingerprint}),
                actions=[action("read", f"/tmp/fixture/{PACK_NAME}")])
        if with_finalize:
            self.child_exec(
                thread,
                f"contact_state.py stage3-finalize --invocation-file "
                f"{CREDENTIAL_FILE} --invocation-sha256 {CREDENTIAL_SHA} "
                "--results /tmp/results"
                + (f" --validation-file {RECORDED_FILE}"
                   if round_no == 2 else ""),
                json.dumps({"status": "ok", "professor": PROFESSOR_NAME,
                            "state_path": "/tmp/fixture/state.json"}),
                actions=[action("read", f"/tmp/fixture/{PACK_NAME}")])
        self.complete_child(thread)

    def prepare(self, round_no, *, handoff_drift=False):
        sha = "drifted" if handoff_drift else HANDOFF_SHA
        self.root_exec(
            "contact_state.py stage3-prepare-validation --invocation-file "
            f"{CREDENTIAL_FILE} --invocation-sha256 {CREDENTIAL_SHA} "
            f"--round {round_no}",
                json.dumps({"status": "ok", "round": round_no,
                        "professor": PROFESSOR_NAME,
                        "professor_dir": "/tmp/fixture",
                        "handoff_file": HANDOFF_FILE,
                        "handoff_sha256": sha,
                        "output_file": OUTPUT_FILE,
                        "validation_file": RECORDED_FILE,
                        "render_sha256": "render-digest"}),
            actions=[action("read", f"/tmp/fixture/{STATE_NAME}")])

    def validator_round(self, thread, *, text=None, no_write=False,
                        protected_write=False, outside_write=False,
                        double_message=False):
        text = text or msg_text()
        actions = [action("read", f"/tmp/fixture/{MD_NAME}")]
        raw = text.encode("utf-8")
        writer = (f"open({OUTPUT_FILE!r}, 'xb').write({raw!r})")
        if not no_write:
            self.child_exec(thread, "python3 -c " + shlex.quote(writer),
                            output="", actions=actions)
        else:
            self.child_exec(thread, f"cat /tmp/fixture/{MD_NAME}",
                            output="read", actions=actions)
        if protected_write:
            self.events.append(file_change_event(
                thread, f"/tmp/fixture/{STATE_NAME}",
                turn_id=self.turn_id(thread)))
        if outside_write:
            self.events.append(file_change_event(
                thread, "/tmp/fixture/别的文件.json",
                turn_id=self.turn_id(thread)))
        self.child_message(thread, text)
        if double_message:
            self.child_message(thread, "第二条业务消息")
        self.complete_child(thread)

    def save(self, *, sha=None, handoff_drift=False, truncate=False,
             validation_file="/tmp/fixture/recorded.json", round_no=1):
        sha = sha or msg_sha()
        used_sha = "drifted" if handoff_drift else HANDOFF_SHA
        self.root_exec(
            "contact_state.py stage3-save-validation --handoff-file "
            f"{HANDOFF_FILE} --handoff-sha256 {used_sha}",
            json.dumps({"status": "ok", "validation_sha256": sha,
                        "professor": PROFESSOR_NAME,
                        "professor_dir": "/tmp/fixture",
                        "validation_file": validation_file,
                        "round": round_no, "render_sha256": "render-digest"}),
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
                        "terminal": not needs_correction,
                        "round": round_no,
                        "state_path": "/tmp/fixture/套磁候选状态.json",
                        "render_sha256": "render-digest"}),
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
        self.events.extend(exec_item(
            self._next(), ROOT,
            "python3 -c 'open(\"" + OUTPUT_FILE + "\", \"w\")'",
            actions=[action("write", OUTPUT_FILE)],
            turn_id=self.turn_id(ROOT)))

    def adapter(self):
        return {"evidence_set_id": "issue66-fixture-run-1",
                "dispatch": {"thread_relations": self.relations,
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
        events = []
        for index, event in enumerate(self.events, start=1):
            sequenced = dict(event)
            sequenced.setdefault("seq", index)
            events.append(sequenced)
        if self.include_turn_completed:
            events.append({"seq": len(events) + 1,
                           "message": {"method": "turn/completed"}})
        return {"evidence_set_id": "issue66-fixture-run-1",
                "output": {"thread_id": ROOT,
                           "app_server_events": events}}


def mutate_command_return(fx, thread, subcommand, mutate):
    for event in fx.events:
        message = event.get("message", {})
        params = message.get("params", {})
        item = params.get("item", {})
        if message.get("method") != "item/completed" \
                or params.get("threadId") != thread \
                or item.get("type") != "commandExecution" \
                or subcommand not in item.get("command", ""):
            continue
        payload, state = judge.Judge._json_from_output(
            item.get("aggregatedOutput"))
        if state != "ok" or not isinstance(payload, dict):
            raise AssertionError(f"cannot mutate {subcommand} return: {state}")
        mutate(payload)
        item["aggregatedOutput"] = json.dumps(payload, ensure_ascii=False)
        return
    raise AssertionError(f"missing {subcommand} return on {thread}")


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
        fx.save(sha=msg_sha(fail_text), round_no=2)
        fx.record(2, sha=msg_sha(fail_text))
    else:
        fx.validator_round(V2, text=msg_text())
        fx.save(sha=msg_sha(), round_no=2)
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


def valid_surfaces(fx: Fixture):
    """Complete independent install, sample, storage, snapshot and route inputs."""
    relations = [row for row in fx.relations
                 if isinstance(row, dict) and row.get("tool") == "spawnAgent"]
    owners = {}
    direct_ids = set()
    nested = []
    for relation in relations:
        sender = relation["sender_thread_id"]
        receivers = relation["receiver_thread_ids"]
        for child in receivers:
            owners.setdefault(child, set()).add(sender)
            if sender == ROOT:
                direct_ids.add(child)
        if sender != ROOT:
            nested.append({"sender_thread_id": sender,
                           "receiver_thread_ids": list(receivers)})
    conflicts = {child: sorted(senders) for child, senders in owners.items()
                 if len(senders) > 1}
    route_checks = [{"name": "formal_ownership",
                     "status": "fail" if conflicts else "pass",
                     "detail": conflicts}]
    if conflicts:
        route_status, route_classification = "invalid", "INVALID_TEST_EXECUTION"
    elif not relations:
        route_checks.append({"name": "formal_spawn_relation_surface",
                             "status": "fail"})
        route_status, route_classification = "blocked", "BLOCKED_OBSERVABILITY"
    else:
        route_checks.append({"name": "no_nested_formal_spawn",
                             "status": "fail" if nested else "pass",
                             "detail": nested})
        if nested:
            route_status, route_classification = "fail", "FAIL_PRODUCT"
        else:
            count_pass = len(direct_ids) >= 2
            route_checks.extend([
                {"name": "root_direct_spawn_child_count",
                 "status": "pass" if count_pass else "fail",
                 "detail": {"observed": len(direct_ids), "required": 2}},
                {"name": "pre_zero_write_snapshot", "status": "pass"},
                {"name": "post_matches_current", "status": "pass"},
            ])
            route_status = "pass" if count_pass else "fail"
            route_classification = "PASS" if count_pass else "FAIL_PRODUCT"
    surfaces = {
        "install": {"status": "pass", "checks": [
            {"name": "locked_target_commit", "status": "pass"},
            {"name": "source_install_projection", "status": "pass"},
            {"name": "request_config_matches_consensus", "status": "pass"}]},
        "fixture": {"status": "pass", "manual_patch": "no", "checks": [
            {"name": "no_manual_patch", "status": "pass"},
            {"name": "initial_input_digest", "status": "pass"},
            {"name": "forbidden_outputs_absent", "status": "pass"}]},
        "routing": {"status": route_status,
                    "classification": route_classification,
                    "root_thread_id": ROOT,
                    "root_direct_spawn_child_ids": sorted(direct_ids),
                    "nested_formal_spawns": nested,
                    "checks": route_checks},
        "pre": {"status": "pass", "checks": [
            {"name": "pre_zero_write_snapshot", "status": "pass"}]},
        "post": {"status": "pass", "checks": [
            {"name": "post_matches_current", "status": "pass"}]},
        "storage": {"status": "ok", "process_id": "case-process-1",
                    "rollout_dir": "/tmp/issue66/case-1",
                    "config_path": "/tmp/issue66/case-1/config.toml",
                    "database_path": "/tmp/issue66/case-1/state.sqlite",
                    "log_path": "/tmp/issue66/case-1/server.log",
                    "checks": [
                        {"name": "process_is_test_only", "status": "pass"},
                        {"name": "config_is_test_only", "status": "pass"},
                        {"name": "database_is_test_only", "status": "pass"},
                        {"name": "logs_are_test_only", "status": "pass"},
                        {"name": "database_path_resolved", "status": "pass"},
                        {"name": "run_records_match_case", "status": "pass"},
                        {"name": "read_only", "status": "pass"}]},
    }
    for evidence in surfaces.values():
        evidence["evidence_set_id"] = "issue66-fixture-run-1"
    return surfaces


_SAMPLE_SCHEMA = "issue66.sample-ledger.v1"
_SAMPLE_LEDGER_ENV = "ISSUE66_SAMPLE_LEDGER"
_R19_SAMPLE_FAMILIES = {
    "three_completion_paths", "source_handoff_values", "formal_relations",
    "raw_messages", "file_permissions", "order_and_stops",
    "refusal_side_effects", "read_reuse", "evidence_channels",
}
_ACTIVE_SAMPLE_TEST = None
_INITIALIZED_LEDGER_PATHS = set()
_TEST_SOURCE = Path(__file__).resolve()
_TEST_AST = ast.parse(_TEST_SOURCE.read_text(encoding="utf-8"))
_ASSERTION_CALLS = [node for node in ast.walk(_TEST_AST)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"assertEqual", "assertNotEqual"}
                    and len(node.args) >= 2]

_CLASS_FAMILY = {
    "LegalCompletionTests": ["three_completion_paths"],
    "AttributionTests": ["formal_relations"],
    "FoldedEvidenceTests": ["evidence_channels"],
    "CredentialValueTests": ["source_handoff_values"],
    "RawOriginalTests": ["raw_messages"],
    "WriteScopeTests": ["file_permissions"],
    "OrderAndStopTests": ["order_and_stops"],
    "EvidenceChannelTests": ["evidence_channels"],
}
_TEST_FAMILY_OVERRIDES = {
    "test_legal_whitespace_message_passes":
        ["three_completion_paths", "raw_messages"],
    "test_machine_failure_prefix_blocks":
        ["formal_relations", "order_and_stops"],
    "test_machine_failure_prefix_does_not_hide_prior_product_failure":
        ["formal_relations", "order_and_stops"],
    "test_routing_ownership_conflict_is_folded_as_invalid":
        ["formal_relations", "evidence_channels"],
    "test_routing_check_conflict_cannot_be_hidden_by_pass_summary":
        ["formal_relations", "evidence_channels"],
    "test_handoff_value_drift_fails": ["source_handoff_values"],
    "test_prepare_return_for_another_round_fails":
        ["source_handoff_values"],
    "test_prepare_return_missing_output_path_is_invalid":
        ["source_handoff_values", "evidence_channels"],
    "test_prepare_professor_source_drift_fails":
        ["source_handoff_values"],
    "test_save_return_missing_round_is_invalid":
        ["source_handoff_values", "evidence_channels"],
    "test_record_return_state_path_drift_fails":
        ["source_handoff_values"],
    "test_record_return_missing_needs_correction_is_invalid":
        ["source_handoff_values", "evidence_channels"],
    "test_non_monotonic_event_seq_invalidates_validator_evidence":
        ["raw_messages", "evidence_channels"],
    "test_mismatched_call_id_cannot_bind_validator_command_completion":
        ["raw_messages", "evidence_channels"],
}


def _json_copy(value):
    """Return the exact JSON-compatible value used by a test assertion."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=repr))


def _sample_families(test_id):
    class_name, method_name = test_id.rsplit(".", 2)[-2:]
    families = list(_TEST_FAMILY_OVERRIDES.get(
        method_name, _CLASS_FAMILY.get(class_name, [])))
    unknown = set(families) - _R19_SAMPLE_FAMILIES
    if unknown:
        raise AssertionError(f"unknown R19 sample families: {sorted(unknown)}")
    return families or ["unclassified"]


def _call_source(frame, name):
    line = frame.f_lineno
    matches = [node for node in _ASSERTION_CALLS
               if node.func.attr == name
               and node.lineno <= line <= getattr(node, "end_lineno", node.lineno)]
    if not matches:
        return None
    node = min(matches, key=lambda item: item.end_lineno - item.lineno)
    return node


def _verdict_aliases(test_id):
    class_name, method_name = test_id.rsplit(".", 2)[-2:]
    test_class = next((node for node in _TEST_AST.body
                       if isinstance(node, ast.ClassDef)
                       and node.name == class_name), None)
    method = next((node for node in test_class.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name == method_name), None) if test_class else None
    aliases = set()
    if method is None:
        return aliases
    changed = True
    while changed:
        changed = False
        for node in ast.walk(method):
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign):
                targets, value = [node.target], node.value
            else:
                continue
            names = {child.id for child in ast.walk(value)
                     if isinstance(child, ast.Name)}
            is_alias = names.intersection(aliases | {"verdict"})
            is_facts_result = (isinstance(value, ast.Call)
                               and isinstance(value.func, ast.Name)
                               and value.func.id == "facts"
                               and "verdict" in names)
            if not (is_alias or is_facts_result):
                continue
            for target in targets:
                for child in ast.walk(target):
                    if isinstance(child, ast.Name) and child.id not in aliases:
                        aliases.add(child.id)
                        changed = True
    return aliases


def _expression_is_verdict_related(node, aliases):
    return any((isinstance(child, ast.Name)
                and child.id in aliases | {"verdict"})
               or (isinstance(child, ast.Call)
                   and isinstance(child.func, ast.Name)
                   and child.func.id == "facts")
               for child in ast.walk(node))


def _assertion_capture(test_case, method_name, actual, expected):
    if not test_case._sample_records:
        return
    frame = inspect.currentframe().f_back.f_back
    node = _call_source(frame, method_name)
    if node is None:
        return
    subject = ast.unparse(node.args[0])
    expected_expression = ast.unparse(node.args[1])
    entry = {
        "operator": "equals" if method_name == "assertEqual" else "not_equals",
        "subject": subject,
        "expected_expression": expected_expression,
        "expected_value": _json_copy(expected),
        "observed_value": _json_copy(actual),
        "source": {"file": _TEST_SOURCE.name, "line": node.lineno},
        "verdict_related": _expression_is_verdict_related(
            node.args[0], test_case._verdict_aliases),
    }
    record = test_case._sample_records[-1]
    record["expected"]["assertions"].append(entry)
    if not entry["verdict_related"]:
        return
    if record["expected"]["classification_status"] != "asserted":
        record["expected"]["status"] = "partial"
    if (isinstance(node.args[0], ast.Subscript)
            and isinstance(node.args[0].value, ast.Name)
            and node.args[0].value.id == "verdict"
            and isinstance(node.args[0].slice, ast.Constant)
            and node.args[0].slice.value == "classification"
            and method_name == "assertEqual"):
        record["expected"]["classification"] = _json_copy(expected)
        record["expected"]["classification_status"] = "asserted"
        record["expected"]["status"] = "available"
    elif (isinstance(node.args[0], ast.Subscript)
          and ((isinstance(node.args[0].value, ast.Name)
                and node.args[0].value.id in test_case._verdict_aliases)
               or (isinstance(node.args[0].value, ast.Call)
                   and isinstance(node.args[0].value.func, ast.Name)
                   and node.args[0].value.func.id == "facts"
                   and any(isinstance(child, ast.Name)
                           and child.id == "verdict"
                           for child in ast.walk(node.args[0].value))))
          and isinstance(node.args[0].slice, ast.Constant)
          and isinstance(node.args[0].slice.value, str)
          and node.args[0].slice.value.startswith("F-")
          ):
        fact_id = node.args[0].slice.value
        if method_name == "assertEqual":
            record["expected"].setdefault("facts", {})[fact_id] = \
                _json_copy(expected)
            record["expected"]["facts_status"] = "asserted"
        else:
            record["expected"].setdefault("fact_constraints", []).append({
                "fact": fact_id,
                "operator": entry["operator"],
                "value": _json_copy(expected),
            })
            record["expected"]["facts_status"] = "partial"


def _event_references(events):
    refs = []
    for position, event in enumerate(events, start=1):
        message = event.get("message", {})
        if not isinstance(message, dict):
            continue
        params = message.get("params", {})
        item = params.get("item", {}) if isinstance(params, dict) else {}
        if not isinstance(item, dict):
            item = {}
        if not item and message.get("method") != "rawResponseItem/completed":
            continue
        refs.append({
            "array_index": position - 1,
            "seq": event.get("seq", position),
            "method": message.get("method"),
            "thread_id": params.get("threadId") if isinstance(params, dict) else None,
            "turn_id": params.get("turnId") if isinstance(params, dict) else None,
            "item_type": item.get("type"),
            "item_id": item.get("id"),
            "call_id": item.get("call_id"),
        })
    return refs


def _append_sample_records(records):
    output = os.environ.get(_SAMPLE_LEDGER_ENV)
    if not output or not records:
        return
    path = Path(output).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path_key = str(path.resolve())
    if path_key not in _INITIALIZED_LEDGER_PATHS:
        path.write_text("", encoding="utf-8")
        _INITIALIZED_LEDGER_PATHS.add(path_key)
    with path.open("a", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False,
                                    sort_keys=True) + "\n")
        stream.flush()


def _record_judge_call(fx, verdict, response, callsite, fixture_inputs):
    test_case = _ACTIVE_SAMPLE_TEST
    if test_case is None:
        return
    test_case._sample_call_index += 1
    ordinal = test_case._sample_call_index
    test_id = test_case.id()
    events = response["output"]["app_server_events"]
    canonical_evidence = json.dumps(
        fixture_inputs, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), default=repr).encode("utf-8")
    record = {
        "schema_version": _SAMPLE_SCHEMA,
        "sample_id": f"{test_id}#run-{ordinal}",
        "test_id": test_id,
        "sample_family": _sample_families(test_id),
        "expected": {"status": "unavailable",
                     "classification_status": "not_asserted",
                     "facts_status": "not_asserted", "assertions": []},
        "actual": {"outcome": verdict.get("classification"),
                   "result": verdict},
        "judge_sha256": hashlib.sha256(
            Path(judge.__file__).resolve().read_bytes()).hexdigest(),
        "evidence_digest": hashlib.sha256(canonical_evidence).hexdigest(),
        "evidence_ref": {
            "kind": "synthetic_fixture",
            "source_file": _TEST_SOURCE.name,
            "run_call_line": callsite["line"],
            "run_ordinal": ordinal,
            "event_count": len(events),
            "event_refs": _event_references(events),
        },
    }
    test_case._sample_records.append(record)


_DEFAULT_PROGRAM_ROOT = object()


def run(fx: Fixture, *, state="default", delegation_override=None,
        adapter_override=None, surface_evidence=None,
        delegation_state="confirmed", program_root=_DEFAULT_PROGRAM_ROOT):
    callsite_frame = inspect.currentframe().f_back
    callsite = {"line": callsite_frame.f_lineno,
                "method": callsite_frame.f_code.co_name}
    tmp = Path(tempfile.mkdtemp())
    if program_root is _DEFAULT_PROGRAM_ROOT:
        program_root = tmp / "program-root"
    if program_root is not None:
        program_root = Path(program_root)
        program_root.mkdir(parents=True, exist_ok=True)
    response_path = tmp / "response.json"
    adapter_path = tmp / "adapter.json"
    state_path = tmp / STATE_NAME
    output_path = tmp / "verdict.json"
    surface_paths = {}
    surface_flags = {"install": "--install-evidence",
                     "fixture": "--fixture-evidence",
                     "routing": "--routing-evidence",
                     "pre": "--pre-snapshot",
                     "post": "--post-snapshot",
                     "storage": "--storage-evidence"}
    response_path.write_text(json.dumps(fx.response(), ensure_ascii=False),
                             encoding="utf-8")
    adapter = fx.adapter()
    if adapter_override is not None:
        adapter = adapter_override
    if delegation_override is not None:
        delegation_children, relations = delegation_override
        adapter["delegation"]["child_thread_ids"] = list(delegation_children)
        adapter["delegation"]["formal_child_count"] = len(delegation_children)
        adapter["dispatch"]["thread_relations"] = relations
    adapter_path.write_text(json.dumps(adapter, ensure_ascii=False),
                            encoding="utf-8")
    surface_evidence = (valid_surfaces(fx) if surface_evidence is None
                        else surface_evidence)
    for name, flag in surface_flags.items():
        if name in surface_evidence:
            surface_path = tmp / f"{name}.json"
            surface_path.write_text(
                json.dumps(surface_evidence[name], ensure_ascii=False),
                encoding="utf-8")
            surface_paths[flag] = str(surface_path)
    if isinstance(state, dict) or state is None:
        if state is not None:
            state_path.write_text(json.dumps(state, ensure_ascii=False),
                                  encoding="utf-8")
    response = fx.response()
    state_input = (state if isinstance(state, dict) or state is None else
                   {"argument": state, "candidate_state_file_written": False})
    fixture_inputs = {"response": response, "adapter": adapter,
                      "candidate_state": state_input,
                      "surface_evidence": surface_evidence,
                      "program_root": str(program_root) if program_root else None}
    response_path.write_text(json.dumps(response, ensure_ascii=False),
                             encoding="utf-8")
    argv = ["--eval-response", str(response_path),
            "--adapter-output", str(adapter_path),
            "--candidate-state", str(state_path),
            "--output", str(output_path)]
    if program_root is not None:
        argv.extend(["--program-root", str(program_root)])
    for flag, path in surface_paths.items():
        argv.extend([flag, path])
    judge.main(argv)
    verdict = json.loads(output_path.read_text(encoding="utf-8"))
    _record_judge_call(fx, verdict, response, callsite, fixture_inputs)
    return verdict


def facts(verdict):
    return {row["fact"]: row["verdict"] for row in verdict["facts"]}


class RuntimeJudgeTestCase(unittest.TestCase):
    def setUp(self):
        global _ACTIVE_SAMPLE_TEST
        super().setUp()
        self._sample_records = []
        self._sample_call_index = 0
        self._verdict_aliases = _verdict_aliases(self.id())
        _ACTIVE_SAMPLE_TEST = self

    def tearDown(self):
        global _ACTIVE_SAMPLE_TEST
        try:
            _append_sample_records(self._sample_records)
        finally:
            if _ACTIVE_SAMPLE_TEST is self:
                _ACTIVE_SAMPLE_TEST = None
            super().tearDown()

    def assertEqual(self, first, second, msg=None):
        _assertion_capture(self, "assertEqual", first, second)
        return super().assertEqual(first, second, msg)

    def assertNotEqual(self, first, second, msg=None):
        _assertion_capture(self, "assertNotEqual", first, second)
        return super().assertNotEqual(first, second, msg)


class LegalCompletionTests(RuntimeJudgeTestCase):
    def test_one_round_pass(self):
        fx = Fixture()
        legal_two_child(fx)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)
        self.assertEqual([agent for _call_id, agent, _thread in fx.spawn_specs],
                         [judge.GENERATOR_AGENT, judge.VALIDATOR_AGENT])
        self.assertEqual(len(fx.relations), 2)
        for relation in fx.relations:
            self.assertEqual(relation["tool"], "spawnAgent")
            self.assertIsInstance(relation["call_id"], str)
            self.assertEqual(relation["sender_thread_id"], ROOT)
            self.assertEqual(len(relation["receiver_thread_ids"]), 1)
        self.assertEqual(facts(verdict)["F-attribution"], "pass")
        self.assertEqual(facts(verdict)["F-routing-verifier"], "pass")

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


class AttributionTests(RuntimeJudgeTestCase):
    def test_incomplete_run_without_relations_does_not_prove_zero_delegation(self):
        fx = Fixture()
        fx.include_turn_completed = False
        verdict = run(fx, state=None)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-attribution"], "gap")

    def test_incomplete_run_with_relation_but_no_child_completion_is_a_gap(self):
        fx = Fixture()
        fx.spawn(judge.GENERATOR_AGENT, G1)
        fx.include_turn_completed = False
        verdict = run(fx, state=None)
        observed = facts(verdict)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(observed["F-attribution"], "gap", verdict)
        self.assertEqual(observed["F-routing-verifier"], "gap", verdict)

    def test_zero_real_delegation_is_a_product_failure(self):
        fx = Fixture()
        fx.root_exec("cat plan", '{"status": "ok"}')
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-attribution"], "fail")

    def test_machine_failure_prefix_blocks(self):
        fx = Fixture()
        fx.spawn(judge.GENERATOR_AGENT, G1)
        fx.generator_round(G1)
        fx.spawn(judge.VALIDATOR_AGENT, None, machine_fail=True)
        verdict = run(fx, state=None,
                      delegation_override=([G1], fx.relations),
                      delegation_state="unconfirmed")
        self.assertEqual(verdict["classification"], "BLOCKED", verdict)

    def test_unrecognized_failure_text_does_not_hide_zero_child_failure(self):
        fx = Fixture()
        fx.spawn(judge.GENERATOR_AGENT)
        call_id = fx.spawn_specs[-1][0]
        fx.events.append({"message": {"method": "rawResponseItem/completed",
            "params": {"threadId": ROOT, "item": {
                "type": "function_call_output", "call_id": call_id,
                "output": [{"type": "input_text",
                            "text": "validation command failed with an error"}]}}}})

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-attribution"], "fail", verdict)

    def test_machine_failure_prefix_does_not_hide_prior_product_failure(self):
        fx = Fixture()
        legal_two_child_spine(fx)
        for event in fx.events:
            message = event.get("message", {})
            params = message.get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == ROOT \
                    and message.get("method") in {
                        "item/started", "item/completed"} \
                    and item.get("type") == "commandExecution" \
                    and "stage3-record-validation" in item.get("command", ""):
                item["command"] = item["command"].replace(
                    HANDOFF_FILE, "/tmp/fixture/wrong-handoff.json")
        fx.spawn(judge.GENERATOR_AGENT, None, machine_fail=True)

        verdict = run(fx, state=None)

        self.assertEqual(facts(verdict)["F-attribution"],
                         "machine_failure_prefix", verdict)
        self.assertEqual(facts(verdict)["F-handoff-chain"], "fail", verdict)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_nested_foreign_relation_is_product_failure(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.relations.append({"call_id": "call-foreign",
                             "sender_thread_id": V1,
                             "receiver_thread_ids": ["nested-thread"],
                             "status": "completed",
                             "tool": "spawnAgent"})
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-attribution"], "fail")

    def test_child_without_formal_relation_is_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.relations = fx.relations[:-1]     # V1 loses its relation
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)

    def test_named_root_call_with_confirmed_zero_children_fails(self):
        fx = Fixture()
        fx.spawn(judge.GENERATOR_AGENT)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-attribution"], "fail")
        self.assertEqual(facts(verdict)["F-routing-verifier"], "gap")

    def test_named_root_call_with_missing_adapter_evidence_is_invalid(self):
        fx = Fixture()
        fx.spawn(judge.GENERATOR_AGENT)
        verdict = run(fx, state=PASS_STATE, adapter_override={})
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        attribution = next(row for row in verdict["facts"]
                          if row["fact"] == "F-attribution")
        self.assertEqual(attribution["verdict"], "invalid")
        self.assertNotEqual(facts(verdict)["F-attribution"], "fail")

    def test_extra_off_root_formal_relation_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.relations.append({"call_id": "call-off-root",
                             "sender_thread_id": "foreign-root",
                             "receiver_thread_ids": ["foreign-child"],
                             "status": "completed", "tool": "spawnAgent"})
        fx.children.append("foreign-child")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-attribution"], "fail")
        self.assertEqual(facts(verdict)["F-routing-verifier"], "fail")

    def test_conflicting_formal_owners_for_child_are_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.relations.append({"call_id": "call-conflict",
                             "sender_thread_id": "foreign-root",
                             "receiver_thread_ids": [G1],
                             "status": "completed", "tool": "spawnAgent"})
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        attribution = next(row for row in verdict["facts"]
                          if row["fact"] == "F-attribution")
        self.assertEqual(attribution["verdict"], "invalid")
        self.assertTrue(any("formal ownership conflict" in item
                            for item in attribution["evidence"]))
        self.assertEqual(facts(verdict)["F-routing-verifier"], "invalid")

    def test_routing_ownership_conflict_is_folded_as_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        surfaces = valid_surfaces(fx)
        surfaces["routing"]["classification"] = "INVALID_TEST_EXECUTION"
        surfaces["routing"]["status"] = "invalid"
        ownership = next(row for row in surfaces["routing"]["checks"]
                         if row["name"] == "formal_ownership")
        ownership["status"] = "fail"
        ownership["detail"] = {G1: [ROOT, "foreign-root"]}
        verdict = run(fx, state=PASS_STATE, surface_evidence=surfaces)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-attribution"], "pass")
        self.assertEqual(facts(verdict)["F-routing-verifier"], "invalid")


class FoldedEvidenceTests(RuntimeJudgeTestCase):
    def test_routing_check_conflict_cannot_be_hidden_by_pass_summary(self):
        fx = Fixture()
        legal_two_child(fx)
        surfaces = valid_surfaces(fx)
        surfaces["routing"]["checks"][1]["status"] = "fail"
        verdict = run(fx, state=PASS_STATE, surface_evidence=surfaces)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-routing-verifier"], "invalid")

    def test_install_check_status_is_folded_into_unique_verdict(self):
        fx = Fixture()
        legal_two_child(fx)
        surfaces = valid_surfaces(fx)
        surfaces["install"]["checks"][0]["status"] = "fail"
        verdict = run(fx, state=PASS_STATE, surface_evidence=surfaces)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-install"], "invalid")

    def test_required_install_sample_storage_and_snapshot_evidence_cannot_be_omitted(self):
        expected_facts = {
            "install": "F-install", "fixture": "F-fixture",
            "storage": "F-storage-ownership", "pre": "F-pre-snapshot",
            "post": "F-post-snapshot", "routing": "F-routing-verifier",
        }
        for missing, fact in expected_facts.items():
            with self.subTest(missing=missing):
                fx = Fixture()
                legal_two_child(fx)
                surfaces = valid_surfaces(fx)
                surfaces.pop(missing)
                verdict = run(fx, state=PASS_STATE,
                              surface_evidence=surfaces)
                self.assertEqual(verdict["classification"],
                                 "INVALID_TEST_EXECUTION", verdict)
                self.assertEqual(facts(verdict)[fact], "gap", verdict)

    def test_sample_provenance_failure_invalidates_the_run(self):
        fx = Fixture()
        legal_two_child(fx)
        surfaces = valid_surfaces(fx)
        next(check for check in surfaces["fixture"]["checks"]
             if check["name"] == "initial_input_digest")["status"] = "fail"
        verdict = run(fx, state=PASS_STATE, surface_evidence=surfaces)
        self.assertEqual(verdict["classification"], "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-fixture"], "invalid", verdict)

    def test_storage_status_without_ownership_checks_is_a_gap(self):
        fx = Fixture()
        legal_two_child(fx)
        surfaces = valid_surfaces(fx)
        surfaces["storage"].pop("checks")
        verdict = run(fx, state=PASS_STATE, surface_evidence=surfaces)
        self.assertEqual(verdict["classification"], "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-storage-ownership"], "gap", verdict)

    def test_failed_post_snapshot_cannot_be_hidden_by_routing_pass(self):
        fx = Fixture()
        legal_two_child(fx)
        surfaces = valid_surfaces(fx)
        surfaces["post"]["checks"][0]["status"] = "fail"
        verdict = run(fx, state=PASS_STATE, surface_evidence=surfaces)
        self.assertEqual(verdict["classification"], "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-post-snapshot"], "invalid", verdict)

    def test_mixed_evidence_set_ids_are_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        surfaces = valid_surfaces(fx)
        surfaces["storage"]["evidence_set_id"] = "another-run"
        verdict = run(fx, state=PASS_STATE, surface_evidence=surfaces)
        self.assertEqual(verdict["classification"], "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-evidence-version"], "invalid", verdict)

    def test_missing_evidence_set_id_is_not_a_pass(self):
        fx = Fixture()
        legal_two_child(fx)
        surfaces = valid_surfaces(fx)
        surfaces["pre"].pop("evidence_set_id")
        verdict = run(fx, state=PASS_STATE, surface_evidence=surfaces)
        self.assertEqual(verdict["classification"], "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-evidence-version"], "gap", verdict)

    def test_program_root_is_required_to_prove_stage4_outputs_absent(self):
        fx = Fixture()
        legal_two_child(fx)
        verdict = run(fx, state=PASS_STATE, program_root=None)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-stage4-absence"], "gap", verdict)

    def test_stage4_artifact_under_program_root_fails_absence_check(self):
        fx = Fixture()
        legal_two_child(fx)
        with tempfile.TemporaryDirectory() as program_root:
            artifact = Path(program_root) / "nested" / "邮件输入.json"
            artifact.parent.mkdir()
            artifact.write_text("{}", encoding="utf-8")
            verdict = run(fx, state=PASS_STATE, program_root=program_root)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-stage4-absence"], "fail", verdict)


class CredentialValueTests(RuntimeJudgeTestCase):
    def test_legal_capture_without_optional_business_inputs_passes(self):
        fx = Fixture()
        legal_two_child(fx)
        capture = next(event["message"]["params"]["item"]["command"]
                       for event in fx.events
                       if event.get("message", {}).get("method") == "item/started"
                       and event.get("message", {}).get("params", {}).get("threadId") == G1
                       and "--capture-invocation" in event.get("message", {}).get(
                           "params", {}).get("item", {}).get("command", ""))
        for optional in ("--profile", "--selection", "--skip-direction-ids",
                         "--cross-direction-groups", "--direction-id"):
            self.assertNotIn(optional, capture)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "pass")

    def test_consumption_uses_actual_capture_return_path_and_digest(self):
        fx = Fixture()
        fx.profile_path = "/tmp/fixture/profile.md"
        fx.profile_fingerprint = "a" * 64
        legal_two_child(fx)
        returned_file = "/tmp/fixture/returned-credential.json"
        returned_sha = hashlib.sha256(b"actual returned credential").hexdigest()
        for event in fx.events:
            message = event.get("message", {})
            params = message.get("params", {})
            item = params.get("item", {})
            if item.get("type") != "commandExecution":
                continue
            command = item.get("command", "")
            if params.get("threadId") == G1 and "--capture-invocation" in command \
                    and message.get("method") == "item/completed":
                output, state = judge.Judge._json_from_output(item.get("aggregatedOutput"))
                self.assertEqual(state, "ok")
                output["invocation_file"] = returned_file
                output["invocation_sha256"] = returned_sha
                item["aggregatedOutput"] = json.dumps(output)
            if CREDENTIAL_FILE in command:
                item["command"] = command.replace(CREDENTIAL_FILE, returned_file)
            if CREDENTIAL_SHA in command:
                item["command"] = item["command"].replace(CREDENTIAL_SHA, returned_sha)
        state = {**PASS_STATE, "profile_fingerprint": fx.profile_fingerprint}
        verdict = run(fx, state=state)
        self.assertEqual(verdict["classification"], "PASS", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "pass")

    def test_committed_profile_fingerprint_must_match_capture(self):
        fx = Fixture()
        fx.profile_path = "/tmp/fixture/profile.md"
        fx.profile_fingerprint = "a" * 64
        legal_two_child(fx)

        state = {**PASS_STATE, "profile_fingerprint": "b" * 64}
        verdict = run(fx, state=state)

        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")

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
                    f"--invocation-sha256 {CREDENTIAL_SHA}",
                    f"--invocation-sha256 {'f' * 64}")
        verdict = run(fx, state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")

    def test_credential_file_path_drift_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            params = event.get("message", {}).get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == G1 and item.get("type") == "commandExecution" \
                    and "stage3-plan" in item.get("command", "") \
                    and "--invocation-file" in item.get("command", ""):
                item["command"] = item["command"].replace(
                    CREDENTIAL_FILE, "/tmp/fixture/wrong-credential.json")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")

    def test_complete_observation_without_capture_fails(self):
        fx = Fixture()
        fx.spawn(judge.GENERATOR_AGENT, G1)
        fx.complete_child(G1)
        verdict = run(fx, state=None)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")

    def test_incomplete_observation_without_capture_is_a_gap(self):
        fx = Fixture()
        fx.spawn(judge.GENERATOR_AGENT, G1)
        fx.include_turn_completed = False
        verdict = run(fx, state=None)
        self.assertEqual(facts(verdict)["F-credential-chain"], "gap")

    def test_source_metadata_drift_fails(self):
        fx = Fixture()
        legal_four_child(fx, second_fails=True)
        for event in fx.events:
            message = event.get("message", {})
            params = message.get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == G2 and item.get("type") == "commandExecution" \
                    and message.get("method") == "item/completed" \
                    and "--validation-file" in item.get("command", ""):
                output, state = judge.Judge._json_from_output(item.get("aggregatedOutput"))
                self.assertEqual(state, "ok")
                output["professor_dir"] = "/tmp/other-professor"
                item["aggregatedOutput"] = json.dumps(output)
        verdict = run(fx, state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")

    def test_credential_return_bound_to_another_professor_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            message = event.get("message", {})
            params = message.get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == G1 and item.get("type") == "commandExecution" \
                    and message.get("method") == "item/completed" \
                    and "--capture-invocation" in item.get("command", ""):
                output, state = judge.Judge._json_from_output(item.get("aggregatedOutput"))
                self.assertEqual(state, "ok")
                output["professor"] = "Other Professor"
                item["aggregatedOutput"] = json.dumps(output)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")

    def test_missing_capture_value_is_a_gap(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            message = event.get("message", {})
            params = message.get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == G1 and item.get("type") == "commandExecution" \
                    and message.get("method") == "item/completed" \
                    and "--capture-invocation" in item.get("command", ""):
                output, state = judge.Judge._json_from_output(item.get("aggregatedOutput"))
                self.assertEqual(state, "ok")
                output.pop("invocation_file")
                item["aggregatedOutput"] = json.dumps(output)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(facts(verdict)["F-credential-chain"], "gap")

    def test_missing_first_commit_fails(self):
        fx = Fixture()
        fx.prepare(1)
        fx.spawn(judge.GENERATOR_AGENT, G1)
        fx.generator_round(G1, with_finalize=False)
        fx.spawn(judge.VALIDATOR_AGENT, V1)
        fx.validator_round(V1)
        fx.save(sha=msg_sha(), round_no=2)
        fx.record(1, sha=msg_sha())
        fx.rebuild()
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")

    def test_finalize_in_second_child_does_not_replace_first_finalize(self):
        fx = Fixture()
        legal_four_child(fx, second_fails=True)
        fx.events = [event for event in fx.events if not (
            event.get("message", {}).get("params", {}).get("threadId") == G1
            and event.get("message", {}).get("params", {}).get("item", {}).get("type")
            == "commandExecution"
            and "stage3-finalize" in event["message"]["params"]["item"].get("command", ""))]
        verdict = run(fx, state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")

    def test_unsuccessful_capture_return_cannot_bind_credentials(self):
        fx = Fixture()
        legal_two_child(fx)
        capture = next(event for event in fx.events
                       if event.get("message", {}).get("params", {}).get("threadId") == G1
                       and event.get("message", {}).get("params", {}).get("item", {}).get("type")
                       == "commandExecution"
                       and "--capture-invocation" in event["message"]["params"]["item"].get("command", ""))
        capture = next(event for event in fx.events
                       if event.get("message", {}).get("method") == "item/completed"
                       and event.get("message", {}).get("params", {}).get("threadId") == G1
                       and event.get("message", {}).get("params", {}).get("item", {}).get("type")
                       == "commandExecution"
                       and "--capture-invocation" in event["message"]["params"]["item"].get("command", ""))
        item = capture["message"]["params"]["item"]
        item["exitCode"] = 1
        item["status"] = "failed"
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-credential-chain"], "fail")
        self.assertEqual(facts(verdict)["F-stop-order"], "fail")

    def test_failed_save_return_cannot_be_followed_by_record_as_pass(self):
        fx = Fixture()
        legal_two_child(fx)
        save = next(event for event in fx.events
                    if event.get("message", {}).get("method") == "item/completed"
                    and event.get("message", {}).get("params", {}).get("threadId") == ROOT
                    and event.get("message", {}).get("params", {}).get("item", {}).get("type")
                    == "commandExecution"
                    and "stage3-save-validation" in event["message"]["params"]["item"].get("command", ""))
        save["message"]["params"]["item"]["exitCode"] = 1
        save["message"]["params"]["item"]["status"] = "failed"
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-handoff-chain"], "fail")
        self.assertEqual(facts(verdict)["F-stop-order"], "fail")

    def test_failed_prepare_write_and_record_stop_dependent_actions(self):
        cases = (
            (ROOT, "stage3-prepare-validation"),
            (V1, "python3 -c"),
            (ROOT, "stage3-record-validation"),
        )
        for thread, command_part in cases:
            with self.subTest(thread=thread, command=command_part):
                fx = Fixture()
                legal_two_child(fx)
                target = next(
                    event for event in fx.events
                    if event.get("message", {}).get("method") == "item/completed"
                    and event.get("message", {}).get("params", {}).get("threadId") == thread
                    and event.get("message", {}).get("params", {}).get("item", {}).get("type")
                    == "commandExecution"
                    and command_part in event["message"]["params"]["item"].get("command", ""))
                target["message"]["params"]["item"]["exitCode"] = 1
                target["message"]["params"]["item"]["status"] = "failed"

                verdict = run(fx, state=PASS_STATE)

                self.assertEqual(verdict["classification"], "FAIL", verdict)
                self.assertEqual(facts(verdict)["F-stop-order"], "fail")


class RawOriginalTests(RuntimeJudgeTestCase):
    @staticmethod
    def prefix_root_stage3_command(fx, subcommand, prefix):
        found = 0
        for event in fx.events:
            params = event.get("message", {}).get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == ROOT \
                    and item.get("type") == "commandExecution" \
                    and subcommand in item.get("command", ""):
                item["command"] = prefix + " && " + item["command"]
                found += 1
        return found

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

    def test_composite_save_command_cannot_hide_a_root_rewrite(self):
        fx = Fixture()
        legal_two_child(fx)
        source = f"open({OUTPUT_FILE!r}, 'wb').write(b'root-rebuilt')"
        prefix = "python3 -c " + shlex.quote(source)
        self.assertEqual(self.prefix_root_stage3_command(
            fx, "stage3-save-validation", prefix), 2)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "fail", verdict)

    def test_root_rewrite_before_validator_dispatch_is_detected(self):
        fx = Fixture()
        legal_two_child(fx)
        source = f"open({OUTPUT_FILE!r}, 'xb').write(b'root-rebuilt')"
        prefix = "python3 -c " + shlex.quote(source)
        self.assertEqual(self.prefix_root_stage3_command(
            fx, "stage3-prepare-validation", prefix), 2)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "fail", verdict)

    def test_unknown_root_operation_leaves_raw_integrity_unproven(self):
        fx = Fixture()
        legal_two_child(fx)
        prefix = "unknown-root-tool --maybe-write"
        self.assertEqual(self.prefix_root_stage3_command(
            fx, "stage3-record-validation", prefix), 2)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "gap", verdict)

    def test_second_business_message_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.child_message(V1, "第二条业务消息")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_complete_run_with_no_validator_production_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            params = event["message"]["params"]
            item = params["item"]
            if item.get("type") == "commandExecution" \
                    and params.get("threadId") == V1:
                item["command"] = f"cat /tmp/fixture/{MD_NAME}"
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "fail", verdict)

    def test_missing_run_completion_leaves_absent_production_as_a_gap(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            params = event["message"]["params"]
            item = params["item"]
            if item.get("type") == "commandExecution" \
                    and params.get("threadId") == V1:
                item["command"] = f"cat /tmp/fixture/{MD_NAME}"
        fx.include_turn_completed = False
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(facts(verdict)["F-raw-original"], "gap", verdict)
        self.assertEqual(verdict["classification"], "INVALID_TEST_EXECUTION", verdict)

    def test_raw_text_blocks_are_concatenated_as_original_utf8_bytes(self):
        blocks = [{"type": "output_text", "text": "  第一块\n"},
                  {"type": "output_text", "text": "第二块  \n"}]
        raw = judge.final_message_bytes({"content": blocks})
        self.assertEqual(raw, "  第一块\n第二块  \n".encode("utf-8"))

    def test_file_change_event_proves_production_without_command_actions(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            params = event.get("message", {}).get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == V1 and item.get("type") == "commandExecution":
                item["commandActions"] = []
        fx.events = [event for event in fx.events if not (
            event.get("message", {}).get("params", {}).get("threadId") == V1
            and (event.get("message", {}).get("params", {}).get("item", {}).get("type")
                 == "fileChange" or (
                     event.get("message", {}).get("params", {}).get("item", {}).get("type")
                     == "commandExecution" and
                     "python3 -c" in event["message"]["params"]["item"].get("command", ""))))]
        add_validator_file_change(fx, OUTPUT_FILE, content=msg_text())
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)

    def test_file_change_without_contents_cannot_prove_raw_production(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.events = [event for event in fx.events if not (
            event.get("message", {}).get("params", {}).get("threadId") == V1
            and event.get("message", {}).get("params", {}).get("item", {}).get("type")
            == "commandExecution"
            and "python3 -c" in event["message"]["params"]["item"].get("command", ""))]
        add_validator_file_change(fx, OUTPUT_FILE)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "gap")

    def test_file_change_with_different_contents_fails_raw_integrity(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.events = [event for event in fx.events if not (
            event.get("message", {}).get("params", {}).get("threadId") == V1
            and event.get("message", {}).get("params", {}).get("item", {}).get("type")
            == "commandExecution"
            and "python3 -c" in event["message"]["params"]["item"].get("command", ""))]
        add_validator_file_change(fx, OUTPUT_FILE, content="different bytes")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "fail")

    def test_variable_body_write_is_an_evidence_gap_when_bytes_are_not_observed(self):
        fx = Fixture()
        legal_two_child(fx)
        payload = msg_text().encode("utf-8")
        source = (f"body = {payload!r}\n"
                  f"open({OUTPUT_FILE!r}, 'xb').write(body)")
        command = "python3 -c " + shlex.quote(source)
        for event in fx.events:
            params = event.get("message", {}).get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == V1 \
                    and item.get("type") == "commandExecution" \
                    and "python3 -c" in item.get("command", ""):
                item["command"] = command
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "gap", verdict)

    def test_incomplete_file_change_cannot_prove_raw_production(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.events = [event for event in fx.events if not (
            event.get("message", {}).get("params", {}).get("threadId") == V1
            and event.get("message", {}).get("params", {}).get("item", {}).get("type")
            == "commandExecution"
            and "python3 -c" in event["message"]["params"]["item"].get("command", ""))]
        add_validator_file_change(fx, OUTPUT_FILE, content=msg_text(),
                                 status="inProgress")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "gap")

    def test_message_without_item_identity_cannot_prove_original(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            params = event.get("message", {}).get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == V1 and item.get("type") == "message":
                item.pop("id", None)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "gap")

    def test_message_from_another_turn_cannot_be_attributed_to_production(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            params = event.get("message", {}).get("params", {})
            if params.get("threadId") == V1:
                params["turnId"] = ("validator-turn" if params.get("item", {}).get("type")
                                     == "commandExecution" else "other-turn")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)


class WriteScopeTests(RuntimeJudgeTestCase):
    @staticmethod
    def replace_validator_command(fx, command):
        found = 0
        for event in fx.events:
            params = event.get("message", {}).get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == V1 \
                    and item.get("type") == "commandExecution" \
                    and item.get("command", "").startswith("python3 -c "):
                item["command"] = command
                found += 1
        return found

    def test_compound_read_and_allowed_write_then_unauthorized_write_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        raw = msg_text().encode("utf-8")
        allowed = f"open({OUTPUT_FILE!r}, 'xb').write({raw!r})"
        unauthorized = "open('/tmp/fixture/protected.json', 'xb').write(b'x')"
        command = "cat /tmp/fixture/" + MD_NAME + " && python3 -c " \
            + shlex.quote(allowed) + " && python3 -c " \
            + shlex.quote(unauthorized)
        self.assertEqual(self.replace_validator_command(fx, command), 2)

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-validator-write-scope"], "fail",
                         verdict)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_python_command_with_multiple_write_targets_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        raw = msg_text().encode("utf-8")
        source = (f"open({OUTPUT_FILE!r}, 'xb').write({raw!r}); "
                  "open('/tmp/fixture/extra.json', 'xb').write(b'x')")
        self.assertEqual(self.replace_validator_command(
            fx, "python3 -c " + shlex.quote(source)), 2)

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-validator-write-scope"], "fail",
                         verdict)

    def test_same_byte_write_then_restore_still_fails_write_scope(self):
        fx = Fixture()
        legal_two_child(fx)
        raw = msg_text().encode("utf-8")
        source = (f"open({OUTPUT_FILE!r}, 'wb').write(b'temporary'); "
                  f"open({OUTPUT_FILE!r}, 'wb').write({raw!r})")
        self.assertEqual(self.replace_validator_command(
            fx, "python3 -c " + shlex.quote(source)), 2)

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-validator-write-scope"], "fail",
                         verdict)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_overwrite_existing_candidate_source_fails_write_scope(self):
        fx = Fixture()
        legal_two_child(fx)
        source_path = f"/tmp/fixture/{MD_NAME}"
        source = f"open({source_path!r}, 'wb').write(b'changed')"
        self.assertEqual(self.replace_validator_command(
            fx, "python3 -c " + shlex.quote(source)), 2)

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-validator-write-scope"], "fail",
                         verdict)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_nonexclusive_output_open_fails_even_when_bytes_match(self):
        fx = Fixture()
        legal_two_child(fx)
        raw = msg_text().encode("utf-8")
        source = f"open({OUTPUT_FILE!r}, 'wb').write({raw!r})"
        self.assertEqual(self.replace_validator_command(
            fx, "python3 -c " + shlex.quote(source)), 2)

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-validator-write-scope"], "fail",
                         verdict)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_proven_unauthorized_write_survives_following_unknown_command(self):
        fx = Fixture()
        legal_two_child(fx)
        source = "open('/tmp/fixture/protected.json', 'xb').write(b'x')"
        command = "python3 -c " + shlex.quote(source) \
            + " && unknown-validator-tool --mode mutate"
        self.assertEqual(self.replace_validator_command(fx, command), 2)

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-validator-write-scope"], "fail",
                         verdict)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_compound_legal_read_and_single_exclusive_output_write_passes(self):
        fx = Fixture()
        legal_two_child(fx)
        raw = msg_text().encode("utf-8")
        writer = f"open({OUTPUT_FILE!r}, 'xb').write({raw!r})"
        command = "cat /tmp/fixture/" + MD_NAME + " && python3 -c " \
            + shlex.quote(writer)
        self.assertEqual(self.replace_validator_command(fx, command), 2)

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-validator-write-scope"], "pass",
                         verdict)

    def test_path_read_text_is_read_only_in_a_legal_output_window(self):
        fx = Fixture()
        legal_two_child(fx)
        raw = msg_text().encode("utf-8")
        source = ("from pathlib import Path\n"
                  f"Path('/tmp/fixture/{MD_NAME}').read_text()\n"
                  f"open({OUTPUT_FILE!r}, 'xb').write({raw!r})")
        command = "python3 -c " + shlex.quote(source)
        self.assertEqual(self.replace_validator_command(fx, command), 2)
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)
        self.assertEqual(facts(verdict)["F-validator-write-scope"], "pass",
                         verdict)

    def test_pure_unknown_command_is_an_evidence_gap(self):
        fx = Fixture()
        legal_two_child(fx)
        command = "unknown-validator-tool --output " + OUTPUT_FILE
        self.assertEqual(self.replace_validator_command(fx, command), 2)

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-validator-write-scope"], "gap",
                         verdict)

    def test_protected_file_write_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        add_validator_file_change(fx, f"/tmp/fixture/{STATE_NAME}")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-validator-write-scope"], "fail")

    def test_outside_output_write_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        add_validator_file_change(fx, "/tmp/fixture/别的文件.json")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_actual_file_change_outside_output_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        add_validator_file_change(fx, "/tmp/fixture/elsewhere.json")
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-validator-write-scope"], "fail")

    def test_command_actions_alone_do_not_establish_write_violation(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            params = event.get("message", {}).get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == V1 and item.get("type") == "commandExecution":
                item["commandActions"] = [action("write", f"/tmp/fixture/{STATE_NAME}")]
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "PASS", verdict)
        self.assertEqual(facts(verdict)["F-validator-write-scope"], "pass",
                         verdict)


class OrderAndStopTests(RuntimeJudgeTestCase):
    def test_correction_dispatch_between_record_start_and_completion_fails(self):
        fx = Fixture()
        legal_two_child_spine(fx)
        record_complete = next(index for index, event in enumerate(fx.events)
            if event.get("message", {}).get("method") == "item/completed"
            and event.get("message", {}).get("params", {}).get("threadId") == ROOT
            and event["message"]["params"].get("item", {}).get("type")
            == "commandExecution"
            and judge.ROOT_RECORD in event["message"]["params"]["item"].get(
                "command", ""))
        completed_record = fx.events.pop(record_complete)
        fx.spawn(judge.GENERATOR_AGENT, G2)
        dispatch_events = fx.events[-2:]
        del fx.events[-2:]
        fx.events[record_complete:record_complete] = dispatch_events
        fx.events.insert(record_complete + len(dispatch_events), completed_record)

        verdict = run(fx, state=None)

        self.assertEqual(facts(verdict)["F-stop-order"], "fail", verdict)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

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
        fx.save(sha=msg_sha(), round_no=2)
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

    def test_terminal_state_round_count_matches_observed_validator_rounds(self):
        fx = Fixture()
        legal_two_child(fx)
        verdict = run(fx, state=TERMINAL2_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-terminal-state"], "fail")

    def test_rebuild_after_terminal_record_is_exactly_once(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.rebuild()
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-rebuild"], "fail")

    def test_rebuild_started_before_terminal_record_completed_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        record_start = next(index for index, event in enumerate(fx.events)
            if event.get("message", {}).get("method") == "item/started"
            and event.get("message", {}).get("params", {}).get("threadId") == ROOT
            and event["message"]["params"].get("item", {}).get("type")
            == "commandExecution"
            and judge.ROOT_RECORD in event["message"]["params"]["item"].get(
                "command", ""))
        record_complete = next(index for index, event in enumerate(fx.events)
            if event.get("message", {}).get("method") == "item/completed"
            and event.get("message", {}).get("params", {}).get("threadId") == ROOT
            and event["message"]["params"].get("item", {}).get("type")
            == "commandExecution"
            and judge.ROOT_RECORD in event["message"]["params"]["item"].get(
                "command", ""))
        rebuild_start = next(index for index, event in enumerate(fx.events)
            if event.get("message", {}).get("method") == "item/started"
            and event.get("message", {}).get("params", {}).get("threadId") == ROOT
            and event["message"]["params"].get("item", {}).get("type")
            == "commandExecution"
            and judge.ROOT_REBUILD in event["message"]["params"]["item"].get(
                "command", ""))
        rebuild_complete = next(index for index, event in enumerate(fx.events)
            if event.get("message", {}).get("method") == "item/completed"
            and event.get("message", {}).get("params", {}).get("threadId") == ROOT
            and event["message"]["params"].get("item", {}).get("type")
            == "commandExecution"
            and judge.ROOT_REBUILD in event["message"]["params"]["item"].get(
                "command", ""))
        record_events = (fx.events[record_start], fx.events[record_complete])
        rebuild_events = (fx.events[rebuild_start], fx.events[rebuild_complete])
        for index in sorted((record_start, record_complete,
                             rebuild_start, rebuild_complete), reverse=True):
            del fx.events[index]
        fx.events[record_start:record_start] = [
            record_events[0], rebuild_events[0],
            record_events[1], rebuild_events[1]]

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-rebuild"], "fail", verdict)
        self.assertEqual(verdict["classification"], "FAIL", verdict)

    def test_rebuild_without_completion_is_an_evidence_gap(self):
        fx = Fixture()
        legal_two_child(fx)
        fx.events.pop()  # remove the rebuild completion, leaving its start

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(facts(verdict)["F-rebuild"], "gap", verdict)
        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)


class EvidenceChannelTests(RuntimeJudgeTestCase):
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

    def test_prepare_return_for_another_round_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            message = event.get("message", {})
            params = message.get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == ROOT and item.get("type") == "commandExecution" \
                    and message.get("method") == "item/completed" \
                    and "stage3-prepare-validation" in item.get("command", ""):
                output, state = judge.Judge._json_from_output(item.get("aggregatedOutput"))
                self.assertEqual(state, "ok")
                output["round"] = 2
                item["aggregatedOutput"] = json.dumps(output)
                break
        verdict = run(fx, state=PASS_STATE)
        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-handoff-chain"], "fail")

    def test_prepare_return_missing_output_path_is_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        mutate_command_return(
            fx, ROOT, "stage3-prepare-validation",
            lambda payload: payload.pop("output_file"))

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-handoff-chain"], "gap")

    def test_prepare_professor_source_drift_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        mutate_command_return(
            fx, ROOT, "stage3-prepare-validation",
            lambda payload: payload.update(professor_dir="/tmp/other"))

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-handoff-chain"], "fail")

    def test_save_return_missing_round_is_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        mutate_command_return(
            fx, ROOT, "stage3-save-validation",
            lambda payload: payload.pop("round"))

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-handoff-chain"], "gap")

    def test_record_return_state_path_drift_fails(self):
        fx = Fixture()
        legal_two_child(fx)
        mutate_command_return(
            fx, ROOT, "stage3-record-validation",
            lambda payload: payload.update(
                state_path="/tmp/other/套磁候选状态.json"))

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(verdict["classification"], "FAIL", verdict)
        self.assertEqual(facts(verdict)["F-handoff-chain"], "fail")

    def test_record_return_missing_needs_correction_is_invalid(self):
        fx = Fixture()
        legal_two_child(fx)
        mutate_command_return(
            fx, ROOT, "stage3-record-validation",
            lambda payload: payload.pop("needs_correction"))

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-handoff-chain"], "gap")

    def test_non_monotonic_event_seq_invalidates_validator_evidence(self):
        fx = Fixture()
        legal_two_child(fx)
        for index, event in enumerate(fx.events, start=1):
            event["seq"] = index
        call_events = [(index, event) for index, event in enumerate(fx.events)
                       if event.get("message", {}).get("params", {}).get(
                           "threadId") == V1
                       and event.get("message", {}).get("params", {}).get(
                           "item", {}).get("type") == "commandExecution"
                       and "python3 -c" in event["message"]["params"][
                           "item"].get("command", "")]
        start_index, start_event = next(
            (index, event) for index, event in call_events
            if event.get("message", {}).get("method") == "item/started")
        _complete_index, complete_event = next(
            (index, event) for index, event in call_events
            if event.get("message", {}).get("method") == "item/completed")
        complete_event["seq"] = start_event["seq"]

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "gap")
        self.assertEqual(facts(verdict)["F-validator-write-scope"], "gap")

    def test_mismatched_call_id_cannot_bind_validator_command_completion(self):
        fx = Fixture()
        legal_two_child(fx)
        for event in fx.events:
            message = event.get("message", {})
            params = message.get("params", {})
            item = params.get("item", {})
            if params.get("threadId") == V1 \
                    and message.get("method") == "item/completed" \
                    and item.get("type") == "commandExecution" \
                    and "python3 -c" in item.get("command", ""):
                item["call_id"] = "different-call-id"
                break

        verdict = run(fx, state=PASS_STATE)

        self.assertEqual(verdict["classification"],
                         "INVALID_TEST_EXECUTION", verdict)
        self.assertEqual(facts(verdict)["F-raw-original"], "gap")
        self.assertEqual(facts(verdict)["F-validator-write-scope"], "gap")


if __name__ == "__main__":
    unittest.main()
