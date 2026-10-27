#!/usr/bin/env python3
"""Direction-scoped experience materials for ``contact_state.py``.

The runner loads this helper by path next to itself and binds it to its own
helpers (``fail``, ``read_json_file``, ``atomic_json``, ...). It never imports
the runner and never builds a second failure channel.

Ownership (plan ``direction-experience-materials`` EP1.2 §3.1-§3.3):

* each canonical professor directory owns one ``方向素材.json`` (schema 1):
  ``directions[<direction_id>]`` is a list of ``material_id``/``question``/
  ``answer`` entries; the answer is the user's own text and is never summarized;
* a missing file means "no materials yet"; an unreadable or foreign file is an
  input error for that professor and never becomes an empty library;
* one filesystem mutex per materials file serialises save, Stage-4 freeze and
  the Stage-5 freshness check / final write;
* the frozen email slice keeps exactly ``direction_id``/``material_id``/
  ``question``/``answer`` and each row gets the source id
  ``direction_material:<direction_id>:<material_id>``.
"""
from __future__ import annotations

import contextlib
import fcntl
from pathlib import Path
from typing import Any
import types

MATERIALS = "方向素材.json"
MATERIALS_SCHEMA = 1
SOURCE_PREFIX = "direction_material:"
LOCK_NAME = f".{MATERIALS}.lock"


