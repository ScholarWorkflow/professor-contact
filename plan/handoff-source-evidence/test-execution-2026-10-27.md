# 轻量 handoff 正文 future-work — 测试执行记录（2026-10-27）

- 执行计划：CONTACT-SOURCE-EP1.1（`Plan conclusion: APPROVED`，P1–P4 PASS）。
- 测试计划：CONTACT-SOURCE-TP1.1（第一关 PASS、第二关 PASS）。
- 被测提交：`cba85a5b4bd58051976e45d7f5339e7a26180acf`（`fix(stage2): report every unresolved blocking page and align the import notes`）。本轮提交序列：`0149e18`（实现，首轮正式执行）→ `0eed997`（manifest 旧契约兼容性修订）→ `cba85a5`（审核 P1/P2 修订，最终候选）。每个提交都包含 `.apm/skills/professor-contact/tests/test_stage2_chatgpt_handoff_source.py`（`git cat-file -e` 返回 0）。下文的 T1–T4 与 hybrid 结果在 `0149e18`、`0eed997`、`cba85a5` 三个提交上都重跑过，结果相同。
- 环境：macOS arm64；解释器 `/nix/store/447smjkzgapdxqrcdg8r8kf8j1a1jrxc-python3-3.14.7-env/bin/python3`（Python 3.14.7，`pymupdf 1.27.2.3`、`scholar-workflow-pdfx 0.1.0`）。
- 上游 helper：`/nix/store/vvdass0s4x1b2h46sqk29dq7rdbjbmr8-paper-analysis-0.1.0/payload/skills/paper-analysis`；`future_work.py` SHA256 `25bd7678f85dc1a8cb527449f65f12d0b4400da5ff8d8806b26a175490d571ea`（与测试计划第 3 节、flake.lock `c140658c` 一致）。
- 运行目录：`/tmp/contact-source-evidence.C7DWxa`；其中 `version.txt`、`source-items.out`、`legacy-hybrid.out`、`shards.out` 保存首轮正式输出，`source-items.cba85a5.out`、`handoff-suite.cba85a5.out`、`legacy-hybrid.cba85a5.out` 保存最终候选的复跑输出，`tmp/` 为用例的临时目录（`CONTACT_SOURCE_TEST_RUN_ROOT`）。仓库外临时产物不入库，提交的是本记录的脱敏结果。

## 结果总览

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 完整 prepare：候选外正文一句 + 旧合法候选 | 通过 | `SourceItemsTests.test_build_and_import_accept_quote_outside_candidates` OK；`Ran 8 tests / OK`（`source-items.out`） |
| T2 旧 prepare 无 source_pages，缓存补必要坏页 | 通过 | `OldPrepareWithCacheTests.test_required_page_cache_reaches_prepare_and_transport` OK；缺缓存变体 `OldPrepareWithoutCacheTests.test_missing_required_cache_blocks_upload_without_pdf_fallback` OK |
| T3 错页 / 改写原话 / 源 PDF 变化 | 通过 | `RejectedSourceItemsTests` 三个变体分别 OK，均 `external_future_work_invalid` 或 `external_result_hash_mismatch` |
| T4 旧 exact 非空候选 + 旧协议拒绝候选外引文 | 通过 | `LegacyExactContractTests` 两个用例 OK，sidecar 保留原引用/页/ID |
| T4 旧 hybrid OCR 选择器（只执行指定一条） | 通过 | `Ran 1 test / OK`（`legacy-hybrid.out`） |
| T5 生成说明、两 runtime 与 SKILL 人工阅读 | 通过 | 见下文 T5 逐项观察与引用位置 |
| shard 索引检查 | 通过 | `python3 scripts/check_test_shards.py`：`OK: 83 test modules across 4 shards, each with a stage`（`shards.out`） |
| 仓库既有回归（非必测，实现自检） | 1143 项中 3 项失败，均在 PR head 同样失败，与本轮修改无关 | 见“既有回归的既有失败” |

T1–T4 模块入口（测试计划第 4 步）：

