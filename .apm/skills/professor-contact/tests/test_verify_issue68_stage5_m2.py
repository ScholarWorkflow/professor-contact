"""M2 regressions: complete-source business omissions are product failures.

Gate-2 review pr72-test-review-r1-2026-10-04 (M2): business_payload() and
owner_outcome() must resolve source completeness and attribution first,
then classify business content. A complete attributable source missing a
required business field is FAIL_PRODUCT; only a truly missing source is
BLOCKED_OBSERVABILITY; corrupted evidence is INVALID_EVIDENCE.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent / "runtime"


def load(name):
    spec = importlib.util.spec_from_file_location(name, RUNTIME / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = load("verify_issue68_stage5_routing")


class M2BusinessPayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.owner = {"professor_dir": str(self.root / "A"),
                      "email_pack": str(self.root / "A" / "邮件输入.json"),
                      "expected_result": {"status": "needs_refresh", "reason_code": "verify_missing"}}
        self.manifest = {"owners": [self.owner], "program_root": str(self.root),
                         "invalid_pack": str(self.root / "C" / "邮件输入.json"),
                         "expected_choices": [{"email_id": "X", "professor_dir": self.owner["professor_dir"]}],
                         "expected_scope": {self.owner["professor_dir"]: ["X"]}}

    def base_row(self):
        return {"email_pack": self.owner["email_pack"],
                "choices": self.manifest["expected_choices"],
                "choices_scope": self.manifest["expected_scope"]}

    def outcome_text(self, **changes):
        row = dict(self.owner["expected_result"], professor_dir=self.owner["professor_dir"])
        row.update(changes)
        return json.dumps(row)

    def test_complete_legitimate_payload_and_result_succeed(self):
        # Confirmation condition 1: a legal success still passes.
        pack, problem = verify.business_payload(json.dumps(self.base_row()), self.manifest)
        self.assertIsNone(problem)
        self.assertEqual(pack, self.owner["email_pack"])
        outcome, problem = verify.owner_outcome([self.outcome_text()], self.owner)
        self.assertIsNone(problem)
        self.assertEqual(outcome, {"professor_dir": self.owner["professor_dir"],
                                   "status": "needs_refresh", "reason_code": "verify_missing"})

    def test_present_but_changed_business_values_stay_product_failures(self):
        # Confirmation condition 2: valid business failures stay FAIL_PRODUCT.
        for field, value in (("choices", []), ("choices_scope", {})):
            with self.subTest(field=field):
                row = self.base_row()
                row[field] = value
                pack, problem = verify.business_payload(json.dumps(row), self.manifest)
                self.assertIsNone(pack)
                self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
                self.assertEqual(problem["reason_code"], field + "_transport_changed")
        outcome, problem = verify.owner_outcome([self.outcome_text(status="ok", reason_code=None)], self.owner)
        self.assertIsNone(outcome)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_verification_boundary_bypassed")

    def test_complete_source_missing_required_field_is_product_failure(self):
        # Confirmation condition 3: a complete attributable business object
        # that omits a required field is a real transport omission.
        for field in ("choices", "choices_scope"):
            with self.subTest(field=field):
                row = self.base_row()
                del row[field]
                pack, problem = verify.business_payload(json.dumps(row), self.manifest)
                self.assertIsNone(pack)
                self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
                self.assertEqual(problem["reason_code"], field + "_transport_missing")
        # A complete completion result of {} is an attributable result
        # object without business content, not a missing observation.
        for text in ("{}", json.dumps({"professor_dir": self.owner["professor_dir"]}),
                     "verification could not continue"):
            with self.subTest(text=text):
                outcome, problem = verify.owner_outcome([text], self.owner)
                self.assertIsNone(outcome)
                self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
                self.assertEqual(problem["reason_code"], "owner_business_result_missing")

    def test_truly_missing_source_still_blocks(self):
        # Confirmation condition 4: no attributable business source at all
        # remains BLOCKED_OBSERVABILITY.
        for text in ("", "no business object here", "null", "[]", None):
            with self.subTest(text=text):
                pack, problem = verify.business_payload(text, self.manifest)
                self.assertIsNone(pack)
                self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")
                self.assertEqual(problem["reason_code"], "owner_business_object_unobservable")
        for texts in ([], [""], ["   "]):
            with self.subTest(texts=texts):
                outcome, problem = verify.owner_outcome(texts, self.owner)
                self.assertIsNone(outcome)
                self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")
                self.assertEqual(problem["reason_code"], "owner_business_result_unobservable")

    def test_corrupted_or_ambiguous_evidence_is_invalid(self):
        # Confirmation condition 5: evidence that cannot be parsed into one
        # attributable source exits INVALID_EVIDENCE.
        with self.subTest(kind="ambiguous_business_object"):
            pack, problem = verify.business_payload(json.dumps([self.base_row(), self.base_row()]), self.manifest)
            self.assertIsNone(pack)
            self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")
            self.assertEqual(problem["reason_code"], "owner_business_object_ambiguous")
        for texts in ([42], [None]):
            with self.subTest(texts=texts):
                outcome, problem = verify.owner_outcome(texts, self.owner)
                self.assertIsNone(outcome)
                self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")
                self.assertEqual(problem["reason_code"], "owner_result_payload_unparseable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
