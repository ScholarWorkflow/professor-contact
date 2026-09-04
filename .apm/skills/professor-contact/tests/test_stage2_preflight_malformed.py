"""Fail-closed regressions for malformed Stage 2 preflight cache state.

Issue #11 requires miss / uncertain / legacy / malformed persisted state to
fall back to the existing Stage 2 slow path rather than becoming a new hard
failure in the optimization gate.
"""

import json

from test_stage2_preflight import PreflightBase


class TestPreflightMalformedState(PreflightBase):
    def test_truthy_non_dict_pack_cache_falls_back_to_process(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["cache"] = ["malformed"]
        self._write_pack(pack)

        payload = self.preflight()
        self.assertEqual(payload["status"], "ok", payload)
        self.assertEqual(payload["action"], "process", payload)

    def test_truthy_non_dict_preflight_directions_falls_back_to_process(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["cache"]["preflight"]["directions"] = ["malformed"]
        self._write_pack(pack)

        payload = self.preflight()
        self.assertEqual(payload["status"], "ok", payload)
        self.assertEqual(payload["action"], "process", payload)

    def test_truthy_non_dict_freshness_entries_falls_back_to_process(self):
        self.build_accepted_state()
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        cache["entries"] = ["malformed"]
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

        payload = self.preflight()
        self.assertEqual(payload["status"], "ok", payload)
        self.assertEqual(payload["action"], "process", payload)


if __name__ == "__main__":
    import unittest

    unittest.main()
