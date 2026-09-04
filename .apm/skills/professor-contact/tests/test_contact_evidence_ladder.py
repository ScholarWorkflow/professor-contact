import importlib.util
import json
import os
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

spec_state = importlib.util.spec_from_file_location(
    "contact_state_module", HERE.parent / "scripts" / "contact_state.py")
contact_state = importlib.util.module_from_spec(spec_state)
sys.modules[spec_state.name] = contact_state
spec_state.loader.exec_module(contact_state)

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


def zulu_ts():
    """Timestamp format the verify-cache TTL parser accepts (...Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


CHECKER_SCRIPT = "contact_evidence.py"
# Runtime skill-locator injection: the upstream checker is resolved OUTSIDE
# program_root (program roots hold user data only — never .apm/skills).
CHECKER_ENV = "PROFESSOR_CONTACT_EVIDENCE_SCRIPT"
# Deterministic stand-in for professor-research's local contact_evidence.py:
# `--check` prints the fixture's per-professor freshness report; the rebuild
# form rewrites the artifact from the fixture and swaps in the post-rebuild
# report, mirroring the idempotent local rebuild contract (professor-research
# #19). `rebuild_error` simulates a failing rebuild command.
CHECKER_STUB = """\
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
fixture = json.loads((root / "教授研究" / "_check_fixture.json").read_text(encoding="utf-8"))
if "--check" in sys.argv:
    if fixture.get("check_error"):
        sys.exit(4)
    print(json.dumps(fixture["check"], ensure_ascii=False))
else:
    if fixture.get("rebuild_error"):
        sys.exit(3)
    rebuilt = fixture.get("rebuild_artifact")
    if rebuilt is not None:
        (root / "教授研究" / "_联系方式证据.json").write_text(
            json.dumps(rebuilt, ensure_ascii=False, indent=1), encoding="utf-8")
    if fixture.get("post_rebuild_check") is not None:
        (root / "教授研究" / "_check_fixture.json").write_text(
            json.dumps({"check": fixture["post_rebuild_check"]}, ensure_ascii=False),
            encoding="utf-8")
    print(json.dumps({"result": "ok",
                      "action": "written" if rebuilt is not None else "unchanged"},
                     ensure_ascii=False))
