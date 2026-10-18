# Cached Nix activation — execution record (2026-10-19)

Scope: the single remaining execution goal of [test plan t4](test-plan.md), "Real Darwin packaging / README consumer", executed with t4's bounded substitutions on [implementation plan r4](implementation-plan.md) steps 1–5. The three other goals (shared ownership, resolved dependency, shared cache/lock behavior) keep their existing results; their static facts were re-confirmed at the current product but no behavior test was rerun.

- Role: local execution engineer. No product file and no test file was changed for this run.
- Producer commit (`CONTACT_SHA`): `f327f54220d321eb0fce3b3908f86c4ab0914745` (PR #96 product revision referenced by implementation plan r4 and test plan t4).
- Producer ref (`CONTACT_REF`): `github:ScholarWorkflow/professor-contact/f327f54220d321eb0fce3b3908f86c4ab0914745`.
- Platform and tools: macOS 26.7 / Darwin 25G229, arm64 (Apple silicon); Nix 2.34.8; direnv 2.37.1. Existing Nix and direnv setup and the immutable caches were reused; nothing was installed or reconfigured on the host.
- Run directory (outside the repository and its worktrees): `/tmp/contact96.OBt8Lw` — `build.log`, `lock.log`, `direnv-allow.log`, `activation.log`, `direnv-data/`, `consumer/`. Helper scripts and the run-path file: `/tmp/contact96-local-execution-20261019/` (`build.sh`, `activate.sh`, `run-path`). These raw records are not committed.
- Attempts: exactly one build and one activation run; no step failed and no retry was taken (t4 does not carry forward t1's one-retry permission).

## 1. Results per goal

| Test plan goal | Result | Evidence |
| --- | --- | --- |
| Shared ownership / same consumer entrypoint (row 1) | PASS (reused, static re-confirmed) | Source inspection below; merged `lib/default.nix` and `lib/cached-activation.nix` read at the pinned revision. |
| Resolved, correctly locked dependency (row 2) | PASS (reused, static re-confirmed) | Node-by-node lock comparison below; `nix flake metadata` for the pinned revision. |
| Shared cache/lock behavior (row 3) | PASS (reused) | Upstream factory/runtime evidence reused within its scope; no shared test rerun. |
| Real Darwin packaging / README consumer (row 4) | PASS (this run) | Sections 2 and 3 below. |

## 2. aarch64-darwin build (t4 step 3)

```sh
CONTACT_REF="github:ScholarWorkflow/professor-contact/f327f54220d321eb0fce3b3908f86c4ab0914745"
nix build "$CONTACT_REF#professor-contact-activate" --out-link "$RUN/activate"   # exit 0
test -x "$RUN/activate/bin/professor-contact-activate"                           # exit 0
```

- Build completed with exit 0 in 32 s (`$RUN/build.log` ends with `building '/nix/store/wxg3z38jh9ih965v604r6kcf4pj8ni17-professor-contact-activate.drv'...`). The exported path is `/nix/store/4999ys7kjnljgngzwdzwqwpzsc6zprlm-professor-contact-activate`.
- The named entrypoint exists and is executable: `$RUN/activate/bin/professor-contact-activate`, mode `0555`, 2313 bytes.
- The built entrypoint fixes `readonly environment='/nix/store/lh3mf2aqy17kssbkwwismk0ayk6d9zbp-professor-contact-environment'`, i.e. the `products.project` environment passed to the shared factory; it resolves Bash and coreutils from fixed store paths rather than `PATH`.

## 3. One isolated direnv activation (t4 step 4)

Consumer `flake.nix` is the README form verbatim; the `contact` input was locked to the same revision, and `.envrc` contains `use flake`:

```sh
cd "$RUN/consumer"
nix flake lock --override-input contact "$CONTACT_REF"     # exit 0
printf '%s\n' 'use flake' > .envrc
export XDG_DATA_HOME="$RUN/direnv-data"
direnv allow .                                             # exit 0
direnv exec . sh -c 'test -f .agent-env-applied && test -f .agents/skills/professor-contact/SKILL.md'   # exit 0
```

- Consumer `flake.lock` `nodes.contact.locked.rev` read with `jq` equals `f327f54220d321eb0fce3b3908f86c4ab0914745`, so the consumer used the reviewed revision rather than the `main` tip (`$RUN/consumer-contact-rev.txt`).
- `$RUN/activation.log` records `direnv: using flake`, `direnv: nix-direnv: Renewed cache` and the installer's own `agent-env: apply completed.`; the entrypoint's `apply` call therefore ran through the real shared installer.
- Observed outputs in the intended project (`$RUN/consumer`):
  - `.agent-env-applied`, 116 bytes, content `v1` + line 2 `/nix/store/lh3mf2aqy17kssbkwwismk0ayk6d9zbp-professor-contact-environment` + line 3 `/private/tmp/contact96.OBt8Lw/consumer`. Line 2 equals the environment store path fixed into the built entrypoint; line 3 is the physical path returned by `pwd -P`, not the `/tmp` spelling of the caller.
  - `.agents/skills/professor-contact/SKILL.md`, 170468 bytes, with the installed `docs/`, `scripts/` and `tests/` siblings.
  - `.agent-env-nix/` installer state directory.
  - The old contact marker `.professor-contact-applied` is absent, as required: the shared marker is the only success evidence and the first shared activation reapplies.
- Isolation: the consumer is a fresh `mktemp -d` directory outside the repository and its worktrees; `XDG_DATA_HOME` is scoped to this run. No user project, HOME configuration, global direnv allow state, Zotero profile, model service or business workflow was used or modified.

## 4. Static re-confirmation of the reused goals

- Implementation items 1–3 are present at this product: `flake.nix` pins `agent-env-nix` to `91861b4f028eda1dbeb41481dcc48cd7c4a60874` and calls `agent-env-nix.lib.mkCachedActivation { inherit pkgs; environment = products.project; name = "professor-contact-activate"; }` directly; no pending `throw` for this input remains outside `nix/contact.nix`'s own argument validation; `nix/activate.nix`, `nix/activate.sh` and `nix/test-activate.py` are absent from both the branch and the net diff against `main`. The merged factory signature at the pinned revision is `{ pkgs, environment, name ? "agent-env-activate" }`, matching the call.
- Lock scope: comparing `flake.lock` at `74bd29b` and at this product with `jq`, the node set and the `root` refs are identical and the only changed node is the top-level `agent-env-nix` node (`rev` `91861b4f…`, `narHash` `sha256-/VgkCnSU4Giw+7P68NMgMnYQ+SHJY45Q8YYxETKqA+w=`, `lastModified` 1792341743). `nix flake metadata github:RekiDunois/agent-env-nix/91861b4f028eda1dbeb41481dcc48cd7c4a60874` reports the same `narHash` and revision.
- Net product diff against `74bd29b` touches `README.md`, `flake.lock`, `flake.nix` and the three `plan/cached-nix-activation/` documents only; no APM or business source, no other product, no shared repository file and no CI file changed.

## 5. Not executed

- Goal 3 shared cache/repair/lock/failure semantics remain covered by the upstream factory tests within their documented scope; they were not rerun, and no contact-owned replacement test was restored (t4 explicitly forbids restoring `nix/test-activate.py` and its offline recipe).
- No model, email, browser, Zotero, knowledge-store or Stage 0–5 business chain, no other platform, no CI substitution and no new test infrastructure.
- No standalone `drvPath` evaluation was added: the build above includes Nix evaluation, as t4 step 3 states.

## 6. Handoff

- All four test plan t4 goals now have a current-version result: rows 1–3 reused with static facts re-confirmed, row 4 passed in this run for product `f327f54220d321eb0fce3b3908f86c4ab0914745`.
- No product defect was found; no product or test change was needed for this run.
- This record reports per-item business results only. Independent reviewers own the implementation/test-plan conclusions and any formal gate; this record is neither a plan approval nor a merge approval.
