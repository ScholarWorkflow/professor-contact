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

# Stage-2 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_CONTACT_BASE_PATH = Path(__file__).with_name("_contact_base.py")
_CONTACT_BASE_SPEC = importlib.util.spec_from_file_location(
    "_contact_base", _CONTACT_BASE_PATH)
if _CONTACT_BASE_SPEC is None or _CONTACT_BASE_SPEC.loader is None:
    raise RuntimeError(f"cannot load _contact_base: {_CONTACT_BASE_PATH}")
_contact_base_module = importlib.util.module_from_spec(_CONTACT_BASE_SPEC)
_CONTACT_BASE_SPEC.loader.exec_module(_contact_base_module)

# Stage-2 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_CONTACT_PACK_PATH = Path(__file__).with_name("_contact_pack.py")
_CONTACT_PACK_SPEC = importlib.util.spec_from_file_location(
    "_contact_pack", _CONTACT_PACK_PATH)
if _CONTACT_PACK_SPEC is None or _CONTACT_PACK_SPEC.loader is None:
    raise RuntimeError(f"cannot load _contact_pack: {_CONTACT_PACK_PATH}")
_contact_pack_module = importlib.util.module_from_spec(_CONTACT_PACK_SPEC)
_CONTACT_PACK_SPEC.loader.exec_module(_contact_pack_module)

# Stage-2 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_STAGE3_VALIDATION_PATH = Path(__file__).with_name("_stage3_validation.py")
_STAGE3_VALIDATION_SPEC = importlib.util.spec_from_file_location(
    "_stage3_validation", _STAGE3_VALIDATION_PATH)
if _STAGE3_VALIDATION_SPEC is None or _STAGE3_VALIDATION_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage3_validation: {_STAGE3_VALIDATION_PATH}")
_stage3_validation_module = importlib.util.module_from_spec(_STAGE3_VALIDATION_SPEC)
_STAGE3_VALIDATION_SPEC.loader.exec_module(_stage3_validation_module)

# Stage-3 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_STAGE3_COMMANDS_PATH = Path(__file__).with_name("_stage3_commands.py")
_STAGE3_COMMANDS_SPEC = importlib.util.spec_from_file_location(
    "_stage3_commands", _STAGE3_COMMANDS_PATH)
if _STAGE3_COMMANDS_SPEC is None or _STAGE3_COMMANDS_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage3_commands: {_STAGE3_COMMANDS_PATH}")
_stage3_commands_module = importlib.util.module_from_spec(_STAGE3_COMMANDS_SPEC)
_STAGE3_COMMANDS_SPEC.loader.exec_module(_stage3_commands_module)

# Stage-5 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_STAGE5_INPUT_PATH = Path(__file__).with_name("_stage5_input.py")
_STAGE5_INPUT_SPEC = importlib.util.spec_from_file_location(
    "_stage5_input", _STAGE5_INPUT_PATH)
if _STAGE5_INPUT_SPEC is None or _STAGE5_INPUT_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage5_input: {_STAGE5_INPUT_PATH}")
_stage5_input_module = importlib.util.module_from_spec(_STAGE5_INPUT_SPEC)
_STAGE5_INPUT_SPEC.loader.exec_module(_stage5_input_module)

# Stage-5 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_STAGE5_COMMANDS_PATH = Path(__file__).with_name("_stage5_commands.py")
_STAGE5_COMMANDS_SPEC = importlib.util.spec_from_file_location(
    "_stage5_commands", _STAGE5_COMMANDS_PATH)
if _STAGE5_COMMANDS_SPEC is None or _STAGE5_COMMANDS_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage5_commands: {_STAGE5_COMMANDS_PATH}")
_stage5_commands_module = importlib.util.module_from_spec(_STAGE5_COMMANDS_SPEC)
_STAGE5_COMMANDS_SPEC.loader.exec_module(_stage5_commands_module)

# Stage-4 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_STAGE4_COMMANDS_PATH = Path(__file__).with_name("_stage4_commands.py")
_STAGE4_COMMANDS_SPEC = importlib.util.spec_from_file_location(
    "_stage4_commands", _STAGE4_COMMANDS_PATH)
if _STAGE4_COMMANDS_SPEC is None or _STAGE4_COMMANDS_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage4_commands: {_STAGE4_COMMANDS_PATH}")
_stage4_commands_module = importlib.util.module_from_spec(_STAGE4_COMMANDS_SPEC)
_STAGE4_COMMANDS_SPEC.loader.exec_module(_stage4_commands_module)

