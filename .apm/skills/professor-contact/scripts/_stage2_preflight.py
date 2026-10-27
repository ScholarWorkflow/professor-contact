#!/usr/bin/env python3
"""Stage-2 preflight, identity and plan-command layer for ``contact_state.py``.

The runner loads this helper by path next to itself, then calls :func:`build`
once with its own helper functions and shared constants. The factory binds
those names in an enclosing scope, so the 27 functions below keep the exact
bodies they had inside the runner (only their indentation changed). The module
never imports the runner, never adds itself to ``sys.path`` and never builds a
second failure channel: every runner dependency arrives as an explicit build
parameter, so a missing one fails the runner import with ``TypeError``.
"""
from __future__ import annotations

import json
import copy
import importlib.util
import re
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path


# The continuation policy (effective round limit, recorded round, history rows)
# is shared with the two stage helpers; it is loaded by path for the same reason
# the runner does, since this directory is not guaranteed to be on sys.path.
_VALIDATION_CONTINUATION_PATH = Path(__file__).with_name("_validation_continuation.py")
_VALIDATION_CONTINUATION_SPEC = importlib.util.spec_from_file_location(
    "_validation_continuation", _VALIDATION_CONTINUATION_PATH)
if _VALIDATION_CONTINUATION_SPEC is None or _VALIDATION_CONTINUATION_SPEC.loader is None:
    raise RuntimeError(
        f"cannot load validation continuation helpers: {_VALIDATION_CONTINUATION_PATH}")
_validation_continuation = importlib.util.module_from_spec(_VALIDATION_CONTINUATION_SPEC)
_VALIDATION_CONTINUATION_SPEC.loader.exec_module(_validation_continuation)

round_limit = _validation_continuation.round_limit
recorded_round = _validation_continuation.recorded_round


SIDECAR_EXTRACTOR_VERSIONS = ("future-work-v1", "legacy-markdown-v0")

FACTS_GENERATOR_VERSIONS = ("facts-v1",)

STAGE2_PREFLIGHT_VERSION = "stage2-preflight-v3"

# Private cache.format of the managed analysis statistics. A pack only records
# this after the current three-class statistics were actually accepted with the
# rendered body; a preflight that finds the marker absent or stale takes the
# level-refresh branch instead of declaring a no-op reuse.
STAGE2_LEVEL_STATISTICS_VERSION = 1

# Stage-2 U1 fixed-evidence display contract. A pack whose managed analysis
# predates this marker (or a later version) must take the ordinary slow path
# once so the display and its ownership map are accepted by the normal
# finalize. The marker lives beside the body hash under cache.render.
# v2 (stage2-u1-r5): the marker also certifies the unified current/old paper
# reference authority, the renderer map as the only direction authority, and
# the lossless raw-byte acceptance/read contract.
# v3: source item_key citations share the trusted-title display contract.
STAGE2_U1_DISPLAY_VERSION = 4

# v2: issue #7 resolved directions become part of the Stage-2 contract the
# preflight must prove — provisional→resolved set mapping in cache.preflight,
# resolution-evidence (candidate-union) artifact guards, and the
# _resolved_directions.json binding to the facts' preflight proof. Packs
# accepted under v1 semantics must re-prove through the slow path.
# v3: authoritative membership comes ONLY from provisional_member_keys plus
# accepted add/remove decisions; analysis references (`relevant_keys`) are
# persisted next to members in the input pack and never become members. Packs
# accepted under v2 may carry reference papers in `supporting_item_keys`, so
# they must be rebuilt (membership re-derived from the current facts) instead
# of reused; preflight therefore misses them and their old validator record no
# longer certifies the rebuilt body.
STAGE2_RESOLUTION_SEMANTICS_VERSION = 3

STAGE2_TARGET_FILE_NAME = "套磁目标.json"

AUTHORSHIP_LEDGER_FILE = Path("教授研究") / "_署名对照.json"

PAPER_ANALYSIS_SCOPES = ("relevant", "all")

STAGE2_GUARD_KINDS = (("analysis", "analysis_file"), ("future_work", "sidecar_file"),
                      ("facts", "facts_file"), ("pdf", "pdf_file"))

