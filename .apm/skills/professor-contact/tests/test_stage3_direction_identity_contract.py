"""Issue #8 canonical direction identity regression tests.

These tests intentionally keep Zotero/projection collection metadata separate
from the authoritative resolved direction identity. A projection-only
collection_key change must not invalidate Stage 3 model state.
"""
import json

from test_stage3_direction_groups import Stage3DirectionGroupBase


class Stage3DirectionIdentityContractTests(Stage3DirectionGroupBase):

    def test_collection_key_projection_change_reuses_same_direction_id(self):
        """Changing only collection_key must not regenerate the same direction.

        Issue #8 defines resolved direction_id as the machine/cache identity;
        collection_key is legacy/projection metadata only. Keep the Stage 2
        direction fingerprint and resolved_direction_id unchanged, rename only
        collection_key, and require Stage 3 to reuse the accepted idea state.
        """
        results = self.write_results("s3-identity", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None]),
        })
        first = self.stage3_finalize(results)
        self.assertEqual(first["status"], "ok", msg=json.dumps(first, ensure_ascii=False))

        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        direction_a = next(
            d for d in pack["directions"]
            if d["resolved_direction"]["resolved_direction_id"] == "dir_A")
        original_fingerprint = direction_a["input_fingerprint"]
        direction_a["collection_key"] = "zotero_projection_A_renamed"
        self.assertEqual(direction_a["resolved_direction"]["resolved_direction_id"], "dir_A")
        self.assertEqual(direction_a["input_fingerprint"], original_fingerprint)
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

        plan = self.stage3_plan()
        self.assertEqual(plan["status"], "ok", msg=json.dumps(plan, ensure_ascii=False))
        by_direction_id = {d["direction_id"]: d for d in plan["directions"]}
        self.assertEqual(by_direction_id["dir_A"]["action"], "reuse")
        self.assertNotIn("dir_A", [job["direction_id"] for job in plan["jobs"]])