def build(*, fail,
          emit,
          read_json_file,
          atomic_json,
          sha256_text,
          professor_dir_containment_error,
          load_input_pack,
          load_candidate_state,
          direction_machine_id,
          now_utc):
    def materials_path(professor_dir: Path) -> Path:
        return Path(professor_dir) / MATERIALS

    def _resolved(professor_dir: Any) -> str:
        return str(Path(professor_dir).resolve())

    def _empty_materials(professor_dir: Path) -> dict:
        return {"schema": MATERIALS_SCHEMA,
                "professor_dir": _resolved(professor_dir),
                "directions": {}}

    def _normalize_entry(entry: Any, context: str) -> dict:
        if not isinstance(entry, dict):
            fail("invalid_direction_materials",
                 f"{context}: material entry must be an object")
        material_id = entry.get("material_id")
        if not isinstance(material_id, str) or not material_id.strip():
            fail("invalid_direction_materials",
                 f"{context}: material entry has no stable material_id")
        answer = entry.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            fail("invalid_direction_materials",
                 f"{context}: material {material_id} has no user answer")
        question = entry.get("question")
        if question is None:
            question = ""
        if not isinstance(question, str):
            fail("invalid_direction_materials",
                 f"{context}: material {material_id} question must be a string")
        return {"material_id": material_id.strip(), "question": question,
                "answer": answer}

    def _normalize_bucket(bucket: Any, direction_id: str, context: str) -> list:
        if bucket is None:
            return []
        if isinstance(bucket, dict):
            bucket = list(bucket.values())
        if not isinstance(bucket, list):
            fail("invalid_direction_materials",
                 f"{context}: directions[{direction_id}] must be a list or mapping")
        rows = []
        seen = set()
        for index, entry in enumerate(bucket):
            row = _normalize_entry(
                entry, f"{context}: directions[{direction_id}][{index}]")
            if row["material_id"] in seen:
                fail("invalid_direction_materials",
                     f"{context}: duplicate material_id {row['material_id']} "
                     f"in direction {direction_id}")
            seen.add(row["material_id"])
            rows.append(row)
        return rows

    def load_materials(professor_dir: Path) -> dict:
        """Read one professor's materials; a missing file is an empty library.

        An existing but unreadable, malformed or foreign-owned file fails this
        professor's caller instead of being treated as "no materials": silently
        replacing a corrupt user answer file would look like a successful save.
        """
        path = materials_path(professor_dir)
        data, error = read_json_file(path)
        if error == "not_found":
            return _empty_materials(professor_dir)
        if error:
            fail("invalid_direction_materials",
                 f"方向素材无法读取（{path}）：{error}。该教授未写入任何文件。",
                 materials_file=str(path))
        if not isinstance(data, dict) or data.get("schema") != MATERIALS_SCHEMA:
            fail("invalid_direction_materials",
                 f"方向素材必须是 schema {MATERIALS_SCHEMA} 的对象：{path}。"
                 "该教授未写入任何文件。", materials_file=str(path))
        owner = data.get("professor_dir")
        if not isinstance(owner, str) or not owner.strip():
            fail("invalid_direction_materials",
                 f"方向素材缺少教授目录归属：{path}。该教授未写入任何文件。",
                 materials_file=str(path))
        if Path(owner).resolve() != Path(professor_dir).resolve():
            fail("invalid_direction_materials",
                 f"方向素材归属不符：{path} 记录的是 {owner}，"
                 f"当前教授目录是 {professor_dir}。该教授未写入任何文件。",
                 materials_file=str(path))
        raw_directions = data.get("directions")
        if raw_directions is None:
            raw_directions = {}
        if not isinstance(raw_directions, dict):
            fail("invalid_direction_materials",
                 f"方向素材的 directions 必须是对象：{path}。该教授未写入任何文件。",
                 materials_file=str(path))
        directions = {}
        for direction_id, bucket in raw_directions.items():
            if not isinstance(direction_id, str) or not direction_id.strip():
                fail("invalid_direction_materials",
                     f"方向素材包含空 direction_id：{path}。该教授未写入任何文件。",
                     materials_file=str(path))
            directions[direction_id.strip()] = _normalize_bucket(
                bucket, direction_id, str(path))
        return {"schema": MATERIALS_SCHEMA,
                "professor_dir": _resolved(professor_dir),
                "directions": directions}

    def frozen_rows(data: dict, direction_ids: list) -> list:
        """The deterministic Stage-4 slice for one email's direction scope.

        Order is sorted direction_id then the file's entry order, so a Stage-4
        recompile and a Stage-5 freshness check derive the identical rows from
        the same file bytes.
        """
        directions = (data or {}).get("directions") or {}
        rows = []
        for direction_id in sorted({str(value).strip() for value in direction_ids
                                    if str(value).strip()}):
            for entry in directions.get(direction_id) or []:
                rows.append({"direction_id": direction_id,
                             "material_id": entry["material_id"],
                             "question": entry.get("question") or "",
                             "answer": entry["answer"]})
        return rows

    def material_source(direction_id: str, material_id: str) -> str:
        return f"{SOURCE_PREFIX}{direction_id}:{material_id}"

    def lock_materials(professor_dir: Path):
        """Acquire the per-materials-file mutex; return the handle to unlock.

        ``方向素材.json`` is replaced atomically (new inode), so the lock lives
        on a sibling ``.方向素材.json.lock`` file rather than on the data file
        itself. The lock file is infrastructure, never user material or business
        state; holding this same mutex is what keeps a save from landing between
        a Stage-4 freeze / Stage-5 freshness check and its commit.
        """
        path = Path(professor_dir) / LOCK_NAME
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = open(path, "a+b")
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except OSError as exc:
            fail("invalid_direction_materials",
                 f"方向素材互斥文件无法打开（{path}）：{exc}")
        return handle

    def unlock_materials(handle) -> None:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    @contextlib.contextmanager
    def _mutex(professor_dir: Path):
        handle = lock_materials(professor_dir)
        try:
            yield handle
        finally:
            unlock_materials(handle)

    def direction_ids_in_scope(professor_dir: Path) -> set:
        """Canonical direction ids this professor may own materials for.

        The formal range comes from the accepted Stage-2 input pack (and, when
        that is unreadable, the Stage-3 candidate state). A direction that never
        belonged to this professor is refused rather than silently saved under
        a foreign identity; a direction that left the current candidate set but
        is still in the pack keeps its stored answers.
        """
        pack, _error = load_input_pack(professor_dir)
        ids = set()
        if isinstance(pack, dict):
            for direction in pack.get("directions") or []:
                if isinstance(direction, dict):
                    ids.add(direction_machine_id(direction))
        if not ids:
            state, _state_error = load_candidate_state(professor_dir, pack)
            for direction in (state or {}).get("directions") or []:
                if isinstance(direction, dict):
                    direction_id = direction.get("direction_id")
                    if isinstance(direction_id, str) and direction_id.strip():
                        ids.add(direction_id.strip())
        return ids

    def _new_material_id(data: dict, direction_id: str, question: str,
                         answer: str) -> str:
        existing = {entry["material_id"]
                    for entries in (data.get("directions") or {}).values()
                    for entry in entries}
        seed = f"{direction_id}\x1f{question}\x1f{answer}\x1f{now_utc()}"
        for attempt in range(1, 1000):
            material_id = "MAT" + sha256_text(f"{seed}\x1f{attempt}")[:10]
            if material_id not in existing:
                return material_id
        fail("invalid_direction_materials", "无法生成唯一的 material_id")

    def cmd_direction_materials_save(args) -> None:
        """Save one user answer for one canonical direction (EP1.2 §3.2).

        The answer is user input, not profile/Stage-3 state: this command only
        touches ``<professor_dir>/方向素材.json`` and never rewrites the input
        pack, candidate state or email pack.
        """
        program_root = Path(args.program_root)
        professor_dir = Path(args.professor_dir)
        containment = professor_dir_containment_error(professor_dir, program_root)
        if containment:
            fail(containment,
                 "教授目录必须位于 <program_root>/教授研究/ 内；本次零写入。",
                 professor_dir=str(professor_dir),
                 allowed_root=str((program_root / "教授研究").resolve()))
        if not professor_dir.is_dir():
            fail("invalid_professor_dir",
                 f"教授目录不存在：{professor_dir}；本次零写入。",
                 professor_dir=str(professor_dir))
        direction_id = str(args.direction_id or "").strip()
        if not direction_id:
            fail("invalid_params", "direction-materials-save requires --direction-id")
        answer = args.answer
        if not isinstance(answer, str) or not answer.strip():
            fail("invalid_params",
                 "direction-materials-save requires a non-empty --answer")
        question = args.question
        if question is None:
            question = ""
        if not isinstance(question, str):
            fail("invalid_params", "direction-materials-save --question must be a string")
        scope = direction_ids_in_scope(professor_dir)
        if direction_id not in scope:
            fail("unknown_direction",
                 f"方向 {direction_id} 不在该教授的正式方向范围内；"
                 "未写入任何素材。",
                 professor_dir=str(professor_dir), direction_id=direction_id)
        path = materials_path(professor_dir)
        requested_id = str(args.material_id or "").strip()
        with _mutex(professor_dir):
            exists = path.is_file()
            if args.expected_sha256:
                if not exists:
                    fail("materials_digest_changed",
                         f"方向素材文件不存在，无法匹配旧摘要：{path}；本次零写入。",
                         materials_file=str(path))
                current = sha256_text(path.read_text(encoding="utf-8"))
                if current != args.expected_sha256:
                    fail("materials_digest_changed",
                         f"方向素材已被修改（当前 {current}，期望 "
                         f"{args.expected_sha256}）：请重新读取后再提交。本次零写入。",
                         materials_file=str(path))
            data = load_materials(professor_dir)
            entries = data.setdefault("directions", {}).setdefault(direction_id, [])
            if args.expect_missing and entries:
                # The marker guards THIS direction, not the whole professor file:
                # a second direction legitimately lives in the same 方向素材.json.
                fail("materials_already_exists",
                     f"方向 {direction_id} 已有素材，不能按“首次保存”覆盖：{path}；"
                     "本次零写入。", materials_file=str(path),
                     direction_id=direction_id)
            if requested_id:
                row = next((entry for entry in entries
                            if entry["material_id"] == requested_id), None)
                if row is None:
                    fail("unknown_material_id",
                         f"方向 {direction_id} 中找不到素材 {requested_id}；"
                         "原有文件保持原字节。",
                         materials_file=str(path), direction_id=direction_id)
                row["answer"] = answer
                if question:
                    row["question"] = question
                material_id = requested_id
            else:
                material_id = _new_material_id(data, direction_id, question, answer)
                entries.append({"material_id": material_id,
                                "question": question, "answer": answer})
            data["schema"] = MATERIALS_SCHEMA
            data["professor_dir"] = _resolved(professor_dir)
            atomic_json(path, data)
        emit({"status": "ok", "material_id": material_id,
              "materials_file": str(path), "direction_id": direction_id})

    return types.SimpleNamespace(
        MATERIALS=MATERIALS,
        SOURCE_PREFIX=SOURCE_PREFIX,
        materials_path=materials_path,
        load_materials=load_materials,
        frozen_rows=frozen_rows,
        material_source=material_source,
        lock_materials=lock_materials,
        unlock_materials=unlock_materials,
        cmd_direction_materials_save=cmd_direction_materials_save,
    )
