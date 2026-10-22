# Public PDF consumer integration — H2

Implemented the narrow Contact input update at `30af35622f54c6ded8ce32a6845fceab25f13bd3` on top of current main, retaining the old PR history with a normal merge commit (no rebase/force).

- Public PDF input and its matching lock node now select merged PDF PR11, `2be1bf850f29b7ccf7bd1b066ae7292aac33fc87`.
- Existing `import pdfx` and `packages.pdfx-agent` composition remains unchanged. Shared nixpkgs/agent-env follows remain unchanged.
- Paper-analysis's independent library-only PDF source is intentionally not updated. No ownership, installer, business behavior, supported platform, or APM/uv behavior changes.
- Exact source Git blob/mode and NAR hashes were checked. Independent static review found the pin/lock change within the bounded consumer scope; this is not author-granted APPROVED or runtime PASS.

The only final combined check is owned by [Study PR16](https://github.com/StudyCoachWorkflow/study-tools/pull/16), with its complete fixed-version [recipe and result record](https://github.com/StudyCoachWorkflow/study-tools/blob/plan/public-pdf-consumer-20261022/plan/pdf-agent-composition/consumer-handoff.md). Contact does not duplicate that run or upstream native/business/installer tests.

As of 2026-10-22: cloud evaluation of the real aarch64-darwin roots stopped acquiring an existing uncached paper-analysis source (GitHub archive timeout), so full graph evaluation is NOT COMPLETED. Actual combined Darwin build/activation is NOT RUN; the cloud is Linux and no Mac execution was authorized here. The implementation is ready for review, but final combined deployment READY is not claimed. This replaces the prior handoff-only status without claiming upstream results prove this final consumer combination.
