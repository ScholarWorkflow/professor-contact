"""Text-only transport projection using installed paper-analysis helpers."""
from __future__ import annotations

import json
import re
from pathlib import Path

MARKER = re.compile(r"(?m)^<!-- PDF_PAGE: ([1-9][0-9]*) -->[ \t]*\n?")


def page_texts(text: str, count: int) -> dict[int, str]:
    matches = list(MARKER.finditer(text))
    if [int(m[1]) for m in matches] != list(range(1, count + 1)):
        raise ValueError("physical_page_markers_missing")
    return {int(m[1]): text[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].rstrip()
            for i, m in enumerate(matches)}


def prepare_text(job: dict, skill_dir: Path, work: Path, run) -> tuple[bytes | None, list[int], str | None]:
    """Return text or a local preparation need; never call an OCR service."""
    prepared = json.loads(Path(job['future_work_prepare_local']).read_text(encoding='utf-8'))
    required = prepared.get('ocr_required_pages') or []
    if required:
        return None, required, 'future_work_pages_need_local_ocr_merge'
    count = prepared.get('page_count')
    qualities = prepared.get('page_quality')
    if not isinstance(count, int) or count < 1 or not isinstance(qualities, list):
        return None, [], 'page_metadata_unavailable'
    tiers = {q.get('page'): q.get('tier') for q in qualities if isinstance(q, dict)}
    if set(tiers) != set(range(1, count + 1)) or any(t not in {'trusted', 'washable', 'untrusted', 'empty'} for t in tiers.values()):
        return None, [], 'page_metadata_unavailable'
    pdf = Path(job['input_path_local'])
    script = skill_dir / 'scripts' / 'pdf_runtime.py'
    work.mkdir(parents=True, exist_ok=True)
    resolved = set()
    pages = None
    cache = Path(str(pdf) + '.llm_ocr.txt')
    if cache.is_file():
        validated = work / 'validated-fulltext.txt'
        proc = run(script, 'validate-fulltext-ocr-cache', '--pdf', str(pdf), '--cache', str(cache),
                   '--expected-sha256', job['input_sha256'], '--output', str(validated))
        if proc.returncode == 0 and validated.is_file():
            try:
                pages = page_texts(validated.read_text(encoding='utf-8'), count)
                resolved = {p for p, text in pages.items() if text.strip()}
            except ValueError:
                pass  # A cache without physical correspondence cannot serve this transport.
    if pages is None:
        source = prepared.get('source_pages')
        if isinstance(source, list) and len(source) == count and all(isinstance(p, dict) and isinstance(p.get('text'), str) for p in source):
            pages = {p.get('page'): p['text'] for p in source}
            if set(pages) != set(range(1, count + 1)):
                return None, [], 'physical_page_markers_missing'
            # Legacy resolved flags do not supply whole-page OCR text.
            resolved = {p['page'] for p in source if p.get('ocr_resolved') and p['text'].strip()}
        else:
            output = work / 'extracted.txt'
            proc = run(script, 'extract', str(pdf), '--output', str(output))
            if proc.returncode != 0 or not output.is_file():
                return None, [], 'text_extraction_failed'
            try:
                pages = page_texts(output.read_text(encoding='utf-8'), count)
            except ValueError:
                return None, [], 'physical_page_markers_missing'
    bad = {p for p, tier in tiers.items() if tier in {'untrusted', 'empty'}} - resolved
    page_cache = Path(str(pdf) + '.llm_ocr.pages.json')
    if bad and page_cache.is_file():
        validated = work / 'validated-pages.json'
        proc = run(script, 'validate-ocr-cache', '--pdf', str(pdf), '--cache', str(page_cache),
                   '--expected-sha256', job['input_sha256'], '--output', str(validated))
        if proc.returncode == 0 and validated.is_file():
            exact = json.loads(validated.read_text(encoding='utf-8')).get('pages', {})
            for p in sorted(bad):
                text = exact.get(str(p))
                if isinstance(text, str) and text.strip():
                    pages[p] = text
                    resolved.add(p)
    bad -= resolved
    untrusted = {p for p in bad if tiers[p] == 'untrusted'}
    has_trusted = any(t == 'trusted' for t in tiers.values())
    needs_ocr = untrusted or (bad if not has_trusted else set())
    if needs_ocr:
        return None, sorted(needs_ocr), 'text_pages_need_local_ocr'
    missing = sorted(p for p in pages if (tiers[p] == 'empty' and p not in resolved) or not pages[p].strip())
    # Keep every physical page, including ordinary blank/missing pages.
    text = '\n\n'.join(f'<!-- PDF_PAGE: {p} -->\n{pages[p]}' for p in range(1, count + 1)) + '\n'
    return text.encode('utf-8'), missing, None
