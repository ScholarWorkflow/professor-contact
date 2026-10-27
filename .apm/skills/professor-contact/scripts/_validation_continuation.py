#!/usr/bin/env python3
"""Human-authorized validation-round continuation shared by Stage 2 and Stage 3.

The normal bound stays two rounds per stage.  After a stage's validation cycle
has genuinely exhausted that bound, the human may explicitly authorize a
positive integer number of additional rounds; grants accumulate (+2 makes the
limit 4, a later +1 makes it 5).  Nothing here chooses a number for the user,
resets an exhausted cycle, erases a recorded failure or treats a grant as a
passing validation.

Two invariants this module owns:

* a grant binds the exact stage state it was decided on — the caller passes the
  digest of the state file it just read, and the grant is only committed while
  that digest still holds;
* every actually recorded round keeps its own result and report reference, so a
  later correction, next record, final PASS or new cycle never loses an earlier
  failure.

The pure policy helpers are module-level functions (Stage-2 legality, the
preflight acceptance gate and the Stage-3 handoff check read them directly).
The two grant commands need the runner's I/O helpers, so :func:`build` binds
them once in an enclosing scope.  This module never imports the runner and
never builds a second failure channel.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import types


CONTINUATION_VERSION = 1
BASE_ROUND_LIMIT = 2
CONTINUATION_FIELD = "continuation"
HISTORY_FIELD = "history"
ROUND_LIMIT_FIELD = "round_limit"
CYCLE_HISTORY_FIELD = "validation_history"

# Terminal labels the existing readers already understand, plus the extended
# exhaustion a granted cycle produces.  ``fail_after_2_rounds`` stays the label
# of an unextended two-round exhaustion so legacy records keep their meaning.
FAIL_AFTER_TWO = "fail_after_2_rounds"
FAIL_AFTER_MAX = "fail_after_max_rounds"
PASSING_RESULTS = ("pass", "skipped")


def continuation_block(validator: dict | None) -> dict:
    """The recorded continuation object, or an empty one when absent."""
    block = (validator or {}).get(CONTINUATION_FIELD)
    if not isinstance(block, dict):
        return {}
    grants = block.get("grants")
    if not isinstance(grants, list):
        return {**block, "grants": []}
    return block


def grants(validator: dict | None) -> list:
    return list(continuation_block(validator).get("grants") or [])


def round_limit(validator: dict | None) -> int:
    """Effective limit of the current cycle: the base plus every recorded grant."""
    total = BASE_ROUND_LIMIT
    for grant in grants(validator):
        if not isinstance(grant, dict):
            continue
        additional = grant.get("additional_rounds")
        if isinstance(additional, bool) or not isinstance(additional, int) or additional < 1:
            continue
        total += additional
    return total


def recorded_round(validator: dict | None) -> int:
    value = (validator or {}).get("round")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def remaining_rounds(validator: dict | None) -> int:
    return max(round_limit(validator) - recorded_round(validator), 0)


def terminal_failure_label(validator: dict | None) -> str:
    """The exhaustion label for the round currently being recorded.

    An unextended two-round cycle keeps the historical label; any granted limit
    reports the real maximum so the record never claims a bound it did not use.
    """
    return FAIL_AFTER_MAX if round_limit(validator) != BASE_ROUND_LIMIT else FAIL_AFTER_TWO


def history_rows(validator: dict | None) -> list:
    rows = (validator or {}).get(HISTORY_FIELD)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def remember_round(validator: dict | None, row: dict) -> list:
    """Append one actual round to the history, never duplicating a round number.

    The newest record for a round wins: a re-record of the same round (only
    reachable through the existing admission rules) replaces its own row instead
    of leaving two rows that claim the same round.
    """
    round_no = row.get("round")
    kept = [entry for entry in history_rows(validator) if entry.get("round") != round_no]
    kept.append({key: value for key, value in row.items() if value is not None})
    kept.sort(key=lambda entry: (entry.get("round") or 0))
    return kept


def snapshot_for_history(validator: dict | None) -> dict | None:
    """The replaced cycle's own record, moved aside by a genuine new cycle.

    A legacy two-round record that never carried continuation or history is
    still worth keeping: its results are the only proof that the cycle failed.
    The binding fields are kept with it, so the moved record can still prove
    which render and input pack its own ``results`` were recorded against.
    An empty validator block has nothing to preserve and yields ``None``.
    """
    if not isinstance(validator, dict) or not validator:
        return None
    snapshot = {}
    for field in ("schema", "round", "phase", ROUND_LIMIT_FIELD, CONTINUATION_FIELD,
                  HISTORY_FIELD, "render_sha256", "validation_render_sha256",
                  "pack_sha256", "raw_verdict", "results", "pending", "fixed_blocking",
                  "issues", "notes", "validation_sha256",
                  "correction_applied_direction_ids", "updated_at"):
        if field in validator:
            snapshot[field] = validator[field]
    return snapshot or None


def append_cycle_history(state: dict | None, snapshot: dict | None) -> list:
    """Return the state's ``validation_history`` with one replaced cycle appended."""
    rows = (state or {}).get(CYCLE_HISTORY_FIELD)
    history = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    if snapshot:
        history.append(snapshot)
    return history


