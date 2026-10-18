# Cached Nix activation — test plan t1

Target: PR #96 baseline `ae890491e4bdd7e95ec4ffee5a48cbf28af14ec3` plus the CDPATH correction and this plan. Requirement/ownership: [implementation plan r1](implementation-plan.md). Proposed review status: pending; first/second/third gate conclusions belong to the reviewer. This is the single complete test plan and execution recipe for this bounded feature.

## Required goals and one sufficient check per goal

| Goal | Input/scenario | Expected result and check |
| --- | --- | --- |
| Cache, repair and failure semantics | First apply, same environment/project, changed environment, force, failed upgrade then rollback | Existing offline `test_first_skip_upgrade_force` and `test_failure_invalidates_old_marker_and_retries` assert calls, successful marker and failure invalidation. Reuse these checks; do not repeat every branch on Darwin. |
| Correct project identity and safe wrapper boundary | Physical alias/move, invalid marker, occupied lock, invalid args | Existing `test_physical_path_and_move` and `test_reject_unsafe_marker_lock_and_bad_args` assert correct paths, refusal and no unintended installer call. |
| Relative project is independent of CDPATH | Calling directory contains `demo`, CDPATH points to another directory also containing `demo` | New `test_relative_project_ignores_cdpath` asserts exactly the caller's `demo` reaches the stub, only that target gets a marker, and the competing target remains empty. |
| New Darwin export is usable through documented consumer path | Exact PR SHA; build new export, then one fresh isolated consumer using README mkShell/direnv | Build succeeds and exported executable exists; one direnv invocation succeeds and creates the intended project's success marker and installed contact SKILL.md. This checks real packaging/wiring, not another cache/failure matrix or business workflow. |

No model, email, browser, Zotero, knowledge-store or full Stage 0–5 run is required. No new generic evidence tooling or CI expansion. Existing GitHub regression CI does not execute `nix/test-activate.py`; do not substitute it for the offline wrapper checks.

## Completed checks and reuse

- Baseline ae890491: four offline unittest methods, `bash -n`, and Nix parsing succeeded. GitHub [test job 117697931665](https://github.com/ScholarWorkflow/professor-contact/actions/runs/39135110431/job/117697931665) completed **success**, not running; this is the existing regression suite, not the new wrapper suite.
- CDPATH candidate: `python3 nix/test-activate.py -v` completed five methods successfully on Linux with host Bash/GNU coreutils; includes the original four methods unchanged plus the targeted counterexample. Bash syntax and both Nix parse checks passed. The local execution record is `/tmp/contact96-cdpath-tests.log`; temporary raw records are not committed.
- Darwin export build and real direnv activation: **executed 2026-10-18** on aarch64-darwin for commit `4d59c05` by the local execution engineer; build log, activation exit results, run paths and observed outputs are in the [execution record](test-execution-2026-10-18.md). Fact sync only; the third-gate conclusion stays with the reviewer.
- Subsequent unrelated SHA/docs changes do not invalidate unaffected results. CDPATH changes directly affect project resolution; cache/failure implementations remain unchanged. No automatic full-chain rerun.

## Offline recipe

From the producer checkout, use Python 3 with Bash/GNU coreutils in PATH (macOS default BSD utilities do not satisfy this test harness):

```sh
python3 nix/test-activate.py -v
bash -n nix/activate.sh
nix-instantiate --parse nix/activate.nix >/dev/null
nix-instantiate --parse flake.nix >/dev/null
git diff --check
```

The five-method result above is already recorded; these commands describe reproduction, not an instruction to rerun unaffected checks at every revision. No real installer is called by the offline suite.

## Darwin build and isolated direnv recipe (executed 2026-10-18, see the [execution record](test-execution-2026-10-18.md))

Owner: the assigned execution engineer, after a suitable aarch64-darwin environment is authorized and the plan/steps are reviewed. This document does not authorize connecting a computer, installing dependencies or using a real user project. Use the existing Nix and direnv setup; record their actual versions and exact producer SHA. If missing or unavailable, report the affected item as unexecuted rather than install or change the host automatically. Execution status: completed on 2026-10-18 with the existing setup and an isolated `/tmp` consumer, without touching a user project; actual versions, commands, exit results and observed outputs are in the [execution record](test-execution-2026-10-18.md).

Preparation: set `CONTACT_SHA` to the exact reviewed 40-character PR head for this run. Create a fresh `/tmp` run directory outside producer/worktrees. Reuse immutable Nix caches. Use the README's consumer flake exactly, with its `contact` input locked to this SHA by the override below; `.envrc` contains `use flake`. No copied installer, local-path producer input, patched consumer artifact or business services.

```sh
set -eu
: "${CONTACT_SHA:?Set the exact reviewed PR head SHA first}"
CONTACT_REF="github:ScholarWorkflow/professor-contact/$CONTACT_SHA"
RUN=$(mktemp -d /tmp/contact96.XXXXXX)
mkdir -p "$RUN/consumer"
nix build "$CONTACT_REF#professor-contact-activate" --out-link "$RUN/activate" >"$RUN/build.log" 2>&1
test -x "$RUN/activate/bin/professor-contact-activate"
cd "$RUN/consumer"
cat > flake.nix <<'NIX'
{
  inputs = {
    contact.url = "github:ScholarWorkflow/professor-contact/main";
    nixpkgs.follows = "contact/nixpkgs";
  };
  outputs = { contact, nixpkgs, ... }:
    let
      system = "aarch64-darwin";
      pkgs = nixpkgs.legacyPackages.${system};
      activate = contact.packages.${system}.professor-contact-activate;
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = [ activate ];
        shellHook = ''
          "${activate}/bin/professor-contact-activate" --project "$PWD" || exit $?
        '';
      };
    };
}
NIX
nix flake lock --override-input contact "$CONTACT_REF" >"$RUN/lock.log" 2>&1
printf '%s\n' 'use flake' > .envrc
# Scope direnv trust/state to this disposable run; retain existing Nix/direnv config.
export XDG_DATA_HOME="$RUN/direnv-data"
direnv allow .
direnv exec . sh -c 'test -f .professor-contact-applied && test -f .agents/skills/professor-contact/SKILL.md' >"$RUN/activation.log" 2>&1
```

Record the exact SHA, run path, commands and build/activation exit results. The marker and installed SKILL.md are the sufficient observed outputs; do not trigger skill business operations. Retain the isolated consumer and logs for review; do not remove user GC roots or unrelated state as cleanup.

Failure handling: stop the affected step at its first failure and preserve its log. Dependency/access failure is unable to judge, not product pass/fail. Permit at most one retry only after a transient external access failure has demonstrably cleared, retaining the same SHA/config and both logs; reuse existing build cache and consumer if still clean. Product/recipe failure requires correction and impact review, not repeated sampling. If a failed real install left partial mutable state, use a new isolated consumer for that corrected install, never patch it in place. No additional project, platform or business-chain coverage is implied.
