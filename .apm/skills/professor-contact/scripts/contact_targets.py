#!/usr/bin/env python3
"""Deterministic per-professor target-state helper for professor-contact Stage 0-2.

One professor owns exactly one authoritative Stage-0 file:
``<professor_dir>/套磁目标.json`` (schema 2, one target object, no ``targets[]``).
``select`` only revises that professor's existing file and ``resolve`` only reads
the file its caller names; neither touches the retired program-level table, and a
missing local file is a ``bootstrap_required`` result with zero writes.
``bootstrap`` is the sole path that establishes a professor's first local target
and the only runtime reader of ``教授研究/套磁目标.json``; ``migrate`` reuses the
same per-professor classification and commit helpers. Never opens Zotero, starts
models, or performs network I/O.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 2
KIND = "professor-contact-target"
RESEARCH_DIR = Path("教授研究")
TARGET_FILE_NAME = "套磁目标.json"
# Legacy program-level table: migration input only, never read by select/resolve.
LEGACY_TARGET_FILE = RESEARCH_DIR / TARGET_FILE_NAME
PREVIEW_NAME = "方向预筛.json"
VALID_CONFIDENCE = {"high", "low"}
LEGACY_SCHEMA_VERSION = 1
LEGACY_KIND = "professor-contact-targets"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1))


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=1)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _require_nonempty(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _relative_under(path: Path, root: Path, field: str) -> str:
    resolved = path.resolve()
    allowed = (root.resolve() / RESEARCH_DIR).resolve()
    try:
        rel = resolved.relative_to(allowed)
    except ValueError as exc:
        raise ValueError(f"{field} must be under {allowed}") from exc
    return str(RESEARCH_DIR / rel)


def local_target_path(professor_dir: Path) -> Path:
    """Authoritative Stage-0 file of the professor owning ``professor_dir``."""
    return professor_dir / TARGET_FILE_NAME


def validate_preview(preview_path: Path) -> dict[str, Any]:
    preview_path = preview_path.resolve()
    if preview_path.name != PREVIEW_NAME:
        raise ValueError(f"preview file must be named {PREVIEW_NAME}")
    preview = load_json(preview_path)
    if not isinstance(preview, dict):
        raise ValueError("preview root must be an object")

    professor = _require_nonempty(preview.get("professor"), "professor")
    fingerprint = _require_nonempty(preview.get("preview_fingerprint"), "preview_fingerprint")
    fingerprint_version = _require_nonempty(
        preview.get("preview_fingerprint_version"), "preview_fingerprint_version"
    )
    _require_nonempty(preview.get("direction_id_version"), "direction_id_version")
    membership_mode = _require_nonempty(preview.get("membership_mode"), "membership_mode")
    if membership_mode != "overlap_allowed":
        raise ValueError("preview membership_mode must be overlap_allowed")

    directions = preview.get("directions")
    if not isinstance(directions, list) or not directions:
        raise ValueError("preview directions must be a non-empty array")

    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw in directions:
        if not isinstance(raw, dict):
            raise ValueError("preview direction must be an object")
        direction = deepcopy(raw)
        direction_id = _require_nonempty(direction.get("direction_id"), "direction_id")
        if direction_id in seen_ids:
            raise ValueError(f"duplicate direction_id: {direction_id}")
        seen_ids.add(direction_id)
        _require_nonempty(direction.get("member_fingerprint"), f"{direction_id}.member_fingerprint")
        for field in ("name_ja", "name_zh", "summary_zh"):
            if not isinstance(direction.get(field), str):
                raise ValueError(f"{direction_id}.{field} must be a string")

        members = direction.get("members")
        if not isinstance(members, list) or not members:
            raise ValueError(f"{direction_id}.members must be a non-empty array")
        member_keys: set[str] = set()
        normalized_members = []
        for member in members:
            if not isinstance(member, dict):
                raise ValueError(f"{direction_id}.members entries must be objects")
            item_key = _require_nonempty(member.get("item_key"), f"{direction_id}.member.item_key")
            confidence = _require_nonempty(
                member.get("preview_confidence"), f"{direction_id}.{item_key}.preview_confidence"
            )
            if confidence not in VALID_CONFIDENCE:
                raise ValueError(f"{direction_id}.{item_key}: invalid preview_confidence")
            if item_key in member_keys:
                raise ValueError(f"{direction_id}: duplicate member {item_key}")
            member_keys.add(item_key)
            normalized_members.append({"item_key": item_key, "preview_confidence": confidence})

        representatives = direction.get("representatives")
        if not isinstance(representatives, list):
            raise ValueError(f"{direction_id}.representatives must be an array")
        for rep in representatives:
            if not isinstance(rep, dict):
                raise ValueError(f"{direction_id}.representatives entries must be objects")
            rep_key = _require_nonempty(rep.get("item_key"), f"{direction_id}.representative.item_key")
            if rep_key not in member_keys:
                raise ValueError(f"{direction_id}: representative {rep_key} is not a member")

        direction["members"] = normalized_members
        normalized.append(direction)

    out = deepcopy(preview)
    out["professor"] = professor
    out["preview_fingerprint"] = fingerprint
    out["preview_fingerprint_version"] = fingerprint_version
    out["directions"] = normalized
    return out


def preview_options(preview_path: Path) -> dict[str, Any]:
    preview = validate_preview(preview_path)
    global_warnings: list[str] = []
    confidence = str(preview.get("data_confidence") or "").strip().lower()
    coverage = preview.get("coverage")
    if confidence in {"medium", "low"}:
        global_warnings.append(f"preview data confidence is {confidence}")
    if isinstance(coverage, (int, float)) and coverage < 0.6:
        global_warnings.append(f"abstract coverage is {coverage:.1%}")
    membership_coverage = preview.get("membership_coverage")
    if isinstance(membership_coverage, dict):
        unassigned = int(membership_coverage.get("unassigned_mountable_count") or 0)
        if unassigned:
            global_warnings.append(f"{unassigned} mountable papers are unassigned")

    options = []
    for direction in preview["directions"]:
        warnings = list(global_warnings)
        low = int(direction.get("low_confidence_count") or 0)
        if low:
            warnings.append(f"{low} member papers are low-confidence")
        representatives = []
        for rep in direction.get("representatives", []):
            representatives.append({
                key: rep.get(key)
                for key in ("item_key", "title_zh", "title", "year", "zotero_url")
                if rep.get(key) is not None
            })
        options.append({
            "direction_id": direction["direction_id"],
            "name_ja": direction.get("name_ja") or "",
            "name_zh": direction.get("name_zh") or "",
            "summary_zh": direction.get("summary_zh") or "",
            "paper_count": len(direction["members"]),
            "representatives": representatives,
            "warnings": warnings,
        })
    return {
        "status": "ok",
        "professor": preview["professor"],
        "preview_fingerprint": preview["preview_fingerprint"],
        "preview_fingerprint_version": preview["preview_fingerprint_version"],
        "options": options,
    }


def _validate_selected_directions(target: dict[str, Any]) -> None:
    _require_nonempty(target.get("professor"), "professor")
    if "targets" in target:
        raise ValueError("per-professor target state must not carry a targets[] envelope")
    raw_ids = target.get("selected_direction_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValueError("selected_direction_ids must be a non-empty array")
    direction_ids = [_require_nonempty(value, "selected_direction_ids[]") for value in raw_ids]
    if len(direction_ids) != len(set(direction_ids)):
        raise ValueError("selected_direction_ids contains duplicates")

    directions = target.get("directions")
    if not isinstance(directions, list) or not directions:
        raise ValueError("directions must be a non-empty array")
    seen_ids: set[str] = set()
    for direction in directions:
        if not isinstance(direction, dict):
            raise ValueError("target direction must be an object")
        direction_id = _require_nonempty(direction.get("direction_id"), "directions[].direction_id")
        if direction_id in seen_ids:
            raise ValueError(f"duplicate direction_id: {direction_id}")
        seen_ids.add(direction_id)
        members = direction.get("members")
        if not isinstance(members, list) or not members:
            raise ValueError(f"{direction_id}.members must be a non-empty array")
        for member in members:
            if not isinstance(member, dict):
                raise ValueError(f"{direction_id}.members entries must be objects")
            _require_nonempty(member.get("item_key"), f"{direction_id}.member.item_key")
        note = direction.get("user_note", "")
        if not isinstance(note, str):
            raise ValueError(f"{direction_id}.user_note must be a string")
    unknown = sorted(set(direction_ids) - seen_ids)
    if unknown:
        raise ValueError(f"directions[] missing selected direction_id(s): {unknown}")


def _validate_target_identity(target: dict[str, Any], target_path: Path, program_root: Path) -> None:
    """Prove the file is the authoritative Stage-0 state of exactly its own professor."""
    target_rel = _relative_under(target_path, program_root, "target_path")
    if Path(target_rel).name != TARGET_FILE_NAME:
        raise ValueError(f"target file must be named {TARGET_FILE_NAME}")
    professor_dir = str(Path(target_rel).parent)
    stored_dir = _require_nonempty(target.get("professor_dir"), "professor_dir")
    if stored_dir != professor_dir:
        raise ValueError(f"professor_dir {stored_dir} does not match the directory holding the target")
    preview_rel = _require_nonempty(target.get("preview_path"), "preview_path")
    if Path(preview_rel).name != PREVIEW_NAME:
        raise ValueError(f"preview_path must name {PREVIEW_NAME}")
    if str(Path(preview_rel).parent) != professor_dir:
        raise ValueError(f"preview_path must resolve under the stored professor_dir: {preview_rel}")


def _load_local_target(target_path: Path, program_root: Path) -> dict[str, Any]:
    state = load_json(target_path)
    if not isinstance(state, dict):
        raise ValueError("target state root must be an object")
    if state.get("schema_version") != SCHEMA_VERSION or state.get("kind") != KIND:
        raise ValueError("unsupported target state schema")
    _validate_selected_directions(state)
    _validate_target_identity(state, target_path, program_root)
    return state


def _history_snapshot(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "preview_fingerprint": target.get("preview_fingerprint"),
        "preview_fingerprint_version": target.get("preview_fingerprint_version"),
        "selected_direction_ids": list(target.get("selected_direction_ids") or []),
        "directions": [
            {"direction_id": direction.get("direction_id"), "user_note": direction.get("user_note") or ""}
            for direction in target.get("directions", [])
        ],
        "selected_at": target.get("selected_at"),
        "revised_at": now_utc(),
    }


def _transaction(professor: str, professor_dir_rel: str, preview_rel: str,
                 state_path: Path) -> dict[str, Any]:
    """Professor-local transaction record: canonical identity, never display name alone."""
    return {
        "professor": professor,
        "professor_dir": professor_dir_rel,
        "preview_path": preview_rel,
        "target_state": str(Path(state_path).resolve()),
    }


def _validated_selection(preview: dict[str, Any], selection: Any) -> tuple[list[str], dict[str, Any]]:
    if not isinstance(selection, dict):
        raise ValueError("selection must be an object")
    raw_ids = selection.get("direction_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValueError("selection.direction_ids must be a non-empty array")
    direction_ids = [_require_nonempty(value, "selection.direction_ids[]") for value in raw_ids]
    if len(direction_ids) != len(set(direction_ids)):
        raise ValueError("selection.direction_ids contains duplicates")
    notes = selection.get("notes") or {}
    if not isinstance(notes, dict):
        raise ValueError("selection.notes must be an object")
    by_id = {direction["direction_id"] for direction in preview["directions"]}
    unknown = sorted(set(direction_ids) - by_id)
    if unknown:
        raise ValueError(f"unknown direction_id(s): {unknown}")
    return direction_ids, notes


def _target_from_selection(preview: dict[str, Any], preview_rel: str, direction_ids: list[str],
                           note_for: Any, history: list[dict[str, Any]], timestamp: str) -> dict[str, Any]:
    by_id = {direction["direction_id"]: direction for direction in preview["directions"]}
    selected_directions = []
    for direction_id in direction_ids:
        source = deepcopy(by_id[direction_id])
        note = note_for(direction_id)
        if note is None:
            note = ""
        if not isinstance(note, str):
            raise ValueError(f"selection note for {direction_id} must be a string")
        selected_directions.append({
            "direction_id": direction_id,
            "name_ja": source.get("name_ja") or "",
            "name_zh": source.get("name_zh") or "",
            "summary_zh": source.get("summary_zh") or "",
            "member_fingerprint": source.get("member_fingerprint"),
            "members": deepcopy(source.get("members") or []),
            "representatives": deepcopy(source.get("representatives") or []),
            "paper_count": len(source.get("members") or []),
            "low_confidence_count": int(source.get("low_confidence_count") or 0),
            "coverage_share": source.get("coverage_share"),
            "user_note": note,
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "professor": preview["professor"],
        "professor_dir": str(Path(preview_rel).parent),
        "preview_path": preview_rel,
        "preview_fingerprint": preview["preview_fingerprint"],
        "preview_fingerprint_version": preview["preview_fingerprint_version"],
        "direction_id_version": preview.get("direction_id_version"),
        "membership_mode": preview.get("membership_mode"),
        "selected_direction_ids": direction_ids,
        "directions": selected_directions,
        "selected_at": timestamp,
        "selection_history": history,
    }


def select_target(program_root: Path, preview_path: Path, selection: dict[str, Any], *, selected_at: str | None = None) -> dict[str, Any]:
    """Revise the professor's existing local target; never establish one here.

    A missing local file is ``bootstrap_required`` with zero writes: first
    establishment belongs to :func:`bootstrap_target`, the only path allowed to
    read the retired program-level table.
    """
    program_root = program_root.resolve()
    preview_path = preview_path.resolve()
    preview_rel = _relative_under(preview_path, program_root, "preview_path")
    preview = validate_preview(preview_path)
    direction_ids, notes = _validated_selection(preview, selection)

    state_path = local_target_path(preview_path.parent)
    professor_dir_rel = str(Path(preview_rel).parent)
    transaction = _transaction(preview["professor"], professor_dir_rel, preview_rel, state_path)
    if not state_path.is_file():
        return {
            "status": "needs_input",
            "reason_code": "bootstrap_required",
            "message": "run contact_targets.py bootstrap to establish the first professor-local target",
            "transaction": transaction,
            "state_path": transaction["target_state"],
        }

    existing = _load_local_target(state_path, program_root)
    if existing.get("professor") != preview["professor"]:
        raise ValueError(
            f"target professor {existing.get('professor')!r} does not match current preview professor "
            f"{preview['professor']!r}"
        )
    existing_notes = {
        direction.get("direction_id"): direction.get("user_note") or ""
        for direction in existing.get("directions", [])
    }
    history = list(existing.get("selection_history") or [])
    history.append(_history_snapshot(existing))
    timestamp = selected_at or now_utc()

    def note_for(direction_id: str) -> Any:
        return notes[direction_id] if direction_id in notes else existing_notes.get(direction_id, "")

    target = _target_from_selection(preview, preview_rel, direction_ids, note_for, history, timestamp)
    atomic_json(state_path, target)
    return {
        "status": "ok",
        "mode": "revised",
        "state_path": str(state_path),
        "transaction": transaction,
        "professor": preview["professor"],
        "selected_direction_ids": direction_ids,
        "selected_count": len(direction_ids),
    }


def _member_keys(direction: dict[str, Any]) -> list[str]:
    """Membership identity: sorted itemKeys. Upstream derives direction_id from
    these, while member_fingerprint also hashes preview_confidence, so only the
    key set is material for target validity."""
    return sorted(
        str(member.get("item_key") or "")
        for member in (direction.get("members") or [])
    )


def _selected_projection(direction: dict[str, Any]) -> dict[str, Any]:
    """Projection of a preview direction into target state; mirrors select_target fields."""
    return {
        "name_ja": direction.get("name_ja") or "",
        "name_zh": direction.get("name_zh") or "",
        "summary_zh": direction.get("summary_zh") or "",
        "member_fingerprint": direction.get("member_fingerprint"),
        "members": deepcopy(direction.get("members") or []),
        "representatives": deepcopy(direction.get("representatives") or []),
        "paper_count": len(direction.get("members") or []),
        "low_confidence_count": int(direction.get("low_confidence_count") or 0),
        "coverage_share": direction.get("coverage_share"),
    }


def _projection_differs(stored: dict[str, Any], current: dict[str, Any]) -> bool:
    expected = _selected_projection(current)
    return any(stored.get(key) != value for key, value in expected.items())


def resolve_target(target_path: Path, program_root: Path, professors: list[str] | None = None) -> dict[str, Any]:
    """Resolve one professor from its professor-local authoritative target file.

    Only that file and that preview are read; a projection refresh writes only
    the same local file. The legacy program-level table is never consulted.
    """
    program_root = program_root.resolve()
    target_path = target_path.resolve()
    state_path = str(target_path)
    if not target_path.is_file():
        return {"status": "needs_input", "reason_code": "missing_target_state", "state_path": state_path, "targets": []}
    target = _load_local_target(target_path, program_root)
    transaction = _transaction(target["professor"], target["professor_dir"],
                               target["preview_path"], target_path)

    requested = {name.strip() for name in (professors or []) if name.strip()}
    if requested and target["professor"] not in requested:
        return {
            "status": "needs_input",
            "reason_code": "professor_not_selected",
            "missing_professors": sorted(requested),
            "state_path": state_path,
            "transaction": transaction,
            "targets": [],
        }

    targets = [target]
    stale: list[dict[str, Any]] = []
    refreshed: list[dict[str, Any]] = []
    try:
        preview_path = program_root / str(target.get("preview_path") or "")
        _relative_under(preview_path, program_root, "preview_path")
        preview = validate_preview(preview_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        stale.append({"professor": target.get("professor"), "reason": "preview_unreadable", "detail": str(exc)})
        preview = None
    if preview is not None:
        if preview.get("professor") != target.get("professor"):
            stale.append({"professor": target.get("professor"), "reason": "professor_changed"})
        else:
            current_by_id = {direction["direction_id"]: direction for direction in preview["directions"]}
            stale_directions = []
            projection_updates = []
            for stored in target.get("directions", []):
                direction_id = stored.get("direction_id")
                current = current_by_id.get(direction_id)
                if current is None:
                    stale_directions.append({
                        "direction_id": direction_id,
                        "reason": "selected_direction_removed",
                        "stored_member_fingerprint": stored.get("member_fingerprint"),
                        "stored_member_keys": _member_keys(stored),
                    })
                elif _member_keys(current) != _member_keys(stored):
                    stale_directions.append({
                        "direction_id": direction_id,
                        "reason": "selected_direction_changed",
                        "stored_member_fingerprint": stored.get("member_fingerprint"),
                        "current_member_fingerprint": current.get("member_fingerprint"),
                        "stored_member_keys": _member_keys(stored),
                        "current_member_keys": _member_keys(current),
                    })
                elif _projection_differs(stored, current):
                    projection_updates.append((stored, _selected_projection(current)))
            if stale_directions:
                stale.append({
                    "professor": target.get("professor"),
                    "reason": "selected_directions_stale",
                    "direction_ids": [entry["direction_id"] for entry in stale_directions],
                    "directions": stale_directions,
                    "stored_preview_fingerprint": target.get("preview_fingerprint"),
                    "current_preview_fingerprint": preview.get("preview_fingerprint"),
                })
            elif projection_updates:
                for stored, expected in projection_updates:
                    stored.update(expected)
                target["preview_fingerprint"] = preview["preview_fingerprint"]
                target["preview_fingerprint_version"] = preview["preview_fingerprint_version"]
                target["direction_id_version"] = preview.get("direction_id_version")
                target["projection_refreshed_at"] = now_utc()
                refreshed.append({
                    "professor": target.get("professor"),
                    "direction_ids": [stored.get("direction_id") for stored, _ in projection_updates],
                })
                atomic_json(target_path, target)
    if stale:
        return {"status": "needs_refresh", "reason_code": "preview_changed", "state_path": state_path,
                "transaction": transaction, "stale_targets": stale, "targets": targets}
    result = {"status": "ok", "state_path": state_path, "transaction": transaction, "targets": targets,
              "professors": [target.get("professor") for target in targets]}
    if refreshed:
        result["projection_refreshed"] = refreshed
    return result


def _load_legacy_state(legacy_path: Path) -> list[Any]:
    """Parse the retired program-level table and return its entries untouched."""
    state = load_json(legacy_path)
    if not isinstance(state, dict):
        raise ValueError("legacy target state root must be an object")
    if state.get("schema_version") != LEGACY_SCHEMA_VERSION or state.get("kind") != LEGACY_KIND:
        raise ValueError("unsupported legacy target state schema")
    if not isinstance(state.get("targets"), list):
        raise ValueError("legacy target state targets must be an array")
    return state["targets"]


def _legacy_entry_to_target(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("legacy target entry must be an object")
    history = entry.get("selection_history") or []
    if not isinstance(history, list):
        raise ValueError("legacy selection_history must be an array")
    target = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "professor": _require_nonempty(entry.get("professor"), "professor"),
        "professor_dir": _require_nonempty(entry.get("professor_dir"), "professor_dir"),
        "preview_path": _require_nonempty(entry.get("preview_path"), "preview_path"),
        "preview_fingerprint": _require_nonempty(entry.get("preview_fingerprint"), "preview_fingerprint"),
        "preview_fingerprint_version": _require_nonempty(
            entry.get("preview_fingerprint_version"), "preview_fingerprint_version"),
        "direction_id_version": entry.get("direction_id_version"),
        "membership_mode": entry.get("membership_mode"),
        "selected_direction_ids": entry.get("selected_direction_ids"),
        "directions": entry.get("directions"),
        "selected_at": _require_nonempty(entry.get("selected_at"), "selected_at"),
        "selection_history": deepcopy(history),
    }
    if "projection_refreshed_at" in entry:
        target["projection_refreshed_at"] = entry["projection_refreshed_at"]
    _validate_selected_directions(target)
    return target


def _comparable_target(target: dict[str, Any]) -> dict[str, Any]:
    """Migration identity comparison: the refresh timestamp is runtime metadata."""
    return {key: value for key, value in target.items() if key != "projection_refreshed_at"}


def _canonical_rel(value: Any) -> str:
    """Canonical program-relative path text, rejecting absolute or escaping values."""
    text = str(value or "").strip()
    if not text:
        raise ValueError("canonical path must be non-empty")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"path is not a canonical program-relative path: {text}")
    return str(path)


def _entry_canonical(entry: Any) -> tuple[str, str, str] | None:
    """Cheap canonical identity of a legacy entry; None when it cannot be attributed."""
    if not isinstance(entry, dict):
        return None
    try:
        professor = _require_nonempty(entry.get("professor"), "professor")
        professor_dir = _canonical_rel(entry.get("professor_dir"))
        preview_path = _canonical_rel(entry.get("preview_path"))
    except ValueError:
        return None
    return professor, professor_dir, preview_path


def _candidate_key(target: dict[str, Any]) -> str:
    """Normalized legacy-candidate semantics for the pre-write conflict check."""
    return json.dumps({
        "professor": target.get("professor"),
        "professor_dir": target.get("professor_dir"),
        "preview_path": target.get("preview_path"),
        "selected_direction_ids": sorted(target.get("selected_direction_ids") or []),
        "directions": sorted(
            [{
                "direction_id": direction.get("direction_id"),
                "user_note": direction.get("user_note") or "",
                "members": _member_keys(direction),
            } for direction in target.get("directions") or []],
            key=lambda item: str(item["direction_id"])),
    }, ensure_ascii=False, sort_keys=True)


def _preflight_candidates(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, int]:
    """Collapse semantically identical candidates to one source.

    Returns ``(source, conflict_count)``; a conflict count above one means the
    caller must fail closed with zero writes, before any local file exists.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        groups.setdefault(_candidate_key(candidate), []).append(candidate)
    if len(groups) > 1:
        return None, len(groups)
    if not groups:
        return None, 0
    group = next(iter(groups.values()))
    source = max(group, key=lambda item: (len(item.get("selection_history") or []),
                                          str(item.get("selected_at") or "")))
    return source, 1


