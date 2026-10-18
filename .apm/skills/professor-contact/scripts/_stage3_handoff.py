#!/usr/bin/env python3
"""Stage-3 validator-handoff primitives for ``contact_state.py``.

The runner loads this helper by path next to itself and keeps the pre-split
module-level entry points (aliases, plus one same-signature wrapper for
``stage3_render_line_scopes``). The shared failure channel is **injected**: the
functions that can fail take it as an explicit keyword-only ``fail`` argument,
so this module never imports the runner and never builds a second channel
instance (which would fork the business-failure state).
"""
from __future__ import annotations

import json
import os
import types
from pathlib import Path
from typing import Any


CANDIDATE_META_PREFIX = "<!-- candidate_meta: "
STAGE3_SCOPE_PREFIX = "<!-- stage3_scope: "
STAGE3_VALIDATION_MAX_ROUNDS = 2

def _stage3_marker_payload(text: str, prefix: str, *, fail) -> dict:
    try:
        payload = json.loads(text[len(prefix):].removesuffix("-->").strip())
    except json.JSONDecodeError as exc:
        fail("validation_render_unparsable", f"{prefix!r} marker is not JSON: {exc}")
    return payload if isinstance(payload, dict) else {}

def stage3_render_line_scopes(md_text: str, *, fail) -> list:
    """Per-line machine scope of the runner-rendered candidate document.

    Section markers come from the renderer itself and every idea block carries
    its canonical ``direction_ids``/``group_id`` in ``candidate_meta``, so a
    rendered line is addressable without reading professor names or positions.
    ``None`` means the line sits outside any direction or group section.
    """
    scopes: list = []
    section = None
    block = None
    heading_line = None
    for index, raw in enumerate(md_text.splitlines(), start=1):
        text = raw.strip()
        if text.startswith("## "):
            section, block, heading_line = None, None, None
            scopes.append(section)
            continue
        if text.startswith("### "):
            block, heading_line = None, index
            scopes.append(section)
            continue
        if text.startswith(STAGE3_SCOPE_PREFIX):
            section, block = _stage3_marker_payload(text, STAGE3_SCOPE_PREFIX, fail=fail), None
            heading_line = None
            scopes.append(section)
            continue
        if text.startswith(CANDIDATE_META_PREFIX):
            meta = _stage3_marker_payload(text, CANDIDATE_META_PREFIX, fail=fail)
            ids = [x for x in (meta.get("direction_ids") or []) if isinstance(x, str) and x]
            if meta.get("group_id"):
                block = {"kind": "group", "group_id": meta["group_id"]}
            elif len(ids) == 1:
                block = {"kind": "direction", "direction_id": ids[0]}
            else:
                block = {"kind": "global"}
            block["candidate_id"] = meta.get("id")
            if heading_line and index - heading_line <= 4:
                for back in range(heading_line, index):
                    scopes[back - 1] = block
            heading_line = None
            scopes.append(block)
            continue
        scopes.append(block if block is not None else section)
    return scopes

def scope_key(scope: dict) -> str:
    """Canonical machine identity of a rendered scope: direction_id or group_id."""
    if not isinstance(scope, dict):
        return "global"
    if scope.get("kind") == "direction" and scope.get("direction_id"):
        return f"direction:{scope['direction_id']}"
    if scope.get("kind") == "group" and scope.get("group_id"):
        return f"group:{scope['group_id']}"
    return "global"

def _stage3_issue_scopes(issue: dict, body: str, scopes: list, path: Path, *,
                         fail) -> list:
    quote = issue.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        fail("invalid_validation_json",
             f"{path}: every Stage-3 validation issue needs the verbatim rendered quote")
    needle = quote.strip()
    hits = [index for index, line in enumerate(body.splitlines()) if needle in line]
    if not hits:
        fail("validation_quote_not_in_render",
             f"{path}: validator quote {needle[:20]!r} is not part of the bound render")
    found = []
    for line in hits:
        scope = scopes[line] or {"kind": "global"}
        if scope_key(scope) not in [scope_key(item) for item in found]:
            found.append(scope)
    return found

def _stage3_validation_files(data: Any, path: Path, *, fail) -> list:
    """Return the raw Stage-3 validator file entries after the shared envelope check."""
    if not isinstance(data, dict) or data.get("result") != "ok" \
            or not isinstance(data.get("files"), list):
        fail("invalid_validation_json", f"style-validator output unreadable: {path}")
    return data["files"]

