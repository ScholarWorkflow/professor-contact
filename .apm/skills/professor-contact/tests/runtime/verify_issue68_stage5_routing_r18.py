#!/usr/bin/env python3
"""Gate-2 r18 PC68-R1 verifier: the owner business input the owner consumed.

r13 keeps the root final business message selector unchanged: exactly one
current-root, current-turn ``rawResponseItem/completed`` assistant
``final_answer``. r18 changes only the owner business-input evidence source.

A real Codex V2 child receives its task as ``rawResponseItem/completed``
``item.type=agent_message`` whose content is an ``input_text`` NEW_TASK shell
plus ``encrypted_content``; no plaintext ``email_pack``/``choices``/
``choices_scope`` object is observable on that surface, and
``output.child_thread_reads`` is metadata only. The plaintext business object
the owner actually consumed is recorded in the owner's own
``commandExecution`` items. r18 reads it there, per formal child thread.

The frozen content conditions are unchanged: each child carries exactly one
attributable ``email_pack`` plus complete, unmodified ``choices`` and
``choices_scope``. The supported ``choices_scope`` value is the mapping
``professor_dir -> email ids``; the owner may carry that mapping as the object
form or as the equivalent list of ``{professor_dir, email_ids}`` entries, so the
comparison is on the parsed mapping and never on the serialization form. A
proven product failure is never downgraded to a blocked or invalid terminal by
another child's missing or ambiguous evidence.
"""
import argparse
import ast
import json
from pathlib import Path

import verify_issue68_stage5_routing as base
import verify_issue68_stage5_routing_r13 as final_source


AGENT = base.AGENT
verdict = base.verdict
combine = base.combine
owner_outcome = base.owner_outcome
codex_final_result_source = final_source.codex_final_result_source
opencode_final_result_source = final_source.opencode_final_result_source
verify_opencode = final_source.verify_opencode


def _shell_decoded(text):
    """Undo the quoting a recorded shell command applies to inline payloads."""
    out, index = [], 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text) and text[index + 1] in "\"'\\$`":
            out.append(text[index + 1])
            index += 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


def _quoted_regions(text):
    """Contents of the single- and double-quoted regions of a command text."""
    regions, buffer, quote, escaped = [], [], None, False
    for char in text:
        if quote is not None:
            if escaped:
                buffer.append(char)
                escaped = False
            elif char == "\\":
                buffer.append(char)
                escaped = True
            elif char == quote:
                regions.append("".join(buffer))
                buffer, quote = [], None
            else:
                buffer.append(char)
        elif char in "\"'":
            quote = char
    return regions


def _text_variants(text, depth=3):
    """The recorded command plus the payload-bearing texts nested in its quoting."""
    yield text
    if depth <= 0:
        return
    decoded = _shell_decoded(text)
    source = text
    if decoded != text:
        source = decoded
        yield from _text_variants(decoded, depth - 1)
    for region in _quoted_regions(source):
        if region != source:
            yield from _text_variants(region, depth - 1)


def _balanced_objects(text):
    """Brace-balanced regions of arbitrary text, outermost first."""
    start, depth = None, 0
    for index, char in enumerate(text):
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth:
                depth -= 1
                if depth == 0 and start is not None:
                    yield text[start:index + 1]
                    start = None


def _rows(value):
    return [node for node in base.objects(value) if "email_pack" in node]


def _json_rows(text):
    return [row for value in base.json_values(text) for row in _rows(value)]


def _literal_rows(text):
    """Python-literal payload forms: ``packet = {...}`` with ``False``/``None``."""
    rows = []
    for region in _balanced_objects(text):
        try:
            value = ast.literal_eval(region)
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            continue
        rows.extend(_rows(value))
    return rows


def _unique(rows):
    unique, seen = [], set()
    for row in rows:
        key = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def business_objects(text):
    """Plaintext business objects recorded in one command text.

    The recorded command may embed the object as JSON or as a Python literal,
    inside shell quoting; both supported forms are decoded from the same text.
    """
    if not isinstance(text, str):
        return []
    rows = []
    for variant in _text_variants(text):
        rows.extend(_json_rows(variant))
        rows.extend(_literal_rows(variant))
    return _unique(rows)


def scope_mapping(value):
    """The supported ``choices_scope`` value as ``{professor_dir: [email_ids]}``.

    Object form and list-of-entries form describe the same mapping. Any other
    shape, a non-string directory or a non-list of strings is not a supported
    scope value and returns ``None``.
    """
    mapping = {}
    if isinstance(value, dict):
        items = list(value.items())
    elif isinstance(value, list):
        items = []
        for entry in value:
            if not isinstance(entry, dict) or "professor_dir" not in entry or "email_ids" not in entry:
                return None
            items.append((entry["professor_dir"], entry["email_ids"]))
    else:
        return None
    for raw_dir, ids in items:
        if not isinstance(raw_dir, str) or not isinstance(ids, list) \
                or any(not isinstance(email_id, str) for email_id in ids) or raw_dir in mapping:
            return None
        mapping[raw_dir] = list(ids)
    return mapping


