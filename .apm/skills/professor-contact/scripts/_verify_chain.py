#!/usr/bin/env python3
"""Verify-cache helper module for ``contact_state.py``.

The runner loads this helper by path next to itself and calls :func:`build`
once with its own helper functions and shared constants. The factory binds
those names in an enclosing scope, so the functions below keep the exact
bodies they had inside the runner (only their indentation changed). The
module never imports the runner, never adds itself to ``sys.path`` and
never builds a second failure channel.
"""
from __future__ import annotations

import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any





def build(*, read_json_file,
          VERIFY_TTL_DAYS,
          VERIFY_TIMESTAMP_FORMAT,
          VERIFY_FILE,
          email_item_is_evidence_seeded,
          current_source_fingerprints):
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

    return types.SimpleNamespace(
                _fingerprint_failure_kind=_fingerprint_failure_kind,
                _verify_diagnostic_failure=_verify_diagnostic_failure,
                verify_state=verify_state,
    )
