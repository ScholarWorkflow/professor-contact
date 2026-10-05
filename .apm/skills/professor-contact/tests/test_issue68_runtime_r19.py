"""Gate-2 r25 regressions for owner-local consumption and the root partition.

Synthetic evidence characterizes the evaluator and the recipe wiring. It is not
a real-host PC68-R1 acceptance PASS.

Test Plan r22 §4 keeps three explicit verdict channels over the §7
counterexample matrix:
- PASS channel (restored: a valid clean run is reported as PASS): the valid
  owner-local A+B run whose every formal child result is consumed through a
  root-thread ``agent_message`` FINAL_ANSWER receipt bound to that child's
  agent path, a diagnostic object recorded by a non-stage5 command, a
  non-FINAL_ANSWER diagnostic agent_message on the root thread, the single
  ``results`` wrapper, a stale earlier-turn final answer, the canonical
  ``試験`` spelling, and the r15 real-host compound command shapes (a
  ``python3 -c`` child packet and a ``python3 -c`` root partition
  preparation). Each asserts a plain PASS verdict with the preserved product
  facts (``owner_pack_set``/``rebuild_count``/``partition_executions``).
- FAIL_PRODUCT channel: every proven isolation/partition/orchestration
  violation — a sibling sentinel or a ``choices_scope`` field in the consumed
  input, missing/multiple/owner-executed (strict or compound)/changed root
  partitions, an owner business command starting before the root partition
  completed, a plan ``--choices-scope``, discovery ``--emit-choices-scope``,
  a changed bundle file, wrong owner count, an aggregate rebuilt before the
  root receipt consumption point, early or repeated rebuilds, a root receipt
  whose complete payload differs from the child's own returned outcome, a
  changed owner result behind an intact formal topology, and the rewritten
  ``試験`` spelling counterexample (carried by
  test_canonical_unicode_is_preserved). A proven sibling failure stays
  terminal when another child's completed commandExecution lacks its started
  record.
- BLOCKED_OBSERVABILITY / INVALID_EVIDENCE channel: missing consumption
  evidence on the frozen child surfaces (completed_user_payload_unobservable,
  owner_business_object_unobservable), two distinct consumed objects
  (owner_business_object_ambiguous), a missing root receipt
  (root_result_consumption_unobservable), a well-shaped receipt sent by
  another child's author, which the author binding alone keeps from being
  misattributed (root_result_consumption_unobservable), a shape-correct
  receipt from the child's own author whose Payload top level carries only a
  nested diagnostic object, which the top-level-only payload read keeps from
  ever counting as consumption (root_result_consumption_unobservable), a
  receipt whose Payload names the owner but lacks status/reason_code, which
  is malformed evidence and never a product failure
  (root_result_receipt_malformed), a completed commandExecution without a
  started record, deferred to the otherwise-clean terminal
  (command_start_unobservable), one formal child observed under two distinct
  agentPath values while the surviving path's own receipt is perfectly shaped
  and outcome-correct (child_agent_path_mapping_ambiguous), two receipts with
  conflicting outcomes for one owner (root_result_receipt_ambiguous), and a
  compound root text carrying several action words
  (root_orchestration_ambiguous).
"""
import importlib
import importlib.util
import json
import shlex
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))


