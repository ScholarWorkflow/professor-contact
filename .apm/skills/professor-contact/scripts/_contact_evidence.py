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
