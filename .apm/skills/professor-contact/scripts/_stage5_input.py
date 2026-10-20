#!/usr/bin/env python3
"""Stage-5 helper module for ``contact_state.py``.

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
import json
import os
import types





def build(*, emit,
          fail,
          soft_exit,
          STAGE4_LOCAL_SCHEMA,
          EMAIL_PACK_KIND,
          EMAIL_PACK,
          sha256_text,
          read_json_file,
          professor_dir_containment_error,
          require_professor_dir_under_program,
          filename_component):
    def stage5_output_peers(email: dict, all_emails: list, professor_dir: Path,
                            *, targeted: bool) -> list:
        """Rows that share this email's output-collision namespace.

        Targeted mode cannot resolve unrelated ``professor_dir`` values, so it
        derives peers from identity metadata only. Batch mode preserves the
        pre-Issue-59 directory-scoped naming contract after the normal all-row path
        validation has succeeded.
        """
        if not targeted:
            target_dir = professor_dir.resolve()
            peers = []
            for candidate in all_emails:
                candidate_dir = Path(
                    candidate.get("professor_dir") or professor_dir).resolve()
                if candidate_dir == target_dir:
                    peers.append(candidate)
            return peers

        professor = email.get("professor")
        if not isinstance(professor, str) or not professor:
            return [email]
        peers = []
        seen_ids = set()
        for peer in all_emails:
            if not isinstance(peer, dict) or peer.get("professor") != professor:
                continue
            peer_id = peer.get("email_id")
            if not isinstance(peer_id, str) or not peer_id or peer_id in seen_ids:
                continue
            seen_ids.add(peer_id)
            peers.append(peer)
        return peers or [email]

    def stage5_output_paths(email: dict, peers: list, professor_dir: Path,
                            kind: str = "initial") -> tuple[Path, Path]:
        prefix = "套磁跟进邮件" if kind == "followup" else "套磁邮件"
        if len(peers) <= 1:
            return professor_dir / f"{prefix}.md", professor_dir / f"{prefix}.txt"
        email_id = str(email.get("email_id") or "email")
        idea_id = (email.get("idea") or {}).get("id") or "email"
        # Issue #8 §8.2: the filename suffix derives from the canonical direction
        # scope + email id hash — a v2 entry may not have a collection_key at all.
        scope = "+".join(sorted(email.get("direction_ids") or [idea_id]))
        suffix = "_".join((filename_component(scope),
                             filename_component(idea_id), sha256_text(email_id)[:8]))
        return (professor_dir / f"{prefix}_{suffix}.md",
                professor_dir / f"{prefix}_{suffix}.txt")

    def stage5_output_id(email_id: str, kind: str) -> str:
        return email_id if kind == "initial" else f"{email_id}::followup"

    def select_stage5_email(all_emails: list, requested_email_id: str) -> list:
        """Resolve ``--email-id`` into the hard single-email execution scope.

        Identity resolution happens before any path, evidence, cache, result or
        state validation, so an unrelated malformed pack entry can neither block
        nor be mistaken for the target: non-dict rows and rows without the
        requested id are skipped while searching. An id that appears more than
        once is an ambiguous pack and fails closed rather than picking one."""
        matches = [row for row in all_emails
                   if isinstance(row, dict) and row.get("email_id") == requested_email_id]
        if not matches:
            fail("invalid_params", f"email_id not found: {requested_email_id}")
        if len(matches) > 1:
            fail("invalid_email_pack",
                 f"email pack contains duplicate email_id: {requested_email_id}")
        return matches

    def stage5_mode(args) -> str:
        mode = getattr(args, "mode", None) or "first"
        if mode not in ("first", "both", "followup"):
            fail("invalid_params", f"invalid stage-5 mode: {mode}")
        return mode

    def stage5_pack_owner(pack, pack_path: Path) -> dict:
        """The single professor a Stage-5 pack claims, or a fail-closed stop.

        Issue #67's professor-local ``<professor_dir>/邮件输入.json`` is the only pack
        Stage 5 accepts: the legacy program-level pack is #67's migration input, not
        a second Stage-5 authority, so a pack that cannot name exactly one professor
        inside the program stops the run before any row is read.
        """
        if not isinstance(pack, dict):
            fail("invalid_email_pack", "email pack is not an object", email_pack=str(pack_path))
        if pack.get("schema") != STAGE4_LOCAL_SCHEMA or pack.get("kind") != EMAIL_PACK_KIND:
            fail("invalid_email_pack",
                 f"email pack must be the professor-local schema {STAGE4_LOCAL_SCHEMA} "
                 f"{EMAIL_PACK} written by stage4-finalize", email_pack=str(pack_path))
        professor = pack.get("professor")
        professor_dir = pack.get("professor_dir")
        if not isinstance(professor, str) or not professor.strip() or \
                not isinstance(professor_dir, str) or not professor_dir.strip():
            fail("invalid_email_pack", "email pack does not prove a single professor owner",
                 email_pack=str(pack_path))
        return {"professor": professor, "professor_dir": Path(professor_dir)}

    def stage5_local_pack(args, program_root: Path) -> tuple[Path, dict, list, list]:
        """Resolve the one professor-local pack that owns this Stage-5 run.

        Returns ``(pack_path, pack, pack_rows, selected_rows)``. ``--email-pack`` is
        mandatory and is the only fact source, so no program-level path is ever
        constructed here. Row-level validity keeps the Issue #59 ordering: id
        resolution stays the first boundary, so an unselected malformed row cannot
        become a precondition of the selected transaction, while the selected rows
        must still agree with the pack's own professor ownership.
        """
        if not getattr(args, "email_pack", None):
            fail("invalid_params",
                 "stage5 requires --email-pack with the professor-local "
                 f"{EMAIL_PACK} written by stage4-finalize")
        pack_path = Path(args.email_pack)
        pack, error = read_json_file(pack_path)
        if error:
            soft_exit("needs_refresh", "missing_email_pack", email_pack=str(pack_path),
                      message="缺该教授的 邮件输入.json：先跑阶段 4（professor-contact-selection）编译。")
        owner = stage5_pack_owner(pack, pack_path)
        require_professor_dir_under_program(owner["professor_dir"], program_root)
        all_emails = pack.get("emails")
        if not isinstance(all_emails, list):
            fail("invalid_email_pack", "email pack has no emails list", email_pack=str(pack_path))
        emails = (select_stage5_email(all_emails, args.email_id) if args.email_id
                  else all_emails)
        if not args.email_id:
            all_ids = [email.get("email_id") for email in all_emails]
            if len(set(all_ids)) != len(all_ids) or any(not isinstance(email_id, str) for email_id in all_ids):
                fail("invalid_email_pack", "email pack contains duplicate or missing email_id")
        for email in emails:
            if not isinstance(email, dict):
                fail("invalid_email_pack", "email pack row is not an object",
                     email_pack=str(pack_path))
            professor_dir = Path(email.get("professor_dir") or program_root)
            # Escaped paths keep their own reason code and stay first: an outside
            # program root is an invalid_professor_dir contract, not a ownership one.
            require_professor_dir_under_program(professor_dir, program_root)
            if email.get("professor") != owner["professor"] or \
                    professor_dir.resolve() != owner["professor_dir"].resolve():
                fail("invalid_email_pack",
                     f"{email.get('email_id')}: row names a professor other than the "
                     f"pack owner {owner['professor']}", email_pack=str(pack_path),
                     professor_dir=str(professor_dir))
        return pack_path, pack, all_emails, emails

    def stage5_choices_rows(path: Path) -> list:
        """The raw caller rows: ``choices`` stays a plain object or object list.

        Non-dict rows are unattributable noise under the Issue #68 §3 attribution
        order — they name no professor, so they can neither be validated nor fail
        any professor — matching the targeted noise contract ``load_id_map``
        already kept for them.
        """
        data, error = read_json_file(path)
        if error:
            fail("invalid_result_json", f"choices unreadable: {path}: {error}")
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = [data]
        else:
            fail("invalid_result_json", "choices must be an object or a list of objects")
        return [row for row in rows if isinstance(row, dict)]

    def stage5_choices_by_id(args, owner: dict, emails: list) -> dict:
        """Owner-local ``choices`` loader for one professor transaction.

        Plan r12 §3.3/§3.5: cross-professor attribution happened exactly once at
        the root partition entry (``stage5-partition-choices``), so this loader
        only ever consumes the current owner's one-professor bundle rows. An
        explicit ``professor_dir`` row naming another professor is a caller
        contract violation: the runner fails closed as this owner's input error
        and never re-routes the row to its professor. The professor's own
        explicit rows keep the frozen #59 / R68-2 / R68-3 behavior: a targeted
        run (``--email-id``) filters unselected, missing or unknown ids before
        any ownership or field judgment — they never block the target and never
        count as a legal explicit binding — while a full-professor batch treats
        an id outside the pack's execution range as ``needs_input``
        ``choice_owner_invalid``. Legacy rows without a directory keep the
        exact-one binding semantics as this professor's own business validation:
        a row whose id sits inside the current execution range binds and joins
        the exact-one duplicate check, anything else is noise. Duplicate,
        missing and field checks below belong to this professor alone.
        """
        choices_path = getattr(args, "choices", None)
        if not choices_path:
            return {}
        rows = stage5_choices_rows(Path(choices_path))
        owner_dir = str(owner["professor_dir"].resolve())
        targeted = bool(getattr(args, "email_id", None))
        expected = {email.get("email_id") for email in emails}
        attributed: dict = {}
        legacy_rows = []
        for row in rows:
            row_id = row.get("email_id")
            raw_dir = row.get("professor_dir")
            if "professor_dir" in row:
                if not isinstance(raw_dir, str) or not raw_dir.strip():
                    # An invalid explicit directory is never a legacy binding.
                    continue
                canonical = str(Path(raw_dir).resolve())
                if canonical != owner_dir:
                    # Another professor's row reached this owner-local bundle:
                    # fail closed on this owner's input, never re-route the row.
                    fail("invalid_params",
                         f"owner-local choices name another professor: {raw_dir}",
                         professor_dir=str(canonical))
                if row_id not in expected:
                    if targeted:
                        # R68-2: a targeted run filters the professor's unselected
                        # ids before any ownership or field judgment — an explicit
                        # Y row never blocks the target X, and it is not a legal
                        # explicit binding.
                        continue
                    soft_exit("needs_input", "choice_owner_invalid",
                              message=f"{row_id}: 显式目录内的邮件编号不属于本教授当前执行范围。未写盘。",
                              email_id=row_id, professor_dir=canonical)
                attributed.setdefault(row_id, []).append(row)
                continue
            legacy_rows.append(row)
        # Legacy rows: the execution range of this pack is the only candidate
        # owner, so a row whose id sits inside it binds and joins this professor's
        # exact-one duplicate check; every other id is unrelated noise.
        for row in legacy_rows:
            row_id = row.get("email_id")
            if row_id in expected:
                attributed.setdefault(row_id, []).append(row)
        for email_id in sorted(expected):
            count = len(attributed.get(email_id, ()))
            if count != 1:
                fail("invalid_result_json",
                     f"choices email_id set does not match selected emails "
                     f"({email_id}: {count} attributable rows)")
        return {email_id: rows[0] for email_id, rows in attributed.items()}

    def stage5_list_input_rows(program_root: Path) -> list:
        """Issue #68 §2: every professor-local pack discovered independently.

        Read-only enumeration of ``教授研究/**/邮件输入.json``. A container that
        cannot be read, cannot prove one professor, or does not sit inside the
        professor directory it names fails as its own error row; it never blocks
        another valid professor and never reads verify/state/render/overview files
        or the legacy program-level pack.
        """
        research = program_root / "教授研究"
        inputs = []
        for pack_path in (sorted(research.rglob(EMAIL_PACK)) if research.is_dir() else []):
            if pack_path.parent == research:
                # The legacy program-level pack is Issue #67's migration input and
                # names no professor, so it is not a Stage-5 input row.
                continue
            row = {"professor": None, "professor_dir": str(pack_path.parent),
                   "email_pack": str(pack_path), "status": "error",
                   "reason_code": None}
            pack, error = read_json_file(pack_path)
            if error or not isinstance(pack, dict):
                row["reason_code"] = "missing_email_pack"
                inputs.append(row)
                continue
            if pack.get("schema") != STAGE4_LOCAL_SCHEMA or pack.get("kind") != EMAIL_PACK_KIND:
                row["reason_code"] = "invalid_email_pack"
                inputs.append(row)
                continue
            professor = pack.get("professor")
            professor_dir = pack.get("professor_dir")
            if not isinstance(professor, str) or not professor.strip() or \
                    not isinstance(professor_dir, str) or not professor_dir.strip():
                row["reason_code"] = "invalid_email_pack"
                inputs.append(row)
                continue
            row["professor"] = professor
            row["professor_dir"] = professor_dir
            contained = professor_dir_containment_error(
                Path(professor_dir), program_root) is None
            if contained:
                contained = Path(professor_dir).resolve() == pack_path.parent.resolve()
            if not contained:
                row["reason_code"] = "invalid_professor_dir"
            else:
                row["status"] = "ok"
            inputs.append(row)
        return inputs

    def cmd_stage5_list_inputs(args) -> None:
        """Read-only Stage-5 input discovery for a standalone Stage-5 call.

        Returns one row per professor-local pack with ``professor``,
        ``professor_dir``, ``email_pack``, ``status`` and ``reason_code``. No
        managed state is consulted; a bad container only fails its own row.
        ``--professor`` keeps only the rows whose top-level name matches it
        exactly, and a name with no such row returns ``needs_input`` instead of
        guessing. Discovery only finds packs: it never writes a file and never
        produces data one owner would share with another (plan r12 §3.7).
        """
        inputs = stage5_list_input_rows(Path(args.program_root))
        wanted = getattr(args, "professor", None)
        if wanted:
            named = [row for row in inputs if row["professor"] == wanted]
            if not named:
                soft_exit("needs_input", "professor_not_found", professor=wanted)
            inputs = named
        emit({"status": "ok", "inputs": inputs})

    def stage5_partition_pack_spec(program_root: Path, pack_path: str,
                                   email_id: str | None) -> dict:
        """Resolve one ``--owner`` pack into a partition spec or its own failure.

        The partition consumes packs the caller already selected from Stage-4
        success results or read-only discovery rows. A pack that cannot prove one
        professor stays that owner's own input-resolution failure with the
        runner's verdict shape; it never blocks another owner (plan r12 §3.2).
        """
        path = Path(pack_path)
        spec = {"pack_path": pack_path, "email_id": email_id, "professor": None,
                "owner_dir": None, "ids": None, "failure": None}

        def owner_failure(status, reason_code, message):
            spec["failure"] = {"status": status, "reason_code": reason_code,
                               "email_pack": pack_path, "message": message}
            return spec

        pack, error = read_json_file(path)
        if error:
            return owner_failure(
                "needs_refresh", "missing_email_pack",
                "缺该教授的 邮件输入.json：先跑阶段 4（professor-contact-selection）编译。")
        if not isinstance(pack, dict) or \
                pack.get("schema") != STAGE4_LOCAL_SCHEMA or pack.get("kind") != EMAIL_PACK_KIND:
            return owner_failure(
                "error", "invalid_email_pack",
                f"email pack must be the professor-local schema {STAGE4_LOCAL_SCHEMA} "
                f"{EMAIL_PACK} written by stage4-finalize")
        professor = pack.get("professor")
        professor_dir = pack.get("professor_dir")
        if not isinstance(professor, str) or not professor.strip() or \
                not isinstance(professor_dir, str) or not professor_dir.strip():
            return owner_failure(
                "error", "invalid_email_pack",
                "email pack does not prove a single professor owner")
        allowed = (program_root / "教授研究").resolve()
        canonical = Path(professor_dir).resolve()
        try:
            canonical.relative_to(allowed)
        except ValueError:
            return owner_failure(
                "error", "invalid_professor_dir",
                "professor_dir must be inside program_root/教授研究")
        emails = pack.get("emails")
        if not isinstance(emails, list):
            return owner_failure("error", "invalid_email_pack",
                                 "email pack has no emails list")
        ids = [email.get("email_id") for email in emails
               if isinstance(email, dict) and isinstance(email.get("email_id"), str)]
        spec["professor"] = professor
        spec["owner_dir"] = str(canonical)
        spec["ids"] = ids
        spec["range"] = {email_id} if email_id else set(ids)
        return spec

    def cmd_stage5_partition_choices(args) -> None:
        """Root-side deterministic ``choices`` partition (plan r12 §3.3).

        One user request may carry A+B's raw ``choices``, but the raw
        multi-professor object is never delegated to any professor owner. This
        entry partitions it exactly once by the frozen identity ``(canonical
        professor_dir, email_id)`` and answers one self-contained per-owner
        bundle: each holds only that professor's ``professor_dir``, ``email_pack``
        path, targeted ``email_id`` if any, and its own ``choices`` row subset.
        Explicit ``professor_dir`` rows enter their named owner only; a targeted
        owner excludes its own unselected ids first; a full-professor batch id
        error stays that owner's ``needs_input`` ``choice_owner_invalid``. A
        legacy row without a directory computes its candidates from this run's
        selected packs alone: zero candidates is an unrelated row (dropped), one
        candidate binds that owner, and several candidates stay at root as the
        affected owners' ``needs_input`` ``choice_owner_ambiguous`` — the row is
        broadcast to no one, and one owner's partition failure never blocks
        another owner's legal bundle. Business validation (duplicate, missing,
        fields, recipient) is not copied here; each owner's deterministic Stage-5
        path keeps running it on its own bundle.
        """
        program_root = Path(args.program_root)
        raw_owners = getattr(args, "owner", None)
        if not raw_owners:
            fail("invalid_params",
                 "stage5-partition-choices requires at least one "
                 "--owner <email_pack> [email_id]")
        specs = []
        for owner in raw_owners:
            if len(owner) > 2:
                fail("invalid_params",
                     "--owner accepts at most <email_pack> <email_id>")
            specs.append(stage5_partition_pack_spec(
                program_root, owner[0], owner[1] if len(owner) > 1 else None))
        seen_dirs: dict = {}
        for spec in specs:
            if spec["owner_dir"] is None:
                continue
            if spec["owner_dir"] in seen_dirs:
                fail("invalid_params",
                     "--owner names the same professor_dir more than once",
                     professor_dir=spec["owner_dir"])
            seen_dirs[spec["owner_dir"]] = spec
        rows = stage5_choices_rows(Path(args.choices))
        by_dir = {spec["owner_dir"]: spec for spec in specs if spec["owner_dir"]}
        attributed: dict = {dir_: {} for dir_ in by_dir}
        explicit_satisfied: dict = {}
        invalid_ids: dict = {}
        ambiguous_ids: dict = {dir_: set() for dir_ in by_dir}
        legacy_rows = []
        ranges = {dir_: spec["range"] for dir_, spec in by_dir.items()}
        for row in rows:
            row_id = row.get("email_id")
            raw_dir = row.get("professor_dir")
            if "professor_dir" in row:
                if not isinstance(raw_dir, str) or not raw_dir.strip():
                    # An invalid explicit directory is never a legacy binding.
                    continue
                canonical = str(Path(raw_dir).resolve())
                spec = by_dir.get(canonical)
                if spec is None:
                    # The row leaves with its professor; nobody in this run owns
                    # it, so no bundle ever carries it.
                    continue
                try:
                    in_range = row_id in spec["range"]
                except TypeError:
                    in_range = False
                if in_range:
                    attributed[canonical].setdefault(row_id, []).append(row)
                    explicit_satisfied.setdefault(row_id, set()).add(canonical)
                elif spec["email_id"]:
                    # R68-2: a targeted owner's unselected ids stay noise.
                    continue
                else:
                    # R68-3: the professor's own batch error id fails only that
                    # owner's partition, never another owner's bundle.
                    invalid_ids.setdefault(canonical, row_id)
                continue
            legacy_rows.append(row)
        # Resolve legacy rows only after every legal explicit binding is known:
        # input order cannot change ownership or turn a claimed id ambiguous.
        for row in legacy_rows:
            row_id = row.get("email_id")
            try:
                candidates = sorted(dir_ for dir_, rng in ranges.items()
                                    if row_id in rng)
            except TypeError:
                candidates = []
            if not candidates:
                continue  # unrelated row: dropped, changes no verdict
            if len(candidates) == 1:
                bound = candidates[0]
            else:
                # Only a multi-candidate row may exclude owners a legal explicit
                # row already satisfied; an undecided collision stays at root.
                satisfied = explicit_satisfied.get(row_id) or set()
                remaining = [dir_ for dir_ in candidates if dir_ not in satisfied]
                if not remaining:
                    continue
                if len(remaining) > 1:
                    for dir_ in remaining:
                        ambiguous_ids[dir_].add(row_id)
                    continue
                bound = remaining[0]
            attributed[bound].setdefault(row_id, []).append(row)
        owners = []
        for spec in specs:
            email_id = spec["email_id"]
            base = {"professor": spec["professor"],
                    "professor_dir": spec["owner_dir"],
                    "email_pack": spec["pack_path"],
                    "email_id": email_id}
            if spec["failure"] is not None:
                owners.append({**base, "partition": spec["failure"]})
                continue
            dir_ = spec["owner_dir"]
            if ambiguous_ids[dir_]:
                owners.append({**base, "partition": {
                    "status": "needs_input", "reason_code": "choice_owner_ambiguous",
                    "email_ids": sorted(ambiguous_ids[dir_]),
                    "message": "无目录旧格式 choices 行在多个已选教授范围内命中同一 email_id："
                               "请为每行显式补充 professor_dir 后重跑。未写盘。"}})
                continue
            if dir_ in invalid_ids:
                owners.append({**base, "partition": {
                    "status": "needs_input", "reason_code": "choice_owner_invalid",
                    "email_id": invalid_ids[dir_],
                    "message": "显式目录内的邮件编号不属于本教授当前执行范围。未写盘。"}})
                continue
            ordered: list = []
            for pack_email_id in spec["ids"]:
                if email_id and pack_email_id != email_id:
                    continue
                ordered.extend(attributed[dir_].get(pack_email_id, []))
            owners.append({**base, "partition": {"status": "ok"},
                           "choices_rows": ordered})
        payload = {"status": "ok", "choices": str(Path(args.choices)),
                   "owners": owners}
        out_path = getattr(args, "out", None)
        if out_path:
            # A transport representation for this request only: the caller hands
            # each owner its own bundle and cleans the file up with the request.
            Path(out_path).write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                encoding="utf-8")
        emit(payload)

    return types.SimpleNamespace(
                stage5_output_peers=stage5_output_peers,
                stage5_output_paths=stage5_output_paths,
                stage5_output_id=stage5_output_id,
                select_stage5_email=select_stage5_email,
                stage5_mode=stage5_mode,
                stage5_pack_owner=stage5_pack_owner,
                stage5_local_pack=stage5_local_pack,
                stage5_choices_rows=stage5_choices_rows,
                stage5_choices_by_id=stage5_choices_by_id,
                stage5_list_input_rows=stage5_list_input_rows,
                cmd_stage5_list_inputs=cmd_stage5_list_inputs,
                stage5_partition_pack_spec=stage5_partition_pack_spec,
                cmd_stage5_partition_choices=cmd_stage5_partition_choices,
    )
