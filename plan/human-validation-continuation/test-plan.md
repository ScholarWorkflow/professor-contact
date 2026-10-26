# Human validation continuation — TP1

- Requirement R1 / execution EP1.1; baseline `18fd48d1b6f2e26241c304d6acddb025297f08e4`.
- Proposed review status: pending. No implementation/tests run or PASS claimed. [EP1.1](execution-plan.md) defines the sole intended contract; [review](review.md) records independent decisions.
- Rules: [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253), [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d); versions in EP1.1.

## Required checklist — acceptance ceiling

| Goal / input | Expected result | Sufficient check |
|---|---|---|
| C-A: Stage2 and Stage3 terminal two-round failure, explicit +2 then exhausted +1 grant | Default remains2; effective limit4 then5; actual rounds advance without reset through correction/record; successful later result stops; old failure/report/history retained | Focused product command tests using existing per-stage synthetic fixtures; direct JSON and result assertions. Exercise one cumulative path per stage, not every possible number |
| C-B: No grant, invalid nonpositive grant, repeated grant on reopened state, next-round jump or terminal pass | No automatic extension/restart or extra validation accepted; no failure erased; no mutation on rejected requests | Representative command tests for these directly changed admission rules; existing default2 results reused where unchanged |
| C-C: Continued correction with Stage2 fixed-source block and Stage3 recorded global/scoped findings | Fixed block stays with source/generator owner; only recorded failed scope reopens; untouched machine facts/candidates preserved; current render/input binding remains required | Reuse Stage2 fixed-evidence and Stage3 correction fixtures/assertions in the focused per-stage tests; no new boundary matrix |
| C-D: Legacy no-policy records and real new-cycle transition | Legacy terminal unchanged unless explicitly granted; preserved historical failure; new genuine cycle default2/no inherited grant, no-op correction/rerender does not reset | Direct state lifecycle assertions at existing acceptance/carry boundary, with one actual changed-source/new-generation fixture |
| C-E: Runtime instructions, result readers and Stage5 boundary | Human must choose N for named stage/professor; native delegation/correction contracts retained; extended result recognized by direct Stage2/3 readers; Stage5 unchanged | Static review of affected caller/reader changes plus existing assertions only where directly modified; do not add a Stage5 workflow run |

Each stage needs one integrated command path because it has distinct state consumers. No separate live-model repetition for each limit, no numeric boundary sweep, no default-three migration, statistics, total workflow, installation matrix, credential authenticity tests or new test framework. Human identity is the stated caller trust boundary, not a claim to test cryptographic authorization.

## Recipe and pending executable wiring

This is the complete test design. Gate2 is pending: product/tests are not yet written, so exact new selectors/fixture setup are not falsely presented as executable. Test owner must fill this file before execution, not append contradictory comments or add a separate proof manual.

1. Reuse current Python/unittest producer tests and disposable tempfile fixtures under `.apm/skills/professor-contact/tests/`; starting references are `test_stage2_style_validation_handoff.py`, `test_stage3_validation_refine.py`, and `test_issue66_validation_handoff.py`. Do not run their full suites merely because they are referenced; select/adapt only cases required above. No user state or model service required.
2. Add focused cases invoking the public grant commands and existing record/correction/Stage3 handoff entries. Supply exact next report files and expected current rounds. Check persisted JSON with ordinary assertions; use the producer fixture builders for valid report, render and input binding, not a parallel implementation of validation policy.
3. Before Gate2, record implementation SHA/interpreter, exact module/selectors/command, the per-stage prepared fixture inputs, output paths and the mapping to C-A–E. Shared helper unit tests must not duplicate complete command proof of the same targets. New tests live in producer, not shared fixtures.
4. Output under one isolated `/tmp/contact-validation-continuation.*` directory. Preserve first failures and later affected retries; commit only concise non-sensitive result summaries. Human authorization examples use synthetic text, not private conversation archives.
5. Missing dependencies/fixtures are unable-to-judge. Do not install or repeatedly rerun unchanged failures. One same-input retry after a documented concrete external setup correction is permitted by this recipe; changed product reruns only impacted checks, changed expectation/input requires recipe impact review. No retry merely to get a preferable validator result.

## Review and delivery

Independent reviewer confirms test design/Gate1 and later Gate2 executable wiring. Execution owner records PASS/business failure/unable-to-judge/unexecuted per target; Gate3 reviewer evaluates recorded results without re-certifying source or rerunning unaffected checks. Plan-only commits do not invalidate prior evidence. Implementation, exact recipe and all formal results remain pending at this PR's publication.
