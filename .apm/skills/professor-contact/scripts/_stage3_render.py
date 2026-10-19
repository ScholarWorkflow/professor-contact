#!/usr/bin/env python3
"""Pure Stage-3 Markdown rendering for ``contact_state.py``.

The runner loads this helper by path next to itself and keeps the pre-split
module-level API: the two public renderers below are wrapped by same-named,
same-signature entry points, and the private helpers are re-exported.

The renderer owns the exact bytes, so the runner injects the two names the
group would otherwise import back from it: the clock (``now_utc``) so the
timestamp keeps one source, and the candidate file-name label
(``candidates_md``) so the overview link text keeps one owner. This module
never imports the runner.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _red_line_key(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).casefold()


def _candidate_red_lines(candidate: dict, shared_red_lines: set) -> list:
    """Deterministic red-line presentation (style rule C10 lives in the runner).

    Range labels and duplication are rendering decisions, so the renderer owns
    them: a candidate line already stated by the section header is dropped, and
    what remains is labelled with the candidate number.  The candidate's own
    ``red_lines`` machine facts stay untouched either way.
    """
    out, seen = [], set(shared_red_lines or ())
    for text in candidate.get("red_lines") or []:
        value = str(text).strip()
        key = _red_line_key(value)
        if not value or key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _render_idea_block(lines: list, number: int, heading_label: str,
                       candidate: dict, paper_index: dict,
                       group_id: str | None = None,
                       shared_red_lines: set | None = None) -> None:
    """Render one idea (per-direction candidate or explicit cross-direction
    idea) with its machine meta comment and full body (issue #8 §7.2: meta
    carries direction_ids provenance and exact gap_refs triples)."""
    meta = {"id": candidate["id"], "kind": candidate.get("kind") or "direction",
            "direction_ids": list(candidate.get("direction_ids") or []),
            "gap_refs": [{"direction_id": g["direction_id"], "item_key": g["item_key"],
                          "gap_id": g["gap_id"]} for g in candidate.get("gap_refs", [])]}
    if candidate.get("kind") == "cross_direction":
        meta["cross_direction"] = True
        if group_id:
            meta["group_id"] = group_id
    lines.append(f"### {heading_label} {number}：{candidate.get('title') or candidate['id']}（{candidate['id']}）")
    lines.append("")
    lines.append(f"<!-- candidate_meta: {json.dumps(meta, ensure_ascii=False)} -->")
    lines.append("")
    if candidate.get("kind") == "cross_direction":
        participants = candidate.get("_participants") or []
        label = "＋".join(f"{p.get('name_ja') or p.get('direction_id')}（{p.get('direction_id')}）"
                          for p in participants)
        lines.append(f"**参与方向**：{label}")
        lines.append("")
    lines.append(f"**一句话**：{candidate.get('one_liner') or '—'}")
    lines.append("")
    lines.append(f"**研究问题**：{candidate['research_question']}")
    lines.append("")
    lines.append("**展开**：")
    for point in candidate.get("points", []):
        lines.append(f"- {point}")
    lines.append("")
    lines.append("**支撑论文**")
    lines.append("")
    lines.append("| 论文 | 年份 | 署名 | 作用 | 分析 |")
    lines.append("|---|---|---|---|---|")
    for paper in candidate.get("papers", []):
        key = paper["item_key"]
        meta_paper = paper_index.get(key) or {}
        analysis_rel = meta_paper.get("_analysis_rel")
        analysis_cell = f"[分析]({analysis_rel})" if analysis_rel else "—"
        lines.append(f"| [{paper['title']}](zotero://select/library/items/{key}) | {paper.get('year') or '—'} | {paper.get('authorship') or 'pending'} | {paper.get('role') or '—'} | {analysis_cell} |")
    lines.append("")
    fit_note = candidate.get("fit_note") or ""
    middle_flags = [p for p in candidate.get("papers", []) if p.get("authorship") == "middle"]
    if middle_flags:
        fit_note = (fit_note + " " if fit_note else "") + "⚠️ 此论文教授为中间作者"
    lines.append(f"**贴合度**：{candidate.get('fit')} — {fit_note or '—'}")
    lines.append("")
    red_lines = _candidate_red_lines(candidate, shared_red_lines)
    if red_lines:
        lines.append(f"**红线**：{'；'.join(f'【候选 {number}】{text}' for text in red_lines)}")
        lines.append("")
    lines.append(f"**为何值得推**：{candidate.get('why_recommended') or '—'}")
    if candidate.get("tension_points"):
        lines.append("")
        lines.append(f"**张力点**：{'；'.join(candidate['tension_points'])}")
    for gap in candidate.get("gap_refs", []):
        if gap.get("done_by_self"):
            lines.append("")
            lines.append(f"> 注：该候选踩着已完成 future work（{gap['gap_id'][:12]}…）作【我的延伸】，差异点见 anchor_notes。")
    lines.append("")


def _stage3_scope_marker(payload: dict) -> str:
    return f"<!-- stage3_scope: {json.dumps(payload, ensure_ascii=False, sort_keys=True)} -->"


def render_candidates_md(professor: str, category: str, direction_entries: list,
                         profile_fp: str | None, state_fingerprint: str,
                         professor_dir: Path, cross_groups: list | None = None, *,
                         now_utc) -> str:
    lines = [
        f"# 套磁想法候选 — {professor}（{category}）",
        "",
        "$$\\newcommand{\\dif}{\\mathop{}\\!\\mathrm{d}}$$",
        "",
        f"> {now_utc()} ｜ profile：{'有' if profile_fp else '无'}{'（未按个人资料校准）' if not profile_fp else ''} ｜ 由 contact_state 确定性渲染；方向脉络与 future work 原文见同目录《套磁候选分析.md》，本文件不复述",
        "",
    ]
    for entry in direction_entries:
        credibility = entry.get("credibility") or {}
        verdict = credibility.get("verdict") or "未判定"
        direction_id = entry.get("direction_id") or entry.get("collection_key")
        lines.append(f"## {entry['name_ja']}（{entry.get('name_zh') or ''}）")
        lines.append("")
        lines.append(_stage3_scope_marker({"kind": "direction", "direction_id": direction_id}))
        lines.append("")
        lines.append(f"> 方向 ID：{direction_id} ｜ 脉络、论文一览、用户笔记 → 见《套磁候选分析.md》。")
        red_lines = [r for r in entry.get("red_lines", []) if r.get("scope") != "global"]
        shared_red_lines = {_red_line_key(r.get("text")) for r in red_lines}
        if red_lines:
            rendered = "；".join(f"【方向】{r.get('text', '').strip()}" for r in red_lines)
            lines.append(f"> 方向级共享红线（只在这里写一次）：{rendered}")
        if verdict in ("勉强", "疑似幻觉"):
            lines.append("> ⚠️ 该方向的归类目前不够可靠。建议先重新整理这位教授的研究方向，再决定是否继续使用这个方向；下方候选仍只依据论文实际内容生成。")
        lines.append("")
        refined = entry.get("refined")
        if refined:
            lines.append("### 你的草稿修正版（基本方向，非终稿；校准后的用户想法已作为可选候选列出）")
            lines.append("")
            lines.append(f"- **保真**：{refined.get('core_intent') or '—'}")
            calibration = refined.get("calibration") or []
            lines.append(f"- **校准**：{'；'.join(calibration) if calibration else '无'}")
            lines.append(f"- **基本方向**：{refined.get('idea_zh')}")
            variants = refined.get("variants") or []
            if variants:
                lines.append(f"- **替代表述变体**：{'；'.join(variants)}")
            lines.append("")
        candidates = entry.get("candidates") or []
        paper_index = {}
        for d in (entry.get("_pack_papers") or []):
            paper_index[d["item_key"]] = d
        for number, candidate in enumerate(candidates, start=1):
            _render_idea_block(lines, number, "候选", candidate, paper_index,
                               shared_red_lines=shared_red_lines)
        if entry.get("priority"):
            lines.append("## 推荐优先级")
            lines.append("")
            lines.append(_stage3_scope_marker({"kind": "direction",
                                               "direction_id": direction_id}))
            lines.append("")
            lines.append(entry["priority"])
            lines.append("")
    for group in cross_groups or []:
        entries = group.get("candidates") or []
        if not entries:
            continue
        lines.append("## 跨方向想法（显式标注）")
        lines.append("")
        lines.append(_stage3_scope_marker({"kind": "group", "group_id": group.get("group_id")}))
        lines.append("")
        lines.append("> 以下候选显式跨越多个已解析方向（绝不隐式合并方向池）；每条列出全部参与方向的 resolved 方向 ID。")
        lines.append("")
        paper_index = {}
        for d in (group.get("_pack_papers") or []):
            paper_index[d["item_key"]] = d
        for number, candidate in enumerate(entries, start=1):
            _render_idea_block(lines, number, "跨方向候选", candidate, paper_index,
                               group_id=group.get("group_id"))
    return "\n".join(lines).rstrip() + "\n"


def render_candidates_overview(entries: list, program_root: Path,
                               cross_groups: list | None = None, *,
                               now_utc, candidates_md: str) -> str:
    lines = [
        "# 套磁想法候选总览",
        "",
        f"> {now_utc()} ｜ 由 contact_state 渲染；选好后跑阶段 4 professor-contact-selection。",
        "",
        "| 教授 | 方向 | 候选数 | 推荐顺序 | 文件 |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        count = len(entry.get("candidates") or [])
        priority = (entry.get("priority") or "").replace("\n", " ")[:40] or "—"
        md = entry.get("_candidates_md_rel") or "—"
        lines.append(f"| {entry['professor']} | {entry['name_ja']} | {count} | {priority} | [{candidates_md}]({md}) |")
    for group in cross_groups or []:
        label = "＋".join(group.get("direction_ids") or [])
        count = len(group.get("candidates") or [])
        lines.append(f"| {group.get('professor')} | 跨方向：{label} | {count} | 显式跨方向组（group_id {group.get('group_id')}） | [{candidates_md}]({group.get('_candidates_md_rel') or '—'}) |")
    lines.append("")
    return "\n".join(lines) + "\n"
