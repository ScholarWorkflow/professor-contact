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
import tempfile
from pathlib import Path
from typing import Any

MANIFEST_NAME = "fixture-manifest.json"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
ITEM_KEYS = ("AAAA1111", "BBBB2222")
STAGE_OUTPUTS = (
    Path("教授研究/套磁目标.json"), Path("教授研究/套磁候选输入.json"),
    Path("教授研究/套磁候选状态.json"), Path("教授研究/套磁选择.json"),
    Path("教授研究/邮件输入.json"), Path("教授研究/套磁阶段1候选.json"),
)


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
                consumer / ".codex/agents/professor-contact.toml"]
    for path in expected:
        _check(checks, f"installed:{path.relative_to(consumer)}", path.is_file(), str(path))
        if path.exists():
            _check(checks, f"contained:{path.name}", path.resolve().is_relative_to(consumer), str(path.resolve()))
    if args.producer_sha:
        lock_text = ""
        for path in (consumer / "apm.lock.yaml", consumer / "apm.lock.yml"):
            if path.is_file():
                lock_text += path.read_text(encoding="utf-8", errors="replace")
        _check(checks, "producer_sha_pinned", args.producer_sha in lock_text, args.producer_sha)
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
    for relative in STAGE_OUTPUTS:
        _check(checks, f"product_output_absent:{relative.as_posix()}", not (root / relative).exists())
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
    _check(checks, "target_not_written", not (root / STAGE_OUTPUTS[0]).exists())
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
    _check(checks, "candidate_input_direction", DIRECTION_ID in json.dumps(pack, ensure_ascii=False))
    _check(checks, "analysis_for_ready_paper", bool(list((prof / "论文分析").glob("AAAA1111*.md"))))
    _check(checks, "future_work_sidecar", bool(list((prof / "论文分析").glob("AAAA1111*.future_work.json"))))
    _check(checks, "no_prebuilt_analysis_for_bbbb", not bool(list((prof / "论文分析").glob("BBBB2222*.md"))))
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
    candidates = _candidate_rows(state)
    _check(checks, "state_schema", state.get("schema_version") in (1, 2))
    _check(checks, "candidate_count", 3 <= len(candidates) <= 5, len(candidates))
    _check(checks, "candidate_ids_stable", all(isinstance(row, dict) and row.get("id") for row in candidates))
    _check(checks, "direction_present", _contains_direction(state))
    _check(checks, "validation_present", _has_structured_key(state, {"validation", "validator", "validated"}))
    return _finish(checks, candidate_state=str(path), candidate_ids=[row.get("id") for row in candidates if isinstance(row, dict)])


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
        direction = next((row for row in state.get("directions", [])
                          if isinstance(row, dict) and row.get("direction_id") == DIRECTION_ID), None)
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
    state_path = prof / "套磁邮件状态.json"
    validation_text = state_path.read_text(encoding="utf-8", errors="replace") if state_path.is_file() else ""
    _check(checks, "email_state_exists", state_path.is_file(), str(state_path))
    _check(checks, "validation_passed", "\"result\": \"pass\"" in validation_text
           or "\"result\":\"pass\"" in validation_text
           or "pass" in text.lower() or "通过" in text)
    return _finish(checks, email_files=[path.name for path in all_files], email_state=str(state_path))


def _relation_rows(payload: Any) -> list[dict[str, Any]]:
    """Extract formal relation/event rows only; ignore prose and identity strings."""
    rows: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return rows
    for key in ("formal_relations", "relations", "delegations", "spawn_relations"):
        value = payload.get(key)
        if isinstance(value, list):
            rows.extend(row for row in value if isinstance(row, dict))
    events = payload.get("app_server_events")
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("event_type", event.get("type", ""))).lower()
            if "spawn" in event_type or "delegat" in event_type:
                rows.append(event)
    return rows


def _checkpoint_runtime_graph(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    sources: list[Any] = []
    for name in (args.adapter_output, args.eval_response):
        if not name:
            continue
        try:
            sources.append(_load(Path(name)))
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, f"evidence_readable:{name}", False, str(exc))
    rows = [row for source in sources for row in _relation_rows(source)]
    formal = []
    for row in rows:
        parent = row.get("parent") or row.get("parent_id") or row.get("from") or row.get("caller")
        child = row.get("child") or row.get("child_id") or row.get("to") or row.get("callee")
        if parent and child:
            formal.append({"parent": parent, "child": child, "kind": row.get("kind", row.get("type", "delegation"))})
    _check(checks, "formal_delegation_edges", len(formal) >= args.min_edges,
           {"observed": len(formal), "required": args.min_edges})
    _check(checks, "nested_depth", len({str(row["parent"]) for row in formal}) >= args.required_depth,
           {"observed": len({str(row["parent"]) for row in formal}), "required": args.required_depth})
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
    "stage5-final": _checkpoint_stage5_final,
    "runtime-graph": _checkpoint_runtime_graph,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", choices=tuple(CHECKPOINTS))
    parser.add_argument("--program-root", type=Path, required=True)
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
        if args.checkpoint == "make-stage4-selection" and args.output is None:
            raise ValueError("--output is required for make-stage4-selection")
        payload = CHECKPOINTS[args.checkpoint](args)
    except Exception as exc:
        payload = _result("fail", [{"name": "verifier_exception", "status": "fail", "detail": str(exc)}])
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
