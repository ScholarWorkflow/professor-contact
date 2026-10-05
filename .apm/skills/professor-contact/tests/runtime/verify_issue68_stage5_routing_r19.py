#!/usr/bin/env python3
"""Gate-2 r21 PC68-R1 verifier: owner-local consumption and the root partition.

r13 keeps the root final business message selector unchanged: exactly one
current-root, current-turn ``rawResponseItem/completed`` assistant
``final_answer``. r19 rewrites the owner business-input oracle around the r19
fixture: the root discovers the local packs, runs the deterministic
``stage5-partition-choices`` entry exactly once and hands every formal child a
one-professor packet (``email_pack`` plus that owner's own ``choices`` rows,
never a ``choices_scope``).

r21 rewrites the wait/consume semantics around the real root result-receipt
surface: the root's result-consumption point per formal child is proven only
by a root-thread ``rawResponseItem/completed`` ``agent_message`` FINAL_ANSWER
receipt whose payload JSON names that owner's ``professor_dir`` and whose
professor_dir/status/reason_code outcome equals the outcome the child itself
returned on its own thread; the receipt's ``runtime_seq`` is the consumption
point. The official Codex V2 wait item (openai/codex
``multi_agents_v2/wait.rs``) always carries empty ``receiverThreadIds``/
``agentsStates`` and a ``WaitAgentResult.message`` that is only the "Wait
completed." status text, so wait pairing fields are never consumption
evidence. A child's ``turn/completed`` and the root's ``subAgentActivity``
report are diagnostics only and their absence never blocks; a missing receipt
stays ``root_result_consumption_unobservable`` and is never cured into a PASS
by the completion surfaces.

The oracle also freezes the partition ordering fact: the root's successful
``stage5-partition-choices`` call must complete before any owner business
call starts on a child thread; an owner business command that starts before
the partition completed is a product failure
(``owner_business_precedes_partition``). EVAL_PORT resolution is the formal
entry's responsibility and takes the port only from ``direnv exec``.

A child's consumption surface is only its own command texts that reference the
producer CLI (``contact_state.py``) together with a supported stage5 action
word; objects recorded by other commands (echo/log/diagnostic examples) are
never consumption evidence. Real Codex hosts hand the child a compound
``python3 -c``/wrapper expression whose packet rides inside as a JSON or
Python literal and whose stage5 arguments are a quoted argv list, so the
consumption surface is recognized by that loose text shape and never requires
the command to parse into standalone flags. Each consumed object must equal
the manifest's per-owner expected bundle rows after parsing, must not carry
any sibling marker or a ``choices_scope`` field, and must keep
``professor_dir``/``email_id`` byte for byte. The root orchestration oracle
proves exactly one successful root partition consistent with the manifest,
owner plans bound to their own pack and bundle file without a choices scope,
and at most one rebuild after both owner results were consumed; root
orchestration calls are recognized either by strict flag parsing or, for
compound preparations, by their single action word plus their
``aggregatedOutput``. A proven product failure is never downgraded to a
blocked or invalid terminal by another child's missing or ambiguous evidence.
"""
import argparse
import json
import shlex
from pathlib import Path

import verify_issue68_stage5_routing as base
import verify_issue68_stage5_routing_r13 as final_source
import verify_issue68_stage5_routing_r18 as command_surface


AGENT = base.AGENT
verdict = base.verdict
combine = base.combine
owner_outcome = base.owner_outcome
codex_final_result_source = final_source.codex_final_result_source

ACTIONS = {"stage5-list-inputs", "stage5-partition-choices", "stage5-plan",
           "stage5-rebuild-overview"}


