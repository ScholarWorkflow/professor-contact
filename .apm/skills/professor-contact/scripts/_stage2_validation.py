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
from pathlib import Path
import types


def build(*, Stage2Context,
          Stage2PackRefineContext,
          atomic_json,
          emit,
          fail,
          soft_exit,
          _stage3_normalized_absolute_path,
          now_utc,
          sha256_bytes,
          sha256_obj,
          read_json_file,
          truncate,
          filename_component,
          direction_machine_id,
          pack_paper_index,
          load_input_pack,
          pack_direction_relevant_keys,
          managed_snapshot,
          split_frontmatter,
          split_frontmatter_bytes,
          managed_conflict,
          managed_write,
          _canonical_directory,
          stage2_pack_state_fingerprint,
          stage2_pack_content_fingerprint,
          validate_narrative_entry,
          render_analysis_document,
          stage2_require_paper_reference_titles,
          stage2_trusted_paper_title,
          stage2_require_later_paper_titles,
          MANAGED_BY,
          INPUT_PACK,
          ANALYSIS_MD,
          QUOTE_INPUT_CHARS,
          TRANSLATION_INPUT_CHARS,
          PLACEHOLDER_RE):
    def stage2_pack_scope(ctx, did: str) -> dict:
        """Reference/gap scope of one FINAL pack direction.

        The refinement entry validates against the accepted pack direction, so a
        split child or merge target uses its own persisted `relevant_keys` and
        migrated gaps instead of the provisional facts direction's scope.
        """
        for direction in (ctx.pack or {}).get("directions", []) or []:
            if direction_machine_id(direction) != did:
                continue
            gaps = list(direction.get("gap_shortlist") or []) + list(direction.get("gaps_excluded") or [])
            return {
                "papers": {key for key in pack_direction_relevant_keys(direction)
                           if isinstance(key, str) and key},
                "later": set(Stage2PackRefineContext.narrative_later_keys_for(direction)),
                "gaps": {gap.get("gap_id") for gap in gaps
                         if isinstance(gap, dict) and isinstance(gap.get("gap_id"), str)},
            }
        return {"papers": set(), "later": set(), "gaps": set()}

    def stage2_bound_snapshot(professor_dir: Path, pack: dict) -> dict:
        """Return the lossless managed snapshot only when pack and file agree.

        Stage-2 U1 r5 §3.6: the validator/report/refine chain proves the actual
        bytes on disk.  A universal-newline text read would hide an LF -> CRLF
        edit and let a stale report bind to a changed file.
        """
        cache = pack.get("cache") if isinstance(pack, dict) else None
        render = cache.get("render") if isinstance(cache, dict) else None
        entry = render.get(ANALYSIS_MD) if isinstance(render, dict) else None
        recorded = entry.get("sha256") if isinstance(entry, dict) else None
        path = professor_dir / ANALYSIS_MD
        if path.is_symlink():
            fail("validation_render_stale", f"{path}: managed analysis must not be a symlink")
        try:
            data = path.read_bytes()
        except OSError as exc:
            fail("validation_render_missing", f"{path}: {exc}")
        header, body_bytes = split_frontmatter_bytes(data)
        try:
            body = body_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            fail("validation_render_missing", f"{path}: {exc}")
        body_start = data.find(body_bytes)
        if body_start < 0:
            fail("validation_render_stale",
                 f"{path}: managed analysis body could not be located in its file")
        current = sha256_bytes(body_bytes)
        snapshot = {"header": header, "body": body, "body_bytes": body_bytes,
                    "body_sha256": current, "line_offset": data[:body_start].count(b"\n"),
                    "raw": data}
        expected_title = f"# 套磁候选分析 — {pack.get('professor')}"
        if not isinstance(header, dict) or header.get("managed_by") != MANAGED_BY \
                or header.get("render_sha256") != current or current != recorded \
                or header.get("state_fingerprint") != stage2_pack_state_fingerprint(pack) \
                or not body.splitlines() or body.splitlines()[0] != expected_title:
            fail("validation_render_stale",
                 f"{path}: validator evidence must bind the current managed analysis render")
        return snapshot

    def stage2_bound_render(professor_dir: Path, pack: dict) -> tuple[str, str]:
        """Return the managed analysis body only when pack and file prove the same render."""
        snapshot = stage2_bound_snapshot(professor_dir, pack)
        return snapshot["body_sha256"], snapshot["body"]

    def stage2_merge_later_paper_source(target: dict, source: dict | None,
                                       item_key: str) -> None:
        if not isinstance(source, dict):
            return
        for field, value in source.items():
            if value is None:
                continue
            if field == "title":
                title = stage2_trusted_paper_title(source, item_key)
                if title is not None:
                    target[field] = title
            else:
                target[field] = value

    def stage2_rendered_later_papers(body: str, professor_dir: Path,
                                     direction: dict, pack: dict | None = None) -> dict:
        """Recover later-paper metadata without treating link labels as title facts."""
        narrative = direction.get("narrative")
        if not isinstance(narrative, dict):
            narrative = {}
        positioning = narrative.get("positioning")
        if not isinstance(positioning, list):
            positioning = []
        later_keys = {
            key for block in positioning
            if isinstance(block, dict)
            for kind, key in PLACEHOLDER_RE.findall(block.get("text") or "")
            if kind == "L"
        }
        rendered = {key: {"item_key": key} for key in later_keys}
        citation_re = re.compile(
            r"\[([^\]\n]*)\]\(zotero://select/library/items/([^)]+)\)"
            r"(?:｜\[分析\]\(([^)\n]+)\))?(?:（([^）]*)）)?")
        for match in citation_re.finditer(body):
            _label, key, analysis_path, year = match.groups()
            if key not in later_keys:
                continue
            paper = rendered[key]
            if analysis_path and not paper.get("analysis_file"):
                paper["analysis_file"] = professor_dir / analysis_path
            if year and not paper.get("year"):
                paper["year"] = year

        canonical_papers = pack_paper_index(pack or {})
        saved = direction.get("narrative_later_papers")
        for key in later_keys:
            paper = rendered[key]
            stage2_merge_later_paper_source(paper, canonical_papers.get(key), key)
            stage2_merge_later_paper_source(
                paper, saved.get(key) if isinstance(saved, dict) else None, key)
        return rendered

    def stage2_restore_pack_later_papers(
            ctx: Stage2Context | Stage2PackRefineContext) -> None:
        """Restore old-pack L citation data before pure-pack renders or repair plans."""
        _, body = stage2_bound_render(ctx.professor_dir, ctx.pack)
        for direction in ctx.pack.get("directions", []):
            for key, paper in stage2_rendered_later_papers(
                    body, ctx.professor_dir, direction, ctx.pack).items():
                existing = ctx.papers.get(key)
                restored = dict(paper)
                if isinstance(existing, dict):
                    stage2_merge_later_paper_source(restored, existing, key)
                ctx.papers[key] = restored

    def stage2_parse_report_location(location) -> tuple[int | None, str | None]:
        """Physical line addressed by a Stage-2 report `location`, if unambiguous.

        Supported Stage-2 notations: a positive integer, a pure ASCII decimal
        string, and the exact form `第N行`. A vague multi-position notation
        (`第57行及多处`, `多处`, …) must never be silently expanded to one of the
        matched lines; the caller rejects it with an actionable error. Any other
        short text stays a legacy short location and is only usable when the quote
        itself hits exactly one rendered line.
        """
        if isinstance(location, bool):
            return None, None
        if isinstance(location, int):
            return (location if location > 0 else None), None
        if not isinstance(location, str):
            return None, None
        text = location.strip()
        if text.isascii() and text.isdigit():
            number = int(text)
            return (number if number > 0 else None), None
        matches = re.fullmatch(r"第\s*([0-9]+)\s*行", text)
        if matches:
            number = int(matches.group(1))
            return (number if number > 0 else None), None
        if re.fullmatch(r"第\s*[0-9]+\s*行\s*(及|等|和|、|,|，)?\s*多\s*处", text) \
                or text in ("多处", "多个位置", "多处位置", "多处及多处"):
            return None, "validation_location_ambiguous"
        return None, None

    def stage2_render_ownership(pack: dict, render_sha: str, line_count: int) -> dict:
        """The generated ownership map that must describe this exact managed body."""
        cache = pack.get("cache") if isinstance(pack, dict) else None
        render = cache.get("render") if isinstance(cache, dict) else None
        entry = render.get(ANALYSIS_MD) if isinstance(render, dict) else None
        ownership = entry.get("ownership") if isinstance(entry, dict) else None
        if not isinstance(ownership, dict):
            fail("validation_ownership_missing",
                 "the accepted input pack has no fixed-evidence ownership map for the managed "
                 "analysis; run the normal Stage 2 preflight -> process -> finalize update first "
                 "(old packs must not be reverse-engineered from Markdown)",
                 target=str(ANALYSIS_MD))
        if ownership.get("version") != 1 \
                or ownership.get("body_sha256") != render_sha \
                or ownership.get("line_count") != line_count:
            fail("validation_render_stale",
                 "the managed analysis ownership map does not describe the current body; "
                 "re-run the normal Stage 2 finalize before validating",
                 target=str(ANALYSIS_MD))
        if not isinstance(ownership.get("fragments"), list):
            fail("validation_render_stale",
                 "the managed analysis ownership map has no fragment list",
                 target=str(ANALYSIS_MD))
        return ownership

    def stage2_fragment_overlaps(fragment: dict, line: int, start: int, end: int) -> bool:
        for span in fragment.get("ranges") or []:
            if not isinstance(span, list) or len(span) != 3:
                continue
            span_line, span_start, span_end = span
            if span_line != line:
                continue
            if start < span_end and end > span_start:
                return True
        return False

    def stage2_validation_report(path: Path, professor_dir: Path, pack: dict, *,
                                require_repairable: bool = True) -> dict:
        """Read and validate the raw style-validator report for this managed analysis."""
        try:
            raw = path.read_bytes()
        except (OSError, ValueError) as exc:
            fail("invalid_validation_json", f"style-validator output unreadable: {path}: {exc}")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            fail("invalid_validation_json", f"style-validator output is not valid UTF-8 JSON: {path}")
        if not isinstance(data, dict) or data.get("result") != "ok" \
                or not isinstance(data.get("files"), list) or not data["files"] \
                or not isinstance(data.get("notes"), str):
            fail("invalid_validation_json",
                 f"style-validator output needs result=ok, non-empty files and string notes: {path}")

        try:
            target = str((professor_dir / ANALYSIS_MD).resolve(strict=False))
        except (OSError, RuntimeError, ValueError):
            fail("invalid_validation_json", "managed analysis target cannot be normalized")
        matches = []
        for index, entry in enumerate(data["files"]):
            label = f"style-validator files[{index}]"
            if not isinstance(entry, dict):
                fail("invalid_validation_json", f"{label} must be an object")
            candidate_path = _stage3_normalized_absolute_path(entry.get("file"), f"{label}.file", fail=fail)
            artifact = entry.get("artifact")
            if artifact not in ("analysis", "candidates"):
                fail("invalid_validation_json", f"{label}.artifact must be analysis|candidates")
            verdict = entry.get("verdict")
            if verdict not in ("pass", "pass_with_minor", "fail"):
                fail("invalid_validation_json", f"{label}.verdict is invalid: {verdict!r}")
            blocking_count, minor_count = entry.get("blocking"), entry.get("minor")
            if isinstance(blocking_count, bool) or not isinstance(blocking_count, int) \
                    or blocking_count < 0 or isinstance(minor_count, bool) \
                    or not isinstance(minor_count, int) or minor_count < 0:
                fail("invalid_validation_json",
                     f"{label} blocking/minor counts must be non-negative integers")
            issues = entry.get("issues")
            if not isinstance(issues, list):
                fail("invalid_validation_json", f"{label}.issues must be a list")
            blocking, minor = 0, 0
            for issue_index, issue in enumerate(issues):
                issue_label = f"{label}.issues[{issue_index}]"
                if not isinstance(issue, dict):
                    fail("invalid_validation_json", f"{issue_label} must be an object")
                for field in ("rule", "severity", "quote", "suggestion"):
                    value = issue.get(field)
                    if not isinstance(value, str) or not value.strip():
                        fail("invalid_validation_json",
                             f"{issue_label}.{field} must be a non-empty string")
                location = issue.get("location")
                if isinstance(location, bool) or not (
                        (isinstance(location, int) and location > 0)
                        or (isinstance(location, str) and location.strip()
                            and len(location) <= 20)):
                    fail("invalid_validation_json",
                         f"{issue_label}.location must be a positive line number or a short string")
                if len(issue["quote"]) > 40:
                    fail("invalid_validation_json", f"{issue_label}.quote must be at most 40 characters")
                if issue["severity"] == "blocking":
                    blocking += 1
                elif issue["severity"] == "minor":
                    minor += 1
                else:
                    fail("invalid_validation_json",
                         f"{issue_label}.severity must be blocking|minor")
            if (blocking, minor) != (blocking_count, minor_count):
                fail("invalid_validation_json", f"{label} counts do not match its issues")
            if blocking and verdict != "fail":
                fail("invalid_validation_json", f"{label} blocking issues require verdict=fail")
            if not blocking and verdict == "fail":
                fail("invalid_validation_json", f"{label} fail verdict needs a blocking issue")
            if not blocking and minor and verdict != "pass_with_minor":
                fail("invalid_validation_json", f"{label} minor issues require verdict=pass_with_minor")
            if not blocking and not minor and verdict != "pass":
                fail("invalid_validation_json", f"{label} without issues must have verdict=pass")
            if candidate_path == target:
                matches.append(entry)
        if not matches:
            fail("validation_target_mismatch",
                 f"validator output does not contain the current managed analysis: {target}")
        if len(matches) != 1:
            fail("invalid_validation_json",
                 f"validator output must contain exactly one analysis result for {target}")
        if matches[0].get("artifact") != "analysis":
            fail("validation_target_mismatch",
                 f"validator output marks the managed analysis as another artifact: {target}")

        entry = matches[0]
        render_sha, body = stage2_bound_render(professor_dir, pack)
        try:
            rendered_data = (professor_dir / ANALYSIS_MD).read_bytes()
        except OSError as exc:
            fail("validation_render_missing", f"{professor_dir / ANALYSIS_MD}: {exc}")
        current_header, current_body_bytes = split_frontmatter_bytes(rendered_data)
        try:
            current_body = current_body_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            fail("validation_render_missing", f"{professor_dir / ANALYSIS_MD}: {exc}")
        body_start = rendered_data.find(current_body_bytes)
        if not isinstance(current_header, dict) or current_header.get("managed_by") != MANAGED_BY \
                or current_header.get("state_fingerprint") != stage2_pack_state_fingerprint(pack) \
                or current_header.get("render_sha256") != render_sha \
                or current_body != body or sha256_bytes(current_body_bytes) != render_sha:
            fail("validation_render_stale",
                 "managed analysis changed while the style-validator report was being read")
        if body_start < 0:
            fail("validation_render_stale", "managed analysis body could not be located in its file")
        line_offset = rendered_data[:body_start].count(b"\n")
        direction_rows = pack.get("directions")
        if not isinstance(direction_rows, list) or not direction_rows:
            fail("validation_direction_ambiguous", "input pack has no canonical directions")
        direction_ids = set()
        for direction in direction_rows:
            did = direction_machine_id(direction)
            if not isinstance(did, str) or not did or did in direction_ids:
                fail("validation_direction_ambiguous",
                     "input pack does not contain unique canonical direction IDs")
            direction_ids.add(did)
        lines = body.splitlines()
        ownership = stage2_render_ownership(pack, render_sha, len(lines))

        def stage2_quote_mapping(hit: int, start: int, end: int):
            """Resolve one quote interval through the renderer ownership map.

            The map is the single direction/region authority (plan stage2-u1-r5
            §3.2.2): Markdown headings, prefixes or the current text are never
            scanned to rebuild it. A quote must be fully covered by mapped
            fragments of one direction; a gap, an unknown direction or two
            directions is not repairable.
            """
            overlaps = [fragment for fragment in ownership["fragments"]
                        if isinstance(fragment, dict)
                        and stage2_fragment_overlaps(fragment, hit, start, end)]
            mapped = {fragment.get("direction") for fragment in overlaps
                      if isinstance(fragment.get("direction"), str)}
            if len(mapped) > 1:
                fail("validation_direction_ambiguous",
                     "the ownership map assigns one quote to several directions: "
                     f"{sorted(mapped)}")
            did = next(iter(mapped)) if mapped else None
            spans = sorted(
                (row[1], row[2])
                for fragment in overlaps
                if did is not None and fragment.get("direction") == did
                for row in fragment.get("ranges") or []
                if isinstance(row, list) and len(row) == 3 and row[0] == hit)
            cursor = start
            covered = False
            for span_start, span_end in spans:
                if span_end <= cursor:
                    continue
                if span_start > cursor:
                    break
                cursor = max(cursor, span_end)
                if cursor >= end:
                    covered = True
                    break
            return did, overlaps, covered

        blocking_by_direction: dict[str, list] = {}
        issues_by_direction: dict[str, list] = {}
        fixed_blocking_by_direction: dict[str, list] = {}
        for issue in entry["issues"]:
            quote = issue["quote"]
            hits = [i for i, line in enumerate(lines) if quote in line]
            line_location, location_error = stage2_parse_report_location(issue["location"])
            if location_error:
                fail(location_error,
                     "the style-validator report names a vague multi-position location "
                     f"({issue['location']!r}); re-run the check so every occurrence is reported "
                     "as its own issue with its actual line number (按实际行号逐条重做校验). "
                     f"quote={quote!r}")
            if line_location is not None:
                hits = [i for i in hits if i + 1 + line_offset == line_location]
            if issue["severity"] != "blocking" and len(hits) != 1:
                continue
            if len(hits) != 1:
                fail("validation_quote_ambiguous" if hits else "validation_quote_not_in_render",
                     f"blocking quote must identify exactly one line in the managed render: {quote!r}")
            hit = hits[0]
            if issue["severity"] == "blocking" and lines[hit].count(quote) != 1:
                fail("validation_quote_ambiguous",
                     f"blocking quote appears more than once on its rendered line: {quote!r}")
            quote_start = lines[hit].find(quote)
            quote_end = quote_start + len(quote)
            did, overlaps, covered = stage2_quote_mapping(hit, quote_start, quote_end)
            regions = {fragment.get("region") for fragment in overlaps}
            fixed_fragments = [fragment for fragment in overlaps
                               if fragment.get("region") == "fixed"]
            narrative_fragments = [fragment for fragment in overlaps
                                   if fragment.get("region") == "narrative"]
            if did is not None and covered:
                issues_by_direction.setdefault(did, []).append(issue)
            if issue["severity"] != "blocking":
                continue
            if did is None:
                # A blocking quote with no mapped direction (global preamble,
                # unowned template text, missing map fragment) keeps the old
                # refusal boundary; round 2 must not turn it into a silent pass.
                fail("validation_direction_ambiguous",
                     f"blocking quote has no renderer ownership direction: {quote!r}")
            if not covered:
                if require_repairable:
                    fail("validation_issue_not_repairable",
                         "blocking quote is not fully covered by one direction's renderer "
                         f"ownership map: {quote!r}")
                blocking_by_direction.setdefault(did, []).append(issue)
                continue
            if "excluded" in regions:
                # Existing excluded regions (user notes, paper lists, global red
                # lines) keep their old boundary; they never become fixed cards.
                if require_repairable:
                    fail("validation_issue_not_repairable",
                         f"blocking quote is outside repairable positioning or gap_notes prose: {quote!r}")
                blocking_by_direction.setdefault(did, []).append(issue)
                continue
            if fixed_fragments:
                # A real fixed-evidence blocker: record the source/generator
                # owners so the finding can be handed to the actual data/renderer
                # owner. It never grants the model a right to rewrite the fact.
                blockers, seen_owners = [], set()
                for fragment in fixed_fragments:
                    owner_key = (fragment.get("owner"), fragment.get("gap_id"),
                                 fragment.get("field"))
                    if owner_key in seen_owners:
                        continue
                    seen_owners.add(owner_key)
                    blockers.append({"owner": fragment.get("owner"),
                                     "gap_id": fragment.get("gap_id"),
                                     "field": fragment.get("field")})
                fixed_blocking_by_direction.setdefault(did, []).append({
                    "issue": issue, "owners": blockers,
                    "mixed_narrative": bool(narrative_fragments)})
                blocking_by_direction.setdefault(did, []).append(issue)
                continue
            if not narrative_fragments or any(
                    not fragment.get("repairable") for fragment in narrative_fragments):
                if require_repairable:
                    fail("validation_issue_not_repairable",
                         f"blocking quote is outside repairable positioning or gap_notes prose: {quote!r}")
                blocking_by_direction.setdefault(did, []).append(issue)
                continue
            blocking_by_direction.setdefault(did, []).append(issue)

        return {"validation_sha256": sha256_bytes(raw), "render_sha256": render_sha,
                "verdict": entry["verdict"], "notes": data["notes"],
                "issues": entry["issues"], "issues_by_direction": issues_by_direction,
                "blocking_by_direction": blocking_by_direction,
                "fixed_blocking_by_direction": fixed_blocking_by_direction}

    def stage2_require_recorded_validation(ctx, validation_path: Path) -> tuple[dict, dict, list[str]]:
        """Authorize refinement only from the exact raw report and open recorded findings."""
        pack = ctx.pack if isinstance(ctx.pack, dict) else {}
        validator = pack.get("validator") if isinstance(pack.get("validator"), dict) else {}
        if validator.get("schema") != 2:
            fail("validation_evidence_not_recorded",
                 "record the raw style-validator report with stage2-record-validation first")
        recorded_round = validator.get("round")
        if isinstance(recorded_round, bool) or recorded_round not in (1, 2):
            fail("validation_evidence_not_recorded", "recorded Stage-2 validation round is malformed")
        try:
            raw = validation_path.read_bytes()
        except (OSError, ValueError) as exc:
            fail("validation_evidence_not_recorded", f"{validation_path}: {exc}")
        if sha256_bytes(raw) != validator.get("validation_sha256"):
            fail("validation_evidence_not_recorded",
                 "stage2 refinement must use the exact raw report previously recorded")
        render_sha, _body = stage2_bound_render(ctx.professor_dir, pack)
        if render_sha != validator.get("render_sha256") \
                or stage2_pack_content_fingerprint(pack) != validator.get("pack_sha256"):
            fail("validation_evidence_not_recorded",
                 "the managed render or input pack changed after validation was recorded")
        pending = validator.get("pending")
        results = validator.get("results")
        if not isinstance(pending, dict) or not isinstance(results, dict):
            fail("validation_evidence_not_recorded", "recorded Stage-2 validation state is malformed")
        allowed = {direction_machine_id(d) for d in pack.get("directions", [])}
        corrected = validator.get("correction_applied_direction_ids")
        if not isinstance(corrected, list) or any(not isinstance(did, str) or did not in allowed
                                                   for did in corrected):
            fail("validation_evidence_not_recorded", "recorded correction direction set is malformed")
        unresolved = [did for did in pending if did not in set(corrected)]
        for did, issues in pending.items():
            if did not in allowed or not isinstance(issues, list) or not issues:
                fail("validation_evidence_not_recorded", f"recorded findings are malformed for {did}")
        fixed = validator.get("fixed_blocking")
        if fixed is not None:
            if not isinstance(fixed, dict) or any(
                    not isinstance(did, str) or not isinstance(rows, list)
                    for did, rows in fixed.items()):
                fail("validation_evidence_not_recorded",
                     "recorded fixed-evidence blocker set is malformed")
        phase = validator.get("phase")
        if phase not in ("needs_correction", "awaiting_second_validation", "terminal"):
            fail("validation_evidence_not_recorded", "recorded Stage-2 validation phase is invalid")
        if (phase in ("needs_correction", "awaiting_second_validation") and recorded_round != 1) \
                or (phase == "awaiting_second_validation" and not pending):
            fail("validation_evidence_not_recorded", "recorded Stage-2 phase and round do not agree")
        if phase == "needs_correction" and not unresolved:
            fail("validation_evidence_not_recorded", "recorded correction phase has no open directions")
        if phase == "awaiting_second_validation" and unresolved:
            fail("validation_evidence_not_recorded", "recorded correction is not complete")
        if phase == "terminal":
            unresolved = []
        return validator, pending, unresolved

    def stage2_pack_matches_facts(ctx: Stage2Context) -> None:
        """Do not apply a validator rewrite to facts newer than the accepted pack.

        Compares the ORIGINAL facts fingerprint saved with the accepted pack
        (`provisional_input_fingerprint` on the final direction or on its
        provisional→target mapping row), never the downstream `input_fingerprint`:
        the latter is the resolved-member hash Stage 3 consumes and no longer
        represents the original facts state. A disappeared direction is only legal
        as an already-merged source whose mapping row proves its provenance; a
        genuinely changed fact (including one of a merged-away source) requires a
        refresh instead of silently serving the pack-only path.
        """
        if not ctx.pack:
            fail("missing_input_pack", f"input pack unreadable: {ctx.pack_path}")
        accepted = {direction_machine_id(d): d for d in ctx.pack.get("directions", [])}
        rows = {}
        resolved_block = ctx.pack.get("resolved_directions")
        has_resolution_rows = isinstance(resolved_block, dict) and isinstance(
            resolved_block.get("directions"), list)
        if has_resolution_rows:
            for row in resolved_block.get("directions") or []:
                if isinstance(row, dict) and isinstance(row.get("provisional_direction_id"), str):
                    rows[row["provisional_direction_id"]] = row

        def _refresh(direction_id: str, problem: str) -> None:
            soft_exit("needs_refresh", "source_fingerprint_changed",
                      direction=direction_id, problem=problem,
                      pack_path=str(ctx.pack_path))

        # Identity first: facts from another professor (or another professor
        # directory) must never drive a refinement of this accepted pack.
        facts_professor = ctx.facts.get("professor")
        pack_professor = ctx.pack.get("professor")
        if facts_professor != pack_professor:
            soft_exit("needs_refresh", "source_fingerprint_changed",
                      problem="professor_mismatch", facts_professor=facts_professor,
                      pack_professor=pack_professor, pack_path=str(ctx.pack_path))
        pack_dir_value = ctx.pack.get("professor_dir")
        if isinstance(pack_dir_value, str) and pack_dir_value:
            if _canonical_directory(ctx.professor_dir) != _canonical_directory(pack_dir_value):
                soft_exit("needs_refresh", "source_fingerprint_changed",
                          problem="professor_dir_mismatch",
                          facts_professor_dir=str(ctx.professor_dir),
                          pack_professor_dir=pack_dir_value,
                          pack_path=str(ctx.pack_path))

        for plan in ctx.direction_plans:
            did = plan["did"]
            final = accepted.get(did)
            row = rows.get(did)
            if final is not None:
                recorded = final.get("provisional_input_fingerprint")
                if not isinstance(recorded, str):
                    resolved_subfield = final.get("resolved_direction") or {}
                    if has_resolution_rows or resolved_subfield.get("resolution_type") not in (
                            None, "unchanged"):
                        # Materialized ownership without a provable original source
                        # cannot be compared by the public downstream fingerprint.
                        _refresh(did, "missing_provisional_source_fingerprint")
                    recorded = final.get("input_fingerprint")
                row_recorded = (row or {}).get("provisional_input_fingerprint")
                if isinstance(row_recorded, str) and row_recorded != recorded:
                    _refresh(did, "direction_source_fingerprint_mismatch")
                if recorded != plan["fingerprint"]:
                    _refresh(did, "original_facts_changed")
                continue
            # The provisional direction disappeared from the final pack: it must be
            # an already-merged source whose mapping row keeps the original facts
            # fingerprint and the surviving target.
            if row is None or row.get("resolution_type") != "merged_into":
                _refresh(did, "missing_resolved_source_mapping")
            target = row.get("merge_target")
            if not isinstance(target, str) or target not in accepted:
                _refresh(did, "missing_merge_target")
            recorded = row.get("provisional_input_fingerprint")
            if not isinstance(recorded, str):
                _refresh(did, "missing_provisional_source_fingerprint")
            if recorded != plan["fingerprint"]:
                _refresh(did, "original_facts_changed")

        plan_ids = {plan["did"] for plan in ctx.direction_plans}
        # Every final direction that is not backed by a current provisional plan
        # must be an already-materialized split child whose source row is still in
        # the current facts selection and still declares this child.
        for child_id, child in accepted.items():
            if child_id in plan_ids:
                continue
            subfield = child.get("resolved_direction") or {}
            source_id = subfield.get("provisional_direction_id")
            if subfield.get("resolution_type") != "split_from" \
                    or subfield.get("split_target") != child_id \
                    or not isinstance(source_id, str) or source_id not in plan_ids:
                _refresh(child_id, "unexpected_final_direction")
            source_row = rows.get(source_id) or {}
            if source_row.get("resolution_type") != "split_from" \
                    or source_row.get("split_target") != child_id:
                _refresh(child_id, "unexpected_split_child")
        # Every resolution mapping row must belong to a provisional direction that
        # still exists in the current facts selection; a removed direction makes
        # the old pack unmatchable and requires a refresh.
        for source_id in rows:
            if source_id not in plan_ids:
                _refresh(source_id, "unexpected_resolved_source")

    def stage2_validation_material(ctx, direction: dict) -> dict:
        """The P/later/gap material one final pack direction exposes to a rewrite.

        Read from the ACCEPTED PACK direction (not the provisional facts direction):
        a refinement of a split child or merge target must see that final
        direction's reference licence, trusted paper records and migrated gaps.
        """
        canonical = pack_paper_index(ctx.pack or {})
        paper_keys = set(pack_direction_relevant_keys(direction))
        paper_keys.update(Stage2PackRefineContext.narrative_later_keys_for(direction))
        papers = []
        for key in sorted(paper_keys):
            paper = canonical.get(key) or ctx.papers.get(key)
            if not paper:
                continue
            papers.append({"item_key": key, "title": paper.get("title"),
                           "year": paper.get("year"), "authorship": paper.get("authorship")})
        gaps = []
        for gap in list(direction.get("gap_shortlist") or []) + list(direction.get("gaps_excluded") or []):
            if not isinstance(gap, dict) or not isinstance(gap.get("gap_id"), str):
                continue
            gaps.append({"gap_id": gap.get("gap_id"), "item_key": gap.get("item_key"),
                         "paper_title": gap.get("paper_title"),
                         "paper_year": gap.get("paper_year"),
                         "quote": truncate(gap.get("quote"), QUOTE_INPUT_CHARS),
                         "translation_zh": truncate(gap.get("translation_zh"),
                                                    TRANSLATION_INPUT_CHARS),
                         "status": gap.get("status"), "evidence": gap.get("evidence")})
        return {"papers": papers, "gaps": gaps}

    def stage2_refine_context(args):
        if args.facts:
            ctx = Stage2Context(Path(args.facts))
            stage2_pack_matches_facts(ctx)
        else:
            ctx = Stage2PackRefineContext(Path(args.professor_dir))
        stage2_restore_pack_later_papers(ctx)
        return ctx

    def cmd_stage2_refine_plan(args) -> None:
        ctx = stage2_refine_context(args)
        dids = [direction_machine_id(d) for d in ctx.pack.get("directions", [])]
        allowed = set(dids)
        validator, pending, failed_ids = stage2_require_recorded_validation(
            ctx, Path(args.validation_file))
        fixed = validator.get("fixed_blocking")
        if isinstance(fixed, dict) and any(isinstance(rows, list) and rows
                                           for rows in fixed.values()):
            # A fixed-evidence blocker stops the whole report before any rewrite
            # job is produced; a direction filter may not bypass that rule.
            emit({"status": "needs_owner_fix", "professor": ctx.professor,
                  "reason_code": "fixed_evidence_blocking",
                  "message": "fixed evidence/card text must be repaired by the source-data "
                             "or generator owner; the model may not rewrite these facts",
                  "directions": sorted(fixed), "fixed_blocking": fixed,
                  "jobs": [], "write_needed": False})
            return
        failed = {did: pending[did] for did in failed_ids}
        scope_did = getattr(args, "direction_id", None)
        if getattr(args, "collection_key", None) and not scope_did:
            matches = [d for d in ctx.pack.get("directions", [])
                       if d.get("collection_key") == args.collection_key]
            if len(matches) != 1:
                fail("invalid_params",
                     f"collection_key not found (or ambiguous) in input pack: {args.collection_key}")
            scope_did = direction_machine_id(matches[0])
        if scope_did:
            if scope_did not in allowed:
                fail("invalid_params", f"direction_id not found in input pack: {scope_did}")
            failed = {key: value for key, value in failed.items() if key == scope_did}

        old_directions = {direction_machine_id(d): d for d in ctx.pack.get("directions", [])}
        jobs = []
        for did in sorted(failed):
            direction = old_directions.get(did)
            # The FINAL pack direction is the refinement unit: a split child or a
            # merge target has no provisional facts plan, while a vanished merged
            # source has no final direction at all.
            if not direction or not isinstance(direction.get("narrative"), dict):
                fail("invalid_result_json", f"input pack has no reusable narrative for {did}")
            stage2_require_later_paper_titles(ctx, direction)
            issues = failed[did]
            jobs.append({
                "job_id": f"narrative-rewrite:{ctx.professor}:{did}",
                "kind": "narrative-rewrite",
                "direction_id": did,
                "result_file": f"narrative-rewrite-{filename_component(did)}.json",
                "result_schema": {"schema": 1, "kind": "narrative-rewrite",
                                  "direction_id": did,
                                  "positioning": [{"kind": "para|bullet", "text": "…",
                                                    "refs": ["paper:ITEMKEY"],
                                                    "concrete_object": "具体对象",
                                                    "input_example": "具体输入",
                                                    "output_example": "具体输出"}],
                                  "gap_notes": [{"gap_id": "", "summary": "一句话",
                                                  "explanation": "大白话"}]},
                "model_input": {
                    "direction_id": did,
                    "current_narrative": direction["narrative"],
                    "issues": issues,
                    "allowed_material": stage2_validation_material(ctx, direction),
                    "rules": "返回完整的当前方向 narrative，未命中的 block 和 gap_notes 原样保留，只重写 validator 指出的文字。保留且只使用允许的 paper/later/gap 引用。不得修改 freshness 状态、用户笔记、论文事实或红线。每个 positioning block 必须有 concrete_object、input_example、output_example；text 中占位符集合必须与 refs 完全相等。用最日常中文解释术语，不能把 item_key 写进 text。"},
            })
        reason = None
        if not jobs:
            reason = ("awaiting_second_validation"
                      if validator.get("phase") == "awaiting_second_validation"
                      else "no_failed_directions")
        emit({"status": "ok", "professor": ctx.professor,
              "validation_file": str(Path(args.validation_file)),
              "directions": sorted(failed), "jobs": jobs,
              "write_needed": bool(jobs), "reason_code": reason})

    def cmd_stage2_refine_finalize(args) -> None:
        ctx = stage2_refine_context(args)
        dids = [direction_machine_id(d) for d in ctx.pack.get("directions", [])]
        allowed = set(dids)
        validator, pending, failed_ids = stage2_require_recorded_validation(
            ctx, Path(args.validation_file))
        fixed = validator.get("fixed_blocking")
        if isinstance(fixed, dict) and any(isinstance(rows, list) and rows
                                           for rows in fixed.values()):
            # Consuming a rewrite result would modify facts the model does not own.
            emit({"status": "needs_owner_fix", "professor": ctx.professor,
                  "reason_code": "fixed_evidence_blocking",
                  "message": "fixed evidence/card text must be repaired by the source-data "
                             "or generator owner; the model may not rewrite these facts",
                  "directions": sorted(fixed), "fixed_blocking": fixed,
                  "rewritten": [], "write_needed": False})
            return
        failed = set(failed_ids)
        scope_did = getattr(args, "direction_id", None)
        if getattr(args, "collection_key", None) and not scope_did:
            matches = [d for d in ctx.pack.get("directions", [])
                       if d.get("collection_key") == args.collection_key]
            if len(matches) != 1:
                fail("invalid_params",
                     f"collection_key not found (or ambiguous) in input pack: {args.collection_key}")
            scope_did = direction_machine_id(matches[0])
        if scope_did:
            if scope_did not in allowed:
                fail("invalid_params", f"direction_id not found in input pack: {scope_did}")
            failed &= {scope_did}
        if not failed:
            emit({"status": "ok", "rewritten": [], "write_needed": False,
                  "reason_code": "no_failed_directions"})
            return

        directions = {direction_machine_id(direction): direction
                      for direction in ctx.pack.get("directions", [])}
        for did in sorted(failed):
            direction = directions.get(did)
            if direction is None:
                fail("invalid_result_json", f"input pack has no reusable direction for {did}")
            stage2_require_later_paper_titles(ctx, direction)

        results_dir = Path(args.results)
        rewrites = {}
        for did in sorted(failed):
            path = results_dir / f"narrative-rewrite-{filename_component(did)}.json"
            data, error = read_json_file(path)
            if error:
                fail("result_missing", f"{path}: {error}")
            if not isinstance(data, dict) or data.get("schema") != 1 or data.get("kind") != "narrative-rewrite":
                fail("invalid_result_json", f"{path}: schema/kind must be 1/narrative-rewrite")
            data_did = data.get("direction_id") or data.get("collection_key")
            if data_did != did:
                fail("invalid_result_json", f"{path}: unexpected direction {data_did}")
            _, rewrites[did] = validate_narrative_entry(
                ctx, path, data, expected_did=did,
                scope=stage2_pack_scope(ctx, did), allowed_directions=allowed)

        pack_directions = []
        for direction in ctx.pack.get("directions", []):
            updated = dict(direction)
            if direction_machine_id(direction) in rewrites:
                updated["narrative"] = rewrites[direction_machine_id(direction)]
            pack_directions.append(updated)
        state_fingerprint = sha256_obj({
            "professor": ctx.professor,
            "directions": {direction_machine_id(d): d.get("input_fingerprint")
                           for d in pack_directions}})
        render_pack = {**ctx.pack, "directions": pack_directions}
        # The rewrite must obey the same pre-write reference contract as the
        # ordinary finalize: every {{P:key}} needs the direction's persisted
        # licence and a trusted title in the canonical pack/facts, never a raw
        # item_key fallback in the managed Markdown.
        for direction in pack_directions:
            stage2_require_paper_reference_titles(ctx.papers, render_pack, direction)
        body, ownership = render_analysis_document(ctx, render_pack, state_fingerprint)
        old_render = ((ctx.pack or {}).get("cache") or {}).get("render", {})
        decision = None
        if getattr(args, "decision_file", None):
            decision_data, error = read_json_file(Path(args.decision_file))
            if error is None and isinstance(decision_data, dict):
                decision = decision_data.get("decision")
        md_path = ctx.professor_dir / ANALYSIS_MD
        conflict = managed_conflict(md_path, body,
                                    old_render.get(ANALYSIS_MD, {}).get("sha256"), decision)
        if conflict:
            soft_exit("needs_decision", conflict["reason_code"], target=str(md_path),
                      options=["overwrite", "keep_manual", "promote"])
        md_result = managed_write(md_path, body, state_fingerprint,
                                  old_render.get(ANALYSIS_MD, {}).get("sha256"), decision)
        if md_result.get("needs_decision"):
            soft_exit("needs_decision", md_result["reason_code"], target=md_result.get("target"))
        ownership["body_sha256"] = md_result["sha256"]
        old_render_entry = old_render.get(ANALYSIS_MD)
        if not isinstance(old_render_entry, dict):
            old_render_entry = {}
        old_u1 = old_render_entry.get("u1")
        # A narrative refine re-renders the body, but it is not the normal
        # acceptance entry: it may not create or upgrade the U1 display marker
        # for an old pack (plan stage2-u1-r5 §3.4). Keep an existing marker
        # verbatim; a missing or older one stays missing/older so the next
        # preflight still forces the ordinary process update.
        u1_marker = dict(old_u1) if isinstance(old_u1, dict) else None
        updated_pack = dict(ctx.pack)
        updated_pack["generated_at"] = now_utc()
        updated_pack["directions"] = pack_directions
        # A refinement owns only cache.render; keep the U1 ownership/marker
        # metadata on that render entry. The preflight proof still expires: the
        # rewritten body must re-prove through the slow path (U5 L6).
        cache_block = copy.deepcopy(ctx.pack.get("cache")) \
            if isinstance(ctx.pack.get("cache"), dict) else {}
        cache_block.pop("preflight", None)
        render_block = dict(cache_block.get("render")) \
            if isinstance(cache_block.get("render"), dict) else {}
        render_entry = {"sha256": md_result["sha256"], "ownership": ownership}
        if u1_marker is not None:
            render_entry["u1"] = u1_marker
        render_block[ANALYSIS_MD] = render_entry
        cache_block["render"] = render_block
        updated_pack["cache"] = cache_block
        updated_validator = dict(validator)
        applied = set(updated_validator.get("correction_applied_direction_ids") or [])
        applied.update(rewrites)
        updated_validator["correction_applied_direction_ids"] = sorted(applied)
        still_open = set(pending) - applied
        updated_validator["phase"] = "needs_correction" if still_open else "awaiting_second_validation"
        updated_validator["render_sha256"] = md_result["sha256"]
        updated_validator["pack_sha256"] = stage2_pack_content_fingerprint(updated_pack)
        updated_validator["updated_at"] = now_utc()
        updated_pack["validator"] = updated_validator
        atomic_json(ctx.pack_path, updated_pack)
        emit({"status": "ok", "professor": ctx.professor,
              "rewritten": sorted(rewrites), "analysis_md": str(md_path),
              "md_sha256": md_result["sha256"], "validator_reset": False,
              "round_retained": True, "phase": updated_validator["phase"]})

    def cmd_stage2_record_validation(args) -> None:
        professor_dir = Path(args.professor_dir)
        pack, error = load_input_pack(professor_dir)
        if error or pack is None:
            fail("missing_input_pack", f"input pack unreadable: {professor_dir / INPUT_PACK}")
        previous = pack.get("validator") if isinstance(pack.get("validator"), dict) else {}
        previous_round = previous.get("round", 0)
        if isinstance(previous_round, bool) or not isinstance(previous_round, int) or previous_round < 0:
            fail("validation_evidence_not_recorded", "existing Stage-2 validator round is malformed")
        round_no = 1
        previous_pending = previous.get("pending") if isinstance(previous.get("pending"), dict) else {}
        state_error = None
        if previous.get("schema") == 2:
            if previous_round >= 2:
                state_error = ("validation_rounds_exhausted",
                               "Stage-2 style validation is bounded to two rounds; "
                               "the terminal record already exists")
            else:
                corrected = previous.get("correction_applied_direction_ids")
                if previous_round != 1 or previous.get("phase") != "awaiting_second_validation" \
                        or not isinstance(corrected, list) \
                        or any(not isinstance(did, str) for did in corrected) \
                        or set(previous_pending) - set(corrected):
                    state_error = ("validation_correction_required",
                                   "complete all recorded Stage-2 correction jobs before "
                                   "recording the second round")
                else:
                    round_no = 2

        evidence = stage2_validation_report(Path(args.validation_file), professor_dir, pack,
                                            require_repairable=(state_error is None and round_no == 1))
        if state_error:
            fail(*state_error)
        if round_no == 2:
            old_render, _body = stage2_bound_render(professor_dir, pack)
            if old_render != previous.get("render_sha256") \
                    or stage2_pack_content_fingerprint(pack) != previous.get("pack_sha256"):
                fail("validation_evidence_not_recorded",
                     "the managed render or input pack changed after Stage-2 correction")
        directions = pack.get("directions", [])
        results = {}
        at = now_utc()
        for direction in directions:
            did = direction_machine_id(direction)
            issues = evidence["issues_by_direction"].get(did, [])
            blocking = evidence["blocking_by_direction"].get(did, [])
            result = ("fail_after_2_rounds" if round_no == 2 else "needs_correction") \
                if blocking else "pass"
            results[did] = {"result": result, "rounds": round_no, "issues": issues,
                            "validated_at": at}
        pending = {did: issues for did, issues in evidence["blocking_by_direction"].items()}
        fixed_blocking = {}
        for did, entries in evidence.get("fixed_blocking_by_direction", {}).items():
            rows, seen = [], set()
            for entry in entries:
                for owner in entry.get("owners") or []:
                    marker = (owner.get("gap_id"), owner.get("field"), owner.get("owner"))
                    if marker in seen:
                        continue
                    seen.add(marker)
                    rows.append({"direction_id": did, "gap_id": owner.get("gap_id"),
                                 "field": owner.get("field"), "owner": owner.get("owner")})
            if rows:
                fixed_blocking[did] = rows
        phase = "needs_correction" if round_no == 1 and pending else "terminal"
        if round_no == 2:
            phase = "terminal"
        updated = dict(pack)
        validator = {
            "schema": 2,
            "round": round_no,
            "phase": phase,
            "render_sha256": evidence["render_sha256"],
            "validation_render_sha256": evidence["render_sha256"],
            "validation_sha256": evidence["validation_sha256"],
            "pack_sha256": None,
            "raw_verdict": evidence["verdict"],
            "notes": evidence["notes"],
            "issues": evidence["issues"],
            "results": results,
            "pending": pending,
            "fixed_blocking": fixed_blocking,
            "correction_applied_direction_ids": sorted(
                previous.get("correction_applied_direction_ids") or []) if round_no == 2 else [],
            "updated_at": at,
        }
        updated["validator"] = validator
        validator["pack_sha256"] = stage2_pack_content_fingerprint(updated)
        atomic_json(professor_dir / INPUT_PACK, updated)
        status = "needs_correction" if phase == "needs_correction" else "ok"
        emit({"status": status, "pack_path": str(professor_dir / INPUT_PACK),
              "updated": sorted(results), "round": round_no,
              "raw_verdict": evidence["verdict"], "render_sha256": evidence["render_sha256"],
              "needs_correction": bool(pending and round_no == 1),
              "fixed_blocking": fixed_blocking,
              "needs_owner_fix": bool(fixed_blocking),
              "terminal": phase == "terminal"})

    return types.SimpleNamespace(
        stage2_pack_scope=stage2_pack_scope,
        stage2_bound_render=stage2_bound_render,
        stage2_merge_later_paper_source=stage2_merge_later_paper_source,
        stage2_rendered_later_papers=stage2_rendered_later_papers,
        stage2_restore_pack_later_papers=stage2_restore_pack_later_papers,
        stage2_parse_report_location=stage2_parse_report_location,
        stage2_validation_report=stage2_validation_report,
        stage2_require_recorded_validation=stage2_require_recorded_validation,
        stage2_pack_matches_facts=stage2_pack_matches_facts,
        stage2_validation_material=stage2_validation_material,
        stage2_refine_context=stage2_refine_context,
        cmd_stage2_refine_plan=cmd_stage2_refine_plan,
        cmd_stage2_refine_finalize=cmd_stage2_refine_finalize,
        cmd_stage2_record_validation=cmd_stage2_record_validation,
    )
