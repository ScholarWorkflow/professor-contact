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

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import re
import types





def build(*, atomic_json,
          fail,
          ANALYSIS_LEVELS,
          SCHEMA,
          MANAGED_BY,
          INPUT_PACK,
          FRESHNESS_CACHE,
          GAP_SCOPES,
          FRESHNESS_SCOPES,
          GAP_STATUSES,
          AUTHORSHIP_RANK,
          FACTS_SCHEMA,
          FACTS_KIND,
          FACTS_TEXT_FIELDS,
          FACTS_LIST_FIELDS,
          SHORTLIST_MAX,
          SHORTLIST_FLOOR,
          EXT_EVIDENCE_RE,
          PLACEHOLDER_RE,
          SIDECAR_EXTRACTOR_VERSIONS,
          FACTS_GENERATOR_VERSIONS,
          sha256_bytes,
          quote_id,
          read_json_file,
          text_tokens,
          title_tokens,
          direction_machine_id,
          facts_direction_id,
          pack_paper_index,
          load_input_pack,
          paper_digest,
          sidecar_sha,
          gap_fingerprint,
          candidate_fingerprint,
          direction_relevant_keys,
          pack_direction_relevant_keys,
          direction_fingerprint):
    def sidecar_analysis_matches(recorded: Any, expected_analysis: str) -> bool:
        """Bind a sidecar's `analysis` field to the analysis it belongs to.

        Canonical paper-analysis sidecars record the basename (`analysis.name` in
        both `future_work.py` and `facts.py`); legacy sidecars recorded the absolute
        analysis path. This binds only the recorded field: the physical sidecar
        location is bound separately by the sibling-path check in the loaders, which
        is what keeps same-basename analyses in different directories apart.
        """
        if not isinstance(recorded, str) or not recorded.strip():
            return False
        path = Path(recorded.strip())
        if path.is_absolute():
            try:
                return path.resolve() == Path(expected_analysis).resolve()
            except OSError:
                return False
        return len(path.parts) == 1 and path.name == Path(expected_analysis).name

    def sidecar_path_matches(path: Path, expected_analysis: str, suffix: str) -> bool:
        """Require the sidecar file to be the analysis's exact sibling on disk.

        `<analysis>.future_work.json` / `<analysis>.facts.json` are written next to
        their analysis by every paper-analysis writer. Accepting any other location
        would let a mis-assembled sidecar reference lend one analysis's evidence to
        another with the same basename.
        """
        expected_sibling = Path(str(expected_analysis) + suffix)
        try:
            return path.resolve() == expected_sibling.resolve()
        except OSError:
            return False

    def load_sidecar(path: str | None, expected_analysis: str | None = None) -> tuple[list, list, str | None]:
        """Return (anchorable_items, legacy_items, error).

        With `expected_analysis`, the sidecar must be that analysis's exact
        `<analysis>.future_work.json` sibling and its recorded `analysis` field must
        bind to the same analysis.
        """
        if not path:
            return [], [], None
        sidecar_path = Path(path)
        if not sidecar_path.is_file():
            return [], [], "missing"
        data, error = read_json_file(sidecar_path)
        if error:
            return [], [], "invalid"
        if not isinstance(data, dict) or data.get("schema") != 1 or data.get("status") != "ok":
            return [], [], "invalid"
        extractor_version = data.get("extractor_version")
        if extractor_version not in SIDECAR_EXTRACTOR_VERSIONS:
            return [], [], "invalid"
        if expected_analysis:
            if not sidecar_path_matches(sidecar_path, expected_analysis, ".future_work.json"):
                return [], [], "invalid"
            if not sidecar_analysis_matches(data.get("analysis"), expected_analysis):
                return [], [], "invalid"
        elif not isinstance(data.get("analysis"), str) or not data["analysis"].strip():
            return [], [], "invalid"
        items = data.get("items")
        if not isinstance(items, list):
            return [], [], "invalid"
        anchorable, legacy = [], []
        seen_ids = set()
        for item in items:
            if not isinstance(item, dict):
                return [], [], "invalid"
            gap_id = item.get("id")
            quote = item.get("quote")
            if not isinstance(gap_id, str) or not re.fullmatch(r"[0-9a-f]{64}", gap_id or ""):
                return [], [], "invalid"
            if gap_id in seen_ids:
                return [], [], "invalid"
            seen_ids.add(gap_id)
            if not isinstance(quote, str) or not quote.strip():
                return [], [], "invalid"
            if gap_id != quote_id(quote):
                return [], [], "invalid"
            if not isinstance(item.get("translation_zh"), str) or not item["translation_zh"].strip():
                return [], [], "invalid"
            if not isinstance(item.get("source"), str) or not item["source"].strip():
                return [], [], "invalid"
            record = {
                "gap_id": gap_id,
                "quote": quote,
                "translation_zh": item["translation_zh"].strip(),
                "source": item["source"].strip(),
                "page": item.get("page"),
            }
            if isinstance(item.get("page"), bool) or (item.get("page") is not None and
                                                       not isinstance(item.get("page"), int)):
                return [], [], "invalid"
            if isinstance(item.get("page"), int) and item["page"] >= 1:
                anchorable.append(record)
            else:
                legacy.append(record)
        return anchorable, legacy, None

    def load_facts_sidecar(
        facts_file: str | None,
        expected_analysis: str | None,
        pdf_file: str | None,
        valid_gap_ids: set | None,
    ) -> tuple[dict | None, str, str | None]:
        """Validate a paper-analysis `<analysis>.facts.json` sidecar for reuse.

        Returns (normalized_facts, facts_state, facts_error). The sidecar is only
        reusable when it is the analysis's exact `.facts.json` sibling, its
        schema/generator are known, it names the current analysis, its
        `input_fingerprint` matches the sha256 of the current source PDF, and its
        `future_work_ids` are exact joins into the current valid future-work sidecar
        (which stays the authoritative quoted evidence). Any mismatch fails closed:
        no normalized facts are exposed and the caller must not re-derive them with
        another model pass.
        """
        if not facts_file:
            return None, "unavailable", "missing_facts_sidecar"
        path = Path(facts_file)
        if not path.is_file():
            return None, "unavailable", "missing_facts_sidecar"
        data, error = read_json_file(path)
        if error or not isinstance(data, dict):
            return None, "failed", "invalid_facts_sidecar"
        if (data.get("schema") != FACTS_SCHEMA or data.get("kind") != FACTS_KIND
                or data.get("status") != "ok"
                or data.get("generator_version") not in FACTS_GENERATOR_VERSIONS
                or data.get("evidence_level") != "fulltext"):
            return None, "failed", "invalid_facts_sidecar"
        if expected_analysis and not sidecar_path_matches(path, expected_analysis, ".facts.json"):
            return None, "failed", "invalid_facts_sidecar"
        recorded_analysis = data.get("analysis")
        if not isinstance(recorded_analysis, str) or not recorded_analysis.strip():
            return None, "failed", "invalid_facts_sidecar"
        if expected_analysis and not sidecar_analysis_matches(recorded_analysis, expected_analysis):
            return None, "failed", "invalid_facts_sidecar"
        for field in FACTS_TEXT_FIELDS:
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                return None, "failed", "invalid_facts_sidecar"
        for field in FACTS_LIST_FIELDS:
            value = data.get(field)
            if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                return None, "failed", "invalid_facts_sidecar"
        anchors = data.get("source_anchors")
        if anchors is not None and not isinstance(anchors, dict):
            return None, "failed", "invalid_facts_sidecar"
        confidence = data.get("confidence")
        if confidence is not None and (not isinstance(confidence, (int, float))
                                       or isinstance(confidence, bool) or not 0 <= confidence <= 1):
            return None, "failed", "invalid_facts_sidecar"
        fingerprint = data.get("input_fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint.startswith("sha256:"):
            return None, "failed", "invalid_facts_sidecar"
        if not pdf_file or not Path(pdf_file).is_file():
            return None, "failed", "facts_source_fingerprint_mismatch"
        current = "sha256:" + sha256_bytes(Path(pdf_file).read_bytes())
        if fingerprint != current:
            return None, "failed", "facts_source_fingerprint_mismatch"
        joined_ids = data.get("future_work_ids")
        if (not isinstance(joined_ids, list)
                or any(not isinstance(gap_id, str) or not re.fullmatch(r"[0-9a-f]{64}", gap_id) for gap_id in joined_ids)
                or len(set(joined_ids)) != len(joined_ids)):
            return None, "failed", "invalid_facts_sidecar"
        if valid_gap_ids is None or not set(joined_ids).issubset(valid_gap_ids):
            return None, "failed", "facts_future_work_join_mismatch"
        normalized = {
            "facts_file": str(path),
            "evidence_level": "fulltext",
            "input_fingerprint": fingerprint,
            "research_problem": data["research_problem"].strip(),
            "research_object": data["research_object"].strip(),
            "approach": data["approach"].strip(),
            "findings": [item.strip() for item in data["findings"]],
            "contributions": [item.strip() for item in data["contributions"]],
            "topic_terms": [item.strip() for item in data["topic_terms"]],
            "limitations": [item.strip() for item in data["limitations"]],
            "source_anchors": anchors or {},
            "confidence": float(confidence) if confidence is not None else None,
            "future_work_ids": list(joined_ids),
        }
        return normalized, "valid", None

    def compute_version_families(papers: dict) -> dict:
        confirmed, possible = [], []
        keys = sorted(papers)
        for index, left in enumerate(keys):
            for right in keys[index + 1:]:
                early, late = papers[left], papers[right]
                ey, em = early.get("year") or 0, early.get("month") or 0
                ly, lm = late.get("year") or 0, late.get("month") or 0
                if not (ly, lm) > (ey, em):
                    continue
                early_tokens = title_tokens(early.get("title") or "")
                late_tokens = title_tokens(late.get("title") or "")
                denominator = min(len(early_tokens), len(late_tokens)) or 1
                overlap = len(early_tokens & late_tokens) / denominator
                early_authors = {a.lower() for a in (early.get("authors") or [])}
                late_authors = {a.lower() for a in (late.get("authors") or [])}
                author_overlap = None
                if early_authors and late_authors:
                    author_overlap = len(early_authors & late_authors) / min(len(early_authors), len(late_authors))
                explicit = bool(EXT_EVIDENCE_RE.search(late.get("abstract") or ""))
                base = {"family_id": f"vf:{left}+{right}", "members": [left, right],
                        "primary": right, "role": {left: "preliminary", right: "journal_ext"},
                        "title_overlap": round(overlap, 2)}
                if overlap >= 0.4 and explicit and (author_overlap is None or author_overlap >= 0.5):
                    base["evidence"] = "题名词重叠＋时间顺序＋后续摘要明示扩展"
                    confirmed.append(base)
                elif overlap >= 0.4:
                    base["evidence"] = "题名词重叠＋时间顺序（扩展证据不足）"
                    possible.append(base)
        return {"confirmed": confirmed, "possible": possible}

    def score_gap(gap: dict, current_year: int) -> int:
        score = 0
        if gap.get("named_by_user"):
            score += 30
        if gap.get("relevant"):
            score += 10
        score += AUTHORSHIP_RANK.get(gap.get("authorship"), 0)
        year = gap.get("paper_year") or 0
        if year:
            score += max(0, 10 - (current_year - year))
        if gap.get("quote") and gap.get("translation_zh") and gap.get("page"):
            score += 5
        if gap.get("family_primary_confirmed"):
            score += 5
        return score

    def rank_gaps(gaps: list, current_year: int) -> list:
        for gap in gaps:
            gap["_score"] = score_gap(gap, current_year)
        return sorted(gaps, key=lambda g: (-g["_score"], -(g.get("paper_year") or 0),
                                           g.get("item_key") or "", g.get("gap_id") or ""))

    def shortlist_size(pool_size: int) -> int:
        if pool_size >= SHORTLIST_FLOOR:
            return min(SHORTLIST_MAX, pool_size)
        return pool_size

    def is_later_or_same_unknown(paper: dict, source: dict) -> bool:
        py, pm = paper.get("year"), paper.get("month")
        sy, sm = source.get("year"), source.get("month")
        if not isinstance(py, int) or not isinstance(sy, int):
            return False
        if py > sy:
            return True
        if py < sy or paper.get("item_key") == source.get("item_key"):
            return False
        # A same-year paper is only later when both publication months are known.
        return isinstance(pm, int) and isinstance(sm, int) and pm > sm

    def gap_related(gap: dict, paper: dict) -> bool:
        gap_tokens = text_tokens(gap.get("quote") or "") | text_tokens(gap.get("translation_zh") or "")
        paper_tokens = text_tokens(paper.get("title") or "") | text_tokens((paper.get("abstract") or "")[:600])
        return len(gap_tokens & paper_tokens) >= 2

    def freshness_candidates(gap: dict, source_paper: dict, library: dict,
                             current_year: int, family_members: set, history_refs: set) -> dict:
        tiers = {"confirmed_family": [], "authorship": [], "recent": [], "topic": []}
        excluded_no_clue = 0
        later_total = 0
        for key in sorted(library):
            paper = library[key]
            if key == source_paper.get("item_key") or not is_later_or_same_unknown(paper, source_paper):
                continue
            later_total += 1
            if key in family_members:
                tier = "confirmed_family"
            elif paper.get("year") and current_year - paper["year"] <= 3 and \
                    paper.get("authorship") in ("corresponding", "solo", "first"):
                tier = "authorship"
            elif paper.get("year") and current_year - paper["year"] <= 3 and \
                    paper.get("authorship") in ("pending", "middle"):
                tier = "recent"
            elif key in history_refs or gap_related(gap, paper):
                tier = "topic"
            else:
                excluded_no_clue += 1
                continue
            tiers[tier].append(key)
        return {"tiers": tiers, "later_total": later_total, "excluded_no_clue": excluded_no_clue}

    def load_freshness_cache(professor_dir: Path) -> dict:
        data, error = read_json_file(professor_dir / FRESHNESS_CACHE)
        if error or not isinstance(data, dict):
            return {}
        entries = data.get("entries")
        # A malformed truthy `entries` container degrades to an empty view so the
        # freshness-view fingerprint mismatches the accepted one (fail closed to
        # `freshness_cache_changed`) instead of crashing on a non-dict .get().
        return entries if isinstance(entries, dict) else {}

    def save_freshness_cache(professor_dir: Path, entries: dict) -> None:
        atomic_json(professor_dir / FRESHNESS_CACHE, {
            "schema": SCHEMA, "managed_by": MANAGED_BY, "entries": entries})

    def gap_scope_keys(facts: dict, direction: dict) -> list:
        scope = (facts.get("params") or {}).get("gap_scope") or "selected_direction"
        if scope == "all":
            return sorted({p.get("item_key") for p in facts.get("papers", []) if p.get("item_key")})
        if scope == "relevant":
            return direction_relevant_keys(direction)
        return list(direction.get("member_keys") or [])

    def canonical_index_path(value: Any) -> str | None:
        """Absolute, comparable form of an index/paper path (never a guess)."""
        if not isinstance(value, str) or not value.strip():
            return None
        path = Path(value.strip())
        try:
            return str(path.expanduser().resolve())
        except OSError:
            return str(path.expanduser())

    def read_analysis_index(professor_dir: Path) -> tuple[dict | None, str]:
        """Read `<professor_dir>/论文分析/_index.json` and classify its state.

        Returns ``(papers, state)`` where state is ``"ok"`` (a papers map),
        ``"missing"`` (no index file: an explicit unknown registration state) or
        ``"malformed"`` (unreadable/broken record: business equality cannot be
        proven). The resolver never rewrites the index and never invents fields.
        """
        data, error = read_json_file(Path(professor_dir) / "论文分析" / "_index.json")
        if error == "not_found":
            return {}, "missing"
        if error or not isinstance(data, dict):
            return None, "malformed"
        papers = data.get("papers")
        if not isinstance(papers, dict):
            return None, "malformed"
        return papers, "ok"

    def index_entry_level(entry: dict) -> tuple[str | None, bool]:
        """(level, legal) for one index entry; missing/null means unconfirmed."""
        level = entry.get("level")
        if level is None:
            return None, True
        if isinstance(level, str) and level in ANALYSIS_LEVELS:
            return level, True
        return None, False

    def index_entry_analysis_path(entry: dict) -> str | None:
        """The analysis path a successful index registration selects, if usable."""
        if not isinstance(entry, dict):
            return None
        path = canonical_index_path(entry.get("file"))
        if path is None:
            return None
        try:
            exists = Path(path).is_file()
        except OSError:
            exists = False
        return path if exists else None

    def resolve_declared_level(entry: Any, analysis_file: Any,
                               declared: Any) -> tuple[str | None, str | None]:
        """Shared eligibility rule for the current paper's actual analysis level.

        A level is only known on the current professor, current item and the
        selected analysis source: the index must carry an object record, its
        `file` must be an existing analysis, and the facts' selected
        `analysis_file` must be the same canonical path. A declared known level
        that contradicts that registration is invalid input; no declared value
        is the honest unconfirmed state and is never revived from the index.
        """
        if declared is not None and declared not in ANALYSIS_LEVELS:
            return None, "invalid_analysis_level"
        if entry is None:
            # No success-only registration: no known level can be confirmed.
            return (None, "analysis_level_conflict") if declared is not None else (None, None)
        if not isinstance(entry, dict):
            return None, "invalid_analysis_index_record"
        recorded, legal = index_entry_level(entry)
        if not legal:
            return None, "invalid_analysis_index_level"
        current_path = index_entry_analysis_path(entry)
        selected = canonical_index_path(analysis_file)
        eligible = bool(current_path) and selected is not None and current_path == selected
        if declared is None:
            # A missing/None facts declaration is honest only while the current
            # analysis is unconfirmed. If the same eligible registration is
            # already known, accepting null would create the split authority r4
            # removes: the next preflight would revive the index value.
            if eligible and recorded is not None:
                return None, "analysis_level_conflict"
            return None, None
        if not eligible or recorded != declared:
            return None, "analysis_level_conflict"
        return declared, None

    def _path_state(value: Any) -> dict:
        path = canonical_index_path(value)
        if path is None:
            return {"path": None, "state": "undeclared"}
        try:
            exists = Path(path).is_file()
        except OSError:
            exists = False
        return {"path": path, "state": "present" if exists else "missing"}

    def _fixed_candidate_state(analysis_path: str | None, suffix: str) -> str:
        if not analysis_path:
            return "unknown"
        try:
            return "present" if Path(analysis_path + suffix).is_file() else "missing"
        except OSError:
            return "missing"

    def observed_source_projection(professor_dir: Path, keys) -> dict:
        """Limited business-source view over the accepted package's own papers.

        Only the current analysis index record shape, its declared analysis /
        future-work / facts sources and the fixed `.facts.json` /
        `.future_work.json` candidates (derived from the current valid analysis
        path) are recorded. Administrative fields (generated_at, KB ids, level)
        never enter this business identity; a missing index is an explicit
        unknown state while an unreadable one cannot prove business equality.
        """
        index_papers, state = read_analysis_index(professor_dir)
        if state == "malformed":
            return {"index": "malformed"}
        papers = {}
        for key in sorted({key for key in keys if isinstance(key, str)}):
            entry = index_papers.get(key)
            if entry is None:
                record = {"index": "missing",
                          "analysis": {"path": None, "state": "undeclared"},
                          "future_work": {"path": None, "state": "undeclared"},
                          "facts": {"path": None, "state": "undeclared"},
                          "fixed": {"future_work": "unknown", "facts": "unknown"}}
            elif not isinstance(entry, dict):
                record = {"index": "malformed"}
            else:
                analysis_path = index_entry_analysis_path(entry)
                record = {
                    "index": "object",
                    "analysis": _path_state(entry.get("file")),
                    "future_work": _path_state(entry.get("future_work_sidecar")),
                    "facts": _path_state(entry.get("facts_sidecar")),
                    "fixed": {
                        "future_work": _fixed_candidate_state(analysis_path, ".future_work.json"),
                        "facts": _fixed_candidate_state(analysis_path, ".facts.json"),
                    },
                }
            papers[key] = record
        return {"index": state, "papers": papers}

    def observed_level_projection(professor_dir: Path, keys) -> dict:
        """Current observable level per consumed paper (index-only, no facts).

        The value is a known level only when the index record selects an existing
        analysis file; otherwise it is null (unconfirmed). An illegal enum/type is
        reported as invalid so preflight can take the slow path instead of
        writing a known value. The level stays OUT of the business projection.
        """
        index_papers, state = read_analysis_index(professor_dir)
        if state == "malformed":
            return {"index": state, "valid": False, "values": {}}
        values, valid = {}, True
        for key in sorted({key for key in keys if isinstance(key, str)}):
            entry = index_papers.get(key)
            if entry is None:
                values[key] = None
                continue
            if not isinstance(entry, dict):
                values[key] = None
                valid = False
                continue
            level, legal = index_entry_level(entry)
            if not legal:
                values[key] = None
                valid = False
                continue
            values[key] = level if index_entry_analysis_path(entry) else None
        return {"index": state, "valid": valid, "values": values}

    def consumed_sources(facts_papers: dict, keys) -> dict:
        """Record the source declarations this run actually consumed (audit only).

        Preflight only sees candidates; this records what the accepted facts named
        for each consumed paper so a later run can tell an observed candidate from
        the actual accepted source. It never participates in change equality.
        """
        out = {}
        for key in sorted({key for key in keys if isinstance(key, str)}):
            paper = facts_papers.get(key)
            if not isinstance(paper, dict):
                continue
            out[key] = {
                "analysis_file": canonical_index_path(paper.get("analysis_file")),
                "sidecar_file": canonical_index_path(paper.get("sidecar_file")),
                "facts_file": canonical_index_path(paper.get("facts_file")),
                "pdf_file": canonical_index_path(paper.get("pdf_file")),
            }
        return out

    def load_papers_with_digests(facts: dict, professor_dir: Path) -> dict:
        index_papers, index_state = read_analysis_index(professor_dir)
        papers = {}
        for paper in facts.get("papers", []):
            key = paper.get("item_key")
            if not key:
                continue
            record = dict(paper)
            declared = record.get("analysis_level")
            if declared is not None and declared not in ANALYSIS_LEVELS:
                fail("invalid_facts",
                     f"paper {key}: analysis_level must be one of {ANALYSIS_LEVELS} or null",
                     item_key=key)
            if index_state == "malformed":
                # A broken registration record cannot prove the declared value.
                if declared is not None:
                    fail("invalid_facts",
                         f"paper {key}: 论文分析/_index.json is unreadable; "
                         "analysis_level cannot be verified", item_key=key)
                level = None
            else:
                entry = index_papers.get(key)
                level, error = resolve_declared_level(
                    entry, record.get("analysis_file"), declared)
                if error:
                    fail("invalid_facts", f"paper {key}: {error}", item_key=key)
                # Acceptance check of the actual consumed sources against the
                # current registration. A contradiction between two DECLARED
                # paths (facts consumed vs index observation) is input error; a
                # source only one side declares stays legal, so an old
                # unregistered analysis is still honestly consumed as unknown.
                if isinstance(entry, dict):
                    for facts_field, index_field in (
                            ("analysis_file", "file"),
                            ("sidecar_file", "future_work_sidecar"),
                            ("facts_file", "facts_sidecar")):
                        consumed = canonical_index_path(record.get(facts_field))
                        registered = canonical_index_path(entry.get(index_field))
                        if consumed is not None and registered is not None \
                                and consumed != registered:
                            fail("invalid_facts",
                                 f"paper {key}: {facts_field} {consumed!r} contradicts the "
                                 f"current analysis index {index_field} {registered!r}",
                                 item_key=key)
            record["analysis_level"] = level
            record["_digest"] = paper_digest(record)
            papers[key] = record
        return papers

    def build_gap_pool(facts: dict, papers: dict, families: dict,
                       sidecar_cache: dict) -> tuple[dict, dict]:
        """Build per-direction anchorable gap pools from valid sidecars."""
        confirmed_members = {}
        for family in families.get("confirmed", []):
            for member in family["members"]:
                confirmed_members.setdefault(member, set()).update(family["members"])
        pools = {}
        for direction in facts.get("directions", []):
            scope = gap_scope_keys(facts, direction)
            gaps = []
            for key in sorted(scope):
                paper = papers.get(key)
                if not paper:
                    continue
                sidecar_file = paper.get("sidecar_file")
                if not sidecar_file:
                    continue
                if sidecar_file not in sidecar_cache:
                    sha = sidecar_sha(sidecar_file)
                    items, legacy_items, error = load_sidecar(sidecar_file, paper.get("analysis_file"))
                    sidecar_cache[sidecar_file] = (items, legacy_items, error, sha)
                items, legacy_items, error, sha = sidecar_cache[sidecar_file]
                if error:
                    continue
                for item in items:
                    gaps.append({
                        "gap_id": item["gap_id"], "item_key": key,
                        "paper_title": paper.get("title"), "paper_year": paper.get("year"),
                        "authorship": paper.get("authorship"),
                        "quote": item["quote"], "translation_zh": item["translation_zh"],
                        "source": item["source"], "page": item["page"],
                        "named_by_user": key in (direction.get("named_keys") or []),
                        "relevant": True,
                        "family_primary_confirmed": any(
                            f["primary"] == key for f in families.get("confirmed", [])),
                        "sidecar_sha": sha})
            duplicate_ids = {}
            for gap in gaps:
                duplicate_ids.setdefault(gap["gap_id"], []).append(gap)
            suppressed = set()
            for gap_id, group in duplicate_ids.items():
                if len(group) > 1:
                    group_sorted = sorted(group, key=lambda g: (0 if g["family_primary_confirmed"] else 1,
                                                                g["item_key"]))
                    for loser in group_sorted[1:]:
                        loser["suppressed_by"] = group_sorted[0]["item_key"]
                        suppressed.add(id(loser))
            pools[facts_direction_id(direction)] = [g for g in gaps if id(g) not in suppressed]
        return pools, confirmed_members

    class Stage2Context:
        """Everything plan and finalize need, computed once from the facts file."""

        def __init__(self, facts_path: Path):
            self.facts_path = facts_path
            data, error = read_json_file(facts_path)
            if error:
                fail("invalid_facts", f"facts file unreadable: {error}")
            self.facts = data
            self.professor = self.facts.get("professor") or fail("invalid_facts", "facts.professor missing")
            self.professor_dir = Path(self.facts.get("professor_dir") or fail("invalid_facts", "facts.professor_dir missing"))
            self.program_root = Path(self.facts.get("program_root") or (self.professor_dir.parent.parent))
            self.current_year = int(self.facts.get("current_year") or datetime.now().year)
            params = self.facts.get("params") or {}
            self.gap_scope = params.get("gap_scope") or "selected_direction"
            self.freshness_scope = params.get("freshness_scope") or "shortlist"
            if self.gap_scope not in GAP_SCOPES:
                fail("invalid_params", f"gap_scope must be one of {GAP_SCOPES}")
            if self.freshness_scope not in FRESHNESS_SCOPES:
                fail("invalid_params", f"freshness_scope must be one of {FRESHNESS_SCOPES}")
            self.papers = load_papers_with_digests(self.facts, self.professor_dir)
            self.sidecar_cache = {}
            self.facts_cache = {}
            self.families = compute_version_families(self.papers)
            self.pools, self.family_members = build_gap_pool(self.facts, self.papers, self.families, self.sidecar_cache)
            self.pack_path = self.professor_dir / INPUT_PACK
            self.pack, _ = load_input_pack(self.professor_dir)
            self.cache = load_freshness_cache(self.professor_dir)
            self.direction_plans = []
            self._prepare_directions()

        def _prepare_directions(self) -> None:
            old_directions = {}
            if self.pack:
                for entry in self.pack.get("directions", []):
                    old_directions[direction_machine_id(entry)] = entry
            for direction in self.facts.get("directions", []):
                # `did` is the machine identity routed through every Stage-2 map;
                # `legacy_collection_key` is projection metadata only (issue #8).
                did = facts_direction_id(direction)
                pool = self.pools.get(did, [])
                ranked = rank_gaps([dict(g) for g in pool], self.current_year)
                fingerprint = direction_fingerprint(
                    direction, self.papers, [g["gap_id"] for g in pool], self.families)
                old = old_directions.get(did)
                old_narrative = (old or {}).get("narrative") or {}
                old_blocks = [b for b in old_narrative.get("positioning", []) if isinstance(b, dict)]
                narrative_has_examples = bool(old_blocks) and all(
                    all(isinstance(b.get(field), str) and b[field].strip()
                        for field in ("concrete_object", "input_example", "output_example"))
                    for b in old_blocks)
                # Stage-2 internal freshness is judged against the PROVISIONAL
                # fingerprint. Once a resolution has been applied, the pack keeps it
                # in `provisional_input_fingerprint` because the public
                # `input_fingerprint` is recomputed to the resolved-aware downstream
                # value that Stage 3's reuse gate consumes.
                old_provisional_fp = (old or {}).get("provisional_input_fingerprint",
                                                     (old or {}).get("input_fingerprint"))
                reuse = bool(old and old_provisional_fp == fingerprint and narrative_has_examples)
                plan_entry = {
                    "direction": direction, "did": did, "pool": pool, "ranked": ranked,
                    "fingerprint": fingerprint, "old": old, "reuse": reuse,
                }
                if reuse and self.freshness_stale(plan_entry):
                    plan_entry["reuse"] = False
                self.direction_plans.append(plan_entry)

        def freshness_stale(self, plan: dict) -> bool:
            for gap in self.judge_set(plan):
                item, _hit = self.freshness_entry(plan, gap)
                if not item.get("cached"):
                    return True
            return False

        def facts_for(self, key: str) -> tuple[dict | None, str, str | None]:
            """Validated normalized paper facts for one paper (memoized).

            Reuse requires the current valid future-work sidecar: its item ids stay
            the authoritative quoted evidence and `facts.future_work_ids` may only
            exact-join into them. A paper without a facts sidecar is honestly
            "unavailable"; a facts sidecar whose evidence chain (valid sidecar,
            fingerprint, joins) is broken fails closed.
            """
            paper = self.papers.get(key)
            if not paper:
                return None, "unavailable", "missing_facts_sidecar"
            cached = self.facts_cache.get(key)
            if cached is not None:
                return cached
            if not paper.get("facts_file"):
                record = (None, "unavailable", "missing_facts_sidecar")
            else:
                sidecar_file = paper.get("sidecar_file")
                valid_ids: set | None = None
                if sidecar_file:
                    if sidecar_file not in self.sidecar_cache:
                        sha = sidecar_sha(sidecar_file)
                        items, legacy_items, error = load_sidecar(sidecar_file, paper.get("analysis_file"))
                        self.sidecar_cache[sidecar_file] = (items, legacy_items, error, sha)
                    items, legacy_items, error, _sha = self.sidecar_cache[sidecar_file]
                    if not error:
                        valid_ids = {item["gap_id"] for item in items} | {item["gap_id"] for item in legacy_items}
                if valid_ids is None:
                    record = (None, "failed", "facts_future_work_join_mismatch")
                else:
                    record = load_facts_sidecar(
                        paper.get("facts_file"), paper.get("analysis_file"),
                        paper.get("pdf_file"), valid_ids)
            self.facts_cache[key] = record
            return record

        def freshness_entry(self, plan: dict, gap: dict):
            source = self.papers.get(gap["item_key"], {})
            cands = freshness_candidates(
                gap, source, self.papers, self.current_year,
                self.family_members.get(gap["item_key"], set()),
                self.history_refs(gap))
            gap_fp = gap_fingerprint(gap, gap.get("sidecar_sha"))
            cand_list = [
                {"item_key": key, "digest": self.papers[key]["_digest"]}
                for key in
                cands["tiers"]["confirmed_family"] + cands["tiers"]["authorship"] +
                cands["tiers"]["recent"] + cands["tiers"]["topic"]]
            cand_fp = candidate_fingerprint(cand_list)
            entry = self.cache.get(gap["gap_id"])
            if entry and entry.get("gap_fingerprint") == gap_fp and \
                    entry.get("candidate_fingerprint") == cand_fp and \
                    entry.get("status") in GAP_STATUSES:
                status = dict(entry)
                status["cache_hit"] = True
                return {"gap": gap, "status": status, "cands": cands,
                        "gap_fp": gap_fp, "cand_fp": cand_fp, "cached": True}, 1
            return {"gap": gap, "status": None, "cands": cands,
                    "gap_fp": gap_fp, "cand_fp": cand_fp, "cached": False}, 0

        def judge_set(self, plan: dict) -> list:
            ranked = plan["ranked"]
            if self.freshness_scope == "shortlist":
                return ranked[:shortlist_size(len(ranked))]
            return list(ranked)

        def freshness_job_items(self, plan: dict) -> tuple[list, list, int]:
            """Return (job gap items, cache-hit statuses, hit count)."""
            jobs, hits = [], 0
            for gap in self.judge_set(plan):
                item, hit = self.freshness_entry(plan, gap)
                hits += hit
                jobs.append(item)
            return jobs, hits

        def history_refs(self, gap: dict) -> set:
            entry = self.cache.get(gap.get("gap_id")) or {}
            return set(entry.get("candidate_paper_ids") or [])

        def narrative_later_keys(self, plan: dict) -> list[str]:
            keys = set()
            for gap in plan["ranked"]:
                source = self.papers.get(gap["item_key"], {})
                candidates = freshness_candidates(
                    gap, source, self.papers, self.current_year,
                    self.family_members.get(gap["item_key"], set()),
                    self.history_refs(gap))
                for tier in candidates["tiers"].values():
                    keys.update(tier)
            return sorted(keys)

        def narrative_needed(self, plan: dict) -> bool:
            return not plan["reuse"]

    class Stage2PackRefineContext:
        """Read-only context for repairing an accepted pack when /tmp facts expired.

        Everything the refine entry needs is recovered from the accepted input
        pack itself: the professor-level canonical `papers` map supplies trusted
        titles/year/authorship/analysis paths, while each direction's persisted
        `relevant_keys` restores its `P` citation licence (an explicit empty list
        stays empty; only a legacy direction without the field falls back to its
        members). `supporting_item_keys` remains the separate formal membership.
        """

        def __init__(self, professor_dir: Path):
            self.professor_dir = professor_dir
            self.pack_path = professor_dir / INPUT_PACK
            self.pack, error = load_input_pack(self.pack_path.parent)
            if error or self.pack is None:
                fail("missing_input_pack", f"input pack unreadable: {self.pack_path}")
            self.professor = self.pack.get("professor") or fail("invalid_facts", "input pack.professor missing")
            self.current_year = datetime.now().year
            self.papers = {}
            for key, record in pack_paper_index(self.pack).items():
                if isinstance(key, str) and isinstance(record, dict):
                    self.papers[key] = dict(record)
            self.direction_plans = []
            for direction in self.pack.get("directions", []):
                did = direction_machine_id(direction)
                for gap in direction.get("gap_shortlist", []) + direction.get("gaps_excluded", []):
                    key = gap.get("item_key")
                    if key:
                        self.papers.setdefault(key, {
                            "item_key": key, "title": gap.get("paper_title"),
                            "year": gap.get("paper_year"), "authorship": gap.get("authorship")})
                saved_later_papers = direction.get("narrative_later_papers")
                if isinstance(saved_later_papers, dict):
                    for key, paper in saved_later_papers.items():
                        if isinstance(key, str) and isinstance(paper, dict):
                            existing = self.papers.get(key)
                            restored = dict(paper)
                            if isinstance(existing, dict):
                                for field, value in existing.items():
                                    if value is not None:
                                        restored[field] = value
                            self.papers[key] = restored
                gaps = [dict(gap) for gap in direction.get("gap_shortlist", [])]
                gaps.extend(dict(gap) for gap in direction.get("gaps_excluded", []))
                supporting_keys = list(direction.get("supporting_item_keys") or [])
                relevant_keys = pack_direction_relevant_keys(direction)
                self.direction_plans.append({
                    "did": did,
                    "direction": {"relevant_keys": relevant_keys,
                                   "member_keys": supporting_keys,
                                   "named_keys": list(direction.get("named_keys") or [])},
                    "ranked": [gap for gap in gaps if gap.get("gap_id")],
                })

        @staticmethod
        def narrative_later_keys_for(direction: dict) -> list[str]:
            keys = set()
            narrative = direction.get("narrative") or {}
            for block in narrative.get("positioning", []):
                for kind, value in PLACEHOLDER_RE.findall(block.get("text") or ""):
                    if kind == "L":
                        keys.add(value)

        @staticmethod
        def narrative_later_keys_for(direction: dict) -> list[str]:
            keys = set()
            narrative = direction.get("narrative") or {}
            for block in narrative.get("positioning", []):
                for kind, value in PLACEHOLDER_RE.findall(block.get("text") or ""):
                    if kind == "L":
                        keys.add(value)
            return sorted(keys)

        def narrative_later_keys(self, plan: dict) -> list[str]:
            direction = next((d for d in self.pack.get("directions", [])
                              if direction_machine_id(d) == plan["did"]), {})
            return self.narrative_later_keys_for(direction)

    return types.SimpleNamespace(
                sidecar_analysis_matches=sidecar_analysis_matches,
                sidecar_path_matches=sidecar_path_matches,
                load_sidecar=load_sidecar,
                load_facts_sidecar=load_facts_sidecar,
                compute_version_families=compute_version_families,
                score_gap=score_gap,
                rank_gaps=rank_gaps,
                shortlist_size=shortlist_size,
                is_later_or_same_unknown=is_later_or_same_unknown,
                gap_related=gap_related,
                freshness_candidates=freshness_candidates,
                load_freshness_cache=load_freshness_cache,
                save_freshness_cache=save_freshness_cache,
                gap_scope_keys=gap_scope_keys,
                canonical_index_path=canonical_index_path,
                read_analysis_index=read_analysis_index,
                index_entry_level=index_entry_level,
                index_entry_analysis_path=index_entry_analysis_path,
                resolve_declared_level=resolve_declared_level,
                observed_source_projection=observed_source_projection,
                observed_level_projection=observed_level_projection,
                consumed_sources=consumed_sources,
                load_papers_with_digests=load_papers_with_digests,
                build_gap_pool=build_gap_pool,
                Stage2Context=Stage2Context,
                Stage2PackRefineContext=Stage2PackRefineContext,
    )