# Migration helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_MIGRATE_COMMANDS_PATH = Path(__file__).with_name("_migrate_commands.py")
_MIGRATE_COMMANDS_SPEC = importlib.util.spec_from_file_location(
    "_migrate_commands", _MIGRATE_COMMANDS_PATH)
if _MIGRATE_COMMANDS_SPEC is None or _MIGRATE_COMMANDS_SPEC.loader is None:
    raise RuntimeError(f"cannot load _migrate_commands: {_MIGRATE_COMMANDS_PATH}")
_migrate_commands_module = importlib.util.module_from_spec(_MIGRATE_COMMANDS_SPEC)
_MIGRATE_COMMANDS_SPEC.loader.exec_module(_migrate_commands_module)

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


# Authoritative paper fields: two direction-local snapshots of the same paper
# must agree exactly on these during v1 normalization or the pack is ambiguous.
_CANONICAL_PAPER_FIELDS = ("title", "year", "authorship", "analysis_file",
                           "pdf_available", "facts_state", "facts_error",
                           "paper_facts")


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_contact_base = _contact_base_module.build(
    atomic_write=atomic_write,
    atomic_json=atomic_json,
    fail=fail,
    MANAGED_BY=MANAGED_BY,
    DIRECTION_IDENTITY_VERSION=DIRECTION_IDENTITY_VERSION,
    PROJECTIONS_FILE=PROJECTIONS_FILE,
    VERIFY_TIMESTAMP_FORMAT=VERIFY_TIMESTAMP_FORMAT
)

now_utc = _contact_base.now_utc
sha256_bytes = _contact_base.sha256_bytes
sha256_text = _contact_base.sha256_text
sha256_obj = _contact_base.sha256_obj
normalized_quote = _contact_base.normalized_quote
quote_id = _contact_base.quote_id
load_json = _contact_base.load_json
read_json_file = _contact_base.read_json_file
professor_dir_containment_error = _contact_base.professor_dir_containment_error
require_professor_dir_under_program = _contact_base.require_professor_dir_under_program
truncate = _contact_base.truncate
text_tokens = _contact_base.text_tokens
title_tokens = _contact_base.title_tokens
rel_path = _contact_base.rel_path
filename_component = _contact_base.filename_component
safe_result_file = _contact_base.safe_result_file
direction_machine_id = _contact_base.direction_machine_id
facts_direction_id = _contact_base.facts_direction_id
cross_group_id = _contact_base.cross_group_id
pack_paper_index = _contact_base.pack_paper_index
direction_papers = _contact_base.direction_papers
paper_digest = _contact_base.paper_digest
sidecar_sha = _contact_base.sidecar_sha
gap_fingerprint = _contact_base.gap_fingerprint
candidate_fingerprint = _contact_base.candidate_fingerprint
direction_relevant_keys = _contact_base.direction_relevant_keys
direction_provisional_member_keys = _contact_base.direction_provisional_member_keys
pack_direction_relevant_keys = _contact_base.pack_direction_relevant_keys
direction_candidate_keys = _contact_base.direction_candidate_keys
selected_candidate_union = _contact_base.selected_candidate_union
direction_fingerprint = _contact_base.direction_fingerprint
render_frontmatter = _contact_base.render_frontmatter
split_frontmatter = _contact_base.split_frontmatter
managed_conflict = _contact_base.managed_conflict
managed_write = _contact_base.managed_write
managed_write_raw = _contact_base.managed_write_raw
projection_conflict = _contact_base.projection_conflict
projection_write = _contact_base.projection_write
load_projections = _contact_base.load_projections
save_projections = _contact_base.save_projections
# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_contact_pack = _contact_pack_module.build(
    fail=fail,
    soft_exit=soft_exit,
    INPUT_PACK_SCHEMA=INPUT_PACK_SCHEMA,
    CANDIDATE_STATE_SCHEMA=CANDIDATE_STATE_SCHEMA,
    DIRECTION_IDENTITY_VERSION=DIRECTION_IDENTITY_VERSION,
    STAGE3_GENERATOR_CONTRACT_VERSION=STAGE3_GENERATOR_CONTRACT_VERSION,
    INPUT_PACK_KIND=INPUT_PACK_KIND,
    CANDIDATE_STATE_KIND=CANDIDATE_STATE_KIND,
    INPUT_PACK=INPUT_PACK,
    CANDIDATE_STATE=CANDIDATE_STATE,
    _CANONICAL_PAPER_FIELDS=_CANONICAL_PAPER_FIELDS,
    read_json_file=read_json_file,
    direction_machine_id=direction_machine_id,
    cross_group_id=cross_group_id
)

