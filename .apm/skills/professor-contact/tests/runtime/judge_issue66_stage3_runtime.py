"""Mechanical judge for the S3-RT-CODEX-1 runtime evidence (issue #66).

This is the single decision program required by the frozen test plan
(``issue-66-test-plan-r19-clarification-r3-2026-10-05`` §四/§六).  It folds
every required evidence surface into ONE verdict — formal delegation
attribution, the invocation-credential value chain, the per-round
prepare→validate→save→record handoff, the validator-produced raw bytes, the
file-operation behavior proven by complete command inputs and completed
``fileChange`` records, the completion-order
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
  ``--post-snapshot``   required producer verifier outputs, folded in
- ``--routing-evidence`` required legacy topology verifier output,
                        folded into the unique conclusion
- ``--storage-evidence`` required read-only storage ownership record

Every evidence input must carry the same non-empty ``evidence_set_id``. The
collector must bind the raw /eval response, adapter and verifier outputs to
the same run before invoking this judge.

Unknown event shapes and missing required surfaces are evidence gaps —
never silent passes.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shlex
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
    """Return a flag's parsed argv value, not a substring from shell text."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    try:
        index = tokens.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(tokens) or tokens[index + 1].startswith("--"):
        return None
    return tokens[index + 1]


def stage3_command(command: str) -> str | None:
    """Identify a contact_state.py subcommand from the actual argv."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    for index, token in enumerate(tokens[:-1]):
        if Path(token).name == "contact_state.py" \
                and tokens[index + 1].startswith("stage3-"):
            return tokens[index + 1]
    return None


def command_file_behavior(command: str, cwd: str | None):
    """Return every legible file operation and whether any part is unknown.

    Operations are ``(kind, absolute_path, exclusive_create)`` tuples. Shell
    composition is split into commands so a later write cannot be hidden by an
    earlier read. Unsupported pieces are reported separately; callers retain
    already-proven writes while classifying the unsupported evidence as a gap.
    ``commandActions`` is deliberately not consulted.
    """
    base = Path(cwd or ".")
    operations = []
    unknown = False

    def full_path(raw):
        if not isinstance(raw, str) or not raw or raw == "-" \
                or any(char in raw for char in ("$", "`", "*", "?")):
            return None
        path = Path(raw)
        return str(path if path.is_absolute() else (base / path).resolve())

    def add(kind, raw_path, exclusive=False):
        nonlocal unknown
        path = full_path(raw_path)
        if path is None:
            unknown = True
            return False
        operations.append((kind, path, exclusive))
        return True

    def dotted_name(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = dotted_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ""

    def literal_path(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Call) and dotted_name(node.func) in {
                "Path", "pathlib.Path"} and node.args \
                and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            return node.args[0].value
        return None

    def python_operations(argv):
        nonlocal unknown
        try:
            code_index = argv.index("-c")
            source = argv[code_index + 1]
            tree = ast.parse(source)
        except (ValueError, IndexError, SyntaxError):
            unknown = True
            return
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        recognized = set()
        for node in calls:
            func_name = dotted_name(node.func)
            if func_name in {"Path", "pathlib.Path"}:
                recognized.add(id(node))
                if literal_path(node) is None:
                    unknown = True
                continue
            if func_name == "open":
                recognized.add(id(node))
                path_node = node.args[0] if node.args else next(
                    (kw.value for kw in node.keywords if kw.arg == "file"), None)
                raw_path = literal_path(path_node)
                mode_node = node.args[1] if len(node.args) > 1 else next(
                    (kw.value for kw in node.keywords if kw.arg == "mode"), None)
                mode = (mode_node.value if isinstance(mode_node, ast.Constant)
                        and isinstance(mode_node.value, str) else "r"
                        if mode_node is None else None)
                if raw_path is None or mode is None:
                    unknown = True
                elif mode in {"r", "rb", "rt"}:
                    add("read", raw_path)
                elif mode in {"x", "xb", "x+"}:
                    add("write", raw_path, True)
                elif mode in {"w", "wb", "w+", "a", "ab", "a+"}:
                    add("write", raw_path, False)
                else:
                    unknown = True
                continue
            if isinstance(node.func, ast.Attribute):
                method = node.func.attr
                receiver = node.func.value
                if method == "write" and isinstance(receiver, ast.Call) \
                        and dotted_name(receiver.func) == "open":
                    recognized.add(id(node))
                    continue
                if method in {"read_text", "read_bytes", "write_text",
                              "write_bytes", "unlink", "mkdir", "rmdir",
                              "rename", "replace"}:
                    raw_path = literal_path(receiver)
                    recognized.add(id(node))
                    if raw_path is None:
                        unknown = True
                    elif method in {"read_text", "read_bytes"}:
                        add("read", raw_path)
                    elif method in {"rename", "replace"}:
                        target = literal_path(node.args[0]) if node.args else None
                        if target is None:
                            unknown = True
                        else:
                            add("write", raw_path)
                            add("write", target)
                    else:
                        add("write", raw_path)
                    continue
            if func_name in {"os.remove", "os.unlink", "os.mkdir", "os.rmdir"}:
                recognized.add(id(node))
                raw_path = literal_path(node.args[0]) if node.args else None
                if raw_path is None:
                    unknown = True
                else:
                    add("write", raw_path)
                continue
            if func_name in {"os.rename", "os.replace"}:
                recognized.add(id(node))
                paths = [literal_path(arg) for arg in node.args[:2]]
                if len(paths) != 2 or any(path is None for path in paths):
                    unknown = True
                else:
                    for path in paths:
                        add("write", path)
                continue
            if func_name in {"shutil.copy", "shutil.copy2",
                             "shutil.copyfile", "shutil.move"}:
                recognized.add(id(node))
                paths = [literal_path(arg) for arg in node.args[:2]]
                if len(paths) != 2 or any(path is None for path in paths):
                    unknown = True
                else:
                    add("read", paths[0])
                    if func_name == "shutil.move":
                        add("write", paths[0])
                    add("write", paths[1])
                continue
        if any(id(node) not in recognized for node in calls):
            unknown = True
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = ({alias.name for alias in node.names}
                         if isinstance(node, ast.Import) else
                         {node.module or ""})
                if not names <= {"os", "shutil", "pathlib"}:
                    unknown = True

    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return [], True
    if not tokens:
        return [], True

    # Keep each shell command, but do not discard neighboring commands around
    # separators. Empty commands and unsupported separators make the whole
    # command incomplete evidence while known operations remain usable.
    separators = {";", "&&", "||", "|", "&"}
    segments = []
    current = []
    for token in tokens:
        if token in separators:
            if current:
                segments.append(current)
                current = []
            else:
                unknown = True
        else:
            current.append(token)
    if current:
        segments.append(current)
    elif tokens[-1] in separators:
        unknown = True

    for segment in segments:
        argv = []
        redirections = []
        index = 0
        while index < len(segment):
            token = segment[index]
            operator = token
            if token in {"1", "2"} and index + 1 < len(segment) \
                    and segment[index + 1] in {">", ">>", "<", "<<"}:
                operator = segment[index + 1]
                index += 1
            if operator in {">", ">>", ">|", "<", "<<", "<>"}:
                if index + 1 >= len(segment):
                    unknown = True
                    index += 1
                    continue
                target = segment[index + 1]
                if operator == "<":
                    redirections.append(("read", target, False))
                elif operator == "<<":
                    unknown = True
                elif operator == "<>" or operator in {">>", ">|"}:
                    redirections.append(("write", target, False))
                    if operator == "<>":
                        redirections.append(("read", target, False))
                else:
                    redirections.append(("write", target, False))
                index += 2
                continue
            if operator in {"&>", "&>>"}:
                if index + 1 >= len(segment):
                    unknown = True
                else:
                    redirections.append(("write", segment[index + 1], False))
                index += 2
                continue
            if token and all(char in ";&|<>" for char in token):
                unknown = True
            else:
                argv.append(token)
            index += 1
        for kind, target, exclusive in redirections:
            if not add(kind, target, exclusive):
                unknown = True
        if not argv:
            continue
        executable = Path(argv[0]).name
        if executable in {"cat", "head", "tail", "jq", "rg", "grep", "ls",
                          "pwd", "wc", "file"}:
            for operand in argv[1:]:
                if operand == "--":
                    continue
                if operand.startswith("-"):
                    continue
                if not add("read", operand):
                    unknown = True
        elif executable.startswith("python") or executable in {"uv", "pypy"}:
            python_operations(argv)
        else:
            unknown = True
    return operations, unknown


class RunModel:
    """Ordered evidence extracted from the raw event stream + adapter."""

    def __init__(self, response: dict, adapter: dict):
        self.gaps: list[str] = []
        self.evidence_set_id = response.get("evidence_set_id")
        self.adapter_evidence_set_id = adapter.get("evidence_set_id")
        self.root_id = (response.get("output") or {}).get("thread_id")
        self.events = ((response.get("output") or {}).get(
            "app_server_events") or [])
        self.run_completed = any(
            (e.get("message") or {}).get("method") == "turn/completed"
            for e in self.events)
        # -- formal relations (adapter) ------------------------------------
        dispatch = adapter.get("dispatch")
        relations = dispatch.get("thread_relations") \
            if isinstance(dispatch, dict) else None
        self.relation_surface_complete = isinstance(relations, list)
        self.relations = relations if isinstance(relations, list) else []
        self.child_reads = ((adapter.get("child_thread_reads") or {})
                            .get("entries") or [])
        self.read_roles = {entry.get("thread_id"):
                           entry.get("effective_role")
                           for entry in self.child_reads}
        delegation = adapter.get("delegation")
        delegation = delegation if isinstance(delegation, dict) else {}
        self.delegation_state = delegation.get("state")
        self.adapter_children = delegation.get("child_thread_ids")
        self.delegation_summary_complete = (
            self.delegation_state == "confirmed"
            and isinstance(delegation.get("basis"), list)
            and "formal_spawn_relation" in delegation.get("basis", [])
            and isinstance(self.adapter_children, list)
            and isinstance(delegation.get("formal_child_count"), int)
            and delegation.get("formal_child_count") == len(self.adapter_children))
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
                self.spawn_outputs[item["call_id"]] = {
                    "method": message.get("method"),
                    "index": index,
                    "text": self._output_text(item),
                    "completed": message.get("method") in {
                        "rawResponseItem/completed", "item/completed"}}
        # -- subAgentActivity: call_id -> agent thread ids ------------------
        self.activity_children = {}
        self.completed_activity_children = {}
        self.activity_completion_index = {}
        self.activity_start_index = {}
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
                    if item.get("kind") == "started":
                        self.activity_start_index[call_id] = index
                    if item.get("kind") == "completed" \
                            and message.get("method") == "item/completed":
                        self.completed_activity_children.setdefault(
                            call_id, set()).add(thread_id)
                        self.activity_completion_index[call_id] = index
        # -- command inputs and their actual completion returns -------------
        self.execs = {}
        pending_execs = {}
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
            record = {
                "call_index": index,
                "index": None,
                "thread_id": thread_id,
                "turn_id": params.get("turnId"),
                "item_id": item.get("id"),
                "call_id": item.get("call_id") or item.get("id"),
                "command": item.get("command") or "",
                "cwd": item.get("cwd") or params.get("cwd"),
                "output": None,
                "exit_code": None,
                "status": item.get("status"),
                "truncated": False,
                "actions": [],
                "completion_method": message.get("method"),
            }
            key = (thread_id, params.get("turnId"), record["call_id"])
            bucket = self.execs.setdefault(thread_id, [])
            is_start = message.get("method") == "item/started" \
                or record["status"] in {"inProgress", "started"}
            is_complete = message.get("method") == "item/completed" \
                or record["status"] in {"completed", "failed", "errored"}
            if is_start and not is_complete:
                if not record["item_id"]:
                    self.gaps.append(
                        f"event {index}: commandExecution input lacks item id")
                pending_execs[key] = record
                continue
            if is_complete:
                prior = pending_execs.pop(key, None)
                if prior:
                    prior.update({name: value for name, value in record.items()
                                  if value is not None and name not in {
                                      "call_index", "command", "cwd", "thread_id",
                                      "turn_id", "item_id", "call_id"}})
                    if not prior["command"]:
                        prior["command"] = record["command"]
                    if not prior["cwd"]:
                        prior["cwd"] = record["cwd"]
                    record = prior
                else:
                    record["call_index"] = index
                record["index"] = index
                record["output"] = item.get("aggregatedOutput")
                record["exit_code"] = item.get("exitCode")
                record["status"] = item.get("status")
                record["truncated"] = bool(
                    record["output"] and TRUNCATION_MARKER in record["output"])
                if not record["command"] or not record["item_id"]:
                    self.gaps.append(
                        f"event {index}: command completion cannot be tied to its input")
                bucket.append(record)
            else:
                self.gaps.append(
                    f"event {index}: commandExecution has no recognized completion state")
        for record in pending_execs.values():
            self.execs.setdefault(record["thread_id"], []).append(record)
            self.gaps.append(
                f"event {record['call_index']}: commandExecution input has no completion")
        # -- actual patch/file change events; never commandActions -----------
        self.file_changes = {}
        self.incomplete_file_changes = []
        for index, event in enumerate(self.events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if item.get("type") != "fileChange":
                continue
            if message.get("method") != "item/completed":
                continue
            thread_id = params.get("threadId")
            turn_id = params.get("turnId")
            item_id = item.get("id")
            status = item.get("status")
            changes = item.get("changes")
            if status != "completed" or not thread_id or not turn_id \
                    or not item_id or not isinstance(changes, list):
                self.incomplete_file_changes.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id})
                self.gaps.append(
                    f"event {index}: fileChange lacks completed status, item, "
                    "turn, thread, or structured changes")
                continue
            for change in changes:
                if not isinstance(change, dict):
                    self.incomplete_file_changes.append({
                        "index": index, "thread_id": thread_id,
                        "turn_id": turn_id, "item_id": item_id})
                    self.gaps.append(f"event {index}: fileChange entry is not an object")
                    continue
                operation = (change.get("operation") or change.get("kind")
                             or change.get("type"))
                path = change.get("path")
                self.file_changes.setdefault(thread_id, []).append({
                    "index": index, "turn_id": turn_id,
                    "item_id": item_id, "status": status, "path": path,
                    "operation": operation,
                    "diff": change.get("diff"),
                    "content": change.get("content"),
                    "completed": True})
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
            turn_id = params.get("turnId")
            item_id = item.get("id")
            raw = final_message_bytes(item)
            if raw is None or not thread_id or not turn_id or not item_id:
                self.unsupported_shapes[thread_id] = \
                    self.unsupported_shapes.get(thread_id, 0) + 1
                self.gaps.append(
                    f"event {index}: unsupported message shape or missing "
                    f"identity fields on {thread_id}")
                continue
            self.assistant_messages.setdefault(
                thread_id, []).append({"index": index,
                                       "turn_id": turn_id,
                                       "item_id": item_id,
                                       "bytes": raw})

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
        self.attribution_incomplete = False
        self.first_finalize = None

    def row(self, fact_id, verdict, detail, evidence):
        self.rows.append({"fact": fact_id, "verdict": verdict,
                          "detail": detail, "evidence": evidence})

    def flag_value(self, command, flag):
        return extract_flag_value(command, flag)

    # -- folded surfaces ---------------------------------------------------

    def _routing_relation_integrity(self, routing, checks_by_name):
        """Check routing.json's formal-edge summary against the adapter.

        The topology verifier projects the formal graph into root child ids
        and nested spawn rows.  Keep those observations in the unique verdict
        and reject summaries that disagree with the source relation surface.
        """
        root_id = routing.get("root_thread_id")
        direct_ids = routing.get("root_direct_spawn_child_ids")
        nested = routing.get("nested_formal_spawns")
        if not isinstance(direct_ids, list) or not isinstance(nested, list):
            return "gap", ["routing.json lacks root child or nested relation observations"]
        if not isinstance(root_id, str) or not root_id:
            return "gap", ["routing.json has no observed root thread id"]
        if self.m.root_id and root_id != self.m.root_id:
            return "invalid", ["routing.json root thread id conflicts with the raw event stream"]
        if any(not isinstance(child, str) or not child for child in direct_ids) \
                or len(set(direct_ids)) != len(direct_ids):
            return "invalid", ["routing.json root child ids are malformed or duplicated"]

        def signature(row):
            if not isinstance(row, dict):
                return None
            sender = row.get("sender_thread_id")
            receivers = row.get("receiver_thread_ids")
            if not isinstance(sender, str) or not sender \
                    or not isinstance(receivers, list) or not receivers \
                    or any(not isinstance(child, str) or not child
                           for child in receivers):
                return None
            return sender, tuple(receivers)

        actual_nested = [signature(row) for row in nested]
        if any(row is None for row in actual_nested):
            return "invalid", ["routing.json contains a malformed nested relation"]

        ownership = checks_by_name.get("formal_ownership")
        ownership_detail = ownership.get("detail") if ownership else None
        if ownership and ownership.get("status") == "fail" \
                or isinstance(ownership_detail, dict) and ownership_detail:
            return "invalid", ["routing.json reports conflicting formal owners"]

        nested_check = checks_by_name.get("no_nested_formal_spawn")
        nested_detail = nested_check.get("detail") if nested_check else None
        if nested_check and nested_check.get("status") == "pass" and nested \
                or nested_check and nested_check.get("status") == "fail" and not nested:
            return "invalid", ["nested relation rows conflict with the no-nested check"]
        if isinstance(nested_detail, list):
            detailed_nested = [signature(row) for row in nested_detail]
            if any(row is None for row in detailed_nested) \
                    or sorted(detailed_nested) != sorted(actual_nested):
                return "invalid", ["nested relation check detail conflicts with routing.json rows"]

        count_check = checks_by_name.get("root_direct_spawn_child_count")
        count_detail = count_check.get("detail") if count_check else None
        if isinstance(count_detail, dict) and "observed" in count_detail \
                and count_detail["observed"] != len(direct_ids):
            return "invalid", ["root child count detail conflicts with routing.json child ids"]

        if not self.m.relation_surface_complete:
            return "gap", ["adapter formal relation surface is missing"]
        expected_direct = set()
        expected_nested = []
        for relation in self.m.relations:
            if not isinstance(relation, dict):
                return "invalid", ["adapter formal relation entry is malformed"]
            if relation.get("tool") != "spawnAgent":
                continue
            sender = relation.get("sender_thread_id")
            receivers = relation.get("receiver_thread_ids")
            if not isinstance(sender, str) or not sender \
                    or not isinstance(receivers, list) or not receivers \
                    or any(not isinstance(child, str) or not child
                           for child in receivers):
                return "invalid", ["adapter formal relation shape is unsupported"]
            if sender == root_id:
                expected_direct.update(receivers)
            else:
                expected_nested.append((sender, tuple(receivers)))
        if set(direct_ids) != expected_direct:
            return "invalid", ["routing.json root child ids conflict with adapter formal relations"]
        if sorted(actual_nested) != sorted(expected_nested):
            return "invalid", ["routing.json nested rows conflict with adapter formal relations"]
        return "ok", []

    def _fold_required_checks(self, surface_name, fact, required_names,
                              description):
        """Fold one required verifier output into the unique verdict.

        The producer verifier owns each domain-specific comparison. This
        layer still requires every frozen check and never treats absent or
        unsupported output as success.
        """
        evidence = self.surfaces.get(surface_name)
        if evidence is None:
            self.row(fact, "gap", f"required {description} evidence is missing", [])
            return
        if not isinstance(evidence, dict):
            self.row(fact, "invalid", f"{description} evidence has an unsupported shape",
                     [type(evidence).__name__])
            return
        checks = evidence.get("checks")
        if not isinstance(checks, list):
            self.row(fact, "gap", f"{description} evidence has no structured checks", [])
            return
        named_checks = [item for item in checks
                        if isinstance(item, dict)
                        and isinstance(item.get("name"), str)]
        by_name = {item["name"]: item for item in named_checks}
        duplicate_names = sorted({item["name"] for item in named_checks
                                  if sum(other["name"] == item["name"]
                                         for other in named_checks) > 1})
        missing = sorted(set(required_names) - set(by_name))
        unsupported = [item for item in checks
                       if not isinstance(item, dict)
                       or item.get("status") not in ("pass", "fail")]
        failed = [name for name, item in by_name.items()
                  if item.get("status") == "fail"]
        status = evidence.get("status")
        if unsupported or duplicate_names:
            self.row(fact, "invalid", f"{description} evidence has unsupported check rows",
                     [f"rows={len(unsupported)}", f"duplicates={duplicate_names}"])
        elif failed or status in ("fail", "invalid", "INVALID_TEST_EXECUTION"):
            self.row(fact, "invalid", f"{description} prerequisite did not pass",
                     failed or [f"status={status}"])
        elif missing or status not in ("pass", "ok"):
            self.row(fact, "gap", f"{description} evidence is incomplete",
                     [f"missing={missing}", f"status={status!r}"])
        else:
            self.row(fact, "pass", f"{description} checks folded into the verdict",
                     list(required_names))

    def judge_folded_surfaces(self):
        evidence_ids = [(name, self.surfaces.get(name, {}).get("evidence_set_id")
                         if isinstance(self.surfaces.get(name), dict) else None)
                        for name in ("install", "fixture", "routing", "pre", "post", "storage")]
        evidence_ids.extend((
            ("eval-response", self.m.evidence_set_id),
            ("adapter-output", self.m.adapter_evidence_set_id),
        ))
        missing_ids = [name for name, value in evidence_ids
                       if not isinstance(value, str) or not value.strip()]
        observed_ids = {value for _name, value in evidence_ids
                        if isinstance(value, str) and value.strip()}
        if missing_ids:
            self.row("F-evidence-version", "gap",
                     "run evidence identifiers are missing from one or more inputs",
                     missing_ids)
        elif len(observed_ids) > 1:
            self.row("F-evidence-version", "invalid",
                     "evidence inputs mix different run identifiers",
                     [f"{name}={value}" for name, value in evidence_ids])
        else:
            self.row("F-evidence-version", "pass",
                     "all inputs are bound to one run evidence set",
                     [next(iter(observed_ids))])
        self._fold_required_checks(
            "install", "F-install",
            ("locked_target_commit", "source_install_projection",
             "request_config_matches_consensus"), "install")
        fixture = self.surfaces.get("fixture")
        self._fold_required_checks(
            "fixture", "F-fixture",
            ("no_manual_patch", "initial_input_digest",
             "forbidden_outputs_absent"), "sample")
        if isinstance(fixture, dict) and fixture.get("manual_patch") != "no":
            self.rows[-1] = {
                "fact": "F-fixture", "verdict": "invalid",
                "summary": "sample evidence declares a manual patch",
                "evidence": [f"manual_patch={fixture.get('manual_patch')}"]}
        self._fold_required_checks(
            "storage", "F-storage-ownership",
            ("process_is_test_only", "config_is_test_only",
             "database_is_test_only", "logs_are_test_only",
             "database_path_resolved", "run_records_match_case", "read_only"),
            "storage ownership")
        self._fold_required_checks(
            "pre", "F-pre-snapshot", ("pre_zero_write_snapshot",),
            "pre-run snapshot")
        self._fold_required_checks(
            "post", "F-post-snapshot", ("post_matches_current",),
            "post-run snapshot")
        routing = self.surfaces.get("routing")
        if isinstance(routing, dict):
            classification = routing.get("classification") or routing.get("status")
            checks = routing.get("checks")
            required = {"formal_ownership", "no_nested_formal_spawn",
                        "root_direct_spawn_child_count",
                        "pre_zero_write_snapshot", "post_matches_current"}
            if not isinstance(checks, list):
                self.row("F-routing-verifier", "gap",
                         "routing.json has no structured check list", [])
            else:
                by_name = {c.get("name"): c for c in checks
                           if isinstance(c, dict) and isinstance(c.get("name"), str)}
                missing = sorted(required - set(by_name))
                bad = [c for c in checks if isinstance(c, dict)
                       and c.get("status") == "fail"]
                unknown = [c for c in checks if not isinstance(c, dict)
                           or c.get("status") not in ("pass", "fail")]
                owner_check = by_name.get("formal_ownership")
                owner_detail = owner_check.get("detail") if owner_check else None
                owner_conflict = bool(owner_check and
                                      owner_check.get("status") == "fail") \
                    or isinstance(owner_detail, dict) and bool(owner_detail)
                integrity, integrity_evidence = self._routing_relation_integrity(
                    routing, by_name)
                if classification in ("INVALID_TEST_EXECUTION", "INVALID",
                                      "invalid") or owner_conflict:
                    self.row("F-routing-verifier", "invalid",
                             "routing evidence cannot establish formal ownership",
                             integrity_evidence or [str(routing.get("reason_code")
                                                        or classification)])
                elif integrity == "invalid":
                    self.row("F-routing-verifier", "invalid",
                             "routing relation summary conflicts with formal evidence",
                             integrity_evidence)
                elif classification in ("FAIL", "FAIL_PRODUCT", "fail", "failed") \
                        and bad and integrity == "ok":
                    bad_names = {c.get("name") for c in bad}
                    machine_prefix = any(
                        row.get("fact") == "F-attribution"
                        and row.get("verdict") == "machine_failure_prefix"
                        for row in self.rows)
                    if machine_prefix and bad_names <= {
                            "root_direct_spawn_child_count"}:
                        self.row("F-routing-verifier", "gap",
                                 "root child count is incomplete after a confirmed machine failure",
                                 [str(name) for name in sorted(bad_names)])
                    elif not self.m.run_completed and bad_names <= {
                            "root_direct_spawn_child_count"}:
                        self.row("F-routing-verifier", "gap",
                                 "root run is incomplete; the observed child count cannot establish a delegation violation",
                                 [str(name) for name in sorted(bad_names)])
                    else:
                        self.row("F-routing-verifier", "fail",
                                 "routing.json reports a product contract violation",
                                 [str(c.get("name")) for c in bad])
                elif integrity == "gap" or missing or unknown:
                    self.row("F-routing-verifier", "gap",
                             "routing.json lacks required formal or snapshot findings",
                             integrity_evidence +
                             [f"missing={missing}", f"unknown={len(unknown)}"])
                elif classification in ("PASS", "pass", "ok") and bad:
                    self.row("F-routing-verifier", "invalid",
                             "routing summary conflicts with failed structured checks",
                             [str(c.get("name")) for c in bad])
                elif classification in ("PASS", "pass", "ok"):
                    self.row("F-routing-verifier", "pass",
                             "formal ownership, nesting and snapshot checks passed",
                             [str(c.get("name")) for c in checks])
                else:
                    self.row("F-routing-verifier", "gap",
                             f"routing.json classification: {classification}", [])
        else:
            self.row("F-routing-verifier", "gap",
                     "required routing.json evidence is missing", [])
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
        if not m.relation_surface_complete:
            invalid.append("formal thread_relations observation is missing")
        if not m.delegation_summary_complete:
            invalid.append("confirmed formal delegation summary is missing or inconsistent")

        formal = []
        owners = {}
        for relation in m.relations:
            if not isinstance(relation, dict):
                invalid.append("formal relation entry is not an object")
                continue
            if relation.get("tool") != "spawnAgent":
                continue
            call_id = relation.get("call_id")
            sender = relation.get("sender_thread_id")
            receivers = relation.get("receiver_thread_ids")
            if not isinstance(call_id, str) or not call_id \
                    or not isinstance(sender, str) or not sender \
                    or not isinstance(receivers, list) or not receivers \
                    or any(not isinstance(child, str) or not child
                           for child in receivers):
                invalid.append(f"formal relation has an unsupported shape: {relation}")
                continue
            edge = {"call_id": call_id, "sender": sender,
                    "receivers": set(receivers)}
            formal.append(edge)
            for child in receivers:
                owners.setdefault(child, set()).add(sender)

        conflicts = {child: sorted(senders) for child, senders in owners.items()
                     if len(senders) > 1}
        if conflicts:
            invalid.append(f"formal ownership conflict for child threads: {conflicts}")
            self.attribution_invalid = True

        root_calls = {}
        for spawn in m.spawns:
            call_id = spawn.get("call_id")
            if call_id in root_calls:
                invalid.append(f"duplicate root spawn call id {call_id}")
            root_calls[call_id] = spawn

        relation_by_call = {}
        for edge in formal:
            relation_by_call.setdefault(edge["call_id"], []).append(edge)
            if edge["sender"] != m.root_id:
                if edge["call_id"] in root_calls:
                    invalid.append(
                        f"formal owner for root call {edge['call_id']} conflicts "
                        f"with the root event: {edge['sender']}")
                elif not any(child in conflicts for child in edge["receivers"]):
                    problems.append(
                        f"formal spawn {edge['call_id']} originates outside "
                        f"this root at {edge['sender']}")
        for call_id, edges in relation_by_call.items():
            if edges[0]["sender"] == m.root_id and call_id not in root_calls:
                invalid.append(
                    f"formal root relation {call_id} has no matching actual root call")

        linked_sequence = []
        linked_children = []
        machine_prefix = False
        detail = []
        for position, spawn in enumerate(m.spawns):
            call_id = spawn["call_id"]
            observed = m.activity_children.get(call_id) or set()
            completed = m.completed_activity_children.get(call_id) or set()
            edges = relation_by_call.get(call_id) or []
            if len(observed) > 1 or len(completed) > 1:
                invalid.append(
                    f"root call {call_id} maps to multiple child threads: "
                    f"observed={sorted(observed)}, completed={sorted(completed)}")
                continue
            if not edges:
                if observed or completed:
                    invalid.append(
                        f"root call {call_id} formed child {sorted(observed or completed)} "
                        "without a formal relation")
                elif self._spawn_output_is_failure(m.spawn_outputs.get(call_id)) \
                        and position == len(m.spawns) - 1:
                    machine_prefix = True
                    detail.append(
                        f"event {spawn['index']}: actual machine failure for "
                        f"call {call_id}")
                elif m.run_completed and m.relation_surface_complete \
                        and m.delegation_summary_complete:
                    problems.append(
                        f"root call {call_id} completed without a formal relation "
                        "or formed child")
                else:
                    invalid.append(
                        f"root call {call_id} has no attributable completed child")
                continue
            if len(edges) != 1:
                invalid.append(
                    f"root call {call_id} has {len(edges)} formal relations")
                continue
            edge = edges[0]
            if edge["sender"] != m.root_id:
                continue
            if not completed:
                if self._spawn_output_is_failure(m.spawn_outputs.get(call_id)) \
                        and position == len(m.spawns) - 1:
                    machine_prefix = True
                    detail.append(
                        f"event {spawn['index']}: actual machine failure for "
                        f"call {call_id}")
                elif not m.run_completed:
                    if observed and observed != edge["receivers"]:
                        invalid.append(
                            f"call {call_id} observed child mapping disagrees "
                            f"before completion: activity={sorted(observed)}, "
                            f"formal={sorted(edge['receivers'])}")
                    else:
                        detail.append(
                            f"event {spawn['index']}: formal relation for "
                            f"{call_id} has no completed child activity in an "
                            "incomplete root run")
                        linked_sequence.append(spawn["agent_type"])
                else:
                    problems.append(
                        f"root call {call_id} has no completed child activity")
                continue
            if observed != completed or edge["receivers"] != completed:
                invalid.append(
                    f"call {call_id} child mapping disagrees: activity="
                    f"{sorted(completed)}, formal={sorted(edge['receivers'])}")
                continue
            child = next(iter(completed))
            linked_sequence.append(spawn["agent_type"])
            linked_children.append(child)
            detail.append(f"event {spawn['index']}: {call_id} → {child}")

        legal = [[GENERATOR_AGENT, VALIDATOR_AGENT],
                 [GENERATOR_AGENT, VALIDATOR_AGENT, GENERATOR_AGENT,
                  VALIDATOR_AGENT]]
        bad_agents = [agent for agent in linked_sequence
                      if agent not in LEGAL_AGENTS]
        if bad_agents:
            problems.append(
                f"spawn target outside the two legal named agents: "
                f"{bad_agents}")
        else:
            legal_prefix = any(seq[:len(linked_sequence)] == linked_sequence
                               for seq in legal)
            if not linked_sequence and not m.spawns:
                pass
            elif linked_sequence in legal:
                pass
            elif (machine_prefix or not m.run_completed) and legal_prefix:
                pass
            elif not problems and not invalid:
                problems.append(
                    f"formal root child path {linked_sequence} violates the "
                    "fixed 2/4 state machine")
        if invalid:
            self.attribution_invalid = True
        evidence = detail + [f"formal relations: {len(formal)}; "
                             f"completed root children: {linked_children}; "
                             f"delegation state: {m.delegation_state}"]
        if invalid:
            self.row("F-attribution", "invalid",
                     "formal ownership or observation evidence is "
                     "incomplete or conflicting", invalid)
        elif problems:
            self.row("F-attribution", "fail",
                     "formal delegation attribution violated", problems +
                     evidence)
        elif not m.spawns and m.run_completed \
                and m.relation_surface_complete \
                and m.delegation_summary_complete and not formal:
            self.row("F-attribution", "fail",
                     "zero real delegation with a complete run record",
                     ["the root never attempted spawn_agent; delegation "
                      "absence is a product violation, not a blocker"])
        elif machine_prefix and not problems:
            self.row("F-attribution", "machine_failure_prefix",
                     "spawn sequence stopped at a machine-level failure",
                     evidence)
        elif not m.run_completed:
            self.attribution_incomplete = True
            self.row("F-attribution", "gap",
                     "the root run is incomplete; delegation absence is not established",
                     evidence)
        else:
            self.row("F-attribution", "pass",
                     "every formal child is owned by this root and maps to "
                     "a completed actual call",
                     [f"spawn order: {linked_sequence}"] + evidence)

    @staticmethod
    def _spawn_output_is_failure(output):
        if not isinstance(output, dict) or output.get("completed") is not True:
            return False
        return output.get("text", "").strip() == \
            "collab spawn failed: no thread with id"

    # -- fix 2: credential value chain --------------------------------------

    def _generator_children(self):
        return [child for spawn, child in self.m.ordered_children()
                if child and spawn["agent_type"] == GENERATOR_AGENT]

    def _child_exec(self, child, needle):
        for record in self.m.execs.get(child, []):
            try:
                tokens = shlex.split(record["command"])
            except ValueError:
                continue
            if needle in tokens:
                return record
        return None

    def _root_exec(self, needle, after=0):
        for record in self.m.execs.get(self.m.root_id, []):
            if record["call_index"] >= after \
                    and stage3_command(record["command"]) == needle:
                return record
        return None

    @staticmethod
    def _exec_result(record):
        """Return success/failure/unknown from the paired actual call result."""
        if record is None or record.get("index") is None:
            return None
        if record.get("status") in {"failed", "errored"}:
            return False
        if record.get("exit_code") is not None and record.get("exit_code") != 0:
            return False
        if record.get("status") == "completed" and record.get("exit_code") == 0:
            return True
        return None

    def _result_payload(self, record, label, problems, gaps):
        state = self._exec_result(record)
        if state is False:
            problems.append(f"{label}: actual command completed unsuccessfully")
            return None
        if state is None:
            gaps.append(f"{label}: actual command completion status is missing")
            return None
        payload, parse_state = self._json_from_output(record.get("output"))
        if parse_state != "ok" or not isinstance(payload, dict):
            gaps.append(f"{label}: structured return {parse_state}")
            return None
        if payload.get("status") != "ok":
            problems.append(
                f"{label}: structured return status is {payload.get('status')!r}")
            return None
        return payload

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

    @staticmethod
    def _flag_values(command, flag):
        try:
            tokens = shlex.split(command)
        except ValueError:
            return None
        values = []
        for index, token in enumerate(tokens):
            if token == flag:
                values.append(tokens[index + 1] if index + 1 < len(tokens)
                              and not tokens[index + 1].startswith("--") else None)
            elif token.startswith(flag + "="):
                values.append(token[len(flag) + 1:])
        return values

    @staticmethod
    def _path_identity(value, cwd):
        if not isinstance(value, str) or not value.strip():
            return None
        path = Path(value)
        return str((path if path.is_absolute() else Path(cwd or ".") / path).resolve())

    def _credential_source(self, record, payload, problems, gaps):
        professor = payload.get("professor")
        professor_dir = payload.get("professor_dir")
        if not isinstance(professor, str) or not professor.strip():
            gaps.append(f"event {record['index']}: capture return misses professor identity")
        if not isinstance(professor_dir, str) or not professor_dir.strip():
            gaps.append(f"event {record['index']}: capture return misses professor_dir")
        else:
            inputs = self._flag_values(record["command"], "--professor-dir")
            if inputs is None:
                gaps.append(f"event {record['call_index']}: capture source arguments are unparsable")
            elif len(inputs) != 1 or not inputs[0]:
                problems.append("capture command has missing or ambiguous --professor-dir")
            elif self._path_identity(inputs[0], record.get("cwd")) \
                    != self._path_identity(professor_dir, record.get("cwd")):
                problems.append("capture return professor_dir differs from its command input")
        for field in ("refresh_scope", "direction_id"):
            if field not in payload:
                gaps.append(f"event {record['index']}: capture return misses source metadata {field}")
        requested_scope = self._flag_values(record["command"], "--refresh-scope")
        if requested_scope is None:
            gaps.append(f"event {record['call_index']}: refresh-scope input is unparsable")
        elif len(requested_scope) > 1:
            problems.append("capture command has duplicated --refresh-scope")
        expected_scope = requested_scope[0] if requested_scope else "flagged"
        if "refresh_scope" in payload and payload["refresh_scope"] != expected_scope:
            problems.append("capture return refresh_scope differs from the actual command input")
        requested_direction = self._flag_values(record["command"], "--direction-id")
        if requested_direction is None:
            gaps.append(f"event {record['call_index']}: direction-id input is unparsable")
        elif len(requested_direction) > 1:
            problems.append("capture command has duplicated --direction-id")
        if requested_direction and "direction_id" in payload \
                and payload["direction_id"] != requested_direction[0]:
            problems.append("capture return direction_id differs from the actual command input")
        return {"professor": professor, "professor_dir": professor_dir,
                "refresh_scope": payload.get("refresh_scope"),
                "direction_id": payload.get("direction_id"),
                "profile_fingerprint": payload.get("profile_fingerprint")}

    def _check_credential_consumer_source(self, record, payload, subcommand,
                                          captured, problems, gaps):
        label = f"event {record['index']}: {subcommand}"
        professor = payload.get("professor")
        if not isinstance(professor, str) or not professor.strip():
            gaps.append(f"{label} return misses professor identity")
        elif captured.get("professor") and professor != captured["professor"]:
            problems.append(f"{label} professor differs from the captured source")
        if subcommand == CHILD_PLAN:
            reported_dir = payload.get("professor_dir")
        else:
            state_path = payload.get("state_path")
            reported_dir = (str(Path(state_path).parent)
                            if isinstance(state_path, str) and state_path.strip()
                            else None)
        if not isinstance(reported_dir, str) or not reported_dir.strip():
            field = "professor_dir" if subcommand == CHILD_PLAN else "state_path"
            gaps.append(f"{label} return misses {field}")
        elif captured.get("professor_dir") and self._path_identity(
                reported_dir, record.get("cwd")) != self._path_identity(
                    captured["professor_dir"], record.get("cwd")):
            problems.append(f"{label} professor path differs from the captured source")
        if subcommand == CHILD_PLAN:
            for field in ("refresh_scope", "direction_id"):
                if field not in payload:
                    gaps.append(f"{label} return misses source metadata {field}")
                elif field in captured and payload[field] != captured[field]:
                    problems.append(f"{label} source metadata {field} differs from capture")
            profile_fingerprint = captured.get("profile_fingerprint")
            if profile_fingerprint is not None:
                if "profile_fingerprint" not in payload:
                    gaps.append(f"{label} return misses profile source fingerprint")
                elif payload["profile_fingerprint"] != profile_fingerprint:
                    problems.append(f"{label} profile source fingerprint differs from capture")

    def judge_credential_chain(self):
        m = self.m
        children = self._generator_children()
        if not children:
            complete = (m.run_completed and m.relation_surface_complete
                        and m.delegation_summary_complete
                        and not any(child is None for _, child in m.ordered_children()))
            self.row("F-credential-chain", "fail" if complete else "gap",
                     "no attributable generator child is available for the "
                     "invocation credential chain", [f"children: {children}"])
            return

        captures = []
        consumers = []
        for child in children:
            for record in m.execs.get(child, []):
                subcommand = stage3_command(record["command"])
                if subcommand not in {CHILD_PLAN, CHILD_FINALIZE}:
                    continue
                args = self._flag_values(record["command"], "--capture-invocation")
                if args is None:
                    self.row("F-credential-chain", "gap",
                             "credential command arguments cannot be parsed",
                             [f"event {record['call_index']}"])
                    return
                if args and subcommand == CHILD_PLAN:
                    captures.append((child, record))
                else:
                    consumers.append((child, record, subcommand))
        if not captures:
            completed_children = {thread for rows in m.completed_activity_children.values()
                                  for thread in rows}
            complete = (m.run_completed and m.relation_surface_complete
                        and m.delegation_summary_complete
                        and all(child in completed_children for child in children))
            self.row("F-credential-chain", "fail" if complete else "gap",
                     "no stage3-plan captured an invocation credential",
                     [f"generator children: {children}"])
            return
        capture_child, capture = captures[0]
        problems, gaps = [], []
        if capture_child != children[0]:
            problems.append("the first generator child did not capture its invocation credential")
        if len(captures) != 1:
            problems.append(f"expected one invocation capture, observed {len(captures)}")
        capture_args = self._flag_values(capture["command"], "--capture-invocation")
        if len(capture_args or []) != 1 or not capture_args[0]:
            problems.append("capture command has missing or duplicated --capture-invocation")
        try:
            capture_tokens = shlex.split(capture["command"])
        except ValueError:
            capture_tokens = []
            gaps.append(f"event {capture['call_index']}: capture command is unparsable")
        if any(self._flag_values(capture["command"], flag)
               for flag in CREDENTIAL_FLAGS):
            problems.append("capture command also supplied a credential")
        cap_payload = self._result_payload(
            capture, "first invocation capture", problems, gaps)
        if cap_payload is None:
            self.row("F-credential-chain", "fail" if problems else "gap",
                     "the invocation credential capture did not return a "
                     "usable structured result", problems + gaps)
            return
        if "invocation_file" not in cap_payload \
                or "invocation_sha256" not in cap_payload:
            self.row("F-credential-chain", "fail" if problems else "gap",
                     "capture return misses invocation_file or "
                     "invocation_sha256",
                     problems + [f"event {capture['index']}"])
            return
        real_file = cap_payload["invocation_file"]
        real_sha = cap_payload["invocation_sha256"]
        if not isinstance(real_file, str) or not real_file.strip() \
                or not isinstance(real_sha, str) or not real_sha.strip():
            self.row("F-credential-chain", "gap",
                     "capture return has no usable invocation file and digest",
                     [f"event {capture['index']}"])
            return
        if not re.fullmatch(r"[0-9a-fA-F]{64}", real_sha):
            problems.append("capture return invocation_sha256 is not a "
                            "64-character SHA-256 digest")
        captured = self._credential_source(capture, cap_payload, problems, gaps)
        consumption = []
        for child, record, subcommand in consumers:
            try:
                tokens = shlex.split(record["command"])
            except ValueError:
                gaps.append(f"event {record['call_index']}: command input is unparsable")
                continue
            consumption.append((child, record, subcommand))
            if self._exec_result(record) is False:
                problems.append(
                    f"event {record['index']}: {subcommand} returned an unsuccessful result")
                payload = None
            elif self._exec_result(record) is None:
                gaps.append(f"event {record['call_index']}: {subcommand} completion is missing")
                payload = None
            else:
                payload, state = self._json_from_output(record.get("output"))
                if state != "ok" or not isinstance(payload, dict):
                    gaps.append(f"event {record['index']}: {subcommand} structured return {state}")
                    payload = None
                elif payload.get("status") != "ok":
                    problems.append(
                        f"event {record['index']}: {subcommand} structured return "
                        f"status is {payload.get('status')!r}")
            for flag, real in ((CREDENTIAL_FLAGS[0], real_file),
                               (CREDENTIAL_FLAGS[1], real_sha)):
                values = self._flag_values(record["command"], flag)
                if values is None:
                    gaps.append(f"event {record['call_index']}: {flag} argument is unparsable")
                elif len(values) != 1 or not values[0]:
                    problems.append(f"event {record['call_index']}: {flag} is missing or duplicated")
                elif values[0] != real:
                    problems.append(f"event {record['index']}: {flag} value drifts from "
                                    "the actual capture return")
            replayed = [flag for flag in SOURCE_FLAGS if flag in tokens]
            replayed.extend(flag for flag in SOURCE_FLAGS
                            if any(token.startswith(flag + "=") for token in tokens))
            if self._flag_values(record["command"], "--capture-invocation"):
                problems.append(f"event {record['call_index']}: credential consumer "
                                "also requested a new capture")
            if replayed:
                problems.append(f"event {record['call_index']}: source parameters "
                                f"replayed alongside the credential: {replayed}")
            if payload is not None:
                self._check_credential_consumer_source(
                    record, payload, subcommand, captured, problems, gaps)
        correction_plans = [r for child, r, subcommand in consumption
                            if child == children[-1]
                            and subcommand == CHILD_PLAN
                            and self.flag_value(r["command"], "--validation-file")]
        if len(children) >= 2 and not correction_plans:
            problems.append("the correction round did not consume a "
                            "recorded validation file")
        first_finalize = [r for child, r, subcommand in consumption
                          if child == children[0]
                          and subcommand == CHILD_FINALIZE]
        if len(first_finalize) != 1:
            problems.append("the first commit (stage3-finalize) never ran "
                            "exactly once in the first generator child")
        self.first_finalize = first_finalize[0] if len(first_finalize) == 1 else None
        self.credential_values = {"file": real_file, "sha": real_sha}
        if problems:
            self.row("F-credential-chain", "fail",
                     "the captured credential values were not consumed "
                     "verbatim", problems)
        elif gaps:
            self.row("F-credential-chain", "gap",
                     "the credential value chain has incomplete completion evidence",
                     gaps)
        else:
            self.row("F-credential-chain", "pass",
                     "first-round capture and verbatim credential "
                     "consumption verified against the actual capture and "
                     "professor/source returns",
                     [f"invocation_file={real_file}", f"{len(consumption)} "
                      f"consumption exec(s)"])

    # -- fix 3+2: per-round handoff chain with actual values -----------------

    def judge_handoff_chain(self):
        m = self.m
        validator_spawns = [(spawn, child) for spawn, child in m.ordered_children()
                            if child and spawn["agent_type"] == VALIDATOR_AGENT]
        if not validator_spawns:
            self.row("F-handoff-chain", "gap",
                     "no completed validator child to judge the handoff on",
                     [])
            self.rounds = []
            return
        cursor = 0
        problems = []
        gaps = []
        rounds = []
        for round_no, (spawn, child) in enumerate(validator_spawns, start=1):
            prepare = self._root_exec(ROOT_PREPARE, after=cursor)
            if prepare is None or self.flag_value(
                    prepare["command"], "--round") != str(round_no):
                problems.append(
                    f"round {round_no}: no root prepare exec with --round "
                    f"{round_no} before the validator child")
                break
            if self.first_finalize is None or self.first_finalize["index"] \
                    >= prepare["call_index"]:
                problems.append(
                    f"round {round_no}: first generator finalize did not "
                    "complete before prepare began")
            prep_payload = self._result_payload(
                prepare, f"round {round_no} prepare", problems, gaps)
            if prep_payload is None:
                break
            handoff_file = prep_payload.get("handoff_file")
            handoff_sha = prep_payload.get("handoff_sha256")
            output_file = prep_payload.get("output_file")
            validation_file = prep_payload.get("validation_file")
            render_sha = prep_payload.get("render_sha256")
            prepared_round = prep_payload.get("round")
            if not all((handoff_file, handoff_sha, output_file,
                        validation_file, render_sha)) \
                    or prepared_round != round_no:
                problems.append(
                    f"round {round_no}: successful prepare return lacks or "
                    "drifts in round/handoff/output/validation/render values")
                break
            credential = getattr(self, "credential_values", {})
            for flag, value in (("--invocation-file", credential.get("file")),
                                ("--invocation-sha256", credential.get("sha"))):
                if not value or self.flag_value(prepare["command"], flag) != value:
                    problems.append(
                        f"round {round_no}: prepare {flag} does not use the "
                        "captured invocation credential")
            if prepare["index"] >= spawn["index"]:
                problems.append(
                    f"round {round_no}: prepare completion did not precede "
                    "the validator spawn input")
            child_completion = m.activity_completion_index.get(spawn["call_id"])
            if child_completion is None:
                gaps.append(
                    f"round {round_no}: validator child has no correlated "
                    "completion event")
                break
            save = self._root_exec(ROOT_SAVE, after=child_completion + 1)
            if save is None:
                problems.append(f"round {round_no}: no root save exec after "
                                f"the validator child")
                break
            if save["call_index"] <= child_completion:
                problems.append(
                    f"round {round_no}: save started before validator child "
                    "completion")
            if self._exec_result(save) is False:
                problems.append(
                    f"round {round_no}: save command returned unsuccessfully")
            for flag, real in (("--handoff-file", handoff_file),
                               ("--handoff-sha256", handoff_sha)):
                used = self.flag_value(save["command"], flag)
                if used != real:
                    problems.append(
                        f"round {round_no}: save {flag} drifts from the "
                        f"prepare return value")
            save_payload = self._result_payload(
                save, f"round {round_no} save", problems, gaps)
            if save_payload is None:
                break
            validation_sha = save_payload.get("validation_sha256")
            saved_file = save_payload.get("validation_file")
            if not validation_sha or saved_file != validation_file \
                    or save_payload.get("round") != round_no \
                    or save_payload.get("render_sha256") != render_sha:
                problems.append(
                    f"round {round_no}: save return does not preserve the "
                    "prepared validation path, round and render")
            if round_no > 1:
                previous_validation = rounds[-1]["validation_file"] if rounds else None
                generator = self._generator_children()
                correction = [r for r in m.execs.get(generator[-1], [])
                              if stage3_command(r["command"]) == CHILD_PLAN
                              and self.flag_value(r["command"], "--validation-file")]
                if not correction or self.flag_value(
                        correction[0]["command"], "--validation-file") != previous_validation:
                    problems.append(
                        "the correction plan did not consume the exact "
                        "round-1 saved validation file")
                if rounds and rounds[0]["record_payload"].get(
                        "needs_correction") is not True:
                    problems.append(
                        "the correction round began without a successful "
                        "round-1 needs_correction=true record")
            record = self._root_exec(ROOT_RECORD, after=save["index"] + 1)
            if record is None:
                problems.append(
                    f"round {round_no}: no record call follows save completion")
                break
            if record["call_index"] <= save["index"]:
                problems.append(
                    f"round {round_no}: record started before save completed")
            expected_inputs = (("--handoff-file", handoff_file),
                               ("--handoff-sha256", handoff_sha),
                               ("--expected-validation-sha256", validation_sha))
            if any(self.flag_value(record["command"], flag) != value
                   for flag, value in expected_inputs):
                problems.append(
                    f"round {round_no}: record inputs do not consume the "
                    "prepare handoff and save digest values")
            record_payload = self._result_payload(
                record, f"round {round_no} record", problems, gaps)
            if record_payload is None:
                break
            if record_payload.get("round") != round_no \
                    or record_payload.get("render_sha256") != render_sha \
                    or record_payload.get("validation_input_sha256") != validation_sha:
                problems.append(
                    f"round {round_no}: record return does not summarize "
                    "the round/render/bytes returned by save")
            rounds.append({
                "round": round_no, "child": child, "prepare": prepare,
                "save": save, "record": record, "output_file": output_file,
                "validation_file": validation_file,
                "render_sha256": render_sha,
                "save_payload": save_payload,
                "record_payload": record_payload})
            cursor = record["index"]
        self.chain_gaps = gaps
        if problems:
            self.row("F-handoff-chain", "fail",
                     "the handoff chain or its actual values are broken",
                     problems + gaps)
        elif gaps:
            self.row("F-handoff-chain", "gap",
                     "the handoff chain is missing actual completion or turn evidence",
                     gaps)
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
            message = messages[0]
            msg_sha = sha256_bytes(message["bytes"])
            save_sha = entry["save_payload"].get("validation_sha256")
            record_sha = entry["record_payload"].get(
                "validation_input_sha256")
            produced = self._production_evidence(entry, message)
            if produced is None:
                gapped = True
                rows.append(f"round {entry['round']}: validator production "
                            "or turn association is not evidenced")
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

    def _validator_window(self, entry):
        child = entry["child"]
        spawn = next((spawn for spawn, target in self.m.ordered_children()
                      if target == child), None)
        if spawn is None:
            return None, None, None
        start = spawn["index"]
        finish = self.m.activity_completion_index.get(spawn["call_id"])
        if finish is None:
            return start, None, None
        execs = [record for record in self.m.execs.get(child, [])
                 if record.get("call_index", -1) > start
                 and record.get("index") is not None
                 and record["index"] < finish]
        changes = [change for change in self.m.file_changes.get(child, [])
                   if change["index"] > start and change["index"] < finish]
        return start, finish, (execs, changes)

    @staticmethod
    def _literal_written_bytes(command):
        try:
            tokens = shlex.split(command)
            source = tokens[tokens.index("-c") + 1]
            tree = ast.parse(source)
        except (ValueError, IndexError, SyntaxError):
            return None
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) \
                    or node.func.attr != "write" or not node.args:
                continue
            value = node.args[0]
            if isinstance(value, ast.Constant) \
                    and isinstance(value.value, (bytes, str)):
                return value.value if isinstance(value.value, bytes) \
                    else value.value.encode("utf-8")
        return None

    @staticmethod
    def _filechange_added_bytes(change):
        """Return complete bytes only for a self-contained added-file patch."""
        content = change.get("content")
        if isinstance(content, bytes):
            return content
        if isinstance(content, str):
            return content.encode("utf-8")
        if change.get("operation") not in {"add", "created", "create", "added"}:
            return None
        diff = change.get("diff")
        if not isinstance(diff, str) or not diff:
            return None
        added = [line[1:] for line in diff.splitlines()
                 if line.startswith("+") and not line.startswith("+++")]
        if not added:
            return None
        raw = "\n".join(added).encode("utf-8")
        if diff.endswith("\n") and "\\ No newline at end of file" not in diff:
            raw += b"\n"
        return raw

    def _production_evidence(self, entry, message):
        """True/False/None: link one validator turn to its real output write."""
        output_file = entry.get("output_file")
        start, finish, window = self._validator_window(entry)
        if window is None or not output_file:
            return None
        execs, changes = window
        turn_id = message.get("turn_id")
        if not turn_id:
            return None
        if any(change.get("thread_id") == entry.get("child")
               and start < change.get("index", -1) < finish
               for change in self.m.incomplete_file_changes):
            return None
        if any(not record.get("turn_id") for record in execs) \
                or any(change.get("turn_id") != turn_id
                       or not change.get("item_id")
                       or change.get("status") != "completed"
                       for change in changes):
            return None
        if any(record.get("turn_id") != turn_id for record in execs):
            return None
        if message.get("index", -1) <= start or message.get("index", -1) >= finish:
            return None
        writes = []
        for record in execs:
            operations, unknown = command_file_behavior(
                record.get("command", ""), record.get("cwd"))
            if unknown:
                return None
            write_ops = [operation for operation in operations
                         if operation[0] == "write"]
            if write_ops and self._exec_result(record) is not True:
                return None
            for _kind, path, exclusive in write_ops:
                writes.append((Path(path), exclusive, record))
        for change in changes:
            if not change.get("completed") or not change.get("path"):
                return None
            writes.append((Path(change["path"]),
                           change.get("operation") in {
                               "add", "created", "create", "added"},
                           change))
        if not writes:
            # The correlated child, message, activity completion and complete
            # run envelope establish an empty producer window. That is a
            # confirmed product omission; an incomplete run remains a gap.
            return False if self.m.run_completed else None
        if len(writes) != 1:
            return False
        path, exclusive, observation = writes[0]
        if path != Path(output_file) or not exclusive:
            return False
        if isinstance(observation, dict) and "command" in observation:
            raw = self._literal_written_bytes(observation["command"])
        else:
            raw = self._filechange_added_bytes(observation)
            if raw is None:
                return None
        if raw is None or raw != message["bytes"]:
            return False
        return True

    def _root_source_rewrite(self, entry):
        """Actual root command/fileChange operations touching validator bytes."""
        output_file = entry.get("output_file") or ""
        validation_file = entry.get("validation_file") or ""
        record_cutoff = (entry.get("record") or {}).get("index")
        if record_cutoff is None:
            return []
        spawn_index = next(
            (spawn["index"] for spawn, c in self.m.ordered_children()
             if c == entry["child"]), -1)
        hits = []
        for record in self.m.execs.get(self.m.root_id, []):
            if record.get("index") is None or record.get("call_index") is None \
                    or record["call_index"] <= spawn_index \
                    or record["index"] >= record_cutoff:
                continue
            if stage3_command(record["command"]) in {
                    ROOT_SAVE, ROOT_RECORD, ROOT_PREPARE}:
                continue
            operations, _unknown = command_file_behavior(
                record.get("command", ""), record.get("cwd"))
            for kind, path, _exclusive in operations:
                if kind != "write":
                    continue
                if output_file and Path(path) == Path(output_file):
                    hits.append(f"event {record['index']}: {path}")
                if validation_file \
                        and Path(path) == Path(validation_file):
                    hits.append(f"event {record['index']}: {path}")
        for change in self.m.file_changes.get(self.m.root_id, []):
            if change["index"] <= spawn_index \
                    or change["index"] >= record_cutoff:
                continue
            path = change.get("path") or ""
            if path and (Path(path) == Path(output_file)
                         or Path(path) == Path(validation_file)):
                hits.append(f"event {change['index']}: {path}")
        return hits

    # -- fix 4: real file-operation write scope ------------------------------

    def judge_write_scope(self):
        rounds = getattr(self, "rounds", [])
        if not rounds:
            self.row("F-validator-write-scope", "gap",
                     "no validator child to judge the write scope on", [])
            return
        problems = []
        gaps = []
        observed = []
        for entry in rounds:
            child = entry["child"]
            output_file = entry.get("output_file") or ""
            _start, _finish, window = self._validator_window(entry)
            if window is None:
                gaps.append(f"round {entry['round']}: no correlated validator "
                            "completion window")
                continue
            execs, changes = window
            operation_count = 0
            turn_id = None
            for record in execs:
                record_turn = record.get("turn_id")
                turn_id = turn_id or record_turn
                if not record_turn or record_turn != turn_id:
                    gaps.append(f"round {entry['round']}: command turn ids do "
                                "not form one attributable validator turn")
                    continue
                if self._exec_result(record) is not True:
                    gaps.append(f"round {entry['round']}: a tool call lacks a "
                                "successful completion return")
                    continue
                operations, unknown = command_file_behavior(
                    record.get("command", ""), record.get("cwd"))
                if unknown:
                    gaps.append(f"round {entry['round']} event "
                                f"{record['call_index']}: command behavior is "
                                "not clear from its complete input")
                for kind, path, exclusive in operations:
                    if kind == "read":
                        observed.append(
                            f"round {entry['round']} event {record['index']}: "
                            f"read {path}")
                        continue
                    operation_count += 1
                    observed.append(
                        f"round {entry['round']} event {record['index']}: "
                        f"write {path} exclusive={exclusive}")
                    if Path(path) != Path(output_file):
                        problems.append(
                            f"round {entry['round']} event {record['index']}: "
                            f"write on {path} — outside assigned output file")
                    elif not exclusive:
                        problems.append(
                            f"round {entry['round']} event {record['index']}: "
                            "output file was not created exclusively")
            if turn_id is None:
                messages = self.m.assistant_messages.get(child) or []
                turn_id = messages[0].get("turn_id") if len(messages) == 1 else None
            for change in changes:
                if not change.get("completed") or not change.get("path") \
                        or not change.get("turn_id") or change.get("turn_id") != turn_id:
                    gaps.append(f"round {entry['round']}: fileChange cannot be "
                                "attributed to the validator turn")
                    continue
                operation_count += 1
                path = change["path"]
                exclusive = change.get("operation") in {
                    "add", "created", "create", "added"}
                observed.append(
                    f"round {entry['round']} event {change['index']}: "
                    f"fileChange {change.get('operation')} {path}")
                if Path(path) != Path(output_file):
                    problems.append(
                        f"round {entry['round']} event {change['index']}: "
                        f"fileChange on {path} — outside assigned output file")
                elif not exclusive:
                    problems.append(
                        f"round {entry['round']} event {change['index']}: "
                        "output file change was not an exclusive create")
            if operation_count == 0:
                gaps.append(f"round {entry['round']}: no actual file operation "
                            "can be established from the tool inputs")
            if operation_count > 1:
                problems.append(
                    f"round {entry['round']}: expected one exclusive output "
                    f"creation, observed {operation_count} writes")
        if problems:
            self.row("F-validator-write-scope", "fail",
                     "the validator wrote outside its assigned output file",
                     problems)
        elif gaps:
            self.row("F-validator-write-scope", "gap",
                     "validator file operations are not fully evidenced",
                     gaps + observed)
        else:
            self.row("F-validator-write-scope", "pass",
                     "every real write operation in the validator windows "
                     "targets the assigned output file only", observed)

    # -- fix 5: completion order, stop boundaries, terminal ------------------

    def judge_stop_order(self):
        m = self.m
        rounds = getattr(self, "rounds", [])
        problems = []
        gaps = []
        records = {entry["round"]: entry["record"] for entry in rounds}
        last_record = max((r["index"] for r in records.values()), default=-1)
        # A dispatch is the root's function_call event. Check it even when the
        # child never starts or completes, since an early attempt is observable.
        terminal_records = [entry for entry in rounds
                            if (entry["record_payload"] or {}).get(
                                "needs_correction") is False]
        for spawn, child in m.ordered_children():
            if terminal_records and spawn["index"] > min(
                    entry["record"]["index"] for entry in terminal_records):
                problems.append(
                    f"event {spawn['index']}: spawn after the terminal "
                    f"record (no third generator / no post-terminal "
                    f"validator)")
        # The second generator dispatch is checked as soon as it is observed;
        # it need not have completed a second validator round. This also checks
        # a machine-failed dispatch against the preceding record boundary.
        generator_spawns = [spawn for spawn in m.spawns
                            if spawn["agent_type"] == GENERATOR_AGENT]
        if len(generator_spawns) >= 2:
            record1 = records.get(1)
            if record1 is None:
                if m.run_completed:
                    problems.append(
                        "the correction generator was dispatched without a "
                        "completed round-1 record")
                else:
                    gaps.append(
                        "round-1 record completion is missing before the "
                        "second generator dispatch")
            else:
                correction_spawn = generator_spawns[1]
                if correction_spawn["index"] <= record1["index"]:
                    problems.append(
                        f"the correction generator started (event "
                        f"{correction_spawn['index']}) before the round-1 "
                        f"record completed (event {record1['index']})")
                needs = (rounds[0]["record_payload"] or {}).get(
                    "needs_correction") if rounds else None
                if needs is not True:
                    problems.append(
                        f"the correction generator was dispatched although "
                        f"round 1 needs_correction={needs!r}")
        elif rounds and (rounds[0]["record_payload"] or {}).get(
                "needs_correction") is True:
            attribution = {row["fact"]: row["verdict"] for row in self.rows}.get(
                "F-attribution")
            if attribution != "machine_failure_prefix":
                if m.run_completed:
                    problems.append(
                        "round 1 requested correction but no second "
                        "generator dispatch was observed")
                else:
                    gaps.append(
                        "round 1 requested correction but the run is "
                        "incomplete before a second generator dispatch")

        if problems:
            self.row("F-stop-order", "fail", "stop boundaries violated",
                     problems + gaps)
        elif gaps:
            self.row("F-stop-order", "gap",
                     "stop boundaries cannot be fully checked", gaps)
        else:
            self.row("F-stop-order", "pass", "stop boundaries honored",
                     [f"last record event {last_record}"])

    def judge_terminal_state(self):
        state = self.state
        attribution = {row["fact"]: row["verdict"] for row in self.rows}.get(
            "F-attribution")
        if attribution == "machine_failure_prefix":
            self.row("F-terminal-state", "gap",
                     "the run stopped at a machine-level failure prefix; "
                     "no terminal state is required", [])
            return
        if not getattr(self, "rounds", []) and any(
                row.get("fact") == "F-handoff-chain"
                and row.get("verdict") == "gap" for row in self.rows):
            self.row("F-terminal-state", "gap",
                     "terminal-round count cannot be checked because the "
                     "handoff record is incomplete", [])
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
            observed_rounds = max((row.get("round", 0)
                                   for row in getattr(self, "rounds", [])),
                                  default=0)
            if rounds_value != observed_rounds:
                problems.append(
                    f"{direction}: terminal rounds={rounds_value!r} but "
                    f"observed validator rounds={observed_rounds}")
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
        if last_record < 0:
            if rebuilds:
                record_attempts = [r for r in root_execs
                                   if ROOT_RECORD in r["command"]]
                if record_attempts or not m.run_completed:
                    self.row("F-rebuild", "gap",
                             "record completion does not establish the rebuild boundary",
                             [f"record attempts={len(record_attempts)}"])
                else:
                    self.row("F-rebuild", "fail",
                             "rebuild ran without a record call in a completed run",
                             [f"rebuild start event {r.get('call_index')}"
                              for r in rebuilds])
            else:
                self.row("F-rebuild", "gap",
                         "no completed terminal record establishes the rebuild boundary",
                         ["the run stopped before a record or the record evidence is incomplete"])
            return
        if rounds := getattr(self, "rounds", []):
            terminal = next((entry for entry in reversed(rounds)
                             if (entry["record_payload"] or {}).get(
                                 "needs_correction") is False), None)
        else:
            terminal = None
        if terminal is None:
            if rebuilds:
                self.row("F-rebuild", "fail",
                         "rebuild ran before a terminal correction record",
                         [f"rebuild start event {r.get('call_index')}"
                          for r in rebuilds])
            elif attribution == "machine_failure_prefix":
                self.row("F-rebuild", "gap",
                         "the machine failure stopped the run before a terminal record and rebuild",
                         [])
            else:
                self.row("F-rebuild", "gap",
                         "no terminal record establishes whether rebuild was required",
                         [])
            return

        terminal_record = terminal["record"]
        problems = []
        gaps = []
        if len(rebuilds) == 0 and not m.run_completed:
            self.row("F-rebuild", "gap",
                     "the run ended before rebuild completion was observed", [])
            return
        if len(rebuilds) != 1:
            if len(rebuilds) > 1 or m.run_completed:
                problems.append(f"expected exactly one rebuild exec, saw "
                                f"{len(rebuilds)}")
            else:
                gaps.append(f"rebuild count is incomplete: observed {len(rebuilds)}")
        else:
            rebuild = rebuilds[0]
            if rebuild.get("call_index") is None:
                gaps.append("rebuild start event is missing")
            elif rebuild["call_index"] <= terminal_record["index"]:
                problems.append(
                    f"rebuild started at event {rebuild['call_index']} before "
                    f"the terminal record completed at event "
                    f"{terminal_record['index']}")
            if rebuild.get("index") is None:
                gaps.append("rebuild completion event is missing")
            elif self._exec_result(rebuild) is False:
                problems.append("rebuild command returned unsuccessfully")
            elif self._exec_result(rebuild) is None:
                gaps.append("rebuild completion status is missing")
        for thread_id, records_ in m.execs.items():
            for r in records_:
                if CHILD_FINALIZE in r["command"] \
                        and r.get("call_index") is not None \
                        and r["call_index"] > terminal_record["index"]:
                    problems.append(
                        f"finalize started after the terminal record: event "
                        f"{r['call_index']} on {thread_id[:8]}")
        if problems:
            self.row("F-rebuild", "fail",
                     "terminal rebuild / no-finalize-after violated",
                     problems + gaps)
        elif gaps:
            self.row("F-rebuild", "gap",
                     "terminal rebuild completion is not fully evidenced",
                     gaps)
        else:
            self.row("F-rebuild", "pass",
                     "exactly one rebuild after the terminal record; no "
                  "finalize afterwards",
                     [f"rebuild event {rebuilds[0]['index']}"] if rebuilds
                     else [])

    # -- entry --------------------------------------------------------------

    def run(self) -> dict:
        self.judge_attribution()
        self.judge_folded_surfaces()
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
        elif self.attribution_incomplete:
            classification = "INVALID_TEST_EXECUTION"
            reason = ("root run incomplete — product failures cannot be derived "
                      "from absent child evidence")
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