def command_action(command, manifest):
    """Only a structured executed shell item can supply a stage5 CLI invocation.

    Same structural gate as the base parser. r19 adds
    ``stage5-partition-choices`` to the supported actions, lets ``--owner``
    repeat on the partition call (values accumulate into a list) and pins
    ``--program-root`` to the manifest program root.
    """
    tokens = shlex.split(command)
    if len(tokens) == 3 and Path(tokens[0]).name in ("sh", "bash", "zsh") and tokens[1] in ("-c", "-lc"):
        tokens = shlex.split(tokens[2])
    found = [token for token in tokens if token in ACTIONS]
    if not found:
        return None
    # Compound shell/code expressions are outside this parser's frozen
    # command grammar. Missing observation is never inferred as no call.
    if len(found) != 1 or any(token in (";", "&&", "||", "|") for token in tokens):
        raise ValueError("compound_or_multiple_stage5_commands")
    action = found[0]
    index = tokens.index(action)
    if index == 0 or Path(tokens[index - 1]).name != "contact_state.py":
        raise ValueError("stage5_invocation_script_unobservable")
    tail = tokens[index + 1:]
    if "--help" in tail or "-h" in tail:
        return None
    if len(tail) % 2:
        raise ValueError("stage5_invocation_arguments_unobservable")
    flags = {}
    for offset in range(0, len(tail), 2):
        flag, value = tail[offset], tail[offset + 1]
        if not flag.startswith("--"):
            raise ValueError("stage5_invocation_arguments_unobservable")
        if flag == "--owner":
            flags.setdefault(flag, []).append(value)
            continue
        if flag in flags:
            raise ValueError("stage5_invocation_arguments_unobservable")
        flags[flag] = value
    if flags.get("--program-root") != manifest["program_root"]:
        return {"action": action, "problem": "wrong_program_root"}
    return {"action": action, "flags": flags}


def is_business_surface(text):
    """Loose business-surface recognition over one command text.

    A command text is a consumption or orchestration candidate when it
    references the producer CLI (``contact_state.py``) and any supported
    stage5 action word. Real Codex hosts wrap both inside ``python3 -c`` and
    wrapper compound expressions — the action word then lives inside a quoted
    string, never a standalone token — so this check only decides whether a
    text is worth extracting business objects or output facts from; it never
    parses flags. Strict ``command_action`` parsing stays the only source for
    flag facts.
    """
    if not isinstance(text, str):
        return False
    return "contact_state.py" in text and any(action in text for action in ACTIONS)


def consumed_business_objects(stage5_command_texts, payload_texts):
    """The one business object this owner consumed, from its stage5 commands.

    Only command texts on the loose business surface (producer CLI plus a
    supported stage5 action word, however compound the expression) are the
    consumption surface; a business object recorded by any other command
    (echo/log or a diagnostic example) is never consumption evidence. The
    plaintext child user message stays the delivery fallback for hosts that
    hand the business object to the child itself; it keeps the frozen
    ``completed_user_payload_unobservable`` blocker when it is absent or not
    unique and no stage5 command surface exists.
    """
    consumed = command_surface._unique([row for text in stage5_command_texts
                                        for row in command_surface.business_objects(text)])
    if len(consumed) > 1:
        return [], verdict("INVALID_EVIDENCE", "owner_business_object_ambiguous",
                           observed_candidates=len(consumed))
    if consumed:
        return consumed, None
    if stage5_command_texts:
        return [], verdict("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable")
    delivered = [text for text in payload_texts
                 if any("email_pack" in row for value in base.json_values(text) for row in base.objects(value))]
    if len(delivered) == 1:
        return command_surface._unique([row for text in delivered
                                        for row in command_surface.business_objects(text)]), None
    return [], verdict("BLOCKED_OBSERVABILITY", "completed_user_payload_unobservable")


def _choices_summary(observed, expected):
    """Compact machine-readable summary of how consumed choices deviate."""
    summary = {"observed_rows": len(observed) if isinstance(observed, list) else None,
               "expected_rows": len(expected) if isinstance(expected, list) else None}
    if isinstance(observed, list) and isinstance(expected, list):
        summary["changed_row_indexes"] = [index for index in range(max(len(observed), len(expected)))
                                          if index >= len(observed) or index >= len(expected)
                                          or observed[index] != expected[index]]
    else:
        summary["observed_type"] = type(observed).__name__
    return summary


