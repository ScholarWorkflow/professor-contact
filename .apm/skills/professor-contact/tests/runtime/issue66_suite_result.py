"""保留完整测试日志，同时从受支持的结果回调记录结构化证据。"""
import argparse
import json
import unittest
from pathlib import Path


class Result(unittest.TextTestResult):
    def __init__(self, *args):
        super().__init__(*args)
        self.records = []
        self.active = None

    def startTest(self, test):
        super().startTest(test)
        self.active = {"ordinal": self.testsRun, "test_id": test.id(),
                       "method": getattr(test, "_testMethodName", None),
                       "status": "ok", "events": []}
        self.records.append(self.active)

    def event(self, status, test, err=None, params=None):
        event = {"type": status, "test_id": test.id(), "params": params}
        if err:
            event.update(exception_type=err[0].__name__, reason=str(err[1]),
                         traceback=self._exc_info_to_string(err, test))
        self.active["events"].append(event)
        if status == "error" or self.active["status"] == "ok":
            self.active["status"] = status

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.event("failure", test, err)

    def addError(self, test, err):
        super().addError(test, err)
        self.event("error", test, err)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            status = "failure" if issubclass(err[0], test.failureException) else "error"
            self.event(status, subtest, err, dict(subtest.params))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.event("skipped", test)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.event("expected_failure", test, err)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.event("unexpected_success", test)

    def report(self):
        invalid = bool(self.errors or self.skipped or self.expectedFailures)
        classification = ("INVALID_TEST_EXECUTION" if invalid else
                          "PRODUCT_FAIL" if self.failures or self.unexpectedSuccesses else "PASS")
        return {"schema": "issue66-suite-result-v1", "tests_run": self.testsRun,
                "failures": len(self.failures), "errors": len(self.errors),
                "skipped": len(self.skipped), "classification": classification,
                "exit_code": 0 if self.wasSuccessful() else 1, "tests": self.records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(args.directory, args.pattern)
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    value = result.report()
    with Path(args.report).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=repr)
    return value["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
