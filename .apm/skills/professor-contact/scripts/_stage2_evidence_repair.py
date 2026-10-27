#!/usr/bin/env python3
"""Stage-2 source-evidence repair helper for ``contact_state.py``.

The runner loads this helper by path next to itself and calls :func:`build`
once with its own helper functions and shared constants, exactly like the other
Stage-2 helpers.  The module never imports the runner, never adds itself to
``sys.path`` and never builds a second failure channel.

This is the narrow source-owner entry from execution plan EP2: it corrects the
*wording* of ``model_evidence``, ``completed_part`` and ``remaining_gap`` in the
professor-local freshness cache after a registered fixed-evidence finding.  It
never calls a model, never judges semantic equivalence (the source owner checks
that the fact keeps its meaning before calling it), never edits the managed
Markdown and never changes a candidate/status/confidence fact.
"""
from __future__ import annotations

import copy
import sys
import types
import uuid
from pathlib import Path

#: Schema of the repair batch document.
REPAIR_SCHEMA = 1

#: Exact freshness-cache fields this entry may correct.
REPAIR_FIELDS = ("model_evidence", "completed_part", "remaining_gap")

#: Rendered fixed-evidence field -> the cache field it authorizes.
#:
#: A rendered ``evidence`` on a shortlist card and a rendered
#: ``blacklist_evidence`` on a completed-gap card are the same cache field
#: ``model_evidence``; the other two keep their own identity.  A finding on one
#: rendered field never authorizes a different cache field.
DISPLAY_TO_CACHE = {
    "evidence": "model_evidence",
    "blacklist_evidence": "model_evidence",
    "completed_part": "completed_part",
    "remaining_gap": "remaining_gap",
}

#: Every key one repair row must carry as a string.
ROW_FIELDS = ("direction_id", "gap_id", "field", "expected_old_text",
              "replacement", "expected_validation_sha256",
              "expected_cache_sha256")


