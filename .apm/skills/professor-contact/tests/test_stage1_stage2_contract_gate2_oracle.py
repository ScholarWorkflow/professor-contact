import unittest

from test_stage1_stage2_contract import ROOT, bash_commands


class Issue64Gate2T7OracleTests(unittest.TestCase):
    """Supplement G64-T7-b with an exact plan/finalize proof-path check."""

    def test_issue64_t7_plan_and_finalize_consume_same_transaction_preflight_file(self):
        expected = "--preflight-file <本教授事务临时目录>/stage2_preflight.json"
        retired = "--preflight-file /tmp/<教授名>_stage2_preflight.json"

        for target in ("professor-contact-codex", "professor-contact-opencode"):
            with self.subTest(target=target):
                path = (
                    ROOT.parents[2]
                    / "packages"
                    / target
                    / ".apm"
                    / "agents"
                    / "professor-contact-analyzer.agent.md"
                )
                commands = bash_commands(path.read_text(encoding="utf-8"))
                plan = [command for command in commands
                        if "contact_state.py stage2-plan" in command]
                finalize = [command for command in commands
                            if "contact_state.py stage2-finalize" in command]

                self.assertEqual(len(plan), 1, msg=plan)
                self.assertEqual(len(finalize), 1, msg=finalize)
                for command in (plan[0], finalize[0]):
                    self.assertIn(expected, command, msg=command)
                    self.assertNotIn(retired, command, msg=command)


if __name__ == "__main__":
    unittest.main()
