# Stage 2 source evidence repair — execution plan

- Requirement revision: R1, user 2026-10-26 17:46 UTC: separate item 2 (source evidence repair entry) from display fixes and prepare execution/test plans.
- Plan revision: EP1. Proposed review status: pending. This PR changes plans only; no implementation, execution or merge is claimed.
- Target: `ScholarWorkflow/professor-contact`, baseline `18fd48d1b6f2e26241c304d6acddb025297f08e4`.
- Canonical companion: [test-plan.md](test-plan.md). Review verdicts belong only in [review.md](review.md).
- Rules: [Plan Reviewer](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c) (2026-10-09 20:13 UTC), [Test Engineer](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) (2026-10-09 20:37 UTC), [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d) (2026-10-26 04:11 UTC); full texts read for this plan.

## Requirement and limits

Provide a supported, narrowly scoped source-owner entry to correct the **text of `model_evidence` in the professor-local freshness cache** after a registered fixed-evidence finding. Normal Stage 2 acceptance then projects the corrected evidence into the affected pack rows and rendered report. This is not candidate-paper selection repair: `candidate_paper_ids`, freshness status, confidence, gap identity, source quotations and other scientific facts stay unchanged.

The existing [PR107 U1 plan](https://github.com/ScholarWorkflow/professor-contact/blob/b4e93542e013f0b8824eb682e10a1832b75729b8/plan/stage2-fixed-evidence/implementation-plan.md), especially §3.3, remains authoritative for fixed evidence protection, registered failures and normal acceptance. The new user request adds this bounded source repair entry; it does not permit narrative refine to rewrite fixed facts. [PR137](https://github.com/ScholarWorkflow/professor-contact/pull/137) only changes renderer/style responsibilities; it is not authorization for source editing. This work is independent of display fixes, human round continuation, and PR143 future-work handoff. No Stage 3–5, new gap discovery, new model judgement, author-quote rewriting, cache-wide reset, statistics, general migration framework or provenance certification.

The reattached diff (`libfile_9e63e048ebe08191b3ea16dece4aa083`, read 2026-10-26) is not an implementation baseline: its new repair/continuation modules are only first-80-line previews (194/252 total lines). The following is a new proposed solution grounded in the repository below; helper/CLI names are proposed, not claims that code already exists.

## Facts → decisions (all source links fixed to baseline)

1. [`_stage2_validation.py`](https://github.com/ScholarWorkflow/professor-contact/blob/18fd48d1b6f2e26241c304d6acddb025297f08e4/.apm/skills/professor-contact/scripts/_stage2_validation.py) registers `fixed_blocking` by direction/gap/field/owner and makes both refine entries stop before producing or consuming jobs. **Decision:** the new entry consumes the existing registered report and current binding; it never changes those permissions or turns a failure into PASS.
2. [`_stage2_facts.py`](https://github.com/ScholarWorkflow/professor-contact/blob/18fd48d1b6f2e26241c304d6acddb025297f08e4/.apm/skills/professor-contact/scripts/_stage2_facts.py), `load/save_freshness_cache`, `Stage2Context.freshness_entry`: cache is professor-local `论文分析/_freshness_cache.json`; a reusable record matches gap and candidate fingerprints and valid status. **Decision:** preserve record identity and fingerprints, edit only the explicitly selected evidence text, and rely on existing freshness applicability during ordinary processing. Missing/malformed records are not created by this repair.
3. [`_stage2_finalize.py`](https://github.com/ScholarWorkflow/professor-contact/blob/18fd48d1b6f2e26241c304d6acddb025297f08e4/.apm/skills/professor-contact/scripts/_stage2_finalize.py), `stage2_checked_gap_statuses`, reused-entry assembly, `stage2_old_pack_gap_statuses` and ordinary acceptance: reused entries can carry old evidence, while checked statuses already expose valid cache records. **Decision:** add a targeted projection before ordinary rendering, including the reuse branch, rather than patching the Markdown or input pack in the repair command.
4. [`_stage2_preflight.py`](https://github.com/ScholarWorkflow/professor-contact/blob/18fd48d1b6f2e26241c304d6acddb025297f08e4/.apm/skills/professor-contact/scripts/_stage2_preflight.py) and finalize already compare freshness views, old business/body state and validator binding. **Decision:** changed source text follows normal `preflight → process → finalize`; only ordinary acceptance may invalidate stale validation. Preserve manual-edit conflict handling and unchanged-state reuse.

## Frozen design and ownership

### A. Source-owner repair command

Add `stage2-repair-evidence --professor-dir DIR --repair-file FILE` to `contact_state.py`, with a small adjacent helper following existing explicit factory injection. Source owner supplies the corrected text; the command does not call a model or invent facts. JSON input contains schema 1 and repairs, each identifying `direction_id`, `gap_id`, `field="model_evidence"`, the expected old evidence and replacement evidence. It also names the current registered validation digest and expected cache digest, for stale-write detection, not identity certification. No arbitrary paths or arbitrary field updates in a repair row.

Before writing anything:
- Load the current managed input pack and registered validator using existing bound-render/pack checks. Require a matching registered fixed blocking source-owner row for that direction/gap whose displayed `evidence` maps to this cache's `model_evidence`. A source quote, completed_part, remaining_gap, template/generator issue or unregistered gap is outside this entry; return the actual owner without mutation.
- Require the corresponding cache record, matching gap identity and expected old text; verify current cache digest. Validate the complete repair batch before writing. Duplicate/conflicting rows reject rather than last-wins; unchanged replacement is a no-op.
- Deep-copy the cache document and replace only targeted `model_evidence`; preserve all unrelated entries, metadata and protected fields exactly. Use the existing atomic JSON replacement convention. Require exclusive use of this professor's Stage 2 write flow during this operator action; if an active writer/lease is observable through the existing writer guard, refuse. Re-read the expected pack/cache binding immediately before commit and stop on detected drift. Do not introduce a cross-workflow transaction/locking service or claim this detects an uncoordinated external edit after the last check.

Successful changed write returns `needs_refresh` and the affected direction/gap list, not PASS, corrected-validator, or completed Stage 2. It does not edit Markdown, the accepted input pack, validator histories, raw reports or resolved decisions. If the single cache replacement fails, report failure without claiming source repair; a successful replacement followed by later workflow failure remains an explicit pending refresh, not a rollback of history.

### B. Normal acceptance and targeted projection

In `_stage2_finalize.py`, use the existing checked-cache applicability path during ordinary candidate assembly. For each affected gap appearing in shortlist, excluded gaps or completed-gap blacklist, project `model_evidence → evidence` only from the still-valid record for that exact gap. Match existing accepted row identity and protected status/candidate facts before projection; a mismatch belongs to normal source regeneration, not a silent repair. Never infer candidates or identity from natural-language text. Apply to copied candidate entries, including reused/resolved directions, never mutate the old accepted snapshot.

All rows referencing the same cache-owned gap receive the same current evidence; unrelated gaps/narratives remain unchanged. Existing renderer, trusted citations, ownership map, manual edit protection, membership/resolve authority and ordinary body/business-change validation invalidation remain owners of their current responsibilities. No change to `candidate_paper_ids`, confidence, status, completed-by identity, completed_part/remaining_gap, author excerpts/translations/pages, user notes or red lines.

After the cache edit, caller reruns normal preflight with current source inputs; stale preflight/facts/resolved evidence is not re-signed by the repair command. Finalize refreshes the accepted source projection and render through its existing acceptance checks. Existing raw report remains available. The new accepted artifact must get an ordinary fresh validator result; a repaired string is never evidence of a passing review. No change/no-op cannot reset exhausted rounds.

### C. Compatibility, failure and rollout

- Existing cache/pack files remain readable. A missing U1 ownership map or ambiguous legacy mapping returns an actionable normal-refresh/source-owner requirement; do not reverse-engineer Markdown or bulk migrate files.
- Repair inputs are opt-in; ordinary Stage 2 remains unchanged except consuming current valid source evidence rather than stale projected text.
- Work is professor-local. Agent documentation instructs callers to stop on fixed evidence, obtain a source-owner correction, invoke this entry only for eligible model evidence and then resume the normal path. A display-only bug remains renderer-owned.
- Alternative: hand-edit cache then rerun. It has no supported scope/stale-input checks and invites editing protected fields. A general source-editor or direct pack/Markdown rewrite would duplicate authority and bypass acceptance; reject that alternative. The narrow source operation plus ordinary acceptance reuses existing owners.

## Invariants and representative counterexamples

- Registered failure is not edit authority for every field: a quote/source excerpt issue cannot change model_evidence merely because both have owner=source.
- Same gap in several resolved views: update its valid projected evidence consistently, never another gap or professor; do not change membership to make mapping fit.
- Stale repair or changed source: expected old text/cache binding mismatch rejects without partial batch write; ordinary freshness mismatch does not bless a stale cache.
- Fixed block plus narrative issue: source repair does not reopen automatic narrative refine or declare PASS; ordinary acceptance and validator remain necessary.
- No-op/time-only invocation: no source/accepted-version change, no reset of failure/round state.
- Critical assumptions: none about the incomplete local implementation. Proposed operator serialization is explicit; uncoordinated external writes are not a new supported concurrency contract. If implementation needs a broader concurrency guarantee, return the requirement question rather than silently building a new framework.

## Ordered implementation handoff

1. Independent plan review; separate test design/Gate1 confirmation. This plan PR does not implement or run anything.
2. Product owner adds the narrow source command and input checks, then the ordinary finalize projection; keeps both changes together so a repair can actually reach the report.
3. Update SKILL and directly affected analyzer instructions with eligibility, `needs_refresh` and normal resume steps; no unrelated prompt rewrite.
4. Test owner supplies the TP1 focused executable recipe against the resulting implementation, obtains Gate2, and runs only approved targets. Preserve unaffected results; a documentation SHA alone is not a rerun reason.
5. Independent reviewer evaluates implementation and results. Do not self-approve or merge. Product implementation, exact runnable test selectors and formal execution remain pending after this plan-only PR.
