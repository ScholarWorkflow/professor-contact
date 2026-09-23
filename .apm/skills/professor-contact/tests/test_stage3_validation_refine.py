"""Regression coverage for the Stage-3 validator ingest and correction round.

The runner owns the whole handoff: the caller passes the style validator's own
JSON, the runner binds it to the exact rendered revision, derives the machine
scope of every finding from the rendered text, counts rounds, and only then
allows a correction plan.  A caller never translates a verdict, never nominates
a scope the validator did not fail, and never replays evidence for a render that
has been replaced.
"""
import json

from test_stage2_resolved_direction import run_cli, parse, write_json
from test_stage3_direction_groups import (
    Stage3DirectionGroupBase, contact_state, result_file)

CANDIDATES_MD = "套磁想法候选.md"
CANDIDATE_STATE = "套磁候选状态.json"
CROSS_GROUP = '[["dir_A","dir_B"]]'
CROSS_GID = contact_state.cross_group_id(["dir_A", "dir_B"])


class Stage3ValidationIngestTests(Stage3DirectionGroupBase):
    """One shared render + one raw validator file per test."""

    def setUp(self):
        super().setUp()
        self.validation = self.root / "stage3-style-validation.json"

    # -- fixture helpers -------------------------------------------------

    def render_single(self):
        out = self.stage3_finalize(
            self.results("s3-single", {"dir_A": self.generated_doc("dir_A", ["P1", "P2", None])}),
            "--direction-id", "dir_A")
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        return out

    def render_two(self):
        results = self.results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        return out

    def render_cross(self):
        self.render_two()
        cross = self.cross_candidate("X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
                                     gap_owner={"P2": "dir_A", "P3": "dir_B"})
        cross["title"] = "跨方向融合标题"
        write_json(self.results_dir / result_file("candidates", CROSS_GID),
                   self.cross_doc(["dir_A", "dir_B"], [cross]))
        out = self.stage3_finalize(self.results_dir, "--cross-direction-groups", CROSS_GROUP)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        return out

    def render_refined(self):
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        direction = next(d for d in pack["directions"] if d["direction_id"] == "dir_A")
        direction["user_note"] = "请以流式输入为主线"
        direction["input_fingerprint"] = "refined-fp"
        direction["red_lines"] = [{"text": "不要承诺做医疗数据", "source": "user"}]
        write_json(pack_path, pack)
        doc = self.generated_doc("dir_A", ["P1", "P2", None])
        doc["mode"] = "refined"
        doc["refined"] = {
            "core_intent": "把流式输入落到校园网", "calibration": ["教授组做过 P1"],
            "idea_zh": "把方法推进到流式输入场景", "variants": ["先看鲁棒性"],
            "mismatches": [], "gap_ids": [{"item_key": "P1", "gap_id": self.gap_ids["P1"]}]}
        doc["candidates"][0]["origin"] = "user_refined"
        doc["candidates"][0]["red_lines"] = ["不要承诺做医疗数据", " 不要承诺做医疗数据 "]
        out = self.stage3_finalize(self.results("s3-refined", {"dir_A": doc}),
                                   "--direction-id", "dir_A")
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        return out

    def results(self, name, docs):
        """Write one results dir and remember it for correction_finalize()."""
        self.results_dir = self.write_results(name, docs)
        return self.results_dir

    @staticmethod
    def finding(quote, severity="blocking", rule="B5"):
        return {"rule": rule, "severity": severity, "location": "validator 自报位置",
                "quote": quote, "suggestion": "首次出现时用日常语言解释。"}

    def validator_output(self, issues=(), verdict=None, file=None, artifact="candidates",
                         extra=None, entry_extra=None):
        """Write the style validator's own output shape — nothing pre-normalized."""
        blocking = [issue for issue in issues if issue.get("severity") == "blocking"]
        entry = {"file": str(file or (self.prof_dir / CANDIDATES_MD)),
                 "artifact": artifact,
                 "verdict": verdict or ("fail" if blocking else "pass"),
                 "blocking": len(blocking), "minor": 0, "issues": list(issues)}
        entry.update(entry_extra or {})
        payload = {"result": "ok", "files": [entry]}
        payload.update(extra or {})
        write_json(self.validation, payload)
        return self.validation

    def record(self):
        return parse(run_cli("stage3-record-validation", "--professor-dir", self.prof_dir,
                             "--validation-file", self.validation))

    def correction_plan(self, *extra):
        return parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root,
                             "--validation-file", self.validation, *extra))

    def correction_finalize(self, *extra):
        return parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                             "--program-root", self.root, "--results", self.results_dir,
                             "--validation-file", self.validation, *extra))

    def validator_block(self):
        return self.load_state().get("validator") or {}

    # -- 1. single direction: pass ---------------------------------------

    def test_pass_round_records_terminal_result_without_correction(self):
        first = self.render_single()
        self.validator_output([])
        out = self.record()
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["round"], 1)
        self.assertEqual(out["scopes"], [{"scope": "direction:dir_A", "result": "pass",
                                          "rounds": 1, "blocking": 0}])
        self.assertFalse(out["needs_correction"])
        self.assertTrue(out["terminal"])
        block = self.validator_block()
        self.assertEqual(block["results"]["dir_A"]["result"], "pass")
        self.assertEqual(block["results"]["dir_A"]["rounds"], 1)
        self.assertEqual(block["render_sha256"], first["md_sha256"])
        self.assertEqual(block["pending"], {})
        # A passing round is already terminal: planning with it yields no job.
        plan = self.correction_plan()
        self.assertEqual(plan["status"], "ok", msg=json.dumps(plan))
        self.assertEqual(plan["jobs"], [])
        self.assertEqual(plan["correction_scopes"], [])

    # -- 2. single direction: fail -> correction -> pass -----------------

    def test_fail_then_correction_then_pass_terminates_at_round_two(self):
        first = self.render_single()
        self.validator_output([self.finding("候选 dir_A_1")])
        recorded = self.record()
        self.assertEqual(recorded["round"], 1)
        self.assertTrue(recorded["needs_correction"])
        self.assertFalse(recorded["terminal"])
        block = self.validator_block()
        self.assertEqual(block["results"], {})
        self.assertEqual(list(block["pending"]), ["direction:dir_A"])
        self.assertEqual(block["pending"]["direction:dir_A"]["candidate_ids"], ["dir_A_1"])

        plan = self.correction_plan()
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["dir_A"])
        job = plan["jobs"][0]
        self.assertTrue(job["job_id"].startswith("candidates-correction:"))
        self.assertEqual(job["model_input"]["scope"],
                         {"kind": "direction", "direction_id": "dir_A"})
        self.assertEqual(job["model_input"]["validator_issues"][0]["quote"], "候选 dir_A_1")
        self.assertEqual(job["model_input"]["repairable_candidate_ids"], ["dir_A_1"])
        self.assertEqual(job["model_input"]["current_result"]["candidates"][0]["id"],
                         "dir_A_1")

        corrected = self.generated_doc("dir_A", ["P1", "P2", None])
        corrected["candidates"][0]["title"] = "候选 dir_A_1 改写"
        corrected["candidates"][0]["research_question"] = (
            "数据一条条到来时，方法还能否稳定收敛？")
        self.results("refined", {"dir_A": corrected})
        out = self.correction_finalize("--direction-id", "dir_A")
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["corrected"], ["dir_A"])
        self.assertNotEqual(out["md_sha256"], first["md_sha256"])
        after = self.validator_block()
        self.assertEqual(after["round"], 1, "a correction must not reset the round counter")
        self.assertEqual(after["pending"], {})
        self.assertEqual(after["render_sha256"], out["md_sha256"])

        self.validator_output([])
        second = self.record()
        self.assertEqual(second["round"], 2)
        self.assertTrue(second["terminal"])
        final = self.validator_block()
        self.assertEqual(final["results"]["dir_A"]["result"], "pass")
        self.assertEqual(final["results"]["dir_A"]["rounds"], 2)

    # -- 3. single direction: fail -> correction -> fail_after_2_rounds --

    def test_second_failing_round_is_terminal_and_blocks_a_third(self):
        self.render_single()
        self.validator_output([self.finding("候选 dir_A_1")])
        self.assertEqual(self.record()["round"], 1)
        self.results("refined-same", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None])})
        self.assertEqual(self.correction_finalize()["status"], "ok")
        self.validator_output([self.finding("候选 dir_A_1")])
        out = self.record()
        self.assertEqual(out["round"], 2)
        self.assertTrue(out["terminal"])
        block = self.validator_block()
        self.assertEqual(set(block["results"]), {"dir_A"})
        self.assertEqual(block["results"]["dir_A"], {
            **block["results"]["dir_A"], "result": "fail_after_2_rounds", "rounds": 2})
        self.assertEqual(block["results"]["dir_A"]["issues"][0]["quote"], "候选 dir_A_1")
        self.assertEqual(block["pending"], {})
        # The bounded cycle is closed: a third round is refused, not planned.
        self.validator_output([self.finding("候选 dir_A_1")])
        third = self.record()
        self.assertEqual(third["status"], "error")
        self.assertEqual(third["reason_code"], "validation_rounds_exhausted")
        plan = self.correction_plan()
        self.assertEqual(plan["status"], "error")
        self.assertEqual(plan["reason_code"], "validation_evidence_not_recorded")

    # -- 4. two directions: only the failed scope is corrected -----------

    def test_issue_in_second_direction_repairs_only_that_scope(self):
        self.render_two()
        self.validator_output([self.finding("候选 dir_B_2")])
        out = self.record()
        self.assertEqual([row["scope"] for row in out["scopes"]],
                         ["direction:dir_A", "direction:dir_B"])
        self.assertEqual(out["needs_correction"], True)
        block = self.validator_block()
        self.assertEqual(block["results"]["dir_A"]["result"], "pass")
        self.assertEqual(list(block["pending"]), ["direction:dir_B"])

        plan = self.correction_plan()
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["dir_B"])
        self.assertEqual(plan["correction_scopes"], ["direction:dir_B"])
        named_wrong = self.correction_plan("--direction-id", "dir_A")
        self.assertEqual(named_wrong["status"], "error")
        self.assertEqual(named_wrong["reason_code"], "validation_scope_not_in_evidence")

        before = {d["direction_id"]: d for d in self.load_state()["directions"]}
        corrected = self.generated_doc("dir_B", ["P1", "P3", None])
        corrected["candidates"][1]["title"] = "候选 dir_B_2 改写"
        self.results("refined-b", {"dir_B": corrected})
        out = self.correction_finalize()
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["corrected"], ["dir_B"])
        after = {d["direction_id"]: d for d in self.load_state()["directions"]}
        self.assertEqual(after["dir_A"], before["dir_A"])
        self.assertEqual(after["dir_B"]["candidates"][0], before["dir_B"]["candidates"][0])
        block = self.validator_block()
        self.assertEqual(block["results"]["dir_A"]["result"], "pass")
        self.assertEqual(block["results"]["dir_A"]["rounds"], 1)
        self.assertEqual(block["pending"], {})

    def test_wording_repeated_across_directions_repairs_every_scope(self):
        """1B: scope comes from the rendered text, not from a caller's guess."""
        self.render_two()
        self.validator_output([self.finding("流式输入")])
        self.assertEqual(self.record()["needs_correction"], True)
        plan = self.correction_plan()
        self.assertEqual(plan["correction_scopes"], ["direction:dir_A", "direction:dir_B"])
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["dir_A", "dir_B"])
        only_one = self.correction_plan("--direction-id", "dir_A")
        self.assertEqual(only_one["reason_code"], "validation_scope_not_in_evidence")

    # -- 5. refined mode: prose repairable, grounding immutable ----------

    def test_refined_prose_and_priority_are_repairable(self):
        self.render_refined()
        self.validator_output([self.finding("把方法推进到流式输入场景"),
                               self.finding("主推 1")])
        self.assertEqual(self.record()["needs_correction"], True)
        plan = self.correction_plan()
        job = plan["jobs"][0]
        self.assertEqual(job["model_input"]["repairable_candidate_ids"], [])
        self.assertEqual(job["model_input"]["current_result"]["mode"], "refined")

        doc = self.generated_doc("dir_A", ["P1", "P2", None])
        doc["mode"] = "refined"
        doc["priority"] = "主推 1（先做鲁棒性核对）"
        doc["refined"] = {"core_intent": "把流式输入落到校园网",
                          "calibration": ["教授组做过 P1"],
                          "idea_zh": "把一条条到来的数据接进同一套收敛判据",
                          "variants": ["先看鲁棒性"], "mismatches": [],
                          "gap_ids": [{"item_key": "P1", "gap_id": self.gap_ids["P1"]}]}
        doc["candidates"][0]["origin"] = "user_refined"
        doc["candidates"][0]["red_lines"] = ["不要承诺做医疗数据", " 不要承诺做医疗数据 "]
        self.results("refined-prose", {"dir_A": doc})
        out = self.correction_finalize()
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        state_dir = next(d for d in self.load_state()["directions"]
                         if d["direction_id"] == "dir_A")
        self.assertIn("一条条到来", state_dir["refined"]["idea_zh"])
        self.assertEqual(state_dir["refined"]["gap_ids"],
                         [{"item_key": "P1", "gap_id": self.gap_ids["P1"]}])
        self.assertEqual(state_dir["priority"], "主推 1（先做鲁棒性核对）")

    def test_refined_grounding_change_still_fails_closed(self):
        self.render_refined()
        self.validator_output([self.finding("主推 1")])
        self.assertEqual(self.record()["needs_correction"], True)
        doc = self.generated_doc("dir_A", ["P1", "P2", None])
        doc["mode"] = "refined"
        doc["priority"] = "主推 2"
        doc["refined"] = {"core_intent": "把流式输入落到校园网", "calibration": [],
                          "idea_zh": "把方法推进到流式输入场景", "variants": [],
                          "mismatches": [],
                          "gap_ids": [{"item_key": "P2", "gap_id": self.gap_ids["P2"]}]}
        doc["candidates"][0]["origin"] = "user_refined"
        self.results("refined-grounding", {"dir_A": doc})
        out = self.correction_finalize()
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "validation_correction_changed_machine_facts")

    def test_shared_red_line_is_deduplicated_by_the_renderer(self):
        """1C fix: label + dedup live in rendering, so no finding can target them."""
        self.render_refined()
        md = self.load_md()
        self.assertEqual(md.count("不要承诺做医疗数据"), 1)
        self.assertIn("方向级共享红线（只在这里写一次）：【方向】不要承诺做医疗数据", md)
        self.assertNotIn("【候选 1】不要承诺做医疗数据", md)
        # The machine facts stay exactly as recorded; only presentation changed.
        state_dir = next(d for d in self.load_state()["directions"]
                         if d["direction_id"] == "dir_A")
        self.assertEqual(state_dir["candidates"][0]["red_lines"],
                         ["不要承诺做医疗数据", " 不要承诺做医疗数据 "])

    # -- 6. cross-direction group ----------------------------------------

    def test_cross_direction_issue_routes_to_the_exact_group_id(self):
        self.render_cross()
        self.validator_output([self.finding("跨方向融合标题")])
        out = self.record()
        block = self.validator_block()
        self.assertEqual(list(block["pending"]), [f"group:{CROSS_GID}"])
        self.assertEqual(block["pending"][f"group:{CROSS_GID}"]["candidate_ids"], ["X1"])
        self.assertEqual(block["results"]["dir_A"]["result"], "pass")
        self.assertEqual(block["results"]["dir_B"]["result"], "pass")

        plan = self.correction_plan()
        self.assertEqual(plan["correction_scopes"], [f"group:{CROSS_GID}"])
        self.assertEqual([job["kind"] for job in plan["jobs"]], ["cross_direction"])
        job = plan["jobs"][0]
        self.assertEqual(job["group_id"], CROSS_GID)
        self.assertTrue(job["job_id"].startswith("cross-correction:"))
        self.assertEqual(job["model_input"]["scope"], {"kind": "group", "group_id": CROSS_GID})
        self.assertEqual(job["model_input"]["repairable_candidate_ids"], ["X1"])

        corrected = self.cross_candidate("X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
                                         gap_owner={"P2": "dir_A", "P3": "dir_B"})
        corrected["title"] = "跨方向融合标题 改写"
        write_json(self.results_dir / result_file("candidates", CROSS_GID),
                   self.cross_doc(["dir_A", "dir_B"], [corrected]))
        # The caller re-declares nothing: the group is repaired because the
        # evidence named it, not because --cross-direction-groups did.
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--program-root", self.root, "--results", self.results_dir,
                            "--validation-file", self.validation))
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["corrected"], [])
        self.assertEqual(out["corrected_groups"], [CROSS_GID])
        self.assertEqual([g["group_id"] for g in self.load_state()["cross_direction_groups"]],
                         [CROSS_GID])
        self.assertEqual(self.validator_block()["pending"], {})

    # -- 7. stale evidence ------------------------------------------------

    def test_evidence_must_bind_the_current_render(self):
        self.render_single()
        path = self.prof_dir / CANDIDATES_MD
        path.write_text(path.read_text(encoding="utf-8") + "\n人工改动一行\n", encoding="utf-8")
        self.validator_output([self.finding("候选 dir_A_1")])
        out = self.record()
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "validation_render_stale")

    def test_replay_after_a_replaced_render_fails_closed(self):
        self.render_single()
        self.validator_output([self.finding("候选 dir_A_1")])
        self.assertEqual(self.record()["round"], 1)
        # The direction's own evidence changed, so a fresh render replaces it.
        self.rewrite_pack_fingerprint("dir_A", "changed-after-validation")
        self.results("s3-regen", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None])})
        out = self.stage3_finalize(self.results_dir, "--direction-id", "dir_A")
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        replay = self.correction_plan()
        self.assertEqual(replay["status"], "error")
        self.assertEqual(replay["reason_code"], "validation_evidence_not_recorded")

    def test_source_change_still_needs_refresh_before_correction(self):
        self.render_single()
        self.validator_output([self.finding("候选 dir_A_1")])
        self.assertEqual(self.record()["round"], 1)
        self.rewrite_pack_fingerprint("dir_A", "changed-after-validation")
        payload = self.correction_plan()
        self.assertEqual(payload["status"], "needs_refresh")
        self.assertEqual(payload["reason_code"], "validation_source_changed")

    # -- 8. malformed handoff --------------------------------------------

    def test_raw_validator_handoff_fail_closed(self):
        self.render_single()
        cases = {
            "wrong file": lambda: self.validator_output([self.finding("候选 dir_A_1")],
                                                        file=self.prof_dir / "套磁候选分析.md"),
            "wrong artifact": lambda: self.validator_output([self.finding("候选 dir_A_1")],
                                                            artifact="analysis"),
            "no candidates entry": lambda: self.validator_output([], artifact="overview"),
            "fail verdict without a blocking issue": lambda: self.validator_output(
                [self.finding("候选 dir_A_1", severity="minor")], verdict="fail"),
            "blocking issue under a pass verdict": lambda: self.validator_output(
                [self.finding("候选 dir_A_1")], verdict="pass"),
            "issue without a quote": lambda: self.validator_output(
                [{"rule": "B5", "severity": "blocking", "location": "第 20 行"}]),
            "quote outside the bound render": lambda: self.validator_output(
                [self.finding("这句话渲染结果里根本没有")]),
        }
        for label, write in cases.items():
            with self.subTest(case=label):
                write()
                out = self.record()
                self.assertEqual(out["status"], "error", msg=json.dumps(out, ensure_ascii=False))
                self.assertIn(out["reason_code"],
                              {"invalid_validation_json", "validation_quote_not_in_render"})
                self.assertNotIn("validator", self.load_state())

        write_json(self.validation, {"results": [{"direction_id": "dir_A", "result": "pass",
                                                   "rounds": 1, "issues": []}]})
        caller_authored = self.record()
        self.assertEqual(caller_authored["status"], "error")
        self.assertEqual(caller_authored["reason_code"], "invalid_validation_json")

    def test_correction_cannot_skip_or_add_scopes(self):
        self.render_two()
        self.validator_output([self.finding("候选 dir_B_2")])
        self.assertEqual(self.record()["round"], 1)
        self.results("refined-b", {
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        for label, args in [("skip", ("--skip-direction-ids", "dir_A")),
                            ("new group", ("--cross-direction-groups", CROSS_GROUP))]:
            with self.subTest(case=label):
                out = self.correction_finalize(*args)
                self.assertEqual(out["status"], "error")
                self.assertEqual(out["reason_code"], "invalid_params")
        planned = self.correction_plan("--skip-direction-ids", "dir_A")
        self.assertEqual(planned["reason_code"], "invalid_params")

    # -- 9. machine facts -------------------------------------------------

    def test_machine_fact_mutation_during_correction_fails_closed(self):
        self.render_single()
        self.validator_output([self.finding("候选 dir_A_1")])
        self.assertEqual(self.record()["round"], 1)
        broken = self.generated_doc("dir_A", ["P1", "P2", None])
        broken["candidates"][0]["gap_refs"] = []
        self.results("refined-broken", {"dir_A": broken})
        out = self.correction_finalize()
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "validation_correction_changed_machine_facts")

        reattributed = self.generated_doc("dir_A", ["P1", "P2", None])
        reattributed["candidates"][1]["fit"] = "low"
        reattributed["candidates"][1]["red_lines"] = ["临时加一条红线"]
        self.results("refined-anchors", {"dir_A": reattributed})
        out = self.correction_finalize()
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "validation_correction_changed_machine_facts")

    def test_prose_edit_on_an_unnamed_candidate_fails_closed(self):
        self.render_single()
        self.validator_output([self.finding("候选 dir_A_1")])
        self.assertEqual(self.record()["round"], 1)
        smuggled = self.generated_doc("dir_A", ["P1", "P2", None])
        smuggled["candidates"][0]["title"] = "候选 dir_A_1 改写"
        smuggled["candidates"][1]["why_recommended"] = "顺手改写了一个未被点名的候选"
        self.results("refined-smuggled", {"dir_A": smuggled})
        out = self.correction_finalize()
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "validation_correction_changed_untouched_candidate")

    # -- 10. the record is the producer's, not the caller's ---------------

    def test_second_validator_round_requires_completed_correction(self):
        self.render_single()
        self.validator_output([self.finding("候选 dir_A_1")])
        first = self.record()
        self.assertEqual(first["round"], 1)
        self.assertTrue(first["needs_correction"])

        state_path = self.prof_dir / CANDIDATE_STATE
        before_bytes = state_path.read_bytes()
        before_validator = json.loads(json.dumps(
            self.validator_block(), ensure_ascii=False))

        # A second validator result cannot substitute for the required
        # correction transition, even if that second result says pass.
        self.validator_output([])
        rejected = self.record()
        self.assertEqual(rejected["status"], "error")
        self.assertEqual(rejected["reason_code"], "validation_correction_required")
        self.assertEqual(state_path.read_bytes(), before_bytes)
        self.assertEqual(self.validator_block(), before_validator)

    def test_round_and_terminal_result_are_derived_not_supplied(self):
        self.render_two()
        # Junk a caller might invent is ignored: the runner reads only verdict,
        # issues, and its own round counter.
        self.validator_output([self.finding("候选 dir_A_1")],
                              extra={"schema": 99, "summary": {"direction_id": "dir_B"}},
                              entry_extra={"result": "pass", "rounds": 7,
                                           "direction_id": "dir_B"})
        out = self.record()
        self.assertEqual(out["round"], 1)
        block = self.validator_block()
        self.assertEqual(block["raw_verdict"], "fail")
        self.assertEqual(block["results"]["dir_B"]["rounds"], 1)
        self.assertEqual(block["results"]["dir_B"]["result"], "pass")
        self.assertEqual(list(block["pending"]), ["direction:dir_A"])

        # The second validator round is legal only after the runner-authorized
        # correction plan/finalize transition clears pending while preserving
        # the round counter.
        plan = self.correction_plan()
        self.assertEqual(plan["correction_scopes"], ["direction:dir_A"])
        corrected = self.generated_doc("dir_A", ["P1", "P2", None])
        corrected["candidates"][0]["title"] = "候选 dir_A_1 改写"
        self.results("round-derived-correction", {"dir_A": corrected})
        correction = self.correction_finalize()
        self.assertEqual(correction["status"], "ok",
                         msg=json.dumps(correction, ensure_ascii=False))
        after_correction = self.validator_block()
        self.assertEqual(after_correction["round"], 1)
        self.assertEqual(after_correction["pending"], {})

        self.validator_output([])
        self.assertEqual(self.record()["round"], 2)
        final = self.validator_block()
        self.assertEqual(sorted(final["results"]), ["dir_A", "dir_B"])
        self.assertEqual(final["results"]["dir_A"], {
            **final["results"]["dir_A"], "result": "pass", "rounds": 2})
        # The frozen runtime contract reads exactly this shape.
        self.assertEqual(set(final["results"]), {"dir_A", "dir_B"})
        for row in final["results"].values():
            self.assertEqual({"result", "rounds", "issues"} <= set(row), True)


if __name__ == "__main__":
    import unittest
    unittest.main()