def owner_payload(rows, manifest):
    """The r19 owner-local packet conditions for one formal child.

    Source completeness and attribution first, then the frozen isolation
    conditions: no ``choices_scope`` field, exact owner-local ``choices``
    rows, no sibling marker anywhere in the serialized object, and an
    ``email_id`` belonging to this owner when the object carries one.
    """
    if len(rows) > 1:
        return None, verdict("INVALID_EVIDENCE", "owner_business_object_ambiguous",
                             observed_candidates=len(rows))
    if not rows:
        return None, verdict("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable")
    row = rows[0]
    pack = row["email_pack"]
    owner = next((candidate for candidate in manifest["owners"] if candidate["email_pack"] == pack), None)
    if owner is None:
        return None, verdict("FAIL_PRODUCT", "unexpected_owner_pack", observed_pack=pack)
    if "choices_scope" in row:
        return None, verdict("FAIL_PRODUCT", "owner_input_carries_choices_scope", observed_pack=pack)
    if "choices" not in row:
        return None, verdict("FAIL_PRODUCT", "choices_transport_missing", observed_pack=pack)
    if row["choices"] != owner["expected_choices_rows"]:
        return None, verdict("FAIL_PRODUCT", "owner_bundle_choices_changed", observed_pack=pack,
                             choices_summary=_choices_summary(row["choices"], owner["expected_choices_rows"]))
    text = json.dumps(row, ensure_ascii=False)
    markers = [marker for marker in owner["sibling_exclusions"] if marker in text]
    if markers:
        return None, verdict("FAIL_PRODUCT", "owner_input_contains_sibling_data", observed_pack=pack,
                             observed_markers=markers)
    if "email_id" in row and row["email_id"] not in owner["email_ids"]:
        return None, verdict("FAIL_PRODUCT", "owner_target_mismatch", observed_pack=pack,
                             observed_email_id=row["email_id"])
    return pack, None


def final_result_rows(texts):
    """The pinned final business result source, single wrapper layer aware.

    For every top-level JSON value of the pinned root text: a list contributes
    its dicts, a result row (``status`` plus ``reason_code``) contributes
    itself, and a dict with exactly one key contributes only the dicts of that
    one list value. Recursion never goes deeper, so historical references and
    nested diagnostics are never terminal results; top-level values are never
    merged or deduplicated against each other.
    """
    rows = []
    for text in texts:
        for value in base.json_values(text):
            if isinstance(value, list):
                rows.extend(row for row in value if isinstance(row, dict))
            elif isinstance(value, dict) and "status" in value and "reason_code" in value:
                rows.append(value)
            elif isinstance(value, dict) and len(value) == 1:
                nested = next(iter(value.values()))
                if isinstance(nested, list):
                    rows.extend(row for row in nested if isinstance(row, dict))
    return rows


def receipt_outcomes(text, professor_dir):
    """The distinct outcome triples one root receipt carries for one owner.

    A receipt matches the owner when its payload JSON — extracted with the
    shared ``json_values``/``objects`` decoders — contains a row whose
    ``professor_dir`` equals the owner's directory; each matching row
    contributes its professor_dir/status/reason_code triple.
    """
    outcomes = []
    for value in base.json_values(text):
        for row in base.objects(value):
            if row.get("professor_dir") == professor_dir:
                outcome = {key: row.get(key) for key in ("professor_dir", "status", "reason_code")}
                if outcome not in outcomes:
                    outcomes.append(outcome)
    return outcomes


def _plan_checks(parsed, manifest, expected_pack):
    flags = parsed["flags"]
    if expected_pack is not None and flags.get("--email-pack") != expected_pack:
        return verdict("FAIL_PRODUCT", "owner_plan_directory_changed", observed_call=parsed["command"])
    if "--choices-scope" in flags:
        return verdict("FAIL_PRODUCT", "owner_plan_carries_choices_scope")
    if expected_pack is None or "--choices" not in flags:
        return None
    owner = next(candidate for candidate in manifest["owners"] if candidate["email_pack"] == expected_pack)
    try:
        transported = json.loads(Path(flags["--choices"]).read_text())
    except (OSError, ValueError):
        return verdict("BLOCKED_OBSERVABILITY", "transport_file_unobservable")
    if transported != owner["expected_choices_rows"]:
        return verdict("FAIL_PRODUCT", "owner_bundle_choices_changed", observed_pack=expected_pack,
                       choices_summary=_choices_summary(transported, owner["expected_choices_rows"]))
    return None