def load(name):
    spec = importlib.util.spec_from_file_location(name, RUNTIME / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verify = load("verify_issue68_stage5_routing_r19")
bridge = load("run_issue68_stage5_routing_r19")
entry = load("run_issue68_stage5_routing_r19_codex")

FIXTURE_SHA = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"
CANONICAL_SPELLING = "試験"
REWRITTEN_SPELLING = "试验"
CHILD_AGENT_PATHS = ("/root/stage5_x", "/root/stage5_y")

PASS_CHANNEL = (
    "test_valid_owner_local_run_passes",
    "test_compound_child_packet_is_still_consumption_evidence",
    "test_compound_root_partition_is_recognized",
    "test_diagnostic_object_outside_stage5_commands_does_not_change_the_verdict",
    "test_non_final_answer_diagnostic_message_is_not_consumption",
    "test_results_wrapper_final_answer_still_passes",
    "test_stale_final_answer_is_not_terminal",
    "test_canonical_unicode_is_preserved",
)
FAIL_CHANNEL = (
    "test_sibling_sentinel_in_consumed_input_is_a_product_failure",
    "test_consumed_choices_scope_field_is_a_product_failure",
    "test_missing_root_partition_is_a_product_failure",
    "test_multiple_successful_partitions_are_a_product_failure",
    "test_partition_executed_by_owner_is_a_product_failure",
    "test_compound_partition_by_owner_is_a_product_failure",
    "test_changed_partition_output_is_a_product_failure",
    "test_owner_business_before_root_partition_is_a_product_failure",
    "test_plan_carrying_choices_scope_is_a_product_failure",
    "test_discovery_emitting_scope_is_a_product_failure",
    "test_changed_bundle_file_is_a_product_failure",
    "test_wrong_owner_count_is_a_product_failure",
    "test_rebuild_before_result_consumption_fails",
    "test_early_or_multiple_rebuild_is_a_product_failure",
    "test_receipt_payload_changed_is_a_product_failure",
    "test_routing_proof_survives_downstream_business_failure",
    "test_canonical_unicode_is_preserved",
    "test_missing_command_start_does_not_mask_sibling_product_failure",
)
BLOCKED_INVALID_CHANNEL = (
    "test_ambiguous_consumed_objects_are_invalid_evidence",
    "test_missing_consumption_evidence_is_blocked",
    "test_missing_root_receipt_blocks",
    "test_cross_child_body_is_not_a_consumption_receipt",
    "test_nested_diagnostic_payload_is_not_a_consumption_receipt",
    "test_receipt_missing_required_fields_is_not_a_product_failure",
    "test_command_start_gap_blocks_the_clean_terminal",
    "test_conflicting_agent_path_mapping_is_invalid",
    "test_ambiguous_root_receipts_are_invalid",
    "test_multi_action_compound_root_command_blocks_orchestration",
)
WIRING_TESTS = (
    "test_bridge_pins_the_r19_verifier_and_r12_builder",
    "test_codex_only_entry_binds_the_r19_contract",
    "test_contract_freezes_owner_input_isolation_and_partition_evidence",
    "test_verifier_refuses_the_opencode_host",
    "test_channel_declaration_matches_the_matrix",
    "test_resolve_eval_port_uses_direnv_only",
    "test_resolve_eval_port_refuses_to_start_without_direnv",
)


class TestIssue68RuntimeR19(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        owners = []
        for index, name in enumerate(("試験 教授", "佐藤 花子")):
            directory = str(self.root / name)
            owners.append({
                "professor": name,
                "professor_dir": directory,
                "email_pack": str(self.root / name / "邮件输入.json"),
                "email_ids": ["email-" + str(index)],
                "transport_sentinel": "owner-" + str(index),
                "expected_choices_rows": [{
                    "email_id": "email-" + str(index), "first_choice": False,
                    "professor_dir": directory, "transport_sentinel": "owner-" + str(index),
                }],
                "expected_result": {"status": "needs_refresh", "reason_code": "verify_missing"},
            })
        for index, owner in enumerate(owners):
            other = owners[1 - index]
            owner["sibling_exclusions"] = [other["email_pack"], other["professor_dir"],
                                           other["email_ids"][0], other["transport_sentinel"],
                                           "choices_scope"]
        self.manifest = {
            "owners": owners,
            "program_root": str(self.root),
            "invalid_pack": str(self.root / "C" / "邮件输入.json"),
            "partition": {"owners": [{"professor_dir": owner["professor_dir"], "status": "ok",
                                      "choices_rows": owner["expected_choices_rows"]}
                                     for owner in owners]},
        }
        for index in (0, 1):
            self.write_bundle(index, owners[index]["expected_choices_rows"])

    # ---- fixture pieces ---------------------------------------------------

    def owner(self, index):
        return self.manifest["owners"][index]

    def packet(self, owner):
        """The r19 one-professor packet: email_pack plus the owner's own rows."""
        return {"email_pack": owner["email_pack"], "choices": owner["expected_choices_rows"]}

    def bundle_path(self, index):
        return str(self.root / ("choices-bundle-owner-" + str(index) + ".json"))

    def write_bundle(self, index, rows):
        Path(self.bundle_path(index)).write_text(json.dumps(rows, ensure_ascii=False),
                                                 encoding="utf-8")

    def stage5_command(self, action, *flag_pairs):
        tokens = ["python3", "/installed/contact_state.py", action,
                  "--program-root", self.manifest["program_root"]]
        for flag, value in flag_pairs:
            tokens.extend((flag, value))
        return shlex.join(tokens)

    def compound_command(self, action, *owner_packs):
        """The r15 real-host compound preparation shape: a ``python3 -c``
        wrapper whose stage5 argv is a quoted JSON list, so no action word is
        a standalone shell token and strict flag parsing sees nothing."""
        argv = ["python3", "/installed/contact_state.py", action,
                "--program-root", self.manifest["program_root"]]
        for pack in owner_packs:
            argv.extend(("--owner", pack))
        body = ("import subprocess\n"
                "argv = " + json.dumps(argv, ensure_ascii=False) + "\n"
                "subprocess.check_output(argv, text=True)")
        return shlex.join(["/bin/zsh", "-lc", "python3 -c " + shlex.quote(body)])

    def compound_plan_command(self, owner, packet):
        """The r15 real-host child shape: the one-professor packet rides as a
        JSON/Python literal inside a ``python3 -c`` wrapper around the
        ``stage5-plan`` argv list."""
        argv = ["python3", "/installed/contact_state.py", "stage5-plan",
                "--program-root", self.manifest["program_root"],
                "--email-pack", owner["email_pack"]]
        body = ("import subprocess, json\n"
                "packet = " + json.dumps(packet, ensure_ascii=False) + "\n"
                "argv = " + json.dumps(argv, ensure_ascii=False) + "\n"
                "subprocess.check_output(argv + [\"--packet\", json.dumps(packet, ensure_ascii=False)],"
                " text=True)")
        return shlex.join(["/bin/zsh", "-lc", "python3 -c " + shlex.quote(body)])

    def compound_two_action_command(self):
        """A compound root text carrying two action words: unattributable."""
        discovery = json.dumps(["python3", "/installed/contact_state.py", "stage5-list-inputs",
                                "--program-root", self.manifest["program_root"]], ensure_ascii=False)
        partition = json.dumps(["python3", "/installed/contact_state.py", "stage5-partition-choices",
                                "--program-root", self.manifest["program_root"]], ensure_ascii=False)
        body = ("import subprocess\n"
                "discovery = " + discovery + "\n"
                "partition = " + partition + "\n"
                "subprocess.check_output(discovery, text=True)\n"
                "subprocess.check_output(partition, text=True)")
        return shlex.join(["/bin/zsh", "-lc", "python3 -c " + shlex.quote(body)])

    def discovery(self):
        return json.dumps({"status": "ok", "inputs": [
            *[{"email_pack": owner["email_pack"], "status": "ok"} for owner in self.manifest["owners"]],
            {"email_pack": self.manifest["invalid_pack"], "status": "error"},
        ]}, ensure_ascii=False)

    def partition_rows(self):
        return [{"professor_dir": owner["professor_dir"], "status": "ok",
                 "choices_rows": owner["expected_choices_rows"]}
                for owner in self.manifest["owners"]]

    def partition_output(self, rows=None):
        return json.dumps({"status": "ok", "owners": [
            {"professor_dir": row["professor_dir"], "partition": {"status": "ok"},
             "choices_rows": row["choices_rows"]}
            for row in (self.partition_rows() if rows is None else rows)]}, ensure_ascii=False)

    def root_result(self):
        return json.dumps([dict(owner["expected_result"], professor_dir=owner["professor_dir"])
                           for owner in self.manifest["owners"]], ensure_ascii=False)

    def evidence(self, *, per_owner=None, partition_present=True, partition_count=1,
                 partition_rows=None, discovery_flags=(), rebuild_timing=None,
                 old_turn_final=None, final_text=None, receipts="normal",
                 partition_compound=False, root_extra_commands=(),
                 owner_business_before_partition=False, agent_paths=None,
                 drop_started=()):
        """One faithful r24 baseline: root discovery plus one deterministic
        partition, the root-thread ``subAgentActivity`` items binding each
        child thread to its agent path, two formal children each consuming
        its own packet on its own stage5 plan surface, one root-thread
        ``agent_message`` FINAL_ANSWER receipt per child on the current turn,
        and the current-turn root final answer. ``receipts`` selects the
        receipt counterexample shape ("normal" default, "missing",
        "changed", "ambiguous", "cross_child", "diagnostic_only", "nested",
        "malformed"); ``partition_compound`` emits the root partition in the
        r15 real-host ``python3 -c`` compound shape and ``root_extra_commands``
        appends further root command items.
        ``rebuild_timing="between"`` places one root rebuild before the first
        child's receipt consumption point;
        ``owner_business_before_partition`` starts a child business command
        before the root partition completes. ``agent_paths`` maps a child
        index to the list of ``agentPath`` values its subAgentActivity items
        carry (default one canonical path per child; more than one makes the
        child-to-path mapping ambiguous, and the child's own receipt is then
        authored by the last path in its list). ``drop_started`` names item
        ids whose ``item/started`` event is omitted, so the completed
        commandExecution has no started record (the r24 gap shape)."""
        per_owner = per_owner or {}
        events, relations, seq = [], [], 0

        def event(method, thread, item, turn="turn-current", turn_status=None):
            nonlocal seq
            seq += 1
            params = {"threadId": thread, "turnId": turn, "item": item}
            if turn_status is not None:
                params["turn"] = {"id": turn, "status": turn_status}
            events.append({"runtime_seq": seq, "runtime_generation": "g", "direction": "recv",
                           "message": {"method": method, "params": params}})

        def command(thread, item_id, command_text, output=""):
            if item_id not in drop_started:
                event("item/started", thread, {"type": "commandExecution", "id": item_id,
                                               "command": command_text})
            event("item/completed", thread, {"type": "commandExecution", "id": item_id,
                                             "command": command_text, "exitCode": 0,
                                             "aggregatedOutput": output})

        def agent_message_receipt(author_path, text, item_id):
            event("rawResponseItem/completed", "root", {
                "type": "agent_message",
                "id": item_id,
                "author": author_path,
                "recipient": "/root",
                "content": [{"type": "input_text", "text": text}],
            })

        def root_receipt(child, author_path, payload, suffix=""):
            """The real-host root receipt shape: a root-thread
            ``agent_message`` FINAL_ANSWER whose Payload JSON names the
            owner's professor_dir (author is the child's agent path)."""
            agent_message_receipt(
                author_path,
                "Message Type: FINAL_ANSWER\nTask name: /root\nSender: "
                + author_path + "\nPayload:\n" + payload,
                "receipt-" + child + suffix)

        def receipt_payload(owner):
            return json.dumps(dict(owner["expected_result"], professor_dir=owner["professor_dir"]),
                              ensure_ascii=False)

        def changed_receipt_payload(owner):
            return json.dumps(dict(owner["expected_result"], professor_dir=owner["professor_dir"],
                                   status="ok", reason_code="invented"), ensure_ascii=False)

        def ambiguous_receipt_payload(owner):
            return json.dumps(dict(owner["expected_result"], professor_dir=owner["professor_dir"],
                                   status="needs_input"), ensure_ascii=False)

        def nested_receipt_payload(owner):
            """The reviewer's blocker-3 shape: a Payload whose top level
            carries only a nested diagnostic object naming this owner with
            the child's own outcome values."""
            return json.dumps({"diagnostic": dict(owner["expected_result"],
                                                  professor_dir=owner["professor_dir"])},
                              ensure_ascii=False)

        def malformed_receipt_payload(owner):
            """The r24 blocker-2 shape: a Payload whose top level names this
            owner's professor_dir but lacks the status/reason_code fields."""
            return json.dumps({"professor_dir": owner["professor_dir"]}, ensure_ascii=False)

        command("root", "root-discovery",
                self.stage5_command("stage5-list-inputs", *discovery_flags), self.discovery())
        if owner_business_before_partition:
            # r20 ordering counterexample: the first owner's own one-professor
            # plan command starts before the root partition completes. The
            # command text matches the child's later packet command, so the
            # packet oracle still sees exactly one consumed object.
            early_owner = self.owner(0)
            command("child-0", "exec-early-packet",
                    self.stage5_command("stage5-plan",
                                        ("--email-pack", early_owner["email_pack"]),
                                        ("--packet", json.dumps(self.packet(early_owner),
                                                                ensure_ascii=False))),
                    json.dumps(early_owner["expected_result"], ensure_ascii=False))
        if partition_present:
            for number in range(partition_count):
                partition_command = (self.compound_command("stage5-partition-choices",
                                                           self.owner(0)["email_pack"],
                                                           self.owner(1)["email_pack"])
                                     if partition_compound else
                                     self.stage5_command("stage5-partition-choices",
                                                         ("--owner", self.owner(0)["email_pack"]),
                                                         ("--owner", self.owner(1)["email_pack"])))
                command("root", "root-partition-" + str(number), partition_command,
                        self.partition_output(partition_rows))
        if rebuild_timing == "early":
            command("root", "root-rebuild-early", self.stage5_command("stage5-rebuild-overview"))
        for offset, (command_text, output) in enumerate(root_extra_commands):
            command("root", "root-extra-" + str(offset), command_text, output)
        path_lists = agent_paths or {}
        for index in range(len(self.manifest["owners"])):
            # The real-host child_thread_id -> agent_path association: the
            # completed root-thread subAgentActivity item carries both keys.
            for offset, path in enumerate(path_lists.get(index, [CHILD_AGENT_PATHS[index]])):
                event("item/completed", "root", {
                    "type": "subAgentActivity",
                    "id": "subagent-" + str(index) + ("" if offset == 0 else "-" + str(offset)),
                    "kind": "completed",
                    "agentThreadId": "child-" + str(index),
                    "agentPath": path,
                })
        for index, owner in enumerate(self.manifest["owners"]):
            child = "child-" + str(index)
            paths = path_lists.get(index, [CHILD_AGENT_PATHS[index]])
            relations.append({"tool": "spawnAgent", "sender_thread_id": "root",
                              "receiver_thread_ids": [child]})
            event("rawResponseItem/completed", child, {
                "type": "agent_message",
                "id": "amsg-" + str(index),
                "author": "/root",
                "recipient": paths[0],
                "content": [
                    {"type": "input_text",
                     "text": "Message Type: NEW_TASK\nTask name: " + paths[0]
                             + "\nSender: /root\nPayload:\n"},
                    {"type": "encrypted_content", "encrypted_content": "gAAAAA-encrypted-task-payload"},
                ],
            })
            spec = per_owner.get(index, {})
            if spec.get("commands", True):
                for offset, packet in enumerate(spec.get("packets", [self.packet(owner)])):
                    packet_command = (self.compound_plan_command(owner, packet)
                                      if spec.get("compound_packet") else
                                      self.stage5_command("stage5-plan",
                                                          ("--email-pack", owner["email_pack"]),
                                                          ("--packet", json.dumps(packet, ensure_ascii=False))))
                    command(child, "exec-" + str(index) + "-packet-" + str(offset), packet_command,
                            json.dumps(owner["expected_result"], ensure_ascii=False))
                command(child, "exec-" + str(index) + "-choices",
                        self.stage5_command("stage5-plan",
                                            ("--email-pack", owner["email_pack"]),
                                            ("--choices", self.bundle_path(index)),
                                            *spec.get("choices_flags", ())),
                        json.dumps(owner["expected_result"], ensure_ascii=False))
            for offset, (command_text, output) in enumerate(spec.get("extra_commands", ())):
                command(child, "exec-" + str(index) + "-extra-" + str(offset), command_text, output)
            event("rawResponseItem/completed", child, {
                "type": "message", "role": "assistant", "phase": "final_answer",
                "content": [{"type": "output_text", "text": spec.get("result_text") or json.dumps(
                    dict(owner["expected_result"], professor_dir=owner["professor_dir"]),
                    ensure_ascii=False)}],
            })
            event("turn/completed", child, {"type": "turn", "id": "turn-" + str(index)},
                  turn="turn-" + str(index), turn_status="completed")
            if rebuild_timing == "between" and index == 0:
                # Timing counterexample: the root rebuilds before the
                # root-thread receipt that consumes this child's result.
                command("root", "root-rebuild-between",
                        self.stage5_command("stage5-rebuild-overview"))
            if receipts == "missing":
                continue
            if receipts == "cross_child" and index == 0:
                continue  # this child's own receipt is absent in this shape
            if receipts == "diagnostic_only" and index == 0:
                root_receipt(child, paths[-1], receipt_payload(owner))
                # A root agent_message from this child's author whose body
                # carries the same result JSON without the FINAL_ANSWER
                # shape: a diagnostic surface, never a consumption receipt.
                agent_message_receipt(
                    paths[-1],
                    "Message Type: PROGRESS\nTask name: /root\nSender: "
                    + paths[-1] + "\nPayload:\n" + receipt_payload(owner),
                    "receipt-progress-" + child)
                continue
            if receipts == "nested" and index == 0:
                # Blocker-3 discriminator: the child's own author sends a
                # fully shaped FINAL_ANSWER receipt whose Payload top level
                # carries only a nested diagnostic object naming this owner
                # with the child's own outcome values. The payload is read at
                # its top level only, so this receipt is never consumption.
                root_receipt(child, paths[-1], nested_receipt_payload(owner))
                continue
            if receipts == "cross_child" and index == 1:
                # Judge's discriminator: the other child's author sends a
                # fully shaped FINAL_ANSWER receipt whose Payload carries
                # child-0's result JSON. Only the author binding keeps it
                # from being misattributed as child-0's receipt.
                agent_message_receipt(
                    CHILD_AGENT_PATHS[1],
                    "Message Type: FINAL_ANSWER\nTask name: /root\nSender: "
                    + CHILD_AGENT_PATHS[1] + "\nPayload:\n" + receipt_payload(self.owner(0)),
                    "receipt-cross-child-0")
            if receipts == "changed":
                root_receipt(child, paths[-1], changed_receipt_payload(owner))
            elif receipts == "malformed":
                root_receipt(child, paths[-1], malformed_receipt_payload(owner))
            elif receipts == "ambiguous" and index == 0:
                root_receipt(child, paths[-1], receipt_payload(owner), suffix="-a")
                root_receipt(child, paths[-1], ambiguous_receipt_payload(owner), suffix="-b")
            else:
                root_receipt(child, paths[-1], receipt_payload(owner))
        if rebuild_timing == "double":
            command("root", "root-rebuild-a", self.stage5_command("stage5-rebuild-overview"))
            command("root", "root-rebuild-b", self.stage5_command("stage5-rebuild-overview"))
        if old_turn_final is not None:
            event("rawResponseItem/completed", "root", {
                "type": "message", "role": "assistant", "phase": "final_answer",
                "content": [{"type": "output_text", "text": old_turn_final}],
            }, turn="turn-old")
        event("rawResponseItem/completed", "root", {
            "type": "message", "role": "assistant", "phase": "final_answer",
            "content": [{"type": "output_text", "text": final_text or self.root_result()}],
        })
        response = {"version": "codex-cli 0.159.0-alpha.12.1",
                    "output": {"thread_id": "root", "turn_id": "turn-current", "runtime_generation": "g",
                               "termination_reason": "completed", "app_server_events": events}}
        adapter = {"fixture_status": "FIXTURE_READY",
                   "delegation": {"state": "confirmed", "formal_child_count": 2, "basis": ["formal_spawn_relation"]},
                   "dispatch": {"thread_relations": relations, "agent_identity": {}}}
        return response, adapter

    # ---- PASS channel: the valid owner-local run ---------------------------

    def test_valid_owner_local_run_passes(self):
        """A valid professor-local run passes."""
        response, adapter = self.evidence()
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["partition_executions"], 1)
        self.assertEqual(result["rebuild_count"], 0)
        self.assertEqual(result["owner_pack_set"],
                         sorted(owner["email_pack"] for owner in self.manifest["owners"]))
        self.assertIn("identity_diagnostics", result)

    def test_compound_child_packet_is_still_consumption_evidence(self):
        """The r15 real-host child shape: the packet rides inside a
        ``python3 -c`` compound expression whose stage5 argv is a quoted
        list, so strict parsing sees no invocation; the loose business
        surface still attributes the consumed packet."""
        response, adapter = self.evidence(per_owner={0: {"compound_packet": True},
                                                     1: {"compound_packet": True}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["owner_pack_set"],
                         sorted(owner["email_pack"] for owner in self.manifest["owners"]))

    def test_compound_root_partition_is_recognized(self):
        """The r15 real-host root shape: the partition preparation is a
        ``python3 -c`` compound command whose single action word is
        ``stage5-partition-choices``; success is judged from the
        aggregatedOutput JSON alone."""
        response, adapter = self.evidence(partition_compound=True)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["partition_executions"], 1)

    def test_diagnostic_object_outside_stage5_commands_does_not_change_the_verdict(self):
        echo = shlex.join(["echo", json.dumps({"email_pack": self.owner(1)["email_pack"],
                                               "note": "diagnostic example"}, ensure_ascii=False)])
        response, adapter = self.evidence(per_owner={0: {"extra_commands": [(echo, "")]}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")

    def test_non_final_answer_diagnostic_message_is_not_consumption(self):
        """Reviewer discriminator 2: a root agent_message from child-0's
        author whose body carries the same result JSON without the
        FINAL_ANSWER shape (here a PROGRESS header) is a diagnostic surface;
        it neither adds nor replaces a consumption receipt, and the child's
        real FINAL_ANSWER receipt still proves consumption."""
        response, adapter = self.evidence(receipts="diagnostic_only")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["partition_executions"], 1)

    def test_results_wrapper_final_answer_still_passes(self):
        response, adapter = self.evidence(final_text=json.dumps(
            {"results": json.loads(self.root_result())}, ensure_ascii=False))
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")

    def test_stale_final_answer_is_not_terminal(self):
        response, adapter = self.evidence(old_turn_final=json.dumps(
            [{"professor_dir": "stale", "status": "ok", "reason_code": "invented"}]))
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")

    def test_canonical_unicode_is_preserved(self):
        packet = self.packet(self.owner(0))
        self.assertIn(CANONICAL_SPELLING, json.dumps(packet, ensure_ascii=False))
        response, adapter = self.evidence()
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")
        rewritten = dict(packet, choices=json.loads(json.dumps(
            packet["choices"], ensure_ascii=False).replace(CANONICAL_SPELLING, REWRITTEN_SPELLING)))
        self.assertNotEqual(rewritten["choices"], self.owner(0)["expected_choices_rows"])
        response, adapter = self.evidence(per_owner={0: {"packets": [rewritten]}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "owner_bundle_choices_changed"))
        self.assertEqual(result["observed_pack"], self.owner(0)["email_pack"])

    # ---- FAIL_PRODUCT channel: isolation counterexamples -------------------

    def test_sibling_sentinel_in_consumed_input_is_a_product_failure(self):
        owner, other = self.owner(0), self.owner(1)
        packet = dict(self.packet(owner),
                      carried_note="forwarded " + other["transport_sentinel"] + " records")
        response, adapter = self.evidence(per_owner={0: {"packets": [packet]}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "owner_input_contains_sibling_data"))
        self.assertEqual(result["observed_pack"], owner["email_pack"])
        self.assertEqual(result["observed_markers"], [other["transport_sentinel"]])

    def test_consumed_choices_scope_field_is_a_product_failure(self):
        owner = self.owner(0)
        packet = dict(self.packet(owner), choices_scope=[
            {"professor_dir": owner["professor_dir"], "email_ids": list(owner["email_ids"])}])
        response, adapter = self.evidence(per_owner={0: {"packets": [packet]}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "owner_input_carries_choices_scope"))
        self.assertEqual(result["observed_pack"], owner["email_pack"])

    # ---- FAIL_PRODUCT channel: the root partition oracle -------------------

    def test_missing_root_partition_is_a_product_failure(self):
        response, adapter = self.evidence(partition_present=False)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "root_partition_not_deterministic"))
        self.assertEqual(result["partition_commands"], 0)

    def test_multiple_successful_partitions_are_a_product_failure(self):
        response, adapter = self.evidence(partition_count=2)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "multiple_root_partitions"))

    def test_partition_executed_by_owner_is_a_product_failure(self):
        response, adapter = self.evidence(per_owner={0: {"extra_commands": [(
            self.stage5_command("stage5-partition-choices",
                                ("--owner", self.owner(0)["email_pack"]),
                                ("--owner", self.owner(1)["email_pack"])),
            self.partition_output())]}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "partition_executed_by_owner"))

    def test_compound_partition_by_owner_is_a_product_failure(self):
        """A child compound text whose single action word is
        ``stage5-partition-choices`` proves an owner executed the partition
        entry even when strict parsing cannot attribute the call."""
        compound = self.compound_command("stage5-partition-choices",
                                         self.owner(0)["email_pack"],
                                         self.owner(1)["email_pack"])
        response, adapter = self.evidence(
            per_owner={0: {"extra_commands": [(compound, self.partition_output())]}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "partition_executed_by_owner"))

    def test_changed_partition_output_is_a_product_failure(self):
        rows = self.partition_rows()
        rows[0] = dict(rows[0], choices_rows=[])
        response, adapter = self.evidence(partition_rows=rows)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "root_partition_changed"))

    def test_owner_business_before_root_partition_is_a_product_failure(self):
        """r20 ordering fact: the root's successful partition must complete
        before any owner business call starts; a child business command that
        starts earlier is a product failure."""
        response, adapter = self.evidence(owner_business_before_partition=True)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "owner_business_precedes_partition"))
        self.assertIn("stage5-plan", result["observed_call"])
        self.assertIn("contact_state.py", result["observed_call"])

    # ---- FAIL_PRODUCT channel: plan, discovery and bundle files ------------

    def test_plan_carrying_choices_scope_is_a_product_failure(self):
        response, adapter = self.evidence(per_owner={0: {"choices_flags": (
            ("--choices-scope", str(self.root / "scope.json")),)}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "owner_plan_carries_choices_scope"))

    def test_discovery_emitting_scope_is_a_product_failure(self):
        response, adapter = self.evidence(discovery_flags=(
            ("--emit-choices-scope", str(self.root / "scope.json")),))
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "discovery_emits_choices_scope"))

    def test_changed_bundle_file_is_a_product_failure(self):
        owner = self.owner(0)
        response, adapter = self.evidence()
        rows = json.loads(json.dumps(owner["expected_choices_rows"], ensure_ascii=False))
        rows[0]["transport_sentinel"] = "rewritten"
        self.write_bundle(0, rows)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "owner_bundle_choices_changed"))
        self.assertEqual(result["observed_pack"], owner["email_pack"])

    # ---- FAIL_PRODUCT channel: orchestration -------------------------------

    def test_wrong_owner_count_is_a_product_failure(self):
        response, adapter = self.evidence()
        adapter["dispatch"]["thread_relations"] = adapter["dispatch"]["thread_relations"][:1]
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "wrong_owner_count"))

    def test_rebuild_before_result_consumption_fails(self):
        """The children returned their results, but the rebuild runs before
        the root-thread agent_message receipt that consumes each result —
        the aggregate still precedes result consumption."""
        response, adapter = self.evidence(rebuild_timing="between")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "aggregate_precedes_result_consumption"))

    def test_early_or_multiple_rebuild_is_a_product_failure(self):
        response, adapter = self.evidence(rebuild_timing="early")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "aggregate_precedes_result_consumption"))
        response, adapter = self.evidence(rebuild_timing="double")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "multiple_aggregate_rebuilds"))

    def test_receipt_payload_changed_is_a_product_failure(self):
        """The root receipt's Payload outcome differs from the outcome the
        child itself returned on its own thread: the root did not receive
        what the child produced."""
        response, adapter = self.evidence(receipts="changed")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "root_receipt_payload_changed"))
        self.assertEqual(result["observed_result"],
                         {"professor_dir": self.owner(0)["professor_dir"],
                          "status": "ok", "reason_code": "invented"})
        self.assertEqual(result["expected_result"],
                         dict(self.owner(0)["expected_result"],
                              professor_dir=self.owner(0)["professor_dir"]))

    def test_missing_command_start_does_not_mask_sibling_product_failure(self):
        """Reviewer blocker 3 (r24): a completed commandExecution without a
        started record is deferred as an observability gap instead of ending
        the scan, so the sibling child's proven isolation failure keeps its
        terminal precedence and the run is not blocked as
        command_start_unobservable."""
        packet = dict(self.packet(self.owner(1)),
                      carried_note="forwarded " + self.owner(0)["transport_sentinel"] + " records")
        echo = shlex.join(["echo", "diagnostic"])
        response, adapter = self.evidence(per_owner={0: {"extra_commands": [(echo, "")]},
                                                     1: {"packets": [packet]}},
                                          drop_started={"exec-0-extra-0"})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "owner_input_contains_sibling_data"))
        self.assertEqual(result["observed_markers"], [self.owner(0)["transport_sentinel"]])

    def test_multi_action_compound_root_command_blocks_orchestration(self):
        """A compound root text carrying two action words cannot be
        attributed to one orchestration step and stays blocked."""
        compound = self.compound_two_action_command()
        response, adapter = self.evidence(root_extra_commands=[(compound, "")])
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "root_orchestration_ambiguous"))
        self.assertEqual(result["detail"], compound[:200])

    def test_routing_proof_survives_downstream_business_failure(self):
        changed = json.dumps({"status": "needs_refresh", "reason_code": "verify_missing",
                              "professor_dir": self.owner(1)["professor_dir"]}, ensure_ascii=False)
        response, adapter = self.evidence(per_owner={0: {"result_text": changed}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "owner_result_directory_changed"))
        self.assertNotIn(result["reason_code"],
                         ("wrong_owner_count", "formal_delegation_unobservable"))

    # ---- frozen blocked and invalid channels -------------------------------

    def test_ambiguous_consumed_objects_are_invalid_evidence(self):
        owner = self.owner(0)
        variant = dict(self.packet(owner), note="second embedded example")
        response, adapter = self.evidence(
            per_owner={0: {"packets": [self.packet(owner), variant]}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("INVALID_EVIDENCE", "owner_business_object_ambiguous"))
        self.assertEqual(result["observed_candidates"], 2)

    def test_missing_consumption_evidence_is_blocked(self):
        response, adapter = self.evidence(per_owner={0: {"commands": False}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable"))
        response, adapter = self.evidence(per_owner={0: {"packets": []}})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable"))

    def test_missing_root_receipt_blocks(self):
        """Without any root-thread agent_message receipt the root never
        provably consumed the child results, and no wait or completion event
        cures the missing consumption surface."""
        response, adapter = self.evidence(receipts="missing")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "root_result_consumption_unobservable"))

    def test_cross_child_body_is_not_a_consumption_receipt(self):
        """Reviewer discriminator 1: child-0's own receipt is absent while
        child-1's author sends a fully shaped FINAL_ANSWER receipt whose
        Payload carries child-0's result JSON. The body alone never
        attributes a receipt — the author must equal the child's agent path
        — so child-0 keeps no consumption point and the run stays blocked,
        never a guessed PASS."""
        response, adapter = self.evidence(receipts="cross_child")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "root_result_consumption_unobservable"))

    def test_nested_diagnostic_payload_is_not_a_consumption_receipt(self):
        """Reviewer blocker 3: the child's own author sends a fully shaped
        FINAL_ANSWER receipt whose Payload top level carries only a nested
        diagnostic object naming this owner with the child's own outcome
        values. The payload is read at its top level only and never
        recursively, so the nested object is not an outcome: the child keeps
        no consumption receipt and the run stays blocked, never a false
        PASS."""
        response, adapter = self.evidence(receipts="nested")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "root_result_consumption_unobservable"))

    def test_receipt_missing_required_fields_is_not_a_product_failure(self):
        """Reviewer blocker 2 (r24): a FINAL_ANSWER receipt whose Payload top
        level names this owner's professor_dir but lacks status/reason_code is
        malformed evidence, never a changed payload: the receipt counts as no
        legal receipt, the child is blocked with the missing field names and
        the run is never failed as root_receipt_payload_changed."""
        response, adapter = self.evidence(receipts="malformed")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "root_result_receipt_malformed"))
        self.assertEqual(result["detail"], ["reason_code", "status"])

    def test_command_start_gap_blocks_the_clean_terminal(self):
        """A completed commandExecution without a started record yields no
        call and surfaces as command_start_unobservable only after every
        child verdict and the runtime oracle stayed clean, with the gap
        summary attached to the detail."""
        echo = shlex.join(["echo", "diagnostic"])
        response, adapter = self.evidence(per_owner={0: {"extra_commands": [(echo, "")]}},
                                          drop_started={"exec-0-extra-0"})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "command_start_unobservable"))
        self.assertEqual(len(result["detail"]), 1)
        gap = result["detail"][0]
        self.assertEqual(gap[0], "command_start_unobservable")
        self.assertEqual(gap[1], "child-0")
        self.assertIsInstance(gap[2], int)

    def test_conflicting_agent_path_mapping_is_invalid(self):
        """Reviewer blocker 4: the same formal child is observed under two
        distinct agentPath values while only the second path sends a
        perfectly shaped, outcome-correct receipt. The child-to-author
        association is no longer unique, so the evidence itself is damaged
        (INVALID) even though the surviving receipt alone would have
        matched."""
        response, adapter = self.evidence(agent_paths={0: ["/root/a", "/root/b"]})
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("INVALID_EVIDENCE", "child_agent_path_mapping_ambiguous"))
        self.assertEqual(result["detail"], ["/root/a", "/root/b"])

    def test_ambiguous_root_receipts_are_invalid(self):
        """Two root receipts for one owner carrying different outcomes leave
        the consumed result ambiguous: damaged evidence, never a guessed
        product failure."""
        response, adapter = self.evidence(receipts="ambiguous")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("INVALID_EVIDENCE", "root_result_receipt_ambiguous"))
        self.assertEqual(result["observed_outcomes"], [
            dict(self.owner(0)["expected_result"], professor_dir=self.owner(0)["professor_dir"]),
            {"professor_dir": self.owner(0)["professor_dir"], "status": "needs_input",
             "reason_code": "verify_missing"},
        ])

    # ---- wiring and contract ----------------------------------------------

    def test_bridge_pins_the_r19_verifier_and_r12_builder(self):
        base = importlib.import_module("run_issue68_stage5_routing")
        build = importlib.import_module("build_issue68_codex_request_r12")
        original = {"FIXTURE_SHA": base.FIXTURE_SHA, "build_request": base.build_request,
                    "verify_codex": base.verify_codex, "verify_opencode": base.verify_opencode}
        self.addCleanup(lambda: [setattr(base, key, value) for key, value in original.items()])
        bridge.pin_base_runner()
        self.assertEqual(base.FIXTURE_SHA, FIXTURE_SHA)
        self.assertIs(base.build_request, build.build_request)
        self.assertIs(base.verify_codex, verify.verify_codex)
        with self.assertRaises(ValueError):
            base.verify_opencode([], {}, {})

    def test_codex_only_entry_binds_the_r19_contract(self):
        self.assertEqual(entry.CONTRACT.name, "issue68-runtime-evidence-contract-r19.json")
        self.assertEqual(entry.FIXTURE_SHA, FIXTURE_SHA)
        self.assertEqual(entry.HOST, "codex")
        self.assertEqual(entry.CASE, "PC68-R1")
        self.assertEqual(entry.EXECUTION_KIND, "acceptance")
        self.assertEqual(entry.load_contract()["revision"], entry.CONTRACT_REVISION)
        self.assertTrue(entry.check_entry_uniqueness(
            str(RUNTIME / "run_issue68_stage5_routing_r19_codex.py")))
        with self.assertRaises(ValueError):
            entry.check_entry_uniqueness(str(RUNTIME / "run_issue68_stage5_routing_r18_codex.py"))

    def test_contract_freezes_owner_input_isolation_and_partition_evidence(self):
        contract = json.loads(
            (RUNTIME / "issue68-runtime-evidence-contract-r19.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["revision"], "issue-68-runtime-evidence-r26-2026-10-05")
        self.assertEqual(contract["fixture_sha"], FIXTURE_SHA)
        self.assertEqual(contract["eval_server_revision"], "3fdfa9387140cfc2e2aa3af415f85015f79706d2")
        self.assertEqual(contract["runner"], ".apm/skills/professor-contact/tests/runtime/"
                         + "run_issue68_stage5_routing_r19_codex.py")
        codex = contract["codex"]
        self.assertIn("sibling", codex["owner_input_isolation"])
        self.assertIn("byte for byte", codex["canonical_preservation"])
        self.assertIn("exactly once", codex["partition_evidence"])
        self.assertIn("owner_business_precedes_partition", codex["partition_evidence"])
        self.assertIn("agent_message", codex["wait_consume_evidence"])
        self.assertIn("spawnAgent relation", codex["wait_consume_evidence"])
        self.assertIn("association key only", codex["wait_consume_evidence"])
        self.assertIn("item.author equals that child's agent path", codex["wait_consume_evidence"])
        self.assertIn("message.params.turnId equals output.turn_id", codex["wait_consume_evidence"])
        self.assertIn("FINAL_ANSWER", codex["wait_consume_evidence"])
        self.assertIn("root_result_consumption_unobservable", codex["wait_consume_evidence"])
        self.assertIn("top level only", codex["wait_consume_evidence"])
        self.assertIn("child_agent_path_mapping_ambiguous", codex["wait_consume_evidence"])
        self.assertIn("root_result_receipt_ambiguous", codex["wait_consume_evidence"])
        self.assertIn("root_receipt_payload_changed", codex["wait_consume_evidence"])
        self.assertIn("receiverThreadIds/agentsStates", codex["wait_consume_evidence"])
        self.assertIn("diagnostics only", codex["wait_consume_evidence"])
        self.assertIn("never guesses a PASS", codex["wait_consume_evidence"])
        self.assertIn("subagentactivity", codex["producer_verifier_uses"][1].lower())
        self.assertIn("diagnostics only", codex["producer_verifier_uses"][3])
        self.assertIn("never downgraded", codex["terminal_precedence"])
        self.assertEqual(codex["missing_observation"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(codex["malformed_or_ambiguous_observation"], "INVALID_EVIDENCE")
        for key in ("capability_entry", "isolation_entry"):
            self.assertTrue((RUNTIME / Path(contract["preflight"][key]).name).is_file())

    def test_verifier_refuses_the_opencode_host(self):
        original = sys.argv
        sys.argv = ["verify_issue68_stage5_routing_r19.py", "--host", "opencode",
                    "--manifest", "manifest.json", "--events", "events.json",
                    "--shared-verdict", "shared.json", "--output", "verdict.json"]
        try:
            with self.assertRaises(SystemExit):
                verify.main()
        finally:
            sys.argv = original

    def test_resolve_eval_port_uses_direnv_only(self):
        """A valid direnv EVAL_PORT is the only source: it is returned as-is
        and neither a listener scan nor the instance verification runs."""
        calls = []

        def fake_check_output(argv, *args, **kwargs):
            calls.append(list(argv))
            return "17902\n"

        with unittest.mock.patch("subprocess.check_output", side_effect=fake_check_output), \
                unittest.mock.patch.object(entry, "capture_service_instance") as capture:
            self.assertEqual(entry.resolve_eval_port("/eval-server"), "17902")
        self.assertEqual(calls, [["direnv", "exec", "/eval-server", "printenv", "EVAL_PORT"]])
        capture.assert_not_called()

    def test_resolve_eval_port_refuses_to_start_without_direnv(self):
        """direnv missing means the Executable precondition is unsatisfied:
        the entry refuses to start with eval_port_unavailable instead of
        scanning listening ports."""
        def fake_check_output(argv, *args, **kwargs):
            raise FileNotFoundError("direnv is not installed")

        with unittest.mock.patch("subprocess.check_output", side_effect=fake_check_output):
            with self.assertRaises(ValueError) as caught:
                entry.resolve_eval_port("/eval-server")
        self.assertEqual(str(caught.exception), "eval_port_unavailable")

    def test_channel_declaration_matches_the_matrix(self):
        declared = set(PASS_CHANNEL) | set(FAIL_CHANNEL) | set(BLOCKED_INVALID_CHANNEL)
        methods = {name for name in dir(type(self)) if name.startswith("test_")}
        self.assertTrue(declared <= methods)
        self.assertEqual(methods, declared | set(WIRING_TESTS))


if __name__ == "__main__":
    unittest.main()