def _prepare_migration_source(source: dict[str, Any], preview: dict[str, Any]) -> dict[str, Any]:
    """Validate a legacy selection against the current preview before it gains authority.

    Bulk migration has no current user selection with which to revise a stale
    legacy choice. Therefore a removed direction or changed selected member set
    must fail before the first local write. Projection-only changes are safe to
    refresh in memory, matching normal Stage-0 resolve semantics.
    """
    prepared = deepcopy(source)
    current_by_id = {direction["direction_id"]: direction for direction in preview["directions"]}
    projection_changed = False
    for stored in prepared.get("directions", []):
        direction_id = stored.get("direction_id")
        current = current_by_id.get(direction_id)
        if current is None:
            raise ValueError(f"selected direction {direction_id} no longer exists")
        if _member_keys(current) != _member_keys(stored):
            raise ValueError(f"selected direction {direction_id} membership changed")
        if _projection_differs(stored, current):
            stored.update(_selected_projection(current))
            projection_changed = True
    if projection_changed:
        prepared["preview_fingerprint"] = preview["preview_fingerprint"]
        prepared["preview_fingerprint_version"] = preview["preview_fingerprint_version"]
        prepared["direction_id_version"] = preview.get("direction_id_version")
        prepared["projection_refreshed_at"] = now_utc()
    return prepared


