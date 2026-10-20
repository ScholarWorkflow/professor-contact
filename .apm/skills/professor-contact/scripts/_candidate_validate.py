#!/usr/bin/env python3
"""Candidate validation helper module for ``contact_state.py``.

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
import types





def build(*, ANCHORABLE,
          fail,
          _direction_slices,
          direction_machine_id,
          _stage3_render,
          now_utc,
          CANDIDATES_MD):
    def _validate_candidate_core(candidate: Any, path: Path,
                                 gap_index: dict, blacklist: dict,
                                 paper_index: dict, direction_ids: list[str],
                                 kind: str,
                                 paper_slices: dict | None = None) -> dict:
        """Validate one idea against exact (direction_id, item_key, gap_id) join
        indexes and return the normalized candidate record (issue #8 §5).

        `direction_ids` is the ONLY provenance the candidate may claim: an ordinary
        candidate gets exactly its own direction, a cross candidate gets the sorted
        participant group. Gap refs join through the full triple, so a valid
        (item_key, gap_id) from another direction is rejected when paired with the
        wrong direction_id.
        """
        if not isinstance(candidate, dict):
            fail("invalid_result_json", f"{path}: candidates[] must be objects")
        if candidate.get("id") is not None and not isinstance(candidate.get("id"), str):
            fail("invalid_result_json", f"{path}: candidate id must be a string")
        cid = (candidate.get("id") or "").strip()
        if not cid:
            fail("invalid_result_json", f"{path}: candidate id required: {cid!r}")
        for field in ("title", "one_liner", "research_question", "fit_note", "why_recommended"):
            if candidate.get(field) is not None and not isinstance(candidate.get(field), str):
                fail("invalid_result_json", f"{path}: candidate {cid} field {field} must be a string")
        if not (candidate.get("research_question") or "").strip():
            fail("invalid_result_json",
                 f"{path}: candidate {cid} 缺非空研究问题（求知式）；纯交付物候选应并入主候选而非单列")
        raw_ids = candidate.get("direction_ids")
        if not isinstance(raw_ids, list) or [x.strip() if isinstance(x, str) else None
                                             for x in raw_ids] != direction_ids:
            fail("invalid_result_json",
                 f"{path}: candidate {cid} direction_ids must be exactly {direction_ids} "
                 f"(got {raw_ids!r})")
        origin = candidate.get("origin")
        if origin is not None and (not isinstance(origin, str) or origin.strip()
                                   not in ("generated", "user_refined")):
            fail("invalid_result_json",
                 f"{path}: candidate {cid} origin must be 'generated' or 'user_refined'")
        anchor_notes = candidate.get("anchor_notes") or {}
        if not isinstance(anchor_notes, dict):
            fail("invalid_result_json", f"{path}: candidate {cid} anchor_notes must be an object")
        for note_key in ("remaining_focus", "difference_point"):
            if note_key in anchor_notes and not isinstance(anchor_notes[note_key], str):
                fail("invalid_result_json", f"{path}: candidate {cid} anchor_notes.{note_key} must be a string")
        if "unverified" in anchor_notes and not isinstance(anchor_notes["unverified"], bool):
            fail("invalid_result_json", f"{path}: candidate {cid} anchor_notes.unverified must be boolean")
        for field in ("points", "red_lines", "tension_points"):
            value = candidate.get(field) or []
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                fail("invalid_result_json", f"{path}: candidate {cid} field {field} must be a string list")
        raw_refs = candidate.get("gap_refs") or []
        if not isinstance(raw_refs, list) or not all(isinstance(pair, dict) for pair in raw_refs):
            fail("invalid_result_json", f"{path}: candidate {cid} gap_refs must be an object list "
                                        "of {direction_id, item_key, gap_id} triples")
        gap_refs = []
        seen_triples = set()
        for pair in raw_refs:
            did = pair.get("direction_id")
            key = (did, pair.get("item_key"), pair.get("gap_id"))
            if key in seen_triples:
                fail("invalid_result_json", f"{path}: candidate {cid} contains duplicate gap {key}")
            seen_triples.add(key)
            if did not in direction_ids:
                fail("unknown_reference_id",
                     f"{path}: candidate {cid} gap {key} cites a direction outside its provenance")
            in_pool = key in gap_index
            in_blacklist = key in blacklist
            if not in_pool and not in_blacklist:
                fail("unknown_reference_id",
                     f"{path}: candidate {cid} gap {key} is not an exact (direction_id, item_key, "
                     "gap_id) join into the cited direction's slice")
            if in_pool:
                status = gap_index[key].get("status")
                if status not in ANCHORABLE:
                    fail("blacklisted_gap_anchor",
                         f"{path}: candidate {cid} anchors {key} status={status}")
                if status == "partial" and not (anchor_notes.get("remaining_focus") or "").strip():
                    fail("invalid_result_json",
                         f"{path}: candidate {cid} partial anchor needs anchor_notes.remaining_focus")
                if status == "unknown" and not anchor_notes.get("unverified"):
                    fail("invalid_result_json",
                         f"{path}: candidate {cid} unknown anchor needs anchor_notes.unverified=true")
            else:
                if not (anchor_notes.get("difference_point") or "").strip():
                    fail("blacklisted_gap_anchor",
                         f"{path}: candidate {cid} uses done_by_self gap {key} without "
                         "my_extension difference_point")
            gap_refs.append({"direction_id": did, "item_key": key[1], "gap_id": key[2],
                             "done_by_self": in_blacklist})
        raw_papers = candidate.get("papers") or []
        if not isinstance(raw_papers, list) or not all(isinstance(paper, dict) for paper in raw_papers):
            fail("invalid_result_json", f"{path}: candidate {cid} papers must be an object list")
        papers = []
        seen_papers = set()
        for paper in raw_papers:
            item_key = paper.get("item_key")
            source = paper_index.get(item_key)
            if not source:
                fail("unknown_paper_id", f"{path}: candidate {cid} paper {item_key} outside package")
            if item_key in seen_papers:
                fail("invalid_result_json", f"{path}: candidate {cid} contains duplicate paper {item_key}")
            seen_papers.add(item_key)
            paper_ids = paper.get("direction_ids")
            if paper_ids is None:
                paper_ids = list(direction_ids)
            else:
                if not isinstance(paper_ids, list) or not paper_ids \
                        or any(not isinstance(x, str) or x.strip() not in direction_ids
                               for x in paper_ids):
                    fail("invalid_result_json",
                         f"{path}: candidate {cid} paper {item_key} direction_ids must be a non-empty "
                         f"subset of {direction_ids}")
                paper_ids = sorted({x.strip() for x in paper_ids})
                # Each cited direction must actually ALLOW the paper: the item_key
                # has to live in that direction's own slice (issue #8 §5).
                for cited in paper_ids:
                    if paper_slices is not None and item_key not in paper_slices.get(cited, ()):
                        fail("unknown_paper_id",
                             f"{path}: candidate {cid} paper {item_key} is not part of direction "
                             f"{cited!r}'s slice, so it cannot carry {cited!r} provenance")
            papers.append({"item_key": item_key, "direction_ids": paper_ids,
                           "title": source.get("title"), "year": source.get("year"),
                           "authorship": source.get("authorship"),
                           "role": (paper.get("role") or "").strip(),
                           "fit_note": (paper.get("fit_note") or "").strip()})
        has_author_gap = any(not g["done_by_self"] for g in gap_refs)
        anchor_type = "author_future_work" if gap_refs and has_author_gap else (
            "my_extension" if gap_refs else "none")
        return {
            "id": cid,
            "kind": kind,
            "direction_ids": list(direction_ids),
            "origin": (origin or "generated").strip(),
            "title": (candidate.get("title") or "").strip(),
            "one_liner": (candidate.get("one_liner") or "").strip(),
            "research_question": candidate.get("research_question").strip(),
            "points": [str(x) for x in (candidate.get("points") or [])],
            "gap_refs": gap_refs,
            "anchor_type": anchor_type,
            "anchor_notes": anchor_notes,
            "papers": papers,
            "fit": candidate.get("fit") if candidate.get("fit") in ("high", "partial", "weak", "null") else "null",
            "fit_note": (candidate.get("fit_note") or "").strip(),
            "red_lines": [str(x) for x in (candidate.get("red_lines") or [])],
            "why_recommended": (candidate.get("why_recommended") or "").strip(),
            "tension_points": [str(x) for x in (candidate.get("tension_points") or [])]}

    def validate_candidate_result(pack: dict, pack_direction: dict, data: Any, path: Path) -> dict:
        """Validate one direction's stage-3 result against the input pack (v2).

        The result must carry the job's direction_id, and every candidate must
        claim exactly that direction's provenance with exact-triple gap refs. The
        optional 3-5 quota now ALSO applies to refined mode: the calibrated user
        idea itself becomes one selectable candidate (origin=user_refined).
        """
        if not isinstance(data, dict) or data.get("schema") != 2 or data.get("kind") != "candidates":
            fail("invalid_result_json", f"{path}: schema/kind must be 2/candidates")
        did = direction_machine_id(pack_direction)
        if data.get("direction_id") != did:
            fail("invalid_result_json",
                 f"{path}: direction_id {data.get('direction_id')!r} does not match the job direction {did!r}")
        mode = data.get("mode")
        if mode not in ("refined", "generated"):
            fail("invalid_result_json", f"{path}: mode must be refined|generated")
        if mode == "refined" and not (pack_direction.get("user_note") or "").strip():
            fail("invalid_result_json", f"{path}: refined mode without user note")
        gap_index, blacklist, paper_index = _direction_slices(pack, pack_direction)
        refined = data.get("refined")
        if mode == "refined":
            if not isinstance(refined, dict):
                fail("invalid_result_json", f"{path}: refined block required in refined mode")
            if not isinstance(refined.get("idea_zh"), str) or not refined["idea_zh"].strip():
                fail("invalid_result_json", f"{path}: refined.idea_zh required")
            for field in ("calibration", "variants", "mismatches"):
                value = refined.get(field) or []
                if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                    fail("invalid_result_json", f"{path}: refined.{field} must be a string list")
            refined_gap_ids = refined.get("gap_ids") or []
            if not isinstance(refined_gap_ids, list) or not all(isinstance(pair, dict) for pair in refined_gap_ids):
                fail("invalid_result_json", f"{path}: refined.gap_ids must be an object list")
            for pair in refined_gap_ids:
                key = (pair.get("item_key"), pair.get("gap_id"))
                if key not in {(i, g) for (d, i, g) in gap_index} \
                        and key not in {(i, g) for (d, i, g) in blacklist}:
                    fail("unknown_reference_id", f"{path}: refined gap {key} outside package")
        candidates = data.get("candidates")
        if not isinstance(candidates, list):
            fail("invalid_result_json", f"{path}: candidates must be a list")
        if not 3 <= len(candidates) <= 5:
            fail("invalid_result_json", f"{path}: {mode} mode needs 3-5 selectable candidates")
        checked = []
        seen_ids = set()
        user_refined_count = 0
        for candidate in candidates:
            single = _validate_candidate_core(candidate, path, gap_index, blacklist,
                                              paper_index, [did], "direction")
            cid = single["id"]
            if cid in seen_ids:
                fail("invalid_result_json", f"{path}: candidate id required and unique: {cid!r}")
            seen_ids.add(cid)
            if single["origin"] == "user_refined":
                user_refined_count += 1
            checked.append(single)
        if mode == "refined" and user_refined_count != 1:
            fail("invalid_result_json",
                 f"{path}: refined mode needs exactly one origin='user_refined' candidate "
                 f"(found {user_refined_count})")
        if mode == "refined":
            refined_checked = {
                "core_intent": (refined.get("core_intent") or "").strip(),
                "calibration": [str(x) for x in (refined.get("calibration") or [])],
                "idea_zh": refined.get("idea_zh").strip(),
                "variants": [str(x) for x in (refined.get("variants") or [])],
                "mismatches": [str(x) for x in (refined.get("mismatches") or [])],
                "gap_ids": [{"item_key": p.get("item_key"), "gap_id": p.get("gap_id")}
                            for p in (refined.get("gap_ids") or [])],
            }
        else:
            refined_checked = None
        priority = data.get("priority") or ""
        if not isinstance(priority, str):
            fail("invalid_result_json", f"{path}: priority must be a string")
        return {"direction_id": did, "mode": mode, "refined": refined_checked,
                "candidates": checked, "priority": priority.strip()}

    def validate_cross_result(pack: dict, group: dict, data: Any, path: Path) -> dict:
        """Validate one explicit cross-direction group's result (issue #8 §6).

        Every candidate must cite the exact sorted participant group, join gaps
        through the full triple against each cited direction's own slice, key
        papers once by item_key, and be GROUNDED in every participant: a candidate
        labeled A+B but carrying only A evidence is rejected.
        """
        if not isinstance(data, dict) or data.get("schema") != 2 \
                or data.get("kind") != "cross_candidates":
            fail("invalid_result_json", f"{path}: schema/kind must be 2/cross_candidates")
        ids = group["direction_ids"]
        if data.get("group_id") != group["group_id"] or data.get("direction_ids") != ids:
            fail("invalid_result_json",
                 f"{path}: group identity mismatch (expected {group['group_id']} / {ids})")
        candidates = data.get("candidates")
        if not isinstance(candidates, list):
            fail("invalid_result_json", f"{path}: candidates must be a list")
        if not 1 <= len(candidates) <= 3:
            fail("invalid_result_json", f"{path}: cross-direction groups need 1-3 candidates")
        by_id = {direction_machine_id(d): d for d in (pack or {}).get("directions") or []}
        union_gap: dict = {}
        union_blacklist: dict = {}
        union_papers: dict = {}
        paper_slices: dict = {}
        for pid in ids:
            p_gaps, p_blacklist, p_papers = _direction_slices(pack, by_id[pid])
            union_gap.update(p_gaps)
            union_blacklist.update(p_blacklist)
            union_papers.update(p_papers)
            paper_slices[pid] = set(p_papers)
        checked = []
        seen_ids = set()
        for candidate in candidates:
            single = _validate_candidate_core(candidate, path, union_gap, union_blacklist,
                                              union_papers, ids, "cross_direction",
                                              paper_slices=paper_slices)
            cid = single["id"]
            if cid in seen_ids:
                fail("invalid_result_json", f"{path}: candidate id required and unique: {cid!r}")
            seen_ids.add(cid)
            grounded = {ref["direction_id"] for ref in single["gap_refs"]}
            grounded |= {pid for paper in single["papers"]
                         for pid in paper.get("direction_ids") or []}
            missing = [pid for pid in ids if pid not in grounded]
            if missing:
                fail("unknown_reference_id",
                     f"{path}: cross-direction candidate {cid} has no grounded evidence "
                     f"from participant(s) {missing}")
            checked.append(single)
        return {"group_id": group["group_id"], "direction_ids": list(ids),
                "candidates": checked}

    def render_candidates_md(professor: str, category: str, direction_entries: list,
                             profile_fp: str | None, state_fingerprint: str,
                             professor_dir: Path, cross_groups: list | None = None) -> str:
        return _stage3_render.render_candidates_md(
            professor, category, direction_entries, profile_fp, state_fingerprint,
            professor_dir, cross_groups, now_utc=now_utc)

    def render_candidates_overview(entries: list, program_root: Path,
                                   cross_groups: list | None = None) -> str:
        return _stage3_render.render_candidates_overview(
            entries, program_root, cross_groups,
            now_utc=now_utc, candidates_md=CANDIDATES_MD)

    return types.SimpleNamespace(
                _validate_candidate_core=_validate_candidate_core,
                validate_candidate_result=validate_candidate_result,
                validate_cross_result=validate_cross_result,
                render_candidates_md=render_candidates_md,
                render_candidates_overview=render_candidates_overview,
    )
