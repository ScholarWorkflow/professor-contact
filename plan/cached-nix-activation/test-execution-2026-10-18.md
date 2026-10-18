# Cached Nix activation — execution record (2026-10-18)

Scope: the two outstanding integration checks of [test plan t1](test-plan.md): the line 12 goal (new Darwin export usable through the documented consumer path) and its recipe at lines 37–83. The three offline goals at lines 9–11 reuse the records at lines 18–19; they were not rerun, as lines 25–35 describe reproduction rather than a rerun instruction.

- Role: local execution engineer. No product file and no test file was changed for this run.
- Producer commit (`CONTACT_SHA`): `4d59c0556de113cee554e8879236c9cc378ec826` (PR #96 head, including the relative-path correction).
- Producer ref: `CONTACT_REF=github:ScholarWorkflow/professor-contact/4d59c0556de113cee554e8879236c9cc378ec826`.
- Platform and tools: macOS 26.7 / Darwin 25.6.0, aarch64 (Apple silicon); Nix 2.34.8; direnv 2.37.1; Bash 5.3.15; Python 3.14.7. Existing Nix and direnv setup reused; nothing was installed or reconfigured on the host.
- Run directory (outside the repository): `/tmp/contact96.56f6R8` — `build.log`, `lock.log`, `activation.log`, `direnv-data/`, `consumer/`. Helper script and per-step exit codes: `/tmp/contact96-local-execution/` (`run-activation.sh`, `step-exit-codes.txt`). These raw records are not committed.

## 1. Results per goal

| Test plan goal | Result | Evidence |
| --- | --- | --- |
| Cache, repair and failure semantics (line 9) | PASS (reused) | Offline record at lines 18–19; method `test_first_skip_upgrade_force` plus `test_failure_invalidates_old_marker_and_retries`. |
| Correct project identity and safe wrapper boundary (line 10) | PASS (reused) | Offline record at lines 18–19; methods `test_physical_path_and_move` and `test_reject_unsafe_marker_lock_and_bad_args`. |
| Relative project is independent of CDPATH (line 11) | PASS (reused) | Offline record at lines 18–19; method `test_relative_project_ignores_cdpath`, run on the CDPATH candidate that is this commit. |
| New Darwin export usable through the documented consumer path (line 12) | PASS (this run) | Sections 2 and 3 below. |

## 2. aarch64-darwin build (line 12)

```sh
CONTACT_REF="github:ScholarWorkflow/professor-contact/4d59c0556de113cee554e8879236c9cc378ec826"
nix build "$CONTACT_REF#professor-contact-activate" --out-link "$RUN/activate"   # exit 0
test -x "$RUN/activate/bin/professor-contact-activate"                            # exit 0
```

- The build completed with exit 0 (`$RUN/build.log`, elevated derivation logs end with `professor-contact-activate`); the exported path is `/nix/store/2pxfxwwgndx1j096jcdshqfmg90r0f8g-professor-contact-activate`.
- The exported entrypoint exists and is executable: `$RUN/activate/bin/professor-contact-activate`, mode `0555`, 2316 bytes.
- Entrypoint content check: byte-identical to `nix/activate.sh` with exactly the three fixed substitutions of `nix/activate.nix` — `@bash@` → `bash-interactive-5.3p15`, `@coreutils@` → `coreutils-9.11`, `@environment@` → the environment store path evaluated for this commit. Shebang points at the fixed Nix Bash, and the script resolves `environment` and `coreutils` from those fixed paths rather than from `PATH` (`diff` output `/tmp/contact96-local-execution/entrypoint.diff` is empty).
- Attempt 1 of the `--dry-run` preflight failed while fetching this commit's tarball: `cannot read file from tarball: Truncated tar archive detected while reading data`. This is an external access failure, not a product result. `/tmp/contact96-local-execution/dryrun.log` is that failed preflight's own log; `/tmp/contact96-local-execution/dryrun.attempt1.log` is a byte-identical copy of it (same 339 bytes, MD5 `37c8a6b5c3bc8beff779efefc1d769c8`), retained as the attempt-1 record. No other attempt produced a truncated-tarball failure.
- The same `codeload.github.com` tarball endpoint was checked by hand right after the failure and answered HTTP 200; that hand check's output was not retained. The endpoint was re-checked while writing this record and still answers HTTP 200 (`/tmp/contact96-local-execution/endpoint-check.txt`). The retry allowed by line 83 was then taken once — the real build with the identical producer SHA, flake ref and locked inputs, but without the `--dry-run` flag, since that flag was only the preflight — and it succeeded: `build.log`, the out-link `/nix/store/2pxfxwwgndx1j096jcdshqfmg90r0f8g-professor-contact-activate` and the executable entrypoint above are all from that single retry, and nothing after it failed.

## 3. One isolated direnv activation (lines 41–81)

The consumer flake and `.envrc` use the README consumer form verbatim; the `contact` input is locked to the same commit:

```sh
cd "$RUN/consumer"
nix flake lock --override-input contact "$CONTACT_REF"     # exit 0
printf '%s\n' 'use flake' > .envrc
export XDG_DATA_HOME="$RUN/direnv-data"
direnv allow .                                             # exit 0
direnv exec . sh -c 'test -f .professor-contact-applied && test -f .agents/skills/professor-contact/SKILL.md'   # exit 0
```

- Consumer `flake.lock` `nodes.contact.locked.rev` read with `jq` equals `4d59c0556de113cee554e8879236c9cc378ec826`, so the consumer really used the reviewed commit rather than the `main` tip.
- `$RUN/activation.log` records `direnv: using flake` and the installer's own `agent-env: apply completed.`; the wrapper's `apply` call therefore ran through the real shared installer.
- Observed outputs in the intended project (`$RUN/consumer`):
  - `.professor-contact-applied`, 116 bytes, content `v1` + line 2 `/nix/store/lh3mf2aqy17kssbkwwismk0ayk6d9zbp-professor-contact-environment` + line 3 `/private/tmp/contact96.56f6R8/consumer`. Line 2 equals the environment store path fixed into the built entrypoint, so the marker records this environment; line 3 is the physical path returned by `pwd -P`, not the `/tmp` spelling of the caller.
  - `.agents/skills/professor-contact/SKILL.md`, 170468 bytes, with the installed `docs/`, `scripts/` and `tests/` siblings.
  - `.agent-env-nix/` installer state directory.
- Isolation: the consumer is a fresh `mktemp -d` directory outside the repository and its worktrees; `XDG_DATA_HOME` is scoped to this run. No user project, HOME configuration, global direnv allow state, Zotero profile, model service or business workflow was used or modified.

## 4. Reuse and not executed

- The offline goals reuse the record at lines 18–19: five `python3 nix/test-activate.py -v` methods, `bash -n nix/activate.sh`, and `nix-instantiate --parse` for `nix/activate.nix` and `flake.nix`, with target log `/tmp/contact96-cdpath-tests.log`. That run was produced on Linux with host Bash/GNU coreutils, which the recipe at lines 25–35 states; its raw log is not present in this environment and is not required by the plan. Reuse follows lines 21 and 25–35 and Test Engineer Rule sections 4 and 6.
- `git diff --check` is a step of the recipe at line 32, not a result recorded at lines 18–19, and this run did not re-execute it. For reference only: over the candidate range `74bd29b..4d59c05` it reports two whitespace warnings, `new blank line at EOF` in `README.md` and `flake.nix`, both introduced by the feature commit. They are whitespace-only, they are not a required result of this plan, and no product file was edited for this record, because editing them would change the tested commit and require re-evaluating results that this plan reuses.
- Nothing outside the line 12 goal was run: no model, email, browser, Zotero, knowledge-store or Stage 0–5 business chain, no CI substitution (line 14), no new test asset or evidence tooling.

## 5. Handoff

- All four test plan goals now have a current-version result: lines 9–11 reused, line 12 passed in this run. No product defect was found and no product or test change was needed.
- This record reports per-item business results only. The third-gate conclusion belongs to the reviewer; this record is neither a plan approval nor a merge approval.
- Next owner: third-gate review of test plan t1 against this record; merge review, if requested, follows `Merge Reviewer Rule.md`.
