#!/usr/bin/env python3
"""Build the producer-owned raw fixture for issue #32/#40 runtime evaluation.

This builder deliberately stops before the first product-generated state.  It
creates synthetic upstream inputs, a legal direction preview, deterministic
synthetic PDFs, and the fixed email/profile inputs.  The installed
professor-contact runner must create every target, snapshot, analysis,
candidate, selection, evidence, and email artifact during the runtime run.

Issue #40 contract: the builder no longer owns fixed Zotero keys.  Callers
(the issue #40 runtime setup helper) pass the real disposable-Zotero item and
attachment keys via a versioned items config; the historical ``AAAA1111`` /
``BBBB2222`` constants are rejected wherever they appear so fake keys can
never masquerade as real library keys.
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
ITEMS_CONFIG_SCHEMA_VERSION = 1
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
# Forbidden as item/attachment keys: these literals were the pre-#40 hardcoded
# fixture keys.  They are never real Zotero keys and are rejected so a stale
# config cannot fake provenance.
LEGACY_ITEM_KEYS = ("AAAA1111", "BBBB2222")
# The fill target must sit in the product's formal retryable pre-download
# state (the ``pending -> downloaded`` collector state machine); anything else
# is not accepted as fill-target input.
RETRYABLE_FILL_STATUSES = ("pending",)
READY_PDF_STATUS = "downloaded"
FIXED_NOTE = "I want to study adaptive and nonlinear extensions of this processing framework."
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


def paper_metadata(role: str) -> dict:
    """Deterministic synthetic paper metadata for one fixture role.

    ``role`` is ``"ready"`` for an already-downloaded paper and ``"fill"``
    for the fill target whose PDF the runtime must collect.
    """
    catalog = {
        "ready": {
            "title": "Adaptive Processing in Synthetic Systems",
            "title_zh": "合成系统中的自适应处理",
            "year": 2024,
            "authors": [PROFESSOR, "Synthetic Researcher"],
            "abstract": "A deterministic synthetic paper about adaptive and nonlinear processing.",
        },
        "fill": {
            "title": "Nonlinear Extensions of Synthetic Processing",
            "title_zh": "合成处理的非线性扩展",
            "year": 2023,
            "authors": [PROFESSOR, "Synthetic Collaborator"],
            "abstract": "A synthetic paper whose PDF must be collected during Stage 1.",
        },
    }
    if role not in catalog:
        raise FixtureBuildError(f"unknown fixture paper role: {role!r}")
    return catalog[role]


def paper_pdf_bytes(item_key: str, role: str) -> bytes:
    """Deterministic PDF bytes for an item, shared by local inputs and the
    attachment imported into the disposable Zotero fixture."""
    meta = paper_metadata(role)
    return render_text_pdf([
        f"Synthetic paper: {meta['title']} ({item_key})",
        f"Abstract: {meta['abstract'][0].lower()}{meta['abstract'][1:]}",
        "Future work: extend the framework to nonlinear and adaptive settings.",
        "This deterministic PDF is producer-owned input, not a completed analysis.",
    ])


def load_items_config(source: Path | str | dict) -> dict:
    """Load and validate the dynamic Zotero items config (issue #40)."""
    if isinstance(source, dict):
        config = json.loads(json.dumps(source))
    else:
        path = Path(source)
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise FixtureBuildError(f"cannot read zotero items config: {path}") from exc
        except json.JSONDecodeError as exc:
            raise FixtureBuildError(f"zotero items config is not valid JSON: {path}: {exc}") from exc
    if not isinstance(config, dict):
        raise FixtureBuildError("zotero items config must be a JSON object")
    if config.get("schema_version") != ITEMS_CONFIG_SCHEMA_VERSION:
        raise FixtureBuildError(
            f"zotero items config schema_version must be {ITEMS_CONFIG_SCHEMA_VERSION}")

    def _string_list(name: str) -> list[str]:
        value = config.get(name)
        if not isinstance(value, list) or not value or \
                not all(isinstance(row, str) and row.strip() for row in value):
            raise FixtureBuildError(f"zotero items config.{name} must be a non-empty string list")
        return list(value)

    item_keys = _string_list("item_keys")
    ready_item_keys = _string_list("ready_item_keys")
    fill_target = config.get("fill_target_item_key")
    if not isinstance(fill_target, str) or not fill_target.strip():
        raise FixtureBuildError("zotero items config.fill_target_item_key must be a non-empty string")
    run_id = config.get("fixture_run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise FixtureBuildError("zotero items config.fixture_run_id must be a non-empty string")
    if len(set(item_keys)) != len(item_keys):
        raise FixtureBuildError("zotero items config.item_keys contains duplicates")
    legacy = sorted(set(item_keys) & set(LEGACY_ITEM_KEYS))
    if legacy:
        raise FixtureBuildError(
            f"zotero items config reuses forbidden hardcoded fixture keys: {legacy}")
    unknown_ready = sorted(set(ready_item_keys) - set(item_keys))
    if unknown_ready:
        raise FixtureBuildError(f"ready_item_keys outside item_keys: {unknown_ready}")
    if fill_target not in item_keys:
        raise FixtureBuildError(f"fill_target_item_key {fill_target!r} is not in item_keys")
    if fill_target in ready_item_keys:
        raise FixtureBuildError("fill_target_item_key must not also be a ready item key")
    if len(item_keys) < 2 or not ready_item_keys:
        raise FixtureBuildError(
            "runtime fixture requires at least one ready item and one distinct fill target")
    status = config.get("fill_target_pdf_status")
    if status not in RETRYABLE_FILL_STATUSES:
        raise FixtureBuildError(
            f"fill_target_pdf_status must be one of {list(RETRYABLE_FILL_STATUSES)}, got {status!r}")
    attachment_keys = config.get("attachment_keys")
    if not isinstance(attachment_keys, dict) or not attachment_keys:
        raise FixtureBuildError(
            "zotero items config.attachment_keys must map every item key to a real attachment key")
    for key, attachment in attachment_keys.items():
        if key not in item_keys:
            raise FixtureBuildError(f"attachment_keys references unknown item key: {key}")
        if not isinstance(attachment, str) or not attachment.strip():
            raise FixtureBuildError(f"attachment key for {key} must be a non-empty string")
        if attachment in LEGACY_ITEM_KEYS:
            raise FixtureBuildError(f"attachment key for {key} reuses a forbidden fixture key")
    missing_attachments = sorted(set(item_keys) - set(attachment_keys))
    if missing_attachments:
        raise FixtureBuildError(f"attachment_keys missing entries for: {missing_attachments}")
    return {
        "schema_version": ITEMS_CONFIG_SCHEMA_VERSION,
        "fixture_run_id": run_id,
        "item_keys": item_keys,
        "ready_item_keys": ready_item_keys,
        "fill_target_item_key": fill_target,
        "fill_target_pdf_status": status,
        "attachment_keys": dict(attachment_keys),
    }


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


def _write_inputs(program_root: Path, profile_root: Path, items: dict) -> dict[str, str]:
    item_keys = items["item_keys"]
    ready_keys = set(items["ready_item_keys"])
    fill_target = items["fill_target_item_key"]
    fill_status = items["fill_target_pdf_status"]
    professor_dir = program_root / "教授研究" / "X分野" / PROFESSOR
    analysis_dir = professor_dir / "论文分析"
    analysis_dir.mkdir(parents=True, exist_ok=True)
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
            "members": [{"item_key": key, "preview_confidence": "high"} for key in item_keys],
            "representatives": [{"item_key": item_keys[0]}],
        }],
    }
    _write_json(program_root / preview_relative, preview)
    papers = []
    for key in item_keys:
        role = "ready" if key in ready_keys else "fill"
        meta = paper_metadata(role)
        row = {
            "item_key": key,
            "title": meta["title"],
            "title_zh": meta["title_zh"],
            "year": meta["year"],
            "authors": meta["authors"],
            "abstract": meta["abstract"],
        }
        if role == "ready":
            row["pdf_status"] = READY_PDF_STATUS
            row["pdf_path"] = f"论文分析/{key}.pdf"
        else:
            row["pdf_status"] = fill_status
        papers.append(row)
    _write_json(professor_dir / "papers.json", {"papers": papers})
    for key in sorted(ready_keys):
        (analysis_dir / f"{key}.pdf").write_bytes(paper_pdf_bytes(key, "ready"))
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
    _write_json(program_root / "教授研究" / "contact-evidence-fixture-input.json", {
        "schema_version": 1,
        "kind": "synthetic-contact-evidence-input",
        "professor": PROFESSOR,
        "official_only": {
            "email": "faculty@example.edu",
            "url": "https://example.test/faculty/example-professor",
            "source": "synthetic official faculty page",
        },
    })

    profile_root.mkdir(parents=True, exist_ok=True)
    (profile_root / "套磁邮件").mkdir(parents=True, exist_ok=True)
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
    (profile_root / "套磁邮件" / "套磁信息.md").write_text(profile, encoding="utf-8")
    (profile_root / "套磁邮件" / "套磁模板.md").write_text(
        "{{大学}}／{{研究科}}／{{先生名}}先生\n\n"
        "{{出身校}}出身の{{氏名}}（{{入学年度}}年{{入学月}}月、{{専攻}}、{{学位}}）です。\n"
        "{{兴趣段}} {{未来志向}} {{学習中}} {{志望}}\n", encoding="utf-8")
    (profile_root / "套磁邮件" / "套磁跟进模板.md").write_text(
        "{{先生名}}先生（{{大学}}／{{研究科}}）\n\n"
        "{{学位}}の{{氏名}}です。{{出身校}}出身で、{{初回送信日}}に初回連絡しました。\n"
        "研究主题：{{研究主题}}\n連絡先：{{メールアドレス}}\n", encoding="utf-8")
    return _tree_hashes(program_root)


