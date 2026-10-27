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
import copy
import importlib.util
import json
import os
import sys
import tempfile
import types


# The human-authorized continuation policy is shared with the Stage-2 helpers and
# the Stage-3 handoff.  It is loaded by path for the same reason the runner does:
# neither the runner nor this helper may assume this directory is on ``sys.path``.
_VALIDATION_CONTINUATION_PATH = Path(__file__).with_name("_validation_continuation.py")
_VALIDATION_CONTINUATION_SPEC = importlib.util.spec_from_file_location(
    "_validation_continuation", _VALIDATION_CONTINUATION_PATH)
if _VALIDATION_CONTINUATION_SPEC is None or _VALIDATION_CONTINUATION_SPEC.loader is None:
    raise RuntimeError(
        f"cannot load validation continuation helpers: {_VALIDATION_CONTINUATION_PATH}")
_validation_continuation = importlib.util.module_from_spec(_VALIDATION_CONTINUATION_SPEC)
_VALIDATION_CONTINUATION_SPEC.loader.exec_module(_validation_continuation)

CONTINUATION_FIELD = _validation_continuation.CONTINUATION_FIELD
HISTORY_FIELD = _validation_continuation.HISTORY_FIELD
ROUND_LIMIT_FIELD = _validation_continuation.ROUND_LIMIT_FIELD
FAIL_AFTER_MAX = _validation_continuation.FAIL_AFTER_MAX
round_limit = _validation_continuation.round_limit
recorded_round = _validation_continuation.recorded_round
terminal_failure_label = _validation_continuation.terminal_failure_label
history_rows = _validation_continuation.history_rows
remember_round = _validation_continuation.remember_round
history_row = _validation_continuation.history_row



