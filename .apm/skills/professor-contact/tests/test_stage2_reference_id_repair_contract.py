"""Runtime batches 3/4 regression locks: reference IDs must be copied
verbatim from job payloads, and a rejected ``unknown_reference_id`` result
gets exactly one mechanical repair round.

Batch 3 (producer 1667315) failed PC40-R2 because the analyzer hand-typed a
63-hex gap id into ``freshness-DIR00001.json`` instead of copying the 64-hex
id from the job payload, then returned ``partial`` without repairing its own
transcription. These tests lock the producer contract that prevents both
halves of that failure in every analyzer projection.
"""

from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[4]
PROJECTIONS = (
    REPO_ROOT / "packages" / "professor-contact-codex" / ".apm" / "agents"
    / "professor-contact-analyzer.agent.md",
    REPO_ROOT / "packages" / "professor-contact-opencode" / ".apm" / "agents"
    / "professor-contact-analyzer.agent.md",
)


def _body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{path}: missing opening frontmatter delimiter")
    end = lines.index("---", 1)
    return "\n".join(lines[end + 1 :])


class ReferenceIdRepairContractTests(unittest.TestCase):
    def test_every_projection_documents_verbatim_id_copying(self):
        for path in PROJECTIONS:
            with self.subTest(projection=path.parents[2].name):
                body = _body(path)
                freshness = body[body.index("`freshness:<教授>:<方向>`"):]
                self.assertIn("引用 ID 一律逐字节复制", freshness)
                self.assertIn("model_input.gaps[].gap_id", freshness)
                self.assertIn("candidate_paper_ids", freshness)

    def test_every_projection_documents_the_unknown_reference_id_repair_round(self):
        for path in PROJECTIONS:
            with self.subTest(projection=path.parents[2].name):
                body = _body(path)
                self.assertIn("`unknown_reference_id` 修复轮", body)
                # The repair round is bounded: exactly one retry, then partial.
                self.assertRegex(
                    body, r"修复轮至多一次，仍被拒才返回 `partial/error`")
                # The repair round stays inside the model's own result file;
                # runner-owned artifacts are never hand-written.
                self.assertRegex(body, r"仍只由 runner 写，不构成手写兜底")

    def test_runner_division_rule_points_at_the_repair_round(self):
        for path in PROJECTIONS:
            with self.subTest(projection=path.parents[2].name):
                body = _body(path)
                division = body[body.index("**Runner 分工"):]
                division = division[: division.index("\n\n")]
                self.assertIn("唯一例外：`unknown_reference_id`", division)

    def test_sidecar_gap_ids_are_copied_verbatim(self):
        for path in PROJECTIONS:
            with self.subTest(projection=path.parents[2].name):
                body = _body(path)
                self.assertIn(
                    "将 valid sidecar items 的 `id` **逐字节复制**", body)


if __name__ == "__main__":
    unittest.main()
