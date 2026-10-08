#!/usr/bin/env python3
"""Prepare the producer-owned Stage-2 prerequisite for issue #57 PC57-R1.

The helper builds one minimal, deterministic pre-Stage-2 case **outside** the
producer checkout:

1. it talks to the active disposable Zotero fixture only through its
   supported HTTP/MCP surface (``GET /connector/ping`` plus a real MCP
   ``write_item`` create) and uses the actually returned Zotero item key in
   product state — fixture SQLite is never edited and no key is invented;
2. it materializes canonical Stage-0/Stage-1 state with the producer's own
   deterministic runners from the clean consumer's installed skill dir;
3. it guarantees the selected paper still requires a **new** Stage-2
   delegated analysis: no reusable analysis, sidecar, facts, ``_index.json``,
   ``套磁候选输入.json``, ``_resolved_directions.json`` or ChatGPT result ZIP
   exists beforehand.

The disposable Zotero MCP fixture at the pinned revision does not expose an
attachment-creation tool, so no attachment is created; ``attachment_keys``
stays empty and the deterministic parseable PDF is producer-owned program
input (the #39 pattern), never a preexisting Stage-2 result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


HELPER_ID = "tests/runtime/prepare_issue57_stage2_fixture.py"
SCHEMA_VERSION = 1
PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "pc57-zotero-seed", "version": "1"}
PROFESSOR = "Issue57 Route Professor"
DIRECTION_ID = "DIR57STAGE2"
FIXED_NOTE = "I want to study deterministic routing and nested delegation stability."
LEGACY_ITEM_KEYS = {"AAAA1111", "BBBB2222"}
PRODUCTION_ZOTERO_PORTS = {23119, 23120}
RUNNER_SCRIPTS = ("scripts/contact_targets.py", "scripts/contact_stage1.py")
FORBIDDEN_OUTPUTS = (
    "教授研究/X分野/Issue57 Route Professor/套磁候选输入.json",
    "教授研究/X分野/Issue57 Route Professor/论文分析/_resolved_directions.json",
    "教授研究/X分野/Issue57 Route Professor/论文分析/_index.json",
    "教授研究/X分野/Issue57 Route Professor/套磁候选状态.json",
    "教授研究/X分野/Issue57 Route Professor/套磁选择.json",
    "教授研究/X分野/Issue57 Route Professor/邮件输入.json",
)


class SetupError(RuntimeError):
    """Raised when the PC57 Stage-2 prerequisite cannot be built safely."""


def _validate_expected_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not run_id.strip():
        raise SetupError(
            "fixture run id is required (pass --fixture-run-id or export "
            "FIXTURE_RUN_ID/ZOTERO_TEST_RUN_ID from the disposable fixture env)")
    return run_id.strip()


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
                f"{name} uses production Zotero port {port}; refusing PC57-R1 setup")
    if not urlsplit(zotero_mcp_url.rstrip("/")).path.endswith("/mcp"):
        raise SetupError("zotero_mcp_url must be the complete endpoint ending in /mcp")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8",
    )


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
                prior = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SetupError(f"cannot read prior fixture manifest: {manifest_path}") from exc
            if not isinstance(prior, dict) or prior.get("helper") != HELPER_ID:
                raise SetupError(f"fixture belongs to another builder: {root}")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=False)
    return root


def validate_installed_skill_dir(skill_dir: Path | str) -> dict:
    """Resolve the clean-consumer installed skill dir and hash its runners.

    The deterministic Stage 0/1 runners must execute from the exact final SHA
    installed inside the clean consumer — never from the producer checkout the
    helper itself happens to live in.
    """
    resolved = Path(skill_dir).resolve()
    if not resolved.is_dir():
        raise SetupError(f"professor-contact skill dir does not exist: {resolved}")
    runner_records = []
    for relative in RUNNER_SCRIPTS:
        script = resolved / relative
        if not script.is_file():
            raise SetupError(f"installed skill dir is missing runner: {script}")
        runner_records.append({"path": relative, "sha256": _sha256_file(script)})
    return {"path": str(resolved), "runner_scripts": runner_records}


def _http_get(url: str) -> int:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.status


def _http_post(url: str, payload_bytes: bytes, headers: dict[str, str]):
    """Post one JSON-RPC payload; returns (status, response headers, text)."""
    request = urllib.request.Request(
        url, data=payload_bytes, method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream", **headers})
    with urllib.request.urlopen(request, timeout=60) as response:
        return (response.status,
                {key.lower(): value for key, value in response.headers.items()},
                response.read().decode("utf-8"))


def _parse_rpc_response(text: str) -> object:
    """Parse a JSON or SSE-framed JSON-RPC message."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            candidate = line.strip()
            if candidate.startswith("data:"):
                try:
                    return json.loads(candidate[5:].strip())
                except json.JSONDecodeError:
                    continue
    return None


