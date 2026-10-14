"""Published narrative examples must pass the runner's existing output gate."""

import copy
import json
from pathlib import Path

from test_contact_state import BaseEnv, parse, run_cli
from stage2_upstream_fixture import run_bound_stage2_finalize


REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLE_FIELDS = ("concrete_object", "input_example", "output_example")


class NarrativeExampleContractTests(BaseEnv):
    def check_example(self, example, facts):
        results = self.root / "results"
        self.write_stage2_results(results)
        path = results / "narrative.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        entry = copy.deepcopy(example["directions"][0])
        original = fixture["directions"][0]
        entry.pop("direction_id", None)
        entry["collection_key"] = original["collection_key"]
        entry["gap_notes"] = original["gap_notes"]
        for block in entry["positioning"]:
            # Bind illustrative references to real synthetic fixture IDs;
            # preserve the published example fields for product validation.
            block["kind"] = "para"
            block["text"] = original["positioning"][0]["text"]
            block["refs"] = original["positioning"][0]["refs"]
        fixture["directions"] = [entry]
        path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
        outcome = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(outcome["status"], "ok", outcome)
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        saved = pack["directions"][0]["narrative"]["positioning"][0]
        for field in EXAMPLE_FIELDS:
            self.assertEqual(saved[field], entry["positioning"][0][field].strip())

    def check_projection(self, runtime):
        path = (REPO_ROOT / "packages" / f"professor-contact-{runtime}"
                / ".apm" / "agents" / "professor-contact-analyzer.agent.md")
        section = path.read_text(encoding="utf-8").split("`narrative:<教授>:<方向>`", 1)[1]
        example = json.loads(section.split("```json", 1)[1].split("```", 1)[0])
        facts = self.write_facts()
        plan = parse(self.run_bound_stage2_plan(facts))
        self.assertEqual(plan["status"], "ok", plan)
        self.check_example(example, facts)

    def test_codex_example_passes_finalize(self):
        self.check_projection("codex")

    def test_opencode_example_passes_finalize(self):
        self.check_projection("opencode")

    def test_plan_example_passes_finalize(self):
        facts = self.write_facts()
        plan = parse(self.run_bound_stage2_plan(facts))
        self.assertEqual(plan["status"], "ok", plan)
        job = next(job for job in plan["jobs"] if job["kind"] == "narrative")
        self.check_example(job["result_schema"], facts)
