#!/usr/bin/env python3
"""Deterministic state runner for professor-contact stages 2-5.

Only local deterministic work: JSON/schema validation, fingerprinting, cache
invalidation, scope selection, stable ordering, version-family heuristics,
state updates, atomic writes, model-job assembly and deterministic Markdown
projection.  Never starts subagents, models, browsers, Zotero or the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = 1
MANAGED_BY = "contact_state"
RESOLVED_DIRECTION_SCHEMA = 1
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
SIDECAR_EXTRACTOR_VERSIONS = ("future-work-v1", "legacy-markdown-v0")
FACTS_SCHEMA = 1
FACTS_KIND = "paper-analysis-facts"
FACTS_GENERATOR_VERSIONS = ("facts-v1",)
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


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(payload: Any) -> str:
    return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def normalized_quote(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip()


def quote_id(value: str) -> str:
    return sha256_text(normalized_quote(value))


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_json_file(path: Path) -> tuple[Any, str | None]:
    try:
        return load_json(path), None
    except FileNotFoundError:
        return None, "not_found"
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return None, f"invalid: {exc}"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_json(path: Path, payload: Any) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n")


def atomic_json_many(items: list[tuple[Path, Any]]) -> None:
    """Replace a small set of JSON files together, restoring old files on error."""
    staged = []
    records = []
    try:
        for path, payload in items:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((path, Path(temporary)))
        for path, temporary in staged:
            backup = None
            record = {"path": path, "temporary": temporary, "backup": backup,
                      "installed": False}
            records.append(record)
            if path.exists():
                fd, backup_name = tempfile.mkstemp(prefix=f".{path.name}.backup.", dir=path.parent)
                os.close(fd)
                backup = Path(backup_name)
                backup.unlink()
                record["backup"] = backup
                os.replace(path, backup)
            os.replace(temporary, path)
            record["installed"] = True
    except BaseException:
        for record in reversed(records):
            path = record["path"]
            try:
                if record["installed"] and path.exists():
                    path.unlink()
                backup = record["backup"]
                if backup and backup.exists():
                    os.replace(backup, path)
            except OSError:
                pass
        for path, temporary in staged:
            temporary.unlink(missing_ok=True)
        raise
    else:
        for record in records:
            backup = record["backup"]
            if backup and backup.exists():
                backup.unlink()
        for path, temporary in staged:
            temporary.unlink(missing_ok=True)


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1))


def fail(reason_code: str, message: str = "", **extra) -> None:
    payload = {"status": "error", "reason_code": reason_code, "message": message}
    payload.update(extra)
    emit(payload)
    sys.exit(1)


def require_professor_dir_under_program(professor_dir: Path, program_root: Path) -> None:
    """Prevent workflow state from being written outside the selected program."""
    allowed = (program_root / "教授研究").resolve()
    actual = professor_dir.resolve()
    try:
        actual.relative_to(allowed)
    except ValueError:
        fail("invalid_professor_dir", "professor_dir must be inside program_root/教授研究",
             professor_dir=str(actual), allowed_root=str(allowed))


def soft_exit(status: str, reason_code: str, **extra) -> None:
    payload = {"status": status, "reason_code": reason_code}
    payload.update(extra)
    emit(payload)
    sys.exit(2)


def truncate(text: str | None, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "…"


def text_tokens(text: str) -> set:
    tokens = set()
    for word in re.findall(r"[A-Za-z0-9]+", text or ""):
        if len(word) >= 3:
            tokens.add(word.lower())
    for run in re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", text or ""):
        for index in range(len(run) - 1):
            tokens.add(run[index:index + 2])
    return tokens


def title_tokens(title: str) -> set:
    return text_tokens(title)


def rel_path(target: Path, base: Path) -> str:
    try:
        return os.path.relpath(str(Path(target).resolve()), str(Path(base).resolve()))
    except ValueError:
        return str(target)


def filename_component(value: Any) -> str:
    raw = unicodedata.normalize("NFKC", str(value or ""))
    cleaned = re.sub(r"[^\w.-]+", "_", raw, flags=re.UNICODE).strip("._")
    return cleaned[:80] or sha256_text(raw)[:12]


def stage5_output_paths(email: dict, emails: list[dict], professor_dir: Path,
                        kind: str = "initial") -> tuple[Path, Path]:
    target_dir = professor_dir.resolve()
    peers = []
    for candidate in emails:
        candidate_dir = Path(candidate.get("professor_dir") or professor_dir).resolve()
        if candidate_dir == target_dir:
            peers.append(candidate)
    prefix = "套磁跟进邮件" if kind == "followup" else "套磁邮件"
    if len(peers) <= 1:
        return professor_dir / f"{prefix}.md", professor_dir / f"{prefix}.txt"
    email_id = str(email.get("email_id") or "email")
    idea_id = (email.get("idea") or {}).get("id") or "email"
    suffix = "_".join((filename_component(email.get("collection_key")),
                         filename_component(idea_id), sha256_text(email_id)[:8]))
    return (professor_dir / f"{prefix}_{suffix}.md",
            professor_dir / f"{prefix}_{suffix}.txt")


def stage5_output_id(email_id: str, kind: str) -> str:
    return email_id if kind == "initial" else f"{email_id}::followup"


def paper_digest(paper: dict) -> str:
    analysis_file = paper.get("analysis_file")
    sidecar_file = paper.get("sidecar_file")
    facts_file = paper.get("facts_file")
    payload = {
        "item_key": paper.get("item_key"),
        "title": paper.get("title"),
        "year": paper.get("year"),
        "month": paper.get("month"),
        "authorship": paper.get("authorship"),
        "abstract_sha": sha256_text(paper.get("abstract") or "") if paper.get("abstract") else None,
        "has_pdf": bool(paper.get("has_pdf")),
        "analysis_sha": sha256_bytes(Path(analysis_file).read_bytes()) if analysis_file and Path(analysis_file).is_file() else None,
        "sidecar_sha": sha256_bytes(Path(sidecar_file).read_bytes()) if sidecar_file and Path(sidecar_file).is_file() else None,
        "facts_sha": sha256_bytes(Path(facts_file).read_bytes()) if facts_file and Path(facts_file).is_file() else None,
    }
    return sha256_obj(payload)


def sidecar_sha(path: str | None) -> str | None:
    if path and Path(path).is_file():
        return sha256_bytes(Path(path).read_bytes())
    return None


def gap_fingerprint(item: dict, sha: str | None) -> str:
    return sha256_obj({
        "quote": unicodedata.normalize("NFKC", item.get("quote") or "").strip(),
        "translation_zh": item.get("translation_zh"),
        "source": item.get("source"),
        "page": item.get("page"),
        "sidecar_sha": sha,
    })


def candidate_fingerprint(candidates: list) -> str:
    return sha256_obj(sorted(candidates, key=lambda c: json.dumps(c, ensure_ascii=False, sort_keys=True)))


def direction_relevant_keys(direction: dict) -> list:
    relevant = direction.get("relevant_keys")
    if relevant:
        return list(relevant)
    return list(direction.get("member_keys") or [])


def direction_candidate_keys(direction: dict) -> list:
    """The full per-direction candidate universe from the Stage 1 snapshot.

    Issue #7 requires every unique candidate paper to get one full
    paper-analysis pass and to be resolvable into/out of the authoritative
    direction from full-text evidence. Relevant keys are the post-relevance
    gap/narrative scope and must NOT bound the resolution evidence — otherwise
    a paper the abstract-level gate dropped can never earn its way back in.
    """
    members = direction.get("member_keys")
    if members:
        return list(members)
    return direction_relevant_keys(direction)


def direction_fingerprint(direction: dict, papers: dict, gap_ids: list, families: dict) -> str:
    relevant = direction_relevant_keys(direction)
    return sha256_obj({
        "collection_key": direction.get("collection_key"),
        "name_ja": direction.get("name_ja"),
        "name_zh": direction.get("name_zh"),
        "status": direction.get("status"),
        "user_note_sha": sha256_text(direction.get("user_note") or ""),
        "member_keys": sorted(direction.get("member_keys") or []),
        "relevant_keys": sorted(relevant),
        "named_keys": sorted(direction.get("named_keys") or []),
        "credibility": direction.get("credibility"),
        "red_lines": direction.get("red_lines") or [],
        "paper_digests": {key: papers[key]["_digest"] for key in sorted(relevant) if key in papers},
        "gap_ids": sorted(set(gap_ids)),
        "version_families": families,
    })


def render_frontmatter(state_fingerprint: str, body_sha: str) -> str:
    return (f"---\nmanaged_by: {MANAGED_BY}\n"
            f"state_fingerprint: {state_fingerprint}\n"
            f"render_sha256: {body_sha}\n---\n\n")


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    header = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            header[key.strip()] = value.strip()
    body_start = end + 5
    if text[body_start:body_start + 1] == "\n":
        body_start += 1
    return header, text[body_start:]


def managed_conflict(path: Path, body: str, previous_sha: str | None,
                     decision: str | None) -> dict | None:
    body_sha = sha256_text(body)
    if path.is_file():
        _, existing_body = split_frontmatter(path.read_text(encoding="utf-8"))
        existing_sha = sha256_text(existing_body)
        if existing_sha != body_sha and previous_sha and existing_sha != previous_sha:
            if decision != "overwrite":
                return {"written": False, "needs_decision": True,
                        "reason_code": "manual_markdown_changed",
                        "target": str(path),
                        "existing_sha256": existing_sha, "new_sha256": body_sha}
    return None


def managed_write(path: Path, body: str, state_fingerprint: str,
                  previous_sha: str | None, decision: str | None) -> dict:
    body_sha = sha256_text(body)
    conflict = managed_conflict(path, body, previous_sha, decision)
    if conflict:
        return conflict
    atomic_write(path, render_frontmatter(state_fingerprint, body_sha) + body)
    return {"written": True, "needs_decision": False, "sha256": body_sha}


def managed_write_raw(path: Path, body: str, previous_sha: str | None,
                      decision: str | None) -> dict:
    body_sha = sha256_text(body)
    if path.is_file():
        existing_sha = sha256_text(path.read_text(encoding="utf-8"))
        if existing_sha != body_sha and previous_sha and existing_sha != previous_sha:
            if decision != "overwrite":
                return {"written": False, "needs_decision": True,
                        "reason_code": "manual_markdown_changed", "target": str(path),
                        "existing_sha256": existing_sha, "new_sha256": body_sha}
    atomic_write(path, body)
    return {"written": True, "needs_decision": False, "sha256": body_sha}


def projection_conflict(path: Path, body: str, projections: dict, key: str) -> dict | None:
    body_sha = sha256_text(body)
    previous = (projections or {}).get("render", {}).get(key, {}).get("sha256")
    if path.is_file():
        _, existing_body = split_frontmatter(path.read_text(encoding="utf-8"))
        existing_sha = sha256_text(existing_body)
        if existing_sha != body_sha and previous and existing_sha != previous:
            return {"written": False, "needs_decision": True,
                    "reason_code": "manual_markdown_changed", "target": str(path)}
    return None


def projection_write(path: Path, body: str, projections: dict, key: str) -> dict:
    conflict = projection_conflict(path, body, projections, key)
    if conflict:
        return conflict
    body_sha = sha256_text(body)
    projection_fingerprint = sha256_obj({"projection": key, "body": body_sha})
    atomic_write(path, render_frontmatter(projection_fingerprint, body_sha) + body)
    return {"written": True, "needs_decision": False, "sha256": body_sha}


def load_projections(program_root: Path) -> dict:
    data, error = read_json_file(program_root / "教授研究" / PROJECTIONS_FILE)
    if error or not isinstance(data, dict):
        return {"render": {}}
    data.setdefault("render", {})
    return data


def save_projections(program_root: Path, projections: dict) -> None:
    atomic_json(program_root / "教授研究" / PROJECTIONS_FILE, projections)


def sidecar_analysis_matches(recorded: Any, expected_analysis: str) -> bool:
    """Bind a sidecar's `analysis` field to the analysis it belongs to.

    Canonical paper-analysis sidecars record the basename (`analysis.name` in
    both `future_work.py` and `facts.py`); legacy sidecars recorded the absolute
    analysis path. This binds only the recorded field: the physical sidecar
    location is bound separately by the sibling-path check in the loaders, which
    is what keeps same-basename analyses in different directories apart.
    """
    if not isinstance(recorded, str) or not recorded.strip():
        return False
    path = Path(recorded.strip())
    if path.is_absolute():
        try:
            return path.resolve() == Path(expected_analysis).resolve()
        except OSError:
            return False
    return len(path.parts) == 1 and path.name == Path(expected_analysis).name


def sidecar_path_matches(path: Path, expected_analysis: str, suffix: str) -> bool:
    """Require the sidecar file to be the analysis's exact sibling on disk.

    `<analysis>.future_work.json` / `<analysis>.facts.json` are written next to
    their analysis by every paper-analysis writer. Accepting any other location
    would let a mis-assembled sidecar reference lend one analysis's evidence to
    another with the same basename.
    """
    expected_sibling = Path(str(expected_analysis) + suffix)
    try:
        return path.resolve() == expected_sibling.resolve()
    except OSError:
        return False


def load_sidecar(path: str | None, expected_analysis: str | None = None) -> tuple[list, list, str | None]:
    """Return (anchorable_items, legacy_items, error).

    With `expected_analysis`, the sidecar must be that analysis's exact
    `<analysis>.future_work.json` sibling and its recorded `analysis` field must
    bind to the same analysis.
    """
    if not path:
        return [], [], None
    sidecar_path = Path(path)
    if not sidecar_path.is_file():
        return [], [], "missing"
    data, error = read_json_file(sidecar_path)
    if error:
        return [], [], "invalid"
    if not isinstance(data, dict) or data.get("schema") != 1 or data.get("status") != "ok":
        return [], [], "invalid"
    extractor_version = data.get("extractor_version")
    if extractor_version not in SIDECAR_EXTRACTOR_VERSIONS:
        return [], [], "invalid"
    if expected_analysis:
        if not sidecar_path_matches(sidecar_path, expected_analysis, ".future_work.json"):
            return [], [], "invalid"
        if not sidecar_analysis_matches(data.get("analysis"), expected_analysis):
            return [], [], "invalid"
    elif not isinstance(data.get("analysis"), str) or not data["analysis"].strip():
        return [], [], "invalid"
    items = data.get("items")
    if not isinstance(items, list):
        return [], [], "invalid"
    anchorable, legacy = [], []
    seen_ids = set()
    for item in items:
        if not isinstance(item, dict):
            return [], [], "invalid"
        gap_id = item.get("id")
        quote = item.get("quote")
        if not isinstance(gap_id, str) or not re.fullmatch(r"[0-9a-f]{64}", gap_id or ""):
            return [], [], "invalid"
        if gap_id in seen_ids:
            return [], [], "invalid"
        seen_ids.add(gap_id)
        if not isinstance(quote, str) or not quote.strip():
            return [], [], "invalid"
        if gap_id != quote_id(quote):
            return [], [], "invalid"
        if not isinstance(item.get("translation_zh"), str) or not item["translation_zh"].strip():
            return [], [], "invalid"
        if not isinstance(item.get("source"), str) or not item["source"].strip():
            return [], [], "invalid"
        record = {
            "gap_id": gap_id,
            "quote": quote,
            "translation_zh": item["translation_zh"].strip(),
            "source": item["source"].strip(),
            "page": item.get("page"),
        }
        if isinstance(item.get("page"), bool) or (item.get("page") is not None and
                                                   not isinstance(item.get("page"), int)):
            return [], [], "invalid"
        if isinstance(item.get("page"), int) and item["page"] >= 1:
            anchorable.append(record)
        else:
            legacy.append(record)
    return anchorable, legacy, None


def load_facts_sidecar(
    facts_file: str | None,
    expected_analysis: str | None,
    pdf_file: str | None,
    valid_gap_ids: set | None,
) -> tuple[dict | None, str, str | None]:
    """Validate a paper-analysis `<analysis>.facts.json` sidecar for reuse.

    Returns (normalized_facts, facts_state, facts_error). The sidecar is only
    reusable when it is the analysis's exact `.facts.json` sibling, its
    schema/generator are known, it names the current analysis, its
    `input_fingerprint` matches the sha256 of the current source PDF, and its
    `future_work_ids` are exact joins into the current valid future-work sidecar
    (which stays the authoritative quoted evidence). Any mismatch fails closed:
    no normalized facts are exposed and the caller must not re-derive them with
    another model pass.
    """
    if not facts_file:
        return None, "unavailable", "missing_facts_sidecar"
    path = Path(facts_file)
    if not path.is_file():
        return None, "unavailable", "missing_facts_sidecar"
    data, error = read_json_file(path)
    if error or not isinstance(data, dict):
        return None, "failed", "invalid_facts_sidecar"
    if (data.get("schema") != FACTS_SCHEMA or data.get("kind") != FACTS_KIND
            or data.get("status") != "ok"
            or data.get("generator_version") not in FACTS_GENERATOR_VERSIONS
            or data.get("evidence_level") != "fulltext"):
        return None, "failed", "invalid_facts_sidecar"
    if expected_analysis and not sidecar_path_matches(path, expected_analysis, ".facts.json"):
        return None, "failed", "invalid_facts_sidecar"
    recorded_analysis = data.get("analysis")
    if not isinstance(recorded_analysis, str) or not recorded_analysis.strip():
        return None, "failed", "invalid_facts_sidecar"
    if expected_analysis and not sidecar_analysis_matches(recorded_analysis, expected_analysis):
        return None, "failed", "invalid_facts_sidecar"
    for field in FACTS_TEXT_FIELDS:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return None, "failed", "invalid_facts_sidecar"
    for field in FACTS_LIST_FIELDS:
        value = data.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            return None, "failed", "invalid_facts_sidecar"
    anchors = data.get("source_anchors")
    if anchors is not None and not isinstance(anchors, dict):
        return None, "failed", "invalid_facts_sidecar"
    confidence = data.get("confidence")
    if confidence is not None and (not isinstance(confidence, (int, float))
                                   or isinstance(confidence, bool) or not 0 <= confidence <= 1):
        return None, "failed", "invalid_facts_sidecar"
    fingerprint = data.get("input_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint.startswith("sha256:"):
        return None, "failed", "invalid_facts_sidecar"
    if not pdf_file or not Path(pdf_file).is_file():
        return None, "failed", "facts_source_fingerprint_mismatch"
    current = "sha256:" + sha256_bytes(Path(pdf_file).read_bytes())
    if fingerprint != current:
        return None, "failed", "facts_source_fingerprint_mismatch"
    joined_ids = data.get("future_work_ids")
    if (not isinstance(joined_ids, list)
            or any(not isinstance(gap_id, str) or not re.fullmatch(r"[0-9a-f]{64}", gap_id) for gap_id in joined_ids)
            or len(set(joined_ids)) != len(joined_ids)):
        return None, "failed", "invalid_facts_sidecar"
    if valid_gap_ids is None or not set(joined_ids).issubset(valid_gap_ids):
        return None, "failed", "facts_future_work_join_mismatch"
    normalized = {
        "facts_file": str(path),
        "evidence_level": "fulltext",
        "input_fingerprint": fingerprint,
        "research_problem": data["research_problem"].strip(),
        "research_object": data["research_object"].strip(),
        "approach": data["approach"].strip(),
        "findings": [item.strip() for item in data["findings"]],
        "contributions": [item.strip() for item in data["contributions"]],
        "topic_terms": [item.strip() for item in data["topic_terms"]],
        "limitations": [item.strip() for item in data["limitations"]],
        "source_anchors": anchors or {},
        "confidence": float(confidence) if confidence is not None else None,
        "future_work_ids": list(joined_ids),
    }
    return normalized, "valid", None


def compute_version_families(papers: dict) -> dict:
    confirmed, possible = [], []
    keys = sorted(papers)
    for index, left in enumerate(keys):
        for right in keys[index + 1:]:
            early, late = papers[left], papers[right]
            ey, em = early.get("year") or 0, early.get("month") or 0
            ly, lm = late.get("year") or 0, late.get("month") or 0
            if not (ly, lm) > (ey, em):
                continue
            early_tokens = title_tokens(early.get("title") or "")
            late_tokens = title_tokens(late.get("title") or "")
            denominator = min(len(early_tokens), len(late_tokens)) or 1
            overlap = len(early_tokens & late_tokens) / denominator
            early_authors = {a.lower() for a in (early.get("authors") or [])}
            late_authors = {a.lower() for a in (late.get("authors") or [])}
            author_overlap = None
            if early_authors and late_authors:
                author_overlap = len(early_authors & late_authors) / min(len(early_authors), len(late_authors))
            explicit = bool(EXT_EVIDENCE_RE.search(late.get("abstract") or ""))
            base = {"family_id": f"vf:{left}+{right}", "members": [left, right],
                    "primary": right, "role": {left: "preliminary", right: "journal_ext"},
                    "title_overlap": round(overlap, 2)}
            if overlap >= 0.4 and explicit and (author_overlap is None or author_overlap >= 0.5):
                base["evidence"] = "题名词重叠＋时间顺序＋后续摘要明示扩展"
                confirmed.append(base)
            elif overlap >= 0.4:
                base["evidence"] = "题名词重叠＋时间顺序（扩展证据不足）"
                possible.append(base)
    return {"confirmed": confirmed, "possible": possible}


def score_gap(gap: dict, current_year: int) -> int:
    score = 0
    if gap.get("named_by_user"):
        score += 30
    if gap.get("relevant"):
        score += 10
    score += AUTHORSHIP_RANK.get(gap.get("authorship"), 0)
    year = gap.get("paper_year") or 0
    if year:
        score += max(0, 10 - (current_year - year))
    if gap.get("quote") and gap.get("translation_zh") and gap.get("page"):
        score += 5
    if gap.get("family_primary_confirmed"):
        score += 5
    return score


def rank_gaps(gaps: list, current_year: int) -> list:
    for gap in gaps:
        gap["_score"] = score_gap(gap, current_year)
    return sorted(gaps, key=lambda g: (-g["_score"], -(g.get("paper_year") or 0),
                                       g.get("item_key") or "", g.get("gap_id") or ""))


def shortlist_size(pool_size: int) -> int:
    if pool_size >= SHORTLIST_FLOOR:
        return min(SHORTLIST_MAX, pool_size)
    return pool_size


def is_later_or_same_unknown(paper: dict, source: dict) -> bool:
    py, pm = paper.get("year"), paper.get("month")
    sy, sm = source.get("year"), source.get("month")
    if not isinstance(py, int) or not isinstance(sy, int):
        return False
    if py > sy:
        return True
    if py < sy or paper.get("item_key") == source.get("item_key"):
        return False
    # A same-year paper is only later when both publication months are known.
    return isinstance(pm, int) and isinstance(sm, int) and pm > sm


def gap_related(gap: dict, paper: dict) -> bool:
    gap_tokens = text_tokens(gap.get("quote") or "") | text_tokens(gap.get("translation_zh") or "")
    paper_tokens = text_tokens(paper.get("title") or "") | text_tokens((paper.get("abstract") or "")[:600])
    return len(gap_tokens & paper_tokens) >= 2


def freshness_candidates(gap: dict, source_paper: dict, library: dict,
                         current_year: int, family_members: set, history_refs: set) -> dict:
    tiers = {"confirmed_family": [], "authorship": [], "recent": [], "topic": []}
    excluded_no_clue = 0
    later_total = 0
    for key in sorted(library):
        paper = library[key]
        if key == source_paper.get("item_key") or not is_later_or_same_unknown(paper, source_paper):
            continue
        later_total += 1
        if key in family_members:
            tier = "confirmed_family"
        elif paper.get("year") and current_year - paper["year"] <= 3 and \
                paper.get("authorship") in ("corresponding", "solo", "first"):
            tier = "authorship"
        elif paper.get("year") and current_year - paper["year"] <= 3 and \
                paper.get("authorship") in ("pending", "middle"):
            tier = "recent"
        elif key in history_refs or gap_related(gap, paper):
            tier = "topic"
        else:
            excluded_no_clue += 1
            continue
        tiers[tier].append(key)
    return {"tiers": tiers, "later_total": later_total, "excluded_no_clue": excluded_no_clue}


def load_freshness_cache(professor_dir: Path) -> dict:
    data, error = read_json_file(professor_dir / FRESHNESS_CACHE)
    if error or not isinstance(data, dict):
        return {}
    return data.get("entries") or {}


def save_freshness_cache(professor_dir: Path, entries: dict) -> None:
    atomic_json(professor_dir / FRESHNESS_CACHE, {
        "schema": SCHEMA, "managed_by": MANAGED_BY, "entries": entries})


def gap_scope_keys(facts: dict, direction: dict) -> list:
    scope = (facts.get("params") or {}).get("gap_scope") or "selected_direction"
    if scope == "all":
        return sorted({p.get("item_key") for p in facts.get("papers", []) if p.get("item_key")})
    if scope == "relevant":
        return direction_relevant_keys(direction)
    return list(direction.get("member_keys") or [])


def load_papers_with_digests(facts: dict) -> dict:
    papers = {}
    for paper in facts.get("papers", []):
        key = paper.get("item_key")
        if not key:
            continue
        record = dict(paper)
        record["_digest"] = paper_digest(record)
        papers[key] = record
    return papers


def build_gap_pool(facts: dict, papers: dict, families: dict,
                   sidecar_cache: dict) -> tuple[dict, dict]:
    """Build per-direction anchorable gap pools from valid sidecars."""
    confirmed_members = {}
    for family in families.get("confirmed", []):
        for member in family["members"]:
            confirmed_members.setdefault(member, set()).update(family["members"])
    pools = {}
    for direction in facts.get("directions", []):
        scope = gap_scope_keys(facts, direction)
        gaps = []
        for key in sorted(scope):
            paper = papers.get(key)
            if not paper:
                continue
            sidecar_file = paper.get("sidecar_file")
            if not sidecar_file:
                continue
            if sidecar_file not in sidecar_cache:
                sha = sidecar_sha(sidecar_file)
                items, legacy_items, error = load_sidecar(sidecar_file, paper.get("analysis_file"))
                sidecar_cache[sidecar_file] = (items, legacy_items, error, sha)
            items, legacy_items, error, sha = sidecar_cache[sidecar_file]
            if error:
                continue
            for item in items:
                gaps.append({
                    "gap_id": item["gap_id"], "item_key": key,
                    "paper_title": paper.get("title"), "paper_year": paper.get("year"),
                    "authorship": paper.get("authorship"),
                    "quote": item["quote"], "translation_zh": item["translation_zh"],
                    "source": item["source"], "page": item["page"],
                    "named_by_user": key in (direction.get("named_keys") or []),
                    "relevant": True,
                    "family_primary_confirmed": any(
                        f["primary"] == key for f in families.get("confirmed", [])),
                    "sidecar_sha": sha})
        duplicate_ids = {}
        for gap in gaps:
            duplicate_ids.setdefault(gap["gap_id"], []).append(gap)
        suppressed = set()
        for gap_id, group in duplicate_ids.items():
            if len(group) > 1:
                group_sorted = sorted(group, key=lambda g: (0 if g["family_primary_confirmed"] else 1,
                                                            g["item_key"]))
                for loser in group_sorted[1:]:
                    loser["suppressed_by"] = group_sorted[0]["item_key"]
                    suppressed.add(id(loser))
        pools[direction["collection_key"]] = [g for g in gaps if id(g) not in suppressed]
    return pools, confirmed_members


class Stage2Context:
    """Everything plan and finalize need, computed once from the facts file."""

    def __init__(self, facts_path: Path):
        self.facts_path = facts_path
        data, error = read_json_file(facts_path)
        if error:
            fail("invalid_facts", f"facts file unreadable: {error}")
        self.facts = data
        self.professor = self.facts.get("professor") or fail("invalid_facts", "facts.professor missing")
        self.professor_dir = Path(self.facts.get("professor_dir") or fail("invalid_facts", "facts.professor_dir missing"))
        self.program_root = Path(self.facts.get("program_root") or (self.professor_dir.parent.parent))
        self.current_year = int(self.facts.get("current_year") or datetime.now().year)
        params = self.facts.get("params") or {}
        self.gap_scope = params.get("gap_scope") or "selected_direction"
        self.freshness_scope = params.get("freshness_scope") or "shortlist"
        if self.gap_scope not in GAP_SCOPES:
            fail("invalid_params", f"gap_scope must be one of {GAP_SCOPES}")
        if self.freshness_scope not in FRESHNESS_SCOPES:
            fail("invalid_params", f"freshness_scope must be one of {FRESHNESS_SCOPES}")
        self.papers = load_papers_with_digests(self.facts)
        self.sidecar_cache = {}
        self.facts_cache = {}
        self.families = compute_version_families(self.papers)
        self.pools, self.family_members = build_gap_pool(self.facts, self.papers, self.families, self.sidecar_cache)
        self.pack_path = self.professor_dir / INPUT_PACK
        self.pack, _ = read_json_file(self.pack_path)
        if not isinstance(self.pack, dict):
            self.pack = None
        self.cache = load_freshness_cache(self.professor_dir)
        self.direction_plans = []
        self._prepare_directions()

    def _prepare_directions(self) -> None:
        old_directions = {}
        if self.pack:
            for entry in self.pack.get("directions", []):
                old_directions[entry.get("collection_key")] = entry
        for direction in self.facts.get("directions", []):
            ckey = direction.get("collection_key") or fail("invalid_facts", "direction.collection_key missing")
            pool = self.pools.get(ckey, [])
            ranked = rank_gaps([dict(g) for g in pool], self.current_year)
            fingerprint = direction_fingerprint(
                direction, self.papers, [g["gap_id"] for g in pool], self.families)
            old = old_directions.get(ckey)
            old_narrative = (old or {}).get("narrative") or {}
            old_blocks = [b for b in old_narrative.get("positioning", []) if isinstance(b, dict)]
            narrative_has_examples = bool(old_blocks) and all(
                all(isinstance(b.get(field), str) and b[field].strip()
                    for field in ("concrete_object", "input_example", "output_example"))
                for b in old_blocks)
            # Stage-2 internal freshness is judged against the PROVISIONAL
            # fingerprint. Once a resolution has been applied, the pack keeps it
            # in `provisional_input_fingerprint` because the public
            # `input_fingerprint` is recomputed to the resolved-aware downstream
            # value that Stage 3's reuse gate consumes.
            old_provisional_fp = (old or {}).get("provisional_input_fingerprint",
                                                 (old or {}).get("input_fingerprint"))
            reuse = bool(old and old_provisional_fp == fingerprint and narrative_has_examples)
            plan_entry = {
                "direction": direction, "ckey": ckey, "pool": pool, "ranked": ranked,
                "fingerprint": fingerprint, "old": old, "reuse": reuse,
            }
            if reuse and self.freshness_stale(plan_entry):
                plan_entry["reuse"] = False
            self.direction_plans.append(plan_entry)

    def freshness_stale(self, plan: dict) -> bool:
        for gap in self.judge_set(plan):
            item, _hit = self.freshness_entry(plan, gap)
            if not item.get("cached"):
                return True
        return False

    def facts_for(self, key: str) -> tuple[dict | None, str, str | None]:
        """Validated normalized paper facts for one paper (memoized).

        Reuse requires the current valid future-work sidecar: its item ids stay
        the authoritative quoted evidence and `facts.future_work_ids` may only
        exact-join into them. A paper without a facts sidecar is honestly
        "unavailable"; a facts sidecar whose evidence chain (valid sidecar,
        fingerprint, joins) is broken fails closed.
        """
        paper = self.papers.get(key)
        if not paper:
            return None, "unavailable", "missing_facts_sidecar"
        cached = self.facts_cache.get(key)
        if cached is not None:
            return cached
        if not paper.get("facts_file"):
            record = (None, "unavailable", "missing_facts_sidecar")
        else:
            sidecar_file = paper.get("sidecar_file")
            valid_ids: set | None = None
            if sidecar_file:
                if sidecar_file not in self.sidecar_cache:
                    sha = sidecar_sha(sidecar_file)
                    items, legacy_items, error = load_sidecar(sidecar_file, paper.get("analysis_file"))
                    self.sidecar_cache[sidecar_file] = (items, legacy_items, error, sha)
                items, legacy_items, error, _sha = self.sidecar_cache[sidecar_file]
                if not error:
                    valid_ids = {item["gap_id"] for item in items} | {item["gap_id"] for item in legacy_items}
            if valid_ids is None:
                record = (None, "failed", "facts_future_work_join_mismatch")
            else:
                record = load_facts_sidecar(
                    paper.get("facts_file"), paper.get("analysis_file"),
                    paper.get("pdf_file"), valid_ids)
        self.facts_cache[key] = record
        return record

    def freshness_entry(self, plan: dict, gap: dict):
        source = self.papers.get(gap["item_key"], {})
        cands = freshness_candidates(
            gap, source, self.papers, self.current_year,
            self.family_members.get(gap["item_key"], set()),
            self.history_refs(gap))
        gap_fp = gap_fingerprint(gap, gap.get("sidecar_sha"))
        cand_list = [
            {"item_key": key, "digest": self.papers[key]["_digest"]}
            for key in
            cands["tiers"]["confirmed_family"] + cands["tiers"]["authorship"] +
            cands["tiers"]["recent"] + cands["tiers"]["topic"]]
        cand_fp = candidate_fingerprint(cand_list)
        entry = self.cache.get(gap["gap_id"])
        if entry and entry.get("gap_fingerprint") == gap_fp and \
                entry.get("candidate_fingerprint") == cand_fp and \
                entry.get("status") in GAP_STATUSES:
            status = dict(entry)
            status["cache_hit"] = True
            return {"gap": gap, "status": status, "cands": cands,
                    "gap_fp": gap_fp, "cand_fp": cand_fp, "cached": True}, 1
        return {"gap": gap, "status": None, "cands": cands,
                "gap_fp": gap_fp, "cand_fp": cand_fp, "cached": False}, 0

    def judge_set(self, plan: dict) -> list:
        ranked = plan["ranked"]
        if self.freshness_scope == "shortlist":
            return ranked[:shortlist_size(len(ranked))]
        return list(ranked)

    def freshness_job_items(self, plan: dict) -> tuple[list, list, int]:
        """Return (job gap items, cache-hit statuses, hit count)."""
        jobs, hits = [], 0
        for gap in self.judge_set(plan):
            item, hit = self.freshness_entry(plan, gap)
            hits += hit
            jobs.append(item)
        return jobs, hits

    def history_refs(self, gap: dict) -> set:
        entry = self.cache.get(gap.get("gap_id")) or {}
        return set(entry.get("candidate_paper_ids") or [])

    def narrative_later_keys(self, plan: dict) -> list[str]:
        keys = set()
        for gap in plan["ranked"]:
            source = self.papers.get(gap["item_key"], {})
            candidates = freshness_candidates(
                gap, source, self.papers, self.current_year,
                self.family_members.get(gap["item_key"], set()),
                self.history_refs(gap))
            for tier in candidates["tiers"].values():
                keys.update(tier)
        return sorted(keys)

    def narrative_needed(self, plan: dict) -> bool:
        return not plan["reuse"]


class Stage2PackRefineContext:
    """Read-only context for repairing an accepted pack when /tmp facts expired."""

    def __init__(self, professor_dir: Path):
        self.professor_dir = professor_dir
        self.pack_path = professor_dir / INPUT_PACK
        self.pack, error = read_json_file(self.pack_path)
        if error or not isinstance(self.pack, dict):
            fail("missing_input_pack", f"input pack unreadable: {self.pack_path}")
        self.professor = self.pack.get("professor") or fail("invalid_facts", "input pack.professor missing")
        self.current_year = datetime.now().year
        self.papers = {}
        self.direction_plans = []
        for direction in self.pack.get("directions", []):
            ckey = direction.get("collection_key")
            if not ckey:
                fail("invalid_facts", "input pack direction.collection_key missing")
            for paper in direction.get("supporting_papers", []):
                key = paper.get("item_key")
                if key:
                    self.papers.setdefault(key, {
                        "item_key": key, "title": paper.get("title"),
                        "year": paper.get("year"), "authorship": paper.get("authorship"),
                        "analysis_file": paper.get("analysis_file")})
            for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
                key = gap.get("item_key")
                if key:
                    self.papers.setdefault(key, {
                        "item_key": key, "title": gap.get("paper_title"),
                        "year": gap.get("paper_year"), "authorship": gap.get("authorship")})
            for key in self.narrative_later_keys_for(direction):
                self.papers.setdefault(key, {"item_key": key, "title": "后续论文"})
            gaps = [dict(gap) for gap in direction.get("gap_shortlist", [])]
            gaps.extend(dict(gap) for gap in direction.get("gaps_excluded", []))
            self.direction_plans.append({
                "ckey": ckey,
                "direction": {"relevant_keys": [p.get("item_key") for p in direction.get("supporting_papers", [])],
                               "member_keys": [p.get("item_key") for p in direction.get("supporting_papers", [])],
                               "named_keys": []},
                "ranked": [gap for gap in gaps if gap.get("gap_id")],
            })

    @staticmethod
    def narrative_later_keys_for(direction: dict) -> list[str]:
        keys = set()
        narrative = direction.get("narrative") or {}
        for block in narrative.get("positioning", []):
            for kind, value in PLACEHOLDER_RE.findall(block.get("text") or ""):
                if kind == "L":
                    keys.add(value)
        return sorted(keys)

    def narrative_later_keys(self, plan: dict) -> list[str]:
        direction = next((d for d in self.pack.get("directions", [])
                          if d.get("collection_key") == plan["ckey"]), {})
        return self.narrative_later_keys_for(direction)


def _compute_paper_direction_affinity(ctx: Stage2Context) -> dict[str, dict[str, float]]:
    """Compute per-paper affinity scores to each provisional direction using full-text facts.

    Returns {item_key: {ckey: score}} where score is derived from:
    - paper_facts.topic_terms overlap with direction profile (name_ja/name_zh/summary_zh)
    - authorship weight (first/corresponding/solo > pending > middle)
    - whether the paper contributes gaps to the direction
    """
    import re as _re
    import unicodedata as _ud

    def _tokens(text: str) -> set:
        toks = set()
        for w in _re.findall(r"[A-Za-z0-9]+", text or ""):
            if len(w) >= 3:
                toks.add(w.lower())
        for run in _re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", text or ""):
            for i in range(len(run) - 1):
                toks.add(run[i:i + 2])
        return toks

    direction_profiles: dict[str, set] = {}
    for plan in ctx.direction_plans:
        direction = plan["direction"]
        parts = []
        for field in ("name_ja", "name_zh", "summary_zh"):
            val = direction.get(field)
            if isinstance(val, str) and val.strip():
                parts.append(val)
        direction_profiles[plan["ckey"]] = _tokens(" ".join(parts))

    affinity: dict[str, dict[str, float]] = {}
    for plan in ctx.direction_plans:
        ckey = plan["ckey"]
        profile_toks = direction_profiles[ckey]
        gap_item_keys = {g["item_key"] for g in plan["pool"]}
        # Affinity is resolution evidence: it must cover the full candidate
        # universe so a paper the abstract relevance gate dropped can still be
        # scored against every direction from full-text facts.
        for key in direction_candidate_keys(plan["direction"]):
            paper = ctx.papers.get(key)
            if not paper:
                continue
            score = 0.0
            # Base affinity from provisional membership
            if key in (plan["direction"].get("provisional_member_keys") or []):
                score += 2.0
            # Authorship weight
            auth = paper.get("authorship", "pending")
            score += AUTHORSHIP_RANK.get(auth, 0) / 5.0
            # Gap contribution: paper contributes future-work to this direction
            if key in gap_item_keys:
                score += 1.5
            # Topic overlap from full-text facts
            facts_record, _, _ = ctx.facts_for(key)
            if facts_record:
                topic_terms = facts_record.get("topic_terms") or []
                paper_toks = _tokens(" ".join(str(t) for t in topic_terms))
                if profile_toks and paper_toks:
                    overlap = len(paper_toks & profile_toks)
                    score += overlap * 0.3
            # Title overlap as fallback when no facts
            elif paper.get("title"):
                title_toks = _tokens(paper["title"])
                if profile_toks and title_toks:
                    overlap = len(title_toks & profile_toks)
                    score += overlap * 0.2
            affinity.setdefault(key, {})[ckey] = round(score, 3)
    return affinity


def _detect_candidates_for_addition(ctx: Stage2Context, affinity: dict[str, dict[str, float]]) -> list[dict]:
    """Detect papers whose full-text evidence points to a different direction than their provisional one.

    Paper-centric: for every paper, if the strongest-affinity direction is NOT
    the paper's current provisional direction, the paper is a cross-cluster
    candidate that the strongest direction should add. The target direction is
    the strongest full-text direction (not the iteration variable), so the
    addition always points where the evidence actually points.

    A candidate is emitted when:
    - paper has a non-zero affinity score to at least one direction
    - the strongest-affinity direction is different from the paper's provisional direction
      (resolved from any selected direction the paper belongs to)
    - the affinity gap between top and provisional is significant (>= 1.0)
    - the paper is reachable in the candidate union (member_keys) of the target
    """
    # Build map of paper -> provisional directions (any selected direction whose
    # provisional_member_keys contain the paper).
    paper_provisional: dict[str, list[str]] = {}
    candidate_unions: dict[str, set[str]] = {}
    for plan in ctx.direction_plans:
        ckey = plan["ckey"]
        candidate_unions[ckey] = set(plan["direction"].get("member_keys") or [])
        for key in plan["direction"].get("provisional_member_keys") or []:
            paper_provisional.setdefault(key, []).append(ckey)

    additions = []
    seen: set[tuple[str, str]] = set()
    for key, paper_aff in affinity.items():
        if not paper_aff:
            continue
        sorted_dirs = sorted(paper_aff.items(), key=lambda x: x[1], reverse=True)
        if not sorted_dirs:
            continue
        top_ckey, top_score = sorted_dirs[0]
        provisional_dirs = paper_provisional.get(key, [])
        # If the strongest direction IS the paper's provisional direction, no
        # cross-cluster addition is needed.
        if top_ckey in provisional_dirs:
            continue
        # Find this paper's current (weaker) provisional direction score, if any.
        provisional_scores = [paper_aff.get(d, 0) for d in provisional_dirs]
        max_provisional = max(provisional_scores) if provisional_scores else 0
        if top_score <= max_provisional + 1.0:
            continue
        # The paper must be reachable from the strongest direction's candidate union
        # (or it has no provisional place, which is the new-direction case).
        if top_ckey not in candidate_unions and provisional_dirs:
            continue
        # Avoid duplicate (paper, target) entries when iterating multi-direction plans.
        if (key, top_ckey) in seen:
            continue
        seen.add((key, top_ckey))
        additions.append({
            "item_key": key,
            "target_direction": top_ckey,
            "current_provisional_direction": provisional_dirs[0] if provisional_dirs else None,
            "target_score": top_score,
            "provisional_score": max_provisional,
            "reason": (
                f"paper full-text affinity strongest in {top_ckey}={top_score} "
                f"vs provisional={max_provisional} ({provisional_dirs[0] if provisional_dirs else 'none'})"
            ),
        })
    return additions


def _detect_candidates_for_removal(ctx: Stage2Context, affinity: dict[str, dict[str, float]]) -> list[dict]:
    """Detect provisional members that full-text evidence suggests don't belong.

    A candidate for removal when:
    - paper is a provisional member
    - paper has full-text facts with topic_terms that don't overlap direction profile

    Note: gap contribution does NOT prevent removal — a paper can contribute a
    relevant gap to a direction without being a member of that direction.
    Removal only affects membership, not gap provenance.
    """
    import re as _re
    removals = []
    for plan in ctx.direction_plans:
        ckey = plan["ckey"]
        direction = plan["direction"]
        profile_parts = []
        for field in ("name_ja", "name_zh", "summary_zh"):
            val = direction.get(field)
            if isinstance(val, str) and val.strip():
                profile_parts.append(val)
        profile_text = " ".join(profile_parts).lower()
        # Also build a set of profile tokens for more flexible matching
        profile_toks = set()
        for w in _re.findall(r"[A-Za-z0-9]+", profile_text):
            if len(w) >= 3:
                profile_toks.add(w.lower())
        for run in _re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", profile_text):
            for i in range(len(run) - 1):
                profile_toks.add(run[i:i + 2])
        for key in direction.get("provisional_member_keys") or []:
            paper = ctx.papers.get(key)
            if not paper:
                continue
            facts_record, facts_state, _ = ctx.facts_for(key)
            if facts_state != "valid":
                continue  # can't judge without full-text facts
            topic_terms = (facts_record or {}).get("topic_terms") or []
            title = (paper.get("title") or "").lower()
            # Check if any topic term or title token overlaps with direction profile
            has_overlap = False
            for term in topic_terms:
                term_lower = str(term).lower()
                if term_lower in profile_text:
                    has_overlap = True
                    break
                # Check token-level overlap for multi-word terms
                for tok in _re.findall(r"[A-Za-z0-9]+", term_lower):
                    if len(tok) >= 3 and tok in profile_toks:
                        has_overlap = True
                        break
                if has_overlap:
                    break
            if not has_overlap:
                # Check title tokens against profile tokens
                title_toks = set()
                for w in _re.findall(r"[A-Za-z0-9]+", title):
                    if len(w) >= 3:
                        title_toks.add(w.lower())
                for run in _re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", title):
                    for i in range(len(run) - 1):
                        title_toks.add(run[i:i + 2])
                if title_toks and profile_toks and title_toks & profile_toks:
                    has_overlap = True
            if not has_overlap:
                removals.append({
                    "item_key": key,
                    "direction": ckey,
                    "title": paper.get("title"),
                    "topic_terms": topic_terms[:5],
                    "reason": "full-text topic terms do not overlap direction profile",
                })
    return removals


def _detect_split_candidates(ctx: Stage2Context) -> list[dict]:
    """Detect directions that may need splitting based on distinct topic clusters.

    A direction is a split candidate when:
    - It has ≥4 papers with full-text facts
    - Topic terms cluster into ≥2 distinct groups with low inter-group overlap
    """
    import re as _re
    splits = []
    for plan in ctx.direction_plans:
        ckey = plan["ckey"]
        direction = plan["direction"]
        papers_with_facts = []
        for key in direction_candidate_keys(direction):
            paper = ctx.papers.get(key)
            if not paper:
                continue
            facts_record, facts_state, _ = ctx.facts_for(key)
            if facts_state == "valid" and facts_record:
                papers_with_facts.append({
                    "item_key": key,
                    "title": paper.get("title"),
                    "topic_terms": facts_record.get("topic_terms") or [],
                })
        if len(papers_with_facts) < 4:
            continue
        # Simple clustering: group papers by shared topic terms
        clusters: list[list[dict]] = []
        for paper in papers_with_facts:
            terms = set(str(t).lower() for t in paper["topic_terms"])
            matched = False
            for cluster in clusters:
                cluster_terms = set()
                for cp in cluster:
                    cluster_terms.update(str(t).lower() for t in cp["topic_terms"])
                if terms and cluster_terms and len(terms & cluster_terms) / max(len(terms), 1) >= 0.3:
                    cluster.append(paper)
                    matched = True
                    break
            if not matched:
                clusters.append([paper])
        # Filter: only suggest split if we have ≥2 substantial clusters (≥2 papers each)
        substantial = [c for c in clusters if len(c) >= 2]
        if len(substantial) >= 2:
            splits.append({
                "direction": ckey,
                "name_ja": direction.get("name_ja"),
                "name_zh": direction.get("name_zh"),
                "clusters": [
                    {
                        "papers": [p["item_key"] for p in cluster],
                        "titles": [p["title"] for p in cluster],
                        "common_terms": sorted(set.intersection(*[
                            set(str(t).lower() for t in p["topic_terms"]) for p in cluster
                        ])) if cluster else [],
                    }
                    for cluster in substantial
                ],
                "reason": f"direction splits into {len(substantial)} distinct topic clusters",
            })
    return splits


def _detect_merge_candidates(ctx: Stage2Context) -> list[dict]:
    """Detect pairs of directions that may be the same line based on shared evidence.

    A merge candidate when:
    - Two directions share ≥2 papers in their candidate union (cross-direction
      overlap). A single shared paper is not enough under the documented merge
      contract — it can be a chance co-incidence rather than a "same line" signal.
    - Their topic profiles (from name_ja/name_zh/summary_zh) overlap significantly
    """
    import re as _re
    MERGE_MIN_SHARED = 2
    merges = []
    plans = ctx.direction_plans
    for i, plan_a in enumerate(plans):
        for plan_b in plans[i + 1:]:
            ckey_a, ckey_b = plan_a["ckey"], plan_b["ckey"]
            # Check shared papers in candidate unions
            keys_a = set(direction_candidate_keys(plan_a["direction"]))
            keys_b = set(direction_candidate_keys(plan_b["direction"]))
            shared = keys_a & keys_b
            if len(shared) < MERGE_MIN_SHARED:
                continue
            # Check topic overlap from direction profiles
            parts_a = []
            parts_b = []
            for field in ("name_ja", "name_zh", "summary_zh"):
                val = plan_a["direction"].get(field)
                if isinstance(val, str) and val.strip():
                    parts_a.append(val)
                val = plan_b["direction"].get(field)
                if isinstance(val, str) and val.strip():
                    parts_b.append(val)
            toks_a = set()
            toks_b = set()
            for w in _re.findall(r"[A-Za-z0-9]+", " ".join(parts_a)):
                if len(w) >= 3:
                    toks_a.add(w.lower())
            for run in _re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", " ".join(parts_a)):
                for idx in range(len(run) - 1):
                    toks_a.add(run[idx:idx + 2])
            for w in _re.findall(r"[A-Za-z0-9]+", " ".join(parts_b)):
                if len(w) >= 3:
                    toks_b.add(w.lower())
            for run in _re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", " ".join(parts_b)):
                for idx in range(len(run) - 1):
                    toks_b.add(run[idx:idx + 2])
            if toks_a and toks_b:
                overlap = len(toks_a & toks_b) / min(len(toks_a), len(toks_b))
                if overlap >= 0.5:
                    merges.append({
                        "direction_a": ckey_a,
                        "direction_b": ckey_b,
                        "name_a": plan_a["direction"].get("name_ja"),
                        "name_b": plan_b["direction"].get("name_ja"),
                        "shared_papers": sorted(shared),
                        "overlap_ratio": round(overlap, 2),
                        "reason": f"directions share {len(shared)} papers and {round(overlap * 100)}% profile overlap",
                    })
    return merges


def cmd_stage2_resolve_plan(args) -> None:
    """Plan the direction resolution step: detect splits/merges/additions/removals.

    This is a deterministic pre-flight that uses full-text facts to suggest
    corrections to provisional directions. The actual resolution is performed
    by the model in the resolve job, which has access to the full context.

    Reuse: an existing `_resolved_directions.json` entry whose per-direction
    `input_fingerprint` still matches the current facts is reused as-is and
    gets NO new resolve job — only directions whose relevant paper metadata,
    sidecars, facts files, or profile inputs changed (or that were never
    resolved) are re-resolved.
    """
    ctx = Stage2Context(Path(args.facts))
    affinity = _compute_paper_direction_affinity(ctx)
    additions = _detect_candidates_for_addition(ctx, affinity)
    removals = _detect_candidates_for_removal(ctx, affinity)
    splits = _detect_split_candidates(ctx)
    merges = _detect_merge_candidates(ctx)

    # Determine if any material change is detected
    has_material_changes = bool(additions or removals or splits or merges)

    existing = _load_existing_resolved(ctx.professor_dir, ctx.professor, None)
    existing_by_ckey: dict[str, dict] = {}
    if existing:
        for entry in existing.get("directions") or []:
            if isinstance(entry, dict) and isinstance(entry.get("provisional_direction_id"), str):
                existing_by_ckey[entry["provisional_direction_id"]] = entry

    # Build per-direction resolution jobs
    resolve_jobs = []
    reuse_list = []
    for plan in ctx.direction_plans:
        ckey = plan["ckey"]
        prior = existing_by_ckey.get(ckey)
        current_fingerprint = _per_direction_fingerprint(plan["direction"], ctx.papers)
        if prior and prior.get("input_fingerprint") == current_fingerprint:
            reuse_list.append(ckey)
            continue  # resolved state is fresh; no new job
        direction = plan["direction"]
        # Collect per-paper evidence over the FULL candidate universe: issue #7
        # requires the resolution to judge every unique candidate paper from
        # full-text facts, including candidates the abstract relevance gate
        # dropped from the gap/narrative relevant set.
        paper_evidence = []
        for key in direction_candidate_keys(direction):
            paper = ctx.papers.get(key)
            if not paper:
                continue
            facts_record, facts_state, facts_error = ctx.facts_for(key)
            paper_evidence.append({
                "item_key": key,
                "title": paper.get("title"),
                "year": paper.get("year"),
                "authorship": paper.get("authorship"),
                "is_provisional_member": key in (direction.get("provisional_member_keys") or []),
                "facts_state": facts_state,
                "facts_error": facts_error,
                "topic_terms": (facts_record or {}).get("topic_terms") if facts_record else [],
                "affinity_scores": affinity.get(key, {}),
            })
        # Collect gap evidence
        gap_evidence = []
        for gap in plan["pool"]:
            gap_evidence.append({
                "gap_id": gap["gap_id"],
                "item_key": gap["item_key"],
                "paper_title": gap.get("paper_title"),
                "quote_trunc": truncate(gap.get("quote"), 120),
                "translation_zh": truncate(gap.get("translation_zh"), 80),
            })
        # Collect removal candidates for this direction
        dir_removals = [r for r in removals if r["direction"] == ckey]
        resolve_jobs.append({
            "job_id": f"resolve:{ctx.professor}:{ckey}",
            "kind": "resolve",
            "collection_key": ckey,
            "result_file": f"resolve-{ckey}.json",
            "result_schema": {
                "schema": 1,
                "kind": "resolve",
                "collection_key": ckey,
                "resolved": {
                    "resolved_direction_id": "<stable ID, same as collection_key unless split>",
                    "provisional_direction_id": ckey,
                    "name_ja": "<confirmed or renamed>",
                    "name_zh": "<confirmed or renamed>",
                    "resolution_type": "unchanged|renamed|split_from|merged_into|refined",
                    "papers_to_add": ["<item_key>; for split_from: papers moved INTO the new direction"],
                    "papers_to_remove": ["<item_key>; must be empty for split_from/merged_into>"],
                    "paper_justifications": {"<item_key>": "<1 sentence reason>"},
                    "split_target": "<split_from only: NEW direction ID, must not collide with any existing direction>",
                    "merge_target": "<merged_into only: existing target direction ID>",
                    "user_note": "<preserved from provisional>",
                },
            },
            "model_input": {
                "collection_key": ckey,
                "provisional_direction": {
                    "name_ja": direction.get("name_ja"),
                    "name_zh": direction.get("name_zh"),
                    "summary_zh": direction.get("summary_zh"),
                    "user_note": direction.get("user_note") or "",
                    "provisional_member_keys": direction.get("provisional_member_keys") or [],
                    "credibility": direction.get("credibility") or {},
                },
                "paper_evidence": paper_evidence,
                "gap_evidence": gap_evidence,
                "removal_candidates": dir_removals,
                "split_candidates": [s for s in splits if s["direction"] == ckey],
                "merge_candidates": [m for m in merges if m["direction_a"] == ckey or m["direction_b"] == ckey],
                "addition_candidates": [a for a in additions if a["target_direction"] == ckey],
                "rules": (
                    "Resolve this provisional direction against full-text evidence.\n"
                    "1. Each paper in paper_evidence has full-text facts (facts_state=valid) or not.\n"
                    "2. Papers with valid full-text facts: judge membership by topic_terms overlap with direction profile.\n"
                    "3. Papers without full-text facts: keep provisional membership (can't downgrade without evidence).\n"
                    "4. A paper can support multiple directions (shared papers are allowed).\n"
                    "5. Removal: only when full-text facts clearly show the paper doesn't belong.\n"
                    "6. Addition: only when full-text facts clearly support this direction over the provisional one.\n"
                    "7. Split: only when papers cluster into ≥2 distinct topic groups; set split_target to a NEW "
                    "direction ID and put the papers that move INTO the new direction in papers_to_add "
                    "(the source keeps the rest; papers_to_remove must be empty).\n"
                    "8. Merge: only when another direction shares ≥2 papers and the same line of work; set "
                    "merge_target to that direction ID (papers_to_add/papers_to_remove must be empty — the whole "
                    "direction folds into the target).\n"
                    "9. Keyword/grep matches alone are NOT sufficient for final membership.\n"
                    "10. If no material change, set resolution_type='unchanged' and empty add/remove lists."
                ),
            },
        })

    emit({
        "status": "ok",
        "professor": ctx.professor,
        "professor_dir": str(ctx.professor_dir),
        "has_material_changes": has_material_changes,
        "summary": {
            "directions": len(ctx.direction_plans),
            "reused_resolved": len(reuse_list),
            "addition_candidates": len(additions),
            "removal_candidates": len(removals),
            "split_candidates": len(splits),
            "merge_candidates": len(merges),
        },
        "directions": [{
            "collection_key": plan["ckey"],
            "action": "reuse" if plan["ckey"] in reuse_list else "process",
            "input_fingerprint": _per_direction_fingerprint(plan["direction"], ctx.papers),
        } for plan in ctx.direction_plans],
        "candidates": {
            "additions": additions,
            "removals": removals,
            "splits": splits,
            "merges": merges,
        },
        "jobs": resolve_jobs,
        "write_needed": bool(resolve_jobs),
    })


def _per_direction_fingerprint(direction: dict, papers: dict) -> str:
    """Per-direction fingerprint of the inputs that affect resolved_direction.

    Captures only fields that should invalidate a cached resolved state:
    candidate-universe paper metadata (item_key + title + year + abstract_sha)
    + analysis/sidecar/facts SHAs + direction profile fields. The fingerprint
    stays narrow so that display-only changes (e.g. preview_coverage_share) do
    NOT bust the resolved state, but ANY candidate paper's full-text evidence
    (new facts sidecar, changed analysis) invalidates it — the resolution must
    be able to react to evidence about every unique candidate paper, not just
    the ones the relevance gate let through.
    """
    candidate_keys = sorted(set(direction_candidate_keys(direction)))
    paper_rows = []
    for key in candidate_keys:
        paper = papers.get(key, {})
        paper_rows.append({
            "item_key": key,
            "title": paper.get("title"),
            "year": paper.get("year"),
            "month": paper.get("month"),
            "authorship": paper.get("authorship"),
            "abstract_sha": sha256_text(paper.get("abstract") or "") if paper.get("abstract") else None,
            "has_pdf": bool(paper.get("has_pdf")),
            "analysis_sha": sha256_bytes(Path(paper.get("analysis_file")).read_bytes())
                if paper.get("analysis_file") and Path(paper.get("analysis_file")).is_file() else None,
            "sidecar_sha": sha256_bytes(Path(paper.get("sidecar_file")).read_bytes())
                if paper.get("sidecar_file") and Path(paper.get("sidecar_file")).is_file() else None,
            "facts_sha": sha256_bytes(Path(paper.get("facts_file")).read_bytes())
                if paper.get("facts_file") and Path(paper.get("facts_file")).is_file() else None,
        })
    return sha256_obj({
        "version": 1,
        "provisional_direction_id": direction.get("collection_key"),
        "name_ja": direction.get("name_ja"),
        "name_zh": direction.get("name_zh"),
        "summary_zh": direction.get("summary_zh"),
        "status": direction.get("status"),
        "user_note_sha": sha256_text(direction.get("user_note") or ""),
        "provisional_member_keys": sorted(direction.get("provisional_member_keys") or []),
        "named_keys": sorted(direction.get("named_keys") or []),
        "paper_rows": paper_rows,
    })


def validate_resolve_results(ctx: Stage2Context, results_dir: Path,
                             reused: dict[str, dict] | None = None) -> dict[str, dict]:
    """Validate resolve result JSON files. Returns ckey -> resolved direction.

    `reused` carries previously accepted sidecar entries whose per-direction
    input_fingerprint still matches the current facts; when a direction has no
    new result file its reused entry is kept as-is instead of being reset to
    "unchanged" (a resolve re-run must never silently wipe an applied
    resolution).

    Enforces:
    - schema/kind correctness
    - resolution_type ∈ {unchanged, renamed, split_from, merged_into, refined}
    - split_from requires a NEW split_target ID and moves papers via
      papers_to_add (⊆ relevant keys, source keeps ≥1 paper)
    - merged_into requires merge_target pointing at another direction in this
      professor's plans; merge chains (target is itself merged_into) fail
    - papers_to_remove ⊆ provisional_member_keys
    - papers_to_add ⊆ candidate member_keys
    """
    reused = reused or {}
    resolved = {}
    direction_lookup = {plan["ckey"]: plan for plan in ctx.direction_plans}
    for plan in ctx.direction_plans:
        ckey = plan["ckey"]
        current_fingerprint = _per_direction_fingerprint(plan["direction"], ctx.papers)

        def _unchanged_default() -> dict:
            direction = plan["direction"]
            return {
                "resolved_direction_id": ckey,
                "provisional_direction_id": ckey,
                "name_ja": direction.get("name_ja") or "",
                "name_zh": direction.get("name_zh") or "",
                "resolution_type": "unchanged",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": direction.get("user_note") or "",
                "input_fingerprint": current_fingerprint,
                "reused": False,
            }

        prior = reused.get(ckey)
        if prior:
            # This direction was validated as reuse in the current resolve plan
            # (no job emitted). Analyzer result dirs are typically fixed /tmp
            # paths, so a stale `resolve-<ckey>.json` from a previous run may
            # still sit there — it must NEVER be re-consumed for a direction
            # that got no job this round. The cached entry wins unconditionally.
            entry = dict(prior)
            entry["input_fingerprint"] = current_fingerprint
            entry["reused"] = True
            resolved[ckey] = entry
            continue
        result_path = results_dir / f"resolve-{ckey}.json"
        if not result_path.is_file():
            # No new result: default to unchanged.
            resolved[ckey] = _unchanged_default()
            continue
        data, error = read_json_file(result_path)
        if error:
            fail("result_missing", f"{result_path}: {error}")
        if not isinstance(data, dict) or data.get("schema") != 1 or data.get("kind") != "resolve":
            fail("invalid_result_json", f"{result_path}: schema/kind must be 1/resolve")
        r = data.get("resolved")
        if not isinstance(r, dict):
            fail("invalid_result_json", f"{result_path}: resolved must be an object")
        # Validate required fields
        resolved_direction_id = r.get("resolved_direction_id")
        if not isinstance(resolved_direction_id, str) or not resolved_direction_id.strip():
            fail("invalid_result_json", f"{result_path}: resolved_direction_id must be a non-empty string")
        resolution_type = r.get("resolution_type")
        if resolution_type not in ("unchanged", "renamed", "split_from", "merged_into", "refined"):
            fail("invalid_result_json", f"{result_path}: invalid resolution_type: {resolution_type}")
        papers_to_add = r.get("papers_to_add") or []
        papers_to_remove = r.get("papers_to_remove") or []
        if not isinstance(papers_to_add, list) or not all(isinstance(k, str) for k in papers_to_add):
            fail("invalid_result_json", f"{result_path}: papers_to_add must be a string list")
        if not isinstance(papers_to_remove, list) or not all(isinstance(k, str) for k in papers_to_remove):
            fail("invalid_result_json", f"{result_path}: papers_to_remove must be a string list")
        # Validate that removed papers were provisional members
        provisional = set(plan["direction"].get("provisional_member_keys") or [])
        for key in papers_to_remove:
            if key not in provisional:
                fail("invalid_result_json",
                     f"{result_path}: cannot remove non-provisional paper {key}")
        # Validate that added papers exist in candidate set
        candidate_set = set(plan["direction"].get("member_keys") or [])
        for key in papers_to_add:
            if key not in candidate_set:
                fail("invalid_result_json",
                     f"{result_path}: cannot add paper {key} not in candidate set")
        # Full-text evidence gate: only a CURRENTLY VALID full-text facts
        # sidecar may justify changing authoritative membership. The model
        # prompt alone is not this boundary — abstract-only / legacy / broken
        # evidence chains can never add, remove, or move a paper (split moves
        # ride papers_to_add, so they are covered by the same check).
        for key in sorted(set(papers_to_add) | set(papers_to_remove)):
            _facts_record, facts_state, _facts_error = ctx.facts_for(key)
            if facts_state != "valid":
                fail("invalid_result_json",
                     f"{result_path}: membership change for {key} requires a currently "
                     f"valid full-text facts sidecar (got facts_state={facts_state!r})")
        # Validate split / merge structure
        split_target = r.get("split_target")
        merge_target = r.get("merge_target")
        if resolution_type == "split_from":
            if not isinstance(split_target, str) or not split_target.strip():
                fail("invalid_result_json",
                     f"{result_path}: split_from requires split_target (new direction ID)")
            if papers_to_remove:
                fail("invalid_result_json",
                     f"{result_path}: split_from expresses paper assignment via papers_to_add "
                     "(papers moved to the new direction); papers_to_remove must be empty")
            if not papers_to_add:
                fail("invalid_result_json",
                     f"{result_path}: split_from requires papers_to_add (papers moved to the new direction)")
            relevant = set(direction_relevant_keys(plan["direction"]))
            if not (relevant - set(papers_to_add)):
                fail("invalid_result_json",
                     f"{result_path}: split_from would leave the source direction {ckey} with no papers")
        else:
            if split_target is not None:
                fail("invalid_result_json",
                     f"{result_path}: split_target only valid for split_from resolution")
        if resolution_type == "merged_into":
            if not isinstance(merge_target, str) or not merge_target.strip():
                fail("invalid_result_json",
                     f"{result_path}: merged_into requires merge_target (target direction ID)")
            if merge_target == ckey:
                fail("invalid_result_json",
                     f"{result_path}: merge_target cannot be the same direction {ckey}")
            if merge_target not in direction_lookup:
                fail("invalid_result_json",
                     f"{result_path}: merge_target {merge_target} not in selected directions for this professor")
            if papers_to_add or papers_to_remove:
                fail("invalid_result_json",
                     f"{result_path}: merged_into folds the whole direction into its target; "
                     "papers_to_add/papers_to_remove must be empty")
        else:
            if merge_target is not None:
                fail("invalid_result_json",
                     f"{result_path}: merge_target only valid for merged_into resolution")
        resolved[ckey] = {
            "resolved_direction_id": resolved_direction_id,
            "provisional_direction_id": ckey,
            "name_ja": r.get("name_ja") or plan["direction"].get("name_ja") or "",
            "name_zh": r.get("name_zh") or plan["direction"].get("name_zh") or "",
            "resolution_type": resolution_type,
            "papers_to_add": papers_to_add,
            "papers_to_remove": papers_to_remove,
            "paper_justifications": r.get("paper_justifications") or {},
            "split_target": split_target,
            "merge_target": merge_target,
            "user_note": r.get("user_note") or plan["direction"].get("user_note") or "",
            "input_fingerprint": current_fingerprint,
            "reused": False,
        }
    # Global structural checks across all resolved entries.
    merge_sources = {ckey for ckey, r in resolved.items()
                     if r["resolution_type"] == "merged_into"}
    for ckey in merge_sources:
        target = resolved[ckey]["merge_target"]
        if target in merge_sources:
            fail("invalid_result_json",
                 f"merge chain detected: {ckey} -> {target}, but {target} is itself merged_into another direction")
    # Every split target must be a brand-new ID: never an existing provisional
    # direction and never another split's target or resolved ID.
    all_ids: list[str] = []
    for ckey, r in resolved.items():
        all_ids.append(r["resolved_direction_id"])
        if r["resolution_type"] == "split_from":
            target = r["split_target"]
            if target in direction_lookup:
                fail("invalid_result_json",
                     f"split_target {target} from {ckey} collides with existing provisional direction")
            all_ids.append(target)
    duplicates = sorted({i for i in all_ids if all_ids.count(i) > 1})
    if duplicates:
        fail("invalid_result_json",
             f"resolved_direction_id/split_target must be globally unique, duplicates: {duplicates}")
    return resolved


def _load_existing_resolved(professor_dir: Path, professor: str,
                            expected_facts_sha: str | None) -> dict | None:
    """Load `_resolved_directions.json` if it matches this professor and facts fingerprint.

    Returns None on any mismatch (stale, cross-professor, schema invalid) so the
    caller can fail closed and re-run resolve. Cross-professor and stale files
    are NEVER silently applied — that's a safety boundary for resolved state.
    """
    path = professor_dir / "论文分析" / "_resolved_directions.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema") != RESOLVED_DIRECTION_SCHEMA:
        return None
    if data.get("kind") != "professor-contact-resolved-directions":
        return None
    if data.get("professor") != professor:
        return None
    # Compare facts fingerprint if provided
    if expected_facts_sha is not None:
        stored = data.get("facts_fingerprint")
        if stored and stored != expected_facts_sha:
            return None
    return data


def cmd_stage2_resolve_finalize(args) -> None:
    """Validate resolve results and write resolved_direction state to a sidecar file.

    The resolved direction state is written to `<professor_dir>/论文分析/_resolved_directions.json`
    as an intermediate artifact consumed by stage2-finalize.

    Always emits one entry per direction (even unchanged) so downstream consumers
    have a single resolved_direction_id for every direction. Cross-professor and
    schema-invalid existing sidecars are NOT silently overwritten — the runner
    always validates and re-writes from the current resolve results.
    """
    ctx = Stage2Context(Path(args.facts))
    results_dir = Path(args.results)
    existing = _load_existing_resolved(ctx.professor_dir, ctx.professor, None)
    plan_fingerprints = {plan["ckey"]: _per_direction_fingerprint(plan["direction"], ctx.papers)
                         for plan in ctx.direction_plans}
    existing_by_ckey: dict[str, dict] = {}
    if existing:
        for entry in existing.get("directions") or []:
            if isinstance(entry, dict) and isinstance(entry.get("provisional_direction_id"), str):
                existing_by_ckey[entry["provisional_direction_id"]] = entry
    reused = {ckey: entry for ckey, entry in existing_by_ckey.items()
              if plan_fingerprints.get(ckey) == entry.get("input_fingerprint")}
    resolved = validate_resolve_results(ctx, results_dir, reused)

    # Check for material changes that require user confirmation. Already-applied
    # (reused) resolutions must NOT re-prompt the user on every re-run.
    material_changes = []
    for ckey, r in resolved.items():
        if r["resolution_type"] != "unchanged" and not r.get("reused"):
            material_changes.append({
                "provisional_direction_id": ckey,
                "resolved_direction_id": r["resolved_direction_id"],
                "resolution_type": r["resolution_type"],
                "name_ja": r["name_ja"],
                "name_zh": r["name_zh"],
                "papers_to_add": r["papers_to_add"],
                "papers_to_remove": r["papers_to_remove"],
                "split_target": r["split_target"],
                "merge_target": r["merge_target"],
            })

    # Compute facts fingerprint for cross-professor safety
    facts_payload = {
        "professor": ctx.professor,
        "professor_dir": str(ctx.professor_dir),
        "directions": [
            {"collection_key": plan["ckey"],
             "fingerprint": _per_direction_fingerprint(plan["direction"], ctx.papers)}
            for plan in ctx.direction_plans
        ],
    }
    facts_fingerprint = sha256_obj(facts_payload)

    # Write resolved directions state — always one entry per direction
    resolved_path = ctx.professor_dir / "论文分析" / "_resolved_directions.json"
    resolved_payload = {
        "schema": RESOLVED_DIRECTION_SCHEMA,
        "kind": "professor-contact-resolved-directions",
        "professor": ctx.professor,
        "professor_dir": str(ctx.professor_dir),
        "facts_fingerprint": facts_fingerprint,
        "generated_at": now_utc(),
        "directions": list(resolved.values()),
        "has_material_changes": bool(material_changes),
    }
    atomic_json(resolved_path, resolved_payload)

    # Collect new split directions (targets that don't match any provisional ckey).
    # These are the "new authoritative direction entries" the split resolved.
    existing_ckeys = {plan["ckey"] for plan in ctx.direction_plans}
    new_splits = []
    for ckey, r in resolved.items():
        if r["resolution_type"] == "split_from" and r["split_target"] not in existing_ckeys:
            # Find the source plan to copy the structure
            source_plan = next((p for p in ctx.direction_plans if p["ckey"] == ckey), None)
            if source_plan:
                new_splits.append({
                    "source_provisional_id": ckey,
                    "new_resolved_id": r["split_target"],
                    "name_ja": r["name_ja"],
                    "name_zh": r["name_zh"],
                    "papers_to_add": r["papers_to_add"],
                    "papers_to_remove": r["papers_to_remove"],
                    "paper_justifications": r["paper_justifications"],
                    "user_note": r["user_note"],
                    "input_fingerprint": r["input_fingerprint"],
                })

    emit({
        "status": "ok",
        "professor": ctx.professor,
        "resolved_directions_path": str(resolved_path),
        "facts_fingerprint": facts_fingerprint,
        "directions": [
            {
                "provisional_direction_id": ckey,
                "resolved_direction_id": r["resolved_direction_id"],
                "resolution_type": r["resolution_type"],
                "name_ja": r["name_ja"],
                "name_zh": r["name_zh"],
                "papers_to_add": r["papers_to_add"],
                "papers_to_remove": r["papers_to_remove"],
                "split_target": r["split_target"],
                "merge_target": r["merge_target"],
            }
            for ckey, r in resolved.items()
        ],
        "new_splits": new_splits,
        "material_changes": material_changes,
        "needs_user_choice": bool(material_changes),
    })


def cmd_stage2_plan(args) -> None:
    ctx = Stage2Context(Path(args.facts))
    jobs, reuse_list, process_list = [], [], []
    for plan in ctx.direction_plans:
        ckey = plan["ckey"]
        if plan["reuse"]:
            reuse_list.append(ckey)
            continue
        process_list.append(ckey)
        judge, hits = ctx.freshness_job_items(plan)
        pending = [item for item in judge if not item["cached"]]
        if pending:
            job_gaps = []
            for item in pending:
                gap, cands = item["gap"], item["cands"]
                materials = []
                for tier in ("confirmed_family", "authorship", "recent", "topic"):
                    for key in cands["tiers"][tier]:
                        paper = ctx.papers[key]
                        materials.append({
                            "item_key": key, "title": paper.get("title"),
                            "year": paper.get("year"), "tier": tier,
                            "abstract": truncate(paper.get("abstract"), ABSTRACT_INPUT_CHARS)})
                job_gaps.append({
                    "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                    "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                    "quote": truncate(gap.get("quote"), QUOTE_INPUT_CHARS),
                    "translation_zh": truncate(gap.get("translation_zh"), TRANSLATION_INPUT_CHARS),
                    "candidates": {
                        "papers": materials, "later_total": cands["later_total"],
                        "unverifiable_count": cands["excluded_no_clue"]},
                    "note": "禁止「标题无命中直接写 open」；candidates 为空且 later_total>0 → unknown（unverifiable_count 条无法核对）；candidates 为空且 later_total=0 → open 并说明"})
            jobs.append({
                "job_id": f"freshness:{ctx.professor}:{ckey}", "kind": "freshness",
                "collection_key": ckey,
                "result_file": f"freshness-{ckey}.json",
                "result_schema": {"schema": 1, "kind": "freshness", "collection_key": ckey,
                                  "results": [{"gap_id": "", "status": "open|partial|done_by_self|unknown",
                                               "candidate_paper_ids": [], "evidence": "",
                                               "completed_part": "", "remaining_gap": "",
                                               "confidence": "high|medium|low"}]},
                "model_input": {"gaps": job_gaps}})
        jobs.append({
            "job_id": f"narrative:{ctx.professor}:{ckey}", "kind": "narrative",
            "collection_key": ckey,
            "result_file": "narrative.json",
            "result_schema": {"schema": 1, "kind": "narrative", "directions": [
                {"collection_key": ckey, "positioning": [
                    {"kind": "para|bullet", "text": "…{{P:ITEMKEY}}…{{G:GAPID}}…", "refs": ["paper:ITEMKEY"]}],
                 "gap_notes": [{"gap_id": "", "summary": "一句话概括", "explanation": "大白话≤3句"}]}]},
            "model_input": {
                "collection_key": ckey,
                "user_note": plan["direction"].get("user_note") or "",
                "credibility": plan["direction"].get("credibility"),
                "papers": [{"item_key": key, "title": ctx.papers[key].get("title"),
                            "year": ctx.papers[key].get("year"),
                            "authorship": ctx.papers[key].get("authorship")}
                           for key in direction_relevant_keys(plan["direction"]) if key in ctx.papers],
                 "later_papers": [{"item_key": key, "title": ctx.papers[key].get("title"),
                                   "year": ctx.papers[key].get("year"),
                                   "authorship": ctx.papers[key].get("authorship"),
                                   "abstract": truncate(ctx.papers[key].get("abstract"), ABSTRACT_INPUT_CHARS)}
                                  for key in ctx.narrative_later_keys(plan) if key in ctx.papers],
                 "gaps": [{"gap_id": g["gap_id"], "item_key": g["item_key"],
                           "paper_title": g.get("paper_title"), "paper_year": g.get("paper_year"),
                           "quote": truncate(g.get("quote"), 200),
                           "translation_zh": truncate(g.get("translation_zh"), 200)}
                          for g in plan["ranked"]],
                 "rules": "text 里用 {{P:KEY}} 引方向论文、{{L:KEY}} 引后续论文、{{G:GAPID}} 引 future work；refs 必须与占位符一一对应（集合相等）；叙事不得断言 gap_status（状态由 runner 渲染的 freshness 卡承载）；不得把未在 papers/later_papers/gaps 清单里的 ID 写进 refs；每个 positioning block 必须提供 concrete_object、input_example、output_example 三个具体例子字段，且只能依据对应 papers/gaps"}})
    emit({
        "status": "ok",
        "professor": ctx.professor,
        "professor_dir": str(ctx.professor_dir),
        "pack_path": str(ctx.pack_path),
        "params": {"gap_scope": ctx.gap_scope, "freshness_scope": ctx.freshness_scope},
        "directions": [{
            "collection_key": p["ckey"], "action": "reuse" if p["reuse"] else "process",
            "gap_pool": len(p["pool"]),
            "judge_count": len(ctx.judge_set(p)) if not p["reuse"] else 0,
            "reason_code": ("shortlist_over_limit" if len(p["ranked"]) > SHORTLIST_MAX and
                            ctx.freshness_scope == "shortlist" else None),
        } for p in ctx.direction_plans],
        "jobs": jobs,
        "write_needed": bool(jobs),
    })


def validate_freshness_results(ctx: Stage2Context, results_dir: Path,
                               required: dict) -> dict:
    """required: ckey -> list of pending job items. Returns ckey -> {gap_id: status_record}."""
    accepted = {}
    for ckey, items in required.items():
        pending = [item for item in items if not item["cached"]]
        if not pending:
            accepted[ckey] = {item["gap"]["gap_id"]: item["status"] for item in items}
            continue
        result_path = results_dir / f"freshness-{ckey}.json"
        data, error = read_json_file(result_path)
        if error:
            fail("result_missing", f"{result_path}: {error}")
        if not isinstance(data, dict) or data.get("schema") != 1 or data.get("kind") != "freshness":
            fail("invalid_result_json", f"{result_path}: schema/kind must be 1/freshness")
        rows = data.get("results")
        if not isinstance(rows, list):
            fail("invalid_result_json", f"{result_path}: results must be a list")
        by_gap = {}
        judge_ids = {item["gap"]["gap_id"] for item in items}
        for row in rows:
            if not isinstance(row, dict):
                fail("invalid_result_json", f"{result_path}: results[] must be objects")
            gap_id = row.get("gap_id")
            if not isinstance(gap_id, str):
                fail("invalid_result_json", f"{result_path}: gap_id must be a string")
            if gap_id not in judge_ids:
                fail("unknown_reference_id", f"{result_path}: gap outside package: {gap_id}")
            if gap_id in by_gap:
                fail("invalid_result_json", f"{result_path}: duplicate result for gap {gap_id}")
            by_gap[gap_id] = row
        pending_ids = {item["gap"]["gap_id"] for item in pending}
        if not pending_ids.issubset(set(by_gap)):
            missing = sorted(pending_ids - set(by_gap))
            fail("invalid_result_json", f"{result_path}: missing results for gaps: {missing}")
        statuses = {}
        for item in pending:
            gap_id = item["gap"]["gap_id"]
            row = by_gap.get(gap_id)
            if row is None:
                fail("invalid_result_json", f"{result_path}: missing result for gap {gap_id[:12]}…")
            status = row.get("status")
            if status not in GAP_STATUSES:
                fail("invalid_result_json", f"{result_path}: bad status for {gap_id[:12]}…")
            cand_ids = row.get("candidate_paper_ids") or []
            if not isinstance(cand_ids, list) or any(not isinstance(c, str) for c in cand_ids):
                fail("invalid_result_json", f"{result_path}: candidate_paper_ids must be a string list")
            if len(set(cand_ids)) != len(cand_ids):
                fail("invalid_result_json", f"{result_path}: duplicate candidate paper IDs for {gap_id[:12]}…")
            allowed_ids = set()
            for tier in item["cands"]["tiers"].values():
                allowed_ids.update(tier)
            unknown_ids = [c for c in cand_ids if c not in allowed_ids]
            if unknown_ids:
                fail("unknown_reference_id",
                     f"{result_path}: candidate_paper_ids outside package for {gap_id[:12]}…: {unknown_ids}")
            evidence_value = row.get("evidence")
            if not isinstance(evidence_value, str):
                fail("invalid_result_json", f"{result_path}: evidence must be a string for {gap_id[:12]}…")
            evidence = evidence_value.strip()
            if not evidence:
                fail("invalid_result_json", f"{result_path}: evidence required for {gap_id[:12]}…")
            downgraded = False
            if status == "partial" and (not (row.get("completed_part") or "").strip() or
                                        not (row.get("remaining_gap") or "").strip()):
                status, downgraded = "unknown", True
            record = {
                "gap_id": gap_id, "item_key": item["gap"]["item_key"],
                "status": status,
                "model_evidence": evidence,
                "candidate_paper_ids": cand_ids,
                "candidate_fingerprint": item["cand_fp"],
                "gap_fingerprint": item["gap_fp"],
                "evaluated_at": now_utc(),
                "confidence": row.get("confidence") if row.get("confidence") in ("high", "medium", "low") else "low",
                "completed_part": (row.get("completed_part") or "").strip() or None,
                "remaining_gap": (row.get("remaining_gap") or "").strip() or None,
                "downgraded": downgraded,
            }
            statuses[gap_id] = record
        for item in items:
            if item["cached"]:
                statuses.setdefault(item["gap"]["gap_id"], item["status"])
        accepted[ckey] = statuses
    return accepted


def narrative_scope(ctx: Stage2Context, ckey: str) -> dict:
    for plan in ctx.direction_plans:
        if plan["ckey"] == ckey:
            return {
                "papers": {key for key in direction_relevant_keys(plan["direction"])
                            if key in ctx.papers},
                "later": set(ctx.narrative_later_keys(plan)),
                "gaps": {g["gap_id"] for g in plan["ranked"]},
            }
    return {"papers": set(), "later": set(), "gaps": set()}


def validate_narrative_entry(ctx: Stage2Context, path: Path, entry: dict,
                             expected_ckey: str | None = None) -> tuple[str, dict]:
    if not isinstance(entry, dict):
        fail("invalid_result_json", f"{path}: narrative entry must be an object")
    ckey = entry.get("collection_key")
    if expected_ckey is not None and ckey != expected_ckey:
        fail("invalid_result_json", f"{path}: expected direction {expected_ckey}, got {ckey}")
    if not isinstance(ckey, str):
        fail("invalid_result_json", f"{path}: collection_key must be a string")
    scope = narrative_scope(ctx, ckey)
    if not any(plan["ckey"] == ckey for plan in ctx.direction_plans):
        fail("invalid_result_json", f"{path}: unexpected direction {ckey}")
    positioning = entry.get("positioning")
    if not isinstance(positioning, list) or not positioning:
        fail("invalid_result_json", f"{path}: {ckey} positioning must be a non-empty list")
    checked = []
    for block in positioning:
        if not isinstance(block, dict) or not isinstance(block.get("text"), str):
            fail("invalid_result_json", f"{path}: positioning blocks need text")
        for field in ("concrete_object", "input_example", "output_example"):
            if not isinstance(block.get(field), str) or not block[field].strip():
                fail("invalid_result_json", f"{path}: positioning blocks need {field}")
        if any(block[field].strip().startswith(("输入", "输出")) and
               ("所处理的数据或用户操作" in block[field] or "论文展示的" in block[field])
               for field in ("input_example", "output_example")):
            fail("invalid_result_json", f"{path}: positioning examples must be concrete")
        placeholders = set()
        for kind, value in PLACEHOLDER_RE.findall(block.get("text") or ""):
            if kind == "P":
                placeholders.add(f"paper:{value}")
            elif kind == "L":
                placeholders.add(f"later:{value}")
            else:
                placeholders.add(f"gap:{value}")
        raw_refs = block.get("refs")
        if not isinstance(raw_refs, list) or not all(isinstance(ref, str) for ref in raw_refs):
            fail("invalid_result_json", f"{path}: {ckey} refs must be a string list")
        refs = set(raw_refs)
        if len(raw_refs) != len(refs):
            fail("invalid_result_json", f"{path}: {ckey} refs contain duplicates")
        for ref in refs:
            ref_kind, _, ref_id = ref.partition(":")
            pool = (scope["papers"] if ref_kind == "paper" else
                    scope["later"] if ref_kind == "later" else scope["gaps"])
            if ref_kind not in ("paper", "later", "gap") or ref_id not in pool:
                fail("unknown_reference_id", f"{path}: ref {ref} outside package")
        if placeholders != refs:
            fail("invalid_result_json",
                 f"{path}: {ckey} placeholders {sorted(placeholders)} != refs {sorted(refs)}")
        checked.append({"kind": block.get("kind") if block.get("kind") in ("para", "bullet") else "bullet",
                        "text": block["text"],
                        "refs": list(raw_refs),
                        "concrete_object": block["concrete_object"].strip(),
                        "input_example": block["input_example"].strip(),
                        "output_example": block["output_example"].strip()})
    raw_gap_notes = entry.get("gap_notes") or []
    if not isinstance(raw_gap_notes, list):
        fail("invalid_result_json", f"{path}: {ckey} gap_notes must be a list")
    gap_notes = {}
    for note in raw_gap_notes:
        if not isinstance(note, dict):
            fail("invalid_result_json", f"{path}: {ckey} gap_notes[] must be objects")
        gap_id = note.get("gap_id")
        if gap_id not in scope["gaps"]:
            fail("unknown_reference_id", f"{path}: gap note outside package: {gap_id}")
        if gap_id in gap_notes:
            fail("invalid_result_json", f"{path}: duplicate gap note {gap_id}")
        if not isinstance(note.get("summary"), str) or not isinstance(note.get("explanation"), str):
            fail("invalid_result_json", f"{path}: gap note {gap_id} needs string summary/explanation")
        gap_notes[gap_id] = {
            "summary": truncate(note.get("summary"), 120),
            "explanation": truncate(note.get("explanation"), 300)}
    return ckey, {"positioning": checked, "gap_notes": gap_notes}


def validate_narrative(ctx: Stage2Context, results_dir: Path, needed_keys: list) -> dict:
    path = results_dir / "narrative.json"
    data, error = read_json_file(path)
    if error:
        fail("result_missing", f"{path}: {error}")
    if not isinstance(data, dict) or data.get("schema") != 1 or data.get("kind") != "narrative":
        fail("invalid_result_json", f"{path}: schema/kind must be 1/narrative")
    if not isinstance(data.get("directions"), list):
        fail("invalid_result_json", f"{path}: directions must be a list")
    narratives = {}
    for entry in data["directions"]:
        ckey, checked = validate_narrative_entry(ctx, path, entry)
        if ckey not in needed_keys:
            fail("invalid_result_json", f"{path}: unexpected direction {ckey}")
        if ckey in narratives:
            fail("invalid_result_json", f"{path}: duplicate narrative for {ckey}")
        narratives[ckey] = checked
    for ckey in needed_keys:
        if ckey not in narratives:
            fail("invalid_result_json", f"{path}: missing narrative for {ckey}")
    return narratives


def citation_render(item_key: str, paper: dict, professor_dir: Path,
                    seen: dict) -> str:
    title = paper.get("title") or item_key
    link = f"[{title}](zotero://select/library/items/{item_key})"
    if item_key not in seen:
        seen[item_key] = True
        analysis = paper.get("analysis_file")
        if analysis:
            return link + f"｜[分析]({rel_path(Path(analysis), professor_dir)})"
        return link
    year = paper.get("year") or "年份不明"
    return f"[《{title}》](zotero://select/library/items/{item_key})（{year}）"


def redact_item_keys(text: str, papers: dict) -> str:
    """Keep deterministic human-facing red lines free of internal item keys."""
    rendered = text
    for key in sorted((key for key in papers if key), key=len, reverse=True):
        if key in rendered:
            rendered = rendered.replace(key, papers[key].get("title") or "该论文")
    return re.sub(r"(?<![A-Za-z0-9])[A-Z0-9]{8}(?![A-Za-z0-9])", "相关论文", rendered)


def build_direction_pack(ctx: Stage2Context, plan: dict, statuses: dict,
                         narrative: dict) -> dict:
    direction = plan["direction"]
    judge, ranked = [], plan["ranked"]
    judge = ctx.judge_set(plan)
    judged_ids = {g["gap_id"] for g in judge}
    blacklist, anchorable = [], []
    for gap in ranked:
        record = statuses.get(gap["gap_id"])
        status = record["status"] if record else "unknown"
        entry = {
            "gap_id": gap["gap_id"], "item_key": gap["item_key"],
            "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
            "authorship": gap.get("authorship"),
            "quote": gap["quote"], "translation_zh": gap["translation_zh"],
            "source": gap.get("source"), "page": gap.get("page"),
            "named_by_user": gap.get("named_by_user", False),
        }
        if status == "done_by_self":
            blacklist.append({
                "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                "completed_by_item_key": (record.get("candidate_paper_ids") or [None])[0],
                "evidence": record.get("model_evidence"),
                "quote_trunc": truncate(gap["quote"], 120),
                "translation_zh": truncate(gap["translation_zh"], 120),
                "confidence": record.get("confidence"),
                "evaluated_at": record.get("evaluated_at")})
            continue
        if not record:
            entry.update({"status": "unknown", "evidence": None, "confidence": "low",
                          "evaluated_at": None, "not_judged": True,
                          "completed_part": None, "remaining_gap": None,
                          "candidate_paper_ids": []})
        else:
            entry.update({
                "status": record["status"], "evidence": record.get("model_evidence"),
                "confidence": record.get("confidence"),
                "evaluated_at": record.get("evaluated_at"),
                "completed_part": record.get("completed_part"),
                "remaining_gap": record.get("remaining_gap"),
                "candidate_paper_ids": record.get("candidate_paper_ids") or [],
                "cache_hit": bool(record.get("cache_hit")),
                "downgraded": bool(record.get("downgraded"))})
        anchorable.append(entry)
    size = shortlist_size(len(anchorable))
    shortlist = anchorable[:size]
    shortlist_ids = {g["gap_id"] for g in shortlist}
    excluded, number = [], len(shortlist)
    for gap in anchorable[size:]:
        number += 1
        excluded.append({
            "gap_id": gap["gap_id"], "item_key": gap["item_key"],
            "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
            "authorship": gap.get("authorship"), "quote": gap.get("quote"),
            "translation_zh": gap.get("translation_zh"), "source": gap.get("source"),
            "page": gap.get("page"), "status": gap.get("status"),
            "evidence": gap.get("evidence"), "confidence": gap.get("confidence"),
            "completed_part": gap.get("completed_part"),
            "remaining_gap": gap.get("remaining_gap"),
            "candidate_paper_ids": gap.get("candidate_paper_ids") or [],
            "quote_trunc": truncate(gap["quote"], 80),
            "reason": "low_rank（本轮未选，不代表不重要）"})
    supporting = []
    direction = plan["direction"]
    relevant_keys = direction_relevant_keys(direction)
    ordered = sorted(relevant_keys, key=lambda k: (
        0 if k in (direction.get("named_keys") or []) else 1,
        -(ctx.papers[k].get("year") or 0) if k in ctx.papers else 0, k))
    for key in ordered:
        paper = ctx.papers.get(key)
        if not paper:
            continue
        facts_record, facts_state, facts_error = ctx.facts_for(key)
        supporting.append({
            "item_key": key, "title": paper.get("title"), "year": paper.get("year"),
            "authorship": paper.get("authorship"),
            "named_by_user": key in (direction.get("named_keys") or []),
            "has_analysis": bool(paper.get("analysis_file")),
            "analysis_file": paper.get("analysis_file"),
            "pdf_available": bool(paper.get("has_pdf")),
            "facts_state": facts_state,
            "facts_error": facts_error,
            "paper_facts": facts_record,
        })
    note = direction.get("user_note") or ""
    return {
        "collection_key": plan["ckey"],
        "name_ja": direction.get("name_ja"), "name_zh": direction.get("name_zh"),
        "status": direction.get("status") or "active",
        "input_fingerprint": plan["fingerprint"],
        "user_note": note,
        "credibility": direction.get("credibility") or {},
        "red_lines": direction.get("red_lines") or [],
        "named_keys": list(direction.get("named_keys") or []),
        "supporting_papers": supporting,
        "gap_pool_count": len(plan["pool"]),
        "gap_shortlist": [
            dict(g, no=index + 1) for index, g in enumerate(shortlist)],
        "gaps_excluded": excluded,
        "completed_gap_blacklist": blacklist,
        "version_families": ctx.families,
        "authorship_line": (direction.get("credibility") or {}).get("authorship_line"),
        "narrative": narrative,
    }


def render_analysis_md(ctx: Stage2Context, pack_directions: list,
                       state_fingerprint: str) -> str:
    professor = ctx.professor
    full = sum(1 for d in pack_directions for p in d["supporting_papers"] if p.get("has_analysis") or p.get("pdf_available"))
    abstracted = sum(1 for d in pack_directions for p in d["supporting_papers"]) - full
    lines = [
        f"# 套磁候选分析 — {professor}",
        "",
        "$$\\newcommand{\\dif}{\\mathop{}\\!\\mathrm{d}}$$",
        "",
        f"> {now_utc()} ｜ 数据来源：全文级 {full} 篇 · 摘要级 {abstracted} 篇（共 {full + abstracted} 篇）｜ 由 contact_state 确定性渲染（重跑=全量重写）",
        "",
    ]
    global_lines = []
    for d in pack_directions:
        for red in d.get("red_lines", []):
            if red.get("scope") == "global":
                text = red.get("text", "").strip()
                if text and text not in global_lines:
                    global_lines.append(redact_item_keys(text, ctx.papers))
    lines.append("## 全局须知")
    lines.append("")
    for text in global_lines:
        lines.append(f"- 【全局】{text}")
    if not global_lines:
        lines.append("-（无跨方向红线）")
    lines.append("")
    for index, d in enumerate(pack_directions, start=1):
        credibility = d.get("credibility") or {}
        verdict = credibility.get("verdict") or "未判定"
        mainline = credibility.get("mainline") or "未判定"
        authorship_line = credibility.get("authorship_line") or "insufficient"
        years = [p.get("year") for p in d["supporting_papers"] if p.get("year")]
        span = f"{min(years)}–{max(years)}" if years else "年份不明"
        lines.append(f"## 方向 {index}：{d['name_ja']}（{d.get('name_zh') or ''}）")
        lines.append("")
        # Show resolution info if available
        rd = d.get("resolved_direction")
        if rd and rd.get("resolution_type") and rd["resolution_type"] != "unchanged":
            res_type_label = {
                "renamed": "重命名",
                "split_from": "拆分",
                "merged_into": "合并",
                "refined": "修正",
            }.get(rd["resolution_type"], rd["resolution_type"])
            lines.append(f"> 方向解析：{res_type_label}（provisional → resolved）")
            if rd.get("papers_to_remove"):
                removed_titles = [ctx.papers.get(k, {}).get("title", k) for k in rd["papers_to_remove"]]
                lines.append(f"> - 移除论文：{'、'.join(removed_titles)}")
            if rd.get("papers_to_add"):
                added_titles = [ctx.papers.get(k, {}).get("title", k) for k in rd["papers_to_add"]]
                lines.append(f"> + 新增论文：{'、'.join(added_titles)}")
            lines.append("")
        lines.append("### 方向定位")
        lines.append("")
        lines.append(f"<可信度一句：{verdict} ｜ {mainline} ｜ 相关 {len(d['supporting_papers'])} 篇（{span}）。>")
        lines.append("")
        lines.append(f"<署名线：{authorship_line}。>")
        lines.append("")
        seen = {}
        narrative = d.get("narrative") or {}
        paper_lookup = {p["item_key"]: p for p in d["supporting_papers"]}
        gap_no = {g["gap_id"]: g["no"] for g in d.get("gap_shortlist", [])}
        for block in narrative.get("positioning", []):
            text = block["text"]

            def replace(match, seen=seen, paper_lookup=paper_lookup, gap_no=gap_no):
                kind, value = match.group(1), match.group(2)
                if kind == "G":
                    number = gap_no.get(value)
                    return f"future work #{number}" if number else "future work（本轮未选，见排除清单）"
                paper = paper_lookup.get(value) or {"title": ctx.papers.get(value, {}).get("title"),
                                                    "year": ctx.papers.get(value, {}).get("year"),
                                                    "analysis_file": ctx.papers.get(value, {}).get("analysis_file")}
                return citation_render(value, paper, ctx.professor_dir, seen)

            text = PLACEHOLDER_RE.sub(replace, text)
            examples = "；具体对象：{}；输入：{}；输出：{}。".format(
                block.get("concrete_object", ""), block.get("input_example", ""),
                block.get("output_example", ""))
            text += examples
            prefix = "- " if block.get("kind") == "bullet" else ""
            lines.append(f"{prefix}{text}")
        lines.append("")
        lines.append("### 论文一览")
        lines.append("")
        lines.append("| 论文 | 年份 | 署名 | 分析 | 来源 |")
        lines.append("|---|---|---|---|---|")
        for p in d["supporting_papers"]:
            analysis_cell = "—"
            if p.get("analysis_file"):
                analysis_cell = f"[分析]({rel_path(Path(p['analysis_file']), ctx.professor_dir)})"
            if p.get("resolved_addition"):
                source_cell = "全文验证新增"
            elif p.get("named_by_user"):
                source_cell = "用户指定"
            else:
                source_cell = "provisional"
            lines.append(f"| [{p['title']}](zotero://select/library/items/{p['item_key']}) | {p.get('year') or '—'} | {p.get('authorship') or 'pending'} | {analysis_cell} | {source_cell} |")
        lines.append("")
        lines.append("### 用户笔记（原文）")
        lines.append("")
        if d.get("user_note"):
            for note_line in d["user_note"].splitlines():
                lines.append(f"> {note_line}" if note_line else ">")
        else:
            lines.append("> 仅打标记，未写用户笔记。")
        lines.append("")
        lines.append("### 可延伸方向")
        lines.append("")
        gap_notes = narrative.get("gap_notes") or {}
        for gap in d.get("gap_shortlist", []):
            note_entry = gap_notes.get(gap["gap_id"], {})
            summary = note_entry.get("summary") or truncate(gap["translation_zh"] or gap["quote"], 60)
            explanation = note_entry.get("explanation")
            number = gap["no"]
            lines.append(f"1. 【作者 future work】{summary}（源自 [{gap['paper_title']}](zotero://select/library/items/{gap['item_key']})，{gap.get('paper_year') or '年份不明'}）")
            details = [
                f"- 作者原话：「{gap['quote']}」",
                f"- 中译：{gap['translation_zh']}",
                f"- 页码：p.{gap.get('page')}（{gap.get('source')}）",
                f"- 当前状态：{gap.get('status')}（置信度 {gap.get('confidence')}）",
                f"- 后续论文依据：{gap.get('evidence') or '—'}",
                f"- 评估时间：{gap.get('evaluated_at') or '—'}",
            ]
            if gap.get("status") == "partial":
                details.append(f"- 已做部分：{gap.get('completed_part') or '—'}")
                details.append(f"- 剩余缺口：{gap.get('remaining_gap') or '—'}")
            if gap.get("status") == "unknown":
                details.append("- ⚠ 未查证是否已被后续工作实现（unknown 原因见后续论文依据）")
            if explanation:
                details.append(f"- 大白话：{explanation}")
            lines.append(f"   <details><summary>freshness 卡 — future work #{number}</summary>")
            lines.append("")
            lines.extend(details)
            lines.append("")
            lines.append("   </details>")
        if not d.get("gap_shortlist"):
            lines.append("（本方向相关论文未明示可锚定的 future work，无可延伸点。）")
        if d.get("gaps_excluded"):
            lines.append("")
            names = "；".join(
                f"[{g['paper_title']}](zotero://select/library/items/{g['item_key']}) 的 1 条（{g['reason']}）"
                for g in d["gaps_excluded"])
            lines.append(f"> 另有 {len(d['gaps_excluded'])} 条本轮未选，不代表不重要：{names}。")
        if d.get("completed_gap_blacklist"):
            lines.append("")
            lines.append("**已被本人实现（禁锚）**")
            lines.append("")
            for item in d["completed_gap_blacklist"]:
                completed = item.get("completed_by_item_key")
                completed_render = (f"[{ctx.papers[completed].get('title')}](zotero://select/library/items/{completed})"
                                    if completed and completed in ctx.papers else "（完成论文见证据）")
                lines.append(f"- {item['quote_trunc']}——《{item['paper_title']}》（{item.get('paper_year')}）→ 已被 {completed_render} 接住（依据：{item.get('evidence')}）。")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cmd_stage2_finalize(args) -> None:
    ctx = Stage2Context(Path(args.facts))
    results_dir = Path(args.results)
    decision = None
    if getattr(args, "decision_file", None):
        decision_data, error = read_json_file(Path(args.decision_file))
        if error is None and isinstance(decision_data, dict):
            decision = decision_data.get("decision")

    # Load resolved directions if provided. Fail closed on any identity or
    # freshness problem: a sidecar from another professor, with a broken
    # schema, or built from different facts must NEVER be silently applied.
    resolved_directions = None
    resolved_directions_path = getattr(args, "resolved_directions", None)
    if resolved_directions_path:
        rd_data, rd_error = read_json_file(Path(resolved_directions_path))
        if rd_error is not None or not isinstance(rd_data, dict):
            fail("invalid_resolved_directions",
                 f"resolved directions file unreadable: {resolved_directions_path}")
        if rd_data.get("schema") != RESOLVED_DIRECTION_SCHEMA or \
                rd_data.get("kind") != "professor-contact-resolved-directions":
            fail("invalid_resolved_directions",
                 f"resolved directions schema/kind mismatch: {resolved_directions_path}")
        if rd_data.get("professor") != ctx.professor:
            fail("resolved_directions_professor_mismatch",
                 f"resolved directions file belongs to professor {rd_data.get('professor')!r}, "
                 f"not {ctx.professor!r}", path=str(resolved_directions_path))
        resolved_directions = {
            d["provisional_direction_id"]: d
            for d in rd_data.get("directions", [])
            if isinstance(d, dict) and isinstance(d.get("provisional_direction_id"), str)
        }
        # Per-direction freshness: every current direction must be covered by an
        # entry whose input_fingerprint matches the current facts. Stale or
        # missing entries fail closed so a half-updated resolved file can never
        # leak into the pack.
        stale = []
        for plan in ctx.direction_plans:
            entry = resolved_directions.get(plan["ckey"])
            if entry is None:
                stale.append({"direction": plan["ckey"], "problem": "missing_from_resolved_file"})
            elif entry.get("input_fingerprint") != _per_direction_fingerprint(plan["direction"], ctx.papers):
                stale.append({"direction": plan["ckey"], "problem": "input_fingerprint_mismatch"})
        if stale:
            fail("resolved_directions_stale",
                 "resolved directions do not match current facts; re-run stage2-resolve",
                 stale_directions=stale, path=str(resolved_directions_path))

    required_freshness, needed_keys = {}, []
    for plan in ctx.direction_plans:
        if plan["reuse"]:
            continue
        needed_keys.append(plan["ckey"])
        judge, hits = ctx.freshness_job_items(plan)
        required_freshness[plan["ckey"]] = judge
    statuses_by_direction = validate_freshness_results(ctx, results_dir, required_freshness)
    narratives = validate_narrative(ctx, results_dir, needed_keys) if needed_keys else {}
    old_directions = {e.get("collection_key"): e for e in (ctx.pack or {}).get("directions", [])}
    old_render = ((ctx.pack or {}).get("cache") or {}).get("render", {})
    pack_directions = []
    for plan in ctx.direction_plans:
        if plan["reuse"]:
            pack_directions.append(old_directions[plan["ckey"]])
        else:
            pack_directions.append(build_direction_pack(
                ctx, plan, statuses_by_direction.get(plan["ckey"], {}),
                narratives[plan["ckey"]]))

    # Apply resolved directions to pack_directions. Every direction (including
    # unchanged) gets an explicit resolved_direction subfield so downstream
    # stages consume the authoritative resolved ID and never implicitly fall
    # back to the provisional collection_key.
    if resolved_directions:
        # Keep the provisional fingerprints around: the public
        # `input_fingerprint` is recomputed below to the resolved-aware
        # downstream value, but Stage-2's own freshness gate still needs the
        # pre-resolution value to judge reuse on the next run. A reused pack
        # entry already carries the resolved-aware value in
        # `input_fingerprint`, so the provisional value MUST come from
        # `provisional_input_fingerprint` when present — overwriting it with
        # the downstream hash would silently break the next Stage-2 reuse.
        provisional_fingerprints = {
            d["collection_key"]: d.get("provisional_input_fingerprint") or d.get("input_fingerprint")
            for d in pack_directions}
        reused_ckeys = {p["ckey"] for p in ctx.direction_plans if p["reuse"]}

        # Carry forward accepted derived directions (split children created by
        # a previous finalize). They have no provisional plan entry because the
        # facts only know the source direction, so without this a reuse
        # finalize would silently drop the child — and the split pass would
        # then rebuild it from the already-pruned source with empty membership.
        # A child is kept only while the current resolution still declares the
        # same split; otherwise the new resolution is authoritative and the
        # stale child disappears.
        plan_ckeys = {p["ckey"] for p in ctx.direction_plans}
        for old_entry in (ctx.pack or {}).get("directions", []):
            child_key = old_entry.get("collection_key") if isinstance(old_entry, dict) else None
            if not child_key or child_key in plan_ckeys:
                continue
            if any(d.get("collection_key") == child_key for d in pack_directions):
                continue
            source_rd = resolved_directions.get(old_entry.get("resolved_direction", {})
                                                .get("provisional_direction_id")) or {}
            if source_rd.get("resolution_type") != "split_from" \
                    or source_rd.get("split_target") != child_key:
                continue
            pack_directions.append(old_entry)
            provisional_fingerprints[child_key] = (
                old_entry.get("provisional_input_fingerprint")
                or old_entry.get("input_fingerprint"))

        def _find_pack_direction(ckey: str):
            for d in pack_directions:
                if d.get("collection_key") == ckey:
                    return d
            return None

        def _stamp_subfield(d: dict, rd: dict) -> None:
            d["resolved_direction"] = {
                "resolved_direction_id": rd.get("resolved_direction_id") or d.get("collection_key"),
                "provisional_direction_id": rd.get("provisional_direction_id") or d.get("collection_key"),
                "resolution_type": rd.get("resolution_type") or "unchanged",
                "input_fingerprint": rd.get("input_fingerprint"),
                "papers_to_add": list(rd.get("papers_to_add") or []),
                "papers_to_remove": list(rd.get("papers_to_remove") or []),
                "paper_justifications": dict(rd.get("paper_justifications") or {}),
                "split_target": rd.get("split_target"),
                "merge_target": rd.get("merge_target"),
            }

        def _resolved_paper_entry(key: str, justification: str) -> dict | None:
            """Build a supporting-papers entry straight from library + facts.

            Used when authoritative membership admits a paper the relevance
            gate never placed in the direction's supporting_papers (e.g. a
            full-text rescue that only lives in the candidate union). The
            resolve finalizer already validated facts_state == valid for every
            membership-changing key, so this never fabricates evidence.
            """
            paper = ctx.papers.get(key)
            if not paper:
                return None
            facts_record, facts_state, facts_error = ctx.facts_for(key)
            return {
                "item_key": key,
                "title": paper.get("title"),
                "year": paper.get("year"),
                "authorship": paper.get("authorship"),
                "named_by_user": False,
                "has_analysis": bool(paper.get("analysis_file")),
                "analysis_file": paper.get("analysis_file"),
                "pdf_available": bool(paper.get("has_pdf")),
                "facts_state": facts_state,
                "facts_error": facts_error,
                "paper_facts": facts_record,
                "resolved_addition": True,
                "addition_justification": justification,
            }

        def _apply_membership(d: dict, rd: dict) -> None:
            remove_set = set(rd.get("papers_to_remove") or [])
            if remove_set:
                d["supporting_papers"] = [
                    p for p in d.get("supporting_papers", [])
                    if p.get("item_key") not in remove_set]
            for add_key in rd.get("papers_to_add") or []:
                if any(p.get("item_key") == add_key for p in d.get("supporting_papers", [])):
                    continue
                entry = _resolved_paper_entry(
                    add_key, (rd.get("paper_justifications") or {}).get(add_key, ""))
                if entry is not None:
                    d.setdefault("supporting_papers", []).append(entry)

        # Pass 1: stamp the subfield everywhere + apply rename/refined edits.
        for d in pack_directions:
            rd = resolved_directions.get(d["collection_key"])
            if rd is None:
                continue  # carried-forward split child keeps its own subfield
            _stamp_subfield(d, rd)
            rtype = rd.get("resolution_type") or "unchanged"
            if rtype in ("renamed", "refined"):
                d["name_ja"] = rd.get("name_ja") or d.get("name_ja")
                d["name_zh"] = rd.get("name_zh") or d.get("name_zh")
            if rtype == "refined":
                _apply_membership(d, rd)

        # Pass 2: split_from creates a REAL new authoritative direction entry;
        # the source keeps its identity minus the split-out papers/gaps.
        for d in list(pack_directions):
            ckey = d["collection_key"]
            rd = resolved_directions.get(ckey)
            if rd is None or rd.get("resolution_type") != "split_from":
                continue
            split_id = rd.get("split_target")
            split_set = set(rd.get("papers_to_add") or [])
            # Prune the source first: idempotent on an already-pruned reuse entry.
            moved_papers = [p for p in d.get("supporting_papers", []) if p.get("item_key") in split_set]
            d["supporting_papers"] = [p for p in d.get("supporting_papers", [])
                                      if p.get("item_key") not in split_set]
            moved_shortlist = [g for g in d.get("gap_shortlist", []) if g.get("item_key") in split_set]
            kept_shortlist = [g for g in d.get("gap_shortlist", []) if g.get("item_key") not in split_set]
            d["gap_shortlist"] = [dict(g, no=index + 1) for index, g in enumerate(kept_shortlist)]
            moved_excluded = [g for g in d.get("gaps_excluded", []) if g.get("item_key") in split_set]
            d["gaps_excluded"] = [g for g in d.get("gaps_excluded", [])
                                  if g.get("item_key") not in split_set]
            moved_blacklist = [b for b in d.get("completed_gap_blacklist", []) if b.get("item_key") in split_set]
            d["completed_gap_blacklist"] = [b for b in d.get("completed_gap_blacklist", [])
                                            if b.get("item_key") not in split_set]
            split_named = [k for k in d.get("named_keys", []) if k in split_set]
            d["named_keys"] = [k for k in d.get("named_keys", []) if k not in split_set]
            provisional_fingerprints[split_id] = provisional_fingerprints.get(ckey) \
                or d.get("input_fingerprint")
            existing_child = _find_pack_direction(split_id)
            if existing_child is not None and ckey in reused_ckeys:
                # The child was materialized by an earlier finalize and the
                # source hit Stage-2 reuse: keep the accepted child membership
                # exactly as-is. Rebuilding it from the reuse (already-pruned)
                # source would silently empty it.
                continue
            if existing_child is not None:
                # Source was reprocessed (facts changed and resolve re-ran with
                # the same split target): rebuild the child from the freshly
                # built source so papers/gap references stay current.
                pack_directions.remove(existing_child)
            # A full-text rescue can put a candidate-union paper into the split
            # even though the abstract relevance gate never put it into the
            # source's supporting_papers; materialize those from the library.
            present = {p.get("item_key") for p in moved_papers}
            for key in sorted(split_set - present):
                entry = _resolved_paper_entry(
                    key, (rd.get("paper_justifications") or {}).get(key, ""))
                if entry is not None:
                    moved_papers.append(entry)
            pack_directions.append({
                "collection_key": split_id,
                "name_ja": rd.get("name_ja") or d.get("name_ja"),
                "name_zh": rd.get("name_zh") or "",
                "status": "active",
                "input_fingerprint": d.get("input_fingerprint"),
                "user_note": rd.get("user_note") or "",
                "credibility": d.get("credibility") or {},
                "red_lines": [r for r in d.get("red_lines", []) if r.get("scope") != "global"],
                "named_keys": split_named,
                "supporting_papers": moved_papers,
                "gap_pool_count": len(moved_shortlist) + len(moved_excluded),
                "gap_shortlist": [dict(g, no=index + 1) for index, g in enumerate(moved_shortlist)],
                "gaps_excluded": moved_excluded,
                "completed_gap_blacklist": moved_blacklist,
                "version_families": d.get("version_families"),
                "authorship_line": d.get("authorship_line"),
                "narrative": {},
                "resolved_direction": {
                    "resolved_direction_id": split_id,
                    "provisional_direction_id": ckey,
                    "resolution_type": "split_from",
                    "input_fingerprint": rd.get("input_fingerprint"),
                    "papers_to_add": sorted(split_set),
                    "papers_to_remove": [],
                    "paper_justifications": dict(rd.get("paper_justifications") or {}),
                    "split_target": split_id,
                    "merge_target": None,
                },
            })

        # Pass 3: merged_into folds the source into the target and DROPS the
        # source direction entry, transplanting papers/gaps so references and
        # evidence survive; the pack-root index keeps the source→target mapping.
        merged_sources = []
        for d in list(pack_directions):
            ckey = d["collection_key"]
            rd = resolved_directions.get(ckey)
            if rd is None:
                continue  # split target created in pass 2; not a merge source
            if rd.get("resolution_type") != "merged_into":
                continue
            target = _find_pack_direction(rd.get("merge_target"))
            if target is None:
                fail("invalid_resolved_directions",
                     f"merge target {rd.get('merge_target')} not present in pack")
            for p in d.get("supporting_papers", []):
                key = p.get("item_key")
                if any(q.get("item_key") == key for q in target.get("supporting_papers", [])):
                    continue
                merged_paper = dict(p)
                merged_paper["resolved_addition"] = True
                merged_paper["addition_justification"] = f"merged_from {ckey}"
                target.setdefault("supporting_papers", []).append(merged_paper)
            offset = len(target.get("gap_shortlist", []))
            for index, g in enumerate(d.get("gap_shortlist", [])):
                if any(q.get("gap_id") == g.get("gap_id") for q in target.get("gap_shortlist", [])):
                    continue
                target.setdefault("gap_shortlist", []).append(dict(g, no=offset + index + 1))
            for g in d.get("gaps_excluded", []):
                if not any(q.get("gap_id") == g.get("gap_id") for q in target.get("gaps_excluded", [])):
                    target.setdefault("gaps_excluded", []).append(dict(g))
            for b in d.get("completed_gap_blacklist", []):
                if not any(q.get("gap_id") == b.get("gap_id") for q in target.get("completed_gap_blacklist", [])):
                    target.setdefault("completed_gap_blacklist", []).append(dict(b))
            target_rd = target.get("resolved_direction") or {}
            merged_from = list(target_rd.get("merged_from") or [])
            merged_from.append(ckey)
            target_rd["merged_from"] = merged_from
            target["resolved_direction"] = target_rd
            merged_sources.append(ckey)
        if merged_sources:
            dropped = set(merged_sources)
            pack_directions = [d for d in pack_directions if d.get("collection_key") not in dropped]

        # Recompute the downstream `input_fingerprint` AFTER the resolution has
        # been materialized. Stage 3's reuse gate compares this field, so it
        # must reflect the authoritative identity (resolved ID, final names)
        # and the FINAL membership/gap set — otherwise a refined/split/merged
        # direction would let Stage 3 silently reuse candidates that reference
        # papers or gaps the resolution just moved or removed. Split entries
        # get an independent fingerprint computed from their own final content.
        for d in pack_directions:
            rd = d.get("resolved_direction") or {}
            d["provisional_input_fingerprint"] = provisional_fingerprints.get(
                d.get("collection_key"), d.get("input_fingerprint"))
            d["input_fingerprint"] = sha256_obj({
                "downstream_version": 2,
                "provisional_fingerprint": d["provisional_input_fingerprint"],
                "resolved_identity": {
                    "resolved_direction_id": rd.get("resolved_direction_id") or d.get("collection_key"),
                    "provisional_direction_id": rd.get("provisional_direction_id") or d.get("collection_key"),
                    "resolution_type": rd.get("resolution_type") or "unchanged",
                    "name_ja": d.get("name_ja"),
                    "name_zh": d.get("name_zh"),
                    "merged_from": rd.get("merged_from") or [],
                },
                "final_supporting_keys": sorted(
                    p.get("item_key") for p in d.get("supporting_papers", []) if p.get("item_key")),
                "final_gap_ids": sorted(
                    g.get("gap_id") for g in d.get("gap_shortlist", []) if g.get("gap_id")),
            })

    fingerprints = {d["collection_key"]: d["input_fingerprint"] for d in pack_directions}
    state_fingerprint = sha256_obj({"professor": ctx.professor, "directions": fingerprints})
    cache_entries = dict(ctx.cache)
    for ckey, statuses in statuses_by_direction.items():
        for gap_id, record in statuses.items():
            if isinstance(record, dict) and not record.get("cache_hit"):
                cache_entries[gap_id] = {k: v for k, v in record.items() if k != "cache_hit"}
    md_path = ctx.professor_dir / ANALYSIS_MD
    md_result = None
    if needed_keys or not ctx.pack:
        body = render_analysis_md(ctx, pack_directions, state_fingerprint)
        md_result = managed_write(md_path, body, state_fingerprint,
                                  old_render.get(ANALYSIS_MD, {}).get("sha256"), decision)
        if md_result.get("needs_decision"):
            soft_exit("needs_decision", md_result["reason_code"],
                      target=md_result.get("target"),
                      existing_sha256=md_result.get("existing_sha256"),
                      new_sha256=md_result.get("new_sha256"),
                      options=["overwrite（覆盖为状态版本）", "keep_manual（保留手改，不作为流程输入）",
                               "promote（把要保留的内容经 selection.note 或 profile 写进状态后再渲染）"])
    pack = {
        "schema": SCHEMA, "managed_by": MANAGED_BY, "generated_at": now_utc(),
        "professor": ctx.professor, "professor_dir": str(ctx.professor_dir),
        "directions": pack_directions,
        "cache": {"render": {ANALYSIS_MD: {"sha256": (md_result or {}).get("sha256") or old_render.get(ANALYSIS_MD, {}).get("sha256")}}},
    }
    if resolved_directions:
        pack["resolved_directions"] = {
            "schema": RESOLVED_DIRECTION_SCHEMA,
            "applied_at": now_utc(),
            "directions": [
                {
                    "provisional_direction_id": ckey,
                    "resolved_direction_id": rd.get("resolved_direction_id"),
                    "resolution_type": rd.get("resolution_type"),
                    "split_target": rd.get("split_target"),
                    "merge_target": rd.get("merge_target"),
                    "input_fingerprint": rd.get("input_fingerprint"),
                }
                for ckey, rd in resolved_directions.items()
            ],
        }
    if ctx.pack and not needed_keys and ctx.pack.get("validator"):
        pack["validator"] = ctx.pack["validator"]
    atomic_json(ctx.pack_path, pack)
    save_freshness_cache(ctx.professor_dir, cache_entries)
    judged = sum(1 for statuses in statuses_by_direction.values()
                 for record in statuses.values()
                 if isinstance(record, dict) and not record.get("cache_hit"))
    emit({
        "status": "ok",
        "professor": ctx.professor,
        "pack_path": str(ctx.pack_path),
        "analysis_md": str(md_path),
        "directions": [{"collection_key": d["collection_key"],
                        "shortlist": len(d.get("gap_shortlist", [])),
                        "blacklist": len(d.get("completed_gap_blacklist", [])),
                        "excluded": len(d.get("gaps_excluded", [])),
                        "resolved": bool(resolved_directions and d["collection_key"] in resolved_directions
                                         and resolved_directions[d["collection_key"]].get("resolution_type") != "unchanged")}
                       for d in pack_directions],
        "freshness_judged": judged, "freshness_cache_total": len(cache_entries),
        "md_sha256": (md_result or {}).get("sha256"),
        "resolved_directions_applied": bool(resolved_directions),
    })


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


def cmd_stage3_plan(args) -> None:
    professor_dir = Path(args.professor_dir)
    program_root = Path(args.program_root) if args.program_root else professor_dir.parent.parent
    require_professor_dir_under_program(professor_dir, program_root)
    pack_path = professor_dir / INPUT_PACK
    pack, error = read_json_file(pack_path)
    if error:
        soft_exit("needs_refresh", "missing_input_pack",
                  pack_path=str(pack_path),
                  message="缺 套磁候选输入.json：先跑阶段 2（professor-contact-analyzer）生成输入包；不回读任何 Markdown。")
    refresh_scope = args.refresh_scope or "flagged"
    if refresh_scope not in REFRESH_SCOPES:
        fail("invalid_params", f"refresh_scope must be one of {REFRESH_SCOPES}")
    collection_key = getattr(args, "collection_key", None)
    pack_directions = pack.get("directions") or []
    if collection_key and not any(d.get("collection_key") == collection_key
                                  for d in pack_directions):
        fail("invalid_params", f"collection_key not found in input pack: {collection_key}")
    state, _ = read_json_file(professor_dir / CANDIDATE_STATE)
    state = state if isinstance(state, dict) else None
    current_profile_fp = profile_fingerprint(args.profile)
    old_profile_fp = (state or {}).get("profile_fingerprint")
    profile_changed = bool(state) and current_profile_fp != old_profile_fp
    selected_keys = None
    if refresh_scope == "selected":
        selection_path = args.selection or (Path(args.program_root) / "教授研究" / SELECTION_FILE)
        selection_data, sel_error = read_json_file(Path(selection_path))
        if sel_error:
            fail("invalid_params", f"selection file unreadable: {selection_path}")
        selected_keys = set()
        for sel in selection_data.get("selections", []):
            if sel.get("professor") == pack.get("professor"):
                selected_keys.add(sel.get("collection_key"))
    jobs, reuse = [], []
    input_fps = (state or {}).get("input_fingerprints", {})
    for direction in pack_directions:
        ckey = direction.get("collection_key")
        if collection_key and ckey != collection_key:
            continue
        if refresh_scope == "flagged" and direction.get("status") != "active":
            continue
        if refresh_scope == "selected" and ckey not in (selected_keys or set()):
            continue
        fp_match = input_fps.get(ckey) == direction.get("input_fingerprint")
        if fp_match and not profile_changed:
            old_direction = next((d for d in (state or {}).get("directions", [])
                                  if d.get("collection_key") == ckey), None)
            if old_direction and old_direction.get("candidates") is not None:
                reuse.append(ckey)
                continue
        gap_lines = []
        for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
            gap_lines.append({
                "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                "authorship": gap.get("authorship"),
                "quote": truncate(gap.get("quote"), QUOTE_INPUT_CHARS),
                "translation_zh": truncate(gap.get("translation_zh"), TRANSLATION_INPUT_CHARS),
                "status": gap.get("status"), "evidence": gap.get("evidence"),
                "completed_part": gap.get("completed_part"),
                "remaining_gap": gap.get("remaining_gap"),
                "confidence": gap.get("confidence"),
                "shortlisted": gap in direction.get("gap_shortlist", [])})
        blacklist = [{"gap_id": b["gap_id"], "item_key": b["item_key"],
                      "paper_title": b.get("paper_title"),
                      "completed_by": b.get("completed_by_item_key"),
                      "evidence": b.get("evidence")}
                     for b in direction.get("completed_gap_blacklist", [])]
        mode = "refined" if direction.get("user_note") else "generated"
        jobs.append({
            "job_id": f"candidates:{pack.get('professor')}:{ckey}",
            "kind": "candidates", "collection_key": ckey,
            "result_file": f"candidates-{ckey}.json",
            "model_input": {
                "mode": mode,
                "user_note": direction.get("user_note") or "",
                "credibility": direction.get("credibility"),
                "red_lines": direction.get("red_lines") or [],
                "supporting_papers": [{"item_key": p["item_key"], "title": p.get("title"),
                                       "year": p.get("year"), "authorship": p.get("authorship"),
                                       "named_by_user": p.get("named_by_user")}
                                      for p in direction.get("supporting_papers", [])],
                "gaps": gap_lines,
                "completed_gap_blacklist": blacklist,
                "profile_text": load_profile_text(args.profile),
                "rules": {
                    "research_question": "每个候选必须非空研究问题（求知式表述）；写不出 → 不列该候选，把要点并入主候选展开末尾（前缀「配套承诺：」）",
                    "gap_anchor": "gap_ids 只能引用 model_input.gaps / completed_gap_blacklist 里的精确 (item_key,gap_id)；done_by_self 只能以【我的延伸】+difference_point 差异点方式出现；partial 候选必须写 remaining_gap 关注点；unknown 候选必须带 unverified:true",
                    "papers": "候选 papers[] 只给 {item_key, role, fit_note}；标题/年份/署名由 runner 从输入包回填，禁止自写标题",
                    "count": "generated 模式 3-5 个候选；refined 模式给 refined 块 + 0-3 个补充候选",
                    "diversity": "候选之间切入点/所挂 gap 不重复"}}})
    emit({
        "status": "ok",
        "professor": pack.get("professor"),
        "professor_dir": str(professor_dir),
        "refresh_scope": refresh_scope,
        "collection_key": collection_key,
        "profile_fingerprint": current_profile_fp,
        "profile_changed_reason": "profile_changed" if profile_changed else None,
        "directions": [{"collection_key": d.get("collection_key"),
                        "action": ("reuse" if d.get("collection_key") in reuse else
                                   ("skipped" if d.get("collection_key") not in
                                     [j["collection_key"] for j in jobs] else "process"))}
                        for d in pack_directions
                        if not collection_key or d.get("collection_key") == collection_key],
        "jobs": jobs,
        "write_needed": bool(jobs),
    })


def validate_candidate_result(pack_direction: dict, data: Any, path: Path) -> dict:
    if not isinstance(data, dict) or data.get("schema") != 1 or data.get("kind") != "candidates":
        fail("invalid_result_json", f"{path}: schema/kind must be 1/candidates")
    ckey = data.get("collection_key")
    if ckey != pack_direction.get("collection_key"):
        fail("invalid_result_json", f"{path}: collection_key mismatch")
    mode = data.get("mode")
    if mode not in ("refined", "generated"):
        fail("invalid_result_json", f"{path}: mode must be refined|generated")
    if mode == "refined" and not (pack_direction.get("user_note") or "").strip():
        fail("invalid_result_json", f"{path}: refined mode without user note")
    gap_index = {}
    for gap in pack_direction.get("gap_shortlist", []) + [
            dict(g, status=g.get("status")) for g in pack_direction.get("gaps_excluded", [])]:
        gap_index[(gap["item_key"], gap["gap_id"])] = gap
    blacklist = {(b["item_key"], b["gap_id"]): b
                 for b in pack_direction.get("completed_gap_blacklist", [])}
    paper_index = {p["item_key"]: p for p in pack_direction.get("supporting_papers", [])}
    for gap in pack_direction.get("gap_shortlist", []) + pack_direction.get("gaps_excluded", []):
        paper_index.setdefault(gap["item_key"], {
            "item_key": gap["item_key"], "title": gap.get("paper_title"),
            "year": gap.get("paper_year"), "authorship": gap.get("authorship")})
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
            if key not in gap_index and key not in blacklist:
                fail("unknown_reference_id", f"{path}: refined gap {key} outside package")
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        fail("invalid_result_json", f"{path}: candidates must be a list")
    if mode == "generated" and not 3 <= len(candidates) <= 5:
        fail("invalid_result_json", f"{path}: generated mode needs 3-5 candidates")
    if mode == "refined" and len(candidates) > 3:
        fail("invalid_result_json", f"{path}: refined mode allows at most 3 supplementary candidates")
    checked = []
    seen_ids = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            fail("invalid_result_json", f"{path}: candidates[] must be objects")
        if candidate.get("id") is not None and not isinstance(candidate.get("id"), str):
            fail("invalid_result_json", f"{path}: candidate id must be a string")
        cid = (candidate.get("id") or "").strip()
        if not cid or cid in seen_ids:
            fail("invalid_result_json", f"{path}: candidate id required and unique: {cid!r}")
        seen_ids.add(cid)
        for field in ("title", "one_liner", "research_question", "fit_note", "why_recommended"):
            if candidate.get(field) is not None and not isinstance(candidate.get(field), str):
                fail("invalid_result_json", f"{path}: candidate {cid} field {field} must be a string")
        if not (candidate.get("research_question") or "").strip():
            fail("invalid_result_json",
                 f"{path}: candidate {cid} 缺非空研究问题（求知式）；纯交付物候选应并入主候选而非单列")
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
        raw_gap_ids = candidate.get("gap_ids") or []
        if not isinstance(raw_gap_ids, list) or not all(isinstance(pair, dict) for pair in raw_gap_ids):
            fail("invalid_result_json", f"{path}: candidate {cid} gap_ids must be an object list")
        gap_pairs = []
        seen_gap_pairs = set()
        for pair in raw_gap_ids:
            key = (pair.get("item_key"), pair.get("gap_id"))
            if key in seen_gap_pairs:
                fail("invalid_result_json", f"{path}: candidate {cid} contains duplicate gap {key}")
            seen_gap_pairs.add(key)
            in_pool = key in gap_index
            in_blacklist = key in blacklist
            if not in_pool and not in_blacklist:
                fail("unknown_reference_id", f"{path}: candidate {cid} gap {key} outside package")
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
                         f"{path}: candidate {cid} uses done_by_self gap {key} without my_extension difference_point")
            gap_pairs.append({"item_key": key[0], "gap_id": key[1],
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
            papers.append({"item_key": item_key, "title": source.get("title"),
                           "year": source.get("year"), "authorship": source.get("authorship"),
                           "role": (paper.get("role") or "").strip(),
                           "fit_note": (paper.get("fit_note") or "").strip()})
        has_author_gap = any(not g["done_by_self"] for g in gap_pairs)
        anchor_type = "author_future_work" if gap_pairs and has_author_gap else (
            "my_extension" if gap_pairs else "none")
        checked.append({
            "id": cid,
            "title": (candidate.get("title") or "").strip(),
            "one_liner": (candidate.get("one_liner") or "").strip(),
            "research_question": candidate.get("research_question").strip(),
            "points": [str(x) for x in (candidate.get("points") or [])],
            "gap_ids": gap_pairs,
            "anchor_type": anchor_type,
            "anchor_notes": anchor_notes,
            "papers": papers,
            "fit": candidate.get("fit") if candidate.get("fit") in ("high", "partial", "weak", "null") else "null",
            "fit_note": (candidate.get("fit_note") or "").strip(),
            "red_lines": [str(x) for x in (candidate.get("red_lines") or [])],
            "why_recommended": (candidate.get("why_recommended") or "").strip(),
            "tension_points": [str(x) for x in (candidate.get("tension_points") or [])]})
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
    return {"collection_key": ckey, "mode": mode, "refined": refined_checked,
            "candidates": checked, "priority": priority.strip()}


def render_candidates_md(professor: str, category: str, direction_entries: list,
                         profile_fp: str | None, state_fingerprint: str,
                         professor_dir: Path) -> str:
    lines = [
        f"# 套磁想法候选 — {professor}（{category}）",
        "",
        "$$\\newcommand{\\dif}{\\mathop{}\\!\\mathrm{d}}$$",
        "",
        f"> {now_utc()} ｜ profile：{'有' if profile_fp else '无'}{'（未按个人资料校准）' if not profile_fp else ''} ｜ 由 contact_state 确定性渲染；方向脉络与 future work 原文见同目录《套磁候选分析.md》，本文件不复述",
        "",
    ]
    for entry in direction_entries:
        credibility = entry.get("credibility") or {}
        verdict = credibility.get("verdict") or "未判定"
        lines.append(f"## {entry['name_ja']}（{entry.get('name_zh') or ''}）")
        lines.append("")
        lines.append(f"> 脉络、论文一览、用户笔记 → 见《套磁候选分析.md》。")
        red_lines = [r for r in entry.get("red_lines", []) if r.get("scope") != "global"]
        if red_lines:
            rendered = "；".join(f"【方向】{r.get('text', '').strip()}" for r in red_lines)
            lines.append(f"> 方向级共享红线（只在这里写一次）：{rendered}")
        if verdict in ("勉强", "疑似幻觉"):
            lines.append("> ⚠️ 该方向归类存疑，建议对教授跑 force:true 重聚类后重新考虑；候选内容仍基于论文实际内容。")
        lines.append("")
        refined = entry.get("refined")
        if refined:
            lines.append("### 你的草稿修正版（基本方向，非终稿）")
            lines.append("")
            lines.append(f"- **保真**：{refined.get('core_intent') or '—'}")
            calibration = refined.get("calibration") or []
            lines.append(f"- **校准**：{'；'.join(calibration) if calibration else '无'}")
            lines.append(f"- **基本方向**：{refined.get('idea_zh')}")
            variants = refined.get("variants") or []
            if variants:
                lines.append(f"- **替代表述变体**：{'；'.join(variants)}")
            lines.append("")
        candidates = entry.get("candidates") or []
        paper_index = {}
        for d in (entry.get("_pack_papers") or []):
            paper_index[d["item_key"]] = d
        for number, candidate in enumerate(candidates, start=1):
            meta = {"id": candidate["id"],
                    "gap_ids": [{"item_key": g["item_key"], "gap_id": g["gap_id"]}
                                for g in candidate["gap_ids"]]}
            lines.append(f"### 候选 {number}：{candidate.get('title') or candidate['id']}（{candidate['id']}）")
            lines.append("")
            lines.append(f"<!-- candidate_meta: {json.dumps(meta, ensure_ascii=False)} -->")
            lines.append("")
            lines.append(f"**一句话**：{candidate.get('one_liner') or '—'}")
            lines.append("")
            lines.append(f"**研究问题**：{candidate['research_question']}")
            lines.append("")
            lines.append("**展开**：")
            for point in candidate.get("points", []):
                lines.append(f"- {point}")
            lines.append("")
            lines.append("**支撑论文**")
            lines.append("")
            lines.append("| 论文 | 年份 | 署名 | 作用 | 分析 |")
            lines.append("|---|---|---|---|---|")
            for paper in candidate.get("papers", []):
                key = paper["item_key"]
                meta_paper = paper_index.get(key) or {}
                analysis_rel = meta_paper.get("_analysis_rel")
                analysis_cell = f"[分析]({analysis_rel})" if analysis_rel else "—"
                lines.append(f"| [{paper['title']}](zotero://select/library/items/{key}) | {paper.get('year') or '—'} | {paper.get('authorship') or 'pending'} | {paper.get('role') or '—'} | {analysis_cell} |")
                if paper.get("authorship") == "middle" and (paper.get("role") or "").find("主支撑") >= 0:
                    pass
            lines.append("")
            fit_note = candidate.get("fit_note") or ""
            middle_flags = [p for p in candidate.get("papers", []) if p.get("authorship") == "middle"]
            if middle_flags:
                fit_note = (fit_note + " " if fit_note else "") + "⚠️ 此论文教授为中间作者"
            lines.append(f"**贴合度**：{candidate.get('fit')} — {fit_note or '—'}")
            lines.append("")
            if candidate.get("red_lines"):
                lines.append(f"**红线**：{'；'.join(candidate['red_lines'])}")
                lines.append("")
            lines.append(f"**为何值得推**：{candidate.get('why_recommended') or '—'}")
            if candidate.get("tension_points"):
                lines.append("")
                lines.append(f"**张力点**：{'；'.join(candidate['tension_points'])}")
            for gap in candidate["gap_ids"]:
                if gap.get("done_by_self"):
                    lines.append("")
                    lines.append(f"> 注：该候选踩着已完成 future work（{gap['gap_id'][:12]}…）作【我的延伸】，差异点见 anchor_notes。")
            lines.append("")
        if entry.get("priority"):
            lines.append("## 推荐优先级")
            lines.append("")
            lines.append(entry["priority"])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_candidates_overview(entries: list, program_root: Path) -> str:
    lines = [
        "# 套磁想法候选总览",
        "",
        f"> {now_utc()} ｜ 由 contact_state 渲染；选好后跑阶段 4 professor-contact-selection。",
        "",
        "| 教授 | 方向 | 候选数 | 推荐顺序 | 文件 |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        count = len(entry.get("candidates") or [])
        priority = (entry.get("priority") or "").replace("\n", " ")[:40] or "—"
        md = entry.get("_candidates_md_rel") or "—"
        lines.append(f"| {entry['professor']} | {entry['name_ja']} | {count} | {priority} | [{CANDIDATES_MD}]({md}) |")
    lines.append("")
    return "\n".join(lines) + "\n"


def cmd_stage3_finalize(args) -> None:
    professor_dir = Path(args.professor_dir)
    program_root = Path(args.program_root) if args.program_root else professor_dir.parent.parent
    require_professor_dir_under_program(professor_dir, program_root)
    pack_path = professor_dir / INPUT_PACK
    pack, error = read_json_file(pack_path)
    if error:
        soft_exit("needs_refresh", "missing_input_pack", pack_path=str(pack_path))
    collection_key = getattr(args, "collection_key", None)
    pack_directions = pack.get("directions") or []
    if collection_key and not any(d.get("collection_key") == collection_key
                                  for d in pack_directions):
        fail("invalid_params", f"collection_key not found in input pack: {collection_key}")
    refresh_scope = args.refresh_scope or "flagged"
    state, _ = read_json_file(professor_dir / CANDIDATE_STATE)
    old_state = state if isinstance(state, dict) else None
    current_profile_fp = profile_fingerprint(args.profile)
    old_profile_fp = (old_state or {}).get("profile_fingerprint")
    profile_changed = bool(old_state) and current_profile_fp != old_profile_fp
    old_directions = {d.get("collection_key"): d for d in (old_state or {}).get("directions", [])}
    old_fps = (old_state or {}).get("input_fingerprints", {})
    selected_keys = None
    if refresh_scope == "selected":
        selection_path = args.selection or (Path(args.program_root) / "教授研究" / SELECTION_FILE)
        selection_data, sel_error = read_json_file(Path(selection_path))
        if sel_error:
            fail("invalid_params", f"selection file unreadable: {selection_path}")
        selected_keys = {sel.get("collection_key") for sel in selection_data.get("selections", [])
                         if sel.get("professor") == pack.get("professor")}
    results_dir = Path(args.results)
    decision = None
    if getattr(args, "decision_file", None):
        decision_data, derr = read_json_file(Path(args.decision_file))
        if derr is None and isinstance(decision_data, dict):
            decision = decision_data.get("decision")
    professor = pack.get("professor")
    category = professor_dir.parent.name
    program_root = Path(args.program_root) if args.program_root else professor_dir.parent.parent
    professor_name = professor
    updated_directions, reused, out_of_scope = [], [], []
    processed_keys = set()
    processed_any = False
    analysis_papers = {}
    for direction in pack_directions:
        ckey = direction.get("collection_key")
        analysis_papers[ckey] = direction.get("supporting_papers", [])
        in_scope = True
        if collection_key and ckey != collection_key:
            in_scope = False
        if refresh_scope == "flagged" and direction.get("status") != "active":
            in_scope = False
        if refresh_scope == "selected" and ckey not in (selected_keys or set()):
            in_scope = False
        if not in_scope:
            old = old_directions.get(ckey)
            if old:
                out_of_scope.append(old)
                # A scoped refresh replaces only selected directions. Keep the
                # other accepted directions in the machine state and render.
                updated_directions.append(old)
            continue
        fp_match = old_fps.get(ckey) == direction.get("input_fingerprint")
        old_direction = old_directions.get(ckey)
        if fp_match and not profile_changed and old_direction and old_direction.get("candidates") is not None:
            reused.append(ckey)
            updated_directions.append(old_direction)
            continue
        result_path = results_dir / f"candidates-{ckey}.json"
        processed_any = True
        processed_keys.add(ckey)
        data, rerror = read_json_file(result_path)
        if rerror:
            fail("result_missing", f"{result_path}: {rerror}")
        checked = validate_candidate_result(direction, data, result_path)
        checked["name_ja"] = direction.get("name_ja")
        checked["name_zh"] = direction.get("name_zh")
        checked["credibility"] = direction.get("credibility")
        checked["red_lines"] = direction.get("red_lines") or []
        checked["status"] = direction.get("status")
        checked["user_note_present"] = bool(direction.get("user_note"))
        updated_directions.append(checked)
    if not updated_directions and not reused:
        fail("validation_failed", "no in-scope directions to write")
    for entry in updated_directions:
        papers = {p["item_key"]: p for p in analysis_papers.get(entry.get("collection_key"), [])}
        for candidate in entry.get("candidates", []):
            for paper in candidate.get("papers", []):
                source = papers.get(paper["item_key"])
                if source and source.get("analysis_file"):
                    paper["_analysis_file"] = source["analysis_file"]
    md_entries = []
    for entry in updated_directions:
        clone = dict(entry)
        clone["_pack_papers"] = []
        for p in analysis_papers.get(entry.get("collection_key"), []):
            item = dict(p)
            if item.get("analysis_file"):
                item["_analysis_rel"] = rel_path(Path(item["analysis_file"]), professor_dir)
            clone["_pack_papers"].append(item)
        md_entries.append(clone)
    input_fps = {}
    for direction in pack_directions:
        input_fps[direction.get("collection_key")] = direction.get("input_fingerprint")
    state_fingerprint = sha256_obj({"professor": professor, "directions": input_fps,
                                    "profile": current_profile_fp})
    md_path = professor_dir / CANDIDATES_MD
    old_render = ((old_state or {}).get("cache") or {}).get("render", {})
    body = render_candidates_md(professor, category, md_entries,
                                current_profile_fp, state_fingerprint, professor_dir)
    projections = load_projections(program_root)
    overview_entries = []
    for d in updated_directions:
        overview_entries.append({
            "professor": professor, "name_ja": d.get("name_ja"),
            "candidates": d.get("candidates") or [],
            "priority": d.get("priority"),
            "_candidates_md_rel": rel_path(md_path, program_root / "教授研究")})
    overview_body = render_candidates_overview(overview_entries, program_root)
    overview_path = program_root / "教授研究" / CANDIDATES_OVERVIEW
    md_conflict = managed_conflict(
        md_path, body, old_render.get(CANDIDATES_MD, {}).get("sha256"), decision)
    if md_conflict:
        soft_exit("needs_decision", md_conflict["reason_code"], target=md_conflict.get("target"),
                  options=["overwrite", "keep_manual", "promote"])
    overview_conflict = projection_conflict(overview_path, overview_body, projections,
                                            CANDIDATES_OVERVIEW)
    if overview_conflict:
        soft_exit("needs_decision", overview_conflict["reason_code"],
                  target=overview_conflict.get("target"))
    md_result = managed_write(md_path, body, state_fingerprint,
                              old_render.get(CANDIDATES_MD, {}).get("sha256"), decision)
    if md_result.get("needs_decision"):
        soft_exit("needs_decision", md_result["reason_code"], target=md_result.get("target"),
                  options=["overwrite", "keep_manual", "promote"])
    overview_result = projection_write(overview_path, overview_body, projections,
                                       CANDIDATES_OVERVIEW)
    if overview_result.get("needs_decision"):
        soft_exit("needs_decision", overview_result["reason_code"], target=overview_result.get("target"))
    projections.setdefault("render", {})[CANDIDATES_OVERVIEW] = {
        "sha256": overview_result.get("sha256")}
    save_projections(program_root, projections)
    new_state = {
        "schema": SCHEMA, "managed_by": MANAGED_BY, "generated_at": now_utc(),
        "professor": professor,
        "profile_fingerprint": current_profile_fp,
        "profile_path": args.profile,
        "input_fingerprints": input_fps,
        "directions": updated_directions,
        "cache": {"render": {CANDIDATES_MD: {"sha256": md_result.get("sha256")}}},
    }
    if old_state and old_state.get("validator"):
        old_validator = old_state["validator"]
        old_results = old_validator.get("results") if isinstance(old_validator, dict) else None
        if isinstance(old_results, dict):
            retained = {key: value for key, value in old_results.items()
                        if key not in processed_keys}
            # A processed direction has a new rendered body, so its old
            # validator result is not carried forward; untouched directions are.
            if retained:
                new_state["validator"] = {
                    "results": retained,
                    "updated_at": old_validator.get("updated_at") if isinstance(old_validator, dict) else None}
    atomic_json(professor_dir / CANDIDATE_STATE, new_state)
    emit({
        "status": "ok", "professor": professor,
        "state_path": str(professor_dir / CANDIDATE_STATE),
        "candidates_md": str(md_path),
        "overview_md": str(program_root / "教授研究" / CANDIDATES_OVERVIEW),
        "directions": [{"collection_key": d.get("collection_key"),
                        "mode": d.get("mode"),
                        "candidates": len(d.get("candidates") or [])}
                       for d in updated_directions],
        "reused": reused, "md_sha256": md_result.get("sha256"),
    })


def compile_email_entry(pack: dict, state_direction: dict, pack_direction: dict,
                        idea: dict, note: str, program_root: Path,
                        profile_fp: str | None, papers_override: list[str] | None = None) -> dict:
    gap_records = {}
    for gap in pack_direction.get("gap_shortlist", []) + pack_direction.get("gaps_excluded", []):
        gap_records[(gap["item_key"], gap["gap_id"])] = gap
    blacklist = {(b["item_key"], b["gap_id"]): b
                 for b in pack_direction.get("completed_gap_blacklist", [])}
    paper_meta = {p["item_key"]: p for p in pack_direction.get("supporting_papers", [])}
    for gap in pack_direction.get("gap_shortlist", []) + pack_direction.get("gaps_excluded", []):
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
        papers_out.append({"item_key": meta["item_key"], "title": meta.get("title"),
                           "year": meta.get("year"), "authorship": meta.get("authorship"),
                           "fit_note": paper.get("fit_note") or ""})
    gaps_out = []
    for pair in idea.get("gap_ids") or []:
        key = (pair.get("item_key"), pair.get("gap_id"))
        gap = gap_records.get(key)
        if gap:
            status = gap.get("status")
            email_use = ("remaining_only" if status == "partial" else
                         "anchor_with_caveat" if status == "unknown" else "anchor")
            gaps_out.append({
                "item_key": gap["item_key"], "gap_id": gap["gap_id"],
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
    red_lines = list(pack_direction.get("red_lines") or [])
    candidate_red = idea.get("red_lines") or []
    for text in candidate_red:
        red_lines.append({"scope": "candidate", "text": text,
                          "banned_phrases": idea.get("banned_phrases") or []})
    narrative = pack_direction.get("narrative") or {}
    positioning = [block.get("text", "") for block in narrative.get("positioning", [])]
    allowed = {"user_note", f"idea:{idea.get('id')}", "profile.interest", "template"}
    for paper in papers_out:
        allowed.add(f"paper:{paper['item_key']}")
    for gap in gaps_out:
        allowed.add(f"gap:{gap['gap_id']}")
        allowed.add(f"later:{gap['item_key']}")
    idea_block = {"id": idea.get("id"), "title": idea.get("title"),
                  "idea_zh": idea.get("idea_zh") or ""}
    email_id = f"{pack.get('professor')}::{pack_direction.get('collection_key')}::{idea.get('id')}"
    anchorable_gaps = [g for g in gaps_out if g["email_use"] in ("anchor", "remaining_only", "anchor_with_caveat")]
    entry = {
        "email_id": email_id,
        "professor": pack.get("professor"),
        "professor_dir": pack.get("professor_dir"),
        "name_ja": pack_direction.get("name_ja"), "name_zh": pack_direction.get("name_zh"),
        "collection_key": pack_direction.get("collection_key"),
        "idea": idea_block,
        "user_note": pack_direction.get("user_note") or "",
        "papers": papers_out,
        "gaps": gaps_out,
        "anchorable_gaps": [g["gap_id"] for g in anchorable_gaps],
        "red_lines": red_lines,
        "soft_materials": {"credibility": pack_direction.get("credibility"),
                           "positioning": positioning},
        "profile": {"fingerprint": profile_fp, "fields": idea.get("_profile_fields") or {}},
        "allowed_sources": sorted(allowed),
        "fingerprints": {"input": pack_direction.get("input_fingerprint"),
                         "profile": profile_fp,
                         "candidate_state": idea.get("_state_fingerprint")},
        "user_supplement": note or "",
    }
    entry["source_hash"] = sha256_obj({k: entry[k] for k in (
        "email_id", "idea", "papers", "gaps", "red_lines", "allowed_sources")})
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


def validate_stage4_selections(selects: Any, states: dict, packs: dict) -> None:
    """Validate the complete selection batch before any formal file is written."""
    if not isinstance(selects, list) or not selects:
        fail("invalid_params", "selection input has no selections")
    seen_directions = set()
    seen_email_ids = set()
    for index, select in enumerate(selects):
        if not isinstance(select, dict):
            fail("invalid_selection", f"selection[{index}] must be an object")
        professor = select.get("professor")
        ckey = select.get("collection_key")
        professor_dir = Path(select.get("professor_dir") or "")
        if not isinstance(professor, str) or not professor.strip() or not professor_dir.is_dir() or not ckey:
            fail("invalid_selection", f"selection[{index}] is missing professor, professor_dir, or collection_key")
        direction_key = (professor, ckey)
        if direction_key in seen_directions:
            fail("duplicate_selection", f"duplicate professor+direction selection: {professor}::{ckey}")
        seen_directions.add(direction_key)
        state = states.get(str(professor_dir))
        pack = packs.get(str(professor_dir))
        state_direction = next((d for d in (state or {}).get("directions", [])
                                if d.get("collection_key") == ckey), None)
        pack_direction = next((d for d in (pack or {}).get("directions", [])
                               if d.get("collection_key") == ckey), None)
        if not state_direction or not pack_direction:
            continue
        candidates = {idea.get("id"): idea for idea in state_direction.get("candidates", [])}
        ideas = select.get("ideas")
        if not isinstance(ideas, list):
            fail("invalid_selection", f"{professor}::{ckey}: ideas must be a list")
        seen_ideas = set()
        for idea_index, idea_input in enumerate(ideas):
            if not isinstance(idea_input, dict):
                fail("invalid_selection", f"{professor}::{ckey}: ideas[{idea_index}] must be an object")
            idea_id = idea_input.get("id")
            if idea_id in seen_ideas:
                fail("duplicate_idea_id", f"duplicate idea id in {professor}::{ckey}: {idea_id}")
            seen_ideas.add(idea_id)
            idea = candidates.get(idea_id)
            if idea is None:
                continue
            override = validate_papers_override(
                idea, idea_input.get("papers_override"),
                f"{professor}::{ckey}::{idea_id}")
            email_id = f"{professor}::{ckey}::{idea_id}"
            if email_id in seen_email_ids:
                fail("duplicate_email_id", f"duplicate email id: {email_id}")
            seen_email_ids.add(email_id)


def cmd_stage4_finalize(args) -> None:
    program_root = Path(args.program_root)
    selection_input, error = read_json_file(Path(args.selection_input))
    if error or not isinstance(selection_input, dict):
        fail("invalid_params", f"selection input unreadable: {args.selection_input}")
    current_profile_fp = profile_fingerprint(args.profile)
    selects = selection_input.get("selections") or []
    if not selects:
        fail("invalid_params", "selection input has no selections")
    selection_path = program_root / "教授研究" / SELECTION_FILE
    old_selection, old_error = read_json_file(selection_path)
    if old_error is not None and old_error != "not_found":
        fail("invalid_selection", f"existing selection unreadable: {selection_path}: {old_error}")
    if old_selection is not None and not isinstance(old_selection, dict):
        fail("invalid_selection", f"existing selection must be an object: {selection_path}")
    old_selections = (old_selection or {}).get("selections", [])
    if not isinstance(old_selections, list):
        fail("invalid_selection", f"existing selection.selections must be a list: {selection_path}")
    current_keys = {(s.get("professor"), s.get("collection_key"))
                    for s in selects if isinstance(s, dict)}
    preserved = [s for s in old_selections
                 if isinstance(s, dict) and (s.get("professor"), s.get("collection_key")) not in current_keys]
    all_selects = preserved + selects
    written_selections = []
    email_entries = []
    skipped = []
    pack_cache, state_cache = {}, {}
    for select in all_selects:
        professor_dir = Path(select.get("professor_dir") or "") if isinstance(select, dict) else Path("")
        if professor_dir.is_dir():
            state, serr = read_json_file(professor_dir / CANDIDATE_STATE)
            pack, perr = read_json_file(professor_dir / INPUT_PACK)
            if serr is None and isinstance(state, dict):
                state_cache[str(professor_dir)] = state
            if perr is None and isinstance(pack, dict):
                pack_cache[str(professor_dir)] = pack
    validate_stage4_selections(all_selects, state_cache, pack_cache)
    for select in all_selects:
        professor = select.get("professor")
        professor_dir = Path(select.get("professor_dir") or "")
        ckey = select.get("collection_key")
        if not professor_dir.is_dir() or not ckey:
            skipped.append({"professor": professor, "reason": "invalid_selection_input"})
            continue
        state, serr = read_json_file(professor_dir / CANDIDATE_STATE)
        if serr:
            skipped.append({"professor": professor, "collection_key": ckey,
                            "reason": "needs_stage3", "detail": "缺 套磁候选状态.json"})
            continue
        pack, perr = read_json_file(professor_dir / INPUT_PACK)
        if perr:
            skipped.append({"professor": professor, "collection_key": ckey,
                            "reason": "needs_refresh", "detail": "missing_input_pack"})
            continue
        pack_direction = next((d for d in pack.get("directions", [])
                               if d.get("collection_key") == ckey), None)
        state_direction = next((d for d in state.get("directions", [])
                                if d.get("collection_key") == ckey), None)
        if not pack_direction or not state_direction:
            skipped.append({"professor": professor, "collection_key": ckey,
                            "reason": "needs_refresh", "detail": "direction not in state/pack"})
            continue
        if state.get("input_fingerprints", {}).get(ckey) != pack_direction.get("input_fingerprint"):
            soft_exit("needs_refresh", "source_fingerprint_changed",
                      professor=professor, collection_key=ckey,
                      message="输入包已变化：先重跑阶段 3 刷新候选，再重新选择。未写入任何选择/邮件包。")
        if state.get("profile_fingerprint") != current_profile_fp:
            soft_exit("needs_refresh", "profile_changed",
                      professor=professor, collection_key=ckey,
                      message="profile 已变化：重跑阶段 3 后再选择。未写入任何选择/邮件包。")
        selected_ideas = []
        for idea_input in select.get("ideas", []):
            idea_id = idea_input.get("id")
            idea = next((c for c in state_direction.get("candidates", [])
                         if c.get("id") == idea_id), None)
            if idea is None:
                skipped.append({"professor": professor, "collection_key": ckey,
                                "idea": idea_id, "reason": "unknown_idea_id"})
                continue
            idea_full = dict(idea)
            idea_full["red_lines"] = idea.get("red_lines") or []
            papers_override = validate_papers_override(
                idea, idea_input.get("papers_override"),
                f"{professor}::{ckey}::{idea_id}")
            entry = compile_email_entry(
                pack, state_direction, pack_direction, idea_full,
                idea_input.get("note") or "", program_root, current_profile_fp,
                papers_override)
            email_entries.append(entry)
            selected_ideas.append(idea_input)
        if not selected_ideas:
            continue
        select = dict(select, ideas=selected_ideas)
        written_selections.append({
            "professor": professor,
            "professor_dir": str(professor_dir),
            "zotero_collection": state_direction.get("zotero_collection") or select.get("zotero_collection"),
            "name_ja": pack_direction.get("name_ja"), "name_zh": pack_direction.get("name_zh"),
            "collection_key": ckey,
            "reason": select.get("reason"),
            "ideas": [{"id": i.get("id"), "note": i.get("note") or "",
                       "papers_override": i.get("papers_override") or None}
                      for i in select.get("ideas", [])]})
    if not written_selections:
        fail("validation_failed", "no valid selections")
    selection_doc = {
        "program_root": str(program_root), "generated_at": now_utc(),
        "managed_by": MANAGED_BY,
        "profile_fingerprint": current_profile_fp,
        "selections": written_selections}
    email_pack_path = program_root / "教授研究" / EMAIL_PACK
    email_pack = {
        "schema": SCHEMA, "managed_by": MANAGED_BY, "generated_at": now_utc(),
        "program_root": str(program_root),
        "profile_fingerprint": current_profile_fp,
        "emails": email_entries}
    atomic_json_many([(selection_path, selection_doc), (email_pack_path, email_pack)])
    emit({
        "status": "ok",
        "selection_file": str(selection_path),
        "email_pack": str(email_pack_path),
        "selected_directions": [f"{s['professor']} · {s.get('name_ja')}" for s in written_selections],
        "emails_compiled": len(email_entries),
        "skipped": skipped,
    })


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


def verify_state(professor_dir: Path, sources: dict) -> dict:
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
    warnings = items.get("warnings")
    if not isinstance(warnings, list):
        return {"ok": False, "reason": "invalid_cache", "path": str(path), "data": data}
    if items["email"].get("verdict") == "confirmed" and not str(items["email"].get("value") or "").strip():
        return {"ok": False, "reason": "email_value_missing", "path": str(path), "data": data}
    fps = data.get("source_fingerprints") or {}
    info_path = sources.get("info_path")
    boshu_path = sources.get("boshu_path")
    if not info_path or not boshu_path:
        return {"ok": False, "reason": "missing_source", "path": str(path), "data": data}
    def mtime(p):
        try:
            return f"{p}:{int(Path(p).stat().st_mtime)}"
        except OSError:
            return f"{p}:missing"
    if fps.get("info_json") != mtime(info_path):
        return {"ok": False, "reason": "stale_fingerprint", "path": str(path), "data": data}
    if fps.get("boshu_analysis") != mtime(boshu_path):
        return {"ok": False, "reason": "stale_fingerprint", "path": str(path), "data": data}
    verified_at = data.get("verified_at") or ""
    try:
        if not isinstance(verified_at, str):
            raise ValueError("verified_at must be a string")
        then = datetime.strptime(verified_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - then > timedelta(days=VERIFY_TTL_DAYS):
            return {"ok": False, "reason": "expired", "path": str(path), "data": data}
    except ValueError:
        return {"ok": False, "reason": "bad_timestamp", "path": str(path), "data": data}
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


def stage5_mode(args) -> str:
    mode = getattr(args, "mode", None) or "first"
    if mode not in ("first", "both", "followup"):
        fail("invalid_params", f"invalid stage-5 mode: {mode}")
    return mode


def cmd_stage5_plan(args) -> None:
    program_root = Path(args.program_root)
    mode = stage5_mode(args)
    pack_path = Path(args.email_pack) if args.email_pack else program_root / "教授研究" / EMAIL_PACK
    pack, error = read_json_file(pack_path)
    if error:
        soft_exit("needs_refresh", "missing_email_pack", email_pack=str(pack_path),
                  message="缺 邮件输入.json：先跑阶段 4（professor-contact-selection）编译。")
    all_emails = pack.get("emails") or []
    emails = all_emails
    for email in emails:
        professor_dir = Path(email.get("professor_dir") or program_root)
        require_professor_dir_under_program(professor_dir, program_root)
    if args.email_id:
        emails = [e for e in emails if e.get("email_id") == args.email_id]
        if not emails:
            fail("invalid_params", f"email_id not found: {args.email_id}")
    sources = load_header_sources(program_root)
    verify_checks = {}
    for email in emails:
        professor_dir = Path(email.get("professor_dir") or program_root)
        key = email.get("professor")
        if key not in verify_checks:
            verify_checks[key] = verify_state(professor_dir, sources)
    needs_recheck = [p for p, v in verify_checks.items() if not v["ok"]]
    template_path = None
    profile_path = args.profile
    if getattr(args, "template", None):
        template_path = args.template
    else:
        for candidate in [program_root.parent / "套磁邮件" / "套磁模板.md",
                          program_root / "套磁邮件" / "套磁模板.md"]:
            if candidate.is_file():
                template_path = str(candidate)
                break
    if not template_path:
        fail("template_required", "stage5 requires --template with the user's email template")
    if not Path(template_path).is_file():
        fail("template_error", f"template not found: {template_path}")
    template_text = Path(template_path).read_text(encoding="utf-8")
    if not args.result:
        jobs = []
        for email in emails:
            jobs.append({
                "job_id": f"email:{email['email_id']}", "kind": "email",
                "result_file": f"email-{sha256_text(email['email_id'])[:12]}.json",
                "result_schema": {
                    "schema": 1, "kind": "email", "email_id": email["email_id"],
                    "interest_sentences_ja": ["①自定位", "②点名+桥接", "③宽泛例子", "④软收束"],
                    "future_aspiration_ja": "…",
                    "learning_candidates": ["候补1", "候补2"],
                    "source_map": [{"output": "①", "source_ids": ["profile.interest"]},
                                   {"output": "②", "source_ids": ["paper:<item_key>"]},
                                   {"output": "③", "source_ids": ["gap:<gap_id>"]},
                                   {"output": "④", "source_ids": ["template"]},
                                   {"output": "future", "source_ids": [f"idea:{email['idea']['id']}"]}]},
                "model_input": {
                    "idea": email.get("idea"),
                    "user_note": truncate(email.get("user_note"), 800),
                    "papers": email.get("papers"),
                    "gaps": [gap_job_block(g) for g in email.get("gaps", [])],
                    "red_lines": email.get("red_lines"),
                    "soft_materials": {"positioning": email.get("soft_materials", {}).get("positioning", [])},
                    "profile_text": load_profile_text(profile_path, 1200),
                    "user_supplement": email.get("user_supplement") or "",
                    "allowed_sources": email.get("allowed_sources"),
                    "rules": {
                        "interest": "4 句、只写软层、总长 ≤180 日文字；①自定位（角色+信念，禁恭维）②点名+桥接（真实标题、共同主题逐篇成立）③宽泛例子（仅可用 gaps 里 status∈{open,partial,unknown} 的精确 gap；done_by_self 禁锚；partial 只谈 remaining_gap；引用教授原话式，不找碴）④固定句「このような<领域名词>は、まだ数多く存在すると感じております。」",
                        "exclusions": "禁方法名/模型名/算法名（标题内除外）、指标数字、数据集名、组件名、公式、限定语链、年份叙事",
                        "future_aspiration": "宽泛方向表述+背景技能，禁具体技术栈，不用其他方向原句",
                        "learning": "2-3 个名词短语候选，贴近 profile 真实知识储备，交用户挑选",
                        "source_map": "每句必须给来源；③只能用 gap:<id>；④只能 template；所有 source_ids ⊆ allowed_sources"}}})
        emit({
            "status": "ok", "email_pack": str(pack_path),
            "emails": [e.get("email_id") for e in emails],
            "verify": {p: ("ok" if v["ok"] else f"needs_recheck:{v['reason']}")
                       for p, v in verify_checks.items()},
            "needs_recheck_professors": needs_recheck,
            "template": template_path or "embedded",
            "output_mode": mode,
            "followup_template": (find_followup_template_path(
                program_root, getattr(args, "followup_template", None)) or "embedded"),
            "jobs": jobs,
        })
        return
    result_path = Path(args.result)
    results, rerror = read_json_file(result_path)
    if rerror:
        fail("result_missing", f"{result_path}: {rerror}")
    by_id = load_id_map(result_path, {e.get("email_id") for e in emails}, "email result",
                        exact=not bool(args.email_id))
    choices_path = getattr(args, "choices", None)
    choices_by_id = (load_id_map(Path(choices_path), {e.get("email_id") for e in emails}, "choices",
                                 exact=not bool(args.email_id))
                     if choices_path else {})
    drafts = []
    for email in emails:
        raw = by_id.get(email.get("email_id"))
        if raw is None:
            fail("result_missing", f"no raw result for {email.get('email_id')}")
        problems = validate_email_raw(email, raw)
        hard = [x for x in problems if not x.startswith("WARNING")]
        if hard:
            fail("invalid_result_json", f"{email.get('email_id')}: {'; '.join(hard)}")
        warnings = [x for x in problems if x.startswith("WARNING")]
        choices = choices_by_id.get(email.get("email_id"))
        require_user_choices(email.get("email_id"), choices)
        if mode in ("both", "followup"):
            require_followup_choices(email.get("email_id"), choices)
        if mode in ("first", "both"):
            draft, protected, banned = assemble_draft(
                email, raw, choices, sources, template_text)
            drafts.append({"output_id": stage5_output_id(email.get("email_id"), "initial"),
                           "email_id": email.get("email_id"), "kind": "initial",
                           "draft": draft, "protected": protected, "banned": banned,
                           "warnings": warnings, "result_file": str(result_path)})
        if mode in ("followup", "both"):
            followup_template_path = find_followup_template_path(
                program_root, getattr(args, "followup_template", None))
            if not followup_template_path:
                fail("followup_template_required", "follow-up mode requires --followup-template")
            if not Path(followup_template_path).is_file():
                fail("template_error", f"follow-up template not found: {followup_template_path}")
            followup_template = Path(followup_template_path).read_text(encoding="utf-8")
            followup_draft, followup_protected, followup_banned = assemble_followup_draft(
                email, choices, sources, followup_template,
                verify_checks.get(email.get("professor"), {}).get("data"))
            drafts.append({"output_id": stage5_output_id(email.get("email_id"), "followup"),
                           "email_id": email.get("email_id"), "kind": "followup",
                           "draft": followup_draft, "protected": followup_protected,
                           "banned": followup_banned, "warnings": warnings,
                           "result_file": str(result_path)})
    emit({"status": "ok", "drafts": drafts, "output_mode": mode})


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


def assemble_draft(email: dict, raw: dict, choices: dict,
                   sources: dict, template_text: str) -> tuple[str, list, list]:
    values = header_values(sources, email)
    values["出身校"] = choices.get("alma_mater") or "総合大学出身"
    values["氏名"] = choices.get("signature_name") or ""
    values["志望"] = ("先生の研究室を第一志望として出願させていただきたく存じます"
                      if choices.get("first_choice") else
                      "先生の研究室を志望として出願させていただきたく存じます")
    values["学習中"] = choices.get("learning") or ""
    values["兴趣段"] = "\n".join(raw.get("interest_sentences_ja") or [])
    values["未来志向"] = raw.get("future_aspiration_ja") or ""
    subject = choices.get("subject") or subject_line(values)
    values["subject"] = subject
    body = template_text
    for key, value in values.items():
        body = body.replace("{{" + key + "}}", value or "")
    leftover = re.findall(r"\{\{[^}]+\}\}", body)
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
    values["出身校"] = choices.get("alma_mater") or "総合大学出身"
    values["氏名"] = choices.get("signature_name") or ""
    values["初回送信日"] = choices.get("initial_sent_date") or ""
    values["研究主题"] = (email.get("name_ja") or
                           (email.get("idea") or {}).get("title") or "関連分野")
    verify_items = (verify or {}).get("items") or {}
    values["メールアドレス"] = (choices.get("email_address") or
                              (verify_items.get("email") or {}).get("value") or "")
    subject = choices.get("followup_subject") or f"Re: {choices.get('subject') or subject_line(values)}"
    values["subject"] = subject
    body = template_text
    for key, value in values.items():
        body = body.replace("{{" + key + "}}", value or "")
    leftover = re.findall(r"\{\{[^}]+\}\}", body)
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


def cmd_stage5_finalize(args) -> None:
    program_root = Path(args.program_root)
    mode = stage5_mode(args)
    pack_path = Path(args.email_pack) if args.email_pack else program_root / "教授研究" / EMAIL_PACK
    pack, error = read_json_file(pack_path)
    if error:
        soft_exit("needs_refresh", "missing_email_pack", email_pack=str(pack_path))
    all_emails = pack.get("emails") or []
    all_ids = [email.get("email_id") for email in all_emails]
    if len(set(all_ids)) != len(all_ids) or any(not isinstance(email_id, str) for email_id in all_ids):
        fail("invalid_email_pack", "email pack contains duplicate or missing email_id")
    emails = all_emails
    for email in emails:
        professor_dir = Path(email.get("professor_dir") or program_root)
        require_professor_dir_under_program(professor_dir, program_root)
    if args.email_id:
        emails = [e for e in emails if e.get("email_id") == args.email_id]
        if not emails:
            fail("invalid_params", f"email_id not found: {args.email_id}")
    sources = load_header_sources(program_root)
    result_path = Path(args.result)
    raw_by_id = load_id_map(result_path, {e.get("email_id") for e in emails}, "email result",
                            exact=not bool(args.email_id))
    choices_path = getattr(args, "choices", None)
    choices_by_id = (load_id_map(Path(choices_path), {e.get("email_id") for e in emails}, "choices",
                                 exact=not bool(args.email_id))
                     if choices_path else {})
    humanized_by_id = humanized_paths(args, emails, exact=not bool(args.email_id))
    decision = None
    if getattr(args, "decision_file", None):
        decision_data, decision_error = read_json_file(Path(args.decision_file))
        if decision_error is None and isinstance(decision_data, dict):
            decision = decision_data.get("decision")
    template_path = getattr(args, "template", None)
    if not template_path:
        for candidate in [program_root.parent / "套磁邮件" / "套磁模板.md",
                          program_root / "套磁邮件" / "套磁模板.md"]:
            if candidate.is_file():
                template_path = str(candidate)
                break
    if not template_path:
        fail("template_required", "stage5 requires --template with the user's email template")
    if not Path(template_path).is_file():
        fail("template_error", f"template not found: {template_path}")
    template_text = Path(template_path).read_text(encoding="utf-8")
    followup_template_path = find_followup_template_path(
        program_root, getattr(args, "followup_template", None))
    if mode in ("both", "followup") and not followup_template_path:
        fail("followup_template_required", "follow-up mode requires --followup-template")
    if followup_template_path and not Path(followup_template_path).is_file():
        fail("template_error", f"follow-up template not found: {followup_template_path}")
    followup_template = (Path(followup_template_path).read_text(encoding="utf-8")
                         if followup_template_path else None)
    state_updates = {}
    prepared = []

    # Validate every email and prepare every file before committing any output.
    for email in emails:
        email_id = email.get("email_id")
        raw = raw_by_id.get(email_id)
        problems = validate_email_raw(email, raw)
        hard = [p for p in problems if not p.startswith("WARNING")]
        if hard:
            fail("invalid_result_json", f"{email_id}: {'; '.join(hard)}")
        choices = choices_by_id.get(email_id)
        require_user_choices(email_id, choices)
        if mode in ("both", "followup"):
            require_followup_choices(email_id, choices)
        professor_dir = Path(email.get("professor_dir") or program_root)
        verify_check = verify_state(professor_dir, sources)
        if not verify_check["ok"]:
            soft_exit("needs_refresh", f"verify_{verify_check['reason']}",
                      professor=email.get("professor"),
                      message=f"送信前核验缓存不可用（{verify_check['reason']}）：先完成 Step 2.5 核验。未写盘。")
        verify = verify_check["data"]
        warnings = (verify.get("items") or {}).get("warnings") or []
        roster_verdict = ((verify.get("items") or {}).get("roster") or {}).get("verdict")
        email_verdict = ((verify.get("items") or {}).get("email") or {}).get("verdict")
        banner_needed = bool(warnings) or roster_verdict == "not_found" or email_verdict == "unverified"
        values = header_values(sources, email)
        checklist_header = (f"{values['大学']}／{values['研究科']}／"
                            f"{values['先生名']}先生：")
        variants = []
        if mode in ("first", "both"):
            draft, protected, banned = assemble_draft(email, raw, choices, sources, template_text)
            variants.append(("initial", draft, protected, banned, "套磁邮件",
                             Path(template_path).name if template_path else "内嵌",
                             render_source_table(email, raw)))
        if mode in ("followup", "both"):
            draft, protected, banned = assemble_followup_draft(
                email, choices, sources, followup_template, verify)
            variants.append(("followup", draft, protected, banned, "套磁跟进邮件",
                             Path(followup_template_path).name if followup_template_path else "内嵌",
                             render_followup_source_table(email)))

        input_fp = email.get("source_hash") or sha256_obj(email)
        if str(professor_dir) not in state_updates:
            email_state, serr = read_json_file(professor_dir / EMAIL_STATE)
            state_updates[str(professor_dir)] = (
                json.loads(json.dumps(email_state, ensure_ascii=False))
                if serr is None and isinstance(email_state, dict)
                else {"schema": SCHEMA, "managed_by": MANAGED_BY, "emails": {}})
        email_state = state_updates[str(professor_dir)]
        root_entry = email_state.setdefault("emails", {}).setdefault(email_id, {})
        for kind, draft, protected, banned, heading, template_name, source_rows in variants:
            output_id = stage5_output_id(email_id, kind)
            humanized = humanized_by_id[output_id].read_text(encoding="utf-8")
            missing = [p for p in protected if p and p not in humanized]
            if missing:
                fail("humanizer_violation",
                     f"{output_id}: humanized text lost protected strings: {missing}")
            violated = [b for b in banned if b and b in humanized]
            if violated:
                fail("humanizer_violation", f"{output_id}: banned phrases appeared: {violated}")
            if "{{" in humanized:
                fail("humanizer_violation", f"{output_id}: residual {{}} placeholders")
            subject_match = re.match(r"Subject: (.*)", humanized)
            subject = (choices.get("subject") if kind == "initial" else choices.get("followup_subject"))
            subject = subject or (subject_match.group(1).strip() if subject_match else
                                  (subject_line(values) if kind == "initial" else
                                   f"Re: {choices.get('subject') or subject_line(values)}"))
            body_text = re.sub(r"^Subject: .*\n+", "", humanized, count=1)
            lines = [
                f"# {heading} — {email.get('professor')}（{email.get('name_ja')}）",
                "",
                f"> {now_utc()} ｜ 类型：{'首封' if kind == 'initial' else '无回复跟进'} ｜ profile：{'有' if pack.get('profile_fingerprint') else '无'} ｜ 模板：{template_name} ｜ 方向：{email.get('name_zh') or email.get('name_ja')} ｜ 过稿: humanizer-ja(business)",
                "",
            ]
            if kind == "followup":
                lines.append(f"> 跟进依据：首封邮件 email_id `{email_id}`；初次发送日：{choices.get('initial_sent_date')}。建议在首封邮件发送数日后使用。")
                lines.append("")
            if banner_needed:
                lines.append("> ⚠️ **送信前注意**：" + "；".join(
                    ([f"邮箱 {email_verdict}"] if email_verdict == "unverified" else []) +
                    ([f"教员在册 {roster_verdict}"] if roster_verdict == "not_found" else []) +
                    [str(w) for w in warnings]) + "。请人工确认后再发。")
                lines.append("")
            lines.append(f"## 送信前核对（发信前最后过目；数据源 _contact_verify.json @ {verify.get('verified_at')}）")
            lines.append("")
            lines.extend(render_checklist_table(verify, checklist_header))
            lines.append("")
            lines.append("## 邮件正文")
            lines.append("")
            lines.append(f"Subject: {subject}")
            lines.append("")
            lines.append(body_text.strip())
            lines.append("")
            lines.append("## 来源标注（仅 md 内审用，不进 txt）")
            lines.append("")
            lines.extend(source_rows)
            lines.append("")
            red_lines = email.get("red_lines") or []
            if red_lines:
                lines.append("## 生成时消费的红线（已遵守）")
                lines.append("")
                for red in red_lines:
                    lines.append(f"- 【{red.get('scope')}】{red.get('text')}")
                lines.append("")
            lines.extend(render_fact_check_card(email, pack_path, professor_dir))
            md_body = "\n".join(lines).rstrip() + "\n"
            txt_body = f"Subject: {subject}\n\n{body_text.strip()}\n"
            state_fingerprint = sha256_obj({"output_id": output_id, "input": input_fp})
            md_path, txt_path = stage5_output_paths(email, all_emails, professor_dir, kind)
            previous = root_entry if kind == "initial" else root_entry.get("followup", {})
            old_render = previous.get("render") or {}
            existing_md_sha = None
            if md_path.is_file():
                _, existing_body = split_frontmatter(md_path.read_text(encoding="utf-8"))
                existing_md_sha = sha256_text(existing_body)
            md_sha = sha256_text(md_body)
            if (existing_md_sha is not None and old_render.get("md", {}).get("sha256") and
                    existing_md_sha not in (md_sha, old_render["md"]["sha256"]) and
                    decision != "overwrite"):
                soft_exit("needs_decision", "manual_markdown_changed", target=str(md_path))
            existing_txt_sha = sha256_bytes(txt_path.read_bytes()) if txt_path.is_file() else None
            txt_sha = sha256_text(txt_body)
            if (existing_txt_sha is not None and old_render.get("txt", {}).get("sha256") and
                    existing_txt_sha not in (txt_sha, old_render["txt"]["sha256"]) and
                    decision != "overwrite"):
                soft_exit("needs_decision", "manual_markdown_changed", target=str(txt_path))
            prepared.append({"email": email, "email_id": email_id, "output_id": output_id,
                             "kind": kind, "professor_dir": professor_dir, "raw": raw,
                             "choices": choices, "md": md_path, "txt": txt_path,
                             "md_body": md_body, "txt_body": txt_body, "md_sha": md_sha,
                             "txt_sha": txt_sha, "state_fingerprint": state_fingerprint,
                             "input_fp": input_fp, "warnings": warnings,
                             "banner": banner_needed})
            update = {"generated_at": now_utc(), "input_fingerprint": input_fp,
                      "model_result": raw, "choices": choices,
                      "files": {"md": str(md_path), "txt": str(txt_path)},
                      "render": {"md": {"sha256": md_sha}, "txt": {"sha256": txt_sha}},
                      "validation": {"result": "pending", "rounds": 0}}
            if kind == "initial":
                root_entry.update(update)
            else:
                root_entry.setdefault("followup", {}).update(update)

    projections = load_projections(program_root)
    overview_rows = ["| 教授 | 方向（ja/zh） | 收件邮箱 | 核验 | 首封邮件 | 跟进邮件 | 首封纯文本 | 跟进纯文本 |",
                     "|---|---|---|---|---|---|---|---|"]
    overview_entries = []
    for email in all_emails:
        professor_dir = Path(email.get("professor_dir") or program_root)
        email_state = state_updates.get(str(professor_dir))
        if email_state is None:
            email_state, state_error = read_json_file(professor_dir / EMAIL_STATE)
            if state_error is not None:
                email_state = None
        state_entry = ((email_state or {}).get("emails") or {}).get(email.get("email_id")) \
            if email_state is not None else None
        files = (state_entry or {}).get("files") or {}
        followup_files = ((state_entry or {}).get("followup") or {}).get("files") or {}
        if files or followup_files:
            overview_entries.append({"email": email, "initial": files,
                                     "followup": followup_files})
    for entry in overview_entries:
        email = entry["email"]
        professor_dir = Path(email.get("professor_dir") or program_root)
        verify_check = verify_state(professor_dir, sources)
        items = ((verify_check.get("data") or {}).get("items") or {})
        email_value = (items.get("email") or {}).get("value") or "?"
        warnings = items.get("warnings") or []
        bad = []
        if (items.get("roster") or {}).get("verdict") == "not_found":
            bad.append("在册 not_found")
        if (items.get("email") or {}).get("verdict") == "unverified":
            bad.append("邮箱 unverified")
        bad.extend(str(w) for w in warnings)
        verify_label = "✅ 全 confirmed" if not bad else "⚠ " + "；".join(bad)
        def link(path: str | None, label: str) -> str:
            return f"[{label}]({rel_path(Path(path), program_root / '教授研究')})" if path else "—"
        initial = entry["initial"]
        followup = entry["followup"]
        overview_rows.append(
            f"| {email.get('professor')} | {email.get('name_ja')}/{email.get('name_zh')} | "
            f"{email_value} | {verify_label} | {link(initial.get('md'), '.md')} | "
            f"{link(followup.get('md'), '跟进 .md')} | {link(initial.get('txt'), '首封 .txt')} | "
            f"{link(followup.get('txt'), '跟进 .txt')} |")
    overview_body = ("# 套磁邮件总览\n\n"
                     f"> {now_utc()} ｜ 由 contact_state 渲染\n\n" +
                     "\n".join(overview_rows) + "\n")
    overview_path = program_root / "教授研究" / EMAIL_OVERVIEW
    overview_sha = sha256_text(overview_body)
    overview_conflict = projection_conflict(overview_path, overview_body, projections,
                                            EMAIL_OVERVIEW)
    if overview_conflict:
        soft_exit("needs_decision", overview_conflict["reason_code"],
                  target=overview_conflict.get("target"))

    # Commit only after every email and the aggregate projection passed validation.
    for item in prepared:
        atomic_write(item["md"], render_frontmatter(
            sha256_obj({"email_id": item["email_id"], "input": item["input_fp"]}), item["md_sha"]) + item["md_body"])
        atomic_write(item["txt"], item["txt_body"])
    for professor_dir, email_state in state_updates.items():
        atomic_json(Path(professor_dir) / EMAIL_STATE, email_state)
    overview_fingerprint = sha256_obj({"projection": EMAIL_OVERVIEW, "body": overview_sha})
    atomic_write(overview_path, render_frontmatter(overview_fingerprint, overview_sha) + overview_body)
    projections.setdefault("render", {})[EMAIL_OVERVIEW] = {"sha256": overview_sha}
    save_projections(program_root, projections)
    emit({"status": "ok", "emails": [
        {"email_id": item["email_id"], "output_id": item["output_id"], "kind": item["kind"],
         "md": str(item["md"]), "txt": str(item["txt"]),
         "warnings": len(item["warnings"]), "banner": item["banner"]}
        for item in prepared], "overview_md": str(overview_path)})


def cmd_stage5_record_validation(args) -> None:
    professor_dir = Path(args.professor_dir)
    state_path = professor_dir / EMAIL_STATE
    state, state_error = read_json_file(state_path)
    if state_error or not isinstance(state, dict):
        fail("missing_email_state", f"email state unreadable: {state_path}")
    validation_data, validation_error = read_json_file(Path(args.validation_file))
    if validation_error or not isinstance(validation_data, dict):
        fail("invalid_validation_json", f"validation file unreadable: {args.validation_file}")
    results = validation_data.get("results")
    if not isinstance(results, list) or not results:
        fail("invalid_validation_json", "validation results must be a non-empty list")
    emails = state.get("emails")
    if not isinstance(emails, dict):
        fail("invalid_email_state", "email state has no emails object")
    validated = {}
    seen = set()
    for result in results:
        if not isinstance(result, dict):
            fail("invalid_validation_json", "each validation result must be an object")
        email_id = result.get("email_id")
        output_id = result.get("output_id") or email_id
        kind = "followup" if isinstance(output_id, str) and output_id.endswith("::followup") else "initial"
        base_email_id = output_id[:-len("::followup")] if kind == "followup" else email_id
        validation_result = result.get("result")
        rounds = result.get("rounds", 0)
        issues = result.get("issues")
        if output_id in seen:
            fail("invalid_validation_json", f"duplicate validation result for {output_id}")
        seen.add(output_id)
        if base_email_id not in emails:
            fail("unknown_email_id", f"validation email_id not in state: {base_email_id}")
        if kind == "initial" and output_id != email_id:
            fail("invalid_validation_json", f"initial output_id mismatch for {email_id}")
        if validation_result not in ("pass", "fail_after_2_rounds", "skipped"):
            fail("invalid_validation_json", f"invalid validation result for {output_id}: {validation_result}")
        if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
            fail("invalid_validation_json", f"invalid validation rounds for {output_id}: {rounds}")
        if validation_result == "pass" and rounds not in (1, 2):
            fail("invalid_validation_json", f"pass validation needs 1-2 rounds for {output_id}")
        if validation_result == "fail_after_2_rounds" and rounds != 2:
            fail("invalid_validation_json", f"fail_after_2_rounds needs rounds=2 for {output_id}")
        if validation_result == "skipped" and rounds > 2:
            fail("invalid_validation_json", f"skipped validation needs rounds=0-2 for {output_id}")
        if not isinstance(issues, list):
            fail("invalid_validation_json", f"validation issues must be a list for {output_id}")
        validated[output_id] = {
            "email_id": base_email_id, "kind": kind,
            "result": validation_result, "rounds": rounds,
            "issues": issues, "validated_at": now_utc()}
    updated = []
    for output_id, validation in validated.items():
        target = emails[validation["email_id"]]
        if validation["kind"] == "followup":
            target.setdefault("followup", {})["validation"] = validation
        else:
            target["validation"] = validation
        updated.append(output_id)
    atomic_json(state_path, state)
    emit({"status": "ok", "state_path": str(state_path), "updated": updated})


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


def stage2_pack_matches_facts(ctx: Stage2Context) -> None:
    """Do not apply a validator rewrite to facts newer than the accepted pack."""
    if not ctx.pack:
        fail("missing_input_pack", f"input pack unreadable: {ctx.pack_path}")
    accepted = {d.get("collection_key"): d for d in ctx.pack.get("directions", [])}
    for plan in ctx.direction_plans:
        old = accepted.get(plan["ckey"])
        if not old or old.get("input_fingerprint") != plan["fingerprint"]:
            soft_exit("needs_refresh", "source_fingerprint_changed",
                      direction=plan["ckey"], pack_path=str(ctx.pack_path))


def stage2_validation_material(ctx: Stage2Context, plan: dict, direction: dict) -> dict:
    paper_keys = set(direction.get("named_keys") or [])
    paper_keys.update(direction_relevant_keys(direction))
    paper_keys.update(ctx.narrative_later_keys(plan))
    papers = []
    for key in sorted(paper_keys):
        paper = ctx.papers.get(key)
        if not paper:
            continue
        papers.append({"item_key": key, "title": paper.get("title"),
                       "year": paper.get("year"), "authorship": paper.get("authorship")})
    pack_gaps = {(gap.get("item_key"), gap.get("gap_id")): gap
                 for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", [])}
    gaps = []
    for gap in plan["ranked"]:
        accepted = pack_gaps.get((gap["item_key"], gap["gap_id"]), {})
        gaps.append({"gap_id": gap["gap_id"], "item_key": gap["item_key"],
                     "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                     "quote": truncate(gap.get("quote"), QUOTE_INPUT_CHARS),
                     "translation_zh": truncate(gap.get("translation_zh"), TRANSLATION_INPUT_CHARS),
                     "status": accepted.get("status"), "evidence": accepted.get("evidence")})
    return {"papers": papers, "gaps": gaps}


def stage2_refine_context(args):
    if args.facts:
        ctx = Stage2Context(Path(args.facts))
        stage2_pack_matches_facts(ctx)
        return ctx
    return Stage2PackRefineContext(Path(args.professor_dir))


def cmd_stage2_refine_plan(args) -> None:
    ctx = stage2_refine_context(args)
    allowed = {d.get("collection_key") for d in ctx.pack.get("directions", [])}
    validation = load_validator_results(Path(args.validation_file), allowed, "collection_key")
    failed = {key: value for key, value in validation.items()
              if value["result"] == "fail_after_2_rounds"}
    if args.collection_key:
        if args.collection_key not in allowed:
            fail("invalid_params", f"collection_key not found in input pack: {args.collection_key}")
        failed = {key: value for key, value in failed.items() if key == args.collection_key}

    old_directions = {d.get("collection_key"): d for d in ctx.pack.get("directions", [])}
    plans = {plan["ckey"]: plan for plan in ctx.direction_plans}
    jobs = []
    for ckey in sorted(failed):
        direction = old_directions.get(ckey)
        plan = plans.get(ckey)
        if not direction or not plan or not isinstance(direction.get("narrative"), dict):
            fail("invalid_result_json", f"input pack has no reusable narrative for {ckey}")
        jobs.append({
            "job_id": f"narrative-rewrite:{ctx.professor}:{ckey}",
            "kind": "narrative-rewrite",
            "collection_key": ckey,
            "result_file": f"narrative-rewrite-{filename_component(ckey)}.json",
            "result_schema": {"schema": 1, "kind": "narrative-rewrite",
                              "collection_key": ckey,
                              "positioning": [{"kind": "para|bullet", "text": "…",
                                                "refs": ["paper:ITEMKEY"],
                                                "concrete_object": "具体对象",
                                                "input_example": "具体输入",
                                                "output_example": "具体输出"}],
                              "gap_notes": [{"gap_id": "", "summary": "一句话",
                                              "explanation": "大白话"}]},
            "model_input": {
                "collection_key": ckey,
                "current_narrative": direction["narrative"],
                "issues": failed[ckey]["issues"],
                "allowed_material": stage2_validation_material(ctx, plan, direction),
                "rules": "返回完整的当前方向 narrative，未命中的 block 和 gap_notes 原样保留，只重写 validator 指出的文字。保留且只使用允许的 paper/later/gap 引用。不得修改 freshness 状态、用户笔记、论文事实或红线。每个 positioning block 必须有 concrete_object、input_example、output_example；text 中占位符集合必须与 refs 完全相等。用最日常中文解释术语，不能把 item_key 写进 text。"},
        })
    emit({"status": "ok", "professor": ctx.professor,
          "validation_file": str(Path(args.validation_file)),
          "directions": sorted(failed), "jobs": jobs,
          "write_needed": bool(jobs)})


def cmd_stage2_refine_finalize(args) -> None:
    ctx = stage2_refine_context(args)
    allowed = {d.get("collection_key") for d in ctx.pack.get("directions", [])}
    validation = load_validator_results(Path(args.validation_file), allowed, "collection_key")
    failed = {key for key, value in validation.items()
              if value["result"] == "fail_after_2_rounds"}
    if args.collection_key:
        if args.collection_key not in allowed:
            fail("invalid_params", f"collection_key not found in input pack: {args.collection_key}")
        failed &= {args.collection_key}
    if not failed:
        emit({"status": "ok", "rewritten": [], "write_needed": False,
              "reason_code": "no_failed_directions"})
        return

    results_dir = Path(args.results)
    rewrites = {}
    for ckey in sorted(failed):
        path = results_dir / f"narrative-rewrite-{filename_component(ckey)}.json"
        data, error = read_json_file(path)
        if error:
            fail("result_missing", f"{path}: {error}")
        if not isinstance(data, dict) or data.get("schema") != 1 or data.get("kind") != "narrative-rewrite":
            fail("invalid_result_json", f"{path}: schema/kind must be 1/narrative-rewrite")
        if data.get("collection_key") != ckey:
            fail("invalid_result_json", f"{path}: unexpected direction {data.get('collection_key')}")
        _, rewrites[ckey] = validate_narrative_entry(ctx, path, data, expected_ckey=ckey)

    pack_directions = []
    for direction in ctx.pack.get("directions", []):
        updated = dict(direction)
        if direction.get("collection_key") in rewrites:
            updated["narrative"] = rewrites[direction["collection_key"]]
        pack_directions.append(updated)
    state_fingerprint = sha256_obj({
        "professor": ctx.professor,
        "directions": {d["collection_key"]: d.get("input_fingerprint") for d in pack_directions}})
    body = render_analysis_md(ctx, pack_directions, state_fingerprint)
    old_render = ((ctx.pack or {}).get("cache") or {}).get("render", {})
    decision = None
    if getattr(args, "decision_file", None):
        decision_data, error = read_json_file(Path(args.decision_file))
        if error is None and isinstance(decision_data, dict):
            decision = decision_data.get("decision")
    md_path = ctx.professor_dir / ANALYSIS_MD
    conflict = managed_conflict(md_path, body,
                                old_render.get(ANALYSIS_MD, {}).get("sha256"), decision)
    if conflict:
        soft_exit("needs_decision", conflict["reason_code"], target=str(md_path),
                  options=["overwrite", "keep_manual", "promote"])
    md_result = managed_write(md_path, body, state_fingerprint,
                              old_render.get(ANALYSIS_MD, {}).get("sha256"), decision)
    if md_result.get("needs_decision"):
        soft_exit("needs_decision", md_result["reason_code"], target=md_result.get("target"))
    updated_pack = dict(ctx.pack)
    updated_pack["generated_at"] = now_utc()
    updated_pack["directions"] = pack_directions
    updated_pack["cache"] = {"render": {ANALYSIS_MD: {"sha256": md_result["sha256"]}}}
    # The previous validator result describes the old complete document.
    updated_pack.pop("validator", None)
    atomic_json(ctx.pack_path, updated_pack)
    emit({"status": "ok", "professor": ctx.professor,
          "rewritten": sorted(rewrites), "analysis_md": str(md_path),
          "md_sha256": md_result["sha256"], "validator_reset": True})


def cmd_stage2_record_validation(args) -> None:
    professor_dir = Path(args.professor_dir)
    path = professor_dir / INPUT_PACK
    pack, error = read_json_file(path)
    if error or not isinstance(pack, dict):
        fail("missing_input_pack", f"input pack unreadable: {path}")
    allowed = {d.get("collection_key") for d in pack.get("directions", [])}
    results = load_validator_results(Path(args.validation_file), allowed, "collection_key")
    updated = dict(pack)
    updated["validator"] = {"results": results, "updated_at": now_utc()}
    atomic_json(path, updated)
    emit({"status": "ok", "pack_path": str(path), "updated": sorted(results)})


def cmd_stage3_record_validation(args) -> None:
    professor_dir = Path(args.professor_dir)
    path = professor_dir / CANDIDATE_STATE
    state, error = read_json_file(path)
    if error or not isinstance(state, dict):
        fail("missing_candidate_state", f"candidate state unreadable: {path}")
    allowed = {d.get("collection_key") for d in state.get("directions", [])}
    results = load_validator_results(Path(args.validation_file), allowed, "collection_key")
    updated = dict(state)
    updated["validator"] = {"results": results, "updated_at": now_utc()}
    atomic_json(path, updated)
    emit({"status": "ok", "state_path": str(path), "updated": sorted(results)})


def read_legacy_index(index_path: Path) -> tuple[dict | None, str | None]:
    data, error = read_json_file(index_path)
    if error:
        return None, error
    if not isinstance(data, dict):
        return None, "not an object"
    return data, None


def migration_source_fingerprint(professor_dir: Path) -> str:
    paths = {
        professor_dir / "论文分析" / "_index.json",
        professor_dir / "papers.json",
        professor_dir / CANDIDATES_MD,
    }
    index, error = read_legacy_index(professor_dir / "论文分析" / "_index.json")
    if error is None and isinstance(index, dict):
        for paper in (index.get("papers") or {}).values():
            if not isinstance(paper, dict):
                continue
            for field in ("file", "future_work_sidecar"):
                value = paper.get(field)
                if value:
                    paths.add(Path(value))
    records = []
    for path in sorted(paths, key=lambda item: str(item)):
        try:
            records.append({"path": str(path), "sha256": sha256_bytes(path.read_bytes())})
        except (OSError, ValueError):
            records.append({"path": str(path), "sha256": None})
    return sha256_obj(records)


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


def migrate_entry_for_professor(professor_dir: Path, program_root: Path) -> dict | None:
    index_path = professor_dir / "论文分析" / "_index.json"
    candidates_md = professor_dir / CANDIDATES_MD
    if not index_path.is_file() and not candidates_md.is_file():
        return None
    entry = {
        "professor_dir": str(professor_dir),
        "professor": professor_dir.name,
        "category": professor_dir.parent.name,
        "source_fingerprint": migration_source_fingerprint(professor_dir),
        "already_migrated": (professor_dir / INPUT_PACK).is_file(),
        "schema2": False, "sidecar_ok": False, "candidates_meta": False,
        "metadata_ok": False, "gap_ids_exact": False,
        "gap_papers": 0, "valid_sidecars": 0,
    }
    if index_path.is_file():
        index, error = read_legacy_index(index_path)
        if error:
            entry["classification"] = "blocked"
            entry["reasons"] = [f"_index.json 不可读：{error}"]
            entry["stage2"] = entry["stage3"] = "blocked"
            return entry
        entry["schema2"] = index.get("schema") == 2
        papers = index.get("papers")
        if isinstance(papers, dict):
            gap_papers = 0
            valid = 0
            exact = True
            valid_gap_pairs = set()
            for key, paper in papers.items():
                if not isinstance(paper, dict):
                    continue
                has_gaps = bool(paper.get("gaps")) or bool(paper.get("gap"))
                if not has_gaps:
                    continue
                gap_papers += 1
                sidecar = paper.get("future_work_sidecar")
                if sidecar:
                    items, legacy, err = load_sidecar(sidecar, paper.get("file"))
                    index_gaps = {g.get("gap_id") for g in (paper.get("gaps") or [])
                                  if isinstance(g, dict) and isinstance(g.get("gap_id"), str)}
                    sidecar_gaps = {item.get("gap_id") for item in items}
                    gap_rows = paper.get("gaps") or []
                    statuses_valid = isinstance(gap_rows, list) and all(
                        isinstance(g, dict) and g.get("gap_id") in index_gaps and
                        g.get("status") in GAP_STATUSES and
                        isinstance(g.get("evidence"), str) and g.get("evidence").strip()
                        for g in gap_rows)
                    if err is None and index_gaps and sidecar_gaps == index_gaps and statuses_valid:
                        valid += 1
                        valid_gap_pairs.update((key, gap_id) for gap_id in index_gaps)
                    else:
                        exact = False
                else:
                    exact = False
            entry["gap_papers"] = gap_papers
            entry["valid_sidecars"] = valid
            entry["sidecar_ok"] = gap_papers == 0 or valid == gap_papers
            entry["gap_ids_exact"] = gap_papers == 0 or exact
            papers_json_path = professor_dir / "papers.json"
            papers_meta, metadata_error = read_json_file(papers_json_path)
            metadata_by_key = {}
            if metadata_error is None and isinstance(papers_meta, dict):
                metadata_by_key = {p.get("item_key"): p for p in papers_meta.get("papers", [])
                                   if isinstance(p, dict)}
            metadata_ok = True
            for key, paper in papers.items():
                if not isinstance(paper, dict):
                    metadata_ok = False
                    continue
                meta = metadata_by_key.get(key) or paper
                title = meta.get("title")
                year = meta.get("year")
                authorship = meta.get("authorship")
                if not isinstance(title, str) or not title.strip() or not isinstance(year, int) or \
                        authorship not in ("first", "corresponding", "solo", "middle", "pending"):
                    metadata_ok = False
            entry["metadata_ok"] = metadata_ok
            if not metadata_ok:
                entry.setdefault("reasons", []).append("论文标题/年份/署名元数据不足")
            if not entry["gap_ids_exact"]:
                entry.setdefault("reasons", []).append("sidecar gap ID 与 schema 2 gaps[] 不精确相等")
    if candidates_md.is_file():
        text = candidates_md.read_text(encoding="utf-8", errors="replace")
        metas = re.findall(r"candidate_meta:\s*(\{.*\})", text)
        parsed_ok = 0
        parsed_total = 0
        known_pairs = set()
        if isinstance(index_path, Path) and index_path.is_file():
            index_data, _ = read_legacy_index(index_path)
            for key, paper in (index_data or {}).get("papers", {}).items():
                for gap in (paper or {}).get("gaps", []):
                    if isinstance(gap, dict) and gap.get("gap_id"):
                        known_pairs.add((key, gap["gap_id"]))
        for meta in metas:
            try:
                payload = json.loads(meta)
                parsed_total += 1
                pairs = payload.get("gap_ids") or []
                pairs_ok = all(isinstance(pair, dict) and
                               (pair.get("item_key"), pair.get("gap_id")) in known_pairs
                               for pair in pairs)
                if payload.get("id") and not payload.get("compatibility_fallback") and pairs_ok:
                    parsed_ok += 1
            except json.JSONDecodeError:
                continue
        entry["candidates_meta"] = parsed_ok > 0
        if parsed_total and parsed_ok != parsed_total:
            entry.setdefault("reasons", []).append("候选 candidate_meta 的 gap ID 无法精确恢复")
    if entry["schema2"] or entry["candidates_meta"] or entry["gap_papers"]:
        entry.update(classify_direction(entry))
        if entry["classification"] == "ready" and not entry["metadata_ok"]:
            entry["classification"] = "blocked"
            entry["stage2"] = entry["stage3"] = "blocked"
            entry.setdefault("reasons", []).append("必要论文元数据不足，不能标记 ready")
        elif entry["classification"] == "ready" and not entry["gap_ids_exact"]:
            entry["classification"] = "blocked"
            entry["stage2"] = entry["stage3"] = "blocked"
            entry.setdefault("reasons", []).append("gap ID 不匹配，不能标记 ready")
    else:
        entry.update({"classification": "needs_stage2", "stage2": "needs_stage2",
                      "stage3": "needs_stage3",
                      "reasons": ["index 无 gap 数据或候选无机器元数据，按需重跑阶段 2"]})
    return entry


def cmd_migrate_plan(args) -> None:
    program_root = Path(args.program_root)
    base = program_root / "教授研究"
    if not base.is_dir():
        fail("invalid_params", f"no 教授研究 under {program_root}")
    entries = []
    seen = set()
    candidate_dirs = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        if (child / "papers.json").is_file() or (child / "论文分析").is_dir():
            candidate_dirs.append(child)
        for professor_dir in sorted(child.iterdir()):
            if professor_dir.is_dir() and ((professor_dir / "papers.json").is_file() or
                                           (professor_dir / "论文分析").is_dir()):
                candidate_dirs.append(professor_dir)
    for professor_dir in candidate_dirs:
        resolved = str(professor_dir.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        entry = migrate_entry_for_professor(professor_dir, program_root)
        if entry:
            entries.append(entry)
    ready = [e for e in entries if e.get("classification") == "ready" and not e.get("already_migrated")]
    plan = {
        "status": "ok",
        "schema": SCHEMA, "managed_by": MANAGED_BY, "generated_at": now_utc(),
        "program_root": str(program_root),
        "directions": entries,
        "ready_count": len(ready),
        "note": "ready=纯脚本可迁移；needs_stage2=缺有效 sidecar/精确 ID；needs_stage3=输入包可迁移但候选无机器元数据；blocked=文件损坏。--apply 只处理 ready 且未迁移的条目，绝不隐式启动阶段 2/3。"}
    if args.out:
        atomic_json(Path(args.out), plan)
    emit(plan)


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
        pack_directions.append(build_direction_pack(ctx, plan_entry, statuses, None))
        pack_directions[-1]["migrated"] = True
        pack_directions[-1]["narrative"] = None
    pack = {
        "schema": SCHEMA, "managed_by": MANAGED_BY, "generated_at": now_utc(),
        "professor": entry["professor"], "professor_dir": str(professor_dir),
        "migrated": True,
        "directions": pack_directions,
        "cache": {"render": {}}}
    atomic_json(professor_dir / INPUT_PACK, pack)
    if cache_entries:
        save_freshness_cache(professor_dir, cache_entries)
    return {"professor": entry["professor"], "applied": True,
            "pack": str(professor_dir / INPUT_PACK),
            "gaps_migrated": len(cache_entries)}


def cmd_migrate_apply(args) -> None:
    plan, error = read_json_file(Path(args.apply))
    if error or not isinstance(plan, dict):
        fail("invalid_params", f"plan unreadable: {args.apply}")
    plan_root_value = plan.get("program_root")
    if not isinstance(plan_root_value, str) or not plan_root_value:
        fail("invalid_params", "migration plan has no program_root")
    plan_root = Path(plan_root_value)
    program_root = Path(args.program_root) if args.program_root else plan_root
    try:
        if program_root.resolve() != plan_root.resolve():
            fail("invalid_params", "program_root does not match migration plan")
    except OSError:
        fail("invalid_params", "program_root is not resolvable")
    entries = plan.get("directions")
    if not isinstance(entries, list):
        fail("invalid_params", "migration plan directions must be a list")
    applied, skipped = [], []
    for entry in entries:
        if not isinstance(entry, dict):
            fail("invalid_params", "migration plan direction must be an object")
        if entry.get("classification") != "ready":
            skipped.append({"professor": entry.get("professor"),
                            "reason": entry.get("classification")})
            continue
        if entry.get("already_migrated"):
            skipped.append({"professor": entry.get("professor"), "reason": "already_migrated"})
            continue
        target = Path(entry.get("professor_dir") or "")
        try:
            base = program_root.resolve() / "教授研究"
            if not target.is_absolute() or os.path.commonpath((str(base), str(target.resolve()))) != str(base):
                skipped.append({"professor": entry.get("professor"),
                                "reason": "professor_dir_outside_program_root"})
                continue
        except (OSError, ValueError):
            skipped.append({"professor": entry.get("professor"), "reason": "invalid_professor_dir"})
            continue
        applied.append(apply_ready_entry(program_root, entry, plan))
    emit({"status": "ok", "applied": applied, "skipped": skipped})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="professor-contact deterministic state runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("stage2-resolve-plan")
    p.add_argument("--facts", required=True)
    p.set_defaults(func=lambda a: cmd_stage2_resolve_plan(a))

    p = sub.add_parser("stage2-resolve-finalize")
    p.add_argument("--facts", required=True)
    p.add_argument("--results", required=True)
    p.set_defaults(func=lambda a: cmd_stage2_resolve_finalize(a))

    p = sub.add_parser("stage2-plan")
    p.add_argument("--facts", required=True)
    p.set_defaults(func=lambda a: cmd_stage2_plan(a))

    p = sub.add_parser("stage2-finalize")
    p.add_argument("--facts", required=True)
    p.add_argument("--results", required=True)
    p.add_argument("--decision-file")
    p.add_argument("--resolved-directions")
    p.set_defaults(func=cmd_stage2_finalize)

    p = sub.add_parser("stage2-refine-plan")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--facts", help="原阶段 2 facts；存在时校验其 fingerprint")
    group.add_argument("--professor-dir", help="facts 已过期时，从已接受输入包读取修订材料")
    p.add_argument("--validation-file", required=True)
    p.add_argument("--collection-key", help="只为一个失败方向生成修订 job")
    p.set_defaults(func=cmd_stage2_refine_plan)

    p = sub.add_parser("stage2-refine-finalize")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--facts", help="原阶段 2 facts；存在时校验其 fingerprint")
    group.add_argument("--professor-dir", help="facts 已过期时，从已接受输入包读取修订材料")
    p.add_argument("--results", required=True)
    p.add_argument("--validation-file", required=True)
    p.add_argument("--collection-key", help="只应用一个失败方向的修订结果")
    p.add_argument("--decision-file")
    p.set_defaults(func=cmd_stage2_refine_finalize)

    p = sub.add_parser("stage3-plan")
    p.add_argument("--professor-dir", required=True)
    p.add_argument("--profile")
    p.add_argument("--refresh-scope", choices=REFRESH_SCOPES)
    p.add_argument("--collection-key", help="只处理输入包中的一个方向")
    p.add_argument("--selection")
    p.add_argument("--program-root")
    p.set_defaults(func=cmd_stage3_plan)

    p = sub.add_parser("stage3-finalize")
    p.add_argument("--professor-dir", required=True)
    p.add_argument("--results", required=True)
    p.add_argument("--profile")
    p.add_argument("--refresh-scope", choices=REFRESH_SCOPES)
    p.add_argument("--collection-key", help="只处理输入包中的一个方向")
    p.add_argument("--selection")
    p.add_argument("--program-root")
    p.add_argument("--decision-file")
    p.set_defaults(func=cmd_stage3_finalize)

    p = sub.add_parser("stage4-finalize")
    p.add_argument("--program-root", required=True)
    p.add_argument("--selection-input", required=True)
    p.add_argument("--profile")
    p.set_defaults(func=cmd_stage4_finalize)

    p = sub.add_parser("stage5-plan")
    p.add_argument("--program-root", required=True)
    p.add_argument("--email-pack")
    p.add_argument("--email-id")
    p.add_argument("--profile")
    p.add_argument("--template")
    p.add_argument("--followup-template")
    p.add_argument("--mode", choices=("first", "both", "followup"), default="first",
                    help="生成首封、首封+跟进，或只生成跟进邮件")
    p.add_argument("--result")
    p.add_argument("--choices")
    p.set_defaults(func=cmd_stage5_plan)

    p = sub.add_parser("stage5-finalize")
    p.add_argument("--program-root", required=True)
    p.add_argument("--email-pack")
    p.add_argument("--email-id")
    p.add_argument("--result", required=True)
    p.add_argument("--humanized")
    p.add_argument("--humanized-map", help="JSON object mapping output_id to absolute humanized body path")
    p.add_argument("--choices")
    p.add_argument("--template")
    p.add_argument("--followup-template")
    p.add_argument("--mode", choices=("first", "both", "followup"), default="first",
                    help="生成首封、首封+跟进，或只生成跟进邮件")
    p.add_argument("--profile")
    p.add_argument("--decision-file")
    p.set_defaults(func=cmd_stage5_finalize)

    p = sub.add_parser("stage5-record-validation")
    p.add_argument("--professor-dir", required=True)
    p.add_argument("--validation-file", required=True)
    p.set_defaults(func=cmd_stage5_record_validation)

    p = sub.add_parser("stage2-record-validation")
    p.add_argument("--professor-dir", required=True)
    p.add_argument("--validation-file", required=True)
    p.set_defaults(func=cmd_stage2_record_validation)

    p = sub.add_parser("stage3-record-validation")
    p.add_argument("--professor-dir", required=True)
    p.add_argument("--validation-file", required=True)
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
