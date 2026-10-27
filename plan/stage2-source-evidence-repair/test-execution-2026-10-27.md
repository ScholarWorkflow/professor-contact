# Stage 2 来源证据措辞修复 — 测试执行记录（2026-10-27）

- 执行计划：EP2（`plan/stage2-source-evidence-repair/execution-plan.md`；独立审核 `Plan conclusion: APPROVED`，P1–P4 PASS）。
- 测试计划：TP2（同目录 `test-plan.md`；必测清单 R-A–R-D 为验收上限）。本次按 TP2 `Execution handoff / recipe status` 的精确 selector、环境块与命令运行。TP2 记录的 Gate2 仍是 PENDING（recipe 已由测试工程师补齐，独立 Gate2 审核不在本记录中宣称为通过）；Gate3 由独立 reviewer 采用本记录，不在此自批。
- 被测版本：运行时候选 `259cab0334878c2e7986d69464b938bf52fbe74d`（`feat(stage2): add the narrow source evidence wording repair entry`）；随后的文档契约修正 `20a4dd1` 只改 `SKILL.md` 与两个 analyzer 的说明文字，运行时路径与断言不变。测试资产来自 PR head `f59ff9a`（`test_stage2_source_evidence_repair.py`、TP2 recipe 与 shard 登记），实现与修正提交都未修改任何测试断言、selector 或预期结果。
- 实现范围：`stage2-repair-evidence` 命令（新模块 `scripts/_stage2_evidence_repair.py` 与 `contact_state.py` 接线）、`_stage2_finalize.py` 的定向投影、`SKILL.md` 与两个 analyzer 的说明。未改候选选择、状态、置信度、作者原文或其它 Stage 2–5 行为。
- 环境：macOS arm64；解释器 `/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3`（Python 3.14.7）；工作树 `/Users/rekidunois/code/skill-repos-dev/worktree/professor-contact-pr145-execution-20261027`。
- 运行目录：`/tmp/contact-evidence-repair.TJIIYQ`；正式尝试目录 `/tmp/contact-evidence-repair.TJIIYQ/attempt.xz7suW`（同时作为 `TMPDIR`）。其中 `target-version.txt`、`python-version.txt`、`r-a.log`/`r-a.exit`、`r-b.log`/`r-b.exit`、`r-c.log`/`r-c.exit`、`shards.out` 保存本次正式输出；用例自身临时目录也在该 `TMPDIR` 下，仓库内没有测试写入。本次没有正式重试，未覆盖任何先前输出。
- 预检复用：TP2 `Preparation and precheck record` 已记录 `py_compile`、selector 收集、fixture smoke 与 shard 检查；本轮在同一候选上补跑 shard 索引检查，未重复其已经有效的准备。

## 结果总览

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| R-A 部分 gap 三字段措辞进入投影 | 通过 | `Ran 3 tests in 3.732s / OK`，`r-a.exit=0`（`r-a.log`） |
| R-B 未授权、owner、陈旧输入与部分批次 | 通过 | `Ran 4 tests in 3.923s / OK`，`r-b.exit=0`（`r-b.log`） |
| R-C 人工改正文冲突与 no-op | 通过 | `Ran 2 tests in 3.024s / OK`，`r-c.exit=0`（`r-c.log`） |
| R-D 源数据说明与 CLI 契约 | 已执行（阅读判定） | 独立 `implementation_reviewer` 阅读 `SKILL.md` 与两个 analyzer，TP2 六个观察点均有位置；TP2 未设自动化 selector，本记录转录该阅读结论与位置 |
| shard 索引检查 | 通过 | `python3 scripts/check_test_shards.py`：`OK: 83 test modules across 4 shards, each with a stage`（`shards.out`） |
| 既有回归（非必测，实现自检） | 通过 | 253 项 `OK`（16 个直接受影响模块）+ 90 项 `OK`（`test_contact_state`）+ 20 项 `OK`（caller contract，文档修正后）；见“实现自检”与“推送后 CI 复核” |

## 逐项结果与观察

### R-A（3 项，一次普通 preflight → plan → finalize 周期）

- `test_r_a_partial_gap_three_field_wording_reaches_the_projection` OK。repair 返回 `needs_refresh` 并列出 `DIR00001`/`AAAA1111`；缓存只有 `model_evidence`、`completed_part`、`remaining_gap` 三处措辞变化，`status`、`confidence`、`candidate_paper_ids`、两个指纹、`evaluated_at`、`downgraded` 不变；命令没有改受管 Markdown、输入包与 validator 字节；随后 preflight `action=process` 且带 `freshness_cache_changed`，plan 为 `reuse`，finalize `ok`，shortlist 行的三个字段与渲染正文都是新措辞，旧 validator 没有带入新包。
- `test_r_a_blacklist_evidence_projects_the_repaired_model_evidence` OK。`done_by_self` 的 `blacklist_evidence` 授权并映射到 `model_evidence`；禁锚卡 `evidence` 显示新文本，`completed_by_item_key`、`candidate_paper_ids`、题名、年份、置信度、`evaluated_at` 不变；同一方向的部分 gap 保持自己的证据。
- `test_r_a_reused_direction_projects_the_repaired_evidence` OK。两个方向都走 `reuse`，两行 shortlist 与两条 `- 后续论文依据：` 都显示新措辞，已接受叙事未变。

### R-B（4 项，命令级负例）

