"""Issue #68 T68-7: ``教授研究/套磁邮件总览.md`` is a derived projection.

``stage5-rebuild-overview`` is the only Stage-5 writer of that aggregate. It
enumerates every professor-local ``邮件输入.json``, joins each one with that
professor's own ``套磁邮件状态.json`` and ``_contact_verify.json`` for display,
and modifies nothing else. A manual aggregate edit stops only the rebuild, and a
malformed local pack or state fails closed before the aggregate is touched.
"""

import importlib.util
import hashlib
import io
import contextlib
import json
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("contact_state_test_helpers",
                                              HERE / "test_contact_state.py")
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)

BaseEnv = helpers.BaseEnv
parse = helpers.parse
contact_state = helpers.contact_state
A = helpers.ISSUE59_PROFESSOR
A_ID = helpers.ISSUE59_EMAIL_ID
B = helpers.ISSUE59_OTHER_PROFESSOR
B_ID = helpers.ISSUE59_OTHER_EMAIL_ID
OVERVIEW = contact_state.EMAIL_OVERVIEW
POISON_DIRECTION = "被污染的旧全局方向"


class TestStage5OverviewRebuild(helpers.Stage5LocalHarness, BaseEnv):
    def setUp(self):
        super().setUp()
        fixture = helpers.write_issue59_stage5_fixture(self.root, [
            {"professor": A, "evidence": "fresh"},
            {"professor": B, "evidence": "fresh"}], case=self)
        self.a_dir = Path(fixture["dirs"][A])
        self.b_dir = Path(fixture["dirs"][B])
        self.research = self.root / "教授研究"
        self.overview = self.research / OVERVIEW
        self.registry = self.research / contact_state.PROJECTIONS_FILE

    # ---- deterministic surfaces ------------------------------------------

    def rebuild(self):
        return parse(helpers.run_cli("stage5-rebuild-overview",
                                     "--program-root", self.root))

    def commit(self, professor, email_id):
        """One owner transaction: exactly this professor's local pack."""
        pack = self.pack_for(professor)
        results = helpers.issue59_write_results(
            self.root, f"overview-{professor}-raw.json", [email_id])
        choices = helpers.issue59_write_choices(
            self.root, f"overview-{professor}-choices.json", [email_id])
        draft = self.plan("--result", results, "--choices", choices,
                          "--email-id", email_id, pack=pack)
        self.assertEqual(draft["status"], "ok", draft)
        humanized = self.root / f"overview-{professor}-humanized.txt"
        humanized.write_text(draft["drafts"][0]["draft"], encoding="utf-8")
        out = self.finalize("--result", results, "--choices", choices,
                            "--email-id", email_id, "--humanized", humanized,
                            pack=pack)
        self.assertEqual(out["status"], "ok", out)
        return out

    def local_surfaces(self):
        """Every professor-local Stage-5 input, output and cache, byte-exact."""
        captured = {}
        for directory in (self.a_dir, self.b_dir):
            for path in sorted(directory.iterdir()):
                if path.is_file():
                    captured[str(path)] = path.read_bytes()
        return captured

    def table(self, path=None):
        """The aggregate body with its per-run clock line normalized away."""
        text = (path or self.overview).read_text(encoding="utf-8")
        _, body = contact_state.split_frontmatter(text)
        return re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "<clock>", body)

    # ---- T68-7 -----------------------------------------------------------

    def test_issue68_t68_7_rebuild_joins_each_professor_local_state(self):
        committed = {"A": self.commit(A, A_ID), "B": self.commit(B, B_ID)}
        self.assertFalse(self.overview.exists(),
                         "a professor's finalize created the program aggregate")
        before = self.local_surfaces()

        out = self.rebuild()
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["overview_md"], str(self.overview), out)
        self.assertEqual(out["professors"], 2, out)
        self.assertEqual(out["emails"], 2, out)
        body = self.table()
        self.assertIn(A, body)
        self.assertIn(B, body)
        self.assertIn("✅ 全 confirmed", body, "the verify cache did not reach the display")
        # Exact join: every link is the file that professor's own state names.
        for directory in (self.a_dir, self.b_dir):
            state = json.loads((directory / contact_state.EMAIL_STATE)
                               .read_text(encoding="utf-8"))
            for entry in state["emails"].values():
                for key in ("md", "txt"):
                    linked = Path(entry["files"][key])
                    self.assertIn(f"{directory.parent.name}/{directory.name}/{linked.name}",
                                  body, f"{linked.name} is not this professor's own file")
        for result in committed.values():
            for email in result["emails"]:
                self.assertIn(Path(email["md"]).name, body)
        self.assertEqual(self.local_surfaces(), before,
                         "the rebuild modified a professor-local surface")

    def test_issue68_t68_7_rebuild_is_deterministic_after_deletion(self):
        self.commit(A, A_ID)
        first = self.rebuild()
        self.assertEqual(first["status"], "ok", first)
        bytes_before = self.overview.read_bytes()
        local_before = self.local_surfaces()
        # Distinct clock values must not change a projection of fixed inputs.
        with patch.object(contact_state, "now_utc", return_value="2099-01-01T00:00:00Z"):
            with contextlib.redirect_stdout(io.StringIO()):
                contact_state.cmd_stage5_rebuild_overview(SimpleNamespace(program_root=self.root))
        self.assertEqual(self.overview.read_bytes(), bytes_before)
        self.overview.unlink()

        second = self.rebuild()
        self.assertEqual(second["status"], "ok", second)
        self.assertEqual(self.overview.read_bytes(), bytes_before,
                         "the rebuilt bytes are not deterministic")
        header, body = self.overview.read_text(encoding="utf-8").split("\n---\n\n", 1)
        fields = dict(line.split(": ", 1) for line in header.splitlines()[1:])
        self.assertEqual(fields["managed_by"], "contact_state")
        self.assertEqual(fields["render_sha256"], hashlib.sha256(body.encode()).hexdigest())
        self.assertFalse(self.registry.exists())
        self.assertEqual(self.local_surfaces(), local_before)

    def test_issue68_rebuild_never_reads_or_writes_shared_registry(self):
        self.commit(A, A_ID)
        self.registry.write_text(helpers.ISSUE59_MALFORMED_JSON, encoding="utf-8")
        before = self.registry.read_bytes()
        original_open = Path.open

        def guarded_open(path, *args, **kwargs):
            self.assertNotEqual(path.resolve(), self.registry.resolve(),
                                "overview accessed the shared registry")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", guarded_open), contextlib.redirect_stdout(io.StringIO()):
            contact_state.cmd_stage5_rebuild_overview(SimpleNamespace(program_root=self.root))
        self.assertTrue(self.overview.is_file())
        self.assertEqual(self.registry.read_bytes(), before)

    def test_issue68_t68_7_manual_aggregate_edit_blocks_only_the_rebuild(self):
        self.commit(A, A_ID)
        self.assertEqual(self.rebuild()["status"], "ok")
        edited = self.overview.read_text(encoding="utf-8") + "| 手工 | 手工 | 手工 | 手工 | 手工 | 手工 | 手工 | 手工 |\n"
        self.overview.write_text(edited, encoding="utf-8")
        overview_before = self.overview.read_bytes()
        self.assertFalse(self.registry.exists())
        local_before = self.local_surfaces()

        out = self.rebuild()
        self.assertEqual(out["status"], "needs_decision", out)
        self.assertEqual(out["reason_code"], "manual_markdown_changed", out)
        self.assertEqual(self.overview.read_bytes(), overview_before,
                         "the rebuild overwrote a manual edit")
        self.assertFalse(self.registry.exists())
        self.assertEqual(self.local_surfaces(), local_before)

        # The aggregate is not a commit gate: B still commits while A's
        # projection stands in conflict.
        committed = self.commit(B, B_ID)
        self.assertEqual(committed["status"], "ok", committed)
        self.assertTrue((self.b_dir / contact_state.EMAIL_STATE).is_file())
        self.assertEqual(self.overview.read_bytes(), overview_before,
                         "a professor's finalize wrote the conflicted aggregate")

    def test_issue68_t68_7_malformed_local_input_fails_closed_without_overwrite(self):
        self.commit(A, A_ID)
        self.commit(B, B_ID)
        self.assertEqual(self.rebuild()["status"], "ok")
        overview_before = self.overview.read_bytes()
        b_pack = self.pack_for(B)
        b_state = self.b_dir / contact_state.EMAIL_STATE
        originals = {b_pack: b_pack.read_bytes(), b_state: b_state.read_bytes()}
        for label, target in (("pack", b_pack), ("state", b_state)):
            with self.subTest(defect=label):
                target.write_text(helpers.ISSUE59_MALFORMED_JSON, encoding="utf-8")
                out = self.rebuild()
                self.assertEqual(out["status"], "error", out)
                self.assertEqual(out["reason_code"],
                                 "missing_email_pack" if label == "pack"
                                 else "missing_email_state", out)
                self.assertEqual(self.overview.read_bytes(), overview_before,
                                 f"a broken {label} still overwrote the aggregate")
            for path, payload in originals.items():
                path.write_bytes(payload)

    def test_issue68_t68_7_legacy_program_pack_contributes_no_rows(self):
        self.commit(A, A_ID)
        first = self.rebuild()
        self.assertEqual(first["professors"], 1, first)

        legacy = json.loads(self.pack_for(A).read_text(encoding="utf-8"))
        legacy["schema"] = contact_state.EMAIL_PACK_SCHEMA
        legacy.pop("professor")
        legacy.pop("professor_dir")
        foreign = json.loads(json.dumps(legacy["emails"]))
        for row in foreign:
            row["email_id"] = f"旧全局 教授::{row['collection_key']}::legacy"
            row["professor"] = "旧全局 教授"
            row["name_ja"] = row["name_zh"] = POISON_DIRECTION
        legacy["emails"] = foreign
        path = self.research / contact_state.EMAIL_PACK
        path.write_text(json.dumps(legacy, ensure_ascii=False, indent=1), encoding="utf-8")
        legacy_before, local_before = path.read_bytes(), self.local_surfaces()

        out = self.rebuild()
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["professors"], 1, out)
        self.assertEqual(out["emails"], 1, out)
        self.assertNotIn(POISON_DIRECTION, self.table(),
                         "the legacy program pack became a second projection source")
        self.assertEqual(path.read_bytes(), legacy_before,
                         "the rebuild rewrote the legacy pack #67 owns")
        self.assertEqual(self.local_surfaces(), local_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
