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

# Stage-5 email helper module: loaded by path next to this runner (the runner may
# be executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_STAGE5_EMAIL_PATH = Path(__file__).with_name("_stage5_email.py")
_STAGE5_EMAIL_SPEC = importlib.util.spec_from_file_location(
    "_stage5_email", _STAGE5_EMAIL_PATH)
if _STAGE5_EMAIL_SPEC is None or _STAGE5_EMAIL_SPEC.loader is None:
    raise RuntimeError(f"cannot load _stage5_email: {_STAGE5_EMAIL_PATH}")
_stage5_email_module = importlib.util.module_from_spec(_STAGE5_EMAIL_SPEC)
_STAGE5_EMAIL_SPEC.loader.exec_module(_stage5_email_module)

# Stage-2 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_CANDIDATE_VALIDATE_PATH = Path(__file__).with_name("_candidate_validate.py")
_CANDIDATE_VALIDATE_SPEC = importlib.util.spec_from_file_location(
    "_candidate_validate", _CANDIDATE_VALIDATE_PATH)
if _CANDIDATE_VALIDATE_SPEC is None or _CANDIDATE_VALIDATE_SPEC.loader is None:
    raise RuntimeError(f"cannot load _candidate_validate: {_CANDIDATE_VALIDATE_PATH}")
_candidate_validate_module = importlib.util.module_from_spec(_CANDIDATE_VALIDATE_SPEC)
_CANDIDATE_VALIDATE_SPEC.loader.exec_module(_candidate_validate_module)

# Email core helper module: loaded by path next to this runner (the runner may
# be executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_EMAIL_CORE_PATH = Path(__file__).with_name("_email_core.py")
_EMAIL_CORE_SPEC = importlib.util.spec_from_file_location(
    "_email_core", _EMAIL_CORE_PATH)
if _EMAIL_CORE_SPEC is None or _EMAIL_CORE_SPEC.loader is None:
    raise RuntimeError(f"cannot load _email_core: {_EMAIL_CORE_PATH}")
_email_core_module = importlib.util.module_from_spec(_EMAIL_CORE_SPEC)
_EMAIL_CORE_SPEC.loader.exec_module(_email_core_module)

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


# Stage-2 helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_DIRECTION_INPUTS_PATH = Path(__file__).with_name("_direction_inputs.py")
_DIRECTION_INPUTS_SPEC = importlib.util.spec_from_file_location(
    "_direction_inputs", _DIRECTION_INPUTS_PATH)
if _DIRECTION_INPUTS_SPEC is None or _DIRECTION_INPUTS_SPEC.loader is None:
    raise RuntimeError(f"cannot load _direction_inputs: {_DIRECTION_INPUTS_PATH}")
_direction_inputs_module = importlib.util.module_from_spec(_DIRECTION_INPUTS_SPEC)
_DIRECTION_INPUTS_SPEC.loader.exec_module(_direction_inputs_module)

# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_direction_inputs = _direction_inputs_module.build(
    fail=fail,
    sha256_bytes=sha256_bytes,
    truncate=truncate,
    PROFILE_INPUT_CHARS=PROFILE_INPUT_CHARS,
    direction_machine_id=direction_machine_id,
    direction_papers=direction_papers,
    cross_group_id=cross_group_id
)

profile_fingerprint = _direction_inputs.profile_fingerprint
load_profile_text = _direction_inputs.load_profile_text
_direction_slices = _direction_inputs._direction_slices
_cross_group_fresh = _direction_inputs._cross_group_fresh
_parse_direction_id_list = _direction_inputs._parse_direction_id_list
_parse_cross_groups = _direction_inputs._parse_cross_groups


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_candidate_validate = _candidate_validate_module.build(
    ANCHORABLE=ANCHORABLE,
    fail=fail,
    _direction_slices=_direction_slices,
    direction_machine_id=direction_machine_id,
    _stage3_render=_stage3_render,
    now_utc=now_utc,
    CANDIDATES_MD=CANDIDATES_MD
)

_validate_candidate_core = _candidate_validate._validate_candidate_core
validate_candidate_result = _candidate_validate.validate_candidate_result
validate_cross_result = _candidate_validate.validate_cross_result
render_candidates_md = _candidate_validate.render_candidates_md
render_candidates_overview = _candidate_validate.render_candidates_overview


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


# Stage-3 Markdown rendering lives in the sibling helper ``_stage3_render.py``
# (loaded by path above). These names keep the pre-split module-level API: the
# two public renderers stay same-named and same-signature, and the private
# helpers stay reachable for callers and tests that already used them.
_red_line_key = _stage3_render._red_line_key
_candidate_red_lines = _stage3_render._candidate_red_lines
_render_idea_block = _stage3_render._render_idea_block
_stage3_scope_marker = _stage3_render._stage3_scope_marker


