# Focused verification, 2026-10-24

Baseline and remote main rechecked: `1af814fed6643a27bc1348dcee4d69f13723b253`.
Execution: Python 3.12.14, local cloud checkout; synthetic fixtures only. No real papers, model calls, Zotero, Nix builds, external writes or full business regression.

## Passed

- `python .apm/skills/professor-contact/tests/gate2_evidence.py --start .apm/skills/professor-contact/tests --pattern 'test_stage3_*.py' --out <new-evidence-file>`: 78 tests, PASS; includes three new supporting-paper tests and one stale-contract correction test. Covers current per-direction facts/availability/depth, no out-of-direction facts, non-anchor support with one paper, unchanged current reuse, old v2 and v1 regeneration, partial refresh keeping an unselected direction's old version, and plan/finalize rejecting prose correction of a stale direction. Existing identity, cross-group, caller and correction regressions pass.
- Same evidence entrypoint with `--pattern 'test_issue32_e2e_verifier.py' --contains stage3`: 3 tests, PASS. Current Stage 3 state/checkpoint and routing checks.
- `python scripts/check_test_shards.py`: PASS, 81 modules across 4 shards. New test module registered in its existing Stage 3 shard.
- `git diff --check`: PASS.

## Broader verifier attempt, not a full pass

The same evidence entrypoint with `--pattern 'test_issue32_e2e_verifier.py'` ran 52 tests: 37 passed and 15 failed. The structured runner verdict remains FAIL, not PASS. Inspection shows all 15 remaining failures are installation/projection checks blocked by the absent `yq` executable (`generated_projection_readable` / `producer_sha_pinned`); related isolation tests depend on those checks. No tool was installed to expand this task. Initial execution also caught a canonical isolation fixture still declaring generator v2; its two live declarations were updated to v3, and that mismatch no longer occurs in the repeat run.

This demonstrates deterministic input, validation and reuse behavior only. It does not establish that a live model will select more or better papers, nor certify the entire verifier/business pipeline or CI.

After these runs, the two selection-instruction strings and their documentation were clarified to preserve existing valid gap-based support when paper_facts are missing. No executable projection, reference validation, reuse or test logic changed. The deterministic results above apply to those unchanged paths; instruction wording was reviewed statically and is not live-model evidence. `git diff --check` was repeated after the clarification.
