#!/usr/bin/env python3
"""Static acceptance checks for issue #74 plan-4 test review."""
from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


BASE_SHA = "768b49ef4514e36edec6b57ed3821a99af9e9c00"
ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / ".apm/skills/professor-contact/tests"
RUNTIME = TESTS / "runtime"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str, checks: list[str]) -> None:
    if not condition:
        raise AssertionError(message)
    checks.append(message)


def main() -> int:
    checks: list[str] = []
    try:
        diff = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--name-only", f"{BASE_SHA}..HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        changed = [line for line in diff.stdout.splitlines() if line]
        implementation_paths = {
            ".apm/skills/professor-contact/tests/README.md",
            ".apm/skills/professor-contact/tests/runtime/fixture_support.py",
            ".apm/skills/professor-contact/tests/runtime/prepare_issue53_stage4_fixture.py",
            ".apm/skills/professor-contact/tests/runtime/prepare_issue55_stage3_fixture.py",
            ".apm/skills/professor-contact/tests/test_fixture_support.py",
        }
        test_material_paths = {
            ".apm/skills/professor-contact/tests/test_issue74_cli_compat.py",
        }
        allowed_nonimplementation = {"plan/issue-74.md"}
        unexpected = [
            path for path in changed
            if path not in implementation_paths
            and path not in test_material_paths
            and path not in allowed_nonimplementation
            and not path.startswith("test-plan/issue-74")
        ]
        require(not unexpected, f"no business-program paths changed: {unexpected}", checks)
        require(
            implementation_paths.issubset(set(changed)),
            "all approved implementation paths are present in the PR diff",
            checks,
        )

        helper_path = RUNTIME / "fixture_support.py"
        helper_tree = ast.parse(helper_path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(helper_tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
        forbidden_imports = {
            "subprocess", "socket", "requests", "urllib", "http", "webbrowser",
            "selenium", "playwright",
        }
        require(
            not (imports & forbidden_imports),
            f"shared helper has no external-service/browser process imports: {sorted(imports)}",
            checks,
        )

        fixture53 = load_module(
            "issue74_static_fixture53", RUNTIME / "prepare_issue53_stage4_fixture.py"
        )
        fixture55 = load_module(
            "issue74_static_fixture55", RUNTIME / "prepare_issue55_stage3_fixture.py"
        )
        require(
            fixture53.support is fixture55.support,
            "issue 53 and issue 55 load the same shared helper module",
            checks,
        )
        for label, fixture in (("53", fixture53), ("55", fixture55)):
            require(
                fixture.FixtureBuildError is fixture.support.FixtureBuildError,
                f"issue {label} reuses shared FixtureBuildError",
                checks,
            )
            require(
                fixture.sha256 is fixture.support.file_sha256,
                f"issue {label} reuses shared SHA-256 helper",
                checks,
            )
            require(
                fixture._write_json is fixture.support.write_json,
                f"issue {label} reuses shared JSON writer",
                checks,
            )

        def cli_options(fixture) -> set[str]:
            return {
                option
                for action in fixture._parser()._actions
                for option in action.option_strings
                if option not in {"-h", "--help"}
            }

        require(
            cli_options(fixture53) == {"--program-root", "--profile-root", "--output"},
            "issue 53 CLI parameters remain unchanged",
            checks,
        )
        require(
            cli_options(fixture55) == {"--program-root", "--output"},
            "issue 55 CLI parameters remain unchanged",
            checks,
        )

        source53 = (RUNTIME / "prepare_issue53_stage4_fixture.py").read_text(encoding="utf-8")
        source55 = (RUNTIME / "prepare_issue55_stage3_fixture.py").read_text(encoding="utf-8")
        for marker in ("Example Professor", "Synthetic Systems"):
            require(
                marker in source53 and marker in source55,
                f"both migrated fixtures retain synthetic marker {marker!r}",
                checks,
            )

        readme = (TESTS / "README.md").read_text(encoding="utf-8")
        required_readme_fragments = (
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
        missing = [fragment for fragment in required_readme_fragments if fragment not in readme]
        require(not missing, f"README contains all R4 instructions: {missing}", checks)

        payload = {"schema_version": 1, "verdict": "PASS", "checks": checks}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        payload = {
            "schema_version": 1,
            "verdict": "FAIL",
            "checks": checks,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
