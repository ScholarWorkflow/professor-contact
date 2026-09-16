#!/usr/bin/env python3
"""Mechanical verifier for issue #40 PC40-R2.

R2 is intentionally narrow: it proves the formal nested Codex topology,
canonical Stage-2 artifact production, and that the installed Stage-3 plan
loader can consume that artifact.  Paper-analysis content quality and sidecar
presence are deterministic/product-contract concerns and are not R2 runtime
gates.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path(__file__).resolve().parent
GENERIC_VERIFIER = RUNTIME_DIR / "verify_issue32_e2e.py"
SPEC = importlib.util.spec_from_file_location("issue32_e2e_verifier", GENERIC_VERIFIER)
verifier = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(verifier)

R2_MIN_EDGES = 3
R2_REQUIRED_DEPTH = 3
PROFESSOR_RELATIVE = Path("教授研究/X分野/Example Professor")
INPUT_PACK = "套磁候选输入.json"
PROFILE_RELATIVE = Path("套磁邮件/套磁信息.md")
INSTALLED_RUNNER_RELATIVE = Path(".agents/skills/professor-contact/scripts/contact_state.py")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
        temporary = handle.name
    os.replace(temporary, path)


def verify(*, program_root: Path, consumer_root: Path, eval_response: Path,
           adapter_output: Path) -> dict[str, Any]:
    root = program_root.resolve()
    consumer = consumer_root.resolve()
    professor_dir = root / PROFESSOR_RELATIVE

    graph_args = argparse.Namespace(
        adapter_output=adapter_output.resolve(),
        eval_response=eval_response.resolve(),
        min_edges=R2_MIN_EDGES,
        required_depth=R2_REQUIRED_DEPTH,
    )
    graph = verifier._checkpoint_runtime_graph(graph_args)

    checks: list[dict[str, Any]] = [{
        "name": "formal_root_l1_l2_l3",
        "status": "pass" if graph.get("status") == "pass" else "fail",
        "detail": graph,
    }]

    input_pack = professor_dir / INPUT_PACK
    checks.append({
        "name": "canonical_stage2_input_exists",
        "status": "pass" if input_pack.is_file() else "fail",
        "detail": str(input_pack),
    })

    manifest_path = root / verifier.MANIFEST_NAME
    try:
        manifest = _load_json(manifest_path)
        profile_root = Path(manifest["profile_root"]).resolve()
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        checks.append({
            "name": "fixture_profile_resolved",
            "status": "fail",
            "detail": str(exc),
        })
        profile_root = Path()
    else:
        checks.append({
            "name": "fixture_profile_resolved",
            "status": "pass" if profile_root.is_dir() else "fail",
            "detail": str(profile_root),
        })

    runner = consumer / INSTALLED_RUNNER_RELATIVE
    profile = profile_root / PROFILE_RELATIVE if profile_root else Path()
    checks.append({
        "name": "installed_stage3_runner_exists",
        "status": "pass" if runner.is_file() else "fail",
        "detail": str(runner),
    })
    checks.append({
        "name": "canonical_profile_exists",
        "status": "pass" if profile.is_file() else "fail",
        "detail": str(profile),
    })

    stage3_plan: dict[str, Any] | None = None
    stage3_stdout = ""
    stage3_stderr = ""
    stage3_returncode: int | None = None
    if input_pack.is_file() and runner.is_file() and profile.is_file():
        command = [
            "python3", str(runner), "stage3-plan",
            "--professor-dir", str(professor_dir),
            "--profile", str(profile),
            "--refresh-scope", "flagged",
            "--program-root", str(root),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        stage3_returncode = completed.returncode
        stage3_stdout = completed.stdout
        stage3_stderr = completed.stderr
        try:
            parsed = json.loads(completed.stdout)
            stage3_plan = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            stage3_plan = None
        plan_ok = completed.returncode == 0 and isinstance(stage3_plan, dict)
    else:
        plan_ok = False

    checks.append({
        "name": "stage3_plan_consumes_stage2_input",
        "status": "pass" if plan_ok else "fail",
        "detail": {
            "returncode": stage3_returncode,
            "stdout_json": stage3_plan,
            "stderr": stage3_stderr,
        },
    })

    status = "pass" if all(row["status"] == "pass" for row in checks) else "fail"
    return {
        "status": status,
        "checks": checks,
        "observed": {
            "required_min_edges": R2_MIN_EDGES,
            "required_depth": R2_REQUIRED_DEPTH,
            "candidate_input": str(input_pack),
            "stage3_runner": str(runner),
            "stage3_profile": str(profile),
            "stage3_stdout": stage3_stdout,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--eval-response", type=Path, required=True)
    parser.add_argument("--adapter-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = verify(
            program_root=args.program_root,
            consumer_root=args.consumer_root,
            eval_response=args.eval_response,
            adapter_output=args.adapter_output,
        )
    except Exception as exc:
        payload = {
            "status": "fail",
            "checks": [{"name": "verifier_exception", "status": "fail", "detail": str(exc)}],
            "observed": {},
        }
    _atomic_json(args.output.resolve(), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
