"""Text-only transport projection and future-work evidence from one prepare.

Transport text and future-work evidence must come from the same canonical
``prepare.json``. A prepare that predates ``source_pages`` is regenerated once
from the original PDF through the installed ``future_work.py prepare``
contract; unreadable pages are only filled from same-source, fingerprint
validated OCR caches and merged by the installed ``merge-ocr``. Nothing here
calls an OCR service, copies a PDF, or writes to the caller's input files.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MARKER = re.compile(r"(?m)^<!-- PDF_PAGE: ([1-9][0-9]*) -->[ \t]*\n?")
TIERS = {"trusted", "washable", "untrusted", "empty"}


def page_texts(text: str, count: int) -> dict[int, str]:
    matches = list(MARKER.finditer(text))
    if [int(m[1]) for m in matches] != list(range(1, count + 1)):
        raise ValueError("physical_page_markers_missing")
    return {int(m[1]): text[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].rstrip()
            for i, m in enumerate(matches)}


def _blocked(reason: str, pages=()) -> dict:
    return {
        "text": None,
        "missing_pages": sorted({int(page) for page in pages}),
        "reason": reason,
        "prepare_path": None,
        "candidates_path": None,
        "page_count": None,
    }


def _json_object(path) -> dict | None:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _page_count(prepared: dict) -> int | None:
    count = prepared.get("page_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        return None
    return count


def _source_pages(prepared: dict) -> dict[int, str] | None:
    """Return every page's prepared text or None when the prepare is incomplete."""
    count = _page_count(prepared)
    pages = prepared.get("source_pages")
    if count is None or not isinstance(pages, list):
        return None
    collected: dict[int, str] = {}
    for item in pages:
        if not isinstance(item, dict):
            return None
        page = item.get("page")
        if (not isinstance(page, int) or isinstance(page, bool) or page < 1
                or not isinstance(item.get("text"), str)):
            return None
        collected[page] = item["text"]
    return collected if set(collected) == set(range(1, count + 1)) else None


def _page_tiers(prepared: dict) -> dict[int, str] | None:
    count = _page_count(prepared)
    qualities = prepared.get("page_quality")
    if count is None or not isinstance(qualities, list):
        return None
    tiers: dict[int, str] = {}
    for item in qualities:
        if not isinstance(item, dict):
            return None
        page, tier = item.get("page"), item.get("tier")
        if (not isinstance(page, int) or isinstance(page, bool) or page < 1
                or tier not in TIERS):
            return None
        tiers[page] = tier
    return tiers if set(tiers) == set(range(1, count + 1)) else None


def _page_numbers(value, count: int) -> set[int] | None:
    if value is None:
        return set()
    if not isinstance(value, list):
        return None
    numbers = set()
    for page in value:
        if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= count:
            return None
        numbers.add(page)
    return numbers


def _cached_pages(script: Path, pdf: Path, sha256: str, wanted: set[int], count: int,
                  work: Path, run) -> dict[int, str]:
    """Collect exact page text for ``wanted`` from same-source validated caches."""
    texts: dict[int, str] = {}
    if not wanted:
        return texts
    page_cache = Path(str(pdf) + ".llm_ocr.pages.json")
    if page_cache.is_file():
        validated = work / "validated-pages.json"
        proc = run(script, "validate-ocr-cache", "--pdf", str(pdf), "--cache", str(page_cache),
                   "--expected-sha256", sha256, "--output", str(validated))
        if proc.returncode == 0 and validated.is_file():
            payload = _json_object(validated) or {}
            exact = payload.get("pages") if isinstance(payload.get("pages"), dict) else {}
            for raw_page, text in exact.items():
                try:
                    page = int(raw_page)
                except (TypeError, ValueError):
                    continue
                if page in wanted and isinstance(text, str) and text.strip():
                    texts[page] = text
    remaining = wanted - set(texts)
    full_cache = Path(str(pdf) + ".llm_ocr.txt")
    if remaining and full_cache.is_file():
        validated = work / "validated-fulltext.txt"
        proc = run(script, "validate-fulltext-ocr-cache", "--pdf", str(pdf), "--cache", str(full_cache),
                   "--expected-sha256", sha256, "--output", str(validated))
        if proc.returncode == 0 and validated.is_file():
            try:
                parsed = page_texts(validated.read_text(encoding="utf-8"), count)
            except (OSError, UnicodeDecodeError, ValueError):
                parsed = {}
            for page in sorted(remaining):
                text = parsed.get(page)
                if isinstance(text, str) and text.strip():
                    texts[page] = text
    return texts


