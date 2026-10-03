"""Shared fixture preparation support for professor-contact tests.

This module owns reusable directory validation, file writing and digest
helpers. Each test run is expected to receive its own isolated writable
fixture directory from the caller.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable


class FixtureBuildError(RuntimeError):
    """A preparation refused an input or failed while building samples."""


def producer_root() -> Path:
    # tests/runtime/fixture_support.py -> parents[5] is the producer checkout.
    return Path(__file__).resolve().parents[5]


def is_producer_owned(path: Path) -> bool:
    producer = producer_root()
    return path == producer or path.is_relative_to(producer)


def resolved_outside_producer(path: Path, *, description: str) -> Path:
    resolved = Path(path).resolve()
    if is_producer_owned(resolved):
        raise FixtureBuildError(
            f"{description} must be outside producer checkout: {resolved}")
    return resolved


def check_mutually_independent(
    first: Path, second: Path, *, first_label: str, second_label: str
) -> None:
    first_resolved = Path(first).resolve()
    second_resolved = Path(second).resolve()
    if first_resolved == second_resolved:
        raise FixtureBuildError(
            f"{first_label} and {second_label} must be distinct: {first_resolved}")
    if (first_resolved.is_relative_to(second_resolved)
            or second_resolved.is_relative_to(first_resolved)):
        raise FixtureBuildError(
            f"{first_label} and {second_label} must be independent directories: "
            f"{first_resolved}, {second_resolved}")


def ensure_new_output(
    path: Path,
    *,
    reserved: Iterable[Path] = (),
    description: str = "manifest output",
) -> Path:
    """Resolve a new output path and reject protected or existing targets."""
    raw = Path(os.path.abspath(os.fspath(path)))
    resolved = Path(path).resolve()
    if is_producer_owned(resolved):
        raise FixtureBuildError(
            f"{description} must be outside producer checkout: {resolved}")
    if os.path.lexists(raw):
        raise FixtureBuildError(f"{description} already exists: {resolved}")
    for reserved_path in reserved:
        if resolved == Path(reserved_path).resolve():
            raise FixtureBuildError(
                f"{description} overlaps a reserved fixture path: {resolved}")
    return resolved


class PreparedRoot:
    """A prepared sample root and the identity recorded at preparation time.

    The held open descriptor keeps the prepared directory object alive for
    the identity check: a removed directory keeps ``st_nlink == 0`` while a
    handle to it is open, so a replacement at the same path is detected
    even when the kernel hands out the same inode number again.
    """

    def __init__(self, path: Path, created: bool, identity: tuple[int, int],
                 dir_fd: int):
        self.path = path
        self.created = created
        self._identity = identity
        self._dir_fd: int | None = dir_fd

    def owned(self) -> bool:
        """Whether the directory is still the one this run prepared."""
        if self._dir_fd is None:
            return False
        try:
            held = os.fstat(self._dir_fd)
            current = self.path.stat()
        except OSError:
            return False
        if held.st_nlink == 0:
            return False
        return (self.path.is_dir()
                and (held.st_ino, held.st_dev) == (current.st_ino, current.st_dev))

    def close(self) -> None:
        """Release the held directory descriptor; idempotent."""
        if self._dir_fd is None:
            return
        try:
            os.close(self._dir_fd)
        except OSError:
            pass
        self._dir_fd = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def prepare_root(path: Path, *, description: str = "fixture root") -> PreparedRoot:
    """Prepare an empty fixture directory without replacing existing content."""
    resolved = resolved_outside_producer(path, description=description)
    created = False
    if resolved.exists():
        if not resolved.is_dir():
            raise FixtureBuildError(f"{description} is not a directory: {resolved}")
        if any(resolved.iterdir()):
            raise FixtureBuildError(
                f"refusing to replace non-empty foreign directory: {resolved}")
    else:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        try:
            resolved.mkdir()
            created = True
        except FileExistsError:
            if not resolved.is_dir() or any(resolved.iterdir()):
                raise FixtureBuildError(
                    f"{description} changed during preparation: {resolved}") from None
    identity = resolved.stat()
    try:
        dir_fd = os.open(resolved, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError as exc:
        raise FixtureBuildError(
            f"could not hold the prepared directory open: {resolved}") from exc
    return PreparedRoot(resolved, created, (identity.st_ino, identity.st_dev), dir_fd)


def discard_created_root(prepared: PreparedRoot) -> None:
    """Remove a root created by this run only while its identity still matches."""
    if not prepared.created:
        raise FixtureBuildError(
            "refusing to discard a root that existed before this run: "
            f"{prepared.path}")
    if not prepared.owned():
        raise FixtureBuildError(
            "fixture root ownership changed before rollback; "
            f"refusing destructive cleanup: {prepared.path}")
    shutil.rmtree(prepared.path)
    prepared.close()


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=1) + "\n")


def write_json_exclusive(path: Path, value: Any) -> None:
    """Create the file exclusively; an existing path is never overwritten."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        handle = os.open(path, flags, 0o644)
    except FileExistsError:
        raise FixtureBuildError(
            f"output appeared during preparation; refusing to overwrite: {path}"
        ) from None
    except OSError as exc:
        raise FixtureBuildError(f"could not create output safely: {path}") from exc
    with os.fdopen(handle, "wb") as stream:
        stream.write(payload)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
