#!/usr/bin/env python3
"""Gate-2 r12 PC68-R1 verifier with a machine-pinned final root source.

The r11 oracle remains historical evidence. This successor changes only the
root final-business-source selection required by pr72-test-review-r2-2026-10-04:
Codex uses the formal thread/read terminal AgentMessage, and OpenCode uses the
last completed root text event after foreground owner tasks complete. Earlier
root text is never merged into the final business result.
"""
import argparse
import json
from pathlib import Path

import verify_issue68_stage5_routing as base


AGENT = base.AGENT
verdict = base.verdict
business_payload = base.business_payload
owner_outcome = base.owner_outcome
runtime_checks = base.runtime_checks
combine = base.combine


def codex_final_result_source(response):
    raw = response.get("output", {})
    root = raw.get("thread_id")
    generation = raw.get("runtime_generation")
    if not root:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_final_message_unobservable")
    root_read = raw.get("root_thread_read")
    if root_read is None:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_final_message_unobservable")
    if not isinstance(root_read, dict):
        return None, verdict("INVALID_EVIDENCE", "root_thread_read_malformed")
    if root_read.get("thread_id") != root or root_read.get("runtime_generation") != generation:
        return None, verdict("INVALID_EVIDENCE", "root_thread_read_attribution_mismatch")
    expected_request = {"method": "thread/read", "params": {"threadId": root, "includeTurns": True}}
    if root_read.get("request") != expected_request:
        return None, verdict("INVALID_EVIDENCE", "root_thread_read_request_mismatch")
    error = root_read.get("error")
    result = root_read.get("result")
    if error is not None:
        if result is not None or not isinstance(error, dict):
            return None, verdict("INVALID_EVIDENCE", "root_thread_read_result_error_malformed")
        return None, verdict("BLOCKED_OBSERVABILITY", "root_final_message_unobservable")
    if not isinstance(result, dict):
        return None, verdict("INVALID_EVIDENCE", "root_thread_read_result_malformed")
    thread = result.get("thread")
    if not isinstance(thread, dict) or thread.get("id") != root:
        return None, verdict("INVALID_EVIDENCE", "root_thread_read_thread_mismatch")
    turns = thread.get("turns")
    if not isinstance(turns, list):
        return None, verdict("INVALID_EVIDENCE", "root_thread_read_turns_malformed")

    latest = []
    for turn in turns:
        if not isinstance(turn, dict) or not isinstance(turn.get("items"), list):
            return None, verdict("INVALID_EVIDENCE", "root_thread_read_turn_malformed")
        terminal = []
        for item in turn["items"]:
            if not isinstance(item, dict):
                return None, verdict("INVALID_EVIDENCE", "root_thread_read_item_malformed")
            if item.get("type") == "agentMessage" and item.get("phase") == "final_answer":
                if not isinstance(item.get("text"), str):
                    return None, verdict("INVALID_EVIDENCE", "root_final_message_malformed")
                terminal.append(item["text"])
        if terminal:
            latest = terminal
    if not latest:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_final_message_unobservable")
    if len(latest) != 1:
        return None, verdict("INVALID_EVIDENCE", "root_final_message_ambiguous")
    return latest[0], None


def opencode_final_result_source(events):
    sessions = {event.get("sessionID") for event in events if event.get("sessionID")}
    if len(sessions) != 1:
        return None, verdict("INVALID_EVIDENCE", "root_session_not_unique")
    root = next(iter(sessions))
    task_completion_indices = []
    text_events = []
    for index, event in enumerate(events):
        if event.get("sessionID") != root:
            continue
        if event.get("type") == "tool_use":
            part = event.get("part", {})
            state = part.get("state", {}) if isinstance(part, dict) else {}
            if part.get("tool") == "task" and state.get("status") == "completed":
                task_completion_indices.append(index)
        elif event.get("type") == "text":
            text_events.append((index, event))
    if not text_events:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_final_message_unobservable")
    final_index, event = text_events[-1]
    if task_completion_indices and final_index <= max(task_completion_indices):
        return None, verdict("BLOCKED_OBSERVABILITY", "root_final_message_unobservable")
    part = event.get("part")
    if not isinstance(part, dict):
        return None, verdict("INVALID_EVIDENCE", "root_text_part_malformed")
    time = part.get("time")
    if (not isinstance(part.get("id"), str) or not part["id"] or
            not isinstance(part.get("messageID"), str) or not part["messageID"] or
            part.get("sessionID") != root or not isinstance(part.get("text"), str) or
            not isinstance(time, dict) or not isinstance(time.get("end"), (int, float))):
        return None, verdict("INVALID_EVIDENCE", "root_text_part_malformed")
    return part["text"], None


def _judge_with_final_source(judge, final_text, *args):
    """Run the frozen r11 oracle while replacing only its root-text input.

    The host parsers remain responsible for ownership, waits, commands and
    results. This wrapper prevents their historical root-text collectors from
    entering runtime_checks; exactly one machine-selected terminal source is
    supplied instead.
    """
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
    return _judge_with_final_source(base.verify_codex, final_text, response, adapter, manifest)


def verify_opencode(events, fixture_verdict, manifest):
    final_text, problem = opencode_final_result_source(events)
    if problem:
        return problem
    return _judge_with_final_source(base.verify_opencode, final_text, events, fixture_verdict, manifest)


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