EMAIL_SOURCE_HASH_FIELDS = (
    "email_id", "direction_ids", "directions", "idea", "papers", "gaps",
    "red_lines", "allowed_sources", "contact_evidence", "cross_direction",
)


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_email_core = _email_core_module.build(
    fail=fail,
    direction_machine_id=direction_machine_id,
    direction_papers=direction_papers,
    EMAIL_SOURCE_HASH_FIELDS=EMAIL_SOURCE_HASH_FIELDS,
    sha256_obj=sha256_obj
)

compile_email_entry = _email_core.compile_email_entry
validate_papers_override = _email_core.validate_papers_override
_selection_direction_ids = _email_core._selection_direction_ids
email_source_hash = _email_core.email_source_hash


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


# Verify-chain helper module: loaded by path next to this runner (the runner may be
# executed directly or imported by path, so the scripts directory is not
# guaranteed to be on sys.path). The factory call further down binds it to this
# runner's own helpers; the aliases below the call keep every pre-split entry.
_VERIFY_CHAIN_PATH = Path(__file__).with_name("_verify_chain.py")
_VERIFY_CHAIN_SPEC = importlib.util.spec_from_file_location(
    "_verify_chain", _VERIFY_CHAIN_PATH)
if _VERIFY_CHAIN_SPEC is None or _VERIFY_CHAIN_SPEC.loader is None:
    raise RuntimeError(f"cannot load _verify_chain: {_VERIFY_CHAIN_PATH}")
_verify_chain_module = importlib.util.module_from_spec(_VERIFY_CHAIN_SPEC)
_VERIFY_CHAIN_SPEC.loader.exec_module(_verify_chain_module)


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


# Issue #43 freezes the caller-facing choices contract, but does not redefine
# pre-existing runner-internal compatibility fields. Keep renderer defaults
# here; public caller declarations are owned by the Stage-5 docs/projections.
DEFAULT_ALMA_MATER = "総合大学"
# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_stage5_email = _stage5_email_module.build(
    read_json_file=read_json_file,
    BATCH_RE=BATCH_RE,
    CLOSING_RE=CLOSING_RE,
    INTEREST_HARD_CAP=INTEREST_HARD_CAP,
    INTEREST_SOFT_CAP=INTEREST_SOFT_CAP,
    fail=fail,
    stage5_mode=stage5_mode,
    stage5_output_id=stage5_output_id,
    DEFAULT_ALMA_MATER=DEFAULT_ALMA_MATER,
    EMAIL_PACK=EMAIL_PACK,
    now_utc=now_utc,
    rel_path=rel_path
)

find_boshu_analysis = _stage5_email.find_boshu_analysis
load_header_sources = _stage5_email.load_header_sources
header_values = _stage5_email.header_values
subject_line = _stage5_email.subject_line
compact_name = _stage5_email.compact_name
email_item_is_evidence_seeded = _stage5_email.email_item_is_evidence_seeded
current_source_fingerprints = _stage5_email.current_source_fingerprints
validate_email_raw = _stage5_email.validate_email_raw
require_user_choices = _stage5_email.require_user_choices
require_followup_choices = _stage5_email.require_followup_choices
find_followup_template_path = _stage5_email.find_followup_template_path
load_id_map = _stage5_email.load_id_map
humanized_paths = _stage5_email.humanized_paths
email_template_body = _stage5_email.email_template_body
assemble_draft = _stage5_email.assemble_draft
body_salutation_line = _stage5_email.body_salutation_line
render_checklist_table = _stage5_email.render_checklist_table
cell_source = _stage5_email.cell_source
render_source_table = _stage5_email.render_source_table
render_followup_source_table = _stage5_email.render_followup_source_table
render_fact_check_card = _stage5_email.render_fact_check_card


# Binding point: every helper the module needs is defined by now; the factory
# receives this runner's own function objects and constants (no second channel).
_verify_chain = _verify_chain_module.build(
    read_json_file=read_json_file,
    VERIFY_TTL_DAYS=VERIFY_TTL_DAYS,
    VERIFY_TIMESTAMP_FORMAT=VERIFY_TIMESTAMP_FORMAT,
    VERIFY_FILE=VERIFY_FILE,
    email_item_is_evidence_seeded=email_item_is_evidence_seeded,
    current_source_fingerprints=current_source_fingerprints
)

_fingerprint_failure_kind = _verify_chain._fingerprint_failure_kind
_verify_diagnostic_failure = _verify_chain._verify_diagnostic_failure
verify_state = _verify_chain.verify_state


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
