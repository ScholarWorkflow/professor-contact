"""Focused provenance-link checks; no external services or file discovery."""
import copy
import tempfile
import unittest
from pathlib import Path

from _stage5_issue59_test_support import contact_state


class EmailAnalysisLinksTests(unittest.TestCase):
    def test_compile_freezes_canonical_paths_and_hash(self):
        direction = {"direction_id": "D", "supporting_item_keys": ["P"],
                     "gap_shortlist": [{"item_key": "G", "gap_id": "g", "status": "open"}]}
        pack = {"professor": "教授", "papers": {
            "P": {"item_key": "P", "title": "Paper", "analysis_file": "/tmp/P 分析.md"},
            "G": {"item_key": "G", "analysis_file": "/tmp/G 分析.md"}}}
        idea = {"id": "i", "papers": [{"item_key": "P", "analysis_file": "/wrong.md"}],
                "gap_refs": [{"item_key": "G", "gap_id": "g"}]}
        def compile_entry():
            return contact_state.compile_email_entry(pack, {}, direction, idea, "", Path("/tmp"), None)
        email = compile_entry()
        self.assertEqual(email["papers"][0]["analysis_file"], "/tmp/P 分析.md")
        self.assertEqual(email["gaps"][0]["analysis_file"], "/tmp/G 分析.md")
        pack["papers"]["P"]["analysis_file"] = "/tmp/new.md"
        self.assertNotEqual(email["source_hash"], compile_entry()["source_hash"])
        for paper in pack["papers"].values():
            paper.pop("analysis_file")
        old = compile_entry()
        self.assertNotIn("analysis_file", old["papers"][0])
        self.assertNotIn("analysis_file", old["gaps"][0])

    def test_audit_links_and_legacy_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = {"item_key": "P", "title": "paper", "analysis_file": str(root / "论文分析/横山 昌平.md")}
            g = {"item_key": "G", "gap_id": "g", "zotero_key": "G", "paper_title": "gap paper",
                 "email_use": "anchor", "analysis_file": str(root / "论文分析/別の 論文.md")}
            email = {"papers": [p], "gaps": [g]}
            raw = {"source_map": [{"output": "①", "source_ids": ["paper:P", "gap:g", "later:G"]}]}
            source = "\n".join(contact_state.render_source_table(email, raw, root))
            self.assertIn("[分析](<论文分析/横山 昌平.md>)", source)
            self.assertEqual(source.count("[分析](<论文分析/別の 論文.md>)"), 2)
            self.assertIn("zotero://select/library/items/P", source)
            self.assertIn("zotero://select/library/items/G", source)
            card = "\n".join(contact_state.render_fact_check_card(email, root / "pack.json", root))
            self.assertIn("[分析](<论文分析/別の 論文.md>)", card)
            self.assertNotIn("横山", card)
            no_gap = "\n".join(contact_state.render_source_table({"papers": [p]},
                {"source_map": [{"output": "①", "source_ids": ["paper:P"]}]}, root))
            self.assertIn("[分析](<论文分析/横山 昌平.md>)", no_gap)
            legacy = copy.deepcopy(email)
            for record in legacy["papers"] + legacy["gaps"]:
                del record["analysis_file"]
            for text in ("\n".join(contact_state.render_source_table(legacy, raw, root)),
                         "\n".join(contact_state.render_fact_check_card(legacy, root / "pack.json", root))):
                self.assertNotIn("[分析]", text)
                self.assertIn("zotero://select/library/items/G", text)
