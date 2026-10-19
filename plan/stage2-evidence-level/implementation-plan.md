# Stage 2 固定证据展示、失败登记与分析级别修复

- Requirement revision：2026-10-17 用户要求为此前 U1、U5 两项修复建立独立计划 PR（北京时间）；依据用户提供的《PR91未覆盖问题报告_20261016.md》。报告中的私人实际数据与失败次数不是本计划已复验结果。
- Plan revision：contact-evidence-level-r10；Proposed review status: pending（2026-10-19）。依据用户本轮“直接修改执行计划，写清执行方式并避免同类旧问题”的要求，将 r9 两处修正收敛为一个内部展示接受步骤，并补齐已误标版本 `2` 的旧正文恢复路径。r8 的[正式批准记录](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6260927099)仅作为历史依据；本文件是当前唯一完整候选，不继承旧批准状态。
- 目标：ScholarWorkflow/professor-contact，PR #92 当前计划修订基线 `d9fdb8ffe26a2cfcea2123c74637b1763c6d3dfd`。U1/U5 原产品基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`；r7 七项与三处源码修正见[交付记录](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6260319513)；r8 展示分流的历史产品提交为 `5582dfa`，相关测试结果只按其记录版本使用。当前产品的私有展示版本仍为 `2`，本候选修复后的目标为 `3`；这不是公开 schema 或业务契约升级。
- r10 初次发布仅修订本执行计划，未修改测试计划。随后按用户授权，唯一测试计划已作 t45 候选文档对齐：当前目标 `3`、已误标 `2` 的旧包纳入 t44 原两条正式路径；本文件只同步此交接状态，仍为 r10，不新增执行算法版本。两份候选仍待正式审核，r10 产品实施、测试准备与执行未完成；本轮未改产品或测试代码、未运行测试。保留 r7 的统一 paper 构造、当前来源解析、成员归属、写入保护及 PR91/PR93 集成；当前执行指令仍集中在 §3.3.3—7 和 §4，受影响行为与下一负责人见 §4.9。
- 唯一测试计划：[test-plan.md](test-plan.md)。按 [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)执行。

## 1. 范围与验收目标

U1：固定证据卡正文不泄漏内部论文编号；真实文字阻挡必须能登记，说明处理归属，不能因模型无权改事实而连失败也无法记录。作者原句、译文、出处、时效结论、署名、用户笔记与红线不得被文字修订改写。

U5：全文/摘要统计取实际成功分析的级别，不能用分析文件存在或 PDF 存在代替。级别缺失、失败或不明不能自动冒充全文或摘要。