def _rpc_result(http_post, url: str, session: dict[str, str], payload: dict,
                expect_reply: bool = True) -> object:
    status, headers, text = http_post(
        url, json.dumps(payload).encode("utf-8"),
        {"mcp-session-id": session["id"]} if session["id"] else {})
    if status >= 400:
        raise SetupError(f"MCP endpoint returned HTTP {status} for {payload.get('method')}")
    message = _parse_rpc_response(text)
    if expect_reply and not isinstance(message, dict):
        raise SetupError(f"MCP endpoint returned an unparseable response for {payload.get('method')}")
    if isinstance(message, dict) and message.get("error") is not None:
        raise SetupError(
            f"MCP call {payload.get('method')} failed: "
            f"{json.dumps(message.get('error'), ensure_ascii=False)}")
    return message


def _open_session(http_post, url: str) -> dict[str, str]:
    status, headers, text = http_post(
        url,
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": PROTOCOL_VERSION,
                               "capabilities": {},
                               "clientInfo": CLIENT_INFO}}).encode("utf-8"),
        {})
    if status >= 400:
        raise SetupError(f"MCP initialize returned HTTP {status}")
    message = _parse_rpc_response(text)
    if not isinstance(message, dict) or not isinstance(message.get("result"), dict):
        raise SetupError("MCP initialize did not return a JSON-RPC result")
    session_id = headers.get("mcp-session-id", "")
    if not session_id:
        raise SetupError("MCP initialize response did not carry mcp-session-id")
    _rpc_result(http_post, url, {"id": session_id},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                expect_reply=False)
    return {"id": session_id}


def _extract_item_key(result: object) -> str:
    """Pull the runtime-returned itemKey out of a write_item result."""
    if not isinstance(result, dict):
        raise SetupError("write_item returned no result object")
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        key = structured.get("itemKey", structured.get("key"))
        if isinstance(key, str) and key.strip():
            return key.strip()
    content = result.get("content")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict) or "text" not in block:
                continue
            try:
                payload = json.loads(block["text"])
            except (json.JSONDecodeError, TypeError):
                continue
            candidates: list[object] = [payload]
            if isinstance(payload, dict):
                candidates.extend(payload.values())
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                key = candidate.get("itemKey", candidate.get("key"))
                if isinstance(key, str) and key.strip():
                    return key.strip()
                successful = candidate.get("successful")
                if isinstance(successful, dict):
                    for row in successful.values():
                        if isinstance(row, dict) and isinstance(row.get("key"), str) \
                                and row["key"].strip():
                            return row["key"].strip()
    raise SetupError("write_item returned no itemKey; refusing to invent one")


def probe_http_fixture(zotero_http_url: str, http_get=_http_get) -> int:
    """Confirm the disposable fixture answers on its supported HTTP surface."""
    base = zotero_http_url.rstrip("/")
    try:
        status = http_get(f"{base}/connector/ping")
    except Exception as exc:
        raise SetupError(f"Zotero HTTP fixture probe failed: {exc}") from exc
    if status >= 400:
        raise SetupError(f"Zotero HTTP fixture probe returned HTTP {status}")
    return status


def seed_zotero_paper(*, zotero_mcp_url: str, http_post=_http_post) -> str:
    """Create the synthetic paper via MCP ``write_item`` and return its key."""
    session = _open_session(http_post, zotero_mcp_url)
    message = _rpc_result(
        http_post, zotero_mcp_url, session,
        {"jsonrpc": "2.0", "id": 10, "method": "tools/call",
         "params": {"name": "write_item",
                    "arguments": {"action": "create",
                                  "itemType": "journalArticle",
                                  "fields": {
                                      "title": "Routing Stability in Synthetic "
                                               "Nested Delegation Systems",
                                      "date": "2026",
                                      "publicationTitle": "Synthetic Routing Journal",
                                      "abstractNote": "A deterministic synthetic paper "
                                                      "about routing stability and nested "
                                                      "delegation.",
                                  },
                                  "creators": [
                                      {"creatorType": "author",
                                       "firstName": "Example",
                                       "lastName": "Professor"},
                                  ]}}})
    if not isinstance(message, dict) or not isinstance(message.get("result"), dict):
        raise SetupError("write_item did not return a JSON-RPC result")
    key = _extract_item_key(message["result"])
    if key in LEGACY_ITEM_KEYS:
        raise SetupError(f"write_item returned a legacy fake key: {key!r}")
    return key


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


