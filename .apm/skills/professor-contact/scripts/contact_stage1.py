#!/usr/bin/env python3
"""Deterministic Stage 1 candidate builder for professor-contact.

Turns one professor's selected target state (``<professor_dir>/套磁目标.json``)
into per-direction, high-recall candidate sets for PDF assurance and persists
that professor's own machine-readable snapshot
(``<professor_dir>/套磁阶段1候选.json``). One invocation handles exactly one
professor and touches only that professor's state file. Expansion is
cheap-evidence only and never decides final direction membership. Never opens
Zotero, starts models, performs network I/O, or mutates direction membership
anywhere.
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

SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
KIND = "professor-contact-stage1"
SNAPSHOT_NAME = "套磁阶段1候选.json"
LEGACY_SNAPSHOT_FILE = contact_targets.RESEARCH_DIR / SNAPSHOT_NAME
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


def relative_under(path: Path, root: Path, field: str) -> str:
    """Return ``path`` relative to ``root``, refusing anything outside it."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(root.resolve()))
    except ValueError as exc:
        raise ValueError(f"{field} must be under {root}") from exc


def local_state_path(program_root: Path, professor_dir: str) -> Path:
    """The one Stage-1 state file of the professor owning ``professor_dir``."""
    text = str(professor_dir or "").strip()
    if not text or text in {".", ".."}:
        raise ValueError("professor_dir must be a non-empty relative path")
    directory = (program_root / text).resolve()
    research_root = (program_root / contact_targets.RESEARCH_DIR).resolve()
    relative = relative_under(directory, research_root, "professor_dir")
    if not Path(relative).parts:
        raise ValueError("professor_dir must be a professor directory below the research directory")
    return directory / SNAPSHOT_NAME


def validate_local_state(state: Any, state_path: Path, program_root: Path,
                         target: dict[str, Any]) -> str | None:
    """Return the reason a local Stage-1 state is not this professor's authoritative file."""
    if not isinstance(state, dict):
        return "stage1 snapshot root must be an object"
    if state.get("schema_version") != SCHEMA_VERSION or state.get("kind") != KIND:
        return "unsupported stage1 snapshot schema"
    if "professors" in state:
        return "professor-local stage1 snapshot must not carry a professors array"
    try:
        expected = local_state_path(program_root, str(target.get("professor_dir") or ""))
    except ValueError as exc:
        return str(exc)
    if state_path.resolve() != expected.resolve():
        return f"stage1 snapshot must live at {expected}"
    stored_dir = str(state.get("professor_dir") or "")
    try:
        stored_relative = relative_under(program_root / stored_dir, program_root, "professor_dir")
    except ValueError as exc:
        return str(exc)
    if stored_relative != str(target.get("professor_dir")):
        return f"professor_dir {stored_dir} does not match the resolved target directory"
    if state.get("professor") != target.get("professor"):
        return "stage1 snapshot professor does not match the resolved target professor"
    preview_dir = str(Path(str(state.get("preview_path") or "")).parent)
    if preview_dir != stored_dir:
        return "stage1 snapshot preview_path must resolve under its own professor_dir"
    target_preview = str(target.get("preview_path") or "")
    snapshot_preview = str(state.get("preview_path") or "")
    if not target_preview or not snapshot_preview:
        return "stage1 snapshot preview_path must match the resolved target preview_path"
    try:
        same_preview = ((program_root / snapshot_preview).resolve()
                        == (program_root / target_preview).resolve())
    except OSError:
        same_preview = False
    if not same_preview:
        return "stage1 snapshot preview_path does not match the resolved target preview_path"
    if not isinstance(state.get("directions"), list):
        return "stage1 snapshot directions must be an array"
    return None


