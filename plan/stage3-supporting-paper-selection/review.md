# Contact Stage 3 supporting-paper selection review

NOT_READY for formal merge. The bounded implementation review passes; this is not a mechanical fast-merge change.

Repository: ScholarWorkflow/professor-contact
PR: none; local uncommitted repair only.
Base and current HEAD: 1af814fed6643a27bc1348dcee4d69f13723b253 (remote main independently checked at review time).
Reviewed object: complete working-tree diff plus new test and plan files, archived patch SHA-256 e52b57c69429e7f559bd1129f65740ea899b99ac7e164eaf413961b72d2e8a8f.
Requirement: existing direction-local research facts inform concrete supporting-paper roles; future-work anchors do not exhaust support; allow one paper; no fixed paper count/comparison framework, no zero-paper hard rejection, no Stage 2 rerun or style-validator expansion. Invalidate old-contract reuse.
Canonical plan: plan/stage3-supporting-paper-selection/implementation-plan.md.

## Decisions

- Fast path: not applicable. The change alters evidence-selection instructions, model input, and generation-contract persistence/reuse semantics, rather than only mechanical wording.
- Plan P1–P4: PASS. The initial plan and bounded v1/partial-refresh additions were independently reviewed. The Stage 2 owner already exports facts; Stage 3 projection is the appropriate change point. No unverified core assumption remains for deterministic behavior.
- Test Gates 1/2: PASS for the bounded deterministic targets and existing unittest workflow. Gate 3: PASS for those targets based on the 78-test Stage 3 report, 3 directly relevant verifier tests, and shard/diff checks. This does not certify live-model selection quality.
- M1 Authority & Baseline: PASS for the identified working-tree artifact, not a future commit or PR.
- M2 Implementation Conformance: PASS. Reviewed all changed files and new files, Stage 2 canonical fact production, direction_papers projection, Stage 3 plan/finalize/reuse/correction, legacy normalization, current verifier/fixture, and CI shard registration.
- M3 Scope, Regression & Merge Readiness: NEEDS_MODIFICATION for formal merge readiness only: no submitted head/PR or applicable current-head CI/approval state exists. Source scope and bounded regression review pass.
- Review completeness: COMPLETE for the delivered local artifact and available evidence. No unresolved source defect remains.

## Correctness findings resolved in this review

1. Legacy normalization no longer falsely certifies old candidates as the current generator contract; missing/old versions stay missing/old.
2. A scoped refresh freezes retained directions' old effective versions; refreshing A cannot make old B reusable. Both plan and finalize enforce direction versions in reuse and stale-correction checks, without deleting or regenerating unselected directions.
3. REVIEW_DEFECT corrected: the initial selection wording could over-restrict existing gap-supported references. Final agent and job rules explicitly preserve legal gap evidence as support even without paper_facts; valid facts govern additional research-content inference only. Documentation and plan agree. This wording-only clarification was re-reviewed statically; deterministic test results remain applicable, and no live-model result is claimed.
4. The new test module is registered in the existing CI shard manifest, avoiding a deterministic CI coverage-check failure.

## Evidence and limits

- Existing valid paper_facts, facts_state, and analysis_level reach only their owning direction's model input; unavailable/failed/unknown facts are null, not inferred from titles.
- Instructions require concrete foundation/precedent/boundary relevance, distinguish FW anchors from the full support set, and permit a single paper. Candidate validation remains unchanged, including zero-paper behavior.
- 78 Stage 3 tests PASS (contact-support-selection-stage3-evidence.json); 3 relevant verifier tests PASS (contact-support-selection-stage3-verifier.json).
- Author's shard check PASS: 81 modules/4 shards; git diff --check PASS.
- The broader 52-test verifier attempt remains FAIL: 37 pass, 15 fail with missing yq affecting generated_projection_readable/producer_sha_pinned prerequisites. This is not reported as a full pass or demonstrated product regression. Do not hide the original report.
- No live model, real-paper pipeline, full business regression, install/build, or remote CI was performed or certified.
- ci.yml declares the aggregate test job as the required branch-protection check; actual remote protection/approval state for a new head is not established.

## Next step

The implementation is ready for an authorized commit/PR and normal current-head merge checks, not immediate merging. No additional open-ended business test is requested. After publication, verify the actual required CI/approvals for that head; investigate a remaining missing-yq prerequisite only where it blocks applicable checks. Any content change requires only affected-scope re-review.

Reviewer ran no formal tests, changed no product/test files, and published no comment, approval, or merge.
