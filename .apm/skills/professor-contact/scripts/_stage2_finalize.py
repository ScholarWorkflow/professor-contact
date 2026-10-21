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

import copy
import json
import re
import sys
import types
import uuid
from pathlib import Path


def build(*, Stage2Context,
          Stage2PackRefineContext,
          atomic_json,
          emit,
          fail,
          soft_exit,
          now_utc,
          sha256_text,
          sha256_bytes,
          sha256_obj,
          read_json_file,
          direction_machine_id,
          pack_paper_index,
          pack_direction_relevant_keys,
          managed_snapshot,
          split_frontmatter,
          split_frontmatter_bytes,
          managed_conflict,
          managed_write,
          atomic_write,
          render_frontmatter,
          save_freshness_cache,
          _resolve_evidence,
          _current_resolve_fingerprint,
          _facts_preflight_proof,
          _sidecar_preflight_proof,
          stage2_target_path,
          read_stage2_target,
          read_stage1_professor_entry,
          stage2_preflight_cheap_inputs,
          stage2_preflight_metadata,
          stage2_pack_state_fingerprint,
          stage2_pack_content_fingerprint,
          stage2_group_consumed_keys,
          stage2_refresh_preflight_metadata,
          observed_source_projection,
          stage2_candidate_universe,
          observed_level_projection,
          stage2_artifact_guard_reason,
          _pack_resolved_grouping,
          validate_freshness_results,
          validate_narrative,
          build_direction_pack,
          render_analysis_document,
          render_analysis_md,
          stage2_validation_legality,
          stage2_freshness_view_fingerprint,
          load_freshness_cache,
          MANAGED_BY,
          INPUT_PACK_SCHEMA,
          DIRECTION_IDENTITY_VERSION,
          INPUT_PACK_KIND,
          RESOLVED_DIRECTION_SCHEMA,
          ANALYSIS_MD,
          STAGE2_RESOLUTION_SEMANTICS_VERSION,
          STAGE2_LEVEL_STATISTICS_VERSION,
          STAGE2_PREFLIGHT_VERSION,
          PLACEHOLDER_RE,
          STAGE2_U1_DISPLAY_VERSION,
          stage2_trusted_paper_title,
          stage2_require_later_paper_titles):
    def stage2_preflight_plan_drift(plan_inputs: dict, current: dict) -> list:
        """Field-level drift between the saved preflight plan and current inputs."""
        drift = []
        if plan_inputs.get("versions") != current["versions"]:
            drift.append("versions")
        if plan_inputs.get("current_year") != current["current_year"]:
            drift.append("current_year")
        if plan_inputs.get("identity") != current["identity"]:
            drift.append("identity")
        if plan_inputs.get("program_inputs") != current["program_inputs"]:
            drift.append("program_inputs")
        if plan_inputs.get("selected_direction_ids") != current["selected_direction_ids"]:
            drift.append("selected_direction_ids")
        recorded_directions = plan_inputs.get("directions")
        if not isinstance(recorded_directions, dict):
            drift.append("directions")
        else:
            if set(recorded_directions) != set(current["directions"]):
                drift.append("directions")
            else:
                for direction_id, entry in current["directions"].items():
                    if recorded_directions.get(direction_id) != entry:
                        drift.append(f"directions:{direction_id}")
        return sorted(set(drift))

    def stage2_finalize_preflight_plan(args, ctx: Stage2Context):
        """Load --preflight-file and re-verify its cheap inputs before any write.

        Stage 2 may run for a long time after the preflight decided to prepare
        evidence. Stage 0/1 state or papers.json can change underneath; finalize
        must never stamp results derived from a stale candidate universe as
        current. Returns (plan, target, snapshot_entry); a saved preflight proof is
        required for every finalize invocation.

        The payload is also bound to the facts run it produced: ``preflight_id``
        must be the payload's self-consistent proof id and must equal the id the
        analyzer recorded into the facts file (``facts.stage2_preflight``) when
        that run observed the preflight decision. Without this, a later invocation
        for the same professor could overwrite the shared saved payload and its
        (matching) fingerprints would wrongly certify facts prepared from an
        earlier target state.
        """
        if not getattr(args, "preflight_file", None):
            fail("invalid_params", "stage2-finalize requires --preflight-file")
        plan, error = read_json_file(Path(args.preflight_file))
        if (error or not isinstance(plan, dict) or plan.get("status") != "ok"
                or not isinstance(plan.get("preflight_inputs"), dict)):
            fail("invalid_params", f"preflight file unreadable or not a preflight payload: "
                                   f"{args.preflight_file}")
        if plan.get("professor") != ctx.professor:
            fail("invalid_params", "preflight file professor mismatch: "
                                   f"{plan.get('professor')!r} != {ctx.professor!r}")
        plan_inputs = plan["preflight_inputs"]
        params = plan_inputs.get("params")
        if not isinstance(params, dict) or params.get("gap_scope") != ctx.gap_scope or \
                params.get("freshness_scope") != ctx.freshness_scope:
            soft_exit("needs_refresh", "preflight_inputs_changed", drift=["params"])
        target = read_stage2_target(stage2_target_path(ctx.professor_dir), ctx.program_root, ctx.professor)
        snapshot_entry = read_stage1_professor_entry(ctx.program_root, ctx.professor_dir,
                                                     ctx.professor, target)
        if target is None or snapshot_entry is None:
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=["target_or_snapshot_missing"])
        current = stage2_preflight_cheap_inputs(
            ctx.program_root, ctx.professor_dir, ctx.professor, target, snapshot_entry, params,
            ctx.current_year)
        drift = stage2_preflight_plan_drift(plan_inputs, current)
        if drift:
            soft_exit("needs_refresh", "preflight_inputs_changed", drift=drift)
        preflight_id = sha256_obj({"professor": plan["professor"],
                                   "preflight_inputs": plan_inputs})
        if plan.get("preflight_id") != preflight_id:
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=["preflight_proof_id"])
        binding = ctx.facts.get("stage2_preflight")
        if (not isinstance(binding, dict)
                or binding.get("preflight_id") != preflight_id):
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=["preflight_proof_binding"])
        # Reuse/refresh already claims the accepted sources are unchanged. The
        # cheap inputs above do not include the consumed artifact stat guards, so
        # check them before the normal acceptance path can write anything.
        if plan.get("action") in ("reuse_all", "refresh_level"):
            old_cache = ctx.pack.get("cache") if isinstance(ctx.pack, dict) else None
            old_meta = old_cache.get("preflight") if isinstance(old_cache, dict) else None
            if isinstance(old_meta, dict):
                for direction_id in sorted(old_meta.get("directions") or {}):
                    guard_code, guard_drift = stage2_refresh_guard_drift(
                        old_meta["directions"][direction_id], direction_id)
                    if guard_code:
                        soft_exit("needs_refresh", guard_code, drift=guard_drift)
        return plan, target, snapshot_entry

    def stage2_pack_requires_membership_rebuild(pack: dict | None) -> bool:
        """True when the accepted pack predates the current membership semantics.

        Packs accepted under v2 semantics may carry an analysis reference paper in
        `supporting_item_keys`; they must rebuild authoritative membership from the
        current facts (original provisional members + accepted decisions) instead
        of copying the old members. A pack without the persisted reference scope
        cannot prove that separation either, so it is rebuilt as well.
        """
        if not isinstance(pack, dict) or not pack.get("directions"):
            return False
        cache = pack.get("cache")
        meta = cache.get("preflight") if isinstance(cache, dict) else None
        if not isinstance(meta, dict):
            # A normal U1 acceptance writes an ownership map and display marker
            # into cache.render. A narrative refine deliberately clears the
            # preflight proof, but that does not make the pack a legacy one:
            # membership/reference scope was already persisted by the accepted
            # pack and the render ownership still describes it.
            render = cache.get("render") if isinstance(cache, dict) else None
            entry = render.get(ANALYSIS_MD) if isinstance(render, dict) else None
            if not (isinstance(entry, dict)
                    and isinstance(entry.get("ownership"), dict)
                    and isinstance(entry.get("u1"), dict)):
                return True
            validator = pack.get("validator")
            if isinstance(validator, dict) \
                    and validator.get("pack_sha256") != stage2_pack_content_fingerprint(pack):
                # The pack content changed after the last validation (e.g. the
                # already-recorded preflight block was removed), so this is a
                # legacy slow-path acceptance even though a U1 ownership map is
                # present.
                return True
        elif meta.get("resolution_semantics_version") != STAGE2_RESOLUTION_SEMANTICS_VERSION:
            return True
        for direction in pack.get("directions") or []:
            if not isinstance(direction, dict):
                return True
            if not isinstance(direction.get("relevant_keys"), list):
                return True
        return False

    def stage2_old_pack_gap_statuses(entry: dict) -> dict:
        """Freshness-status records recovered from an old pack entry's gap rows.

        A membership rebuild reuses the old direction's narrative/freshness work
        (no new model job), so the rebuilt pack must keep the gap statuses the old
        pack already recorded instead of resetting them to "unknown".
        """
        statuses = {}
        for gap in list(entry.get("gap_shortlist") or []) + list(entry.get("gaps_excluded") or []):
            gap_id = gap.get("gap_id") if isinstance(gap, dict) else None
            if not isinstance(gap_id, str):
                continue
            statuses[gap_id] = {
                "gap_id": gap_id, "item_key": gap.get("item_key"),
                "status": gap.get("status") or "unknown",
                "model_evidence": gap.get("evidence"),
                "candidate_paper_ids": list(gap.get("candidate_paper_ids") or []),
                "evaluated_at": gap.get("evaluated_at"),
                "confidence": gap.get("confidence") or "low",
                "completed_part": gap.get("completed_part"),
                "remaining_gap": gap.get("remaining_gap"),
            }
        return statuses

    def stage2_render_state(pack: dict, *, include_level: bool = True) -> dict:
        """The exact pack content the managed analysis Markdown displays.

        Used to decide whether a finalized pack must re-render: a membership,
        reference-licence, narrative, gap, name or trusted-title change is visible
        even when no new model job was needed, while a metadata-only rewrite stays
        unchanged. `analysis_level` only feeds the header statistics: it is the
        display change that drives a re-render but not the business-evidence
        change that expires a validator certification, so callers may exclude it
        to obtain the business-only view.
        """
        directions_state = []
        referenced: set = set()
        for direction in pack.get("directions") or []:
            narrative = direction.get("narrative") if isinstance(direction.get("narrative"), dict) else {}
            refs = set()
            for block in narrative.get("positioning") or []:
                if isinstance(block, dict):
                    for kind, key in PLACEHOLDER_RE.findall(block.get("text") or ""):
                        if kind in ("P", "L"):
                            refs.add(key)
            referenced.update(refs)
            referenced.update(direction.get("supporting_item_keys") or [])
            referenced.update(pack_direction_relevant_keys(direction))
            referenced.update(direction.get("named_keys") or [])
            directions_state.append({
                "direction_id": direction_machine_id(direction),
                "name_ja": direction.get("name_ja"),
                "name_zh": direction.get("name_zh"),
                "supporting_item_keys": list(direction.get("supporting_item_keys") or []),
                "relevant_keys": pack_direction_relevant_keys(direction),
                "named_keys": list(direction.get("named_keys") or []),
                "credibility": direction.get("credibility") or {},
                "red_lines": direction.get("red_lines") or [],
                "user_note": direction.get("user_note") or "",
                "gap_shortlist": [
                    {key: gap.get(key) for key in ("gap_id", "item_key", "paper_title", "paper_year",
                                                   "authorship", "quote", "translation_zh", "source",
                                                   "page", "status", "evidence", "confidence",
                                                   "completed_part", "remaining_gap", "no")}
                    for gap in direction.get("gap_shortlist") or []],
                "gaps_excluded": [
                    {key: gap.get(key) for key in ("gap_id", "item_key", "paper_title", "status")}
                    for gap in direction.get("gaps_excluded") or []],
                "completed_gap_blacklist": direction.get("completed_gap_blacklist") or [],
                "narrative": narrative,
                "narrative_later_papers": direction.get("narrative_later_papers") or {},
                "resolved_direction": direction.get("resolved_direction") or {},
            })
        papers = pack_paper_index(pack)
        # A paper's analysis level changes only the managed header statistics and
        # the paper's own display state. `pdf_available` no longer feeds the
        # statistics (the real analysis level does), so it is not display-relevant.
        paper_fields = ["title", "year", "authorship", "analysis_file"]
        if include_level:
            paper_fields.append("analysis_level")
        papers_state = {
            key: {field: (papers.get(key) or {}).get(field) for field in paper_fields}
            for key in sorted(referenced)
        }
        return {"directions": directions_state, "papers": papers_state}

    def stage2_require_paper_reference_titles(fallback_papers: dict, pack: dict,
                                              direction: dict) -> None:
        """Refuse a `{{P:key}}` citation the direction is not licensed to make.

        The persisted `relevant_keys` is the citation licence (an explicit empty
        list licenses nothing); a reference must also resolve to a trusted title
        from the canonical pack or the current facts. It is never acceptable to
        fall back to showing the raw item_key.
        """
        allowed = set(pack_direction_relevant_keys(direction))
        canonical = pack_paper_index(pack)
        narrative = direction.get("narrative") if isinstance(direction.get("narrative"), dict) else {}
        referenced = set()
        for block in narrative.get("positioning") or []:
            if isinstance(block, dict):
                for kind, key in PLACEHOLDER_RE.findall(block.get("text") or ""):
                    if kind == "P":
                        referenced.add(key)
        for key in sorted(referenced):
            if key not in allowed:
                fail("missing_paper_reference_license",
                     f"direction {direction_machine_id(direction)} renders {{{{P:{key}}}}} but "
                     "that paper is outside its persisted analysis reference scope (relevant_keys)",
                     item_key=key, direction=direction_machine_id(direction))
            record = canonical.get(key) if isinstance(canonical.get(key), dict) else fallback_papers.get(key)
            if stage2_trusted_paper_title(record, key) is None:
                fail("missing_paper_reference_title",
                     f"direction {direction_machine_id(direction)} renders {{{{P:{key}}}}} but no "
                     "trusted title is available in the input pack or supported paper facts",
                     item_key=key, direction=direction_machine_id(direction))

    STAGE2_ZOTERO_LINK_RE = re.compile(
        r"zotero://select/library/items/([A-Za-z0-9]+)")
    STAGE2_GENERATED_TIMESTAMP_RE = re.compile(
        r"^> (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) ｜ 数据来源：")
    STAGE2_GENERATED_TIME_PLACEHOLDER = "<generated-at>"

    def stage2_mask_generated_timestamp(line: str) -> str | None:
        match = STAGE2_GENERATED_TIMESTAMP_RE.match(line)
        if not match:
            return None
        return (line[:match.start(1)] + STAGE2_GENERATED_TIME_PLACEHOLDER
                + line[match.end(1):])

    def stage2_equivalent_managed_body(old_body: bytes, new_body: bytes) -> bool:
        """Compare body bytes, ignoring only the top source line's generation time.

        The exemption is limited to the fixed generated source line before the
        first section heading, and then only to the timestamp value: prefix,
        separator and every other byte (including each line ending) must be
        identical.  A user-note line can have the same ``> timestamp ｜
        数据来源：`` shape; it is still compared verbatim.
        """
        if old_body == new_body:
            return True
        try:
            old_text = old_body.decode("utf-8")
            new_text = new_body.decode("utf-8")
        except UnicodeDecodeError:
            return False
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        if len(old_lines) != len(new_lines):
            return False
        first_section = next(
            (index for index, line in enumerate(old_lines)
             if line.startswith("## ")), len(old_lines))
        source_index = None
        for index in range(first_section):
            if STAGE2_GENERATED_TIMESTAMP_RE.match(old_lines[index]):
                if source_index is not None:
                    # The fixed layout can only identify one generated source
                    # line; anything else is not the renderer's fixed header.
                    return False
                source_index = index
        if source_index is None:
            return False
        masked_old = list(old_lines)
        masked_new = list(new_lines)
        old_masked = stage2_mask_generated_timestamp(old_lines[source_index])
        new_masked = stage2_mask_generated_timestamp(new_lines[source_index])
        if old_masked is None or new_masked is None:
            return False
        masked_old[source_index] = old_masked
        masked_new[source_index] = new_masked
        return "".join(masked_old).encode("utf-8") == "".join(masked_new).encode("utf-8")

    def stage2_business_basis(pack: dict | None) -> dict:
        """Identity and licence sets that make the accepted Stage-2 result business state.

        Display metadata (collection_key, names, generated time, U1 marker/map or
        derived candidate lists) is deliberately absent: a pure display update
        never counts as a new business version.
        """
        directions = {}
        for direction in (pack or {}).get("directions") or []:
            if not isinstance(direction, dict):
                continue
            did = direction_machine_id(direction)
            resolved = direction.get("resolved_direction")
            if not isinstance(resolved, dict):
                resolved = {}
            directions[did] = {
                "input_fingerprint": direction.get("input_fingerprint"),
                "provisional_input_fingerprint": (
                    direction.get("provisional_input_fingerprint")
                    or direction.get("input_fingerprint")),
                "supporting_item_keys": sorted(set(
                    direction.get("supporting_item_keys") or [])),
                "relevant_keys": sorted(set(pack_direction_relevant_keys(direction))),
                "named_keys": sorted(set(direction.get("named_keys") or [])),
                "resolved_identity": {
                    "resolved_direction_id": resolved.get("resolved_direction_id"),
                    "provisional_direction_id": resolved.get("provisional_direction_id"),
                    "resolution_type": resolved.get("resolution_type"),
                    "split_target": resolved.get("split_target"),
                    "merge_target": resolved.get("merge_target"),
                    "merged_from": sorted(resolved.get("merged_from") or []),
                },
            }
        rows = []
        block = (pack or {}).get("resolved_directions")
        if isinstance(block, dict):
            for row in block.get("directions") or []:
                if not isinstance(row, dict):
                    continue
                rows.append({key: row.get(key) for key in (
                    "provisional_direction_id", "resolved_direction_id",
                    "resolution_type", "split_target", "merge_target",
                    "input_fingerprint", "provisional_input_fingerprint")})
        rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))
        return {"directions": directions, "resolved_rows": rows}

    def stage2_checked_gap_statuses(ctx) -> dict:
        """Freshness cache records that still prove their gap and candidates."""
        checked = {}
        for plan in ctx.direction_plans:
            for gap in plan["ranked"]:
                item, _hit = ctx.freshness_entry(plan, gap)
                status = item.get("status")
                if item.get("cached") and isinstance(status, dict):
                    checked[gap["gap_id"]] = status
        return checked

    def stage2_fill_blacklist_candidates(entry: dict, checked: dict) -> None:
        """Derive missing blacklist candidate ids from a still-valid cache record.

        Older packs did not persist the structured candidate list; the displayed
        evidence may name them, but natural language is never parsed into a list.
        A genuinely missing or invalid cache record leaves the field absent.
        """
        for item in entry.get("completed_gap_blacklist") or []:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("candidate_paper_ids"), list):
                continue
            status = checked.get(item.get("gap_id"))
            if isinstance(status, dict) and status.get("status") == "done_by_self":
                item["candidate_paper_ids"] = list(
                    status.get("candidate_paper_ids") or [])

    def stage2_display_reference_keys(direction: dict) -> set:
        """Structured paper keys the four fixed-evidence exits actually display."""
        keys = set()

        def add_links(text):
            if isinstance(text, str):
                keys.update(STAGE2_ZOTERO_LINK_RE.findall(text))

        for gap in direction.get("gap_shortlist") or []:
            if not isinstance(gap, dict):
                continue
            declared = [key for key in gap.get("candidate_paper_ids") or []
                        if isinstance(key, str) and key]
            for field in ("evidence", "completed_part", "remaining_gap"):
                text = gap.get(field)
                if not isinstance(text, str):
                    continue
                for key in declared:
                    if re.search(r"(?<![A-Za-z0-9])" + re.escape(key)
                                 + r"(?![A-Za-z0-9])", text):
                        keys.add(key)
                add_links(text)
        for item in direction.get("completed_gap_blacklist") or []:
            if not isinstance(item, dict):
                continue
            completed = item.get("completed_by_item_key")
            if isinstance(completed, str) and completed:
                keys.add(completed)
            declared = [key for key in item.get("candidate_paper_ids") or []
                        if isinstance(key, str) and key]
            text = item.get("evidence")
            if isinstance(text, str):
                for key in declared:
                    if re.search(r"(?<![A-Za-z0-9])" + re.escape(key)
                                 + r"(?![A-Za-z0-9])", text):
                        keys.add(key)
                add_links(text)
        return keys

    _LEASE_OWNER_CACHE: dict = {}


    def stage2_lease_owner() -> tuple:
        """Load the professor-scoped local-writer lease owner on first use.

        The level-refresh command is a second internal user of the handoff
        entrypoint's existing `acquire_local_lease(..., verify_plan=False)` /
        `release_local_lease` API. Loading it lazily keeps the runner's start-up
        contract unchanged for installed layouts that do not ship the handoff
        tools, and never re-implements the lock or lease format.
        """
        owner = _LEASE_OWNER_CACHE.get("owner")
        if owner is None:
            import importlib.util
            path = Path(__file__).with_name("stage2_chatgpt_handoff.py")
            spec = importlib.util.spec_from_file_location("_stage2_lease_owner", path)
            if spec is None or spec.loader is None:
                fail("invalid_params", f"cannot load the Stage-2 lease owner: {path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            owner = (module.acquire_local_lease, module.release_local_lease)
            _LEASE_OWNER_CACHE["owner"] = owner
        return owner


    _GENERATED_LINE_RE = re.compile(
        r"(?m)^> \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z(?=[^\n]*｜ 数据来源：)")


    def stage2_body_without_generation_time(body: str) -> str:
        """The accepted-body comparison basis: only the fixed top timestamp drops.

        The renderer's statistics header is the first `> <generation time> ｜
        数据来源：…` line (below the fixed title/macro block). The substitution
        touches only that timestamp token: line endings, trailing bytes and the
        statistics text on the same line stay exactly as they are.
        """
        return _GENERATED_LINE_RE.sub("> <generated>", body, count=1)


    def stage2_old_managed_render(md_path: Path) -> dict:
        """Read the current managed file: header, real body bytes and its binding."""
        try:
            data = md_path.read_bytes()
        except OSError:
            return {"readable": False, "header": None, "body": "", "body_sha256": None,
                    "binding_valid": False}
        header, body_bytes = split_frontmatter_bytes(data)
        try:
            body = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return {"readable": False, "header": None, "body": "", "body_sha256": None,
                    "binding_valid": False}
        body_sha = sha256_bytes(body_bytes)
        binding_valid = (isinstance(header, dict)
                         and header.get("managed_by") == MANAGED_BY
                         and header.get("render_sha256") == body_sha)
        return {"readable": True, "header": header, "body": body,
                "body_sha256": body_sha, "binding_valid": binding_valid}


    def stage2_accept_managed_body(md_path: Path, body: str, previous_sha: str | None,
                                   decision: str | None, state_fingerprint: str,
                                   old: dict | None = None) -> dict:
        """Bounded acceptance of one rendered candidate body.

        Only the renderer's fixed generation timestamp is ignored. When the old
        body is byte-equivalent and its managed binding was valid, the old body
        bytes and their real SHA are kept (the machine header is synchronized
        only when it is needed to bind the current candidate). Otherwise the
        existing protected write runs. An unreadable/invalid old binding is never
        declared equivalent.
        """
        old = old if old is not None else stage2_old_managed_render(md_path)
        candidate_sha = sha256_text(body)
        equivalent = bool(old.get("binding_valid")) and (
            stage2_body_without_generation_time(old["body"])
            == stage2_body_without_generation_time(body))
        if equivalent:
            actual_sha = old["body_sha256"]
            header = old.get("header") or {}
            if header.get("render_sha256") != actual_sha \
                    or header.get("state_fingerprint") != state_fingerprint:
                md_result = managed_write(md_path, old["body"], state_fingerprint,
                                          previous_sha, decision)
                return {"written": md_result["written"], "equivalent": True,
                        "needs_decision": md_result["needs_decision"],
                        "sha256": actual_sha,
                        "target": md_result.get("target"),
                        "existing_sha256": md_result.get("existing_sha256"),
                        "new_sha256": md_result.get("new_sha256")}
            return {"written": False, "equivalent": True, "needs_decision": False,
                    "sha256": actual_sha}
        md_result = managed_write(md_path, body, state_fingerprint, previous_sha, decision)
        return {"written": md_result.get("written", False), "equivalent": False,
                "needs_decision": md_result.get("needs_decision", False),
                "sha256": md_result.get("sha256"),
                "target": md_result.get("target"),
                "existing_sha256": md_result.get("existing_sha256"),
                "new_sha256": md_result.get("new_sha256")}


    def cmd_stage2_finalize(args) -> None:
        ctx = Stage2Context(Path(args.facts))
        preflight_plan, preflight_target, preflight_snapshot = \
            stage2_finalize_preflight_plan(args, ctx)
        # Isolate the accepted old snapshot before ANY candidate is assembled:
        # normalize_input_pack only shallow-copies, so reusing/mutating one of its
        # nested dicts would silently rewrite the comparison baseline too.
        old_pack = copy.deepcopy(ctx.pack) if isinstance(ctx.pack, dict) else None
        old_render = ((old_pack or {}).get("cache") or {}).get("render", {})
        results_dir = Path(args.results)
        decision = None
        if getattr(args, "decision_file", None):
            decision_data, error = read_json_file(Path(args.decision_file))
            if error is None and isinstance(decision_data, dict):
                decision = decision_data.get("decision")

        # Load resolved directions if provided. Fail closed on any identity or
        # freshness problem: a sidecar from another professor, with a broken
        # schema, or built from different facts must NEVER be silently applied.
        resolved_directions = None
        resolved_directions_path = getattr(args, "resolved_directions", None)
        if resolved_directions_path:
            rd_data, rd_error = read_json_file(Path(resolved_directions_path))
            if rd_error is not None or not isinstance(rd_data, dict):
                fail("invalid_resolved_directions",
                     f"resolved directions file unreadable: {resolved_directions_path}")
            if rd_data.get("schema") != RESOLVED_DIRECTION_SCHEMA or \
                    rd_data.get("kind") != "professor-contact-resolved-directions":
                fail("invalid_resolved_directions",
                     f"resolved directions schema/kind mismatch: {resolved_directions_path}")
            if rd_data.get("professor") != ctx.professor:
                fail("resolved_directions_professor_mismatch",
                     f"resolved directions file belongs to professor {rd_data.get('professor')!r}, "
                     f"not {ctx.professor!r}", path=str(resolved_directions_path))
            resolved_directions = {
                d["provisional_direction_id"]: d
                for d in rd_data.get("directions", [])
                if isinstance(d, dict) and isinstance(d.get("provisional_direction_id"), str)
            }
            # Per-direction freshness: every current direction must be covered by an
            # entry whose input_fingerprint matches the current facts. Stale or
            # missing entries fail closed so a half-updated resolved file can never
            # leak into the pack. Fingerprints hash the exact resolve model_input —
            # the same evidence universe the resolve plan/finalize wrote.
            evidence = _resolve_evidence(ctx)
            stale = []
            for plan in ctx.direction_plans:
                entry = resolved_directions.get(plan["did"])
                if entry is None:
                    stale.append({"direction": plan["did"], "problem": "missing_from_resolved_file"})
                elif entry.get("input_fingerprint") != _current_resolve_fingerprint(ctx, plan, evidence):
                    stale.append({"direction": plan["did"], "problem": "input_fingerprint_mismatch"})
            if stale:
                fail("resolved_directions_stale",
                     "resolved directions do not match current facts; re-run stage2-resolve",
                     stale_directions=stale, path=str(resolved_directions_path))
            # Acceptance is the user-choice machine boundary (issue #7 required flow
            # #5): a material change stays "proposed" until the user explicitly
            # adopts it (stage2-resolve-accept) or keeps provisional
            # (--keep-provisional). A sidecar carrying any proposed entry must
            # NEVER be applied — the choice cannot be bypassed by passing the
            # sidecar file directly.
            not_accepted = sorted(
                plan["did"] for plan in ctx.direction_plans
                if (resolved_directions.get(plan["did"]) or {}).get("acceptance") != "accepted")
            if not_accepted:
                fail("resolved_directions_not_accepted",
                     "resolved directions still contain unaccepted proposals; the user must choose "
                     "first (stage2-resolve-accept --ckeys <dir,...> to adopt, or stage2-resolve-finalize "
                     "--keep-provisional <dir,...> to keep provisional) before stage2-finalize may apply them",
                     not_accepted_directions=not_accepted, path=str(resolved_directions_path))
            # Proof binding (issue #7 × #11): the sidecar must come from the same
            # facts/preflight generation as the facts run it is applied to. This
            # runs BEFORE any pack/freshness/Markdown write, so a mismatch keeps
            # zero-write semantics; it is recoverable like the other preflight
            # binding drifts (restart Stage 2 from the current preflight).
            facts_proof, facts_proof_error = _facts_preflight_proof(ctx.facts)
            if facts_proof_error or _sidecar_preflight_proof(rd_data) != facts_proof:
                soft_exit("needs_refresh", "resolved_directions_proof_mismatch",
                          drift=["resolved_directions_proof_binding"],
                          sidecar_preflight_id=_sidecar_preflight_proof(rd_data),
                          facts_preflight_id=facts_proof,
                          facts_binding_error=facts_proof_error,
                          path=str(resolved_directions_path))

        required_freshness, needed_keys = {}, []
        for plan in ctx.direction_plans:
            if plan["reuse"]:
                continue
            needed_keys.append(plan["did"])
            judge, hits = ctx.freshness_job_items(plan)
            required_freshness[plan["did"]] = judge
        statuses_by_direction = validate_freshness_results(ctx, results_dir, required_freshness)
        narratives = validate_narrative(ctx, results_dir, needed_keys) if needed_keys else {}
        # A deep snapshot of the accepted pack is the ONLY old side this command
        # may compare against or report to the validator. It is taken before any
        # new-field normalization, candidate assembly or reused-entry edit, so
        # nested directions/papers/resolved data can never be polluted by the
        # candidate path (load_input_pack's v2 view is a shallow copy).
        old_pack = copy.deepcopy(ctx.pack) if isinstance(ctx.pack, dict) else None
        old_directions = {direction_machine_id(e): e
                          for e in (old_pack or {}).get("directions", [])}
        old_render = ((old_pack or {}).get("cache") or {}).get("render", {})
        # A pack accepted under older membership semantics must rebuild its
        # authoritative membership from the current facts: only the narrative /
        # freshness work may be reused, never the old `supporting_item_keys`.
        pack_needs_rebuild = stage2_pack_requires_membership_rebuild(old_pack)
        checked_gap_statuses = stage2_checked_gap_statuses(ctx)
        pack_directions = []
        fresh_papers: dict = {}
        for plan in ctx.direction_plans:
            old_entry = old_directions.get(plan["did"])
            if plan["reuse"] and not pack_needs_rebuild:
                # The candidate must be a copy: reused entries are edited below
                # (collection_key/resolved application) and must never mutate the
                # isolated old snapshot that proves the previous acceptance.
                reused_entry = copy.deepcopy(old_entry) if isinstance(old_entry, dict) \
                    else old_entry
                # collection_key is projection metadata: refresh it from the facts
                # so a projection-only rename carries without touching fingerprints.
                reused_entry["collection_key"] = plan["direction"].get("collection_key")
                pack_directions.append(reused_entry)
            else:
                if plan["reuse"]:
                    # Old-semantics rebuild: keep the accepted narrative/freshness
                    # work of this direction, rebuild members and references from
                    # the current facts, then apply the accepted decisions below.
                    old_narrative = (old_entry or {}).get("narrative")
                    statuses = stage2_old_pack_gap_statuses(old_entry or {})
                    narrative = old_narrative if isinstance(old_narrative, dict) else None
                else:
                    statuses = statuses_by_direction.get(plan["did"], {})
                    narrative = narratives[plan["did"]]
                built, papers = build_direction_pack(ctx, plan, statuses, narrative)
                pack_directions.append(built)
                fresh_papers.update(papers)

        def _canonical_record(key: str) -> dict | None:
            """Canonical paper record from the freshest available machine source.

            Order: freshly built records (current facts) → the normalized old
            pack's canonical map → library + facts. Used when authoritative
            membership admits a paper the relevance gate never placed in the
            direction's supporting set (e.g. a full-text rescue that only lives in
            the candidate union). The resolve finalizer already validated
            facts_state == valid for every membership-changing key, so this never
            fabricates evidence.
            """
            record = fresh_papers.get(key) or pack_paper_index(old_pack or {}).get(key)
            if isinstance(record, dict):
                return dict(record)
            paper = ctx.papers.get(key)
            if not paper:
                return None
            facts_record, facts_state, facts_error = ctx.facts_for(key)
            return {
                "item_key": key, "title": paper.get("title"), "year": paper.get("year"),
                "authorship": paper.get("authorship"),
                "analysis_file": paper.get("analysis_file"),
                "analysis_level": paper.get("analysis_level"),
                "pdf_available": bool(paper.get("has_pdf")),
                "facts_state": facts_state, "facts_error": facts_error,
                "paper_facts": facts_record,
            }

        # Apply resolved directions to pack_directions. Every direction (including
        # unchanged) gets an explicit resolved_direction subfield so downstream
        # stages consume the authoritative resolved ID and never implicitly fall
        # back to the provisional collection_key.
        resolved_papers: dict = {}
        if resolved_directions:
            # Keep the provisional fingerprints around: the public
            # `input_fingerprint` is recomputed below to the resolved-aware
            # downstream value, but Stage-2's own freshness gate still needs the
            # pre-resolution value to judge reuse on the next run. A reused pack
            # entry already carries the resolved-aware value in
            # `input_fingerprint`, so the provisional value MUST come from
            # `provisional_input_fingerprint` when present — overwriting it with
            # the downstream hash would silently break the next Stage-2 reuse.
            provisional_fingerprints = {
                direction_machine_id(d): d.get("provisional_input_fingerprint")
                or d.get("input_fingerprint")
                for d in pack_directions}
            reused_ckeys = {p["did"] for p in ctx.direction_plans if p["reuse"]}
            # Papers admitted by the resolution (additions / splits / merges) may
            # reference records outside the freshly built set; they join the same
            # professor-level canonical map instead of per-direction copies.

            # Carry forward accepted derived directions (split children created by
            # a previous finalize). They have no provisional plan entry because the
            # facts only know the source direction, so without this a reuse
            # finalize would silently drop the child — and the split pass would
            # then rebuild it from the already-pruned source with empty membership.
            # A child is kept only while the current resolution still declares the
            # same split; otherwise the new resolution is authoritative and the
            # stale child disappears.
            plan_ckeys = {p["did"] for p in ctx.direction_plans}
            for old_entry in (old_pack or {}).get("directions", []):
                child_id = direction_machine_id(old_entry)
                if child_id in plan_ckeys:
                    continue
                if any(direction_machine_id(d) == child_id for d in pack_directions):
                    continue
                source_rd = resolved_directions.get(old_entry.get("resolved_direction", {})
                                                    .get("provisional_direction_id")) or {}
                if source_rd.get("resolution_type") != "split_from" \
                        or source_rd.get("split_target") != child_id:
                    continue
                pack_directions.append(copy.deepcopy(old_entry))
                provisional_fingerprints[child_id] = (
                    old_entry.get("provisional_input_fingerprint")
                    or old_entry.get("input_fingerprint"))

            def _find_pack_direction(did: str):
                for d in pack_directions:
                    if direction_machine_id(d) == did:
                        return d
                return None

            def _stamp_subfield(d: dict, rd: dict) -> None:
                did = direction_machine_id(d)
                d["resolved_direction"] = {
                    "resolved_direction_id": rd.get("resolved_direction_id") or did,
                    "provisional_direction_id": rd.get("provisional_direction_id") or did,
                    "resolution_type": rd.get("resolution_type") or "unchanged",
                    "input_fingerprint": rd.get("input_fingerprint"),
                    "papers_to_add": list(rd.get("papers_to_add") or []),
                    "papers_to_remove": list(rd.get("papers_to_remove") or []),
                    "paper_justifications": dict(rd.get("paper_justifications") or {}),
                    "split_target": rd.get("split_target"),
                    "merge_target": rd.get("merge_target"),
                }

            def _membership_keys(d: dict) -> list:
                return d.setdefault("supporting_item_keys", [])

            def _apply_membership(d: dict, rd: dict) -> None:
                remove_set = set(rd.get("papers_to_remove") or [])
                if remove_set:
                    d["supporting_item_keys"] = [
                        key for key in _membership_keys(d) if key not in remove_set]
                for add_key in rd.get("papers_to_add") or []:
                    if add_key in _membership_keys(d):
                        continue
                    record = _canonical_record(add_key)
                    if record is not None:
                        resolved_papers[add_key] = record
                        _membership_keys(d).append(add_key)
                        added = set(d.get("resolved_addition_keys") or [])
                        added.add(add_key)
                        d["resolved_addition_keys"] = sorted(added)

            # Pass 1: stamp the subfield everywhere + apply rename/refined edits.
            for d in pack_directions:
                rd = resolved_directions.get(direction_machine_id(d))
                if rd is None:
                    continue  # carried-forward split child keeps its own subfield
                _stamp_subfield(d, rd)
                rtype = rd.get("resolution_type") or "unchanged"
                if rtype in ("renamed", "refined"):
                    d["name_ja"] = rd.get("name_ja") or d.get("name_ja")
                    d["name_zh"] = rd.get("name_zh") or d.get("name_zh")
                if rtype == "refined":
                    _apply_membership(d, rd)

            # Pass 2: split_from creates a REAL new authoritative direction entry;
            # the source keeps its identity minus the split-out papers/gaps.
            for d in list(pack_directions):
                did = direction_machine_id(d)
                rd = resolved_directions.get(did)
                if rd is None or rd.get("resolution_type") != "split_from":
                    continue
                split_id = rd.get("split_target")
                split_set = set(rd.get("papers_to_add") or [])
                # Prune the source first: idempotent on an already-pruned reuse entry.
                moved_keys = [key for key in _membership_keys(d) if key in split_set]
                d["supporting_item_keys"] = [
                    key for key in _membership_keys(d) if key not in split_set]
                moved_shortlist = [g for g in d.get("gap_shortlist", []) if g.get("item_key") in split_set]
                kept_shortlist = [g for g in d.get("gap_shortlist", []) if g.get("item_key") not in split_set]
                d["gap_shortlist"] = [dict(g, no=index + 1) for index, g in enumerate(kept_shortlist)]
                moved_excluded = [g for g in d.get("gaps_excluded", []) if g.get("item_key") in split_set]
                d["gaps_excluded"] = [g for g in d.get("gaps_excluded", [])
                                      if g.get("item_key") not in split_set]
                moved_blacklist = [b for b in d.get("completed_gap_blacklist", []) if b.get("item_key") in split_set]
                d["completed_gap_blacklist"] = [b for b in d.get("completed_gap_blacklist", [])
                                                if b.get("item_key") not in split_set]
                split_named = [k for k in d.get("named_keys", []) if k in split_set]
                d["named_keys"] = [k for k in d.get("named_keys", []) if k not in split_set]
                # Re-verify the emptied-source boundary after materialization. The
                # resolve validator already rejected such a proposal; this second
                # check keeps a hand-edited/legacy sidecar from producing a source
                # entry with no formal members (zero authoritative writes).
                if not d["supporting_item_keys"]:
                    fail("invalid_resolved_directions",
                         f"split_from leaves the source direction {did} with no formal members",
                         direction=did, split_target=split_id)
                provisional_fingerprints[split_id] = provisional_fingerprints.get(did) \
                    or d.get("input_fingerprint")
                existing_child = _find_pack_direction(split_id)
                if existing_child is not None and did in reused_ckeys \
                        and not pack_needs_rebuild:
                    # The child was materialized by an earlier finalize and the
                    # source hit Stage-2 reuse: keep the accepted child membership
                    # exactly as-is. Rebuilding it from the reuse (already-pruned)
                    # source would silently empty it.
                    continue
                if existing_child is not None:
                    # Source was reprocessed (facts changed and resolve re-ran with
                    # the same split target): rebuild the child from the freshly
                    # built source so papers/gap references stay current.
                    pack_directions.remove(existing_child)
                # A full-text rescue can put a candidate-union paper into the split
                # even though the abstract relevance gate never placed it in the
                # source's supporting set; materialize those from the library.
                for key in sorted(set(split_set) - set(moved_keys)):
                    record = _canonical_record(key)
                    if record is not None:
                        resolved_papers[key] = record
                        moved_keys.append(key)
                pack_directions.append({
                    "direction_id": split_id,
                    "collection_key": None,
                    "name_ja": rd.get("name_ja") or d.get("name_ja"),
                    "name_zh": rd.get("name_zh") or "",
                    "status": "active",
                    "input_fingerprint": d.get("input_fingerprint"),
                    "user_note": rd.get("user_note") or "",
                    "credibility": d.get("credibility") or {},
                    "red_lines": [r for r in d.get("red_lines", []) if r.get("scope") != "global"],
                    "named_keys": split_named,
                    "supporting_item_keys": moved_keys,
                    # A brand-new split child starts with the minimal legal
                    # reference scope: exactly its approved final members (a legal
                    # full-text rescue included). It never inherits the source's
                    # extra references.
                    "relevant_keys": sorted(set(moved_keys)),
                    "resolved_addition_keys": sorted(split_set),
                    "gap_pool_count": len(moved_shortlist) + len(moved_excluded),
                    "gap_shortlist": [dict(g, no=index + 1) for index, g in enumerate(moved_shortlist)],
                    "gaps_excluded": moved_excluded,
                    "completed_gap_blacklist": moved_blacklist,
                    "version_families": d.get("version_families"),
                    "authorship_line": d.get("authorship_line"),
                    "narrative": {},
                    "resolved_direction": {
                        "resolved_direction_id": split_id,
                        "provisional_direction_id": did,
                        "resolution_type": "split_from",
                        "input_fingerprint": rd.get("input_fingerprint"),
                        "papers_to_add": sorted(split_set),
                        "papers_to_remove": [],
                        "paper_justifications": dict(rd.get("paper_justifications") or {}),
                        "split_target": split_id,
                        "merge_target": None,
                    },
                })

            # Pass 3: merged_into folds the source into the target and DROPS the
            # source direction entry, transplanting papers/gaps so references and
            # evidence survive; the pack-root index keeps the source→target mapping.
            merged_sources = []
            for d in list(pack_directions):
                did = direction_machine_id(d)
                rd = resolved_directions.get(did)
                if rd is None:
                    continue  # split target created in pass 2; not a merge source
                if rd.get("resolution_type") != "merged_into":
                    continue
                target = _find_pack_direction(rd.get("merge_target"))
                if target is None:
                    fail("invalid_resolved_directions",
                         f"merge target {rd.get('merge_target')} not present in pack")
                for key in list(_membership_keys(d)):
                    if key in _membership_keys(target):
                        continue
                    record = _canonical_record(key)
                    if record is not None:
                        resolved_papers[key] = record
                    _membership_keys(target).append(key)
                    added = set(target.get("resolved_addition_keys") or [])
                    added.add(key)
                    target["resolved_addition_keys"] = sorted(added)
                offset = len(target.get("gap_shortlist", []))
                for index, g in enumerate(d.get("gap_shortlist", [])):
                    if any(q.get("gap_id") == g.get("gap_id") for q in target.get("gap_shortlist", [])):
                        continue
                    target.setdefault("gap_shortlist", []).append(dict(g, no=offset + index + 1))
                for g in d.get("gaps_excluded", []):
                    if not any(q.get("gap_id") == g.get("gap_id") for q in target.get("gaps_excluded", [])):
                        target.setdefault("gaps_excluded", []).append(dict(g))
                for b in d.get("completed_gap_blacklist", []):
                    if not any(q.get("gap_id") == b.get("gap_id") for q in target.get("completed_gap_blacklist", [])):
                        target.setdefault("completed_gap_blacklist", []).append(dict(b))
                # The merge target's reference scope is the deduplicated union of
                # the participants' current reference scopes; only this merge's
                # directions join (an uninvolved direction never leaks in), and the
                # scope stays independent from the merged membership.
                merged_relevant = set(pack_direction_relevant_keys(target)) \
                    | set(pack_direction_relevant_keys(d))
                target["relevant_keys"] = sorted(merged_relevant)
                target_rd = target.get("resolved_direction") or {}
                merged_from = list(target_rd.get("merged_from") or [])
                merged_from.append(did)
                target_rd["merged_from"] = merged_from
                target["resolved_direction"] = target_rd
                merged_sources.append(did)
            if merged_sources:
                dropped = set(merged_sources)
                pack_directions = [d for d in pack_directions
                                   if direction_machine_id(d) not in dropped]

            # Recompute the downstream `input_fingerprint` AFTER the resolution has
            # been materialized. Stage 3's reuse gate compares this field, so it
            # must reflect the authoritative identity (resolved ID) and the FINAL
            # membership/gap set — otherwise a refined/split/merged direction would
            # let Stage 3 silently reuse candidates that reference papers or gaps
            # the resolution just moved or removed. Split entries get an
            # independent fingerprint computed from their own final content.
            # Issue #8: display names are projection metadata and stay OUT of the
            # hash — a rename re-renders deterministically without model work.
            for d in pack_directions:
                rd = d.get("resolved_direction") or {}
                did = direction_machine_id(d)
                d["provisional_input_fingerprint"] = provisional_fingerprints.get(
                    did, d.get("input_fingerprint"))
                d["input_fingerprint"] = sha256_obj({
                    "downstream_version": 3,
                    "identity_version": DIRECTION_IDENTITY_VERSION,
                    "direction_id": did,
                    "provisional_fingerprint": d["provisional_input_fingerprint"],
                    "resolved_identity": {
                        "resolved_direction_id": rd.get("resolved_direction_id") or did,
                        "provisional_direction_id": rd.get("provisional_direction_id") or did,
                        "resolution_type": rd.get("resolution_type") or "unchanged",
                        "merged_from": rd.get("merged_from") or [],
                    },
                    "final_supporting_keys": sorted(set(d.get("supporting_item_keys") or [])),
                    "final_gap_ids": sorted(
                        g.get("gap_id") for g in d.get("gap_shortlist", []) if g.get("gap_id")),
                })

        fingerprints = {direction_machine_id(d): d["input_fingerprint"] for d in pack_directions}
        state_fingerprint = sha256_obj({"professor": ctx.professor, "directions": fingerprints})
        # Professor-level canonical papers (issue #8 §3.3): one record per item_key,
        # resolved from fresh builds > resolution-admitted records > old snapshots.
        # Reference-scope papers (P citations) join the same map so a later render
        # or refine keeps one trusted title record even without the temp facts.
        old_papers = pack_paper_index(old_pack or {})

        def _current_level(key: str) -> str | None:
            """The level this run actually verified for the current paper.

            Only current facts can confirm a level; a paper the current facts do
            not describe is null. The old accepted pack is never a level source.
            """
            paper = ctx.papers.get(key)
            return paper.get("analysis_level") if isinstance(paper, dict) else None

        def _current_paper_record(key: str) -> dict | None:
            """Whole current-facts record, or ``None`` when the key is absent.

            Plan stage2-u1-r5 §3.1.4: existence decides the authority.  When the
            current structured records contain the key, that whole record is the
            reference authority — a null/empty/invalid title must fail instead of
            being filled back from the old canonical pack (that would fabricate
            a mixed "current" record).  Only a genuinely absent key may fall back
            to an accepted old record, and the caller validates that old record's
            title with the same trusted-title rule.
            """
            paper = ctx.papers.get(key)
            if paper is None:
                return None
            record = {"item_key": key}
            for field in ("title", "year", "authorship", "analysis_file"):
                record[field] = paper.get(field)
            record["analysis_level"] = paper.get("analysis_level")
            record["pdf_available"] = bool(paper.get("has_pdf"))
            facts_record, facts_state, facts_error = ctx.facts_for(key)
            record["facts_state"] = facts_state
            record["facts_error"] = facts_error
            record["paper_facts"] = facts_record
            return record

        papers_map: dict = {}
        for d in pack_directions:
            paper_keys = list(d.get("supporting_item_keys") or []) \
                + list(d.get("relevant_keys") or [])
            for key in paper_keys:
                if key in papers_map:
                    continue
                record = fresh_papers.get(key) or _current_paper_record(key) \
                    or resolved_papers.get(key) or old_papers.get(key)
                if record is None:
                    record = _canonical_record(key)
                if isinstance(record, dict):
                    # One explicit rule for every merge source (fresh/reused/
                    # resolved/old): the current verified level is assigned last,
                    # so a null always overrides an old value instead of falling
                    # back to it. The record is copied so no old-side nested data
                    # is mutated by this assignment.
                    canonical = dict(record)
                    canonical["analysis_level"] = _current_level(key)
                    papers_map[key] = canonical
        for direction in pack_directions:
            stage2_fill_blacklist_candidates(direction, checked_gap_statuses)
        cache_entries = dict(ctx.cache)
        for ckey, statuses in statuses_by_direction.items():
            for gap_id, record in statuses.items():
                if isinstance(record, dict) and not record.get("cache_hit"):
                    cache_entries[gap_id] = {k: v for k, v in record.items() if k != "cache_hit"}
        # Structured metadata referenced by the four fixed-evidence exits joins the
        # same canonical paper map; it never changes members or licence sets.
        display_keys = set()
        for direction in pack_directions:
            display_keys.update(stage2_display_reference_keys(direction))
        for key in sorted(display_keys):
            if key in papers_map:
                continue
            record = _current_paper_record(key) or resolved_papers.get(key) \
                or old_papers.get(key) or _canonical_record(key)
            if isinstance(record, dict):
                papers_map[key] = record
        render_pack = {"papers": papers_map, "directions": pack_directions}
        for direction in pack_directions:
            stage2_require_later_paper_titles(ctx, direction, render_pack)
            stage2_require_paper_reference_titles(ctx.papers, render_pack, direction)

        # Always generate the actual candidate body and its ownership map: an
        # equal render-state projection is not proof that the bytes match.
        # The old managed file is read once as bytes (r5 §3.6): body hashes,
        # equivalence, header comparison and the write-back all use that one
        # lossless snapshot, never a universal-newline text view.
        md_path = ctx.professor_dir / ANALYSIS_MD
        old_body_bytes = None
        old_body_text = None
        old_header = None
        if md_path.is_symlink():
            fail("validation_render_stale",
                 "the managed analysis must not be a symlink", target=str(md_path))
        if md_path.is_file():
            snapshot = managed_snapshot(md_path)
            if not isinstance(snapshot, dict) or snapshot.get("error"):
                fail("validation_render_stale",
                     "the managed analysis cannot be read losslessly as UTF-8 with a "
                     "complete frontmatter/body split; restore the managed file before "
                     "finalize may accept a new render", target=str(md_path),
                     detail=snapshot.get("error") if isinstance(snapshot, dict) else None)
            if isinstance(snapshot.get("header"), dict) \
                    and snapshot["header"].get("managed_by") == MANAGED_BY:
                old_header = snapshot["header"]
                old_body_bytes = snapshot["body_bytes"]
                old_body_text = snapshot["body"]
        old_body_sha = sha256_bytes(old_body_bytes) if old_body_bytes is not None else None
        old_state_fingerprint = sha256_obj({
            "professor": (old_pack or {}).get("professor"),
            "directions": {direction_machine_id(d): d.get("input_fingerprint")
                           for d in (old_pack or {}).get("directions") or []}})
        if old_header is not None \
                and isinstance((old_pack or {}).get("validator"), dict) \
                and old_header.get("state_fingerprint") != old_state_fingerprint:
            fail("validation_render_stale",
                 "the managed Markdown header state fingerprint does not bind "
                 "the accepted pack; re-record the old evidence instead of rebinding it",
                 target=str(md_path))
        candidate_body, ownership = render_analysis_document(
            ctx, render_pack, state_fingerprint)
        candidate_body_bytes = candidate_body.encode("utf-8")
        body_equivalent = (
            old_body_bytes is not None
            and stage2_equivalent_managed_body(old_body_bytes, candidate_body_bytes)
            and ownership.get("line_count") == len(old_body_text.splitlines()))
        final_body_bytes = old_body_bytes if body_equivalent else candidate_body_bytes
        final_body = old_body_text if body_equivalent else candidate_body
        final_sha = sha256_bytes(final_body_bytes)

        # Preserve accepted resolution provenance when this run applies no new
        # sidecar; dropping the rows would look like a business change and break
        # the validation binding for an otherwise unchanged pack.
        if resolved_directions:
            raw_provisional_fingerprints = {
                plan["did"]: plan["fingerprint"] for plan in ctx.direction_plans}
            new_resolved_block = {
                "schema": RESOLVED_DIRECTION_SCHEMA,
                "applied_at": now_utc(),
                "directions": [
                    {
                        "provisional_direction_id": ckey,
                        "resolved_direction_id": rd.get("resolved_direction_id"),
                        "resolution_type": rd.get("resolution_type"),
                        "split_target": rd.get("split_target"),
                        "merge_target": rd.get("merge_target"),
                        "input_fingerprint": rd.get("input_fingerprint"),
                        "provisional_input_fingerprint":
                            raw_provisional_fingerprints.get(ckey)
                            or provisional_fingerprints.get(ckey),
                    }
                    for ckey, rd in resolved_directions.items()
                ],
            }
        elif isinstance((old_pack or {}).get("resolved_directions"), dict):
            new_resolved_block = copy.deepcopy(old_pack["resolved_directions"])
        else:
            new_resolved_block = None
        candidate_basis = stage2_business_basis({
            "directions": pack_directions,
            "resolved_directions": new_resolved_block})
        business_changed = (bool(needed_keys) or pack_needs_rebuild
                            or stage2_business_basis(old_pack) != candidate_basis)

        # Old validator lifecycle: a real business or substantive body change
        # starts a new validation round (old raw report files stay untouched).
        # With neither change, an invalid old binding is an evidence error and is
        # rejected before writing, never silently re-bound.
        old_validator, legality_error = stage2_validation_legality(old_pack)
        carried_validator = None
        if legality_error:
            if not business_changed:
                fail("validation_render_stale",
                     f"the recorded Stage-2 validation state is malformed: {legality_error}",
                     target=str(md_path))
        elif isinstance(old_validator, dict) and old_validator.get("schema") == 2:
            binding_valid = (
                old_header is not None and old_body_sha is not None
                and old_header.get("render_sha256") == old_body_sha
                and old_header.get("state_fingerprint")
                == stage2_pack_state_fingerprint(old_pack)
                and old_validator.get("render_sha256") == old_body_sha
                and old_validator.get("pack_sha256")
                == stage2_pack_content_fingerprint(old_pack))
            if not business_changed:
                if not binding_valid:
                    fail("validation_render_stale",
                         "the recorded Stage-2 validation no longer binds the current managed "
                         "render/input pack and no business change explains it; re-record a "
                         "raw validator report too against the current files",
                         target=str(md_path))
                if body_equivalent:
                    carried_validator = dict(old_validator)

        md_result = {"written": False, "needs_decision": False, "sha256": final_sha}
        if not body_equivalent:
            conflict = managed_conflict(
                md_path, candidate_body,
                old_render.get(ANALYSIS_MD, {}).get("sha256"), decision)
            if conflict:
                soft_exit("needs_decision", conflict["reason_code"],
                          target=str(md_path),
                          existing_sha256=conflict.get("existing_sha256"),
                          new_sha256=conflict.get("new_sha256"),
                          options=["overwrite（覆盖为状态版本）", "keep_manual（保留手改，不作为流程输入）",
                                   "promote（把要保留的内容经 selection.note 或 profile 写进状态后再渲染）"])
            md_result = managed_write(
                md_path, candidate_body, state_fingerprint,
                old_render.get(ANALYSIS_MD, {}).get("sha256"), decision)
            if md_result.get("needs_decision"):
                soft_exit("needs_decision", md_result["reason_code"],
                          target=md_result.get("target"),
                          existing_sha256=md_result.get("existing_sha256"),
                          new_sha256=md_result.get("new_sha256"),
                          options=["overwrite（覆盖为状态版本）", "keep_manual（保留手改，不作为流程输入）",
                                   "promote（把要保留的内容经 selection.note 或 profile 写进状态后再渲染）"])
            final_body, final_sha = candidate_body, md_result["sha256"]
        elif (old_header is None or old_header.get("state_fingerprint") != state_fingerprint
              or old_header.get("render_sha256") != final_sha):
            # Equivalent body: keep its bytes, but the machine header still has to
            # describe the current pack.
            atomic_write(md_path,
                         render_frontmatter(state_fingerprint, final_sha) + final_body)
            md_result = {"written": True, "needs_decision": False, "sha256": final_sha}
        ownership["body_sha256"] = final_sha
        render_entry = {
            "sha256": final_sha,
            "ownership": ownership,
            "u1": {"display_version": STAGE2_U1_DISPLAY_VERSION,
                   "completed_at": now_utc()},
        }
        pack = {
            "schema": INPUT_PACK_SCHEMA, "kind": INPUT_PACK_KIND,
            "identity_version": DIRECTION_IDENTITY_VERSION,
            "managed_by": MANAGED_BY, "generated_at": now_utc(),
            "professor": ctx.professor, "professor_dir": str(ctx.professor_dir),
            "papers": papers_map,
            "directions": pack_directions,
            "cache": {"render": {ANALYSIS_MD: render_entry}},
        }
        if new_resolved_block is not None:
            pack["resolved_directions"] = new_resolved_block
        if preflight_plan is not None:
            # The statistics marker is stamped only now: the candidate body was
            # actually accepted (written, or proven byte-equivalent) above, so
            # metadata construction can never claim a success the files lack.
            pack["cache"]["preflight"] = stage2_preflight_metadata(
                program_root=ctx.program_root, professor_dir=ctx.professor_dir,
                target=preflight_target, snapshot_entry=preflight_snapshot,
                pack_directions=pack_directions,
                params=preflight_plan["preflight_inputs"]["params"],
                current_year=ctx.current_year, ctx=ctx, cache_entries=cache_entries,
                statistics_version=STAGE2_LEVEL_STATISTICS_VERSION)
        if carried_validator is not None:
            carried_validator["pack_sha256"] = stage2_pack_content_fingerprint(pack)
            pack["validator"] = carried_validator

        atomic_json(ctx.pack_path, pack)
        save_freshness_cache(ctx.professor_dir, cache_entries)
        # NOTE: stage2-finalize deliberately does NOT touch the sidecar's
        # acceptance flags. Only stage2-resolve-accept / --keep-provisional may
        # flip proposed -> accepted; application and acceptance are separate
        # machine steps so an unconfirmed proposal can never enter the pack.
        judged = sum(1 for statuses in statuses_by_direction.values()
                     for record in statuses.values()
                     if isinstance(record, dict) and not record.get("cache_hit"))
        emit({
            "status": "ok",
            "professor": ctx.professor,
            "pack_path": str(ctx.pack_path),
            "analysis_md": str(md_path),
            "directions": [{"direction_id": direction_machine_id(d),
                            "collection_key": d.get("collection_key"),
                            "shortlist": len(d.get("gap_shortlist", [])),
                            "blacklist": len(d.get("completed_gap_blacklist", [])),
                            "excluded": len(d.get("gaps_excluded", [])),
                            "resolved": bool(resolved_directions and direction_machine_id(d) in resolved_directions
                                             and resolved_directions[direction_machine_id(d)].get("resolution_type") != "unchanged")}
                           for d in pack_directions],
            "freshness_judged": judged, "freshness_cache_total": len(cache_entries),
            "md_sha256": (md_result or {}).get("sha256"),
            "resolved_directions_applied": bool(resolved_directions),
        })



    def stage2_render_precheck(pack: dict) -> list:
        """Renderability problems a level-only refresh must not try to repair.

        The normal process path owns the corresponding data errors; a refresh that
        would need a missing trusted title simply returns to that path.
        """
        problems = []
        canonical = pack_paper_index(pack)
        for direction in pack.get("directions") or []:
            did = direction_machine_id(direction)
            for key in Stage2PackRefineContext.narrative_later_keys_for(direction):
                record = canonical.get(key) or {}
                if stage2_trusted_paper_title(record, key) is None:
                    problems.append({"direction": did, "kind": "later_paper_title",
                                     "item_key": key})
            allowed = set(pack_direction_relevant_keys(direction))
            narrative = direction.get("narrative") if isinstance(direction.get("narrative"), dict) else {}
            for block in narrative.get("positioning") or []:
                if not isinstance(block, dict):
                    continue
                for kind, key in PLACEHOLDER_RE.findall(block.get("text") or ""):
                    if kind != "P":
                        continue
                    if key not in allowed:
                        problems.append({"direction": did, "kind": "paper_reference_license",
                                         "item_key": key})
                    elif stage2_trusted_paper_title(canonical.get(key), key) is None:
                        problems.append({"direction": did, "kind": "paper_reference_title",
                                         "item_key": key})
        return problems


    def stage2_refresh_payload(args) -> dict:
        if not getattr(args, "preflight_file", None):
            fail("invalid_params", "stage2-refresh-level requires --preflight-file")
        plan, error = read_json_file(Path(args.preflight_file))
        if (error or not isinstance(plan, dict) or plan.get("status") != "ok"
                or not isinstance(plan.get("preflight_inputs"), dict)):
            fail("invalid_params", f"preflight file unreadable or not a preflight payload: "
                                   f"{args.preflight_file}")
        if plan.get("professor") != args.professor:
            fail("invalid_params", "preflight file professor mismatch: "
                                   f"{plan.get('professor')!r} != {args.professor!r}")
        if plan.get("action") != "refresh_level":
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=["preflight_action_changed"],
                      recorded_action=plan.get("action"))
        return plan


    def stage2_refresh_verify_binding(plan: dict, program_root: Path, professor: str,
                                      professor_dir: Path) -> dict:
        """Re-read the same professor transaction and prove the payload still binds."""
        plan_inputs = plan["preflight_inputs"]
        params = plan_inputs.get("params")
        if not isinstance(params, dict):
            soft_exit("needs_refresh", "preflight_inputs_changed", drift=["params"])
        target = read_stage2_target(stage2_target_path(professor_dir), program_root, professor)
        snapshot = read_stage1_professor_entry(program_root, professor_dir, professor, target)
        if target is None or snapshot is None:
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=["target_or_snapshot_missing"])
        current = stage2_preflight_cheap_inputs(
            program_root, professor_dir, professor, target, snapshot, params,
            plan_inputs.get("current_year"))
        drift = stage2_preflight_plan_drift(plan_inputs, current)
        if drift:
            soft_exit("needs_refresh", "preflight_inputs_changed", drift=drift)
        preflight_id = sha256_obj({"professor": plan["professor"],
                                   "preflight_inputs": plan_inputs})
        if plan.get("preflight_id") != preflight_id:
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=["preflight_proof_id"])
        return {"target": target, "snapshot": snapshot, "plan_inputs": plan_inputs}


    def stage2_refresh_guard_drift(record: dict, direction_id: str) -> tuple[str | None, list]:
        """Check the accepted per-direction artifact guards without re-reading PDFs."""
        guards = record.get("artifact_guards")
        if not isinstance(guards, dict):
            return "refresh_requires_process", [f"artifact_guards_missing:{direction_id}"]
        drift = []
        for key, entries in guards.items():
            if not isinstance(entries, dict):
                drift.append(f"artifact_guards_invalid:{direction_id}:{key}")
                continue
            for kind, guard in entries.items():
                if not isinstance(guard, dict):
                    drift.append(f"artifact_guards_invalid:{direction_id}:{key}:{kind}")
                    continue
                reason = stage2_artifact_guard_reason(guard)
                if reason:
                    drift.append(f"{reason}:{direction_id}:{key}:{kind}")
        if drift:
            return "preflight_inputs_changed", drift
        return None, []


    def stage2_refresh_evaluate(ctx: Stage2PackRefineContext, professor_dir: Path,
                                plan: dict, program_root: Path) -> dict:
        """The refresh gate: business sources equal and only levels/format change.

        Any unprovable or changed business source returns the caller to a fresh
        preflight instead of writing a level on top of an unknown baseline.
        """
        pack = ctx.pack
        if stage2_pack_requires_membership_rebuild(pack):
            soft_exit("needs_refresh", "refresh_requires_process",
                      drift=["membership_semantics_rebuild"])
        cache = pack.get("cache") if isinstance(pack.get("cache"), dict) else None
        meta = cache.get("preflight") if isinstance(cache, dict) else None
        if not isinstance(meta, dict):
            soft_exit("needs_refresh", "refresh_requires_process",
                      drift=["preflight_metadata_missing"])
        plan_inputs = plan["preflight_inputs"]
        if meta.get("version") != STAGE2_PREFLIGHT_VERSION:
            soft_exit("needs_refresh", "refresh_requires_process",
                      drift=["preflight_version_changed"])
        if meta.get("resolution_semantics_version") != STAGE2_RESOLUTION_SEMANTICS_VERSION:
            soft_exit("needs_refresh", "refresh_requires_process",
                      drift=["resolution_semantics_changed"])
        if meta.get("params") != plan_inputs.get("params") \
                or meta.get("current_year") != plan_inputs.get("current_year"):
            soft_exit("needs_refresh", "preflight_inputs_changed", drift=["params"])
        if meta.get("program_inputs") != plan_inputs.get("program_inputs"):
            soft_exit("needs_refresh", "preflight_inputs_changed", drift=["program_inputs"])
        if meta.get("accepted_directions_sha256") != sha256_obj(pack.get("directions") or []):
            soft_exit("needs_refresh", "refresh_requires_process",
                      drift=["pack_integrity_mismatch"])
        recorded = meta.get("directions")
        target = read_stage2_target(stage2_target_path(professor_dir), program_root,
                                    ctx.professor)
        snapshot = read_stage1_professor_entry(program_root, professor_dir,
                                               ctx.professor, target)
        if target is None or snapshot is None:
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=["target_or_snapshot_missing"])
        candidate_keys = stage2_candidate_universe(target, snapshot)
        recorded_projection = meta.get("resolution_evidence_projection")
        if not isinstance(recorded_projection, dict):
            soft_exit("needs_refresh", "refresh_requires_process",
                      drift=["resolution_evidence_projection_missing"])
        if observed_source_projection(professor_dir, candidate_keys) != recorded_projection:
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=["resolution_evidence_changed"])
        union_drift = []
        for key, entries in (meta.get("resolution_evidence_guards") or {}).items():
            if not isinstance(entries, dict):
                union_drift.append(f"artifact_guards_invalid:{key}")
                continue
            for kind, guard in entries.items():
                if not isinstance(guard, dict):
                    union_drift.append(f"artifact_guards_invalid:{key}:{kind}")
                    continue
                reason = stage2_artifact_guard_reason(guard)
                if reason:
                    union_drift.append(f"{reason}:{key}:{kind}")
        if union_drift:
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=union_drift)
        accepted_by_key = {direction_machine_id(entry): entry
                           for entry in pack.get("directions") or []
                           if isinstance(entry, dict)}
        grouping = _pack_resolved_grouping(list(accepted_by_key.values()))
        cache_entries = load_freshness_cache(professor_dir)
        observed_levels = {}
        changed_levels = {}
        level_changed = False
        for direction_id in sorted(recorded):
            record = recorded[direction_id]
            if not isinstance(record, dict):
                soft_exit("needs_refresh", "refresh_requires_process",
                          drift=[f"preflight_record_missing:{direction_id}"])
            accepted = accepted_by_key.get(direction_id)
            if accepted is not None \
                    and record.get("freshness_view_fingerprint") != \
                    stage2_freshness_view_fingerprint(accepted, cache_entries):
                soft_exit("needs_refresh", "preflight_inputs_changed",
                          drift=[f"freshness_changed:{direction_id}"])
            for resolved_id, resolved_record in (record.get("resolved_entries") or {}).items():
                resolved = accepted_by_key.get(resolved_id)
                if isinstance(resolved, dict) and isinstance(resolved_record, dict) \
                        and resolved_record.get("freshness_view_fingerprint") != \
                        stage2_freshness_view_fingerprint(resolved, cache_entries):
                    soft_exit("needs_refresh", "preflight_inputs_changed",
                              drift=[f"freshness_changed:{direction_id}:{resolved_id}"])
            keys = stage2_group_consumed_keys(accepted_by_key, grouping, direction_id)
            if record.get("source_projection") != observed_source_projection(
                    professor_dir, keys):
                soft_exit("needs_refresh", "preflight_inputs_changed",
                          drift=[f"source_changed:{direction_id}"])
            guard_code, guard_drift = stage2_refresh_guard_drift(record, direction_id)
            if guard_code:
                soft_exit("needs_refresh", guard_code, drift=guard_drift)
            levels = observed_level_projection(professor_dir, keys)
            if not levels.get("valid"):
                soft_exit("needs_refresh", "refresh_requires_process",
                          drift=[f"analysis_level_unreadable:{direction_id}"])
            recorded_levels = record.get("level_projection")
            if not isinstance(recorded_levels, dict):
                soft_exit("needs_refresh", "refresh_requires_process",
                          drift=[f"level_projection_missing:{direction_id}"])
            if levels.get("values") != recorded_levels:
                level_changed = True
                for key, value in (levels.get("values") or {}).items():
                    if recorded_levels.get(key) != value:
                        changed_levels[key] = value
            observed_levels.update(levels.get("values") or {})
        statistics_stale = (meta.get("statistics_version")
                            != STAGE2_LEVEL_STATISTICS_VERSION)
        if not level_changed and not statistics_stale:
            soft_exit("needs_refresh", "preflight_inputs_changed",
                      drift=["levels_already_current"])
        return {"meta": meta, "levels": observed_levels,
                "changed_levels": changed_levels}


    def cmd_stage2_refresh_level(args) -> None:
        plan = stage2_refresh_payload(args)
        professor = args.professor
        program_root = Path(args.program_root)
        if not getattr(args, "target_file", None):
            fail("invalid_params", "stage2-refresh-level requires --target-file")
        target = read_stage2_target(Path(args.target_file), program_root, professor)
        if target is None:
            fail("invalid_params",
                 f"professor has no selected target state; run contact_targets.py resolve first: {professor}")
        professor_dir = program_root / str(target.get("professor_dir") or "")
        # Pre-lease proof check: the payload must still describe this exact
        # professor transaction before a writer lease is even attempted.
        stage2_refresh_verify_binding(plan, program_root, professor, professor_dir)
        token = uuid.uuid4().hex
        try:
            acquire_local_lease, _release = stage2_lease_owner()
            acquire_local_lease(professor_dir, token, verify_plan=False)
        except ValueError as error:
            if str(error) == "stage2_writer_busy":
                soft_exit("stage2_writer_busy", "stage2_writer_busy",
                          message="另一条 Stage-2 本地写入仍持有该教授的 writer lease；"
                                  "本次零业务写入，稍后重新预检")
            fail("invalid_params", f"cannot acquire the professor writer lease: {error}")
        released = False
        release_error = None
        result = None
        try:
            # Re-prove the payload and the source/level binding under the lease;
            # a drift releases the lease and returns needs_refresh, never writes.
            stage2_refresh_verify_binding(plan, program_root, professor, professor_dir)
            ctx = Stage2PackRefineContext(professor_dir)
            if ctx.professor != professor:
                soft_exit("needs_refresh", "preflight_inputs_changed",
                          drift=["professor_mismatch"])
            gate = stage2_refresh_evaluate(ctx, professor_dir, plan, program_root)
            pack = copy.deepcopy(ctx.pack)
            papers = pack_paper_index(pack)
            updated_papers = {}
            for key, record in papers.items():
                canonical = dict(record) if isinstance(record, dict) else record
                if isinstance(canonical, dict):
                    canonical["analysis_level"] = gate["levels"].get(key)
                updated_papers[key] = canonical
            projection_papers = dict(updated_papers)
            for key, level in gate["levels"].items():
                if key not in projection_papers:
                    projection_papers[key] = {"analysis_level": level}
            updated_meta = stage2_refresh_preflight_metadata(
                gate["meta"], pack, projection_papers)
            directions = [copy.deepcopy(entry) for entry in pack.get("directions") or []]
            render_pack = {"papers": updated_papers, "directions": directions}
            problems = stage2_render_precheck(render_pack)
            if problems:
                soft_exit("needs_refresh", "refresh_requires_process",
                          drift=["render_fields_require_process"], problems=problems)
            state_fingerprint = sha256_obj({
                "professor": pack.get("professor"),
                "directions": {direction_machine_id(d): d.get("input_fingerprint")
                               for d in directions}})
            body, ownership = render_analysis_document(
                ctx, render_pack, state_fingerprint)
            current_pack, pack_error = read_json_file(ctx.pack_path)
            if pack_error or not isinstance(current_pack, dict):
                soft_exit("needs_refresh", "preflight_inputs_changed",
                          drift=["accepted_pack_unreadable"])
            if stage2_pack_content_fingerprint(current_pack) != \
                    stage2_pack_content_fingerprint(pack):
                soft_exit("needs_refresh", "preflight_inputs_changed",
                          drift=["accepted_pack_changed"])
            # Re-check the accepted source guards after rendering: a source can
            # change after the gate but before the managed write. The render is
            # still in memory here, so a drift exits with zero business writes.
            for direction_id in sorted(gate["meta"].get("directions") or {}):
                guard_code, guard_drift = stage2_refresh_guard_drift(
                    gate["meta"]["directions"][direction_id], direction_id)
                if guard_code:
                    soft_exit("needs_refresh", guard_code, drift=guard_drift)
            md_path = professor_dir / ANALYSIS_MD
            old_render = (pack.get("cache") or {}).get("render") or {}
            previous_sha = ((old_render.get(ANALYSIS_MD) or {})
                            .get("sha256") if isinstance(old_render, dict) else None)
            old_render_file = stage2_old_managed_render(md_path)
            if old_render_file.get("binding_valid"):
                old_header = old_render_file.get("header") or {}
                if old_header.get("state_fingerprint") != state_fingerprint:
                    fail("validation_render_stale",
                         "the managed Markdown header state fingerprint does not bind "
                         "the current pack; re-record the old evidence instead of rebinding it",
                         analysis_md=str(md_path))
            old_entry = old_render.get(ANALYSIS_MD) if isinstance(old_render, dict) else None
            if not isinstance(old_entry, dict):
                soft_exit("needs_refresh", "refresh_requires_process",
                          drift=["render_entry_missing"])
            old_ownership = old_entry.get("ownership")
            old_u1 = old_entry.get("u1")
            if not isinstance(old_ownership, dict) or not isinstance(old_u1, dict):
                soft_exit("needs_refresh", "refresh_requires_process",
                          drift=["render_metadata_missing"])
            if old_u1.get("display_version") != STAGE2_U1_DISPLAY_VERSION:
                soft_exit("needs_refresh", "refresh_requires_process",
                          drift=["fixed_evidence_display_update"])
            old_header = old_render_file.get("header")
            manual_edit = (
                old_render_file.get("readable")
                and isinstance(old_header, dict)
                and old_header.get("managed_by") == MANAGED_BY
                and old_render_file.get("body_sha256")
                != old_header.get("render_sha256"))
            if not manual_edit:
                if not old_render_file.get("binding_valid"):
                    fail("validation_render_stale",
                         "the managed analysis cannot prove its old render binding; "
                         "re-record the old evidence instead of refreshing it",
                         analysis_md=str(md_path))
                old_validator, legality_error = stage2_validation_legality(pack)
                if legality_error:
                    fail("validation_render_stale",
                         "the recorded Stage-2 validation state is malformed; "
                         "re-record a raw validator report against the current files",
                         target=str(md_path))
                if old_validator is not None:
                    if old_render_file.get("body_sha256") != old_validator.get("render_sha256") \
                            or old_validator.get("pack_sha256") \
                            != stage2_pack_content_fingerprint(pack):
                        fail("validation_render_stale",
                             "the recorded Stage-2 validation no longer binds the current "
                             "managed render/input pack; re-record a raw validator report too "
                             "against the current files",
                             target=str(md_path))
            decision = None
            if getattr(args, "decision_file", None):
                decision_data, error = read_json_file(Path(args.decision_file))
                if error is None and isinstance(decision_data, dict):
                    decision = decision_data.get("decision")
            try:
                md_result = stage2_accept_managed_body(
                    md_path, body, previous_sha, decision, state_fingerprint,
                    old_render_file)
            except OSError as error:
                fail("stage2_managed_write_failed",
                     f"受管分析 Markdown 写入失败，本轮未接受任何级别或统计：{error}",
                     analysis_md=str(md_path))
            if md_result.get("needs_decision"):
                soft_exit("needs_decision", md_result.get("reason_code") or "manual_markdown_changed",
                          target=md_result.get("target"),
                          existing_sha256=md_result.get("existing_sha256"),
                          new_sha256=md_result.get("new_sha256"),
                          options=["overwrite", "keep_manual", "promote"])
            body_changed = not md_result.get("equivalent")
            cache_block = copy.deepcopy(pack.get("cache") or {})
            render_block = cache_block.get("render")
            render_block = dict(render_block) if isinstance(render_block, dict) else {}
            accepted_sha = md_result.get("sha256") or previous_sha
            if not body_changed \
                    and old_ownership.get("body_sha256") != accepted_sha:
                fail("validation_render_stale",
                     "the accepted ownership map does not bind the retained managed body",
                     analysis_md=str(md_path))
            render_entry = dict(old_entry)
            if body_changed:
                # A new body must carry the ownership map rendered with the same
                # candidate. A retained body keeps its existing ownership map.
                ownership["body_sha256"] = accepted_sha
                render_entry["ownership"] = ownership
            if accepted_sha:
                render_entry["sha256"] = accepted_sha
            render_block[ANALYSIS_MD] = render_entry
            cache_block["render"] = render_block
            cache_block["preflight"] = updated_meta
            updated_pack = dict(pack)
            updated_pack["generated_at"] = now_utc()
            updated_pack["papers"] = updated_papers
            updated_pack["cache"] = cache_block
            # A really changed body or business basis expires the old
            # certification; the raw old report stays untouched on disk.
            updated_pack.pop("validator", None)
            validator_preserved = False
            old_validator = pack.get("validator")
            if isinstance(old_validator, dict) and old_validator.get("schema") == 2:
                current_document = old_render_file["body_sha256"] \
                    if old_render_file.get("binding_valid") else None
                binding_valid = (
                    current_document is not None
                    and current_document == old_validator.get("render_sha256")
                    and old_validator.get("pack_sha256")
                    == stage2_pack_content_fingerprint(pack))
                if not body_changed:
                    if not binding_valid:
                        fail("validation_render_stale",
                             "the recorded Stage-2 validation no longer binds the current "
                             "managed render/input pack and no business change explains it; "
                             "re-record a raw validator report too against the current files",
                             target=str(md_path))
                    carried = dict(old_validator)
                    carried["pack_sha256"] = stage2_pack_content_fingerprint(updated_pack)
                    updated_pack["validator"] = carried
                    validator_preserved = True
            # The pack is the acceptance record: the statistics marker and the
            # new level projections only become durable with this write, and a
            # failed write leaves the command explicitly unfinished (never a
            # fabricated cross-file rollback or success marker).
            try:
                atomic_json(ctx.pack_path, updated_pack)
            except OSError as error:
                fail("stage2_pack_write_failed",
                     f"受管分析 Markdown 已接受但输入包写入失败，本轮未完成：{error}",
                     analysis_md=str(md_path), pack_path=str(ctx.pack_path))
            result = {
                "status": "ok",
                "action": "refresh_level",
                "professor": professor,
                "pack_path": str(ctx.pack_path),
                "analysis_md": str(md_path),
                "md_written": bool(md_result.get("written")),
                "md_sha256": md_result.get("sha256"),
                "changed_levels": gate["changed_levels"],
                "validator_preserved": validator_preserved,
            }
        finally:
            try:
                _acquire, release_local_lease = stage2_lease_owner()
                release_local_lease(professor_dir, token)
                released = True
            except (ValueError, OSError) as error:
                release_error = f"{type(error).__name__}: {error}"
                # Report on every exit path (including soft_exit/fail) here:
                # after those exits the code below is never reached.
                print(f"stage2-refresh-level: lease release failed: {release_error}",
                      file=sys.stderr)
        if result is not None:
            result["lease_released"] = released
            if release_error:
                # Never claim a release that did not happen.
                result["lease_release_error"] = release_error
            emit(result)


    return types.SimpleNamespace(
        stage2_preflight_plan_drift=stage2_preflight_plan_drift,
        stage2_finalize_preflight_plan=stage2_finalize_preflight_plan,
        stage2_pack_requires_membership_rebuild=stage2_pack_requires_membership_rebuild,
        stage2_old_pack_gap_statuses=stage2_old_pack_gap_statuses,
        stage2_render_state=stage2_render_state,
        stage2_require_paper_reference_titles=stage2_require_paper_reference_titles,
        stage2_body_without_generation_time=stage2_body_without_generation_time,
        stage2_old_managed_render=stage2_old_managed_render,
        stage2_accept_managed_body=stage2_accept_managed_body,
        cmd_stage2_finalize=cmd_stage2_finalize,
        cmd_stage2_refresh_level=cmd_stage2_refresh_level,
    )
