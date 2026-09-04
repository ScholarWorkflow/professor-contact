#!/usr/bin/env python3
"""Deterministic Stage-2 ChatGPT handoff bundle builder/importer.

The helper is intentionally network/model free. The Stage-2 analyzer supplies
only the exact post-cost-gate, post-idempotency jobs. This helper packages those
jobs and later validates/materializes external results into the ordinary local
paper-analysis artifacts consumed by the existing Stage-2 pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

BUNDLE_SCHEMA = 1
BUNDLE_KIND = "professor-contact-stage2-chatgpt-handoff"
RESULT_KIND = "professor-contact-stage2-chatgpt-result"
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
FUTURE_HEADING = "## 作者明说的未来工作（Future Work）"
HELP_HEADING = "## 对自身研究的帮助评估"
REQUIRED_ANALYSIS_HEADINGS = (
    "## 总结",
    "## 问题是什么",
    "## 挑战是什么",
    "## Solution 是什么",
    "## 研究方法是什么",
    "## 贡献是什么",
    "## 局限性与批判性评价",
    FUTURE_HEADING,
    HELP_HEADING,
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_json_bytes(value))


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_write(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def _safe_component(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value.strip())
    return cleaned[:120] or "job"


def _portable_relpath(raw: str, field: str) -> str:
    normalized = raw.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or ":" in path.parts[0]
    ):
        raise ValueError(f"{field} must be a safe relative path")
    return path.as_posix()


def _resolve_under(root: Path, rel: str) -> Path:
    rel = _portable_relpath(rel, "relative path")
    target = (root / Path(*PurePosixPath(rel).parts)).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("relative path escapes professor directory") from error
    return target


def _local_file_relpath(raw: str | None, professor_dir: Path, field: str) -> str | None:
    """Convert local index metadata to a portable professor-relative path."""
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"{field} must be an existing absolute file")
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(professor_dir.resolve())
    except ValueError as error:
        raise ValueError(f"{field} must stay under professor_dir") from error
    return _portable_relpath(relative.as_posix(), field)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _read_index_entry(professor_dir: Path, item_key: str) -> dict[str, Any] | None:
    index_path = professor_dir / "论文分析" / "_index.json"
    if not index_path.is_file():
        return None
    index = _load_json(index_path)
    if not isinstance(index, dict):
        raise ValueError("existing _index.json must be an object")
    papers = index.get("papers")
    if not isinstance(papers, dict):
        return None
    entry = papers.get(item_key)
    return dict(entry) if isinstance(entry, dict) else None


def _capture_local_baseline(professor_dir: Path, item_key: str, analysis_relpath: str) -> dict[str, Any]:
    """Capture local state needed to prevent overwriting post-bundle work.

    An existing stale/abstract analysis is allowed: if it remains byte-for-byte
    and index-entry-for-index-entry identical to this captured baseline, import
    may replace it. Any local change after bundle creation makes the result stale.
    """
    analysis = _resolve_under(professor_dir, analysis_relpath)
    sidecar = Path(str(analysis) + ".future_work.json")
    facts_sidecar = Path(str(analysis) + ".facts.json")
    entry = _read_index_entry(professor_dir, item_key)
    return {
        "analysis_exists": analysis.is_file(),
        "analysis_sha256": _sha256_file(analysis) if analysis.is_file() else None,
        "sidecar_exists": sidecar.is_file(),
        "sidecar_sha256": _sha256_file(sidecar) if sidecar.is_file() else None,
        "facts_sidecar_exists": facts_sidecar.is_file(),
        "facts_sidecar_sha256": _sha256_file(facts_sidecar) if facts_sidecar.is_file() else None,
        "index_entry_exists": entry is not None,
        "index_entry_sha256": _sha256_json(entry) if entry is not None else None,
        "index_level": entry.get("level") if entry is not None else None,
    }


def _baseline_matches(professor_dir: Path, job: dict[str, Any]) -> bool:
    expected = job.get("local_baseline")
    if not isinstance(expected, dict):
        return False
    current = _capture_local_baseline(professor_dir, job["item_key"], job["analysis_relpath"])
    return current == expected


def _latest_matches(professor_dir: Path, manifest: dict[str, Any]) -> bool:
    latest_path = professor_dir / "论文分析" / "_chatgpt_handoff" / "_latest.json"
    if not latest_path.exists():
        return True
    latest = _load_json(latest_path)
    return (
        isinstance(latest, dict)
        and latest.get("handoff_id") == manifest.get("handoff_id")
        and latest.get("source_fingerprint") == manifest.get("source_fingerprint")
    )


def _verify_bundled_input(bundle_root: Path, job: dict[str, Any]) -> Path:
    """Bind manifest input_sha256 to the actual bytes extracted from the ZIP."""
    try:
        rel = _portable_relpath(str(job.get("input_path") or ""), "input_path")
    except ValueError as error:
        raise ValueError("external_result_hash_mismatch") from error
    path = bundle_root / Path(*PurePosixPath(rel).parts)
    expected = job.get("input_sha256")
    if not isinstance(expected, str) or not expected or not path.is_file():
        raise ValueError("external_result_hash_mismatch")
    if _sha256_file(path) != expected:
        raise ValueError("external_result_hash_mismatch")
    return path


def _validate_future_work_inputs(result: dict[str, Any]) -> None:
    """Require the existing PDF-grounded future-work contract exactly where usable.

    `future_work.py prepare` is PDF-only. PDF carriers therefore require the
    deterministic prepare/candidates pair. OCR-only fulltext carriers remain
    valid analysis jobs, but they must not smuggle an ungrounded future-work
    payload into the importer; their Markdown future-work section is sanitized
    and no authoritative sidecar is fabricated.
    """
    carrier = result["carrier"]
    prepare_raw = result["future_work_prepare_local"]
    candidates_raw = result["future_work_candidates_local"]

    if carrier == "pdf" and not (prepare_raw and candidates_raw):
        raise ValueError("pdf fulltext handoff requires future_work_prepare and future_work_candidates")
    if carrier != "pdf" and (prepare_raw or candidates_raw):
        raise ValueError("future_work_prepare and future_work_candidates are only valid for pdf carriers")
    if not (prepare_raw or candidates_raw):
        return
    if not (prepare_raw and candidates_raw):
        raise ValueError("future_work_prepare and future_work_candidates must be supplied together")

    prepare = Path(str(prepare_raw))
    candidates = Path(str(candidates_raw))
    for field, path in (("future_work_prepare", prepare), ("future_work_candidates", candidates)):
        if not path.is_absolute() or not path.is_file():
            raise ValueError(f"{field} must be an existing absolute file")

    prepare_payload = _load_json(prepare)
    candidates_payload = _load_json(candidates)
    if not isinstance(prepare_payload, dict) or not isinstance(prepare_payload.get("ocr_required_pages", []), list):
        raise ValueError("future_work_prepare must be a prepare JSON object")
    if not isinstance(candidates_payload, (dict, list)):
        raise ValueError("future_work_candidates must be a candidates JSON object/list")
    pdf_sha = prepare_payload.get("pdf_sha256")
    if pdf_sha != result["input_sha256"]:
        raise ValueError("future_work_prepare pdf_sha256 must match the bundled PDF")
    result["future_work_prepare_sha256"] = _sha256_file(prepare)
    result["future_work_candidates_sha256"] = _sha256_file(candidates)


def _validate_job_spec(raw: dict[str, Any], professor_dir: Path) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("each job must be an object")
    item_key = str(raw.get("item_key") or "").strip()
    if not item_key:
        raise ValueError("job.item_key is required")
    carrier = raw.get("carrier")
    level = raw.get("level")
    if carrier not in {"pdf", "ocr", "abstract_json"}:
        raise ValueError(f"unsupported carrier for {item_key}: {carrier}")
    if level not in {"fulltext", "abstract"}:
        raise ValueError(f"unsupported level for {item_key}: {level}")
    if carrier == "abstract_json" and level != "abstract":
        raise ValueError("abstract_json must use level=abstract")
    if carrier in {"pdf", "ocr"} and level != "fulltext":
        raise ValueError("pdf/ocr must use level=fulltext")

    input_path = Path(str(raw.get("input_path") or "")).expanduser()
    if not input_path.is_absolute() or not input_path.is_file():
        raise ValueError(f"input_path for {item_key} must be an existing absolute file")
    analysis_relpath = _portable_relpath(str(raw.get("analysis_relpath") or ""), "analysis_relpath")
    if not analysis_relpath.endswith(".md"):
        raise ValueError("analysis_relpath must end in .md")
    _resolve_under(professor_dir, analysis_relpath)

    direction = raw.get("research_direction") or {}
    if not isinstance(direction, dict):
        raise ValueError("research_direction must be an object")
    direction = {
        "collection_key": str(direction.get("collection_key") or ""),
        "name_ja": str(direction.get("name_ja") or ""),
        "name_zh": str(direction.get("name_zh") or ""),
        "user_note": str(direction.get("user_note") or ""),
    }

    result: dict[str, Any] = {
        "item_key": item_key,
        "carrier": carrier,
        "evidence_level": level,
        "input_path_local": str(input_path.resolve()),
        "input_sha256": _sha256_file(input_path),
        "analysis_relpath": analysis_relpath,
        "research_direction": direction,
        "research_direction_fp": str(raw.get("research_direction_fp") or ""),
        "authorship": str(raw.get("authorship") or "pending"),
        "authorship_note": raw.get("authorship_note"),
        "relevance_reason": str(raw.get("relevance_reason") or ""),
        "ocr_relpath": _local_file_relpath(raw.get("ocr_file"), professor_dir, "ocr_file"),
        "future_work_prepare_local": str(raw.get("future_work_prepare") or "") or None,
        "future_work_candidates_local": str(raw.get("future_work_candidates") or "") or None,
        "local_baseline": _capture_local_baseline(professor_dir, item_key, analysis_relpath),
    }
    _validate_future_work_inputs(result)
    return result


def _build_manifest(professor: str, normalized_jobs: list[dict[str, Any]]) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    fingerprint_rows: list[dict[str, Any]] = []
    for job in normalized_jobs:
        safe_key = _safe_component(job["item_key"])
        suffix = {"pdf": "paper.pdf", "ocr": "paper.txt", "abstract_json": "paper-analysis-input.json"}[job["carrier"]]
        input_rel = f"papers/{safe_key}/{suffix}"
        fp_payload = {
            "item_key": job["item_key"],
            "carrier": job["carrier"],
            "evidence_level": job["evidence_level"],
            "input_sha256": job["input_sha256"],
            "analysis_relpath": job["analysis_relpath"],
            "research_direction": job["research_direction"],
            "research_direction_fp": job["research_direction_fp"],
            "local_baseline": job["local_baseline"],
            "future_work_prepare_sha256": job.get("future_work_prepare_sha256"),
            "future_work_candidates_sha256": job.get("future_work_candidates_sha256"),
        }
        job_fp = _sha256_json(fp_payload)
        expected_future_work = job["carrier"] == "pdf"
        expected_facts = job["carrier"] == "pdf"
        entry: dict[str, Any] = {
            "job_id": f"paper-analysis:{job['item_key']}:{job_fp[:16]}",
            "item_key": job["item_key"],
            "carrier": job["carrier"],
            "evidence_level": job["evidence_level"],
            "input_path": input_rel,
            "input_sha256": job["input_sha256"],
            "analysis_relpath": job["analysis_relpath"],
            "research_direction": job["research_direction"],
            "research_direction_fp": job["research_direction_fp"],
            "local_baseline": job["local_baseline"],
            "expected": {
                "analysis": True,
                "future_work": expected_future_work,
                "facts": expected_facts,
            },
            "index_metadata": {
                "authorship": job["authorship"],
                "authorship_note": job["authorship_note"],
                "relevance_reason": job["relevance_reason"],
                "ocr_relpath": job["ocr_relpath"],
            },
        }
        if expected_future_work:
            prepare_payload = _load_json(Path(str(job["future_work_prepare_local"])))
            entry["future_work"] = {
                "prepare_path": f"papers/{safe_key}/future_work/prepare.json",
                "candidates_path": f"papers/{safe_key}/future_work/candidates.json",
                "prepare_sha256": job["future_work_prepare_sha256"],
                "candidates_sha256": job["future_work_candidates_sha256"],
                "ocr_required_pages": list(prepare_payload.get("ocr_required_pages") or []),
            }
        jobs.append(entry)
        fingerprint_rows.append({
            key: entry[key]
            for key in (
                "job_id", "item_key", "input_sha256", "evidence_level",
                "analysis_relpath", "research_direction_fp", "local_baseline",
            )
        })
        if expected_future_work:
            fingerprint_rows[-1]["future_work"] = entry["future_work"]
    source_fingerprint = _sha256_json({"professor": professor, "jobs": fingerprint_rows})
    return {
        "schema": BUNDLE_SCHEMA,
        "kind": BUNDLE_KIND,
        "handoff_id": source_fingerprint[:20],
        "source_fingerprint": source_fingerprint,
        "professor": professor,
        "jobs": jobs,
    }


def _zip_add_bytes(zf: zipfile.ZipFile, rel: str, data: bytes) -> None:
    info = zipfile.ZipInfo(_portable_relpath(rel, "zip path"), ZIP_EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100644 & 0xFFFF) << 16
    zf.writestr(info, data)


def _zip_add_file(zf: zipfile.ZipFile, rel: str, source: Path) -> None:
    _zip_add_bytes(zf, rel, source.read_bytes())


def _instructions() -> str:
    return """# Stage 2 ChatGPT handoff