def prepare_text(job: dict, skill_dir: Path, work: Path, run) -> dict:
    """Return canonical evidence plus the transport text built from it.

    The result carries ``text``/``missing_pages``/``reason`` and, on success,
    ``prepare_path``/``candidates_path``/``page_count`` for the same canonical
    prepare. A non-empty ``reason`` means the text is not ready; the caller
    must report the specific pages instead of uploading a partial package.
    """
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    pdf = Path(job["input_path_local"])
    sha256 = job["input_sha256"]
    scripts = Path(skill_dir) / "scripts"
    future_work = scripts / "future_work.py"
    pdf_runtime = scripts / "pdf_runtime.py"

    prepared = _json_object(job["future_work_prepare_local"])
    if prepared is None or prepared.get("pdf_sha256") != sha256:
        return _blocked("page_metadata_unavailable")
    if _source_pages(prepared) is None:
        # A prepare from before source text existed is regenerated once from the
        # same original PDF through the installed helper; the PDF stays in place.
        debug = work / "regenerated"
        proc = run(future_work, "prepare", str(pdf), "--debug-dir", str(debug))
        regenerated = _json_object(debug / "prepare.json") if proc.returncode == 0 else None
        regenerated_candidates = debug / "candidates.json"
        if (regenerated is None or regenerated.get("pdf_sha256") != sha256
                or _source_pages(regenerated) is None or not regenerated_candidates.is_file()):
            return _blocked("text_extraction_failed")
        prepared = regenerated

    count = _page_count(prepared)
    tiers = _page_tiers(prepared)
    if count is None or tiers is None:
        return _blocked("page_metadata_unavailable")
    resolved = _page_numbers(prepared.get("ocr_resolved_pages"), count)
    required = _page_numbers(prepared.get("ocr_required_pages"), count)
    if resolved is None or required is None:
        return _blocked("page_metadata_unavailable")
    bad = {page for page, tier in tiers.items() if tier in {"untrusted", "empty"}}
    unresolved_bad = bad - resolved
    wanted = (required - resolved) | unresolved_bad
    provided = _cached_pages(pdf_runtime, pdf, sha256, wanted, count, work, run)

    blocking = required - resolved - set(provided)
    untrusted = {page for page in unresolved_bad if tiers[page] == "untrusted"}
    if not blocking:
        blocking |= untrusted - set(provided)
    if not any(tier == "trusted" for tier in tiers.values()):
        blocking |= unresolved_bad - set(provided)
    if blocking:
        reason = ("future_work_pages_need_local_ocr_merge"
                  if blocking & required else "text_pages_need_local_ocr")
        return _blocked(reason, blocking)

    source_prepare = work / "prepare.json"
    source_candidates = work / "candidates.json"
    _write_json(source_prepare, prepared)
    usable = {page: provided[page] for page in sorted(provided)
              if page in required | unresolved_bad}
    if usable:
        ocr_path = work / "ocr_pages.json"
        _write_json(ocr_path, {
            "schema": 1,
            "pdf_sha256": sha256,
            "pages": {str(page): usable[page] for page in usable},
        })
        proc = run(future_work, "merge-ocr", "--prepared", str(source_prepare),
                   "--ocr", str(ocr_path))
        merged = None
        if proc.returncode == 0:
            try:
                merged = json.loads(proc.stdout.splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                merged = None
        if not isinstance(merged, dict) or merged.get("pdf_sha256") != sha256:
            return _blocked("text_extraction_failed")
        merged_tiers = _page_tiers(merged)
        merged_resolved = _page_numbers(merged.get("ocr_resolved_pages"), count)
        merged_required = _page_numbers(merged.get("ocr_required_pages"), count)
        if merged_tiers is None or merged_resolved is None or merged_required is None:
            return _blocked("page_metadata_unavailable")
        if merged_required - merged_resolved:
            return _blocked("future_work_pages_need_local_ocr_merge",
                            merged_required - merged_resolved)
        prepared = merged
        tiers = merged_tiers
        resolved = merged_resolved
        required = merged_required
        _write_json(source_prepare, prepared)

    pages = _source_pages(prepared)
    if pages is None:
        return _blocked("physical_page_markers_missing")
    canonical_candidates = prepared.get("candidates")
    if not isinstance(canonical_candidates, list):
        return _blocked("page_metadata_unavailable")
    missing = sorted(page for page in pages
                     if (tiers.get(page) == "empty" and page not in resolved)
                     or not pages[page].strip())
    text = "\n\n".join(f"<!-- PDF_PAGE: {page} -->\n{pages[page]}"
                       for page in range(1, count + 1)) + "\n"
    _write_json(source_candidates, {"candidates": canonical_candidates})
    return {
        "text": text.encode("utf-8"),
        "missing_pages": missing,
        "reason": None,
        "prepare_path": str(source_prepare),
        "candidates_path": str(source_candidates),
        "page_count": count,
    }
