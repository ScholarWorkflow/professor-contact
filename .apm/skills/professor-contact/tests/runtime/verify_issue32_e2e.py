#!/usr/bin/env python3
"""Read-only runtime checkpoints for the issue #40 R1–R4 canonical matrix.

This verifier is the canonical #32 runtime recipe after issue #40's test
boundary refactor: the old E0–E7 business-detail gates (Stage 0 selection
previews, collector payload contracts, fingerprints, template placeholders,
validation schemas, ...) moved to deterministic unit tests.  Only the things
a real Codex/eval runtime can prove remain:

- clean install / producer SHA / fixture provenance;
- common eval response validity and adapter @9 formal topology;
- R1: Stage 1 artifact + formal Stage 2 loader consumption;
- R2: Stage 2 artifact + formal Stage 3 plan-loader consumption;
- R3: Stage 3 sibling orchestration + Stage 4 omitted-selection no-write;
- R4: explicit Stage 4 selection + Stage 4 pack + Stage 5 final artifacts.

The verifier observes product state and adapter-provided structured evidence
only.  It never parses assistant prose as delegation or identity evidence,
never fails a run for unobservable or mismatched named identity, and never
repairs product files.  Its only writes go to caller-specified ``--output``
paths outside the product state: verdict files (the R3 pre-omit file-state
snapshot is consumed by the ``r3b`` case) and the ``--make-stage4-selection``
helper output, which applies the issue-frozen lexicographic-first-candidate
policy.

Verdict statuses: ``pass``, ``fail`` (producer topology/continuity clearly
unmet), ``not_tested`` (formal relation unobservable — never a pass),
``invalid_evidence`` (malformed/conflicting machine evidence), and
``blocked`` (harness failure).  Only ``pass`` exits 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

MANIFEST_NAME = "fixture-manifest.json"
MANIFEST_ID = "tests/runtime/build_issue32_e2e_fixture.py"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
ADAPTER_CONTRACT_ID = "skills-test-fixtures/codex-eval-adapter@9"
LEGACY_ITEM_KEYS = ("AAAA1111", "BBBB2222")
RETRYABLE_FILL_STATUSES = ("pending",)
STAGE1_SNAPSHOT = Path("教授研究/套磁阶段1候选.json")
STAGE2_SELECTION_FILE = Path("教授研究/套磁选择.json")
STAGE2_EMAIL_PACK = Path("教授研究/邮件输入.json")
INPUT_PACK_KIND = "professor-contact-stage2-input"
CANDIDATE_STATE_KIND = "professor-contact-stage3-state"
DIRECTION_IDENTITY_VERSION = "direction-id-v1"
STAGE3_GENERATOR_CONTRACT_VERSION = "stage3-ideas-v2"
SELECTION_POLICY_LEXICOGRAPHIC = "lexicographic-first-candidate-id"
CASES = ("install", "r1", "r2", "r3a", "r3b", "r3-pre-omit", "r4a", "r4b")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _result(status: str, checks: list[dict[str, Any]], **observed: Any) -> dict[str, Any]:
    return {"status": status, "checks": checks, "observed": observed}


def _check(checks: list[dict[str, Any]], name: str, ok: bool, detail: Any = None) -> None:
    row: dict[str, Any] = {"name": name, "status": "pass" if ok else "fail"}
    if detail is not None:
        row["detail"] = detail
    checks.append(row)


def _checks_pass(checks: list[dict[str, Any]]) -> bool:
    return all(row["status"] == "pass" for row in checks)


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


def _resolved_commits(consumer: Path) -> tuple[dict[str, Any], list[str]]:
    """Map dependency name -> resolved_commit from the clean consumer lock."""
    resolved: dict[str, Any] = {}
    errors: list[str] = []
    for path in (consumer / "apm.lock.yaml", consumer / "apm.lock.yml"):
        if not path.is_file():
            continue
        payload, error = _load_yaml(path)
        if error:
            errors.append(f"{path.name}: {error}")
            continue
        dependencies = payload.get("dependencies") if isinstance(payload, dict) else None
        if not isinstance(dependencies, list):
            continue
        for dependency in dependencies:
            if isinstance(dependency, dict) and isinstance(dependency.get("name"), str):
                resolved[dependency["name"]] = dependency.get("resolved_commit")
    return resolved, errors


# ---------------------------------------------------------------------------
# shared runtime gates
# ---------------------------------------------------------------------------

def _manifest_gate(root: Path, checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Fixture provenance gate shared by every runtime case."""
    try:
        manifest = _load(root / MANIFEST_NAME)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "fixture_manifest_readable", False, str(exc))
        return None
    _check(checks, "fixture_builder", manifest.get("builder") == MANIFEST_ID, manifest.get("builder"))
    _check(checks, "fixture_mode", manifest.get("fixture_mode") == "initial_raw_inputs",
           manifest.get("fixture_mode"))
    _check(checks, "fixture_run_id_recorded",
           isinstance(manifest.get("fixture_run_id"), str) and bool(manifest.get("fixture_run_id")),
           manifest.get("fixture_run_id"))
    item_keys = manifest.get("item_keys")
    _check(checks, "dynamic_item_keys", isinstance(item_keys, list) and bool(item_keys)
           and all(isinstance(key, str) and key and key not in LEGACY_ITEM_KEYS for key in item_keys),
           item_keys)
    _check(checks, "fill_target_retryable",
           item_keys
           and manifest.get("fill_target_item_key") in item_keys
           and manifest.get("fill_target_item_key") not in (manifest.get("ready_item_keys") or [])
           and manifest.get("fill_target_pdf_status") in RETRYABLE_FILL_STATUSES,
           {"fill_target_item_key": manifest.get("fill_target_item_key"),
            "fill_target_pdf_status": manifest.get("fill_target_pdf_status")})
    _check(checks, "attachment_keys_recorded",
           isinstance(manifest.get("attachment_keys"), dict)
           and set(manifest.get("attachment_keys") or {}) == set(item_keys or ()),
           manifest.get("attachment_keys"))
    _check(checks, "direction_ids", manifest.get("direction_ids") == [DIRECTION_ID],
           manifest.get("direction_ids"))
    return manifest if _checks_pass(checks) else None