This ZIP contains only the exact Stage-2 per-paper analysis jobs selected by the local workflow.

For each `manifest.json.jobs[]` entry:
1. Analyze only the bundled `input_path`; do not use Zotero/MCP or invent missing local context.
2. Preserve `job_id`, `item_key`, `input_sha256`, direction IDs, and target identity exactly.
3. Write the ordinary paper-analysis Markdown template to `results/<safe-job>/analysis.md`, where `<safe-job>` is the deterministic safe form of that exact `job_id`; do not add or override a `result_dir` field in the result row.
4. For every job with `expected.future_work=true` (PDF fulltext only), return `future_work_items.json` selected/translated only from the bundled exact candidates. If `future_work.ocr_required_pages` is non-empty, OCR exactly those pages and return `future_work_ocr.json` as `{\"pages\":{\"N\":\"text\"}}`.
5. For every PDF job with `expected.facts=true`, also return `facts.json`: the compact structured-facts draft already established during the same analysis pass — `paper` (title/authors/year/venue/doi), `research_problem`, `research_object`, `approach`, `findings[]`, `contributions[]`, `topic_terms[]`, `limitations[]`, optional `source_anchors` and `confidence`. Never include `future_work_ids`; the local importer joins them from the validated future-work sidecar. Never re-read the paper a second time just to build the draft.
6. Bind completed rows in `result_manifest.json` with schema/kind/handoff/source/job/item/input hash and `status=ok|partial|error`.

