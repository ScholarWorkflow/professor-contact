# Cached Nix activation — implementation plan r1

- Requirement revision: 2026-10-18 request to keep the activation script in this repo's `nix/` and call the Nix-built entrypoint from the consumer shellHook; subsequent review identifies relative `--project` being redirected by inherited `CDPATH`.
- Target: ScholarWorkflow/professor-contact PR #96; baseline `ae890491e4bdd7e95ec4ffee5a48cbf28af14ec3`, based on main `74bd29b572c1b3f68f230a554f57d0202e54cde8`.
- Proposed review status: pending. This is the single complete implementation plan for this feature, including the CDPATH correction; it does not retroactively claim plan approval or merge readiness.
- Rules: [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d), [Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c), [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253).

## Scope and ownership

Add `professor-contact-activate` only for aarch64-darwin/Codex. Its optional `--project` defaults to the calling directory; relative values must refer to that directory. It applies on first use, environment output change, project move or `--force`, and skips repeated successful installation of the same environment into the same physical project. Unknown arguments and invalid marker types fail clearly. Failed apply must not leave valid cached success.

The contact repository owns this wrapper, its marker and its lock. The existing shared installer owns installation, conflict protection, MCP merging and GC roots. Preserve the existing `professor-contact-environment` export and its `agent-env apply --project` interface, dependency pins, APM sources and all business behavior. Do not modify agent-env-nix, copy its installer, add Linux/Intel support, scan/hash installed trees, silently repair user projects, or expand CI/business tests.

## Decisions and grounding

1. **Wrap the existing environment:** `flake.nix` at the baseline exports `products.project`; `nix/contact.nix` constructs it with `mkProject`. The pinned [installer at 2158e933](https://github.com/RekiDunois/agent-env-nix/blob/2158e933aab6c845ae1ceb1228458d624f8777d5/runtime/activate.sh) supplies the existing apply behavior. Therefore `nix/activate.nix` packages the source shell script with fixed Bash, GNU coreutils and environment paths; `flake.nix` adds an export without changing the old export.
2. **Own successful completion:** the shared installer records schema/roots before all installation work completes; those artifacts do not certify success. The wrapper records environment store path plus physical project path only after apply returns success. Its marker is independent of shared-installer state.
3. **Resolve caller intent before changing directories:** baseline `nix/activate.sh` executes `cd -- "$project"`; for a relative value Bash may search inherited `CDPATH`. This can install into another same-named directory. Prefix relative inputs with caller `$PWD`, then use `cd -P` and `pwd -P`; the absolute argument cannot be redirected through CDPATH. Newline-containing project paths remain explicitly unsupported.
4. **Serialize marker and apply:** an exclusive project-local directory lock covers both cache checking and application. Competing calls fail promptly. Successful publication uses same-filesystem rename; old success is removed before reapplication. Normal exit/signals clean the lock. Uncatchable interruption may leave a stale lock, requiring manual removal only after confirming no activation is running.

## Alternatives, invariants and impacts

Always calling apply preserves the old interface but repeats expensive copying. Pasting cache logic into every consumer duplicates maintenance. Reusing shared roots/state is unsafe after partial failure. A small producer-owned wrapper gives a fixed entrypoint without changing the installer.

- Intended change: cheap successful-version skip and explicit repair command; relative inputs reliably target the caller's project.
- Preserved behavior: when needed, invoke the unchanged installer and propagate failure; preserve its protection rules even under `--force`.
- Invariants: marker means this environment last completed in this physical project; failed upgrade/repair cannot leave old success; cooperating wrappers cannot simultaneously install; inherited CDPATH cannot change the target.
- Representative counterexamples: failed upgrade then rollback must reapply; moving the project changes cache identity; marker symlink/directory fails; concurrent invocation cannot race the cache; `work/demo` versus `other/demo` with `CDPATH=other` must choose `work/demo`.
- Limits: direct agent-env calls do not share this lock/cache. Manual installed-file edits are not detected; `--force` invokes guarded reapply. External hostile filesystem mutation is not a security boundary supplied by this wrapper. No critical unresolved design assumption; packaged Darwin integration remains unexecuted validation, not a claim of success.

## Implementation and handoff

1. Keep `nix/activate.sh`, `nix/activate.nix`, flake export and README consumer usage as the feature implementation. Correct relative path resolution in the wrapper; do not compensate in consumers.
2. Add one focused CDPATH case to the existing offline test file. Keep prior cache/failure tests; use the separate [test plan](test-plan.md) for validation and reuse.
3. Freeze this candidate for independent review, then publish a normal commit to PR #96 using the expected current head. Do not merge, force-push, or create another PR.
4. Darwin build and one isolated README-style direnv activation are pending work under the test plan. Do not start the user's Mac or install to any user project in this change.

The marker name, private format and lock implementation are internal design choices, not new public business contracts. Review status remains pending until a reviewer records the applicable conclusions; prior code checks and CI do not confer plan approval.