def build(*, fail, soft_exit, emit, read_json_file, atomic_json, sha256_obj, sha256_bytes,
          sha256_text, split_frontmatter, split_frontmatter_bytes,
          stage2_validation_legality,
          managed_snapshot, direction_machine_id, facts_direction_id,
          direction_relevant_keys, gap_scope_keys, read_stage1_professor_entry,
          stage1_state_path, _canonical_under, load_input_pack, load_freshness_cache,
          _resolve_evidence, Stage2Context, filename_component, truncate,
          pack_direction_relevant_keys, observed_source_projection,
          observed_level_projection, consumed_sources, canonical_index_path,
          freeze_stage2_sources, observe_stage2_sources,
          INPUT_PACK, FRESHNESS_CACHE, GAP_SCOPES, FRESHNESS_SCOPES, ANALYSIS_MD, MANAGED_BY,
          SHORTLIST_MAX, ABSTRACT_INPUT_CHARS, QUOTE_INPUT_CHARS,
          TRANSLATION_INPUT_CHARS):
    def stage2_preflight_versions() -> dict:
        """Semantic identity of the Stage 2 resolution implementation.

        Any change that can make identical inputs produce different Stage 2 output
        must bump STAGE2_RESOLUTION_SEMANTICS_VERSION so older accepted packs are
        never silently reused by newer code.
        """
        return {
            "preflight_version": STAGE2_PREFLIGHT_VERSION,
            "resolution_semantics_version": STAGE2_RESOLUTION_SEMANTICS_VERSION,
            "sidecar_extractor_versions": list(SIDECAR_EXTRACTOR_VERSIONS),
            "facts_generator_versions": list(FACTS_GENERATOR_VERSIONS),
        }


    def stage2_preflight_params(paper_analysis: str, gap_scope: str, freshness_scope: str,
                                max_relevant_papers: int | None) -> dict:
        return {"paper_analysis": paper_analysis, "gap_scope": gap_scope,
                "freshness_scope": freshness_scope,
                "max_relevant_papers": max_relevant_papers}


    def stage2_target_fingerprint(direction: dict) -> str:
        """Hash only the target fields Stage 2 actually consumes for one direction.

        Deliberately excludes the whole-preview fingerprint, selection history and
        other professors: display-only projection churn must never invalidate a
        selected direction's Stage 2 state.
        """
        members = sorted(
            ({"item_key": member.get("item_key"),
              "preview_confidence": member.get("preview_confidence")}
             for member in direction.get("members") or []),
            key=lambda member: json.dumps(member, ensure_ascii=False, sort_keys=True))
        return sha256_obj({
            "direction_id": direction.get("direction_id"),
            "name_ja": direction.get("name_ja"),
            "name_zh": direction.get("name_zh"),
            "summary_zh": direction.get("summary_zh"),
            "members": members,
            "user_note": direction.get("user_note") or "",
        })


    def stage2_candidate_fingerprint(snapshot_direction: dict | None) -> str | None:
        """Hash the Stage 1 candidate-set view one direction consumes.

        Consumes the already-verified snapshot entry as-is; Stage 1 stays the
        candidate authority and preflight never re-runs candidate expansion.
        """
        if not isinstance(snapshot_direction, dict):
            return None
        readiness = snapshot_direction.get("pdf_readiness") or {}
        return sha256_obj({
            "direction_id": snapshot_direction.get("direction_id"),
            "provisional_member_keys": sorted(snapshot_direction.get("provisional_member_keys") or []),
            "candidate_keys": sorted(snapshot_direction.get("candidate_keys") or []),
            "expansion_reasons": {key: sorted(values or []) for key, values
                                  in sorted((snapshot_direction.get("expansion_reasons") or {}).items())},
            "expansion_evidence": {key: snapshot_direction["expansion_evidence"][key] for key
                                   in sorted(snapshot_direction.get("expansion_evidence") or {})},
            "pdf_readiness": {
                "usable_item_keys": sorted(readiness.get("usable_item_keys") or []),
                "missing_item_keys": sorted(readiness.get("missing_item_keys") or []),
                "unresolved_item_keys": sorted(readiness.get("unresolved_item_keys") or []),
                "status_counts": dict(sorted((readiness.get("status_counts") or {}).items())),
            },
        })


    def stage2_candidate_universe(target: dict | None, snapshot_entry: dict | None) -> set:
        """Union of Stage 1 candidate_keys over the professor's selected directions.

        This is the only catalog slice whose changes can invalidate accepted
        Stage 2 state; catalog/ledger churn outside it must never force the slow
        path.
        """
        snapshot_directions = {entry.get("direction_id"): entry
                               for entry in (snapshot_entry or {}).get("directions") or []
                               if isinstance(entry, dict)}
        keys: set = set()
        for direction_id in (target or {}).get("selected_direction_ids") or []:
            entry = snapshot_directions.get(direction_id)
            if not isinstance(entry, dict):
                continue
            candidate_keys = entry.get("candidate_keys")
            if isinstance(candidate_keys, list):
                keys.update(key for key in candidate_keys if isinstance(key, str))
        return keys


    def stage2_papers_catalog_view_fingerprint(professor_dir: Path,
                                               candidate_keys: set) -> str:
        """Hash only the candidate papers' catalog records, not the whole file.

        A sentinel (never a hex digest) means the catalog cannot prove the
        candidate view; recorded fingerprints can never match a sentinel, so any
        such state fails closed to the slow path.
        """
        path = professor_dir / "papers.json"
        if not path.is_file():
            return "missing"
        data, error = read_json_file(path)
        if error or not isinstance(data, dict) or not isinstance(data.get("papers"), list):
            return "malformed"
        records = {}
        absent = []
        for key in sorted(candidate_keys):
            record = next((paper for paper in data["papers"]
                           if isinstance(paper, dict) and paper.get("item_key") == key), None)
            if record is None:
                absent.append(key)
            else:
                records[key] = record
        return sha256_obj({"records": records, "absent": absent})


    def stage2_authorship_ledger_view_fingerprint(program_root: Path, professor: str) -> str:
        """Hash only this professor's slice of the shared authorship ledger.

        The tagger ledger is a per-professor name-variant book plus per-professor
        human overrides; other professors' entries and the file-level rebuild
        timestamp never feed this professor's Stage 2 authorship work, so they
        stay out of the cache key. Malformed containers fail closed via the same
        sentinel convention as the catalog view.
        """
        path = program_root / AUTHORSHIP_LEDGER_FILE
        if not path.is_file():
            return "missing"
        data, error = read_json_file(path)
        if error or not isinstance(data, dict):
            return "malformed"
        professors = data.get("professors")
        overrides = data.get("overrides")
        if professors is not None and not isinstance(professors, dict):
            return "malformed"
        if overrides is not None and not isinstance(overrides, dict):
            return "malformed"
        return sha256_obj({
            "sigbook": professors.get(professor) if isinstance(professors, dict) else None,
            "overrides": overrides.get(professor) if isinstance(overrides, dict) else None,
        })


    def stage2_program_inputs(program_root: Path, professor_dir: Path, professor: str,
                              target: dict | None, snapshot_entry: dict | None) -> dict:
        """Professor-wide cheap inputs: Stage 1 epoch + candidate-view fingerprints."""
        candidate_keys = stage2_candidate_universe(target, snapshot_entry)
        return {
            "stage1_professor_input_fingerprint": (snapshot_entry or {}).get("input_fingerprint"),
            "papers_catalog_view_sha256":
                stage2_papers_catalog_view_fingerprint(professor_dir, candidate_keys),
            "authorship_ledger_view_sha256":
                stage2_authorship_ledger_view_fingerprint(program_root, professor),
        }

    def _business_inputs(program_root, professor_dir, professor, target, snapshot,
                         params, current_year):
        keys = stage2_candidate_universe(target, snapshot)
        catalog, _ = read_json_file(Path(professor_dir) / "papers.json")
        ledger, _ = read_json_file(Path(program_root) / AUTHORSHIP_LEDGER_FILE)
        catalog_view = {key: next((paper for paper in (catalog or {}).get("papers", [])
                                  if isinstance(paper, dict) and paper.get("item_key") == key), None)
                        for key in sorted(keys)} if isinstance(catalog, dict) else None
        ledger_view = {field: (ledger.get(field) or {}).get(professor)
                       for field in ("professors", "overrides")
                       if isinstance(ledger.get(field) or {}, dict)} if isinstance(ledger, dict) else None
        return {"target": copy.deepcopy(target), "snapshot": copy.deepcopy(snapshot),
                "catalog": catalog_view, "ledger": ledger_view,
                "program_inputs": stage2_program_inputs(program_root, professor_dir,
                                                        professor, target, snapshot),
                "params": copy.deepcopy(params), "current_year": current_year,
                "resolved_source": _resolved_source(professor_dir)}

    def _resolved_source(professor_dir):
        path = Path(professor_dir) / "论文分析" / "_resolved_directions.json"
        try:
            return {"path": str(path.resolve()), "sha256": sha256_bytes(path.read_bytes())}
        except FileNotFoundError:
            return {"path": str(path.resolve()), "sha256": None}
        except OSError:
            return {"path": str(path.resolve()), "sha256": "unreadable"}

    def stage2_consumption_drift(ctx):
        frozen = ctx.sources
        business = frozen.get("business_inputs") or {}
        for field in ("gap_scope", "freshness_scope"):
            if (ctx.facts.get("params") or {}).get(field, getattr(ctx, field)) != business.get("params", {}).get(field):
                return ["params"]
        if ctx.current_year != business.get("current_year"):
            return ["current_year"]
        root = Path(ctx.consumption["program_root"])
        target = read_stage2_target(stage2_target_path(ctx.professor_dir), root, ctx.professor)
        snapshot = read_stage1_professor_entry(root, ctx.professor_dir, ctx.professor, target)
        pack, _ = load_input_pack(ctx.professor_dir)
        declarations = {}
        fields = dict(STAGE2_GUARD_KINDS)
        for key, guards in frozen.get("guards", {}).items():
            declarations[key] = {fields[kind]: value.get("path")
                                 for kind, value in guards.items() if kind in fields}
        current_business = _business_inputs(root, ctx.professor_dir, ctx.professor, target,
            snapshot, business.get("params", {}), datetime.now().year)
        current_sources = observe_stage2_sources(ctx.professor_dir, frozen,
            candidate_keys=stage2_candidate_universe(target, snapshot), business_inputs=current_business)
        observed = stage2_complete_observation(root, ctx.professor_dir, ctx.professor,
            target, snapshot, current_business["params"], current_business["current_year"],
            pack, sources=current_sources)
        return stage2_compare_observation(ctx.consumption.get("observation"), observed,
                                          include_level=True)

    def stage2_complete_observation(program_root, professor_dir, professor, target,
                                    snapshot_entry, params, current_year, pack, *,
                                    sources=None, cache_entries=None, baseline=None):
        """One finite business view, also projectable from frozen materials."""
        if sources is None:
            business = _business_inputs(program_root, professor_dir, professor, target,
                                        snapshot_entry, params, current_year)
            baseline = baseline or (((pack or {}).get("cache") or {}).get("preflight") or {}).get("observation")
            if isinstance(baseline, dict):
                previous = {"candidate_keys": baseline.get("candidate_keys", []),
                            "materials": baseline.get("materials", {}),
                            "guards": baseline.get("artifact_guards", {})}
                sources = observe_stage2_sources(professor_dir, previous,
                    candidate_keys=stage2_candidate_universe(target, snapshot_entry), business_inputs=business)
            else:
                sources = freeze_stage2_sources(professor_dir,
                    stage2_candidate_universe(target, snapshot_entry), business_inputs=business,
                    declared_sources=(pack or {}).get("papers"))
        else:
            business = sources.get("business_inputs") or {}
        target = business.get("target", target)
        snapshot_entry = business.get("snapshot", snapshot_entry)
        selected = set((target or {}).get("selected_direction_ids") or [])
        snapshots = {d.get("direction_id"): d for d in (snapshot_entry or {}).get("directions", [])
                     if isinstance(d, dict) and d.get("direction_id") in selected}
        entries = [d for d in (pack or {}).get("directions", []) if isinstance(d, dict)]
        cache = sources.get("freshness_cache", {}) if cache_entries is None else cache_entries
        index_path = str((Path(professor_dir) / "论文分析" / "_index.json").resolve())
        freshness_path = str((Path(professor_dir) / FRESHNESS_CACHE).resolve())
        # Raw index administration and unrelated freshness entries are not business inputs.
        material_states = {name: {field: record.get(field) for field in ("state", "stat", "sha256")}
                           for name, record in sources.get("materials", {}).items()
                           if name not in (index_path, freshness_path)}
        return {"version": 1, "candidate_keys": list(sources.get("candidate_keys") or []),
                "program_inputs": copy.deepcopy(business.get("program_inputs", {})),
                "params": copy.deepcopy(business.get("params", params)),
                "current_year": business.get("current_year", current_year),
                "targets": {str(d.get("direction_id")): stage2_target_fingerprint(d)
                            for d in (target or {}).get("directions", [])
                            if d.get("direction_id") in selected},
                "candidates": {str(key): stage2_candidate_fingerprint(value)
                               for key, value in snapshots.items()},
                "source_projection": copy.deepcopy(sources.get("projection", {})),
                "artifact_guards": copy.deepcopy(sources.get("guards", {})),
                "materials": material_states,
                "consumed": {direction_machine_id(d): stage2_consumed_source_keys(d) for d in entries},
                "resolved": _pack_resolved_grouping(entries),
                "resolved_source": copy.deepcopy(business.get("resolved_source")),
                "freshness": {direction_machine_id(d): stage2_freshness_view_fingerprint(d, cache)
                              for d in entries},
                "levels": copy.deepcopy(sources.get("levels", {}))}

    def stage2_compare_observation(baseline, current, include_level=False):
        if not isinstance(baseline, dict) or baseline.get("version") != 1:
            return ["consumption_baseline_missing"]
        fields = set(baseline) | set(current)
        if not include_level:
            fields.discard("levels")
        changed = sorted(field for field in fields if baseline.get(field) != current.get(field))
        if "targets" in changed:
            changed.append("selected_direction_ids")
        return changed


    def stage2_target_path(professor_dir: Path) -> Path:
        """Professor-local Stage-0 authority for the professor owning ``professor_dir``."""
        return Path(professor_dir) / STAGE2_TARGET_FILE_NAME


    def read_stage2_target(target_path: Path, program_root: Path, professor: str) -> dict | None:
        """Read one professor's Stage-0 target, fail-closed to ``None``.

        The retired program-level ``教授研究/套磁目标.json`` is not read here: the
        caller passes the professor's own local target file.
        """
        data, error = read_json_file(Path(target_path))
        if error or not isinstance(data, dict):
            return None
        if data.get("schema_version") != 2 or data.get("kind") != "professor-contact-target":
            return None
        if data.get("professor") != professor:
            return None
        professor_dir = str(data.get("professor_dir") or "")
        if not professor_dir:
            return None
        declared = (Path(program_root) / professor_dir / STAGE2_TARGET_FILE_NAME).resolve()
        if str(declared) != str(Path(target_path).resolve()):
            return None
        return data


    def stage2_local_identity(program_root: Path, professor_dir: Path, professor: str,
                              target: dict | None, snapshot_entry: dict | None) -> dict:
        """Canonical transaction identity a Stage-2 proof must keep binding.

        The digest covers the full bytes of the professor-local target file this
        transaction opened, and the fingerprint is the exact Stage-1 input
        fingerprint it matched; display name alone cannot tell two professors
        apart, and partial business-field fingerprints cannot see target content
        outside the selected projection (e.g. selection_history).
        """
        target_path = stage2_target_path(professor_dir)
        try:
            digest = sha256_bytes(Path(target_path).read_bytes())
        except OSError:
            digest = None
        return {
            "professor": professor,
            "professor_dir": _canonical_under(program_root, (target or {}).get("professor_dir"))
                             or str(Path(professor_dir).resolve()),
            "preview_path": _canonical_under(program_root, (target or {}).get("preview_path")),
            "target_state": str(Path(target_path).resolve()),
            "target_state_sha256": digest,
            "stage1_input_fingerprint": (snapshot_entry or {}).get("input_fingerprint"),
        }


    def stage2_transaction_identity(ctx: "Stage2Context") -> tuple[dict | None, dict | None, dict]:
        """Reopen the professor's local target and reread its exact Stage-1 entry."""
        target = read_stage2_target(stage2_target_path(ctx.professor_dir), ctx.program_root,
                                    ctx.professor)
        snapshot_entry = read_stage1_professor_entry(
            ctx.program_root, ctx.professor_dir, ctx.professor, target)
        identity = stage2_local_identity(ctx.program_root, ctx.professor_dir, ctx.professor,
                                         target, snapshot_entry)
        return target, snapshot_entry, identity


    def stage2_preflight_cheap_inputs(program_root: Path, professor_dir: Path, professor: str,
                                      target: dict | None, snapshot_entry: dict | None,
                                      params: dict, current_year: int) -> dict:
        """The structural inputs both preflight and finalize can recompute cheaply.

        This block is the TOCTOU comparison basis: it never touches analysis
        artifacts, PDFs, Zotero or the network — only persisted state fingerprints.
        """
        snapshot_directions = {entry.get("direction_id"): entry
                               for entry in ((snapshot_entry or {}).get("directions") or [])
                               if isinstance(entry, dict)}
        directions = {}
        for direction in (target or {}).get("directions") or []:
            direction_id = str(direction.get("direction_id"))
            directions[direction_id] = {
                "target_fingerprint": stage2_target_fingerprint(direction),
                "candidate_fingerprint": stage2_candidate_fingerprint(
                    snapshot_directions.get(direction.get("direction_id"))),
            }
        return {
            "versions": stage2_preflight_versions(),
            "params": params,
            "current_year": current_year,
            "identity": stage2_local_identity(program_root, professor_dir, professor,
                                              target, snapshot_entry),
            "program_inputs": stage2_program_inputs(program_root, professor_dir, professor,
                                                    target, snapshot_entry),
            "selected_direction_ids": sorted((target or {}).get("selected_direction_ids") or []),
            "directions": directions,
        }


    def stage2_artifact_guard(path: Path, accepted_digest: str | None) -> dict:
        stat = path.stat()
        return {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                "ctime_ns": stat.st_ctime_ns, "accepted_digest": accepted_digest}


    def stage2_artifact_guard_reason(recorded: dict) -> str | None:
        """Filesystem-only guard: stat the accepted artifact, never re-read bytes.

        Cryptographic source identity stays with the normal Stage 2 facts
        validation; this only detects that the recorded file itself changed since
        the accepted run.
        """
        path = Path(str(recorded.get("path") or ""))
        try:
            if not path.is_file():
                return "artifact_missing"
            stat = path.stat()
        except OSError:
            return "artifact_missing"
        if (stat.st_size != recorded.get("size")
                or stat.st_mtime_ns != recorded.get("mtime_ns")
                or stat.st_ctime_ns != recorded.get("ctime_ns")):
            return "artifact_changed"
        return None


    def _artifact_guards_for_keys(ctx: Stage2Context, guard_keys: set) -> dict:
        """Record accepted stat guards for a set of papers.

        Digests reuse SHAs already computed by Stage2Context; PDF bytes are never
        re-read just for metadata.
        """
        if getattr(ctx, "sources", None):
            return {key: copy.deepcopy(ctx.sources.get("guards", {}).get(key, {}))
                    for key in sorted(guard_keys)
                    if ctx.sources.get("guards", {}).get(key)}
        guards = {}
        for key in sorted(guard_keys):
            paper = ctx.papers.get(key)
            if not paper:
                continue
            entries = {}
            for kind, field in STAGE2_GUARD_KINDS:
                value = paper.get(field)
                if not value:
                    continue
                path = Path(value)
                if not path.is_file():
                    continue
                digest = None
                if kind == "future_work":
                    cached = ctx.sidecar_cache.get(value)
                    if cached is not None:
                        digest = cached[3]
                elif kind == "pdf":
                    record = ctx.facts_cache.get(key)
                    if record and record[1] == "valid" and record[0]:
                        digest = record[0].get("input_fingerprint")
                else:
                    digest = sha256_bytes(path.read_bytes())
                entries[kind] = stage2_artifact_guard(path, digest)
            if entries:
                guards[key] = entries
        return guards


    def stage2_direction_artifact_guards(ctx: Stage2Context, direction: dict) -> dict:
        """Record accepted stat guards for artifacts that feed one direction's output.

        Guard keys are the direction's relevant papers plus its gap-scope papers
        (the sidecar sources of the direction gap pool).
        """
        guard_keys = set(direction_relevant_keys(direction))
        guard_keys.update(gap_scope_keys(ctx.facts, direction))
        return _artifact_guards_for_keys(ctx, guard_keys)


    def stage2_resolution_evidence_guards(ctx: Stage2Context) -> dict:
        """Stat guards over the FULL resolution evidence universe (issue #7).

        Resolved membership / rename / split / merge judgments read the
        professor-level selected candidate union — including candidates outside
        every direction's relevant/gap scope that full text could rescue back.
        Every union paper's artifacts therefore join the resolution reuse
        identity: a changed sidecar/PDF/analysis for ANY candidate must miss the
        early preflight so the resolve pipeline re-judges it.
        """
        return _artifact_guards_for_keys(ctx, set(_resolve_evidence(ctx)["evidence_keys"]))


    def _pack_resolved_grouping(pack_directions: list) -> dict[str, dict]:
        """Map each provisional direction to the authoritative entries it produced.

        Derived purely from the accepted pack's stamped `resolved_direction`
        subfields (issue #7 finalize always writes them; packs finalized without
        resolved state group each entry under its own collection_key):

        - split: the source provisional lists the materialized child too
          (`resolved` = [source, child, ...]);
        - merge: the source provisional no longer owns an entry — it maps to the
          target via `merged_into` (recorded from the target's `merged_from`).

        Returns {provisional_id: {"resolved": [direction_ids],
        "merged_into": target_id | None}} keyed by canonical direction identity.
        """
        grouping: dict[str, dict] = {}
        for entry in pack_directions:
            if not isinstance(entry, dict):
                continue
            did = direction_machine_id(entry)
            rd = entry.get("resolved_direction") if isinstance(entry.get("resolved_direction"), dict) else {}
            pid = rd.get("provisional_direction_id") or did
            slot = grouping.setdefault(pid, {"resolved": [], "merged_into": None})
            slot["resolved"].append(did)
            for source in rd.get("merged_from") or []:
                source_slot = grouping.setdefault(source, {"resolved": [], "merged_into": None})
                source_slot["merged_into"] = did
        return grouping


    def stage2_freshness_view_fingerprint(pack_direction: dict, cache_entries: dict) -> str:
        """Hash the freshness-cache view over one accepted direction's gaps.

        Covers every gap the accepted pack surfaced (shortlist, excluded,
        done_by_self blacklist). Entries for unrelated gaps are irrelevant; a
        missing/invalid cache file yields null entries and misses.
        """
        gap_ids = set()
        for section in ("gap_shortlist", "gaps_excluded", "completed_gap_blacklist"):
            for gap in pack_direction.get(section) or []:
                gap_id = gap.get("gap_id") if isinstance(gap, dict) else None
                if gap_id:
                    gap_ids.add(gap_id)
        view = {gap_id: cache_entries.get(gap_id) for gap_id in sorted(gap_ids)}
        return sha256_obj(view)


    def stage2_consumed_source_keys(entry: dict) -> list:
        """Papers whose sources this accepted direction actually consumed.

        Members, the persisted analysis reference scope and every surfaced gap's
        paper: that is the limited union a later level/source refresh may inspect.
        It never scans the professor library or other directions.
        """
        keys = set()
        for key in entry.get("supporting_item_keys") or []:
            keys.add(key)
        for key in pack_direction_relevant_keys(entry):
            keys.add(key)
        for section in ("gap_shortlist", "gaps_excluded", "completed_gap_blacklist"):
            for gap in entry.get(section) or []:
                if isinstance(gap, dict):
                    keys.add(gap.get("item_key"))
        return sorted(key for key in keys if isinstance(key, str) and key)


    def stage2_group_consumed_keys(accepted_by_key: dict, grouping: dict,
                                   direction_id: str) -> list:
        """Union of consumed source keys over one provisional direction's outputs.

        A split child contributes its own keys next to its source; a merged-away
        source has no entry of its own and contributes the surviving target's.
        """
        slot = grouping.get(direction_id) or {"resolved": [], "merged_into": None}
        ids = list(slot["resolved"])
        if slot["merged_into"]:
            ids.append(slot["merged_into"])
        keys = set()
        for resolved_id in ids:
            entry = accepted_by_key.get(resolved_id)
            if isinstance(entry, dict):
                keys.update(stage2_consumed_source_keys(entry))
        return sorted(keys)


    def stage2_level_projection(papers: dict, keys: list) -> dict:
        """The canonical level this run writes for every consumed paper."""
        return {key: (papers.get(key) or {}).get("analysis_level") for key in keys}


    def stage2_pdf_source_projection(papers: dict, keys: list) -> dict:
        """The explicit PDF source each accepted paper named, or an explicit none."""
        return {key: canonical_index_path((papers.get(key) or {}).get("pdf_file"))
                for key in keys}


    def stage2_refresh_preflight_metadata(meta: dict, pack: dict, papers: dict) -> dict:
        """Update only the level projection and the statistics marker.

        A level-only refresh does not re-prove or rewrite any business binding:
        the source projection, artifact guards, target/candidate fingerprints,
        resolved grouping and freshness views stay byte-identical (the refresh
        gate already proved the current observation equals the accepted source
        projection). `consumed_sources`/`pdf_sources` keep describing the last
        facts acceptance, because a refresh consumes neither facts nor PDFs.
        """
        accepted_by_key = {direction_machine_id(entry): entry
                           for entry in pack.get("directions") or []
                           if isinstance(entry, dict)}
        grouping = _pack_resolved_grouping(list(accepted_by_key.values()))
        updated = dict(meta)
        directions = {}
        for direction_id, record in (meta.get("directions") or {}).items():
            if not isinstance(record, dict):
                directions[direction_id] = record
                continue
            keys = stage2_group_consumed_keys(accepted_by_key, grouping, direction_id)
            new_record = dict(record)
            new_record["level_projection"] = stage2_level_projection(papers, keys)
            directions[direction_id] = new_record
        updated["directions"] = directions
        updated["statistics_version"] = STAGE2_LEVEL_STATISTICS_VERSION
        return updated


    def stage2_preflight_metadata(program_root: Path, professor_dir: Path, target: dict,
                                  snapshot_entry: dict | None, pack_directions: list,
                                  params: dict, current_year: int, ctx: Stage2Context,
                                  cache_entries: dict,
                                  statistics_version: int | None = None) -> dict:
        """Build the cache.preflight block seeded into an accepted input pack.

        Written only by stage2-finalize; consumers (stage3+) must keep treating it
        as opaque cache metadata, never as stage facts.

        Each selected PROVISIONAL direction records its full accepted resolved
        output set (issue #7): `resolved_direction_ids` are the pack entries the
        resolution produced for it (a split child appears next to its source; a
        merged source maps to the surviving target via `merged_into`), and
        `resolved_entries` carries per-entry accepted/freshness fingerprints.
        Early reuse must prove the whole resolved set, not just that the old
        provisional collection_key still exists.

        The level/source projections split the two change classes the third
        preflight branch needs: `source_projection` is the business identity and
        `level_projection` the display value. `statistics_version` is stamped
        only after the current statistics were actually accepted with the
        rendered body, so metadata construction alone can never claim success.
        """
        snapshot_directions = {entry.get("direction_id"): entry
                               for entry in (snapshot_entry or {}).get("directions") or []
                               if isinstance(entry, dict)}
        accepted_by_key = {direction_machine_id(entry): entry for entry in pack_directions}
        facts_directions = {facts_direction_id(entry): entry
                            for entry in ctx.facts.get("directions") or []}
        grouping = _pack_resolved_grouping(pack_directions)
        frozen = getattr(ctx, "sources", None)
        if frozen and isinstance((ctx.consumption or {}).get("resolve"), dict):
            frozen = copy.deepcopy(frozen)
            resolved_source = ctx.consumption["resolve"].get("sidecar")
            if resolved_source:
                frozen["business_inputs"]["resolved_source"] = copy.deepcopy(resolved_source)
        source_projection = frozen.get("projection", {}) if frozen else None
        directions = {}
        for direction in target.get("directions") or []:
            direction_id = str(direction.get("direction_id"))
            accepted = accepted_by_key.get(direction_id)
            slot = grouping.get(direction_id) or {"resolved": [], "merged_into": None}
            if not accepted and not slot["merged_into"]:
                # No accepted output at all: the direction was never finalized
                # into this pack (a freshly selected direction). Everything else
                # — including a merged-away source, which owns no entry but keeps
                # its provenance mapping — must still be recorded so the early
                # gate can prove the full resolved set.
                continue
            facts_direction = facts_directions.get(direction_id) or {}
            resolved_entries = {}
            for resolved_id in sorted(slot["resolved"]):
                entry = accepted_by_key.get(resolved_id)
                if not isinstance(entry, dict):
                    continue
                resolved_entries[resolved_id] = {
                    "accepted_input_fingerprint": entry.get("input_fingerprint"),
                    "freshness_view_fingerprint": stage2_freshness_view_fingerprint(
                        entry, cache_entries),
                }
            consumed_keys = stage2_group_consumed_keys(accepted_by_key, grouping, direction_id)
            directions[direction_id] = {
                "target_fingerprint": stage2_target_fingerprint(direction),
                "candidate_fingerprint": stage2_candidate_fingerprint(
                    snapshot_directions.get(direction.get("direction_id"))),
                "accepted_input_fingerprint": accepted.get("input_fingerprint") if accepted else None,
                "freshness_view_fingerprint": stage2_freshness_view_fingerprint(
                    accepted, cache_entries) if accepted else None,
                "artifact_guards": stage2_direction_artifact_guards(ctx, facts_direction),
                "resolved_direction_ids": sorted(slot["resolved"]),
                "merged_into": slot["merged_into"],
                "resolved_entries": resolved_entries,
                # Limited source identity (business) and the separate level value.
                "source_projection": ({"index": source_projection.get("index"),
                                       "papers": {key: copy.deepcopy(source_projection.get("papers", {}).get(key))
                                                  for key in consumed_keys}} if frozen else
                                      observed_source_projection(professor_dir, consumed_keys)),
                "level_projection": stage2_level_projection(ctx.papers, consumed_keys),
                "consumed_sources": consumed_sources(ctx.papers, consumed_keys),
                "pdf_sources": stage2_pdf_source_projection(ctx.papers, consumed_keys),
            }
        return {
            "schema": 1,
            "version": STAGE2_PREFLIGHT_VERSION,
            "resolution_semantics_version": STAGE2_RESOLUTION_SEMANTICS_VERSION,
            "sidecar_extractor_versions": list(SIDECAR_EXTRACTOR_VERSIONS),
            "facts_generator_versions": list(FACTS_GENERATOR_VERSIONS),
            "statistics_version": statistics_version,
            "accepted_directions_sha256": sha256_obj(pack_directions),
            "current_year": current_year,
            "params": params,
            "program_inputs": (copy.deepcopy(frozen["business_inputs"]["program_inputs"])
                               if frozen else stage2_program_inputs(program_root, professor_dir,
                                             ctx.professor, target, snapshot_entry)),
            # Resolution reuse identity (issue #7): the resolve evidence universe
            # is the professor-level candidate union, wider than any single
            # direction's relevant/gap scope — guard it as one block.
            "resolution_evidence_guards": stage2_resolution_evidence_guards(ctx),
            "resolution_evidence_projection": (copy.deepcopy(source_projection) if frozen else
                observed_source_projection(professor_dir, stage2_candidate_universe(target, snapshot_entry))),
            "consumption": {"version": 1, "run_id": (ctx.consumption or {}).get("run_id"),
                            "sources_sha256": (ctx.consumption or {}).get("sources_sha256")},
            "observation": stage2_complete_observation(program_root, professor_dir, ctx.professor,
                target, snapshot_entry, params, current_year, {"directions": pack_directions},
                sources=frozen, cache_entries=cache_entries),
            "directions": directions,
        }


    def stage2_pack_state_fingerprint(pack: dict) -> str:
        return sha256_obj({
            "professor": pack.get("professor"),
            "directions": {direction_machine_id(d): d.get("input_fingerprint")
                           for d in pack.get("directions") or []},
        })


    def stage2_pack_content_fingerprint(pack: dict) -> str:
        return sha256_obj({key: value for key, value in pack.items() if key != "validator"})


    def stage2_validator_accepts(pack: dict | None, direction_ids: list,
                                 professor_dir: Path | None = None) -> str | None:
        """Return a validator-not-accepted reason, or None when reuse may proceed.

        Keeps the existing validator contract: only recorded terminal results
        (`pass`/`skipped`) count as accepted; missing results, malformed state and
        a recorded failure (`fail_after_2_rounds`, or `fail_after_max_rounds` on a
        cycle a human grant extended) force the slow path without redefining
        policy here.
        """
        validator, legality_error = stage2_validation_legality(pack)
        if legality_error:
            return "validator_not_accepted"
        results = validator.get("results") if isinstance(validator, dict) else None
        if not isinstance(results, dict):
            return "validator_not_accepted"
        if isinstance(validator, dict) and validator.get("schema") == 2:
            render_sha = validator.get("render_sha256")
            current_round = recorded_round(validator)
            limit = round_limit(validator)
            if validator.get("phase") != "terminal" \
                    or not 1 <= current_round <= limit \
                    or validator.get("pack_sha256") != stage2_pack_content_fingerprint(pack):
                return "validator_not_accepted"
            cache = pack.get("cache") if isinstance(pack, dict) else None
            render = cache.get("render") if isinstance(cache, dict) else None
            cached = render.get(ANALYSIS_MD) if isinstance(render, dict) else None
            if not isinstance(render_sha, str) or not render_sha \
                    or not isinstance(cached, dict) or cached.get("sha256") != render_sha:
                return "validator_not_accepted"
            if professor_dir is not None:
                path = professor_dir / ANALYSIS_MD
                if path.is_symlink():
                    return "validator_not_accepted"
                # Prove the actual managed body bytes on disk, including a
                # legal CRLF header; the validator gate must not depend on a
                # universal-newline text view.
                try:
                    data = path.read_bytes()
                except OSError:
                    return "validator_not_accepted"
                header, body = split_frontmatter_bytes(data)
                body_sha = sha256_bytes(body)
                if not isinstance(header, dict) or header.get("managed_by") != MANAGED_BY \
                        or header.get("render_sha256") != body_sha or body_sha != render_sha \
                        or header.get("state_fingerprint") != stage2_pack_state_fingerprint(pack):
                    return "validator_not_accepted"
        for direction_id in direction_ids:
            row = results.get(direction_id)
            if not isinstance(row, dict) or row.get("result") not in ("pass", "skipped"):
                return "validator_not_accepted"
        return None


    def cmd_stage2_preflight(args) -> None:
        professor = args.professor
        if args.paper_analysis not in PAPER_ANALYSIS_SCOPES:
            fail("invalid_params", f"paper_analysis must be one of {PAPER_ANALYSIS_SCOPES}")
        if args.gap_scope not in GAP_SCOPES:
            fail("invalid_params", f"gap_scope must be one of {GAP_SCOPES}")
        if args.freshness_scope not in FRESHNESS_SCOPES:
            fail("invalid_params", f"freshness_scope must be one of {FRESHNESS_SCOPES}")
        if args.max_relevant_papers is not None and (isinstance(args.max_relevant_papers, bool)
                                                     or args.max_relevant_papers < 1):
            fail("invalid_params", "max_relevant_papers must be a positive integer when given")
        program_root = Path(args.program_root)
        params = stage2_preflight_params(args.paper_analysis, args.gap_scope,
                                         args.freshness_scope, args.max_relevant_papers)
        current_year = datetime.now().year
        target = read_stage2_target(Path(args.target_file), program_root, professor)
        if target is None:
            fail("invalid_params",
                 f"professor has no selected target state; run contact_targets.py resolve first: {professor}")
        professor_dir = program_root / str(target.get("professor_dir") or "")
        snapshot_entry = read_stage1_professor_entry(program_root, professor_dir, professor, target)
        if snapshot_entry is None:
            # The professor-local Stage-1 state is a required preflight proof input
            # (R64-20 exact-entry binding): missing, malformed or misowned state has
            # no candidate universe to bind, so fail closed to the refresh lifecycle
            # instead of the slow path, and never fall back to another professor's
            # state or the retired program aggregate.
            state_path = stage1_state_path(professor_dir)
            soft_exit("needs_refresh",
                      "missing_stage1_snapshot" if not state_path.is_file()
                      else "invalid_stage1_snapshot",
                      snapshot_path=str(state_path), professor=professor)
        pack_path = professor_dir / INPUT_PACK
        pack, _error = load_input_pack(professor_dir)
        cache_block = (pack or {}).get("cache")
        meta = cache_block.get("preflight") if isinstance(cache_block, dict) else None
        render_block = cache_block.get("render") if isinstance(cache_block, dict) else None
        render_entry = render_block.get(ANALYSIS_MD) if isinstance(render_block, dict) else None
        u1_marker = render_entry.get("u1") if isinstance(render_entry, dict) else None
        u1_update_needed = pack is not None and (
            not isinstance(u1_marker, dict)
            or u1_marker.get("display_version") != STAGE2_U1_DISPLAY_VERSION)

        professor_reasons: list = []
        if u1_update_needed:
            professor_reasons.append("fixed_evidence_display_update")
        if pack is None:
            professor_reasons.append("missing_input_pack")
        elif cache_block is not None and not isinstance(cache_block, dict):
            # Corrupted / half-written containers must fail closed to the slow path
            # with a stable reason; they may never crash the gate itself.
            professor_reasons.append("preflight_cache_malformed")
        elif not isinstance(meta, dict):
            professor_reasons.append(
                "preflight_cache_malformed" if meta is not None else "legacy_pack_no_preflight")
            meta = None
        else:
            if meta.get("version") != STAGE2_PREFLIGHT_VERSION:
                professor_reasons.append("preflight_version_changed")
            if (meta.get("resolution_semantics_version") != STAGE2_RESOLUTION_SEMANTICS_VERSION
                    or meta.get("sidecar_extractor_versions") != list(SIDECAR_EXTRACTOR_VERSIONS)
                    or meta.get("facts_generator_versions") != list(FACTS_GENERATOR_VERSIONS)):
                professor_reasons.append("resolution_semantics_changed")
            if meta.get("accepted_directions_sha256") != sha256_obj(pack.get("directions") or []):
                professor_reasons.append("pack_integrity_mismatch")
            if meta.get("params") != params or meta.get("current_year") != current_year:
                professor_reasons.append("params_changed")
            current_program_inputs = stage2_program_inputs(program_root, professor_dir,
                                                           professor, target, snapshot_entry)
            recorded_program_inputs = meta.get("program_inputs")
            if not isinstance(recorded_program_inputs, dict):
                professor_reasons.append("preflight_cache_malformed")
                recorded_program_inputs = {}
            if recorded_program_inputs.get("stage1_professor_input_fingerprint") != \
                    current_program_inputs["stage1_professor_input_fingerprint"]:
                professor_reasons.append("stage1_professor_changed")
            if recorded_program_inputs.get("papers_catalog_view_sha256") != \
                    current_program_inputs["papers_catalog_view_sha256"]:
                professor_reasons.append("papers_catalog_changed")
            if recorded_program_inputs.get("authorship_ledger_view_sha256") != \
                    current_program_inputs["authorship_ledger_view_sha256"]:
                professor_reasons.append("authorship_ledger_changed")
            # Resolution evidence universe (issue #7): the candidate-union guards
            # recorded at finalize cover every candidate whose full-text facts can
            # enter a resolved membership/rename/split/merge judgment — including
            # candidates outside all directions' relevant/gap scope. Any guard
            # flip must miss the early gate so the resolve pipeline re-judges.
            union_guards = meta.get("resolution_evidence_guards")
            if not isinstance(union_guards, dict):
                if union_guards is not None:
                    professor_reasons.append("preflight_cache_malformed")
            else:
                for item_key in sorted(union_guards):
                    kinds = union_guards[item_key]
                    if not isinstance(kinds, dict):
                        professor_reasons.append("preflight_cache_malformed")
                        continue
                    for kind in sorted(kinds):
                        guard = kinds[kind]
                        reason = stage2_artifact_guard_reason(guard if isinstance(guard, dict) else {})
                        if reason:
                            professor_reasons.append(reason)

        cache_entries = load_freshness_cache(professor_dir) if pack else {}
        observation_reasons = []
        if isinstance(meta, dict):
            baseline = meta.get("observation")
            if not isinstance(baseline, dict) or not isinstance(meta.get("consumption"), dict):
                professor_reasons.append("consumption_baseline_missing")
            elif observed_level_projection(professor_dir,
                    stage2_candidate_universe(target, snapshot_entry)).get("valid"):
                current = stage2_complete_observation(program_root, professor_dir, professor,
                    target, snapshot_entry, params, current_year, pack,
                    cache_entries=cache_entries)
                observation_drift = stage2_compare_observation(baseline, current)
                if observation_drift:
                    professor_reasons.append("business_observation_changed")
                if set(observation_drift) & {"materials", "artifact_guards"}:
                    old_materials = baseline.get("materials") or {}
                    new_materials = current.get("materials") or {}
                    changed_paths = {name for name in set(old_materials) | set(new_materials)
                                     if old_materials.get(name) != new_materials.get(name)}
                    for name in changed_paths:
                        missing = (old_materials.get(name) or {}).get("state") == "present" \
                            and (new_materials.get(name) or {}).get("state") == "missing"
                        observation_reasons.append("artifact_missing" if missing else "artifact_changed")
                    if not changed_paths:
                        observation_reasons.append("artifact_changed")
        pack_directions = {direction_machine_id(entry): entry
                           for entry in (pack or {}).get("directions") or []
                           if isinstance(entry, dict)}
        recorded_directions = (meta or {}).get("directions")
        if not isinstance(recorded_directions, dict):
            if recorded_directions is not None:
                professor_reasons.append("preflight_cache_malformed")
            recorded_directions = {}
        snapshot_directions = {entry.get("direction_id"): entry
                               for entry in (snapshot_entry or {}).get("directions") or []
                               if isinstance(entry, dict)}
        pack_grouping = _pack_resolved_grouping(list(pack_directions.values()))
        target_directions = [entry for entry in target.get("directions") or []
                             if isinstance(entry, dict)]
        direction_results = []
        structural_flags = []
        statistics_stale = (meta is not None
                            and meta.get("statistics_version")
                            != STAGE2_LEVEL_STATISTICS_VERSION)
        level_refresh_needed = statistics_stale
        for direction in target_directions:
            direction_id = str(direction.get("direction_id"))
            # Resolution consumes the selected candidate union. An artifact in
            # that union can affect every direction even outside its own D set.
            reasons = list(observation_reasons)
            level_changed = False
            validator_ids = [direction_id]
            recorded = recorded_directions.get(direction_id)
            if recorded is None or not isinstance(recorded, dict):
                reasons.append("preflight_record_missing")
            else:
                if recorded.get("target_fingerprint") != stage2_target_fingerprint(direction):
                    reasons.append("target_changed")
                if recorded.get("candidate_fingerprint") != stage2_candidate_fingerprint(
                        snapshot_directions.get(direction.get("direction_id"))):
                    reasons.append("candidate_set_changed")
                # Authoritative resolved output set (issue #7): reuse must prove
                # the recorded provisional→resolved mapping still describes this
                # pack exactly — a split child keeps its own early reuse via its
                # stable resolved ID, and a merged source keeps proving its
                # target mapping — plus every resolved entry still being the
                # accepted one with an intact freshness view.
                recorded_ids = recorded.get("resolved_direction_ids")
                recorded_entries = recorded.get("resolved_entries")
                recorded_merged_into = recorded.get("merged_into")
                if not isinstance(recorded_ids, list) or not isinstance(recorded_entries, dict):
                    # v1-semantics records are already rejected above by the
                    # version gate; an unusable container still fails closed.
                    if recorded_ids is not None or recorded_entries is not None:
                        reasons.append("preflight_record_missing")
                    recorded_ids, recorded_entries = [], {}
                resolved_ids = sorted(str(x) for x in recorded_ids if isinstance(x, str))
                if resolved_ids:
                    validator_ids = resolved_ids
                elif isinstance(recorded_merged_into, str) and recorded_merged_into:
                    # Merged-away source: it owns no pack entry, so its validator
                    # proof is the surviving target's row.
                    validator_ids = [recorded_merged_into]
                now_slot = pack_grouping.get(direction_id) or {"resolved": [], "merged_into": None}
                if resolved_ids != sorted(now_slot["resolved"]):
                    reasons.append("resolved_set_changed")
                if recorded_merged_into != now_slot["merged_into"]:
                    reasons.append("resolved_set_changed")
                for resolved_id in resolved_ids:
                    entry = pack_directions.get(resolved_id)
                    rec = recorded_entries.get(resolved_id)
                    if entry is None or not isinstance(rec, dict):
                        reasons.append("preflight_record_missing")
                        continue
                    if rec.get("accepted_input_fingerprint") != entry.get("input_fingerprint"):
                        reasons.append("pack_integrity_mismatch")
                    elif rec.get("freshness_view_fingerprint") != \
                            stage2_freshness_view_fingerprint(entry, cache_entries):
                        reasons.append("freshness_cache_changed")
                guards = recorded.get("artifact_guards")
                if not isinstance(guards, dict):
                    # An unusable guards container cannot prove artifact freshness.
                    if guards is not None:
                        reasons.append("preflight_record_missing")
                    guards = {}
                for item_key in sorted(guards):
                    kinds = guards[item_key]
                    if not isinstance(kinds, dict):
                        reasons.append("preflight_record_missing")
                        continue
                    for kind in sorted(kinds):
                        guard = kinds[kind]
                        reason = stage2_artifact_guard_reason(guard if isinstance(guard, dict) else {})
                        if reason:
                            reasons.append(reason)
                # Business sources compared apart from the level value: an
                # unreadable/broken record cannot prove nothing changed, while a
                # pure legal level change must stay a level-only refresh.
                recorded_sources = recorded.get("source_projection")
                recorded_levels = recorded.get("level_projection")
                consumed_keys = stage2_group_consumed_keys(
                    pack_directions, pack_grouping, direction_id)
                if not isinstance(recorded_sources, dict) or not isinstance(recorded_levels, dict):
                    reasons.append("source_projection_missing")
                else:
                    if recorded_sources != observed_source_projection(
                            professor_dir, consumed_keys):
                        reasons.append("source_changed")
                    current_levels = observed_level_projection(professor_dir, consumed_keys)
                    if not current_levels.get("valid"):
                        reasons.append("analysis_level_unreadable")
                    elif current_levels.get("values") != recorded_levels:
                        level_changed = True
            validator_reason = stage2_validator_accepts(pack, validator_ids, professor_dir)
            # A pack produced under older membership semantics was certified by
            # that old body: its validator record can neither prove the rebuilt
            # document nor re-arm the early gate, so the direction takes the slow
            # path explicitly instead of borrowing the stale acceptance.
            if meta is not None and meta.get("resolution_semantics_version") != \
                    STAGE2_RESOLUTION_SEMANTICS_VERSION:
                reasons.append("validator_not_accepted")
            if u1_update_needed:
                reasons.append("fixed_evidence_display_update")
            reasons = sorted(set(reasons))
            structural = bool(reasons)
            if structural:
                action = "process"
            elif level_changed or statistics_stale:
                # A validator that is no longer accepted is not a source change:
                # the level-refresh acceptance decides separately whether the old
                # certification can be preserved (equivalent body + valid binding)
                # or must expire, and it never fakes reuse_all.
                action = "refresh_level"
                level_refresh_needed = True
            elif validator_reason:
                action = "process"
            else:
                action = "reuse"
            reason_codes = sorted(set(reasons + ([validator_reason] if validator_reason else [])))
            direction_results.append({
                "direction_id": direction_id, "action": action,
                "reason_codes": reason_codes})
            structural_flags.append(structural)
        professor_action = "process" if (professor_reasons or not target_directions) else None
        if professor_action is None:
            if any(structural_flags):
                professor_action = "process"
            elif level_refresh_needed or any(row["action"] == "refresh_level"
                                             for row in direction_results):
                # Some directions may still only report a validator reason; a
                # level-refresh acceptance covers the whole pack's certification
                # and must not be turned into a slow-path process by them.
                professor_action = "refresh_level"
            elif any(row["action"] == "process" for row in direction_results):
                professor_action = "process"
            else:
                professor_action = "reuse_all"
        preflight_inputs = stage2_preflight_cheap_inputs(
            program_root, professor_dir, professor, target, snapshot_entry, params, current_year)
        # The top-level receipt reports the union of the professor-wide and
        # per-direction reasons, so a failure proven only by a direction's raw
        # render/validator binding (e.g. validator_not_accepted) is visible
        # without re-deriving it from the direction rows. Reuse stays empty.
        reason_codes = sorted(set(professor_reasons).union(
            *[row["reason_codes"] for row in direction_results])) if direction_results \
            else sorted(set(professor_reasons))
        emit({
            "status": "ok",
            "professor": professor,
            "preflight_id": sha256_obj({"professor": professor,
                                        "preflight_inputs": preflight_inputs}),
            "action": professor_action,
            "reason_codes": reason_codes,
            "pack_path": str(pack_path),
            "preflight_inputs": preflight_inputs,
            "directions": direction_results,
        })


    def stage2_plan_bind_preflight(ctx: Stage2Context, preflight_file) -> tuple[dict, str | None]:
        """Bind this plan to one professor-local Stage-2 transaction.

        The plan sits between preflight and finalize, so it must carry the canonical
        identity the preflight proof bound — reopen the same professor-local target,
        reread the exact Stage-1 entry — and never rediscover the transaction from
        the display name or emit jobs from inputs the proof never saw.
        """
        _target, _entry, identity = stage2_transaction_identity(ctx)
        if not preflight_file:
            fail("invalid_params", "stage2-plan requires --preflight-file")
        plan, error = read_json_file(Path(preflight_file))
        if (error or not isinstance(plan, dict) or plan.get("status") != "ok"
                or not isinstance(plan.get("preflight_inputs"), dict)):
            fail("invalid_params", f"preflight file unreadable or not a preflight payload: "
                                   f"{preflight_file}")
        if plan.get("professor") != ctx.professor:
            fail("invalid_params", "preflight file professor mismatch: "
                                   f"{plan.get('professor')!r} != {ctx.professor!r}")
        plan_inputs = plan["preflight_inputs"]
        if plan_inputs.get("identity") != identity:
            soft_exit("needs_refresh", "preflight_inputs_changed", drift=["identity"])
        proof_id = sha256_obj({"professor": plan["professor"], "preflight_inputs": plan_inputs})
        if plan.get("preflight_id") != proof_id:
            soft_exit("needs_refresh", "preflight_inputs_changed", drift=["preflight_proof_id"])
        return identity, proof_id


    def _seal_consumption_plan(ctx, run_dir: Path, proof_id: str,
                               jobs: list, reuse_list: list) -> dict:
        """Bind this run's emitted jobs to the frozen consumption companion."""
        companion_path = getattr(ctx, "consumption_file", None)
        if not ctx.consumption or not isinstance(companion_path, Path):
            fail("invalid_params", "facts has no sealed consumption companion")
        if Path(run_dir).resolve() != companion_path.parent.resolve():
            fail("invalid_params", "run directory does not own the consumption companion")
        data, error = read_json_file(companion_path)
        if error or not isinstance(data, dict):
            fail("invalid_params", f"consumption companion unreadable: {error}")
        if data.get("run_id") != ctx.consumption.get("run_id") \
                or data.get("sources_sha256") != ctx.consumption.get("sources_sha256"):
            fail("invalid_facts", "consumption companion changed before the plan was sealed")
        if isinstance(data.get("stage2_plan"), dict):
            fail("invalid_params", "stage2 plan already sealed for this run")
        facts_raw = ctx.facts_path.read_bytes()
        facts_sha = sha256_bytes(facts_raw)
        if data.get("facts_sha256") not in (None, facts_sha):
            fail("invalid_facts", "facts bytes differ from this run's sealed facts")
        data["facts_sha256"] = facts_sha
        data.setdefault("facts", {"path": str(ctx.facts_path.resolve()),
                                  "sha256": facts_sha, "text": facts_raw.decode("utf-8")})
        data.setdefault("resolve", {"jobs": [], "reuse": [],
                                    "sidecar": copy.deepcopy(data["observation"].get("resolved_source"))})
        _validate_resolution_consumption(data)
        plan_jobs = copy.deepcopy(jobs)
        for job in plan_jobs:
            job["model_input_sha256"] = sha256_obj(job.get("model_input"))
        plan = {
            "run_id": data["run_id"], "sources_sha256": data["sources_sha256"],
            "facts_sha256": facts_sha,
            "resolve_sha256": sha256_obj(data.get("resolve")),
            "preflight_id": proof_id,
            "jobs": plan_jobs,
            "reuse": sorted(reuse_list),
            "sealed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        plan["plan_sha256"] = sha256_obj(plan)
        data["stage2_plan"] = plan
        atomic_json(companion_path, data)
        return plan

    def _validate_resolution_consumption(data):
        resolution = data.get("resolve")
        plan = resolution.get("plan") if isinstance(resolution, dict) else None
        if plan is None:
            return
        if not isinstance(plan, dict) or plan.get("plan_sha256") != sha256_obj({
                key: value for key, value in plan.items() if key != "plan_sha256"}):
            fail("invalid_result_json", "saved resolve plan changed")
        if plan.get("run_id") != data.get("run_id") \
                or plan.get("sources_sha256") != data.get("sources_sha256") \
                or plan.get("facts_sha256") != data.get("facts_sha256"):
            fail("invalid_result_json", "resolve plan has different upstream inputs")
        for job in plan.get("jobs", []):
            if job.get("model_input_sha256") != sha256_obj(job.get("model_input")):
                fail("invalid_result_json", "saved resolve input changed")
        results = resolution.get("results")
        if not isinstance(results, dict) or not isinstance(resolution.get("sidecar"), dict):
            fail("invalid_result_json", "resolve stage is not complete")
        if results.get("run_id") != data.get("run_id") \
                or results.get("plan_sha256") != plan.get("plan_sha256") \
                or results.get("results_dir") != plan.get("results_dir"):
            fail("invalid_result_json", "resolve results have a different round")
        files, omitted = results.get("files"), results.get("omitted", {})
        if not isinstance(files, dict) or not isinstance(omitted, dict):
            fail("invalid_result_json", "resolve result mapping is malformed")
        expected_files = set()
        for job in plan.get("jobs", []):
            filename, key = job["result_file"], job["direction_id"]
            if key in omitted:
                if omitted[key] not in ("user_kept_provisional", "accepted_reuse", "pending_reuse"):
                    fail("invalid_result_json", "resolve omitted job has no valid disposition")
                continue
            expected_files.add(filename)
            record = files.get(filename)
            if not isinstance(record, dict) or record.get("job_id") != job["job_id"] \
                    or record.get("direction_id") != key:
                fail("invalid_result_json", "resolve results do not match the saved jobs")
        if set(files) != expected_files or set(omitted) - {job["direction_id"] for job in plan.get("jobs", [])}:
            fail("invalid_result_json", "resolve result collection changed")
        for filename, entry in results.get("files", {}).items():
            try:
                raw = (Path(results["results_dir"]) / filename).read_bytes()
            except OSError:
                fail("invalid_result_json", "sealed resolve result is missing")
            if sha256_bytes(raw) != entry.get("sha256") or raw.decode("utf-8") != entry.get("text"):
                fail("invalid_result_json", "sealed resolve result changed")

    def stage2_validate_consumption_plan(ctx):
        path = getattr(ctx, "consumption_file", None)
        if path is None:
            return None
        data, error = read_json_file(path)
        plan = (data or {}).get("stage2_plan") if isinstance(data, dict) else None
        if error or not isinstance(plan, dict) or not isinstance(plan.get("jobs"), list):
            fail("invalid_result_json", "this run has no sealed stage2 plan")
        unsigned = {key: value for key, value in plan.items() if key != "plan_sha256"}
        if plan.get("plan_sha256") != sha256_obj(unsigned):
            fail("invalid_result_json", "sealed stage2 plan or actual saved input changed")
        if plan.get("run_id") != data.get("run_id") \
                or plan.get("sources_sha256") != data.get("sources_sha256") \
                or plan.get("facts_sha256") != sha256_bytes(ctx.facts_path.read_bytes()) \
                or plan.get("resolve_sha256") != sha256_obj(data.get("resolve")):
            fail("invalid_result_json", "stage2 plan belongs to different upstream inputs")
        for job in plan["jobs"]:
            if "model_input" not in job or job.get("model_input_sha256") != sha256_obj(job["model_input"]):
                fail("invalid_result_json", "saved model input changed after planning")
        facts_record = data.get("facts") or {}
        if not isinstance(facts_record.get("text"), str) or \
                sha256_bytes(facts_record["text"].encode("utf-8")) != plan.get("facts_sha256"):
            fail("invalid_result_json", "sealed facts material changed")
        _validate_resolution_consumption(data)
        return data

    def mark_consumption_repair(ctx, reason_code, failure=None):
        if reason_code != "unknown_reference_id" or not getattr(ctx, "consumption_file", None):
            return
        if not isinstance(failure, dict) or not failure.get("direction_id") \
                or not failure.get("result_file"):
            return
        data = stage2_validate_consumption_plan(ctx)
        if isinstance(data.get("results"), dict) and data["results"].get("revision") == 0:
            permissions = []
            def permit(filename, path, value, allowed):
                if isinstance(value, str) and value not in allowed:
                    permissions.append({"file": filename, "path": path, "allowed": sorted(allowed)})
            for job in data["stage2_plan"]["jobs"]:
                filename, model = job["result_file"], job["model_input"]
                if job["direction_id"] != failure["direction_id"] \
                        or filename != Path(failure["result_file"]).name:
                    continue
                payload = json.loads(data["results"]["files"][filename]["text"])
                if job["kind"] == "narrative":
                    pools = {"paper": {p["item_key"] for p in model.get("papers", [])},
                             "later": {p["item_key"] for p in model.get("later_papers", [])},
                             "gap": {p["gap_id"] for p in model.get("gaps", [])}}
                    for i, direction in enumerate(payload.get("directions", [])):
                        if (direction.get("direction_id") or direction.get("collection_key")) != job["direction_id"]:
                            continue
                        prefix = ["directions", i]
                        for j, note in enumerate(direction.get("gap_notes", [])):
                            permit(filename, prefix + ["gap_notes", j, "gap_id"], note.get("gap_id"), pools["gap"])
                        for j, block in enumerate(direction.get("positioning", [])):
                            for k, ref in enumerate(block.get("refs", [])):
                                kind = ref.split(":", 1)[0] if isinstance(ref, str) else ""
                                permit(filename, prefix + ["positioning", j, "refs", k], ref,
                                       {kind + ":" + key for key in pools.get(kind, set())})
                            replacements = {}
                            for kind, key in re.findall(r"\{\{([PLG]):([^{}]+)\}\}", block.get("text", "")):
                                pool = pools[{"P": "paper", "L": "later", "G": "gap"}[kind]]
                                if key not in pool:
                                    replacements["{{" + kind + ":" + key + "}}"] = ["{{" + kind + ":" + value + "}}" for value in sorted(pool)]
                            if replacements:
                                permissions.append({"file": filename, "path": prefix + ["positioning", j, "text"],
                                                    "replacements": replacements})
                elif job["kind"] == "freshness":
                    gaps = {gap["gap_id"]: gap for gap in model.get("gaps", [])}
                    for i, row in enumerate(payload.get("results", [])):
                        permit(filename, ["results", i, "gap_id"], row.get("gap_id"), set(gaps))
                        gap = gaps.get(row.get("gap_id")) or {}
                        allowed = {p["item_key"] for p in (gap.get("candidates") or {}).get("papers", [])}
                        for j, key in enumerate(row.get("candidate_paper_ids", [])):
                            permit(filename, ["results", i, "candidate_paper_ids", j], key, allowed)
            data["repair_authorization"] = {"reason_code": reason_code, "revision": 0,
                                              "direction_id": failure["direction_id"],
                                              "result_file": Path(failure["result_file"]).name,
                                              "permissions": permissions}
            atomic_json(ctx.consumption_file, data)

    def stage2_preflight_payload_professor(facts_path, preflight_file) -> str:
        """Validate the saved proof before constructing the frozen context.

        A missing/unreadable payload or one belonging to another professor is an
        input error, not evidence that this run's frozen sources changed.
        """
        if not preflight_file:
            fail("invalid_params", "stage2 command requires --preflight-file")
        plan, error = read_json_file(Path(preflight_file))
        if error or not isinstance(plan, dict) or plan.get("status") != "ok" \
                or not isinstance(plan.get("preflight_inputs"), dict):
            fail("invalid_params",
                 f"preflight file unreadable or not a preflight payload: {preflight_file}")
        facts, facts_error = read_json_file(Path(facts_path))
        if facts_error is None and isinstance(facts, dict):
            professor = facts.get("professor")
            if isinstance(professor, str) and professor \
                    and plan.get("professor") != professor:
                fail("invalid_params", "preflight file professor mismatch")
        return plan

    def cmd_stage2_plan(args) -> None:
        stage2_preflight_payload_professor(args.facts, getattr(args, "preflight_file", None))
        ctx = Stage2Context(Path(args.facts))
        ctx.validate_consumption_current()
        identity, proof_id = stage2_plan_bind_preflight(ctx, getattr(args, "preflight_file", None))
        jobs, reuse_list, process_list = [], [], []
        for plan in ctx.direction_plans:
            ckey = plan["did"]
            if plan["reuse"]:
                reuse_list.append(ckey)
                continue
            process_list.append(ckey)
            judge, hits = ctx.freshness_job_items(plan)
            pending = [item for item in judge if not item["cached"]]
            if pending:
                job_gaps = []
                for item in pending:
                    gap, cands = item["gap"], item["cands"]
                    materials = []
                    for tier in ("confirmed_family", "authorship", "recent", "topic"):
                        for key in cands["tiers"][tier]:
                            paper = ctx.papers[key]
                            materials.append({
                                "item_key": key, "title": paper.get("title"),
                                "year": paper.get("year"), "tier": tier,
                                "abstract": truncate(paper.get("abstract"), ABSTRACT_INPUT_CHARS)})
                    job_gaps.append({
                        "gap_id": gap["gap_id"], "item_key": gap["item_key"],
                        "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
                        "quote": truncate(gap.get("quote"), QUOTE_INPUT_CHARS),
                        "translation_zh": truncate(gap.get("translation_zh"), TRANSLATION_INPUT_CHARS),
                        "candidates": {
                            "papers": materials, "later_total": cands["later_total"],
                            "unverifiable_count": cands["excluded_no_clue"]},
                        "note": "禁止「标题无命中直接写 open」；candidates 为空且 later_total>0 → unknown（unverifiable_count 条无法核对）；candidates 为空且 later_total=0 → open 并说明"})
                jobs.append({
                    "job_id": f"freshness:{ctx.professor}:{ckey}", "kind": "freshness",
                    "direction_id": ckey,
                    "result_file": f"freshness-{filename_component(ckey)}.json",
                    "result_schema": {"schema": 1, "kind": "freshness", "direction_id": ckey,
                                      "results": [{"gap_id": "", "status": "open|partial|done_by_self|unknown",
                                                   "candidate_paper_ids": [], "evidence": "",
                                                   "completed_part": "", "remaining_gap": "",
                                                   "confidence": "high|medium|low"}]},
                    "model_input": {"gaps": job_gaps}})
            jobs.append({
                "job_id": f"narrative:{ctx.professor}:{ckey}", "kind": "narrative",
                "direction_id": ckey,
                "result_file": "narrative.json",
                "result_schema": {"schema": 1, "kind": "narrative", "directions": [
                    {"direction_id": ckey, "positioning": [
                        {"kind": "para|bullet", "text": "…{{P:ITEMKEY}}…{{G:GAPID}}…",
                         "refs": ["paper:ITEMKEY", "gap:GAPID"],
                         "concrete_object": "用于比较两种处理方式的合成样本",
                         "input_example": "输入一组固定的合成样本",
                         "output_example": "得到两种处理方式各自的评估结果"}],
                     "gap_notes": [{"gap_id": "", "summary": "一句话概括", "explanation": "大白话≤3句"}]}]},
                "model_input": {
                    "direction_id": ckey,
                    "user_note": plan["direction"].get("user_note") or "",
                    "credibility": plan["direction"].get("credibility"),
                    "papers": [{"item_key": key, "title": ctx.papers[key].get("title"),
                                "year": ctx.papers[key].get("year"),
                                "authorship": ctx.papers[key].get("authorship")}
                               for key in direction_relevant_keys(plan["direction"]) if key in ctx.papers],
                     "later_papers": [{"item_key": key, "title": ctx.papers[key].get("title"),
                                       "year": ctx.papers[key].get("year"),
                                       "authorship": ctx.papers[key].get("authorship"),
                                       "abstract": truncate(ctx.papers[key].get("abstract"), ABSTRACT_INPUT_CHARS)}
                                      for key in ctx.narrative_later_keys(plan) if key in ctx.papers],
                     "gaps": [{"gap_id": g["gap_id"], "item_key": g["item_key"],
                               "paper_title": g.get("paper_title"), "paper_year": g.get("paper_year"),
                               "quote": truncate(g.get("quote"), 200),
                               "translation_zh": truncate(g.get("translation_zh"), 200)}
                              for g in plan["ranked"]],
                     "rules": "text 里用 {{P:KEY}} 引方向论文、{{L:KEY}} 引后续论文、{{G:GAPID}} 引 future work；refs 必须与占位符一一对应（集合相等）；叙事不得断言 gap_status（状态由 runner 渲染的 freshness 卡承载）；不得把未在 papers/later_papers/gaps 清单里的 ID 写进 refs；每个 positioning block 必须提供 concrete_object、input_example、output_example 三个具体例子字段，且只能依据对应 papers/gaps"}})
        saved_plan = None
        if getattr(args, "run_dir", None):
            saved_plan = _seal_consumption_plan(ctx, Path(args.run_dir), proof_id, jobs, reuse_list)
        emit({
            "status": "ok",
            "professor": ctx.professor,
            "professor_dir": str(ctx.professor_dir),
            "preflight_id": proof_id,
            "transaction_identity": identity,
            "pack_path": str(ctx.pack_path),
            "params": {"gap_scope": ctx.gap_scope, "freshness_scope": ctx.freshness_scope},
            "directions": [{
                "direction_id": p["did"], "action": "reuse" if p["reuse"] else "process",
                "gap_pool": len(p["pool"]),
                "judge_count": len(ctx.judge_set(p)) if not p["reuse"] else 0,
                "reason_code": ("shortlist_over_limit" if len(p["ranked"]) > SHORTLIST_MAX and
                                ctx.freshness_scope == "shortlist" else None),
            } for p in ctx.direction_plans],
            "jobs": jobs,
            "plan_file": str(ctx.consumption_file) if saved_plan else None,
            "plan_path": ["stage2_plan"] if saved_plan else None,
            "plan_sha256": saved_plan.get("plan_sha256") if saved_plan else None,
            "write_needed": bool(jobs),
        })

    def cmd_stage2_consumption_seal_results(args) -> None:
        """Seal the complete aggregated result files for the sealed stage2 plan."""
        run_dir = Path(args.run_dir)
        companion_path = run_dir / "stage2-consumption.json"
        data, error = read_json_file(companion_path)
        if error or not isinstance(data, dict):
            fail("invalid_params", f"consumption companion unreadable: {error}")
        plan = data.get("stage2_plan")
        if not isinstance(plan, dict) or not isinstance(plan.get("jobs"), list):
            fail("invalid_params", "stage2 plan is not sealed for this run")
        results_dir = Path(args.results_dir)
        if not results_dir.is_dir():
            fail("invalid_result_json", f"results directory does not exist: {results_dir}")
        previous = data.get("results")
        revision = 0
        if isinstance(previous, dict):
            authorization = data.get("repair_authorization")
            if previous.get("revision") != 0 or not isinstance(authorization, dict) \
                    or authorization.get("reason_code") != "unknown_reference_id" \
                    or authorization.get("revision") != 0 \
                    or not authorization.get("permissions"):
                fail("invalid_params", "this run has no remaining result repair")
            if previous.get("results_dir") == str(results_dir.resolve()):
                fail("invalid_params", "repair must use a new results directory")
            revision = 1
        requested_revision = getattr(args, "repair_revision", None)
        if requested_revision is not None and requested_revision != revision:
            fail("invalid_params", "requested result revision is not authorized")
        unsigned = {key: value for key, value in plan.items() if key != "plan_sha256"}
        if sha256_obj(unsigned) != plan.get("plan_sha256"):
            fail("invalid_result_json", "sealed stage2 input changed")
        files = {}
        for job in plan["jobs"]:
            filename = job.get("result_file")
            if not isinstance(filename, str) or not filename:
                fail("invalid_params", "sealed job has no result_file")
            path = results_dir / filename
            try:
                raw = path.read_bytes()
            except OSError as exc:
                fail("invalid_result_json", f"sealed result file missing: {path}: {exc}")
            digest = sha256_bytes(raw)
            try:
                content = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                fail("invalid_result_json", f"result is not UTF-8 JSON: {path}")
            if not isinstance(content, dict) or content.get("kind") != job.get("kind"):
                fail("invalid_result_json", f"result kind does not match the sealed job: {path}")
            entry = files.setdefault(filename, {"sha256": digest, "bytes": len(raw),
                                                "text": raw.decode("utf-8"),
                                                "jobs": [], "directions": []})
            if entry["sha256"] != digest:
                fail("invalid_result_json", f"result file changed while sealing: {path}")
            entry["jobs"].append(job["job_id"])
            if job.get("direction_id") not in entry["directions"]:
                entry["directions"].append(job["direction_id"])
        for filename, entry in files.items():
            content = json.loads(entry["text"])
            jobs = [job for job in plan["jobs"] if job["result_file"] == filename]
            if jobs[0]["kind"] == "narrative":
                directions = content.get("directions")
                actual = [d.get("direction_id") or d.get("collection_key") for d in directions if isinstance(d, dict)] \
                    if isinstance(directions, list) else []
                if len(actual) != len(set(actual)) or set(actual) != set(entry["directions"]):
                    fail("invalid_result_json", "aggregated narrative directions are incomplete")
            elif any((content.get("direction_id") or content.get("collection_key")) != job["direction_id"] for job in jobs):
                fail("invalid_result_json", "result direction does not match sealed jobs")
        if revision:
            if set(files) != set(previous.get("files") or {}):
                fail("invalid_result_json", "repair changed the sealed result file set")
            def reference_repair(old, new, filename, path=None):
                path = [] if path is None else path
                if type(old) is not type(new):
                    return False
                if isinstance(old, dict):
                    return set(old) == set(new) and all(reference_repair(old[k], new[k], filename, path + [k]) for k in old)
                if isinstance(old, list):
                    return len(old) == len(new) and all(reference_repair(a, b, filename, path + [i]) for i, (a, b) in enumerate(zip(old, new)))
                if old == new:
                    return True
                if not isinstance(old, str):
                    return False
                permission = next((p for p in authorization["permissions"]
                                   if p["file"] == filename and p["path"] == path), None)
                if permission is None:
                    return False
                if "allowed" in permission:
                    return new in permission["allowed"]
                replacements = permission.get("replacements", {})
                old_parts = re.split(r"(\{\{[PLG]:[^{}]+\}\})", old)
                new_parts = re.split(r"(\{\{[PLG]:[^{}]+\}\})", new)
                return len(old_parts) == len(new_parts) and all(
                    b in replacements[a] if a in replacements else a == b
                    for a, b in zip(old_parts, new_parts))
            for name, entry in files.items():
                original = previous["files"][name]
                if not reference_repair(json.loads(original["text"]), json.loads(entry["text"]), name):
                    fail("invalid_result_json", "repair changed content beyond reference identifiers")
            data.setdefault("results_revisions", []).append(copy.deepcopy(previous))
            data.pop("repair_authorization", None)
        data["results"] = {"revision": revision, "run_id": data["run_id"],
                           "plan_sha256": plan["plan_sha256"],
                           "results_dir": str(results_dir.resolve()), "files": files,
                           "sealed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        atomic_json(companion_path, data)
        emit({"status": "ok", "consumption_file": str(companion_path),
              "revision": revision, "files": sorted(files)})

    def cmd_stage2_consumption_prepare(args) -> None:
        """Freeze the sources this run will consume before facts are assembled.

        The companion is private to the current temporary transaction; it never
        becomes a professor-level authority. The facts block may point at it and
        later finalize can prove its source projection is still the same.
        """
        plan, error = read_json_file(Path(args.preflight_file))
        if error or not isinstance(plan, dict) or plan.get("status") != "ok" \
                or not isinstance(plan.get("preflight_inputs"), dict):
            fail("invalid_params",
                 f"preflight file unreadable or not a preflight payload: {args.preflight_file}")
        if plan.get("professor") != args.professor:
            fail("invalid_params", "preflight file professor mismatch")
        program_root = Path(args.program_root)
        target = read_stage2_target(Path(args.target_file), program_root, args.professor)
        if target is None:
            fail("invalid_params",
                 "professor has no selected target state; run contact_targets.py resolve first")
        professor_dir = program_root / str(target.get("professor_dir") or "")
        snapshot = read_stage1_professor_entry(
            program_root, professor_dir, args.professor, target)
        if snapshot is None:
            fail("invalid_params", "Stage-1 professor snapshot is missing or unreadable")
        candidate_keys = sorted(stage2_candidate_universe(target, snapshot))
        inputs = plan["preflight_inputs"]
        business = _business_inputs(program_root, professor_dir, args.professor, target,
                                    snapshot, inputs.get("params") or {}, inputs.get("current_year"))
        declarations = None
        if getattr(args, "sources_file", None):
            declarations, error = read_json_file(Path(args.sources_file))
            if error or not isinstance(declarations, (dict, list)):
                fail("invalid_params", "source declarations are unreadable")
        sources = freeze_stage2_sources(professor_dir, candidate_keys,
            business_inputs=business, declared_sources=declarations)
        current_target = read_stage2_target(Path(args.target_file), program_root, args.professor)
        current_snapshot = read_stage1_professor_entry(program_root, professor_dir, args.professor,
                                                       current_target)
        current_business = _business_inputs(program_root, professor_dir, args.professor,
            current_target, current_snapshot, inputs.get("params") or {}, datetime.now().year)
        if current_business != business:
            fail("invalid_facts", "business inputs changed while preparing frozen material")
        projection = sources["projection"]
        sources_sha256 = sha256_obj(sources)
        run_dir = Path(args.run_dir)
        if not run_dir.is_dir():
            fail("invalid_params", f"run directory does not exist: {run_dir}")
        companion = run_dir / "stage2-consumption.json"
        if companion.exists():
            fail("invalid_params", f"consumption companion already exists: {companion}")
        data = {
            "schema": 1, "version": 1, "run_id": uuid.uuid4().hex,
            "preflight_id": plan.get("preflight_id"),
            "professor": args.professor,
            "professor_dir": str(professor_dir.resolve()),
            "program_root": str(program_root.resolve()),
            "candidate_keys": candidate_keys,
            "sources": sources,
            "sources_projection": projection,
            "sources_sha256": sources_sha256,
            "identity": inputs.get("identity"),
        }
        existing_pack, _ = load_input_pack(professor_dir)
        data["observation"] = stage2_complete_observation(program_root, professor_dir,
            args.professor, target, snapshot, business["params"], business["current_year"],
            existing_pack, sources=sources)
        atomic_json(companion, data)
        emit({"status": "ok", "consumption_file": str(companion),
              "run_id": data["run_id"], "sources_sha256": sources_sha256,
              "professor": args.professor,
              "professor_dir": data["professor_dir"]})


    return types.SimpleNamespace(
        stage2_preflight_versions=stage2_preflight_versions,
        stage2_preflight_params=stage2_preflight_params,
        stage2_target_fingerprint=stage2_target_fingerprint,
        stage2_candidate_fingerprint=stage2_candidate_fingerprint,
        stage2_candidate_universe=stage2_candidate_universe,
        stage2_papers_catalog_view_fingerprint=stage2_papers_catalog_view_fingerprint,
        stage2_authorship_ledger_view_fingerprint=stage2_authorship_ledger_view_fingerprint,
        stage2_program_inputs=stage2_program_inputs,
        stage2_complete_observation=stage2_complete_observation,
        stage2_compare_observation=stage2_compare_observation,
        stage2_consumption_drift=stage2_consumption_drift,
        stage2_validate_consumption_plan=stage2_validate_consumption_plan,
        mark_consumption_repair=mark_consumption_repair,
        stage2_target_path=stage2_target_path,
        read_stage2_target=read_stage2_target,
        stage2_local_identity=stage2_local_identity,
        stage2_transaction_identity=stage2_transaction_identity,
        stage2_preflight_cheap_inputs=stage2_preflight_cheap_inputs,
        stage2_artifact_guard=stage2_artifact_guard,
        stage2_artifact_guard_reason=stage2_artifact_guard_reason,
        _artifact_guards_for_keys=_artifact_guards_for_keys,
        stage2_direction_artifact_guards=stage2_direction_artifact_guards,
        stage2_resolution_evidence_guards=stage2_resolution_evidence_guards,
        _pack_resolved_grouping=_pack_resolved_grouping,
        stage2_consumed_source_keys=stage2_consumed_source_keys,
        stage2_group_consumed_keys=stage2_group_consumed_keys,
        stage2_level_projection=stage2_level_projection,
        stage2_pdf_source_projection=stage2_pdf_source_projection,
        stage2_refresh_preflight_metadata=stage2_refresh_preflight_metadata,
        stage2_freshness_view_fingerprint=stage2_freshness_view_fingerprint,
        stage2_preflight_metadata=stage2_preflight_metadata,
        stage2_preflight_payload_professor=stage2_preflight_payload_professor,
        stage2_pack_state_fingerprint=stage2_pack_state_fingerprint,
        stage2_pack_content_fingerprint=stage2_pack_content_fingerprint,
        stage2_validator_accepts=stage2_validator_accepts,
        cmd_stage2_preflight=cmd_stage2_preflight,
        cmd_stage2_consumption_prepare=cmd_stage2_consumption_prepare,
        cmd_stage2_consumption_seal_results=cmd_stage2_consumption_seal_results,
        stage2_plan_bind_preflight=stage2_plan_bind_preflight,
        cmd_stage2_plan=cmd_stage2_plan,
    )

