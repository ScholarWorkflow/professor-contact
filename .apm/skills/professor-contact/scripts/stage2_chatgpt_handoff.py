#!/usr/bin/env python3
"""Hardened public entrypoint for deterministic Stage-2 ChatGPT handoff.

The transport implementation lives in `_stage2_chatgpt_handoff_impl.py`. This
entrypoint owns the integrity/concurrency invariants that must wrap every
build/import path:

1. manifest/job/source IDs are recomputed from the complete canonical manifest;
2. final artifact/index installation is serialized by a professor-scoped lock;
3. legacy/local Stage-2 writers register a professor-scoped lease before any
   direct analysis/OCR/index writes, so imports never race a non-locking writer;
4. OCR-required future-work selections are rebound locally to the exact
   candidates produced by `future_work.py merge-ocr`, so the external executor
   never has to invent or reproduce candidate IDs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

_IMPL_PATH = Path(__file__).with_name("_stage2_chatgpt_handoff_impl.py")
_SPEC = importlib.util.spec_from_file_location("_stage2_chatgpt_handoff_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load Stage-2 handoff implementation: {_IMPL_PATH}")
_impl = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_impl)

# Preserve the existing module-level API (including tested private helpers).
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

_ORIG_VALIDATE_MANIFEST = _impl._validate_manifest
_ORIG_VERIFY_BUNDLED_INPUT = _impl._verify_bundled_input
_ORIG_INSTALL_JOB = _impl._install_job
_ORIG_BUILD_BUNDLE = _impl.build_bundle
_ORIG_IMPORT_RESULT = _impl.import_result

_LOCAL_LEASE_NAME = ".stage2-local-writer.json"
_LOCAL_LEASE_TTL_SECONDS = 24 * 60 * 60
_SPACE_RE = re.compile(r"\s+")


def _carrier_relpath(item_key: str, carrier: str) -> str:
    suffix = {
        "pdf": "paper.pdf",
        "ocr": "paper.txt",
        "abstract_json": "paper-analysis-input.json",
    }[carrier]
    return f"papers/{_impl._safe_component(item_key)}/{suffix}"


def _future_relpaths(item_key: str) -> tuple[str, str]:
    safe = _impl._safe_component(item_key)
    return (
        f"papers/{safe}/future_work/prepare.json",
        f"papers/{safe}/future_work/candidates.json",
    )


def _job_id_payload(entry: dict[str, Any]) -> dict[str, Any]:
    payload = dict(entry)
    payload.pop("job_id", None)
    return payload


def _expected_job_id(entry: dict[str, Any]) -> str:
    item_key = str(entry.get("item_key") or "")
    fingerprint = _impl._sha256_json(_job_id_payload(entry))
    return f"paper-analysis:{item_key}:{fingerprint[:16]}"


def _source_fingerprint(professor: str, jobs: list[dict[str, Any]]) -> str:
    return _impl._sha256_json({"professor": professor, "jobs": jobs})


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(ch in "0123456789abcdef" for ch in value)


def _verify_manifest_integrity(manifest: dict[str, Any]) -> None:
    """Bind every authoritative manifest field to job/source/handoff IDs."""
    professor = manifest.get("professor")
    jobs = manifest.get("jobs")
    if not isinstance(professor, str) or not professor or not isinstance(jobs, list):
        raise ValueError("external_result_hash_mismatch")

    item_keys: list[str] = []
    job_ids: set[str] = set()
    safe_keys: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("external_result_hash_mismatch")
        item_key = str(job.get("item_key") or "")
        carrier = job.get("carrier")
        level = job.get("evidence_level")
        if not item_key or carrier not in {"pdf", "ocr", "abstract_json"}:
            raise ValueError("external_result_hash_mismatch")
        if level not in {"fulltext", "abstract"}:
            raise ValueError("external_result_hash_mismatch")
        if carrier == "abstract_json" and level != "abstract":
            raise ValueError("external_result_hash_mismatch")
        if carrier in {"pdf", "ocr"} and level != "fulltext":
            raise ValueError("external_result_hash_mismatch")
        if job.get("input_path") != _carrier_relpath(item_key, str(carrier)):
            raise ValueError("external_result_hash_mismatch")
        if not _is_sha256(job.get("input_sha256")):
            raise ValueError("external_result_hash_mismatch")

        try:
            analysis_relpath = _impl._portable_relpath(
                str(job.get("analysis_relpath") or ""), "analysis_relpath"
            )
            if not analysis_relpath.endswith(".md"):
                raise ValueError("analysis target must be markdown")
            metadata = job.get("index_metadata")
            if not isinstance(metadata, dict):
                raise ValueError("index_metadata must be an object")
            if metadata.get("ocr_relpath"):
                _impl._portable_relpath(str(metadata["ocr_relpath"]), "ocr_relpath")
        except ValueError as error:
            raise ValueError("external_result_hash_mismatch") from error

        if not isinstance(job.get("research_direction"), dict):
            raise ValueError("external_result_hash_mismatch")
        if not isinstance(job.get("local_baseline"), dict):
            raise ValueError("external_result_hash_mismatch")

        expected_future_work = carrier == "pdf"
        if job.get("expected") != {"analysis": True, "future_work": expected_future_work}:
            raise ValueError("external_result_hash_mismatch")
        future_work = job.get("future_work")
        if expected_future_work:
            if not isinstance(future_work, dict):
                raise ValueError("external_result_hash_mismatch")
            prepare_path, candidates_path = _future_relpaths(item_key)
            required_pages = future_work.get("ocr_required_pages")
            if (
                future_work.get("prepare_path") != prepare_path
                or future_work.get("candidates_path") != candidates_path
                or not _is_sha256(future_work.get("prepare_sha256"))
                or not _is_sha256(future_work.get("candidates_sha256"))
                or not isinstance(required_pages, list)
            ):
                raise ValueError("external_result_hash_mismatch")
            expected_contract = "ocr-excerpt-v1" if required_pages else "exact-items-v1"
            if future_work.get("selection_contract") != expected_contract:
                raise ValueError("external_result_hash_mismatch")
        elif future_work is not None:
            raise ValueError("external_result_hash_mismatch")

        expected_job_id = _expected_job_id(job)
        if job.get("job_id") != expected_job_id or expected_job_id in job_ids:
            raise ValueError("external_result_hash_mismatch")
        job_ids.add(expected_job_id)
        item_keys.append(item_key)
        safe = _impl._safe_component(item_key)
        if safe in safe_keys:
            raise ValueError("external_result_hash_mismatch")
        safe_keys.add(safe)

    # The logical job set is canonicalized by item_key before fingerprinting.
    if item_keys != sorted(item_keys) or len(set(item_keys)) != len(item_keys):
        raise ValueError("external_result_hash_mismatch")

    source = _source_fingerprint(professor, jobs)
    if manifest.get("source_fingerprint") != source or manifest.get("handoff_id") != source[:20]:
        raise ValueError("external_result_hash_mismatch")


def _build_manifest(professor: str, normalized_jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a manifest whose complete authoritative job payload is content-bound."""
    safe_keys = [_impl._safe_component(job["item_key"]) for job in normalized_jobs]
    if len(set(safe_keys)) != len(safe_keys):
        raise ValueError("item_key safe-path collision in jobs")

    jobs: list[dict[str, Any]] = []
    for job in normalized_jobs:
        expected_future_work = job["carrier"] == "pdf"
        entry: dict[str, Any] = {
            "item_key": job["item_key"],
            "carrier": job["carrier"],
            "evidence_level": job["evidence_level"],
            "input_path": _carrier_relpath(job["item_key"], job["carrier"]),
            "input_sha256": job["input_sha256"],
            "analysis_relpath": job["analysis_relpath"],
            "research_direction": job["research_direction"],
            "research_direction_fp": job["research_direction_fp"],
            "local_baseline": job["local_baseline"],
            "expected": {"analysis": True, "future_work": expected_future_work},
            "index_metadata": {
                "authorship": job["authorship"],
                "authorship_note": job["authorship_note"],
                "relevance_reason": job["relevance_reason"],
                "ocr_relpath": job["ocr_relpath"],
            },
        }
        if expected_future_work:
            prepare_payload = _impl._load_json(Path(str(job["future_work_prepare_local"])))
            required_pages = list(prepare_payload.get("ocr_required_pages") or [])
            prepare_path, candidates_path = _future_relpaths(job["item_key"])
            entry["future_work"] = {
                "prepare_path": prepare_path,
                "candidates_path": candidates_path,
                "prepare_sha256": job["future_work_prepare_sha256"],
                "candidates_sha256": job["future_work_candidates_sha256"],
                "ocr_required_pages": required_pages,
                "selection_contract": "ocr-excerpt-v1" if required_pages else "exact-items-v1",
            }
        entry["job_id"] = _expected_job_id(entry)
        jobs.append(entry)

    source = _source_fingerprint(professor, jobs)
    manifest = {
        "schema": _impl.BUNDLE_SCHEMA,
        "kind": _impl.BUNDLE_KIND,
        "handoff_id": source[:20],
        "source_fingerprint": source,
        "professor": professor,
        "jobs": jobs,
    }
    _verify_manifest_integrity(manifest)
    return manifest


