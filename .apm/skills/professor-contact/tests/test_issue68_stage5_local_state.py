"""PC68-D1: seven proof owners, reusing concrete regression assertions.

Only these seven methods are discovered in this asset. Components are run
with their own setUp/tearDown/cleanups; a skip or nonordinary outcome cannot
turn the enclosing proof into PASS. The component mapping is also used by
the gate runner to avoid running the same component twice.
"""
import importlib
import io
import unittest


PROOFS = {
    "P1": [("test_contact_state", "TestStage5PerProfessorState", [
        "test_issue68_t68_1_local_pack_is_the_only_stage5_fact_source",
        "test_issue68_t68_1b_missing_local_pack_never_falls_back_to_global",
        "test_issue68_t68_1c_local_pack_must_prove_one_professor",
        "test_issue68_t68_2_legacy_global_pack_cannot_change_local_result"])],
    "P2": [("test_contact_state", "TestStage5PerProfessorState", [
        "test_issue68_t68_3_other_professor_files_never_gate_this_one",
        "test_issue68_t68_4_this_professor_stays_fail_closed",
        "test_issue68_unselected_malformed_local_row_is_noise"]),
        ("test_issue68_choices_attribution", "TestStage5ChoicesAttribution", [
        "test_issue68_r11_targeted_run_filters_unselected_explicit_rows"])],
    "P3": [("test_contact_state", "TestStage5PerProfessorState", [
        "test_issue68_t68_5_local_batch_covers_one_professor_only"])],
    "P4": [("test_contact_state", "TestStage5PerProfessorState", [
        "test_issue68_t68_6_second_professor_failure_keeps_first_commit",
        "test_issue68_validation_updates_only_the_named_local_state"])],
    "P5": [("test_contact_state", "TestStage5PerProfessorState", [
        "test_issue68_t68_7_finalize_never_touches_the_aggregate"]),
        ("test_stage5_overview", "TestStage5OverviewRebuild", None)],
    "P6": [("test_issue68_choices_attribution", "TestStage5ListInputs", None)],
    "P7": [("test_issue68_choices_attribution", "TestStage5ChoicesAttribution", [
        "test_issue68_r10_counterexample3_unique_candidate_legacy_row_is_a_duplicate",
        "test_issue68_r10_counterexample4_multi_candidate_excludes_satisfied_owner",
        "test_issue68_r10_undecided_multi_candidate_owner_returns_needs_input",
        "test_issue68_r10_counterexample2_cross_professor_error_stays_with_its_owner",
        "test_issue68_r10_counterexample5_invalid_explicit_dir_never_transfers_by_id",
        "test_issue68_r10_foreign_rows_stay_noise_without_a_scope",
        "test_issue68_r10_single_object_choices_and_default_scope_keep_working"]),
        ("test_issue68_choices_attribution", "TestStage5ImmutableWrapperOwnerLocalChoices", None)],
}


def components(proof):
    for module_name, class_name, names in PROOFS[proof]:
        cls = getattr(importlib.import_module(module_name), class_name)
        for name in names or unittest.defaultTestLoader.getTestCaseNames(cls):
            yield cls(name)


class TestIssue68Stage5LocalState(unittest.TestCase):
    def prove(self, proof):
        cases = list(components(proof))
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
        self.proof_evidence = {"proof": proof, "components": [case.id() for case in cases],
                               "tests_run": result.testsRun, "log": stream.getvalue()}
        if result.testsRun != len(cases) or result.skipped or result.expectedFailures or result.unexpectedSuccesses or result.errors:
            raise RuntimeError("Invalid proof execution: " + stream.getvalue())
        self.assertFalse(result.failures, stream.getvalue())

    def test_stage5_local_pack_is_authoritative_and_global_fallback_is_forbidden(self):
        self.prove("P1")

    def test_stage5_email_id_scope_is_local_and_unrelated_local_rows_are_noise(self):
        self.prove("P2")

    def test_stage5_batch_without_email_id_never_crosses_professor_owner(self):
        self.prove("P3")

    def test_stage5_multi_professor_partial_results_keep_owner_state_isolated(self):
        self.prove("P4")

    def test_stage5_rebuild_overview_reads_owner_outputs_only_and_is_idempotent(self):
        self.prove("P5")

    def test_stage5_list_inputs_discovers_local_packs_independently(self):
        self.prove("P6")

    def test_stage5_choices_attribution_uses_canonical_directory_and_email_id(self):
        self.prove("P7")


if __name__ == "__main__":
    unittest.main(verbosity=2)
