#!/usr/bin/env python3
"""PC68-R1 verifier: parsed fields, formal ownership and ordered lifecycle.

Missing supported business/lifecycle observations are BLOCKED_OBSERVABILITY,
never a guessed product failure. Identity diagnostics cannot create an edge.
Synthetic verifier tests characterize the oracle; they are not runtime PASS.
"""
import argparse
import json
import shlex
import xml.etree.ElementTree as ET
from pathlib import Path

AGENT = "professor-contact-email-generator"


def verdict(value, reason=None, **detail):
    return {"state": "CASE_STARTED", "verdict": value, "reason_code": reason, **detail}


def json_values(text):
    """Decode complete JSON values embedded in a supported text field."""
    if not isinstance(text, str):
        return []
    values, decoder, offset = [], json.JSONDecoder(), 0
    while offset < len(text):
        if text[offset] not in "[{":
            offset += 1
            continue
        try:
            value, length = decoder.raw_decode(text[offset:])
        except ValueError:
            offset += 1
        else:
            values.append(value)
            offset += length
    return values


def objects(value):
    if isinstance(value, dict):
        yield value
        for member in value.values():
            yield from objects(member)
    elif isinstance(value, list):
        for member in value:
            yield from objects(member)


def message_text(item):
    content = item.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(part["text"] for part in content if isinstance(part, dict)
                     and part.get("type") in ("input_text", "output_text")
                     and isinstance(part.get("text"), str))


def business_payload(text, manifest):
    rows = [row for value in json_values(text) for row in objects(value)]
    candidates = [row for row in rows if "email_pack" in row]
    if len(candidates) != 1:
        return None, verdict("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable")
    row = candidates[0]
    pack = row["email_pack"]
    expected = {owner["email_pack"] for owner in manifest["owners"]}
    if pack not in expected:
        return None, verdict("FAIL_PRODUCT", "unexpected_owner_pack", observed_pack=pack)
    for field, expected_value in (("choices", manifest["expected_choices"]),
                                  ("choices_scope", manifest["expected_scope"])):
        if field not in row:
            return None, verdict("BLOCKED_OBSERVABILITY", f"{field}_transport_unobservable")
        if row[field] != expected_value:
            return None, verdict("FAIL_PRODUCT", f"{field}_transport_changed", observed_pack=pack)
    return pack, None


def result_observed(text, expected):
    return any(row.get("status") == expected["status"] and
               row.get("reason_code") == expected["reason_code"]
               for value in json_values(text) for row in objects(value))


def command_action(command, manifest):
    """Only a structured executed shell item can supply a CLI invocation."""
    tokens = shlex.split(command)
    actions = {"stage5-list-inputs", "stage5-plan", "stage5-rebuild-overview"}
    found = [token for token in tokens if token in actions]
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
    flags = {}
    tail = tokens[index + 1:]
    if len(tail) % 2:
        raise ValueError("stage5_invocation_arguments_unobservable")
    for offset in range(0, len(tail), 2):
        if not tail[offset].startswith("--") or tail[offset] in flags:
            raise ValueError("stage5_invocation_arguments_unobservable")
        flags[tail[offset]] = tail[offset + 1]
    if flags.get("--program-root") != manifest["program_root"]:
        return {"action": action, "problem": "wrong_program_root"}
    return {"action": action, "flags": flags}


