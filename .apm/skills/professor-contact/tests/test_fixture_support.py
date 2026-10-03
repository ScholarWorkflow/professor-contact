"""Direct coverage for the shared fixture preparation support (issue #74)."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


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
        self.assertFalse(prepared.created)
        self.assertEqual(prepared.path, existing.resolve())
        self.assertTrue(prepared.owned())
        self.assertEqual(existing.stat().st_ino, identity)
        self.assertFalse(any(existing.iterdir()))

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
        self.assertEqual((nonempty / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_check_roots_distinct_rejects_only_identical_roots(self):
        base = self.root / "base"
        with self.assertRaises(support.FixtureBuildError):
            support.check_roots_distinct(
                base, base, first_label="a", second_label="b")

        # Nesting in either direction is no longer a refusal.
        support.check_roots_distinct(
            base, base / "sub", first_label="a", second_label="b")
        support.check_roots_distinct(
            base / "sub", base, first_label="a", second_label="b")

        support.check_roots_distinct(
            self.root / "left", self.root / "right",
            first_label="a", second_label="b")

    def test_ensure_new_output_rejects_existing_producer_and_reserved_path(self):
        taken = self.root / "taken.json"
        taken.write_text("keep", encoding="utf-8")
        reserved = [self.root / "sample.json"]
        for bad in (
            taken,
            fixture53._producer_root() / ".issue74-output-forbidden",
            self.root / "sample.json",
        ):
            with self.assertRaises(support.FixtureBuildError):
                support.ensure_new_output(bad, reserved=reserved)
        self.assertEqual(taken.read_text(encoding="utf-8"), "keep")

        fresh = support.ensure_new_output(self.root / "fresh.json", reserved=reserved)
        self.assertEqual(fresh, (self.root / "fresh.json").resolve())

    def test_discard_created_root_respects_recorded_identity(self):
        created = support.prepare_root(self.root / "created")
        self.assertTrue(created.created)
        support.discard_created_root(created)
        self.assertFalse(created.path.exists())

        pre_existing = self.root / "pre-existing"
        pre_existing.mkdir()
        prepared = support.prepare_root(pre_existing)
        self.assertFalse(prepared.created)
        with self.assertRaises(support.FixtureBuildError):
            support.discard_created_root(prepared)
        self.assertTrue(pre_existing.is_dir())

        replaced = support.prepare_root(self.root / "replaced")
        replaced.path.rmdir()
        replaced.path.mkdir()
        self.assertFalse(replaced.owned())
        with self.assertRaises(support.FixtureBuildError):
            support.discard_created_root(replaced)
        self.assertTrue(replaced.path.is_dir())


class Issue53ProtectionTests(IsolatedRootsTestCase):
    def test_second_root_failure_rolls_back_created_first_root(self):
        profile = self.root / "profile"
        profile.write_text("not a directory", encoding="utf-8")
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                self.root / "program", profile,
                output=self.output / "setup.json")
        self.assertFalse((self.root / "program").exists())
        self.assertEqual(profile.read_text(encoding="utf-8"), "not a directory")
        self.assertFalse((self.output / "setup.json").exists())

    def test_second_root_failure_keeps_pre_existing_first_root(self):
        program = self.root / "program"
        program.mkdir()
        identity = program.stat().st_ino
        profile = self.root / "profile"
        profile.write_text("not a directory", encoding="utf-8")
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(program, profile, output=self.output / "setup.json")
        self.assertTrue(program.is_dir())
        self.assertEqual(program.stat().st_ino, identity)
        self.assertFalse(any(program.iterdir()))

    def test_equal_roots_refused_but_nested_roots_build(self):
        program = self.root / "program"
        # Identical roots stay refused.
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                program, program, output=self.output / "setup.json")
        self.assertFalse(program.exists())
        self.assertFalse((self.output / "setup.json").exists())

        # A profile root nested inside the program root is a legal layout.
        manifest = fixture53.build_fixture(
            program, program / "profile", output=self.output / "setup.json")
        self.assertIsInstance(manifest, dict)
        self.assertTrue((program / "info.json").is_file())
        self.assertTrue(
            (program / "profile" / "套磁邮件" / "套磁信息.md").is_file())
        self.assertTrue((self.output / "setup.json").is_file())

    def test_nonempty_nested_profile_root_refused_for_content(self):
        program = self.root / "program"
        profile = program / "profile"
        profile.mkdir(parents=True)
        (profile / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(fixture53.FixtureBuildError):
            fixture53.build_fixture(
                program, profile, output=self.output / "setup.json")
        # The refusal is the existing content, not the nesting: nothing is
        # replaced and the pre-existing program root is left as it was.
        self.assertTrue(program.is_dir())
        self.assertEqual(
            sorted(path.name for path in program.iterdir()), ["profile"])
        self.assertEqual(
            (profile / "keep.txt").read_text(encoding="utf-8"), "keep")
        self.assertFalse((self.output / "setup.json").exists())

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


class Issue55ProtectionTests(IsolatedRootsTestCase):
    def test_preexisting_manifest_output_is_refused_without_writes(self):
        pre_manifest = self.output / "taken.json"
        pre_manifest.write_text("keep", encoding="utf-8")
        with self.assertRaises(fixture55.FixtureBuildError):
            fixture55.build_fixture(self.root / "program", output=pre_manifest)
        self.assertEqual(pre_manifest.read_text(encoding="utf-8"), "keep")
        self.assertFalse((self.root / "program").exists())

    def test_manifest_bytes_use_the_stable_json_format(self):
        program = self.root / "program"
        manifest = fixture55.build_fixture(program, output=self.output / "setup.json")
        raw = (self.output / "setup.json").read_bytes()
        self.assertEqual(
            raw,
            (json.dumps(manifest, ensure_ascii=False, indent=1) + "\n").encode("utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
