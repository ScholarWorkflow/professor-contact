#!/usr/bin/env python3
"""Upstream contact-evidence location, check and rebuild for ``contact_state.py``.

The runner loads this helper by path **from the same directory**, which keeps
``upstream_check_script``'s ``Path(__file__).resolve().parents`` resolution
chain byte-for-byte identical to the pre-split runner. Moving this file to
another directory would silently change that chain.

Two runner helpers are injected explicitly instead of being copied here:
``read_json_file`` and ``compact_name``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


CONTACT_EVIDENCE_FILE = "_联系方式证据.json"
CONTACT_EVIDENCE_KIND = "professor-contact-evidence"
CONTACT_EVIDENCE_SCHEMAS = (1, 2)

# professor-research schema-2 freshness interface (local-only): the stable
# per-professor `--check` report and the idempotent deterministic rebuild.
# The script lives in the professor-research SKILL installation — never in a
# program root, which holds only user data (info.json / 教授研究/).
UPSTREAM_REPO_ID = "professor-research"
UPSTREAM_SKILL_ID = "professor-collector"
UPSTREAM_CHECK_RESOURCE = Path(".apm") / "skills" / "professor-collector" / \
    "scripts" / "contact_evidence.py"
UPSTREAM_SCRIPT_ENV = "PROFESSOR_CONTACT_EVIDENCE_SCRIPT"
UPSTREAM_CHECK_TIMEOUT_SECONDS = 60

def load_contact_evidence(program_root: Path, *, read_json_file) -> tuple[dict | None, str | None]:
    """Read the upstream reconciled artifact; absence is absence of evidence.

    The transitional reader accepts the legacy schema-1 layout alongside the
    schema-2 fingerprint contract (review comment 5537970288); whether a
    schema-2 artifact is *fresh* is decided by the upstream `--check`
    interface, never by this reader.
    """
    path = program_root / "教授研究" / CONTACT_EVIDENCE_FILE
    data, error = read_json_file(path)
    if error == "not_found":
        return None, None
    if error:
        return None, "unreadable"
    if (not isinstance(data, dict) or
            data.get("schema") not in CONTACT_EVIDENCE_SCHEMAS or
            data.get("kind") != CONTACT_EVIDENCE_KIND or
            not isinstance(data.get("professors"), list)):
        return None, "invalid_artifact"
    return data, None


def upstream_check_script() -> Path | None:
    """Locate professor-research's contact_evidence.py via the installed-skill
    layout — never derived from program_root (user data directory).

    Resolution order:
    1. explicit runtime locator injection via UPSTREAM_SCRIPT_ENV (an
       absolute path wins authoritatively; a missing file fails closed);
    2. the shared skills root next to this runner's own skill installation
       (checkout `.apm/skills/…` composition, or the APM shared project-scope
       install `.agents/skills/…` used for both Codex and OpenCode targets)
       holding `professor-collector/scripts/…`;
    3. a registered professor-research checkout that is a sibling of one of
       this runner's own ancestors (skillrepo canonical layout: registered
       repos sit side by side, including under a shared worktrees/ dir) —
       probed with fixed-path existence checks only, no directory scans.
    """
    injected = os.environ.get(UPSTREAM_SCRIPT_ENV, "").strip()
    if injected:
        script = Path(injected)
        return script if script.is_file() else None
    here = Path(__file__).resolve()
    parents = here.parents
    if len(parents) > 1:                                        # …/professor-contact
        candidate = (parents[1].parent / UPSTREAM_SKILL_ID /
                     "scripts" / "contact_evidence.py")
        if candidate.is_file():
            return candidate
    resource = UPSTREAM_REPO_ID / UPSTREAM_CHECK_RESOURCE
    for ancestor in list(parents)[:8]:                          # …/<checkout>/… roots
        candidate = ancestor.parent / resource
        if candidate.is_file():
            return candidate
    return None


def run_contact_evidence_check(program_root: Path) -> tuple[dict | None, str | None]:
    """professor-research's stable local freshness interface:
    `contact_evidence.py <program_root> --check` reports per-professor
    fresh/stale/unavailable from the persisted artifact's source
    fingerprints. Returns (report, None) on a valid report, or
    (None, "script_missing" | "script_failed") when live source-state
    freshness cannot be confirmed at all."""
    script = upstream_check_script()
    if script is None:
        return None, "script_missing"
    return run_upstream_check_argv([sys.executable, str(script), str(program_root), "--check"])


def run_contact_evidence_rebuild(program_root: Path) -> bool:
    """The same deterministic local rebuild the upstream contract documents
    for stale artifacts: rewrite the derived artifact from local sources
    (idempotent, local-only), then the caller re-checks."""
    script = upstream_check_script()
    if script is None:
        return False
    try:
        proc = subprocess.run(
            [sys.executable, str(script), str(program_root)],
            capture_output=True, text=True, timeout=UPSTREAM_CHECK_TIMEOUT_SECONDS)
    except (OSError, subprocess.SubprocessError):
        return False
    if proc.returncode != 0:
        return False
    try:
        parsed = json.loads(proc.stdout)
    except ValueError:
        return False
    return isinstance(parsed, dict) and parsed.get("result") == "ok"


def run_upstream_check_argv(argv: list[str]) -> tuple[dict | None, str | None]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=UPSTREAM_CHECK_TIMEOUT_SECONDS)
    except (OSError, subprocess.SubprocessError):
        return None, "script_failed"
    if proc.returncode != 0:
        return None, "script_failed"
    try:
        parsed = json.loads(proc.stdout)
    except ValueError:
        return None, "script_failed"
    if (not isinstance(parsed, dict) or
            parsed.get("result") not in ("fresh", "stale", "unavailable")):
        return None, "script_failed"
    return parsed, None


def professor_source_state(report: dict | None, professor: str, *,
                            compact_name) -> dict | None:
    """The target professor's own freshness entry from the --check report —
    never the top-level aggregate. Absence means the report attributes no
    per-professor state to them (structural artifact problem, or the
    professor has no record upstream)."""
    if not isinstance(report, dict):
        return None
    key = compact_name(professor)
    for entry in report.get("professors") or []:
        if (isinstance(entry, dict) and compact_name(entry.get("name")) == key
                and entry.get("result") in ("fresh", "stale", "unavailable")):
            return {"result": entry["result"],
                    "reasons": [r for r in entry.get("reasons") or []
                                if isinstance(r, str)]}
    return None


def source_state_needs_rebuild(state: dict | None) -> bool:
    """Rebuild-first: a stale derived artifact — or a report that cannot
    attribute any state to the professor (missing/legacy/invalid artifact) —
    is resolved by the deterministic local rebuild whenever it can be
    resolved there. An existing per-professor `unavailable` entry is a
    universal source blocker (e.g. unreadable candidates/papers.json) that
    only an upstream repair can fix, so rebuilding is pointless."""
    if state is None:
        return True
    return state["result"] == "stale"


def resolve_contact_evidence(program_root: Path, professors: list[str], *,
                              read_json_file, compact_name) -> dict:
    """Live artifact + per-professor source-state, with the rebuild-first
    contract applied once per run: while any target professor's source-state
    is not confirmably fresh and a local rebuild could resolve it, rebuild
    and re-check before any decision is made. Never a web operation."""
    artifact, artifact_error = load_contact_evidence(
        program_root, read_json_file=read_json_file)
    report, checker_error = run_contact_evidence_check(program_root)
    rebuild_ran = False
    if checker_error is None and professors:
        needs = any(source_state_needs_rebuild(professor_source_state(
            report, p, compact_name=compact_name))
                    for p in professors)
        if needs and run_contact_evidence_rebuild(program_root):
            artifact, artifact_error = load_contact_evidence(
        program_root, read_json_file=read_json_file)
            report, checker_error = run_contact_evidence_check(program_root)
            rebuild_ran = True
    return {"artifact": artifact, "artifact_error": artifact_error,
            "report": report, "checker_error": checker_error,
            "rebuild_ran": rebuild_ran}


CONTACT_EVIDENCE_SCHEMA_LIVE = 2
CONTACT_EVIDENCE_VERDICTS = ("confirmed_cross_source", "official_only",
                             "paper_only", "conflict", "insufficient")


def contact_evidence_record(artifact: dict, professor: str, *,
                            compact_name) -> dict | None:
    key = compact_name(professor)
    if not key:
        return None
    for record in artifact.get("professors", []):
        if not isinstance(record, dict):
            continue
        name = (record.get("professor") or {}).get("name")
        if name and compact_name(name) == key:
            return record
    return None


def contact_evidence_record_degraded(record: dict) -> bool:
    """Issue-#14 family-scoped degradation: was THIS record's current-email
    decision actually blocked upstream?

    Upstream keeps a record usable when its current_email rests only on
    evidence families that read successfully: an unreadable correspondence
    cache leaves a single official address usable (paper confirmation flagged
    unavailable), and an unreadable signature book only blocks promotion when
    verified contacts remained unresolved by direct identity. Gating on any()
    over the raw availability flags would re-globalize those family-scoped
    failures, so escalate on a non-empty current_email_blocked_by — upstream
    names exactly the families whose failure blocked the promotion decision.
    Artifacts from before that contract carry no evidence_status and count as
    clean here; that stays fail-closed because their producers already nulled
    current_email for every record whenever anything failed, so no degraded
    old record can pass the recipient checks in evaluate_contact_evidence.
    """
    status = record.get("evidence_status")
    if not isinstance(status, dict):
        return False
    blocked = status.get("current_email_blocked_by")
    return isinstance(blocked, list) and any(
        isinstance(family, str) and family for family in blocked)


def contact_evidence_snapshot(artifact: dict | None, artifact_error: str | None,
                              professor: str, *, compact_name, sha256_obj) -> dict | None:
    """Stage-4 copy of the professor's reconciled record into the email pack."""
    if artifact_error or not isinstance(artifact, dict):
        return None
    record = contact_evidence_record(artifact, professor,
                                    compact_name=compact_name)
    if record is None:
        return None
    # degraded is decision-scoped (Issue #14): the snapshot answers "was this
    # professor's current-email decision blocked upstream", not "did anything
    # anywhere fail" — family failures that left the decision intact (e.g. an
    # unreadable correspondence cache next to a single official address) don't
    # count. Packs built before the scoped contract still carry the
    # artifact-level flag and stay maximally conservative in
    # evaluate_contact_evidence.
    status = record.get("evidence_status")
    return {"generated_at": artifact.get("generated_at"),
            "degraded": contact_evidence_record_degraded(record),
            "evidence_status": status if isinstance(status, dict) else None,
            "source_errors": artifact.get("source_errors") or [],
            "recent_paper_years": artifact.get("recent_paper_years"),
            "current_year": artifact.get("current_year"),
            "record_fingerprint": sha256_obj(record),
            "record": record}


