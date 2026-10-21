# U5：实际分析级别贯通与诚实统计测试计划

- Test plan revision：`u5-analysis-level-t6`，2026-10-22 全部测试 Recipe 准备。业务目标、预期及范围沿用 t6；§4.3.1、§4.3.3 是当前完整步骤，本轮仅准备。§4.3.2 保留此前误解请求后实际执行的历史，§4.4–5 保留更早记录，不并行执行历史 Recipe。
- 对象：[PR #106](https://github.com/ScholarWorkflow/professor-contact/pull/106)，分支 `plan/u5-analysis-level-redesign`；对齐同目录[执行计划 r6](implementation-plan.md)。本轮产品与已有测试基线为 `4a6cec8a4335eecb720511e683fbdb075d9fcfa8`，仅修改测试资产和本文。r6 正文基线为 `8fa52a4`；历史读取基线为 `d4e096f105805dfefbf2f4d883fc4919d49fce76`。
- 当前模块 88 个方法：沿用 74 个，新增 14 个；A–I 的选择器及复用方式见 §4.3.1，完整材料、保存输入和静态流程的补充步骤见 §4.3.3。用户已澄清只要求全部编写完成，不执行测试；此前误执行的结果保留于 §4.3.2。`76cba4d` 的 18 个方法执行观察及其中 10 个产品失败也仅为历史记录。I 已有执行结果见 §4.7。完整冻结材料及 analyzer 接线仍存在源码已确认的产品缺项，相关 Recipe 已写出缺项的具体判定；本次不修改产品，不授予测试关口或合并批准。
- 历史正式状态：[2026-10-21 10:58:32Z 的 t5 G2/G3 审核](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6314274110) 已明确第二、第三关口通过，适用产品/测试 `96a1b113722aaba3863b75fcf3b84c31a625639d`、文档 `d4e096f`、执行计划 r4；原始结果见 §4.5。这一历史事实保留。早期 `3c4cda1` 阶段及 CI 失败已由后续修复/复验取代，不是当前仍失败清单；t6 依据新发现的独立错误路径重开直接受影响检查，不能把旧绿扩大为新机制通过。
- **Rebase note（2026-10-21）**：分支已 rebase 到 main `1d8f138`（含 U1 r5）。t5 历史产品/文档提交等价为 `33e49dc`（r4）、`4140b77`（t5）＋`10430f5`（U1/U5 接受边界）、`78acaaf`（t5 记录）；t5 定向复验见 §4.6。当前产品已有部分消费准备实现，完整冻结内容及接线缺项以 §4.3.1 的实际源码核对为准，历史 pending 不因 rebase 自动变为完成。

## 1. 范围、依据与复用原则

规范依据为用户本轮仅准备的授权、r6 §1/4–6（含 §4.5 刷新字段写入范围）、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 与 [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)，本轮已读原文。执行计划 r6 已由[正式审核记录](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6317865160)批准；I 的既有执行结果见 §4.7。L1–L6 业务边界保持，历史误执行见 §4.3.2，本轮不再运行正式用例；不重新设计或批准计划。

不要求全 OCR/模型/导入业务回归、Stage3/4、全仓四分片、所有来源×时点×validator 状态、来源认证平台或新测试框架。用既有 unittest、临时 program root、真实 runner 及确定性合法结果夹具；不调用真实模型。准确消费边界只读两个 analyzer/SKILL 的实际完整读计划→自身判断→聚合写结果流程与 runner 封存接线，不新建 harness/模型调用证明系统。模型内部是否认真阅读不在可验证范围。

复用以具体实现接线为前提：记录实际共同函数及 caller 所传完整对象/集合与调用先后；同名、关键词存在或“其余共用谓词”不足。若仍有独立读取或接受分支，最小补该分支的判别输入，由测试工程师在 §4.1 实际接线表填落点；不因此复制整套矩阵。旧有效统计、字节、兼容、lease 与生命周期结果保留，只有直接改动路径需定向复验。

## 2. 最小充分必测清单

| 目标 | 输入与独立预期 | 检查及适用性 |
|---|---|---|
| L1 当前来源资格 | 原 fulltext/abstract/合法 unknown、OCR-only/facts unavailable、失败升级保留 abstract、新成功 unknown→known、known+null/缺字段冲突继续有效；另加坏 index JSON/结构+null/缺字段，不能折叠 unknown | 实际 plan/finalize 的 invalid_facts 与接受产物零写入；保留 TestFactsLevelContract；新增 §4.2 A，两个声明共用读取分支可用 subTest，不重跑 producer |
| L2 canonical 合流与兼容 | fresh/reused/resolved/old 均从本轮冻结值显式写 level（含 null）；旧 raw/兼容视图/候选深隔离，schema2 缺字段不冒充新 facts | 保留 TestCanonicalMerge/v1 结果；普通 process 正例/漂移及 resolved 真实输入见 B–D，同时读回 canonical 与接受基线。若独立合流仍未同源，补该分支一条而非四分支×三级别 |
| L3 成员统计 | 原 supporting 投影三类互斥、总和与成员数一致，reference/relevant-only 排除，共享成员按原方向贡献 | 复用 TestStatisticsRender 两个有效结果；仅 actual renderer/direction_papers 变化才复验 |
| L4 消费边界与完整分流 | freeze 前读源身份、冻结材料→facts/resolve/plan/model_input/结果集合完整关联；F→O 漂移拒绝；B→O 的 E/D/存在、digest/stat、resolved/freshness、已批准业务输入统一 | A–D 及 E/F 的实际 action、原冻结基线提交与零写入；旧 jobs=[] 漂移只覆盖旧来源复用，不能证明 process。保留原 unchanged/level-only/管理字段/显式外部结果优先等有效例 |
| L5 旧态与无损字节 | 首建、合法无 validator、合法 round1 pending/awaiting_second_validation、合法终态、失效旧态分类；header/body/cache/pack、validator schema/round/phase/pending/results/方向范围独立检查；所有判定在写前 | G/H 及原真实 CRLF、时间 token、manual-body 方法。refresh 失效旧态即使新正文不同也零写入；普通真正新业务只能按显式政策成为未校验，不继承旧认证 |
| L6 持锁及正式写前 | refresh 锁后与渲染后的完整复核覆盖 E、D、freshness、missing→exists；接受 pack 外部更新不被旧 candidate 覆盖；只更新 level/display、不替换 B，保留 `cache.render[ANALYSIS_MD]` 的 `u1` 和与新正文绑定的 `ownership`/`body_sha256`，busy/释放/I/O 边界保持 | E/F 采用既有同进程 refresh hooks 与实际处理函数；I 用真实 refresh 断言字段保留；保留外部 pack、lease、失败中断及 refine 生命周期资产，不增加事务/回滚框架 |

## 3. 继承资产及历史结果边界

以下表格记录 `76cba4d` 阶段的资产和观察，表中 pending 指该阶段，不是当前交付清单。当前补齐和产品缺项以 §4.3.1 为准。此前 A–H 共 18 个方法、模块 74 个；本轮新增 14 个、模块 88 个。`test_stage2_preflight.py`、`stage2_upstream_fixture.py` 继续复用。

| 实际资产 | 保留/修订及明确局限 |
|---|---|
| TestFactsLevelContract / TestCanonicalMerge | known/null/路径冲突、合法 unknown、新成功、OCR-only 与 v1/schema2 兼容仍有效；A 的 prepare 两例与 context-null 两例均在 `76cba4d` 预检为红产品缺口；已有 F 的 finalize 仍 pending。B 只证明 path/state，内容字段契约 pending |
| TestConsumptionFreeze | 新资产：路径/状态冻结、缺失/未封存/错轮、fresh 漂移、revision 1、post-freeze 均已落测试；路径/状态、缺失、未封存、错轮通过；fresh/post-freeze/revision 1 为产品缺口红。B 的内容字段契约、早期读/写后反采样、D 的 resolved 仍 pending |
| TestStatisticsRender | 两个统计/成员结果复用，既有 supporting 范围不扩大 |
| TestPreflightBranches.test_normal_finalize_rejects_consumed_artifact_stat_drift | t5 真正 plan 是 reuse_all、jobs=[]、write_needed=false；保留其旧复用路径结果。它不能证明 fresh/resolved process，D 增加非空 jobs 的普通 finalize 输入 |
| TestPreflightBranches 其他分流 / TestAnalyzerContract | unchanged、level-only、管理字段、固定 missing facts 出现、旧投影、illegal index 与 validator 复用仍有效；静态关键词不足以验证 freeze/准确读计划顺序，改读完整实际段落及 runner 注入接线 |
| TestLevelRefresh 的 state/render 反例 | 现有 header 反例改 state_fingerprint，validator 反例改 validator.render_sha256；保留其独立层。它们不能替代仅 header.render 损坏、cache、pack 摘要及合法 hash 下非法生命周期，G 补这些分支 |
| TestManagedBodyBytes / TestLevelRefresh 的 CRLF、顶部时间、统计等价/业务变化 | 保留真实磁盘 read_bytes、标准 SHA 预期与普通/preflight/record-validation 入口；原 t5 CRLF 仅破坏 body 的 recipe 有效。新共同 I/O/旧态检查若触及入口，只重验直接影响方法 |
| r6 刷新字段 | `TestLevelRefresh.test_refresh_preserves_rendered_ownership_and_u1`：合法 level-only refresh 后保留 `cache.render[ANALYSIS_MD].u1`，并保留与新正文绑定的 `ownership`（version/line_count/fragments/body_sha256），不能整项替换为仅 `sha256`。产品 `4d90c89` 已改为保留该字段；I 于 `223f5b4` 通过，见 §4.7 |
| TestRefreshProtection 两个 source drift hooks | 现在都只改一个 analysis 文件 stat；保留其 D 两时点证明，不能代表 E 外围候选、freshness 或 missing→exists。E/F 补独立语义；外部自洽 pack drift 与 foreign_cache 保留断言继续复用 |
| test_stage2_style_validation_handoff…test_business_rerender_and_bounded_correction_lifecycle | 已有真实 ordinary pending finalize、refine round1→2 与 cache 检查；原通过保留，新合法性层若经过该路径才定向复验，不能改成 terminal-only |
| busy/release_failure（成功与软退）/pack_io_failure_after_markdown | 保留原边界：拒绝零业务写入，释放失败如实报告；I/O 中断可有已发生 Markdown，pack 不伪造接受，不承诺跨文件回滚。它们不是本轮新增矩阵 |

上游 handoff/OCR/facts-sidecar 资产只作仍有效的登记/验证规则来源，不重跑完整业务。新 prepare/封存接线及相应 recipe 是产品/测试准备待办；不能用原 fixtures 自动调用 proof rebuild 的便利函数掩盖错轮或漂移。

## 4. 本轮步骤、接线及关口

### 4.1 共用合法 fixture、独立预期与零写入

以 `AnalysisLevelBase(PreflightBase)` 为基础，每例独立 TemporaryDirectory。教授/target/Stage1/papers.json 两方向不变：DIR00001 candidate union 包含 AAAA1111/BBBB2222/CCCC3333，DIR00002 为 BBBB2222；方向 relevant/gap 实际消费为 A/B，C 不在任何方向 relevant/gap 集。A=fulltext、B=abstract，A/B 各有 analysis 与真实 future-work sidecar，A PDF 为现有合成 bytes。沿现有 writer 生成完整合法 freshness 与 narrative 结果：DIR1 两条 gap、DIR2 一条，gap_id 来自 quote_id；freshness status=open、candidate_paper_ids=[]、confidence=high、非空 evidence；narrative 含每方向合法 refs/占位符及三个例子字段，不用缩水 JSON。

先按本轮 prepare→facts→resolve（需要时）→stage2-plan 顺序生成私有 companion 和保存的完整计划，再由测试 fixture 把上述确定性结果写成**该 plan 对应**结果并调用实际 `stage2-consumption-seal-results`。两个 narrative 方向必须聚合在一个 narrative.json 的 directions[]，全部方向齐备后封存一次；不得先封存 DIR1 再追加 DIR2。fixture 只提供确定性模型结果，不代替源读取/比较、不宣称自己调用过真实模型；真实消费边界通过两个正式 analyzer 完整读取确切 plan/model_input 后自身判断/聚合写结果的静态接线核对，不假设独立 RPC/子模型。`build_accepted_state` 由测试工程师适配新源准备顺序，仍经真实 finalize→record-validation 建立 accepted。初建前所有 prereq 成功是前提，坏引用/invalid_result_json 是夹具失败，不能抵作目标拒绝（C 中明确的机械修复例除外）。

**E 外围 fixture 的确定构造（用于 D-resolved/E，其余例保留原基线）**：在接受前，DIR1 target.members 与 snapshot.provisional_member_keys 只留 A/B；snapshot.candidate_keys 仍 A/B/C，C 作为已有扩召候选，不能在注入时才加入全集。facts.DIR1.provisional_member_keys=[A,B]，member_keys 保留候选 A/B/C，relevant_keys=[A,B]；DIR2 仍仅 B。facts.params.gap_scope=relevant，并让 preflight 使用相同参数；C.year=2020、无 family/history_refs，元数据/正式 snapshot/catalog 同步在 prepare 前完成。为 C 创建真实 analysis/合法 future-work（需要 facts 的例沿 make_facts_sidecar/PDF 夹具），但 C 不能被 accepted resolution 加入 supporting。沿原 `_write_target/_write_snapshot` 与合法 proof 准备更新 fixture。真实 plan/accepted 后逐项断言 C∈selected_candidate_union/resolution_evidence_guards，C 不在任一 direction 的 supporting_item_keys、relevant_keys、gap_scope_keys、全部 surfaced gap item_key、逐方向 artifact_guards 或 narrative_later_keys/model_input.later_papers；若任一不成立就是夹具准备失败。C 的年份条件只用于隔离范围，不改变业务时效规则。
accepted 终态经现有 raw validation 报告与 `record_validation()` 建立：文件级 result=ok，files 对本 analysis artifact=analysis/verdict=pass/blocking=0/minor=0/issues=[]，不能手填虚构 PASS。原报告路径 `self.root/validation.json`，pack.validator.validation_sha256 独立等于其 bytes 的 SHA（pack 不存报告路径，不新增报告发现义务）。

零业务写入快照固定为调用前以下路径的原始 bytes 与存在性：`套磁候选输入.json`、`套磁候选分析.md`、`论文分析/_freshness_cache.json`、该 fixture 原 validator 报告；有 resolved sidecar 的例子另保存 `_resolved_directions.json`。不要求遍历目录全树。故意外部改动后以**注入后** bytes 为不得覆盖基线；不要求回滚外部输入。lease 为 `论文分析/.stage2-local-writer.json`，refresh 结束不存在。拒绝例还断言 cache.preflight 的源/消费/guard/freshness/resolved 业务字段不变或仍不存在，不能写新 statistics 成功标记。

独立预期：来源/错轮拒绝沿既有 `needs_refresh/preflight_inputs_changed`、`refresh_requires_process` 或精确既有输入错误；旧态错误沿 validation_render_stale/validation_evidence_not_recorded/manual_markdown_changed 的既有类别。不得只 assert 非 ok/任意 error；每例明确所破坏层，并用标准 hashlib/JSON/原 bytes 检查其他层原本合法。仅 header 等已给精确类别的例子不得由无关 result 错误计通过。Python 摘要序列化沿现有 ensure_ascii=False、sort_keys=True、默认空格，不自改 separators；正文 SHA 使用 read_bytes 原切片，不调用被测归一化函数算预期。

当前实际接线和对应方法如下；源码缺项的具体说明以 §4.3.1 为准，产品补齐后只更新受影响行：

| 需核对的接线 | 当前核对结果及测试落点 |
|---|---|
| prepare 读源→封存 payload→Stage2Context | `cmd_stage2_consumption_prepare` 仅封存 `observed_source_projection`；`Stage2Context.__init__` 仍读当前文件。B 的 F0 guard、读后及写后注入已准备；完整材料核对和读取落点操作按 §4.3.3，材料缺失记产品失败。 |
| resolve-plan 与 stage2-plan→analyzer 完整读取→结果集合封存→finalize | 原 resolve writer/resolve_run_id 被 D-resolved 复用；`_seal_consumption_plan` 仅存摘要，两个 analyzer 未接消费准备和结果封存。C 的摘要关联例和 §4.3.3 实际保存输入篡改、静态流程步骤均已写全，保存内容缺失记产品失败。 |
| preflight、普通 process、refresh 锁后/写前 | 普通 finalize 在写后调用 `stage2_preflight_metadata`；refresh 经 `stage2_refresh_evaluate`。D 使用真实 finalize 工厂注入，E/F 使用原 context 观察点；当前不能声称完整 observe/compare 已共用。 |
| old-state 基础层→finalize/refresh/refine/preflight | 现有 `stage2_validation_legality` 为共同基础层。G/H 已准备独有入口的旧绑定和生命周期状态，原生命周期资产补消费准备与封存前置；实际执行结果见 §4.3.2。 |

### 4.2 已确认的最小判别 Recipe

以下 A–H 是同一 L1–L6 内直接缺口。原拟定方法与本轮实际选择器的对应见 §4.3.1，不强求固定方法数。本节所有 pending 和各小节末的“本轮准备状态”均为 `76cba4d` 时的历史准备记录；当前准备状态和完整步骤统一由 §4.3.1、§4.3.3 取代。

#### A. 坏登记不是 unknown，不能被 null 绕过（L1）

- 在合法源/结果 fixture 上，准备两个最小输入：`_index.json` 原始 bytes 为 `b'{broken'`；合法 JSON 但 `papers={}`。两个已知声明都置 null；先在合法 index 上保存合法 preflight，再破坏 index，直接调用 `stage2-consumption-prepare`。prepare 不读 facts，因此本测试只验坏 index 被 prepare 接受的产品缺口；null 声明的已有 F finalize 路径仍 pending，不能由本测试冒称覆盖。
- 真实入口：`stage2-consumption-prepare` 在初次读坏 index 应按 invalid_facts 或既有来源输入错误拒绝；对已有 F 的 `stage2-plan`/`stage2-finalize --facts … --results … --preflight-file …` 应在源复核拒绝，不接受 null。若 plan/finalize 真正共用同一无条件 index 解析，只保留一个正常接受代表并核对另一路接线；不要把非法 level=partial 当本例。
- 预期：零业务写入，不写新消费/统计基线，坏 index 保留；缺少坏 JSON/结构与 nullable 声明交叉的实际拒绝不能登记覆盖。拟定 `TestFactsLevelContract.test_malformed_index_cannot_be_accepted_as_null`。
- **本轮准备状态**：prepare 坏 index 两例与 `Stage2Context` null 两例均已落地；`76cba4d` 预检中 prepare 与 context 都接受坏 index/null，未按 `invalid_facts` 拒绝，登记为产品缺口红；已有 F 的 finalize 路径仍 pending。

#### B. 真正冻结、成功只提交原消费值（L2/L4）

- 从无 pack/Markdown 的合法 A/B 输入进入 prepare，独立保存内容 SHA/stat 和返回源材料、guard F0，具体步骤见 §4.3.3 B。analyzer fixture 从这份材料组装 facts，真实 resolve/plan 生成非空 narrative/freshness jobs；生成上述完整结果（两方向聚合 narrative）并经 seal-results 按该 plan 绑定。未变对照普通 finalize 必须 ok，读回 cache.preflight 源字段逐项等于 F0，canonical level/统计正确；原始临时材料不被复制为长期平台记录。
- 早期读边界反例：在 prepare 的真实读取 helper 完成读 bytes 后、其结束复核前只追加 A analysis 内容，使用已有同进程 wrapper/addCleanup 结构，在原读取后修改真实磁盘并返回原值。prepare 必须拒绝、不产出可用封存成功；不能把“读取前采样后返回新材料”当冻结。再一例在 prepare 已封存 F0 后、facts/plan 前修改 A，同轮不得重新读取并把 F1 当消费：plan 应拒绝；若先从 F0 组装 plan，则 finalize 必须拒绝且零接受写入。
- 元数据反采样对照：合法未变例在首个正式 managed 写成功后的现有 wrapper 中才追加 A，返回原真实写结果，不 mock 比较/渲染。本次允许沿既有检查窗口完成或如实未完成；**无论成功或中断都不能持久化 F1 为本轮消费**。成功 pack 必须仍存 F0，下一次真实 preflight=process；若未完成，禁止成功标记、保留已发生真实写入，不能要求此 I/O 窗口零写入。此例独立区分写后 stat/source_projection 重采样，不能仅看无漂移成功。
- `TestConsumptionFreeze.test_process_commits_the_frozen_sources` 与同组边界方法覆盖原 guard 和反采样；实际读源注入及非常规读取 API 的包装步骤已经写在 §4.3.3 B，未具备产品材料入口记产品缺项，不再留待实现后设计 Recipe。
- **本轮准备状态**：成功冻结提交已通过；post-freeze plan 一例已落地，`76cba4d` 预检中 plan 返回 `ok`，登记产品缺口红；content 字段契约、早期读边界、写后反采样仍 pending。

#### C. facts/plan/model/result 错轮和丢失（L4）

- 同教授同 preflight 保持全部业务/源内容相同，分别真实建立两个独立事务目录 R1/R2，各有不同 run_id 与实际 plan。用 R1 的已封存结果集合/关联段替换 R2 对应段（不改公开模型结果业务字段）；另将 R2 必需 source 段或 companion 文件删除。针对独立校验分支，再仅改 R2 已封存 plan 的一个 model_input 字段而不改 facts/结果，或替换已绑定结果 bytes。所有完整合法原对照已能通过，没有模型/OCR 调用。
- 真实入口：相应 `stage2-plan`/`stage2-resolve-finalize`/`stage2-finalize`，以其当前阶段所需材料为准；错轮、缺源、job 输入/输出错配均 fail closed，零接受写入。不能补发 preflight、重建 companion/结果绑定求通过；先前相同 preflight_id 不足以通过。拟定 `test_consumption_binding_rejects_missing_or_other_run`。
- 静态核对两个 analyzer 的 Step6.1.5/6.2 从 runner 保存的确切 plan 完整读取相关 model_input，自身判断并写完整聚合结果，再由 runner seal-results 绑定；没有这段接线时标产品缺口，不能只测自填关联 JSON 自洽就宣称实际模型阅读已被机器证明。resolve 现有 run_id/清空 results_dir 资产沿用，不再增加新公开 echo 字段或认证设施。
- 同一两方向 fixture 内加原一次机械修复的最小对照：先仅把合法 narrative 中 DIR1 的一条 gap_notes[].gap_id 改错一个字符，其他 refs/占位符与方向内容全保持合法，seal revision=0 后真实 finalize 应 unknown_reference_id 且零接受写入；保留原 bytes/失败输出，重新读取同一 plan 的准确 ID，在 repair-1 子目录完整复制原集合后只纠正该 ID 及对应 refs/占位符。实际 seal-results 追加 revision=1，真实 finalize 在源未变时正常接受两方向聚合结果；原 revision=0 文件与失败记录仍在，sources/facts/plan 原摘要不变。再尝试 revision=2 应被原一次上限拒绝，不写接受产物；不增加一般结果重试或真实模型调用。拟定此为 `test_consumption_binding_preserves_the_single_reference_repair`，仅验证新封存机制直接影响的既有政策。
- **本轮准备状态**：缺失封存结果、未封存 companion、已封存结果错轮三例通过；第一次 seal 前先把 DIR1 的 gap_id 改错，真实 finalize 返回 `unknown_reference_id` 且零写入；复制到 repair-1 纠正 gap_id 后第二次 seal 仍返回 `results already sealed`，说明没有 revision 1 修复入口，登记产品缺口红。

#### D. 非空 jobs 的普通 process 与 accepted resolved（L2/L4）

- 保留 t5 reuse_all/jobs=[] 漂移例。新增 fresh process：在合法 accepted 后按既有 fixture 改 direction.user_note 并同步正式 target，使 preflight 真正 process；新 prepare/facts/plan 必须 process、narrative jobs 非空、write_needed=true，生成与本轮 plan 精确匹配的合法结果。不要靠缺 narrative/freshness 造成错误。freeze/plan 成功后、finalize 前只追加 B analysis bytes（路径/存在/level 不变）。调用真实普通 finalize，不走 `finalize_with_current_proof` 自动重建辅助；预期 needs_refresh/preflight_inputs_changed、零业务写入，源保留追加内容。
- resolved 独立输入：复用 `test_stage2_resolved_direction.ResolvedPipelineMixin` 的 `make_paper`、`make_direction`、`write_facts`、`run_resolve`、`accept_resolved` 及 `CandidateUnionEvidenceTests` 的合法 facts-valid 输入构造，经过真实 resolve-plan→合法 result→resolve-finalize→用户 accepted 或 keep-provisional，保持原 proof/run_id/逐方向 fingerprint 全合法；沿 §4.1 E 外围构造把 C 固定在 E、D 外，resolution 使用完整 unchanged/keep-provisional 接受结果，不把 C 新增为成员；`make_paper` 为 A/B/C 建 sidecar/PDF/facts，A/B 沿原当前登记绑定 level。当前 `ResolvedPipelineMixin.write_facts()` 内部硬编码 selected_direction 并立即生成 proof，因此测试准备时给该 helper 增加可选 gap_scope 参数（默认仍 selected_direction），本例调用时传 relevant，使首次写 facts 与首次 prepare_stage2_proof 就使用相关参数；C year=2020 在 make_paper 时给定。不得先调用原 helper 再补字段/重建 proof，也不使用会重新生成 proof 的 finalize 便利包装。本轮 stage2 jobs 至少 narrative 非空。封存后仅变 `CCCC3333` 候选 analysis 或 facts 原文件，C 不在 relevant/gap，但在 E；不改 target/facts/结果/resolved sidecar。真实普通 finalize 同样应拒绝且 sidecar/pack/Markdown/cache/report 零改写，不能以 resolved_directions_stale 或 invalid_result_json 的先置坏夹具代替 E 漂移检查。
- 为区分 finalize 入口复核与写前复核，fresh 例可将同一唯一源改动延迟到真实 render 完成后、首写前；用原 renderer wrapper 返回原 body，只做一次磁盘修改。普通 finalize 的初次 F→O 与写前 F→O 必须都实际接线；已有首轮与 resolved 例选前者、fresh 延迟例选后者，不做二者×所有载体。拟定 `test_process_finalize_rejects_frozen_source_drift`，resolved 分支接线/输入不可仅用 reuse 例替代。
- **本轮准备状态**：fresh process 漂移已落在 `TestConsumptionFreeze.test_process_finalize_rejects_frozen_source_drift`；`76cba4d` 预检中产品返回 `ok`，未返回 `needs_refresh`，登记为产品缺口；resolved 分支仍 pending。

#### E. refresh 锁后覆盖候选全集与 freshness（L4/L6）

- E 外围候选：按 §4.1 的完整 E 外围 fixture 在 accepted 前创建 C analysis/sidecar/index，并逐项核对 supporting/relevant/gap/later 与 artifact 集；不能沿原 member_keys=C 的默认夹具只删除 relevant 来声称 C∉D。真实接受/validation 后只变 A 合法 level 令 preflight=refresh_level。沿 `_drift_after_lease` 的 `Stage2PackRefineContext.__init__` 原调用后注入 C 文件追加，不动 index/level/方向/pack。实际 `_refresh_in_process` 必须 needs_refresh，零写入、lease 释放；若只查 D guards 将错误成功，故不能用 A analysis 漂移代替。
- freshness 独立例：相同合法基线与 level-only proof，在锁后原 ctx 加载完 cache 后，只修改 `_freshness_cache.json` 内一个**已接受 gap**的现有 cache row status（如 open→unknown，字段类型及该 row 其他内容不变）；外部修改后再次标准 JSON 计算对应接受 gap view 与 B 不同，pack/source/index/resolved 均未变。refresh 必须 needs_refresh 且保留**注入后** cache bytes，pack/Markdown/report 不变、lease 释放；不能只重用 ctx 里旧 cache。拟定 `test_refresh_rechecks_union_and_freshness_after_lease` 的两个 subTests。
- 预检复用：对这两个注入后的状态再真实 preflight，E 变化 reason 含 artifact_changed、freshness 变化含 freshness_cache_changed，action=process。不把 validator_not_accepted 当业务守卫证明；前置合法 terminal 未变。
- **本轮准备状态**：freshness 子项已落 `TestRefreshProtection.test_refresh_rechecks_freshness_after_lease`，`76cba4d` 预检通过；候选全集与注入后再 preflight 仍 pending。

#### F. refresh 正式写前 missing→exists 及 freshness（L4/L6）

- 固定候选：accepted 基线中 A 固定 `AAAA1111.md.facts.json` 不存在、index.facts_sidecar 与 facts.facts_file 均 null，其余来源合法。改 level 取得 refresh_level proof。复用既有 `_drift_after_observation` post-gate render-precheck wrapper，arm 在零写入快照后；只在固定路径创建结构合法但尚未供本轮消费的 facts sidecar（沿现有 facts-sidecar writer 及 PDF/analysis/future_work_ids 合法内容），不改任何 index 声明和已存在 analysis stat。这里业务变化是 missing→exists，即便 null 声明仍必须退回 process；不能只依靠 D 已存在 artifact guards。
- 第二个独立语义用 E 的 accepted gap freshness 修改，时点改在同一 post-gate wrapper：先真实 gate 通过，再只改磁盘 cache row，返回原 helper 结果。测试工程师分别核对 E 与 F 的 caller 重读完整对象，F 不能共用 E 的一次旧观察。
- 两例真实 refresh 均 needs_refresh，pack/Markdown/report 不变，facts 新文件或 freshness 注入后 bytes 保留，旧 B 源/guard/视图不变、lease 释放。拟定 `test_refresh_rechecks_missing_candidates_and_freshness_before_write`。这两例加现有 D analysis 两时点、外部 accepted pack 漂移，已区分必要路径，不再穷举 PDF×阶段×存在。
- **本轮准备状态**：missing→exists 已落 `TestRefreshProtection.test_refresh_rechecks_missing_facts_before_write`，`76cba4d` 预检返回 `ok`，登记产品缺口红；同一 post-gate wrapper 下的 freshness 第二语义仍 pending。

#### G. 完整旧态检查在任何 managed 写入前（L5/L6）

使用原 marker-only/level-swap 正例先生成合法旧态，每个 subTest 重新建 accepted。仅破坏表中一层；其余 hash/结构先独立确认合法。**refresh 统一选择令实际统计正文变化**（如 A fulltext→abstract），使“先写新正文后才发现旧态坏”的实现可被 bytes 断言发现；另用普通 finalize 的等价复用候选检查独有入口。无需每个破坏×两入口，完整 helper 实际共用后表中分配即可。

| 唯一破坏 | 实际入口 / 独立预期 |
|---|---|
| 仅 header.render_sha256 改为另一 64 位摘要，header.state/body/cache/validator 全保留 | refresh（新正文变化）应 validation_render_stale 或明确 header/body 保护拒绝，所有接受文件逐字节不变；另 ordinary finalize 等价候选同层拒绝，防入口各自少验 |
| 仅 cache.render[ANALYSIS_MD].sha256 错配；同时用标准旧 pack content 摘要重绑 validator.pack_sha256，避免第二层也坏 | refresh 零写入证据错误；body/header/validator.render 仍全相等，不能被正文变化分支清 validator 后继续 |
| 仅 validator.pack_sha256 错配，其余字段和实际 pack/Markdown 全合法 | refresh 入口（与 ordinary finalize 共用校验层）validation_render_stale，零写入；ordinary finalize 等价候选仍 pending。现有 validator.render 错配与 header.state 错配结果继续保留，各自不替代本层 |
| validator.schema=非法版本；round=True；phase=未知枚举；round2+needs_correction；needs_correction 却无未修 pending；pending 中未知方向；results 中未知方向或非法结果值 | 可用小型 subTest 表测 refresh 新正文变化入口，每次只改一项、沿原 validator owner 接受契约构造；pack 排除 validator 的摘要本来不受这些变更影响，故所有绑定 hash 保持合法。按 validation_evidence_not_recorded/validation_render_stale 的对应旧态类别拒绝，零业务写入，不能跳过非法 schema 当无 validator |

保留现有真实 body CRLF 破坏、state/header/validator.render、报告摘要/范围例；表中非法 round/phase/pending/results 是实际独立判断，不扩问题字段穷举。合法 lifecycle 对照见 H，用以排除“遇 validator 一律拒绝”的错误实现。拟定 `test_refresh_rejects_invalid_old_state_before_body_write` 与普通 header-render/pack-binding 的对应方法。
- **本轮准备状态**：cache 与 header.render 两例为产品缺口红；validator.pack_sha 通过；非法 lifecycle 的 5 个子项（schema/round/phase/pending list/results 非法值）通过，`round2+needs_correction`、`needs_correction 无 pending`、`pending 中未知方向`、`results 中未知方向` 仍 pending；ordinary finalize 等价候选也 pending。`manual_markdown_changed` 只应适用于真实手改正文，不适用于 cache-only 损坏。

#### H. 合法无 validator、pending 及新业务覆盖（L5/L6）

- 首建正例由 B 给出。合法无 validator：真实 finalize 后尚未 record-validation 的 pack/header/body/cache 绑定合法，做 marker-only 或合法 level-only refresh；允许按规则成功，但不生成 validator/PASS。不能把坏 schema validator 字段当作无 validator。
- pending 对照：沿既有 raw validation 与 lifecycle fixture 建立 round1/needs_correction、非空 pending 的合法 pack（不直接伪造 PASS），普通 finalize 业务/正文等价应保留原 round/phase/pending/results；真实 refine 按原步骤转 awaiting_second_validation，下一 round2 正常，不被 terminal-only gate 挡住。新 old-state 层经过哪些实际入口就定向复验哪些现有步骤，不复制完整校验矩阵。合法 terminal 的 pass/skipped 可 reuse_all；合法 fail_after_2_rounds 仍 process，不冒称非法状态。
- 真正新业务覆盖对照：在 G 的仅 header.render 损坏旧态上，按既有合法 user_note/target 同步改变建立**新** F、非空 jobs 与合法结果；普通 finalize 不带决策时按原受管保护拒绝零写入，显式 `decision_file={"decision":"overwrite"}` 才按原政策接受新结果，validator 不存在/未校验、旧 report bytes 保留，不继承旧 PASS。refresh 遇相同坏旧态即使带 overwrite 也仍零写入。此例区分显式新业务与刷级修复旧认证，不增加新的自动修复政策。
- 成功 refresh 与旧 foreign_cache/sources 保持例合用：逐项断言 E/D business source/guards、resolved grouping/fingerprints、freshness 基线与 consumed_sources/pdf_sources 等于刷新前 B；只允许 level/statistics/render/合法 validator.pack 绑定必要变化。不能通过重采样后值恰相同来声称刷新建立了新业务基线，源码须核对纯投影。
- **本轮准备状态**：无 validator 的 level-only refresh 已落在 `test_refresh_without_a_validator_stays_unvalidated`，`76cba4d` 预检通过，不生成 validator；pending/terminal 的既有 lifecycle 资产保留，非法 lifecycle 子项仍 pending。

#### I. r6 刷新正文归属与 U1 字段保留（L6）

- 合法 accepted 基线；真实 level-only refresh（A fulltext→abstract、B abstract，正文确实变化）成功后，`cache.render[套磁候选分析.md]` 的 `u1` 必须原样保留，`ownership` 必须是渲染器返回且与最终正文绑定的记录（含 `version/line_count/fragments`，`body_sha256` 等于最终正文 SHA）；不得整项替换为只有 `sha256` 的对象。测试须断言 `md_written` 为真且新 SHA 与旧 SHA 不同，证明走的是新正文分支。
- 真实入口：`TestLevelRefresh.test_refresh_preserves_rendered_ownership_and_u1`；当前产品的 refresh 在 `_stage2_finalize.py` 将 render 记录替换为仅 `sha256`，按已批准的 r6 §4.5 预期红，属产品缺口，不是夹具错误。
- 该例只覆盖 r6 §4.5 的直接字段保留；A–H 及所有新消费/封存/写前机制仍 pending，不因该例通过而扩大。

### 4.3 执行准备、历史复用与责任

第一关口沿用 L1–L6；r6 已有执行计划批准。t5 的第二、第三关口结论只适用于其历史版本；t6 的步骤和执行结果仍待正式审核。用户最新澄清为编写全部 Recipe，不执行测试、不等待产品实现。本轮只补准备资产；§4.3.2 保留此前误解请求后已经发生的执行事实，不作为继续执行的授权。§4.3.3 补齐完整材料、实际保存输入及分析入口读取流程的操作步骤。

#### 4.3.1 2026-10-22 当前测试准备与 Recipe

**版本与资产**：产品及已有测试基线 `4a6cec8a4335eecb720511e683fbdb075d9fcfa8`；本轮交付版本以包含本节的提交为准，产品代码不变。测试文件为 `.apm/skills/professor-contact/tests/test_stage2_analysis_level.py`；另给 `test_stage2_resolved_direction.py` 的 `ResolvedPipelineMixin.write_facts` 增加可选 `gap_scope`，默认值保持原样，并补 `test_stage2_style_validation_handoff.py` 中原生命周期的消费前置。模块现有 88 个方法，下面只选择本轮直接涉及的方法，不运行整个模块或四分片。`AnalysisLevelBase.stage2_finalize/build_accepted_state` 已走真实 prepare→plan→结果→seal→finalize→record-validation，不再事后 seed 接受元数据；每轮使用独立 run 目录，便于同例进行第二轮准备。原合法结果 writer 按实际 plan 的 jobs 选择 narrative 方向和 freshness gap，移除没有任务的已知结果文件；单方向处理不混入复用方向。

| 目标 | 本轮准备及实际入口 |
|---|---|
| A | 保留 4 个 prepare/context 方法；新增 `TestConsumptionBoundaries.test_finalize_rejects_bad_index_with_an_existing_freeze`，使用真实已有冻结，在坏登记下分别检验 null／缺字段的 finalize 拒绝与零写入。 |
| B | 加强 `TestConsumptionFreeze.test_process_commits_the_frozen_sources`，在 prepare 前用标准 SHA 与 stat 固定 F0，并比对已接受 analysis guard；新增 `test_prepare_rejects_drift_after_the_actual_source_read` 与 `test_finalize_does_not_sample_sources_after_the_managed_write`。前者包装真实文件流，覆盖 `open`、`Path.read_text/read_bytes` 的整读、分段及逐行读取，读完原值后改源；后者在真实受管写入成功后改源，成功包只能保留 F0，中断不能产生接受标记。完整材料供给用 §4.3.3 B 人工步骤核对，不规定私有字段名。 |
| C | 保留丢失结果、未封存和错轮；新增丢失 companion、缺源段、已封存任务输入摘要被改三例。一次机械修复补上 revision=1 的真实 finalize 成功、原结果不变、原来源及计划不变、revision=2 拒绝且不写入的断言。§4.3.3 C 另改 runner 实际保存的 `model_input.user_note`，不以摘要篡改替代；同节给出两个分析入口的静态核对步骤。 |
| D | 保留非空任务普通 process 漂移；新增渲染后源变化。新增 `TestResolvedConsumptionBoundary`，用原 facts-sidecar、resolve-plan/finalize/accept 资产形成合法 accepted unchanged 方向，再生成非空叙事任务并封存；只改 E 内、D 外的 C analysis，直接带原 resolved sidecar 调用 finalize，不自动重建证明。 |
| E | 新增 `TestRefreshRemainingBoundaries.test_refresh_rechecks_an_outer_candidate_after_lease`，接受前固定 C 为扩召候选、年份 2020、相关范围外；先检查成员、相关、gap、后续论文和逐方向 guard 均不含 C，候选全集 guard 包含 C，再在锁后改 C；检查刷新拒绝及后续 preflight 的 artifact_changed。时效缓存锁后例沿用并补具体原因与后续分流检查。 |
| F | 既有 missing→exists 注入改用原合法 facts-sidecar writer，包含真实 PDF 摘要和 future-work ID，避免缩水 JSON；新增写前已接受 gap 的 freshness 行变化，并检查注入后的缓存字节保留、原接受文件不变及后续 freshness_cache_changed。 |
| G | 新增普通等价 finalize 的 header.render／validator.pack 独立损坏；补齐 round2+needs_correction、无待修问题、pending 未知方向和 results 未知方向。拒绝原因限定为原证据错误，不能以任意 validation 前缀计通过。原 cache-only、header、validator 与生命周期方法保留。 |
| H | 保留真实无 validator 对照；新增真实新业务在坏 header.render 下的默认保护、显式 overwrite 后未校验，以及 refresh 即使 overwrite 也拒绝。`test_refresh_keeps_the_accepted_sources_and_foreign_cache` 比较完整原 cache.preflight，仅排除批准更新的级别投影和统计版本，保留原 resolved 和外来缓存。合法 pending→修订→第二轮用原生命周期方法，已为其中实际生成 pack、普通 finalize 和缺成员来源构造补消费准备、计划与结果封存，不复制状态矩阵。 |
| I | 方法和产品未变，沿用 §4.7 的字段保留结果；当前不重复运行。 |

**实际接线核对及产品缺项**（只读源码，不是运行结果）：

- `_stage2_preflight.py:cmd_stage2_consumption_prepare` 目前只调用 `_stage2_facts.py:observed_source_projection`，后者只记录路径、存在性和声明状态，没有先读 analysis/facts/future-work 材料及其结束复核；`Stage2Context.__init__` 仍从当前磁盘加载材料，再比较路径投影。早期实际读取测试会明确区分“根本没读取”和“读后漂移被拒绝”。本角色不猜测完整冻结材料的字段名，也不把 guard 摘要检查冒称材料已从 F0 供应。
- `_seal_consumption_plan` 保存任务输入摘要，却没有保存完整任务输入给 analyzer；`cmd_stage2_consumption_seal_results` 当前拒绝再次封存，不支持原政策的一次修复。`stage2_validate_consumption_results` 检查结果文件，不完整核对任务输入摘要。对应 C 资产已准备，产品负责人修复这些入口后由本地执行工程师执行。
- 两个正式 analyzer 的第 6.1.5／6.2／6.3 段仍是原 resolve、plan、写聚合结果、finalize 流程，没有 `stage2-consumption-prepare`、`--run-dir` 保存完整普通计划、从该计划完整读取输入和 `stage2-consumption-seal-results` 接线；主 `SKILL.md` 也没有这条消费准备接线。该静态核对已完成，不能用原 `TestAnalyzerContract` 的关键词断言代替，也不能在测试提示词里补产品职责。下一负责人为产品实现负责人。
- 普通 finalize 仍在 managed 写入后调用 `stage2_preflight_metadata`，其 `_artifact_guards_for_keys` 会读当前 stat；B 写后注入通过既有 `_stage2_finalize_module.build` 注入原 managed writer 包装，不改判定。D 渲染后注入也使用同一原工厂接线，避免只替换已被闭包捕获的外部别名而使注入不生效。
- refresh 的 `cmd_stage2_refresh_level` 首次调用 `stage2_refresh_evaluate`；后续写前读取及 E/D/缓存覆盖仍须由 E/F 的真实例核对。旧态合法性函数为 `_stage2_validation.py:stage2_validation_legality`，finalize、preflight、refine 使用该层；是否在每条路径首次写入前完成、是否遗漏绑定，由 G/H 判断。没有用“同名函数”声称完整共用已成立。

上述产品缺项不由测试准备修复。§4.3.3 已写出完整材料及保存输入的核对和修改步骤；执行者从真实返回文件定位语义对应的 JSON 路径即可操作，不需要等待产品后再编写 Recipe。早期注入未命中时先核对实际读源调用链：确实没有材料读取属产品缺项；使用其他合法读取 API 而观察不到时记无法判断，按该节已有包装步骤操作，不把未命中一种 API 当作没有读取。

**准备阶段有限预检**：准备阶段实际运行 `uv --version`（0.12.22）、标准库导入、三个修改文件的 `ast.parse`、隔离临时目录写入和 `jq` 字段读取。Python 为 3.14.6，标准库 unittest 可用；分析级别模块 88 个方法通过语法解析，每例仍使用独立 `TemporaryDirectory`。该有限预检没有导入产品或测试模块，没有运行 setUp、测试、产品入口、模型或业务请求，后续正式执行见 §4.3.2。初次 `uv run` 因默认缓存目录不可写失败，改为明确的仓库外 `UV_CACHE_DIR` 后环境命令成功；这不是重跑测试。原始记录为准备者独立 `/tmp` 目录内的 `precheck.json`，不入库。未使用共享 fixtures 仓库，不需要更新或安装它。无额外模型、服务、凭据、配置或用户数据输入。

**准备顺序与隔离**：

1. 本地执行工程师先核对实际产品修复版本与本轮测试提交，完成适用的步骤关口；本角色不代替第二或第三关口。
2. 在包含这些测试的工作树根目录运行下方命令。`checkout` 来自当前 Git 工作树；`run_dir` 是独立 `/tmp` 目录，存输出、uv 缓存及所有 TemporaryDirectory。测试只在各自临时 program root 内生成 target、snapshot、facts、PDF、结果、正文及校验报告；不连接用户教授目录、生产库、浏览器或模型。不需要支持路径之外的安装或消费者。
3. Python 标准库已具备，不安装依赖。未变的旧有效结果按 §3、§4.4–5 复用；只有下面的直接受影响方法进入正式执行。
4. 每条命令完成后保存退出码和完整日志，引用同一产品／测试提交；测试框架的失败、错误或前置失败都保留。前置构造失败不能算作产品按预期拒绝。

以下两条命令留给本地执行工程师，另完成 §4.3.3 的人工步骤。本轮不执行；历史原选择器的结果见 §4.3.2：

```bash
checkout=$(git rev-parse --show-toplevel)
run_dir=$(mktemp -d /tmp/u5-t6-XXXXXX)
export UV_CACHE_DIR="$run_dir/uv-cache"
export TMPDIR="$run_dir"
cd "$checkout/.apm/skills/professor-contact/tests"
git rev-parse HEAD > "$run_dir/target-version.txt"
uv run --no-project python --version > "$run_dir/python-version.txt" 2>&1
uv run --no-project python -m unittest \
  test_stage2_analysis_level.TestFactsLevelContract.test_malformed_index_cannot_be_accepted_as_null \
  test_stage2_analysis_level.TestFactsLevelContract.test_empty_papers_index_cannot_be_accepted_as_null \
  test_stage2_analysis_level.TestFactsLevelContract.test_context_rejects_malformed_index_with_null_levels \
  test_stage2_analysis_level.TestFactsLevelContract.test_context_rejects_empty_papers_with_null_levels \
  test_stage2_analysis_level.TestConsumptionFreeze.test_process_commits_the_frozen_sources \
  test_stage2_analysis_level.TestConsumptionFreeze.test_plan_rejects_a_source_change_after_prepare \
  test_stage2_analysis_level.TestConsumptionFreeze.test_finalize_rejects_a_missing_sealed_result \
  test_stage2_analysis_level.TestConsumptionFreeze.test_finalize_rejects_an_unsealed_companion \
  test_stage2_analysis_level.TestConsumptionFreeze.test_finalize_rejects_sealed_results_from_another_run \
  test_stage2_analysis_level.TestConsumptionFreeze.test_seal_results_supports_a_single_repair_revision \
  test_stage2_analysis_level.TestConsumptionFreeze.test_process_finalize_rejects_frozen_source_drift \
  test_stage2_analysis_level.TestConsumptionBoundaries \
  test_stage2_analysis_level.TestResolvedConsumptionBoundary \
  test_stage2_analysis_level.TestRefreshProtection.test_refresh_rechecks_freshness_after_lease \
  test_stage2_analysis_level.TestRefreshProtection.test_refresh_rechecks_missing_facts_before_write \
  test_stage2_analysis_level.TestRefreshProtection.test_refresh_keeps_the_accepted_sources_and_foreign_cache \
  test_stage2_analysis_level.TestLevelRefresh.test_refresh_rejects_an_invalid_old_cache_render_binding \
  test_stage2_analysis_level.TestLevelRefresh.test_refresh_rejects_an_invalid_old_validator_pack_binding \
  test_stage2_analysis_level.TestLevelRefresh.test_refresh_rejects_an_invalid_old_header_render_binding \
  test_stage2_analysis_level.TestLevelRefresh.test_refresh_rejects_an_invalid_old_validator_lifecycle \
  test_stage2_analysis_level.TestLevelRefresh.test_refresh_without_a_validator_stays_unvalidated \
  test_stage2_analysis_level.TestRefreshRemainingBoundaries \
  test_stage2_analysis_level.TestOrdinaryOldStateBoundaries \
  -v > "$run_dir/t6-direct.log" 2>&1
result=$?
printf '%s\n' "$result" > "$run_dir/t6-direct.exit"
uv run --no-project python -m unittest \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle \
  -v > "$run_dir/lifecycle.log" 2>&1
result=$?
printf '%s\n' "$result" > "$run_dir/lifecycle.exit"
```

第一条选择 33 个方法（原 18 个、新增 14 个，以及本轮加强的原业务基线保留方法），预计 20–60 秒；生命周期沿用已有方法并补消费前置，预计 5–15 秒。耗时超过 60 秒时按 `temp-script` 使用执行工具的原生会话等待，保护窗口 300 秒，不启动自制后台管理器。正式执行时两条命令和 §4.3.3 独立分支都要完成，不因产品缺项或前一条失败跳过后续独立用例。失败方法在首个断言处停止，后续尚未到达的检查单独注明；不能把前置失败算作目标通过。材料或保存输入缺失按 §4.3.3 记录产品失败，不能自行补造后继续本分支。

**失败处理与重试**：本组没有外部请求，默认每个方法正式尝试一次，不因断言失败重新采样。产品失败交产品实现负责人；夹具、选择器或步骤错误交本地测试工程师，修正后只复核影响项；命令／运行时／临时目录故障记无法判断。恢复前先确认具体故障已消除，仅追加一次同参数尝试到新日志文件，不覆盖原日志；仍失败停止该项。产品修复后的定向复验不作为同条件重试，记录新版本和影响。没有额外取证脚本或结果判定器。

**准备符合性审核（2026-10-22）**：专用 `implementation_reviewer` 首次覆盖 r6/t6 的 A–I 全部准备资产、已有未修改测试及必要接线、Recipe、隔离和有限预检，再由同一代理定向复核修正。R1 已改用实际 gap 区域定位时效缓存；R2 已在封存前构造合法 unknown/null 或缺字段事实，封存后只损坏登记；R3 已改真实消费准备与接受顺序，补原生命周期前置，并按真实计划筛选聚合结果；R4 已比较完整原业务基线。四项均关闭。提交前另修正缺来源段例：从当前 companion 仅删来源段，保留已封存计划和结果；同一代理已确认该最小修正有效。

此前准备审核结论为**部分完成，仅限测试准备**，当时 B/C 步骤尚未补齐。用户澄清后，本轮以 §4.3.3 补齐材料核对、实际保存输入修改和静态流程步骤，并扩大原早期读取包装的 API 覆盖。最终准备审核记录在 §4.3.3；产品实现问题仍由产品负责人处理，不再要求其实现后由测试准备者续写步骤。I 仍引用历史结果。本审核不代替测试关口或合并批准。

#### 4.3.2 2026-10-22 当前 Recipe 实际执行

**历史请求理解、版本与环境**：此前把“所有 recipe 都做完，不用等实现，测试不能通过也没关系”误解为执行测试，以下保留已经发生的运行及修正。用户随后澄清仅要求编写全部 Recipe，本节不代表当前执行授权。执行时只运行既定测试并修正实际发现的测试问题，没有修改产品、业务目标或预期。首次执行产品／测试提交为 `c095b23d990172f0c240c66c266551b1b21f1aa4`，产品内容仍为 `4a6cec8`。定向复验基于同一提交加本节所在提交中的测试差异；未受影响结果直接复用。运行环境为 macOS、uv 0.12.22、Python 3.14.6、标准库 unittest，沿用已有预检，不安装依赖或调用模型。两条 Recipe 均执行，不重新执行 §4.4–5 的历史命令或四分片；I 按既定方式复用 §4.7。

**实际命令与原始输出**：首次逐字执行 §4.3.1 的命令块，全部 stdout/stderr、退出码、目标提交和 Python 版本保存在 `/tmp/u5-t6-DER2pR`，不提交原始日志。第一条日志 `t6-direct.log`：33 个方法、26.279 秒、退出码 1，16 通过、14 个断言失败、3 个错误；第二条 `lifecycle.log`：1 个方法、0.569 秒、退出码 1，在构造初始接受包时得到 `invalid_facts`，后续生命周期步骤未到达。没有超时、取消或跳过方法。

**测试问题、修正与全部复验**：

1. 三个新方法用 `out["reason_code"]` 访问没有该字段的返回值，先触发 `KeyError`。仅改为 `out.get("reason_code")`，保留原预期元组及完整返回值，防止诊断错误掩盖产品结果。三个方法在 `t6-direct-recheck.log` 定向复验，共 2.906 秒、退出码 1，均实际返回 `ok`，现为 3 个明确的断言失败，未重跑原 30 个未改方法。
2. 生命周期原夹具把 C 列为相关论文，却没有经正式 Stage-1 生成步骤纳入候选全集；消费 companion 与 facts 来源集合因此不一致。第一次调整合成论文标题和摘要未解决，`lifecycle-recheck.log` 为 0.564 秒、退出码 1，仍停在同一前置断言。该调整已撤回。最终复用原 `contact_stage1.build_command`，在消费准备前用正式 `--named-file` 对应输入把 C 加入两个方向的候选集合，原成员集合、相关身份、事实证据和后续断言不变。`lifecycle-recheck2.log` 为 12.198 秒、退出码 0，完整方法通过。
3. 上述复验是测试错误修正后的定向检查；原失败、无效修正和最终差异都保留在同一运行目录（`test-fixes.patch`、`test-fixes-final.patch`）。没有因产品返回值不满意而重复执行或放宽断言。

三个方法的实际定向命令如下；两次生命周期复验均使用 §4.3.1 第二条原选择器，分别输出到上述新文件，未覆盖旧日志。所有复验继续使用同一 `UV_CACHE_DIR` 和 `TMPDIR`，每例自身的临时根目录互相隔离。

```bash
uv run --no-project python -m unittest \
  test_stage2_analysis_level.TestConsumptionBoundaries.test_finalize_rejects_a_changed_sealed_job_input \
  test_stage2_analysis_level.TestResolvedConsumptionBoundary.test_resolved_process_rejects_an_outer_candidate_drift \
  test_stage2_analysis_level.TestOrdinaryOldStateBoundaries.test_new_business_needs_explicit_overwrite_and_loses_old_validation \
  -v
```

**逐项有效结果**：以下方法均在 `test_stage2_analysis_level` 模块；类名和方法名可直接与 §4.3.1 选择器对应。通过结果均来自首次执行，未受三处诊断修正或生命周期夹具修正影响。

| 类 | 通过的方法 |
|---|---|
| `TestConsumptionFreeze` | `test_process_commits_the_frozen_sources` |
| `TestConsumptionFreeze` | `test_finalize_rejects_a_missing_sealed_result` |
| `TestConsumptionFreeze` | `test_finalize_rejects_an_unsealed_companion` |
| `TestConsumptionFreeze` | `test_finalize_rejects_sealed_results_from_another_run` |
| `TestConsumptionBoundaries` | `test_finalize_rejects_a_missing_companion` |
| `TestConsumptionBoundaries` | `test_finalize_rejects_a_missing_source_section` |
| `TestConsumptionBoundaries` | `test_finalize_rejects_bad_index_with_an_existing_freeze` |
| `TestConsumptionBoundaries` | `test_process_rejects_source_drift_after_render` |
| `TestRefreshProtection` | `test_refresh_rechecks_freshness_after_lease` |
| `TestRefreshProtection` | `test_refresh_keeps_the_accepted_sources_and_foreign_cache` |
| `TestLevelRefresh` | `test_refresh_rejects_an_invalid_old_validator_pack_binding` |
| `TestLevelRefresh` | `test_refresh_rejects_an_invalid_old_validator_lifecycle` |
| `TestLevelRefresh` | `test_refresh_without_a_validator_stays_unvalidated` |
| `TestRefreshRemainingBoundaries` | `test_refresh_rejects_the_remaining_illegal_lifecycle_states` |
| `TestOrdinaryOldStateBoundaries` | `test_ordinary_equivalent_finalize_rejects_header_render_damage` |
| `TestOrdinaryOldStateBoundaries` | `test_ordinary_equivalent_finalize_rejects_validator_pack_damage` |

| 类 | 未通过的方法 | 实际观察与结论 |
|---|---|---|
| `TestFactsLevelContract` | `test_malformed_index_cannot_be_accepted_as_null` | prepare 返回 `ok`，应拒绝坏登记；业务失败。 |
| `TestFactsLevelContract` | `test_empty_papers_index_cannot_be_accepted_as_null` | prepare 返回 `ok`，应拒绝空登记；业务失败。 |
| `TestFactsLevelContract` | `test_context_rejects_malformed_index_with_null_levels` | context 未抛出既定拒绝；业务失败。 |
| `TestFactsLevelContract` | `test_context_rejects_empty_papers_with_null_levels` | context 未抛出既定拒绝；业务失败。 |
| `TestConsumptionFreeze` | `test_plan_rejects_a_source_change_after_prepare` | 源变化后 plan 仍返回 `ok`；业务失败。 |
| `TestConsumptionFreeze` | `test_seal_results_supports_a_single_repair_revision` | 修复后再次 seal 返回 `invalid_params/results already sealed`；业务失败。revision 1 接受及 revision 2 拒绝检查未到达。 |
| `TestConsumptionFreeze` | `test_process_finalize_rejects_frozen_source_drift` | 漂移后返回 `error/result_missing`，缺 `freshness-DIR00001.json`，没有先按预期返回 `needs_refresh/preflight_inputs_changed`；业务失败。结果夹具仅供应原已封存计划所需任务，不临时为漂移后的重新计算补结果。 |
| `TestConsumptionBoundaries` | `test_finalize_does_not_sample_sources_after_the_managed_write` | finalize 成功，但接受 guard 记录写后 F1 的摘要、stat 和 50 字节，而非原 F0 的 20 字节；业务失败。 |
| `TestConsumptionBoundaries` | `test_finalize_rejects_a_changed_sealed_job_input` | 定向复验返回 `ok`，未拒绝被改的已封存任务输入摘要；业务失败。 |
| `TestConsumptionBoundaries` | `test_prepare_rejects_drift_after_the_actual_source_read` | `Path.read_bytes` 注入未命中，首个读取断言失败；本项无法判断。与 §4.3.1 已知落点缺项一致，不能只凭此断言排除其他合法读取方式，更不能登记为已验证读后漂移拒绝。 |
| `TestResolvedConsumptionBoundary` | `test_resolved_process_rejects_an_outer_candidate_drift` | 定向复验返回 `ok` 且 `resolved_directions_applied=true`，接受了候选全集中、实际方向输入外的 C 漂移；业务失败。 |
| `TestRefreshProtection` | `test_refresh_rechecks_missing_facts_before_write` | missing→exists 后刷新仍 `ok` 且已写正文；业务失败。 |
| `TestLevelRefresh` | `test_refresh_rejects_an_invalid_old_cache_render_binding` | cache-only 损坏被分类为 `needs_decision/manual_markdown_changed`；业务失败。 |
| `TestLevelRefresh` | `test_refresh_rejects_an_invalid_old_header_render_binding` | 损坏 header.render 后刷新仍 `ok` 且已写正文；业务失败。 |
| `TestRefreshRemainingBoundaries` | `test_refresh_rechecks_an_outer_candidate_after_lease` | 锁后拒绝及零业务写入检查通过，但后续 preflight 的方向原因没有 `artifact_changed`；业务失败。 |
| `TestRefreshRemainingBoundaries` | `test_refresh_rechecks_freshness_before_the_first_write` | 正式写前时效缓存变化后刷新仍 `ok` 且已写正文；业务失败。 |
| `TestOrdinaryOldStateBoundaries` | `test_new_business_needs_explicit_overwrite_and_loses_old_validation` | 定向复验在首个 refresh+overwrite 检查返回 `ok`，应为 `error/validation_render_stale`；业务失败。其后普通新业务的默认保护、显式覆盖与失去旧认证检查未到达。 |

生命周期方法 `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle` 以最终夹具通过，覆盖既有方法内的旧包重建、接受成员移除、两轮修订、外来缓存保留及不变版本复用。

**结果汇总与交接**：当前两条 Recipe 的 34 个方法全部实际尝试；有效结果为 17 个通过、17 个未通过。按业务分类为 16 个业务失败、1 个读取落点未命中的无法判断；框架初次 3 个错误已有定向诊断结果，生命周期初次前置失败已有最终通过结果，均保留原记录。失败方法首个断言之后的检查未执行，不能据方法已尝试声称所有分支已验证。B 的完整冻结内容、实际读取落点和 C 的完整计划输入字段仍缺产品支持；analyzer 接线仍沿用 §4.3.1 静态核对，不冒称动态通过。产品负责人修复业务失败及缺项；测试工程师随后补接既定字段和读取落点，由执行工程师只复验受影响项目。本次用户要求的运行和记录已完成，产品验收仍未通过。

下列 §4.4–5 原文按历史版本保留；其中“当前”“本轮”“待审核／失败”均为当时口吻。t5 最终正式状态以文件顶部所引审核为准，不因本轮测试准备要求重做历史轮次。

#### 4.3.3 全部 Recipe 补齐后的执行交接（仅准备，未执行）

本节补齐原 B/C 留项；A、D–H 直接使用 §4.3.1 的命令和夹具，I 复用 §4.7。以下人工检查仍在 L2/L4 内，不增加模型调用、公开字段或独立判定器。执行时同时记录自动方法结果与本节 B、C、静态流程三个结果；任一分支失败后继续其他独立分支。预计人工操作 15–25 分钟，不是一个长时间阻塞命令。

**共用准备和变量**：先执行 §4.3.1 命令块中到 Python 版本检查为止的环境准备。在同一测试目录打开 `uv run --no-project python -i`，以下 Python 片段逐段粘贴在同一交互会话；它只用于将已有夹具保持在临时目录，操作完成前不要退出。另开一个终端运行本节 shell 命令，路径从 Python 打印值复制，所有输出放同一 `$run_dir`。不要在本次测试准备任务中实际运行这些片段。

```python
from pathlib import Path
import hashlib, json, shlex
from test_stage2_analysis_level import AnalysisLevelBase, TestConsumptionBoundaries

c = AnalysisLevelBase()
c.setUp()
```

`c.root` 为每个分支独占的临时程序根；`c.prof_dir` 是合成教授目录，`c.facts_path` 是既有合法事实，`proof` 和 `transaction` 来自真实 prepare 返回。JSON 路径均用 `jq` 的数组形式（例如 `["jobs",0,"model_input","user_note"]`），不是文件名猜测。私有字段等价命名按下表定位；这一步只是从产品返回信息复制路径，不需要编写新脚本或适配器。

| 变量 | 唯一取值依据 | 缺失的判定 |
|---|---|---|
| `companion_file` | `transaction/stage2-consumption.json`，同时核对 facts 中真实 consumption.file 指向它 | 产品没有提供本轮消费载体 |
| `material_file`、`material_path` | prepare 返回/companion 中 A 的完整材料对象；内嵌时文件为 companion，引用文件时沿其实际路径读取 | 只有路径、存在性、级别或摘要，没有可消费内容，记产品未供应冻结材料 |
| `plan_file`、`plan_path` | plan 返回或 companion 中 runner 保存的完整计划位置；内嵌计划用所属文件和对象路径，独立计划文件的路径为 `[]` | 仅有输入摘要，没有完整 model_input，记产品未保存完整计划 |

**B：完整冻结材料供给与成功对照**

1. 在 prepare 前保存原值 F0。下段只复制 A/B 分析、相关 JSON 材料及登记；不读 PDF 全文、不计算新增 PDF 全文摘要。默认 fixture 的 facts-sidecar 声明为空；若实际存在则一并保存。已批准的 PDF 验证继续由原产品负责。

```python
source_dir = c.prof_dir / "论文分析"
paths = [source_dir / "_index.json"]
for key in ("AAAA1111", "BBBB2222"):
    paths += [source_dir / f"{key}.md", source_dir / f"{key}.md.future_work.json"]
    optional = source_dir / f"{key}.md.facts.json"
    if optional.exists():
        paths.append(optional)
frozen = {}
snapshot_dir = c.root / "f0"
snapshot_dir.mkdir()
for path in paths:
    raw, stat = path.read_bytes(), path.stat()
    frozen[path] = (raw, hashlib.sha256(raw).hexdigest(), stat)
    (snapshot_dir / path.name).write_bytes(raw)
proof, transaction, companion = c.prepare_consumption()
print("transaction=" + shlex.quote(str(transaction)))
print("snapshot_dir=" + shlex.quote(str(snapshot_dir)))
print("facts_file=" + shlex.quote(str(c.facts_path)))
```

2. 在另一终端设置上段打印的三个变量，运行 `jq . "$transaction/stage2-consumption.json"`、`jq . "$facts_file"`。沿真实返回的材料位置设置 `material_file`、`material_path`；执行 `jq --argjson p "$material_path" 'getpath($p)' "$material_file"` 展开完整材料。逐项对照：A/B 的分析文本等于 F0 文件完整 UTF-8 内容；future-work 的全部 items/quote/ID 等于 F0 JSON；登记路径、合法级别、声明为空的事实来源及其不存在状态等于 F0；实际供应内容的摘要等于 F0 的标准 SHA，已有 size/mtime_ns/ctime_ns 等于保存 stat。材料以原字节保存时比较原字节，以解析字段保存时逐项比较对应字段；不能拿路径或摘要充当正文。其他本轮实际使用的 target/Stage1/catalog/年份参数与当前合法 fixture 相等，freshness 读视图和缺失候选状态也须明确保留。文件引用必须仍位于本轮临时目录；不得引用后来可变的原分析文件充当冻结副本。
3. 用上述材料核对 fixture 已有事实中的 analysis_level、analysis_file、sidecar_file、facts_file、引用 ID/quote、候选范围和相关身份；无差异才保留这些确定性事实继续组装，不重新从当前磁盘取得来源相关判断。若任何完整材料未提供，保存本次 prepare 输出及所缺字段的含义，记 B 产品失败，本分支到此停止；不得自己为 companion 补材料。
4. 继续同一 Python 会话：

```python
plan = c.plan_consumption(proof, transaction)
c.assertTrue(plan["jobs"], plan)
c.assertEqual({job["kind"] for job in plan["jobs"]}, {"narrative", "freshness"})
c.write_stage2_results()
c.seal_consumption(transaction)
out = c.finalize_consumption(proof)
c.assertEqual(out["status"], "ok", out)
meta = c._read_meta()
for key in ("AAAA1111", "BBBB2222"):
    path = source_dir / f"{key}.md"
    raw, digest, stat = frozen[path]
    c.assertEqual(meta["resolution_evidence_guards"][key]["analysis"], dict(
        path=str(path), size=stat.st_size, mtime_ns=stat.st_mtime_ns,
        ctime_ns=stat.st_ctime_ns, accepted_digest=digest))
    c.assertEqual(path.read_bytes(), raw)
print(json.dumps(out, ensure_ascii=False))
```

5. 用 `jq` 检查接受包 canonical 的 A=fulltext、B=abstract，正文统计为全文 1、摘要 2、未确认 1；完整材料和模型输入没有被复制到长期包。自动 B 方法还核对每方向投影、写后反采样与下一次 preflight。保存本节人工结果后执行 `c.tearDown(); c.doCleanups()`。
6. 早期读后漂移由现有自动方法覆盖常见真实 I/O。若产品使用其他合法读取 API，在测试临时同进程补丁中沿 prepare 实际调用链包装**现有读取函数**：保存原函数引用；调用原函数并保留返回值；仅第一次 A 完整材料读取返回后用原写入口追加 `b"\n<!-- after actual read -->\n"`；原样返回原函数值；使用 `addCleanup`/上下文退出恢复函数。直接复用原方法的 prepare 参数、业务快照、精确拒绝及零写入断言，不改比较函数或预期。若根本没有读取完整材料，记产品失败；若确有读取但不能建立该时点，记无法判断并记录具体读取语句，不登记通过。该步骤已固定动作，不要求产品采用某个 Python API。

**C：改 runner 实际保存的完整输入，保留原摘要和结果**

1. 新分支重新创建 `c = AnalysisLevelBase(); c.setUp()`，调用 `proof, transaction, companion = TestConsumptionBoundaries.ready_run(c)`。这是另一份合法 prepare→plan→完整结果→seal；不要复用 B 已接受目录。打印 `transaction`，沿上表定位实际完整 `plan_file` 和 `plan_path`。先用 `jq --argjson p "$plan_path" 'getpath($p) | .jobs[] | {job_id,kind,direction_id,result_file,model_input}' "$plan_file"` 确认 runner 保存的 jobs 与本次 `c.consumption_plan["jobs"]` 一致。缺文件或只有摘要直接记 C 产品失败，不能把 stdout 手工另存后冒充 runner 保存文件。
2. 在 shell 中选第一条真实 narrative job 的下标，不增加新的输入字段；确认该 job 的既有 `model_input.user_note` 是字符串。以下命令只改变实际输入字符串，保留所有关联摘要，不重跑 plan 或 seal：

```bash
cp "$plan_file" "$run_dir/saved-plan-before.json"
job_index=$(jq --argjson p "$plan_path" 'getpath($p).jobs | to_entries | map(select(.value.kind == "narrative"))[0].key' "$plan_file")
input_path=$(jq -cn --argjson p "$plan_path" --argjson i "$job_index" '$p + ["jobs",$i,"model_input","user_note"]')
jq -e --argjson p "$input_path" 'getpath($p) | type == "string"' "$plan_file"
jq --argjson p "$input_path" 'setpath($p; getpath($p) + " saved-input-drift")' "$plan_file" > "$run_dir/saved-plan-mutated.json"
```

3. 尚未覆盖实际计划时，在 Python 保存以下原值。若完整计划内嵌在消费载体，则该文件仅允许第 2 步指定的一个输入字段变化。

```python
before = c.business_snapshot()
facts_before = c.facts_path.read_bytes()
results_before = {p: p.read_bytes() for p in (c.root / "results").iterdir()}
companion_file = transaction / "stage2-consumption.json"
companion_before = companion_file.read_bytes()
```

shell 执行 `cat "$run_dir/saved-plan-mutated.json" > "$plan_file"`，再用以下命令确认去掉唯一指定差异后整个 JSON 与原值相等，所有来源、facts/plan/job 摘要、run_id、结果绑定均未改：

```bash
jq -e --argjson p "$input_path" --slurpfile before "$run_dir/saved-plan-before.json" \
  'setpath($p; $before[0] | getpath($p)) == $before[0]' "$plan_file"
```

4. 回 Python 保存注入后的消费载体 bytes，再调用原 finalize 并检查。独立计划情形下消费载体应仍等于第 3 步原值；内嵌时按上段唯一差异核对。下段对两种情形都检查 finalize 不改消费载体。

```python
companion_injected = companion_file.read_bytes()
out = c.finalize_consumption(proof)
print(json.dumps(out, ensure_ascii=False))
c.assertEqual((out["status"], out.get("reason_code")), ("error", "invalid_result_json"), out)
c.assert_business_unchanged(before)
c.assertEqual(c.facts_path.read_bytes(), facts_before)
c.assertEqual({p: p.read_bytes() for p in results_before}, results_before)
c.assertEqual(companion_file.read_bytes(), companion_injected)
```

保存返回值和结果分类后执行 `c.tearDown(); c.doCleanups()`。不能因产品没有校验实际输入而放宽为任意错误，不能改摘要例替代本例。错轮、丢失、实际结果字节变化及一次机械修复由 §4.3.1 现有方法覆盖。

**两个分析入口与主入口的静态流程**

读取 `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md`、`packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md` 的完整第 6.1／6.1.5／6.2／6.3 段及 `.apm/skills/professor-contact/SKILL.md` 的对应路由。每个入口逐条记录实际段落位置：来源准备结束才 prepare；源相关事实从冻结材料形成；resolve 和普通计划使用本 run；分析代理完整读取 runner 保存的确切 model_input（截断则继续读原文件）；由同一分析代理判断；两方向 narrative 完整聚合后 seal；finalize 消费同一集合；unknown_reference_id 仅一次机械修复保留原版本并限制修复范围。检查段落之间的执行顺序和路径传递，不用关键词出现、自填回执或新模型调用代替。缺任何必需步骤记录该入口产品失败；无需运行分析代理。两个入口分别检查，不以其中一个代替另一个。

**本轮准备预检与审核**：修改后的测试源码经 `ast.parse` 通过，仍为 88 个方法；本节 5 个 Python 片段通过语法解析，2 个 shell 片段通过 `bash -n`，没有导入产品或测试、没有运行上述步骤。独立 `/tmp/u5-t6-preparation-JkjN8Y` 中保留 `precheck-final.json`、`recipe-syntax.json`，不入库。uv 默认缓存不可写后改用该目录下缓存完成语法预检；既有运行时与隔离预检继续复用 §4.3.1。最终专用准备审核在提交前记录；审核只评价 A–I 的准备资产，不宣称产品测试通过。

2026-10-22 同一专用 `implementation_reviewer` 对 `75f414e` 加本次两个文件的最终差异完成复核，结论为 **A–I 测试准备完整**。此前全部测试、夹具、生命周期及入口连接的完整审核继续有效；本次核对 B/C 全部补充动作和实际影响。R1–R5 保持关闭；R6 已修正为读后注入保留原 EOF，R7 已区分当前步骤与历史执行和 pending，均关闭。没有尚欠编写的 Recipe；产品材料供给、完整计划保存、分析入口接线及一次修复仍由产品负责人完成，相关缺失已有执行时的具体失败判定。下一测试负责人为本地执行工程师；本结论仅限准备，不是测试关口或合并批准。

### 4.4 r4 执行结果（2026-10-21）

- **产品／测试提交**：`81c38d4fb0293051cc163d58e92672e4a0be4013`。在 `7c42a40` 的 r4 计划与 t4 测试基础上，补上矛盾 null 拒绝、锁内 artifact 守卫与写前复检、旧 header 绑定拒绝、CRLF 原始字节读取／摘要／比较／写入。
- **测试夹具修正**：`TestManagedBodyBytes._write_managed` 原返回整个受管文件字节，`body_sha` 断言无法成立；按 §4.2 的“方法自身错误先停止受影响项、修正并复核”改为返回正文 SHA，未改变任何断言或预期。
- **环境**：macOS、Python 3.14.7、标准库 unittest；工作树在执行前干净。`run_dir=/tmp/u5-r4-eX3zpI`，原始日志为 `module.log`、`preflight.log`、`lifecycle.log`，不提交。
- **命令与结果**（三条命令退出码均为 0）：
  - 在 `.apm/skills/professor-contact/tests` 执行 `python3 -m unittest test_stage2_analysis_level -v`：`Ran 49 tests in 15.922s`，`OK`。
  - 执行 §4.2 的四个 preflight 选择器：`Ran 4 tests in 1.342s`，`OK`。
  - 执行 L6 生命周期选择器：`Ran 1 test in 5.912s`，`OK`。
- **额外全量回归**：在提交前的同一代码内容上运行四分片，shard1 380、shard2 219、shard3 237、shard4 243（1 skipped），合计 1079 tests、无失败；日志 `/tmp/u5-r4-shard1.log` 至 `/tmp/u5-r4-shard4.log`。该全量结果不是 t4 的必跑门槛，推送后 CI 会在提交上复验四片。
- **本轮新增入口不在上述 49 tests 中**：49 tests 之后有四个入口测试：`test_preflight_reuses_a_legal_crlf_managed_file`、`test_validation_recording_accepts_a_legal_crlf_managed_file`、`test_normal_acceptance_rejects_an_invalid_old_header_binding`、`test_normal_acceptance_rejects_an_invalid_old_validator_binding`；49+4=53，t5 再新增两个（L4/L6）为 55。`81c38d4` 只改 managed write/conflict 的原始字节路径，未改 `_stage2_preflight.py` 665–673 与 `_stage2_validation.py` 87–100/289–296 的 `read_text`；推送后的 CI 显示前三个入口分别得到 `process/validator_not_accepted`、`validation_render_stale`、`ok`，validator 入口按实际执行记录。这些是产品缺口，不是测试方法错误；49 tests 的通过不得扩大为全绿。
- **结论**：上述 49 tests 结果只覆盖 `81c38d4` 执行时的测试集；本轮新增的 preflight/validation CRLF、普通 finalize header/validator 以及 t5 L4/L6 用例未包含在该次执行中，CI 已暴露前三个入口仍失败，待产品修复后由执行工程师按 §4.2 正式运行。该结果不是第二／第三关口或合并批准；独立审核者仍需在实际提交上给出关口结论。

### 4.5 t5 执行结果（2026-10-21）

- **产品／测试提交**：`96a1b113722aaba3863b75fcf3b84c31a625639d`（在 t5 测试 `3c4cda1` 之上；修复普通 finalize 的消费后 artifact stat 守卫与旧 header 绑定、preflight／validation 的 CRLF 原始字节读取、refresh 的外部 pack 漂移拒绝）。执行前工作树干净。
- **计划要求的定向选择器**：`test_normal_finalize_rejects_consumed_artifact_stat_drift`、`test_accepted_pack_drift_after_observation_returns_needs_refresh`、`test_crlf_body_without_a_matching_binding_is_not_accepted`；`Ran 3 tests in 1.365s`，`OK`。
- **先前 CI 转红的入口额外复验**（不是新增测试义务）：`test_normal_acceptance_rejects_an_invalid_old_header_binding`、`test_preflight_reuses_a_legal_crlf_managed_file`、`test_validation_recording_accepts_a_legal_crlf_managed_file`、`test_normal_acceptance_rejects_an_invalid_old_validator_binding`；`Ran 4 tests in 1.569s`，`OK`。
- **同提交的宽范围复验**：模块 `test_stage2_analysis_level` 为 `Ran 55 tests in 17.577s`、`OK`；§4.2 四个 preflight 选择器 `Ran 4 tests in 1.429s`、`OK`；L6 生命周期 `Ran 1 test in 5.985s`、`OK`。四分片 shard1 380、shard2 219、shard3 243、shard4 243（1 skipped），合计 1085 tests、无失败。
- **环境与输出**：macOS、Python 3.14.7、标准库 unittest；`run_dir=/tmp/u5-t5-9qmYmP`，日志为 `t5.log`、`entries.log`、`module.log`、`preflight.log`、`lifecycle.log`、`shard1.log` 至 `shard4.log`；原始日志不提交。
- **结论**：t5 定向三条及先前 CI 红入口在当前提交上均通过，未发现新增业务失败。宽范围复验只用于确认同提交回归；不把 55／1085 结果自动当作第二／第三关口或合并批准；关口结论以独立审核记录为准。

### 4.6 rebase 后的 t5 定向复验（2026-10-21）

- **提交**：产品 `4140b77`（t5 守卫/原始字节）＋`10430f5`（U1 ownership 与 U5 refine/legacy 重建边界）；测试 `3120e19`、`1d3e612`、`bf09858`，夹具 `1c0e370`；执行提交 `1c0e370`。仅复验 t5 已实现范围，不覆盖 t6 新机制。
- **命令与结果**：t5 三条定向 `Ran 3 tests in 1.274s`、`OK`；四个入口 `Ran 4 tests in 1.256s`、`OK`；模块 `Ran 55 tests in 14.333s`、`OK`；preflight 四条 `Ran 4 tests in 1.052s`、`OK`；L6 生命周期 `Ran 1 test in 4.728s`、`OK`。四分片 shard1 380、shard2 219、shard3 243、shard4 249（1 skipped），合计 1091 tests、无失败。
- **环境与输出**：macOS、Python 3.14.7、标准库 unittest；`run_dir=/tmp/u5-rebase-final-IklslU`，原始日志不提交。
- **结论**：rebase 未引入 t5 业务回归；该结果不是 t6 新机制通过，也不改写 §4.5 的历史 t5 G2/G3 审核。

### 4.7 r6 刷新字段执行结果（2026-10-21）

- **产品／测试提交**：产品 `4d90c89`（刷新改用 `render_analysis_document`，保留旧 `u1`，新正文写入同次渲染的 `ownership`，旧正文保留旧归属；旧绑定与 manual 编辑在写前分流）＋测试／夹具 `223f5b4`（`test_refresh_keeps_the_accepted_sources_and_foreign_cache` 在加入 cache/resolved 字段后同步合法 validator 包摘要）。执行提交 `223f5b4`，基于 `a828b94`。
- **命令与结果**：`test_refresh_preserves_rendered_ownership_and_u1` 为 `Ran 1 test in 0.359s`、`OK`；模块 `test_stage2_analysis_level` 为 `Ran 56 tests in 13.593s`、`OK`；U1/preflight/生命周期三模块 `Ran 47 tests in 35.365s`、`OK`。四分片 shard1 380、shard2 219、shard3 244、shard4 249（1 skipped），合计 1092 tests、无失败。
- **环境与输出**：macOS、Python 3.14.7、标准库 unittest；`run_dir=/tmp/u5-r6-final-8ki7Wr`，日志为 `target.log`、`module.log`、`adjacent.log`、`shard1.log` 至 `shard4.log`；原始日志不提交。
- **结论**：I（r6 §4.5 刷新字段）已通过，旧 manual/CRLF/validator 保护未回归。A–H 的消费快照与完整观察入口仍未实现，t6 的第二／第三关口结论仍待独立审核；本记录不把 I 的通过扩大为 t6 全部通过或合并批准。

## 5. 历史执行与公开审核记录（不是 r4 的通过结果）

以下原正式记录按固定版本保留，不追改既有执行事实。原始日志为执行者提供的位置，本轮未重新读取或筛选日志，也未重跑。日期按记录原文，2026-10-21 为 UTC+08:00 当地日期。

### 5.1 版本、环境、命令与结果

- 历史产品／测试版本：`0b9a585bc3d43d7d42a7fa341c89cf161fbda7a3`（含 `dd9d1d5` 主线、`87984db` 补充、`62ca3fd`／`0b9a585` 的 IR 修复，父 main `4cfcf49`）。
- L6 定向测试版本：`231ba03bdeeb2da71aa7fa01334f346e1b7f27b4`（`bff99aa` 补缓存断言，`231ba03` 修注释；产品仍为 `0b9a585`）。
- 环境：macOS、Python 3.14.7、标准库 unittest／仓库夹具、每例独立临时 program root。正式新增模块 `test_stage2_analysis_level.py` 34 tests 归 stage2/shard3；既有 refine 方法属 shard4。
- 历史新模块命令：在 tests 目录执行 `python3 -m unittest test_stage2_analysis_level -v`，`Ran 34 tests`、OK。原输出 `/tmp/u5-formal4-20261020/module.log`。
- 历史四分片结果：shard1 380、shard2 219、shard3 222、shard4 243，共 1064 tests、1 skipped、无失败；原输出 `/tmp/u5-formal4-20261020/suite.log`。分片 totals 是规划估值，不是实测数量。本计划不恢复四分片命令为当前必跑义务。
- 历史 L6 定向命令：在 tests 目录执行 `python3 -m unittest test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle -v`，输出 `/tmp/u5-l6-cache-555AG2/refine.log`；local-execution-engineer 记录退出码 0，`Ran 1 test in 7.785s`、OK。临时目录当时通过 `mktemp -d /tmp/u5-l6-cache-XXXXXX` 建立，未提交原始产物。
- t3 对上述旧版本登记“L1–L6 全部检查通过；无业务失败，L6 无未执行项”。这是真实旧记录的结论，不是当前 r4 结论。方法原映射可在[固定 t3](https://github.com/ScholarWorkflow/professor-contact/blob/3bfe8df6313b2047dad564163e07b30b36c7fd20/plan/stage2-analysis-level/test-plan.md) §4.2 查阅；本正文 §3 已给当前适用性，执行者无需从旧正文拼接新要求。

### 5.2 审核事实及取代关系

- [r3 执行计划审核](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6293315482) 存在，不改写成 r4 通过。
- [t3 第二／第三关口审核](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6297322139) 于 2026-10-20 17:45:18 UTC 发布，对当时 L1–L6 和正式记录给出通过；明确不是合并批准。本轮保留该事实，因具体预期／覆盖条件变化按 §3–4 重审受影响部分，不重复全部历史审核。
- 首次实现符合性审核（所审 `8568a3b`、产品 `dd9d1d5`）的 IR-1 来源保留、IR-2 消费声明核对、IR-3 release 错误、IR-4 比较 helper 行尾、IR-5 analyzer hard rule，曾分别在 `62ca3fd`／`0b9a585` 修复，定向复核 `ce9e370` 将 IR-1…IR-5 按当时对象关闭。该历史关闭不证明后来定位的锁内 stat、null 分叉、旧 header 绑定或磁盘 newline 缺陷不存在。
- 测试准备审核 `bff99aa`／`231ba03` 对缓存断言及注释 R1 给出“完整（仅限测试准备阶段）”；保留该结论及随后 t3 的公开关口审核，不将它提升为 r4 当前批准。
- t4 取代 t3 的“缺失／null 总可接受”、helper 字符串等于真实磁盘覆盖、单个 validator hash 等于完整旧绑定、target 漂移等于锁内全来源保护等不充分口径；保留已确认统计、隔离、原生命周期与历史产物。没有新增模型 eval、框架、外部来源认证或全回归。


