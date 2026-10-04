#!/usr/bin/env python3
"""Record run-bound runtime evidence for issue #67 PC67-RISO.

The POSTed eval request is the machine authority for this run's invocation.
The eval response supplies the actual Codex version/backend/runtime generation.
This recorder never contributes a product verdict; it only fails closed when
those two artifacts cannot be joined to the Gate-2 runtime configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import tempfile
from pathlib import Path
from typing import Any


class EvidenceError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be a JSON object")
    return value


def _flag_once(argv: list[str], flag: str) -> str:
    positions = [index for index, value in enumerate(argv) if value == flag]
    if len(positions) != 1 or positions[0] + 1 >= len(argv):
        raise EvidenceError(f"request must contain exactly one {flag} value")
    return argv[positions[0] + 1]


def _configs(argv: list[str]) -> list[str]:
    values: list[str] = []
    for index, value in enumerate(argv):
        if value == "--config":
            if index + 1 >= len(argv):
                raise EvidenceError("request contains --config without a value")
            values.append(argv[index + 1])
    return values


def record(*, eval_request: Path, eval_response: Path, expected_model: str,
           expected_reasoning: str, output: Path) -> dict[str, Any]:
    request = _load_object(eval_request, "eval request")
    response = _load_object(eval_response, "eval response")
    command = request.get("command")
    if not isinstance(command, str) or not command.strip():
        raise EvidenceError("eval request has no command")
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise EvidenceError(f"eval request command cannot be tokenized: {exc}") from exc

    model = _flag_once(argv, "--model")
    sandbox = _flag_once(argv, "--sandbox")
    cwd = _flag_once(argv, "--cd")
    configs = _configs(argv)
    reasoning_token = f'model_reasoning_effort="{expected_reasoning}"'
    if model != expected_model:
        raise EvidenceError(
            f"request model {model!r} does not match Gate-2 model {expected_model!r}")
    if configs.count(reasoning_token) != 1:
        raise EvidenceError(
            f"request does not contain exactly one Gate-2 reasoning override {reasoning_token!r}")

    version = response.get("version")
    runtime = response.get("output")
    if not isinstance(version, str) or not version.strip():
        raise EvidenceError("eval response has no Codex version")
    if not isinstance(runtime, dict):
        raise EvidenceError("eval response has no output object")
    backend = runtime.get("backend")
    generation = runtime.get("runtime_generation")
    if not isinstance(backend, str) or not backend.strip():
        raise EvidenceError("eval response has no backend")
    if isinstance(generation, bool) or not isinstance(generation, int):
        raise EvidenceError("eval response has no integer runtime_generation")

    evidence = {
        "schema": 1,
        "kind": "issue67-pc67-riso-runtime-evidence",
        "status": "ok",
        "invocation": {
            "model": model,
            "reasoning": expected_reasoning,
            "sandbox": sandbox,
            "consumer_root": cwd,
            "config_overrides": configs,
        },
        "runtime": {
            "codex_version": version,
            "backend": backend,
            "runtime_generation": generation,
        },
        "artifacts": {
            "eval_request_sha256": sha256(eval_request),
            "eval_response_sha256": sha256(eval_response),
        },
    }

    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output.parent,
        prefix=f".{output.name}.", delete=False,
    ) as handle:
        json.dump(evidence, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, output)
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-request", type=Path, required=True)
    parser.add_argument("--eval-response", type=Path, required=True)
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--expected-reasoning", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evidence = record(
            eval_request=args.eval_request,
            eval_response=args.eval_response,
            expected_model=args.expected_model,
            expected_reasoning=args.expected_reasoning,
            output=args.output,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "invalid",
            "classification": "INVALID_TEST_EXECUTION",
            "reason": str(exc),
        }, ensure_ascii=False))
        return 1
    print(json.dumps({
        "status": "ok",
        "output": str(args.output.resolve()),
        "runtime": evidence["runtime"],
        "invocation": {
            "model": evidence["invocation"]["model"],
            "reasoning": evidence["invocation"]["reasoning"],
            "sandbox": evidence["invocation"]["sandbox"],
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