def _relation_rows(adapter: Any) -> list[dict[str, str]]:
    """Extract formal spawnAgent relations from adapter @9's normalized graph."""
    rows: list[dict[str, str]] = []
    if not isinstance(adapter, dict):
        return rows
    dispatch = adapter.get("dispatch")
    relations = dispatch.get("thread_relations") if isinstance(dispatch, dict) else None
    if not isinstance(relations, list):
        return rows
    for relation in relations:
        if not isinstance(relation, dict) or relation.get("tool") != "spawnAgent":
            continue
        if relation.get("status") != "completed":
            continue
        parent = relation.get("parent_thread_id")
        sender = relation.get("sender_thread_id", parent)
        children = relation.get("receiver_thread_ids")
        if not isinstance(parent, str) or not parent or not isinstance(children, list):
            continue
        for child in children:
            if isinstance(child, str) and child:
                rows.append({"parent": parent, "sender": sender if isinstance(sender, str) else parent,
                             "child": child})
    return rows


def _formal_edges(adapter: Any) -> tuple[list[dict[str, str]], str | None]:
    """Deduplicated formal edges; returns (edges, conflict_reason)."""
    edges: dict[tuple[str, str], dict[str, str]] = {}
    senders: dict[str, str] = {}
    for row in _relation_rows(adapter):
        child = row["child"]
        parent = row["parent"]
        edges.setdefault((parent, child), row)
        prior = senders.setdefault(child, row["sender"])
        if prior != row["sender"]:
            return [], (f"child thread {child!r} claimed by conflicting senders "
                        f"{prior!r} and {row['sender']!r}")
    return list(edges.values()), None


def _graph_depth(edges: list[dict[str, str]]) -> int:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge["parent"], set()).add(edge["child"])

    def longest_from(node: str, seen: set[str]) -> int:
        best = 0
        for child in adjacency.get(node, set()):
            if child in seen:
                continue
            best = max(best, 1 + longest_from(child, seen | {child}))
        return best

    return max((longest_from(node, {node}) for node in adjacency), default=0)


def _root_thread_id(adapter: Any) -> str | None:
    evidence = adapter.get("codex_evidence") if isinstance(adapter, dict) else None
    thread = evidence.get("thread_id") if isinstance(evidence, dict) else None
    value = thread.get("value") if isinstance(thread, dict) else None
    return value if isinstance(value, str) and value else None


