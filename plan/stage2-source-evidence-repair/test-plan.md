# Source evidence repair — TP1

- Requirement R1 / execution EP1; product baseline `18fd48d1b6f2e26241c304d6acddb025297f08e4`.
- Proposed review status: pending. Plan-only delivery: no tests executed, no PASS claimed. [Execution plan](execution-plan.md) is the sole design; [review](review.md) records independent conclusions.
- Authority: [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253), [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d), versions recorded in EP1.

## Required checklist (acceptance ceiling)

| Goal / input | Expected business result | Sufficient check |
|---|---|---|
| R-A: One current registered source-owned evidence finding, valid existing cache, changed model_evidence; then normal process/finalize | Only that source evidence changes; affected shortlist/excluded/blacklist views reflect it, including a reused direction; unrelated fields/candidates/status/confidence/narrative unchanged; repair returns needs_refresh and no PASS | One focused existing unittest-style fixture lifecycle through public commands; assert cache and accepted pack fields, rendered evidence and validator state directly |
| R-B: Ineligible fixed quote/template finding and stale repair expected cache/text | Reject with actionable owner/drift result before mutation; no partial batch write or fabricated source | Small command-level negative cases in same product module, assert relevant files unchanged; no combinatorial matrix |
| R-C: Repair followed by normal refresh with manual Markdown change; unchanged repair request | Existing manual-conflict path remains; no-op does not clear accepted validator/rounds or change source | Reuse existing managed-document fixture and direct state/file assertions; no model run |
| R-D: Source instructions and CLI contract | Caller distinguishes eligible model_evidence from fixed scientific facts, resumes normal acceptance and validation, does not bypass PASS or alter candidates | Static review of changed CLI/help, SKILL and affected analyzer sections |

No new model evaluation, Zotero/network, full Stage0–5 regression, installation matrix, source certification, new result parser/framework, all historical U1 tests, or future-work candidate tests. Existing unittest/json assertions are enough. R-A covers successful path and projection; do not repeat it at unit/integration/real-model levels.

## Execution handoff / recipe status

This is a complete test **design**, not a falsely runnable recipe against nonexistent product code. Gate2 remains pending until the product/test owner adds the focused command tests and identifies their exact selectors and fixture preparation below; Gate3 is unexecuted. The test engineer must update this same file rather than require a second manual.

1. Reuse the approved Python environment and existing product unittest/tempfile fixtures in `.apm/skills/professor-contact/tests/`, particularly `test_stage2_style_validation_handoff.py` and U1 fixed-evidence fixtures where applicable. No installation target is added. Record the implementation SHA and interpreter actually used.
2. Product test module will exercise public `contact_state.py stage2-repair-evidence` and normal Stage 2 preparation/finalization using isolated synthetic professor state. Generate legal existing report/ownership state using current fixture helpers, not a new evaluator. Do not touch user data or manually patch installed product behavior.
3. Before Gate2, write exact module/selectors and command, input setup paths, normal process/finalize arguments and expected changed fields for R-A–C. If the existing fixture cannot produce a reuse/blacklist case, adapt only the required producer fixture; do not build general infrastructure.
4. Save command output and first failures below one `/tmp/contact-evidence-repair.*` directory; stdout JSON can be checked by existing unittest assertions or `jq`, not keyword matching. Store only concise non-sensitive results in this plan directory. R-D is static and is not labeled runtime PASS.
5. Missing dependency/fixture is unable-to-judge for its target. No automatic installation, model sampling or unchanged retry. After a concrete setup correction, one retry of the affected command with the same input/expectation; preserve first output. Product failure requires product correction and affected-target rerun, not relaxed assertions. Changed recipe is reviewed for impact before execution.

## Responsibilities / completion

Plan reviewer independently decides design and Gate1. Product/test owner adds implementation and executable recipe; Gate2 reviewer verifies only this checklist's coverage/executability. Execution owner records actual results; independent Gate3 reviewer adopts those results and separates PASS, business failure, unable-to-judge and unexecuted. Existing valid unaffected results are reusable; no reruns merely for docs/review commits. This PR is not merge-ready implementation.