_canonical_paper_record = _contact_pack._canonical_paper_record
_merge_canonical_paper = _contact_pack._merge_canonical_paper
normalize_input_pack = _contact_pack.normalize_input_pack
load_input_pack = _contact_pack.load_input_pack
_migrate_v1_candidate = _contact_pack._migrate_v1_candidate
_slice_gap_directions = _contact_pack._slice_gap_directions
_migrate_v1_cross_group = _contact_pack._migrate_v1_cross_group
normalize_candidate_state = _contact_pack.normalize_candidate_state
load_candidate_state = _contact_pack.load_candidate_state
_strict_candidate_shape = _contact_pack._strict_candidate_shape
strict_candidate_state = _contact_pack.strict_candidate_state


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


STAGE3_IMMUTABLE_CANDIDATE_FIELDS = ("id", "kind", "direction_ids", "origin", "gap_refs",
                                     "anchor_type", "anchor_notes", "fit", "red_lines")
STAGE3_REPAIRABLE_CANDIDATE_FIELDS = ("title", "one_liner", "research_question", "points",
                                      "fit_note", "why_recommended", "tension_points")


# --- Issue #66 r13 §5: per-invocation credential production/consumption ----


STAGE3_INVOCATION_SOURCE_PARAMS = ("professor_dir", "program_root", "profile",
                                   "refresh_scope", "skip_direction_ids",
                                   "cross_direction_groups", "direction_id",
                                   "collection_key", "selection")


# --- Issue #66 r13 §6: validation handoff prepare/save/record ---------------


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage3_validation = _stage3_validation_module.build(
    atomic_json=atomic_json,
    emit=emit,
    fail=fail,
    soft_exit=soft_exit,
    STAGE3_VALIDATION_MAX_ROUNDS=STAGE3_VALIDATION_MAX_ROUNDS,
    scope_key=scope_key,
    _stage3_issue_scopes=_stage3_issue_scopes,
    _stage3_validation_files=_stage3_validation_files,
    _stage3_normalized_absolute_path=_stage3_normalized_absolute_path,
    _stage3_complete_write_result=_stage3_complete_write_result,
    _require_stage3_handoff_round=_require_stage3_handoff_round,
    _stage3_json_object_pairs=_stage3_json_object_pairs,
    _stage3_json_reject_constant=_stage3_json_reject_constant,
    _stage3_write_buffer=_stage3_write_buffer,
    stage3_render_line_scopes=stage3_render_line_scopes,
    INPUT_PACK=INPUT_PACK,
    CANDIDATE_STATE=CANDIDATE_STATE,
    CANDIDATES_MD=CANDIDATES_MD,
    now_utc=now_utc,
    sha256_bytes=sha256_bytes,
    sha256_text=sha256_text,
    require_professor_dir_under_program=require_professor_dir_under_program,
    split_frontmatter=split_frontmatter,
    load_input_pack=load_input_pack,
    load_candidate_state=load_candidate_state,
    profile_fingerprint=profile_fingerprint,
    STAGE3_INVOCATION_VERSION=STAGE3_INVOCATION_VERSION,
    STAGE3_INVOCATION_FILE=STAGE3_INVOCATION_FILE,
    STAGE3_HANDOFF_VERSION=STAGE3_HANDOFF_VERSION,
    STAGE3_HANDOFF_ROOT=STAGE3_HANDOFF_ROOT,
    STAGE3_HANDOFF_FILE=STAGE3_HANDOFF_FILE,
    STAGE3_VALIDATOR_OUTPUT_FILE=STAGE3_VALIDATOR_OUTPUT_FILE,
    STAGE3_VALIDATION_TARGET_FILE=STAGE3_VALIDATION_TARGET_FILE,
    STAGE3_IMMUTABLE_CANDIDATE_FIELDS=STAGE3_IMMUTABLE_CANDIDATE_FIELDS,
    STAGE3_REPAIRABLE_CANDIDATE_FIELDS=STAGE3_REPAIRABLE_CANDIDATE_FIELDS,
    STAGE3_INVOCATION_SOURCE_PARAMS=STAGE3_INVOCATION_SOURCE_PARAMS
)