def build(*, atomic_json,
          emit,
          fail,
          soft_exit,
          scope_key,
          _stage3_issue_scopes,
          _stage3_validation_files,
          _stage3_normalized_absolute_path,
          _stage3_complete_write_result,
          _require_stage3_handoff_round,
          _stage3_json_object_pairs,
          _stage3_json_reject_constant,
          _stage3_write_buffer,
          stage3_render_line_scopes,
          INPUT_PACK,
          CANDIDATE_STATE,
          CANDIDATES_MD,
          now_utc,
          sha256_bytes,
          sha256_text,
          require_professor_dir_under_program,
          split_frontmatter,
          load_input_pack,
          load_candidate_state,
          profile_fingerprint,
          STAGE3_INVOCATION_VERSION,
          STAGE3_INVOCATION_FILE,
          STAGE3_HANDOFF_VERSION,
          STAGE3_HANDOFF_ROOT,
          STAGE3_HANDOFF_FILE,
          STAGE3_VALIDATOR_OUTPUT_FILE,
          STAGE3_VALIDATION_TARGET_FILE,
          STAGE3_IMMUTABLE_CANDIDATE_FIELDS,
          STAGE3_REPAIRABLE_CANDIDATE_FIELDS,
          STAGE3_INVOCATION_SOURCE_PARAMS):
    def _stage3_bound_render(professor_dir: Path, state: dict) -> tuple[str, str]:
        """Current rendered candidate text, bound to the revision the state records."""
        cache = (state or {}).get("cache")
        recorded = cache.get("render", {}).get(CANDIDATES_MD, {}).get("sha256") \
            if isinstance(cache, dict) and isinstance(cache.get("render"), dict) else None
        path = professor_dir / CANDIDATES_MD
        try:
            body = split_frontmatter(path.read_text(encoding="utf-8"))[1]
        except (OSError, UnicodeDecodeError) as exc:
            fail("validation_render_missing", f"{path}: {exc}")
        current = sha256_text(body)
        if not recorded or current != recorded:
            fail("validation_render_stale",
                 f"{path}: validator evidence must bind the candidate revision recorded in "
                 f"{professor_dir / CANDIDATE_STATE}; re-run the style validator on the current render")
        return current, body

    def _stage3_candidates_entry(data: Any, path: Path, professor_dir: Path) -> tuple[dict, str, list]:
        """Shape-check raw style-validator JSON and return the one candidates entry
        bound to this professor's rendered document, with its verdict and issues.

        Shared by the record entry (r13 §6.4) and the save entry (r13 §6.3); per
        §6.5 the remaining ``files`` entries may belong to other professors of a
        batch call and are not this professor's precondition.
        """
        files = _stage3_validation_files(data, path, fail=fail)
        target = (professor_dir / CANDIDATES_MD).resolve()
        matches = []
        for entry in files:
            if not isinstance(entry, dict) or entry.get("artifact") != "candidates":
                continue
            try:
                candidate_path = Path(entry.get("file") or "").resolve()
            except (OSError, ValueError):
                continue
            if candidate_path == target:
                matches.append(entry)
        if len(matches) != 1:
            fail("invalid_validation_json",
                 f"validator output must contain exactly one candidates result for {target}")
        entry = matches[0]
        verdict = entry.get("verdict")
        if verdict not in ("pass", "pass_with_minor", "fail"):
            fail("invalid_validation_json",
                 f"candidates verdict must be pass|pass_with_minor|fail: {verdict!r}")
        issues = entry.get("issues")
        if not isinstance(issues, list) or not all(isinstance(i, dict) for i in issues):
            fail("invalid_validation_json", "candidates validation issues must be an object list")
        blocking = [i for i in issues if i.get("severity") == "blocking"]
        if verdict == "fail" and not blocking:
            fail("invalid_validation_json", "fail verdict needs at least one blocking issue")
        if verdict != "fail" and blocking:
            fail("invalid_validation_json", "blocking issues require verdict=fail")
        return entry, verdict, issues

    def stage3_validation_evidence(path: Path, professor_dir: Path, state: dict, *,
                                   raw_input: bytes | None = None) -> dict:
        """Normalize raw style-validator JSON into bound, machine-scoped evidence.

        This is the only Stage-3 validator handoff: the runner reads the validator's
        own output, binds it to the exact rendered revision, and routes each finding
        to the canonical scope whose rendered text contains the quoted fragment.  A
        caller never translates ``files[].verdict`` into ``results[]``.  The handoff
        mode (r13 §6.4) passes the already digest-checked byte buffer as
        ``raw_input`` so the digest is proven over the exact bytes parsed here —
        never a snapshot re-opened afterwards.
        """
        if raw_input is None:
            try:
                raw_input = path.read_bytes()
            except (OSError, ValueError):
                fail("invalid_validation_json", f"style-validator output unreadable: {path}")
        input_sha = sha256_bytes(raw_input)
        try:
            data = json.loads(raw_input.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            data = None
        _entry, verdict, issues = _stage3_candidates_entry(data, path, professor_dir)
        blocking = [i for i in issues if i.get("severity") == "blocking"]
        render_sha, body = _stage3_bound_render(professor_dir, state)
        scopes = stage3_render_line_scopes(body)
        rendered = {}
        for scope in scopes:
            if scope:
                rendered.setdefault(scope_key(scope), {k: v for k, v in scope.items()
                                                       if k != "candidate_id"})
        failed: dict = {}
        for issue in blocking:
            for scope in _stage3_issue_scopes(issue, body, scopes, path, fail=fail):
                key = scope_key(scope)
                row = failed.setdefault(key, {"scope": {k: v for k, v in scope.items()
                                                        if k != "candidate_id"},
                                              "candidate_ids": [], "issues": []})
                row["issues"].append({**issue, "scope": scope, "render_sha256": render_sha})
                if scope.get("candidate_id") and scope["candidate_id"] not in row["candidate_ids"]:
                    row["candidate_ids"].append(scope["candidate_id"])
        return {
            "verdict": verdict,
            "render_sha256": render_sha,
            "validation_input_sha256": input_sha,
            "scopes": rendered,
            "failed": failed,
            "issues": issues,
            "blocking": blocking,
        }

    def stage3_correction_scopes(state: dict, evidence: dict) -> list:
        """Scopes a correction round may repair, from recorded evidence only.

        The validator file supplied to a correction command is not authoritative:
        the persisted pending rows are the record of which scopes and issues may be
        repaired.  The current evidence is used only to bind the operation to the
        same rendered revision.
        """
        validator = state.get("validator") if isinstance(state.get("validator"), dict) else {}
        recorded = validator.get("pending") if isinstance(validator.get("pending"), dict) else {}
        if validator.get("render_sha256") != evidence.get("render_sha256"):
            fail("validation_evidence_not_recorded",
                 "record this validator round with stage3-record-validation before planning a correction")
        if evidence["failed"] and not recorded:
            fail("validation_evidence_not_recorded",
                 "the recorded round has no open findings on this render: re-run the style validator "
                 "on the current render and record that round")
        scopes = {}
        for key, row in recorded.items():
            if not isinstance(row, dict):
                fail("validation_evidence_not_recorded",
                     f"recorded validator scope is malformed: {key}")
            scope = row.get("scope")
            issues = row.get("issues")
            candidate_ids = row.get("candidate_ids")
            if not isinstance(scope, dict) or scope_key(scope) != key \
                    or scope.get("kind") not in ("direction", "group") \
                    or not isinstance(issues, list) or not issues \
                    or not isinstance(candidate_ids, list) \
                    or row.get("render_sha256") != evidence["render_sha256"]:
                fail("validation_evidence_not_recorded",
                     f"recorded validator scope is malformed or stale: {key}")
            scopes[key] = {"scope": scope, "candidate_ids": candidate_ids,
                           "issues": issues}
        return [scopes[key] for key in sorted(scopes)]

    def stage3_repairable_correction_directions(correction: dict,
                                                directions: dict) -> set[str]:
        """Directions with candidate state that a correction can replace.

        Recorded scopes remain in ``correction`` even when their direction was
        skipped. A skipped, candidate-less direction is still part of the recorded
        validation scope, but it must not become a generator job or result input.
        """
        return {
            key.split(":", 1)[1]
            for key in correction
            if key.startswith("direction:")
            and isinstance(directions.get(key.split(":", 1)[1]), dict)
            and directions[key.split(":", 1)[1]].get("stage3_status") == "ready"
            and directions[key.split(":", 1)[1]].get("candidates")
        }

    def carry_stage3_validator(old_validator: dict, processed_scopes: set, *,
                               correction: bool, render_sha: str | None) -> dict | None:
        """Rewrite the recorded validator block after the render is replaced.

        Every record binds the render it was produced from, so a scope whose text was
        rewritten loses its old proof and must be validated again.  A correction
        round keeps the round counter — the next recorded round is the terminal one
        for that render — while any other re-render starts a fresh bounded cycle.
        Records for scopes this run did not touch stay valid.

        A correction keeps the whole cycle record (its effective limit, the human
        grants and the per-round history) because the next record is the same
        cycle's next round.  A genuine new generation starts the cycle again at the
        default bound and inherits no grant: only the untouched scopes' results
        survive, which is why the caller moves the replaced cycle aside.
        """
        results = {ident: row for ident, row in (old_validator.get("results") or {}).items()
                   if f"direction:{ident}" not in processed_scopes}
        groups = {ident: row for ident, row in (old_validator.get("groups") or {}).items()
                  if f"group:{ident}" not in processed_scopes}
        if not processed_scopes and not correction:
            # Nothing was regenerated.  When the render is also unchanged the
            # recorded evidence still binds it, so the whole cycle record — round,
            # limit, grants and history — survives a no-op rerender untouched.
            if render_sha is not None and render_sha == old_validator.get("render_sha256"):
                return copy.deepcopy(old_validator)
        if not results and not groups and not correction:
            return None
        carried = {
            "round": recorded_round(old_validator) if correction else 0,
            "render_sha256": render_sha if correction else None,
            "raw_verdict": old_validator.get("raw_verdict") if correction else None,
            "results": results,
            "groups": groups,
            "pending": {},
            "global": (old_validator.get("global") or []) if correction else [],
            "updated_at": old_validator.get("updated_at"),
        }
        if correction:
            carried[ROUND_LIMIT_FIELD] = round_limit(old_validator)
            if old_validator.get(CONTINUATION_FIELD) is not None:
                carried[CONTINUATION_FIELD] = old_validator[CONTINUATION_FIELD]
            carried[HISTORY_FIELD] = history_rows(old_validator)
        return carried

    def stage3_current_result(direction: dict) -> dict:
        return {
            "schema": 2,
            "kind": "candidates",
            "direction_id": direction.get("direction_id"),
            "mode": direction.get("mode"),
            "refined": direction.get("refined"),
            "priority": direction.get("priority") or "",
            "candidates": direction.get("candidates") or [],
        }

    def _paper_refs(candidate: dict) -> list:
        return [{"item_key": paper.get("item_key"),
                 "direction_ids": paper.get("direction_ids") or []}
                for paper in (candidate.get("papers") or []) if isinstance(paper, dict)]

    def require_stage3_correction_invariants(old: dict, new: dict, path: Path,
                                             named_candidates: list | None = None) -> None:
        """A style retry repairs prose the validator may reject, never machine facts.

        Red-line presentation and refined grounding IDs are deliberately excluded
        from the repairable set: the renderer owns their label and dedup rules, so
        asking the model to change them would create findings it is forbidden to
        fix.  ``priority`` and the refined prose fields are repairable precisely
        because the style validator is authorized to reject them.
        """
        if old.get("mode") != new.get("mode"):
            fail("validation_correction_changed_machine_facts",
                 f"{path}: correction changed mode")
        old_refined, new_refined = old.get("refined") or {}, new.get("refined") or {}
        if bool(old.get("refined")) != bool(new.get("refined")):
            fail("validation_correction_changed_machine_facts",
                 f"{path}: correction changed the presence of the refined block")
        if old_refined.get("gap_ids") != new_refined.get("gap_ids"):
            fail("validation_correction_changed_machine_facts",
                 f"{path}: correction changed refined.gap_ids grounding")
        old_candidates = old.get("candidates") or []
        new_candidates = new.get("candidates") or []
        if [c.get("id") for c in old_candidates] != [c.get("id") for c in new_candidates]:
            fail("validation_correction_changed_machine_facts",
                 f"{path}: correction changed candidate IDs or order")
        named = set(named_candidates or [])
        for before, after in zip(old_candidates, new_candidates):
            cid = before.get("id")
            changed = [field for field in STAGE3_IMMUTABLE_CANDIDATE_FIELDS
                       if before.get(field) != after.get(field)]
            if _paper_refs(before) != _paper_refs(after):
                changed.append("papers(item_key/direction_ids)")
            if changed:
                fail("validation_correction_changed_machine_facts",
                     f"{path}: candidate {cid} changed {changed}")
            touched = [field for field in STAGE3_REPAIRABLE_CANDIDATE_FIELDS
                       if before.get(field) != after.get(field)]
            for paper_before, paper_after in zip(before.get("papers") or [],
                                                 after.get("papers") or []):
                for field in ("role", "fit_note"):
                    if (paper_before or {}).get(field) != (paper_after or {}).get(field):
                        touched.append(f"papers[{(paper_before or {}).get('item_key')}].{field}")
            if touched and cid not in named:
                fail("validation_correction_changed_untouched_candidate",
                     f"{path}: candidate {cid} rewrote {touched} without a validator finding")

    def _write_stage3_invocation(directory: str, payload: dict) -> tuple[str, str]:
        """Create this invocation's credential file exclusively (r13 §5.1).

        The caller owns a per-invocation temporary directory; the credential file
        inside it must be created with O_EXCL so a reused directory can never
        silently overwrite an earlier credential.  The returned digest is the
        SHA-256 of the exact bytes written; the file is never modified afterwards.
        """
        dir_path = Path(directory)
        if dir_path.exists() and not dir_path.is_dir():
            fail("invalid_params",
                 f"--capture-invocation must name a directory: {directory}")
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            fail("invalid_params", f"--capture-invocation is unusable: {exc}")
        data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
                + "\n").encode("utf-8")
        target = dir_path / STAGE3_INVOCATION_FILE
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            fail("invalid_params",
                 f"--capture-invocation file already exists (the directory must be "
                 f"exclusive to this invocation): {target}")
        except OSError as exc:
            fail("invalid_params", f"--capture-invocation is unusable: {exc}")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return str(target), sha256_bytes(data)

    def _read_stage3_invocation(args) -> dict | None:
        """Load + verify the invocation credential, or return None (r13 §5.2).

        Refuses the credential mode outright when any first-round source/control
        parameter is re-supplied (mutual exclusion, no precedence), when only one
        half of the file/digest pair is given, when the file is damaged, when the
        version is unsupported, or when the digest does not match the bytes this
        invocation actually read — all before any candidate or state write.
        """
        file_arg = getattr(args, "invocation_file", None)
        sha_arg = getattr(args, "invocation_sha256", None)
        if bool(file_arg) != bool(sha_arg):
            fail("invalid_params",
                 "--invocation-file and --invocation-sha256 must be used together")
        if not file_arg:
            return None
        if getattr(args, "capture_invocation", None):
            fail("invalid_params",
                 "--capture-invocation produces a first-round credential and cannot "
                 "be combined with --invocation-file")
        replayed = [name for name in STAGE3_INVOCATION_SOURCE_PARAMS
                    if getattr(args, name, None) is not None]
        if replayed:
            fail("invalid_params",
                 f"--invocation-file is mutually exclusive with {replayed}; the "
                 "credential alone carries the first-round sources and controls")
        try:
            raw = Path(file_arg).read_bytes()
        except (OSError, ValueError):
            fail("invalid_invocation", f"invocation file unreadable: {file_arg}")
        if sha_arg != sha256_bytes(raw):
            fail("invocation_sha256_mismatch",
                 f"invocation digest does not match the bytes read: {file_arg}")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            fail("invalid_invocation", f"invocation file is not valid JSON: {file_arg}")
        if not isinstance(payload, dict):
            fail("invalid_invocation", f"invocation file must hold a JSON object: {file_arg}")
        if payload.get("version") != STAGE3_INVOCATION_VERSION:
            fail("invocation_version_unsupported",
                 f"invocation version {payload.get('version')!r} is not supported "
                 f"(expected {STAGE3_INVOCATION_VERSION!r}); re-run the first-round "
                 "stage3-plan to produce a fresh credential")
        professor_dir = payload.get("professor_dir")
        program_root = payload.get("program_root")
        for name, value in (("professor_dir", professor_dir), ("program_root", program_root)):
            if not isinstance(value, str) or not value.strip():
                fail("invalid_invocation", f"invocation {name} is missing or not a path")
        # Directory ownership: the credential binds the professor to its program.
        require_professor_dir_under_program(Path(professor_dir), Path(program_root))
        return payload

    def _require_invocation_source(invocation: dict) -> None:
        """The recorded profile digest must still match the real input (r13 §5.2)."""
        recorded_sha = invocation.get("profile_sha256")
        if profile_fingerprint(invocation.get("profile_path")) != recorded_sha:
            soft_exit("needs_refresh", "validation_source_changed",
                      message="调用凭据记录的资料摘要与实际资料不符：重新执行首轮 "
                              "stage3-plan 生成新凭据；未修改任何文件。")

    def _stage3_handoff_directory(
            professor_dir: Path, invocation_file: str | Path, round_no: int) -> Path:
        """This professor's, invocation's and round's exclusive handoff directory.

        The canonical invocation credential path identifies the captured call:
        separate calls may contain identical credential bytes, so their content
        digest alone cannot distinguish them. A repeated prepare for the same
        credential and round still resolves to the same directory and collides.
        """
        professor_token = sha256_text(str(Path(professor_dir).resolve()))[:16]
        invocation_token = sha256_text(str(Path(invocation_file).resolve()))
        return (Path(tempfile.gettempdir()) / STAGE3_HANDOFF_ROOT / professor_token /
                invocation_token / f"round-{round_no}")

    def _load_stage3_handoff(args) -> dict:
        """Load + verify the handoff metadata and its invocation credential.

        Shared by save (r13 §6.3) and record (r13 §6.4): the metadata digest is
        checked against the exact bytes read, every binding must be present, and
        the referenced invocation credential must still be the same bytes with a
        supported version and matching professor ownership.  The caller never
        supplies source, target or professor through other parameters.
        """
        try:
            raw = Path(args.handoff_file).read_bytes()
        except (OSError, ValueError):
            fail("invalid_handoff", f"handoff file unreadable: {args.handoff_file}")
        if args.handoff_sha256 != sha256_bytes(raw):
            fail("handoff_sha256_mismatch",
                 f"handoff digest does not match the bytes read: {args.handoff_file}")
        try:
            metadata = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            fail("invalid_handoff", f"handoff file is not valid JSON: {args.handoff_file}")
        if not isinstance(metadata, dict):
            fail("invalid_handoff", f"handoff file must hold a JSON object: {args.handoff_file}")
        if metadata.get("version") != STAGE3_HANDOFF_VERSION:
            fail("invalid_handoff",
                 f"handoff version {metadata.get('version')!r} is not supported "
                 f"(expected {STAGE3_HANDOFF_VERSION!r})")
        for name in ("professor_dir", "program_root", "candidates_md", "invocation_file",
                     "invocation_sha256", "output_file", "validation_file", "render_sha256"):
            value = metadata.get(name)
            if not isinstance(value, str) or not value.strip():
                fail("invalid_handoff", f"handoff {name} is missing or not a path")
        round_no = metadata.get("round")
        if isinstance(round_no, bool) or not isinstance(round_no, int) or round_no < 1:
            fail("invalid_handoff", f"handoff round must be a positive round: {round_no!r}")
        try:
            credential_raw = Path(metadata["invocation_file"]).read_bytes()
        except (OSError, ValueError):
            fail("invalid_handoff",
                 f"handoff invocation credential unreadable: {metadata['invocation_file']}")
        if metadata["invocation_sha256"] != sha256_bytes(credential_raw):
            fail("invalid_handoff",
                 f"handoff invocation credential no longer matches its recorded digest: "
                 f"{metadata['invocation_file']}")
        try:
            credential = json.loads(credential_raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            fail("invalid_handoff", "handoff invocation credential is not valid JSON")
        if not isinstance(credential, dict) \
                or credential.get("version") != STAGE3_INVOCATION_VERSION:
            fail("invalid_handoff", "handoff invocation credential version is not supported")
        if credential.get("professor_dir") != metadata["professor_dir"] \
                or credential.get("program_root") != metadata["program_root"]:
            fail("invalid_handoff",
                 "handoff professor/program bindings do not match the invocation credential")
        require_professor_dir_under_program(Path(metadata["professor_dir"]),
                                            Path(metadata["program_root"]))
        if Path(metadata["candidates_md"]).resolve() != \
                (Path(metadata["professor_dir"]) / CANDIDATES_MD).resolve():
            fail("invalid_handoff",
                 "handoff candidates_md is not this professor's rendered candidate document")
        return metadata

    def cmd_stage3_prepare_validation(args) -> None:
        """r13 §6.1: prepare this round's one-time validation handoff.

        Reads only the invocation credential, the professor's committed candidate
        state and the bound candidate document; commits and changes nothing.  The
        handoff metadata, the validator output path and the saved target path live
        in a per-professor, per-invocation, per-round exclusive directory under the
        system temporary root — never inside the professor state directory.
        """
        invocation = _read_stage3_invocation(args)
        if invocation is None:
            fail("invalid_params",
                 "stage3-prepare-validation needs an invocation credential "
                 "(--invocation-file + --invocation-sha256)")
        _require_invocation_source(invocation)
        professor_dir = Path(invocation["professor_dir"])
        program_root = Path(invocation["program_root"])
        require_professor_dir_under_program(professor_dir, program_root)
        round_no = args.round
        pack, pack_error = load_input_pack(professor_dir)
        if pack is None:
            fail("missing_input_pack", f"{professor_dir / INPUT_PACK}: {pack_error}")
        state, state_error = load_candidate_state(professor_dir, pack)
        if state_error or state is None:
            fail("missing_candidate_state",
                 f"candidate state unreadable: {professor_dir / CANDIDATE_STATE}")
        render_sha, _body = _stage3_bound_render(professor_dir, state)
        _require_stage3_handoff_round(state, render_sha, round_no, fail=fail)
        directory = _stage3_handoff_directory(
            professor_dir, args.invocation_file, round_no)
        output_file = directory / STAGE3_VALIDATOR_OUTPUT_FILE
        validation_file = directory / STAGE3_VALIDATION_TARGET_FILE
        handoff_file = directory / STAGE3_HANDOFF_FILE
        try:
            directory.mkdir(parents=True)
        except FileExistsError:
            fail("validation_handoff_collision",
                 f"the handoff directory for this professor, invocation and round "
                 f"already exists; earlier round results are never reused: {directory}")
        except OSError as exc:
            fail("validation_handoff_collision", f"handoff directory is unusable: {exc}")
        for label, target in (("output_file", output_file),
                              ("validation_file", validation_file),
                              ("handoff_file", handoff_file)):
            if target.is_symlink() or target.exists():
                fail("validation_handoff_collision",
                     f"{label} already exists; the handoff directory must stay exclusive "
                     f"to this professor, invocation and round: {target}")
        metadata = {
            "version": STAGE3_HANDOFF_VERSION,
            "professor_dir": str(professor_dir.resolve()),
            "program_root": str(program_root.resolve()),
            "candidates_md": str((professor_dir / CANDIDATES_MD).resolve()),
            "invocation_file": str(Path(args.invocation_file).resolve()),
            "invocation_sha256": args.invocation_sha256,
            "round": round_no,
            "render_sha256": render_sha,
            "output_file": str(output_file),
            "validation_file": str(validation_file),
        }
        data = (json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=1)
                + "\n").encode("utf-8")
        try:
            fd = os.open(handoff_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as exc:
            fail("validation_handoff_collision", f"handoff file cannot be created: {exc}")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            handoff_file.unlink(missing_ok=True)
            raise
        emit({
            "status": "ok",
            "professor": pack.get("professor"),
            "professor_dir": str(professor_dir),
            "candidates_md": str((professor_dir / CANDIDATES_MD).resolve()),
            "round": round_no,
            "render_sha256": render_sha,
            "handoff_file": str(handoff_file),
            "handoff_sha256": sha256_bytes(data),
            "output_file": str(output_file),
            "validation_file": str(validation_file),
        })

    def cmd_stage3_write_validation(args) -> None:
        """Create the fixed Stage-3 validator handoff from its complete JSON result."""
        if (args.output_file is None) == (args.output_map_json is None):
            fail("invalid_params", "provide exactly one of --output-file or --output-map-json")
        if args.result_json is None or not args.result_json:
            fail("invalid_validation_json", "--result-json must contain the complete JSON result")
        try:
            data = json.loads(args.result_json,
                              object_pairs_hook=_stage3_json_object_pairs,
                              parse_constant=_stage3_json_reject_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            fail("invalid_validation_json", f"--result-json is invalid: {exc}")
        if not isinstance(data, dict):
            fail("invalid_validation_json", "--result-json must be a JSON object")
        entries = _stage3_complete_write_result(data, Path("--result-json"), fail=fail)
        candidate_entries = [(candidate_path, entry) for candidate_path, entry in entries
                             if entry.get("artifact") == "candidates"]

        output_pairs: list[tuple[str, str]] = []
        if args.output_file is not None:
            if len(candidate_entries) != 1:
                fail("invalid_params", "--output-file requires exactly one candidates entry")
            output_pairs.append((candidate_entries[0][0], args.output_file))
        else:
            try:
                mapping = json.loads(args.output_map_json,
                                     object_pairs_hook=_stage3_json_object_pairs,
                                     parse_constant=_stage3_json_reject_constant)
            except (json.JSONDecodeError, ValueError) as exc:
                fail("invalid_params", f"--output-map-json is invalid: {exc}")
            if not isinstance(mapping, list) or not mapping:
                fail("invalid_params", "--output-map-json must be a non-empty JSON list")
            expected_paths = {candidate_path for candidate_path, _entry in candidate_entries}
            mapped_paths = set()
            for index, item in enumerate(mapping):
                if not isinstance(item, dict) or set(item) != {"file", "output_file"}:
                    fail("invalid_params",
                         f"--output-map-json[{index}] must contain only file and output_file")
                candidate_path = _stage3_normalized_absolute_path(
                    item.get("file"), f"--output-map-json[{index}].file", fail=fail)
                if candidate_path in mapped_paths:
                    fail("invalid_params", f"duplicate candidate path in output map: {candidate_path}")
                if candidate_path not in expected_paths:
                    fail("invalid_params", f"output map contains an unrelated candidate path: {candidate_path}")
                mapped_paths.add(candidate_path)
                output_pairs.append((candidate_path, item.get("output_file")))
            if mapped_paths != expected_paths:
                missing = sorted(expected_paths - mapped_paths)
                fail("invalid_params", "--output-map-json must map every candidates entry exactly once",
                     missing_files=missing)

        targets: list[Path] = []
        normalized_targets = set()
        for candidate_path, output_value in output_pairs:
            target_value = _stage3_normalized_absolute_path(output_value, "output_file", fail=fail)
            target = Path(output_value)
            if target_value in normalized_targets:
                fail("invalid_params", f"output paths must be unique: {output_value}")
            normalized_targets.add(target_value)
            if os.path.lexists(target):
                fail("validation_handoff_collision", f"output target already exists: {output_value}",
                     failed_path=output_value, completed_paths=[])
            if not target.parent.is_dir():
                fail("invalid_output_path", f"output parent directory must already exist: {target.parent}",
                     failed_path=output_value, completed_paths=[])
            targets.append(target)

        try:
            raw = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1,
                              allow_nan=False) + "\n").encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            fail("invalid_validation_json", f"validator result cannot be serialized as UTF-8: {exc}")
        if not raw:
            fail("invalid_validation_json", "validator result serialized to an empty buffer")

        completed = []
        for target in targets:
            try:
                _stage3_write_buffer(target, raw)
            except OSError as exc:
                fail("validation_write_failed", f"cannot write validator result: {exc}",
                     failed_path=str(target), reason=str(exc), completed_paths=completed)
            completed.append(str(target))

        try:
            sys.stdout.buffer.write(raw)
            sys.stdout.buffer.flush()
        except OSError as exc:
            fail("validation_output_failed", f"cannot write validator result to stdout: {exc}",
                 failed_path=None, reason=str(exc), completed_paths=completed)

    def cmd_stage3_save_validation(args) -> None:
        """r13 §6.3: copy the validator's raw output bytes to the recorded target.

        Source, target, professor and round all come from the verified handoff
        metadata; the caller cannot pass content, another source or another
        target.  One read of the regular (non-symlink) source fixes the byte
        buffer that is validated, then written unchanged — no re-serialization,
        no field sorting, no whitespace edits — to a target created exclusively.
        A normal failure removes only a target this entry created itself and
        never deletes the source, the credential or committed professor files.
        """
        metadata = _load_stage3_handoff(args)
        professor_dir = Path(metadata["professor_dir"])
        round_no = metadata["round"]
        pack, pack_error = load_input_pack(professor_dir)
        if pack is None:
            fail("missing_input_pack", f"{professor_dir / INPUT_PACK}: {pack_error}")
        state, state_error = load_candidate_state(professor_dir, pack)
        if state_error or state is None:
            fail("missing_candidate_state",
                 f"candidate state unreadable: {professor_dir / CANDIDATE_STATE}")
        render_sha, _body = _stage3_bound_render(professor_dir, state)
        if render_sha != metadata["render_sha256"]:
            fail("validation_render_changed",
                 "the committed candidate render changed since this handoff was prepared; "
                 "re-run stage3-prepare-validation on the current render")
        _require_stage3_handoff_round(state, render_sha, round_no, fail=fail)
        source = Path(metadata["output_file"])
        target = Path(metadata["validation_file"])
        if source.is_symlink() or not source.is_file():
            fail("invalid_validation_source",
                 f"the validator output must be this round's regular source file: {source}")
        if target.is_symlink() or target.exists():
            fail("validation_handoff_collision",
                 f"the validation target already exists: {target}")
        try:
            raw = source.read_bytes()
        except (OSError, ValueError):
            fail("invalid_validation_source", f"validator output unreadable: {source}")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            fail("invalid_validation_json",
                 f"validator output is not complete UTF-8 JSON: {source}")
        _entry, _verdict, _issues = _stage3_candidates_entry(data, source, professor_dir)
        if not isinstance(data.get("notes"), str):
            fail("invalid_validation_json",
                 f"validator output must hold the complete result/files/notes structure: {source}")
        created = False
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created = True
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException as exc:
            # A normal failure removes only the unfinished target this entry
            # created; sources, credentials and committed files stay untouched.
            if created:
                try:
                    target.unlink(missing_ok=True)
                except OSError:
                    pass
            if isinstance(exc, OSError):
                fail("validation_handoff_collision",
                     f"validation target cannot be created: {exc}")
            raise
        emit({
            "status": "ok",
            "professor": pack.get("professor"),
            "professor_dir": str(professor_dir),
            "round": round_no,
            "render_sha256": render_sha,
            "validation_file": str(target),
            "validation_sha256": sha256_bytes(raw),
        })

    def cmd_stage3_record_validation(args) -> None:
        """Record one real Stage-3 validator round from its own raw output.

        The runner owns the translation: rounds are counted here, the terminal
        verdict per machine scope is derived from the validator's own findings, and
        the record is bound to the rendered revision it describes.  Nothing in the
        written state can be asserted by a caller.

        The handoff mode (r13 §6.4, ``--handoff-file`` + ``--handoff-sha256`` +
        ``--expected-validation-sha256``) takes the professor and validation path
        from the verified handoff metadata and digest-checks the exact byte buffer
        it then parses — the legacy ``--professor-dir`` + ``--validation-file``
        calls keep their behavior unchanged, and the two modes are mutually
        exclusive.
        """
        handoff_triple = (getattr(args, "handoff_file", None),
                          getattr(args, "handoff_sha256", None),
                          getattr(args, "expected_validation_sha256", None))
        handoff_mode = any(handoff_triple)
        if handoff_mode and not all(handoff_triple):
            fail("invalid_params",
                 "--handoff-file, --handoff-sha256 and --expected-validation-sha256 "
                 "must be used together")
        legacy_pair = (getattr(args, "professor_dir", None),
                       getattr(args, "validation_file", None))
        if bool(legacy_pair[0]) != bool(legacy_pair[1]):
            fail("invalid_params",
                 "stage3-record-validation needs --professor-dir and --validation-file together")
        if handoff_mode and any(legacy_pair):
            fail("invalid_params",
                 "the handoff mode is mutually exclusive with --professor-dir and "
                 "--validation-file; the handoff metadata alone carries both")
        if not handoff_mode and not all(legacy_pair):
            fail("invalid_params",
                 "stage3-record-validation needs --professor-dir + --validation-file, "
                 "or the handoff mode (--handoff-file + --handoff-sha256 + "
                 "--expected-validation-sha256)")
        metadata = None
        if handoff_mode:
            metadata = _load_stage3_handoff(args)
            professor_dir = Path(metadata["professor_dir"])
            validation_path = Path(metadata["validation_file"])
        else:
            professor_dir = Path(args.professor_dir)
            validation_path = Path(args.validation_file)
        pack, _ = load_input_pack(professor_dir)
        state, state_error = load_candidate_state(professor_dir, pack)
        if state_error or state is None:
            fail("missing_candidate_state",
                 f"candidate state unreadable: {professor_dir / CANDIDATE_STATE}")
        previous = state.get("validator") if isinstance(state.get("validator"), dict) else {}
        raw_round = recorded_round(previous)
        # The default bound plus every round the human explicitly granted on this
        # exhausted cycle; a legacy state with no grant keeps exactly two.
        limit = round_limit(previous)
        previous_pending = (
            previous.get("pending") if isinstance(previous.get("pending"), dict) else {}
        )
        if raw_round >= 1 and previous_pending:
            fail(
                "validation_correction_required",
                "complete the recorded Stage-3 correction with stage3-plan/finalize "
                "--validation-file before recording another validator round",
            )
        raw_input = None
        if handoff_mode:
            # r13 §6.4: the render and round must still match the verified handoff,
            # and the digest must hold over the exact bytes parsed below — never
            # over one snapshot while another file is opened for the record.
            render_sha, _body = _stage3_bound_render(professor_dir, state)
            if render_sha != metadata["render_sha256"]:
                fail("validation_render_changed",
                     "the committed candidate render changed since this handoff was "
                     "prepared; re-run stage3-prepare-validation")
            _require_stage3_handoff_round(state, render_sha, metadata["round"], fail=fail)
            if validation_path.is_symlink() or not validation_path.is_file():
                fail("invalid_validation_source",
                     f"the recorded validation file must be this round's regular "
                     f"target file: {validation_path}")
            try:
                raw_input = validation_path.read_bytes()
            except (OSError, ValueError):
                fail("invalid_validation_json",
                     f"style-validator output unreadable: {validation_path}")
            if sha256_bytes(raw_input) != args.expected_validation_sha256:
                fail("validation_sha256_mismatch",
                     f"the recorded validation bytes do not match the digest returned by "
                     f"stage3-save-validation: {validation_path}")
        evidence = stage3_validation_evidence(validation_path, professor_dir, state,
                                              raw_input=raw_input)
        round_no = raw_round + 1
        if metadata is not None and round_no != metadata["round"]:
            fail("validation_round_sequence_invalid",
                 f"the recorded round {round_no} does not match the handoff round "
                 f"{metadata['round']}")
        if round_no > limit:
            fail("validation_rounds_exhausted",
                 f"Stage-3 style validation is bounded to {limit} round(s) for this "
                 "cycle; the terminal record already exists")
        results = dict(previous.get("results") or {}) if isinstance(previous.get("results"), dict) else {}
        groups = dict(previous.get("groups") or {}) if isinstance(previous.get("groups"), dict) else {}
        pending = dict(previous.get("pending") or {}) if isinstance(previous.get("pending"), dict) else {}
        at = now_utc()
        exhausted = round_no >= limit
        # A failure at the cycle's real bound carries the exhaustion label; every
        # earlier failing round stays a plain `fail` that still needs correction.
        failure_label = terminal_failure_label(previous) if exhausted else "fail"
        summary = []
        global_issues = (evidence["failed"].get("global") or {}).get("issues") or []
        if global_issues:
            rendered_scopes = {
                key: scope for key, scope in evidence["scopes"].items()
                if key != "global"
            }
            if not rendered_scopes:
                fail("validation_evidence_not_recorded",
                     "global validator issues cannot be assigned to a rendered direction or group")
            for key, scope in rendered_scopes.items():
                row = evidence["failed"].setdefault(
                    key, {"scope": scope, "candidate_ids": [], "issues": []})
                row["issues"].extend(
                    {**issue, "scope": scope, "render_sha256": evidence["render_sha256"]}
                    for issue in global_issues
                )
        for key, scope in sorted(evidence["scopes"].items()):
            if key == "global":
                continue
            kind, _, ident = key.partition(":")
            row = evidence["failed"].get(key) or {}
            issues = row.get("issues") or []
            record = {
                "result": "pass" if not issues else failure_label,
                "rounds": round_no,
                "issues": issues,
                "candidate_ids": row.get("candidate_ids") or [],
                "scope": scope,
                "render_sha256": evidence["render_sha256"],
                "validated_at": at,
            }
            if record["result"] == FAIL_AFTER_MAX:
                record["max_rounds"] = limit
            target = results if kind == "direction" else groups
            if issues and not exhausted:
                target.pop(ident, None)
                pending[key] = record
            else:
                target[ident] = record
                pending.pop(key, None)
            summary.append({"scope": key, "result": record["result"], "rounds": round_no,
                            "blocking": len(issues)})
        updated = dict(state)
        validator = {
            "round": round_no,
            ROUND_LIMIT_FIELD: limit,
            "render_sha256": evidence["render_sha256"],
            "raw_verdict": evidence["verdict"],
            "results": results,
            "groups": groups,
            "pending": pending,
            "global": (evidence["failed"].get("global") or {}).get("issues") or [],
            "updated_at": at,
        }
        if previous.get(CONTINUATION_FIELD) is not None:
            validator[CONTINUATION_FIELD] = copy.deepcopy(previous[CONTINUATION_FIELD])
        # The history row records this round's own results only, together with the
        # render and source bindings it was produced from and the raw report it
        # was parsed out of.  A later round never rewrites an earlier row, and a
        # failing scope that moved into ``pending`` still keeps its row here.
        round_results = {ident: copy.deepcopy(record)
                         for ident, record in results.items()
                         if record.get("rounds") == round_no}
        round_results.update({f"group:{ident}": copy.deepcopy(record)
                              for ident, record in groups.items()
                              if record.get("rounds") == round_no})
        for key, record in pending.items():
            if not isinstance(record, dict) or record.get("rounds") != round_no:
                continue
            scope = record.get("scope") if isinstance(record.get("scope"), dict) else {}
            if scope.get("kind") == "group":
                round_results[f"group:{scope.get('group_id')}"] = copy.deepcopy(record)
            elif scope.get("direction_id"):
                round_results[scope["direction_id"]] = copy.deepcopy(record)
        validator[HISTORY_FIELD] = remember_round(previous, history_row(
            round_no=round_no, results=round_results,
            render_sha256=evidence["render_sha256"],
            validation_file=str(validation_path),
            validation_sha256=evidence["validation_input_sha256"],
            recorded_at=at,
            input_fingerprints=copy.deepcopy(state.get("input_fingerprints") or {}),
            max_rounds=limit if exhausted else None))
        updated["validator"] = validator
        atomic_json(professor_dir / CANDIDATE_STATE, updated)
        emit({"status": "ok", "state_path": str(professor_dir / CANDIDATE_STATE),
              "round": round_no, "round_limit": limit,
              "remaining": max(limit - round_no, 0),
              "raw_verdict": evidence["verdict"],
              "render_sha256": evidence["render_sha256"], "scopes": summary,
              "validation_input_sha256": evidence["validation_input_sha256"],
              "needs_correction": bool(pending),
              "terminal": not pending})

    return types.SimpleNamespace(
                _stage3_bound_render=_stage3_bound_render,
                _stage3_candidates_entry=_stage3_candidates_entry,
                stage3_validation_evidence=stage3_validation_evidence,
                stage3_correction_scopes=stage3_correction_scopes,
                stage3_repairable_correction_directions=stage3_repairable_correction_directions,
                carry_stage3_validator=carry_stage3_validator,
                stage3_current_result=stage3_current_result,
                _paper_refs=_paper_refs,
                require_stage3_correction_invariants=require_stage3_correction_invariants,
                _write_stage3_invocation=_write_stage3_invocation,
                _read_stage3_invocation=_read_stage3_invocation,
                _require_invocation_source=_require_invocation_source,
                _stage3_handoff_directory=_stage3_handoff_directory,
                _load_stage3_handoff=_load_stage3_handoff,
                cmd_stage3_prepare_validation=cmd_stage3_prepare_validation,
                cmd_stage3_write_validation=cmd_stage3_write_validation,
                cmd_stage3_save_validation=cmd_stage3_save_validation,
                cmd_stage3_record_validation=cmd_stage3_record_validation,
    )
