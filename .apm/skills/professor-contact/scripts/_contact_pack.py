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

from pathlib import Path
from typing import Any
import types


# The only levels a successful paper analysis may report. `None` (a missing
# field or an explicit JSON null) is the honest "unconfirmed" state; any other
# value is invalid input, never a third analysis level.
ANALYSIS_LEVELS = ("fulltext", "abstract")



def build(*, fail,
          soft_exit,
          INPUT_PACK_SCHEMA,
          CANDIDATE_STATE_SCHEMA,
          DIRECTION_IDENTITY_VERSION,
          STAGE3_GENERATOR_CONTRACT_VERSION,
          INPUT_PACK_KIND,
          CANDIDATE_STATE_KIND,
          INPUT_PACK,
          CANDIDATE_STATE,
          _CANONICAL_PAPER_FIELDS,
          read_json_file,
          direction_machine_id,
          cross_group_id):
    def _canonical_paper_record(entry: dict) -> dict:
        record = {"item_key": entry.get("item_key")}
        for field in _CANONICAL_PAPER_FIELDS:
            record[field] = entry.get(field)
        record["pdf_available"] = bool(record["pdf_available"])
        # One value domain for every canonical record, including v1 migration
        # snapshots: a missing field and an explicit null are the same honest
        # "unconfirmed" state, and an illegal value is never treated as known.
        level = record.get("analysis_level")
        record["analysis_level"] = level if level in ANALYSIS_LEVELS else None
        return record

    def _merge_canonical_paper(papers: dict, owners: dict, entry: dict, owner: str) -> dict:
        """Merge one direction-local paper snapshot into the professor-level map.

        Same item_key from two directions must be the SAME machine paper: records
        agree exactly, or the pack fails closed (shared_paper_conflict) instead of
        silently picking one copy.
        """
        record = _canonical_paper_record(entry)
        key = record["item_key"]
        if not isinstance(key, str) or not key.strip():
            fail("invalid_input_pack", f"direction {owner!r} has a paper without item_key")
        existing = papers.get(key)
        if existing is None:
            papers[key] = record
            owners[key] = [owner]
            return record
        conflicts = [field for field in _CANONICAL_PAPER_FIELDS
                     if existing.get(field) != record.get(field)]
        if conflicts:
            soft_exit("needs_refresh", "shared_paper_conflict",
                      item_key=key, conflict_fields=sorted(conflicts),
                      directions=sorted(set(owners.get(key) or []) | {owner}),
                      message="同一 item_key 在多个方向里带有冲突的权威字段：输入包不可信，"
                              "重跑阶段 2 重建规范 papers 后再继续。未修改任何文件。")
        if owner not in owners.setdefault(key, []):
            owners[key].append(owner)
        return existing

    def normalize_input_pack(raw: Any) -> dict | None:
        """Return the canonical v2 view of an input pack (never mutates the file).

        v2 packs are validated; v1 packs migrate in memory via exact machine
        mappings only: direction_id from the stamped resolved subfield (or 1:1
        collection_key), and direction-local paper snapshots canonicalized into one
        professor-level `papers` map with exact-field conflict detection.
        """
        if raw is None:
            return None
        if not isinstance(raw, dict):
            soft_exit("needs_refresh", "invalid_input_pack",
                      message="套磁候选输入.json 不是对象；重跑阶段 2 重建。")
        schema = raw.get("schema")
        directions_raw = raw.get("directions")
        if not isinstance(directions_raw, list):
            soft_exit("needs_refresh", "invalid_input_pack",
                      message="套磁候选输入.json 缺 directions 列表；重跑阶段 2 重建。")
        pack = dict(raw)
        if schema == INPUT_PACK_SCHEMA:
            if raw.get("kind") != INPUT_PACK_KIND or \
                    raw.get("identity_version") != DIRECTION_IDENTITY_VERSION:
                soft_exit("needs_refresh", "invalid_input_pack",
                          schema=schema, kind=raw.get("kind"),
                          identity_version=raw.get("identity_version"),
                          message="输入包 schema/kind/identity_version 不匹配；重跑阶段 2 重建。")
            papers = raw.get("papers")
            if not isinstance(papers, dict):
                soft_exit("needs_refresh", "invalid_input_pack",
                          message="v2 输入包缺 professor 级 papers 映射；重跑阶段 2 重建。")
        else:
            # v1 → v2 in-memory migration (exact machine mappings only).
            papers = {}
            owners: dict = {}
            directions = []
            seen_ids = {}
            for entry in directions_raw:
                if not isinstance(entry, dict):
                    soft_exit("needs_refresh", "invalid_input_pack",
                              message="输入包 directions[] 含非对象条目；重跑阶段 2 重建。")
                did = direction_machine_id(entry)
                if did in seen_ids:
                    soft_exit("needs_refresh", "legacy_direction_identity",
                              direction_id=did,
                              message=f"两个方向的机器身份都解析为 {did!r}：无法唯一映射，"
                                      "重跑阶段 2/3 重建身份后再继续。未修改任何文件。")
                seen_ids[did] = True
                local = entry.get("supporting_papers")
                keys = []
                if isinstance(local, list):
                    for paper in local:
                        if not isinstance(paper, dict):
                            continue
                        _merge_canonical_paper(papers, owners, paper, did)
                        if paper.get("item_key") not in keys:
                            keys.append(paper.get("item_key"))
                added = sorted({p.get("item_key") for p in (local or []) if isinstance(p, dict)
                                and p.get("resolved_addition") and p.get("item_key")}
                               | set(entry.get("resolved_addition_keys") or []))
                new_entry = dict(entry)
                new_entry["direction_id"] = did
                new_entry["supporting_item_keys"] = keys
                new_entry["resolved_addition_keys"] = added
                new_entry.pop("supporting_papers", None)
                directions.append(new_entry)
            pack["papers"] = papers
            pack["directions"] = directions
        missing = []
        for entry in pack["directions"]:
            for key in entry.get("supporting_item_keys") or []:
                if key not in pack["papers"]:
                    missing.append({"direction_id": direction_machine_id(entry), "item_key": key})
        if missing:
            soft_exit("needs_refresh", "invalid_input_pack",
                      missing=missing,
                      message="supporting_item_keys 引用了 papers 映射里不存在的论文；重跑阶段 2 重建。")
        return pack

    def load_input_pack(professor_dir: Path) -> tuple[dict | None, str | None]:
        """Read + normalize the input pack; (None, reason) when absent/unreadable."""
        raw, error = read_json_file(Path(professor_dir) / INPUT_PACK)
        if error or not isinstance(raw, dict):
            return None, error or "invalid_input_pack"
        return normalize_input_pack(raw), None

    def _migrate_v1_candidate(candidate: dict, did: str) -> dict:
        """Exact v1→v2 candidate record migration: pair gap refs gain the owning
        direction_id (v1 candidates only ever cite their own direction's gaps), and
        paper entries gain the same single-member provenance."""
        record = dict(candidate)
        record["kind"] = "direction"
        record["direction_ids"] = [did]
        record["gap_refs"] = [
            {"direction_id": did, "item_key": pair.get("item_key"), "gap_id": pair.get("gap_id"),
             "done_by_self": bool(pair.get("done_by_self"))}
            for pair in candidate.get("gap_ids") or []]
        record.pop("gap_ids", None)
        record["papers"] = [
            {**paper, "direction_ids": [did]} for paper in candidate.get("papers") or []]
        return record

    def _slice_gap_directions(pack: dict, direction_ids: list[str]) -> tuple[dict, dict]:
        """Exact-join indexes over the UNION of the given directions' slices.

        Returns (gap_owner, paper_owner) mapping each (item_key, gap_id) /
        item_key to the sorted list of participant direction IDs whose slice
        contains it — the machine data needed to attribute v1 cross records.
        """
        by_id = {direction_machine_id(d): d for d in (pack or {}).get("directions") or []}
        gap_owner: dict = {}
        paper_owner: dict = {}
        for did in direction_ids:
            direction = by_id.get(did)
            if direction is None:
                continue
            for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
                gap_owner.setdefault((gap.get("item_key"), gap.get("gap_id")), set()).add(did)
            for banned in direction.get("completed_gap_blacklist", []):
                gap_owner.setdefault((banned.get("item_key"), banned.get("gap_id")),
                                     set()).add(did)
            for key in direction.get("supporting_item_keys") or []:
                paper_owner.setdefault(key, set()).add(did)
            for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
                paper_owner.setdefault(gap.get("item_key"), set()).add(did)
        return gap_owner, paper_owner

    def _migrate_v1_cross_group(entry: dict, ids: list[str], pack: dict | None) -> dict:
        """Migrate one owner-scoped v1 cross entry to a standalone v2 group.

        Attribution uses the pack's exact slices: a gap pair owned by exactly one
        participant gains that direction_id; an ambiguous pair (present in several
        participants) can NOT be mapped exactly, so the whole group's candidates
        are dropped and its fingerprints nulled — the group reprocesses instead of
        keeping evidence with guessed provenance.
        """
        gap_owner, paper_owner = _slice_gap_directions(pack, ids)
        candidates = []
        for candidate in entry.get("candidates") or []:
            if not isinstance(candidate, dict):
                continue
            record = dict(candidate)
            attributable = True
            gap_refs = []
            for pair in candidate.get("gap_ids") or []:
                owners = gap_owner.get((pair.get("item_key"), pair.get("gap_id"))) or set()
                if len(owners) != 1:
                    attributable = False
                    break
                gap_refs.append({"direction_id": next(iter(owners)),
                                 "item_key": pair.get("item_key"),
                                 "gap_id": pair.get("gap_id"),
                                 "done_by_self": bool(pair.get("done_by_self"))})
            papers = []
            for paper in candidate.get("papers") or []:
                owners = sorted(paper_owner.get(paper.get("item_key")) or set() & set(ids))
                papers.append({**paper, "direction_ids": owners or list(ids)})
            if not attributable:
                candidates = []
                break
            record["gap_refs"] = gap_refs
            record.pop("gap_ids", None)
            record["papers"] = papers
            record["kind"] = "cross_direction"
            record["direction_ids"] = list(ids)
            candidates.append(record)
        fingerprints = {}
        for pid, fp in (entry.get("direction_fingerprints") or {}).items():
            if pid in ids:
                fingerprints[pid] = fp
        if not candidates:
            fingerprints = {pid: None for pid in ids}
        return {"group_id": cross_group_id(ids), "direction_ids": list(ids),
                "direction_fingerprints": fingerprints, "candidates": candidates}

    def normalize_candidate_state(raw: Any, pack: dict | None) -> tuple[dict | None, str | None]:
        """Return the canonical v2 view of 套磁候选状态.json (never mutates the file).

        v1 state migrates only through explicit 1:1 machine mappings recorded by
        the pack (collection_key → direction_id). Anything ambiguous fails closed
        with legacy_direction_identity and leaves accepted files untouched.
        """
        if raw is None:
            return None, None
        if not isinstance(raw, dict):
            return None, "invalid_candidate_state"
        schema = raw.get("schema")
        if schema == CANDIDATE_STATE_SCHEMA:
            if raw.get("kind") != CANDIDATE_STATE_KIND or \
                    raw.get("identity_version") != DIRECTION_IDENTITY_VERSION:
                return None, "invalid_candidate_state"
            return raw, None
        # v1 → v2 exact migration.
        key_to_did: dict[str, str] = {}
        ambiguous = set()
        for entry in (pack or {}).get("directions") or []:
            did = direction_machine_id(entry)
            ckey = entry.get("collection_key")
            if isinstance(ckey, str) and ckey.strip():
                if ckey in key_to_did and key_to_did[ckey] != did:
                    ambiguous.add(ckey)
                key_to_did[ckey] = did
        directions = []
        fingerprints = {}
        for entry in raw.get("directions") or []:
            if not isinstance(entry, dict):
                return None, "invalid_candidate_state"
            did = entry.get("direction_id")
            if not (isinstance(did, str) and did.strip()):
                ckey = entry.get("collection_key")
                did = key_to_did.get(ckey) if isinstance(ckey, str) else None
            if not did:
                return None, "legacy_direction_identity"
            new_entry = dict(entry)
            new_entry["direction_id"] = did
            new_entry["candidates"] = [_migrate_v1_candidate(c, did)
                                       for c in entry.get("candidates") or []
                                       if isinstance(c, dict)]
            new_entry["stage3_status"] = "ready" if new_entry["candidates"] else "empty"
            new_entry["generator_contract_version"] = STAGE3_GENERATOR_CONTRACT_VERSION
            directions.append(new_entry)
            old_fps = raw.get("input_fingerprints") or {}
            fp = old_fps.get(did) or old_fps.get(entry.get("collection_key"))
            if fp:
                fingerprints[did] = fp
        if raw.get("input_fingerprints") and not fingerprints:
            return None, "legacy_direction_identity"
        # v1 cross_direction entries were owner-scoped bookkeeping; v2 groups are
        # standalone identities keyed by sorted participant IDs. Candidates whose
        # provenance cannot be attributed exactly from the pack are dropped and
        # the group reprocesses (fingerprints nulled) instead of keeping guesses.
        grouped: dict[tuple, dict] = {}
        for entry in raw.get("cross_direction") or []:
            if not isinstance(entry, dict):
                continue
            ids = sorted({i for i in entry.get("direction_ids") or [] if isinstance(i, str)})
            if len(ids) < 2:
                continue
            key = tuple(ids)
            group = _migrate_v1_cross_group(entry, ids, pack)
            if key in grouped:
                merged = grouped[key]
                known = {c.get("id") for c in merged["candidates"]}
                merged["candidates"].extend(
                    c for c in group["candidates"] if c.get("id") not in known)
                if not merged["candidates"]:
                    merged["direction_fingerprints"] = {pid: None for pid in ids}
            else:
                grouped[key] = group
        state = dict(raw)
        state["schema"] = CANDIDATE_STATE_SCHEMA
        state["kind"] = CANDIDATE_STATE_KIND
        state["identity_version"] = DIRECTION_IDENTITY_VERSION
        state["generator_contract_version"] = STAGE3_GENERATOR_CONTRACT_VERSION
        state["directions"] = directions
        state["input_fingerprints"] = fingerprints
        state["cross_direction_groups"] = list(grouped.values())
        state.pop("cross_direction", None)
        return state, None

    def load_candidate_state(professor_dir: Path, pack: dict | None) -> tuple[dict | None, str | None]:
        """Read + normalize the candidate state against the given (normalized) pack.

        Returns (None, None) when the file does not exist yet; (None, reason) when
        it exists but cannot be exactly migrated."""
        raw, error = read_json_file(Path(professor_dir) / CANDIDATE_STATE)
        if error == "not_found":
            return None, None
        if error or not isinstance(raw, dict):
            return None, error or "invalid_candidate_state"
        return normalize_candidate_state(raw, pack)

    def _strict_candidate_shape(state: dict) -> str | None:
        """Machine-shape proof over the fields the aggregate consumes (issue #66).

        normalize_candidate_state stamps v2 identity fields without a deep
        structural pass — the Stage-4 behavior #66 must not change — so an
        on-disk state whose directions/candidates/groups are structurally
        corrupt would otherwise reach the overview renderer and publish garbage
        rows (r10 §3.7 requires every committed state to fail closed BEFORE the
        overview write). The compatibility/migration owner proves the shape
        here; renderer and rebuild stay pure consumers. Corrupt values are
        never treated as empty: the candidate list (and a group's member list)
        must be present and well-typed, or the state fails closed.
        """
        directions = state.get("directions")
        if not isinstance(directions, list):
            return "invalid_candidate_state"
        for row in directions:
            if not isinstance(row, dict):
                return "invalid_candidate_state"
            did = row.get("direction_id")
            if not (isinstance(did, str) and did.strip()):
                return "invalid_candidate_state"
            candidates = row.get("candidates")
            if not isinstance(candidates, list) or \
                    any(not isinstance(c, dict) for c in candidates):
                return "invalid_candidate_state"
        groups = state.get("cross_direction_groups")
        if groups is not None and not isinstance(groups, list):
            return "invalid_candidate_state"
        for row in groups or []:
            if not isinstance(row, dict):
                return "invalid_candidate_state"
            gid = row.get("group_id")
            if not (isinstance(gid, str) and gid.strip()):
                return "invalid_candidate_state"
            direction_ids = row.get("direction_ids")
            if not isinstance(direction_ids, list) or \
                    any(not isinstance(item, str) for item in direction_ids):
                return "invalid_candidate_state"
            candidates = row.get("candidates")
            if not isinstance(candidates, list) or \
                    any(not isinstance(c, dict) for c in candidates):
                return "invalid_candidate_state"
        return None

    def strict_candidate_state(professor_dir: Path) -> tuple[dict | None, str | None]:
        """Compatibility/migration owner for aggregate consumers (issue #66 r5).

        Loads one professor's candidate state with strict legacy identity proof:
        every collection_key the legacy state actually references must resolve to
        exactly ONE canonical direction_id in the same professor's normalized
        input pack (0 or >1 matches → legacy_direction_identity) before any
        migration runs, and the canonical state's machine shape is proven
        structurally before it may feed the aggregate. Aggregate rebuild only
        consumes the canonical state returned here and never re-implements the
        collection_key mapping itself; the pack supplies identity migration only,
        never candidate facts. Stage 4's existing normalize behavior is untouched.
        """
        raw, error = read_json_file(Path(professor_dir) / CANDIDATE_STATE)
        if error == "not_found":
            return None, None
        if error or not isinstance(raw, dict):
            return None, error or "invalid_candidate_state"
        if raw.get("schema") == CANDIDATE_STATE_SCHEMA:
            canonical, canonical_error = normalize_candidate_state(raw, None)
        else:
            pack, pack_error = load_input_pack(professor_dir)
            if pack is None:
                return None, pack_error or "missing_input_pack"
            pack_directions = pack.get("directions") or []
            for entry in raw.get("directions") or []:
                if not isinstance(entry, dict):
                    return None, "invalid_candidate_state"
                ckey = entry.get("collection_key")
                if not (isinstance(ckey, str) and ckey.strip()):
                    continue
                matches = sorted({direction_machine_id(d) for d in pack_directions
                                  if isinstance(d, dict) and d.get("collection_key") == ckey})
                if len(matches) != 1:
                    return None, "legacy_direction_identity"
            canonical, canonical_error = normalize_candidate_state(raw, pack)
        if canonical is None:
            return None, canonical_error
        shape_error = _strict_candidate_shape(canonical)
        if shape_error:
            return None, shape_error
        return canonical, None

    return types.SimpleNamespace(
                _canonical_paper_record=_canonical_paper_record,
                _merge_canonical_paper=_merge_canonical_paper,
                normalize_input_pack=normalize_input_pack,
                load_input_pack=load_input_pack,
                _migrate_v1_candidate=_migrate_v1_candidate,
                _slice_gap_directions=_slice_gap_directions,
                _migrate_v1_cross_group=_migrate_v1_cross_group,
                normalize_candidate_state=normalize_candidate_state,
                load_candidate_state=load_candidate_state,
                _strict_candidate_shape=_strict_candidate_shape,
                strict_candidate_state=strict_candidate_state,
    )