PDF fulltext jobs are not complete without their future-work payload and their facts draft. OCR-only and abstract-only jobs do not have a PDF-grounded future-work or facts contract (`expected.facts=false`): any external Future Work prose in their Markdown is discarded locally and cannot become a gap source, and no facts sidecar is fabricated for them. Do not return `_index.json`, `套磁候选输入.json`, or a ready-made `.future_work.json`/`.facts.json` as authoritative state. The local importer independently validates/finalizes PDF future-work evidence and facts drafts through the deterministic paper-analysis helpers and installs accepted results into the ordinary Stage-2 artifacts.
"""


def build_bundle(args: argparse.Namespace) -> dict[str, Any]:
    professor_dir = args.professor_dir.expanduser().resolve()
    payload = _load_json(args.jobs)
    if not isinstance(payload, dict) or payload.get("schema") != 1 or not isinstance(payload.get("jobs"), list):
        raise ValueError("jobs file must be {schema:1,jobs:[...]}")
    professor = str(args.professor or payload.get("professor") or professor_dir.name)
    normalized = [_validate_job_spec(job, professor_dir) for job in payload["jobs"]]
    if len({job["item_key"] for job in normalized}) != len(normalized):
        raise ValueError("duplicate item_key in jobs")
    # A handoff is a content-addressed logical set, not an ordered queue. Zotero
    # enumeration/caller ordering must therefore not affect manifest/fingerprint/ZIP bytes.
    normalized.sort(key=lambda job: job["item_key"])
    manifest = _build_manifest(professor, normalized)

    root = professor_dir / "论文分析" / "_chatgpt_handoff"
    bundle_dir = root / f"stage2-{manifest['handoff_id']}"
    zip_path = root / f"stage2-{manifest['handoff_id']}.zip"
    root.mkdir(parents=True, exist_ok=True)
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)
    _atomic_json(bundle_dir / "manifest.json", manifest)
    _atomic_write(bundle_dir / "instructions.md", _instructions().encode("utf-8"))

    by_item = {job["item_key"]: job for job in normalized}
    for entry in manifest["jobs"]:
        job = by_item[entry["item_key"]]
        local = bundle_dir / Path(*PurePosixPath(entry["input_path"]).parts)
        local.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(job["input_path_local"], local)
        if _sha256_file(local) != entry["input_sha256"]:
            raise ValueError("external_result_hash_mismatch: packaged carrier differs from captured source hash")
        _atomic_json(local.parent / "job.json", entry)
        if entry.get("future_work"):
            fw = entry["future_work"]
            for src_field, rel, hash_field in (
                ("future_work_prepare_local", fw["prepare_path"], "prepare_sha256"),
                ("future_work_candidates_local", fw["candidates_path"], "candidates_sha256"),
            ):
                dest = bundle_dir / Path(*PurePosixPath(rel).parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(job[src_field]), dest)
                if _sha256_file(dest) != fw[hash_field]:
                    raise ValueError("external_future_work_invalid: packaged future-work input hash mismatch")

    _atomic_json(root / "_latest.json", {
        "schema": 1,
        "handoff_id": manifest["handoff_id"],
        "source_fingerprint": manifest["source_fingerprint"],
    })
    fd, temp_zip = tempfile.mkstemp(prefix=f".{zip_path.name}.", dir=root)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_zip, "w") as zf:
            files = sorted(
                (p for p in bundle_dir.rglob("*") if p.is_file()),
                key=lambda p: p.relative_to(bundle_dir).as_posix(),
            )
            for path in files:
                _zip_add_file(zf, path.relative_to(bundle_dir).as_posix(), path)
        os.replace(temp_zip, zip_path)
    except BaseException:
        try:
            os.unlink(temp_zip)
        except FileNotFoundError:
            pass
        raise
    return {
        "status": "ready",
        "reason_code": None,
        "handoff_id": manifest["handoff_id"],
        "source_fingerprint": manifest["source_fingerprint"],
        "bundle_path": str(zip_path),
        "bundle_dir": str(bundle_dir),
        "jobs": len(manifest["jobs"]),
    }


def _check_zip(zf: zipfile.ZipFile) -> None:
    seen: set[str] = set()
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name in seen:
            raise ValueError("unsafe_zip_entry: duplicate entry")
        seen.add(name)
        try:
            _portable_relpath(name.rstrip("/"), "zip entry")
        except ValueError as error:
            raise ValueError("unsafe_zip_entry: path traversal") from error
        mode = (info.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise ValueError("unsafe_zip_entry: symlink")


def _extract_checked(zip_path: Path, dest: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        _check_zip(zf)
        for info in zf.infolist():
            parts = PurePosixPath(info.filename.rstrip("/")).parts
            target = dest / Path(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                with zf.open(info) as source, target.open("wb") as sink:
                    shutil.copyfileobj(source, sink)


def _validate_manifest(value: Any, kind: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != BUNDLE_SCHEMA or value.get("kind") != kind:
        raise ValueError(f"invalid {kind} manifest")
    return value


def _validate_analysis(path: Path) -> None:
    if not path.is_file():
        raise ValueError("external_analysis_invalid: missing analysis.md")
    text = path.read_text(encoding="utf-8")
    positions: list[int] = []
    for heading in REQUIRED_ANALYSIS_HEADINGS:
        pos = text.find(heading)
        if pos < 0:
            raise ValueError(f"external_analysis_invalid: missing heading {heading}")
        positions.append(pos)
    if positions != sorted(positions):
        raise ValueError("external_analysis_invalid: template headings out of order")


def _sanitize_unvalidated_future_work(path: Path, reason: str) -> None:
    """Never let unvalidated external Markdown become a legacy future-work source."""
    text = path.read_text(encoding="utf-8")
    left = text.find(FUTURE_HEADING)
    right = text.find(HELP_HEADING, left + len(FUTURE_HEADING))
    if left < 0 or right < 0:
        raise ValueError("external_analysis_invalid: missing future-work anchors")
    section = FUTURE_HEADING + f"\n—（{reason}；不得作为 gap 来源）\n"
    _atomic_write(path, (text[:left] + section + text[right:]).encode("utf-8"))


def _resolved_ocr_file(professor_dir: Path, metadata: dict[str, Any]) -> str | None:
    rel = metadata.get("ocr_relpath")
    if not rel:
        return None
    return str(_resolve_under(professor_dir, str(rel)))


def _index_with_job(
    professor_dir: Path,
    manifest: dict[str, Any],
    job: dict[str, Any],
    analysis_path: Path,
    sidecar_path: Path | None,
    facts_path: Path | None,
) -> dict[str, Any]:
    index_path = professor_dir / "论文分析" / "_index.json"
    if index_path.exists():
        index = _load_json(index_path)
        if not isinstance(index, dict):
            raise ValueError("existing _index.json must be an object")
    else:
        index = {"schema": 2, "future_work_schema": 1, "professor": manifest.get("professor"), "papers": {}}
    index["schema"] = 2
    index["future_work_schema"] = 1
    papers = index.setdefault("papers", {})
    if not isinstance(papers, dict):
        raise ValueError("existing _index.json papers must be an object")
    prior = papers.get(job["item_key"], {}) if isinstance(papers.get(job["item_key"]), dict) else {}
    metadata = job.get("index_metadata") or {}
    entry = dict(prior)
    if sidecar_path:
        future_state = "valid"
        future_error = None
    elif job.get("carrier") == "ocr":
        future_state = "failed"
        future_error = "future_work_unavailable_without_pdf_handoff"
    else:
        future_state = "failed"
        future_error = "future_work_unavailable_abstract_handoff"
    if facts_path:
        facts_state = "valid"
        facts_error = None
    elif job.get("carrier") == "ocr":
        facts_state = "unavailable"
        facts_error = "facts_unavailable_without_pdf_handoff"
    else:
        facts_state = "unavailable"
        facts_error = "facts_unavailable_abstract_handoff"
    entry.update({
        "file": str(analysis_path),
        "level": job["evidence_level"],
        "ocr_file": _resolved_ocr_file(professor_dir, metadata),
        "authorship": metadata.get("authorship", prior.get("authorship", "pending")),
        "authorship_note": metadata.get("authorship_note"),
        "relevance_reason": metadata.get("relevance_reason", prior.get("relevance_reason", "")),
        "future_work_sidecar": str(sidecar_path) if sidecar_path else None,
        "future_work_state": future_state,
        "future_work_error": future_error,
        "facts_sidecar": str(facts_path) if facts_path else None,
        "facts_state": facts_state,
        "facts_error": facts_error,
        "analysis_executor": "chatgpt_handoff",
        "handoff_id": manifest["handoff_id"],
        "source_fingerprint": manifest["source_fingerprint"],
        "input_sha256": job["input_sha256"],
    })
    papers[job["item_key"]] = entry
    return index


def _restore(path: Path, previous: bytes | None) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
    else:
        _atomic_write(path, previous)


def _install_job(
    professor_dir: Path,
    manifest: dict[str, Any],
    job: dict[str, Any],
    staged_analysis: Path,
    staged_sidecar: Path | None,
    staged_facts: Path | None = None,
) -> tuple[Path, Path | None]:
    analysis_target = _resolve_under(professor_dir, job["analysis_relpath"])
    sidecar_target = Path(str(analysis_target) + ".future_work.json")
    facts_target = Path(str(analysis_target) + ".facts.json")
    index_target = professor_dir / "论文分析" / "_index.json"

    # Expensive local finalization may have taken long enough for another Stage-2
    # run to update this item or build a newer handoff. Re-check both guards at
    # the install boundary rather than trusting the earlier import-time check.
    if not _latest_matches(professor_dir, manifest) or not _baseline_matches(professor_dir, job):
        raise ValueError("handoff_stale")
    new_index = _index_with_job(
        professor_dir, manifest, job, analysis_target,
        sidecar_target if staged_sidecar else None,
        facts_target if staged_facts else None,
    )
    if not _latest_matches(professor_dir, manifest) or not _baseline_matches(professor_dir, job):
        raise ValueError("handoff_stale")

    old_analysis = analysis_target.read_bytes() if analysis_target.is_file() else None
    old_sidecar = sidecar_target.read_bytes() if sidecar_target.is_file() else None
    old_facts = facts_target.read_bytes() if facts_target.is_file() else None
    old_index = index_target.read_bytes() if index_target.is_file() else None
    try:
        _atomic_write(analysis_target, staged_analysis.read_bytes())
        if staged_sidecar:
            _atomic_write(sidecar_target, staged_sidecar.read_bytes())
        else:
            sidecar_target.unlink(missing_ok=True)
        if staged_facts:
            _atomic_write(facts_target, staged_facts.read_bytes())
        else:
            facts_target.unlink(missing_ok=True)
        _atomic_json(index_target, new_index)
    except BaseException:
        _restore(analysis_target, old_analysis)
        _restore(sidecar_target, old_sidecar)
        _restore(facts_target, old_facts)
        _restore(index_target, old_index)
        raise
    return analysis_target, sidecar_target if staged_sidecar else None


def _run_future_work(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the installed PEP-723 helper through the paper-analysis uv contract."""
    return subprocess.run(["uv", "run", str(script), *arguments], text=True, capture_output=True, check=False)


