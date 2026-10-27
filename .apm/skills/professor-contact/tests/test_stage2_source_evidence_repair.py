"""Stage 2 source evidence repair (test plan TP2).

Prepared selectors for Gate2.  The approved execution plan EP2 fixes the
entry, the input schema and the observable results below; it permits renaming
only when this module and the TP2 recipe change in the same commit, and never
permits dropping one of these semantics.

- ``stage2-repair-evidence --professor-dir DIR --repair-file FILE`` reads
  ``{"schema": 1, "repairs": [...]}``.  Each row names ``direction_id``,
  ``gap_id``, ``field`` from the exact whitelist
  ``model_evidence | completed_part | remaining_gap``, ``expected_old_text``,
  ``replacement``, ``expected_validation_sha256`` and
  ``expected_cache_sha256``.
- ``expected_validation_sha256`` is the recorded
  ``validator.validation_sha256`` of the accepted input pack.
  ``expected_cache_sha256`` is ``sha256_obj`` of the parsed freshness cache
  document ``论文分析/_freshness_cache.json`` (the whole ``{"schema",
  "managed_by", "entries"}`` document, not one entry).
- Authorization comes only from the registered validator's ``fixed_blocking``
  rows: each requested cache field needs its own source-owned row for that
  direction and gap, mapped as displayed ``evidence`` or
  ``blacklist_evidence`` -> cache ``model_evidence``, displayed
  ``completed_part`` -> cache ``completed_part`` and displayed
  ``remaining_gap`` -> cache ``remaining_gap``.
- A changed write returns ``status="needs_refresh"`` plus the affected
  direction/gap rows and never claims PASS.  It writes only the freshness
  cache: the managed Markdown, the accepted input pack and the recorded
  validator keep their bytes.
- The repaired text reaches the report only through ordinary
  ``stage2-preflight -> stage2-plan -> stage2-finalize``.  Finalize projects the
  current cache text into the affected pack rows (shortlist, excluded gaps and
  the completed-gap blacklist, including a reused direction) and drops the old
  validator, so a repaired string still needs a fresh validation round.
- Rejections happen before any write: another field's finding, a quote or
  generator-owned finding, a stale expectation or one bad row in a batch leave
  every file byte-identical.  A no-op replacement changes nothing and cannot
  reset recorded rounds.

The product command and the documented projections do not exist at the
prepared baseline ``2b6a824``: the runtime cases below therefore fail on
missing product behaviour, not on a test defect, and the static cases fail on
absent documentation.  No target here is executed or declared passing by this
preparation commit.
"""
import json
import re
import unittest
from pathlib import Path

from stage2_upstream_fixture import run_bound_stage2_finalize
from test_contact_state import contact_state, parse, run_cli

#: The U1 producer module is reached through its module object on purpose.
#: Importing ``FixedEvidenceBase`` by name would put another ``TestCase`` with
#: six ``test_u1_*`` methods into this module's namespace, and ``unittest``
#: collects imported test cases as well, so this plan's shard would silently
#: re-run the U1 targets.
fixed_evidence = __import__("test_stage2_fixed_evidence")

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_MD = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"
PROJECTIONS = (
    REPO_ROOT / "packages" / "professor-contact-codex" / ".apm" / "agents"
    / "professor-contact-analyzer.agent.md",
    REPO_ROOT / "packages" / "professor-contact-opencode" / ".apm" / "agents"
    / "professor-contact-analyzer.agent.md",
)
WHITELIST = ("model_evidence", "completed_part", "remaining_gap")
#: An existing U1 producer case name; only its fixture lifecycle is reused.
PRODUCER_CASE = "test_u1_e_old_pack_updates_through_process_to_finalize"
#: Registered finding -> (quoted text, rendered line prefix).  The quote is the
#: exact substring the style validator reports; the prefix selects the rendered
#: line that carries it.
FINDINGS = {
    "evidence": ("日期 2024-05-01", "- 后续论文依据："),
    "completed_part": ("已完成一部分", "- 已做部分："),
    "remaining_gap": ("仍缺", "- 剩余缺口："),
    "blacklist_evidence": ("已接住该点", "- We plan"),
    "quote": ("Future work will extend", "- 作者原话："),
    "label": ("后续论文依据", "- 后续论文依据："),
}


