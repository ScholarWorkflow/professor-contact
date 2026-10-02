"""Non-acceptance characterization of the recipe's injected-error boundary."""
import io
import unittest

from gate2_evidence import EvidenceResult, classify
import test_issue74_fixture_support as recipe


class Issue74RecipeChecks(unittest.TestCase):
    def sample(self, reached, action):
        probe = recipe.Issue74FixtureTests()

        class KnownResult(unittest.TestCase):
            def test_boundary(self):
                with probe.injected_failure([True] if reached else []):
                    action()

        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=EvidenceResult).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(KnownResult))
        return result, classify(result, [])

    def test_valid_rejection_is_accepted(self):
        def valid_rejection():
            raise OSError("known write rejection")
        result, verdict = self.sample(True, valid_rejection)
        self.assertEqual(verdict, "PASS")
        self.assertEqual(result.events, [])

    def test_valid_product_failure_stays_failure(self):
        result, verdict = self.sample(True, lambda: None)
        self.assertEqual(verdict, "FAIL")
        self.assertEqual(result.events[0]["phase"], "product")

    def test_missing_hook_is_invalid(self):
        result, verdict = self.sample(False, lambda: None)
        self.assertEqual(verdict, "INVALID_TEST_EXECUTION")
        self.assertEqual(result.events[0]["phase"], "prerequisite")

    def test_callback_assertion_is_not_swallowed(self):
        def failed_assertion():
            raise AssertionError("known product assertion")
        result, verdict = self.sample(True, failed_assertion)
        self.assertEqual(verdict, "FAIL")
        self.assertEqual(result.events[0]["kind"], "failure")


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(Issue74RecipeChecks)
