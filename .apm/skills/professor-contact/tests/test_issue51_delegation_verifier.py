"""Deterministic coverage for the issue #51 runtime verifier.

The verifier only consumes fixtures ``codex-eval-adapter@9`` output.  These
tests pin its mechanical mapping between adapter machine evidence and the
issue's verdict families (``pass`` / ``blocked`` / ``not_tested`` /
``invalid_evidence``): topology is judged from formal completed ``spawnAgent``
relations only, prose and identity diagnostics never create a PASS, and
corrupted evidence fails closed instead of passing or blaming the producer.
"""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
VERIFIER_PATH = TESTS_DIR / "runtime" / "verify_issue51_delegation.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load_module("issue51_delegation_verifier", VERIFIER_PATH)

ROOT = "thread-root"
L1 = "thread-stage1"
L2 = "thread-collector"
L3 = "thread-deep"


def relation(parent, *children, status="completed", tool="spawnAgent"):
    return {
        "tool": tool,
        "status": status,
        "parent_thread_id": parent,
        "receiver_thread_ids": list(children),
        "sender_thread_id": parent,
    }


def delegation(state="confirmed", children=(L1, L2), basis=None, reason=None):
    payload = {
        "state": state,
        "formal_child_count": len(children),
        "child_thread_ids": list(children),
        "basis": ["formal_spawn_relation"] if basis is None else basis,
        "reason_code": reason,
    }
    if reason is None:
        payload.pop("reason_code")
    return payload


def adapter(relations=None, delegation_payload=None, fixture_status="FIXTURE_READY"):
    return {
        "schema": 1,
        "role": "codex-eval-evidence",
        "fixture_status": fixture_status,
        "problems": [],
        "delegation": delegation_payload if delegation_payload is not None
        else delegation(children=()) if not relations else delegation(),
        "dispatch": {
            "expected_agents": [],
            "thread_relations": relations or [],
        },
    }


def chained_adapter(depth):
    """root -> l1 -> ... -> l{depth} chain of completed formal relations."""
    nodes = [ROOT] + [f"thread-l{index}" for index in range(1, depth + 1)]
    relations = [relation(parent, child) for parent, child in zip(nodes, nodes[1:])]
    return adapter(relations=relations, delegation_payload=delegation(children=tuple(nodes[1:])))


class Issue51VerifierTopologyTests(unittest.TestCase):
    def test_nested_chain_passes_with_depth_and_nested_edges(self):
        payload = verifier.evaluate(chained_adapter(2), "r1")
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["formal_spawn_relation_count"], 2)
        self.assertEqual(payload["nested_edge_count"], 1)
        self.assertEqual(payload["max_depth"], 2)
        self.assertEqual(payload["reason_code"], "")
        self.assertEqual(payload["case"], "r1")
        self.assertEqual(
            payload["proof_scope"],
            "repo-owned-coordinator-formal-nested-delegation-only")

    def test_deeper_chain_passes_and_counts_all_nested_edges(self):
        payload = verifier.evaluate(chained_adapter(3), "r2")
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["max_depth"], 3)
        self.assertEqual(payload["nested_edge_count"], 2)

    def test_flat_delegation_is_not_tested_never_pass(self):
        relations = [relation(ROOT, L1)]
        payload = verifier.evaluate(
            adapter(relations=relations, delegation_payload=delegation(children=(L1,))),
            "r1")
        self.assertEqual(payload["status"], "not_tested", payload)
        self.assertEqual(payload["reason_code"], "nested_formal_delegation_not_observed")
        self.assertEqual(payload["max_depth"], 1)
        self.assertEqual(payload["formal_spawn_relation_count"], 1)

    def test_confirmed_without_completed_relation_is_not_tested(self):
        relations = [relation(ROOT, L1, status="in-progress")]
        payload = verifier.evaluate(
            adapter(relations=relations, delegation_payload=delegation(children=(L1,))),
            "r1")
        self.assertEqual(payload["status"], "not_tested", payload)
        self.assertEqual(
            payload["reason_code"],
            "confirmed_delegation_without_completed_formal_relation")

    def test_assistant_prose_never_creates_delegation_evidence(self):
        noisy = adapter(relations=[], delegation_payload=delegation(
            state="unobservable", children=(),
            reason="no_supported_formal_spawn_relation"))
        noisy["assistant_prose"] = (
            "I delegated to professor-collector and it completed successfully.")
        payload = verifier.evaluate(noisy, "r2")
        self.assertEqual(payload["status"], "not_tested", payload)
        self.assertEqual(
            payload["reason_code"], "no_supported_formal_spawn_relation")

    def test_unobservable_delegation_is_not_tested_with_machine_reason(self):
        payload = verifier.evaluate(adapter(
            relations=[],
            delegation_payload=delegation(state="unobservable", children=(),
                                          reason="no_supported_formal_spawn_relation")),
            "r1")
        self.assertEqual(payload["status"], "not_tested", payload)
        self.assertEqual(payload["reason_code"], "no_supported_formal_spawn_relation")


