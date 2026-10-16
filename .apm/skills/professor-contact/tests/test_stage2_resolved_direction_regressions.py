"""Regression tests for Stage 2 resolved-direction candidate detection and reuse."""
import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"
SPEC = importlib.util.spec_from_file_location("contact_state", SCRIPT)
contact_state = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(contact_state)

# Shared formal-CLI helpers of the resolved-direction pipeline. Imported after
# the direct product-script load above to keep the existing import order.
from test_stage2_resolved_direction import (  # noqa: E402
    ResolvedPipelineMixin,
    finalize_resolve,
    new_resolve_results_dir,
    parse,
    plan_resolve,
    resolve_result,
    run_cli,
    write_json,
    write_resolve_results,
)


def _file_bytes_or_none(path):
    """Exact bytes of an authoritative file, or None when it does not exist."""
    path = Path(path)
    return path.read_bytes() if path.is_file() else None


def _sidecar_entries(sidecar_path):
    """provisional_direction_id -> entry of `_resolved_directions.json`."""
    payload = json.loads(Path(sidecar_path).read_text(encoding="utf-8"))
    return {row["provisional_direction_id"]: row for row in payload["directions"]}


class DummyContext:
    def __init__(self, direction_plans, papers=None):
        self.direction_plans = direction_plans
        self.papers = papers or {}

    def facts_for(self, key):
        # Minimal stand-in: no full-text facts available for any paper.
        return None, "unavailable", "missing_facts_sidecar"


