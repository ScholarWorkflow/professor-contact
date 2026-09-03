#!/usr/bin/env python3
"""Hardened public entrypoint for deterministic Stage-2 ChatGPT handoff.

The transport implementation lives in `_stage2_chatgpt_handoff_impl.py`. This
entrypoint owns the two integrity/concurrency invariants that must wrap every
build/import path:

1. manifest/job/source IDs are recomputed from the complete canonical manifest;
2. final artifact/index installation is serialized by a professor-scoped lock.
"""

from __future__ import annotations

import importlib.util
import json
import os
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

_ORIG_BUILD_MANIFEST = _impl._build_manifest
_ORIG_VALIDATE_MANIFEST = _impl._validate_manifest
_ORIG_VERIFY_BUNDLED_INPUT = _impl._verify_bundled_input
_ORIG_INSTALL_JOB = _impl._install_job
_ORIG_BUILD_BUNDLE = _impl.build_bundle
_ORIG_IMPORT_RESULT = _impl.import_result


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
            if (
                future_work.get("prepare_path") != prepare_path
                or future_work.get("candidates_path") != candidates_path
                or not _is_sha256(future_work.get("prepare_sha256"))
                or not _is_sha256(future_work.get("candidates_sha256"))
                or not isinstance(future_work.get("ocr_required_pages"), list)
            ):
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
            prepare_path, candidates_path = _future_relpaths(job["item_key"])
            entry["future_work"] = {
                "prepare_path": prepare_path,
                "candidates_path": candidates_path,
                "prepare_sha256": job["future_work_prepare_sha256"],
                "candidates_sha256": job["future_work_candidates_sha256"],
                "ocr_required_pages": list(prepare_payload.get("ocr_required_pages") or []),
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
    """Professor-scoped OS lock for the final Stage-2 artifact/index transaction."""
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


def _install_job(
    professor_dir: Path,
    manifest: dict[str, Any],
    job: dict[str, Any],
    staged_analysis: Path,
    staged_sidecar: Path | None,
) -> tuple[Path, Path | None]:
    # The legacy installer already does two stale checks, a fresh _index.json
    # read/merge, and rollback-on-error. Holding this lock around the entire
    # operation closes the check/read/write TOCTOU window between importers.
    with _professor_lock(professor_dir):
        return _ORIG_INSTALL_JOB(
            professor_dir, manifest, job, staged_analysis, staged_sidecar
        )


def build_bundle(args: Any) -> dict[str, Any]:
    # Serialize baseline capture + latest-handoff replacement with imports.
    professor_dir = args.professor_dir.expanduser().resolve()
    with _professor_lock(professor_dir):
        return _ORIG_BUILD_BUNDLE(args)


def _sync_runtime_hooks() -> None:
    """Keep the public module's supported monkeypatch/test hooks effective."""
    hook = globals().get("_run_future_work")
    if callable(hook):
        _impl._run_future_work = hook


def import_result(args: Any) -> dict[str, Any]:
    _sync_runtime_hooks()
    try:
        return _ORIG_IMPORT_RESULT(args)
    except ValueError as error:
        if "external_result_hash_mismatch" in str(error):
            return {
                "status": "needs_external_result",
                "reason_code": "external_result_hash_mismatch",
                "imported": [],
                "missing": [],
            }
        raise


# Patch the implementation module globals because its existing functions resolve
# helpers through their own module namespace at call time.
_impl._build_manifest = _build_manifest
_impl._validate_manifest = _validate_manifest
_impl._verify_bundled_input = _verify_bundled_input
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
    "_install_job": _install_job,
    "build_bundle": build_bundle,
    "import_result": import_result,
})

main = _impl.main


if __name__ == "__main__":
    raise SystemExit(main())
