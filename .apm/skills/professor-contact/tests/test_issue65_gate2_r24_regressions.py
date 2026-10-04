import argparse
import contextlib
import io
import json
import unittest
from pathlib import Path

import test_contact_state as stage2_fixture


class Issue65Gate2R24Base(stage2_fixture.Issue65Stage2BindingEnv):
    """Current-scope Issue #65 fixtures: A and B have distinct display names."""

    DISPLAY = "教授甲"
    B_DISPLAY = "教授乙"

    def _raw_preflight(self, *, professor=None, target_file=None, scenario="preflight"):
        args = argparse.Namespace(
            program_root=str(self.root),
            professor=professor or self.DISPLAY,
            target_file=str(target_file or self.a_target),
            paper_analysis="relevant",
            gap_scope="selected_direction",
            freshness_scope="shortlist",
            max_relevant_papers=None,
        )
        return self._run_formal(
            stage2_fixture.contact_state.cmd_stage2_preflight,
            args,
            scenario=scenario,
        )

    def _payload(self, text, scenario):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            self.fail(f"{scenario} emitted unparseable output: {text!r}")
        self.assertIsInstance(payload, dict, f"{scenario} output is not an object: {payload!r}")
        return payload

    def _require_refresh(self, text, code, scenario, *, drift=None):
        payload = self._payload(text, scenario)
        self.assertEqual(payload.get("status"), "needs_refresh", payload)
        self.assertEqual(payload.get("reason_code"), "preflight_inputs_changed", payload)
        self.assertEqual(code, 2, f"{scenario} exit code: {code!r}")
        if drift is not None:
            self.assertIn(drift, payload.get("drift", []), payload)
        return payload

    def _preflight_for(self, professor, target_file):
        text, code = self._raw_preflight(
            professor=professor,
            target_file=target_file,
            scenario=f"preflight {professor}",
        )
        payload = self._payload(text, f"preflight {professor}")
        self.assertEqual(payload.get("status"), "ok", payload)
        self.assertIsNone(code, f"preflight {professor} exit code: {code!r}")
        return payload


class Issue65Gate2ExactPreviewBindingTests(Issue65Gate2R24Base):
    def test_issue65_r24_exact_preview_binding(self):
        """C65-04: a same-directory but wrong preview path must fail closed."""
        target_before = self.a_target.read_bytes()
        snapshot_before = self.a_snapshot.read_bytes()
        outputs_before = self.outputs_state()
        b_before = self.fingerprint(self.b_snapshot)
        legacy_before = self.fingerprint(self.legacy_snapshot)

        state = json.loads(snapshot_before)
        wrong_preview = self.a_dir / "不存在的预筛.json"
        state["preview_path"] = str(wrong_preview.relative_to(self.root))
        self.a_snapshot.write_text(
            json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        mutated_snapshot = self.a_snapshot.read_bytes()

        try:
            stdout = io.StringIO()
            with self.assertRaises(ValueError) as ctx:
                with contextlib.redirect_stdout(stdout):
                    stage2_fixture.contact_stage1.verify_command(self.root, self.a_target)
            self.assertIn("invalid_stage1_input", str(ctx.exception))
            self.assertIn("preview_path", str(ctx.exception))
            self.assertEqual(self.a_snapshot.read_bytes(), mutated_snapshot)
            self.assertEqual(self.outputs_state(), outputs_before)

            text, code = self._raw_preflight(scenario="wrong-preview preflight")
            payload = self._payload(text, "wrong-preview preflight")
            self.assertEqual(payload.get("status"), "needs_refresh", payload)
            self.assertEqual(payload.get("reason_code"), "invalid_stage1_snapshot", payload)
            self.assertEqual(code, 2, f"wrong-preview preflight exit code: {code!r}")

            self.assertEqual(self.outputs_state(), outputs_before)
            self.assertEqual(self.a_target.read_bytes(), target_before)
            self.assertEqual(self.a_snapshot.read_bytes(), mutated_snapshot)
            self.assertEqual(self.fingerprint(self.b_snapshot), b_before)
            self.assertEqual(self.fingerprint(self.legacy_snapshot), legacy_before)
        finally:
            self.a_snapshot.write_bytes(snapshot_before)


class Issue65Gate2Stage2ProofBindingTests(Issue65Gate2R24Base):
    def test_issue65_r24_stage2_proof_binding(self):
        """C65-05: plan/finalize must stay bound to one complete local target proof."""
        initial_outputs = self.outputs_state()

        # Missing proof cannot be treated as a legal plan input.
        text, code = self.plan_raw(self.root / "不存在的证明.json")
        payload = self._payload(text, "missing-proof plan")
        self.assertEqual(payload.get("reason_code"), "invalid_params", payload)
        self.assertEqual(code, 1, f"missing-proof plan exit code: {code!r}")
        self.assertEqual(self.outputs_state(), initial_outputs)

        # A valid proof from another professor cannot be consumed by A.
        sibling_proof = self._preflight_for(self.B_DISPLAY, self.b_target)
        self.preflight_file.write_text(
            json.dumps(sibling_proof, ensure_ascii=False), encoding="utf-8"
        )
        self._write_facts(preflight_id=sibling_proof["preflight_id"])
        text, code = self.plan_raw(self.preflight_file)
        self._require_refresh(text, code, "sibling-proof plan", drift="identity")
        self.assertEqual(self.outputs_state(), initial_outputs)

        # A legal A proof must cover bytes outside the old partial direction fingerprint.
        proof = self._preflight_for(self.DISPLAY, self.a_target)
        self.preflight_file.write_text(json.dumps(proof, ensure_ascii=False), encoding="utf-8")
        self._write_facts(preflight_id=proof["preflight_id"])
        target_before = self.a_target.read_bytes()
        outputs_before_drift = self.outputs_state()

        target = json.loads(target_before)
        target["selection_history"] = [
            {
                "selected_at": "2026-10-04T00:00:00Z",
                "selected_direction_ids": list(target["selected_direction_ids"]),
            }
        ]
        self.a_target.write_text(
            json.dumps(target, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        mutated_target = self.a_target.read_bytes()

        try:
            text, code = self.plan_raw(self.preflight_file)
            self._require_refresh(text, code, "selection-history drift plan", drift="identity")
            self.assertEqual(self.outputs_state(), outputs_before_drift)

            text, code = self.finalize()
            self._require_refresh(text, code, "selection-history drift finalize", drift="identity")
            self.assertEqual(self.outputs_state(), outputs_before_drift)
            self.assertEqual(self.a_target.read_bytes(), mutated_target)
        finally:
            self.a_target.write_bytes(target_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