class ResolvedDirectionRegressionTests(ResolvedPipelineMixin, unittest.TestCase):
    """Deterministic candidate rules plus the per-round resolve CLI contract.

    The candidate methods drive the internal helpers directly; the round
    isolation method drives the formal `stage2-resolve-plan` /
    `stage2-resolve-finalize` commands.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_addition_candidate_targets_strongest_non_provisional_direction(self):
        """A cross-cluster addition must point at the direction full-text evidence favors."""
        ctx = DummyContext([
            {
                "did": "dir_A",
                "direction": {
                    "member_keys": ["P1"],
                    "relevant_keys": ["P1"],
                    "provisional_member_keys": [],
                },
            },
            {
                "did": "dir_B",
                "direction": {
                    "member_keys": ["P1"],
                    "relevant_keys": ["P1"],
                    "provisional_member_keys": ["P1"],
                },
            },
        ])
        affinity = {"P1": {"dir_A": 3.5, "dir_B": 1.0}}

        additions = contact_state._detect_candidates_for_addition(ctx, affinity)

        self.assertEqual(len(additions), 1)
        self.assertEqual(additions[0]["item_key"], "P1")
        self.assertEqual(additions[0]["target_direction"], "dir_A")

    def test_merge_candidate_requires_at_least_two_shared_papers(self):
        """One shared paper is insufficient under the documented merge contract."""
        ctx = DummyContext([
            {
                "did": "dir_A",
                "direction": {
                    "name_ja": "信号処理",
                    "name_zh": "信号处理",
                    "summary_zh": "自适应信号处理与传感网络",
                    "member_keys": ["P1", "P2"],
                    "relevant_keys": ["P1", "P2"],
                },
            },
            {
                "did": "dir_B",
                "direction": {
                    "name_ja": "信号処理研究",
                    "name_zh": "信号处理研究",
                    "summary_zh": "自适应信号处理与传感网络",
                    "member_keys": ["P1", "P3"],
                    "relevant_keys": ["P1", "P3"],
                },
            },
        ])

        merges = contact_state._detect_merge_candidates(ctx)

        self.assertEqual(merges, [])

    def test_reused_direction_ignores_stale_result_file(self):
        """A cached direction must not be re-applied from a stale result file when no job was emitted."""
        direction = {
            "collection_key": "dir_A",
            "name_ja": "信号処理",
            "name_zh": "信号处理",
            "summary_zh": "信号処理の研究",
            "status": "active",
            "member_keys": ["P1"],
            "relevant_keys": ["P1"],
            "provisional_member_keys": ["P1"],
            "named_keys": [],
            "user_note": "",
        }
        papers = {
            "P1": {
                "item_key": "P1",
                "title": "Adaptive Signal Processing",
                "year": 2024,
                "month": 1,
                "authorship": "corresponding",
                "abstract": "signal processing",
                "has_pdf": False,
            }
        }
        ctx = DummyContext([{"did": "dir_A", "direction": direction, "pool": []}], papers)
        evidence = contact_state._resolve_evidence(ctx)
        fingerprint = contact_state._current_resolve_fingerprint(
            ctx, {"did": "dir_A", "direction": direction, "pool": []}, evidence)
        prior = {
            "resolved_direction_id": "dir_A",
            "provisional_direction_id": "dir_A",
            "name_ja": "信号処理",
            "name_zh": "信号处理",
            "resolution_type": "unchanged",
            "papers_to_add": [],
            "papers_to_remove": [],
            "paper_justifications": {},
            "split_target": None,
            "merge_target": None,
            "user_note": "",
            "input_fingerprint": fingerprint,
            "reused": False,
        }

        with tempfile.TemporaryDirectory() as td:
            results_dir = Path(td)
            # Simulate a fixed /tmp results directory retaining an old result from a
            # previous run. stage2-resolve-plan would emit no job for dir_A because
            # the cached fingerprint matches, so this file must be ignored.
            (results_dir / "resolve-dir_A.json").write_text(json.dumps({
                "schema": 1,
                "kind": "resolve",
                "collection_key": "dir_A",
                "resolved": {
                    "resolved_direction_id": "dir_A",
                    "provisional_direction_id": "dir_A",
                    "name_ja": "古い名前",
                    "name_zh": "旧名称",
                    "resolution_type": "renamed",
                    "papers_to_add": [],
                    "papers_to_remove": [],
                    "paper_justifications": {},
                    "split_target": None,
                    "merge_target": None,
                    "user_note": "",
                },
            }, ensure_ascii=False), encoding="utf-8")

            resolved = contact_state.validate_resolve_results(
                ctx, results_dir, reused={"dir_A": prior})

        self.assertEqual(resolved["dir_A"]["resolution_type"], "unchanged")
        self.assertTrue(resolved["dir_A"].get("reused"))
        self.assertEqual(resolved["dir_A"]["name_ja"], "信号処理")

    def test_resolve_run_isolation_and_missing_results(self):
        """One resolve round = one results directory and one round identity.

        A direction that still needs a model result must never be finalized
        from a missing file (the old default was a silently accepted
        "unchanged") nor from a copy of a previous round's file. Every such
        failure leaves the whole batch unwritten; only this round's complete
        file succeeds, after which the accepted direction is reused without a
        new job and ignores leftover files.
        """
        ckey = "dir_A"
        paper = self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"],
                                ["Future work A."])
        facts_path = self.write_facts(
            [paper],
            [self.make_direction(ckey, ["P1"], name_ja="Signal Processing",
                                 name_zh="信号处理", summary="signal processing")],
        )
        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        pack_path = self.prof_dir / "套磁候选输入.json"

        # --- Round 1: the direction really needs a new result. The model file
        # is written with this round's identity, but the round is never
        # finalized (an interrupted run that is planned again). ---
        round_one = new_resolve_results_dir(self.root)
        first_plan = plan_resolve(facts_path, round_one)
        self.assertEqual(first_plan["status"], "ok", msg=json.dumps(first_plan, ensure_ascii=False))
        self.assertIsInstance(first_plan.get("resolve_run_id"), str)
        self.assertTrue(first_plan["resolve_run_id"])
        first_jobs = [job for job in first_plan["jobs"] if job["direction_id"] == ckey]
        self.assertEqual(len(first_jobs), 1, msg=json.dumps(first_plan, ensure_ascii=False))
        self.assertEqual(first_jobs[0]["result_file"], "resolve-dir_A.json")
        # The round identity the model must echo back is part of the job schema.
        self.assertIn("resolve_run_id", json.dumps(first_jobs[0]["result_schema"]))
        first_actions = {row["direction_id"]: row["action"] for row in first_plan["directions"]}
        self.assertEqual(first_actions[ckey], "process")
        result_file = first_jobs[0]["result_file"]
        first_written = write_resolve_results(round_one, first_plan, {}, facts_path)
        self.assertTrue(Path(first_written[ckey]).is_file())
        self.assertFalse(sidecar_path.exists(),
                         "round 1 was deliberately left unfinalized")

        # --- Round 2: same facts, a NEW directory, still a required result. ---
        round_two = new_resolve_results_dir(self.root)
        second_plan = plan_resolve(facts_path, round_two)
        self.assertEqual(second_plan["status"], "ok", msg=json.dumps(second_plan, ensure_ascii=False))
        second_jobs = [job for job in second_plan["jobs"] if job["direction_id"] == ckey]
        self.assertEqual(len(second_jobs), 1,
                         "round 1 was never accepted, so this round still needs a result")
        self.assertEqual(second_jobs[0]["result_file"], result_file)

        # Nothing written into round 2: the batch fails as a whole.
        sidecar_before = _file_bytes_or_none(sidecar_path)
        pack_before = _file_bytes_or_none(pack_path)
        self.assertIsNone(sidecar_before)
        self.assertIsNone(pack_before)
        missing = finalize_resolve(facts_path, round_two)
        self.assertEqual(missing["status"], "error", msg=json.dumps(missing, ensure_ascii=False))
        self.assertEqual(missing["reason_code"], "result_missing")
        self.assertIn(str(round_two / result_file), missing["message"])
        self.assertEqual(_file_bytes_or_none(sidecar_path), sidecar_before)
        self.assertEqual(_file_bytes_or_none(pack_path), pack_before)

        # A copy of ROUND 1's file is the wrong round: still a whole-batch failure.
        (round_two / result_file).write_bytes((round_one / result_file).read_bytes())
        stale = finalize_resolve(facts_path, round_two)
        self.assertEqual(stale["status"], "error", msg=json.dumps(stale, ensure_ascii=False))
        self.assertEqual(stale["reason_code"], "invalid_result_json")
        self.assertEqual(_file_bytes_or_none(sidecar_path), sidecar_before)
        self.assertEqual(_file_bytes_or_none(pack_path), pack_before)

        # Completing the SAME round with this round's identity succeeds.
        write_resolve_results(round_two, second_plan, {}, facts_path)
        resolved = finalize_resolve(facts_path, round_two)
        self.assertEqual(resolved["status"], "ok", msg=json.dumps(resolved, ensure_ascii=False))
        self.assertFalse(resolved["needs_user_choice"])
        resolved_rows = {row["provisional_direction_id"]: row for row in resolved["directions"]}
        self.assertEqual(resolved_rows[ckey]["resolution_type"], "unchanged")
        accepted_entries = _sidecar_entries(sidecar_path)
        self.assertEqual(accepted_entries[ckey]["resolution_type"], "unchanged")
        self.assertEqual(accepted_entries[ckey]["acceptance"], "accepted")

        # --- Next round: the accepted direction is reused with no job, and a
        # leftover file from an earlier round is ignored. ---
        reuse_round = new_resolve_results_dir(self.root)
        reuse_plan = plan_resolve(facts_path, reuse_round)
        self.assertEqual(reuse_plan["status"], "ok", msg=json.dumps(reuse_plan, ensure_ascii=False))
        reuse_actions = {row["direction_id"]: row["action"] for row in reuse_plan["directions"]}
        self.assertEqual(reuse_actions[ckey], "reuse")
        self.assertEqual([job for job in reuse_plan["jobs"] if job["direction_id"] == ckey], [])
        leftover = resolve_result(first_jobs[0], {
            "resolved_direction_id": ckey,
            "provisional_direction_id": ckey,
            "name_ja": "信号処理（古い結果）",
            "name_zh": "信号处理（旧结果）",
            "resolution_type": "renamed",
            "papers_to_add": [],
            "papers_to_remove": [],
            "paper_justifications": {},
            "split_target": None,
            "merge_target": None,
            "user_note": "",
        }, first_plan["resolve_run_id"])
        write_json(reuse_round / result_file, leftover)
        reuse_payload = finalize_resolve(facts_path, reuse_round)
        self.assertEqual(reuse_payload["status"], "ok",
                         msg=json.dumps(reuse_payload, ensure_ascii=False))
        reused_entries = _sidecar_entries(sidecar_path)
        self.assertEqual(reused_entries[ckey]["resolution_type"], "unchanged")
        self.assertEqual(reused_entries[ckey]["acceptance"], "accepted")
        self.assertEqual(reused_entries[ckey]["resolved_direction_id"], ckey)
        self.assertFalse(reuse_payload["needs_user_choice"])

    def test_keep_provisional_exempts_only_the_named_direction(self):
        """An explicit --keep-provisional covers the direction it names only.

        Two directions both need this round's result. Naming dir_A in
        --keep-provisional must not let the batch pass while dir_B's file is
        missing, and nothing may be written by the rejected batch. Completing
        dir_B's file in the same round then succeeds; dir_A needs no model file
        and is persisted as the user's explicit keep decision.
        """
        facts_path = self.write_facts(
            [
                self.make_paper("A1", "Signal Baseline", ["signal", "processing"], ["Future A1."]),
                self.make_paper("B1", "Control Baseline", ["control", "robust"], ["Future B1."]),
            ],
            [
                self.make_direction("dir_A", ["A1"], name_ja="Signal Processing",
                                    name_zh="信号处理", summary="signal processing"),
                self.make_direction("dir_B", ["B1"], name_ja="Robust Control",
                                    name_zh="鲁棒控制", summary="robust control"),
            ],
        )
        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        pack_path = self.prof_dir / "套磁候选输入.json"

        keep_round = new_resolve_results_dir(self.root)
        plan_payload = plan_resolve(facts_path, keep_round)
        self.assertEqual(plan_payload["status"], "ok", msg=json.dumps(plan_payload, ensure_ascii=False))
        file_by_ckey = {job["direction_id"]: job["result_file"] for job in plan_payload["jobs"]}
        self.assertEqual(set(file_by_ckey), {"dir_A", "dir_B"})

        # No model file at all: only dir_A is explicitly kept provisional, so
        # dir_B must still fail the batch and dir_A's decision stays unwritten.
        missing = parse(run_cli(
            "stage2-resolve-finalize",
            "--facts", str(facts_path),
            "--results", str(keep_round),
            "--keep-provisional", "dir_A",
        ))
        self.assertEqual(missing["status"], "error", msg=json.dumps(missing, ensure_ascii=False))
        self.assertEqual(missing["reason_code"], "result_missing")
        self.assertIn(str(keep_round / file_by_ckey["dir_B"]), missing["message"])
        self.assertFalse(sidecar_path.exists(),
                         "a rejected batch must not persist the keep-provisional decision")
        self.assertFalse(pack_path.exists())

        # Completing dir_B's result in the SAME round succeeds: dir_A is
        # covered by the user's explicit decision, not by a default.
        write_resolve_results(keep_round, plan_payload, {}, facts_path, skip=("dir_A",))
        self.assertFalse((keep_round / file_by_ckey["dir_A"]).exists())
        kept = parse(run_cli(
            "stage2-resolve-finalize",
            "--facts", str(facts_path),
            "--results", str(keep_round),
            "--keep-provisional", "dir_A",
        ))
        self.assertEqual(kept["status"], "ok", msg=json.dumps(kept, ensure_ascii=False))
        kept_rows = {row["provisional_direction_id"]: row for row in kept["directions"]}
        self.assertEqual(kept_rows["dir_A"]["resolution_type"], "unchanged")
        self.assertEqual(kept_rows["dir_A"]["decision"], "user_kept_provisional")
        entries = _sidecar_entries(sidecar_path)
        self.assertEqual(entries["dir_A"]["resolution_type"], "unchanged")
        self.assertEqual(entries["dir_A"]["decision"], "user_kept_provisional")
        self.assertEqual(entries["dir_A"]["acceptance"], "accepted")
        self.assertEqual(entries["dir_B"]["acceptance"], "accepted")
        self.assertFalse(kept["needs_user_choice"])


if __name__ == "__main__":
    unittest.main()
