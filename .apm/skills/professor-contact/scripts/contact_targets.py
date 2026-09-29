#!/usr/bin/env python3
"""Deterministic per-professor target-state helper for professor-contact Stage 0-2.

One professor owns exactly one authoritative Stage-0 file:
``<professor_dir>/套磁目标.json`` (schema 2, one target object, no ``targets[]``).
``select`` and ``resolve`` only ever touch that professor's own file and preview.
The retired program-level table ``教授研究/套磁目标.json`` is read by ``migrate``
only; it is never a runtime authority. Never opens Zotero, starts models, or
performs network I/O.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
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


def select_target(program_root: Path, preview_path: Path, selection: dict[str, Any], *, selected_at: str | None = None) -> dict[str, Any]:
    program_root = program_root.resolve()
    preview_path = preview_path.resolve()
    preview_rel = _relative_under(preview_path, program_root, "preview_path")
    preview = validate_preview(preview_path)

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

    by_id = {direction["direction_id"]: direction for direction in preview["directions"]}
    unknown = sorted(set(direction_ids) - set(by_id))
    if unknown:
        raise ValueError(f"unknown direction_id(s): {unknown}")

    state_path = local_target_path(preview_path.parent)
    existing = _load_local_target(state_path, program_root) if state_path.is_file() else None
    existing_notes = {
        direction.get("direction_id"): direction.get("user_note") or ""
        for direction in (existing or {}).get("directions", [])
    }
    history = list((existing or {}).get("selection_history") or [])
    if existing:
        history.append(_history_snapshot(existing))

    selected_directions = []
    for direction_id in direction_ids:
        source = deepcopy(by_id[direction_id])
        note = notes[direction_id] if direction_id in notes else existing_notes.get(direction_id, "")
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

    timestamp = selected_at or now_utc()
    target = {
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
    atomic_json(state_path, target)
    return {
        "status": "ok",
        "state_path": str(state_path),
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

    requested = {name.strip() for name in (professors or []) if name.strip()}
    if requested and target["professor"] not in requested:
        return {
            "status": "needs_input",
            "reason_code": "professor_not_selected",
            "missing_professors": sorted(requested),
            "state_path": state_path,
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
        return {"status": "needs_refresh", "reason_code": "preview_changed", "state_path": state_path, "stale_targets": stale, "targets": targets}
    result = {"status": "ok", "state_path": state_path, "targets": targets, "professors": [target.get("professor") for target in targets]}
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


def _migrate_entry(program_root: Path, entry: Any) -> dict[str, Any]:
    target = _legacy_entry_to_target(entry)
    professor = target["professor"]
    professor_dir = program_root / target["professor_dir"]
    _validate_target_identity(target, local_target_path(professor_dir), program_root)

    preview_path = program_root / target["preview_path"]
    preview = validate_preview(preview_path)
    if preview.get("professor") != professor:
        raise ValueError(f"preview professor {preview.get('professor')} does not match entry {professor}")

    state_path = local_target_path(professor_dir).resolve()
    if state_path.is_file():
        try:
            existing = load_json(state_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return {"status": "conflict", "professor": professor, "state_path": str(state_path),
                    "detail": f"existing local target is unreadable: {exc}"}
        if not isinstance(existing, dict):
            return {"status": "conflict", "professor": professor, "state_path": str(state_path),
                    "detail": "existing local target root is not an object"}
        if _comparable_target(existing) == _comparable_target(target):
            return {"status": "already_migrated", "professor": professor, "state_path": str(state_path)}
        return {"status": "conflict", "professor": professor, "state_path": str(state_path),
                "detail": "existing local target differs from the legacy entry"}

    atomic_json(state_path, target)
    return {"status": "migrated", "professor": professor, "state_path": str(state_path)}


def migrate_legacy_targets(program_root: Path) -> dict[str, Any]:
    """Fan the retired program-level table out into professor-local targets.

    The only code path allowed to read legacy contents. Entries are migrated
    independently: one bad entry cannot block or roll back the others, and the
    legacy file itself is left untouched for audit.
    """
    program_root = program_root.resolve()
    legacy_path = program_root / LEGACY_TARGET_FILE
    if not legacy_path.is_file():
        return {"status": "ok", "reason_code": "no_legacy_state", "legacy_path": str(legacy_path), "entries": []}
    try:
        entries = _load_legacy_state(legacy_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "error", "reason_code": "legacy_unreadable", "message": str(exc),
                "legacy_path": str(legacy_path), "entries": []}

    results = []
    for entry in entries:
        professor = entry.get("professor") if isinstance(entry, dict) else None
        try:
            results.append(_migrate_entry(program_root, entry))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            results.append({"status": "failed", "professor": professor, "detail": str(exc)})

    def names(status: str) -> list[str]:
        return [item["professor"] for item in results if item["status"] == status]

    failures = [item for item in results if item["status"] in {"failed", "conflict"}]
    payload = {
        "status": "partial" if failures else "ok",
        "legacy_path": str(legacy_path),
        "migrated": names("migrated"),
        "already_migrated": names("already_migrated"),
        "failures": failures,
        "entries": results,
    }
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    preview = sub.add_parser("preview")
    preview.add_argument("--preview", required=True, type=Path)
    select = sub.add_parser("select")
    select.add_argument("--program-root", required=True, type=Path)
    select.add_argument("--preview", required=True, type=Path)
    select.add_argument("--selection-file", required=True, type=Path)
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
        if args.command == "select":
            emit(select_target(args.program_root, args.preview, load_json(args.selection_file)))
            return 0
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
