"""Direct filesystem observations for the existing issue-64 proofs."""
import builtins
from contextlib import contextmanager, ExitStack
import io
import os
from pathlib import Path
from unittest import mock


def path_set(root):
    return {str(path.relative_to(root)) for path in Path(root).rglob('*')}


@contextmanager
def observe_target_access(target):
    """Observe the current Python producer's open/stat and directory surfaces.

    Activation surrounds only the product call; fixture and oracle reads remain
    outside it. No I/O is blocked or substituted, including discarded reads.
    """
    target = os.path.abspath(target)
    events = []
    with ExitStack() as stack:
        for owner, name in ((builtins, 'open'), (io, 'open'), (os, 'open'),
                            (os, 'stat'), (os, 'lstat'), (os, 'scandir'), (os, 'listdir')):
            original = getattr(owner, name)
            def observe(path, *args, _original=original, _name=name, **kwargs):
                if isinstance(path, (str, bytes, os.PathLike)):
                    candidate = os.path.abspath(os.fsdecode(path))
                    if candidate == target:
                        events.append({'operation': _name, 'path': candidate})
                return _original(path, *args, **kwargs)
            stack.enter_context(mock.patch.object(owner, name, observe))
        yield events