def _bundle_future_paths(bundle_root: Path, job: dict[str, Any]) -> tuple[Path, Path, dict[str, Any]]:
    fw = job.get("future_work")
    if not isinstance(fw, dict):
        raise ValueError("external_future_work_invalid")
    try:
        prepare_rel = _portable_relpath(str(fw["prepare_path"]), "prepare_path")
        candidates_rel = _portable_relpath(str(fw["candidates_path"]), "candidates_path")
    except (KeyError, ValueError) as error:
        raise ValueError("external_future_work_invalid") from error
    prepared = bundle_root / Path(*PurePosixPath(prepare_rel).parts)
    candidates = bundle_root / Path(*PurePosixPath(candidates_rel).parts)
    if not prepared.is_file() or not candidates.is_file():
        raise ValueError("external_future_work_invalid")
    if fw.get("prepare_sha256") != _sha256_file(prepared) or fw.get("candidates_sha256") != _sha256_file(candidates):
        raise ValueError("external_future_work_invalid")
    return prepared, candidates, fw


def _finalize_future_work(
    args: argparse.Namespace,
    bundle_root: Path,
    source_dir: Path,
    staged_dir: Path,
    staged_analysis: Path,
    analysis_target: Path,
    job: dict[str, Any],
) -> Path:
    try:
        prepared, candidates, _ = _bundle_future_paths(bundle_root, job)
    except (OSError, ValueError):
        raise ValueError("external_future_work_invalid")

    working_prepared = prepared
    ocr = source_dir / "future_work_ocr.json"
    prepared_payload = _load_json(prepared)
    required_pages = prepared_payload.get("ocr_required_pages") or []
    if required_pages:
        if not ocr.is_file():
            raise ValueError("external_result_incomplete")
        proc = _run_future_work(args.future_work_script, "merge-ocr", "--prepared", str(prepared), "--ocr", str(ocr))
        if proc.returncode != 0:
            raise ValueError("external_future_work_invalid")
        try:
            merged_payload = json.loads(proc.stdout.splitlines()[-1])
        except (IndexError, json.JSONDecodeError) as error:
            raise ValueError("external_future_work_invalid") from error
        working_prepared = staged_dir / "merged_prepare.json"
        candidates = staged_dir / "merged_candidates.json"
        _atomic_json(working_prepared, merged_payload)
        _atomic_json(candidates, {"candidates": merged_payload.get("candidates", [])})

    items = source_dir / "future_work_items.json"
    if not items.is_file():
        raise ValueError("external_result_incomplete")
    proc = _run_future_work(args.future_work_script, "validate", "--items", str(items), "--candidates", str(candidates))
    if proc.returncode != 0:
        raise ValueError("external_future_work_invalid")
    prep_payload = _load_json(working_prepared)
    proc = _run_future_work(
        args.future_work_script,
        "finalize", "--analysis", str(staged_analysis),
        "--items", str(items), "--candidates", str(candidates), "--patch",
        "--pdf-sha256", str(prep_payload.get("pdf_sha256") or ""),
        "--evidence-level", "fulltext",
    )
    if proc.returncode != 0:
        raise ValueError("external_future_work_invalid")
    staged_sidecar = Path(str(staged_analysis) + ".future_work.json")
    if not staged_sidecar.is_file():
        raise ValueError("external_future_work_invalid")
    sidecar = _load_json(staged_sidecar)
    if sidecar.get("status") != "ok" or sidecar.get("analysis") != analysis_target.name:
        raise ValueError("external_future_work_invalid")
    return staged_sidecar


