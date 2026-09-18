#!/usr/bin/env python3
"""Prepare the producer-owned, Stage-4-only fixture for issue #53."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


MANIFEST_ID = "tests/runtime/prepare_issue53_stage4_fixture.py"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
SELECTION_FILE = Path("教授研究/套磁选择.json")
EMAIL_INPUT_FILE = Path("教授研究/邮件输入.json")


class FixtureBuildError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _producer_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _prepare_root(root: Path) -> None:
    root = root.resolve()
    producer = _producer_root()
    if root == producer or root.is_relative_to(producer):
        raise FixtureBuildError(f"fixture root must be outside producer checkout: {root}")
    if root.exists():
        if not root.is_dir():
            raise FixtureBuildError(f"fixture root is not a directory: {root}")
        entries = list(root.iterdir())
        if entries:
            raise FixtureBuildError(f"refusing to replace non-empty foreign directory: {root}")
        root.rmdir()
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir()


def _candidate_state(profile_path: Path) -> dict[str, Any]:
    return {
        "schema": 2,
        "kind": "professor-contact-stage3-state",
        "identity_version": "direction-id-v1",
        "generator_contract_version": "stage3-ideas-v2",
        "profile_path": str(profile_path.resolve()),
        "directions": [{
            "direction_id": DIRECTION_ID,
            "name_ja": "適応信号処理",
            "name_zh": "自适应信号处理",
            "candidates": [
                {
                    "id": "idea-001",
                    "direction_ids": [DIRECTION_ID],
                    "title": "Adaptive extension",
                    "one_liner": "Explore an adaptive extension of the synthetic processing setting.",
                    "research_question": "How can the synthetic setting adapt to changing conditions?",
                    "fit": "high",
                    "gap_refs": [],
                    "papers": [],
                },
                {
                    "id": "idea-002",
                    "direction_ids": [DIRECTION_ID],
                    "title": "Robust extension",
                    "one_liner": "Explore robustness under changing synthetic conditions.",
                    "research_question": "How robust is the synthetic setting under change?",
                    "fit": "medium",
                    "gap_refs": [],
                    "papers": [],
                },
            ],
        }],
        "cross_direction_groups": [],
        "validator": {"results": {DIRECTION_ID: {
            "result": "pass", "rounds": 1, "issues": []
        }}},
    }


def build_fixture(program_root: Path, profile_root: Path, *, output: Path) -> dict[str, Any]:
    program_root = Path(program_root).resolve()
    profile_root = Path(profile_root).resolve()
    if program_root == profile_root:
        raise FixtureBuildError("program and profile roots must be distinct")
    _prepare_root(program_root)
    try:
        _prepare_root(profile_root)
    except Exception:
        shutil.rmtree(program_root)
        raise

    _write_json(program_root / "info.json", {
        "schema": 1,
        "kind": "issue53-stage4-program",
        "program": "Synthetic Systems",
    })
    state_path = program_root / "教授研究/X分野/Example Professor/套磁候选状态.json"
    profile_path = profile_root / "套磁邮件/套磁信息.md"
    _write_json(state_path, _candidate_state(profile_path))
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        "# Synthetic applicant profile\n\n"
        "大学：Fixture University\n研究科：Synthetic Systems\n"
        "専攻：適応信号処理\n",
        encoding="utf-8",
    )

    input_hashes = {
        "info.json": sha256(program_root / "info.json"),
        "教授研究/X分野/Example Professor/套磁候选状态.json": sha256(state_path),
        "profile/套磁邮件/套磁信息.md": sha256(profile_path),
    }
    # Keep the manifest small and deterministic: it records the fixed input,
    # not a runtime output that the child may create.
    manifest = {
        "schema_version": 1,
        "builder": MANIFEST_ID,
        "fixture_kind": "stage4-only",
        "program_root": str(program_root),
        "profile_root": str(profile_root),
        "professor": PROFESSOR,
        "direction_id": DIRECTION_ID,
        "input_hashes": input_hashes,
        "forbidden_outputs": [SELECTION_FILE.as_posix(), EMAIL_INPUT_FILE.as_posix()],
        "manual_patch": "no",
    }
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output, manifest)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = build_fixture(args.program_root, args.profile_root, output=args.output)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({
        "status": "ok",
        "program_root": manifest["program_root"],
        "profile_root": manifest["profile_root"],
        "output": str(args.output.resolve()),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