def runtime_checks(calls, manifest, completion_points, root_texts, root=None):
    discovery, plans, rebuilds = [], [], []
    for call in calls:
        try:
            parsed = command_action(call["command"], manifest)
        except ValueError as exc:
            return verdict("BLOCKED_OBSERVABILITY", str(exc))
        if parsed is None:
            continue
        if parsed.get("problem"):
            return verdict("FAIL_PRODUCT", parsed["problem"])
        parsed.update(call)
        if root is not None and call.get("thread") != root:
            if parsed["action"] == "stage5-rebuild-overview":
                return verdict("FAIL_PRODUCT", "owner_rebuilds_aggregate")
            if parsed["action"] == "stage5-list-inputs":
                continue
        if parsed["action"] == "stage5-list-inputs":
            discovery.append(parsed)
        elif parsed["action"] == "stage5-plan":
            plans.append(parsed)
        else:
            rebuilds.append(parsed)
    if not discovery:
        return verdict("BLOCKED_OBSERVABILITY", "executed_discovery_unobservable")
    expected_packs = {owner["email_pack"] for owner in manifest["owners"]}
    discovered = None
    for call in discovery:
        for value in json_values(call.get("output")):
            if isinstance(value, dict) and value.get("status") == "ok" and isinstance(value.get("inputs"), list):
                discovered = {row.get("email_pack"): row.get("status") for row in value["inputs"]}
    if discovered is None:
        return verdict("BLOCKED_OBSERVABILITY", "discovery_result_unobservable")
    if discovered != {**{pack: "ok" for pack in expected_packs}, manifest["invalid_pack"]: "error"}:
        return verdict("FAIL_PRODUCT", "discovery_owner_set_changed")
    for owner in manifest["owners"]:
        scoped = [call for call in plans if call["flags"].get("--email-pack") == owner["email_pack"]
                  and result_observed(call.get("output"), owner["expected_result"])]
        # P7 owns actual runner attribution/consumption. R1 proves native
        # transport. OpenCode's root stream does not expose child Bash calls;
        # do not require an unsupported child lifecycle surface here.
        for call in scoped:
            for flag, expected in (("--choices", manifest["expected_choices"]),
                                   ("--choices-scope", manifest["expected_scope"])):
                if flag not in call["flags"]:
                    return verdict("FAIL_PRODUCT", "owner_plan_missing_" + flag[2:])
                try:
                    transported = json.loads(Path(call["flags"][flag]).read_text())
                except (OSError, ValueError):
                    return verdict("BLOCKED_OBSERVABILITY", "transport_file_unobservable")
                if transported != expected:
                    return verdict("FAIL_PRODUCT", "owner_plan_changed_" + flag[2:])
    if len(rebuilds) > 1:
        return verdict("FAIL_PRODUCT", "multiple_aggregate_rebuilds")
    if rebuilds and rebuilds[0]["start"] <= max(completion_points):
        return verdict("FAIL_PRODUCT", "aggregate_precedes_result_consumption")
    for owner in manifest["owners"]:
        rows = [row for text in root_texts for value in json_values(text) for row in objects(value)]
        if not any(row.get("professor_dir") == owner["professor_dir"]
                   and row.get("status") == owner["expected_result"]["status"]
                   and row.get("reason_code") == owner["expected_result"]["reason_code"] for row in rows):
            return verdict("BLOCKED_OBSERVABILITY", "root_consumed_result_unobservable")
    return verdict("PASS", owner_pack_set=sorted(expected_packs), rebuild_count=len(rebuilds))


def combine(hosts):
    for value in ("FAIL_PRODUCT", "INVALID_TEST_FIXTURE", "INVALID_TEST_EXECUTION",
                  "INVALID_EVIDENCE", "BLOCKED_OBSERVABILITY", "BLOCKED_DEPENDENCY"):
        if any(host.get("verdict") == value for host in hosts):
            return verdict(value, "host_verdict", hosts=hosts)
    if all(host.get("state") == "CASE_STARTED" and host.get("verdict") == "PASS" for host in hosts):
        return verdict("PASS", hosts=hosts)
    if any(host.get("state") == "CASE_NOT_STARTED" for host in hosts):
        return {"state": "CASE_NOT_STARTED", "reason_code": "host_not_started", "hosts": hosts}
    return verdict("INVALID_EVIDENCE", "unclassified_combination", hosts=hosts)


def verify_codex(response, adapter, manifest):
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
    command_starts, calls, root_texts = {}, [], []
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
            text = message_text(item)
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
                calls.append({"start": command_starts[item_id], "end": seq,
                              "command": item.get("command", ""), "output": item.get("aggregatedOutput", ""),
                              "thread": thread})
    assigned = {}
    for child in children:
        texts = payloads.get(child, [])
        if len(texts) != 1:
            return verdict("BLOCKED_OBSERVABILITY", "completed_user_payload_unobservable")
        pack, problem = business_payload(texts[0], manifest)
        if problem:
            return problem
        if pack in assigned:
            return verdict("FAIL_PRODUCT", "duplicate_owner_pack")
        assigned[pack] = child
        owner = next(owner for owner in manifest["owners"] if owner["email_pack"] == pack)
        if child not in complete or child not in waits:
            return verdict("BLOCKED_OBSERVABILITY", "completion_or_wait_unobservable")
        if waits[child] < complete[child]:
            return verdict("FAIL_PRODUCT", "wait_precedes_owner_completion")
        if not any(result_observed(text, owner["expected_result"]) for text in results.get(child, [])):
            return verdict("BLOCKED_OBSERVABILITY", "owner_business_result_unobservable")
    if raw.get("termination_reason") != "completed":
        return verdict("BLOCKED_DEPENDENCY", "root_turn_not_completed")
    result = runtime_checks(calls, manifest, list(waits.values()), root_texts, root=root)
    result["identity_diagnostics"] = adapter.get("dispatch", {}).get("agent_identity", {})
    return result


