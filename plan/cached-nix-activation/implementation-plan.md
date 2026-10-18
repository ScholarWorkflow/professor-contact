# Cached Nix activation — implementation plan r2

Status: pending independent review and upstream merge. This revision supersedes r1 for current product work; it does not grant plan approval or merge readiness.

## Requirement and baseline

- 2026-10-18: refactor professor-contact #96 to use agent-env-nix #4's shared `mkCachedActivation`. Preparing the dependency as waiting for #4 is explicitly allowed; fill in the merged revision later.
- Contact baseline: `47a7fe0831418178871d29218e2dc26be9c6119a`, branch `feat/cached-nix-activation`; original product `4d59c0556de113cee554e8879236c9cc378ec826`.
- Upstream candidate: [agent-env-nix #4](https://github.com/RekiDunois/agent-env-nix/pull/4), inspected head `472fdee073f0b899d4f47737a6471766fbe9f725`, product `c20fd73562e24ef288aa222a9e2e56e961f1894b`. It is unmerged; the current released pin `2158e933aab6c845ae1ceb1228458d624f8777d5` does not export the factory.
- Rules: [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d), [Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c), [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253).

## Ownership, implementation and invariants

1. Replace the local import with `agent-env-nix.lib.mkCachedActivation { inherit pkgs; environment = products.project; name = "professor-contact-activate"; }`. Keep `packages.aarch64-darwin.professor-contact-activate`, its executable name, `--project` (default caller directory), `--force`, and the existing environment output.
2. Delete `nix/activate.nix`, `nix/activate.sh`, and `nix/test-activate.py`. Shared factory/runtime/tests own successful-cache identity, CDPATH-safe physical paths, failure invalidation, locking and atomic publication. Contact owns only the environment and named export; do not copy shared behavior or tests back here.
3. Preserve the current released input pin and lock. While its lib lacks the factory, the new output throws an explicit pending-upstream diagnostic. Nix's lazy attribute evaluation leaves existing package/runtime/environment outputs unchanged; broad evaluation that forces the new output is blocked. No placeholder SHA, unmerged-branch pin, vendored fallback or temporary lock churn.
4. Use the shared `.agent-env-applied` and `.agent-env-apply.lock`. Do not migrate the old marker as success: first shared activation reapplies. Old and new commands must not run concurrently. Multiple roots must be composed into one `mkProject` environment before wrapping; independently activated environments replace each other.
5. Update README for pending consumption, shared ownership, marker/lock migration, direct apply/remove and manual-edit cache boundaries. Keep APM, business behavior, platform support and all existing dependencies unchanged in this candidate. Do not modify upstream #4 or Study.

## Alternatives and risk

Keeping the local wrapper would retain duplicated ownership; pinning #4's branch would make an unmerged candidate look like a released dependency and create avoidable lock churn. Deferring all code would leave the requested refactor unprepared. The explicit lazy failure is the smallest candidate wiring: intentionally unavailable new output, no behavior fallback and no claim of build success. The factory interface can still change before merge, so its final name/arguments/semantics must be rechecked.

The common marker is not an installation integrity scan. Manual changes and direct `agent-env apply/remove` require forced guarded reapplication before trusting the cache again. Existing installer configuration protection still applies, including under `--force`.

## Completion and handoff

- Now: independent candidate review, necessary static wiring/parse checks only, then normal expected-head publication to the same draft PR; no merge or formal approval asserted.
- Waiting: #4 must actually merge. Verify its merged commit and public factory interface; update contact's input to a real merged revision containing the interface, refresh only the affected lock graph, and review that diff. Do not use the current candidate SHA as a fictional future merge SHA.
- Then: reassess only affected integration evidence under [test plan t2](test-plan.md). No automatic Mac activation, broad rerun, business execution, or CI expansion is authorized by this document.
- Historical r1 and original results remain available at [baseline plans](https://github.com/ScholarWorkflow/professor-contact/tree/47a7fe0831418178871d29218e2dc26be9c6119a/plan/cached-nix-activation); retain the original execution record unchanged.
