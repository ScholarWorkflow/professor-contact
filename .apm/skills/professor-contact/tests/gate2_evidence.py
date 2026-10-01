import argparse
import json
import os
from pathlib import Path
import sys
import unittest


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started = []
        self.completed = []
        self.events = []
        self.phases = {}
        self.originals = {}

    def startTest(self, test):
        self.started.append(test.id())
        self.phases[test.id()] = 'setup'
        originals = {}
        for name, phase in (('_callSetUp', 'setup'), ('_callTestMethod', 'product'),
                            ('_callTearDown', 'teardown'), ('_callCleanup', 'cleanup')):
            original = getattr(test, name)
            originals[name] = (name in test.__dict__, test.__dict__.get(name))
            def invoke(*args, _original=original, _phase=phase, **kwargs):
                self.phases[test.id()] = _phase
                return _original(*args, **kwargs)
            setattr(test, name, invoke)
        self.originals[test.id()] = originals
        super().startTest(test)

    def stopTest(self, test):
        self.completed.append(test.id())
        for name, (present, value) in self.originals.pop(test.id(), {}).items():
            if present:
                setattr(test, name, value)
            else:
                delattr(test, name)
        super().stopTest(test)

    def record(self, test, kind, detail=None):
        # Module/class setup errors arrive as unittest _ErrorHolder objects.
        owner = getattr(test, 'test_case', test)
        phase = self.phases.get(owner.id(), 'setup')
        verdict = ('FAIL' if phase == 'product' else 'INVALID_TEST_EXECUTION')
        self.events.append({'test_id': owner.id(), 'evidence_id': test.id(),
                            'kind': kind, 'phase': phase, 'verdict': verdict,
                            'detail': detail})

    def addError(self, test, err):
        self.record(test, 'error', self._exc_info_to_string(err, test))
        super().addError(test, err)

    def addFailure(self, test, err):
        self.record(test, 'failure', self._exc_info_to_string(err, test))
        super().addFailure(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.record(subtest, 'subtest', self._exc_info_to_string(err, subtest))
        super().addSubTest(test, subtest, err)


def classify(result, load_errors):
    if load_errors or result is None:
        return "CASE_NOT_STARTED"
    if (result.testsRun == 0 or result.started != result.completed
            or result.expectedFailures or result.unexpectedSuccesses
            or any(e['verdict'] == 'INVALID_TEST_EXECUTION' for e in result.events)):
        return "INVALID_TEST_EXECUTION"
    if result.failures or result.errors:
        return "FAIL"
    if result.skipped:
        return "NOT TESTED"
    return "PASS"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--contains")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if Path(args.out).exists():
        parser.error('--out already exists; use a new evidence file')
    # 子进程的 python3 必须使用与本入口相同的解释器。
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    loader = unittest.TestLoader()
    if args.contains:
        loader.testNamePatterns = ["*" + args.contains + "*"]
    load_errors = []
    result = None
    interruption = None
    try:
        suite = loader.discover(args.start, pattern=args.pattern)
        load_errors = list(loader.errors)
        if not load_errors:
            def make_result(*args, **kwargs):
                nonlocal result
                result = EvidenceResult(*args, **kwargs)
                return result
            result = unittest.TextTestRunner(
                verbosity=2, resultclass=make_result
            ).run(suite)
    except BaseException as exc:
        interruption = {"type": type(exc).__name__, "message": str(exc)}
    verdict = ("INVALID_TEST_EXECUTION" if interruption
               else classify(result, load_errors))

    def records(items):
        return [{"test_id": test.id(), "detail": detail} for test, detail in items]

    evidence = {
        "schema_version": 2,
        "python": sys.version,
        "cwd": str(Path.cwd()),
        "selection": {"start": args.start, "pattern": args.pattern,
                      "contains": args.contains},
        "load_errors": load_errors,
        "interruption": interruption,
        "tests_run": result.testsRun if result else 0,
        "started": result.started if result else [],
        "completed": result.completed if result else [],
        "failures": records(result.failures) if result else [],
        "errors": records(result.errors) if result else [],
        "events": result.events if result else [],
        "skipped": records(result.skipped) if result else [],
        "expected_failures": records(result.expectedFailures) if result else [],
        "unexpected_successes": [test.id() for test in result.unexpectedSuccesses] if result else [],
        "verdict": verdict,
    }
    Path(args.out).write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
