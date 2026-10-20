#!/usr/bin/env python3
"""Stage-2 helper module for ``contact_state.py``.

The runner loads this helper by path next to itself and calls :func:`build`
once with its own helper functions and shared constants. The factory binds
those names in an enclosing scope, so the functions below keep the exact
bodies they had inside the runner (only their indentation changed). The
module never imports the runner, never adds itself to ``sys.path`` and
never builds a second failure channel.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import re
import types





def build(*, fail,
          GAP_STATUSES,
          PLACEHOLDER_RE,
          now_utc,
          read_json_file,
          truncate,
          rel_path,
          filename_component,
          direction_machine_id,
          pack_paper_index,
          direction_papers,
          direction_relevant_keys,
          direction_provisional_member_keys,
          shortlist_size,
          Stage2Context,
          Stage2PackRefineContext):
    def validate_freshness_results(ctx: Stage2Context, results_dir: Path,
                                   required: dict) -> dict:
        """required: ckey -> list of pending job items. Returns ckey -> {gap_id: status_record}."""
        accepted = {}
        for ckey, items in required.items():
            pending = [item for item in items if not item["cached"]]
            if not pending:
                accepted[ckey] = {item["gap"]["gap_id"]: item["status"] for item in items}
                continue
            result_path = results_dir / f"freshness-{filename_component(ckey)}.json"
            data, error = read_json_file(result_path)
            if error:
                fail("result_missing", f"{result_path}: {error}")
            if not isinstance(data, dict) or data.get("schema") != 1 or data.get("kind") != "freshness":
                fail("invalid_result_json", f"{result_path}: schema/kind must be 1/freshness")
            data_direction_id = data.get("direction_id") or data.get("collection_key")
            if data_direction_id != ckey:
                fail("invalid_result_json",
                     f"{result_path}: direction_id {data_direction_id!r} does not match the job direction {ckey!r}")
            rows = data.get("results")
            if not isinstance(rows, list):
                fail("invalid_result_json", f"{result_path}: results must be a list")
            by_gap = {}
            judge_ids = {item["gap"]["gap_id"] for item in items}
            for row in rows:
                if not isinstance(row, dict):
                    fail("invalid_result_json", f"{result_path}: results[] must be objects")
                gap_id = row.get("gap_id")
                if not isinstance(gap_id, str):
                    fail("invalid_result_json", f"{result_path}: gap_id must be a string")
                if gap_id not in judge_ids:
                    fail("unknown_reference_id",
                         f"{result_path}: gap outside package: {gap_id!r} "
                         f"(likely mistyped; copy one of the job model_input gap ids verbatim: "
                         f"{sorted(judge_ids)})")
                if gap_id in by_gap:
                    fail("invalid_result_json", f"{result_path}: duplicate result for gap {gap_id}")
                by_gap[gap_id] = row
            pending_ids = {item["gap"]["gap_id"] for item in pending}
            if not pending_ids.issubset(set(by_gap)):
                missing = sorted(pending_ids - set(by_gap))
                fail("invalid_result_json", f"{result_path}: missing results for gaps: {missing}")
            statuses = {}
            for item in pending:
                gap_id = item["gap"]["gap_id"]
                row = by_gap.get(gap_id)
                if row is None:
                    fail("invalid_result_json", f"{result_path}: missing result for gap {gap_id[:12]}…")
                status = row.get("status")
                if status not in GAP_STATUSES:
                    fail("invalid_result_json", f"{result_path}: bad status for {gap_id[:12]}…")
                cand_ids = row.get("candidate_paper_ids") or []
                if not isinstance(cand_ids, list) or any(not isinstance(c, str) for c in cand_ids):
                    fail("invalid_result_json", f"{result_path}: candidate_paper_ids must be a string list")
                if len(set(cand_ids)) != len(cand_ids):
                    fail("invalid_result_json", f"{result_path}: duplicate candidate paper IDs for {gap_id[:12]}…")
                allowed_ids = set()
                for tier in item["cands"]["tiers"].values():
                    allowed_ids.update(tier)
                unknown_ids = [c for c in cand_ids if c not in allowed_ids]
                if unknown_ids:
                    fail("unknown_reference_id",
                         f"{result_path}: candidate_paper_ids outside package for {gap_id[:12]}…: {unknown_ids}")
                evidence_value = row.get("evidence")
                if not isinstance(evidence_value, str):
                    fail("invalid_result_json", f"{result_path}: evidence must be a string for {gap_id[:12]}…")
                evidence = evidence_value.strip()
                if not evidence:
                    fail("invalid_result_json", f"{result_path}: evidence required for {gap_id[:12]}…")
                downgraded = False
                if status == "partial" and (not (row.get("completed_part") or "").strip() or
                                            not (row.get("remaining_gap") or "").strip()):
                    status, downgraded = "unknown", True
                record = {
                    "gap_id": gap_id, "item_key": item["gap"]["item_key"],
                    "status": status,
                    "model_evidence": evidence,
                    "candidate_paper_ids": cand_ids,
                    "candidate_fingerprint": item["cand_fp"],
                    "gap_fingerprint": item["gap_fp"],
                    "evaluated_at": now_utc(),
                    "confidence": row.get("confidence") if row.get("confidence") in ("high", "medium", "low") else "low",
                    "completed_part": (row.get("completed_part") or "").strip() or None,
                    "remaining_gap": (row.get("remaining_gap") or "").strip() or None,
                    "downgraded": downgraded,
                }
                statuses[gap_id] = record
            for item in items:
                if item["cached"]:
                    statuses.setdefault(item["gap"]["gap_id"], item["status"])
            accepted[ckey] = statuses
        return accepted

    def narrative_scope(ctx: Stage2Context, ckey: str) -> dict:
        for plan in ctx.direction_plans:
            if plan["did"] == ckey:
                return {
                    "papers": {key for key in direction_relevant_keys(plan["direction"])
                                if key in ctx.papers},
                    "later": set(ctx.narrative_later_keys(plan)),
                    "gaps": {g["gap_id"] for g in plan["ranked"]},
                }
        return {"papers": set(), "later": set(), "gaps": set()}

    def validate_narrative_entry(ctx: Stage2Context, path: Path, entry: dict,
                                 expected_did: str | None = None, *,
                                 scope: dict | None = None,
                                 allowed_directions: set | None = None) -> tuple[str, dict]:
        if not isinstance(entry, dict):
            fail("invalid_result_json", f"{path}: narrative entry must be an object")
        did = entry.get("direction_id") or entry.get("collection_key")
        if expected_did is not None and did != expected_did:
            fail("invalid_result_json", f"{path}: expected direction {expected_did}, got {did}")
        if not isinstance(did, str) or not did.strip():
            fail("invalid_result_json", f"{path}: direction_id must be a non-empty string")
        if scope is None:
            scope = narrative_scope(ctx, did)
        if allowed_directions is None:
            allowed_directions = {plan["did"] for plan in ctx.direction_plans}
        if did not in allowed_directions:
            fail("invalid_result_json", f"{path}: unexpected direction {did}")
        positioning = entry.get("positioning")
        if not isinstance(positioning, list) or not positioning:
            fail("invalid_result_json", f"{path}: {did} positioning must be a non-empty list")
        checked = []
        for block in positioning:
            if not isinstance(block, dict) or not isinstance(block.get("text"), str):
                fail("invalid_result_json", f"{path}: positioning blocks need text")
            for field in ("concrete_object", "input_example", "output_example"):
                if not isinstance(block.get(field), str) or not block[field].strip():
                    fail("invalid_result_json", f"{path}: positioning blocks need {field}")
            if any(block[field].strip().startswith(("输入", "输出")) and
                   ("所处理的数据或用户操作" in block[field] or "论文展示的" in block[field])
                   for field in ("input_example", "output_example")):
                fail("invalid_result_json", f"{path}: positioning examples must be concrete")
            placeholders = set()
            for kind, value in PLACEHOLDER_RE.findall(block.get("text") or ""):
                if kind == "P":
                    placeholders.add(f"paper:{value}")
                elif kind == "L":
                    placeholders.add(f"later:{value}")
                else:
                    placeholders.add(f"gap:{value}")
            raw_refs = block.get("refs")
            if not isinstance(raw_refs, list) or not all(isinstance(ref, str) for ref in raw_refs):
                fail("invalid_result_json", f"{path}: {did} refs must be a string list")
            refs = set(raw_refs)
            if len(raw_refs) != len(refs):
                fail("invalid_result_json", f"{path}: {did} refs contain duplicates")
            for ref in refs:
                ref_kind, _, ref_id = ref.partition(":")
                pool = (scope["papers"] if ref_kind == "paper" else
                        scope["later"] if ref_kind == "later" else scope["gaps"])
                if ref_kind not in ("paper", "later", "gap") or ref_id not in pool:
                    fail("unknown_reference_id",
                         f"{path}: ref {ref!r} outside package (likely mistyped; legal "
                         f"{ref_kind} ids: {sorted(pool)})")
            if placeholders != refs:
                fail("invalid_result_json",
                     f"{path}: {did} placeholders {sorted(placeholders)} != refs {sorted(refs)}")
            checked.append({"kind": block.get("kind") if block.get("kind") in ("para", "bullet") else "bullet",
                            "text": block["text"],
                            "refs": list(raw_refs),
                            "concrete_object": block["concrete_object"].strip(),
                            "input_example": block["input_example"].strip(),
                            "output_example": block["output_example"].strip()})
        raw_gap_notes = entry.get("gap_notes") or []
        if not isinstance(raw_gap_notes, list):
            fail("invalid_result_json", f"{path}: {did} gap_notes must be a list")
        gap_notes = {}
        for note in raw_gap_notes:
            if not isinstance(note, dict):
                fail("invalid_result_json", f"{path}: {did} gap_notes[] must be objects")
            gap_id = note.get("gap_id")
            if gap_id not in scope["gaps"]:
                fail("unknown_reference_id",
                     f"{path}: gap note outside package: {gap_id!r} (likely mistyped; "
                     f"copy one of the job model_input gap ids verbatim: {sorted(scope['gaps'])})")
            if gap_id in gap_notes:
                fail("invalid_result_json", f"{path}: duplicate gap note {gap_id}")
            if not isinstance(note.get("summary"), str) or not isinstance(note.get("explanation"), str):
                fail("invalid_result_json", f"{path}: gap note {gap_id} needs string summary/explanation")
            gap_notes[gap_id] = {
                "summary": truncate(note.get("summary"), 120),
                "explanation": truncate(note.get("explanation"), 300)}
        return did, {"positioning": checked, "gap_notes": gap_notes}

    def validate_narrative(ctx: Stage2Context, results_dir: Path, needed_keys: list) -> dict:
        path = results_dir / "narrative.json"
        data, error = read_json_file(path)
        if error:
            fail("result_missing", f"{path}: {error}")
        if not isinstance(data, dict) or data.get("schema") != 1 or data.get("kind") != "narrative":
            fail("invalid_result_json", f"{path}: schema/kind must be 1/narrative")
        if not isinstance(data.get("directions"), list):
            fail("invalid_result_json", f"{path}: directions must be a list")
        narratives = {}
        for entry in data["directions"]:
            ckey, checked = validate_narrative_entry(ctx, path, entry)
            if ckey not in needed_keys:
                fail("invalid_result_json", f"{path}: unexpected direction {ckey}")
            if ckey in narratives:
                fail("invalid_result_json", f"{path}: duplicate narrative for {ckey}")
            narratives[ckey] = checked
        for ckey in needed_keys:
            if ckey not in narratives:
                fail("invalid_result_json", f"{path}: missing narrative for {ckey}")
        return narratives

    def citation_render(item_key: str, paper: dict, professor_dir: Path,
                        seen: dict) -> str:
        title = paper.get("title") or item_key
        link = f"[{title}](zotero://select/library/items/{item_key})"
        if item_key not in seen:
            seen[item_key] = True
            analysis = paper.get("analysis_file")
            if analysis:
                return link + f"｜[分析]({rel_path(Path(analysis), professor_dir)})"
            return link
        year = paper.get("year") or "年份不明"
        return f"[《{title}》](zotero://select/library/items/{item_key})（{year}）"

    def rendered_markdown_block_lines(text: str) -> list[str]:
        """Split one rendered list item into the physical rows Markdown exposes."""
        lines = text.splitlines()
        if not lines:
            return [""]
        if text.endswith(("\n", "\r", "\v", "\f", "\x1c", "\x1d", "\x1e",
                          "\x85", "\u2028", "\u2029")):
            lines.append("")
        return lines

    def render_positioning_block_parts(block: dict, paper_lookup: dict, gap_no: dict,
                                       professor_dir: Path, seen: dict,
                                       fallback_papers: dict | None = None,
                                       meta_for=None) -> list:
        """Render one positioning block as ordered (text, ownership) segments."""
        text = block["text"]
        fallback_papers = fallback_papers or {}

        def replace(match):
            kind, value = match.group(1), match.group(2)
            if kind == "G":
                number = gap_no.get(value)
                return f"future work #{number}" if number else "future work（本轮未选，见排除清单）"
            paper = paper_lookup.get(value) or fallback_papers.get(value) or {
                "title": None, "year": None, "analysis_file": None}
            return citation_render(value, paper, professor_dir, seen)

        text = PLACEHOLDER_RE.sub(replace, text)

        def meta(field):
            return meta_for(field) if meta_for else None

        prefix = "- " if block.get("kind") == "bullet" else ""
        parts = [(prefix, meta("template")), (text, meta("text"))]
        for field, label in (("concrete_object", "；具体对象："),
                             ("input_example", "；输入："),
                             ("output_example", "；输出：")):
            parts.append((label, meta("template")))
            parts.append((block.get(field, ""), meta(field)))
        parts.append(("。", meta("template")))
        return parts

    def render_positioning_block(block: dict, paper_lookup: dict, gap_no: dict,
                                 professor_dir: Path, seen: dict,
                                 fallback_papers: dict | None = None) -> str:
        """Render one structured positioning block exactly as the analysis view does."""
        return "".join(text for text, _meta in render_positioning_block_parts(
            block, paper_lookup, gap_no, professor_dir, seen, fallback_papers))

    def redact_item_keys(text: str, papers: dict) -> str:
        """Keep deterministic human-facing red lines free of internal item keys."""
        rendered = text
        for key in sorted((key for key in papers if key), key=len, reverse=True):
            if key in rendered:
                rendered = rendered.replace(key, papers[key].get("title") or "该论文")
        return re.sub(r"(?<![A-Za-z0-9])[A-Z0-9]{8}(?![A-Za-z0-9])", "相关论文", rendered)

    STAGE2_ZOTERO_PREFIX = "zotero://select/library/items/"
    STAGE2_MARKDOWN_LINK_RE = re.compile(r"\[([^\]\n]*)\]\(([^)\n]*)\)")
    STAGE2_BARE_URL_RE = re.compile(r"https?://[^\s<>()]+")

    def stage2_trusted_citation_title(title_for, key: str, *, direction,
                                      gap_id, field) -> str:
        title = title_for(key)
        if title is None:
            fail("missing_paper_reference_title",
                 f"cannot render the declared paper reference {key} in {field}: no trusted "
                 "title exists in the current structured records or the accepted input pack; "
                 "fix the source data instead of editing the managed Markdown",
                 item_key=key, direction=direction, gap_id=gap_id, field=field)
        return title

    def stage2_replace_declared_citations(text: str, declared_keys, title_for, *,
                                          direction, gap_id, field) -> str:
        """Display declared paper references as trusted titles plus Zotero links.

        Only structured references (the field's declared candidate/completed keys or
        an explicit `zotero://select/library/items/<key>` link) may turn into a
        citation. Ordinary prose, dates and eight-character strings without a
        structured reference stay untouched; external links and their labels are
        never rewritten.
        """
        if not isinstance(text, str) or not text:
            return text

        def link_replace(match):
            label, destination = match.group(1), match.group(2)
            if not destination.startswith(STAGE2_ZOTERO_PREFIX):
                return match.group(0)
            key = destination[len(STAGE2_ZOTERO_PREFIX):].strip()
            title = stage2_trusted_citation_title(
                title_for, key, direction=direction, gap_id=gap_id, field=field)
            if label == title:
                return match.group(0)
            return f"[{title}]({destination})"

        rendered = STAGE2_MARKDOWN_LINK_RE.sub(link_replace, text)
        keys = sorted({key for key in declared_keys if isinstance(key, str) and key},
                      key=len, reverse=True)
        if not keys:
            return rendered
        protected = [(match.start(), match.end())
                     for match in STAGE2_MARKDOWN_LINK_RE.finditer(rendered)]
        for match in STAGE2_BARE_URL_RE.finditer(rendered):
            if any(start <= match.start() < end for start, end in protected):
                continue
            protected.append((match.start(), match.end()))
        protected.sort()
        key_pattern = re.compile(
            r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(key) for key in keys)
            + r")(?![A-Za-z0-9])")

        def bare_replace(match):
            key = match.group(0)
            title = stage2_trusted_citation_title(
                title_for, key, direction=direction, gap_id=gap_id, field=field)
            return f"[{title}]({STAGE2_ZOTERO_PREFIX}{key})"

        pieces, cursor = [], 0
        for start, end in protected:
            pieces.append(key_pattern.sub(bare_replace, rendered[cursor:start]))
            pieces.append(rendered[start:end])
            cursor = end
        pieces.append(key_pattern.sub(bare_replace, rendered[cursor:]))
        return "".join(pieces)

    class Stage2RenderDocument:
        """Accumulate the exact managed Markdown body plus its ownership map.

        Every text segment carries the source/generator/narrative/excluded region
        it came from, so the validator can look up ownership by the final physical
        line and character interval instead of reverse-engineering the Markdown.
        """

        def __init__(self):
            self.rows: list[list] = []
            self.fragments: list[dict] = []

        def add(self, *segments) -> None:
            row: list = []
            self.rows.append(row)
            for segment in segments:
                if isinstance(segment, str):
                    text, meta = segment, None
                else:
                    text, meta = segment
                if text is None:
                    continue
                if meta is not None and not isinstance(meta, dict):
                    meta = None
                pieces = re.split(
                    "\r\n|[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]",
                    str(text))
                for index, piece in enumerate(pieces):
                    if index:
                        row = []
                        self.rows.append(row)
                    if meta is not None and not meta.get("_fid"):
                        self.fragments.append(meta)
                        meta["_fid"] = len(self.fragments)
                    if piece:
                        row.append((piece, meta))

        def add_line(self, text: str, meta=None) -> None:
            self.add((text, meta) if meta is not None else text)

        def blank(self) -> None:
            self.rows.append([])

        def build(self) -> tuple[str, dict]:
            while self.rows and not any(text for text, _meta in self.rows[-1]):
                self.rows.pop()
            lines = ["".join(text for text, _meta in row) for row in self.rows]
            body = "\n".join(lines) + "\n"
            ranges: dict[int, list] = {id(meta): [] for meta in self.fragments}
            for line_index, row in enumerate(self.rows):
                column = 0
                for text, meta in row:
                    if meta is not None:
                        ranges[id(meta)].append([line_index, column, column + len(text)])
                    column += len(text)
            fragments = []
            for meta in self.fragments:
                entry = {key: value for key, value in meta.items()
                         if not str(key).startswith("_")}
                entry["ranges"] = ranges[id(meta)]
                fragments.append(entry)
            return body, {"version": 1, "line_count": len(lines),
                          "fragments": fragments}

    def build_direction_pack(ctx: Stage2Context, plan: dict, statuses: dict,
                             narrative: dict | None) -> tuple[dict, dict]:
        """Build one v2 pack direction plus its canonical paper records.

        Returns (direction, papers) — the caller merges `papers` into the
        professor-level canonical map (issue #8 §3.3): a shared paper keeps ONE
        machine record regardless of how many directions reference it.
        """
        direction = plan["direction"]
        judge, ranked = [], plan["ranked"]
        judge = ctx.judge_set(plan)
        judged_ids = {g["gap_id"] for g in judge}
        blacklist, anchorable = [], []
        for gap in ranked:
            record = statuses.get(gap["gap_id"])
            status = record["status"] if record else "unknown"
            entry = {
                "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                "authorship": gap.get("authorship"),
                "quote": gap["quote"], "translation_zh": gap["translation_zh"],
                "source": gap.get("source"), "page": gap.get("page"),
                "named_by_user": gap.get("named_by_user", False),
            }
            if status == "done_by_self":
                blacklist.append({
                    "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                    "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                    "completed_by_item_key": (record.get("candidate_paper_ids") or [None])[0],
                    "candidate_paper_ids": list(record.get("candidate_paper_ids") or []),
                    "evidence": record.get("model_evidence"),
                    "quote_trunc": truncate(gap["quote"], 120),
                    "translation_zh": truncate(gap["translation_zh"], 120),
                    "confidence": record.get("confidence"),
                    "evaluated_at": record.get("evaluated_at")})
                continue
            if not record:
                entry.update({"status": "unknown", "evidence": None, "confidence": "low",
                              "evaluated_at": None, "not_judged": True,
                              "completed_part": None, "remaining_gap": None,
                              "candidate_paper_ids": []})
            else:
                entry.update({
                    "status": record["status"], "evidence": record.get("model_evidence"),
                    "confidence": record.get("confidence"),
                    "evaluated_at": record.get("evaluated_at"),
                    "completed_part": record.get("completed_part"),
                    "remaining_gap": record.get("remaining_gap"),
                    "candidate_paper_ids": record.get("candidate_paper_ids") or [],
                    "cache_hit": bool(record.get("cache_hit")),
                    "downgraded": bool(record.get("downgraded"))})
            anchorable.append(entry)
        size = shortlist_size(len(anchorable))
        shortlist = anchorable[:size]
        shortlist_ids = {g["gap_id"] for g in shortlist}
        excluded, number = [], len(shortlist)
        for gap in anchorable[size:]:
            number += 1
            excluded.append({
                "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                "authorship": gap.get("authorship"), "quote": gap.get("quote"),
                "translation_zh": gap.get("translation_zh"), "source": gap.get("source"),
                "page": gap.get("page"), "status": gap.get("status"),
                "evidence": gap.get("evidence"), "confidence": gap.get("confidence"),
                "completed_part": gap.get("completed_part"),
                "remaining_gap": gap.get("remaining_gap"),
                "candidate_paper_ids": gap.get("candidate_paper_ids") or [],
                "quote_trunc": truncate(gap["quote"], 80),
                "reason": "low_rank（本轮未选，不代表不重要）"})
        # R1: authoritative membership starts from the ORIGINAL provisional members
        # only. `relevant_keys` is the analysis reference scope (P citations,
        # future work, gaps) and can never add a member; accepted add/remove
        # decisions are applied later by cmd_stage2_finalize.
        direction = plan["direction"]
        original_members = direction_provisional_member_keys(direction)
        if original_members is None:
            fail("invalid_facts",
                 f"direction {plan['did']} has no original formal member source "
                 "(provisional_member_keys/member_keys missing); Stage 2 cannot rebuild "
                 "authoritative membership from the analysis reference set")
        relevant_keys = []
        seen_relevant: set = set()
        for key in direction_relevant_keys(direction):
            if isinstance(key, str) and key not in seen_relevant:
                seen_relevant.add(key)
                relevant_keys.append(key)
        supporting_keys = []
        papers = {}
        named = set(direction.get("named_keys") or [])
        ordered = sorted(original_members, key=lambda k: (
            0 if k in named else 1,
            -(ctx.papers[k].get("year") or 0) if k in ctx.papers else 0, k))
        for key in ordered:
            paper = ctx.papers.get(key)
            if not paper:
                continue
            facts_record, facts_state, facts_error = ctx.facts_for(key)
            papers[key] = {
                "item_key": key, "title": paper.get("title"), "year": paper.get("year"),
                "authorship": paper.get("authorship"),
                "analysis_file": paper.get("analysis_file"),
                "pdf_available": bool(paper.get("has_pdf")),
                "facts_state": facts_state,
                "facts_error": facts_error,
                "paper_facts": facts_record,
            }
            supporting_keys.append(key)
        # Reference-scope papers live in the SAME professor-level canonical map so
        # a P citation keeps one trusted record (title/year/authorship/analysis
        # path) after the temporary facts expire. They never enter members.
        for key in sorted(relevant_keys):
            if key in papers:
                continue
            paper = ctx.papers.get(key)
            if not paper:
                continue
            facts_record, facts_state, facts_error = ctx.facts_for(key)
            papers[key] = {
                "item_key": key, "title": paper.get("title"), "year": paper.get("year"),
                "authorship": paper.get("authorship"),
                "analysis_file": paper.get("analysis_file"),
                "pdf_available": bool(paper.get("has_pdf")),
                "facts_state": facts_state,
                "facts_error": facts_error,
                "paper_facts": facts_record,
            }
        note = direction.get("user_note") or ""
        narrative_later_papers = {}
        narrative_data = narrative if isinstance(narrative, dict) else {}
        for block in narrative_data.get("positioning", []):
            if not isinstance(block, dict):
                continue
            for kind, key in PLACEHOLDER_RE.findall(block.get("text") or ""):
                if kind != "L" or key in narrative_later_papers:
                    continue
                paper = ctx.papers.get(key)
                if paper:
                    narrative_later_papers[key] = {
                        "item_key": key, "title": paper.get("title"),
                        "year": paper.get("year"), "authorship": paper.get("authorship"),
                        "analysis_file": paper.get("analysis_file")}
        pack_direction = {
            "direction_id": plan["did"],
            "collection_key": direction.get("collection_key"),
            "name_ja": direction.get("name_ja"), "name_zh": direction.get("name_zh"),
            "status": direction.get("status") or "active",
            "input_fingerprint": plan["fingerprint"],
            "user_note": note,
            "credibility": direction.get("credibility") or {},
            "red_lines": direction.get("red_lines") or [],
            "named_keys": list(direction.get("named_keys") or []),
            "supporting_item_keys": supporting_keys,
            # Persisted analysis reference scope (an explicit empty list is an
            # empty P licence). Kept strictly separate from authoritative members.
            "relevant_keys": relevant_keys,
            "resolved_addition_keys": [],
            "gap_pool_count": len(plan["pool"]),
            "gap_shortlist": [
                dict(g, no=index + 1) for index, g in enumerate(shortlist)],
            "gaps_excluded": excluded,
            "completed_gap_blacklist": blacklist,
            "version_families": ctx.families,
            "authorship_line": (direction.get("credibility") or {}).get("authorship_line"),
            "narrative_later_papers": narrative_later_papers,
            "narrative": narrative,
        }
        return pack_direction, papers

    def render_analysis_document(ctx: Stage2Context, pack: dict,
                                 state_fingerprint: str) -> tuple[str, dict]:
        """Render the managed analysis body plus its generated ownership map."""
        professor = ctx.professor
        pack_directions = pack.get("directions") or []
        for direction in pack_directions:
            stage2_require_later_paper_titles(ctx, direction, pack)
        projected = {direction_machine_id(d): direction_papers(pack, d)
                     for d in pack_directions}
        full = sum(1 for papers in projected.values() for p in papers
                   if p.get("analysis_file") or p.get("pdf_available"))
        abstracted = sum(len(papers) for papers in projected.values()) - full
        papers_lookup = pack_paper_index(pack)

        def paper_record(key: str) -> dict | None:
            record = papers_lookup.get(key)
            if isinstance(record, dict):
                return record
            return ctx.papers.get(key)

        def title_for(key: str) -> str | None:
            return stage2_trusted_paper_title(paper_record(key), key)

        def meta(region: str, owner: str, direction=None, gap_id=None, field=None,
                 repairable: bool = False) -> dict:
            return {"region": region, "owner": owner, "direction": direction,
                    "gap_id": gap_id, "field": field, "repairable": bool(repairable)}

        def excluded(direction=None) -> dict:
            return meta("excluded", "excluded", direction)

        def generator(direction, gap_id=None, field=None) -> dict:
            return meta("fixed", "generator", direction, gap_id, field)

        def source(direction, gap_id, field) -> dict:
            return meta("fixed", "source", direction, gap_id, field)

        def narrative(direction, gap_id, field) -> dict:
            return meta("narrative", "narrative", direction, gap_id, field, True)

        doc = Stage2RenderDocument()
        doc.add_line(f"# 套磁候选分析 — {professor}", excluded())
        doc.blank()
        doc.add_line("$$\\newcommand{\\dif}{\\mathop{}\\!\\mathrm{d}}$$", excluded())
        doc.blank()
        doc.add_line(
            f"> {now_utc()} ｜ 数据来源：全文级 {full} 篇 · 摘要级 {abstracted} 篇"
            f"（共 {full + abstracted} 篇）｜ 由 contact_state 确定性渲染（重跑=全量重写）",
            excluded())
        doc.blank()
        global_lines = []
        for d in pack_directions:
            for red in d.get("red_lines", []):
                if red.get("scope") == "global":
                    text = red.get("text", "").strip()
                    if text and text not in global_lines:
                        global_lines.append(redact_item_keys(text, ctx.papers))
        doc.add_line("## 全局须知", excluded())
        doc.blank()
        for text in global_lines:
            doc.add_line(f"- 【全局】{text}", excluded())
        if not global_lines:
            doc.add_line("-（无跨方向红线）", excluded())
        doc.blank()
        for index, d in enumerate(pack_directions, start=1):
            did = direction_machine_id(d)
            credibility = d.get("credibility") or {}
            verdict = credibility.get("verdict") or "未判定"
            mainline = credibility.get("mainline") or "未判定"
            authorship_line = credibility.get("authorship_line") or "insufficient"
            years = [p.get("year") for p in projected[did] if p.get("year")]
            span = f"{min(years)}–{max(years)}" if years else "年份不明"
            doc.add_line(f"## 方向 {index}：{d['name_ja']}（{d.get('name_zh') or ''}）",
                         excluded())
            doc.blank()
            rd = d.get("resolved_direction")
            if rd and rd.get("resolution_type") and rd["resolution_type"] != "unchanged":
                res_type_label = {
                    "renamed": "重命名",
                    "split_from": "拆分",
                    "merged_into": "合并",
                    "refined": "修正",
                }.get(rd["resolution_type"], rd["resolution_type"])
                doc.add_line(f"> 方向解析：{res_type_label}（provisional → resolved）", excluded())
                if rd.get("papers_to_remove"):
                    removed_titles = [ctx.papers.get(k, {}).get("title", k)
                                      for k in rd["papers_to_remove"]]
                    doc.add_line(f"> - 移除论文：{'、'.join(removed_titles)}", excluded())
                if rd.get("papers_to_add"):
                    added_titles = [ctx.papers.get(k, {}).get("title", k)
                                    for k in rd["papers_to_add"]]
                    doc.add_line(f"> + 新增论文：{'、'.join(added_titles)}", excluded())
                doc.blank()
            doc.add_line("### 方向定位", excluded())
            doc.blank()
            doc.add_line(
                f"<可信度一句：{verdict} ｜ {mainline} ｜ 相关 {len(projected[did])} 篇（{span}）。>",
                excluded())
            doc.blank()
            doc.add_line(f"<署名线：{authorship_line}。>", excluded())
            doc.blank()
            seen = {}
            narrative_data = d.get("narrative") or {}
            paper_lookup = {p["item_key"]: p for p in projected[did]}
            reference_lookup = pack_paper_index(pack)
            gap_no = {g["gap_id"]: g["no"] for g in d.get("gap_shortlist", [])}
            for block in narrative_data.get("positioning", []):
                doc.add(*render_positioning_block_parts(
                    block, paper_lookup, gap_no, ctx.professor_dir, seen,
                    {**ctx.papers, **reference_lookup},
                    meta_for=lambda field, direction_id=did: (
                        narrative(direction_id, None, f"positioning.{field}")
                        if field != "template" else excluded(direction_id))))
            doc.blank()
            doc.add_line("### 论文一览", excluded())
            doc.blank()
            doc.add_line("| 论文 | 年份 | 署名 | 分析 | 来源 |", excluded())
            doc.add_line("|---|---|---|---|---|", excluded())
            for p in projected[did]:
                analysis_cell = "—"
                if p.get("analysis_file"):
                    analysis_cell = f"[分析]({rel_path(Path(p['analysis_file']), ctx.professor_dir)})"
                if p.get("resolved_addition"):
                    source_cell = "全文验证新增"
                elif p.get("named_by_user"):
                    source_cell = "用户指定"
                else:
                    source_cell = "provisional"
                doc.add_line(
                    f"| [{p['title']}](zotero://select/library/items/{p['item_key']}) "
                    f"| {p.get('year') or '—'} | {p.get('authorship') or 'pending'} "
                    f"| {analysis_cell} | {source_cell} |", excluded(did))
            doc.blank()
            doc.add_line("### 用户笔记（原文）", excluded())
            doc.blank()
            if d.get("user_note"):
                for note_line in d["user_note"].splitlines():
                    doc.add_line(f"> {note_line}" if note_line else ">", excluded(did))
            else:
                doc.add_line("> 仅打标记，未写用户笔记。", excluded(did))
            doc.blank()
            doc.add_line("### 可延伸方向", excluded())
            doc.blank()
            gap_notes = narrative_data.get("gap_notes") or {}
            for gap in d.get("gap_shortlist", []):
                gap_id = gap["gap_id"]
                note_entry = gap_notes.get(gap_id, {})
                summary_text = note_entry.get("summary")
                if summary_text:
                    summary = summary_text
                    summary_meta = narrative(did, gap_id, "summary")
                else:
                    summary = truncate(gap.get("translation_zh") or gap.get("quote"), 60)
                    summary_meta = source(did, gap_id, "summary")
                explanation = note_entry.get("explanation")
                number = gap["no"]
                doc.add((f"1. 【作者 future work】", excluded(did)),
                        (summary, summary_meta),
                        ("（源自 ", excluded(did)),
                        (f"[{gap.get('paper_title')}]"
                         f"(zotero://select/library/items/{gap.get('item_key')})",
                         excluded(did)),
                        (f"，{gap.get('paper_year') or '年份不明'}）", excluded(did)))
                card_id = gap_id
                card_title = generator(did, card_id, "card_title")
                doc.add_line(
                    f"   <details><summary>freshness 卡 — future work #{number}</summary>",
                    card_title)
                doc.blank()
                doc.add(("- 作者原话：「", generator(did, card_id, "label")),
                        (str(gap.get("quote")), source(did, card_id, "quote")),
                        ("」", generator(did, card_id, "label")))
                doc.add(("- 中译：", generator(did, card_id, "label")),
                        (str(gap.get("translation_zh")),
                         source(did, card_id, "translation_zh")))
                doc.add(("- 页码：p.", generator(did, card_id, "label")),
                        (str(gap.get("page")), source(did, card_id, "page")),
                        ("（", generator(did, card_id, "label")),
                        (str(gap.get("source")), source(did, card_id, "source")),
                        ("）", generator(did, card_id, "label")))
                doc.add(("- 当前状态：", generator(did, card_id, "label")),
                        (str(gap.get("status")), source(did, card_id, "status")),
                        ("（置信度 ", generator(did, card_id, "label")),
                        (str(gap.get("confidence")), source(did, card_id, "confidence")),
                        ("）", generator(did, card_id, "label")))
                declared = list(gap.get("candidate_paper_ids") or [])
                evidence = stage2_replace_declared_citations(
                    gap.get("evidence") or "—", declared, title_for,
                    direction=did, gap_id=card_id, field="evidence")
                doc.add(("- 后续论文依据：", generator(did, card_id, "label")),
                        (evidence, source(did, card_id, "evidence")))
                doc.add(("- 评估时间：", generator(did, card_id, "label")),
                        (str(gap.get("evaluated_at") or "—"),
                         source(did, card_id, "evaluated_at")))
                if gap.get("status") == "partial":
                    completed_part = stage2_replace_declared_citations(
                        gap.get("completed_part") or "—", declared, title_for,
                        direction=did, gap_id=card_id, field="completed_part")
                    remaining_gap = stage2_replace_declared_citations(
                        gap.get("remaining_gap") or "—", declared, title_for,
                        direction=did, gap_id=card_id, field="remaining_gap")
                    doc.add(("- 已做部分：", generator(did, card_id, "label")),
                            (completed_part, source(did, card_id, "completed_part")))
                    doc.add(("- 剩余缺口：", generator(did, card_id, "label")),
                            (remaining_gap, source(did, card_id, "remaining_gap")))
                if gap.get("status") == "unknown":
                    doc.add_line(
                        "- ⚠ 未查证是否已被后续工作实现（unknown 原因见后续论文依据）",
                        generator(did, card_id, "warning"))
                if explanation:
                    doc.add(("- 大白话：", generator(did, card_id, "label")),
                            (explanation, narrative(did, card_id, "explanation")))
                doc.blank()
                doc.add_line("   </details>", generator(did, card_id, "card_end"))
            if not d.get("gap_shortlist"):
                doc.add_line("（本方向相关论文未明示可锚定的 future work，无可延伸点。）",
                             excluded(did))
            if d.get("gaps_excluded"):
                doc.blank()
                names = "；".join(
                    f"[{g['paper_title']}](zotero://select/library/items/{g['item_key']}) "
                    f"的 1 条（{g['reason']}）"
                    for g in d["gaps_excluded"])
                doc.add_line(
                    f"> 另有 {len(d['gaps_excluded'])} 条本轮未选，不代表不重要：{names}。",
                    excluded(did))
            if d.get("completed_gap_blacklist"):
                doc.blank()
                doc.add_line("**已被本人实现（禁锚）**", excluded(did))
                doc.blank()
                for item in d["completed_gap_blacklist"]:
                    completed = item.get("completed_by_item_key")
                    blacklist_id = item.get("gap_id")
                    declared = list(item.get("candidate_paper_ids") or [])
                    if isinstance(completed, str) and completed:
                        declared.append(completed)
                    evidence = stage2_replace_declared_citations(
                        item.get("evidence") or "—", declared, title_for,
                        direction=did, gap_id=blacklist_id, field="blacklist_evidence")
                    parts = [
                        ("- ", generator(did, blacklist_id, "item")),
                        (str(item.get("quote_trunc")),
                         source(did, blacklist_id, "quote")),
                        ("——《", generator(did, blacklist_id, "item")),
                        (str(item.get("paper_title")),
                         source(did, blacklist_id, "paper_title")),
                        ("》（", generator(did, blacklist_id, "item")),
                        (str(item.get("paper_year")),
                         source(did, blacklist_id, "paper_year")),
                        ("）→ 已被 ", generator(did, blacklist_id, "item")),
                    ]
                    if isinstance(completed, str) and completed:
                        completed_title = stage2_trusted_citation_title(
                            title_for, completed, direction=did,
                            gap_id=blacklist_id, field="completed_paper")
                        parts.extend([
                            ("[", generator(did, blacklist_id, "completed_link")),
                            (completed_title,
                             source(did, blacklist_id, "completed_paper")),
                            (f"]({STAGE2_ZOTERO_PREFIX}{completed})",
                             generator(did, blacklist_id, "completed_link")),
                        ])
                    else:
                        parts.append(("（完成论文见证据）",
                                      generator(did, blacklist_id, "completed_paper")))
                    parts.extend([
                        (" 接住（依据：", generator(did, blacklist_id, "item")),
                        (evidence, source(did, blacklist_id, "blacklist_evidence")),
                        ("）。", generator(did, blacklist_id, "item")),
                    ])
                    doc.add(*parts)
            doc.blank()
        return doc.build()

    def render_analysis_md(ctx: Stage2Context, pack: dict,
                           state_fingerprint: str) -> str:
        body, _ownership = render_analysis_document(ctx, pack, state_fingerprint)
        return body

    def stage2_trusted_paper_title(paper: dict | None, item_key: str) -> str | None:
        """Return a usable title only when a structured source contains one."""
        if not isinstance(paper, dict):
            return None
        title = paper.get("title")
        if not isinstance(title, str):
            return None
        title = title.strip()
        if not title or title in ("后续论文", item_key):
            return None
        return title
    def stage2_require_later_paper_titles(ctx, direction: dict,
                                         pack: dict | None = None) -> None:
        """Resolve each L reference from structured sources or fail before writing."""
        sources_pack = pack if isinstance(pack, dict) else ctx.pack
        canonical_papers = pack_paper_index(sources_pack or {})
        saved = direction.get("narrative_later_papers")
        for key in Stage2PackRefineContext.narrative_later_keys_for(direction):
            existing = ctx.papers.get(key)
            candidates = [existing,
                          saved.get(key) if isinstance(saved, dict) else None,
                          canonical_papers.get(key)]
            title = next((value for candidate in candidates
                          if (value := stage2_trusted_paper_title(candidate, key)) is not None),
                         None)
            if title is None:
                fail("missing_later_paper_title",
                     f"cannot render or refine later-paper reference {key}: "
                     "no trusted title is available "
                     "in the input pack or supported paper facts", item_key=key)
            paper = dict(existing) if isinstance(existing, dict) else {"item_key": key}
            paper["title"] = title
            ctx.papers[key] = paper

    return types.SimpleNamespace(
        stage2_trusted_paper_title=stage2_trusted_paper_title,
        stage2_require_later_paper_titles=stage2_require_later_paper_titles,
                validate_freshness_results=validate_freshness_results,
                narrative_scope=narrative_scope,
                validate_narrative_entry=validate_narrative_entry,
                validate_narrative=validate_narrative,
                citation_render=citation_render,
                rendered_markdown_block_lines=rendered_markdown_block_lines,
                render_positioning_block=render_positioning_block,
                render_positioning_block_parts=render_positioning_block_parts,
                redact_item_keys=redact_item_keys,
                stage2_replace_declared_citations=stage2_replace_declared_citations,
                build_direction_pack=build_direction_pack,
                render_analysis_document=render_analysis_document,
                render_analysis_md=render_analysis_md,
    )
