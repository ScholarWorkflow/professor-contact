#!/usr/bin/env python3
"""Shared error channel and atomic-write helpers for ``contact_state.py``.

The runner loads this helper by path next to itself and aliases every name
below back into its own namespace, so the hundreds of existing call sites,
the ``except ProfessorBusinessFailure`` handlers and the tested module-level
API keep working unchanged.

Two invariants this module owns:

* the business channel is process-local state of *this module instance* — one
  runner instance per load, exactly like the pre-split module global;
* every file replacement goes through ``os.replace`` on a ``mkstemp`` staged
  file, which is what the issue67 fault injection targets.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_json(path: Path, payload: Any) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n")


def atomic_json_many(items: list[tuple[Path, Any]]) -> None:
    """Replace a small set of JSON files together, restoring old files on error."""
    staged = []
    records = []
    try:
        for path, payload in items:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((path, Path(temporary)))
        for path, temporary in staged:
            backup = None
            record = {"path": path, "temporary": temporary, "backup": backup,
                      "installed": False}
            records.append(record)
            if path.exists():
                fd, backup_name = tempfile.mkstemp(prefix=f".{path.name}.backup.", dir=path.parent)
                os.close(fd)
                backup = Path(backup_name)
                backup.unlink()
                record["backup"] = backup
                os.replace(path, backup)
            os.replace(temporary, path)
            record["installed"] = True
    except BaseException:
        for record in reversed(records):
            path = record["path"]
            try:
                if record["installed"] and path.exists():
                    path.unlink()
                backup = record["backup"]
                if backup and backup.exists():
                    os.replace(backup, path)
            except OSError:
                pass
        for path, temporary in staged:
            temporary.unlink(missing_ok=True)
        raise
    else:
        for record in records:
            backup = record["backup"]
            if backup and backup.exists():
                backup.unlink()
        for path, temporary in staged:
            temporary.unlink(missing_ok=True)


def staged_pair_commit(items: list[tuple[Path, str]]) -> None:
    """Replace a small set of text files as one local transaction (issue #66).

    All files are staged first, then installed in list order with one atomic
    replace each — the LAST install is the business commit point. An ordinary
    exception before the final install restores every previous file's old
    bytes (absence included), so no reader ever observes a state that the
    transaction later rolls back. Once the final install returned, the
    transaction is committed: remaining cleanup is best-effort and a cleanup
    error never rolls business files back or re-frames the result as
    uncommitted. Hard-crash durability between two replaces is out of scope.
    """
    staged: list[tuple[Path, Path]] = []
    installed: list[Path] = []
    backups: dict[Path, bytes | None] = {}
    try:
        for path, text in items:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((path, Path(temporary)))
        for path, temporary in staged:
            backups[path] = path.read_bytes() if path.exists() else None
            os.replace(temporary, path)
            installed.append(path)
    except BaseException:
        for path in reversed(installed):
            old = backups.get(path)
            try:
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    fd, temporary = tempfile.mkstemp(
                        prefix=f".{path.name}.restore.", dir=path.parent)
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(old)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary, path)
            except OSError:
                pass
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)
        raise
    else:
        for _, temporary in staged:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1))


class ProfessorBusinessFailure(Exception):
    """Expected professor-scoped business failure inside a Stage-4 transaction.

    It carries the machine payload a top-level `fail()`/`soft_exit()` would have
    printed, so the caller can turn it into that professor's result row while
    the single aggregate JSON stays the only output of the command."""

    def __init__(self, payload: dict) -> None:
        super().__init__(payload.get("reason_code") or "")
        self.payload = payload


_BUSINESS_CHANNEL: list = []


@contextlib.contextmanager
def professor_business_channel():
    """Route expected business exits into ProfessorBusinessFailure.

    A one-professor Stage-4 transaction must never print or end the process:
    only the outer command emits the single machine result."""
    _BUSINESS_CHANNEL.append(True)
    try:
        yield
    finally:
        _BUSINESS_CHANNEL.pop()


def _business_channel_open() -> bool:
    return bool(_BUSINESS_CHANNEL)


def fail(reason_code: str, message: str = "", **extra) -> None:
    payload = {"status": "error", "reason_code": reason_code, "message": message}
    payload.update(extra)
    if _business_channel_open():
        raise ProfessorBusinessFailure(payload)
    emit(payload)
    sys.exit(1)


def soft_exit(status: str, reason_code: str, **extra) -> None:
    payload = {"status": status, "reason_code": reason_code}
    payload.update(extra)
    if _business_channel_open():
        raise ProfessorBusinessFailure(payload)
    emit(payload)
    sys.exit(2)