```bash
export CONTACT_PAPER_ANALYSIS_SKILL=/nix/store/vvdass0s4x1b2h46sqk29dq7rdbjbmr8-paper-analysis-0.1.0/payload/skills/paper-analysis
export CONTACT_PAPER_ANALYSIS_AGENT=/nix/store/vvdass0s4x1b2h46sqk29dq7rdbjbmr8-paper-analysis-0.1.0/codex/agents/paper-analysis.toml
export CONTACT_PAPER_ANALYSIS_PYTHON=/nix/store/447smjkzgapdxqrcdg8r8kf8j1a1jrxc-python3-3.14.7-env/bin/python3
export CONTACT_SOURCE_TEST_RUN_ROOT="$RUN/tmp"
"$CONTACT_PAPER_ANALYSIS_PYTHON" -B -m unittest discover \
  -s .apm/skills/professor-contact/tests \
  -p 'test_stage2_chatgpt_handoff_source.py' -v 2>&1 | tee "$RUN/source-items.out"
```

结果：`Ran 8 tests in 17.601s`、`OK`、退出码 0，无 skip。

## 逐项结果

### T1 完整 prepare：候选外正文、原 PDF 不变、facts join

`SourceItemsTests.test_build_and_import_accept_quote_outside_candidates` OK。断言覆盖：

- manifest job：`source_mode=local`、`future_work.selection_contract=source-items-v1`、`ocr_required_pages=[]`、`text_transport.page_count=7`、`missing_text_pages=[]`；
- ZIP 内无 PDF；bundle 内 prepare/candidates 的 SHA256 与 manifest 一致，`prepare.pdf_sha256 == job.input_sha256`；运输文本每页与 prepare `source_pages` 逐页相同，候选外句 `Our next study will validate the pipeline on multilingual documents.` 在第 2 页且不在 `candidates.json`；
- import 后正式 sidecar 含两条（候选外引用 + 原候选），页、`source_pdf_fingerprint`、候选 ID 保留；候选外条目的 ID 等于该引文的规范化 SHA256；`facts.future_work_ids` 与 sidecar 两条 ID 精确一致；
- 原 PDF 字节未变，handoff 目录无 PDF 副本。

### T2 旧 prepare：统一补齐与必要坏页

`OldPrepareWithCacheTests.test_required_page_cache_reaches_prepare_and_transport` OK：5 页合成 PDF（末页空白），旧 prepare 去掉 `source_pages`/`ocr_resolved_pages`，`<pdf>.llm_ocr.pages.json` 为第 5 页提供精确页文字。结果：

- build 用真实 `future_work.py prepare` 重新生成完整 prepare，再用 `pdf_runtime.py validate-ocr-cache` 校验页缓存，最后经 `merge-ocr` 合并；
- bundle 内 prepare `ocr_required_pages=[]`、`ocr_resolved_pages` 含 5、第 5 页正文等于缓存文字；运输文本第 5 页与该 prepare 相同，`missing_text_pages=[]`；
- 调用者原 prepare/candidates 字节未变。

`OldPrepareWithoutCacheTests.test_missing_required_cache_blocks_upload_without_pdf_fallback` OK：同一路径缺必要缓存时 `upload_ready=false`、`bundle_path=null`、`bundle_dir=null`、`text_preparation=[{item_key:T2, pages:[5]}]`，handoff 目录无 `stage2-*.zip`、无 PDF 副本，原输入字节不变。

### T3 三个拒绝变体

- `test_wrong_physical_page_is_rejected`：引文放到第 1 页 → `external_future_work_invalid`，未安装 analysis/sidecar/index。
- `test_rewritten_quote_is_rejected`：把 `documents` 改成 `papers` → `external_future_work_invalid`，未安装。
- `test_changed_source_pdf_is_rejected`：build 后改写原 PDF → `external_result_hash_mismatch`，未安装。

三项都没有改输入或放宽匹配。

### T4 旧协议兼容

- `test_legacy_exact_bundle_keeps_candidate_only_scope`：旧 `exact-items-v1` 包（无 `source_mode`/`text_transport`，ZIP 内嵌原 PDF）导入合法非空候选成功，sidecar 保留引用、页、原 ID。
- `test_legacy_exact_bundle_rejects_quote_outside_candidates`：同一旧包提交候选外引文 → `external_future_work_invalid`，未安装。
- 旧 hybrid 只执行测试计划指定的一条：`test_ocr_required_selection_rebinds_after_merge_without_external_candidate_id` OK（`merge-ocr` + 唯一绑定 + validate/finalize 调用可见）。

### T5 生成说明、两 runtime 与 SKILL 人工阅读

逐项读过的位置与本轮结论：