_stage3_bound_render = _stage3_validation._stage3_bound_render
_stage3_candidates_entry = _stage3_validation._stage3_candidates_entry
stage3_validation_evidence = _stage3_validation.stage3_validation_evidence
stage3_correction_scopes = _stage3_validation.stage3_correction_scopes
stage3_repairable_correction_directions = _stage3_validation.stage3_repairable_correction_directions
carry_stage3_validator = _stage3_validation.carry_stage3_validator
stage3_current_result = _stage3_validation.stage3_current_result
_paper_refs = _stage3_validation._paper_refs
require_stage3_correction_invariants = _stage3_validation.require_stage3_correction_invariants
_write_stage3_invocation = _stage3_validation._write_stage3_invocation
_read_stage3_invocation = _stage3_validation._read_stage3_invocation
_require_invocation_source = _stage3_validation._require_invocation_source
_stage3_handoff_directory = _stage3_validation._stage3_handoff_directory
_load_stage3_handoff = _stage3_validation._load_stage3_handoff
cmd_stage3_prepare_validation = _stage3_validation.cmd_stage3_prepare_validation
cmd_stage3_write_validation = _stage3_validation.cmd_stage3_write_validation
cmd_stage3_save_validation = _stage3_validation.cmd_stage3_save_validation
cmd_stage3_record_validation = _stage3_validation.cmd_stage3_record_validation


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
# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage3_commands = _stage3_commands_module.build(
    atomic_write=atomic_write,
    staged_pair_commit=staged_pair_commit,
    emit=emit,
    fail=fail,
    soft_exit=soft_exit,
    _stage3_args_from_invocation=_stage3_args_from_invocation,
    MANAGED_BY=MANAGED_BY,
    CANDIDATE_STATE_SCHEMA=CANDIDATE_STATE_SCHEMA,
    DIRECTION_IDENTITY_VERSION=DIRECTION_IDENTITY_VERSION,
    STAGE3_GENERATOR_CONTRACT_VERSION=STAGE3_GENERATOR_CONTRACT_VERSION,
    CANDIDATE_STATE_KIND=CANDIDATE_STATE_KIND,
    INPUT_PACK=INPUT_PACK,
    CANDIDATE_STATE=CANDIDATE_STATE,
    CANDIDATES_MD=CANDIDATES_MD,
    CANDIDATES_OVERVIEW=CANDIDATES_OVERVIEW,
    SELECTION_FILE=SELECTION_FILE,
    REFRESH_SCOPES=REFRESH_SCOPES,
    QUOTE_INPUT_CHARS=QUOTE_INPUT_CHARS,
    TRANSLATION_INPUT_CHARS=TRANSLATION_INPUT_CHARS,
    now_utc=now_utc,
    sha256_text=sha256_text,
    sha256_obj=sha256_obj,
    read_json_file=read_json_file,
    require_professor_dir_under_program=require_professor_dir_under_program,
    truncate=truncate,
    rel_path=rel_path,
    safe_result_file=safe_result_file,
    direction_machine_id=direction_machine_id,
    direction_papers=direction_papers,
    render_frontmatter=render_frontmatter,
    split_frontmatter=split_frontmatter,
    managed_conflict=managed_conflict,
    load_input_pack=load_input_pack,
    load_candidate_state=load_candidate_state,
    strict_candidate_state=strict_candidate_state,
    profile_fingerprint=profile_fingerprint,
    load_profile_text=load_profile_text,
    _direction_slices=_direction_slices,
    _cross_group_fresh=_cross_group_fresh,
    _parse_direction_id_list=_parse_direction_id_list,
    _parse_cross_groups=_parse_cross_groups,
    STAGE3_INVOCATION_VERSION=STAGE3_INVOCATION_VERSION,
    stage3_validation_evidence=stage3_validation_evidence,
    stage3_correction_scopes=stage3_correction_scopes,
    stage3_repairable_correction_directions=stage3_repairable_correction_directions,
    carry_stage3_validator=carry_stage3_validator,
    stage3_current_result=stage3_current_result,
    require_stage3_correction_invariants=require_stage3_correction_invariants,
    _write_stage3_invocation=_write_stage3_invocation,
    _read_stage3_invocation=_read_stage3_invocation,
    _require_invocation_source=_require_invocation_source,
    validate_candidate_result=validate_candidate_result,
    validate_cross_result=validate_cross_result,
    render_candidates_md=render_candidates_md,
    render_candidates_overview=render_candidates_overview,
    canonical_professor_dir=canonical_professor_dir
)

