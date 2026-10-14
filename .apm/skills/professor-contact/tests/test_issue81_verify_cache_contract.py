"""Issue 81: Stage 5 verification-cache format and freshness contract."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "issue81_contact_state_test_helpers", HERE / "test_contact_state.py")
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)

PROFESSOR = helpers.ISSUE59_PROFESSOR
EMAIL_ID = helpers.ISSUE59_EMAIL_ID
REQUIRED_ITEMS = {
    "email", "roster", "season", "header", "subject_batch", "schedule",
    "consent", "warnings",
}


class Issue81VerifyCacheContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="issue81-verify-cache-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def initial_plan(self, fixture):
        template, _ = helpers.stage5_templates(self.root)
        result = helpers.raw_cli(
            "stage5-plan", "--program-root", fixture["program_root"],
            "--email-pack", fixture["pack"], "--template", template,
            "--mode", "first")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"stage5-plan did not return JSON: {exc}: {result.stdout}")

    def prepare_valid_cache(self, name):
        program_root = self.root / name
        fixture = helpers.write_issue59_stage5_fixture(program_root, case=self)
        verify_path = fixture["verify"][PROFESSOR]
        cached = json.loads(verify_path.read_text(encoding="utf-8"))

        # The first call is the actual read-only plan, before any verification
        # cache exists. Its hints are the only source of cached fingerprints.
        verify_path.unlink()
        first_plan = self.initial_plan(fixture)
        self.assertEqual(first_plan["verify"][PROFESSOR], "needs_recheck:missing")
        hint = first_plan["verify_write_hints"][PROFESSOR]
        self.assertEqual(
            set(hint["source_fingerprints"]), {"info_json", "boshu_analysis"})
        self.assertTrue(all(hint["source_fingerprints"].values()))
        self.assertEqual(hint["verified_at_format"], "%Y-%m-%dT%H:%M:%SZ")

        cached["verified_at"] = helpers.contact_state.now_utc()
        cached["source_fingerprints"] = hint["source_fingerprints"]
        verify_path.write_text(
            json.dumps(cached, ensure_ascii=False, indent=1), encoding="utf-8")
        return fixture, verify_path, cached, hint

    def test_a_actual_plan_hints_seed_a_reusable_complete_cache(self):
        fixture, verify_path, cached, hint = self.prepare_valid_cache("case-a")

        plan = self.initial_plan(fixture)

        program_root = Path(fixture["program_root"])
        expected_fingerprints = {
            "info_json": (
                f"{program_root / 'info.json'}:"
                f"{int((program_root / 'info.json').stat().st_mtime)}"),
            "boshu_analysis": (
                f"{program_root / 'boshu_analysis.json'}:"
                f"{int((program_root / 'boshu_analysis.json').stat().st_mtime)}"),
        }
        self.assertEqual(plan["verify"][PROFESSOR], "ok", plan)
        self.assertNotIn(PROFESSOR, plan["needs_recheck_professors"], plan)
        self.assertEqual(set(cached["items"]), REQUIRED_ITEMS)
        self.assertEqual(len(cached["items"]), 8)
        self.assertEqual(hint["source_fingerprints"], expected_fingerprints)
        self.assertEqual(hint["verified_at_format"], "%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(plan["verify_write_hints"][PROFESSOR]["source_fingerprints"],
                         json.loads(verify_path.read_text(encoding="utf-8"))[
                             "source_fingerprints"])
        self.assertEqual(plan["verify_write_hints"][PROFESSOR], hint)
        self.assertEqual(plan["verify_diagnostics"][PROFESSOR], {
            "reason": None, "failed_field": None, "diagnostic_kind": None})
        self.assertEqual(plan["emails"], [EMAIL_ID])
        self.assertEqual([job["job_id"] for job in plan["jobs"]],
                         [f"email:{EMAIL_ID}"])

    def test_b_noncanonical_values_keep_the_reason_and_report_the_field(self):
        cases = (
            ("float-mtime", "stale_fingerprint",
             "source_fingerprints.info_json", "format_incompatible"),
            ("alternate-path", "stale_fingerprint",
             "source_fingerprints.boshu_analysis", "format_incompatible"),
            ("fractional-time", "bad_timestamp", "verified_at",
             "format_incompatible"),
            ("offset-time", "bad_timestamp", "verified_at",
             "format_incompatible"),
        )
        for name, reason, field, kind in cases:
            with self.subTest(case=name):
                fixture, verify_path, cached, _ = self.prepare_valid_cache(
                    f"case-b-{name}")
                info_path = Path(fixture["program_root"]) / "info.json"
                boshu_path = Path(fixture["program_root"]) / "boshu_analysis.json"
                if name == "float-mtime":
                    cached["source_fingerprints"]["info_json"] = (
                        f"{info_path}:{int(info_path.stat().st_mtime)}.5")
                elif name == "alternate-path":
                    alternate = f"{boshu_path.parent}//{boshu_path.name}"
                    cached["source_fingerprints"]["boshu_analysis"] = (
                        f"{alternate}:{int(boshu_path.stat().st_mtime)}")
                elif name == "fractional-time":
                    cached["verified_at"] = (
                        helpers.contact_state.now_utc().replace("Z", ".123Z"))
                else:
                    cached["verified_at"] = (
                        helpers.contact_state.now_utc().replace("Z", "+00:00"))
                verify_path.write_text(
                    json.dumps(cached, ensure_ascii=False, indent=1),
                    encoding="utf-8")

                plan = self.initial_plan(fixture)

                self.assertEqual(plan["verify"][PROFESSOR],
                                 f"needs_recheck:{reason}", plan)
                self.assertIn(PROFESSOR, plan["needs_recheck_professors"], plan)
                self.assertEqual(plan["verify_diagnostics"][PROFESSOR], {
                    "reason": reason, "failed_field": field,
                    "diagnostic_kind": kind})

    def test_c_changed_mtime_and_31_day_cache_remain_rejected(self):
        fixture, verify_path, cached, _ = self.prepare_valid_cache("case-c-mtime")
        info_path = Path(fixture["program_root"]) / "info.json"
        stat = info_path.stat()
        changed_mtime = int(stat.st_mtime) + 3600
        os.utime(info_path, (stat.st_atime, changed_mtime))

        plan = self.initial_plan(fixture)

        self.assertEqual(plan["verify"][PROFESSOR],
                         "needs_recheck:stale_fingerprint", plan)
        self.assertEqual(plan["verify_diagnostics"][PROFESSOR], {
            "reason": "stale_fingerprint",
            "failed_field": "source_fingerprints.info_json",
            "diagnostic_kind": "recorded_mtime_mismatch"})

        expired_fixture, expired_path, expired_cache, _ = self.prepare_valid_cache(
            "case-c-expired")
        expired_cache["verified_at"] = (
            (datetime.now(timezone.utc) - timedelta(days=31))
            .strftime("%Y-%m-%dT%H:%M:%SZ"))
        expired_path.write_text(
            json.dumps(expired_cache, ensure_ascii=False, indent=1),
            encoding="utf-8")

        expired_plan = self.initial_plan(expired_fixture)

        self.assertEqual(expired_plan["verify"][PROFESSOR],
                         "needs_recheck:expired", expired_plan)
        self.assertEqual(expired_plan["verify_diagnostics"][PROFESSOR], {
            "reason": "expired", "failed_field": "verified_at",
            "diagnostic_kind": "age_expired"})


if __name__ == "__main__":
    unittest.main()
