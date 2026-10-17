import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_input_router.py"
AGENT = (
    ROOT.parents[2]
    / "packages"
    / "professor-contact-opencode"
    / ".apm"
    / "agents"
    / "professor-contact-analyzer.agent.md"
)
SPEC = importlib.util.spec_from_file_location("stage2_input_router", SCRIPT)
router = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = router
assert SPEC.loader is not None
SPEC.loader.exec_module(router)


class Stage2InputRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root / "inputs"
        self.pdf = self.root / "paper.pdf"
        self.ocr = self.root / "paper.txt"
        self.pdf.write_bytes(b"%PDF-1.4\n")
        self.ocr.write_text("OCR text", encoding="utf-8")
        self.exporter = self.root / "zotero-item-export"
        self.exporter.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            "args=sys.argv[1:]; out=pathlib.Path(args[args.index('--output-dir')+1]); out.mkdir(parents=True, exist_ok=True)\n"
            "keys=args[:args.index('--output-dir')]\n"
            "for key in keys:\n"
            " p=out/f'{key}.json'; p.write_text(json.dumps({'schema':1,'kind':'paper-analysis-input','level':'abstract','source':'zotero','item_key':key,'metadata':{'title':'T','authors':['A'],'year':2025,'venue':'V','doi':''},'abstract':'SECRET ABSTRACT BODY'}), encoding='utf-8')\n"
            "print(json.dumps({'status':'ok','exported':len(keys),'failed':0,'output_dir':str(out.resolve())}))\n",
            encoding="utf-8",
        )
        self.exporter.chmod(self.exporter.stat().st_mode | stat.S_IEXEC)

    def tearDown(self):
        self.temp.cleanup()

    def test_ocr_has_priority_over_pdf(self):
        route = router.route_batch([{"item_key":"A","ocr_path":str(self.ocr),"pdf_path":str(self.pdf)}], self.out, str(self.exporter))[0]
        self.assertEqual(route.carrier, "ocr")
        self.assertEqual(route.level, "fulltext")
        self.assertEqual(route.paper, str(self.ocr.resolve()))
        self.assertTrue(route.gap_only_allowed)

    def test_pdf_is_second_priority(self):
        route = router.route_batch([{"item_key":"A","pdf_path":str(self.pdf)}], self.out, str(self.exporter))[0]
        self.assertEqual(route.carrier, "pdf")
        self.assertEqual(route.level, "fulltext")
        self.assertEqual(route.paper, str(self.pdf.resolve()))
        self.assertTrue(route.gap_only_allowed)

    def test_missing_pdf_batches_export_and_prompt_only_contains_json_path(self):
        routes = router.route_batch([{"item_key":"A"},{"item_key":"B"}], self.out, str(self.exporter))
        self.assertEqual([r.carrier for r in routes], ["abstract_json", "abstract_json"])
        self.assertTrue(all(r.level == "abstract" for r in routes))
        self.assertTrue(all(Path(r.paper).is_absolute() for r in routes))
        prompt = router.build_task_prompt(routes[0], "/tmp/direction.md", "/tmp/save")
        self.assertIn(str((self.out / "A.json").resolve()), prompt)
        self.assertNotIn("SECRET ABSTRACT BODY", prompt)
        self.assertFalse(routes[0].gap_only_allowed)

    def test_loaded_skill_uses_uv_argv_and_preserves_partial_batch(self):
        skill_dir = self.root / "installed skills" / "zotero-read"
        script = skill_dir / "scripts" / "zotero_item_export.py"
        script.parent.mkdir(parents=True)
        script.touch()
        self.out.mkdir()
        (self.out / "B.json").write_text("stale", encoding="utf-8")

        def export(command, **kwargs):
            self.assertEqual(command, ["uv", "run", str(script), "A", "B", "--output-dir", str(self.out.resolve())])
            self.assertFalse((self.out / "B.json").exists())
            (self.out / "A.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(command, 1, json.dumps({
                "status": "partial", "errors": [{"item_key": "B", "reason": "no abstract"}]}), "")

        with mock.patch.object(router.subprocess, "run", side_effect=export) as run:
            routes = router.route_batch(
                [{"item_key": "A"}, {"item_key": "B"}, {"item_key": "A"}],
                self.out, zotero_read_skill_dir=skill_dir)
        run.assert_called_once()
        self.assertEqual([r.status for r in routes], ["ok", "error", "ok"])
        self.assertEqual(routes[0].carrier, "abstract_json")
        self.assertEqual(routes[1].reason, "no abstract")

    def test_missing_or_relative_skill_is_error_without_path_fallback(self):
        for skill_dir in (None, Path("relative/zotero-read"), self.root / "missing"):
            with self.subTest(skill_dir=skill_dir), mock.patch.object(router.subprocess, "run") as run:
                route = router.route_batch([{"item_key": "A"}], self.out,
                                           zotero_read_skill_dir=skill_dir)[0]
                run.assert_not_called()
                self.assertEqual(route.status, "error")
                self.assertIsNone(route.paper)
                self.assertIn("exporter unavailable", route.reason)

    def test_local_carrier_does_not_require_exporter_configuration(self):
        with mock.patch.object(router.subprocess, "run") as run:
            route = router.route_batch([{"item_key": "A", "pdf_path": str(self.pdf)}], self.out)[0]
        run.assert_not_called()
        self.assertEqual(route.carrier, "pdf")

    def test_export_failure_is_explicit_and_cannot_build_prompt(self):
        failed = self.root / "failed-exporter"
        failed.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        failed.chmod(failed.stat().st_mode | stat.S_IEXEC)
        route = router.route_batch([{"item_key":"A"}], self.out, str(failed))[0]
        self.assertEqual(route.status, "error")
        self.assertIsNone(route.paper)
        with self.assertRaises(ValueError):
            router.build_task_prompt(route, "/tmp/direction.md", "/tmp/save")

    def test_stale_success_file_cannot_mask_later_export_failure(self):
        first = router.route_batch([{"item_key":"A"}], self.out, str(self.exporter))[0]
        self.assertEqual(first.status, "ok")
        stale_path = Path(first.paper)
        self.assertTrue(stale_path.is_file())

        failed = self.root / "failed-exporter"
        failed.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        failed.chmod(failed.stat().st_mode | stat.S_IEXEC)
        second = router.route_batch([{"item_key":"A"}], self.out, str(failed))[0]

        self.assertEqual(second.status, "error")
        self.assertIsNone(second.paper)
        self.assertFalse(stale_path.exists())
        with self.assertRaises(ValueError):
            router.build_task_prompt(second, "/tmp/direction.md", "/tmp/save")

    def test_later_pdf_upgrades_abstract_route_to_fulltext(self):
        first = router.route_batch([{"item_key":"A"}], self.out, str(self.exporter))[0]
        self.assertEqual(first.level, "abstract")
        second = router.route_batch([{"item_key":"A","pdf_path":str(self.pdf)}], self.out, str(self.exporter))[0]
        self.assertEqual(second.level, "fulltext")
        self.assertEqual(second.carrier, "pdf")

    def test_reused_analysis_with_current_pdf_remains_gap_only_eligible(self):
        # Full-analysis idempotence is a caller concern. Carrier eligibility must
        # be derived independently from the paper's current OCR/PDF state.
        route = router.route_existing("A", None, str(self.pdf))
        self.assertIsNotNone(route)
        self.assertEqual(route.carrier, "pdf")
        self.assertTrue(route.gap_only_allowed)

    def test_agent_execution_contract_uses_router_and_forbids_raw_item_key_fallback(self):
        for target in ("opencode", "codex"):
            agent = AGENT.parents[3] / f"professor-contact-{target}" / ".apm" / "agents" / AGENT.name
            text = agent.read_text(encoding="utf-8")
            self.assertIn('`zotero-read/SKILL.md` 的父目录', text)
            self.assertIn('stage2_input_router.py --zotero-read-skill-dir "<zotero-read-skill-dir>"', text)
            self.assertIn('--zotero-read-skill-dir "<zotero-read-skill-dir>" \\', text)
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("stage2_input_router.py", text)
        self.assertIn("--papers /tmp/<教授名>_<collection_key>_paper_routes.json", text)
        self.assertIn("gap_only_allowed=false", text)
        self.assertIn("normalized abstract JSON absolute path", text)
        self.assertIn("绝不把 raw Zotero `item_key` 当作 `paper`", text)
        self.assertIn("独立于本轮 full-analysis route", text)
        self.assertIn("当前 PDF/OCR carrier", text)
        self.assertIn("本轮是否需要 full-analysis、是否产生过 route 都不影响这个资格判断", text)
        self.assertNotIn("该篇最近一次 route 的 `gap_only_allowed=true`", text)
        self.assertNotIn("③Zotero item_key（无 PDF/无 OCR 时）", text)
        self.assertNotIn("仅 item_key/摘要 → `abstract`", text)


if __name__ == "__main__":
    unittest.main()
