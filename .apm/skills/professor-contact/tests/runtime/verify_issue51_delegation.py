#!/usr/bin/env python3
"""Issue #51 runtime verifier: repo-owned coordinator nested delegation.

Consumes only the fixtures ``codex-eval-adapter@9`` output for one eval
phase (``--case r1|r2``) and decides whether the machine evidence proves the
formal nested delegation topology ``root -> child -> nested-child``:

* machine basis is the adapter's completed formal ``spawnAgent`` relation
  graph and its independent ``delegation`` summary — never assistant prose,
  prompt text or child self-reported role;
* named-role identity is explicitly out of scope: requested_role /
  loaded_identity, including mismatch or unobservable states, are optional
  diagnostics and never decide PASS/FAIL; this verifier only proves topology;
* ``pass`` requires at least one nested completed formal spawn edge and graph
  depth ``>= 2``; everything else is ``blocked`` / ``not_tested`` /
  ``invalid_evidence`` and never counts as acceptance.

The frozen #51/#52 acceptance boundary is *completed* formal topology.  The
#57 Stage-2 attempt semantics (which never require child completion) stay in
the #57 checkpoints; only the field authority/shape rules — senderThreadId as
the formal owner per the pinned sender_rule — are shared through
``_relation_rows``.

Topology helpers are reused from ``verify_issue32_e2e.py`` so both verifiers
share one adapter schema interpretation.

The #52 acceptance recipe runs this verifier standalone on the Stage 2
direct-delegation case (``--case r2``): the fixed prompt
``prompts/issue51-r2.txt`` routes the root caller to the analyzer once, and
the analyzer's own documented downstream delegation — proved only by the
formal adapter relations — must produce ``max_depth >= 2`` and at least one
nested edge.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

PROOF_SCOPE = "repo-owned-coordinator-formal-nested-delegation-only"
STATUSES = ("pass", "blocked", "not_tested", "invalid_evidence")

# Reuse the established adapter-topology helpers (issue #32 runtime gate)
# instead of inventing a second interpretation of the adapter schema.
_HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "_verify_issue32_e2e_topology", _HERE / "verify_issue32_e2e.py")
_ISSUE32 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ISSUE32)

relation_rows = _ISSUE32._relation_rows
graph_depth = _ISSUE32._graph_depth


def _verdict(
    status: str,
    case: str,
    edges: list[dict[str, Any]],
    reason_code: str = "",
    **detail: Any,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"unknown verifier status: {status!r}")
    nested_children = {str(edge["child"]) for edge in edges}
    nested_edge_count = sum(
        1 for edge in edges if str(edge["parent"]) in nested_children
    )
    return {
        "status": status,
        "case": case,
        "formal_spawn_relation_count": len(edges),
        "nested_edge_count": nested_edge_count,
        "max_depth": graph_depth(edges),
        "proof_scope": PROOF_SCOPE,
        "reason_code": reason_code,
        "detail": detail,
    }


def _malformed(case: str, reason: str, **detail: Any) -> dict[str, Any]:
    return _verdict("invalid_evidence", case, [], reason, **detail)


def _corrupted_relations(adapter: dict[str, Any]) -> str | None:
    """Self-defensive re-checks mirroring the adapter's fail-closed rules."""
    dispatch = adapter.get("dispatch")
    relations = dispatch.get("thread_relations") if isinstance(dispatch, dict) else None
    if not isinstance(relations, list):
        return None
    owners: dict[str, set[str]] = {}
    for relation in relations:
        if not isinstance(relation, dict) or relation.get("tool") != "spawnAgent":
            continue
        sender = relation.get("sender_thread_id")
        if not isinstance(sender, str) or not sender:
            # The pinned sender_rule fails closed on a formal spawn relation
            # without its issuing thread, whatever the raw status says.
            return "formal_spawn_without_concrete_owner"
        receivers = relation.get("receiver_thread_ids")
        if relation.get("status") == "completed" and (
                receivers in (None, [],) or not isinstance(receivers, list)
                or not all(isinstance(child, str) and child for child in receivers)):
            return "completed_spawn_without_concrete_receivers"
        for child in receivers if isinstance(receivers, list) else []:
            if isinstance(child, str) and child:
                owners.setdefault(child, set()).add(sender)
    if any(len(senders) > 1 for senders in owners.values()):
        return "conflicting_formal_ownership"
    return None


