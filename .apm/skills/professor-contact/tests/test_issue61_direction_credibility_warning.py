"""Issue #61 regression: the direction credibility warning must be plain-language safe.

Stage 3 renders the 勉强 / 疑似幻觉 warning into 套磁想法候选.md **before**
professor-contact-style-validator reads that file, so the deterministic line is
part of the validated input.  An internal execution parameter such as
``force:true`` inside it makes an otherwise clean artifact fail the
plain-language gate.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import (
    ResolvedPipelineMixin, parse, quote_id, run_cli, write_json)

_SCRIPT = Path(__file__).parents[1] / "scripts" / "contact_state.py"
_spec = importlib.util.spec_from_file_location("contact_state_issue61", _SCRIPT)
contact_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contact_state)

PROFESSOR = "試験 教授"
QUOTE = "Future work will extend the shared method to streaming inputs."
# Verdicts that must keep showing the warning (issue #61 acceptance 1).
FLAGGED_VERDICTS = ["勉强", "疑似幻觉"]
# Verdicts that must keep showing no warning.
CLEAN_VERDICTS = ["站得住", "未判定"]


class DirectionCredibilityWarningTests(ResolvedPipelineMixin, unittest.TestCase):
    """Render the real Stage 3 artifact for one direction per verdict."""

    professor = PROFESSOR

    def candidate(self, cid):
        return {
            "id": cid, "kind": "direction", "direction_ids": ["dir_A"],
            "origin": "generated", "title": f"候选 {cid}",
            "one_liner": "教授的工作启发我思考延伸方向",
            "research_question": "该方法在流式输入下是否保持相同表现？",
            "points": ["挂在作者写明的延伸点上"],
            "gap_refs": [{"direction_id": "dir_A", "item_key": "P1",
                          "gap_id": quote_id(QUOTE)}],
            "papers": [{"item_key": "P1", "direction_ids": ["dir_A"],
                        "role": "基座", "fit_note": "教授通讯"}],
            "fit": "high", "fit_note": "", "red_lines": [],
            "why_recommended": "兴趣契合", "tension_points": [],
        }

    def render_candidates_md(self, verdict):
        """Run stage 1→2→3 for a single direction with the given credibility verdict."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / self.professor
        (self.prof_dir / "论文分析").mkdir(parents=True)
        paper = self.make_paper("P1", "Shared Method Paper", ["method", "shared"], [QUOTE])
        direction = self.make_direction("dir_A", ["P1"], name_ja="信号処理",
                                        name_zh="信号处理", summary="信号处理方向")
        direction["credibility"] = {
            "verdict": verdict, "mainline": "未判定",
            "authorship_line": "corresponding_dominant", "note": "",
        }
        facts_path = self.write_facts([paper], [direction])
        self.run_resolve(facts_path, {})
        stage2 = self.run_stage2_finalize(facts_path)
        self.assertEqual(stage2["status"], "ok", msg=json.dumps(stage2, ensure_ascii=False))

        results = self.root / "stage3_results"
        results.mkdir(parents=True)
        write_json(results / contact_state.safe_result_file("candidates", "dir_A"), {
            "schema": 2, "kind": "candidates", "direction_id": "dir_A",
            "mode": "generated", "priority": "主推 1",
            "candidates": [self.candidate(f"dir_A_{n}") for n in range(1, 4)],
        })
        stage3 = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                               "--results", results, "--program-root", self.root))
        self.assertEqual(stage3["status"], "ok", msg=json.dumps(stage3, ensure_ascii=False))
        return self.prof_dir

    def direction_header_lines(self, professor_dir):
        """Quote lines the renderer emits between the direction heading and its
        first candidate block — where the credibility warning must live."""
        body = (professor_dir / "套磁想法候选.md").read_text(encoding="utf-8")
        lines = body.splitlines()
        try:
            heading = next(i for i, line in enumerate(lines) if line.startswith("## 信号処理"))
        except StopIteration:
            raise AssertionError(f"direction heading missing from render:\n{body}")
        header = []
        for line in lines[heading + 1:]:
            if line.startswith("## ") or line.startswith("### "):
                break
            header.append(line)
        return header, body

    def warning_lines(self, verdict):
        professor_dir = self.render_candidates_md(verdict)
        header, body = self.direction_header_lines(professor_dir)
        warnings = [line for line in header if line.startswith("> ⚠️")]
        return professor_dir, header, body, warnings

    # -- acceptance 1: the warning stays visible under the direction section --

    def test_flagged_verdicts_render_one_visible_warning(self):
        for verdict in FLAGGED_VERDICTS:
            with self.subTest(verdict=verdict):
                _, header, body, warnings = self.warning_lines(verdict)
                self.assertEqual(len(warnings), 1,
                                 msg=f"verdict {verdict} lost its warning:\n" + "\n".join(header))
                self.assertTrue(warnings[0][len("> ⚠️"):].strip(),
                                msg=f"empty warning text:\n{body}")

    def test_clean_verdicts_render_no_warning(self):
        for verdict in CLEAN_VERDICTS:
            with self.subTest(verdict=verdict):
                _, _, _, warnings = self.warning_lines(verdict)
                self.assertEqual(warnings, [], msg=f"verdict {verdict} must not warn")

    # -- acceptance 2 regression: the concrete force:true parameter leak is gone --

    def test_warning_does_not_leak_force_parameter(self):
        for verdict in FLAGGED_VERDICTS:
            with self.subTest(verdict=verdict):
                _, _, _, warnings = self.warning_lines(verdict)
                self.assertEqual(len(warnings), 1, msg="warning disappeared from the render")
                text = warnings[0]
                compact = "".join(text.lower().split())
                self.assertNotIn("force:true", compact,
                                 msg=f"force execution parameter leaked into the warning: {text}")

    # -- acceptance 3/4: the warning ships inside the render the validator binds to --

    def test_warning_is_part_of_the_sha_bound_render(self):
        for verdict in FLAGGED_VERDICTS:
            with self.subTest(verdict=verdict):
                professor_dir, _, _, warnings = self.warning_lines(verdict)
                self.assertEqual(len(warnings), 1, msg="warning disappeared from the render")
                state = json.loads((professor_dir / "套磁候选状态.json").read_text(encoding="utf-8"))
                bound_sha, bound_body = contact_state._stage3_bound_render(professor_dir, state)
                self.assertIn(warnings[0], bound_body.splitlines(),
                              msg="validator evidence is bound to a render without the warning")
                self.assertTrue(bound_sha)


if __name__ == "__main__":
    unittest.main()