class Issue51VerifierBlockerTests(unittest.TestCase):
    def test_blocked_dependency_is_blocked_not_failed(self):
        payload = adapter(fixture_status="BLOCKED_DEPENDENCY")
        payload["problems"] = ["eval service unreachable"]
        verdict = verifier.evaluate(payload, "r1")
        self.assertEqual(verdict["status"], "blocked", verdict)
        self.assertEqual(verdict["reason_code"], "adapter_blocked_dependency")

    def test_harness_dispatch_unconfirmed_does_not_downgrade_confirmed_topology(self):
        payload = chained_adapter(2)
        payload["fixture_status"] = "HARNESS_DISPATCH_UNCONFIRMED"
        verdict = verifier.evaluate(payload, "r2")
        self.assertEqual(verdict["status"], "pass", verdict)

    def test_harness_dispatch_mismatch_is_identity_diagnostic_only(self):
        payload = chained_adapter(2)
        payload["fixture_status"] = "HARNESS_DISPATCH_MISMATCH"
        payload["dispatch"]["agent_identity"] = {
            "diagnostic-role": {
                "requested_role": {
                    "state": "contradicted",
                    "value": "another-role",
                },
                "loaded_identity": {
                    "state": "unobservable",
                },
            },
        }
        verdict = verifier.evaluate(payload, "r2")
        self.assertEqual(verdict["status"], "pass", verdict)
        self.assertEqual(verdict["max_depth"], 2)
        self.assertEqual(verdict["nested_edge_count"], 1)