def _adapter_gate(args: argparse.Namespace, checks: list[dict[str, Any]]) -> tuple[Any | None, str]:
    """Common adapter validity gate; returns (adapter, classification)."""
    classification = "pass"
    if not args.adapter_evidence:
        _check(checks, "adapter_evidence_supplied", False)
        return None, "invalid_evidence"
    try:
        adapter = _load(Path(args.adapter_evidence))
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "adapter_evidence_readable", False, str(exc))
        return None, "invalid_evidence"
    if not isinstance(adapter, dict):
        _check(checks, "adapter_evidence_object", False, type(adapter).__name__)
        return None, "invalid_evidence"
    edges, conflict = _formal_edges(adapter)
    _check(checks, "formal_ownership_consistent", conflict is None, conflict)
    contract_id = adapter.get("adapter_contract_id")
    _check(checks, "adapter_contract_at9", contract_id == ADAPTER_CONTRACT_ID, contract_id)
    fixture_status = adapter.get("fixture_status")
    delegation = adapter.get("delegation") if isinstance(adapter.get("delegation"), dict) else {}
    delegation_confirmed = delegation.get("state") == "confirmed" \
        and isinstance(delegation.get("basis"), list) \
        and "formal_spawn_relation" in delegation["basis"]
    _check(checks, "adapter_delegation_confirmed", delegation_confirmed,
           {"state": delegation.get("state"), "basis": delegation.get("basis"),
            "reason_code": delegation.get("reason_code")})
    if fixture_status == "INVALID_EVIDENCE":
        classification = "invalid_evidence"
    elif fixture_status in ("HARNESS_ERROR", "HARNESS_CONTAMINATION"):
        classification = "blocked"
    elif conflict is not None:
        # Mutually inconsistent formal ownership is corrupted machine
        # evidence (adapter @9 fail-closed), never a plain producer FAIL.
        classification = "invalid_evidence"
    elif not delegation_confirmed:
        # Named-identity diagnostics (unobservable or mismatched) never gate
        # a run; only an unproven formal relation itself leaves the formal
        # delegation unobservable, which is never a pass but also never a
        # producer FAIL.
        classification = "not_tested"
    elif contract_id != ADAPTER_CONTRACT_ID:
        classification = "invalid_evidence"
    return adapter, classification


def _delegation_children(adapter: Any) -> list[str]:
    delegation = adapter.get("delegation") if isinstance(adapter, dict) else None
    children = delegation.get("child_thread_ids") if isinstance(delegation, dict) else None
    return children if isinstance(children, list) else []


def _topology_gate(adapter: Any, checks: list[dict[str, Any]], *, required_depth: int,
                   min_root_children: int = 0) -> None:
    edges, conflict = _formal_edges(adapter)
    if conflict:
        _check(checks, "formal_ownership_consistent", False, conflict)
        return
    _check(checks, "formal_ownership_consistent", True)
    _check(checks, "formal_spawn_edges", len(edges) >= 1,
           {"observed": len(edges), "edges": edges})
    depth = _graph_depth(edges)
    _check(checks, "nested_depth", depth >= required_depth,
           {"observed": depth, "required": required_depth})
    if min_root_children:
        root = _root_thread_id(adapter)
        children = {edge["child"] for edge in edges if edge["parent"] == root} if root else set()
        _check(checks, "root_sibling_children", bool(root) and len(children) >= min_root_children,
               {"root_thread_id": root, "observed_children": sorted(children),
                "required": min_root_children})
    _check(checks, "delegation_children_recorded",
           set(_delegation_children(adapter)) == {edge["child"] for edge in edges} and bool(edges),
           _delegation_children(adapter))


def _run_installed_helper(script: Path, arguments: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            [sys.executable, str(script), *arguments],
            capture_output=True, text=True, check=False)
    except OSError as exc:
        return False, str(exc)
    return completed.returncode == 0, completed.stdout.strip() or completed.stderr.strip()


