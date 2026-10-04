#!/usr/bin/env python3
"""Observe shared Codex eval-service storage isolation without running a model.

The existing eval service is allowed to persist Codex state only when it uses a
test-only CODEX_HOME and test-only SQLite/log locations. This helper inspects
the already-running service and uses the same storage verifier as the formal
r14 acceptance entry. It never starts, stops, restarts, or sends an /eval
request.
"""
import argparse
import json
import subprocess
import tomllib
from pathlib import Path

import issue68_eval_service_isolation_r14 as isolation
import run_issue68_stage5_routing_r14_codex as formal


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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

    try:
        contract = formal.load_contract()
        eval_root = args.eval_direnv_root.resolve()
        revision = formal.base.clean_revision(eval_root, contract["eval_server_revision"])
        port = formal.resolve_eval_port(eval_root)
        service = formal.capture_service_instance(eval_root, port)
        storage = isolation.capture_storage_isolation(service)
        result = {
            "status": "ISOLATION_CONFIRMED",
            "eval_server": revision,
            "service": service,
            "storage": storage,
        }
    except (OSError, ValueError, subprocess.SubprocessError, tomllib.TOMLDecodeError) as exc:
        result = {
            "status": "CASE_NOT_STARTED",
            "reason_code": str(exc),
        }

    write_json(output / "isolation.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "ISOLATION_CONFIRMED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
