#!/usr/bin/env python3
"""Stage-4 helper module for ``contact_state.py``.

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
import sys
import types





def build(*, atomic_json_many,
          emit,
          ProfessorBusinessFailure,
          professor_business_channel,
          fail,
          soft_exit,
          contact_evidence_snapshot,
          load_contact_evidence,
          MANAGED_BY,
          STAGE4_LOCAL_SCHEMA,
          DIRECTION_IDENTITY_VERSION,
          SELECTION_KIND,
          EMAIL_PACK_KIND,
          EMAIL_PACK,
          SELECTION_FILE,
          now_utc,
          read_json_file,
          professor_dir_containment_error,
          direction_machine_id,
          load_input_pack,
          load_candidate_state,
          profile_fingerprint,
          compile_email_entry,
          validate_papers_override,
          _selection_direction_ids,
          canonical_professor_dir,
          STAGE4_MIGRATION_COMMITTED):
    def _stage4_cross_group(pack: dict, group_entry: dict) -> list[dict] | None:
        """Resolve a cross-direction group's participants against the CURRENT pack.

        Returns the participant pack directions in the group's recorded
        direction_ids order, or None when anything fails to exact-join (unknown
        direction id, changed fingerprint, malformed bookkeeping) — the caller
        fails closed with needs_refresh instead of compiling a stale email."""
        direction_ids = group_entry.get("direction_ids")
        recorded = group_entry.get("direction_fingerprints")
        if not isinstance(direction_ids, list) or len(set(direction_ids)) < 2 \
                or not isinstance(recorded, dict) or not recorded:
            return None
        by_id = {direction_machine_id(d): d for d in pack.get("directions") or []}
        participants = []
        for direction_id in direction_ids:
            pack_direction = by_id.get(direction_id)
            if pack_direction is None \
                    or recorded.get(direction_id) != pack_direction.get("input_fingerprint"):
                return None
            participants.append(pack_direction)
        return participants

    def validate_stage4_selections(selects: Any, states: dict, packs: dict) -> None:
        """Validate the complete selection batch before any formal file is written."""
        if not isinstance(selects, list) or not selects:
            fail("invalid_params", "selection input has no selections")
        seen_scopes = set()
        seen_email_ids = set()
        for index, select in enumerate(selects):
            if not isinstance(select, dict):
                fail("invalid_selection", f"selection[{index}] must be an object")
            professor = select.get("professor")
            professor_dir = Path(select.get("professor_dir") or "")
            if not isinstance(professor, str) or not professor.strip() or not professor_dir.is_dir():
                fail("invalid_selection", f"selection[{index}] is missing professor or professor_dir")
            direction_ids, identity_error = _selection_direction_ids(select, packs)
            if identity_error or not direction_ids:
                fail("legacy_direction_identity",
                     f"selection[{index}] ({professor}) cannot be mapped to canonical direction_ids "
                     "through an exact machine relation; re-run stage 3 for this professor")
            # The duplicate scope is formal identity: canonical professor_dir plus the
            # machine-normalized direction set. Display text can never split or merge
            # a scope, so rewriting it cannot bypass this check (issue #67 R67-G1-9).
            scope_key = (canonical_professor_dir(select.get("professor_dir")),
                         tuple(direction_ids))
            if scope_key in seen_scopes:
                fail("duplicate_selection",
                     f"duplicate professor+direction-scope selection: {professor}::{'+'.join(direction_ids)}")
            seen_scopes.add(scope_key)
            state = states.get(str(professor_dir))
            pack = packs.get(str(professor_dir))
            state_direction = next((d for d in (state or {}).get("directions", [])
                                    if d.get("direction_id") in direction_ids), None) \
                if len(direction_ids) == 1 else None
            pack_direction = next((d for d in (pack or {}).get("directions", [])
                                   if direction_machine_id(d) in direction_ids), None) \
                if len(direction_ids) == 1 else None
            if len(direction_ids) == 1 and not (state_direction and pack_direction):
                continue
            candidates = {idea.get("id"): idea for idea in (state_direction or {}).get("candidates", [])}
            # Explicit cross-direction ideas live in their own groups: look the id
            # up in the group whose sorted direction_ids match this selection scope.
            cross_by_id = {}
            if len(direction_ids) >= 2:
                for group in (state or {}).get("cross_direction_groups") or []:
                    if isinstance(group, dict) \
                            and sorted(group.get("direction_ids") or []) == direction_ids:
                        cross_by_id = {entry.get("id"): entry
                                       for entry in group.get("candidates") or []}
            ideas = select.get("ideas")
            if not isinstance(ideas, list):
                fail("invalid_selection",
                     f"{professor}::{'+'.join(direction_ids)}: ideas must be a list")
            seen_ideas = set()
            for idea_index, idea_input in enumerate(ideas):
                if not isinstance(idea_input, dict):
                    fail("invalid_selection",
                         f"{professor}::{'+'.join(direction_ids)}: ideas[{idea_index}] must be an object")
                idea_id = idea_input.get("id")
                if idea_id in seen_ideas:
                    fail("duplicate_idea_id",
                         f"duplicate idea id in {professor}::{'+'.join(direction_ids)}: {idea_id}")
                seen_ideas.add(idea_id)
                idea = candidates.get(idea_id)
                if idea is None and idea_id in cross_by_id:
                    idea = cross_by_id[idea_id]
                if idea is None:
                    # An explicit selection that matches nothing must fail the whole
                    # batch up front: silently skipping it would write the remaining
                    # ideas while the user believes this one was selected too.
                    fail("unknown_idea_id",
                         f"{professor}::{'+'.join(direction_ids)}: unknown idea id: {idea_id}")
                override = validate_papers_override(
                    idea, idea_input.get("papers_override"),
                    f"{professor}::{'+'.join(direction_ids)}::{idea_id}")
                email_id = f"{professor}::{'+'.join(direction_ids)}::{idea_id}"
                if email_id in seen_email_ids:
                    fail("duplicate_email_id", f"duplicate email id: {email_id}")
                seen_email_ids.add(email_id)

    def stage4_local_pair_paths(professor_dir: Path) -> tuple[Path, Path]:
        """The professor-local Stage-4 pair owned by one canonical professor_dir."""
        return (Path(professor_dir) / SELECTION_FILE, Path(professor_dir) / EMAIL_PACK)

    def stage4_professor_row(professor: Any, professor_dir: Any, status: str,
                             reason_code: str | None = None, **extra) -> dict:
        row = {"professor": professor, "professor_dir": str(professor_dir or ""),
               "status": status, "reason_code": reason_code,
               "selection_file": None, "email_pack": None}
        row.update(extra)
        return row

    def _stage4_failure_row(row: dict, payload: dict) -> dict:
        """Turn one expected business payload into that professor's failed row.

        A failed row keeps selection_file/email_pack null: nothing was committed, and
        a caller must not mistake a diagnostic path for written authority."""
        failed = dict(row)
        failed["status"] = payload.get("status") or "error"
        for key, value in payload.items():
            if key not in ("professor", "professor_dir"):
                failed[key] = value
        failed["selection_file"] = None
        failed["email_pack"] = None
        return failed

    def _stage4_professor_commit(program_root: Path, professor_dir: Path, selects: list,
                                 current_profile_fp: str | None, evidence: tuple,
                                 row: dict) -> dict:
        """Run the whole Stage-4 transaction for ONE canonical professor_dir.

        Only this professor's candidate state, input pack and professor-local prior
        selection are read: an unrelated professor is never a prerequisite (issue #67
        R67-G1-2). Inside this professor nothing is relaxed — the same exact identity,
        fingerprint, gap-join and papers_override validation still fails the whole
        professor through one pair-atomic write (R67-G1-3)."""
        professor = row.get("professor")
        if not str(professor_dir):
            fail("invalid_selection", "该条目没有 professor_dir，无法建立教授事务边界。")
        containment = professor_dir_containment_error(professor_dir, program_root)
        if containment:
            fail(containment, "越界 professor_dir：该教授零本地写入、零外部写入。",
                 allowed_root=str((program_root / "教授研究").resolve()))
        selection_path, email_pack_path = stage4_local_pair_paths(professor_dir)
        # A half-present local pair is a corrupt authority: never guess which file to
        # trust and never mint the missing counterpart.
        if selection_path.exists() != email_pack_path.exists():
            fail("local_pair_incomplete",
                 f"professor-local Stage-4 pair is half-present in {professor_dir}; "
                 "resolve the pair before finalizing instead of guessing which half is authority")
        canonical = canonical_professor_dir(professor_dir)
        professor_pack, _pack_error = load_input_pack(professor_dir)
        professor_state, state_error = load_candidate_state(professor_dir, professor_pack)
        if professor_state is None and state_error:
            soft_exit("needs_refresh", state_error,
                      message="候选状态无法按机器身份精确迁移：重跑阶段 3 重建 v2 状态。该教授未写入任何文件。")
        packs: dict = {}
        states: dict = {}
        for key in {str(select.get("professor_dir") or "") for select in selects} | {str(professor_dir)}:
            if key:
                packs[key] = professor_pack
                states[key] = professor_state

        prior_selection, prior_error = read_json_file(selection_path)
        if prior_error not in (None, "not_found"):
            fail("invalid_selection", f"existing local selection unreadable: {selection_path}: {prior_error}")
        if prior_selection is not None and not isinstance(prior_selection, dict):
            fail("invalid_selection", f"existing local selection must be an object: {selection_path}")
        prior_rows = (prior_selection or {}).get("selections") or []
        if not isinstance(prior_rows, list):
            fail("invalid_selection", f"existing local selection.selections must be a list: {selection_path}")
        for index, old in enumerate(prior_rows):
            if not isinstance(old, dict):
                # A non-object entry in the professor-local prior selection is a
                # corrupt authority: fail closed without rewriting the pair, never
                # silently drop the entry (R67-G1-3).
                fail("invalid_selection",
                     f"existing local selection contains a non-object entry at "
                     f"index {index}: {selection_path}")
            if canonical_professor_dir(old.get("professor_dir")) != canonical:
                fail("local_selection_foreign_row",
                     f"existing local selection in {professor_dir} carries a row bound to "
                     f"{old.get('professor_dir')}; a professor-local container may not hold "
                     "another professor's selection")
            key = str(old.get("professor_dir") or "")
            if key:
                packs.setdefault(key, professor_pack)
                states.setdefault(key, professor_state)

        resolved_selects = []
        for select in selects:
            ids, identity_error = _selection_direction_ids(select, packs)
            if identity_error or not ids:
                fail("legacy_direction_identity",
                     f"selection for {select.get('professor')} cannot be mapped to canonical "
                     "direction_ids through an exact machine relation; re-run stage 3 for this "
                     "professor. This professor wrote no file.")
            resolved_selects.append({**select, "direction_ids": ids})
        # The container already fixes the professor: inside one canonical
        # professor_dir the scope is only the direction set, so a display-name change
        # neither preserves a stale row nor splits one scope into two (issue #67).
        current_scope = {tuple(s.get("direction_ids") or [])
                         for s in resolved_selects}
        # Same-professor preserved directions are recompiled into the same local pair,
        # so they share this professor's fail-closed outcome instead of being dropped.
        preserved = []
        for old in prior_rows:
            if not isinstance(old, dict):
                continue
            ids, identity_error = _selection_direction_ids(old, packs)
            if ids and tuple(ids) in current_scope:
                continue
            if identity_error or not ids:
                fail("legacy_direction_identity",
                     f"existing local selection entry for {old.get('professor')} cannot be mapped "
                     "to canonical direction_ids through an exact machine relation; re-run stage 3 "
                     "for this professor. This professor wrote no file.")
            if professor_state is None:
                soft_exit("needs_refresh", "candidate_state_missing",
                          direction_ids=ids,
                          message="既有选择对应的候选状态缺失：先重跑阶段 3，再重新选择。该教授未写入任何选择/邮件包。")
            preserved.append({**old, "direction_ids": ids})

        all_selects = preserved + resolved_selects
        preserved_keys = {tuple(p.get("direction_ids") or [])
                          for p in preserved}
        skipped = []

        def record_skip(select_obj: dict, entry: dict) -> None:
            if tuple(select_obj.get("direction_ids") or []) in preserved_keys:
                soft_exit("needs_refresh", "preserved_selection_uncompilable",
                          direction_ids=select_obj.get("direction_ids"),
                          message="既有选择无法按当前候选状态/输入包重编译：先重跑阶段 3，再重新选择。该教授未写入任何选择/邮件包。")
            skipped.append(entry)

        validate_stage4_selections(all_selects, states, packs)
        written_selections = []
        email_entries = []
        evidence_artifact, evidence_error = evidence
        evidence_snapshot = contact_evidence_snapshot(evidence_artifact, evidence_error, professor)
        for select in all_selects:
            select_dir = Path(select.get("professor_dir") or "")
            direction_ids = select.get("direction_ids") or []
            scope = "+".join(direction_ids)
            if not select_dir.is_dir() or not direction_ids:
                record_skip(select, {"professor": professor, "reason": "invalid_selection_input"})
                continue
            state = states.get(str(select_dir))
            pack = packs.get(str(select_dir))
            if state is None:
                record_skip(select, {"professor": professor, "direction_ids": direction_ids,
                                     "reason": "needs_stage3", "detail": "缺 套磁候选状态.json"})
                continue
            if pack is None:
                record_skip(select, {"professor": professor, "direction_ids": direction_ids,
                                     "reason": "needs_refresh", "detail": "missing_input_pack"})
                continue
            if len(direction_ids) == 1:
                pack_direction = next((d for d in pack.get("directions", [])
                                       if direction_machine_id(d) == direction_ids[0]), None)
                state_direction = next((d for d in state.get("directions", [])
                                        if d.get("direction_id") == direction_ids[0]), None)
                if not pack_direction or not state_direction:
                    record_skip(select, {"professor": professor, "direction_ids": direction_ids,
                                         "reason": "needs_refresh",
                                         "detail": "direction not in state/pack"})
                    continue
                if state.get("input_fingerprints", {}).get(direction_ids[0]) != \
                        pack_direction.get("input_fingerprint"):
                    soft_exit("needs_refresh", "source_fingerprint_changed",
                              direction_id=direction_ids[0],
                              message="输入包已变化：先重跑阶段 3 刷新候选，再重新选择。该教授未写入任何选择/邮件包。")
                if state.get("profile_fingerprint") != current_profile_fp:
                    soft_exit("needs_refresh", "profile_changed",
                              direction_id=direction_ids[0],
                              message="profile 已变化：重跑阶段 3 后再选择。该教授未写入任何选择/邮件包。")
            else:
                pack_direction = next((d for d in pack.get("directions", [])
                                       if direction_machine_id(d) == direction_ids[0]), None)
                state_direction = None
                if pack_direction is None:
                    record_skip(select, {"professor": professor, "direction_ids": direction_ids,
                                         "reason": "needs_refresh", "detail": "direction not in pack"})
                    continue
                if state.get("profile_fingerprint") != current_profile_fp:
                    soft_exit("needs_refresh", "profile_changed",
                              direction_ids=direction_ids,
                              message="profile 已变化：重跑阶段 3 后再选择。该教授未写入任何选择/邮件包。")
            selected_ideas = []
            for idea_input in select.get("ideas", []):
                idea_id = idea_input.get("id")
                idea = None
                group_entry = None
                if len(direction_ids) == 1:
                    idea = next((c for c in state_direction.get("candidates", [])
                                 if c.get("id") == idea_id), None)
                if idea is None:
                    group_entry = next(
                        (group for group in state.get("cross_direction_groups") or []
                         if isinstance(group, dict)
                         and sorted(group.get("direction_ids") or []) == direction_ids
                         and any(c.get("id") == idea_id for c in group.get("candidates") or [])),
                        None)
                    if group_entry is not None:
                        idea = next(c for c in group_entry.get("candidates") or []
                                    if c.get("id") == idea_id)
                if idea is None:
                    skipped.append({"professor": professor, "direction_ids": direction_ids,
                                    "idea": idea_id, "reason": "unknown_idea_id"})
                    continue
                participants = None
                if len(direction_ids) >= 2:
                    participants = _stage4_cross_group(pack, group_entry or {})
                    if participants is None:
                        soft_exit("needs_refresh", "cross_participant_changed",
                                  direction_ids=direction_ids, idea=idea_id,
                                  message="跨方向想法引用的参与方向已变化或指纹过期：先重跑阶段 3 刷新候选，再重新选择。该教授未写入任何选择/邮件包。")
                idea_full = dict(idea)
                idea_full["red_lines"] = idea.get("red_lines") or []
                papers_override = validate_papers_override(
                    idea, idea_input.get("papers_override"),
                    f"{professor}::{scope}::{idea_id}")
                entry = compile_email_entry(
                    pack, state_direction, pack_direction, idea_full,
                    idea_input.get("note") or "", program_root, current_profile_fp,
                    papers_override, evidence_snapshot,
                    group_entry=group_entry if len(direction_ids) >= 2 else None,
                    participant_directions=participants)
                email_entries.append(entry)
                selected_ideas.append(idea_input)
            if not selected_ideas:
                continue
            select = dict(select, ideas=selected_ideas, direction_ids=direction_ids)
            primary = next((d for d in pack.get("directions", [])
                            if direction_machine_id(d) == direction_ids[0]), {})
            written_selections.append({
                "professor": professor,
                "professor_dir": str(professor_dir),
                "direction_ids": direction_ids,
                "zotero_collection": (state_direction or {}).get("zotero_collection")
                or select.get("zotero_collection"),
                "name_ja": primary.get("name_ja"), "name_zh": primary.get("name_zh"),
                "collection_key": primary.get("collection_key"),
                "reason": select.get("reason"),
                "ideas": [{"id": i.get("id"), "note": i.get("note") or "",
                           "papers_override": i.get("papers_override") or None}
                          for i in select.get("ideas", [])]})
        if skipped or not written_selections:
            # R67-G1-3: inside ONE professor any entry failure fails the whole
            # batch with zero writes -- a valid remainder must never be partially
            # committed while another entry of the same professor failed. skipped
            # carries the exact per-entry reason (missing input pack, needs_stage3,
            # direction not in state/pack, ...) so the row stays actionable.
            fail("validation_failed", "selection batch has uncompilable entries",
                 skipped=skipped)
        selection_doc = {
            "schema": STAGE4_LOCAL_SCHEMA, "kind": SELECTION_KIND,
            "identity_version": DIRECTION_IDENTITY_VERSION,
            "managed_by": MANAGED_BY, "program_root": str(program_root),
            "professor": professor, "professor_dir": str(professor_dir),
            "generated_at": now_utc(),
            "profile_fingerprint": current_profile_fp,
            "selections": written_selections}
        email_pack_doc = {
            "schema": STAGE4_LOCAL_SCHEMA, "kind": EMAIL_PACK_KIND,
            "identity_version": DIRECTION_IDENTITY_VERSION,
            "managed_by": MANAGED_BY, "program_root": str(program_root),
            "professor": professor, "professor_dir": str(professor_dir),
            "generated_at": now_utc(),
            "profile_fingerprint": current_profile_fp,
            "emails": email_entries}
        atomic_json_many([(selection_path, selection_doc), (email_pack_path, email_pack_doc)])
        return stage4_professor_row(
            professor, professor_dir, "ok", None,
            selection_file=str(selection_path), email_pack=str(email_pack_path),
            selected_directions=[
                f"{professor} · {'+'.join(s.get('direction_ids') or [])}"
                for s in written_selections],
            emails_compiled=len(email_entries), skipped=skipped)

    def stage4_professor_transaction(program_root: Path, professor_dir: Any, selects: list,
                                     current_profile_fp: str | None,
                                     evidence: tuple) -> dict:
        """One professor's Stage-4 transaction as a machine row, with no process exit.

        Expected professor-scoped business failures become that professor's row; an
        unexpected programming error keeps propagating after `atomic_json_many()` has
        rolled the current pair back, so it is never downgraded to a business row."""
        professor_dir = Path(str(professor_dir))
        professor = next((s.get("professor") for s in selects
                          if isinstance(s, dict) and s.get("professor")), None)
        row = stage4_professor_row(professor, professor_dir, "error")
        try:
            with professor_business_channel():
                return _stage4_professor_commit(program_root, professor_dir, selects,
                                                current_profile_fp, evidence, row)
        except ProfessorBusinessFailure as failure:
            return _stage4_failure_row(row, failure.payload)

    def cmd_stage4_finalize(args) -> None:
        """Commit Stage-4 authority per professor and emit one aggregate machine result."""
        program_root = Path(args.program_root)
        selection_input, error = read_json_file(Path(args.selection_input))
        if error or not isinstance(selection_input, dict):
            fail("invalid_params", f"selection input unreadable: {args.selection_input}")
        current_profile_fp = profile_fingerprint(args.profile)
        selects = selection_input.get("selections") or []
        if not isinstance(selects, list) or not selects:
            fail("invalid_params", "selection input has no selections")
        # Group by canonical professor_dir in first-appearance order: the display name
        # is business content, never the transaction key (issue #67 R67-G1-9).
        groups: dict = {}
        for index, select in enumerate(selects):
            if not isinstance(select, dict):
                fail("invalid_selection", f"selections[{index}] must be an object")
            if not str(select.get("professor") or "").strip() and \
                    not str(select.get("professor_dir") or "").strip():
                fail("invalid_selection",
                     f"selections[{index}] carries neither professor nor professor_dir")
            key = canonical_professor_dir(select.get("professor_dir")) \
                if str(select.get("professor_dir") or "").strip() else f"missing-professor-dir#{index}"
            groups.setdefault(key, []).append(select)
        evidence = load_contact_evidence(program_root)
        results = []
        for group in groups.values():
            results.append(stage4_professor_transaction(
                program_root, group[0].get("professor_dir"), group, current_profile_fp, evidence))
        committed = [row for row in results if row["status"] == "ok"]
        status = "ok" if len(committed) == len(results) else ("partial" if committed else "error")
        emit({"status": status, "results": results})
        if not committed:
            sys.exit(1)

    def _stage4_migration_result(outcome: str, source: dict | None = None, **extra) -> None:
        """Single machine result + exit code for one professor's migration attempt.

        Only outcomes that leave a usable (or deliberately untouched) local pair exit
        0; every other expected migration outcome is that professor's own failure and
        the caller keeps routing the remaining professors."""
        payload = {"status": outcome}
        for key in ("professor", "professor_dir", "reason_code", "selection_file", "email_pack"):
            payload[key] = (source or {}).get(key)
        payload.update(extra)
        emit(payload)
        if outcome in STAGE4_MIGRATION_COMMITTED:
            sys.exit(0)
        sys.exit(1 if outcome == "error" else 2)

    def cmd_stage4_migrate_local(args) -> None:
        """Scoped legacy migration: one canonical professor_dir, current facts only.

        The legacy program-level selection is read as a row source for THIS professor
        and is never modified; the legacy program-level email pack is never a source of
        truth, so the local email facts are recompiled from current Stage-3 state/input
        (issue #67 R67-G1-5 / R67-G1-11)."""
        program_root = Path(args.program_root)
        professor_dir = Path(str(args.professor_dir))
        containment = professor_dir_containment_error(professor_dir, program_root)
        if containment:
            fail(containment, "professor_dir must be inside program_root/教授研究",
                 professor_dir=str(professor_dir),
                 allowed_root=str((program_root / "教授研究").resolve()))
        selection_path, email_pack_path = stage4_local_pair_paths(professor_dir)
        canonical = canonical_professor_dir(professor_dir)
        if selection_path.exists() and email_pack_path.exists():
            prior, prior_error = read_json_file(selection_path)
            if prior_error or not isinstance(prior, dict):
                fail("invalid_selection",
                     f"existing local selection unreadable: {selection_path}: {prior_error}")
            rows = prior.get("selections") or []
            _stage4_migration_result(
                "already_local",
                {"professor": prior.get("professor"), "professor_dir": str(professor_dir),
                 "selection_file": str(selection_path), "email_pack": str(email_pack_path)},
                migrated_rows=len(rows) if isinstance(rows, list) else 0,
                message="完整 professor-local pair 已存在：byte-for-byte 保留，不覆盖。")
        if selection_path.exists() or email_pack_path.exists():
            _stage4_migration_result(
                "local_pair_incomplete",
                {"professor": None, "professor_dir": str(professor_dir),
                 "reason_code": "local_pair_incomplete"},
                message="professor-local Stage-4 pair 只存在一个文件：整批 fail closed、零写入，"
                        "不猜测哪一份更可信，也不生成另一半。")
        legacy_path = program_root / "教授研究" / SELECTION_FILE
        legacy, legacy_error = read_json_file(legacy_path)
        legacy_rows = ((legacy or {}).get("selections") or []) if isinstance(legacy, dict) else []
        scoped = [row for row in legacy_rows
                  if isinstance(row, dict)
                  and canonical_professor_dir(row.get("professor_dir")) == canonical]
        if not scoped:
            # An unreadable legacy file or another professor's rows are never this
            # professor's prerequisite: normal local finalize compiles from facts.
            _stage4_migration_result(
                "not_applicable",
                {"professor": None, "professor_dir": str(professor_dir),
                 "reason_code": "legacy_selection_unreadable"
                 if legacy_error not in (None, "not_found") else None},
                migrated_rows=0,
                message="该教授没有可迁移的 legacy 选择行：零迁移写入，直接按当前事实进入正常 local finalize。")
        row = stage4_professor_transaction(program_root, professor_dir, scoped,
                                            profile_fingerprint(args.profile),
                                            load_contact_evidence(program_root))
        if row["status"] == "ok":
            _stage4_migration_result(
                "migrated", row, migrated_rows=len(scoped),
                message="已按当前候选状态/输入包重编译该教授的 local pair；"
                        "legacy global 文件保持原 bytes，仅作历史兼容来源。")
        _stage4_migration_result(row["status"], row)

    return types.SimpleNamespace(
                _stage4_cross_group=_stage4_cross_group,
                validate_stage4_selections=validate_stage4_selections,
                stage4_local_pair_paths=stage4_local_pair_paths,
                stage4_professor_row=stage4_professor_row,
                _stage4_failure_row=_stage4_failure_row,
                _stage4_professor_commit=_stage4_professor_commit,
                stage4_professor_transaction=stage4_professor_transaction,
                cmd_stage4_finalize=cmd_stage4_finalize,
                _stage4_migration_result=_stage4_migration_result,
                cmd_stage4_migrate_local=cmd_stage4_migrate_local,
    )
