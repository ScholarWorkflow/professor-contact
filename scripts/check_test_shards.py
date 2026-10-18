#!/usr/bin/env python3
"""Verify that the CI shard lists cover every test module exactly once.

``plan/test-grouping/shards.json`` is the single source of truth for the
shards; this script fails when a module is missing from every shard, listed
twice, listed with a name that has no file, or listed without being
discoverable. ``--print <shard>`` emits that shard's module list for the CI
step that runs it.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / ".apm/skills/professor-contact/tests"
MANIFEST = ROOT / "plan/test-grouping/shards.json"


def load_shards() -> dict[str, list[str]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {shard["name"]: list(shard["modules"]) for shard in data["shards"]}


def discovered() -> list[str]:
    return sorted(path.stem for path in TESTS.glob("test_*.py"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", dest="print_shard", metavar="SHARD",
                        help="print this shard's module list and exit")
    args = parser.parse_args()

    shards = load_shards()
    if args.print_shard:
        if args.print_shard not in shards:
            print(f"unknown shard: {args.print_shard}", file=sys.stderr)
            return 2
        print(" ".join(shards[args.print_shard]))
        return 0

    found = set(discovered())
    problems: list[str] = []
    owner: dict[str, str] = {}
    for name, modules in shards.items():
        if not modules:
            problems.append(f"{name} lists no modules")
        for module in modules:
            if not (TESTS / f"{module}.py").is_file():
                problems.append(f"{name}: no such test module: {module}.py")
            if module in owner:
                problems.append(f"{module} listed in both {owner[module]} and {name}")
            owner[module] = name
    for module in sorted(found - set(owner)):
        problems.append(f"not covered by any shard: {module}")
    for module in sorted(set(owner) - found):
        problems.append(f"listed but not discoverable: {module}")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    print(f"OK: {len(owner)} test modules across {len(shards)} shards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
