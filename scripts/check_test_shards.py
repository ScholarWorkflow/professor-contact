#!/usr/bin/env python3
"""Verify that the CI shard lists cover every test module exactly once.

``plan/test-grouping/shards.json`` is the single source of truth for the
shards and for the behaviour-based stage of each module. This script fails
when a module is missing from every shard, listed twice, listed with a name
that has no file, listed without being discoverable, listed without a stage,
or carrying a stage outside the documented vocabulary.
``--print <shard>`` emits that shard's module names for the CI step that runs
it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / ".apm/skills/professor-contact/tests"
MANIFEST = ROOT / "plan/test-grouping/shards.json"
WORKFLOW = ROOT / ".github/workflows/ci.yml"
STAGES = {"stage1", "stage2", "stage3", "stage4", "stage5", "non-stage"}


def load_shards() -> list[dict]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return list(data["shards"])


def discovered() -> list[str]:
    return sorted(path.stem for path in TESTS.glob("test_*.py"))


def workflow_shards() -> list[str]:
    """Shard names the CI workflow actually runs (matrix.shard list)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"matrix:\s*\n\s*shard:\s*\[([^\]]*)\]", text)
    if not match:
        return []
    return [name.strip().strip("'\"") for name in match.group(1).split(",") if name.strip()]


def stage_of(module: dict) -> str:
    return str(module.get("stage", ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", dest="print_shard", metavar="SHARD",
                        help="print this shard's module names and exit")
    args = parser.parse_args()

    shards = load_shards()
    if args.print_shard:
        for shard in shards:
            if shard["name"] == args.print_shard:
                print(" ".join(module["name"] for module in shard["modules"]))
                return 0
        print(f"unknown shard: {args.print_shard}", file=sys.stderr)
        return 2

    found = set(discovered())
    problems: list[str] = []
    owner: dict[str, str] = {}
    for shard in shards:
        modules = shard.get("modules", [])
        if not modules:
            problems.append(f"{shard.get('name')} lists no modules")
        for module in modules:
            name = module.get("name", "")
            if not (TESTS / f"{name}.py").is_file():
                problems.append(f"{shard['name']}: no such test module: {name}.py")
            if name in owner:
                problems.append(f"{name} listed in both {owner[name]} and {shard['name']}")
            owner[name] = shard["name"]
            stage = stage_of(module)
            if not stage:
                problems.append(f"{name} carries no stage")
            elif stage not in STAGES and not stage.startswith("mixed:"):
                problems.append(f"{name} carries an unknown stage: {stage}")
    for module in sorted(found - set(owner)):
        problems.append(f"not covered by any shard: {module}")
    for module in sorted(set(owner) - found):
        problems.append(f"listed but not discoverable: {module}")

    # The manifest must describe exactly the shards the workflow runs: a shard
    # that exists only in the manifest would never execute, and a workflow
    # shard missing from the manifest would run nothing.
    manifest_names = [shard.get("name") for shard in shards]
    workflow_names = workflow_shards()
    # Duplicate names would silently drop tests: two shards called shard1 both
    # count towards coverage, but ``--print shard1`` only emits the first one,
    # so the second shard's modules never run.
    for label, names in (("manifest", manifest_names), ("workflow", workflow_names)):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            problems.append(f"{label} repeats shard name(s): {', '.join(duplicates)}")
    if not workflow_names:
        problems.append("cannot read the shard list from .github/workflows/ci.yml")
    else:
        for name in manifest_names:
            if name not in workflow_names:
                problems.append(f"shard {name} is not run by the workflow")
        for name in workflow_names:
            if name not in manifest_names:
                problems.append(f"workflow shard {name} has no manifest entry")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    print(f"OK: {len(owner)} test modules across {len(shards)} shards, "
          f"each with a stage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