def _reliable_candidates(entries: list[Any], program_root: Path, professor_dir_rel: str,
                         preview_rel: str, professor: str) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[str]]:
    """Split legacy entries into this professor's candidates and non-blocking others.

    Only entries whose canonical name, ``professor_dir`` and ``preview_path`` all
    match the current professor are validated further; foreign, unknown-owner and
    path-conflicting entries are reported and never imported or business-checked.
    """
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    defective: list[str] = []
    for entry in entries:
        canonical = _entry_canonical(entry)
        if canonical is None:
            skipped.append({"reason": "identity_unreliable"})
            continue
        if canonical != (professor, professor_dir_rel, preview_rel):
            skipped.append({"reason": "same_name_other_dir" if canonical[0] == professor else "other_professor"})
            continue
        try:
            target = _legacy_entry_to_target(entry)
            _validate_target_identity(target, local_target_path(program_root / professor_dir_rel), program_root)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            defective.append(str(exc))
            continue
        candidates.append(target)
    return candidates, skipped, defective


def _write_first_local(program_root: Path, professor_dir_rel: str, target: dict[str, Any]) -> Path:
    """The single commit shared by bootstrap and bulk migration: one atomic write."""
    state_path = local_target_path(program_root / professor_dir_rel).resolve()
    atomic_json(state_path, target)
    return state_path