"""


class TestContactEvidenceLadder(BaseEnv):
    prepare = TestStage5.prepare
    raw_result = TestStage5.raw_result
    choices = TestStage5.choices

    def setUp(self):
        super().setUp()
        # Pin the checker locator to a missing path so tests are hermetic:
        # the real sibling/installed-skill layout of the machine running the
        # tests must never leak into expectations. write_checker() re-points
        # it at a stub kept OUTSIDE the program root.
        self._saved_checker_env = os.environ.get(CHECKER_ENV)
        os.environ[CHECKER_ENV] = str(self.root / "missing-checker.py")

    def tearDown(self):
        if self._saved_checker_env is None:
            os.environ.pop(CHECKER_ENV, None)
        else:
            os.environ[CHECKER_ENV] = self._saved_checker_env
        super().tearDown()

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

    def compile_pack_two_professors(self, second_professor="佐藤 花子"):
        """Compile a pack with a second target professor whose stage-3
        state/pack is copied from the primary one."""
        second_dir = self.root / "教授研究" / "Y分野" / second_professor
        second_dir.mkdir(parents=True, exist_ok=True)
        for name in ("套磁候选状态.json", "套磁候选输入.json"):
            data = json.loads((self.prof_dir / name).read_text(encoding="utf-8"))
            if name == "套磁候选输入.json":
                data["professor"] = second_professor
                data["professor_dir"] = str(second_dir)
            (second_dir / name).write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        sel_input = self.root / "sel_input.json"
        sel_input.write_text(json.dumps({"selections": [
            {"professor": "試験 教授", "professor_dir": str(self.prof_dir),
             "collection_key": "DIR00001", "ideas": [{"id": "DIR00001_1"}]},
            {"professor": second_professor, "professor_dir": str(second_dir),
             "collection_key": "DIR00001", "ideas": [{"id": "DIR00001_1"}]},
        ]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage4-finalize", "--program-root", self.root,
                            "--selection-input", sel_input))
        self.assertEqual(out["status"], "ok", out)
        return second_dir

    def write_checker(self, check, rebuild_artifact=None, post_rebuild_check=None,
                      rebuild_error=False, check_error=False):
        """Install the deterministic upstream checker stub via the runtime
        skill locator. The stub lives OUTSIDE the program root: a real
        program root holds only user data (info.json / 教授研究/), never the
        installed skill tree."""
        self.checker_root = Path(str(self.temp.name) + "-checker")
        script_dir = self.checker_root / "skills" / "professor-collector" / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        (script_dir / CHECKER_SCRIPT).write_text(CHECKER_STUB, encoding="utf-8")
        os.environ[CHECKER_ENV] = str(script_dir / CHECKER_SCRIPT)
        fixture = {"check": check, "rebuild_artifact": rebuild_artifact,
                   "post_rebuild_check": post_rebuild_check,
                   "rebuild_error": rebuild_error, "check_error": check_error}
        (self.root / "教授研究" / "_check_fixture.json").write_text(
            json.dumps(fixture, ensure_ascii=False, indent=1), encoding="utf-8")

    def check_report(self, result, reasons=None, professors=None):
        """A --check report shaped like professor-research #19's output: the
        overall result aggregates the per-professor entries."""
        entries = professors if professors is not None else [
            {"name": "試験 教授", "result": result, "reasons": reasons or []}]
        if any(e["result"] == "unavailable" for e in entries):
            overall = "unavailable"
        elif any(e["result"] == "stale" for e in entries):
            overall = "stale"
        else:
            overall = "fresh"
        return {"result": overall,
                "reasons": sorted({r for e in entries for r in e["reasons"]}),
                "professors": entries}

    def schema2_record(self, overrides=None):
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
            "evidence_status": {
                "official_candidates_unavailable": False,
                "professor_papers_unavailable": False,
                "paper_correspondence_unavailable": False,
                "signature_aliases_unavailable": False,
                "current_email_blocked_by": []},
        }
        record.update(overrides or {})
        return record

    def write_schema2_artifact(self, professors=None, overrides=None):
        artifact = {
            "schema": 2, "kind": "professor-contact-evidence",
            "generated_at": fresh_ts(),
            "recent_paper_years": 5, "current_year": 2026,
            "scope": "workflow_evidence_not_send_time_authority",
            "sources": {}, "degraded": False, "global_degraded": False,
            "source_errors": [],
            "source_fingerprints": {"algorithm": "sha256", "files": []},
            "professors": professors if professors is not None
            else [self.schema2_record()]}
        artifact.update(overrides or {})
        path = self.root / EVIDENCE_FILE
        path.write_text(json.dumps(artifact, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        return artifact

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

    def test_plan_escalates_when_this_record_evidence_is_unavailable(self):
        self.prepare()
        self.write_artifact(record_overrides={
            "verdict": "official_only", "confirmed_emails": [],
            "paper_correspondence": [], "current_email": None,
            "evidence_status": {
                "official_candidates_unavailable": False,
                "professor_papers_unavailable": True,
                "paper_correspondence_unavailable": False,
                "signature_aliases_unavailable": False,
                "current_email_blocked_by": ["professor_papers_unavailable"]}},
            artifact_overrides={
                "degraded": True,
                "source_errors": [{"source": "papers_json", "scope": "professor",
                                   "path": "研究領域A/試験 教授/papers.json",
                                   "error": "malformed JSON"}]})
        self.compile_pack()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_artifact_degraded")
        self.assertTrue(decision["web_lookup_required"])
        self.assertIsNone(decision["recipient_email"])

    def test_plan_scopes_degradation_to_the_affected_record(self):
        # Issue-#14 acceptance: professor B's malformed papers.json degrades only
        # B's record; professor A stays usable without web escalation.
        self.prepare()
        good_status = {"official_candidates_unavailable": False,
                       "professor_papers_unavailable": False,
                       "paper_correspondence_unavailable": False,
                       "signature_aliases_unavailable": False,
                       "current_email_blocked_by": []}
        record = self.write_artifact(record_overrides={
            "evidence_status": dict(good_status)})
        broken = dict(record)
        broken["professor"] = {"name": "佐藤 花子", "name_romaji": None}
        broken["verdict"] = "official_only"
        broken["confirmed_emails"] = []
        broken["current_email"] = None
        broken["evidence_status"] = {
            "official_candidates_unavailable": False,
            "professor_papers_unavailable": True,
            "paper_correspondence_unavailable": False,
            "signature_aliases_unavailable": False,
            "current_email_blocked_by": ["professor_papers_unavailable"]}
        self.write_artifact(record_overrides={"evidence_status": dict(good_status)},
                            artifact_overrides={
                                "degraded": True,
                                "source_errors": [{
                                    "source": "papers_json", "scope": "professor",
                                    "path": "研究領域B/佐藤花子/papers.json",
                                    "error": "malformed JSON"}],
                                "professors": [record, broken]})
        entry = self.compile_pack()
        snapshot = entry["contact_evidence"]
        self.assertIsNotNone(snapshot)
        self.assertFalse(snapshot["degraded"])
        self.assertEqual(snapshot["evidence_status"], good_status)
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "confirmed_cross_source")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "faculty@example.test")
        # The same artifact still escalates the professor it actually concerns.
        artifact = json.loads((self.root / EVIDENCE_FILE).read_text(encoding="utf-8"))
        broken_decision = contact_state.evaluate_contact_evidence(
            "佐藤 花子", None, artifact, None, checker_error="script_missing")
        self.assertEqual(broken_decision["status"], "escalate")
        self.assertEqual(broken_decision["reason_code"],
                         "contact_evidence_artifact_degraded")
        self.assertTrue(broken_decision["web_lookup_required"])

    def test_plan_keeps_official_only_usable_when_correspondence_unavailable(self):
        # Issue-#14 family scoping: an unreadable correspondence cache removes
        # paper-side confirmation but not a single valid official address, so
        # upstream keeps current_email with current_email_blocked_by empty and
        # the record must be accepted instead of forced to web lookup.
        self.prepare()
        self.write_artifact({
            "verdict": "official_only", "confirmed_emails": [],
            "paper_correspondence": [],
            "evidence_status": {
                "official_candidates_unavailable": False,
                "professor_papers_unavailable": False,
                "paper_correspondence_unavailable": True,
                "signature_aliases_unavailable": False,
                "current_email_blocked_by": []}},
            artifact_overrides={
                "degraded": True, "global_degraded": True,
                "source_errors": [{"source": "paper_correspondence",
                                   "scope": "global",
                                   "path": "_corresp_cache.json",
                                   "error": "malformed JSON"}]})
        entry = self.compile_pack()
        self.assertFalse(entry["contact_evidence"]["degraded"])
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "official_only")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "faculty@example.test")
        self.assertTrue(decision["single_source"])

    def test_plan_keeps_direct_evidence_usable_when_signature_book_unavailable(self):
        # Issue-#14 family scoping: an unreadable signature book only removes
        # alias matching; verified contacts that resolved directly (and a
        # decision not blocked upstream) keep the record usable.
        self.prepare()
        self.write_artifact({
            "evidence_status": {
                "official_candidates_unavailable": False,
                "professor_papers_unavailable": False,
                "paper_correspondence_unavailable": False,
                "signature_aliases_unavailable": True,
                "current_email_blocked_by": []}},
            artifact_overrides={
                "degraded": True, "global_degraded": True,
                "source_errors": [{"source": "signature_book", "scope": "global",
                                   "path": "_署名对照.json",
                                   "error": "malformed JSON"}]})
        self.compile_pack()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "confirmed_cross_source")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "faculty@example.test")

    def test_plan_escalates_when_signature_aliases_block_promotion(self):
        # An unreadable signature book with unresolved verified contacts blocks
        # promotion upstream (a readable alias book could have matched the
        # contact at a conflicting address); the non-empty
        # current_email_blocked_by is what escalates here.
        self.prepare()
        self.write_artifact({
            "verdict": "official_only", "confirmed_emails": [],
            "paper_correspondence": [], "current_email": None,
            "identity": {"matched_verified_contacts": 0,
                         "unmatched_verified_contacts": [
                             {"email": "other@example.test"}],
                         "ambiguous_unpaired_records_ignored": 0},
            "evidence_status": {
                "official_candidates_unavailable": False,
                "professor_papers_unavailable": False,
                "paper_correspondence_unavailable": False,
                "signature_aliases_unavailable": True,
                "current_email_blocked_by": ["signature_aliases_unavailable"]}},
            artifact_overrides={
                "degraded": True, "global_degraded": True,
                "source_errors": [{"source": "signature_book", "scope": "global",
                                   "path": "_署名对照.json",
                                   "error": "malformed JSON"}]})
        self.compile_pack()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"],
                         "contact_evidence_artifact_degraded")
        self.assertTrue(decision["web_lookup_required"])
        self.assertIsNone(decision["recipient_email"])

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

    def test_plan_escalates_when_freshness_cannot_be_confirmed(self):
        self.prepare()
        for bad_timestamp in (None, "", "not-a-date"):
            self.write_artifact(artifact_overrides={"generated_at": bad_timestamp})
            decision = self.decision(self.plan_jobs())
            self.assertEqual(decision["status"], "escalate", bad_timestamp)
            self.assertEqual(decision["reason_code"],
                             "contact_evidence_timestamp_invalid", bad_timestamp)
            self.assertTrue(decision["web_lookup_required"])

    def test_plan_never_accepts_pack_snapshot_when_artifact_file_absent(self):
        # The pack snapshot is an audit/portability input, never a live
        # freshness authority: with the artifact file gone the snapshot cannot
        # be consumed regardless of its embedded timestamp.
        self.prepare()
        self.write_artifact()
        self.compile_pack()
        (self.root / EVIDENCE_FILE).unlink()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_missing")
        self.assertTrue(decision["web_lookup_required"])
        self.assertIsNone(decision["recipient_email"])

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
        # A ladder/legacy-verified cache (no contact_evidence sources) keeps
        # its own TTL and generation proceeds; the escalation is recorded.
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

    EVIDENCE_SEED_SOURCES = [{"level": "contact_evidence",
                              "note": "confirmed_cross_source｜官方+近期高置信论文通讯一致"}]
    LADDER_SOURCES = [{"level": 3, "url": "https://example.test/faculty",
                       "note": "官方教员主页"}]

    def seed_verify_email(self, sources, value=None):
        verify_path = self.prof_dir / "_contact_verify.json"
        verify = json.loads(verify_path.read_text(encoding="utf-8"))
        verify["verified_at"] = zulu_ts()
        verify["items"]["email"]["sources"] = sources
        if value is not None:
            verify["items"]["email"]["value"] = value
        verify_path.write_text(json.dumps(verify, ensure_ascii=False, indent=1),
                               encoding="utf-8")

    def test_fresh_evidence_seeded_cache_is_accepted(self):
        g1 = self.prepare()
        self.write_artifact()
        self.compile_pack()
        self.seed_verify_email(self.EVIDENCE_SEED_SOURCES)
        out = self.run_finalize_flow(g1, "seed-fresh")
        self.assertEqual(out["status"], "ok", out)
        state = json.loads((self.prof_dir / "套磁邮件状态.json")
                           .read_text(encoding="utf-8"))
        recorded = state["emails"][self.choices()["email_id"]]["contact_evidence"]
        self.assertEqual(recorded["status"], "confirmed_cross_source")
        self.assertEqual(recorded["chosen_email"], "faculty@example.test")

    def test_stale_evidence_invalidates_seeded_cache_until_reverified(self):
        g1 = self.prepare()
        self.write_artifact()
        self.compile_pack()
        self.seed_verify_email(self.EVIDENCE_SEED_SOURCES)
        self.write_artifact(artifact_overrides={"generated_at": stale_ts()})
        plan = self.plan_jobs()
        self.assertEqual(self.decision(plan)["reason_code"], "contact_evidence_stale")
        self.assertEqual(plan["verify"]["試験 教授"],
                         "needs_recheck:contact_evidence_escalated")
        self.assertIn("試験 教授", plan["needs_recheck_professors"])
        out = self.run_finalize_flow(g1, "seed-stale")
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "verify_contact_evidence_escalated")
        self.assertFalse((self.prof_dir / "套磁邮件.md").exists())

    def test_ladder_reverification_after_escalation_unblocks_finalize(self):
        g1 = self.prepare()
        self.write_artifact(artifact_overrides={"generated_at": stale_ts()})
        self.compile_pack()
        self.seed_verify_email(self.LADDER_SOURCES)
        out = self.run_finalize_flow(g1, "seed-reverified")
        self.assertEqual(out["status"], "ok", out)
        state = json.loads((self.prof_dir / "套磁邮件状态.json")
                           .read_text(encoding="utf-8"))
        recorded = state["emails"][self.choices()["email_id"]]["contact_evidence"]
        self.assertEqual(recorded["status"], "escalate")
        self.assertEqual(recorded["reason_code"], "contact_evidence_stale")
        self.assertEqual(recorded["chosen_email"], "faculty@example.test")
        self.assertTrue(recorded["web_lookup_required"])

    def test_finalize_rejects_override_of_confirmed_evidence(self):
        # A hand-edited cache address conflicting with an accepted evidence
        # decision is surfaced deterministically at plan/finalize time (the
        # generic verify conflict), never discovered only at the last
        # mismatch guard — and nothing is written before it is resolved.
        g1 = self.prepare()
        self.write_artifact()
        self.compile_pack()
        verify_path = self.prof_dir / "_contact_verify.json"
        verify = json.loads(verify_path.read_text(encoding="utf-8"))
        verify["items"]["email"]["value"] = "user-overridden@example.test"
        verify_path.write_text(json.dumps(verify, ensure_ascii=False, indent=1),
                               encoding="utf-8")
        plan = self.plan_jobs()
        self.assertEqual(plan["verify"]["試験 教授"],
                         "needs_recheck:contact_evidence_verify_conflict")
        out = self.run_finalize_flow(g1, "mismatch")
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "verify_contact_evidence_verify_conflict")
        self.assertFalse((self.prof_dir / "套磁邮件.md").exists())

    def test_fresh_independent_verify_cache_conflict_is_detected_before_generation(self):
        # Review blocker (PR #14 re-review): a fresh independent ladder/user
        # verification is the send-time authority; when fresh accepted
        # contact evidence names a DIFFERENT address, stage5-plan must expose
        # the conflict deterministically before any generation — verify must
        # not be ok + accepted evidence, and the agent must never silently
        # reseed over the independent verification.
        g1 = self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        self.seed_verify_email(self.LADDER_SOURCES, value="faculty-b@example.test")
        self.write_checker(self.check_report("fresh"))
        plan = self.plan_jobs()
        decision = self.decision(plan)
        self.assertEqual(decision["status"], "confirmed_cross_source")
        self.assertEqual(decision["recipient_email"], "faculty@example.test")
        self.assertEqual(plan["verify"]["試験 教授"],
                         "needs_recheck:contact_evidence_verify_conflict")
        self.assertIn("試験 教授", plan["needs_recheck_professors"])
        out = self.run_finalize_flow(g1, "independent-conflict")
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "verify_contact_evidence_verify_conflict")
        self.assertFalse((self.prof_dir / "套磁邮件.md").exists())

    def test_same_address_independent_verify_cache_is_reused_without_recheck(self):
        # Same address: an independent web/user verification in its own TTL
        # is directly reusable — no forced re-web, no conflict.
        g1 = self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        self.seed_verify_email(self.LADDER_SOURCES, value="faculty@example.test")
        self.write_checker(self.check_report("fresh"))
        plan = self.plan_jobs()
        self.assertEqual(plan["verify"]["試験 教授"], "ok")
        self.assertNotIn("試験 教授", plan["needs_recheck_professors"])
        out = self.run_finalize_flow(g1, "independent-same")
        self.assertEqual(out["status"], "ok", out)

    def test_schema2_checker_is_resolved_outside_program_root(self):
        # Review blocker (PR #14 re-review): a real program root holds only
        # user data (info.json / 教授研究/) and NEVER the installed skill
        # tree; the upstream checker must be resolved via the skill locator
        # relative to this runner's own install instead. A schema-2 artifact
        # must be consumed through that locator, not degraded to
        # contact_evidence_check_unavailable.
        self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        self.write_checker(self.check_report("fresh"))
        self.assertFalse((self.root / ".apm").exists(),
                         "program root must not contain the skill tree")
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "confirmed_cross_source")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "faculty@example.test")

    def test_missing_injected_checker_fails_closed(self):
        # An explicit locator injection pointing at a missing file is
        # authoritative — fail closed instead of silently falling back to
        # machine-layout guessing.
        self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"],
                         "contact_evidence_check_unavailable")

    # --- live source-state freshness (professor-research schema-2 contract,
    #     final cross-repo acceptance criteria in PR #14 comment 5540723034) ---

    def test_schema2_artifact_is_accepted_without_reintroducing_global_degradation(self):
        # Review comment 5537970288, verbatim regression: a schema-2 artifact
        # is a legitimate upstream input (never invalid_artifact), and the
        # artifact-level degraded/global_degraded flags must not override the
        # per-record current_email_blocked_by semantics for this professor.
        self.prepare()
        self.write_artifact(
            record_overrides={
                "evidence_status": {
                    "official_candidates_unavailable": False,
                    "professor_papers_unavailable": False,
                    "paper_correspondence_unavailable": True,
                    "signature_aliases_unavailable": False,
                    "current_email_blocked_by": [],
                },
            },
            artifact_overrides={
                "schema": 2,
                "degraded": True,
                "global_degraded": True,
                "source_errors": [{
                    "source": "paper_correspondence",
                    "scope": "global",
                    "path": "_corresp_cache.json",
                    "error": "malformed JSON",
                }],
                "source_fingerprints": {
                    "algorithm": "sha256",
                    "files": [{
                        "source": "paper_correspondence",
                        "path": "_corresp_cache.json",
                        "present": True,
                        "sha256": None,
                        "bytes": None,
                        "error": "unreadable: malformed JSON",
                    }],
                },
            },
        )
        self.write_checker(self.check_report("fresh"))
        entry = self.compile_pack()
        snapshot = entry["contact_evidence"]
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["record"]["verdict"], "confirmed_cross_source")
        self.assertFalse(snapshot["degraded"])

        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "confirmed_cross_source")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "faculty@example.test")

    def test_fresh_source_state_still_escalates_blocked_current_email(self):
        # fresh per-professor source-state only unlocks the live record; a
        # record whose current_email decision was blocked upstream
        # (current_email_blocked_by non-empty) still escalates.
        self.prepare()
        self.write_schema2_artifact(overrides={"professors": [self.schema2_record({
            "current_email": None,
            "evidence_status": {
                "official_candidates_unavailable": False,
                "professor_papers_unavailable": True,
                "paper_correspondence_unavailable": False,
                "signature_aliases_unavailable": False,
                "current_email_blocked_by": ["professor_papers_unavailable"]}})]})
        self.compile_pack()
        self.write_checker(self.check_report("fresh"))
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"],
                         "contact_evidence_artifact_degraded")
        self.assertTrue(decision["web_lookup_required"])
        self.assertIsNone(decision["recipient_email"])

    def test_stale_source_state_rebuilds_instead_of_trusting_fresh_timestamp(self):
        # Regression 2: live source fingerprints stale while generated_at is
        # still inside the 30-day window — Stage 5 must run the deterministic
        # local rebuild/re-check and consume the rebuilt record, never accept
        # the timestamp-fresh old snapshot or the pre-rebuild artifact.
        self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        rebuilt_record = self.schema2_record({
            "verdict": "official_only", "confirmed_emails": [],
            "paper_correspondence": [], "current_email": "office@example.test",
            "official_emails": [{
                "email": "office@example.test", "current_source": True,
                "provenance": [{"source_type": "official_professor_candidate",
                                "source": "recruitment-faculty-list"}]}]})
        rebuilt_artifact = {
            "schema": 2, "kind": "professor-contact-evidence",
            "generated_at": fresh_ts(),
            "recent_paper_years": 5, "current_year": 2026,
            "scope": "workflow_evidence_not_send_time_authority",
            "sources": {}, "degraded": False, "global_degraded": False,
            "source_errors": [],
            "source_fingerprints": {"algorithm": "sha256", "files": []},
            "professors": [rebuilt_record]}
        self.write_checker(
            self.check_report(
                "stale", reasons=["source_changed:papers_json:教授研究/X分野/試験 教授/papers.json"]),
            rebuild_artifact=rebuilt_artifact,
            post_rebuild_check=self.check_report("fresh"))
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "official_only")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "office@example.test")
        self.assertTrue(decision["snapshot_stale"])

    def test_unreadable_correspondence_rebuild_resolves_official_only(self):
        # Regression 3 + professor-research #19 rebuild-first scenario: a newly
        # unreadable _corresp_cache.json reports stale, the local rebuild keeps
        # the single official address usable (artifact degraded), and Stage 5
        # must accept it instead of entering the web ladder.
        self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        rebuilt_record = self.schema2_record({
            "verdict": "official_only", "confirmed_emails": [],
            "paper_correspondence": [], "current_email": "office@example.test",
            "official_emails": [{
                "email": "office@example.test", "current_source": True,
                "provenance": [{"source_type": "official_professor_candidate",
                                "source": "recruitment-faculty-list"}]}]})
        rebuilt_artifact = {
            "schema": 2, "kind": "professor-contact-evidence",
            "generated_at": fresh_ts(),
            "recent_paper_years": 5, "current_year": 2026,
            "scope": "workflow_evidence_not_send_time_authority",
            "sources": {},
            "degraded": True, "global_degraded": True,
            "source_errors": [{"source": "paper_correspondence", "scope": "global",
                               "path": "_corresp_cache.json", "error": "malformed JSON"}],
            "source_fingerprints": {"algorithm": "sha256", "files": []},
            "professors": [rebuilt_record]}
        self.write_checker(
            self.check_report(
                "stale", reasons=["source_unreadable:paper_correspondence:_corresp_cache.json"]),
            rebuild_artifact=rebuilt_artifact,
            post_rebuild_check=self.check_report("fresh"))
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "official_only")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "office@example.test")

    def test_stale_rebuild_still_conflict_escalates_to_web(self):
        # Regression 4: only when the rebuilt + rechecked evidence is still
        # conflict does the web ladder enter the picture.
        self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        conflict_record = self.schema2_record({
            "verdict": "conflict", "confirmed_emails": [],
            "current_email": None,
            "conflicting_paper_emails": ["old-affiliation@example.test"],
            "paper_correspondence": [{
                "email": "old-affiliation@example.test", "name": "試験 教授",
                "item_key": "AAAA1111", "doi": None, "paper_year": 2018,
                "channel": "correspondence", "confidence": "high",
                "identity_match": "direct", "recent": False,
                "current_email_evidence": False}]})
        rebuilt_artifact = {
            "schema": 2, "kind": "professor-contact-evidence",
            "generated_at": fresh_ts(),
            "recent_paper_years": 5, "current_year": 2026,
            "scope": "workflow_evidence_not_send_time_authority",
            "sources": {}, "degraded": False, "global_degraded": False,
            "source_errors": [],
            "source_fingerprints": {"algorithm": "sha256", "files": []},
            "professors": [conflict_record]}
        self.write_checker(
            self.check_report(
                "stale", reasons=["source_changed:paper_correspondence:_corresp_cache.json"]),
            rebuild_artifact=rebuilt_artifact,
            post_rebuild_check=self.check_report("fresh"))
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_conflict")
        self.assertTrue(decision["web_lookup_required"])
        self.assertIsNone(decision["recipient_email"])

    def test_unavailable_professor_escalates_without_blocking_fresh_target(self):
        # Regression 5: per-professor scoping — an unavailable professor B
        # (universal blocker) must not degrade the fresh target professor A,
        # and the aggregated top-level result is never consulted directly.
        self.prepare()
        self.compile_pack_two_professors()
        fresh_record = self.schema2_record()
        blocked_record = self.schema2_record({
            "professor": {"name": "佐藤 花子", "name_romaji": None},
            "verdict": "official_only", "confirmed_emails": [],
            "current_email": None,
            "evidence_status": {
                "official_candidates_unavailable": False,
                "professor_papers_unavailable": True,
                "paper_correspondence_unavailable": False,
                "signature_aliases_unavailable": False,
                "current_email_blocked_by": ["professor_papers_unavailable"]}})
        self.write_schema2_artifact(professors=[fresh_record, blocked_record])
        self.write_checker(self.check_report(
            "unavailable",
            professors=[
                {"name": "試験 教授", "result": "fresh", "reasons": []},
                {"name": "佐藤 花子", "result": "unavailable",
                 "reasons": ["source_unreadable:papers_json:教授研究/Y分野/佐藤 花子/papers.json"]},
            ]))
        plan = self.plan_jobs()
        fresh_decision = plan["contact_evidence"]["試験 教授"]
        self.assertEqual(fresh_decision["status"], "confirmed_cross_source")
        self.assertIsNone(fresh_decision["reason_code"])
        self.assertFalse(fresh_decision["web_lookup_required"])
        unavailable_decision = plan["contact_evidence"]["佐藤 花子"]
        self.assertEqual(unavailable_decision["status"], "escalate")
        self.assertEqual(unavailable_decision["reason_code"],
                         "contact_evidence_source_unavailable")
        self.assertTrue(unavailable_decision["web_lookup_required"])
        self.assertIsNone(unavailable_decision["recipient_email"])

    def test_artifact_missing_pack_snapshot_never_carries_the_decision(self):
        # Regression 6: without the live artifact the pack snapshot proves
        # nothing — no checker installed means the decision escalates; with
        # the checker installed the deterministic rebuild re-establishes live
        # evidence and the rebuilt record (not the snapshot) is consumed.
        self.prepare()
        self.write_artifact()
        self.compile_pack()
        (self.root / EVIDENCE_FILE).unlink()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_missing")
        self.assertTrue(decision["web_lookup_required"])
        rebuilt_record = self.schema2_record({
            "verdict": "official_only", "confirmed_emails": [],
            "paper_correspondence": [], "current_email": "office@example.test",
            "official_emails": [{
                "email": "office@example.test", "current_source": True,
                "provenance": [{"source_type": "official_professor_candidate",
                                "source": "recruitment-faculty-list"}]}]})
        rebuilt_artifact = {
            "schema": 2, "kind": "professor-contact-evidence",
            "generated_at": fresh_ts(),
            "recent_paper_years": 5, "current_year": 2026,
            "scope": "workflow_evidence_not_send_time_authority",
            "sources": {}, "degraded": False, "global_degraded": False,
            "source_errors": [],
            "source_fingerprints": {"algorithm": "sha256", "files": []},
            "professors": [rebuilt_record]}
        self.write_checker(
            {"result": "unavailable", "reasons": ["artifact_missing"]},
            rebuild_artifact=rebuilt_artifact,
            post_rebuild_check=self.check_report("fresh"))
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "official_only")
        self.assertIsNone(decision["reason_code"])
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "office@example.test")
        self.assertTrue(decision["snapshot_stale"])

    def test_legacy_schema_artifact_migrates_through_deterministic_rebuild(self):
        # Transitional reader keeps accepting schema-1, but once the upstream
        # checker is installed a legacy artifact has no fingerprint contract —
        # the rebuild migrates it to schema-2 and the live record is consumed.
        self.prepare()
        self.write_artifact()
        self.compile_pack()
        rebuilt_record = self.schema2_record()
        rebuilt_artifact = {
            "schema": 2, "kind": "professor-contact-evidence",
            "generated_at": fresh_ts(),
            "recent_paper_years": 5, "current_year": 2026,
            "scope": "workflow_evidence_not_send_time_authority",
            "sources": {}, "degraded": False, "global_degraded": False,
            "source_errors": [],
            "source_fingerprints": {"algorithm": "sha256", "files": []},
            "professors": [rebuilt_record]}
        self.write_checker(
            {"result": "unavailable", "reasons": ["artifact_legacy_schema"]},
            rebuild_artifact=rebuilt_artifact,
            post_rebuild_check=self.check_report("fresh"))
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "confirmed_cross_source")
        self.assertFalse(decision["web_lookup_required"])
        self.assertEqual(decision["recipient_email"], "faculty@example.test")

    def test_failed_rebuild_keeps_web_escalation(self):
        # Rebuild-first is only an alternative to web when it actually runs:
        # a failing rebuild command leaves the stale source-state in place and
        # the decision escalates to the existing web ladder.
        self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        self.write_checker(
            self.check_report(
                "stale", reasons=["source_changed:paper_correspondence:_corresp_cache.json"]),
            rebuild_error=True)
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"], "contact_evidence_rebuild_failed")
        self.assertTrue(decision["web_lookup_required"])
        self.assertIsNone(decision["recipient_email"])

    def test_schema2_artifact_without_checker_fails_closed(self):
        # A schema-2 artifact's freshness lives in its source fingerprints;
        # without the upstream checker installed it cannot be confirmed live,
        # so the decision fails closed instead of trusting generated_at.
        self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"],
                         "contact_evidence_check_unavailable")
        self.assertTrue(decision["web_lookup_required"])
        self.assertIsNone(decision["recipient_email"])

    def test_failing_checker_fails_closed(self):
        # A broken checker (non-zero exit) also means live source-state
        # freshness is unconfirmable — fail closed, never seed confirmed.
        self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        self.write_checker(self.check_report("fresh"), check_error=True)
        decision = self.decision(self.plan_jobs())
        self.assertEqual(decision["status"], "escalate")
        self.assertEqual(decision["reason_code"],
                         "contact_evidence_check_unavailable")
        self.assertTrue(decision["web_lookup_required"])

    def test_seeded_verify_cache_cannot_bypass_source_state_gate(self):
        # Regression 7: a contact-evidence-seeded verify cache must be
        # invalidated when the live source-state goes stale — even while the
        # cache TTL is still running — so plan demands a re-check and finalize
        # refuses to write the email before re-verification.
        g1 = self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        self.seed_verify_email(self.EVIDENCE_SEED_SOURCES)
        self.write_checker(
            self.check_report(
                "stale", reasons=["source_changed:paper_correspondence:_corresp_cache.json"]),
            rebuild_error=True)
        plan = self.plan_jobs()
        self.assertEqual(self.decision(plan)["reason_code"],
                         "contact_evidence_rebuild_failed")
        self.assertEqual(plan["verify"]["試験 教授"],
                         "needs_recheck:contact_evidence_escalated")
        self.assertIn("試験 教授", plan["needs_recheck_professors"])
        out = self.run_finalize_flow(g1, "seed-source-stale")
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "verify_contact_evidence_escalated")
        self.assertFalse((self.prof_dir / "套磁邮件.md").exists())

    def test_independently_verified_cache_survives_unrelated_source_stale(self):
        # Regression 7 (second half): a cache provenance that went through the
        # faculty/lab web ladder or user confirmation keeps its own TTL and is
        # not force-invalidated by unrelated contact-evidence staleness.
        g1 = self.prepare()
        self.write_schema2_artifact()
        self.compile_pack()
        self.seed_verify_email(self.LADDER_SOURCES)
        self.write_checker(
            self.check_report(
                "stale", reasons=["source_changed:paper_correspondence:_corresp_cache.json"]),
            rebuild_error=True)
        out = self.run_finalize_flow(g1, "ladder-source-stale")
        self.assertEqual(out["status"], "ok", out)
        state = json.loads((self.prof_dir / "套磁邮件状态.json")
                           .read_text(encoding="utf-8"))
        recorded = state["emails"][self.choices()["email_id"]]["contact_evidence"]
        self.assertEqual(recorded["status"], "escalate")
        self.assertEqual(recorded["reason_code"], "contact_evidence_rebuild_failed")
        self.assertEqual(recorded["chosen_email"], "faculty@example.test")
        self.assertTrue(recorded["web_lookup_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
