import unittest

import test_contact_targets as base


class Issue64Gate2T3OracleTests(unittest.TestCase):
    """Supplement G64-T3 with the missing direct no-write observation."""

    def setUp(self):
        self.fixture = base.ContactTargetsTests(
            "test_issue64_t3_path_conflicting_entry_is_skipped_without_blocking_its_professor"
        )
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_issue64_t3_path_conflict_cannot_publish_any_sibling_target(self):
        case = self.fixture
        case.bootstrap(["dir_A"], {"dir_A": "note A"})
        a_target = case.read_target()
        case.target_path.unlink()

        conflicting = case.a_entry(a_target)
        conflicting["preview_path"] = str(base.PROFESSOR_B_DIR / base.PREVIEW_NAME)
        case.write_legacy(case.a_entry(a_target), conflicting)
        legacy_before = case.legacy_path.read_bytes()

        result = base.mod.migrate_legacy_targets(case.root)

        self.assertEqual(result["migrated"], ["教授A"])
        local_targets = {
            path.relative_to(case.root)
            for path in case.root.rglob(base.TARGET_NAME)
            if path.resolve() != case.legacy_path.resolve()
        }
        self.assertEqual(local_targets, {base.PROFESSOR_A_DIR / base.TARGET_NAME})
        self.assertFalse(case.b_target_path().exists())
        self.assertEqual(case.legacy_path.read_bytes(), legacy_before)


if __name__ == "__main__":
    unittest.main()
