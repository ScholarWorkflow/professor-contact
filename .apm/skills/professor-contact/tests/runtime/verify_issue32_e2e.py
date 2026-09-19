#!/usr/bin/env python3
"""Read-only checkpoints for issue #32's Stage 0–5 runtime evaluation.

The verifier observes product state and adapter-provided structured evidence.
It never repairs product files.  The sole intentional write is the
``make-stage4-selection`` helper, which models an explicit user selection and
writes only the requested output path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

MANIFEST_NAME = "fixture-manifest.json"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
ITEM_KEYS = ("AAAA1111", "BBBB2222")
PROGRAM_STAGE_OUTPUTS = (
    Path("教授研究/套磁目标.json"), Path("教授研究/套磁阶段1候选.json"),
)
PROFESSOR_STAGE_OUTPUTS = (
    Path("套磁候选输入.json"), Path("套磁候选状态.json"),
    Path("套磁选择.json"), Path("邮件输入.json"),
)
INPUT_PACK_KIND = "professor-contact-stage2-input"
CANDIDATE_STATE_KIND = "professor-contact-stage3-state"
DIRECTION_IDENTITY_VERSION = "direction-id-v1"
STAGE3_GENERATOR_CONTRACT_VERSION = "stage3-ideas-v2"
INSTALL_REQUIRED_FILES = (
    ".agents/skills/professor-contact/SKILL.md",
    ".agents/skills/professor-contact/scripts/contact_state.py",
    ".codex/agents/professor-contact.toml",
    ".codex/agents/professor-contact-idea-generator.toml",
    ".codex/agents/professor-contact-style-validator.toml",
    ".agents/skills/professor-contact/tests/runtime/prepare_issue55_stage3_fixture.py",
    ".agents/skills/professor-contact/tests/runtime/build_issue55_eval_request.py",
    ".agents/skills/professor-contact/tests/runtime/verify_issue32_e2e.py",
    ".agents/skills/professor-contact/tests/runtime/prompts/issue55-stage3-routing.txt",
    # PC57-R2 reuses the #53 Stage-4 request builder and prompt, so a clean
    # consumer must carry them before either runtime case may start.
    ".agents/skills/professor-contact/tests/runtime/build_issue53_eval_request.py",
    ".agents/skills/professor-contact/tests/runtime/prompts/issue53-stage4-missing-selection.txt",
    ".agents/skills/professor-contact/tests/runtime/prepare_issue57_stage2_fixture.py",
    ".agents/skills/professor-contact/tests/runtime/build_issue57_stage2_eval_request.py",
    ".agents/skills/professor-contact/tests/runtime/prepare_issue57_stage4_fixture.py",
    ".agents/skills/professor-contact/tests/runtime/prompts/issue57-stage2-routing.txt",
)
STAGE4_PROGRAM_OUTPUTS = {
    "套磁选择.json": Path("教授研究/套磁选择.json"),
    "邮件输入.json": Path("教授研究/邮件输入.json"),
}
STAGE3_SNAPSHOT_OUTPUTS = {
    "套磁候选状态.json": Path("教授研究/X分野/Example Professor/套磁候选状态.json"),
    "套磁想法候选.md": Path("教授研究/X分野/Example Professor/套磁想法候选.md"),
    "套磁想法候选总览.md": Path("教授研究/套磁想法候选总览.md"),
    **STAGE4_PROGRAM_OUTPUTS,
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _result(status: str, checks: list[dict[str, Any]], **observed: Any) -> dict[str, Any]:
    return {"status": status, "checks": checks, "observed": observed}


def _check(checks: list[dict[str, Any]], name: str, ok: bool, detail: Any = None) -> None:
    row: dict[str, Any] = {"name": name, "status": "pass" if ok else "fail"}
    if detail is not None:
        row["detail"] = detail
    checks.append(row)


def _finish(checks: list[dict[str, Any]], **observed: Any) -> dict[str, Any]:
    return _result("pass" if all(row["status"] == "pass" for row in checks) else "fail",
                   checks, **observed)


def _manifest(root: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    path = root / MANIFEST_NAME
    try:
        manifest = _load(path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "fixture_manifest_readable", False, str(exc))
        return None, checks
    _check(checks, "fixture_builder", manifest.get("builder") == "tests/runtime/build_issue32_e2e_fixture.py",
           manifest.get("builder"))
    _check(checks, "fixture_mode", manifest.get("fixture_mode") == "initial_raw_inputs",
           manifest.get("fixture_mode"))
    _check(checks, "program_root_matches", Path(manifest.get("program_root", "")).resolve() == root.resolve())
    _check(checks, "direction_ids", manifest.get("direction_ids") == [DIRECTION_ID], manifest.get("direction_ids"))
    _check(checks, "item_keys", manifest.get("item_keys") == ["AAAA1111", "BBBB2222"], manifest.get("item_keys"))
    return manifest, checks


def _professor_dir(root: Path) -> Path:
    return root / "教授研究" / "X分野" / PROFESSOR


def _direction(root: Path) -> dict[str, Any] | None:
    path = _professor_dir(root) / "方向预筛.json"
    try:
        payload = _load(path)
    except (OSError, json.JSONDecodeError):
        return None
    return next((row for row in payload.get("directions", [])
                 if isinstance(row, dict) and row.get("direction_id") == DIRECTION_ID), None)


def _json_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*.json") if path.is_file()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_yaml(path: Path) -> tuple[Any | None, str | None]:
    """Parse YAML through yq, the repository's structured YAML tool."""
    try:
        completed = subprocess.run(
            ["yq", "-o=json", ".", str(path)],
            capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        return None, str(exc)
    if completed.returncode != 0:
        return None, completed.stderr.strip() or f"yq exited {completed.returncode}"
    try:
        return json.loads(completed.stdout), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def _resolved_professor_contact_commit(consumer: Path) -> tuple[str | None, str]:
    matches: list[tuple[Path, Any]] = []
    parse_errors: list[str] = []
    for path in (consumer / "apm.lock.yaml", consumer / "apm.lock.yml"):
        if not path.is_file():
            continue
        payload, error = _load_yaml(path)
        if error:
            parse_errors.append(f"{path.name}: {error}")
            continue
        dependencies = payload.get("dependencies") if isinstance(payload, dict) else None
        if not isinstance(dependencies, list):
            continue
        for dependency in dependencies:
            if isinstance(dependency, dict) and dependency.get("name") == "professor-contact":
                matches.append((path, dependency.get("resolved_commit")))
    if parse_errors:
        return None, "; ".join(parse_errors)
    if len(matches) != 1:
        return None, f"expected one professor-contact dependency, found {len(matches)}"
    path, commit = matches[0]
    if not isinstance(commit, str) or not commit.strip():
        return None, f"{path.name}: professor-contact.resolved_commit is missing"
    return commit, f"{path.name}: professor-contact.resolved_commit"


def _has_structured_key(value: Any, keys: set[str]) -> bool:
    if isinstance(value, dict):
        if any(key in value for key in keys):
            return True
        return any(_has_structured_key(child, keys) for child in value.values())
    if isinstance(value, list):
        return any(_has_structured_key(child, keys) for child in value)
    return False


def _structured_values(value: Any, keys: set[str]) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys:
                found.append(child)
            found.extend(_structured_values(child, keys))
    elif isinstance(value, list):
        for child in value:
            found.extend(_structured_values(child, keys))
    return found


def _contains_direction(value: Any) -> bool:
    if isinstance(value, dict):
        for key in ("direction_id", "direction_ids", "selected_direction_ids", "collection_key"):
            child = value.get(key)
            if child == DIRECTION_ID or (isinstance(child, list) and DIRECTION_ID in child):
                return True
        return any(_contains_direction(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_direction(child) for child in value)
    return False


def _checkpoint_install(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    consumer = Path(args.consumer_root or "").resolve()
    _check(checks, "consumer_root_exists", bool(args.consumer_root) and consumer.is_dir(), str(consumer))
    expected = [consumer / relative for relative in INSTALL_REQUIRED_FILES]
    for path in expected:
        _check(checks, f"installed:{path.relative_to(consumer)}", path.is_file(), str(path))
        _check(checks, f"contained:{path.relative_to(consumer)}",
               path.resolve().is_relative_to(consumer), str(path.resolve()))
    if args.producer_sha:
        resolved_commit, detail = _resolved_professor_contact_commit(consumer)
        _check(checks, "producer_sha_pinned", resolved_commit == args.producer_sha,
               {"expected": args.producer_sha, "observed": resolved_commit, "source": detail})
    return _finish(checks, consumer_root=str(consumer))


def _checkpoint_initial(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    manifest, checks = _manifest(root)
    if manifest is None:
        return _finish(checks)
    builder_path = Path(__file__).with_name("build_issue32_e2e_fixture.py")
    _check(checks, "builder_hash", builder_path.is_file()
           and _sha256(builder_path) == manifest.get("builder_sha256"))
    protected = manifest.get("protected_files", {})
    protected_ok = isinstance(protected, dict) and all(
        (root / relative).is_file() and _sha256(root / relative) == expected
        for relative, expected in protected.items())
    _check(checks, "protected_file_hashes", protected_ok)
    profile_root = Path(manifest.get("profile_root", ""))
    profile_hashes = manifest.get("profile_files", {})
    profile_ok = profile_root.is_dir() and isinstance(profile_hashes, dict) and all(
        (profile_root / relative).is_file() and _sha256(profile_root / relative) == expected
        for relative, expected in profile_hashes.items())
    _check(checks, "profile_file_hashes", profile_ok)
    prof = _professor_dir(root)
    _check(checks, "preview_exists", (prof / "方向预筛.json").is_file())
    direction = _direction(root)
    _check(checks, "legal_direction_preview", direction is not None)
    try:
        papers = _load(prof / "papers.json").get("papers", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        papers = []
    by_key = {row.get("item_key"): row for row in papers if isinstance(row, dict)}
    _check(checks, "catalog_keys", set(by_key) == {"AAAA1111", "BBBB2222"}, list(by_key))
    _check(checks, "ready_and_missing", by_key.get("AAAA1111", {}).get("pdf_status") == "downloaded"
           and by_key.get("BBBB2222", {}).get("pdf_status") == "missing", by_key)
    pdf = prof / "论文分析/AAAA1111.pdf"
    pdf_bytes = pdf.read_bytes() if pdf.is_file() else b""
    _check(checks, "deterministic_text_pdf", pdf_bytes.startswith(b"%PDF-1.4")
           and b"/Type /Page" in pdf_bytes and b"/Contents" in pdf_bytes and b"%%EOF" in pdf_bytes)
    _check(checks, "profile_inputs", all((Path(manifest["profile_root"]) / name).is_file() for name in
                                          ("套磁邮件/套磁信息.md", "套磁邮件/套磁模板.md", "套磁邮件/套磁跟进模板.md")))
    _check(checks, "legal_application_inputs", (root / "info.json").is_file()
           and (root / "boshu_analysis.json").is_file())
    _check(checks, "raw_contact_prerequisite", (root / "教授研究/contact-evidence-fixture-input.json").is_file()
           and not (root / "教授研究/_联系方式证据.json").exists())
    for relative in PROGRAM_STAGE_OUTPUTS:
        _check(checks, f"product_output_absent:{relative.as_posix()}", not (root / relative).exists())
    for relative in PROFESSOR_STAGE_OUTPUTS:
        _check(checks, f"product_output_absent:{relative.as_posix()}",
               not (_professor_dir(root) / relative).exists())
    _check(checks, "no_prebuilt_analysis", not list((prof / "论文分析").glob("*.md"))
           and not list((prof / "论文分析").glob("*.future_work.json")))
    return _finish(checks, professor=PROFESSOR, direction_id=DIRECTION_ID,
                   item_keys=sorted(by_key), pdf=str(pdf))


def _response(args: argparse.Namespace) -> Any:
    if not args.eval_response:
        return None
    return _load(Path(args.eval_response))


def _checkpoint_stage0_needs_input(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    response = None
    try:
        response = _response(args)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "eval_response_readable", False, str(exc))
    _check(checks, "target_not_written", not (root / PROGRAM_STAGE_OUTPUTS[0]).exists())
    _check(checks, "selection_request_structured", isinstance(response, (dict, list))
           and _has_structured_key(response, {"selection_request", "pending_selection", "needs_input"}))
    _check(checks, "selection_direction", _contains_direction(response))
    return _finish(checks)


def _checkpoint_stage0_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    path = root / "教授研究/套磁目标.json"
    try:
        payload = _load(path)
        targets = payload.get("targets", [])
        target = next(row for row in targets if row.get("professor") == PROFESSOR)
    except (OSError, json.JSONDecodeError, StopIteration, AttributeError) as exc:
        _check(checks, "target_readable", False, str(exc))
        return _finish(checks)
    selected = target.get("selected_direction_ids", [])
    _check(checks, "selected_direction", selected == [DIRECTION_ID], selected)
    _check(checks, "target_note", any(row.get("user_note") ==
           "I want to study adaptive and nonlinear extensions of this processing framework."
           for row in target.get("directions", []) if isinstance(row, dict)))
    _check(checks, "no_legacy_stage0_output", not (root / "教授研究/套磁候选.md").exists())
    return _finish(checks, target_file=str(path))


def _checkpoint_stage1_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    prof = _professor_dir(root)
    snapshot_path = root / "教授研究/套磁阶段1候选.json"
    try:
        snapshot = _load(snapshot_path)
        papers = _load(prof / "papers.json").get("papers", [])
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        _check(checks, "stage1_files_readable", False, str(exc))
        return _finish(checks)
    _check(checks, "snapshot_schema", snapshot.get("schema_version") == 1
           and snapshot.get("kind") == "professor-contact-stage1")
    professor_row = next((row for row in snapshot.get("professors", [])
                          if isinstance(row, dict) and row.get("professor") == PROFESSOR), None)
    _check(checks, "snapshot_professor", professor_row is not None)
    direction = next((row for row in (professor_row or {}).get("directions", [])
                      if isinstance(row, dict) and row.get("direction_id") == DIRECTION_ID), None)
    _check(checks, "snapshot_direction", direction is not None)
    if direction:
        _check(checks, "snapshot_members", set(direction.get("candidate_keys", [])) == set(ITEM_KEYS), direction.get("candidate_keys"))
        readiness = direction.get("pdf_readiness", {})
        _check(checks, "pdf_readiness", set(readiness.get("usable_item_keys", [])) == set(ITEM_KEYS)
               and readiness.get("missing_item_keys", []) == [], readiness)
    by_key = {row.get("item_key"): row for row in papers if isinstance(row, dict)}
    _check(checks, "collector_completed", by_key.get("BBBB2222", {}).get("pdf_status") == "downloaded")
    if args.eval_response:
        try:
            response = _response(args)
            payloads = _structured_values(response, {"collector_payload", "collector_request", "tool_payload"})
            if isinstance(response, dict):
                payloads.append(response)
            exact = any(isinstance(row, dict) and row.get("folder_path") and row.get("pdf_only") is True
                        and row.get("item_keys") == ["BBBB2222"] and "professors" not in row
                        for row in payloads)
            _check(checks, "collector_payload_contract", exact)
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, "eval_response_readable", False, str(exc))
    return _finish(checks, snapshot_file=str(snapshot_path), papers=sorted(by_key))


def _checkpoint_stage2_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    prof = _professor_dir(root)
    try:
        pack = _load(prof / "套磁候选输入.json")
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "candidate_input_readable", False, str(exc))
        return _finish(checks)
    if not isinstance(pack, dict):
        _check(checks, "candidate_input_object", False, type(pack).__name__)
        return _finish(checks)
    _check(checks, "candidate_input_schema", pack.get("schema") == 2
           and pack.get("kind") == INPUT_PACK_KIND
           and pack.get("identity_version") == DIRECTION_IDENTITY_VERSION
           and pack.get("managed_by") == "contact_state")
    _check(checks, "candidate_input_runner_contract",
           pack.get("professor") == PROFESSOR
           and isinstance(pack.get("professor_dir"), str)
           and isinstance(pack.get("papers"), dict))
    directions = pack.get("directions")
    direction = next((row for row in directions if isinstance(row, dict)
                      and row.get("direction_id") == DIRECTION_ID), None) \
        if isinstance(directions, list) else None
    _check(checks, "candidate_input_direction", direction is not None)
    _check(checks, "candidate_input_fingerprint",
           isinstance(direction, dict)
           and isinstance(direction.get("input_fingerprint"), str)
           and bool(direction.get("input_fingerprint"))
           and isinstance(direction.get("supporting_item_keys"), list))
    _check(checks, "analysis_for_ready_paper", bool(list((prof / "论文分析").glob("AAAA1111*.md"))))
    _check(checks, "future_work_sidecar", bool(list((prof / "论文分析").glob("AAAA1111*.future_work.json"))))
    return _finish(checks, candidate_input=str(prof / "套磁候选输入.json"))


def _checkpoint_stage3_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    path = _professor_dir(root) / "套磁候选状态.json"
    try:
        state = _load(path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "candidate_state_readable", False, str(exc))
        return _finish(checks)
    if not isinstance(state, dict):
        _check(checks, "candidate_state_object", False, type(state).__name__)
        return _finish(checks)
    candidates = _candidate_rows(state)
    _check(checks, "state_schema", state.get("schema") == 2
           and state.get("kind") == CANDIDATE_STATE_KIND
           and state.get("identity_version") == DIRECTION_IDENTITY_VERSION
           and state.get("generator_contract_version") == STAGE3_GENERATOR_CONTRACT_VERSION)
    _check(checks, "candidate_count", 3 <= len(candidates) <= 5, len(candidates))
    _check(checks, "candidate_ids_stable", all(
        isinstance(row, dict) and isinstance(row.get("id"), str) and row.get("id")
        and row.get("direction_ids") == [DIRECTION_ID] for row in candidates))
    directions = state.get("directions")
    direction = next((row for row in directions if isinstance(row, dict)
                      and row.get("direction_id") == DIRECTION_ID), None) \
        if isinstance(directions, list) else None
    _check(checks, "direction_present", direction is not None)
    validator = state.get("validator")
    results = validator.get("results") if isinstance(validator, dict) else None
    result = results.get(DIRECTION_ID) if isinstance(results, dict) else None
    _check(checks, "validation_present", _valid_validation_record(result), result)
    return _finish(checks, candidate_state=str(path), candidate_ids=[row.get("id") for row in candidates if isinstance(row, dict)])


def _stage3_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for name, relative in STAGE3_SNAPSHOT_OUTPUTS.items():
        path = root / relative
        exists = path.exists()
        artifacts[name] = {
            "exists": exists,
            "sha256": _sha256(path) if path.is_file() else None,
        }
    return artifacts


def _checkpoint_stage3_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    artifacts = _stage3_artifacts(root)
    checks: list[dict[str, Any]] = []
    _check(checks, "program_root_exists", root.is_dir(), str(root))
    for name, artifact in artifacts.items():
        _check(checks, f"snapshot:{name}", set(artifact) == {"exists", "sha256"}, artifact)
        _check(
            checks,
            f"snapshot_hash_shape:{name}",
            (not artifact["exists"] and artifact["sha256"] is None)
            or (artifact["exists"] and isinstance(artifact["sha256"], str)
                and len(artifact["sha256"]) == 64),
            artifact,
        )
    return {
        "status": "pass" if all(row["status"] == "pass" for row in checks) else "fail",
        "checks": checks,
        "artifacts": artifacts,
    }


def _load_stage3_snapshot(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load(path)
    if isinstance(payload, dict) and isinstance(payload.get("artifacts"), dict):
        payload = payload["artifacts"]
    if not isinstance(payload, dict):
        raise ValueError("stage3 snapshot must be an object")
    expected = set(STAGE3_SNAPSHOT_OUTPUTS)
    if set(payload) != expected:
        raise ValueError(f"stage3 snapshot artifact names differ: {set(payload)!r}")
    result: dict[str, dict[str, Any]] = {}
    for name in expected:
        row = payload[name]
        if not isinstance(row, dict) or set(row) != {"exists", "sha256"}:
            raise ValueError(f"invalid stage3 snapshot row: {name}")
        if not isinstance(row["exists"], bool):
            raise ValueError(f"invalid exists flag: {name}")
        if row["exists"] and (not isinstance(row["sha256"], str)
                               or len(row["sha256"]) != 64):
            raise ValueError(f"missing sha256 for existing artifact: {name}")
        if not row["exists"] and row["sha256"] is not None:
            raise ValueError(f"absent artifact has a sha256: {name}")
        result[name] = row
    return result


def _valid_issue55_validation_record(value: Any) -> bool:
    """Validate the stricter terminal record for the fixed Stage-3 case."""
    return (_valid_validation_record(value)
            and isinstance(value, dict)
            and value.get("result") in {"pass", "fail_after_2_rounds"})


def _valid_validation_record(value: Any) -> bool:
    if not isinstance(value, dict) or value.get("result") not in (
            "pass", "fail_after_2_rounds", "skipped"):
        return False
    rounds = value.get("rounds")
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
        return False
    result = value["result"]
    if result == "pass" and rounds not in (1, 2):
        return False
    if result == "fail_after_2_rounds" and rounds != 2:
        return False
    if result == "skipped" and rounds > 2:
        return False
    return isinstance(value.get("issues"), list)


def _checkpoint_stage3_routing(args: argparse.Namespace) -> dict[str, Any]:
    """Verify PC55-R1's root routing and terminal Stage-3 product state.

    The adapter's formal relation is the only delegation evidence consumed
    here.  In particular, this checkpoint deliberately does not inspect child
    names, roles, prose, ordering, or completion claims.
    """
    checks: list[dict[str, Any]] = []
    root = Path(args.program_root).resolve()
    root_thread_id: str | None = None
    direct_children: set[str] = set()
    nested_formal_spawns: list[dict[str, Any]] = []

    def machine(status: str, classification: str) -> dict[str, Any]:
        return {
            "status": status,
            "classification": classification,
            "root_thread_id": root_thread_id,
            "root_direct_spawn_child_ids": sorted(direct_children),
            "nested_formal_spawns": nested_formal_spawns,
            "checks": checks,
        }

    pre_path = getattr(args, "pre_snapshot", None)
    post_path = getattr(args, "post_snapshot", None)
    if not pre_path or not post_path:
        _check(checks, "snapshots_supplied", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    try:
        pre = _load_stage3_snapshot(Path(pre_path))
        post = _load_stage3_snapshot(Path(post_path))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        _check(checks, "snapshots_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")

    expected_pre = {
        name: {"exists": False, "sha256": None}
        for name in STAGE3_SNAPSHOT_OUTPUTS
    }
    _check(checks, "pre_zero_write_snapshot", pre == expected_pre, pre)
    current = _stage3_artifacts(root)
    _check(checks, "post_matches_current", post == current,
           {"post": post, "current": current})
    if pre != expected_pre or post != current:
        return machine("invalid", "INVALID_TEST_EXECUTION")

    try:
        adapter = _load(Path(args.adapter_output)) if args.adapter_output else None
        response = _load(Path(args.eval_response)) if args.eval_response else None
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "evidence_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")
    if not isinstance(adapter, dict) or not isinstance(response, dict):
        _check(checks, "evidence_objects", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")

    output = response.get("output")
    root_thread_id = output.get("thread_id") if isinstance(output, dict) else None
    events = output.get("app_server_events") if isinstance(output, dict) else None
    _check(checks, "common_envelope_passed", response.get("passed") is True,
           response.get("passed"))
    _check(checks, "common_envelope_exit_code",
           isinstance(output, dict) and output.get("exit_code") == 0,
           output.get("exit_code") if isinstance(output, dict) else None)
    _check(checks, "common_envelope_completed",
           isinstance(output, dict) and output.get("termination_reason") == "completed",
           output.get("termination_reason") if isinstance(output, dict) else None)
    _check(checks, "raw_eval_surface",
           isinstance(root_thread_id, str) and bool(root_thread_id.strip())
           and isinstance(events, list),
           {"thread_id": root_thread_id, "events": type(events).__name__})
    if not all(row["status"] == "pass" for row in checks[-4:]):
        return machine("blocked", "BLOCKED_RUNTIME/PROVIDER")

    delegation = adapter.get("delegation")
    if not isinstance(delegation, dict):
        _check(checks, "adapter_delegation_object", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    if delegation.get("state") == "unobservable":
        _check(checks, "delegation_observable", False, delegation)
        return machine("blocked", "BLOCKED_OBSERVABILITY")
    _check(checks, "delegation_confirmed", delegation.get("state") == "confirmed",
           delegation.get("state"))
    basis = delegation.get("basis")
    _check(checks, "adapter_formal_basis",
           isinstance(basis, list) and "formal_spawn_relation" in basis, basis)
    if delegation.get("state") != "confirmed" or not isinstance(basis, list) \
            or "formal_spawn_relation" not in basis:
        return machine("invalid", "INVALID_TEST_EXECUTION")

    dispatch = adapter.get("dispatch")
    relations = dispatch.get("thread_relations") if isinstance(dispatch, dict) else None
    if not isinstance(relations, list):
        _check(checks, "adapter_relations", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")

    owners: dict[str, set[str]] = {}
    for relation in relations:
        if not isinstance(relation, dict) or relation.get("tool") != "spawnAgent":
            continue
        sender = relation.get("sender_thread_id")
        children = relation.get("receiver_thread_ids")
        if not isinstance(sender, str) or not sender or not isinstance(children, list):
            _check(checks, "adapter_relation_shape", False, relation)
            return machine("invalid", "INVALID_TEST_EXECUTION")
        for child in children:
            if not isinstance(child, str) or not child:
                _check(checks, "adapter_child_id_shape", False, relation)
                return machine("invalid", "INVALID_TEST_EXECUTION")
            owners.setdefault(child, set()).add(sender)
            if sender == root_thread_id:
                direct_children.add(child)
        if sender != root_thread_id:
            nested_formal_spawns.append({
                "sender_thread_id": sender,
                "receiver_thread_ids": list(children),
            })
    ownership_conflicts = {
        child: sorted(senders) for child, senders in owners.items() if len(senders) != 1
    }
    _check(checks, "formal_ownership", not ownership_conflicts, ownership_conflicts)
    if ownership_conflicts:
        return machine("invalid", "INVALID_TEST_EXECUTION")
    if not owners:
        _check(checks, "formal_spawn_relation_surface", False)
        return machine("blocked", "BLOCKED_OBSERVABILITY")
    _check(checks, "no_nested_formal_spawn", not nested_formal_spawns,
           nested_formal_spawns)
    if nested_formal_spawns:
        return machine("fail", "FAIL_PRODUCT")
    _check(checks, "root_direct_spawn_child_count", len(direct_children) >= 2,
           {"observed": len(direct_children), "required": 2})

    state_path = _professor_dir(root) / "套磁候选状态.json"
    try:
        state = _load(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "candidate_state_readable", False, str(exc))
        return machine("fail", "FAIL_PRODUCT")
    if not isinstance(state, dict):
        _check(checks, "candidate_state_object", False, type(state).__name__)
        return machine("fail", "FAIL_PRODUCT")
    _check(checks, "state_schema", state.get("schema") == 2
           and state.get("kind") == CANDIDATE_STATE_KIND
           and state.get("identity_version") == DIRECTION_IDENTITY_VERSION
           and state.get("generator_contract_version") == STAGE3_GENERATOR_CONTRACT_VERSION)
    directions = state.get("directions")
    direction_rows = [row for row in directions if isinstance(row, dict)
                      and row.get("direction_id") == DIRECTION_ID] \
        if isinstance(directions, list) else []
    direction = direction_rows[0] if len(direction_rows) == 1 else None
    _check(checks, "direction_row_unique", len(direction_rows) == 1,
           {"observed": len(direction_rows), "required": 1})
    candidates = direction.get("candidates") if isinstance(direction, dict) else None
    if not isinstance(candidates, list):
        candidates = []
    candidates = [row for row in candidates if isinstance(row, dict)]
    _check(checks, "candidate_count", 3 <= len(candidates) <= 5, len(candidates))
    _check(checks, "candidate_ids_stable", all(
        isinstance(row.get("id"), str) and bool(row.get("id"))
        and row.get("direction_ids") == [DIRECTION_ID]
        for row in candidates))
    _check(checks, "direction_present", direction is not None)
    validator = state.get("validator")
    results = validator.get("results") if isinstance(validator, dict) else None
    _check(checks, "validator_result_keys",
           isinstance(results, dict) and set(results) == {DIRECTION_ID},
           sorted(results) if isinstance(results, dict) else results)
    result = results.get(DIRECTION_ID) if isinstance(results, dict) else None
    _check(checks, "validation_present", _valid_issue55_validation_record(result), result)
    rounds = result.get("rounds") if isinstance(result, dict) else None
    expected_root_children = (
        2 * rounds
        if isinstance(rounds, int) and not isinstance(rounds, bool)
        else None
    )
    _check(
        checks,
        "root_direct_spawn_child_count_matches_rounds",
        expected_root_children is not None
        and len(direct_children) == expected_root_children,
        {
            "observed": len(direct_children),
            "rounds": rounds,
            "required": expected_root_children,
        },
    )

    stage4_current = {name: current[name] for name in STAGE4_PROGRAM_OUTPUTS}
    stage4_absent = all(not row["exists"] for row in stage4_current.values())
    _check(checks, "stage4_outputs_absent", stage4_absent, stage4_current)
    product_checks = [row for row in checks if row["name"] in {
        "state_schema", "direction_row_unique", "candidate_count",
        "candidate_ids_stable", "direction_present", "validator_result_keys",
        "validation_present", "root_direct_spawn_child_count",
        "root_direct_spawn_child_count_matches_rounds", "stage4_outputs_absent",
    }]
    if not stage4_absent or not all(row["status"] == "pass" for row in product_checks):
        return machine("fail", "FAIL_PRODUCT")
    return machine("pass", "PASS")


def _formal_spawn_relations(adapter: Any) -> tuple[list[dict[str, str]], list[Any]]:
    """Extract formal spawn edges from adapter@9's normalized relation graph.

    The pinned adapter@9 contract freezes exactly three formal-relation
    conditions: ``tool == "spawnAgent"``, a non-empty ``sender_thread_id``
    owner, and one or more concrete ``receiver_thread_ids``.
    ``dispatch.thread_relations[].status`` is only the raw ``item.status``
    projection and has no frozen enum, so it is never read here (diagnostics
    only) and a formal edge never requires child completion.
    ``sender_thread_id`` is the formal owner; ``parent_thread_id`` is
    app-server event attribution and is never read here.  Shape violations
    are returned separately so each checkpoint can classify them as invalid
    evidence.
    """
    edges: list[dict[str, str]] = []
    malformed: list[Any] = []
    dispatch = adapter.get("dispatch") if isinstance(adapter, dict) else None
    relations = dispatch.get("thread_relations") if isinstance(dispatch, dict) else None
    if not isinstance(relations, list):
        return edges, [relations]
    for relation in relations:
        if not isinstance(relation, dict) or relation.get("tool") != "spawnAgent":
            continue
        sender = relation.get("sender_thread_id")
        children = relation.get("receiver_thread_ids")
        if not isinstance(sender, str) or not sender.strip() \
                or not isinstance(children, list) or not children:
            malformed.append(relation)
            continue
        concrete: list[str] = []
        for child in children:
            if not isinstance(child, str) or not child.strip():
                malformed.append(relation)
                break
            concrete.append(child)
        if len(concrete) != len(children):
            continue
        for child in concrete:
            edges.append({"sender_thread_id": sender, "receiver_thread_id": child})
    return edges, malformed


def _expected_delegation_summary(edges: list[dict[str, str]]) -> dict[str, Any]:
    """adapter@9's frozen delegation summary, derived mechanically from the
    formal edges of the same response.

    The pinned parser builds the summary from every supported formal
    spawnAgent relation: ``child_thread_ids`` is the sorted distinct
    concrete receiver union, ``formal_child_count`` its size, and a
    confirmed summary carries ``basis=["formal_spawn_relation"]`` with
    ``reason_code=None`` while an unobservable graph carries the zeroed
    shape with ``reason_code="no_supported_formal_spawn_relation"``.  The
    #57 checkpoints compare the observed summary against this derivation
    field by field before trusting any of it.
    """
    children = sorted({edge["receiver_thread_id"] for edge in edges})
    if children:
        return {
            "state": "confirmed",
            "formal_child_count": len(children),
            "child_thread_ids": children,
            "basis": ["formal_spawn_relation"],
            "reason_code": None,
        }
    return {
        "state": "unobservable",
        "formal_child_count": 0,
        "child_thread_ids": [],
        "basis": [],
        "reason_code": "no_supported_formal_spawn_relation",
    }


def _ownership_index(edges: list[dict[str, str]]) -> tuple[dict[str, set[str]], dict[str, str]]:
    """Index formal edges by receiver owner; empty senders never own a child."""
    owners: dict[str, set[str]] = {}
    direct: dict[str, str] = {}
    for edge in edges:
        sender = edge["sender_thread_id"]
        child = edge["receiver_thread_id"]
        owners.setdefault(child, set()).add(sender)
        direct.setdefault(child, sender)
    return owners, direct


ADAPTER_FIXTURE_READY_STATUSES = (
    "FIXTURE_READY", "HARNESS_DISPATCH_UNCONFIRMED", "HARNESS_DISPATCH_MISMATCH",
)


def _adapter_prerequisite_block(
        adapter: Any, checks: list[dict[str, Any]]) -> tuple[str, str] | None:
    """adapter@9's fail-closed prerequisite, evaluated before any delegation
    or relation topology is interpreted.

    ``BLOCKED_DEPENDENCY`` (for example a null ``codex_version``) is a runtime
    dependency failure: blocked / NOT TESTED, never a producer FAIL and never
    INVALID_TEST_EXECUTION.  ``INVALID_EVIDENCE``, an unknown status, or a
    missing status is corrupted adapter evidence.  Returns the early-exit
    ``(status, classification)`` or ``None`` when the prerequisite passes.
    """
    fixture_status = adapter.get("fixture_status") if isinstance(adapter, dict) else None
    if fixture_status == "BLOCKED_DEPENDENCY":
        _check(checks, "adapter_prerequisite", False, {"fixture_status": fixture_status})
        return "blocked", "BLOCKED_RUNTIME_PROVIDER"
    if fixture_status == "INVALID_EVIDENCE":
        _check(checks, "adapter_invalid_evidence", False, {"fixture_status": fixture_status})
        return "invalid", "INVALID_TEST_EXECUTION"
    if fixture_status not in ADAPTER_FIXTURE_READY_STATUSES:
        _check(checks, "adapter_fixture_status", False, {"fixture_status": fixture_status})
        return "invalid", "INVALID_TEST_EXECUTION"
    return None


def _checkpoint_stage2_routing(args: argparse.Namespace) -> dict[str, Any]:
    """Verify PC57-R1's Stage-2 nested native-routing target (adapter@9).

    Only the routing invariant is graded: the root reached the Stage-2
    coordinator and that coordinator performed a real nested native
    delegation.  Downstream ``paper-analysis``/uvx/OCR/finalization quality is
    out of scope once the routing target is mechanically proven; a later
    unchanged downstream failure is recorded as
    ``blocked_or_failed_out_of_scope`` and never reverses the verdict.
    Absence of a supported formal relation is conservatively
    ``BLOCKED_OBSERVABILITY`` and is never inferred as a zero attempt.
    A delegation summary that disagrees with the mechanical derivation from
    its own relation graph — any frozen field: ``state``, the sorted
    distinct receiver union, ``formal_child_count``, ``basis``, or
    ``reason_code`` — is impossible adapter output and fails closed as
    ``INVALID_TEST_EXECUTION`` before the observability verdict.
    """
    checks: list[dict[str, Any]] = []
    root_thread_id: str | None = None
    direct_children: set[str] = set()
    nested_formal_spawns: list[dict[str, Any]] = []
    max_depth = 0
    routing_target_proved = False
    downstream: str | None = None

    def machine(status: str, classification: str) -> dict[str, Any]:
        return {
            "status": status,
            "classification": classification,
            "root_thread_id": root_thread_id,
            "root_direct_spawn_child_ids": sorted(direct_children),
            "nested_formal_spawns": nested_formal_spawns,
            "max_anonymous_depth": max_depth,
            "routing_target_proved": routing_target_proved,
            "downstream_status": downstream,
            "checks": checks,
        }

    try:
        adapter = _load(Path(args.adapter_output)) if args.adapter_output else None
        response = _load(Path(args.eval_response)) if args.eval_response else None
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "evidence_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")
    if not isinstance(adapter, dict) or not isinstance(response, dict):
        _check(checks, "evidence_objects", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    prerequisite = _adapter_prerequisite_block(adapter, checks)
    if prerequisite:
        return machine(*prerequisite)

    output = response.get("output")
    root_thread_id = output.get("thread_id") if isinstance(output, dict) else None
    events = output.get("app_server_events") if isinstance(output, dict) else None
    raw_surface_ok = (isinstance(root_thread_id, str) and bool(root_thread_id.strip())
                      and isinstance(events, list))
    _check(checks, "raw_eval_surface", raw_surface_ok,
           {"thread_id": root_thread_id, "events": type(events).__name__})
    if not raw_surface_ok:
        return machine("blocked", "BLOCKED_RUNTIME_PROVIDER")
    envelope_ok = (response.get("passed") is True
                   and isinstance(output, dict) and output.get("exit_code") == 0
                   and output.get("termination_reason") == "completed")
    # Before the routing target is proven, a failed eval envelope means the
    # provider/runtime failed first; a healthy envelope that still cannot
    # prove the edge is an observability gap.
    unproven_block = "BLOCKED_RUNTIME_PROVIDER" if not envelope_ok else "BLOCKED_OBSERVABILITY"

    delegation = adapter.get("delegation")
    if not isinstance(delegation, dict):
        _check(checks, "adapter_delegation_object", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    delegation_state = delegation.get("state")
    if delegation_state not in ("confirmed", "unobservable"):
        _check(checks, "delegation_state", False, delegation_state)
        return machine("invalid", "INVALID_TEST_EXECUTION")

    dispatch = adapter.get("dispatch")
    relations = dispatch.get("thread_relations") if isinstance(dispatch, dict) else None
    if not isinstance(relations, list):
        _check(checks, "adapter_relations", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")

    edges, malformed = _formal_spawn_relations(adapter)
    _check(checks, "adapter_relation_shape", not malformed, malformed)
    if malformed:
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # adapter@9 derives the delegation summary mechanically from the
    # relation graph, so every frozen summary field — state, the sorted
    # distinct receiver union, its count, basis, and reason code — must
    # equal that derivation from the adapter's own edges.  A summary that
    # disagrees anywhere is contradictory machine evidence and fails closed
    # before any observability verdict can downgrade it.
    expected_summary = _expected_delegation_summary(edges)
    observed_summary = {field: delegation.get(field)
                        for field in expected_summary}
    summary_consistent = observed_summary == expected_summary
    _check(checks, "delegation_summary_consistent", summary_consistent,
           {"observed": observed_summary, "expected": expected_summary})
    if not summary_consistent:
        return machine("invalid", "INVALID_TEST_EXECUTION")
    if delegation_state == "unobservable":
        _check(checks, "delegation_observable", False, delegation)
        return machine("blocked", unproven_block)

    owners, _ = _ownership_index(edges)
    conflicts = {child: sorted(senders) for child, senders in owners.items()
                 if len(senders) != 1}
    _check(checks, "formal_ownership", not conflicts, conflicts)
    if conflicts:
        return machine("invalid", "INVALID_TEST_EXECUTION")

    for edge in edges:
        if edge["sender_thread_id"] == root_thread_id:
            direct_children.add(edge["receiver_thread_id"])
    max_depth = _graph_depth([
        {"parent": edge["sender_thread_id"], "child": edge["receiver_thread_id"]}
        for edge in edges
    ])
    # Unreachable with zero edges: the consistency gate already failed
    # closed on confirmed-without-relations.
    _check(checks, "formal_spawn_surface", bool(edges),
           {"observed": len(edges)})
    _check(checks, "root_direct_formal_child", bool(direct_children),
           sorted(direct_children))
    if not direct_children:
        return machine("blocked", unproven_block)

    nested = [edge for edge in edges
              if edge["sender_thread_id"] in direct_children
              and edge["sender_thread_id"] != root_thread_id]
    seen: set[tuple[str, str]] = set()
    for edge in nested:
        pair = (edge["sender_thread_id"], edge["receiver_thread_id"])
        if pair not in seen:
            seen.add(pair)
            nested_formal_spawns.append({
                "sender_thread_id": edge["sender_thread_id"],
                "receiver_thread_ids": [edge["receiver_thread_id"]],
            })
    # A proven nested relation rules out the zero-attempt
    # coordinator-unavailable path: the coordinator demonstrably delegated.
    _check(checks, "nested_formal_spawn_from_root_child", bool(nested),
           {"observed": len(nested_formal_spawns)})
    if not nested:
        return machine("blocked", unproven_block)
    _check(checks, "anonymous_depth_at_least_two", max_depth >= 2,
           {"observed": max_depth, "required": 2})
    if max_depth < 2:
        return machine("blocked", unproven_block)

    routing_target_proved = True
    downstream = "completed" if envelope_ok else "blocked_or_failed_out_of_scope"
    _check(checks, "routing_target_proved", True,
           {"downstream_status": downstream, "envelope_passed": envelope_ok})
    return machine("pass", "PASS_TARGET")


def _stage4_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for name, relative in STAGE4_PROGRAM_OUTPUTS.items():
        path = root / relative
        exists = path.is_file()
        artifacts[name] = {
            "exists": exists,
            "sha256": _sha256(path) if exists else None,
        }
    return artifacts


def _checkpoint_stage4_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    artifacts = _stage4_artifacts(root)
    checks: list[dict[str, Any]] = []
    _check(checks, "program_root_exists", root.is_dir(), str(root))
    for name, artifact in artifacts.items():
        _check(checks, f"snapshot:{name}", set(artifact) == {"exists", "sha256"}, artifact)
        _check(checks, f"snapshot_hash_shape:{name}",
               (not artifact["exists"] and artifact["sha256"] is None)
               or (artifact["exists"] and isinstance(artifact["sha256"], str)
                   and len(artifact["sha256"]) == 64), artifact)
    return {
        "status": "pass" if all(row["status"] == "pass" for row in checks) else "fail",
        "checks": checks,
        "artifacts": artifacts,
    }


def _load_stage4_snapshot(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load(path)
    if isinstance(payload, dict) and isinstance(payload.get("artifacts"), dict):
        payload = payload["artifacts"]
    if not isinstance(payload, dict):
        raise ValueError("stage4 snapshot must be an object")
    expected = set(STAGE4_PROGRAM_OUTPUTS)
    if set(payload) != expected:
        raise ValueError(f"stage4 snapshot artifact names differ: {set(payload)!r}")
    result: dict[str, dict[str, Any]] = {}
    for name in expected:
        row = payload[name]
        if not isinstance(row, dict) or set(row) != {"exists", "sha256"}:
            raise ValueError(f"invalid stage4 snapshot row: {name}")
        if not isinstance(row["exists"], bool):
            raise ValueError(f"invalid exists flag: {name}")
        if row["exists"] and not isinstance(row["sha256"], str):
            raise ValueError(f"missing sha256 for existing artifact: {name}")
        if not row["exists"] and row["sha256"] is not None:
            raise ValueError(f"absent artifact has a sha256: {name}")
        result[name] = row
    return result


PENDING_CANDIDATE_FIELDS = ("id", "title", "one_liner", "research_question", "fit")


def _pending_selection_projection(value: Any) -> list[dict[str, Any]] | None:
    """Normalize an observed ``pending_selection`` onto the pinned fields."""
    if not isinstance(value, list):
        return None
    projected: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            return None
        professor = row.get("professor")
        kind = row.get("kind")
        direction_ids = row.get("direction_ids")
        candidates = row.get("candidates")
        if not isinstance(professor, str) or not isinstance(kind, str):
            return None
        if not isinstance(direction_ids, list) or not all(isinstance(item, str) for item in direction_ids):
            return None
        if not isinstance(candidates, list):
            return None
        projected_candidates: list[dict[str, Any]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                return None
            if any(field not in candidate for field in PENDING_CANDIDATE_FIELDS):
                return None
            projected_candidates.append({field: candidate[field] for field in PENDING_CANDIDATE_FIELDS})
        projected.append({
            "professor": professor,
            "kind": kind,
            "direction_ids": direction_ids,
            "candidates": projected_candidates,
        })
    return projected


def _project_state_candidates(value: Any) -> list[dict[str, Any]] | None:
    """Project canonical candidate rows, or ``None`` on malformed state."""
    if not isinstance(value, list):
        return None
    projected: list[dict[str, Any]] = []
    for candidate in value:
        if not isinstance(candidate, dict):
            return None
        if any(field not in candidate for field in PENDING_CANDIDATE_FIELDS):
            return None
        projected.append({field: candidate[field] for field in PENDING_CANDIDATE_FIELDS})
    return projected


def _expected_pending_projection(program_root: Path) -> list[dict[str, Any]] | None:
    """Derive the deterministic Path-C expectation from current canonical state.

    The projection mirrors the selection-agent contract: one entry per
    ordinary direction (``kind: "direction"``, exact ``direction_ids``) and
    per explicit cross-direction group (``kind: "cross_direction"``, sorted
    canonical ``direction_ids``), in file order per professor, with
    candidates projected onto the presentation fields in stored order.
    Directories with no candidates contribute no entry; a program without any
    selectable candidate yields ``None``.
    """
    research_dir = program_root / "教授研究"
    if not research_dir.is_dir():
        return None
    state_paths = sorted(
        path for path in research_dir.glob("*/*/套磁候选状态.json") if path.is_file())
    if not state_paths:
        return None
    expected: list[dict[str, Any]] = []
    for state_path in state_paths:
        try:
            state = _load(state_path)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(state, dict):
            return None
        professor = state_path.parent.name
        directions = state.get("directions")
        direction_rows = [row for row in directions if isinstance(row, dict)] \
            if isinstance(directions, list) else []
        for direction in direction_rows:
            projected = _project_state_candidates(direction.get("candidates"))
            if projected is None:
                return None
            direction_id = direction.get("direction_id")
            if not projected:
                continue
            if not isinstance(direction_id, str) or not direction_id:
                return None
            expected.append({
                "professor": professor,
                "kind": "direction",
                "direction_ids": [direction_id],
                "candidates": projected,
            })
        groups = state.get("cross_direction_groups")
        group_rows = [row for row in groups if isinstance(row, dict)] \
            if isinstance(groups, list) else []
        for group in group_rows:
            projected = _project_state_candidates(group.get("candidates"))
            if projected is None:
                return None
            direction_ids = group.get("direction_ids")
            if not projected:
                continue
            if not isinstance(direction_ids, list) or not direction_ids \
                    or not all(isinstance(item, str) and item for item in direction_ids):
                return None
            expected.append({
                "professor": professor,
                "kind": "cross_direction",
                "direction_ids": sorted(direction_ids),
                "candidates": projected,
            })
    return expected or None


def _checkpoint_stage4_needs_input(args: argparse.Namespace) -> dict[str, Any]:
    """Verify the PC53 child-attributed Stage-4 Path-C evidence."""
    checks: list[dict[str, Any]] = []
    root = Path(args.program_root).resolve()
    target_child_id: str | None = None
    business_result: dict[str, Any] | None = None

    def machine(status: str, classification: str) -> dict[str, Any]:
        return {
            "status": status,
            "classification": classification,
            "target_child_id": target_child_id,
            "business_result": business_result,
            "checks": checks,
        }

    pre_path = getattr(args, "pre_snapshot", None)
    post_path = getattr(args, "post_snapshot", None)
    if not pre_path or not post_path:
        _check(checks, "snapshots_supplied", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    try:
        pre = _load_stage4_snapshot(Path(pre_path))
        post = _load_stage4_snapshot(Path(post_path))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        _check(checks, "snapshots_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")
    expected_absent = {
        name: {"exists": False, "sha256": None}
        for name in STAGE4_PROGRAM_OUTPUTS
    }
    _check(checks, "pre_zero_write_snapshot", pre == expected_absent, pre)
    _check(checks, "post_zero_write_snapshot", post == expected_absent, post)
    current = _stage4_artifacts(root)
    zero_write = current == expected_absent
    _check(checks, "current_zero_write", zero_write, current)
    if not (pre == expected_absent and post == expected_absent and zero_write):
        return machine("fail", "FAIL_PRODUCT")

    try:
        adapter = _load(Path(args.adapter_output)) if args.adapter_output else None
        response = _load(Path(args.eval_response)) if args.eval_response else None
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "evidence_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")
    if not isinstance(adapter, dict) or not isinstance(response, dict):
        _check(checks, "evidence_objects", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    prerequisite = _adapter_prerequisite_block(adapter, checks)
    if prerequisite:
        return machine(*prerequisite)

    output = response.get("output")
    root_thread_id = output.get("thread_id") if isinstance(output, dict) else None
    events = output.get("app_server_events") if isinstance(output, dict) else None
    if not isinstance(root_thread_id, str) or not root_thread_id.strip() or not isinstance(events, list):
        _check(checks, "raw_eval_surface", False, {
            "thread_id": root_thread_id, "events": type(events).__name__,
        })
        return machine("invalid", "INVALID_TEST_EXECUTION")
    delegation = adapter.get("delegation")
    if not isinstance(delegation, dict):
        _check(checks, "adapter_delegation_object", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    delegation_state = delegation.get("state")
    if delegation_state not in ("confirmed", "unobservable"):
        _check(checks, "delegation_state", False, delegation_state)
        return machine("invalid", "INVALID_TEST_EXECUTION")

    dispatch = adapter.get("dispatch")
    relations = dispatch.get("thread_relations") if isinstance(dispatch, dict) else None
    if not isinstance(relations, list):
        _check(checks, "adapter_relations", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    edges, malformed = _formal_spawn_relations(adapter)
    _check(checks, "adapter_relation_shape", not malformed, malformed)
    if malformed:
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # Same full-field consistency gate as the Stage-2 routing checkpoint:
    # every frozen delegation summary field must equal the mechanical
    # derivation from the adapter's own relation graph, and a mismatch
    # fails closed before the observability verdict.
    expected_summary = _expected_delegation_summary(edges)
    observed_summary = {field: delegation.get(field)
                        for field in expected_summary}
    summary_consistent = observed_summary == expected_summary
    _check(checks, "delegation_summary_consistent", summary_consistent,
           {"observed": observed_summary, "expected": expected_summary})
    if not summary_consistent:
        return machine("invalid", "INVALID_TEST_EXECUTION")
    if delegation_state == "unobservable":
        _check(checks, "delegation_observable", False, delegation)
        return machine("blocked", "BLOCKED_OBSERVABILITY")
    owners, _ = _ownership_index(edges)
    direct_children: set[str] = set()
    for edge in edges:
        if edge["sender_thread_id"] == root_thread_id:
            direct_children.add(edge["receiver_thread_id"])
    ownership_conflicts = {child: sorted(parents) for child, parents in owners.items() if len(parents) != 1}
    if ownership_conflicts:
        _check(checks, "formal_ownership", False, ownership_conflicts)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    _check(checks, "formal_root_children", bool(direct_children), sorted(direct_children))
    if not direct_children:
        return machine("blocked", "BLOCKED_OBSERVABILITY")

    def child_result(child_id: str) -> tuple[str, dict[str, Any] | None]:
        assistant_messages: list[str] = []
        for event in events:
            message = event.get("message") if isinstance(event, dict) else None
            if not isinstance(message, dict):
                continue
            if message.get("method") != "rawResponseItem/completed":
                continue
            params = message.get("params")
            if not isinstance(params, dict) or params.get("threadId") != child_id:
                continue
            item = params.get("item")
            if not isinstance(item, dict) or item.get("type") != "message" or item.get("role") != "assistant":
                # A child thread emits developer, user, reasoning, and tool
                # items as well.  The contract pins business-result parsing to
                # assistant output_text messages only.
                continue
            content = item.get("content")
            if not isinstance(content, list):
                return "malformed", None
            texts: list[str] = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if not isinstance(text, str):
                        return "malformed", None
                    texts.append(text)
            if texts:
                assistant_messages.append("".join(texts))
        if not assistant_messages:
            return "absent", None
        try:
            parsed = json.loads(assistant_messages[-1])
        except (TypeError, json.JSONDecodeError):
            return "not_json", None
        return ("object", parsed) if isinstance(parsed, dict) else ("not_json", None)

    observed: dict[str, tuple[str, dict[str, Any] | None]] = {
        child: child_result(child) for child in sorted(direct_children)
    }
    _check(checks, "child_message_surface", any(state != "absent" for state, _ in observed.values()), observed)
    if all(state == "absent" for state, _ in observed.values()):
        return machine("blocked", "BLOCKED_OBSERVABILITY")
    if any(state in {"malformed", "not_json"} for state, _ in observed.values()):
        return machine("fail", "FAIL_PRODUCT")

    path_c_children = [
        child for child, (state, result) in observed.items()
        if state == "object" and isinstance(result, dict)
        and result.get("result") == "needs_input"
    ]
    if len(path_c_children) != 1:
        object_children = [child for child, (state, _) in observed.items() if state == "object"]
        if len(object_children) == 1:
            target_child_id = object_children[0]
            business_result = observed[target_child_id][1]
        _check(checks, "exactly_one_path_c_child", False, path_c_children)
        return machine("fail", "FAIL_PRODUCT")
    target_child_id = path_c_children[0]
    business_result = observed[target_child_id][1]
    pending = business_result.get("pending_selection") if isinstance(business_result, dict) else None
    _check(checks, "pending_selection_nonempty", isinstance(pending, list) and bool(pending), pending)
    if not isinstance(pending, list) or not pending:
        return machine("fail", "FAIL_PRODUCT")
    projection = _pending_selection_projection(pending)
    expected = _expected_pending_projection(root)
    _check(checks, "expected_projection_derivable", expected is not None,
           {"program_root": str(root)})
    if expected is None:
        return machine("invalid", "INVALID_TEST_EXECUTION")
    _check(checks, "pending_selection_matches_current_state", projection == expected,
           {"expected": expected, "observed": projection})
    if projection != expected:
        return machine("fail", "FAIL_PRODUCT")
    _check(checks, "no_root_prose_gate", True)
    return machine("pass", "PASS")


def _candidate_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = state.get("candidates", [])
    if isinstance(candidates, dict):
        candidates = candidates.get(DIRECTION_ID, candidates.get("items", []))
    if not candidates:
        directions = state.get("directions")
        direction = next((row for row in directions if isinstance(row, dict)
                          and row.get("direction_id") == DIRECTION_ID), None) \
            if isinstance(directions, list) else None
        candidates = (direction or {}).get("candidates", [])
    return [row for row in candidates if isinstance(row, dict) and row.get("id")]


def _checkpoint_make_stage4_selection(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    state_path = _professor_dir(root) / "套磁候选状态.json"
    try:
        rows = sorted(_candidate_rows(_load(state_path)), key=lambda row: str(row["id"]))
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        _check(checks, "candidate_state_readable", False, str(exc))
        return _finish(checks)
    _check(checks, "candidate_available", bool(rows))
    if not rows:
        return _finish(checks)
    selected = rows[0]
    payload = {"selection": [{"professor": PROFESSOR, "direction_ids": [DIRECTION_ID],
                               "ideas": [{"id": selected["id"]}]}]}
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                                     prefix=f".{output.name}.", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, output)
    _check(checks, "selection_written", output.is_file(), str(output))
    return _finish(checks, selected_id=selected["id"], output=str(output), payload=payload)


def _checkpoint_stage4_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    prof = _professor_dir(root)
    try:
        selection = _load(prof / "套磁选择.json")
        email_input = _load(prof / "邮件输入.json")
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "stage4_outputs_readable", False, str(exc))
        return _finish(checks)
    _check(checks, "selection_has_direction", _contains_direction(selection))
    emails = email_input.get("emails", email_input.get("messages", []))
    if isinstance(emails, dict):
        emails = list(emails.values())
    _check(checks, "email_pack_nonempty", bool(emails), len(emails) if isinstance(emails, list) else type(emails).__name__)
    evidence = [row.get("contact_evidence") for row in emails if isinstance(row, dict)] if isinstance(emails, list) else []
    _check(checks, "contact_evidence_frozen", bool(evidence) and all(
        isinstance(item, dict) and bool(item.get("record_fingerprint")) and isinstance(item.get("record"), dict)
        for item in evidence), evidence)
    return _finish(checks, selection_file=str(prof / "套磁选择.json"), email_count=len(emails) if isinstance(emails, list) else 0)


def _checkpoint_stage5_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    prof = _professor_dir(root)
    # The installed runner writes final outputs directly in the professor
    # directory (``套磁邮件.md`` / ``套磁跟进邮件.md``); accept the nested
    # directory form too because profile inputs use ``套磁邮件/``.
    md_files = sorted(path for path in prof.glob("套磁*.md") if path.is_file())
    md_files.extend(sorted(path for path in (prof / "套磁邮件").glob("套磁*.md") if path.is_file()))
    txt_files = sorted(path for path in prof.glob("套磁*.txt") if path.is_file())
    txt_files.extend(sorted(path for path in (prof / "套磁邮件").glob("套磁*.txt") if path.is_file()))
    all_files = md_files + txt_files
    initial_md = [path for path in md_files if "套磁邮件" in path.name and "跟进" not in path.name]
    followup_md = [path for path in md_files if "跟进" in path.name or "follow" in path.name.lower()]
    initial_txt = [path for path in txt_files if "套磁邮件" in path.name and "跟进" not in path.name]
    followup_txt = [path for path in txt_files if "跟进" in path.name or "follow" in path.name.lower()]
    _check(checks, "initial_email_output", bool(initial_md) and bool(initial_txt), [path.name for path in all_files])
    _check(checks, "followup_email_output", bool(followup_md) and bool(followup_txt), [path.name for path in all_files])
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in all_files)
    _check(checks, "no_unresolved_placeholders", "{{" not in text and "}}" not in text)
    _check(checks, "pre_send_checklist", "送信前核对" in text or "send" in text.lower())
    email_pack_path = prof / "邮件输入.json"
    state_path = prof / "套磁邮件状态.json"
    try:
        email_pack = _load(email_pack_path)
        email_state = _load(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "email_state_and_pack_readable", False, str(exc))
        return _finish(checks, email_files=[path.name for path in all_files],
                       email_state=str(state_path))
    _check(checks, "email_pack_object", isinstance(email_pack, dict), type(email_pack).__name__)
    _check(checks, "email_state_object", isinstance(email_state, dict), type(email_state).__name__)
    if not isinstance(email_pack, dict) or not isinstance(email_state, dict):
        return _finish(checks, email_files=[path.name for path in all_files],
                       email_state=str(state_path))
    _check(checks, "email_pack_schema", email_pack.get("schema") == 2
           and email_pack.get("kind") == "professor-contact-email-input"
           and email_pack.get("identity_version") == DIRECTION_IDENTITY_VERSION)
    _check(checks, "email_state_schema", email_state.get("schema") == 1
           and isinstance(email_state.get("emails"), dict))
    pack_emails = email_pack.get("emails", [])
    if isinstance(pack_emails, dict):
        pack_emails = list(pack_emails.values())
    state_emails = email_state.get("emails", {}) if isinstance(email_state, dict) else {}
    frozen_and_valid = True
    invalid_details: list[Any] = []
    for email in pack_emails if isinstance(pack_emails, list) else []:
        if not isinstance(email, dict):
            frozen_and_valid = False
            invalid_details.append("email entry is not an object")
            continue
        email_id = email.get("email_id")
        evidence = email.get("contact_evidence")
        entry = state_emails.get(email_id) if isinstance(state_emails, dict) else None
        initial_validation = entry.get("validation") if isinstance(entry, dict) else None
        followup = entry.get("followup") if isinstance(entry, dict) else None
        followup_validation = followup.get("validation") if isinstance(followup, dict) else None
        valid_evidence = (isinstance(evidence, dict)
                          and isinstance(evidence.get("record"), dict)
                          and isinstance(evidence.get("record_fingerprint"), str)
                          and bool(evidence.get("record_fingerprint")))
        valid_source = (isinstance(email_id, str) and isinstance(email.get("source_hash"), str)
                        and bool(email.get("source_hash")) and isinstance(entry, dict)
                        and entry.get("input_fingerprint") == email.get("source_hash"))
        valid_validation = (_valid_validation_record(initial_validation)
                            and initial_validation.get("result") == "pass"
                            and _valid_validation_record(followup_validation)
                            and followup_validation.get("result") == "pass")
        if not (valid_evidence and valid_source and valid_validation):
            frozen_and_valid = False
            invalid_details.append({"email_id": email_id, "evidence": valid_evidence,
                                    "source": valid_source, "validation": valid_validation})
    _check(checks, "email_entries_frozen_and_valid", bool(pack_emails) and frozen_and_valid,
           invalid_details)
    return _finish(checks, email_files=[path.name for path in all_files], email_state=str(state_path))


def _relation_rows(payload: Any) -> list[dict[str, Any]]:
    """Extract completed formal spawn edges from adapter @9's normalized graph.

    Field authority and shape follow the same pinned sender_rule as
    ``_formal_spawn_relations``: the formal owner is ``sender_thread_id`` and
    ``parent_thread_id`` is app-server event attribution that is never read.
    The completion boundary is issue-specific and stays frozen: the #32
    runtime-graph checkpoint and the #51/#52 standalone verifier judge
    completed formal ``spawnAgent`` topology, so only ``status ==
    "completed"`` relations build edges here; the #57 attempt-style
    extraction that never requires completion lives in
    ``_formal_spawn_relations``.
    """
    rows: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return rows
    dispatch = payload.get("dispatch")
    relations = dispatch.get("thread_relations") if isinstance(dispatch, dict) else None
    if not isinstance(relations, list):
        return rows
    for relation in relations:
        if not isinstance(relation, dict) or relation.get("tool") != "spawnAgent":
            continue
        if relation.get("status") != "completed":
            continue
        sender = relation.get("sender_thread_id")
        children = relation.get("receiver_thread_ids")
        if not isinstance(sender, str) or not sender or not isinstance(children, list):
            continue
        for child in children:
            if isinstance(child, str) and child:
                rows.append({"parent": sender, "child": child, "kind": "spawnAgent"})
    return rows


def _graph_depth(edges: list[dict[str, Any]]) -> int:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(str(edge["parent"]), set()).add(str(edge["child"]))

    def longest_from(node: str, seen: set[str]) -> int:
        best = 0
        for child in adjacency.get(node, set()):
            if child in seen:
                continue
            best = max(best, 1 + longest_from(child, seen | {child}))
        return best

    return max((longest_from(node, {node}) for node in adjacency), default=0)


def _checkpoint_runtime_graph(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    adapter = None
    if args.adapter_output:
        try:
            adapter = _load(Path(args.adapter_output))
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, "adapter_evidence_readable", False, str(exc))
    else:
        _check(checks, "adapter_evidence_supplied", False)
    if args.eval_response:
        try:
            response = _load(Path(args.eval_response))
            output = response.get("output") if isinstance(response, dict) else None
            _check(checks, "raw_app_server_events_readable",
                   isinstance(output, dict) and isinstance(output.get("app_server_events"), list))
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, "raw_evidence_readable", False, str(exc))
    delegation = adapter.get("delegation") if isinstance(adapter, dict) else None
    basis = delegation.get("basis") if isinstance(delegation, dict) else None
    children = delegation.get("child_thread_ids") if isinstance(delegation, dict) else None
    delegation_ok = (isinstance(delegation, dict)
                     and delegation.get("state") == "confirmed"
                     and isinstance(basis, list)
                     and "formal_spawn_relation" in basis
                     and isinstance(children, list)
                     and bool(children))
    _check(checks, "adapter_delegation_confirmed", delegation_ok,
           {"state": delegation.get("state") if isinstance(delegation, dict) else None,
            "basis": basis, "child_thread_ids": children})
    rows = _relation_rows(adapter)
    formal = []
    for row in rows:
        parent = row.get("parent") or row.get("parent_id") or row.get("from") or row.get("caller")
        child = row.get("child") or row.get("child_id") or row.get("to") or row.get("callee")
        if parent and child:
            formal.append({"parent": str(parent), "child": str(child), "kind": "spawnAgent"})
    formal = list({(row["parent"], row["child"]): row for row in formal}.values())
    _check(checks, "formal_delegation_edges", delegation_ok and len(formal) >= args.min_edges,
           {"observed": len(formal), "required": args.min_edges})
    depth = _graph_depth(formal)
    _check(checks, "nested_depth", delegation_ok and depth >= args.required_depth,
           {"observed": depth, "required": args.required_depth})
    return _finish(checks, formal_relations=formal)


CHECKPOINTS = {
    "install": _checkpoint_install,
    "initial": _checkpoint_initial,
    "stage0-needs-input": _checkpoint_stage0_needs_input,
    "stage0-final": _checkpoint_stage0_final,
    "stage1-final": _checkpoint_stage1_final,
    "stage2-final": _checkpoint_stage2_final,
    "stage3-final": _checkpoint_stage3_final,
    "stage3-snapshot": _checkpoint_stage3_snapshot,
    "stage3-routing": _checkpoint_stage3_routing,
    "stage2-routing": _checkpoint_stage2_routing,
    "stage4-snapshot": _checkpoint_stage4_snapshot,
    "stage4-needs-input": _checkpoint_stage4_needs_input,
    "make-stage4-selection": _checkpoint_make_stage4_selection,
    "stage4-final": _checkpoint_stage4_final,
    "stage5-final": _checkpoint_stage5_final,
    "runtime-graph": _checkpoint_runtime_graph,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", choices=tuple(CHECKPOINTS))
    parser.add_argument("--program-root", type=Path)
    parser.add_argument("--consumer-root", type=Path)
    parser.add_argument("--eval-response", type=Path)
    parser.add_argument("--adapter-output", type=Path)
    parser.add_argument("--pre-snapshot", type=Path)
    parser.add_argument("--post-snapshot", type=Path)
    parser.add_argument("--producer-sha", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-edges", type=int, default=1)
    parser.add_argument("--required-depth", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.checkpoint != "install" and args.program_root is None:
            raise ValueError("--program-root is required for this checkpoint")
        if args.checkpoint == "make-stage4-selection" and args.output is None:
            raise ValueError("--output is required for make-stage4-selection")
        payload = CHECKPOINTS[args.checkpoint](args)
    except Exception as exc:
        payload = _result("fail", [{"name": "verifier_exception", "status": "fail", "detail": str(exc)}])
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
