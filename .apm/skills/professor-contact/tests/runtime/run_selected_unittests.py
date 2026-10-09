#!/usr/bin/env python3
"""Run an exact unittest selection and write a machine-readable result."""

import argparse
import json
import sys
import unittest
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("tests", nargs="+")
    args = parser.parse_args()

    # Executing this file by path makes Python put ``runtime/`` rather than the
    # caller's test directory first on sys.path.  The recipes intentionally run
    # from that test directory, so make the import root explicit.
    sys.path.insert(0, str(Path.cwd()))
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(args.tests)
    count = suite.countTestCases()
    if loader.errors or count != args.expected_count:
        payload = {"status": "collection_mismatch", "expected_count": args.expected_count,
                   "test_count": count, "collection_errors": loader.errors,
                   "successful": False}
        args.result.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 2

    run = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
    payload = {
        "status": "passed" if run.wasSuccessful() else "failed",
        "expected_count": args.expected_count,
        "test_count": run.testsRun,
        "failures": len(run.failures),
        "errors": len(run.errors),
        "skipped": len(run.skipped),
        "successful": run.wasSuccessful(),
    }
    args.result.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0 if run.wasSuccessful() and run.testsRun == args.expected_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
