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
import hashlib
import json
import os
import re
import types
import unicodedata





def build(*, atomic_write,
          atomic_json,
          fail,
          MANAGED_BY,
          DIRECTION_IDENTITY_VERSION,
          PROJECTIONS_FILE,
          VERIFY_TIMESTAMP_FORMAT):
    def now_utc() -> str:
        return datetime.now(timezone.utc).strftime(VERIFY_TIMESTAMP_FORMAT)

    def sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def sha256_text(text: str) -> str:
        return sha256_bytes(text.encode("utf-8"))

    def sha256_obj(payload: Any) -> str:
        return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))

    def normalized_quote(value: str) -> str:
        return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip()

    def quote_id(value: str) -> str:
        return sha256_text(normalized_quote(value))

    def load_json(path: Path) -> Any:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def read_json_file(path: Path) -> tuple[Any, str | None]:
        try:
            return load_json(path), None
        except FileNotFoundError:
            return None, "not_found"
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            return None, f"invalid: {exc}"

    def professor_dir_containment_error(professor_dir: Path, program_root: Path) -> str | None:
        """Return `invalid_professor_dir` when a professor dir leaves the program."""
        try:
            allowed = (program_root / "教授研究").resolve()
            actual = Path(professor_dir).resolve()
            actual.relative_to(allowed)
        except (OSError, ValueError):
            return "invalid_professor_dir"
        return None

    def require_professor_dir_under_program(professor_dir: Path, program_root: Path) -> None:
        """Prevent workflow state from being written outside the selected program."""
        if professor_dir_containment_error(professor_dir, program_root) is None:
            return
        fail("invalid_professor_dir", "professor_dir must be inside program_root/教授研究",
             professor_dir=str(Path(professor_dir).resolve()),
             allowed_root=str((program_root / "教授研究").resolve()))

    def truncate(text: str | None, limit: int) -> str:
        text = text or ""
        return text if len(text) <= limit else text[:limit] + "…"

    def text_tokens(text: str) -> set:
        tokens = set()
        for word in re.findall(r"[A-Za-z0-9]+", text or ""):
            if len(word) >= 3:
                tokens.add(word.lower())
        for run in re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]+", text or ""):
            for index in range(len(run) - 1):
                tokens.add(run[index:index + 2])
        return tokens

    def title_tokens(title: str) -> set:
        return text_tokens(title)

    def rel_path(target: Path, base: Path) -> str:
        try:
            return os.path.relpath(str(Path(target).resolve()), str(Path(base).resolve()))
        except ValueError:
            return str(target)

    def filename_component(value: Any) -> str:
        raw = unicodedata.normalize("NFKC", str(value or ""))
        cleaned = re.sub(r"[^\w.-]+", "_", raw, flags=re.UNICODE).strip("._")
        return cleaned[:80] or sha256_text(raw)[:12]

    def safe_result_file(kind: str, identity: str) -> str:
        """Deterministic result filename that never embeds an arbitrary machine ID raw."""
        return f"{kind}-{filename_component(identity)}-{sha256_text(identity)[:8]}.json"

    def direction_machine_id(direction: dict) -> str:
        """Canonical direction identity (issue #8 direction-id-v1).

        v2 pack directions carry `direction_id` directly. Legacy v1 packs are
        normalized in memory (see normalize_input_pack) using the exact 1:1
        machine relations the pack itself records — the authoritative resolved id
        when present, else the provisional collection_key. Display names, array
        positions and Zotero collection NAMES are never consulted.
        """
        did = direction.get("direction_id")
        if isinstance(did, str) and did.strip():
            return did.strip()
        rd = direction.get("resolved_direction")
        if isinstance(rd, dict):
            rid = rd.get("resolved_direction_id")
            if isinstance(rid, str) and rid.strip():
                return rid.strip()
        ckey = direction.get("collection_key")
        if isinstance(ckey, str) and ckey.strip():
            return ckey.strip()
        fail("invalid_input_pack", "pack direction has no machine direction identity")

    def facts_direction_id(direction: dict) -> str:
        """Direction identity while reading Stage-2 facts (pre-pack).

        v2 facts carry the selected `direction_id` from 套磁目标.json unchanged.
        Legacy facts without it map collection_key 1:1 — the explicit machine
        mapping §9 allows; nothing is inferred from names or array positions.
        """
        did = direction.get("direction_id")
        if isinstance(did, str) and did.strip():
            return did.strip()
        ckey = direction.get("collection_key")
        if isinstance(ckey, str) and ckey.strip():
            return ckey.strip()
        fail("invalid_facts", "facts direction needs direction_id (or legacy collection_key)")

    def cross_group_id(direction_ids: list[str]) -> str:
        """Stable cross-direction group identity: cross:<hash of sorted IDs>."""
        return "cross:" + sha256_text("\x1f".join(sorted(direction_ids)))[:12]

    def pack_paper_index(pack: dict) -> dict:
        papers = (pack or {}).get("papers")
        return papers if isinstance(papers, dict) else {}

    def direction_papers(pack: dict, direction: dict) -> list[dict]:
        """Project the professor-level canonical paper records for one direction.

        The canonical record lives once in `pack["papers"][item_key]`; per-direction
        display flags (named_by_user, resolved addition provenance) are projected
        here and never stored per direction copy.
        """
        papers = pack_paper_index(pack)
        named = set(direction.get("named_keys") or [])
        added = set(direction.get("resolved_addition_keys") or [])
        out = []
        for key in direction.get("supporting_item_keys") or []:
            record = papers.get(key)
            if not isinstance(record, dict):
                continue
            out.append({**record, "named_by_user": key in named,
                        "resolved_addition": key in added})
        return out

    def paper_digest(paper: dict) -> str:
        analysis_file = paper.get("analysis_file")
        sidecar_file = paper.get("sidecar_file")
        facts_file = paper.get("facts_file")
        payload = {
            "item_key": paper.get("item_key"),
            "title": paper.get("title"),
            "year": paper.get("year"),
            "month": paper.get("month"),
            "authorship": paper.get("authorship"),
            "abstract_sha": sha256_text(paper.get("abstract") or "") if paper.get("abstract") else None,
            "has_pdf": bool(paper.get("has_pdf")),
            "analysis_sha": sha256_bytes(Path(analysis_file).read_bytes()) if analysis_file and Path(analysis_file).is_file() else None,
            "sidecar_sha": sha256_bytes(Path(sidecar_file).read_bytes()) if sidecar_file and Path(sidecar_file).is_file() else None,
            "facts_sha": sha256_bytes(Path(facts_file).read_bytes()) if facts_file and Path(facts_file).is_file() else None,
        }
        return sha256_obj(payload)

    def sidecar_sha(path: str | None) -> str | None:
        if path and Path(path).is_file():
            return sha256_bytes(Path(path).read_bytes())
        return None

    def gap_fingerprint(item: dict, sha: str | None) -> str:
        return sha256_obj({
            "quote": unicodedata.normalize("NFKC", item.get("quote") or "").strip(),
            "translation_zh": item.get("translation_zh"),
            "source": item.get("source"),
            "page": item.get("page"),
            "sidecar_sha": sha,
        })

    def candidate_fingerprint(candidates: list) -> str:
        return sha256_obj(sorted(candidates, key=lambda c: json.dumps(c, ensure_ascii=False, sort_keys=True)))

    def direction_relevant_keys(direction: dict) -> list:
        """The analysis reference scope of a facts direction.

        An explicitly empty `relevant_keys` list is a real (empty) licence and must
        stay empty; only a genuinely missing field falls back to the Stage-1
        member set for legacy inputs. A present-but-malformed value is rejected
        instead of being read as "missing".
        """
        if "relevant_keys" in direction:
            relevant = direction.get("relevant_keys")
            if not isinstance(relevant, list):
                fail("invalid_facts",
                     f"direction {facts_direction_id(direction)} has a malformed relevant_keys "
                     "value (must be a list); refusing to treat it as a missing legacy field")
            return list(relevant)
        return list(direction.get("member_keys") or [])

    def direction_provisional_member_keys(direction: dict) -> list | None:
        """The ORIGINAL formal members of a facts direction (R1 single source).

        `provisional_member_keys` is the explicit Stage-1 origin list. Legacy facts
        that predate the field carry the same Stage-1 membership in `member_keys`;
        that list is accepted ONLY as the whole original set — never merged with or
        topped up from the analysis reference scope (`relevant_keys`) or user
        `named_keys`, so a reference paper can never silently become a member.
        Returns None when neither source states the original membership; callers
        must fail before writing.
        """
        keys = direction.get("provisional_member_keys")
        if not isinstance(keys, list):
            keys = direction.get("member_keys")
        if not isinstance(keys, list):
            return None
        seen: set = set()
        out: list = []
        for key in keys:
            if isinstance(key, str) and key not in seen:
                seen.add(key)
                out.append(key)
        return out

    def pack_direction_relevant_keys(direction: dict) -> list:
        """The persisted analysis reference scope of a pack direction.

        A v3 pack always stores `relevant_keys` explicitly (an empty list is an
        empty `P` licence). A legacy pack without the field keeps its members as
        the minimal read-only scope; a present-but-malformed value is rejected
        because falling back to members would silently widen the citation licence.
        """
        if "relevant_keys" in direction:
            relevant = direction.get("relevant_keys")
            if not isinstance(relevant, list):
                fail("invalid_input_pack",
                     f"direction {direction_machine_id(direction)} has a malformed relevant_keys "
                     "value (must be a list); refusing to fall back to its members",
                     direction=direction_machine_id(direction))
            return list(relevant)
        return list(direction.get("supporting_item_keys") or [])

    def direction_candidate_keys(direction: dict) -> list:
        """The full per-direction candidate universe from the Stage 1 snapshot.

        Issue #7 requires every unique candidate paper to get one full
        paper-analysis pass and to be resolvable into/out of the authoritative
        direction from full-text evidence. Relevant keys are the post-relevance
        gap/narrative scope and must NOT bound the resolution evidence — otherwise
        a paper the abstract-level gate dropped can never earn its way back in.
        """
        members = direction.get("member_keys")
        if members:
            return list(members)
        return direction_relevant_keys(direction)

    def selected_candidate_union(ctx: "Stage2Context") -> list:
        """Every unique candidate paper across this professor's selected directions.

        Per-direction Stage-1 candidate sets may be disjoint, but issue #7's
        acceptance #2 lets a paper from another preview cluster be added to a
        selected direction when full text supports it. So the resolved-membership
        evidence universe (affinity scoring, resolve-job paper evidence, and the
        papers_to_add allow-list) is the professor-level union — while the
        relevant/cost scope that drives gap/narrative work stays per direction.
        """
        seen: set[str] = set()
        union: list = []
        for plan in ctx.direction_plans:
            for key in direction_candidate_keys(plan["direction"]):
                if key not in seen:
                    seen.add(key)
                    union.append(key)
        return union

    def direction_fingerprint(direction: dict, papers: dict, gap_ids: list, families: dict) -> str:
        """Model-relevant Stage-2 direction fingerprint, keyed by direction_id.

        Issue #8 §3.2: only evidence that can change Stage-3 meaning belongs here.
        collection_key and display names (name_ja/name_zh) are projection/display
        metadata — a projection-only rename or a display-only rename must never
        invalidate model work; downstream rendering handles those deterministically.
        """
        relevant = direction_relevant_keys(direction)
        return sha256_obj({
            "identity_version": DIRECTION_IDENTITY_VERSION,
            "direction_id": facts_direction_id(direction),
            "user_note_sha": sha256_text(direction.get("user_note") or ""),
            "member_keys": sorted(direction.get("member_keys") or []),
            "relevant_keys": sorted(relevant),
            "named_keys": sorted(direction.get("named_keys") or []),
            "credibility": direction.get("credibility"),
            "red_lines": direction.get("red_lines") or [],
            "paper_digests": {key: papers[key]["_digest"] for key in sorted(relevant) if key in papers},
            "gap_ids": sorted(set(gap_ids)),
            "version_families": families,
        })

    def render_frontmatter(state_fingerprint: str, body_sha: str) -> str:
        return (f"---\nmanaged_by: {MANAGED_BY}\n"
                f"state_fingerprint: {state_fingerprint}\n"
                f"render_sha256: {body_sha}\n---\n\n")

    def split_frontmatter(text: str) -> tuple[dict | None, str]:
        if not text.startswith("---\n"):
            return None, text
        end = text.find("\n---\n", 4)
        if end < 0:
            return None, text
        header = {}
        for line in text[4:end].splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                header[key.strip()] = value.strip()
        body_start = end + 5
        if text[body_start:body_start + 1] == "\n":
            body_start += 1
        return header, text[body_start:]

    def managed_snapshot(path: Path) -> dict:
        """Lossless byte view of one managed Markdown file (Stage-2 U1 r5).

        Reads the file once as bytes, splits the frontmatter at the exact byte
        separators the renderer writes, and keeps the original header/body bytes
        next to the strict UTF-8 text view. Universal-newline text reads and
        line-ending-dropping splitlines are never the proof of the original
        file; callers that compare, hash or rewrite the managed body must use
        this snapshot (plan stage2-u1-r5 §3.6).
        """
        try:
            raw = Path(path).read_bytes()
        except OSError as exc:
            return {"error": f"unreadable: {exc}"}
        if not raw.startswith(b"---\n"):
            return {"error": "missing_frontmatter"}
        end = raw.find(b"\n---\n", 4)
        if end < 0:
            return {"error": "unterminated_frontmatter"}
        header_text_bytes = raw[4:end]
        body_start = end + 5
        if raw[body_start:body_start + 1] == b"\n":
            body_start += 1
        if body_start > len(raw):
            return {"error": "invalid_body_boundary"}
        body_bytes = raw[body_start:]
        try:
            header_text = header_text_bytes.decode("utf-8")
            body_text = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return {"error": "invalid_utf8"}
        header = {}
        for line in header_text.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                header[key.strip()] = value.strip()
        header_bytes = raw[:body_start]
        return {
            "raw": raw,
            "header_bytes": header_bytes,
            "body_bytes": body_bytes,
            "header": header,
            "body": body_text,
            "body_sha256": sha256_bytes(body_bytes),
            "line_offset": header_bytes.count(b"\n"),
        }

    def split_frontmatter_bytes(data: bytes) -> tuple[dict | None, bytes]:
        """Split a managed file without decoding/de-newlining its body bytes.

        The renderer normally writes LF headers, but a legal accepted body may
        have CRLF line endings (and an older writer may have used CRLF for the
        header too). The body slice must preserve the exact on-disk bytes; only
        the header keys are decoded.
        """
        if data.startswith(b"---\r\n"):
            sep = b"\r\n"
            start = len(b"---\r\n")
        elif data.startswith(b"---\n"):
            sep = b"\n"
            start = len(b"---\n")
        else:
            return None, data
        marker = sep + b"---" + sep
        end = data.find(marker, start)
        if end < 0:
            return None, data
        header = {}
        try:
            for line in data[start:end].split(sep):
                if b":" not in line:
                    continue
                key, _, value = line.partition(b":")
                header[key.strip().decode("utf-8")] = value.strip().decode("utf-8")
        except UnicodeDecodeError:
            return None, data
        body_start = end + len(marker)
        if data[body_start:body_start + len(sep)] == sep:
            body_start += len(sep)
        return header, data[body_start:]

    def managed_conflict(path: Path, body: str, previous_sha: str | None,
                         decision: str | None) -> dict | None:
        body_sha = sha256_text(body)
        if path.is_file():
            try:
                raw = path.read_bytes()
            except OSError:
                header, existing_body = None, b""
            else:
                header, existing_body = split_frontmatter_bytes(raw)
            existing_sha = sha256_bytes(existing_body) if header is not None else None
            if existing_sha is None:
                # An unreadable, unterminated or non-UTF-8 managed file cannot
                # prove the accepted render; every write needs an explicit
                # decision instead of silently replacing it.
                if decision != "overwrite":
                    return {"written": False, "needs_decision": True,
                            "reason_code": "manual_markdown_changed",
                            "target": str(path),
                            "existing_sha256": None, "new_sha256": body_sha}
            elif existing_sha != body_sha and previous_sha and existing_sha != previous_sha:
                if decision != "overwrite":
                    return {"written": False, "needs_decision": True,
                            "reason_code": "manual_markdown_changed",
                            "target": str(path),
                            "existing_sha256": existing_sha, "new_sha256": body_sha}
        return None

    def managed_write(path: Path, body: str, state_fingerprint: str,
                      previous_sha: str | None, decision: str | None) -> dict:
        body_sha = sha256_text(body)
        conflict = managed_conflict(path, body, previous_sha, decision)
        if conflict:
            return conflict
        atomic_write(path, render_frontmatter(state_fingerprint, body_sha) + body)
        return {"written": True, "needs_decision": False, "sha256": body_sha}

    def managed_write_raw(path: Path, body: str, previous_sha: str | None,
                          decision: str | None) -> dict:
        body_sha = sha256_text(body)
        if path.is_file():
            existing_sha = sha256_bytes(path.read_bytes())
            if existing_sha != body_sha and previous_sha and existing_sha != previous_sha:
                if decision != "overwrite":
                    return {"written": False, "needs_decision": True,
                            "reason_code": "manual_markdown_changed", "target": str(path),
                            "existing_sha256": existing_sha, "new_sha256": body_sha}
        atomic_write(path, body)
        return {"written": True, "needs_decision": False, "sha256": body_sha}

    def projection_conflict(path: Path, body: str, projections: dict, key: str) -> dict | None:
        body_sha = sha256_text(body)
        previous = (projections or {}).get("render", {}).get(key, {}).get("sha256")
        if path.is_file():
            _, existing_body = split_frontmatter_bytes(path.read_bytes())
            existing_sha = sha256_bytes(existing_body)
            if existing_sha != body_sha and previous and existing_sha != previous:
                return {"written": False, "needs_decision": True,
                        "reason_code": "manual_markdown_changed", "target": str(path)}
        return None

    def projection_write(path: Path, body: str, projections: dict, key: str) -> dict:
        conflict = projection_conflict(path, body, projections, key)
        if conflict:
            return conflict
        body_sha = sha256_text(body)
        projection_fingerprint = sha256_obj({"projection": key, "body": body_sha})
        atomic_write(path, render_frontmatter(projection_fingerprint, body_sha) + body)
        return {"written": True, "needs_decision": False, "sha256": body_sha}

    def load_projections(program_root: Path) -> dict:
        data, error = read_json_file(program_root / "教授研究" / PROJECTIONS_FILE)
        if error or not isinstance(data, dict):
            return {"render": {}}
        data.setdefault("render", {})
        return data

    def save_projections(program_root: Path, projections: dict) -> None:
        atomic_json(program_root / "教授研究" / PROJECTIONS_FILE, projections)

    return types.SimpleNamespace(
                now_utc=now_utc,
                sha256_bytes=sha256_bytes,
                sha256_text=sha256_text,
                sha256_obj=sha256_obj,
                normalized_quote=normalized_quote,
                quote_id=quote_id,
                load_json=load_json,
                read_json_file=read_json_file,
                professor_dir_containment_error=professor_dir_containment_error,
                require_professor_dir_under_program=require_professor_dir_under_program,
                truncate=truncate,
                text_tokens=text_tokens,
                title_tokens=title_tokens,
                rel_path=rel_path,
                filename_component=filename_component,
                safe_result_file=safe_result_file,
                direction_machine_id=direction_machine_id,
                facts_direction_id=facts_direction_id,
                cross_group_id=cross_group_id,
                pack_paper_index=pack_paper_index,
                direction_papers=direction_papers,
                paper_digest=paper_digest,
                sidecar_sha=sidecar_sha,
                gap_fingerprint=gap_fingerprint,
                candidate_fingerprint=candidate_fingerprint,
                direction_relevant_keys=direction_relevant_keys,
                direction_provisional_member_keys=direction_provisional_member_keys,
                pack_direction_relevant_keys=pack_direction_relevant_keys,
                direction_candidate_keys=direction_candidate_keys,
                selected_candidate_union=selected_candidate_union,
                direction_fingerprint=direction_fingerprint,
                render_frontmatter=render_frontmatter,
                split_frontmatter=split_frontmatter,
                managed_snapshot=managed_snapshot,
                split_frontmatter_bytes=split_frontmatter_bytes,
                managed_conflict=managed_conflict,
                managed_write=managed_write,
                managed_write_raw=managed_write_raw,
                projection_conflict=projection_conflict,
                projection_write=projection_write,
                load_projections=load_projections,
                save_projections=save_projections,
    )