def _stage3_normalized_absolute_path(value: Any, label: str, *, fail) -> str:
    if not isinstance(value, str) or not value:
        fail("invalid_validation_json", f"{label} must be a non-empty absolute path")
    candidate = Path(value)
    if not candidate.is_absolute():
        fail("invalid_validation_json", f"{label} must be an absolute path: {value!r}")
    try:
        return str(candidate.resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        fail("invalid_validation_json", f"{label} cannot be normalized: {value!r}")

def _stage3_complete_write_result(data: Any, path: Path, *,
                                  fail) -> list[tuple[str, dict]]:
    """Validate the complete Stage-3 validator protocol without reading its files."""
    files = _stage3_validation_files(data, path, fail=fail)
    if not files:
        fail("invalid_validation_json", "style-validator files must be a non-empty list")
    if not isinstance(data.get("notes"), str):
        fail("invalid_validation_json", "style-validator notes must be a string")

    normalized_entries: list[tuple[str, dict]] = []
    candidate_paths: set[str] = set()
    for index, entry in enumerate(files):
        label = f"style-validator files[{index}]"
        if not isinstance(entry, dict):
            fail("invalid_validation_json", f"{label} must be an object")
        candidate_path = _stage3_normalized_absolute_path(entry.get("file"), f"{label}.file", fail=fail)
        artifact = entry.get("artifact")
        if artifact not in ("analysis", "candidates"):
            fail("invalid_validation_json", f"{label}.artifact must be analysis|candidates")
        verdict = entry.get("verdict")
        if verdict not in ("pass", "pass_with_minor", "fail"):
            fail("invalid_validation_json", f"{label}.verdict is invalid: {verdict!r}")
        blocking_count = entry.get("blocking")
        minor_count = entry.get("minor")
        if isinstance(blocking_count, bool) or not isinstance(blocking_count, int) \
                or blocking_count < 0 or isinstance(minor_count, bool) \
                or not isinstance(minor_count, int) or minor_count < 0:
            fail("invalid_validation_json", f"{label} blocking/minor counts must be non-negative integers")
        issues = entry.get("issues")
        if not isinstance(issues, list):
            fail("invalid_validation_json", f"{label}.issues must be a list")
        blocking_issues = 0
        minor_issues = 0
        for issue_index, issue in enumerate(issues):
            issue_label = f"{label}.issues[{issue_index}]"
            if not isinstance(issue, dict):
                fail("invalid_validation_json", f"{issue_label} must be an object")
            for field in ("rule", "severity", "quote", "suggestion"):
                value = issue.get(field)
                if not isinstance(value, str) or not value.strip():
                    fail("invalid_validation_json", f"{issue_label}.{field} must be a non-empty string")
            location = issue.get("location")
            if isinstance(location, bool) or not (
                    (isinstance(location, int) and location > 0)
                    or (isinstance(location, str) and location.strip() and len(location) <= 20)):
                fail("invalid_validation_json",
                     f"{issue_label}.location must be a positive line number or a non-empty string of at most 20 characters")
            if len(issue["quote"]) > 40:
                fail("invalid_validation_json", f"{issue_label}.quote must be at most 40 characters")
            if issue["severity"] == "blocking":
                blocking_issues += 1
            elif issue["severity"] == "minor":
                minor_issues += 1
            else:
                fail("invalid_validation_json", f"{issue_label}.severity must be blocking|minor")
        if (blocking_count, minor_count) != (blocking_issues, minor_issues):
            fail("invalid_validation_json", f"{label} counts do not match its issues")
        if blocking_issues:
            if verdict != "fail":
                fail("invalid_validation_json", f"{label} blocking issues require verdict=fail")
        elif verdict == "fail":
            fail("invalid_validation_json", f"{label} fail verdict needs a blocking issue")
        elif minor_issues and verdict != "pass_with_minor":
            fail("invalid_validation_json", f"{label} minor issues require verdict=pass_with_minor")
        elif not minor_issues and verdict != "pass":
            fail("invalid_validation_json", f"{label} without issues must have verdict=pass")
        if artifact == "candidates":
            if candidate_path in candidate_paths:
                fail("invalid_validation_json", f"duplicate candidates path: {candidate_path}")
            candidate_paths.add(candidate_path)
        normalized_entries.append((candidate_path, entry))
    if not candidate_paths:
        fail("invalid_validation_json", "style-validator output needs a candidates entry")
    return normalized_entries

def _stage3_args_from_invocation(args, invocation: dict, correction: bool):
    """Rebuild this call's parsed parameters from one verified credential.

    Plain generation replays the recorded first-round controls exactly as they
    were parsed ("未传入" stays absent).  A credential correction keeps those
    controls as records only: no re-applied skip, no replayed group request,
    no first-round direction limit — the work set comes from the recorded
    validation round (r13 §5.4).
    """
    overrides = {
        "professor_dir": invocation["professor_dir"],
        "program_root": invocation["program_root"],
        "profile": invocation.get("profile_path"),
        "refresh_scope": invocation.get("refresh_scope"),
        "selection": invocation.get("selection"),
    }
    if correction:
        overrides.update({
            "direction_id": None,
            "collection_key": None,
            "skip_direction_ids": None,
            "cross_direction_groups": None,
        })
    else:
        overrides.update({
            "direction_id": invocation.get("direction_id"),
            "collection_key": invocation.get("collection_key"),
            "skip_direction_ids": invocation.get("skip_direction_ids_argument"),
            "cross_direction_groups": invocation.get("cross_direction_groups_argument"),
        })
    return types.SimpleNamespace(**{**vars(args), **overrides})

def _require_stage3_handoff_round(state: dict, render_sha: str,
                                   requested_round: int, *, fail) -> None:
    """The requested validation round must match the committed record facts.

    r13 §6.1: the round decision reuses the record entry's own facts — the
    committed ``validator`` block — never the emptiness of a temporary
    directory.  A caller cannot reopen round 1 over a recorded round, cannot
    start round 2 without a previous round whose open findings were corrected
    and committed under the existing correction constraints, and cannot pass
    ``round=2`` to bypass an owed correction.
    """
    validator = state.get("validator") if isinstance(state.get("validator"), dict) else {}
    raw_round = validator.get("round")
    if isinstance(raw_round, bool) or not isinstance(raw_round, int):
        raw_round = 0
    pending = validator.get("pending") if isinstance(validator.get("pending"), dict) else {}
    if requested_round == 1:
        if raw_round >= 1:
            fail("validation_round_already_recorded",
                 f"this professor already has a recorded Stage-3 validator round "
                 f"{raw_round}; a first validation round cannot be prepared again")
        return
    if raw_round == 0:
        fail("validation_round_sequence_invalid",
             "round 2 needs a recorded previous round whose findings were corrected")
    if raw_round >= STAGE3_VALIDATION_MAX_ROUNDS:
        fail("validation_rounds_exhausted",
             f"Stage-3 style validation is bounded to {STAGE3_VALIDATION_MAX_ROUNDS} rounds; "
             "the terminal record already exists")
    if validator.get("raw_verdict") != "fail":
        fail("validation_rounds_exhausted",
             "the previous validator round recorded no correction: the terminal "
             "record already exists")
    if pending:
        fail("validation_correction_required",
             "complete the recorded Stage-3 correction with stage3-plan/finalize "
             "--validation-file before preparing round 2")
    if validator.get("render_sha256") != render_sha:
        fail("validation_round_sequence_invalid",
             "the committed correction round does not carry the current render")

def _stage3_json_object_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def _stage3_json_reject_constant(value: str):
    raise ValueError(f"non-finite JSON number: {value}")

def _stage3_created_file_identity(fd: int) -> tuple[int, int]:
    info = os.fstat(fd)
    return info.st_dev, info.st_ino

def _stage3_cleanup_incomplete_write(path: Path, identity: tuple[int, int] | None) -> None:
    if identity is None:
        return
    try:
        info = os.lstat(path)
        if (info.st_dev, info.st_ino) == identity:
            os.unlink(path)
    except OSError:
        pass

def _stage3_write_buffer(path: Path, data: bytes) -> None:
    """Exclusively write and verify one buffer through the creating descriptor."""
    descriptor = None
    identity = None
    try:
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        identity = _stage3_created_file_identity(descriptor)
        os.fchmod(descriptor, 0o600)
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise OSError("write returned no bytes")
            offset += written
        os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        actual = bytearray()
        while len(actual) < len(data) + 1:
            chunk = os.read(descriptor, min(65536, len(data) + 1 - len(actual)))
            if not chunk:
                break
            actual.extend(chunk)
        if bytes(actual) != data:
            raise OSError("read-back bytes differ from the written buffer")
        os.close(descriptor)
        descriptor = None
    except Exception:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        _stage3_cleanup_incomplete_write(path, identity)
        raise