def _body(path: Path) -> str:
    """Document body without the YAML frontmatter the projections start with."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        lines = lines[lines.index("---", 1) + 1:]
    return "\n".join(lines)


def _section(path: Path, anchor: str, radius: int = 14) -> str:
    """Documentation around ``anchor``, bounded twice over.

    The window never leaves the heading that contains the first mention and
    never grows beyond ``radius`` lines, so a long enclosing section cannot
    supply a requirement the repair paragraph itself omits.  A mention that
    sits inside an existing section is read as that section; a mention with no
    heading above it falls back to the plain window.
    """
    lines = _body(path).splitlines()
    hits = [index for index, line in enumerate(lines) if anchor in line]
    if not hits:
        raise AssertionError(f"{path}: no {anchor!r} section")
    hit = hits[0]
    start = hit
    while start > 0 and not lines[start].lstrip().startswith("#"):
        start -= 1
    if lines[start].lstrip().startswith("#"):
        level = len(lines[start]) - len(lines[start].lstrip("#"))
        for index in range(start + 1, len(lines)):
            stripped = lines[index].lstrip()
            if stripped.startswith("#"):
                heading = len(stripped) - len(stripped.lstrip("#"))
                if heading <= level:
                    start, end = start, index
                    break
        else:
            end = len(lines)
    else:
        start, end = 0, len(lines)
    return "\n".join(lines[max(start, hit - radius):min(end, hit + radius)])


def _scalar_tokens(payload) -> set:
    """Every scalar string in a parsed command payload.

    Machine identifiers (gap id, field name, owner) are asserted through this
    structural walk, never by matching the serialized JSON text.
    """
    tokens = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            tokens.add(str(key))
            tokens.update(_scalar_tokens(value))
    elif isinstance(payload, list):
        for value in payload:
            tokens.update(_scalar_tokens(value))
    elif payload is not None:
        tokens.add(str(payload))
    return tokens


class SourceEvidenceRepairFixture(unittest.TestCase):
    """Shared lifecycle helpers for the repair command; holds no test itself.

    The U1 producer fixture is reused through composition rather than
    inheritance: subclassing ``FixedEvidenceBase`` would also import its six
    ``test_u1_*`` cases into this module, so the TP2 module would silently
    re-run another plan's targets.
    """

    def setUp(self):
        # ``FixedEvidenceBase`` is a TestCase and rejects an unknown method name,
        # so the producer fixture is bound to one of its own case names.  Nothing
        # of that case runs: only its setUp/tearDown and helpers are used.
        self.env = fixed_evidence.FixedEvidenceBase(PRODUCER_CASE)
        self.env.setUp()
        self.addCleanup(self.env.tearDown)

    def __getattr__(self, name):
        # Every fixture helper (gap_override, generate_pack, record, ...) is
        # reached on the inner producer fixture; only TP2 helpers live here.
        if name == "env":
            raise AttributeError(name)
        return getattr(self.env, name)

    @staticmethod
    def _add_narrative_block(narrative):
        """Append a purely narrative paragraph the U1 fixture may refine."""
        narrative["directions"][0]["positioning"].append({
            "kind": "para", "text": "纯叙事待改文字。", "refs": [],
            "concrete_object": "合成叙事对象",
            "input_example": "输入一份叙事样本",
            "output_example": "得到一段叙事结论"})

    def fresh_repair_env(self):
        """An independent fixture instance of this same repair test class.

        The child never runs its own test method, so its registered cleanups
        (the producer fixture's temporary directory) would otherwise be
        dropped; ``doCleanups`` runs them on this test's teardown.
        """
        env = self.__class__(self._testMethodName)
        env.setUp()
        self.addCleanup(env.doCleanups)
        return env

    # -- observation ---------------------------------------------------------

    def gap_id(self, key):
        return contact_state.quote_id(self.gap_quotes[key])

    def cache_path(self):
        return self.prof_dir / contact_state.FRESHNESS_CACHE

    def cache_document(self):
        return json.loads(self.cache_path().read_text(encoding="utf-8"))

    def cache_entry(self, gap_id):
        return self.cache_document()["entries"][gap_id]

    def cache_digest(self):
        return contact_state.sha256_obj(self.cache_document())

    def validation_digest(self):
        validator = self.pack().get("validator")
        return validator.get("validation_sha256") if isinstance(validator, dict) else None

    def analysis_bytes(self):
        return (self.prof_dir / contact_state.ANALYSIS_MD).read_bytes()

    def protected_snapshot(self):
        """Everything a repair row may not touch: Markdown, pack, validator."""
        return {
            "analysis": self.analysis_bytes(),
            "pack": (self.prof_dir / contact_state.INPUT_PACK).read_bytes(),
            "validator": json.loads(json.dumps(self.pack().get("validator"))),
        }

    def all_files_snapshot(self):
        snapshot = self.protected_snapshot()
        snapshot["cache"] = self.cache_path().read_bytes()
        return snapshot

    # -- registered findings -------------------------------------------------

    def line_with(self, needle, prefix, expected=1):
        hits = [index + 1 for index, line in enumerate(self.body_lines())
                if line.startswith(prefix) and needle in line]
        self.assertEqual(len(hits), expected, (needle, prefix, hits))
        return hits if expected > 1 else hits[0]

    def record_findings(self, *fields, name="repair-round1.json"):
        """Register one blocking finding per named rendered field."""
        issues = [self.blocking_issue(FINDINGS[field][0],
                                      self.line_with(*FINDINGS[field]))
                  for field in fields]
        return self.record_issues(issues, name)

    def record_issues(self, issues, name="repair-round1.json"):
        report = self.write_report(name, issues)
        payload = self.record(report)
        self.assertIn(payload.get("status"), ("ok", "needs_correction"), payload)
        return payload

    def record_one_of_two(self, field, name="repair-round1.json"):
        """Quote only the first of two identical rendered lines.

        Two directions render the same accepted evidence, so the report must
        quote one concrete line: a finding on one direction's line must not
        register a failure against the other direction.
        """
        needle, prefix = FINDINGS[field]
        first, second = self.line_with(needle, prefix, expected=2)
        self.assertNotEqual(first, second)
        return self.record_issues([self.blocking_issue(needle, first)], name)

    # -- repair input --------------------------------------------------------

    def repair_row(self, field, old_text, new_text, *, direction_id="DIR00001",
                   gap_id=None, expected_validation=None, expected_cache=None):
        return {
            "direction_id": direction_id,
            "gap_id": gap_id or self.gap_id("AAAA1111"),
            "field": field,
            "expected_old_text": old_text,
            "replacement": new_text,
            "expected_validation_sha256": (
                self.validation_digest() if expected_validation is None
                else expected_validation),
            "expected_cache_sha256": (
                self.cache_digest() if expected_cache is None else expected_cache),
        }

    def repair_result(self, rows, *, name="repair.json", schema=1):
        path = self.root / name
        path.write_text(json.dumps({"schema": schema, "repairs": rows},
                                   ensure_ascii=False), encoding="utf-8")
        result = run_cli("stage2-repair-evidence", "--professor-dir", self.prof_dir,
                         "--repair-file", path)
        try:
            payload = json.loads(result.stdout)
        except ValueError:
            payload = None
        return result, payload

    def _command_payload(self, result):
        """JSON payload of one repair call, with the product-missing case named."""
        if not result.stdout.strip():
            self.fail(
                "stage2-repair-evidence produced no JSON payload; the product "
                "command is absent or refused at the argparse layer "
                f"(exit {result.returncode}): {result.stderr.strip()[:400]}")
        try:
            payload = json.loads(result.stdout)
        except ValueError:
            self.fail(f"stage2-repair-evidence stdout is not JSON: {result.stdout[:400]}")
        self.assertIsInstance(payload, dict, result.stdout)
        return payload

    def repair(self, rows, **kwargs):
        """Accepted repair call: exit 0 with a JSON payload."""
        result, _ = self.repair_result(rows, **kwargs)
        payload = self._command_payload(result)
        self.assertEqual(result.returncode, 0, payload)
        return payload

    def rejected(self, rows, **kwargs):
        """Rejected repair call: non-zero exit with an actionable reason.

        EP2 fixes the rejection behaviour, not the exact reason-code spelling,
        so this asserts the shape every rejection must have (non-zero exit plus
        the product's ``status``/``reason_code`` error payload) instead of
        inventing a code the product was never asked to emit.
        """
        result, _ = self.repair_result(rows, **kwargs)
        payload = self._command_payload(result)
        self.assertNotEqual(result.returncode, 0, payload)
        self.assertEqual(payload.get("status"), "error", payload)
        self.assertTrue(payload.get("reason_code"), payload)
        return payload

    # -- ordinary acceptance -------------------------------------------------

    def refresh(self, facts_path):
        """Ordinary preflight -> plan for the current on-disk sources."""
        payload = self.preflight()
        proof_path = Path(facts_path).with_name(Path(facts_path).stem + "-preflight.json")
        proof_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        self.bind_facts_to_preflight(facts_path, payload)
        plan = parse(run_cli("stage2-plan", "--facts", facts_path,
                             "--preflight-file", proof_path))
        self.assertEqual(plan["status"], "ok", plan)
        return proof_path, payload, plan

    def finalize_bound(self, facts_path, results, *extra):
        return run_bound_stage2_finalize(run_cli, facts_path, "--results", results,
                                         *extra)

    def two_direction_facts(self, facts):
        second = json.loads(json.dumps(facts["directions"][0]))
        second["collection_key"] = "DIR00002"
        second["user_note"] = "第二个合成方向，用来验证复用分支。"
        facts["directions"].append(second)

    def generate_two_directions(self):
        facts_path = self.write_facts(self.two_direction_facts)
        results = self.root / "results"
        self.write_stage2_results(results, self.gap_override(),
                                  directions=[{"collection_key": "DIR00001"},
                                              {"collection_key": "DIR00002"}])
        plan = parse(self.run_bound_stage2_plan(facts_path))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(self.finalize_bound(facts_path, results))
        self.assertEqual(finalized["status"], "ok", finalized)
        return facts_path, results

    def direction_entry(self, direction_id="DIR00001"):
        return next(direction for direction in self.pack()["directions"]
                    if direction["direction_id"] == direction_id)

    def shortlist_row(self, gap_id, direction_id="DIR00001"):
        return next(row for row in self.direction_entry(direction_id)["gap_shortlist"]
                    if row["gap_id"] == gap_id)

    def blacklist_row(self, gap_id, direction_id="DIR00001"):
        return next(row for row in self.direction_entry(direction_id)["completed_gap_blacklist"]
                    if row["gap_id"] == gap_id)


class SourceEvidenceRepairTests(SourceEvidenceRepairFixture):
    """TP2 R-A..R-C: the public command plus ordinary Stage 2 acceptance."""

    # -- R-A: successful repair and projection -------------------------------

    def test_r_a_partial_gap_three_field_wording_reaches_the_projection(self):
        """One partial gap, all three eligible fields, one ordinary refresh."""
        facts_path, results, _proof = self.generate_pack(self.gap_override())
        recorded = self.record_findings("evidence", "completed_part", "remaining_gap",
                                        "blacklist_evidence")
        self.assertTrue(recorded["needs_owner_fix"], recorded)
        gap = self.gap_id("AAAA1111")
        before = self.cache_entry(gap)
        self.assertEqual(before["status"], "partial", before)
        old = {field: before[field] for field in WHITELIST}
        new = {
            "model_evidence": old["model_evidence"].replace("后续由", "后续工作由"),
            "completed_part": old["completed_part"].replace(
                "已完成一部分", "已完成其中一部分"),
            "remaining_gap": old["remaining_gap"].replace("仍缺", "仍缺少"),
        }
        for field in WHITELIST:
            self.assertNotEqual(old[field], new[field], (field, old[field]))
        protected = self.protected_snapshot()

        payload = self.repair([
            self.repair_row("model_evidence", old["model_evidence"],
                            new["model_evidence"]),
            self.repair_row("completed_part", old["completed_part"],
                            new["completed_part"]),
            self.repair_row("remaining_gap", old["remaining_gap"],
                            new["remaining_gap"]),
        ])

        # A changed write is a refresh request, never a passing result.
        self.assertEqual(payload["status"], "needs_refresh", payload)
        affected = payload.get("affected")
        self.assertIsInstance(affected, list, payload)
        # EP2 fixes the affected direction/gap rows; it does not fix a field
        # column, so the field name is not required here.
        self.assertIn(gap, _scalar_tokens(affected), payload)
        self.assertIn("DIR00001", _scalar_tokens(affected), payload)

        after = self.cache_entry(gap)
        for field in WHITELIST:
            self.assertEqual(after[field], new[field], (field, after[field]))
        for field in ("status", "confidence", "candidate_paper_ids", "gap_fingerprint",
                      "candidate_fingerprint", "evaluated_at", "downgraded"):
            self.assertEqual(after[field], before[field], (field, after[field]))
        # The repair command owns the cache only.
        current = self.protected_snapshot()
        self.assertEqual(current["analysis"], protected["analysis"])
        self.assertEqual(current["pack"], protected["pack"])
        self.assertEqual(current["validator"], protected["validator"])

        proof_path, preflight, plan = self.refresh(facts_path)
        self.assertEqual(preflight["action"], "process", preflight)
        self.assertIn("freshness_cache_changed", preflight["reason_codes"], preflight)
        self.assertEqual([row["action"] for row in plan["directions"]], ["reuse"], plan)

        finalized = parse(self.finalize_bound(facts_path, results))
        self.assertEqual(finalized["status"], "ok", finalized)

        # EP2 section B: the affected gap's accepted rows are re-projected from
        # the still-valid cache record before rendering, including on the reuse
        # path.  This is the observable the repaired wording exists for.
        row = self.shortlist_row(gap)
        self.assertEqual(row["evidence"], new["model_evidence"], row)
        self.assertEqual(row["completed_part"], new["completed_part"], row)
        self.assertEqual(row["remaining_gap"], new["remaining_gap"], row)
        for field in ("status", "confidence", "evaluated_at", "candidate_paper_ids"):
            self.assertEqual(row[field], before[field], (field, row[field]))

        body = self.document()["body"]
        self.assertIn("后续工作由", body)
        self.assertIn("已完成其中一部分", body)
        self.assertIn("仍缺少", body)
        self.assertNotIn("后续由 ", body)
        self.assertNotIn("已完成一部分", body)
        self.assertNotIn("仍缺 ", body)
        # A repaired string is not evidence of a passing review: the old
        # validator was bound to the previous text and is not carried over.
        self.assertNotIn("validator", self.pack())

    def test_r_a_blacklist_evidence_projects_the_repaired_model_evidence(self):
        """A done_by_self row maps displayed ``blacklist_evidence`` to the cache."""
        facts_path, results, _proof = self.generate_pack(self.gap_override())
        recorded = self.record_findings("blacklist_evidence")
        self.assertTrue(recorded["needs_owner_fix"], recorded)
        gap = self.gap_id("BBBB2222")
        before = self.cache_entry(gap)
        self.assertEqual(before["status"], "done_by_self", before)
        row_before = self.blacklist_row(gap)
        old = before["model_evidence"]
        new = old.replace("已接住该点", "已接住了该点")
        self.assertNotEqual(old, new)

        payload = self.repair([self.repair_row("model_evidence", old, new, gap_id=gap)])
        self.assertEqual(payload["status"], "needs_refresh", payload)

        proof_path, preflight, _plan = self.refresh(facts_path)
        self.assertEqual(preflight["action"], "process", preflight)
        finalized = parse(self.finalize_bound(facts_path, results))
        self.assertEqual(finalized["status"], "ok", finalized)

        row = self.blacklist_row(gap)
        self.assertEqual(row["evidence"], new, row)
        for field in ("completed_by_item_key", "candidate_paper_ids", "paper_title",
                      "paper_year", "confidence", "evaluated_at"):
            self.assertEqual(row[field], row_before[field], (field, row[field]))
        body = self.document()["body"]
        self.assertIn("接住（依据：", body)
        self.assertIn("已接住了该点", body)
        self.assertNotIn("已接住该点。", body)
        # The partial gap of the same direction keeps its own evidence.
        self.assertEqual(self.cache_entry(self.gap_id("AAAA1111"))["model_evidence"],
                         self.shortlist_row(self.gap_id("AAAA1111"))["evidence"])

    def test_r_a_reused_direction_projects_the_repaired_evidence(self):
        """Both directions reuse their accepted rows and still show the new text."""
        facts_path, results = self.generate_two_directions()
        recorded = self.record_one_of_two("evidence")
        self.assertTrue(recorded["needs_owner_fix"], recorded)
        fixed = self.pack()["validator"]["fixed_blocking"]
        self.assertEqual(list(fixed), ["DIR00001"], fixed)
        self.assertEqual([row["field"] for row in fixed["DIR00001"]], ["evidence"], fixed)
        gap = self.gap_id("AAAA1111")
        old = self.cache_entry(gap)["model_evidence"]
        new = old.replace("后续由", "后续工作由")
        payload = self.repair([self.repair_row("model_evidence", old, new)])
        self.assertEqual(payload["status"], "needs_refresh", payload)

        proof_path, preflight, plan = self.refresh(facts_path)
        self.assertEqual(preflight["action"], "process", preflight)
        self.assertEqual([row["action"] for row in plan["directions"]],
                         ["reuse", "reuse"], plan)
        finalized = parse(self.finalize_bound(facts_path, results))
        self.assertEqual(finalized["status"], "ok", finalized)

        for direction_id in ("DIR00001", "DIR00002"):
            self.assertEqual(self.shortlist_row(gap, direction_id)["evidence"], new,
                             direction_id)
        lines = [line for line in self.document()["body"].splitlines()
                 if line.startswith("- 后续论文依据：")]
        self.assertEqual(len(lines), 2, lines)
        for line in lines:
            self.assertIn("后续工作由", line)
            self.assertNotIn("后续由 ", line)
        # Reuse carried the accepted narrative untouched.
        narrative = self.direction_entry()["narrative"]["positioning"][0]["text"]
        self.assertIn("合成输入比较", narrative)

    # -- R-B: ineligible, stale and partial batches --------------------------

    def test_r_b_finding_on_one_field_does_not_authorize_the_other_fields(self):
        """Only ``model_evidence`` is registered; the two gap fields stay refused."""
        self.generate_pack(self.gap_override())
        self.record_findings("evidence")
        gap = self.gap_id("AAAA1111")
        entry = self.cache_entry(gap)
        protected = self.all_files_snapshot()
        payload = self.rejected([
            self.repair_row("completed_part", entry["completed_part"],
                            entry["completed_part"].replace("已完成一部分",
                                                            "已完成其中一部分")),
            self.repair_row("remaining_gap", entry["remaining_gap"],
                            entry["remaining_gap"].replace("仍缺", "仍缺少")),
        ])
        # EP2 requires an actionable result, not a bare refusal: the caller must
        # get more than a status and a code so it can tell what was not covered.
        self.assertTrue(set(payload) - {"status", "reason_code"}, payload)
        self.assertEqual(self.all_files_snapshot(), protected)

    def test_r_b_quote_and_generator_findings_keep_their_owner(self):
        """A quote finding and a label finding authorize no cache field."""
        quote_env = self.fresh_repair_env()
        quote_env.generate_pack(quote_env.gap_override())
        quote_env.record_findings("quote")
        gap = quote_env.gap_id("AAAA1111")
        entry = quote_env.cache_entry(gap)
        protected = quote_env.all_files_snapshot()
        quote_env.rejected([
            quote_env.repair_row("model_evidence", entry["model_evidence"],
                                 entry["model_evidence"].replace("后续由", "后续工作由"))])
        # A quote's owner is the source owner as well, so naming that owner is
        # not authority to rewrite the cache: the row still has to be refused,
        # and the refusal must not change a byte.
        self.assertEqual(quote_env.all_files_snapshot(), protected)

        label_env = self.fresh_repair_env()
        label_env.generate_pack(label_env.gap_override())
        label_env.record_findings("label")
        gap = label_env.gap_id("AAAA1111")
        entry = label_env.cache_entry(gap)
        protected = label_env.all_files_snapshot()
        payload = label_env.rejected([
            label_env.repair_row("model_evidence", entry["model_evidence"],
                                 entry["model_evidence"].replace("后续由", "后续工作由"))])
        # The template/label owner is the generator, so the caller must be sent
        # there instead of being told to repair the source text.
        self.assertIn("generator", _scalar_tokens(payload), payload)
        self.assertEqual(label_env.all_files_snapshot(), protected)

    def test_r_b_stale_expectations_are_rejected_before_writing(self):
        """A stale cache digest, validation digest or old text stops the row."""
        self.generate_pack(self.gap_override())
        self.record_findings("evidence")
        gap = self.gap_id("AAAA1111")
        old = self.cache_entry(gap)["model_evidence"]
        new = old.replace("后续由", "后续工作由")
        protected = self.all_files_snapshot()

        for label, row in (
                ("stale cache digest",
                 self.repair_row("model_evidence", old, new,
                                 expected_cache="0" * 64)),
                ("stale validation digest",
                 self.repair_row("model_evidence", old, new,
                                 expected_validation="1" * 64)),
                # The expected old text is part of the same stale-write
                # protection: a drifted field text is not silently applied.
                ("drifted field text",
                 self.repair_row("model_evidence", "不存在的旧文本", new))):
            with self.subTest(case=label):
                self.rejected([row])
                self.assertEqual(self.all_files_snapshot(), protected)

    def test_r_b_a_batch_with_one_bad_row_writes_nothing(self):
        """The whole batch is validated before the first cache byte changes."""
        self.generate_pack(self.gap_override())
        self.record_findings("evidence")
        gap = self.gap_id("AAAA1111")
        entry = self.cache_entry(gap)
        protected = self.all_files_snapshot()
        # The second row targets a field the registered finding does not cover.
        self.rejected([
            self.repair_row("model_evidence", entry["model_evidence"],
                            entry["model_evidence"].replace("后续由", "后续工作由")),
            self.repair_row("completed_part", entry["completed_part"],
                            entry["completed_part"].replace("已完成一部分",
                                                            "已完成其中一部分")),
        ])
        self.assertEqual(self.all_files_snapshot(), protected)

        # Duplicate rows for the same direction/gap/field reject instead of
        # letting the last row win.
        self.rejected([
            self.repair_row("model_evidence", entry["model_evidence"],
                            entry["model_evidence"].replace("后续由", "后续工作由")),
            self.repair_row("model_evidence", entry["model_evidence"],
                            entry["model_evidence"].replace("后续由", "后续工作由了")),
        ])
        self.assertEqual(self.all_files_snapshot(), protected)

    # -- R-C: manual conflict and no-op --------------------------------------

    def test_r_c_manual_markdown_change_keeps_the_conflict_path(self):
        """A hand-edited managed body is never silently replaced or re-bound."""
        facts_path, results, _proof = self.generate_pack(self.gap_override())
        self.record_pass("repair-pass.json")
        validator_before = json.loads(json.dumps(self.pack()["validator"]))
        self.assertEqual(validator_before["phase"], "terminal", validator_before)
        gap = self.gap_id("AAAA1111")
        old = self.cache_entry(gap)["model_evidence"]
        new = old.replace("后续由", "后续工作由")
        payload = self.repair([self.repair_row("model_evidence", old, new)])
        self.assertEqual(payload["status"], "needs_refresh", payload)

        proof_path, preflight, _plan = self.refresh(facts_path)
        self.assertEqual(preflight["action"], "process", preflight)
        md_path = self.prof_dir / contact_state.ANALYSIS_MD
        md_path.write_text(md_path.read_text(encoding="utf-8").replace(
            "- 页码：p.8", "- 页码：p.9（人工改写）"), encoding="utf-8")
        edited = md_path.read_bytes()

        for attempt in (1, 2):
            result = self.finalize_bound(facts_path, results)
            try:
                outcome = json.loads(result.stdout)
            except ValueError:
                outcome = {}
            if result.returncode == 0:
                self.assertEqual(outcome.get("status"), "needs_decision", outcome)
            else:
                self.assertEqual(outcome.get("status"), "error", outcome)
                self.assertEqual(outcome.get("reason_code"), "validation_render_stale",
                                 outcome)
            self.assertEqual(md_path.read_bytes(), edited, attempt)
            self.assertEqual(json.loads(json.dumps(self.pack()["validator"])),
                             validator_before, attempt)

        # The existing explicit overwrite decision still resolves the conflict;
        # it accepts the new body and therefore drops the stale validator.
        decision = self.root / "decision.json"
        decision.write_text(json.dumps({"decision": "overwrite"}), encoding="utf-8")
        resolved = self.finalize_bound(facts_path, results, "--decision-file", decision)
        self.assertEqual(resolved.returncode, 0, (resolved.stdout, resolved.stderr))
        self.assertEqual(parse(resolved).get("status"), "ok", resolved.stdout)
        body = self.document()["body"]
        self.assertNotIn("人工改写", body)
        self.assertIn("后续工作由", body)
        self.assertNotIn("validator", self.pack())

    def test_r_c_no_op_repair_changes_nothing_and_keeps_the_recorded_rounds(self):
        """An unchanged replacement is not a new source version."""
        # Exhaust the review first: a passing round 1 would let a no-op look
        # harmless for the wrong reason, because there would be nothing to reset.
        facts_path, results, _proof = self.generate_pack(
            self.gap_override(), narrative_mutate=self._add_narrative_block)
        narrative_line = self.physical_line("纯叙事待改文字")
        first = self.write_report("noop-round1.json", [
            self.blocking_issue("纯叙事待改文字", narrative_line)])
        recorded = self.record(first)
        self.assertFalse(recorded["needs_owner_fix"], recorded)
        self.assertEqual(self.refine_plan(first)["status"], "ok")
        refined = self.refine_finalize(
            self.write_narrative_rewrite("纯叙事待改文字", "纯叙事已改文字"), first)
        self.assertEqual(refined["phase"], "awaiting_second_validation", refined)

        # Round 2 lands on the source-owned evidence line: terminal, two rounds
        # used, the fix still owned by the source owner.
        needle, prefix = FINDINGS["evidence"]
        second = self.write_report("noop-round2.json", [
            self.blocking_issue(needle, self.line_with(needle, prefix))])
        terminal = self.record(second)
        self.assertEqual(terminal["round"], 2, terminal)
        self.assertTrue(terminal["terminal"], terminal)
        self.assertTrue(terminal["needs_owner_fix"], terminal)
        validator_before = json.loads(json.dumps(self.pack()["validator"]))
        self.assertEqual(validator_before["phase"], "terminal", validator_before)
        self.assertEqual(
            validator_before["results"]["DIR00001"]["result"], "fail_after_2_rounds",
            validator_before)

        gap = self.gap_id("AAAA1111")
        old = self.cache_entry(gap)["model_evidence"]
        protected = self.all_files_snapshot()

        payload = self.repair([self.repair_row("model_evidence", old, old)])
        # A no-op cannot be a fresh source version, so it cannot restart the
        # exhausted round: no cache, Markdown, pack or validator change.
        self.assertIn(payload.get("status"), ("ok", "needs_refresh"), payload)
        self.assertNotEqual(payload.get("status"), "pass", payload)
        self.assertEqual(self.all_files_snapshot(), protected)
        self.assertEqual(json.loads(json.dumps(self.pack()["validator"])),
                         validator_before)
        self.assertEqual(self.cache_entry(gap)["model_evidence"], old)


class SourceEvidenceRepairContractTests(unittest.TestCase):
    """TP2 R-D: the CLI surface and the caller-facing instructions."""

    def test_cli_exposes_the_repair_entry_and_its_two_flags(self):
        result = run_cli("stage2-repair-evidence", "--help")
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertIn("--professor-dir", result.stdout)
        self.assertIn("--repair-file", result.stdout)

    def test_skill_and_analyzers_document_the_repair_contract(self):
        for path in (SKILL_MD, *PROJECTIONS):
            with self.subTest(document=path.name,
                              projection=(path.parents[2].name
                                          if path is not SKILL_MD else "skill")):
                section = _section(path, "stage2-repair-evidence")
                for field in WHITELIST:
                    self.assertIn(field, section)
                # The displayed-name map is stated, not inferred.
                mapping = [line for line in section.splitlines()
                           if "blacklist_evidence" in line and "model_evidence" in line]
                self.assertTrue(mapping, section)
                self.assertIn("needs_refresh", section)
                # The repaired string still needs an ordinary fresh validation
                # and does not itself become a passing result.
                self.assertTrue(re.search(r"校验|validator", section), section)
                self.assertTrue(re.search(r"PASS|通过|合格", section), section)

    def test_docs_do_not_claim_this_entry_repairs_other_errors(self):
        for path in (SKILL_MD, *PROJECTIONS):
            with self.subTest(document=path.name,
                              projection=(path.parents[2].name
                                          if path is not SKILL_MD else "skill")):
                section = _section(path, "stage2-repair-evidence")
                # The eligibility limit is explicit: one finding authorizes one
                # field, and quote/template findings stay with their owner.
                self.assertTrue(re.search(r"字段|field", section), section)
                self.assertTrue(re.search(r"不授权|只授权|不得|不能", section), section)


if __name__ == "__main__":
    unittest.main()
