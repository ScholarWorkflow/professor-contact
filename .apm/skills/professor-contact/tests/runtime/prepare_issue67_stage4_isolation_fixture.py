#!/usr/bin/env python3
"""Prepare the producer-owned, Stage-4-only fixture for issue #67 (PC67-RISO).

The fixture carries two professors whose display name is identical and whose
only difference is the canonical professor directory: one carries a canonical
Stage-3 state, the other carries a single fixed malformed canonical
candidate-state file.  A legacy program-level Stage-4 pair is present as
history only, so the run must show that an unrelated professor never blocks a
valid one and that the legacy container never regains authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


MANIFEST_ID = "tests/runtime/prepare_issue67_stage4_isolation_fixture.py"
DIRECTION_ID = "DIR00001"
COLLECTION_KEY = "DIR00001"
DISPLAY_NAME = "Isolation Professor"
ITEM_KEY = "ISSUE67AAA1"
GAP_ID = "GAP0001"
INPUT_FINGERPRINT = "issue67-fixture-input-fingerprint"
LEGACY_DIRECTION_ID = "DIR99999"
LEGACY_IDEA_ID = "legacy-idea-not-current"
PROFILE_RELATIVE = Path("套磁邮件/套磁信息.md")

# Both professors share this display name on purpose: the transaction boundary
# under test is the canonical professor directory, not the name.
PROFESSORS = (
    {
        "role": "valid",
        "field": "AL分野",
        "directory": "isolation-alpha",
        "idea_id": "issue67-alpha-1",
    },
    {
        "role": "malformed_candidate_state",
        "field": "BE分野",
        "directory": "isolation-beta",
        "idea_id": "issue67-beta-1",
    },
)

# The single fault: bytes that parse as JSON but are not a canonical Stage-3
# candidate state (identity_version is outside the direction-id-v1 contract, so
# the producer can only fail this professor and leave the file untouched).
MALFORMED_CANDIDATE_STATE_BYTES = (
    b"{\n"
    b"  \"schema\": 2,\n"
    b"  \"kind\": \"professor-contact-stage3-state\",\n"
    b"  \"identity_version\": \"direction-id-v0-not-canonical\",\n"
    b"  \"directions\": [],\n"
    b"  \"note\": \"issue67 frozen malformed canonical candidate-state fault\"\n"
    b"}\n"
)


class FixtureBuildError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _producer_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _prepare_root(root: Path) -> None:
    root = Path(root).resolve()
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


def _input_pack(professor_dir: Path) -> dict[str, Any]:
    return {
        "schema": 2,
        "kind": "professor-contact-stage2-input",
        "identity_version": "direction-id-v1",
        "professor": DISPLAY_NAME,
        "professor_dir": str(professor_dir),
        "papers": {
            ITEM_KEY: {
                "item_key": ITEM_KEY,
                "title": "A synthetic fixture paper for issue 67",
                "year": 2025,
                "authorship": "Fixture Author",
            },
        },
        "directions": [{
            "direction_id": DIRECTION_ID,
            "collection_key": COLLECTION_KEY,
            "name_ja": "適応信号処理",
            "name_zh": "自适应信号处理",
            "input_fingerprint": INPUT_FINGERPRINT,
            "supporting_item_keys": [ITEM_KEY],
            "named_keys": [ITEM_KEY],
            "resolved_addition_keys": [],
            "gap_shortlist": [{
                "item_key": ITEM_KEY,
                "gap_id": GAP_ID,
                "paper_title": "A synthetic fixture paper for issue 67",
                "paper_year": 2025,
                "authorship": "Fixture Author",
                "quote": "Adaptation was left for future work.",
                "translation_zh": "自适应部分留作后续工作。",
                "source": "discussion",
                "page": "9",
                "status": "unknown",
                "evidence": "The authors state adaptation is future work.",
                "confidence": "medium",
                "completed_part": None,
                "remaining_gap": "Adaptation under changing conditions.",
            }],
            "gaps_excluded": [],
            "completed_gap_blacklist": [],
            "red_lines": [],
            "narrative": {"positioning": []},
            "user_note": "",
        }],
    }


def _candidate_state(professor_dir: Path, profile_path: Path, profile_sha: str,
                     idea_id: str) -> dict[str, Any]:
    return {
        "schema": 2,
        "kind": "professor-contact-stage3-state",
        "identity_version": "direction-id-v1",
        "generator_contract_version": "stage3-ideas-v2",
        "profile_path": str(profile_path.resolve()),
        "profile_fingerprint": profile_sha,
        "input_fingerprints": {DIRECTION_ID: INPUT_FINGERPRINT},
        "directions": [{
            "direction_id": DIRECTION_ID,
            "name_ja": "適応信号処理",
            "name_zh": "自适应信号处理",
            "zotero_collection": "Fixture Collection",
            "stage3_status": "ready",
            "generator_contract_version": "stage3-ideas-v2",
            "candidates": [{
                "id": idea_id,
                "direction_ids": [DIRECTION_ID],
                "title": "Adaptive extension",
                "one_liner": "Explore an adaptive extension of the synthetic setting.",
                "research_question": "How can the synthetic setting adapt to change?",
                "idea_zh": "把合成设定扩展到自适应场景。",
                "fit": "high",
                "gap_refs": [{"direction_id": DIRECTION_ID, "item_key": ITEM_KEY,
                              "gap_id": GAP_ID}],
                "papers": [{"item_key": ITEM_KEY, "direction_ids": [DIRECTION_ID],
                            "role": "基座", "fit_note": "教授通讯"}],
            }],
        }],
        "cross_direction_groups": [],
        "validator": {"results": {DIRECTION_ID: {"result": "pass", "rounds": 1,
                                                 "issues": []}}},
    }


def _legacy_program_pair(program_root: Path) -> dict[str, dict[str, Any]]:
    """History-only schema-2 container that contradicts the current facts."""
    selection = {
        "schema": 2,
        "kind": "professor-contact-selection",
        "identity_version": "direction-id-v1",
        "managed_by": "contact_state.py",
        "professor": DISPLAY_NAME,
        "selections": [{
            "professor": DISPLAY_NAME,
            "professor_dir": str(program_root / "教授研究" / "AL分野" / "isolation-alpha"),
            "direction_ids": [LEGACY_DIRECTION_ID],
            "collection_key": LEGACY_DIRECTION_ID,
            "ideas": [{"id": LEGACY_IDEA_ID, "note": ""}],
        }],
    }
    email_pack = {
        "schema": 2,
        "kind": "professor-contact-email-input",
        "identity_version": "direction-id-v1",
        "managed_by": "contact_state.py",
        "professor": DISPLAY_NAME,
        "emails": [{
            "email_id": f"{DISPLAY_NAME}::{LEGACY_DIRECTION_ID}::{LEGACY_IDEA_ID}",
            "professor": DISPLAY_NAME,
            "direction_ids": [LEGACY_DIRECTION_ID],
            "idea": {"id": LEGACY_IDEA_ID, "title": "Legacy idea, not in current state"},
            "papers": [],
            "gaps": [],
        }],
    }
    return {"教授研究/套磁选择.json": selection, "教授研究/邮件输入.json": email_pack}


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

    profile_path = profile_root / PROFILE_RELATIVE
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        "# Synthetic applicant profile\n\n"
        "大学：Fixture University\n研究科：Synthetic Systems\n"
        "専攻：適応信号処理\n",
        encoding="utf-8",
    )
    profile_sha = sha256(profile_path)

    _write_json(program_root / "info.json", {
        "schema": 1,
        "kind": "issue67-stage4-isolation-program",
        "program": "Synthetic Systems",
    })

    professors: list[dict[str, Any]] = []
    input_hashes: dict[str, str] = {"info.json": sha256(program_root / "info.json")}
    forbidden_outputs: list[str] = []
    fault: dict[str, Any] | None = None
    for spec in PROFESSORS:
        professor_dir = program_root / "教授研究" / spec["field"] / spec["directory"]
        professor_dir.mkdir(parents=True, exist_ok=True)
        pack_path = professor_dir / "套磁候选输入.json"
        state_path = professor_dir / "套磁候选状态.json"
        _write_json(pack_path, _input_pack(professor_dir))
        if spec["role"] == "malformed_candidate_state":
            state_path.write_bytes(MALFORMED_CANDIDATE_STATE_BYTES)
        else:
            _write_json(state_path, _candidate_state(professor_dir, profile_path,
                                                     profile_sha, spec["idea_id"]))
        state_is_malformed = spec["role"] == "malformed_candidate_state"
        relative_dir = Path("教授研究") / spec["field"] / spec["directory"]
        professors.append({
            "role": spec["role"],
            "professor": DISPLAY_NAME,
            "field": spec["field"],
            "relative_path": relative_dir.as_posix(),
            "professor_dir": str(professor_dir),
            "canonical_professor_dir": str(professor_dir.resolve()),
            "idea_id": spec["idea_id"],
            "direction_id": DIRECTION_ID,
            "input_pack": {"relative_path": "套磁候选输入.json",
                           "sha256": sha256(pack_path),
                           "canonical": True},
            "candidate_state": {"relative_path": "套磁候选状态.json",
                                "sha256": sha256(state_path),
                                "canonical": not state_is_malformed},
        })
        input_hashes[f"{relative_dir.as_posix()}/套磁候选输入.json"] = sha256(pack_path)
        input_hashes[f"{relative_dir.as_posix()}/套磁候选状态.json"] = sha256(state_path)
        forbidden_outputs.extend([
            f"{relative_dir.as_posix()}/套磁选择.json",
            f"{relative_dir.as_posix()}/邮件输入.json",
        ])
        if state_is_malformed:
            fault = {
                "professor_dir": str(professor_dir),
                "canonical_professor_dir": str(professor_dir.resolve()),
                "relative_path": "套磁候选状态.json",
                "kind": "malformed_canonical_candidate_state",
                "expected_reason_code": "invalid_candidate_state",
                "sha256": sha256(state_path),
                "spec_sha256": sha256_bytes(MALFORMED_CANDIDATE_STATE_BYTES),
            }
    if fault is None or len(professors) != 2:
        raise FixtureBuildError("fixture must declare exactly two professors and one fault")

    legacy = _legacy_program_pair(program_root)
    legacy_hashes: dict[str, str] = {}
    for relative, document in legacy.items():
        path = program_root / relative
        _write_json(path, document)
        legacy_hashes[relative] = sha256(path)
        input_hashes[relative] = sha256(path)

    manifest = {
        "schema_version": 1,
        "builder": MANIFEST_ID,
        "builder_sha256": sha256(Path(__file__)),
        "fixture_kind": "stage4-isolation",
        "program_root": str(program_root),
        "profile_root": str(profile_root),
        "profile_file": str(profile_path),
        "profile_sha256": profile_sha,
        "direction_id": DIRECTION_ID,
        "item_key": ITEM_KEY,
        "gap_id": GAP_ID,
        "input_fingerprint": INPUT_FINGERPRINT,
        "display_name": DISPLAY_NAME,
        "professors": professors,
        "fault": fault,
        "legacy_program_pair": legacy_hashes,
        "input_hashes": input_hashes,
        "forbidden_outputs": forbidden_outputs,
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
