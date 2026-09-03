#!/usr/bin/env python3
"""Deterministic Stage 1 candidate builder for professor-contact.

Turns the selected target state (``教授研究/套磁目标.json``) into per-direction,
high-recall candidate sets for PDF assurance and persists a machine-readable
snapshot (``教授研究/套磁阶段1候选.json``). Expansion is cheap-evidence only and
never decides final direction membership. Never opens Zotero, starts models,
performs network I/O, or mutates direction membership anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contact_targets  # noqa: E402

SCHEMA_VERSION = 1
KIND = "professor-contact-stage1"
SNAPSHOT_FILE = Path("教授研究") / "套磁阶段1候选.json"
USABLE_STATUS = "downloaded"
MEMBERSHIP_CLAIM = "non_final_candidates_only"

REASON_PROVISIONAL = "provisional_member"
REASON_LOW_CONFIDENCE = "low_confidence_preview"
REASON_CROSS_DIRECTION = "cross_direction_overlap"
REASON_UNCLASSIFIED_OR_NEW = "unclassified_or_new_since_preview"
REASON_USER_NAMED = "user_named"

# Cheap lexical evidence gates. STRICT applies to high-confidence members of
# other preview directions; RELAXED applies to low-confidence members and to
# papers the preview never placed (unclassified or added after the preview).
STRICT_MIN_MATCHED = 2
STRICT_MIN_COVERAGE = 0.5
RELAXED_MIN_MATCHED = 2
RELAXED_MIN_COVERAGE = 0.34
MAX_EVIDENCE_TOKENS = 6

EXPANSION_POLICY = {
    "evidence": "local lexical overlap only; candidates are not final direction membership",
    "strict": {"min_matched_tokens": STRICT_MIN_MATCHED, "min_coverage": STRICT_MIN_COVERAGE},
    "relaxed": {"min_matched_tokens": RELAXED_MIN_MATCHED, "min_coverage": RELAXED_MIN_COVERAGE},
}


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


def sha256_obj(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def text_tokens(text: str) -> set:
    tokens = set()
    for word in re.findall(r"[A-Za-z0-9]+", text or ""):
        if len(word) >= 3:
            tokens.add(word.lower())
    for run in re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", text or ""):
        for index in range(len(run) - 1):
            tokens.add(run[index:index + 2])
    return tokens


def paper_tokens(paper: dict[str, Any]) -> set:
    parts = []
    for field in ("title", "title_zh"):
        value = paper.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    return text_tokens(" ".join(parts))


def direction_profile_tokens(direction: dict[str, Any]) -> set:
    parts = []
    for field in ("name_ja", "name_zh", "summary_zh"):
        value = direction.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    for rep in direction.get("representatives") or []:
        if isinstance(rep, dict):
            for field in ("title", "title_zh"):
                value = rep.get(field)
                if isinstance(value, str) and value.strip():
                    parts.append(value)
    return text_tokens(" ".join(parts))


def overlap_evidence(paper_toks: set, profile_toks: set) -> dict[str, Any] | None:
    if not paper_toks or not profile_toks:
        return None
    matched = paper_toks & profile_toks
    if not matched:
        return None
    coverage = len(matched) / len(paper_toks)
    return {
        "matched_count": len(matched),
        "coverage": round(coverage, 2),
        "matched_tokens": sorted(matched)[:MAX_EVIDENCE_TOKENS],
    }


def passes(matched_count: int, coverage: float, min_matched: int, min_coverage: float) -> bool:
    return matched_count >= min_matched and coverage >= min_coverage


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def load_papers(papers_path: Path) -> dict[str, dict[str, Any]]:
    data = load_json(papers_path)
    if not isinstance(data, dict) or not isinstance(data.get("papers"), list):
        raise ValueError(f"papers.json at {papers_path} must be an object with a papers array")
    papers: dict[str, dict[str, Any]] = {}
    for paper in data["papers"]:
        if not isinstance(paper, dict):
            continue
        item_key = str(paper.get("item_key") or "").strip()
        if item_key:
            papers.setdefault(item_key, paper)
    return papers


def resolve_named_entries(entries: list[str], papers: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Resolve user-named entries (item key or exact normalized title) to item keys."""
    resolved: list[str] = []
    unmatched: list[str] = []
    title_index: dict[str, str] = {}
    for item_key, paper in papers.items():
        title = paper.get("title")
        if isinstance(title, str) and title.strip():
            title_index.setdefault(normalize_text(title), item_key)
    for entry in entries:
        text = str(entry or "").strip()
        if not text:
            continue
        if text in papers:
            resolved.append(text)
            continue
        by_title = title_index.get(normalize_text(text))
        if by_title:
            resolved.append(by_title)
        else:
            unmatched.append(text)
    return resolved, unmatched


