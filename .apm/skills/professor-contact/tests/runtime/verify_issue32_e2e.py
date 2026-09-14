#!/usr/bin/env python3
"""Runtime checkpoints for issue #32's R1–R4 Codex evaluation (issue #40).

The verifier proves only two things:

A. runtime-specific machine evidence — the common eval gate plus adapter @9
   formal ``spawnAgent`` delegation topology (anonymous thread ownership);
B. minimum continuity sanity — a canonical artifact was produced and the next
   stage's formal plan/input loader can actually consume it.

Named-role identity (``requested_role`` / ``loaded_identity``) is recorded as
an observed diagnostic and never gates a verdict.  ``delegation=unobservable``
is an observability gap reported as ``not_tested`` (exit code 2), never a
producer FAIL and never a retry signal.  Malformed or mutually inconsistent
evidence still fails closed as a harness/evidence error.

The verifier observes product state; it never repairs product files.  The
sole intentional write is the ``make-stage4-selection`` helper, which models
an explicit user selection and writes only the requested output path.
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
PROGRAM_STAGE_OUTPUTS = (
    Path("教授研究/套磁目标.json"), Path("教授研究/套磁阶段1候选.json"),
)
PROFESSOR_STAGE_OUTPUTS = (
    Path("套磁候选输入.json"), Path("套磁候选状态.json"),
)
# Stage 4/5 canonical files are program-level only; professor-dir same-name
# files never count (issue #40 §6).
PROGRAM_SELECTION_FILE = Path("教授研究/套磁选择.json")
PROGRAM_EMAIL_PACK_FILE = Path("教授研究/邮件输入.json")
SNAPSHOT_FILE = Path("教授研究/套磁阶段1候选.json")
INPUT_PACK_NAME = "套磁候选输入.json"
CANDIDATE_STATE_NAME = "套磁候选状态.json"
RAW_CONTACT_SOURCES = ("_professor_candidates.json", "_corresp_cache.json", "_署名对照.json")
CONSUMER_SCRIPTS = Path(".agents/skills/professor-contact/scripts")
INITIAL_EMAIL_MARKER = "套磁邮件"
FOLLOWUP_EMAIL_MARKER = "跟进"


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


def _professor_dir(root: Path) -> Path:
    return root / "教授研究" / "X分野" / PROFESSOR


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
        resolved_commit, detail = _resolved_professor_contact_commit(consumer)
        _check(checks, "producer_sha_pinned", resolved_commit == args.producer_sha,
               {"expected": args.producer_sha, "observed": resolved_commit, "source": detail})
    return _finish(checks, consumer_root=str(consumer))


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
    _check(checks, "dynamic_item_keys", isinstance(manifest.get("item_keys"), list)
           and bool(manifest.get("item_keys"))
           and isinstance(manifest.get("ready_item_keys"), list)
           and isinstance(manifest.get("fill_target_item_key"), str)
           and bool(manifest.get("fill_target_item_key")),
           {key: manifest.get(key) for key in
            ("item_keys", "ready_item_keys", "fill_target_item_key")})
    return manifest, checks


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
    item_keys = [str(key) for key in manifest.get("item_keys", [])]
    ready_keys = [str(key) for key in manifest.get("ready_item_keys", [])]
    fill_key = str(manifest.get("fill_target_item_key", ""))
    try:
        papers = _load(prof / "papers.json").get("papers", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        papers = []
    by_key = {row.get("item_key"): row for row in papers if isinstance(row, dict)}
    _check(checks, "catalog_keys_match_manifest", set(by_key) == set(item_keys), sorted(by_key))
    ready_rows_ok = all(by_key.get(key, {}).get("pdf_status") == "downloaded"
                        and bool(by_key.get(key, {}).get("pdf_path"))
                        and (prof / f"论文分析/{key}.pdf").is_file()
                        for key in ready_keys)
    _check(checks, "ready_papers_have_deterministic_pdfs", ready_rows_ok, ready_keys)
    fill_row = by_key.get(fill_key, {})
    _check(checks, "fill_target_uses_retry_state", fill_row
           and fill_row.get("pdf_status") == manifest.get("fill_target_pdf_status")
           and not fill_row.get("pdf_path"), fill_row)
    pdf_bytes = b""
    if ready_keys:
        ready_pdf = prof / f"论文分析/{ready_keys[0]}.pdf"
        pdf_bytes = ready_pdf.read_bytes() if ready_pdf.is_file() else b""
    _check(checks, "deterministic_text_pdf", pdf_bytes.startswith(b"%PDF-1.4")
           and b"/Type /Page" in pdf_bytes and b"/Contents" in pdf_bytes and b"%%EOF" in pdf_bytes)
    _check(checks, "profile_inputs", all((Path(manifest["profile_root"]) / name).is_file() for name in
                                          ("套磁信息.md", "套磁模板.md", "套磁跟进模板.md")))
    _check(checks, "legal_application_inputs", (root / "info.json").is_file()
           and (root / "boshu_analysis.json").is_file())
    professors_root = root / "教授研究"
    _check(checks, "owner_consumable_raw_sources", all(
        (professors_root / name).is_file() for name in RAW_CONTACT_SOURCES),
        [name for name in RAW_CONTACT_SOURCES])
    _check(checks, "no_ownerless_contact_input",
           not (professors_root / "contact-evidence-fixture-input.json").exists())
    _check(checks, "no_prebuilt_contact_evidence",
           not (professors_root / "_联系方式证据.json").exists())
    for relative in PROGRAM_STAGE_OUTPUTS:
        _check(checks, f"product_output_absent:{relative.as_posix()}", not (root / relative).exists())
    for relative in PROFESSOR_STAGE_OUTPUTS:
        _check(checks, f"product_output_absent:{relative.as_posix()}",
               not (_professor_dir(root) / relative).exists())
    _check(checks, "no_prebuilt_analysis", not list((prof / "论文分析").glob("*.md"))
           and not list((prof / "论文分析").glob("*.future_work.json")))
    return _finish(checks, professor=PROFESSOR, direction_id=DIRECTION_ID,
                   item_keys=sorted(by_key))


def _common_eval_gate(args: argparse.Namespace, checks: list[dict[str, Any]]) -> None:
    """The common eval gate: this run's response shows a normally terminated run."""
    if not args.eval_response:
        checks.append({"name": "common_eval_gate", "status": "pass",
                       "detail": "eval response not supplied; gate enforced by the recipe"})
        return
    try:
        response = _load(Path(args.eval_response))
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "common_eval_gate", False, f"eval response unreadable: {exc}")
        return
    output = response.get("output") if isinstance(response, dict) else None
    termination = output.get("termination_reason") if isinstance(output, dict) else None
    _check(checks, "common_eval_gate",
           isinstance(termination, str) and bool(termination),
           {"termination_reason": termination})


