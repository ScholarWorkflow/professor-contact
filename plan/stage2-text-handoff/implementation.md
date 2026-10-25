# Stage 2 text-only upload handoff — execution plan

- Requirement revision: user 2026-10-25; lightweight text package, reuse unified PDF processing, ordinary process/two plans; latest clarification: hash the original PDF in place and do not copy it into any new local/temporary handoff package.
- Plan revision: EP3.1 (candidate). Proposed review status: pending.
- Repository baseline: professor-contact PR140 `856f396e3ac3083600919f094fd63908bc99a4e2`; main `05e0e8dc9030d5f1bbed0cc4d57561e7844b56e9` (API checked).
- New PR stacks on `fix/stage2-bundle-paper-instructions`; no merge permission. Retarget only after that dependency merges.
- Rules: [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d), [Plan Reviewer](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c), [Test Engineer](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253).

## Scope and non-goals

Upload page-tagged original paper text plus existing skill instructions and necessary evidence/job metadata. New handoff directories/ZIPs contain no PDF or image, including local staging. Source PDFs stay at their existing paths. Preserve PDF-grounded facts/future-work finalization, identities, current-input checks, writer leases, and legacy full-bundle imports. No new extraction engine, quality formula, installation path, global automatic OCR, candidate algorithm change, semantic analysis pass, complete-workflow regression or source/process certification.

Existing valid text is reused; otherwise use the same installed paper-analysis/pdf-processing-core processing path to export it. Empty pages and visual information unavailable in text are reported honestly under existing policy, without inventing chart/figure content. Orchestrator stdout remains compact and excludes paper text.

## Grounded decisions

Contact source paths below are at baseline above.

| Decision | Supporting facts and source |
|---|---|
| Contact owns transport/local source mapping | `.apm/skills/professor-contact/scripts/_stage2_chatgpt_handoff_impl.py`: `build_bundle`, `import_result`, `_finalize_facts`; root `apm.yml` already declares paper-analysis/pdf-processing-core. |
| Keep PDF carrier/source SHA; bind text separately | facade `stage2_chatgpt_handoff.py`: `_build_manifest`, `_verify_manifest_integrity` include whole job in job/source identity. PDF alone enables facts/future_work; `ocr` disables them. |
| Replace new PDF copy with local-only source record | impl currently copies input into ZIP and `_verify_bundled_input` hashes extracted bytes; `_finalize_facts` accepts a Path. It can consume the verified original Path directly. User expressly superseded the old copying design. |
| Preserve continue leases with local manifest | facade `_current_handoff_manifest_unlocked` currently reads `stage2-<id>.zip`; `build_bundle` and local lease operations share professor lock. Continue requires build identity before lease. Read new local record first, legacy ZIP fallback only for legacy jobs. |
| Reuse existing processing | paper-analysis Step1/1.5, `future_work.py prepare`, `pdf_runtime.py extract`, `validate-fulltext-ocr-cache`, `validate-ocr-cache`; prepare quality is owned by pdfx. Contact `_run_future_work` already supports fixed `CONTACT_PAPER_PYTHON` or PEP723 uv. |
| Handle installed generations | inspected paper-analysis commit `0d04f648f2c0379d8d70279fb3b2278494a31e2d` (`.apm/agents/paper-analysis.agent.md` Step1/1.5 and `.apm/skills/paper-analysis/scripts/future_work.py`) supports prepare.source_pages; existing consumer `contact90-cloud-live/consumer-full-attempt-preserved/.agents/skills/paper-analysis` has prepare.page_quality and pdf_runtime.extract physical markers but no source_pages. Inspect payload capability, never mix checkout helper into installation. |
| No hidden OCR | pdfcore `1451a0a7ab8e28a50173bfce70489d99d4a5074b`, `lib/pdfx/extract.py`: max-vision-pages=0 does not disable washable fallback vision. Use paper-analysis's deterministic prepare/extract + existing explicit OCR policy. |

The newer snapshot is descriptive only, not a minimum installation requirement. The installed paper-analysis helper remains the selected owner. Existing interpreter is `scholar-workflow-pdfx==0.1.0`, PyMuPDF1.28.2 in `/workspace/shared/paper-sentence-fix/.venv`; no dependency upgrade is planned.

