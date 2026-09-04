"""Regression for Stage 2 preflight/facts TOCTOU binding.

A saved preflight payload is a proof for the evidence preparation that follows it.
If another invocation replaces that payload before finalize, stale facts from the
first invocation must not be accepted merely because the replacement payload
matches the *current* target state.
"""

import json

from test_stage2_preflight import PreflightBase, parse, run_cli


class TestStage2PreflightBinding(PreflightBase):
    def test_finalize_rejects_preflight_from_later_invocation(self):
        # Accepted state/facts belong to target state A.
        self.build_accepted_state()
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.prof_dir / "套磁候选分析.md"
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        pack_before = pack_path.read_bytes()
        md_before = md_path.read_bytes()
        cache_before = cache_path.read_bytes()

        # A later invocation observes target state B and overwrites the saved
        # preflight proof.  The old facts file still contains state A's note.
        self.target["targets"][0]["directions"][0]["user_note"] = "later invocation note"
        self._write_target()
        later_plan = self.preflight()
        self.assertEqual(later_plan["action"], "process", later_plan)
        plan_path = self.root / "shared-preflight.json"
        plan_path.write_text(json.dumps(later_plan, ensure_ascii=False), encoding="utf-8")

        # Finalize must bind the preflight proof to the facts/evidence run, not
        # merely prove that the replacement payload matches current disk state.
        out = parse(run_cli(
            "stage2-finalize",
            "--facts", self.facts_path,
            "--results", self.root / "results",
            "--preflight-file", plan_path,
        ))
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "preflight_inputs_changed", out)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(md_path.read_bytes(), md_before)
        self.assertEqual(cache_path.read_bytes(), cache_before)

    def test_finalize_rejects_facts_bound_to_earlier_preflight(self):
        # Facts record proof A — the invocation that actually prepared them.
        self.build_accepted_state()
        first_plan_path = self.root / "first-preflight.json"
        first_plan_path.write_text(json.dumps(self.preflight(), ensure_ascii=False),
                                   encoding="utf-8")
        self.bind_facts_to_plan(first_plan_path)

        # A later invocation observes target state B; its payload matches the
        # current disk state, but the facts were prepared under proof A.
        self.target["targets"][0]["directions"][0]["user_note"] = "later invocation note"
        self._write_target()
        later_plan = self.preflight()
        self.assertEqual(later_plan["action"], "process", later_plan)
        plan_path = self.root / "shared-preflight.json"
        plan_path.write_text(json.dumps(later_plan, ensure_ascii=False), encoding="utf-8")

        out = parse(run_cli(
            "stage2-finalize",
            "--facts", self.facts_path,
            "--results", self.root / "results",
            "--preflight-file", plan_path,
        ))
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "preflight_inputs_changed", out)

    def test_finalize_rejects_payload_with_foreign_proof_id(self):
        self.build_accepted_state()
        first_plan_path = self.root / "first-preflight.json"
        first_plan_path.write_text(json.dumps(self.preflight(), ensure_ascii=False),
                                   encoding="utf-8")
        self.bind_facts_to_plan(first_plan_path)

        # A payload re-computed for the current state but carrying proof A's id
        # is not a self-consistent proof and must fail closed.
        self.target["targets"][0]["directions"][0]["user_note"] = "later invocation note"
        self._write_target()
        later_plan = self.preflight()
        first_plan = json.loads(first_plan_path.read_text(encoding="utf-8"))
        plan_path = self.root / "tampered-preflight.json"
        plan_path.write_text(json.dumps(dict(later_plan,
                                             preflight_id=first_plan["preflight_id"]),
                                        ensure_ascii=False), encoding="utf-8")

        out = parse(run_cli(
            "stage2-finalize",
            "--facts", self.facts_path,
            "--results", self.root / "results",
            "--preflight-file", plan_path,
        ))
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "preflight_inputs_changed", out)
        self.assertIn("preflight_proof_id", out["drift"], out)

    def test_finalize_rejects_corrupt_facts_binding_block(self):
        self.build_accepted_state()
        plan_path = self.root / "shared-preflight.json"
        plan_path.write_text(json.dumps(self.preflight(), ensure_ascii=False),
                             encoding="utf-8")
        self.facts["stage2_preflight"] = ["corrupt"]
        self.facts_path.write_text(json.dumps(self.facts, ensure_ascii=False, indent=1),
                                   encoding="utf-8")

        out = parse(run_cli(
            "stage2-finalize",
            "--facts", self.facts_path,
            "--results", self.root / "results",
            "--preflight-file", plan_path,
        ))
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "preflight_inputs_changed", out)
