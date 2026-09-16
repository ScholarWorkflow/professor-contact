#!/usr/bin/env python3
"""Verify the producer-owned PR #47 clean-consumer target projections."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tomllib
from pathlib import Path


ANALYZER = "professor-contact-analyzer"
CODEX_FORBIDDEN = ("opencode run", "task(", "question(", "spawn_agent(", "spawnAgent")


def parse_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"{path}: missing frontmatter terminator")
    raw = text[4:end]
    parsed = subprocess.run(
        ["yq", "-p=yaml", "-o=json", ".", "-"],
        input=raw + "\n",
        text=True,
        capture_output=True,
        check=False,
    )
    if parsed.returncode != 0:
        raise ValueError(f"{path}: invalid YAML frontmatter: {parsed.stderr}")
    return json.loads(parsed.stdout), text[end + 5 :]


def read_codex(root: Path) -> tuple[Path, dict[str, object], str]:
    path = root / ".codex" / "agents" / f"{ANALYZER}.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return path, data, str(data.get("developer_instructions", ""))


def read_opencode(root: Path) -> tuple[Path, dict[str, object], str]:
    path = root / ".opencode" / "agents" / f"{ANALYZER}.md"
    data, body = parse_frontmatter(path)
    return path, data, body


def lock_packages(root: Path) -> list[str]:
    lock = root / "apm.lock.yaml"
    parsed = subprocess.run(
        ["yq", "-p=yaml", "-o=json", ".", str(lock)],
        text=True,
        capture_output=True,
        check=False,
    )
    if parsed.returncode != 0:
        raise ValueError(f"{lock}: invalid YAML: {parsed.stderr}")
    data = json.loads(parsed.stdout)
    found: list[str] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            name = node.get("name")
            if isinstance(name, str) and name in {"professor-contact-opencode", "professor-contact-codex"}:
                found.append(name)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(data)
    return sorted(set(found))


def suite_passed(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return (
        bool(re.search(r"Ran\s+\d+\s+tests", text))
        and bool(re.search(r"(?m)^OK(?:\s+\([^\n]*\))?$", text))
        and "FAILED" not in text
    )


def check(name: str, passed: bool, details: object) -> dict[str, object]:
    return {"name": name, "passed": passed, "details": details}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--codex-root", type=Path, required=True)
    parser.add_argument("--opencode-root", type=Path, required=True)
    parser.add_argument("--combined-root", type=Path, required=True)
    parser.add_argument("--suite-output", type=Path, required=True)
    parser.add_argument("--producer-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    codex_path, codex_data, codex_body = read_codex(args.codex_root)
    opencode_path, opencode_data, opencode_body = read_opencode(args.opencode_root)
    combined_codex_path, combined_codex_data, combined_codex_body = read_codex(args.combined_root)
    combined_opencode_path, combined_opencode_data, combined_opencode_body = read_opencode(args.combined_root)

    codex_agents = []
    for path in sorted((args.codex_root / ".codex" / "agents").glob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if data.get("name") == ANALYZER:
            codex_agents.append(path.name)

    root_skill = args.producer / ".apm" / "skills" / "professor-contact" / "SKILL.md"
    package_skill_paths = [
        args.producer / "packages" / "professor-contact-opencode" / ".apm" / "skills",
        args.producer / "packages" / "professor-contact-codex" / ".apm" / "skills",
    ]
    checks = [
        check("codex_r2_agent_unique", len(codex_agents) == 1, {"matches": codex_agents}),
        check("codex_r2_agent_name_matches_contract", codex_data.get("name") == ANALYZER, {"name": codex_data.get("name")}),
        check(
            "codex_r2_delegation_contract_present",
            all(token in codex_body for token in ("paper-analysis", "professor-contact-style-validator"))
            and bool(re.search(r"(?is)(?:delegate|use|委派).*?(?:wait|等待)", codex_body)),
            {"has_paper_analysis": "paper-analysis" in codex_body, "has_style_validator": "professor-contact-style-validator" in codex_body},
        ),
        check("codex_no_opencode_shell_launch_contract", "opencode run" not in codex_body, None),
        check("codex_no_opencode_task_api_contract", "task(" not in codex_body, None),
        check("codex_no_opencode_question_api_contract", "question(" not in codex_body, None),
        check(
            "opencode_professor_contact_primitives_present",
            opencode_path.is_file() and root_skill.is_file(),
            {"agent": str(opencode_path), "shared_skill": str(root_skill)},
        ),
        check(
            "opencode_task_subagent_contract_preserved",
            opencode_data.get("mode") == "subagent"
            and opencode_data.get("hidden") is True
            and opencode_data.get("permission", {}).get("task") == "allow",
            {"mode": opencode_data.get("mode"), "hidden": opencode_data.get("hidden"), "task": opencode_data.get("permission", {}).get("task")},
        ),
        check(
            "opencode_question_contract_preserved",
            opencode_data.get("permission", {}).get("question") == "allow",
            {"question": opencode_data.get("permission", {}).get("question")},
        ),
        check(
            "combined_target_codex_projection_correct",
            combined_codex_data.get("name") == ANALYZER and all(token not in combined_codex_body for token in CODEX_FORBIDDEN),
            {"name": combined_codex_data.get("name"), "forbidden": [token for token in CODEX_FORBIDDEN if token in combined_codex_body]},
        ),
        check(
            "combined_target_opencode_projection_correct",
            combined_opencode_data.get("name") == ANALYZER
            and combined_opencode_data.get("mode") == "subagent"
            and combined_opencode_data.get("permission", {}).get("task") == "allow"
            and combined_opencode_data.get("permission", {}).get("question") == "allow",
            {"name": combined_opencode_data.get("name"), "mode": combined_opencode_data.get("mode")},
        ),
        check(
            "combined_target_no_cross_target_leakage",
            all(token not in combined_codex_body for token in CODEX_FORBIDDEN)
            and "### OpenCode 分支" in combined_opencode_body
            and "### Codex 分支" in combined_opencode_body,
            {"codex_forbidden": [token for token in CODEX_FORBIDDEN if token in combined_codex_body]},
        ),
        check(
            "shared_business_assets_single_source",
            root_skill.is_file() and all(not path.exists() for path in package_skill_paths),
            {"shared_skill": str(root_skill), "package_skill_dirs": [str(path) for path in package_skill_paths]},
        ),
        check("producer_deterministic_suite_passed", suite_passed(args.suite_output), str(args.suite_output)),
    ]
    result = {
        "schema": 1,
        "producer_sha": args.producer_sha,
        "producer": str(args.producer),
        "consumers": {"codex": str(args.codex_root), "opencode": str(args.opencode_root), "combined": str(args.combined_root)},
        "lock_packages": {
            "codex": lock_packages(args.codex_root),
            "opencode": lock_packages(args.opencode_root),
            "combined": lock_packages(args.combined_root),
        },
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "passed": result["passed"]}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
