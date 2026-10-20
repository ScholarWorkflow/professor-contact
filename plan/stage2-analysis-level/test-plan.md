# U5：实际分析级别贯通与诚实统计测试计划

- Test plan revision：u5-analysis-level-t2（2026-10-20）。唯一完整文件为 `plan/stage2-analysis-level/test-plan.md`。t2 只补 §4 的真实执行接线与结果，不改 L1–L6 目标、预期或范围。
- 对象：[PR #106](https://github.com/ScholarWorkflow/professor-contact/pull/106)，对齐 [执行计划 r3](https://github.com/ScholarWorkflow/professor-contact/blob/12fbaaaf89a1fc6cdc082228c526dd9e3ee3f6f9/plan/stage2-analysis-level/implementation-plan.md)。2026-10-20 用户授权编写测试计划；同一日的后续指令授权按执行计划实现产品、运行适用测试并把结果更新到本 PR。
- 已读源码基线：main `879982abe1d7d811bd9d014c03dce4f5912cc64f`，包含 Stage 2 拆分及 shared/input-pack 提取。该版本用于定位现有资产，不声称已实现 U5。实际受测产品／测试版本待实施后登记。
- 当前状态：第一关口设计待独立复核；第二关口步骤已由本轮补齐、待独立复核；第三关口已按 §4.0 的真实提交执行并记录，待审核确认。本文不自授 APPROVED 或 PASS，不继承 #92 的结论。

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

- 目标／依据：r3 §4.4、§6.3。新增 writer 不绕过已有保护，也不把一次修复变成清轮次入口。
- 输入／场景：沿 L5 夹具，只检查新增刷新入口直接触及的拒绝点：已有 writer busy；取得 lease 后、写入前输入漂移；受管 body 已人工修改。用现有 unittest 替身在实际 pack 持久调用处模拟一次写 Markdown 后的 I/O 失败，不新增故障框架。另复用原 round1 修订→round2 的已有检查，将含新增 level/render 元数据的 pack 作为输入。
- 预期：busy 零业务写入；漂移零业务写入返回 needs_refresh；人工修改沿既有 needs_decision 不覆盖。自持 lease 在成功／拒绝／异常后走现有 finally release，不借别人的 token，也不在普通路径重复拿锁；release 故障不得报告已解除。部分 I/O 失败如实未完成、不伪造跨文件回滚或成功标识，下一次既有绑定守卫不得直接 reuse。refine 保持原轮次转换和清除 preflight 的规则，不重置为 round1，只保存仍有效的 render 元数据。
- 检查入口：既有 lease／managed write／refine 测试入口的返回结果、目标文件、锁及 pack 状态；本项不穷举所有失败阶段，不重复原 lease 协议或整个校验业务。共享接受保护已有适用结果时复用，仅新增 handler 的直接接线需覆盖。

## 3. 已有资产及复用边界

以下路径均位于 `.apm/skills/professor-contact/tests/`，已按上述 main SHA 阅读；它们是接线候选，不是 U5 已通过的结果，也不是整文件必跑清单。

- `test_stage2_chatgpt_handoff.py`：`HandoffTests.test_valid_result_installs_analysis_sidecar_and_index` 已断言成功 import 登记 fulltext；`test_ocr_only_fulltext_build_and_import_without_pdf` 已断言 fulltext 与 facts unavailable 共存。用于 L1 上游事实资产，不要求重做导入或运行模型。
- `test_stage2_facts_sidecar.py`：`FactsSidecarTests.test_valid_facts_sidecar_is_normalized_into_the_pack` 提供 facts→pack 的现有夹具；`test_facts_sidecar_change_invalidates_direction_reuse` 已检查事实副车变化后 process，可复用该断言方式接 L1/L2/L4，不将 sidecar 所有安全分支搬入 U5。
- `test_stage2_preflight.py`：`PreflightBase.build_accepted_state`、`TestPreflightDecision.test_b_perfect_no_change_reuses_without_pdf_reads` 提供真实接受基线及不读 PDF 入口；`test_c_target_note_change_invalidates_only_that_direction`、`TestFinalizePreflightWiring.test_finalize_race_on_target_change_writes_nothing` 提供业务变化／写前漂移的现有断言。接 L4/L6 时补真实 U5 接受投影，不能手填成功标记制造通过前提。
- `test_contact_state.py`：`BaseEnv` 与 `TestRunnerBasics.test_13_stage2_validator_rewrite_round_trips_structured_narrative` 提供规范 pack、受管输出及修订轮次入口，可接 L2/L3/L5/L6。
- `test_stage2_style_validation_handoff.py`：`Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle` 包含业务重渲染、旧报告保留及原两轮生命周期；`test_stage2_report_for_stale_render_is_rejected_without_pack_write` 包含旧 render 拒绝断言。只复用与 L5/L6 对应的子目标／资产，不把其完整旧 T5 场景或全部历史义务设为本项前置。

本轮补 U5 专用断言时复用了这些资产提供的夹具与入口（§4 记录实际选择器与命令），没有把它们的整文件必跑清单设为本项前置。新增方法名、选择器和 CLI 参数均以真实实现为准。

## 4. 执行接线与结果记录（本地执行工程师）

本节由本轮实现负责人补齐真实步骤并执行；它不代替独立审核，也不把结果写成正式 PASS。

### 4.0 固定的产品与测试版本

- 产品与测试提交：`87984db61f6d3de22f2cbbcb7b41669d27cb95ad`（其中产品代码为 `dd9d1d5`，`87984db` 追加 L1/L5 的三条必测覆盖；父提交 main `4cfcf49`，已推送到 PR #106 的 head 分支 `plan/u5-analysis-level-redesign`）。本节的记录写在紧随其后的 docs 提交里；doc 改动不触碰产品或测试代码，上述执行结果仍对 `87984db` 有效。
- 环境：macOS，`python3 --version` = 3.14.7；只使用标准库 unittest 与仓库内现有夹具，无新增依赖。
- 隔离：每个测试用例使用独立 `tempfile.TemporaryDirectory()` 作为 program root；不读用户 Zotero、真实 PDF、私有配置或生产状态。新增测试在 L4/L6 的 guard 场景通过现有 `Path.read_bytes` / `atomic_write` 替身隔离外部工作。
- 新增正式测试：`.apm/skills/professor-contact/tests/test_stage2_analysis_level.py`（30 tests），已登记 `plan/test-grouping/shards.json`（stage2 / shard3）。
- 唯一完整原始输出：`/tmp/u5-formal2-20261020/suite.log`（仓库外临时目录，按共识不提交）。

### 4.1 准备顺序与命令

在仓库根目录执行；测试在 tests 目录运行，与 CI 同构：

```bash
# 1) 分片清单完整（新增模块只能出现一次）
python3 scripts/check_test_shards.py

# 2) 本轮新增模块
cd .apm/skills/professor-contact/tests
python3 -m unittest test_stage2_analysis_level -v

# 3) 四个 CI shard 的全量回归（逐 shard 打印模块清单后运行）
modules="$(python3 <repo-root>/scripts/check_test_shards.py --print shard3)"
python3 -m unittest $modules -v
```

单个目标也可用 `python3 -m unittest test_stage2_analysis_level.<Class>.<method> -v` 定位；不需要安装、网络、Zotero、PDF 或模型。执行前后唯一需要清理的可变状态是各用例自建的临时目录，用例结束时由 `TemporaryDirectory` 清理；共享的 `plan/test-grouping/shards.json` 只读。

### 4.2 L1–L6 的实际检查入口与结果

| 目标 | 实际检查方法（唯一入口） | 结果 |
|---|---|---|
| L1 实际成功级别 | `TestFactsLevelContract`：`test_known_and_unknown_levels_reach_the_canonical_pack`（fulltext/abstract/null 进入 canonical papers，且 OCR-only 全文与 `facts_state=unavailable` 并存）、`test_facts_level_conflicting_with_the_current_registration_is_invalid`、`test_illegal_level_is_an_input_error`、`test_explicit_null_clears_a_registered_level`、`test_analysis_file_and_pdf_without_a_success_registration_are_unknown`（有分析文件+PDF 但无成功登记 → null）、`test_ocr_only_fulltext_without_facts_can_still_be_fulltext`（OCR-only 全文 + facts unavailable → fulltext）；静态契约 `TestAnalyzerContract.test_both_analyzers_pass_the_level_and_consume_the_refresh_branch` | PASS |
| L2 canonical 合流与旧包兼容 | `TestCanonicalMerge`：`test_known_level_survives_a_reuse_finalize_and_validator`（复用条目深拷贝、旧 validator 仍可携带）、`test_missing_level_field_in_an_old_pack_reads_as_null`、`test_v1_migration_treats_missing_and_null_alike_but_rejects_conflict` | PASS |
| L3 三类统计 | `TestStatisticsRender`：`test_header_counts_members_only_and_shared_members_per_contribution`（实际标题为 `全文级 1 篇 · 摘要级 2 篇 · 未确认 1 篇（共 4 篇）`，共享成员按两次成员贡献计数）、`test_reference_only_paper_stays_out_of_the_statistic` | PASS |
| L4 早期分流 | `TestPreflightBranches`：`test_unchanged_state_reuses_all`、`test_level_only_change_takes_the_refresh_branch`、`test_management_fields_do_not_change_the_business_source`、`test_new_fixed_facts_candidate_is_a_business_change`、`test_missing_projection_processes_once`、`test_illegal_index_level_processes_instead_of_writing_a_known_value`、`test_not_accepted_validator_blocks_reuse_all` | PASS |
| L5 级别刷新与有限接受 | `TestLevelRefresh`：`test_statistic_change_updates_body_and_expires_old_certification`、`test_equivalent_body_swap_keeps_the_valid_old_certification`、`test_invalid_old_binding_is_an_evidence_error_not_a_rebind`、`test_legacy_statistics_body_is_reaccepted_before_the_marker`、`test_business_change_with_equivalent_body_keeps_body_but_expires_certification`（业务依据变化但真实正文相同 → 保 body、旧认证失效）、`test_manual_body_edit_needs_decision_without_writing_the_pack`；比较基准 `TestGenerationTimeNormalization.test_only_the_generation_time_is_ignored` | PASS |
| L6 写入保护与原 refine | `TestRefreshProtection`：`test_busy_writer_returns_without_any_business_write`、`test_binding_drift_returns_needs_refresh_releases_and_writes_nothing`、`test_successful_refresh_releases_the_lease`、`test_pack_io_failure_after_the_markdown_write_stays_unfinished` | PASS |

`stage2-refresh-level` 的真实参数以 `contact_state.py build_parser()` 为准：`--program-root`、`--professor`、`--target-file`、`--preflight-file`，可选 `--decision-file`。返回 `ok`（新级别/统计/受管正文已接受）、`stage2_writer_busy`（零业务写入）、`needs_refresh`（预检漂移或渲染字段需走 process）、`needs_decision`（受管 Markdown 被人工修改）。L1 的统计观察直接读受管 Markdown 的统计行；L2/L4/L6 的结构化结果读 `套磁候选输入.json` 的 `papers`、`cache.preflight` 与命令 stdout；不另建判定器。

### 4.3 正式结果

- 新模块：`Ran 30 tests`，全部 OK（见 `/tmp/u5-formal2-20261020/suite.log`）。
- 全量回归（同一提交）：shard1 `Ran 380 tests` OK；shard2 `Ran 219 tests` OK；shard3 `Ran 218 tests` OK；shard4 `Ran 243 tests` OK（1 skipped）。合计 1060 tests、1 skipped，无失败。
- 每项结论：L1–L6 均为通过，无业务失败、无无法判断、无未执行。
- 未执行且不在本清单范围：模型分析质量、#92 整套矩阵、Stage 3/4、外部 Zotero/handoff 全链、通用来源认证；按 §1 排除，不补做。
- 未因提交编号变化重跑；上述结果即为固定提交 `87984db` 的当前记录。

### 4.4 未完成项与下一负责人

- 第二关口：真实步骤与选择器已补齐（本节），但独立测试计划审核者尚未复核，作者不能自批。
- 第三关口：上述结果按正式命令取得，仍需按 `Test Engineer Rule.md` 由审核者确认对当前版本有效；实现符合性审核另行安排。
- 产品实现负责人：本轮按执行计划 r3 完成实现；后续只按具体受影响意见处理。
- 范围内未发现需要产品修复的缺陷；若后续审核指出业务不符，按测试规则只复核受影响项。
