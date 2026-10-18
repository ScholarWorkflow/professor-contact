# Cached Nix activation — test plan t4

Scope: [implementation plan r4](implementation-plan.md), current product contact `f327f54220d321eb0fce3b3908f86c4ab0914745` with merged shared pin and direct factory wiring. Candidate review status; no formal gate or merge approval asserted. The 2026-10-19 result sync below changes no goal, check or step text relative to t4; it only fact-syncs the result status from the [execution record](test-execution-2026-10-19.md).

## Goals and sufficient checks

| Goal | Check and expected outcome | Current result |
| --- | --- | --- |
| Shared ownership / same consumer entrypoint | Inspect exact `mkCachedActivation` arguments and merged API; old outputs unchanged; no local implementation/testing duplication. | Source inspection matches merged lib/default.nix and factory. |
| Resolved, correctly locked dependency | Verify #4 merged/main SHA, source hash and timestamp; only top-level shared node changes; all other nodes/edges remain equal. | Merge `91861b4f028eda1dbeb41481dcc48cd7c4a60874`; exact-tree hash metadata verified. |
| Shared cache/lock behavior | Reuse upstream's bounded factory/runtime evidence and inspect unchanged interface/semantics; preserve migration and direct apply/remove guidance. | Upstream results reused within their scope; no repeated shared tests. |
| Real Darwin packaging / README consumer (only remaining execution goal) | Build current product → verify `bin/professor-contact-activate` is executable → one isolated README/direnv activation → observe `.agent-env-applied` and `.agents/skills/professor-contact/SKILL.md`. Build includes evaluation; no separate drvPath pass required. | PASS for current product `f327f54220d321eb0fce3b3908f86c4ab0914745`, executed 2026-10-19 following the bounded substitutions in steps 1–5 below; commands, exit results and observed outputs are in the [execution record](test-execution-2026-10-19.md). Original-product results still apply only to that product/unaffected behavior. |

## Existing checks, metadata and historical diagnosis

- GitHub confirmed #4 merged and main at `91861b4f028eda1dbeb41481dcc48cd7c4a60874`; both public factory files were read at that revision.
- Merged source tree `06f46141427da736ff366a86082b50c9d3d77996` equals the archived Git index tree. Existing Nix hash of that source: `sha256-/VgkCnSU4Giw+7P68NMgMnYQ+SHJY45Q8YYxETKqA+w=`. `lastModified=1792341743` is the merge committer timestamp. All non-target lock nodes/edges are unchanged.
- Direct Nix prefetch of the merged GitHub tarball returned HTTP 404. The exact-tree archive supplies verifiable bytes without changing credentials, permissions or the committed github lock source type.
- The contact source used for evaluation was assembled from already cached source; every preexisting blob was checked against GitHub's non-truncated recursive tree for baseline `20e044fb`, and the reviewed candidate files were overlaid. No stub installer, altered dependencies or business sources were substituted.
- Actual command: `nix eval --offline --no-write-lock-file --raw path:/workspace/shared/contact96-merged-eval#packages.aarch64-darwin.professor-contact-activate.drvPath`. It reached derivation `professor-contact-activate` via the shared factory, then exited 1 while accessing the already pinned pdf-processing-core `3444dca0e0b84f46d1839ab5c707afa78e23d3a7` under offline mode and a one-second timeout. This records that attempt only: it neither diagnoses current network availability nor adds an independent remaining gate. Do not rerun it separately; the required build includes evaluation. No full evaluation, build or execution pass is inferred.
- `nix-instantiate --parse flake.nix` and `git diff --check` both exited 0 for the published product candidate (before this documentation-only revision). These are static evidence, never a formal test gate.

## Historical reuse and boundaries

