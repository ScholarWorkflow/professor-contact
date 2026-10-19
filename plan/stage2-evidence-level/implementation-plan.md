# Stage 2 固定证据展示、失败登记与分析级别修复

- Requirement revision：2026-10-17 用户要求为此前 U1、U5 两项修复建立独立计划 PR（北京时间）；依据用户提供的《PR91未覆盖问题报告_20261016.md》。报告中的私人实际数据与失败次数不是本计划已复验结果。
- Plan revision：contact-evidence-level-r9；Proposed review status: pending（2026-10-19，补齐两条已有 U1 展示规则的关键实现步骤：时间戳比较范围和普通 finalize 的旧版本重绘顺序）。r8 已在[正式计划审核](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6260927099)获批；r9 为当前唯一待审完整候选，不能继承 r8 的批准状态。
- 目标：ScholarWorkflow/professor-contact。U1/U5 原产品基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`；第 7 版修复及既有三处源码修正见[交付记录](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6260319513)。第 8 版展示分流已在产品提交 `5582dfa` 实施，测试计划 t43 的现有 25 个选择器在其记录版本上通过。本版依据 PR #92 变基前受审提交 `aae1d54ca5065b907c794557c772d2753695de6d` 及变基后同一业务行为的提交 `d69d9938456a05330df30033200887cd974da8ac` 的生产源码，以及 2026-10-19 用户要求，只补正文比较与正常处理的两项关键决定；其他已批准 U1/U5 目标、成员归属、写入边界及 PR91/PR93 集成不变。代码与测试未因本次计划编写而修复或执行；r9 与配套 t44 均待受影响关口复核。
- 唯一测试计划：[test-plan.md](test-plan.md)。按 [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)执行。

## 1. 范围与验收目标

U1：固定证据卡正文不泄漏内部论文编号；真实文字阻挡必须能登记，说明处理归属，不能因模型无权改事实而连失败也无法记录。作者原句、译文、出处、时效结论、署名、用户笔记与红线不得被文字修订改写。

U5：全文/摘要统计取实际成功分析的级别，不能用分析文件存在或 PDF 存在代替。级别缺失、失败或不明不能自动冒充全文或摘要。

不包含 U2/U4 分句、U3 跨页 sidecar、成员归属重构、Stage 3—5、新 Nix 安装、全教授业务重跑、额外去重统计。遵守 [Nix 单源边界](https://app.notion.com/p/3fb0101a85f38185b17adb417590e50e)：改正式业务源，不在安装产物或 Nix 层补另一套业务实现。

[PR91](https://github.com/ScholarWorkflow/professor-contact/pull/91) 当前 `b0991da8e0b0f9456acbcdd79dece96c53164dec` 的执行 r3 / test-r3 处理另外三项缺陷，本 PR 不复制它的全套修复与测试。两者若先后落地，只合并重叠的记录器/普通 finalize 生命周期改动；PR91 的“不可修订区域拒绝”在本 PR 的新授权范围内改为“允许记录、禁止模型改写”。不存在必须等待 PR91 全部业务完成的依赖。

## 2. 决策依据（当前源码事实，不替代需求）

下列行号均对应上述基线的 [contact_state.py](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py)。

1. 展示归 runner：L4042–4055 接受非空 model_evidence，L4286–4293 带入 gap，L4481–4518 原样写固定卡 evidence/completed_part/remaining_gap 及禁锚区 evidence；因此模型合法机器结果中的 item key 可泄漏。既有 `redact_item_keys`（L4236–4243）可作局部复用，但其未知编号替换不能冒充已核验引用。
2. 登记与修订权限是两回事：`stage2_validation_report` L10716–10989 已做报告/正文/方向绑定；L10980–10984 把不属于 narrative 的 blocking 拒绝。`stage2_require_recorded_validation` L10992 起又要求先登记，所以固定区阻挡没有处理路径。
3. 仍可保持 fail closed：`stage2_validator_accepts` L3609–3654 仅接受有效绑定的 terminal pass/skipped；`stage2-refine-plan/finalize` L11088–11243 是唯一 narrative 修订入口。新增失败记录不能使通过门槛放宽。
4. 实际分析级别已存在于 Stage 2 写入的索引：Codex analyzer [L339–380](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L339-L380) 明确成功的 pdf/ocr 路由为 fulltext、abstract_json 为 abstract。它的 [L405–430](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L405-L430) facts 示例漏传级别；runner L4323–4334、L4720–4740 规范记录也未保存级别，L4384–4386 错用文件/PDF存在计数。
5. 已有分析级别与 facts 可用性不同：analyzer L263–274 允许 OCR-only fulltext 分析而 facts unavailable。不能用 facts_state 反推分析级别。
6. analyzer 的 [Step 2.6 L142–159](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L142-L159) 在 reuse_all 时不进入 facts 准备或 finalize；因此仅在 finalize 比较 level 或增加渲染版本，无法发现同版本下成功分析索引的级别变化。
7. `Stage2PackRefineContext` L1707–1765 已提供临时 facts 过期后的持久包展示上下文，但它不是完整业务 facts；普通 finalize 仍依赖 facts，不能将该上下文伪装成 facts 重验/重签旧 resolved 结果。
8. preflight cheap inputs L3352–3381 不读取分析索引，`_artifact_guards_for_keys` L3411–3444 只登记已有路径且已存在的文件；现状不能仅凭“旧 guards 未变”排除新增分析/sidecar 或索引换址，不能直接据此批准仅展示刷新。
9. 普通 finalize L5020–5080 可能不重绘、继承旧 validator；升级展示和级别后必须只使受影响生成物失效，不能重新绑定旧 PASS。PR91 §3.4.1 已设计实质变化/等价重写区分，可复用同一实现，不另建历史系统。
10. 展示版本比较缺口（当前代码事实）：`STAGE2_DISPLAY_REFRESH_VERSION` 当前为 `1`，成功刷新才写入 `cache.preflight.display_refresh_version`；正常成功接受基线的 `stage2_preflight_metadata` 未持久保存它，预检只在 `level_changes` 非空时选择 `refresh_display`，而刷新入口对空 `level_changes` 直接拒绝。因此已接受包即使业务来源与级别都未变，仍可能因旧展示规则留下原始论文编号而被 `reuse_all` 沿用。对应[版本常量](https://github.com/ScholarWorkflow/professor-contact/blob/9505081d14a0e4a02627fed0a530b0e7c4c4db64/.apm/skills/professor-contact/scripts/contact_state.py#L127-L140)、[基线生成](https://github.com/ScholarWorkflow/professor-contact/blob/9505081d14a0e4a02627fed0a530b0e7c4c4db64/.apm/skills/professor-contact/scripts/contact_state.py#L4019-L4099)、[预检分流](https://github.com/ScholarWorkflow/professor-contact/blob/9505081d14a0e4a02627fed0a530b0e7c4c4db64/.apm/skills/professor-contact/scripts/contact_state.py#L4428-L4445)、[刷新入口](https://github.com/ScholarWorkflow/professor-contact/blob/9505081d14a0e4a02627fed0a530b0e7c4c4db64/.apm/skills/professor-contact/scripts/contact_state.py#L6529-L6543)。本项为已确认 U1 的旧包适配事实，不把私有版本号升级成产品契约。

11. **r9 新确认的正文比较事实（描述证据）**：[`contact_state.py@aae1d54` L6502—6514](https://github.com/ScholarWorkflow/professor-contact/blob/aae1d54ca5065b907c794557c772d2753695de6d/.apm/skills/professor-contact/scripts/contact_state.py#L6502-L6514) 的 `stage2_visible_body()` 对正文每一行查找 ` ｜ 数据来源：`，并舍弃此前全部文字；而同一 runner 的 `render_analysis_md()` 既生成唯一的报告顶部数据来源行，也会打印来源数据中的固定卡 evidence 文本。旧行 `- 后续论文依据：AAAA1111 ｜ 数据来源：作者论文` 与新行 `- 后续论文依据：[可信题名](zotero://select/library/items/AAAA1111) ｜ 数据来源：作者论文` 会被该比较错误视为相等，实际 U1 转换得不到写入，旧校验可能被保留。变基后同一问题仍存在于 [`contact_state.py@d69d993` L6479—6491](https://github.com/ScholarWorkflow/professor-contact/blob/d69d9938456a05330df30033200887cd974da8ac/.apm/skills/professor-contact/scripts/contact_state.py#L6479-L6491)。正式要求依据为 §1 的 U1 和 §3.3.5 的正文实质变化判断。
12. **r9 新确认的普通路径事实（描述证据）**：[`contact_state.py@aae1d54` L6281—6288](https://github.com/ScholarWorkflow/professor-contact/blob/aae1d54ca5065b907c794557c772d2753695de6d/.apm/skills/professor-contact/scripts/contact_state.py#L6281-L6288) 仅按模型任务、新包或 `stage2_render_state` 差异选择正常 finalize 的重绘；[`L6331—6338`](https://github.com/ScholarWorkflow/professor-contact/blob/aae1d54ca5065b907c794557c772d2753695de6d/.apm/skills/professor-contact/scripts/contact_state.py#L6331-L6338) 调用的 [`stage2_preflight_metadata` L4133—4138](https://github.com/ScholarWorkflow/professor-contact/blob/aae1d54ca5065b907c794557c772d2753695de6d/.apm/skills/professor-contact/scripts/contact_state.py#L4133-L4138) 直接登记新展示版本。旧包即使因文件保护变化走正常 `process`，只要模型及展示状态可复用，就可能保留含原始编号的旧 Markdown，却登记版本 `2` 并沿用旧校验。正式要求依据为 §1 的 U1、§3.2 和 §3.3.3—5；变基后同一分支仍见 [`contact_state.py@d69d993` L6258—6265](https://github.com/ScholarWorkflow/professor-contact/blob/d69d9938456a05330df30033200887cd974da8ac/.apm/skills/professor-contact/scripts/contact_state.py#L6258-L6265) 与 [`L4110—4115`](https://github.com/ScholarWorkflow/professor-contact/blob/d69d9938456a05330df30033200887cd974da8ac/.apm/skills/professor-contact/scripts/contact_state.py#L4110-L4115)；需要冻结成功登记版本前的正文校验顺序。

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
3. **先判业务变化，再判展示变化（包括私有渲染版本）。** runner 用既有 `STAGE2_DISPLAY_REFRESH_VERSION` 表示固定证据引用和统计的展示规则版本；本轮目标值为 `2`，以区分此前可能已接受的 `1` 与未登记版本的旧正文。正常 Stage 2 finalize 成功接受输入包，以及受保护展示刷新成功时，都在现有 `cache.preflight.display_refresh_version` 写当前值；版本只属于私有展示缓存，不进入事实、模型输入、业务指纹、`paper_digest`、resolved proof 或公开 schema。preflight 在 `reuse_all` 前将已接受版本与当前版本比较：缺字段或有效的较小版本只说明“需用当前渲染器确认展示”；不合法、超前或无法解释的版本视为不可比较，走原 `process`，不借版本变化接受旧认证。先核本次来源投影、成功资格、业务 inputs/guards 与完整已接受基线：来源 key/type 集合、存在状态、路径、成功资格/业务字段、文件 guard 任一变化，或旧业务基线缺失/不完整、当前索引不可读、映射不明确，均走原 `process` 并保留正常流程的有效分析复用；未知→fulltext 若伴新增分析或 facts 也必须 process。只有业务依据完整可比较且完全未变、差异仅在已记录 level 或有效旧展示版本时，才选择 `refresh_display`；两者都未变化才 `reuse_all`。即使 level 没变，只要展示版本过时且业务基线有效，仍须进入受保护展示刷新，避免旧 U1 编号正文被直接沿用。旧包缺可信展示引用信息，不能凭历史正文补齐，须回原 Stage 2 数据准备/正常处理。两种 analyzer 同步消费既有三态分流，不新增模型任务；旧 validator 未通过本身不算分析来源变化，但不绕过现有校验合法性约束。
4. **仅展示的正式入口。** 在既有 runner 复用 `Stage2PackRefineContext`、renderer、教授 lease/原子 JSON 与 managed_write，读取已接受 pack 的规范论文、方向、模型结果和引用元数据，以及本次只读索引/预检投影。不依赖旧 /tmp facts，不重建完整历史 facts，不重签旧 resolved proof。只更新确有变化的 analysis_level、展示/缓存版本与渲染绑定，并同步因这些字段实际受影响的 accepted_directions_sha256 等包完整性摘要，避免下次误报 pack_integrity_mismatch；不调用依赖完整 facts 的 stage2_preflight_metadata 伪造接受元数据。保留 accepted assignment、事实判断、叙事、freshness 结果和模型指纹；不产生新分析/归属/时效任务。因展示版本差异进入时，即使 `level_changes` 为空，入口也必须接受合法的 `refresh_display` 决定；在既有 writer lease 内读取当前接受版本、同口径业务来源及受管正文，确认与预检决定相符后，使用持久可信元数据实际生成当前候选正文，不得仅凭两个同级别包的 `stage2_render_state` 相等就跳过重绘。候选内容缺可信引用或已接受基线不能比较时返回正常 `process` / `needs_refresh`，零写入；不得反向解析旧 Markdown 或猜题名。成功刷新不能把业务变化的当前来源冒充新的接受基线；业务来源基线仅由正常处理成功建立，展示刷新只保留已验证相等的业务部分并推进展示部分。
5. **写前再核同一输入。** 沿用教授/pack/正文归属、受管摘要和输入漂移检查，重新读取与预检相同的业务来源及 level 投影，确认仍为该 accepted pack、相同业务基线和本轮 level；刷新入口及取得既有 writer lease 后、写入前，都重新读取与正常预检同口径的当前业务年份（当前实现为 `datetime.now().year`），与 payload 年份比较，不复用 payload 年份冒充当前年份。跨年或任一漂移均零写入并要求重新预检，由新预检决定后续分流。手改正文按 managed_write 保护。正常 finalize 与展示刷新共用 renderer 拥有的实际展示语义：比较最终可见内容（包括正式成员聚合计数、实际引用题名等），排除生成时间及非实质受管包装；不比较全 `papers` 或逐论文 level 作为重绘充分条件。旧侧使用已接受快照，不能用当前 ctx 的题名/元数据回填旧快照掩盖变化；新侧使用当前规范记录。仅未展示字段变化，或成员级别交换但最终可见内容/统计等价时，保持正文和校验轮次。由私有展示版本差异触发时，必须用当前 renderer 生成的候选可见正文与原受管正文在既有保护下比较，排除生成时间及非实质包装；即使 level 和包的可见状态投影相同，也不能跳过这次比较。候选正文实质变化才写受管正文、按 §3.2 使旧 validator 失效并从新正文开始合法校验；候选正文等价则不重写 Markdown，只推进展示版本和必要的包摘要/绑定，保留原本合法的 validator 与轮次，已失效记录不能借版本更新重新取得通过。展示等价不替代旧报告/正文/包绑定合法性检查：只允许保留本来合法的记录，不能修复或洗白旧失效认证；正常 narrative refine 仍保留既有两轮生命周期。不新增锁、journal 或认证框架。
6. **字段与旧数据。** `_CANONICAL_PAPER_FIELDS`、build_direction_pack、_canonical_record、fresh/reused/resolved records 与 pack-only context 保存级别，同 key 一致合并，当前正式来源不得被旧记录覆盖。在 runner 内集中当前 paper 的构造/更新入口，供 `build_direction_pack` 的正式成员与 relevant 两分支、`_canonical_record` 及 `_current_paper_record` 共用；从旧包取记录也必须经过当前字段更新。当前 `stage2_analysis_level(paper)` 的 null 是有效覆盖值，必须清除旧 fulltext/abstract，不能用 truthy fallback 保留旧级别。仍保持 schema 2、成员资格及引用许可，不新增另一套 paper 模型。`paper_digest` 及 resolve/freshness 模型摘要不加入 level、render version 或展示投影。旧包缺 level 可显示未确认；旧包若缺展示版本且业务基线完整可比较，按 §3.3.3 进入展示刷新核验，不因缺版本直接放行 reuse_all；旧包缺可比较业务基线走原 process，不从历史 Markdown/临时 facts 猜造基线。资料不足导致正常流程不能完成时真实报告停止，保留原数据，不强制所有坏旧包成功。只在受影响的下一次调用按上述分流更新，不批量迁移或为文档 SHA 重跑。


7. **r9：统一实际正文比较与展示版本接受顺序（补足 §3.3.3—5 的实现决定）。** 由现有 `contact_state.py` 的 renderer、普通 `cmd_stage2_finalize` 和 `cmd_stage2_refresh_display` 负责；不改 Stage 2 以外的 owner，不新增第二种展示实现。
   - **可见正文比较的精确定义**：仅在报告顶部 renderer 固定生成的**唯一数据来源标题行**，确认位置和 `> <生成时间> ｜ 数据来源：` 格式后，忽略其中的生成时间，保留该行 `数据来源：` 起的完整统计内容。其余行保持原文参加比较；正文中的 ` ｜ 数据来源：`、已知论文编号、可信题名/链接、作者原句和用户笔记都不能被统一截断或删除。无法识别为该唯一生成标题的行不得消除差异。正式接受条件是两份实际受管正文在只忽略这一个生成时间后内容相同；只比较包摘要、方向统计或局部片段不足以判等。
   - **两条正式入口复用同一个比较规则**：展示刷新仍通过当前 renderer 生成候选正文，与在盘旧受管正文比较；当固定证据前缀从裸 `AAAA1111` 变为可信论文链接，即使后缀恰为 ` ｜ 数据来源：作者论文`，也必须认定有实质变化。正文未变时既有合法校验轮次保留；正文变更时使用原 `managed_write` 写入并失效旧 `validator`，原始报告文件不改。禁止通过弱化校验或只改包内展示版本来掩盖差异。
   - **普通 finalize 先判旧展示版本，再决定是否可跳过重绘**：读取原已接受包的 `cache.preflight.display_refresh_version` 与对应在盘受管正文/旧绑定，判定其为当前、有效旧版/缺失、或不可比较。完成正常 Stage 2 原有 facts、方向、缓存和模型结果复用后，构造当前候选包。若原展示版本为旧版、缺失或不可比较，即使 `needed_keys` 为空、旧新 `stage2_render_state` 相等，仍必须从**当前可信引用与当前 renderer**生成完整候选正文并与旧受管正文比较；不能只凭业务重处理完成就认为旧展示已升级。原展示版本有效且当前、且无现有重绘触发条件时，才允许沿用当前已认证正文，不重复生成模型任务。因业务来源变化而进入原 `process` 的路径同样执行此判定，不强制改走仅展示刷新。
   - **比较结果决定提交和旧校验**：候选正文缺可信引用、旧正文/绑定不可核实或 `managed_write` 发现手改时，沿用原失败/人工决定规则，受影响状态不得被标为已成功升级。候选正文与旧正文有实质差异时，先按原写入保护生成新受管正文并使旧 `validator` 失效，重新校验从第一轮开始；候选正文等价时不重写受管 Markdown，只按既有绑定规则保留原本合法的校验与轮次，不能用新摘要重新激活失效的旧记录。普通业务流程仍保留自身既有的输入、成员与失败要求，不能为了保持旧校验而忽略真实业务变更。
   - **新版本只在接受成功后记录**：正常 finalize 和受保护的展示刷新，仅在上述候选正文生成/比较、写入保护及校验处理完成后，才可把 `cache.preflight.display_refresh_version` 登记为 `STAGE2_DISPLAY_REFRESH_VERSION`（当前值 `2`）。写入新版本后必须真实对应磁盘上已按当前规则确认的正文；不能出现“正文未重绘、版本却升级”的状态。展示版本仍不进入业务事实、模型输入、`paper_digest`、resolved proof 或对外 schema；不回读历史 `/tmp` facts，不增加新的锁或文件。
   - **直接反例及影响**：① 旧版正文的固定证据恰含 ` ｜ 数据来源：`，换成可信链接后前缀变化须被发现；② 已接受旧版本在分析载体仅修改时间、内容和 level 未变时被来源 guard 判为 `process`，模型/方向结果可复用，普通 finalize 仍必须更新旧展示、失效旧校验后才记新版本。未受影响的既有 t43 等价展示刷新、成员交换后统计等价、旧报告留存与两轮上限行为继续保留。这两个反例属于已确认 U1 的直接生产路径，所需测试只由配套测试计划 T4 制定。

### 3.4 已完成的 PR93 固定入口兼容

r5 的入口对齐已在本轮基线中完成，历史[批准记录](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6248571193)及测试计划 §10 的整合/执行记录保留。Codex/OpenCode analyzer Step 2.6 与主 SKILL 的 `refresh_display` 分支均使用同目录 `scripts/contact_state`，原 `--professor-dir`、`--preflight-file`、payload 与返回消费保持不变。本轮七项不要求再次对齐、重装或重跑入口测试。

保留 PR93 薄入口向相邻 `contact_state.py` 原样转交参数的边界：runner 仍是唯一业务实现，非 Nix 直接 `.py` 调用能力与原解释器选择不变；不改 Nix/runtime/依赖、七入口清单，不新增 wrapper、fallback 或第二份业务正文。已整合 PR91 的位置解析、规范 papers、成员保护与 validator 生命周期继续保留。

## 4. 顺序、安全和替代方案

1. 实现者先核最新基线及 PR91 是否已落地，保留其位置解析/摘要/轮次/成员保护；只整合本计划涉及的交接。
2. 已实施的 r7/r8 A—D 保留原语义；本轮只修订 `contact_state.py` 中 r9 两处实现，不要求把 A—D 重新实施或拆成独立提交：
   - A（问题 1/2）：按 §3.3.6 合并当前 paper 构造/更新职责，贯通新增正式成员及复用记录的当前级别，含 null 覆盖。
   - B（问题 3，依赖 A）：按 §3.3.3—5 由 runner 在正常 finalize 与刷新中保存目标私有展示版本，并由 renderer 给出共享展示比较语义；同级别旧包可因版本差异走刷新，按实际可见正文变化判定是否失效旧 validator，不以版本变化自动清轮次。
   - C（问题 4/5/7，依赖 B 的版本定义）：按 §3.3.2—5 建立统一来源解析入口，preflight 在已确认业务来源未变后才比较 level 与展示版本；修正 missing/no_path/显式空/坏记录与两处当前年份复核，保留旧无索引兼容和既有 lease。
   - D（问题 6）：按 §3.1 在固定 evidence 引用收集与展示出口完成兼容修复，保留可信已有链接及非引用文本。
   - E（本轮 r9，依赖既有 B 的展示版本）：按 §3.3.7 在 `stage2_visible_body` 限定只忽略真实生成标题时间，并在 `cmd_stage2_finalize` 以旧展示版本为条件强制当前 renderer 的候选正文比较；在确认写入、旧认证处理完成后才登记新版本。展示刷新调用同一比较规则，原模型任务、人工写入保护和两轮限制不变。
3. 替代方案“开放所有固定区给模型改写”会改事实，排除；“只屏蔽校验或直接删除依据”掩盖缺陷，排除；选定方案在 runner 确定性展示、记录器保留失败，原 owner 处理问题。
4. 不新增并发锁或跨文件 journal，沿用已有教授写入 lease、原子 JSON 和 managed_write 保护；不自动覆盖人工文档、不重置用户选择、不改变成员归属。
5. 关键反例：abstract 有分析文件仍不能计 fulltext；OCR fulltext facts unavailable 仍可计全文输入级；旧包无级别应显式未知；固定+叙事混合阻挡不允许模型越权；同一未修复报告不能清轮数；正常 narrative 修订不应重开第一轮。
6. 现实替代是给各分支分别补字段、另写刷新专用 level 比较及正则替换；这样容易再次漏分支、误清轮次或破坏已有链接，因此选择复用上述职责各自的内部入口，而非新增公共 API/框架。代表性反例包括完整业务基线下 level 未变但已接受展示版本为 1 或缺失、版本过时却错误 reuse_all、版本升级后可见正文未变而校验轮次被清零、旧 known→当前 null、成员级别交换但聚合未变、仅相关论文级别改变、旧快照题名与当前题名不同、missing 文件出现、显式删除路径、无索引历史包、跨年等待 lease 和 evidence 已带合法链接；这些只用于解释方案边界，不自动转成新增测试矩阵。
7. 版本化依据：本轮 [contact_state.py](https://github.com/ScholarWorkflow/professor-contact/blob/e1e8e48a0f4bee8e5d22acd61813dccd53ac9632/.apm/skills/professor-contact/scripts/contact_state.py) 的 L4982—5019、L5588—5614、L5901—5924 对应 A；L5067—5079、L5376—5436、L5959—5960、L6314—6353 对应 B；L3590—3612、L3627—3723、L6194—6200、L6291—6297 对应 C；L4796—4887 对应 D。上述为实现现状证据，正式目标仍为 §1 U1/U5；内部 helper 名称、状态布局与比较表示不升级为新 contract。
来源发现依据：[Codex analyzer Step 6.5—7](https://github.com/ScholarWorkflow/professor-contact/blob/1422fa3224bf7f01dda20f5c91f202568504c3a1/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L359-L410) 明确固定候选探测与 index 空值可并存；该事实纠正 r6 的缺省解释，不赋予新来源或跳过验证的权限。
8. r8 本轮请求复核两组仍待审的直接影响：① r6/r7 的七项 A—D 修复方案及统一来源 owner（P1 的版本化源码事实、P2 的 paper 构造/renderer/来源归属、P3 的固定候选/旧基线和失败保护、P4 的单一来源入口及顺序）；② 本次补充的 U1 旧正文展示版本分流（P1 的当前只写未读事实、P2 的 runner/renderer owner、P3 的旧包与 validator 安全条件、P4 的正常成功写版本→预检分流→取得 lease 后重核→候选正文比较）。`no_path` 说明只澄清正式有限来源的观测边界，不扩大 PDF 搜索或测试范围。r4/r5 未受影响的固定区交源、成员归属、入口兼容结论按影响分析复用；r6/r7 的 pending 不由本计划作者升格为 PASS。下一负责人为计划审核者；批准后由产品实现者仅落实尚未实施的展示版本处理，测试负责人依据已批准 U1/U5 与 Test Engineer Rule 判断现有 T1/T4 记录的适用性，不由本计划新增 Case ID、断言或测试设施。本轮只改唯一执行计划，不执行产品和测试，也不授予合并批准。
9. **r9 修订影响与交接**：本轮用户要求补足执行细节和漏测输入，属于已确认 U1 的两项实现决定收紧，不增加业务需求。规范依据仍为 §1、§3.2、§3.3.3—5；新增描述事实见 §2 第 11／12 项；具体责任和实施顺序见 §3.3.7 与本节 E。P1 仅核新增源码事实与版本，P2 核 runner/renderer owner 及正常入口实际生效，P3 核前缀差异、旧校验/受管保护与等价保留，P4 核正常 finalize 与 refresh_display 的先后条件；r8 其他已通过决定可按无影响记录沿用，不从 `APPROVED` 推定 r9 获批。配套测试计划仅修 T4 的两项直接受影响输入，现有成功记录继续按各自版本使用。实施负责人修正产品，测试工程师按 t44 受影响步骤准备与执行，审核者复核修订后的必要关口。