| 材料 | 位置（被测提交） | 观察 |
| --- | --- | --- |
| 生成说明 `_instructions()` | `scripts/stage2_chatgpt_handoff.py` web adaptation 段与第 4 步 | 新契约 `source-items-v1` 明写“从 `text_transport` 已读正文中作者明示的待做事项选择；bundled candidates 只作阅读优先提示、不构成边界；页码用引文实际所在的物理页；不得改写引文、不得换页、不得索取原 PDF 或页图”；`exact-items-v1`/`ocr-excerpt-v1` 只作为旧包兼容说明 |
| Codex analyzer 全局原则 | `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md` 第 34 行 | 改为“任何已读正文里作者明说的待做事项，不按章节名排除；绝不把局限或读者建议推断成作者承诺；局限本身仍不挖，但作者在局限节里明写的后续工作仍按明示选择” |
| Codex analyzer Step 4.5 A | 同文件第 277–278 行、第 701 行 | 文本准备与证据共用同一 prepare；旧 prepare 用 `future_work.py prepare` 补齐；required 页缺正文只报 `upload_ready=false`；新契约从正文选择、页码取实际物理页；6.5 的 gap 来源改为“可从任何已读正文选择明示事项，不得从局限性/摘要预览/读者建议推断未明示计划” |
| Codex analyzer Step 4.5 C | 同文件第 303–304 行（`cba85a5`） | 导入按 manifest 的 `selection_contract` 分支：`source-items-v1` 用完整 prepare 交本地 validate/finalize；旧 `exact-items-v1` 候选封闭、旧 `ocr-excerpt-v1` 原 merge-ocr，且只用于已存在的旧包；`status=imported` 段改为“这些已导入 jobs” |
| OpenCode analyzer 全局原则与 Step 4.5 A/C | `packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md` 第 49、285–286、311–312、707 行 | 与 Codex 同口径，业务文字一致，只保留各自 runtime 的调用差异；C 段同样按 `selection_contract` 分支并标明旧契约只用于旧包 |
| SKILL handoff 简短说明 | `.apm/skills/professor-contact/SKILL.md` 第 123、125 行 | 新包契约为 `source-items-v1`；运输文字与 future-work 证据共用同一份 prepare；旧两契约只用于旧包 |

两份 runtime 说明都没有新增全文 pass、额外模型或上传 PDF 的步骤；`_impl._instructions`（废弃分支）未改，真实 wrapper 的 `_instructions()` 已更新。

## 实现自检：仓库既有回归

用同一解释器跑完 `.apm/skills/professor-contact/tests` 全量发现（`test_*.py`）：`Ran 1143 tests in 452.059s`，3 项失败、6 项跳过。3 项失败在 PR head（未含本轮实现）同样失败，属既有环境问题：

1. `test_text_only_and_original_source_record_with_allowed_blank_page`：macOS `/var` 与 `/private/var` 同一临时目录的两个路径形式；PR head 上同样失败，Linux CI 不受影响。
2. `test_stage2_input_router.Stage2InputRouterTests.test_unreadable_export_is_item_error_without_leaking_content`（两个子用例）：在 PR head 的 `pr143-test-preparation` 工作树用同一解释器复跑，同样 `FAILED (failures=2)`，与本轮修改无关。

README 未把这两项列为通过条件；本记录不把它们算作本轮回归。

## 对既有测试的必要修订

批准的方案替换了两处旧行为，`tests/test_stage2_chatgpt_handoff_text.py` 中直接断言旧行为的 3 个用例随之更新（未新增必测项）：

| 用例 | 旧断言 | 修改后 |
| --- | --- | --- |
| `test_old_prepare_regenerates_full_prepare_from_installed_helper`（原 `test_old_prepare_uses_installed_extract`） | 旧 prepare 走 `pdf_runtime.py extract` | 旧 prepare 走一次 `future_work.py prepare`，写入完整 `prepare.json`/`candidates.json` 后 `upload_ready=true` |
| `test_fulltext_cache_only_fills_bad_pages_through_merge`（原 `test_fulltext_cache_valid_or_stale_reuses_or_falls_back`） | 有效全文缓存直接替换整篇运输文字 | 全文缓存只给坏页提供精确文字并经 `merge-ocr` 回写；可读页仍保留 prepare 原文，缺缓存时该页仍记缺页 |
| `test_page_cache_resolves_bad_page_through_merge`（原 `test_page_cache_and_actual_resolved_text`） | 页缓存文字由 builder 直接写入运输文本 | 页缓存只经 `validate-ocr-cache` 与 `merge-ocr` 生效；无缓存时 `upload_ready=false` |

