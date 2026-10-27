# Source evidence repair — TP2

- Requirement R2 / execution EP2; product baseline `18fd48d1b6f2e26241c304d6acddb025297f08e4`.
- Proposed review status: pending. Test assets are prepared; no formal target executed, no PASS claimed. [Execution plan](execution-plan.md) is the sole design; [review](review.md) records independent conclusions.
- Authority: [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253), [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d), versions recorded in EP2.

## Required checklist (acceptance ceiling)

| Goal / input | Expected business result | Sufficient check |
|---|---|---|
| R-A: Current registered source-owned findings and valid existing cache; retain the evidence projection case and add one representative partial gap with wording corrections to all three eligible fields, each matched to its registered field; then normal process/finalize | Only the selected wording changes, preserving the fixture's factual meaning; affected shortlist/excluded/blacklist evidence views reflect model_evidence, including a reused direction, while the partial card/pack reflects completed_part and remaining_gap; unrelated data/candidates/status/confidence/narrative unchanged; repair returns needs_refresh and no PASS | Focused existing unittest-style public-command lifecycle; directly assert cache/pack/render/validator state, including evidence/blacklist_evidence mapping. Use a prewritten semantically equivalent partial fixture, not a semantic judge or field-combination matrix |
| R-B: Ineligible fixed quote/template finding and stale repair expected cache/text | Reject with actionable owner/drift result before mutation; no partial batch write or fabricated source | Small command-level negative cases in same product module, assert relevant files unchanged; no combinatorial matrix |
| R-C: Repair followed by normal refresh with manual Markdown change; unchanged repair request | Existing manual-conflict path remains; no-op does not clear accepted validator/rounds or change source | Reuse existing managed-document fixture and direct state/file assertions; no model run |
| R-D: Source instructions and CLI contract | Caller distinguishes the three-field wording whitelist and exact displayed/cache mapping from fixed scientific facts; instructions assign semantic preservation to source owner without claiming automatic proof or promising all other errors are repaired, resumes normal acceptance and validation, does not bypass PASS or alter candidates | Static review of changed CLI/help, SKILL and affected analyzer sections |

No new model evaluation, Zotero/network, full Stage0–5 regression, installation matrix, source certification, new result parser/framework, all historical U1 tests, or future-work candidate tests. Existing unittest/json assertions are enough. R-A covers successful path and projection; do not repeat it at unit/integration/real-model levels.

## Execution handoff / recipe status

Test assets are prepared; Gate2 stays **PENDING** and Gate3 **UNEXECUTED**. This section records the exact selectors, inputs and expected observables for R-A–R-D. It was written by the test engineer in the same PR, so no second manual is needed. Nothing below was run as a formal target: the product entry `stage2-repair-evidence` and the caller-facing documentation of the three-field whitelist do not exist at the prepared baseline, so the runtime targets are expected to fail as **product missing**, not as test defects.

### Prepared assets

- New module: `.apm/skills/professor-contact/tests/test_stage2_source_evidence_repair.py` — `SourceEvidenceRepairTests` (R-A/R-B/R-C, 9 selectors) and `SourceEvidenceRepairContractTests` (R-D, 3 selectors). The selectors are named in the per-target commands below, so no separate index is needed.
- Shard registration: `plan/test-grouping/shards.json` shard4 `{"name": "test_stage2_source_evidence_repair", "stage": "stage2"}`; `python scripts/check_test_shards.py` reports `OK: 83 test modules across 4 shards`.
- Producer fixtures reused unchanged: `test_stage2_fixed_evidence.py` (report recording, managed Markdown, pack, preflight/finalize), `stage2_upstream_fixture.py` (`run_bound_stage2_finalize`), `test_contact_state.py` (`BaseEnv`, `run_cli`, `parse`). The producer module is reached through its module object on purpose, so its six U1 cases are not collected into this plan's shard.
- Prepared baseline: `2b6a824`; interpreter `/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3`.

### Environment

Run from the PR worktree root; every artefact stays below one `/tmp/contact-evidence-repair.*` directory and no test writes into the checkout.

```bash
checkout=$(git rev-parse --show-toplevel)
run_dir=$(mktemp -d /tmp/contact-evidence-repair.XXXXXX)
export TMPDIR="$run_dir"
cd "$checkout/.apm/skills/professor-contact/tests"
git rev-parse HEAD > "$run_dir/target-version.txt"
/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3 --version > "$run_dir/python-version.txt" 2>&1
```

### Per-target commands

`R-A` (three cases, one ordinary `preflight -> plan -> finalize` cycle each), expected 60–120 s:

```bash
/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3 -m unittest -v \
  test_stage2_source_evidence_repair.SourceEvidenceRepairTests.test_r_a_partial_gap_three_field_wording_reaches_the_projection \
  test_stage2_source_evidence_repair.SourceEvidenceRepairTests.test_r_a_blacklist_evidence_projects_the_repaired_model_evidence \
  test_stage2_source_evidence_repair.SourceEvidenceRepairTests.test_r_a_reused_direction_projects_the_repaired_evidence \
  > "$run_dir/r-a.log" 2>&1; printf '%s\n' "$?" > "$run_dir/r-a.exit"
```

`R-B` (four negative cases), expected 40–90 s:

```bash
/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3 -m unittest -v \
  test_stage2_source_evidence_repair.SourceEvidenceRepairTests.test_r_b_finding_on_one_field_does_not_authorize_the_other_fields \
  test_stage2_source_evidence_repair.SourceEvidenceRepairTests.test_r_b_quote_and_generator_findings_keep_their_owner \
  test_stage2_source_evidence_repair.SourceEvidenceRepairTests.test_r_b_stale_expectations_are_rejected_before_writing \
  test_stage2_source_evidence_repair.SourceEvidenceRepairTests.test_r_b_a_batch_with_one_bad_row_writes_nothing \
  > "$run_dir/r-b.log" 2>&1; printf '%s\n' "$?" > "$run_dir/r-b.exit"
```

`R-C` (two cases), expected 40–90 s:

```bash
/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3 -m unittest -v \
  test_stage2_source_evidence_repair.SourceEvidenceRepairTests.test_r_c_manual_markdown_change_keeps_the_conflict_path \
  test_stage2_source_evidence_repair.SourceEvidenceRepairTests.test_r_c_no_op_repair_changes_nothing_and_keeps_the_recorded_rounds \
  > "$run_dir/r-c.log" 2>&1; printf '%s\n' "$?" > "$run_dir/r-c.exit"
```

`R-D` (static: CLI surface plus SKILL and both analyzer projections), expected under 5 s:

```bash
/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3 -m unittest -v \
  test_stage2_source_evidence_repair.SourceEvidenceRepairContractTests \
  > "$run_dir/r-d.log" 2>&1; printf '%s\n' "$?" > "$run_dir/r-d.exit"
```

### Inputs and expected observables

Every case builds an isolated synthetic professor directory with `BaseEnv`; no user data, network, model call or installed-product edit is involved. The producer fixture supplies two gaps: `AAAA1111` (`partial`) and `BBBB2222` (`done_by_self`).

- **R-A1** — record `evidence`, `completed_part`, `remaining_gap` findings on `AAAA1111`, then repair all three cache fields (`后续由`→`后续工作由`, `已完成一部分`→`已完成其中一部分`, `仍缺`→`仍缺少`). Expected: `status=needs_refresh` naming the affected direction and gap; only those three strings change; `status`, `confidence`, `candidate_paper_ids`, both fingerprints, `evaluated_at`, `downgraded` unchanged; `ANALYSIS_MD`, `INPUT_PACK` and the validator bytes unchanged by the command; after preflight `action=process` with `freshness_cache_changed`, plan `reuse`, finalize `ok` with the three repaired strings in the shortlist row and the rendered body, and no validator carried. On the current baseline the projection assertion fails because reuse keeps the old accepted rows — that is the EP2 section B product gap, not a test defect.
- **R-A2** — record `blacklist_evidence` on `BBBB2222` (`已接住该点`→`已接住了该点`) and repair its `model_evidence`. Expected: `needs_refresh`; the completed-gap blacklist row's `evidence` shows the new text while `completed_by_item_key`, `candidate_paper_ids`, title, year, confidence and `evaluated_at` stay unchanged; the rendered `接住（依据：…）` line carries it; the partial gap of the same direction keeps its own evidence.
- **R-A3** — two directions (`DIR00001`, `DIR00002`) both accepting the same partial gap; the report quotes only the first of the two identical `- 后续论文依据：` lines, so `fixed_blocking` names `DIR00001` only; repair `AAAA1111` `model_evidence`. Expected: `needs_refresh`; preflight `process`; plan `reuse` for both directions; finalize `ok`; both shortlist rows and both rendered `- 后续论文依据：` lines show the new text; the accepted narrative is unchanged.
- **R-B1** — only `model_evidence` registered, request `completed_part` and `remaining_gap`. Expected: non-zero exit with the product's error payload carrying more than `status`/`reason_code`, so the caller learns something it can act on; every file byte-identical.
- **R-B2** — a `quote` finding (`owner=source`) and a `label` finding (`owner=generator`), each followed by a `model_evidence` request. Expected: both refused; the generator case names `generator` so the caller is sent to the right owner; every file byte-identical.
- **R-B3** — stale `expected_cache_sha256`, stale `expected_validation_sha256`, and a wrong `expected_old_text`. Expected: three separate refusals, each with an actionable payload, every file byte-identical.
- **R-B4** — a two-row batch whose second row is unauthorized, then a batch with two rows for the same direction/gap/field. Expected: both batches refused; no partial write, no last-row-wins; every file byte-identical.
- **R-C1** — terminal validator, repair `model_evidence`, then a manual `- 页码：p.8` → `- 页码：p.9（人工改写）` edit before finalize without `--decision-file`. Expected: either `needs_decision` or `error/validation_render_stale`; the Markdown bytes and the recorded validator stay unchanged. The explicit `{"decision": "overwrite"}` file then resolves it: exit 0, the manual marker gone, the repaired text rendered, validator dropped.
- **R-C2** — the unchanged repair request of TP2 R-C, exercised on an exhausted review: a narrative round 1 is refined, then round 2 lands on the source-owned evidence line and closes as `terminal` / `round 2` / `fail_after_2_rounds`. A repair row whose replacement equals the current text is then submitted. Expected: no cache, Markdown, pack or validator byte change and no reset of the recorded rounds — a no-op is not a new source version.
- **R-D** — `stage2-repair-evidence --help` exposes `--professor-dir` and `--repair-file`; `SKILL.md` and both `professor-contact-analyzer.agent.md` bodies document the three-field whitelist, the `evidence`/`blacklist_evidence` → `model_evidence` mapping, `needs_refresh`, that one field's finding does not authorize the other two, and that a fresh validation is still required. Static evidence only, never a runtime PASS.

