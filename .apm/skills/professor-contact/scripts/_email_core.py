#!/usr/bin/env python3
"""Email core helper module for ``contact_state.py``.

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


def build(*, fail,
          direction_machine_id,
          direction_papers,
          EMAIL_SOURCE_HASH_FIELDS,
          sha256_obj):
    def email_source_hash(entry: dict) -> str:
        """Return the canonical Stage-4 → Stage-5 fact hash for one email row."""
        return sha256_obj({key: entry[key] for key in EMAIL_SOURCE_HASH_FIELDS})

    def compile_email_entry(pack: dict, state_direction: dict, pack_direction: dict,
                            idea: dict, note: str, program_root: Path,
                            profile_fp: str | None, papers_override: list[str] | None = None,
                            contact_evidence: dict | None = None,
                            group_entry: dict | None = None,
                            participant_directions: list[dict] | None = None) -> dict:
        """Compile one v2 email entry (issue #8 §8.2).

        Identity: direction_ids provenance (sorted, so A+B == B+A) and an email_id
        built from the canonical direction scope + idea id — never the
        collection_key. A cross-direction idea joins evidence against the UNION of
        its participants' slices; every gap row keeps the direction_ids union that
        actually contains it, and shared papers appear once by item_key."""
        # A cross-direction idea joins evidence against the UNION of its
        # participants' slices (owner included); per-direction ideas keep the
        # single-slice indexes. Duplicate (item_key, gap_id) identities resolve to
        # their first occurrence in direction_ids order — never re-invented.
        slice_directions = participant_directions or [pack_direction]
        direction_ids = sorted(idea.get("direction_ids")
                               or [pack_direction.get("direction_id")
                                   or direction_machine_id(pack_direction)])
        gap_records: dict = {}
        blacklist: dict = {}
        paper_meta: dict = {}
        for slice_direction in slice_directions:
            for gap in slice_direction.get("gap_shortlist", []) + slice_direction.get("gaps_excluded", []):
                gap_records.setdefault((gap["item_key"], gap["gap_id"]), gap)
            for banned in slice_direction.get("completed_gap_blacklist", []):
                blacklist.setdefault((banned["item_key"], banned["gap_id"]), banned)
            for paper in direction_papers(pack, slice_direction):
                paper_meta.setdefault(paper["item_key"], paper)
        for slice_direction in slice_directions:
            for gap in slice_direction.get("gap_shortlist", []) + slice_direction.get("gaps_excluded", []):
                paper_meta.setdefault(gap["item_key"], {
                    "item_key": gap["item_key"], "title": gap.get("paper_title"),
                    "year": gap.get("paper_year"), "authorship": gap.get("authorship")})
        papers_out = []
        candidate_papers = idea.get("papers") or []
        if papers_override:
            by_key = {paper.get("item_key"): paper for paper in candidate_papers}
            candidate_papers = [by_key[key] for key in papers_override]
        for paper in candidate_papers:
            meta = paper_meta.get(paper.get("item_key"))
            if not meta:
                fail("unknown_paper_id", f"candidate paper outside input pack: {paper.get('item_key')}")
            papers_out.append({"item_key": meta["item_key"],
                               "direction_ids": sorted(paper.get("direction_ids")
                                                       or [pack_direction.get("direction_id")
                                                           or direction_machine_id(pack_direction)]),
                               "title": meta.get("title"),
                               "year": meta.get("year"), "authorship": meta.get("authorship"),
                               "fit_note": paper.get("fit_note") or ""})
        gaps_out = []
        for ref in idea.get("gap_refs") or []:
            key = (ref.get("item_key"), ref.get("gap_id"))
            gap = gap_records.get(key)
            if gap:
                status = gap.get("status")
                email_use = ("remaining_only" if status == "partial" else
                             "anchor_with_caveat" if status == "unknown" else "anchor")
                gaps_out.append({
                    "item_key": gap["item_key"], "gap_id": gap["gap_id"],
                    "direction_id": ref.get("direction_id"),
                    "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                    "quote": gap.get("quote"), "translation_zh": gap.get("translation_zh"),
                    "source": gap.get("source"), "page": gap.get("page"),
                    "status": status, "evidence": gap.get("evidence"),
                    "confidence": gap.get("confidence"),
                    "completed_part": gap.get("completed_part"),
                    "remaining_gap": gap.get("remaining_gap"),
                    "email_use": email_use,
                     "zotero_key": gap["item_key"]})
                continue
            done = blacklist.get(key)
            if done:
                gaps_out.append({
                    "item_key": done["item_key"], "gap_id": done["gap_id"],
                    "direction_id": ref.get("direction_id"),
                    "paper_title": done.get("paper_title"), "paper_year": done.get("paper_year"),
                    "quote": done.get("quote_trunc"), "translation_zh": done.get("translation_zh"),
                    "source": None, "page": None,
                    "status": "done_by_self", "evidence": done.get("evidence"),
                    "confidence": done.get("confidence"),
                    "completed_part": None, "remaining_gap": None,
                    "email_use": "extension_context_only",
                     "zotero_key": done["item_key"]})
                continue
            fail("unknown_reference_id", f"candidate gap outside input pack: {key}")
        if group_entry:
            red_lines = []
            seen_red = set()
            for slice_direction in slice_directions:
                for red in slice_direction.get("red_lines") or []:
                    marker = (red.get("scope"), red.get("text"))
                    if marker not in seen_red:
                        seen_red.add(marker)
                        red_lines.append(red)
        else:
            red_lines = list(pack_direction.get("red_lines") or [])
        candidate_red = idea.get("red_lines") or []
        for text in candidate_red:
            red_lines.append({"scope": "candidate", "text": text,
                              "banned_phrases": idea.get("banned_phrases") or []})
        primary = slice_directions[0]
        narrative = primary.get("narrative") or {}
        positioning = [block.get("text", "") for block in narrative.get("positioning", [])]
        for slice_direction in slice_directions[1:]:
            narrative_other = slice_direction.get("narrative") or {}
            for block in narrative_other.get("positioning", []):
                text = block.get("text", "")
                if text and text not in positioning:
                    positioning.append(text)
        allowed = {"user_note", f"idea:{idea.get('id')}", "profile.interest", "template"}
        for paper in papers_out:
            allowed.add(f"paper:{paper['item_key']}")
        for gap in gaps_out:
            allowed.add(f"gap:{gap['gap_id']}")
            allowed.add(f"later:{gap['item_key']}")
        idea_block = {"id": idea.get("id"), "title": idea.get("title"),
                      "idea_zh": idea.get("idea_zh") or ""}
        email_id = f"{pack.get('professor')}::{'+'.join(direction_ids)}::{idea.get('id')}"
        anchorable_gaps = [g for g in gaps_out if g["email_use"] in ("anchor", "remaining_only", "anchor_with_caveat")]
        entry = {
            "email_id": email_id,
            "professor": pack.get("professor"),
            "professor_dir": pack.get("professor_dir"),
            "direction_ids": direction_ids,
            "directions": [{"direction_id": direction_machine_id(d),
                            "name_ja": d.get("name_ja"), "name_zh": d.get("name_zh")}
                           for d in slice_directions],
            "name_ja": primary.get("name_ja"), "name_zh": primary.get("name_zh"),
            "collection_key": primary.get("collection_key"),
            "idea": idea_block,
            "user_note": primary.get("user_note") or "",
            "papers": papers_out,
            "gaps": gaps_out,
            "anchorable_gaps": [g["gap_id"] for g in anchorable_gaps],
            "red_lines": red_lines,
            "soft_materials": {"credibility": primary.get("credibility"),
                               "positioning": positioning},
            "profile": {"fingerprint": profile_fp, "fields": idea.get("_profile_fields") or {}},
            "allowed_sources": sorted(allowed),
            "fingerprints": {"input": pack_direction.get("input_fingerprint"),
                             "profile": profile_fp,
                             "candidate_state": idea.get("_state_fingerprint")},
            "user_supplement": note or "",
            "contact_evidence": contact_evidence,
            "cross_direction": (
                {"group_id": group_entry.get("group_id"),
                 "direction_ids": list(group_entry.get("direction_ids") or []),
                 "direction_fingerprints": dict(group_entry.get("direction_fingerprints") or {})}
                if group_entry else None),
        }
        # contact_evidence is a fact field (the frozen recipient snapshot), so it
        # belongs in the pack integrity hash: a refrozen snapshot always yields a
        # new source_hash, never a silent in-place substitution. cross_direction
        # joins it so a re-participated idea re-hashes too.
        entry["source_hash"] = email_source_hash(entry)
        return entry

    def validate_papers_override(idea: dict, override: Any, context: str) -> list[str] | None:
        """Validate the user-selected paper order without accepting metadata."""
        if override is None:
            return None
        if not isinstance(override, list):
            fail("invalid_papers_override", f"{context}: papers_override must be a list of item keys")
        if not override:
            return None
        if any(not isinstance(key, str) or not key.strip() for key in override):
            fail("invalid_papers_override", f"{context}: papers_override entries must be non-empty strings")
        if len(set(override)) != len(override):
            fail("invalid_papers_override", f"{context}: papers_override contains duplicate item keys")
        allowed = {paper.get("item_key") for paper in idea.get("papers") or []}
        unknown = [key for key in override if key not in allowed]
        if unknown:
            fail("invalid_papers_override", f"{context}: item keys outside candidate papers: {unknown}")
        return list(override)

    def _selection_direction_ids(select: dict, packs: dict) -> tuple[list[str] | None, str | None]:
        """Resolve a selection entry's canonical direction_ids (issue #8 §8.1).

        v2 entries carry direction_id/direction_ids directly. The deprecated
        collection_key path resolves ONLY through the pack's exact machine mapping
        (unique collection_key → direction_id); ambiguous or missing mappings fail
        closed with legacy_direction_identity instead of guessing."""
        professor_dir = str(select.get("professor_dir") or "")
        pack = packs.get(professor_dir)
        explicit = select.get("direction_ids") or (
            [select.get("direction_id")] if select.get("direction_id") else None)
        if explicit:
            ids = sorted({str(x).strip() for x in explicit if str(x).strip()})
            return (ids or None), None
        ckey = select.get("collection_key")
        if not ckey or pack is None:
            return None, "legacy_direction_identity"
        matches = [direction_machine_id(d) for d in pack.get("directions") or []
                   if d.get("collection_key") == ckey]
        unique = sorted(set(matches))
        if len(unique) != 1:
            return None, "legacy_direction_identity"
        return unique, None

    return types.SimpleNamespace(
                email_source_hash=email_source_hash,
                compile_email_entry=compile_email_entry,
                validate_papers_override=validate_papers_override,
                _selection_direction_ids=_selection_direction_ids,
    )
