"""Static acceptance proofs for issue #74 plan-4 migration."""
from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

from gate2_evidence import TestPreparationError


BASE_SHA = "768b49ef4514e36edec6b57ed3821a99af9e9c00"
TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"
REPO_ROOT = TESTS_DIR.parents[3]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Issue74StaticAcceptanceTests(unittest.TestCase):
    def test_pr_diff_contains_only_approved_implementation_and_test_materials(self):
        try:
            result = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "diff", "--name-only", f"{BASE_SHA}..HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise TestPreparationError(f"could not inspect repository diff: {exc}") from exc

        changed = {line for line in result.stdout.splitlines() if line}
        implementation_paths = {
            ".apm/skills/professor-contact/tests/README.md",
            ".apm/skills/professor-contact/tests/runtime/fixture_support.py",
            ".apm/skills/professor-contact/tests/runtime/prepare_issue53_stage4_fixture.py",
            ".apm/skills/professor-contact/tests/runtime/prepare_issue55_stage3_fixture.py",
            ".apm/skills/professor-contact/tests/test_fixture_support.py",
        }
        test_material_paths = {
            ".apm/skills/professor-contact/tests/test_issue74_cli_compat.py",
            ".apm/skills/professor-contact/tests/test_issue74_static_acceptance.py",
            "test-plan/issue-74.md",
        }
        allowed = implementation_paths | test_material_paths | {"plan/issue-74.md"}
        self.assertEqual(changed - allowed, set())
        self.assertTrue(implementation_paths.issubset(changed))

    def test_shared_helper_has_no_external_runtime_imports(self):
        helper_path = RUNTIME_DIR / "fixture_support.py"
        tree = ast.parse(helper_path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
        forbidden = {
            "subprocess", "socket", "requests", "urllib", "http", "webbrowser",
            "selenium", "playwright",
        }
        self.assertEqual(imports & forbidden, set())

    def test_both_entrypoints_reuse_shared_helpers_and_keep_cli_options(self):
        fixture53 = load_module(
            "issue74_static_fixture53", RUNTIME_DIR / "prepare_issue53_stage4_fixture.py"
        )
        fixture55 = load_module(
            "issue74_static_fixture55", RUNTIME_DIR / "prepare_issue55_stage3_fixture.py"
        )
        self.assertIs(fixture53.support, fixture55.support)
        for fixture in (fixture53, fixture55):
            self.assertIs(fixture.FixtureBuildError, fixture.support.FixtureBuildError)
            self.assertIs(fixture.sha256, fixture.support.file_sha256)
            self.assertIs(fixture._write_json, fixture.support.write_json)

        def cli_options(fixture) -> set[str]:
            return {
                option
                for action in fixture._parser()._actions
                for option in action.option_strings
                if option not in {"-h", "--help"}
            }

        self.assertEqual(
            cli_options(fixture53),
            {"--program-root", "--profile-root", "--output"},
        )
        self.assertEqual(
            cli_options(fixture55),
            {"--program-root", "--output"},
        )

    def test_fixtures_stay_synthetic_and_readme_freezes_owner_and_roles(self):
        source53 = (RUNTIME_DIR / "prepare_issue53_stage4_fixture.py").read_text(encoding="utf-8")
        source55 = (RUNTIME_DIR / "prepare_issue55_stage3_fixture.py").read_text(encoding="utf-8")
        for marker in ("Example Professor", "Synthetic Systems"):
            self.assertIn(marker, source53)
            self.assertIn(marker, source55)

        readme = (TESTS_DIR / "README.md").read_text(encoding="utf-8")
        required = (
            "## 职责分工",
            "## 目录分配",
            "跨运行目录分配的唯一责任方是测试执行层",
            "## 调用既有准备入口",
            "## 执行测试与判定结果",
            "gate2_evidence.py",
            "产品断言失败不能当成准备失败",
            "空执行不能当成通过",
            "## 新增议题专属样例",
        )
        for fragment in required:
            self.assertIn(fragment, readme)


if __name__ == "__main__":
    unittest.main()