def _validate_manifest(value: Any, kind: str) -> dict[str, Any]:
    manifest = _ORIG_VALIDATE_MANIFEST(value, kind)
    if kind == _impl.BUNDLE_KIND:
        _verify_manifest_integrity(manifest)
    return manifest


def _verify_bundled_input(bundle_root: Path, job: dict[str, Any]) -> Path:
    path = _ORIG_VERIFY_BUNDLED_INPUT(bundle_root, job)
    job_json = path.parent / "job.json"
    try:
        if not job_json.is_file() or _impl._load_json(job_json) != job:
            raise ValueError("external_result_hash_mismatch")
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("external_result_hash_mismatch") from error
    return path


@contextmanager
def _professor_lock(professor_dir: Path) -> Iterator[None]:
    """Professor-scoped OS lock for Stage-2 coordination/transactions."""
    lock_path = professor_dir / "论文分析" / ".stage2-write.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt  # type: ignore

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl  # type: ignore

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt  # type: ignore

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl  # type: ignore

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _local_lease_path(professor_dir: Path) -> Path:
    return professor_dir / "论文分析" / _LOCAL_LEASE_NAME


def _active_local_lease_unlocked(professor_dir: Path) -> dict[str, Any] | None:
    """Read an active local-writer lease while the caller holds `_professor_lock`."""
    path = _local_lease_path(professor_dir)
    if not path.is_file():
        return None
    try:
        payload = _impl._load_json(path)
    except (OSError, json.JSONDecodeError):
        # A malformed marker is treated as active rather than risk an overwrite.
        return {"malformed": True}
    if not isinstance(payload, dict):
        return {"malformed": True}
    expires_at = payload.get("expires_at")
    if isinstance(expires_at, (int, float)) and expires_at <= time.time():
        path.unlink(missing_ok=True)
        return None
    return payload


