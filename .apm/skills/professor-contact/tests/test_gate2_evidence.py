"""Minimal counterexamples for the shared evidence evaluator, not product cases."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from gate2_evidence import EvidenceResult, TestPreparationError, classify, main
import stage2_upstream_fixture


class Gate2EvidenceTests(unittest.TestCase):
    def run_sample(self, cls):
        return unittest.TextTestRunner(stream=io.StringIO(), resultclass=EvidenceResult).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(cls))

    def test_valid_success_and_product_failure_keep_their_channels(self):
        class Sample(unittest.TestCase):
            def test_value(self):
                self.assertEqual(1, 1)
        self.assertEqual(classify(self.run_sample(Sample), []), 'PASS')
        Sample.test_value = lambda self: self.assertEqual(1, 2)
        self.assertEqual(classify(self.run_sample(Sample), []), 'FAIL')
        def error(self):
            raise ValueError('valid product call failed')
        Sample.test_value = error
        self.assertEqual(classify(self.run_sample(Sample), []), 'FAIL')

    def test_fixture_failure_never_becomes_product_failure(self):
        executed = []
        class Sample(unittest.TestCase):
            def setUp(self):
                raise OSError('fixture directory unavailable')
            def test_value(self):
                executed.append(True)
        result = self.run_sample(Sample)
        self.assertEqual(classify(result, []), 'INVALID_TEST_EXECUTION')
        self.assertEqual(executed, [])
        self.assertEqual(result.events[0]['phase'], 'setup')

        class InMethodPrerequisite(unittest.TestCase):
            def test_value(self):
                raise TestPreparationError('upstream prerequisite unavailable')
        result = self.run_sample(InMethodPrerequisite)
        self.assertEqual(classify(result, []), 'INVALID_TEST_EXECUTION')
        self.assertEqual(result.events[0]['phase'], 'prerequisite')
        self.assertEqual(result.events[0]['verdict'], 'INVALID_TEST_EXECUTION')

        class WrappedStage2Prerequisite(unittest.TestCase):
            def test_value(self):
                stage2_upstream_fixture.prepare_stage2_proof(None, 'unused.json')
        with mock.patch.object(
                stage2_upstream_fixture, '_prepare_stage2_proof',
                side_effect=AssertionError('controlled upstream preparation failure')):
            result = self.run_sample(WrappedStage2Prerequisite)
        self.assertEqual(classify(result, []), 'INVALID_TEST_EXECUTION')
        self.assertEqual(result.events[0]['phase'], 'prerequisite')
        self.assertEqual(result.events[0]['verdict'], 'INVALID_TEST_EXECUTION')

    def test_subtest_failure_is_fail_and_cleanup_error_retains_product_failure(self):
        class Sample(unittest.TestCase):
            def test_value(self):
                with self.subTest(value=1):
                    self.assertEqual(1, 2)
                self.addCleanup(lambda: (_ for _ in ()).throw(OSError('cleanup failed')))
        result = self.run_sample(Sample)
        self.assertEqual(classify(result, []), 'INVALID_TEST_EXECUTION')
        self.assertEqual([e['verdict'] for e in result.events],
                         ['FAIL', 'INVALID_TEST_EXECUTION'])

    def test_missing_execution_is_not_pass(self):
        self.assertEqual(classify(None, ['import failure']), 'CASE_NOT_STARTED')
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=EvidenceResult).run(
            unittest.TestSuite())
        self.assertEqual(classify(result, []), 'INVALID_TEST_EXECUTION')
        class Present(unittest.TestCase):
            def test_value(self):
                pass
        result = self.run_sample(Present)
        self.assertEqual(classify(result, [], ['missing.required.proof.']),
                         'INVALID_TEST_EXECUTION')
        duplicate = self.run_sample(Present)
        duplicate.started.append(duplicate.started[0])
        duplicate.completed.append(duplicate.completed[0])
        self.assertEqual(classify(duplicate, []), 'INVALID_TEST_EXECUTION')
        class Skipped(unittest.TestCase):
            @unittest.skip('declared unavailable path')
            def test_value(self):
                pass
        self.assertEqual(classify(self.run_sample(Skipped), []), 'NOT TESTED')
        result.started.append('incomplete.test')
        self.assertEqual(classify(result, []), 'INVALID_TEST_EXECUTION')
        class Interrupted(unittest.TestCase):
            def test_a_failure(self):
                self.assertEqual(1, 2)
            def test_b_interrupt(self):
                raise KeyboardInterrupt('execution interrupted')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence.json'
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(Interrupted)
            with mock.patch.object(unittest.TestLoader, 'discover', return_value=suite), \
                    mock.patch.object(sys, 'argv', ['gate2_evidence', '--start', directory,
                                                   '--pattern', 'test_*.py', '--out', str(output)]), \
                    mock.patch('sys.stderr', io.StringIO()):
                self.assertEqual(main(), 1)
            evidence = json.loads(output.read_text())
            self.assertEqual(evidence['verdict'], 'INVALID_TEST_EXECUTION')
            self.assertEqual(evidence['interruption']['type'], 'KeyboardInterrupt')
            self.assertEqual(evidence['tests_run'], 2)
            self.assertEqual(evidence['events'][0]['verdict'], 'FAIL')
            self.assertTrue(evidence['failures'][0]['test_id'].endswith('test_a_failure'))
