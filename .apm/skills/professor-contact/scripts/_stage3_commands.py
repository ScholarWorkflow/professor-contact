#!/usr/bin/env python3
"""Stage-3 helper module for ``contact_state.py``.

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
import json
import os
import sys
import types





def build(*, atomic_write,
          staged_pair_commit,
          emit,
          fail,
          soft_exit,
          _stage3_args_from_invocation,
          MANAGED_BY,
          CANDIDATE_STATE_SCHEMA,
          DIRECTION_IDENTITY_VERSION,
          STAGE3_GENERATOR_CONTRACT_VERSION,
          CANDIDATE_STATE_KIND,
          INPUT_PACK,
          CANDIDATE_STATE,
          CANDIDATES_MD,
          CANDIDATES_OVERVIEW,
          SELECTION_FILE,
          REFRESH_SCOPES,
          QUOTE_INPUT_CHARS,
          TRANSLATION_INPUT_CHARS,
          now_utc,
          sha256_text,
          sha256_obj,
          read_json_file,
          require_professor_dir_under_program,
          truncate,
          rel_path,
          safe_result_file,
          direction_machine_id,
          direction_papers,
          render_frontmatter,
          split_frontmatter,
          managed_conflict,
          load_input_pack,
          load_candidate_state,
          strict_candidate_state,
          profile_fingerprint,
          load_profile_text,
          _direction_slices,
          _cross_group_fresh,
          _parse_direction_id_list,
          _parse_cross_groups,
          STAGE3_INVOCATION_VERSION,
          stage3_validation_evidence,
          stage3_correction_scopes,
          stage3_repairable_correction_directions,
          carry_stage3_validator,
          stage3_current_result,
          require_stage3_correction_invariants,
          _write_stage3_invocation,
          _read_stage3_invocation,
          _require_invocation_source,
          validate_candidate_result,
          validate_cross_result,
          render_candidates_md,
          render_candidates_overview,
          canonical_professor_dir):
    def _stage3_selected_scope_keys(selection_path: Path, professor_dir: Path,
                                    by_ckey: dict) -> set:
        """Selected-refresh scope from one explicit professor-local selection container.

        An explicit ``--selection`` is ONE professor's own container (issue #67): the
        container's top-level canonical ``professor_dir`` and every row's canonical
        ``professor_dir`` must equal the current professor directory before any
        direction is consumed. A missing, unresolvable or foreign identity fails the
        refresh before task generation or any formal write — never silently skipped,
        rebound to the container's directory, or accepted on the top-level check
        alone. Direction reading keeps the exact machine relation (canonical
        ``direction_ids`` first, deprecated ``direction_id`` / ``collection_key``
        through the pack's unique mapping); the display name never filters rows."""
        selection_data, sel_error = read_json_file(Path(selection_path))
        if sel_error:
            fail("invalid_params", f"selection file unreadable: {selection_path}")
        if not isinstance(selection_data, dict):
            fail("invalid_selection",
                 f"selection container must be an object: {selection_path}")
        canonical = canonical_professor_dir(professor_dir)
        container_dir = selection_data.get("professor_dir")
        if not str(container_dir or "").strip() \
                or canonical_professor_dir(container_dir) != canonical:
            fail("selection_scope_mismatch",
                 f"selection container {selection_path} is bound to "
                 f"{container_dir or 'no professor_dir'}, not the current professor "
                 f"directory {professor_dir}")
        rows = selection_data.get("selections")
        if not isinstance(rows, list):
            fail("invalid_selection",
                 f"selection container selections must be a list: {selection_path}")
        selected_keys = set()
        for index, sel in enumerate(rows):
            if not isinstance(sel, dict):
                fail("invalid_selection",
                     f"selections[{index}] in {selection_path} must be an object")
            row_dir = sel.get("professor_dir")
            if not str(row_dir or "").strip() \
                    or canonical_professor_dir(row_dir) != canonical:
                fail("selection_scope_mismatch",
                     f"selections[{index}] in {selection_path} carries professor_dir "
                     f"{row_dir or 'missing'}; a professor-local container may only hold "
                     "rows bound to the same canonical directory")
            scope = sel.get("direction_ids")
            if isinstance(scope, list) and scope:
                selected_keys.update(str(did) for did in scope if did)
                continue
            sel_did = sel.get("direction_id")
            if not sel_did:
                legacy = by_ckey.get(sel.get("collection_key"))
                sel_did = direction_machine_id(legacy) if legacy is not None else None
            if sel_did:
                selected_keys.add(sel_did)
        return selected_keys

    def cmd_stage3_plan(args) -> None:
        invocation = _read_stage3_invocation(args)
        if invocation is None and not getattr(args, "professor_dir", None):
            fail("invalid_params",
                 "stage3-plan needs --professor-dir or an invocation credential "
                 "(--invocation-file + --invocation-sha256)")
        credential_correction = invocation is not None and \
            bool(getattr(args, "validation_file", None))
        if getattr(args, "capture_invocation", None) and \
                getattr(args, "validation_file", None):
            fail("invalid_params",
                 "--capture-invocation records a first-round plan; correction plans "
                 "reuse the original invocation credential")
        if invocation is not None:
            _require_invocation_source(invocation)
            args = _stage3_args_from_invocation(args, invocation,
                                                correction=credential_correction)
        professor_dir = Path(args.professor_dir)
        program_root = Path(args.program_root) if args.program_root else professor_dir.parent.parent
        require_professor_dir_under_program(professor_dir, program_root)
        pack, pack_error = load_input_pack(professor_dir)
        if pack is None:
            soft_exit("needs_refresh", "missing_input_pack",
                      pack_path=str(professor_dir / INPUT_PACK),
                      message="缺 套磁候选输入.json：先跑阶段 2（professor-contact-analyzer）生成输入包；不回读任何 Markdown。")
        refresh_scope = args.refresh_scope or "flagged"
        if refresh_scope not in REFRESH_SCOPES:
            fail("invalid_params", f"refresh_scope must be one of {REFRESH_SCOPES}")
        pack_directions = pack.get("directions") or []
        by_did = {direction_machine_id(d): d for d in pack_directions}
        by_ckey = {}
        for d in pack_directions:
            ckey = d.get("collection_key")
            if isinstance(ckey, str) and ckey.strip() and ckey not in by_ckey:
                by_ckey[ckey] = d
            elif isinstance(ckey, str) and ckey.strip():
                by_ckey[ckey] = None  # ambiguous projection name
        direction_id_arg = getattr(args, "direction_id", None)
        collection_key_arg = getattr(args, "collection_key", None)
        if collection_key_arg and not direction_id_arg:
            # Deprecated v1 compatibility path: resolve through the pack's exact
            # machine mapping; never treat the projection key as identity itself.
            resolved = by_ckey.get(collection_key_arg)
            if resolved is None:
                fail("invalid_params",
                     f"collection_key not found (or ambiguous) in input pack: {collection_key_arg}")
            direction_id_arg = direction_machine_id(resolved)
        if direction_id_arg and direction_id_arg not in by_did:
            fail("invalid_params", f"direction_id not found in input pack: {direction_id_arg}")
        if collection_key_arg and direction_id_arg:
            resolved = by_ckey.get(collection_key_arg)
            if resolved is None or direction_machine_id(resolved) != direction_id_arg:
                fail("invalid_params",
                     f"collection_key {collection_key_arg!r} and direction_id {direction_id_arg!r} "
                     "resolve to different directions")
        skip_ids = _parse_direction_id_list(getattr(args, "skip_direction_ids", None),
                                            "skip_direction_ids")
        unknown_skip = [d for d in skip_ids if d not in by_did]
        if unknown_skip:
            fail("invalid_params", f"skip_direction_ids outside input pack: {unknown_skip}")
        cross_groups = _parse_cross_groups(getattr(args, "cross_direction_groups", None),
                                           pack_directions)
        state, state_error = load_candidate_state(professor_dir, pack)
        if state_error:
            soft_exit("needs_refresh", state_error,
                      message="候选状态无法按机器身份精确迁移：重跑阶段 3（必要时连同阶段 2）重建 v2 状态。"
                              "未修改任何文件。")
        current_profile_fp = profile_fingerprint(args.profile)
        old_profile_fp = (state or {}).get("profile_fingerprint")
        profile_changed = bool(state) and current_profile_fp != old_profile_fp
        contract_changed = bool(state) and \
            (state or {}).get("generator_contract_version") != STAGE3_GENERATOR_CONTRACT_VERSION
        selected_keys = None
        if refresh_scope == "selected":
            if not args.selection:
                selection_path = professor_dir / SELECTION_FILE
                fail("invalid_params",
                     f"selection file unreadable without explicit --selection: {selection_path}")
            # Selected refresh is bound to the explicit professor-local Stage-4
            # container. Never fall back to the legacy program-level file.
            selected_keys = _stage3_selected_scope_keys(
                Path(args.selection), professor_dir, by_ckey)
        pack_fps = {direction_machine_id(d): d.get("input_fingerprint")
                    for d in pack_directions}
        input_fps = (state or {}).get("input_fingerprints", {})
        state_directions = {d.get("direction_id"): d
                            for d in (state or {}).get("directions", [])
                            if isinstance(d, dict)}
        state_groups = {(g.get("group_id") if isinstance(g, dict) else None): g
                        for g in (state or {}).get("cross_direction_groups", [])
                        if isinstance(g, dict)}
        correction: dict = {}
        validation_render_sha = None
        if getattr(args, "validation_file", None):
            evidence = stage3_validation_evidence(Path(args.validation_file), professor_dir, state)
            validation_render_sha = evidence["render_sha256"]
            if skip_ids:
                fail("invalid_params", "Stage-3 correction cannot skip directions")
            if cross_groups:
                fail("invalid_params", "Stage-3 correction cannot request new cross-direction groups")
            for row in stage3_correction_scopes(state, evidence):
                scope = row["scope"]
                if scope["kind"] == "direction":
                    did = scope["direction_id"]
                    current = state_directions.get(did)
                    if not current or not (
                            (current.get("stage3_status") == "ready"
                             and current.get("candidates"))
                            or (current.get("stage3_status") == "skipped"
                                and not current.get("candidates"))):
                        fail("missing_candidate_state", f"no reusable Stage-3 result for {did}")
                    if direction_id_arg and did != direction_id_arg:
                        fail("validation_scope_not_in_evidence",
                             f"--direction-id {direction_id_arg!r} is not the failed scope {did!r}")
                    if contract_changed or profile_changed \
                            or input_fps.get(did) != pack_fps.get(did):
                        soft_exit("needs_refresh", "validation_source_changed", direction_id=did)
                    correction[f"direction:{did}"] = row
                elif scope["kind"] == "group":
                    gid = scope["group_id"]
                    if gid not in state_groups or not (state_groups[gid].get("candidates") or []):
                        fail("missing_candidate_state", f"no reusable Stage-3 group result for {gid}")
                    if credential_correction and (
                            contract_changed or profile_changed
                            or not _cross_group_fresh(state_groups[gid], pack_fps,
                                                      current_profile_fp)):
                        soft_exit("needs_refresh", "validation_source_changed", group_id=gid)
                    correction[f"group:{gid}"] = row
            if direction_id_arg and f"direction:{direction_id_arg}" not in correction:
                fail("validation_scope_not_in_evidence",
                     f"direction_id {direction_id_arg!r} has no failed Stage-3 validation scope")
            for key in [k for k in correction if k.startswith("group:")]:
                gid = key.split(":", 1)[1]
                cross_groups.append({"group_id": gid,
                                     "direction_ids": list(state_groups[gid].get("direction_ids") or [])})
            if credential_correction and not correction:
                fail("validation_evidence_not_recorded",
                     "the credential correction needs a recorded round with open findings")
        # Keep every recorded direction scope in ``correction``. Only directions
        # with ready candidates are sent through generation and replacement; a
        # skipped direction stays candidate-less and is carried through unchanged.
        correction_dids = stage3_repairable_correction_directions(correction, state_directions)
        scoped_dids = set()
        for direction in pack_directions:
            did = direction_machine_id(direction)
            if getattr(args, "validation_file", None) and did not in correction_dids:
                continue
            if credential_correction:
                # r13 §5.4: the credential correction work set is exactly D — the
                # first-round refresh/selection/scope filters must not shrink it.
                scoped_dids.add(did)
                continue
            if direction_id_arg and did != direction_id_arg:
                continue
            if refresh_scope == "flagged" and direction.get("status") != "active":
                continue
            if refresh_scope == "selected" and did not in (selected_keys or set()):
                continue
            scoped_dids.add(did)

        def _direction_reusable(did: str) -> bool:
            if contract_changed:
                return False
            old = state_directions.get(did)
            return bool(
                input_fps.get(did) == pack_fps.get(did)
                and not profile_changed
                and old
                and old.get("stage3_status") == "ready"
                and old.get("candidates"))

        jobs, reuse, skipped = [], [], []
        for direction in pack_directions:
            did = direction_machine_id(direction)
            if did not in scoped_dids:
                continue
            if did in skip_ids:
                skipped.append(did)
                continue
            if _direction_reusable(did) and did not in correction_dids:
                reuse.append(did)
                continue
            gap_lines = []
            for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
                gap_lines.append({
                    "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                    "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                    "authorship": gap.get("authorship"),
                    "quote": truncate(gap.get("quote"), QUOTE_INPUT_CHARS),
                    "translation_zh": truncate(gap.get("translation_zh"), TRANSLATION_INPUT_CHARS),
                    "status": gap.get("status"), "evidence": gap.get("evidence"),
                    "completed_part": gap.get("completed_part"),
                    "remaining_gap": gap.get("remaining_gap"),
                    "confidence": gap.get("confidence"),
                    "shortlisted": gap in direction.get("gap_shortlist", [])})
            blacklist = [{"gap_id": b["gap_id"], "item_key": b["item_key"],
                          "paper_title": b.get("paper_title"),
                          "completed_by": b.get("completed_by_item_key"),
                          "evidence": b.get("evidence")}
                         for b in direction.get("completed_gap_blacklist", [])]
            mode = "refined" if direction.get("user_note") else "generated"
            jobs.append({
                "job_id": f"candidates:{pack.get('professor')}:{did}",
                "kind": "candidates",
                "direction_id": did,
                "result_file": safe_result_file("candidates", did),
                "result_schema": {"schema": 2, "kind": "candidates", "direction_id": did,
                                  "candidates": [{"id": "", "kind": "direction",
                                                  "direction_ids": [did],
                                                  "gap_refs": [{"direction_id": did,
                                                                "item_key": "", "gap_id": ""}],
                                                  "papers": [{"item_key": "",
                                                              "direction_ids": [did],
                                                              "role": "", "fit_note": ""}],
                                                  "origin": "generated|user_refined"}]},
                "model_input": {
                    "direction_id": did,
                    "mode": mode,
                    "user_note": direction.get("user_note") or "",
                    "credibility": direction.get("credibility"),
                    "red_lines": direction.get("red_lines") or [],
                    "supporting_papers": [
                        {"item_key": p["item_key"], "title": p.get("title"),
                         "year": p.get("year"), "authorship": p.get("authorship"),
                         "named_by_user": bool(p.get("named_by_user"))}
                        for p in direction_papers(pack, direction)],
                    "gaps": gap_lines,
                    "completed_gap_blacklist": blacklist,
                    "profile_text": load_profile_text(args.profile),
                    "rules": {
                        "research_question": "每个候选必须非空研究问题（求知式表述）；写不出 → 不列该候选，把要点并入主候选展开末尾（前缀「配套承诺：」）",
                        "provenance": "每条候选必须带 kind:'direction' 和 direction_ids:[本方向 direction_id]；gap_refs 每条必须是 {direction_id, item_key, gap_id} 精确三元组，且 direction_id 就是本方向；papers[] 每篇 {item_key, direction_ids:[本方向], role, fit_note}，同一论文不得重复出现",
                        "gap_anchor": "gap_refs 只能引用 model_input.gaps / completed_gap_blacklist 里的精确 (item_key,gap_id)；done_by_self 只能以【我的延伸】+difference_point 差异点方式出现；partial 候选必须写 remaining_gap 关注点；unknown 候选必须带 unverified:true",
                        "papers": "候选 papers[] 只给 {item_key, direction_ids, role, fit_note}；标题/年份/署名由 runner 从输入包回填，禁止自写标题",
                        "count": "generated 与 refined 模式都必须给 3-5 个可选候选；有用户笔记时其中恰好 1 条 origin='user_refined'（校准后的用户想法本身成为可选候选），其余为真正不同的备选",
                        "diversity": "候选之间切入点/所挂 gap 不重复",
                        "scope": "本任务只属于 direction_id 指向的这一个方向；跨方向组合不在本任务内，绝不混入 candidates[]"}}})
            row = correction.get(f"direction:{did}")
            if row is not None:
                jobs[-1]["job_id"] = f"candidates-correction:{pack.get('professor')}:{did}"
                jobs[-1]["model_input"].update({
                    "current_result": stage3_current_result(state_directions[did]),
                    "validator_issues": row["issues"],
                    "repairable_candidate_ids": row["candidate_ids"],
                    "scope": row["scope"],
                    "correction_rules": (
                        "返回完整 result；只改 validator_issues 点名的候选文字，"
                        "且只改 repairable_candidate_ids 列出的候选。"
                        "候选 ID、顺序、方向、来源、gap_refs、anchor_notes、papers 引用、fit、"
                        "红线内容与 refined 的 gap_ids 锚定属于机器事实，必须原样保留；"
                        "候选标题、一句话、研究问题、展开、贴合度说明、为何值得推、张力点、"
                        "推荐优先级与 refined 说明文字可以按清单改写。"),
                })
        # Cross-direction jobs: explicit opt-in only (issue #8 §6). No requested
        # group ⇒ no cross job, no cross model call, no cross section.
        cross_jobs = []
        for group in cross_groups:
            stale = True
            old_group = state_groups.get(group["group_id"])
            group_correction = correction.get(f"group:{group['group_id']}")
            if old_group and not contract_changed and group_correction is None \
                    and _cross_group_fresh(old_group, pack_fps, current_profile_fp) \
                    and old_group.get("candidates"):
                continue
            gap_union: dict = {}
            paper_union: dict = {}
            for pid in group["direction_ids"]:
                p_gaps, p_blacklist, p_papers = _direction_slices(pack, by_did[pid])
                for (owner, item_key, gap_id), gap in p_gaps.items():
                    row = gap_union.setdefault((item_key, gap_id),
                                               {**gap, "direction_ids": []})
                    row["direction_ids"].append(pid)
                for (owner, item_key, gap_id), banned in p_blacklist.items():
                    row = gap_union.setdefault((item_key, gap_id),
                                               {**banned, "status": "done_by_self",
                                                "direction_ids": []})
                    row["direction_ids"].append(pid)
                for item_key, paper in p_papers.items():
                    row = paper_union.setdefault(item_key, {**paper, "direction_ids": []})
                    if pid not in row["direction_ids"]:
                        row["direction_ids"].append(pid)
            cross_jobs.append({
                "job_id": f"cross:{pack.get('professor')}:{group['group_id']}",
                "kind": "cross_direction",
                "group_id": group["group_id"],
                "direction_ids": group["direction_ids"],
                "result_file": safe_result_file("candidates", group["group_id"]),
                "result_schema": {"schema": 2, "kind": "cross_candidates",
                                  "group_id": group["group_id"],
                                  "direction_ids": group["direction_ids"],
                                  "candidates": [{"id": "", "kind": "cross_direction",
                                                  "direction_ids": group["direction_ids"],
                                                  "gap_refs": [{"direction_id": "", "item_key": "",
                                                                "gap_id": ""}],
                                                  "papers": [{"item_key": "",
                                                              "direction_ids": group["direction_ids"],
                                                              "role": "", "fit_note": ""}]}]},
                "model_input": {
                    "group_id": group["group_id"],
                    "direction_ids": group["direction_ids"],
                    "directions": [{"direction_id": pid, "name_ja": by_did[pid].get("name_ja"),
                                    "name_zh": by_did[pid].get("name_zh")}
                                   for pid in group["direction_ids"]],
                    "papers": [{"item_key": p["item_key"], "title": p.get("title"),
                                "year": p.get("year"), "authorship": p.get("authorship"),
                                "direction_ids": p.get("direction_ids") or []}
                               for p in paper_union.values()],
                    "gaps": [{"gap_id": g["gap_id"], "item_key": g["item_key"],
                              "paper_title": g.get("paper_title"),
                              "paper_year": g.get("paper_year"),
                              "quote": truncate(g.get("quote"), QUOTE_INPUT_CHARS),
                              "translation_zh": truncate(g.get("translation_zh"), TRANSLATION_INPUT_CHARS),
                              "status": g.get("status"), "evidence": g.get("evidence"),
                              "completed_part": g.get("completed_part"),
                              "remaining_gap": g.get("remaining_gap"),
                              "confidence": g.get("confidence"),
                              "direction_ids": g.get("direction_ids") or []}
                             for g in gap_union.values()],
                    "profile_text": load_profile_text(args.profile),
                    "rules": {
                        "provenance": "每条候选 kind:'cross_direction'、direction_ids 必须等于本组全部参与方向（排序后）；gap_refs 每条 {direction_id, item_key, gap_id} 三元组只能引用该 direction_id 自己切片里的精确 gap；papers[] 每篇 {item_key, direction_ids, role, fit_note}，direction_ids 是真实支撑该论文的方向子集，同一论文只出现一次",
                        "grounding": "每个参与方向都必须贡献至少一条真实证据（挂它的 gap 或支撑它的论文）；只引用单方向证据的伪跨方向候选会被拒绝",
                        "count": "给 1-3 个跨方向候选；没有真正的跨方向洞察就输出更少；3-5 的常规名额只属于普通方向任务"}}})
            if group_correction is not None:
                cross_jobs[-1]["job_id"] = f"cross-correction:{pack.get('professor')}:{group['group_id']}"
                cross_jobs[-1]["model_input"].update({
                    "current_result": {"schema": 2, "kind": "cross_candidates",
                                       "group_id": group["group_id"],
                                       "direction_ids": group["direction_ids"],
                                       "candidates": (old_group or {}).get("candidates") or []},
                    "validator_issues": group_correction["issues"],
                    "repairable_candidate_ids": group_correction["candidate_ids"],
                    "scope": group_correction["scope"],
                    "correction_rules": "返回完整 result；只改 validator_issues 点名且列在 "
                                        "repairable_candidate_ids 里的跨方向候选文字，kind、"
                                        "direction_ids、gap_refs、papers 引用等机器事实原样保留。",
                })
        # r13 §5.1: after every input check passed and the plan succeeded, freeze
        # THIS invocation's parsed parameters into an exclusive credential file.
        # A capture failure fails the plan: no ok payload is emitted at all.
        invocation_result = {}
        capture_dir = getattr(args, "capture_invocation", None)
        if capture_dir:
            credential = {
                "version": STAGE3_INVOCATION_VERSION,
                "professor_dir": str(professor_dir.resolve()),
                "program_root": str(program_root.resolve()),
                "profile_path": str(Path(args.profile).resolve()) if args.profile else None,
                "profile_sha256": current_profile_fp,
                "refresh_scope": args.refresh_scope,
                "direction_id": args.direction_id,
                "collection_key": args.collection_key,
                "collection_key_direction_id": direction_id_arg,
                "skip_direction_ids_argument": args.skip_direction_ids,
                "skipped_direction_ids": list(skip_ids),
                "cross_direction_groups_argument": args.cross_direction_groups,
                "cross_direction_groups": [
                    {"group_id": g["group_id"], "direction_ids": list(g["direction_ids"])}
                    for g in cross_groups],
                "selection": str(Path(args.selection).resolve()) if args.selection else None,
            }
            file_path, file_sha = _write_stage3_invocation(capture_dir, credential)
            invocation_result = {"invocation_file": file_path,
                                 "invocation_sha256": file_sha}
        emit({
            "status": "ok",
            "professor": pack.get("professor"),
            "professor_dir": str(professor_dir),
            "refresh_scope": refresh_scope,
            "direction_id": direction_id_arg,
            "correction_scopes": sorted(correction),
            "validation_render_sha256": validation_render_sha,
            "profile_fingerprint": current_profile_fp,
            "profile_changed_reason": "profile_changed" if profile_changed else None,
            "generator_contract_version": STAGE3_GENERATOR_CONTRACT_VERSION,
            "skipped_direction_ids": skipped,
            "directions": [{"direction_id": direction_machine_id(d),
                            "collection_key": d.get("collection_key"),
                            "action": ("reuse" if direction_machine_id(d) in reuse else
                                       ("skipped" if direction_machine_id(d) in skipped
                                        else "process"))}
                           for d in pack_directions
                           if not direction_id_arg or direction_machine_id(d) == direction_id_arg],
            "cross_direction_groups": [{"group_id": g["group_id"],
                                         "direction_ids": g["direction_ids"],
                                         "action": "process"}
                                        for g in cross_groups],
            "jobs": jobs + cross_jobs,
            "write_needed": bool(jobs + cross_jobs),
            **invocation_result,
        })

    def cmd_stage3_finalize(args) -> None:
        invocation = _read_stage3_invocation(args)
        if invocation is None and not getattr(args, "professor_dir", None):
            fail("invalid_params",
                 "stage3-finalize needs --professor-dir or an invocation credential "
                 "(--invocation-file + --invocation-sha256)")
        credential_correction = invocation is not None and \
            bool(getattr(args, "validation_file", None))
        if invocation is not None:
            _require_invocation_source(invocation)
            args = _stage3_args_from_invocation(args, invocation,
                                                correction=credential_correction)
        professor_dir = Path(args.professor_dir)
        program_root = Path(args.program_root) if args.program_root else professor_dir.parent.parent
        require_professor_dir_under_program(professor_dir, program_root)
        pack, pack_error = load_input_pack(professor_dir)
        if pack is None:
            soft_exit("needs_refresh", "missing_input_pack", pack_path=str(professor_dir / INPUT_PACK))
        pack_directions = pack.get("directions") or []
        by_did = {direction_machine_id(d): d for d in pack_directions}
        by_ckey = {}
        for d in pack_directions:
            ckey = d.get("collection_key")
            if isinstance(ckey, str) and ckey.strip() and ckey not in by_ckey:
                by_ckey[ckey] = d
            elif isinstance(ckey, str) and ckey.strip():
                by_ckey[ckey] = None
        direction_id_arg = getattr(args, "direction_id", None)
        collection_key_arg = getattr(args, "collection_key", None)
        if collection_key_arg and not direction_id_arg:
            resolved = by_ckey.get(collection_key_arg)
            if resolved is None:
                fail("invalid_params",
                     f"collection_key not found (or ambiguous) in input pack: {collection_key_arg}")
            direction_id_arg = direction_machine_id(resolved)
        if direction_id_arg and direction_id_arg not in by_did:
            fail("invalid_params", f"direction_id not found in input pack: {direction_id_arg}")
        if collection_key_arg and direction_id_arg:
            resolved = by_ckey.get(collection_key_arg)
            if resolved is None or direction_machine_id(resolved) != direction_id_arg:
                fail("invalid_params",
                     f"collection_key {collection_key_arg!r} and direction_id {direction_id_arg!r} "
                     "resolve to different directions")
        skip_ids = _parse_direction_id_list(getattr(args, "skip_direction_ids", None),
                                            "skip_direction_ids")
        unknown_skip = [d for d in skip_ids if d not in by_did]
        if unknown_skip:
            fail("invalid_params", f"skip_direction_ids outside input pack: {unknown_skip}")
        cross_groups = _parse_cross_groups(getattr(args, "cross_direction_groups", None),
                                           pack_directions)
        refresh_scope = args.refresh_scope or "flagged"
        state, state_error = load_candidate_state(professor_dir, pack)
        if state_error:
            soft_exit("needs_refresh", state_error,
                      message="候选状态无法按机器身份精确迁移：重跑阶段 3（必要时连同阶段 2）重建 v2 状态。"
                              "未修改任何文件。")
        current_profile_fp = profile_fingerprint(args.profile)
        old_profile_fp = (state or {}).get("profile_fingerprint")
        profile_changed = bool(state) and current_profile_fp != old_profile_fp
        contract_changed = bool(state) and \
            (state or {}).get("generator_contract_version") != STAGE3_GENERATOR_CONTRACT_VERSION
        if getattr(args, "validation_file", None) and profile_changed:
            # r13 §5.5-5: correction prose never rebinds the recorded profile.
            soft_exit("needs_refresh", "validation_source_changed")
        old_directions = {d.get("direction_id"): d
                          for d in (state or {}).get("directions", []) if isinstance(d, dict)}
        old_group_list = [g for g in (state or {}).get("cross_direction_groups", [])
                          if isinstance(g, dict)]
        old_groups = {(g.get("group_id") if isinstance(g, dict) else None): g
                      for g in old_group_list}
        old_fps = (state or {}).get("input_fingerprints", {})
        pack_fps = {direction_machine_id(d): d.get("input_fingerprint")
                    for d in pack_directions}
        correction: dict = {}
        if getattr(args, "validation_file", None):
            if skip_ids or cross_groups:
                fail("invalid_params", "Stage-3 correction cannot skip or request cross-direction groups")
            evidence = stage3_validation_evidence(Path(args.validation_file), professor_dir, state)
            for row in stage3_correction_scopes(state, evidence):
                scope = row["scope"]
                if scope["kind"] == "direction":
                    did = scope["direction_id"]
                    current = old_directions.get(did)
                    if not current or not (
                            (current.get("stage3_status") == "ready"
                             and current.get("candidates"))
                            or (current.get("stage3_status") == "skipped"
                                and not current.get("candidates"))):
                        fail("missing_candidate_state", f"no reusable Stage-3 result for {did}")
                    if direction_id_arg and did != direction_id_arg:
                        fail("validation_scope_not_in_evidence",
                             f"--direction-id {direction_id_arg!r} is not the failed scope {did!r}")
                    if contract_changed or profile_changed or old_fps.get(did) != pack_fps.get(did):
                        soft_exit("needs_refresh", "validation_source_changed", direction_id=did)
                    correction[f"direction:{did}"] = row
                elif scope["kind"] == "group":
                    gid = scope["group_id"]
                    if gid not in old_groups or not (old_groups[gid].get("candidates") or []):
                        fail("missing_candidate_state", f"no reusable Stage-3 group result for {gid}")
                    if credential_correction and (
                            contract_changed or profile_changed
                            or not _cross_group_fresh(old_groups[gid], pack_fps,
                                                      current_profile_fp)):
                        soft_exit("needs_refresh", "validation_source_changed", group_id=gid)
                    correction[f"group:{gid}"] = row
            if direction_id_arg and f"direction:{direction_id_arg}" not in correction:
                fail("validation_scope_not_in_evidence",
                     f"direction_id {direction_id_arg!r} has no failed Stage-3 validation scope")
            for key in [k for k in correction if k.startswith("group:")]:
                gid = key.split(":", 1)[1]
                cross_groups.append({"group_id": gid,
                                     "direction_ids": list(old_groups[gid].get("direction_ids") or [])})
            if credential_correction and not correction:
                fail("validation_evidence_not_recorded",
                     "the credential correction needs a recorded round with open findings")
        # Only ready, candidate-bearing scopes are replaced. Recorded skipped
        # scopes remain authoritative but stay outside the correction work set.
        correction_dids = stage3_repairable_correction_directions(correction, old_directions)
        selected_keys = None
        if refresh_scope == "selected":
            if not args.selection:
                selection_path = professor_dir / SELECTION_FILE
                fail("invalid_params",
                     f"selection file unreadable without explicit --selection: {selection_path}")
            # Plan and finalize consume the same explicit professor-local selection.
            selected_keys = _stage3_selected_scope_keys(
                Path(args.selection), professor_dir, by_ckey)
        results_dir = Path(args.results)
        decision = None
        if getattr(args, "decision_file", None):
            decision_data, derr = read_json_file(Path(args.decision_file))
            if derr is None and isinstance(decision_data, dict):
                decision = decision_data.get("decision")
        professor = pack.get("professor")
        category = professor_dir.parent.name
        scoped_dids = set()
        for direction in pack_directions:
            did = direction_machine_id(direction)
            if getattr(args, "validation_file", None) and did not in correction_dids:
                continue
            if credential_correction:
                # r13 §5.4: the credential correction work set is exactly D — the
                # first-round refresh/selection/scope filters must not shrink it.
                scoped_dids.add(did)
                continue
            if direction_id_arg and did != direction_id_arg:
                continue
            if refresh_scope == "flagged" and direction.get("status") != "active":
                continue
            if refresh_scope == "selected" and did not in (selected_keys or set()):
                continue
            scoped_dids.add(did)
        updated_directions, reused, skipped_out = [], [], []
        processed_scopes = set()
        for direction in pack_directions:
            did = direction_machine_id(direction)
            if did not in scoped_dids:
                old = old_directions.get(did)
                if old:
                    # A scoped refresh replaces only the selected directions; the
                    # other accepted directions stay in the machine state + render.
                    updated_directions.append(old)
                continue
            old_direction = old_directions.get(did)
            if did in skip_ids:
                # Explicit skip is persisted state (issue #8 §4.2): visible,
                # candidate-less, and distinct from "never processed". A later run
                # without the skip processes the direction normally (empty
                # candidates never satisfy the reuse gate).
                skipped_out.append(did)
                updated_directions.append({
                    "direction_id": did,
                    "name_ja": direction.get("name_ja"),
                    "name_zh": direction.get("name_zh"),
                    "status": direction.get("status"),
                    "stage3_status": "skipped",
                    "candidates": [], "mode": None, "refined": None, "priority": "",
                    "credibility": direction.get("credibility"),
                    "red_lines": direction.get("red_lines") or [],
                    "user_note_present": bool(direction.get("user_note")),
                })
                continue
            if old_direction and did not in correction_dids and not contract_changed \
                    and not profile_changed \
                    and old_fps.get(did) == pack_fps.get(did) \
                    and old_direction.get("stage3_status") == "ready" \
                    and old_direction.get("candidates"):
                reused.append(did)
                # Display names/status are pack projections, not cached evidence:
                # sync them so a display-only rename re-renders deterministically
                # without any idea model call (issue #8 §4.4).
                for field in ("name_ja", "name_zh", "status"):
                    old_direction[field] = direction.get(field)
                updated_directions.append(old_direction)
                continue
            result_path = results_dir / safe_result_file("candidates", did)
            processed_scopes.add(f"direction:{did}")
            data, rerror = read_json_file(result_path)
            if rerror:
                fail("result_missing", f"{result_path}: {rerror}")
            checked = validate_candidate_result(pack, direction, data, result_path)
            row = correction.get(f"direction:{did}")
            if row is not None:
                require_stage3_correction_invariants(old_direction, checked, result_path,
                                                     row["candidate_ids"])
            checked["name_ja"] = direction.get("name_ja")
            checked["name_zh"] = direction.get("name_zh")
            checked["credibility"] = direction.get("credibility")
            checked["red_lines"] = direction.get("red_lines") or []
            checked["status"] = direction.get("status")
            checked["user_note_present"] = bool(direction.get("user_note"))
            checked["stage3_status"] = "ready"
            updated_directions.append(checked)
        # Cross-direction groups: only EXPLICITLY requested groups exist (issue #8
        # §6). A group survives when its recorded participant fingerprints + profile
        # still match; otherwise it needs the result file its plan job pointed at.
        # Plain generation still drops earlier groups that are no longer requested
        # and reports them — never silently keeps them. A correction (credential or
        # explicit) instead replaces in place inside the OLD group list and
        # preserves every uninvolved group: an unrequested group is never a
        # removal request (r13 §5.5).
        final_groups, dropped_groups = [], []
        for group in cross_groups:
            old_group = old_groups.get(group["group_id"])
            group_row = correction.get(f"group:{group['group_id']}")
            if old_group and group_row is None and not contract_changed \
                    and _cross_group_fresh(old_group, pack_fps, current_profile_fp) \
                    and old_group.get("candidates"):
                final_groups.append(old_group)
                continue
            result_path = results_dir / safe_result_file("candidates", group["group_id"])
            processed_scopes.add(f"group:{group['group_id']}")
            data, rerror = read_json_file(result_path)
            if rerror:
                fail("result_missing", f"{result_path}: {rerror}")
            checked = validate_cross_result(pack, group, data, result_path)
            if group_row is not None:
                require_stage3_correction_invariants(
                    old_group, {"candidates": checked["candidates"]}, result_path,
                    group_row["candidate_ids"])
            final_groups.append({
                "group_id": group["group_id"],
                "direction_ids": list(group["direction_ids"]),
                # r13 §5.5-5: correction prose never rebinds a group's recorded
                # source fingerprints; only a real (re)generation does.
                "direction_fingerprints": (
                    old_group.get("direction_fingerprints") if group_row is not None
                    else {pid: pack_fps.get(pid) for pid in group["direction_ids"]}),
                "profile_fingerprint": (
                    old_group.get("profile_fingerprint") if group_row is not None
                    else current_profile_fp),
                "candidates": checked["candidates"],
            })
        requested_ids = {g["group_id"] for g in cross_groups}
        if correction:
            # r13 §5.5-2/3: the identity set and the list order stay exactly as
            # before; each old group is either replaced in place or kept as-is.
            kept = {g["group_id"]: g for g in final_groups}
            final_groups = [kept.get(g.get("group_id"), g) for g in old_group_list]
        else:
            for group_id, group in old_groups.items():
                if group_id in requested_ids:
                    continue
                dropped_groups.append({"group_id": group_id,
                                       "direction_ids": group.get("direction_ids") or [],
                                       "reason": "group_not_requested"})
        all_group_candidates = [c for g in final_groups for c in g.get("candidates") or []]
        cross_ids = [c.get("id") for c in all_group_candidates]
        if len(set(cross_ids)) != len(cross_ids):
            fail("duplicate_idea_id", f"cross-direction idea ids not unique: {cross_ids}")
        if not updated_directions and not reused and not final_groups:
            fail("validation_failed", "no in-scope directions or groups to write")
        md_entries = []
        for entry in updated_directions:
            clone = dict(entry)
            clone["_pack_papers"] = []
            pack_direction = by_did.get(entry.get("direction_id"))
            if pack_direction is not None:
                for paper in direction_papers(pack, pack_direction):
                    item = dict(paper)
                    if item.get("analysis_file"):
                        item["_analysis_rel"] = rel_path(Path(item["analysis_file"]), professor_dir)
                    clone["_pack_papers"].append(item)
            md_entries.append(clone)
        cross_md_groups = []
        for group in final_groups:
            clone = dict(group)
            clone["_pack_papers"] = []
            seen_keys = set()
            participants = []
            for pid in group.get("direction_ids") or []:
                pack_direction = by_did.get(pid) or {}
                participants.append({"direction_id": pid,
                                     "name_ja": pack_direction.get("name_ja") or pid})
                for paper in direction_papers(pack, pack_direction):
                    if paper["item_key"] in seen_keys:
                        continue
                    seen_keys.add(paper["item_key"])
                    item = dict(paper)
                    if item.get("analysis_file"):
                        item["_analysis_rel"] = rel_path(Path(item["analysis_file"]), professor_dir)
                    clone["_pack_papers"].append(item)
            clone["_participants"] = participants
            # The 参与方向 label is rendered per candidate from the group's roster.
            clone["candidates"] = [dict(c, _participants=participants)
                                   for c in clone.get("candidates") or []]
            cross_md_groups.append(clone)
        if correction:
            # r13 §5.5-2: objects outside the correction work set keep their
            # recorded source fingerprints — correction prose never re-binds them.
            input_fps = {did: (pack_fps.get(did) if did in scoped_dids
                               else old_fps.get(did, pack_fps.get(did)))
                         for did in pack_fps}
        else:
            input_fps = dict(pack_fps)
        state_fingerprint = sha256_obj({"professor": professor, "directions": input_fps,
                                        "profile": current_profile_fp})
        md_path = professor_dir / CANDIDATES_MD
        old_render = ((state or {}).get("cache") or {}).get("render", {})
        body = render_candidates_md(professor, category, md_entries,
                                    current_profile_fp, state_fingerprint, professor_dir,
                                    cross_groups=cross_md_groups)
        md_conflict = managed_conflict(
            md_path, body, old_render.get(CANDIDATES_MD, {}).get("sha256"), decision)
        if md_conflict:
            soft_exit("needs_decision", md_conflict["reason_code"], target=md_conflict.get("target"),
                      options=["overwrite", "keep_manual", "promote"])
        body_sha = sha256_text(body)
        new_state = {
            "schema": CANDIDATE_STATE_SCHEMA, "kind": CANDIDATE_STATE_KIND,
            "identity_version": DIRECTION_IDENTITY_VERSION,
            "generator_contract_version": STAGE3_GENERATOR_CONTRACT_VERSION,
            "managed_by": MANAGED_BY, "generated_at": now_utc(),
            "professor": professor,
            "profile_fingerprint": current_profile_fp,
            "profile_path": args.profile,
            "input_fingerprints": input_fps,
            "directions": updated_directions,
            "cross_direction_groups": final_groups,
            "cache": {"render": {CANDIDATES_MD: {"sha256": body_sha}}},
        }
        if isinstance((state or {}).get("validator"), dict):
            retained = carry_stage3_validator(
                state["validator"], processed_scopes,
                correction=bool(correction), render_sha=body_sha)
            if retained:
                new_state["validator"] = retained
        # Local transaction (issue #66 r10 §2): stage both files, install the
        # local Markdown first, and install the candidate state LAST — the state
        # replace is the only business commit point. The program level is NOT part
        # of this transaction: finalize never reads or writes 套磁想法候选总览.md /
        # _contact_projections.json, so another professor's state, a stale or
        # missing overview, or a corrupt projection registry can never block or
        # re-judge this commit. The derived overview is rebuilt from committed
        # states by `stage3-rebuild-overview` after terminal validation.
        state_path = professor_dir / CANDIDATE_STATE
        try:
            staged_pair_commit([
                (md_path, render_frontmatter(state_fingerprint, body_sha) + body),
                (state_path, json.dumps(new_state, ensure_ascii=False, sort_keys=True,
                                        indent=1) + "\n"),
            ])
        except Exception as exc:
            fail("local_pair_commit_failed", str(exc), target=str(state_path))
        emit({
            "status": "ok", "professor": professor,
            "state_path": str(professor_dir / CANDIDATE_STATE),
            "candidates_md": str(md_path),
            "overview_md": str(program_root / "教授研究" / CANDIDATES_OVERVIEW),
            "directions": [{"direction_id": d.get("direction_id"),
                            "stage3_status": d.get("stage3_status"),
                            "mode": d.get("mode"),
                            "candidates": len(d.get("candidates") or [])}
                           for d in updated_directions],
            "skipped_direction_ids": skipped_out,
            # r13 §5.5: the reported correction set is what this run actually
            # replaced — never a scope the admission filters kept out.
            "corrected": sorted(correction_dids & scoped_dids),
            "corrected_groups": sorted(key.split(":", 1)[1] for key in correction
                                       if key.startswith("group:")),
            "cross_direction_groups": [{"group_id": g["group_id"],
                                         "direction_ids": g["direction_ids"],
                                         "candidates": len(g.get("candidates") or [])}
                                        for g in final_groups],
            "dropped_cross_direction": dropped_groups,
            "reused": reused, "md_sha256": body_sha,
        })

    def cmd_stage3_rebuild_overview(args) -> None:
        """Rebuild the program-level candidates overview from committed states.

        The overview is a human-facing projection derived ONLY from committed
        professor-local candidate states (issue #66 r10 §3): the local Markdown
        contributes a link path and never machine facts; `_contact_projections.json`
        is not read and not written; manual-edit protection is projection-local
        (frontmatter render_sha256 must match the current body, otherwise the
        rebuild fails closed with manual_markdown_changed and nothing changes).
        Any discovered state that is malformed or cannot be exactly identity-
        migrated fails the whole rebuild BEFORE the overview write — no partial
        overview is ever published.
        """
        program_root = Path(args.program_root)
        research_root = (program_root / "教授研究").resolve()
        if not research_root.is_dir():
            fail("invalid_params", f"program_root has no 教授研究 directory: {program_root}")
        discovered: dict[str, Path] = {}
        for state_path in sorted(research_root.rglob(CANDIDATE_STATE)):
            try:
                parent = state_path.parent.resolve()
                relative = parent.relative_to(research_root)
            except (OSError, ValueError):
                fail("state_outside_program_root", str(state_path),
                     message="discovered candidate state resolves outside the 教授研究 root")
            discovered.setdefault(relative.as_posix(), parent)
        records = []
        for identity in sorted(discovered):
            professor_dir = discovered[identity]
            state, state_error = strict_candidate_state(professor_dir)
            if state is None and state_error is None:
                # The state vanished between discovery and read: this professor
                # currently has no committed state and contributes no rows.
                continue
            if state_error:
                fail(state_error,
                     "candidate state cannot be included in the program overview",
                     professor_identity=identity, professor_dir=str(professor_dir))
            records.append((identity, professor_dir, state))
        direction_entries, cross_entries = [], []
        for identity, professor_dir, state in records:
            display = state.get("professor") or identity
            md_rel = rel_path(professor_dir / CANDIDATES_MD, research_root)
            for row in sorted((state.get("directions") or []),
                              key=lambda item: str(item.get("direction_id") or "")):
                direction_entries.append({
                    "professor": display, "name_ja": row.get("name_ja"),
                    "candidates": row.get("candidates") or [],
                    "priority": row.get("priority"),
                    "_candidates_md_rel": md_rel})
            for row in sorted((state.get("cross_direction_groups") or []),
                              key=lambda item: str(item.get("group_id") or "")):
                cross_entries.append({
                    "professor": display, "group_id": row.get("group_id"),
                    "direction_ids": row.get("direction_ids") or [],
                    "candidates": row.get("candidates") or [],
                    "_candidates_md_rel": md_rel})
        body = render_candidates_overview(direction_entries, research_root,
                                          cross_groups=cross_entries)
        overview_path = research_root / CANDIDATES_OVERVIEW
        if overview_path.is_file():
            try:
                existing_text = overview_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                fail("overview_unreadable", str(exc), target=str(overview_path))
            header, existing_body = split_frontmatter(existing_text)
            if not isinstance(header, dict) or header.get("managed_by") != MANAGED_BY or \
                    header.get("render_sha256") != sha256_text(existing_body):
                soft_exit("needs_decision", "manual_markdown_changed",
                          target=str(overview_path))
        body_sha = sha256_text(body)
        projection_fingerprint = sha256_obj({"projection": CANDIDATES_OVERVIEW,
                                             "body": body_sha})
        try:
            atomic_write(overview_path,
                         render_frontmatter(projection_fingerprint, body_sha) + body)
        except Exception as exc:
            fail("overview_write_failed", str(exc), target=str(overview_path))
        emit({
            "status": "ok",
            "overview_md": str(overview_path),
            "sha256": body_sha,
            "professor_count": len(records),
            "direction_rows": len(direction_entries),
            "cross_direction_rows": len(cross_entries),
            "professors": [{"professor_identity": identity,
                            "professor": state.get("professor"),
                            "directions": len(state.get("directions") or []),
                            "cross_direction_groups":
                                len(state.get("cross_direction_groups") or [])}
                           for identity, _, state in records],
        })

    return types.SimpleNamespace(
                _stage3_selected_scope_keys=_stage3_selected_scope_keys,
                cmd_stage3_plan=cmd_stage3_plan,
                cmd_stage3_finalize=cmd_stage3_finalize,
                cmd_stage3_rebuild_overview=cmd_stage3_rebuild_overview,
    )
