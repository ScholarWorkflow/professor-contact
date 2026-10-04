#!/usr/bin/env python3
"""Gate-2 r13 PC68-R1 verifier using the existing Codex raw-event surface.

r12 remains historical evidence. r13 changes only the Codex root final-business
source: no root thread/read extension is required. The current eval response
already preserves rawResponseItem/completed notifications in
output.app_server_events. The unique final source is the current eval root,
current eval turn, assistant message whose phase is final_answer.
"""
import argparse
import json
from pathlib import Path

import verify_issue68_stage5_routing as base
import verify_issue68_stage5_routing_r12 as prior


AGENT = base.AGENT
verdict = base.verdict
business_payload = base.business_payload
owner_outcome = base.owner_outcome
runtime_checks = base.runtime_checks
combine = base.combine
opencode_final_result_source = prior.opencode_final_result_source
verify_opencode = prior.verify_opencode


def _message_output_text(item):
    content = item.get("content")
    if not isinstance(content, list):
        return None, verdict("INVALID_EVIDENCE", "root_final_message_malformed")
    parts = []
    for part in content:
        if not isinstance(part, dict):
            return None, verdict("INVALID_EVIDENCE", "root_final_message_malformed")
        if part.get("type") != "output_text":
            continue
        text = part.get("text")
        if not isinstance(text, str):
            return None, verdict("INVALID_EVIDENCE", "root_final_message_malformed")
        parts.append(text)
    if not parts:
        return None, verdict("INVALID_EVIDENCE", "root_final_message_malformed")
    return "".join(parts), None


def codex_final_result_source(response):
    """Select exactly one current-root/current-turn raw final answer.

    A prior turn, child thread, commentary message, unknown/missing phase, or a
    different runtime generation can never become the terminal business result.
    Missing supported evidence is BLOCKED_OBSERVABILITY. A candidate that is
    attributable but structurally malformed is INVALID_EVIDENCE.
    """
    if not isinstance(response, dict):
        return None, verdict("INVALID_EVIDENCE", "codex_response_malformed")
    raw = response.get("output")
    if not isinstance(raw, dict):
        return None, verdict("INVALID_EVIDENCE", "codex_output_malformed")

    root = raw.get("thread_id")
    turn = raw.get("turn_id")
    generation = raw.get("runtime_generation")
    if not isinstance(root, str) or not root or not isinstance(turn, str) or not turn:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_final_message_unobservable")

    events = raw.get("app_server_events")
    if events is None:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_final_message_unobservable")
    if not isinstance(events, list):
        return None, verdict("INVALID_EVIDENCE", "root_raw_events_malformed")

    terminal = []
    for entry in events:
        if not isinstance(entry, dict):
            return None, verdict("INVALID_EVIDENCE", "root_raw_events_malformed")
        if entry.get("runtime_generation") != generation:
            continue
        message = entry.get("message")
        if not isinstance(message, dict) or message.get("method") != "rawResponseItem/completed":
            continue
        params = message.get("params")
        if not isinstance(params, dict):
            return None, verdict("INVALID_EVIDENCE", "root_raw_event_malformed")
        thread_id = params.get("threadId")
        turn_id = params.get("turnId")
        if not isinstance(thread_id, str) or not thread_id or not isinstance(turn_id, str) or not turn_id:
            return None, verdict("INVALID_EVIDENCE", "root_raw_event_malformed")
        if thread_id != root or turn_id != turn:
            continue
        item = params.get("item")
        if not isinstance(item, dict):
            return None, verdict("INVALID_EVIDENCE", "root_raw_event_malformed")
        if item.get("type") != "message":
            continue
        if item.get("phase") != "final_answer":
            continue
        if item.get("role") != "assistant":
            return None, verdict("INVALID_EVIDENCE", "root_final_message_malformed")
        text, problem = _message_output_text(item)
        if problem:
            return None, problem
        terminal.append(text)

    if not terminal:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_final_message_unobservable")
    if len(terminal) != 1:
        return None, verdict("INVALID_EVIDENCE", "root_final_message_ambiguous")
    return terminal[0], None


def _judge_with_final_source(judge, final_text, *args):
    """Run the frozen r11 business oracle with one machine-selected root text."""
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
