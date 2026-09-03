#!/usr/bin/env python3
"""Deterministic Stage-2 paper input routing for professor-contact.

Routes relevant papers to paper-analysis with the priority OCR -> PDF ->
normalized Zotero abstract JSON. The helper never prints or returns abstract
content; exporter stdout is reduced to compact status/path data.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PaperInput:
    item_key: str
    paper: str | None
    level: str | None
    carrier: str | None
    status: str
    reason: str | None = None

    @property
    def gap_only_allowed(self) -> bool:
        return self.carrier in {"ocr", "pdf"}


def _absolute_existing(path: str | None) -> str | None:
    if not path:
        return None
    value = Path(path).expanduser()
    if not value.is_absolute() or not value.exists():
        return None
    return str(value.resolve())


def route_existing(item_key: str, ocr_path: str | None, pdf_path: str | None) -> PaperInput | None:
    """Route current local carriers without considering whether full analysis is needed."""
    ocr = _absolute_existing(ocr_path)
    if ocr:
        return PaperInput(item_key, ocr, "fulltext", "ocr", "ok")
    pdf = _absolute_existing(pdf_path)
    if pdf:
        return PaperInput(item_key, pdf, "fulltext", "pdf", "ok")
    return None


def export_missing(item_keys: Iterable[str], output_dir: Path, executable: str = "zotero-item-export") -> dict[str, PaperInput]:
    keys = list(dict.fromkeys(key.strip() for key in item_keys if key and key.strip()))
    if not keys:
        return {}
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # The exporter atomically overwrites successful keys but intentionally does
    # not delete an older file when a later export fails. Remove every expected
    # output before this invocation so an accepted file is necessarily fresh.
    clean_keys: list[str] = []
    routed: dict[str, PaperInput] = {}
    for key in keys:
        path = output_dir / f"{key}.json"
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            routed[key] = PaperInput(
                key, None, None, None, "error",
                f"cannot clear stale export: {exc.__class__.__name__}",
            )
        else:
            clean_keys.append(key)

    if not clean_keys:
        return routed

    command = [executable, *clean_keys, "--output-dir", str(output_dir)]
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
    except OSError as exc:
        reason = f"exporter unavailable: {exc.__class__.__name__}"
        routed.update({key: PaperInput(key, None, None, None, "error", reason) for key in clean_keys})
        return routed

    payload = None
    for line in reversed(result.stdout.splitlines()):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            payload = parsed
            break

    errors: dict[str, str] = {}
    if isinstance(payload, dict):
        for error in payload.get("errors", []) or []:
            if isinstance(error, dict) and error.get("item_key"):
                errors[str(error["item_key"])] = str(error.get("reason") or "export failed")[:200]

    for key in clean_keys:
        path = output_dir / f"{key}.json"
        if path.is_file():
            routed[key] = PaperInput(key, str(path.resolve()), "abstract", "abstract_json", "ok")
        else:
            reason = errors.get(key)
            if not reason:
                reason = "exporter failed" if result.returncode else "exporter produced no file"
            routed[key] = PaperInput(key, None, None, None, "error", reason)
    return routed


def route_batch(papers: list[dict], output_dir: Path, executable: str = "zotero-item-export") -> list[PaperInput]:
    results: dict[str, PaperInput] = {}
    missing: list[str] = []
    for paper in papers:
        key = str(paper["item_key"])
        existing = route_existing(key, paper.get("ocr_path"), paper.get("pdf_path"))
        if existing:
            results[key] = existing
        else:
            missing.append(key)
    results.update(export_missing(missing, output_dir, executable=executable))
    return [results[str(paper["item_key"])] for paper in papers]


def build_task_prompt(route: PaperInput, research_direction_file: str, save: str) -> str:
    if route.status != "ok" or not route.paper:
        raise ValueError(f"cannot build task prompt for failed route: {route.item_key}")
    return f"paper: {route.paper}\nresearch_direction_file: {research_direction_file}\nsave: {save}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", type=Path, required=True, help="JSON array with item_key/ocr_path/pdf_path")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--exporter", default="zotero-item-export")
    return parser


def main() -> None:
    args = _parser().parse_args()
    papers = json.loads(args.papers.read_text(encoding="utf-8"))
    routes = route_batch(papers, args.output_dir, executable=args.exporter)
    print(json.dumps({"status": "ok" if all(r.status == "ok" for r in routes) else "partial", "routes": [dict(asdict(r), gap_only_allowed=r.gap_only_allowed) for r in routes]}, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
