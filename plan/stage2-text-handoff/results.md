# TP3 execution observations

- Product candidate: local commit containing this record, based on `856f396e3ac3083600919f094fd63908bc99a4e2`; independent implementation/third-gate review pending.
- Plan: EP3.1 / TP3, independent Gate1/2 approval in `review.md`.
- Environment: isolated cloud checkout; Python3.12.14. Real helper run reused installed `scholar-workflow-pdfx==0.1.0` / PyMuPDF1.28.2 and the existing consumer specified in TP3. No installation, model, vision/OCR service, user profile or complete workflow run.
- Raw attempts: `/tmp/contact-text-handoff-tests.nysQ0j`; real CLI: `/tmp/contact-text-handoff.YyTGxW`; executable copy of the unchanged TP3 recipe `/tmp/contact-text-real-recipe.sh`.

| Target | Observed outcome and source |
|---|---|
| T1 | New ZIP contains original page text/markers and abstract input, no PDF/image/local record or original absolute path. Local record resolves original PDF; no PDF under handoff. `test_text_only_and_original_source_record_with_allowed_blank_page` successful; final mixed-input check in `final-targeted.txt`. |
| T2 | New test module's old-prepare, full-cache valid/stale and page-cache tests successful. Self-review corrected scan handling: one resolved page must not make other scanned empty pages count as ordinary blank; exact-page cache case rechecked in `scan-cache-policy.txt`. Real old installed prepare had no source_pages; TP3 CLI exported successfully via installed pdf_runtime.extract. |
| T3 | Required OCR suppresses upload and reports page2; current local record successfully acquires/releases existing writer lease. Ordinary nonrequired blank page preserved without OCR. Focused test output `first.txt`. |
| T4 | New result imports with facts tied to original source SHA and helper argv contains original PDF path. Missing/changed original and changed transport reject before analysis install. Legacy embedded-source import, old no-context import, embedded-source tamper rejection and legacy OCR merge cases successful. |
| T5 | Both runtime docs reviewed against current upload_ready/local record/current bundle paths. Legacy caller assertion initially failed because quote_excerpt field explanation was dropped; restored the legacy selection fields in both docs and reran that one assertion successfully. No assertion weakened. |

## Commands and attempts

- `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_stage2_chatgpt_handoff_text.py' -v`: 8 tests successful (`first.txt`).
- `PYTHONPATH=.apm/skills/professor-contact/tests python -m unittest -v` with these exact existing selectors (`legacy-and-callers.txt`):
  - `test_stage2_chatgpt_handoff.HandoffTests.test_valid_result_installs_analysis_sidecar_and_index`
  - `test_stage2_chatgpt_handoff.HandoffTests.test_legacy_bundle_without_context_still_imports`
  - `test_stage2_chatgpt_handoff.HandoffTests.test_tampered_bundled_carrier_is_rejected_by_actual_byte_hash`
  - `test_stage2_chatgpt_handoff.HandoffTests.test_workflow_contract_wires_continue_wait_and_resume`
  - `test_stage2_chatgpt_handoff_review3.Review3RegressionTests.test_ocr_required_selection_rebinds_after_merge_without_external_candidate_id`
  - `test_stage2_chatgpt_handoff_review3.Review3RegressionTests.test_agent_contract_registers_and_releases_local_writer_lease`
  - `test_stage2_chatgpt_handoff_review4.Review4RegressionTests.test_mixed_readable_and_ocr_pages_preserve_both_future_work_items`
- First selection: 6 successful, 1 documentation assertion failed. After restoring legacy field explanation, only the failed selector rerun: successful (`legacy-doc-fix.txt`).
- `test_stage2_chatgpt_handoff_text.TextTransportTests.test_page_cache_and_actual_resolved_text`: successful after the narrow scan-cache policy correction (`scan-cache-policy.txt`).
- Final affected selectors `test_stage2_chatgpt_handoff_text.TextTransportTests.test_text_only_and_original_source_record_with_allowed_blank_page` and `.test_new_import_finalizes_against_original`: both successful (`final-targeted.txt`). Unaffected results reused.
- TP3 exact real CLI recipe: successful, `upload_ready=true`, 13 archive files, 39,194 bytes, 1,071 text bytes. Direct ZIP/JSON observations saved in `observations.json`: original SHA and source record match, page marker and expected sentence present, transport SHA matches, no PDF/image/local absolute path, zero handoff PDF copies. Size is descriptive, not a performance gate.
- `git diff --check`: clean. `python scripts/check_test_shards.py`: 82 modules/4 shards, successful. No all-repo regression requested or run.

Legacy tests use an explicit pre-text embedded-bundle fixture to retain the old import contract. New default producer output is exercised by the new module and actual CLI. This fixture is test-only and does not restore a PDF-copy option to production.

No formal Gate3 or merge verdict is claimed by the implementer; next owner is independent reviewer.
