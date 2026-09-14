#!/usr/bin/env python3
"""Build the producer-owned raw fixture for issue #32's runtime evaluation.

This builder deliberately stops before the first product-generated state.  It
creates synthetic upstream inputs, a legal direction preview, one ready PDF,
one fill-target paper, and the fixed email/profile inputs.  The installed
professor-contact runner must create every target, snapshot, analysis,
candidate, selection, evidence, and email artifact during the runtime run.

Zotero item keys are never hardcoded: the Test Recipe setup creates the
disposable-Zotero items through the owner write surface, records the real
keys in a ``zotero-items.json`` config, and this builder consumes that config
(issue #40 §4.1).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

MANIFEST_NAME = "fixture-manifest.json"
MANIFEST_ID = "tests/runtime/build_issue32_e2e_fixture.py"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
FIXED_NOTE = "I want to study adaptive and nonlinear extensions of this processing framework."
# The ready paper ships a deterministic local PDF; the fill target must carry a
# retry state the collector contract actually emits (issue #40 §4.2).  The
# historical `missing` value is deliberately not accepted.
READY_PDF_STATUS = "downloaded"
RETRYABLE_PDF_STATUSES = ("pending", "failed", "no_env", "deferred")
ITEMS_CONFIG_NAME = "zotero-items.json"
FORBIDDEN_STAGE_OUTPUTS = (
    Path("教授研究/套磁目标.json"),
    Path("教授研究/套磁阶段1候选.json"),
    Path("教授研究/X分野/Example Professor/套磁候选输入.json"),
    Path("教授研究/X分野/Example Professor/套磁候选状态.json"),
    Path("教授研究/X分野/Example Professor/套磁选择.json"),
    Path("教授研究/X分野/Example Professor/邮件输入.json"),
)


class FixtureBuildError(RuntimeError):
    pass


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def render_text_pdf(lines: list[str]) -> bytes:
    """Return a deterministic, parseable one-page text PDF."""
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
               for line in lines]
    commands = ["BT", "/F1 11 Tf", "72 748 Td"]
    for index, line in enumerate(escaped):
        if index:
            commands.append("0 -16 Td")
        commands.append(f"({line}) Tj")
    commands.append("ET")
    stream = ("\n".join(commands) + "\n").encode("ascii")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"5 0 obj\n<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream + b"endstream\nendobj\n",
    ]
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body.extend(obj)
    xref = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    body.extend((f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                 f"startxref\n{xref}\n%%EOF\n").encode("ascii"))
    return bytes(body)


def _producer_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _prepare_output(root: Path) -> None:
    root = root.resolve()
    if root.exists():
        manifest_path = root / MANIFEST_NAME
        if not manifest_path.is_file():
            raise FixtureBuildError(f"refusing to replace non-fixture directory: {root}")
        try:
            prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FixtureBuildError(f"cannot read prior fixture manifest: {manifest_path}") from exc
        if prior.get("builder") != MANIFEST_ID:
            raise FixtureBuildError(f"fixture belongs to another builder: {root}")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=False)


def _tree_hashes(root: Path, *, exclude: set[str] | None = None) -> dict[str, str]:
    excluded = exclude or set()
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    }


def load_zotero_items_config(path: Path) -> dict:
    """Parse and validate the dynamic Zotero item config written by setup."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureBuildError(f"cannot read zotero items config {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise FixtureBuildError(f"zotero items config must be an object: {path}")
    item_keys = payload.get("item_keys")
    ready_keys = payload.get("ready_item_keys")
    fill_target = payload.get("fill_target_item_key")
    for name, value in (("item_keys", item_keys), ("ready_item_keys", ready_keys)):
        if (not isinstance(value, list) or not value
                or not all(isinstance(key, str) and key for key in value)
                or len(set(value)) != len(value)):
            raise FixtureBuildError(f"zotero items config: {name} must be unique non-empty strings")
    if not isinstance(fill_target, str) or not fill_target:
        raise FixtureBuildError("zotero items config: fill_target_item_key is required")
    unknown = [key for key in ([fill_target] + list(ready_keys)) if key not in item_keys]
    if unknown:
        raise FixtureBuildError(f"zotero items config: keys not in item_keys: {unknown}")
    if fill_target in ready_keys:
        raise FixtureBuildError("zotero items config: fill target cannot also be a ready key")
    fill_status = payload.get("fill_target_pdf_status", "pending")
    if fill_status not in RETRYABLE_PDF_STATUSES:
        raise FixtureBuildError(
            "zotero items config: fill_target_pdf_status must be one of "
            f"{list(RETRYABLE_PDF_STATUSES)}, got {fill_status!r}")
    return {
        "item_keys": list(item_keys),
        "ready_item_keys": list(ready_keys),
        "fill_target_item_key": fill_target,
        "fill_target_pdf_status": fill_status,
        "fixture_run_id": str(payload.get("fixture_run_id", "")),
    }


def _write_inputs(program_root: Path, profile_root: Path, items: dict) -> dict[str, str]:
    professor_dir = program_root / "教授研究" / "X分野" / PROFESSOR
    analysis_dir = professor_dir / "论文分析"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    ready_keys = items["ready_item_keys"]
    fill_key = items["fill_target_item_key"]
    fill_status = items["fill_target_pdf_status"]
    preview_relative = Path("教授研究/X分野/Example Professor/方向预筛.json")
    preview = {
        "schema_version": 1,
        "professor": PROFESSOR,
        "preview_fingerprint": "issue32-preview-v1",
        "preview_fingerprint_version": "v1",
        "direction_id_version": "v1",
        "membership_mode": "overlap_allowed",
        "directions": [{
            "direction_id": DIRECTION_ID,
            "member_fingerprint": "issue32-members-v1",
            "name_ja": "Adaptive and nonlinear processing",
            "name_zh": "自适应与非线性处理",
            "summary_zh": "Synthetic direction for the issue #32 runtime contract.",
            "user_note": FIXED_NOTE,
            "members": [{"item_key": key, "preview_confidence": "high"}
                        for key in items["item_keys"]],
            "representatives": [{"item_key": ready_keys[0]}],
        }],
    }
    _write_json(program_root / preview_relative, preview)
    papers = {"papers": []}
    for key in items["item_keys"]:
        row = {
            "item_key": key,
            "title": f"Synthetic Processing Study {key}",
            "title_zh": "合成处理研究",
            "year": 2024,
            "authors": [PROFESSOR, "Synthetic Researcher"],
            "abstract": "A deterministic synthetic paper about adaptive and nonlinear processing.",
        }
        if key in ready_keys:
            row["pdf_status"] = READY_PDF_STATUS
            row["pdf_path"] = f"论文分析/{key}.pdf"
        elif key == fill_key:
            row["pdf_status"] = fill_status
        else:
            row["pdf_status"] = "pending"
        papers["papers"].append(row)
    _write_json(professor_dir / "papers.json", papers)
    for key in ready_keys:
        (analysis_dir / f"{key}.pdf").write_bytes(render_text_pdf([
            f"Synthetic paper: Synthetic Processing Study {key}",
            "Abstract: adaptive and nonlinear processing is evaluated.",
            "Future work: extend the framework to nonlinear and adaptive settings.",
            "This deterministic PDF is producer-owned input, not a completed analysis.",
        ]))
    _write_json(program_root / "info.json", {
        "schema_version": 1,
        "program": "issue32-stage0-5-runtime-fixture",
        "source": "synthetic producer input",
        "university": "Fixture University A",
        "department": "Synthetic Systems",
        "target": {"intake_year": 2027, "intake_term": "april"},
    })
    _write_json(program_root / "boshu_analysis.json", {
        "schema_version": 1,
        "research_area": "adaptive and nonlinear processing",
        "requirements": ["research fit", "future direction", "contact evidence"],
        "exam_type": {
            "degree": "Master of Science",
            "selection_name": "Spring Synthetic Systems Selection",
        },
    })

    # Raw contact sources in exactly the shapes the owner's
    # contact_evidence.py consumes; no owner-less fixture input and never a
    # pre-built evidence artifact (issue #40 §4.4).
    _write_json(program_root / "教授研究" / "_professor_candidates.json", [
        {
            "name": PROFESSOR,
            "email": "faculty@example.edu",
            "source": "synthetic official faculty page",
        },
    ])
    _write_json(program_root / "教授研究" / "_corresp_cache.json", {})
    _write_json(program_root / "教授研究" / "_署名对照.json", {})

    profile_root.mkdir(parents=True, exist_ok=True)
    profile = """# Applicant profile

大学：Fixture University A
研究科：Synthetic Systems
先生名：Example Professor
出身校：Fixture University B
氏名：Fixture Applicant
入学年度：2026
入学月：4
専攻：Adaptive and nonlinear processing
学位：Master of Science
兴趣段：I am interested in your work on adaptive processing.
未来志向：I hope to study nonlinear extensions of this framework.
学習中：I am studying reproducible research workflows.
志望：I would like to contribute to your laboratory.
研究主题：Adaptive and nonlinear processing
邮件アドレス：faculty@example.edu
"""
    (profile_root / "套磁信息.md").write_text(profile, encoding="utf-8")
    (profile_root / "套磁模板.md").write_text(
        "{{大学}}／{{研究科}}／{{先生名}}先生\n\n"
        "{{出身校}}出身の{{氏名}}（{{入学年度}}年{{入学月}}月、{{専攻}}、{{学位}}）です。\n"
        "{{兴趣段}} {{未来志向}} {{学習中}} {{志望}}\n", encoding="utf-8")
    (profile_root / "套磁跟进模板.md").write_text(
        "{{先生名}}先生（{{大学}}／{{研究科}}）\n\n"
        "{{学位}}の{{氏名}}です。{{出身校}}出身で、{{初回送信日}}に初回連絡しました。\n"
        "研究主题：{{研究主题}}\n連絡先：{{メールアドレス}}\n", encoding="utf-8")
    return _tree_hashes(program_root)


def build_fixture(program_root: Path, profile_root: Path, *, consumer_root: Path | None = None,
                  professor_research_sha: str = "", zotero_http_url: str = "",
                  zotero_mcp_url: str = "",
                  zotero_items_config: Path | None = None) -> dict:
    if zotero_items_config is None:
        raise FixtureBuildError(
            f"zotero items config is required (setup-written {ITEMS_CONFIG_NAME})")
    items = load_zotero_items_config(Path(zotero_items_config))
    program_root = Path(program_root).resolve()
    profile_root = Path(profile_root).resolve()
    _prepare_output(program_root)
    program_hashes = _write_inputs(program_root, profile_root, items)
    manifest = {
        "schema_version": 1,
        "builder": MANIFEST_ID,
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fixture_mode": "initial_raw_inputs",
        "program_root": str(program_root),
        "profile_root": str(profile_root),
        "consumer_root": str(Path(consumer_root).resolve()) if consumer_root else None,
        "professor": PROFESSOR,
        "direction_ids": [DIRECTION_ID],
        "item_keys": items["item_keys"],
        "ready_item_keys": items["ready_item_keys"],
        "fill_target_item_key": items["fill_target_item_key"],
        "fill_target_pdf_status": items["fill_target_pdf_status"],
        "fixture_run_id": items["fixture_run_id"],
        "professor_research_sha": professor_research_sha,
        "zotero_http_url": zotero_http_url,
        "zotero_mcp_url": zotero_mcp_url,
        "protected_files": program_hashes,
        "profile_files": _tree_hashes(profile_root),
        "forbidden_product_outputs": [path.as_posix() for path in FORBIDDEN_STAGE_OUTPUTS],
    }
    _write_json(program_root / MANIFEST_NAME, manifest)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--consumer-root", type=Path)
    parser.add_argument("--professor-research-sha", default="")
    parser.add_argument("--zotero-http-url", default="")
    parser.add_argument("--zotero-mcp-url", default="")
    parser.add_argument("--zotero-items-config", type=Path, required=True,
                        help=f"setup-written {ITEMS_CONFIG_NAME} with the real disposable-Zotero keys")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = build_fixture(
            args.program_root, args.profile_root, consumer_root=args.consumer_root,
            professor_research_sha=args.professor_research_sha,
            zotero_http_url=args.zotero_http_url, zotero_mcp_url=args.zotero_mcp_url,
            zotero_items_config=args.zotero_items_config)
    except Exception as exc:  # CLI callers need machine-readable failure.
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "program_root": manifest["program_root"],
                      "profile_root": manifest["profile_root"], "manifest": MANIFEST_NAME},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