### Failure handling

- A missing product entry (`argparse: invalid choice`, exit 2, no JSON) is a **product-missing failure** for its runtime target; the module reports it as such and does not weaken the assertion.
- A missing dependency or fixture is **unable-to-judge** for that target. No automatic installation, model sampling or unchanged retry; after one concrete setup correction the affected command may be retried once with the same input and expectation, keeping the first output.
- A product failure needs a product correction and a rerun of the affected targets only; assertions are never relaxed to reach green. First failures stay in `$run_dir`.
- Expected result at the prepared baseline: the nine runtime cases fail at the absent subcommand and the three static cases fail on the absent documentation sections — 18 reported failures from 12 selectors, because the documentation cases and the stale-expectation case use `subTest`; R-C's overwrite branch and every other case are blocked behind the same missing entry.

### Preparation and precheck record

Limited precheck only — no formal target was executed and no PASS is claimed:

- `py_compile` on the new module: passed.
- `unittest` collection of the new module: 12 selectors (`SourceEvidenceRepairTests` 9, `SourceEvidenceRepairContractTests` 3), no U1 case imported.
- Fixture smoke through the producer helpers in an isolated synthetic professor directory: pack generation, finding recording, and the registered `fixed_blocking` owner/field rows confirmed as `evidence`, `completed_part`, `remaining_gap`, `blacklist_evidence` (`owner=source`), `quote` (`owner=source`) and `label` (`owner=generator`).
- Fixture smoke of the reused two-direction and manual-edit paths on the prepared baseline: plan reports `reuse` for both directions, and a hand-edited managed body yields `error/validation_render_stale` with unchanged bytes until `{"decision": "overwrite"}` is supplied. This confirms the recipe's inputs are producible; it is not a result for the repair targets.
- `python scripts/check_test_shards.py`: `OK: 83 test modules across 4 shards, each with a stage`.
- `python scripts/check_test_shards.py --print shard4` lists `test_stage2_source_evidence_repair`.
- One trial run of the new module was made during preparation to confirm the failure cause, not to obtain a result: 12 tests, 18 reported failures, all of them the absent subcommand (11) or the absent documentation sections (7). No target is recorded as passing, and no PASS is claimed.
- Fixture hygiene was checked directly: the two-direction helper produces two distinct temporary professor directories and both are removed on teardown, so a run leaves nothing behind.
- Missing item that blocks Gate2: the product `stage2-repair-evidence` subcommand and the SKILL/analyzer documentation of its three-field whitelist. Next owner: the local execution engineer runs R-A–R-D once the product lands.

## Responsibilities / completion

Plan reviewer independently decides design and Gate1. Product/test owner adds implementation and executable recipe; Gate2 reviewer verifies only this checklist's coverage/executability. Execution owner records actual results; independent Gate3 reviewer adopts those results and separates PASS, business failure, unable-to-judge and unexecuted. Existing valid unaffected results are reusable; no reruns merely for docs/review commits. This PR is not merge-ready implementation.