class Issue51VerifierInvalidEvidenceTests(unittest.TestCase):
    def test_adapter_invalid_evidence_status_fails_closed(self):
        payload = adapter(fixture_status="INVALID_EVIDENCE")
        payload["problems"] = ["corrupted app-server dispatch evidence"]
        verdict = verifier.evaluate(payload, "r1")
        self.assertEqual(verdict["status"], "invalid_evidence", verdict)
        self.assertEqual(verdict["reason_code"], "adapter_invalid_evidence")

    def test_completed_spawn_without_receivers_is_invalid_evidence(self):
        relations = [relation(ROOT, L1), relation(L1, status="completed")]
        payload = verifier.evaluate(
            adapter(relations=relations, delegation_payload=delegation(children=(L1, L2))),
            "r1")
        self.assertEqual(payload["status"], "invalid_evidence", payload)
        self.assertEqual(
            payload["reason_code"], "completed_spawn_without_concrete_receivers")

    def test_conflicting_formal_ownership_is_invalid_evidence(self):
        relations = [
            relation(ROOT, L1),
            relation("thread-other-parent", L1),
            relation(L1, L2),
        ]
        payload = verifier.evaluate(
            adapter(relations=relations, delegation_payload=delegation(children=(L1, L2))),
            "r1")
        self.assertEqual(payload["status"], "invalid_evidence", payload)
        self.assertEqual(payload["reason_code"], "conflicting_formal_ownership")

    def test_unobservable_summary_with_completed_relations_contradicts(self):
        relations = [relation(ROOT, L1), relation(L1, L2)]
        payload = verifier.evaluate(
            adapter(relations=relations,
                    delegation_payload=delegation(state="unobservable", children=(),
                                                  reason="no_supported_formal_spawn_relation")),
            "r1")
        self.assertEqual(payload["status"], "invalid_evidence", payload)
        self.assertEqual(
            payload["reason_code"], "delegation_summary_contradicts_relations")

    def test_confirmed_summary_missing_basis_is_inconsistent(self):
        relations = [relation(ROOT, L1), relation(L1, L2)]
        payload = verifier.evaluate(
            adapter(relations=relations,
                    delegation_payload=delegation(basis=[])),
            "r1")
        self.assertEqual(payload["status"], "invalid_evidence", payload)
        self.assertEqual(payload["reason_code"], "delegation_summary_inconsistent")

    def test_completed_child_missing_from_summary_is_inconsistent(self):
        relations = [relation(ROOT, L1), relation(L1, L2)]
        payload = verifier.evaluate(
            adapter(relations=relations,
                    delegation_payload=delegation(children=(L1,))),
            "r1")
        self.assertEqual(payload["status"], "invalid_evidence", payload)
        self.assertEqual(
            payload["reason_code"], "delegation_summary_missing_completed_child")

    def test_non_object_adapter_is_invalid_evidence(self):
        verdict = verifier.evaluate(["not", "an", "object"], "r1")
        self.assertEqual(verdict["status"], "invalid_evidence", verdict)
        self.assertEqual(verdict["reason_code"], "adapter_not_object")

    def test_missing_delegation_or_dispatch_is_malformed(self):
        payload = adapter(relations=[])
        del payload["delegation"]
        self.assertEqual(
            verifier.evaluate(payload, "r1")["reason_code"], "adapter_malformed")

        payload = adapter(relations=[])
        del payload["dispatch"]["thread_relations"]
        self.assertEqual(
            verifier.evaluate(payload, "r1")["reason_code"], "adapter_malformed")

    def test_unknown_delegation_state_is_malformed(self):
        payload = adapter(relations=[relation(ROOT, L1), relation(L1, L2)],
                          delegation_payload=delegation())
        payload["delegation"]["state"] = "guessed"
        self.assertEqual(
            verifier.evaluate(payload, "r1")["reason_code"], "adapter_malformed")

    def test_unknown_fixture_status_is_malformed(self):
        payload = adapter(fixture_status="SOMETHING_ELSE")
        self.assertEqual(
            verifier.evaluate(payload, "r1")["reason_code"],
            "adapter_unknown_fixture_status")


class Issue51VerifierCliTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)

    def _run(self, argv):
        # The CLI prints the verdict for eval-run logs; keep that out of the
        # unittest output while still exercising the real main().
        with contextlib.redirect_stdout(io.StringIO()):
            return verifier.main(argv)

    def test_cli_passes_on_nested_chain_and_writes_verdict_file(self):
        adapter_path = self.root / "r1-adapter.json"
        output_path = self.root / "r1-verdict.json"
        adapter_path.write_text(json.dumps(chained_adapter(2)), encoding="utf-8")
        exit_code = self._run([
            "--case", "r1", "--adapter", str(adapter_path), "--output", str(output_path)])
        self.assertEqual(exit_code, 0)
        verdict = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(verdict["status"], "pass")
        self.assertEqual(verdict["case"], "r1")

    def test_cli_fails_closed_on_not_tested_and_invalid_input(self):
        adapter_path = self.root / "r2-adapter.json"
        output_path = self.root / "r2-verdict.json"
        adapter_path.write_text("not json at all", encoding="utf-8")
        exit_code = self._run([
            "--case", "r2", "--adapter", str(adapter_path), "--output", str(output_path)])
        self.assertEqual(exit_code, 1)
        verdict = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(verdict["status"], "invalid_evidence")
        self.assertEqual(verdict["reason_code"], "adapter_unreadable")

        flat = self.root / "flat.json"
        flat.write_text(json.dumps(
            adapter(relations=[relation(ROOT, L1)],
                    delegation_payload=delegation(children=(L1,)))), encoding="utf-8")
        exit_code = self._run([
            "--case", "r1", "--adapter", str(flat), "--output", str(self.root / "flat-verdict.json")])
        self.assertEqual(exit_code, 1)

    def test_cli_rejects_unknown_case(self):
        with self.assertRaises(SystemExit):
            verifier._parser().parse_args([
                "--case", "r3", "--adapter", "x.json", "--output", "y.json"])


if __name__ == "__main__":
    unittest.main()
