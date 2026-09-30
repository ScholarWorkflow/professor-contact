"""Shared helpers for Stage-2 business tests that are not preflight tests."""

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"
_SPEC = importlib.util.spec_from_file_location("stage2_test_support_contact_state", SCRIPT)
contact_state = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(contact_state)


def run_bound_stage2_plan(run_cli, facts_path: Path):
    """Invoke stage2-plan with an identity-valid synthetic preflight payload.

    These callers test plan/finalize business rules, while the real preflight
    lifecycle is covered separately.  The CLI still receives the now-required
    proof, and the production binder recomputes and verifies its local identity.
    """
    facts_path = Path(facts_path)
    ctx = contact_state.Stage2Context(facts_path)
    _target, _entry, identity = contact_state.stage2_transaction_identity(ctx)
    preflight_inputs = {"identity": identity}
    proof = {
        "status": "ok",
        "professor": ctx.professor,
        "preflight_inputs": preflight_inputs,
        "preflight_id": contact_state.sha256_obj({
            "professor": ctx.professor,
            "preflight_inputs": preflight_inputs,
        }),
    }
    proof_path = facts_path.parent / "synthetic-stage2-plan-proof.json"
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=1), encoding="utf-8")
    return run_cli("stage2-plan", "--facts", facts_path, "--preflight-file", proof_path)
