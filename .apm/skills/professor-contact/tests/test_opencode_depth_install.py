"""Deterministic install contract for the OpenCode subagent depth budget.

Issue #29 / PR #34 recipe case D: the fresh formal OpenCode install must
itself provide an effective ``subagent_depth >= 3`` for the three-layer
analyzer orchestration, and the value must come from the producer's own
install contract — never from test-owned config injection. APM deploys only
agents/skills primitives (machine-probed: no arbitrary config file, no
package lifecycle execution), so the producer ships a deterministic
configurator that the documented install flow runs after ``apm install``.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".apm" / "skills" / "professor-contact"
INSTALLER_PATH = SKILL_DIR / "scripts" / "configure_opencode_depth.py"
ANALYZER_PATH = REPO_ROOT / ".apm" / "agents" / "professor-contact-analyzer.agent.md"
SKILL_PATH = SKILL_DIR / "SKILL.md"

SCHEMA = "https://opencode.ai/config.json"


def _run_installer(args, cwd):
    return subprocess.run(
        [sys.executable, str(INSTALLER_PATH), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _read_config(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ConfigureOpencodeDepthInstallerTest(unittest.TestCase):
    def test_installer_exists_next_to_product_runner(self):
        self.assertTrue(
            INSTALLER_PATH.is_file(),
            "configure_opencode_depth.py must ship inside the installed skill scripts",
        )

    def test_apply_creates_root_config_with_schema_and_required_depth(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = _run_installer(["--project-root", str(root)], cwd=tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            config_path = root / "opencode.json"
            self.assertTrue(config_path.is_file())
            config = _read_config(config_path)
            self.assertGreaterEqual(config["subagent_depth"], 3)
            self.assertEqual(config["$schema"], SCHEMA)
            self.assertEqual(
                sorted(config.keys()), ["$schema", "subagent_depth"]
            )

    def test_apply_is_idempotent_byte_for_byte(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(_run_installer(["--project-root", str(root)], cwd=tmp).returncode, 0)
            first = (root / "opencode.json").read_bytes()
            second = _run_installer(["--project-root", str(root)], cwd=tmp)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                (root / "opencode.json").read_bytes(),
                first,
                "re-running the documented install step must not rewrite the config",
            )

    def test_merge_preserves_unrelated_existing_keys(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "opencode.json"
            config_path.write_text(
                json.dumps(
                    {"$schema": SCHEMA, "model": "x/y", "subagent_depth": 1},
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            proc = _run_installer(["--project-root", str(root)], cwd=tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            config = _read_config(config_path)
            self.assertEqual(config["model"], "x/y")
            self.assertGreaterEqual(config["subagent_depth"], 3)

    def test_apply_never_downgrades_higher_existing_depth(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "opencode.json"
            config_path.write_text(
                json.dumps({"$schema": SCHEMA, "subagent_depth": 5}) + "\n",
                encoding="utf-8",
            )
            before = config_path.read_bytes()
            proc = _run_installer(["--project-root", str(root)], cwd=tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(_read_config(config_path)["subagent_depth"], 5)
            self.assertEqual(
                config_path.read_bytes(),
                before,
                "an already-satisfied config must stay byte-identical",
            )

    def test_check_reports_ok_and_needs_config_without_writing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = _run_installer(
                ["--project-root", str(root), "--check"], cwd=tmp
            )
            self.assertEqual(
                missing.returncode,
                2,
                "--check without any config must fail closed with needs_config",
            )
            payload = json.loads(missing.stdout)
            self.assertEqual(payload["status"], "needs_config")
            self.assertEqual(
                sorted(p.name for p in root.iterdir() if p.is_file()),
                [],
                "--check must never write",
            )
            applied = _run_installer(["--project-root", str(root)], cwd=tmp)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            ok = _run_installer(["--project-root", str(root), "--check"], cwd=tmp)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertGreaterEqual(json.loads(ok.stdout)["effective_depth"], 3)

    def test_check_fails_ambiguous_when_dotdir_config_conflicts(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "opencode.json").write_text(
                json.dumps({"$schema": SCHEMA, "subagent_depth": 3}) + "\n",
                encoding="utf-8",
            )
            dotdir = root / ".opencode"
            dotdir.mkdir()
            (dotdir / "opencode.json").write_text(
                json.dumps({"subagent_depth": 1}) + "\n",
                encoding="utf-8",
            )
            proc = _run_installer(
                ["--project-root", str(root), "--check"], cwd=tmp
            )
            self.assertEqual(
                proc.returncode,
                3,
                "an unresolvable precedence conflict must fail closed",
            )
            self.assertEqual(json.loads(proc.stdout)["status"], "ambiguous")

    def test_invalid_existing_json_fails_closed_without_modification(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "opencode.json"
            config_path.write_text("{not json", encoding="utf-8")
            before = config_path.read_bytes()
            proc = _run_installer(["--project-root", str(root)], cwd=tmp)
            self.assertNotEqual(
                proc.returncode,
                0,
                "corrupt project config must fail closed, never be overwritten",
            )
            self.assertEqual(config_path.read_bytes(), before)

    def test_depth_below_one_is_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            proc = _run_installer(
                ["--project-root", tmp, "--depth", "0"], cwd=tmp
            )
            self.assertNotEqual(proc.returncode, 0)


class OpenCodeDepthInstallContractTest(unittest.TestCase):
    """The documented install flow, not test-owned injection, owns the depth."""

    def test_analyzer_documents_producer_owned_install_step(self):
        body = ANALYZER_PATH.read_text(encoding="utf-8")
        self.assertIn("configure_opencode_depth", body)
        self.assertIn("subagent_depth", body)
        self.assertNotIn(
            "由 `professor-contact` 的正常安装配置负责提供，不依赖用户全局旧配置。",
            body,
            "the false one-step install claim must stay removed",
        )

    def test_skill_opencode_branch_references_install_step(self):
        skill = SKILL_PATH.read_text(encoding="utf-8")
        opencode_branch = skill.index("### OpenCode 分支")
        codex_branch = skill.index("### Codex 分支")
        branch = skill[opencode_branch:codex_branch]
        self.assertIn("configure_opencode_depth", branch)
        self.assertIn("subagent_depth", branch)


if __name__ == "__main__":
    unittest.main()