def validate_grant_request(*, additional_rounds: Any, authorization: Any,
                           expected_round: Any, expected_state_sha256: Any,
                           fail) -> int:
    """Reject a malformed or nonpositive request before any state is read."""
    if isinstance(additional_rounds, bool) or not isinstance(additional_rounds, int) \
            or additional_rounds < 1:
        fail("invalid_params",
             "additional_rounds must be a positive integer chosen by the human; "
             "the runner never picks a number")
    if not isinstance(authorization, str) or not authorization.strip():
        fail("invalid_params",
             "authorization must be the human's own statement for this grant")
    if isinstance(expected_round, bool) or not isinstance(expected_round, int) \
            or expected_round < 1:
        fail("invalid_params", "expected_round must be the round the human decided on")
    digest = expected_state_sha256 if isinstance(expected_state_sha256, str) else ""
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
        fail("invalid_params",
             "expected_state_sha256 must be the SHA-256 of the exact stage state file")
    return additional_rounds


def grant_admission(validator: dict | None, *, expected_round: int,
                    exhausted_phase: bool, fail) -> None:
    """The state must be the exact exhausted cycle the human decided on.

    A grant only ever reopens a cycle that already recorded its whole limit and
    already failed; a passing terminal state, an open correction or an earlier
    round cannot borrow rounds from a decision made about another state.
    """
    recorded = recorded_round(validator)
    if recorded != expected_round:
        fail("validation_round_mismatch",
             f"the recorded round is {recorded}, not the {expected_round} the human "
             "decided on")
    if not exhausted_phase:
        fail("validation_rounds_not_exhausted",
             "an additional-round grant needs a cycle that already recorded its whole "
             "limit and failed")
    limit = round_limit(validator)
    if recorded < limit:
        fail("validation_rounds_not_exhausted",
             f"the cycle still has {limit - recorded} round(s) at limit {limit}; "
             "no grant is needed")
    results = (validator or {}).get("results")
    if not isinstance(results, dict) or not results:
        fail("validation_evidence_not_recorded",
             "the exhausted cycle has no recorded results to continue")
    passing = [ident for ident, row in results.items()
               if isinstance(row, dict) and row.get("result") in PASSING_RESULTS]
    failing = [ident for ident, row in results.items()
               if isinstance(row, dict) and row.get("result") not in PASSING_RESULTS]
    if not failing:
        fail("validation_already_passed",
             "every recorded scope passed; a passing validation cannot be reopened "
             "for extra sampling")
    # Only the recorded failed scope reopens; untouched passing scopes keep
    # their result exactly as recorded.


def build_grant(*, validator: dict | None, additional_rounds: int, authorization: str,
                expected_state_sha256: str, granted_at: str) -> dict:
    """One grant row in the versioned continuation object."""
    block = continuation_block(validator)
    old_limit = round_limit(validator)
    rows = list(block.get("grants") or [])
    rows.append({
        "old_limit": old_limit,
        "additional_rounds": additional_rounds,
        "new_limit": old_limit + additional_rounds,
        "granted_at": granted_at,
        "authorization": authorization.strip(),
        "exhausted_round": recorded_round(validator),
        "expected_state_sha256": expected_state_sha256,
    })
    return {"version": CONTINUATION_VERSION, "base_limit": BASE_ROUND_LIMIT,
            "grants": rows}