def evidence_provenance(record: dict, recipient: str) -> dict:
    return {
        "verdict": record.get("verdict"),
        "current_email": record.get("current_email"),
        "official_provenance": [row for row in record.get("official_emails", [])
                                if isinstance(row, dict) and row.get("email") == recipient],
        "paper_evidence": [row for row in record.get("paper_correspondence", [])
                           if isinstance(row, dict) and row.get("email") == recipient],
        "conflicting_paper_emails": record.get("conflicting_paper_emails") or [],
    }


def contact_evidence_freshness_reason(timestamp: Any, *,
                                       verify_ttl_days) -> str | None:
    """Issue-#10 freshness gate for contact-evidence timestamps.

    Returns a stable escalate reason when the timestamp is absent, unparseable,
    or older than the same VERIFY_TTL_DAYS window the pre-send verify cache
    uses; None when the evidence is fresh enough to act on.
    """
    if not isinstance(timestamp, str) or not timestamp.strip():
        return "contact_evidence_timestamp_invalid"
    raw = timestamp.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return "contact_evidence_timestamp_invalid"
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - moment > timedelta(days=verify_ttl_days):
        return "contact_evidence_stale"
    return None


def evaluate_contact_evidence(professor: str, snapshot: Any,
                              artifact: dict | None,
                              artifact_error: str | None,
                              state: dict | None = None,
                              checker_error: str | None = None,
                              rebuild_ran: bool = False, *,
                              compact_name, sha256_obj, verify_ttl_days) -> dict:
    """Issue-#10 decision ladder under the schema-2 source-state contract
    (final cross-repo acceptance criteria, PR #14 comment 5540723034), with
    the frozen-pack fact-source boundary from the final review round.

    邮件输入.json is Stage 5's single fact source: the recipient is read from
    the Stage-4 snapshot frozen inside the email pack, and the live artifact
    (plus any deterministic Stage-5 rebuild of it) only certifies freshness —
    the live record fingerprint must stay byte-identical to the frozen one.

    The primary gate is live source-state freshness from professor-research's
    local `--check` interface, judged per target professor:

    - `fresh`: the frozen snapshot is consumable when the live record still
      matches its fingerprint and its own decision is unblocked
      (current_email_blocked_by empty); artifact-level degraded/global_degraded
      flags alone never force web. The verdict ladder
      (confirmed_cross_source, single official_only) then applies unchanged.
    - fingerprint mismatch (including after a rebuild changed the record):
      status `needs_refresh` — a Stage-4 re-run must refreeze the pack; the
      live record is never accepted directly.
    - `stale`: never accepted on a fresh timestamp and never resolved from the
      pack snapshot — the deterministic local rebuild ran and the re-check
      still could not confirm fresh evidence (rebuild_failed).
    - `unavailable`: a universal source blocker only an upstream repair can
      fix; pack snapshots and previously seeded verify caches are not
      substitutes for it.

    The generated_at/VERIFY_TTL_DAYS window remains only as the send-time age
    policy on top of source-state freshness. Without the upstream checker
    installed, legacy schema-1 artifacts keep the transitional age-policy
    gate; schema-2 artifacts fail closed because their freshness cannot be
    confirmed live.
    """
    def escalate(reason_code: str) -> dict:
        return {"status": "escalate", "reason_code": reason_code,
                "recipient_email": None, "single_source": None,
                "web_lookup_required": True, "source": None,
                "snapshot_stale": None, "provenance": {}}

    def needs_refresh(reason_code: str, stale: bool) -> dict:
        # The pack is out of sync with upstream contact facts (or predates
        # the frozen snapshot entirely). The fix is a Stage-4 refresh, not a
        # web lookup — web verification cannot repair the pack, and Stage 5
        # must never accept a live record its own pack cannot replay.
        return {"status": "needs_refresh", "reason_code": reason_code,
                "recipient_email": None, "single_source": None,
                "web_lookup_required": False, "source": None,
                "snapshot_stale": stale, "provenance": {}}

    def accept(status: str, record: dict, recipient: str, source: str,
               single_source: bool) -> dict:
        return {"status": status, "reason_code": None,
                "recipient_email": recipient, "single_source": single_source,
                "web_lookup_required": False, "source": source,
                "snapshot_stale": False,
                "provenance": evidence_provenance(record, recipient)}

    if checker_error == "script_failed":
        # The checker exists but live source-state freshness is unconfirmable.
        return escalate("contact_evidence_check_unavailable")
    if checker_error == "script_missing":
        # Transitional install without professor-research's checker: legacy
        # schema-1 artifacts keep the age-policy gate; schema-2 artifacts
        # fail closed because their freshness cannot be confirmed live.
        if artifact_error:
            return escalate("contact_evidence_artifact_unreadable")
        if artifact is None:
            return escalate("contact_evidence_missing")
        if artifact.get("schema") == CONTACT_EVIDENCE_SCHEMA_LIVE:
            return escalate("contact_evidence_check_unavailable")
        return _evaluate_record_ladder(
            professor, snapshot, artifact, escalate, accept, needs_refresh,
            compact_name=compact_name, sha256_obj=sha256_obj,
            verify_ttl_days=verify_ttl_days)
    if state is None:
        # The checker ran but attributes no state to this professor, so the
        # rebuild-first pass already ran: either the rebuild itself failed, or
        # it succeeded and the professor genuinely has no upstream record.
        if not rebuild_ran:
            return escalate("contact_evidence_rebuild_failed")
        if artifact_error:
            return escalate("contact_evidence_artifact_unreadable")
        return escalate("contact_evidence_professor_not_found")
    if state["result"] == "unavailable":
        return escalate("contact_evidence_source_unavailable")
    if state["result"] == "stale":
        # Stale source-state after the rebuild-first pass: the local rebuild
        # cannot resolve this, so it never becomes a timestamp/age question.
        return escalate("contact_evidence_rebuild_failed")
    if artifact_error:
        return escalate("contact_evidence_artifact_unreadable")
    return _evaluate_record_ladder(
        professor, snapshot, artifact, escalate, accept, needs_refresh,
        compact_name=compact_name, sha256_obj=sha256_obj,
        verify_ttl_days=verify_ttl_days)


