#!/usr/bin/env python3
"""Read-only checkpoints for issue #32's Stage 0–5 runtime evaluation.

The verifier observes product state and adapter-provided structured evidence.
It never repairs product files.  The only intentional writes are the
``make-stage4-selection`` and ``make-stage5-choices`` helpers, which model
explicit caller inputs and write only their requested output paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Any

MANIFEST_NAME = "fixture-manifest.json"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
ITEM_KEYS = ("AAAA1111", "BBBB2222")
PROGRAM_STAGE_OUTPUTS = (
    Path("教授研究/套磁目标.json"), Path("教授研究/套磁阶段1候选.json"),
    Path("教授研究/套磁选择.json"), Path("教授研究/邮件输入.json"),
)
PROFESSOR_STAGE_OUTPUTS = (
    Path("套磁候选输入.json"), Path("套磁候选状态.json"),
)
INPUT_PACK_KIND = "professor-contact-stage2-input"
CANDIDATE_STATE_KIND = "professor-contact-stage3-state"
DIRECTION_IDENTITY_VERSION = "direction-id-v1"
STAGE3_GENERATOR_CONTRACT_VERSION = "stage3-ideas-v2"
STAGE5_FINAL_NAMES = (
    "套磁邮件.md", "套磁邮件.txt", "套磁跟进邮件.md", "套磁跟进邮件.txt",
)
STAGE5_CHOICES_SENTINELS = {
    "first_choice": False,
    "signature_name": "Fixture Applicant",
    "learning": "I am studying reproducible research workflows.",
    "initial_sent_date": "2026-09-15",
}
STAGE5_FIRST_CHOICE_PHRASE = "先生の研究室を第一志望として出願させていただきたく存じます"
STAGE5_NON_FIRST_CHOICE_PHRASE = "先生の研究室を志望として出願させていただきたく存じます"
# Issue #43 §6.4 requires the sentinels at the deterministic template slots:
# the signature inside ``出身の{{氏名}}（`` on the identity line, learning
# directly before the aspiration value on the same template line, and the
# follow-up date inside ``{{初回送信日}}に初回連絡しました。``.
STAGE5_SIGNATURE_SLOT = "出身の{name}（"
STAGE5_LEARNING_SLOT_TAIL = " 先生の研究室を"
STAGE5_SENT_DATE_SLOT = "{date}に初回連絡しました。"


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
    item_keys = manifest.get("item_keys")
    valid_item_keys = (isinstance(item_keys, list) and len(item_keys) == 2
                       and all(isinstance(key, str) and key for key in item_keys)
                       and len(set(item_keys)) == 2)
    _check(checks, "item_keys", valid_item_keys, item_keys)
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


def _runtime_item_roles(root: Path) -> tuple[tuple[str, str], tuple[str, str]]:
    """Return the fixture's item keys and its ready/fill roles.

    The deterministic fixture keeps the historical ``ITEM_KEYS`` constants,
    while the runtime recipe replaces them with keys returned by Zotero.  The
    manifest is the provenance source for those runtime keys, so checkpoints
    must derive their expectations from it instead of inventing literals.
    """
    try:
        manifest = _load(root / MANIFEST_NAME)
    except (OSError, json.JSONDecodeError):
        return ITEM_KEYS, ITEM_KEYS
    keys = manifest.get("item_keys")
    ready = manifest.get("ready_item_keys")
    missing = manifest.get("missing_item_keys")
    valid_keys = (isinstance(keys, list) and len(keys) == 2
                  and all(isinstance(key, str) and key for key in keys)
                  and len(set(keys)) == 2)
    valid_roles = (isinstance(ready, list) and len(ready) == 1
                   and isinstance(missing, list) and len(missing) == 1
                   and ready[0] in keys and missing[0] in keys
                   and ready[0] != missing[0]) if valid_keys else False
    if not valid_keys:
        return ITEM_KEYS, ITEM_KEYS
    item_keys = (keys[0], keys[1])
    return item_keys, (ready[0], missing[0]) if valid_roles else item_keys


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
    expected = [consumer / ".agents/skills/professor-contact/SKILL.md",
                consumer / ".codex/agents/professor-contact.toml",
                consumer / ".codex/agents/professor-contact-email-generator.toml"]
    for path in expected:
        _check(checks, f"installed:{path.relative_to(consumer)}", path.is_file(), str(path))
        if path.exists():
            _check(checks, f"contained:{path.name}", path.resolve().is_relative_to(consumer), str(path.resolve()))
    generator_path = consumer / ".codex/agents/professor-contact-email-generator.toml"
    if generator_path.is_file():
        try:
            generator = tomllib.loads(generator_path.read_text(encoding="utf-8"))
            instructions = generator.get("developer_instructions")
            _check(checks, "generated_generator_name",
                   generator.get("name") == "professor-contact-email-generator")
            _check(checks, "generated_choices_contract",
                   isinstance(instructions, str)
                   and all(token in instructions for token in (
                       "Stage 5", "choices", "email_id", "first_choice",
                       "signature_name", "learning", "initial_sent_date", "--choices")))
            if isinstance(instructions, str):
                branch_start = instructions.find("### Codex branch")
                branch_end = instructions.find("### humanizer-ja stage-5 constraints", branch_start + 1)
                codex_branch = instructions[branch_start:branch_end] \
                    if branch_start >= 0 and branch_end > branch_start else ""
                _check(checks, "generated_codex_branch_present", bool(codex_branch))
                _check(checks, "generated_codex_no_opencode_question",
                       bool(codex_branch) and "question(" not in codex_branch)
                _check(checks, "generated_codex_no_opencode_task",
                       bool(codex_branch) and "task(subagent_type" not in codex_branch)
            else:
                _check(checks, "generated_codex_branch_present", False)
                _check(checks, "generated_codex_no_opencode_question", False)
                _check(checks, "generated_codex_no_opencode_task", False)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            _check(checks, "generated_projection_readable", False, str(exc))
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
    item_keys, (ready_key, fill_key) = _runtime_item_roles(root)
    _check(checks, "preview_exists", (prof / "方向预筛.json").is_file())
    direction = _direction(root)
    _check(checks, "legal_direction_preview", direction is not None)
    try:
        papers = _load(prof / "papers.json").get("papers", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        papers = []
    by_key = {row.get("item_key"): row for row in papers if isinstance(row, dict)}
    _check(checks, "catalog_keys", set(by_key) == set(item_keys), list(by_key))
    _check(checks, "ready_and_missing", by_key.get(ready_key, {}).get("pdf_status") == "downloaded"
           and by_key.get(fill_key, {}).get("pdf_status") == "missing", by_key)
    pdf = prof / f"论文分析/{ready_key}.pdf"
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
    item_keys, (_, fill_key) = _runtime_item_roles(root)
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
        _check(checks, "snapshot_members", set(direction.get("candidate_keys", [])) == set(item_keys), direction.get("candidate_keys"))
        readiness = direction.get("pdf_readiness", {})
        _check(checks, "pdf_readiness", set(readiness.get("usable_item_keys", [])) == set(item_keys)
               and readiness.get("missing_item_keys", []) == [], readiness)
    by_key = {row.get("item_key"): row for row in papers if isinstance(row, dict)}
    _check(checks, "collector_completed", by_key.get(fill_key, {}).get("pdf_status") == "downloaded")
    if args.eval_response:
        try:
            response = _response(args)
            payloads = _structured_values(response, {"collector_payload", "collector_request", "tool_payload"})
            if isinstance(response, dict):
                payloads.append(response)
            exact = any(isinstance(row, dict) and row.get("folder_path") and row.get("pdf_only") is True
                        and row.get("item_keys") == [fill_key] and "professors" not in row
                        for row in payloads)
            _check(checks, "collector_payload_contract", exact)
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, "eval_response_readable", False, str(exc))
    return _finish(checks, snapshot_file=str(snapshot_path), papers=sorted(by_key))


def _checkpoint_stage2_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    prof = _professor_dir(root)
    _, (ready_key, _) = _runtime_item_roles(root)
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
    _check(checks, "analysis_for_ready_paper", bool(list((prof / "论文分析").glob(f"{ready_key}*.md"))))
    _check(checks, "future_work_sidecar", bool(list((prof / "论文分析").glob(f"{ready_key}*.future_work.json"))))
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


def _checkpoint_stage4_needs_input(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    response = None
    try:
        response = _response(args)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "eval_response_readable", False, str(exc))
    _check(checks, "selection_file_absent", not (root / "教授研究/套磁选择.json").exists())
    _check(checks, "email_input_absent", not (root / "教授研究/邮件输入.json").exists())
    _check(checks, "selection_request_structured", isinstance(response, (dict, list))
           and _has_structured_key(response, {"pending_selection", "selection_request", "needs_input"}))
    return _finish(checks)


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
    direction_id = getattr(args, "direction_id", DIRECTION_ID)
    selection_policy = getattr(args, "selection_policy", "lexicographic-first-candidate-id")
    _check(checks, "stage4_direction_id", direction_id == DIRECTION_ID, direction_id)
    _check(checks, "stage4_selection_policy",
           selection_policy == "lexicographic-first-candidate-id", selection_policy)
    if any(row["status"] == "fail" for row in checks):
        return _finish(checks)
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
    stage4_root = root / "教授研究"
    try:
        selection = _load(stage4_root / "套磁选择.json")
        email_input = _load(stage4_root / "邮件输入.json")
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
    return _finish(checks, selection_file=str(stage4_root / "套磁选择.json"),
                   email_count=len(emails) if isinstance(emails, list) else 0)


def _stage5_candidate_paths(professor_dir: Path, name: str) -> tuple[Path, ...]:
    return (professor_dir / name, professor_dir / "套磁邮件" / name)


def _checkpoint_stage5_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    """Capture the issue-43 Stage 5 artifact state without changing it."""
    root = Path(args.program_root).resolve()
    relative_paths = (
        Path("教授研究/X分野/Example Professor/套磁邮件.md"),
        Path("教授研究/X分野/Example Professor/套磁邮件.txt"),
        Path("教授研究/X分野/Example Professor/套磁跟进邮件.md"),
        Path("教授研究/X分野/Example Professor/套磁跟进邮件.txt"),
        Path("教授研究/X分野/Example Professor/套磁邮件状态.json"),
    )
    artifacts: dict[str, dict[str, Any]] = {}
    for relative in relative_paths:
        path = root / relative
        artifacts[relative.as_posix()] = {
            "exists": path.exists(),
            "sha256": _sha256(path) if path.is_file() else None,
        }
    return {"status": "pass", "observed": {"artifacts": artifacts}}


def _checkpoint_stage5_pristine(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    prof = _professor_dir(root)
    stage4_root = root / "教授研究"
    try:
        selection = _load(stage4_root / "套磁选择.json")
        email_pack = _load(stage4_root / "邮件输入.json")
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "stage4_outputs_readable", False, str(exc))
        return _finish(checks)

    _check(checks, "selection_has_direction", _contains_direction(selection))
    emails = email_pack.get("emails", email_pack.get("messages", [])) \
        if isinstance(email_pack, dict) else []
    if isinstance(emails, dict):
        emails = list(emails.values())
    _check(checks, "email_pack_readable", isinstance(email_pack, dict)
           and email_pack.get("kind") == "professor-contact-email-input")
    _check(checks, "email_pack_nonempty", isinstance(emails, list) and bool(emails),
           len(emails) if isinstance(emails, list) else type(emails).__name__)

    for name in STAGE5_FINAL_NAMES:
        candidates = _stage5_candidate_paths(prof, name)
        _check(checks, f"{name}_absent", not any(path.exists() for path in candidates),
               [str(path) for path in candidates])
    state_candidates = _stage5_candidate_paths(prof, "套磁邮件状态.json")
    _check(checks, "email_state_absent", not any(path.exists() for path in state_candidates),
           [str(path) for path in state_candidates])
    return _finish(checks, professor_dir=str(prof), email_count=len(emails) if isinstance(emails, list) else 0)


def _checkpoint_make_stage5_choices(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    stage4_root = root / "教授研究"
    try:
        email_pack = _load(stage4_root / "邮件输入.json")
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "email_pack_readable", False, str(exc))
        return _finish(checks)
    emails = email_pack.get("emails", email_pack.get("messages", [])) \
        if isinstance(email_pack, dict) else []
    if isinstance(emails, dict):
        emails = list(emails.values())
    valid_rows = [row for row in emails if isinstance(row, dict) and isinstance(row.get("email_id"), str)
                  and row.get("email_id")]
    _check(checks, "exactly_one_real_email", len(emails) == 1 and len(valid_rows) == 1,
           [row.get("email_id") for row in valid_rows])
    if len(emails) != 1 or len(valid_rows) != 1:
        return _finish(checks, output=str(Path(args.output).resolve()))

    payload = {"email_id": valid_rows[0]["email_id"], **STAGE5_CHOICES_SENTINELS}
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                                     prefix=f".{output.name}.", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, output)
    _check(checks, "choices_written", output.is_file(), str(output))
    return _finish(checks, email_id=valid_rows[0]["email_id"], output=str(output), payload=payload)


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
    _check(checks, "final_initial_exists", bool(initial_md) and bool(initial_txt),
           [str(path) for path in initial_md + initial_txt])
    _check(checks, "final_followup_exists", bool(followup_md) and bool(followup_txt),
           [str(path) for path in followup_md + followup_txt])
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in all_files)
    _check(checks, "no_unresolved_placeholders", "{{" not in text and "}}" not in text)
    _check(checks, "pre_send_checklist", "送信前核对" in text or "send" in text.lower())
    email_pack_path = root / "教授研究/邮件输入.json"
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
    initial_text = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                              for path in initial_md + initial_txt)
    followup_text = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                               for path in followup_md + followup_txt)
    initial_txt_text = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                                 for path in initial_txt)
    followup_txt_text = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                                  for path in followup_txt)
    choice_email_id_ok = bool(pack_emails)
    choice_signature_ok = bool(pack_emails)
    choice_learning_ok = bool(pack_emails)
    choice_initial_sent_date_ok = bool(pack_emails)
    choice_branch_ok = bool(pack_emails)
    for email in pack_emails if isinstance(pack_emails, list) else []:
        email_id = email.get("email_id") if isinstance(email, dict) else None
        entry = state_emails.get(email_id) if isinstance(state_emails, dict) else None
        choices = entry.get("choices") if isinstance(entry, dict) else None
        followup_choices = entry.get("followup", {}).get("choices") \
            if isinstance(entry, dict) and isinstance(entry.get("followup"), dict) else None
        choice_rows = [row for row in (choices, followup_choices) if isinstance(row, dict)]
        choice_email_id_ok = choice_email_id_ok and len(choice_rows) == 2 \
            and all(row.get("email_id") == email_id for row in choice_rows)
        # Issue #43 pins the caller's fixed sentinels as the independent
        # expected, rendered at the deterministic template slots from §6.4:
        # expected values never come from product state, and only the slot
        # occurrence in the canonical .txt -- not presence anywhere in the
        # merged output -- decides the render checks.
        choice_signature_ok = choice_signature_ok and isinstance(choices, dict) \
            and choices.get("signature_name") == STAGE5_CHOICES_SENTINELS["signature_name"] \
            and STAGE5_SIGNATURE_SLOT.format(
                name=STAGE5_CHOICES_SENTINELS["signature_name"]) in initial_txt_text
        choice_learning_ok = choice_learning_ok and isinstance(choices, dict) \
            and choices.get("learning") == STAGE5_CHOICES_SENTINELS["learning"] \
            and STAGE5_CHOICES_SENTINELS["learning"] + STAGE5_LEARNING_SLOT_TAIL \
            in initial_txt_text
        choice_initial_sent_date_ok = choice_initial_sent_date_ok \
            and isinstance(followup_choices, dict) \
            and followup_choices.get("initial_sent_date") \
            == STAGE5_CHOICES_SENTINELS["initial_sent_date"] \
            and STAGE5_SENT_DATE_SLOT.format(
                date=STAGE5_CHOICES_SENTINELS["initial_sent_date"]) in followup_txt_text
        choice_branch_ok = choice_branch_ok and isinstance(choices, dict) \
            and choices.get("first_choice") is False \
            and STAGE5_NON_FIRST_CHOICE_PHRASE in initial_text \
            and STAGE5_FIRST_CHOICE_PHRASE not in initial_text
    _check(checks, "choice_email_id_matches_pack", choice_email_id_ok)
    _check(checks, "choice_signature_rendered", choice_signature_ok)
    _check(checks, "choice_learning_rendered", choice_learning_ok)
    _check(checks, "choice_initial_sent_date_rendered", choice_initial_sent_date_ok)
    _check(checks, "choice_non_first_choice_branch_rendered", choice_branch_ok)
    # Issue #43 keeps frozen contact evidence and the pack/source fingerprint
    # as its machine invariants, while the unchanged downstream email
    # validator's copy quality stays separate evidence that never decides the
    # issue-43 feature verdict.
    frozen_and_valid = True
    validator_pass = True
    invalid_details: list[Any] = []
    for email in pack_emails if isinstance(pack_emails, list) else []:
        if not isinstance(email, dict):
            frozen_and_valid = False
            validator_pass = False
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
        if not (valid_evidence and valid_source):
            frozen_and_valid = False
        if not valid_validation:
            validator_pass = False
        if not (valid_evidence and valid_source and valid_validation):
            invalid_details.append({"email_id": email_id, "evidence": valid_evidence,
                                    "source": valid_source, "validation": valid_validation})
    _check(checks, "email_entries_frozen_and_valid", bool(pack_emails) and frozen_and_valid,
           invalid_details)
    _check(checks, "email_validator_result_pass", bool(pack_emails) and validator_pass,
           invalid_details)
    return _finish(checks, email_files=[path.name for path in all_files], email_state=str(state_path))


def _relation_rows(payload: Any) -> list[dict[str, Any]]:
    """Extract formal spawn relations from adapter @9's normalized graph."""
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
        parent = relation.get("parent_thread_id")
        children = relation.get("receiver_thread_ids")
        if not isinstance(parent, str) or not parent or not isinstance(children, list):
            continue
        for child in children:
            if isinstance(child, str) and child:
                rows.append({"parent": parent, "child": child, "kind": "spawnAgent"})
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
    "stage4-needs-input": _checkpoint_stage4_needs_input,
    "make-stage4-selection": _checkpoint_make_stage4_selection,
    "stage4-final": _checkpoint_stage4_final,
    "stage5-snapshot": _checkpoint_stage5_snapshot,
    "stage5-pristine": _checkpoint_stage5_pristine,
    "make-stage5-choices": _checkpoint_make_stage5_choices,
    "stage5-final": _checkpoint_stage5_final,
    "runtime-graph": _checkpoint_runtime_graph,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", nargs="?", choices=tuple(CHECKPOINTS))
    parser.add_argument("--make-stage4-selection", action="store_true")
    parser.add_argument("--direction-id", default=DIRECTION_ID)
    parser.add_argument("--selection-policy", default="lexicographic-first-candidate-id")
    parser.add_argument("--program-root", type=Path)
    parser.add_argument("--consumer-root", type=Path)
    parser.add_argument("--eval-response", type=Path)
    parser.add_argument("--adapter-output", type=Path)
    parser.add_argument("--producer-sha", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-edges", type=int, default=1)
    parser.add_argument("--required-depth", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.make_stage4_selection:
            if args.checkpoint and args.checkpoint != "make-stage4-selection":
                raise ValueError("--make-stage4-selection cannot be combined with another checkpoint")
            args.checkpoint = "make-stage4-selection"
        if args.checkpoint is None:
            raise ValueError("checkpoint is required")
        if args.checkpoint != "install" and args.program_root is None:
            raise ValueError("--program-root is required for this checkpoint")
        if args.checkpoint in {"make-stage4-selection", "make-stage5-choices"} and args.output is None:
            raise ValueError(f"--output is required for {args.checkpoint}")
        payload = CHECKPOINTS[args.checkpoint](args)
    except Exception as exc:
        payload = _result("fail", [{"name": "verifier_exception", "status": "fail", "detail": str(exc)}])
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
