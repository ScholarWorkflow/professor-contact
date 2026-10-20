#!/usr/bin/env python3
"""Direction-input helper module for ``contact_state.py``.

The runner loads this helper by path next to itself and calls :func:`build`
once with its own helper functions and shared constants. The factory binds
those names in an enclosing scope, so the functions below keep the exact
bodies they had inside the runner (only their indentation changed). The
module never imports the runner, never adds itself to ``sys.path`` and
never builds a second failure channel.
"""
from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Any


def build(*, fail,
          sha256_bytes,
          truncate,
          PROFILE_INPUT_CHARS,
          direction_machine_id,
          direction_papers,
          cross_group_id):
    def profile_fingerprint(profile_path: str | None) -> str | None:
        if not profile_path:
            return None
        path = Path(profile_path)
        if not path.is_file():
            return None
        return sha256_bytes(path.read_bytes())

    def load_profile_text(profile_path: str | None, limit: int = PROFILE_INPUT_CHARS) -> str | None:
        if not profile_path:
            return None
        path = Path(profile_path)
        if not path.is_file():
            return None
        return truncate(path.read_text(encoding="utf-8"), limit)

    def _direction_slices(pack: dict, direction: dict) -> tuple[dict, dict, dict]:
        """Exact-join indexes for one pack direction slice (issue #8 §5).

        gap/blacklist indexes are keyed by the exact provenance triple
        (direction_id, item_key, gap_id): a valid (item_key, gap_id) that exists in
        ANOTHER direction can never join through the wrong direction_id. The paper
        index is keyed by item_key over the direction's canonical universe
        (supporting_item_keys ∪ gap item keys) resolved from the professor-level
        papers map.
        """
        did = direction_machine_id(direction)
        gap_index = {}
        for gap in direction.get("gap_shortlist", []) + [
                dict(g, status=g.get("status")) for g in direction.get("gaps_excluded", [])]:
            gap_index[(did, gap["item_key"], gap["gap_id"])] = gap
        blacklist = {(did, b["item_key"], b["gap_id"]): b
                     for b in direction.get("completed_gap_blacklist", [])}
        paper_index = {p["item_key"]: p for p in direction_papers(pack, direction)}
        for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
            paper_index.setdefault(gap["item_key"], {
                "item_key": gap["item_key"], "title": gap.get("paper_title"),
                "year": gap.get("paper_year"), "authorship": gap.get("authorship")})
        return gap_index, blacklist, paper_index

    def _cross_group_fresh(group: dict, pack_fps: dict,
                           current_profile_fp: str | None) -> bool:
        """A cross-direction group survives only while EVERY participant's pack
        fingerprint and the profile are unchanged; unknown participants never
        count as fresh."""
        recorded = group.get("direction_fingerprints")
        if not isinstance(recorded, dict) or not recorded:
            return False
        if group.get("profile_fingerprint") != current_profile_fp:
            return False
        return all(pack_fps.get(pid) == fingerprint
                   for pid, fingerprint in recorded.items())

    def _parse_direction_id_list(raw: str | None, param: str) -> list[str]:
        values = [v.strip() for v in (raw or "").split(",") if v.strip()]
        seen, out = set(), []
        for value in values:
            if value not in seen:
                seen.add(value)
                out.append(value)
        return out

    def _parse_cross_groups(raw: Any, pack_directions: list) -> list[dict]:
        """Validate + normalize explicit cross_direction_groups input.

        Default (absent/empty) means NO cross work at all. Each group needs >=2
        distinct existing direction IDs; IDs are sorted/deduped for stable
        identity and duplicate groups are collapsed deterministically.
        """
        if raw is None or raw == "":
            return []
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError as exc:
                fail("invalid_params", f"cross_direction_groups must be JSON: {exc}")
        if not isinstance(raw, list):
            fail("invalid_params", "cross_direction_groups must be a list of ID lists")
        known = {direction_machine_id(d) for d in pack_directions}
        groups: dict[tuple, list[str]] = {}
        for index, group in enumerate(raw):
            if not isinstance(group, list) or any(not isinstance(x, str) or not x.strip()
                                                  for x in group):
                fail("invalid_params",
                     f"cross_direction_groups[{index}] must be a list of direction ID strings")
            ids = sorted({x.strip() for x in group})
            if len(ids) < 2:
                fail("invalid_params",
                     f"cross_direction_groups[{index}] needs >=2 distinct direction IDs")
            unknown = [x for x in ids if x not in known]
            if unknown:
                fail("invalid_params",
                     f"cross_direction_groups[{index}] cites unknown direction IDs: {unknown}")
            groups[tuple(ids)] = ids
        return [{"group_id": cross_group_id(ids), "direction_ids": list(ids)}
                for ids in groups.values()]

    return types.SimpleNamespace(
                profile_fingerprint=profile_fingerprint,
                load_profile_text=load_profile_text,
                _direction_slices=_direction_slices,
                _cross_group_fresh=_cross_group_fresh,
                _parse_direction_id_list=_parse_direction_id_list,
                _parse_cross_groups=_parse_cross_groups,
    )