def _partition_payload(output):
    for value in base.json_values(output):
        if isinstance(value, dict) and value.get("status") == "ok":
            return value
    return None


def _owner_projection(entry):
    """One partition owner as {professor_dir, status, choices_rows}.

    The supported output form carries the status nested under ``partition``;
    the flat form describes the same value, so both project identically.
    """
    if not isinstance(entry, dict):
        return {"professor_dir": None, "status": None, "choices_rows": None}
    status = entry.get("status")
    if status is None and isinstance(entry.get("partition"), dict):
        status = entry["partition"].get("status")
    return {"professor_dir": entry.get("professor_dir"), "status": status,
            "choices_rows": entry.get("choices_rows")}


def _partition_rows(payload):
    owners = payload.get("owners")
    if not isinstance(owners, list):
        return None
    return [_owner_projection(entry) for entry in owners]


def _dir_key(row):
    return str(row.get("professor_dir"))


def _compound_action(command):
    """The single supported stage5 action word in a compound command text.

    Compound host expressions carry action words inside quoted strings, so
    strict parsing cannot attribute them; the loose text scan does. Returns
    None when several action words appear — such a text cannot be attributed
    to one orchestration step.
    """
    actions = [action for action in ACTIONS if action in command]
    return actions[0] if len(actions) == 1 else None


