#!/usr/bin/env python3
"""Stage-2 resolve-plan layer for ``contact_state.py``.

The runner loads this helper by path next to itself and calls :func:`build`
once with its own helper functions and shared constants. The factory binds
those names in an enclosing scope, so the functions below keep the exact
bodies they had inside the runner (only their indentation changed). The module
never imports the runner, never adds itself to ``sys.path`` and never builds a
second failure channel.
"""
from __future__ import annotations

import types
from pathlib import Path


MERGE_MIN_SHARED = 2

MERGE_MIN_FACTS_PAPERS = 2

MERGE_MIN_SHARED_TERMS = 3

MERGE_TOPIC_OVERLAP = 0.5

# Authoritative-merge validation floor: deliberately weaker than the detector
# hint thresholds above. The model, not the detector, judges merges from
# full-text evidence — the validator only refuses merges with no full-text
# grounding at all, it does not re-run hint detection.
MERGE_VALIDATION_MIN_FACTS_PAPERS = 1

MERGE_VALIDATION_MIN_SHARED_TERMS = 2

RESOLVE_INPUT_FINGERPRINT_VERSION = 4


def build(*, AUTHORSHIP_RANK,
          Stage2Context,
          _facts_preflight_proof,
          _load_existing_resolved,
          direction_candidate_keys,
          selected_candidate_union,
          emit,
          fail,
          filename_component,
          sha256_obj,
          truncate):
    def _compute_paper_direction_affinity(ctx: Stage2Context) -> dict[str, dict[str, dict]]:
        """Compute per-paper affinity scores to each provisional direction using full-text facts.

        Returns {item_key: {ckey: {"total": score, "fulltext": score}}} where:
        - `total` derives from topic_terms overlap, provisional membership,
          authorship weight, and gap contribution (full picture, shown to the model)
        - `fulltext` isolates ONLY the full-text evidence (facts topic_terms vs the
          direction profile; title overlap as fallback when no facts exist).
          Membership comparison must use the full-text component alone: provisional
          membership, gap contribution, and authorship are abstract-level priors or
          artifacts of the provisional assignment — mixing them into the comparison
          lets the prior outweigh full-text evidence forever, which defeats the
          whole point of issue #7.
        """
        import re as _re
        import unicodedata as _ud

        def _tokens(text: str) -> set:
            toks = set()
            for w in _re.findall(r"[A-Za-z0-9]+", text or ""):
                if len(w) >= 3:
                    toks.add(w.lower())
            for run in _re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", text or ""):
                for i in range(len(run) - 1):
                    toks.add(run[i:i + 2])
            return toks

        direction_profiles: dict[str, set] = {}
        for plan in ctx.direction_plans:
            direction = plan["direction"]
            parts = []
            for field in ("name_ja", "name_zh", "summary_zh"):
                val = direction.get(field)
                if isinstance(val, str) and val.strip():
                    parts.append(val)
            direction_profiles[plan["did"]] = _tokens(" ".join(parts))

        affinity: dict[str, dict[str, dict]] = {}
        union_keys = selected_candidate_union(ctx)
        for plan in ctx.direction_plans:
            ckey = plan["did"]
            profile_toks = direction_profiles[ckey]
            gap_item_keys = {g["item_key"] for g in plan["pool"]}
            # Affinity is resolution evidence: it must cover the full candidate
            # universe so a paper the abstract relevance gate dropped can still be
            # scored against every direction from full-text facts — including
            # papers whose own provisional direction is a different one.
            for key in union_keys:
                paper = ctx.papers.get(key)
                if not paper:
                    continue
                score = 0.0
                fulltext = 0.0
                # Base affinity from provisional membership
                if key in (plan["direction"].get("provisional_member_keys") or []):
                    score += 2.0
                # Authorship weight
                auth = paper.get("authorship", "pending")
                score += AUTHORSHIP_RANK.get(auth, 0) / 5.0
                # Gap contribution: paper contributes future-work to this direction
                if key in gap_item_keys:
                    score += 1.5
                # Topic overlap from full-text facts
                facts_record, _, _ = ctx.facts_for(key)
                if facts_record:
                    topic_terms = facts_record.get("topic_terms") or []
                    paper_toks = _tokens(" ".join(str(t) for t in topic_terms))
                    if profile_toks and paper_toks:
                        overlap = len(paper_toks & profile_toks)
                        score += overlap * 0.3
                        fulltext += overlap * 0.3
                # Title overlap as fallback when no facts
                elif paper.get("title"):
                    title_toks = _tokens(paper["title"])
                    if profile_toks and title_toks:
                        overlap = len(title_toks & profile_toks)
                        score += overlap * 0.2
                        fulltext += overlap * 0.2
                affinity.setdefault(key, {})[ckey] = {
                    "total": round(score, 3),
                    "fulltext": round(fulltext, 3),
                }
        return affinity

    def _detect_candidates_for_addition(ctx: Stage2Context, affinity: dict[str, dict[str, dict]]) -> list[dict]:
        """Detect papers whose full-text evidence points to a different direction than their provisional one.

        Paper-centric: for every paper, if the strongest FULL-TEXT affinity
        direction is NOT the paper's current provisional direction, the paper is a
        cross-cluster candidate that the strongest direction should add. The
        comparison uses only the full-text component of the affinity score —
        provisional membership, gap contribution, and authorship are priors, not
        evidence, and must never outweigh what the paper's full text actually says.

        A candidate is emitted when:
        - paper has full-text affinity to at least one direction
        - the strongest full-text direction is different from the paper's
          provisional direction (resolved from any selected direction the paper
          belongs to)
        - the full-text affinity gap between top and provisional is significant
          (>= 1.0)

        Papers are scored over the professor-level candidate union, so the target
        direction does NOT need to have Stage-1-expanded the paper itself: a
        cross-preview-cluster paper reaches the target through the union.
        """
        # Build map of paper -> provisional directions (any selected direction whose
        # provisional_member_keys contain the paper).
        paper_provisional: dict[str, list[str]] = {}
        for plan in ctx.direction_plans:
            for key in plan["direction"].get("provisional_member_keys") or []:
                paper_provisional.setdefault(key, []).append(plan["did"])

        additions = []
        seen: set[tuple[str, str]] = set()

        def _fulltext(score) -> float:
            # Accept both the {total, fulltext} score dict and a bare float
            # (a bare float is understood AS the full-text component).
            if isinstance(score, dict):
                return float(score.get("fulltext") or 0.0)
            return float(score or 0.0)

        for key, paper_aff in affinity.items():
            if not paper_aff:
                continue
            # Rank directions by the FULL-TEXT component only.
            sorted_dirs = sorted(paper_aff.items(), key=lambda kv: _fulltext(kv[1]), reverse=True)
            if not sorted_dirs:
                continue
            top_ckey, top_scores = sorted_dirs[0]
            top_score = _fulltext(top_scores)
            provisional_dirs = paper_provisional.get(key, [])
            # If the strongest direction IS the paper's provisional direction, no
            # cross-cluster addition is needed.
            if top_ckey in provisional_dirs:
                continue
            # Find this paper's current (weaker) provisional full-text score, if any.
            provisional_scores = [_fulltext(paper_aff.get(d)) for d in provisional_dirs]
            max_provisional = max(provisional_scores) if provisional_scores else 0
            if top_score <= max_provisional + 1.0:
                continue
            # Avoid duplicate (paper, target) entries when iterating multi-direction plans.
            if (key, top_ckey) in seen:
                continue
            seen.add((key, top_ckey))
            additions.append({
                "item_key": key,
                "target_direction": top_ckey,
                "current_provisional_direction": provisional_dirs[0] if provisional_dirs else None,
                "target_score": top_score,
                "provisional_score": max_provisional,
                "reason": (
                    f"paper full-text affinity strongest in {top_ckey}={top_score} "
                    f"vs provisional={max_provisional} ({provisional_dirs[0] if provisional_dirs else 'none'})"
                ),
            })
        return additions

    def _detect_candidates_for_removal(ctx: Stage2Context, affinity: dict[str, dict[str, float]]) -> list[dict]:
        """Detect provisional members that full-text evidence suggests don't belong.

        A candidate for removal when:
        - paper is a provisional member
        - paper has full-text facts with topic_terms that don't overlap direction profile

        Note: gap contribution does NOT prevent removal — a paper can contribute a
        relevant gap to a direction without being a member of that direction.
        Removal only affects membership, not gap provenance.
        """
        import re as _re
        removals = []
        for plan in ctx.direction_plans:
            ckey = plan["did"]
            direction = plan["direction"]
            profile_parts = []
            for field in ("name_ja", "name_zh", "summary_zh"):
                val = direction.get(field)
                if isinstance(val, str) and val.strip():
                    profile_parts.append(val)
            profile_text = " ".join(profile_parts).lower()
            # Also build a set of profile tokens for more flexible matching
            profile_toks = set()
            for w in _re.findall(r"[A-Za-z0-9]+", profile_text):
                if len(w) >= 3:
                    profile_toks.add(w.lower())
            for run in _re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", profile_text):
                for i in range(len(run) - 1):
                    profile_toks.add(run[i:i + 2])
            for key in direction.get("provisional_member_keys") or []:
                paper = ctx.papers.get(key)
                if not paper:
                    continue
                facts_record, facts_state, _ = ctx.facts_for(key)
                if facts_state != "valid":
                    continue  # can't judge without full-text facts
                topic_terms = (facts_record or {}).get("topic_terms") or []
                title = (paper.get("title") or "").lower()
                # Check if any topic term or title token overlaps with direction profile
                has_overlap = False
                for term in topic_terms:
                    term_lower = str(term).lower()
                    if term_lower in profile_text:
                        has_overlap = True
                        break
                    # Check token-level overlap for multi-word terms
                    for tok in _re.findall(r"[A-Za-z0-9]+", term_lower):
                        if len(tok) >= 3 and tok in profile_toks:
                            has_overlap = True
                            break
                    if has_overlap:
                        break
                if not has_overlap:
                    # Check title tokens against profile tokens
                    title_toks = set()
                    for w in _re.findall(r"[A-Za-z0-9]+", title):
                        if len(w) >= 3:
                            title_toks.add(w.lower())
                    for run in _re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", title):
                        for i in range(len(run) - 1):
                            title_toks.add(run[i:i + 2])
                    if title_toks and profile_toks and title_toks & profile_toks:
                        has_overlap = True
                if not has_overlap:
                    removals.append({
                        "item_key": key,
                        "direction": ckey,
                        "title": paper.get("title"),
                        "topic_terms": topic_terms[:5],
                        "reason": "full-text topic terms do not overlap direction profile",
                    })
        return removals

    def _detect_split_candidates(ctx: Stage2Context) -> list[dict]:
        """Detect directions that may need splitting based on distinct topic clusters.

        A direction is a split candidate when:
        - It has ≥4 papers with full-text facts
        - Topic terms cluster into ≥2 distinct groups with low inter-group overlap
        """
        import re as _re
        splits = []
        for plan in ctx.direction_plans:
            ckey = plan["did"]
            direction = plan["direction"]
            papers_with_facts = []
            for key in direction_candidate_keys(direction):
                paper = ctx.papers.get(key)
                if not paper:
                    continue
                facts_record, facts_state, _ = ctx.facts_for(key)
                if facts_state == "valid" and facts_record:
                    papers_with_facts.append({
                        "item_key": key,
                        "title": paper.get("title"),
                        "topic_terms": facts_record.get("topic_terms") or [],
                    })
            if len(papers_with_facts) < 4:
                continue
            # Simple clustering: group papers by shared topic terms
            clusters: list[list[dict]] = []
            for paper in papers_with_facts:
                terms = set(str(t).lower() for t in paper["topic_terms"])
                matched = False
                for cluster in clusters:
                    cluster_terms = set()
                    for cp in cluster:
                        cluster_terms.update(str(t).lower() for t in cp["topic_terms"])
                    if terms and cluster_terms and len(terms & cluster_terms) / max(len(terms), 1) >= 0.3:
                        cluster.append(paper)
                        matched = True
                        break
                if not matched:
                    clusters.append([paper])
            # Filter: only suggest split if we have ≥2 substantial clusters (≥2 papers each)
            substantial = [c for c in clusters if len(c) >= 2]
            if len(substantial) >= 2:
                splits.append({
                    "direction": ckey,
                    "name_ja": direction.get("name_ja"),
                    "name_zh": direction.get("name_zh"),
                    "clusters": [
                        {
                            "papers": [p["item_key"] for p in cluster],
                            "titles": [p["title"] for p in cluster],
                            "common_terms": sorted(set.intersection(*[
                                set(str(t).lower() for t in p["topic_terms"]) for p in cluster
                            ])) if cluster else [],
                        }
                        for cluster in substantial
                    ],
                    "reason": f"direction splits into {len(substantial)} distinct topic clusters",
                })
        return splits

    def _profile_topic_tokens(direction: dict) -> set:
        """Tokenize name_ja/name_zh/summary_zh into a comparable topic-profile set."""
        import re as _re
        parts = []
        for field in ("name_ja", "name_zh", "summary_zh"):
            val = direction.get(field)
            if isinstance(val, str) and val.strip():
                parts.append(val)
        toks: set = set()
        for w in _re.findall(r"[A-Za-z0-9]+", " ".join(parts)):
            if len(w) >= 3:
                toks.add(w.lower())
        for run in _re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", " ".join(parts)):
            for idx in range(len(run) - 1):
                toks.add(run[idx:idx + 2])
        return toks

    def _direction_fulltext_terms(ctx: Stage2Context, direction: dict) -> tuple[int, set]:
        """Count of currently facts-valid candidate papers + their topic-term union."""
        count = 0
        terms: set = set()
        for key in direction_candidate_keys(direction):
            if not ctx.papers.get(key):
                continue
            facts_record, facts_state, _ = ctx.facts_for(key)
            if facts_state == "valid" and facts_record:
                count += 1
                terms.update(str(t).lower() for t in (facts_record.get("topic_terms") or []))
        return count, terms

    def _merge_fulltext_basis(ctx: Stage2Context, source_direction: dict,
                              target_direction: dict) -> dict | None:
        """Full-text convergence between two directions at DETECTOR hint strength.

        Both directions hold ≥MERGE_MIN_FACTS_PAPERS currently facts-valid
        candidate papers whose topic terms converge (≥MERGE_MIN_SHARED_TERMS
        shared terms, ≥MERGE_TOPIC_OVERLAP of the smaller term set). Used to
        propose merge candidates to the resolve model — never as the
        authoritative-result gate (see `_authoritative_merge_basis`).
        """
        count_a, terms_a = _direction_fulltext_terms(ctx, source_direction)
        count_b, terms_b = _direction_fulltext_terms(ctx, target_direction)
        shared_terms = terms_a & terms_b
        smaller = min(len(terms_a), len(terms_b))
        if (count_a >= MERGE_MIN_FACTS_PAPERS
                and count_b >= MERGE_MIN_FACTS_PAPERS
                and len(shared_terms) >= MERGE_MIN_SHARED_TERMS
                and len(shared_terms) / smaller >= MERGE_TOPIC_OVERLAP):
            return {
                "merge_basis": "fulltext_convergence",
                "shared_topic_terms": sorted(shared_terms),
                "overlap_ratio": round(len(shared_terms) / smaller, 2),
                "facts_papers": {"source": count_a, "target": count_b},
            }
        return None

    def _authoritative_merge_basis(ctx: Stage2Context, source_direction: dict,
                                   target_direction: dict) -> dict | None:
        """Deterministic evidence floor for AUTHORITATIVE merged_into results.

        Both directions must hold at least one currently facts-valid candidate
        paper and their full-text topic terms must converge (≥2 shared terms,
        ≥MERGE_TOPIC_OVERLAP of the smaller term set). This is a floor, not a
        re-detection: shared candidate papers plus profile overlap is
        provisional-level evidence and never satisfies it on its own.
        """
        count_a, terms_a = _direction_fulltext_terms(ctx, source_direction)
        count_b, terms_b = _direction_fulltext_terms(ctx, target_direction)
        shared_terms = terms_a & terms_b
        smaller = min(len(terms_a), len(terms_b))
        if (count_a >= MERGE_VALIDATION_MIN_FACTS_PAPERS
                and count_b >= MERGE_VALIDATION_MIN_FACTS_PAPERS
                and len(shared_terms) >= MERGE_VALIDATION_MIN_SHARED_TERMS
                and len(shared_terms) / smaller >= MERGE_TOPIC_OVERLAP):
            return {
                "merge_basis": "fulltext_convergence",
                "shared_topic_terms": sorted(shared_terms),
                "overlap_ratio": round(len(shared_terms) / smaller, 2),
                "facts_papers": {"source": count_a, "target": count_b},
            }
        return None

    def _direction_has_valid_fulltext(ctx: Stage2Context, direction: dict) -> bool:
        """True when at least one candidate paper currently has valid full-text facts."""
        for key in direction_candidate_keys(direction):
            if not ctx.papers.get(key):
                continue
            _record, state, _error = ctx.facts_for(key)
            if state == "valid":
                return True
        return False

    def _detect_merge_candidates(ctx: Stage2Context) -> list[dict]:
        """Detect pairs of directions that may be the same research line.

        Preview clusters are provisional, so issue #7 makes full-text evidence —
        not provisional overlap — the merge signal. A merge candidate when either:
        - The two candidate unions share ≥2 papers AND their topic profiles overlap
          significantly (a single shared paper can be a chance co-incidence), or
        - `_merge_fulltext_basis` converges: both directions have ≥2 papers with
          valid full-text facts whose topic terms overlap — disjoint preview
          clusters describing the same line must still be mergeable even with
          zero shared paper IDs.
        """
        merges = []
        plans = ctx.direction_plans
        for i, plan_a in enumerate(plans):
            for plan_b in plans[i + 1:]:
                ckey_a, ckey_b = plan_a["did"], plan_b["did"]
                dir_a, dir_b = plan_a["direction"], plan_b["direction"]
                keys_a = set(direction_candidate_keys(dir_a))
                keys_b = set(direction_candidate_keys(dir_b))
                shared = keys_a & keys_b
                toks_a = _profile_topic_tokens(dir_a)
                toks_b = _profile_topic_tokens(dir_b)
                profile_overlap = (
                    len(toks_a & toks_b) / min(len(toks_a), len(toks_b))
                    if toks_a and toks_b else 0.0)
                row = None
                if len(shared) >= MERGE_MIN_SHARED and profile_overlap >= MERGE_TOPIC_OVERLAP:
                    row = {
                        "direction_a": ckey_a,
                        "direction_b": ckey_b,
                        "name_a": dir_a.get("name_ja"),
                        "name_b": dir_b.get("name_ja"),
                        "merge_basis": "shared_papers",
                        "shared_papers": sorted(shared),
                        "overlap_ratio": round(profile_overlap, 2),
                        "reason": f"directions share {len(shared)} papers and {round(profile_overlap * 100)}% profile overlap",
                    }
                else:
                    basis = _merge_fulltext_basis(ctx, dir_a, dir_b)
                    if basis:
                        count_a = basis["facts_papers"]["source"]
                        count_b = basis["facts_papers"]["target"]
                        row = {
                            "direction_a": ckey_a,
                            "direction_b": ckey_b,
                            "name_a": dir_a.get("name_ja"),
                            "name_b": dir_b.get("name_ja"),
                            "merge_basis": "fulltext_convergence",
                            "shared_papers": sorted(shared),
                            "shared_topic_terms": basis["shared_topic_terms"],
                            "overlap_ratio": basis["overlap_ratio"],
                            "reason": (f"full-text topic terms converge on {len(basis['shared_topic_terms'])} shared terms "
                                       f"across {count_a}+{count_b} facts-backed papers"),
                        }
                if row:
                    merges.append(row)
        return merges

    def _canonical_directory(value) -> Path | None:
        """Canonical absolute path of a directory argument (None when unreadable)."""
        try:
            return Path(value).expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            return None

    def stage2_resolve_run_id(professor_dir: Path, facts: dict, results_dir: Path) -> str:
        """Identity of ONE resolve round: professor + preflight proof + results dir.

        Plan and finalize compute the same value from the same three inputs, so a
        result file from another round (a copied previous file, a fixed shared /tmp
        directory, another professor) can never pass the finalizer's check. The id
        only constrains temporary job outputs and is never part of the resolve
        reuse fingerprint or the accepted cache.
        """
        proof, _error = _facts_preflight_proof(facts)
        professor_canonical = _canonical_directory(professor_dir) or professor_dir
        results_canonical = _canonical_directory(results_dir) or results_dir
        return sha256_obj({
            "professor_dir": str(professor_canonical),
            "preflight_id": proof,
            "results_dir": str(results_canonical),
        })

    def cmd_stage2_resolve_plan(args) -> None:
        """Plan the direction resolution step: detect splits/merges/additions/removals.

        This is a deterministic pre-flight that uses full-text facts to suggest
        corrections to provisional directions. The actual resolution is performed
        by the model in the resolve job, which has access to the full context.

        One round = one exclusive results directory. `--results-dir` is required:
        every emitted job's `result_file` must be absent from it before the round
        starts (a leftover would be consumed as this round's model output), and the
        round identity `resolve_run_id` binds this plan's jobs to that directory.

        Reuse: an existing `_resolved_directions.json` entry whose per-direction
        `input_fingerprint` (the SHA of the direction's canonical resolve
        model_input) still matches is reused as-is and gets NO new resolve job —
        only directions whose job input changed (union paper metadata, effective
        facts state, any direction's profile, cross-direction candidate evidence,
        this direction's gap evidence) or that were never resolved/accepted are
        re-resolved. Editorial-only analysis Markdown edits do not affect the
        resolve model_input and keep accepted state reusable.
        """
        raw_results_dir = getattr(args, "results_dir", None)
        if not raw_results_dir or not Path(raw_results_dir).expanduser().is_absolute():
            fail("invalid_params",
                 f"stage2-resolve-plan requires an absolute --results-dir: {raw_results_dir!r}")
        results_dir = _canonical_directory(raw_results_dir)
        if results_dir is None or not results_dir.is_dir():
            fail("invalid_params",
                 f"--results-dir must be an existing directory: {raw_results_dir!r}")
        ctx = Stage2Context(Path(args.facts))
        # The resolution evidence universe is the professor-level candidate union:
        # reuse fingerprints must hash the same universe the resolve jobs score.
        evidence = _resolve_evidence(ctx)
        additions = evidence["additions"]
        removals = evidence["removals"]
        splits = evidence["splits"]
        merges = evidence["merges"]

        # Determine if any material change is detected
        has_material_changes = bool(additions or removals or splits or merges)

        existing = _load_existing_resolved(ctx.professor_dir, ctx.professor, None)
        existing_by_ckey: dict[str, dict] = {}
        if existing:
            for entry in existing.get("directions") or []:
                if isinstance(entry, dict) and isinstance(entry.get("provisional_direction_id"), str):
                    existing_by_ckey[entry["provisional_direction_id"]] = entry

        # Build per-direction resolution jobs
        resolve_jobs = []
        reuse_list = []
        fingerprints: dict[str, str] = {}
        for plan in ctx.direction_plans:
            ckey = plan["did"]
            prior = existing_by_ckey.get(ckey)
            current_fingerprint = _current_resolve_fingerprint(ctx, plan, evidence)
            fingerprints[ckey] = current_fingerprint
            # Only ACCEPTED resolved state is reusable. A material change is written
            # as "proposed" before the user picks (adopt / provisional / re-select);
            # re-resolving it until the choice is made keeps the promised re-prompt
            # alive instead of caching an unaccepted proposal as fact.
            if prior and prior.get("input_fingerprint") == current_fingerprint \
                    and prior.get("acceptance") == "accepted":
                reuse_list.append(ckey)
                continue  # resolved state is fresh and accepted; no new job
            resolve_jobs.append({
                "job_id": f"resolve:{ctx.professor}:{ckey}",
                "kind": "resolve",
                "direction_id": ckey,
                "result_file": f"resolve-{filename_component(ckey)}.json",
                "result_schema": {
                    "schema": 1,
                    "kind": "resolve",
                    "direction_id": ckey,
                    # Must be echoed verbatim from this plan: the finalizer only
                    # accepts files produced for ITS round directory/proof.
                    "resolve_run_id": "<this plan's resolve_run_id>",
                    "resolved": {
                        "resolved_direction_id": "<stable ID, same as direction_id unless split>",
                        "provisional_direction_id": ckey,
                        "name_ja": "<confirmed or renamed>",
                        "name_zh": "<confirmed or renamed>",
                        "resolution_type": "unchanged|renamed|split_from|merged_into|refined",
                        "papers_to_add": ["<item_key>; for split_from: papers moved INTO the new direction"],
                        "papers_to_remove": ["<item_key>; must be empty for split_from/merged_into>"],
                        "paper_justifications": {"<item_key>": "<1 sentence reason>"},
                        "split_target": "<split_from only: NEW direction ID, must not collide with any existing direction>",
                        "merge_target": "<merged_into only: existing target direction ID>",
                        "user_note": "<preserved from provisional>",
                    },
                },
                # Built by the same function the reuse fingerprint hashes, so the
                # cached state can never drift from what the job would receive.
                "model_input": _build_resolve_model_input(ctx, plan, evidence),
            })

        # One round owns its result files: every expected file must be absent
        # before the round starts, otherwise a leftover from another round could be
        # consumed as this round's model output. File names must also be unique.
        expected_files = [job["result_file"] for job in resolve_jobs]
        collisions = sorted({name for name in expected_files if expected_files.count(name) > 1})
        if collisions:
            fail("invalid_params",
                 f"resolve result file names collide inside this round: {collisions}")
        existing_files = sorted(name for name in set(expected_files)
                                if (results_dir / name).exists())
        if existing_files:
            fail("invalid_params",
                 "this resolve round's results directory already contains expected result "
                 "files; allocate a new round directory instead: "
                 f"{[str(results_dir / name) for name in existing_files]}",
                 results_dir=str(results_dir), existing_result_files=existing_files)

        resolve_run_id = stage2_resolve_run_id(ctx.professor_dir, ctx.facts, results_dir)
        for job in resolve_jobs:
            job["result_schema"]["resolve_run_id"] = resolve_run_id

        emit({
            "status": "ok",
            "professor": ctx.professor,
            "professor_dir": str(ctx.professor_dir),
            "results_dir": str(results_dir),
            "resolve_run_id": resolve_run_id,
            "has_material_changes": has_material_changes,
            # Traceability: the preflight proof this resolve round is bound to
            # (issue #11 binding, extended to the resolve pipeline in issue #7).
            "stage2_preflight_id": _facts_preflight_proof(ctx.facts)[0],
            "summary": {
                "directions": len(ctx.direction_plans),
                "reused_resolved": len(reuse_list),
                "addition_candidates": len(additions),
                "removal_candidates": len(removals),
                "split_candidates": len(splits),
                "merge_candidates": len(merges),
            },
            "directions": [{
                "direction_id": plan["did"],
                "action": "reuse" if plan["did"] in reuse_list else "process",
                "input_fingerprint": fingerprints[plan["did"]],
            } for plan in ctx.direction_plans],
            "candidates": {
                "additions": additions,
                "removals": removals,
                "splits": splits,
                "merges": merges,
            },
            "jobs": resolve_jobs,
            "write_needed": bool(resolve_jobs),
        })

    def _resolve_evidence(ctx: Stage2Context) -> dict:
        """Deterministic inputs shared by every per-direction resolve job.

        The evidence universe is the professor-level selected candidate union (a
        paper that entered the union through ANOTHER direction is still scored
        here), and affinity plus the four candidate detections are derived from
        it. Resolve reuse fingerprints hash these rendered per direction, so
        plan, finalize and the finalize-time staleness check can never disagree
        about what a resolve job would receive.
        """
        evidence_keys = selected_candidate_union(ctx)
        affinity = _compute_paper_direction_affinity(ctx)
        return {
            "evidence_keys": evidence_keys,
            "affinity": affinity,
            "additions": _detect_candidates_for_addition(ctx, affinity),
            "removals": _detect_candidates_for_removal(ctx, affinity),
            "splits": _detect_split_candidates(ctx),
            "merges": _detect_merge_candidates(ctx),
        }

    def _build_resolve_model_input(ctx: Stage2Context, plan: dict, evidence: dict) -> dict:
        """The exact deterministic model_input a resolve job for `plan` receives.

        Single source of truth shared by job emission and the reuse fingerprint:
        any state change that alters this dict invalidates the direction's cached
        resolution, and anything NOT in it (analysis Markdown prose, abstract
        preview fields) must not. The dict covers:
        - the direction's own profile, provenance and credibility;
        - union-wide paper evidence with the EFFECTIVE facts_state/facts_error/
          topic_terms from `facts_for` — the future-work sidecar join is part of
          the evidence chain, so a sidecar edit that breaks the join changes every
          direction that would see the paper;
        - per-paper affinity scores to ALL selected directions and the
          cross-direction removal/split/merge/addition candidate detections,
          which depend on other directions' profiles, membership and gaps;
        - this direction's own gap evidence (its pool's sidecar-rendered rows).
        """
        direction = plan["direction"]
        ckey = plan["did"]
        paper_evidence = []
        for key in evidence["evidence_keys"]:
            paper = ctx.papers.get(key)
            if not paper:
                continue
            facts_record, facts_state, facts_error = ctx.facts_for(key)
            paper_evidence.append({
                "item_key": key,
                "title": paper.get("title"),
                "year": paper.get("year"),
                "authorship": paper.get("authorship"),
                "is_provisional_member": key in (direction.get("provisional_member_keys") or []),
                "facts_state": facts_state,
                "facts_error": facts_error,
                "topic_terms": (facts_record or {}).get("topic_terms") if facts_record else [],
                "affinity_scores": evidence["affinity"].get(key, {}),
            })
        gap_evidence = []
        for gap in plan.get("pool") or []:
            gap_evidence.append({
                "gap_id": gap["gap_id"],
                "item_key": gap["item_key"],
                "paper_title": gap.get("paper_title"),
                "quote_trunc": truncate(gap.get("quote"), 120),
                "translation_zh": truncate(gap.get("translation_zh"), 80),
            })
        return {
            "collection_key": ckey,
            "provisional_direction": {
                "name_ja": direction.get("name_ja"),
                "name_zh": direction.get("name_zh"),
                "summary_zh": direction.get("summary_zh"),
                "user_note": direction.get("user_note") or "",
                "provisional_member_keys": direction.get("provisional_member_keys") or [],
                "credibility": direction.get("credibility") or {},
            },
            "paper_evidence": paper_evidence,
            "gap_evidence": gap_evidence,
            "removal_candidates": [r for r in evidence["removals"] if r["direction"] == ckey],
            "split_candidates": [s for s in evidence["splits"] if s["direction"] == ckey],
            "merge_candidates": [m for m in evidence["merges"]
                                 if m["direction_a"] == ckey or m["direction_b"] == ckey],
            "addition_candidates": [a for a in evidence["additions"]
                                    if a["target_direction"] == ckey],
            "rules": (
                "Resolve this provisional direction against full-text evidence.\n"
                "1. Each paper in paper_evidence has full-text facts (facts_state=valid) or not.\n"
                "2. Papers with valid full-text facts: judge membership by topic_terms overlap with direction profile.\n"
                "3. Papers without full-text facts: keep provisional membership (can't downgrade without evidence).\n"
                "4. A paper can support multiple directions (shared papers are allowed).\n"
                "5. Removal: only when full-text facts clearly show the paper doesn't belong.\n"
                "6. Addition: only when full-text facts clearly support this direction over the provisional one.\n"
                "7. Split: only when papers cluster into ≥2 distinct topic groups; set split_target to a NEW "
                "direction ID and put the papers that move INTO the new direction in papers_to_add "
                "(the source keeps the rest; papers_to_remove must be empty).\n"
                        "8. Merge: only when full-text evidence shows another direction is the same line of "
                        "work. The runner only accepts merges backed by converging topic terms across BOTH "
                        "directions' currently valid facts papers — shared candidate papers with similar "
                        "profiles (merge_basis=shared_papers) are a hint but never sufficient on their own. "
                        "Set merge_target to that direction ID (papers_to_add/papers_to_remove must be empty "
                        "— the whole direction folds into the target).\n"
                "9. Keyword/grep matches alone are NOT sufficient for final membership.\n"
                "10. If no material change, set resolution_type='unchanged' and empty add/remove lists."
            ),
        }

    def _current_resolve_fingerprint(ctx: Stage2Context, plan: dict, evidence: dict) -> str:
        """Per-direction fingerprint of the exact resolve model_input.

        Hashes the canonical job input the direction would receive right now, so
        reuse is stale-proof by construction: another direction's profile or
        facts-validity change, a broken future-work sidecar join, a metadata edit
        or a rules-text change all alter the hash, while editorial analysis
        Markdown edits (never part of the job input) keep accepted state
        reusable.
        """
        return sha256_obj({
            "version": RESOLVE_INPUT_FINGERPRINT_VERSION,
            "resolve_model_input": _build_resolve_model_input(ctx, plan, evidence),
        })

    return types.SimpleNamespace(
        _compute_paper_direction_affinity=_compute_paper_direction_affinity,
        _detect_candidates_for_addition=_detect_candidates_for_addition,
        _detect_candidates_for_removal=_detect_candidates_for_removal,
        _detect_split_candidates=_detect_split_candidates,
        _profile_topic_tokens=_profile_topic_tokens,
        _direction_fulltext_terms=_direction_fulltext_terms,
        _merge_fulltext_basis=_merge_fulltext_basis,
        _authoritative_merge_basis=_authoritative_merge_basis,
        _direction_has_valid_fulltext=_direction_has_valid_fulltext,
        _detect_merge_candidates=_detect_merge_candidates,
        _canonical_directory=_canonical_directory,
        stage2_resolve_run_id=stage2_resolve_run_id,
        cmd_stage2_resolve_plan=cmd_stage2_resolve_plan,
        _resolve_evidence=_resolve_evidence,
        _build_resolve_model_input=_build_resolve_model_input,
        _current_resolve_fingerprint=_current_resolve_fingerprint,
    )