def read_local_state(program_root: Path, target: dict[str, Any]) -> tuple[Path, dict | None, str | None]:
    """Read one professor's own Stage-1 state. Never consults the legacy aggregate."""
    state_path = local_state_path(program_root, str(target.get("professor_dir") or ""))
    if not state_path.is_file():
        return state_path, None, "missing_stage1_snapshot"
    try:
        state = load_json(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return state_path, None, f"invalid_stage1_input: {exc}"
    problem = validate_local_state(state, state_path, program_root, target)
    if problem is not None:
        return state_path, None, f"invalid_stage1_input: {problem}"
    return state_path, state, None


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


def stage1_papers_digest(papers: dict[str, dict[str, Any]],
                         candidate_keys: set[str] | None = None) -> list[dict[str, Any]]:
    """Exactly the paper fields Stage 1 reads, scoped by what each field affects.

    title/title_zh feed paper_tokens() and can bring ANY paper into the candidate
    set via expansion, so they are always fingerprinted across all papers.
    pdf_status only affects readiness AFTER candidate_keys are determined, so it
    is fingerprinted only for the actual candidate union (or all papers when the
    caller has not yet computed candidates). A non-candidate paper flipping
    pdf_status cannot change candidate membership, work_queue_item_keys, missing/
    usable readiness, or any Stage-2 input, so it must not invalidate the snapshot.
    """
    rows = []
    for item_key in sorted(papers):
        paper = papers[item_key]
        row: dict[str, Any] = {
            "item_key": item_key,
            "title": paper.get("title"),
            "title_zh": paper.get("title_zh"),
        }
        if candidate_keys is None or item_key in candidate_keys:
            row["pdf_status"] = paper.get("pdf_status")
        rows.append(row)
    return rows


def input_fingerprint(target: dict[str, Any], preview: dict[str, Any],
                      papers: dict[str, dict[str, Any]],
                      candidate_keys: set[str] | None = None) -> str:
    """Exact fingerprint of everything candidate building consumes — no wider, no narrower.

    - selected direction identities + provisional member item keys (candidate base set);
    - selected-direction lexical profile inputs read by direction_profile_tokens()
      (name_ja/name_zh/summary_zh + representative title/title_zh);
    - membership placement and preview_confidence of ALL preview directions, because
      the cross-direction gates / low-confidence reasons / unplaced detection all
      derive from the full preview member index;
    - paper fields read by Stage 1: title/title_zh across all papers (expansion
      inputs), pdf_status scoped to the candidate union (readiness only matters for
      candidates — a non-candidate pdf_status change cannot affect any Stage-2 input).

    The whole-preview preview_fingerprint is deliberately NOT a validity input here
    (it stays in the snapshot as provenance only): resolve legitimately rewrites the
    target's stored fingerprint for display-only projection changes (e.g.
    coverage_share) and whole-preview churn that Stage 1 never reads.

    User-named papers are deliberately excluded: they extend the candidate set but
    not the readiness state, so ``verify`` can recompute this fingerprint without
    the named-papers file.
    """
    selected = []
    for direction in target.get("directions", []):
        representatives = [
            {"item_key": rep.get("item_key"),
             "title": rep.get("title"),
             "title_zh": rep.get("title_zh")}
            for rep in sorted(direction.get("representatives") or [],
                              key=lambda r: str(r.get("item_key")))
        ]
        selected.append({
            "direction_id": direction.get("direction_id"),
            "member_item_keys": sorted({m["item_key"] for m in direction.get("members", [])}),
            "name_ja": direction.get("name_ja"),
            "name_zh": direction.get("name_zh"),
            "summary_zh": direction.get("summary_zh"),
            "representatives": representatives,
        })
    selected.sort(key=lambda d: str(d["direction_id"]))
    membership = []
    for direction in preview.get("directions", []):
        membership.append({
            "direction_id": direction.get("direction_id"),
            "members": [
                {"item_key": member.get("item_key"),
                 "preview_confidence": member.get("preview_confidence")}
                for member in sorted(direction.get("members", []),
                                     key=lambda m: str(m.get("item_key")))
            ],
        })
    membership.sort(key=lambda d: str(d["direction_id"]))
    return sha256_obj({
        "version": 2,
        "selected_direction_ids": target.get("selected_direction_ids"),
        "selected_directions": selected,
        "preview_membership": membership,
        "papers": stage1_papers_digest(papers, candidate_keys),
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
        "preview_fingerprint": preview.get("preview_fingerprint"),
        "preview_fingerprint_version": preview.get("preview_fingerprint_version"),
        "direction_id_version": target.get("direction_id_version"),
        "membership_claim": MEMBERSHIP_CLAIM,
        "input_fingerprint": input_fingerprint(target, preview, papers, work_queue),
        "built_at": built_at,
        "action": action,
        "directions": direction_entries,
        "work_queue_item_keys": sorted(work_queue),
        "missing_item_keys": sorted(missing),
        "unresolved_item_keys": sorted(unresolved),
    }
    summary = {
        "professor": target.get("professor"),
        "professor_dir": target.get("professor_dir"),
        "preview_path": target.get("preview_path"),
        "action": action,
        "work_queue_item_keys": sorted(work_queue),
        "missing_item_keys": sorted(missing),
        "unresolved_item_keys": sorted(unresolved),
    }
    return professor_entry, summary, unmatched


def _single_target(resolution: dict[str, Any]) -> dict[str, Any]:
    targets = resolution.get("targets") or []
    if len(targets) != 1:
        raise ValueError(f"one Stage-1 call resolves exactly one professor, got {len(targets)}")
    return targets[0]


def _state_root(entry: dict[str, Any]) -> dict[str, Any]:
    root = dict(entry)
    root.update({
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "membership_claim": MEMBERSHIP_CLAIM,
        "expansion_policy": EXPANSION_POLICY,
    })
    return root


def build_command(program_root: Path, target_file: Path, named_file: Path | None) -> dict[str, Any]:
    program_root = program_root.resolve()
    resolution = contact_targets.resolve_target(target_file, program_root)
    if resolution.get("status") != "ok":
        emit(resolution)
        raise SystemExit(2)
    target = _single_target(resolution)

    named_by_direction: dict[str, list[str]] = {}
    if named_file is not None:
        owned = {direction["direction_id"] for direction in target.get("directions", [])}
        for direction_id, entries in parse_named_file(named_file).items():
            if direction_id not in owned:
                raise ValueError(f"named-papers reference unknown direction_id: {direction_id}")
            named_by_direction[direction_id] = entries

    entry, summary, unmatched = build_professor_entry(program_root, target, named_by_direction)
    state_path = local_state_path(program_root, str(target.get("professor_dir") or ""))
    root = _state_root(entry)
    problem = validate_local_state(root, state_path, program_root, target)
    if problem is not None:
        raise ValueError(problem)
    atomic_json(state_path, root)

    return {
        "status": "ok",
        "action": summary["action"],
        "snapshot_path": str(state_path),
        "professors": [summary["professor"]],
        "missing_item_keys": summary["missing_item_keys"],
        "unresolved_item_keys": summary["unresolved_item_keys"],
        "unmatched_named_entries": unmatched,
        "per_professor": {
            summary["professor"]: {
                "action": summary["action"],
                "work_queue_item_keys": summary["work_queue_item_keys"],
                "missing_item_keys": summary["missing_item_keys"],
                "unresolved_item_keys": summary["unresolved_item_keys"],
            }
        },
    }


def verify_command(program_root: Path, target_file: Path) -> dict[str, Any]:
    """Read-only consistency check between one professor's state and its inputs.

    Stage 2 consumes the snapshot's candidate sets, so it must verify (not trust)
    that the snapshot exists, is this professor's own authoritative file, covers
    every selected direction, and was built from the current target selection and
    papers state. Never writes, never opens another professor's state.
    """
    program_root = program_root.resolve()
    resolution = contact_targets.resolve_target(target_file, program_root)
    if resolution.get("status") != "ok":
        emit(resolution)
        raise SystemExit(2)
    target = _single_target(resolution)
    name = target.get("professor")
    state_path, entry, problem = read_local_state(program_root, target)
    if problem == "missing_stage1_snapshot":
        emit({"status": "needs_input", "reason_code": "missing_stage1_snapshot",
              "snapshot_path": str(state_path), "professor": name,
              "notes": "run Stage 1 (contact_stage1.py build) first"})
        raise SystemExit(2)
    if problem is not None:
        raise ValueError(problem)

    problems: list[str] = []
    snapshot_directions = {direction.get("direction_id"): direction
                           for direction in entry.get("directions", []) if isinstance(direction, dict)}
    for direction in target.get("directions", []):
        snapshot_direction = snapshot_directions.get(direction.get("direction_id"))
        if snapshot_direction is None:
            problems.append(f"missing_direction:{direction.get('direction_id')}")
            continue
        provisional = sorted({member["item_key"] for member in direction.get("members", [])})
        if not set(provisional) <= set(snapshot_direction.get("candidate_keys") or []):
            problems.append(f"candidate_keys_incomplete:{direction.get('direction_id')}")
    professor_dir = program_root / str(target.get("professor_dir") or "")
    papers_path = professor_dir / "papers.json"
    if not papers_path.is_file():
        problems.append("missing_papers_json")
    preview_path = program_root / str(target.get("preview_path") or "")
    try:
        current_preview = contact_targets.validate_preview(preview_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        problems.append(f"preview_unreadable:{exc}")
        current_preview = None
    if papers_path.is_file() and current_preview is not None:
        # Scope pdf_status to the snapshot's candidate union: a non-candidate
        # paper flipping pdf_status cannot change any Stage-2 input, so it
        # must not invalidate the snapshot. Preview-driven candidate changes
        # are caught by the preview_membership component above.
        snapshot_candidate_keys = {
            key for direction in entry.get("directions", [])
            for key in (direction or {}).get("candidate_keys", [])
        }
        current_fingerprint = input_fingerprint(
            target, current_preview, load_papers(papers_path), snapshot_candidate_keys or None)
        if entry.get("input_fingerprint") != current_fingerprint:
            problems.append("input_fingerprint_mismatch")
    if problems:
        emit({"status": "needs_input", "reason_code": "stale_stage1_snapshot",
              "snapshot_path": str(state_path), "professor": name,
              "stale_professors": [{"professor": name,
                                    "professor_dir": target.get("professor_dir"),
                                    "preview_path": target.get("preview_path"),
                                    "problems": sorted(set(problems))}],
              "notes": "re-run Stage 1 (contact_stage1.py build) before Stage 2"})
        raise SystemExit(2)
    return {"status": "ok", "snapshot_path": str(state_path), "professors": [name]}


def _owner_target(program_root: Path, professor_dir: str) -> dict[str, Any]:
    """The Stage-0 target that proves who owns one legacy aggregate entry."""
    target_path = program_root / professor_dir / contact_targets.TARGET_FILE_NAME
    if not target_path.is_file():
        raise FileNotFoundError(f"no professor-local Stage-0 target at {target_path}")
    target = load_json(target_path)
    if not isinstance(target, dict):
        raise ValueError(f"target state at {target_path} must be an object")
    if (target.get("schema_version") != contact_targets.SCHEMA_VERSION
            or target.get("kind") != contact_targets.KIND):
        raise ValueError(f"unsupported target state schema at {target_path}")
    return target


def migrate_legacy_command(program_root: Path) -> dict[str, Any]:
    """Fan the retired program-level aggregate out into professor-local v2 state.

    This is the only code path that opens the legacy file, and it never writes to
    it: every entry becomes that professor's own state file, existing local state
    is left byte-identical, and one bad entry cannot block the other professors.
    """
    program_root = program_root.resolve()
    legacy_path = program_root / LEGACY_SNAPSHOT_FILE
    migrated: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    if not legacy_path.is_file():
        return {"status": "ok", "legacy_snapshot": str(legacy_path),
                "migrated": migrated, "skipped_existing": skipped, "errors": errors}
    state = load_json(legacy_path)
    if (not isinstance(state, dict) or state.get("kind") != KIND
            or state.get("schema_version") != LEGACY_SCHEMA_VERSION
            or not isinstance(state.get("professors"), list)):
        raise ValueError("legacy stage1 aggregate is not a v1 professors array")
    for item in state["professors"]:
        entry = item if isinstance(item, dict) else {}
        professor = entry.get("professor")
        professor_dir = str(entry.get("professor_dir") or "")
        try:
            target = _owner_target(program_root, professor_dir)
            if target.get("professor") != professor:
                raise ValueError("legacy entry professor does not own the local Stage-0 target")
            if str(target.get("professor_dir") or "") != professor_dir:
                raise ValueError("legacy entry professor_dir does not match the local Stage-0 target")
            state_path = local_state_path(program_root, professor_dir)
            if state_path.is_file():
                existing = load_json(state_path)
                problem = validate_local_state(existing, state_path, program_root, target)
                if problem is not None:
                    raise ValueError(f"existing local stage1 state is not reusable: {problem}")
                skipped.append({"professor": str(professor), "snapshot_path": str(state_path)})
                continue
            root = _state_root(entry)
            problem = validate_local_state(root, state_path, program_root, target)
            if problem is not None:
                raise ValueError(problem)
            atomic_json(state_path, root)
            migrated.append({"professor": str(professor), "snapshot_path": str(state_path)})
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append({"professor": str(professor or ""), "professor_dir": professor_dir,
                           "reason": str(exc)})
    return {"status": "ok" if not errors else "partial", "legacy_snapshot": str(legacy_path),
            "migrated": migrated, "skipped_existing": skipped, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="professor-contact Stage 1 candidate builder")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--program-root", required=True, type=Path)
    build.add_argument("--target-file", required=True, type=Path,
                       help="authoritative professor-local Stage-0 target file")
    build.add_argument("--named-file", default=None, type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("--program-root", required=True, type=Path)
    verify.add_argument("--target-file", required=True, type=Path,
                        help="authoritative professor-local Stage-0 target file")
    migrate = sub.add_parser("migrate-legacy",
                             help="one-off move of the retired program-level snapshot into "
                                  "each professor's own state file; never a runtime path")
    migrate.add_argument("--program-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "build":
            emit(build_command(args.program_root, args.target_file, args.named_file))
            return 0
        if args.command == "verify":
            emit(verify_command(args.program_root, args.target_file))
            return 0
        payload = migrate_legacy_command(args.program_root)
        emit(payload)
        return 0 if payload["status"] == "ok" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        emit({"status": "error", "reason_code": "invalid_stage1_input", "message": str(exc)})
        return 1
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
