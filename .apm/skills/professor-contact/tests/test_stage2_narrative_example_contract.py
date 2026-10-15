"""校验公开的叙事示例及其第二阶段运行器输入。"""

import copy
import json
import re
from pathlib import Path

from test_contact_state import BaseEnv, parse, run_cli
from stage2_upstream_fixture import run_bound_stage2_finalize


REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLE_FIELDS = ("concrete_object", "input_example", "output_example")
REFERENCE_TYPES = {"P": "paper", "L": "later", "G": "gap"}
PLACEHOLDER_PATTERN = re.compile(r"\{\{([PLG]):([^{}]+)\}\}")


class NarrativeExampleContractTests(BaseEnv):
    def assert_example_contract(self, example):
        directions = example.get("directions", [])
        self.assertTrue(directions, "叙事示例必须包含方向")
        for direction in directions:
            for block in direction.get("positioning", []):
                placeholders = {
                    (REFERENCE_TYPES[prefix], identifier)
                    for prefix, identifier in PLACEHOLDER_PATTERN.findall(block.get("text", ""))
                }
                refs = block.get("refs", [])
                self.assertIsInstance(refs, list, f"refs 必须是列表：{refs!r}")
                self.assertTrue(
                    all(isinstance(ref, str) and ":" in ref for ref in refs),
                    f"refs 必须使用类型:标识格式：{refs!r}",
                )
                self.assertEqual(len(refs), len(set(refs)), f"refs 不得重复：{refs!r}")
                actual = {tuple(ref.split(":", 1)) for ref in refs}
                self.assertEqual(placeholders, actual, f"text 与 refs 不一致：{block!r}")

    def bind_example(self, example, model_input):
        papers = model_input.get("papers", [])
        gaps = model_input.get("gaps", [])
        self.assertTrue(papers, "叙事任务输入必须提供合成论文")
        self.assertTrue(gaps, "叙事任务输入必须提供合成研究缺口")
        identifiers = {
            "paper": papers[0]["item_key"],
            "gap": gaps[0]["gap_id"],
        }
        later_papers = model_input.get("later_papers", [])
        if any(
            prefix == "L"
            for direction in example.get("directions", [])
            for block in direction.get("positioning", [])
            for prefix, _ in PLACEHOLDER_PATTERN.findall(block.get("text", ""))
        ) or any(
            ref.startswith("later:")
            for direction in example.get("directions", [])
            for block in direction.get("positioning", [])
            for ref in block.get("refs", [])
        ):
            self.assertTrue(later_papers, "含 `later` 引用的示例必须有合法的 `later_papers`")
            identifiers["later"] = later_papers[0]["item_key"]

        entry = copy.deepcopy(example["directions"][0])
        direction_id = model_input["direction_id"]
        if "direction_id" in entry:
            entry["direction_id"] = direction_id
        elif "collection_key" in entry:
            entry["collection_key"] = direction_id
        else:
            self.fail("叙事示例必须含 direction_id 或 collection_key")

        for block in entry.get("positioning", []):
            if block.get("kind") == "para|bullet":
                block["kind"] = "para"

            def bind_placeholder(match):
                prefix, _ = match.groups()
                return "{{" + prefix + ":" + identifiers[REFERENCE_TYPES[prefix]] + "}}"

            block["text"] = PLACEHOLDER_PATTERN.sub(bind_placeholder, block["text"])
            bound_refs = []
            for ref in block.get("refs", []):
                ref_type, separator, identifier = ref.partition(":")
                if separator and identifier in {"ITEMKEY", "GAPID"}:
                    bound_refs.append(f"{ref_type}:{identifiers[ref_type]}")
                else:
                    bound_refs.append(ref)
            block["refs"] = bound_refs

        for note in entry.get("gap_notes", []):
            note["gap_id"] = identifiers["gap"]
        return entry

    def check_example(self, example, facts, model_input):
        self.assert_example_contract(example)
        entry = self.bind_example(example, model_input)
        results = self.root / "results"
        self.write_stage2_results(results)
        path = results / "narrative.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        fixture["directions"] = [entry]
        path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")

        outcome = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(outcome["status"], "ok", outcome)
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        saved = pack["directions"][0]["narrative"]["positioning"][0]
        expected = entry["positioning"][0]
        self.assertEqual(saved["text"], expected["text"])
        self.assertEqual(saved["refs"], expected["refs"])
        for field in EXAMPLE_FIELDS:
            self.assertEqual(saved[field], expected[field].strip())

    def stage2_plan(self, facts):
        plan = parse(self.run_bound_stage2_plan(facts))
        self.assertEqual(plan["status"], "ok", plan)
        job = next(job for job in plan["jobs"] if job["kind"] == "narrative")
        return plan, job

    def projection_example(self, runtime):
        path = (
            REPO_ROOT
            / "packages"
            / f"professor-contact-{runtime}"
            / ".apm"
            / "agents"
            / "professor-contact-analyzer.agent.md"
        )
        section = path.read_text(encoding="utf-8").split("`narrative:<教授>:<方向>`", 1)[1]
        return json.loads(section.split("```json", 1)[1].split("```", 1)[0])

    def test_reference_contract_rejects_mismatches(self):
        valid = {
            "directions": [
                {
                    "positioning": [
                        {
                            "text": "{{P:ITEMKEY}} 与 {{G:GAPID}}",
                            "refs": ["paper:ITEMKEY", "gap:GAPID"],
                        }
                    ]
                }
            ]
        }
        extra_ref = copy.deepcopy(valid)
        extra_ref["directions"][0]["positioning"][0]["refs"].append("later:ITEMKEY")
        missing_ref = copy.deepcopy(valid)
        missing_ref["directions"][0]["positioning"][0]["refs"].remove("gap:GAPID")

        with self.assertRaises(AssertionError):
            self.assert_example_contract(extra_ref)
        with self.assertRaises(AssertionError):
            self.assert_example_contract(missing_ref)

    def test_codex_example_passes_finalize(self):
        example = self.projection_example("codex")
        facts = self.write_facts()
        _, job = self.stage2_plan(facts)
        self.check_example(example, facts, job["model_input"])

    def test_opencode_example_passes_finalize(self):
        example = self.projection_example("opencode")
        facts = self.write_facts()
        _, job = self.stage2_plan(facts)
        self.check_example(example, facts, job["model_input"])

    def test_plan_example_passes_finalize(self):
        facts = self.write_facts()
        _, job = self.stage2_plan(facts)
        self.check_example(job["result_schema"], facts, job["model_input"])