_stage3_selected_scope_keys = _stage3_commands._stage3_selected_scope_keys
cmd_stage3_plan = _stage3_commands.cmd_stage3_plan
cmd_stage3_finalize = _stage3_commands.cmd_stage3_finalize
cmd_stage3_rebuild_overview = _stage3_commands.cmd_stage3_rebuild_overview


STAGE4_MIGRATION_COMMITTED = ("migrated", "already_local", "not_applicable")


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage4_commands = _stage4_commands_module.build(
    atomic_json_many=atomic_json_many,
    emit=emit,
    ProfessorBusinessFailure=ProfessorBusinessFailure,
    professor_business_channel=professor_business_channel,
    fail=fail,
    soft_exit=soft_exit,
    contact_evidence_snapshot=contact_evidence_snapshot,
    load_contact_evidence=load_contact_evidence,
    MANAGED_BY=MANAGED_BY,
    STAGE4_LOCAL_SCHEMA=STAGE4_LOCAL_SCHEMA,
    DIRECTION_IDENTITY_VERSION=DIRECTION_IDENTITY_VERSION,
    SELECTION_KIND=SELECTION_KIND,
    EMAIL_PACK_KIND=EMAIL_PACK_KIND,
    EMAIL_PACK=EMAIL_PACK,
    SELECTION_FILE=SELECTION_FILE,
    now_utc=now_utc,
    read_json_file=read_json_file,
    professor_dir_containment_error=professor_dir_containment_error,
    direction_machine_id=direction_machine_id,
    load_input_pack=load_input_pack,
    load_candidate_state=load_candidate_state,
    profile_fingerprint=profile_fingerprint,
    compile_email_entry=compile_email_entry,
    validate_papers_override=validate_papers_override,
    _selection_direction_ids=_selection_direction_ids,
    canonical_professor_dir=canonical_professor_dir,
    STAGE4_MIGRATION_COMMITTED=STAGE4_MIGRATION_COMMITTED
)

_stage4_cross_group = _stage4_commands._stage4_cross_group
validate_stage4_selections = _stage4_commands.validate_stage4_selections
stage4_local_pair_paths = _stage4_commands.stage4_local_pair_paths
stage4_professor_row = _stage4_commands.stage4_professor_row
_stage4_failure_row = _stage4_commands._stage4_failure_row
_stage4_professor_commit = _stage4_commands._stage4_professor_commit
stage4_professor_transaction = _stage4_commands.stage4_professor_transaction
cmd_stage4_finalize = _stage4_commands.cmd_stage4_finalize
_stage4_migration_result = _stage4_commands._stage4_migration_result
cmd_stage4_migrate_local = _stage4_commands.cmd_stage4_migrate_local


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


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage5_input = _stage5_input_module.build(
    emit=emit,
    fail=fail,
    soft_exit=soft_exit,
    STAGE4_LOCAL_SCHEMA=STAGE4_LOCAL_SCHEMA,
    EMAIL_PACK_KIND=EMAIL_PACK_KIND,
    EMAIL_PACK=EMAIL_PACK,
    sha256_text=sha256_text,
    read_json_file=read_json_file,
    professor_dir_containment_error=professor_dir_containment_error,
    require_professor_dir_under_program=require_professor_dir_under_program,
    filename_component=filename_component
)