def acquire_local_lease(
    professor_dir: Path,
    token: str,
    *,
    ttl_seconds: int = _LOCAL_LEASE_TTL_SECONDS,
) -> dict[str, Any]:
    """Register the legacy/local Stage-2 writer without requiring it to hold a lock.

    Registration itself is serialized by `_professor_lock`. Once registered,
    importer installation checks the marker while holding the same lock. Thus a
    local writer may continue to use its historical direct file writes, yet it
    cannot overlap an importer transaction.
    """
    professor_dir = professor_dir.expanduser().resolve()
    token = token.strip()
    if not token:
        raise ValueError("local lease token is required")
    if ttl_seconds < 60:
        raise ValueError("local lease ttl must be at least 60 seconds")
    with _professor_lock(professor_dir):
        current = _active_local_lease_unlocked(professor_dir)
        if current and current.get("token") != token:
            raise ValueError("stage2_writer_busy")
        now = time.time()
        payload = {
            "schema": 1,
            "token": token,
            "acquired_at": current.get("acquired_at", now) if current else now,
            "expires_at": now + ttl_seconds,
        }
        _impl._atomic_json(_local_lease_path(professor_dir), payload)
        return {"status": "acquired", "reason_code": None, "token": token}


def release_local_lease(professor_dir: Path, token: str) -> dict[str, Any]:
    professor_dir = professor_dir.expanduser().resolve()
    token = token.strip()
    if not token:
        raise ValueError("local lease token is required")
    with _professor_lock(professor_dir):
        current = _active_local_lease_unlocked(professor_dir)
        if current is None:
            return {"status": "released", "reason_code": None, "released": False}
        if current.get("token") != token:
            raise ValueError("stage2_lease_token_mismatch")
        _local_lease_path(professor_dir).unlink(missing_ok=True)
        return {"status": "released", "reason_code": None, "released": True}


