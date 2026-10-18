# Cached Nix activation — test plan t2

Scope: [implementation plan r2](implementation-plan.md), contact #96 at baseline `47a7fe0831418178871d29218e2dc26be9c6119a` plus shared-factory refactor. Status: pending review and upstream #4 merge. This plan records affected evidence boundaries; it does not authorize a new formal test run or assign any test gate PASS.

## Goals and sufficient checks

| Goal | Check and expected outcome | Current status |
| --- | --- | --- |
| Shared ownership and preserved consumer entrypoint | Inspect flake diff: factory receives `pkgs`, `products.project`, `name = "professor-contact-activate"`; local wrapper/package/tests removed; old environment export and pins unchanged. Parse changed Nix; compare factory interface with upstream #4. | Static candidate inspection only. |
| Honest pending dependency | Current released input lacks factory; missing-attribute fallback explicitly throws only when new output is forced. No fabricated merged SHA or branch pin; existing outputs retain lazy independence. | Deliberately pending; new export cannot build with current pin. |
| Shared cache/lock behavior | Reuse upstream's bounded factory/runtime tests rather than cloning them. Review shared `.agent-env-applied` / `.agent-env-apply.lock`, one-environment composition, direct apply/remove and old-marker migration guidance. | Upstream candidate evidence is available; final merged interface/revision still to verify. |
| Real contact packaging and README-style consumption after final pin | Reassess the changed factory boundary against old contact and shared results. If a new integration run is required and authorized, build the exact reviewed final contact export and use one fresh isolated README consumer; observe executable, shared marker and installed contact SKILL.md. | New shared contact wiring has not been built or activated. Current pin blocks it. No run starts in this revision. |

## Existing results and reuse

- Original contact product `4d59c0556de113cee554e8879236c9cc378ec826`: five offline wrapper methods and syntax/parse records; real aarch64-darwin build and isolated README-style direnv activation were completed on 2026-10-18. See the unchanged [execution record](test-execution-2026-10-18.md) and [original t1](https://github.com/ScholarWorkflow/professor-contact/blob/47a7fe0831418178871d29218e2dc26be9c6119a/plan/cached-nix-activation/test-plan.md). Those results remain valid for that product and unaffected behavior. They are not new shared-factory integration results.
- Shared product `c20fd73562e24ef288aa222a9e2e56e961f1894b`, documented by [upstream TP1](https://github.com/RekiDunois/agent-env-nix/blob/472fdee073f0b899d4f47737a6471766fbe9f725/plan/cached-activation/test-plan.md): seven offline methods and Linux actual-factory stub check passed; Darwin drvPath evaluation passed. These cover the common algorithm and default/custom names. Evaluation is not Darwin execution or real contact installation.
- No business owner, `nix/contact.nix`, installer implementation or other product dependency changes in this candidate. Reuse unaffected original results; do not rerun a full business chain, model, email, Zotero, browser, knowledge-store workflow, or introduce test infrastructure.
- The historical record's t1 line references and overall per-item completion statements describe t1 at its recorded commit, not t2. The old `.professor-contact-applied` must never be copied/renamed to fabricate new shared success.

## Current permitted static checks

Use the existing cloud Nix parser for `flake.nix` and `git diff --check`. Inspect exact source against the stated factory interface and old output bindings; no Nix build, real apply, Mac access, software install or mutable consumer test is part of this revision. Record parse/whitespace results as static evidence, never as a test gate or integration pass.

## Deferred integration procedure and stop conditions

1. Wait for #4 to merge; verify merged public interface, update the actual contact dependency pin and affected lock entries, and freeze the exact final reviewed contact SHA. A changed upstream interface requires revisiting the wiring before execution.
2. Review affected goals and existing evidence first. If an integration run is still needed, obtain the required environment/execution authorization and applicable plan/step review. Reuse existing immutable caches and tools; do not install software or touch a user's working project.
3. Adapt the original t1 isolated recipe only at the changed boundary: set `CONTACT_SHA` to the real final reviewed commit, build `professor-contact-activate`, retain the same README consumer/shellHook, and check `.agent-env-applied` plus `.agents/skills/professor-contact/SKILL.md` in a fresh isolated project. Preserve the executable name and `--project "$PWD"`; never use the old marker as proof. Record SHA, commands, exit results and observed outputs.
4. Stop on missing dependency, permission/tool access or failed step; preserve logs and distinguish dependency inability from product failure. No automatic retry or switch to a different computer; decide any needed correction/retry against the specific failure before running it. No other platforms, roots matrix or business-chain run is implied.

The final pin/lock and new integration evidence are pending, not silently waived. Independent reviewers own implementation/test-plan conclusions and all formal gates; this author supplies no APPROVED or G3 PASS.
