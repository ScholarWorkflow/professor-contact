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

import types
from pathlib import Path


def build(*, Stage2Context,
          Stage2PackRefineContext,
          atomic_json,
          emit,
          fail,
          soft_exit,
          now_utc,
          sha256_text,
          sha256_obj,
          read_json_file,
          direction_machine_id,
          pack_paper_index,
          pack_direction_relevant_keys,
          split_frontmatter,
          managed_write,
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
          stage2_pack_content_fingerprint,
          validate_freshness_results,
          validate_narrative,
          build_direction_pack,
          render_analysis_md,
          MANAGED_BY,
          INPUT_PACK_SCHEMA,
          DIRECTION_IDENTITY_VERSION,
          INPUT_PACK_KIND,
          RESOLVED_DIRECTION_SCHEMA,
          ANALYSIS_MD,
          STAGE2_RESOLUTION_SEMANTICS_VERSION,
          PLACEHOLDER_RE):
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
            return True
        if meta.get("resolution_semantics_version") != STAGE2_RESOLUTION_SEMANTICS_VERSION:
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

    def stage2_render_state(pack: dict) -> dict:
        """The exact pack content the managed analysis Markdown displays.

        Used to decide whether a finalized pack must re-render: a membership,
        reference-licence, narrative, gap, name or trusted-title change is visible
        even when no new model job was needed, while a metadata-only rewrite stays
        unchanged.
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
        # `pdf_available` feeds the managed header's full-text/abstract counts, so a
        # PDF-availability change is display-relevant even when the analysis path
        # stays the same.
        papers_state = {
            key: {field: (papers.get(key) or {}).get(field)
                  for field in ("title", "year", "authorship", "analysis_file",
                                "pdf_available")}
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

    def cmd_stage2_finalize(args) -> None:
        ctx = Stage2Context(Path(args.facts))
        preflight_plan, preflight_target, preflight_snapshot = \
            stage2_finalize_preflight_plan(args, ctx)
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
        old_directions = {direction_machine_id(e): e
                          for e in (ctx.pack or {}).get("directions", [])}
        old_render = ((ctx.pack or {}).get("cache") or {}).get("render", {})
        # A pack accepted under older membership semantics must rebuild its
        # authoritative membership from the current facts: only the narrative /
        # freshness work may be reused, never the old `supporting_item_keys`.
        pack_needs_rebuild = stage2_pack_requires_membership_rebuild(ctx.pack)
        pack_directions = []
        fresh_papers: dict = {}
        for plan in ctx.direction_plans:
            old_entry = old_directions.get(plan["did"])
            if plan["reuse"] and not pack_needs_rebuild:
                reused_entry = old_entry
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
            record = fresh_papers.get(key) or pack_paper_index(ctx.pack or {}).get(key)
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
            for old_entry in (ctx.pack or {}).get("directions", []):
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
                pack_directions.append(old_entry)
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
        old_papers = pack_paper_index(ctx.pack or {})

        def _current_paper_record(key: str) -> dict | None:
            """Current-facts record, filled from the old pack only where facts lack it.

            Plan 3.1.3: the current facts are the trusted source for every
            displayed/consumed paper field; the old cache may only fill values the
            current facts do not state, and never overrides a current value.
            """
            paper = ctx.papers.get(key)
            if paper is None:
                return None
            previous = old_papers.get(key)
            record = dict(previous) if isinstance(previous, dict) else {}
            record["item_key"] = key
            for field, value in (("title", paper.get("title")), ("year", paper.get("year")),
                                 ("authorship", paper.get("authorship")),
                                 ("analysis_file", paper.get("analysis_file"))):
                if value is not None:
                    record[field] = value
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
                    papers_map[key] = record
        cache_entries = dict(ctx.cache)
        for ckey, statuses in statuses_by_direction.items():
            for gap_id, record in statuses.items():
                if isinstance(record, dict) and not record.get("cache_hit"):
                    cache_entries[gap_id] = {k: v for k, v in record.items() if k != "cache_hit"}
        render_pack = {"papers": papers_map, "directions": pack_directions}
        for direction in pack_directions:
            stage2_require_later_paper_titles(ctx, direction, render_pack)
            stage2_require_paper_reference_titles(ctx.papers, render_pack, direction)
        # A display-only rename, a membership/reference correction or a changed
        # narrative/gap display must re-render the analysis Markdown WITHOUT
        # requiring new model work. Compare the exact displayed content so a
        # metadata-only rewrite (timestamp/cache) stays a no-render no-op.
        render_changed = ctx.pack is None or stage2_render_state(
            render_pack) != stage2_render_state(ctx.pack)
        md_path = ctx.professor_dir / ANALYSIS_MD
        md_result = None
        if needed_keys or not ctx.pack or render_changed:
            body = render_analysis_md(ctx, render_pack, state_fingerprint)
            md_result = managed_write(md_path, body, state_fingerprint,
                                      old_render.get(ANALYSIS_MD, {}).get("sha256"), decision)
            if md_result.get("needs_decision"):
                soft_exit("needs_decision", md_result["reason_code"],
                          target=md_result.get("target"),
                          existing_sha256=md_result.get("existing_sha256"),
                          new_sha256=md_result.get("new_sha256"),
                          options=["overwrite（覆盖为状态版本）", "keep_manual（保留手改，不作为流程输入）",
                                   "promote（把要保留的内容经 selection.note 或 profile 写进状态后再渲染）"])
        pack = {
            "schema": INPUT_PACK_SCHEMA, "kind": INPUT_PACK_KIND,
            "identity_version": DIRECTION_IDENTITY_VERSION,
            "managed_by": MANAGED_BY, "generated_at": now_utc(),
            "professor": ctx.professor, "professor_dir": str(ctx.professor_dir),
            "papers": papers_map,
            "directions": pack_directions,
            "cache": {"render": {ANALYSIS_MD: {"sha256": (md_result or {}).get("sha256") or old_render.get(ANALYSIS_MD, {}).get("sha256")}}},
        }
        if resolved_directions:
            # Each raw source→target row stores the ORIGINAL facts fingerprint of
            # its provisional direction, so the facts-bound refine entry can prove
            # this accepted pack (including an already-merged source, which owns no
            # final direction entry) still matches the current facts.
            raw_provisional_fingerprints = {
                plan["did"]: plan["fingerprint"] for plan in ctx.direction_plans}
            pack["resolved_directions"] = {
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
        if preflight_plan is not None:
            pack["cache"]["preflight"] = stage2_preflight_metadata(
                program_root=ctx.program_root, professor_dir=ctx.professor_dir,
                target=preflight_target, snapshot_entry=preflight_snapshot,
                pack_directions=pack_directions,
                params=preflight_plan["preflight_inputs"]["params"],
                current_year=ctx.current_year, ctx=ctx, cache_entries=cache_entries)
        # Validator lifecycle (plan 3.4.1): the old record is carried over only
        # when NOTHING the validator certified changed — no new model work, no
        # membership/reference/narrative re-render and no old-semantics rebuild —
        # and its recorded pack/render binding still describes the actual files.
        # A changed business version silently expires the old certification (the
        # new version starts at round 1, raw old reports stay untouched); with NO
        # business change an invalid old binding is an evidence error and must be
        # rejected before writing, never "restored" by re-binding the hashes.
        old_validator = (ctx.pack or {}).get("validator")
        if isinstance(old_validator, dict) and old_validator.get("schema") == 2:
            current_document = None
            try:
                document_text = md_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                document_text = ""
            header, document_body = split_frontmatter(document_text)
            if isinstance(header, dict) and header.get("managed_by") == MANAGED_BY:
                current_document = sha256_text(document_body)
            business_changed = bool(needed_keys) or pack_needs_rebuild or render_changed
            binding_valid = (
                current_document == old_validator.get("render_sha256")
                and old_validator.get("pack_sha256")
                == stage2_pack_content_fingerprint(ctx.pack or {}))
            if not business_changed:
                if not binding_valid:
                    fail("validation_render_stale",
                         "the recorded Stage-2 validation no longer binds the current managed "
                         "render/input pack and no business change explains it; re-record a "
                         "raw validator report too against the current files",
                         target=str(md_path))
                carried = dict(old_validator)
                carried["pack_sha256"] = stage2_pack_content_fingerprint(pack)
                pack["validator"] = carried
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
        stage2_preflight_plan_drift=stage2_preflight_plan_drift,
        stage2_finalize_preflight_plan=stage2_finalize_preflight_plan,
        stage2_pack_requires_membership_rebuild=stage2_pack_requires_membership_rebuild,
        stage2_old_pack_gap_statuses=stage2_old_pack_gap_statuses,
        stage2_render_state=stage2_render_state,
        stage2_require_paper_reference_titles=stage2_require_paper_reference_titles,
        cmd_stage2_finalize=cmd_stage2_finalize,
        stage2_trusted_paper_title=stage2_trusted_paper_title,
        stage2_require_later_paper_titles=stage2_require_later_paper_titles,
    )
