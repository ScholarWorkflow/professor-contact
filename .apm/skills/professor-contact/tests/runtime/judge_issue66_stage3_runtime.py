"""Mechanical judge for the S3-RT-CODEX-1 runtime evidence (issue #66).

This is the single decision program required by the frozen test plan
(``issue-66-test-plan-r19-clarification-r3-2026-10-05`` §四/§六).  It folds
every required evidence surface into ONE verdict — formal delegation
attribution, the invocation-credential value chain, the per-round
prepare→validate→save→record handoff, the validator-produced raw bytes, the
REAL file-operation observation (``commandActions``), the completion-order
stop boundaries, the terminal state, and the install/fixture/storage
checks — and classifies per the frozen rules:

- attribution conflicts / version mixing / unsupported evidence shapes
  → ``INVALID_TEST_EXECUTION`` (they cannot be used to derive product
  failures);
- any attributable product contract violation → ``FAIL``;
- a real machine-level spawn failure whose stop was honored, with no other
  violation → ``BLOCKED``;
- only a complete legal run with every fact passing → ``PASS``.

Inputs (files only; the judge never talks to the network):

- ``--eval-response``   the complete /eval response (app_server_events)
- ``--adapter-output``  the @16 adapter output (formal relations +
                        child_thread_reads)
- ``--candidate-state`` the professor's committed 套磁候选状态.json
- ``--program-root``    the run's program root (Stage-4 absence check)
- ``--install-evidence`` / ``--fixture-evidence`` / ``--pre-snapshot`` /
  ``--post-snapshot``   optional: the producer verifier outputs, folded in
- ``--routing-evidence`` optional: the legacy topology verifier output,
                        folded into the unique conclusion
- ``--storage-evidence`` optional: the read-only storage ownership record

Unknown event shapes and missing required surfaces are evidence gaps —
never silent passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

GENERATOR_AGENT = "professor-contact-idea-generator"
VALIDATOR_AGENT = "professor-contact-style-validator"
LEGAL_AGENTS = {GENERATOR_AGENT, VALIDATOR_AGENT}

CANDIDATE_STATE_NAME = "套磁候选状态.json"
CANDIDATES_MD_NAME = "套磁想法候选.md"
OVERVIEW_NAME = "套磁想法候选总览.md"
INPUT_PACK_NAME = "套磁候选输入.json"

ROOT_PREPARE = "stage3-prepare-validation"
ROOT_SAVE = "stage3-save-validation"
ROOT_RECORD = "stage3-record-validation"
ROOT_REBUILD = "stage3-rebuild-overview"
CHILD_PLAN = "stage3-plan"
CHILD_FINALIZE = "stage3-finalize"

CREDENTIAL_FLAGS = ("--invocation-file", "--invocation-sha256")
SOURCE_FLAGS = ("--professor-dir", "--program-root", "--profile",
                "--refresh-scope", "--skip-direction-ids",
                "--cross-direction-groups", "--collection-key",
                "--selection", "--direction-id")
TRUNCATION_MARKER = "Warning: truncated output"

WRITE_ACTION_TYPES = {"write", "create", "delete", "move", "copy",
                      "replace", "rename", "mkdir", "rmdir"}
READ_ACTION_TYPES = {"read", "search", "listFiles"}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def final_message_bytes(item) -> bytes | None:
    content = item.get("content")
    if isinstance(content, list) and content and all(
            isinstance(block, dict) and block.get("type") == "output_text"
            and isinstance(block.get("text"), str) for block in content):
        return "".join(block["text"] for block in content).encode("utf-8")
    if isinstance(item.get("text"), str):
        return item["text"].encode("utf-8")
    return None


def extract_flag_value(command: str, flag: str) -> str | None:
    """The actual parsed argument value of one flag occurrence."""
    match = re.search(re.escape(flag) + r"\s+(\"[^\"]+\"|\S+)", command)
    if not match:
        return None
    return match.group(1).strip("\"")


class RunModel:
    """Ordered evidence extracted from the raw event stream + adapter."""

    def __init__(self, response: dict, adapter: dict):
        self.gaps: list[str] = []
        self.root_id = (response.get("output") or {}).get("thread_id")
        self.events = ((response.get("output") or {}).get(
            "app_server_events") or [])
        self.run_completed = any(
            (e.get("message") or {}).get("method") == "turn/completed"
            for e in self.events)
        # -- formal relations (adapter) ------------------------------------
        relations = (adapter.get("dispatch") or {}).get(
            "thread_relations", [])
        self.relations = relations
        self.child_reads = ((adapter.get("child_thread_reads") or {})
                            .get("entries") or [])
        self.read_roles = {entry.get("thread_id"):
                           entry.get("effective_role")
                           for entry in self.child_reads}
        self.delegation_state = (adapter.get("delegation") or {}).get("state")
        self.adapter_children = (adapter.get("delegation") or {}).get(
            "child_thread_ids") or []
        # -- spawns observed on the root thread ----------------------------
        self.spawns = []
        self.spawn_outputs = {}
        for index, event in enumerate(self.events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if item.get("type") == "function_call" \
                    and item.get("name") == "spawn_agent" \
                    and params.get("threadId") == self.root_id:
                try:
                    arguments = json.loads(item.get("arguments") or "{}")
                except json.JSONDecodeError:
                    self.gaps.append(
                        f"event {index}: spawn_agent arguments unparsable")
                    arguments = {}
                self.spawns.append({
                    "index": index, "call_id": item.get("call_id"),
                    "agent_type": arguments.get("agent_type"),
                    "task_name": arguments.get("task_name")})
            if item.get("type") == "function_call_output" \
                    and params.get("threadId") == self.root_id \
                    and item.get("call_id"):
                self.spawn_outputs[item["call_id"]] = self._output_text(item)
        # -- subAgentActivity: call_id -> agent thread ids ------------------
        self.activity_children = {}
        for index, event in enumerate(self.events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if item.get("type") == "subAgentActivity" \
                    and item.get("kind") in ("started", "completed"):
                call_id, thread_id = item.get("id"), item.get("agentThreadId")
                if call_id and thread_id:
                    self.activity_children.setdefault(
                        call_id, set()).add(thread_id)
        # -- per-thread execs with REAL operation actions -------------------
        self.execs = {}
        for index, event in enumerate(self.events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if item.get("type") != "commandExecution":
                continue
            thread_id = params.get("threadId")
            if not thread_id:
                self.gaps.append(
                    f"event {index}: commandExecution without threadId")
                continue
            output = item.get("aggregatedOutput")
            record = {
                "index": index,
                "command": item.get("command") or "",
                "output": output,
                "exit_code": item.get("exitCode"),
                "status": item.get("status"),
                "truncated": bool(output and TRUNCATION_MARKER in output),
                "actions": [
                    {"type": action.get("type"),
                     "path": action.get("path"),
                     "command": action.get("command")}
                    for action in item.get("commandActions") or []
                    if isinstance(action, dict)],
            }
            bucket = self.execs.setdefault(thread_id, [])
            if bucket and bucket[-1]["command"] == record["command"] \
                    and bucket[-1]["status"] == "inProgress" \
                    and record["status"] == "completed":
                bucket[-1] = record
            else:
                bucket.append(record)
        # -- assistant business messages per thread --------------------------
        self.assistant_messages = {}
        self.unsupported_shapes = {}
        for index, event in enumerate(self.events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if message.get("method") != "rawResponseItem/completed" \
                    or item.get("type") != "message" \
                    or item.get("role") != "assistant":
                continue
            thread_id = params.get("threadId")
            raw = final_message_bytes(item)
            if raw is None:
                self.unsupported_shapes[thread_id] = \
                    self.unsupported_shapes.get(thread_id, 0) + 1
                self.gaps.append(
                    f"event {index}: unsupported message shape on "
                    f"{thread_id}")
                continue
            self.assistant_messages.setdefault(
                thread_id, []).append({"index": index, "bytes": raw})

    @staticmethod
    def _output_text(item) -> str:
        blocks = item.get("output")
        if isinstance(blocks, list):
            return "".join(
                block.get("text", "") if isinstance(block, dict) else ""
                for block in blocks)
        if isinstance(blocks, str):
            return blocks
        return ""

    def ordered_children(self):
        ordered = []
        for spawn in self.spawns:
            targets = sorted(self.activity_children.get(
                spawn["call_id"]) or [])
            ordered.append((spawn, targets[0] if targets else None))
        return ordered

    def last_completion_index(self, thread_id, default=-1):
        entries = self.assistant_messages.get(thread_id) or []
        execs = self.execs.get(thread_id) or []
        candidates = [e["index"] for e in entries] + \
                     [e["index"] for e in execs if e["status"] == "completed"]
        return max(candidates, default=default)


class Judge:
    def __init__(self, model: RunModel, candidate_state, program_root,
                 surfaces: dict):
        self.m = model
        self.state = candidate_state
        self.program_root = program_root
        self.surfaces = surfaces          # install/fixture/routing/pre/post/storage
        self.rows: list[dict] = []
        self.attribution_invalid = False

    def row(self, fact_id, verdict, detail, evidence):
        self.rows.append({"fact": fact_id, "verdict": verdict,
                          "detail": detail, "evidence": evidence})

    def flag_value(self, command, flag):
        return extract_flag_value(command, flag)

    # -- folded surfaces ---------------------------------------------------

    def judge_folded_surfaces(self):
        install = self.surfaces.get("install")
        if install is not None:
            checks = install.get("checks")
            if isinstance(checks, list):
                bad = [c for c in checks
                       if isinstance(c, dict) and not c.get("pass", True)]
                self.row("F-install", "pass" if not bad else
                         ("invalid" if bad else "gap"),
                         "producer install checks folded into the verdict",
                         [f"failed checks: {[c.get('name') for c in bad]}"
                          if bad else f"{len(checks)} checks all pass"])
            else:
                self.row("F-install", "gap",
                         "install evidence has no structured checks list",
                         [])
        fixture = self.surfaces.get("fixture")
        if fixture is not None:
            if fixture.get("manual_patch") not in (None, "no"):
                self.row("F-fixture", "fail",
                         "fixture declares manual_patch other than 'no'",
                         [f"manual_patch={fixture.get('manual_patch')}"])
            else:
                self.row("F-fixture", "pass",
                         "fixture evidence folded in (manual_patch=no)",
                         [])
        storage = self.surfaces.get("storage")
        if storage is not None:
            status = storage.get("status")
            if status == "ok":
                self.row("F-storage-ownership", "pass",
                         "storage ownership record folded in",
                         [str(storage.get("rollout_dir", ""))[:120]])
            else:
                self.row("F-storage-ownership", "gap",
                         "storage ownership record incomplete",
                         [str(storage)[:160]])
        routing = self.surfaces.get("routing")
        if routing is not None:
            classification = routing.get("classification") or \
                routing.get("status")
            if classification in ("PASS", "pass", "ok"):
                self.row("F-routing-verifier", "pass",
                         "legacy topology verifier passed (folded in)", [])
            elif classification in ("FAIL", "FAIL_PRODUCT", "fail",
                                    "failed"):
                self.row("F-routing-verifier", "fail",
                         "legacy topology verifier reported a product "
                         "failure (folded in)",
                         [str(routing.get("failed")
                              or routing.get("reason_code")
                              or classification)[:200]])
            else:
                self.row("F-routing-verifier", "gap",
                         f"legacy topology verifier classification: "
                         f"{classification}",
                         [])
        pre = self.surfaces.get("pre")
        post = self.surfaces.get("post")
        if pre is not None and post is not None:
            self.row("F-stage4-absence", "pass" if not self._stage4_files()
                     else "fail",
                     "Stage-4 selection / mail-input artifacts absent",
                     self._stage4_files() or [])

    def _stage4_files(self):
        found = []
        if self.program_root is not None:
            for pattern in ("套磁选择.json", "邮件输入.json"):
                found.extend(str(p) for p in self.program_root.rglob(pattern))
        return found

    # -- fix 1: formal attribution -----------------------------------------

    def judge_attribution(self):
        m = self.m
        problems = []
        invalid = []
        # every formal relation must originate at this root
        for relation in m.relations:
            sender = relation.get("sender_thread_id")
            if sender != m.root_id:
                invalid.append(
                    f"relation {relation.get('call_id')}: sender {sender} "
                    f"is not this root (extra nesting or foreign origin)")
        # same-name self-delegation via diagnostic roles
        for relation in m.relations:
            sender = relation.get("sender_thread_id")
            for receiver in relation.get("receiver_thread_ids") or []:
                if m.read_roles.get(sender) and \
                        m.read_roles.get(sender) == m.read_roles.get(receiver):
                    problems.append(
                        f"relation {relation.get('call_id')}: same-name "
                        f"self-delegation ({m.read_roles.get(sender)})")
        # spawn → activity → formal relation linkage
        relation_by_call = {r.get("call_id"): r for r in m.relations}
        conflicts = []
        for spawn in m.spawns:
            targets = m.activity_children.get(spawn["call_id"]) or set()
            if len(targets) > 1:
                conflicts.append(
                    f"spawn {spawn['call_id']}: subAgentActivity maps to "
                    f"{len(targets)} threads")
            relation = relation_by_call.get(spawn["call_id"])
            if targets and relation is None:
                invalid.append(
                    f"spawn {spawn['call_id']}: observed child {targets} "
                    f"has no formal adapter relation")
            if relation is not None:
                receivers = set(relation.get("receiver_thread_ids") or [])
                if not receivers & targets and targets:
                    invalid.append(
                        f"spawn {spawn['call_id']}: formal relation does "
                        f"not confirm the observed child")
        # attribution conflict anywhere → unattributable evidence
        if conflicts:
            self.attribution_invalid = True
        ordered = m.ordered_children()
        agent_sequence = [spawn["agent_type"] for spawn, _ in ordered]
        legal = [[GENERATOR_AGENT, VALIDATOR_AGENT],
                 [GENERATOR_AGENT, VALIDATOR_AGENT, GENERATOR_AGENT,
                  VALIDATOR_AGENT]]
        detail = []
        machine_prefix = False
        for position, (spawn, child) in enumerate(ordered):
            if child is None:
                output = m.spawn_outputs.get(spawn["call_id"]) or ""
                detail.append(
                    f"event {spawn['index']}: spawn produced no child; "
                    f"machine output: {output[:160]!r}")
                if position == len(ordered) - 1:
                    machine_prefix = True
            else:
                detail.append(f"event {spawn['index']}: child {child}")
        bad_agents = [s for s in m.spawns
                      if s["agent_type"] not in LEGAL_AGENTS]
        if bad_agents:
            problems.append(
                f"spawn target outside the two legal named agents: "
                f"{[s['agent_type'] for s in bad_agents]}")
        else:
            legal_prefix = any(
                legal_seq[:len(agent_sequence)] == agent_sequence
                for legal_seq in legal)
            if agent_sequence in legal:
                pass
            elif machine_prefix and legal_prefix:
                # a legal path cut short by a machine-level failure: judged
                # as a failure prefix, never as a contract violation.
                pass
            else:
                problems.append(
                    f"spawn sequence {agent_sequence} violates the fixed "
                    f"2/4 state machine")
        if invalid:
            self.attribution_invalid = True
        evidence = detail + [f"relations: {len(m.relations)}; "
                             f"child_reads: {len(m.child_reads)}; "
                             f"delegation state: {m.delegation_state}"]
        if invalid or conflicts:
            self.row("F-attribution", "invalid",
                     "formal attribution conflicts or gaps make the "
                     "delegation facts unattributable", invalid + conflicts)
        elif problems:
            self.row("F-attribution", "fail",
                     "formal delegation attribution violated", problems +
                     evidence)
        elif not m.spawns and m.run_completed:
            self.row("F-attribution", "fail",
                     "zero real delegation with a complete run record",
                     ["the root never attempted spawn_agent; delegation "
                      "absence is a product violation, not a blocker"])
        elif machine_prefix and not problems:
            self.row("F-attribution", "machine_failure_prefix",
                     "spawn sequence stopped at a machine-level failure",
                     evidence)
        else:
            self.row("F-attribution", "pass",
                     "every formal relation originates at this root and "
                     "matches the observed spawn order",
                     [f"spawn order: {agent_sequence}"])

    # -- fix 2: credential value chain --------------------------------------

    def _generator_children(self):
        return [child for spawn, child in self.m.ordered_children()
                if child and spawn["agent_type"] == GENERATOR_AGENT]

    def _child_exec(self, child, needle):
        for record in self.m.execs.get(child, []):
            if needle in record["command"]:
                return record
        return None

    def _root_exec(self, needle, after=0):
        for record in self.m.execs.get(self.m.root_id, []):
            if record["index"] >= after and needle in record["command"]:
                return record
        return None

    @staticmethod
    def _json_from_output(output):
        if not output:
            return None, "missing"
        if TRUNCATION_MARKER in output:
            return None, "truncated"
        start = output.find("{")
        if start < 0:
            return None, "no json"
        try:
            return json.loads(output[start:]), "ok"
        except json.JSONDecodeError:
            return None, "unparsable"

    def judge_credential_chain(self):
        m = self.m
        children = self._generator_children()
        if not children:
            machine_prefix = any(child is None
                                 for _, child in m.ordered_children())
            if machine_prefix:
                self.row("F-credential-chain", "gap",
                         "machine-level spawn failure before any generator "
                         "child ran", [])
            else:
                self.row("F-credential-chain", "fail",
                         "no stage3-plan/finalize exec in any generator "
                         "child", [f"children: {children}"])
            return
        capture = self._child_exec(children[0], "--capture-invocation")
        if capture is None:
            self.row("F-credential-chain", "fail",
                     "the first stage3-plan did not capture an invocation "
                     "credential", [])
            return
        cap_payload, cap_state = self._json_from_output(capture["output"])
        if cap_state != "ok" or not isinstance(cap_payload, dict) \
                or not cap_payload.get("invocation_file") \
                or not cap_payload.get("invocation_sha256"):
            self.row("F-credential-chain", "gap",
                     f"capture exec output {cap_state} — the credential "
                     f"value chain cannot be verified",
                     [f"event {capture['index']}"])
            return
        real_file = cap_payload["invocation_file"]
        real_sha = cap_payload["invocation_sha256"]
        problems = []
        consumption = []
        for child in children:
            for record in m.execs.get(child, []):
                command = record["command"]
                if CHILD_PLAN not in command and CHILD_FINALIZE not in command:
                    continue
                if "--capture-invocation" in command:
                    continue
                consumption.append((child, record))
                for flag, real in ((CREDENTIAL_FLAGS[0], real_file),
                                   (CREDENTIAL_FLAGS[1], real_sha)):
                    used = self.flag_value(command, flag)
                    if used is None:
                        problems.append(
                            f"event {record['index']}: {flag} missing")
                    elif used != real:
                        problems.append(
                            f"event {record['index']}: {flag} value drifts "
                            f"from the captured credential")
                replayed = [f for f in SOURCE_FLAGS if f in command]
                if replayed:
                    problems.append(
                        f"event {record['index']}: source parameters "
                        f"replayed alongside the credential: {replayed}")
        corrections = [command for _, r in consumption
                       for command in [r["command"]]
                       if "--validation-file" in command]
        if len(children) >= 2 and not corrections:
            problems.append("the correction round did not consume a "
                            "recorded validation file")
        finalize_execs = [r for _, r in consumption
                          if CHILD_FINALIZE in r["command"]]
        if not finalize_execs:
            problems.append("the first commit (stage3-finalize) never ran "
                            "in the generator child")
        self.credential_values = {"file": real_file, "sha": real_sha}
        if problems:
            self.row("F-credential-chain", "fail",
                     "the captured credential values were not consumed "
                     "verbatim", problems)
        else:
            self.row("F-credential-chain", "pass",
                     "first-round capture and verbatim credential "
                     "consumption verified against actual return values",
                     [f"invocation_file={real_file}", f"{len(consumption)} "
                      f"consumption exec(s)"])

    # -- fix 3+2: per-round handoff chain with actual values -----------------

    def judge_handoff_chain(self):
        m = self.m
        validator_children = [child for spawn, child in m.ordered_children()
                              if child and spawn["agent_type"]
                              == VALIDATOR_AGENT]
        if not validator_children:
            self.row("F-handoff-chain", "gap",
                     "no completed validator child to judge the handoff on",
                     [])
            self.rounds = []
            return
        cursor = 0
        problems = []
        rounds = []
        self.chain_gaps = []
        for round_no, child in enumerate(validator_children, start=1):
            prepare = self._root_exec(ROOT_PREPARE, after=cursor)
            if prepare is None or \
                    f"--round {round_no}" not in prepare["command"]:
                problems.append(
                    f"round {round_no}: no root prepare exec with --round "
                    f"{round_no} before the validator child")
                break
            prep_payload, prep_state = self._json_from_output(
                prepare["output"])
            if prep_state != "ok" or not isinstance(prep_payload, dict):
                self.chain_gaps.append(
                    f"round {round_no}: prepare output {prep_state} — "
                    f"handoff values unverifiable")
                break
            handoff_file = prep_payload.get("handoff_file")
            handoff_sha = prep_payload.get("handoff_sha256")
            output_file = prep_payload.get("output_file")
            if not all((handoff_file, handoff_sha, output_file)):
                problems.append(
                    f"round {round_no}: prepare output misses handoff "
                    f"file/sha/output_file values")
                break
            spawn_index = next(spawn["index"] for spawn, c
                               in m.ordered_children() if c == child)
            if prepare["index"] > spawn_index:
                problems.append(
                    f"round {round_no}: prepare completed after the "
                    f"validator spawn (event {prepare['index']} > "
                    f"{spawn_index})")
            save = self._root_exec(ROOT_SAVE, after=spawn_index)
            if save is None:
                problems.append(f"round {round_no}: no root save exec after "
                                f"the validator child")
                break
            for flag, real in (("--handoff-file", handoff_file),
                               ("--handoff-sha256", handoff_sha)):
                used = self.flag_value(save["command"], flag)
                if used != real:
                    problems.append(
                        f"round {round_no}: save {flag} drifts from the "
                        f"prepare return value")
            save_payload, save_state = self._json_from_output(
                save["output"])
            if save_state != "ok" or not isinstance(save_payload, dict) \
                    or not save_payload.get("validation_sha256"):
                self.chain_gaps.append(
                    f"round {round_no}: save output {save_state} — digest "
                    f"unverifiable")
                break
            validation_file = save_payload.get("validation_file")
            record = self._root_exec(ROOT_RECORD, after=save["index"])
            if record is None or self.flag_value(
                    record["command"], "--expected-validation-sha256") \
                    != save_payload["validation_sha256"]:
                problems.append(
                    f"round {round_no}: record exec missing or its "
                    f"expected digest is not the save return value")
                break
            used_handoff = self.flag_value(record["command"],
                                           "--handoff-file")
            if used_handoff != handoff_file:
                problems.append(
                    f"round {round_no}: record --handoff-file drifts from "
                    f"the prepare return value")
            record_payload, record_state = self._json_from_output(
                record["output"])
            if record_state != "ok" or not isinstance(record_payload, dict):
                self.chain_gaps.append(
                    f"round {round_no}: record output {record_state}")
                break
            rounds.append({
                "round": round_no, "child": child, "prepare": prepare,
                "save": save, "record": record, "output_file": output_file,
                "validation_file": validation_file,
                "save_payload": save_payload,
                "record_payload": record_payload})
            cursor = record["index"]
        # correction rounds must consume the recorded validation file
        if len(self._generator_children()) >= 2 and rounds:
            recorded = rounds[0]["validation_file"]
            correction_ok = any(
                recorded and recorded in r["command"]
                for r in m.execs.get(self._generator_children()[-1], [])
                if CHILD_PLAN in r["command"])
            if not correction_ok:
                problems.append(
                    "the correction plan did not consume the round-1 "
                    "recorded validation file")
        if problems:
            self.row("F-handoff-chain", "fail",
                     "the handoff chain or its actual values are broken",
                     problems)
        else:
            self.row("F-handoff-chain", "pass",
                     f"{len(rounds)} round(s) followed the fixed chain with "
                     f"verbatim prepare/save/record values",
                     [f"round {r['round']}: events "
                      f"{r['prepare']['index']}→{r['record']['index']}"
                      for r in rounds])
        self.rounds = rounds

    # -- fix 3: validator-produced original ---------------------------------

    def judge_raw_original(self):
        rounds = getattr(self, "rounds", [])
        if not rounds:
            self.row("F-raw-original", "gap",
                     "no completed handoff round to judge raw production",
                     [])
            return
        problems = []
        gapped = False
        rows = []
        for entry in rounds:
            child = entry["child"]
            if self.m.unsupported_shapes.get(child):
                gapped = True
                rows.append(f"round {entry['round']}: unsupported final "
                            f"message shape on the validator child")
                continue
            messages = self.m.assistant_messages.get(child) or []
            if len(messages) != 1:
                problems.append(
                    f"round {entry['round']}: the validator child sent "
                    f"{len(messages)} assistant business messages (exactly "
                    f"one required)")
                continue
            msg_sha = sha256_bytes(messages[0]["bytes"])
            save_sha = entry["save_payload"].get("validation_sha256")
            record_sha = entry["record_payload"].get(
                "validation_input_sha256")
            # producer evidence: a real write of the assigned output file
            # inside the child window, before the root save completed.
            produced = self._production_evidence(entry)
            if produced is None:
                gapped = True
                rows.append(f"round {entry['round']}: no file-operation "
                            f"observation for the validator window")
                continue
            if not produced:
                problems.append(
                    f"round {entry['round']}: no validator-window write of "
                    f"the assigned output file (root could have rebuilt "
                    f"the source)")
                continue
            if msg_sha == save_sha == record_sha:
                rows.append(f"round {entry['round']}: {msg_sha} "
                            f"(message == save == record, producer verified)")
            else:
                problems.append(
                    f"round {entry['round']}: MISMATCH msg={msg_sha} "
                    f"save={save_sha} record={record_sha}")
            # the root must not touch the source outside the save entry
            root_rewrite = self._root_source_rewrite(entry)
            if root_rewrite:
                problems.append(
                    f"round {entry['round']}: root window writes the "
                    f"validator source outside the save entry "
                    f"({root_rewrite})")
        if problems:
            self.row("F-raw-original", "fail",
                     "raw validator production or integrity violated",
                     problems + rows)
        elif gapped:
            self.row("F-raw-original", "gap",
                     "raw production not judgeable from the captured "
                     "observations", rows)
        else:
            self.row("F-raw-original", "pass",
                     "each round: one business message, real validator "
                     "production, byte-identical save and record",
                     rows)

    def _production_evidence(self, entry):
        """True/False/None: real write of output_file in the child window."""
        child = entry["child"]
        output_file = entry.get("output_file")
        if not output_file:
            return None
        actions_seen = False
        for record in self.m.execs.get(child, []):
            for action in record["actions"]:
                if action.get("type") in READ_ACTION_TYPES:
                    continue
                actions_seen = True
                path = action.get("path")
                if path and Path(path) == Path(output_file):
                    return True
        if not actions_seen:
            return None
        return False

    def _root_source_rewrite(self, entry):
        """Real root-window writes touching the validator source/output."""
        output_file = entry.get("output_file") or ""
        validation_file = entry.get("validation_file") or ""
        spawn_index = next(
            (spawn["index"] for spawn, c in self.m.ordered_children()
             if c == entry["child"]), -1)
        hits = []
        for record in self.m.execs.get(self.m.root_id, []):
            if record["index"] <= spawn_index \
                    or record["index"] >= entry["record"]["index"]:
                continue
            if ROOT_SAVE in record["command"] \
                    or ROOT_RECORD in record["command"] \
                    or ROOT_PREPARE in record["command"]:
                continue
            for action in record["actions"]:
                if action.get("type") in READ_ACTION_TYPES | {"unknown"}:
                    continue
                path = action.get("path") or ""
                if output_file and Path(path) == Path(output_file):
                    hits.append(f"event {record['index']}: {path}")
                if validation_file \
                        and Path(path) == Path(validation_file):
                    hits.append(f"event {record['index']}: {path}")
        return hits

    # -- fix 4: real file-operation write scope ------------------------------

    def judge_write_scope(self):
        rounds = getattr(self, "rounds", [])
        if not rounds:
            self.row("F-validator-write-scope", "gap",
                     "no validator child to judge the write scope on", [])
            return
        problems = []
        observed = []
        for entry in rounds:
            child = entry["child"]
            output_file = entry.get("output_file") or ""
            actions_seen = False
            for record in self.m.execs.get(child, []):
                for action in record["actions"]:
                    atype = action.get("type")
                    if atype in READ_ACTION_TYPES:
                        continue
                    actions_seen = True
                    path = action.get("path")
                    if atype == "unknown" and not path:
                        continue
                    observed.append(
                        f"round {entry['round']} event {record['index']}: "
                        f"{atype} {path}")
                    if not path:
                        continue
                    if Path(path) != Path(output_file):
                        problems.append(
                            f"round {entry['round']} event "
                            f"{record['index']}: {atype} on {path} — "
                            f"outside the assigned output file")
            if not actions_seen:
                self.row("F-validator-write-scope", "gap",
                         f"round {entry['round']}: no file-operation "
                         f"observation on the validator child; write "
                         f"compliance not judgeable",
                         observed)
                return
        if problems:
            self.row("F-validator-write-scope", "fail",
                     "the validator wrote outside its assigned output file",
                     problems)
        else:
            self.row("F-validator-write-scope", "pass",
                     "every real write operation in the validator windows "
                     "targets the assigned output file only", observed)

    # -- fix 5: completion order, stop boundaries, terminal ------------------

    def judge_stop_order(self):
        m = self.m
        rounds = getattr(self, "rounds", [])
        problems = []
        records = {entry["round"]: entry["record"] for entry in rounds}
        last_record = max((r["index"] for r in records.values()), default=-1)
        # No completed-child spawn after the final record, except the legal
        # correction generator dispatched by a needs_correction=true record.
        terminal_records = [entry for entry in rounds
                            if (entry["record_payload"] or {}).get(
                                "needs_correction") is False]
        for spawn, child in m.ordered_children():
            if child is None:
                continue  # machine-failed spawns are judged by attribution
            if terminal_records and spawn["index"] > min(
                    entry["record"]["index"] for entry in terminal_records):
                problems.append(
                    f"event {spawn['index']}: spawn after the terminal "
                    f"record (no third generator / no post-terminal "
                    f"validator)")
        # The correction generator may only be dispatched after the round-1
        # record completed with needs_correction=true.
        if len(rounds) >= 2:
            generator_children = self._generator_children()
            if generator_children:
                correction_child = generator_children[-1]
                correction_spawn = next(
                    (spawn for spawn, child in m.ordered_children()
                     if child == correction_child), None)
                record1 = rounds[0]["record"]
                if correction_spawn is not None and \
                        correction_spawn["index"] < record1["index"]:
                    problems.append(
                        f"the correction generator spawned (event "
                        f"{correction_spawn['index']}) before the round-1 "
                        f"record completed (event {record1['index']})")
                if correction_spawn is not None:
                    needs = (rounds[0]["record_payload"] or {}).get(
                        "needs_correction")
                    if needs is not True:
                        problems.append(
                            f"the correction generator was dispatched "
                            f"although round 1 needs_correction={needs!r}")
        self.row("F-stop-order", "fail" if problems else "pass",
                 "stop boundaries" + (" violated" if problems else
                                      " honored"),
                 problems or [f"last record event {last_record}"])

    def judge_terminal_state(self):
        state = self.state
        attribution = {row["fact"]: row["verdict"] for row in self.rows}.get(
            "F-attribution")
        if attribution == "machine_failure_prefix":
            self.row("F-terminal-state", "gap",
                     "the run stopped at a machine-level failure prefix; "
                     "no terminal state is required", [])
            return
        if not isinstance(state, dict):
            self.row("F-terminal-state", "gap",
                     "candidate state unreadable or missing", [])
            return
        validator = state.get("validator")
        if not isinstance(validator, dict):
            self.row("F-terminal-state", "fail",
                     "no validator record in the committed state",
                     ["Stage 3 without a terminal validator record is "
                      "incomplete"])
            return
        results = validator.get("results") or {}
        if not results:
            self.row("F-terminal-state", "fail",
                     "validator record carries no per-direction results",
                     [])
            return
        problems = []
        for direction, entry in results.items():
            result = entry.get("result")
            rounds_value = entry.get("rounds")
            if result == "pass":
                if rounds_value not in (1, 2):
                    problems.append(
                        f"{direction}: pass with rounds={rounds_value!r} "
                        f"(must be 1 or 2)")
            elif result == "fail_after_2_rounds":
                if rounds_value != 2:
                    problems.append(
                        f"{direction}: fail_after_2_rounds with "
                        f"rounds={rounds_value!r} (must be 2)")
            else:
                problems.append(
                    f"{direction}: non-terminal result {result!r}")
        if problems:
            self.row("F-terminal-state", "fail",
                     "the terminal record is missing, non-terminal or "
                     "violates the round bookkeeping", problems)
            return
        self.row("F-terminal-state", "pass",
                 "terminal validator record with correct round bookkeeping",
                 [f"{k}: {v.get('result')} rounds={v.get('rounds')}"
                  for k, v in results.items()])

    def judge_rebuild_and_finalize(self):
        m = self.m
        root_execs = m.execs.get(m.root_id, [])
        rebuilds = [r for r in root_execs if ROOT_REBUILD in r["command"]]
        records = [entry["record"] for entry in getattr(self, "rounds", [])]
        last_record = max((r["index"] for r in records), default=-1)
        attribution = {row["fact"]: row["verdict"] for row in self.rows}.get(
            "F-attribution")
        if attribution == "machine_failure_prefix" or last_record < 0 \
                and not rebuilds:
            self.row("F-rebuild", "gap",
                     "the run stopped at a machine-level failure prefix; "
                     "the terminal rebuild was never reached", [])
            return
        problems = []
        if len(rebuilds) != 1:
            problems.append(f"expected exactly one rebuild exec, saw "
                            f"{len(rebuilds)}")
        elif rebuilds[0]["index"] < last_record:
            problems.append(
                f"rebuild (event {rebuilds[0]['index']}) ran before the "
                f"terminal record (event {last_record})")
        for thread_id, records_ in m.execs.items():
            for r in records_:
                if CHILD_FINALIZE in r["command"] and r["index"] > last_record >= 0:
                    problems.append(
                        f"finalize ran after the terminal record: event "
                        f"{r['index']} on {thread_id[:8]}")
        if problems:
            self.row("F-rebuild", "fail",
                     "terminal rebuild / no-finalize-after violated",
                     problems)
        else:
            self.row("F-rebuild", "pass",
                     "exactly one rebuild after the terminal record; no "
                     "finalize afterwards",
                     [f"rebuild event {rebuilds[0]['index']}"] if rebuilds
                     else [])

    # -- entry --------------------------------------------------------------

    def run(self) -> dict:
        self.judge_folded_surfaces()
        self.judge_attribution()
        self.judge_credential_chain()
        self.judge_handoff_chain()
        self.judge_raw_original()
        self.judge_write_scope()
        self.judge_stop_order()
        self.judge_terminal_state()
        self.judge_rebuild_and_finalize()

        gaps = self.m.gaps or []
        gap_rows = [row for row in self.rows
                    if row["verdict"] == "gap"]
        invalid_rows = [row for row in self.rows
                        if row["verdict"] == "invalid"]
        failures = [row for row in self.rows if row["verdict"] == "fail"]
        machine_prefix = [row for row in self.rows
                          if row["verdict"] == "machine_failure_prefix"]

        if self.attribution_invalid or invalid_rows:
            classification = "INVALID_TEST_EXECUTION"
            reason = ("formal attribution conflicts or invalid evidence — "
                      "product failures cannot be derived")
        elif failures:
            classification = "FAIL"
            reason = "; ".join(row["fact"] for row in failures)
        elif machine_prefix:
            classification = "BLOCKED"
            reason = "machine-level spawn failure with the stop honored"
        elif gaps or gap_rows:
            classification = "INVALID_TEST_EXECUTION"
            reason = "evidence missing, gapped or of an unsupported shape"
        elif self.rows and all(row["verdict"] == "pass"
                               for row in self.rows):
            classification = "PASS"
            reason = "all frozen runtime facts hold"
        else:
            classification = "INVALID_TEST_EXECUTION"
            reason = "unjudgeable evidence set"
        return {
            "schema": "issue66-runtime-judge-v2",
            "classification": classification,
            "reason": reason,
            "evidence_gaps": gaps,
            "facts": self.rows,
        }


def _load(path: str | None):
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-response", required=True)
    parser.add_argument("--adapter-output", required=True)
    parser.add_argument("--candidate-state", default=None)
    parser.add_argument("--program-root", default=None)
    parser.add_argument("--install-evidence", default=None)
    parser.add_argument("--fixture-evidence", default=None)
    parser.add_argument("--routing-evidence", default=None)
    parser.add_argument("--pre-snapshot", default=None)
    parser.add_argument("--post-snapshot", default=None)
    parser.add_argument("--storage-evidence", default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    response = _load(args.eval_response)
    adapter = _load(args.adapter_output) or {}
    if response is None:
        print("eval response unreadable", file=sys.stderr)
        return 2
    candidate_state = _load(args.candidate_state)
    program_root = Path(args.program_root) if args.program_root else None
    surfaces = {
        "install": _load(args.install_evidence),
        "fixture": _load(args.fixture_evidence),
        "routing": _load(args.routing_evidence),
        "pre": _load(args.pre_snapshot),
        "post": _load(args.post_snapshot),
        "storage": _load(args.storage_evidence),
    }
    model = RunModel(response, adapter)
    verdict = Judge(model, candidate_state, program_root, surfaces).run()
    Path(args.output).write_text(
        json.dumps(verdict, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(verdict["classification"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