def _write_raw_inputs(root: Path, item_key: str) -> list[dict[str, str]]:
    professor_dir = root / "教授研究" / "X分野" / PROFESSOR
    analysis_dir = professor_dir / "论文分析"
    preview_path = professor_dir / "方向预筛.json"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    preview = {
        "schema_version": 1,
        "professor": PROFESSOR,
        "preview_fingerprint": "pc57-stage2-preview-v1",
        "preview_fingerprint_version": "v1",
        "direction_id_version": "v1",
        "membership_mode": "overlap_allowed",
        "directions": [{
            "direction_id": DIRECTION_ID,
            "member_fingerprint": "pc57-stage2-members-v1",
            "name_ja": "Routing stability and nested delegation",
            "name_zh": "路由稳定性与嵌套委派",
            "summary_zh": "Synthetic direction for the PC57 Stage-2 routing smoke.",
            "user_note": FIXED_NOTE,
            "members": [{"item_key": item_key, "preview_confidence": "high"}],
            "representatives": [{"item_key": item_key}],
        }],
    }
    _write_json(preview_path, preview)

    papers = [{
        "item_key": item_key,
        "title": "Routing Stability in Synthetic Nested Delegation Systems",
        "title_zh": "合成嵌套委派系统中的路由稳定性",
        "year": 2026,
        "abstract": "A deterministic synthetic paper about routing stability and "
                    "nested delegation.",
        "authors": [PROFESSOR, "Synthetic Researcher"],
        "pdf_status": "downloaded",
        "pdf_path": f"论文分析/{item_key}.pdf",
    }]
    _write_json(professor_dir / "papers.json", {"papers": papers})
    (analysis_dir / f"{item_key}.pdf").write_bytes(_render_text_pdf([
        "Synthetic paper: Routing Stability in Synthetic Nested Delegation Systems",
        "Issue57 Route Professor",
        "Abstract: routing stability and nested delegation are evaluated.",
        "Future work: extend the framework to cross-runtime delegation settings.",
        "This deterministic PDF is producer-owned input, not a completed analysis.",
    ]))

    _write_json(root / "info.json", {
        "schema_version": 1,
        "program": "issue57-stage2-routing-fixture",
        "source": "synthetic producer input",
        "university": "Fixture University B",
        "department": "Synthetic Routing Systems",
        "target": {"intake_year": 2027, "intake_term": "april"},
    })
    _write_json(root / "boshu_analysis.json", {
        "schema_version": 1,
        "research_area": "routing stability and nested delegation",
        "requirements": ["research fit", "future direction"],
    })
    _write_json(root / "教授研究" / "_署名对照.json", {
        "updated_at": "2026-01-01T00:00:00Z",
        "overrides": {},
        "professors": {
            PROFESSOR: {
                "books": [{
                    "prof_name_tokens": ["Issue57", "Route", "Professor"],
                    "seed_count": 1,
                    "auto": [],
                    "conflicted": [],
                    "offenders": [],
                    "typos": [],
                    "mashes": [],
                }],
                "seed_count": 1,
            }
        },
    })
    return [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256_file(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


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


def _stage0_target(root: Path) -> Path:
    """The professor-local Stage-0 file this fixture's own ``bootstrap`` run writes."""
    return root / "教授研究" / "X分野" / PROFESSOR / "套磁目标.json"


def _run_stage0(root: Path, skill_dir: Path) -> dict:
    script = skill_dir / "scripts" / "contact_targets.py"
    preview = _stage0_target(root).parent / "方向预筛.json"
    selection = {"direction_ids": [DIRECTION_ID], "notes": {DIRECTION_ID: FIXED_NOTE}}
    with tempfile.TemporaryDirectory(prefix="pc57-stage0-") as directory:
        selection_path = Path(directory) / "selection.json"
        _write_json(selection_path, selection)
        result = _run_json(script, [
            "bootstrap", "--program-root", root, "--preview", preview,
            "--selection-file", selection_path,
        ])
    target = _stage0_target(root)
    if not target.is_file():
        raise SetupError(f"Stage 0 runner did not create {target}")
    return {"status": result.get("status"), "result": result, "target_file": str(target)}


def _run_stage1(root: Path, skill_dir: Path) -> dict:
    script = skill_dir / "scripts" / "contact_stage1.py"
    target = _stage0_target(root)
    built = _run_json(script, [
        "build", "--program-root", root, "--target-file", target,
    ])
    verified = _run_json(script, [
        "verify", "--program-root", root, "--target-file", target,
    ])
    if built.get("status") != "ok" or verified.get("status") != "ok":
        raise SetupError("product Stage 1 runner did not produce a verified snapshot")
    snapshot = target.parent / "套磁阶段1候选.json"
    if not snapshot.is_file():
        raise SetupError(f"Stage 1 runner did not create {snapshot}")
    return {"build": built, "verify": verified, "snapshot_file": str(snapshot)}


def _assert_new_analysis_preconditions(root: Path, item_key: str) -> None:
    professor_dir = root / "教授研究" / "X分野" / PROFESSOR
    analysis_dir = professor_dir / "论文分析"
    preexisting = []
    for relative in FORBIDDEN_OUTPUTS:
        if (root / relative).exists():
            preexisting.append(relative)
    for pattern in ("*.md", "*.future_work.json", "*.facts.json"):
        preexisting.extend(path.name for path in analysis_dir.glob(pattern))
    if list(analysis_dir.glob("_chatgpt_handoff")):
        preexisting.append("论文分析/_chatgpt_handoff")
    if preexisting:
        raise SetupError(
            "the selected paper must require a new Stage-2 delegated analysis; "
            f"preexisting artifacts found: {sorted(preexisting)}")
    if not (analysis_dir / f"{item_key}.pdf").is_file():
        raise SetupError("the deterministic parseable PDF input is missing")


def prepare_stage2_fixture(*, program_root: Path, profile_root: Path,
                           consumer_root: Path,
                           zotero_http_url: str,
                           zotero_mcp_url: str,
                           output: Path,
                           fixture_run_id: str = "",
                           http_post=_http_post,
                           http_get=_http_get) -> dict:
    """Build and verify the complete producer-owned PC57-R1 local input."""
    validate_runtime_endpoints(zotero_http_url, zotero_mcp_url)
    run_id = _validate_expected_run_id(
        fixture_run_id
        or os.environ.get("FIXTURE_RUN_ID", "")
        or os.environ.get("ZOTERO_TEST_RUN_ID", ""))
    consumer_root = Path(consumer_root).resolve()
    installed_skill = validate_installed_skill_dir(
        consumer_root / ".agents" / "skills" / "professor-contact")

    probe_http_fixture(zotero_http_url, http_get=http_get)
    item_key = seed_zotero_paper(zotero_mcp_url=zotero_mcp_url, http_post=http_post)

    root = _prepare_program_root(program_root)
    profile_root = Path(profile_root).resolve()
    profile_path = profile_root / "套磁邮件/套磁信息.md"
    try:
        raw_hashes = _write_raw_inputs(root, item_key)
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            "# Synthetic applicant profile\n\n"
            "大学：Fixture University B\n研究科：Synthetic Routing Systems\n"
            "専攻：ルーティング安定性とネステッドデリゲーション\n",
            encoding="utf-8",
        )
        skill_dir = Path(installed_skill["path"])
        stage0 = _run_stage0(root, skill_dir)
        if stage0.get("status") != "ok":
            raise SetupError(f"Stage 0 setup failed: {stage0}")
        stage1 = _run_stage1(root, skill_dir)
        _assert_new_analysis_preconditions(root, item_key)
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise

    input_hashes = {
        "info.json": _sha256_file(root / "info.json"),
        f"教授研究/X分野/{PROFESSOR}/套磁目标.json": _sha256_file(_stage0_target(root)),
        f"教授研究/X分野/{PROFESSOR}/套磁阶段1候选.json":
            _sha256_file(_stage0_target(root).parent / "套磁阶段1候选.json"),
        f"教授研究/X分野/{PROFESSOR}/论文分析/{item_key}.pdf":
            _sha256_file(root / f"教授研究/X分野/{PROFESSOR}/论文分析/{item_key}.pdf"),
        "profile/套磁邮件/套磁信息.md": _sha256_file(profile_path),
    }
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "helper": HELPER_ID,
        "fixture_run_id": run_id,
        "zotero_http_url": zotero_http_url,
        "zotero_mcp_url": zotero_mcp_url,
        "item_keys": [item_key],
        "attachment_keys": [],
        "professor": PROFESSOR,
        "direction_id": DIRECTION_ID,
        "program_root": str(root),
        "profile_root": str(profile_root),
        "consumer_root": str(consumer_root),
        "installed_skill": installed_skill,
        "input_hashes": input_hashes,
        "raw_input_hashes": raw_hashes,
        "stage0": stage0,
        "stage1": stage1,
        "forbidden_outputs": list(FORBIDDEN_OUTPUTS),
        "manual_patch": "no",
    }
    _write_json(root / "fixture-manifest.json", evidence)
    output = Path(output).resolve()
    _write_json(output, evidence)
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare the issue #57 Stage-2 routing fixture")
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--zotero-http-url", required=True)
    parser.add_argument("--zotero-mcp-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-run-id", default="",
                        help="fixture run id from the disposable fixture env "
                             "(defaults to FIXTURE_RUN_ID / ZOTERO_TEST_RUN_ID)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evidence = prepare_stage2_fixture(
            program_root=args.program_root,
            profile_root=args.profile_root,
            consumer_root=args.consumer_root,
            zotero_http_url=args.zotero_http_url,
            zotero_mcp_url=args.zotero_mcp_url,
            output=args.output,
            fixture_run_id=args.fixture_run_id,
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
