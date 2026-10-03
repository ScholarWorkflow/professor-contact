"""Issue 74: deterministic checks through the two supported preparation entries."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest import mock

from gate2_evidence import TestPreparationError


BASELINE = "768b49ef4514e36edec6b57ed3821a99af9e9c00"
TESTS = Path(__file__).resolve().parent
PRODUCER = TESTS.parents[3]
RELATIVE = ".apm/skills/professor-contact/tests/runtime/"


def load_entry(number):
    filename = f"prepare_issue{number}_stage{4 if number == 53 else 3}_fixture.py"
    spec = importlib.util.spec_from_file_location(f"issue74_entry_{number}", TESTS / "runtime" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Issue74FixtureTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory(prefix="issue74-", dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.holder.cleanup)
        self.space = Path(self.holder.name).resolve()
        if self.space.is_relative_to(PRODUCER):
            raise TestPreparationError("isolated test directory is inside producer")
        self.entries = {number: load_entry(number) for number in (53, 55)}

    def paths(self, name):
        parent = self.space / name
        parent.mkdir()
        return parent / "program", parent / "profile", parent / "manifest.json"

    def build(self, number, paths, entry=None):
        program, profile, output = paths
        module = entry or self.entries[number]
        if number == 53:
            return module.build_fixture(program, profile, output=output)
        return module.build_fixture(program, output=output)

    def snapshot(self, parent):
        result = {}
        for path in sorted(parent.rglob("*")):
            key = str(path.relative_to(parent))
            if path.is_symlink():
                result[key] = ("symlink", os.readlink(path))
            elif path.is_dir():
                result[key] = ("directory", None)
            else:
                result[key] = ("file", path.read_bytes())
        return result

    def require_hook(self, triggered):
        if triggered != [True]:
            raise TestPreparationError("declared operation hook was not reached exactly once")

    @contextmanager
    def injected_failure(self, triggered):
        error = None
        try:
            yield
        except Exception as caught:
            error = caught
        self.require_hook(triggered)
        if error is None:
            self.fail("valid injected conflict or write error was silently accepted")
        if isinstance(error, AssertionError):
            raise error

    def writing(self, args, kwargs):
        mode = kwargs.get("mode", args[0] if args else "r")
        return any(flag in mode for flag in "wax+")

    def baseline(self, number):
        filename = Path(self.entries[number].__file__).name
        process = subprocess.run(["git", "show", f"{BASELINE}:{RELATIVE}{filename}"],
                                 cwd=PRODUCER, capture_output=True, text=True)
        if process.returncode:
            raise TestPreparationError("fixed baseline object unavailable: " + process.stderr)
        # Load immutable reference source in memory. Its root detector still sees
        # the actual producer; no reference artifacts are installed in a consumer.
        from types import SimpleNamespace
        namespace = {"__file__": str(TESTS / "runtime" / filename), "__name__": "issue74_reference"}
        exec(compile(process.stdout, filename, "exec"), namespace)
        return SimpleNamespace(**namespace)

    def test_compatibility_bytes_manifest_hashes_and_returns(self):
        for number, inside in ((53, False), (53, True), (55, False), (55, True)):
            with self.subTest(entry=number, manifest_inside=inside):
                paths = self.paths(f"bytes-{number}-{inside}")
                if inside:
                    paths = (paths[0], paths[1], paths[0] / "new-manifest.json")
                reference = self.build(number, paths, self.baseline(number))
                expected = self.snapshot(paths[0].parent)
                # Only the exclusive test-owned parent is reset. Both versions
                # receive exactly the same resolved path values.
                shutil.rmtree(paths[0].parent)
                paths[0].parent.mkdir()
                actual = self.build(number, paths)
                self.assertEqual(actual, reference)
                self.assertEqual(self.snapshot(paths[0].parent), expected)
                self.assertEqual(json.loads(paths[2].read_text(encoding="utf-8")), actual)
                for relative, digest in actual["input_hashes"].items():
                    path = paths[1] / relative.removeprefix("profile/") if relative.startswith("profile/") else paths[0] / relative
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
                for relative in actual["forbidden_outputs"]:
                    self.assertFalse((paths[0] / relative).exists())
                root = self.space / f"wrapper-{number}-{inside}"
                result = self.entries[number]._prepare_root(root)
                self.assertIsNone(result) if number == 53 else self.assertEqual(result, root.resolve())

    def test_cli_from_unrelated_directory_without_pythonpath(self):
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        for number in (53, 55):
            with self.subTest(entry=number):
                paths = self.paths(f"cli-{number}")
                args = [sys.executable, self.entries[number].__file__, "--program-root", str(paths[0]), "--output", str(paths[2])]
                if number == 53:
                    args.extend(["--profile-root", str(paths[1])])
                success = subprocess.run(args, cwd=self.space, env=environment, capture_output=True, text=True)
                self.assertEqual(success.returncode, 0, success.stderr)
                message = json.loads(success.stdout)
                self.assertEqual(message["status"], "ok")
                self.assertEqual(message["program_root"], str(paths[0].resolve()))
                self.assertEqual(message["output"], str(paths[2].resolve()))
                if number == 53:
                    self.assertEqual(message["profile_root"], str(paths[1].resolve()))
                before = self.snapshot(paths[0].parent)
                failure = subprocess.run(args, cwd=self.space, env=environment, capture_output=True, text=True)
                self.assertEqual(failure.returncode, 1, failure.stderr)
                self.assertEqual(json.loads(failure.stdout)["status"], "error")
                self.assertEqual(self.snapshot(paths[0].parent), before)

    def test_preexisting_conflicts_fail_before_any_sample_write(self):
        for number in (53, 55):
            kinds = ["file-root", "nonempty-root", "file-output", "directory-output", "sample-output", "producer-root", "producer-root-exact", "producer-output"]
            if number == 53:
                kinds.extend(["file-profile", "nonempty-profile", "producer-profile", "producer-profile-exact"])
            for kind in kinds:
                with self.subTest(entry=number, conflict=kind):
                    program, profile, output = self.paths(f"conflict-{number}-{kind}")
                    producer = program.parent / "synthetic-producer"
                    producer.mkdir()
                    if kind == "file-root":
                        program.write_bytes(b"original-root")
                    elif kind == "nonempty-root":
                        program.mkdir()
                        (program / "keep").write_bytes(b"original-content")
                    elif kind == "file-output":
                        output.write_bytes(b"original-manifest")
                    elif kind == "directory-output":
                        output.mkdir()
                    elif kind == "sample-output":
                        output = program / "info.json"
                    elif kind == "producer-root":
                        program = producer / "forbidden"
                    elif kind == "producer-root-exact":
                        program = producer
                    elif kind == "producer-output":
                        output = producer / "forbidden.json"
                    elif kind == "file-profile":
                        profile.write_bytes(b"original-profile")
                    elif kind == "nonempty-profile":
                        profile.mkdir()
                        (profile / "keep").write_bytes(b"original-profile-content")
                    elif kind == "producer-profile":
                        profile = producer / "forbidden-profile"
                    elif kind == "producer-profile-exact":
                        profile = producer
                    before = self.snapshot(program.parent if kind != "producer-root" else producer.parent)
                    with mock.patch.object(self.entries[number].support, "producer_root", return_value=producer):
                        with self.assertRaises(self.entries[number].FixtureBuildError):
                            self.build(number, (program, profile, output))
                    parent = producer.parent
                    self.assertEqual(self.snapshot(parent), before)
                    if kind not in ("file-profile", "nonempty-profile", "producer-profile-exact"):
                        self.assertFalse(profile.exists())
                    if kind not in ("file-root", "nonempty-root", "producer-root-exact"):
                        self.assertFalse(program.exists())

    def test_equal_and_nested_issue53_roots_are_rejected_without_changes(self):
        for relation in ("equal", "profile-below", "program-below"):
            with self.subTest(relation=relation):
                program, profile, output = self.paths(relation)
                if relation == "equal":
                    profile = program
                elif relation == "profile-below":
                    profile = program / "nested"
                else:
                    program = profile / "nested"
                with self.assertRaises(self.entries[53].FixtureBuildError):
                    self.build(53, (program, profile, output))
                self.assertFalse(program.exists())
                self.assertFalse(profile.exists())
                self.assertFalse(output.exists())

    def test_existing_empty_root_identity_is_preserved(self):
        original_rmdir = os.rmdir
        for number in (53, 55):
            with self.subTest(entry=number):
                paths = self.paths(f"empty-{number}")
                paths[0].mkdir()
                identity = (paths[0].stat().st_dev, paths[0].stat().st_ino)
                deleted = []

                def record_delete(path, *args, **kwargs):
                    if Path(path) == paths[0]:
                        deleted.append(str(path))
                    return original_rmdir(path, *args, **kwargs)

                with mock.patch.object(os, "rmdir", record_delete):
                    self.build(number, paths)
                self.assertEqual(deleted, [])
                self.assertEqual((paths[0].stat().st_dev, paths[0].stat().st_ino), identity)

    def test_different_runs_do_not_share_writable_outputs(self):
        for number in (53, 55):
            with self.subTest(entry=number):
                left = self.paths(f"left-{number}")
                right = self.paths(f"right-{number}")
                self.build(number, left)
                before = self.snapshot(left[0].parent)
                self.build(number, right)
                (right[0] / "info.json").write_bytes(b"changed-right-only")
                self.assertEqual(self.snapshot(left[0].parent), before)

    def test_overlapping_call_cannot_recreate_first_empty_root(self):
        original_open = Path.open
        for number in (53, 55):
            with self.subTest(entry=number):
                paths = self.paths(f"overlap-{number}")
                triggered = []

                def interleave(path, *args, **kwargs):
                    if path == paths[0] / "info.json" and self.writing(args, kwargs) and not triggered:
                        triggered.append(True)
                        identity = (paths[0].stat().st_dev, paths[0].stat().st_ino)
                        alias = self.space / f"alias-{number}"
                        alias.symlink_to(paths[0], target_is_directory=True)
                        contender = (alias, paths[0].parent / "other-profile", paths[0].parent / "other-output.json")
                        with self.assertRaises(self.entries[number].FixtureBuildError):
                            self.build(number, contender)
                        self.assertEqual((paths[0].stat().st_dev, paths[0].stat().st_ino), identity)
                        self.assertFalse(contender[1].exists())
                        self.assertFalse(contender[2].exists())
                    return original_open(path, *args, **kwargs)

                with mock.patch.object(Path, "open", interleave):
                    self.build(number, paths)
                self.require_hook(triggered)
                self.assertEqual(set(path.name for path in paths[0].parent.iterdir()),
                                 {"program", "profile", "manifest.json"} if number == 53 else {"program", "manifest.json"})

    def test_abrupt_exit_leaves_occupation_and_next_call_cannot_take_over(self):
        child = '''
import importlib.util
import os
from pathlib import Path
import sys
from unittest import mock
spec = importlib.util.spec_from_file_location("issue74_abrupt", sys.argv[1])
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
program, profile, output = map(Path, sys.argv[2:5])
original = Path.open
def stop_at_first_write(path, *args, **kwargs):
    mode = kwargs.get("mode", args[0] if args else "r")
    if path == program / "info.json" and any(flag in mode for flag in "wax+"):
        os._exit(91)
    return original(path, *args, **kwargs)
with mock.patch.object(Path, "open", stop_at_first_write):
    if "issue53" in sys.argv[1]:
        entry.build_fixture(program, profile, output=output)
    else:
        entry.build_fixture(program, output=output)
'''
        for number in (53, 55):
            with self.subTest(entry=number):
                paths = self.paths(f"abrupt-{number}")
                environment = dict(os.environ)
                environment.pop("PYTHONPATH", None)
                try:
                    result = subprocess.run([sys.executable, "-c", child, self.entries[number].__file__, *map(str, paths)],
                                            cwd=self.space, env=environment, capture_output=True, text=True, timeout=30)
                except subprocess.TimeoutExpired as error:
                    raise TestPreparationError("abrupt-exit probe did not finish") from error
                if result.returncode != 91:
                    raise TestPreparationError("abrupt-exit hook not reached: " + result.stderr)
                before_files = self.snapshot(paths[0].parent)
                before_paths = set(path.relative_to(paths[0].parent) for path in paths[0].parent.rglob("*"))
                self.assertGreater(len(list(paths[0].parent.iterdir())), 2 if number == 53 else 1,
                                   "abrupt termination must preserve the exclusive occupation")
                with self.assertRaises(self.entries[number].FixtureBuildError):
                    self.build(number, paths)
                self.assertEqual(self.snapshot(paths[0].parent), before_files)
                self.assertEqual(set(path.relative_to(paths[0].parent) for path in paths[0].parent.rglob("*")), before_paths)

    def test_manifest_creation_race_preserves_competing_bytes_and_partial_samples(self):
        original_open = os.open
        for number in (53, 55):
            with self.subTest(entry=number):
                paths = self.paths(f"race-{number}")
                triggered = []

                def conflict(path, flags, *args, **kwargs):
                    if Path(path) == paths[2] and flags & os.O_CREAT and not triggered:
                        triggered.append(True)
                        handle = original_open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
                        with os.fdopen(handle, "wb") as stream:
                            stream.write(b"other-call-manifest")
                    return original_open(path, flags, *args, **kwargs)

                with mock.patch.object(os, "open", conflict):
                    with self.injected_failure(triggered):
                        self.build(number, paths)
                self.require_hook(triggered)
                self.assertEqual(paths[2].read_bytes(), b"other-call-manifest")
                self.assertTrue((paths[0] / "info.json").is_file())
                self.assertEqual(set(path.name for path in paths[0].parent.iterdir()),
                                 {"program", "profile", "manifest.json"} if number == 53 else {"program", "manifest.json"})

    def test_second_root_failure_rolls_back_only_new_owned_first_root(self):
        original_mkdir = Path.mkdir
        for initial in ("new", "existing-empty", "replaced"):
            with self.subTest(initial=initial):
                paths = self.paths(f"rollback-{initial}")
                if initial == "existing-empty":
                    paths[0].mkdir()
                identity = paths[0].stat().st_ino if paths[0].exists() else None
                triggered = []

                def fail_second(path, *args, **kwargs):
                    if path == paths[1]:
                        triggered.append(True)
                        if initial == "replaced":
                            paths[0].rename(paths[0].parent / "original-owned")
                            original_mkdir(paths[0])
                            (paths[0] / "keep").write_bytes(b"replacement-owner")
                        raise OSError("controlled second-root creation failure")
                    return original_mkdir(path, *args, **kwargs)

                with mock.patch.object(Path, "mkdir", fail_second):
                    with self.injected_failure(triggered):
                        self.build(53, paths)
                self.require_hook(triggered)
                self.assertFalse(paths[1].exists())
                self.assertFalse(paths[2].exists())
                if initial == "new":
                    self.assertFalse(paths[0].exists())
                elif initial == "existing-empty":
                    self.assertTrue(paths[0].is_dir())
                    self.assertEqual(paths[0].stat().st_ino, identity)
                    self.assertEqual(list(paths[0].iterdir()), [])
                else:
                    self.assertEqual((paths[0] / "keep").read_bytes(), b"replacement-owner")
                self.assertEqual(set(path.name for path in paths[0].parent.iterdir()),
                                 set() if initial == "new" else {"program"} if initial == "existing-empty" else {"program", "original-owned"})

    def test_sample_write_failure_preserves_partial_samples(self):
        original_open = Path.open
        for number in (53, 55):
            with self.subTest(entry=number):
                paths = self.paths(f"write-failure-{number}")
                profile_file = (paths[1] if number == 53 else paths[0]) / "套磁邮件/套磁信息.md"
                triggered = []

                def fail_write(path, *args, **kwargs):
                    if path == profile_file and self.writing(args, kwargs):
                        triggered.append(True)
                        raise OSError("controlled sample write failure")
                    return original_open(path, *args, **kwargs)

                with mock.patch.object(Path, "open", fail_write):
                    with self.injected_failure(triggered):
                        self.build(number, paths)
                self.require_hook(triggered)
                self.assertTrue((paths[0] / "info.json").is_file())
                self.assertFalse(paths[2].exists())
                self.assertEqual(set(path.name for path in paths[0].parent.iterdir()),
                                 {"program", "profile"} if number == 53 else {"program"})


if __name__ == "__main__":
    unittest.main()
