"""日志排版不得改变结果回调给出的结论。"""
import importlib.util
import io
import json
import os
import subprocess
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("suite_result", Path(__file__).parent / "runtime/issue66_suite_result.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class StructuredResultTests(unittest.TestCase):
    def candidate_case(self, *, ledger_valid, suite_valid, product_fails,
                       expected_overall, expected_failures, expected_validity):
        # 预期按计划第六节四种组合固定，不从被测汇总程序取值。
        class Case(unittest.TestCase):
            def test_product(self):
                if product_fails:
                    self.fail("独立产品断言违反")
        raw, _ = self.run_case(Case)
        failures = [row for row in raw["tests"] if row["status"] != "ok"]
        record = {"suite": "product_control", "owner": "product",
                  "result": raw["classification"],
                  "evidence_validity": "VALID" if suite_valid else "INVALID",
                  "structured_status_source": "raw-suite.json#tests.status",
                  "raw_event_source": "raw-suite.json#tests.events",
                  "failures": failures}
        value = {"candidate": {"validity": "VALID", "source": "candidate-files.sha256"},
                 "ledger": {"validity": "VALID" if ledger_valid else "INVALID",
                            "source": "samples.tsv;judge-samples.jsonl"},
                 "suites": [record]}
        parsed = subprocess.run(["jq", "-f", str(Path(__file__).parent /
                                "runtime/issue66_candidate_classify.jq")],
                                input=json.dumps(value), text=True,
                                capture_output=True, check=True)
        actual = json.loads(parsed.stdout)
        expected = {"overall": expected_overall,
                    "local_product_failure_count": expected_failures,
                    "evidence_validity": expected_validity}
        evidence_root = os.environ.get("EVIDENCE_DIR")
        if evidence_root:
            directory = Path(evidence_root) / "candidate-combinations" / self._testMethodName
            directory.mkdir(parents=True, exist_ok=False)
            for filename, content in (("raw-suite.json", raw), ("input.json", value),
                                      ("independent-expected.json", expected),
                                      ("actual.json", actual)):
                (directory / filename).write_text(json.dumps(content, ensure_ascii=False,
                                                             indent=2), encoding="utf-8")
        self.assertEqual(actual["overall"], expected_overall)
        self.assertEqual(actual["evidence_validity"], expected_validity)
        self.assertEqual(len(actual["local_product_failures"]), expected_failures)
        self.assertEqual(actual["runner_execution"], "COMPLETE")
        self.assertIn("仅表示运行器已执行完全部步骤", actual["runner_execution_meaning"])
        self.assertEqual(bool(actual["gaps"]), expected_validity == "INVALID")
        if expected_failures:
            self.assertEqual(actual["local_product_failures"][0]["test_id"], failures[0]["test_id"])
            self.assertEqual(actual["local_product_failures"][0]["events"], failures[0]["events"])
            self.assertEqual(actual["local_product_failures"][0]["raw_event_source"],
                             record["raw_event_source"])
        if product_fails and not suite_valid:
            # 套件自称有效却声称通过，与原始失败相矛盾，仍不能归因产品。
            contradictory = json.loads(json.dumps(value))
            contradictory["suites"][0]["evidence_validity"] = "VALID"
            contradictory["suites"][0]["result"] = "PASS"
            control = subprocess.run(["jq", "-f", str(Path(__file__).parent /
                                     "runtime/issue66_candidate_classify.jq")],
                                     input=json.dumps(contradictory), text=True,
                                     capture_output=True, check=True)
            control_result = json.loads(control.stdout)
            self.assertEqual(control_result["overall"], "INVALID_TEST_EXECUTION")
            self.assertEqual(control_result["local_product_failures"], [])
            if evidence_root:
                (directory / "contradictory-input.json").write_text(
                    json.dumps(contradictory, ensure_ascii=False, indent=2), encoding="utf-8")
                (directory / "contradictory-actual.json").write_text(control.stdout, encoding="utf-8")
        # 同一断言若归属测试程序，必须记执行无效，不能计作产品失败。
        if product_fails:
            value["suites"][0]["owner"] = "test_program"
            value["suites"][0]["result"] = "INVALID_TEST_EXECUTION"
            control = subprocess.run(["jq", "-f", str(Path(__file__).parent /
                                     "runtime/issue66_candidate_classify.jq")],
                                     input=json.dumps(value), text=True,
                                     capture_output=True, check=True)
            control_result = json.loads(control.stdout)
            self.assertEqual(control_result["overall"], "INVALID_TEST_EXECUTION")
            self.assertEqual(control_result["local_product_failures"], [])
            if evidence_root:
                (directory / "test-program-input.json").write_text(
                    json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
                (directory / "test-program-actual.json").write_text(control.stdout, encoding="utf-8")

    def test_valid_candidate_with_independent_product_failure(self):
        self.candidate_case(ledger_valid=True, suite_valid=True, product_fails=True,
                            expected_overall="FAIL", expected_failures=1, expected_validity="VALID")

    def test_invalid_ledger_keeps_independent_product_failure(self):
        self.candidate_case(ledger_valid=False, suite_valid=True, product_fails=True,
                            expected_overall="INVALID_TEST_EXECUTION", expected_failures=1,
                            expected_validity="INVALID")

    def test_invalid_material_cannot_attribute_product_failure(self):
        self.candidate_case(ledger_valid=False, suite_valid=False, product_fails=True,
                            expected_overall="INVALID_TEST_EXECUTION", expected_failures=0,
                            expected_validity="INVALID")

    def test_valid_candidate_all_checks_pass(self):
        self.candidate_case(ledger_valid=True, suite_valid=True, product_fails=False,
                            expected_overall="PASS", expected_failures=0, expected_validity="VALID")

    def run_case(self, case):
        log = io.StringIO()
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=helper.Result).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(case))
        value = result.report()
        # 与正式脚本使用相同字段，经 jq 解析；人读日志不参与分类。
        parsed = subprocess.run(["jq", "-r", ".classification"],
            input=json.dumps(value), text=True, capture_output=True, check=True)
        self.assertEqual(parsed.stdout.strip(), value["classification"])
        filter_path = Path(__file__).parent / "runtime/issue66_suite_classify.jq"
        for owner in ("product", "test_program"):
            mapped = subprocess.run(["jq", "-r", "--arg", "owner", owner,
                                    "-f", str(filter_path)], input=json.dumps(value),
                                    text=True, capture_output=True, check=True)
            expected = ("INVALID_TEST_EXECUTION" if owner == "test_program"
                        and value["classification"] == "PRODUCT_FAIL"
                        else value["classification"])
            self.assertEqual(mapped.stdout.strip(), expected)
        return value, log.getvalue()

    def test_valid_success_with_docstring(self):
        class Case(unittest.TestCase):
            def test_pass(self):
                """第一行\n第二行包含 FAILED 文本。"""
                self.assertEqual(1, 1)
        value, _ = self.run_case(Case)
        self.assertEqual(value["classification"], "PASS")
        self.assertEqual(value["tests_run"], 1)

    def test_multiline_failure_and_docstring_remain_product_failure(self):
        class Case(unittest.TestCase):
            def test_bad(self):
                """正常说明\n多行说明。"""
                self.fail("第一行\n第二行\nERROR: 只是断言详情")
        value, log = self.run_case(Case)
        self.assertEqual(value["classification"], "PRODUCT_FAIL")
        self.assertEqual(value["failures"], 1)
        self.assertIn("第二行", value["tests"][0]["events"][0]["reason"])
        self.assertIn("正常说明", log)

    def test_subtest_failures_keep_parent_identity_and_parameters(self):
        class Case(unittest.TestCase):
            def test_bad(self):
                """正常说明。"""
                for section in ("一", "二"):
                    with self.subTest(section=section):
                        self.fail("产品行为失败\n详情")
        value, _ = self.run_case(Case)
        self.assertEqual(value["classification"], "PRODUCT_FAIL")
        self.assertEqual(value["tests_run"], 1)
        self.assertEqual(value["failures"], 2)
        self.assertEqual([row["params"] for row in value["tests"][0]["events"]],
                         [{"section": "一"}, {"section": "二"}])

    def test_fixture_error_is_invalid(self):
        class Case(unittest.TestCase):
            def setUp(self):
                raise RuntimeError("夹具缺失\n详情")
            def test_case(self):
                self.fail("未执行")
        value, _ = self.run_case(Case)
        self.assertEqual(value["classification"], "INVALID_TEST_EXECUTION")
        self.assertEqual(value["errors"], 1)

    def test_loading_error_is_invalid(self):
        log = io.StringIO()
        result = unittest.TextTestRunner(stream=log, resultclass=helper.Result).run(
            unittest.defaultTestLoader.loadTestsFromName("missing_issue66_module"))
        self.assertEqual(result.report()["classification"], "INVALID_TEST_EXECUTION")
