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
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

MANIFEST_NAME = "fixture-manifest.json"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
CANONICAL_ITEM_KEY = "AAAA1111"
STAGE0_TARGET_RELATIVE = Path(f"教授研究/X分野/{PROFESSOR}/套磁目标.json")
PROGRAM_STAGE_OUTPUTS = (
    STAGE0_TARGET_RELATIVE, Path("教授研究/套磁选择.json"), Path("教授研究/邮件输入.json"),
)
PROFESSOR_STAGE_OUTPUTS = (
    Path("套磁阶段1候选.json"),
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
INSTALL_REQUIRED_FILES = (
    ".agents/skills/professor-contact/SKILL.md",
    ".agents/skills/professor-contact/scripts/contact_state.py",
    ".codex/agents/professor-contact.toml",
    ".codex/agents/professor-contact-idea-generator.toml",
    ".codex/agents/professor-contact-style-validator.toml",
    ".codex/agents/professor-contact-email-generator.toml",
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
    # PC67-RISO drives one real explicit-selection Stage-4 call, so a clean
    # consumer must carry the isolation fixture and its frozen prompt.
    ".agents/skills/professor-contact/tests/runtime/prepare_issue67_stage4_isolation_fixture.py",
    ".agents/skills/professor-contact/tests/runtime/prompts/issue67-stage4-isolation.txt",
)
STAGE4_PROGRAM_OUTPUTS = {
    "套磁选择.json": Path("教授研究/套磁选择.json"),
    "邮件输入.json": Path("教授研究/邮件输入.json"),
}
# Issue #67 PC67-RISO grades one explicit-selection Stage-4 call from file
# bytes and formal delegation evidence only: the professor-local pair is schema
# 3 and the legacy program-level container keeps its schema-2 identity.
ISSUE67_FIXTURE_BUILDER = "tests/runtime/prepare_issue67_stage4_isolation_fixture.py"
ISSUE67_PROMPT_NAME = "issue67-stage4-isolation.txt"
ISSUE67_FORBIDDEN_REQUEST_TOKENS = ("network_access", "ZOTERO", "CHROME", "NPM",
                                    "agents.max_concurrent")
ISSUE67_REQUEST_ARGV_PREFIX = ("--json", "--skip-git-repo-check",
                               "--sandbox", "workspace-write")
ISSUE67_REQUEST_MODEL = "gpt-5.6-luna"
ISSUE67_REQUEST_REASONING = "low"
INPUT_PACK_SCHEMA = 2
CANDIDATE_STATE_SCHEMA = 2
STAGE4_LOCAL_SCHEMA = 3
SELECTION_KIND = "professor-contact-selection"
EMAIL_PACK_KIND = "professor-contact-email-input"
LOCAL_SELECTION_FILE = "套磁选择.json"
LOCAL_EMAIL_PACK_FILE = "邮件输入.json"
LOCAL_INPUT_PACK_FILE = "套磁候选输入.json"
LOCAL_CANDIDATE_STATE_FILE = "套磁候选状态.json"
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
    item_keys = manifest.get("item_keys")
    valid_item_keys = (isinstance(item_keys, list) and len(item_keys) == 1
                       and isinstance(item_keys[0], str) and item_keys[0])
    _check(checks, "item_keys", valid_item_keys, item_keys)
    _check(checks, "canonical_item_key",
           valid_item_keys and manifest.get("canonical_item_key") == item_keys[0],
           manifest.get("canonical_item_key"))
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


def _runtime_item_key(root: Path) -> str:
    """Return the fixture's single canonical Zotero item key.

    The deterministic fixture keeps the historical ``CANONICAL_ITEM_KEY``
    constant, while the runtime recipe replaces it with the key returned by the
    disposable Zotero.  The manifest is the provenance source for that runtime
    key, so checkpoints must derive their expectations from it instead of
    inventing literals.
    """
    try:
        manifest = _load(root / MANIFEST_NAME)
    except (OSError, json.JSONDecodeError):
        return CANONICAL_ITEM_KEY
    keys = manifest.get("item_keys")
    if (isinstance(keys, list) and len(keys) == 1
            and isinstance(keys[0], str) and keys[0]):
        return keys[0]
    return CANONICAL_ITEM_KEY


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


def _load_toml(path: Path) -> tuple[Any | None, str | None]:
    """Parse TOML through yq, the repository's structured TOML tool."""
    try:
        completed = subprocess.run(
            ["yq", "-p=toml", "-o=json", ".", str(path)],
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
    expected.append(consumer / ".codex/agents/professor-contact-email-generator.toml")
    for path in expected:
        _check(checks, f"installed:{path.relative_to(consumer)}", path.is_file(), str(path))
        _check(checks, f"contained:{path.relative_to(consumer)}",
               path.resolve().is_relative_to(consumer), str(path.resolve()))
    generator_path = consumer / ".codex/agents/professor-contact-email-generator.toml"
    if generator_path.is_file():
        generator, error = _load_toml(generator_path)
        if error or not isinstance(generator, dict):
            _check(checks, "generated_projection_readable", False,
                   error or f"TOML root must be an object, got {type(generator).__name__}")
        else:
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
    item_key = _runtime_item_key(root)
    _check(checks, "preview_exists", (prof / "方向预筛.json").is_file())
    direction = _direction(root)
    _check(checks, "legal_direction_preview", direction is not None)
    preview_members = [row.get("item_key") for row in (direction or {}).get("members", [])
                       if isinstance(row, dict)]
    preview_representatives = [
        row.get("item_key") for row in (direction or {}).get("representatives", [])
        if isinstance(row, dict)]
    _check(checks, "preview_single_item",
           preview_members == [item_key] and preview_representatives == [item_key],
           {"members": preview_members, "representatives": preview_representatives})
    try:
        papers = _load(prof / "papers.json").get("papers", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        papers = []
    by_key = {row.get("item_key"): row for row in papers if isinstance(row, dict)}
    _check(checks, "catalog_keys", list(by_key) == [item_key], list(by_key))
    catalog_row = by_key.get(item_key, {})
    _check(checks, "catalog_pdf_pending",
           catalog_row.get("pdf_status") == "pending" and not catalog_row.get("pdf_path"),
           catalog_row)
    local_pdfs = sorted(path.name for path in (prof / "论文分析").glob("*.pdf"))
    _check(checks, "no_prebuilt_local_pdf", not local_pdfs, local_pdfs)
    _check(checks, "profile_inputs", all((Path(manifest["profile_root"]) / name).is_file() for name in
                                          ("套磁邮件/套磁信息.md", "套磁邮件/套磁模板.md", "套磁邮件/套磁跟进模板.md")))
    _check(checks, "legal_application_inputs", (root / "info.json").is_file()
           and (root / "boshu_analysis.json").is_file())
    contact_fixture = root / "教授研究/contact-evidence-fixture-input.json"
    professor_candidates = root / "教授研究/_professor_candidates.json"
    raw_contact_ok = contact_fixture.is_file() and professor_candidates.is_file() \
        and not (root / "教授研究/_联系方式证据.json").exists()
    if raw_contact_ok:
        try:
            fixture_contact = _load(contact_fixture)
            candidate_rows = _load(professor_candidates)
            expected_email = str(
                ((fixture_contact.get("official_only") or {}).get("email") or "")
            ).strip()
            raw_contact_ok = bool(expected_email) and any(
                isinstance(row, dict)
                and row.get("name") == fixture_contact.get("professor")
                and row.get("email") == expected_email
                for row in candidate_rows
            )
        except (OSError, json.JSONDecodeError, AttributeError):
            raw_contact_ok = False
    _check(checks, "raw_contact_prerequisite", raw_contact_ok)
    for relative in PROGRAM_STAGE_OUTPUTS:
        _check(checks, f"product_output_absent:{relative.as_posix()}", not (root / relative).exists())
    for relative in PROFESSOR_STAGE_OUTPUTS:
        _check(checks, f"product_output_absent:{relative.as_posix()}",
               not (_professor_dir(root) / relative).exists())
    _check(checks, "no_prebuilt_analysis", not list((prof / "论文分析").glob("*.md"))
           and not list((prof / "论文分析").glob("*.future_work.json")))
    return _finish(checks, professor=PROFESSOR, direction_id=DIRECTION_ID,
                   item_keys=sorted(by_key))


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
    path = root / STAGE0_TARGET_RELATIVE
    try:
        payload = _load(path)
        if payload.get("professor") != PROFESSOR:
            raise ValueError(f"target professor mismatch: {payload.get('professor')!r}")
        target = payload
    except (OSError, json.JSONDecodeError, AttributeError, ValueError) as exc:
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
    item_key = _runtime_item_key(root)
    snapshot_path = prof / "套磁阶段1候选.json"
    try:
        snapshot = _load(snapshot_path)
        papers = _load(prof / "papers.json").get("papers", [])
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        _check(checks, "stage1_files_readable", False, str(exc))
        return _finish(checks)
    _check(checks, "snapshot_schema", snapshot.get("schema_version") == 2
           and snapshot.get("kind") == "professor-contact-stage1"
           and "professors" not in snapshot)
    _check(checks, "snapshot_professor", snapshot.get("professor") == PROFESSOR)
    direction = next((row for row in snapshot.get("directions", [])
                      if isinstance(row, dict) and row.get("direction_id") == DIRECTION_ID), None)
    _check(checks, "snapshot_direction", direction is not None)
    missing_item_keys = None
    if direction:
        _check(checks, "snapshot_members", direction.get("candidate_keys") == [item_key],
               direction.get("candidate_keys"))
        readiness = direction.get("pdf_readiness", {})
        missing_item_keys = readiness.get("missing_item_keys")
        _check(checks, "pdf_readiness",
               readiness.get("usable_item_keys") == [item_key]
               and missing_item_keys == [], readiness)
    by_key = {row.get("item_key"): row for row in papers if isinstance(row, dict)}
    _check(checks, "collector_completed",
           by_key.get(item_key, {}).get("pdf_status") == "downloaded",
           by_key.get(item_key))
    if args.eval_response:
        try:
            response = _response(args)
            collector_payloads = _structured_values(response, {"collector_payload", "collector_request", "tool_payload"})
            payloads = list(collector_payloads)
            if isinstance(response, dict):
                payloads.append(response)
            exact = any(isinstance(row, dict) and row.get("folder_path") and row.get("pdf_only") is True
                        and row.get("item_keys") == [item_key] and "professors" not in row
                        for row in payloads)
            noop = (missing_item_keys == []
                    and not collector_payloads
                    and by_key.get(item_key, {}).get("pdf_status") == "downloaded")
            _check(checks, "collector_payload_contract", noop or exact,
                   "stage1 action=noop: all candidate PDFs are downloaded" if noop else None)
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, "eval_response_readable", False, str(exc))
    return _finish(checks, snapshot_file=str(snapshot_path), papers=sorted(by_key))


def _checkpoint_stage2_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    prof = _professor_dir(root)
    item_key = _runtime_item_key(root)
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
    # Stage 2 must analyze the single canonical item Stage 1 collected, so the
    # continuity gate cannot be satisfied by a separately pre-ready paper.
    _check(checks, "analysis_for_canonical_paper",
           bool(list((prof / "论文分析").glob(f"{item_key}*.md"))))
    _check(checks, "future_work_sidecar",
           bool(list((prof / "论文分析").glob(f"{item_key}*.future_work.json"))))
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


# The pinned adapter@9 contract enumerates exactly eight fixture statuses
# (skills-test-fixtures@88d2056, FIXTURE_STATUSES), each with its own
# semantics, so the prerequisite is a frozen status matrix instead of an
# allowlist-plus-catch-all: identity diagnostics never gate, harness and
# dependency blockers are NOT TESTED, and only corrupted adapter evidence
# — or a status outside the pinned contract — is INVALID.
ADAPTER_STATUS_VERDICTS: dict[str, tuple[str, str] | None] = {
    "FIXTURE_READY": None,
    "HARNESS_DISPATCH_UNCONFIRMED": None,
    "HARNESS_DISPATCH_MISMATCH": None,
    "BLOCKED_DEPENDENCY": ("blocked", "BLOCKED_RUNTIME_PROVIDER"),
    "HARNESS_ERROR": ("blocked", "BLOCKED_RUNTIME_PROVIDER"),
    "HARNESS_CONTAMINATION": ("blocked", "BLOCKED_RUNTIME_PROVIDER"),
    "NOT_RUN": ("blocked", "BLOCKED_RUNTIME_PROVIDER"),
    "INVALID_EVIDENCE": ("invalid", "INVALID_TEST_EXECUTION"),
}


def _adapter_prerequisite_block(
        adapter: Any, checks: list[dict[str, Any]]) -> tuple[str, str] | None:
    """adapter@9's frozen fixture-status prerequisite, evaluated before any
    delegation or relation topology is interpreted.

    ``FIXTURE_READY`` and the two named-role identity diagnostics
    (``HARNESS_DISPATCH_UNCONFIRMED`` / ``HARNESS_DISPATCH_MISMATCH``) let
    the checkpoint proceed — identity is non-gating and never downgrades a
    confirmed delegation.  ``BLOCKED_DEPENDENCY`` (for example a null
    ``codex_version``), ``HARNESS_ERROR`` (fixture/wiring error),
    ``HARNESS_CONTAMINATION`` (evidence sourced outside the allowed roots),
    and ``NOT_RUN`` are provider/harness-side blockers: blocked / NOT
    TESTED, never a producer FAIL and never INVALID_TEST_EXECUTION.  Only
    ``INVALID_EVIDENCE`` — input evidence corrupt, stale, or mismatched —
    plus a status outside the frozen contract (unknown or missing) is
    malformed adapter evidence.  Returns the early-exit
    ``(status, classification)`` or ``None`` when the prerequisite passes.
    """
    fixture_status = adapter.get("fixture_status") if isinstance(adapter, dict) else None
    if isinstance(fixture_status, str) and fixture_status in ADAPTER_STATUS_VERDICTS:
        early = ADAPTER_STATUS_VERDICTS[fixture_status]
    else:
        early = ("invalid", "INVALID_TEST_EXECUTION")
    if early is None:
        return None
    check_name = ("adapter_invalid_evidence" if fixture_status == "INVALID_EVIDENCE"
                  else "adapter_prerequisite" if early[0] == "blocked"
                  else "adapter_fixture_status")
    _check(checks, check_name, False, {"fixture_status": fixture_status})
    return early


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


def _file_state(path: Path) -> dict[str, Any]:
    exists = Path(path).is_file()
    return {"exists": exists, "sha256": _sha256(path) if exists else None}


def _canonical_dir(value: Any) -> str:
    """Canonical professor_dir identity: the resolved path, never a name."""
    return str(Path(str(value or "")).resolve())


def _canonical_input_pack(document: Any) -> tuple[bool, Any]:
    """Structural check of the shipped canonical v2 input-pack contract."""
    if not isinstance(document, dict):
        return False, "not_object"
    if (document.get("schema") != INPUT_PACK_SCHEMA
            or document.get("kind") != INPUT_PACK_KIND
            or document.get("identity_version") != DIRECTION_IDENTITY_VERSION):
        return False, {"schema": document.get("schema"), "kind": document.get("kind"),
                       "identity_version": document.get("identity_version")}
    if not str(document.get("professor") or "").strip() \
            or not str(document.get("professor_dir") or "").strip():
        return False, "missing_pack_professor_identity"
    papers = document.get("papers")
    directions = document.get("directions")
    if not isinstance(papers, dict) or not isinstance(directions, list) or not directions:
        return False, "missing_pack_papers_or_directions"
    ids: list[str] = []
    fingerprints: dict[str, str] = {}
    for row in directions:
        if not isinstance(row, dict):
            return False, "pack_direction_not_object"
        direction_id = row.get("direction_id")
        if not isinstance(direction_id, str) or not direction_id.strip():
            return False, "pack_direction_without_machine_identity"
        ids.append(direction_id)
        fingerprint = row.get("input_fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            return False, {"direction_id": direction_id, "reason": "missing_input_fingerprint"}
        fingerprints[direction_id] = fingerprint
        for key in row.get("supporting_item_keys") or []:
            if key not in papers:
                return False, {"direction_id": direction_id,
                               "reason": "unresolved_supporting_item_key", "item_key": key}
    if len(set(ids)) != len(ids):
        return False, "duplicate_pack_direction_id"
    return True, {"direction_ids": ids, "input_fingerprints": fingerprints,
                  "professor": document.get("professor"), "item_keys": sorted(papers)}


def _canonical_candidate_state(document: Any, pack: Any, profile_sha: str | None,
                              ) -> tuple[bool, Any]:
    """Structural check of the shipped canonical v2 candidate-state contract.

    A state that fails here is exactly the malformed-bytes condition the #67
    isolation fixture freezes for professor B: the producer can only fail that
    professor and must leave these bytes untouched.
    """
    if not isinstance(document, dict):
        return False, "not_object"
    if (document.get("schema") != CANDIDATE_STATE_SCHEMA
            or document.get("kind") != CANDIDATE_STATE_KIND
            or document.get("identity_version") != DIRECTION_IDENTITY_VERSION
            or document.get("generator_contract_version")
            != STAGE3_GENERATOR_CONTRACT_VERSION):
        return False, {"schema": document.get("schema"), "kind": document.get("kind"),
                       "identity_version": document.get("identity_version"),
                       "generator_contract_version": document.get("generator_contract_version")}
    if not isinstance(profile_sha, str) or document.get("profile_fingerprint") != profile_sha:
        return False, {"reason": "profile_fingerprint_mismatch",
                       "observed": document.get("profile_fingerprint")}
    if not isinstance(pack, dict):
        return False, "pack_unavailable_for_join"
    pack_directions = {row["direction_id"]: row.get("input_fingerprint")
                       for row in pack.get("directions") or [] if isinstance(row, dict)}
    directions = document.get("directions")
    if not isinstance(directions, list) or not directions:
        return False, "missing_state_directions"
    state_ids: list[str] = []
    idea_ids: dict[str, list[str]] = {}
    for row in directions:
        if not isinstance(row, dict):
            return False, "state_direction_not_object"
        direction_id = row.get("direction_id")
        if not isinstance(direction_id, str) or direction_id not in pack_directions:
            return False, {"reason": "state_direction_outside_pack",
                           "direction_id": direction_id}
        state_ids.append(direction_id)
        candidates = row.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return False, {"reason": "missing_state_candidates", "direction_id": direction_id}
        ideas: list[str] = []
        for candidate in candidates:
            if not isinstance(candidate, dict) or not str(candidate.get("id") or "").strip():
                return False, {"reason": "candidate_without_id", "direction_id": direction_id}
            ideas.append(str(candidate["id"]))
        idea_ids[direction_id] = ideas
    fingerprints = document.get("input_fingerprints")
    if not isinstance(fingerprints, dict):
        return False, "missing_state_input_fingerprints"
    for direction_id in state_ids:
        if fingerprints.get(direction_id) != pack_directions[direction_id]:
            return False, {"reason": "state_pack_fingerprint_mismatch",
                           "direction_id": direction_id}
    return True, {"direction_ids": state_ids, "idea_ids": idea_ids}


def _issue67_manifest(path: Path, root: Path, checks: list[dict[str, Any]],
                      ) -> dict[str, Any] | None:
    """Load the frozen isolation manifest and prove it describes this program."""
    try:
        manifest = _load(Path(path))
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "fixture_manifest_readable", False, str(exc))
        return None
    if not isinstance(manifest, dict):
        _check(checks, "fixture_manifest_object", False, type(manifest).__name__)
        return None
    _check(checks, "fixture_builder", manifest.get("builder") == ISSUE67_FIXTURE_BUILDER,
           manifest.get("builder"))
    _check(checks, "fixture_kind", manifest.get("fixture_kind") == "stage4-isolation",
           manifest.get("fixture_kind"))
    _check(checks, "program_root_matches",
           _canonical_dir(manifest.get("program_root")) == str(root),
           {"manifest": manifest.get("program_root"), "observed": str(root)})
    _check(checks, "manual_patch_absent", manifest.get("manual_patch") == "no",
           manifest.get("manual_patch"))
    installed_builder = Path(__file__).with_name(Path(ISSUE67_FIXTURE_BUILDER).name)
    _check(checks, "installed_builder_is_the_manifest_builder",
           installed_builder.is_file() and _sha256(installed_builder) == manifest.get("builder_sha256"),
           {"installed": str(installed_builder), "pinned": manifest.get("builder_sha256")})
    if any(row["status"] == "fail" for row in checks):
        return None
    return manifest


def _issue67_fixture_facts(root: Path, manifest: dict[str, Any],
                           checks: list[dict[str, Any]], *,
                           expect_local_pairs_absent: bool) -> dict[str, Any] | None:
    """Prove the frozen fixture's single-fault precondition from current bytes.

    The fault under test is exactly one non-canonical canonical candidate-state
    file in professor B's directory while every other declared fixture input
    stays canonical.  A preparer that moves that single fault onto another file
    breaks this precondition, so the oracle reports a broken test run instead of
    grading a product claim.
    """
    entries = manifest.get("professors")
    if not isinstance(entries, list) or len(entries) != 2:
        _check(checks, "fixture_two_professors", False, entries)
        return None
    entries = [row for row in entries if isinstance(row, dict)]
    faults = [row for row in entries
              if (row.get("candidate_state") or {}).get("canonical") is False]
    _check(checks, "fixture_single_fault", len(faults) == 1,
           {"faults": len(faults), "roles": [row.get("role") for row in entries]})
    if len(faults) != 1:
        return None
    fault = faults[0]
    _check(checks, "fixture_fault_role", fault.get("role") == "malformed_candidate_state",
           fault.get("role"))
    _check(checks, "fixture_fault_is_candidate_state",
           (fault.get("candidate_state") or {}).get("relative_path")
           == LOCAL_CANDIDATE_STATE_FILE,
           (fault.get("candidate_state") or {}).get("relative_path"))
    profile_sha = manifest.get("profile_sha256")
    _check(checks, "fixture_profile_matches_manifest",
           isinstance(profile_sha, str)
           and _file_state(Path(manifest.get("profile_file") or ""))["sha256"] == profile_sha,
           {"profile_file": manifest.get("profile_file")})
    facts: dict[str, Any] = {}
    for entry in entries:
        directory = Path(entry.get("professor_dir") or "")
        canonical = _canonical_dir(directory)
        pack_path = directory / LOCAL_INPUT_PACK_FILE
        state_path = directory / LOCAL_CANDIDATE_STATE_FILE
        _check(checks, f"fixture_professor_dir_canonical[{canonical}]",
               canonical == (entry.get("canonical_professor_dir") or "")
               and directory.is_dir()
               and Path(str(root / "教授研究")) in Path(canonical).parents,
               {"declared": entry.get("canonical_professor_dir"), "observed": canonical})
        _check(checks, f"fixture_professor_input_hashes[{canonical}]",
               _file_state(pack_path)["sha256"] == (entry.get("input_pack") or {}).get("sha256")
               and _file_state(state_path)["sha256"]
               == (entry.get("candidate_state") or {}).get("sha256"),
               {"input_pack": _file_state(pack_path), "candidate_state": _file_state(state_path)})
        try:
            pack_document = _load(pack_path)
            state_document = _load(state_path)
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, f"fixture_professor_inputs_readable[{canonical}]", False, str(exc))
            continue
        pack_ok, pack_detail = _canonical_input_pack(pack_document)
        state_ok, state_detail = _canonical_candidate_state(state_document,
                                                            pack_document, profile_sha)
        declared = (entry.get("candidate_state") or {}).get("canonical")
        _check(checks, f"fixture_input_pack_canonical[{canonical}]", pack_ok, pack_detail)
        _check(checks, f"fixture_candidate_state_canonical_matches_declaration[{canonical}]",
               state_ok is bool(declared),
               {"declared": declared, "observed": state_ok, "detail": state_detail})
        selection_state = _file_state(directory / LOCAL_SELECTION_FILE)
        email_state = _file_state(directory / LOCAL_EMAIL_PACK_FILE)
        if expect_local_pairs_absent:
            _check(checks, f"fixture_local_pair_absent[{canonical}]",
                   not selection_state["exists"] and not email_state["exists"],
                   {"selection": selection_state, "email_pack": email_state})
        facts[canonical] = {
            "role": entry.get("role"),
            "professor": entry.get("professor"),
            "idea_id": entry.get("idea_id"),
            "direction_id": entry.get("direction_id"),
            "directory": canonical,
            "input_pack": _file_state(pack_path),
            "candidate_state": _file_state(state_path),
            "selection_file": selection_state,
            "email_pack": email_state,
            "pack_document": pack_document,
            "pack_facts": pack_detail,
            "state_document": state_document,
            "state_facts": state_detail,
            "state_canonical": bool(state_ok),
        }
    _check(checks, "fixture_fault_is_the_only_non_canonical_state",
           len(facts) == len(entries)
           and [row for row in facts.values() if not row["state_canonical"]]
           and all(row["state_canonical"] for key, row in facts.items()
                   if key != _canonical_dir(fault.get("professor_dir"))),
           {"fault": _canonical_dir(fault.get("professor_dir")),
            "non_canonical": [key for key, row in facts.items() if not row["state_canonical"]]})
    if any(row["status"] == "fail" for row in checks):
        return None
    return {"manifest": manifest, "fault_dir": _canonical_dir(fault.get("professor_dir")),
            "fault_sha256": (fault.get("candidate_state") or {}).get("sha256"),
            "profile_sha256": profile_sha, "professors": facts}


def _issue67_isolation_pre_state(root: Path, manifest_path: Path
                                ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Snapshot the per-professor pre-run state the isolation oracle needs."""
    checks: list[dict[str, Any]] = []
    manifest = _issue67_manifest(manifest_path, root, checks)
    if manifest is None:
        return None, checks
    facts = _issue67_fixture_facts(root, manifest, checks, expect_local_pairs_absent=True)
    if facts is None:
        return None, checks
    professors = {
        canonical: {key: row[key] for key in
                    ("professor", "idea_id", "direction_id", "input_pack", "candidate_state",
                     "selection_file", "email_pack")}
        for canonical, row in facts["professors"].items()}
    return {
        "builder": manifest.get("builder"),
        "manifest_sha256": _sha256(Path(manifest_path)),
        "program_root": str(root),
        "professors": professors,
        "fault": {"professor_dir": facts["fault_dir"],
                  "relative_path": LOCAL_CANDIDATE_STATE_FILE,
                  "sha256": facts["fault_sha256"]},
    }, checks


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
    payload: dict[str, Any] = {
        "status": "pass" if all(row["status"] == "pass" for row in checks) else "fail",
        "checks": checks,
        "artifacts": artifacts,
    }
    manifest_path = getattr(args, "fixture_manifest", None)
    if manifest_path:
        isolation, isolation_checks = _issue67_isolation_pre_state(
            root, Path(manifest_path))
        payload["checks"].extend(isolation_checks)
        payload["isolation_pre"] = isolation
        payload["status"] = "pass" if all(row["status"] == "pass"
                                         for row in payload["checks"]) else "fail"
    return payload


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
    """Verify the PC53 child-attributed Stage-4 Path-C evidence.

    Snapshot evidence is classified by attribution, per the frozen #57
    verdict table: a pre snapshot that is not all-absent is precondition
    pollution that can never be blamed on this run
    (``INVALID_TEST_EXECUTION``), a post snapshot that disagrees with the
    current artifacts is stale or tampered evidence
    (``INVALID_TEST_EXECUTION``), and only consistent evidence showing
    Stage-4 outputs after a clean pre state proves the omitted-selection
    path wrote them (``FAIL_PRODUCT``).  The adapter prerequisite is
    decided before that product-write attribution: a harness/provider
    blocker or corrupted adapter evidence preempts the feature verdict,
    while named-role identity diagnostics stay non-gating.
    """
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
    current = _stage4_artifacts(root)

    # Step 1: the pre snapshot must prove a clean initial state.  Outputs
    # that already existed before this run are stale/polluted fixture
    # state, so the write cannot be attributed to the omitted-selection
    # path and is never a producer FAIL.
    pre_absent = pre == expected_absent
    _check(checks, "pre_zero_write_snapshot", pre_absent, pre)
    if not pre_absent:
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # Step 2: the post snapshot must still match the current filesystem —
    # same existence and same content hashes.  Any drift means the
    # snapshot evidence is stale or was tampered with after the run.
    post_consistent = post == current
    _check(checks, "post_snapshot_matches_current", post_consistent,
           {"post": post, "current": current})
    if not post_consistent:
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # Step 3: the adapter prerequisite is decided before any feature
    # attribution.  A harness/provider blocker or corrupted adapter
    # evidence outranks the product-write observation — under
    # HARNESS_CONTAMINATION the evidence sources themselves are outside
    # the allowed roots, so this run's filesystem writes can no longer be
    # trusted as a producer FAIL — while named-role identity diagnostics
    # stay non-gating and never excuse a real product write.
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

    # Step 4: with valid pre/post/current evidence and a passed
    # prerequisite, outputs present after the run are positively
    # attributed to this run's omitted-selection path.
    zero_write = current == expected_absent
    _check(checks, "current_zero_write", zero_write, current)
    if not zero_write:
        return machine("fail", "FAIL_PRODUCT")

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

    def business_message_row(item: Any) -> tuple[str, dict[str, Any] | None] | None:
        """One ``(state, parsed)`` row for a completed assistant message
        item, or ``None`` for items outside the pinned business surface."""
        if not isinstance(item, dict) or item.get("type") != "message" or item.get("role") != "assistant":
            # A child thread emits developer, user, reasoning, and tool
            # items as well.  The contract pins business-result parsing to
            # assistant output_text messages only.
            return None
        content = item.get("content")
        if not isinstance(content, list):
            return ("malformed", None)
        texts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if not isinstance(text, str):
                    return ("malformed", None)
                texts.append(text)
        if not texts:
            return None
        try:
            parsed = json.loads("".join(texts))
        except (TypeError, json.JSONDecodeError):
            return ("not_json", None)
        return ("object", parsed) if isinstance(parsed, dict) else ("not_json", None)

    def child_messages(child_id: str) -> list[tuple[str, dict[str, Any] | None]]:
        """Every supported business message of one child thread, in
        arrival order.

        The frozen PC57 verdict counts business JSONs, not children, and
        makes each observable business message load-bearing: no later
        message may repair or mask an earlier malformed or wrong one, so
        the rows are never collapsed into a last-wins parse.
        """
        rows: list[tuple[str, dict[str, Any] | None]] = []
        for event in events:
            message = event.get("message") if isinstance(event, dict) else None
            if not isinstance(message, dict):
                continue
            if message.get("method") != "rawResponseItem/completed":
                continue
            params = message.get("params")
            if not isinstance(params, dict) or params.get("threadId") != child_id:
                continue
            row = business_message_row(params.get("item"))
            if row is not None:
                rows.append(row)
        return rows

    observed: dict[str, list[tuple[str, dict[str, Any] | None]]] = {
        child: child_messages(child) for child in sorted(direct_children)
    }
    _check(checks, "child_message_surface",
           any(rows for rows in observed.values()), observed)
    if all(not rows for rows in observed.values()):
        return machine("blocked", "BLOCKED_OBSERVABILITY")

    # Every observed business message is a product statement in its own
    # right: a malformed message, a non-JSON message, or a wrong-result
    # object is already a violation, and more than one Path-C result —
    # repeated in one child or spread over children — is a duplicate.
    path_c_results: list[tuple[str, dict[str, Any]]] = []
    for child, rows in observed.items():
        for state, parsed in rows:
            if state == "object" and isinstance(parsed, dict) \
                    and parsed.get("result") == "needs_input":
                path_c_results.append((child, parsed))
                continue
            _check(checks, "child_business_results_supported", False,
                   {"child_thread_id": child, "observed": parsed if state == "object" else state})
            return machine("fail", "FAIL_PRODUCT")
    if len(path_c_results) != 1:
        _check(checks, "exactly_one_path_c_result", False,
               [child for child, _ in path_c_results])
        return machine("fail", "FAIL_PRODUCT")
    target_child_id, business_result = path_c_results[0]
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


def _is_sha(value: Any, length: int = 64) -> bool:
    return isinstance(value, str) and len(value) == length \
        and all(char in "0123456789abcdef" for char in value)


def _issue67_input_sha_records(path: Path) -> dict[str, str]:
    """Parse ``shasum -a 256`` output into ``{recorded path: sha256}``."""
    records: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, separator, recorded = line.partition(" ")
        if not separator or not _is_sha(digest):
            raise ValueError(f"unparsable sha256 line: {line!r}")
        records[recorded.strip()] = digest
    return records


def _issue67_local_identity_values(*documents: Any) -> set[str]:
    """Every machine identifier a Stage-4 container asserts, as strings."""
    values: set[str] = set()
    for document in documents:
        if not isinstance(document, dict):
            continue
        for key in ("email_id", "collection_key"):
            if document.get(key):
                values.add(str(document[key]))
        for key in ("direction_ids",):
            values.update(str(item) for item in document.get(key) or [])
        rows = document.get("selections") or document.get("emails") or []
        if isinstance(rows, list):
            for row in rows:
                values.update(_issue67_local_identity_values(row))
        values.update(_issue67_local_identity_values(document.get("idea")))
    return values


def _checkpoint_stage4_professor_isolation(args: argparse.Namespace) -> dict[str, Any]:
    """Grade PC67-RISO: one professor's fault must stay that professor's own.

    Every claim is decided from file bytes and the adapter's formal spawn
    relations: the valid professor's professor-local pair must exist and agree
    with the current candidate state and input pack, the fault professor's pair
    must be absent, the fault professor's frozen malformed candidate-state
    bytes must be untouched, and the legacy program-level Stage-4 pair must be
    byte-identical and never promoted into local authority.  Model prose is
    never evidence.
    """
    checks: list[dict[str, Any]] = []
    given_root = Path(args.program_root)
    root = given_root.resolve()
    observed: dict[str, Any] = {"program_root": str(root)}

    def machine(status: str, classification: str) -> dict[str, Any]:
        return {"status": status, "classification": classification,
                "checks": checks, "observed": observed}

    def phase_failed() -> bool:
        return any(row["status"] == "fail" for row in checks)

    # Phase A: the recipe's frozen evidence set must all be present.
    supplied = {
        "fixture_manifest": getattr(args, "fixture_manifest", None),
        "pre_snapshot": getattr(args, "pre_snapshot", None),
        "eval_request": getattr(args, "eval_request", None),
        "input_sha256": getattr(args, "input_sha256", None),
        "eval_response": getattr(args, "eval_response", None),
        "adapter_output": getattr(args, "adapter_output", None),
        "install_verdict": getattr(args, "install_verdict", None),
    }
    _check(checks, "evidence_supplied",
           not [name for name, value in supplied.items() if not value],
           sorted(name for name, value in supplied.items() if not value))
    _check(checks, "producer_sha_wellformed", _is_sha(args.producer_sha or "", 40),
           args.producer_sha)
    _check(checks, "fixture_sha_wellformed",
           _is_sha(getattr(args, "fixture_sha", "") or "", 40),
           getattr(args, "fixture_sha", ""))
    if phase_failed():
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # Phase B: the frozen fixture manifest describes this program root.
    manifest = _issue67_manifest(Path(supplied["fixture_manifest"]), root, checks)
    if manifest is None:
        return machine("invalid", "INVALID_TEST_EXECUTION")
    observed["display_name"] = manifest.get("display_name")

    # Phase C: the pre snapshot was taken from this manifest, before any write.
    try:
        pre = _load(Path(supplied["pre_snapshot"]))
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "pre_snapshot_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")
    isolation_pre = pre.get("isolation_pre") if isinstance(pre, dict) else None
    _check(checks, "pre_snapshot_carries_isolation_pre", isinstance(isolation_pre, dict),
           type(isolation_pre).__name__)
    if not isinstance(isolation_pre, dict):
        return machine("invalid", "INVALID_TEST_EXECUTION")
    _check(checks, "pre_snapshot_is_for_this_manifest",
           isolation_pre.get("builder") == ISSUE67_FIXTURE_BUILDER
           and isolation_pre.get("manifest_sha256")
           == _sha256(Path(supplied["fixture_manifest"]))
           and _canonical_dir(isolation_pre.get("program_root")) == str(root),
           {"builder": isolation_pre.get("builder"),
            "manifest_sha256": isolation_pre.get("manifest_sha256"),
            "program_root": isolation_pre.get("program_root")})
    expected_legacy = {
        name: (manifest.get("legacy_program_pair") or {}).get(relative.as_posix())
        for name, relative in STAGE4_PROGRAM_OUTPUTS.items()}
    observed_legacy = {
        name: (row or {}).get("sha256")
        for name, row in (pre.get("artifacts") or {}).items()}
    _check(checks, "pre_snapshot_legacy_program_pair_pinned",
           observed_legacy == expected_legacy and all(_is_sha(value)
                                                      for value in expected_legacy.values()),
           {"expected": expected_legacy, "observed": observed_legacy})
    _check(checks, "pre_snapshot_fault_pinned",
           (isolation_pre.get("fault") or {}).get("sha256")
           == (manifest.get("fault") or {}).get("sha256")
           and (isolation_pre.get("fault") or {}).get("relative_path")
           == LOCAL_CANDIDATE_STATE_FILE,
           {"pre": isolation_pre.get("fault"), "manifest": manifest.get("fault")})
    _check(checks, "pre_snapshot_professor_set_matches_manifest",
           set(isolation_pre.get("professors") or {})
           == {(row.get("canonical_professor_dir") or "")
               for row in manifest.get("professors") or []},
           {"pre": sorted(isolation_pre.get("professors") or {}),
            "manifest": sorted(str(row.get("canonical_professor_dir") or "")
                               for row in manifest.get("professors") or [])})
    if phase_failed():
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # Phase D: exact-SHA install and provenance, re-derived from the lock.
    try:
        install = _load(Path(supplied["install_verdict"]))
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "install_verdict_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")
    install_rows = install.get("checks") if isinstance(install, dict) else None
    _check(checks, "install_verdict_pass",
           isinstance(install, dict) and install.get("status") == "pass"
           and isinstance(install_rows, list) and bool(install_rows)
           and all(isinstance(row, dict) and row.get("status") == "pass"
                   for row in install_rows),
           {"status": install.get("status") if isinstance(install, dict) else None,
            "failed": [row.get("name") for row in install_rows or []
                       if isinstance(row, dict) and row.get("status") != "pass"]})
    pinned_row = next((row for row in install_rows or [] if isinstance(row, dict)
                       and row.get("name") == "producer_sha_pinned"), None)
    _check(checks, "install_verdict_pinned_producer_sha",
           isinstance(pinned_row, dict) and pinned_row.get("status") == "pass", pinned_row)
    consumer = Path(str((install.get("observed") or {}).get("consumer_root")
                        if isinstance(install, dict) else "") or "")
    if consumer.is_dir():
        resolved_commit, source = _resolved_professor_contact_commit(consumer)
    else:
        resolved_commit, source = None, f"consumer root missing: {consumer}"
    _check(checks, "install_provenance_rederived",
           resolved_commit == args.producer_sha,
           {"expected": args.producer_sha, "observed": resolved_commit, "source": source})
    observed["consumer_root"] = str(consumer)
    observed["producer_sha"] = args.producer_sha
    observed["fixture_sha"] = getattr(args, "fixture_sha", "")
    if phase_failed():
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # Phase E: the frozen inputs the run consumed are the ones hashed upfront.
    try:
        records = _issue67_input_sha_records(Path(supplied["input_sha256"]))
    except (OSError, ValueError) as exc:
        _check(checks, "input_sha256_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")
    _check(checks, "input_sha256_records_stable",
           all(digest == _file_state(Path(recorded))["sha256"]
               for recorded, digest in records.items()),
           {recorded: {"recorded": digest, "observed": _file_state(Path(recorded))["sha256"]}
            for recorded, digest in records.items()
            if digest != _file_state(Path(recorded))["sha256"]})
    required_names = {Path(supplied["fixture_manifest"]).name,
                      Path(supplied["pre_snapshot"]).name, ISSUE67_PROMPT_NAME,
                      Path(supplied["eval_request"]).name}
    _check(checks, "input_sha256_covers_frozen_inputs",
           required_names <= {Path(recorded).name for recorded in records},
           sorted(Path(recorded).name for recorded in records))
    prompt_paths = [recorded for recorded in records
                    if Path(recorded).name == ISSUE67_PROMPT_NAME]
    _check(checks, "input_sha256_names_one_prompt", len(prompt_paths) == 1, prompt_paths)
    if phase_failed():
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # Phase F: the eval request carries only the frozen command surface, and its
    # prompt is the substituted frozen prompt for this program root.
    try:
        request = _load(Path(supplied["eval_request"]))
        prompt_text = Path(prompt_paths[0]).read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "eval_request_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")
    command = request.get("command") if isinstance(request, dict) else None
    timeout = request.get("timeout") if isinstance(request, dict) else None
    _check(checks, "eval_request_shape",
           isinstance(command, str) and isinstance(timeout, int) and timeout > 0,
           {"command": command, "timeout": timeout})
    if phase_failed():
        return machine("invalid", "INVALID_TEST_EXECUTION")
    argv = shlex.split(command)
    for forbidden in ISSUE67_FORBIDDEN_REQUEST_TOKENS:
        _check(checks, f"eval_request_excludes[{forbidden}]", forbidden not in command,
               forbidden)
    trust_config = "projects={" + json.dumps(str(consumer)) + '={trust_level="trusted"}}'
    expected_configs = ["features.multi_agent_v2.enabled=true",
                        f'model_reasoning_effort="{ISSUE67_REQUEST_REASONING}"',
                        trust_config]
    expected_argv = [*ISSUE67_REQUEST_ARGV_PREFIX, "--cd", str(consumer),
                     "--model", ISSUE67_REQUEST_MODEL]
    for config in expected_configs:
        expected_argv.extend(["--config", config])
    expected_argv.extend(["--", prompt_text])
    _check(checks, "eval_request_command_surface", argv == expected_argv, argv[:8])
    configs = [argv[index + 1] for index, item in enumerate(argv) if item == "--config"]
    _check(checks, "eval_request_config_surface",
           configs == expected_configs,
           configs)
    values: dict[str, str] = {}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv) and not argv[index + 1].startswith("--"):
            values.setdefault(item, argv[index + 1])
    _check(checks, "eval_request_targets_installed_consumer",
           values.get("--cd") == str(consumer)
           and values.get("--model") == ISSUE67_REQUEST_MODEL, values)
    _check(checks, "eval_request_prompt_is_frozen_prompt",
           argv[-1] == prompt_text and "<PROGRAM_ROOT>" not in prompt_text
           and any(str(root) == spelling or prompt_text.count(spelling) == 1
                   for spelling in {str(root), str(given_root)} if spelling in prompt_text)
           and all(str(row.get("relative_path")) in prompt_text
                   for row in manifest.get("professors") or []),
           {"prompt": prompt_text, "argv_tail": argv[-1],
            "relative_paths": [str(row.get("relative_path"))
                               for row in manifest.get("professors") or []]})
    if phase_failed():
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # Phase G: the product never edits a frozen fixture input.  This is decided
    # before the fixture's structural precondition so that a repaired or
    # rewritten fault file is attributed to the producer, not to the harness.
    drift = {relative: {"recorded": digest,
                        "observed": _file_state(root / relative)["sha256"]}
             for relative, digest in (manifest.get("input_hashes") or {}).items()
             if digest != _file_state(root / relative)["sha256"]}
    _check(checks, "fixture_inputs_unchanged", not drift, drift)
    fault_path = Path(str((manifest.get("fault") or {}).get("professor_dir") or "")) \
        / LOCAL_CANDIDATE_STATE_FILE
    _check(checks, "fault_professor_bytes_unchanged",
           not drift and _file_state(fault_path)["sha256"]
           == (manifest.get("fault") or {}).get("sha256"),
           {"manifest": (manifest.get("fault") or {}).get("sha256"),
            "observed": _file_state(fault_path)["sha256"]})
    _check(checks, "program_level_pair_unchanged",
           {name: _file_state(root / relative)
            for name, relative in STAGE4_PROGRAM_OUTPUTS.items()}
           == {name: {"exists": True, "sha256": digest}
               for name, digest in expected_legacy.items()},
           {name: _file_state(root / relative) for name, relative in
            STAGE4_PROGRAM_OUTPUTS.items()})
    if phase_failed():
        return machine("fail", "FAIL_PRODUCT")

    # Phase H: the frozen fixture really carries one malformed canonical
    # candidate state and nothing else.  A preparer that moved that single
    # fault onto another file makes this run ungradeable, never a PASS.
    facts = _issue67_fixture_facts(root, manifest, checks, expect_local_pairs_absent=False)
    if facts is None:
        return machine("invalid", "INVALID_TEST_EXECUTION")
    valid_dirs = [key for key, row in facts["professors"].items() if row["role"] == "valid"]
    _check(checks, "fixture_exactly_one_valid_professor", len(valid_dirs) == 1, valid_dirs)
    if phase_failed():
        return machine("invalid", "INVALID_TEST_EXECUTION")

    # Phase I: formal delegation evidence, decided before any product claim.
    try:
        adapter = _load(Path(supplied["adapter_output"]))
        response = _load(Path(supplied["eval_response"]))
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "evidence_readable", False, str(exc))
        return machine("invalid", "INVALID_TEST_EXECUTION")
    prerequisite = _adapter_prerequisite_block(adapter, checks)
    if prerequisite:
        return machine(*prerequisite)
    delegation = adapter.get("delegation")
    if not isinstance(delegation, dict):
        _check(checks, "adapter_delegation_object", False)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    delegation_state = delegation.get("state")
    if delegation_state not in ("confirmed", "unobservable"):
        _check(checks, "delegation_state", False, delegation_state)
        return machine("invalid", "INVALID_TEST_EXECUTION")
    edges, malformed = _formal_spawn_relations(adapter)
    _check(checks, "adapter_relation_shape", not malformed, malformed)
    if malformed:
        return machine("invalid", "INVALID_TEST_EXECUTION")
    expected_summary = _expected_delegation_summary(edges)
    observed_summary = {field: delegation.get(field) for field in expected_summary}
    _check(checks, "delegation_summary_consistent", observed_summary == expected_summary,
           {"observed": observed_summary, "expected": expected_summary})
    if observed_summary != expected_summary:
        return machine("invalid", "INVALID_TEST_EXECUTION")
    if delegation_state == "unobservable":
        _check(checks, "delegation_observable", False, delegation)
        return machine("blocked", "BLOCKED_OBSERVABILITY")
    output = response.get("output") if isinstance(response, dict) else None
    root_thread_id = output.get("thread_id") if isinstance(output, dict) else None
    events = output.get("app_server_events") if isinstance(output, dict) else None
    if not isinstance(root_thread_id, str) or not root_thread_id.strip() \
            or not isinstance(events, list):
        _check(checks, "raw_eval_surface", False, {
            "thread_id": root_thread_id, "events": type(events).__name__})
        return machine("invalid", "INVALID_TEST_EXECUTION")
    owners, _ = _ownership_index(edges)
    conflicts = {child: sorted(parents) for child, parents in owners.items()
                 if len(parents) != 1}
    _check(checks, "formal_ownership", not conflicts, conflicts)
    if conflicts:
        return machine("invalid", "INVALID_TEST_EXECUTION")
    direct_children = sorted({edge["receiver_thread_id"] for edge in edges
                              if edge["sender_thread_id"] == root_thread_id})
    _check(checks, "formal_root_child", bool(direct_children), direct_children)
    observed["formal_child_thread_ids"] = direct_children
    if not direct_children:
        return machine("blocked", "BLOCKED_OBSERVABILITY")

    # Phase J: the isolation product claim itself.
    a = facts["professors"][valid_dirs[0]]
    b = facts["professors"][facts["fault_dir"]]
    a_dir = Path(valid_dirs[0])
    selection_state = _file_state(a_dir / LOCAL_SELECTION_FILE)
    email_state = _file_state(a_dir / LOCAL_EMAIL_PACK_FILE)
    _check(checks, "valid_professor_local_pair_written",
           selection_state["exists"] and email_state["exists"],
           {"selection": selection_state, "email_pack": email_state})
    if not (selection_state["exists"] and email_state["exists"]):
        return machine("fail", "FAIL_PRODUCT")
    try:
        selection_doc = _load(a_dir / LOCAL_SELECTION_FILE)
        email_doc = _load(a_dir / LOCAL_EMAIL_PACK_FILE)
        legacy_selection = _load(root / STAGE4_PROGRAM_OUTPUTS["套磁选择.json"])
        legacy_pack = _load(root / STAGE4_PROGRAM_OUTPUTS["邮件输入.json"])
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "valid_professor_local_pair_readable", False, str(exc))
        return machine("fail", "FAIL_PRODUCT")
    rows = selection_doc.get("selections") if isinstance(
        selection_doc.get("selections"), list) else []
    emails = email_doc.get("emails") if isinstance(email_doc.get("emails"), list) else []
    _check(checks, "valid_professor_pair_is_professor_local_schema",
           selection_doc.get("schema") == STAGE4_LOCAL_SCHEMA
           and email_doc.get("schema") == STAGE4_LOCAL_SCHEMA
           and selection_doc.get("kind") == SELECTION_KIND
           and email_doc.get("kind") == EMAIL_PACK_KIND
           and selection_doc.get("identity_version") == DIRECTION_IDENTITY_VERSION
           and email_doc.get("identity_version") == DIRECTION_IDENTITY_VERSION,
           {"selection": {key: selection_doc.get(key)
                          for key in ("schema", "kind", "identity_version")},
            "email_pack": {key: email_doc.get(key)
                           for key in ("schema", "kind", "identity_version")}})
    scope = a["direction_id"]
    expected_email_id = f"{a['professor']}::{scope}::{a['idea_id']}"
    _check(checks, "valid_professor_pair_bound_to_canonical_professor_dir",
           all(_canonical_dir(document.get("professor_dir")) == valid_dirs[0]
               for document in (selection_doc, email_doc))
           and all(_canonical_dir(row.get("professor_dir")) == valid_dirs[0]
                   for row in rows + emails if isinstance(row, dict))
           and all(str(row.get("professor") or "") == str(a["professor"])
                   for row in rows + emails if isinstance(row, dict))
           and _canonical_dir(selection_doc.get("program_root")) == str(root)
           and _canonical_dir(email_doc.get("program_root")) == str(root),
           {"selection_dir": selection_doc.get("professor_dir"),
            "email_dir": email_doc.get("professor_dir"),
            "canonical": valid_dirs[0], "rows": [row.get("professor_dir") for row in rows],
            "emails": [row.get("professor_dir") for row in emails]})
    _check(checks, "valid_professor_pair_carries_current_profile_fingerprint",
           selection_doc.get("profile_fingerprint") == facts["profile_sha256"]
           and email_doc.get("profile_fingerprint") == facts["profile_sha256"],
           {"selection": selection_doc.get("profile_fingerprint"),
            "email_pack": email_doc.get("profile_fingerprint"),
            "expected": facts["profile_sha256"]})
    idea_ids_in_state = (a["state_facts"] or {}).get("idea_ids", {}).get(scope) or []
    _check(checks, "valid_professor_selection_matches_this_request_and_current_state",
           len(rows) == 1 and isinstance(rows[0], dict)
           and rows[0].get("direction_ids") == [scope]
           and [str(idea.get("id")) for idea in rows[0].get("ideas") or []
                if isinstance(idea, dict)] == [a["idea_id"]]
           and a["idea_id"] in idea_ids_in_state,
           {"rows": rows, "state_idea_ids": idea_ids_in_state,
            "requested": {"direction_id": scope, "idea_id": a["idea_id"]}})
    pack_direction = next((row for row in a["pack_document"].get("directions") or []
                           if isinstance(row, dict)
                           and row.get("direction_id") == scope), {})
    allowed_gap_keys = {
        (row.get("item_key"), row.get("gap_id"))
        for row in (pack_direction.get("gap_shortlist") or [])
        + (pack_direction.get("gaps_excluded") or [])
        + (pack_direction.get("completed_gap_blacklist") or [])}
    allowed_item_keys = set((a["pack_facts"] or {}).get("item_keys") or [])
    pack_fingerprints = (a["pack_facts"] or {}).get("input_fingerprints") or {}
    emails_ok = (len(emails) == 1 and all(
        isinstance(row, dict)
        and row.get("email_id") == expected_email_id
        and row.get("direction_ids") == [scope]
        and (row.get("idea") or {}).get("id") == a["idea_id"]
        and (row.get("fingerprints") or {}).get("input") == pack_fingerprints.get(scope)
        and (row.get("fingerprints") or {}).get("profile") == facts["profile_sha256"]
        and all((gap.get("item_key"), gap.get("gap_id")) in allowed_gap_keys
                for gap in row.get("gaps") or [] if isinstance(gap, dict))
        and all(paper.get("item_key") in allowed_item_keys
                for paper in row.get("papers") or [] if isinstance(paper, dict))
        for row in emails))
    _check(checks, "valid_professor_email_pack_matches_current_facts", emails_ok,
           {"expected_email_id": expected_email_id, "emails": emails,
            "allowed_gaps": sorted(str(key) for key in allowed_gap_keys),
            "input_fingerprint": pack_fingerprints.get(scope)})
    legacy_markers = _issue67_local_identity_values(legacy_selection, legacy_pack)
    local_markers = _issue67_local_identity_values(selection_doc, email_doc)
    promoted = sorted(value for value in local_markers & legacy_markers
                      if value not in {str(a["professor"])})
    _check(checks, "legacy_program_pair_not_promoted_into_local_authority",
           not promoted, {"legacy_markers": sorted(legacy_markers), "promoted": promoted})
    _check(checks, "fault_professor_local_pair_absent",
           not b["selection_file"]["exists"] and not b["email_pack"]["exists"],
           {"selection": b["selection_file"], "email_pack": b["email_pack"]})
    expected_locations = sorted(str(path) for path in (
        (a_dir / LOCAL_SELECTION_FILE).resolve(), (a_dir / LOCAL_EMAIL_PACK_FILE).resolve(),
        (root / STAGE4_PROGRAM_OUTPUTS["套磁选择.json"]).resolve(),
        (root / STAGE4_PROGRAM_OUTPUTS["邮件输入.json"]).resolve()))
    found_locations = sorted(str(path.resolve()) for path in (root / "教授研究").rglob("*")
                             if path.is_file() and path.name
                             in {LOCAL_SELECTION_FILE, LOCAL_EMAIL_PACK_FILE})
    _check(checks, "stage4_pair_written_only_where_the_contract_allows",
           found_locations == expected_locations,
           {"found": found_locations, "expected": expected_locations})
    _check(checks, "no_program_level_pair_rewritten",
           all(_file_state(root / relative)["sha256"] == expected
               for relative, expected in (manifest.get("legacy_program_pair") or {}).items()),
           {relative: _file_state(root / relative)["sha256"]
            for relative in (manifest.get("legacy_program_pair") or {})})
    observed["valid_professor_dir"] = valid_dirs[0]
    observed["fault_professor_dir"] = facts["fault_dir"]
    observed["valid_professor_selection_file"] = str(a_dir / LOCAL_SELECTION_FILE)
    observed["valid_professor_email_pack"] = str(a_dir / LOCAL_EMAIL_PACK_FILE)
    observed["fault_professor_bytes_sha256"] = b["candidate_state"]["sha256"]
    if phase_failed():
        return machine("fail", "FAIL_PRODUCT")
    return machine("pass", "PASS_TARGET")


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
    # Issue #40 separates two machine facts that must not gate each other: the
    # validator must have produced a contract-valid terminal record, while the
    # unchanged validator's copy quality stays independent diagnostics.
    terminal_records_ok = bool(pack_emails)
    copy_quality_pass = bool(pack_emails)
    frozen_and_valid = bool(pack_emails)
    invalid_details: list[Any] = []
    for email in pack_emails if isinstance(pack_emails, list) else []:
        if not isinstance(email, dict):
            invalid_details.append("email entry is not an object")
            terminal_records_ok = False
            copy_quality_pass = False
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
        terminal_valid = (_valid_validation_record(initial_validation)
                          and _valid_validation_record(followup_validation))
        if not terminal_valid:
            terminal_records_ok = False
        if not (terminal_valid and initial_validation.get("result") == "pass"
                and followup_validation.get("result") == "pass"):
            copy_quality_pass = False
        if not (valid_evidence and valid_source):
            frozen_and_valid = False
        if not (valid_evidence and valid_source and terminal_valid):
            invalid_details.append({"email_id": email_id, "evidence": valid_evidence,
                                    "source": valid_source,
                                    "terminal_validation": terminal_valid})
    _check(checks, "email_entries_frozen_and_valid", bool(pack_emails) and frozen_and_valid,
           invalid_details)
    _check(checks, "email_validator_terminal_records_valid", terminal_records_ok,
           invalid_details)
    _check(checks, "email_validator_result_pass", copy_quality_pass, invalid_details)
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
    "stage4-professor-isolation": _checkpoint_stage4_professor_isolation,
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
    parser.add_argument("--pre-snapshot", type=Path)
    parser.add_argument("--post-snapshot", type=Path)
    # PC67-RISO evidence inputs: the frozen fixture, its pre snapshot, the exact
    # request that ran, the recorded input hashes, and the install verdict.
    parser.add_argument("--fixture-manifest", type=Path)
    parser.add_argument("--eval-request", type=Path)
    parser.add_argument("--input-sha256", type=Path)
    parser.add_argument("--install-verdict", type=Path)
    parser.add_argument("--fixture-sha", default="")
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
    # The two make-* checkpoints own their output path: it is the product-like
    # input they construct, while their evidence is emitted on stdout.  Other
    # checkpoints use --output for the evidence document itself.
    if args.output is not None and args.checkpoint not in {
        "make-stage4-selection", "make-stage5-choices",
    }:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
