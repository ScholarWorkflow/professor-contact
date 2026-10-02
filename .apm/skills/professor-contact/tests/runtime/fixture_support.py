"""Shared fixture preparation support for the professor-contact test entries.

This module owns the directory protection, exclusive claim, write and digest
primitives that the per-issue preparation entries reuse. It carries no
business data and no business assertions: callers pass explicit roots,
planned sample paths and manifest content.

Directory identity is the fully resolved path. For every sample root the
caller acquires an exclusive claim (an empty claim directory created
exclusively next to the root) before touching the directory, and keeps the
claim until its writes are done or its rollback has finished. A leftover
claim from an abnormal termination is refused and reported; it is never
taken over or deleted automatically.
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


_CLAIM_SUFFIX = ".fixture-claim"


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


def claim_path_for(root: Path) -> Path:
    """Exclusive-claim location for a resolved sample root (internal encoding)."""
    return root.parent / ("." + root.name + _CLAIM_SUFFIX)


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
    path: Path, *, reserved: Iterable[Path] = (), description: str = "manifest output"
) -> Path:
    """Resolve a not-yet-existing output path that overlaps no reserved path."""
    resolved = resolved_outside_producer(path, description=description)
    if resolved.exists():
        raise FixtureBuildError(f"{description} already exists: {resolved}")
    for reserved_path in reserved:
        if resolved == Path(reserved_path).resolve():
            raise FixtureBuildError(
                f"{description} overlaps a reserved fixture path: {resolved}")
    return resolved


class PreparedRoot:
    """An acquired sample root plus the exclusive claim held for it."""

    def __init__(self, path: Path, claim: Path, created: bool, identity: tuple[int, int]):
        self.path = path
        self.claim = claim
        self.created = created
        self._identity = identity
        self._claim_released = False

    def owned(self) -> bool:
        """Whether the directory is still the one this run prepared."""
        try:
            current = self.path.stat()
        except OSError:
            return False
        return self.path.is_dir() and (current.st_ino, current.st_dev) == self._identity

    def release(self) -> None:
        """Release this run's claim; never touches the root directory itself."""
        if self._claim_released:
            return
        self._claim_released = True
        try:
            self.claim.rmdir()
        except FileNotFoundError:
            pass


def prepare_root(path: Path, *, description: str = "fixture root") -> PreparedRoot:
    """Acquire one sample root exclusively and prepare it as an empty directory.

    An existing empty directory is kept as-is (its ownership is recorded);
    a missing directory is created. Non-empty, non-directory and producer
    owned targets are refused. The claim directory next to the root is held
    by the returned object and must be released by the caller.
    """
    resolved = resolved_outside_producer(path, description=description)
    if resolved.exists():
        if not resolved.is_dir():
            raise FixtureBuildError(f"{description} is not a directory: {resolved}")
        if any(resolved.iterdir()):
            raise FixtureBuildError(
                f"refusing to replace non-empty foreign directory: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    claim = claim_path_for(resolved)
    try:
        claim.mkdir()
    except FileExistsError:
        raise FixtureBuildError(
            "another preparation still holds the claim for this fixture root; "
            f"refusing to take over or delete it: {claim}") from None
    try:
        created = False
        if resolved.exists():
            if not resolved.is_dir() or any(resolved.iterdir()):
                raise FixtureBuildError(
                    f"{description} changed while the claim was held: {resolved}")
        else:
            try:
                resolved.mkdir()
                created = True
            except FileExistsError:
                if not resolved.is_dir() or any(resolved.iterdir()):
                    raise FixtureBuildError(
                        f"{description} changed while the claim was held: {resolved}"
                    ) from None
        identity = resolved.stat()
    except BaseException:
        _discard_claim(claim)
        raise
    return PreparedRoot(resolved, claim, created, (identity.st_ino, identity.st_dev))


def discard_created_root(prepared: PreparedRoot) -> None:
    """Remove a root that this run created, only while ownership still holds."""
    if not prepared.created:
        raise FixtureBuildError(
            "refusing to discard a root that existed before this run: "
            f"{prepared.path}")
    if not prepared.owned():
        raise FixtureBuildError(
            "fixture root ownership changed before rollback; "
            f"refusing destructive cleanup: {prepared.path}")
    shutil.rmtree(prepared.path)


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=1) + "\n")


def write_json_exclusive(path: Path, value: Any) -> None:
    """Create the file exclusively; an existing file is never overwritten."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    try:
        handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        raise FixtureBuildError(
            f"output appeared during preparation; refusing to overwrite: {path}"
        ) from None
    with os.fdopen(handle, "wb") as stream:
        stream.write(payload)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _discard_claim(claim: Path) -> None:
    try:
        claim.rmdir()
    except FileNotFoundError:
        pass
