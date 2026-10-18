# Cached Nix activation — implementation plan r4

Status: candidate for independent review. Upstream merge dependency is resolved; formal plan and merge conclusions are not asserted here. This documentation-only revision narrows the remaining integration check; product remains `f327f54220d321eb0fce3b3908f86c4ab0914745`.

## Requirement and baseline

- 2026-10-18: refactor contact #96 to shared `mkCachedActivation`; initially wait for agent-env-nix #4, then complete the real merged pin and wiring when it lands.
- Contact baseline: `20e044fb52f71d98d894775147242d51c9a07dfe`, branch `feat/cached-nix-activation`. Original local-wrapper product: `4d59c0556de113cee554e8879236c9cc378ec826`.
- [agent-env-nix #4](https://github.com/RekiDunois/agent-env-nix/pull/4) is actually merged. Merge and main verified as `91861b4f028eda1dbeb41481dcc48cd7c4a60874`; public interface remains `mkCachedActivation { pkgs, environment, name ? "agent-env-activate" }`.
- Rules: [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d), [Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c), [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253).

## Implementation and ownership

1. Pin `agent-env-nix` to the actual merge above in `flake.nix` and only the top-level `agent-env-nix` node of `flake.lock`. Preserve all other nodes, follows edges and owner-controlled nested agent-env pins. The merged upstream input graph is unchanged.
2. Remove the lazy pending throw. Call `agent-env-nix.lib.mkCachedActivation { inherit pkgs; environment = products.project; name = "professor-contact-activate"; }` directly. Preserve the exported package/executable, `--project`, `--force`, and old environment/runtime/package bindings.
3. Continue the r2 deletion of local `nix/activate.nix`, `nix/activate.sh`, `nix/test-activate.py`. The shared owner supplies cache semantics, physical path/CDPATH safety, failure invalidation, lock and atomic marker publication. Contact only supplies its environment and command name.
4. Preserve shared `.agent-env-applied` / `.agent-env-apply.lock` and documented migration: old contact marker cannot certify shared success; first shared activation reapplies; old/new commands must not run concurrently. Multiple roots must be composed into one environment before wrapping.
5. Update README and plans to resolved upstream state, without claiming actual new Darwin execution. Do not modify APM/business sources, other products, shared repository, Study, platform support or CI.

## Metadata and risk

The merged Git tree `06f46141427da736ff366a86082b50c9d3d77996` was verified against the exact local Git index tree and archived without checkout artifacts. Nix recursive hash of that archive is `sha256-/VgkCnSU4Giw+7P68NMgMnYQ+SHJY45Q8YYxETKqA+w=`; merge committer time supplies `lastModified = 1792341743`. This is actual merged-source metadata, not a branch pin or guessed hash. A direct Nix GitHub prefetch returned HTTP 404; no credentials or access settings were changed.

A prior contact drvPath evaluation reached the shared factory, then exited 1 with an unavailable cached pdf-processing-core input under offline mode and a one-second timeout. Keep this as historical diagnostic evidence, not a current network diagnosis or an independent remaining pass condition. The scoped build below already includes evaluation. The old pending input-pin blocker is removed. The current-product build and the single real activation were executed on 2026-10-19 for `f327f54220d321eb0fce3b3908f86c4ab0914745` and their results are in the [execution record](test-execution-2026-10-19.md); this status sentence is the only part of r4 fact-synced after that execution, and the requirements above are unchanged by the sync.

The common marker is not an integrity scan. Manual changes and direct `agent-env apply/remove` require forced guarded reapplication; installer protection still applies. Updating the shared source pin can change derivation identities even with unchanged installer code; old Darwin store paths must not be presented as new-output evidence.

## Handoff

This revision changes only the two plans and PR description, based on published product `f327f54220d321eb0fce3b3908f86c4ab0914745`; no product, lock or test files change. After independent review publish normally to the same draft PR using the expected head; do not merge. [Test plan t4](test-plan.md) keeps one remaining integration sequence: build the current product, verify the named executable, and activate once in an isolated README-style direnv consumer, observing the shared marker and contact SKILL.md. Reuse existing shared tests; do not add a standalone drvPath rerun. Actual execution requires separately arranged environment/steps authorization; no Mac activation or business rerun was performed in that documentation-only revision. The execution carried out later on 2026-10-19 is recorded separately and does not change this handoff.

Historical [r2/t2](https://github.com/ScholarWorkflow/professor-contact/tree/20e044fb52f71d98d894775147242d51c9a07dfe/plan/cached-nix-activation) and the original execution record remain available; do not overwrite their product-specific results.