def evaluate(adapter: Any, case: str) -> dict[str, Any]:
    if not isinstance(adapter, dict):
        return _malformed(case, "adapter_not_object", observed=type(adapter).__name__)

    fixture_status = adapter.get("fixture_status")
    problems = adapter.get("problems") if isinstance(adapter.get("problems"), list) else []
    if not isinstance(fixture_status, str):
        return _malformed(case, "adapter_malformed", problems=problems)
    if fixture_status == "INVALID_EVIDENCE":
        return _verdict("invalid_evidence", case, [], "adapter_invalid_evidence",
                        problems=problems)
    if fixture_status == "BLOCKED_DEPENDENCY":
        return _verdict("blocked", case, [], "adapter_blocked_dependency",
                        problems=problems)
    # fixtures@9 makes named-role identity optional diagnostics.  Both
    # UNCONFIRMED and MISMATCH may coexist with delegation=confirmed and must
    # not downgrade a topology-confirmed run.
    if fixture_status not in (
        "FIXTURE_READY", "HARNESS_DISPATCH_UNCONFIRMED",
        "HARNESS_DISPATCH_MISMATCH",
    ):
        return _malformed(case, "adapter_unknown_fixture_status",
                          observed=fixture_status, problems=problems)

    dispatch = adapter.get("dispatch")
    relations = dispatch.get("thread_relations") if isinstance(dispatch, dict) else None
    delegation = adapter.get("delegation")
    if not isinstance(relations, list) or not isinstance(delegation, dict):
        return _malformed(case, "adapter_malformed", problems=problems)

    corruption = _corrupted_relations(adapter)
    if corruption:
        return _verdict("invalid_evidence", case, [], corruption, problems=problems)

    edges = relation_rows(adapter)

    state = delegation.get("state")
    if state not in ("confirmed", "unobservable"):
        return _malformed(case, "adapter_malformed",
                          observed=state, problems=problems)

    if state == "unobservable":
        if edges:
            return _verdict("invalid_evidence", case, [],
                            "delegation_summary_contradicts_relations",
                            problems=problems)
        reason = delegation.get("reason_code")
        return _verdict(
            "not_tested", case, [],
            reason if isinstance(reason, str) and reason
            else "formal_delegation_unobservable",
            problems=problems,
        )

    basis = delegation.get("basis")
    children = delegation.get("child_thread_ids")
    if basis != ["formal_spawn_relation"] or not isinstance(children, list) or not children:
        return _verdict("invalid_evidence", case, [],
                        "delegation_summary_inconsistent",
                        observed={"basis": basis, "child_thread_ids": children},
                        problems=problems)

    edge_children = {str(edge["child"]) for edge in edges}
    if not edge_children:
        # Frozen #51/#52 acceptance: the standalone verifier judges completed
        # formal spawn topology. Confirmed ownership without a single
        # completed formal relation is NOT TESTED — the #57 attempt
        # semantics never auto-promote it to a topology proof.
        return _verdict("not_tested", case, [],
                        "confirmed_delegation_without_completed_formal_relation",
                        problems=problems)
    summary_children = {str(child) for child in children if isinstance(child, str)}
    missing = sorted(child for child in edge_children if child not in summary_children)
    if missing:
        # A completed formal relation's child must be covered by the adapter's
        # confirmed delegation summary; the reverse is legal (the summary may
        # also count in-progress formal relations).
        return _verdict("invalid_evidence", case, [],
                        "delegation_summary_missing_completed_child",
                        observed={"uncovered_children": missing},
                        problems=problems)

    if graph_depth(edges) >= 2 and any(
        str(edge["parent"]) in edge_children for edge in edges
    ):
        return _verdict("pass", case, edges)

    return _verdict("not_tested", case, edges,
                    "nested_formal_delegation_not_observed")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("r1", "r2"), required=True)
    parser.add_argument("--adapter", type=Path, required=True,
                        help="fixtures @9 parse_codex_eval_evidence.py output")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        adapter = json.loads(args.adapter.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload = _malformed(args.case, "adapter_unreadable", detail=str(exc))
    else:
        payload = evaluate(adapter, args.case)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