## Frozen solution

### 1. Text preprocessing

Add a small Contact text-projection helper module; run same-install helpers via existing `_run_future_work`, no dependency/installer addition.

1. Validate source PDF SHA and prepare/candidates as today; preserve exact candidate scope and authoritative inputs.
2. Try sibling `<pdf>.llm_ocr.txt` using installed `validate-fulltext-ocr-cache --pdf ... --cache ... --expected-sha256 ... --output ...`. Only validated output with physical page coverage is reusable. Missing/stale cache or cache without page correspondence falls back to current source processing.
3. Otherwise reuse complete `prepare.source_pages`; old prepare lacking that field uses same installed `pdf_runtime.py extract <absolute-pdf> --output <temporary-text>`. Reuse prepare.page_quality and page_count. Do not re-prepare merely to select new candidates or implement a separate quality scorer. Malformed/missing processing metadata reports unavailable preparation, without claiming ready upload.
4. When needed, same-source page cache is consumed only after installed `validate-ocr-cache`; apply exact validated text to its page in the transport projection. OCR resolution is honored only when the actual transported page text comes from resolved `source_pages` or validated fulltext/page cache. An older prepare's `ocr_resolved_pages` alone records candidate refresh and supplies no full-page text; it cannot mark newly extracted unreadable text resolved. Without corresponding exact page text, the existing preparation need remains. Never alter authoritative prepare/candidates just to make transport pass.
5. Preserve physical-page positions including allowed empty pages. Apply existing Step1.5 decision: unresolved untrusted triggers local OCR need; empty pages with no trusted pages trigger it; isolated empty pages alongside trusted pages remain marked ordinary missing pages and do not independently block. Do not impose every-page-nonempty. Cache-resolved pages no longer count unresolved. Metadata records missing text pages for webpage limitations.
6. Nonempty prepare.ocr_required_pages still needs the caller's existing local merge-ocr flow: fulltext cache cannot replace future-work page evidence. Since the new upload has no images, it cannot ask webpage to OCR unseen pages. Return affected item/pages and let existing installed policy obtain any required authorization and resolve/merge locally; no global OCR from builder.
7. Required missing text/failed extraction suppresses only the upload. Local source/manifest record remains available so continue mode can follow its original local workflow. Invalid source identity/context remains a build error. No incomplete upload ZIP and no PDF upload fallback.

### 2. Local record and transport contract

- PDF carrier/evidence/expected fields stay unchanged. `input_sha256` remains original PDF SHA; `input_path` remains its portable logical source name, never a user absolute path.
- New PDF jobs have `source_mode: local` and, when prepared, optional `text_transport` containing fixed text path, SHA256, physical page_count, format identifier, and missing_text_pages. Canonical job/source identity includes these fields. No duplicate source-hash field or source provenance ledger.
- Local-only `stage2-<id>.local.json` contains the canonical manifest plus `sources` mapping PDF item_key to original absolute path. It is written by this build from validated jobs, never accepted from webpage/result ZIP, and never packaged. Source SHA is already in manifest.
- New `stage2-<id>.zip` is the only upload archive and contains text/JSON/context helper sources from an explicit allowed list. It does not contain source PDFs, images, cache/debug directories or local records. Its extracted local bundle_dir likewise contains no PDF copies.
- Return `upload_ready`, `bundle_path` (ZIP only when ready, otherwise null), `local_manifest_path`, existing identity/jobs, and minimal `text_preparation` item/pages/reasons. Local record exists even when text is unready. Zero jobs/abstract-only stay supported.
- Webpage reads text_transport.path for PDF; other carriers keep existing input_path. It returns existing result identity and original input_sha256. Missing page/visual evidence is disclosed and partial/error used when it prevents justified conclusions. Existing candidate scope is unchanged.

### 3. Import, resume and leases