def bootstrap_target(program_root: Path, preview_path: Path, selection: dict[str, Any], *, selected_at: str | None = None) -> dict[str, Any]:
    """Establish the first professor-local target; the only runtime legacy reader.

    Fixed order: validate the current preview and this round's selection, classify
    the legacy table, keep only reliably-attributable candidates, finish the
    conflict preflight in memory, then write at most once. A whole-document parse
    failure is reported as recovery-unavailable and never blocks this professor.
    """
    program_root = program_root.resolve()
    preview_path = preview_path.resolve()
    preview_rel = _relative_under(preview_path, program_root, "preview_path")
    preview = validate_preview(preview_path)
    direction_ids, notes = _validated_selection(preview, selection)

    state_path = local_target_path(preview_path.parent)
    professor_dir_rel = str(Path(preview_rel).parent)
    professor = preview["professor"]
    transaction = _transaction(professor, professor_dir_rel, preview_rel, state_path)
    if state_path.is_file():
        established = _load_local_target(state_path, program_root)
        if established.get("professor") != professor:
            raise ValueError(
                f"target professor {established.get('professor')!r} does not match current preview professor "
                f"{professor!r}"
            )
        return {
            "status": "ok",
            "mode": "already_established",
            "state_path": str(state_path),
            "transaction": transaction,
            "professor": professor,
            "selected_direction_ids": established["selected_direction_ids"],
        }

    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    legacy_recovery: str | None = None
    source: dict[str, Any] | None = None
    legacy_path = program_root / LEGACY_TARGET_FILE
    if legacy_path.is_file():
        try:
            raw_entries = _load_legacy_state(legacy_path)
        except (OSError, ValueError, json.JSONDecodeError):
            legacy_recovery = "legacy_recovery_unavailable"
        else:
            candidates, skipped, defective = _reliable_candidates(
                raw_entries, program_root, professor_dir_rel, preview_rel, professor)
            if defective:
                return {"status": "error", "reason_code": "invalid_legacy_candidate_state",
                        "message": "; ".join(defective), "transaction": transaction,
                        "skipped": skipped}
            source, conflicts = _preflight_candidates(candidates)
            if conflicts > 1:
                return {"status": "error", "reason_code": "legacy_candidates_conflict",
                        "message": f"{conflicts} conflicting legacy entries claim this professor",
                        "transaction": transaction, "skipped": skipped}
            if skipped:
                legacy_recovery = "legacy_recovery_ambiguous"

    history = list(source.get("selection_history") or []) if source else []
    if source:
        history.append(_history_snapshot(source))
    existing_notes = {
        direction.get("direction_id"): direction.get("user_note") or ""
        for direction in (source or {}).get("directions", [])
    }

    def note_for(direction_id: str) -> Any:
        return notes[direction_id] if direction_id in notes else existing_notes.get(direction_id, "")

    target = _target_from_selection(preview, preview_rel, direction_ids, note_for, history,
                                    selected_at or now_utc())
    if source is None:
        mode = "fresh"
    elif _candidate_key(source) == _candidate_key(target):
        # Unchanged selection migrates rather than revises: legacy history and its own timestamp carry over.
        mode = "migrated"
        target = _target_from_selection(
            preview, preview_rel, direction_ids, note_for,
            deepcopy(source.get("selection_history") or []),
            source.get("selected_at") or target["selected_at"])
    else:
        mode = "migrated_revised"
    committed = _write_first_local(program_root, professor_dir_rel, target)
    result = {
        "status": "ok",
        "mode": mode,
        "state_path": str(committed),
        "transaction": _transaction(professor, professor_dir_rel, preview_rel, committed),
        "professor": professor,
        "selected_direction_ids": direction_ids,
        "selected_count": len(direction_ids),
        "legacy_candidates": len(candidates),
    }
    if legacy_recovery:
        result["legacy_recovery"] = legacy_recovery
    if skipped:
        result["legacy_skipped"] = skipped
    return result