def _installed_script(name: str, consumer_root: Path | None) -> Path | None:
    candidates = []
    if consumer_root:
        candidates.append(Path(consumer_root) / ".agents/skills/professor-contact/scripts" / name)
    candidates.append(Path(__file__).resolve().parents[2] / "scripts" / name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

def _checkpoint_install(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    consumer = Path(args.consumer_root or "").resolve()
    _check(checks, "consumer_root_exists", bool(args.consumer_root) and consumer.is_dir(), str(consumer))
    if not consumer.is_dir():
        return _result("blocked", checks, consumer_root=str(consumer))
    expected = [consumer / ".agents/skills/professor-contact/SKILL.md",
                consumer / ".codex/agents/professor-contact.toml"]
    for path in expected:
        _check(checks, f"installed:{path.relative_to(consumer)}", path.is_file(), str(path))
        if path.exists():
            _check(checks, f"contained:{path.name}", path.resolve().is_relative_to(consumer), str(path.resolve()))
    resolved, errors = _resolved_commits(consumer)
    _check(checks, "lockfile_parseable", not errors and bool(resolved), errors)
    if args.producer_sha:
        _check(checks, "producer_sha_pinned", resolved.get("professor-contact") == args.producer_sha,
               {"expected": args.producer_sha, "observed": resolved.get("professor-contact")})
    if args.professor_research_sha:
        _check(checks, "professor_research_sha_pinned",
               resolved.get("professor-research") == args.professor_research_sha,
               {"expected": args.professor_research_sha, "observed": resolved.get("professor-research")})
    if not _checks_pass(checks):
        return _result("blocked", checks, consumer_root=str(consumer))
    return _result("pass", checks, consumer_root=str(consumer),
                   resolved_commits={key: value for key, value in resolved.items()})


# ---------------------------------------------------------------------------
# R1 / R2 continuity cases
# ---------------------------------------------------------------------------

def _checkpoint_r1(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    manifest = _manifest_gate(root, checks)
    if manifest is None:
        return _result("blocked", checks, case="r1")
    adapter, classification = _adapter_gate(args, checks)
    if classification != "pass":
        return _result(classification, checks, case="r1")
    _topology_gate(adapter, checks, required_depth=2)
    if not _checks_pass(checks):
        return _result("fail", checks, case="r1")
    snapshot = _stage1_artifact_gate(root, manifest, checks)
    if snapshot is None:
        return _result("fail", checks, case="r1")
    if not _stage2_loader_gate(root, args, checks):
        return _result("fail", checks, case="r1")
    return _result("pass", checks, case="r1", stage1_snapshot=str(root / STAGE1_SNAPSHOT))


def _stage1_artifact_gate(root: Path, manifest: dict[str, Any], checks: list[dict[str, Any]]) -> dict | None:
    try:
        snapshot = _load(root / STAGE1_SNAPSHOT)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "stage1_snapshot_readable", False, str(exc))
        return None
    _check(checks, "stage1_snapshot_schema", snapshot.get("schema_version") == 1
           and snapshot.get("kind") == "professor-contact-stage1",
           {"schema_version": snapshot.get("schema_version"), "kind": snapshot.get("kind")})
    professors = snapshot.get("professors") if isinstance(snapshot.get("professors"), list) else []
    professor_row = next((row for row in professors
                          if isinstance(row, dict) and row.get("professor") == PROFESSOR), None)
    _check(checks, "stage1_professor_present", professor_row is not None)
    directions = (professor_row or {}).get("directions") if isinstance(professor_row, dict) else None
    direction = next((row for row in (directions or [])
                      if isinstance(row, dict) and row.get("direction_id") == DIRECTION_ID), None)
    _check(checks, "stage1_direction_present", direction is not None)
    candidate_keys = (direction or {}).get("candidate_keys") if isinstance(direction, dict) else None
    _check(checks, "stage1_candidates_join_fixture_keys",
           isinstance(candidate_keys, list)
           and set(manifest["item_keys"]) <= set(candidate_keys),
           {"candidate_keys": candidate_keys, "fixture_item_keys": manifest["item_keys"]})
    return snapshot if _checks_pass(checks) else None


def _stage2_loader_gate(root: Path, args: argparse.Namespace, checks: list[dict[str, Any]]) -> bool:
    """Stage 2's formal prerequisite loader (contact_stage1.py verify) must
    consume the runtime-produced Stage 1 snapshot."""
    script = _installed_script("contact_stage1.py", args.consumer_root)
    _check(checks, "stage2_loader_installed", script is not None, str(script))
    if script is None:
        return False
    ok, output = _run_installed_helper(script, ["verify", "--program-root", str(root)])
    _check(checks, "stage2_loader_consumes_stage1_artifact", ok, output[-2000:])
    return ok


def _stage2_artifact_gate(root: Path, checks: list[dict[str, Any]]) -> Path | None:
    pack_path = _professor_dir(root) / "套磁候选输入.json"
    try:
        pack = _load(pack_path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "stage2_pack_readable", False, str(exc))
        return None
    _check(checks, "stage2_pack_schema", pack.get("schema") == 2
           and pack.get("kind") == INPUT_PACK_KIND
           and pack.get("identity_version") == DIRECTION_IDENTITY_VERSION
           and pack.get("managed_by") == "contact_state",
           {"schema": pack.get("schema"), "kind": pack.get("kind"),
            "identity_version": pack.get("identity_version"),
            "managed_by": pack.get("managed_by")})
    _check(checks, "stage2_pack_professor", pack.get("professor") == PROFESSOR
           and isinstance(pack.get("professor_dir"), str)
           and isinstance(pack.get("papers"), dict),
           {"professor": pack.get("professor")})
    directions = pack.get("directions") if isinstance(pack.get("directions"), list) else []
    direction = next((row for row in directions
                      if isinstance(row, dict) and row.get("direction_id") == DIRECTION_ID), None)
    _check(checks, "stage2_pack_direction", direction is not None)
    _check(checks, "stage2_pack_fingerprint",
           isinstance(direction, dict)
           and isinstance(direction.get("input_fingerprint"), str)
           and bool(direction.get("input_fingerprint"))
           and isinstance(direction.get("supporting_item_keys"), list))
    return pack_path if _checks_pass(checks) else None


def _stage3_plan_loader_gate(root: Path, args: argparse.Namespace, checks: list[dict[str, Any]]) -> bool:
    """Stage 3's formal plan loader (contact_state.py stage3-plan) must
    consume the runtime-produced Stage 2 input pack."""
    script = _installed_script("contact_state.py", args.consumer_root)
    _check(checks, "stage3_loader_installed", script is not None, str(script))
    if script is None:
        return False
    professor_dir = _professor_dir(root)
    ok, output = _run_installed_helper(script, [
        "stage3-plan", "--professor-dir", str(professor_dir),
        "--direction-id", DIRECTION_ID, "--program-root", str(root)])
    if not ok:
        _check(checks, "stage3_loader_consumes_stage2_pack", False, output[-2000:])
        return False
    try:
        plan = json.loads(output)
    except json.JSONDecodeError as exc:
        _check(checks, "stage3_loader_consumes_stage2_pack", False, f"non-JSON plan output: {exc}")
        return False
    consumed = isinstance(plan, dict) and isinstance(plan.get("jobs"), list) \
        and any(isinstance(job, dict) and job.get("direction_id") == DIRECTION_ID
                for job in plan["jobs"])
    _check(checks, "stage3_loader_consumes_stage2_pack", consumed,
           {"jobs": [job.get("direction_id") for job in plan.get("jobs", [])
                     if isinstance(job, dict)]})
    return consumed


def _checkpoint_r2(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    manifest = _manifest_gate(root, checks)
    if manifest is None:
        return _result("blocked", checks, case="r2")
    adapter, classification = _adapter_gate(args, checks)
    if classification != "pass":
        return _result(classification, checks, case="r2")
    _topology_gate(adapter, checks, required_depth=3)
    if not _checks_pass(checks):
        return _result("fail", checks, case="r2")
    if _stage2_artifact_gate(root, checks) is None:
        return _result("fail", checks, case="r2")
    if not _stage3_plan_loader_gate(root, args, checks):
        return _result("fail", checks, case="r2")
    return _result("pass", checks, case="r2", stage2_pack=str(_professor_dir(root) / "套磁候选输入.json"))


# ---------------------------------------------------------------------------
# R3: sibling orchestration + omitted-selection no-write
# ---------------------------------------------------------------------------

def _stage3_state_gate(root: Path, checks: list[dict[str, Any]]) -> dict | None:
    path = _professor_dir(root) / "套磁候选状态.json"
    try:
        state = _load(path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "stage3_state_readable", False, str(exc))
        return None
    _check(checks, "stage3_state_schema", state.get("schema") == 2
           and state.get("kind") == CANDIDATE_STATE_KIND
           and state.get("identity_version") == DIRECTION_IDENTITY_VERSION
           and state.get("generator_contract_version") == STAGE3_GENERATOR_CONTRACT_VERSION,
           {"schema": state.get("schema"), "kind": state.get("kind"),
            "generator_contract_version": state.get("generator_contract_version")})
    candidates = _candidate_rows(state)
    _check(checks, "stage3_candidates_present", bool(candidates),
           {"count": len(candidates), "ids": [row.get("id") for row in candidates]})
    _check(checks, "stage3_candidates_scoped_to_direction", all(
        row.get("direction_ids") == [DIRECTION_ID] for row in candidates),
        [row.get("direction_ids") for row in candidates])
    return state if _checks_pass(checks) else None


def _checkpoint_r3a(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    manifest = _manifest_gate(root, checks)
    if manifest is None:
        return _result("blocked", checks, case="r3a")
    adapter, classification = _adapter_gate(args, checks)
    if classification != "pass":
        return _result(classification, checks, case="r3a")
    _topology_gate(adapter, checks, required_depth=1, min_root_children=2)
    if not _checks_pass(checks):
        return _result("fail", checks, case="r3a")
    if _stage3_state_gate(root, checks) is None:
        return _result("fail", checks, case="r3a")
    return _result("pass", checks, case="r3a",
                   candidate_state=str(_professor_dir(root) / "套磁候选状态.json"))


def _stage_outputs_snapshot(root: Path) -> dict[str, dict[str, Any]]:
    """Existence/hash evidence for the Stage 4 outputs; prose never enters."""
    snapshot: dict[str, dict[str, Any]] = {}
    for relative in (STAGE2_SELECTION_FILE, STAGE2_EMAIL_PACK):
        path = root / relative
        row: dict[str, Any] = {"exists": path.is_file()}
        if path.is_file():
            row["sha256"] = _sha256(path)
        snapshot[relative.as_posix()] = row
    return snapshot


def _checkpoint_r3_pre_omit(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    manifest = _manifest_gate(root, checks)
    if manifest is None:
        return _result("blocked", checks, case="r3-pre-omit")
    snapshot = _stage_outputs_snapshot(root)
    for name, row in snapshot.items():
        _check(checks, f"absent_before_omit:{name}", row["exists"] is False, row)
    if not _checks_pass(checks):
        return _result("fail", checks, case="r3-pre-omit", snapshot=snapshot)
    return _result("pass", checks, case="r3-pre-omit", snapshot=snapshot)


def _checkpoint_r3b(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    manifest = _manifest_gate(root, checks)
    if manifest is None:
        return _result("blocked", checks, case="r3b")
    pre_state = None
    if args.pre_state:
        try:
            pre_state = _load(Path(args.pre_state))
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, "pre_state_readable", False, str(exc))
    else:
        _check(checks, "pre_state_supplied", False)
    adapter, classification = _adapter_gate(args, checks)
    if classification != "pass":
        return _result(classification, checks, case="r3b")
    if not _checks_pass(checks):
        return _result("fail", checks, case="r3b")
    post = _stage_outputs_snapshot(root)
    pre_snapshot = (pre_state or {}).get("observed", {}).get("snapshot", {})
    for name, row in post.items():
        _check(checks, f"absent_before_omit:{name}", pre_snapshot.get(name, {}).get("exists") is False,
               pre_snapshot.get(name))
        _check(checks, f"absent_after_omit:{name}", row["exists"] is False, row)
    if not _checks_pass(checks):
        return _result("fail", checks, case="r3b", post_snapshot=post)
    return _result("pass", checks, case="r3b", post_snapshot=post)


# ---------------------------------------------------------------------------
# R4: explicit selection + Stage 4 pack + Stage 5 final artifacts
# ---------------------------------------------------------------------------

def _checkpoint_r4a(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    manifest = _manifest_gate(root, checks)
    if manifest is None:
        return _result("blocked", checks, case="r4a")
    selection = None
    if args.selection_input:
        try:
            selection = _load(Path(args.selection_input))
        except (OSError, json.JSONDecodeError) as exc:
            _check(checks, "selection_input_readable", False, str(exc))
    else:
        _check(checks, "selection_input_supplied", False)
    adapter, classification = _adapter_gate(args, checks)
    if classification != "pass":
        return _result(classification, checks, case="r4a")
    if not _checks_pass(checks):
        return _result("fail", checks, case="r4a")
    ideas = selection.get("selection", [{}])[0].get("ideas", []) \
        if isinstance(selection, dict) and selection.get("selection") else []
    selected_ids = [row.get("id") for row in ideas if isinstance(row, dict)]
    _check(checks, "selection_names_one_candidate", len(selected_ids) == 1, selected_ids)
    try:
        product_selection = _load(root / STAGE2_SELECTION_FILE)
        email_pack = _load(root / STAGE2_EMAIL_PACK)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "stage4_outputs_readable", False, str(exc))
        return _result("fail", checks, case="r4a")
    _check(checks, "stage4_selection_schema", product_selection.get("schema") == 2,
           product_selection.get("schema"))
    consumed_ids = _selected_idea_ids(product_selection)
    _check(checks, "stage4_consumed_selection_matches_input",
           len(selected_ids) == 1 and consumed_ids == selected_ids,
           {"selection_input": selected_ids, "product_selection": consumed_ids})
    emails = email_pack.get("emails", email_pack.get("messages", []))
    if isinstance(emails, dict):
        emails = list(emails.values())
    _check(checks, "stage4_email_pack_nonempty", bool(emails),
           len(emails) if isinstance(emails, list) else type(emails).__name__)
    if not _checks_pass(checks):
        return _result("fail", checks, case="r4a")
    return _result("pass", checks, case="r4a",
                   consumed_candidate_ids=consumed_ids,
                   selection_input=str(args.selection_input))


def _selected_idea_ids(product_selection: dict[str, Any]) -> list[str]:
    rows = product_selection.get("selection") if isinstance(product_selection.get("selection"), list) else []
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ideas = row.get("ideas") if isinstance(row.get("ideas"), list) else []
        for idea in ideas:
            if isinstance(idea, dict) and isinstance(idea.get("id"), str):
                ids.append(idea["id"])
    return sorted(ids)


def _checkpoint_r4b(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.program_root).resolve()
    checks: list[dict[str, Any]] = []
    manifest = _manifest_gate(root, checks)
    if manifest is None:
        return _result("blocked", checks, case="r4b")
    adapter, classification = _adapter_gate(args, checks)
    if classification != "pass":
        return _result(classification, checks, case="r4b")
    _topology_gate(adapter, checks, required_depth=2)
    if not _checks_pass(checks):
        return _result("fail", checks, case="r4b")
    prof = _professor_dir(root)
    md_files = sorted(path for path in prof.glob("套磁*.md") if path.is_file())
    md_files.extend(sorted(path for path in (prof / "套磁邮件").glob("套磁*.md") if path.is_file()))
    txt_files = sorted(path for path in prof.glob("套磁*.txt") if path.is_file())
    txt_files.extend(sorted(path for path in (prof / "套磁邮件").glob("套磁*.txt") if path.is_file()))
    initial_md = [path for path in md_files if "套磁邮件" in path.name and "跟进" not in path.name]
    followup_md = [path for path in md_files if "跟进" in path.name]
    initial_txt = [path for path in txt_files if "套磁邮件" in path.name and "跟进" not in path.name]
    followup_txt = [path for path in txt_files if "跟进" in path.name]
    _check(checks, "initial_email_artifacts", bool(initial_md) and bool(initial_txt),
           {"md": [path.name for path in md_files], "txt": [path.name for path in txt_files]})
    _check(checks, "followup_email_artifacts", bool(followup_md) and bool(followup_txt),
           {"md": [path.name for path in md_files], "txt": [path.name for path in txt_files]})
    try:
        email_state = _load(prof / "套磁邮件状态.json")
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "email_state_readable", False, str(exc))
        return _result("fail", checks, case="r4b")
    _check(checks, "email_state_object", isinstance(email_state, dict)
           and isinstance(email_state.get("emails"), dict), type(email_state).__name__)
    if not _checks_pass(checks):
        return _result("fail", checks, case="r4b")
    return _result("pass", checks, case="r4b",
                   initial=[path.name for path in initial_md + initial_txt],
                   followup=[path.name for path in followup_md + followup_txt])


# ---------------------------------------------------------------------------
# make-stage4-selection: the only intentional write
# ---------------------------------------------------------------------------

def _checkpoint_make_stage4_selection(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    root = Path(args.program_root).resolve()
    _check(checks, "frozen_selection_policy", args.selection_policy == SELECTION_POLICY_LEXICOGRAPHIC,
           args.selection_policy)
    direction_id = args.direction_id or DIRECTION_ID
    if args.output is None:
        return _result("fail", checks + [{"name": "output_required", "status": "fail"}],
                       case="make-stage4-selection")
    state_path = _professor_dir(root) / "套磁候选状态.json"
    try:
        state = _load(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, "candidate_state_readable", False, str(exc))
        return _result("fail", checks, case="make-stage4-selection")
    rows = [row for row in _candidate_rows(state)
            if row.get("direction_ids") == [direction_id]]
    _check(checks, "candidates_scoped_to_direction", bool(rows),
           {"direction_id": direction_id, "count": len(rows)})
    if not rows:
        return _result("fail", checks, case="make-stage4-selection")
    selected = sorted(rows, key=lambda row: str(row["id"]))[0]
    payload = {
        "selection_policy": SELECTION_POLICY_LEXICOGRAPHIC,
        "direction_id": direction_id,
        "selection": [{"professor": PROFESSOR, "direction_ids": [direction_id],
                       "ideas": [{"id": selected["id"]}]}],
        "first_choice": args.first_choice,
        "signature_name": args.signature_name,
        "learning": args.learning,
        "initial_sent_date": args.initial_sent_date,
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                                     prefix=f".{output.name}.", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, output)
    _check(checks, "selection_written", output.is_file(), str(output))
    return _result("pass" if _checks_pass(checks) else "fail", checks,
                   case="make-stage4-selection", selected_id=selected["id"],
                   output=str(output), payload=payload)


CHECKPOINTS = {
    "install": _checkpoint_install,
    "r1": _checkpoint_r1,
    "r2": _checkpoint_r2,
    "r3a": _checkpoint_r3a,
    "r3-pre-omit": _checkpoint_r3_pre_omit,
    "r3b": _checkpoint_r3b,
    "r4a": _checkpoint_r4a,
    "r4b": _checkpoint_r4b,
}


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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    runtime = parser.add_mutually_exclusive_group(required=True)
    runtime.add_argument("--case", choices=CASES)
    runtime.add_argument("--make-stage4-selection", action="store_true",
                         help="apply the issue-frozen lexicographic-first-candidate "
                              "selection policy and write only --output")
    parser.add_argument("--program-root", type=Path)
    parser.add_argument("--consumer-root", type=Path)
    parser.add_argument("--adapter-evidence", type=Path)
    parser.add_argument("--pre-state", type=Path)
    parser.add_argument("--selection-input", type=Path)
    parser.add_argument("--producer-sha", default="")
    parser.add_argument("--professor-research-sha", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--direction-id", default=DIRECTION_ID)
    parser.add_argument("--selection-policy", default="")
    parser.add_argument("--first-choice", choices=("true", "false"), default="false")
    parser.add_argument("--signature-name", default="")
    parser.add_argument("--learning", default="")
    parser.add_argument("--initial-sent-date", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.make_stage4_selection:
            if args.program_root is None:
                raise ValueError("--program-root is required for --make-stage4-selection")
            if not args.selection_policy:
                raise ValueError("--selection-policy is required (frozen: "
                                 f"{SELECTION_POLICY_LEXICOGRAPHIC})")
            args.first_choice = args.first_choice == "true"
            payload = _checkpoint_make_stage4_selection(args)
        else:
            if args.case != "install" and args.program_root is None:
                raise ValueError("--program-root is required for this case")
            if args.case == "install" and args.consumer_root is None:
                raise ValueError("--consumer-root is required for the install case")
            payload = CHECKPOINTS[args.case](args)
    except Exception as exc:
        payload = _result("fail", [{"name": "verifier_exception", "status": "fail", "detail": str(exc)}])
    if args.output is not None:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                                         prefix=f".{output.name}.", delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1)
            handle.write("\n")
            temp_name = handle.name
        os.replace(temp_name, output)
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