def parse_named_file(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return {}
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("named-papers file must be an object")
    directions = data.get("directions")
    if not isinstance(directions, dict):
        raise ValueError('named-papers file must contain a "directions" object')
    named: dict[str, list[str]] = {}
    for direction_id, entries in directions.items():
        if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
            raise ValueError(f"named-papers entries for {direction_id} must be an array of strings")
        cleaned = [item.strip() for item in entries if item.strip()]
        if cleaned:
            named[str(direction_id)] = cleaned
    return named


def preview_member_index(preview: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Map item_key -> [{direction_id, preview_confidence}, ...] across ALL preview directions."""
    index: dict[str, list[dict[str, Any]]] = {}
    for direction in preview.get("directions", []):
        for member in direction.get("members", []):
            index.setdefault(member["item_key"], []).append({
                "item_key": member["item_key"],
                "direction_id": direction["direction_id"],
                "preview_confidence": member.get("preview_confidence", "high"),
            })
    return index


def papers_digest(papers: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item_key in sorted(papers):
        paper = papers[item_key]
        rows.append({
            "item_key": item_key,
            "title": paper.get("title"),
            "year": paper.get("year"),
            "pdf_status": paper.get("pdf_status"),
        })
    return rows


def input_fingerprint(target: dict[str, Any], papers: dict[str, dict[str, Any]]) -> str:
    """Fingerprint of the candidate-build inputs (target selection + papers state).

    User-named papers are deliberately excluded: they extend the candidate set but
    not the readiness state, so ``verify`` can recompute this fingerprint without
    the named-papers file.
    """
    return sha256_obj({
        "version": 1,
        "preview_fingerprint": target.get("preview_fingerprint"),
        "preview_fingerprint_version": target.get("preview_fingerprint_version"),
        "selected_direction_ids": target.get("selected_direction_ids"),
        "directions": [
            {
                "direction_id": direction.get("direction_id"),
                "member_fingerprint": direction.get("member_fingerprint"),
                "members": direction.get("members"),
            }
            for direction in target.get("directions", [])
        ],
        "papers": papers_digest(papers),
    })


def build_direction_entry(
    direction: dict[str, Any],
    member_index: dict[str, list[dict[str, Any]]],
    papers: dict[str, dict[str, Any]],
    named_entries: list[str],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Build one selected direction's candidate set. Returns (entry, missing_keys, unresolved_keys)."""
    profile_toks = direction_profile_tokens(direction)
    provisional_keys = sorted({member["item_key"] for member in direction.get("members", [])})
    reasons: dict[str, list[str]] = {}
    evidence: dict[str, dict[str, Any]] = {}

    def add_reason(key: str, reason: str) -> None:
        bucket = reasons.setdefault(key, [])
        if reason not in bucket:
            bucket.append(reason)

    for item_key in provisional_keys:
        add_reason(item_key, REASON_PROVISIONAL)
        memberships = member_index.get(item_key, [])
        if any(m["direction_id"] == direction["direction_id"]
               and m["preview_confidence"] == "low" for m in memberships):
            add_reason(item_key, REASON_LOW_CONFIDENCE)

    def consider(key: str) -> None:
        if key in reasons and REASON_PROVISIONAL in reasons[key]:
            return
        memberships = member_index.get(key, [])
        placed_elsewhere = any(m["direction_id"] != direction["direction_id"] for m in memberships)
        low_confidence = any(m["preview_confidence"] == "low" for m in memberships)
        paper = papers.get(key)
        paper_toks = paper_tokens(paper) if paper else set()
        detail = overlap_evidence(paper_toks, profile_toks)
        matched = detail["matched_count"] if detail else 0
        coverage = detail["coverage"] if detail else 0.0

        if placed_elsewhere:
            if passes(matched, coverage, STRICT_MIN_MATCHED, STRICT_MIN_COVERAGE):
                add_reason(key, REASON_CROSS_DIRECTION)
                evidence[key] = detail
            elif low_confidence and passes(matched, coverage, RELAXED_MIN_MATCHED, RELAXED_MIN_COVERAGE):
                add_reason(key, REASON_LOW_CONFIDENCE)
                add_reason(key, REASON_CROSS_DIRECTION)
                evidence[key] = detail
            return
        if paper is not None and passes(matched, coverage, RELAXED_MIN_MATCHED, RELAXED_MIN_COVERAGE):
            add_reason(key, REASON_UNCLASSIFIED_OR_NEW)
            evidence[key] = detail

    for memberships in member_index.values():
        for membership in memberships:
            if membership["direction_id"] != direction["direction_id"]:
                consider(membership["item_key"])
    for item_key in papers:
        if item_key not in member_index:
            consider(item_key)

    # named_entries are already resolved to item keys present in papers.json.
    for item_key in sorted(set(named_entries)):
        add_reason(item_key, REASON_USER_NAMED)

    candidate_keys = sorted(reasons)
    usable_keys: list[str] = []
    missing_keys: list[str] = []
    unresolved_keys: list[str] = []
    status_counts: dict[str, int] = {}
    for item_key in candidate_keys:
        paper = papers.get(item_key)
        if paper is None:
            unresolved_keys.append(item_key)
            continue
        status = str(paper.get("pdf_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == USABLE_STATUS:
            usable_keys.append(item_key)
        else:
            missing_keys.append(item_key)

    entry = {
        "direction_id": direction.get("direction_id"),
        "name_ja": direction.get("name_ja") or "",
        "name_zh": direction.get("name_zh") or "",
        "provisional_member_keys": provisional_keys,
        "candidate_keys": candidate_keys,
        "expansion_reasons": {key: reasons[key] for key in candidate_keys},
        "expansion_evidence": {key: evidence[key] for key in sorted(evidence) if key in reasons},
        "pdf_readiness": {
            "usable_item_keys": usable_keys,
            "missing_item_keys": missing_keys,
            "unresolved_item_keys": unresolved_keys,
            "status_counts": dict(sorted(status_counts.items())),
        },
    }
    return entry, missing_keys, unresolved_keys


def build_professor_entry(
    program_root: Path,
    target: dict[str, Any],
    named_by_direction: dict[str, list[str]],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    professor_dir = program_root / str(target.get("professor_dir") or "")
    preview_path = program_root / str(target.get("preview_path") or "")
    preview = contact_targets.validate_preview(preview_path)
    papers_path = professor_dir / "papers.json"
    if not papers_path.is_file():
        raise FileNotFoundError(f"missing papers.json for {target.get('professor')}: {papers_path}")
    papers = load_papers(papers_path)
    member_index = preview_member_index(preview)

    unmatched: list[dict[str, str]] = []
    named_resolved: dict[str, list[str]] = {}
    for direction_id, entries in named_by_direction.items():
        if direction_id not in {d["direction_id"] for d in target.get("directions", [])}:
            raise ValueError(f"named-papers reference unknown direction_id: {direction_id}")
        keys, leftovers = resolve_named_entries(entries, papers)
        named_resolved[direction_id] = keys
        for leftover in leftovers:
            unmatched.append({"direction_id": direction_id, "entry": leftover})

    direction_entries: list[dict[str, Any]] = []
    work_queue: set[str] = set()
    missing: set[str] = set()
    unresolved: set[str] = set()
    for direction in target.get("directions", []):
        entry, missing_keys, unresolved_keys = build_direction_entry(
            direction, member_index, papers, named_resolved.get(direction["direction_id"], [])
        )
        direction_entries.append(entry)
        work_queue.update(entry["candidate_keys"])
        missing.update(missing_keys)
        unresolved.update(unresolved_keys)

    action = "pdf_fill_needed" if missing else "needs_resolution" if unresolved else "noop"
    built_at = now_utc()
    professor_entry = {
        "professor": target.get("professor"),
        "professor_dir": target.get("professor_dir"),
        "preview_path": target.get("preview_path"),
        "preview_fingerprint": target.get("preview_fingerprint"),
        "preview_fingerprint_version": target.get("preview_fingerprint_version"),
        "direction_id_version": target.get("direction_id_version"),
        "membership_claim": MEMBERSHIP_CLAIM,
        "input_fingerprint": input_fingerprint(target, papers),
        "built_at": built_at,
        "action": action,
        "directions": direction_entries,
        "work_queue_item_keys": sorted(work_queue),
        "missing_item_keys": sorted(missing),
        "unresolved_item_keys": sorted(unresolved),
    }
    summary = {
        "professor": target.get("professor"),
        "action": action,
        "work_queue_item_keys": sorted(work_queue),
        "missing_item_keys": sorted(missing),
        "unresolved_item_keys": sorted(unresolved),
    }
    return professor_entry, summary, unmatched


def load_snapshot(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": KIND,
            "membership_claim": MEMBERSHIP_CLAIM,
            "expansion_policy": EXPANSION_POLICY,
            "updated_at": None,
            "professors": [],
        }
    state = load_json(path)
    if not isinstance(state, dict):
        raise ValueError("stage1 snapshot root must be an object")
    if state.get("schema_version") != SCHEMA_VERSION or state.get("kind") != KIND:
        raise ValueError("unsupported stage1 snapshot schema")
    if not isinstance(state.get("professors"), list):
        raise ValueError("stage1 snapshot professors must be an array")
    return state


def build_command(program_root: Path, professors: list[str] | None, named_file: Path | None) -> dict[str, Any]:
    program_root = program_root.resolve()
    resolution = contact_targets.resolve_targets(program_root, professors)
    if resolution.get("status") != "ok":
        emit(resolution)
        raise SystemExit(2)

    named_by_professor: dict[str, dict[str, list[str]]] = {}
    if named_file is not None:
        named_directions = parse_named_file(named_file)
        all_targets = resolution.get("targets", [])
        owner: dict[str, dict[str, Any]] = {}
        for target in all_targets:
            for direction in target.get("directions", []):
                owner[direction["direction_id"]] = target
        for direction_id, entries in named_directions.items():
            target = owner.get(direction_id)
            if target is None:
                raise ValueError(f"named-papers reference unknown direction_id: {direction_id}")
            named_by_professor.setdefault(target["professor"], {})[direction_id] = entries

    snapshot_path = program_root / SNAPSHOT_FILE
    snapshot = load_snapshot(snapshot_path)
    entries = [item for item in snapshot["professors"] if isinstance(item, dict)]
    processed: dict[str, dict[str, Any]] = {}
    summaries: list[dict[str, Any]] = []
    unmatched_all: list[dict[str, str]] = []
    for target in resolution.get("targets", []):
        name = target.get("professor")
        entry, summary, unmatched = build_professor_entry(
            program_root, target, named_by_professor.get(name, {})
        )
        processed[name] = entry
        summaries.append(summary)
        unmatched_all.extend(unmatched)
    merged = [item for item in entries if item.get("professor") not in processed]
    merged.extend(processed.values())
    merged.sort(key=lambda item: (str(item.get("professor") or ""), str(item.get("professor_dir") or "")))
    snapshot["professors"] = merged
    snapshot["updated_at"] = now_utc()
    atomic_json(snapshot_path, snapshot)

    missing_union = sorted({key for item in summaries for key in item["missing_item_keys"]})
    unresolved_union = sorted({key for item in summaries for key in item["unresolved_item_keys"]})
    if missing_union:
        action = "pdf_fill_needed"
    elif unresolved_union:
        action = "needs_resolution"
    else:
        action = "noop"
    return {
        "status": "ok",
        "action": action,
        "snapshot_path": str(snapshot_path),
        "professors": [item["professor"] for item in summaries],
        "missing_item_keys": missing_union,
        "unresolved_item_keys": unresolved_union,
        "unmatched_named_entries": unmatched_all,
        "per_professor": {
            item["professor"]: {
                "action": item["action"],
                "work_queue_item_keys": item["work_queue_item_keys"],
                "missing_item_keys": item["missing_item_keys"],
                "unresolved_item_keys": item["unresolved_item_keys"],
            }
            for item in summaries
        },
    }


def verify_command(program_root: Path, professors: list[str] | None) -> dict[str, Any]:
    """Read-only consistency check between the snapshot and the current inputs.

    Stage 2 consumes the snapshot's candidate sets, so it must verify (not trust)
    that the snapshot exists, covers every selected direction, and was built from
    the current target selection and papers state. Never writes.
    """
    program_root = program_root.resolve()
    resolution = contact_targets.resolve_targets(program_root, professors)
    if resolution.get("status") != "ok":
        emit(resolution)
        raise SystemExit(2)
    snapshot_path = program_root / SNAPSHOT_FILE
    if not snapshot_path.is_file():
        emit({"status": "needs_input", "reason_code": "missing_stage1_snapshot",
              "snapshot_path": str(snapshot_path), "notes": "run Stage 1 (contact_stage1.py build) first"})
        raise SystemExit(2)
    snapshot = load_snapshot(snapshot_path)
    entries = {item.get("professor"): item for item in snapshot["professors"] if isinstance(item, dict)}
    stale: list[dict[str, Any]] = []
    checked: list[str] = []
    for target in resolution.get("targets", []):
        name = target.get("professor")
        entry = entries.get(name)
        if entry is None:
            emit({"status": "needs_input", "reason_code": "professor_missing_from_snapshot",
                  "snapshot_path": str(snapshot_path), "professor": name,
                  "notes": "run Stage 1 (contact_stage1.py build) first"})
            raise SystemExit(2)
        problems: list[str] = []
        if entry.get("preview_fingerprint") != target.get("preview_fingerprint") or \
                entry.get("preview_fingerprint_version") != target.get("preview_fingerprint_version"):
            problems.append("preview_fingerprint_mismatch")
        snapshot_directions = {d.get("direction_id"): d for d in entry.get("directions", [])
                               if isinstance(d, dict)}
        for direction in target.get("directions", []):
            snapshot_direction = snapshot_directions.get(direction.get("direction_id"))
            if snapshot_direction is None:
                problems.append(f"missing_direction:{direction.get('direction_id')}")
                continue
            provisional = sorted({m["item_key"] for m in direction.get("members", [])})
            if not set(provisional) <= set(snapshot_direction.get("candidate_keys") or []):
                problems.append(f"candidate_keys_incomplete:{direction.get('direction_id')}")
        professor_dir = program_root / str(target.get("professor_dir") or "")
        papers_path = professor_dir / "papers.json"
        if not papers_path.is_file():
            problems.append("missing_papers_json")
        else:
            current_fingerprint = input_fingerprint(target, load_papers(papers_path))
            if entry.get("input_fingerprint") != current_fingerprint:
                problems.append("input_fingerprint_mismatch")
        if problems:
            stale.append({"professor": name, "problems": sorted(set(problems))})
        else:
            checked.append(name)
    if stale:
        emit({"status": "needs_input", "reason_code": "stale_stage1_snapshot",
              "snapshot_path": str(snapshot_path), "stale_professors": stale,
              "notes": "re-run Stage 1 (contact_stage1.py build) before Stage 2"})
        raise SystemExit(2)
    return {"status": "ok", "snapshot_path": str(snapshot_path), "professors": checked}


def main() -> int:
    parser = argparse.ArgumentParser(description="professor-contact Stage 1 candidate builder")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--program-root", required=True, type=Path)
    build.add_argument("--professors", default="")
    build.add_argument("--named-file", default=None, type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("--program-root", required=True, type=Path)
    verify.add_argument("--professors", default="")
    args = parser.parse_args()
    try:
        if args.command == "build":
            professors = [part.strip() for part in args.professors.split(",") if part.strip()]
            payload = build_command(args.program_root, professors or None, args.named_file)
            emit(payload)
            return 0
        if args.command == "verify":
            professors = [part.strip() for part in args.professors.split(",") if part.strip()]
            payload = verify_command(args.program_root, professors or None)
            emit(payload)
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        emit({"status": "error", "reason_code": "invalid_stage1_input", "message": str(exc)})
        return 1
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
