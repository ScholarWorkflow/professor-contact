#!/usr/bin/env python3
"""Build the producer-owned raw fixture for issue #32's Stage 0–5 E2E.

This builder deliberately stops before the first product-generated state.  It
creates synthetic upstream inputs, a legal direction preview, one catalog paper
whose PDF is still pending, and the fixed email/profile inputs.  The installed
professor-contact runner must create every target, snapshot, analysis,
candidate, selection, evidence, and email artifact during the E2E run.

The #40/#47 canonical fixture carries exactly one item so R1 fills and R2
analyzes the same paper, which is what makes the Stage 1 -> Stage 2 continuity
gate observable instead of satisfiable by a pre-ready second paper.
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
CANONICAL_ITEM_KEY = "AAAA1111"
CANONICAL_PAPER_TITLE = "Adaptive Processing in Synthetic Systems"
CANONICAL_PAPER_TITLE_ZH = "合成系统中的自适应处理"
CANONICAL_PAPER_YEAR = 2024
CANONICAL_PAPER_AUTHORS = (PROFESSOR, "Synthetic Researcher")
CANONICAL_PAPER_ABSTRACT = (
    "A deterministic synthetic paper about adaptive and nonlinear processing.")
CANONICAL_PUBLICATION_TITLE = "Synthetic Processing Journal"
CANONICAL_PDF_LINES = (
    "Synthetic paper: Adaptive Processing in Synthetic Systems",
    "Abstract: adaptive and nonlinear processing is evaluated.",
    "Future work: extend the framework to nonlinear and adaptive settings.",
    "This deterministic PDF is producer-owned input, not a completed analysis.",
)
FIXED_NOTE = "I want to study adaptive and nonlinear extensions of this processing framework."
FORBIDDEN_STAGE_OUTPUTS = (
    Path("教授研究/套磁阶段1候选.json"),
    Path("教授研究/套磁选择.json"),
    Path("教授研究/邮件输入.json"),
    Path("教授研究/X分野/Example Professor/套磁目标.json"),
    Path("教授研究/X分野/Example Professor/套磁候选输入.json"),
    Path("教授研究/X分野/Example Professor/套磁候选状态.json"),
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


def _write_inputs(program_root: Path, profile_root: Path,
                  item_key: str = CANONICAL_ITEM_KEY) -> dict[str, str]:
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
            "members": [{"item_key": item_key, "preview_confidence": "high"}],
            "representatives": [{"item_key": item_key}],
        }],
    }
    _write_json(program_root / preview_relative, preview)
    # The single catalog row stays ``pending`` on purpose: the deterministic PDF
    # lives in the disposable Zotero as an attachment, so Stage 1 must collect it
    # before Stage 2 can analyze the same item.
    papers = {
        "papers": [{
            "item_key": item_key,
            "title": CANONICAL_PAPER_TITLE,
            "title_zh": CANONICAL_PAPER_TITLE_ZH,
            "year": CANONICAL_PAPER_YEAR,
            "authors": list(CANONICAL_PAPER_AUTHORS),
            "abstract": CANONICAL_PAPER_ABSTRACT,
            "pdf_status": "pending",
        }]
    }
    _write_json(professor_dir / "papers.json", papers)
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
    # Seed the real professor-research input contract as well as the
    # human-readable fixture provenance above.  The collector's deterministic
    # contact-evidence rebuild consumes _professor_candidates.json; the
    # fixture-only file is deliberately not a production input surface.
    _write_json(program_root / "教授研究" / "_professor_candidates.json", [{
        "name": PROFESSOR,
        "email": "faculty@example.edu",
        "source": "https://example.test/faculty/example-professor",
        "provenance": "synthetic official faculty page",
    }])

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


def build_fixture(program_root: Path, profile_root: Path, *, consumer_root: Path | None = None,
                  professor_research_sha: str = "", zotero_http_url: str = "",
                  zotero_mcp_url: str = "",
                  item_key: str | None = None,
                  fixture_run_id: str = "") -> dict:
    """Build the raw fixture; ``item_key`` injects the runtime-returned Zotero key.

    The default ``item_key`` keeps the deterministic E2E fixture byte-stable;
    the issue #40 runtime setup helper passes the real key it received from the
    disposable Zotero so no fake key ever enters ``papers.json``/preview.
    """
    key = item_key if item_key is not None else CANONICAL_ITEM_KEY
    if not isinstance(key, str) or not key.strip():
        raise FixtureBuildError(f"item_key must be a non-empty string: {key!r}")
    if key == CANONICAL_ITEM_KEY and fixture_run_id:
        raise FixtureBuildError(
            "fixture_run_id requires a runtime item_key; the deterministic "
            "fixture must stay decoupled from fixture runs")
    program_root = Path(program_root).resolve()
    profile_root = Path(profile_root).resolve()
    _prepare_output(program_root)
    program_hashes = _write_inputs(program_root, profile_root, key)
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
        "item_keys": [key],
        "canonical_item_key": key,
        "professor_research_sha": professor_research_sha,
        "zotero_http_url": zotero_http_url,
        "zotero_mcp_url": zotero_mcp_url,
        "protected_files": program_hashes,
        "profile_files": _tree_hashes(profile_root),
        "forbidden_product_outputs": [path.as_posix() for path in FORBIDDEN_STAGE_OUTPUTS],
    }
    if fixture_run_id:
        manifest["fixture_run_id"] = fixture_run_id
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = build_fixture(
            args.program_root, args.profile_root, consumer_root=args.consumer_root,
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
