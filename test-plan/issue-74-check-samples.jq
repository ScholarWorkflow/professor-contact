($required[0]) as $ids |
{schema_version: 2, verdict: "PASS", tests_run: ($ids | length),
 started: $ids, completed: $ids, load_errors: [], interruption: null,
 missing_required_prefixes: [], events: [], failures: [], errors: [],
 skipped: [], expected_failures: [], unexpected_successes: []} as $ok |
[
 {name: "valid-success", expected: true, evidence: $ok},
 {name: "valid-success-reordered", expected: true,
  evidence: ($ok | .started |= reverse | .completed = .started | .optional_diagnostic = "extra")},
 {name: "valid-product-failure", expected: false,
  evidence: ($ok | .verdict = "FAIL" | .events = [{test_id: $ids[0], evidence_id: $ids[0],
    phase: "product", kind: "failure", verdict: "FAIL", detail: "known false assertion"}]
    | .failures = [{test_id: $ids[0], detail: "known false assertion"}])},
 {name: "invalid-empty-execution", expected: false,
  evidence: ($ok | .tests_run = 0 | .started = [] | .completed = [] | .verdict = "INVALID_TEST_EXECUTION")},
 {name: "missing-required-method", expected: false,
  evidence: ($ok | .started = .started[1:] | .completed = .started | .tests_run = (.started | length))},
 {name: "conflicting-pass-evidence", expected: false,
  evidence: ($ok | .events = [{test_id: $ids[0], evidence_id: $ids[0], phase: "setup",
    kind: "error", verdict: "INVALID_TEST_EXECUTION", detail: "invalid prerequisite"}])}
]