def _evaluate_record_ladder(professor: str, snapshot: Any, artifact: dict,
                            escalate, accept, needs_refresh, *,
                            compact_name, sha256_obj, verify_ttl_days) -> dict:
    """Verdict ladder over the Stage-4 frozen pack snapshot, freshness-
    certified live. The recipient fact comes from the snapshot embedded in
    邮件输入.json; the live record must still match the frozen fingerprint
    byte-for-byte or the decision demands a Stage-4 refresh — so a Stage-5
    rebuild that changed upstream facts can never inject a recipient the
    input pack cannot replay. The generated_at TTL gate here is the send-time
    age policy only; source-state freshness is judged upstream (or,
    transitionally for legacy artifacts, not at all)."""
    stale_reason = contact_evidence_freshness_reason(
        artifact.get("generated_at"), verify_ttl_days=verify_ttl_days)
    if stale_reason:
        return escalate(stale_reason)
    record = contact_evidence_record(artifact, professor,
                                    compact_name=compact_name)
    if record is None:
        return escalate("contact_evidence_professor_not_found")
    if not isinstance(snapshot, dict) or \
            not isinstance(snapshot.get("record_fingerprint"), str):
        return needs_refresh("contact_evidence_snapshot_missing", False)
    if snapshot["record_fingerprint"] != sha256_obj(record):
        return needs_refresh("contact_evidence_snapshot_stale", True)
    # Fingerprints match, so the frozen record is byte-identical to the live
    # one; reading the facts from the pack keeps the contract explicit.
    frozen = snapshot.get("record")
    if isinstance(frozen, dict):
        record = frozen
    if contact_evidence_record_degraded(record):
        # Scoped degradation (Issue #14): escalate only when this record's
        # current-email decision was actually blocked upstream — raw
        # family-unavailable flags are not enough, since upstream keeps a
        # record usable when its decision rests only on readable families.
        return escalate("contact_evidence_artifact_degraded")
    if record.get("verdict") not in CONTACT_EVIDENCE_VERDICTS:
        return escalate("contact_evidence_invalid_record")
    verdict = record.get("verdict")
    recipient = record.get("current_email")
    if verdict == "confirmed_cross_source":
        confirmed = record.get("confirmed_emails")
        if recipient and isinstance(confirmed, list) and len(confirmed) == 1:
            return accept("confirmed_cross_source", record, recipient,
                          "pack_snapshot", False)
        return escalate("contact_evidence_ambiguous")
    if verdict == "official_only":
        if recipient:
            return accept("official_only", record, recipient,
                          "pack_snapshot", True)
        return escalate("contact_evidence_ambiguous")
    if verdict == "conflict":
        return escalate("contact_evidence_conflict")
    if verdict == "paper_only":
        # Paper correspondence is never a current outreach address on its own.
        return escalate("contact_evidence_paper_only")
    return escalate("contact_evidence_insufficient")


def contact_evidence_decisions(emails: list[dict], resolved: dict, *,
                               compact_name, sha256_obj, verify_ttl_days) -> dict:
    decisions = {}
    for email in emails:
        professor = email.get("professor")
        if professor in decisions:
            continue
        decisions[professor] = evaluate_contact_evidence(
            professor, email.get("contact_evidence"), resolved["artifact"],
            resolved["artifact_error"],
            professor_source_state(resolved["report"], professor,
                                   compact_name=compact_name),
            resolved["checker_error"], resolved["rebuild_ran"],
            compact_name=compact_name, sha256_obj=sha256_obj,
            verify_ttl_days=verify_ttl_days)
    return decisions
