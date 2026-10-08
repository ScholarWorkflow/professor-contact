"""Mechanical judge for the S3-RT-CODEX-1 runtime evidence (issue #66).

This is the single decision program required by the current test plan
(``issue-66-test-plan-r21-stage3-write-validation-r9-2026-10-08`` §五/§六).
It folds
every required evidence surface into ONE verdict — formal delegation
attribution, the invocation-credential value chain, the per-round
prepare→validate→fixed-writer→save→record handoff, the validator-produced raw
bytes and independent fixed-writer file observations, the file-operation
behavior proven by complete command inputs and completed ``fileChange``
records, the completion-order
stop boundaries, the terminal state, and the install/fixture/snapshot
checks — and classifies per the approved business requirements:

- attribution conflicts / unsupported evidence shapes
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
- ``--writer-evidence`` independent per-call fixed-writer file observations,
                        folded into the same run conclusion
Every evidence input must carry the same non-empty ``evidence_set_id``. The
collector must bind the raw /eval response, adapter and verifier outputs to
the same run before invoking this judge.

Unknown event shapes and missing required surfaces are evidence gaps —
never silent passes.
"""
from __future__ import annotations

import argparse
import ast
import base64
import binascii
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
VALIDATOR_WRITE = "stage3-write-validation"
WRITER_EVIDENCE_SCHEMA = "issue66.writer-observation.v1"
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
    values = []
    for index, token in enumerate(tokens):
        if token == flag:
            if index + 1 >= len(tokens) or tokens[index + 1].startswith("--"):
                return None
            values.append(tokens[index + 1])
        elif token.startswith(flag + "="):
            values.append(token[len(flag) + 1:])
    # argparse store options use the final supplied value.
    return values[-1] if values else None


def stage3_command(command: str, cwd=None, expected_script=None) -> str | None:
    """Identify a contact_state.py subcommand from the actual argv."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    for index, token in enumerate(tokens[:-1]):
        if Path(token).name == "contact_state.py" \
                and tokens[index + 1].startswith("stage3-"):
            if expected_script is not None:
                calls, uncertain = stage3_entry_calls(command, cwd)
                matching = [subcommand for subcommand, path in calls
                            if path == str(Path(expected_script).resolve())]
                return matching[0] if len(matching) == 1 and not uncertain else None
            return tokens[index + 1]
    return None


def stage3_entry_calls(command, cwd):
    """Resolve actual script argv, never a script name inside other arguments.

    Supported shells may compose commands and change directory. Unknown
    launchers, expansions and interpreter code are evidence gaps, rather than
    evidence that the installed program executed.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return [], True
    segments, current = [], []
    for token in tokens:
        if token in {";", "&&", "||", "|", "&"}:
            if current:
                segments.append(current)
                current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    base = Path(cwd) if isinstance(cwd, str) and Path(cwd).is_absolute() else None
    calls, uncertain = [], any(token in {"||", "|", "&"} for token in tokens)
    for argv in segments:
        if not argv:
            continue
        if argv[0] == "cd" and len(argv) == 2:
            directory = Path(argv[1])
            if any(char in argv[1] for char in "$`*?"):
                base = None
            else:
                base = directory if directory.is_absolute() else base / directory if base else None
            continue
        candidates = [index for index, token in enumerate(argv[:-1])
                      if Path(token).name == "contact_state.py"
                      and argv[index + 1].startswith("stage3-")]
        if not candidates:
            continue
        # Literal environment assignments can prefix an actual interpreter.
        offset = 0
        while offset < len(argv) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", argv[offset]):
            offset += 1
        if offset < len(argv) and Path(argv[offset]).name == "uv":
            offset += 1
            if offset >= len(argv) or argv[offset] != "run":
                uncertain = True
                continue
            offset += 1
            value_flags = {"--python", "--with", "--with-requirements", "--project", "--cache-dir"}
            boolean_flags = {"--no-project", "--no-sync", "--offline", "--locked", "--frozen", "--isolated", "--managed-python", "--no-managed-python"}
            while offset < len(argv) and argv[offset].startswith("-"):
                option = argv[offset]
                if option == "--":
                    offset += 1
                    break
                if option in value_flags:
                    offset += 2
                elif option in boolean_flags or option.split("=", 1)[0] in value_flags and "=" in option:
                    offset += 1
                else:
                    break
        if offset < len(argv) and re.fullmatch(r"(?:python(?:\d+(?:\.\d+)*)?|pypy(?:\d+)?)", Path(argv[offset]).name):
            offset += 1
            while offset < len(argv) and argv[offset] in {"-B", "-u", "-I", "-E", "-s", "-S", "-O", "-OO"}:
                offset += 1
            if offset < len(argv) and argv[offset] == "--":
                offset += 1
        if len(candidates) != 1 or candidates[0] != offset:
            uncertain = True
            continue
        script = argv[offset]
        if any(char in script for char in "$`*?") or any(token in {"|", "&", "<<"} for token in tokens):
            uncertain = True
            continue
        path = Path(script)
        if not path.is_absolute() and base is None:
            uncertain = True
            continue
        calls.append((argv[offset + 1], str((path if path.is_absolute() else base / path).resolve())))
    return calls, uncertain


