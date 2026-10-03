"""Non-acceptance checks: exercise recipe observers without fixture builds."""
from pathlib import Path
import sys
import unittest
import os
from unittest import mock

TESTS = Path(__file__).resolve().parents[1] / ".apm/skills/professor-contact/tests"
sys.path.insert(0, str(TESTS))
import test_issue74_fixture_support as recipe


class RecipeObserverChecks(unittest.TestCase):
    def probe(self):
        probe = recipe.Issue74FixtureTests()
        probe.setUp()
        self.addCleanup(probe.doCleanups)
        return probe

    def test_synthetic_producer_reaches_actual_path_guard(self):
        probe = self.probe()

        def guard_only(number, paths):
            support = probe.entries[number].support
            program, profile, output = paths
            for path in (program, output) + ((profile,) if number == 53 else ()):
                support.resolved_outside_producer(path, description="observer check")
            roots = (program, profile) if number == 53 else (program,)
            if any(p.exists() and (not p.is_dir() or any(p.iterdir())) for p in roots):
                raise support.FixtureBuildError("known root conflict")
            if output.exists() or output == program / "info.json":
                raise support.FixtureBuildError("known output conflict")
            # Legal inputs return without preparing any sample.

        probe.build = guard_only
        probe.test_preexisting_conflicts_fail_before_any_sample_write()

    def test_manifest_competitor_reaches_actual_exclusive_creation(self):
        probe = self.probe()

        def create_only(number, paths):
            program, profile, output = paths
            program.mkdir()
            (program / "info.json").touch()
            if number == 53:
                profile.mkdir()
            # Minimal filesystem state, no fixture data or business execution.
            probe.entries[number].support.write_json_exclusive(output, {"probe": True})

        probe.build = create_only
        probe.test_manifest_creation_race_preserves_competing_bytes_and_partial_samples()

    def test_overwriting_creation_is_rejected(self):
        original = os.open

        def overwriting(path, flags, *args, **kwargs):
            return original(path, (flags & ~os.O_EXCL) | os.O_TRUNC, *args, **kwargs)

        with mock.patch.object(os, "open", overwriting):
            with self.assertRaises(AssertionError):
                self.test_manifest_competitor_reaches_actual_exclusive_creation()

    def test_missing_producer_protection_is_rejected(self):
        probe_entry = recipe.load_entry(53)
        with mock.patch.object(probe_entry.support, "is_producer_owned", return_value=False):
            with self.assertRaises(AssertionError):
                self.test_synthetic_producer_reaches_actual_path_guard()


if __name__ == "__main__":
    unittest.main()
