"""Human-authorized Stage-2/Stage-3 validation continuation (test plan TP1).

Prepared selectors for Gate2 (the approved execution plan EP1.1 permits
renaming, but not omitting these semantics):

- ``stage2-continue-validation`` / ``stage3-continue-validation`` accept
  ``--professor-dir``, ``--additional-rounds``, ``--authorization``,
  ``--expected-round`` and ``--expected-state-sha256``.  They succeed only on
  a currently exhausted failing state whose round and exact state-file digest
  match, and they report ``round``, ``round_limit`` and ``remaining``.
- The stage's professor-local validator block keeps one versioned
  ``continuation`` object ``{"version": 1, "base_limit": 2, "grants": [...]}``
  whose grants carry ``old_limit``, ``additional_rounds``, ``new_limit``,
  ``granted_at``, ``authorization``, ``exhausted_round`` and
  ``expected_state_sha256``.
- Every recorded round, including the final passing round, leaves exactly one
  ``history`` row with ``round``, ``results`` (the same minimal per-direction
  rows the validator records), the render binding, the input binding
  (``pack_sha256`` for Stage 2, ``input_fingerprints`` for Stage 3) and the raw
  report ``validation_file`` / ``validation_sha256``.  A grant keeps the
  just-exhausted failure row in current ``results`` until the next record
  replaces it, and never appends a second row for an already-recorded round.
- An extended terminal row reads ``fail_after_max_rounds`` with ``rounds`` and
  ``max_rounds``; an unextended two-round exhaustion keeps
  ``fail_after_2_rounds``.  ``stage2-record-validation`` reports
  ``round_limit`` so the effective limit stays readable while rounds advance.
- A genuine new cycle moves the replaced validator snapshot into the state's
  top-level ``validation_history`` list; a no-op rerender keeps the current
  validator unchanged.

Stage 3 rounds 3-5 all go through the complete prepare -> write -> save ->
record handoff; no extended round falls back to the direct record entry.

The tests are the TP1 C-A..C-D checking entry points.  C-E is a static review
listed in the recipe and is not duplicated here.
"""
import copy
import hashlib
import json
import tempfile
from pathlib import Path

from stage2_upstream_fixture import run_bound_stage2_finalize
from test_contact_state import BaseEnv, contact_state, parse, run_cli, stage2_style_validation_report
from test_stage3_direction_groups import Stage3DirectionGroupBase

NOTE = "用户明确要求继续修订合成稿件。"
FIRST = "合成追加校验第一处。"
SECOND = "合成追加校验第二处。"
THIRD = "合成追加校验第三处。"
FOURTH = "合成追加校验第四处。"
FIFTH = "合成追加校验第五处。"
GLOBAL_QUOTE = "本文件不复述"
STAGE2_STATE = contact_state.INPUT_PACK
STAGE3_STATE = contact_state.CANDIDATE_STATE


def sha256_path(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def continuation_arguments(stage, professor_dir, *, additional_rounds, authorization,
                           expected_round, expected_state_sha256):
    return [f"stage{stage}-continue-validation",
            "--professor-dir", professor_dir,
            "--additional-rounds", additional_rounds,
            "--authorization", authorization,
            "--expected-round", expected_round,
            "--expected-state-sha256", expected_state_sha256]


def parse_continuation(*arguments):
    result = run_cli(*arguments)
    if result.returncode != 0:
        raise AssertionError(
            f"continuation command exited {result.returncode}: "
            f"{result.stdout!r} / {result.stderr!r}")
    return parse(result)


def refused(result):
    """A command is refused when the CLI rejects it or JSON reports an error."""
    if result.returncode != 0:
        return True
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return True
    return payload.get("status") != "ok"


def latest_history_round(validator, round_no):
    """The last recorded history row for one actual round."""
    rows = [row for row in validator.get("history") or []
            if isinstance(row, dict) and row.get("round") == round_no]
    if not rows:
        raise AssertionError(f"no history row for round {round_no}: {validator.get('history')!r}")
    return rows[-1]


class ContinuationContractMixin:
    def assert_grant(self, validator, *, old_limit, additional_rounds, new_limit,
                     exhausted_round, authorization, state_sha, total):
        continuation = validator.get("continuation")
        self.assertIsInstance(continuation, dict, validator)
        self.assertEqual(continuation.get("version"), 1, continuation)
        self.assertEqual(continuation.get("base_limit"), 2, continuation)
        grants = continuation.get("grants")
        self.assertIsInstance(grants, list, continuation)
        self.assertEqual(len(grants), total, continuation)
        grant = grants[-1]
        self.assertEqual(grant.get("old_limit"), old_limit, grant)
        self.assertEqual(grant.get("additional_rounds"), additional_rounds, grant)
        self.assertEqual(grant.get("new_limit"), new_limit, grant)
        self.assertEqual(grant.get("exhausted_round"), exhausted_round, grant)
        self.assertEqual(grant.get("authorization"), authorization, grant)
        self.assertEqual(grant.get("expected_state_sha256"), state_sha, grant)
        self.assertIsInstance(grant.get("granted_at"), str, grant)
        self.assertTrue(grant.get("granted_at"), grant)

    def assert_continuation_refused_without_write(self, result, path, before):
        self.assertTrue(refused(result), result)
        self.assertEqual(Path(path).read_bytes(), before)


class Stage2Fixture(BaseEnv):
    """The Stage-2 producer fixtures TP1 reuses, without another module's tests."""

    def _fresh_env(self):
        env = self.__class__(self._testMethodName)
        env.setUp()
        self.addCleanup(env.tearDown)
        return env

    def generate_pack(self, mutate_facts=None, narrative_mutate=None):
        facts_path = self.write_facts(mutate_facts)
        results = self.root / "results"
        self.write_stage2_results(results)
        if narrative_mutate:
            narrative_path = results / "narrative.json"
            narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
            narrative_mutate(narrative)
            narrative_path.write_text(json.dumps(narrative, ensure_ascii=False),
                                      encoding="utf-8")
        plan = parse(self.run_bound_stage2_plan(facts_path))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(
            run_cli, facts_path, "--results", results))
        self.assertEqual(finalized["status"], "ok", finalized)
        return facts_path, results

    def pack(self):
        return json.loads((self.prof_dir / STAGE2_STATE).read_text(encoding="utf-8"))

    def write_pack(self, payload):
        (self.prof_dir / STAGE2_STATE).write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    def body_lines(self):
        return (self.prof_dir / contact_state.ANALYSIS_MD).read_text(
            encoding="utf-8").splitlines()

    def physical_line(self, needle, expected=1):
        hits = [index + 1 for index, line in enumerate(self.body_lines())
                if needle in line]
        self.assertEqual(len(hits), expected, (needle, hits))
        return hits if expected > 1 else hits[0]

    def blocking_issue(self, quote, location):
        return {"rule": "A1", "severity": "blocking", "location": location,
                "quote": quote, "suggestion": "改用日常语言解释。"}

    def write_report(self, name, issues, verdict=None):
        issues = [dict(issue) for issue in issues]
        if verdict is None:
            verdict = ("fail" if any(issue.get("severity") == "blocking"
                                     for issue in issues)
                       else "pass_with_minor" if issues else "pass")
        analysis = self.prof_dir / contact_state.ANALYSIS_MD
        payload = stage2_style_validation_report(analysis, verdict, issues)
        path = self.root / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def record(self, report):
        return parse(run_cli("stage2-record-validation", "--professor-dir",
                             self.prof_dir, "--validation-file", report))

    def refine_plan(self, report):
        return parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                             "--validation-file", report))

    def refine_finalize(self, results, report):
        return parse(run_cli("stage2-refine-finalize", "--professor-dir",
                             self.prof_dir, "--results", results,
                             "--validation-file", report))

    def write_narrative_rewrite(self, before, after, name="rewrite"):
        direction = self.pack()["directions"][0]
        narrative = copy.deepcopy(direction["narrative"])
        block = next(block for block in narrative["positioning"]
                     if before in block.get("text", ""))
        block["text"] = block["text"].replace(before, after, 1)
        rewrite = {
            "schema": 1, "kind": "narrative-rewrite",
            "direction_id": direction["direction_id"],
            "collection_key": direction.get("collection_key"),
            "positioning": narrative["positioning"],
            "gap_notes": [
                {"gap_id": gap_id, "summary": value["summary"],
                 "explanation": value["explanation"]}
                for gap_id, value in narrative["gap_notes"].items()],
        }
        results = self.root / name
        results.mkdir(parents=True, exist_ok=True)
        (results / f"narrative-rewrite-{direction['direction_id']}.json").write_text(
            json.dumps(rewrite, ensure_ascii=False), encoding="utf-8")
        return results


