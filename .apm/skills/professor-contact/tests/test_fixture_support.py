"""Direct coverage for the shared fixture preparation support (issue #74).

The migrated #53/#55 asset suites prove the business compatibility of the
two real entries. This module pins the protection boundaries of the shared
tool itself: directory ownership, exclusive claims, output protection,
byte-format parity and the #53 rollback rules.
"""

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = load_module(
    "issue74_fixture_support_for_tests",
    RUNTIME_DIR / "fixture_support.py",
)
fixture53 = load_module(
    "issue74_fixture53_for_tests",
    RUNTIME_DIR / "prepare_issue53_stage4_fixture.py",
)
fixture55 = load_module(
    "issue74_fixture55_for_tests",
    RUNTIME_DIR / "prepare_issue55_stage3_fixture.py",
)


class IsolatedRootsTestCase(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)
        self.output = self.root / "output"
        self.output.mkdir()


class FixtureSupportPrimitiveTests(IsolatedRootsTestCase):
    def test_json_write_byte_format_is_stable(self):
        value = {"kind": "probe", "备注": "文", "n": 2}
        expected = json.dumps(value, ensure_ascii=False, indent=1) + "\n"
        first = self.root / "plain.json"
        support.write_json(first, value)
        self.assertEqual(first.read_text(encoding="utf-8"), expected)

        second = self.root / "exclusive.json"
        support.write_json_exclusive(second, value)
        self.assertEqual(second.read_text(encoding="utf-8"), expected)

    def test_exclusive_json_write_refuses_to_overwrite(self):
        target = self.root / "manifest.json"
        target.write_text("keep", encoding="utf-8")
        with self.assertRaises(support.FixtureBuildError):
            support.write_json_exclusive(target, {"schema_version": 1})
        self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    def test_file_sha256_matches_file_bytes(self):
        payload = "字节摘要\n".encode("utf-8")
        path = self.root / "digest.bin"
        path.write_bytes(payload)
        self.assertEqual(support.file_sha256(path), hashlib.sha256(payload).hexdigest())

    def test_prepare_root_keeps_existing_empty_directory(self):
        existing = self.root / "kept"
        existing.mkdir()
        identity = existing.stat().st_ino
        prepared = support.prepare_root(existing)
        try:
            self.assertFalse(prepared.created)
            self.assertEqual(prepared.path, existing.resolve())
            self.assertTrue(prepared.owned())
            self.assertEqual(existing.stat().st_ino, identity)
            self.assertFalse(any(existing.iterdir()))
        finally:
            prepared.release()
        self.assertFalse(support.claim_path_for(existing.resolve()).exists())

    def test_prepare_root_rejects_producer_non_dir_and_nonempty(self):
        producer_child = fixture53._producer_root() / ".issue74-support-forbidden"
        with self.assertRaises(support.FixtureBuildError):
            support.prepare_root(producer_child)
        self.assertFalse(producer_child.exists())

        file_root = self.root / "plain-file"
        file_root.write_text("data", encoding="utf-8")
        with self.assertRaises(support.FixtureBuildError):
            support.prepare_root(file_root)
        self.assertEqual(file_root.read_text(encoding="utf-8"), "data")

        nonempty = self.root / "nonempty"
        nonempty.mkdir()
        (nonempty / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(support.FixtureBuildError):
            support.prepare_root(nonempty)
        self.assertTrue((nonempty / "keep.txt").exists())

    def test_second_preparation_of_same_path_fails_without_recreating(self):
        first = support.prepare_root(self.root / "claimed")
        identity = first.path.stat().st_ino
        try:
            with self.assertRaises(support.FixtureBuildError):
                support.prepare_root(self.root / "claimed")
            self.assertTrue(first.path.is_dir())
            self.assertEqual(first.path.stat().st_ino, identity)
            self.assertFalse(any(first.path.iterdir()))
        finally:
            first.release()
        second = support.prepare_root(self.root / "claimed")
        second.release()

    def test_prepared_root_release_never_touches_root_content(self):
        prepared = support.prepare_root(self.root / "root")
        (prepared.path / "info.json").write_text("{}", encoding="utf-8")
        prepared.release()
        self.assertTrue((prepared.path / "info.json").exists())

    def test_check_mutually_independent_rejects_equal_and_nested(self):
        base = self.root / "base"
        for first, second in (
            (base, base),
            (base, base / "sub"),
            (base / "sub", base),
        ):
            with self.assertRaises(support.FixtureBuildError):
                support.check_mutually_independent(
                    first, second, first_label="a", second_label="b")

        support.check_mutually_independent(
            self.root / "left", self.root / "right",
            first_label="a", second_label="b")

    def test_roots_separated_from_claims_rejects_overlap_and_containment(self):
        root = self.root / "root"
        claim = self.root / "sibling.fixture-claim"
        for bad_root in (claim, claim / "inner", self.root):
            with self.assertRaises(support.FixtureBuildError):
                support.check_roots_separated_from_claims([bad_root], [claim])
        support.check_roots_separated_from_claims(
            [root, claim.parent / "other"], [claim])

    def test_ensure_new_output_rejects_existing_producer_and_overlap(self):
        taken = self.root / "taken.json"
        taken.write_text("keep", encoding="utf-8")
        reserved = [self.root / "sample.json"]
        claims = [self.root / ".sample.fixture-claim"]
        for bad in (
            taken,
            self.root,
            fixture53._producer_root() / ".issue74-output-forbidden",
            self.root / "sample.json",
        ):
            with self.assertRaises(support.FixtureBuildError):
                support.ensure_new_output(bad, reserved=reserved, claims=claims)
        self.assertEqual(taken.read_text(encoding="utf-8"), "keep")

        fresh = support.ensure_new_output(
            self.root / "fresh.json", reserved=reserved, claims=claims)
        self.assertEqual(fresh, (self.root / "fresh.json").resolve())

    def test_ensure_new_output_refuses_claim_directory_and_its_inside(self):
        claim = self.root / ".sample.fixture-claim"
        for bad in (claim, claim / "manifest.json", claim / "nested" / "out.json"):
            with self.assertRaises(support.FixtureBuildError):
                support.ensure_new_output(bad, claims=[claim])
        self.assertFalse(claim.exists())

    def test_claim_like_names_are_legal_without_live_claim(self):
        direct_root = self.root / ".ordinary.fixture-claim"
        prepared = support.prepare_root(direct_root)
        self.assertEqual(prepared.path, direct_root.resolve())
        prepared.release()

        nested_parent = self.root / ".ordinary-parent.fixture-claim"
        nested_parent.mkdir()
        nested_root = nested_parent / "inner"
        prepared_nested = support.prepare_root(nested_root)
        self.assertEqual(prepared_nested.path, nested_root.resolve())
        prepared_nested.release()

        direct_output = self.root / ".ordinary-output.fixture-claim"
        self.assertEqual(
            support.ensure_new_output(direct_output), direct_output.resolve())

        output_parent = self.root / ".ordinary-output-parent.fixture-claim"
        output_parent.mkdir()
        nested_output = output_parent / "manifest.json"
        self.assertEqual(
            support.ensure_new_output(nested_output), nested_output.resolve())

    def test_live_claim_collision_is_refused_but_shaped_names_stay_legal(self):
        holder = support.prepare_root(self.root / "holder")
        self.addCleanup(holder.release)
        live = support.claim_path_for(holder.path)
        self.assertTrue(live.is_symlink())
        self.assertEqual(len(list(live.iterdir())), 0)
        with self.assertRaises(support.FixtureBuildError):
            support.prepare_root(live)
        with self.assertRaises(support.FixtureBuildError):
            support.prepare_root(live / "inner")
        with self.assertRaises(support.FixtureBuildError):
            support.ensure_new_output(live)
        with self.assertRaises(support.FixtureBuildError):
            support.ensure_new_output(live / "out.json")
        with self.assertRaises(support.FixtureBuildError):
            support.write_text(live / "late.txt", "text")
        self.assertEqual(len(list(live.iterdir())), 0)
        holder.release()
        self.assertFalse(live.exists())

        inactive = self.root / ".taken.fixture-claim"
        inactive.mkdir()
        inside = support.prepare_root(inactive / "inner")
        self.assertTrue(inside.created)
        inside.release()
        self.assertTrue((inactive / "inner").is_dir())
        output = support.ensure_new_output(inactive / "out.json")
        support.write_json_exclusive(output, {"schema_version": 1})
        self.assertTrue(output.is_file())

        shaped = support.prepare_root(self.root / ".ordinary.fixture-claim")
        self.assertTrue(shaped.created)
        shaped.release()
        self.assertTrue((self.root / ".ordinary.fixture-claim").is_dir())

        nested = support.prepare_root(self.root / ".layer.fixture-claim" / "inner")
        nested.release()
        plain_output = support.ensure_new_output(self.root / ".named.fixture-claim")
        support.write_json_exclusive(plain_output, {"schema_version": 1})

        normal = support.prepare_root(self.root / "plain-root")
        normal.release()
        support.ensure_new_output(self.root / "plain-output.json")

    def test_preexisting_empty_claim_shaped_root_stays_legal(self):
        pre = self.root / ".pre-existing.fixture-claim"
        pre.mkdir()
        identity = pre.stat().st_ino
        prepared = support.prepare_root(pre)
        self.assertFalse(prepared.created)
        self.assertTrue(prepared.owned())
        prepared.release()
        self.assertEqual(pre.stat().st_ino, identity)
        self.assertFalse(any(pre.iterdir()))

    def test_live_claim_appearing_after_upfront_check_blocks_claim_and_root(self):
        parent = (self.root / ".late.fixture-claim").resolve()
        inner = parent / "inner"
        original_mkdir = Path.mkdir
        planted = []

        def plant_anchor_after_parent_creation(path, *args, **kwargs):
            result = original_mkdir(path, *args, **kwargs)
            if path == parent and not planted:
                planted.append(True)
                parent.rmdir()
                held = self.root / ".late.fixture-claim.held-1"
                held.mkdir()
                os.symlink(held, parent)
            return result

        with mock.patch.object(Path, "mkdir", plant_anchor_after_parent_creation):
            with self.assertRaises(support.FixtureBuildError):
                support.prepare_root(inner)
        self.assertTrue(planted)
        self.assertTrue((self.root / ".late.fixture-claim.held-1").is_dir())
        self.assertEqual(len(list(parent.iterdir())), 0)
        self.assertFalse(inner.exists())

    def test_sample_and_manifest_write_refuse_live_claim_ancestor(self):
        holder = support.prepare_root(self.root / "holder")
        self.addCleanup(holder.release)
        anchor = support.claim_path_for(holder.path)
        with self.assertRaises(support.FixtureBuildError):
            support.write_text(anchor / "late.txt", "text")
        with self.assertRaises(support.FixtureBuildError):
            support.write_json(anchor / "late.json", {"schema_version": 1})
        self.assertEqual(len(list(anchor.iterdir())), 0)

        manifest_parent = self.root / ".late-manifest.fixture-claim"
        manifest_parent.mkdir()
        output = support.ensure_new_output(manifest_parent / "out.json")
        manifest_parent.rmdir()
        held = self.root / ".late-manifest.fixture-claim.held-1"
        held.mkdir()
        os.symlink(held, manifest_parent)
        with self.assertRaises(support.FixtureBuildError):
            support.write_json_exclusive(output, {"schema_version": 1})
        self.assertFalse(output.exists())

    def test_claim_shaped_roots_stay_legal_for_both_entries(self):
        program = self.root / ".shaped-program.fixture-claim"
        profile = self.root / "shaped-profile"
        manifest = fixture53.build_fixture(
            program, profile, output=self.output / "shaped53.json")
        self.assertEqual(manifest["fixture_kind"], "stage4-only")

        program55 = self.root / ".shaped-55.fixture-claim"
        manifest55 = fixture55.build_fixture(
            program55, output=self.output / "shaped55.json")
        self.assertEqual(manifest55["fixture_kind"], "issue55-stage3-pre")

    def test_discard_created_root_respects_ownership(self):
        created = support.prepare_root(self.root / "created")
        self.assertTrue(created.created)
        support.discard_created_root(created)
        self.assertFalse(created.path.exists())
        created.release()

        pre_existing = self.root / "pre-existing"
        pre_existing.mkdir()
        prepared = support.prepare_root(pre_existing)
        self.assertFalse(prepared.created)
        with self.assertRaises(support.FixtureBuildError):
            support.discard_created_root(prepared)
        self.assertTrue(pre_existing.is_dir())
        prepared.release()

        vanished = support.prepare_root(self.root / "vanished")
        vanished.path.rmdir()
        self.assertFalse(vanished.owned())
        with self.assertRaises(support.FixtureBuildError):
            support.discard_created_root(vanished)
        vanished.release()


class Issue53RollbackAndProtectionTests(IsolatedRootsTestCase):
    def hold_claim(self, root: Path) -> Path:
        """Simulate another run holding the exclusive claim for root."""
        claim = support.claim_path_for(root.resolve())
        claim.parent.mkdir(parents=True, exist_ok=True)
        claim.mkdir()
        self.addCleanup(claim.rmdir)
        return claim

    def test_second_root_failure_rolls_back_created_first_root(self):
        self.hold_claim(self.root / "profile")
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                self.root / "program", self.root / "profile",
                output=self.output / "setup.json")
        self.assertFalse((self.root / "program").exists())
        self.assertFalse((self.root / "profile").exists())
        self.assertTrue(support.claim_path_for(self.root / "profile").exists())

    def test_second_root_failure_keeps_pre_existing_first_root(self):
        program = self.root / "program"
        program.mkdir()
        identity = program.stat().st_ino
        self.hold_claim(self.root / "profile")
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                program, self.root / "profile",
                output=self.output / "setup.json")
        self.assertTrue(program.is_dir())
        self.assertEqual(program.stat().st_ino, identity)
        self.assertFalse(any(program.iterdir()))

    def test_claim_conflict_on_first_root_fails_without_side_effects(self):
        program = self.root / "program"
        program.mkdir()
        self.hold_claim(program)
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                program, self.root / "profile",
                output=self.output / "setup.json")
        self.assertTrue(program.is_dir())
        self.assertFalse((self.root / "profile").exists())
        self.assertFalse((self.output / "setup.json").exists())

    def test_equal_and_nested_roots_are_refused(self):
        program = self.root / "program"
        for profile in (program, program / "sub", self.root):
            with self.assertRaises(fixture53.FixtureBuildError):
                fixture53.build_fixture(
                    program, profile, output=self.output / "setup.json")
        self.assertFalse(program.exists())

    def test_manifest_inside_root_is_allowed_but_sample_overlap_is_not(self):
        program = self.root / "program"
        profile = self.root / "profile"
        fixture53.build_fixture(program, profile, output=program / "manifest.json")
        self.assertEqual(
            json.loads((program / "manifest.json").read_text(encoding="utf-8"))["fixture_kind"],
            "stage4-only",
        )

        second = self.root / "program2"
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                second, self.root / "profile2",
                output=second / "info.json")
        self.assertFalse((self.root / "profile2").exists())
        self.assertFalse(second.exists())

    def test_preexisting_manifest_output_is_refused_without_writes(self):
        pre_manifest = self.output / "taken.json"
        pre_manifest.write_text("keep", encoding="utf-8")
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                self.root / "program", self.root / "profile",
                output=pre_manifest)
        self.assertEqual(pre_manifest.read_text(encoding="utf-8"), "keep")
        self.assertFalse((self.root / "program").exists())
        self.assertFalse((self.root / "profile").exists())

    def test_manifest_inside_claim_directory_is_refused_before_any_write(self):
        program = self.root / "program"
        profile = self.root / "profile"
        claim = support.claim_path_for(program.resolve())
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                program, profile, output=claim / "nested" / "setup.json")
        self.assertFalse(claim.exists())
        self.assertFalse((claim / "nested" / "setup.json").exists())
        self.assertFalse(program.exists())
        self.assertFalse(profile.exists())

    def test_profile_root_taking_the_program_claim_path_is_refused(self):
        program = self.root / "program"
        profile = support.claim_path_for(program.resolve())
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                program, profile, output=self.output / "setup.json")
        self.assertFalse(program.exists())
        self.assertFalse(profile.exists())
        self.assertFalse((self.output / "setup.json").exists())

    def test_root_inside_the_other_claim_directory_is_refused(self):
        program = self.root / "program"
        profile = support.claim_path_for(program.resolve()) / "inner"
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                program, profile, output=self.output / "setup.json")
        self.assertFalse(program.exists())
        self.assertFalse(profile.exists())

    def test_root_equal_to_another_run_claim_is_refused_and_claim_stays_empty(self):
        holder_root = self.root / "holder"
        prepared = support.prepare_root(holder_root)
        self.addCleanup(prepared.release)
        claim = support.claim_path_for(holder_root.resolve())
        self.assertTrue(claim.is_symlink())
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                self.root / "b-program", claim, output=self.output / "b-setup.json")
        self.assertEqual(len(list(claim.iterdir())), 0)
        self.assertTrue(prepared.owned())
        prepared.release()
        self.assertFalse(claim.exists())
        normal = support.prepare_root(self.root / "normal-root")
        normal.release()

    def test_success_releases_both_claims(self):
        program = self.root / "program"
        profile = self.root / "profile"
        fixture53.build_fixture(program, profile, output=self.output / "setup.json")
        self.assertFalse(support.claim_path_for(program.resolve()).exists())
        self.assertFalse(support.claim_path_for(profile.resolve()).exists())
        self.assertTrue((self.output / "setup.json").is_file())