- `test_r_b_finding_on_one_field_does_not_authorize_the_other_fields` OK。只登记 `evidence` 时，`completed_part` 与 `remaining_gap` 被拒（结构化 `status=error` + `reason_code`），所有文件字节不变。
- `test_r_b_quote_and_generator_findings_keep_their_owner` OK。`quote`（`owner=source`）与 `label`（`owner=generator`）都不授权缓存字段；拒绝结果里出现 `generator`，文件字节不变。
- `test_r_b_stale_expectations_are_rejected_before_writing` OK。陈旧的缓存摘要、陈旧的校验报告摘要、与当前文本不符的 `expected_old_text` 三个输入各自被拒，文件字节不变。
- `test_r_b_a_batch_with_one_bad_row_writes_nothing` OK。混入未授权行与同一 direction/gap/field 的重复行都整批拒绝，零部分写入。

### R-C（2 项）

- `test_r_c_manual_markdown_change_keeps_the_conflict_path` OK。人工改页后单次 finalize 返回 `needs_decision` 或 `error/validation_render_stale`，Markdown 与已记录 validator 不变；显式 `{"decision": "overwrite"}` 后 `ok`，人工标记被替换为新渲染、旧 validator 丢弃。
- `test_r_c_no_op_repair_changes_nothing_and_keeps_the_recorded_rounds` OK。两轮校验已到 `terminal`（round 2、`fail_after_2_rounds`）时提交与当前文本相同的替换，命令返回 `ok` 而不是 `pass`，缓存、Markdown、输入包与 validator 字节均不变，已记录轮次没有被重置。

### R-D 阅读判定与交付位置（无自动化 selector）

独立 `implementation_reviewer` 按 TP2 的六项观察点阅读以下三份文档，并在审核结论中确认六项均有位置；本记录转录该结论与位置，不把它转成关键词断言，正式 Gate3 仍由独立 reviewer 采用本记录判定。

- `.apm/skills/professor-contact/SKILL.md` 第 258 行：三字段白名单、显示字段到缓存字段的映射、每字段独立授权、语义由 source owner 核对、成功返回 `needs_refresh` 且需重新校验、no-op 不重置轮次、其它 owner 分流。
- `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md` 第 636 行：同一套白名单/映射/独立授权、`needs_refresh` 与非 PASS、重新 preflight→plan→finalize 和重新校验、其它 owner 分流。
- `packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md` 第 644 行：与 Codex 版本的同一组说明。

## 推送后 CI 复核与文档契约修正（非必测，不影响 R-A–R-C 结果）

- 首次推送后 CI run `40508820295`：shard2、shard3、shard4 通过；shard1 失败于 `test_stage01_caller_contract.test_issue64_t7_every_target_bound_command_names_the_local_target_file`——新增的 `SKILL.md` 句子在同一分句里写了 `stage2-preflight`，却没有 `--target-file`，触发既有 caller contract。该失败是文档契约回归，不是 R-A–R-C 的运行时结果，也没有改写任何产品行为。
- 修正提交 `20a4dd1`：`SKILL.md` 与两个 analyzer 的 resume 句改为显式 `stage2-preflight --target-file <教授目录>/套磁目标.json`。只改说明文字，不涉及命令实现或测试资产。
- 复核：`test_stage01_caller_contract` `Ran 20 tests ... OK`；`test_stage1_stage2_contract` + `test_stage2_source_evidence_repair` `Ran 26 tests ... OK`。R-A–R-C 的输入、断言与运行路径未变，按 Test Engineer Rule §6 复用已通过结果，不因文档提交重跑。
- 修正后 CI run `40509634189`（head `fa74ef9`）：shards 1–4 与聚合 `test` 检查全部通过。CI 不是 TP2 必测项，本记录只把它作为上述文档契约回归的复核结果，不写成必测项。

## 实现自检（非必测，不构成验收范围）

在同一候选 `259cab0` 上运行直接受影响的既有模块，全部通过：`test_stage2_fixed_evidence`、`test_stage2_analysis_level`、`test_stage2_style_validation_handoff`、`test_stage2_preflight`、`test_stage2_preflight_binding`、`test_stage2_preflight_malformed`、`test_stage2_resolved_direction`、`test_stage2_resolved_direction_acceptance_boundary`、`test_stage2_resolved_direction_downstream_regressions`、`test_stage1_stage2_contract`、`test_resolved_direction_preflight_integration`、`test_stage2_narrative_example_contract`、`test_stage2_resolved_direction_regressions`、`test_stage2_resolved_direction_fresh_review_regressions`、`test_apm_deployment_metadata`、`test_gate2_evidence`，合计 `Ran 253 tests ... OK`；另 `test_contact_state` `Ran 90 tests ... OK`。文档修正后又补跑 `test_stage01_caller_contract`（20 项 `OK`）。这些结果不替代 TP2 的四项，也没有据此增加测试义务。

## 未完成项与下一负责人

- Gate2：TP2 的 recipe 已可直接执行，独立 Gate2 审核尚未在本记录中确认；下一负责人为独立 Gate2 审核者。
- Gate3：由独立 reviewer 采用本记录并按业务结果判定 PASS/业务失败/无法判断/未执行；本记录不自行给出关口结论。
- R-D：已由独立 reviewer 阅读判定，记录的是阅读结论与位置，不是自动化断言；正式 Gate3 仍由独立 reviewer 采用本记录。
- 实现符合性审核：`implementation_reviewer` 已复核 259cab0–fa74ef9 的产物，结论为“完整（仅实现符合性）”，并在补记 `42a884c` 后复核通过；该结论不是 Gate2/Gate3 或合并批准。
