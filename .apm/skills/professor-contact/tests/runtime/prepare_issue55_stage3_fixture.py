#!/usr/bin/env python3
"""Build the producer-owned, pre-Stage-3 fixture for issue #55."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


MANIFEST_ID = "tests/runtime/prepare_issue55_stage3_fixture.py"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
ITEM_KEY = "PAPER0001"
GAP_ID = "GAP0001"
FORBIDDEN_OUTPUTS = (
    "教授研究/X分野/Example Professor/套磁候选状态.json",
    "教授研究/X分野/Example Professor/套磁想法候选.md",
    "教授研究/套磁想法候选总览.md",
    "教授研究/套磁选择.json",
    "教授研究/邮件输入.json",
)


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


def _prepare_root(root: Path) -> Path:
    prepared = support.prepare_root(root, description="fixture root")
    prepared.release()
    return prepared.path


def _stage2_input(professor_dir: Path) -> dict[str, Any]:
    quote = "Future work will investigate adaptation under changing conditions."
    gap = {
        "gap_id": GAP_ID,
        "item_key": ITEM_KEY,
        "status": "open",
        "quote": quote,
        "translation_zh": "未来工作将研究变化条件下的自适应。",
        "remaining_gap": "adaptation under changing conditions",
        "confidence": "high",
        "paper_title": "Adaptive Signal Processing in Synthetic Environments",
        "paper_year": 2025,
        "authorship": "corresponding",
    }
    return {
        "schema": 2,
        "kind": "professor-contact-stage2-input",
        "identity_version": "direction-id-v1",
        "managed_by": "contact_state",
        "professor": PROFESSOR,
        "professor_dir": str(professor_dir.resolve()),
        "papers": {
            ITEM_KEY: {
                "item_key": ITEM_KEY,
                "title": "Adaptive Signal Processing in Synthetic Environments",
                "year": 2025,
                "authorship": "corresponding",
                "analysis_file": str(professor_dir / "论文分析/PAPER0001.md"),
                "pdf_available": True,
                "facts_state": "valid",
                "facts_error": None,
                "paper_facts": {
                    "facts_file": str(professor_dir / "论文分析/PAPER0001.md.facts.json"),
                    "evidence_level": "fulltext",
                    "input_fingerprint": "sha256:" + "0" * 64,
                    "research_problem": "adaptation under distribution shift",
                    "research_object": "online adaptive filtering under synthetic shift",
                    "approach": "online adaptive filtering",
                    "findings": ["adaptive updating improves stability under synthetic shift"],
                    "contributions": ["a synthetic benchmark for adaptive filtering"],
                    "topic_terms": ["adaptive filtering", "distribution shift"],
                    "limitations": ["evaluation uses a synthetic environment"],
                    "source_anchors": {"approach": ["Synthetic fixture"]},
                    "confidence": 0.8,
                    "future_work_ids": [hashlib.sha256(quote.encode("utf-8")).hexdigest()],
                },
            },
        },
        "directions": [{
            "direction_id": DIRECTION_ID,
            "name_ja": "適応信号処理",
            "name_zh": "自适应信号处理",
            "status": "active",
            "input_fingerprint": "issue55-stage2-input-v1",
            "supporting_item_keys": [ITEM_KEY],
            "gap_shortlist": [gap],
            "gaps_excluded": [],
            "completed_gap_blacklist": [],
            "user_note": "",
            "red_lines": [],
        }],
        "cross_direction_groups": [],
    }


def build_fixture(program_root: Path, *, output: Path) -> dict[str, Any]:
    root = support.resolved_outside_producer(program_root, description="fixture root")
    professor_dir = root / "教授研究" / "X分野" / PROFESSOR
    info = root / "info.json"
    profile = root / "套磁邮件" / "套磁信息.md"
    input_pack = professor_dir / "套磁候选输入.json"
    manifest_path = support.ensure_new_output(
        output,
        reserved=[root, support.claim_path_for(root), info, profile, input_pack])

    root_prepared = support.prepare_root(root, description="fixture root")
    try:
        _write_json(info, {
            "schema_version": 1,
            "kind": "issue55-stage3-program",
            "program": "Synthetic Systems",
        })
        support.write_text(
            profile,
            "# Synthetic applicant profile\n\n"
            "研究兴趣：适应信号处理、分布变化下的稳健性。\n"
            "经验：使用 Python 进行信号处理实验与可复现分析。\n"
            "希望探索：在变化环境中如何保持在线模型的稳定适应。\n",
        )
        _write_json(input_pack, _stage2_input(professor_dir))

        input_hashes = {
            "info.json": sha256(info),
            "套磁邮件/套磁信息.md": sha256(profile),
            "教授研究/X分野/Example Professor/套磁候选输入.json": sha256(input_pack),
        }
        manifest = {
            "schema_version": 1,
            "builder": MANIFEST_ID,
            "fixture_kind": "issue55-stage3-pre",
            "program_root": str(root),
            "professor": PROFESSOR,
            "direction_id": DIRECTION_ID,
            "item_key": ITEM_KEY,
            "gap_id": GAP_ID,
            "input_hashes": input_hashes,
            "forbidden_outputs": list(FORBIDDEN_OUTPUTS),
            "stage1_stage2_runtime_artifacts": [],
            "manual_patch": "no",
            "network_used": False,
            "runtime_fixture_started": False,
        }
        support.write_json_exclusive(manifest_path, manifest)
    finally:
        root_prepared.release()
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = build_fixture(args.program_root, output=args.output)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({
        "status": "ok",
        "program_root": manifest["program_root"],
        "output": str(args.output.resolve()),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