class Stage2ContinuationTests(ContinuationContractMixin, Stage2Fixture):
    def add_block(self, text):
        def mutate(narrative):
            narrative["directions"][0]["positioning"].append({
                "kind": "para", "text": text, "refs": [],
                "concrete_object": "合成追加校验对象",
                "input_example": "输入一份合成样本",
                "output_example": "得到一份合成结果"})
        return mutate

    def terminal_two_rounds(self):
        """A genuine two-round Stage-2 failure with a repairable narrative finding."""
        self.round_bindings = {}
        self.generate_pack(narrative_mutate=self.add_block(FIRST))
        first = self.write_report("continuation-round-1.json", [
            self.blocking_issue(FIRST, self.physical_line(FIRST))])
        recorded = self.record(first)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.round_bindings[1] = {
            "render_sha256": recorded["render_sha256"],
            "pack_sha256": self.pack()["validator"]["pack_sha256"]}
        self.correct(first, FIRST, SECOND, "continuation-rewrite-1")

        second = self.write_report("continuation-round-2.json", [
            self.blocking_issue(SECOND, self.physical_line(SECOND))])
        terminal = self.record(second)
        self.assertEqual(terminal["status"], "ok", terminal)
        self.assertEqual(terminal["round"], 2, terminal)
        self.assertTrue(terminal["terminal"], terminal)
        self.round_bindings[2] = {
            "render_sha256": terminal["render_sha256"],
            "pack_sha256": self.pack()["validator"]["pack_sha256"]}
        return first, second

    def correct(self, report, before, after, name):
        planned = self.refine_plan(report)
        self.assertEqual(planned["status"], "ok", planned)
        self.assertEqual([job["direction_id"] for job in planned["jobs"]], ["DIR00001"])
        written = self.refine_finalize(
            self.write_narrative_rewrite(before, after, name=name), report)
        self.assertEqual(written["status"], "ok", written)

    def grant(self, *, additional_rounds, expected_round, expected_state_sha256,
              authorization=NOTE):
        return parse_continuation(*continuation_arguments(
            2, self.prof_dir, additional_rounds=additional_rounds,
            authorization=authorization, expected_round=expected_round,
            expected_state_sha256=expected_state_sha256))

    def raw_grant(self, *, additional_rounds=2, expected_round=2,
                  expected_state_sha256=None, authorization=NOTE):
        if expected_state_sha256 is None:
            expected_state_sha256 = sha256_path(self.prof_dir / STAGE2_STATE)
        return run_cli(*continuation_arguments(
            2, self.prof_dir, additional_rounds=additional_rounds,
            authorization=authorization, expected_round=expected_round,
            expected_state_sha256=expected_state_sha256))

    def test_c_a_extended_rounds_accumulate_and_keep_old_failures(self):
        first, second = self.terminal_two_rounds()
        pack_path = self.prof_dir / STAGE2_STATE
        pack_sha = sha256_path(pack_path)
        terminal_validator = self.pack()["validator"]
        terminal_render_sha = terminal_validator["render_sha256"]
        terminal_pack_sha = terminal_validator["pack_sha256"]
        raw_reports = {path: path.read_bytes() for path in (first, second)}

        # A.2 default stays two: a third record is refused before any grant.
        refused_third = self.record(self.write_report(
            "continuation-refused-3.json",
            [self.blocking_issue(SECOND, self.physical_line(SECOND))]))
        self.assertEqual(refused_third["status"], "error", refused_third)
        self.assertEqual(refused_third["reason_code"], "validation_rounds_exhausted",
                         refused_third)
        self.assertEqual(sha256_path(pack_path), pack_sha)

        # A.3 explicit +2: limit 4, round 2 kept, old failure still visible.
        granted = self.grant(additional_rounds=2, expected_round=2,
                             expected_state_sha256=pack_sha)
        self.assertEqual(granted["status"], "ok", granted)
        self.assertEqual(granted["round"], 2, granted)
        self.assertEqual(granted["round_limit"], 4, granted)
        self.assertEqual(granted["remaining"], 2, granted)
        validator = self.pack()["validator"]
        self.assert_grant(validator, old_limit=2, additional_rounds=2, new_limit=4,
                          exhausted_round=2, authorization=NOTE,
                          state_sha=pack_sha, total=1)
        self.assertEqual(validator["phase"], "needs_correction", validator)
        self.assertEqual(validator["results"]["DIR00001"]["result"],
                         "fail_after_2_rounds", validator["results"])
        self.assertEqual(sorted(validator["pending"]), ["DIR00001"], validator)
        rounds = [row.get("round") for row in validator["history"] or []]
        self.assertEqual(rounds.count(2), 1, validator["history"])

        # A.4 correction, then a real cumulative round 3.
        self.correct(second, SECOND, THIRD, "continuation-rewrite-2")
        third_report = self.write_report("continuation-round-3.json", [
            self.blocking_issue(THIRD, self.physical_line(THIRD))])
        third = self.record(third_report)
        self.assertEqual(third["status"], "needs_correction", third)
        self.assertEqual(third["round"], 3, third)
        self.assertEqual(third["round_limit"], 4, third)
        self.round_bindings[3] = {
            "render_sha256": third["render_sha256"],
            "pack_sha256": self.pack()["validator"]["pack_sha256"]}
        validator = self.pack()["validator"]
        self.assertEqual(validator["round"], 3, validator)
        round_two = latest_history_round(validator, 2)
        self.assertEqual(round_two["results"]["DIR00001"]["result"],
                         "fail_after_2_rounds", round_two)
        self.assertEqual(round_two["render_sha256"], terminal_render_sha, round_two)
        self.assertEqual(round_two["pack_sha256"], terminal_pack_sha, round_two)
        self.assertEqual(round_two["validation_file"], str(second), round_two)
        self.assertEqual(round_two["validation_sha256"], sha256_path(second), round_two)

        # A.5 round 4 fails at the extended limit and reports the real exhaustion.
        self.correct(third_report, THIRD, FOURTH, "continuation-rewrite-3")
        fourth_report = self.write_report("continuation-round-4.json", [
            self.blocking_issue(FOURTH, self.physical_line(FOURTH))])
        fourth = self.record(fourth_report)
        self.assertEqual(fourth["round"], 4, fourth)
        self.assertTrue(fourth["terminal"], fourth)
        self.round_bindings[4] = {
            "render_sha256": fourth["render_sha256"],
            "pack_sha256": self.pack()["validator"]["pack_sha256"]}
        validator = self.pack()["validator"]
        row = validator["results"]["DIR00001"]
        self.assertEqual(row["result"], "fail_after_max_rounds", row)
        self.assertEqual(row["rounds"], 4, row)
        self.assertEqual(row["max_rounds"], 4, row)

        # A.6 no borrowed extension: a fifth record is refused at limit 4.
        before_fifth = pack_path.read_bytes()
        refused_fifth = self.record(self.write_report(
            "continuation-refused-5.json",
            [self.blocking_issue(FOURTH, self.physical_line(FOURTH))]))
        self.assertEqual(refused_fifth["status"], "error", refused_fifth)
        self.assertEqual(refused_fifth["reason_code"], "validation_rounds_exhausted",
                         refused_fifth)
        self.assertEqual(pack_path.read_bytes(), before_fifth)

        # A.7 a second explicit +1 raises the limit from 4 to 5 and round 5 passes.
        before_second_grant = sha256_path(pack_path)
        granted_again = self.grant(additional_rounds=1, expected_round=4,
                                   expected_state_sha256=before_second_grant)
        self.assertEqual(granted_again["status"], "ok", granted_again)
        self.assertEqual(granted_again["round_limit"], 5, granted_again)
        self.assertEqual(granted_again["remaining"], 1, granted_again)
        validator = self.pack()["validator"]
        self.assert_grant(validator, old_limit=4, additional_rounds=1, new_limit=5,
                          exhausted_round=4, authorization=NOTE,
                          state_sha=before_second_grant, total=2)
        self.correct(fourth_report, FOURTH, FIFTH, "continuation-rewrite-4")
        passed_report = self.write_report("continuation-round-5.json", [],
                                          verdict="pass")
        passed = self.record(passed_report)
        self.assertEqual(passed["round"], 5, passed)
        self.assertTrue(passed["terminal"], passed)
        self.round_bindings[5] = {
            "render_sha256": passed["render_sha256"],
            "pack_sha256": self.pack()["validator"]["pack_sha256"]}
        validator = self.pack()["validator"]
        self.assertEqual(validator["results"]["DIR00001"]["result"], "pass",
                         validator["results"])
        self.assertEqual(validator["results"]["DIR00001"]["rounds"], 5,
                         validator["results"])
        round_three = latest_history_round(validator, 3)
        self.assertEqual(round_three["results"]["DIR00001"]["result"],
                         "needs_correction", round_three)
        round_four = latest_history_round(validator, 4)
        self.assertEqual(round_four["results"]["DIR00001"]["result"],
                         "fail_after_max_rounds", round_four)
        self.assertEqual(round_four["results"]["DIR00001"]["max_rounds"], 4,
                         round_four)
        self.assertEqual(validator["continuation"]["grants"][0]["exhausted_round"], 2,
                         validator["continuation"])
        self.assertEqual(validator["continuation"]["grants"][1]["old_limit"], 4,
                         validator["continuation"])

        # Every actual round keeps its result, report path and digest.  The final
        # passing round is in the history too; a grant never duplicates a row.
        expected_history = [
            (1, "needs_correction", first),
            (2, "fail_after_2_rounds", second),
            (3, "needs_correction", third_report),
            (4, "fail_after_max_rounds", fourth_report),
            (5, "pass", passed_report),
        ]
        for round_no, label, report in expected_history:
            recorded = latest_history_round(validator, round_no)
            self.assertEqual(recorded["results"]["DIR00001"]["result"], label,
                             (round_no, recorded))
            self.assertEqual(recorded["validation_file"], str(report),
                             (round_no, recorded))
            self.assertEqual(recorded["validation_sha256"], sha256_path(report),
                             (round_no, recorded))
            self.assertEqual(recorded["render_sha256"],
                             self.round_bindings[round_no]["render_sha256"],
                             (round_no, recorded))
            self.assertEqual(recorded["pack_sha256"],
                             self.round_bindings[round_no]["pack_sha256"],
                             (round_no, recorded))
        rounds = [row.get("round") for row in validator["history"] or []]
        self.assertEqual(rounds.count(2), 1, validator["history"])
        self.assertEqual(rounds.count(4), 1, validator["history"])
        self.assertEqual(validator["round"], 5, validator)
        self.assertEqual({path: path.read_bytes() for path in raw_reports}, raw_reports)

        # A.8 a passing terminal state cannot be reopened for extra sampling.
        before_pass_grant = pack_path.read_bytes()
        after_pass = self.raw_grant(additional_rounds=1, expected_round=5,
                                    expected_state_sha256=sha256_path(pack_path))
        self.assert_continuation_refused_without_write(
            after_pass, pack_path, before_pass_grant)

    def test_c_b_stage2_rejected_requests_leave_the_record_unchanged(self):
        self.terminal_two_rounds()
        pack_path = self.prof_dir / STAGE2_STATE
        baseline = pack_path.read_bytes()
        cases = {
            "zero additional rounds": dict(additional_rounds=0),
            "negative additional rounds": dict(additional_rounds=-1),
            "empty authorization": dict(authorization=""),
            "wrong expected round": dict(expected_round=1),
            "wrong state digest": dict(expected_state_sha256="0" * 64),
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                result = self.raw_grant(**overrides)
                self.assert_continuation_refused_without_write(
                    result, pack_path, baseline)

        # A valid grant reopens the state; the same request cannot grant twice.
        granted = self.grant(additional_rounds=2, expected_round=2,
                             expected_state_sha256=sha256_path(pack_path))
        self.assertEqual(granted["status"], "ok", granted)
        reopened_bytes = pack_path.read_bytes()
        repeated = self.raw_grant(additional_rounds=2, expected_round=2,
                                  expected_state_sha256=sha256_path(pack_path))
        self.assert_continuation_refused_without_write(
            repeated, pack_path, reopened_bytes)
        self.assertEqual(
            len(self.pack()["validator"]["continuation"]["grants"]), 1,
            self.pack()["validator"])

        # A real round still needs the existing correction transition.
        skipped = self.record(self.write_report("continuation-jump.json", [
            self.blocking_issue(SECOND, self.physical_line(SECOND))]))
        self.assertEqual(skipped["status"], "error", skipped)
        self.assertEqual(pack_path.read_bytes(), reopened_bytes)

        # A changed managed render or a changed input pack is refused.
        drift = self._fresh_env()
        drift.terminal_two_rounds()
        drift_pack = drift.prof_dir / STAGE2_STATE
        drift_baseline = drift_pack.read_bytes()
        (drift.prof_dir / contact_state.ANALYSIS_MD).write_bytes(
            (drift.prof_dir / contact_state.ANALYSIS_MD).read_bytes() + b"\nmanual drift\n")
        render_result = drift.raw_grant(
            expected_state_sha256=sha256_path(drift_pack))
        self.assert_continuation_refused_without_write(
            render_result, drift_pack, drift_baseline)

        source = self._fresh_env()
        source.terminal_two_rounds()
        source_pack = source.prof_dir / STAGE2_STATE
        payload = source.pack()
        payload["directions"][0]["input_fingerprint"] = "changed-after-validation"
        source.write_pack(payload)
        source_baseline = source_pack.read_bytes()
        source_result = source.raw_grant(
            expected_state_sha256=sha256_path(source_pack))
        self.assert_continuation_refused_without_write(
            source_result, source_pack, source_baseline)

    def test_c_c_stage2_fixed_source_block_stays_owner_work_after_a_grant(self):
        self.generate_pack(narrative_mutate=self.add_block(FIRST))
        first = self.write_report("continuation-fixed-1.json", [
            self.blocking_issue(FIRST, self.physical_line(FIRST))])
        self.assertEqual(self.record(first)["round"], 1)
        self.correct(first, FIRST, SECOND, "continuation-fixed-rewrite")
        fixed_line = self.physical_line("评估时间：", expected=2)[0]
        structural_issue = self.blocking_issue("评估时间：", fixed_line)
        # Simulate a structural owner finding; the timestamp is only its locator.
        structural_issue["rule"] = "C9"
        second = self.write_report("continuation-fixed-2.json", [structural_issue])
        terminal = self.record(second)
        self.assertEqual(terminal["round"], 2, terminal)
        self.assertTrue(terminal["terminal"], terminal)
        self.assertTrue(terminal["needs_owner_fix"], terminal)
        fixed_rows = self.pack()["validator"]["fixed_blocking"]["DIR00001"]
        self.assertTrue(fixed_rows, fixed_rows)
        for row in fixed_rows:
            self.assertEqual(set(row), {"direction_id", "gap_id", "field", "owner"}, row)
        self.assertIn("generator", {row["owner"] for row in fixed_rows}, fixed_rows)

        granted = self.grant(additional_rounds=2, expected_round=2,
                             expected_state_sha256=sha256_path(
                                 self.prof_dir / STAGE2_STATE))
        self.assertEqual(granted["status"], "ok", granted)
        validator = self.pack()["validator"]
        self.assertEqual(validator["fixed_blocking"]["DIR00001"], fixed_rows)
        self.assertEqual(sorted(validator["pending"]), ["DIR00001"])

        pack_path = self.prof_dir / STAGE2_STATE
        analysis_path = self.prof_dir / contact_state.ANALYSIS_MD
        pack_before = pack_path.read_bytes()
        analysis_before = analysis_path.read_bytes()
        planned = self.refine_plan(second)
        self.assertEqual(planned["status"], "needs_owner_fix", planned)
        self.assertEqual(planned["reason_code"], "fixed_evidence_blocking", planned)
        self.assertEqual(planned["jobs"], [], planned)
        self.assertFalse(planned["write_needed"], planned)
        finalized = self.refine_finalize(self.root / "unused-results", second)
        self.assertEqual(finalized["status"], "needs_owner_fix", finalized)
        self.assertEqual(finalized["rewritten"], [], finalized)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(analysis_path.read_bytes(), analysis_before)

    def test_c_d_stage2_legacy_record_needs_an_explicit_grant(self):
        _first, second = self.terminal_two_rounds()
        pack_path = self.prof_dir / STAGE2_STATE
        payload = self.pack()
        for field in ("continuation", "history", "round_limit"):
            payload["validator"].pop(field, None)
        self.write_pack(payload)
        legacy_sha = sha256_path(pack_path)

        refused_third = self.record(self.write_report(
            "continuation-legacy-third.json",
            [self.blocking_issue(SECOND, self.physical_line(SECOND))]))
        self.assertEqual(refused_third["status"], "error", refused_third)
        self.assertEqual(refused_third["reason_code"], "validation_rounds_exhausted",
                         refused_third)
        self.assertEqual(sha256_path(pack_path), legacy_sha)

        granted = self.grant(additional_rounds=2, expected_round=2,
                             expected_state_sha256=legacy_sha)
        self.assertEqual(granted["status"], "ok", granted)
        self.assertEqual(granted["round_limit"], 4, granted)
        validator = self.pack()["validator"]
        self.assert_grant(validator, old_limit=2, additional_rounds=2, new_limit=4,
                          exhausted_round=2, authorization=NOTE,
                          state_sha=legacy_sha, total=1)
        self.assertEqual(validator["results"]["DIR00001"]["result"],
                         "fail_after_2_rounds", validator["results"])

        # A real new generation replaces the cycle: default two, no inherited grant.
        def new_cycle(facts):
            facts["directions"][0]["user_note"] = "新生成周期的合成用户笔记。"

        self.generate_pack(mutate_facts=new_cycle,
                           narrative_mutate=self.add_block("合成新周期文本。"))
        payload = self.pack()
        validator = payload.get("validator") or {}
        self.assertFalse((validator.get("continuation") or {}).get("grants"),
                         validator)
        self.assertIn(validator.get("round_limit", 2), (None, 2), validator)
        retained_history = payload.get("validation_history")
        self.assertIsInstance(retained_history, list, payload)
        self.assertTrue(retained_history, payload)
        snapshot = retained_history[-1]
        self.assertEqual(snapshot["continuation"]["grants"][0]["authorization"],
                         NOTE, snapshot)
        # This fixture removed the old history on purpose: only the recorded
        # failure result must survive, never a fabricated history row.
        self.assertEqual(snapshot["results"]["DIR00001"]["result"],
                         "fail_after_2_rounds", snapshot)


class Stage3ContinuationTests(ContinuationContractMixin, Stage3DirectionGroupBase):
    def setUp(self):
        super().setUp()
        self.results_dir = None

    def render_two(self):
        results = self.write_results("continuation-two", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.results_dir = results
        return out

    @staticmethod
    def finding(quote, severity="blocking", rule="B5"):
        return {"rule": rule, "severity": severity, "location": "validator 自报位置",
                "quote": quote, "suggestion": "首次出现时用日常语言解释。"}

    def payload(self, issues=(), verdict=None):
        issues = list(issues)
        blocking = [issue for issue in issues if issue.get("severity") == "blocking"]
        return {
            "result": "ok",
            "files": [{
                "file": str(self.prof_dir / "套磁想法候选.md"),
                "artifact": "candidates",
                "verdict": verdict or ("fail" if blocking else "pass"),
                "blocking": len(blocking), "minor": 0, "issues": issues,
            }],
            "notes": "",
        }

    def write_validation(self, name, issues=(), verdict=None):
        path = self.root / name
        path.write_text(json.dumps(self.payload(issues, verdict), ensure_ascii=False),
                        encoding="utf-8")
        return path

    def record(self, report):
        return parse(run_cli("stage3-record-validation", "--professor-dir",
                             self.prof_dir, "--validation-file", report))

    def correction_plan(self, report):
        return parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root,
                             "--validation-file", report))

    def correction_finalize(self, results, report):
        return parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                             "--program-root", self.root, "--results", results,
                             "--validation-file", report))

    def results(self, name, docs):
        results = self.write_results(name, docs)
        self.results_dir = results
        return results

    def correct(self, report, before, after, name):
        planned = self.correction_plan(report)
        self.assertEqual(planned["status"], "ok", planned)
        self.assertTrue(planned["jobs"], planned)
        docs = {}
        for job in planned["jobs"]:
            data = copy.deepcopy(job["model_input"]["current_result"])
            changed = 0
            for candidate in data["candidates"]:
                if candidate.get("title") == before:
                    candidate["title"] = after
                    changed += 1
            self.assertEqual(changed, 1, data["candidates"])
            docs[job["direction_id"]] = data
        results = self.results(name, docs)
        written = self.correction_finalize(results, report)
        self.assertEqual(written["status"], "ok", written)
        self.assertEqual(sorted(written["corrected"]), sorted(docs), written)

    def submit_current(self, report, name):
        planned = self.correction_plan(report)
        self.assertEqual(planned["status"], "ok", planned)
        self.assertTrue(planned["jobs"], planned)
        docs = {}
        for job in planned["jobs"]:
            current = copy.deepcopy(job["model_input"]["current_result"])
            self.assertEqual(job["model_input"]["repairable_candidate_ids"], [], job)
            docs[job["direction_id"]] = current
        results = self.results(name, docs)
        written = self.correction_finalize(results, report)
        self.assertEqual(written["status"], "ok", written)
        self.assertEqual(sorted(written["corrected"]), sorted(docs), written)

    def terminal_two_rounds(self):
        self.round_bindings = {}
        self.render_two()
        first = self.write_validation("continuation-s3-1.json",
                                      [self.finding("候选 dir_B_2")])
        recorded = self.record(first)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertTrue(recorded["needs_correction"], recorded)
        self.round_bindings[1] = {
            "render_sha256": recorded["render_sha256"],
            "input_fingerprints": self.load_state()["input_fingerprints"]}
        self.correct(first, "候选 dir_B_2", "候选 dir_B_2 改写",
                     "continuation-s3-correct-1")
        second = self.write_validation("continuation-s3-2.json",
                                       [self.finding("候选 dir_B_2 改写")])
        terminal = self.record(second)
        self.assertEqual(terminal["round"], 2, terminal)
        self.assertTrue(terminal["terminal"], terminal)
        self.round_bindings[2] = {
            "render_sha256": terminal["render_sha256"],
            "input_fingerprints": self.load_state()["input_fingerprints"]}
        return first, second

    def capture_invocation(self):
        directory = Path(tempfile.mkdtemp(prefix="continuation-invocation-",
                                          dir=self.root))
        planned = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                                "--program-root", self.root,
                                "--direction-id", "dir_B",
                                "--capture-invocation", directory))
        self.assertEqual(planned["status"], "ok", planned)
        return planned["invocation_file"], planned["invocation_sha256"]

    def handoff_record(self, prepared, issues):
        result = run_cli("stage3-write-validation",
                         "--output-file", prepared["output_file"],
                         "--result-json", json.dumps(self.payload(issues),
                                                     ensure_ascii=False))
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = parse(run_cli("stage3-save-validation",
                              "--handoff-file", prepared["handoff_file"],
                              "--handoff-sha256", prepared["handoff_sha256"]))
        self.assertEqual(saved["status"], "ok", saved)
        recorded = parse(run_cli(
            "stage3-record-validation", "--handoff-file", prepared["handoff_file"],
            "--handoff-sha256", prepared["handoff_sha256"],
            "--expected-validation-sha256", saved["validation_sha256"]))
        return recorded, Path(saved["validation_file"])

    def grant(self, *, additional_rounds, expected_round, expected_state_sha256,
              authorization=NOTE):
        return parse_continuation(*continuation_arguments(
            3, self.prof_dir, additional_rounds=additional_rounds,
            authorization=authorization, expected_round=expected_round,
            expected_state_sha256=expected_state_sha256))

    def raw_grant(self, *, additional_rounds=2, expected_round=2,
                  expected_state_sha256=None, authorization=NOTE):
        if expected_state_sha256 is None:
            expected_state_sha256 = sha256_path(self.prof_dir / STAGE3_STATE)
        return run_cli(*continuation_arguments(
            3, self.prof_dir, additional_rounds=additional_rounds,
            authorization=authorization, expected_round=expected_round,
            expected_state_sha256=expected_state_sha256))

    def prepare_round(self, invocation_file, invocation_sha256, round_no):
        return run_cli("stage3-prepare-validation",
                       "--invocation-file", invocation_file,
                       "--invocation-sha256", invocation_sha256,
                       "--round", round_no)

    def test_c_a_extended_rounds_advance_through_the_real_handoff(self):
        first, second = self.terminal_two_rounds()
        state_path = self.prof_dir / STAGE3_STATE
        state_sha = sha256_path(state_path)
        second_bytes = second.read_bytes()
        invocation_file, invocation_sha = self.capture_invocation()
        terminal_validator = self.load_state()["validator"]
        terminal_render_sha = terminal_validator["render_sha256"]
        terminal_inputs = self.load_state()["input_fingerprints"]

        # A.2 default stays two: round 3 is refused before any grant.
        terminal_state_bytes = state_path.read_bytes()
        refused_record = self.record(self.write_validation(
            "continuation-s3-refused-3.json", [self.finding("候选 dir_B_2 改写")]))
        self.assertEqual(refused_record["status"], "error", refused_record)
        self.assertEqual(refused_record["reason_code"], "validation_rounds_exhausted",
                         refused_record)
        refused_prepare = self.prepare_round(invocation_file, invocation_sha, 3)
        self.assertTrue(refused(refused_prepare), refused_prepare)
        self.assertEqual(state_path.read_bytes(), terminal_state_bytes)

        # A.3 explicit +2 restores only the recorded failed scope.
        granted = self.grant(additional_rounds=2, expected_round=2,
                             expected_state_sha256=state_sha)
        self.assertEqual(granted["status"], "ok", granted)
        self.assertEqual(granted["round"], 2, granted)
        self.assertEqual(granted["round_limit"], 4, granted)
        self.assertEqual(granted["remaining"], 2, granted)
        state = self.load_state()
        self.assert_grant(state["validator"], old_limit=2, additional_rounds=2,
                          new_limit=4, exhausted_round=2, authorization=NOTE,
                          state_sha=state_sha, total=1)
        self.assertEqual(state["validator"]["round"], 2, state["validator"])
        self.assertEqual(sorted(state["validator"]["pending"]), ["direction:dir_B"],
                         state["validator"]["pending"])
        self.assertEqual(state["validator"]["results"]["dir_A"]["result"], "pass",
                         state["validator"]["results"])
        self.assertEqual(state["validator"]["results"]["dir_B"]["result"],
                         "fail_after_2_rounds", state["validator"]["results"])

        # A.4 correction, then the next real handoff round; a skipped round fails.
        self.correct(second, "候选 dir_B_2 改写", "候选 dir_B_2 二次改写",
                     "continuation-s3-correct-2")
        jump = self.prepare_round(invocation_file, invocation_sha, 4)
        self.assertTrue(refused(jump), jump)
        prepared = parse(self.prepare_round(invocation_file, invocation_sha, 3))
        self.assertEqual(prepared["status"], "ok", prepared)
        third, third_path = self.handoff_record(
            prepared, [self.finding("候选 dir_B_2 二次改写")])
        third_bytes = third_path.read_bytes()
        self.assertEqual(third["status"], "ok", third)
        self.assertEqual(third["round"], 3, third)
        self.assertTrue(third["needs_correction"], third)
        self.assertEqual(third["round_limit"], 4, third)
        self.round_bindings[3] = {
            "render_sha256": third["render_sha256"],
            "input_fingerprints": self.load_state()["input_fingerprints"]}
        state = self.load_state()
        round_two = latest_history_round(state["validator"], 2)
        self.assertEqual(round_two["results"]["dir_B"]["result"],
                         "fail_after_2_rounds", round_two)
        self.assertEqual(round_two["render_sha256"], terminal_render_sha, round_two)
        self.assertEqual(round_two["input_fingerprints"], terminal_inputs, round_two)
        self.assertEqual(round_two["validation_file"], str(second), round_two)
        self.assertEqual(round_two["validation_sha256"], sha256_path(second), round_two)

        # A.5 round 4 fails at the extended limit through the same handoff.
        self.correct(third_path, "候选 dir_B_2 二次改写", "候选 dir_B_2 三次改写",
                     "continuation-s3-correct-3")
        prepared_fourth = parse(self.prepare_round(
            invocation_file, invocation_sha, 4))
        self.assertEqual(prepared_fourth["status"], "ok", prepared_fourth)
        fourth, fourth_path = self.handoff_record(
            prepared_fourth, [self.finding("候选 dir_B_2 三次改写")])
        fourth_bytes = fourth_path.read_bytes()
        self.assertEqual(fourth["round"], 4, fourth)
        self.assertTrue(fourth["terminal"], fourth)
        self.round_bindings[4] = {
            "render_sha256": fourth["render_sha256"],
            "input_fingerprints": self.load_state()["input_fingerprints"]}
        state = self.load_state()
        row = state["validator"]["results"]["dir_B"]
        self.assertEqual(row["result"], "fail_after_max_rounds", row)
        self.assertEqual(row["rounds"], 4, row)
        self.assertEqual(row["max_rounds"], 4, row)

        # A.6 +1 moves the exhausted limit from 4 to 5; a passing round 5 stops.
        granted_again = self.grant(additional_rounds=1, expected_round=4,
                                   expected_state_sha256=sha256_path(state_path))
        self.assertEqual(granted_again["status"], "ok", granted_again)
        self.assertEqual(granted_again["round_limit"], 5, granted_again)
        self.assertEqual(granted_again["remaining"], 1, granted_again)
        self.correct(fourth_path, "候选 dir_B_2 三次改写", "候选 dir_B_2 四次改写",
                     "continuation-s3-correct-4")
        prepared_fifth = parse(self.prepare_round(
            invocation_file, invocation_sha, 5))
        self.assertEqual(prepared_fifth["status"], "ok", prepared_fifth)
        fifth, fifth_path = self.handoff_record(prepared_fifth, [])
        fifth_bytes = fifth_path.read_bytes()
        self.assertEqual(fifth["round"], 5, fifth)
        self.assertTrue(fifth["terminal"], fifth)
        self.round_bindings[5] = {
            "render_sha256": fifth["render_sha256"],
            "input_fingerprints": self.load_state()["input_fingerprints"]}
        state = self.load_state()
        self.assertEqual(state["validator"]["results"]["dir_B"]["result"], "pass",
                         state["validator"]["results"])
        self.assertEqual(state["validator"]["results"]["dir_B"]["rounds"], 5,
                         state["validator"]["results"])

        # Every actual round keeps its result, report path and digest.  The final
        # passing round is in the history too; a grant never duplicates a row.
        expected_history = [
            (1, "fail", first),
            (2, "fail_after_2_rounds", second),
            (3, "fail", third_path),
            (4, "fail_after_max_rounds", fourth_path),
            (5, "pass", fifth_path),
        ]
        for round_no, label, report in expected_history:
            recorded = latest_history_round(state["validator"], round_no)
            self.assertEqual(recorded["results"]["dir_B"]["result"], label,
                             (round_no, recorded))
            self.assertEqual(recorded["validation_file"], str(report),
                             (round_no, recorded))
            self.assertEqual(recorded["validation_sha256"], sha256_path(report),
                             (round_no, recorded))
            self.assertEqual(recorded["render_sha256"],
                             self.round_bindings[round_no]["render_sha256"],
                             (round_no, recorded))
            self.assertEqual(recorded["input_fingerprints"],
                             self.round_bindings[round_no]["input_fingerprints"],
                             (round_no, recorded))
        rounds = [row.get("round") for row in state["validator"]["history"] or []]
        self.assertEqual(rounds.count(2), 1, state["validator"]["history"])
        self.assertEqual(rounds.count(4), 1, state["validator"]["history"])
        self.assertEqual(state["validator"]["round"], 5, state["validator"])
        self.assertEqual(second.read_bytes(), second_bytes)
        self.assertEqual(third_path.read_bytes(), third_bytes)
        self.assertEqual(fourth_path.read_bytes(), fourth_bytes)
        self.assertEqual(fifth_path.read_bytes(), fifth_bytes)

        before_pass_grant = state_path.read_bytes()
        after_pass = self.raw_grant(additional_rounds=1, expected_round=5,
                                    expected_state_sha256=sha256_path(state_path))
        self.assert_continuation_refused_without_write(
            after_pass, state_path, before_pass_grant)

    def test_c_b_stage3_rejected_requests_leave_the_state_unchanged(self):
        self.terminal_two_rounds()
        state_path = self.prof_dir / STAGE3_STATE
        baseline = state_path.read_bytes()
        cases = {
            "zero additional rounds": dict(additional_rounds=0),
            "negative additional rounds": dict(additional_rounds=-1),
            "empty authorization": dict(authorization=""),
            "wrong expected round": dict(expected_round=1),
            "wrong state digest": dict(expected_state_sha256="0" * 64),
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                result = self.raw_grant(**overrides)
                self.assert_continuation_refused_without_write(
                    result, state_path, baseline)

        granted = self.grant(additional_rounds=2, expected_round=2,
                             expected_state_sha256=sha256_path(state_path))
        self.assertEqual(granted["status"], "ok", granted)
        reopened_bytes = state_path.read_bytes()
        repeated = self.raw_grant(additional_rounds=2, expected_round=2,
                                  expected_state_sha256=sha256_path(state_path))
        self.assert_continuation_refused_without_write(
            repeated, state_path, reopened_bytes)
        self.assertEqual(
            len(self.load_state()["validator"]["continuation"]["grants"]), 1,
            self.load_state()["validator"])
        # A real round still needs the existing correction transition.
        invocation_file, invocation_sha = self.capture_invocation()
        before_correction = self.prepare_round(invocation_file, invocation_sha, 3)
        self.assertTrue(refused(before_correction), before_correction)
        self.assertEqual(state_path.read_bytes(), reopened_bytes)

        # A changed candidate render or source input is refused.
        render = self._fresh_env()
        render.terminal_two_rounds()
        render_state = render.prof_dir / STAGE3_STATE
        render_baseline = render_state.read_bytes()
        candidates = render.prof_dir / contact_state.CANDIDATES_MD
        candidates.write_bytes(candidates.read_bytes() + b"\nmanual drift\n")
        render_result = render.raw_grant(expected_state_sha256=sha256_path(render_state))
        self.assert_continuation_refused_without_write(
            render_result, render_state, render_baseline)

        source = self._fresh_env()
        source.terminal_two_rounds()
        source_state = source.prof_dir / STAGE3_STATE
        payload = json.loads((source.prof_dir / STAGE2_STATE).read_text(encoding="utf-8"))
        payload["directions"][0]["input_fingerprint"] = "changed-after-validation"
        (source.prof_dir / STAGE2_STATE).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        source_baseline = source_state.read_bytes()
        source_result = source.raw_grant(
            expected_state_sha256=sha256_path(source_state))
        self.assert_continuation_refused_without_write(
            source_result, source_state, source_baseline)

    def test_c_c_stage3_global_findings_and_untouched_scopes_survive_the_grant(self):
        self.render_two()
        first = self.write_validation("continuation-s3-global-1.json",
                                      [self.finding(GLOBAL_QUOTE)])
        recorded = self.record(first)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertEqual(sorted(recorded_scopes(recorded)),
                         ["direction:dir_A", "direction:dir_B"], recorded)
        self.submit_current(first, "continuation-s3-global-correct-1")

        second = self.write_validation("continuation-s3-global-2.json",
                                       [self.finding(GLOBAL_QUOTE)])
        terminal = self.record(second)
        self.assertEqual(terminal["round"], 2, terminal)
        self.assertTrue(terminal["terminal"], terminal)
        state = self.load_state()
        for direction_id in ("dir_A", "dir_B"):
            row = state["validator"]["results"][direction_id]
            self.assertEqual(row["result"], "fail_after_2_rounds", row)
            self.assertEqual([issue["quote"] for issue in row["issues"]],
                             [GLOBAL_QUOTE], row)
        candidates_before = copy.deepcopy(state["directions"])

        granted = self.grant(additional_rounds=2, expected_round=2,
                             expected_state_sha256=sha256_path(
                                 self.prof_dir / STAGE3_STATE))
        self.assertEqual(granted["status"], "ok", granted)
        state = self.load_state()
        pending = state["validator"]["pending"]
        self.assertEqual(sorted(pending), ["direction:dir_A", "direction:dir_B"],
                         pending)
        for key in pending:
            self.assertEqual([issue["quote"] for issue in pending[key]["issues"]],
                             [GLOBAL_QUOTE], pending[key])
        self.assertEqual(state["directions"], candidates_before)

        planned = self.correction_plan(second)
        self.assertEqual(planned["status"], "ok", planned)
        self.assertEqual(planned["correction_scopes"],
                         ["direction:dir_A", "direction:dir_B"], planned)
        self.submit_current(second, "continuation-s3-global-correct-2")
        state = self.load_state()
        self.assertEqual(state["validator"]["pending"], {}, state["validator"])
        self.assertEqual(state["directions"], candidates_before)

    def test_c_d_stage3_new_cycle_starts_at_two_and_preserves_history(self):
        _first, second = self.terminal_two_rounds()
        invocation_file, invocation_sha = self.capture_invocation()
        granted = self.grant(additional_rounds=2, expected_round=2,
                             expected_state_sha256=sha256_path(
                                 self.prof_dir / STAGE3_STATE))
        self.assertEqual(granted["status"], "ok", granted)
        self.correct(second, "候选 dir_B_2 改写", "候选 dir_B_2 二次改写",
                     "continuation-s3-cycle-correct")
        prepared = parse(self.prepare_round(invocation_file, invocation_sha, 3))
        self.assertEqual(prepared["status"], "ok", prepared)
        third, _third_path = self.handoff_record(prepared, [])
        self.assertEqual(third["round"], 3, third)
        self.assertTrue(third["terminal"], third)
        before = self.load_state()
        self.assertEqual(before["validator"]["round"], 3, before["validator"])

        # A no-op rerender of an unchanged direction must not reset the count.
        noop = self.stage3_finalize(self.results_dir, "--direction-id", "dir_B")
        self.assertEqual(noop["status"], "ok", noop)
        self.assertIn("dir_B", noop["reused"], noop)
        after_noop = self.load_state()
        self.assertEqual(after_noop["validator"]["round"], 3, after_noop["validator"])
        self.assertEqual(after_noop["validator"].get("continuation"),
                         before["validator"].get("continuation"), after_noop["validator"])

        # A real new generation replaces the cycle: default two, no inherited grants.
        pack_path = self.prof_dir / STAGE2_STATE
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        for direction in payload["directions"]:
            if direction["direction_id"] == "dir_B":
                direction["input_fingerprint"] = "new-generation"
        pack_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        fresh = self.results("continuation-s3-new-cycle", {
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        generated = self.stage3_finalize(fresh, "--direction-id", "dir_B")
        self.assertEqual(generated["status"], "ok", generated)
        state = self.load_state()
        validator = state.get("validator") or {}
        self.assertFalse((validator.get("continuation") or {}).get("grants"),
                         validator)
        self.assertIn(validator.get("round_limit", 2), (None, 2), validator)
        self.assertNotIn("dir_B", validator.get("results") or {}, validator)

        retained = state.get("validation_history")
        self.assertIsInstance(retained, list, state)
        self.assertTrue(retained, state)
        snapshot = retained[-1]
        self.assertEqual(snapshot.get("round"), 3, snapshot)
        self.assertEqual(snapshot["continuation"]["grants"][0]["authorization"],
                         NOTE, snapshot)
        labels = [row.get("result")
                  for record in snapshot.get("history") or []
                  for row in (record.get("results") or {}).values()]
        self.assertIn("fail_after_2_rounds", labels, snapshot.get("history"))

    def _fresh_env(self):
        env = self.__class__(self._testMethodName)
        env.setUp()
        self.addCleanup(env.tearDown)
        return env


def recorded_scopes(recorded):
    return [row["scope"] for row in recorded.get("scopes") or []]
