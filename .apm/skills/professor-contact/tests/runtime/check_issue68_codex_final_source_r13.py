#!/usr/bin/env python3
"""Minimal r13 capability check for the Codex raw final-answer source.

This is Recipe Preflight evidence, not PC68-R1 acceptance. It sends one
root-only request through the existing eval service using the same model,
reasoning, sandbox and trust shape as the formal r13 request, then verifies
that the response exposes exactly one attributable current-turn
rawResponseItem/completed assistant message with phase=final_answer.
"""
import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

import build_issue68_codex_request_r12 as builder
import verify_issue68_stage5_routing_r13 as verifier


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify(response):
    text, problem = verifier.codex_final_result_source(response)
    if problem:
        verdict = problem.get("verdict")
        if verdict == "BLOCKED_OBSERVABILITY":
            return {
                "status": "CAPABILITY_ABSENT",
                "reason_code": problem.get("reason_code"),
                "formal_pc68_r1_allowed": False,
            }
        return {
            "status": "INVALID_EVIDENCE",
            "reason_code": problem.get("reason_code"),
            "formal_pc68_r1_allowed": False,
        }
    return {
        "status": "CAPABILITY_CONFIRMED",
        "reason_code": None,
        "formal_pc68_r1_allowed": True,
        "final_text_observed": isinstance(text, str),
        "final_text_length": len(text),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-direnv-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        print(json.dumps({"status": "CASE_NOT_STARTED", "reason_code": "output_directory_not_empty"}))
        return 2
    output.mkdir(parents=True, exist_ok=True)
    consumer = output / "consumer"
    consumer.mkdir()

    request = builder.build_request(consumer, "Reply with the single word ok")
    request["timeout"] = 300
    write_json(output / "request.json", request)

    try:
        port = subprocess.check_output(
            ["direnv", "exec", str(args.eval_direnv_root.resolve()), "printenv", "EVAL_PORT"],
            cwd=args.eval_direnv_root.resolve(),
            text=True,
        ).strip()
        if not port.isdecimal() or not 1 <= int(port) <= 65535:
            raise ValueError("eval_port_unavailable")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/eval",
            json.dumps(request).encode(),
            {"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=330) as response:
            payload = json.loads(response.read())
        write_json(output / "response.json", payload)
        result = classify(payload)
        result["codex_version"] = payload.get("version")
        out = payload.get("output") if isinstance(payload, dict) else None
        if isinstance(out, dict):
            result["backend"] = out.get("backend")
            result["runtime_generation"] = out.get("runtime_generation")
            result["thread_id"] = out.get("thread_id")
            result["turn_id"] = out.get("turn_id")
            result["termination_reason"] = out.get("termination_reason")
    except (OSError, TimeoutError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        result = {
            "status": "CASE_NOT_STARTED",
            "reason_code": "preflight_transport_or_bootstrap_failed",
            "detail": type(exc).__name__,
            "formal_pc68_r1_allowed": False,
        }

    write_json(output / "capability.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "CAPABILITY_CONFIRMED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
