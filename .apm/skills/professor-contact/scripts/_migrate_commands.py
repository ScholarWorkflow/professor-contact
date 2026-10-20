#!/usr/bin/env python3
"""Migration helper module for ``contact_state.py``.

The runner loads this helper by path next to itself and calls :func:`build`
once with its own helper functions and shared constants. The factory binds
those names in an enclosing scope, so the functions below keep the exact
bodies they had inside the runner (only their indentation changed). The
module never imports the runner, never adds itself to ``sys.path`` and
never builds a second failure channel.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import re
import types





def build(*, atomic_json,
          emit,
          fail,
          SCHEMA,
          MANAGED_BY,
          INPUT_PACK,
          CANDIDATES_MD,
          GAP_STATUSES,
          now_utc,
          sha256_bytes,
          sha256_obj,
          read_json_file,
          load_sidecar,
          read_legacy_index,
          classify_direction,
          apply_ready_entry):
    def migration_source_fingerprint(professor_dir: Path) -> str:
        paths = {
            professor_dir / "论文分析" / "_index.json",
            professor_dir / "papers.json",
            professor_dir / CANDIDATES_MD,
        }
        index, error = read_legacy_index(professor_dir / "论文分析" / "_index.json")
        if error is None and isinstance(index, dict):
            for paper in (index.get("papers") or {}).values():
                if not isinstance(paper, dict):
                    continue
                for field in ("file", "future_work_sidecar"):
                    value = paper.get(field)
                    if value:
                        paths.add(Path(value))
        records = []
        for path in sorted(paths, key=lambda item: str(item)):
            try:
                records.append({"path": str(path), "sha256": sha256_bytes(path.read_bytes())})
            except (OSError, ValueError):
                records.append({"path": str(path), "sha256": None})
        return sha256_obj(records)

    def migrate_entry_for_professor(professor_dir: Path, program_root: Path) -> dict | None:
        index_path = professor_dir / "论文分析" / "_index.json"
        candidates_md = professor_dir / CANDIDATES_MD
        if not index_path.is_file() and not candidates_md.is_file():
            return None
        entry = {
            "professor_dir": str(professor_dir),
            "professor": professor_dir.name,
            "category": professor_dir.parent.name,
            "source_fingerprint": migration_source_fingerprint(professor_dir),
            "already_migrated": (professor_dir / INPUT_PACK).is_file(),
            "schema2": False, "sidecar_ok": False, "candidates_meta": False,
            "metadata_ok": False, "gap_ids_exact": False,
            "gap_papers": 0, "valid_sidecars": 0,
        }
        if index_path.is_file():
            index, error = read_legacy_index(index_path)
            if error:
                entry["classification"] = "blocked"
                entry["reasons"] = [f"_index.json 不可读：{error}"]
                entry["stage2"] = entry["stage3"] = "blocked"
                return entry
            entry["schema2"] = index.get("schema") == 2
            papers = index.get("papers")
            if isinstance(papers, dict):
                gap_papers = 0
                valid = 0
                exact = True
                valid_gap_pairs = set()
                for key, paper in papers.items():
                    if not isinstance(paper, dict):
                        continue
                    has_gaps = bool(paper.get("gaps")) or bool(paper.get("gap"))
                    if not has_gaps:
                        continue
                    gap_papers += 1
                    sidecar = paper.get("future_work_sidecar")
                    if sidecar:
                        items, legacy, err = load_sidecar(sidecar, paper.get("file"))
                        index_gaps = {g.get("gap_id") for g in (paper.get("gaps") or [])
                                      if isinstance(g, dict) and isinstance(g.get("gap_id"), str)}
                        sidecar_gaps = {item.get("gap_id") for item in items}
                        gap_rows = paper.get("gaps") or []
                        statuses_valid = isinstance(gap_rows, list) and all(
                            isinstance(g, dict) and g.get("gap_id") in index_gaps and
                            g.get("status") in GAP_STATUSES and
                            isinstance(g.get("evidence"), str) and g.get("evidence").strip()
                            for g in gap_rows)
                        if err is None and index_gaps and sidecar_gaps == index_gaps and statuses_valid:
                            valid += 1
                            valid_gap_pairs.update((key, gap_id) for gap_id in index_gaps)
                        else:
                            exact = False
                    else:
                        exact = False
                entry["gap_papers"] = gap_papers
                entry["valid_sidecars"] = valid
                entry["sidecar_ok"] = gap_papers == 0 or valid == gap_papers
                entry["gap_ids_exact"] = gap_papers == 0 or exact
                papers_json_path = professor_dir / "papers.json"
                papers_meta, metadata_error = read_json_file(papers_json_path)
                metadata_by_key = {}
                if metadata_error is None and isinstance(papers_meta, dict):
                    metadata_by_key = {p.get("item_key"): p for p in papers_meta.get("papers", [])
                                       if isinstance(p, dict)}
                metadata_ok = True
                for key, paper in papers.items():
                    if not isinstance(paper, dict):
                        metadata_ok = False
                        continue
                    meta = metadata_by_key.get(key) or paper
                    title = meta.get("title")
                    year = meta.get("year")
                    authorship = meta.get("authorship")
                    if not isinstance(title, str) or not title.strip() or not isinstance(year, int) or \
                            authorship not in ("first", "corresponding", "solo", "middle", "pending"):
                        metadata_ok = False
                entry["metadata_ok"] = metadata_ok
                if not metadata_ok:
                    entry.setdefault("reasons", []).append("论文标题/年份/署名元数据不足")
                if not entry["gap_ids_exact"]:
                    entry.setdefault("reasons", []).append("sidecar gap ID 与 schema 2 gaps[] 不精确相等")
        if candidates_md.is_file():
            text = candidates_md.read_text(encoding="utf-8", errors="replace")
            metas = re.findall(r"candidate_meta:\s*(\{.*\})", text)
            parsed_ok = 0
            parsed_total = 0
            known_pairs = set()
            if isinstance(index_path, Path) and index_path.is_file():
                index_data, _ = read_legacy_index(index_path)
                for key, paper in (index_data or {}).get("papers", {}).items():
                    for gap in (paper or {}).get("gaps", []):
                        if isinstance(gap, dict) and gap.get("gap_id"):
                            known_pairs.add((key, gap["gap_id"]))
            for meta in metas:
                try:
                    payload = json.loads(meta)
                    parsed_total += 1
                    pairs = payload.get("gap_ids") or []
                    pairs_ok = all(isinstance(pair, dict) and
                                   (pair.get("item_key"), pair.get("gap_id")) in known_pairs
                                   for pair in pairs)
                    if payload.get("id") and not payload.get("compatibility_fallback") and pairs_ok:
                        parsed_ok += 1
                except json.JSONDecodeError:
                    continue
            entry["candidates_meta"] = parsed_ok > 0
            if parsed_total and parsed_ok != parsed_total:
                entry.setdefault("reasons", []).append("候选 candidate_meta 的 gap ID 无法精确恢复")
        if entry["schema2"] or entry["candidates_meta"] or entry["gap_papers"]:
            entry.update(classify_direction(entry))
            if entry["classification"] == "ready" and not entry["metadata_ok"]:
                entry["classification"] = "blocked"
                entry["stage2"] = entry["stage3"] = "blocked"
                entry.setdefault("reasons", []).append("必要论文元数据不足，不能标记 ready")
            elif entry["classification"] == "ready" and not entry["gap_ids_exact"]:
                entry["classification"] = "blocked"
                entry["stage2"] = entry["stage3"] = "blocked"
                entry.setdefault("reasons", []).append("gap ID 不匹配，不能标记 ready")
        else:
            entry.update({"classification": "needs_stage2", "stage2": "needs_stage2",
                          "stage3": "needs_stage3",
                          "reasons": ["index 无 gap 数据或候选无机器元数据，按需重跑阶段 2"]})
        return entry

    def cmd_migrate_plan(args) -> None:
        program_root = Path(args.program_root)
        base = program_root / "教授研究"
        if not base.is_dir():
            fail("invalid_params", f"no 教授研究 under {program_root}")
        entries = []
        seen = set()
        candidate_dirs = []
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            if (child / "papers.json").is_file() or (child / "论文分析").is_dir():
                candidate_dirs.append(child)
            for professor_dir in sorted(child.iterdir()):
                if professor_dir.is_dir() and ((professor_dir / "papers.json").is_file() or
                                               (professor_dir / "论文分析").is_dir()):
                    candidate_dirs.append(professor_dir)
        for professor_dir in candidate_dirs:
            resolved = str(professor_dir.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            entry = migrate_entry_for_professor(professor_dir, program_root)
            if entry:
                entries.append(entry)
        ready = [e for e in entries if e.get("classification") == "ready" and not e.get("already_migrated")]
        plan = {
            "status": "ok",
            "schema": SCHEMA, "managed_by": MANAGED_BY, "generated_at": now_utc(),
            "program_root": str(program_root),
            "directions": entries,
            "ready_count": len(ready),
            "note": "ready=纯脚本可迁移；needs_stage2=缺有效 sidecar/精确 ID；needs_stage3=输入包可迁移但候选无机器元数据；blocked=文件损坏。--apply 只处理 ready 且未迁移的条目，绝不隐式启动阶段 2/3。"}
        if args.out:
            atomic_json(Path(args.out), plan)
        emit(plan)

    def cmd_migrate_apply(args) -> None:
        plan, error = read_json_file(Path(args.apply))
        if error or not isinstance(plan, dict):
            fail("invalid_params", f"plan unreadable: {args.apply}")
        plan_root_value = plan.get("program_root")
        if not isinstance(plan_root_value, str) or not plan_root_value:
            fail("invalid_params", "migration plan has no program_root")
        plan_root = Path(plan_root_value)
        program_root = Path(args.program_root) if args.program_root else plan_root
        try:
            if program_root.resolve() != plan_root.resolve():
                fail("invalid_params", "program_root does not match migration plan")
        except OSError:
            fail("invalid_params", "program_root is not resolvable")
        entries = plan.get("directions")
        if not isinstance(entries, list):
            fail("invalid_params", "migration plan directions must be a list")
        applied, skipped = [], []
        for entry in entries:
            if not isinstance(entry, dict):
                fail("invalid_params", "migration plan direction must be an object")
            if entry.get("classification") != "ready":
                skipped.append({"professor": entry.get("professor"),
                                "reason": entry.get("classification")})
                continue
            if entry.get("already_migrated"):
                skipped.append({"professor": entry.get("professor"), "reason": "already_migrated"})
                continue
            target = Path(entry.get("professor_dir") or "")
            try:
                base = program_root.resolve() / "教授研究"
                if not target.is_absolute() or os.path.commonpath((str(base), str(target.resolve()))) != str(base):
                    skipped.append({"professor": entry.get("professor"),
                                    "reason": "professor_dir_outside_program_root"})
                    continue
            except (OSError, ValueError):
                skipped.append({"professor": entry.get("professor"), "reason": "invalid_professor_dir"})
                continue
            applied.append(apply_ready_entry(program_root, entry, plan))
        emit({"status": "ok", "applied": applied, "skipped": skipped})

    return types.SimpleNamespace(
                migration_source_fingerprint=migration_source_fingerprint,
                migrate_entry_for_professor=migrate_entry_for_professor,
                cmd_migrate_plan=cmd_migrate_plan,
                cmd_migrate_apply=cmd_migrate_apply,
    )
