"""Mechanical judge for the S3-RT-CODEX-1 runtime evidence (issue #66 Gate 2).

The frozen recipe leaves the credential chain, the per-round handoff order,
the byte-exact raw handoff, the per-round validator write scope, the stop
order and the terminal rebuild as fixed facts that must be judged by a
deterministic program over the captured evidence — not by hand-waved tables.
This script is that program.  It consumes:

- ``--eval-response``   the complete /eval response (app_server_events stream)
- ``--adapter-output``  the shared fixture adapter output (@16 contract) for
                        the formal spawn relations
- ``--candidate-state`` the professor's committed 套磁候选状态.json
- ``--program-root``    the run's program root (Stage-4 absence check)

and emits one verdict JSON with per-fact rows.  Classification order is
fixed: evidence gaps (missing or unsupported shapes) make the whole run
``INVALID_TEST_EXECUTION``; any contract violation makes it ``FAIL``; a
machine-level spawn failure whose stop was honored and with no other
violation is ``BLOCKED``; only a complete legal run with every fact passing
is ``PASS``.  Unknown event shapes are evidence gaps, never silent passes.

The judge never talks to the network, never executes product code and never
reads anything but the files given on the command line.
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

# Root-owned runner commands (r13 §6/§7); the generator child owns plan/finalize.
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


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def final_message_bytes(item) -> bytes | None:
    """The exact UTF-8 bytes of one final assistant message item."""
    content = item.get("content")
    if isinstance(content, list) and content and all(
            isinstance(block, dict) and block.get("type") == "output_text"
            and isinstance(block.get("text"), str) for block in content):
        return "".join(block["text"] for block in content).encode("utf-8")
    if isinstance(item.get("text"), str):
        return item["text"].encode("utf-8")
    return None


class RunModel:
    """The ordered evidence model extracted from the raw event stream."""

    def __init__(self, response: dict, adapter: dict):
        self.gaps: list[str] = []
        self.root_id = (response.get("output") or {}).get("thread_id")
        events = ((response.get("output") or {}).get("app_server_events")
                  or [])
        self.events = events
        # --- spawns: ordered function_call spawn_agent items on the root ---
        self.spawns = []          # {index, agent_type, call_id, arguments}
        self.spawn_outputs = {}   # call_id -> raw output text (function_call_output)
        child_ids = set()
        for relation in (adapter.get("dispatch") or {}).get(
                "thread_relations", []):
            for receiver in relation.get("receiver_thread_ids") or []:
                child_ids.add(receiver)
        self.adapter_children = (adapter.get("delegation") or {}).get(
            "child_thread_ids") or []
        self.formal_child_count = (adapter.get("delegation") or {}).get(
            "formal_child_count")
        delegation_state = (adapter.get("delegation") or {}).get("state")
        self.delegation_state = delegation_state
        for index, event in enumerate(events):
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
                        f"event {index}: spawn_agent arguments are not JSON")
                    arguments = {}
                self.spawns.append({
                    "index": index,
                    "call_id": item.get("call_id"),
                    "agent_type": arguments.get("agent_type"),
                    "task_name": arguments.get("task_name"),
                })
            if item.get("type") == "function_call_output" \
                    and params.get("threadId") == self.root_id:
                call_id = item.get("call_id")
                if call_id:
                    self.spawn_outputs[call_id] = self._output_text(item)
        # --- subAgentActivity: call_id -> child thread id ---
        self.activity_child = {}
        for index, event in enumerate(events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if item.get("type") == "subAgentActivity" \
                    and item.get("kind") in ("started", "completed"):
                call_id = item.get("id")
                thread_id = item.get("agentThreadId")
                if call_id and thread_id:
                    self.activity_child.setdefault(call_id, thread_id)
        # --- per-thread ordered exec commands (completed form wins) ---
        self.execs = {}   # thread_id -> [{index, command, output, exit_code, truncated}]
        for index, event in enumerate(events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if item.get("type") != "commandExecution":
                continue
            thread_id = params.get("threadId")
            if not thread_id:
                self.gaps.append(f"event {index}: commandExecution without threadId")
                continue
            output = item.get("aggregatedOutput")
            bucket = self.execs.setdefault(thread_id, [])
            record = {
                "index": index,
                "command": item.get("command") or "",
                "output": output,
                "exit_code": item.get("exitCode"),
                "status": item.get("status"),
                "truncated": bool(output and TRUNCATION_MARKER in output),
            }
            if bucket and bucket[-1]["command"] == record["command"] \
                    and bucket[-1]["status"] == "inProgress" \
                    and record["status"] == "completed":
                bucket[-1] = record          # completed form supersedes
            else:
                bucket.append(record)
        # --- per-thread final assistant message ---
        self.final_messages = {}  # thread_id -> {index, bytes}
        for index, event in enumerate(events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if message.get("method") != "rawResponseItem/completed" \
                    or item.get("type") != "message" \
                    or item.get("role") != "assistant":
                continue
            thread_id = params.get("threadId")
            if not thread_id:
                continue
            raw = final_message_bytes(item)
            if raw is None:
                self.gaps.append(
                    f"event {index}: unsupported final message shape on "
                    f"{thread_id}")
                continue
            self.final_messages[thread_id] = {"index": index, "bytes": raw}
        # --- per-thread first user message (the delegation payload) ---
        self.child_prompts = {}   # thread_id -> str
        for index, event in enumerate(events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if item.get("type") in ("userMessage", "message") \
                    and item.get("role") in (None, "user"):
                thread_id = params.get("threadId")
                text = item.get("text")
                if thread_id and thread_id != self.root_id \
                        and isinstance(text, str) \
                        and thread_id not in self.child_prompts:
                    self.child_prompts[thread_id] = text

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
        """Child thread ids in spawn order (machine-observed)."""
        ordered = []
        for spawn in self.spawns:
            child = self.activity_child.get(spawn["call_id"])
            ordered.append((spawn, child))
        return ordered


class Judge:
    def __init__(self, model: RunModel, candidate_state: dict | None,
                 program_root: Path | None):
        self.m = model
        self.state = candidate_state
        self.program_root = program_root
        self.rows: list[dict] = []

    def row(self, fact_id, verdict, detail, evidence):
        self.rows.append({"fact": fact_id, "verdict": verdict,
                          "detail": detail, "evidence": evidence})

    # -- facts -------------------------------------------------------------

    def judge_topology(self):
        m = self.m
        spawns = m.spawns
        bad = [s for s in spawns if s["agent_type"] not in LEGAL_AGENTS]
        if bad:
            self.row("F-topology-roles", "fail",
                     "spawn target outside the two legal named agents",
                     [f"event {s['index']}: agent_type={s['agent_type']}"
                      for s in bad])
            return
        pattern = [s["agent_type"] for s in spawns]
        legal = [[GENERATOR_AGENT, VALIDATOR_AGENT],
                 [GENERATOR_AGENT, VALIDATOR_AGENT, GENERATOR_AGENT,
                  VALIDATOR_AGENT]]
        if pattern in legal:
            self.row("F-topology-roles", "pass",
                     f"{len(spawns)} direct children in the legal order",
                     [f"spawn order: {pattern}"])
            return
        # failure prefix: a spawn whose call produced no child and an error
        # output, with no further spawn after it.
        prefix_ok = True
        detail = []
        for position, spawn in enumerate(spawns):
            child = m.activity_child.get(spawn["call_id"])
            if child is None:
                output = m.spawn_outputs.get(spawn["call_id"]) or ""
                if position != len(spawns) - 1:
                    prefix_ok = False
                detail.append(
                    f"event {spawn['index']}: spawn produced no child; "
                    f"machine output: {output[:160]!r}")
            else:
                detail.append(f"event {spawn['index']}: child {child}")
        if spawns and prefix_ok and m.delegation_state != "confirmed":
            self.row("F-topology-roles", "machine_failure_prefix",
                     "spawn sequence stopped at a machine-level failure; "
                     "not a legal completion",
                     detail + [f"adapter delegation state: "
                               f"{m.delegation_state}"])
            return
        self.row("F-topology-roles", "fail",
                 "spawn sequence violates the fixed 2/4 state machine",
                 detail or ["no spawn_agent call on the root thread"])

    def judge_credential_chain(self):
        m = self.m
        generator_children = [child for spawn, child in m.ordered_children()
                              if child and spawn["agent_type"]
                              == GENERATOR_AGENT]
        plan_execs = []
        for child in generator_children:
            for record in m.execs.get(child, []):
                command = record["command"]
                if CHILD_PLAN in command or CHILD_FINALIZE in command:
                    plan_execs.append((child, record))
        if not plan_execs:
            machine_prefix = any(
                child is None for _, child in m.ordered_children())
            if machine_prefix:
                self.row("F-credential-chain", "evidence_gap",
                         "the run stopped at a machine-level spawn failure; "
                         "the credential chain was never reached",
                         [f"children: {generator_children}"])
            else:
                self.row("F-credential-chain", "fail",
                         "no stage3-plan/stage3-finalize exec in any "
                         "generator child (caller inlined the business or "
                         "never ran it)",
                         [f"children: {generator_children}"])
            return
        # The capture exec legitimately carries the source parameters it
        # freezes; every later exec must consume the credential instead.
        first = plan_execs[0][1]
        if "--capture-invocation" not in first["command"]:
            self.row("F-credential-chain", "fail",
                     "the first stage3-plan did not capture an invocation "
                     "credential",
                     [f"event {first['index']}: {first['command'][:200]}"])
            return
        problems = []
        for child, record in plan_execs[1:]:
            command = record["command"]
            if not all(flag in command for flag in CREDENTIAL_FLAGS):
                problems.append(
                    f"event {record['index']} ({child[:8]}): credential "
                    f"flags missing")
            replayed = [flag for flag in SOURCE_FLAGS if flag in command]
            if replayed:
                problems.append(
                    f"event {record['index']} ({child[:8]}): source "
                    f"parameters replayed alongside the credential: "
                    f"{replayed}")
        if problems:
            self.row("F-credential-chain", "fail",
                     "credential consumption violated",
                     problems)
            return
        corrections = [command for _, record in plan_execs
                       for command in [record["command"]]
                       if "--validation-file" in command]
        expected_corrections = 1 if len(generator_children) >= 2 else 0
        if len(corrections) < expected_corrections:
            self.row("F-credential-chain", "fail",
                     "the correction round did not consume the recorded "
                     "validation file",
                     [f"correction execs: {len(corrections)}",
                      f"expected >= {expected_corrections}"])
            return
        self.row("F-credential-chain", "pass",
                 "capture once, credential-only consumption, correction "
                 "adds only the recorded validation file",
                 [f"{len(plan_execs)} credential execs across "
                  f"{len(generator_children)} generator child(ren)"])

    def _root_exec(self, needle, after=0):
        """The first completed root exec matching needle, in event order."""
        root = self.m.root_id
        for record in self.m.execs.get(root, []):
            if record["index"] >= after and needle in record["command"]:
                return record
        return None

    @staticmethod
    def _json_from_output(output: str | None):
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

    def judge_handoff_chain(self):
        m = self.m
        validator_children = [child for spawn, child in m.ordered_children()
                              if child and spawn["agent_type"]
                              == VALIDATOR_AGENT]
        if not validator_children:
            self.row("F-handoff-chain", "evidence_gap",
                     "no validator child to judge the handoff chain on",
                     ["spawn order saw no completed validator child"])
            return
        cursor = 0
        problems = []
        rounds = []
        for round_no, child in enumerate(validator_children, start=1):
            prepare = self._root_exec(ROOT_PREPARE, after=cursor)
            if prepare is None or f"--round {round_no}" not in prepare["command"]:
                problems.append(
                    f"round {round_no}: no root prepare exec with --round "
                    f"{round_no} before the validator child")
                break
            spawn_index = next(spawn["index"] for spawn, c
                               in m.ordered_children() if c == child)
            if prepare["index"] > spawn_index:
                problems.append(
                    f"round {round_no}: prepare happened after the child "
                    f"spawn (event {prepare['index']} > {spawn_index})")
            prompt = m.child_prompts.get(child)
            if prompt is None:
                problems.append(
                    f"round {round_no}: validator child prompt not observed")
            else:
                required = ("artifact", "candidates")
                if not all(part in prompt for part in required) \
                        or "output_file" not in prompt:
                    problems.append(
                        f"round {round_no}: validator prompt misses the "
                        f"candidates path / artifact / output_file binding")
                forbidden = (CANDIDATE_STATE_NAME, OVERVIEW_NAME,
                             "invocation", "invocations",
                             INPUT_PACK_NAME)
                leaked = [token for token in forbidden if token in prompt]
                if leaked:
                    problems.append(
                        f"round {round_no}: validator prompt carries "
                        f"forbidden material: {leaked}")
            save = self._root_exec(ROOT_SAVE, after=spawn_index)
            record = self._root_exec(
                ROOT_RECORD, after=save["index"] if save else spawn_index)
            if save is None or ROOT_SAVE not in save["command"]:
                problems.append(f"round {round_no}: no root save exec after "
                                f"the validator child")
                break
            if record is None or "--expected-validation-sha256" \
                    not in record["command"]:
                problems.append(
                    f"round {round_no}: no root record exec in handoff mode "
                    f"after the save")
                break
            rounds.append({"round": round_no, "child": child,
                           "prepare": prepare, "save": save,
                           "record": record})
            cursor = record["index"]
        if problems:
            self.row("F-handoff-chain", "fail",
                     "prepare → validator → save → record chain broken",
                     problems)
        else:
            self.row("F-handoff-chain", "pass",
                     f"{len(rounds)} round(s) followed the fixed handoff "
                     f"chain with a bounded validator payload",
                     [f"round {r['round']}: events "
                      f"{r['prepare']['index']}→{r['record']['index']}"
                      for r in rounds])
        self.rounds = rounds

    def judge_four_point(self):
        rounds = getattr(self, "rounds", [])
        if not rounds:
            self.row("F-four-point-identity", "evidence_gap",
                     "no completed handoff round to compare digests on",
                     ["handoff chain did not complete"])
            return
        rows = []
        failed = False
        gapped = False
        for entry in rounds:
            child = entry["child"]
            message = self.m.final_messages.get(child)
            if message is None:
                gapped = True
                rows.append(f"round {entry['round']}: no final assistant "
                            f"message for the validator child")
                continue
            msg_sha = sha256_bytes(message["bytes"])
            save_payload, save_state = self._json_from_output(
                entry["save"]["output"])
            record_payload, record_state = self._json_from_output(
                entry["record"]["output"])
            save_sha = save_payload.get("validation_sha256") \
                if isinstance(save_payload, dict) else None
            record_sha = record_payload.get("validation_input_sha256") \
                if isinstance(record_payload, dict) else None
            if save_state != "ok" or record_state != "ok":
                gapped = True
                rows.append(
                    f"round {entry['round']}: save output {save_state}, "
                    f"record output {record_state} — digests not judgeable")
                continue
            if msg_sha == save_sha == record_sha:
                rows.append(f"round {entry['round']}: {msg_sha} (message == "
                            f"save == record)")
            else:
                failed = True
                rows.append(
                    f"round {entry['round']}: MISMATCH msg={msg_sha} "
                    f"save={save_sha} record={record_sha}")
        if gapped:
            self.row("F-four-point-identity", "evidence_gap",
                     "byte-identity not judgeable from the captured output",
                     rows)
        elif failed:
            self.row("F-four-point-identity", "fail",
                     "the raw validator bytes drifted on some round", rows)
        else:
            self.row("F-four-point-identity", "pass",
                     "every round: final message == saved bytes == recorded "
                     "digest", rows)

    def judge_write_scope(self):
        rounds = getattr(self, "rounds", [])
        if not rounds:
            self.row("F-validator-write-scope", "evidence_gap",
                     "no validator child to judge the write scope on",
                     ["handoff chain did not complete"])
            return
        problems = []
        observed = []
        write_markers = (">", ">>", "tee ", "rm ", "mv ", "cp ",
                         "open(", "O_CREAT", "O_WRONLY")
        protected = (CANDIDATE_STATE_NAME, OVERVIEW_NAME, INPUT_PACK_NAME)
        for entry in rounds:
            child = entry["child"]
            prompt = self.m.child_prompts.get(child) or ""
            match = re.search(r"output_file[\"': =]+(\S+)", prompt)
            output_file = match.group(1) if match else None
            for record in self.m.execs.get(child, []):
                command = record["command"]
                if not any(marker in command for marker in write_markers):
                    continue
                observed.append(f"round {entry['round']} event "
                                f"{record['index']}: {command[:120]}")
                hit = [name for name in protected if name in command]
                if hit:
                    problems.append(
                        f"round {entry['round']} event {record['index']}: "
                        f"write touches a protected file {hit}")
                if output_file and output_file not in command \
                        and not hit:
                    problems.append(
                        f"round {entry['round']} event {record['index']}: "
                        f"write outside the assigned output_file")
            md_hit = [record["index"] for record in
                      self.m.execs.get(child, [])
                      if CANDIDATES_MD_NAME in record["command"]
                      and any(marker in record["command"]
                              for marker in (">", "tee ", "open("))]
            if md_hit:
                problems.append(
                    f"round {entry['round']}: validator exec wrote the "
                    f"candidates markdown (events {md_hit})")
        if problems:
            self.row("F-validator-write-scope", "fail",
                     "the validator wrote outside its assigned output file",
                     problems)
        else:
            self.row("F-validator-write-scope", "pass",
                     "every validator exec write stayed on the assigned "
                     "output file",
                     observed or ["no write-capable exec on the validator "
                                  "children"])

    def _record_needs_correction(self, record_entry):
        payload, state = self._json_from_output(record_entry["output"])
        if state != "ok" or not isinstance(payload, dict):
            return None
        return payload.get("needs_correction")

    def judge_stop_order(self):
        m = self.m
        ordered = m.ordered_children()
        problems = []
        rounds = getattr(self, "rounds", [])
        records = {entry["round"]: entry["record"] for entry in rounds}
        # No spawn after the last record (no third generator, no V2 after a
        # failed G2 — the pattern check in topology covers the sequence, this
        # covers the ordering against the record results).
        last_record = max((r["index"] for r in records.values()), default=-1)
        for spawn, child in ordered:
            if child is not None and spawn["index"] > last_record >= 0:
                problems.append(
                    f"event {spawn['index']}: spawn after the last record "
                    f"(event {last_record})")
        if len(ordered) >= 4:
            record1 = self._record_needs_correction(records.get(1)) \
                if 1 in records else None
            if record1 is not True and len(ordered) >= 3:
                problems.append(
                    "a correction generator was dispatched although round 1 "
                    f"did not return needs_correction=true ({record1!r})")
        if problems:
            self.row("F-stop-order", "fail",
                     "the caller kept dispatching past the stop points",
                     problems)
        else:
            self.row("F-stop-order", "pass",
                     "no dispatch after the stop points",
                     [f"{len(ordered)} spawn(s); last record event "
                      f"{last_record}"])

    def judge_rebuild_and_stage4(self):
        m = self.m
        root_execs = m.execs.get(m.root_id, [])
        rebuilds = [r for r in root_execs if ROOT_REBUILD in r["command"]]
        records = [entry["record"] for entry in getattr(self, "rounds", [])]
        last_record = max((r["index"] for r in records), default=-1)
        problems = []
        if last_record < 0 and not rebuilds:
            self.row("F-rebuild-stage4", "evidence_gap",
                     "no terminal record and no rebuild: the run never "
                     "reached the terminal boundary",
                     [])
            return
        if len(rebuilds) != 1:
            problems.append(f"expected exactly one rebuild exec, saw "
                            f"{len(rebuilds)}")
        elif rebuilds[0]["index"] < last_record:
            problems.append(
                f"rebuild (event {rebuilds[0]['index']}) ran before the "
                f"terminal record (event {last_record})")
        finalize_after = [r["index"] for r in root_execs
                          if CHILD_FINALIZE in r["command"]
                          and r["index"] > last_record >= 0]
        child_finalize_after = []
        for thread_id, records_ in m.execs.items():
            if thread_id == m.root_id:
                continue
            child_finalize_after.extend(
                r["index"] for r in records_
                if CHILD_FINALIZE in r["command"] and r["index"] > last_record >= 0)
        if finalize_after or child_finalize_after:
            problems.append(
                f"finalize ran after the terminal record: "
                f"{finalize_after + child_finalize_after}")
        stage4 = []
        if self.program_root is not None:
            for pattern in ("套磁选择.json", "邮件输入.json"):
                stage4.extend(
                    str(path) for path in self.program_root.rglob(pattern))
            if stage4:
                problems.append(f"Stage-4 artifacts present: {stage4}")
        if problems:
            self.row("F-rebuild-stage4", "fail",
                     "terminal rebuild / stage boundary violated", problems)
        else:
            self.row("F-rebuild-stage4", "pass",
                     "exactly one rebuild after the terminal record; no "
                     "finalize or Stage-4 artifacts afterwards",
                     [f"rebuild event {rebuilds[0]['index']}" if rebuilds
                      else "no rebuild observed"])

    def judge_terminal_state(self):
        state = self.state
        if not isinstance(state, dict):
            self.row("F-terminal-state", "evidence_gap",
                     "candidate state unreadable or missing",
                     ["the committed 套磁候选状态.json was not available"])
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
        terminal = all(
            entry.get("result") in ("pass", "fail_after_2_rounds")
            for entry in results.values())
        rounds_ok = all(
            entry.get("rounds", 0) <= 2 for entry in results.values())
        if terminal and rounds_ok:
            self.row("F-terminal-state", "pass",
                     "the committed state holds a terminal validator record "
                     "within the two-round cap",
                     [f"results: { {k: v.get('result') for k, v in
                               results.items()} }"])
        else:
            self.row("F-terminal-state", "fail",
                     "the validator record is not terminal or exceeds the "
                     "two-round cap",
                     [json.dumps(results, ensure_ascii=False)[:300]])

    # -- entry -------------------------------------------------------------

    def run(self) -> dict:
        self.judge_topology()
        self.judge_credential_chain()
        self.judge_handoff_chain()
        self.judge_four_point()
        self.judge_write_scope()
        self.judge_stop_order()
        self.judge_rebuild_and_stage4()
        self.judge_terminal_state()
        gaps = self.m.gaps or []
        gap_rows = [row for row in self.rows if row["verdict"] == "evidence_gap"]
        machine_prefix = [row for row in self.rows
                          if row["verdict"] == "machine_failure_prefix"]
        failures = [row for row in self.rows if row["verdict"] == "fail"]
        # Fixed order: a proven contract violation is a product FAIL even
        # when later facts were never reached (their gaps are consequences,
        # not evidence defects); INVALID is reserved for runs where the
        # captured evidence itself is missing or of an unsupported shape.
        if failures:
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
            "schema": "issue66-runtime-judge-v1",
            "classification": classification,
            "reason": reason,
            "evidence_gaps": gaps,
            "facts": self.rows,
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-response", required=True)
    parser.add_argument("--adapter-output", required=True)
    parser.add_argument("--candidate-state", default=None)
    parser.add_argument("--program-root", default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    response = json.loads(Path(args.eval_response).read_text(encoding="utf-8"))
    adapter = json.loads(Path(args.adapter_output).read_text(encoding="utf-8"))
    candidate_state = None
    if args.candidate_state:
        path = Path(args.candidate_state)
        if path.exists():
            try:
                candidate_state = json.loads(
                    path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                candidate_state = None
    program_root = Path(args.program_root) if args.program_root else None

    model = RunModel(response, adapter)
    verdict = Judge(model, candidate_state, program_root).run()
    Path(args.output).write_text(
        json.dumps(verdict, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(verdict["classification"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
