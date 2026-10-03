#!/usr/bin/env python3
"""Prepare the producer-owned, Stage-4-only fixture for issue #53."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


MANIFEST_ID = "tests/runtime/prepare_issue53_stage4_fixture.py"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
SELECTION_FILE = Path("教授研究/套磁选择.json")
EMAIL_INPUT_FILE = Path("教授研究/邮件输入.json")


def _load_fixture_support():
    module_path = Path(__file__).with_name("fixture_support.py").resolve()
    digest = hashlib.sha256(str(module_path).encode("utf-8")).hexdigest()[:16]
    name = f"professor_contact_fixture_support_{digest}"
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load_fixture_support()
FixtureBuildError = support.FixtureBuildError
sha256 = support.file_sha256
_write_json = support.write_json


def _producer_root() -> Path:
    return support.producer_root()


def _prepare_root(root: Path) -> None:
    support.prepare_root(root, description="fixture root")


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


def _rollback_prepared_root(prepared) -> None:
    """Remove the first root only when this call created it and still owns it."""
    if prepared.created:
        support.discard_created_root(prepared)


def build_fixture(program_root: Path, profile_root: Path, *, output: Path) -> dict[str, Any]:
    program = support.resolved_outside_producer(program_root, description="program root")
    profile = support.resolved_outside_producer(profile_root, description="profile root")
    support.check_roots_distinct(
        program, profile, first_label="program root", second_label="profile root")
    info_path = program / "info.json"
    state_path = program / "教授研究/X分野/Example Professor/套磁候选状态.json"
    profile_path = profile / "套磁邮件/套磁信息.md"
    manifest_path = support.ensure_new_output(
        output,
        reserved=[program, profile, info_path, state_path, profile_path])

    program_prepared = support.prepare_root(program, description="program root")
    try:
        support.prepare_root(profile, description="profile root")
    except BaseException:
        _rollback_prepared_root(program_prepared)
        raise

    _write_json(info_path, {
        "schema": 1,
        "kind": "issue53-stage4-program",
        "program": "Synthetic Systems",
    })
    _write_json(state_path, _candidate_state(profile_path))
    support.write_text(
        profile_path,
        "# Synthetic applicant profile\n\n"
        "大学：Fixture University\n研究科：Synthetic Systems\n"
        "専攻：適応信号処理\n",
    )

    input_hashes = {
        "info.json": sha256(info_path),
        "教授研究/X分野/Example Professor/套磁候选状态.json": sha256(state_path),
        "profile/套磁邮件/套磁信息.md": sha256(profile_path),
    }
    manifest = {
        "schema_version": 1,
        "builder": MANIFEST_ID,
        "fixture_kind": "stage4-only",
        "program_root": str(program),
        "profile_root": str(profile),
        "professor": PROFESSOR,
        "direction_id": DIRECTION_ID,
        "input_hashes": input_hashes,
        "forbidden_outputs": [SELECTION_FILE.as_posix(), EMAIL_INPUT_FILE.as_posix()],
        "manual_patch": "no",
    }
    support.write_json_exclusive(manifest_path, manifest)
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
