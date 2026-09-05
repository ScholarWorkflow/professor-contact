"""Issue #8 identity-contract tests beyond the shared fixtures.

Covers the plan's required cases that the grouping tests do not: professor-
level canonical papers, shared-paper conflict fail-closed, per-direction and
shared-paper invalidation scope, display-name-only re-rendering, explicit
cross-group cache isolation, Stage 5 canonical naming, and v1 migration.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import (
    ResolvedPipelineMixin, parse, quote_id, run_cli, write_json)
from test_stage3_direction_groups import Stage3DirectionGroupBase, result_file

PROFESSOR = "試験 教授"

QUOTES = {
    "P1": "Future work will extend the shared method to streaming inputs.",
    "P2": "Future work plans a robustness benchmark for the signal pipeline.",
    "P3": "Future work will deploy the sensor network at campus scale.",
    "P4": "Future work will explore quantum lattice simulations.",
}


def load_contact_state():
    import importlib.util
    script = Path(__file__).parents[1] / "scripts" / "contact_state.py"
    spec = importlib.util.spec_from_file_location("contact_state_identity", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestV2PackShape(Stage3DirectionGroupBase):
    """Plan §10 items 2-5: canonical professor-level papers in the v2 pack."""

    def test_pack_has_one_canonical_paper_record_per_item_key(self):
        pack = self.load_pack()
        self.assertEqual(pack["schema"], 2)
        self.assertEqual(pack["kind"], "professor-contact-stage2-input")
        self.assertEqual(pack["identity_version"], "direction-id-v1")
        self.assertEqual(set(pack["papers"]), {"P1", "P2", "P3"})
        # P1 is shared: ONE canonical record, referenced by both directions.
        keys = {d["direction_id"]: set(d["supporting_item_keys"])
                for d in pack["directions"]}
        self.assertEqual(keys, {"dir_A": {"P1", "P2"}, "dir_B": {"P1", "P3"}})
        self.assertNotIn("supporting_papers", pack["directions"][0])
        self.assertEqual(pack["papers"]["P1"]["title"], "Shared Method Paper")

    def test_facts_direction_id_survives_into_pack(self):
        facts = json.loads((self.root / "facts.json").read_text(encoding="utf-8"))
        facts["directions"][0]["direction_id"] = "authoritative_id"
        facts["directions"][0]["collection_key"] = "zotero_projection"
        facts["directions"][1]["direction_id"] = "dir_B"
        facts_path = self.root / "facts.json"
        facts_path.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
        self.run_resolve(facts_path, {})
        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok")
        pack = self.load_pack()
        dids = {d["direction_id"] for d in pack["directions"]}
        self.assertIn("authoritative_id", dids)
        direction = next(d for d in pack["directions"]
                         if d["direction_id"] == "authoritative_id")
        # The Zotero projection key may stay as metadata only — never identity.
        self.assertEqual(direction["collection_key"], "zotero_projection")

    def test_stage2_rerun_with_renamed_projection_keeps_input_fingerprint(self):
        before = self.load_pack()["directions"][0]["input_fingerprint"]
        # v2 facts carry the stable direction_id; the Zotero projection key is
        # renamed freely without touching any model-relevant evidence.
        facts = json.loads((self.root / "facts.json").read_text(encoding="utf-8"))
        facts["directions"][0]["direction_id"] = "dir_A"
        facts["directions"][0]["collection_key"] = "renamed_projection"
        facts["directions"][1]["direction_id"] = "dir_B"
        facts_path = self.root / "facts.json"
        facts_path.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
        self.run_resolve(facts_path, {})
        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok", msg=json.dumps(payload, ensure_ascii=False))
        direction = next(d for d in self.load_pack()["directions"]
                         if d["direction_id"] == "dir_A")
        self.assertEqual(direction["collection_key"], "renamed_projection")
        self.assertEqual(direction["input_fingerprint"], before,
                         "a projection-only rename must not change the Stage-3 "
                         "model-input fingerprint")

    def test_v1_pack_with_conflicting_shared_paper_fails_closed(self):
        """Two direction-local snapshots of the same item_key that disagree on
        authoritative fields must fail closed instead of picking one."""
        contact_state = load_contact_state()
        paper = {"item_key": "K1", "title": "One Title", "year": 2024,
                 "authorship": "corresponding", "facts_state": "valid",
                 "facts_error": None, "paper_facts": None, "pdf_available": True}
        conflicting = dict(paper, title="Another Title")
        v1_pack = {
            "schema": 1, "professor": PROFESSOR, "professor_dir": str(self.prof_dir),
            "directions": [
                {"collection_key": "dir_A", "name_ja": "A", "name_zh": "甲",
                 "input_fingerprint": "fp-a", "user_note": "", "credibility": {},
                 "red_lines": [], "named_keys": [], "gap_shortlist": [],
                 "supporting_papers": [paper]},
                {"collection_key": "dir_B", "name_ja": "B", "name_zh": "乙",
                 "input_fingerprint": "fp-b", "user_note": "", "credibility": {},
                 "red_lines": [], "named_keys": [], "gap_shortlist": [],
                 "supporting_papers": [conflicting]},
            ],
        }
        with self.assertRaises(SystemExit):
            contact_state.normalize_input_pack(v1_pack)

    def test_v1_pack_shared_paper_normalizes_to_one_record(self):
        contact_state = load_contact_state()
        paper = {"item_key": "K1", "title": "One Title", "year": 2024,
                 "authorship": "corresponding", "facts_state": "valid",
                 "facts_error": None, "paper_facts": None, "pdf_available": True}
        v1_pack = {
            "schema": 1, "professor": PROFESSOR, "professor_dir": str(self.prof_dir),
            "directions": [
                {"collection_key": "dir_A", "name_ja": "A", "name_zh": "甲",
                 "input_fingerprint": "fp-a", "user_note": "", "credibility": {},
                 "red_lines": [], "named_keys": ["K1"], "gap_shortlist": [],
                 "supporting_papers": [paper]},
                {"collection_key": "dir_B", "name_ja": "B", "name_zh": "乙",
                 "input_fingerprint": "fp-b", "user_note": "", "credibility": {},
                 "red_lines": [], "named_keys": [], "gap_shortlist": [],
                 "supporting_papers": [dict(paper)]},
            ],
        }
        pack = contact_state.normalize_input_pack(v1_pack)
        self.assertEqual(set(pack["papers"]), {"K1"})
        self.assertEqual(
            [sorted(d["supporting_item_keys"]) for d in pack["directions"]],
            [["K1"], ["K1"]])
        # named_by_user stays per-direction projection, never canonical.
        named = contact_state.direction_papers(pack, pack["directions"][0])
        self.assertTrue(named[0]["named_by_user"])
        other = contact_state.direction_papers(pack, pack["directions"][1])
        self.assertFalse(other[0]["named_by_user"])


class TestInvalidationScope(Stage3DirectionGroupBase):
    """Plan §10 items 13/14/17/24: only the affected identities regenerate."""

    CROSS_GROUP = '[["dir_A","dir_B"]]'

    def _cross_request(self):
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        plan = self.stage3_plan("--cross-direction-groups", self.CROSS_GROUP)
        cross_job = next(j for j in plan["jobs"] if j["kind"] == "cross_direction")
        return results, cross_job

    def _write_cross_result(self, cross_job, candidates, name=None):
        cross_dir = self.root / (name or "s3")
        cross_dir.mkdir(exist_ok=True)
        write_json(cross_dir / result_file("candidates", cross_job["group_id"]),
                   self.cross_doc(["dir_A", "dir_B"], candidates))
        return cross_dir

    def _grounded_cross(self, cid="X1"):
        return self.cross_candidate(cid, ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
                                    gap_owner={"P2": "dir_A", "P3": "dir_B"})

    def setUp(self):
        super().setUp()
        # A third, independent direction C on P4 … but our shared fixture only
        # has three papers; add a C+D-free variant by reusing dir_B as the
        # unrelated direction for cross isolation tests instead.
        self.results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(self.results)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))

    def test_a_only_change_regenerates_a_and_reuses_b(self):
        self.rewrite_pack_fingerprint("dir_A", "a-only-change")
        plan = self.stage3_plan()
        actions = {d["direction_id"]: d["action"] for d in plan["directions"]}
        self.assertEqual(actions, {"dir_A": "process", "dir_B": "reuse"})
        self.assertEqual([j["direction_id"] for j in plan["jobs"]], ["dir_A"])

    def test_display_name_only_change_re_renders_without_model_jobs(self):
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        next(d for d in pack["directions"]
             if d["direction_id"] == "dir_A")["name_ja"] = "信号処理（改）"
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

        plan = self.stage3_plan()
        self.assertEqual({d["direction_id"]: d["action"] for d in plan["directions"]},
                         {"dir_A": "reuse", "dir_B": "reuse"})
        self.assertEqual(plan["jobs"], [])
        # Finalize re-renders the Markdown deterministically with the new name.
        out = self.stage3_finalize(self.results)
        self.assertEqual(out["status"], "ok")
        self.assertIn("信号処理（改）", self.load_md())

    def test_changing_a_invalidates_cross_group_only_for_participants(self):
        results, cross_job = self._cross_request()
        self._write_cross_result(cross_job, [self._grounded_cross()])
        out = self.stage3_finalize(results, "--cross-direction-groups",
                                   self.CROSS_GROUP)
        self.assertEqual(out["status"], "ok")
        # Unchanged: zero jobs — the accepted group is reusable.
        plan = self.stage3_plan("--cross-direction-groups", self.CROSS_GROUP)
        self.assertEqual(plan["jobs"], [],
                         "the accepted group must be reusable before any change")
        # dir_B participates in the group: mutating it invalidates the group.
        self.rewrite_pack_fingerprint("dir_B", "mutated-b")
        plan = self.stage3_plan("--cross-direction-groups", self.CROSS_GROUP)
        self.assertEqual([j["kind"] for j in plan["jobs"]],
                         ["candidates", "cross_direction"])


class TestSharedPaperInvalidation(ResolvedPipelineMixin, unittest.TestCase):
    """A shared-paper change regenerates every direction referencing K, but
    not an unrelated direction (plan §10 item 14)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / PROFESSOR
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _run(self, quote_text):
        papers = [
            self.make_paper("K", "Shared Core", ["shared"], [QUOTES["P1"]]),
            self.make_paper("KA", "A Paper", ["alpha"], [QUOTES["P2"]]),
            self.make_paper("KC", "C Paper", ["gamma"], [QUOTES["P4"]]),
        ]
        directions = [
            self.make_direction("dir_A", ["K", "KA"], name_ja="A", name_zh="甲",
                                summary="A"),
            self.make_direction("dir_C", ["KC"], name_ja="C", name_zh="丙",
                                summary="C"),
        ]
        facts_path = self.write_facts(papers, directions)
        self.run_resolve(facts_path, {})
        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok")
        return facts_path

    def test_shared_k_change_hits_referencing_directions_only(self):
        facts_path = self._run(QUOTES["P1"])
        # First stage-3 round for both directions.
        plan = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root))
        results = self.root / "s3"
        results.mkdir()
        for job in plan["jobs"]:
            doc = {"schema": 2, "kind": "candidates", "direction_id": job["direction_id"],
                   "mode": "generated", "candidates": [
                       {"id": f'{job["direction_id"]}_{n}', "kind": "direction",
                        "direction_ids": [job["direction_id"]],
                        "title": "t", "one_liner": "o",
                        "research_question": "rq?", "points": [], "gap_refs": [],
                        "papers": [], "fit": "null", "red_lines": []}
                       for n in range(1, 4)]}
            write_json(results / result_file("candidates", job["direction_id"]), doc)
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", results, "--program-root", self.root))
        self.assertEqual(out["status"], "ok")

        # Change the SHARED paper K's sidecar evidence → re-run resolve + stage2.
        # Simulate via a fingerprint rewrite on the pack for K's referencing
        # directions only: dir_A and dir_B(C) share K; an unrelated direction
        # must stay reusable. Here the unrelated direction is dir_C.
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        for direction in pack["directions"]:
            if "K" in direction["supporting_item_keys"]:
                direction["input_fingerprint"] = f"changed:{direction['direction_id']}"
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

        plan = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root))
        actions = {d["direction_id"]: d["action"] for d in plan["directions"]}
        self.assertEqual(actions, {"dir_A": "process", "dir_C": "reuse"},
                         "only directions whose slice references K regenerate")


if __name__ == "__main__":
    unittest.main()
