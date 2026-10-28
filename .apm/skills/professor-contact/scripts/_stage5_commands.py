#!/usr/bin/env python3
"""Stage-5 helper module for ``contact_state.py``.

The runner loads this helper by path next to itself and calls :func:`build`
once with its own helper functions and shared constants. The factory binds
those names in an enclosing scope, so the functions below keep the exact
bodies they had inside the runner (only their indentation changed). The
module never imports the runner, never adds itself to ``sys.path`` and
never builds a second failure channel.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
import types





def build(*, atomic_write,
          atomic_json,
          emit,
          fail,
          soft_exit,
          contact_evidence_decisions,
          resolve_contact_evidence,
          SCHEMA,
          MANAGED_BY,
          EMAIL_PACK,
          EMAIL_STATE,
          EMAIL_OVERVIEW,
          STAGE5_AUDIT_PROVENANCE,
          VERIFY_TIMESTAMP_FORMAT,
          now_utc,
          sha256_bytes,
          sha256_text,
          sha256_obj,
          read_json_file,
          require_professor_dir_under_program,
          truncate,
          rel_path,
          render_frontmatter,
          split_frontmatter,
          load_profile_text,
          load_header_sources,
          header_values,
          subject_line,
          current_source_fingerprints,
          verify_state,
          gap_job_block,
          stage5_output_peers,
          stage5_output_paths,
          stage5_output_id,
          stage5_mode,
          stage5_pack_owner,
          stage5_local_pack,
          stage5_choices_by_id,
          validate_email_raw,
          require_user_choices,
          require_followup_choices,
          find_followup_template_path,
          load_id_map,
          humanized_paths,
          assemble_draft,
          assemble_followup_draft,
          body_salutation_line,
          render_checklist_table,
          render_source_table,
          render_followup_source_table,
          render_fact_check_card):
    def cmd_stage5_plan(args) -> None:
        program_root = Path(args.program_root)
        mode = stage5_mode(args)
        pack_path, pack, all_emails, emails = stage5_local_pack(args, program_root)
        sources = load_header_sources(program_root)
        resolved_evidence = resolve_contact_evidence(
            program_root, list(dict.fromkeys(
                e.get("professor") for e in emails if e.get("professor"))))
        decisions = contact_evidence_decisions(emails, resolved_evidence)
        initial_read_only_plan = not getattr(args, "result", None) and \
            not getattr(args, "choices", None)
        fingerprint_state = (current_source_fingerprints(sources)
                             if initial_read_only_plan else None)
        verify_checks = {}
        for email in emails:
            professor_dir = Path(email.get("professor_dir") or program_root)
            key = email.get("professor")
            if key in verify_checks:
                continue
            check = verify_state(professor_dir, sources, decisions.get(key), fingerprint_state)
            decision = decisions.get(key)
            if check["ok"] and decision is not None and \
                    decision.get("status") == "needs_refresh":
                # A frozen-snapshot mismatch makes this professor's pack entry
                # stale for the whole run regardless of cache usability: plan
                # must demand the Stage-4 refresh deterministically, never leave
                # it to the agent reading the decision object alone.
                check = {"ok": False,
                         "reason": decision.get("reason_code") or "contact_evidence_snapshot_stale",
                         "path": None, "data": None}
            verify_checks[key] = check
        needs_recheck = [p for p, v in verify_checks.items() if not v["ok"]]
        template_path = None
        profile_path = args.profile
        if getattr(args, "template", None):
            template_path = args.template
        else:
            for candidate in [program_root.parent / "套磁邮件" / "套磁模板.md",
                              program_root / "套磁邮件" / "套磁模板.md"]:
                if candidate.is_file():
                    template_path = str(candidate)
                    break
        if not template_path:
            fail("template_required", "stage5 requires --template with the user's email template")
        if not Path(template_path).is_file():
            fail("template_error", f"template not found: {template_path}")
        template_text = Path(template_path).read_text(encoding="utf-8")
        if not args.result:
            jobs = []
            for email in emails:
                jobs.append({
                    "job_id": f"email:{email['email_id']}", "kind": "email",
                    "result_file": f"email-{sha256_text(email['email_id'])[:12]}.json",
                    "result_schema": {
                        "schema": 1, "kind": "email", "email_id": email["email_id"],
                        "interest_sentences_ja": ["①真实关注", "②点名+桥接", "③宽泛例子"],
                        "future_aspiration_ja": "…",
                        "learning_candidates": ["候补1", "候补2"],
                        "source_map": [{"output": "①", "source_ids": ["profile.interest"]},
                                       {"output": "②", "source_ids": ["paper:<item_key>"]},
                                       {"output": "③", "source_ids": ["gap:<gap_id>"]},
                                       {"output": "future", "source_ids": [f"idea:{email['idea']['id']}"]}]},
                    "model_input": {
                        "idea": email.get("idea"),
                        "direction_ids": email.get("direction_ids") or [],
                        "directions": email.get("directions") or [],
                        "user_note": truncate(email.get("user_note"), 800),
                        "papers": email.get("papers"),
                        "gaps": [gap_job_block(g) for g in email.get("gaps", [])],
                        "red_lines": email.get("red_lines"),
                        "soft_materials": {"positioning": email.get("soft_materials", {}).get("positioning", [])},
                        "profile_text": load_profile_text(profile_path, 1200),
                        "user_supplement": email.get("user_supplement") or "",
                        "allowed_sources": email.get("allowed_sources"),
                        "rules": {
                            "interest": "3 句、只写软层；长度按净正文计：当前邮件包 papers[].title 中实际完整逐字引用的论文标题文本不计入字数，标题以外的书名号、引号、标点和其他正文照常计入；净正文软上限 ≤180 日文字（runner：>180 警告、>200 拒绝）；①真实关注（普通发信人的接触、有限认识与自然好奇，禁恭维）②点名+桥接（真实标题、共同主题逐篇成立）③宽泛例子（仅可用 gaps 里 status∈{open,partial,unknown} 的精确 gap；done_by_self 禁锚；partial 只谈 remaining_gap；引用教授原话式，不找碴）",
                            "opening": "从普通发信人对这件事的真实接触和认识写起，允许有限认识（如听说过、觉得有用但还不熟悉），再顺承自然的好奇；不替用户提出研究问题，不把论文问题翻译成白话冒充个人兴趣。根据已有 profile、用户笔记和补充表达，不编具体经历、应用名称、长期兴趣或研究能力；没有依据时不声称听过、用过或读懂。日语简洁礼貌，不固定身份、自定位或「私は」开头，也不固定成「听过但没用过」句型。",
                            "exclusions": "禁方法名/模型名/算法名（标题内除外）、指标数字、数据集名、组件名、公式、限定语链、年份叙事",
                            "future_aspiration": "宽泛方向表述+背景技能，禁具体技术栈，不用其他方向原句",
                            "learning": "2-3 个名词短语候选，贴近 profile 真实知识储备，交用户挑选",
                            "source_map": "每句必须给来源；③只能用 gap:<id>；所有 source_ids ⊆ allowed_sources"}}})
            payload = {
                "status": "ok", "email_pack": str(pack_path),
                "emails": [e.get("email_id") for e in emails],
                "verify": {p: ("ok" if v["ok"] else f"needs_recheck:{v['reason']}")
                           for p, v in verify_checks.items()},
                "needs_recheck_professors": needs_recheck,
                "contact_evidence": decisions,
                "template": template_path or "embedded",
                "output_mode": mode,
                "followup_template": (find_followup_template_path(
                    program_root, getattr(args, "followup_template", None)) or "embedded"),
                "jobs": jobs,
            }
            if initial_read_only_plan:
                fingerprints = fingerprint_state["source_fingerprints"]
                hint = None if fingerprint_state["failed_field"] else {
                    "source_fingerprints": fingerprints,
                    "verified_at_format": VERIFY_TIMESTAMP_FORMAT,
                }
                payload["verify_write_hints"] = {
                    professor: hint for professor in verify_checks
                }
                payload["verify_diagnostics"] = {
                    professor: {
                        "reason": check.get("reason"),
                        "failed_field": check.get("failed_field"),
                        "diagnostic_kind": check.get("diagnostic_kind"),
                    }
                    for professor, check in verify_checks.items()
                }
            emit(payload)
            return
        result_path = Path(args.result)
        results, rerror = read_json_file(result_path)
        if rerror:
            fail("result_missing", f"{result_path}: {rerror}")
        by_id = load_id_map(result_path, {e.get("email_id") for e in emails}, "email result",
                            exact=not bool(args.email_id))
        # The model result contract is checked before anything else: it is the
        # caller's own file, and a broken result must not hide behind a cache gate.
        problems_by_id = {}
        for email in emails:
            email_id = email.get("email_id")
            raw = by_id.get(email_id)
            if raw is None:
                fail("result_missing", f"no raw result for {email_id}")
            problems = validate_email_raw(email, raw)
            hard = [x for x in problems if not x.startswith("WARNING")]
            if hard:
                fail("invalid_result_json", f"{email_id}: {'; '.join(hard)}")
            problems_by_id[email_id] = [x for x in problems if x.startswith("WARNING")]
        # Verification hard gate: until every selected professor's 送信前核验 is
        # usable, no caller row may be read at all — the only pre-gate recipient
        # decision surface is Step 2.5 writing `_contact_verify.json` items.email.
        # The two stop codes keep their distinct repairs: a bare contact-evidence
        # reason means Stage 4 must re-freeze the pack, `verify_*` means Step 2.5.
        for professor, check in verify_checks.items():
            if check["ok"]:
                continue
            decision = decisions.get(professor) or {}
            if decision.get("status") == "needs_refresh":
                soft_exit("needs_refresh", decision.get("reason_code") or
                          "contact_evidence_snapshot_stale", professor=professor,
                          message="联系方式证据快照与上游 live 指纹不一致或缺失：先重跑阶段 4 刷新 "
                                  "邮件输入.json，再重跑阶段 5。核验通过前不读取 choices。未写盘。")
            soft_exit("needs_refresh", f"verify_{check['reason']}", professor=professor,
                      message=f"送信前核验缓存不可用（{check['reason']}）：先完成 Step 2.5 核验。"
                              "核验通过前不读取 choices。未写盘。")
        # Issue #68 plan r12: plan and finalize share one owner-local choices
        # loader — root already partitioned the raw choices once, so this runner
        # only validates the rows of its own one-professor bundle (exact-one
        # duplicate, missing and field checks stay here).
        choices_by_id = stage5_choices_by_id(
            args, stage5_pack_owner(pack, pack_path), emails)
        drafts = []
        for email in emails:
            raw = by_id.get(email.get("email_id"))
            warnings = problems_by_id[email.get("email_id")]
            choices = choices_by_id.get(email.get("email_id"))
            require_user_choices(email.get("email_id"), choices)
            if mode in ("both", "followup"):
                require_followup_choices(email.get("email_id"), choices)
            stage5_recipient_authority(
                email.get("email_id"), choices,
                (verify_checks.get(email.get("professor")) or {}).get("data"))
            if mode in ("first", "both"):
                draft, protected, banned = assemble_draft(
                    email, raw, choices, sources, template_text)
                drafts.append({"output_id": stage5_output_id(email.get("email_id"), "initial"),
                               "email_id": email.get("email_id"), "kind": "initial",
                               "draft": draft, "protected": protected, "banned": banned,
                               "warnings": warnings, "result_file": str(result_path)})
            if mode in ("followup", "both"):
                followup_template_path = find_followup_template_path(
                    program_root, getattr(args, "followup_template", None))
                if not followup_template_path:
                    fail("followup_template_required", "follow-up mode requires --followup-template")
                if not Path(followup_template_path).is_file():
                    fail("template_error", f"follow-up template not found: {followup_template_path}")
                followup_template = Path(followup_template_path).read_text(encoding="utf-8")
                followup_draft, followup_protected, followup_banned = assemble_followup_draft(
                    email, choices, sources, followup_template,
                    verify_checks.get(email.get("professor"), {}).get("data"))
                drafts.append({"output_id": stage5_output_id(email.get("email_id"), "followup"),
                               "email_id": email.get("email_id"), "kind": "followup",
                               "draft": followup_draft, "protected": followup_protected,
                               "banned": followup_banned, "warnings": warnings,
                               "result_file": str(result_path)})
        emit({"status": "ok", "drafts": drafts, "output_mode": mode})

    def cmd_stage5_finalize(args) -> None:
        audit_suffix = STAGE5_AUDIT_PROVENANCE[args.audit_provenance]
        program_root = Path(args.program_root)
        mode = stage5_mode(args)
        pack_path, pack, all_emails, emails = stage5_local_pack(args, program_root)
        sources = load_header_sources(program_root)
        resolved_evidence = resolve_contact_evidence(
            program_root, list(dict.fromkeys(
                e.get("professor") for e in emails if e.get("professor"))))
        decisions = contact_evidence_decisions(emails, resolved_evidence)
        # Verification hard gate, mirroring cmd_stage5_plan: until every selected
        # professor's 送信前核验 is usable, no caller row — choices, result rows,
        # humanized bodies — may be read at all. The per-email loop below consumes
        # these saved checks so plan and finalize share one verify semantics.
        verify_checks = {}
        for email in emails:
            professor_dir = Path(email.get("professor_dir") or program_root)
            key = email.get("professor")
            if key in verify_checks:
                continue
            check = verify_state(professor_dir, sources, decisions.get(key))
            decision = decisions.get(key)
            if check["ok"] and decision is not None and \
                    decision.get("status") == "needs_refresh":
                # A frozen-snapshot mismatch makes this professor's pack entry
                # stale for the whole run regardless of cache usability: the
                # deterministic repair is a Stage-4 refresh, not a web lookup.
                check = {"ok": False,
                         "reason": decision.get("reason_code") or "contact_evidence_snapshot_stale",
                         "path": None, "data": None}
            verify_checks[key] = check
        for professor, check in verify_checks.items():
            decision = decisions.get(professor)
            if not check["ok"]:
                if decision is not None and decision.get("status") == "needs_refresh":
                    soft_exit("needs_refresh", decision.get("reason_code") or
                              "contact_evidence_snapshot_stale", professor=professor,
                              message="联系方式证据快照与上游 live 指纹不一致或缺失：先重跑阶段 4 刷新 "
                                      "邮件输入.json，再重跑阶段 5。未写盘。")
                soft_exit("needs_refresh", f"verify_{check['reason']}",
                          professor=professor,
                          message=f"送信前核验缓存不可用（{check['reason']}）：先完成 Step 2.5 核验。未写盘。")
            if decision is not None and decision.get("status") not in ("escalate", "needs_refresh"):
                # Recipient-evidence consistency backstop: an accepted decision
                # must still match the cache the checklist will print, and the
                # conflict is resolved before any choices row is read.
                cache_email_value = str((((check["data"] or {}).get("items") or {}).get("email") or {})
                                        .get("value") or "").strip()
                recipient = str(decision.get("recipient_email") or "").strip()
                if not cache_email_value or cache_email_value.casefold() != recipient.casefold():
                    fail("contact_evidence_mismatch",
                         f"{professor}: 本地联系方式证据判定 {decision['status']}，收件邮箱应为 "
                         f"{recipient}；核对表邮箱为「{cache_email_value or '空'}」。"
                         "请按证据填写 _contact_verify.json，或重建 _联系方式证据.json 后重跑阶段 4。")
        result_path = Path(args.result)
        raw_by_id = load_id_map(result_path, {e.get("email_id") for e in emails}, "email result",
                                exact=not bool(args.email_id))
        # Same owner-local bundle loader as stage5-plan (Issue #68 plan r12).
        choices_by_id = stage5_choices_by_id(
            args, stage5_pack_owner(pack, pack_path), emails)
        humanized_by_id = humanized_paths(args, emails, exact=not bool(args.email_id))
        decision = None
        if getattr(args, "decision_file", None):
            decision_data, decision_error = read_json_file(Path(args.decision_file))
            if decision_error is None and isinstance(decision_data, dict):
                decision = decision_data.get("decision")
        template_path = getattr(args, "template", None)
        if not template_path:
            for candidate in [program_root.parent / "套磁邮件" / "套磁模板.md",
                              program_root / "套磁邮件" / "套磁模板.md"]:
                if candidate.is_file():
                    template_path = str(candidate)
                    break
        if not template_path:
            fail("template_required", "stage5 requires --template with the user's email template")
        if not Path(template_path).is_file():
            fail("template_error", f"template not found: {template_path}")
        template_text = Path(template_path).read_text(encoding="utf-8")
        followup_template_path = find_followup_template_path(
            program_root, getattr(args, "followup_template", None))
        if mode in ("both", "followup") and not followup_template_path:
            fail("followup_template_required", "follow-up mode requires --followup-template")
        if followup_template_path and not Path(followup_template_path).is_file():
            fail("template_error", f"follow-up template not found: {followup_template_path}")
        followup_template = (Path(followup_template_path).read_text(encoding="utf-8")
                             if followup_template_path else None)
        state_updates = {}
        prepared = []

        # Validate every email and prepare every file before committing any output.
        for email in emails:
            email_id = email.get("email_id")
            raw = raw_by_id.get(email_id)
            problems = validate_email_raw(email, raw)
            hard = [p for p in problems if not p.startswith("WARNING")]
            if hard:
                fail("invalid_result_json", f"{email_id}: {'; '.join(hard)}")
            choices = choices_by_id.get(email_id)
            professor_dir = Path(email.get("professor_dir") or program_root)
            # The whole-batch verification gate above already stopped on any
            # unusable professor before choices were read; consume its saved
            # result instead of re-deriving a second verify semantics.
            verify = verify_checks[email.get("professor")]["data"]
            warnings = (verify.get("items") or {}).get("warnings") or []
            decision = decisions.get(email.get("professor"))
            cache_email_value = str(((verify.get("items") or {}).get("email") or {})
                                    .get("value") or "").strip()
            # Past the verification gate: only now may this row be validated, and
            # its explicit address only ever confirm the verified authority.
            require_user_choices(email_id, choices)
            if mode in ("both", "followup"):
                require_followup_choices(email_id, choices)
            stage5_recipient_authority(email_id, choices, verify)
            roster_verdict = ((verify.get("items") or {}).get("roster") or {}).get("verdict")
            email_verdict = ((verify.get("items") or {}).get("email") or {}).get("verdict")
            banner_needed = bool(warnings) or roster_verdict == "not_found" or email_verdict == "unverified"
            values = header_values(sources, email)
            # Fallback only: the 「抬头逐字」 row must show the assembled body's own
            # salutation verbatim (the user template's fixed text may format the
            # header differently, e.g. without a trailing 「：」), so the per-variant
            # header is derived from the draft body below.
            checklist_header = (f"{values['大学']}／{values['研究科']}／"
                                f"{values['先生名']}先生：")
            variants = []
            if mode in ("first", "both"):
                draft, protected, banned = assemble_draft(email, raw, choices, sources, template_text)
                variants.append(("initial", draft, protected, banned, "套磁邮件",
                                 Path(template_path).name if template_path else "内嵌",
                                 render_source_table(email, raw)))
            if mode in ("followup", "both"):
                draft, protected, banned = assemble_followup_draft(
                    email, choices, sources, followup_template, verify)
                variants.append(("followup", draft, protected, banned, "套磁跟进邮件",
                                 Path(followup_template_path).name if followup_template_path else "内嵌",
                                 render_followup_source_table(email)))

            input_fp = email.get("source_hash") or sha256_obj(email)
            if str(professor_dir) not in state_updates:
                email_state, serr = read_json_file(professor_dir / EMAIL_STATE)
                state_updates[str(professor_dir)] = (
                    json.loads(json.dumps(email_state, ensure_ascii=False))
                    if serr is None and isinstance(email_state, dict)
                    else {"schema": SCHEMA, "managed_by": MANAGED_BY, "emails": {}})
            email_state = state_updates[str(professor_dir)]
            root_entry = email_state.setdefault("emails", {}).setdefault(email_id, {})
            if decision:
                root_entry["contact_evidence"] = {
                    "status": decision["status"], "reason_code": decision["reason_code"],
                    "chosen_email": cache_email_value or None,
                    "evidence_email": decision["recipient_email"],
                    "web_lookup_required": decision["web_lookup_required"],
                    "source": decision["source"], "snapshot_stale": decision["snapshot_stale"],
                    "provenance": decision["provenance"], "recorded_at": now_utc()}
            for kind, draft, protected, banned, heading, template_name, source_rows in variants:
                output_id = stage5_output_id(email_id, kind)
                humanized = humanized_by_id[output_id].read_text(encoding="utf-8")
                missing = [p for p in protected if p and p not in humanized]
                if missing:
                    fail("humanizer_violation",
                         f"{output_id}: humanized text lost protected strings: {missing}")
                violated = [b for b in banned if b and b in humanized]
                if violated:
                    fail("humanizer_violation", f"{output_id}: banned phrases appeared: {violated}")
                if "{{" in humanized:
                    fail("humanizer_violation", f"{output_id}: residual {{}} placeholders")
                subject_match = re.match(r"Subject: (.*)", humanized)
                subject = choices.get("followup_subject") if kind == "followup" else None
                subject = subject or (subject_match.group(1).strip() if subject_match else
                                      (subject_line(values) if kind == "initial" else
                                       f"Re: {subject_line(values)}"))
                body_text = re.sub(r"^Subject: .*\n+", "", humanized, count=1)
                lines = [
                    f"# {heading} — {email.get('professor')}（{email.get('name_ja')}）",
                    "",
                    f"> {now_utc()} ｜ 类型：{'首封' if kind == 'initial' else '无回复跟进'} ｜ profile：{'有' if pack.get('profile_fingerprint') else '无'} ｜ 模板：{template_name} ｜ 方向：{email.get('name_zh') or email.get('name_ja')}{audit_suffix}",
                    "",
                ]
                if kind == "followup":
                    lines.append(f"> 跟进依据：首封邮件 email_id `{email_id}`；初次发送日：{choices.get('initial_sent_date')}。建议在首封邮件发送数日后使用。")
                    lines.append("")
                if banner_needed:
                    lines.append("> ⚠️ **送信前注意**：" + "；".join(
                        ([f"邮箱 {email_verdict}"] if email_verdict == "unverified" else []) +
                        ([f"教员在册 {roster_verdict}"] if roster_verdict == "not_found" else []) +
                        [str(w) for w in warnings]) + "。请人工确认后再发。")
                    lines.append("")
                lines.append(f"## 送信前核对（发信前最后过目；数据源 _contact_verify.json @ {verify.get('verified_at')}）")
                lines.append("")
                lines.extend(render_checklist_table(
                    verify, body_salutation_line(body_text, values) or checklist_header))
                lines.append("")
                lines.append("## 邮件正文")
                lines.append("")
                lines.append(f"Subject: {subject}")
                lines.append("")
                lines.append(body_text.strip())
                lines.append("")
                lines.append("## 来源标注（仅 md 内审用，不进 txt）")
                lines.append("")
                lines.extend(source_rows)
                lines.append("")
                red_lines = email.get("red_lines") or []
                if red_lines:
                    lines.append("## 生成时消费的红线（已遵守）")
                    lines.append("")
                    for red in red_lines:
                        lines.append(f"- 【{red.get('scope')}】{red.get('text')}")
                    lines.append("")
                lines.extend(render_fact_check_card(email, pack_path, professor_dir))
                md_body = "\n".join(lines).rstrip() + "\n"
                txt_body = f"Subject: {subject}\n\n{body_text.strip()}\n"
                state_fingerprint = sha256_obj({"output_id": output_id, "input": input_fp})
                md_path, txt_path = stage5_output_paths(
                    email,
                    stage5_output_peers(
                        email, all_emails, professor_dir, targeted=bool(args.email_id)),
                    professor_dir, kind)
                previous = root_entry if kind == "initial" else root_entry.get("followup", {})
                old_render = previous.get("render") or {}
                existing_md_sha = None
                if md_path.is_file():
                    _, existing_body = split_frontmatter(md_path.read_text(encoding="utf-8"))
                    existing_md_sha = sha256_text(existing_body)
                md_sha = sha256_text(md_body)
                if (existing_md_sha is not None and old_render.get("md", {}).get("sha256") and
                        existing_md_sha not in (md_sha, old_render["md"]["sha256"]) and
                        decision != "overwrite"):
                    soft_exit("needs_decision", "manual_markdown_changed", target=str(md_path))
                existing_txt_sha = sha256_bytes(txt_path.read_bytes()) if txt_path.is_file() else None
                txt_sha = sha256_text(txt_body)
                if (existing_txt_sha is not None and old_render.get("txt", {}).get("sha256") and
                        existing_txt_sha not in (txt_sha, old_render["txt"]["sha256"]) and
                        decision != "overwrite"):
                    soft_exit("needs_decision", "manual_markdown_changed", target=str(txt_path))
                prepared.append({"email": email, "email_id": email_id, "output_id": output_id,
                                 "kind": kind, "professor_dir": professor_dir, "raw": raw,
                                 "choices": choices, "md": md_path, "txt": txt_path,
                                 "md_body": md_body, "txt_body": txt_body, "md_sha": md_sha,
                                 "txt_sha": txt_sha, "state_fingerprint": state_fingerprint,
                                 "input_fp": input_fp, "warnings": warnings,
                                 "banner": banner_needed})
                update = {"generated_at": now_utc(), "input_fingerprint": input_fp,
                          "model_result": raw, "choices": choices,
                          "files": {"md": str(md_path), "txt": str(txt_path)},
                          "render": {"md": {"sha256": md_sha}, "txt": {"sha256": txt_sha}},
                          "validation": {"result": "pending", "rounds": 0}}
                if kind == "initial":
                    root_entry.update(update)
                else:
                    root_entry.setdefault("followup", {}).update(update)

        # Issue #68: this professor's transaction commits on its own validation. The
        # program aggregate is a derived projection that stage5-rebuild-overview
        # owns, so a stale, conflicting or missing overview is never a commit gate
        # here and no local run writes it.
        for item in prepared:
            atomic_write(item["md"], render_frontmatter(
                sha256_obj({"email_id": item["email_id"], "input": item["input_fp"]}), item["md_sha"]) + item["md_body"])
            atomic_write(item["txt"], item["txt_body"])
        for professor_dir, email_state in state_updates.items():
            atomic_json(Path(professor_dir) / EMAIL_STATE, email_state)
        overview_path = program_root / "教授研究" / EMAIL_OVERVIEW
        emit({"status": "ok", "emails": [
            {"email_id": item["email_id"], "output_id": item["output_id"], "kind": item["kind"],
             "md": str(item["md"]), "txt": str(item["txt"]),
             "warnings": len(item["warnings"]), "banner": item["banner"]}
            for item in prepared],
            "overview_md": str(overview_path) if overview_path.is_file() else None})

    def stage5_recipient_authority(email_id: str, choices: dict, verify: dict | None) -> str:
        """Return the single recipient address an email may render.

        `_contact_verify.json` is the send-time authority; `choices.email_address`
        is the caller's explicit recipient *decision*, which Step 2.5 records into
        that cache. It may confirm the authority and may never replace it, so an
        address that disagrees with — or arrives before — the verified value fails
        closed instead of silently steering a follow-up to a different mailbox.
        """
        verified = str((((verify or {}).get("items") or {}).get("email") or {})
                       .get("value") or "").strip()
        stated = str((choices or {}).get("email_address") or "").strip()
        if not stated:
            return verified
        if not verified:
            fail("recipient_conflict",
                 f"{email_id}: choices.email_address 已给出，但 _contact_verify.json 还没有已核验的"
                 "收件邮箱。先在 Step 2.5 把用户的明确答复写入 items.email（source user_provided，"
                 "verdict confirmed）再重跑；choices 不得代替送信前核验。")
        if stated.casefold() != verified.casefold():
            fail("recipient_conflict",
                 f"{email_id}: choices.email_address「{stated}」与送信前核验的权威收件邮箱"
                 f"「{verified}」不一致。按 Step 2.5 复核结论修正 choices 或重写缓存，"
                 "不存在第二份收件人权威。")
        return verified

    def cmd_stage5_rebuild_overview(args) -> None:
        """Rebuild the program 套磁邮件总览.md from professor-local Stage-5 state.

        Issue #68 made this aggregate the only Stage-5 writer of a derived
        projection: it reads every professor-local pack, its exact local state and
        its verify cache, and writes nothing else. A malformed pack or state fails
        closed before the file is touched, and a manual overview edit stops only
        this rebuild.
        """
        program_root = Path(args.program_root)
        research_root = program_root / "教授研究"
        sources = load_header_sources(program_root)
        overview_rows = ["| 教授 | 方向（ja/zh） | 收件邮箱 | 核验 | 首封邮件 | 跟进邮件 | 首封纯文本 | 跟进纯文本 |",
                         "|---|---|---|---|---|---|---|---|"]
        professors = 0
        rendered = 0
        generated_at = []
        for pack_path in (sorted(research_root.rglob(EMAIL_PACK)) if research_root.is_dir() else []):
            if pack_path.parent == research_root:
                # The legacy program-level pack is Issue #67's migration input and
                # names no professor, so it contributes no rows to the aggregate.
                continue
            pack, error = read_json_file(pack_path)
            if error:
                fail("missing_email_pack", f"email pack unreadable: {pack_path}",
                     email_pack=str(pack_path))
            owner = stage5_pack_owner(pack, pack_path)
            require_professor_dir_under_program(owner["professor_dir"], program_root)
            state_path = owner["professor_dir"] / EMAIL_STATE
            email_state, state_error = read_json_file(state_path)
            if state_error == "not_found":
                # Stage 5 never ran for this professor: there is nothing to project.
                continue
            if state_error or not isinstance(email_state, dict):
                fail("missing_email_state",
                     f"{owner['professor']}: email state unreadable: {state_path}")
            entries = email_state.get("emails") or {}
            if not isinstance(entries, dict):
                fail("missing_email_state",
                     f"{owner['professor']}: email state has no emails object: {state_path}")
            verify_check = verify_state(owner["professor_dir"], sources)
            items = ((verify_check.get("data") or {}).get("items") or {})
            email_value = (items.get("email") or {}).get("value") or "?"
            bad = []
            if (items.get("roster") or {}).get("verdict") == "not_found":
                bad.append("在册 not_found")
            if (items.get("email") or {}).get("verdict") == "unverified":
                bad.append("邮箱 unverified")
            bad.extend(str(w) for w in (items.get("warnings") or []))
            verify_label = "✅ 全 confirmed" if not bad else "⚠ " + "；".join(bad)

            def link(path: str | None, label: str) -> str:
                return f"[{label}]({rel_path(Path(path), research_root)})" if path else "—"

            professors += 1
            for email in pack.get("emails") or []:
                if not isinstance(email, dict):
                    continue
                entry = entries.get(email.get("email_id"))
                if not isinstance(entry, dict):
                    continue
                initial = entry.get("files") or {}
                followup = (entry.get("followup") or {}).get("files") or {}
                if not initial and not followup:
                    continue
                for value in (entry.get("generated_at"),
                              (entry.get("followup") or {}).get("generated_at")):
                    if isinstance(value, str) and value:
                        generated_at.append(value)
                rendered += 1
                overview_rows.append(
                    f"| {email.get('professor')} | {email.get('name_ja')}/{email.get('name_zh')} | "
                    f"{email_value} | {verify_label} | {link(initial.get('md'), '.md')} | "
                    f"{link(followup.get('md'), '跟进 .md')} | {link(initial.get('txt'), '首封 .txt')} | "
                    f"{link(followup.get('txt'), '跟进 .txt')} |")
        overview_body = ("# 套磁邮件总览\n\n"
                         f"> {max(generated_at, default='尚无已提交邮件')} ｜ 由 contact_state 渲染\n\n" +
                         "\n".join(overview_rows) + "\n")
        overview_path = research_root / EMAIL_OVERVIEW
        if overview_path.exists():
            header, existing_body = split_frontmatter(overview_path.read_text(encoding="utf-8"))
            if not header or header.get("managed_by") != MANAGED_BY or \
                    header.get("render_sha256") != sha256_text(existing_body):
                soft_exit("needs_decision", "manual_markdown_changed", target=str(overview_path))
        body_sha = sha256_text(overview_body)
        atomic_write(overview_path, render_frontmatter(
            sha256_obj({"projection": EMAIL_OVERVIEW, "body": body_sha}), body_sha) + overview_body)
        emit({"status": "ok", "overview_md": str(overview_path), "professors": professors,
              "emails": rendered})

    def cmd_stage5_record_validation(args) -> None:
        professor_dir = Path(args.professor_dir)
        state_path = professor_dir / EMAIL_STATE
        state, state_error = read_json_file(state_path)
        if state_error or not isinstance(state, dict):
            fail("missing_email_state", f"email state unreadable: {state_path}")
        validation_data, validation_error = read_json_file(Path(args.validation_file))
        if validation_error or not isinstance(validation_data, dict):
            fail("invalid_validation_json", f"validation file unreadable: {args.validation_file}")
        results = validation_data.get("results")
        if not isinstance(results, list) or not results:
            fail("invalid_validation_json", "validation results must be a non-empty list")
        emails = state.get("emails")
        if not isinstance(emails, dict):
            fail("invalid_email_state", "email state has no emails object")
        validated = {}
        seen = set()
        for result in results:
            if not isinstance(result, dict):
                fail("invalid_validation_json", "each validation result must be an object")
            email_id = result.get("email_id")
            output_id = result.get("output_id") or email_id
            kind = "followup" if isinstance(output_id, str) and output_id.endswith("::followup") else "initial"
            base_email_id = output_id[:-len("::followup")] if kind == "followup" else email_id
            validation_result = result.get("result")
            rounds = result.get("rounds", 0)
            issues = result.get("issues")
            if output_id in seen:
                fail("invalid_validation_json", f"duplicate validation result for {output_id}")
            seen.add(output_id)
            if base_email_id not in emails:
                fail("unknown_email_id", f"validation email_id not in state: {base_email_id}")
            if kind == "initial" and output_id != email_id:
                fail("invalid_validation_json", f"initial output_id mismatch for {email_id}")
            if validation_result not in ("pass", "fail_after_2_rounds", "skipped"):
                fail("invalid_validation_json", f"invalid validation result for {output_id}: {validation_result}")
            if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
                fail("invalid_validation_json", f"invalid validation rounds for {output_id}: {rounds}")
            if validation_result == "pass" and rounds not in (1, 2):
                fail("invalid_validation_json", f"pass validation needs 1-2 rounds for {output_id}")
            if validation_result == "fail_after_2_rounds" and rounds != 2:
                fail("invalid_validation_json", f"fail_after_2_rounds needs rounds=2 for {output_id}")
            if validation_result == "skipped" and rounds > 2:
                fail("invalid_validation_json", f"skipped validation needs rounds=0-2 for {output_id}")
            if not isinstance(issues, list):
                fail("invalid_validation_json", f"validation issues must be a list for {output_id}")
            validated[output_id] = {
                "email_id": base_email_id, "kind": kind,
                "result": validation_result, "rounds": rounds,
                "issues": issues, "validated_at": now_utc()}
        updated = []
        for output_id, validation in validated.items():
            target = emails[validation["email_id"]]
            if validation["kind"] == "followup":
                target.setdefault("followup", {})["validation"] = validation
            else:
                target["validation"] = validation
            updated.append(output_id)
        atomic_json(state_path, state)
        emit({"status": "ok", "state_path": str(state_path), "updated": updated})

    return types.SimpleNamespace(
                cmd_stage5_plan=cmd_stage5_plan,
                cmd_stage5_finalize=cmd_stage5_finalize,
                stage5_recipient_authority=stage5_recipient_authority,
                cmd_stage5_rebuild_overview=cmd_stage5_rebuild_overview,
                cmd_stage5_record_validation=cmd_stage5_record_validation,
    )
