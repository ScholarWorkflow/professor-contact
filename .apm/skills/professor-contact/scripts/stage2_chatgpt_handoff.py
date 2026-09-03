#!/usr/bin/env python3
"""Deterministic Stage-2 ChatGPT handoff bundle builder/importer.

This helper is deliberately network/model free.  The analyzer supplies the exact
post-cost-gate, post-idempotency paper-analysis jobs.  The helper packages only
those jobs and later validates/materializes external results into the ordinary
paper-analysis artifacts consumed by Stage 2.
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
REQUIRED_ANALYSIS_HEADINGS = (
    "## 总结",
    "## 问题是什么",
    "## 挑战是什么",
    "## Solution 是什么",
    "## 研究方法是什么",
    "## 贡献是什么",
    "## 局限性与批判性评价",
    "## 作者明说的未来工作（Future Work）",
    "## 对自身研究的帮助评估",
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


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
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
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


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


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
    result = {
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
        "ocr_file": str(raw.get("ocr_file") or "") or None,
        "future_work_prepare_local": str(raw.get("future_work_prepare") or "") or None,
        "future_work_candidates_local": str(raw.get("future_work_candidates") or "") or None,
    }
    if result["future_work_prepare_local"] or result["future_work_candidates_local"]:
        if not (result["future_work_prepare_local"] and result["future_work_candidates_local"]):
            raise ValueError("future_work_prepare and future_work_candidates must be supplied together")
        for field in ("future_work_prepare_local", "future_work_candidates_local"):
            path = Path(str(result[field]))
            if not path.is_absolute() or not path.is_file():
                raise ValueError(f"{field} must be an existing absolute file")
    return result


def _build_manifest(professor: str, normalized_jobs: list[dict[str, Any]]) -> dict[str, Any]:
    jobs = []
    fingerprint_rows = []
    for job in normalized_jobs:
        safe_key = _safe_component(job["item_key"])
        if job["carrier"] == "pdf":
            input_rel = f"papers/{safe_key}/paper.pdf"
        elif job["carrier"] == "ocr":
            input_rel = f"papers/{safe_key}/paper.txt"
        else:
            input_rel = f"papers/{safe_key}/paper-analysis-input.json"
        fp_payload = {
            "item_key": job["item_key"],
            "carrier": job["carrier"],
            "evidence_level": job["evidence_level"],
            "input_sha256": job["input_sha256"],
            "analysis_relpath": job["analysis_relpath"],
            "research_direction": job["research_direction"],
            "research_direction_fp": job["research_direction_fp"],
        }
        job_fp = _sha256_json(fp_payload)
        job_id = f"paper-analysis:{job['item_key']}:{job_fp[:16]}"
        entry = {
            "job_id": job_id,
            "item_key": job["item_key"],
            "carrier": job["carrier"],
            "evidence_level": job["evidence_level"],
            "input_path": input_rel,
            "input_sha256": job["input_sha256"],
            "analysis_relpath": job["analysis_relpath"],
            "research_direction": job["research_direction"],
            "research_direction_fp": job["research_direction_fp"],
            "expected": {
                "analysis": True,
                "future_work": bool(job["future_work_prepare_local"]),
            },
            "index_metadata": {
                "authorship": job["authorship"],
                "authorship_note": job["authorship_note"],
                "relevance_reason": job["relevance_reason"],
                "ocr_file": job["ocr_file"],
            },
        }
        if job["future_work_prepare_local"]:
            entry["future_work"] = {
                "prepare_path": f"papers/{safe_key}/future_work/prepare.json",
                "candidates_path": f"papers/{safe_key}/future_work/candidates.json",
            }
        jobs.append(entry)
        fingerprint_rows.append({k: entry[k] for k in ("job_id", "item_key", "input_sha256", "evidence_level", "analysis_relpath", "research_direction_fp")})
    source_fingerprint = _sha256_json({"professor": professor, "jobs": fingerprint_rows})
    handoff_id = source_fingerprint[:20]
    return {
        "schema": BUNDLE_SCHEMA,
        "kind": BUNDLE_KIND,
        "handoff_id": handoff_id,
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


def build_bundle(args: argparse.Namespace) -> dict[str, Any]:
    professor_dir = args.professor_dir.expanduser().resolve()
    payload = _load_json(args.jobs)
    if not isinstance(payload, dict) or payload.get("schema") != 1 or not isinstance(payload.get("jobs"), list):
        raise ValueError("jobs file must be {schema:1,jobs:[...]}")
    professor = str(args.professor or payload.get("professor") or professor_dir.name)
    normalized = [_validate_job_spec(job, professor_dir) for job in payload["jobs"]]
    if len({job["item_key"] for job in normalized}) != len(normalized):
        raise ValueError("duplicate item_key in jobs")
    manifest = _build_manifest(professor, normalized)
    root = professor_dir / "论文分析" / "_chatgpt_handoff"
    bundle_dir = root / f"stage2-{manifest['handoff_id']}"
    zip_path = root / f"stage2-{manifest['handoff_id']}.zip"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    _atomic_json(bundle_dir / "manifest.json", manifest)
    instructions = (
        "# Stage 2 ChatGPT handoff\n\n"
        "For every manifest job, analyze only the bundled carrier. Do not invent or change job_id, item_key, hashes, direction IDs, or target paths.\n"
        "Return result_manifest.json plus one results/<safe-job>/ directory per completed job. analysis.md must follow the ordinary paper-analysis template.\n"
        "When future_work is expected, select/translate only exact prepared candidates; if OCR is required, return future_work_ocr.json using the {\"pages\":{\"N\":\"text\"}} shape.\n"
        "Never return _index.json, 套磁候选输入.json, or a ready-made .future_work.json as authoritative state.\n"
    )
    _atomic_write(bundle_dir / "instructions.md", instructions.encode("utf-8"))

    by_item = {job["item_key"]: job for job in normalized}
    for entry in manifest["jobs"]:
        job = by_item[entry["item_key"]]
        local = bundle_dir / Path(*PurePosixPath(entry["input_path"]).parts)
        local.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(job["input_path_local"], local)
        job_dir = local.parent
        _atomic_json(job_dir / "job.json", entry)
        if entry.get("future_work"):
            fw = entry["future_work"]
            for src_field, rel in (
                ("future_work_prepare_local", fw["prepare_path"]),
                ("future_work_candidates_local", fw["candidates_path"]),
            ):
                dest = bundle_dir / Path(*PurePosixPath(rel).parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(job[src_field]), dest)

    root.mkdir(parents=True, exist_ok=True)
    _atomic_json(root / "_latest.json", {"schema": 1, "handoff_id": manifest["handoff_id"], "source_fingerprint": manifest["source_fingerprint"]})
    fd, temp_zip = tempfile.mkstemp(prefix=f".{zip_path.name}.", dir=root)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_zip, "w") as zf:
            for path in sorted((p for p in bundle_dir.rglob("*") if p.is_file()), key=lambda p: p.relative_to(bundle_dir).as_posix()):
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
        path = PurePosixPath(name)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("unsafe_zip_entry: path traversal")
        mode = (info.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise ValueError("unsafe_zip_entry: symlink")


def _extract_checked(zip_path: Path, dest: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        _check_zip(zf)
        for info in zf.infolist():
            target = dest / Path(*PurePosixPath(info.filename).parts)
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
    positions = []
    for heading in REQUIRED_ANALYSIS_HEADINGS:
        pos = text.find(heading)
        if pos < 0:
            raise ValueError(f"external_analysis_invalid: missing heading {heading}")
        positions.append(pos)
    if positions != sorted(positions):
        raise ValueError("external_analysis_invalid: template headings out of order")


def _update_index(professor_dir: Path, manifest: dict[str, Any], job: dict[str, Any], analysis_path: Path, sidecar_path: Path | None) -> None:
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
    entry.update({
        "file": str(analysis_path),
        "level": job["evidence_level"],
        "ocr_file": metadata.get("ocr_file"),
        "authorship": metadata.get("authorship", prior.get("authorship", "pending")),
        "authorship_note": metadata.get("authorship_note"),
        "relevance_reason": metadata.get("relevance_reason", prior.get("relevance_reason", "")),
        "future_work_sidecar": str(sidecar_path) if sidecar_path else None,
        "future_work_state": "valid" if sidecar_path else prior.get("future_work_state", "none"),
        "future_work_error": None,
        "analysis_executor": "chatgpt_handoff",
        "handoff_id": manifest["handoff_id"],
    })
    papers[job["item_key"]] = entry
    _atomic_json(index_path, index)


def import_result(args: argparse.Namespace) -> dict[str, Any]:
    professor_dir = args.professor_dir.expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix="stage2-handoff-import-") as temp:
        temp_root = Path(temp)
        bundle_root = temp_root / "bundle"
        result_root = temp_root / "result"
        _extract_checked(args.bundle.expanduser().resolve(), bundle_root)
        _extract_checked(args.result.expanduser().resolve(), result_root)
        manifest = _validate_manifest(_load_json(bundle_root / "manifest.json"), BUNDLE_KIND)
        latest_path = professor_dir / "论文分析" / "_chatgpt_handoff" / "_latest.json"
        if latest_path.exists():
            latest = _load_json(latest_path)
            if latest.get("handoff_id") != manifest.get("handoff_id") or latest.get("source_fingerprint") != manifest.get("source_fingerprint"):
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
        job_map = {job["job_id"]: job for job in jobs}
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
            if row.get("item_key") != job.get("item_key") or row.get("input_sha256") != job.get("input_sha256"):
                invalid.append({"job_id": jid, "reason_code": "external_result_hash_mismatch"})
                continue
            if row.get("status") not in {"ok", "partial"}:
                invalid.append({"job_id": jid, "reason_code": "external_result_incomplete"})
                continue
            safe_job = str(row.get("result_dir") or _safe_component(jid))
            try:
                safe_job = _portable_relpath(safe_job, "result_dir")
            except ValueError:
                invalid.append({"job_id": jid, "reason_code": "unsafe_zip_entry"})
                continue
            source_dir = result_root / "results" / Path(*PurePosixPath(safe_job).parts)
            analysis_source = source_dir / "analysis.md"
            try:
                _validate_analysis(analysis_source)
            except ValueError:
                invalid.append({"job_id": jid, "reason_code": "external_analysis_invalid"})
                continue
            analysis_target = _resolve_under(professor_dir, job["analysis_relpath"])
            if analysis_target.exists():
                index_path = professor_dir / "论文分析" / "_index.json"
                current = _load_json(index_path) if index_path.exists() else {}
                current_entry = ((current.get("papers") or {}).get(job["item_key"]) or {}) if isinstance(current, dict) else {}
                if current_entry.get("handoff_id") != manifest["handoff_id"]:
                    invalid.append({"job_id": jid, "reason_code": "handoff_stale"})
                    continue
            staged_analysis = temp_root / "staged" / _safe_component(jid) / "analysis.md"
            staged_analysis.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(analysis_source, staged_analysis)
            sidecar_target: Path | None = None
            if (job.get("expected") or {}).get("future_work"):
                fw = job.get("future_work") or {}
                prepared = bundle_root / Path(*PurePosixPath(fw["prepare_path"]).parts)
                candidates = bundle_root / Path(*PurePosixPath(fw["candidates_path"]).parts)
                working_prepared = prepared
                ocr = source_dir / "future_work_ocr.json"
                if ocr.exists():
                    merged = temp_root / "staged" / _safe_component(jid) / "merged_prepare.json"
                    proc = subprocess.run([str(args.future_work_script), "merge-ocr", "--prepared", str(prepared), "--ocr", str(ocr)], text=True, capture_output=True, check=False)
                    if proc.returncode != 0:
                        invalid.append({"job_id": jid, "reason_code": "external_future_work_invalid"})
                        continue
                    merged_payload = json.loads(proc.stdout.splitlines()[-1])
                    _atomic_json(merged, merged_payload)
                    cand_payload = {"candidates": merged_payload.get("candidates", [])}
                    merged_candidates = merged.with_name("merged_candidates.json")
                    _atomic_json(merged_candidates, cand_payload)
                    working_prepared = merged
                    candidates = merged_candidates
                else:
                    prepared_payload = _load_json(prepared)
                    if prepared_payload.get("ocr_required_pages"):
                        invalid.append({"job_id": jid, "reason_code": "external_future_work_invalid"})
                        continue
                items = source_dir / "future_work_items.json"
                if not items.is_file():
                    invalid.append({"job_id": jid, "reason_code": "external_result_incomplete"})
                    continue
                proc = subprocess.run([str(args.future_work_script), "validate", "--items", str(items), "--candidates", str(candidates)], text=True, capture_output=True, check=False)
                if proc.returncode != 0:
                    invalid.append({"job_id": jid, "reason_code": "external_future_work_invalid"})
                    continue
                prep_payload = _load_json(working_prepared)
                proc = subprocess.run([
                    str(args.future_work_script), "finalize", "--analysis", str(staged_analysis),
                    "--items", str(items), "--candidates", str(candidates), "--patch",
                    "--pdf-sha256", str(prep_payload.get("pdf_sha256") or ""),
                    "--evidence-level", "fulltext",
                ], text=True, capture_output=True, check=False)
                if proc.returncode != 0:
                    invalid.append({"job_id": jid, "reason_code": "external_future_work_invalid"})
                    continue
                staged_sidecar = Path(str(staged_analysis) + ".future_work.json")
                if not staged_sidecar.is_file():
                    invalid.append({"job_id": jid, "reason_code": "external_future_work_invalid"})
                    continue
                sidecar_target = Path(str(analysis_target) + ".future_work.json")
            _atomic_write(analysis_target, staged_analysis.read_bytes())
            if sidecar_target:
                _atomic_write(sidecar_target, Path(str(staged_analysis) + ".future_work.json").read_bytes())
            _update_index(professor_dir, manifest, job, analysis_target, sidecar_target)
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


def main() -> None:
    args = _parser().parse_args()
    try:
        output = build_bundle(args) if args.command == "build" else import_result(args)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        message = str(exc)
        reason = "unsafe_zip_entry" if message.startswith("unsafe_zip_entry") else "error"
        output = {"status": "error", "reason_code": reason, "message": message[:400]}
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