def command_file_behavior(command: str, cwd: str | None, *,
                          ignored_stage3_subcommands=(), expected_stage3_script=None):
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
        control_flow = (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
            ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While,
            ast.Try, ast.TryStar, ast.With, ast.AsyncWith, ast.Match,
            ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
            ast.BoolOp, ast.comprehension,
        )
        parents = {child: parent for parent in ast.walk(tree)
                   for child in ast.iter_child_nodes(parent)}

        def conditional_or_deferred(node):
            parent = parents.get(node)
            while parent is not None:
                if isinstance(parent, control_flow):
                    return True
                parent = parents.get(parent)
            return False

        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        recognized = set()
        for statement in tree.body:
            if isinstance(statement, ast.Assign):
                if not all(isinstance(target, ast.Name) for target in statement.targets):
                    unknown = True
            elif not isinstance(statement, (ast.Import, ast.ImportFrom, ast.Expr)):
                unknown = True
        if any(isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               and any(isinstance(target, ast.Name) and target.id in
                       {"open", "os", "shutil", "pathlib", "Path"}
                       for target in ast.walk(node)
                       if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store))
               for node in ast.walk(tree)):
            unknown = True
        for node in calls:
            if conditional_or_deferred(node):
                unknown = True
                recognized.add(id(node))
                continue
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
        stage3 = next((argv[position + 1] for position, token in
                       enumerate(argv[:-1])
                       if Path(token).name == "contact_state.py"
                       and argv[position + 1].startswith("stage3-")), None)
        bound_stage3 = (stage3_command(shlex.join(argv), str(base), expected_stage3_script)
                        if expected_stage3_script is not None else None)
        if stage3 in ignored_stage3_subcommands and bound_stage3 == stage3:
            continue
        executable = Path(argv[0]).name
        if executable in {"cat", "head", "tail", "jq", "rg", "grep", "ls",
                          "pwd", "wc", "file"}:
            # These switches execute programs, load mutable code, or change
            # the command's role. A command name alone is no read-only proof.
            if any(token in {"--pre", "--pre-glob", "-L", "--library-path"}
                   or token.startswith(("--pre=", "--pre-glob=", "--library-path="))
                   for token in argv[1:]):
                unknown = True
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
        if not isinstance(response, dict):
            self.gaps.append("eval response is not an object")
            response = {}
        if not isinstance(adapter, dict):
            self.gaps.append("adapter evidence is not an object")
            adapter = {}
        self.evidence_set_id = response.get("evidence_set_id")
        self.adapter_evidence_set_id = adapter.get("evidence_set_id")
        output = response.get("output")
        if not isinstance(output, dict):
            self.gaps.append("eval response output is missing or not an object")
            output = {}
        self.root_id = output.get("thread_id")
        if not isinstance(self.root_id, str) or not self.root_id:
            self.gaps.append("eval response root thread_id is missing or invalid")
            self.root_id = None
        raw_events = output.get("app_server_events")
        if not isinstance(raw_events, list):
            self.gaps.append("app_server_events is missing or not an array")
            raw_events = []
        self.events = []
        for index, raw_event in enumerate(raw_events):
            if not isinstance(raw_event, dict):
                self.gaps.append(f"event {index}: event is not an object")
                raw_event = {}
            event = dict(raw_event)
            message = event.get("message")
            if not isinstance(message, dict):
                self.gaps.append(f"event {index}: message is missing or not an object")
                message = {}
            else:
                message = dict(message)
            method = message.get("method")
            if method is not None and not isinstance(method, str):
                self.gaps.append(f"event {index}: message method is not a string")
                method = None
            message["method"] = method
            params = message.get("params")
            if params is not None and not isinstance(params, dict):
                self.gaps.append(f"event {index}: params is not an object")
                params = {}
            elif params is None:
                params = {}
            else:
                params = dict(params)
            for key in ("threadId", "turnId"):
                value = params.get(key)
                if value is not None and (not isinstance(value, str) or not value):
                    self.gaps.append(
                        f"event {index}: {key} is not a nonempty string")
                    params[key] = None
            if params.get("cwd") is not None \
                    and not isinstance(params.get("cwd"), str):
                self.gaps.append(f"event {index}: cwd is not a string")
                params["cwd"] = None
            item = params.get("item")
            if item is not None and not isinstance(item, dict):
                self.gaps.append(f"event {index}: item is not an object")
                item = {}
            elif item is None:
                item = {}
            else:
                item = dict(item)
            for key in ("id", "call_id", "agentThreadId", "name", "type",
                        "role", "kind", "status"):
                value = item.get(key)
                if value is not None and not isinstance(value, str):
                    self.gaps.append(
                        f"event {index}: item {key} is not a string")
                    item[key] = None
            for key in ("command", "arguments", "aggregatedOutput", "cwd"):
                value = item.get(key)
                if value is not None and not isinstance(value, str):
                    self.gaps.append(
                        f"event {index}: item {key} is not a string")
                    item[key] = None
            exit_code = item.get("exitCode")
            if exit_code is not None and (
                    isinstance(exit_code, bool) or not isinstance(exit_code, int)):
                self.gaps.append(f"event {index}: item exitCode is not an integer")
                item["exitCode"] = None
            params["item"] = item
            message["params"] = params
            event["message"] = message
            self.events.append(event)
        self.invalid_sequence_indices = set()
        sequence_values = [event.get("seq") if isinstance(event, dict) else None
                           for event in self.events]
        if self.events and (
                any(isinstance(value, bool) or not isinstance(value, int)
                    for value in sequence_values)
                or any(right <= left for left, right in
                       zip(sequence_values, sequence_values[1:]))):
            self.invalid_sequence_indices = set(range(len(self.events)))
            self.gaps.append(
                "app_server_events seq values are missing, invalid, duplicated, "
                "or out of order")
        self.run_completed = False
        self.root_turn_status = None
        self.root_turn_completion_count = 0
        valid_turn_statuses = {"completed", "interrupted", "failed", "inProgress"}
        for index, event in enumerate(self.events):
            message = event["message"]
            if message.get("method") != "turn/completed":
                continue
            params = message.get("params") or {}
            thread_id = params.get("threadId")
            turn = params.get("turn")
            turn_status = turn.get("status") if isinstance(turn, dict) else None
            if not isinstance(thread_id, str) or not thread_id \
                    or not isinstance(turn, dict) \
                    or not isinstance(turn.get("id"), str) or not turn.get("id") \
                    or not isinstance(turn_status, str) \
                    or turn_status not in valid_turn_statuses:
                self.gaps.append(
                    f"event {index}: turn/completed lacks a valid threadId, turn id, or status")
                continue
            if thread_id != self.root_id:
                continue
            self.root_turn_completion_count += 1
            status = turn_status
            if status == "completed":
                self.root_turn_status = status
                self.run_completed = True
            elif status in {"failed", "interrupted"}:
                self.root_turn_status = status
                self.gaps.append(
                    f"event {index}: root turn ended {status}; external failure "
                    "is not established by turn status alone")
            else:
                self.root_turn_status = status
                self.gaps.append(
                    f"event {index}: root turn/completed has nonterminal status {status!r}")
        if self.root_turn_completion_count > 1:
            self.gaps.append("root thread has multiple turn/completed events")
        # -- formal relations (adapter) ------------------------------------
        dispatch = adapter.get("dispatch")
        relations = dispatch.get("thread_relations") \
            if isinstance(dispatch, dict) else None
        self.relation_surface_complete = isinstance(relations, list)
        self.relations = []
        if isinstance(relations, list):
            for index, relation in enumerate(relations):
                if not isinstance(relation, dict):
                    self.gaps.append(
                        f"adapter thread_relations entry {index} is not an object")
                    continue
                self.relations.append(relation)
        child_reads = adapter.get("child_thread_reads")
        if not isinstance(child_reads, dict):
            if child_reads is not None:
                self.gaps.append("child_thread_reads is not an object")
            child_reads = {}
        child_entries = child_reads.get("entries")
        if not isinstance(child_entries, list):
            if child_entries is not None:
                self.gaps.append("child_thread_reads.entries is not an array")
            child_entries = []
        self.child_reads = []
        for index, entry in enumerate(child_entries):
            if not isinstance(entry, dict):
                self.gaps.append(
                    f"adapter child_thread_reads entry {index} is not an object")
                continue
            thread_id = entry.get("thread_id")
            if thread_id is not None and not isinstance(thread_id, str):
                self.gaps.append(
                    f"adapter child_thread_reads entry {index} thread_id is invalid")
                continue
            if entry.get("effective_role") is not None \
                    and not isinstance(entry.get("effective_role"), str):
                self.gaps.append(
                    f"adapter child_thread_reads entry {index} role is invalid")
                continue
            self.child_reads.append(entry)
        self.read_roles = {entry["thread_id"]: entry.get("effective_role")
                           for entry in self.child_reads
                           if entry.get("thread_id")}
        delegation = adapter.get("delegation")
        delegation = delegation if isinstance(delegation, dict) else {}
        self.delegation_state = delegation.get("state")
        self.adapter_children = delegation.get("child_thread_ids")
        if isinstance(self.adapter_children, list):
            if any(not isinstance(child, str) or not child
                   for child in self.adapter_children):
                self.gaps.append("delegation child_thread_ids contains invalid ids")
                self.adapter_children = [child for child in self.adapter_children
                                         if isinstance(child, str) and child]
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
                except (json.JSONDecodeError, TypeError):
                    self.gaps.append(
                        f"event {index}: spawn_agent arguments unparsable")
                    arguments = {}
                if not isinstance(arguments, dict):
                    self.gaps.append(
                        f"event {index}: spawn_agent arguments are not an object")
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
        self.incomplete_execs = []
        pending_execs = {}
        seen_exec_starts = set()
        start_statuses = {"inProgress", "started"}
        completion_statuses = {"completed", "failed", "errored", "declined"}
        for index, event in enumerate(self.events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if item.get("type") != "commandExecution":
                continue
            method = message.get("method")
            thread_id = params.get("threadId")
            turn_id = params.get("turnId")
            item_id = item.get("id")
            call_id = item.get("call_id")
            status = item.get("status")
            identity = (thread_id, turn_id, item_id)
            if method not in {"item/started", "item/completed"}:
                self.incomplete_execs.append({"index": index,
                                              "thread_id": thread_id,
                                              "turn_id": turn_id,
                                              "item_id": item_id,
                                              "call_id": call_id})
                self.gaps.append(
                    f"event {index}: commandExecution has unsupported lifecycle method")
                continue
            if not all(isinstance(value, str) and value
                       for value in (thread_id, turn_id, item_id)):
                self.incomplete_execs.append({"index": index,
                                              "thread_id": thread_id,
                                              "turn_id": turn_id,
                                              "item_id": item_id,
                                              "call_id": call_id})
                self.gaps.append(
                    f"event {index}: commandExecution lacks thread, turn, or item identity")
                continue
            record = {
                "call_index": index,
                "index": None,
                "thread_id": thread_id,
                "turn_id": turn_id,
                "item_id": item_id,
                "call_id": call_id,
                "command": item.get("command") or "",
                "cwd": item.get("cwd") or params.get("cwd"),
                "output": None,
                "exit_code": None,
                "status": status,
                "truncated": False,
                "actions": [],
                "completion_method": method,
            }
            key = identity
            bucket = self.execs.setdefault(thread_id, [])
            if method == "item/started":
                if status not in start_statuses:
                    self.incomplete_execs.append({
                        "index": index, "thread_id": thread_id,
                        "turn_id": turn_id, "item_id": item_id,
                        "call_id": call_id})
                    self.gaps.append(
                        f"event {index}: commandExecution start status is malformed")
                    continue
                if key in pending_execs or key in seen_exec_starts:
                    self.incomplete_execs.append({
                        "index": index, "thread_id": thread_id,
                        "turn_id": turn_id, "item_id": item_id,
                        "call_id": call_id})
                    self.gaps.append(
                        f"event {index}: duplicate or reused commandExecution identity")
                    continue
                seen_exec_starts.add(key)
                pending_execs[key] = record
                continue
            if status not in completion_statuses:
                self.incomplete_execs.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id,
                    "call_id": call_id})
                self.gaps.append(
                    f"event {index}: commandExecution completion status is malformed")
                continue
            prior = pending_execs.pop(key, None)
            if prior is None:
                self.incomplete_execs.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id,
                    "call_id": call_id})
                self.gaps.append(
                    f"event {index}: commandExecution completion has no matching start")
                continue
            if ((prior.get("call_id") is None) != (call_id is None)
                    or prior.get("call_id") != call_id):
                self.incomplete_execs.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id,
                    "call_id": call_id})
                self.gaps.append(
                    f"event {index}: commandExecution call id differs from its start")
                continue
            if prior["command"] and record["command"] \
                    and prior["command"] != record["command"]:
                self.incomplete_execs.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id,
                    "call_id": call_id})
                self.gaps.append(
                    f"event {index}: commandExecution command differs from its start")
                continue
            if prior["cwd"] and record["cwd"] \
                    and prior["cwd"] != record["cwd"]:
                self.incomplete_execs.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id,
                    "call_id": call_id})
                self.gaps.append(
                    f"event {index}: commandExecution cwd differs from its start")
                continue
            prior.update({name: value for name, value in record.items()
                          if name not in {"call_index", "command", "cwd",
                                          "thread_id", "turn_id", "item_id",
                                          "call_id"}})
            prior["command"] = prior["command"] or record["command"]
            prior["cwd"] = prior["cwd"] or record["cwd"]
            prior["index"] = index
            prior["output"] = item.get("aggregatedOutput")
            prior["exit_code"] = item.get("exitCode")
            prior["status"] = status
            prior["truncated"] = bool(
                prior["output"] and TRUNCATION_MARKER in prior["output"])
            if not prior["command"]:
                self.incomplete_execs.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id,
                    "call_id": call_id})
                self.gaps.append(
                    f"event {index}: command completion has no command input")
            bucket.append(prior)
        for record in pending_execs.values():
            self.execs.setdefault(record["thread_id"], []).append(record)
            self.incomplete_execs.append({
                "index": record["call_index"],
                "thread_id": record["thread_id"],
                "turn_id": record.get("turn_id"),
                "item_id": record.get("item_id"),
                "call_id": record.get("call_id")})
            self.gaps.append(
                f"event {record['call_index']}: commandExecution input has no completion")
        # -- actual patch/file change events; never commandActions -----------
        self.file_changes = {}
        self.incomplete_file_changes = []
        pending_file_changes = {}
        seen_file_change_starts = set()
        for index, event in enumerate(self.events):
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if item.get("type") != "fileChange":
                continue
            method = message.get("method")
            if method not in {"item/started", "item/completed"}:
                self.incomplete_file_changes.append({
                    "index": index, "thread_id": params.get("threadId"),
                    "turn_id": params.get("turnId"),
                    "item_id": item.get("id")})
                self.gaps.append(
                    f"event {index}: fileChange has an unsupported lifecycle event")
                continue
            thread_id = params.get("threadId")
            turn_id = params.get("turnId")
            item_id = item.get("id")
            status = item.get("status")
            changes = item.get("changes")
            key = (thread_id, turn_id, item_id)
            if not all(isinstance(value, str) and value
                       for value in (thread_id, turn_id, item_id)) \
                    or not isinstance(changes, list):
                self.incomplete_file_changes.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id})
                self.gaps.append(
                    f"event {index}: fileChange lacks item identity or structured changes")
                continue
            if method == "item/started":
                if status != "inProgress" or key in pending_file_changes \
                        or key in seen_file_change_starts:
                    self.incomplete_file_changes.append({
                        "index": index, "thread_id": thread_id,
                        "turn_id": turn_id, "item_id": item_id})
                    self.gaps.append(
                        f"event {index}: fileChange start state is malformed or duplicated")
                    continue
                pending_file_changes[key] = {
                    "index": index, "changes": changes,
                    "thread_id": thread_id, "turn_id": turn_id,
                    "item_id": item_id}
                seen_file_change_starts.add(key)
                continue
            started = pending_file_changes.pop(key, None)
            successful = status == "completed"
            if started is None or not successful:
                self.incomplete_file_changes.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id})
                reason = ("has no matching start" if started is None else
                          "did not complete successfully")
                self.gaps.append(f"event {index}: fileChange {reason}")
            elif started["changes"] != changes:
                self.incomplete_file_changes.append({
                    "index": index, "thread_id": thread_id,
                    "turn_id": turn_id, "item_id": item_id})
                self.gaps.append(
                    f"event {index}: fileChange start and completion changes differ")
            for change in changes:
                if not isinstance(change, dict):
                    self.incomplete_file_changes.append({
                        "index": index, "thread_id": thread_id,
                        "turn_id": turn_id, "item_id": item_id})
                    self.gaps.append(f"event {index}: fileChange entry is not an object")
                    continue
                kind = change.get("kind")
                operation = kind.get("type") if isinstance(kind, dict) else None
                move_path = kind.get("move_path") if operation == "update" else None
                path = change.get("path")
                if set(change) != {"path", "kind", "diff"} \
                        or not isinstance(kind, dict) \
                        or "type" not in kind \
                        or not set(kind) <= {"type", "move_path"} \
                        or not isinstance(operation, str) \
                        or operation not in {"add", "delete", "update"} \
                        or not isinstance(path, str) or not path \
                        or not isinstance(change.get("diff"), str) \
                        or (operation == "update" and "move_path" in kind
                            and (not isinstance(move_path, str) or not move_path)) \
                        or (operation != "update" and isinstance(kind, dict)
                            and "move_path" in kind):
                    self.incomplete_file_changes.append({
                        "index": index, "thread_id": thread_id,
                        "turn_id": turn_id, "item_id": item_id})
                    self.gaps.append(
                        f"event {index}: fileChange change is unsupported or malformed")
                    continue
                self.file_changes.setdefault(thread_id, []).append({
                    "index": index, "turn_id": turn_id,
                    "item_id": item_id, "status": status, "path": path,
                    "operation": operation,
                    "move_path": move_path,
                    "diff": change.get("diff"),
                    "completed": successful and started is not None
                    and started["changes"] == changes,
                    # App Server fileChange says which patch hunk ran; it does
                    # not expose the pre-write state needed to prove O_EXCL.
                    "exclusive": None if operation == "add" else False})
        for pending in pending_file_changes.values():
            self.incomplete_file_changes.append({
                "index": pending["index"],
                "thread_id": pending["thread_id"],
                "turn_id": pending["turn_id"],
                "item_id": pending["item_id"]})
            self.gaps.append(
                f"event {pending['index']}: fileChange start has no completion")
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
        self.surfaces = surfaces          # install/fixture/routing/pre/post/writer
        self.rows: list[dict] = []
        self.attribution_invalid = False
        self.attribution_incomplete = False
        self.first_finalize = None
        self.external_declines = []
        install = surfaces.get("install") or {}
        consumer = install.get("consumer_root")
        self.installed_script = (str(Path(consumer) / ".agents/skills/professor-contact/scripts/contact_state.py")
                                 if isinstance(consumer, str) and Path(consumer).is_absolute() else None)

    def _stage3_command(self, record):
        if self.installed_script is None:
            return None
        return stage3_command(record.get("command", ""), record.get("cwd"), self.installed_script)

    def judge_entry_binding(self):
        if self.installed_script is None:
            self.row("F-entry-binding", "invalid", "installation evidence lacks an absolute consumer root", [])
            return
        wrong, unknown, observed = [], [], []
        for records in self.m.execs.values():
            for record in records:
                command = record.get("command", "")
                if stage3_command(command) is None:
                    if "contact_state.py" in command and "stage3-" in command:
                        unknown.append(f"event {record['call_index']}: script text does not expose actual executable argv")
                    continue
                calls, uncertain = stage3_entry_calls(command, record.get("cwd"))
                if uncertain or not calls:
                    unknown.append(f"event {record['call_index']}: actual executable argv cannot be resolved")
                    # A candidate inside an uncertain shell expression does
                    # not independently prove that this program executed.
                    continue
                for subcommand, path in calls:
                    observed.append(f"event {record['call_index']}: {subcommand}: {path}")
                    if path != str(Path(self.installed_script).resolve()):
                        if self._exec_result(record) is True:
                            wrong.append(observed[-1])
                        else:
                            unknown.append(observed[-1] + ": successful execution is not established")
        if wrong:
            self.row("F-entry-binding", "fail", "actual Stage-3 call uses a program outside the verified installation", wrong, independent=True)
            if unknown:
                self.row("F-entry-observation", "gap", "other Stage-3 calls lack executable evidence; the completed independent violation is retained", unknown)
        elif unknown:
            self.row("F-entry-binding", "invalid", "actual Stage-3 executable is not supported by the observed command input", unknown)
        else:
            self.row("F-entry-binding", "pass", "actual Stage-3 executable paths bind to the verified consumer installation", observed)

    def row(self, fact_id, verdict, detail, evidence, *, independent=False):
        row = {"fact": fact_id, "verdict": verdict,
               "detail": detail, "evidence": evidence}
        if independent:
            row["independent"] = True
        self.rows.append(row)

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
        layer requires each named check and never treats absent or unsupported
        output as success.
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
                        for name in ("install", "fixture", "routing", "pre", "post", "writer")]
        evidence_ids.extend((
            ("eval-response", self.m.evidence_set_id),
            ("adapter-output", self.m.adapter_evidence_set_id),
        ))
        missing_ids = [name for name, value in evidence_ids
                       if not isinstance(value, str) or not value.strip()]
        observed_ids = {value for _name, value in evidence_ids
                        if isinstance(value, str) and value.strip()}
        if missing_ids:
            self.row("F-evidence-set", "gap",
                     "run evidence identifiers are missing from one or more inputs",
                     missing_ids)
        elif len(observed_ids) > 1:
            self.row("F-evidence-set", "invalid",
                     "evidence inputs mix different run identifiers",
                     [f"{name}={value}" for name, value in evidence_ids])
        else:
            self.row("F-evidence-set", "pass",
                     "all inputs are bound to one run evidence set",
                     [next(iter(observed_ids))])
        self._fold_required_checks(
            "install", "F-install",
            ("supported_install_entry_completed",), "supported installation entry")
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
                    if (machine_prefix or self._declined_business_operations()) and bad_names <= {
                            "root_direct_spawn_child_count"}:
                        self.row("F-routing-verifier", "gap",
                                 "root child count is incomplete after a confirmed external failure",
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
            stage4_files = self._stage4_files()
            if stage4_files is None:
                self.row("F-stage4-absence", "gap",
                         "program_root is missing or unreadable; Stage-4 absence cannot be checked",
                         [])
            elif stage4_files:
                self.row("F-stage4-absence", "fail",
                         "Stage-4 selection / mail-input artifacts must be absent",
                         stage4_files)
            else:
                self.row("F-stage4-absence", "pass",
                         "Stage-4 selection / mail-input artifacts absent", [])

    def _stage4_files(self):
        if self.program_root is None or not self.program_root.is_dir():
            return None
        found = []
        try:
            for pattern in ("套磁选择.json", "邮件输入.json"):
                found.extend(str(p) for p in self.program_root.rglob(pattern))
        except OSError:
            return None
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
            elif (machine_prefix or self._declined_business_operations()
                  or not m.run_completed) and legal_prefix:
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

    def _declined_business_operations(self, thread=None, before=None):
        """Only paired, explicitly declined business tools establish a blocker."""
        roles = {child: spawn["agent_type"]
                 for spawn, child in self.m.ordered_children() if child}
        declines = []
        for owner, records in self.m.execs.items():
            if thread is not None and owner != thread:
                continue
            for record in records:
                index = record.get("index")
                if record.get("status") != "declined" or index is None \
                        or before is not None and index >= before:
                    continue
                operations, _unknown = command_file_behavior(
                    record.get("command", ""), record.get("cwd"))
                if stage3_command(record.get("command", "")) is not None \
                        or roles.get(owner) == GENERATOR_AGENT \
                        or roles.get(owner) == VALIDATOR_AGENT and any(
                            kind == "write" for kind, _path, _exclusive in operations):
                    declines.append(record)
        return declines

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
                    and self._stage3_command(record) == needle:
                return record
        return None

    @staticmethod
    def _exec_result(record):
        """Return success/failure/unknown from the paired actual call result."""
        if record is None or record.get("index") is None:
            return None
        if record.get("status") == "declined":
            return None
        if record.get("status") in {"failed", "errored"}:
            return False
        if record.get("exit_code") is not None and record.get("exit_code") != 0:
            return False
        if record.get("status") == "completed" and record.get("exit_code") == 0:
            return True
        return None

    @classmethod
    def _is_writer_error_message(cls, message):
        """Recognize the fixed writer's structured error return message."""
        raw = message.get("bytes") if isinstance(message, dict) else None
        if not isinstance(raw, bytes):
            return False
        try:
            payload = cls._strict_json_value(raw.decode("utf-8"))
        except UnicodeDecodeError:
            return False
        return isinstance(payload, dict) \
            and payload.get("status") == "error" \
            and isinstance(payload.get("reason_code"), str) \
            and bool(payload.get("reason_code")) \
            and isinstance(payload.get("message"), str)

    def _result_payload(self, record, label, problems, gaps):
        if record is not None and record.get("status") == "declined":
            if not any(item.get("index") == record.get("index")
                       and item.get("thread_id") == record.get("thread_id")
                       for item in self.external_declines):
                self.external_declines.append({
                    "index": record.get("index"),
                    "thread_id": record.get("thread_id"),
                    "command": record.get("command")})
            gaps.append(f"{label}: tool call was explicitly declined")
            return None
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
        if "status" not in payload:
            gaps.append(f"{label}: structured return misses status")
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
                subcommand = self._stage3_command(record)
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
        fixture = self.surfaces.get("fixture") or {}
        observation = fixture.get("credential_observation")
        if not isinstance(observation, dict):
            gaps.append("credential file bytes and source observation are missing")
        else:
            raw_text = observation.get("invocation_utf8")
            if not isinstance(raw_text, str):
                gaps.append("credential observation misses the original UTF-8 bytes")
            else:
                try:
                    raw = raw_text.encode("utf-8")
                    document = json.loads(raw_text)
                except (UnicodeEncodeError, json.JSONDecodeError):
                    document = None
                    gaps.append("credential observation has invalid UTF-8/JSON")
                if not isinstance(document, dict):
                    gaps.append("credential observation is not a credential object")
                else:
                    if sha256_bytes(raw) != real_sha or observation.get("invocation_file") != real_file:
                        problems.append("observed credential bytes or file differ from capture")
                    if self._path_identity(document.get("professor_dir"), capture.get("cwd")) != self._path_identity(captured["professor_dir"], capture.get("cwd")):
                        problems.append("credential document professor differs from capture")
                    profile_args = self._flag_values(capture["command"], "--profile")
                    expected_profile = profile_args[0] if profile_args else None
                    if self._path_identity(document.get("profile_path"), capture.get("cwd")) != self._path_identity(expected_profile, capture.get("cwd")):
                        problems.append("credential profile path differs from actual capture input")
                    program_args = self._flag_values(capture["command"], "--program-root")
                    if program_args and self._path_identity(document.get("program_root"), capture.get("cwd")) != self._path_identity(program_args[-1], capture.get("cwd")):
                        problems.append("credential program root differs from actual capture input")
                    if document.get("profile_sha256") != captured.get("profile_fingerprint"):
                        problems.append("credential profile digest differs from plan fingerprint")
                    if expected_profile is not None:
                        profile_text = observation.get("profile_utf8")
                        if not isinstance(profile_text, str):
                            gaps.append("actual profile bytes are missing")
                        elif sha256_bytes(profile_text.encode("utf-8")) != document.get("profile_sha256"):
                            problems.append("actual profile bytes differ from credential source digest")
        profile_fingerprint = captured.get("profile_fingerprint")
        if profile_fingerprint is not None:
            if not isinstance(self.state, dict) \
                    or "profile_fingerprint" not in self.state:
                gaps.append("committed candidate state misses the captured profile fingerprint")
            elif self.state["profile_fingerprint"] != profile_fingerprint:
                problems.append("committed candidate state profile fingerprint differs from capture")
        elif isinstance(self.state, dict) \
                and self.state.get("profile_fingerprint") is not None:
            problems.append("committed candidate state has a profile fingerprint absent from capture")
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
        self.credential_values = {"file": real_file, "sha": real_sha,
                                  "professor": captured.get("professor"),
                                  "professor_dir": captured.get("professor_dir")}
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
        self.prepared_rounds = []
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
            generators = self._generator_children()
            round_generator = (generators[round_no - 1]
                               if len(generators) >= round_no else None)
            round_commits = [r for r in m.execs.get(round_generator, [])
                             if self._stage3_command(r) == CHILD_FINALIZE]
            if len(round_commits) != 1:
                problems.append(f"round {round_no}: expected exactly one corresponding generator commit")
            elif round_commits[0].get("index") is None:
                gaps.append(f"round {round_no}: corresponding commit completion is missing")
            elif round_commits[0]["index"] >= prepare["call_index"]:
                problems.append(f"round {round_no}: prepare began before its generator commit completed")
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
            prepare_fields = ("professor", "professor_dir", "round",
                              "handoff_file", "handoff_sha256", "output_file",
                              "validation_file", "render_sha256")
            missing_prepare = [field for field in prepare_fields
                               if field not in prep_payload
                               or prep_payload[field] is None
                               or prep_payload[field] == ""]
            if missing_prepare:
                gaps.append(
                    f"round {round_no}: prepare return misses required fields "
                    f"{missing_prepare}")
                break
            if type(prepared_round) is not int or prepared_round != round_no:
                problems.append(
                    f"round {round_no}: prepare returned round "
                    f"{prepared_round!r}")
                break
            if output_file == validation_file:
                problems.append(f"round {round_no}: source and saved target must differ")
            if any(output_file in (previous["output_file"], previous["validation_file"])
                   or validation_file in (previous["output_file"], previous["validation_file"])
                   for previous in rounds):
                problems.append(f"round {round_no}: source or saved target reuses a previous round")
            credential = getattr(self, "credential_values", {})
            if not credential:
                gaps.append(f"round {round_no}: captured credential binding is unavailable")
            if credential.get("professor") and prep_payload.get("professor") != credential.get("professor"):
                problems.append(
                    f"round {round_no}: prepare professor differs from the "
                    "captured invocation source")
            if credential.get("professor_dir") and self._path_identity(prep_payload.get("professor_dir"),
                                   prepare.get("cwd")) != self._path_identity(
                                       credential.get("professor_dir"),
                                       prepare.get("cwd")):
                problems.append(
                    f"round {round_no}: prepare professor_dir differs from "
                    "the captured invocation source")
            for flag, value in (("--invocation-file", credential.get("file")),
                                ("--invocation-sha256", credential.get("sha"))):
                if value and self.flag_value(prepare["command"], flag) != value:
                    problems.append(
                        f"round {round_no}: prepare {flag} does not use the "
                        "captured invocation credential")
            if prepare["index"] >= spawn["index"]:
                problems.append(
                    f"round {round_no}: prepare completion did not precede "
                    "the validator spawn input")
            pending_entry = {"round": round_no, "child": child,
                             "prepare": prepare, "output_file": output_file,
                             "validation_file": validation_file,
                             "render_sha256": render_sha,
                             "save_payload": {}, "record_payload": {}}
            self.prepared_rounds.append(pending_entry)
            child_completion = m.activity_completion_index.get(spawn["call_id"])
            if child_completion is None:
                gaps.append(
                    f"round {round_no}: validator child has no correlated "
                    "completion event")
                break
            failed_writers = [record for record in m.execs.get(child, [])
                              if self._writer_call(record) is not None
                              and self._exec_result(record) is False
                              and record.get("call_index", -1) < child_completion]
            save = self._root_exec(ROOT_SAVE, after=child_completion + 1)
            if failed_writers:
                if save is not None:
                    problems.append(
                        f"round {round_no}: root save was called after the "
                        "fixed writer failed")
                else:
                    gaps.append(
                        f"round {round_no}: fixed writer failed and the "
                        "handoff correctly stopped before save")
                break
            if save is None:
                if self._declined_business_operations(child, child_completion):
                    gaps.append(f"round {round_no}: validator production was declined; save was not reached")
                else:
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
            pending_entry["save_payload"] = save_payload or {}
            if save_payload is None:
                break
            save_fields = ("professor", "professor_dir", "round",
                           "render_sha256", "validation_file",
                           "validation_sha256")
            missing_save = [field for field in save_fields
                            if field not in save_payload
                            or save_payload[field] is None
                            or save_payload[field] == ""]
            if missing_save:
                gaps.append(
                    f"round {round_no}: save return misses required fields "
                    f"{missing_save}")
                break
            validation_sha = save_payload.get("validation_sha256")
            saved_file = save_payload.get("validation_file")
            if save_payload.get("professor") != prep_payload.get("professor") \
                    or self._path_identity(save_payload.get("professor_dir"),
                                           save.get("cwd")) != self._path_identity(
                                               prep_payload.get("professor_dir"),
                                               save.get("cwd")):
                problems.append(
                    f"round {round_no}: save return changed the prepared "
                    "professor source")
            if saved_file != validation_file \
                    or type(save_payload.get("round")) is not int \
                    or save_payload.get("round") != round_no \
                    or save_payload.get("render_sha256") != render_sha:
                problems.append(
                    f"round {round_no}: save return does not preserve the "
                    "prepared validation path, round and render")
            if round_no > 1:
                previous_validation = rounds[-1]["validation_file"] if rounds else None
                generator = self._generator_children()
                correction = [r for r in m.execs.get(generator[-1], [])
                              if self._stage3_command(r) == CHILD_PLAN
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
            pending_entry["record"] = record
            pending_entry["record_payload"] = record_payload or {}
            if record_payload is None:
                break
            record_fields = ("state_path", "round", "render_sha256",
                             "validation_input_sha256", "needs_correction",
                             "terminal")
            missing_record = [field for field in record_fields
                              if field not in record_payload
                              or record_payload[field] is None
                              or record_payload[field] == ""]
            if missing_record:
                gaps.append(
                    f"round {round_no}: record return misses required fields "
                    f"{missing_record}")
                break
            if not isinstance(record_payload.get("needs_correction"), bool) \
                    or not isinstance(record_payload.get("terminal"), bool):
                gaps.append(
                    f"round {round_no}: record correction/terminal values "
                    "are not boolean")
                break
            state_path = record_payload.get("state_path")
            state_dir = (str(Path(state_path).parent)
                         if isinstance(state_path, str) else None)
            if self._path_identity(state_dir, record.get("cwd")) != \
                    self._path_identity(prep_payload.get("professor_dir"),
                                        record.get("cwd")):
                problems.append(
                    f"round {round_no}: record state_path belongs to a "
                    "different professor directory")
            if type(record_payload.get("round")) is not int \
                    or record_payload.get("round") != round_no \
                    or record_payload.get("render_sha256") != render_sha \
                    or record_payload.get("validation_input_sha256") != validation_sha:
                problems.append(
                    f"round {round_no}: record return does not summarize "
                    "the round/render/bytes returned by save")
            # Current product returns state_path rather than professor/path
            # again. If those fields are present in a supported projection,
            # they must agree; absent optional fields are not invented duties.
            if "professor" in record_payload and record_payload["professor"] != prep_payload["professor"]:
                problems.append(f"round {round_no}: record professor differs from prepare")
            if "validation_file" in record_payload and record_payload["validation_file"] != validation_file:
                problems.append(f"round {round_no}: record validation_file differs from save")
            if record_payload.get("terminal") is record_payload.get(
                    "needs_correction"):
                problems.append(
                    f"round {round_no}: record terminal flag disagrees with "
                    "needs_correction")
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

    @staticmethod
    def _writer_identity(value):
        if not isinstance(value, dict) or set(value) != {
                "thread_id", "turn_id", "item_id"}:
            return None
        fields = (value.get("thread_id"), value.get("turn_id"),
                  value.get("item_id"))
        return tuple(fields) if all(isinstance(item, str) and item
                                    for item in fields) else None

    @staticmethod
    def _decode_writer_bytes(value):
        if not isinstance(value, str):
            return None
        try:
            raw = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error):
            return None
        return raw if base64.b64encode(raw).decode("ascii") == value else None

    @staticmethod
    def _strict_json_value(text):
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON member: {key}")
                result[key] = value
            return result

        def reject_constant(value):
            raise ValueError(f"non-finite JSON number: {value}")

        try:
            value = json.loads(text, object_pairs_hook=unique_pairs,
                               parse_constant=reject_constant)
        except (ValueError, TypeError):
            return None
        return value

    @staticmethod
    def _json_semantically_equal(left, right):
        """Compare JSON values without Python's bool/int equality overlap."""
        if type(left) is not type(right):
            return False
        if isinstance(left, dict):
            return left.keys() == right.keys() and all(
                Judge._json_semantically_equal(left[key], right[key])
                for key in left)
        if isinstance(left, list):
            return len(left) == len(right) and all(
                Judge._json_semantically_equal(a, b)
                for a, b in zip(left, right))
        return left == right

    @staticmethod
    def _complete_writer_result(value):
        """Validate the complete structured result passed to the fixed writer."""
        if not isinstance(value, dict) or value.get("result") != "ok" \
                or not isinstance(value.get("files"), list) \
                or not value["files"] \
                or not isinstance(value.get("notes"), str):
            return False

        candidates = set()
        for entry in value["files"]:
            if not isinstance(entry, dict):
                return False
            file_path = entry.get("file")
            if not isinstance(file_path, str) or not file_path:
                return False
            candidate = Path(file_path)
            if not candidate.is_absolute():
                return False
            try:
                normalized_path = str(candidate.resolve(strict=False))
            except (OSError, RuntimeError, ValueError):
                return False

            artifact = entry.get("artifact")
            verdict = entry.get("verdict")
            blocking = entry.get("blocking")
            minor = entry.get("minor")
            issues = entry.get("issues")
            if artifact not in ("analysis", "candidates") \
                    or verdict not in ("pass", "pass_with_minor", "fail") \
                    or isinstance(blocking, bool) or not isinstance(blocking, int) \
                    or blocking < 0 or isinstance(minor, bool) \
                    or not isinstance(minor, int) or minor < 0 \
                    or not isinstance(issues, list):
                return False

            blocking_issues = 0
            minor_issues = 0
            for issue in issues:
                if not isinstance(issue, dict):
                    return False
                if any(not isinstance(issue.get(field), str)
                       or not issue[field].strip()
                       for field in ("rule", "severity", "quote", "suggestion")):
                    return False
                location = issue.get("location")
                if isinstance(location, bool) or not (
                        isinstance(location, int) and location > 0
                        or isinstance(location, str) and location.strip()
                        and len(location) <= 20):
                    return False
                if len(issue["quote"]) > 40:
                    return False
                if issue["severity"] == "blocking":
                    blocking_issues += 1
                elif issue["severity"] == "minor":
                    minor_issues += 1
                else:
                    return False
            if (blocking, minor) != (blocking_issues, minor_issues):
                return False
            if blocking_issues and verdict != "fail":
                return False
            if not blocking_issues and verdict == "fail":
                return False
            if not blocking_issues and minor_issues and verdict != "pass_with_minor":
                return False
            if not blocking_issues and not minor_issues and verdict != "pass":
                return False
            if artifact == "candidates":
                if normalized_path in candidates:
                    return False
                candidates.add(normalized_path)
        return bool(candidates)

    @staticmethod
    def _argv_values(command, flag):
        try:
            tokens = shlex.split(command)
        except ValueError:
            return None
        values = []
        for index, token in enumerate(tokens):
            if token == flag:
                if index + 1 >= len(tokens) or tokens[index + 1].startswith("--"):
                    values.append(None)
                else:
                    values.append(tokens[index + 1])
            elif token.startswith(flag + "="):
                values.append(token[len(flag) + 1:])
        return values

    def _writer_argument_check(self, entry, record, script):
        problems, gaps = [], []
        if self.installed_script is None or script != \
                str(Path(self.installed_script).resolve()):
            problems.append(f"round {entry['round']}: fixed writer did not use the installed consumer entry")
        output_values = self._argv_values(record["command"], "--output-file")
        map_values = self._argv_values(record["command"], "--output-map-json")
        result_values = self._argv_values(record["command"], "--result-json")
        if output_values is None or map_values is None or result_values is None:
            gaps.append(f"round {entry['round']}: writer command argv cannot be parsed")
            return problems, gaps, None
        if len(output_values) != 1 or not output_values[0] \
                or len(map_values) != 0 or len(result_values) != 1 \
                or not result_values[0]:
            problems.append(f"round {entry['round']}: writer command arguments are incomplete, duplicated, or use the wrong output mode")
            return problems, gaps, None
        if output_values[0] != entry.get("output_file"):
            problems.append(f"round {entry['round']}: --output-file differs from prepare's output_file")
        result_value = self._strict_json_value(result_values[0])
        if not self._complete_writer_result(result_value):
            problems.append(f"round {entry['round']}: --result-json is not a complete result object")
            result_value = None
        return problems, gaps, result_value

    @staticmethod
    def _record_identity(record):
        values = (record.get("thread_id"), record.get("turn_id"),
                  record.get("item_id"))
        return tuple(values) if all(isinstance(item, str) and item
                                    for item in values) else None

    @staticmethod
    def _writer_call(record):
        calls, uncertain = stage3_entry_calls(record.get("command", ""),
                                               record.get("cwd"))
        if uncertain or len(calls) != 1:
            return None
        subcommand, script = calls[0]
        if subcommand != VALIDATOR_WRITE:
            return None
        return script

    def _writer_events_in_window(self, entry, start, finish):
        """Find raw writer command items, including incomplete lifecycle rows."""
        candidates = []
        for index in range(max(0, start + 1), min(finish, len(self.m.events))):
            event = self.m.events[index]
            message = event.get("message") or {}
            params = message.get("params") or {}
            item = params.get("item") or {}
            if params.get("threadId") != entry.get("child") \
                    or item.get("type") != "commandExecution":
                continue
            record = {"command": item.get("command") or "",
                      "cwd": item.get("cwd") or params.get("cwd")}
            if self._writer_call(record) is None:
                continue
            fields = (params.get("threadId"), params.get("turnId"),
                      item.get("id"))
            identity = tuple(fields) if all(
                isinstance(value, str) and value for value in fields) else None
            candidates.append((index, identity))
        return candidates

    def judge_writer_observations(self):
        """Bind independent writer observations to native events and handoff.

        ``writer-evidence`` has this compact shape::

            {"schema":"issue66.writer-observation.v1",
             "evidence_set_id":"...", "observations":[{
              "round":1,
              "writer_call":{"thread_id":"...","turn_id":"...",
                             "item_id":"..."},
              "command":"<complete native command input>",
              "stdout_b64":"<raw stdout bytes>",
              "output":{"path":"<prepared absolute path>",
                "exists_before":false,"exists_after":true,
                "mode":"0600","bytes_b64":"<file bytes>"},
              "save_input":{"thread_id":"...","turn_id":"...",
                "item_id":"...","path":"<source read by save>",
                "bytes_b64":"<bytes read before save>"}}]}

        For a failed writer call, ``output`` records the attempted prepared
        path, ``exists_after`` may be false, and ``mode``/``bytes_b64`` are
        null. ``save_input`` is null when save was correctly never reached.
        The call identities are App Server commandExecution thread/turn/item
        identities; text that merely mentions the command is not a call.
        """
        evidence = self.surfaces.get("writer")
        self.writer_calls_by_round = {}
        self.writer_actual_by_round = {}
        self.writer_untrusted_rounds = set()

        # Discover native writer calls before reading the independent surface.
        # That way, a missing observation leaves raw-production judging at GAP
        # when the native call exists, instead of turning an unobserved file
        # into a product failure.
        prepared = getattr(self, "prepared_rounds", [])
        native_problems, native_gaps = [], []
        all_exec_by_identity = {}
        writer_records_by_identity = {}
        for records in self.m.execs.values():
            for record in records:
                identity = self._record_identity(record)
                if identity is not None:
                    all_exec_by_identity.setdefault(identity, []).append(record)
        for entry in prepared:
            start, finish, window = self._validator_window(entry)
            if window is None:
                native_gaps.append(
                    f"round {entry['round']}: validator command window is incomplete")
                self.writer_untrusted_rounds.add(entry["round"])
                continue
            if any(index in self.m.invalid_sequence_indices
                   for index in range(start + 1, finish)):
                native_gaps.append(
                    f"round {entry['round']}: event sequence does not establish a reliable writer call order")
                self.writer_untrusted_rounds.add(entry["round"])
                continue
            execs, _changes = window
            completed_writer_ids = {
                self._record_identity(record) for record in execs
                if self._writer_call(record) is not None
                and self._record_identity(record) is not None}
            incomplete_writer_items = [identity for _index, identity in
                                       self._writer_events_in_window(
                                           entry, start, finish)
                                       if identity not in completed_writer_ids]
            if incomplete_writer_items:
                native_gaps.append(
                    f"round {entry['round']}: fixed-writer lifecycle is incomplete or mismatched")
                self.writer_untrusted_rounds.add(entry["round"])
            for record in execs:
                script = self._writer_call(record)
                if script is None:
                    if VALIDATOR_WRITE in record.get("command", ""):
                        native_gaps.append(
                            f"round {entry['round']}: fixed-writer invocation cannot be resolved")
                    continue
                self.writer_actual_by_round.setdefault(
                    entry["round"], []).append(record)
                identity = self._record_identity(record)
                if identity is None:
                    native_gaps.append(
                        f"round {entry['round']}: fixed-writer item identity is missing")
                    continue
                writer_records_by_identity.setdefault(identity, []).append(
                    (entry, record, script))

        for identity, matches in writer_records_by_identity.items():
            if len(matches) != 1:
                native_gaps.append(
                    f"native writer identity {identity} is not unique")
                continue
            entry, record, script = matches[0]
            arg_problems, arg_gaps, result_value = \
                self._writer_argument_check(entry, record, script)
            native_problems.extend(arg_problems)
            native_gaps.extend(arg_gaps)
            result = self._exec_result(record)
            if result is False:
                native_problems.append(
                    f"round {entry['round']}: fixed-writer command returned nonzero or failed")
            elif result is None:
                native_gaps.append(
                    f"round {entry['round']}: native writer completion result is not established")
            else:
                native_stdout = record.get("output")
                if not isinstance(native_stdout, str) or record.get("truncated"):
                    native_gaps.append(
                        f"round {entry['round']}: native writer stdout is missing or truncated")
                else:
                    stdout_value = self._strict_json_value(native_stdout)
                    if not self._complete_writer_result(stdout_value):
                        native_problems.append(
                            f"round {entry['round']}: successful stdout is not a complete result object")
                    elif isinstance(result_value, dict) \
                            and not self._json_semantically_equal(
                                stdout_value, result_value):
                        native_problems.append(
                            f"round {entry['round']}: --result-json semantics differ from writer stdout")

        for entry in prepared:
            actual_records = self.writer_actual_by_round.get(entry["round"], [])
            if len(actual_records) > 1:
                native_problems.append(
                    f"round {entry['round']}: validator invoked the fixed writer "
                    f"{len(actual_records)} times")
            if not actual_records:
                if entry["round"] in self.writer_untrusted_rounds:
                    continue
                if self.m.run_completed:
                    native_problems.append(
                        f"round {entry['round']}: validator completed without calling the fixed writer")
                else:
                    native_gaps.append(
                        f"round {entry['round']}: fixed-writer call is not fully observed")

        if not prepared:
            native_gaps.append("no prepared validator round is available")
        self.row("F-writer-command",
                 "fail" if native_problems else "gap" if native_gaps else "pass",
                 "native fixed-writer command, arguments, stdout and completion result",
                 native_problems + native_gaps)

        if evidence is None:
            self.row("F-writer-evidence", "gap",
                     "independent fixed-writer observation surface is missing",
                     [])
            return
        if not isinstance(evidence, dict):
            self.row("F-writer-evidence", "invalid",
                     "writer evidence is not a JSON object", [])
            return
        if evidence.get("schema") != WRITER_EVIDENCE_SCHEMA:
            self.row("F-writer-evidence", "invalid",
                     "writer evidence schema is missing or unsupported",
                     [str(evidence.get("schema"))])
            return
        observations = evidence.get("observations")
        if not isinstance(observations, list):
            self.row("F-writer-evidence", "invalid",
                     "writer observations are not an array",
                     [])
            return

        invalid, problems, gaps, observed = [], [], [], []
        normalized = []
        required_observation = {"round", "writer_call", "command",
                                "stdout_b64", "output", "save_input"}
        required_output = {"path", "exists_before", "exists_after",
                           "mode", "bytes_b64"}
        required_save = {"thread_id", "turn_id", "item_id", "path",
                         "bytes_b64"}
        for number, row in enumerate(observations, start=1):
            prefix = f"writer observation {number}"
            if not isinstance(row, dict) or set(row) != required_observation:
                invalid.append(f"{prefix}: unsupported fields or shape")
                continue
            round_no = row.get("round")
            identity = self._writer_identity(row.get("writer_call"))
            stdout_bytes = self._decode_writer_bytes(row.get("stdout_b64"))
            output = row.get("output")
            if type(round_no) is not int or round_no < 1 or identity is None \
                    or not isinstance(row.get("command"), str) \
                    or not row.get("command") or stdout_bytes is None \
                    or not isinstance(output, dict) \
                    or set(output) != required_output:
                invalid.append(f"{prefix}: required call, command, stdout, or output fields are malformed")
                continue
            output_bytes = self._decode_writer_bytes(output.get("bytes_b64"))
            output_path = output.get("path")
            before, after, mode = (output.get("exists_before"),
                                   output.get("exists_after"),
                                   output.get("mode"))
            valid_mode = mode is None or isinstance(mode, str) \
                and re.fullmatch(r"0[0-7]{3}", mode) is not None
            if not isinstance(output_path, str) \
                    or not Path(output_path).is_absolute() \
                    or type(before) is not bool or type(after) is not bool \
                    or not valid_mode \
                    or (after and (mode is None or output_bytes is None)) \
                    or (not after and (mode is not None
                                       or output.get("bytes_b64") is not None)):
                invalid.append(f"{prefix}: file existence, path, mode, or bytes are malformed")
                continue
            save_input = row.get("save_input")
            save_bytes = None
            save_identity = None
            save_path = None
            if save_input is not None:
                if not isinstance(save_input, dict) \
                        or set(save_input) != required_save:
                    invalid.append(f"{prefix}: save input observation is malformed")
                    continue
                save_identity = self._writer_identity({
                    "thread_id": save_input.get("thread_id"),
                    "turn_id": save_input.get("turn_id"),
                    "item_id": save_input.get("item_id")})
                save_path = save_input.get("path")
                save_bytes = self._decode_writer_bytes(
                    save_input.get("bytes_b64"))
                if save_identity is None or not isinstance(save_path, str) \
                        or not Path(save_path).is_absolute() \
                        or save_bytes is None:
                    invalid.append(f"{prefix}: save input identity, path, or bytes are malformed")
                    continue
            normalized.append({"round": round_no, "identity": identity,
                               "command": row["command"],
                               "stdout_bytes": stdout_bytes,
                               "output_path": output_path,
                               "exists_before": before,
                               "exists_after": after, "mode": mode,
                               "output_bytes": output_bytes,
                               "save_identity": save_identity,
                               "save_path": save_path,
                               "save_bytes": save_bytes})

        duplicate_ids = sorted({item["identity"] for item in normalized
                                if sum(other["identity"] == item["identity"]
                                       for other in normalized) > 1})
        if duplicate_ids:
            invalid.append(f"duplicate writer observations for {duplicate_ids}")

        seen_observation_ids = set()
        for row in normalized:
            prefix = f"round {row['round']} writer observation"
            if row["round"] in self.writer_untrusted_rounds:
                gaps.append(f"{prefix}: native ordering or call lifecycle is incomplete")
                continue
            identity = row["identity"]
            matches = writer_records_by_identity.get(identity, [])
            if len(matches) != 1:
                if identity in all_exec_by_identity and not matches:
                    gaps.append(f"{prefix}: native item does not execute the fixed writer")
                else:
                    invalid.append(f"{prefix}: thread/turn/item identity does not bind one native writer call")
                continue
            entry, record, script = matches[0]
            if identity in seen_observation_ids:
                continue
            seen_observation_ids.add(identity)
            if row["round"] != entry["round"] or record.get("thread_id") != entry["child"]:
                invalid.append(f"{prefix}: round or validator thread conflicts with the handoff chain")
                continue
            if row["command"] != record.get("command"):
                invalid.append(f"{prefix}: command text conflicts with its native item")
                continue
            if self._exec_result(record) is None:
                gaps.append(f"{prefix}: native command has no determinate completion result")
                continue
            native_stdout = record.get("output")
            if not isinstance(native_stdout, str) or record.get("truncated"):
                gaps.append(f"{prefix}: native command stdout is missing or truncated")
                continue
            if row["stdout_bytes"] != native_stdout.encode("utf-8"):
                invalid.append(f"{prefix}: stdout bytes conflict with the native completion")
                continue
            self.writer_calls_by_round[entry["round"]] = {
                "entry": entry, "record": record,
                "stdout_bytes": row["stdout_bytes"],
                "output_bytes": row["output_bytes"],
                "output_path": row["output_path"],
                "exists_before": row["exists_before"],
                "exists_after": row["exists_after"],
                "mode": row["mode"],
                "save_identity": row["save_identity"],
                "save_path": row["save_path"],
                "save_bytes": row["save_bytes"],
                "script": script,
            }

        for entry in prepared:
            round_no = entry["round"]
            actual_records = self.writer_actual_by_round.get(round_no, [])
            if not actual_records:
                continue
            identity = self._record_identity(actual_records[0])
            if identity not in seen_observation_ids:
                gaps.append(f"round {round_no}: independent file observation is missing or unbound")
                continue
            writer = self.writer_calls_by_round.get(round_no)
            if writer is None:
                continue
            record = writer["record"]
            result = self._exec_result(record)
            output_file = entry.get("output_file")
            output_values = self._argv_values(record["command"], "--output-file")
            if output_values and len(output_values) == 1 \
                    and output_values[0] is not None \
                    and writer["output_path"] != output_values[0]:
                invalid.append(f"round {round_no}: observed output path conflicts with the actual --output-file argument")
                continue
            if writer["output_path"] != output_file:
                problems.append(f"round {round_no}: observed file path differs from prepare's output_file")

            if result is True:
                if writer["exists_before"]:
                    problems.append(f"round {round_no}: assigned output existed before the fixed writer call")
                if not writer["exists_after"]:
                    problems.append(f"round {round_no}: fixed writer returned success without an output file")
                if writer["exists_after"] and writer["mode"] != "0600":
                    problems.append(f"round {round_no}: output mode is not 0600")
                if writer["exists_after"] and writer["output_bytes"] != writer["stdout_bytes"]:
                    problems.append(f"round {round_no}: output file bytes differ from writer stdout")
            messages = self.m.assistant_messages.get(entry["child"], [])
            if len(messages) != 1:
                if self.m.unsupported_shapes.get(entry["child"]):
                    gaps.append(
                        f"round {round_no}: final validator message shape is unsupported")
                elif self.m.run_completed:
                    problems.append(
                        f"round {round_no}: validator completed with "
                        f"{len(messages)} final business messages, expected one")
                else:
                    gaps.append(
                        f"round {round_no}: final validator message is not fully observed")
            else:
                message = messages[0]
                if message.get("turn_id") != record.get("turn_id"):
                    invalid.append(f"round {round_no}: final message turn does not bind to the writer call")
                elif message.get("index", -1) <= record.get("index", -1):
                    problems.append(f"round {round_no}: validator final message preceded fixed-writer completion")
                elif result is True and writer["stdout_bytes"] != message.get("bytes"):
                    problems.append(f"round {round_no}: final message bytes differ from fixed-writer stdout")

            if result is False:
                if writer["save_identity"] is not None:
                    problems.append(
                        f"round {round_no}: failed writer observation claims a save input")
                continue

            complete = next((item for item in getattr(self, "rounds", [])
                             if item.get("round") == round_no), None)
            if complete is None:
                if result is True:
                    gaps.append(f"round {round_no}: save input observation is not yet available")
                continue
            save = complete.get("save")
            save_identity = self._record_identity(save) if save else None
            if writer["save_identity"] is None:
                gaps.append(f"round {round_no}: raw save-input bytes are missing")
            elif save_identity != writer["save_identity"]:
                invalid.append(f"round {round_no}: save-input observation does not bind the native save command")
            else:
                if writer["save_path"] != output_file:
                    problems.append(f"round {round_no}: save consumed a path other than the prepared output_file")
                if writer["save_bytes"] != writer["output_bytes"]:
                    problems.append(f"round {round_no}: save input bytes differ from the writer output file")
                save_payload = complete.get("save_payload") or {}
                record_payload = complete.get("record_payload") or {}
                observed_sha = sha256_bytes(writer["save_bytes"])
                if save_payload.get("validation_sha256") != observed_sha:
                    problems.append(f"round {round_no}: save return digest differs from the observed save input bytes")
                if record_payload.get("validation_input_sha256") != observed_sha:
                    problems.append(f"round {round_no}: record input digest differs from the observed save input bytes")
            observed.append(f"round {round_no}: command item {identity[2]} → prepared path {output_file}")

        if invalid:
            self.row("F-writer-evidence", "invalid",
                     "writer observation is malformed or cannot be associated with the native run",
                     invalid + gaps + observed)
        elif problems:
            self.row("F-writer-evidence", "fail",
                     "a directly observed fixed-writer contract was violated",
                     problems + gaps + observed)
        elif gaps:
            self.row("F-writer-evidence", "gap",
                     "writer command or raw file observation is incomplete",
                     gaps + observed)
        else:
            self.row("F-writer-evidence", "pass",
                     "fixed-writer arguments, file observation, final message and save input are bound byte-for-byte",
                     observed)

    # -- fix 3: validator-produced original ---------------------------------

    def judge_raw_original(self):
        rounds = getattr(self, "prepared_rounds", []) or getattr(self, "rounds", [])
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
            if not messages and self._declined_business_operations(child):
                root_rewrite, root_gaps = self._root_source_rewrite(entry)
                if root_rewrite:
                    problems.append(f"round {entry['round']}: root writes validator source ({root_rewrite})")
                gapped = True
                rows.append(f"round {entry['round']}: production was explicitly declined before a business message")
                rows.extend(root_gaps)
                continue
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
            if save_sha is None or record_sha is None:
                gapped = True
                rows.append(f"round {entry['round']}: save/record byte digest is missing")
            elif msg_sha == save_sha == record_sha:
                rows.append(f"round {entry['round']}: {msg_sha} "
                            f"(message == save == record, producer verified)")
            else:
                problems.append(
                    f"round {entry['round']}: MISMATCH msg={msg_sha} "
                    f"save={save_sha} record={record_sha}")
            # the root must not touch the source outside the save entry
            root_rewrite, root_gaps = self._root_source_rewrite(entry)
            if root_rewrite:
                problems.append(
                    f"round {entry['round']}: root window writes the "
                    f"validator source outside the save entry "
                    f"({root_rewrite})")
            if root_gaps:
                gapped = True
                rows.append(f"round {entry['round']}: root file operations "
                            f"are not fully observable ({root_gaps})")
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
    def _literal_written_bytes(command, expected_path, cwd):
        try:
            tokens = shlex.split(command)
            source = tokens[tokens.index("-c") + 1]
            tree = ast.parse(source)
        except (ValueError, IndexError, SyntaxError):
            return None
        expected = Path(expected_path)
        if not expected.is_absolute():
            expected = (Path(cwd or ".") / expected).resolve()
        control_flow = (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
            ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While,
            ast.Try, ast.TryStar, ast.With, ast.AsyncWith, ast.Match,
            ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
            ast.BoolOp, ast.comprehension,
        )
        parents = {child: parent for parent in ast.walk(tree)
                   for child in ast.iter_child_nodes(parent)}

        def conditional_or_deferred(node):
            parent = parents.get(node)
            while parent is not None:
                if isinstance(parent, control_flow):
                    return True
                parent = parents.get(parent)
            return False

        writes = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) \
                    or node.func.attr != "write" or not node.args:
                continue
            if conditional_or_deferred(node):
                return None
            receiver = node.func.value
            if not isinstance(receiver, ast.Call) \
                    or not isinstance(receiver.func, ast.Name) \
                    or receiver.func.id != "open":
                continue
            path_node = (receiver.args[0] if receiver.args else next(
                (kw.value for kw in receiver.keywords if kw.arg == "file"), None))
            if not isinstance(path_node, ast.Constant) \
                    or not isinstance(path_node.value, str):
                return None
            actual = Path(path_node.value)
            if not actual.is_absolute():
                actual = (Path(cwd or ".") / actual).resolve()
            if actual != expected:
                continue
            value = node.args[0]
            if isinstance(value, ast.Name):
                assignments = [assignment for assignment in tree.body
                               if isinstance(assignment, ast.Assign)
                               and assignment.lineno < node.lineno
                               and any(isinstance(target, ast.Name)
                                       and target.id == value.id
                                       for target in assignment.targets)]
                if assignments:
                    value = assignments[-1].value
            if isinstance(value, ast.Constant) \
                    and isinstance(value.value, (bytes, str)):
                writes.append(value.value if isinstance(value.value, bytes)
                              else value.value.encode("utf-8"))
            else:
                return None
        return writes[0] if len(writes) == 1 else None

    @staticmethod
    def _filechange_added_bytes(change):
        """Return bytes from the app-server's complete Add payload.

        The current fileChange protocol projects ``FileChange::Add.content``
        unchanged into ``changes[].diff``. The patch tool writes that Rust
        string as UTF-8 bytes without newline normalization. For Update,
        ``diff`` is a unified patch and cannot establish resulting file bytes.
        """
        if change.get("operation") != "add":
            return None
        diff = change.get("diff")
        if not isinstance(diff, str):
            return None
        try:
            return diff.encode("utf-8")
        except UnicodeEncodeError:
            return None

    def _production_evidence(self, entry, message):
        """True/False/None: bind native writer, file observation and message."""
        if entry.get("round") in getattr(self, "writer_untrusted_rounds", set()):
            return None
        writer = getattr(self, "writer_calls_by_round", {}).get(
            entry.get("round"))
        if writer is None:
            if not getattr(self, "writer_actual_by_round", {}).get(
                    entry.get("round")) and self.m.run_completed:
                return False
            return None
        record = writer["record"]
        if self._exec_result(record) is not True:
            return None
        if record.get("thread_id") != entry.get("child") \
                or not record.get("turn_id") \
                or message.get("turn_id") != record.get("turn_id"):
            return None
        if record.get("index") is None or message.get("index", -1) <= record["index"]:
            return False
        raw = writer.get("output_bytes")
        if raw is None:
            return None
        if raw != writer.get("stdout_bytes") or raw != message.get("bytes"):
            return False
        return True

    def _root_source_rewrite(self, entry):
        """Actual root command/fileChange operations touching validator bytes."""
        output_file = entry.get("output_file") or ""
        validation_file = entry.get("validation_file") or ""
        record_cutoff = (entry.get("record") or {}).get("index")
        if record_cutoff is None:
            record_cutoff = len(self.m.events)
        hits, gaps = [], []
        for record in self.m.execs.get(self.m.root_id, []):
            if record.get("index") is None or record.get("call_index") is None \
                    or record["call_index"] >= record_cutoff:
                continue
            operations, unknown = command_file_behavior(
                record.get("command", ""), record.get("cwd"),
                ignored_stage3_subcommands={ROOT_SAVE, ROOT_RECORD,
                                           ROOT_PREPARE}, expected_stage3_script=self.installed_script)
            if unknown:
                gaps.append(f"event {record['index']}: command includes "
                            "unresolved file behavior")
            for kind, path, _exclusive in operations:
                if kind != "write":
                    continue
                if output_file and Path(path) == Path(output_file):
                    hits.append(f"event {record['index']}: {path}")
                if validation_file \
                        and Path(path) == Path(validation_file):
                    hits.append(f"event {record['index']}: {path}")
        for incomplete in self.m.incomplete_execs:
            if incomplete.get("thread_id") == self.m.root_id \
                    and incomplete.get("index", -1) < record_cutoff:
                gaps.append(f"event {incomplete.get('index')}: incomplete "
                            "root command before record completion")
        for change in self.m.file_changes.get(self.m.root_id, []):
            if change["index"] >= record_cutoff:
                continue
            for path in (change.get("path"), change.get("move_path")):
                if path and (Path(path) == Path(output_file)
                             or Path(path) == Path(validation_file)):
                    hits.append(f"event {change['index']}: {path}")
        for change in self.m.incomplete_file_changes:
            if change.get("thread_id") == self.m.root_id \
                    and change.get("index", -1) < record_cutoff:
                gaps.append(f"event {change.get('index')}: incomplete root "
                            "fileChange before record completion")
        return hits, gaps

    # -- fix 4: real file-operation write scope ------------------------------

    def judge_write_scope(self):
        rounds = getattr(self, "prepared_rounds", []) or getattr(self, "rounds", [])
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
            writer = getattr(self, "writer_calls_by_round", {}).get(
                entry.get("round"))
            start, finish, window = self._validator_window(entry)
            if window is None:
                gaps.append(f"round {entry['round']}: no correlated validator "
                            "completion window")
                continue
            execs, changes = window
            if any(index in self.m.invalid_sequence_indices
                   for index in range(start + 1, finish)):
                gaps.append(f"round {entry['round']}: app_server_events seq "
                            "does not establish a reliable call order")
            for incomplete in self.m.incomplete_execs:
                if incomplete.get("thread_id") == child \
                        and start < incomplete.get("index", -1) < finish:
                    gaps.append(
                        f"round {entry['round']}: commandExecution item/call_id "
                        "does not bind a started call to its completion")
            for incomplete in self.m.incomplete_file_changes:
                if incomplete.get("thread_id") == child \
                        and start < incomplete.get("index", -1) < finish:
                    gaps.append(
                        f"round {entry['round']}: fileChange item id/status "
                        "does not bind a successful start to its completion")
            operation_count = 0
            turn_id = None
            for record in execs:
                if self._writer_call(record) is not None:
                    turn_id = turn_id or record.get("turn_id")
                    if writer is None or self._record_identity(record) != \
                            self._record_identity(writer.get("record")):
                        gaps.append(f"round {entry['round']}: fixed-writer file observation is not bound")
                        continue
                    operation_count += 1
                    observed.append(
                        f"round {entry['round']} event {record['index']}: "
                        f"fixed writer observed {writer['output_path']} mode="
                        f"{writer['mode']}")
                    if Path(writer["output_path"]) != Path(output_file):
                        problems.append(
                            f"round {entry['round']}: fixed writer target "
                            "differs from its prepared output")
                    operations, unknown = command_file_behavior(
                        record.get("command", ""), record.get("cwd"),
                        ignored_stage3_subcommands={VALIDATOR_WRITE},
                        expected_stage3_script=self.installed_script)
                    if unknown:
                        gaps.append(f"round {entry['round']} event "
                                    f"{record['call_index']}: compound writer "
                                    "command has unresolved neighboring behavior")
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
                    continue
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
                path = change["path"]
                operation = change.get("operation")
                if operation not in {"add", "delete", "update"}:
                    gaps.append(f"round {entry['round']}: unsupported fileChange kind")
                    continue
                duplicate_writer_add = writer is not None \
                    and Path(path) == Path(output_file) and operation == "add"
                if not duplicate_writer_add:
                    operation_count += 1
                paths = [(path, change.get("exclusive"))]
                if change.get("move_path"):
                    paths.append((change["move_path"], False))
                for changed_path, exclusive in paths:
                    if duplicate_writer_add \
                            and Path(changed_path) == Path(output_file):
                        # The independent writer observation proves existence,
                        # mode and bytes; fileChange is only a duplicate view.
                        continue
                    observed.append(
                        f"round {entry['round']} event {change['index']}: "
                        f"fileChange {operation} {changed_path}")
                    if Path(changed_path) != Path(output_file):
                        problems.append(
                            f"round {entry['round']} event {change['index']}: "
                            f"fileChange on {changed_path} — outside assigned output file")
                    elif exclusive is None:
                        gaps.append(
                            f"round {entry['round']} event {change['index']}: "
                            "App Server fileChange Add does not prove exclusive "
                            "creation because it omits the pre-write target state")
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
                     problems + gaps + observed)
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
        reports = []
        child_roles = {child: spawn["agent_type"]
                       for spawn, child in m.ordered_children() if child}
        failed_operations = []
        for thread, records_for_thread in m.execs.items():
            role = child_roles.get(thread)
            for record in records_for_thread:
                subcommand = stage3_command(record.get("command", ""))
                operations, _unknown = command_file_behavior(
                    record.get("command", ""), record.get("cwd"))
                has_write = any(kind == "write" for kind, _path, _exclusive
                                in operations)
                tracked = (subcommand is not None
                           or role == GENERATOR_AGENT
                           or role == VALIDATOR_AGENT and has_write)
                if not tracked:
                    continue
                result = self._exec_result(record)
                failed_return = False
                if subcommand is not None and result is True:
                    payload, state = self._json_from_output(record.get("output"))
                    failed_return = state == "ok" and isinstance(payload, dict) \
                        and payload.get("status") not in (None, "ok")
                declined = record.get("status") == "declined"
                if declined:
                    decline = {
                        "index": record.get("index"),
                        "thread_id": thread,
                        "command": record.get("command")}
                    if not any(item.get("index") == decline["index"]
                               and item.get("thread_id") == thread
                               for item in self.external_declines):
                        self.external_declines.append(decline)
                if result is False or failed_return or declined:
                    failed_operations.append((record.get("index"),
                                              record.get("call_index"),
                                              thread, role, subcommand,
                                              has_write or (role == VALIDATOR_AGENT
                                                            and subcommand == VALIDATOR_WRITE),
                                              declined,
                                              record.get("turn_id")))
                elif result is None and subcommand is not None \
                        and record.get("index") is None:
                    gaps.append(f"event {record.get('call_index')}: {subcommand} "
                                "has no completed result for stop-order checking")
        for spawn in m.spawns:
            output = m.spawn_outputs.get(spawn.get("call_id"))
            if self._spawn_output_is_failure(output):
                failed_operations.append((output["index"], spawn["index"],
                                          m.root_id, None, "spawn_agent", False,
                                          False, None))

        for finish, start, thread, role, operation, failed_write, declined, turn_id \
                in failed_operations:
            if finish is None:
                continue
            dependents = []
            for spawn in m.spawns:
                if spawn["index"] > finish:
                    dependents.append(f"spawn event {spawn['index']}")
            for owner, records_for_thread in m.execs.items():
                for record in records_for_thread:
                    if record.get("call_index", -1) <= finish:
                        continue
                    if stage3_command(record.get("command", "")) is not None:
                        dependents.append(
                            f"event {record['call_index']}: "
                            f"{stage3_command(record['command'])}")
                    elif owner == thread and (role == GENERATOR_AGENT
                                              or role == VALIDATOR_AGENT
                                              and failed_write):
                        dependents.append(f"event {record['call_index']}: child command")
            if not declined and role in {GENERATOR_AGENT, VALIDATOR_AGENT}:
                messages = m.assistant_messages.get(thread, [])
                for message in messages:
                    if message["index"] > finish:
                        # A tool failure is a command result, not an assistant
                        # business message. The generator or validator may
                        # report that failure once to its caller; that report
                        # is not a dependent business action. Keep the failed
                        # command in the product verdict.
                        if role == VALIDATOR_AGENT \
                                and operation == VALIDATOR_WRITE \
                                and len(messages) == 1 \
                                and messages[0].get("turn_id") == turn_id \
                                and self._is_writer_error_message(messages[0]):
                            reports.append(
                                f"event {finish}: {operation} failed; event "
                                f"{messages[0]['index']}: unique structured "
                                f"error report on {thread}, turn {turn_id}")
                            continue
                        if role == GENERATOR_AGENT \
                                and operation in {CHILD_PLAN, CHILD_FINALIZE} \
                                and len(messages) == 1 \
                                and message.get("turn_id") == turn_id:
                            try:
                                report = json.loads(message["bytes"])
                            except (ValueError, UnicodeDecodeError):
                                report = None
                            if isinstance(report, dict) \
                                    and report.get("result") == "error" \
                                    and "program_root" in report \
                                    and (report["program_root"] is None
                                         or isinstance(report["program_root"], str)) \
                                    and report.get("directions") == [] \
                                    and isinstance(report.get("notes"), str) \
                                    and report["notes"].strip():
                                reports.append(
                                    f"event {finish}: {operation} failed; "
                                    f"event {message['index']}: unique error "
                                    f"report on {thread}, turn {turn_id}")
                                continue
                        dependents.append(f"event {message['index']}: child message")
            if dependents:
                problems.append(
                    f"event {finish}: {operation} failed but dependent business "
                    f"actions followed: {dependents}")

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
                     [f"last record event {last_record}"] + reports)

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
        groups = validator.get("groups") or {}
        if not isinstance(results, dict) or not isinstance(groups, dict):
            self.row("F-terminal-state", "gap", "terminal result collections have an unsupported shape", [])
            return
        results = {**results, **{f"group:{key}": value for key, value in groups.items()}}
        if not results:
            self.row("F-terminal-state", "fail",
                     "validator record carries no per-direction results",
                     [])
            return
        problems = []
        terminal = next((entry for entry in reversed(getattr(self, "rounds", []))
                         if entry["record_payload"].get("terminal") is True), None)
        scopes = terminal["record_payload"].get("scopes") if terminal else None
        if not isinstance(scopes, list) or not scopes:
            self.row("F-terminal-state", "gap", "terminal record scopes are missing", [])
            return
        for scope in scopes:
            if not isinstance(scope, dict) or not isinstance(scope.get("scope"), str):
                self.row("F-terminal-state", "gap", "terminal scope shape is unsupported", [])
                return
            kind, separator, ident = scope["scope"].partition(":")
            if not separator or kind not in {"direction", "group"}:
                self.row("F-terminal-state", "gap", "terminal scope identity is unsupported", [scope["scope"]])
                return
            collection = validator.get("results" if kind == "direction" else "groups")
            actual = collection.get(ident) if isinstance(collection, dict) else None
            if not isinstance(actual, dict) or any(actual.get(field) != scope.get(field)
                                                  for field in ("result", "rounds")):
                problems.append(f"{scope['scope']}: committed terminal differs from record return")
        for direction, entry in results.items():
            if not isinstance(entry, dict):
                self.row("F-terminal-state", "gap", "terminal result entry has an unsupported shape", [direction])
                return
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
                              for r in rebuilds], independent=True)
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
                         [f"root rebuild start event {r.get('call_index')}"
                          for r in rebuilds], independent=True)
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
                     problems + gaps, independent=True)
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
        self.judge_entry_binding()
        self.judge_credential_chain()
        self.judge_handoff_chain()
        self.judge_writer_observations()
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
        independent_failures = [row for row in failures
                                if row.get("independent") is True]
        machine_prefix = [row for row in self.rows
                          if row["verdict"] == "machine_failure_prefix"]
        external_blockers = bool(machine_prefix or self.external_declines)

        provenance_invalid = [row for row in invalid_rows if row["fact"] not in
                              {"F-attribution", "F-routing-verifier"}]
        if provenance_invalid:
            classification = "INVALID_TEST_EXECUTION"
            reason = "evidence or product/input provenance is invalid; business facts cannot be attributed"
        elif independent_failures:
            classification = "FAIL"
            reason = ("independent product violation: " + "; ".join(
                row["fact"] for row in independent_failures))
            if self.attribution_invalid or invalid_rows:
                reason += "; additional attribution or evidence invalidity retained"
        elif self.attribution_invalid or invalid_rows:
            classification = "INVALID_TEST_EXECUTION"
            reason = ("formal attribution conflicts or invalid evidence — "
                      "product failures cannot be derived")
        elif failures:
            classification = "FAIL"
            reason = "; ".join(row["fact"] for row in failures)
        elif external_blockers:
            classification = "BLOCKED"
            blocker_details = []
            if machine_prefix:
                blocker_details.append("machine-level spawn failure")
            blocker_details.extend(
                f"tool declined at event {decline['index']} on "
                f"{decline['thread_id']}"
                for decline in self.external_declines)
            reason = "; ".join(blocker_details) + "; dependent actions checked"
        elif self.attribution_incomplete:
            classification = "INVALID_TEST_EXECUTION"
            reason = ("root run incomplete — product failures cannot be derived "
                      "from absent child evidence")
        elif gaps or gap_rows:
            classification = "INVALID_TEST_EXECUTION"
            reason = "evidence missing, gapped or of an unsupported shape"
        elif self.rows and all(row["verdict"] == "pass"
                               for row in self.rows):
            classification = "PASS"
            reason = "all required runtime facts hold"
        else:
            classification = "INVALID_TEST_EXECUTION"
            reason = "unjudgeable evidence set"
        evidence_gaps = list(gaps)
        evidence_gaps.extend(
            f"{row['fact']}: {row['detail']} — {row['evidence']}"
            for row in invalid_rows + gap_rows)
        branch_statuses = []
        rounds = getattr(self, "rounds", [])
        generator_spawns = [spawn for spawn in self.m.spawns
                            if spawn["agent_type"] == GENERATOR_AGENT]
        if classification == "PASS" and self.m.run_completed \
                and len(rounds) == 1 and len(generator_spawns) == 1 \
                and (rounds[0]["record_payload"] or {}).get(
                    "needs_correction") is False:
            branch_statuses.append({
                "branch": "correction_round",
                "classification": "NOT TESTED",
                "reason": "round 1 completed without requesting correction"})
        return {
            "schema": "issue66-runtime-judge-v2",
            "classification": classification,
            "reason": reason,
            "evidence_gaps": evidence_gaps,
            "branch_statuses": branch_statuses,
            "facts": self.rows,
        }


