"""Tests for the Stage-2 raw style report handoff and one-round correction.

Besides the existing raw-report handoff coverage this module implements the two
targets of the current plan (``plan/stage2-three-runner-defects-implementation-plan.md``
§5.1): T4 repeated-quote line locations / ambiguous reports and T5 business
re-render with a bounded correction lifecycle.
"""
import copy
import json
import shutil
import tempfile
from pathlib import Path

from stage2_upstream_fixture import prepare_stage2_proof

from test_contact_state import (
    BaseEnv,
    contact_stage1,
    contact_state,
    parse,
    quote_id,
    run_bound_stage2_finalize,
    run_cli,
    stage2_style_validation_report,
)

# The T5 fixture produces its one accepted member change through the real
# resolve chain (plan §3.1.6/§5.1 T5.1); only that module's top-level helper
# functions are reused, never its TestCase classes.
from test_stage2_resolved_direction import (
    finalize_resolve,
    make_facts_sidecar,
    new_resolve_results_dir,
    plan_resolve,
    write_resolve_results,
)

# T4 (plan §3.2): one quote that must be locatable on three physical lines.
_T4_REPEAT_QUOTE = "合成输入对照句"
# A quote that occurs exactly once, addressed by the legacy short-text location.
_T4_LEGACY_TEXT_QUOTE = "唯一合成句用于旧文本定位"

# T5 (plan §3.1/§3.4.1): synthetic old-semantics pack with a relevant-only paper
# in membership, then two-direction corrections on the re-rendered version.
_T5_MEMBER_KEYS = ["AAAA1111", "BBBB2222"]
_T5_LEGACY_KEY = "CCCC3333"
# The one member change accepted through the formal resolve entry: an ORIGINAL
# member of the second direction is removed with current full-text evidence
# (plan §3.1.1/§3.1.6, §5.1 T5.1).
_T5_ACCEPTED_REMOVAL_KEY = "BBBB2222"
_T5_LEGACY_QUOTE = "旧版第一处待改文字"
_T5_LEGACY_REVISED = "旧版第一处已改文字"
_T5_LEGACY_FINAL = "旧版第一处最终文字"
_T5_SECOND_QUOTE = "第二方向待改文字"
_T5_SECOND_REVISED = "第二方向已改文字"


