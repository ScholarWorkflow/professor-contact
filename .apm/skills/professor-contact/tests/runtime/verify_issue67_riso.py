#!/usr/bin/env python3
"""Issue #67 PC67-RISO verifier entrypoint.

The product assertions remain owned by verify_issue32_e2e.py.  This thin entry
only supplies the runtime model/reasoning values frozen by the current Gate-2
recipe, so the issue-67 proof does not duplicate a project-wide default.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE_VERIFIER = HERE / "verify_issue32_e2e.py"


def _load_base_verifier():
    spec = importlib.util.spec_from_file_location("issue67_riso_base_verifier", BASE_VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base verifier: {BASE_VERIFIER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = _load_base_verifier()


def _config_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--expected-reasoning", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        config, forwarded = _config_parser().parse_known_args(raw)
        if not forwarded or forwarded[0] != "stage4-professor-isolation":
            raise ValueError("verify_issue67_riso.py only accepts stage4-professor-isolation")
        if not config.expected_model.strip() or not config.expected_reasoning.strip():
            raise ValueError("expected model and reasoning must be non-empty")
    except (SystemExit, ValueError) as exc:
        print(json.dumps({
            "status": "invalid",
            "classification": "INVALID_TEST_EXECUTION",
            "reason": str(exc),
        }, ensure_ascii=False))
        return 1

    # These constants are only the request-surface expectations used by the
    # existing PC67-RISO verifier.  Product assertions, evidence parsing and
    # verdict logic remain unchanged in the base verifier.
    verifier.ISSUE67_REQUEST_MODEL = config.expected_model
    verifier.ISSUE67_REQUEST_REASONING = config.expected_reasoning
    return verifier.main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