def task_result(text):
    try:
        node = ET.fromstring(text)
    except (ET.ParseError, TypeError):
        return ""
    if node.tag != "task" or node.get("state") != "completed":
        return ""
    result = node.find("task_result")
    return "" if result is None else (result.text or "")


def verify_opencode(events, fixture_verdict, manifest):
    if fixture_verdict.get("fixture_status") == "INVALID_EVIDENCE":
        return verdict("INVALID_EVIDENCE", "shared_parser_rejected")
    if fixture_verdict.get("fixture_status") != "FIXTURE_READY":
        return verdict("BLOCKED_DEPENDENCY", "opencode_fixture_not_ready")
    sessions = {event.get("sessionID") for event in events if event.get("sessionID")}
    if len(sessions) != 1:
        return verdict("INVALID_EVIDENCE", "root_session_not_unique")
    tasks, calls, done, root_texts = {}, {}, {}, []
    for index, event in enumerate(events):
        if event.get("type") == "text":
            root_texts.append(event.get("part", {}).get("text", ""))
        if event.get("type") != "tool_use":
            continue
        part = event.get("part", {})
        state = part.get("state", {})
        tool, call_id, inputs = part.get("tool"), part.get("callID"), state.get("input", {})
        if tool == "task":
            if not call_id or not isinstance(inputs, dict):
                return verdict("BLOCKED_OBSERVABILITY", "structured_task_input_unobservable")
            if inputs.get("subagent_type") != AGENT:
                return verdict("FAIL_PRODUCT", "unexpected_task_owner")
            if inputs.get("background") is True or state.get("metadata", {}).get("background") is True:
                return verdict("FAIL_PRODUCT", "background_owner_task")
            tasks.setdefault(call_id, inputs)
            if tasks[call_id] != inputs:
                return verdict("INVALID_EVIDENCE", "task_input_changed")
            if state.get("status") == "completed":
                time = state.get("time", {})
                if not isinstance(time.get("end"), (int, float)):
                    return verdict("BLOCKED_OBSERVABILITY", "task_completion_time_unobservable")
                done[call_id] = (time["end"], task_result(state.get("output")))
        elif tool == "bash" and isinstance(inputs, dict):
            time = state.get("time", {})
            if state.get("status") == "completed":
                if not all(isinstance(time.get(field), (int, float)) for field in ("start", "end")):
                    return verdict("BLOCKED_OBSERVABILITY", "bash_execution_time_unobservable")
                if time["end"] < time["start"]:
                    return verdict("INVALID_EVIDENCE", "negative_execution_duration")
                if not call_id:
                    return verdict("BLOCKED_OBSERVABILITY", "bash_call_id_unobservable")
                call = {"start": time["start"], "end": time["end"],
                        "command": inputs.get("command", ""), "output": state.get("output", "")}
                if call_id in calls and calls[call_id] != call:
                    return verdict("INVALID_EVIDENCE", "bash_completed_record_changed")
                calls[call_id] = call
    if not tasks:
        return verdict("BLOCKED_OBSERVABILITY", "structured_tasks_unobservable")
    if len(tasks) != 2:
        return verdict("FAIL_PRODUCT", "wrong_owner_count")
    assigned = {}
    for call_id, inputs in tasks.items():
        pack, problem = business_payload(inputs.get("prompt"), manifest)
        if problem:
            return problem
        if pack in assigned:
            return verdict("FAIL_PRODUCT", "duplicate_owner_pack")
        assigned[pack] = call_id
        if call_id not in done:
            return verdict("BLOCKED_OBSERVABILITY", "foreground_task_terminal_unobservable")
        owner = next(owner for owner in manifest["owners"] if owner["email_pack"] == pack)
        if not result_observed(done[call_id][1], owner["expected_result"]):
            return verdict("BLOCKED_OBSERVABILITY", "owner_business_result_unobservable")
    return runtime_checks(list(calls.values()), manifest, [row[0] for row in done.values()], root_texts)


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