def _facts_script_path(args: argparse.Namespace) -> Path:
    """paper-analysis ships facts.py next to future_work.py in the same install.

    Reusing the sibling keeps the two deterministic helpers on one version, so a
    handoff result can never be finalized by mismatched helper generations. The
    path is absolutized but not symlink-resolved, matching how the caller passed
    the future-work script in.
    """
    return Path(str(args.future_work_script)).expanduser().absolute().with_name("facts.py")


def _finalize_facts(
    args: argparse.Namespace,
    source_dir: Path,
    staged_analysis: Path,
    staged_sidecar: Path,
    analysis_target: Path,
    job: dict[str, Any],
    bundled_input: Path,
) -> Path:
    """Finalize the external facts draft into the local sidecar contract.

    The draft from the external result is never installed as-is: the deterministic
    paper-analysis `facts.py` helper validates it against the staged analysis, the
    locally finalized future-work sidecar, and the exact bundled PDF, and only the
    helper writes `<analysis>.facts.json`. This is the same contract a local
    `paper-analysis full` pass satisfies, so both execution paths converge on one
    normalized paper-facts representation.
    """
    draft = source_dir / "facts.json"
    if not draft.is_file():
        raise ValueError("external_result_incomplete")
    facts_script = _facts_script_path(args)
    if not facts_script.is_file():
        raise ValueError("external_facts_invalid")
    staged_facts = Path(str(staged_analysis) + ".facts.json")
    staged_facts.unlink(missing_ok=True)
    proc = _run_future_work(
        facts_script,
        "finalize",
        "--analysis", str(staged_analysis),
        "--draft", str(draft),
        "--future-work", str(staged_sidecar),
        "--input", str(bundled_input),
        "--evidence-level", "fulltext",
    )
    if proc.returncode != 0:
        raise ValueError("external_facts_invalid")
    if not staged_facts.is_file():
        raise ValueError("external_facts_invalid")
    payload = _load_json(staged_facts)
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "ok"
        or payload.get("analysis") != analysis_target.name
        or payload.get("evidence_level") != "fulltext"
        or payload.get("input_fingerprint") != f"sha256:{job['input_sha256']}"
    ):
        raise ValueError("external_facts_invalid")
    return staged_facts