def _run_formal_loader(args: argparse.Namespace, checks: list[dict[str, Any]], name: str,
                       script: str, cli_args: list[str]) -> None:
    """Run the next stage's formal plan/input loader and require it to accept."""
    consumer = Path(args.consumer_root or "").resolve() if args.consumer_root else None
    if not consumer or not consumer.is_dir():
        _check(checks, name, False, "consumer root with installed runner is required")
        return
    script_path = consumer / CONSUMER_SCRIPTS / script
    if not script_path.is_file():
        _check(checks, name, False, f"installed runner missing: {script_path}")
        return
    try:
        completed = subprocess.run(
            ["python3", str(script_path), *cli_args],
            capture_output=True, text=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        _check(checks, name, False, str(exc))
        return
    detail: Any = {"returncode": completed.returncode}
    ok = completed.returncode == 0
    if ok:
        try:
            payload = json.loads(completed.stdout)
            status = payload.get("status") if isinstance(payload, dict) else None
            ok = status is None or status == "ok"
            detail["status"] = status
        except json.JSONDecodeError:
            ok = False
            detail["stdout"] = "not a JSON payload"
    _check(checks, name, ok, detail)


def _stage1_snapshot_entry(root: Path, manifest: dict[str, Any],
                           checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        snapshot = _load(root / SNAPSHOT_FILE)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "stage1_snapshot_readable", False, str(exc))
        return None
    professor_rows = [row for row in snapshot.get("professors", [])
                      if isinstance(row, dict) and row.get("professor") == PROFESSOR]
    _check(checks, "stage1_snapshot_professor", len(professor_rows) == 1, len(professor_rows))
    direction = None
    if professor_rows:
        direction = next((row for row in professor_rows[0].get("directions", [])
                          if isinstance(row, dict) and row.get("direction_id") == DIRECTION_ID), None)
        _check(checks, "stage1_snapshot_direction", direction is not None)
    if direction:
        candidate_keys = direction.get("candidate_keys", [])
        _check(checks, "stage1_snapshot_covers_manifest_keys",
               set(candidate_keys) >= set(manifest.get("item_keys", [])),
               {"candidate_keys": candidate_keys, "item_keys": manifest.get("item_keys")})
    return direction


def _checkpoint_stage1_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    manifest, manifest_checks = _manifest(root)
    checks.extend(manifest_checks)
    if manifest is None:
        return _finish(checks)
    _common_eval_gate(args, checks)
    _stage1_snapshot_entry(root, manifest, checks)
    # R1 continuity: the Stage 2 formal precondition loader must actually
    # consume the snapshot, not a schema grep.
    _run_formal_loader(args, checks, "stage2_precondition_loader_consumes_snapshot",
                       "contact_stage1.py", ["verify", "--program-root", str(root)])
    return _finish(checks, snapshot_file=str(root / SNAPSHOT_FILE))


def _checkpoint_stage2_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    manifest, manifest_checks = _manifest(root)
    checks.extend(manifest_checks)
    if manifest is None:
        return _finish(checks)
    _common_eval_gate(args, checks)
    prof = _professor_dir(root)
    pack_path = prof / INPUT_PACK_NAME
    try:
        pack = _load(pack_path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "candidate_input_readable", False, str(exc))
        return _finish(checks)
    directions = pack.get("directions") if isinstance(pack, dict) else None
    direction_present = isinstance(directions, list) and any(
        isinstance(row, dict) and row.get("direction_id") == DIRECTION_ID for row in directions)
    _check(checks, "candidate_input_has_machine_direction", direction_present)
    # R2 continuity: the Stage 3 formal plan loader must actually consume the pack.
    _run_formal_loader(args, checks, "stage3_plan_loader_consumes_input_pack",
                       "contact_state.py", ["stage3-plan", "--professor-dir", str(prof)])
    return _finish(checks, candidate_input=str(pack_path))


def _checkpoint_stage3_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    _common_eval_gate(args, checks)
    state_path = _professor_dir(root) / CANDIDATE_STATE_NAME
    try:
        state = _load(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "candidate_state_readable", False, str(exc))
        return _finish(checks)
    directions = state.get("directions") if isinstance(state, dict) else None
    direction = next((row for row in directions if isinstance(row, dict)
                      and row.get("direction_id") == DIRECTION_ID), None) \
        if isinstance(directions, list) else None
    _check(checks, "candidate_state_has_machine_direction", direction is not None)
    candidates = (direction or {}).get("candidates", [])
    _check(checks, "candidate_state_offers_candidates",
           isinstance(candidates, list) and bool(candidates), len(candidates))
    return _finish(checks, candidate_state=str(state_path))


def _checkpoint_stage4_needs_input(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    _common_eval_gate(args, checks)
    # The run must end without auto-selecting: program-level canonical files
    # stay absent.  Professor-dir same-name files are never consulted.
    _check(checks, "selection_file_absent", not (root / PROGRAM_SELECTION_FILE).exists(),
           str(root / PROGRAM_SELECTION_FILE))
    _check(checks, "email_input_absent", not (root / PROGRAM_EMAIL_PACK_FILE).exists(),
           str(root / PROGRAM_EMAIL_PACK_FILE))
    return _finish(checks)


def _checkpoint_make_stage4_selection(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    state_path = _professor_dir(root) / CANDIDATE_STATE_NAME
    try:
        state = _load(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "candidate_state_readable", False, str(exc))
        return _finish(checks)
    rows = sorted(_candidate_rows(state), key=lambda row: str(row["id"]))
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


def _checkpoint_stage4_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    _common_eval_gate(args, checks)
    try:
        selection = _load(root / PROGRAM_SELECTION_FILE)
        email_input = _load(root / PROGRAM_EMAIL_PACK_FILE)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "program_level_stage4_outputs_readable", False, str(exc))
        return _finish(checks)
    _check(checks, "selection_is_object", isinstance(selection, dict), type(selection).__name__)
    emails = email_input.get("emails", []) if isinstance(email_input, dict) else []
    _check(checks, "email_pack_nonempty", bool(emails), len(emails) if isinstance(emails, list) else "invalid")
    # R4 continuity: the Stage 5 formal plan loader must actually consume the pack.
    _run_formal_loader(args, checks, "stage5_plan_loader_consumes_email_pack",
                       "contact_state.py", ["stage5-plan", "--program-root", str(root)])
    return _finish(checks, selection_file=str(root / PROGRAM_SELECTION_FILE),
                   email_pack=str(root / PROGRAM_EMAIL_PACK_FILE))


def _checkpoint_stage5_final(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    _common_eval_gate(args, checks)
    prof = _professor_dir(root)
    md_files = sorted(path for path in prof.glob("套磁*.md") if path.is_file())
    initial = [path for path in md_files
               if INITIAL_EMAIL_MARKER in path.name and FOLLOWUP_EMAIL_MARKER not in path.name]
    followup = [path for path in md_files if FOLLOWUP_EMAIL_MARKER in path.name]
    _check(checks, "initial_email_artifact_exists", bool(initial), [path.name for path in md_files])
    if args.require_followup:
        _check(checks, "followup_email_artifact_exists", bool(followup),
               [path.name for path in md_files])
    try:
        email_pack = _load(root / PROGRAM_EMAIL_PACK_FILE)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "frozen_email_pack_readable", False, str(exc))
        return _finish(checks)
    emails = email_pack.get("emails", []) if isinstance(email_pack, dict) else []
    _check(checks, "frozen_email_pack_nonempty", bool(emails),
           len(emails) if isinstance(emails, list) else "invalid")
    return _finish(checks, email_files=[path.name for path in md_files],
                   email_pack=str(root / PROGRAM_EMAIL_PACK_FILE))


def _relation_rows(payload: Any) -> list[dict[str, Any]]:
    """Extract formal spawnAgent relations from the adapter's normalized graph."""
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


def _max_siblings(edges: list[dict[str, Any]]) -> int:
    degree: dict[str, int] = {}
    for edge in edges:
        degree[edge["parent"]] = degree.get(edge["parent"], 0) + 1
    return max(degree.values(), default=0)


def _checkpoint_runtime_graph(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    adapter = None
    if args.adapter_output:
        try:
            adapter = _load(Path(args.adapter_output))
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, "adapter_evidence_readable", False, str(exc))
            return _result("fail", checks)
    else:
        _check(checks, "adapter_evidence_supplied", False)
        return _result("fail", checks)
    fixture_status = adapter.get("fixture_status") if isinstance(adapter, dict) else None
    if fixture_status == "INVALID_EVIDENCE":
        return _result("fail", [{"name": "adapter_evidence_valid", "status": "fail",
                                 "detail": "INVALID_EVIDENCE is corrupted machine evidence"}],
                       classification="invalid_evidence")
    if fixture_status == "BLOCKED_DEPENDENCY":
        return _result("not_tested",
                       [{"name": "adapter_evidence_valid", "status": "pass",
                         "detail": "harness dependency unavailable; never a producer FAIL"}],
                       classification="blocked_dependency")
    _common_eval_gate(args, checks)
    delegation = adapter.get("delegation") if isinstance(adapter, dict) else None
    state = delegation.get("state") if isinstance(delegation, dict) else None
    if state == "unobservable":
        # Observation gap on this evidence surface: never a producer FAIL,
        # never a retry signal (adapter @9 / issue #40 §2.4).
        return _result("not_tested",
                       [{"name": "formal_delegation_observed", "status": "pass",
                         "detail": "delegation=unobservable is an observation state"}],
                       classification="observability_gap",
                       reason_code=(delegation or {}).get("reason_code"))
    if state != "confirmed":
        return _result("fail", [{"name": "adapter_delegation_dimension", "status": "fail",
                                 "detail": f"delegation state {state!r} is not a supported value"}],
                       classification="invalid_evidence")
    rows = _relation_rows(adapter)
    senders_by_child: dict[str, set[str]] = {}
    for row in rows:
        child = row["child"]
        for relation in adapter.get("dispatch", {}).get("thread_relations", []) \
                if isinstance(adapter.get("dispatch"), dict) else []:
            if (isinstance(relation, dict) and relation.get("tool") == "spawnAgent"
                    and relation.get("status") == "completed"
                    and isinstance(relation.get("receiver_thread_ids"), list)
                    and child in relation["receiver_thread_ids"]):
                sender = relation.get("sender_thread_id")
                if isinstance(sender, str) and sender:
                    senders_by_child.setdefault(child, set()).add(sender)
    conflicted = sorted(child for child, senders in senders_by_child.items() if len(senders) > 1)
    if conflicted:
        return _result("fail", [{"name": "formal_ownership_consistent", "status": "fail",
                                 "detail": f"conflicting formal ownership for children: {conflicted}"}],
                       classification="invalid_evidence")
    _check(checks, "formal_delegation_edges", len(rows) >= args.min_edges,
           {"observed": len(rows), "required": args.min_edges})
    depth = _graph_depth(rows)
    _check(checks, "nested_depth", depth >= args.required_depth,
           {"observed": depth, "required": args.required_depth})
    siblings = _max_siblings(rows)
    _check(checks, "minimum_siblings", siblings >= args.min_siblings,
           {"observed": siblings, "required": args.min_siblings})
    payload = _finish(checks, formal_relations=rows, formal_depth=depth, formal_edges=len(rows),
                      classification="formal_delegation_confirmed")
    # Identity diagnostics are recorded verbatim and never participate in the
    # verdict (issue #40 §2.3).
    dispatch = adapter.get("dispatch") if isinstance(adapter, dict) else None
    identity = dispatch.get("agent_identity") if isinstance(dispatch, dict) else None
    payload["observed"]["identity_diagnostics"] = identity
    return payload


CHECKPOINTS = {
    "install": _checkpoint_install,
    "initial": _checkpoint_initial,
    "stage1-final": _checkpoint_stage1_final,
    "stage2-final": _checkpoint_stage2_final,
    "stage3-final": _checkpoint_stage3_final,
    "stage4-needs-input": _checkpoint_stage4_needs_input,
    "make-stage4-selection": _checkpoint_make_stage4_selection,
    "stage4-final": _checkpoint_stage4_final,
    "stage5-final": _checkpoint_stage5_final,
    "runtime-graph": _checkpoint_runtime_graph,
}

EXIT_CODES = {"pass": 0, "fail": 1, "not_tested": 2}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", choices=tuple(CHECKPOINTS))
    parser.add_argument("--program-root", type=Path)
    parser.add_argument("--consumer-root", type=Path)
    parser.add_argument("--eval-response", type=Path)
    parser.add_argument("--adapter-output", type=Path)
    parser.add_argument("--producer-sha", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-edges", type=int, default=1)
    parser.add_argument("--required-depth", type=int, default=1)
    parser.add_argument("--min-siblings", type=int, default=1)
    parser.add_argument("--require-followup", action="store_true")
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
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return EXIT_CODES.get(payload.get("status"), 1)


if __name__ == "__main__":
    raise SystemExit(main())
