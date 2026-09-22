#!/usr/bin/env python3
"""Prepare the issue #40 runtime fixture: dynamic Zotero key + Stage 0 target.

This is the single setup helper for the #40/#43 Codex runtime recipes.  In one
invocation it seeds the disposable Zotero fixture through the real MCP write
surface, imports the deterministic synthetic PDF onto that same item, builds the
raw program/profile inputs with the runtime-returned item key, records the
official deterministic Stage 0 selection, and writes machine readable setup
evidence.  Runners must never assemble this state by hand, must never touch
fixture SQLite, must never copy a real user Zotero profile, and must never
target the production ports 23119/23120.

The MCP protocol functions are shared with the #39 seed helper so the fixture
wire format has exactly one producer-owned implementation.  The catalog metadata
comes from the fixture builder so the Zotero item, ``papers.json`` and the
imported PDF can never describe different papers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

_RUNTIME_DIR = Path(__file__).resolve().parent
if str(_RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_DIR))

import build_issue32_e2e_fixture as builder  # noqa: E402
import prepare_issue39_stage2_fixture as pc39  # noqa: E402
import seed_issue39_zotero as zseed  # noqa: E402

HELPER_ID = "tests/runtime/prepare_issue40_runtime_fixture.py"
SCHEMA_VERSION = 1
FIXTURE_REPOSITORY = "skills-test-fixtures"
FIXTURE_REVISION = "f03aea49d22ca22d5b885569a8d52706d50c8950"
STAGE0_TARGET_RELATIVE = Path("教授研究/套磁目标.json")
PAPER_FILE_NAME = "canonical-paper.pdf"


class PrepareError(RuntimeError):
    """Raised when the runtime fixture cannot be prepared safely."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _validate_professor_research_sha(value: str) -> str:
    if not isinstance(value, str) or len(value) != 40 \
            or any(char not in "0123456789abcdef" for char in value):
        raise PrepareError(
            "professor_research_sha must be a full 40-hex commit SHA; refusing "
            f"placeholder or abbreviated value: {value!r}")
    return value


