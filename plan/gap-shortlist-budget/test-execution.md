# Test execution

Requirement R1 / EP2 / TP2 Recipe R2. Execution environment: cloud Linux x86_64, Python 3.12.14. Remote base `214dbef122d023c20db06fc49654daccc0411b10`; candidate I1/TI1 (uncommitted source diff at first attempt, final fixed revision recorded below).

## Attempt 1 — 2026-10-28 07:24 UTC

Executed the six-selector command in test-plan.md from `.apm/skills/professor-contact/tests`. Exit 1; 6 tests in 7.564s, five `ok`, T1 failed. Full output (not committed): `/tmp/contact-gap-shortlist-tests/attempt-1.log`.

T1 stopped at finalize `unknown_reference_id`: its old budget-only fixture had `relevant_keys=[]`, while the reused narrative helper references `paper:AAAA1111`. Product correctly refused a reference outside its package. The test author is correcting only fixture scope; no expectation or product rule relaxed. Independent Gate 3 classifies this and determines the affected retry below.

The three T2 selectors and two maintained document-contract selectors completed `ok`; final acceptance and reuse belong to independent Gate 3, not this execution record.

## Manual T3 observation

Read shared SKILL parameter/cache/input-contract/behavior sections and both analyzer parameter, Step 5.2.4 cost gate, output and failure sections, plus their full diff. Both specify <=20 all; >20 asks all or ranked top20 unless explicit max; named exemptions and candidate-union full analysis unchanged. Default freshness is at most10/full, final shortlist has no numeric cap, legacy reason is informational not another mandatory prompt. No model run, external service, installation or real user data involved.

## Final status

Attempt2 completed after the independent Gate 3 reviewer authorized only T1 retry (PROOF_IMPLEMENTATION_DEFECT). T1 fixture now uses the actual synthetic papers as relevant_keys; no product or expectation change.

Command: `python -B -m unittest -v test_contact_state.TestRunnerBasics.test_01_freshness_budget_does_not_cap_final_shortlist` from the same test directory. 2026-10-28 07:25 UTC, exit0, 1 test in1.960s, OK. Full output (not committed): `/tmp/contact-gap-shortlist-tests/attempt-2.log`.

Observed executions now cover all listed targets; independent Gate 3 PASS / COMPLETE (review_shortlist_dual_plans, 2026-10-28 07:26 UTC; see review.md). Other five results reused from attempt1 as directed; no full rerun.


## Fixed revision applicability

Product/test revision: `0d818c35ebdfd2a0253c89d72f864a8b8b93989c`. The committed product/test blobs are identical to the executed final candidate; existing file modes retained. Independent Gate 3 reviewer confirmed applicability to this fixed head on 2026-10-28 07:31 UTC. Subsequent SHA/review record-only edits do not change tested behavior or require rerunning these targets.
