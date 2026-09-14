import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
BUILDER_PATH = TESTS_DIR / "runtime/build_issue32_e2e_fixture.py"
VERIFIER_PATH = TESTS_DIR / "runtime/verify_issue32_e2e.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module("issue32_fixture_builder_for_verifier", BUILDER_PATH)
verifier = load_module("issue32_verifier", VERIFIER_PATH)


class Issue32VerifierTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name) / "program"
        self.profile = Path(self.holder.name) / "profile"
        builder.build_fixture(self.root, self.profile)

    def args(self, **overrides):
        values = {
            "program_root": self.root,
            "consumer_root": None,
            "eval_response": None,
            "adapter_output": None,
            "producer_sha": "",
            "output": None,
            "min_edges": 1,
            "required_depth": 1,
        }
        values.update(overrides)
        return Namespace(**values)

    def test_initial_checkpoint_is_pass_and_stage0_state_is_absent(self):
        payload = verifier._checkpoint_initial(self.args())
        self.assertEqual(payload["status"], "pass", payload)
        self.assertFalse((self.root / "教授研究/套磁目标.json").exists())

    def test_stage0_needs_input_requires_structured_selection_request(self):
        response = Path(self.holder.name) / "stage0.json"
        response.write_text(json.dumps({
            "selection_request": {"direction_ids": ["DIR00001"], "status": "needs_input"}
        }), encoding="utf-8")
        payload = verifier._checkpoint_stage0_needs_input(self.args(eval_response=response))
        self.assertEqual(payload["status"], "pass", payload)

        response.write_text("The model says it needs a selection.", encoding="utf-8")
        payload = verifier._checkpoint_stage0_needs_input(self.args(eval_response=response))
        self.assertEqual(payload["status"], "fail", payload)

    def test_make_stage4_selection_sorts_candidates_and_writes_only_requested_file(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        state = {"schema_version": 2, "directions": [{"direction_id": "DIR00001"}],
                 "candidates": [{"id": "zeta"}, {"id": "alpha"}, {"id": "beta"}]}
        (prof / "套磁候选状态.json").write_text(json.dumps(state), encoding="utf-8")
        output = Path(self.holder.name) / "selection.json"
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        payload = verifier._checkpoint_make_stage4_selection(self.args(output=output))
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["observed"]["selected_id"], "alpha")
        selected = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(selected["selection"][0]["ideas"][0]["id"], "alpha")
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        self.assertEqual(before, after)

    def test_runtime_graph_rejects_identity_only_and_accepts_formal_events(self):
        identity = Path(self.holder.name) / "identity.json"
        identity.write_text(json.dumps({"loaded_agents": ["professor-contact", "downloader"]}), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(self.args(adapter_output=identity))
        self.assertEqual(payload["status"], "fail", payload)

        events = Path(self.holder.name) / "events.json"
        events.write_text(json.dumps({"app_server_events": [
            {"event_type": "spawn_agent", "parent_id": "contact", "child_id": "downloader"},
            {"event_type": "spawn_agent", "parent_id": "downloader", "child_id": "analyzer"},
        ]}), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(
            self.args(adapter_output=events, min_edges=2, required_depth=2))
        self.assertEqual(payload["status"], "pass", payload)


if __name__ == "__main__":
    unittest.main()
