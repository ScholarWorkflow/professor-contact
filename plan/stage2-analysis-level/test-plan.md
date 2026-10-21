# U5：实际分析级别贯通与诚实统计测试计划

- Test plan revision：`u5-analysis-level-t4`，2026-10-21（UTC+08:00）。本正文整体取代 t3；唯一完整文件为 `plan/stage2-analysis-level/test-plan.md`，不并行执行历史正文或评论中的相反要求。
- 对象：[PR #106](https://github.com/ScholarWorkflow/professor-contact/pull/106)，分支 `plan/u5-analysis-level-redesign`；对齐[执行计划 r4](https://github.com/ScholarWorkflow/professor-contact/blob/3bfe8df6313b2047dad564163e07b30b36c7fd20/plan/stage2-analysis-level/implementation-plan.md)。修订读取基线 head `3bfe8df6313b2047dad564163e07b30b36c7fd20`、原测试计划 blob `033523a43b2b1ac8f7b1527db73afa4307224a54`。
- 用户已明确要求修改执行计划的三个机制，并随后要求“你改测试计划”。计划修订轮只修计划；随后测试准备轮按 §2–3 修改既有测试方法并补齐 §4.2 recipe，未修改产品代码、未运行正式用例。
- 当前设计状态：pending 独立复核，作者不自授 APPROVED/PASS。L1–L6 的业务范围保持；仅修正与 r4 直接相关的来源资格、完整守卫／旧绑定和磁盘字节检查。三个测试关口与历史结果分别见 §4、§5，不继承旧版“全部通过”为当前结论。

## 1. 范围、依据与复用原则

依据执行计划 r4 §1、§3–7、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 和 [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)。测试规则于本轮重新读取，页面最后编辑于 2026-10-09；沿用其范围、证据及三个关口规则。执行计划确定预期，不能从当前存在缺陷的实现反推预期。

清单 L1–L6 是验收上限。不引入 #92 整套矩阵、全教授流程、Stage 3/4、模型分析质量、引用／归属／时效重新验收、来源认证、边界笛卡尔组合、重复安装、全仓回归或两 harness 完整业务回归。不新增采集器、oracle、测试框架、全局锁或跨文件事务测试义务。两 analyzer 的来源 owner 和事实组装契约只作静态核对，不重新执行分析或外部 import 证明登记历史。

一个足够的真实业务入口可同时检查多个目标。优先最小修正现有方法，删除相反预期，不默认新增测试模块或固定测试数量。共同机制可由一个入口的业务结果加实际接线核对复用；不同输入读取／接受分支没有真正共用实现时，不能只凭同名 helper 或一个样例宣布全部覆盖。只补实际独有接线，不在单元、集成和全流程重复证明。

U5 独立于 U1；若共享 owner 变化，只检查直接受影响的行为，不要求 U1 标记、owner map 或第二套接受机制。未受影响结果直接复用，不因文档 SHA、提交编号或完整性审核重跑。以下“待修正”是现有清单对应方法尚未落实 r4，不是本轮运行授权。

## 2. 最小充分必测清单

### L1 当前成功资格一致贯通，不再接受矛盾 null

- 目标／依据：r4 §3、§4.1、§5.1。正常 facts 接受、下一轮 preflight 与锁内 refresh 使用同一 known／unknown／invalid 语义，分析 producer／成功 import 仍拥有登记。
- 输入／场景：沿既有 facts→finalize 的真实接受夹具保留 fulltext（含 OCR-only 与 facts unavailable）、abstract 和无登记但有文件的 null 正常输入。把当前“合法 known 登记仍在而 facts=null 可接受”的旧预期替换为拒绝；新 facts 缺字段使用同一未确认声明分支。用一个合法摘要源保留的失败升级状态、一个原 owner 已使正式状态变为 unknown 的状态及其后真实成功登记对照，覆盖资格转移，不枚举失败原因。无效 level 保留现有代表，坏／不可读记录与合法 unknown 的区分共用 L4。
- 预期：known 与声明必须匹配；known 遇新 facts null／缺字段，或 known 值／消费路径矛盾，按原输入错误零接受写入拒绝。有效 abstract 的失败升级仍为 abstract，不能制造 fulltext 或 null。正式来源已 unknown 且其余事实资格仍合法时，正常接受 null；下次预检与允许的刷新不能由旧 canonical 恢复 known。随后原 owner 提供新有效成功登记时可以转 known，旧 null 不永久压制它。Stage 2 不清 index、不制造失效证明；只有失败描述而正式登记仍 known 的矛盾必须报错等待原 owner。
- 检查方式：对上述正常接受后的持久 pack 继续调用既有 preflight；确属 level-only 的合法后续变化再调用实际 refresh，观察 canonical、分流和最终持久值。复用已有合法 validator 夹具，使分流的前提真实成立；无 terminal 记录时 process 不误写为级别不一致。拒绝时比较 pack、Markdown 接受状态未变。静态核对两 analyzer 均按当前登记组装新 facts、旧 facts 缺字段需重新组装而非回填 canonical，不强制重跑模型；不做生成来源认证。

### L2 canonical 各实际合流与旧 accepted 包兼容

- 目标／依据：r4 §4.1、§4.3、§5.1。fresh/reused/resolved/old 的 canonical 都显式采用当前核实值；旧 raw、兼容视图、candidate 三者不混淆。
- 输入／场景：复用现有 pack/finalize 夹具，仅覆盖实际不同合流代码；当前合法 unknown 覆盖旧 known（先按 L1 准备真实 unknown，而非让矛盾 facts 绕过登记）。旧 accepted schema 2 缺字段单独读取；随后给合法当前 known 的 facts 进入正常处理。v1 缺字段与 null 等价／known 冲突的现有迁移断言继续复用，不展开迁移矩阵。
- 预期：所有实际合流结果采用当前值，null 不被 truthy fallback 补回。旧 accepted 缺字段在兼容视图为 null，原 schema 2 与旧 raw／深快照未被候选修改；它不是新 facts 声明，不能阻止后来真实成功。原成员／reference 指向同一 canonical 记录；旧嵌套状态不被 reused/resolved 候选污染。
- 检查方式：结构化 pack、原始旧包字节和既有深快照断言。若各分支确实调用同一最终赋值，可复用共同结果并核对接线；独立分支才保留对应最小输入，不做四分支×三级别×validator 组合。L1 的接受序列可同时给出本项目标，L5 使用其未污染旧快照检查绑定，不重复执行。

### L3 只统计既有方向成员

- 目标／依据：r4 §1、§6.5。三类互斥、总数等于原 supporting 成员投影，不改成员或引用资格。
- 输入／场景：现有确定性 pack 包含三类 supporting 成员、reference/relevant-only 论文及跨方向共享成员。
- 预期：标题为“全文级 X 篇 · 摘要级 Y 篇 · 未确认 Z 篇（共 N 篇）”；reference/relevant-only 排除，共享成员按原贡献计数，不额外去重；成员 key、顺序、身份、引用许可不变。
- 检查方式：复用 `TestStatisticsRender` 两个现有方法的实际 Markdown 和 supporting_item_keys 断言。r4 未改变统计算法，本项现有结果继续适用；后续若实现实际改动该路径，再仅核对直接影响，不因修订计划重跑。

### L4 完整业务来源守卫与早期分流

- 目标／依据：r4 §4.2、§5.2。完整已接受来源与当前业务比较决定 process／refresh_level／reuse_all；有限路径投影不能代替 artifact guards。
- 输入／场景：保留已接受合法基线的完全不变、仅合法 level／统计格式变化、固定 missing facts 候选出现、旧投影缺失／旧不一致私有版本、坏来源记录的现有独立变体。对已存在合法分析来源加入路径、存在、level 不变而文件 stat 已变的实际磁盘变体；与 L6 锁内漂移共用夹具，不重复跑全部业务变化。既有已接受 PDF 的离线 no-PDF-read 检查复用。
- 预期：业务相同且 terminal 校验有效才 reuse_all；业务相同仅级别／格式变化才 refresh_level；业务变化、不可比较、旧不一致基线或坏输入先 process，不将 invalid 折叠为 unknown。index generated_at／KB id 等管理字段不影响业务判等。缺基线 process 不等于强制重跑有效模型，只有正常成功接受可建立新消费基线，refresh 不能补造历史来源。显式 chatgpt_result／kb_import 继续 process 优先。
- 检查方式：实际 preflight action、pack 的真实接受基线及现有 jobs 结果。针对完整守卫的源码核对只确认正常接受、preflight、锁内刷新确实共用包含原 stat／已得摘要的相同谓词，以及 analysis／facts／future-work／已接受 PDF 的实际接线；若某载体或时点仍独立走弱化分支，需在该独有入口最小补相应输入，不能把“一个 analysis 文件变了”称为未经接线验证的全来源覆盖。不要重做归属／时效算法、全 PDF hash、Zotero 查询或环境 trace。两 caller 的外部结果优先级只核对实际文本／分支语义，不把关键词出现当优先级证明。

### L5 完整旧绑定、合法生命周期及真实磁盘字节

- 目标／依据：r4 §4.3–4.4、§5.1–5.2。先验证旧 raw 绑定，再决定继承；正文比较只能忽略固定顶部时间 token，不能由读写归一化隐藏差异。
- 输入／场景：保留三个真实接受结果：统计正文变化；两个成员 level 换位且业务／正文等价；业务变化但正文等价。对等价场景使用独立旧绑定缺陷：旧 header.state_fingerprint 错配，以及现有 validator.render_sha256 错配；其他旧身份／body-header-cache／validator-pack 层按已有断言和实际共同谓词核对，缺少独立层检查时最小补该层，不把一个错误 render SHA 当作完整绑定。使用既有真实非终态 round1/pending 普通 finalize 和 refine 生命周期，不新增校验轮次矩阵。
- 预期：正文或业务变化使旧认证失效、原报告保留；两者等价且完整旧绑定有效才能保留合法 validator 并按原规则更新必要 pack 绑定。旧 header 或任何旧绑定无效不能由先修头／回填 candidate／重算 hash 恢复 PASS；refresh 拒绝且不写接受状态。普通 genuinely 新业务／正文仅能按原冲突与显式覆盖政策接受为未校验，内容不变不能重新签旧证据。首建不伪造旧绑定，无 validator 不伪造 PASS；合法 pending 不被 terminal gate 拒绝，terminal pass/skipped 只约束 reuse_all。旧 raw 不被 compatibility/candidate 污染。
- 磁盘字节场景与预期：将现有时间比较检查接到真实受管文件读取和正式接受入口。合法 LF 基线只改顶部生成时间候选时保留旧 body bytes 与真实 SHA；另将实际磁盘正文 LF 改为 CRLF 而不重签旧 header/cache/validator，必须被旧绑定／人工保护拒绝，不能因 universal-newline 转换仍继承。对合法 CRLF 文件用原始字节和标准 SHA-256 构造自洽的既有受管格式夹具，走同一无损读取/hash/冲突/写回路径；需要仅更新必要机器头时正文 bytes 不变，header/cache/validator 使用真实 body SHA。CRLF 旧正文与实际 LF 候选的差异仍属变化，不得强求等价或为 PASS 改 renderer 输出。尾换行差异与非顶部叙事时间的现有比较断言仅作为该同一语义的最小补充，不扩编码／所有空白组合。
- 检查方式：实际 runner 接受／拒绝、受管文件 `read_bytes()`、现有标准 `hashlib.sha256` 和 pack/header/cache/validator/report 断言，不调用被测归一化函数计算预期。不得在写文件前用 `read_text()` 抹掉换行再声称测磁盘；不得替换正式渲染输出或替身返回“守卫通过”。合法 CRLF 夹具只建立预先指定的已接受输入，不在被测调用后修补绑定求通过。正式路径未具备合法仅更新头的触发条件时，接到它真实调用的既有受管写入口检查保存 bytes，另核对调用接线，不发明产品 API。
- 复用边界：正常 finalize、refresh、preflight、validation、managed conflict/write 的共同无损原语与分层谓词须实际接线后才能共享结果；不同独有 I/O 路径最小补检查，不复制整套接受场景。刷新仍只改 level、统计接受元数据及必要包绑定，保留成员、assignment、模型结果、resolved proof 与无关有效缓存，不消费临时 facts 或执行模型。

### L6 锁内完整复核、写前漂移与原 refine 保护

- 目标／依据：r4 §5–6。刷新使用已有 lease，获锁后和写前都核对完整业务／来源及接受文件；原 refine 保留合法轮次、清 preflight、不清无关有效缓存。
- 输入／场景：保留 busy、人工 body、一次 Markdown 已写而 pack 持久失败、release 成功／失败的已有结果和断言。将原仅“预检后 target 改变”的漂移检查最小修正为真实刷新入口中：在获锁后的重新观察之前改变已存在分析文件，路径／存在／level 保持；另在该观察之后、正式写入之前改变已有 guard 可见的来源或接受文件，以区分第二个检查时点。沿既有 lease／写入替身在准确边界改变真实临时文件，不替换比较结果，不建竞态框架。L4 的源类型接线核对决定是否有独立弱分支，避免无依据地穷举所有载体×时点。
- 预期：busy 零业务写入；任一可观测漂移返回原 needs_refresh、零接受写入、不补造新来源基线，finally 释放自持 lease，随后 process 而非继续纯级别刷新。人工 body 不覆盖。release 失败如实报告；部分 I/O 失败未完成且不承诺回滚，下一次完整旧绑定不允许直接 reuse，不补打成功标记或自动救旧 PASS。
- 检查方式：真实 pack、Markdown、锁与原返回状态，复用现有 unittest mock。原 `test_business_rerender_and_bounded_correction_lifecycle` 中合法 pending→refine→第二轮及缓存断言继续使用：当前 render SHA 对实际 body、无关 cache 与 cache.render 不变、cache.preflight 清除、不重置 round1。仅因 r4 共用绑定／I/O 接线受影响时定向复核该方法；不重做其全部历史 T5 业务或扩大轮次测试。
- 边界：lease 只锁合作 writer，stat 只提供原合同可观察的一致性。这里不要求不可观察外部修改的绝对原子快照，不增加全局锁、外部文件锁或跨文件回滚承诺。

## 3. 当前资产、最小修正与历史适用性

以下现有方法在基线 head 已读取，位于 `.apm/skills/professor-contact/tests/`。名称表示已有资产，不表示 r4 检查已实现。历史固定版本与结果见 §5。未来只修这些方法中实际受影响断言，不能保留相反旧预期再新增一个“新规则”平行测试。

| 目标 | 当前真实资产与局限 | 本轮接线决定／结果适用性 |
|---|---|---|
| L1 | `test_stage2_analysis_level.TestFactsLevelContract` 的 known/unknown、冲突、非法值、无登记、OCR-only、消费路径方法；`test_explicit_null_clears_a_registered_level` 在合法 known index 不变时断言 null 接受 | 旧 null 方法预期与 r4 相反，不可复用为通过；最小替换为冲突零写入并接合法 unknown→下一轮→新成功序列。其他已知正常事实结果保留，不重复外部导入。失败升级摘要有效分支不能由 null 样例替代 |
| L2 | `TestCanonicalMerge.test_known_level_survives_a_reuse_finalize_and_validator`、`test_missing_level_field_in_an_old_pack_reads_as_null`、`test_v1_migration_treats_missing_and_null_alike_but_rejects_conflict` | 旧缺字段方法同时传与 known index 矛盾的新 null facts，故旧通过不能证明 r4 兼容；分离旧 accepted 兼容视图与新 facts，最小修正。v1 等价现有结果复用；合流接线随实际改动检查 |
| L3 | `TestStatisticsRender.test_header_counts_members_only_and_shared_members_per_contribution`、`test_reference_only_paper_stays_out_of_the_statistic` | 现有统计／身份结果有效复用，不要求重新执行 |
| L4 | `TestPreflightBranches` 中 unchanged、level-only、management fields、fixed facts、missing projection、illegal index、not accepted validator | 保留仍适用的预期／历史结果；missing projection 修正覆盖现有私有版本保守失效，补现有 artifact stat 与 L6 的共同守卫接线。旧关键词静态断言不是优先级完整证明 |
| L5 | `TestLevelRefresh` 中统计变化、等价换位、业务变正文等价、人工 body、legacy stats；`test_invalid_old_binding_is_an_evidence_error_not_a_rebind` 只改 validator.render_sha256 | 旧 render 错配仅证明这一层，不覆盖 header.state_fingerprint 或完整层次；按 L5 最小扩展。legacy stats 旧夹具只改正文/cache 且未保持完整旧头绑定，须按 r4 修正为合法旧格式输入或预期拒绝，不能用破损旧态证明格式升级成功 |
| L5 字节 | `TestGenerationTimeNormalization.test_only_the_generation_time_is_ignored` 直接向 helper 传字符串 | 历史 helper 通过保留，但不证明磁盘 CRLF 无损；转接真实磁盘读/hash/比较/写，保留时间、统计、尾换行的有限语义，不为这些再建平行框架 |
| L6 | `TestRefreshProtection.test_binding_drift_returns_needs_refresh_releases_and_writes_nothing` 在调用前改 target | 只证明旧 target 漂移；不证明锁内 artifact 重验和最终写前检查。按 L6 修正准确时点和文件。其他 busy/release/I/O 方法保留，I/O 旧方法未观察失败后的下一次 preflight，最小接后续拒绝复用 |
| L5/L6 共享生命周期 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle` 有普通 pending finalize、refine、两轮及缓存断言 | 历史 `231ba03` 结果不撤销。r4 如修改它所经共同绑定/I/O，定向复核这些直接行为，不能误用 terminal 复用条件拒绝合法 pending；不扩完整旧 T5 清单 |
| 来源与缓存保护 | `TestRefreshProtection.test_refresh_keeps_the_accepted_sources_and_foreign_cache` | 旧结果证明既有来源/cache 不被刷新替换，不证明来源最新有效。复用其保持断言；若增强绑定使原夹具新增元数据后旧 validator 不再合法，应在被测调用前建立合法夹具，不绕过新保护 |

上游已有 `test_stage2_chatgpt_handoff.HandoffTests.test_valid_result_installs_analysis_sidecar_and_index`、`test_ocr_only_fulltext_build_and_import_without_pdf` 只作成功登记资产；`test_stage2_facts_sidecar` 的 facts→pack／副车变更、`test_stage2_preflight.PreflightBase.build_accepted_state` 与 no-PDF-read／正常 finalize 竞态入口继续复用。没有因此把整文件或全仓登记为本轮必跑。

## 4. r4 的接线与三个关口状态

### 4.1 当前事实

- 第一关口：L1–L6 原范围已确认；t4 按用户已批准 r4 修正相反预期与不足方法，完整候选待独立设计复核，作者不宣布新批准。
- 第二关口：t3 已有公开审核结论，不再标成“t3 待审”。测试资产已按 §2–3 改到 r4，recipe 见 §4.2；产品修复已由 `81c38d4` 提交，第二关口仍待独立审核在实际产品提交上核对受影响接线、选择器和具体命令，不重开未受影响范围。
- 第三关口：§5 是真实历史结果；r4 受影响机制已在 `81c38d4` 上执行，结果见 §4.4。不能以 34 tests 或 1064 tests 旧绿代替；L3 及实际未变子目标复用旧结果，L1/L2 的矛盾预期、L4/L6 完整守卫、L5 旧绑定／实际字节和共享生命周期接线以 §4.4 的新结果为准，关口结论仍待独立审核。
- 当前产品 r4 修复已提交；测试准备缺口与产品失败分开记录，不声称第二/第三关口已通过。§4.4 记录本轮新的正式执行，独立关口审核仍待完成。

### 4.2 本地测试工程师补齐的 recipe（r4）

- **准备状态**：测试资产已按 §2–3 改到 r4；准备时产品 r4 三个机制尚未入库（基线 `7c42a40`），因此当时预期 L1/L2 的矛盾 null、L4/L6 的锁内完整守卫、L5 的旧 header 绑定与 CRLF 字节检查失败。产品修复提交 `81c38d4` 已入库，执行结果见 §4.4；不得为求绿改断言或预期。
- **本阶段预检**：Python 3.14.7 下 `py_compile` 通过；测试模块可导入，`unittest.TestLoader` 统计 49 个测试；本 recipe 的类选择器与逐项方法选择器均可解析；`git diff --check` 通过。未运行任何目标测试方法、产品入口或正式业务请求。
- **环境与工作目录**：仓库根目录下 `.apm/skills/professor-contact/tests`；Python 标准库 `unittest`；不加载模型、Zotero、网络或生产 PDF；每例沿用既有 `TemporaryDirectory`。本机 Python 3.14.7，CI 为 Python 3.12（`.github/workflows/ci.yml`）。
- **准备顺序**：1）固定产品 r4 提交与测试提交，工作树干净；2）按 §3 建立合法正常接受基线，只有指定缺陷变体在调用前故意破坏对应层，header/cache/validator 初始自洽；3）运行下列选择器；4）只记录退出状态和业务结果，原始输出放仓库外。
- **L1 选择器**（`test_stage2_analysis_level.TestFactsLevelContract`）：
  `test_known_and_unknown_levels_reach_the_canonical_pack`、`test_facts_level_conflicting_with_the_current_registration_is_invalid`、`test_illegal_level_is_an_input_error`、`test_null_facts_against_a_known_registration_are_rejected_without_writes`、`test_missing_level_field_against_a_known_registration_is_rejected`、`test_unknown_level_accepts_null_then_a_new_registration_turns_known`、`test_abstract_registration_survives_a_failed_fulltext_upgrade`、`test_analysis_file_and_pdf_without_a_success_registration_are_unknown`、`test_consumed_analysis_path_contradicting_the_index_is_invalid`、`test_ocr_only_fulltext_without_facts_can_still_be_fulltext`。
- **L2 选择器**（`test_stage2_analysis_level.TestCanonicalMerge`）：
  `test_known_level_survives_a_reuse_finalize_and_validator`、`test_current_legal_unknown_overrides_an_old_known_canonical`、`test_missing_level_field_in_an_old_pack_reads_as_null`、`test_v1_migration_treats_missing_and_null_alike_but_rejects_conflict`。
- **L3 选择器**（`test_stage2_analysis_level.TestStatisticsRender`）：
  `test_header_counts_members_only_and_shared_members_per_contribution`、`test_reference_only_paper_stays_out_of_the_statistic`。r4 未改统计路径，按 §3 复用 `0b9a585` 的历史通过结果；只有产品实际改统计路径时才定向重跑。
- **L4 选择器**（`test_stage2_analysis_level.TestPreflightBranches` 全部）：
  `test_unchanged_state_reuses_all`、`test_level_only_change_takes_the_refresh_branch`、`test_management_fields_do_not_change_the_business_source`、`test_new_fixed_facts_candidate_is_a_business_change`、`test_missing_projection_processes_once`、`test_illegal_index_level_processes_instead_of_writing_a_known_value`、`test_not_accepted_validator_blocks_reuse_all`；并复用 `test_stage2_preflight.TestPreflightDecision.test_b_perfect_no_change_reuses_without_pdf_reads`、`test_j_deleted_artifact_prevents_reuse`、`test_k_artifact_stat_change_prevents_reuse_without_pdf_reads`、`test_p_validator_gate`。
- **L5 选择器**（`test_stage2_analysis_level.TestLevelRefresh`）：
  `test_statistic_change_updates_body_and_expires_old_certification`、`test_equivalent_body_swap_keeps_the_valid_old_certification`、`test_invalid_old_binding_is_an_evidence_error_not_a_rebind`、`test_invalid_old_header_binding_is_an_evidence_error_not_a_rebind`、`test_legacy_statistics_body_is_reaccepted_before_the_marker`、`test_statistics_marker_only_refresh_keeps_the_old_body_bytes`、`test_refresh_with_an_illegal_index_level_returns_needs_refresh`（同时覆盖 L1 的 invalid refresh 语义）、`test_legal_crlf_managed_file_is_read_as_real_bytes`、`test_crlf_body_without_a_matching_binding_is_not_accepted`、`test_business_change_with_equivalent_body_keeps_body_but_expires_certification`、`test_manual_body_edit_needs_decision_without_writing_the_pack`。
  以及 `test_stage2_analysis_level.TestManagedBodyBytes` 全部：`test_only_the_fixed_generation_time_is_ignored`、`test_statistics_and_narrative_time_stay_significant`、`test_crlf_bytes_are_read_and_hashed_without_normalization`、`test_legal_crlf_body_keeps_its_bytes_when_only_the_header_changes`、`test_crlf_body_without_a_matching_binding_is_not_accepted`、`test_a_crlf_old_body_and_an_lf_candidate_are_a_change`。
- **L6 选择器**（`test_stage2_analysis_level.TestRefreshProtection`）：
  `test_busy_writer_returns_without_any_business_write`、`test_source_drift_after_lease_returns_needs_refresh`、`test_source_drift_after_observation_returns_needs_refresh`、`test_refresh_keeps_the_accepted_sources_and_foreign_cache`、`test_successful_refresh_releases_the_lease`、`test_release_failure_is_reported_on_the_success_path`、`test_release_failure_on_a_soft_exit_is_also_reported`、`test_pack_io_failure_after_the_markdown_write_stays_unfinished`；并定向复核 `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle`，只核对 r4 影响的绑定／I/O 行为，不重做其全部历史 T5 业务。两个漂移用例在测试进程内直接调用 `contact_state.cmd_stage2_refresh_level`；观察后漂移用例先捕获 pack/Markdown 快照，再 arm gate 后的 render-precheck 入口（`Stage2PackRefineContext` 的既有静态方法），使修改落在观察之后、写入之前；其余用例仍可走 CLI。
- **命令**：
  - `python3 -m unittest test_stage2_analysis_level -v`
  - `python3 -m unittest test_stage2_preflight.TestPreflightDecision.test_b_perfect_no_change_reuses_without_pdf_reads test_stage2_preflight.TestPreflightDecision.test_j_deleted_artifact_prevents_reuse test_stage2_preflight.TestPreflightDecision.test_k_artifact_stat_change_prevents_reuse_without_pdf_reads test_stage2_preflight.TestPreflightDecision.test_p_validator_gate -v`
  - `python3 -m unittest test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle -v`
  - 本轮没有新增测试文件，`plan/test-grouping/shards.json` 不需要变更；不把四分片或全仓回归作为 r4 的必跑义务。
- **输出位置**：执行工程师用 `mktemp -d /tmp/u5-r4-XXXXXX` 建立仓库外目录，把上述三条命令的 stdout/stderr 分别保存为 `module.log`、`preflight.log`、`lifecycle.log`；记录产品 SHA、测试 SHA、Python 版本、退出码、`Ran N tests` 和 OK/FAILED。原始日志不提交、不推送。
- **失败处理**：L1/L2 矛盾 null 或 L4/L6 锁内守卫失败，保留原结果并交产品 owner；L5 旧绑定／CRLF 失败先确认测试夹具在调用前自洽，再交产品 owner；方法自身错误先停止受影响项、修正并复核；不得换输入或放宽断言求绿。缺日志先请求已有记录，不默认重跑；无法运行与未执行如实区分。

### 4.3 完成条件与责任

测试计划工程师负责本正文和预期；产品 owner 落实三个机制；本地测试工程师落实已有测试的最小修正与可执行接线；独立 reviewer 分别核对设计、受影响第二关口与第三关口；执行工程师只按确认方法及执行授权运行。所有 L1–L6 已知范围内缺陷处理、当前有效必测结果齐备才结束。没有“补一次全仓”或“所有平台再跑”的隐藏收尾门槛。

### 4.4 r4 执行结果（2026-10-21）

- **产品／测试提交**：`81c38d4fb0293051cc163d58e92672e4a0be4013`。在 `7c42a40` 的 r4 计划与 t4 测试基础上，补上矛盾 null 拒绝、锁内 artifact 守卫与写前复检、旧 header 绑定拒绝、CRLF 原始字节读取／摘要／比较／写入。
- **测试夹具修正**：`TestManagedBodyBytes._write_managed` 原返回整个受管文件字节，`body_sha` 断言无法成立；按 §4.2 的“方法自身错误先停止受影响项、修正并复核”改为返回正文 SHA，未改变任何断言或预期。
- **环境**：macOS、Python 3.14.7、标准库 unittest；工作树在执行前干净。`run_dir=/tmp/u5-r4-eX3zpI`，原始日志为 `module.log`、`preflight.log`、`lifecycle.log`，不提交。
- **命令与结果**（三条命令退出码均为 0）：
  - 在 `.apm/skills/professor-contact/tests` 执行 `python3 -m unittest test_stage2_analysis_level -v`：`Ran 49 tests in 15.922s`，`OK`。
  - 执行 §4.2 的四个 preflight 选择器：`Ran 4 tests in 1.342s`，`OK`。
  - 执行 L6 生命周期选择器：`Ran 1 test in 5.912s`，`OK`。
- **额外全量回归**：在提交前的同一代码内容上运行四分片，shard1 380、shard2 219、shard3 237、shard4 243（1 skipped），合计 1079 tests、无失败；日志 `/tmp/u5-r4-shard1.log` 至 `/tmp/u5-r4-shard4.log`。该全量结果不是 t4 的必跑门槛，推送后 CI 会在提交上复验四片。
- **结论**：本次执行范围内 L1–L6 的当前测试全部通过，没有未执行的 r4 必测选择器。该结果不是第二／第三关口或合并批准；独立审核者仍需在实际提交上给出关口结论。

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