- Original contact product `4d59c0556de113cee554e8879236c9cc378ec826`: five offline methods, syntax/parse and actual aarch64-darwin build plus isolated README-style direnv activation completed on 2026-10-18. Preserve the unchanged [execution record](test-execution-2026-10-18.md) and [original t1](https://github.com/ScholarWorkflow/professor-contact/blob/47a7fe0831418178871d29218e2dc26be9c6119a/plan/cached-nix-activation/test-plan.md). Its t1 line references and completion statements describe that version only.
- Upstream product `c20fd73562e24ef288aa222a9e2e56e961f1894b`, subsequently merged through #4: seven offline methods, actual Linux factory/stub check and Darwin drvPath evaluation documented in [upstream TP1](https://github.com/RekiDunois/agent-env-nix/blob/91861b4f028eda1dbeb41481dcc48cd7c4a60874/plan/cached-activation/test-plan.md). Reuse common behavior evidence; evaluation is not Darwin execution or real contact installation.
- Existing `nix/contact.nix`, APM/business sources, shared installer semantics and other product pins remain unchanged. No full business chain, model/email/Zotero/browser/knowledge-store test, other platform matrix or new test infrastructure is required by this change.
- Old `.professor-contact-applied` is not shared success. Never copy or rename it to fabricate new evidence; preserve first-reapply migration and one composed environment for multiple roots.

## Remaining work and stop conditions

The upstream merge/pin wait is resolved. The only remaining execution goal was the single current-product integration sequence below; it was executed once on 2026-10-19 for `f327f54220d321eb0fce3b3908f86c4ab0914745` with no failed step and no retry, and its results are in the [execution record](test-execution-2026-10-19.md). No standalone drvPath result is needed in addition to build; shared seven-method and factory results remain reused, without new execution.

Use only the **Darwin build and isolated direnv recipe** section of [original t1 at 47a7fe0](https://github.com/ScholarWorkflow/professor-contact/blob/47a7fe0831418178871d29218e2dc26be9c6119a/plan/cached-nix-activation/test-plan.md), with these bounded substitutions and observations:

1. Set `CONTACT_SHA` to the exact current reviewed product revision `f327f54220d321eb0fce3b3908f86c4ab0914745`; if later product changes occur, review their impact and use the newly reviewed product SHA. Subsequent documentation-only commits do not require a different product or repeat run.
2. Reuse the existing aarch64-darwin Nix/direnv setup and immutable caches. Keep t1's fresh external `mktemp` consumer, README flake/shellHook, locked `contact` override, `.envrc = use flake`, and run-scoped `XDG_DATA_HOME`. No real user project, software install, local-path producer input or patched consumer.
3. Build `"$CONTACT_REF#professor-contact-activate"` with t1's isolated out-link, then require `test -x "$RUN/activate/bin/professor-contact-activate"`. This build includes Nix evaluation; do not add a separate drvPath check.
4. Run exactly one real README-style direnv activation in that isolated consumer, replacing t1's old-marker assertion with `direnv exec . sh -c 'test -f .agent-env-applied && test -f .agents/skills/professor-contact/SKILL.md'`. Retain the existing `--project "$PWD"` shellHook. Do not reuse/copy the old contact marker.
5. Record the exact product SHA, run path, commands and exit results, named executable and both observed files. Success means every step in this sequence succeeds. No second activation/cache matrix, old offline wrapper tests or business workflow is added.

Only t1's isolated integration steps are reused; its old one-retry permission is not carried forward, and this document's stop rules govern. Only t1's isolated integration recipe is reused: do not restore `nix/test-activate.py`, its old offline recipe or contact-owned behavior tests. Existing shared seven-method/factory evidence covers those semantics. All current-product integration steps were NOT RUN before 2026-10-19; they are now recorded as executed for `f327f54220d321eb0fce3b3908f86c4ab0914745` in the [execution record](test-execution-2026-10-19.md), with the shared evidence still reused rather than rerun.

Stop at access/dependency failure and preserve evidence; no automatic retry, environment switch, installing software, dependency replacement or broadening scope. Product/recipe failure requires a targeted correction and impact review. Independent reviewers own implementation/test-plan conclusions and formal gates.
