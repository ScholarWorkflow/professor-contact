#!/usr/bin/env python3
"""Deterministic target-state helper for professor-contact Stage 0-2.

Turns normalized professor direction previews into the canonical
``教授研究/套磁目标.json`` machine state. Never opens Zotero, starts models,
or performs network I/O.
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

SCHEMA_VERSION = 1
KIND = "professor-contact-targets"
TARGET_FILE = Path("教授研究") / "套磁目标.json"
PREVIEW_NAME = "方向预筛.json"
VALID_CONFIDENCE = {"high", "low"}


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
    allowed = (root.resolve() / "教授研究").resolve()
    try:
        rel = resolved.relative_to(allowed)
    except ValueError as exc:
        raise ValueError(f"{field} must be under {allowed}") from exc
    return str(Path("教授研究") / rel)


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


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "kind": KIND, "updated_at": None, "targets": []}
    state = load_json(path)
    if not isinstance(state, dict):
        raise ValueError("target state root must be an object")
    if state.get("schema_version") != SCHEMA_VERSION or state.get("kind") != KIND:
        raise ValueError("unsupported target state schema")
    if not isinstance(state.get("targets"), list):
        raise ValueError("target state targets must be an array")
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

    state_path = program_root / TARGET_FILE
    state = _load_state(state_path)
    targets = list(state["targets"])
    existing_index = next((i for i, target in enumerate(targets) if target.get("professor") == preview["professor"]), None)
    existing = targets[existing_index] if existing_index is not None else None
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
    if existing_index is None:
        targets.append(target)
    else:
        targets[existing_index] = target
    targets.sort(key=lambda item: (str(item.get("professor") or ""), str(item.get("professor_dir") or "")))
    state["targets"] = targets
    state["updated_at"] = timestamp
    atomic_json(state_path, state)
    return {
        "status": "ok",
        "state_path": str(state_path),
        "professor": preview["professor"],
        "selected_direction_ids": direction_ids,
        "selected_count": len(direction_ids),
    }


def resolve_targets(program_root: Path, professors: list[str] | None = None) -> dict[str, Any]:
    program_root = program_root.resolve()
    state_path = program_root / TARGET_FILE
    if not state_path.is_file():
        return {"status": "needs_input", "reason_code": "missing_target_state", "state_path": str(state_path), "targets": []}
    state = _load_state(state_path)
    requested = {name.strip() for name in (professors or []) if name.strip()}
    targets = [deepcopy(target) for target in state["targets"] if not requested or target.get("professor") in requested]
    if requested:
        found = {target.get("professor") for target in targets}
        missing = sorted(requested - found)
        if missing:
            return {"status": "needs_input", "reason_code": "professor_not_selected", "missing_professors": missing, "state_path": str(state_path), "targets": targets}

    stale = []
    for target in targets:
        preview_path = program_root / str(target.get("preview_path") or "")
        try:
            _relative_under(preview_path, program_root, "preview_path")
            preview = validate_preview(preview_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            stale.append({"professor": target.get("professor"), "reason": f"preview_unreadable: {exc}"})
            continue
        if preview.get("professor") != target.get("professor"):
            stale.append({"professor": target.get("professor"), "reason": "professor_changed"})
            continue
        if preview.get("preview_fingerprint") != target.get("preview_fingerprint") or preview.get("preview_fingerprint_version") != target.get("preview_fingerprint_version"):
            stale.append({
                "professor": target.get("professor"),
                "reason": "preview_changed",
                "stored_preview_fingerprint": target.get("preview_fingerprint"),
                "current_preview_fingerprint": preview.get("preview_fingerprint"),
            })
    if stale:
        return {"status": "needs_refresh", "reason_code": "preview_changed", "state_path": str(state_path), "stale_targets": stale, "targets": targets}
    return {"status": "ok", "state_path": str(state_path), "targets": targets, "professors": [target.get("professor") for target in targets]}


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
    resolve.add_argument("--professors", default="")
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
            payload = resolve_targets(args.program_root, professors)
            emit(payload)
            return 0 if payload["status"] == "ok" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        emit({"status": "error", "reason_code": "invalid_target_state", "message": str(exc)})
        return 1
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
