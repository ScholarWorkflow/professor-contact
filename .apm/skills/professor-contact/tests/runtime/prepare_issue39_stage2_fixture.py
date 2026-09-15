#!/usr/bin/env python3
"""Prepare the producer-owned prerequisite for issue #39 PC39-R1.

The runtime smoke must start Stage 2 from a valid product state without
running the Stage 1 downloader/collector LLM chain.  The disposable Zotero
fixture setup supplies real item and attachment keys in a small JSON config;
this helper binds those keys to synthetic program inputs, runs the product's
Stage 0 and Stage 1 deterministic runners at the final path, and records the
resulting provenance.

This helper does not start Zotero, create MCP data, proxy production ports, or
write any Stage 2 product output.  The fixture setup owns the external Zotero
items; the helper owns only the local program prerequisite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


HELPER_ID = "tests/runtime/prepare_issue39_stage2_fixture.py"
SCHEMA_VERSION = 1
ITEM_CONFIG_SCHEMA_VERSION = 1
FIXTURE_REPOSITORY = "skills-test-fixtures"
FIXTURE_REVISION = "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972"
PROFESSOR = "Example Professor"
DIRECTION_ID = "DIR00001"
FIXED_NOTE = "I want to study adaptive and nonlinear extensions of this processing framework."
LEGACY_ITEM_KEYS = {"AAAA1111", "BBBB2222"}
PRODUCTION_ZOTERO_PORTS = {23119, 23120}
ITEM_COUNT = 2
FILL_STATUS = "pending"
STAGE2_OUTPUTS = (
    Path("教授研究/X分野/Example Professor/套磁候选输入.json"),
    Path("教授研究/X分野/Example Professor/套磁候选状态.json"),
    Path("教授研究/X分野/Example Professor/套磁选择.json"),
    Path("教授研究/X分野/Example Professor/邮件输入.json"),
    Path("教授研究/X分野/Example Professor/套磁候选分析.md"),
)


class SetupError(RuntimeError):
    """Raised when the PC39 prerequisite cannot be built safely."""


def read_json(source: Path | str | dict) -> object:
    """Read a JSON file or clone an in-memory config for test callers."""
    if isinstance(source, dict):
        return json.loads(json.dumps(source, ensure_ascii=False))
    with Path(source).open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hashes(root: Path) -> list[dict[str, str]]:
    return [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256_file(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "fixture-manifest.json"
    ]


def _producer_repo_root() -> Path:
    # .../.apm/skills/professor-contact/tests/runtime/<this file>
    return Path(__file__).resolve().parents[5]


def _prepare_program_root(root: Path) -> Path:
    root = Path(root).resolve()
    repo_root = _producer_repo_root()
    if root == repo_root or repo_root in root.parents:
        raise SetupError(f"program root must be outside the producer checkout: {root}")
    if root.exists():
        manifest_path = root / "fixture-manifest.json"
        if not manifest_path.is_file():
            if any(root.iterdir()):
                raise SetupError(f"refusing to replace a foreign directory: {root}")
        else:
            try:
                prior = read_json(manifest_path)
            except (OSError, json.JSONDecodeError) as exc:
                raise SetupError(f"cannot read prior fixture manifest: {manifest_path}") from exc
            if not isinstance(prior, dict) or prior.get("helper") != HELPER_ID:
                raise SetupError(f"fixture belongs to another builder: {root}")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=False)
    return root


def validate_runtime_endpoints(zotero_http_url: str, zotero_mcp_url: str) -> None:
    """Require disposable HTTP/MCP endpoints and reject production ports."""
    for name, raw in (("zotero_http_url", zotero_http_url),
                      ("zotero_mcp_url", zotero_mcp_url)):
        if not isinstance(raw, str) or not raw.strip():
            raise SetupError(f"{name} is required")
        parsed = urlsplit(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise SetupError(f"{name} must be an absolute http(s) URL: {raw!r}")
        try:
            port = parsed.port
        except ValueError as exc:
            raise SetupError(f"{name} has an invalid port: {raw!r}") from exc
        if port in PRODUCTION_ZOTERO_PORTS:
            raise SetupError(
                f"{name} uses production Zotero port {port}; refusing PC39-R1 setup")
    mcp_path = urlsplit(zotero_mcp_url.rstrip("/")).path
    if not mcp_path.endswith("/mcp"):
        raise SetupError("zotero_mcp_url must be the complete endpoint ending in /mcp")


def validate_items_config(source: Path | str | dict) -> dict:
    """Validate the dynamic item/attachment provenance from the fixture."""
    config = read_json(source)
    if not isinstance(config, dict):
        raise SetupError("zotero items config must be a JSON object")
    if config.get("schema_version") != ITEM_CONFIG_SCHEMA_VERSION:
        raise SetupError(
            f"zotero items config schema_version must be {ITEM_CONFIG_SCHEMA_VERSION}")
    if config.get("fixture_repository") != FIXTURE_REPOSITORY:
        raise SetupError(f"fixture_repository must be {FIXTURE_REPOSITORY!r}")
    if config.get("fixture_revision") != FIXTURE_REVISION:
        raise SetupError(
            "fixture_revision must remain pinned to "
            f"{FIXTURE_REPOSITORY}@{FIXTURE_REVISION}")

    def string_list(field: str) -> list[str]:
        value = config.get(field)
        if (not isinstance(value, list) or len(value) == 0
                or not all(isinstance(item, str) and item.strip() for item in value)):
            raise SetupError(f"zotero items config.{field} must be a non-empty string list")
        return list(value)

    item_keys = string_list("item_keys")
    ready_item_keys = string_list("ready_item_keys")
    if len(item_keys) != ITEM_COUNT or len(set(item_keys)) != ITEM_COUNT:
        raise SetupError(f"runtime fixture requires exactly {ITEM_COUNT} distinct item keys")
    if set(item_keys) & LEGACY_ITEM_KEYS:
        raise SetupError("zotero items config contains legacy fake item keys")
    if len(ready_item_keys) != 1 or not set(ready_item_keys) <= set(item_keys):
        raise SetupError("runtime fixture requires one ready item key from item_keys")

    fill_target = config.get("fill_target_item_key")
    if not isinstance(fill_target, str) or not fill_target.strip():
        raise SetupError("fill_target_item_key must be a non-empty string")
    if fill_target not in item_keys or fill_target in ready_item_keys:
        raise SetupError("fill_target_item_key must be distinct from the ready item")
    if config.get("fill_target_pdf_status") != FILL_STATUS:
        raise SetupError(f"fill_target_pdf_status must be {FILL_STATUS!r}")

    run_id = config.get("fixture_run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise SetupError("fixture_run_id must be a non-empty string")
    attachments = config.get("attachment_keys")
    if not isinstance(attachments, dict):
        raise SetupError("attachment_keys must be an object mapping every item key")
    if set(attachments) != set(item_keys):
        raise SetupError("attachment_keys must cover exactly every item key")
    for item_key, attachment_key in attachments.items():
        if not isinstance(attachment_key, str) or not attachment_key.strip():
            raise SetupError(f"attachment key for {item_key} must be a non-empty string")
        if attachment_key in LEGACY_ITEM_KEYS:
            raise SetupError("attachment_keys contains a legacy fake key")
    return {
        "schema_version": ITEM_CONFIG_SCHEMA_VERSION,
        "fixture_repository": FIXTURE_REPOSITORY,
        "fixture_revision": FIXTURE_REVISION,
        "fixture_run_id": run_id,
        "item_keys": item_keys,
        "ready_item_keys": ready_item_keys,
        "fill_target_item_key": fill_target,
        "fill_target_pdf_status": FILL_STATUS,
        "attachment_keys": dict(attachments),
    }


def _render_text_pdf(lines: list[str]) -> bytes:
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
               for line in lines]
    stream = ("\n".join(["BT", "/F1 11 Tf", "72 748 Td"]
                         + sum((["0 -16 Td", f"({line}) Tj"] if index else [f"({line}) Tj"]
                                for index, line in enumerate(escaped)), [])
                         + ["ET"]) + "\n").encode("ascii")
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


def _run_json(script: Path, arguments: list[object]) -> dict:
    completed = subprocess.run(
        [sys.executable, str(script), *map(str, arguments)],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SetupError(
            f"{script.name} returned non-JSON output: {completed.stdout!r} "
            f"{completed.stderr!r}") from exc
    if completed.returncode != 0 or not isinstance(payload, dict):
        raise SetupError(
            f"{script.name} failed (exit {completed.returncode}): "
            + json.dumps(payload, ensure_ascii=False))
    return payload


def _write_raw_inputs(root: Path, items: dict) -> list[dict[str, str]]:
    item_keys = items["item_keys"]
    ready_key = items["ready_item_keys"][0]
    fill_key = items["fill_target_item_key"]
    professor_dir = root / "教授研究" / "X分野" / PROFESSOR
    analysis_dir = professor_dir / "论文分析"
    preview_path = professor_dir / "方向预筛.json"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    preview = {
        "schema_version": 1,
        "professor": PROFESSOR,
        "preview_fingerprint": "pc39-stage2-preview-v1",
        "preview_fingerprint_version": "v1",
        "direction_id_version": "v1",
        "membership_mode": "overlap_allowed",
        "directions": [{
            "direction_id": DIRECTION_ID,
            "member_fingerprint": "pc39-stage2-members-v1",
            "name_ja": "Adaptive and nonlinear processing",
            "name_zh": "自适应与非线性处理",
            "summary_zh": "Synthetic direction for the PC39 endpoint smoke.",
            "user_note": FIXED_NOTE,
            "members": [{"item_key": key, "preview_confidence": "high"}
                        for key in item_keys],
            "representatives": [{"item_key": ready_key}],
        }],
    }
    _write_json(preview_path, preview)

    metadata = {
        ready_key: {
            "title": "Adaptive Processing in Synthetic Systems",
            "title_zh": "合成系统中的自适应处理",
            "year": 2024,
            "abstract": "A deterministic synthetic paper about adaptive and nonlinear processing.",
            "authors": [PROFESSOR, "Synthetic Researcher"],
        },
        fill_key: {
            "title": "Nonlinear Extensions of Synthetic Processing",
            "title_zh": "合成处理的非线性扩展",
            "year": 2023,
            "abstract": "A synthetic paper used to keep the runtime fill target explicit.",
            "authors": [PROFESSOR, "Synthetic Collaborator"],
        },
    }
    papers = []
    for key in item_keys:
        paper = {"item_key": key, **metadata[key]}
        if key == ready_key:
            paper.update({"pdf_status": "downloaded", "pdf_path": f"论文分析/{key}.pdf"})
        else:
            paper["pdf_status"] = items["fill_target_pdf_status"]
        papers.append(paper)
    _write_json(professor_dir / "papers.json", {"papers": papers})
    (analysis_dir / f"{ready_key}.pdf").write_bytes(_render_text_pdf([
        "Synthetic paper: Adaptive Processing in Synthetic Systems",
        "Example Professor",
        "Abstract: adaptive and nonlinear processing is evaluated.",
        "Future work: extend the framework to nonlinear and adaptive settings.",
        "This deterministic PDF is producer-owned input, not a completed analysis.",
    ]))

    _write_json(root / "info.json", {
        "schema_version": 1,
        "program": "issue39-stage2-endpoint-runtime-fixture",
        "source": "synthetic producer input",
        "university": "Fixture University A",
        "department": "Synthetic Systems",
        "target": {"intake_year": 2027, "intake_term": "april"},
    })
    _write_json(root / "boshu_analysis.json", {
        "schema_version": 1,
        "research_area": "adaptive and nonlinear processing",
        "requirements": ["research fit", "future direction"],
    })
    _write_json(root / "教授研究" / "_署名对照.json", {
        "updated_at": "2026-01-01T00:00:00Z",
        "overrides": {},
        "professors": {
            PROFESSOR: {
                "books": [{
                    "prof_name_tokens": ["Example", "Professor"],
                    "seed_count": len(item_keys),
                    "auto": [],
                    "conflicted": [],
                    "offenders": [],
                    "typos": [],
                    "mashes": [],
                }],
                "seed_count": len(item_keys),
            }
        },
    })
    return [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256_file(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def _run_stage0(root: Path) -> dict:
    runtime_dir = Path(__file__).resolve().parent
    script = runtime_dir.parent.parent / "scripts" / "contact_targets.py"
    preview = root / "教授研究" / "X分野" / PROFESSOR / "方向预筛.json"
    selection = {"direction_ids": [DIRECTION_ID], "notes": {DIRECTION_ID: FIXED_NOTE}}
    with tempfile.TemporaryDirectory(prefix="pc39-stage0-") as directory:
        selection_path = Path(directory) / "selection.json"
        _write_json(selection_path, selection)
        result = _run_json(script, [
            "select", "--program-root", root, "--preview", preview,
            "--selection-file", selection_path,
        ])
    target = root / "教授研究" / "套磁目标.json"
    if not target.is_file():
        raise SetupError(f"Stage 0 runner did not create {target}")
    return {"status": result.get("status"), "result": result, "target_file": str(target)}


def _run_stage1(root: Path) -> dict:
    runtime_dir = Path(__file__).resolve().parent
    script = runtime_dir.parent.parent / "scripts" / "contact_stage1.py"
    built = _run_json(script, [
        "build", "--program-root", root, "--professors", PROFESSOR,
    ])
    verified = _run_json(script, [
        "verify", "--program-root", root, "--professors", PROFESSOR,
    ])
    if built.get("status") != "ok" or verified.get("status") != "ok":
        raise SetupError("product Stage 1 runner did not produce a verified snapshot")
    snapshot = root / "教授研究" / "套磁阶段1候选.json"
    if not snapshot.is_file():
        raise SetupError(f"Stage 1 runner did not create {snapshot}")
    return {"build": built, "verify": verified, "snapshot_file": str(snapshot)}


def prepare_stage2_prerequisite(*, program_root: Path,
                                zotero_items_config: Path | str | dict,
                                zotero_http_url: str,
                                zotero_mcp_url: str,
                                output: Path,
                                professor_research_sha: str = "") -> dict:
    """Build and verify the complete producer-owned PC39-R1 local input."""
    validate_runtime_endpoints(zotero_http_url, zotero_mcp_url)
    items = validate_items_config(zotero_items_config)
    root = _prepare_program_root(program_root)
    raw_hashes = _write_raw_inputs(root, items)
    stage0 = _run_stage0(root)
    if stage0.get("status") != "ok":
        raise SetupError(f"Stage 0 setup failed: {stage0}")
    stage1 = _run_stage1(root)
    stage2_paths = [str(root / relative) for relative in STAGE2_OUTPUTS]
    if any(Path(path).exists() for path in stage2_paths):
        raise SetupError("Stage 2 prerequisite unexpectedly contains a product output")

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "helper": HELPER_ID,
        "fixture": {
            "repository": items["fixture_repository"],
            "revision": items["fixture_revision"],
            "run_id": items["fixture_run_id"],
        },
        "program_root": str(root),
        "fixture_run_id": items["fixture_run_id"],
        "zotero_http_url": zotero_http_url,
        "zotero_mcp_url": zotero_mcp_url,
        "professor_research_sha": professor_research_sha,
        "item_keys": items["item_keys"],
        "ready_item_keys": items["ready_item_keys"],
        "fill_target_item_key": items["fill_target_item_key"],
        "attachment_keys": items["attachment_keys"],
        "raw_input_hashes": raw_hashes,
        "stage0": stage0,
        "stage1": stage1,
        "stage2_outputs_absent": True,
        "protected_files": _tree_hashes(root),
        "forbidden_stage2_outputs": [path.as_posix() for path in STAGE2_OUTPUTS],
    }
    _write_json(root / "fixture-manifest.json", evidence)
    output = Path(output).resolve()
    _write_json(output, evidence)
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare the issue #39 Stage 2 smoke prerequisite")
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--zotero-items-config", type=Path, required=True)
    parser.add_argument("--zotero-http-url", required=True)
    parser.add_argument("--zotero-mcp-url", required=True)
    parser.add_argument("--professor-research-sha", default="")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evidence = prepare_stage2_prerequisite(
            program_root=args.program_root,
            zotero_items_config=args.zotero_items_config,
            zotero_http_url=args.zotero_http_url,
            zotero_mcp_url=args.zotero_mcp_url,
            professor_research_sha=args.professor_research_sha,
            output=args.output,
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "helper": HELPER_ID,
                      "program_root": evidence["program_root"],
                      "output": str(Path(args.output).resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