class Issue55ProtectionTests(IsolatedRootsTestCase):
    def test_claim_conflict_blocks_preparation_and_keeps_directory(self):
        program = self.root / "program"
        program.mkdir()
        claim = support.claim_path_for(program.resolve())
        claim.mkdir()
        self.addCleanup(claim.rmdir)
        with self.assertRaises(fixture55.FixtureBuildError):
            fixture55.build_fixture(program, output=self.output / "setup.json")
        self.assertTrue(program.is_dir())
        self.assertFalse(any(program.iterdir()))
        self.assertFalse((self.output / "setup.json").exists())

    def test_manifest_inside_claim_directory_is_refused_before_any_write(self):
        program = self.root / "program"
        claim = support.claim_path_for(program.resolve())
        with self.assertRaises(fixture55.FixtureBuildError):
            fixture55.build_fixture(program, output=claim / "manifest.json")
        self.assertFalse(claim.exists())
        self.assertFalse((claim / "manifest.json").exists())
        self.assertFalse(program.exists())

    def test_manifest_bytes_use_the_stable_json_format(self):
        program = self.root / "program"
        manifest = fixture55.build_fixture(program, output=self.output / "setup.json")
        raw = (self.output / "setup.json").read_bytes()
        self.assertEqual(
            raw,
            (json.dumps(manifest, ensure_ascii=False, indent=1) + "\n").encode("utf-8"),
        )
        self.assertFalse(support.claim_path_for(program.resolve()).exists())


if __name__ == "__main__":
    unittest.main()