def _migrate_group(program_root: Path, professor_dir_rel: str,
                   candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Migrate one professor's already-classified legacy candidates.

    Any conflict or unreadable local state is decided in memory before the only
    commit, so a group never partially writes.
    """
    professor = candidates[0]["professor"]
    preview_rel = candidates[0]["preview_path"]
    state_path = local_target_path(program_root / professor_dir_rel)
    source, conflicts = _preflight_candidates(candidates)
    if conflicts > 1:
        return {"status": "conflict", "professor": professor, "state_path": str(state_path),
                "detail": f"{conflicts} conflicting legacy entries claim this professor"}

    try:
        preview = validate_preview(program_root / preview_rel)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "failed", "professor": professor, "state_path": str(state_path),
                "detail": f"preview unreadable: {exc}"}
    if preview.get("professor") != professor:
        return {"status": "failed", "professor": professor, "state_path": str(state_path),
                "detail": f"preview professor {preview.get('professor')} does not match entry {professor}"}
    try:
        source = _prepare_migration_source(source, preview)
    except ValueError as exc:
        return {"status": "failed", "professor": professor, "state_path": str(state_path),
                "detail": f"legacy target is stale: {exc}"}

    if state_path.is_file():
        try:
            existing = load_json(state_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return {"status": "conflict", "professor": professor, "state_path": str(state_path.resolve()),
                    "detail": f"existing local target is unreadable: {exc}"}
        if not isinstance(existing, dict):
            return {"status": "conflict", "professor": professor, "state_path": str(state_path.resolve()),
                    "detail": "existing local target root is not an object"}
        if _comparable_target(existing) == _comparable_target(source):
            return {"status": "already_migrated", "professor": professor,
                    "state_path": str(state_path.resolve())}
        return {"status": "conflict", "professor": professor, "state_path": str(state_path.resolve()),
                "detail": "existing local target differs from the legacy entry"}

    committed = _write_first_local(program_root, professor_dir_rel, deepcopy(source))
    return {"status": "migrated", "professor": professor, "state_path": str(committed)}


def migrate_legacy_targets(program_root: Path) -> dict[str, Any]:
    """Fan the retired program-level table out into professor-local targets.

    Explicit bulk migration reuses the bootstrap classification, per-professor
    conflict preflight and commit helper, so the two paths cannot disagree:
    entries group by canonical ``professor_dir``, a group writes at most once and
    only after every conflict in that group is resolved in memory. The legacy
    file itself is left untouched for audit.
    """
    program_root = program_root.resolve()
    legacy_path = program_root / LEGACY_TARGET_FILE
    if not legacy_path.is_file():
        return {"status": "ok", "reason_code": "no_legacy_state", "legacy_path": str(legacy_path), "entries": []}
    try:
        raw_entries = _load_legacy_state(legacy_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "error", "reason_code": "legacy_unreadable", "message": str(exc),
                "legacy_path": str(legacy_path), "entries": []}

    groups: dict[str, list[dict[str, Any]]] = {}
    owner_of: list[str | None] = []
    defective: list[str | None] = []
    for entry in raw_entries:
        canonical = _entry_canonical(entry)
        if canonical is None:
            owner_of.append(None)
            defective.append("legacy entry identity is unreliable")
            continue
        professor, professor_dir_rel, _preview_rel = canonical
        try:
            target = _legacy_entry_to_target(entry)
            _validate_target_identity(target, local_target_path(program_root / professor_dir_rel), program_root)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            owner_of.append(None)
            defective.append(str(exc))
            continue
        owner_of.append(professor_dir_rel)
        defective.append(None)
        groups.setdefault(professor_dir_rel, []).append(target)

    decided = {professor_dir_rel: _migrate_group(program_root, professor_dir_rel, candidates)
               for professor_dir_rel, candidates in groups.items()}

    outcomes = list(decided.values())
    results: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_entries):
        professor = entry.get("professor") if isinstance(entry, dict) else None
        if defective[index]:
            orphan = {"status": "failed", "professor": professor, "detail": defective[index]}
            outcomes.append(orphan)
            results.append(orphan)
            continue
        outcome = decided[owner_of[index]]
        results.append({**outcome, "professor": outcome["professor"] or professor})

    def names(status: str) -> list[str]:
        return [item["professor"] for item in outcomes if item["status"] == status]

    failures = [item for item in outcomes if item["status"] in {"failed", "conflict"}]
    return {
        "status": "partial" if failures else "ok",
        "legacy_path": str(legacy_path),
        "migrated": names("migrated"),
        "already_migrated": names("already_migrated"),
        "failures": failures,
        "entries": results,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    preview = sub.add_parser("preview")
    preview.add_argument("--preview", required=True, type=Path)
    select = sub.add_parser("select")
    select.add_argument("--program-root", required=True, type=Path)
    select.add_argument("--preview", required=True, type=Path)
    select.add_argument("--selection-file", required=True, type=Path)
    bootstrap = sub.add_parser("bootstrap")
    bootstrap.add_argument("--program-root", required=True, type=Path)
    bootstrap.add_argument("--preview", required=True, type=Path)
    bootstrap.add_argument("--selection-file", required=True, type=Path)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--program-root", required=True, type=Path)
    resolve.add_argument("--target-file", required=True, type=Path)
    resolve.add_argument("--professors", default="")
    migrate = sub.add_parser("migrate")
    migrate.add_argument("--program-root", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "preview":
            emit(preview_options(args.preview))
            return 0
        if args.command in {"select", "bootstrap"}:
            handler = select_target if args.command == "select" else bootstrap_target
            payload = handler(args.program_root, args.preview, load_json(args.selection_file))
            emit(payload)
            return 0 if payload["status"] == "ok" else 2
        if args.command == "resolve":
            professors = [part.strip() for part in args.professors.split(",") if part.strip()]
            payload = resolve_target(args.target_file, args.program_root, professors)
            emit(payload)
            return 0 if payload["status"] == "ok" else 2
        if args.command == "migrate":
            payload = migrate_legacy_targets(args.program_root)
            emit(payload)
            return 0 if payload["status"] == "ok" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        emit({"status": "error", "reason_code": "invalid_target_state", "message": str(exc)})
        return 1
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
