"""Issue 74 R3: cross-run claim safety without reserving internal claim names."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from gate2_evidence import TestPreparationError


TESTS = Path(__file__).resolve().parent
PRODUCER = TESTS.parents[3]


def load_entry(number):
    filename = f"prepare_issue{number}_stage{4 if number == 53 else 3}_fixture.py"
    spec = importlib.util.spec_from_file_location(
        f"issue74_cross_run_entry_{number}", TESTS / "runtime" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Issue74CrossRunClaimTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory(
            prefix="issue74-cross-run-", dir=os.environ.get("TMPDIR")
        )
        self.addCleanup(self.holder.cleanup)
        self.space = Path(self.holder.name).resolve()
        if self.space.is_relative_to(PRODUCER):
            raise TestPreparationError("isolated test directory is inside producer")
        self.entries = {number: load_entry(number) for number in (53, 55)}

    def paths(self, name):
        parent = self.space / name
        parent.mkdir()
        return parent / "program", parent / "profile", parent / "manifest.json"

    def build(self, number, paths):
        program, profile, output = paths
        if number == 53:
            return self.entries[number].build_fixture(program, profile, output=output)
        return self.entries[number].build_fixture(program, output=output)

    @staticmethod
    def writing(args, kwargs):
        mode = kwargs.get("mode", args[0] if args else "r")
        return any(flag in mode for flag in "wax+")

    def test_live_claim_directory_cannot_be_used_as_another_run_root(self):
        original_open = Path.open
        for number in (53, 55):
            with self.subTest(entry=number):
                paths = self.paths(f"live-claim-{number}")
                reached = []

                def interleave(path, *args, **kwargs):
                    if (path == paths[0] / "info.json"
                            and self.writing(args, kwargs)
                            and not reached):
                        reached.append(True)
                        roots = {paths[0].resolve()}
                        if number == 53:
                            roots.add(paths[1].resolve())
                        live_claims = sorted(
                            candidate for candidate in paths[0].parent.iterdir()
                            if candidate.is_dir() and candidate.resolve() not in roots
                        )
                        expected_claims = 2 if number == 53 else 1
                        if len(live_claims) != expected_claims:
                            raise TestPreparationError(
                                "could not identify the live occupation directories "
                                "from the isolated run state"
                            )
                        live_claim = live_claims[0]
                        before = list(live_claim.iterdir())
                        contender_parent = self.space / f"contender-{number}"
                        contender_parent.mkdir()
                        contender = (
                            live_claim,
                            contender_parent / "profile",
                            contender_parent / "manifest.json",
                        )
                        with self.assertRaises(self.entries[number].FixtureBuildError):
                            self.build(number, contender)
                        self.assertEqual(list(live_claim.iterdir()), before)
                        self.assertFalse(contender[1].exists())
                        self.assertFalse(contender[2].exists())
                    return original_open(path, *args, **kwargs)

                with mock.patch.object(Path, "open", interleave):
                    self.build(number, paths)
                if reached != [True]:
                    raise TestPreparationError(
                        "first run did not reach the declared pre-write interleave point"
                    )
                self.assertTrue((paths[0] / "info.json").is_file())
                self.assertTrue(paths[2].is_file())

    def test_claim_like_paths_without_live_claim_remain_legal(self):
        """Internal claim-name encoding alone must not make a legal path invalid."""
        for number in (53, 55):
            for surface in (
                "root-name",
                "root-ancestor",
                "output-name",
                "output-ancestor",
            ):
                with self.subTest(entry=number, surface=surface):
                    parent = self.space / f"inactive-claim-like-{number}-{surface}"
                    parent.mkdir()
                    program = parent / "program"
                    profile = parent / "profile"
                    output = parent / "manifest.json"
                    claim_like = ".ordinary.fixture-claim"

                    if surface == "root-name":
                        program = parent / claim_like
                    elif surface == "root-ancestor":
                        ordinary_parent = parent / claim_like
                        ordinary_parent.mkdir()
                        program = ordinary_parent / "program"
                    elif surface == "output-name":
                        output = parent / claim_like
                    else:
                        ordinary_parent = parent / claim_like
                        ordinary_parent.mkdir()
                        output = ordinary_parent / "manifest.json"

                    result = self.build(number, (program, profile, output))
                    self.assertIsInstance(result, dict)
                    self.assertTrue((program / "info.json").is_file())
                    if number == 53:
                        self.assertTrue(profile.is_dir())
                    self.assertTrue(output.is_file())
                    self.assertGreater(len(output.read_bytes()), 0)


if __name__ == "__main__":
    unittest.main()