stage5_output_peers = _stage5_input.stage5_output_peers
stage5_output_paths = _stage5_input.stage5_output_paths
stage5_output_id = _stage5_input.stage5_output_id
select_stage5_email = _stage5_input.select_stage5_email
stage5_mode = _stage5_input.stage5_mode
stage5_pack_owner = _stage5_input.stage5_pack_owner
stage5_local_pack = _stage5_input.stage5_local_pack
stage5_choices_rows = _stage5_input.stage5_choices_rows
stage5_choices_by_id = _stage5_input.stage5_choices_by_id
stage5_list_input_rows = _stage5_input.stage5_list_input_rows
cmd_stage5_list_inputs = _stage5_input.cmd_stage5_list_inputs
stage5_partition_pack_spec = _stage5_input.stage5_partition_pack_spec
cmd_stage5_partition_choices = _stage5_input.cmd_stage5_partition_choices


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
# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage5_commands = _stage5_commands_module.build(
    atomic_write=atomic_write,
    atomic_json=atomic_json,
    emit=emit,
    fail=fail,
    soft_exit=soft_exit,
    contact_evidence_decisions=contact_evidence_decisions,
    resolve_contact_evidence=resolve_contact_evidence,
    SCHEMA=SCHEMA,
    MANAGED_BY=MANAGED_BY,
    EMAIL_PACK=EMAIL_PACK,
    EMAIL_STATE=EMAIL_STATE,
    EMAIL_OVERVIEW=EMAIL_OVERVIEW,
    STAGE5_AUDIT_PROVENANCE=STAGE5_AUDIT_PROVENANCE,
    VERIFY_TIMESTAMP_FORMAT=VERIFY_TIMESTAMP_FORMAT,
    now_utc=now_utc,
    sha256_bytes=sha256_bytes,
    sha256_text=sha256_text,
    sha256_obj=sha256_obj,
    read_json_file=read_json_file,
    require_professor_dir_under_program=require_professor_dir_under_program,
    truncate=truncate,
    rel_path=rel_path,
    render_frontmatter=render_frontmatter,
    split_frontmatter=split_frontmatter,
    load_profile_text=load_profile_text,
    load_header_sources=load_header_sources,
    header_values=header_values,
    subject_line=subject_line,
    current_source_fingerprints=current_source_fingerprints,
    verify_state=verify_state,
    gap_job_block=gap_job_block,
    stage5_output_peers=stage5_output_peers,
    stage5_output_paths=stage5_output_paths,
    stage5_output_id=stage5_output_id,
    stage5_mode=stage5_mode,
    stage5_pack_owner=stage5_pack_owner,
    stage5_local_pack=stage5_local_pack,
    stage5_choices_by_id=stage5_choices_by_id,
    validate_email_raw=validate_email_raw,
    require_user_choices=require_user_choices,
    require_followup_choices=require_followup_choices,
    find_followup_template_path=find_followup_template_path,
    load_id_map=load_id_map,
    humanized_paths=humanized_paths,
    assemble_draft=assemble_draft,
    assemble_followup_draft=assemble_followup_draft,
    body_salutation_line=body_salutation_line,
    render_checklist_table=render_checklist_table,
    render_source_table=render_source_table,
    render_followup_source_table=render_followup_source_table,
    render_fact_check_card=render_fact_check_card
)

cmd_stage5_plan = _stage5_commands.cmd_stage5_plan
cmd_stage5_finalize = _stage5_commands.cmd_stage5_finalize
stage5_recipient_authority = _stage5_commands.stage5_recipient_authority
cmd_stage5_rebuild_overview = _stage5_commands.cmd_stage5_rebuild_overview
cmd_stage5_record_validation = _stage5_commands.cmd_stage5_record_validation


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


def read_legacy_index(index_path: Path) -> tuple[dict | None, str | None]:
    data, error = read_json_file(index_path)
    if error:
        return None, error
    if not isinstance(data, dict):
        return None, "not an object"
    return data, None


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


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_migrate_commands = _migrate_commands_module.build(
    atomic_json=atomic_json,
    emit=emit,
    fail=fail,
    SCHEMA=SCHEMA,
    MANAGED_BY=MANAGED_BY,
    INPUT_PACK=INPUT_PACK,
    CANDIDATES_MD=CANDIDATES_MD,
    GAP_STATUSES=GAP_STATUSES,
    now_utc=now_utc,
    sha256_bytes=sha256_bytes,
    sha256_obj=sha256_obj,
    read_json_file=read_json_file,
    load_sidecar=load_sidecar,
    read_legacy_index=read_legacy_index,
    classify_direction=classify_direction,
    apply_ready_entry=apply_ready_entry
)

migration_source_fingerprint = _migrate_commands.migration_source_fingerprint
migrate_entry_for_professor = _migrate_commands.migrate_entry_for_professor
cmd_migrate_plan = _migrate_commands.cmd_migrate_plan
cmd_migrate_apply = _migrate_commands.cmd_migrate_apply


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