def build_fixture(program_root: Path, profile_root: Path, zotero_items_config=None, *,
                  consumer_root: Path | None = None, professor_research_sha: str = "",
                  zotero_http_url: str = "", zotero_mcp_url: str = "") -> dict:
    """Build raw fixture inputs bound to real disposable-Zotero keys.

    ``zotero_items_config`` (path or dict) carries the dynamic item /
    attachment keys returned by the issue #40 setup helper; it is required so
    the builder can never fall back to fabricated keys.
    """
    if zotero_items_config is None:
        raise FixtureBuildError(
            "zotero_items_config is required: the builder no longer owns Zotero keys")
    items = load_items_config(zotero_items_config)
    program_root = Path(program_root).resolve()
    profile_root = Path(profile_root).resolve()
    _prepare_output(program_root)
    program_hashes = _write_inputs(program_root, profile_root, items)
    manifest = {
        "schema_version": 1,
        "builder": MANIFEST_ID,
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fixture_mode": "initial_raw_inputs",
        "fixture_run_id": items["fixture_run_id"],
        "program_root": str(program_root),
        "profile_root": str(profile_root),
        "consumer_root": str(Path(consumer_root).resolve()) if consumer_root else None,
        "professor": PROFESSOR,
        "direction_ids": [DIRECTION_ID],
        "item_keys": items["item_keys"],
        "ready_item_keys": items["ready_item_keys"],
        "fill_target_item_key": items["fill_target_item_key"],
        "fill_target_pdf_status": items["fill_target_pdf_status"],
        "missing_item_keys": [items["fill_target_item_key"]],
        "attachment_keys": items["attachment_keys"],
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
    parser.add_argument("--zotero-items-config", type=Path, required=True,
                        help="JSON file with the real disposable-Zotero item/attachment keys")
    parser.add_argument("--consumer-root", type=Path)
    parser.add_argument("--professor-research-sha", default="")
    parser.add_argument("--zotero-http-url", default="")
    parser.add_argument("--zotero-mcp-url", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = build_fixture(
            args.program_root, args.profile_root,
            zotero_items_config=args.zotero_items_config,
            consumer_root=args.consumer_root,
            professor_research_sha=args.professor_research_sha,
            zotero_http_url=args.zotero_http_url, zotero_mcp_url=args.zotero_mcp_url)
    except Exception as exc:  # CLI callers need machine-readable failure.
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "program_root": manifest["program_root"],
                      "profile_root": manifest["profile_root"], "manifest": MANIFEST_NAME},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
