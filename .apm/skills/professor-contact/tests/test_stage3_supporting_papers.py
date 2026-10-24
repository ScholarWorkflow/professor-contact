"""Stage 3 consumes existing direction facts without equating papers to FW anchors."""
import copy

from test_stage3_direction_groups import Stage3DirectionGroupBase, contact_state
from test_stage2_resolved_direction import write_json


class SupportingPaperSelectionTests(Stage3DirectionGroupBase):
    def test_plan_projects_only_direction_facts_and_preserves_availability(self):
        pack = self.load_pack()
        facts = {"contributions": ["A concrete foundation independent of the FW anchor"],
                 "methods": ["Existing signal method"], "limitations": ["Static inputs only"]}
        pack["papers"]["P2"].update(paper_facts=facts, facts_state="valid",
                                    analysis_level="fulltext")
        # P2 remains a support paper but has no future-work anchor in direction A.
        for field in ("gap_shortlist", "gaps_excluded", "completed_gap_blacklist"):
            pack["directions"][0][field] = [
                gap for gap in pack["directions"][0].get(field, [])
                if gap["item_key"] != "P2"]
        for state in ("unavailable", "failed", None):
            with self.subTest(facts_state=state):
                pack["papers"]["P1"].update(paper_facts={"contributions": ["untrusted"]},
                                            facts_state=state, analysis_level="abstract")
                write_json(self.prof_dir / "套磁候选输入.json", pack)
                plan = self.stage3_plan()
                self.assertEqual(plan["status"], "ok", plan)
                inputs = {job["direction_id"]: job["model_input"] for job in plan["jobs"]}
                papers = {p["item_key"]: p for p in inputs["dir_A"]["supporting_papers"]}
                self.assertEqual(set(papers), {"P1", "P2"})
                self.assertEqual(papers["P2"]["paper_facts"], facts)
                self.assertEqual(papers["P2"]["facts_state"], "valid")
                self.assertEqual(papers["P2"]["analysis_level"], "fulltext")
                self.assertEqual(papers["P1"]["facts_state"], state)
                self.assertEqual(papers["P1"]["analysis_level"], "abstract")
                self.assertIsNone(papers["P1"]["paper_facts"])
                self.assertNotIn("P2", {g["item_key"] for g in inputs["dir_A"]["gaps"]})
                self.assertNotIn("P2", {p["item_key"] for p in inputs["dir_B"]["supporting_papers"]})
        pack["papers"]["P1"].update(facts_state="valid", paper_facts=None,
                                    analysis_level=None)
        write_json(self.prof_dir / "套磁候选输入.json", pack)
        paper = self.stage3_plan()["jobs"][0]["model_input"]["supporting_papers"][0]
        self.assertIsNone(paper["paper_facts"])
        self.assertIsNone(paper["analysis_level"])

    def test_non_anchor_support_single_paper_and_current_contract_reuse(self):
        doc = self.generated_doc("dir_A", ["P1", "P2", None])
        doc["candidates"][0]["papers"] = [{"item_key": "P2", "direction_ids": ["dir_A"],
                                             "role": "基座", "fit_note": "已有方法提供基础"}]
        results = self.write_results("support", {"dir_A": doc,
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        result = self.stage3_finalize(results)
        self.assertEqual(result["status"], "ok", result)
        state = self.load_state()
        self.assertEqual(state["generator_contract_version"], "stage3-ideas-v3")
        candidate = state["directions"][0]["candidates"][0]
        self.assertEqual([p["item_key"] for p in candidate["papers"]], ["P2"])
        self.assertEqual(candidate["gap_refs"][0]["item_key"], "P1")
        self.assertEqual({d["action"] for d in self.stage3_plan()["directions"]}, {"reuse"})
        for legacy_schema in (False, True):
            with self.subTest(legacy_schema=legacy_schema):
                old = copy.deepcopy(state)
                old["generator_contract_version"] = "stage3-ideas-v2"
                if legacy_schema:
                    old["schema"] = 1
                    old.pop("generator_contract_version")
                for direction in old["directions"]:
                    direction["generator_contract_version"] = "stage3-ideas-v2"
                write_json(self.prof_dir / "套磁候选状态.json", old)
                plan = self.stage3_plan()
                self.assertEqual(plan["status"], "ok", plan)
                self.assertEqual({d["action"] for d in plan["directions"]}, {"process"})
                normalized, error = contact_state.normalize_candidate_state(old, self.load_pack())
                self.assertIsNone(error)
                self.assertEqual(normalized["generator_contract_version"], old.get("generator_contract_version"))
                self.assertEqual({d["generator_contract_version"] for d in normalized["directions"]},
                                 {"stage3-ideas-v2"})

    def test_partial_refresh_does_not_upgrade_unselected_direction(self):
        results = self.write_results("partial", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        self.assertEqual(self.stage3_finalize(results)["status"], "ok")
        old = self.load_state()
        old["generator_contract_version"] = "stage3-ideas-v2"
        for direction in old["directions"]:
            direction.pop("generator_contract_version", None)
        write_json(self.prof_dir / "套磁候选状态.json", old)
        self.assertEqual(self.stage3_finalize(results, "--direction-id", "dir_A")["status"], "ok")
        state = self.load_state()
        by_id = {d["direction_id"]: d for d in state["directions"]}
        self.assertEqual(by_id["dir_A"]["generator_contract_version"], "stage3-ideas-v3")
        self.assertEqual(by_id["dir_B"]["generator_contract_version"], "stage3-ideas-v2")
        self.assertEqual(by_id["dir_B"]["candidates"], old["directions"][1]["candidates"])
        plan = self.stage3_plan()
        self.assertEqual({d["direction_id"]: d["action"] for d in plan["directions"]},
                         {"dir_A": "reuse", "dir_B": "process"})
        # Finalize independently applies the gate, even if called without plan.
        refreshed = self.stage3_finalize(results, "--direction-id", "dir_B")
        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertEqual({d["action"] for d in self.stage3_plan()["directions"]}, {"reuse"})
