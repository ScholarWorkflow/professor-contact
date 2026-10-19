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

    def render_positioning_block(block: dict, paper_lookup: dict, gap_no: dict,
                                 professor_dir: Path, seen: dict,
                                 fallback_papers: dict | None = None) -> str:
        """Render one structured positioning block exactly as the analysis view does."""
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
        examples = "；具体对象：{}；输入：{}；输出：{}。".format(
            block.get("concrete_object", ""), block.get("input_example", ""),
            block.get("output_example", ""))
        prefix = "- " if block.get("kind") == "bullet" else ""
        return f"{prefix}{text}{examples}"

    def redact_item_keys(text: str, papers: dict) -> str:
        """Keep deterministic human-facing red lines free of internal item keys."""
        rendered = text
        for key in sorted((key for key in papers if key), key=len, reverse=True):
            if key in rendered:
                rendered = rendered.replace(key, papers[key].get("title") or "该论文")
        return re.sub(r"(?<![A-Za-z0-9])[A-Z0-9]{8}(?![A-Za-z0-9])", "相关论文", rendered)

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

    def render_analysis_md(ctx: Stage2Context, pack: dict,
                           state_fingerprint: str) -> str:
        professor = ctx.professor
        pack_directions = pack.get("directions") or []
        for direction in pack_directions:
            stage2_require_later_paper_titles(ctx, direction, pack)
        projected = {direction_machine_id(d): direction_papers(pack, d)
                     for d in pack_directions}
        full = sum(1 for papers in projected.values() for p in papers
                   if p.get("analysis_file") or p.get("pdf_available"))
        abstracted = sum(len(papers) for papers in projected.values()) - full
        lines = [
            f"# 套磁候选分析 — {professor}",
            "",
            "$$\\newcommand{\\dif}{\\mathop{}\\!\\mathrm{d}}$$",
            "",
            f"> {now_utc()} ｜ 数据来源：全文级 {full} 篇 · 摘要级 {abstracted} 篇（共 {full + abstracted} 篇）｜ 由 contact_state 确定性渲染（重跑=全量重写）",
            "",
        ]
        global_lines = []
        for d in pack_directions:
            for red in d.get("red_lines", []):
                if red.get("scope") == "global":
                    text = red.get("text", "").strip()
                    if text and text not in global_lines:
                        global_lines.append(redact_item_keys(text, ctx.papers))
        lines.append("## 全局须知")
        lines.append("")
        for text in global_lines:
            lines.append(f"- 【全局】{text}")
        if not global_lines:
            lines.append("-（无跨方向红线）")
        lines.append("")
        for index, d in enumerate(pack_directions, start=1):
            credibility = d.get("credibility") or {}
            verdict = credibility.get("verdict") or "未判定"
            mainline = credibility.get("mainline") or "未判定"
            authorship_line = credibility.get("authorship_line") or "insufficient"
            years = [p.get("year") for p in projected[direction_machine_id(d)] if p.get("year")]
            span = f"{min(years)}–{max(years)}" if years else "年份不明"
            lines.append(f"## 方向 {index}：{d['name_ja']}（{d.get('name_zh') or ''}）")
            lines.append("")
            # Show resolution info if available
            rd = d.get("resolved_direction")
            if rd and rd.get("resolution_type") and rd["resolution_type"] != "unchanged":
                res_type_label = {
                    "renamed": "重命名",
                    "split_from": "拆分",
                    "merged_into": "合并",
                    "refined": "修正",
                }.get(rd["resolution_type"], rd["resolution_type"])
                lines.append(f"> 方向解析：{res_type_label}（provisional → resolved）")
                if rd.get("papers_to_remove"):
                    removed_titles = [ctx.papers.get(k, {}).get("title", k) for k in rd["papers_to_remove"]]
                    lines.append(f"> - 移除论文：{'、'.join(removed_titles)}")
                if rd.get("papers_to_add"):
                    added_titles = [ctx.papers.get(k, {}).get("title", k) for k in rd["papers_to_add"]]
                    lines.append(f"> + 新增论文：{'、'.join(added_titles)}")
                lines.append("")
            lines.append("### 方向定位")
            lines.append("")
            lines.append(f"<可信度一句：{verdict} ｜ {mainline} ｜ 相关 {len(projected[direction_machine_id(d)])} 篇（{span}）。>")
            lines.append("")
            lines.append(f"<署名线：{authorship_line}。>")
            lines.append("")
            seen = {}
            narrative = d.get("narrative") or {}
            paper_lookup = {p["item_key"]: p for p in projected[direction_machine_id(d)]}
            # Reference-scope records (relevant_keys) live in the same canonical
            # map; they may be cited through {{P:key}} without being members.
            reference_lookup = pack_paper_index(pack)
            gap_no = {g["gap_id"]: g["no"] for g in d.get("gap_shortlist", [])}
            for block in narrative.get("positioning", []):
                lines.append(render_positioning_block(
                    block, paper_lookup, gap_no, ctx.professor_dir, seen,
                    {**ctx.papers, **reference_lookup}))
            lines.append("")
            lines.append("### 论文一览")
            lines.append("")
            lines.append("| 论文 | 年份 | 署名 | 分析 | 来源 |")
            lines.append("|---|---|---|---|---|")
            for p in projected[direction_machine_id(d)]:
                analysis_cell = "—"
                if p.get("analysis_file"):
                    analysis_cell = f"[分析]({rel_path(Path(p['analysis_file']), ctx.professor_dir)})"
                if p.get("resolved_addition"):
                    source_cell = "全文验证新增"
                elif p.get("named_by_user"):
                    source_cell = "用户指定"
                else:
                    source_cell = "provisional"
                lines.append(f"| [{p['title']}](zotero://select/library/items/{p['item_key']}) | {p.get('year') or '—'} | {p.get('authorship') or 'pending'} | {analysis_cell} | {source_cell} |")
            lines.append("")
            lines.append("### 用户笔记（原文）")
            lines.append("")
            if d.get("user_note"):
                for note_line in d["user_note"].splitlines():
                    lines.append(f"> {note_line}" if note_line else ">")
            else:
                lines.append("> 仅打标记，未写用户笔记。")
            lines.append("")
            lines.append("### 可延伸方向")
            lines.append("")
            gap_notes = narrative.get("gap_notes") or {}
            for gap in d.get("gap_shortlist", []):
                note_entry = gap_notes.get(gap["gap_id"], {})
                summary = note_entry.get("summary") or truncate(gap["translation_zh"] or gap["quote"], 60)
                explanation = note_entry.get("explanation")
                number = gap["no"]
                lines.append(f"1. 【作者 future work】{summary}（源自 [{gap['paper_title']}](zotero://select/library/items/{gap['item_key']})，{gap.get('paper_year') or '年份不明'}）")
                details = [
                    f"- 作者原话：「{gap['quote']}」",
                    f"- 中译：{gap['translation_zh']}",
                    f"- 页码：p.{gap.get('page')}（{gap.get('source')}）",
                    f"- 当前状态：{gap.get('status')}（置信度 {gap.get('confidence')}）",
                    f"- 后续论文依据：{gap.get('evidence') or '—'}",
                    f"- 评估时间：{gap.get('evaluated_at') or '—'}",
                ]
                if gap.get("status") == "partial":
                    details.append(f"- 已做部分：{gap.get('completed_part') or '—'}")
                    details.append(f"- 剩余缺口：{gap.get('remaining_gap') or '—'}")
                if gap.get("status") == "unknown":
                    details.append("- ⚠ 未查证是否已被后续工作实现（unknown 原因见后续论文依据）")
                if explanation:
                    details.append(f"- 大白话：{explanation}")
                lines.append(f"   <details><summary>freshness 卡 — future work #{number}</summary>")
                lines.append("")
                lines.extend(details)
                lines.append("")
                lines.append("   </details>")
            if not d.get("gap_shortlist"):
                lines.append("（本方向相关论文未明示可锚定的 future work，无可延伸点。）")
            if d.get("gaps_excluded"):
                lines.append("")
                names = "；".join(
                    f"[{g['paper_title']}](zotero://select/library/items/{g['item_key']}) 的 1 条（{g['reason']}）"
                    for g in d["gaps_excluded"])
                lines.append(f"> 另有 {len(d['gaps_excluded'])} 条本轮未选，不代表不重要：{names}。")
            if d.get("completed_gap_blacklist"):
                lines.append("")
                lines.append("**已被本人实现（禁锚）**")
                lines.append("")
                for item in d["completed_gap_blacklist"]:
                    completed = item.get("completed_by_item_key")
                    completed_render = (f"[{ctx.papers[completed].get('title')}](zotero://select/library/items/{completed})"
                                        if completed and completed in ctx.papers else "（完成论文见证据）")
                    lines.append(f"- {item['quote_trunc']}——《{item['paper_title']}》（{item.get('paper_year')}）→ 已被 {completed_render} 接住（依据：{item.get('evidence')}）。")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

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
                redact_item_keys=redact_item_keys,
                build_direction_pack=build_direction_pack,
                render_analysis_md=render_analysis_md,
    )