- New import `--bundle` is the current lightweight ZIP. Existing API remains; no external absolute source path is honored.
- For source_mode=local, find the local record under current professor's `_chatgpt_handoff` using verified manifest handoff_id. Require its canonical manifest to match this bundle; resolve original path only from that local mapping. Missing record/source or changed original SHA fails explicitly before sidecar/install. Do not search Zotero/filesystem or silently choose another PDF.
- Verify transport bytes against its bound hash and source PDF in place against input_sha256. Return original PDF Path to facts finalize. Future-work continues using the bundled prepare/candidates and original source SHA; facts helper reads the same original path and its existing output fingerprint check remains. No source PDF copy into import temp directory.
- Result ZIP extraction, path safety, current/baseline guards, existing per-job transactional install and local finalizers remain. The existing professor lock/current guards protect coordination. Because the source is now mutable in place rather than a copied snapshot, the existing guarded install also rechecks the mapped original source SHA immediately before writing; a change is stale input and installs nothing. This closes the new source lifecycle gap without a new provenance protocol.
- `_current_handoff_manifest_unlocked` reads canonical manifest from the new local record for lease/current-plan checks. If absent, legacy archive path remains readable for old bundles. New source_mode=local cannot silently fall back to treating absent local source as embedded evidence.
- Resume rebuilds against current original files and text before import, as today. Changed source/text changes identity; missing source is a concrete error. It does not regenerate or copy PDF. Old full ZIPs without source_mode/text_transport use the unchanged embedded-source verification path, including legacy OCR import.

### 4. Publication, failures and callers

- Use existing professor lock/active-writer guard. Prepare in temporary text-only staging. Validate before publishing; local record and ready ZIP use atomic replacement; `_latest.json` is published last. Failure in source/context validation does not advance latest.
- A text-unready build still publishes the local record/identity needed for continue, without a ZIP. On retry/rebuild, improved text is reflected in canonical identity. Never label a stale ZIP as the current upload.
- Sources, caches, previous handoff versions and user artifacts are not deleted; clean only new temporary staging. Same inputs/text retain deterministic serialization/ZIP behavior.
- Codex and OpenCode Step4.5: wait with upload_ready=false soft-stops with exact local preparation need; continue consumes local manifest identity and original writer lease/local analysis path. When ready, expose only bundle_path for upload and retain local_manifest_path. On resume use current lightweight bundle_path for import. No missing-text fallback to PDF upload.
- Update shared SKILL and webpage instructions; replace outdated no-local-OCR/upload-PDF wording only in the affected handoff section. Keep runtime-specific native routing and full template intact. Existing legacy OCR protocol remains import compatibility, not new upload instructions.

## Impact and representative counterexamples

- intended/approved change: text-only handoff plus original-PDF in-place hash/local source lookup, explicitly authorized by user. Source paths remain local.
- preserved: PDF facts/future-work, old import, exact candidate scope, current identity/baseline, continue writer lease, installed skill snapshot, original file/cache bytes.
- prohibited: new PDF copies (local or upload), upload images/absolute source paths, stale cache acceptance, global OCR, unrelated candidate fixes, merge/deploy.
- Same item replaced PDF: current in-place hash changes identity or fails import. Same PDF changed transport: text hash changes identity. Missing original path: explicit failure without guessing.
- New lightweight ZIP copied to another machine without local record/source: explicit unavailable evidence; no fabricated facts. Legacy embedded bundle retains its old behavior.
- Text-unready continue: local record enables existing lease and local processing. Text-unready wait: reports specific preparation need, no accidental PDF upload.
- Isolated blank page: retains physical page marker and missing-page metadata without new OCR requirement. Required evidence/visuals absent: no fabricated complete result.
- Plan critical assumptions/unresolved impacts: none proposed; independent review decides before implementation.

## Order and revision

1. Independent EP3.1 review and separate TP3 Gate1/Gate2 confirmation.
2. Implement text helper, local record, manifest validation, source resolution, lease reads and import together; all local/source persistence paths covered above.
3. Update direct callers/docs and TP3-directed tests; execute approved recipe and obtain independent result/code review.
4. Commit normally, open stacked draft PR, verify remote head/base/diff and CI; no self-approval or merge.

EP3.1 supersedes EP2 entirely: latest user requirement removes both local full archive and all PDF copying; local record provides source lookup/continue coordination. It also restores Step1.5's ordinary missing-page allowance and makes test commands explicit. No earlier copy design remains applicable.

EP3.1 clarification: OCR resolved metadata alone is insufficient for old prepare without source_pages; actual transport must contain the resolved page text. No new behavior/test obligation beyond existing cache/quality handling.
