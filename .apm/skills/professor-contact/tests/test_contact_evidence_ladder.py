import importlib.util
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location(
    "contact_state_test_helpers", HERE / "test_contact_state.py")
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)

BaseEnv = helpers.BaseEnv
TestStage5 = helpers.TestStage5
parse = helpers.parse
run_cli = helpers.run_cli

EVIDENCE_FILE = "教授研究/_联系方式证据.json"
# Same freshness window the runner applies (contact_state.VERIFY_TTL_DAYS);
# +1 day keeps the fixture unambiguously stale.
VERIFY_TTL_DAYS = 30


def fresh_ts():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stale_ts():
    return (datetime.now(timezone.utc) - timedelta(days=VERIFY_TTL_DAYS + 1)
            ).isoformat(timespec="seconds")


class TestContactEvidenceLadder(BaseEnv):
    prepare = TestStage5.prepare
    raw_result = TestStage5.raw_result
    choices = TestStage5.choices

    def write_artifact(self, record_overrides=None, artifact_overrides=None):
        record = {
            "professor": {"name": "試験 教授", "name_romaji": None},
            "official_emails": [{
                "email": "faculty@example.test", "current_source": True,
                "provenance": [{"source_type": "official_professor_candidate",
                                "source": "recruitment-faculty-list"}]}],
            "paper_correspondence": [{
                "email": "faculty@example.test", "name": "試験 教授",
                "item_key": "AAAA1111", "doi": None, "paper_year": 2025,
                "channel": "correspondence", "confidence": "high",
                "identity_match": "direct", "recent": True,
                "current_email_evidence": False}],
            "identity": {"matched_verified_contacts": 1,
                         "unmatched_verified_contacts": [],
                         "ambiguous_unpaired_records_ignored": 0},
            "verdict": "confirmed_cross_source",
            "confirmed_emails": ["faculty@example.test"],
            "conflicting_paper_emails": [],
            "current_email": "faculty@example.test",
        }
        record.update(record_overrides or {})
        artifact = {
            "schema": 1, "kind": "professor-contact-evidence",
            "generated_at": fresh_ts(),
            "recent_paper_years": 5, "current_year": 2026,
            "scope": "workflow_evidence_not_send_time_authority",
            "sources": {}, "degraded": False, "source_errors": [],
            "professors": [record],
        }
        artifact.update(artifact_overrides or {})
        path = self.root / EVIDENCE_FILE
        path.write_text(json.dumps(artifact, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        return record

    def compile_pack(self):
        sel_input = self.root / "sel_input.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1"}]}]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage4-finalize", "--program-root", self.root,
                            "--selection-input", sel_input))
        self.assertEqual(out["status"], "ok", out)
        pack = json.loads((self.root / "教授研究" / "邮件输入.json")
                          .read_text(encoding="utf-8"))
        return pack["emails"][0]

    def plan_jobs(self):
        return parse(run_cli("stage5-plan", "--program-root", self.root))

    def decision(self, plan):
        return plan["contact_evidence"]["試験 教授"]

    def run_finalize_flow(self, g1, tag):
        raw_path = self.root / f"{tag}-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False),
                            encoding="utf-8")
        choices_path = self.root / f"{tag}-choices.json"
        choices_path.write_text(json.dumps(self.choices(), ensure_ascii=False),
                                encoding="utf-8")
        draft = parse(run_cli("stage5-plan", "--program-root", self.root,
                              "--result", raw_path, "--choices", choices_path))
        self.assertEqual(draft["status"], "ok", draft)
        humanized_path = self.root / f"{tag}-humanized.txt"
        humanized_path.write_text(draft["drafts"][0]["draft"], encoding="utf-8")
        return parse(run_cli("stage5-finalize", "--program-root", self.root,
                             "--result", raw_path, "--humanized", humanized_path,
                             "--choices", choices_path))

    def test_stage4_embeds_snapshot_and_handles_absence(self):
        self.prepare()
        entry = self.compile_pack()
        self.assertIsNone(entry["contact_evidence"])
        self.write_artifact()
        entry = self.compile_pack()
        snapshot = entry["contact_evidence"]
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["record"]["verdict"], "confirmed_cross_source")
        self.assertEqual(snapshot["record"]["current_email"], "faculty@example.test")
        self.assertFalse(snapshot["degraded"])
        self.assertTrue(snapshot["record_fingerprint"])

    def test_plan_accepts_cross_source_without_web_lookup(self):
        g1 = self.prepare()
        self.write_artifact()
        self.compile_pack()
        plan = self.plan_jobs()
        decision = self.decision(plan)
        self.assertEqual(decision["status"], "confirmed_cross_source")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "faculty@example.test")
        self.assertFalse(decision["single_source"])
        self.assertEqual(decision["source"], "artifact")
        self.assertFalse(decision["snapshot_stale"])
        self.assertTrue(decision["provenance"]["official_provenance"])
        self.assertTrue(decision["provenance"]["paper_evidence"])

    def test_plan_escalates_conflict_instead_of_silently_choosing(self):
        self.prepare()
        record = self.write_artifact({
            "verdict": "conflict",
            "confirmed_emails": [],
            "conflicting_paper_emails": ["old-affiliation@example.test"],
            "paper_correspondence": [{
                "email": "old-affiliation@example.test", "name": "試験 教授",
                "item_key": "AAAA1111", "doi": None, "paper_year": 2018,
                "channel": "correspondence", "confidence": "high",
                "identity_match": "direct", "recent": False,
                "current_email_evidence": False}],
            "current_email": None})
        self.compile_pack()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_conflict")
        self.assertTrue(decision["web_lookup_required"])
        self.assertIsNone(decision["recipient_email"])
        self.assertNotIn(record["paper_correspondence"][0]["email"],
                         (decision["recipient_email"],))

    def test_plan_never_promotes_paper_only_email(self):
        self.prepare()
        record = self.write_artifact({
            "verdict": "paper_only", "current_email": None,
            "confirmed_emails": [], "official_emails": [],
            "paper_correspondence": [{
                "email": "old-alumni@example.test", "name": "試験 教授",
                "item_key": "AAAA1111", "doi": None, "paper_year": 2015,
                "channel": "correspondence", "confidence": "high",
                "identity_match": "direct", "recent": False,
                "current_email_evidence": False}]})
        self.compile_pack()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_paper_only")
        self.assertTrue(decision["web_lookup_required"])
        self.assertNotEqual(decision.get("recipient_email"),
                            record["paper_correspondence"][0]["email"])

    def test_plan_allows_single_official_only_source(self):
        self.prepare()
        self.write_artifact({
            "verdict": "official_only", "confirmed_emails": [],
            "paper_correspondence": []})
        self.compile_pack()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "official_only")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "faculty@example.test")
        self.assertTrue(decision["single_source"])

    def test_plan_escalates_on_degraded_artifact(self):
        self.prepare()
        self.write_artifact(artifact_overrides={
            "degraded": True,
            "source_errors": [{"source": "paper_correspondence",
                               "path": "_corresp_cache.json", "error": "invalid"}]})
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_artifact_degraded")
        self.assertTrue(decision["web_lookup_required"])

    def test_plan_escalates_on_unreadable_artifact(self):
        self.prepare()
        (self.root / EVIDENCE_FILE).write_text("{not json", encoding="utf-8")
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_artifact_unreadable")

    def test_plan_escalates_when_no_artifact_and_no_snapshot(self):
        self.prepare()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_missing")

    def test_plan_escalates_when_artifact_is_stale(self):
        self.prepare()
        self.write_artifact(artifact_overrides={"generated_at": stale_ts()})
        self.compile_pack()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_stale")
        self.assertTrue(decision["web_lookup_required"])
        self.assertIsNone(decision["recipient_email"])

    def test_plan_escalates_when_pack_snapshot_is_stale_and_artifact_absent(self):
        self.prepare()
        self.write_artifact(artifact_overrides={"generated_at": stale_ts()})
        self.compile_pack()
        (self.root / EVIDENCE_FILE).unlink()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_stale")
        self.assertTrue(decision["web_lookup_required"])

    def test_plan_escalates_when_freshness_cannot_be_confirmed(self):
        self.prepare()
        for bad_timestamp in (None, "", "not-a-date"):
            self.write_artifact(artifact_overrides={"generated_at": bad_timestamp})
            decision = self.decision(self.plan_jobs())
            self.assertEqual(decision["status"], "escalate", bad_timestamp)
            self.assertEqual(decision["reason_code"],
                             "contact_evidence_timestamp_invalid", bad_timestamp)
            self.assertTrue(decision["web_lookup_required"])

    def test_plan_uses_pack_snapshot_when_artifact_file_absent(self):
        self.prepare()
        self.write_artifact()
        self.compile_pack()
        (self.root / EVIDENCE_FILE).unlink()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "confirmed_cross_source")
        self.assertEqual(decision["source"], "pack_snapshot")
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "faculty@example.test")

    def test_plan_flags_stale_snapshot_but_uses_current_artifact(self):
        self.prepare()
        self.write_artifact()
        self.compile_pack()
        stale_record = self.write_artifact(record_overrides={
            "paper_correspondence": [{
                "email": "faculty@example.test", "name": "試験 教授",
                "item_key": "AAAA1111", "doi": None, "paper_year": 2024,
                "channel": "correspondence", "confidence": "high",
                "identity_match": "direct", "recent": True,
                "current_email_evidence": False}]})
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "confirmed_cross_source")
        self.assertTrue(decision["snapshot_stale"])
        self.assertEqual(decision["source"], "artifact")
        self.assertEqual(decision["recipient_email"],
                         stale_record["current_email"])

    def test_finalize_records_chosen_email_and_provenance(self):
        g1 = self.prepare()
        self.write_artifact()
        self.compile_pack()
        out = self.run_finalize_flow(g1, "evidence")
        self.assertEqual(out["status"], "ok", out)
        state = json.loads((self.prof_dir / "套磁邮件状态.json")
                           .read_text(encoding="utf-8"))
        recorded = state["emails"][self.choices()["email_id"]]["contact_evidence"]
        self.assertEqual(recorded["status"], "confirmed_cross_source")
        self.assertIsNone(recorded["reason_code"])
        self.assertEqual(recorded["chosen_email"], "faculty@example.test")
        self.assertEqual(recorded["evidence_email"], "faculty@example.test")
        self.assertFalse(recorded["web_lookup_required"])
        self.assertTrue(recorded["provenance"]["official_provenance"])
        self.assertTrue(recorded["provenance"]["paper_evidence"])
        self.assertIn("faculty@example.test",
                      (self.prof_dir / "套磁邮件.md").read_text(encoding="utf-8"))

    def test_finalize_records_stale_escalation_for_audit(self):
        g1 = self.prepare()
        self.write_artifact(artifact_overrides={"generated_at": stale_ts()})
        self.compile_pack()
        out = self.run_finalize_flow(g1, "stale-audit")
        self.assertEqual(out["status"], "ok", out)
        state = json.loads((self.prof_dir / "套磁邮件状态.json")
                           .read_text(encoding="utf-8"))
        recorded = state["emails"][self.choices()["email_id"]]["contact_evidence"]
        self.assertEqual(recorded["status"], "escalate")
        self.assertEqual(recorded["reason_code"], "contact_evidence_stale")
        self.assertTrue(recorded["web_lookup_required"])
        self.assertIsNone(recorded["evidence_email"])

    def test_finalize_rejects_override_of_confirmed_evidence(self):
        g1 = self.prepare()
        self.write_artifact()
        self.compile_pack()
        verify_path = self.prof_dir / "_contact_verify.json"
        verify = json.loads(verify_path.read_text(encoding="utf-8"))
        verify["items"]["email"]["value"] = "user-overridden@example.test"
        verify_path.write_text(json.dumps(verify, ensure_ascii=False, indent=1),
                               encoding="utf-8")
        out = self.run_finalize_flow(g1, "mismatch")
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "contact_evidence_mismatch")


if __name__ == "__main__":
    unittest.main(verbosity=2)