def runtime_checks(calls, manifest, consumption_points, root_texts, root=None, outcomes=None, owner_threads=None):
    """The r21 root orchestration oracle over executed stage5 calls.

    Discovery must report exactly the fixture owner set and must not emit a
    choices scope; the root must succeed at exactly one partition whose
    per-owner bundles match the manifest partition record and whose
    completion precedes every owner business call; owner plans stay
    bound to their own pack and bundle file and never carry a choices scope;
    at most one rebuild may run after every owner result was consumed
    (``consumption_points`` are the root's per-child result-consumption
    points, the earliest matching root-thread receipt seqs); and the pinned
    final source must carry one consistent consumed outcome per owner
    directory.

    A supported call is recognized on two surfaces. A call whose command
    parses strictly under ``command_action`` keeps every flag fact: only such
    a call can prove the ``--emit-choices-scope``/``--choices-scope``/
    ``--program-root`` facts. A compound command (a ``python3 -c``/wrapper
    preparation whose action words are quoted string fragments, never
    standalone tokens) is recognized by ``is_business_surface`` plus its
    single action word and contributes only its thread attribution and its
    ``aggregatedOutput``: discovery and partition success are judged from the
    output JSON alone. A compound root text carrying several action words
    cannot be attributed to one orchestration step and stays
    BLOCKED_OBSERVABILITY/root_orchestration_ambiguous. A child's compound
    consumption is judged by the packet oracle; on a child thread only a
    strictly parsed partition, or a compound text whose single action word is
    ``stage5-partition-choices``, proves ``partition_executed_by_owner``.
    """
    discovery, partitions, plans, rebuilds = [], [], [], []
    owner_threads = owner_threads or {}
    for call in calls:
        command, thread = call["command"], call.get("thread")
        try:
            parsed = command_action(command, manifest)
        except ValueError as exc:
            if not is_business_surface(command):
                return verdict("BLOCKED_OBSERVABILITY", str(exc))
            parsed = None
        if parsed is None:
            if not is_business_surface(command):
                continue
            if "--help" in command:
                # Help output stays non-evidence, mirroring the strict
                # grammar's --help exclusion for compound texts too.
                continue
            action = _compound_action(command)
            if action is None:
                if root is None or thread == root:
                    return verdict("BLOCKED_OBSERVABILITY", "root_orchestration_ambiguous",
                                   detail=command[:200])
                continue
            if root is not None and thread != root:
                # A child's compound consumption is judged by the packet
                # oracle, never by orchestration flag facts.
                if action == "stage5-partition-choices":
                    return verdict("FAIL_PRODUCT", "partition_executed_by_owner")
                continue
            parsed = {"action": action, "flags": {}, "compound": True}
        if parsed.get("problem"):
            return verdict("FAIL_PRODUCT", parsed["problem"])
        parsed.update(call)
        action, thread = parsed["action"], call.get("thread")
        # Compound calls carry empty flags, so this scope check can only ever
        # fire for a strictly parsed discovery call.
        if action == "stage5-list-inputs" and "--emit-choices-scope" in parsed["flags"]:
            return verdict("FAIL_PRODUCT", "discovery_emits_choices_scope")
        if action == "stage5-plan":
            problem = _plan_checks(parsed, manifest, owner_threads.get(thread))
            if problem:
                return problem
        if root is not None and thread != root:
            if action == "stage5-rebuild-overview":
                return verdict("FAIL_PRODUCT", "owner_rebuilds_aggregate")
            if action == "stage5-partition-choices":
                return verdict("FAIL_PRODUCT", "partition_executed_by_owner")
            if action == "stage5-list-inputs":
                continue
            plans.append(parsed)
            continue
        if action == "stage5-list-inputs":
            discovery.append(parsed)
        elif action == "stage5-partition-choices":
            partitions.append(parsed)
        elif action == "stage5-plan":
            plans.append(parsed)
        else:
            rebuilds.append(parsed)
    if not discovery:
        return verdict("BLOCKED_OBSERVABILITY", "executed_discovery_unobservable")
    expected_packs = {owner["email_pack"] for owner in manifest["owners"]}
    discovered = None
    for call in discovery:
        for value in base.json_values(call.get("output")):
            if isinstance(value, dict) and value.get("status") == "ok" and isinstance(value.get("inputs"), list):
                discovered = {row.get("email_pack"): row.get("status") for row in value["inputs"]}
    if discovered is None:
        return verdict("BLOCKED_OBSERVABILITY", "discovery_result_unobservable")
    if discovered != {**{pack: "ok" for pack in expected_packs}, manifest["invalid_pack"]: "error"}:
        return verdict("FAIL_PRODUCT", "discovery_owner_set_changed")
    successful = [(call, payload) for call in partitions
                  for payload in [_partition_payload(call.get("output"))] if payload is not None]
    if not successful:
        return verdict("FAIL_PRODUCT", "root_partition_not_deterministic", partition_commands=len(partitions))
    if len(successful) > 1:
        return verdict("FAIL_PRODUCT", "multiple_root_partitions")
    partition_call, partition_payload = successful[0]
    observed = _partition_rows(partition_payload)
    expected = [_owner_projection(entry) for entry in manifest["partition"]["owners"]]
    if observed is None or sorted(observed, key=_dir_key) != sorted(expected, key=_dir_key):
        return verdict("FAIL_PRODUCT", "root_partition_changed", observed_owners=observed)
    # r20 ordering fact: the successful root partition must complete before
    # any owner business call starts on a child thread. On a child thread a
    # strictly parsed stage5-list-inputs stays outside the business surface;
    # every other strictly parsed stage5 call and every compound command on
    # the loose business surface counts as an owner business call.
    partition_end = partition_call["end"]
    for call in calls:
        if root is None or call.get("thread") == root:
            continue
        command = call.get("command", "")
        try:
            parsed = command_action(command, manifest)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed["action"] == "stage5-list-inputs":
                continue
        elif not is_business_surface(command):
            continue
        if call["start"] < partition_end:
            return verdict("FAIL_PRODUCT", "owner_business_precedes_partition",
                           observed_call=command[:200])
    if len(rebuilds) > 1:
        return verdict("FAIL_PRODUCT", "multiple_aggregate_rebuilds")
    if rebuilds and rebuilds[0]["start"] <= max(consumption_points):
        return verdict("FAIL_PRODUCT", "aggregate_precedes_result_consumption")
    # The pinned final business result source is root's own final message.
    # Inside that source each professor directory must resolve to exactly one
    # consistent consumed outcome matching the owner's returned result.
    if base.source_malformed(root_texts):
        return verdict("INVALID_EVIDENCE", "root_final_result_malformed")
    rows = [row for row in final_result_rows(root_texts) if "status" in row and "reason_code" in row]
    for owner in manifest["owners"]:
        expected = (outcomes or {}).get(owner["email_pack"],
                    dict(owner["expected_result"], professor_dir=owner["professor_dir"]))
        consumed = [row for row in rows if row.get("professor_dir") == owner["professor_dir"]]
        if not consumed:
            return verdict("BLOCKED_OBSERVABILITY", "root_consumed_result_unobservable")
        seen = []
        for row in consumed:
            outcome = {key: row[key] for key in ("professor_dir", "status", "reason_code")}
            if outcome not in seen:
                seen.append(outcome)
        if len(seen) != 1:
            return verdict("FAIL_PRODUCT", "root_consumed_results_conflict", observed_results=seen)
        if seen[0] != expected:
            return verdict("FAIL_PRODUCT", "root_changed_owner_result", observed_result=seen[0])
    return verdict("PASS", owner_pack_set=sorted(expected_packs), rebuild_count=len(rebuilds),
                   partition_executions=1)


