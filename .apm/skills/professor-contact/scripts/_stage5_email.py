#!/usr/bin/env python3
"""Stage-5 email helper module for ``contact_state.py``.

The runner loads this helper by path next to itself and calls :func:`build`
once with its own helper functions and shared constants. The factory binds
those names in an enclosing scope, so the functions below keep the exact
bodies they had inside the runner (only their indentation changed). The
module never imports the runner, never adds itself to ``sys.path`` and
never builds a second failure channel.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import unicodedata
import types





def build(*, read_json_file,
          BATCH_RE,
          INTEREST_HARD_CAP,
          INTEREST_SOFT_CAP,
          fail,
          stage5_mode,
          stage5_output_id,
          DEFAULT_ALMA_MATER,
          EMAIL_PACK,
          now_utc,
          rel_path):
    def find_boshu_analysis(program_root: Path) -> Path | None:
        candidates = ([program_root / "boshu_analysis.json"] if
                      (program_root / "boshu_analysis.json").is_file() else []) + \
            sorted(program_root.glob("*/boshu_analysis.json")) + \
            sorted(program_root.glob("*/*/boshu_analysis.json"))
        return candidates[0] if candidates else None

    def load_header_sources(program_root: Path) -> dict:
        info = {}
        info_path = program_root / "info.json"
        if info_path.is_file():
            data, error = read_json_file(info_path)
            if error is None and isinstance(data, dict):
                info = data
        boshu = {}
        boshu_path = find_boshu_analysis(program_root)
        if boshu_path and boshu_path.is_file():
            data, error = read_json_file(boshu_path)
            if error is None and isinstance(data, dict):
                boshu = data
        return {"info": info, "boshu": boshu,
                "info_path": str(info_path) if info_path.is_file() else None,
                "boshu_path": str(boshu_path) if boshu_path else None}

    def header_values(sources: dict, email: dict) -> dict:
        info = sources.get("info") or {}
        boshu = sources.get("boshu") or {}
        target = info.get("target") or {}
        term = str(target.get("intake_term") or "").lower()
        month = {"april": "4月", "october": "10月"}.get(term, target.get("intake_term") or "")
        exam_type = boshu.get("exam_type") or {}
        degree = exam_type.get("degree") or "大学院修士課程"
        selection_name = exam_type.get("selection_name") or ""
        batch_match = BATCH_RE.search(selection_name or "")
        batch = batch_match.group(1) if batch_match else ""
        major = ""
        for token in re.findall(r"([\u4e00-\u9fffぁ-んァ-ヶー]+専攻|[\u4e00-\u9fffぁ-んァ-ヶー]+コース)", selection_name):
            major = token
            break
        return {
            "大学": info.get("university") or "", "研究科": info.get("department") or "",
            "専攻": major or info.get("department") or "", "学位": degree,
            "入試批次": batch, "入学年度": str(target.get("intake_year") or ""),
            "入学月": month, "先生名": email.get("professor") or "",
            "出身校": None, "氏名": None,
        }

    def subject_line(values: dict) -> str:
        return (f"【入学希望】{values['入学年度']}年{values['入学月']}期 "
                f"{values['学位']}{values['入試批次']}入学に関するご相談")

    def compact_name(value: Any) -> str:
        return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or "")))

    def email_item_is_evidence_seeded(items: dict) -> bool:
        """True when the cached recipient email was seeded from the artifact."""
        sources = (items.get("email") or {}).get("sources") or []
        return bool(sources) and all(
            isinstance(source, dict) and source.get("level") == "contact_evidence"
            for source in sources)

    def current_source_fingerprints(sources: dict) -> dict:
        """Return the current canonical fingerprints, or the first unavailable field."""
        fingerprints = {}
        for field, source_key in (("info_json", "info_path"),
                                  ("boshu_analysis", "boshu_path")):
            source_path = sources.get(source_key)
            if not isinstance(source_path, str) or not source_path:
                return {"source_fingerprints": fingerprints,
                        "failed_field": f"source_fingerprints.{field}"}
            try:
                mtime = int(Path(source_path).stat().st_mtime)
            except (OSError, ValueError, TypeError, OverflowError):
                return {"source_fingerprints": fingerprints,
                        "failed_field": f"source_fingerprints.{field}"}
            fingerprints[field] = f"{source_path}:{mtime}"
        return {"source_fingerprints": fingerprints, "failed_field": None}

    def cited_title_chars(sentences: list, titles: list) -> int:
        """Characters that are verbatim quotes of a pack paper title.

        A character is exempt only when the sentence carries the title exactly
        as the pack states it. Each position is counted once even when one pack
        title contains another, and a title split across two sentences never
        matches, because every sentence is scanned on its own.
        """
        covered = set()
        for index, sentence in enumerate(sentences):
            for title in titles:
                if not title:
                    continue
                start = sentence.find(title)
                while start >= 0:
                    covered.update((index, offset)
                                   for offset in range(start, start + len(title)))
                    start = sentence.find(title, start + 1)
        return len(covered)

    def validate_email_raw(email: dict, raw: Any) -> list:
        problems = []
        if not isinstance(raw, dict) or raw.get("schema") != 1 or raw.get("kind") != "email":
            return ["schema/kind must be 1/email"]
        if raw.get("email_id") != email.get("email_id"):
            problems.append("email_id mismatch")
        sentences = raw.get("interest_sentences_ja")
        if not isinstance(sentences, list) or len(sentences) != 3 or \
                not all(isinstance(s, str) and s.strip() for s in sentences):
            problems.append("interest_sentences_ja must be 3 non-empty sentences")
            return problems
        titles = [p["title"] for p in email.get("papers") or []
                  if isinstance(p, dict) and isinstance(p.get("title"), str)]
        total = sum(len(s) for s in sentences) - cited_title_chars(sentences, titles)
        if total > INTEREST_HARD_CAP:
            problems.append(f"interest total {total} exceeds hard cap {INTEREST_HARD_CAP}")
        elif total > INTEREST_SOFT_CAP:
            problems.append(f"WARNING interest total {total} exceeds soft cap {INTEREST_SOFT_CAP}")
        if not (raw.get("future_aspiration_ja") or "").strip():
            problems.append("future_aspiration_ja required")
        learning = raw.get("learning_candidates")
        if not isinstance(learning, list) or not (2 <= len(learning) <= 3) or \
                not all(isinstance(item, str) and item.strip() for item in learning):
            problems.append("learning_candidates must have 2-3 entries")
        allowed = set(email.get("allowed_sources") or [])
        anchorable = set(email.get("anchorable_gaps") or [])
        gap_status = {g["gap_id"]: g for g in email.get("gaps", [])}
        source_map = raw.get("source_map")
        if not isinstance(source_map, list):
            problems.append("source_map must be a list")
            return problems
        covered = set()
        for entry in source_map:
            if not isinstance(entry, dict):
                problems.append("source_map entries must be objects")
                continue
            output = entry.get("output")
            if not isinstance(output, str):
                problems.append("source_map output must be a string")
                continue
            if output in covered:
                problems.append(f"source_map duplicate output {output}")
            covered.add(output)
            source_ids = entry.get("source_ids") or []
            if not isinstance(source_ids, list) or not all(isinstance(sid, str) for sid in source_ids):
                problems.append(f"source_map {output}: source_ids must be a string list")
                continue
            if not source_ids:
                problems.append(f"source_map {output}: empty source_ids")
                continue
            if output == "④":
                problems.append("source_map ④ is retired; regenerate the three-part interest result")
                continue
            if output == "③":
                if not all(sid.startswith("gap:") for sid in source_ids):
                    problems.append("source_map ③ may only use gap:<gap_id> sources")
                for sid in source_ids:
                    gap_id = sid[4:]
                    if gap_id not in anchorable:
                        if gap_id in gap_status and gap_status[gap_id].get("status") == "done_by_self":
                            problems.append(f"source_map ③ anchors done_by_self gap {gap_id[:12]}…")
                        else:
                            problems.append(f"source_map ③ references gap outside anchorable set: {gap_id[:12]}…")
                continue
            for sid in source_ids:
                if sid not in allowed:
                    problems.append(f"source_map {output}: source {sid} not in allowed_sources")
        for required in ("①", "②", "③", "future"):
            if required not in covered:
                problems.append(f"source_map missing output {required}")
        return problems

    def require_user_choices(email_id: str, choices: Any) -> dict:
        if not isinstance(choices, dict):
            fail("missing_user_choice", f"{email_id}: choices object required")
        if not isinstance(choices.get("first_choice"), bool):
            fail("missing_user_choice", f"{email_id}: first_choice must be boolean")
        if not isinstance(choices.get("signature_name"), str) or not choices["signature_name"].strip():
            fail("missing_user_choice", f"{email_id}: signature_name is required")
        if not isinstance(choices.get("learning"), str) or not choices["learning"].strip():
            fail("missing_user_choice", f"{email_id}: learning is required")
        return choices

    def require_followup_choices(email_id: str, choices: dict) -> None:
        sent_date = choices.get("initial_sent_date")
        if not isinstance(sent_date, str) or not sent_date.strip() or "{{" in sent_date:
            fail("missing_user_choice", f"{email_id}: initial_sent_date is required for follow-up email")

    def find_followup_template_path(program_root: Path, explicit: str | None) -> str | None:
        if explicit:
            return explicit
        for candidate in [program_root.parent / "套磁邮件" / "套磁跟进模板.md",
                          program_root / "套磁邮件" / "套磁跟进模板.md"]:
            if candidate.is_file():
                return str(candidate)
        return None

    def load_id_map(path: Path, expected_ids: set, label: str, exact: bool = True) -> dict:
        data, error = read_json_file(path)
        if error:
            fail("invalid_result_json", f"{label} unreadable: {path}: {error}")
        rows = data if isinstance(data, list) else [data]
        if not exact:
            # Scoped/targeted mode: unrelated rows are noise, however malformed,
            # duplicated or unknown. Only the selected ids' own occurrences are
            # validated below, and each of them must appear exactly once.
            rows = [row for row in rows
                    if isinstance(row, dict) and row.get("email_id") in expected_ids]
            if len(rows) != len(expected_ids):
                fail("invalid_result_json", f"{label} email_id set does not match selected emails")
        if not all(isinstance(row, dict) for row in rows):
            fail("invalid_result_json", f"{label} must contain objects")
        ids = [row.get("email_id") for row in rows]
        if any(not isinstance(email_id, str) or not email_id for email_id in ids):
            fail("invalid_result_json", f"{label} contains missing email_id")
        if len(set(ids)) != len(ids) or (set(ids) != expected_ids if exact else not expected_ids.issubset(set(ids))):
            fail("invalid_result_json", f"{label} email_id set does not match selected emails")
        return {row["email_id"]: row for row in rows}

    def humanized_paths(args, emails: list[dict], exact: bool = True) -> dict[str, Path]:
        mode = stage5_mode(args)
        expected = set()
        if mode in ("first", "both"):
            expected.update(stage5_output_id(email.get("email_id"), "initial") for email in emails)
        if mode in ("followup", "both"):
            expected.update(stage5_output_id(email.get("email_id"), "followup") for email in emails)
        map_path = getattr(args, "humanized_map", None)
        if map_path:
            data, error = read_json_file(Path(map_path))
            if error or not isinstance(data, dict):
                fail("invalid_humanized_map", f"humanized map unreadable or not an object: {map_path}")
            if (set(data) != expected if exact else not expected.issubset(set(data))):
                fail("invalid_humanized_map", "humanized map keys do not match selected email IDs")
            paths = {}
            for email_id, value in data.items():
                if email_id not in expected:
                    continue
                if not isinstance(value, str) or not Path(value).is_absolute():
                    fail("invalid_humanized_map", f"humanized path for {email_id} must be absolute")
                paths[email_id] = Path(value)
        elif len(expected) == 1 and getattr(args, "humanized", None):
            paths = {next(iter(expected)): Path(args.humanized)}
        elif len(emails) > 1:
            fail("humanized_map_required", "multiple emails require --humanized-map email_id->absolute path")
        else:
            fail("result_missing", "humanized body file required (--humanized)")
        if len(set(paths.values())) != len(paths):
            fail("invalid_humanized_map", "multiple emails must use distinct humanized body paths")
        for email_id, path in paths.items():
            if not path.is_file():
                fail("result_missing", f"humanized body missing for {email_id}: {path}")
        return paths

    def email_template_body(template_text: str) -> str:
        """Select the email body without copying Markdown instructions into mail.

        Plain templates are unchanged. Markdown templates may delimit the body
        with a body heading or a single text fence; trailing instruction sections
        are document metadata. Never guess between multiple body sections/blocks.
        """
        fences = []
        headings = []
        opened = None
        offset = 0
        for line in template_text.splitlines(keepends=True):
            marker = re.fullmatch(r" {0,3}(`{3,}|~{3,})([^\r\n]*)\r?\n?", line)
            if opened:
                start, content_start, delimiter = opened
                if (marker and marker[1][0] == delimiter[0]
                        and len(marker[1]) >= len(delimiter) and not marker[2].strip()):
                    fences.append((start, offset + len(line), content_start, offset))
                    opened = None
            elif marker:
                opened = (offset, offset + len(line), marker[1])
            else:
                heading = re.fullmatch(r"(#{1,6})[ \t]+([^\r\n]+)\r?\n?", line)
                if heading:
                    headings.append((offset, offset + len(line), len(heading[1]),
                                     heading[2].strip().rstrip("# ：:")))
            offset += len(line)
        if opened:
            fail("template_error", "unclosed email template code fence")

        body_names = {"正文", "邮件正文", "本文", "メール本文"}
        note_names = {"说明", "模板说明", "使用说明", "占位符说明", "注意事项"}
        sections = [row for row in headings if row[3] in body_names]
        if len(sections) > 1:
            fail("template_error", "multiple email body sections; keep one body section")
        start, end = 0, len(template_text)
        if sections:
            _, start, level, _ = sections[0]
            end = next((row[0] for row in headings if row[0] >= start and row[2] <= level), end)
        else:
            end = next((row[0] for row in headings if row[3] in note_names), end)
        blocks = [row for row in fences if start <= row[0] and row[1] <= end]
        if len(blocks) > 1:
            fail("template_error", "multiple email body code blocks; use a body heading to select one")
        if blocks:
            return template_text[blocks[0][2]:blocks[0][3]]
        body = template_text[start:end]
        return body.strip("\r\n") + "\n" if sections or end < len(template_text) else body

    def assemble_draft(email: dict, raw: dict, choices: dict,
                       sources: dict, template_text: str) -> tuple[str, list, list]:
        values = header_values(sources, email)
        values["出身校"] = choices.get("alma_mater") or DEFAULT_ALMA_MATER
        values["氏名"] = choices.get("signature_name") or ""
        values["志望"] = ("先生の研究室を第一志望として出願させていただきたく存じます"
                          if choices.get("first_choice") else
                          "先生の研究室を志望として出願させていただきたく存じます")
        values["学習中"] = choices.get("learning") or ""
        values["兴趣段"] = "\n".join(raw.get("interest_sentences_ja") or [])
        values["未来志向"] = raw.get("future_aspiration_ja") or ""
        subject = choices.get("subject") or subject_line(values)
        values["subject"] = subject
        body = email_template_body(template_text)
        for key, value in values.items():
            body = body.replace("{{" + key + "}}", value or "")
        leftover = re.findall(r"\{\{[^}]*\}\}", body)
        if leftover:
            fail("template_error", f"unresolved placeholders after fill: {leftover}")
        draft = f"Subject: {subject}\n\n{body}"
        protected = [subject, values["氏名"], values["志望"], values["学習中"], values["未来志向"]]
        protected += [p["title"] for p in email.get("papers", []) if p.get("title")]
        protected += [v for v in (values["大学"], values["研究科"], values["専攻"],
                                  values["学位"], values["入学年度"] + "年" + values["入学月"]) if v]
        banned = []
        for red in email.get("red_lines", []):
            banned.extend(red.get("banned_phrases") or [])
        return draft, [p for p in protected if p], banned

    def body_salutation_line(body: str, values: dict) -> str | None:
        """The template's fixed salutation line, matched verbatim from the
        assembled body. The 「抬头逐字」 checklist row must show exactly the text
        the recipient sees — the user template may format the header differently
        from the synthesized 大学／研究科／先生名： form (e.g. without the trailing
        full-width colon), and a mismatching row reads as a self-contradicting
        checklist. Returns None when the professor name does not appear, leaving
        the caller's fallback in place."""
        name = values.get("先生名") or ""
        if not name:
            return None
        for line in body.splitlines():
            text = line.strip()
            if text and name in text:
                return text
        return None

    def render_checklist_table(verify: dict, header_text: str | None = None) -> list:
        items = verify.get("items") or {}
        def cell(key, default="—"):
            entry = items.get(key) or {}
            verdict = entry.get("verdict") or "unverified"
            value = entry.get("value")
            return value if value not in (None, "") else default, verdict
        email_value, email_verdict = cell("email", "（空）")
        roster_value, roster_verdict = cell("roster")
        season_value, season_verdict = cell("season")
        header_value, header_verdict = cell("header")
        if header_text:
            header_value = header_text
        subject_value, subject_verdict = cell("subject_batch")
        schedule_value, schedule_verdict = cell("schedule")
        consent_value, consent_verdict = cell("consent")
        warnings = items.get("warnings") or []
        warning_text = "；".join(str(w) for w in warnings) if warnings else "（无）"
        return [
            "| 项目 | 内容 | 结论 | 来源 |", "|---|---|---|---|",
            f"| 收件邮箱 | {email_value} | {email_verdict} | {cell_source(items, 'email')} |",
            f"| 教授在册 | {roster_value} | {roster_verdict} | {cell_source(items, 'roster')} |",
            f"| 批次存在性 | {season_value} | {season_verdict} | {cell_source(items, 'season')} |",
            f"| 抬头逐字 | {header_value} | {header_verdict} | {cell_source(items, 'header')} |",
            f"| 件名批次词 | {subject_value} | {subject_verdict} | {cell_source(items, 'subject_batch')} |",
            f"| 日程快照 | {schedule_value} | {schedule_verdict} | {cell_source(items, 'schedule')} |",
            f"| 内诺制度 | {consent_value} | {consent_verdict} | {cell_source(items, 'consent')} |",
            f"| 特记 ⚠ | {warning_text} | — | info.json notes 等 |",
        ]

    def cell_source(items: dict, key: str) -> str:
        entry = items.get(key) or {}
        sources = entry.get("sources") or []
        if not sources:
            return "—"
        first = sources[0]
        return str(first.get("url") or first.get("note") or "—")

    def direction_material_label(email: dict, source_id: str) -> str:
        """Human-readable provenance for one frozen user-material source.

        The bare machine id is only the pack's join key; the md source table is
        the pre-send audit surface, so it shows the material id plus the user's
        own answer (truncated, never rewritten). An id outside the frozen slice
        keeps the raw value instead of inventing a citation.
        """
        parts = source_id.split(":", 2)
        direction_id = parts[1] if len(parts) > 1 else ""
        material_id = parts[2] if len(parts) > 2 else ""
        entry = next((row for row in email.get("direction_materials") or []
                      if isinstance(row, dict)
                      and row.get("direction_id") == direction_id
                      and row.get("material_id") == material_id), None)
        if entry is None:
            return f"[用户素材] {source_id}"
        answer = re.sub(r"\s+", " ", str(entry.get("answer") or "")).strip()
        answer = answer.replace("|", "｜")
        if len(answer) > 36:
            answer = answer[:36] + "…"
        return f"[用户素材] 方向素材 {material_id}：「{answer}」"

    def analysis_link(record: dict, document_dir: Path) -> str:
        path = record.get("analysis_file")
        if not isinstance(path, str) or not path.strip() or not Path(path).is_absolute():
            return ""
        return f"｜[分析](<{rel_path(Path(path), document_dir)}>)"

    def paper_links(record: dict, item_key: str, document_dir: Path) -> str:
        return (f"（[zotero](zotero://select/library/items/{item_key})）"
                + analysis_link(record, document_dir))

    def render_source_table(email: dict, raw: dict, document_dir: Path) -> list:
        label = {"user_note": "用户 note（原文）", "template": "[模板] 固定文本",
                 "profile.interest": "[生成] 用户意图层（profile）"}
        paper_index = {p["item_key"]: p for p in email.get("papers", [])}
        for gap in email.get("gaps", []):
            paper_index.setdefault(gap["item_key"], gap)
        gap_index = {g["gap_id"]: g for g in email.get("gaps", [])}
        rows = ["| 句 | 来源 |", "|---|---|"]
        output_names = {"①": "兴趣段①真实关注", "②": "兴趣段②点名+桥接",
                        "③": "兴趣段③宽泛例子",
                        "future": "未来志向句"}
        for entry in raw.get("source_map", []):
            output = entry.get("output")
            names = []
            for sid in entry.get("source_ids", []):
                if sid in label:
                    names.append(label[sid])
                elif sid.startswith("paper:"):
                    paper = paper_index.get(sid[6:]) or {}
                    names.append(f"[生成] 论文《{paper.get('title') or paper.get('paper_title') or sid[6:]}》"
                                 + paper_links(paper, sid[6:], document_dir))
                elif sid.startswith("gap:"):
                    gap = gap_index.get(sid[4:]) or {}
                    names.append(f"[生成] future work（{gap.get('status')}，p.{gap.get('page')}，{gap.get('paper_title')}）"
                                 + paper_links(gap, gap.get("item_key") or gap.get("zotero_key"), document_dir))
                elif sid.startswith("later:"):
                    paper = paper_index.get(sid[6:]) or {}
                    names.append(f"[生成] 后续论文《{paper.get('title') or paper.get('paper_title') or sid[6:]}》"
                                 + paper_links(paper, sid[6:], document_dir))
                elif sid.startswith("idea:"):
                    names.append("[生成] 选中想法（idea_zh）")
                elif sid.startswith("direction_material:"):
                    names.append(direction_material_label(email, sid))
                else:
                    names.append(sid)
            rows.append(f"| {output_names.get(output, output)} | {'；'.join(names)} |")
        rows.append("| 資历段（現在は……取り組んでおります） | [生成候选+用户挑选] |")
        rows.append("| 抬头/寒暄/自我介绍/请求/收尾 | [模板] 固定文本 |")
        return rows

    def render_followup_source_table(email: dict) -> list:
        if len(email.get("direction_ids") or []) > 1:
            direction = (email.get("idea") or {}).get("title") or "跨方向想法"
        else:
            direction = email.get("name_zh") or email.get("name_ja") or "相关方向"
        return [
            "| 项目 | 来源 |", "|---|---|",
            "| 首封邮件中的学校、研究科、入学信息 | [邮件包] 同一 email 记录 |",
            f"| 首封邮件中的研究方向 | [邮件包] {direction} |",
            "| 初次发送日期、署名、附件说明 | [用户选择] 首封邮件发送记录 |",
            "| 其余正文 | [模板] 跟进邮件固定文本 |",
        ]

    def render_fact_check_card(email: dict, pack_path: Path, professor_dir: Path) -> list:
        lines = ["## 事实核对卡（发送前人工确认）", ""]
        key_gaps = [g for g in email.get("gaps", [])
                    if g.get("email_use") in ("anchor", "remaining_only", "anchor_with_caveat", "extension_context_only")]
        if not key_gaps:
            lines.append("（本封邮件未使用任何 future-work 事实锚点。）")
            lines.append("")
            return lines
        pack_rel = rel_path(pack_path, professor_dir)
        for gap in key_gaps:
            status = gap.get("status")
            lines.append(f"<details><summary>《{gap.get('paper_title')}》 future work（{status}）</summary>")
            lines.append("")
            lines.append(f"- 论文 Zotero 链接：[zotero](zotero://select/library/items/{gap.get('zotero_key')})"
                         + analysis_link(gap, professor_dir))
            lines.append(f"- 作者原话：「{gap.get('quote')}」")
            lines.append(f"- 中译：{gap.get('translation_zh')}")
            lines.append(f"- 页码：p.{gap.get('page')}（{gap.get('source')}）")
            lines.append(f"- 状态：{status}（置信度 {gap.get('confidence')}）")
            lines.append(f"- 后续论文依据：{gap.get('evidence') or '—'}")
            if status == "partial":
                lines.append(f"- 已做部分：{gap.get('completed_part') or '—'}")
                lines.append(f"- 剩余缺口：{gap.get('remaining_gap') or '—'}")
            if status == "unknown":
                lines.append("- ⚠ unknown：未查证是否已被教授后续论文实现，发送前请人工复核。")
            if status == "done_by_self":
                lines.append("- ⚠ 已被教授本人后续论文实现；本邮件只能以【我的延伸】口径提及，不得当开放 future work。")
            lines.append(f"- 邮件包：[{EMAIL_PACK}]({pack_rel})")
            lines.append(f"- 生成时间：{now_utc()}")
            lines.append("")
            lines.append("</details>")
            lines.append("")
        return lines

    return types.SimpleNamespace(
                find_boshu_analysis=find_boshu_analysis,
                load_header_sources=load_header_sources,
                header_values=header_values,
                subject_line=subject_line,
                compact_name=compact_name,
                email_item_is_evidence_seeded=email_item_is_evidence_seeded,
                current_source_fingerprints=current_source_fingerprints,
                validate_email_raw=validate_email_raw,
                require_user_choices=require_user_choices,
                require_followup_choices=require_followup_choices,
                find_followup_template_path=find_followup_template_path,
                load_id_map=load_id_map,
                humanized_paths=humanized_paths,
                email_template_body=email_template_body,
                assemble_draft=assemble_draft,
                body_salutation_line=body_salutation_line,
                render_checklist_table=render_checklist_table,
                cell_source=cell_source,
                render_source_table=render_source_table,
                direction_material_label=direction_material_label,
                render_followup_source_table=render_followup_source_table,
                render_fact_check_card=render_fact_check_card,
    )
