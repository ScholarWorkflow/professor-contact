"""Collect per-child-thread evidence from the test-dedicated Codex rollout
store (issue #66 Gate 2 fix: the supported formal read channel for child
thread input and business messages).

The root /eval response alone does not carry each child thread's business
input.  The shared test environment's rollout store does: one JSONL file per
thread under ``CODEX_HOME/sessions/YYYY/MM/DD/``, named
``rollout-<ts>-<thread_id>.jsonl``.  This helper locates the file for each
requested thread id, verifies the session metadata matches, and extracts —
read-only — the ordered record inventory, the user inputs (business input is
the user message text after the runtime-injected environment context), every
agent message, and every tool call input.

It never writes into the store, never interprets business content, and never
guesses: a missing file or a session-id mismatch is reported as a gap the
judge must treat as an evidence gap.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def extract_thread(rollout_dir: Path, thread_id: str) -> dict:
    matches = sorted(rollout_dir.glob(f"rollout-*-{thread_id}.jsonl"))
    if not matches:
        return {"thread_id": thread_id, "status": "rollout_not_found",
                "searched": str(rollout_dir)}
    path = matches[0]
    session_ids = []
    user_inputs = []
    agent_messages = []
    tool_calls = []
    other_types = {}
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                other_types[f"line{line_no}:unparsable"] = 1
                continue
            rtype = record.get("type")
            payload = record.get("payload") or {}
            if rtype == "session_meta":
                session_ids.append(payload.get("session_id") or payload.get("id"))
                continue
            if rtype != "response_item":
                continue
            ptype = payload.get("type")
            if ptype == "message" and payload.get("role") == "user":
                text = "".join(
                    block.get("text", "")
                    for block in payload.get("content") or []
                    if isinstance(block, dict))
                user_inputs.append({"line": line_no, "text": text})
            elif ptype == "agent_message":
                text = "".join(
                    block.get("text", "")
                    for block in payload.get("content") or []
                    if isinstance(block, dict))
                agent_messages.append({"line": line_no, "text": text})
            elif ptype == "custom_tool_call":
                tool_calls.append({"line": line_no, "call_id":
                                   payload.get("call_id"),
                                   "name": payload.get("name"),
                                   "input": payload.get("input")})
            else:
                other_types[ptype or "none"] = \
                    other_types.get(ptype or "none", 0) + 1
    return {
        "thread_id": thread_id,
        "status": "ok",
        "rollout_file": str(path),
        "session_ids": session_ids,
        "user_inputs": user_inputs,
        "agent_messages": agent_messages,
        "tool_calls": tool_calls,
        "other_response_item_types": other_types,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollout-dir", required=True,
                        help="CODEX_HOME/sessions/YYYY/MM/DD directory")
    parser.add_argument("--thread-id", action="append", required=True,
                        help="formal child thread id (repeatable)")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    rollout_dir = Path(args.rollout_dir)
    result = {
        "schema": "issue66-child-evidence-v1",
        "rollout_dir": str(rollout_dir),
        "threads": [extract_thread(rollout_dir, thread_id)
                    for thread_id in args.thread_id],
    }
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    ok = all(t["status"] == "ok" for t in result["threads"])
    print("ok" if ok else "gaps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