def _classify(problem, failures, invalids, blockers):
    bucket = problem.get("verdict")
    if bucket == "FAIL_PRODUCT":
        failures.append(problem)
    elif bucket == "INVALID_EVIDENCE":
        invalids.append(problem)
    else:
        blockers.append(problem)


def _verify_codex_events(response, adapter, manifest):
    status = adapter.get("fixture_status")
    if status in ("INVALID_EVIDENCE", "HARNESS_ERROR", "HARNESS_CONTAMINATION"):
        return verdict("INVALID_EVIDENCE", "shared_adapter_rejected")
    if status == "BLOCKED_DEPENDENCY":
        return verdict("BLOCKED_DEPENDENCY", "shared_adapter_dependency_unavailable")
    if status not in ("FIXTURE_READY", "HARNESS_DISPATCH_UNCONFIRMED", "HARNESS_DISPATCH_MISMATCH"):
        return verdict("INVALID_EVIDENCE", "unknown_shared_adapter_status")
    raw = response.get("output", {})
    root, generation = raw.get("thread_id"), raw.get("runtime_generation")
    events = raw.get("app_server_events")
    if not isinstance(events, list) or not root:
        return verdict("BLOCKED_OBSERVABILITY", "app_server_events_unobservable")
    relations = adapter.get("dispatch", {}).get("thread_relations", [])
    children = {child for edge in relations if edge.get("tool") == "spawnAgent"
                and edge.get("sender_thread_id") == root
                for child in edge.get("receiver_thread_ids", [])}
    if not children:
        return verdict("BLOCKED_OBSERVABILITY", "formal_delegation_unobservable")
    if len(children) != 2:
        return verdict("FAIL_PRODUCT", "wrong_owner_count", formal_children=sorted(children))
    payloads, complete, results = {}, {}, {}
    receipts = []
    command_starts, calls, root_texts, commands = {}, [], [], {}
    previous_seq = -1
    for event in events:
        seq = event.get("runtime_seq")
        if not isinstance(seq, int) or seq <= previous_seq or event.get("runtime_generation") != generation:
            return verdict("INVALID_EVIDENCE", "event_order_or_generation_invalid")
        previous_seq = seq
        message = event.get("message", {})
        method, params = message.get("method"), message.get("params", {})
        thread, item = params.get("threadId"), params.get("item", {})
        if method == "turn/completed" and thread in children:
            turn = params.get("turn", {})
            if turn.get("id") and turn.get("status") == "completed":
                complete[thread] = seq
        if method == "rawResponseItem/completed" and item.get("type") == "message":
            text = base.message_text(item)
            if thread in children and item.get("role") == "user":
                payloads.setdefault(thread, []).append(text)
            elif thread in children and item.get("role") == "assistant":
                results.setdefault(thread, []).append(text)
            elif thread == root and item.get("role") == "assistant":
                root_texts.append(text)
        if method == "rawResponseItem/completed" and item.get("type") == "agent_message" \
                and thread == root:
            # The real root result-consumption surface: the child's
            # FINAL_ANSWER receipt delivered back on the root thread. The
            # official V2 wait item's pairing fields are always empty and its
            # message is only wait status text, so collabAgentToolCall wait
            # items are never parsed as consumption evidence.
            receipts.append({"seq": seq, "author": item.get("author"),
                             "text": base.message_text(item)})
        if thread in children | {root} and item.get("type") == "commandExecution":
            item_id = (thread, item.get("id"))
            if method == "item/started":
                command_starts[item_id] = seq
            elif method == "item/completed":
                if item_id not in command_starts:
                    return verdict("BLOCKED_OBSERVABILITY", "command_start_unobservable")
                if thread in children:
                    commands.setdefault(thread, []).append(item.get("command", ""))
                calls.append({"start": command_starts[item_id], "end": seq,
                              "command": item.get("command", ""), "output": item.get("aggregatedOutput", ""),
                              "thread": thread})
    failures, invalids, blockers = [], [], []
    assigned, outcomes, consume_points = {}, {}, {}
    for child in sorted(children):
        stage5_texts = [text for text in commands.get(child, []) if is_business_surface(text)]
        rows, problem = consumed_business_objects(stage5_texts, payloads.get(child, []))
        if not problem:
            pack, problem = owner_payload(rows, manifest)
        if problem:
            _classify(problem, failures, invalids, blockers)
            continue
        if pack in assigned:
            failures.append(verdict("FAIL_PRODUCT", "duplicate_owner_pack"))
            continue
        assigned[pack] = child
        owner = next(owner for owner in manifest["owners"] if owner["email_pack"] == pack)
        outcome, problem = base.owner_outcome(results.get(child, []), owner)
        if problem:
            _classify(problem, failures, invalids, blockers)
            continue
        # The root consumed this child's result only where a root-thread
        # agent_message receipt names this owner's professor_dir and carries
        # exactly the outcome the child itself returned.
        matched = []
        for receipt in receipts:
            receipt_own = receipt_outcomes(receipt["text"], owner["professor_dir"])
            if receipt_own:
                matched.append((receipt["seq"], receipt_own))
        if not matched:
            blockers.append(verdict("BLOCKED_OBSERVABILITY", "root_result_consumption_unobservable"))
            continue
        observed = []
        for _, receipt_own in matched:
            for candidate in receipt_own:
                if candidate not in observed:
                    observed.append(candidate)
        if len(observed) != 1:
            invalids.append(verdict("INVALID_EVIDENCE", "root_result_receipt_ambiguous",
                                    observed_outcomes=observed))
            continue
        receipt_seq = min(seq for seq, _ in matched)
        completion = complete.get(child)
        if completion is not None and receipt_seq < completion:
            invalids.append(verdict("INVALID_EVIDENCE", "root_receipt_precedes_child_completion",
                                    receipt_seq=receipt_seq, child_completion=completion))
            continue
        if observed[0] != outcome:
            failures.append(verdict("FAIL_PRODUCT", "root_receipt_payload_changed",
                                    observed_result=observed[0], expected_result=outcome))
            continue
        consume_points[child] = receipt_seq
        outcomes[pack] = outcome
    for bucket in (failures, invalids, blockers):
        if bucket:
            return bucket[0]
    if raw.get("termination_reason") != "completed":
        return verdict("BLOCKED_DEPENDENCY", "root_turn_not_completed")
    result = runtime_checks(calls, manifest, list(consume_points.values()), root_texts, root=root,
                            outcomes=outcomes,
                            owner_threads={child: pack for pack, child in assigned.items()})
    result["identity_diagnostics"] = adapter.get("dispatch", {}).get("agent_identity", {})
    return result


def _judge_with_final_source(judge, final_text, *args):
    """Run the frozen r19 orchestration oracle with one machine-selected root text."""
    original = runtime_checks

    def pinned(calls, manifest, consumption_points, _root_texts, **kwargs):
        return original(calls, manifest, consumption_points, [final_text], **kwargs)

    globals()["runtime_checks"] = pinned
    try:
        return judge(*args)
    finally:
        globals()["runtime_checks"] = original


def verify_codex(response, adapter, manifest):
    final_text, problem = codex_final_result_source(response)
    if problem:
        return problem
    return _judge_with_final_source(_verify_codex_events, final_text, response, adapter, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--shared-verdict", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.host != "codex":
        parser.error("r19 verifies the codex host only")
    try:
        manifest = json.loads(args.manifest.read_text())
        shared = json.loads(args.shared_verdict.read_text())
        result = verify_codex(json.loads(args.events.read_text()), shared, manifest)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = verdict("INVALID_EVIDENCE", "unreadable_or_malformed_evidence", detail=str(exc))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