def history_row(*, round_no: int, results: dict, render_sha256: str | None,
                validation_file: str | None, validation_sha256: str | None,
                recorded_at: str, pack_sha256: str | None = None,
                input_fingerprints: dict | None = None,
                groups: dict | None = None,
                max_rounds: int | None = None) -> dict:
    """The minimal per-round record: result, bindings and the raw report reference."""
    row = {
        "round": round_no,
        "results": results,
        "render_sha256": render_sha256,
        "validation_file": validation_file,
        "validation_sha256": validation_sha256,
        "recorded_at": recorded_at,
    }
    if pack_sha256 is not None:
        row["pack_sha256"] = pack_sha256
    if input_fingerprints is not None:
        row["input_fingerprints"] = input_fingerprints
    if groups:
        row["groups"] = groups
    if max_rounds is not None:
        row["max_rounds"] = max_rounds
    return row


def continuation_report(validator: dict | None) -> dict:
    """The successful continuation command's machine result."""
    return {"round": recorded_round(validator),
            "round_limit": round_limit(validator),
            "remaining": remaining_rounds(validator),
            "grants": len(grants(validator))}


def build(*, fail, emit, atomic_json, sha256_bytes, sha256_text, now_utc,
          load_input_pack, load_candidate_state, split_frontmatter,
          direction_machine_id, scope_key, stage2_validation_legality,
          stage2_bound_render, stage2_pack_content_fingerprint,
          INPUT_PACK, CANDIDATE_STATE, CANDIDATES_MD):
    """Bind the grant commands to this runner's own helpers."""

    def _state_path(professor_dir: Path, stage: int) -> Path:
        return professor_dir / (INPUT_PACK if stage == 2 else CANDIDATE_STATE)

    def _state_bytes(path: Path) -> bytes:
        try:
            return path.read_bytes()
        except (OSError, ValueError) as exc:
            fail("missing_stage_state", f"{path}: {exc}")

    def _require_expected_digest(path: Path, expected: str) -> bytes:
        raw = _state_bytes(path)
        if sha256_bytes(raw) != expected:
            fail("validation_state_changed",
                 f"{path} is not the state the human decided on; re-read the current "
                 "stage state and grant again against its digest")
        return raw

    def _stage2_loaded(professor_dir: Path) -> tuple[dict, dict]:
        pack, error = load_input_pack(professor_dir)
        if error or pack is None:
            fail("missing_input_pack", f"input pack unreadable: {professor_dir / INPUT_PACK}")
        validator, legality_error = stage2_validation_legality(pack)
        if legality_error:
            fail("validation_evidence_not_recorded",
                 f"recorded Stage-2 validation state is malformed: {legality_error}")
        if not isinstance(validator, dict):
            fail("validation_evidence_not_recorded",
                 "record a raw Stage-2 validator report before asking for more rounds")
        render_sha, _body = stage2_bound_render(professor_dir, pack)
        if validator.get("render_sha256") != render_sha \
                or validator.get("pack_sha256") != stage2_pack_content_fingerprint(pack):
            fail("validation_render_stale",
                 "the recorded Stage-2 validation no longer binds the current managed "
                 "render/input pack; grant on the state the validator actually saw")
        return pack, validator

    def _stage3_loaded(professor_dir: Path) -> tuple[dict, dict, dict]:
        pack, pack_error = load_input_pack(professor_dir)
        if pack is None:
            fail("missing_input_pack",
                 f"input pack unreadable: {professor_dir / INPUT_PACK}")
        state, state_error = load_candidate_state(professor_dir, pack)
        if state_error or state is None:
            fail("missing_candidate_state",
                 f"candidate state unreadable: {professor_dir / CANDIDATE_STATE}")
        validator = state.get("validator")
        if not isinstance(validator, dict) or not isinstance(validator.get("results"), dict):
            fail("validation_evidence_not_recorded",
                 "record a raw Stage-3 validator report before asking for more rounds")
        path = professor_dir / CANDIDATES_MD
        try:
            body = split_frontmatter(path.read_text(encoding="utf-8"))[1]
        except (OSError, UnicodeDecodeError) as exc:
            fail("validation_render_missing", f"{path}: {exc}")
        render_sha = sha256_text(body)
        cache = state.get("cache") if isinstance(state.get("cache"), dict) else {}
        render = cache.get("render") if isinstance(cache.get("render"), dict) else {}
        recorded = render.get(CANDIDATES_MD) if isinstance(render.get(CANDIDATES_MD), dict) else {}
        if recorded.get("sha256") != render_sha or validator.get("render_sha256") != render_sha:
            fail("validation_render_stale",
                 "the recorded Stage-3 validation no longer binds the current candidate "
                 "render; grant on the state the validator actually saw")
        pack_fps = {direction_machine_id(direction): direction.get("input_fingerprint")
                    for direction in pack.get("directions") or [] if isinstance(direction, dict)}
        if state.get("input_fingerprints") != pack_fps:
            fail("validation_source_changed",
                 "the source inputs changed after this Stage-3 round was recorded; "
                 "grant on the state the validator actually saw")
        return pack, state, validator

    def _stage3_pending(validator: dict) -> dict:
        """Reopen exactly the recorded failing scopes, from the record itself.

        A grant authorizes more rounds; it never rewrites evidence.  Each pending
        row therefore keeps the recorded round's own facts — scope, candidate
        ids, issues and the render it was bound to — so the next correction plan
        can still prove it repairs the findings the validator actually wrote.
        """
        pending = {}
        for target in ("results", "groups"):
            rows = validator.get(target)
            if not isinstance(rows, dict):
                continue
            for row in rows.values():
                if not isinstance(row, dict) or row.get("result") in PASSING_RESULTS:
                    continue
                scope = row.get("scope")
                key = scope_key(scope) if isinstance(scope, dict) else "global"
                if key == "global":
                    fail("validation_evidence_not_recorded",
                         "a recorded Stage-3 failure has no direction/group scope")
                pending[key] = dict(row)
        return pending

    def _grant(args, *, stage: int) -> None:
        additional = validate_grant_request(
            additional_rounds=args.additional_rounds,
            authorization=args.authorization,
            expected_round=args.expected_round,
            expected_state_sha256=args.expected_state_sha256,
            fail=fail)
        professor_dir = Path(args.professor_dir)
        path = _state_path(professor_dir, stage)
        _require_expected_digest(path, args.expected_state_sha256)
        if stage == 2:
            pack, validator = _stage2_loaded(professor_dir)
            grant_admission(validator, expected_round=args.expected_round,
                            exhausted_phase=validator.get("phase") == "terminal",
                            fail=fail)
            updated_validator = dict(validator)
            updated_validator[CONTINUATION_FIELD] = build_grant(
                validator=validator, additional_rounds=additional,
                authorization=args.authorization,
                expected_state_sha256=args.expected_state_sha256,
                granted_at=now_utc())
            updated_validator[ROUND_LIMIT_FIELD] = round_limit(updated_validator)
            updated_validator["phase"] = "needs_correction"
            updated_validator["correction_applied_direction_ids"] = []
            updated_validator["pending"] = {
                ident: list(row.get("issues") or [])
                for ident, row in (validator.get("results") or {}).items()
                if isinstance(row, dict) and row.get("result") not in PASSING_RESULTS}
            updated_validator["updated_at"] = now_utc()
            updated = dict(pack)
            updated["validator"] = updated_validator
            updated_validator["pack_sha256"] = stage2_pack_content_fingerprint(updated)
            professor = pack.get("professor")
        else:
            pack, state, validator = _stage3_loaded(professor_dir)
            grant_admission(validator, expected_round=args.expected_round,
                            exhausted_phase=not validator.get("pending"), fail=fail)
            updated_validator = dict(validator)
            updated_validator[CONTINUATION_FIELD] = build_grant(
                validator=validator, additional_rounds=additional,
                authorization=args.authorization,
                expected_state_sha256=args.expected_state_sha256,
                granted_at=now_utc())
            updated_validator[ROUND_LIMIT_FIELD] = round_limit(updated_validator)
            updated_validator["pending"] = _stage3_pending(validator)
            updated_validator["updated_at"] = now_utc()
            updated = dict(state)
            updated["validator"] = updated_validator
            professor = state.get("professor") or pack.get("professor")
        # Compare the exact bytes once more before the single atomic replacement:
        # any concurrent change makes this grant belong to a different state.
        _require_expected_digest(path, args.expected_state_sha256)
        atomic_json(path, updated)
        report = continuation_report(updated_validator)
        emit({"status": "ok", "professor": professor, "stage": stage,
              "state_path": str(path), **report,
              "authorization": args.authorization.strip(),
              "message": (f"已记录人类授权的追加校验轮次：本轮上限 {report['round_limit']}，"
                          f"已完成 {report['round']} 轮，还可校验 {report['remaining']} 轮。"
                          "只重开已记录的失败范围；通过的范围保持原记录。")})

    def cmd_stage2_continue_validation(args) -> None:
        _grant(args, stage=2)

    def cmd_stage3_continue_validation(args) -> None:
        _grant(args, stage=3)

    return types.SimpleNamespace(
        cmd_stage2_continue_validation=cmd_stage2_continue_validation,
        cmd_stage3_continue_validation=cmd_stage3_continue_validation)
