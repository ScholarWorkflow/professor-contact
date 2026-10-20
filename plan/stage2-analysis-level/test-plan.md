# U5：实际分析级别贯通与诚实统计测试计划

- Test plan revision：u5-analysis-level-t3（2026-10-21）。唯一完整文件为 `plan/stage2-analysis-level/test-plan.md`。t3 按测试计划审核意见修正执行步骤和分片记录，补齐 L6 已在执行计划 r3 规定的修订缓存行为检查；L1–L6 业务目标与验收范围不变。尚未执行的新断言不得记为通过。
- 对象：[PR #106](https://github.com/ScholarWorkflow/professor-contact/pull/106)，对齐 [执行计划 r3](https://github.com/ScholarWorkflow/professor-contact/blob/12fbaaaf89a1fc6cdc082228c526dd9e3ee3f6f9/plan/stage2-analysis-level/implementation-plan.md)。2026-10-20 用户授权编写测试计划；同一日的后续指令授权按执行计划实现产品、运行适用测试并把结果更新到本 PR。
- 已读源码基线：main `879982abe1d7d811bd9d014c03dce4f5912cc64f`，包含 Stage 2 拆分及 shared/input-pack 提取。该版本用于定位现有资产，不声称已实现 U5。实际受测产品／测试版本已在 §4.0 固定。
- 当前状态：第一关口 L1–L6 清单已获本轮审核通过，目标不变；第二关口依据审核意见修订步骤，待复核；第三关口已有执行结果保留，L6 修订缓存行为的断言已补入既有生命周期方法，并在测试提交 `231ba03` 定向复验通过；L6 的检查已完成，但第三关口结论仍待独立测试审核。本文不把作者记录当作独立测试批准，也不继承 #92 的结论。

## 1. 范围、依据和结束条件

仅检查已确认的实际全文／摘要／未确认级别贯通、现有成员统计，以及本修复直接改变的 canonical 合流、缓存分流和受管接受生命周期。依据执行计划 r3 §1、§4、§6，以及 [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 和 [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)。以下清单是本项验收上限；引用既有文件仅用于复用对应资产，不引入其全部用例或前置。

不要求 #92 整套矩阵、旧关口补审、全教授流程、Stage 3/4、全文分析质量、引用/归属/时效重新验收、通用来源认证、组合穷举、重复安装或两 harness 完整业务回归。不为该确定性状态修复新增模型 eval、专用采集器、判定器或测试框架。Codex/OpenCode 的本次 analyzer 文档差异作一次静态契约核对；级别与分流的业务结果由下面同一 runner 入口检查，不在两边重复证明。

每个目标只选一个足够的入口，可以让同一夹具运行同时检查多个目标。共享接受逻辑已有当前有效结果时直接复用；引用并说明适用性即可，不因计划／文档 SHA 或后续 U1 合入而重跑。U5 可独立验收，无需 U1 标记或 owner map；U1 先合入时复用同一接受实现和有效断言，U5 仅补级别／统计的差异，不再复制第二套接受回归。全部清单取得当前有效结果且范围内已知缺陷处理后结束，不另加最终全仓回归。

## 2. 最小充分必测清单

### L1 实际成功级别，不以载体或 facts 状态猜测

- 目标／依据：r3 §4.1。facts 只传播当前成功登记的实际级别，未知诚实保留；本项不重新测试分析器生成质量。
- 输入／场景：复用已有成功登记样本，包含 fulltext（OCR-only、facts unavailable）与 abstract；另以存在 PDF/分析 Markdown 但没有可确认成功级别登记的样本检查 unknown。沿同一读取入口对原摘要有效但全文升级失败的状态、原来源已失效的状态作直接对照；不枚举所有失败原因。静态核对两 analyzer 都传相同字段、成功登记后才使用，并消费第三分支。
- 预期：分别为 fulltext、abstract、null；升级未成功不得虚报全文，原摘要仍有效则仍为 abstract，原来源确已失效则 null，下一次读取不得由残留旧包复活已知值。非法 level／事实与当前已知登记冲突按既有输入错误处理，不任选一个已知值；缺失或显式 null 不算非法输入。仅选一个非法值代表该拒绝分支。
- 检查入口：实现后的 facts／级别读取正式入口，观察返回的 facts paper 字段或原错误结果；直接使用已认可 index 和文件样本，不重新证明其生成历史。已有外部 import 成功登记断言作为上游资产复用，不重复跑导入再证明下游传播。

### L2 canonical 合流和旧包兼容，当前 null 必须覆盖

- 目标／依据：r3 §4.2、§4.4.1。fresh/reused/resolved/old fallback 均携带同一当前值，旧原始包不被兼容化或候选回填改变。
- 输入／场景：同一现有 pack/finalize 夹具，最小选取实际不同合流入口，原值 fulltext、当前值 null；已知值正常传播沿 L1 的样本复用。读取旧 schema 2 缺字段包并构造 candidate；如实际修改触及 v1 canonical 迁移，则在已有迁移入口仅检查缺字段与显式 null 等价及已知值冲突仍拒绝，不展开历史迁移矩阵。
- 预期：最终 canonical papers 全部采用当前核实值，null 不被旧值补回；成员/reference 均保持同一规范记录。schema 2 不升级，旧缺字段在兼容视图视为 null，但原始旧文件及用于旧完整性／validator 核验的深快照保持原内容；reused/resolved 嵌套修改不得污染旧侧。
- 检查入口：现有 finalize/normalize 资产中的结构化 pack 断言和旧快照前后比较；只覆盖实际不同合流代码，不把四分支与全部 level/来源/validator 状态做笛卡尔组合。旧包绑定保护的最终接受结果归 L5，同一运行可一并观察。

### L3 仅统计既有方向成员，三类互斥且总数正确

- 目标／依据：r3 §1、§4.2。改正统计而不改变成员或引文资格。
- 输入／场景：一个确定性 pack 含三种级别的 supporting 成员、一个 reference/relevant-only 论文，以及跨方向共享的成员；复用已有有效方向拆分／合并产物作为输入，不重新运行决定成员的业务。
- 预期：现有统计位置输出“全文级 X 篇 · 摘要级 Y 篇 · 未确认 Z 篇（共 N 篇）”，三类总和等于原 supporting 成员投影；reference/relevant-only 不计入，跨方向共享成员按原成员贡献计数，不额外去重。成员 key、顺序、身份和引用许可不因级别变化改变。
- 检查入口：现有 renderer 接受 canonical pack 后的实际 Markdown 标题及 pack 的 supporting_item_keys；在同一断言检查统计关系，不另造统计 oracle 或再跑全流程。

### L4 早期分流：纯 level 刷新不能吞业务变化

- 目标／依据：r3 §4.3–4.4。有限来源与 level 分开比较，正常复用不扩大离线承诺。
- 输入／场景：同一有真实接受投影和合法旧校验的基线依次作独立变体：完全不变；只改合法 level／本版统计格式尚未接受；业务来源变化（用原 missing 固定 facts 候选出现代表此前漏守卫的路径）；旧包缺新投影。另以已接受 PDF guard 及不变正式本地输入检查原离线复用，不另读 Zotero 或扫描 PDF。不可读／坏来源记录只选一个代表，区别于 L1 的明确未知。
- 预期：分别 reuse_all、refresh_level、process、process；级别本身及 index generated_at 等管理字段不造成业务变化。无法比较资格或来源转 process，不把坏记录当已知值。旧包 process 一次后只在真实成功接受时建立投影／统计标识，原有效模型缓存仍可复用。保留既有 validator 门槛；显式 chatgpt_result 或 kb_import=true 的路由仍优先 process，静态核对两 caller 的此分支即可，不运行外部导入全链。
- 检查入口：现有 preflight 返回 action 和持久 pack 的本次投影／格式标识；基线必须实际满足其声称的复用前提。使用现有 no-PDF-read 断言检查离线用法，不新增全调用 trace。若方法在同一 runner 测试内已覆盖，L5 的 refresh 不再次证明这些分流变体。

### L5 级别刷新及普通 finalize 共用有限接受，不救活无效认证

- 目标／依据：r3 §4.4。实际 body、业务依据和原绑定分别决定是否接受及保留校验，避免仅看统计或完整包 hash。
- 输入／场景：在同一现有受管文件夹具检查三个必要结果：①级别使实际统计正文变化；②两篇互换 level、聚合不变且实际 body 等价、业务未变；③业务依据变化但实际正文碰巧相同（普通 process/finalize）。②再用一个原绑定无效样本检查不能重绑救 PASS。兼容旧包样本复用 L2；首建正常成功结果可与 L2/L3 合并观察。
- 预期：①受保护接受新 body，旧认证失效且原报告保留；②只忽略 renderer 固定顶部生成时间，保留统计文字与其他正文的实际比较，等价时保留旧 body 原字节／真实 SHA，原合法 round/phase/pending 不清零，必要头和完整包绑定可更新；③保 body 但旧业务认证失效。无效旧绑定且 body、业务均未变必须按原证据错误返回，不能由 candidate 反填旧侧或重绑成 PASS。完整包摘要因字段／缓存改变本身不等同业务变更。
- 同一接受观察还须确认：刷新只改 level、统计接受缓存与必要绑定，不动成员、assignment、模型结果、业务指纹或 resolved proof；cache 按所有权合并而不清除其他仍有效 render 字段；成功接受后才登记本版标识。refresh 仅使用持久 pack，不要求临时 facts 或模型工作。普通 finalize 和新增 handler 实际共享的检查复用一次，只有二者独有接线分别检查，不复制完整场景。
- 检查入口：runner 的实际受管输出、canonical pack、原 validator/report 和现有 jobs／依赖替身断言。正式测试中的替身只隔离无须执行的外部工作，不替产品传值或替换业务输出。没有重新设计来源证明、header 认证或额外渲染协议。

### L6 刷新写入保护及原 refine 轮次的直接影响

- 目标／依据：r3 §4.4、§6.3。新增 writer 不绕过已有保护；原 refine 不清轮次、不误删仍有效的缓存。缓存检查属于本次修改直接改变的现有行为，不增加独立测试目标。
- 输入／场景：沿 L5 夹具，只检查新增刷新入口直接触及的拒绝点：已有 writer busy；取得 lease 后、写入前输入漂移；受管 body 已人工修改。用现有 unittest 替身在实际 pack 持久调用处模拟一次写 Markdown 后的 I/O 失败，不新增故障框架。复用原 round1 修订→round2 测试，并在合法的原校验绑定下为修订前的 pack 预置一项其他仍有效的 `cache` 子项和一项无关的 `cache.render` 记录；调用原 `stage2-refine-finalize` 后比较前后持久状态，不另建修订流程。
- 预期：busy 零业务写入；漂移零业务写入返回 needs_refresh；人工修改沿既有 needs_decision 不覆盖。自持 lease 在成功／拒绝／异常后走现有 finally release，不借别人的 token，也不在普通路径重复拿锁；release 故障不得报告已解除。部分 I/O 失败如实未完成、不伪造跨文件回滚或成功标识，下一次既有绑定守卫不得直接 reuse。refine 保持原轮次转换和清除 `cache.preflight` 的规则，不重置为 round1；当前 `cache.render[套磁候选分析.md].sha256` 更新为实际接受的正文摘要，其他仍有效的 `cache` 子项和 `cache.render` 记录保持原值。
- 检查入口：原 lease／managed write／refine 测试入口的返回结果、目标文件、锁及 pack 状态；在 `Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle` 的既有修订入口补充一次缓存前后断言。该方法既有轮次断言继续复用；补充的缓存断言通过前，L6 不得整体记为通过。不穷举失败阶段，不重做校验业务，也不新增判定器。

## 3. 已有资产及复用边界

以下路径均位于 `.apm/skills/professor-contact/tests/`，已按上述 main SHA 阅读；它们是接线候选，不是 U5 已通过的结果，也不是整文件必跑清单。

- `test_stage2_chatgpt_handoff.py`：`HandoffTests.test_valid_result_installs_analysis_sidecar_and_index` 已断言成功 import 登记 fulltext；`test_ocr_only_fulltext_build_and_import_without_pdf` 已断言 fulltext 与 facts unavailable 共存。用于 L1 上游事实资产，不要求重做导入或运行模型。
- `test_stage2_facts_sidecar.py`：`FactsSidecarTests.test_valid_facts_sidecar_is_normalized_into_the_pack` 提供 facts→pack 的现有夹具；`test_facts_sidecar_change_invalidates_direction_reuse` 已检查事实副车变化后 process，可复用该断言方式接 L1/L2/L4，不将 sidecar 所有安全分支搬入 U5。
- `test_stage2_preflight.py`：`PreflightBase.build_accepted_state`、`TestPreflightDecision.test_b_perfect_no_change_reuses_without_pdf_reads` 提供真实接受基线及不读 PDF 入口；`test_c_target_note_change_invalidates_only_that_direction`、`TestFinalizePreflightWiring.test_finalize_race_on_target_change_writes_nothing` 提供业务变化／写前漂移的现有断言。接 L4/L6 时补真实 U5 接受投影，不能手填成功标记制造通过前提。
- `test_contact_state.py`：`BaseEnv` 与 `TestRunnerBasics.test_13_stage2_validator_rewrite_round_trips_structured_narrative` 提供规范 pack、受管输出及修订轮次入口，可接 L2/L3/L5/L6。
- `test_stage2_style_validation_handoff.py`：`Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle` 包含业务重渲染、旧报告保留及原两轮生命周期；`test_stage2_report_for_stale_render_is_rejected_without_pack_write` 包含旧 render 拒绝断言。只复用与 L5/L6 对应的子目标／资产，不把其完整旧 T5 场景或全部历史义务设为本项前置。

本轮补 U5 专用断言时复用了这些资产提供的夹具与入口（§4 记录实际选择器与命令），没有把它们的整文件必跑清单设为本项前置。新增方法名、选择器和 CLI 参数均以真实实现为准。

## 4. 执行接线与结果记录（本地执行工程师）

本节记录已经执行的步骤与结果，并指定尚未执行的定向补测；执行记录本身不代替独立审核。

### 4.0 固定的产品与测试版本

- 产品与测试提交（历史全量记录）：`0b9a585bc3d43d7d42a7fa341c89cf161fbda7a3`（含 `dd9d1d5` 产品或测试主线、`87984db` 的 L1/L5 补充和 `62ca3fd`/`0b9a585` 对首次实现符合性审核 IR-1…IR-5 的修复；父提交 main `4cfcf49`，已推送到 PR #106 的 head 分支 `plan/u5-analysis-level-redesign`）。本节的记录写在紧随其后的 docs 提交里；doc 改动不触碰产品或测试代码，上述执行结果仍对 `0b9a585` 有效。
- L6 定向复验的测试提交：`231ba03bdeeb2da71aa7fa01334f346e1b7f27b4`（`bff99aa` 补入 §2 L6 缓存断言，`231ba03` 只修正该处注释；产品代码自 `0b9a585` 起未再变化）。命令、`run_dir` 与结果见 §4.3；该记录写在其后的 docs 提交里，不改变已运行的测试代码。
- 环境：macOS，`python3 --version` = 3.14.7；只使用标准库 unittest 与仓库内现有夹具，无新增依赖。
- 隔离：每个测试用例使用独立 `tempfile.TemporaryDirectory()` 作为 program root；不读用户 Zotero、真实 PDF、私有配置或生产状态。新增测试在 L4/L6 的 guard 场景通过现有 `Path.read_bytes` / `atomic_write` 替身隔离外部工作。
- 新增正式测试：`.apm/skills/professor-contact/tests/test_stage2_analysis_level.py`（34 tests），已登记 `plan/test-grouping/shards.json`（stage2 / shard3）。
- L6 的缓存断言位于既有 `.apm/skills/professor-contact/tests/test_stage2_style_validation_handoff.py` 的 `Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle`（shard4），不新增测试方法，也不改变 34 tests 的新模块。
- 唯一完整原始输出：`/tmp/u5-formal4-20261020/module.log`（新模块单独运行）与 `/tmp/u5-formal4-20261020/suite.log`（四 shard 全量）；均在仓库外临时目录，按共识不提交。
- L6 定向复验原始输出：`/tmp/u5-l6-cache-555AG2/refine.log`（单个受影响方法）；同样在仓库外，不提交。

### 4.1 准备顺序与命令

原正式执行已完成新模块与四个分片，输出见 §4.3；这些执行结果作为历史记录保留，不要求因文档修订重跑全仓。现有新模块及分片登记可通过下列命令复现（当前没有重复执行义务）：

- 在仓库根目录执行 `python3 scripts/check_test_shards.py`，检查分片登记；仅在分片文件变更影响登记时补跑。
- 进入 `.apm/skills/professor-contact/tests`，执行 `python3 -m unittest test_stage2_analysis_level -v`。既有 34 项结果见 §4.3。

§2 L6 的缓存前后断言已补入既有修订方法；已在测试提交 `231ba03` 按以下完整命令执行一次定向复验，结果见 §4.3。从仓库根目录开始，复现命令为：

```bash
cd .apm/skills/professor-contact/tests
run_dir="$(mktemp -d /tmp/u5-l6-cache-XXXXXX)"
python3 -m unittest test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle -v > "$run_dir/refine.log" 2>&1
```

检查测试退出状态和 `refine.log` 中该方法的业务断言；记录实际测试提交、命令、`run_dir` 路径及结果。失败时保留输出并交对应负责人处理，不把失败改记为未执行；若测试步骤有误，先修订并复核受影响部分。使用现有 Python 标准库和测试夹具；用例以 `TemporaryDirectory` 隔离程序目录，不需要模型、网络、真实 Zotero/PDF 或重新安装。其他有效检查不重跑。

### 4.2 L1–L6 的实际检查入口与结果

| 目标 | 实际检查方法（唯一入口） | 结果 |
|---|---|---|
| L1 实际成功级别 | `TestFactsLevelContract`：`test_known_and_unknown_levels_reach_the_canonical_pack`（fulltext/abstract/null 进入 canonical papers，且 OCR-only 全文与 `facts_state=unavailable` 并存）、`test_facts_level_conflicting_with_the_current_registration_is_invalid`、`test_illegal_level_is_an_input_error`、`test_explicit_null_clears_a_registered_level`、`test_analysis_file_and_pdf_without_a_success_registration_are_unknown`（有分析文件+PDF 但无成功登记 → null）、`test_ocr_only_fulltext_without_facts_can_still_be_fulltext`（OCR-only 全文 + facts unavailable → fulltext）、`test_consumed_analysis_path_contradicting_the_index_is_invalid`（facts 实际消费路径与 index 登记矛盾 → `invalid_facts`）；静态契约 `TestAnalyzerContract.test_both_analyzers_pass_the_level_and_consume_the_refresh_branch` | PASS |
| L2 canonical 合流与旧包兼容 | `TestCanonicalMerge`：`test_known_level_survives_a_reuse_finalize_and_validator`（复用条目深拷贝、旧 validator 仍可携带）、`test_missing_level_field_in_an_old_pack_reads_as_null`、`test_v1_migration_treats_missing_and_null_alike_but_rejects_conflict` | PASS |
| L3 三类统计 | `TestStatisticsRender`：`test_header_counts_members_only_and_shared_members_per_contribution`（实际标题为 `全文级 1 篇 · 摘要级 2 篇 · 未确认 1 篇（共 4 篇）`，共享成员按两次成员贡献计数）、`test_reference_only_paper_stays_out_of_the_statistic` | PASS |
| L4 早期分流 | `TestPreflightBranches`：`test_unchanged_state_reuses_all`、`test_level_only_change_takes_the_refresh_branch`、`test_management_fields_do_not_change_the_business_source`、`test_new_fixed_facts_candidate_is_a_business_change`、`test_missing_projection_processes_once`、`test_illegal_index_level_processes_instead_of_writing_a_known_value`、`test_not_accepted_validator_blocks_reuse_all`；`TestAnalyzerContract` 对两份 analyzer 文档核对 `chatgpt_result`、`kb_import` 与 `禁止 early hard exit` 关键字（只断言关键字存在，不解析优先级的精确语法） | PASS |
| L5 级别刷新与有限接受 | `TestLevelRefresh`：`test_statistic_change_updates_body_and_expires_old_certification`、`test_equivalent_body_swap_keeps_the_valid_old_certification`、`test_invalid_old_binding_is_an_evidence_error_not_a_rebind`、`test_legacy_statistics_body_is_reaccepted_before_the_marker`、`test_business_change_with_equivalent_body_keeps_body_but_expires_certification`（业务依据变化但真实正文相同 → 保 body、旧认证失效）、`test_manual_body_edit_needs_decision_without_writing_the_pack`；比较基准 `TestGenerationTimeNormalization.test_only_the_generation_time_is_ignored`（含行尾/尾部字节不被规范化）；缓存与 resolved 保持 `TestRefreshProtection.test_refresh_keeps_the_accepted_sources_and_foreign_cache` | PASS |
| L6 写入保护与原 refine | `TestRefreshProtection`：`test_busy_writer_returns_without_any_business_write`、`test_binding_drift_returns_needs_refresh_releases_and_writes_nothing`、`test_successful_refresh_releases_the_lease`、`test_release_failure_is_reported_on_the_success_path`、`test_release_failure_on_a_soft_exit_is_also_reported`、`test_pack_io_failure_after_the_markdown_write_stays_unfinished`；原两轮生命周期复用 `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle` 在 `shard4` 的已有结果。该旧方法已按 §2 L6 补入 refine 前后缓存断言：预置其他有效 cache 子项与无关 cache.render 记录，核对 refine 后 `cache.preflight` 清除、当前 render SHA 与实际接受正文一致、其余缓存保持；既有 `_assert_t5_render_binding` 仍核对 render 缓存与正文一致。补断言后已在测试提交 `231ba03` 定向复验通过（§4.3）。 | 原有检查 PASS；修订缓存检查 PASS（`231ba03` 定向复验） |

`stage2-refresh-level` 的真实参数以 `contact_state.py build_parser()` 为准：`--program-root`、`--professor`、`--target-file`、`--preflight-file`，可选 `--decision-file`。返回 `ok`（新级别/统计/受管正文已接受）、`stage2_writer_busy`（零业务写入）、`needs_refresh`（预检漂移或渲染字段需走 process）、`needs_decision`（受管 Markdown 被人工修改）。L1 的统计观察直接读受管 Markdown 的统计行；L2/L4/L6 的结构化结果读 `套磁候选输入.json` 的 `papers`、`cache.preflight` 与命令 stdout；不另建判定器。

### 4.3 正式结果

- 新模块单独运行：`Ran 34 tests`，全部 OK（`/tmp/u5-formal4-20261020/module.log`）。
- 全量回归（同一提交）：shard1 `Ran 380 tests` OK；shard2 `Ran 219 tests` OK；shard3 `Ran 222 tests` OK；shard4 `Ran 243 tests` OK（1 skipped）。合计 1064 tests、1 skipped，无失败。
- `plan/test-grouping/shards.json` 的 `totals` 是分片规划的声明性估值（不是实测条数）；实测条数以上两行为准。
- L6 定向复验（测试提交 `231ba03`，执行者 local-execution-engineer，2026-10-21）：在 `.apm/skills/professor-contact/tests` 执行 `python3 -m unittest test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle -v`；`run_dir=/tmp/u5-l6-cache-555AG2`；退出码 0；`Ran 1 test in 7.785s`，`OK`。日志见 `/tmp/u5-l6-cache-555AG2/refine.log`。
- 当前结果：L1–L6 全部检查通过；L6 的 writer／异常／原校验轮次检查沿用 `0b9a585` 的通过结果，修订后的 refine 缓存保留断言在 `231ba03` 定向复验通过。现有记录无业务失败；L6 不再保留未执行项。
- 未执行且不在本清单范围：模型分析质量、#92 整套矩阵、Stage 3/4、外部 Zotero/handoff 全链、通用来源认证；按 §1 排除，不补做。
- 新模块与四分片结果固定为 `0b9a585`；本次只按 §4.1 在测试提交 `231ba03` 对 L6 受影响方法执行一次定向复验，未重跑其他检查。

### 4.4 未完成项与下一负责人

- 第二关口：§4.1 已删除四分片作为本轮必跑步骤的要求，改为仅复验 L6 受影响方法；步骤修订待独立复核。
- 第三关口：§4.3 已有正式记录保留；L6 的 refine 缓存保留断言已按 §2 补入既有 `test_business_rerender_and_bounded_correction_lifecycle`，并已在测试提交 `231ba03` 定向复验通过，L6 的检查已完成。执行与结果登记由本地执行工程师按 §4.1 完成；测试审核者仍只复核该受影响项，L6 结果不代替第三关口的独立结论。
- 产品实现负责人：本轮按执行计划 r3 完成实现，并按首次实现符合性审核处理 IR-1…IR-5；后续只按具体受影响意见处理。
- 首次实现符合性审核（所审版本 `8568a3b`，产品 `dd9d1d5`）提出 IR-1…IR-5：IR-1 刷新覆盖已接受消费来源（由 `62ca3fd` 修复并补 `test_refresh_keeps_the_accepted_sources_and_foreign_cache`）、IR-2 接受时未核对实际消费来源（`0b9a585` 增加声明矛盾的 fail-closed 核对与对应测试）、IR-3 软退出路径不报告 lease 释放失败（`0b9a585` 在 `finally` 内统一报告并补两条替身测试）、IR-4 body 比较经 `splitlines` 规范化行尾（`0b9a585` 改为只替换时间戳 token）、IR-5 两个 analyzer 的 hard rule 与第三分支冲突（`0b9a585` 同步两个 harness）。上述修复后按当时确认的步骤运行新模块与四个分片，结果见 §4.3；IR-1…IR-5 的实现符合性定向复核已完成，记录见本节末条。
- 记录层面的修正（t3）：保留 §4.3 的既有运行记录和分片估值说明；更正原 refine 测试所属 `shard4`；撤销 §4.1 的四分片必跑命令及路径占位符；当时将 L6 尚缺的缓存行为检查列为未执行（已在 `231ba03` 定向复验完成），不要求重跑未受影响的测试。
- 定向复核结论（所审版本 `ce9e370`，产品与测试 `0b9a585`）：IR-1…IR-5 均按原编号关闭，结论由“部分完成”更新为“完整”；仅保留一条记录强度备注——L4 的静态断言只核对关键字出现，已在 §4.2 如实写明，不构成产品待办，也不扩大本轮测试义务。
- 测试准备实现审核（所审版本 `bff99aa`，R1 修正后 `231ba03`）：结论「完整（仅限测试准备阶段）」；R1 的预置注释已按审核意见修正并关闭。该结论不是 Gate 2、Gate 3 或合并批准。
