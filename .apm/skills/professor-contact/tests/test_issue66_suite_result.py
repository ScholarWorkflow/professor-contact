"""日志排版不得改变结果回调给出的结论。"""
import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("suite_result", Path(__file__).parent / "runtime/issue66_suite_result.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class StructuredResultTests(unittest.TestCase):
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