def validate_fixture_evidence(source: Path | str | None) -> dict:
    """Fail closed unless the evidence belongs to the pinned clean fixture."""
    if source is None:
        source = os.environ.get("FIXTURE_EVIDENCE_FILE")
    if not source or not str(source).strip():
        raise PrepareError(
            "fixture evidence is required: pass --fixture-evidence or export "
            "FIXTURE_EVIDENCE_FILE from the disposable fixture environment")
    with Path(source).open(encoding="utf-8") as handle:
        evidence = json.load(handle)
    if not isinstance(evidence, dict):
        raise PrepareError("fixture evidence must be a JSON object")
    if evidence.get("fixture_repo_sha") != FIXTURE_REVISION:
        raise PrepareError(
            "fixture evidence fixture_repo_sha does not match the pinned "
            f"{FIXTURE_REPOSITORY}@{FIXTURE_REVISION}")
    if evidence.get("fixture_repo_dirty") != "no":
        raise PrepareError("fixture evidence must record fixture_repo_dirty=no")
    if evidence.get("manual_patch") != "no":
        raise PrepareError("fixture evidence must record manual_patch=no")
    run_id = evidence.get("fixture_run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise PrepareError("fixture evidence fixture_run_id must be a non-empty string")
    return {"revision": FIXTURE_REVISION, "run_id": run_id}


def _validate_http_url(zotero_http_url: str) -> None:
    parsed = urlsplit(zotero_http_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise PrepareError(
            f"zotero_http_url must be an absolute http(s) URL: {zotero_http_url!r}")
    try:
        port = parsed.port
    except ValueError as exc:
        raise PrepareError(
            f"zotero_http_url has an invalid port: {zotero_http_url!r}") from exc
    if port in zseed.PRODUCTION_ZOTERO_PORTS:
        raise PrepareError(
            f"zotero_http_url uses production Zotero port {port}; refusing setup")


def _contact_targets_script(consumer_root: Path | str | None) -> Path:
    """Resolve the installed Stage 0 runner; consumer install wins over producer."""
    candidates = []
    if consumer_root:
        candidates.append(Path(consumer_root) / ".agents" / "skills"
                          / "professor-contact" / "scripts" / "contact_targets.py")
    candidates.append(_RUNTIME_DIR.parents[1] / "scripts" / "contact_targets.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise PrepareError(
        "contact_targets.py not found in the consumer install or producer tree")


def _extract_attachment_key(result: object) -> str:
    """Pull the runtime-returned attachmentKey out of a write_item import."""
    if not isinstance(result, dict):
        raise PrepareError("write_item import returned no result object")
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        data = structured.get("data")
        if isinstance(data, dict) and isinstance(data.get("attachmentKey"), str) \
                and data["attachmentKey"].strip():
            return data["attachmentKey"].strip()
        if isinstance(structured.get("attachmentKey"), str) \
                and structured["attachmentKey"].strip():
            return structured["attachmentKey"].strip()
    content = result.get("content")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict) or "text" not in block:
                continue
            try:
                payload = json.loads(block["text"])
            except (json.JSONDecodeError, TypeError):
                continue
            candidates = [payload] + (list(payload.values())
                                      if isinstance(payload, dict) else [])
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                for holder in (candidate, candidate.get("data")):
                    if isinstance(holder, dict) and isinstance(holder.get("attachmentKey"), str) \
                            and holder["attachmentKey"].strip():
                        return holder["attachmentKey"].strip()
    raise PrepareError("write_item import returned no attachmentKey; refusing to invent one")


def _canonical_item_fields() -> dict[str, str]:
    return {
        "title": builder.CANONICAL_PAPER_TITLE,
        "date": str(builder.CANONICAL_PAPER_YEAR),
        "publicationTitle": builder.CANONICAL_PUBLICATION_TITLE,
        "abstractNote": builder.CANONICAL_PAPER_ABSTRACT,
    }


def _seed_canonical_item(http_post, zotero_mcp_url: str) -> tuple[dict[str, str], str]:
    """Create the one synthetic journal item through the real MCP write surface."""
    session = zseed._open_session(http_post, zotero_mcp_url)
    message = zseed._rpc_result(
        http_post, zotero_mcp_url, session,
        {"jsonrpc": "2.0", "id": 10, "method": "tools/call",
         "params": {"name": "write_item",
                    "arguments": {"action": "create",
                                  "itemType": "journalArticle",
                                  "fields": _canonical_item_fields(),
                                  "creators": [dict(zseed.AUTHOR)]}}})
    if not isinstance(message, dict) or not isinstance(message.get("result"), dict):
        raise PrepareError("write_item did not return a JSON-RPC result")
    key = zseed._extract_item_key(message["result"])
    if not isinstance(key, str) or not key.strip():
        raise PrepareError("write_item returned a non-string itemKey")
    if key.strip() in zseed.LEGACY_ITEM_KEYS:
        raise PrepareError(f"write_item returned a legacy fake key: {key!r}")
    return session, key.strip()


def _import_paper_attachment(http_post, zotero_mcp_url: str,
                             session: dict[str, str], item_key: str,
                             work_dir: Path) -> tuple[str, bytes]:
    """Attach the deterministic PDF for the canonical item through write_item import."""
    pdf_bytes = builder.render_text_pdf(list(builder.CANONICAL_PDF_LINES))
    pdf_path = work_dir / PAPER_FILE_NAME
    pdf_path.write_bytes(pdf_bytes)
    message = zseed._rpc_result(
        http_post, zotero_mcp_url, session,
        {"jsonrpc": "2.0", "id": 20, "method": "tools/call",
         "params": {"name": "write_item",
                    "arguments": {"action": "import",
                                  "filePath": str(pdf_path),
                                  "parentItemKey": item_key,
                                  "title": builder.CANONICAL_PAPER_TITLE}}})
    if not isinstance(message, dict) or not isinstance(message.get("result"), dict):
        raise PrepareError("write_item import did not return a JSON-RPC result")
    return _extract_attachment_key(message["result"]), pdf_bytes


def _record_stage0_selection(program_root: Path, consumer_root: Path | str | None) -> dict:
    """Run the official contact_targets select runner on a deterministic input."""
    script = _contact_targets_script(consumer_root)
    preview_path = program_root / "教授研究" / "X分野" / builder.PROFESSOR / "方向预筛.json"
    selection = {"direction_ids": [builder.DIRECTION_ID], "notes": {}}
    with tempfile.TemporaryDirectory(prefix="issue40-stage0-input.") as tmp:
        selection_path = Path(tmp) / "stage0-selection.json"
        selection_path.write_text(
            json.dumps(selection, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8")
        result = pc39._run_json(script, [
            "select",
            "--program-root", program_root,
            "--preview", preview_path,
            "--selection-file", selection_path,
        ])
    if result.get("status") != "ok":
        raise PrepareError(f"contact_targets select did not report ok: {result!r}")
    try:
        state = json.loads((program_root / STAGE0_TARGET_RELATIVE)
                           .read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrepareError(f"Stage 0 target unreadable after select: {exc}") from exc
    targets = state.get("targets") if isinstance(state, dict) else None
    row = next((row for row in targets or []
                if isinstance(row, dict) and row.get("professor") == builder.PROFESSOR), None)
    if row is None or row.get("selected_direction_ids") != [builder.DIRECTION_ID]:
        raise PrepareError(
            "Stage 0 target does not record the deterministic selection: "
            f"{json.dumps(row, ensure_ascii=False) if row else 'target missing'}")
    return {"runner": script, "selection": selection,
            "selected_direction_ids": row["selected_direction_ids"],
            "runner_sha256": _sha256_bytes(script.read_bytes())}


def _forbidden_outputs_absent(program_root: Path) -> bool:
    return all(not (program_root / relative).exists()
               for relative in builder.FORBIDDEN_STAGE_OUTPUTS
               if relative != STAGE0_TARGET_RELATIVE)


def prepare_runtime_fixture(*, program_root: Path, profile_root: Path,
                            consumer_root: Path | str | None,
                            zotero_http_url: str, zotero_mcp_url: str,
                            professor_research_sha: str,
                            fixture_evidence: Path | str | None,
                            output: Path,
                            http_post=zseed._http_post) -> dict:
    pc39.validate_runtime_endpoints(zotero_http_url, zotero_mcp_url)
    _validate_http_url(zotero_http_url)
    _validate_professor_research_sha(professor_research_sha)
    evidence = validate_fixture_evidence(fixture_evidence)
    session, item_key = _seed_canonical_item(http_post, zotero_mcp_url)
    program_root = Path(program_root).resolve()
    profile_root = Path(profile_root).resolve()
    consumer_root = Path(consumer_root).resolve() if consumer_root else None
    with tempfile.TemporaryDirectory(prefix="issue40-paper-pdf.") as tmp:
        attachment_key, pdf_bytes = _import_paper_attachment(
            http_post, zotero_mcp_url, session, item_key, Path(tmp))
    manifest = builder.build_fixture(
        program_root, profile_root, consumer_root=consumer_root,
        professor_research_sha=professor_research_sha,
        zotero_http_url=zotero_http_url, zotero_mcp_url=zotero_mcp_url,
        item_key=item_key, fixture_run_id=evidence["run_id"])
    stage0 = _record_stage0_selection(program_root, consumer_root)
    if not _forbidden_outputs_absent(program_root):
        raise PrepareError(
            "Stage 1–5 canonical outputs already exist; the setup helper must "
            "never pre-create product state")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "helper": HELPER_ID,
        "helper_sha256": _sha256_bytes(Path(__file__).read_bytes()),
        "builder": builder.MANIFEST_ID,
        "builder_sha256": manifest["builder_sha256"],
        "fixture_repository": FIXTURE_REPOSITORY,
        "fixture_repo_sha": evidence["revision"],
        "fixture_run_id": evidence["run_id"],
        "zotero_http_url": zotero_http_url,
        "zotero_mcp_url": zotero_mcp_url,
        "professor_research_sha": professor_research_sha,
        "consumer_root": str(consumer_root) if consumer_root else None,
        "program_root": manifest["program_root"],
        "profile_root": manifest["profile_root"],
        "item_key": item_key,
        "paper_attachment": {
            "key": attachment_key,
            "parent_item_key": item_key,
            "title": builder.CANONICAL_PAPER_TITLE,
            "file_name": PAPER_FILE_NAME,
            "sha256": _sha256_bytes(pdf_bytes),
        },
        "stage0": {
            "runner": "scripts/contact_targets.py",
            "runner_sha256": stage0["runner_sha256"],
            "selection": stage0["selection"],
            "target_path": STAGE0_TARGET_RELATIVE.as_posix(),
            "selected_direction_ids": stage0["selected_direction_ids"],
        },
        "input_hashes": {
            "program_inputs": manifest["protected_files"],
            "profile_inputs": manifest["profile_files"],
        },
        "forbidden_outputs_absent": True,
    }
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare the PC40 disposable-Zotero runtime fixture and "
                    "Stage 0 canonical target")
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--consumer-root", type=Path)
    parser.add_argument("--zotero-http-url", required=True)
    parser.add_argument("--zotero-mcp-url", required=True)
    parser.add_argument("--professor-research-sha", required=True)
    parser.add_argument("--fixture-evidence", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = prepare_runtime_fixture(
            program_root=args.program_root, profile_root=args.profile_root,
            consumer_root=args.consumer_root,
            zotero_http_url=args.zotero_http_url, zotero_mcp_url=args.zotero_mcp_url,
            professor_research_sha=args.professor_research_sha,
            fixture_evidence=args.fixture_evidence, output=args.output)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(Path(args.output).resolve()),
                      "item_key": payload["item_key"],
                      "paper_attachment_key": payload["paper_attachment"]["key"],
                      "fixture_run_id": payload["fixture_run_id"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
