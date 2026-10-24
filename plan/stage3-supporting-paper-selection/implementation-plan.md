# Stage 3 support-paper repair: bounded implementation and verification

Baseline: ScholarWorkflow/professor-contact main 1af814fed6643a27bc1348dcee4d69f13723b253.

Scope frozen before implementation:
1. Enrich existing per-direction generator model_input.supporting_papers with existing paper_facts, facts_state and analysis_level. Do not reopen or rerun Stage 2 or paper analysis. Only valid existing facts may serve as evidence; unavailable or failed facts must not be replaced by title inference.
2. Align idea-generator instructions and job rules: future-work anchors identify extensions, not the entire supporting-paper set. Consider available in-direction facts and include papers only for a concrete foundation, precedent or boundary role. A single paper may suffice; no fixed number, padding or full comparison report.
3. Bump the generator contract version to invalidate old candidate reuse; align current workflow reference and any live verifier constant.
4. Add focused tests in the existing unittest framework for fact propagation/direction isolation/unavailable facts and old-contract regeneration/current-contract reuse, plus retain single-paper candidates without adding zero-paper rejection or style-validator duties.

Verification: focused Stage 3 identity/group/refine/caller tests and current verifier tests only where the constant changes, plus diff whitespace check. No full business regression, model-runtime run, external service, Nix installation, pushes, comments or merge. Report limits explicitly.

Review: independent bounded regular review; eligibility for fast merge is a reviewer decision, not assumed.

Rationale and trade-off: Stage 2 already owns and exports validated facts, so repair only the Stage 3 consumer projection, not Stage 2 or style-validator responsibilities. Unknown/failed facts project as null; facts_state and analysis_level preserve their existing values. This verifies deterministic projection and reuse behavior, not real-model selection quality.

Reviewed scope addition: v1 identity normalization must preserve the original generator contract (missing means null), rather than stamp current v3 onto unregenerated candidates. Include one focused legacy compatibility check; identity/schema migration is unchanged.

Reviewed partial-refresh addition: track generator_contract_version on each generated direction. Direction reuse and direction correction gates in both plan/finalize must check that version, falling back to the original global version for pre-field v2 records. Before finalize retains out-of-scope directions, freeze their original effective version; do not regenerate or delete them. Add a partial-refresh A-then-B regression and a stale-direction correction regression. Existing cross-group scope/schema remain unchanged.

CI registration: add the new module to the existing Stage 3 shard and run scripts/check_test_shards.py; do not expand to all-shard execution.

Wording clarification: valid paper_facts are the basis for inferring additional papers’ research contributions, not a new prerequisite for all paper references. Existing valid gap evidence may still support its source paper under the original rules even when paper_facts are unavailable or failed. No citation validator change.
