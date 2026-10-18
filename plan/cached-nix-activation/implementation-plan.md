# Cached Nix activation — implementation plan r3

Status: candidate for independent review. Upstream merge dependency is resolved; formal plan and merge conclusions are not asserted here. Supersedes r2's temporary waiting state.

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

A direct contact drvPath evaluation reached the shared factory but was blocked by the existing pdf-processing-core input not being available in the cloud cache. This is not a full evaluation pass. The old input pin blocked activation by design; that specific blocker is now removed, while new integration remains unproven.

The common marker is not an integrity scan. Manual changes and direct `agent-env apply/remove` require forced guarded reapplication; installer protection still applies. Updating the shared source pin can change derivation identities even with unchanged installer code; old Darwin store paths must not be presented as new-output evidence.

## Handoff

Independent review covers the exact five-file pin/wiring/docs diff, including the narrow lock change and unchanged factory API. After review publish normally to the same draft PR using the expected head; do not merge. [Test plan t3](test-plan.md) distinguishes current static/source checks, blocked evaluation and historical reuse. No automatic Mac activation, business rerun or additional test machinery.

Historical [r2/t2](https://github.com/ScholarWorkflow/professor-contact/tree/20e044fb52f71d98d894775147242d51c9a07dfe/plan/cached-nix-activation) and the original execution record remain available; do not overwrite their product-specific results.