def import_result(args: argparse.Namespace) -> dict[str, Any]:
    professor_dir = args.professor_dir.expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix="stage2-handoff-import-") as temp:
        temp_root = Path(temp)
        bundle_root = temp_root / "bundle"
        result_root = temp_root / "result"
        _extract_checked(args.bundle.expanduser().resolve(), bundle_root)
        _extract_checked(args.result.expanduser().resolve(), result_root)
        manifest = _validate_manifest(_load_json(bundle_root / "manifest.json"), BUNDLE_KIND)

        if not _latest_matches(professor_dir, manifest):
            return {"status": "error", "reason_code": "handoff_stale", "imported": [], "missing": []}

        result_manifest = _validate_manifest(_load_json(result_root / "result_manifest.json"), RESULT_KIND)
        if result_manifest.get("handoff_id") != manifest.get("handoff_id"):
            return {"status": "error", "reason_code": "handoff_id_mismatch", "imported": [], "missing": []}
        if result_manifest.get("source_fingerprint") != manifest.get("source_fingerprint"):
            return {"status": "error", "reason_code": "source_fingerprint_mismatch", "imported": [], "missing": []}

        jobs = manifest.get("jobs")
        results = result_manifest.get("results")
        if not isinstance(jobs, list) or not isinstance(results, list):
            raise ValueError("manifest jobs/results must be arrays")
        job_map = {job["job_id"]: job for job in jobs if isinstance(job, dict) and job.get("job_id")}
        if len(job_map) != len(jobs):
            raise ValueError("external_result_duplicate_job")
        result_map: dict[str, dict[str, Any]] = {}
        for row in results:
            if not isinstance(row, dict) or not row.get("job_id"):
                raise ValueError("external_result_unknown_job")
            jid = row["job_id"]
            if jid in result_map:
                raise ValueError("external_result_duplicate_job")
            if jid not in job_map:
                raise ValueError("external_result_unknown_job")
            result_map[jid] = row

        imported: list[str] = []
        invalid: list[dict[str, str]] = []
        for jid, row in result_map.items():
            job = job_map[jid]
            try:
                bundled_input = _verify_bundled_input(bundle_root, job)
            except (OSError, ValueError):
                invalid.append({"job_id": jid, "reason_code": "external_result_hash_mismatch"})
                continue
            if row.get("item_key") != job.get("item_key") or row.get("input_sha256") != job.get("input_sha256"):
                invalid.append({"job_id": jid, "reason_code": "external_result_hash_mismatch"})
                continue
            if row.get("status") != "ok":
                invalid.append({"job_id": jid, "reason_code": "external_result_incomplete"})
                continue
            if not _baseline_matches(professor_dir, job):
                invalid.append({"job_id": jid, "reason_code": "handoff_stale"})
                continue
            # Result artifacts are bound to the job by a fixed directory derived
            # only from job_id. Never honor an external row-level path override.
            if "result_dir" in row:
                invalid.append({"job_id": jid, "reason_code": "external_result_hash_mismatch"})
                continue
            safe_job = _safe_component(jid)
            source_dir = result_root / "results" / safe_job
            analysis_source = source_dir / "analysis.md"
            try:
                _validate_analysis(analysis_source)
            except (OSError, UnicodeError, ValueError):
                invalid.append({"job_id": jid, "reason_code": "external_analysis_invalid"})
                continue

            analysis_target = _resolve_under(professor_dir, job["analysis_relpath"])
            staged_dir = temp_root / "staged" / _safe_component(jid)
            staged_dir.mkdir(parents=True, exist_ok=True)
            staged_analysis = staged_dir / analysis_target.name
            shutil.copyfile(analysis_source, staged_analysis)
            staged_sidecar: Path | None = None
            staged_facts: Path | None = None

            if (job.get("expected") or {}).get("future_work"):
                try:
                    staged_sidecar = _finalize_future_work(
                        args, bundle_root, source_dir, staged_dir,
                        staged_analysis, analysis_target, job,
                    )
                except (OSError, ValueError, json.JSONDecodeError) as error:
                    reason = "external_result_incomplete" if "external_result_incomplete" in str(error) else "external_future_work_invalid"
                    invalid.append({"job_id": jid, "reason_code": reason})
                    continue
                if (job.get("expected") or {}).get("facts"):
                    try:
                        staged_facts = _finalize_facts(
                            args, source_dir, staged_analysis, staged_sidecar,
                            analysis_target, job, bundled_input,
                        )
                    except (OSError, ValueError, json.JSONDecodeError) as error:
                        reason = "external_result_incomplete" if "external_result_incomplete" in str(error) else "external_facts_invalid"
                        invalid.append({"job_id": jid, "reason_code": reason})
                        continue
            else:
                try:
                    if job.get("carrier") == "ocr":
                        reason = "OCR-only handoff 无原 PDF，无法建立页码级 future-work 证据"
                    else:
                        reason = "abstract-only handoff 无页码级可验证 future-work 证据"
                    _sanitize_unvalidated_future_work(staged_analysis, reason)
                except (OSError, UnicodeError, ValueError):
                    invalid.append({"job_id": jid, "reason_code": "external_analysis_invalid"})
                    continue

            try:
                _install_job(professor_dir, manifest, job, staged_analysis, staged_sidecar, staged_facts)
            except (OSError, ValueError):
                invalid.append({"job_id": jid, "reason_code": "handoff_stale"})
                continue
            imported.append(jid)

        missing = [job["job_id"] for job in jobs if job["job_id"] not in imported]
        if invalid:
            return {
                "status": "partial" if imported else "needs_external_result",
                "reason_code": invalid[0]["reason_code"],
                "handoff_id": manifest["handoff_id"],
                "imported": imported,
                "missing": missing,
                "invalid": invalid,
            }
        if missing:
            return {
                "status": "partial",
                "reason_code": "external_result_incomplete",
                "handoff_id": manifest["handoff_id"],
                "imported": imported,
                "missing": missing,
            }
        return {
            "status": "imported",
            "reason_code": None,
            "handoff_id": manifest["handoff_id"],
            "imported": imported,
            "missing": [],
        }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--professor-dir", required=True, type=Path)
    build.add_argument("--jobs", required=True, type=Path)
    build.add_argument("--professor")
    imp = sub.add_parser("import")
    imp.add_argument("--professor-dir", required=True, type=Path)
    imp.add_argument("--bundle", required=True, type=Path)
    imp.add_argument("--result", required=True, type=Path)
    imp.add_argument("--future-work-script", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "build":
            output = build_bundle(args)
        else:
            output = import_result(args)
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        message = str(error)
        known = (
            "unsafe_zip_entry", "handoff_stale", "handoff_id_mismatch",
            "source_fingerprint_mismatch", "external_result_incomplete",
            "external_result_unknown_job", "external_result_duplicate_job",
            "external_result_hash_mismatch", "external_analysis_invalid",
            "external_future_work_invalid", "external_facts_invalid",
        )
        reason = next((code for code in known if code in message), "invalid_handoff_input")
        output = {"status": "error", "reason_code": reason, "error": message[:300]}
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
