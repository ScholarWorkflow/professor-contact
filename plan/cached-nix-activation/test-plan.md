# Cached Nix activation — test plan t3

Scope: [implementation plan r3](implementation-plan.md), baseline contact `20e044fb52f71d98d894775147242d51c9a07dfe` plus actual merged upstream pin and removal of pending wiring. Candidate review status; no formal gate or merge approval asserted.

## Goals and sufficient checks

| Goal | Check and expected outcome | Current result |
| --- | --- | --- |
| Shared ownership / same consumer entrypoint | Inspect exact `mkCachedActivation` arguments and merged API; old outputs unchanged; no local implementation/testing duplication. | Source inspection matches merged lib/default.nix and factory. |
| Resolved, correctly locked dependency | Verify #4 merged/main SHA, source hash and timestamp; only top-level shared node changes; all other nodes/edges remain equal. | Merge `91861b4f028eda1dbeb41481dcc48cd7c4a60874`; exact-tree hash metadata verified. |
| Contact factory can evaluate with its real environment | One offline/no-write-lock drvPath evaluation against the updated actual contact source and lock. | BLOCKED by unavailable existing pdf-processing-core source; no drvPath result claimed. |
| Shared cache/lock behavior | Reuse upstream's bounded factory/runtime evidence and inspect unchanged interface/semantics; preserve migration and direct apply/remove guidance. | Upstream results reused within their scope; no repeated shared tests. |
| Real Darwin packaging / README consumer | Reassess changed packaging boundary against old contact and shared evidence. Any new execution requires the corresponding environment/steps authorization. | New shared contact Darwin build and real direnv activation NOT RUN. Original-product results remain valid only for that product/unaffected behavior. |

## Current checks and metadata

- GitHub confirmed #4 merged and main at `91861b4f028eda1dbeb41481dcc48cd7c4a60874`; both public factory files were read at that revision.
- Merged source tree `06f46141427da736ff366a86082b50c9d3d77996` equals the archived Git index tree. Existing Nix hash of that source: `sha256-/VgkCnSU4Giw+7P68NMgMnYQ+SHJY45Q8YYxETKqA+w=`. `lastModified=1792341743` is the merge committer timestamp. All non-target lock nodes/edges are unchanged.
- Direct Nix prefetch of the merged GitHub tarball returned HTTP 404. The exact-tree archive supplies verifiable bytes without changing credentials, permissions or the committed github lock source type.
- The contact source used for evaluation was assembled from already cached source; every preexisting blob was checked against GitHub's non-truncated recursive tree for baseline `20e044fb`, and the reviewed candidate files were overlaid. No stub installer, altered dependencies or business sources were substituted.
- Actual command: `nix eval --offline --no-write-lock-file --raw path:/workspace/shared/contact96-merged-eval#packages.aarch64-darwin.professor-contact-activate.drvPath`. It reached derivation `professor-contact-activate` via the shared factory, then exited 1 while fetching the already pinned pdf-processing-core `3444dca0e0b84f46d1839ab5c707afa78e23d3a7` (missing cache / timeout). Stop this item; no full evaluation, build or execution pass is inferred. No automatic network retry or dependency override.
- `nix-instantiate --parse flake.nix` and `git diff --check` both exited 0 for the current candidate. These are static evidence, never a formal test gate.

## Historical reuse and boundaries

- Original contact product `4d59c0556de113cee554e8879236c9cc378ec826`: five offline methods, syntax/parse and actual aarch64-darwin build plus isolated README-style direnv activation completed on 2026-10-18. Preserve the unchanged [execution record](test-execution-2026-10-18.md) and [original t1](https://github.com/ScholarWorkflow/professor-contact/blob/47a7fe0831418178871d29218e2dc26be9c6119a/plan/cached-nix-activation/test-plan.md). Its t1 line references and completion statements describe that version only.
- Upstream product `c20fd73562e24ef288aa222a9e2e56e961f1894b`, subsequently merged through #4: seven offline methods, actual Linux factory/stub check and Darwin drvPath evaluation documented in [upstream TP1](https://github.com/RekiDunois/agent-env-nix/blob/91861b4f028eda1dbeb41481dcc48cd7c4a60874/plan/cached-activation/test-plan.md). Reuse common behavior evidence; evaluation is not Darwin execution or real contact installation.
- Existing `nix/contact.nix`, APM/business sources, shared installer semantics and other product pins remain unchanged. No full business chain, model/email/Zotero/browser/knowledge-store test, other platform matrix or new test infrastructure is required by this change.
- Old `.professor-contact-applied` is not shared success. Never copy or rename it to fabricate new evidence; preserve first-reapply migration and one composed environment for multiple roots.

## Remaining work and stop conditions

The upstream merge/pin wait is resolved. Current remaining evidence is the blocked real-contact evaluation and unexecuted new Darwin integration. Do not turn these into passes or automatically repeat unaffected tests.

If the missing original input becomes available, reconsider the same scoped evaluation with unchanged candidate and lock. Any later Darwin integration should use the actual final reviewed contact SHA and the original t1 isolated README recipe, changing the observed success marker to `.agent-env-applied`; observe the named executable and installed contact SKILL.md. It requires suitable environment and steps authorization before execution; do not start a Mac or touch a user project now.

Stop at access/dependency failure and preserve evidence; no automatic retry, environment switch, installing software, dependency replacement or broadening scope. Product/recipe failure requires a targeted correction and impact review. Independent reviewers own implementation/test-plan conclusions and formal gates.