这三处变化对应执行计划 A.2、A.3 的明确要求（旧 prepare 用 `future_work.py prepare` 补齐；另一份全文缓存不得独立覆盖运输文字），不是放宽预期。

## 补充：契约兼容性修订与最终候选

首轮正式执行停在 `0149e18`，执行记录提交为 `dbfb109`。之后按执行计划 B.1“旧两个 contract 按原逻辑验”复核了 `_verify_manifest_integrity` 的接受集合，并提交 `0eed997`：

- 旧 `exact-items-v1`（`required_pages` 为空）与 `ocr-excerpt-v1`（`required_pages` 非空）恢复为原规则，仍接受；因此基线实现产出、已声明 `exact-items-v1` 的旧文本包仍能按其候选封闭语义导入，不被新契约改写。
- `source-items-v1` 仍只允许 local + `text_transport` + `required_pages` 已解决的 PDF job；未知 contract 仍拒绝。
- `_build_manifest` 的选择逻辑未变：新文本包固定声明 `source-items-v1`。

改动只影响 manifest 契约校验的接受集合，T1–T4 覆盖的行为未变；在该提交上重跑 `test_stage2_chatgpt_handoff_source.py`：`Ran 8 tests`、`OK`；handoff 既有 48 项仍只有上面那项 macOS 路径形式失败。CI（四个 shard 与聚合 `test`）在 `0eed997` 全部通过。

实现符合性审核在 `0eed997` 给出“部分完成”，指出三项（P1 两 runtime 的 Step 4.5 C 仍写旧 exact 协议、P2 同时缺 required 与 untrusted 页时只报 required、P3 本记录未覆盖 `0eed997` 且 T5 未读 C 段）。`cba85a5` 处理 P1/P2，P3 由本记录补齐：

- P1：两份 analyzer 的 C 段改为按 manifest 的 `future_work.selection_contract` 分支——`source-items-v1` 把完整 prepare 交给 `validate`/`finalize`，旧 `exact-items-v1` 保持候选封闭、旧 `ocr-excerpt-v1` 保持 merge-ocr，两者只用于已存在的旧包；“这些 exact jobs”改为“这些已导入 jobs”。
- P2：`_stage2_handoff_text.prepare_text` 现在把全部未解决的 required 页与 untrusted 页一起放进 `text_preparation.pages`（原因仍按 required 优先）；`upload_ready` 行为不变。

`cba85a5` 的复跑（同一解释器与 helper）：

```bash
cd .apm/skills/professor-contact/tests
"$CONTACT_PAPER_ANALYSIS_PYTHON" -B -m unittest test_stage2_chatgpt_handoff test_stage2_chatgpt_handoff_text \
  test_stage2_chatgpt_handoff_review test_stage2_chatgpt_handoff_review3 \
  test_stage2_chatgpt_handoff_review4 test_stage2_chatgpt_handoff_review5
```

结果：`Ran 48 tests`、1 项失败（只有本记录已说明的 macOS 路径形式）、1 项跳过；T1–T4 模块 `Ran 8 tests`、`OK`；旧 hybrid 指定项 `Ran 1 test`、`OK`。P2 的页面报告另用一次性诊断（/tmp，不入库）确认：required 与 untrusted 同时缺缓存时报告 `[2, 3]`，仅 untrusted 时报告 `[2]`，仅 required 时报告 `[3]`，允许的非 required 空页仍为 `upload_ready=true` + 缺页标记 `[3]`。

最终候选为 `cba85a5`；本轮改动不涉及 `flake.lock` 或其它依赖。

## 未完成项与下一负责人

- 已在 `cba85a5` 上完成 T1–T5 与 shard 索引检查（shard 索引在首轮 `0149e18` 运行，结论 `OK: 83 test modules`；本轮未改测试模块或 shard 登记，结论继续适用）；T1–T4、shard 均通过，T5 通过人工阅读（含 P1 修订后的 Step 4.5 C 段）。
- 本轮没有真实回放生产教授目录、Zotero 或私有 PDF（执行计划明确不要求），也没有重跑全文模型。
- 下一负责人：实现符合性审核（implementation_reviewer）；通过后由本地执行工程师推送并更新 PR。本记录不构成合并批准。