class Stage2ValidationHandoffTests(BaseEnv):
    def write_validation(self, name, verdict="fail", quote="教授从", severity="blocking",
                         location=None):
        issues = []
        if quote:
            issues.append({
                "rule": "A1",
                "severity": severity,
                "location": location or quote,
                "quote": quote,
                "suggestion": "改用日常语言解释。",
            })
        report = stage2_style_validation_report(
            self.prof_dir / "套磁候选分析.md", verdict, issues)
        path = self.root / name
        path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        return path

    def record_validation(self, path):
        return parse(run_cli("stage2-record-validation", "--professor-dir", self.prof_dir,
                             "--validation-file", path))

    def assert_direction_not_accepted(self, direction_id):
        direction = self.stage2_preflight_direction(direction_id)
        self.assertIn("validator_not_accepted", direction["reason_codes"])

    def assert_no_accepted_validation(self, direction_id):
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        results = pack.get("validator", {}).get("results", {})
        record = results.get(direction_id, {})
        self.assertNotIn(record.get("result"), {"pass", "skipped"}, record)

    def rewrite_direction(self, direction_id, before, after):
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        direction = next(d for d in pack["directions"]
                         if d["direction_id"] == direction_id)
        narrative = direction["narrative"]
        block = copy.deepcopy(narrative["positioning"][0])
        self.assertIn(before, block["text"])
        block["text"] = block["text"].replace(before, after, 1)
        rewrite = {
            "schema": 1,
            "kind": "narrative-rewrite",
            "direction_id": direction_id,
            "collection_key": direction["collection_key"],
            "positioning": [block],
            "gap_notes": [
                {"gap_id": gap_id, "summary": value["summary"],
                 "explanation": value["explanation"]}
                for gap_id, value in narrative["gap_notes"].items()
            ],
        }
        results = self.root / f"rewrite-{direction_id}"
        results.mkdir()
        (results / f"narrative-rewrite-{direction_id}.json").write_text(
            json.dumps(rewrite, ensure_ascii=False), encoding="utf-8")
        return results

    # -- helpers shared by the T4/T5 scenarios (plan §5.1) -------------------

    def _fresh_stage2_env(self):
        """One independent BaseEnv instance for an isolated synthetic state.

        ``unittest.TestCase`` refuses a method name the class does not define,
        so the container reuses this instance's real test name and only runs its
        ``setUp()``; the inner test method itself is never executed here, and its
        teardown is registered once on the outer test.
        """
        env = self.__class__(self._testMethodName)
        env.setUp()
        self.addCleanup(env.tearDown)
        return env

    def write_validation_issues(self, name, issues, verdict=None):
        """Raw ``result/files/notes`` report carrying exactly these issues."""
        issues = [dict(issue) for issue in issues]
        if verdict is None:
            verdict = ("fail" if any(issue.get("severity") == "blocking" for issue in issues)
                       else "pass_with_minor" if issues else "pass")
        report = stage2_style_validation_report(
            self.prof_dir / "套磁候选分析.md", verdict, issues)
        path = self.root / name
        path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        return path

    def _blocking_issue(self, quote, location):
        return {"rule": "A1", "severity": "blocking", "location": location,
                "quote": quote, "suggestion": "改用日常语言解释。"}

    def _analysis_lines(self):
        return (self.prof_dir / "套磁候选分析.md").read_text(encoding="utf-8").splitlines()

    def _physical_line_of(self, needle, expected=1):
        """Physical (frontmatter included) line numbers holding ``needle``."""
        hits = [index + 1 for index, line in enumerate(self._analysis_lines())
                if needle in line]
        self.assertEqual(len(hits), expected, (needle, hits))
        return hits if expected > 1 else hits[0]

    def _pack_direction(self, payload, direction_id):
        return next(row for row in payload["directions"]
                    if row["direction_id"] == direction_id)

    def _issue_line(self, issue):
        """Physical line an already recorded issue points at."""
        location = issue["location"]
        self.assertNotIsInstance(location, bool, issue)
        if isinstance(location, int):
            return location
        text = str(location).strip()
        if text.isascii() and text.isdigit():
            return int(text)
        if text.startswith("第") and text.endswith("行") and text[1:-1].isdigit():
            return int(text[1:-1])
        return self._physical_line_of(issue["quote"])

    def _section_owner(self, line_number):
        """Direction whose rendered section owns one physical analysis line."""
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        headings = [index for index, line in enumerate(self._analysis_lines())
                    if line.startswith("## 方向 ")]
        owned = [position for position, heading in enumerate(headings)
                 if heading < line_number - 1]
        self.assertTrue(owned, line_number)
        return pack["directions"][owned[-1]]["direction_id"]

    # -- T4 fixture: one quote on three repairable physical lines -----------

    def _t4_two_direction_body(self):
        """Normally generated managed body with the repeat quote on three lines."""
        def add_second_direction(facts):
            # Plan §3.1.1/§5.1 T4: the formal members come only from the
            # direction's original `provisional_member_keys`; the product must
            # not fall back to `member_keys`. The synthetic T4 facts therefore
            # state that source explicitly for both directions (the second one
            # inherits it through the deep copy below).
            first = facts["directions"][0]
            first["provisional_member_keys"] = list(first["member_keys"])
            second = copy.deepcopy(first)
            second["collection_key"] = "DIR00002"
            second["name_ja"] = "第二合成方向"
            second["name_zh"] = "第二合成方向"
            second["user_note"] = "第二方向的合成输入笔记。"
            facts["directions"].append(second)

        facts_path = self.write_facts(add_second_direction)
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        results = self.root / "t4-results"
        self.write_stage2_results(results, directions=facts["directions"])
        gap_notes = [{"gap_id": quote_id(self.gap_quotes["AAAA1111"]),
                      "summary": "扩展到第二种输入模式",
                      "explanation": "研究计划比较另一种合成场景。"}]
        narrative = {"schema": 1, "kind": "narrative", "directions": [
            {"direction_id": "DIR00001", "collection_key": "DIR00001", "positioning": [
                {"kind": "para", "text": f"{_T4_REPEAT_QUOTE}是合成比较的第一处复现。",
                 "refs": [], "concrete_object": "合成输入与第二种模式",
                 "input_example": "输入一组固定的合成样本",
                 "output_example": "系统给出两种处理结果"},
                {"kind": "para", "text": "第二处复现写在具体对象字段里。",
                 "refs": [], "concrete_object": f"与{_T4_REPEAT_QUOTE}对照的合成对象",
                 "input_example": "输入第二组固定的合成样本",
                 "output_example": "系统给出对照后的处理结果"},
            ], "gap_notes": copy.deepcopy(gap_notes)},
            {"direction_id": "DIR00002", "collection_key": "DIR00002", "positioning": [
                {"kind": "para", "text": "第二方向把复现放进输入示例。", "refs": [],
                 "concrete_object": "第二方向的合成对象",
                 "input_example": f"输入包含{_T4_REPEAT_QUOTE}的合成样本",
                 "output_example": "系统给出第二方向的处理结果"},
                {"kind": "para", "text": "第二方向的旧写法定位段落。", "refs": [],
                 "concrete_object": _T4_LEGACY_TEXT_QUOTE,
                 "input_example": "输入第二方向的旧样本",
                 "output_example": "系统给出旧写法的处理结果"},
            ], "gap_notes": copy.deepcopy(gap_notes)},
        ]}
        (results / "narrative.json").write_text(
            json.dumps(narrative, ensure_ascii=False), encoding="utf-8")
        plan = parse(self.run_bound_stage2_plan(facts_path))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(run_cli, facts_path, "--results", results))
        self.assertEqual(finalized["status"], "ok", finalized)
        return facts_path

    # -- T5 fixtures: old-semantics pack and the re-rendered version --------

    def _t6_prepare(self, facts_path, proof_path=None):
        """Bind this lifecycle round to a real, exclusive consumption run."""
        if proof_path is None:
            proof_path = prepare_stage2_proof(run_cli, facts_path)
        run_dir = Path(tempfile.mkdtemp(prefix="t6-consumption-", dir=self.root))
        prepared = parse(run_cli(
            "stage2-consumption-prepare", "--program-root", self.root,
            "--professor", "試験 教授", "--target-file", self.prof_dir / "套磁目标.json",
            "--preflight-file", proof_path, "--run-dir", run_dir))
        self.assertEqual(prepared["status"], "ok", prepared)
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        facts["stage2_preflight"]["consumption"] = {
            "file": prepared["consumption_file"], "run_id": prepared["run_id"],
            "sources_sha256": prepared["sources_sha256"]}
        Path(facts_path).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        return proof_path

    def _t6_plan(self, facts_path, proof_path):
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        run_dir = Path(facts["stage2_preflight"]["consumption"]["file"]).parent
        return parse(run_cli("stage2-plan", "--facts", facts_path,
                             "--preflight-file", proof_path, "--run-dir", run_dir))

    def _t6_seal(self, facts_path, results):
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        run_dir = Path(facts["stage2_preflight"]["consumption"]["file"]).parent
        sealed = parse(run_cli("stage2-consumption-seal-results", "--run-dir", run_dir,
                               "--results-dir", results))
        self.assertEqual(sealed["status"], "ok", sealed)

    def _t5_write_facts(self):
        """Facts whose ORIGINAL members exclude the relevant-only paper."""
        def customise(facts):
            first = facts["directions"][0]
            first["member_keys"] = list(_T5_MEMBER_KEYS)
            first["provisional_member_keys"] = list(_T5_MEMBER_KEYS)
            first["relevant_keys"] = list(_T5_MEMBER_KEYS) + [_T5_LEGACY_KEY]
            # Plan §3.1.1: an accepted membership change needs CURRENT
            # full-text evidence, so the member the accepted decision removes
            # gets the real future-work/facts sidecar pair.
            self._t5_add_fulltext_evidence(facts, _T5_ACCEPTED_REMOVAL_KEY)
            second = copy.deepcopy(first)
            second["collection_key"] = "DIR00002"
            second["name_ja"] = "第二合成方向"
            second["name_zh"] = "第二合成方向"
            second["user_note"] = "第二方向的合成输入笔记。"
            facts["directions"].append(second)
        facts_path = self.write_facts(customise)
        prepare_stage2_proof(run_cli, facts_path)
        # C is relevant-only in this established lifecycle fixture. Include it
        # through the supported Stage-1 named-paper input before freezing E;
        # its original-member status and facts evidence remain unchanged.
        named_path = self.root / "t5-named-papers.json"
        named_path.write_text(json.dumps({"directions": {
            "DIR00001": [_T5_LEGACY_KEY], "DIR00002": [_T5_LEGACY_KEY]}},
            ensure_ascii=False), encoding="utf-8")
        contact_stage1.build_command(
            self.root, self.prof_dir / "套磁目标.json", named_path)
        return facts_path

    def _t5_add_fulltext_evidence(self, facts, item_key):
        """Give one original member a currently valid ``.facts.json`` sidecar.

        ``BaseEnv.setUp`` already wrote the paper's future-work sidecar, so
        only the sibling facts sidecar (plus the source PDF it fingerprints)
        is missing. Nothing here touches authoritative runner state.
        """
        paper = next(row for row in facts["papers"] if row["item_key"] == item_key)
        analysis = Path(paper["analysis_file"])
        pdf = self.root / f"{item_key}.pdf"
        pdf.write_bytes(b"%PDF-1.4\nsynthetic full-text body\n")
        make_facts_sidecar(analysis, pdf, [self.gap_quotes[item_key]])
        paper["pdf_file"] = str(pdf)
        paper["facts_file"] = str(analysis) + ".facts.json"
        return paper

    def _t5_accept_member_removal(self, facts_path, direction_id="DIR00002"):
        """Accept ONE member removal through the formal resolve entry points.

        Plan §3.1.6/§5.1 T5.1: the old-semantics pack re-run must keep applying
        the current facts round's accepted decision. The decision is therefore
        produced by the real chain — ``stage2-resolve-plan`` with its own round
        directory, a complete ``refined`` result file, ``stage2-resolve-finalize``
        and ``stage2-resolve-accept`` — never by editing state directly.
        """
        # The initial pack is already committed; the accepted resolve belongs
        # to a new consumption round rather than that completed plan.
        self._t6_prepare(facts_path)
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        direction = next(row for row in facts["directions"]
                         if row["collection_key"] == direction_id)
        results_dir = new_resolve_results_dir(self.root, "t5-resolve-run")
        plan = plan_resolve(facts_path, results_dir)
        self.assertEqual(plan["status"], "ok", plan)
        refined = {
            "resolved_direction_id": direction_id,
            "provisional_direction_id": direction_id,
            "name_ja": direction.get("name_ja") or "",
            "name_zh": direction.get("name_zh") or "",
            "resolution_type": "refined",
            "papers_to_add": [],
            "papers_to_remove": [_T5_ACCEPTED_REMOVAL_KEY],
            "paper_justifications": {
                _T5_ACCEPTED_REMOVAL_KEY: "全文事实显示该论文不属于本方向。"},
            "split_target": None,
            "merge_target": None,
            "user_note": direction.get("user_note") or "",
        }
        write_resolve_results(results_dir, plan, {direction_id: refined}, facts_path)
        finalized = finalize_resolve(facts_path, results_dir)
        self.assertEqual(finalized["status"], "ok", finalized)
        proposed = next(row for row in finalized["directions"]
                        if row["provisional_direction_id"] == direction_id)
        self.assertEqual(proposed["resolution_type"], "refined", proposed)
        self.assertEqual(proposed["papers_to_remove"], [_T5_ACCEPTED_REMOVAL_KEY],
                         proposed)
        accepted = parse(run_cli("stage2-resolve-accept", "--facts", facts_path,
                                 "--ckeys", direction_id))
        self.assertEqual(accepted["status"], "ok", accepted)
        resolved_path = Path(accepted["resolved_directions_path"])
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        entry = next(row for row in payload["directions"]
                     if row["provisional_direction_id"] == direction_id)
        self.assertEqual(entry["acceptance"], "accepted", entry)
        return resolved_path

    def _t5_write_narrative(self, results, gap_notes=True):
        notes = []
        if gap_notes:
            notes.append({"gap_id": quote_id(self.gap_quotes["AAAA1111"]),
                          "summary": "扩展到第二种输入模式",
                          "explanation": "研究计划比较另一种合成场景。"})

        def blocks(quote, second_line):
            return [
                {"kind": "para", "text": f"{quote}是合成比较的定位句。", "refs": [],
                 "concrete_object": "合成输入与第二种模式",
                 "input_example": "输入一组固定的合成样本",
                 "output_example": "系统给出两种处理结果"},
                {"kind": "para", "text": second_line, "refs": [],
                 "concrete_object": "该方向的第二段合成对象",
                 "input_example": "输入该方向的第二组样本",
                 "output_example": "系统给出该方向的第二组结果"},
            ]

        narrative = {"schema": 1, "kind": "narrative", "directions": [
            {"direction_id": "DIR00001", "collection_key": "DIR00001",
             "positioning": blocks(_T5_LEGACY_QUOTE,
                                   "第一方向的第二段定位句保持不变。"),
             "gap_notes": copy.deepcopy(notes)},
            {"direction_id": "DIR00002", "collection_key": "DIR00002",
             "positioning": blocks(_T5_SECOND_QUOTE,
                                   "第二方向的第二段定位句保持不变。"),
             "gap_notes": copy.deepcopy(notes)},
        ]}
        (results / "narrative.json").write_text(
            json.dumps(narrative, ensure_ascii=False), encoding="utf-8")

    def _t5_generate_pack(self):
        """Formal plan/finalize run producing a legal current-semantics pack."""
        facts_path = self._t5_write_facts()
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        results = self.root / "t5-results"
        self.write_stage2_results(results, directions=facts["directions"])
        self._t5_write_narrative(results)
        proof_path = self._t6_prepare(facts_path)
        plan = self._t6_plan(facts_path, proof_path)
        self.assertEqual(plan["status"], "ok", plan)
        self._t6_seal(facts_path, results)
        finalized = parse(run_cli("stage2-finalize", "--facts", facts_path,
                                  "--preflight-file", proof_path, "--results", results))
        self.assertEqual(finalized["status"], "ok", finalized)
        return facts_path, results

    def _t5_preflight(self, facts_path, name):
        """Formal preflight receipt saved as the proof this facts run is bound to."""
        payload = parse(run_cli(
            "stage2-preflight", "--program-root", self.root, "--professor", "試験 教授",
            "--target-file", self.prof_dir / "套磁目标.json",
            "--paper-analysis", "relevant", "--gap-scope", "selected_direction",
            "--freshness-scope", "shortlist"))
        self.assertEqual(payload["status"], "ok", payload)
        proof_path = self.root / name
        proof_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        facts["stage2_preflight"] = {"preflight_id": payload["preflight_id"]}
        Path(facts_path).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        self._t6_prepare(facts_path, proof_path)
        return proof_path, payload

    def _t5_pack(self):
        return json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))

    def _t5_document(self):
        raw = (self.prof_dir / contact_state.ANALYSIS_MD).read_text(encoding="utf-8")
        header, body = contact_state.split_frontmatter(raw)
        return {"raw": raw, "header": header, "body": body,
                "sha256": contact_state.sha256_text(body)}

    def _t5_document_member_keys(self):
        """Item keys listed per direction in the managed 论文一览 tables."""
        pack = self._t5_pack()
        order = [direction["direction_id"] for direction in pack["directions"]]
        listed, current, in_table = {}, None, False
        for line in self._analysis_lines():
            if line.startswith("## 方向 "):
                current = order[len(listed)]
                listed[current] = []
                in_table = False
                continue
            if line.strip() == "### 论文一览":
                in_table = True
                continue
            if in_table and current and line.startswith("| [") \
                    and "zotero://select/library/items/" in line:
                key = line.split("zotero://select/library/items/", 1)[1].split(")", 1)[0]
                listed[current].append(key)
        return listed

    def _assert_t5_render_binding(self):
        """Pack, frontmatter and the actual managed file must describe one render."""
        pack = self._t5_pack()
        document = self._t5_document()
        header = document["header"]
        self.assertIsInstance(header, dict, header)
        self.assertEqual(header.get("managed_by"), contact_state.MANAGED_BY, header)
        self.assertEqual(header.get("render_sha256"), document["sha256"], header)
        self.assertEqual(header.get("state_fingerprint"),
                         contact_state.stage2_pack_state_fingerprint(pack), header)
        render = (pack.get("cache") or {}).get("render") or {}
        self.assertEqual((render.get(contact_state.ANALYSIS_MD) or {}).get("sha256"),
                         document["sha256"], render)
        listed = self._t5_document_member_keys()
        for direction in pack["directions"]:
            direction_id = direction["direction_id"]
            self.assertEqual(sorted(set(listed.get(direction_id) or [])),
                             sorted(set(direction.get("supporting_item_keys") or [])),
                             (direction_id, listed.get(direction_id)))

    def _t5_write_rewrite(self, direction_id, before, after, name):
        """Full narrative-rewrite result for one direction's first phrase."""
        pack = self._t5_pack()
        direction = self._pack_direction(pack, direction_id)
        narrative = copy.deepcopy(direction["narrative"])
        block = narrative["positioning"][0]
        self.assertIn(before, block["text"])
        block["text"] = block["text"].replace(before, after, 1)
        rewrite = {"schema": 1, "kind": "narrative-rewrite", "direction_id": direction_id,
                   "collection_key": direction.get("collection_key"),
                   "positioning": narrative["positioning"],
                   "gap_notes": [{"gap_id": gap_id, "summary": note["summary"],
                                  "explanation": note["explanation"]}
                                 for gap_id, note in narrative["gap_notes"].items()]}
        results = self.root / name
        results.mkdir(parents=True, exist_ok=True)
        (results / f"narrative-rewrite-{contact_state.filename_component(direction_id)}.json"
         ).write_text(json.dumps(rewrite, ensure_ascii=False), encoding="utf-8")
        return results

    def _t5_inject_legacy_member(self, facts_path):
        """Synthesize the old-semantics pack (plan §3.1.6/§5.1 T5.1).

        The new runner cannot produce a pack whose membership still carries a
        relevant-only paper, so the fixture assembles that historical state
        before any tested call: membership keeps the extra key, the recorded
        preflight metadata keeps the previous resolution-semantics version, and
        the managed analysis is rendered from that very pack so document and
        pack agree.
        """
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        direction = self._pack_direction(pack, "DIR00001")
        paper = next(row for row in
                     json.loads(Path(facts_path).read_text(encoding="utf-8"))["papers"]
                     if row["item_key"] == _T5_LEGACY_KEY)
        direction["supporting_item_keys"] = sorted(
            set(direction.get("supporting_item_keys") or []) | {_T5_LEGACY_KEY})
        pack.setdefault("papers", {})[_T5_LEGACY_KEY] = {
            "item_key": _T5_LEGACY_KEY, "title": paper.get("title"),
            "year": paper.get("year"), "authorship": paper.get("authorship"),
            "analysis_file": paper.get("analysis_file"),
            "pdf_available": bool(paper.get("has_pdf")),
            "facts_state": "unavailable", "facts_error": "missing_facts_sidecar",
            "paper_facts": None}
        meta = (pack.get("cache") or {}).get("preflight")
        if isinstance(meta, dict):
            meta["resolution_semantics_version"] = \
                contact_state.STAGE2_RESOLUTION_SEMANTICS_VERSION - 1
            meta["accepted_directions_sha256"] = contact_state.sha256_obj(pack["directions"])
        state_fingerprint = contact_state.stage2_pack_state_fingerprint(pack)
        ctx = contact_state.Stage2Context(Path(facts_path))
        body, ownership = contact_state.render_analysis_document(
            ctx, pack, state_fingerprint)
        body_sha = contact_state.sha256_text(body)
        ownership["body_sha256"] = body_sha
        (self.prof_dir / contact_state.ANALYSIS_MD).write_text(
            contact_state.render_frontmatter(state_fingerprint, body_sha) + body,
            encoding="utf-8")
        render_entry = dict((pack.get("cache") or {}).get("render", {}).get(
            contact_state.ANALYSIS_MD) or {})
        render_entry.update({"sha256": body_sha, "ownership": ownership})
        render_entry.setdefault(
            "u1", {"display_version": contact_state.STAGE2_U1_DISPLAY_VERSION,
                   "completed_at": contact_state.now_utc()})
        pack.setdefault("cache", {})["render"] = {
            contact_state.ANALYSIS_MD: render_entry}
        pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
        return meta

    def _t5_restore_legacy_preflight(self, meta):
        """Re-establish the historical preflight binding the correction cycle replaced.

        The ordinary correction entry rewrites cache metadata, so the synthetic
        old pack must restore its recorded preflight block and re-bind the
        terminal record to its own content before the tested calls.
        """
        self.assertIsInstance(meta, dict, meta)
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        pack.setdefault("cache", {})["preflight"] = meta
        pack["validator"]["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
        pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")

    def _t5_legacy_pack_env(self):
        """Isolated env holding the synthetic old-semantics pack and its terminal record."""
        env = self._fresh_stage2_env()
        facts_path, results = env._t5_generate_pack()
        # Plan §3.1.6/§5.1 T5.1: this facts round carries one member change the
        # user accepted through the formal resolve entry, so the ordinary
        # finalize below can be checked for "rebuild the original members and
        # keep applying the accepted decision".
        resolved_path = env._t5_accept_member_removal(facts_path)
        meta = env._t5_inject_legacy_member(facts_path)
        legacy_first = env.write_validation_issues(
            "t5-legacy-round1.json",
            [env._blocking_issue(_T5_LEGACY_QUOTE,
                                 env._physical_line_of(_T5_LEGACY_QUOTE))])
        recorded = env.record_validation(legacy_first)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        rewrite = env._t5_write_rewrite("DIR00001", _T5_LEGACY_QUOTE, _T5_LEGACY_REVISED,
                                        "t5-legacy-rewrite")
        refined = parse(run_cli("stage2-refine-finalize", "--professor-dir", env.prof_dir,
                                "--results", rewrite, "--validation-file", legacy_first))
        self.assertEqual(refined["status"], "ok", refined)
        self.assertEqual(refined["phase"], "awaiting_second_validation", refined)
        legacy_second = env.write_validation_issues(
            "t5-legacy-round2.json",
            [env._blocking_issue(_T5_SECOND_QUOTE,
                                 env._physical_line_of(_T5_SECOND_QUOTE))])
        terminal = env.record_validation(legacy_second)
        self.assertEqual(terminal["status"], "ok", terminal)
        self.assertEqual(terminal["round"], 2, terminal)
        self.assertTrue(terminal["terminal"], terminal)
        env._t5_restore_legacy_preflight(meta)
        validator = env._t5_pack()["validator"]
        return env, {"facts": facts_path, "results": results,
                     "reports": (legacy_first, legacy_second),
                     "resolved_directions": resolved_path,
                     "validator_sha256": validator["validation_sha256"],
                     "render_sha256": validator["render_sha256"]}

    def _t5_missing_member_source_state(self):
        """Legal current-facts pack with ONLY the original member source removed.

        Plan §5.1 T5.1 (test-r5): every other fact and existing authoritative
        artifact stays as generated, the modified facts are re-bound through the
        formal ``stage2-preflight``/``stage2-plan`` pair, and the complete
        freshness/narrative results of the legal run are reused, filling only
        what this round's plan still asks for. That keeps the refusal from
        landing on a stale proof, a missing result or a format error.
        """
        env = self._fresh_stage2_env()
        facts_path, generated_results = env._t5_generate_pack()
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        for direction in facts["directions"]:
            direction.pop("member_keys", None)
            direction.pop("provisional_member_keys", None)
        Path(facts_path).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        proof_path, _receipt = env._t5_preflight(facts_path,
                                                 "t5-missing-members-preflight.json")
        results = env.root / "t5-missing-members-results"
        results.mkdir()
        for existing in sorted(generated_results.glob("*.json")):
            shutil.copyfile(existing, results / existing.name)
        plan = env._t6_plan(facts_path, proof_path)
        self.assertEqual(plan["status"], "ok", plan)
        for job in plan["jobs"]:
            if (results / job["result_file"]).exists():
                continue
            if job["kind"] == "narrative":
                env._t5_write_narrative(results)
            elif job["kind"] == "freshness":
                env.write_stage2_results(results, directions=facts["directions"])
            else:
                self.fail(f"unexpected stage2 job kind in the T5 fixture: {job}")
        env._t6_seal(facts_path, results)
        return env, facts_path, proof_path, results

    def _t5_assert_missing_member_source_rejected(self):
        """Plan §3.1.1: no legal original-member source fails before any write."""
        env, facts_path, proof_path, results = self._t5_missing_member_source_state()
        pack_path = env.prof_dir / "套磁候选输入.json"
        analysis_path = env.prof_dir / contact_state.ANALYSIS_MD
        pack_before = pack_path.read_bytes()
        analysis_before = analysis_path.read_bytes()
        out = parse(run_cli("stage2-finalize", "--facts", facts_path,
                            "--preflight-file", proof_path, "--results", results))
        self.assertNotEqual(out["status"], "ok", out)
        # Only a refusal that is NOT one of the failures plan §5.1 T5.1 names as
        # inconclusive can pass: bad parameters, a stale/mismatched preflight
        # proof, a missing result, or an invalid result file.
        unrelated = {"invalid_params", "preflight_inputs_changed",
                     "result_missing", "invalid_result_json"}
        self.assertNotIn(out.get("reason_code"), unrelated, out)
        detail = " ".join(str(out.get(field) or "")
                          for field in ("message", "detail", "hint")).lower()
        self.assertTrue(
            any(marker in detail for marker in
                ("provisional_member_keys", "member_keys", "member", "成员")),
            f"refusal does not name the missing original member source: {out}")
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(analysis_path.read_bytes(), analysis_before)

    def test_stage2_second_blocking_round_is_terminal(self):
        def later_reference_only(facts):
            # Plan §3.1.1: in this scenario CCCC3333 is only the
            # `{{L:CCCC3333}}` later reference rendered inside DIR00001. The
            # original formal members therefore exclude it, while `papers`
            # keeps its record for the reference. `provisional_member_keys` is
            # the single explicit original-member source.
            first = facts["directions"][0]
            members = [key for key in first["member_keys"] if key != "CCCC3333"]
            first["member_keys"] = members
            first["provisional_member_keys"] = list(members)

        facts = self.write_facts(later_reference_only)
        results = self.root / "results"
        self.write_stage2_results(results)
        narrative_path = results / "narrative.json"
        narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
        block = narrative["directions"][0]["positioning"][0]
        block["text"] = block["text"].replace(
            "起研究合成输入比较；",
            "起研究合成输入比较，并由后续论文 {{L:CCCC3333}} 展示处理路径；",
            1)
        block["refs"].append("later:CCCC3333")
        narrative_path.write_text(json.dumps(narrative, ensure_ascii=False), encoding="utf-8")
        plan = parse(self.run_bound_stage2_plan(facts))
        self.assertEqual(plan["status"], "ok", plan)
        finalized_stage2 = parse(run_bound_stage2_finalize(
            run_cli, facts, "--results", results))
        self.assertEqual(finalized_stage2["status"], "ok", finalized_stage2)

        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        direction = next(row for row in pack["directions"]
                         if row["direction_id"] == "DIR00001")
        self.assertNotIn("CCCC3333", direction["supporting_item_keys"], direction)
        self.assertIn("{{L:CCCC3333}}", direction["narrative"]["positioning"][0]["text"])
        self.assertIn("later:CCCC3333", direction["narrative"]["positioning"][0]["refs"])
        later_title = next(paper["title"] for paper in self.papers
                           if paper["item_key"] == "CCCC3333")
        saved_later_paper = direction.get("narrative_later_papers", {}).get("CCCC3333")
        self.assertIsInstance(saved_later_paper, dict)
        self.assertEqual(saved_later_paper.get("title"), later_title)
        self.assertNotIn("CCCC3333", contact_state.pack_paper_index(pack))
        analysis_lines = (self.prof_dir / "套磁候选分析.md").read_text(
            encoding="utf-8").splitlines()
        title_lines = [line for line in analysis_lines if later_title in line]
        self.assertEqual(len(title_lines), 1, title_lines)
        title_line = title_lines[0]
        self.assertIn("教授从", title_line)
        first = self.write_validation(
            "first-round.json", quote=later_title,
            location=str(analysis_lines.index(title_line) + 1))
        recorded = self.record_validation(first)
        self.assertEqual(recorded["status"], "needs_correction", recorded)

        plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                             "--validation-file", first))
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["DIR00001"])
        results = self.rewrite_direction("DIR00001", "教授从", "教授先从")
        finalized = parse(run_cli("stage2-refine-finalize", "--professor-dir", self.prof_dir,
                                  "--results", results, "--validation-file", first))
        self.assertEqual(finalized["status"], "ok", finalized)
        self.assertIn(later_title, (self.prof_dir / "套磁候选分析.md").read_text(
            encoding="utf-8"))
        self.assert_direction_not_accepted("DIR00001")

        second = self.write_validation("second-round.json", quote="教授先从")
        recorded_again = self.record_validation(second)
        self.assertEqual(recorded_again["status"], "ok", recorded_again)
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        terminal = pack["validator"]["results"]["DIR00001"]
        self.assertEqual(terminal["result"], "fail_after_2_rounds")
        self.assertEqual(terminal["rounds"], 2)
        self.assert_direction_not_accepted("DIR00001")

        third_plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                                   "--validation-file", second))
        self.assertEqual(third_plan["status"], "ok", third_plan)
        self.assertEqual(third_plan["jobs"], [])

        missing_env = self.__class__("test_stage2_second_blocking_round_is_terminal")
        missing_env.setUp()
        try:
            missing_facts = missing_env.write_facts(later_reference_only)
            missing_results = missing_env.root / "missing-title-results"
            missing_env.write_stage2_results(missing_results)
            missing_narrative_path = missing_results / "narrative.json"
            missing_narrative = json.loads(
                missing_narrative_path.read_text(encoding="utf-8"))
            missing_block = missing_narrative["directions"][0]["positioning"][0]
            missing_block["text"] = missing_block["text"].replace(
                "起研究合成输入比较；",
                "起研究合成输入比较，并由后续论文 {{L:CCCC3333}} 展示处理路径；",
                1)
            missing_block["refs"].append("later:CCCC3333")
            missing_narrative_path.write_text(
                json.dumps(missing_narrative, ensure_ascii=False), encoding="utf-8")
            missing_plan = parse(missing_env.run_bound_stage2_plan(missing_facts))
            self.assertEqual(missing_plan["status"], "ok", missing_plan)
            missing_finalized = parse(run_bound_stage2_finalize(
                run_cli, missing_facts, "--results", missing_results))
            self.assertEqual(missing_finalized["status"], "ok", missing_finalized)

            missing_pack_path = missing_env.prof_dir / "套磁候选输入.json"
            missing_pack = json.loads(
                missing_pack_path.read_text(encoding="utf-8"))
            missing_direction = next(
                row for row in missing_pack["directions"]
                if row["direction_id"] == "DIR00001")
            self.assertIn("CCCC3333", missing_direction.get(
                "narrative_later_papers", {}))
            del missing_direction["narrative_later_papers"]
            paper_index = contact_state.pack_paper_index(missing_pack)
            paper_index.pop("CCCC3333", None)
            self.assertNotIn("CCCC3333", paper_index)
            missing_pack_path.write_text(
                json.dumps(missing_pack, ensure_ascii=False), encoding="utf-8")

            gap_quote = "研究计划比较另一种合成场景"
            missing_analysis_path = missing_env.prof_dir / "套磁候选分析.md"
            missing_analysis_lines = missing_analysis_path.read_text(
                encoding="utf-8").splitlines()
            gap_line = next(index + 1 for index, line in enumerate(missing_analysis_lines)
                            if gap_quote in line)
            missing_report = missing_env.write_validation(
                "missing-later-title.json", quote=gap_quote,
                location=str(gap_line))
            recorded_missing = missing_env.record_validation(missing_report)
            self.assertEqual(recorded_missing["status"], "needs_correction",
                             recorded_missing)

            before_refine_pack = json.loads(
                missing_pack_path.read_text(encoding="utf-8"))
            protected_directions = copy.deepcopy(before_refine_pack["directions"])
            before_refine_analysis = missing_analysis_path.read_bytes()
            missing_title = parse(run_cli(
                "stage2-refine-plan", "--professor-dir", missing_env.prof_dir,
                "--validation-file", missing_report))
            self.assertNotIn(missing_title.get("status"),
                             {"ok", "needs_correction"}, missing_title)
            title_error = " ".join(str(missing_title.get(field, ""))
                                   for field in ("reason_code", "message", "detail"))
            self.assertTrue("title" in title_error.casefold() or "标题" in title_error,
                            missing_title)
            self.assertFalse(missing_title.get("jobs"), missing_title)
            after_refine_pack = json.loads(
                missing_pack_path.read_text(encoding="utf-8"))
            self.assertEqual(after_refine_pack["directions"], protected_directions)
            self.assertEqual(missing_analysis_path.read_bytes(), before_refine_analysis)
        finally:
            missing_env.tearDown()

    def test_stage2_report_for_stale_render_is_rejected_without_pack_write(self):
        self.stage2_run()
        pack_path = self.prof_dir / "套磁候选输入.json"
        before = pack_path.read_bytes()
        analysis_path = self.prof_dir / "套磁候选分析.md"
        original_analysis = analysis_path.read_text(encoding="utf-8")

        wrong_target = self.write_validation("wrong-target.json", verdict="pass", quote=None)
        report_data = json.loads(wrong_target.read_text(encoding="utf-8"))
        report_data["files"][0]["file"] = str(self.prof_dir / "not-managed.md")
        wrong_target.write_text(json.dumps(report_data, ensure_ascii=False), encoding="utf-8")
        out = self.record_validation(wrong_target)
        self.assertIn(out["status"], {"error", "needs_refresh"}, out)
        self.assertNotEqual(out.get("reason_code"), "invalid_validation_json", out)
        self.assertTrue(out.get("reason_code") or out.get("message"), out)
        self.assertEqual(pack_path.read_bytes(), before)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), original_analysis)

        report = self.write_validation("stale-render.json", verdict="pass", quote=None)
        analysis_path.write_text(analysis_path.read_text(encoding="utf-8") +
                                "\n合成的人工修改。\n", encoding="utf-8")
        protected_analysis = analysis_path.read_text(encoding="utf-8")

        out = self.record_validation(report)
        self.assertIn(out["status"], {"error", "needs_refresh"}, out)
        self.assertNotEqual(out.get("reason_code"), "invalid_validation_json", out)
        self.assertTrue(out.get("reason_code") or out.get("message"), out)
        self.assertEqual(pack_path.read_bytes(), before)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), protected_analysis)

    def test_stage2_nonrepairable_user_note_does_not_create_a_correction_job(self):
        facts = self.write_facts()
        results = self.root / "results"
        self.write_stage2_results(results)
        note_quote = "我想比较两种合成输入的处理结果"
        facts_data = json.loads(facts.read_text(encoding="utf-8"))
        next(paper for paper in facts_data["papers"]
             if paper["item_key"] == "AAAA1111")["title"] = note_quote
        facts.write_text(json.dumps(facts_data, ensure_ascii=False), encoding="utf-8")
        narrative_path = results / "narrative.json"
        narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
        narrative["directions"][0]["positioning"].append({
            "kind": "para", "text": note_quote, "refs": [],
            "concrete_object": "两种合成输入",
            "input_example": "输入两种固定的合成样本",
            "output_example": "比较两种处理结果",
        })
        multiline_quote = "续行叙事可修订"
        narrative["directions"][0]["positioning"].append({
            "kind": "para", "text": f"条目首行叙述。\n{multiline_quote}", "refs": [],
            "concrete_object": "两种合成输入",
            "input_example": "输入两种固定的合成样本",
            "output_example": "比较两种处理结果",
        })
        narrative_path.write_text(json.dumps(narrative, ensure_ascii=False), encoding="utf-8")
        plan = parse(self.run_bound_stage2_plan(facts))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(finalized["status"], "ok", finalized)
        pack_path = self.prof_dir / "套磁候选输入.json"
        analysis_path = self.prof_dir / "套磁候选分析.md"
        protected_pack = json.loads(pack_path.read_text(encoding="utf-8"))
        protected_directions = copy.deepcopy(protected_pack["directions"])
        protected_analysis = analysis_path.read_text(encoding="utf-8")
        note_line = protected_analysis.splitlines().index(f"> {note_quote}。") + 1
        citation_line = next(index + 1 for index, line in enumerate(protected_analysis.splitlines())
                             if note_quote in line and "zotero://" in line)
        reports = []
        for name, location in (("nonrepairable-note.json", note_line),
                               ("nonrepairable-citation.json", citation_line)):
            report = self.write_validation(name, quote=note_quote, location=str(location))
            out = self.record_validation(report)
            self.assertNotIn(out["status"], {"ok", "needs_correction"}, out)
            self.assertNotEqual(out.get("reason_code"), "invalid_validation_json", out)
            self.assertTrue(out.get("reason_code") or out.get("message"), out)
            reports.append(report)
        pack_after_record = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(pack_after_record["directions"], protected_directions)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), protected_analysis)
        for report in reports:
            self.assert_no_accepted_validation("DIR00001")
            plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                                 "--validation-file", report))
            self.assertNotIn(plan["status"], {"ok", "needs_correction"}, plan)
            self.assertNotEqual(plan.get("reason_code"), "invalid_validation_json", plan)
            self.assertTrue(plan.get("reason_code") or plan.get("message"), plan)
            self.assertEqual(plan.get("jobs", []), [])
        pack_after_plan = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(pack_after_plan["directions"], protected_directions)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), protected_analysis)

        multiline_line = next(
            index + 1 for index, line in enumerate(protected_analysis.splitlines())
            if line.startswith(f"{multiline_quote}；具体对象："))
        report = self.write_validation(
            "repairable-multiline-positioning.json", quote=multiline_quote,
            location=str(multiline_line))
        out = self.record_validation(report)
        self.assertEqual(out["status"], "needs_correction", out)
        plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                             "--validation-file", report))
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["DIR00001"])
        pack_after_multiline = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(pack_after_multiline["directions"], protected_directions)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), protected_analysis)

    def test_stage2_refinement_rejects_changed_input_pack(self):
        self.stage2_run()
        report = self.write_validation("changed-pack.json")
        recorded = self.record_validation(report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)

        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        pack["directions"][0]["user_note"] = "合成状态变更，不得沿用旧报告。"
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        before = pack_path.read_bytes()
        out = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                            "--validation-file", report))
        self.assertIn(out["status"], {"error", "needs_refresh"}, out)
        self.assertNotEqual(out.get("reason_code"), "invalid_validation_json", out)
        self.assertTrue(out.get("reason_code") or out.get("message"), out)
        self.assertEqual(out.get("jobs", []), [])
        self.assertEqual(pack_path.read_bytes(), before)

    def test_stage2_preflight_accepts_legacy_pass_and_skipped_records(self):
        self.stage2_run()
        pack_path = self.prof_dir / "套磁候选输入.json"
        target_path = self.prof_dir / "套磁目标.json"
        for result in ("pass", "skipped"):
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            pack["validator"] = {"results": {"DIR00001": {"result": result}}}
            pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
            preflight = parse(run_cli(
                "stage2-preflight", "--program-root", self.root,
                "--professor", "試験 教授", "--target-file", target_path,
                "--paper-analysis", "relevant", "--gap-scope", "selected_direction",
                "--freshness-scope", "shortlist"))
            self.assertEqual(preflight["status"], "ok", preflight)
            direction = next(row for row in preflight["directions"]
                             if row["direction_id"] == "DIR00001")
            self.assertNotIn("validator_not_accepted", direction["reason_codes"])

    def test_repeated_quote_locations_and_ambiguous_report(self):
        """Plan §5.1 T4: one quote on three lines maps per line; ambiguous is refused."""
        # 1. Normally generated managed body: the same blocking quote occupies
        #    three physical lines (frontmatter offset included) in two directions.
        self._t4_two_direction_body()
        body_start = next(index + 1 for index, line in enumerate(self._analysis_lines())
                          if line.startswith("# 套磁候选分析"))
        repeat_lines = self._physical_line_of(_T4_REPEAT_QUOTE, expected=3)
        legacy_line = self._physical_line_of(_T4_LEGACY_TEXT_QUOTE)
        self.assertGreater(body_start, 1, body_start)
        for line_number in repeat_lines + [legacy_line]:
            self.assertGreater(line_number, body_start, (line_number, body_start))
        owners = [self._section_owner(line_number) for line_number in repeat_lines]
        self.assertEqual(owners, ["DIR00001", "DIR00001", "DIR00002"], owners)
        self.assertEqual(self._section_owner(legacy_line), "DIR00002")

        # 2. One raw report whose three issues carry the actual physical line
        #    number in the three supported notations, plus the legacy short-text
        #    location for a quote that hits exactly one line.
        report = self.write_validation_issues("t4-precise-locations.json", [
            self._blocking_issue(_T4_REPEAT_QUOTE, repeat_lines[0]),
            self._blocking_issue(_T4_REPEAT_QUOTE, str(repeat_lines[1])),
            self._blocking_issue(_T4_REPEAT_QUOTE, f"第{repeat_lines[2]}行"),
            self._blocking_issue(_T4_LEGACY_TEXT_QUOTE, _T4_LEGACY_TEXT_QUOTE),
        ])
        analysis_path = self.prof_dir / "套磁候选分析.md"
        analysis_before = analysis_path.read_bytes()
        recorded = self.record_validation(report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertFalse(recorded["terminal"], recorded)
        self.assertEqual(sorted(recorded["updated"]), ["DIR00001", "DIR00002"], recorded)
        _header, rendered_body = contact_state.split_frontmatter(
            analysis_path.read_text(encoding="utf-8"))
        self.assertEqual(recorded["render_sha256"],
                         contact_state.sha256_text(rendered_body), recorded)
        self.assertEqual(analysis_path.read_bytes(), analysis_before)

        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        validator = pack["validator"]
        expected_by_direction = {"DIR00001": [repeat_lines[0], repeat_lines[1]],
                                 "DIR00002": [repeat_lines[2], legacy_line]}
        for direction_id, lines in expected_by_direction.items():
            pending = validator["pending"][direction_id]
            self.assertEqual([self._issue_line(issue) for issue in pending], lines, pending)
            self.assertEqual(validator["results"][direction_id]["result"],
                             "needs_correction", validator["results"][direction_id])
            self.assertEqual(validator["results"][direction_id]["rounds"], 1,
                             validator["results"][direction_id])

        # 3. The repair scope follows those per-line findings, not the first hit.
        plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                             "--validation-file", report))
        self.assertEqual(plan["status"], "ok", plan)
        jobs = {job["direction_id"]: job for job in plan["jobs"]}
        self.assertEqual(sorted(jobs), ["DIR00001", "DIR00002"], plan)
        self.assertTrue(plan["write_needed"], plan)
        for direction_id, lines in expected_by_direction.items():
            issues = jobs[direction_id]["model_input"]["issues"]
            self.assertEqual([self._issue_line(issue) for issue in issues], lines, issues)
            self.assertEqual(jobs[direction_id]["result_schema"]["direction_id"],
                             direction_id, jobs[direction_id])

        # 4. An independent unrecorded fixture with the same body: the ambiguous
        #    "第N行及多处" report is refused with a locatable error and changes
        #    nothing; a compliant report is a separate, normal input.
        ambiguous_env = self._fresh_stage2_env()
        ambiguous_env._t4_two_direction_body()
        ambiguous_lines = ambiguous_env._physical_line_of(_T4_REPEAT_QUOTE, expected=3)
        ambiguous = ambiguous_env.write_validation_issues("t4-ambiguous-locations.json", [
            ambiguous_env._blocking_issue(_T4_REPEAT_QUOTE,
                                          f"第{ambiguous_lines[0]}行及多处")])
        ambiguous_bytes = ambiguous.read_bytes()
        ambiguous_pack_path = ambiguous_env.prof_dir / "套磁候选输入.json"
        ambiguous_analysis_path = ambiguous_env.prof_dir / "套磁候选分析.md"
        pack_before = ambiguous_pack_path.read_bytes()
        self.assertNotIn("validator", json.loads(pack_before.decode("utf-8")),
                         "fixture must start unrecorded")
        analysis_before = ambiguous_analysis_path.read_bytes()
        refused = ambiguous_env.record_validation(ambiguous)
        self.assertEqual(refused["status"], "error", refused)
        reason = str(refused.get("reason_code") or "")
        self.assertTrue(reason.startswith("validation_"), refused)
        self.assertNotEqual(reason, "invalid_validation_json", refused)
        hint = " ".join(str(refused.get(field) or "")
                        for field in ("reason_code", "message", "detail", "hint", "action",
                                      "remediation", "instruction"))
        markers = ("逐条", "实际行号", "actual line", "line by line", "line-by-line",
                   "per line", "per-line")
        self.assertTrue(any(marker in hint for marker in markers), refused)
        self.assertEqual(ambiguous_pack_path.read_bytes(), pack_before)
        self.assertEqual(ambiguous_analysis_path.read_bytes(), analysis_before)
        self.assertEqual(ambiguous.read_bytes(), ambiguous_bytes)

        compliant = ambiguous_env.write_validation_issues("t4-compliant-locations.json", [
            ambiguous_env._blocking_issue(_T4_REPEAT_QUOTE, ambiguous_lines[0]),
            ambiguous_env._blocking_issue(_T4_LEGACY_TEXT_QUOTE, _T4_LEGACY_TEXT_QUOTE)])
        recorded_again = ambiguous_env.record_validation(compliant)
        self.assertEqual(recorded_again["status"], "needs_correction", recorded_again)
        self.assertEqual(recorded_again["round"], 1, recorded_again)
        self.assertNotEqual(compliant.read_bytes(), ambiguous_bytes)

    def test_business_rerender_and_bounded_correction_lifecycle(self):
        """Plan §5.1 T5: old-pack re-render, bounded two rounds, unchanged-package reuse."""
        # -- 5.1 T5.1: synthetic old-semantics pack with a terminal two-round record
        legacy_env, legacy = self._t5_legacy_pack_env()
        facts_path, results = legacy["facts"], legacy["results"]
        legacy_first, legacy_second = legacy["reports"]
        legacy_reports = {path: path.read_bytes() for path in (legacy_first, legacy_second)}
        legacy_pack = legacy_env._t5_pack()
        self.assertEqual(legacy_pack["validator"]["round"], 2, legacy_pack["validator"])
        self.assertEqual(legacy_pack["validator"]["phase"], "terminal", legacy_pack["validator"])
        self.assertEqual(legacy_pack["validator"]["validation_sha256"],
                         legacy["validator_sha256"], legacy_pack["validator"])
        legacy_direction = legacy_env._pack_direction(legacy_pack, "DIR00001")
        self.assertIn(_T5_LEGACY_KEY, legacy_direction["supporting_item_keys"], legacy_direction)
        self.assertIn(_T5_LEGACY_KEY, legacy_env._t5_document_member_keys()["DIR00001"])
        legacy_document = legacy_env._t5_document()["sha256"]

        # -- preflight must miss the old-semantics pack; the plan still reuses the
        #    unchanged narrative/freshness work and demands no new model job
        #    (plan §3.1.6: only the finalize rebuilds the authoritative members).
        proof_path, preflight = legacy_env._t5_preflight(facts_path, "t5-legacy-preflight.json")
        self.assertNotEqual(preflight["action"], "reuse_all", preflight)
        self.assertIn("resolution_semantics_changed", preflight["reason_codes"], preflight)
        preflight_direction = legacy_env._pack_direction(preflight, "DIR00001")
        self.assertEqual(preflight_direction["action"], "process", preflight_direction)
        self.assertIn("validator_not_accepted", preflight_direction["reason_codes"],
                      preflight_direction)

        plan = legacy_env._t6_plan(facts_path, proof_path)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual({row["direction_id"]: row["action"] for row in plan["directions"]},
                         {"DIR00001": "reuse", "DIR00002": "reuse"}, plan)
        self.assertEqual(plan["jobs"], [], plan)
        self.assertFalse(plan["write_needed"], plan)
        legacy_env._t6_seal(facts_path, results)

        # -- ordinary finalize rebuilds the authoritative members from the current
        #    facts, keeps applying this round's accepted decision, re-renders the
        #    document, and must not certify the old terminal record for the new
        #    business version.
        finalized = parse(run_cli("stage2-finalize", "--facts", facts_path,
                                  "--preflight-file", proof_path, "--results", results,
                                  "--resolved-directions",
                                  legacy["resolved_directions"]))
        self.assertEqual(finalized["status"], "ok", finalized)
        new_pack = legacy_env._t5_pack()
        new_direction = legacy_env._pack_direction(new_pack, "DIR00001")
        self.assertEqual(sorted(new_direction["supporting_item_keys"]),
                         sorted(_T5_MEMBER_KEYS), new_direction)
        self.assertNotIn(_T5_LEGACY_KEY, legacy_env._t5_document_member_keys()["DIR00001"])
        # Plan §3.1.1/§3.1.6: the accepted removal is a formal-member change
        # only — the rebuilt second direction keeps exactly the remaining
        # original member, and `relevant_keys` must not restore the removed
        # paper as a member.
        second_direction = legacy_env._pack_direction(new_pack, "DIR00002")
        self.assertEqual(sorted(second_direction["supporting_item_keys"]),
                         ["AAAA1111"], second_direction)
        self.assertNotIn(_T5_ACCEPTED_REMOVAL_KEY,
                         legacy_env._t5_document_member_keys()["DIR00002"])
        legacy_env._assert_t5_render_binding()
        self.assertNotEqual(legacy_env._t5_document()["sha256"], legacy_document)
        carried = new_pack.get("validator") or {}
        self.assertFalse(carried.get("round") == 2 and carried.get("phase") == "terminal"
                         and carried.get("validation_sha256") == legacy["validator_sha256"],
                         carried)
        if carried:
            self.assertNotEqual(carried.get("render_sha256"), legacy["render_sha256"], carried)
        for path, payload in legacy_reports.items():
            self.assertEqual(path.read_bytes(), payload, path)

        # -- the new business version starts again at round 1 (not exhausted).
        first_line = legacy_env._physical_line_of(_T5_LEGACY_REVISED)
        second_line = legacy_env._physical_line_of(_T5_SECOND_QUOTE)
        # Plan §2 L6: seed one foreign cache child and one unrelated synthetic
        # render record before the new round-1 validation is recorded. That
        # record is created only after this write, so its `pack_sha256` covers
        # both entries and the refine is authorised against the seeded pack;
        # the managed render binding itself is unchanged.
        lifecycle_pack_path = legacy_env.prof_dir / "套磁候选输入.json"
        lifecycle_pack = legacy_env._t5_pack()
        lifecycle_pack["cache"]["u1_render"] = {"future": "kept"}
        lifecycle_pack["cache"]["render"]["其他方向.md"] = {"sha256": "0" * 64}
        lifecycle_pack_path.write_text(
            json.dumps(lifecycle_pack, ensure_ascii=False, indent=1), encoding="utf-8")
        lifecycle_pack = legacy_env._t5_pack()
        self.assertIsInstance(lifecycle_pack["cache"]["preflight"], dict)
        before_sha = lifecycle_pack["cache"]["render"][contact_state.ANALYSIS_MD]["sha256"]
        new_round1 = legacy_env.write_validation_issues("t5-new-round1.json", [
            legacy_env._blocking_issue(_T5_LEGACY_REVISED, first_line),
            legacy_env._blocking_issue(_T5_SECOND_QUOTE, second_line)])
        recorded = legacy_env.record_validation(new_round1)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertFalse(recorded["terminal"], recorded)
        validator = legacy_env._t5_pack()["validator"]
        self.assertEqual(validator["phase"], "needs_correction", validator)
        self.assertEqual(sorted(validator["pending"]), ["DIR00001", "DIR00002"], validator)
        self.assertEqual([legacy_env._issue_line(issue)
                          for issue in validator["pending"]["DIR00001"]], [first_line],
                         validator["pending"]["DIR00001"])
        self.assertEqual([legacy_env._issue_line(issue)
                          for issue in validator["pending"]["DIR00002"]], [second_line],
                         validator["pending"]["DIR00002"])

        # -- facts without any original-member source are refused before any write.
        self._t5_assert_missing_member_source_rejected()

        # -- 5.1 T5.2: bounded correction lifecycle on the new version.
        plan = parse(run_cli("stage2-refine-plan", "--professor-dir", legacy_env.prof_dir,
                             "--validation-file", new_round1))
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual([job["direction_id"] for job in plan["jobs"]],
                         ["DIR00001", "DIR00002"], plan)
        scoped = parse(run_cli("stage2-refine-plan", "--professor-dir", legacy_env.prof_dir,
                               "--validation-file", new_round1, "--direction-id", "DIR00002"))
        self.assertEqual(scoped["status"], "ok", scoped)
        self.assertEqual([job["direction_id"] for job in scoped["jobs"]], ["DIR00002"], scoped)

        rewrite = legacy_env._t5_write_rewrite("DIR00002", _T5_SECOND_QUOTE, _T5_SECOND_REVISED,
                                               "t5-rewrite-second")
        refined = parse(run_cli("stage2-refine-finalize", "--professor-dir", legacy_env.prof_dir,
                                "--results", rewrite, "--validation-file", new_round1,
                                "--direction-id", "DIR00002"))
        self.assertEqual(refined["status"], "ok", refined)
        self.assertEqual(refined["rewritten"], ["DIR00002"], refined)
        self.assertEqual(refined["phase"], "needs_correction", refined)
        self.assertTrue(refined["round_retained"], refined)
        self.assertFalse(refined["validator_reset"], refined)
        validator = legacy_env._t5_pack()["validator"]
        self.assertEqual(validator["round"], 1, validator)
        self.assertEqual(validator["phase"], "needs_correction", validator)
        self.assertEqual(validator["correction_applied_direction_ids"], ["DIR00002"], validator)
        self.assertEqual(sorted(validator["pending"]), ["DIR00001", "DIR00002"], validator)
        body = legacy_env._t5_document()["body"]
        self.assertIn(_T5_SECOND_REVISED, body)
        self.assertNotIn(_T5_SECOND_QUOTE, body)
        self.assertIn(_T5_LEGACY_REVISED, body)
        legacy_env._assert_t5_render_binding()
        # Plan §2 L6: the refine updates only this render binding, keeps every
        # other still-valid cache child and conservatively drops the preflight
        # proof; compare against the seeded value so the body change is proven.
        cache = legacy_env._t5_pack()["cache"]
        self.assertNotIn("preflight", cache)
        self.assertEqual(cache["render"][contact_state.ANALYSIS_MD]["sha256"],
                         legacy_env._t5_document()["sha256"], cache["render"])
        self.assertNotEqual(cache["render"][contact_state.ANALYSIS_MD]["sha256"], before_sha,
                            "the accepted rewrite must really change the body")
        self.assertEqual(cache["u1_render"], {"future": "kept"})
        self.assertEqual(cache["render"]["其他方向.md"], {"sha256": "0" * 64})
        self.assertEqual(sorted(cache["render"]),
                         sorted([contact_state.ANALYSIS_MD, "其他方向.md"]), cache["render"])

        # -- the second round cannot be recorded while a correction is open.
        premature = legacy_env.write_validation_issues(
            "t5-premature-round2.json",
            [legacy_env._blocking_issue(_T5_SECOND_REVISED,
                                        legacy_env._physical_line_of(_T5_SECOND_REVISED))])
        pack_path = legacy_env.prof_dir / "套磁候选输入.json"
        protected = pack_path.read_bytes()
        refused = legacy_env.record_validation(premature)
        self.assertEqual(refused["status"], "error", refused)
        self.assertEqual(refused["reason_code"], "validation_correction_required", refused)
        self.assertEqual(pack_path.read_bytes(), protected)
        remaining = parse(run_cli("stage2-refine-plan", "--professor-dir", legacy_env.prof_dir,
                                  "--validation-file", new_round1))
        self.assertEqual(remaining["status"], "ok", remaining)
        self.assertEqual([job["direction_id"] for job in remaining["jobs"]], ["DIR00001"],
                         remaining)

        # -- completing the last direction reaches awaiting_second_validation.
        rewrite = legacy_env._t5_write_rewrite("DIR00001", _T5_LEGACY_REVISED, _T5_LEGACY_FINAL,
                                               "t5-rewrite-first")
        refined = parse(run_cli("stage2-refine-finalize", "--professor-dir", legacy_env.prof_dir,
                                "--results", rewrite, "--validation-file", new_round1,
                                "--direction-id", "DIR00001"))
        self.assertEqual(refined["status"], "ok", refined)
        self.assertEqual(refined["rewritten"], ["DIR00001"], refined)
        self.assertEqual(refined["phase"], "awaiting_second_validation", refined)
        self.assertTrue(refined["round_retained"], refined)
        validator = legacy_env._t5_pack()["validator"]
        self.assertEqual(validator["round"], 1, validator)
        self.assertEqual(validator["phase"], "awaiting_second_validation", validator)

        round2 = legacy_env.write_validation_issues(
            "t5-new-round2.json",
            [legacy_env._blocking_issue(_T5_LEGACY_FINAL,
                                        legacy_env._physical_line_of(_T5_LEGACY_FINAL))])
        terminal = legacy_env.record_validation(round2)
        self.assertEqual(terminal["status"], "ok", terminal)
        self.assertEqual(terminal["round"], 2, terminal)
        self.assertTrue(terminal["terminal"], terminal)
        validator = legacy_env._t5_pack()["validator"]
        self.assertEqual(validator["phase"], "terminal", validator)
        self.assertEqual(sorted(validator["correction_applied_direction_ids"]),
                         ["DIR00001", "DIR00002"], validator)
        self.assertEqual(validator["results"]["DIR00001"]["result"], "fail_after_2_rounds",
                         validator["results"]["DIR00001"])
        self.assertEqual(validator["results"]["DIR00001"]["rounds"], 2,
                         validator["results"]["DIR00001"])
        self.assertEqual(validator["results"]["DIR00002"]["result"], "pass",
                         validator["results"]["DIR00002"])

        # -- the two-round bound stops a third round and further jobs.
        protected = pack_path.read_bytes()
        third = legacy_env.record_validation(round2)
        self.assertEqual(third["status"], "error", third)
        self.assertEqual(third["reason_code"], "validation_rounds_exhausted", third)
        self.assertEqual(pack_path.read_bytes(), protected)
        stopped = parse(run_cli("stage2-refine-plan", "--professor-dir", legacy_env.prof_dir,
                                "--validation-file", round2))
        self.assertEqual(stopped["status"], "ok", stopped)
        self.assertEqual(stopped["jobs"], [], stopped)
        for path, payload in legacy_reports.items():
            self.assertEqual(path.read_bytes(), payload, path)

        # -- 5.1 T5.3a: a legal unchanged pack reuses everything and is not written.
        stable_env = self._fresh_stage2_env()
        stable_facts, _stable_results = stable_env._t5_generate_pack()
        stable_env._t5_preflight(stable_facts, "t5-stable-preflight.json")
        recorded = stable_env.record_validation(
            stable_env.write_validation_issues("t5-stable-pass.json", []))
        self.assertEqual(recorded["status"], "ok", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        stable_pack_path = stable_env.prof_dir / "套磁候选输入.json"
        stable_before = stable_pack_path.read_bytes()
        _proof, stable = stable_env._t5_preflight(stable_facts, "t5-stable-preflight-2.json")
        self.assertEqual(stable["action"], "reuse_all", stable)
        self.assertEqual(stable_pack_path.read_bytes(), stable_before)
        self.assertEqual(stable_env._t5_pack()["generated_at"],
                         json.loads(stable_before.decode("utf-8"))["generated_at"])
        self.assertEqual(stable_env._t5_pack()["validator"],
                         json.loads(stable_before.decode("utf-8"))["validator"])

        # -- 5.1 T5.3b: an ordinary finalize on an unfinished correction state keeps
        #    round/phase/pending and re-binds them to the (equivalent) new pack.
        meta_env = self._fresh_stage2_env()
        meta_facts, meta_results = meta_env._t5_generate_pack()
        meta_proof, _receipt = meta_env._t5_preflight(meta_facts, "t5-unfinished-preflight.json")
        unfinished = meta_env.write_validation_issues(
            "t5-unfinished-round1.json",
            [meta_env._blocking_issue(_T5_LEGACY_QUOTE,
                                      meta_env._physical_line_of(_T5_LEGACY_QUOTE))])
        recorded = meta_env.record_validation(unfinished)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        before = meta_env._t5_pack()["validator"]
        self.assertEqual(before["round"], 1, before)
        self.assertEqual(before["phase"], "needs_correction", before)
        self.assertEqual(sorted(before["pending"]), ["DIR00001"], before)
        meta_plan = meta_env._t6_plan(meta_facts, meta_proof)
        self.assertEqual(meta_plan["status"], "ok", meta_plan)
        self.assertEqual(meta_plan["jobs"], [], meta_plan)
        meta_env._t6_seal(meta_facts, meta_results)
        out = parse(run_cli("stage2-finalize", "--facts", meta_facts,
                            "--preflight-file", meta_proof, "--results", meta_results))
        self.assertEqual(out["status"], "ok", out)
        self.assertIsInstance(out.get("directions"), list, out)
        after_pack = meta_env._t5_pack()
        after = after_pack.get("validator") or {}
        self.assertEqual(after.get("round"), 1, after)
        self.assertEqual(after.get("phase"), "needs_correction", after)
        self.assertEqual(after.get("validation_sha256"), before["validation_sha256"], after)
        self.assertEqual(sorted(after.get("pending") or {}), ["DIR00001"], after)
        self.assertEqual(after.get("pending", {}).get("DIR00001"),
                         before["pending"]["DIR00001"], after)
        self.assertEqual(after.get("correction_applied_direction_ids"), [], after)
        self.assertEqual(after.get("pack_sha256"),
                         contact_state.stage2_pack_content_fingerprint(after_pack), after)
        self.assertEqual(after.get("render_sha256"), meta_env._t5_document()["sha256"], after)
        meta_env._assert_t5_render_binding()
        meta_pack_path = meta_env.prof_dir / "套磁候选输入.json"
        protected = meta_pack_path.read_bytes()
        premature = meta_env.write_validation_issues(
            "t5-unfinished-round2.json",
            [meta_env._blocking_issue(_T5_LEGACY_QUOTE,
                                      meta_env._physical_line_of(_T5_LEGACY_QUOTE))])
        refused = meta_env.record_validation(premature)
        self.assertEqual(refused["status"], "error", refused)
        self.assertEqual(refused["reason_code"], "validation_correction_required", refused)
        self.assertEqual(meta_pack_path.read_bytes(), protected)
        pending_jobs = parse(run_cli("stage2-refine-plan", "--professor-dir", meta_env.prof_dir,
                                     "--validation-file", unfinished))
        self.assertEqual([job["direction_id"] for job in pending_jobs["jobs"]], ["DIR00001"],
                         pending_jobs)

        # -- 5.1 T5.3c: an explicitly stale binding is not restored by metadata
        #    rewriting and the next evidence consumer still refuses it.
        stale_env = self._fresh_stage2_env()
        stale_facts, stale_results = stale_env._t5_generate_pack()
        stale_proof, _receipt = stale_env._t5_preflight(stale_facts, "t5-stale-preflight.json")
        stale_report = stale_env.write_validation_issues(
            "t5-stale-round1.json",
            [stale_env._blocking_issue(_T5_LEGACY_QUOTE,
                                       stale_env._physical_line_of(_T5_LEGACY_QUOTE))])
        recorded = stale_env.record_validation(stale_report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        stale_plan = stale_env._t6_plan(stale_facts, stale_proof)
        self.assertEqual(stale_plan["status"], "ok", stale_plan)
        self.assertEqual(stale_plan["jobs"], [], stale_plan)
        stale_env._t6_seal(stale_facts, stale_results)
        stale_pack_path = stale_env.prof_dir / "套磁候选输入.json"
        stale_pack_before = stale_pack_path.read_bytes()
        analysis_path = stale_env.prof_dir / contact_state.ANALYSIS_MD
        analysis_path.write_text(analysis_path.read_text(encoding="utf-8") +
                                 "\n合成的人工修改。\n", encoding="utf-8")
        analysis_before = analysis_path.read_bytes()
        out = parse(run_cli("stage2-finalize", "--facts", stale_facts,
                            "--preflight-file", stale_proof, "--results", stale_results))
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out.get("reason_code"), "validation_render_stale", out)
        self.assertEqual(stale_pack_path.read_bytes(), stale_pack_before)
        self.assertEqual(analysis_path.read_bytes(), analysis_before)
        protected = stale_pack_path.read_bytes()
        refused = parse(run_cli("stage2-refine-plan", "--professor-dir", stale_env.prof_dir,
                                "--validation-file", stale_report))
        self.assertNotEqual(refused["status"], "ok", refused)
        reason = str(refused.get("reason_code") or "")
        self.assertTrue(reason.startswith("validation_"), refused)
        self.assertNotIn(reason, {"invalid_params", "invalid_validation_json"}, refused)
        self.assertEqual(refused.get("jobs", []), [])
        self.assertEqual(stale_pack_path.read_bytes(), protected)


if __name__ == "__main__":
    import unittest
    unittest.main()
