"""Focused non-formal checks for the PC68-R1 fixture builder's partition oracle."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


RUNTIME = Path(__file__).resolve().parent
BUILDER_PATH = RUNTIME / "prepare_issue68_stage5_routing.py"
SPEC = importlib.util.spec_from_file_location("prepare_issue68_stage5_routing", BUILDER_PATH)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class TestIssue68FixturePartitionOracle(unittest.TestCase):
    def test_partition_expectation_is_fixed_and_builder_does_not_partition(self):
        with tempfile.TemporaryDirectory(prefix="pc68-fixture-preflight-") as temp:
            root = Path(temp)
            fake_cli = root / "fake-contact-state.py"
            calls_file = root / "cli-calls.jsonl"
            fake_cli.write_text(
                "import json, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                f"with pathlib.Path({str(calls_file)!r}).open('a', encoding='utf-8') as stream:\n"
                "    stream.write(json.dumps(args, ensure_ascii=False) + '\\n')\n"
                "if not args or args[0] != 'stage5-plan':\n"
                "    raise SystemExit(88)\n"
                "pack = pathlib.Path(args[args.index('--email-pack') + 1])\n"
                "professor = pack.parent.name\n"
                "if '--result' in args:\n"
                "    print(json.dumps({'status': 'needs_refresh', 'reason_code': 'verify_missing',\n"
                "                      'professor_dir': str(pack.parent)} , ensure_ascii=False))\n"
                "    raise SystemExit(2)\n"
                "print(json.dumps({'status': 'ok', 'verify': {professor: 'needs_recheck:missing'}},\n"
                "                 ensure_ascii=False))\n",
                encoding="utf-8",
            )

            manifest = builder.prepare(root / "program", fake_cli, root / "out")

            owners = {owner["professor"]: owner for owner in manifest["owners"]}
            expected_specs = {
                "試験 教授": {
                    "email_id": "試験 教授::DIR00001::DIR00001_1",
                    "first_choice": False,
                    "signature_name": "試験 太郎",
                    "learning": "比較手法の基礎知識の習得",
                    "transport_sentinel": "owner-0",
                },
                "佐藤 花子": {
                    "email_id": "佐藤 花子::DIR00001::DIR00001_1",
                    "first_choice": False,
                    "signature_name": "試験 太郎",
                    "learning": "比較手法の基礎知識の習得",
                    "transport_sentinel": "owner-1",
                },
            }
            self.assertEqual(set(owners), set(expected_specs))
            expected_partition = []
            for professor, fixed in expected_specs.items():
                row = {**fixed, "professor_dir": owners[professor]["professor_dir"]}
                self.assertEqual(owners[professor]["expected_choices_rows"], [row])
                expected_partition.append({
                    "professor_dir": owners[professor]["professor_dir"],
                    "status": "ok",
                    "choices_rows": [row],
                })
            self.assertEqual(manifest["partition"]["owners"], expected_partition)
            self.assertEqual(
                json.loads((root / "out" / "canonical-choices.json").read_text(encoding="utf-8")),
                manifest["expected_choices"],
            )

            output_files = {path.name for path in (root / "out").iterdir()}
            self.assertNotIn("partition-bundles.json", output_files)
            self.assertFalse(any(name.startswith("owner-") and "bundle-choices" in name
                                 for name in output_files))
            self.assertFalse(any(name.startswith("root-partition.") for name in output_files))

            cli_calls = [json.loads(line) for line in calls_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(cli_calls), 4)
            self.assertTrue(all(args[0] == "stage5-plan" for args in cli_calls))
            self.assertTrue(all("--choices" not in args for args in cli_calls))


if __name__ == "__main__":
    unittest.main()