def _load_json(path: str | None):
    if path is None:
        return None, None
    p = Path(path)
    if not p.exists():
        return None, f"{path}: file is missing"
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return None, f"{path}: {type(exc).__name__}: {exc}"


def _invalid_input_verdict(issues):
    details = list(issues)
    return {
        "schema": "issue66-runtime-judge-v2",
        "classification": "INVALID_TEST_EXECUTION",
        "reason": "required evidence input could not be read as the selected JSON record",
        "evidence_gaps": details,
        "branch_statuses": [],
        "facts": [
            {"fact": "F-test-program", "verdict": "invalid",
             "detail": "the selected evidence reader could not provide a complete input",
             "evidence": details},
            {"fact": "F-evidence-input", "verdict": "invalid",
             "detail": "one or more selected JSON evidence files are missing or unreadable",
             "evidence": details},
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-response", required=True)
    parser.add_argument("--adapter-output", required=True)
    parser.add_argument("--candidate-state", default=None)
    parser.add_argument("--program-root", default=None)
    parser.add_argument("--install-evidence", default=None)
    parser.add_argument("--fixture-evidence", default=None)
    parser.add_argument("--routing-evidence", default=None)
    parser.add_argument("--writer-evidence", default=None)
    parser.add_argument("--pre-snapshot", default=None)
    parser.add_argument("--post-snapshot", default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    load_issues = []
    response, issue = _load_json(args.eval_response)
    if issue:
        load_issues.append(f"eval-response: {issue}")
    adapter, issue = _load_json(args.adapter_output)
    if issue:
        load_issues.append(f"adapter-output: {issue}")
    candidate_state, issue = _load_json(args.candidate_state)
    if issue and "file is missing" not in issue:
        load_issues.append(f"candidate-state: {issue}")
    surface_paths = {
        "install": args.install_evidence,
        "fixture": args.fixture_evidence,
        "routing": args.routing_evidence,
        "writer": args.writer_evidence,
        "pre": args.pre_snapshot,
        "post": args.post_snapshot,
    }
    surfaces = {}
    for name, path in surface_paths.items():
        value, issue = _load_json(path)
        surfaces[name] = value
        if issue:
            load_issues.append(f"{name}: {issue}")
    if load_issues:
        verdict = _invalid_input_verdict(load_issues)
        Path(args.output).write_text(
            json.dumps(verdict, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
        print(verdict["classification"])
        return 2

    program_root = Path(args.program_root) if args.program_root else None
    model = RunModel(response, adapter)
    verdict = Judge(model, candidate_state, program_root, surfaces).run()
    Path(args.output).write_text(
        json.dumps(verdict, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(verdict["classification"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