def _normalized_excerpt(value: str) -> str:
    return _SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value).strip())


def _bind_ocr_selections(
    selections_path: Path,
    candidates: list[dict[str, Any]],
    required_pages: list[int],
) -> dict[str, Any]:
    """Resolve external page+excerpt selections to exact post-OCR candidates.

    The external executor never supplies a candidate id. It supplies a page and
    a verbatim excerpt from the sentence it selected. After local `merge-ocr`,
    exactly one candidate on that page must contain the normalized excerpt. The
    importer then writes the complete exact candidate quote for the existing
    `future_work.py validate/finalize` contract.
    """
    payload = _impl._load_json(selections_path)
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("external_future_work_invalid")
    required = {int(page) for page in required_pages}
    canonical: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("external_future_work_invalid")
        if set(raw) != {"page", "quote_excerpt", "translation_zh", "source"}:
            raise ValueError("external_future_work_invalid")
        page = raw.get("page")
        excerpt = raw.get("quote_excerpt")
        translation = raw.get("translation_zh")
        source = raw.get("source")
        if (
            not isinstance(page, int)
            or isinstance(page, bool)
            or page not in required
            or not isinstance(excerpt, str)
            or not _normalized_excerpt(excerpt)
            or not isinstance(translation, str)
            or not translation.strip()
            or not isinstance(source, str)
            or not source.strip()
        ):
            raise ValueError("external_future_work_invalid")
        needle = _normalized_excerpt(excerpt)
        matches = []
        for candidate in candidates:
            if not isinstance(candidate, dict) or candidate.get("page") != page:
                continue
            quote = candidate.get("quote")
            if isinstance(quote, str) and needle in _normalized_excerpt(quote):
                matches.append(candidate)
        if len(matches) != 1:
            raise ValueError("external_future_work_invalid")
        candidate = matches[0]
        canonical.append({
            "quote": str(candidate["quote"]),
            "translation_zh": translation.strip(),
            "source": source.strip(),
            "page": page,
        })
    return {"items": canonical}


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
        prepared, candidates, fw = _impl._bundle_future_paths(bundle_root, job)
    except (OSError, ValueError):
        raise ValueError("external_future_work_invalid")

    working_prepared = prepared
    prepared_payload = _impl._load_json(prepared)
    required_pages = list(prepared_payload.get("ocr_required_pages") or [])
    selection_contract = fw.get("selection_contract")
    if required_pages:
        if selection_contract != "ocr-excerpt-v1":
            raise ValueError("external_future_work_invalid")
        ocr = source_dir / "future_work_ocr.json"
        selections = source_dir / "future_work_selections.json"
        if not ocr.is_file() or not selections.is_file():
            raise ValueError("external_result_incomplete")
        proc = _impl._run_future_work(
            args.future_work_script,
            "merge-ocr", "--prepared", str(prepared), "--ocr", str(ocr),
        )
        if proc.returncode != 0:
            raise ValueError("external_future_work_invalid")
        try:
            merged_payload = json.loads(proc.stdout.splitlines()[-1])
        except (IndexError, json.JSONDecodeError) as error:
            raise ValueError("external_future_work_invalid") from error
        merged_candidates = merged_payload.get("candidates")
        if not isinstance(merged_candidates, list):
            raise ValueError("external_future_work_invalid")
        working_prepared = staged_dir / "merged_prepare.json"
        candidates = staged_dir / "merged_candidates.json"
        _impl._atomic_json(working_prepared, merged_payload)
        _impl._atomic_json(candidates, {"candidates": merged_candidates})
        items = staged_dir / "future_work_items.json"
        try:
            canonical = _bind_ocr_selections(selections, merged_candidates, required_pages)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise ValueError("external_future_work_invalid") from error
        _impl._atomic_json(items, canonical)
    else:
        if selection_contract != "exact-items-v1":
            raise ValueError("external_future_work_invalid")
        items = source_dir / "future_work_items.json"
        if not items.is_file():
            raise ValueError("external_result_incomplete")

    proc = _impl._run_future_work(
        args.future_work_script,
        "validate", "--items", str(items), "--candidates", str(candidates),
    )
    if proc.returncode != 0:
        raise ValueError("external_future_work_invalid")
    prep_payload = _impl._load_json(working_prepared)
    proc = _impl._run_future_work(
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
    sidecar = _impl._load_json(staged_sidecar)
    if sidecar.get("status") != "ok" or sidecar.get("analysis") != analysis_target.name:
        raise ValueError("external_future_work_invalid")
    return staged_sidecar


def _instructions() -> str:
    return """# Stage 2 ChatGPT handoff

This ZIP contains only the exact Stage-2 per-paper analysis jobs selected by the local workflow.

For each `manifest.json.jobs[]` entry:
1. Analyze only the bundled `input_path`; do not use Zotero/MCP or invent missing local context.
2. Preserve `job_id`, `item_key`, `input_sha256`, direction IDs, and target identity exactly.
3. Write the ordinary paper-analysis Markdown template to `results/<safe-job>/analysis.md`, where `<safe-job>` is the deterministic safe form of that exact `job_id`; do not add or override a `result_dir` field in the result row.
4. For every PDF job with `expected.future_work=true`, follow `future_work.selection_contract` exactly:
   - `exact-items-v1`: return `future_work_items.json` selected/translated only from the bundled exact candidates. `id` may be omitted; the local helper derives/verifies it.
   - `ocr-excerpt-v1`: OCR every page in `future_work.ocr_required_pages` into `future_work_ocr.json` as `{\"pages\":{\"N\":\"text\"}}`. Do NOT guess candidate ids and do NOT precompute `future_work_items.json`. Instead return `future_work_selections.json` as `{\"items\":[{\"page\":N,\"quote_excerpt\":\"a verbatim distinctive excerpt from the selected OCR sentence\",\"translation_zh\":\"...\",\"source\":\"...\"}]}`. The local importer runs `merge-ocr`, uniquely binds each page+excerpt to the exact regenerated candidate, then runs `validate` and `finalize`.
5. Bind completed rows in `result_manifest.json` with schema/kind/handoff/source/job/item/input hash and `status=ok|partial|error`.

PDF fulltext jobs are not complete without their future-work payload. OCR-only and abstract-only jobs do not have a PDF-grounded future-work contract: any external Future Work prose in their Markdown is discarded locally and cannot become a gap source. Do not return `_index.json`, `套磁候选输入.json`, or a ready-made `.future_work.json` as authoritative state. The local importer independently validates/finalizes PDF future-work evidence and installs accepted results into the ordinary Stage-2 artifacts.
"""


def _install_job(
    professor_dir: Path,
    manifest: dict[str, Any],
    job: dict[str, Any],
    staged_analysis: Path,
    staged_sidecar: Path | None,
) -> tuple[Path, Path | None]:
    # The legacy installer already does final stale checks, a fresh whole-index
    # read/merge, and rollback-on-error. The OS lock closes importer/importer
    # TOCTOU, while the local-writer lease closes importer/legacy-writer races.
    with _professor_lock(professor_dir):
        if _active_local_lease_unlocked(professor_dir) is not None:
            raise ValueError("stage2_writer_busy")
        return _ORIG_INSTALL_JOB(
            professor_dir, manifest, job, staged_analysis, staged_sidecar
        )


def build_bundle(args: Any) -> dict[str, Any]:
    # Serialize baseline capture + latest-handoff replacement with imports and
    # reject a second Stage-2 planner while a local execution lease is active.
    professor_dir = args.professor_dir.expanduser().resolve()
    with _professor_lock(professor_dir):
        if _active_local_lease_unlocked(professor_dir) is not None:
            raise ValueError("stage2_writer_busy")
        return _ORIG_BUILD_BUNDLE(args)


def _sync_runtime_hooks() -> None:
    """Keep the public module's supported monkeypatch/test hooks effective."""
    hook = globals().get("_run_future_work")
    if callable(hook):
        _impl._run_future_work = hook


def import_result(args: Any) -> dict[str, Any]:
    _sync_runtime_hooks()
    professor_dir = args.professor_dir.expanduser().resolve()
    with _professor_lock(professor_dir):
        if _active_local_lease_unlocked(professor_dir) is not None:
            return {
                "status": "needs_external_result",
                "reason_code": "stage2_writer_busy",
                "imported": [],
                "missing": [],
            }
    try:
        output = _ORIG_IMPORT_RESULT(args)
    except ValueError as error:
        if "external_result_hash_mismatch" in str(error):
            return {
                "status": "needs_external_result",
                "reason_code": "external_result_hash_mismatch",
                "imported": [],
                "missing": [],
            }
        raise
    # A local writer can acquire its lease after the pre-check but before one
    # of the per-job install transactions. The hardened installer blocks that
    # write; remap the legacy catch-all stale code to the precise busy reason.
    if isinstance(output, dict) and output.get("reason_code") == "handoff_stale":
        with _professor_lock(professor_dir):
            if _active_local_lease_unlocked(professor_dir) is not None:
                output = dict(output)
                output["reason_code"] = "stage2_writer_busy"
                invalid = output.get("invalid")
                if isinstance(invalid, list):
                    output["invalid"] = [
                        ({**row, "reason_code": "stage2_writer_busy"}
                         if isinstance(row, dict) and row.get("reason_code") == "handoff_stale"
                         else row)
                        for row in invalid
                    ]
    return output


def _lease_cli(command: str) -> int:
    parser = argparse.ArgumentParser(prog=f"{Path(sys.argv[0]).name} {command}")
    parser.add_argument("--professor-dir", required=True, type=Path)
    parser.add_argument("--token", required=True)
    if command == "local-lease-acquire":
        parser.add_argument("--ttl-seconds", type=int, default=_LOCAL_LEASE_TTL_SECONDS)
    args = parser.parse_args(sys.argv[2:])
    try:
        if command == "local-lease-acquire":
            output = acquire_local_lease(
                args.professor_dir, args.token, ttl_seconds=args.ttl_seconds
            )
        else:
            output = release_local_lease(args.professor_dir, args.token)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        message = str(error)
        known = ("stage2_writer_busy", "stage2_lease_token_mismatch")
        reason = next((code for code in known if code in message), "invalid_handoff_input")
        print(json.dumps(
            {"status": "error", "reason_code": reason, "error": message[:300]},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ))
        return 2
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


# Patch the implementation module globals because its existing functions resolve
# helpers through their own module namespace at call time.
_impl._build_manifest = _build_manifest
_impl._validate_manifest = _validate_manifest
_impl._verify_bundled_input = _verify_bundled_input
_impl._finalize_future_work = _finalize_future_work
_impl._instructions = _instructions
_impl._install_job = _install_job
_impl.build_bundle = build_bundle
_impl.import_result = import_result

# Re-export hardened replacements for callers/tests importing this entrypoint.
globals().update({
    "_build_manifest": _build_manifest,
    "_verify_manifest_integrity": _verify_manifest_integrity,
    "_validate_manifest": _validate_manifest,
    "_verify_bundled_input": _verify_bundled_input,
    "_professor_lock": _professor_lock,
    "_active_local_lease_unlocked": _active_local_lease_unlocked,
    "acquire_local_lease": acquire_local_lease,
    "release_local_lease": release_local_lease,
    "_bind_ocr_selections": _bind_ocr_selections,
    "_finalize_future_work": _finalize_future_work,
    "_instructions": _instructions,
    "_install_job": _install_job,
    "build_bundle": build_bundle,
    "import_result": import_result,
})


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"local-lease-acquire", "local-lease-release"}:
        return _lease_cli(sys.argv[1])
    return _impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