def owner_business_objects(payload_texts, command_texts):
    """The business objects this owner consumed, else the payload it received.

    The owner's own ``commandExecution`` commands are the consumption surface of
    a real Codex V2 child. The plaintext child user message stays the delivery
    fallback for hosts that hand the business object to the child itself. When
    the consumption surface is observable but exposes no business object, the
    verdict is the frozen ``owner_business_object_unobservable`` blocker; the
    legacy ``completed_user_payload_unobservable`` blocker is kept only for a run
    where neither surface carries the payload.
    """
    consumed = _unique([row for text in command_texts for row in business_objects(text)])
    if consumed:
        return consumed, None
    delivered = [text for text in payload_texts
                 if any("email_pack" in row for value in base.json_values(text) for row in base.objects(value))]
    if len(delivered) > 1 or (not delivered and not command_texts):
        return [], verdict("BLOCKED_OBSERVABILITY", "completed_user_payload_unobservable")
    if len(delivered) == 1:
        return _unique([row for text in delivered for row in business_objects(text)]), None
    return [], None


def owner_payload(rows, manifest):
    """Frozen source-completeness-then-content conditions for one owner payload."""
    if len(rows) > 1:
        return None, verdict("INVALID_EVIDENCE", "owner_business_object_ambiguous",
                             observed_candidates=len(rows))
    if not rows:
        return None, verdict("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable")
    row = rows[0]
    pack = row["email_pack"]
    if pack not in {owner["email_pack"] for owner in manifest["owners"]}:
        return None, verdict("FAIL_PRODUCT", "unexpected_owner_pack", observed_pack=pack)
    if "choices" not in row:
        return None, verdict("FAIL_PRODUCT", "choices_transport_missing", observed_pack=pack)
    if row["choices"] != manifest["expected_choices"]:
        return None, verdict("FAIL_PRODUCT", "choices_transport_changed", observed_pack=pack)
    if "choices_scope" not in row:
        return None, verdict("FAIL_PRODUCT", "choices_scope_transport_missing", observed_pack=pack)
    expected = scope_mapping(manifest["expected_scope"])
    if expected is None:
        return None, verdict("INVALID_EVIDENCE", "manifest_scope_unusable")
    observed = scope_mapping(row["choices_scope"])
    if observed != expected:
        return None, verdict("FAIL_PRODUCT", "choices_scope_transport_changed", observed_pack=pack,
                             observed_scope=observed)
    return pack, None


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
    seqs, payloads, complete, results, waits = set(), {}, {}, {}, {}
    command_starts, calls, root_texts, commands = {}, [], [], {}
    previous_seq = -1
    for event in events:
        seq = event.get("runtime_seq")
        if not isinstance(seq, int) or seq <= previous_seq or event.get("runtime_generation") != generation:
            return verdict("INVALID_EVIDENCE", "event_order_or_generation_invalid")
        seqs.add(seq)
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
        if method == "item/completed" and item.get("type") == "collabAgentToolCall" \
                and item.get("senderThreadId") == root and item.get("tool") == "wait" \
                and item.get("status") == "completed":
            for child in item.get("receiverThreadIds", []):
                if child in children:
                    state = item.get("agentsStates", {}).get(child, {})
                    if state.get("status") == "completed":
                        waits[child] = seq
                        complete.setdefault(child, seq)
                        results.setdefault(child, []).append(state.get("message", ""))
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
    assigned, outcomes = {}, {}
    for child in sorted(children):
        rows, problem = owner_business_objects(payloads.get(child, []), commands.get(child, []))
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
        if child not in complete or child not in waits:
            blockers.append(verdict("BLOCKED_OBSERVABILITY", "completion_or_wait_unobservable"))
            continue
        if waits[child] < complete[child]:
            failures.append(verdict("FAIL_PRODUCT", "wait_precedes_owner_completion"))
            continue
        outcome, problem = base.owner_outcome(results.get(child, []), owner)
        if problem:
            _classify(problem, failures, invalids, blockers)
            continue
        outcomes[pack] = outcome
    for bucket in (failures, invalids, blockers):
        if bucket:
            return bucket[0]
    if raw.get("termination_reason") != "completed":
        return verdict("BLOCKED_DEPENDENCY", "root_turn_not_completed")
    result = base.runtime_checks(calls, manifest, list(waits.values()), root_texts, root=root, outcomes=outcomes,
                                 owner_threads={child: pack for pack, child in assigned.items()})
    result["identity_diagnostics"] = adapter.get("dispatch", {}).get("agent_identity", {})
    return result


def _judge_with_final_source(judge, final_text, *args):
    """Run the frozen business oracle with one machine-selected root text."""
    original = base.runtime_checks

    def pinned(calls, manifest, completion_points, _root_texts, **kwargs):
        return original(calls, manifest, completion_points, [final_text], **kwargs)

    base.runtime_checks = pinned
    try:
        return judge(*args)
    finally:
        base.runtime_checks = original


def verify_codex(response, adapter, manifest):
    final_text, problem = codex_final_result_source(response)
    if problem:
        return problem
    return _judge_with_final_source(_verify_codex_events, final_text, response, adapter, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("codex", "opencode"), required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--shared-verdict", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        shared = json.loads(args.shared_verdict.read_text())
        if args.host == "codex":
            result = verify_codex(json.loads(args.events.read_text()), shared, manifest)
        else:
            events = [json.loads(line) for line in args.events.read_text().splitlines() if line.strip()]
            result = verify_opencode(events, shared, manifest)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = verdict("INVALID_EVIDENCE", "unreadable_or_malformed_evidence", detail=str(exc))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