def build(*, fail, emit, read_json_file, atomic_json, sha256_obj,
          load_input_pack, stage2_validation_legality, stage2_bound_render,
          stage2_pack_content_fingerprint, lease_owner,
          INPUT_PACK, FRESHNESS_CACHE):
    """Bind the runner's helpers; return the command and its observation helpers."""

    def _load_batch(path) -> list[dict]:
        data, error = read_json_file(Path(path))
        if error is not None or not isinstance(data, dict):
            fail("invalid_repair_file",
                 f"repair input is unreadable or not a JSON object: {path}",
                 path=str(path))
        if data.get("schema") != REPAIR_SCHEMA:
            fail("invalid_repair_file",
                 f"repair input schema must be {REPAIR_SCHEMA}", path=str(path),
                 schema=data.get("schema"))
        repairs = data.get("repairs")
        if not isinstance(repairs, list):
            fail("invalid_repair_file",
                 "repair input must contain a repairs list", path=str(path))
        rows = []
        for index, raw in enumerate(repairs):
            if not isinstance(raw, dict):
                fail("invalid_repair_file",
                     f"repairs[{index}] is not an object", path=str(path))
            row = {}
            for key in ROW_FIELDS:
                value = raw.get(key)
                if not isinstance(value, str):
                    fail("invalid_repair_file",
                         f"repairs[{index}].{key} must be a string", path=str(path))
                row[key] = value
            if row["field"] not in REPAIR_FIELDS:
                fail("invalid_repair_field",
                     f"repairs[{index}].field is outside the wording whitelist",
                     field=row["field"], allowed=list(REPAIR_FIELDS))
            rows.append(row)
        return rows

    def _load_registered(pack: dict, professor_dir: Path) -> dict:
        validator, legality_error = stage2_validation_legality(pack)
        if legality_error is not None:
            fail("validation_evidence_not_recorded",
                 f"recorded Stage-2 validation state is malformed: {legality_error}")
        if not isinstance(validator, dict):
            fail("validation_evidence_not_recorded",
                 "a source evidence repair needs a recorded style-validator report "
                 "with fixed blocking rows")
        if validator.get("pack_sha256") != stage2_pack_content_fingerprint(pack):
            fail("validation_evidence_not_recorded",
                 "the recorded validation no longer binds the current input pack; "
                 "re-record a raw validator report against the current files")
        render_sha, _body = stage2_bound_render(professor_dir, pack)
        if render_sha != validator.get("render_sha256"):
            fail("validation_render_stale",
                 "the recorded validation no longer binds the current managed analysis; "
                 "re-record a raw validator report instead of repairing the cache")
        return validator

    def _registered_rows(validator: dict, direction_id: str, gap_id: str) -> list:
        fixed = validator.get("fixed_blocking")
        rows = fixed.get(direction_id) if isinstance(fixed, dict) else None
        if not isinstance(rows, list):
            return []
        return [row for row in rows
                if isinstance(row, dict) and row.get("gap_id") == gap_id]

    def _authorized(registered: list, field: str) -> bool:
        wanted = {display for display, cache in DISPLAY_TO_CACHE.items()
                  if cache == field}
        return any(row.get("owner") == "source" and row.get("field") in wanted
                   for row in registered)

    def _owner_names(registered: list) -> list:
        owners = []
        for row in registered:
            owner = row.get("owner")
            if isinstance(owner, str) and owner not in owners:
                owners.append(owner)
        return owners

    def _row_key(row: dict) -> tuple:
        return (row["direction_id"], row["gap_id"], row["field"])

    def _validate_rows(rows: list[dict], validator: dict, document: dict) -> None:
        """Validate the complete batch before any byte is written."""
        cache_digest = sha256_obj(document)
        validation_digest = validator.get("validation_sha256")
        entries = document.get("entries")
        if not isinstance(entries, dict):
            fail("missing_freshness_cache", "the freshness cache has no entries map")
        seen = set()
        for row in rows:
            key = _row_key(row)
            if key in seen:
                fail("duplicate_repair_row",
                     "the repair batch repeats one direction/gap/field row",
                     direction_id=row["direction_id"], gap_id=row["gap_id"],
                     field=row["field"])
            seen.add(key)
            if row["expected_cache_sha256"] != cache_digest:
                fail("stale_repair_input",
                     "the freshness cache changed since this repair input was prepared",
                     direction_id=row["direction_id"], gap_id=row["gap_id"],
                     field=row["field"])
            if row["expected_validation_sha256"] != validation_digest:
                fail("stale_repair_input",
                     "the recorded validation changed since this repair input was prepared",
                     direction_id=row["direction_id"], gap_id=row["gap_id"],
                     field=row["field"])
            registered = _registered_rows(validator, row["direction_id"],
                                          row["gap_id"])
            if not _authorized(registered, row["field"]):
                fail("repair_not_authorized",
                     "no registered source-owned fixed-evidence row authorizes this "
                     "cache field for the named direction and gap",
                     direction_id=row["direction_id"], gap_id=row["gap_id"],
                     field=row["field"], owners=_owner_names(registered))
            entry = entries.get(row["gap_id"])
            if not isinstance(entry, dict):
                fail("repair_gap_not_in_cache",
                     "the named gap has no corresponding freshness cache record",
                     direction_id=row["direction_id"], gap_id=row["gap_id"],
                     field=row["field"])
            current = entry.get(row["field"])
            if not isinstance(current, str) or current != row["expected_old_text"]:
                fail("stale_repair_input",
                     "the freshness cache field no longer carries the expected old text",
                     direction_id=row["direction_id"], gap_id=row["gap_id"],
                     field=row["field"])

    def _changed_rows(rows: list[dict]) -> list[dict]:
        return [row for row in rows
                if row["replacement"] != row["expected_old_text"]]

    def _affected(changed: list[dict]) -> list[dict]:
        return [{"direction_id": row["direction_id"], "gap_id": row["gap_id"],
                 "field": row["field"]} for row in changed]

    def _recheck_and_commit(professor_dir: Path, pack: dict, validator: dict,
                            document: dict, changed: list[dict]) -> None:
        """Re-prove the pack/cache binding, then replace only the whitelisted text."""
        latest_pack, pack_error = load_input_pack(professor_dir)
        if pack_error is not None or not isinstance(latest_pack, dict):
            fail("stale_repair_input",
                 "the accepted input pack became unreadable before the write",
                 pack_path=str(professor_dir / INPUT_PACK))
        latest_validator = latest_pack.get("validator")
        if (not isinstance(latest_validator, dict)
                or latest_validator.get("validation_sha256")
                != validator.get("validation_sha256")
                or stage2_pack_content_fingerprint(latest_pack)
                != stage2_pack_content_fingerprint(pack)):
            fail("stale_repair_input",
                 "the accepted input pack changed before the repair could be committed",
                 pack_path=str(professor_dir / INPUT_PACK))
        latest_document, cache_error = read_json_file(professor_dir / FRESHNESS_CACHE)
        if (cache_error is not None or not isinstance(latest_document, dict)
                or sha256_obj(latest_document) != sha256_obj(document)):
            fail("stale_repair_input",
                 "the freshness cache changed before the repair could be committed",
                 cache_path=str(professor_dir / FRESHNESS_CACHE))
        updated = copy.deepcopy(latest_document)
        entries = updated.get("entries")
        for row in changed:
            entry = entries.get(row["gap_id"]) if isinstance(entries, dict) else None
            if (not isinstance(entry, dict)
                    or entry.get(row["field"]) != row["expected_old_text"]):
                fail("stale_repair_input",
                     "the freshness cache field changed before the repair could be "
                     "committed", direction_id=row["direction_id"],
                     gap_id=row["gap_id"], field=row["field"])
            entry[row["field"]] = row["replacement"]
        try:
            atomic_json(professor_dir / FRESHNESS_CACHE, updated)
        except OSError as error:
            fail("stage2_repair_write_failed",
                 f"the freshness cache could not be replaced: {error}",
                 cache_path=str(professor_dir / FRESHNESS_CACHE))

    def cmd_stage2_repair_evidence(args) -> None:
        professor_dir = Path(args.professor_dir)
        rows = _load_batch(args.repair_file)
        pack, error = load_input_pack(professor_dir)
        if error is not None or not isinstance(pack, dict):
            fail("missing_input_pack",
                 f"input pack unreadable: {professor_dir / INPUT_PACK}")
        validator = _load_registered(pack, professor_dir)
        document, cache_error = read_json_file(professor_dir / FRESHNESS_CACHE)
        if (cache_error is not None or not isinstance(document, dict)
                or not isinstance(document.get("entries"), dict)):
            fail("missing_freshness_cache",
                 f"freshness cache is unreadable or malformed: "
                 f"{professor_dir / FRESHNESS_CACHE}")
        _validate_rows(rows, validator, document)
        changed = _changed_rows(rows)
        if not changed:
            # An unchanged replacement is not a new source version: no writer
            # lease, no cache write and no reset of recorded validation rounds.
            emit({"status": "ok", "changed": False, "affected": [],
                  "professor_dir": str(professor_dir),
                  "cache_path": str(professor_dir / FRESHNESS_CACHE)})
            return
        acquire_local_lease, release_local_lease = lease_owner()
        token = uuid.uuid4().hex
        released = False
        release_error = None
        try:
            try:
                acquire_local_lease(professor_dir, token, verify_plan=False)
            except ValueError as error:
                if str(error) == "stage2_writer_busy":
                    fail("stage2_writer_busy",
                         "another Stage-2 local writer holds this professor's writer "
                         "lease; no source text was changed")
                fail("invalid_params",
                     f"cannot acquire the professor writer lease: {error}")
            _recheck_and_commit(professor_dir, pack, validator, document, changed)
        finally:
            try:
                release_local_lease(professor_dir, token)
                released = True
            except (ValueError, OSError) as error:
                release_error = f"{type(error).__name__}: {error}"
                print(f"stage2-repair-evidence: lease release failed: {release_error}",
                      file=sys.stderr)
        payload = {
            "status": "needs_refresh",
            "reason_code": "source_evidence_changed",
            "changed": True,
            "affected": _affected(changed),
            "professor_dir": str(professor_dir),
            "cache_path": str(professor_dir / FRESHNESS_CACHE),
            "lease_released": released,
        }
        if release_error:
            payload["lease_release_error"] = release_error
        emit(payload)

    return types.SimpleNamespace(cmd_stage2_repair_evidence=cmd_stage2_repair_evidence)