不包含 U2/U4 分句、U3 跨页 sidecar、成员归属重构、Stage 3—5、新 Nix 安装、全教授业务重跑、额外去重统计。遵守 [Nix 单源边界](https://app.notion.com/p/3fb0101a85f38185b17adb417590e50e)：改正式业务源，不在安装产物或 Nix 层补另一套业务实现。

[PR91](https://github.com/ScholarWorkflow/professor-contact/pull/91) 历史提交 `b0991da8e0b0f9456acbcdd79dece96c53164dec` 的执行 r3 / test-r3 处理另外三项缺陷，本 PR 不复制它的全套修复与测试。当前已整合的状态见 §3.4；交叉范围仅为记录器/普通 finalize 生命周期改动；PR91 的“不可修订区域拒绝”在本 PR 的新授权范围内改为“允许记录、禁止模型改写”。不存在必须等待 PR91 全部业务完成的依赖。

## 2. 决策依据（当前源码事实，不替代需求）

第 1—9 项是原 U1/U5 基线事实，行号对应 [contact_state.py](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py)。

1. 展示归 runner：L4042–4055 接受非空 model_evidence，L4286–4293 带入 gap，L4481–4518 原样写固定卡 evidence/completed_part/remaining_gap 及禁锚区 evidence；因此模型合法机器结果中的 item key 可泄漏。既有 `redact_item_keys`（L4236–4243）可作局部复用，但其未知编号替换不能冒充已核验引用。
2. 登记与修订权限是两回事：`stage2_validation_report` L10716–10989 已做报告/正文/方向绑定；L10980–10984 把不属于 narrative 的 blocking 拒绝。`stage2_require_recorded_validation` L10992 起又要求先登记，所以固定区阻挡没有处理路径。
3. 仍可保持 fail closed：`stage2_validator_accepts` L3609–3654 仅接受有效绑定的 terminal pass/skipped；`stage2-refine-plan/finalize` L11088–11243 是唯一 narrative 修订入口。新增失败记录不能使通过门槛放宽。
4. 实际分析级别已存在于 Stage 2 写入的索引：Codex analyzer [L339–380](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L339-L380) 明确成功的 pdf/ocr 路由为 fulltext、abstract_json 为 abstract。它的 [L405–430](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L405-L430) facts 示例漏传级别；runner L4323–4334、L4720–4740 规范记录也未保存级别，L4384–4386 错用文件/PDF存在计数。
5. 已有分析级别与 facts 可用性不同：analyzer L263–274 允许 OCR-only fulltext 分析而 facts unavailable。不能用 facts_state 反推分析级别。
6. analyzer 的 [Step 2.6 L142–159](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L142-L159) 在 reuse_all 时不进入 facts 准备或 finalize；因此仅在 finalize 比较 level 或增加渲染版本，无法发现同版本下成功分析索引的级别变化。
7. `Stage2PackRefineContext` L1707–1765 已提供临时 facts 过期后的持久包展示上下文，但它不是完整业务 facts；普通 finalize 仍依赖 facts，不能将该上下文伪装成 facts 重验/重签旧 resolved 结果。
8. preflight cheap inputs L3352–3381 不读取分析索引，`_artifact_guards_for_keys` L3411–3444 只登记已有路径且已存在的文件；现状不能仅凭“旧 guards 未变”排除新增分析/sidecar 或索引换址，不能直接据此批准仅展示刷新。
9. 普通 finalize L5020–5080 可能不重绘、继承旧 validator；升级展示和级别后必须只使受影响生成物失效，不能重新绑定旧 PASS。PR91 §3.4.1 已设计实质变化/等价重写区分，可复用同一实现，不另建历史系统。
10. r8 修复前的历史展示版本缺口（下列链接的版本事实，不代表当前代码）：`STAGE2_DISPLAY_REFRESH_VERSION` 当时为 `1`，成功刷新才写入 `cache.preflight.display_refresh_version`；正常成功接受基线的 `stage2_preflight_metadata` 未持久保存它，预检只在 `level_changes` 非空时选择 `refresh_display`，而刷新入口对空 `level_changes` 直接拒绝。因此已接受包即使业务来源与级别都未变，仍可能因旧展示规则留下原始论文编号而被 `reuse_all` 沿用。对应[版本常量](https://github.com/ScholarWorkflow/professor-contact/blob/9505081d14a0e4a02627fed0a530b0e7c4c4db64/.apm/skills/professor-contact/scripts/contact_state.py#L127-L140)、[基线生成](https://github.com/ScholarWorkflow/professor-contact/blob/9505081d14a0e4a02627fed0a530b0e7c4c4db64/.apm/skills/professor-contact/scripts/contact_state.py#L4019-L4099)、[预检分流](https://github.com/ScholarWorkflow/professor-contact/blob/9505081d14a0e4a02627fed0a530b0e7c4c4db64/.apm/skills/professor-contact/scripts/contact_state.py#L4428-L4445)、[刷新入口](https://github.com/ScholarWorkflow/professor-contact/blob/9505081d14a0e4a02627fed0a530b0e7c4c4db64/.apm/skills/professor-contact/scripts/contact_state.py#L6529-L6543)。本项为已确认 U1 的旧包适配事实，不把私有版本号升级成产品契约。

11. **r9 新确认的正文比较事实（描述证据）**：[`contact_state.py@aae1d54` L6502—6514](https://github.com/ScholarWorkflow/professor-contact/blob/aae1d54ca5065b907c794557c772d2753695de6d/.apm/skills/professor-contact/scripts/contact_state.py#L6502-L6514) 的 `stage2_visible_body()` 对正文每一行查找 ` ｜ 数据来源：`，并舍弃此前全部文字；而同一 runner 的 `render_analysis_md()` 既生成唯一的报告顶部数据来源行，也会打印来源数据中的固定卡 evidence 文本。旧行 `- 后续论文依据：AAAA1111 ｜ 数据来源：作者论文` 与新行 `- 后续论文依据：[可信题名](zotero://select/library/items/AAAA1111) ｜ 数据来源：作者论文` 会被该比较错误视为相等，实际 U1 转换得不到写入，旧校验可能被保留。变基后同一问题仍存在于 [`contact_state.py@d69d993` L6479—6491](https://github.com/ScholarWorkflow/professor-contact/blob/d69d9938456a05330df30033200887cd974da8ac/.apm/skills/professor-contact/scripts/contact_state.py#L6479-L6491)。正式要求依据为 §1 的 U1 和 §3.3.5 的正文实质变化判断。
12. **r9 新确认的普通路径事实（描述证据）**：[`contact_state.py@aae1d54` L6281—6288](https://github.com/ScholarWorkflow/professor-contact/blob/aae1d54ca5065b907c794557c772d2753695de6d/.apm/skills/professor-contact/scripts/contact_state.py#L6281-L6288) 仅按模型任务、新包或 `stage2_render_state` 差异选择正常 finalize 的重绘；[`L6331—6338`](https://github.com/ScholarWorkflow/professor-contact/blob/aae1d54ca5065b907c794557c772d2753695de6d/.apm/skills/professor-contact/scripts/contact_state.py#L6331-L6338) 调用的 [`stage2_preflight_metadata` L4133—4138](https://github.com/ScholarWorkflow/professor-contact/blob/aae1d54ca5065b907c794557c772d2753695de6d/.apm/skills/professor-contact/scripts/contact_state.py#L4133-L4138) 直接登记新展示版本。旧包即使因文件保护变化走正常 `process`，只要模型及展示状态可复用，就可能保留含原始编号的旧 Markdown，却登记版本 `2` 并沿用旧校验。正式要求依据为 §1 的 U1、§3.2 和 §3.3.3—5；变基后同一分支仍见 [`contact_state.py@d69d993` L6258—6265](https://github.com/ScholarWorkflow/professor-contact/blob/d69d9938456a05330df30033200887cd974da8ac/.apm/skills/professor-contact/scripts/contact_state.py#L6258-L6265) 与 [`L4110—4115`](https://github.com/ScholarWorkflow/professor-contact/blob/d69d9938456a05330df30033200887cd974da8ac/.apm/skills/professor-contact/scripts/contact_state.py#L4110-L4115)；需要冻结成功登记版本前的正文校验顺序。

13. **r10 当前核对与恢复缺口（描述证据 → 决策）**：在本轮基线 [`d9fdb8f` 的 runner](https://github.com/ScholarWorkflow/professor-contact/blob/d9fdb8ffe26a2cfcea2123c74637b1763c6d3dfd/.apm/skills/professor-contact/scripts/contact_state.py) 中，L293 的目标仍为 `2`；L4110—4115 的 metadata 构造器直接赋版本；L6254—6349 的普通 finalize 仍按模型任务与 `stage2_render_state` 判定重绘，再生成带新版本的接受基线；L6479—6491 的正文比较仍对任意来源分隔符截前缀；L6687—6762 的刷新路径另有自己的渲染/比较/旧校验处理。故第 11／12 项缺陷在当前基线仍成立。L3324—3346 把等于常量的版本视为 current，L4454—4472 仅对旧版本或 level 差异选择刷新：先前 buggy finalize 已可能留下“旧正文 + 合法旧绑定 + 版本 2”；若只修两个分支却保持目标 2，后续仍可能 `reuse_all`。因此将私有目标推进至 3，沿用既有 stale 分流，让包括误标 2 在内的旧接受包在下一次调用核验实际正文；不新增迁移系统或正文认证字段。
14. **共享接受步骤的现有落点（描述证据 → 决策）**：同一 runner L5330—5356 由 renderer 生成完整正文及固定位置的唯一数据来源标题；L1207—1253 的 frontmatter／`managed_write` 已提供包装和人工改动保护；L6454—6476 可读取受管正文；L6317—6349 与 L6721—6762 已有旧包／正文绑定、失效或保留的语义。r10 将这些职责收敛到两入口共用的一份内部接受实现，metadata 构造器只准备业务元数据，不能声明正文已接受。L6395—6416／L6625 起的刷新 lease、来源与年份复核照旧；普通 finalize 保留自身原业务/preflight 保护，不另造锁或跨文件事务。L12108 起的 narrative refine 另有第一轮→修订→第二轮生命周期，本次不把它接入“正文变化即重开”的处理。

## 3. 实施方案

### 3.1 固定证据展示

- runner 使用当前可信论文元数据及 `candidate_paper_ids` 解析已知 item key，在固定卡 evidence、completed_part、remaining_gap 及禁锚区 evidence 的既有人读展示出口统一显示题名及 Zotero 链接；编号仅留机器字段或链接目标。保留原 model_evidence 和候选引用列表，不改变 freshness 判定、不删整段依据。
- 已知编号出现在说明句时只做等价引用替换，保留其余文字含义；不改作者 quote、translation、status；completed_part、remaining_gap 和 evidence 仅转换展示引用，其原始机器字段逐字保留，不改结论和原意。仅对上述生成出口作确定性格式化，不做全文清洗，不改用户笔记或作者引文。明确属于论文引用但缺可信题名时不能猜标题/静默删除，明确报告所缺元数据并停止受影响生成，交 Stage 2 数据准备者补齐后重试。普通日期、数字及无引用含义的文字不因匹配八位字符就被当成引用。
- 引用识别和展示同属 Stage 2 固定证据出口：`stage2_referenced_item_keys` / `stage2_collect_display_references` 与 `stage2_display_text` 使用一致的正式引用信息（规范论文映射、候选引用及完成论文引用），不能仅靠 `ITEM_KEY_RE` 判定任意八位文本。先保护经可信元数据核对、题名和目标均正确的已有论文链接，避免替换其地址或产生嵌套链接；裸 key 只有能由上述引用信息确认才转换。明确引用缺题名仍 fail closed，不能因引用收集漏掉它而降为普通文本。只做该出口的兼容修复，不全局修改 `ITEM_KEY_RE`，不改变机器 evidence、schema、freshness cache、Stage 3—5，也不要求模型改成 `{{P:...}}`。
- 固定卡术语需要解释时由已有 narrative.gap_notes.explanation 承担独立说明；不将作者原句/译文变成可自由重写字段。固定模板的措辞缺陷交 runner 实现者，事实或译文错误交其原 producer，用户笔记保持用户所有。
- 新鲜构建和 pack-only 重渲染都从输入包的可信引用元数据取得同样展示。将上述展示出口实际引用的题名/年份持久保存或复用已有可用论文映射；仅有事实关联不扩大 supporting_item_keys 或 narrative 的 P/L 引用许可。缺少旧元数据要求从正式 Stage 2 准备刷新，不能从正文反解析。

### 3.2 真实失败可登记，权限不扩大

- 保留原始报告格式、精确位置/方向归属、当前正文及输入包摘要校验；先完成这些合法性检查，再把 blocking 分为现有 narrative 可修订项与允许校验的固定证据卡项。不得仅把 require_repairable 改成 false 后把全部问题发给模型。
- 报告合法时原样保留 issues/notes/raw verdict，仍在既有 validator schema 2 中按当前合法轮次登记；第一轮 blocking 为 needs_correction。增加最小的固定区阻挡及责任说明字段（字段名称为实现细节），不改原报告、不新增通用状态机/问题库。
- 用户笔记、论文一览等现有明确跳过区域仍不属于合法校验对象，相关报告继续拒绝，不因本修复扩大校验范围。只要本轮含合法固定证据卡阻挡（包括混合报告），refine-plan 返回明确的“需修复源数据或生成器”结果、零 rewrite jobs；refine-finalize 同样拒绝写入。调用方停止自动修订/校验循环，报告具体引文和责任归属，不自动再次运行相同失败。
- 仅 narrative 阻挡仍走现有一次修订→第二次校验。固定区阻挡不被写成 pass/skipped；第一轮发现固定阻挡时仍是第一轮真实未解决失败，不写 fail_after_2_rounds；如果第一轮只有 narrative 问题、合法修订后第二轮首次发现固定卡阻挡，则照常登记 terminal/fail_after_2_rounds 并交源 owner，不降回第一轮、不再发修订。后续直接提交第二轮或伪造修订完成不得越过既有顺序校验。
- 生成器/正式源修复后，通过正常 Stage 2 finalize（业务源变化）或 §3.3 受保护展示刷新（仅展示变化）重建受影响受管正文，旧报告留在原路径。只有校验依据实质变化才失效旧 validator，并对新业务版本重新开始校验；相同正文或仅时间戳变化不能清零两轮限制。正常 narrative refine 的正文变化不属于重开版本，必须保留原第一轮/问题直到第二轮。
- 同步主 SKILL.md、两个 analyzer 安装投影的 Stage 2 分支说明；style-validator 保持现有文字标准，不通过屏蔽固定卡或放宽 C8 求通过。两种 harness 只同步已有业务交接，不新增委派机制。

### 3.3 分析级别贯通、分流与兼容

1. **级别来源与统计。** Stage 2 analyzer 在正常成功分析/导入后，从教授 `论文分析/_index.json` 的相关论文记录读取实际 level，并在 facts.papers[] 增传 `analysis_level`（fulltext/abstract/null）；失败、未完成、陈旧或缺失级别为 null，非法枚举报输入错误。不从文件存在、PDF 或 facts_state 推断；OCR-only 成功全文仍为 fulltext。保持现有成员规则，按各方向 `supporting_item_keys` 的正式成员统计全文/摘要/未确认三类及合计；引用范围与规范 `papers` 映射不等于统计集合，不新增去重。同步两个 analyzer 和 SKILL。
2. **统一来源解析与当前接受基线。** 在 Stage 2 runner 内设置单一来源解析入口，供正常处理成功接受基线、preflight、刷新入口及取得既有 writer lease 后的写前复核调用；当前 `stage2_analysis_index`、`stage2_analysis_projection` 与 artifact guards 的相关规则收敛到该职责，不让三条路径各自猜测。范围仍是 `stage2_candidate_universe/selected_candidate_union` 的本次被选方向候选并集（覆盖相关/缺口及 resolution 来源），不缩为正式成员，也不全库扫描。两种 analyzer 的正常来源发现说明对齐这一个来源契约，不在 analyzer 或预检中再维护冲突的缺省规则；不新增公共命令、通用来源框架或改变 facts 权威验证。
   - **声明层。** 区分无该 key 记录、相关记录非对象（不可比较）、字段未声明、明确空、明确路径；读取当前索引及正式关联输入，不能把坏记录当无记录。当前显式空不得从旧 pack/accepted projection 把旧路径补成当前声明或已选用来源；null 本身不是用户禁用探测的指令。
   - **候选位置层。** 独立按正常流程既有发现规则列出有限候选，不把“当前未选用/声明为空”当成“没有候选位置”。对有当前有效分析路径的论文，analyzer Step 6.7 固定探测 `<analysis_file>.facts.json`，即使索引 `facts_sidecar=null` 也必须保留该候选并观测；Step 6.5 的 `<analysis>.future_work.json` 读取及其既有补齐限制照旧。显式空不得取消这些已有固定位置；也不得为探测而用旧包路径掩盖当前分析路径删除。仅在无记录/未声明、且既有兼容规则允许时使用已确认的历史路径；无法确定当前候选集合则不可比较。
   - **观测层。** 对各相关 analysis/future_work/facts/pdf 载体的声明或固定候选位置记录 present、missing 或不可确定；候选不存在也保存规范路径及 missing 占位，present 沿用现有 stat guard/已得摘要，不新增全文件哈希或读取 PDF 正文。`stage2_artifact_guard_reason` 复核 missing→出现；no_path 表示当时没有可定位的声明路径；由同一解析入口核对当前正式输入是否新增声明路径或已有规则定义的固定候选，出现即走原 process。对没有当前声明、也不能按正式规则派生位置的孤立 PDF 文件，不猜位置、不扫描全目录；正式来源若出现应观测但无法比较的候选，不得当作“未变”。
   - **可选用与接受层。** 观测到文件不等于来源可用、更不等于已接受；沿用正常流程对成功资格及 facts schema/指纹/future_work join 的权威校验，不以路径、存在或 level 代替证据。正常成功处理把实际消费的来源及同规则观测到的候选状态，随 accepted pack 同次保存至既有 guards/有限投影，不能把旧预检投影当作新接受基线；展示刷新只核对并保留已相等的业务部分，不自行接受后来出现的文件。
   正常成功接受基线、preflight 与 lease 内复核必须使用同一声明/候选/观测规则及当前来源输入，后两者只读，不执行迁移、补齐或 facts 重认证。候选 missing→present、声明/路径删除换址、成功资格或 guard 变化，以及任何不可比较，按 §3.3.3/5 拒绝旧预检的展示刷新并交正常流程。索引两侧均不存在、持久来源完整可比较的既有兼容继续保留；旧基线若缺本规则必需的固定候选占位，不能省略后当作未变，走原 process。仅记录必要业务字段，generated_at、kb_entry_id 等管理字段不参与，纯展示 level 单列；不遍历无关目录、不建立认证系统。
3. **先判业务变化，再判展示变化。** 保留既有三态分流，runner 的 `STAGE2_DISPLAY_REFRESH_VERSION` 在本次产品修复时从历史值 `2` 推进为 `3`。缺字段或合法较小版本（含 `1`、`2`）只表示需要确认实际展示；不合法、超前或无法解释的版本仍走原 `process`。版本只属于 `cache.preflight` 的私有展示缓存，不进入事实、模型输入、业务指纹、`paper_digest`、resolved proof 或公开 schema。
   - preflight 在 `reuse_all` 前先核当前来源投影、成功资格、业务 inputs/guards 与完整接受基线。来源 key/type 集合、存在状态、路径、成功资格/业务字段、文件 guard 任一变化，或基线缺失/不完整、当前索引不可读、映射不明确，均走原 `process`，保留正常流程的有效分析复用；未知→fulltext 若伴新增分析或 facts 也必须 process。
   - 只有业务依据完整可比较且完全未变、差异仅为已记录 level 或合法旧展示版本时，才选择 `refresh_display`；二者都未变化才 `reuse_all`。旧版本即使 level 未变也须刷新。既有错误实现已写入 `2` 的包同样属于旧版，不能因旧 PASS 绑定仍合法而跳过恢复；若业务来源变化或不可比较，则先正常 process，再由普通 finalize 执行同一个展示接受步骤。
   - 不在 preflight 渲染正文或重建模型任务；两种 analyzer 继续消费现有三态。旧包缺可信引用信息不能从历史正文猜造，交原 Stage 2 数据准备。旧 validator 未通过不等于分析来源变化，但不能绕过既有合法性约束。
4. **两条入口各守业务边界，共用展示接受。** 普通 `cmd_stage2_finalize` 先完成原 facts、方向、模型结果、缓存及 preflight 检查，并由既有 canonical paper/source 入口构造当前候选包；`cmd_stage2_refresh_display` 先复核本次预检、同一 accepted pack、当前来源和 level，以 `Stage2PackRefineContext` 从已接受规范论文、方向、模型结果及可信引用构造候选包。随后两者都调用 §3.3.7 的同一内部实现，不在入口内保留另一套“比较→写入→validator→版本”算法。刷新不调用依赖完整 facts 的 metadata 构造器，不回读旧 `/tmp` facts，不重建历史 facts、不重签 resolved proof，也不接受后来出现的业务来源。
   普通 finalize 无论旧版本为当前、旧版、缺失或不可比较，无论是否有新模型任务，都用当前 renderer 实际生成候选正文后交共享步骤判断；不维护容易漏字段的免渲染白名单。`stage2_render_state` 可以保留为内部信息，但其相等、level 相等、任务数为零或版本已是当前值，都不能代替实际正文接受。确定性渲染不产生新分析、归属、时效或叙事模型任务。
5. **保持原写前保护和有限更新范围。** 刷新入口及取得既有 writer lease 后，按同一来源解析规则重读教授/pack/正文归属、业务来源、level、目标/Stage 1 状态与当前业务年份（当前实现为 `datetime.now().year`），确认和预检一致；不得复用 payload 年份冒充当前年份。跨年、输入或接受包漂移，均在写前零写入退出并要求重新预检。普通 finalize 保留其现有 facts、成员、来源和 preflight 绑定要求，不借共享展示步骤绕过业务核验。
   刷新只更新确有变化的 analysis_level、展示/缓存版本、渲染绑定及因这些字段实际受影响的 accepted_directions_sha256 等既有包完整性摘要；业务来源基线只保留已验证相等的部分。普通成功处理仍是新业务接受基线的 owner。两者保留 accepted assignment、未失效模型指纹、原始报告与人工文档保护；具体正文/validator/版本提交顺序只以 §3.3.7 为准。
6. **字段与旧数据。** `_CANONICAL_PAPER_FIELDS`、build_direction_pack、_canonical_record、fresh/reused/resolved records 与 pack-only context 保存级别，同 key 一致合并，当前正式来源不得被旧记录覆盖。在 runner 内集中当前 paper 的构造/更新入口，供 `build_direction_pack` 的正式成员与 relevant 两分支、`_canonical_record` 及 `_current_paper_record` 共用；从旧包取记录也必须经过当前字段更新。当前 `stage2_analysis_level(paper)` 的 null 是有效覆盖值，必须清除旧 fulltext/abstract，不能用 truthy fallback 保留旧级别。仍保持 schema 2、成员资格及引用许可，不新增另一套 paper 模型。`paper_digest` 及 resolve/freshness 模型摘要不加入 level、render version 或展示投影。旧包缺 level 可显示未确认；旧包若缺展示版本且业务基线完整可比较，按 §3.3.3 进入展示刷新核验，不因缺版本直接放行 reuse_all；旧包缺可比较业务基线走原 process，不从历史 Markdown/临时 facts 猜造基线。资料不足导致正常流程不能完成时真实报告停止，保留原数据，不强制所有坏旧包成功。只在受影响的下一次调用按上述分流更新，不批量迁移或为文档 SHA 重跑。


7. **r10：一个内部展示接受步骤，唯一当前执行算法。** owner 为 `contact_state.py` 的 Stage 2 runner/renderer。复用现有受管正文读写、包摘要与 validator 逻辑；不增加公共 API、持久证明字段或第二份 renderer。内部 helper 的名称和返回表示由实现者选择，但下列输入、结果及先后关系不可由两个入口分别实现或省略。

   **输入与输出。** 输入为：在各入口既有保护范围内读取的旧已接受包快照（首建为无旧包）、旧受管正文与其真实摘要/既有 render 绑定、原 validator 及旧包绑定有效性、当前已通过本入口业务检查的候选包与渲染上下文、该入口已确认的校验业务依据变化，以及既有写入决定。旧快照必须在覆盖或更新 ctx/包前取得，不得用当前题名/元数据回填旧侧；普通 finalize 的新业务基线和刷新已验证相等的业务基线分别由各自 owner 提供。成功结果是已确认的正文/实际摘要、正文是否实质变化、旧校验保留或失效的结论和可提交候选包；失败、需重预检或需人工决定均不是成功接受，也不能产生可发布的新展示版本。

   **接受顺序：**
   1. 保存上述旧快照并在任何文件写入前核清原受管正文及旧报告/正文/包绑定。区分“无旧包的新生成”“可比较受管旧正文”“需原人工决定或原错误处理的旧文件/绑定”；不能把读不到旧正文或无效绑定默认当作等价。这里记录的是旧绑定是否合法，不因后续写新正文而把旧合法认证误判为本来就失效。
   2. 从当前候选包及可信引用实际调用当前 renderer 生成完整候选正文。首次正常生成也走这一步。缺引用或无法渲染时，刷新沿用 `needs_refresh` 交正常处理，普通 finalize 沿用原数据/业务失败；均不得写成功版本、反解析旧 Markdown、猜题名或替换模型结果。
   3. 比较两份实际受管正文。先按已有 frontmatter 规则取 body，包装摘要不作可见正文；在 body 中仅对 renderer 固定顶部位置、结构与 `> <生成时间> ｜ 数据来源：` 格式相符的唯一生成标题，忽略其生成时间，完整保留 `数据来源：` 后统计与说明。其余正文全部原样比较，不按任意行的分隔符删除前缀，不作全局空白/标点/引用归一化；标题识别失败时保留该处差异。固定证据、作者原句、用户笔记中同名分隔符前后的文字都不能被忽略。只比较包摘要、统计、字段列表或 `stage2_render_state` 不足以判等。
   4. 无旧正文的正常首建或正文实质变化时，按原 `managed_write`／既有人工决定机制写候选正文并取得实际摘要；不能自动覆盖手改。等价时先确认在盘正文仍符合原受管摘要与归属保护，再保留 Markdown 原字节与真实摘要，不仅为了新时间戳、版本或包字段而重写。无法确认属于本次可写/可保留对象时，按原失败或人工决定路径退出，不假定接受成功。
   5. 根据步骤 1 的旧合法性、步骤 3 的实际正文变化和本入口已确认的业务变化处理 validator：正文实质变化，或普通处理确实改变其认证依据（如新模型业务结果、成员/引用/事实/叙事依据重建），旧认证正式失效，新业务正文可从第一轮开始，旧原始报告文件保留。仅展示字段变化但最终正文等价，且无其他认证依据变化时，只保留原本合法的记录、round、phase 与 pending 信息；级别互换但聚合等价、未展示字段或纯时间戳变化不得单独清轮次。无真实业务变化却旧绑定无效时沿用原证据错误处理；有真实变化而旧记录失效时也只能移除旧认证，绝不能改摘要把它恢复为 PASS。没有旧 validator 就不创建 PASS。
   6. 完成正文写入或受保护的等价保留、并确定上述 validator 结论后，才在内存候选包登记当前私有展示版本 `3`、实际正文摘要与必要缓存/完整性字段。`stage2_preflight_metadata` 只构造业务接受元数据，移除其无条件赋予当前展示版本的权限；两个入口都不能在共享接受步骤之前自行打新版本。仅对步骤 5 允许保留的旧记录，按最终候选包的既有摘要规则更新包绑定，正文绑定仍指向实际保留正文；禁止以重绑挽救无效旧记录。最后通过各入口原 `atomic_json` 等持久化路径提交接受包及原有配套状态，所存版本必须对应已经确认的在盘正文。

   **失败与持久化边界。** 所有可在写前判定的缺引用、输入漂移、旧绑定问题及人工冲突都先判定，沿用原有错误/`needs_refresh`/`needs_decision` surface；不增加统一原因码或新证明协议。写文件前退出保持零写入；若正文已写而后续 I/O 失败，明确为未完成，不承诺 Markdown、输入包和 freshness cache 跨文件原子回滚。不得另行补写成功版本或伪造通过；再次调用仍由既有摘要、绑定、来源守卫及人工保护发现不一致并处理，不直接 reuse。保留各入口现有 lease 范围与写入顺序的保护，不新建锁、journal、全局扫描或绕过冲突的修复器。

   **生命周期边界与旧数据恢复。** 上述共享接受用于普通 finalize 和仅展示刷新；正常 `stage2-refine-finalize` 仍属于既有一次 narrative 修订→第二轮校验，不因其正常正文变化重开第一轮，也不能靠再次普通 finalize 清除未变的轮次。发布修复时一次推进私有目标 2→3，借 §3.3.3 的下次调用懒刷新覆盖缺版本、1 和包括误标旧正文的 2；不批量迁移、不重跑无关模型、不重建 facts，不引入额外哈希证明。正文已等价的旧包只推进必要元数据并保留合法轮次；业务变化/不可比较的旧包走正常处理后接受，不能强制通过仅展示入口。

   **直接反例与预期。** 固定证据裸 `AAAA1111` 与可信链接仅在 ` ｜ 数据来源：作者论文` 前不同，必须认定正文变化；旧版（包括先前误标 2）的分析载体只改 mtime、内容和 level 未变而进入 process，允许复用原模型/方向结果，但普通 finalize 仍确认实际正文后才记 3；误标 2 且来源未变者因版本过时进入刷新，而非继续 reuse_all。这些是同一 U1 恢复链的代表性输入，不派生入口×版本×故障组合矩阵；测试影响与权限见 §4.9。

### 3.4 已完成的 PR93 固定入口兼容

r5 的入口对齐已在本轮基线中完成，历史[批准记录](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6248571193)及测试计划 §10 的整合/执行记录保留。Codex/OpenCode analyzer Step 2.6 与主 SKILL 的 `refresh_display` 分支均使用同目录 `scripts/contact_state`，原 `--professor-dir`、`--preflight-file`、payload 与返回消费保持不变。本轮七项不要求再次对齐、重装或重跑入口测试。

保留 PR93 薄入口向相邻 `contact_state.py` 原样转交参数的边界：runner 仍是唯一业务实现，非 Nix 直接 `.py` 调用能力与原解释器选择不变；不改 Nix/runtime/依赖、七入口清单，不新增 wrapper、fallback 或第二份业务正文。已整合 PR91 的位置解析、规范 papers、成员保护与 validator 生命周期继续保留。

## 4. 顺序、安全和替代方案

1. **当前范围。** 本次是 r10 完整执行计划候选的文档修订；当前产品仍是 §2.13 所核版本。实施前由计划审核者复核本轮受影响决定，不能把本计划的提交当作产品实现、测试通过或合并批准。实施者先核最新代码与本轮基线差异，保留已整合 PR91 的位置解析、摘要、轮次和成员保护及 §3.4 的固定入口。
2. **唯一实施顺序。** r7/r8 已有 A—D（canonical paper 更新、展示字段贯通、单一来源解析及固定引用出口）按 §3.1—3.3 保留，不要求重做或拆成额外提交。本轮在同一 runner 内完成以下相互依赖的改动后再交付：
   - 将实际正文比较收敛到 renderer 的唯一时间戳例外，按 §3.3.7 建立一份接受实现，保存旧快照/绑定后生成当前候选，区分正文变化与真实业务校验依据变化。
   - 普通 finalize 和展示刷新在各自业务检查之后调用它；删除入口内重复的接受算法与普通 finalize 的投影相等免生成捷径。`stage2_preflight_metadata` 不再自行登记展示成功，最终 stamp 与合法 validator 包绑定由接受结果驱动。
   - 同次产品修复将私有展示目标从 2 推至 3，保持 preflight 先业务、后展示的既有分流；不得只提交函数修补却仍用目标 2，也不得只升版本而未完成两条入口的共享接受。
   - 保持原 CLI、返回消费及两种 analyzer 三态交接；如已有说明引用具体旧私有版本，只作必要当前描述同步，不改公开 schema、模型任务、Nix 或安装入口。
3. **Owner 与替代方案。** runner 负责固定引用展示、真实文件接受和缓存标记，validator 负责原报告/轮次，source producer 负责事实。开放固定区给模型改写、删掉依据或屏蔽校验均不满足 U1。为两入口分别打补丁虽然改动局部，但会继续存在比较/失效/版本顺序分叉；选择共享接受步骤。只给普通 finalize 增加旧版本条件仍会漏掉既有误标 2 的包，且字段白名单会再次遗漏 renderer 的新内容；选择确定性实际渲染并将目标推至 3。增加新 hash/certification 字段或批量迁移也可识别旧产物，但引入多余状态和恢复成本，既有私有版本懒刷新已足够，故不采用。
4. **保留行为与禁止副作用。** 不新增并发锁、跨文件 journal 或认证框架；保留现有教授 lease、来源守卫、原子 JSON、managed_write 和人工决定。不同文件不是一个新增原子事务，失败语义按 §3.3.7。不得自动覆盖人工文档、改成员归属、重置用户选择、改变事实或公开 schema，不把未获接受的 resolved 结果带入包。
5. **关键不变量。** 写入当前展示版本必须意味着同一受管正文已被当前 renderer 实际确认；投影相等不等于正文接受；等价展示只能保留原本合法的校验；实质业务版本变化不能沿用旧 PASS；同一未修复报告和正常 narrative refine 都不能清两轮限制。旧包版本落后既不能自动通过，也不能单凭版本变化清轮数。
6. **代表性边界。** abstract 有分析文件仍不计 fulltext；OCR fulltext/facts unavailable 可计全文级；当前 null 覆盖旧 known level；成员级别互换但聚合等价不重绘/清轮次；来源缺失后出现、显式删除路径、无索引历史包与跨年仍由既有来源规则处理。当前正文比较另覆盖正文分隔符前的变化、普通 process 无新模型任务、已误标 2 的旧正文以及等价旧包恢复。上述仅解释冻结方案，不自动成为新增测试矩阵或过程留证要求。
7. **既有版本证据。** r7 A—D 的源码事实仍见 [`contact_state.py@e1e8e48`](https://github.com/ScholarWorkflow/professor-contact/blob/e1e8e48a0f4bee8e5d22acd61813dccd53ac9632/.apm/skills/professor-contact/scripts/contact_state.py)：L4982—5019、L5588—5614、L5901—5924（paper 构造）；L5067—5079、L5376—5436、L5959—5960、L6314—6353（展示）；L3590—3612、L3627—3723、L6194—6200、L6291—6297（来源）；L4796—4887（引用）。[Codex analyzer Step 6.5—7](https://github.com/ScholarWorkflow/professor-contact/blob/1422fa3224bf7f01dda20f5c91f202568504c3a1/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L359-L410) 支持固定候选探测与 index 空值可并存。当前新增决策映射见 §2.13—14；以上均是实现描述，不把 helper 名称、私有版本数字或状态表示升格为新产品 contract。
8. **历史状态与本轮复核边界。** 原 r8 §4.8 的“r6/r7 A—D 及展示分流仍待审、待实施”是当时交接说明，已由后续 r8 正式批准及实施记录取代，不再作为当前执行指令。r9 曾补第 11／12 项但未处理已误标 2 的恢复及分支接受职责统一；本版已合并取代该候选。未受影响的 U1/U5 来源、字段、固定区交源、成员归属、PR91/PR93 入口决定按实际影响引用原批准与结果；批准状态只属于相应正式审核记录，本作者不自行重写为 PASS。r10 的 P1 复核新增当前源码事实与恢复因果；P2 复核 shared runner/renderer owner；P3 复核实际正文、旧绑定、业务校验依据、旧 2 恢复与失败/两轮保护；P4 复核两入口、metadata、提交顺序和下次调用路径。
9. **当前交接及未完成项。** 下一负责人为计划审核者，审核此唯一 r10 候选及直接影响；批准后由产品实现负责人按 §4.2 修改 runner。本轮没有产品实现或测试结果。唯一测试计划已按用户授权修订为 t45 候选，在 t44 原两条 T4 正式路径内对齐目标 `3` 与已误标 `2` 的旧包恢复；文档对齐已完成，设计及第二关受影响步骤/接线仍待审核，测试准备与第三关执行未完成。旧包输入、业务观察及既有等价/轮次记录的实际影响复用见测试计划 §2.1／§3.3；不新增入口×版本矩阵或第三套验证，本执行计划不定义新 Case ID、断言、命令、采集器或测试门槛。r10 初次编写未修改测试计划是历史记录，不再表示当前对齐待处理。原有效结果只复用未受影响部分；独立审核与实际产品/测试完成状态分别记录，均不能外推为合并批准。
