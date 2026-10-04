#!/usr/bin/env python3
"""Prepare the complete issue #67 PC67-RISO case before CASE_STARTED.

The producer-owned base fixture intentionally contains a legacy program-level
selection row for the valid professor.  PC67-RISO needs that professor to enter
normal local finalization rather than legacy migration, while the legacy global
containers must still exist as immutable history.  This preparer therefore
removes only that one legacy selection row, updates the manifest hashes, and
leaves the legacy email pack plus every professor-local input byte unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "prepare_issue67_stage4_isolation_fixture.py"
PREPARER_ID = "tests/runtime/prepare_issue67_riso_case.py"
LEGACY_SELECTION = Path("教授研究/套磁选择.json")
LEGACY_EMAIL = Path("教授研究/邮件输入.json")


def _load_base():
    spec = importlib.util.spec_from_file_location("issue67_riso_base_fixture", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base fixture builder: {BASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base()


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def prepare_case(program_root: Path, profile_root: Path, *,
                 source_output: Path, output: Path) -> dict[str, Any]:
    program_root = Path(program_root).resolve()
    source_output = Path(source_output).resolve()
    output = Path(output).resolve()
    source = base.build_fixture(program_root, profile_root, output=source_output)

    valid = [row for row in source.get("professors") or []
             if isinstance(row, dict) and row.get("role") == "valid"]
    if len(valid) != 1:
        raise RuntimeError(f"expected exactly one valid professor, got {len(valid)}")
    valid_dir = str(Path(valid[0]["canonical_professor_dir"]).resolve())

    selection_path = program_root / LEGACY_SELECTION
    selection_doc = json.loads(selection_path.read_text(encoding="utf-8"))
    rows = selection_doc.get("selections")
    if not isinstance(rows, list):
        raise RuntimeError("legacy selections must be a list")

    kept = []
    removed = 0
    for row in rows:
        if isinstance(row, dict) and row.get("professor_dir"):
            row_dir = str(Path(row["professor_dir"]).resolve())
            if row_dir == valid_dir:
                removed += 1
                continue
        kept.append(row)
    if removed != 1:
        raise RuntimeError(f"expected to remove exactly one valid legacy row, removed {removed}")
    selection_doc["selections"] = kept
    _write_json(selection_path, selection_doc)

    email_path = program_root / LEGACY_EMAIL
    if not email_path.is_file():
        raise RuntimeError("legacy email pack must remain present")

    manifest = json.loads(json.dumps(source))
    selection_key = LEGACY_SELECTION.as_posix()
    selection_sha = sha256(selection_path)
    manifest["legacy_program_pair"][selection_key] = selection_sha
    manifest["input_hashes"][selection_key] = selection_sha
    manifest["case_preparer"] = PREPARER_ID
    manifest["case_preparer_sha256"] = sha256(Path(__file__))
    manifest["source_manifest_sha256"] = sha256(source_output)
    manifest["derivation"] = {
        "removed_valid_legacy_selection_rows": removed,
        "valid_professor_dir": valid_dir,
        "legacy_email_sha256": sha256(email_path),
    }
    _write_json(output, manifest)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--source-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = prepare_case(
            args.program_root,
            args.profile_root,
            source_output=args.source_output,
            output=args.output,
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({
        "status": "ok",
        "program_root": manifest["program_root"],
        "source_output": str(args.source_output.resolve()),
        "output": str(args.output.resolve()),
        "removed_valid_legacy_selection_rows":
            manifest["derivation"]["removed_valid_legacy_selection_rows"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
