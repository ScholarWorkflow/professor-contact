"""Shared fixture preparation support for the professor-contact test entries.

This module owns the directory protection, exclusive claim, write and digest
primitives that the per-issue preparation entries reuse. It carries no
business data and no business assertions: callers pass explicit roots,
planned sample paths and manifest content.

Directory identity is the fully resolved path. For every sample root the
caller acquires an exclusive claim before touching the directory and keeps
it until its writes are done or its rollback has finished. The claim is an
occupation anchor symlink published beside the root with one atomic
exclusive creation and removed with one atomic unlink; it points at an
occupation directory in the temporary isolation space and carries an
internal marker, so an occupation is recognisable in exactly one complete
state from birth to removal. A legacy anchor keeps refusing takeover. A
claim-shaped name without an anchor is an ordinary legal path, and normal
content that happens to occupy the preferred anchor name only moves the
anchor to the next deterministic internal name.

Every parent creation and file write walks its components with atomic
mkdir/O_EXCL steps and re-refuses live claims, so an anchor another run
publishes after an earlier check can never be followed into. Conflict
detection for an acquisition runs over the whole deterministic anchor-name
sequence before any name is selected, so mutual exclusion of one real root
never depends on which business path occupies which internal name. The
occupation directory behind an anchor is sealed read-only once marked, so
the resolved occupation directory cannot be written through any other
spelling, and only the release path re-enables writing inside it. A
leftover anchor from an abnormal termination is refused and reported; it
is never taken over or deleted automatically.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Iterable


class FixtureBuildError(RuntimeError):
    """A preparation refused an input or failed while building samples."""


_CLAIM_SUFFIX = ".fixture-claim"
_HELD_MARKER = ".held"


def _is_claim_name(name: str) -> bool:
    return name.startswith(".") and name.endswith(_CLAIM_SUFFIX) and name != _CLAIM_SUFFIX


def _is_live_claim(path: Path) -> bool:
    """Whether path is an occupation anchor published by a preparation run.

    The anchor is a symlink created atomically (complete from birth) and
    removed atomically, and the occupation directory it points to carries
    the internal marker before publication and keeps it until the anchor is
    removed, so an anchor is recognisable in exactly its held state. The
    claim-name encoding never turns a symlink (or anything else) without
    the marker into an occupation: ordinary directories, files and user
    symlinks of the same shape are legal inputs.
    """
    if not path.is_symlink():
        return False
    try:
        return (path / _HELD_MARKER).exists()
    except OSError:
        return False


def _refuse_live_claim_path(*paths: Path, description: str) -> None:
    for path in paths:
        if _is_live_claim(path):
            raise FixtureBuildError(
                f"{description} collides with an existing claim directory: {path}")


def _refuse_live_claim_ancestors(*paths: Path) -> None:
    """Refuse live claim anchors on the ancestors of any given spelling."""
    seen = set()
    for path in paths:
        for ancestor in Path(path).parents:
            if ancestor in seen:
                continue
            seen.add(ancestor)
            if _is_live_claim(ancestor):
                raise FixtureBuildError(
                    "refusing to create or write inside an existing claim "
                    f"directory: {ancestor}")


def _mkdir_parents_claim_free(*paths: Path) -> None:
    """Create missing parent components one atomic mkdir at a time.

    os.mkdir never follows or replaces symlinks, so an occupation anchor
    another run publishes at a missing component after the pre-checks loses
    the creation race (EEXIST) or is recognised and refused; once a
    component exists as a real directory no later anchor can take its
    place. Existing non-claim symlinks stay ordinary user state.
    """
    seen = set()
    for path in paths:
        probe = Path(path)
        missing = []
        while True:
            if _is_live_claim(probe):
                raise FixtureBuildError(
                    "refusing to create or write inside an existing claim "
                    f"directory: {probe}")
            if probe.is_symlink():
                break
            if probe.exists():
                break
            missing.append(probe)
            parent = probe.parent
            if parent == probe:
                break
            probe = parent
        for component in reversed(missing):
            try:
                component.mkdir()
            except FileExistsError:
                pass
            except OSError as exc:
                raise FixtureBuildError(
                    "refusing to create inside a read-only occupation "
                    f"directory: {component}") from exc
            if _is_live_claim(component):
                raise FixtureBuildError(
                    "refusing to create or write inside an existing claim "
                    f"directory: {component}")


def producer_root() -> Path:
    # tests/runtime/fixture_support.py -> parents[5] is the producer checkout.
    return Path(__file__).resolve().parents[5]


def is_producer_owned(path: Path) -> bool:
    producer = producer_root()
    return path == producer or path.is_relative_to(producer)


def resolved_outside_producer(path: Path, *, description: str) -> Path:
    raw = Path(os.path.abspath(os.fspath(path)))
    resolved = Path(path).resolve()
    # The caller-supplied spelling is checked before resolving: an
    # occupation anchor is a symlink and would otherwise disappear from
    # the resolved path and be taken over as an ordinary directory.
    _refuse_live_claim_path(raw, resolved, description=description)
    _refuse_live_claim_ancestors(raw, resolved)
    if is_producer_owned(resolved):
        raise FixtureBuildError(
            f"{description} must be outside producer checkout: {resolved}")
    return resolved


def claim_path_for(root: Path) -> Path:
    """Preferred exclusive-claim location for a resolved sample root.

    Internal encoding. When ordinary content already occupies this name the
    acquisition falls back to the next deterministic internal name, so the
    encoding never becomes a restriction on user paths.
    """
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


def check_roots_separated_from_claims(
    roots: Iterable[Path], claims: Iterable[Path]
) -> None:
    """Refuse roots equal to, inside, or containing a published occupation.

    Only a live claim (an anchor symlink carrying the internal marker)
    blocks a root: an unused candidate claim name is an ordinary legal
    path for business use, because the acquisition either skips it or
    falls back to the next internal name. The claim is resolved before
    comparison so a root can never follow an anchor symlink into the
    occupation directory behind it.
    """
    claim_dirs = []
    for claim in claims:
        claim_path = Path(claim)
        if not _is_live_claim(claim_path):
            continue
        claim_dirs.append(claim_path.resolve())
    for root in roots:
        resolved_root = Path(root).resolve()
        for claim in claim_dirs:
            if (resolved_root == claim
                    or resolved_root.is_relative_to(claim)
                    or claim.is_relative_to(resolved_root)):
                raise FixtureBuildError(
                    "fixture root overlaps an exclusive claim directory of "
                    f"this run: {resolved_root} vs {claim}")


def ensure_new_output(
    path: Path,
    *,
    reserved: Iterable[Path] = (),
    claims: Iterable[Path] = (),
    description: str = "manifest output",
) -> Path:
    """Resolve a not-yet-existing output path that overlaps no reserved path.

    A live claim anchor on the output path itself or an ancestor is refused;
    sample roots may still contain the output as long as no sample file is
    hit. The caller must create the file through ``write_json_exclusive``,
    which re-runs the live-claim guard at creation time.
    """
    raw = Path(os.path.abspath(os.fspath(path)))
    resolved = Path(path).resolve()
    _refuse_live_claim_path(raw, resolved, description=description)
    _refuse_live_claim_ancestors(raw, resolved)
    if is_producer_owned(resolved):
        raise FixtureBuildError(
            f"{description} must be outside producer checkout: {resolved}")
    if resolved.exists():
        raise FixtureBuildError(f"{description} already exists: {resolved}")
    for reserved_path in reserved:
        if resolved == Path(reserved_path).resolve():
            raise FixtureBuildError(
                f"{description} overlaps a reserved fixture path: {resolved}")
    for claim_path in claims:
        claim = Path(claim_path)
        if not _is_live_claim(claim):
            # An unused candidate claim name stays an ordinary legal path
            # for business use; only a published occupation may block the
            # output path.
            continue
        claim_dir = claim.resolve()
        if resolved == claim_dir or resolved.is_relative_to(claim_dir):
            raise FixtureBuildError(
                f"{description} overlaps an exclusive claim directory: {resolved}")
    return resolved


class PreparedRoot:
    """An acquired sample root plus the exclusive claim held for it."""

    def __init__(self, path: Path, anchor: Path, held: Path, created: bool,
                 identity: tuple[int, int]):
        self.path = path
        self.anchor = anchor
        self.held = held
        self.created = created
        self.claim = anchor
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
        _discard_claim(self.anchor, self.held)


def _held_dir_for(resolved: Path) -> Path:
    """Occupation directory path in the shared temporary isolation space.

    The anchor symlink beside the sample root points here. Keeping the
    occupation directory out of the root's parent leaves exactly one
    visible entry per held root beside it.
    """
    token = f"{os.getpid():x}-{uuid.uuid4().hex[:8]}"
    return Path(tempfile.gettempdir()) / f"professor-contact-claim-{token}"


def _seal_held_dir(held: Path) -> None:
    """Make the occupation directory read-only for every caller.

    The resolved occupation directory must never be writable by another
    invocation through any spelling: after sealing, a foreign creation
    inside it fails with a kernel permission error instead of corrupting
    the held state. Only the release path re-enables writing.
    """
    try:
        held.chmod(0o500)
    except OSError as exc:
        raise FixtureBuildError(
            f"could not seal the occupation directory: {held}") from exc


def _remove_held_dir(held: Path) -> None:
    try:
        held.chmod(0o700)
    except OSError:
        pass
    try:
        (held / _HELD_MARKER).unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass
    try:
        held.rmdir()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _discard_claim(anchor: Path, held: Path) -> None:
    try:
        anchor.unlink()
    except FileNotFoundError:
        pass
    _remove_held_dir(held)


def _publish_anchor(resolved: Path, held: Path, business_paths: Iterable[Path],
                    description: str) -> Path:
    """Publish the occupation anchor for one resolved sample root.

    Conflict detection runs over the whole deterministic anchor-name
    sequence before any name is selected, so mutual exclusion of one real
    root never depends on which business path occupies which internal
    name: if any candidate carries another run's live occupation, this
    acquisition refuses instead of settling on a later free name. A name
    occupied by ordinary content is only skipped for selection, so the
    internal encoding never blocks an otherwise legal root. Candidates
    that would overlap or contain any of this run's business paths
    (roots, sample files, manifest output) are skipped as well: a
    fallback anchor must never occupy a legal business path.
    """
    business = [Path(b).resolve() for b in business_paths]

    def overlaps_business(candidate: Path) -> bool:
        return any(candidate == b or candidate.is_relative_to(b)
                   or b.is_relative_to(candidate) for b in business)

    def conflict(candidate: Path) -> FixtureBuildError:
        return FixtureBuildError(
            "another preparation still holds the claim for this fixture "
            f"root; refusing to take over or delete it: {candidate}")

    first = claim_path_for(resolved)
    candidates = [first]
    for attempt in range(63):
        candidates.append(first.with_name(first.name + f".r{attempt + 2}"))
    for candidate in candidates:
        if _is_live_claim(candidate):
            raise conflict(candidate)
    for candidate in candidates:
        if os.path.lexists(candidate):
            # The name appeared after the sequence-wide probe: re-classify.
            # A live claim is a hard conflict; ordinary content only moves
            # the selection to the next internal name.
            if _is_live_claim(candidate):
                raise conflict(candidate)
            continue
        if overlaps_business(candidate):
            continue
        try:
            os.symlink(held, candidate)
        except FileExistsError:
            if _is_live_claim(candidate):
                raise conflict(candidate) from None
            continue
        return candidate
    raise FixtureBuildError(
        f"could not find a free claim anchor name beside {resolved}")


def prepare_root(path: Path, *, description: str = "fixture root",
                 business_paths: Iterable[Path] = ()) -> PreparedRoot:
    """Acquire one sample root exclusively and prepare it as an empty directory.

    An existing empty directory is kept as-is (its ownership is recorded);
    a missing directory is created. Non-empty, non-directory and producer
    owned targets are refused. The occupation anchor beside the root is
    published atomically and held by the returned object until the caller
    releases it.
    """
    raw = Path(os.path.abspath(os.fspath(path)))
    resolved = Path(path).resolve()
    _refuse_live_claim_path(raw, resolved, description=description)
    _refuse_live_claim_ancestors(raw, resolved)
    if is_producer_owned(resolved):
        raise FixtureBuildError(
            f"{description} must be outside producer checkout: {resolved}")
    if resolved.exists():
        if not resolved.is_dir():
            raise FixtureBuildError(f"{description} is not a directory: {resolved}")
        if any(resolved.iterdir()):
            raise FixtureBuildError(
                f"refusing to replace non-empty foreign directory: {resolved}")
    _mkdir_parents_claim_free(raw.parent, resolved.parent)
    _refuse_live_claim_ancestors(raw, resolved)
    held = _held_dir_for(resolved)
    held.mkdir()
    try:
        (held / _HELD_MARKER).touch(exist_ok=False)
    except OSError:
        _remove_held_dir(held)
        raise FixtureBuildError(
            f"could not prepare the occupation directory: {held}") from None
    _seal_held_dir(held)
    try:
        anchor = _publish_anchor(
            resolved, held,
            business_paths=[raw, resolved, *business_paths],
            description=description)
    except BaseException:
        _remove_held_dir(held)
        raise
    try:
        created = False
        if _is_live_claim(resolved):
            raise FixtureBuildError(
                f"{description} collides with an existing claim directory: "
                f"{resolved}")
        _refuse_live_claim_ancestors(raw, resolved)
        if resolved.exists():
            if not resolved.is_dir() or any(resolved.iterdir()):
                raise FixtureBuildError(
                    f"{description} changed while the claim was held: {resolved}")
        else:
            try:
                resolved.mkdir()
                created = True
            except FileExistsError:
                if (_is_live_claim(resolved) or not resolved.is_dir()
                        or any(resolved.iterdir())):
                    raise FixtureBuildError(
                        f"{description} changed while the claim was held: {resolved}"
                    ) from None
            except OSError as exc:
                raise FixtureBuildError(
                    f"{description} cannot be created (the location is not "
                    f"writable, for example inside a sealed occupation "
                    f"directory): {resolved}") from exc
        identity = resolved.stat()
    except BaseException:
        _discard_claim(anchor, held)
        raise
    return PreparedRoot(resolved, anchor, held, created, (identity.st_ino, identity.st_dev))


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
    raw = Path(os.path.abspath(os.fspath(path)))
    resolved = path.resolve()
    _refuse_live_claim_path(raw, resolved, description="sample write")
    _refuse_live_claim_ancestors(raw, resolved)
    _mkdir_parents_claim_free(raw.parent, resolved.parent)
    try:
        path.write_text(text, encoding="utf-8")
    except PermissionError as exc:
        raise FixtureBuildError(
            "sample path is not writable (refused; it may lie inside a "
            f"sealed occupation directory): {path}") from exc


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=1) + "\n")


def write_json_exclusive(path: Path, value: Any) -> None:
    """Create the file exclusively; an existing file is never overwritten."""
    path = Path(path)
    raw = Path(os.path.abspath(os.fspath(path)))
    resolved = path.resolve()
    _refuse_live_claim_path(raw, resolved, description="manifest output")
    _refuse_live_claim_ancestors(raw, resolved)
    _mkdir_parents_claim_free(raw.parent, resolved.parent)
    payload = (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    try:
        handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o644)
    except FileExistsError:
        raise FixtureBuildError(
            f"output appeared during preparation; refusing to overwrite: {path}"
        ) from None
    except PermissionError as exc:
        raise FixtureBuildError(
            "output path is not writable (refused; it may lie inside a "
            f"sealed occupation directory): {path}") from exc
    except OSError as exc:
        raise FixtureBuildError(
            f"refusing to write through a symlink at the output path: {path}"
        ) from exc
    with os.fdopen(handle, "wb") as stream:
        stream.write(payload)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
