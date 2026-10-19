#!/usr/bin/env python3
"""Deterministic state runner for professor-contact stages 2-5.

Only local deterministic work: JSON/schema validation, fingerprinting, cache
invalidation, scope selection, stable ordering, version-family heuristics,
state updates, atomic writes, model-job assembly and deterministic Markdown
projection.  Never starts subagents, models, browsers, Zotero or the network.
The single child process it may run is professor-research's local
deterministic `contact_evidence.py` freshness check/rebuild (local sources
only, no web/PDF/Zotero/model work on its side either).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Stage-3 Markdown rendering lives in a sibling helper. It is loaded by path
# (the runner may be executed directly or imported by path, so the scripts
# directory is not guaranteed to be on sys.path) and the pre-split module-level
# API is preserved below where the group used to live.
_STAGE3_RENDER_PATH = Path(__file__).with_name("_stage3_render.py")
_STAGE3_RENDER_SPEC = importlib.util.spec_from_file_location(
    "_stage3_render", _STAGE3_RENDER_PATH)
if _STAGE3_RENDER_SPEC is None or _STAGE3_RENDER_SPEC.loader is None:
    raise RuntimeError(f"cannot load Stage-3 renderer: {_STAGE3_RENDER_PATH}")
_stage3_render = importlib.util.module_from_spec(_STAGE3_RENDER_SPEC)
_STAGE3_RENDER_SPEC.loader.exec_module(_stage3_render)

# Shared error-channel and atomic-write helpers live in a sibling module
# (loaded by path for the same reason as the renderer above). Every name keeps
# its pre-split identity in this namespace: `fail`/`soft_exit`/`emit` have
# hundreds of call sites, and the business-failure class must stay the same
# object a caller catches.
_CONTACT_IO_PATH = Path(__file__).with_name("_contact_io.py")
_CONTACT_IO_SPEC = importlib.util.spec_from_file_location(
    "_contact_io", _CONTACT_IO_PATH)
if _CONTACT_IO_SPEC is None or _CONTACT_IO_SPEC.loader is None:
    raise RuntimeError(f"cannot load contact I/O helpers: {_CONTACT_IO_PATH}")
_contact_io = importlib.util.module_from_spec(_CONTACT_IO_SPEC)
_CONTACT_IO_SPEC.loader.exec_module(_contact_io)

atomic_write = _contact_io.atomic_write
atomic_json = _contact_io.atomic_json
atomic_json_many = _contact_io.atomic_json_many
staged_pair_commit = _contact_io.staged_pair_commit
emit = _contact_io.emit
ProfessorBusinessFailure = _contact_io.ProfessorBusinessFailure
_BUSINESS_CHANNEL = _contact_io._BUSINESS_CHANNEL
professor_business_channel = _contact_io.professor_business_channel
_business_channel_open = _contact_io._business_channel_open
fail = _contact_io.fail
soft_exit = _contact_io.soft_exit

# Upstream contact-evidence location/check/rebuild lives in a sibling module in
# this same directory (its __file__-based resolution depends on that). The five
# functions that already had their final signatures are aliases; the three that
# need runner helpers keep same-signature wrappers so every existing call site
# and test call stays unchanged.
_CONTACT_EVIDENCE_PATH = Path(__file__).with_name("_contact_evidence.py")
_CONTACT_EVIDENCE_SPEC = importlib.util.spec_from_file_location(
    "_contact_evidence", _CONTACT_EVIDENCE_PATH)
if _CONTACT_EVIDENCE_SPEC is None or _CONTACT_EVIDENCE_SPEC.loader is None:
    raise RuntimeError(
        f"cannot load contact-evidence helpers: {_CONTACT_EVIDENCE_PATH}")
_contact_evidence = importlib.util.module_from_spec(_CONTACT_EVIDENCE_SPEC)
_CONTACT_EVIDENCE_SPEC.loader.exec_module(_contact_evidence)

CONTACT_EVIDENCE_FILE = _contact_evidence.CONTACT_EVIDENCE_FILE
CONTACT_EVIDENCE_KIND = _contact_evidence.CONTACT_EVIDENCE_KIND
CONTACT_EVIDENCE_SCHEMAS = _contact_evidence.CONTACT_EVIDENCE_SCHEMAS
UPSTREAM_REPO_ID = _contact_evidence.UPSTREAM_REPO_ID
UPSTREAM_SKILL_ID = _contact_evidence.UPSTREAM_SKILL_ID
UPSTREAM_CHECK_RESOURCE = _contact_evidence.UPSTREAM_CHECK_RESOURCE
UPSTREAM_SCRIPT_ENV = _contact_evidence.UPSTREAM_SCRIPT_ENV
UPSTREAM_CHECK_TIMEOUT_SECONDS = _contact_evidence.UPSTREAM_CHECK_TIMEOUT_SECONDS
upstream_check_script = _contact_evidence.upstream_check_script
run_contact_evidence_check = _contact_evidence.run_contact_evidence_check
run_contact_evidence_rebuild = _contact_evidence.run_contact_evidence_rebuild
run_upstream_check_argv = _contact_evidence.run_upstream_check_argv
source_state_needs_rebuild = _contact_evidence.source_state_needs_rebuild


CONTACT_EVIDENCE_SCHEMA_LIVE = _contact_evidence.CONTACT_EVIDENCE_SCHEMA_LIVE
CONTACT_EVIDENCE_VERDICTS = _contact_evidence.CONTACT_EVIDENCE_VERDICTS
contact_evidence_record = _contact_evidence.contact_evidence_record
contact_evidence_record_degraded = _contact_evidence.contact_evidence_record_degraded
evidence_provenance = _contact_evidence.evidence_provenance
contact_evidence_freshness_reason = _contact_evidence.contact_evidence_freshness_reason
_evaluate_record_ladder = _contact_evidence._evaluate_record_ladder


def contact_evidence_snapshot(artifact: dict | None, artifact_error: str | None,
                              professor: str) -> dict | None:
    """Same-signature entry point; injects the runner helpers."""
    return _contact_evidence.contact_evidence_snapshot(
        artifact, artifact_error, professor, compact_name=compact_name,
        sha256_obj=sha256_obj)


def evaluate_contact_evidence(professor: str, snapshot: Any,
                              artifact: dict | None,
                              artifact_error: str | None,
                              state: dict | None = None,
                              checker_error: str | None = None,
                              rebuild_ran: bool = False) -> dict:
    """Same-signature entry point; injects the runner helpers."""
    return _contact_evidence.evaluate_contact_evidence(
        professor, snapshot, artifact, artifact_error, state=state,
        checker_error=checker_error, rebuild_ran=rebuild_ran,
        compact_name=compact_name, sha256_obj=sha256_obj,
        verify_ttl_days=VERIFY_TTL_DAYS)


def contact_evidence_decisions(emails: list[dict], resolved: dict) -> dict:
    """Same-signature entry point; injects the runner helpers."""
    return _contact_evidence.contact_evidence_decisions(
        emails, resolved, compact_name=compact_name, sha256_obj=sha256_obj,
        verify_ttl_days=VERIFY_TTL_DAYS)


def load_contact_evidence(program_root: Path) -> tuple[dict | None, str | None]:
    """Same-signature entry point; injects the runner's JSON reader."""
    return _contact_evidence.load_contact_evidence(
        program_root, read_json_file=read_json_file)


def professor_source_state(report: dict | None, professor: str) -> dict | None:
    """Same-signature entry point; injects the runner's name normalizer."""
    return _contact_evidence.professor_source_state(
        report, professor, compact_name=compact_name)


def resolve_contact_evidence(program_root: Path, professors: list[str]) -> dict:
    """Same-signature entry point; injects both runner helpers."""
    return _contact_evidence.resolve_contact_evidence(
        program_root, professors, read_json_file=read_json_file,
        compact_name=compact_name)

# Stage-3 validator-handoff primitives live in a sibling helper. The failure
# channel is injected at every call, so the helper owns no second channel
# instance. Aliases keep the pre-split module-level API; `stage3_render_line_scopes`
# additionally keeps a same-signature wrapper because tests call it with the
# rendered text only.
_STAGE3_HANDOFF_PATH = Path(__file__).with_name("_stage3_handoff.py")
_STAGE3_HANDOFF_SPEC = importlib.util.spec_from_file_location(
    "_stage3_handoff", _STAGE3_HANDOFF_PATH)
if _STAGE3_HANDOFF_SPEC is None or _STAGE3_HANDOFF_SPEC.loader is None:
    raise RuntimeError(f"cannot load Stage-3 handoff helpers: {_STAGE3_HANDOFF_PATH}")
_stage3_handoff = importlib.util.module_from_spec(_STAGE3_HANDOFF_SPEC)
_STAGE3_HANDOFF_SPEC.loader.exec_module(_stage3_handoff)

CANDIDATE_META_PREFIX = _stage3_handoff.CANDIDATE_META_PREFIX
STAGE3_SCOPE_PREFIX = _stage3_handoff.STAGE3_SCOPE_PREFIX
STAGE3_VALIDATION_MAX_ROUNDS = _stage3_handoff.STAGE3_VALIDATION_MAX_ROUNDS
_stage3_marker_payload = _stage3_handoff._stage3_marker_payload
scope_key = _stage3_handoff.scope_key
_stage3_issue_scopes = _stage3_handoff._stage3_issue_scopes
_stage3_validation_files = _stage3_handoff._stage3_validation_files
_stage3_normalized_absolute_path = _stage3_handoff._stage3_normalized_absolute_path
_stage3_complete_write_result = _stage3_handoff._stage3_complete_write_result
_stage3_args_from_invocation = _stage3_handoff._stage3_args_from_invocation
_require_stage3_handoff_round = _stage3_handoff._require_stage3_handoff_round
_stage3_json_object_pairs = _stage3_handoff._stage3_json_object_pairs
_stage3_json_reject_constant = _stage3_handoff._stage3_json_reject_constant
_stage3_created_file_identity = _stage3_handoff._stage3_created_file_identity
_stage3_cleanup_incomplete_write = _stage3_handoff._stage3_cleanup_incomplete_write
_stage3_write_buffer = _stage3_handoff._stage3_write_buffer


def stage3_render_line_scopes(md_text: str) -> list:
    """Same-signature entry point (tests call it with the rendered text only)."""
    return _stage3_handoff.stage3_render_line_scopes(md_text, fail=fail)

# Stage-2 resolve-plan helpers live in a sibling module in this same directory.
# It is loaded by path (the runner may be executed directly or imported by
# path, so the scripts directory is not guaranteed to be on sys.path) and bound
# to this runner's helpers by one explicit factory call further down, after
# those helpers are defined. The aliases keep every pre-split module-level
# entry point unchanged.
_STAGE2_RESOLVE_PATH = Path(__file__).with_name("_stage2_resolve.py")
_STAGE2_RESOLVE_SPEC = importlib.util.spec_from_file_location(
    "_stage2_resolve", _STAGE2_RESOLVE_PATH)
if _STAGE2_RESOLVE_SPEC is None or _STAGE2_RESOLVE_SPEC.loader is None:
    raise RuntimeError(f"cannot load Stage-2 resolve helpers: {_STAGE2_RESOLVE_PATH}")
_stage2_resolve_module = importlib.util.module_from_spec(_STAGE2_RESOLVE_SPEC)
_STAGE2_RESOLVE_SPEC.loader.exec_module(_stage2_resolve_module)
# Stage-2 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_STAGE2_FINALIZE_PATH = Path(__file__).with_name("_stage2_finalize.py")
_STAGE2_FINALIZE_SPEC = importlib.util.spec_from_file_location(
    "_stage2_finalize", _STAGE2_FINALIZE_PATH)
if _STAGE2_FINALIZE_SPEC is None or _STAGE2_FINALIZE_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage2_finalize: {_STAGE2_FINALIZE_PATH}")
_stage2_finalize_module = importlib.util.module_from_spec(_STAGE2_FINALIZE_SPEC)
_STAGE2_FINALIZE_SPEC.loader.exec_module(_stage2_finalize_module)
_STAGE2_VALIDATION_PATH = Path(__file__).with_name("_stage2_validation.py")
_STAGE2_VALIDATION_SPEC = importlib.util.spec_from_file_location(
    "_stage2_validation", _STAGE2_VALIDATION_PATH)
if _STAGE2_VALIDATION_SPEC is None or _STAGE2_VALIDATION_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage2_validation: {_STAGE2_VALIDATION_PATH}")
_stage2_validation_module = importlib.util.module_from_spec(_STAGE2_VALIDATION_SPEC)
_STAGE2_VALIDATION_SPEC.loader.exec_module(_stage2_validation_module)

# Stage-2 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_STAGE2_FACTS_PATH = Path(__file__).with_name("_stage2_facts.py")
_STAGE2_FACTS_SPEC = importlib.util.spec_from_file_location(
    "_stage2_facts", _STAGE2_FACTS_PATH)
if _STAGE2_FACTS_SPEC is None or _STAGE2_FACTS_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage2_facts: {_STAGE2_FACTS_PATH}")
_stage2_facts_module = importlib.util.module_from_spec(_STAGE2_FACTS_SPEC)
_STAGE2_FACTS_SPEC.loader.exec_module(_stage2_facts_module)

# Stage-2 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_STAGE2_RENDER_PATH = Path(__file__).with_name("_stage2_render.py")
_STAGE2_RENDER_SPEC = importlib.util.spec_from_file_location(
    "_stage2_render", _STAGE2_RENDER_PATH)
if _STAGE2_RENDER_SPEC is None or _STAGE2_RENDER_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage2_render: {_STAGE2_RENDER_PATH}")
_stage2_render_module = importlib.util.module_from_spec(_STAGE2_RENDER_SPEC)
_STAGE2_RENDER_SPEC.loader.exec_module(_stage2_render_module)

SCHEMA = 1

# Stage-2 preflight, identity and plan-command helpers live in a sibling module
# in this same directory. It is loaded by path (the runner may be executed
# directly or imported by path, so the scripts directory is not guaranteed to
# be on sys.path) and bound to this runner's helpers by one explicit factory
# call further down, after those helpers are defined. The aliases keep every
# pre-split module-level entry point unchanged.
_STAGE2_PREFLIGHT_PATH = Path(__file__).with_name("_stage2_preflight.py")
_STAGE2_PREFLIGHT_SPEC = importlib.util.spec_from_file_location(
    "_stage2_preflight", _STAGE2_PREFLIGHT_PATH)
if _STAGE2_PREFLIGHT_SPEC is None or _STAGE2_PREFLIGHT_SPEC.loader is None:
    raise RuntimeError(f"cannot load Stage-2 preflight helpers: {_STAGE2_PREFLIGHT_PATH}")
_stage2_preflight_module = importlib.util.module_from_spec(_STAGE2_PREFLIGHT_SPEC)
_STAGE2_PREFLIGHT_SPEC.loader.exec_module(_stage2_preflight_module)
SIDECAR_EXTRACTOR_VERSIONS = _stage2_preflight_module.SIDECAR_EXTRACTOR_VERSIONS
FACTS_GENERATOR_VERSIONS = _stage2_preflight_module.FACTS_GENERATOR_VERSIONS

MANAGED_BY = "contact_state"
# Issue #8 identity contract (direction-id-v1): the machine identity of a
# direction is the canonical `direction_id`; `collection_key` is legacy
# Zotero-projection metadata only and must never route cache/state/results.
# Files below carry their own schema + identity discriminators; SCHEMA=1 stays
# only for structures this migration does not touch (freshness cache, email
# state, migrate ledger).
INPUT_PACK_SCHEMA = 2
CANDIDATE_STATE_SCHEMA = 2
SELECTION_SCHEMA = 2
EMAIL_PACK_SCHEMA = 2
# Issue #67: schema 3 marks a professor-local Stage-4 container
# (<professor_dir>/套磁选择.json + 邮件输入.json). The legacy program-level
# containers keep their schema-2 identity so migration can still tell them
# apart instead of treating every file as the new authority.
STAGE4_LOCAL_SCHEMA = 3
DIRECTION_IDENTITY_VERSION = "direction-id-v1"
STAGE3_GENERATOR_CONTRACT_VERSION = "stage3-ideas-v2"
STAGE3_CROSS_CONTRACT_VERSION = "stage3-cross-v1"
INPUT_PACK_KIND = "professor-contact-stage2-input"
CANDIDATE_STATE_KIND = "professor-contact-stage3-state"
SELECTION_KIND = "professor-contact-selection"
EMAIL_PACK_KIND = "professor-contact-email-input"
# v2 adds per-entry `acceptance` ("proposed"|"accepted"): a material change is
# written as proposed BEFORE the user makes the Stage-2 choice. Acceptance is
# a machine-enforced boundary, not a side effect: an entry becomes accepted
# ONLY via `stage2-resolve-accept --ckeys` (the user adopting the proposal) or
# `stage2-resolve-finalize --keep-provisional` (the user explicitly keeping the
# provisional identity). stage2-finalize fails closed on any sidecar that
# still contains proposed entries and never flips acceptance itself. Reuse
# gates only ever consume accepted entries.
RESOLVED_DIRECTION_SCHEMA = 2
INPUT_PACK = "套磁候选输入.json"
CANDIDATE_STATE = "套磁候选状态.json"
EMAIL_PACK = "邮件输入.json"
EMAIL_STATE = "套磁邮件状态.json"
FRESHNESS_CACHE = "论文分析/_freshness_cache.json"
ANALYSIS_MD = "套磁候选分析.md"
CANDIDATES_MD = "套磁想法候选.md"
CANDIDATES_OVERVIEW = "套磁想法候选总览.md"
EMAIL_OVERVIEW = "套磁邮件总览.md"
SELECTION_FILE = "套磁选择.json"
PROJECTIONS_FILE = "_contact_projections.json"
VERIFY_FILE = "_contact_verify.json"


GAP_SCOPES = ("relevant", "selected_direction", "all")
FRESHNESS_SCOPES = ("shortlist", "full")
REFRESH_SCOPES = ("flagged", "selected", "all")
GAP_STATUSES = ("open", "partial", "done_by_self", "unknown")
ANCHORABLE = ("open", "partial", "unknown")
AUTHORSHIP_RANK = {"corresponding": 15, "solo": 15, "first": 12, "pending": 5}
# Stage-5 audit provenance suffixes. The business entry is the legacy
# full-body-humanizer label; the immutable wrapper declares the other two
# through the internal --audit-provenance input instead of rewriting this
# file's source. Each entry is the complete rendered suffix, and the wrapper
# verifies the business literal is still the single occurrence before it
# delegates, so splitting these strings silently would fail closed.
STAGE5_AUDIT_PROVENANCE = {
    "business": " ｜ 过稿: humanizer-ja(business)",
    "none": " ｜ 过稿: none",
    "dynamic-fields-only": " ｜ 过稿: humanizer-ja(dynamic-fields-only)",
}
FACTS_SCHEMA = 1
FACTS_KIND = "paper-analysis-facts"
STAGE1_STATE_FILE_NAME = "套磁阶段1候选.json"
STAGE1_STATE_SCHEMA_VERSION = 2
STAGE1_STATE_KIND = "professor-contact-stage1"
FACTS_TEXT_FIELDS = ("research_problem", "research_object", "approach")
FACTS_LIST_FIELDS = ("findings", "contributions", "topic_terms", "limitations")
SHORTLIST_MAX = 10
SHORTLIST_FLOOR = 5
QUOTE_INPUT_CHARS = 300
TRANSLATION_INPUT_CHARS = 200
ABSTRACT_INPUT_CHARS = 400
PROFILE_INPUT_CHARS = 2000
INTEREST_HARD_CAP = 200
INTEREST_SOFT_CAP = 180
VERIFY_TTL_DAYS = 30
VERIFY_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CLOSING_RE = re.compile(r"^このような.+は、まだ数多く存在すると感じております。$")
BATCH_RE = re.compile(r"(冬季|夏季|[123]次募集|海外特別入試)")
EXT_EVIDENCE_RE = re.compile(
    r"(extend(?:ed|s)?\s+(?:version|journal|conference|our|the)|journal version|"
    r"preliminary (?:version|report)|conference version|earlier version|拡張版)",
    re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"\{\{([PGL]):([^}]+)\}\}")
DEFAULT_TEMPLATE = None
DEFAULT_FOLLOWUP_TEMPLATE = None
"""Embedded email templates are intentionally absent; callers must provide them."""


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime(VERIFY_TIMESTAMP_FORMAT)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(payload: Any) -> str:
    return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def normalized_quote(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip()


def quote_id(value: str) -> str:
    return sha256_text(normalized_quote(value))


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_json_file(path: Path) -> tuple[Any, str | None]:
    try:
        return load_json(path), None
    except FileNotFoundError:
        return None, "not_found"
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return None, f"invalid: {exc}"


def professor_dir_containment_error(professor_dir: Path, program_root: Path) -> str | None:
    """Return `invalid_professor_dir` when a professor dir leaves the program."""
    try:
        allowed = (program_root / "教授研究").resolve()
        actual = Path(professor_dir).resolve()
        actual.relative_to(allowed)
    except (OSError, ValueError):
        return "invalid_professor_dir"
    return None


def require_professor_dir_under_program(professor_dir: Path, program_root: Path) -> None:
    """Prevent workflow state from being written outside the selected program."""
    if professor_dir_containment_error(professor_dir, program_root) is None:
        return
    fail("invalid_professor_dir", "professor_dir must be inside program_root/教授研究",
         professor_dir=str(Path(professor_dir).resolve()),
         allowed_root=str((program_root / "教授研究").resolve()))


def truncate(text: str | None, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "…"


def text_tokens(text: str) -> set:
    tokens = set()
    for word in re.findall(r"[A-Za-z0-9]+", text or ""):
        if len(word) >= 3:
            tokens.add(word.lower())
    for run in re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", text or ""):
        for index in range(len(run) - 1):
            tokens.add(run[index:index + 2])
    return tokens


def title_tokens(title: str) -> set:
    return text_tokens(title)


def rel_path(target: Path, base: Path) -> str:
    try:
        return os.path.relpath(str(Path(target).resolve()), str(Path(base).resolve()))
    except ValueError:
        return str(target)


def filename_component(value: Any) -> str:
    raw = unicodedata.normalize("NFKC", str(value or ""))
    cleaned = re.sub(r"[^\w.-]+", "_", raw, flags=re.UNICODE).strip("._")
    return cleaned[:80] or sha256_text(raw)[:12]


def safe_result_file(kind: str, identity: str) -> str:
    """Deterministic result filename that never embeds an arbitrary machine ID raw."""
    return f"{kind}-{filename_component(identity)}-{sha256_text(identity)[:8]}.json"


def direction_machine_id(direction: dict) -> str:
    """Canonical direction identity (issue #8 direction-id-v1).

    v2 pack directions carry `direction_id` directly. Legacy v1 packs are
    normalized in memory (see normalize_input_pack) using the exact 1:1
    machine relations the pack itself records — the authoritative resolved id
    when present, else the provisional collection_key. Display names, array
    positions and Zotero collection NAMES are never consulted.
    """
    did = direction.get("direction_id")
    if isinstance(did, str) and did.strip():
        return did.strip()
    rd = direction.get("resolved_direction")
    if isinstance(rd, dict):
        rid = rd.get("resolved_direction_id")
        if isinstance(rid, str) and rid.strip():
            return rid.strip()
    ckey = direction.get("collection_key")
    if isinstance(ckey, str) and ckey.strip():
        return ckey.strip()
    fail("invalid_input_pack", "pack direction has no machine direction identity")


def facts_direction_id(direction: dict) -> str:
    """Direction identity while reading Stage-2 facts (pre-pack).

    v2 facts carry the selected `direction_id` from 套磁目标.json unchanged.
    Legacy facts without it map collection_key 1:1 — the explicit machine
    mapping §9 allows; nothing is inferred from names or array positions.
    """
    did = direction.get("direction_id")
    if isinstance(did, str) and did.strip():
        return did.strip()
    ckey = direction.get("collection_key")
    if isinstance(ckey, str) and ckey.strip():
        return ckey.strip()
    fail("invalid_facts", "facts direction needs direction_id (or legacy collection_key)")


def cross_group_id(direction_ids: list[str]) -> str:
    """Stable cross-direction group identity: cross:<hash of sorted IDs>."""
    return "cross:" + sha256_text("\x1f".join(sorted(direction_ids)))[:12]


def pack_paper_index(pack: dict) -> dict:
    papers = (pack or {}).get("papers")
    return papers if isinstance(papers, dict) else {}


def direction_papers(pack: dict, direction: dict) -> list[dict]:
    """Project the professor-level canonical paper records for one direction.

    The canonical record lives once in `pack["papers"][item_key]`; per-direction
    display flags (named_by_user, resolved addition provenance) are projected
    here and never stored per direction copy.
    """
    papers = pack_paper_index(pack)
    named = set(direction.get("named_keys") or [])
    added = set(direction.get("resolved_addition_keys") or [])
    out = []
    for key in direction.get("supporting_item_keys") or []:
        record = papers.get(key)
        if not isinstance(record, dict):
            continue
        out.append({**record, "named_by_user": key in named,
                    "resolved_addition": key in added})
    return out


# Authoritative paper fields: two direction-local snapshots of the same paper
# must agree exactly on these during v1 normalization or the pack is ambiguous.
_CANONICAL_PAPER_FIELDS = ("title", "year", "authorship", "analysis_file",
                           "pdf_available", "facts_state", "facts_error",
                           "paper_facts")


def _canonical_paper_record(entry: dict) -> dict:
    record = {"item_key": entry.get("item_key")}
    for field in _CANONICAL_PAPER_FIELDS:
        record[field] = entry.get(field)
    record["pdf_available"] = bool(record["pdf_available"])
    return record


def _merge_canonical_paper(papers: dict, owners: dict, entry: dict, owner: str) -> dict:
    """Merge one direction-local paper snapshot into the professor-level map.

    Same item_key from two directions must be the SAME machine paper: records
    agree exactly, or the pack fails closed (shared_paper_conflict) instead of
    silently picking one copy.
    """
    record = _canonical_paper_record(entry)
    key = record["item_key"]
    if not isinstance(key, str) or not key.strip():
        fail("invalid_input_pack", f"direction {owner!r} has a paper without item_key")
    existing = papers.get(key)
    if existing is None:
        papers[key] = record
        owners[key] = [owner]
        return record
    conflicts = [field for field in _CANONICAL_PAPER_FIELDS
                 if existing.get(field) != record.get(field)]
    if conflicts:
        soft_exit("needs_refresh", "shared_paper_conflict",
                  item_key=key, conflict_fields=sorted(conflicts),
                  directions=sorted(set(owners.get(key) or []) | {owner}),
                  message="同一 item_key 在多个方向里带有冲突的权威字段：输入包不可信，"
                          "重跑阶段 2 重建规范 papers 后再继续。未修改任何文件。")
    if owner not in owners.setdefault(key, []):
        owners[key].append(owner)
    return existing


def normalize_input_pack(raw: Any) -> dict | None:
    """Return the canonical v2 view of an input pack (never mutates the file).

    v2 packs are validated; v1 packs migrate in memory via exact machine
    mappings only: direction_id from the stamped resolved subfield (or 1:1
    collection_key), and direction-local paper snapshots canonicalized into one
    professor-level `papers` map with exact-field conflict detection.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        soft_exit("needs_refresh", "invalid_input_pack",
                  message="套磁候选输入.json 不是对象；重跑阶段 2 重建。")
    schema = raw.get("schema")
    directions_raw = raw.get("directions")
    if not isinstance(directions_raw, list):
        soft_exit("needs_refresh", "invalid_input_pack",
                  message="套磁候选输入.json 缺 directions 列表；重跑阶段 2 重建。")
    pack = dict(raw)
    if schema == INPUT_PACK_SCHEMA:
        if raw.get("kind") != INPUT_PACK_KIND or \
                raw.get("identity_version") != DIRECTION_IDENTITY_VERSION:
            soft_exit("needs_refresh", "invalid_input_pack",
                      schema=schema, kind=raw.get("kind"),
                      identity_version=raw.get("identity_version"),
                      message="输入包 schema/kind/identity_version 不匹配；重跑阶段 2 重建。")
        papers = raw.get("papers")
        if not isinstance(papers, dict):
            soft_exit("needs_refresh", "invalid_input_pack",
                      message="v2 输入包缺 professor 级 papers 映射；重跑阶段 2 重建。")
    else:
        # v1 → v2 in-memory migration (exact machine mappings only).
        papers = {}
        owners: dict = {}
        directions = []
        seen_ids = {}
        for entry in directions_raw:
            if not isinstance(entry, dict):
                soft_exit("needs_refresh", "invalid_input_pack",
                          message="输入包 directions[] 含非对象条目；重跑阶段 2 重建。")
            did = direction_machine_id(entry)
            if did in seen_ids:
                soft_exit("needs_refresh", "legacy_direction_identity",
                          direction_id=did,
                          message=f"两个方向的机器身份都解析为 {did!r}：无法唯一映射，"
                                  "重跑阶段 2/3 重建身份后再继续。未修改任何文件。")
            seen_ids[did] = True
            local = entry.get("supporting_papers")
            keys = []
            if isinstance(local, list):
                for paper in local:
                    if not isinstance(paper, dict):
                        continue
                    _merge_canonical_paper(papers, owners, paper, did)
                    if paper.get("item_key") not in keys:
                        keys.append(paper.get("item_key"))
            added = sorted({p.get("item_key") for p in (local or []) if isinstance(p, dict)
                            and p.get("resolved_addition") and p.get("item_key")}
                           | set(entry.get("resolved_addition_keys") or []))
            new_entry = dict(entry)
            new_entry["direction_id"] = did
            new_entry["supporting_item_keys"] = keys
            new_entry["resolved_addition_keys"] = added
            new_entry.pop("supporting_papers", None)
            directions.append(new_entry)
        pack["papers"] = papers
        pack["directions"] = directions
    missing = []
    for entry in pack["directions"]:
        for key in entry.get("supporting_item_keys") or []:
            if key not in pack["papers"]:
                missing.append({"direction_id": direction_machine_id(entry), "item_key": key})
    if missing:
        soft_exit("needs_refresh", "invalid_input_pack",
                  missing=missing,
                  message="supporting_item_keys 引用了 papers 映射里不存在的论文；重跑阶段 2 重建。")
    return pack


def load_input_pack(professor_dir: Path) -> tuple[dict | None, str | None]:
    """Read + normalize the input pack; (None, reason) when absent/unreadable."""
    raw, error = read_json_file(Path(professor_dir) / INPUT_PACK)
    if error or not isinstance(raw, dict):
        return None, error or "invalid_input_pack"
    return normalize_input_pack(raw), None


def _migrate_v1_candidate(candidate: dict, did: str) -> dict:
    """Exact v1→v2 candidate record migration: pair gap refs gain the owning
    direction_id (v1 candidates only ever cite their own direction's gaps), and
    paper entries gain the same single-member provenance."""
    record = dict(candidate)
    record["kind"] = "direction"
    record["direction_ids"] = [did]
    record["gap_refs"] = [
        {"direction_id": did, "item_key": pair.get("item_key"), "gap_id": pair.get("gap_id"),
         "done_by_self": bool(pair.get("done_by_self"))}
        for pair in candidate.get("gap_ids") or []]
    record.pop("gap_ids", None)
    record["papers"] = [
        {**paper, "direction_ids": [did]} for paper in candidate.get("papers") or []]
    return record


def _slice_gap_directions(pack: dict, direction_ids: list[str]) -> tuple[dict, dict]:
    """Exact-join indexes over the UNION of the given directions' slices.

    Returns (gap_owner, paper_owner) mapping each (item_key, gap_id) /
    item_key to the sorted list of participant direction IDs whose slice
    contains it — the machine data needed to attribute v1 cross records.
    """
    by_id = {direction_machine_id(d): d for d in (pack or {}).get("directions") or []}
    gap_owner: dict = {}
    paper_owner: dict = {}
    for did in direction_ids:
        direction = by_id.get(did)
        if direction is None:
            continue
        for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
            gap_owner.setdefault((gap.get("item_key"), gap.get("gap_id")), set()).add(did)
        for banned in direction.get("completed_gap_blacklist", []):
            gap_owner.setdefault((banned.get("item_key"), banned.get("gap_id")),
                                 set()).add(did)
        for key in direction.get("supporting_item_keys") or []:
            paper_owner.setdefault(key, set()).add(did)
        for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
            paper_owner.setdefault(gap.get("item_key"), set()).add(did)
    return gap_owner, paper_owner


def _migrate_v1_cross_group(entry: dict, ids: list[str], pack: dict | None) -> dict:
    """Migrate one owner-scoped v1 cross entry to a standalone v2 group.

    Attribution uses the pack's exact slices: a gap pair owned by exactly one
    participant gains that direction_id; an ambiguous pair (present in several
    participants) can NOT be mapped exactly, so the whole group's candidates
    are dropped and its fingerprints nulled — the group reprocesses instead of
    keeping evidence with guessed provenance.
    """
    gap_owner, paper_owner = _slice_gap_directions(pack, ids)
    candidates = []
    for candidate in entry.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        record = dict(candidate)
        attributable = True
        gap_refs = []
        for pair in candidate.get("gap_ids") or []:
            owners = gap_owner.get((pair.get("item_key"), pair.get("gap_id"))) or set()
            if len(owners) != 1:
                attributable = False
                break
            gap_refs.append({"direction_id": next(iter(owners)),
                             "item_key": pair.get("item_key"),
                             "gap_id": pair.get("gap_id"),
                             "done_by_self": bool(pair.get("done_by_self"))})
        papers = []
        for paper in candidate.get("papers") or []:
            owners = sorted(paper_owner.get(paper.get("item_key")) or set() & set(ids))
            papers.append({**paper, "direction_ids": owners or list(ids)})
        if not attributable:
            candidates = []
            break
        record["gap_refs"] = gap_refs
        record.pop("gap_ids", None)
        record["papers"] = papers
        record["kind"] = "cross_direction"
        record["direction_ids"] = list(ids)
        candidates.append(record)
    fingerprints = {}
    for pid, fp in (entry.get("direction_fingerprints") or {}).items():
        if pid in ids:
            fingerprints[pid] = fp
    if not candidates:
        fingerprints = {pid: None for pid in ids}
    return {"group_id": cross_group_id(ids), "direction_ids": list(ids),
            "direction_fingerprints": fingerprints, "candidates": candidates}


def normalize_candidate_state(raw: Any, pack: dict | None) -> tuple[dict | None, str | None]:
    """Return the canonical v2 view of 套磁候选状态.json (never mutates the file).

    v1 state migrates only through explicit 1:1 machine mappings recorded by
    the pack (collection_key → direction_id). Anything ambiguous fails closed
    with legacy_direction_identity and leaves accepted files untouched.
    """
    if raw is None:
        return None, None
    if not isinstance(raw, dict):
        return None, "invalid_candidate_state"
    schema = raw.get("schema")
    if schema == CANDIDATE_STATE_SCHEMA:
        if raw.get("kind") != CANDIDATE_STATE_KIND or \
                raw.get("identity_version") != DIRECTION_IDENTITY_VERSION:
            return None, "invalid_candidate_state"
        return raw, None
    # v1 → v2 exact migration.
    key_to_did: dict[str, str] = {}
    ambiguous = set()
    for entry in (pack or {}).get("directions") or []:
        did = direction_machine_id(entry)
        ckey = entry.get("collection_key")
        if isinstance(ckey, str) and ckey.strip():
            if ckey in key_to_did and key_to_did[ckey] != did:
                ambiguous.add(ckey)
            key_to_did[ckey] = did
    directions = []
    fingerprints = {}
    for entry in raw.get("directions") or []:
        if not isinstance(entry, dict):
            return None, "invalid_candidate_state"
        did = entry.get("direction_id")
        if not (isinstance(did, str) and did.strip()):
            ckey = entry.get("collection_key")
            did = key_to_did.get(ckey) if isinstance(ckey, str) else None
        if not did:
            return None, "legacy_direction_identity"
        new_entry = dict(entry)
        new_entry["direction_id"] = did
        new_entry["candidates"] = [_migrate_v1_candidate(c, did)
                                   for c in entry.get("candidates") or []
                                   if isinstance(c, dict)]
        new_entry["stage3_status"] = "ready" if new_entry["candidates"] else "empty"
        new_entry["generator_contract_version"] = STAGE3_GENERATOR_CONTRACT_VERSION
        directions.append(new_entry)
        old_fps = raw.get("input_fingerprints") or {}
        fp = old_fps.get(did) or old_fps.get(entry.get("collection_key"))
        if fp:
            fingerprints[did] = fp
    if raw.get("input_fingerprints") and not fingerprints:
        return None, "legacy_direction_identity"
    # v1 cross_direction entries were owner-scoped bookkeeping; v2 groups are
    # standalone identities keyed by sorted participant IDs. Candidates whose
    # provenance cannot be attributed exactly from the pack are dropped and
    # the group reprocesses (fingerprints nulled) instead of keeping guesses.
    grouped: dict[tuple, dict] = {}
    for entry in raw.get("cross_direction") or []:
        if not isinstance(entry, dict):
            continue
        ids = sorted({i for i in entry.get("direction_ids") or [] if isinstance(i, str)})
        if len(ids) < 2:
            continue
        key = tuple(ids)
        group = _migrate_v1_cross_group(entry, ids, pack)
        if key in grouped:
            merged = grouped[key]
            known = {c.get("id") for c in merged["candidates"]}
            merged["candidates"].extend(
                c for c in group["candidates"] if c.get("id") not in known)
            if not merged["candidates"]:
                merged["direction_fingerprints"] = {pid: None for pid in ids}
        else:
            grouped[key] = group
    state = dict(raw)
    state["schema"] = CANDIDATE_STATE_SCHEMA
    state["kind"] = CANDIDATE_STATE_KIND
    state["identity_version"] = DIRECTION_IDENTITY_VERSION
    state["generator_contract_version"] = STAGE3_GENERATOR_CONTRACT_VERSION
    state["directions"] = directions
    state["input_fingerprints"] = fingerprints
    state["cross_direction_groups"] = list(grouped.values())
    state.pop("cross_direction", None)
    return state, None


def load_candidate_state(professor_dir: Path, pack: dict | None) -> tuple[dict | None, str | None]:
    """Read + normalize the candidate state against the given (normalized) pack.

    Returns (None, None) when the file does not exist yet; (None, reason) when
    it exists but cannot be exactly migrated."""
    raw, error = read_json_file(Path(professor_dir) / CANDIDATE_STATE)
    if error == "not_found":
        return None, None
    if error or not isinstance(raw, dict):
        return None, error or "invalid_candidate_state"
    return normalize_candidate_state(raw, pack)


def _strict_candidate_shape(state: dict) -> str | None:
    """Machine-shape proof over the fields the aggregate consumes (issue #66).

    normalize_candidate_state stamps v2 identity fields without a deep
    structural pass — the Stage-4 behavior #66 must not change — so an
    on-disk state whose directions/candidates/groups are structurally
    corrupt would otherwise reach the overview renderer and publish garbage
    rows (r10 §3.7 requires every committed state to fail closed BEFORE the
    overview write). The compatibility/migration owner proves the shape
    here; renderer and rebuild stay pure consumers. Corrupt values are
    never treated as empty: the candidate list (and a group's member list)
    must be present and well-typed, or the state fails closed.
    """
    directions = state.get("directions")
    if not isinstance(directions, list):
        return "invalid_candidate_state"
    for row in directions:
        if not isinstance(row, dict):
            return "invalid_candidate_state"
        did = row.get("direction_id")
        if not (isinstance(did, str) and did.strip()):
            return "invalid_candidate_state"
        candidates = row.get("candidates")
        if not isinstance(candidates, list) or \
                any(not isinstance(c, dict) for c in candidates):
            return "invalid_candidate_state"
    groups = state.get("cross_direction_groups")
    if groups is not None and not isinstance(groups, list):
        return "invalid_candidate_state"
    for row in groups or []:
        if not isinstance(row, dict):
            return "invalid_candidate_state"
        gid = row.get("group_id")
        if not (isinstance(gid, str) and gid.strip()):
            return "invalid_candidate_state"
        direction_ids = row.get("direction_ids")
        if not isinstance(direction_ids, list) or \
                any(not isinstance(item, str) for item in direction_ids):
            return "invalid_candidate_state"
        candidates = row.get("candidates")
        if not isinstance(candidates, list) or \
                any(not isinstance(c, dict) for c in candidates):
            return "invalid_candidate_state"
    return None


def strict_candidate_state(professor_dir: Path) -> tuple[dict | None, str | None]:
    """Compatibility/migration owner for aggregate consumers (issue #66 r5).

    Loads one professor's candidate state with strict legacy identity proof:
    every collection_key the legacy state actually references must resolve to
    exactly ONE canonical direction_id in the same professor's normalized
    input pack (0 or >1 matches → legacy_direction_identity) before any
    migration runs, and the canonical state's machine shape is proven
    structurally before it may feed the aggregate. Aggregate rebuild only
    consumes the canonical state returned here and never re-implements the
    collection_key mapping itself; the pack supplies identity migration only,
    never candidate facts. Stage 4's existing normalize behavior is untouched.
    """
    raw, error = read_json_file(Path(professor_dir) / CANDIDATE_STATE)
    if error == "not_found":
        return None, None
    if error or not isinstance(raw, dict):
        return None, error or "invalid_candidate_state"
    if raw.get("schema") == CANDIDATE_STATE_SCHEMA:
        canonical, canonical_error = normalize_candidate_state(raw, None)
    else:
        pack, pack_error = load_input_pack(professor_dir)
        if pack is None:
            return None, pack_error or "missing_input_pack"
        pack_directions = pack.get("directions") or []
        for entry in raw.get("directions") or []:
            if not isinstance(entry, dict):
                return None, "invalid_candidate_state"
            ckey = entry.get("collection_key")
            if not (isinstance(ckey, str) and ckey.strip()):
                continue
            matches = sorted({direction_machine_id(d) for d in pack_directions
                              if isinstance(d, dict) and d.get("collection_key") == ckey})
            if len(matches) != 1:
                return None, "legacy_direction_identity"
        canonical, canonical_error = normalize_candidate_state(raw, pack)
    if canonical is None:
        return None, canonical_error
    shape_error = _strict_candidate_shape(canonical)
    if shape_error:
        return None, shape_error
    return canonical, None


def stage5_output_peers(email: dict, all_emails: list, professor_dir: Path,
                        *, targeted: bool) -> list:
    """Rows that share this email's output-collision namespace.

    Targeted mode cannot resolve unrelated ``professor_dir`` values, so it
    derives peers from identity metadata only. Batch mode preserves the
    pre-Issue-59 directory-scoped naming contract after the normal all-row path
    validation has succeeded.
    """
    if not targeted:
        target_dir = professor_dir.resolve()
        peers = []
        for candidate in all_emails:
            candidate_dir = Path(
                candidate.get("professor_dir") or professor_dir).resolve()
            if candidate_dir == target_dir:
                peers.append(candidate)
        return peers

    professor = email.get("professor")
    if not isinstance(professor, str) or not professor:
        return [email]
    peers = []
    seen_ids = set()
    for peer in all_emails:
        if not isinstance(peer, dict) or peer.get("professor") != professor:
            continue
        peer_id = peer.get("email_id")
        if not isinstance(peer_id, str) or not peer_id or peer_id in seen_ids:
            continue
        seen_ids.add(peer_id)
        peers.append(peer)
    return peers or [email]


def stage5_output_paths(email: dict, peers: list, professor_dir: Path,
                        kind: str = "initial") -> tuple[Path, Path]:
    prefix = "套磁跟进邮件" if kind == "followup" else "套磁邮件"
    if len(peers) <= 1:
        return professor_dir / f"{prefix}.md", professor_dir / f"{prefix}.txt"
    email_id = str(email.get("email_id") or "email")
    idea_id = (email.get("idea") or {}).get("id") or "email"
    # Issue #8 §8.2: the filename suffix derives from the canonical direction
    # scope + email id hash — a v2 entry may not have a collection_key at all.
    scope = "+".join(sorted(email.get("direction_ids") or [idea_id]))
    suffix = "_".join((filename_component(scope),
                         filename_component(idea_id), sha256_text(email_id)[:8]))
    return (professor_dir / f"{prefix}_{suffix}.md",
            professor_dir / f"{prefix}_{suffix}.txt")


def stage5_output_id(email_id: str, kind: str) -> str:
    return email_id if kind == "initial" else f"{email_id}::followup"


def paper_digest(paper: dict) -> str:
    analysis_file = paper.get("analysis_file")
    sidecar_file = paper.get("sidecar_file")
    facts_file = paper.get("facts_file")
    payload = {
        "item_key": paper.get("item_key"),
        "title": paper.get("title"),
        "year": paper.get("year"),
        "month": paper.get("month"),
        "authorship": paper.get("authorship"),
        "abstract_sha": sha256_text(paper.get("abstract") or "") if paper.get("abstract") else None,
        "has_pdf": bool(paper.get("has_pdf")),
        "analysis_sha": sha256_bytes(Path(analysis_file).read_bytes()) if analysis_file and Path(analysis_file).is_file() else None,
        "sidecar_sha": sha256_bytes(Path(sidecar_file).read_bytes()) if sidecar_file and Path(sidecar_file).is_file() else None,
        "facts_sha": sha256_bytes(Path(facts_file).read_bytes()) if facts_file and Path(facts_file).is_file() else None,
    }
    return sha256_obj(payload)


def sidecar_sha(path: str | None) -> str | None:
    if path and Path(path).is_file():
        return sha256_bytes(Path(path).read_bytes())
    return None


def gap_fingerprint(item: dict, sha: str | None) -> str:
    return sha256_obj({
        "quote": unicodedata.normalize("NFKC", item.get("quote") or "").strip(),
        "translation_zh": item.get("translation_zh"),
        "source": item.get("source"),
        "page": item.get("page"),
        "sidecar_sha": sha,
    })


def candidate_fingerprint(candidates: list) -> str:
    return sha256_obj(sorted(candidates, key=lambda c: json.dumps(c, ensure_ascii=False, sort_keys=True)))


def direction_relevant_keys(direction: dict) -> list:
    """The analysis reference scope of a facts direction.

    An explicitly empty `relevant_keys` list is a real (empty) licence and must
    stay empty; only a genuinely missing field falls back to the Stage-1
    member set for legacy inputs. A present-but-malformed value is rejected
    instead of being read as "missing".
    """
    if "relevant_keys" in direction:
        relevant = direction.get("relevant_keys")
        if not isinstance(relevant, list):
            fail("invalid_facts",
                 f"direction {facts_direction_id(direction)} has a malformed relevant_keys "
                 "value (must be a list); refusing to treat it as a missing legacy field")
        return list(relevant)
    return list(direction.get("member_keys") or [])


def direction_provisional_member_keys(direction: dict) -> list | None:
    """The ORIGINAL formal members of a facts direction (R1 single source).

    `provisional_member_keys` is the explicit Stage-1 origin list. Legacy facts
    that predate the field carry the same Stage-1 membership in `member_keys`;
    that list is accepted ONLY as the whole original set — never merged with or
    topped up from the analysis reference scope (`relevant_keys`) or user
    `named_keys`, so a reference paper can never silently become a member.
    Returns None when neither source states the original membership; callers
    must fail before writing.
    """
    keys = direction.get("provisional_member_keys")
    if not isinstance(keys, list):
        keys = direction.get("member_keys")
    if not isinstance(keys, list):
        return None
    seen: set = set()
    out: list = []
    for key in keys:
        if isinstance(key, str) and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def pack_direction_relevant_keys(direction: dict) -> list:
    """The persisted analysis reference scope of a pack direction.

    A v3 pack always stores `relevant_keys` explicitly (an empty list is an
    empty `P` licence). A legacy pack without the field keeps its members as
    the minimal read-only scope; a present-but-malformed value is rejected
    because falling back to members would silently widen the citation licence.
    """
    if "relevant_keys" in direction:
        relevant = direction.get("relevant_keys")
        if not isinstance(relevant, list):
            fail("invalid_input_pack",
                 f"direction {direction_machine_id(direction)} has a malformed relevant_keys "
                 "value (must be a list); refusing to fall back to its members",
                 direction=direction_machine_id(direction))
        return list(relevant)
    return list(direction.get("supporting_item_keys") or [])


def direction_candidate_keys(direction: dict) -> list:
    """The full per-direction candidate universe from the Stage 1 snapshot.

    Issue #7 requires every unique candidate paper to get one full
    paper-analysis pass and to be resolvable into/out of the authoritative
    direction from full-text evidence. Relevant keys are the post-relevance
    gap/narrative scope and must NOT bound the resolution evidence — otherwise
    a paper the abstract-level gate dropped can never earn its way back in.
    """
    members = direction.get("member_keys")
    if members:
        return list(members)
    return direction_relevant_keys(direction)


def selected_candidate_union(ctx: "Stage2Context") -> list:
    """Every unique candidate paper across this professor's selected directions.

    Per-direction Stage-1 candidate sets may be disjoint, but issue #7's
    acceptance #2 lets a paper from another preview cluster be added to a
    selected direction when full text supports it. So the resolved-membership
    evidence universe (affinity scoring, resolve-job paper evidence, and the
    papers_to_add allow-list) is the professor-level union — while the
    relevant/cost scope that drives gap/narrative work stays per direction.
    """
    seen: set[str] = set()
    union: list = []
    for plan in ctx.direction_plans:
        for key in direction_candidate_keys(plan["direction"]):
            if key not in seen:
                seen.add(key)
                union.append(key)
    return union


def direction_fingerprint(direction: dict, papers: dict, gap_ids: list, families: dict) -> str:
    """Model-relevant Stage-2 direction fingerprint, keyed by direction_id.

    Issue #8 §3.2: only evidence that can change Stage-3 meaning belongs here.
    collection_key and display names (name_ja/name_zh) are projection/display
    metadata — a projection-only rename or a display-only rename must never
    invalidate model work; downstream rendering handles those deterministically.
    """
    relevant = direction_relevant_keys(direction)
    return sha256_obj({
        "identity_version": DIRECTION_IDENTITY_VERSION,
        "direction_id": facts_direction_id(direction),
        "user_note_sha": sha256_text(direction.get("user_note") or ""),
        "member_keys": sorted(direction.get("member_keys") or []),
        "relevant_keys": sorted(relevant),
        "named_keys": sorted(direction.get("named_keys") or []),
        "credibility": direction.get("credibility"),
        "red_lines": direction.get("red_lines") or [],
        "paper_digests": {key: papers[key]["_digest"] for key in sorted(relevant) if key in papers},
        "gap_ids": sorted(set(gap_ids)),
        "version_families": families,
    })


def render_frontmatter(state_fingerprint: str, body_sha: str) -> str:
    return (f"---\nmanaged_by: {MANAGED_BY}\n"
            f"state_fingerprint: {state_fingerprint}\n"
            f"render_sha256: {body_sha}\n---\n\n")


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    header = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            header[key.strip()] = value.strip()
    body_start = end + 5
    if text[body_start:body_start + 1] == "\n":
        body_start += 1
    return header, text[body_start:]


def managed_conflict(path: Path, body: str, previous_sha: str | None,
                     decision: str | None) -> dict | None:
    body_sha = sha256_text(body)
    if path.is_file():
        _, existing_body = split_frontmatter(path.read_text(encoding="utf-8"))
        existing_sha = sha256_text(existing_body)
        if existing_sha != body_sha and previous_sha and existing_sha != previous_sha:
            if decision != "overwrite":
                return {"written": False, "needs_decision": True,
                        "reason_code": "manual_markdown_changed",
                        "target": str(path),
                        "existing_sha256": existing_sha, "new_sha256": body_sha}
    return None


def managed_write(path: Path, body: str, state_fingerprint: str,
                  previous_sha: str | None, decision: str | None) -> dict:
    body_sha = sha256_text(body)
    conflict = managed_conflict(path, body, previous_sha, decision)
    if conflict:
        return conflict
    atomic_write(path, render_frontmatter(state_fingerprint, body_sha) + body)
    return {"written": True, "needs_decision": False, "sha256": body_sha}


def managed_write_raw(path: Path, body: str, previous_sha: str | None,
                      decision: str | None) -> dict:
    body_sha = sha256_text(body)
    if path.is_file():
        existing_sha = sha256_text(path.read_text(encoding="utf-8"))
        if existing_sha != body_sha and previous_sha and existing_sha != previous_sha:
            if decision != "overwrite":
                return {"written": False, "needs_decision": True,
                        "reason_code": "manual_markdown_changed", "target": str(path),
                        "existing_sha256": existing_sha, "new_sha256": body_sha}
    atomic_write(path, body)
    return {"written": True, "needs_decision": False, "sha256": body_sha}


def projection_conflict(path: Path, body: str, projections: dict, key: str) -> dict | None:
    body_sha = sha256_text(body)
    previous = (projections or {}).get("render", {}).get(key, {}).get("sha256")
    if path.is_file():
        _, existing_body = split_frontmatter(path.read_text(encoding="utf-8"))
        existing_sha = sha256_text(existing_body)
        if existing_sha != body_sha and previous and existing_sha != previous:
            return {"written": False, "needs_decision": True,
                    "reason_code": "manual_markdown_changed", "target": str(path)}
    return None


def projection_write(path: Path, body: str, projections: dict, key: str) -> dict:
    conflict = projection_conflict(path, body, projections, key)
    if conflict:
        return conflict
    body_sha = sha256_text(body)
    projection_fingerprint = sha256_obj({"projection": key, "body": body_sha})
    atomic_write(path, render_frontmatter(projection_fingerprint, body_sha) + body)
    return {"written": True, "needs_decision": False, "sha256": body_sha}


def load_projections(program_root: Path) -> dict:
    data, error = read_json_file(program_root / "教授研究" / PROJECTIONS_FILE)
    if error or not isinstance(data, dict):
        return {"render": {}}
    data.setdefault("render", {})
    return data


def save_projections(program_root: Path, projections: dict) -> None:
    atomic_json(program_root / "教授研究" / PROJECTIONS_FILE, projections)


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage2_facts = _stage2_facts_module.build(
    atomic_json=atomic_json,
    fail=fail,
    SCHEMA=SCHEMA,
    MANAGED_BY=MANAGED_BY,
    INPUT_PACK=INPUT_PACK,
    FRESHNESS_CACHE=FRESHNESS_CACHE,
    GAP_SCOPES=GAP_SCOPES,
    FRESHNESS_SCOPES=FRESHNESS_SCOPES,
    GAP_STATUSES=GAP_STATUSES,
    AUTHORSHIP_RANK=AUTHORSHIP_RANK,
    FACTS_SCHEMA=FACTS_SCHEMA,
    FACTS_KIND=FACTS_KIND,
    FACTS_TEXT_FIELDS=FACTS_TEXT_FIELDS,
    FACTS_LIST_FIELDS=FACTS_LIST_FIELDS,
    SHORTLIST_MAX=SHORTLIST_MAX,
    SHORTLIST_FLOOR=SHORTLIST_FLOOR,
    EXT_EVIDENCE_RE=EXT_EVIDENCE_RE,
    PLACEHOLDER_RE=PLACEHOLDER_RE,
    SIDECAR_EXTRACTOR_VERSIONS=SIDECAR_EXTRACTOR_VERSIONS,
    FACTS_GENERATOR_VERSIONS=FACTS_GENERATOR_VERSIONS,
    sha256_bytes=sha256_bytes,
    quote_id=quote_id,
    read_json_file=read_json_file,
    text_tokens=text_tokens,
    title_tokens=title_tokens,
    direction_machine_id=direction_machine_id,
    facts_direction_id=facts_direction_id,
    pack_paper_index=pack_paper_index,
    load_input_pack=load_input_pack,
    paper_digest=paper_digest,
    sidecar_sha=sidecar_sha,
    gap_fingerprint=gap_fingerprint,
    candidate_fingerprint=candidate_fingerprint,
    direction_relevant_keys=direction_relevant_keys,
    pack_direction_relevant_keys=pack_direction_relevant_keys,
    direction_fingerprint=direction_fingerprint
)

sidecar_analysis_matches = _stage2_facts.sidecar_analysis_matches
sidecar_path_matches = _stage2_facts.sidecar_path_matches
load_sidecar = _stage2_facts.load_sidecar
load_facts_sidecar = _stage2_facts.load_facts_sidecar
compute_version_families = _stage2_facts.compute_version_families
score_gap = _stage2_facts.score_gap
rank_gaps = _stage2_facts.rank_gaps
shortlist_size = _stage2_facts.shortlist_size
is_later_or_same_unknown = _stage2_facts.is_later_or_same_unknown
gap_related = _stage2_facts.gap_related
freshness_candidates = _stage2_facts.freshness_candidates
load_freshness_cache = _stage2_facts.load_freshness_cache
save_freshness_cache = _stage2_facts.save_freshness_cache
gap_scope_keys = _stage2_facts.gap_scope_keys
load_papers_with_digests = _stage2_facts.load_papers_with_digests
build_gap_pool = _stage2_facts.build_gap_pool
Stage2Context = _stage2_facts.Stage2Context
Stage2PackRefineContext = _stage2_facts.Stage2PackRefineContext


# Stage-2 resolve module binding point. Every helper it needs is defined by
# now; the factory receives this runner's own function objects and constants,
# so the module never builds a second channel or a second copy of a helper.
# The submit-side helpers just above stay in the runner for the next batch and
# are injected here only by value.
_stage2_resolve = _stage2_resolve_module.build(
    AUTHORSHIP_RANK=AUTHORSHIP_RANK,
    Stage2Context=Stage2Context,
    direction_candidate_keys=direction_candidate_keys,
    selected_candidate_union=selected_candidate_union,
    emit=emit,
    fail=fail,
    filename_component=filename_component,
    sha256_obj=sha256_obj,
    truncate=truncate,
    atomic_json=atomic_json,
    RESOLVED_DIRECTION_SCHEMA=RESOLVED_DIRECTION_SCHEMA,
    now_utc=now_utc,
    read_json_file=read_json_file,
    direction_provisional_member_keys=direction_provisional_member_keys)

_compute_paper_direction_affinity = _stage2_resolve._compute_paper_direction_affinity
_detect_candidates_for_addition = _stage2_resolve._detect_candidates_for_addition
_detect_candidates_for_removal = _stage2_resolve._detect_candidates_for_removal
_detect_split_candidates = _stage2_resolve._detect_split_candidates
_profile_topic_tokens = _stage2_resolve._profile_topic_tokens
_direction_fulltext_terms = _stage2_resolve._direction_fulltext_terms
_merge_fulltext_basis = _stage2_resolve._merge_fulltext_basis
_authoritative_merge_basis = _stage2_resolve._authoritative_merge_basis
_direction_has_valid_fulltext = _stage2_resolve._direction_has_valid_fulltext
_detect_merge_candidates = _stage2_resolve._detect_merge_candidates
_canonical_directory = _stage2_resolve._canonical_directory
stage2_resolve_run_id = _stage2_resolve.stage2_resolve_run_id
cmd_stage2_resolve_plan = _stage2_resolve.cmd_stage2_resolve_plan
_resolve_evidence = _stage2_resolve._resolve_evidence
_build_resolve_model_input = _stage2_resolve._build_resolve_model_input
_current_resolve_fingerprint = _stage2_resolve._current_resolve_fingerprint
validate_resolve_results = _stage2_resolve.validate_resolve_results
_load_existing_resolved = _stage2_resolve._load_existing_resolved
_facts_preflight_proof = _stage2_resolve._facts_preflight_proof
_sidecar_preflight_proof = _stage2_resolve._sidecar_preflight_proof
_check_resolved_proof_binding = _stage2_resolve._check_resolved_proof_binding
cmd_stage2_resolve_finalize = _stage2_resolve.cmd_stage2_resolve_finalize
cmd_stage2_resolve_accept = _stage2_resolve.cmd_stage2_resolve_accept

MERGE_MIN_SHARED = _stage2_resolve_module.MERGE_MIN_SHARED
MERGE_MIN_FACTS_PAPERS = _stage2_resolve_module.MERGE_MIN_FACTS_PAPERS
MERGE_MIN_SHARED_TERMS = _stage2_resolve_module.MERGE_MIN_SHARED_TERMS
MERGE_TOPIC_OVERLAP = _stage2_resolve_module.MERGE_TOPIC_OVERLAP
MERGE_VALIDATION_MIN_FACTS_PAPERS = _stage2_resolve_module.MERGE_VALIDATION_MIN_FACTS_PAPERS
MERGE_VALIDATION_MIN_SHARED_TERMS = _stage2_resolve_module.MERGE_VALIDATION_MIN_SHARED_TERMS
RESOLVE_INPUT_FINGERPRINT_VERSION = _stage2_resolve_module.RESOLVE_INPUT_FINGERPRINT_VERSION


def stage1_state_path(professor_dir: Path) -> Path:
    """Professor-local Stage-1 authority for the professor owning ``professor_dir``."""
    return Path(professor_dir) / STAGE1_STATE_FILE_NAME


def read_stage1_professor_entry(program_root: Path, professor_dir: Path, professor: str,
                                target: dict | None) -> dict | None:
    """Read one professor's own Stage-1 state, fail-closed to ``None``.

    The professor-local file is the only authority consulted here, so another
    professor's missing, corrupt or unmigrated state can never block this
    professor. The stored identity fields must agree with the already-resolved
    local target, otherwise the file is someone else's and is not used.
    """
    if not isinstance(target, dict):
        return None
    expected_dir = str(target.get("professor_dir") or "")
    if not expected_dir:
        return None
    if str((program_root / expected_dir).resolve()) != str(Path(professor_dir).resolve()):
        return None
    state_path = stage1_state_path(professor_dir)
    data, error = read_json_file(state_path)
    if error or not isinstance(data, dict):
        return None
    if (data.get("schema_version") != STAGE1_STATE_SCHEMA_VERSION
            or data.get("kind") != STAGE1_STATE_KIND):
        return None
    if "professors" in data:
        return None
    if data.get("professor") != professor:
        return None
    stored_dir = str(data.get("professor_dir") or "")
    if str((program_root / stored_dir / STAGE1_STATE_FILE_NAME).resolve()) != str(state_path.resolve()):
        return None
    if str(Path(str(data.get("preview_path") or "")).parent) != stored_dir:
        return None
    target_preview = str((target or {}).get("preview_path") or "")
    snapshot_preview = str(data.get("preview_path") or "")
    if not target_preview or not snapshot_preview:
        return None
    if str((program_root / snapshot_preview).resolve()) != str((program_root / target_preview).resolve()):
        return None
    if not isinstance(data.get("directions"), list):
        return None
    return data


def _canonical_under(program_root: Path, value) -> str | None:
    """Resolved absolute path of a program-relative or absolute value."""
    if value in (None, ""):
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = Path(program_root) / path
    try:
        return str(path.resolve())
    except OSError:
        return None


# Stage-2 preflight module binding point. All helpers it needs are defined by
# now (the three Stage-1 helpers just above stay in the runner); the factory
# receives this runner's own function objects and constants, so the module
# never builds a second channel or a second copy of any helper.
_stage2_preflight = _stage2_preflight_module.build(
    fail=fail, soft_exit=soft_exit, emit=emit, read_json_file=read_json_file,
    sha256_obj=sha256_obj, sha256_bytes=sha256_bytes, sha256_text=sha256_text,
    split_frontmatter=split_frontmatter, direction_machine_id=direction_machine_id,
    facts_direction_id=facts_direction_id, direction_relevant_keys=direction_relevant_keys,
    gap_scope_keys=gap_scope_keys, read_stage1_professor_entry=read_stage1_professor_entry,
    stage1_state_path=stage1_state_path, _canonical_under=_canonical_under,
    load_input_pack=load_input_pack, load_freshness_cache=load_freshness_cache,
    _resolve_evidence=_resolve_evidence, Stage2Context=Stage2Context,
    filename_component=filename_component, truncate=truncate,
    INPUT_PACK=INPUT_PACK, GAP_SCOPES=GAP_SCOPES, FRESHNESS_SCOPES=FRESHNESS_SCOPES,
    ANALYSIS_MD=ANALYSIS_MD, MANAGED_BY=MANAGED_BY, SHORTLIST_MAX=SHORTLIST_MAX,
    ABSTRACT_INPUT_CHARS=ABSTRACT_INPUT_CHARS, QUOTE_INPUT_CHARS=QUOTE_INPUT_CHARS,
    TRANSLATION_INPUT_CHARS=TRANSLATION_INPUT_CHARS)

stage2_preflight_versions = _stage2_preflight.stage2_preflight_versions
stage2_preflight_params = _stage2_preflight.stage2_preflight_params
stage2_target_fingerprint = _stage2_preflight.stage2_target_fingerprint
stage2_candidate_fingerprint = _stage2_preflight.stage2_candidate_fingerprint
stage2_candidate_universe = _stage2_preflight.stage2_candidate_universe
stage2_papers_catalog_view_fingerprint = _stage2_preflight.stage2_papers_catalog_view_fingerprint
stage2_authorship_ledger_view_fingerprint = _stage2_preflight.stage2_authorship_ledger_view_fingerprint
stage2_program_inputs = _stage2_preflight.stage2_program_inputs
stage2_target_path = _stage2_preflight.stage2_target_path
read_stage2_target = _stage2_preflight.read_stage2_target
stage2_local_identity = _stage2_preflight.stage2_local_identity
stage2_transaction_identity = _stage2_preflight.stage2_transaction_identity
stage2_preflight_cheap_inputs = _stage2_preflight.stage2_preflight_cheap_inputs
stage2_artifact_guard = _stage2_preflight.stage2_artifact_guard
stage2_artifact_guard_reason = _stage2_preflight.stage2_artifact_guard_reason
_artifact_guards_for_keys = _stage2_preflight._artifact_guards_for_keys
stage2_direction_artifact_guards = _stage2_preflight.stage2_direction_artifact_guards
stage2_resolution_evidence_guards = _stage2_preflight.stage2_resolution_evidence_guards
_pack_resolved_grouping = _stage2_preflight._pack_resolved_grouping
stage2_freshness_view_fingerprint = _stage2_preflight.stage2_freshness_view_fingerprint
stage2_preflight_metadata = _stage2_preflight.stage2_preflight_metadata
stage2_pack_state_fingerprint = _stage2_preflight.stage2_pack_state_fingerprint
stage2_pack_content_fingerprint = _stage2_preflight.stage2_pack_content_fingerprint
stage2_validator_accepts = _stage2_preflight.stage2_validator_accepts
cmd_stage2_preflight = _stage2_preflight.cmd_stage2_preflight
stage2_plan_bind_preflight = _stage2_preflight.stage2_plan_bind_preflight
cmd_stage2_plan = _stage2_preflight.cmd_stage2_plan

STAGE2_PREFLIGHT_VERSION = _stage2_preflight_module.STAGE2_PREFLIGHT_VERSION
STAGE2_RESOLUTION_SEMANTICS_VERSION = _stage2_preflight_module.STAGE2_RESOLUTION_SEMANTICS_VERSION
STAGE2_TARGET_FILE_NAME = _stage2_preflight_module.STAGE2_TARGET_FILE_NAME
AUTHORSHIP_LEDGER_FILE = _stage2_preflight_module.AUTHORSHIP_LEDGER_FILE
PAPER_ANALYSIS_SCOPES = _stage2_preflight_module.PAPER_ANALYSIS_SCOPES
STAGE2_GUARD_KINDS = _stage2_preflight_module.STAGE2_GUARD_KINDS


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage2_render = _stage2_render_module.build(
    fail=fail,
    GAP_STATUSES=GAP_STATUSES,
    PLACEHOLDER_RE=PLACEHOLDER_RE,
    now_utc=now_utc,
    read_json_file=read_json_file,
    truncate=truncate,
    rel_path=rel_path,
    filename_component=filename_component,
    direction_machine_id=direction_machine_id,
    pack_paper_index=pack_paper_index,
    direction_papers=direction_papers,
    direction_relevant_keys=direction_relevant_keys,
    direction_provisional_member_keys=direction_provisional_member_keys,
    shortlist_size=shortlist_size,
    Stage2Context=Stage2Context,
    Stage2PackRefineContext=Stage2PackRefineContext
)

validate_freshness_results = _stage2_render.validate_freshness_results
narrative_scope = _stage2_render.narrative_scope
validate_narrative_entry = _stage2_render.validate_narrative_entry
validate_narrative = _stage2_render.validate_narrative
citation_render = _stage2_render.citation_render
rendered_markdown_block_lines = _stage2_render.rendered_markdown_block_lines
render_positioning_block = _stage2_render.render_positioning_block
redact_item_keys = _stage2_render.redact_item_keys
build_direction_pack = _stage2_render.build_direction_pack
render_analysis_md = _stage2_render.render_analysis_md
stage2_trusted_paper_title = _stage2_render.stage2_trusted_paper_title
stage2_require_later_paper_titles = _stage2_render.stage2_require_later_paper_titles


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage2_finalize = _stage2_finalize_module.build(
    Stage2Context=Stage2Context,
    Stage2PackRefineContext=Stage2PackRefineContext,
    atomic_json=atomic_json,
    emit=emit,
    fail=fail,
    soft_exit=soft_exit,
    now_utc=now_utc,
    sha256_text=sha256_text,
    sha256_obj=sha256_obj,
    read_json_file=read_json_file,
    direction_machine_id=direction_machine_id,
    pack_paper_index=pack_paper_index,
    pack_direction_relevant_keys=pack_direction_relevant_keys,
    split_frontmatter=split_frontmatter,
    managed_write=managed_write,
    save_freshness_cache=save_freshness_cache,
    _resolve_evidence=_resolve_evidence,
    _current_resolve_fingerprint=_current_resolve_fingerprint,
    _facts_preflight_proof=_facts_preflight_proof,
    _sidecar_preflight_proof=_sidecar_preflight_proof,
    stage2_target_path=stage2_target_path,
    read_stage2_target=read_stage2_target,
    read_stage1_professor_entry=read_stage1_professor_entry,
    stage2_preflight_cheap_inputs=stage2_preflight_cheap_inputs,
    stage2_preflight_metadata=stage2_preflight_metadata,
    stage2_pack_content_fingerprint=stage2_pack_content_fingerprint,
    validate_freshness_results=validate_freshness_results,
    validate_narrative=validate_narrative,
    build_direction_pack=build_direction_pack,
    render_analysis_md=render_analysis_md,
    MANAGED_BY=MANAGED_BY,
    INPUT_PACK_SCHEMA=INPUT_PACK_SCHEMA,
    DIRECTION_IDENTITY_VERSION=DIRECTION_IDENTITY_VERSION,
    INPUT_PACK_KIND=INPUT_PACK_KIND,
    RESOLVED_DIRECTION_SCHEMA=RESOLVED_DIRECTION_SCHEMA,
    ANALYSIS_MD=ANALYSIS_MD,
    STAGE2_RESOLUTION_SEMANTICS_VERSION=STAGE2_RESOLUTION_SEMANTICS_VERSION,
    PLACEHOLDER_RE=PLACEHOLDER_RE,
    stage2_trusted_paper_title=stage2_trusted_paper_title,
    stage2_require_later_paper_titles=stage2_require_later_paper_titles)

stage2_preflight_plan_drift = _stage2_finalize.stage2_preflight_plan_drift
stage2_finalize_preflight_plan = _stage2_finalize.stage2_finalize_preflight_plan
stage2_pack_requires_membership_rebuild = _stage2_finalize.stage2_pack_requires_membership_rebuild
stage2_old_pack_gap_statuses = _stage2_finalize.stage2_old_pack_gap_statuses
stage2_render_state = _stage2_finalize.stage2_render_state
stage2_require_paper_reference_titles = _stage2_finalize.stage2_require_paper_reference_titles
cmd_stage2_finalize = _stage2_finalize.cmd_stage2_finalize


def profile_fingerprint(profile_path: str | None) -> str | None:
    if not profile_path:
        return None
    path = Path(profile_path)
    if not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


def load_profile_text(profile_path: str | None, limit: int = PROFILE_INPUT_CHARS) -> str | None:
    if not profile_path:
        return None
    path = Path(profile_path)
    if not path.is_file():
        return None
    return truncate(path.read_text(encoding="utf-8"), limit)


def _direction_slices(pack: dict, direction: dict) -> tuple[dict, dict, dict]:
    """Exact-join indexes for one pack direction slice (issue #8 §5).

    gap/blacklist indexes are keyed by the exact provenance triple
    (direction_id, item_key, gap_id): a valid (item_key, gap_id) that exists in
    ANOTHER direction can never join through the wrong direction_id. The paper
    index is keyed by item_key over the direction's canonical universe
    (supporting_item_keys ∪ gap item keys) resolved from the professor-level
    papers map.
    """
    did = direction_machine_id(direction)
    gap_index = {}
    for gap in direction.get("gap_shortlist", []) + [
            dict(g, status=g.get("status")) for g in direction.get("gaps_excluded", [])]:
        gap_index[(did, gap["item_key"], gap["gap_id"])] = gap
    blacklist = {(did, b["item_key"], b["gap_id"]): b
                 for b in direction.get("completed_gap_blacklist", [])}
    paper_index = {p["item_key"]: p for p in direction_papers(pack, direction)}
    for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
        paper_index.setdefault(gap["item_key"], {
            "item_key": gap["item_key"], "title": gap.get("paper_title"),
            "year": gap.get("paper_year"), "authorship": gap.get("authorship")})
    return gap_index, blacklist, paper_index


def _cross_group_fresh(group: dict, pack_fps: dict,
                       current_profile_fp: str | None) -> bool:
    """A cross-direction group survives only while EVERY participant's pack
    fingerprint and the profile are unchanged; unknown participants never
    count as fresh."""
    recorded = group.get("direction_fingerprints")
    if not isinstance(recorded, dict) or not recorded:
        return False
    if group.get("profile_fingerprint") != current_profile_fp:
        return False
    return all(pack_fps.get(pid) == fingerprint
               for pid, fingerprint in recorded.items())


def _parse_direction_id_list(raw: str | None, param: str) -> list[str]:
    values = [v.strip() for v in (raw or "").split(",") if v.strip()]
    seen, out = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _parse_cross_groups(raw: Any, pack_directions: list) -> list[dict]:
    """Validate + normalize explicit cross_direction_groups input.

    Default (absent/empty) means NO cross work at all. Each group needs >=2
    distinct existing direction IDs; IDs are sorted/deduped for stable
    identity and duplicate groups are collapsed deterministically.
    """
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            fail("invalid_params", f"cross_direction_groups must be JSON: {exc}")
    if not isinstance(raw, list):
        fail("invalid_params", "cross_direction_groups must be a list of ID lists")
    known = {direction_machine_id(d) for d in pack_directions}
    groups: dict[tuple, list[str]] = {}
    for index, group in enumerate(raw):
        if not isinstance(group, list) or any(not isinstance(x, str) or not x.strip()
                                              for x in group):
            fail("invalid_params",
                 f"cross_direction_groups[{index}] must be a list of direction ID strings")
        ids = sorted({x.strip() for x in group})
        if len(ids) < 2:
            fail("invalid_params",
                 f"cross_direction_groups[{index}] needs >=2 distinct direction IDs")
        unknown = [x for x in ids if x not in known]
        if unknown:
            fail("invalid_params",
                 f"cross_direction_groups[{index}] cites unknown direction IDs: {unknown}")
        groups[tuple(ids)] = ids
    return [{"group_id": cross_group_id(ids), "direction_ids": list(ids)}
            for ids in groups.values()]


# Issue #66 r13 §5.1: the runner-generated per-invocation credential. It
# freezes the first-round parse (sources + first-round controls) so a
# correction sub-thread never re-derives professor/profile/scope arguments.
STAGE3_INVOCATION_VERSION = "stage3-invocation-v1"
STAGE3_INVOCATION_FILE = "stage3-invocation.json"
# Issue #66 r13 §6: the mechanical validation-evidence handoff. The validator
# writes its one raw output file; the root saves those exact bytes to the
# recorded target and records that same file. All three files live in the
# per-professor, per-invocation, per-round handoff directory under the system
# temporary root — never inside the professor state directory.
STAGE3_HANDOFF_VERSION = "stage3-handoff-v1"
STAGE3_HANDOFF_ROOT = "professor-contact-stage3-handoff"
STAGE3_HANDOFF_FILE = "handoff.json"
STAGE3_VALIDATOR_OUTPUT_FILE = "validator-output.json"
STAGE3_VALIDATION_TARGET_FILE = "validation-result.json"






def _stage3_bound_render(professor_dir: Path, state: dict) -> tuple[str, str]:
    """Current rendered candidate text, bound to the revision the state records."""
    cache = (state or {}).get("cache")
    recorded = cache.get("render", {}).get(CANDIDATES_MD, {}).get("sha256") \
        if isinstance(cache, dict) and isinstance(cache.get("render"), dict) else None
    path = professor_dir / CANDIDATES_MD
    try:
        body = split_frontmatter(path.read_text(encoding="utf-8"))[1]
    except (OSError, UnicodeDecodeError) as exc:
        fail("validation_render_missing", f"{path}: {exc}")
    current = sha256_text(body)
    if not recorded or current != recorded:
        fail("validation_render_stale",
             f"{path}: validator evidence must bind the candidate revision recorded in "
             f"{professor_dir / CANDIDATE_STATE}; re-run the style validator on the current render")
    return current, body




def _stage3_candidates_entry(data: Any, path: Path, professor_dir: Path) -> tuple[dict, str, list]:
    """Shape-check raw style-validator JSON and return the one candidates entry
    bound to this professor's rendered document, with its verdict and issues.

    Shared by the record entry (r13 §6.4) and the save entry (r13 §6.3); per
    §6.5 the remaining ``files`` entries may belong to other professors of a
    batch call and are not this professor's precondition.
    """
    files = _stage3_validation_files(data, path, fail=fail)
    target = (professor_dir / CANDIDATES_MD).resolve()
    matches = []
    for entry in files:
        if not isinstance(entry, dict) or entry.get("artifact") != "candidates":
            continue
        try:
            candidate_path = Path(entry.get("file") or "").resolve()
        except (OSError, ValueError):
            continue
        if candidate_path == target:
            matches.append(entry)
    if len(matches) != 1:
        fail("invalid_validation_json",
             f"validator output must contain exactly one candidates result for {target}")
    entry = matches[0]
    verdict = entry.get("verdict")
    if verdict not in ("pass", "pass_with_minor", "fail"):
        fail("invalid_validation_json",
             f"candidates verdict must be pass|pass_with_minor|fail: {verdict!r}")
    issues = entry.get("issues")
    if not isinstance(issues, list) or not all(isinstance(i, dict) for i in issues):
        fail("invalid_validation_json", "candidates validation issues must be an object list")
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    if verdict == "fail" and not blocking:
        fail("invalid_validation_json", "fail verdict needs at least one blocking issue")
    if verdict != "fail" and blocking:
        fail("invalid_validation_json", "blocking issues require verdict=fail")
    return entry, verdict, issues




def stage3_validation_evidence(path: Path, professor_dir: Path, state: dict, *,
                               raw_input: bytes | None = None) -> dict:
    """Normalize raw style-validator JSON into bound, machine-scoped evidence.

    This is the only Stage-3 validator handoff: the runner reads the validator's
    own output, binds it to the exact rendered revision, and routes each finding
    to the canonical scope whose rendered text contains the quoted fragment.  A
    caller never translates ``files[].verdict`` into ``results[]``.  The handoff
    mode (r13 §6.4) passes the already digest-checked byte buffer as
    ``raw_input`` so the digest is proven over the exact bytes parsed here —
    never a snapshot re-opened afterwards.
    """
    if raw_input is None:
        try:
            raw_input = path.read_bytes()
        except (OSError, ValueError):
            fail("invalid_validation_json", f"style-validator output unreadable: {path}")
    input_sha = sha256_bytes(raw_input)
    try:
        data = json.loads(raw_input.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        data = None
    _entry, verdict, issues = _stage3_candidates_entry(data, path, professor_dir)
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    render_sha, body = _stage3_bound_render(professor_dir, state)
    scopes = stage3_render_line_scopes(body)
    rendered = {}
    for scope in scopes:
        if scope:
            rendered.setdefault(scope_key(scope), {k: v for k, v in scope.items()
                                                   if k != "candidate_id"})
    failed: dict = {}
    for issue in blocking:
        for scope in _stage3_issue_scopes(issue, body, scopes, path, fail=fail):
            key = scope_key(scope)
            row = failed.setdefault(key, {"scope": {k: v for k, v in scope.items()
                                                    if k != "candidate_id"},
                                          "candidate_ids": [], "issues": []})
            row["issues"].append({**issue, "scope": scope, "render_sha256": render_sha})
            if scope.get("candidate_id") and scope["candidate_id"] not in row["candidate_ids"]:
                row["candidate_ids"].append(scope["candidate_id"])
    return {
        "verdict": verdict,
        "render_sha256": render_sha,
        "validation_input_sha256": input_sha,
        "scopes": rendered,
        "failed": failed,
        "issues": issues,
        "blocking": blocking,
    }


def stage3_correction_scopes(state: dict, evidence: dict) -> list:
    """Scopes a correction round may repair, from recorded evidence only.

    The validator file supplied to a correction command is not authoritative:
    the persisted pending rows are the record of which scopes and issues may be
    repaired.  The current evidence is used only to bind the operation to the
    same rendered revision.
    """
    validator = state.get("validator") if isinstance(state.get("validator"), dict) else {}
    recorded = validator.get("pending") if isinstance(validator.get("pending"), dict) else {}
    if validator.get("render_sha256") != evidence.get("render_sha256"):
        fail("validation_evidence_not_recorded",
             "record this validator round with stage3-record-validation before planning a correction")
    if evidence["failed"] and not recorded:
        fail("validation_evidence_not_recorded",
             "the recorded round has no open findings on this render: re-run the style validator "
             "on the current render and record that round")
    scopes = {}
    for key, row in recorded.items():
        if not isinstance(row, dict):
            fail("validation_evidence_not_recorded",
                 f"recorded validator scope is malformed: {key}")
        scope = row.get("scope")
        issues = row.get("issues")
        candidate_ids = row.get("candidate_ids")
        if not isinstance(scope, dict) or scope_key(scope) != key \
                or scope.get("kind") not in ("direction", "group") \
                or not isinstance(issues, list) or not issues \
                or not isinstance(candidate_ids, list) \
                or row.get("render_sha256") != evidence["render_sha256"]:
            fail("validation_evidence_not_recorded",
                 f"recorded validator scope is malformed or stale: {key}")
        scopes[key] = {"scope": scope, "candidate_ids": candidate_ids,
                       "issues": issues}
    return [scopes[key] for key in sorted(scopes)]


def stage3_repairable_correction_directions(correction: dict,
                                            directions: dict) -> set[str]:
    """Directions with candidate state that a correction can replace.

    Recorded scopes remain in ``correction`` even when their direction was
    skipped. A skipped, candidate-less direction is still part of the recorded
    validation scope, but it must not become a generator job or result input.
    """
    return {
        key.split(":", 1)[1]
        for key in correction
        if key.startswith("direction:")
        and isinstance(directions.get(key.split(":", 1)[1]), dict)
        and directions[key.split(":", 1)[1]].get("stage3_status") == "ready"
        and directions[key.split(":", 1)[1]].get("candidates")
    }


def carry_stage3_validator(old_validator: dict, processed_scopes: set, *,
                           correction: bool, render_sha: str | None) -> dict | None:
    """Rewrite the recorded validator block after the render is replaced.

    Every record binds the render it was produced from, so a scope whose text was
    rewritten loses its old proof and must be validated again.  A correction
    round keeps the round counter — the next recorded round is the terminal one
    for that render — while any other re-render starts a fresh bounded cycle.
    Records for scopes this run did not touch stay valid.
    """
    results = {ident: row for ident, row in (old_validator.get("results") or {}).items()
               if f"direction:{ident}" not in processed_scopes}
    groups = {ident: row for ident, row in (old_validator.get("groups") or {}).items()
              if f"group:{ident}" not in processed_scopes}
    if not results and not groups and not correction:
        return None
    return {
        "round": int(old_validator.get("round") or 0) if correction else 0,
        "render_sha256": render_sha if correction else None,
        "raw_verdict": old_validator.get("raw_verdict") if correction else None,
        "results": results,
        "groups": groups,
        "pending": {},
        "global": (old_validator.get("global") or []) if correction else [],
        "updated_at": old_validator.get("updated_at"),
    }


def stage3_current_result(direction: dict) -> dict:
    return {
        "schema": 2,
        "kind": "candidates",
        "direction_id": direction.get("direction_id"),
        "mode": direction.get("mode"),
        "refined": direction.get("refined"),
        "priority": direction.get("priority") or "",
        "candidates": direction.get("candidates") or [],
    }


STAGE3_IMMUTABLE_CANDIDATE_FIELDS = ("id", "kind", "direction_ids", "origin", "gap_refs",
                                     "anchor_type", "anchor_notes", "fit", "red_lines")
STAGE3_REPAIRABLE_CANDIDATE_FIELDS = ("title", "one_liner", "research_question", "points",
                                      "fit_note", "why_recommended", "tension_points")


def _paper_refs(candidate: dict) -> list:
    return [{"item_key": paper.get("item_key"),
             "direction_ids": paper.get("direction_ids") or []}
            for paper in (candidate.get("papers") or []) if isinstance(paper, dict)]


def require_stage3_correction_invariants(old: dict, new: dict, path: Path,
                                         named_candidates: list | None = None) -> None:
    """A style retry repairs prose the validator may reject, never machine facts.

    Red-line presentation and refined grounding IDs are deliberately excluded
    from the repairable set: the renderer owns their label and dedup rules, so
    asking the model to change them would create findings it is forbidden to
    fix.  ``priority`` and the refined prose fields are repairable precisely
    because the style validator is authorized to reject them.
    """
    if old.get("mode") != new.get("mode"):
        fail("validation_correction_changed_machine_facts",
             f"{path}: correction changed mode")
    old_refined, new_refined = old.get("refined") or {}, new.get("refined") or {}
    if bool(old.get("refined")) != bool(new.get("refined")):
        fail("validation_correction_changed_machine_facts",
             f"{path}: correction changed the presence of the refined block")
    if old_refined.get("gap_ids") != new_refined.get("gap_ids"):
        fail("validation_correction_changed_machine_facts",
             f"{path}: correction changed refined.gap_ids grounding")
    old_candidates = old.get("candidates") or []
    new_candidates = new.get("candidates") or []
    if [c.get("id") for c in old_candidates] != [c.get("id") for c in new_candidates]:
        fail("validation_correction_changed_machine_facts",
             f"{path}: correction changed candidate IDs or order")
    named = set(named_candidates or [])
    for before, after in zip(old_candidates, new_candidates):
        cid = before.get("id")
        changed = [field for field in STAGE3_IMMUTABLE_CANDIDATE_FIELDS
                   if before.get(field) != after.get(field)]
        if _paper_refs(before) != _paper_refs(after):
            changed.append("papers(item_key/direction_ids)")
        if changed:
            fail("validation_correction_changed_machine_facts",
                 f"{path}: candidate {cid} changed {changed}")
        touched = [field for field in STAGE3_REPAIRABLE_CANDIDATE_FIELDS
                   if before.get(field) != after.get(field)]
        for paper_before, paper_after in zip(before.get("papers") or [],
                                             after.get("papers") or []):
            for field in ("role", "fit_note"):
                if (paper_before or {}).get(field) != (paper_after or {}).get(field):
                    touched.append(f"papers[{(paper_before or {}).get('item_key')}].{field}")
        if touched and cid not in named:
            fail("validation_correction_changed_untouched_candidate",
                 f"{path}: candidate {cid} rewrote {touched} without a validator finding")


def _stage3_selected_scope_keys(selection_path: Path, professor_dir: Path,
                                by_ckey: dict) -> set:
    """Selected-refresh scope from one explicit professor-local selection container.

    An explicit ``--selection`` is ONE professor's own container (issue #67): the
    container's top-level canonical ``professor_dir`` and every row's canonical
    ``professor_dir`` must equal the current professor directory before any
    direction is consumed. A missing, unresolvable or foreign identity fails the
    refresh before task generation or any formal write — never silently skipped,
    rebound to the container's directory, or accepted on the top-level check
    alone. Direction reading keeps the exact machine relation (canonical
    ``direction_ids`` first, deprecated ``direction_id`` / ``collection_key``
    through the pack's unique mapping); the display name never filters rows."""
    selection_data, sel_error = read_json_file(Path(selection_path))
    if sel_error:
        fail("invalid_params", f"selection file unreadable: {selection_path}")
    if not isinstance(selection_data, dict):
        fail("invalid_selection",
             f"selection container must be an object: {selection_path}")
    canonical = canonical_professor_dir(professor_dir)
    container_dir = selection_data.get("professor_dir")
    if not str(container_dir or "").strip() \
            or canonical_professor_dir(container_dir) != canonical:
        fail("selection_scope_mismatch",
             f"selection container {selection_path} is bound to "
             f"{container_dir or 'no professor_dir'}, not the current professor "
             f"directory {professor_dir}")
    rows = selection_data.get("selections")
    if not isinstance(rows, list):
        fail("invalid_selection",
             f"selection container selections must be a list: {selection_path}")
    selected_keys = set()
    for index, sel in enumerate(rows):
        if not isinstance(sel, dict):
            fail("invalid_selection",
                 f"selections[{index}] in {selection_path} must be an object")
        row_dir = sel.get("professor_dir")
        if not str(row_dir or "").strip() \
                or canonical_professor_dir(row_dir) != canonical:
            fail("selection_scope_mismatch",
                 f"selections[{index}] in {selection_path} carries professor_dir "
                 f"{row_dir or 'missing'}; a professor-local container may only hold "
                 "rows bound to the same canonical directory")
        scope = sel.get("direction_ids")
        if isinstance(scope, list) and scope:
            selected_keys.update(str(did) for did in scope if did)
            continue
        sel_did = sel.get("direction_id")
        if not sel_did:
            legacy = by_ckey.get(sel.get("collection_key"))
            sel_did = direction_machine_id(legacy) if legacy is not None else None
        if sel_did:
            selected_keys.add(sel_did)
    return selected_keys
# --- Issue #66 r13 §5: per-invocation credential production/consumption ----

def _write_stage3_invocation(directory: str, payload: dict) -> tuple[str, str]:
    """Create this invocation's credential file exclusively (r13 §5.1).

    The caller owns a per-invocation temporary directory; the credential file
    inside it must be created with O_EXCL so a reused directory can never
    silently overwrite an earlier credential.  The returned digest is the
    SHA-256 of the exact bytes written; the file is never modified afterwards.
    """
    dir_path = Path(directory)
    if dir_path.exists() and not dir_path.is_dir():
        fail("invalid_params",
             f"--capture-invocation must name a directory: {directory}")
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        fail("invalid_params", f"--capture-invocation is unusable: {exc}")
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
            + "\n").encode("utf-8")
    target = dir_path / STAGE3_INVOCATION_FILE
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        fail("invalid_params",
             f"--capture-invocation file already exists (the directory must be "
             f"exclusive to this invocation): {target}")
    except OSError as exc:
        fail("invalid_params", f"--capture-invocation is unusable: {exc}")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return str(target), sha256_bytes(data)


STAGE3_INVOCATION_SOURCE_PARAMS = ("professor_dir", "program_root", "profile",
                                   "refresh_scope", "skip_direction_ids",
                                   "cross_direction_groups", "direction_id",
                                   "collection_key", "selection")


def _read_stage3_invocation(args) -> dict | None:
    """Load + verify the invocation credential, or return None (r13 §5.2).

    Refuses the credential mode outright when any first-round source/control
    parameter is re-supplied (mutual exclusion, no precedence), when only one
    half of the file/digest pair is given, when the file is damaged, when the
    version is unsupported, or when the digest does not match the bytes this
    invocation actually read — all before any candidate or state write.
    """
    file_arg = getattr(args, "invocation_file", None)
    sha_arg = getattr(args, "invocation_sha256", None)
    if bool(file_arg) != bool(sha_arg):
        fail("invalid_params",
             "--invocation-file and --invocation-sha256 must be used together")
    if not file_arg:
        return None
    if getattr(args, "capture_invocation", None):
        fail("invalid_params",
             "--capture-invocation produces a first-round credential and cannot "
             "be combined with --invocation-file")
    replayed = [name for name in STAGE3_INVOCATION_SOURCE_PARAMS
                if getattr(args, name, None) is not None]
    if replayed:
        fail("invalid_params",
             f"--invocation-file is mutually exclusive with {replayed}; the "
             "credential alone carries the first-round sources and controls")
    try:
        raw = Path(file_arg).read_bytes()
    except (OSError, ValueError):
        fail("invalid_invocation", f"invocation file unreadable: {file_arg}")
    if sha_arg != sha256_bytes(raw):
        fail("invocation_sha256_mismatch",
             f"invocation digest does not match the bytes read: {file_arg}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("invalid_invocation", f"invocation file is not valid JSON: {file_arg}")
    if not isinstance(payload, dict):
        fail("invalid_invocation", f"invocation file must hold a JSON object: {file_arg}")
    if payload.get("version") != STAGE3_INVOCATION_VERSION:
        fail("invocation_version_unsupported",
             f"invocation version {payload.get('version')!r} is not supported "
             f"(expected {STAGE3_INVOCATION_VERSION!r}); re-run the first-round "
             "stage3-plan to produce a fresh credential")
    professor_dir = payload.get("professor_dir")
    program_root = payload.get("program_root")
    for name, value in (("professor_dir", professor_dir), ("program_root", program_root)):
        if not isinstance(value, str) or not value.strip():
            fail("invalid_invocation", f"invocation {name} is missing or not a path")
    # Directory ownership: the credential binds the professor to its program.
    require_professor_dir_under_program(Path(professor_dir), Path(program_root))
    return payload


def _require_invocation_source(invocation: dict) -> None:
    """The recorded profile digest must still match the real input (r13 §5.2)."""
    recorded_sha = invocation.get("profile_sha256")
    if profile_fingerprint(invocation.get("profile_path")) != recorded_sha:
        soft_exit("needs_refresh", "validation_source_changed",
                  message="调用凭据记录的资料摘要与实际资料不符：重新执行首轮 "
                          "stage3-plan 生成新凭据；未修改任何文件。")


# --- Issue #66 r13 §6: validation handoff prepare/save/record ---------------


def _stage3_handoff_directory(
        professor_dir: Path, invocation_file: str | Path, round_no: int) -> Path:
    """This professor's, invocation's and round's exclusive handoff directory.

    The canonical invocation credential path identifies the captured call:
    separate calls may contain identical credential bytes, so their content
    digest alone cannot distinguish them. A repeated prepare for the same
    credential and round still resolves to the same directory and collides.
    """
    professor_token = sha256_text(str(Path(professor_dir).resolve()))[:16]
    invocation_token = sha256_text(str(Path(invocation_file).resolve()))
    return (Path(tempfile.gettempdir()) / STAGE3_HANDOFF_ROOT / professor_token /
            invocation_token / f"round-{round_no}")


def _load_stage3_handoff(args) -> dict:
    """Load + verify the handoff metadata and its invocation credential.

    Shared by save (r13 §6.3) and record (r13 §6.4): the metadata digest is
    checked against the exact bytes read, every binding must be present, and
    the referenced invocation credential must still be the same bytes with a
    supported version and matching professor ownership.  The caller never
    supplies source, target or professor through other parameters.
    """
    try:
        raw = Path(args.handoff_file).read_bytes()
    except (OSError, ValueError):
        fail("invalid_handoff", f"handoff file unreadable: {args.handoff_file}")
    if args.handoff_sha256 != sha256_bytes(raw):
        fail("handoff_sha256_mismatch",
             f"handoff digest does not match the bytes read: {args.handoff_file}")
    try:
        metadata = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("invalid_handoff", f"handoff file is not valid JSON: {args.handoff_file}")
    if not isinstance(metadata, dict):
        fail("invalid_handoff", f"handoff file must hold a JSON object: {args.handoff_file}")
    if metadata.get("version") != STAGE3_HANDOFF_VERSION:
        fail("invalid_handoff",
             f"handoff version {metadata.get('version')!r} is not supported "
             f"(expected {STAGE3_HANDOFF_VERSION!r})")
    for name in ("professor_dir", "program_root", "candidates_md", "invocation_file",
                 "invocation_sha256", "output_file", "validation_file", "render_sha256"):
        value = metadata.get(name)
        if not isinstance(value, str) or not value.strip():
            fail("invalid_handoff", f"handoff {name} is missing or not a path")
    round_no = metadata.get("round")
    if isinstance(round_no, bool) or round_no not in (1, 2):
        fail("invalid_handoff", f"handoff round must be 1 or 2: {round_no!r}")
    try:
        credential_raw = Path(metadata["invocation_file"]).read_bytes()
    except (OSError, ValueError):
        fail("invalid_handoff",
             f"handoff invocation credential unreadable: {metadata['invocation_file']}")
    if metadata["invocation_sha256"] != sha256_bytes(credential_raw):
        fail("invalid_handoff",
             f"handoff invocation credential no longer matches its recorded digest: "
             f"{metadata['invocation_file']}")
    try:
        credential = json.loads(credential_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("invalid_handoff", "handoff invocation credential is not valid JSON")
    if not isinstance(credential, dict) \
            or credential.get("version") != STAGE3_INVOCATION_VERSION:
        fail("invalid_handoff", "handoff invocation credential version is not supported")
    if credential.get("professor_dir") != metadata["professor_dir"] \
            or credential.get("program_root") != metadata["program_root"]:
        fail("invalid_handoff",
             "handoff professor/program bindings do not match the invocation credential")
    require_professor_dir_under_program(Path(metadata["professor_dir"]),
                                        Path(metadata["program_root"]))
    if Path(metadata["candidates_md"]).resolve() != \
            (Path(metadata["professor_dir"]) / CANDIDATES_MD).resolve():
        fail("invalid_handoff",
             "handoff candidates_md is not this professor's rendered candidate document")
    return metadata


def cmd_stage3_prepare_validation(args) -> None:
    """r13 §6.1: prepare this round's one-time validation handoff.

    Reads only the invocation credential, the professor's committed candidate
    state and the bound candidate document; commits and changes nothing.  The
    handoff metadata, the validator output path and the saved target path live
    in a per-professor, per-invocation, per-round exclusive directory under the
    system temporary root — never inside the professor state directory.
    """
    invocation = _read_stage3_invocation(args)
    if invocation is None:
        fail("invalid_params",
             "stage3-prepare-validation needs an invocation credential "
             "(--invocation-file + --invocation-sha256)")
    _require_invocation_source(invocation)
    professor_dir = Path(invocation["professor_dir"])
    program_root = Path(invocation["program_root"])
    require_professor_dir_under_program(professor_dir, program_root)
    round_no = args.round
    pack, pack_error = load_input_pack(professor_dir)
    if pack is None:
        fail("missing_input_pack", f"{professor_dir / INPUT_PACK}: {pack_error}")
    state, state_error = load_candidate_state(professor_dir, pack)
    if state_error or state is None:
        fail("missing_candidate_state",
             f"candidate state unreadable: {professor_dir / CANDIDATE_STATE}")
    render_sha, _body = _stage3_bound_render(professor_dir, state)
    _require_stage3_handoff_round(state, render_sha, round_no, fail=fail)
    directory = _stage3_handoff_directory(
        professor_dir, args.invocation_file, round_no)
    output_file = directory / STAGE3_VALIDATOR_OUTPUT_FILE
    validation_file = directory / STAGE3_VALIDATION_TARGET_FILE
    handoff_file = directory / STAGE3_HANDOFF_FILE
    try:
        directory.mkdir(parents=True)
    except FileExistsError:
        fail("validation_handoff_collision",
             f"the handoff directory for this professor, invocation and round "
             f"already exists; earlier round results are never reused: {directory}")
    except OSError as exc:
        fail("validation_handoff_collision", f"handoff directory is unusable: {exc}")
    for label, target in (("output_file", output_file),
                          ("validation_file", validation_file),
                          ("handoff_file", handoff_file)):
        if target.is_symlink() or target.exists():
            fail("validation_handoff_collision",
                 f"{label} already exists; the handoff directory must stay exclusive "
                 f"to this professor, invocation and round: {target}")
    metadata = {
        "version": STAGE3_HANDOFF_VERSION,
        "professor_dir": str(professor_dir.resolve()),
        "program_root": str(program_root.resolve()),
        "candidates_md": str((professor_dir / CANDIDATES_MD).resolve()),
        "invocation_file": str(Path(args.invocation_file).resolve()),
        "invocation_sha256": args.invocation_sha256,
        "round": round_no,
        "render_sha256": render_sha,
        "output_file": str(output_file),
        "validation_file": str(validation_file),
    }
    data = (json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=1)
            + "\n").encode("utf-8")
    try:
        fd = os.open(handoff_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as exc:
        fail("validation_handoff_collision", f"handoff file cannot be created: {exc}")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        handoff_file.unlink(missing_ok=True)
        raise
    emit({
        "status": "ok",
        "professor": pack.get("professor"),
        "professor_dir": str(professor_dir),
        "candidates_md": str((professor_dir / CANDIDATES_MD).resolve()),
        "round": round_no,
        "render_sha256": render_sha,
        "handoff_file": str(handoff_file),
        "handoff_sha256": sha256_bytes(data),
        "output_file": str(output_file),
        "validation_file": str(validation_file),
    })










def cmd_stage3_write_validation(args) -> None:
    """Create the fixed Stage-3 validator handoff from its complete JSON result."""
    if (args.output_file is None) == (args.output_map_json is None):
        fail("invalid_params", "provide exactly one of --output-file or --output-map-json")
    if args.result_json is None or not args.result_json:
        fail("invalid_validation_json", "--result-json must contain the complete JSON result")
    try:
        data = json.loads(args.result_json,
                          object_pairs_hook=_stage3_json_object_pairs,
                          parse_constant=_stage3_json_reject_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        fail("invalid_validation_json", f"--result-json is invalid: {exc}")
    if not isinstance(data, dict):
        fail("invalid_validation_json", "--result-json must be a JSON object")
    entries = _stage3_complete_write_result(data, Path("--result-json"), fail=fail)
    candidate_entries = [(candidate_path, entry) for candidate_path, entry in entries
                         if entry.get("artifact") == "candidates"]

    output_pairs: list[tuple[str, str]] = []
    if args.output_file is not None:
        if len(candidate_entries) != 1:
            fail("invalid_params", "--output-file requires exactly one candidates entry")
        output_pairs.append((candidate_entries[0][0], args.output_file))
    else:
        try:
            mapping = json.loads(args.output_map_json,
                                 object_pairs_hook=_stage3_json_object_pairs,
                                 parse_constant=_stage3_json_reject_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            fail("invalid_params", f"--output-map-json is invalid: {exc}")
        if not isinstance(mapping, list) or not mapping:
            fail("invalid_params", "--output-map-json must be a non-empty JSON list")
        expected_paths = {candidate_path for candidate_path, _entry in candidate_entries}
        mapped_paths = set()
        for index, item in enumerate(mapping):
            if not isinstance(item, dict) or set(item) != {"file", "output_file"}:
                fail("invalid_params",
                     f"--output-map-json[{index}] must contain only file and output_file")
            candidate_path = _stage3_normalized_absolute_path(
                item.get("file"), f"--output-map-json[{index}].file", fail=fail)
            if candidate_path in mapped_paths:
                fail("invalid_params", f"duplicate candidate path in output map: {candidate_path}")
            if candidate_path not in expected_paths:
                fail("invalid_params", f"output map contains an unrelated candidate path: {candidate_path}")
            mapped_paths.add(candidate_path)
            output_pairs.append((candidate_path, item.get("output_file")))
        if mapped_paths != expected_paths:
            missing = sorted(expected_paths - mapped_paths)
            fail("invalid_params", "--output-map-json must map every candidates entry exactly once",
                 missing_files=missing)

    targets: list[Path] = []
    normalized_targets = set()
    for candidate_path, output_value in output_pairs:
        target_value = _stage3_normalized_absolute_path(output_value, "output_file", fail=fail)
        target = Path(output_value)
        if target_value in normalized_targets:
            fail("invalid_params", f"output paths must be unique: {output_value}")
        normalized_targets.add(target_value)
        if os.path.lexists(target):
            fail("validation_handoff_collision", f"output target already exists: {output_value}",
                 failed_path=output_value, completed_paths=[])
        if not target.parent.is_dir():
            fail("invalid_output_path", f"output parent directory must already exist: {target.parent}",
                 failed_path=output_value, completed_paths=[])
        targets.append(target)

    try:
        raw = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1,
                          allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        fail("invalid_validation_json", f"validator result cannot be serialized as UTF-8: {exc}")
    if not raw:
        fail("invalid_validation_json", "validator result serialized to an empty buffer")

    completed = []
    for target in targets:
        try:
            _stage3_write_buffer(target, raw)
        except OSError as exc:
            fail("validation_write_failed", f"cannot write validator result: {exc}",
                 failed_path=str(target), reason=str(exc), completed_paths=completed)
        completed.append(str(target))

    try:
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
    except OSError as exc:
        fail("validation_output_failed", f"cannot write validator result to stdout: {exc}",
             failed_path=None, reason=str(exc), completed_paths=completed)


def cmd_stage3_save_validation(args) -> None:
    """r13 §6.3: copy the validator's raw output bytes to the recorded target.

    Source, target, professor and round all come from the verified handoff
    metadata; the caller cannot pass content, another source or another
    target.  One read of the regular (non-symlink) source fixes the byte
    buffer that is validated, then written unchanged — no re-serialization,
    no field sorting, no whitespace edits — to a target created exclusively.
    A normal failure removes only a target this entry created itself and
    never deletes the source, the credential or committed professor files.
    """
    metadata = _load_stage3_handoff(args)
    professor_dir = Path(metadata["professor_dir"])
    round_no = metadata["round"]
    pack, pack_error = load_input_pack(professor_dir)
    if pack is None:
        fail("missing_input_pack", f"{professor_dir / INPUT_PACK}: {pack_error}")
    state, state_error = load_candidate_state(professor_dir, pack)
    if state_error or state is None:
        fail("missing_candidate_state",
             f"candidate state unreadable: {professor_dir / CANDIDATE_STATE}")
    render_sha, _body = _stage3_bound_render(professor_dir, state)
    if render_sha != metadata["render_sha256"]:
        fail("validation_render_changed",
             "the committed candidate render changed since this handoff was prepared; "
             "re-run stage3-prepare-validation on the current render")
    _require_stage3_handoff_round(state, render_sha, round_no, fail=fail)
    source = Path(metadata["output_file"])
    target = Path(metadata["validation_file"])
    if source.is_symlink() or not source.is_file():
        fail("invalid_validation_source",
             f"the validator output must be this round's regular source file: {source}")
    if target.is_symlink() or target.exists():
        fail("validation_handoff_collision",
             f"the validation target already exists: {target}")
    try:
        raw = source.read_bytes()
    except (OSError, ValueError):
        fail("invalid_validation_source", f"validator output unreadable: {source}")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("invalid_validation_json",
             f"validator output is not complete UTF-8 JSON: {source}")
    _entry, _verdict, _issues = _stage3_candidates_entry(data, source, professor_dir)
    if not isinstance(data.get("notes"), str):
        fail("invalid_validation_json",
             f"validator output must hold the complete result/files/notes structure: {source}")
    created = False
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException as exc:
        # A normal failure removes only the unfinished target this entry
        # created; sources, credentials and committed files stay untouched.
        if created:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
        if isinstance(exc, OSError):
            fail("validation_handoff_collision",
                 f"validation target cannot be created: {exc}")
        raise
    emit({
        "status": "ok",
        "professor": pack.get("professor"),
        "professor_dir": str(professor_dir),
        "round": round_no,
        "render_sha256": render_sha,
        "validation_file": str(target),
        "validation_sha256": sha256_bytes(raw),
    })


def cmd_stage3_plan(args) -> None:
    invocation = _read_stage3_invocation(args)
    if invocation is None and not getattr(args, "professor_dir", None):
        fail("invalid_params",
             "stage3-plan needs --professor-dir or an invocation credential "
             "(--invocation-file + --invocation-sha256)")
    credential_correction = invocation is not None and \
        bool(getattr(args, "validation_file", None))
    if getattr(args, "capture_invocation", None) and \
            getattr(args, "validation_file", None):
        fail("invalid_params",
             "--capture-invocation records a first-round plan; correction plans "
             "reuse the original invocation credential")
    if invocation is not None:
        _require_invocation_source(invocation)
        args = _stage3_args_from_invocation(args, invocation,
                                            correction=credential_correction)
    professor_dir = Path(args.professor_dir)
    program_root = Path(args.program_root) if args.program_root else professor_dir.parent.parent
    require_professor_dir_under_program(professor_dir, program_root)
    pack, pack_error = load_input_pack(professor_dir)
    if pack is None:
        soft_exit("needs_refresh", "missing_input_pack",
                  pack_path=str(professor_dir / INPUT_PACK),
                  message="缺 套磁候选输入.json：先跑阶段 2（professor-contact-analyzer）生成输入包；不回读任何 Markdown。")
    refresh_scope = args.refresh_scope or "flagged"
    if refresh_scope not in REFRESH_SCOPES:
        fail("invalid_params", f"refresh_scope must be one of {REFRESH_SCOPES}")
    pack_directions = pack.get("directions") or []
    by_did = {direction_machine_id(d): d for d in pack_directions}
    by_ckey = {}
    for d in pack_directions:
        ckey = d.get("collection_key")
        if isinstance(ckey, str) and ckey.strip() and ckey not in by_ckey:
            by_ckey[ckey] = d
        elif isinstance(ckey, str) and ckey.strip():
            by_ckey[ckey] = None  # ambiguous projection name
    direction_id_arg = getattr(args, "direction_id", None)
    collection_key_arg = getattr(args, "collection_key", None)
    if collection_key_arg and not direction_id_arg:
        # Deprecated v1 compatibility path: resolve through the pack's exact
        # machine mapping; never treat the projection key as identity itself.
        resolved = by_ckey.get(collection_key_arg)
        if resolved is None:
            fail("invalid_params",
                 f"collection_key not found (or ambiguous) in input pack: {collection_key_arg}")
        direction_id_arg = direction_machine_id(resolved)
    if direction_id_arg and direction_id_arg not in by_did:
        fail("invalid_params", f"direction_id not found in input pack: {direction_id_arg}")
    if collection_key_arg and direction_id_arg:
        resolved = by_ckey.get(collection_key_arg)
        if resolved is None or direction_machine_id(resolved) != direction_id_arg:
            fail("invalid_params",
                 f"collection_key {collection_key_arg!r} and direction_id {direction_id_arg!r} "
                 "resolve to different directions")
    skip_ids = _parse_direction_id_list(getattr(args, "skip_direction_ids", None),
                                        "skip_direction_ids")
    unknown_skip = [d for d in skip_ids if d not in by_did]
    if unknown_skip:
        fail("invalid_params", f"skip_direction_ids outside input pack: {unknown_skip}")
    cross_groups = _parse_cross_groups(getattr(args, "cross_direction_groups", None),
                                       pack_directions)
    state, state_error = load_candidate_state(professor_dir, pack)
    if state_error:
        soft_exit("needs_refresh", state_error,
                  message="候选状态无法按机器身份精确迁移：重跑阶段 3（必要时连同阶段 2）重建 v2 状态。"
                          "未修改任何文件。")
    current_profile_fp = profile_fingerprint(args.profile)
    old_profile_fp = (state or {}).get("profile_fingerprint")
    profile_changed = bool(state) and current_profile_fp != old_profile_fp
    contract_changed = bool(state) and \
        (state or {}).get("generator_contract_version") != STAGE3_GENERATOR_CONTRACT_VERSION
    selected_keys = None
    if refresh_scope == "selected":
        if not args.selection:
            selection_path = professor_dir / SELECTION_FILE
            fail("invalid_params",
                 f"selection file unreadable without explicit --selection: {selection_path}")
        # Selected refresh is bound to the explicit professor-local Stage-4
        # container. Never fall back to the legacy program-level file.
        selected_keys = _stage3_selected_scope_keys(
            Path(args.selection), professor_dir, by_ckey)
    pack_fps = {direction_machine_id(d): d.get("input_fingerprint")
                for d in pack_directions}
    input_fps = (state or {}).get("input_fingerprints", {})
    state_directions = {d.get("direction_id"): d
                        for d in (state or {}).get("directions", [])
                        if isinstance(d, dict)}
    state_groups = {(g.get("group_id") if isinstance(g, dict) else None): g
                    for g in (state or {}).get("cross_direction_groups", [])
                    if isinstance(g, dict)}
    correction: dict = {}
    validation_render_sha = None
    if getattr(args, "validation_file", None):
        evidence = stage3_validation_evidence(Path(args.validation_file), professor_dir, state)
        validation_render_sha = evidence["render_sha256"]
        if skip_ids:
            fail("invalid_params", "Stage-3 correction cannot skip directions")
        if cross_groups:
            fail("invalid_params", "Stage-3 correction cannot request new cross-direction groups")
        for row in stage3_correction_scopes(state, evidence):
            scope = row["scope"]
            if scope["kind"] == "direction":
                did = scope["direction_id"]
                current = state_directions.get(did)
                if not current or not (
                        (current.get("stage3_status") == "ready"
                         and current.get("candidates"))
                        or (current.get("stage3_status") == "skipped"
                            and not current.get("candidates"))):
                    fail("missing_candidate_state", f"no reusable Stage-3 result for {did}")
                if direction_id_arg and did != direction_id_arg:
                    fail("validation_scope_not_in_evidence",
                         f"--direction-id {direction_id_arg!r} is not the failed scope {did!r}")
                if contract_changed or profile_changed \
                        or input_fps.get(did) != pack_fps.get(did):
                    soft_exit("needs_refresh", "validation_source_changed", direction_id=did)
                correction[f"direction:{did}"] = row
            elif scope["kind"] == "group":
                gid = scope["group_id"]
                if gid not in state_groups or not (state_groups[gid].get("candidates") or []):
                    fail("missing_candidate_state", f"no reusable Stage-3 group result for {gid}")
                if credential_correction and (
                        contract_changed or profile_changed
                        or not _cross_group_fresh(state_groups[gid], pack_fps,
                                                  current_profile_fp)):
                    soft_exit("needs_refresh", "validation_source_changed", group_id=gid)
                correction[f"group:{gid}"] = row
        if direction_id_arg and f"direction:{direction_id_arg}" not in correction:
            fail("validation_scope_not_in_evidence",
                 f"direction_id {direction_id_arg!r} has no failed Stage-3 validation scope")
        for key in [k for k in correction if k.startswith("group:")]:
            gid = key.split(":", 1)[1]
            cross_groups.append({"group_id": gid,
                                 "direction_ids": list(state_groups[gid].get("direction_ids") or [])})
        if credential_correction and not correction:
            fail("validation_evidence_not_recorded",
                 "the credential correction needs a recorded round with open findings")
    # Keep every recorded direction scope in ``correction``. Only directions
    # with ready candidates are sent through generation and replacement; a
    # skipped direction stays candidate-less and is carried through unchanged.
    correction_dids = stage3_repairable_correction_directions(correction, state_directions)
    scoped_dids = set()
    for direction in pack_directions:
        did = direction_machine_id(direction)
        if getattr(args, "validation_file", None) and did not in correction_dids:
            continue
        if credential_correction:
            # r13 §5.4: the credential correction work set is exactly D — the
            # first-round refresh/selection/scope filters must not shrink it.
            scoped_dids.add(did)
            continue
        if direction_id_arg and did != direction_id_arg:
            continue
        if refresh_scope == "flagged" and direction.get("status") != "active":
            continue
        if refresh_scope == "selected" and did not in (selected_keys or set()):
            continue
        scoped_dids.add(did)

    def _direction_reusable(did: str) -> bool:
        if contract_changed:
            return False
        old = state_directions.get(did)
        return bool(
            input_fps.get(did) == pack_fps.get(did)
            and not profile_changed
            and old
            and old.get("stage3_status") == "ready"
            and old.get("candidates"))

    jobs, reuse, skipped = [], [], []
    for direction in pack_directions:
        did = direction_machine_id(direction)
        if did not in scoped_dids:
            continue
        if did in skip_ids:
            skipped.append(did)
            continue
        if _direction_reusable(did) and did not in correction_dids:
            reuse.append(did)
            continue
        gap_lines = []
        for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
            gap_lines.append({
                "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                "authorship": gap.get("authorship"),
                "quote": truncate(gap.get("quote"), QUOTE_INPUT_CHARS),
                "translation_zh": truncate(gap.get("translation_zh"), TRANSLATION_INPUT_CHARS),
                "status": gap.get("status"), "evidence": gap.get("evidence"),
                "completed_part": gap.get("completed_part"),
                "remaining_gap": gap.get("remaining_gap"),
                "confidence": gap.get("confidence"),
                "shortlisted": gap in direction.get("gap_shortlist", [])})
        blacklist = [{"gap_id": b["gap_id"], "item_key": b["item_key"],
                      "paper_title": b.get("paper_title"),
                      "completed_by": b.get("completed_by_item_key"),
                      "evidence": b.get("evidence")}
                     for b in direction.get("completed_gap_blacklist", [])]
        mode = "refined" if direction.get("user_note") else "generated"
        jobs.append({
            "job_id": f"candidates:{pack.get('professor')}:{did}",
            "kind": "candidates",
            "direction_id": did,
            "result_file": safe_result_file("candidates", did),
            "result_schema": {"schema": 2, "kind": "candidates", "direction_id": did,
                              "candidates": [{"id": "", "kind": "direction",
                                              "direction_ids": [did],
                                              "gap_refs": [{"direction_id": did,
                                                            "item_key": "", "gap_id": ""}],
                                              "papers": [{"item_key": "",
                                                          "direction_ids": [did],
                                                          "role": "", "fit_note": ""}],
                                              "origin": "generated|user_refined"}]},
            "model_input": {
                "direction_id": did,
                "mode": mode,
                "user_note": direction.get("user_note") or "",
                "credibility": direction.get("credibility"),
                "red_lines": direction.get("red_lines") or [],
                "supporting_papers": [
                    {"item_key": p["item_key"], "title": p.get("title"),
                     "year": p.get("year"), "authorship": p.get("authorship"),
                     "named_by_user": bool(p.get("named_by_user"))}
                    for p in direction_papers(pack, direction)],
                "gaps": gap_lines,
                "completed_gap_blacklist": blacklist,
                "profile_text": load_profile_text(args.profile),
                "rules": {
                    "research_question": "每个候选必须非空研究问题（求知式表述）；写不出 → 不列该候选，把要点并入主候选展开末尾（前缀「配套承诺：」）",
                    "provenance": "每条候选必须带 kind:'direction' 和 direction_ids:[本方向 direction_id]；gap_refs 每条必须是 {direction_id, item_key, gap_id} 精确三元组，且 direction_id 就是本方向；papers[] 每篇 {item_key, direction_ids:[本方向], role, fit_note}，同一论文不得重复出现",
                    "gap_anchor": "gap_refs 只能引用 model_input.gaps / completed_gap_blacklist 里的精确 (item_key,gap_id)；done_by_self 只能以【我的延伸】+difference_point 差异点方式出现；partial 候选必须写 remaining_gap 关注点；unknown 候选必须带 unverified:true",
                    "papers": "候选 papers[] 只给 {item_key, direction_ids, role, fit_note}；标题/年份/署名由 runner 从输入包回填，禁止自写标题",
                    "count": "generated 与 refined 模式都必须给 3-5 个可选候选；有用户笔记时其中恰好 1 条 origin='user_refined'（校准后的用户想法本身成为可选候选），其余为真正不同的备选",
                    "diversity": "候选之间切入点/所挂 gap 不重复",
                    "scope": "本任务只属于 direction_id 指向的这一个方向；跨方向组合不在本任务内，绝不混入 candidates[]"}}})
        row = correction.get(f"direction:{did}")
        if row is not None:
            jobs[-1]["job_id"] = f"candidates-correction:{pack.get('professor')}:{did}"
            jobs[-1]["model_input"].update({
                "current_result": stage3_current_result(state_directions[did]),
                "validator_issues": row["issues"],
                "repairable_candidate_ids": row["candidate_ids"],
                "scope": row["scope"],
                "correction_rules": (
                    "返回完整 result；只改 validator_issues 点名的候选文字，"
                    "且只改 repairable_candidate_ids 列出的候选。"
                    "候选 ID、顺序、方向、来源、gap_refs、anchor_notes、papers 引用、fit、"
                    "红线内容与 refined 的 gap_ids 锚定属于机器事实，必须原样保留；"
                    "候选标题、一句话、研究问题、展开、贴合度说明、为何值得推、张力点、"
                    "推荐优先级与 refined 说明文字可以按清单改写。"),
            })
    # Cross-direction jobs: explicit opt-in only (issue #8 §6). No requested
    # group ⇒ no cross job, no cross model call, no cross section.
    cross_jobs = []
    for group in cross_groups:
        stale = True
        old_group = state_groups.get(group["group_id"])
        group_correction = correction.get(f"group:{group['group_id']}")
        if old_group and not contract_changed and group_correction is None \
                and _cross_group_fresh(old_group, pack_fps, current_profile_fp) \
                and old_group.get("candidates"):
            continue
        gap_union: dict = {}
        paper_union: dict = {}
        for pid in group["direction_ids"]:
            p_gaps, p_blacklist, p_papers = _direction_slices(pack, by_did[pid])
            for (owner, item_key, gap_id), gap in p_gaps.items():
                row = gap_union.setdefault((item_key, gap_id),
                                           {**gap, "direction_ids": []})
                row["direction_ids"].append(pid)
            for (owner, item_key, gap_id), banned in p_blacklist.items():
                row = gap_union.setdefault((item_key, gap_id),
                                           {**banned, "status": "done_by_self",
                                            "direction_ids": []})
                row["direction_ids"].append(pid)
            for item_key, paper in p_papers.items():
                row = paper_union.setdefault(item_key, {**paper, "direction_ids": []})
                if pid not in row["direction_ids"]:
                    row["direction_ids"].append(pid)
        cross_jobs.append({
            "job_id": f"cross:{pack.get('professor')}:{group['group_id']}",
            "kind": "cross_direction",
            "group_id": group["group_id"],
            "direction_ids": group["direction_ids"],
            "result_file": safe_result_file("candidates", group["group_id"]),
            "result_schema": {"schema": 2, "kind": "cross_candidates",
                              "group_id": group["group_id"],
                              "direction_ids": group["direction_ids"],
                              "candidates": [{"id": "", "kind": "cross_direction",
                                              "direction_ids": group["direction_ids"],
                                              "gap_refs": [{"direction_id": "", "item_key": "",
                                                            "gap_id": ""}],
                                              "papers": [{"item_key": "",
                                                          "direction_ids": group["direction_ids"],
                                                          "role": "", "fit_note": ""}]}]},
            "model_input": {
                "group_id": group["group_id"],
                "direction_ids": group["direction_ids"],
                "directions": [{"direction_id": pid, "name_ja": by_did[pid].get("name_ja"),
                                "name_zh": by_did[pid].get("name_zh")}
                               for pid in group["direction_ids"]],
                "papers": [{"item_key": p["item_key"], "title": p.get("title"),
                            "year": p.get("year"), "authorship": p.get("authorship"),
                            "direction_ids": p.get("direction_ids") or []}
                           for p in paper_union.values()],
                "gaps": [{"gap_id": g["gap_id"], "item_key": g["item_key"],
                          "paper_title": g.get("paper_title"),
                          "paper_year": g.get("paper_year"),
                          "quote": truncate(g.get("quote"), QUOTE_INPUT_CHARS),
                          "translation_zh": truncate(g.get("translation_zh"), TRANSLATION_INPUT_CHARS),
                          "status": g.get("status"), "evidence": g.get("evidence"),
                          "completed_part": g.get("completed_part"),
                          "remaining_gap": g.get("remaining_gap"),
                          "confidence": g.get("confidence"),
                          "direction_ids": g.get("direction_ids") or []}
                         for g in gap_union.values()],
                "profile_text": load_profile_text(args.profile),
                "rules": {
                    "provenance": "每条候选 kind:'cross_direction'、direction_ids 必须等于本组全部参与方向（排序后）；gap_refs 每条 {direction_id, item_key, gap_id} 三元组只能引用该 direction_id 自己切片里的精确 gap；papers[] 每篇 {item_key, direction_ids, role, fit_note}，direction_ids 是真实支撑该论文的方向子集，同一论文只出现一次",
                    "grounding": "每个参与方向都必须贡献至少一条真实证据（挂它的 gap 或支撑它的论文）；只引用单方向证据的伪跨方向候选会被拒绝",
                    "count": "给 1-3 个跨方向候选；没有真正的跨方向洞察就输出更少；3-5 的常规名额只属于普通方向任务"}}})
        if group_correction is not None:
            cross_jobs[-1]["job_id"] = f"cross-correction:{pack.get('professor')}:{group['group_id']}"
            cross_jobs[-1]["model_input"].update({
                "current_result": {"schema": 2, "kind": "cross_candidates",
                                   "group_id": group["group_id"],
                                   "direction_ids": group["direction_ids"],
                                   "candidates": (old_group or {}).get("candidates") or []},
                "validator_issues": group_correction["issues"],
                "repairable_candidate_ids": group_correction["candidate_ids"],
                "scope": group_correction["scope"],
                "correction_rules": "返回完整 result；只改 validator_issues 点名且列在 "
                                    "repairable_candidate_ids 里的跨方向候选文字，kind、"
                                    "direction_ids、gap_refs、papers 引用等机器事实原样保留。",
            })
    # r13 §5.1: after every input check passed and the plan succeeded, freeze
    # THIS invocation's parsed parameters into an exclusive credential file.
    # A capture failure fails the plan: no ok payload is emitted at all.
    invocation_result = {}
    capture_dir = getattr(args, "capture_invocation", None)
    if capture_dir:
        credential = {
            "version": STAGE3_INVOCATION_VERSION,
            "professor_dir": str(professor_dir.resolve()),
            "program_root": str(program_root.resolve()),
            "profile_path": str(Path(args.profile).resolve()) if args.profile else None,
            "profile_sha256": current_profile_fp,
            "refresh_scope": args.refresh_scope,
            "direction_id": args.direction_id,
            "collection_key": args.collection_key,
            "collection_key_direction_id": direction_id_arg,
            "skip_direction_ids_argument": args.skip_direction_ids,
            "skipped_direction_ids": list(skip_ids),
            "cross_direction_groups_argument": args.cross_direction_groups,
            "cross_direction_groups": [
                {"group_id": g["group_id"], "direction_ids": list(g["direction_ids"])}
                for g in cross_groups],
            "selection": str(Path(args.selection).resolve()) if args.selection else None,
        }
        file_path, file_sha = _write_stage3_invocation(capture_dir, credential)
        invocation_result = {"invocation_file": file_path,
                             "invocation_sha256": file_sha}
    emit({
        "status": "ok",
        "professor": pack.get("professor"),
        "professor_dir": str(professor_dir),
        "refresh_scope": refresh_scope,
        "direction_id": direction_id_arg,
        "correction_scopes": sorted(correction),
        "validation_render_sha256": validation_render_sha,
        "profile_fingerprint": current_profile_fp,
        "profile_changed_reason": "profile_changed" if profile_changed else None,
        "generator_contract_version": STAGE3_GENERATOR_CONTRACT_VERSION,
        "skipped_direction_ids": skipped,
        "directions": [{"direction_id": direction_machine_id(d),
                        "collection_key": d.get("collection_key"),
                        "action": ("reuse" if direction_machine_id(d) in reuse else
                                   ("skipped" if direction_machine_id(d) in skipped
                                    else "process"))}
                       for d in pack_directions
                       if not direction_id_arg or direction_machine_id(d) == direction_id_arg],
        "cross_direction_groups": [{"group_id": g["group_id"],
                                     "direction_ids": g["direction_ids"],
                                     "action": "process"}
                                    for g in cross_groups],
        "jobs": jobs + cross_jobs,
        "write_needed": bool(jobs + cross_jobs),
        **invocation_result,
    })


def _validate_candidate_core(candidate: Any, path: Path,
                             gap_index: dict, blacklist: dict,
                             paper_index: dict, direction_ids: list[str],
                             kind: str,
                             paper_slices: dict | None = None) -> dict:
    """Validate one idea against exact (direction_id, item_key, gap_id) join
    indexes and return the normalized candidate record (issue #8 §5).

    `direction_ids` is the ONLY provenance the candidate may claim: an ordinary
    candidate gets exactly its own direction, a cross candidate gets the sorted
    participant group. Gap refs join through the full triple, so a valid
    (item_key, gap_id) from another direction is rejected when paired with the
    wrong direction_id.
    """
    if not isinstance(candidate, dict):
        fail("invalid_result_json", f"{path}: candidates[] must be objects")
    if candidate.get("id") is not None and not isinstance(candidate.get("id"), str):
        fail("invalid_result_json", f"{path}: candidate id must be a string")
    cid = (candidate.get("id") or "").strip()
    if not cid:
        fail("invalid_result_json", f"{path}: candidate id required: {cid!r}")
    for field in ("title", "one_liner", "research_question", "fit_note", "why_recommended"):
        if candidate.get(field) is not None and not isinstance(candidate.get(field), str):
            fail("invalid_result_json", f"{path}: candidate {cid} field {field} must be a string")
    if not (candidate.get("research_question") or "").strip():
        fail("invalid_result_json",
             f"{path}: candidate {cid} 缺非空研究问题（求知式）；纯交付物候选应并入主候选而非单列")
    raw_ids = candidate.get("direction_ids")
    if not isinstance(raw_ids, list) or [x.strip() if isinstance(x, str) else None
                                         for x in raw_ids] != direction_ids:
        fail("invalid_result_json",
             f"{path}: candidate {cid} direction_ids must be exactly {direction_ids} "
             f"(got {raw_ids!r})")
    origin = candidate.get("origin")
    if origin is not None and (not isinstance(origin, str) or origin.strip()
                               not in ("generated", "user_refined")):
        fail("invalid_result_json",
             f"{path}: candidate {cid} origin must be 'generated' or 'user_refined'")
    anchor_notes = candidate.get("anchor_notes") or {}
    if not isinstance(anchor_notes, dict):
        fail("invalid_result_json", f"{path}: candidate {cid} anchor_notes must be an object")
    for note_key in ("remaining_focus", "difference_point"):
        if note_key in anchor_notes and not isinstance(anchor_notes[note_key], str):
            fail("invalid_result_json", f"{path}: candidate {cid} anchor_notes.{note_key} must be a string")
    if "unverified" in anchor_notes and not isinstance(anchor_notes["unverified"], bool):
        fail("invalid_result_json", f"{path}: candidate {cid} anchor_notes.unverified must be boolean")
    for field in ("points", "red_lines", "tension_points"):
        value = candidate.get(field) or []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            fail("invalid_result_json", f"{path}: candidate {cid} field {field} must be a string list")
    raw_refs = candidate.get("gap_refs") or []
    if not isinstance(raw_refs, list) or not all(isinstance(pair, dict) for pair in raw_refs):
        fail("invalid_result_json", f"{path}: candidate {cid} gap_refs must be an object list "
                                    "of {direction_id, item_key, gap_id} triples")
    gap_refs = []
    seen_triples = set()
    for pair in raw_refs:
        did = pair.get("direction_id")
        key = (did, pair.get("item_key"), pair.get("gap_id"))
        if key in seen_triples:
            fail("invalid_result_json", f"{path}: candidate {cid} contains duplicate gap {key}")
        seen_triples.add(key)
        if did not in direction_ids:
            fail("unknown_reference_id",
                 f"{path}: candidate {cid} gap {key} cites a direction outside its provenance")
        in_pool = key in gap_index
        in_blacklist = key in blacklist
        if not in_pool and not in_blacklist:
            fail("unknown_reference_id",
                 f"{path}: candidate {cid} gap {key} is not an exact (direction_id, item_key, "
                 "gap_id) join into the cited direction's slice")
        if in_pool:
            status = gap_index[key].get("status")
            if status not in ANCHORABLE:
                fail("blacklisted_gap_anchor",
                     f"{path}: candidate {cid} anchors {key} status={status}")
            if status == "partial" and not (anchor_notes.get("remaining_focus") or "").strip():
                fail("invalid_result_json",
                     f"{path}: candidate {cid} partial anchor needs anchor_notes.remaining_focus")
            if status == "unknown" and not anchor_notes.get("unverified"):
                fail("invalid_result_json",
                     f"{path}: candidate {cid} unknown anchor needs anchor_notes.unverified=true")
        else:
            if not (anchor_notes.get("difference_point") or "").strip():
                fail("blacklisted_gap_anchor",
                     f"{path}: candidate {cid} uses done_by_self gap {key} without "
                     "my_extension difference_point")
        gap_refs.append({"direction_id": did, "item_key": key[1], "gap_id": key[2],
                         "done_by_self": in_blacklist})
    raw_papers = candidate.get("papers") or []
    if not isinstance(raw_papers, list) or not all(isinstance(paper, dict) for paper in raw_papers):
        fail("invalid_result_json", f"{path}: candidate {cid} papers must be an object list")
    papers = []
    seen_papers = set()
    for paper in raw_papers:
        item_key = paper.get("item_key")
        source = paper_index.get(item_key)
        if not source:
            fail("unknown_paper_id", f"{path}: candidate {cid} paper {item_key} outside package")
        if item_key in seen_papers:
            fail("invalid_result_json", f"{path}: candidate {cid} contains duplicate paper {item_key}")
        seen_papers.add(item_key)
        paper_ids = paper.get("direction_ids")
        if paper_ids is None:
            paper_ids = list(direction_ids)
        else:
            if not isinstance(paper_ids, list) or not paper_ids \
                    or any(not isinstance(x, str) or x.strip() not in direction_ids
                           for x in paper_ids):
                fail("invalid_result_json",
                     f"{path}: candidate {cid} paper {item_key} direction_ids must be a non-empty "
                     f"subset of {direction_ids}")
            paper_ids = sorted({x.strip() for x in paper_ids})
            # Each cited direction must actually ALLOW the paper: the item_key
            # has to live in that direction's own slice (issue #8 §5).
            for cited in paper_ids:
                if paper_slices is not None and item_key not in paper_slices.get(cited, ()):
                    fail("unknown_paper_id",
                         f"{path}: candidate {cid} paper {item_key} is not part of direction "
                         f"{cited!r}'s slice, so it cannot carry {cited!r} provenance")
        papers.append({"item_key": item_key, "direction_ids": paper_ids,
                       "title": source.get("title"), "year": source.get("year"),
                       "authorship": source.get("authorship"),
                       "role": (paper.get("role") or "").strip(),
                       "fit_note": (paper.get("fit_note") or "").strip()})
    has_author_gap = any(not g["done_by_self"] for g in gap_refs)
    anchor_type = "author_future_work" if gap_refs and has_author_gap else (
        "my_extension" if gap_refs else "none")
    return {
        "id": cid,
        "kind": kind,
        "direction_ids": list(direction_ids),
        "origin": (origin or "generated").strip(),
        "title": (candidate.get("title") or "").strip(),
        "one_liner": (candidate.get("one_liner") or "").strip(),
        "research_question": candidate.get("research_question").strip(),
        "points": [str(x) for x in (candidate.get("points") or [])],
        "gap_refs": gap_refs,
        "anchor_type": anchor_type,
        "anchor_notes": anchor_notes,
        "papers": papers,
        "fit": candidate.get("fit") if candidate.get("fit") in ("high", "partial", "weak", "null") else "null",
        "fit_note": (candidate.get("fit_note") or "").strip(),
        "red_lines": [str(x) for x in (candidate.get("red_lines") or [])],
        "why_recommended": (candidate.get("why_recommended") or "").strip(),
        "tension_points": [str(x) for x in (candidate.get("tension_points") or [])]}


def validate_candidate_result(pack: dict, pack_direction: dict, data: Any, path: Path) -> dict:
    """Validate one direction's stage-3 result against the input pack (v2).

    The result must carry the job's direction_id, and every candidate must
    claim exactly that direction's provenance with exact-triple gap refs. The
    optional 3-5 quota now ALSO applies to refined mode: the calibrated user
    idea itself becomes one selectable candidate (origin=user_refined).
    """
    if not isinstance(data, dict) or data.get("schema") != 2 or data.get("kind") != "candidates":
        fail("invalid_result_json", f"{path}: schema/kind must be 2/candidates")
    did = direction_machine_id(pack_direction)
    if data.get("direction_id") != did:
        fail("invalid_result_json",
             f"{path}: direction_id {data.get('direction_id')!r} does not match the job direction {did!r}")
    mode = data.get("mode")
    if mode not in ("refined", "generated"):
        fail("invalid_result_json", f"{path}: mode must be refined|generated")
    if mode == "refined" and not (pack_direction.get("user_note") or "").strip():
        fail("invalid_result_json", f"{path}: refined mode without user note")
    gap_index, blacklist, paper_index = _direction_slices(pack, pack_direction)
    refined = data.get("refined")
    if mode == "refined":
        if not isinstance(refined, dict):
            fail("invalid_result_json", f"{path}: refined block required in refined mode")
        if not isinstance(refined.get("idea_zh"), str) or not refined["idea_zh"].strip():
            fail("invalid_result_json", f"{path}: refined.idea_zh required")
        for field in ("calibration", "variants", "mismatches"):
            value = refined.get(field) or []
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                fail("invalid_result_json", f"{path}: refined.{field} must be a string list")
        refined_gap_ids = refined.get("gap_ids") or []
        if not isinstance(refined_gap_ids, list) or not all(isinstance(pair, dict) for pair in refined_gap_ids):
            fail("invalid_result_json", f"{path}: refined.gap_ids must be an object list")
        for pair in refined_gap_ids:
            key = (pair.get("item_key"), pair.get("gap_id"))
            if key not in {(i, g) for (d, i, g) in gap_index} \
                    and key not in {(i, g) for (d, i, g) in blacklist}:
                fail("unknown_reference_id", f"{path}: refined gap {key} outside package")
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        fail("invalid_result_json", f"{path}: candidates must be a list")
    if not 3 <= len(candidates) <= 5:
        fail("invalid_result_json", f"{path}: {mode} mode needs 3-5 selectable candidates")
    checked = []
    seen_ids = set()
    user_refined_count = 0
    for candidate in candidates:
        single = _validate_candidate_core(candidate, path, gap_index, blacklist,
                                          paper_index, [did], "direction")
        cid = single["id"]
        if cid in seen_ids:
            fail("invalid_result_json", f"{path}: candidate id required and unique: {cid!r}")
        seen_ids.add(cid)
        if single["origin"] == "user_refined":
            user_refined_count += 1
        checked.append(single)
    if mode == "refined" and user_refined_count != 1:
        fail("invalid_result_json",
             f"{path}: refined mode needs exactly one origin='user_refined' candidate "
             f"(found {user_refined_count})")
    if mode == "refined":
        refined_checked = {
            "core_intent": (refined.get("core_intent") or "").strip(),
            "calibration": [str(x) for x in (refined.get("calibration") or [])],
            "idea_zh": refined.get("idea_zh").strip(),
            "variants": [str(x) for x in (refined.get("variants") or [])],
            "mismatches": [str(x) for x in (refined.get("mismatches") or [])],
            "gap_ids": [{"item_key": p.get("item_key"), "gap_id": p.get("gap_id")}
                        for p in (refined.get("gap_ids") or [])],
        }
    else:
        refined_checked = None
    priority = data.get("priority") or ""
    if not isinstance(priority, str):
        fail("invalid_result_json", f"{path}: priority must be a string")
    return {"direction_id": did, "mode": mode, "refined": refined_checked,
            "candidates": checked, "priority": priority.strip()}


def validate_cross_result(pack: dict, group: dict, data: Any, path: Path) -> dict:
    """Validate one explicit cross-direction group's result (issue #8 §6).

    Every candidate must cite the exact sorted participant group, join gaps
    through the full triple against each cited direction's own slice, key
    papers once by item_key, and be GROUNDED in every participant: a candidate
    labeled A+B but carrying only A evidence is rejected.
    """
    if not isinstance(data, dict) or data.get("schema") != 2 \
            or data.get("kind") != "cross_candidates":
        fail("invalid_result_json", f"{path}: schema/kind must be 2/cross_candidates")
    ids = group["direction_ids"]
    if data.get("group_id") != group["group_id"] or data.get("direction_ids") != ids:
        fail("invalid_result_json",
             f"{path}: group identity mismatch (expected {group['group_id']} / {ids})")
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        fail("invalid_result_json", f"{path}: candidates must be a list")
    if not 1 <= len(candidates) <= 3:
        fail("invalid_result_json", f"{path}: cross-direction groups need 1-3 candidates")
    by_id = {direction_machine_id(d): d for d in (pack or {}).get("directions") or []}
    union_gap: dict = {}
    union_blacklist: dict = {}
    union_papers: dict = {}
    paper_slices: dict = {}
    for pid in ids:
        p_gaps, p_blacklist, p_papers = _direction_slices(pack, by_id[pid])
        union_gap.update(p_gaps)
        union_blacklist.update(p_blacklist)
        union_papers.update(p_papers)
        paper_slices[pid] = set(p_papers)
    checked = []
    seen_ids = set()
    for candidate in candidates:
        single = _validate_candidate_core(candidate, path, union_gap, union_blacklist,
                                          union_papers, ids, "cross_direction",
                                          paper_slices=paper_slices)
        cid = single["id"]
        if cid in seen_ids:
            fail("invalid_result_json", f"{path}: candidate id required and unique: {cid!r}")
        seen_ids.add(cid)
        grounded = {ref["direction_id"] for ref in single["gap_refs"]}
        grounded |= {pid for paper in single["papers"]
                     for pid in paper.get("direction_ids") or []}
        missing = [pid for pid in ids if pid not in grounded]
        if missing:
            fail("unknown_reference_id",
                 f"{path}: cross-direction candidate {cid} has no grounded evidence "
                 f"from participant(s) {missing}")
        checked.append(single)
    return {"group_id": group["group_id"], "direction_ids": list(ids),
            "candidates": checked}


# Stage-3 Markdown rendering lives in the sibling helper ``_stage3_render.py``
# (loaded by path above). These names keep the pre-split module-level API: the
# two public renderers stay same-named and same-signature, and the private
# helpers stay reachable for callers and tests that already used them.
_red_line_key = _stage3_render._red_line_key
_candidate_red_lines = _stage3_render._candidate_red_lines
_render_idea_block = _stage3_render._render_idea_block
_stage3_scope_marker = _stage3_render._stage3_scope_marker


def render_candidates_md(professor: str, category: str, direction_entries: list,
                         profile_fp: str | None, state_fingerprint: str,
                         professor_dir: Path, cross_groups: list | None = None) -> str:
    return _stage3_render.render_candidates_md(
        professor, category, direction_entries, profile_fp, state_fingerprint,
        professor_dir, cross_groups, now_utc=now_utc)


def render_candidates_overview(entries: list, program_root: Path,
                               cross_groups: list | None = None) -> str:
    return _stage3_render.render_candidates_overview(
        entries, program_root, cross_groups,
        now_utc=now_utc, candidates_md=CANDIDATES_MD)



def cmd_stage3_finalize(args) -> None:
    invocation = _read_stage3_invocation(args)
    if invocation is None and not getattr(args, "professor_dir", None):
        fail("invalid_params",
             "stage3-finalize needs --professor-dir or an invocation credential "
             "(--invocation-file + --invocation-sha256)")
    credential_correction = invocation is not None and \
        bool(getattr(args, "validation_file", None))
    if invocation is not None:
        _require_invocation_source(invocation)
        args = _stage3_args_from_invocation(args, invocation,
                                            correction=credential_correction)
    professor_dir = Path(args.professor_dir)
    program_root = Path(args.program_root) if args.program_root else professor_dir.parent.parent
    require_professor_dir_under_program(professor_dir, program_root)
    pack, pack_error = load_input_pack(professor_dir)
    if pack is None:
        soft_exit("needs_refresh", "missing_input_pack", pack_path=str(professor_dir / INPUT_PACK))
    pack_directions = pack.get("directions") or []
    by_did = {direction_machine_id(d): d for d in pack_directions}
    by_ckey = {}
    for d in pack_directions:
        ckey = d.get("collection_key")
        if isinstance(ckey, str) and ckey.strip() and ckey not in by_ckey:
            by_ckey[ckey] = d
        elif isinstance(ckey, str) and ckey.strip():
            by_ckey[ckey] = None
    direction_id_arg = getattr(args, "direction_id", None)
    collection_key_arg = getattr(args, "collection_key", None)
    if collection_key_arg and not direction_id_arg:
        resolved = by_ckey.get(collection_key_arg)
        if resolved is None:
            fail("invalid_params",
                 f"collection_key not found (or ambiguous) in input pack: {collection_key_arg}")
        direction_id_arg = direction_machine_id(resolved)
    if direction_id_arg and direction_id_arg not in by_did:
        fail("invalid_params", f"direction_id not found in input pack: {direction_id_arg}")
    if collection_key_arg and direction_id_arg:
        resolved = by_ckey.get(collection_key_arg)
        if resolved is None or direction_machine_id(resolved) != direction_id_arg:
            fail("invalid_params",
                 f"collection_key {collection_key_arg!r} and direction_id {direction_id_arg!r} "
                 "resolve to different directions")
    skip_ids = _parse_direction_id_list(getattr(args, "skip_direction_ids", None),
                                        "skip_direction_ids")
    unknown_skip = [d for d in skip_ids if d not in by_did]
    if unknown_skip:
        fail("invalid_params", f"skip_direction_ids outside input pack: {unknown_skip}")
    cross_groups = _parse_cross_groups(getattr(args, "cross_direction_groups", None),
                                       pack_directions)
    refresh_scope = args.refresh_scope or "flagged"
    state, state_error = load_candidate_state(professor_dir, pack)
    if state_error:
        soft_exit("needs_refresh", state_error,
                  message="候选状态无法按机器身份精确迁移：重跑阶段 3（必要时连同阶段 2）重建 v2 状态。"
                          "未修改任何文件。")
    current_profile_fp = profile_fingerprint(args.profile)
    old_profile_fp = (state or {}).get("profile_fingerprint")
    profile_changed = bool(state) and current_profile_fp != old_profile_fp
    contract_changed = bool(state) and \
        (state or {}).get("generator_contract_version") != STAGE3_GENERATOR_CONTRACT_VERSION
    if getattr(args, "validation_file", None) and profile_changed:
        # r13 §5.5-5: correction prose never rebinds the recorded profile.
        soft_exit("needs_refresh", "validation_source_changed")
    old_directions = {d.get("direction_id"): d
                      for d in (state or {}).get("directions", []) if isinstance(d, dict)}
    old_group_list = [g for g in (state or {}).get("cross_direction_groups", [])
                      if isinstance(g, dict)]
    old_groups = {(g.get("group_id") if isinstance(g, dict) else None): g
                  for g in old_group_list}
    old_fps = (state or {}).get("input_fingerprints", {})
    pack_fps = {direction_machine_id(d): d.get("input_fingerprint")
                for d in pack_directions}
    correction: dict = {}
    if getattr(args, "validation_file", None):
        if skip_ids or cross_groups:
            fail("invalid_params", "Stage-3 correction cannot skip or request cross-direction groups")
        evidence = stage3_validation_evidence(Path(args.validation_file), professor_dir, state)
        for row in stage3_correction_scopes(state, evidence):
            scope = row["scope"]
            if scope["kind"] == "direction":
                did = scope["direction_id"]
                current = old_directions.get(did)
                if not current or not (
                        (current.get("stage3_status") == "ready"
                         and current.get("candidates"))
                        or (current.get("stage3_status") == "skipped"
                            and not current.get("candidates"))):
                    fail("missing_candidate_state", f"no reusable Stage-3 result for {did}")
                if direction_id_arg and did != direction_id_arg:
                    fail("validation_scope_not_in_evidence",
                         f"--direction-id {direction_id_arg!r} is not the failed scope {did!r}")
                if contract_changed or profile_changed or old_fps.get(did) != pack_fps.get(did):
                    soft_exit("needs_refresh", "validation_source_changed", direction_id=did)
                correction[f"direction:{did}"] = row
            elif scope["kind"] == "group":
                gid = scope["group_id"]
                if gid not in old_groups or not (old_groups[gid].get("candidates") or []):
                    fail("missing_candidate_state", f"no reusable Stage-3 group result for {gid}")
                if credential_correction and (
                        contract_changed or profile_changed
                        or not _cross_group_fresh(old_groups[gid], pack_fps,
                                                  current_profile_fp)):
                    soft_exit("needs_refresh", "validation_source_changed", group_id=gid)
                correction[f"group:{gid}"] = row
        if direction_id_arg and f"direction:{direction_id_arg}" not in correction:
            fail("validation_scope_not_in_evidence",
                 f"direction_id {direction_id_arg!r} has no failed Stage-3 validation scope")
        for key in [k for k in correction if k.startswith("group:")]:
            gid = key.split(":", 1)[1]
            cross_groups.append({"group_id": gid,
                                 "direction_ids": list(old_groups[gid].get("direction_ids") or [])})
        if credential_correction and not correction:
            fail("validation_evidence_not_recorded",
                 "the credential correction needs a recorded round with open findings")
    # Only ready, candidate-bearing scopes are replaced. Recorded skipped
    # scopes remain authoritative but stay outside the correction work set.
    correction_dids = stage3_repairable_correction_directions(correction, old_directions)
    selected_keys = None
    if refresh_scope == "selected":
        if not args.selection:
            selection_path = professor_dir / SELECTION_FILE
            fail("invalid_params",
                 f"selection file unreadable without explicit --selection: {selection_path}")
        # Plan and finalize consume the same explicit professor-local selection.
        selected_keys = _stage3_selected_scope_keys(
            Path(args.selection), professor_dir, by_ckey)
    results_dir = Path(args.results)
    decision = None
    if getattr(args, "decision_file", None):
        decision_data, derr = read_json_file(Path(args.decision_file))
        if derr is None and isinstance(decision_data, dict):
            decision = decision_data.get("decision")
    professor = pack.get("professor")
    category = professor_dir.parent.name
    scoped_dids = set()
    for direction in pack_directions:
        did = direction_machine_id(direction)
        if getattr(args, "validation_file", None) and did not in correction_dids:
            continue
        if credential_correction:
            # r13 §5.4: the credential correction work set is exactly D — the
            # first-round refresh/selection/scope filters must not shrink it.
            scoped_dids.add(did)
            continue
        if direction_id_arg and did != direction_id_arg:
            continue
        if refresh_scope == "flagged" and direction.get("status") != "active":
            continue
        if refresh_scope == "selected" and did not in (selected_keys or set()):
            continue
        scoped_dids.add(did)
    updated_directions, reused, skipped_out = [], [], []
    processed_scopes = set()
    for direction in pack_directions:
        did = direction_machine_id(direction)
        if did not in scoped_dids:
            old = old_directions.get(did)
            if old:
                # A scoped refresh replaces only the selected directions; the
                # other accepted directions stay in the machine state + render.
                updated_directions.append(old)
            continue
        old_direction = old_directions.get(did)
        if did in skip_ids:
            # Explicit skip is persisted state (issue #8 §4.2): visible,
            # candidate-less, and distinct from "never processed". A later run
            # without the skip processes the direction normally (empty
            # candidates never satisfy the reuse gate).
            skipped_out.append(did)
            updated_directions.append({
                "direction_id": did,
                "name_ja": direction.get("name_ja"),
                "name_zh": direction.get("name_zh"),
                "status": direction.get("status"),
                "stage3_status": "skipped",
                "candidates": [], "mode": None, "refined": None, "priority": "",
                "credibility": direction.get("credibility"),
                "red_lines": direction.get("red_lines") or [],
                "user_note_present": bool(direction.get("user_note")),
            })
            continue
        if old_direction and did not in correction_dids and not contract_changed \
                and not profile_changed \
                and old_fps.get(did) == pack_fps.get(did) \
                and old_direction.get("stage3_status") == "ready" \
                and old_direction.get("candidates"):
            reused.append(did)
            # Display names/status are pack projections, not cached evidence:
            # sync them so a display-only rename re-renders deterministically
            # without any idea model call (issue #8 §4.4).
            for field in ("name_ja", "name_zh", "status"):
                old_direction[field] = direction.get(field)
            updated_directions.append(old_direction)
            continue
        result_path = results_dir / safe_result_file("candidates", did)
        processed_scopes.add(f"direction:{did}")
        data, rerror = read_json_file(result_path)
        if rerror:
            fail("result_missing", f"{result_path}: {rerror}")
        checked = validate_candidate_result(pack, direction, data, result_path)
        row = correction.get(f"direction:{did}")
        if row is not None:
            require_stage3_correction_invariants(old_direction, checked, result_path,
                                                 row["candidate_ids"])
        checked["name_ja"] = direction.get("name_ja")
        checked["name_zh"] = direction.get("name_zh")
        checked["credibility"] = direction.get("credibility")
        checked["red_lines"] = direction.get("red_lines") or []
        checked["status"] = direction.get("status")
        checked["user_note_present"] = bool(direction.get("user_note"))
        checked["stage3_status"] = "ready"
        updated_directions.append(checked)
    # Cross-direction groups: only EXPLICITLY requested groups exist (issue #8
    # §6). A group survives when its recorded participant fingerprints + profile
    # still match; otherwise it needs the result file its plan job pointed at.
    # Plain generation still drops earlier groups that are no longer requested
    # and reports them — never silently keeps them. A correction (credential or
    # explicit) instead replaces in place inside the OLD group list and
    # preserves every uninvolved group: an unrequested group is never a
    # removal request (r13 §5.5).
    final_groups, dropped_groups = [], []
    for group in cross_groups:
        old_group = old_groups.get(group["group_id"])
        group_row = correction.get(f"group:{group['group_id']}")
        if old_group and group_row is None and not contract_changed \
                and _cross_group_fresh(old_group, pack_fps, current_profile_fp) \
                and old_group.get("candidates"):
            final_groups.append(old_group)
            continue
        result_path = results_dir / safe_result_file("candidates", group["group_id"])
        processed_scopes.add(f"group:{group['group_id']}")
        data, rerror = read_json_file(result_path)
        if rerror:
            fail("result_missing", f"{result_path}: {rerror}")
        checked = validate_cross_result(pack, group, data, result_path)
        if group_row is not None:
            require_stage3_correction_invariants(
                old_group, {"candidates": checked["candidates"]}, result_path,
                group_row["candidate_ids"])
        final_groups.append({
            "group_id": group["group_id"],
            "direction_ids": list(group["direction_ids"]),
            # r13 §5.5-5: correction prose never rebinds a group's recorded
            # source fingerprints; only a real (re)generation does.
            "direction_fingerprints": (
                old_group.get("direction_fingerprints") if group_row is not None
                else {pid: pack_fps.get(pid) for pid in group["direction_ids"]}),
            "profile_fingerprint": (
                old_group.get("profile_fingerprint") if group_row is not None
                else current_profile_fp),
            "candidates": checked["candidates"],
        })
    requested_ids = {g["group_id"] for g in cross_groups}
    if correction:
        # r13 §5.5-2/3: the identity set and the list order stay exactly as
        # before; each old group is either replaced in place or kept as-is.
        kept = {g["group_id"]: g for g in final_groups}
        final_groups = [kept.get(g.get("group_id"), g) for g in old_group_list]
    else:
        for group_id, group in old_groups.items():
            if group_id in requested_ids:
                continue
            dropped_groups.append({"group_id": group_id,
                                   "direction_ids": group.get("direction_ids") or [],
                                   "reason": "group_not_requested"})
    all_group_candidates = [c for g in final_groups for c in g.get("candidates") or []]
    cross_ids = [c.get("id") for c in all_group_candidates]
    if len(set(cross_ids)) != len(cross_ids):
        fail("duplicate_idea_id", f"cross-direction idea ids not unique: {cross_ids}")
    if not updated_directions and not reused and not final_groups:
        fail("validation_failed", "no in-scope directions or groups to write")
    md_entries = []
    for entry in updated_directions:
        clone = dict(entry)
        clone["_pack_papers"] = []
        pack_direction = by_did.get(entry.get("direction_id"))
        if pack_direction is not None:
            for paper in direction_papers(pack, pack_direction):
                item = dict(paper)
                if item.get("analysis_file"):
                    item["_analysis_rel"] = rel_path(Path(item["analysis_file"]), professor_dir)
                clone["_pack_papers"].append(item)
        md_entries.append(clone)
    cross_md_groups = []
    for group in final_groups:
        clone = dict(group)
        clone["_pack_papers"] = []
        seen_keys = set()
        participants = []
        for pid in group.get("direction_ids") or []:
            pack_direction = by_did.get(pid) or {}
            participants.append({"direction_id": pid,
                                 "name_ja": pack_direction.get("name_ja") or pid})
            for paper in direction_papers(pack, pack_direction):
                if paper["item_key"] in seen_keys:
                    continue
                seen_keys.add(paper["item_key"])
                item = dict(paper)
                if item.get("analysis_file"):
                    item["_analysis_rel"] = rel_path(Path(item["analysis_file"]), professor_dir)
                clone["_pack_papers"].append(item)
        clone["_participants"] = participants
        # The 参与方向 label is rendered per candidate from the group's roster.
        clone["candidates"] = [dict(c, _participants=participants)
                               for c in clone.get("candidates") or []]
        cross_md_groups.append(clone)
    if correction:
        # r13 §5.5-2: objects outside the correction work set keep their
        # recorded source fingerprints — correction prose never re-binds them.
        input_fps = {did: (pack_fps.get(did) if did in scoped_dids
                           else old_fps.get(did, pack_fps.get(did)))
                     for did in pack_fps}
    else:
        input_fps = dict(pack_fps)
    state_fingerprint = sha256_obj({"professor": professor, "directions": input_fps,
                                    "profile": current_profile_fp})
    md_path = professor_dir / CANDIDATES_MD
    old_render = ((state or {}).get("cache") or {}).get("render", {})
    body = render_candidates_md(professor, category, md_entries,
                                current_profile_fp, state_fingerprint, professor_dir,
                                cross_groups=cross_md_groups)
    md_conflict = managed_conflict(
        md_path, body, old_render.get(CANDIDATES_MD, {}).get("sha256"), decision)
    if md_conflict:
        soft_exit("needs_decision", md_conflict["reason_code"], target=md_conflict.get("target"),
                  options=["overwrite", "keep_manual", "promote"])
    body_sha = sha256_text(body)
    new_state = {
        "schema": CANDIDATE_STATE_SCHEMA, "kind": CANDIDATE_STATE_KIND,
        "identity_version": DIRECTION_IDENTITY_VERSION,
        "generator_contract_version": STAGE3_GENERATOR_CONTRACT_VERSION,
        "managed_by": MANAGED_BY, "generated_at": now_utc(),
        "professor": professor,
        "profile_fingerprint": current_profile_fp,
        "profile_path": args.profile,
        "input_fingerprints": input_fps,
        "directions": updated_directions,
        "cross_direction_groups": final_groups,
        "cache": {"render": {CANDIDATES_MD: {"sha256": body_sha}}},
    }
    if isinstance((state or {}).get("validator"), dict):
        retained = carry_stage3_validator(
            state["validator"], processed_scopes,
            correction=bool(correction), render_sha=body_sha)
        if retained:
            new_state["validator"] = retained
    # Local transaction (issue #66 r10 §2): stage both files, install the
    # local Markdown first, and install the candidate state LAST — the state
    # replace is the only business commit point. The program level is NOT part
    # of this transaction: finalize never reads or writes 套磁想法候选总览.md /
    # _contact_projections.json, so another professor's state, a stale or
    # missing overview, or a corrupt projection registry can never block or
    # re-judge this commit. The derived overview is rebuilt from committed
    # states by `stage3-rebuild-overview` after terminal validation.
    state_path = professor_dir / CANDIDATE_STATE
    try:
        staged_pair_commit([
            (md_path, render_frontmatter(state_fingerprint, body_sha) + body),
            (state_path, json.dumps(new_state, ensure_ascii=False, sort_keys=True,
                                    indent=1) + "\n"),
        ])
    except Exception as exc:
        fail("local_pair_commit_failed", str(exc), target=str(state_path))
    emit({
        "status": "ok", "professor": professor,
        "state_path": str(professor_dir / CANDIDATE_STATE),
        "candidates_md": str(md_path),
        "overview_md": str(program_root / "教授研究" / CANDIDATES_OVERVIEW),
        "directions": [{"direction_id": d.get("direction_id"),
                        "stage3_status": d.get("stage3_status"),
                        "mode": d.get("mode"),
                        "candidates": len(d.get("candidates") or [])}
                       for d in updated_directions],
        "skipped_direction_ids": skipped_out,
        # r13 §5.5: the reported correction set is what this run actually
        # replaced — never a scope the admission filters kept out.
        "corrected": sorted(correction_dids & scoped_dids),
        "corrected_groups": sorted(key.split(":", 1)[1] for key in correction
                                   if key.startswith("group:")),
        "cross_direction_groups": [{"group_id": g["group_id"],
                                     "direction_ids": g["direction_ids"],
                                     "candidates": len(g.get("candidates") or [])}
                                    for g in final_groups],
        "dropped_cross_direction": dropped_groups,
        "reused": reused, "md_sha256": body_sha,
    })


def cmd_stage3_rebuild_overview(args) -> None:
    """Rebuild the program-level candidates overview from committed states.

    The overview is a human-facing projection derived ONLY from committed
    professor-local candidate states (issue #66 r10 §3): the local Markdown
    contributes a link path and never machine facts; `_contact_projections.json`
    is not read and not written; manual-edit protection is projection-local
    (frontmatter render_sha256 must match the current body, otherwise the
    rebuild fails closed with manual_markdown_changed and nothing changes).
    Any discovered state that is malformed or cannot be exactly identity-
    migrated fails the whole rebuild BEFORE the overview write — no partial
    overview is ever published.
    """
    program_root = Path(args.program_root)
    research_root = (program_root / "教授研究").resolve()
    if not research_root.is_dir():
        fail("invalid_params", f"program_root has no 教授研究 directory: {program_root}")
    discovered: dict[str, Path] = {}
    for state_path in sorted(research_root.rglob(CANDIDATE_STATE)):
        try:
            parent = state_path.parent.resolve()
            relative = parent.relative_to(research_root)
        except (OSError, ValueError):
            fail("state_outside_program_root", str(state_path),
                 message="discovered candidate state resolves outside the 教授研究 root")
        discovered.setdefault(relative.as_posix(), parent)
    records = []
    for identity in sorted(discovered):
        professor_dir = discovered[identity]
        state, state_error = strict_candidate_state(professor_dir)
        if state is None and state_error is None:
            # The state vanished between discovery and read: this professor
            # currently has no committed state and contributes no rows.
            continue
        if state_error:
            fail(state_error,
                 "candidate state cannot be included in the program overview",
                 professor_identity=identity, professor_dir=str(professor_dir))
        records.append((identity, professor_dir, state))
    direction_entries, cross_entries = [], []
    for identity, professor_dir, state in records:
        display = state.get("professor") or identity
        md_rel = rel_path(professor_dir / CANDIDATES_MD, research_root)
        for row in sorted((state.get("directions") or []),
                          key=lambda item: str(item.get("direction_id") or "")):
            direction_entries.append({
                "professor": display, "name_ja": row.get("name_ja"),
                "candidates": row.get("candidates") or [],
                "priority": row.get("priority"),
                "_candidates_md_rel": md_rel})
        for row in sorted((state.get("cross_direction_groups") or []),
                          key=lambda item: str(item.get("group_id") or "")):
            cross_entries.append({
                "professor": display, "group_id": row.get("group_id"),
                "direction_ids": row.get("direction_ids") or [],
                "candidates": row.get("candidates") or [],
                "_candidates_md_rel": md_rel})
    body = render_candidates_overview(direction_entries, research_root,
                                      cross_groups=cross_entries)
    overview_path = research_root / CANDIDATES_OVERVIEW
    if overview_path.is_file():
        try:
            existing_text = overview_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            fail("overview_unreadable", str(exc), target=str(overview_path))
        header, existing_body = split_frontmatter(existing_text)
        if not isinstance(header, dict) or header.get("managed_by") != MANAGED_BY or \
                header.get("render_sha256") != sha256_text(existing_body):
            soft_exit("needs_decision", "manual_markdown_changed",
                      target=str(overview_path))
    body_sha = sha256_text(body)
    projection_fingerprint = sha256_obj({"projection": CANDIDATES_OVERVIEW,
                                         "body": body_sha})
    try:
        atomic_write(overview_path,
                     render_frontmatter(projection_fingerprint, body_sha) + body)
    except Exception as exc:
        fail("overview_write_failed", str(exc), target=str(overview_path))
    emit({
        "status": "ok",
        "overview_md": str(overview_path),
        "sha256": body_sha,
        "professor_count": len(records),
        "direction_rows": len(direction_entries),
        "cross_direction_rows": len(cross_entries),
        "professors": [{"professor_identity": identity,
                        "professor": state.get("professor"),
                        "directions": len(state.get("directions") or []),
                        "cross_direction_groups":
                            len(state.get("cross_direction_groups") or [])}
                       for identity, _, state in records],
    })


def _stage4_cross_group(pack: dict, group_entry: dict) -> list[dict] | None:
    """Resolve a cross-direction group's participants against the CURRENT pack.

    Returns the participant pack directions in the group's recorded
    direction_ids order, or None when anything fails to exact-join (unknown
    direction id, changed fingerprint, malformed bookkeeping) — the caller
    fails closed with needs_refresh instead of compiling a stale email."""
    direction_ids = group_entry.get("direction_ids")
    recorded = group_entry.get("direction_fingerprints")
    if not isinstance(direction_ids, list) or len(set(direction_ids)) < 2 \
            or not isinstance(recorded, dict) or not recorded:
        return None
    by_id = {direction_machine_id(d): d for d in pack.get("directions") or []}
    participants = []
    for direction_id in direction_ids:
        pack_direction = by_id.get(direction_id)
        if pack_direction is None \
                or recorded.get(direction_id) != pack_direction.get("input_fingerprint"):
            return None
        participants.append(pack_direction)
    return participants


EMAIL_SOURCE_HASH_FIELDS = (
    "email_id", "direction_ids", "directions", "idea", "papers", "gaps",
    "red_lines", "allowed_sources", "contact_evidence", "cross_direction",
)


def email_source_hash(entry: dict) -> str:
    """Return the canonical Stage-4 → Stage-5 fact hash for one email row."""
    return sha256_obj({key: entry[key] for key in EMAIL_SOURCE_HASH_FIELDS})


def compile_email_entry(pack: dict, state_direction: dict, pack_direction: dict,
                        idea: dict, note: str, program_root: Path,
                        profile_fp: str | None, papers_override: list[str] | None = None,
                        contact_evidence: dict | None = None,
                        group_entry: dict | None = None,
                        participant_directions: list[dict] | None = None) -> dict:
    """Compile one v2 email entry (issue #8 §8.2).

    Identity: direction_ids provenance (sorted, so A+B == B+A) and an email_id
    built from the canonical direction scope + idea id — never the
    collection_key. A cross-direction idea joins evidence against the UNION of
    its participants' slices; every gap row keeps the direction_ids union that
    actually contains it, and shared papers appear once by item_key."""
    # A cross-direction idea joins evidence against the UNION of its
    # participants' slices (owner included); per-direction ideas keep the
    # single-slice indexes. Duplicate (item_key, gap_id) identities resolve to
    # their first occurrence in direction_ids order — never re-invented.
    slice_directions = participant_directions or [pack_direction]
    direction_ids = sorted(idea.get("direction_ids")
                           or [pack_direction.get("direction_id")
                               or direction_machine_id(pack_direction)])
    gap_records: dict = {}
    blacklist: dict = {}
    paper_meta: dict = {}
    for slice_direction in slice_directions:
        for gap in slice_direction.get("gap_shortlist", []) + slice_direction.get("gaps_excluded", []):
            gap_records.setdefault((gap["item_key"], gap["gap_id"]), gap)
        for banned in slice_direction.get("completed_gap_blacklist", []):
            blacklist.setdefault((banned["item_key"], banned["gap_id"]), banned)
        for paper in direction_papers(pack, slice_direction):
            paper_meta.setdefault(paper["item_key"], paper)
    for slice_direction in slice_directions:
        for gap in slice_direction.get("gap_shortlist", []) + slice_direction.get("gaps_excluded", []):
            paper_meta.setdefault(gap["item_key"], {
                "item_key": gap["item_key"], "title": gap.get("paper_title"),
                "year": gap.get("paper_year"), "authorship": gap.get("authorship")})
    papers_out = []
    candidate_papers = idea.get("papers") or []
    if papers_override:
        by_key = {paper.get("item_key"): paper for paper in candidate_papers}
        candidate_papers = [by_key[key] for key in papers_override]
    for paper in candidate_papers:
        meta = paper_meta.get(paper.get("item_key"))
        if not meta:
            fail("unknown_paper_id", f"candidate paper outside input pack: {paper.get('item_key')}")
        papers_out.append({"item_key": meta["item_key"],
                           "direction_ids": sorted(paper.get("direction_ids")
                                                   or [pack_direction.get("direction_id")
                                                       or direction_machine_id(pack_direction)]),
                           "title": meta.get("title"),
                           "year": meta.get("year"), "authorship": meta.get("authorship"),
                           "fit_note": paper.get("fit_note") or ""})
    gaps_out = []
    for ref in idea.get("gap_refs") or []:
        key = (ref.get("item_key"), ref.get("gap_id"))
        gap = gap_records.get(key)
        if gap:
            status = gap.get("status")
            email_use = ("remaining_only" if status == "partial" else
                         "anchor_with_caveat" if status == "unknown" else "anchor")
            gaps_out.append({
                "item_key": gap["item_key"], "gap_id": gap["gap_id"],
                "direction_id": ref.get("direction_id"),
                "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                "quote": gap.get("quote"), "translation_zh": gap.get("translation_zh"),
                "source": gap.get("source"), "page": gap.get("page"),
                "status": status, "evidence": gap.get("evidence"),
                "confidence": gap.get("confidence"),
                "completed_part": gap.get("completed_part"),
                "remaining_gap": gap.get("remaining_gap"),
                "email_use": email_use,
                 "zotero_key": gap["item_key"]})
            continue
        done = blacklist.get(key)
        if done:
            gaps_out.append({
                "item_key": done["item_key"], "gap_id": done["gap_id"],
                "direction_id": ref.get("direction_id"),
                "paper_title": done.get("paper_title"), "paper_year": done.get("paper_year"),
                "quote": done.get("quote_trunc"), "translation_zh": done.get("translation_zh"),
                "source": None, "page": None,
                "status": "done_by_self", "evidence": done.get("evidence"),
                "confidence": done.get("confidence"),
                "completed_part": None, "remaining_gap": None,
                "email_use": "extension_context_only",
                 "zotero_key": done["item_key"]})
            continue
        fail("unknown_reference_id", f"candidate gap outside input pack: {key}")
    if group_entry:
        red_lines = []
        seen_red = set()
        for slice_direction in slice_directions:
            for red in slice_direction.get("red_lines") or []:
                marker = (red.get("scope"), red.get("text"))
                if marker not in seen_red:
                    seen_red.add(marker)
                    red_lines.append(red)
    else:
        red_lines = list(pack_direction.get("red_lines") or [])
    candidate_red = idea.get("red_lines") or []
    for text in candidate_red:
        red_lines.append({"scope": "candidate", "text": text,
                          "banned_phrases": idea.get("banned_phrases") or []})
    primary = slice_directions[0]
    narrative = primary.get("narrative") or {}
    positioning = [block.get("text", "") for block in narrative.get("positioning", [])]
    for slice_direction in slice_directions[1:]:
        narrative_other = slice_direction.get("narrative") or {}
        for block in narrative_other.get("positioning", []):
            text = block.get("text", "")
            if text and text not in positioning:
                positioning.append(text)
    allowed = {"user_note", f"idea:{idea.get('id')}", "profile.interest", "template"}
    for paper in papers_out:
        allowed.add(f"paper:{paper['item_key']}")
    for gap in gaps_out:
        allowed.add(f"gap:{gap['gap_id']}")
        allowed.add(f"later:{gap['item_key']}")
    idea_block = {"id": idea.get("id"), "title": idea.get("title"),
                  "idea_zh": idea.get("idea_zh") or ""}
    email_id = f"{pack.get('professor')}::{'+'.join(direction_ids)}::{idea.get('id')}"
    anchorable_gaps = [g for g in gaps_out if g["email_use"] in ("anchor", "remaining_only", "anchor_with_caveat")]
    entry = {
        "email_id": email_id,
        "professor": pack.get("professor"),
        "professor_dir": pack.get("professor_dir"),
        "direction_ids": direction_ids,
        "directions": [{"direction_id": direction_machine_id(d),
                        "name_ja": d.get("name_ja"), "name_zh": d.get("name_zh")}
                       for d in slice_directions],
        "name_ja": primary.get("name_ja"), "name_zh": primary.get("name_zh"),
        "collection_key": primary.get("collection_key"),
        "idea": idea_block,
        "user_note": primary.get("user_note") or "",
        "papers": papers_out,
        "gaps": gaps_out,
        "anchorable_gaps": [g["gap_id"] for g in anchorable_gaps],
        "red_lines": red_lines,
        "soft_materials": {"credibility": primary.get("credibility"),
                           "positioning": positioning},
        "profile": {"fingerprint": profile_fp, "fields": idea.get("_profile_fields") or {}},
        "allowed_sources": sorted(allowed),
        "fingerprints": {"input": pack_direction.get("input_fingerprint"),
                         "profile": profile_fp,
                         "candidate_state": idea.get("_state_fingerprint")},
        "user_supplement": note or "",
        "contact_evidence": contact_evidence,
        "cross_direction": (
            {"group_id": group_entry.get("group_id"),
             "direction_ids": list(group_entry.get("direction_ids") or []),
             "direction_fingerprints": dict(group_entry.get("direction_fingerprints") or {})}
            if group_entry else None),
    }
    # contact_evidence is a fact field (the frozen recipient snapshot), so it
    # belongs in the pack integrity hash: a refrozen snapshot always yields a
    # new source_hash, never a silent in-place substitution. cross_direction
    # joins it so a re-participated idea re-hashes too.
    entry["source_hash"] = email_source_hash(entry)
    return entry


def validate_papers_override(idea: dict, override: Any, context: str) -> list[str] | None:
    """Validate the user-selected paper order without accepting metadata."""
    if override is None:
        return None
    if not isinstance(override, list):
        fail("invalid_papers_override", f"{context}: papers_override must be a list of item keys")
    if not override:
        return None
    if any(not isinstance(key, str) or not key.strip() for key in override):
        fail("invalid_papers_override", f"{context}: papers_override entries must be non-empty strings")
    if len(set(override)) != len(override):
        fail("invalid_papers_override", f"{context}: papers_override contains duplicate item keys")
    allowed = {paper.get("item_key") for paper in idea.get("papers") or []}
    unknown = [key for key in override if key not in allowed]
    if unknown:
        fail("invalid_papers_override", f"{context}: item keys outside candidate papers: {unknown}")
    return list(override)


def _selection_direction_ids(select: dict, packs: dict) -> tuple[list[str] | None, str | None]:
    """Resolve a selection entry's canonical direction_ids (issue #8 §8.1).

    v2 entries carry direction_id/direction_ids directly. The deprecated
    collection_key path resolves ONLY through the pack's exact machine mapping
    (unique collection_key → direction_id); ambiguous or missing mappings fail
    closed with legacy_direction_identity instead of guessing."""
    professor_dir = str(select.get("professor_dir") or "")
    pack = packs.get(professor_dir)
    explicit = select.get("direction_ids") or (
        [select.get("direction_id")] if select.get("direction_id") else None)
    if explicit:
        ids = sorted({str(x).strip() for x in explicit if str(x).strip()})
        return (ids or None), None
    ckey = select.get("collection_key")
    if not ckey or pack is None:
        return None, "legacy_direction_identity"
    matches = [direction_machine_id(d) for d in pack.get("directions") or []
               if d.get("collection_key") == ckey]
    unique = sorted(set(matches))
    if len(unique) != 1:
        return None, "legacy_direction_identity"
    return unique, None


def validate_stage4_selections(selects: Any, states: dict, packs: dict) -> None:
    """Validate the complete selection batch before any formal file is written."""
    if not isinstance(selects, list) or not selects:
        fail("invalid_params", "selection input has no selections")
    seen_scopes = set()
    seen_email_ids = set()
    for index, select in enumerate(selects):
        if not isinstance(select, dict):
            fail("invalid_selection", f"selection[{index}] must be an object")
        professor = select.get("professor")
        professor_dir = Path(select.get("professor_dir") or "")
        if not isinstance(professor, str) or not professor.strip() or not professor_dir.is_dir():
            fail("invalid_selection", f"selection[{index}] is missing professor or professor_dir")
        direction_ids, identity_error = _selection_direction_ids(select, packs)
        if identity_error or not direction_ids:
            fail("legacy_direction_identity",
                 f"selection[{index}] ({professor}) cannot be mapped to canonical direction_ids "
                 "through an exact machine relation; re-run stage 3 for this professor")
        # The duplicate scope is formal identity: canonical professor_dir plus the
        # machine-normalized direction set. Display text can never split or merge
        # a scope, so rewriting it cannot bypass this check (issue #67 R67-G1-9).
        scope_key = (canonical_professor_dir(select.get("professor_dir")),
                     tuple(direction_ids))
        if scope_key in seen_scopes:
            fail("duplicate_selection",
                 f"duplicate professor+direction-scope selection: {professor}::{'+'.join(direction_ids)}")
        seen_scopes.add(scope_key)
        state = states.get(str(professor_dir))
        pack = packs.get(str(professor_dir))
        state_direction = next((d for d in (state or {}).get("directions", [])
                                if d.get("direction_id") in direction_ids), None) \
            if len(direction_ids) == 1 else None
        pack_direction = next((d for d in (pack or {}).get("directions", [])
                               if direction_machine_id(d) in direction_ids), None) \
            if len(direction_ids) == 1 else None
        if len(direction_ids) == 1 and not (state_direction and pack_direction):
            continue
        candidates = {idea.get("id"): idea for idea in (state_direction or {}).get("candidates", [])}
        # Explicit cross-direction ideas live in their own groups: look the id
        # up in the group whose sorted direction_ids match this selection scope.
        cross_by_id = {}
        if len(direction_ids) >= 2:
            for group in (state or {}).get("cross_direction_groups") or []:
                if isinstance(group, dict) \
                        and sorted(group.get("direction_ids") or []) == direction_ids:
                    cross_by_id = {entry.get("id"): entry
                                   for entry in group.get("candidates") or []}
        ideas = select.get("ideas")
        if not isinstance(ideas, list):
            fail("invalid_selection",
                 f"{professor}::{'+'.join(direction_ids)}: ideas must be a list")
        seen_ideas = set()
        for idea_index, idea_input in enumerate(ideas):
            if not isinstance(idea_input, dict):
                fail("invalid_selection",
                     f"{professor}::{'+'.join(direction_ids)}: ideas[{idea_index}] must be an object")
            idea_id = idea_input.get("id")
            if idea_id in seen_ideas:
                fail("duplicate_idea_id",
                     f"duplicate idea id in {professor}::{'+'.join(direction_ids)}: {idea_id}")
            seen_ideas.add(idea_id)
            idea = candidates.get(idea_id)
            if idea is None and idea_id in cross_by_id:
                idea = cross_by_id[idea_id]
            if idea is None:
                # An explicit selection that matches nothing must fail the whole
                # batch up front: silently skipping it would write the remaining
                # ideas while the user believes this one was selected too.
                fail("unknown_idea_id",
                     f"{professor}::{'+'.join(direction_ids)}: unknown idea id: {idea_id}")
            override = validate_papers_override(
                idea, idea_input.get("papers_override"),
                f"{professor}::{'+'.join(direction_ids)}::{idea_id}")
            email_id = f"{professor}::{'+'.join(direction_ids)}::{idea_id}"
            if email_id in seen_email_ids:
                fail("duplicate_email_id", f"duplicate email id: {email_id}")
            seen_email_ids.add(email_id)


def stage4_local_pair_paths(professor_dir: Path) -> tuple[Path, Path]:
    """The professor-local Stage-4 pair owned by one canonical professor_dir."""
    return (Path(professor_dir) / SELECTION_FILE, Path(professor_dir) / EMAIL_PACK)


def canonical_professor_dir(value: Any) -> str:
    """Canonical Stage-4 transaction identity (issue #67 R67-G1-9).

    Display names can collide and one directory can be spelled in more than one
    way, so grouping uses the resolved path while each machine row keeps the
    caller-supplied path verbatim."""
    raw = Path(str(value or ""))
    try:
        return str(raw.resolve())
    except OSError:
        return str(raw)


def stage4_professor_row(professor: Any, professor_dir: Any, status: str,
                         reason_code: str | None = None, **extra) -> dict:
    row = {"professor": professor, "professor_dir": str(professor_dir or ""),
           "status": status, "reason_code": reason_code,
           "selection_file": None, "email_pack": None}
    row.update(extra)
    return row


def _stage4_failure_row(row: dict, payload: dict) -> dict:
    """Turn one expected business payload into that professor's failed row.

    A failed row keeps selection_file/email_pack null: nothing was committed, and
    a caller must not mistake a diagnostic path for written authority."""
    failed = dict(row)
    failed["status"] = payload.get("status") or "error"
    for key, value in payload.items():
        if key not in ("professor", "professor_dir"):
            failed[key] = value
    failed["selection_file"] = None
    failed["email_pack"] = None
    return failed


def _stage4_professor_commit(program_root: Path, professor_dir: Path, selects: list,
                             current_profile_fp: str | None, evidence: tuple,
                             row: dict) -> dict:
    """Run the whole Stage-4 transaction for ONE canonical professor_dir.

    Only this professor's candidate state, input pack and professor-local prior
    selection are read: an unrelated professor is never a prerequisite (issue #67
    R67-G1-2). Inside this professor nothing is relaxed — the same exact identity,
    fingerprint, gap-join and papers_override validation still fails the whole
    professor through one pair-atomic write (R67-G1-3)."""
    professor = row.get("professor")
    if not str(professor_dir):
        fail("invalid_selection", "该条目没有 professor_dir，无法建立教授事务边界。")
    containment = professor_dir_containment_error(professor_dir, program_root)
    if containment:
        fail(containment, "越界 professor_dir：该教授零本地写入、零外部写入。",
             allowed_root=str((program_root / "教授研究").resolve()))
    selection_path, email_pack_path = stage4_local_pair_paths(professor_dir)
    # A half-present local pair is a corrupt authority: never guess which file to
    # trust and never mint the missing counterpart.
    if selection_path.exists() != email_pack_path.exists():
        fail("local_pair_incomplete",
             f"professor-local Stage-4 pair is half-present in {professor_dir}; "
             "resolve the pair before finalizing instead of guessing which half is authority")
    canonical = canonical_professor_dir(professor_dir)
    professor_pack, _pack_error = load_input_pack(professor_dir)
    professor_state, state_error = load_candidate_state(professor_dir, professor_pack)
    if professor_state is None and state_error:
        soft_exit("needs_refresh", state_error,
                  message="候选状态无法按机器身份精确迁移：重跑阶段 3 重建 v2 状态。该教授未写入任何文件。")
    packs: dict = {}
    states: dict = {}
    for key in {str(select.get("professor_dir") or "") for select in selects} | {str(professor_dir)}:
        if key:
            packs[key] = professor_pack
            states[key] = professor_state

    prior_selection, prior_error = read_json_file(selection_path)
    if prior_error not in (None, "not_found"):
        fail("invalid_selection", f"existing local selection unreadable: {selection_path}: {prior_error}")
    if prior_selection is not None and not isinstance(prior_selection, dict):
        fail("invalid_selection", f"existing local selection must be an object: {selection_path}")
    prior_rows = (prior_selection or {}).get("selections") or []
    if not isinstance(prior_rows, list):
        fail("invalid_selection", f"existing local selection.selections must be a list: {selection_path}")
    for index, old in enumerate(prior_rows):
        if not isinstance(old, dict):
            # A non-object entry in the professor-local prior selection is a
            # corrupt authority: fail closed without rewriting the pair, never
            # silently drop the entry (R67-G1-3).
            fail("invalid_selection",
                 f"existing local selection contains a non-object entry at "
                 f"index {index}: {selection_path}")
        if canonical_professor_dir(old.get("professor_dir")) != canonical:
            fail("local_selection_foreign_row",
                 f"existing local selection in {professor_dir} carries a row bound to "
                 f"{old.get('professor_dir')}; a professor-local container may not hold "
                 "another professor's selection")
        key = str(old.get("professor_dir") or "")
        if key:
            packs.setdefault(key, professor_pack)
            states.setdefault(key, professor_state)

    resolved_selects = []
    for select in selects:
        ids, identity_error = _selection_direction_ids(select, packs)
        if identity_error or not ids:
            fail("legacy_direction_identity",
                 f"selection for {select.get('professor')} cannot be mapped to canonical "
                 "direction_ids through an exact machine relation; re-run stage 3 for this "
                 "professor. This professor wrote no file.")
        resolved_selects.append({**select, "direction_ids": ids})
    # The container already fixes the professor: inside one canonical
    # professor_dir the scope is only the direction set, so a display-name change
    # neither preserves a stale row nor splits one scope into two (issue #67).
    current_scope = {tuple(s.get("direction_ids") or [])
                     for s in resolved_selects}
    # Same-professor preserved directions are recompiled into the same local pair,
    # so they share this professor's fail-closed outcome instead of being dropped.
    preserved = []
    for old in prior_rows:
        if not isinstance(old, dict):
            continue
        ids, identity_error = _selection_direction_ids(old, packs)
        if ids and tuple(ids) in current_scope:
            continue
        if identity_error or not ids:
            fail("legacy_direction_identity",
                 f"existing local selection entry for {old.get('professor')} cannot be mapped "
                 "to canonical direction_ids through an exact machine relation; re-run stage 3 "
                 "for this professor. This professor wrote no file.")
        if professor_state is None:
            soft_exit("needs_refresh", "candidate_state_missing",
                      direction_ids=ids,
                      message="既有选择对应的候选状态缺失：先重跑阶段 3，再重新选择。该教授未写入任何选择/邮件包。")
        preserved.append({**old, "direction_ids": ids})

    all_selects = preserved + resolved_selects
    preserved_keys = {tuple(p.get("direction_ids") or [])
                      for p in preserved}
    skipped = []

    def record_skip(select_obj: dict, entry: dict) -> None:
        if tuple(select_obj.get("direction_ids") or []) in preserved_keys:
            soft_exit("needs_refresh", "preserved_selection_uncompilable",
                      direction_ids=select_obj.get("direction_ids"),
                      message="既有选择无法按当前候选状态/输入包重编译：先重跑阶段 3，再重新选择。该教授未写入任何选择/邮件包。")
        skipped.append(entry)

    validate_stage4_selections(all_selects, states, packs)
    written_selections = []
    email_entries = []
    evidence_artifact, evidence_error = evidence
    evidence_snapshot = contact_evidence_snapshot(evidence_artifact, evidence_error, professor)
    for select in all_selects:
        select_dir = Path(select.get("professor_dir") or "")
        direction_ids = select.get("direction_ids") or []
        scope = "+".join(direction_ids)
        if not select_dir.is_dir() or not direction_ids:
            record_skip(select, {"professor": professor, "reason": "invalid_selection_input"})
            continue
        state = states.get(str(select_dir))
        pack = packs.get(str(select_dir))
        if state is None:
            record_skip(select, {"professor": professor, "direction_ids": direction_ids,
                                 "reason": "needs_stage3", "detail": "缺 套磁候选状态.json"})
            continue
        if pack is None:
            record_skip(select, {"professor": professor, "direction_ids": direction_ids,
                                 "reason": "needs_refresh", "detail": "missing_input_pack"})
            continue
        if len(direction_ids) == 1:
            pack_direction = next((d for d in pack.get("directions", [])
                                   if direction_machine_id(d) == direction_ids[0]), None)
            state_direction = next((d for d in state.get("directions", [])
                                    if d.get("direction_id") == direction_ids[0]), None)
            if not pack_direction or not state_direction:
                record_skip(select, {"professor": professor, "direction_ids": direction_ids,
                                     "reason": "needs_refresh",
                                     "detail": "direction not in state/pack"})
                continue
            if state.get("input_fingerprints", {}).get(direction_ids[0]) != \
                    pack_direction.get("input_fingerprint"):
                soft_exit("needs_refresh", "source_fingerprint_changed",
                          direction_id=direction_ids[0],
                          message="输入包已变化：先重跑阶段 3 刷新候选，再重新选择。该教授未写入任何选择/邮件包。")
            if state.get("profile_fingerprint") != current_profile_fp:
                soft_exit("needs_refresh", "profile_changed",
                          direction_id=direction_ids[0],
                          message="profile 已变化：重跑阶段 3 后再选择。该教授未写入任何选择/邮件包。")
        else:
            pack_direction = next((d for d in pack.get("directions", [])
                                   if direction_machine_id(d) == direction_ids[0]), None)
            state_direction = None
            if pack_direction is None:
                record_skip(select, {"professor": professor, "direction_ids": direction_ids,
                                     "reason": "needs_refresh", "detail": "direction not in pack"})
                continue
            if state.get("profile_fingerprint") != current_profile_fp:
                soft_exit("needs_refresh", "profile_changed",
                          direction_ids=direction_ids,
                          message="profile 已变化：重跑阶段 3 后再选择。该教授未写入任何选择/邮件包。")
        selected_ideas = []
        for idea_input in select.get("ideas", []):
            idea_id = idea_input.get("id")
            idea = None
            group_entry = None
            if len(direction_ids) == 1:
                idea = next((c for c in state_direction.get("candidates", [])
                             if c.get("id") == idea_id), None)
            if idea is None:
                group_entry = next(
                    (group for group in state.get("cross_direction_groups") or []
                     if isinstance(group, dict)
                     and sorted(group.get("direction_ids") or []) == direction_ids
                     and any(c.get("id") == idea_id for c in group.get("candidates") or [])),
                    None)
                if group_entry is not None:
                    idea = next(c for c in group_entry.get("candidates") or []
                                if c.get("id") == idea_id)
            if idea is None:
                skipped.append({"professor": professor, "direction_ids": direction_ids,
                                "idea": idea_id, "reason": "unknown_idea_id"})
                continue
            participants = None
            if len(direction_ids) >= 2:
                participants = _stage4_cross_group(pack, group_entry or {})
                if participants is None:
                    soft_exit("needs_refresh", "cross_participant_changed",
                              direction_ids=direction_ids, idea=idea_id,
                              message="跨方向想法引用的参与方向已变化或指纹过期：先重跑阶段 3 刷新候选，再重新选择。该教授未写入任何选择/邮件包。")
            idea_full = dict(idea)
            idea_full["red_lines"] = idea.get("red_lines") or []
            papers_override = validate_papers_override(
                idea, idea_input.get("papers_override"),
                f"{professor}::{scope}::{idea_id}")
            entry = compile_email_entry(
                pack, state_direction, pack_direction, idea_full,
                idea_input.get("note") or "", program_root, current_profile_fp,
                papers_override, evidence_snapshot,
                group_entry=group_entry if len(direction_ids) >= 2 else None,
                participant_directions=participants)
            email_entries.append(entry)
            selected_ideas.append(idea_input)
        if not selected_ideas:
            continue
        select = dict(select, ideas=selected_ideas, direction_ids=direction_ids)
        primary = next((d for d in pack.get("directions", [])
                        if direction_machine_id(d) == direction_ids[0]), {})
        written_selections.append({
            "professor": professor,
            "professor_dir": str(professor_dir),
            "direction_ids": direction_ids,
            "zotero_collection": (state_direction or {}).get("zotero_collection")
            or select.get("zotero_collection"),
            "name_ja": primary.get("name_ja"), "name_zh": primary.get("name_zh"),
            "collection_key": primary.get("collection_key"),
            "reason": select.get("reason"),
            "ideas": [{"id": i.get("id"), "note": i.get("note") or "",
                       "papers_override": i.get("papers_override") or None}
                      for i in select.get("ideas", [])]})
    if skipped or not written_selections:
        # R67-G1-3: inside ONE professor any entry failure fails the whole
        # batch with zero writes -- a valid remainder must never be partially
        # committed while another entry of the same professor failed. skipped
        # carries the exact per-entry reason (missing input pack, needs_stage3,
        # direction not in state/pack, ...) so the row stays actionable.
        fail("validation_failed", "selection batch has uncompilable entries",
             skipped=skipped)
    selection_doc = {
        "schema": STAGE4_LOCAL_SCHEMA, "kind": SELECTION_KIND,
        "identity_version": DIRECTION_IDENTITY_VERSION,
        "managed_by": MANAGED_BY, "program_root": str(program_root),
        "professor": professor, "professor_dir": str(professor_dir),
        "generated_at": now_utc(),
        "profile_fingerprint": current_profile_fp,
        "selections": written_selections}
    email_pack_doc = {
        "schema": STAGE4_LOCAL_SCHEMA, "kind": EMAIL_PACK_KIND,
        "identity_version": DIRECTION_IDENTITY_VERSION,
        "managed_by": MANAGED_BY, "program_root": str(program_root),
        "professor": professor, "professor_dir": str(professor_dir),
        "generated_at": now_utc(),
        "profile_fingerprint": current_profile_fp,
        "emails": email_entries}
    atomic_json_many([(selection_path, selection_doc), (email_pack_path, email_pack_doc)])
    return stage4_professor_row(
        professor, professor_dir, "ok", None,
        selection_file=str(selection_path), email_pack=str(email_pack_path),
        selected_directions=[
            f"{professor} · {'+'.join(s.get('direction_ids') or [])}"
            for s in written_selections],
        emails_compiled=len(email_entries), skipped=skipped)


def stage4_professor_transaction(program_root: Path, professor_dir: Any, selects: list,
                                 current_profile_fp: str | None,
                                 evidence: tuple) -> dict:
    """One professor's Stage-4 transaction as a machine row, with no process exit.

    Expected professor-scoped business failures become that professor's row; an
    unexpected programming error keeps propagating after `atomic_json_many()` has
    rolled the current pair back, so it is never downgraded to a business row."""
    professor_dir = Path(str(professor_dir))
    professor = next((s.get("professor") for s in selects
                      if isinstance(s, dict) and s.get("professor")), None)
    row = stage4_professor_row(professor, professor_dir, "error")
    try:
        with professor_business_channel():
            return _stage4_professor_commit(program_root, professor_dir, selects,
                                            current_profile_fp, evidence, row)
    except ProfessorBusinessFailure as failure:
        return _stage4_failure_row(row, failure.payload)


def cmd_stage4_finalize(args) -> None:
    """Commit Stage-4 authority per professor and emit one aggregate machine result."""
    program_root = Path(args.program_root)
    selection_input, error = read_json_file(Path(args.selection_input))
    if error or not isinstance(selection_input, dict):
        fail("invalid_params", f"selection input unreadable: {args.selection_input}")
    current_profile_fp = profile_fingerprint(args.profile)
    selects = selection_input.get("selections") or []
    if not isinstance(selects, list) or not selects:
        fail("invalid_params", "selection input has no selections")
    # Group by canonical professor_dir in first-appearance order: the display name
    # is business content, never the transaction key (issue #67 R67-G1-9).
    groups: dict = {}
    for index, select in enumerate(selects):
        if not isinstance(select, dict):
            fail("invalid_selection", f"selections[{index}] must be an object")
        if not str(select.get("professor") or "").strip() and \
                not str(select.get("professor_dir") or "").strip():
            fail("invalid_selection",
                 f"selections[{index}] carries neither professor nor professor_dir")
        key = canonical_professor_dir(select.get("professor_dir")) \
            if str(select.get("professor_dir") or "").strip() else f"missing-professor-dir#{index}"
        groups.setdefault(key, []).append(select)
    evidence = load_contact_evidence(program_root)
    results = []
    for group in groups.values():
        results.append(stage4_professor_transaction(
            program_root, group[0].get("professor_dir"), group, current_profile_fp, evidence))
    committed = [row for row in results if row["status"] == "ok"]
    status = "ok" if len(committed) == len(results) else ("partial" if committed else "error")
    emit({"status": status, "results": results})
    if not committed:
        sys.exit(1)


STAGE4_MIGRATION_COMMITTED = ("migrated", "already_local", "not_applicable")


def _stage4_migration_result(outcome: str, source: dict | None = None, **extra) -> None:
    """Single machine result + exit code for one professor's migration attempt.

    Only outcomes that leave a usable (or deliberately untouched) local pair exit
    0; every other expected migration outcome is that professor's own failure and
    the caller keeps routing the remaining professors."""
    payload = {"status": outcome}
    for key in ("professor", "professor_dir", "reason_code", "selection_file", "email_pack"):
        payload[key] = (source or {}).get(key)
    payload.update(extra)
    emit(payload)
    if outcome in STAGE4_MIGRATION_COMMITTED:
        sys.exit(0)
    sys.exit(1 if outcome == "error" else 2)


def cmd_stage4_migrate_local(args) -> None:
    """Scoped legacy migration: one canonical professor_dir, current facts only.

    The legacy program-level selection is read as a row source for THIS professor
    and is never modified; the legacy program-level email pack is never a source of
    truth, so the local email facts are recompiled from current Stage-3 state/input
    (issue #67 R67-G1-5 / R67-G1-11)."""
    program_root = Path(args.program_root)
    professor_dir = Path(str(args.professor_dir))
    containment = professor_dir_containment_error(professor_dir, program_root)
    if containment:
        fail(containment, "professor_dir must be inside program_root/教授研究",
             professor_dir=str(professor_dir),
             allowed_root=str((program_root / "教授研究").resolve()))
    selection_path, email_pack_path = stage4_local_pair_paths(professor_dir)
    canonical = canonical_professor_dir(professor_dir)
    if selection_path.exists() and email_pack_path.exists():
        prior, prior_error = read_json_file(selection_path)
        if prior_error or not isinstance(prior, dict):
            fail("invalid_selection",
                 f"existing local selection unreadable: {selection_path}: {prior_error}")
        rows = prior.get("selections") or []
        _stage4_migration_result(
            "already_local",
            {"professor": prior.get("professor"), "professor_dir": str(professor_dir),
             "selection_file": str(selection_path), "email_pack": str(email_pack_path)},
            migrated_rows=len(rows) if isinstance(rows, list) else 0,
            message="完整 professor-local pair 已存在：byte-for-byte 保留，不覆盖。")
    if selection_path.exists() or email_pack_path.exists():
        _stage4_migration_result(
            "local_pair_incomplete",
            {"professor": None, "professor_dir": str(professor_dir),
             "reason_code": "local_pair_incomplete"},
            message="professor-local Stage-4 pair 只存在一个文件：整批 fail closed、零写入，"
                    "不猜测哪一份更可信，也不生成另一半。")
    legacy_path = program_root / "教授研究" / SELECTION_FILE
    legacy, legacy_error = read_json_file(legacy_path)
    legacy_rows = ((legacy or {}).get("selections") or []) if isinstance(legacy, dict) else []
    scoped = [row for row in legacy_rows
              if isinstance(row, dict)
              and canonical_professor_dir(row.get("professor_dir")) == canonical]
    if not scoped:
        # An unreadable legacy file or another professor's rows are never this
        # professor's prerequisite: normal local finalize compiles from facts.
        _stage4_migration_result(
            "not_applicable",
            {"professor": None, "professor_dir": str(professor_dir),
             "reason_code": "legacy_selection_unreadable"
             if legacy_error not in (None, "not_found") else None},
            migrated_rows=0,
            message="该教授没有可迁移的 legacy 选择行：零迁移写入，直接按当前事实进入正常 local finalize。")
    row = stage4_professor_transaction(program_root, professor_dir, scoped,
                                        profile_fingerprint(args.profile),
                                        load_contact_evidence(program_root))
    if row["status"] == "ok":
        _stage4_migration_result(
            "migrated", row, migrated_rows=len(scoped),
            message="已按当前候选状态/输入包重编译该教授的 local pair；"
                    "legacy global 文件保持原 bytes，仅作历史兼容来源。")
    _stage4_migration_result(row["status"], row)


def find_boshu_analysis(program_root: Path) -> Path | None:
    candidates = ([program_root / "boshu_analysis.json"] if
                  (program_root / "boshu_analysis.json").is_file() else []) + \
        sorted(program_root.glob("*/boshu_analysis.json")) + \
        sorted(program_root.glob("*/*/boshu_analysis.json"))
    return candidates[0] if candidates else None


def load_header_sources(program_root: Path) -> dict:
    info = {}
    info_path = program_root / "info.json"
    if info_path.is_file():
        data, error = read_json_file(info_path)
        if error is None and isinstance(data, dict):
            info = data
    boshu = {}
    boshu_path = find_boshu_analysis(program_root)
    if boshu_path and boshu_path.is_file():
        data, error = read_json_file(boshu_path)
        if error is None and isinstance(data, dict):
            boshu = data
    return {"info": info, "boshu": boshu,
            "info_path": str(info_path) if info_path.is_file() else None,
            "boshu_path": str(boshu_path) if boshu_path else None}


def header_values(sources: dict, email: dict) -> dict:
    info = sources.get("info") or {}
    boshu = sources.get("boshu") or {}
    target = info.get("target") or {}
    term = str(target.get("intake_term") or "").lower()
    month = {"april": "4月", "october": "10月"}.get(term, target.get("intake_term") or "")
    exam_type = boshu.get("exam_type") or {}
    degree = exam_type.get("degree") or "大学院修士課程"
    selection_name = exam_type.get("selection_name") or ""
    batch_match = BATCH_RE.search(selection_name or "")
    batch = batch_match.group(1) if batch_match else ""
    major = ""
    for token in re.findall(r"([\u4e00-\u9fffぁ-んァ-ヶー]+専攻|[\u4e00-\u9fffぁ-んァ-ヶー]+コース)", selection_name):
        major = token
        break
    return {
        "大学": info.get("university") or "", "研究科": info.get("department") or "",
        "専攻": major or info.get("department") or "", "学位": degree,
        "入試批次": batch, "入学年度": str(target.get("intake_year") or ""),
        "入学月": month, "先生名": email.get("professor") or "",
        "出身校": None, "氏名": None,
    }


def subject_line(values: dict) -> str:
    return (f"【入学希望】{values['入学年度']}年{values['入学月']}期 "
            f"{values['学位']}{values['入試批次']}入学に関するご相談")


def compact_name(value: Any) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or "")))


def email_item_is_evidence_seeded(items: dict) -> bool:
    """True when the cached recipient email was seeded from the artifact."""
    sources = (items.get("email") or {}).get("sources") or []
    return bool(sources) and all(
        isinstance(source, dict) and source.get("level") == "contact_evidence"
        for source in sources)


def current_source_fingerprints(sources: dict) -> dict:
    """Return the current canonical fingerprints, or the first unavailable field."""
    fingerprints = {}
    for field, source_key in (("info_json", "info_path"),
                              ("boshu_analysis", "boshu_path")):
        source_path = sources.get(source_key)
        if not isinstance(source_path, str) or not source_path:
            return {"source_fingerprints": fingerprints,
                    "failed_field": f"source_fingerprints.{field}"}
        try:
            mtime = int(Path(source_path).stat().st_mtime)
        except (OSError, ValueError, TypeError, OverflowError):
            return {"source_fingerprints": fingerprints,
                    "failed_field": f"source_fingerprints.{field}"}
        fingerprints[field] = f"{source_path}:{mtime}"
    return {"source_fingerprints": fingerprints, "failed_field": None}


def _fingerprint_failure_kind(recorded: Any, source_path: str) -> str:
    """Distinguish an incompatible representation from a changed mtime."""
    if not isinstance(recorded, str):
        return "format_incompatible"
    prefix = f"{source_path}:"
    if not recorded.startswith(prefix):
        return "format_incompatible"
    raw_mtime = recorded[len(prefix):]
    try:
        parsed_mtime = int(raw_mtime)
    except (ValueError, OverflowError):
        return "format_incompatible"
    if str(parsed_mtime) != raw_mtime:
        return "format_incompatible"
    return "recorded_mtime_mismatch"


def _verify_diagnostic_failure(path: Path, data: Any, reason: str,
                               failed_field: str, diagnostic_kind: str) -> dict:
    return {"ok": False, "reason": reason, "path": str(path), "data": data,
            "failed_field": failed_field, "diagnostic_kind": diagnostic_kind}


def verify_state(professor_dir: Path, sources: dict, decision: dict | None = None,
                 fingerprint_state: dict | None = None) -> dict:
    path = professor_dir / VERIFY_FILE
    data, error = read_json_file(path)
    if error:
        return {"ok": False, "reason": "missing", "path": str(path), "data": None}
    if not isinstance(data, dict):
        return {"ok": False, "reason": "invalid_cache", "path": str(path), "data": data}
    items = (data or {}).get("items")
    if not isinstance(items, dict) or not {"email", "roster", "season", "header",
                                            "subject_batch", "schedule", "consent"}.issubset(items):
        return {"ok": False, "reason": "incomplete", "path": str(path), "data": data}
    allowed_verdicts = {"confirmed", "not_found", "unverified"}
    for key in ("email", "roster", "season", "header", "subject_batch", "schedule", "consent"):
        item = items.get(key)
        if not isinstance(item, dict) or item.get("verdict") not in allowed_verdicts:
            return {"ok": False, "reason": "invalid_cache", "path": str(path), "data": data}
        if not isinstance(item.get("sources", []), list):
            return {"ok": False, "reason": "invalid_cache", "path": str(path), "data": data}
    # Issue-#10 linkage: an escalation voids exactly the trust chain that
    # broke, so a recipient email seeded from the contact-evidence artifact
    # can never outlive the decision that produced it. A needs_refresh
    # decision (frozen snapshot out of sync with upstream) breaks the same
    # chain. Ladder/user-verified entries keep their own 30-day TTL.
    if decision is not None and decision.get("status") in ("escalate", "needs_refresh") and \
            email_item_is_evidence_seeded(items):
        return {"ok": False, "reason": "contact_evidence_escalated",
                "path": str(path), "data": data}
    # Issue-#10 conflict gate: the upstream artifact scopes itself as
    # workflow evidence, NOT the send-time authority — the verify cache is.
    # While an accepted decision stands, a still-usable cache entry holding
    # a DIFFERENT address is a real evidence conflict regardless of
    # provenance: it must be resolved explicitly before generation instead
    # of being silently reseeded (or discovered only at finalize's mismatch
    # guard). Same address in any provenance reuses the cache freely.
    if decision is not None and decision.get("status") not in ("escalate", "needs_refresh") and \
            decision.get("recipient_email"):
        cache_value = str(items["email"].get("value") or "").strip()
        recipient = str(decision["recipient_email"]).strip()
        if cache_value and cache_value.casefold() != recipient.casefold():
            return {"ok": False, "reason": "contact_evidence_verify_conflict",
                    "path": str(path), "data": data}
    warnings = items.get("warnings")
    if not isinstance(warnings, list):
        return {"ok": False, "reason": "invalid_cache", "path": str(path), "data": data}
    if items["email"].get("verdict") == "confirmed" and not str(items["email"].get("value") or "").strip():
        return {"ok": False, "reason": "email_value_missing", "path": str(path), "data": data}
    fingerprint_state = fingerprint_state or current_source_fingerprints(sources)
    if fingerprint_state.get("failed_field"):
        return _verify_diagnostic_failure(
            path, data, "missing_source", fingerprint_state["failed_field"],
            "source_unavailable")
    current_fingerprints = fingerprint_state["source_fingerprints"]
    fps = data.get("source_fingerprints")
    if not isinstance(fps, dict):
        fps = {}
    for field, source_key in (("info_json", "info_path"),
                              ("boshu_analysis", "boshu_path")):
        if fps.get(field) == current_fingerprints[field]:
            continue
        return _verify_diagnostic_failure(
            path, data, "stale_fingerprint", f"source_fingerprints.{field}",
            _fingerprint_failure_kind(fps.get(field), sources[source_key]))
    verified_at = data.get("verified_at") or ""
    try:
        if not isinstance(verified_at, str):
            raise ValueError("verified_at must be a string")
        then = datetime.strptime(verified_at, VERIFY_TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - then > timedelta(days=VERIFY_TTL_DAYS):
            return _verify_diagnostic_failure(
                path, data, "expired", "verified_at", "age_expired")
    except ValueError:
        return _verify_diagnostic_failure(
            path, data, "bad_timestamp", "verified_at", "format_incompatible")
    return {"ok": True, "reason": None, "path": str(path), "data": data}


def gap_job_block(gap: dict) -> dict:
    return {"gap_id": gap["gap_id"], "item_key": gap["item_key"],
            "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
            "quote": truncate(gap.get("quote"), QUOTE_INPUT_CHARS),
            "translation_zh": truncate(gap.get("translation_zh"), TRANSLATION_INPUT_CHARS),
            "page": gap.get("page"), "status": gap.get("status"),
            "email_use": gap.get("email_use"),
            "remaining_gap": gap.get("remaining_gap"),
             "completed_part": gap.get("completed_part") if gap.get("email_use") == "extension_context_only" else None,
             "evidence": gap.get("evidence"), "confidence": gap.get("confidence")}


def select_stage5_email(all_emails: list, requested_email_id: str) -> list:
    """Resolve ``--email-id`` into the hard single-email execution scope.

    Identity resolution happens before any path, evidence, cache, result or
    state validation, so an unrelated malformed pack entry can neither block
    nor be mistaken for the target: non-dict rows and rows without the
    requested id are skipped while searching. An id that appears more than
    once is an ambiguous pack and fails closed rather than picking one."""
    matches = [row for row in all_emails
               if isinstance(row, dict) and row.get("email_id") == requested_email_id]
    if not matches:
        fail("invalid_params", f"email_id not found: {requested_email_id}")
    if len(matches) > 1:
        fail("invalid_email_pack",
             f"email pack contains duplicate email_id: {requested_email_id}")
    return matches


def stage5_mode(args) -> str:
    mode = getattr(args, "mode", None) or "first"
    if mode not in ("first", "both", "followup"):
        fail("invalid_params", f"invalid stage-5 mode: {mode}")
    return mode


def stage5_pack_owner(pack, pack_path: Path) -> dict:
    """The single professor a Stage-5 pack claims, or a fail-closed stop.

    Issue #67's professor-local ``<professor_dir>/邮件输入.json`` is the only pack
    Stage 5 accepts: the legacy program-level pack is #67's migration input, not
    a second Stage-5 authority, so a pack that cannot name exactly one professor
    inside the program stops the run before any row is read.
    """
    if not isinstance(pack, dict):
        fail("invalid_email_pack", "email pack is not an object", email_pack=str(pack_path))
    if pack.get("schema") != STAGE4_LOCAL_SCHEMA or pack.get("kind") != EMAIL_PACK_KIND:
        fail("invalid_email_pack",
             f"email pack must be the professor-local schema {STAGE4_LOCAL_SCHEMA} "
             f"{EMAIL_PACK} written by stage4-finalize", email_pack=str(pack_path))
    professor = pack.get("professor")
    professor_dir = pack.get("professor_dir")
    if not isinstance(professor, str) or not professor.strip() or \
            not isinstance(professor_dir, str) or not professor_dir.strip():
        fail("invalid_email_pack", "email pack does not prove a single professor owner",
             email_pack=str(pack_path))
    return {"professor": professor, "professor_dir": Path(professor_dir)}


def stage5_local_pack(args, program_root: Path) -> tuple[Path, dict, list, list]:
    """Resolve the one professor-local pack that owns this Stage-5 run.

    Returns ``(pack_path, pack, pack_rows, selected_rows)``. ``--email-pack`` is
    mandatory and is the only fact source, so no program-level path is ever
    constructed here. Row-level validity keeps the Issue #59 ordering: id
    resolution stays the first boundary, so an unselected malformed row cannot
    become a precondition of the selected transaction, while the selected rows
    must still agree with the pack's own professor ownership.
    """
    if not getattr(args, "email_pack", None):
        fail("invalid_params",
             "stage5 requires --email-pack with the professor-local "
             f"{EMAIL_PACK} written by stage4-finalize")
    pack_path = Path(args.email_pack)
    pack, error = read_json_file(pack_path)
    if error:
        soft_exit("needs_refresh", "missing_email_pack", email_pack=str(pack_path),
                  message="缺该教授的 邮件输入.json：先跑阶段 4（professor-contact-selection）编译。")
    owner = stage5_pack_owner(pack, pack_path)
    require_professor_dir_under_program(owner["professor_dir"], program_root)
    all_emails = pack.get("emails")
    if not isinstance(all_emails, list):
        fail("invalid_email_pack", "email pack has no emails list", email_pack=str(pack_path))
    emails = (select_stage5_email(all_emails, args.email_id) if args.email_id
              else all_emails)
    if not args.email_id:
        all_ids = [email.get("email_id") for email in all_emails]
        if len(set(all_ids)) != len(all_ids) or any(not isinstance(email_id, str) for email_id in all_ids):
            fail("invalid_email_pack", "email pack contains duplicate or missing email_id")
    for email in emails:
        if not isinstance(email, dict):
            fail("invalid_email_pack", "email pack row is not an object",
                 email_pack=str(pack_path))
        professor_dir = Path(email.get("professor_dir") or program_root)
        # Escaped paths keep their own reason code and stay first: an outside
        # program root is an invalid_professor_dir contract, not a ownership one.
        require_professor_dir_under_program(professor_dir, program_root)
        if email.get("professor") != owner["professor"] or \
                professor_dir.resolve() != owner["professor_dir"].resolve():
            fail("invalid_email_pack",
                 f"{email.get('email_id')}: row names a professor other than the "
                 f"pack owner {owner['professor']}", email_pack=str(pack_path),
                 professor_dir=str(professor_dir))
    return pack_path, pack, all_emails, emails


def stage5_choices_rows(path: Path) -> list:
    """The raw caller rows: ``choices`` stays a plain object or object list.

    Non-dict rows are unattributable noise under the Issue #68 §3 attribution
    order — they name no professor, so they can neither be validated nor fail
    any professor — matching the targeted noise contract ``load_id_map``
    already kept for them.
    """
    data, error = read_json_file(path)
    if error:
        fail("invalid_result_json", f"choices unreadable: {path}: {error}")
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = [data]
    else:
        fail("invalid_result_json", "choices must be an object or a list of objects")
    return [row for row in rows if isinstance(row, dict)]


def stage5_choices_by_id(args, owner: dict, emails: list) -> dict:
    """Owner-local ``choices`` loader for one professor transaction.

    Plan r12 §3.3/§3.5: cross-professor attribution happened exactly once at
    the root partition entry (``stage5-partition-choices``), so this loader
    only ever consumes the current owner's one-professor bundle rows. An
    explicit ``professor_dir`` row naming another professor is a caller
    contract violation: the runner fails closed as this owner's input error
    and never re-routes the row to its professor. The professor's own
    explicit rows keep the frozen #59 / R68-2 / R68-3 behavior: a targeted
    run (``--email-id``) filters unselected, missing or unknown ids before
    any ownership or field judgment — they never block the target and never
    count as a legal explicit binding — while a full-professor batch treats
    an id outside the pack's execution range as ``needs_input``
    ``choice_owner_invalid``. Legacy rows without a directory keep the
    exact-one binding semantics as this professor's own business validation:
    a row whose id sits inside the current execution range binds and joins
    the exact-one duplicate check, anything else is noise. Duplicate,
    missing and field checks below belong to this professor alone.
    """
    choices_path = getattr(args, "choices", None)
    if not choices_path:
        return {}
    rows = stage5_choices_rows(Path(choices_path))
    owner_dir = str(owner["professor_dir"].resolve())
    targeted = bool(getattr(args, "email_id", None))
    expected = {email.get("email_id") for email in emails}
    attributed: dict = {}
    legacy_rows = []
    for row in rows:
        row_id = row.get("email_id")
        raw_dir = row.get("professor_dir")
        if "professor_dir" in row:
            if not isinstance(raw_dir, str) or not raw_dir.strip():
                # An invalid explicit directory is never a legacy binding.
                continue
            canonical = str(Path(raw_dir).resolve())
            if canonical != owner_dir:
                # Another professor's row reached this owner-local bundle:
                # fail closed on this owner's input, never re-route the row.
                fail("invalid_params",
                     f"owner-local choices name another professor: {raw_dir}",
                     professor_dir=str(canonical))
            if row_id not in expected:
                if targeted:
                    # R68-2: a targeted run filters the professor's unselected
                    # ids before any ownership or field judgment — an explicit
                    # Y row never blocks the target X, and it is not a legal
                    # explicit binding.
                    continue
                soft_exit("needs_input", "choice_owner_invalid",
                          message=f"{row_id}: 显式目录内的邮件编号不属于本教授当前执行范围。未写盘。",
                          email_id=row_id, professor_dir=canonical)
            attributed.setdefault(row_id, []).append(row)
            continue
        legacy_rows.append(row)
    # Legacy rows: the execution range of this pack is the only candidate
    # owner, so a row whose id sits inside it binds and joins this professor's
    # exact-one duplicate check; every other id is unrelated noise.
    for row in legacy_rows:
        row_id = row.get("email_id")
        if row_id in expected:
            attributed.setdefault(row_id, []).append(row)
    for email_id in sorted(expected):
        count = len(attributed.get(email_id, ()))
        if count != 1:
            fail("invalid_result_json",
                 f"choices email_id set does not match selected emails "
                 f"({email_id}: {count} attributable rows)")
    return {email_id: rows[0] for email_id, rows in attributed.items()}


def stage5_list_input_rows(program_root: Path) -> list:
    """Issue #68 §2: every professor-local pack discovered independently.

    Read-only enumeration of ``教授研究/**/邮件输入.json``. A container that
    cannot be read, cannot prove one professor, or does not sit inside the
    professor directory it names fails as its own error row; it never blocks
    another valid professor and never reads verify/state/render/overview files
    or the legacy program-level pack.
    """
    research = program_root / "教授研究"
    inputs = []
    for pack_path in (sorted(research.rglob(EMAIL_PACK)) if research.is_dir() else []):
        if pack_path.parent == research:
            # The legacy program-level pack is Issue #67's migration input and
            # names no professor, so it is not a Stage-5 input row.
            continue
        row = {"professor": None, "professor_dir": str(pack_path.parent),
               "email_pack": str(pack_path), "status": "error",
               "reason_code": None}
        pack, error = read_json_file(pack_path)
        if error or not isinstance(pack, dict):
            row["reason_code"] = "missing_email_pack"
            inputs.append(row)
            continue
        if pack.get("schema") != STAGE4_LOCAL_SCHEMA or pack.get("kind") != EMAIL_PACK_KIND:
            row["reason_code"] = "invalid_email_pack"
            inputs.append(row)
            continue
        professor = pack.get("professor")
        professor_dir = pack.get("professor_dir")
        if not isinstance(professor, str) or not professor.strip() or \
                not isinstance(professor_dir, str) or not professor_dir.strip():
            row["reason_code"] = "invalid_email_pack"
            inputs.append(row)
            continue
        row["professor"] = professor
        row["professor_dir"] = professor_dir
        contained = professor_dir_containment_error(
            Path(professor_dir), program_root) is None
        if contained:
            contained = Path(professor_dir).resolve() == pack_path.parent.resolve()
        if not contained:
            row["reason_code"] = "invalid_professor_dir"
        else:
            row["status"] = "ok"
        inputs.append(row)
    return inputs


def cmd_stage5_list_inputs(args) -> None:
    """Read-only Stage-5 input discovery for a standalone Stage-5 call.

    Returns one row per professor-local pack with ``professor``,
    ``professor_dir``, ``email_pack``, ``status`` and ``reason_code``. No
    managed state is consulted; a bad container only fails its own row.
    ``--professor`` keeps only the rows whose top-level name matches it
    exactly, and a name with no such row returns ``needs_input`` instead of
    guessing. Discovery only finds packs: it never writes a file and never
    produces data one owner would share with another (plan r12 §3.7).
    """
    inputs = stage5_list_input_rows(Path(args.program_root))
    wanted = getattr(args, "professor", None)
    if wanted:
        named = [row for row in inputs if row["professor"] == wanted]
        if not named:
            soft_exit("needs_input", "professor_not_found", professor=wanted)
        inputs = named
    emit({"status": "ok", "inputs": inputs})


def stage5_partition_pack_spec(program_root: Path, pack_path: str,
                               email_id: str | None) -> dict:
    """Resolve one ``--owner`` pack into a partition spec or its own failure.

    The partition consumes packs the caller already selected from Stage-4
    success results or read-only discovery rows. A pack that cannot prove one
    professor stays that owner's own input-resolution failure with the
    runner's verdict shape; it never blocks another owner (plan r12 §3.2).
    """
    path = Path(pack_path)
    spec = {"pack_path": pack_path, "email_id": email_id, "professor": None,
            "owner_dir": None, "ids": None, "failure": None}

    def owner_failure(status, reason_code, message):
        spec["failure"] = {"status": status, "reason_code": reason_code,
                           "email_pack": pack_path, "message": message}
        return spec

    pack, error = read_json_file(path)
    if error:
        return owner_failure(
            "needs_refresh", "missing_email_pack",
            "缺该教授的 邮件输入.json：先跑阶段 4（professor-contact-selection）编译。")
    if not isinstance(pack, dict) or \
            pack.get("schema") != STAGE4_LOCAL_SCHEMA or pack.get("kind") != EMAIL_PACK_KIND:
        return owner_failure(
            "error", "invalid_email_pack",
            f"email pack must be the professor-local schema {STAGE4_LOCAL_SCHEMA} "
            f"{EMAIL_PACK} written by stage4-finalize")
    professor = pack.get("professor")
    professor_dir = pack.get("professor_dir")
    if not isinstance(professor, str) or not professor.strip() or \
            not isinstance(professor_dir, str) or not professor_dir.strip():
        return owner_failure(
            "error", "invalid_email_pack",
            "email pack does not prove a single professor owner")
    allowed = (program_root / "教授研究").resolve()
    canonical = Path(professor_dir).resolve()
    try:
        canonical.relative_to(allowed)
    except ValueError:
        return owner_failure(
            "error", "invalid_professor_dir",
            "professor_dir must be inside program_root/教授研究")
    emails = pack.get("emails")
    if not isinstance(emails, list):
        return owner_failure("error", "invalid_email_pack",
                             "email pack has no emails list")
    ids = [email.get("email_id") for email in emails
           if isinstance(email, dict) and isinstance(email.get("email_id"), str)]
    spec["professor"] = professor
    spec["owner_dir"] = str(canonical)
    spec["ids"] = ids
    spec["range"] = {email_id} if email_id else set(ids)
    return spec


def cmd_stage5_partition_choices(args) -> None:
    """Root-side deterministic ``choices`` partition (plan r12 §3.3).

    One user request may carry A+B's raw ``choices``, but the raw
    multi-professor object is never delegated to any professor owner. This
    entry partitions it exactly once by the frozen identity ``(canonical
    professor_dir, email_id)`` and answers one self-contained per-owner
    bundle: each holds only that professor's ``professor_dir``, ``email_pack``
    path, targeted ``email_id`` if any, and its own ``choices`` row subset.
    Explicit ``professor_dir`` rows enter their named owner only; a targeted
    owner excludes its own unselected ids first; a full-professor batch id
    error stays that owner's ``needs_input`` ``choice_owner_invalid``. A
    legacy row without a directory computes its candidates from this run's
    selected packs alone: zero candidates is an unrelated row (dropped), one
    candidate binds that owner, and several candidates stay at root as the
    affected owners' ``needs_input`` ``choice_owner_ambiguous`` — the row is
    broadcast to no one, and one owner's partition failure never blocks
    another owner's legal bundle. Business validation (duplicate, missing,
    fields, recipient) is not copied here; each owner's deterministic Stage-5
    path keeps running it on its own bundle.
    """
    program_root = Path(args.program_root)
    raw_owners = getattr(args, "owner", None)
    if not raw_owners:
        fail("invalid_params",
             "stage5-partition-choices requires at least one "
             "--owner <email_pack> [email_id]")
    specs = []
    for owner in raw_owners:
        if len(owner) > 2:
            fail("invalid_params",
                 "--owner accepts at most <email_pack> <email_id>")
        specs.append(stage5_partition_pack_spec(
            program_root, owner[0], owner[1] if len(owner) > 1 else None))
    seen_dirs: dict = {}
    for spec in specs:
        if spec["owner_dir"] is None:
            continue
        if spec["owner_dir"] in seen_dirs:
            fail("invalid_params",
                 "--owner names the same professor_dir more than once",
                 professor_dir=spec["owner_dir"])
        seen_dirs[spec["owner_dir"]] = spec
    rows = stage5_choices_rows(Path(args.choices))
    by_dir = {spec["owner_dir"]: spec for spec in specs if spec["owner_dir"]}
    attributed: dict = {dir_: {} for dir_ in by_dir}
    explicit_satisfied: dict = {}
    invalid_ids: dict = {}
    ambiguous_ids: dict = {dir_: set() for dir_ in by_dir}
    legacy_rows = []
    ranges = {dir_: spec["range"] for dir_, spec in by_dir.items()}
    for row in rows:
        row_id = row.get("email_id")
        raw_dir = row.get("professor_dir")
        if "professor_dir" in row:
            if not isinstance(raw_dir, str) or not raw_dir.strip():
                # An invalid explicit directory is never a legacy binding.
                continue
            canonical = str(Path(raw_dir).resolve())
            spec = by_dir.get(canonical)
            if spec is None:
                # The row leaves with its professor; nobody in this run owns
                # it, so no bundle ever carries it.
                continue
            try:
                in_range = row_id in spec["range"]
            except TypeError:
                in_range = False
            if in_range:
                attributed[canonical].setdefault(row_id, []).append(row)
                explicit_satisfied.setdefault(row_id, set()).add(canonical)
            elif spec["email_id"]:
                # R68-2: a targeted owner's unselected ids stay noise.
                continue
            else:
                # R68-3: the professor's own batch error id fails only that
                # owner's partition, never another owner's bundle.
                invalid_ids.setdefault(canonical, row_id)
            continue
        legacy_rows.append(row)
    # Resolve legacy rows only after every legal explicit binding is known:
    # input order cannot change ownership or turn a claimed id ambiguous.
    for row in legacy_rows:
        row_id = row.get("email_id")
        try:
            candidates = sorted(dir_ for dir_, rng in ranges.items()
                                if row_id in rng)
        except TypeError:
            candidates = []
        if not candidates:
            continue  # unrelated row: dropped, changes no verdict
        if len(candidates) == 1:
            bound = candidates[0]
        else:
            # Only a multi-candidate row may exclude owners a legal explicit
            # row already satisfied; an undecided collision stays at root.
            satisfied = explicit_satisfied.get(row_id) or set()
            remaining = [dir_ for dir_ in candidates if dir_ not in satisfied]
            if not remaining:
                continue
            if len(remaining) > 1:
                for dir_ in remaining:
                    ambiguous_ids[dir_].add(row_id)
                continue
            bound = remaining[0]
        attributed[bound].setdefault(row_id, []).append(row)
    owners = []
    for spec in specs:
        email_id = spec["email_id"]
        base = {"professor": spec["professor"],
                "professor_dir": spec["owner_dir"],
                "email_pack": spec["pack_path"],
                "email_id": email_id}
        if spec["failure"] is not None:
            owners.append({**base, "partition": spec["failure"]})
            continue
        dir_ = spec["owner_dir"]
        if ambiguous_ids[dir_]:
            owners.append({**base, "partition": {
                "status": "needs_input", "reason_code": "choice_owner_ambiguous",
                "email_ids": sorted(ambiguous_ids[dir_]),
                "message": "无目录旧格式 choices 行在多个已选教授范围内命中同一 email_id："
                           "请为每行显式补充 professor_dir 后重跑。未写盘。"}})
            continue
        if dir_ in invalid_ids:
            owners.append({**base, "partition": {
                "status": "needs_input", "reason_code": "choice_owner_invalid",
                "email_id": invalid_ids[dir_],
                "message": "显式目录内的邮件编号不属于本教授当前执行范围。未写盘。"}})
            continue
        ordered: list = []
        for pack_email_id in spec["ids"]:
            if email_id and pack_email_id != email_id:
                continue
            ordered.extend(attributed[dir_].get(pack_email_id, []))
        owners.append({**base, "partition": {"status": "ok"},
                       "choices_rows": ordered})
    payload = {"status": "ok", "choices": str(Path(args.choices)),
               "owners": owners}
    out_path = getattr(args, "out", None)
    if out_path:
        # A transport representation for this request only: the caller hands
        # each owner its own bundle and cleans the file up with the request.
        Path(out_path).write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
            encoding="utf-8")
    emit(payload)


def cmd_stage5_plan(args) -> None:
    program_root = Path(args.program_root)
    mode = stage5_mode(args)
    pack_path, pack, all_emails, emails = stage5_local_pack(args, program_root)
    sources = load_header_sources(program_root)
    resolved_evidence = resolve_contact_evidence(
        program_root, list(dict.fromkeys(
            e.get("professor") for e in emails if e.get("professor"))))
    decisions = contact_evidence_decisions(emails, resolved_evidence)
    initial_read_only_plan = not getattr(args, "result", None) and \
        not getattr(args, "choices", None)
    fingerprint_state = (current_source_fingerprints(sources)
                         if initial_read_only_plan else None)
    verify_checks = {}
    for email in emails:
        professor_dir = Path(email.get("professor_dir") or program_root)
        key = email.get("professor")
        if key in verify_checks:
            continue
        check = verify_state(professor_dir, sources, decisions.get(key), fingerprint_state)
        decision = decisions.get(key)
        if check["ok"] and decision is not None and \
                decision.get("status") == "needs_refresh":
            # A frozen-snapshot mismatch makes this professor's pack entry
            # stale for the whole run regardless of cache usability: plan
            # must demand the Stage-4 refresh deterministically, never leave
            # it to the agent reading the decision object alone.
            check = {"ok": False,
                     "reason": decision.get("reason_code") or "contact_evidence_snapshot_stale",
                     "path": None, "data": None}
        verify_checks[key] = check
    needs_recheck = [p for p, v in verify_checks.items() if not v["ok"]]
    template_path = None
    profile_path = args.profile
    if getattr(args, "template", None):
        template_path = args.template
    else:
        for candidate in [program_root.parent / "套磁邮件" / "套磁模板.md",
                          program_root / "套磁邮件" / "套磁模板.md"]:
            if candidate.is_file():
                template_path = str(candidate)
                break
    if not template_path:
        fail("template_required", "stage5 requires --template with the user's email template")
    if not Path(template_path).is_file():
        fail("template_error", f"template not found: {template_path}")
    template_text = Path(template_path).read_text(encoding="utf-8")
    if not args.result:
        jobs = []
        for email in emails:
            jobs.append({
                "job_id": f"email:{email['email_id']}", "kind": "email",
                "result_file": f"email-{sha256_text(email['email_id'])[:12]}.json",
                "result_schema": {
                    "schema": 1, "kind": "email", "email_id": email["email_id"],
                    "interest_sentences_ja": ["①自定位", "②点名+桥接", "③宽泛例子", "④软收束"],
                    "future_aspiration_ja": "…",
                    "learning_candidates": ["候补1", "候补2"],
                    "source_map": [{"output": "①", "source_ids": ["profile.interest"]},
                                   {"output": "②", "source_ids": ["paper:<item_key>"]},
                                   {"output": "③", "source_ids": ["gap:<gap_id>"]},
                                   {"output": "④", "source_ids": ["template"]},
                                   {"output": "future", "source_ids": [f"idea:{email['idea']['id']}"]}]},
                "model_input": {
                    "idea": email.get("idea"),
                    "direction_ids": email.get("direction_ids") or [],
                    "directions": email.get("directions") or [],
                    "user_note": truncate(email.get("user_note"), 800),
                    "papers": email.get("papers"),
                    "gaps": [gap_job_block(g) for g in email.get("gaps", [])],
                    "red_lines": email.get("red_lines"),
                    "soft_materials": {"positioning": email.get("soft_materials", {}).get("positioning", [])},
                    "profile_text": load_profile_text(profile_path, 1200),
                    "user_supplement": email.get("user_supplement") or "",
                    "allowed_sources": email.get("allowed_sources"),
                    "rules": {
                        "interest": "4 句、只写软层、总长 ≤180 日文字；①自定位（角色+信念，禁恭维）②点名+桥接（真实标题、共同主题逐篇成立）③宽泛例子（仅可用 gaps 里 status∈{open,partial,unknown} 的精确 gap；done_by_self 禁锚；partial 只谈 remaining_gap；引用教授原话式，不找碴）④固定句「このような<领域名词>は、まだ数多く存在すると感じております。」",
                        "exclusions": "禁方法名/模型名/算法名（标题内除外）、指标数字、数据集名、组件名、公式、限定语链、年份叙事",
                        "future_aspiration": "宽泛方向表述+背景技能，禁具体技术栈，不用其他方向原句",
                        "learning": "2-3 个名词短语候选，贴近 profile 真实知识储备，交用户挑选",
                        "source_map": "每句必须给来源；③只能用 gap:<id>；④只能 template；所有 source_ids ⊆ allowed_sources"}}})
        payload = {
            "status": "ok", "email_pack": str(pack_path),
            "emails": [e.get("email_id") for e in emails],
            "verify": {p: ("ok" if v["ok"] else f"needs_recheck:{v['reason']}")
                       for p, v in verify_checks.items()},
            "needs_recheck_professors": needs_recheck,
            "contact_evidence": decisions,
            "template": template_path or "embedded",
            "output_mode": mode,
            "followup_template": (find_followup_template_path(
                program_root, getattr(args, "followup_template", None)) or "embedded"),
            "jobs": jobs,
        }
        if initial_read_only_plan:
            fingerprints = fingerprint_state["source_fingerprints"]
            hint = None if fingerprint_state["failed_field"] else {
                "source_fingerprints": fingerprints,
                "verified_at_format": VERIFY_TIMESTAMP_FORMAT,
            }
            payload["verify_write_hints"] = {
                professor: hint for professor in verify_checks
            }
            payload["verify_diagnostics"] = {
                professor: {
                    "reason": check.get("reason"),
                    "failed_field": check.get("failed_field"),
                    "diagnostic_kind": check.get("diagnostic_kind"),
                }
                for professor, check in verify_checks.items()
            }
        emit(payload)
        return
    result_path = Path(args.result)
    results, rerror = read_json_file(result_path)
    if rerror:
        fail("result_missing", f"{result_path}: {rerror}")
    by_id = load_id_map(result_path, {e.get("email_id") for e in emails}, "email result",
                        exact=not bool(args.email_id))
    # The model result contract is checked before anything else: it is the
    # caller's own file, and a broken result must not hide behind a cache gate.
    problems_by_id = {}
    for email in emails:
        email_id = email.get("email_id")
        raw = by_id.get(email_id)
        if raw is None:
            fail("result_missing", f"no raw result for {email_id}")
        problems = validate_email_raw(email, raw)
        hard = [x for x in problems if not x.startswith("WARNING")]
        if hard:
            fail("invalid_result_json", f"{email_id}: {'; '.join(hard)}")
        problems_by_id[email_id] = [x for x in problems if x.startswith("WARNING")]
    # Verification hard gate: until every selected professor's 送信前核验 is
    # usable, no caller row may be read at all — the only pre-gate recipient
    # decision surface is Step 2.5 writing `_contact_verify.json` items.email.
    # The two stop codes keep their distinct repairs: a bare contact-evidence
    # reason means Stage 4 must re-freeze the pack, `verify_*` means Step 2.5.
    for professor, check in verify_checks.items():
        if check["ok"]:
            continue
        decision = decisions.get(professor) or {}
        if decision.get("status") == "needs_refresh":
            soft_exit("needs_refresh", decision.get("reason_code") or
                      "contact_evidence_snapshot_stale", professor=professor,
                      message="联系方式证据快照与上游 live 指纹不一致或缺失：先重跑阶段 4 刷新 "
                              "邮件输入.json，再重跑阶段 5。核验通过前不读取 choices。未写盘。")
        soft_exit("needs_refresh", f"verify_{check['reason']}", professor=professor,
                  message=f"送信前核验缓存不可用（{check['reason']}）：先完成 Step 2.5 核验。"
                          "核验通过前不读取 choices。未写盘。")
    # Issue #68 plan r12: plan and finalize share one owner-local choices
    # loader — root already partitioned the raw choices once, so this runner
    # only validates the rows of its own one-professor bundle (exact-one
    # duplicate, missing and field checks stay here).
    choices_by_id = stage5_choices_by_id(
        args, stage5_pack_owner(pack, pack_path), emails)
    drafts = []
    for email in emails:
        raw = by_id.get(email.get("email_id"))
        warnings = problems_by_id[email.get("email_id")]
        choices = choices_by_id.get(email.get("email_id"))
        require_user_choices(email.get("email_id"), choices)
        if mode in ("both", "followup"):
            require_followup_choices(email.get("email_id"), choices)
        stage5_recipient_authority(
            email.get("email_id"), choices,
            (verify_checks.get(email.get("professor")) or {}).get("data"))
        if mode in ("first", "both"):
            draft, protected, banned = assemble_draft(
                email, raw, choices, sources, template_text)
            drafts.append({"output_id": stage5_output_id(email.get("email_id"), "initial"),
                           "email_id": email.get("email_id"), "kind": "initial",
                           "draft": draft, "protected": protected, "banned": banned,
                           "warnings": warnings, "result_file": str(result_path)})
        if mode in ("followup", "both"):
            followup_template_path = find_followup_template_path(
                program_root, getattr(args, "followup_template", None))
            if not followup_template_path:
                fail("followup_template_required", "follow-up mode requires --followup-template")
            if not Path(followup_template_path).is_file():
                fail("template_error", f"follow-up template not found: {followup_template_path}")
            followup_template = Path(followup_template_path).read_text(encoding="utf-8")
            followup_draft, followup_protected, followup_banned = assemble_followup_draft(
                email, choices, sources, followup_template,
                verify_checks.get(email.get("professor"), {}).get("data"))
            drafts.append({"output_id": stage5_output_id(email.get("email_id"), "followup"),
                           "email_id": email.get("email_id"), "kind": "followup",
                           "draft": followup_draft, "protected": followup_protected,
                           "banned": followup_banned, "warnings": warnings,
                           "result_file": str(result_path)})
    emit({"status": "ok", "drafts": drafts, "output_mode": mode})


def validate_email_raw(email: dict, raw: Any) -> list:
    problems = []
    if not isinstance(raw, dict) or raw.get("schema") != 1 or raw.get("kind") != "email":
        return ["schema/kind must be 1/email"]
    if raw.get("email_id") != email.get("email_id"):
        problems.append("email_id mismatch")
    sentences = raw.get("interest_sentences_ja")
    if not isinstance(sentences, list) or len(sentences) != 4 or \
            not all(isinstance(s, str) and s.strip() for s in sentences):
        problems.append("interest_sentences_ja must be 4 non-empty sentences")
        return problems
    total = sum(len(s) for s in sentences)
    if total > INTEREST_HARD_CAP:
        problems.append(f"interest total {total} exceeds hard cap {INTEREST_HARD_CAP}")
    elif total > INTEREST_SOFT_CAP:
        problems.append(f"WARNING interest total {total} exceeds soft cap {INTEREST_SOFT_CAP}")
    if not CLOSING_RE.match(sentences[3].strip()):
        problems.append("sentence ④ must be the fixed closing with a domain noun")
    if not (raw.get("future_aspiration_ja") or "").strip():
        problems.append("future_aspiration_ja required")
    learning = raw.get("learning_candidates")
    if not isinstance(learning, list) or not (2 <= len(learning) <= 3) or \
            not all(isinstance(item, str) and item.strip() for item in learning):
        problems.append("learning_candidates must have 2-3 entries")
    allowed = set(email.get("allowed_sources") or [])
    anchorable = set(email.get("anchorable_gaps") or [])
    gap_status = {g["gap_id"]: g for g in email.get("gaps", [])}
    source_map = raw.get("source_map")
    if not isinstance(source_map, list):
        problems.append("source_map must be a list")
        return problems
    covered = set()
    for entry in source_map:
        if not isinstance(entry, dict):
            problems.append("source_map entries must be objects")
            continue
        output = entry.get("output")
        if not isinstance(output, str):
            problems.append("source_map output must be a string")
            continue
        if output in covered:
            problems.append(f"source_map duplicate output {output}")
        covered.add(output)
        source_ids = entry.get("source_ids") or []
        if not isinstance(source_ids, list) or not all(isinstance(sid, str) for sid in source_ids):
            problems.append(f"source_map {output}: source_ids must be a string list")
            continue
        if not source_ids:
            problems.append(f"source_map {output}: empty source_ids")
            continue
        if output == "④":
            if set(source_ids) != {"template"}:
                problems.append("source_map ④ must be exactly ['template']")
            continue
        if output == "③":
            if not all(sid.startswith("gap:") for sid in source_ids):
                problems.append("source_map ③ may only use gap:<gap_id> sources")
            for sid in source_ids:
                gap_id = sid[4:]
                if gap_id not in anchorable:
                    if gap_id in gap_status and gap_status[gap_id].get("status") == "done_by_self":
                        problems.append(f"source_map ③ anchors done_by_self gap {gap_id[:12]}…")
                    else:
                        problems.append(f"source_map ③ references gap outside anchorable set: {gap_id[:12]}…")
            continue
        for sid in source_ids:
            if sid not in allowed:
                problems.append(f"source_map {output}: source {sid} not in allowed_sources")
    for required in ("①", "②", "③", "④", "future"):
        if required not in covered:
            problems.append(f"source_map missing output {required}")
    return problems


# Issue #43 freezes the caller-facing choices contract, but does not redefine
# pre-existing runner-internal compatibility fields. Keep renderer defaults
# here; public caller declarations are owned by the Stage-5 docs/projections.
DEFAULT_ALMA_MATER = "総合大学"

def require_user_choices(email_id: str, choices: Any) -> dict:
    if not isinstance(choices, dict):
        fail("missing_user_choice", f"{email_id}: choices object required")
    if not isinstance(choices.get("first_choice"), bool):
        fail("missing_user_choice", f"{email_id}: first_choice must be boolean")
    if not isinstance(choices.get("signature_name"), str) or not choices["signature_name"].strip():
        fail("missing_user_choice", f"{email_id}: signature_name is required")
    if not isinstance(choices.get("learning"), str) or not choices["learning"].strip():
        fail("missing_user_choice", f"{email_id}: learning is required")
    return choices


def stage5_recipient_authority(email_id: str, choices: dict, verify: dict | None) -> str:
    """Return the single recipient address an email may render.

    `_contact_verify.json` is the send-time authority; `choices.email_address`
    is the caller's explicit recipient *decision*, which Step 2.5 records into
    that cache. It may confirm the authority and may never replace it, so an
    address that disagrees with — or arrives before — the verified value fails
    closed instead of silently steering a follow-up to a different mailbox.
    """
    verified = str((((verify or {}).get("items") or {}).get("email") or {})
                   .get("value") or "").strip()
    stated = str((choices or {}).get("email_address") or "").strip()
    if not stated:
        return verified
    if not verified:
        fail("recipient_conflict",
             f"{email_id}: choices.email_address 已给出，但 _contact_verify.json 还没有已核验的"
             "收件邮箱。先在 Step 2.5 把用户的明确答复写入 items.email（source user_provided，"
             "verdict confirmed）再重跑；choices 不得代替送信前核验。")
    if stated.casefold() != verified.casefold():
        fail("recipient_conflict",
             f"{email_id}: choices.email_address「{stated}」与送信前核验的权威收件邮箱"
             f"「{verified}」不一致。按 Step 2.5 复核结论修正 choices 或重写缓存，"
             "不存在第二份收件人权威。")
    return verified


def require_followup_choices(email_id: str, choices: dict) -> None:
    sent_date = choices.get("initial_sent_date")
    if not isinstance(sent_date, str) or not sent_date.strip() or "{{" in sent_date:
        fail("missing_user_choice", f"{email_id}: initial_sent_date is required for follow-up email")


def find_followup_template_path(program_root: Path, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    for candidate in [program_root.parent / "套磁邮件" / "套磁跟进模板.md",
                      program_root / "套磁邮件" / "套磁跟进模板.md"]:
        if candidate.is_file():
            return str(candidate)
    return None


def load_id_map(path: Path, expected_ids: set, label: str, exact: bool = True) -> dict:
    data, error = read_json_file(path)
    if error:
        fail("invalid_result_json", f"{label} unreadable: {path}: {error}")
    rows = data if isinstance(data, list) else [data]
    if not exact:
        # Scoped/targeted mode: unrelated rows are noise, however malformed,
        # duplicated or unknown. Only the selected ids' own occurrences are
        # validated below, and each of them must appear exactly once.
        rows = [row for row in rows
                if isinstance(row, dict) and row.get("email_id") in expected_ids]
        if len(rows) != len(expected_ids):
            fail("invalid_result_json", f"{label} email_id set does not match selected emails")
    if not all(isinstance(row, dict) for row in rows):
        fail("invalid_result_json", f"{label} must contain objects")
    ids = [row.get("email_id") for row in rows]
    if any(not isinstance(email_id, str) or not email_id for email_id in ids):
        fail("invalid_result_json", f"{label} contains missing email_id")
    if len(set(ids)) != len(ids) or (set(ids) != expected_ids if exact else not expected_ids.issubset(set(ids))):
        fail("invalid_result_json", f"{label} email_id set does not match selected emails")
    return {row["email_id"]: row for row in rows}


def humanized_paths(args, emails: list[dict], exact: bool = True) -> dict[str, Path]:
    mode = stage5_mode(args)
    expected = set()
    if mode in ("first", "both"):
        expected.update(stage5_output_id(email.get("email_id"), "initial") for email in emails)
    if mode in ("followup", "both"):
        expected.update(stage5_output_id(email.get("email_id"), "followup") for email in emails)
    map_path = getattr(args, "humanized_map", None)
    if map_path:
        data, error = read_json_file(Path(map_path))
        if error or not isinstance(data, dict):
            fail("invalid_humanized_map", f"humanized map unreadable or not an object: {map_path}")
        if (set(data) != expected if exact else not expected.issubset(set(data))):
            fail("invalid_humanized_map", "humanized map keys do not match selected email IDs")
        paths = {}
        for email_id, value in data.items():
            if email_id not in expected:
                continue
            if not isinstance(value, str) or not Path(value).is_absolute():
                fail("invalid_humanized_map", f"humanized path for {email_id} must be absolute")
            paths[email_id] = Path(value)
    elif len(expected) == 1 and getattr(args, "humanized", None):
        paths = {next(iter(expected)): Path(args.humanized)}
    elif len(emails) > 1:
        fail("humanized_map_required", "multiple emails require --humanized-map email_id->absolute path")
    else:
        fail("result_missing", "humanized body file required (--humanized)")
    if len(set(paths.values())) != len(paths):
        fail("invalid_humanized_map", "multiple emails must use distinct humanized body paths")
    for email_id, path in paths.items():
        if not path.is_file():
            fail("result_missing", f"humanized body missing for {email_id}: {path}")
    return paths


def email_template_body(template_text: str) -> str:
    """Select the email body without copying Markdown instructions into mail.

    Plain templates are unchanged. Markdown templates may delimit the body
    with a body heading or a single text fence; trailing instruction sections
    are document metadata. Never guess between multiple body sections/blocks.
    """
    fences = []
    headings = []
    opened = None
    offset = 0
    for line in template_text.splitlines(keepends=True):
        marker = re.fullmatch(r" {0,3}(`{3,}|~{3,})([^\r\n]*)\r?\n?", line)
        if opened:
            start, content_start, delimiter = opened
            if (marker and marker[1][0] == delimiter[0]
                    and len(marker[1]) >= len(delimiter) and not marker[2].strip()):
                fences.append((start, offset + len(line), content_start, offset))
                opened = None
        elif marker:
            opened = (offset, offset + len(line), marker[1])
        else:
            heading = re.fullmatch(r"(#{1,6})[ \t]+([^\r\n]+)\r?\n?", line)
            if heading:
                headings.append((offset, offset + len(line), len(heading[1]),
                                 heading[2].strip().rstrip("# ：:")))
        offset += len(line)
    if opened:
        fail("template_error", "unclosed email template code fence")

    body_names = {"正文", "邮件正文", "本文", "メール本文"}
    note_names = {"说明", "模板说明", "使用说明", "占位符说明", "注意事项"}
    sections = [row for row in headings if row[3] in body_names]
    if len(sections) > 1:
        fail("template_error", "multiple email body sections; keep one body section")
    start, end = 0, len(template_text)
    if sections:
        _, start, level, _ = sections[0]
        end = next((row[0] for row in headings if row[0] >= start and row[2] <= level), end)
    else:
        end = next((row[0] for row in headings if row[3] in note_names), end)
    blocks = [row for row in fences if start <= row[0] and row[1] <= end]
    if len(blocks) > 1:
        fail("template_error", "multiple email body code blocks; use a body heading to select one")
    if blocks:
        return template_text[blocks[0][2]:blocks[0][3]]
    body = template_text[start:end]
    return body.strip("\r\n") + "\n" if sections or end < len(template_text) else body


def assemble_draft(email: dict, raw: dict, choices: dict,
                   sources: dict, template_text: str) -> tuple[str, list, list]:
    values = header_values(sources, email)
    values["出身校"] = choices.get("alma_mater") or DEFAULT_ALMA_MATER
    values["氏名"] = choices.get("signature_name") or ""
    values["志望"] = ("先生の研究室を第一志望として出願させていただきたく存じます"
                      if choices.get("first_choice") else
                      "先生の研究室を志望として出願させていただきたく存じます")
    values["学習中"] = choices.get("learning") or ""
    values["兴趣段"] = "\n".join(raw.get("interest_sentences_ja") or [])
    values["未来志向"] = raw.get("future_aspiration_ja") or ""
    subject = choices.get("subject") or subject_line(values)
    values["subject"] = subject
    body = email_template_body(template_text)
    for key, value in values.items():
        body = body.replace("{{" + key + "}}", value or "")
    leftover = re.findall(r"\{\{[^}]*\}\}", body)
    if leftover:
        fail("template_error", f"unresolved placeholders after fill: {leftover}")
    draft = f"Subject: {subject}\n\n{body}"
    protected = [subject, values["氏名"], values["志望"], values["学習中"], values["未来志向"]]
    protected += [p["title"] for p in email.get("papers", []) if p.get("title")]
    protected += [v for v in (values["大学"], values["研究科"], values["専攻"],
                              values["学位"], values["入学年度"] + "年" + values["入学月"]) if v]
    banned = []
    for red in email.get("red_lines", []):
        banned.extend(red.get("banned_phrases") or [])
    return draft, [p for p in protected if p], banned


def assemble_followup_draft(email: dict, choices: dict, sources: dict,
                            template_text: str, verify: dict | None = None) -> tuple[str, list, list]:
    values = header_values(sources, email)
    values["出身校"] = choices.get("alma_mater") or DEFAULT_ALMA_MATER
    values["氏名"] = choices.get("signature_name") or ""
    values["初回送信日"] = choices.get("initial_sent_date") or ""
    # Issue #8 §8.3: a multi-direction (cross) email must not guess ONE
    # direction name — prefer the selected idea title as the follow-up topic.
    if len(email.get("direction_ids") or []) > 1:
        values["研究主题"] = ((email.get("idea") or {}).get("title")
                               or email.get("name_ja") or "関連分野")
    else:
        values["研究主题"] = (email.get("name_ja") or
                               (email.get("idea") or {}).get("title") or "関連分野")
    values["メールアドレス"] = stage5_recipient_authority(
        email.get("email_id"), choices, verify)
    subject = choices.get("followup_subject") or f"Re: {choices.get('subject') or subject_line(values)}"
    values["subject"] = subject
    body = email_template_body(template_text)
    for key, value in values.items():
        body = body.replace("{{" + key + "}}", value or "")
    leftover = re.findall(r"\{\{[^}]*\}\}", body)
    if leftover:
        fail("template_error", f"unresolved follow-up placeholders after fill: {leftover}")
    draft = f"Subject: {subject}\n\n{body}"
    protected = [subject, values["氏名"], values["初回送信日"], values["研究主题"],
                 values["大学"], values["研究科"], values["入学年度"] + "年" + values["入学月"]]
    if values["メールアドレス"]:
        protected.append(values["メールアドレス"])
    banned = []
    for red in email.get("red_lines", []):
        banned.extend(red.get("banned_phrases") or [])
    return draft, [p for p in protected if p], banned


def body_salutation_line(body: str, values: dict) -> str | None:
    """The template's fixed salutation line, matched verbatim from the
    assembled body. The 「抬头逐字」 checklist row must show exactly the text
    the recipient sees — the user template may format the header differently
    from the synthesized 大学／研究科／先生名： form (e.g. without the trailing
    full-width colon), and a mismatching row reads as a self-contradicting
    checklist. Returns None when the professor name does not appear, leaving
    the caller's fallback in place."""
    name = values.get("先生名") or ""
    if not name:
        return None
    for line in body.splitlines():
        text = line.strip()
        if text and name in text:
            return text
    return None


def render_checklist_table(verify: dict, header_text: str | None = None) -> list:
    items = verify.get("items") or {}
    def cell(key, default="—"):
        entry = items.get(key) or {}
        verdict = entry.get("verdict") or "unverified"
        value = entry.get("value")
        return value if value not in (None, "") else default, verdict
    email_value, email_verdict = cell("email", "（空）")
    roster_value, roster_verdict = cell("roster")
    season_value, season_verdict = cell("season")
    header_value, header_verdict = cell("header")
    if header_text:
        header_value = header_text
    subject_value, subject_verdict = cell("subject_batch")
    schedule_value, schedule_verdict = cell("schedule")
    consent_value, consent_verdict = cell("consent")
    warnings = items.get("warnings") or []
    warning_text = "；".join(str(w) for w in warnings) if warnings else "（无）"
    return [
        "| 项目 | 内容 | 结论 | 来源 |", "|---|---|---|---|",
        f"| 收件邮箱 | {email_value} | {email_verdict} | {cell_source(items, 'email')} |",
        f"| 教授在册 | {roster_value} | {roster_verdict} | {cell_source(items, 'roster')} |",
        f"| 批次存在性 | {season_value} | {season_verdict} | {cell_source(items, 'season')} |",
        f"| 抬头逐字 | {header_value} | {header_verdict} | {cell_source(items, 'header')} |",
        f"| 件名批次词 | {subject_value} | {subject_verdict} | {cell_source(items, 'subject_batch')} |",
        f"| 日程快照 | {schedule_value} | {schedule_verdict} | {cell_source(items, 'schedule')} |",
        f"| 内诺制度 | {consent_value} | {consent_verdict} | {cell_source(items, 'consent')} |",
        f"| 特记 ⚠ | {warning_text} | — | info.json notes 等 |",
    ]


def cell_source(items: dict, key: str) -> str:
    entry = items.get(key) or {}
    sources = entry.get("sources") or []
    if not sources:
        return "—"
    first = sources[0]
    return str(first.get("url") or first.get("note") or "—")


def render_source_table(email: dict, raw: dict) -> list:
    label = {"user_note": "用户 note（原文）", "template": "[模板] 固定文本",
             "profile.interest": "[生成] 用户意图层（profile）"}
    paper_titles = {p["item_key"]: p.get("title") for p in email.get("papers", [])}
    gap_index = {g["gap_id"]: g for g in email.get("gaps", [])}
    rows = ["| 句 | 来源 |", "|---|---|"]
    output_names = {"①": "兴趣段①自定位", "②": "兴趣段②点名+桥接",
                    "③": "兴趣段③宽泛例子", "④": "兴趣段④软收束（模板固定）",
                    "future": "未来志向句"}
    for entry in raw.get("source_map", []):
        output = entry.get("output")
        names = []
        for sid in entry.get("source_ids", []):
            if sid in label:
                names.append(label[sid])
            elif sid.startswith("paper:"):
                names.append(f"[生成] 论文《{paper_titles.get(sid[6:], sid[6:])}》")
            elif sid.startswith("gap:"):
                gap = gap_index.get(sid[4:]) or {}
                names.append(f"[生成] future work（{gap.get('status')}，p.{gap.get('page')}，{gap.get('paper_title')}）")
            elif sid.startswith("later:"):
                names.append(f"[生成] 后续论文《{paper_titles.get(sid[6:], sid[6:])}》")
            elif sid.startswith("idea:"):
                names.append("[生成] 选中想法（idea_zh）")
            else:
                names.append(sid)
        rows.append(f"| {output_names.get(output, output)} | {'；'.join(names)} |")
    rows.append("| 資历段（現在は……取り組んでおります） | [生成候选+用户挑选] |")
    rows.append("| 抬头/寒暄/自我介绍/请求/收尾 | [模板] 固定文本 |")
    return rows


def render_followup_source_table(email: dict) -> list:
    if len(email.get("direction_ids") or []) > 1:
        direction = (email.get("idea") or {}).get("title") or "跨方向想法"
    else:
        direction = email.get("name_zh") or email.get("name_ja") or "相关方向"
    return [
        "| 项目 | 来源 |", "|---|---|",
        "| 首封邮件中的学校、研究科、入学信息 | [邮件包] 同一 email 记录 |",
        f"| 首封邮件中的研究方向 | [邮件包] {direction} |",
        "| 初次发送日期、署名、附件说明 | [用户选择] 首封邮件发送记录 |",
        "| 其余正文 | [模板] 跟进邮件固定文本 |",
    ]


def render_fact_check_card(email: dict, pack_path: Path, professor_dir: Path) -> list:
    lines = ["## 事实核对卡（发送前人工确认）", ""]
    key_gaps = [g for g in email.get("gaps", [])
                if g.get("email_use") in ("anchor", "remaining_only", "anchor_with_caveat", "extension_context_only")]
    if not key_gaps:
        lines.append("（本封邮件未使用任何 future-work 事实锚点。）")
        lines.append("")
        return lines
    pack_rel = rel_path(pack_path, professor_dir)
    for gap in key_gaps:
        status = gap.get("status")
        lines.append(f"<details><summary>《{gap.get('paper_title')}》 future work（{status}）</summary>")
        lines.append("")
        lines.append(f"- 论文 Zotero 链接：[zotero](zotero://select/library/items/{gap.get('zotero_key')})")
        lines.append(f"- 作者原话：「{gap.get('quote')}」")
        lines.append(f"- 中译：{gap.get('translation_zh')}")
        lines.append(f"- 页码：p.{gap.get('page')}（{gap.get('source')}）")
        lines.append(f"- 状态：{status}（置信度 {gap.get('confidence')}）")
        lines.append(f"- 后续论文依据：{gap.get('evidence') or '—'}")
        if status == "partial":
            lines.append(f"- 已做部分：{gap.get('completed_part') or '—'}")
            lines.append(f"- 剩余缺口：{gap.get('remaining_gap') or '—'}")
        if status == "unknown":
            lines.append("- ⚠ unknown：未查证是否已被教授后续论文实现，发送前请人工复核。")
        if status == "done_by_self":
            lines.append("- ⚠ 已被教授本人后续论文实现；本邮件只能以【我的延伸】口径提及，不得当开放 future work。")
        lines.append(f"- 邮件包：[{EMAIL_PACK}]({pack_rel})")
        lines.append(f"- 生成时间：{now_utc()}")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    return lines


def cmd_stage5_finalize(args) -> None:
    audit_suffix = STAGE5_AUDIT_PROVENANCE[args.audit_provenance]
    program_root = Path(args.program_root)
    mode = stage5_mode(args)
    pack_path, pack, all_emails, emails = stage5_local_pack(args, program_root)
    sources = load_header_sources(program_root)
    resolved_evidence = resolve_contact_evidence(
        program_root, list(dict.fromkeys(
            e.get("professor") for e in emails if e.get("professor"))))
    decisions = contact_evidence_decisions(emails, resolved_evidence)
    # Verification hard gate, mirroring cmd_stage5_plan: until every selected
    # professor's 送信前核验 is usable, no caller row — choices, result rows,
    # humanized bodies — may be read at all. The per-email loop below consumes
    # these saved checks so plan and finalize share one verify semantics.
    verify_checks = {}
    for email in emails:
        professor_dir = Path(email.get("professor_dir") or program_root)
        key = email.get("professor")
        if key in verify_checks:
            continue
        check = verify_state(professor_dir, sources, decisions.get(key))
        decision = decisions.get(key)
        if check["ok"] and decision is not None and \
                decision.get("status") == "needs_refresh":
            # A frozen-snapshot mismatch makes this professor's pack entry
            # stale for the whole run regardless of cache usability: the
            # deterministic repair is a Stage-4 refresh, not a web lookup.
            check = {"ok": False,
                     "reason": decision.get("reason_code") or "contact_evidence_snapshot_stale",
                     "path": None, "data": None}
        verify_checks[key] = check
    for professor, check in verify_checks.items():
        decision = decisions.get(professor)
        if not check["ok"]:
            if decision is not None and decision.get("status") == "needs_refresh":
                soft_exit("needs_refresh", decision.get("reason_code") or
                          "contact_evidence_snapshot_stale", professor=professor,
                          message="联系方式证据快照与上游 live 指纹不一致或缺失：先重跑阶段 4 刷新 "
                                  "邮件输入.json，再重跑阶段 5。未写盘。")
            soft_exit("needs_refresh", f"verify_{check['reason']}",
                      professor=professor,
                      message=f"送信前核验缓存不可用（{check['reason']}）：先完成 Step 2.5 核验。未写盘。")
        if decision is not None and decision.get("status") not in ("escalate", "needs_refresh"):
            # Recipient-evidence consistency backstop: an accepted decision
            # must still match the cache the checklist will print, and the
            # conflict is resolved before any choices row is read.
            cache_email_value = str((((check["data"] or {}).get("items") or {}).get("email") or {})
                                    .get("value") or "").strip()
            recipient = str(decision.get("recipient_email") or "").strip()
            if not cache_email_value or cache_email_value.casefold() != recipient.casefold():
                fail("contact_evidence_mismatch",
                     f"{professor}: 本地联系方式证据判定 {decision['status']}，收件邮箱应为 "
                     f"{recipient}；核对表邮箱为「{cache_email_value or '空'}」。"
                     "请按证据填写 _contact_verify.json，或重建 _联系方式证据.json 后重跑阶段 4。")
    result_path = Path(args.result)
    raw_by_id = load_id_map(result_path, {e.get("email_id") for e in emails}, "email result",
                            exact=not bool(args.email_id))
    # Same owner-local bundle loader as stage5-plan (Issue #68 plan r12).
    choices_by_id = stage5_choices_by_id(
        args, stage5_pack_owner(pack, pack_path), emails)
    humanized_by_id = humanized_paths(args, emails, exact=not bool(args.email_id))
    decision = None
    if getattr(args, "decision_file", None):
        decision_data, decision_error = read_json_file(Path(args.decision_file))
        if decision_error is None and isinstance(decision_data, dict):
            decision = decision_data.get("decision")
    template_path = getattr(args, "template", None)
    if not template_path:
        for candidate in [program_root.parent / "套磁邮件" / "套磁模板.md",
                          program_root / "套磁邮件" / "套磁模板.md"]:
            if candidate.is_file():
                template_path = str(candidate)
                break
    if not template_path:
        fail("template_required", "stage5 requires --template with the user's email template")
    if not Path(template_path).is_file():
        fail("template_error", f"template not found: {template_path}")
    template_text = Path(template_path).read_text(encoding="utf-8")
    followup_template_path = find_followup_template_path(
        program_root, getattr(args, "followup_template", None))
    if mode in ("both", "followup") and not followup_template_path:
        fail("followup_template_required", "follow-up mode requires --followup-template")
    if followup_template_path and not Path(followup_template_path).is_file():
        fail("template_error", f"follow-up template not found: {followup_template_path}")
    followup_template = (Path(followup_template_path).read_text(encoding="utf-8")
                         if followup_template_path else None)
    state_updates = {}
    prepared = []

    # Validate every email and prepare every file before committing any output.
    for email in emails:
        email_id = email.get("email_id")
        raw = raw_by_id.get(email_id)
        problems = validate_email_raw(email, raw)
        hard = [p for p in problems if not p.startswith("WARNING")]
        if hard:
            fail("invalid_result_json", f"{email_id}: {'; '.join(hard)}")
        choices = choices_by_id.get(email_id)
        professor_dir = Path(email.get("professor_dir") or program_root)
        # The whole-batch verification gate above already stopped on any
        # unusable professor before choices were read; consume its saved
        # result instead of re-deriving a second verify semantics.
        verify = verify_checks[email.get("professor")]["data"]
        warnings = (verify.get("items") or {}).get("warnings") or []
        decision = decisions.get(email.get("professor"))
        cache_email_value = str(((verify.get("items") or {}).get("email") or {})
                                .get("value") or "").strip()
        # Past the verification gate: only now may this row be validated, and
        # its explicit address only ever confirm the verified authority.
        require_user_choices(email_id, choices)
        if mode in ("both", "followup"):
            require_followup_choices(email_id, choices)
        stage5_recipient_authority(email_id, choices, verify)
        roster_verdict = ((verify.get("items") or {}).get("roster") or {}).get("verdict")
        email_verdict = ((verify.get("items") or {}).get("email") or {}).get("verdict")
        banner_needed = bool(warnings) or roster_verdict == "not_found" or email_verdict == "unverified"
        values = header_values(sources, email)
        # Fallback only: the 「抬头逐字」 row must show the assembled body's own
        # salutation verbatim (the user template's fixed text may format the
        # header differently, e.g. without a trailing 「：」), so the per-variant
        # header is derived from the draft body below.
        checklist_header = (f"{values['大学']}／{values['研究科']}／"
                            f"{values['先生名']}先生：")
        variants = []
        if mode in ("first", "both"):
            draft, protected, banned = assemble_draft(email, raw, choices, sources, template_text)
            variants.append(("initial", draft, protected, banned, "套磁邮件",
                             Path(template_path).name if template_path else "内嵌",
                             render_source_table(email, raw)))
        if mode in ("followup", "both"):
            draft, protected, banned = assemble_followup_draft(
                email, choices, sources, followup_template, verify)
            variants.append(("followup", draft, protected, banned, "套磁跟进邮件",
                             Path(followup_template_path).name if followup_template_path else "内嵌",
                             render_followup_source_table(email)))

        input_fp = email.get("source_hash") or sha256_obj(email)
        if str(professor_dir) not in state_updates:
            email_state, serr = read_json_file(professor_dir / EMAIL_STATE)
            state_updates[str(professor_dir)] = (
                json.loads(json.dumps(email_state, ensure_ascii=False))
                if serr is None and isinstance(email_state, dict)
                else {"schema": SCHEMA, "managed_by": MANAGED_BY, "emails": {}})
        email_state = state_updates[str(professor_dir)]
        root_entry = email_state.setdefault("emails", {}).setdefault(email_id, {})
        if decision:
            root_entry["contact_evidence"] = {
                "status": decision["status"], "reason_code": decision["reason_code"],
                "chosen_email": cache_email_value or None,
                "evidence_email": decision["recipient_email"],
                "web_lookup_required": decision["web_lookup_required"],
                "source": decision["source"], "snapshot_stale": decision["snapshot_stale"],
                "provenance": decision["provenance"], "recorded_at": now_utc()}
        for kind, draft, protected, banned, heading, template_name, source_rows in variants:
            output_id = stage5_output_id(email_id, kind)
            humanized = humanized_by_id[output_id].read_text(encoding="utf-8")
            missing = [p for p in protected if p and p not in humanized]
            if missing:
                fail("humanizer_violation",
                     f"{output_id}: humanized text lost protected strings: {missing}")
            violated = [b for b in banned if b and b in humanized]
            if violated:
                fail("humanizer_violation", f"{output_id}: banned phrases appeared: {violated}")
            if "{{" in humanized:
                fail("humanizer_violation", f"{output_id}: residual {{}} placeholders")
            subject_match = re.match(r"Subject: (.*)", humanized)
            subject = choices.get("followup_subject") if kind == "followup" else None
            subject = subject or (subject_match.group(1).strip() if subject_match else
                                  (subject_line(values) if kind == "initial" else
                                   f"Re: {subject_line(values)}"))
            body_text = re.sub(r"^Subject: .*\n+", "", humanized, count=1)
            lines = [
                f"# {heading} — {email.get('professor')}（{email.get('name_ja')}）",
                "",
                f"> {now_utc()} ｜ 类型：{'首封' if kind == 'initial' else '无回复跟进'} ｜ profile：{'有' if pack.get('profile_fingerprint') else '无'} ｜ 模板：{template_name} ｜ 方向：{email.get('name_zh') or email.get('name_ja')}{audit_suffix}",
                "",
            ]
            if kind == "followup":
                lines.append(f"> 跟进依据：首封邮件 email_id `{email_id}`；初次发送日：{choices.get('initial_sent_date')}。建议在首封邮件发送数日后使用。")
                lines.append("")
            if banner_needed:
                lines.append("> ⚠️ **送信前注意**：" + "；".join(
                    ([f"邮箱 {email_verdict}"] if email_verdict == "unverified" else []) +
                    ([f"教员在册 {roster_verdict}"] if roster_verdict == "not_found" else []) +
                    [str(w) for w in warnings]) + "。请人工确认后再发。")
                lines.append("")
            lines.append(f"## 送信前核对（发信前最后过目；数据源 _contact_verify.json @ {verify.get('verified_at')}）")
            lines.append("")
            lines.extend(render_checklist_table(
                verify, body_salutation_line(body_text, values) or checklist_header))
            lines.append("")
            lines.append("## 邮件正文")
            lines.append("")
            lines.append(f"Subject: {subject}")
            lines.append("")
            lines.append(body_text.strip())
            lines.append("")
            lines.append("## 来源标注（仅 md 内审用，不进 txt）")
            lines.append("")
            lines.extend(source_rows)
            lines.append("")
            red_lines = email.get("red_lines") or []
            if red_lines:
                lines.append("## 生成时消费的红线（已遵守）")
                lines.append("")
                for red in red_lines:
                    lines.append(f"- 【{red.get('scope')}】{red.get('text')}")
                lines.append("")
            lines.extend(render_fact_check_card(email, pack_path, professor_dir))
            md_body = "\n".join(lines).rstrip() + "\n"
            txt_body = f"Subject: {subject}\n\n{body_text.strip()}\n"
            state_fingerprint = sha256_obj({"output_id": output_id, "input": input_fp})
            md_path, txt_path = stage5_output_paths(
                email,
                stage5_output_peers(
                    email, all_emails, professor_dir, targeted=bool(args.email_id)),
                professor_dir, kind)
            previous = root_entry if kind == "initial" else root_entry.get("followup", {})
            old_render = previous.get("render") or {}
            existing_md_sha = None
            if md_path.is_file():
                _, existing_body = split_frontmatter(md_path.read_text(encoding="utf-8"))
                existing_md_sha = sha256_text(existing_body)
            md_sha = sha256_text(md_body)
            if (existing_md_sha is not None and old_render.get("md", {}).get("sha256") and
                    existing_md_sha not in (md_sha, old_render["md"]["sha256"]) and
                    decision != "overwrite"):
                soft_exit("needs_decision", "manual_markdown_changed", target=str(md_path))
            existing_txt_sha = sha256_bytes(txt_path.read_bytes()) if txt_path.is_file() else None
            txt_sha = sha256_text(txt_body)
            if (existing_txt_sha is not None and old_render.get("txt", {}).get("sha256") and
                    existing_txt_sha not in (txt_sha, old_render["txt"]["sha256"]) and
                    decision != "overwrite"):
                soft_exit("needs_decision", "manual_markdown_changed", target=str(txt_path))
            prepared.append({"email": email, "email_id": email_id, "output_id": output_id,
                             "kind": kind, "professor_dir": professor_dir, "raw": raw,
                             "choices": choices, "md": md_path, "txt": txt_path,
                             "md_body": md_body, "txt_body": txt_body, "md_sha": md_sha,
                             "txt_sha": txt_sha, "state_fingerprint": state_fingerprint,
                             "input_fp": input_fp, "warnings": warnings,
                             "banner": banner_needed})
            update = {"generated_at": now_utc(), "input_fingerprint": input_fp,
                      "model_result": raw, "choices": choices,
                      "files": {"md": str(md_path), "txt": str(txt_path)},
                      "render": {"md": {"sha256": md_sha}, "txt": {"sha256": txt_sha}},
                      "validation": {"result": "pending", "rounds": 0}}
            if kind == "initial":
                root_entry.update(update)
            else:
                root_entry.setdefault("followup", {}).update(update)

    # Issue #68: this professor's transaction commits on its own validation. The
    # program aggregate is a derived projection that stage5-rebuild-overview
    # owns, so a stale, conflicting or missing overview is never a commit gate
    # here and no local run writes it.
    for item in prepared:
        atomic_write(item["md"], render_frontmatter(
            sha256_obj({"email_id": item["email_id"], "input": item["input_fp"]}), item["md_sha"]) + item["md_body"])
        atomic_write(item["txt"], item["txt_body"])
    for professor_dir, email_state in state_updates.items():
        atomic_json(Path(professor_dir) / EMAIL_STATE, email_state)
    overview_path = program_root / "教授研究" / EMAIL_OVERVIEW
    emit({"status": "ok", "emails": [
        {"email_id": item["email_id"], "output_id": item["output_id"], "kind": item["kind"],
         "md": str(item["md"]), "txt": str(item["txt"]),
         "warnings": len(item["warnings"]), "banner": item["banner"]}
        for item in prepared],
        "overview_md": str(overview_path) if overview_path.is_file() else None})


def cmd_stage5_rebuild_overview(args) -> None:
    """Rebuild the program 套磁邮件总览.md from professor-local Stage-5 state.

    Issue #68 made this aggregate the only Stage-5 writer of a derived
    projection: it reads every professor-local pack, its exact local state and
    its verify cache, and writes nothing else. A malformed pack or state fails
    closed before the file is touched, and a manual overview edit stops only
    this rebuild.
    """
    program_root = Path(args.program_root)
    research_root = program_root / "教授研究"
    sources = load_header_sources(program_root)
    overview_rows = ["| 教授 | 方向（ja/zh） | 收件邮箱 | 核验 | 首封邮件 | 跟进邮件 | 首封纯文本 | 跟进纯文本 |",
                     "|---|---|---|---|---|---|---|---|"]
    professors = 0
    rendered = 0
    generated_at = []
    for pack_path in (sorted(research_root.rglob(EMAIL_PACK)) if research_root.is_dir() else []):
        if pack_path.parent == research_root:
            # The legacy program-level pack is Issue #67's migration input and
            # names no professor, so it contributes no rows to the aggregate.
            continue
        pack, error = read_json_file(pack_path)
        if error:
            fail("missing_email_pack", f"email pack unreadable: {pack_path}",
                 email_pack=str(pack_path))
        owner = stage5_pack_owner(pack, pack_path)
        require_professor_dir_under_program(owner["professor_dir"], program_root)
        state_path = owner["professor_dir"] / EMAIL_STATE
        email_state, state_error = read_json_file(state_path)
        if state_error == "not_found":
            # Stage 5 never ran for this professor: there is nothing to project.
            continue
        if state_error or not isinstance(email_state, dict):
            fail("missing_email_state",
                 f"{owner['professor']}: email state unreadable: {state_path}")
        entries = email_state.get("emails") or {}
        if not isinstance(entries, dict):
            fail("missing_email_state",
                 f"{owner['professor']}: email state has no emails object: {state_path}")
        verify_check = verify_state(owner["professor_dir"], sources)
        items = ((verify_check.get("data") or {}).get("items") or {})
        email_value = (items.get("email") or {}).get("value") or "?"
        bad = []
        if (items.get("roster") or {}).get("verdict") == "not_found":
            bad.append("在册 not_found")
        if (items.get("email") or {}).get("verdict") == "unverified":
            bad.append("邮箱 unverified")
        bad.extend(str(w) for w in (items.get("warnings") or []))
        verify_label = "✅ 全 confirmed" if not bad else "⚠ " + "；".join(bad)

        def link(path: str | None, label: str) -> str:
            return f"[{label}]({rel_path(Path(path), research_root)})" if path else "—"

        professors += 1
        for email in pack.get("emails") or []:
            if not isinstance(email, dict):
                continue
            entry = entries.get(email.get("email_id"))
            if not isinstance(entry, dict):
                continue
            initial = entry.get("files") or {}
            followup = (entry.get("followup") or {}).get("files") or {}
            if not initial and not followup:
                continue
            for value in (entry.get("generated_at"),
                          (entry.get("followup") or {}).get("generated_at")):
                if isinstance(value, str) and value:
                    generated_at.append(value)
            rendered += 1
            overview_rows.append(
                f"| {email.get('professor')} | {email.get('name_ja')}/{email.get('name_zh')} | "
                f"{email_value} | {verify_label} | {link(initial.get('md'), '.md')} | "
                f"{link(followup.get('md'), '跟进 .md')} | {link(initial.get('txt'), '首封 .txt')} | "
                f"{link(followup.get('txt'), '跟进 .txt')} |")
    overview_body = ("# 套磁邮件总览\n\n"
                     f"> {max(generated_at, default='尚无已提交邮件')} ｜ 由 contact_state 渲染\n\n" +
                     "\n".join(overview_rows) + "\n")
    overview_path = research_root / EMAIL_OVERVIEW
    if overview_path.exists():
        header, existing_body = split_frontmatter(overview_path.read_text(encoding="utf-8"))
        if not header or header.get("managed_by") != MANAGED_BY or \
                header.get("render_sha256") != sha256_text(existing_body):
            soft_exit("needs_decision", "manual_markdown_changed", target=str(overview_path))
    body_sha = sha256_text(overview_body)
    atomic_write(overview_path, render_frontmatter(
        sha256_obj({"projection": EMAIL_OVERVIEW, "body": body_sha}), body_sha) + overview_body)
    emit({"status": "ok", "overview_md": str(overview_path), "professors": professors,
          "emails": rendered})


def cmd_stage5_record_validation(args) -> None:
    professor_dir = Path(args.professor_dir)
    state_path = professor_dir / EMAIL_STATE
    state, state_error = read_json_file(state_path)
    if state_error or not isinstance(state, dict):
        fail("missing_email_state", f"email state unreadable: {state_path}")
    validation_data, validation_error = read_json_file(Path(args.validation_file))
    if validation_error or not isinstance(validation_data, dict):
        fail("invalid_validation_json", f"validation file unreadable: {args.validation_file}")
    results = validation_data.get("results")
    if not isinstance(results, list) or not results:
        fail("invalid_validation_json", "validation results must be a non-empty list")
    emails = state.get("emails")
    if not isinstance(emails, dict):
        fail("invalid_email_state", "email state has no emails object")
    validated = {}
    seen = set()
    for result in results:
        if not isinstance(result, dict):
            fail("invalid_validation_json", "each validation result must be an object")
        email_id = result.get("email_id")
        output_id = result.get("output_id") or email_id
        kind = "followup" if isinstance(output_id, str) and output_id.endswith("::followup") else "initial"
        base_email_id = output_id[:-len("::followup")] if kind == "followup" else email_id
        validation_result = result.get("result")
        rounds = result.get("rounds", 0)
        issues = result.get("issues")
        if output_id in seen:
            fail("invalid_validation_json", f"duplicate validation result for {output_id}")
        seen.add(output_id)
        if base_email_id not in emails:
            fail("unknown_email_id", f"validation email_id not in state: {base_email_id}")
        if kind == "initial" and output_id != email_id:
            fail("invalid_validation_json", f"initial output_id mismatch for {email_id}")
        if validation_result not in ("pass", "fail_after_2_rounds", "skipped"):
            fail("invalid_validation_json", f"invalid validation result for {output_id}: {validation_result}")
        if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
            fail("invalid_validation_json", f"invalid validation rounds for {output_id}: {rounds}")
        if validation_result == "pass" and rounds not in (1, 2):
            fail("invalid_validation_json", f"pass validation needs 1-2 rounds for {output_id}")
        if validation_result == "fail_after_2_rounds" and rounds != 2:
            fail("invalid_validation_json", f"fail_after_2_rounds needs rounds=2 for {output_id}")
        if validation_result == "skipped" and rounds > 2:
            fail("invalid_validation_json", f"skipped validation needs rounds=0-2 for {output_id}")
        if not isinstance(issues, list):
            fail("invalid_validation_json", f"validation issues must be a list for {output_id}")
        validated[output_id] = {
            "email_id": base_email_id, "kind": kind,
            "result": validation_result, "rounds": rounds,
            "issues": issues, "validated_at": now_utc()}
    updated = []
    for output_id, validation in validated.items():
        target = emails[validation["email_id"]]
        if validation["kind"] == "followup":
            target.setdefault("followup", {})["validation"] = validation
        else:
            target["validation"] = validation
        updated.append(output_id)
    atomic_json(state_path, state)
    emit({"status": "ok", "state_path": str(state_path), "updated": updated})


def load_validator_results(path: Path, allowed_ids: set, id_field: str) -> dict:
    data, error = read_json_file(path)
    if error or not isinstance(data, dict) or not isinstance(data.get("results"), list) or not data["results"]:
        fail("invalid_validation_json", f"validation results must be a non-empty list: {path}")
    output = {}
    for result in data["results"]:
        if not isinstance(result, dict):
            fail("invalid_validation_json", "each validator result must be an object")
        item_id = result.get(id_field)
        if item_id not in allowed_ids:
            fail("unknown_reference_id", f"validator {id_field} outside state: {item_id}")
        if item_id in output:
            fail("invalid_validation_json", f"duplicate validator result: {item_id}")
        if result.get("result") not in ("pass", "fail_after_2_rounds", "skipped"):
            fail("invalid_validation_json", f"invalid validator result for {item_id}")
        rounds = result.get("rounds")
        if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
            fail("invalid_validation_json", f"invalid validator rounds for {item_id}")
        if result["result"] == "pass" and rounds not in (1, 2):
            fail("invalid_validation_json", f"pass validator needs 1-2 rounds for {item_id}")
        if result["result"] == "fail_after_2_rounds" and rounds != 2:
            fail("invalid_validation_json", f"fail_after_2_rounds needs rounds=2 for {item_id}")
        if result["result"] == "skipped" and rounds > 2:
            fail("invalid_validation_json", f"skipped validator needs rounds=0-2 for {item_id}")
        if not isinstance(result.get("issues"), list):
            fail("invalid_validation_json", f"validator issues must be a list for {item_id}")
        output[item_id] = {
            "result": result["result"], "rounds": rounds,
            "issues": result["issues"], "validated_at": now_utc()}
    return output






# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage2_validation = _stage2_validation_module.build(
    Stage2Context=Stage2Context,
    Stage2PackRefineContext=Stage2PackRefineContext,
    atomic_json=atomic_json,
    emit=emit,
    fail=fail,
    soft_exit=soft_exit,
    _stage3_normalized_absolute_path=_stage3_normalized_absolute_path,
    now_utc=now_utc,
    sha256_bytes=sha256_bytes,
    sha256_text=sha256_text,
    sha256_obj=sha256_obj,
    read_json_file=read_json_file,
    truncate=truncate,
    filename_component=filename_component,
    direction_machine_id=direction_machine_id,
    pack_paper_index=pack_paper_index,
    direction_papers=direction_papers,
    load_input_pack=load_input_pack,
    pack_direction_relevant_keys=pack_direction_relevant_keys,
    split_frontmatter=split_frontmatter,
    managed_conflict=managed_conflict,
    managed_write=managed_write,
    _canonical_directory=_canonical_directory,
    stage2_pack_state_fingerprint=stage2_pack_state_fingerprint,
    stage2_pack_content_fingerprint=stage2_pack_content_fingerprint,
    validate_narrative_entry=validate_narrative_entry,
    rendered_markdown_block_lines=rendered_markdown_block_lines,
    render_positioning_block=render_positioning_block,
    render_analysis_md=render_analysis_md,
    stage2_require_paper_reference_titles=stage2_require_paper_reference_titles,
    stage2_trusted_paper_title=stage2_trusted_paper_title,
    stage2_require_later_paper_titles=stage2_require_later_paper_titles,
    MANAGED_BY=MANAGED_BY,
    INPUT_PACK=INPUT_PACK,
    ANALYSIS_MD=ANALYSIS_MD,
    QUOTE_INPUT_CHARS=QUOTE_INPUT_CHARS,
    TRANSLATION_INPUT_CHARS=TRANSLATION_INPUT_CHARS,
    PLACEHOLDER_RE=PLACEHOLDER_RE
)

stage2_pack_scope = _stage2_validation.stage2_pack_scope
stage2_bound_render = _stage2_validation.stage2_bound_render
stage2_merge_later_paper_source = _stage2_validation.stage2_merge_later_paper_source
stage2_rendered_later_papers = _stage2_validation.stage2_rendered_later_papers
stage2_restore_pack_later_papers = _stage2_validation.stage2_restore_pack_later_papers
stage2_parse_report_location = _stage2_validation.stage2_parse_report_location
stage2_validation_report = _stage2_validation.stage2_validation_report
stage2_require_recorded_validation = _stage2_validation.stage2_require_recorded_validation
stage2_pack_matches_facts = _stage2_validation.stage2_pack_matches_facts
stage2_validation_material = _stage2_validation.stage2_validation_material
stage2_refine_context = _stage2_validation.stage2_refine_context
cmd_stage2_refine_plan = _stage2_validation.cmd_stage2_refine_plan
cmd_stage2_refine_finalize = _stage2_validation.cmd_stage2_refine_finalize
cmd_stage2_record_validation = _stage2_validation.cmd_stage2_record_validation


def cmd_stage3_record_validation(args) -> None:
    """Record one real Stage-3 validator round from its own raw output.

    The runner owns the translation: rounds are counted here, the terminal
    verdict per machine scope is derived from the validator's own findings, and
    the record is bound to the rendered revision it describes.  Nothing in the
    written state can be asserted by a caller.

    The handoff mode (r13 §6.4, ``--handoff-file`` + ``--handoff-sha256`` +
    ``--expected-validation-sha256``) takes the professor and validation path
    from the verified handoff metadata and digest-checks the exact byte buffer
    it then parses — the legacy ``--professor-dir`` + ``--validation-file``
    calls keep their behavior unchanged, and the two modes are mutually
    exclusive.
    """
    handoff_triple = (getattr(args, "handoff_file", None),
                      getattr(args, "handoff_sha256", None),
                      getattr(args, "expected_validation_sha256", None))
    handoff_mode = any(handoff_triple)
    if handoff_mode and not all(handoff_triple):
        fail("invalid_params",
             "--handoff-file, --handoff-sha256 and --expected-validation-sha256 "
             "must be used together")
    legacy_pair = (getattr(args, "professor_dir", None),
                   getattr(args, "validation_file", None))
    if bool(legacy_pair[0]) != bool(legacy_pair[1]):
        fail("invalid_params",
             "stage3-record-validation needs --professor-dir and --validation-file together")
    if handoff_mode and any(legacy_pair):
        fail("invalid_params",
             "the handoff mode is mutually exclusive with --professor-dir and "
             "--validation-file; the handoff metadata alone carries both")
    if not handoff_mode and not all(legacy_pair):
        fail("invalid_params",
             "stage3-record-validation needs --professor-dir + --validation-file, "
             "or the handoff mode (--handoff-file + --handoff-sha256 + "
             "--expected-validation-sha256)")
    metadata = None
    if handoff_mode:
        metadata = _load_stage3_handoff(args)
        professor_dir = Path(metadata["professor_dir"])
        validation_path = Path(metadata["validation_file"])
    else:
        professor_dir = Path(args.professor_dir)
        validation_path = Path(args.validation_file)
    pack, _ = load_input_pack(professor_dir)
    state, state_error = load_candidate_state(professor_dir, pack)
    if state_error or state is None:
        fail("missing_candidate_state",
             f"candidate state unreadable: {professor_dir / CANDIDATE_STATE}")
    previous = state.get("validator") if isinstance(state.get("validator"), dict) else {}
    raw_round = previous.get("round")
    if isinstance(raw_round, bool) or not isinstance(raw_round, int):
        raw_round = 0
    previous_pending = (
        previous.get("pending") if isinstance(previous.get("pending"), dict) else {}
    )
    if raw_round >= 1 and previous_pending:
        fail(
            "validation_correction_required",
            "complete the recorded Stage-3 correction with stage3-plan/finalize "
            "--validation-file before recording another validator round",
        )
    raw_input = None
    if handoff_mode:
        # r13 §6.4: the render and round must still match the verified handoff,
        # and the digest must hold over the exact bytes parsed below — never
        # over one snapshot while another file is opened for the record.
        render_sha, _body = _stage3_bound_render(professor_dir, state)
        if render_sha != metadata["render_sha256"]:
            fail("validation_render_changed",
                 "the committed candidate render changed since this handoff was "
                 "prepared; re-run stage3-prepare-validation")
        _require_stage3_handoff_round(state, render_sha, metadata["round"], fail=fail)
        if validation_path.is_symlink() or not validation_path.is_file():
            fail("invalid_validation_source",
                 f"the recorded validation file must be this round's regular "
                 f"target file: {validation_path}")
        try:
            raw_input = validation_path.read_bytes()
        except (OSError, ValueError):
            fail("invalid_validation_json",
                 f"style-validator output unreadable: {validation_path}")
        if sha256_bytes(raw_input) != args.expected_validation_sha256:
            fail("validation_sha256_mismatch",
                 f"the recorded validation bytes do not match the digest returned by "
                 f"stage3-save-validation: {validation_path}")
    evidence = stage3_validation_evidence(validation_path, professor_dir, state,
                                          raw_input=raw_input)
    round_no = raw_round + 1
    if metadata is not None and round_no != metadata["round"]:
        fail("validation_round_sequence_invalid",
             f"the recorded round {round_no} does not match the handoff round "
             f"{metadata['round']}")
    if round_no > STAGE3_VALIDATION_MAX_ROUNDS:
        fail("validation_rounds_exhausted",
             f"Stage-3 style validation is bounded to {STAGE3_VALIDATION_MAX_ROUNDS} rounds; "
             "the terminal record already exists")
    results = dict(previous.get("results") or {}) if isinstance(previous.get("results"), dict) else {}
    groups = dict(previous.get("groups") or {}) if isinstance(previous.get("groups"), dict) else {}
    pending = dict(previous.get("pending") or {}) if isinstance(previous.get("pending"), dict) else {}
    at = now_utc()
    exhausted = round_no >= STAGE3_VALIDATION_MAX_ROUNDS
    summary = []
    global_issues = (evidence["failed"].get("global") or {}).get("issues") or []
    if global_issues:
        rendered_scopes = {
            key: scope for key, scope in evidence["scopes"].items()
            if key != "global"
        }
        if not rendered_scopes:
            fail("validation_evidence_not_recorded",
                 "global validator issues cannot be assigned to a rendered direction or group")
        for key, scope in rendered_scopes.items():
            row = evidence["failed"].setdefault(
                key, {"scope": scope, "candidate_ids": [], "issues": []})
            row["issues"].extend(
                {**issue, "scope": scope, "render_sha256": evidence["render_sha256"]}
                for issue in global_issues
            )
    for key, scope in sorted(evidence["scopes"].items()):
        if key == "global":
            continue
        kind, _, ident = key.partition(":")
        row = evidence["failed"].get(key) or {}
        issues = row.get("issues") or []
        record = {
            "result": "pass" if not issues else (
                "fail_after_2_rounds" if exhausted else "fail"),
            "rounds": round_no,
            "issues": issues,
            "candidate_ids": row.get("candidate_ids") or [],
            "scope": scope,
            "render_sha256": evidence["render_sha256"],
            "validated_at": at,
        }
        target = results if kind == "direction" else groups
        if issues and not exhausted:
            target.pop(ident, None)
            pending[key] = record
        else:
            target[ident] = record
            pending.pop(key, None)
        summary.append({"scope": key, "result": record["result"], "rounds": round_no,
                        "blocking": len(issues)})
    updated = dict(state)
    updated["validator"] = {
        "round": round_no,
        "render_sha256": evidence["render_sha256"],
        "raw_verdict": evidence["verdict"],
        "results": results,
        "groups": groups,
        "pending": pending,
        "global": (evidence["failed"].get("global") or {}).get("issues") or [],
        "updated_at": at,
    }
    atomic_json(professor_dir / CANDIDATE_STATE, updated)
    emit({"status": "ok", "state_path": str(professor_dir / CANDIDATE_STATE),
          "round": round_no, "raw_verdict": evidence["verdict"],
          "render_sha256": evidence["render_sha256"], "scopes": summary,
          "validation_input_sha256": evidence["validation_input_sha256"],
          "needs_correction": bool(pending),
          "terminal": not pending})


def read_legacy_index(index_path: Path) -> tuple[dict | None, str | None]:
    data, error = read_json_file(index_path)
    if error:
        return None, error
    if not isinstance(data, dict):
        return None, "not an object"
    return data, None


def migration_source_fingerprint(professor_dir: Path) -> str:
    paths = {
        professor_dir / "论文分析" / "_index.json",
        professor_dir / "papers.json",
        professor_dir / CANDIDATES_MD,
    }
    index, error = read_legacy_index(professor_dir / "论文分析" / "_index.json")
    if error is None and isinstance(index, dict):
        for paper in (index.get("papers") or {}).values():
            if not isinstance(paper, dict):
                continue
            for field in ("file", "future_work_sidecar"):
                value = paper.get(field)
                if value:
                    paths.add(Path(value))
    records = []
    for path in sorted(paths, key=lambda item: str(item)):
        try:
            records.append({"path": str(path), "sha256": sha256_bytes(path.read_bytes())})
        except (OSError, ValueError):
            records.append({"path": str(path), "sha256": None})
    return sha256_obj(records)


def classify_direction(pack_entry: dict) -> dict:
    reasons = list(pack_entry.get("reasons") or [])
    schema2 = pack_entry["schema2"]
    sidecars_ok = pack_entry["sidecar_ok"]
    candidates_meta = pack_entry["candidates_meta"]
    if not schema2:
        reasons.append("index 非 schema 2（无精确 per-gap gaps[]）")
    if not sidecars_ok:
        reasons.append("存在无有效 sidecar 的 gap 论文")
    if schema2 and sidecars_ok:
        stage2 = "ready"
        stage3 = "recoverable" if candidates_meta else "needs_stage3"
        classification = "ready" if candidates_meta else "needs_stage3"
        if not candidates_meta:
            reasons.append("阶段 3 候选无可安全恢复的机器元数据（无 candidate_meta/gap_ids）")
    else:
        stage2 = "needs_stage2"
        stage3 = "needs_stage3"
        classification = "needs_stage2"
        reasons.append("缺有效 sidecar/精确 gap ID，需重跑阶段 2 sidecar-first 流程")
    return {"classification": classification, "stage2": stage2, "stage3": stage3,
            "reasons": reasons}


def migrate_entry_for_professor(professor_dir: Path, program_root: Path) -> dict | None:
    index_path = professor_dir / "论文分析" / "_index.json"
    candidates_md = professor_dir / CANDIDATES_MD
    if not index_path.is_file() and not candidates_md.is_file():
        return None
    entry = {
        "professor_dir": str(professor_dir),
        "professor": professor_dir.name,
        "category": professor_dir.parent.name,
        "source_fingerprint": migration_source_fingerprint(professor_dir),
        "already_migrated": (professor_dir / INPUT_PACK).is_file(),
        "schema2": False, "sidecar_ok": False, "candidates_meta": False,
        "metadata_ok": False, "gap_ids_exact": False,
        "gap_papers": 0, "valid_sidecars": 0,
    }
    if index_path.is_file():
        index, error = read_legacy_index(index_path)
        if error:
            entry["classification"] = "blocked"
            entry["reasons"] = [f"_index.json 不可读：{error}"]
            entry["stage2"] = entry["stage3"] = "blocked"
            return entry
        entry["schema2"] = index.get("schema") == 2
        papers = index.get("papers")
        if isinstance(papers, dict):
            gap_papers = 0
            valid = 0
            exact = True
            valid_gap_pairs = set()
            for key, paper in papers.items():
                if not isinstance(paper, dict):
                    continue
                has_gaps = bool(paper.get("gaps")) or bool(paper.get("gap"))
                if not has_gaps:
                    continue
                gap_papers += 1
                sidecar = paper.get("future_work_sidecar")
                if sidecar:
                    items, legacy, err = load_sidecar(sidecar, paper.get("file"))
                    index_gaps = {g.get("gap_id") for g in (paper.get("gaps") or [])
                                  if isinstance(g, dict) and isinstance(g.get("gap_id"), str)}
                    sidecar_gaps = {item.get("gap_id") for item in items}
                    gap_rows = paper.get("gaps") or []
                    statuses_valid = isinstance(gap_rows, list) and all(
                        isinstance(g, dict) and g.get("gap_id") in index_gaps and
                        g.get("status") in GAP_STATUSES and
                        isinstance(g.get("evidence"), str) and g.get("evidence").strip()
                        for g in gap_rows)
                    if err is None and index_gaps and sidecar_gaps == index_gaps and statuses_valid:
                        valid += 1
                        valid_gap_pairs.update((key, gap_id) for gap_id in index_gaps)
                    else:
                        exact = False
                else:
                    exact = False
            entry["gap_papers"] = gap_papers
            entry["valid_sidecars"] = valid
            entry["sidecar_ok"] = gap_papers == 0 or valid == gap_papers
            entry["gap_ids_exact"] = gap_papers == 0 or exact
            papers_json_path = professor_dir / "papers.json"
            papers_meta, metadata_error = read_json_file(papers_json_path)
            metadata_by_key = {}
            if metadata_error is None and isinstance(papers_meta, dict):
                metadata_by_key = {p.get("item_key"): p for p in papers_meta.get("papers", [])
                                   if isinstance(p, dict)}
            metadata_ok = True
            for key, paper in papers.items():
                if not isinstance(paper, dict):
                    metadata_ok = False
                    continue
                meta = metadata_by_key.get(key) or paper
                title = meta.get("title")
                year = meta.get("year")
                authorship = meta.get("authorship")
                if not isinstance(title, str) or not title.strip() or not isinstance(year, int) or \
                        authorship not in ("first", "corresponding", "solo", "middle", "pending"):
                    metadata_ok = False
            entry["metadata_ok"] = metadata_ok
            if not metadata_ok:
                entry.setdefault("reasons", []).append("论文标题/年份/署名元数据不足")
            if not entry["gap_ids_exact"]:
                entry.setdefault("reasons", []).append("sidecar gap ID 与 schema 2 gaps[] 不精确相等")
    if candidates_md.is_file():
        text = candidates_md.read_text(encoding="utf-8", errors="replace")
        metas = re.findall(r"candidate_meta:\s*(\{.*\})", text)
        parsed_ok = 0
        parsed_total = 0
        known_pairs = set()
        if isinstance(index_path, Path) and index_path.is_file():
            index_data, _ = read_legacy_index(index_path)
            for key, paper in (index_data or {}).get("papers", {}).items():
                for gap in (paper or {}).get("gaps", []):
                    if isinstance(gap, dict) and gap.get("gap_id"):
                        known_pairs.add((key, gap["gap_id"]))
        for meta in metas:
            try:
                payload = json.loads(meta)
                parsed_total += 1
                pairs = payload.get("gap_ids") or []
                pairs_ok = all(isinstance(pair, dict) and
                               (pair.get("item_key"), pair.get("gap_id")) in known_pairs
                               for pair in pairs)
                if payload.get("id") and not payload.get("compatibility_fallback") and pairs_ok:
                    parsed_ok += 1
            except json.JSONDecodeError:
                continue
        entry["candidates_meta"] = parsed_ok > 0
        if parsed_total and parsed_ok != parsed_total:
            entry.setdefault("reasons", []).append("候选 candidate_meta 的 gap ID 无法精确恢复")
    if entry["schema2"] or entry["candidates_meta"] or entry["gap_papers"]:
        entry.update(classify_direction(entry))
        if entry["classification"] == "ready" and not entry["metadata_ok"]:
            entry["classification"] = "blocked"
            entry["stage2"] = entry["stage3"] = "blocked"
            entry.setdefault("reasons", []).append("必要论文元数据不足，不能标记 ready")
        elif entry["classification"] == "ready" and not entry["gap_ids_exact"]:
            entry["classification"] = "blocked"
            entry["stage2"] = entry["stage3"] = "blocked"
            entry.setdefault("reasons", []).append("gap ID 不匹配，不能标记 ready")
    else:
        entry.update({"classification": "needs_stage2", "stage2": "needs_stage2",
                      "stage3": "needs_stage3",
                      "reasons": ["index 无 gap 数据或候选无机器元数据，按需重跑阶段 2"]})
    return entry


def cmd_migrate_plan(args) -> None:
    program_root = Path(args.program_root)
    base = program_root / "教授研究"
    if not base.is_dir():
        fail("invalid_params", f"no 教授研究 under {program_root}")
    entries = []
    seen = set()
    candidate_dirs = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        if (child / "papers.json").is_file() or (child / "论文分析").is_dir():
            candidate_dirs.append(child)
        for professor_dir in sorted(child.iterdir()):
            if professor_dir.is_dir() and ((professor_dir / "papers.json").is_file() or
                                           (professor_dir / "论文分析").is_dir()):
                candidate_dirs.append(professor_dir)
    for professor_dir in candidate_dirs:
        resolved = str(professor_dir.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        entry = migrate_entry_for_professor(professor_dir, program_root)
        if entry:
            entries.append(entry)
    ready = [e for e in entries if e.get("classification") == "ready" and not e.get("already_migrated")]
    plan = {
        "status": "ok",
        "schema": SCHEMA, "managed_by": MANAGED_BY, "generated_at": now_utc(),
        "program_root": str(program_root),
        "directions": entries,
        "ready_count": len(ready),
        "note": "ready=纯脚本可迁移；needs_stage2=缺有效 sidecar/精确 ID；needs_stage3=输入包可迁移但候选无机器元数据；blocked=文件损坏。--apply 只处理 ready 且未迁移的条目，绝不隐式启动阶段 2/3。"}
    if args.out:
        atomic_json(Path(args.out), plan)
    emit(plan)


def apply_ready_entry(program_root: Path, entry: dict, plan: dict) -> dict:
    professor_dir = Path(entry.get("professor_dir") or "")
    try:
        root = program_root.resolve()
        target = professor_dir.resolve()
        if os.path.commonpath((str(root / "教授研究"), str(target))) != str(root / "教授研究"):
            return {"professor": entry.get("professor"), "applied": False,
                    "reason": "professor_dir_outside_program_root"}
    except (OSError, ValueError):
        return {"professor": entry.get("professor"), "applied": False,
                "reason": "invalid_professor_dir"}
    current = migrate_entry_for_professor(professor_dir, program_root)
    if not current or current.get("classification") != "ready":
        return {"professor": entry.get("professor"), "applied": False,
                "reason": "source_changed_or_not_ready"}
    expected_fingerprint = entry.get("source_fingerprint")
    if expected_fingerprint and expected_fingerprint != current.get("source_fingerprint"):
        return {"professor": entry.get("professor"), "applied": False,
                "reason": "source_changed"}
    entry = current
    if (professor_dir / INPUT_PACK).is_file():
        return {"professor": entry["professor"], "applied": False,
                "reason": "already_migrated"}
    index, error = read_legacy_index(professor_dir / "论文分析" / "_index.json")
    if error:
        return {"professor": entry["professor"], "applied": False, "reason": f"index_unreadable:{error}"}
    papers_json_path = professor_dir / "papers.json"
    papers_meta = {}
    if papers_json_path.is_file():
        data, perr = read_json_file(papers_json_path)
        if perr is None and isinstance(data, dict):
            papers_meta = {p.get("item_key"): p for p in data.get("papers", []) if isinstance(p, dict)}
    index_papers = index.get("papers") if isinstance(index.get("papers"), dict) else {}
    library = {}
    for key, paper in index_papers.items():
        if not isinstance(paper, dict):
            continue
        meta = papers_meta.get(key) or {}
        library[key] = {
            "item_key": key,
            "title": meta.get("title") or (paper.get("file") or "").rsplit("/", 1)[-1].replace(".md", ""),
            "year": meta.get("year") or paper.get("year"),
            "month": meta.get("month"),
            "authorship": paper.get("authorship"),
            "abstract": meta.get("abstract") or "",
            "authors": [],
            "has_pdf": meta.get("pdf_status") == "downloaded",
            "analysis_file": paper.get("file"),
            "sidecar_file": paper.get("future_work_sidecar"),
        }
    ctx_facts = {
        "program_root": str(program_root),
        "professor_dir": str(professor_dir),
        "professor": entry["professor"],
        "current_year": datetime.now().year,
        "params": {"gap_scope": "selected_direction", "freshness_scope": "full"},
        "papers": [dict(v, item_key=k) for k, v in library.items()],
        "directions": [{
            "collection_key": f"migrated:{entry['professor']}",
            "name_ja": "（迁移方向）", "name_zh": "migrated from legacy index",
            "status": "active",
            "member_keys": sorted(k for k, p in library.items()
                                  if isinstance(index_papers.get(k), dict) and
                                  (index_papers[k].get("gaps") or index_papers[k].get("gap"))),
            "relevant_keys": [], "named_keys": [],
            "user_note": "",
            "credibility": (index.get("credibility") or index.get("direction", {}).get("credibility")
                            if isinstance(index.get("direction"), dict) else index.get("credibility")) or {},
            "red_lines": [],
        }],
    }
    fd, facts_name = tempfile.mkstemp(prefix="contact-migrate-facts-", suffix=".json")
    os.close(fd)
    facts_path = Path(facts_name)
    try:
        atomic_json(facts_path, ctx_facts)
        ctx = Stage2Context(facts_path)
    finally:
        facts_path.unlink(missing_ok=True)
    pack_directions = []
    papers_map = {}
    cache_entries = {}
    for plan_entry in ctx.direction_plans:
        statuses = {}
        for gap in plan_entry["ranked"]:
            index_paper = index_papers.get(gap["item_key"]) or {}
            status = None
            evidence = None
            for g in index_paper.get("gaps") or []:
                if isinstance(g, dict) and g.get("gap_id") == gap["gap_id"]:
                    status, evidence = g.get("status"), g.get("evidence")
                    break
            if status is None and index_paper.get("gap"):
                status = index_paper.get("gap_status")
                evidence = index_paper.get("gap_status_evidence")
            if status not in GAP_STATUSES:
                continue
            source = ctx.papers.get(gap["item_key"], {})
            cands = freshness_candidates(gap, source, ctx.papers, ctx.current_year,
                                         ctx.family_members.get(gap["item_key"], set()), set())
            cand_list = [{"item_key": key, "digest": ctx.papers[key]["_digest"]}
                         for key in sorted(ctx.papers) if key in sum(cands["tiers"].values(), [])]
            record = {
                "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                "status": status, "model_evidence": evidence or "",
                "candidate_paper_ids": [], "candidate_fingerprint": candidate_fingerprint(cand_list),
                "gap_fingerprint": gap_fingerprint(gap, gap.get("sidecar_sha")),
                "evaluated_at": now_utc(), "confidence": "medium",
                "completed_part": None, "remaining_gap": None, "migrated": True}
            statuses[gap["gap_id"]] = record
            cache_entries[gap["gap_id"]] = record
        built, built_papers = build_direction_pack(ctx, plan_entry, statuses, None)
        built["migrated"] = True
        built["narrative"] = None
        pack_directions.append(built)
        papers_map.update(built_papers)
    pack = {
        "schema": INPUT_PACK_SCHEMA, "kind": INPUT_PACK_KIND,
        "identity_version": DIRECTION_IDENTITY_VERSION,
        "managed_by": MANAGED_BY, "generated_at": now_utc(),
        "professor": entry["professor"], "professor_dir": str(professor_dir),
        "migrated": True,
        "papers": papers_map,
        "directions": pack_directions,
        "cache": {"render": {}}}
    atomic_json(professor_dir / INPUT_PACK, pack)
    if cache_entries:
        save_freshness_cache(professor_dir, cache_entries)
    return {"professor": entry["professor"], "applied": True,
            "pack": str(professor_dir / INPUT_PACK),
            "gaps_migrated": len(cache_entries)}


def cmd_migrate_apply(args) -> None:
    plan, error = read_json_file(Path(args.apply))
    if error or not isinstance(plan, dict):
        fail("invalid_params", f"plan unreadable: {args.apply}")
    plan_root_value = plan.get("program_root")
    if not isinstance(plan_root_value, str) or not plan_root_value:
        fail("invalid_params", "migration plan has no program_root")
    plan_root = Path(plan_root_value)
    program_root = Path(args.program_root) if args.program_root else plan_root
    try:
        if program_root.resolve() != plan_root.resolve():
            fail("invalid_params", "program_root does not match migration plan")
    except OSError:
        fail("invalid_params", "program_root is not resolvable")
    entries = plan.get("directions")
    if not isinstance(entries, list):
        fail("invalid_params", "migration plan directions must be a list")
    applied, skipped = [], []
    for entry in entries:
        if not isinstance(entry, dict):
            fail("invalid_params", "migration plan direction must be an object")
        if entry.get("classification") != "ready":
            skipped.append({"professor": entry.get("professor"),
                            "reason": entry.get("classification")})
            continue
        if entry.get("already_migrated"):
            skipped.append({"professor": entry.get("professor"), "reason": "already_migrated"})
            continue
        target = Path(entry.get("professor_dir") or "")
        try:
            base = program_root.resolve() / "教授研究"
            if not target.is_absolute() or os.path.commonpath((str(base), str(target.resolve()))) != str(base):
                skipped.append({"professor": entry.get("professor"),
                                "reason": "professor_dir_outside_program_root"})
                continue
        except (OSError, ValueError):
            skipped.append({"professor": entry.get("professor"), "reason": "invalid_professor_dir"})
            continue
        applied.append(apply_ready_entry(program_root, entry, plan))
    emit({"status": "ok", "applied": applied, "skipped": skipped})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="professor-contact deterministic state runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("stage2-resolve-plan")
    p.add_argument("--facts", required=True)
    p.add_argument("--results-dir", required=True,
                   help="absolute, existing, empty results directory exclusive to this "
                        "resolve round; every emitted job writes its result_file here and "
                        "the plan's resolve_run_id binds the round to it")
    p.set_defaults(func=lambda a: cmd_stage2_resolve_plan(a))

    p = sub.add_parser("stage2-resolve-finalize")
    p.add_argument("--facts", required=True)
    p.add_argument("--results", required=True)
    p.add_argument("--keep-provisional",
                   help="comma-separated collection keys the user explicitly decided to keep "
                        "provisional; persisted as accepted resolved state (decision="
                        "user_kept_provisional) instead of leaving a pending proposal")
    p.set_defaults(func=lambda a: cmd_stage2_resolve_finalize(a))

    p = sub.add_parser("stage2-resolve-accept")
    p.add_argument("--facts", required=True)
    p.add_argument("--ckeys", required=True,
                   help="comma-separated collection keys the user adopted; flips their "
                        "proposed resolved entries to accepted so stage2-finalize may apply them")
    p.set_defaults(func=lambda a: cmd_stage2_resolve_accept(a))

    p = sub.add_parser("stage2-plan")
    p.add_argument("--facts", required=True)
    p.add_argument("--preflight-file", required=True,
                   help="saved stage2-preflight stdout; the plan is bound to the same "
                        "professor-local transaction identity before it emits jobs")
    p.set_defaults(func=lambda a: cmd_stage2_plan(a))

    p = sub.add_parser("stage2-preflight")
    p.add_argument("--program-root", required=True)
    p.add_argument("--professor", required=True)
    p.add_argument("--target-file", required=True,
                   help="authoritative professor-local Stage-0 target file")
    p.add_argument("--paper-analysis", default="relevant")
    p.add_argument("--gap-scope", default="selected_direction")
    p.add_argument("--freshness-scope", default="shortlist")
    p.add_argument("--max-relevant-papers", type=int, default=None)
    p.set_defaults(func=cmd_stage2_preflight)

    p = sub.add_parser("stage2-finalize")
    p.add_argument("--facts", required=True)
    p.add_argument("--results", required=True)
    p.add_argument("--decision-file")
    p.add_argument("--resolved-directions")
    p.add_argument("--preflight-file", required=True,
                   help="saved stage2-preflight stdout; re-verifies cheap inputs "
                        "before any write and seeds cache.preflight")
    p.set_defaults(func=cmd_stage2_finalize)

    p = sub.add_parser("stage2-refine-plan")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--facts", help="原阶段 2 facts；存在时校验其 fingerprint")
    group.add_argument("--professor-dir", help="facts 已过期时，从已接受输入包读取修订材料")
    p.add_argument("--validation-file", required=True)
    p.add_argument("--direction-id", help="只为一个失败方向（机器身份）生成修订 job")
    p.add_argument("--collection-key", help="deprecated v1 兼容：经输入包精确映射解析为 direction_id")
    p.set_defaults(func=cmd_stage2_refine_plan)

    p = sub.add_parser("stage2-refine-finalize")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--facts", help="原阶段 2 facts；存在时校验其 fingerprint")
    group.add_argument("--professor-dir", help="facts 已过期时，从已接受输入包读取修订材料")
    p.add_argument("--results", required=True)
    p.add_argument("--validation-file", required=True)
    p.add_argument("--direction-id", help="只应用一个失败方向（机器身份）的修订结果")
    p.add_argument("--collection-key", help="deprecated v1 兼容：经输入包精确映射解析为 direction_id")
    p.add_argument("--decision-file")
    p.set_defaults(func=cmd_stage2_refine_finalize)

    p = sub.add_parser("stage3-plan")
    p.add_argument("--professor-dir",
                   help="required without an invocation credential; mutually "
                        "exclusive with --invocation-file")
    p.add_argument("--profile")
    p.add_argument("--refresh-scope", choices=REFRESH_SCOPES)
    p.add_argument("--direction-id", help="只处理输入包中的一个方向（canonical 机器身份）")
    p.add_argument("--collection-key", help="deprecated v1 兼容：经输入包精确映射解析为 direction_id")
    p.add_argument("--skip-direction-ids",
                   help="comma-separated direction IDs the user explicitly skipped; "
                        "persisted as stage3_status=skipped, never as silent omission")
    p.add_argument("--cross-direction-groups",
                   help="JSON list of direction-ID lists, e.g. '[\"dir_A\",\"dir_B\"]'. "
                        "Explicit opt-in ONLY: each group gets one separate cross job; "
                        "absent/empty means no cross-direction work at all")
    p.add_argument("--selection",
                   help="selection container for --refresh-scope selected; the Stage-4 "
                        "workflow passes <professor_dir>/套磁选择.json (issue #67)")
    p.add_argument("--program-root")
    p.add_argument("--validation-file",
                   help="raw style-validator JSON; forces text-only correction jobs for the scopes "
                        "the recorded round actually failed (--direction-id may only narrow them)")
    p.add_argument("--capture-invocation", metavar="DIR",
                   help="first-round only: write this invocation's exclusive credential "
                        "file into the per-invocation directory and return its path+sha256")
    p.add_argument("--invocation-file", metavar="FILE",
                   help="consume a captured invocation credential (with --invocation-sha256); "
                        "mutually exclusive with re-supplied professor/profile/root/scope/"
                        "skip/group/direction/selection source parameters")
    p.add_argument("--invocation-sha256", metavar="SHA256",
                   help="SHA-256 of the exact credential file bytes")
    p.set_defaults(func=cmd_stage3_plan)

    p = sub.add_parser("stage3-finalize")
    p.add_argument("--professor-dir",
                   help="required without an invocation credential; mutually "
                        "exclusive with --invocation-file")
    p.add_argument("--results", required=True)
    p.add_argument("--profile")
    p.add_argument("--refresh-scope", choices=REFRESH_SCOPES)
    p.add_argument("--direction-id", help="只处理输入包中的一个方向（canonical 机器身份）")
    p.add_argument("--collection-key", help="deprecated v1 兼容：经输入包精确映射解析为 direction_id")
    p.add_argument("--skip-direction-ids",
                   help="comma-separated direction IDs the user explicitly skipped")
    p.add_argument("--cross-direction-groups",
                   help="JSON list of direction-ID lists；必须与 stage3-plan 的请求一致")
    p.add_argument("--selection",
                   help="selection container for --refresh-scope selected; the Stage-4 "
                        "workflow passes <professor_dir>/套磁选择.json (issue #67)")
    p.add_argument("--program-root")
    p.add_argument("--decision-file")
    p.add_argument("--validation-file",
                   help="same raw style-validator JSON used by stage3-plan correction")
    p.add_argument("--invocation-file", metavar="FILE",
                   help="consume a captured invocation credential (with --invocation-sha256); "
                        "mutually exclusive with re-supplied professor/profile/root/scope/"
                        "skip/group/direction/selection source parameters")
    p.add_argument("--invocation-sha256", metavar="SHA256",
                   help="SHA-256 of the exact credential file bytes")
    p.set_defaults(func=cmd_stage3_finalize)

    p = sub.add_parser("stage3-rebuild-overview",
                       help="rebuild the program-level candidates overview from committed "
                            "professor-local candidate states (derived projection; issue #66)")
    p.add_argument("--program-root", required=True)
    p.set_defaults(func=cmd_stage3_rebuild_overview)

    p = sub.add_parser("stage3-write-validation",
                       help="write the complete Stage-3 validator result to its specified handoff path")
    p.add_argument("--output-file",
                   help="one specified absolute output path for a single candidates entry")
    p.add_argument("--output-map-json",
                   help="JSON list mapping every candidates file path to its specified output_file")
    p.add_argument("--result-json",
                   help="the complete validator result object as one JSON command argument")
    p.set_defaults(func=cmd_stage3_write_validation)

    p = sub.add_parser("stage3-prepare-validation",
                       help="issue #66 r13 §6.1: create this round's one-time validation "
                            "handoff (metadata, validator output path, saved target path) "
                            "from this professor's invocation credential and committed state")
    p.add_argument("--invocation-file", metavar="FILE", required=True,
                   help="the captured invocation credential of the committed round")
    p.add_argument("--invocation-sha256", metavar="SHA256", required=True,
                   help="SHA-256 of the exact credential file bytes")
    p.add_argument("--round", type=int, required=True, choices=(1, 2),
                   help="the validation round to prepare; must match the professor's "
                        "recorded validator facts, never the temp directory state")
    p.set_defaults(func=cmd_stage3_prepare_validation)

    p = sub.add_parser("stage3-save-validation",
                       help="issue #66 r13 §6.3: copy the validator's raw output bytes, "
                            "unchanged, from the handoff's source file to its recorded target")
    p.add_argument("--handoff-file", metavar="FILE", required=True,
                   help="the handoff metadata file returned by stage3-prepare-validation")
    p.add_argument("--handoff-sha256", metavar="SHA256", required=True,
                   help="SHA-256 of the exact handoff metadata bytes")
    p.set_defaults(func=cmd_stage3_save_validation)

    p = sub.add_parser("stage4-finalize",
                       help="commit professor-local Stage-4 authority per professor and emit "
                            "one aggregate 教授-scoped result (issue #67)")
    p.add_argument("--program-root", required=True)
    p.add_argument("--selection-input", required=True)
    p.add_argument("--profile")
    p.set_defaults(func=cmd_stage4_finalize)

    p = sub.add_parser("stage4-migrate-local",
                       help="scoped legacy migration of ONE professor_dir into its "
                            "professor-local Stage-4 pair; legacy files stay untouched")
    p.add_argument("--program-root", required=True)
    p.add_argument("--professor-dir", required=True)
    p.add_argument("--profile")
    p.set_defaults(func=cmd_stage4_migrate_local)

    p = sub.add_parser("stage5-plan")
    p.add_argument("--program-root", required=True)
    # Optional at the parser on purpose: a missing local pack must answer with
    # this runner's own JSON error contract (invalid_params), not an argparse
    # usage dump. Issue #68 removed the program-level fallback, so there is no
    # default path left to construct.
    p.add_argument("--email-pack",
                   help="教授本地 邮件输入.json（阶段 4 产出；阶段 5 必填的唯一事实源）")
    p.add_argument("--email-id")
    p.add_argument("--profile")
    p.add_argument("--template")
    p.add_argument("--followup-template")
    p.add_argument("--mode", choices=("first", "both", "followup"), default="first",
                    help="生成首封、首封+跟进，或只生成跟进邮件")
    p.add_argument("--result")
    p.add_argument("--choices",
                   help="当前教授选择 JSON 文件的路径；只含本教授已分配的行")
    p.set_defaults(func=cmd_stage5_plan)

    p = sub.add_parser("stage5-finalize")
    p.add_argument("--program-root", required=True)
    p.add_argument("--email-pack",
                   help="教授本地 邮件输入.json（阶段 4 产出；阶段 5 必填的唯一事实源）")
    p.add_argument("--email-id")
    p.add_argument("--result", required=True)
    p.add_argument("--humanized")
    p.add_argument("--humanized-map", help="JSON object mapping output_id to absolute humanized body path")
    p.add_argument("--choices",
                   help="当前教授选择 JSON 文件的路径；只含本教授已分配的行")
    p.add_argument("--template")
    p.add_argument("--followup-template")
    p.add_argument("--mode", choices=("first", "both", "followup"), default="first",
                    help="生成首封、首封+跟进，或只生成跟进邮件")
    p.add_argument("--profile")
    p.add_argument("--decision-file")
    p.add_argument("--audit-provenance",
                   choices=tuple(STAGE5_AUDIT_PROVENANCE), default="business",
                   help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_stage5_finalize)

    p = sub.add_parser("stage5-partition-choices",
                       help="根代理确定性分配：按 (professor_dir, email_id) 一次性分配原始选择；"
                            "返回顶层 owners 列表，根代理逐项生成单教授交接文件；"
                            "歧义留在根代理，不向教授代理广播多教授数据",
                       description="返回对象的顶层 owners 列表包含本次所有教授的分配结果；"
                                   "仅根代理解析，并逐项生成单教授交接文件。")
    p.add_argument("--program-root", required=True)
    p.add_argument("--owner", action="append", nargs="+",
                   metavar=("EMAIL_PACK", "EMAIL_ID"),
                   help="本次选中的一个教授本地 邮件输入.json（来自阶段 4 结果或 discovery 行），"
                        "可后跟该教授的定向 email_id；每位教授恰好一次，可重复")
    p.add_argument("--choices", required=True,
                   help="原始用户选择 JSON 文件的路径；文件内容为对象或对象列表；只在根代理分配")
    p.add_argument("--out",
                   help="写出包含完整 owners 列表的多教授分配对象的 JSON 文件路径；"
                        "仅根代理解析并逐项生成单教授交接文件，不能整份交给教授代理；"
                        "本次请求生命周期结束后由调用方清理")
    p.set_defaults(func=cmd_stage5_partition_choices)

    p = sub.add_parser("stage5-list-inputs",
                       help="只读发现各教授本地 邮件输入.json：逐个返回 professor、professor_dir、"
                            "email_pack、status、reason_code；坏包只形成自己的失败行，不写任何文件")
    p.add_argument("--program-root", required=True)
    p.add_argument("--professor",
                   help="只返回顶层姓名精确匹配该教授名的行；没有匹配返回 needs_input")
    p.set_defaults(func=cmd_stage5_list_inputs)

    p = sub.add_parser("stage5-rebuild-overview",
                       help="只重建程序级 套磁邮件总览.md：从各教授本地 pack 与其本地状态派生，"
                            "不改动任何 pack/状态/邮件/核验文件")
    p.add_argument("--program-root", required=True)
    p.set_defaults(func=cmd_stage5_rebuild_overview)

    p = sub.add_parser("stage5-record-validation")
    p.add_argument("--professor-dir", required=True)
    p.add_argument("--validation-file", required=True)
    p.set_defaults(func=cmd_stage5_record_validation)

    p = sub.add_parser("stage2-record-validation")
    p.add_argument("--professor-dir", required=True)
    p.add_argument("--validation-file", required=True)
    p.set_defaults(func=cmd_stage2_record_validation)

    p = sub.add_parser("stage3-record-validation")
    p.add_argument("--professor-dir", required=False,
                   help="legacy mode together with --validation-file; mutually "
                        "exclusive with the handoff mode")
    p.add_argument("--validation-file", required=False,
                   help="legacy mode together with --professor-dir; mutually "
                        "exclusive with the handoff mode")
    p.add_argument("--handoff-file", metavar="FILE",
                   help="handoff mode (issue #66 r13 §6.4) together with --handoff-sha256 "
                        "and --expected-validation-sha256: professor and validation path "
                        "come from the verified handoff metadata")
    p.add_argument("--handoff-sha256", metavar="SHA256",
                   help="SHA-256 of the exact handoff metadata bytes")
    p.add_argument("--expected-validation-sha256",
                   metavar="SHA256",
                   help="digest returned by stage3-save-validation; proven over the exact "
                        "bytes this record parses")
    p.set_defaults(func=cmd_stage3_record_validation)

    p = sub.add_parser("migrate-v3")
    p.add_argument("--plan", action="store_true")
    p.add_argument("--apply")
    p.add_argument("--program-root")
    p.add_argument("--out")
    p.set_defaults(func=lambda a: cmd_migrate_plan(a) if a.plan and not a.apply
                   else cmd_migrate_apply(a))

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
