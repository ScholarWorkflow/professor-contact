# U5：实际分析级别贯通与诚实统计测试计划

- Test plan revision：`u5-analysis-level-t6`，2026-10-21。本正文 §1–4.3 整体取代 t5 的当前指令；§4.4–5（含 §4.6）保留历史原文，不并行执行历史 recipe。
- 对象：[PR #106](https://github.com/ScholarWorkflow/professor-contact/pull/106)，分支 `plan/u5-analysis-level-redesign`；对齐同目录[执行计划 r6](implementation-plan.md)（本地当前测试提交 `6022e98`，r6 字段测试新增于 `db63276`；远端 `8ec2aa4`；r6 正文基线 `8fa52a4`）。读取基线 head `d4e096f105805dfefbf2f4d883fc4919d49fce76`，r4 blob `38c71e8d4ec3105b639738086daccfdd360d9d6c`、t5 blob `6243873fb70d3c64e9db4773f04128f6878020be`。
- 本轮以计划为主。新消费快照、完整比较及写前旧态机制和 A–H recipe **尚未实现、未执行，pending**；本地测试工程师先补 r6 §4.5 直接影响的 `test_refresh_preserves_rendered_ownership_and_u1`，当前模块 56 methods，未运行；其余拟定选择器仍是交接目标，不冒称已存在可运行代码。作者不自授 APPROVED/PASS。
- 历史正式状态：[2026-10-21 10:58:32Z 的 t5 G2/G3 审核](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6314274110) 已明确第二、第三关口通过，适用产品/测试 `96a1b113722aaba3863b75fcf3b84c31a625639d`、文档 `d4e096f`、执行计划 r4；原始结果见 §4.5。这一历史事实保留。早期 `3c4cda1` 阶段及 CI 失败已由后续修复/复验取代，不是当前仍失败清单；t6 依据新发现的独立错误路径重开直接受影响检查，不能把旧绿扩大为新机制通过。
- **Rebase note（2026-10-21）**：分支已 rebase 到 main `1d8f138`（含 U1 r5）。t5 历史产品/文档提交等价为 `33e49dc`（r4）、`4140b77`（t5）＋`10430f5`（U1/U5 接受边界）、`78acaaf`（t5 记录）；t5 定向复验见 §4.6。t6 的新消费快照、完整比较及写前旧态机制仍未实现，本文的 pending 状态不因 rebase 改变。

## 1. 范围、依据与复用原则

规范依据为用户本轮授权、r6 §1/4–6（含 §4.5 刷新字段写入范围）、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 与 [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)，本轮已读原文。执行计划 r6 已由[2026-10-21 正式审核记录](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6317865160)批准，所审计划内容与当前版本一致；I 项测试已准备、未执行，测试关口状态见 §4.3。采用可用个人执行/测试计划审核技能，不从当前有缺陷实现反推验收预期。L1–L6 业务边界保持；新增具体检查只针对本轮授权的消费边界、完整来源、写前合法性及刷新字段写入范围缺口。

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

## 3. 当前资产及有效结果边界

已在 `d4e096f` 读取 `.apm/skills/professor-contact/tests/test_stage2_analysis_level.py`（t5 55 methods）；本次在 `db63276`（`8ec2aa4` 之上）增补 r6 字段测试，并在 `6022e98` 补正文变化断言，当前为 56 methods。`test_stage2_preflight.py`、`stage2_upstream_fixture.py` 和相应产品源码继续沿用；现有资产不因更换文档 SHA 自动失效。

| 实际资产 | 保留/修订及明确局限 |
|---|---|
| TestFactsLevelContract / TestCanonicalMerge | known/null/路径冲突、合法 unknown、新成功、OCR-only 与 v1/schema2 兼容仍有效；`test_illegal_index_level...` 是合法 JSON 中 level=partial，不能替代 malformed JSON+null。按 A 补读源失败分支，按 B 使用新冻结入口，不手造快照 |
| TestStatisticsRender | 两个统计/成员结果复用，既有 supporting 范围不扩大 |
| TestPreflightBranches.test_normal_finalize_rejects_consumed_artifact_stat_drift | t5 真正 plan 是 reuse_all、jobs=[]、write_needed=false；保留其旧复用路径结果。它不能证明 fresh/resolved process，D 增加非空 jobs 的普通 finalize 输入 |
| TestPreflightBranches 其他分流 / TestAnalyzerContract | unchanged、level-only、管理字段、固定 missing facts 出现、旧投影、illegal index 与 validator 复用仍有效；静态关键词不足以验证 freeze/准确读计划顺序，改读完整实际段落及 runner 注入接线 |
| TestLevelRefresh 的 state/render 反例 | 现有 header 反例改 state_fingerprint，validator 反例改 validator.render_sha256；保留其独立层。它们不能替代仅 header.render 损坏、cache、pack 摘要及合法 hash 下非法生命周期，G 补这些分支 |
| TestManagedBodyBytes / TestLevelRefresh 的 CRLF、顶部时间、统计等价/业务变化 | 保留真实磁盘 read_bytes、标准 SHA 预期与普通/preflight/record-validation 入口；原 t5 CRLF 仅破坏 body 的 recipe 有效。新共同 I/O/旧态检查若触及入口，只重验直接影响方法 |
| r6 刷新字段 | `TestLevelRefresh.test_refresh_preserves_rendered_ownership_and_u1`：合法 level-only refresh 后保留 `cache.render[ANALYSIS_MD].u1`，并保留与新正文绑定的 `ownership`（version/line_count/fragments/body_sha256），不能整项替换为仅 `sha256`。当前产品会丢字段，预期红，属产品缺口 |
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

测试工程师在产品实现后填写最小实际接线表，提交精确函数/caller 及测试 selector：

| 需核对的接线 | 允许复用的条件 / 尚待准备 |
|---|---|
| prepare 读源→封存 payload→Stage2Context | 对 analysis/facts/future-work 解析使用同一已读 bytes、PDF 只用现有验证读摘要；缺失探测与 E key 覆盖未被跳过。B 的业务结果覆盖首次冻结与写后采样，源码补核对实际读取 owner；当前 pending |
| resolve-plan 与 stage2-plan→analyzer 完整读取→结果集合封存→finalize | resolve 继续使用 `_build_resolve_model_input`/resolve_run_id；ordinary job 使用该 plan model_input，analyzer 自身读取相关完整 model_input 后判断，不再重构输入/新增 pass；共享 narrative 在全部方向齐备后封存，结果段核对完整 job/文件/方向集与摘要。B/C/D 的入口分别支持复用；当前 pending |
| preflight、普通 process、refresh 锁后/写前 | 实际调用同一 observe/compare，传 E/D/存在/源/guard/resolved/freshness/资格完整对象；普通比较 F→O、refresh B→O，元数据纯投影。D/E/F 业务结果加接线记录，不凭“其余共用”覆盖；当前 pending |
| old-state 基础层→finalize/refresh/refine/preflight | 全部绑定和原 validator schema/lifecycle 检查早于首个 managed write；terminal 接受层只用于 reuse_all。G/H 支撑各层/独有入口；当前 pending |

### 4.2 由最终机制推导的最小判别 recipe（A–H 准备及执行均 pending；I 已准备、未运行）

以下 A–H 是同一 L1–L6 内直接缺口。方法名为拟定落点，可等价合并现有方法但须保持每条独立错误路径的判别；不强求固定方法数。

#### A. 坏登记不是 unknown，不能被 null 绕过（L1）

- 在合法源/结果 fixture 上，准备两个最小输入：`_index.json` 原始 bytes 为 `b'{broken'`；合法 JSON 但 `papers=[]`。每种仅令 A facts.analysis_level=null（第二种可用缺字段走同一 declared=None 分支）；分析及 sidecar 均存在且内容合法。先准备合法事务，再破坏 index；同时另走坏 index 直接 prepare/plan，不能只测已封存后的漂移。
- 真实入口：`stage2-consumption-prepare` 在初次读坏 index 应按 invalid_facts 或既有来源输入错误拒绝；对已有 F 的 `stage2-plan`/`stage2-finalize --facts … --results … --preflight-file …` 应在源复核拒绝，不接受 null。若 plan/finalize 真正共用同一无条件 index 解析，只保留一个正常接受代表并核对另一路接线；不要把非法 level=partial 当本例。
- 预期：零业务写入，不写新消费/统计基线，坏 index 保留；缺少坏 JSON/结构与 nullable 声明交叉的实际拒绝不能登记覆盖。拟定 `TestFactsLevelContract.test_malformed_index_cannot_be_accepted_as_null`。

#### B. 真正冻结、成功只提交原消费值（L2/L4）

- 从无 pack/Markdown 的合法 A/B 输入进入 prepare，记下返回源材料和 guard F0（标准 SHA/stat 独立留值）。analyzer fixture 从这份材料组装 facts，真实 resolve/plan 生成非空 narrative/freshness jobs；生成上述完整结果（两方向聚合 narrative）并经 seal-results 按该 plan 绑定。未变对照普通 finalize 必须 ok，读回 cache.preflight 源字段逐项等于 F0，canonical level/统计正确；原始临时材料不被复制为长期平台记录。
- 早期读边界反例：在 prepare 的真实读取 helper 完成读 bytes 后、其结束复核前只追加 A analysis 内容，使用已有同进程 wrapper/addCleanup 结构，在原读取后修改真实磁盘并返回原值。prepare 必须拒绝、不产出可用封存成功；不能把“读取前采样后返回新材料”当冻结。再一例在 prepare 已封存 F0 后、facts/plan 前修改 A，同轮不得重新读取并把 F1 当消费：plan 应拒绝；若先从 F0 组装 plan，则 finalize 必须拒绝且零接受写入。
- 元数据反采样对照：合法未变例在首个正式 managed 写成功后的现有 wrapper 中才追加 A，返回原真实写结果，不 mock 比较/渲染。本次允许沿既有检查窗口完成或如实未完成；**无论成功或中断都不能持久化 F1 为本轮消费**。成功 pack 必须仍存 F0，下一次真实 preflight=process；若未完成，禁止成功标记、保留已发生真实写入，不能要求此 I/O 窗口零写入。此例独立区分写后 stat/source_projection 重采样，不能仅看无漂移成功。
- 拟定 `TestPreflightBranches.test_process_commits_the_frozen_sources` 与同组边界 subTests；hook 精确落点由测试工程师在实现后记录，未具备入口时是准备 pending，不能伪称执行。

#### C. facts/plan/model/result 错轮和丢失（L4）

- 同教授同 preflight 保持全部业务/源内容相同，分别真实建立两个独立事务目录 R1/R2，各有不同 run_id 与实际 plan。用 R1 的已封存结果集合/关联段替换 R2 对应段（不改公开模型结果业务字段）；另将 R2 必需 source 段或 companion 文件删除。针对独立校验分支，再仅改 R2 已封存 plan 的一个 model_input 字段而不改 facts/结果，或替换已绑定结果 bytes。所有完整合法原对照已能通过，没有模型/OCR 调用。
- 真实入口：相应 `stage2-plan`/`stage2-resolve-finalize`/`stage2-finalize`，以其当前阶段所需材料为准；错轮、缺源、job 输入/输出错配均 fail closed，零接受写入。不能补发 preflight、重建 companion/结果绑定求通过；先前相同 preflight_id 不足以通过。拟定 `test_consumption_binding_rejects_missing_or_other_run`。
- 静态核对两个 analyzer 的 Step6.1.5/6.2 从 runner 保存的确切 plan 完整读取相关 model_input，自身判断并写完整聚合结果，再由 runner seal-results 绑定；没有这段接线时标产品缺口，不能只测自填关联 JSON 自洽就宣称实际模型阅读已被机器证明。resolve 现有 run_id/清空 results_dir 资产沿用，不再增加新公开 echo 字段或认证设施。
- 同一两方向 fixture 内加原一次机械修复的最小对照：先仅把合法 narrative 中 DIR1 的一条 gap_notes[].gap_id 改错一个字符，其他 refs/占位符与方向内容全保持合法，seal revision=0 后真实 finalize 应 unknown_reference_id 且零接受写入；保留原 bytes/失败输出，重新读取同一 plan 的准确 ID，在 repair-1 子目录完整复制原集合后只纠正该 ID 及对应 refs/占位符。实际 seal-results 追加 revision=1，真实 finalize 在源未变时正常接受两方向聚合结果；原 revision=0 文件与失败记录仍在，sources/facts/plan 原摘要不变。再尝试 revision=2 应被原一次上限拒绝，不写接受产物；不增加一般结果重试或真实模型调用。拟定此为 `test_consumption_binding_preserves_the_single_reference_repair`，仅验证新封存机制直接影响的既有政策。

#### D. 非空 jobs 的普通 process 与 accepted resolved（L2/L4）

- 保留 t5 reuse_all/jobs=[] 漂移例。新增 fresh process：在合法 accepted 后按既有 fixture 改 direction.user_note 并同步正式 target，使 preflight 真正 process；新 prepare/facts/plan 必须 process、narrative jobs 非空、write_needed=true，生成与本轮 plan 精确匹配的合法结果。不要靠缺 narrative/freshness 造成错误。freeze/plan 成功后、finalize 前只追加 B analysis bytes（路径/存在/level 不变）。调用真实普通 finalize，不走 `finalize_with_current_proof` 自动重建辅助；预期 needs_refresh/preflight_inputs_changed、零业务写入，源保留追加内容。
- resolved 独立输入：复用 `test_stage2_resolved_direction.ResolvedPipelineMixin` 的 `make_paper`、`make_direction`、`write_facts`、`run_resolve`、`accept_resolved` 及 `CandidateUnionEvidenceTests` 的合法 facts-valid 输入构造，经过真实 resolve-plan→合法 result→resolve-finalize→用户 accepted 或 keep-provisional，保持原 proof/run_id/逐方向 fingerprint 全合法；沿 §4.1 E 外围构造把 C 固定在 E、D 外，resolution 使用完整 unchanged/keep-provisional 接受结果，不把 C 新增为成员；`make_paper` 为 A/B/C 建 sidecar/PDF/facts，A/B 沿原当前登记绑定 level。当前 `ResolvedPipelineMixin.write_facts()` 内部硬编码 selected_direction 并立即生成 proof，因此测试准备时给该 helper 增加可选 gap_scope 参数（默认仍 selected_direction），本例调用时传 relevant，使首次写 facts 与首次 prepare_stage2_proof 就使用相关参数；C year=2020 在 make_paper 时给定。不得先调用原 helper 再补字段/重建 proof，也不使用会重新生成 proof 的 finalize 便利包装。本轮 stage2 jobs 至少 narrative 非空。封存后仅变 `CCCC3333` 候选 analysis 或 facts 原文件，C 不在 relevant/gap，但在 E；不改 target/facts/结果/resolved sidecar。真实普通 finalize 同样应拒绝且 sidecar/pack/Markdown/cache/report 零改写，不能以 resolved_directions_stale 或 invalid_result_json 的先置坏夹具代替 E 漂移检查。
- 为区分 finalize 入口复核与写前复核，fresh 例可将同一唯一源改动延迟到真实 render 完成后、首写前；用原 renderer wrapper 返回原 body，只做一次磁盘修改。普通 finalize 的初次 F→O 与写前 F→O 必须都实际接线；已有首轮与 resolved 例选前者、fresh 延迟例选后者，不做二者×所有载体。拟定 `test_process_finalize_rejects_frozen_source_drift`，resolved 分支接线/输入不可仅用 reuse 例替代。

#### E. refresh 锁后覆盖候选全集与 freshness（L4/L6）

- E 外围候选：按 §4.1 的完整 E 外围 fixture 在 accepted 前创建 C analysis/sidecar/index，并逐项核对 supporting/relevant/gap/later 与 artifact 集；不能沿原 member_keys=C 的默认夹具只删除 relevant 来声称 C∉D。真实接受/validation 后只变 A 合法 level 令 preflight=refresh_level。沿 `_drift_after_lease` 的 `Stage2PackRefineContext.__init__` 原调用后注入 C 文件追加，不动 index/level/方向/pack。实际 `_refresh_in_process` 必须 needs_refresh，零写入、lease 释放；若只查 D guards 将错误成功，故不能用 A analysis 漂移代替。
- freshness 独立例：相同合法基线与 level-only proof，在锁后原 ctx 加载完 cache 后，只修改 `_freshness_cache.json` 内一个**已接受 gap**的现有 cache row status（如 open→unknown，字段类型及该 row 其他内容不变）；外部修改后再次标准 JSON 计算对应接受 gap view 与 B 不同，pack/source/index/resolved 均未变。refresh 必须 needs_refresh 且保留**注入后** cache bytes，pack/Markdown/report 不变、lease 释放；不能只重用 ctx 里旧 cache。拟定 `test_refresh_rechecks_union_and_freshness_after_lease` 的两个 subTests。
- 预检复用：对这两个注入后的状态再真实 preflight，E 变化 reason 含 artifact_changed、freshness 变化含 freshness_cache_changed，action=process。不把 validator_not_accepted 当业务守卫证明；前置合法 terminal 未变。

#### F. refresh 正式写前 missing→exists 及 freshness（L4/L6）

- 固定候选：accepted 基线中 A 固定 `AAAA1111.md.facts.json` 不存在、index.facts_sidecar 与 facts.facts_file 均 null，其余来源合法。改 level 取得 refresh_level proof。复用既有 `_drift_after_observation` post-gate render-precheck wrapper，arm 在零写入快照后；只在固定路径创建结构合法但尚未供本轮消费的 facts sidecar（沿现有 facts-sidecar writer 及 PDF/analysis/future_work_ids 合法内容），不改任何 index 声明和已存在 analysis stat。这里业务变化是 missing→exists，即便 null 声明仍必须退回 process；不能只依靠 D 已存在 artifact guards。
- 第二个独立语义用 E 的 accepted gap freshness 修改，时点改在同一 post-gate wrapper：先真实 gate 通过，再只改磁盘 cache row，返回原 helper 结果。测试工程师分别核对 E 与 F 的 caller 重读完整对象，F 不能共用 E 的一次旧观察。
- 两例真实 refresh 均 needs_refresh，pack/Markdown/report 不变，facts 新文件或 freshness 注入后 bytes 保留，旧 B 源/guard/视图不变、lease 释放。拟定 `test_refresh_rechecks_missing_candidates_and_freshness_before_write`。这两例加现有 D analysis 两时点、外部 accepted pack 漂移，已区分必要路径，不再穷举 PDF×阶段×存在。

#### G. 完整旧态检查在任何 managed 写入前（L5/L6）

使用原 marker-only/level-swap 正例先生成合法旧态，每个 subTest 重新建 accepted。仅破坏表中一层；其余 hash/结构先独立确认合法。**refresh 统一选择令实际统计正文变化**（如 A fulltext→abstract），使“先写新正文后才发现旧态坏”的实现可被 bytes 断言发现；另用普通 finalize 的等价复用候选检查独有入口。无需每个破坏×两入口，完整 helper 实际共用后表中分配即可。

| 唯一破坏 | 实际入口 / 独立预期 |
|---|---|
| 仅 header.render_sha256 改为另一 64 位摘要，header.state/body/cache/validator 全保留 | refresh（新正文变化）应 validation_render_stale 或明确 header/body 保护拒绝，所有接受文件逐字节不变；另 ordinary finalize 等价候选同层拒绝，防入口各自少验 |
| 仅 cache.render[ANALYSIS_MD].sha256 错配；同时用标准旧 pack content 摘要重绑 validator.pack_sha256，避免第二层也坏 | refresh 零写入证据错误；body/header/validator.render 仍全相等，不能被正文变化分支清 validator 后继续 |
| 仅 validator.pack_sha256 错配，其余字段和实际 pack/Markdown 全合法 | ordinary finalize 等价候选 validation_render_stale，零写入；现有 validator.render 错配与 header.state 错配结果继续保留，各自不替代本层 |
| validator.schema=非法版本；round=True；phase=未知枚举；round2+needs_correction；needs_correction 却无未修 pending；pending 中未知方向；results 中未知方向或非法结果值 | 可用小型 subTest 表测 refresh 新正文变化入口，每次只改一项、沿原 validator owner 接受契约构造；pack 排除 validator 的摘要本来不受这些变更影响，故所有绑定 hash 保持合法。按 validation_evidence_not_recorded/validation_render_stale 的对应旧态类别拒绝，零业务写入，不能跳过非法 schema 当无 validator |

保留现有真实 body CRLF 破坏、state/header/validator.render、报告摘要/范围例；表中非法 round/phase/pending/results 是实际独立判断，不扩问题字段穷举。合法 lifecycle 对照见 H，用以排除“遇 validator 一律拒绝”的错误实现。拟定 `test_refresh_rejects_invalid_old_state_before_body_write` 与普通 header-render/pack-binding 的对应方法。

#### H. 合法无 validator、pending 及新业务覆盖（L5/L6）

- 首建正例由 B 给出。合法无 validator：真实 finalize 后尚未 record-validation 的 pack/header/body/cache 绑定合法，做 marker-only 或合法 level-only refresh；允许按规则成功，但不生成 validator/PASS。不能把坏 schema validator 字段当作无 validator。
- pending 对照：沿既有 raw validation 与 lifecycle fixture 建立 round1/needs_correction、非空 pending 的合法 pack（不直接伪造 PASS），普通 finalize 业务/正文等价应保留原 round/phase/pending/results；真实 refine 按原步骤转 awaiting_second_validation，下一 round2 正常，不被 terminal-only gate 挡住。新 old-state 层经过哪些实际入口就定向复验哪些现有步骤，不复制完整校验矩阵。合法 terminal 的 pass/skipped 可 reuse_all；合法 fail_after_2_rounds 仍 process，不冒称非法状态。
- 真正新业务覆盖对照：在 G 的仅 header.render 损坏旧态上，按既有合法 user_note/target 同步改变建立**新** F、非空 jobs 与合法结果；普通 finalize 不带决策时按原受管保护拒绝零写入，显式 `decision_file={"decision":"overwrite"}` 才按原政策接受新结果，validator 不存在/未校验、旧 report bytes 保留，不继承旧 PASS。refresh 遇相同坏旧态即使带 overwrite 也仍零写入。此例区分显式新业务与刷级修复旧认证，不增加新的自动修复政策。
- 成功 refresh 与旧 foreign_cache/sources 保持例合用：逐项断言 E/D business source/guards、resolved grouping/fingerprints、freshness 基线与 consumed_sources/pdf_sources 等于刷新前 B；只允许 level/statistics/render/合法 validator.pack 绑定必要变化。不能通过重采样后值恰相同来声称刷新建立了新业务基线，源码须核对纯投影。

#### I. r6 刷新正文归属与 U1 字段保留（L6）

- 合法 accepted 基线；真实 level-only refresh（A fulltext→abstract、B abstract，正文确实变化）成功后，`cache.render[套磁候选分析.md]` 的 `u1` 必须原样保留，`ownership` 必须是渲染器返回且与最终正文绑定的记录（含 `version/line_count/fragments`，`body_sha256` 等于最终正文 SHA）；不得整项替换为只有 `sha256` 的对象。测试须断言 `md_written` 为真且新 SHA 与旧 SHA 不同，证明走的是新正文分支。
- 真实入口：`TestLevelRefresh.test_refresh_preserves_rendered_ownership_and_u1`；当前产品的 refresh 在 `_stage2_finalize.py` 将 render 记录替换为仅 `sha256`，按已批准的 r6 §4.5 预期红，属产品缺口，不是夹具错误。
- 该例只覆盖 r6 §4.5 的直接字段保留；A–H 及所有新消费/封存/写前机制仍 pending，不因该例通过而扩大。

### 4.3 执行准备、历史复用与责任

- 当前 t6 设计/步骤候选 pending 独立复核；第一关 L1–L6 业务范围沿用，本轮授权的直接缺口并入；t5 G2/G3 已通过的事实不撤销。新机制的 G2（资产/步骤接线）、G3（执行结果）pending，尚无新运行结果。
- 执行计划 r6 已获批准，产品负责人继续完成其尚未实现的修改；测试工程师准备上述受影响方法、适配共用 fixture 的真实 prepare/plan/结果集合封存入口，并填写 §4.1 实际函数/selector/产品与测试 SHA。当前已补 I 的字段测试，测试提交为 `6022e98`（r6 字段测试新增于 `db63276`）；A–H 等待 r6 产品入口。既有命令环境为 repo 的 `.apm/skills/professor-contact/tests`、Python 标准库 unittest、隔离 TemporaryDirectory；无需安装模型/服务。不得为通过断言修补产品返回或以自填关联冒充模型读取证明。
- 未来执行在步骤准备确认且另有运行授权后，仅用 `python3 -m unittest <实际填入的受影响完整选择器> -v` 定向运行。I 的选择器已存在，完整命令为 `python3 -m unittest test_stage2_analysis_level.TestLevelRefresh.test_refresh_preserves_rendered_ownership_and_u1 -v`；A–H 拟定名字尚未实现，不能把占位字符串当可执行命令。不恢复全模块/四分片/模型回归为门槛；如产品 diff 确实触及原 CRLF/refine 入口，只附相应现有方法选择器。
- 临时目录沿 `mktemp -d /tmp/u5-t6-XXXXXX`，日志只记实际命令/产品与测试 SHA/Python 版本/退出码/必要业务输出，仓库外保存。原始历史日志直接引用 §4.4–4.6，不重新筛选。文档静态 diff/读回不是产品测试。
- 失败按夹具准备、业务失败、环境无法判断、未执行区分；不因返回任意错误计通过，不放宽预期或重建 proof 求绿。业务失败即停止受影响项交产品 owner；fixture/步骤错误交测试工程师修正并复核，保留原尝试。无新信息的 provider/network 故障不重复采样；此确定性定向测试不需要外部调用或模型重试。
- 完成条件：本轮独立计划设计意见已处理；后续实际接线/步骤经 G2 确认，受影响目标取得适用 G3 结果。当前已准备 I 的字段测试但未运行；A–H 仅计划，不声称准备/执行已完成，更不授予合并批准。

下列 §4.4–4.6 原文按历史版本保留；其中“当前”“本轮”“待审核/失败”等均是记录当时口吻，t5 最终正式 G2/G3 状态以本文件顶部所引 10:58 审核为准，不能用这些历史句子推翻该结论或要求重做旧轮。它们也不代表 r5/t6 已实现。

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


