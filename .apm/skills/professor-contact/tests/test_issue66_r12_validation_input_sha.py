"""Issue #66 Gate 2 r12 regression: the record-validation input hash.

`stage3-record-validation` must return `validation_input_sha256` computed
from the raw UTF-8 bytes THIS invocation actually read and parsed, so a
later overwrite of the same `validation_file` path cannot destroy the
per-round evidence of what the runner consumed.  The field is read-only
observability: it must never enter `套磁候选状态.json` and must not change
any round/correction semantics.  This module proves exactly that
observability field and nothing else.
"""
import hashlib
import json
import unittest

from test_stage2_resolved_direction import parse, run_cli
from test_stage3_direction_groups import Stage3DirectionGroupBase

CANDIDATE_STATE = "套磁候选状态.json"
CANDIDATES_MD = "套磁想法候选.md"


def validator_entry(prof_dir, verdict, minor):
    return {"result": "ok", "files": [{
        "file": str(prof_dir / CANDIDATES_MD), "artifact": "candidates",
        "verdict": verdict, "blocking": 0, "minor": minor, "issues": []}]}


class Issue66RecordValidationInputShaTests(Stage3DirectionGroupBase):
    def test_record_validation_returns_input_bytes_sha(self):
        """A→hash(A), overwrite with B, second call→hash(B); state untouched."""
        results = self.write_results(
            "r12-sha", {"dir_A": self.generated_doc("dir_A", ["P1", "P2", None])})
        out = self.stage3_finalize(results, "--direction-id", "dir_A")
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        validation_file = self.root / "validation-stage3.json"
        state_path = self.prof_dir / CANDIDATE_STATE

        payload_a = validator_entry(self.prof_dir, "pass", 0)
        validation_file.write_text(
            json.dumps(payload_a, ensure_ascii=False), encoding="utf-8")
        sha_a = hashlib.sha256(validation_file.read_bytes()).hexdigest()

        first = parse(run_cli("stage3-record-validation",
                              "--professor-dir", self.prof_dir,
                              "--validation-file", validation_file))
        self.assertEqual(first["status"], "ok", first)
        self.assertEqual(first["round"], 1)
        self.assertEqual(first["validation_input_sha256"], sha_a)

        # Overwrite the SAME path with different valid content B; the first
        # call's already-returned value cannot change, and the second call
        # must hash the bytes it actually read this time.
        payload_b = validator_entry(self.prof_dir, "pass_with_minor", 1)
        validation_file.write_text(
            json.dumps(payload_b, ensure_ascii=False), encoding="utf-8")
        sha_b = hashlib.sha256(validation_file.read_bytes()).hexdigest()
        self.assertNotEqual(sha_a, sha_b)

        second = parse(run_cli("stage3-record-validation",
                               "--professor-dir", self.prof_dir,
                               "--validation-file", validation_file))
        self.assertEqual(second["status"], "ok", second)
        self.assertEqual(second["round"], 2)
        self.assertEqual(second["validation_input_sha256"], sha_b)
        self.assertEqual(first["validation_input_sha256"], sha_a,
                         "the first round's returned hash is immutable evidence")

        # Read-only observability: the field must never enter the state file.
        state_text = state_path.read_text(encoding="utf-8")
        self.assertNotIn("validation_input_sha256", state_text)
        state = json.loads(state_text)
        self.assertNotIn("validation_input_sha256", state.get("validator") or {})

    def test_unreadable_validation_file_still_fails_closed(self):
        """A malformed input keeps the existing fail-closed channel (no hash)."""
        results = self.write_results(
            "r12-sha-bad", {"dir_A": self.generated_doc("dir_A", ["P1", "P2", None])})
        out = self.stage3_finalize(results, "--direction-id", "dir_A")
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        validation_file = self.root / "validation-broken.json"
        validation_file.write_text("{ malformed", encoding="utf-8")
        broken = parse(run_cli("stage3-record-validation",
                               "--professor-dir", self.prof_dir,
                               "--validation-file", validation_file))
        self.assertEqual(broken["status"], "error", broken)
        self.assertEqual(broken["reason_code"], "invalid_validation_json")
        self.assertNotIn("validation_input_sha256", broken)


if __name__ == "__main__":
    unittest.main()
