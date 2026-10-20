# Stage 2 U1：固定证据展示与真实阻挡归属

- Plan revision：`stage2-u1-r3`（2026-10-20）；Proposed review status: pending。
- 唯一目标路径：`plan/stage2-fixed-evidence/implementation-plan.md`。本轮交执行计划与同目录 [测试计划](test-plan.md)；计划编写时未实施、未运行测试，不沿用 #92 的批准或测试状态作为本计划通过结论。产品实施与执行记录见文末交付状态。
- Requirement revision：2026-10-17 已确认 U1，2026-10-19 用户明确要求总结 #92 至今经验，将 U1/U5 分成两个 PR 从头设计；保持 main 行为先完成 Stage 2 模块拆分，再分别修复。2026-10-20 用户授权开始 U1/U5 两个计划；本轮完成拆分后设计落点更新，仍仅计划，不实施。
- Repository baseline：`ScholarWorkflow/professor-contact@879982abe1d7d811bd9d014c03dce4f5912cc64f`，2026-10-20 13:09 UTC 读取最新 main（#117）。PR107 原计划 head 为 `86da1d4b59ea4b59a95b0b5449b4531d192ccfd3`、版本 r2；本 r3 是其完整替代候选，不继承旧计划审核结论作为本轮自授状态。#92 `10324b8f10ff84080e9f7132bef807926de23279` 的 r11/t47 仅作历史教训，不移植补丁或扩张旧测试矩阵。
- Stage 2 行为保持拆分已落地，原“等待拆分并再找模块”前提已解除。下面直接冻结当前实际模块、入口和共享接点；Stage 3 后续拆分不属于 U1 前置。
- 规则：[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)（2026-10-19 14:02 UTC）、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)（2026-10-09 20:13 UTC）、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)（2026-10-09 20:37 UTC），2026-10-20 本轮重新读取，正文未变。

## 1. 正式目标、保留行为与非目标

### 正式目标

1. 固定卡 `evidence/completed_part/remaining_gap` 及禁锚区 `evidence` 的人读出口，把有可信依据的论文引用显示为题名与 Zotero 链接；内部 key 可留在机器字段和链接目标。只等价转换引用，不改证据含义、不删整段依据。
2. 合法固定卡文字 blocking 能按原始校验报告登记并说明源数据/生成器责任；不能因模型无权改事实而连失败也登记不了。登记不等于允许模型修改。
3. 真实固定 blocking（包含与 narrative 混合的报告）停止自动文字修订循环，交实际 owner。纯 narrative 仍保持现有一次修订、第二次校验的两轮上限。
4. 已有旧报告在下一次正常 Stage 2 使用时也适用修复；不能只修新建包。正文、机器头、输入依据、既有校验状态分别处理。

### 保留与禁止副作用

保留报告合法的正整数行号、短字符串 location（长度不超过 20）、原始 issues/notes/verdict、quote 唯一定位、教授和方向归属、正文与包绑定、人工修改保护、成员/引用许可和来源守卫。保留作者原句、译文、出处、署名、freshness 结论、用户笔记、红线及机器证据原文。笔记、论文一览等原来跳过区域继续不作为可校验固定卡。

不改上游 style-validator schema/文字标准，不屏蔽固定卡，不放宽通过门槛，不扩 Stage 3—5、不增加同名支持、不重构成员归属、不实现 U5 分析级别统计、不移植 #92 的索引刷新大方案、不重签 resolved 决定、不建通用迁移/认证/事务框架。两份计划共享文件不等于互为业务前置。

下文 owner map、私有展示标记、内部接受步骤是实现决定，不升级为外部产品契约或额外测试义务。

## 2. 当前事实与决策映射

以下事实来自本轮逐模块读取，路径与行号均固定到上述 main。拆分不是新需求，原 r2 的方案决定仍须由这些真实调用点支撑。

- **展示 owner**：[\_stage2_render.py](https://github.com/ScholarWorkflow/professor-contact/blob/879982abe1d7d811bd9d014c03dce4f5912cc64f/.apm/skills/professor-contact/scripts/_stage2_render.py) 的 `build_direction_pack`、`render_analysis_md`、`stage2_trusted_paper_title`/`stage2_require_later_paper_titles`。四目标字段仍直接写入 Markdown；禁锚条目只持久 `completed_by_item_key`，未持久完整候选；`redact_item_keys` 的泛八位清洗不适合作论文引用 authority。决定：四出口有限转换及生成时归属在该模块实现，不把格式化放到事实 loader。
- **事实与恢复 owner**：[\_stage2_facts.py](https://github.com/ScholarWorkflow/professor-contact/blob/879982abe1d7d811bd9d014c03dce4f5912cc64f/.apm/skills/professor-contact/scripts/_stage2_facts.py#L430) 的 `Stage2Context` 负责当前事实及 freshness；`freshness_entry` L538 以 gap/candidate 指纹和状态确认 cache 可复用。`Stage2PackRefineContext` L596 从持久 canonical papers/方向恢复 refine，不需要旧临时 facts。决定：缺失的引用元数据由正常 finalize 收齐；旧禁锚只使用仍有效的已有 cache 补齐，不猜自然语言。
- **规范包 owner**：[\_contact_pack.py](https://github.com/ScholarWorkflow/professor-contact/blob/879982abe1d7d811bd9d014c03dce4f5912cc64f/.apm/skills/professor-contact/scripts/_contact_pack.py#L35) 的 `_canonical_paper_record`、`_merge_canonical_paper`、`normalize_input_pack`/`load_input_pack` 已从 runner 移出；canonical 字段白名单仍由 [runner 常量与工厂接线](https://github.com/ScholarWorkflow/professor-contact/blob/879982abe1d7d811bd9d014c03dce4f5912cc64f/.apm/skills/professor-contact/scripts/contact_state.py#L380) 注入。决定：复用现有 papers 结构和冲突守卫；本 U1 不增加新的 paper schema 字段或 U5 analysis_level。新增引用记录不能扩大成员或 P/L 许可。
- **预检 owner**：[\_stage2_preflight.py](https://github.com/ScholarWorkflow/professor-contact/blob/879982abe1d7d811bd9d014c03dce4f5912cc64f/.apm/skills/professor-contact/scripts/_stage2_preflight.py#L580) 的 `cmd_stage2_preflight` 仍只有 reuse_all/process；`stage2_preflight_metadata` L444 由正常 finalize 调用。决定：缺 U1 完成标记走 process，但不改变分析/freshness 指纹，不制造额外模型工作。
- **正常接受 owner**：[\_stage2_finalize.py](https://github.com/ScholarWorkflow/professor-contact/blob/879982abe1d7d811bd9d014c03dce4f5912cc64f/.apm/skills/professor-contact/scripts/_stage2_finalize.py#L275) 的 `cmd_stage2_finalize` L376 仍把 old_entry 原对象放入候选并改 collection_key；L758 用 render_state 投影决定是否实际渲染，L781 重建 cache.render，L823 才检查旧 validator。决定：旧快照先隔离，实际候选先生成，校验/冲突先判断后写；有限接受步骤放在此模块，非通用事务框架。
- **报告与修订 owner**：[\_stage2_validation.py](https://github.com/ScholarWorkflow/professor-contact/blob/879982abe1d7d811bd9d014c03dce4f5912cc64f/.apm/skills/professor-contact/scripts/_stage2_validation.py#L166) 的 `stage2_parse_report_location` 保留合法短文本；`stage2_validation_report` L195 先确定 quote 命中，再从标题、偏移、前缀和字段文本反推 owner；L461 仍在 require_repairable 时拒绝固定失败。`cmd_stage2_refine_plan` L663、`cmd_stage2_refine_finalize` L725、`cmd_stage2_record_validation` L827 负责两轮。决定：定位继续沿用，归属改消费 renderer map；合法固定阻挡可登记，两个 refine 入口在方向过滤/结果读取与写入前统一阻止改写。
- **写入与绑定基础**：[\_contact_base.py](https://github.com/ScholarWorkflow/professor-contact/blob/879982abe1d7d811bd9d014c03dce4f5912cc64f/.apm/skills/professor-contact/scripts/_contact_base.py#L333) 的 `split_frontmatter`/`managed_conflict`/`managed_write` 管理既有人工正文保护；pack/render 指纹由 preflight 模块提供，`stage2_bound_render` 在 validation 模块。决定：复用现有写入保护与绑定，不扩大到人工改机器头认证；通过 runner 显式注入有限 helper，模块不反向导入 runner、不靠新的隐式全局或第二份状态。

历史 #92 的 [r11](https://github.com/ScholarWorkflow/professor-contact/blob/10324b8f10ff84080e9f7132bef807926de23279/plan/stage2-evidence-level/implementation-plan.md) 与 [t47](https://github.com/ScholarWorkflow/professor-contact/blob/10324b8f10ff84080e9f7132bef807926de23279/plan/stage2-evidence-level/test-plan.md) 展示了上述交叉风险及其版本适用性；本计划不复制历史测试矩阵，也不把旧分支通过记录外推到 main 上的新实现。

## 3. 核心方案

### 3.1 有限的可信引用显示

1. 从每个目标字段所属 gap/禁锚项取得结构化 `candidate_paper_ids`、`completed_by_item_key`，结合当前可信 canonical papers/facts 确定可解析 key。字段内显式 Zotero item 引用也声明了引用意图；此时缺元数据是错误，不能降级成普通文字。
2. 已知裸 key 仅按完整 token 边界替换。普通数字、日期及没有结构化引用依据的八位字符串保持不动，不能用通用八位正则当引用 authority。
3. 先识别已有 Markdown 链接与 URL 区间，不在地址里替换、不生成嵌套链接。已正确的题名/目标原样保留；已声明为 Zotero 论文引用但标签不是可信题名时，以该目标的可信题名重绘这一引用，保留其前后文字。普通外部链接不改写。
4. 题名取当前正式结构化记录；当前来源明确给空/无效题名时不拿旧标题遮盖。当前来源没有该条记录时可用已接受包中仍有效的 canonical 记录。缺可信题名/明确引用指向未知论文时，在写入前报告具体 gap、字段、key 及缺失元数据，交 Stage 2 数据准备 owner，保留原文件，不猜题名、不删引用。
5. 正常 finalize 将实际被这四个出口引用的结构化论文元数据并入现有 canonical papers。新建禁锚项从已通过校验的 freshness record 保存 candidate_paper_ids；reuse 的旧禁锚项在复制后的候选组装中，按 gap_id 取既有 freshness cache record，仅在现有 gap_fingerprint/candidate_fingerprint/status 有效性判断确认仍适用该 gap 时补回候选列表，并保留原 completed_by_item_key/evidence。新建与复用分支消费同一可信引用收集逻辑，不依赖仅覆盖 shortlist/excluded 的 stage2_old_pack_gap_statuses。当前该 helper 属于 `_stage2_finalize.py`；复用分支与新建分支都在候选隔离后完成引用收集。此为派生元数据补全，不改 freshness 结果。没有有效 cache record 时不从 evidence 自然语言猜全列表，也不为补无用列表强迫模型重跑：继续使用已有 completed_by_item_key、canonical 记录及明确引用；只有实际显示引用无法解析或缺可信题名时按第4项停止交源。完整候选列表不是所有旧包的新接受门槛。
6. `supporting_item_keys`、`relevant_keys`、P/L 引用许可与被显示引用元数据是不同集合；扩 canonical papers 不自动扩大任何前两者。纯包 refine 使用同一 renderer 和持久元数据，不能依赖已过期 /tmp facts。

### 3.2 renderer 显式生成归属，记录器只消费归属

renderer 输出内部结果 `body + ownership`，外部 Markdown 格式不因映射新增可见标记。写每个片段时同时携带稳定 direction_id、可选 gap_id、字段、事实 owner、区域类型与既有修订权限。区域是否合法与事实由谁拥有是两件事；本次新增合法固定区域只限固定证据卡/禁锚卡，不扩至卡片外。具体分类：

- narrative positioning 的可改文本、gap_notes 的真实 summary/explanation → narrative 区；按当前合法性标记可修订片段。main 已允许的展开 later-paper 题名命中继续属于既有 narrative 报告/修订路径，模型可调整受允许的表达或引用方式，但不能改可信题名事实。其事实 owner 为 source 不会将它变成本次新增固定对象；卡外模板和其他原本不可修订片段继续原限制。
- 固定卡 evidence/completed_part/remaining_gap、作者引文/译文/页码/状态/评估信息，及禁锚卡源字段 → source owner。固定卡的确定性标签/模板/链接排版 → generator owner。
- summary 未提供、回退到作者译文/原句时，回退片段是 source，不是假定为 narrative。
- 用户笔记、论文一览、全局红线等既有排除区 → excluded；不将它们变成新合法报告目标。

映射以最终 body 的物理行和该行字符区间描述输出片段。多行源值、LF/CRLF/裸 CR 及其他 `splitlines` 支持的分隔符按最终输出的同一分行函数累计；一次 append 绝不视为一行。模板与值同一行（尤其禁锚卡、summary+出处）仍有各自片段归属。行号读取使用同一实际文件内容及 frontmatter 偏移，不能混用逻辑 append 数量与物理行号。

内部 map 与当前 body 摘要放在已有 `cache.render[ANALYSIS_MD]` 下；它不含副本事实，只含归属位置。普通 finalize 与 narrative refine 重绘都同时更新 map，等价 body 保留时 map 必须对应实际保留 body。cache 整块替换不得抹掉 map 或 U1 标记。记录器仍验证现有 body/包/机器头绑定，并验证 map 的 body hash 与实际 body 一致；`_stage2_validation.py` 不得为生成 map 反向调用正常 finalize 或触发模型工作；缺 map 的旧包先走 §3.4 更新，绝不从 Markdown 标题/前缀临时猜 owner。

报告处理保持既有 schema、目标、计数、verdict 和原始字节不变：

1. 按现有逻辑从 quote 得到命中行；若 location 是有效结构化行号，按实际文件行号收窄。合法短文本 location 没有可解析行号时，允许 quote 在全文唯一命中。多处位置、quote 多行命中、同一行重复 quote 仍按现有边界拒绝，提示逐项准确定位。
2. 得到唯一 hit 和唯一 quote 字符区间后，查 renderer map。方向只能来自 map 的稳定 direction_id，必须与当前包存在的方向一致。
3. 先查区域与既有权限，再查事实 owner。quote 命中原来合法的 narrative 区时保留既有修订路径和权限（包括既有允许的展开 later title）；不能仅因其事实 owner 为 source 就转为固定停止。只有命中本次合法固定卡/禁锚区的固定片段才登记新增固定阻挡，并保留涉及的 owner/字段。同句跨两个固定片段可列两个 owner，不为了选一个 owner 而拒绝真实失败；与同卡 narrative 片段混合也按固定阻挡停止自动修订。碰到 excluded、卡外原不合法区或无可信映射，则维持原拒绝边界，不能冒充合法固定阻挡。
4. minor 沿用现有宽松非阻挡语义，不制造新停止条件；只有合法 blocking 决定修订/交源路径。

### 3.3 登记失败不授予修改权

原始报告、round/phase/results/pending 仍由现有 validator schema 2 管理。最小新增内部字段记录固定 blocking 的 direction/gap/field/owner；原 issues/notes/raw verdict 不删改。

- 第一轮含固定 blocking：正常登记 `needs_correction` 与 round=1，输出具体问题及源数据/生成器 owner。两个 refine 入口在产生或消费任何 rewrite 之前检查整个已登记报告；只要仍含固定阻挡，返回明确需要 owner 修复、零 jobs、零正文写入。方向过滤不能绕过全报告停止要求。
- 第一轮仅 narrative blocking：保留原一次修订流程，refine-finalize 更新 body/map 和校验绑定，保留第一轮问题和轮次，转 awaiting_second_validation。
- 第二轮首次出现固定 blocking：登记 terminal/fail_after_2_rounds，同时说明 owner；不再生成修订任务，不倒退到第一轮。
- 固定阻挡不能变成 pass/skipped。未修复就重复登记、直接跳第二轮、伪造 correction_applied 仍由原顺序/绑定检查拒绝。调用方停止重复提交同一失败，不无限调用 validator。
- source owner 修复真实来源，generator owner 修复 renderer 后，正常 Stage 2 finalize 接受新业务版本或实质新正文，才使旧 validator 失效；原报告文件保留。未变正文/依据、仅生成时间或元数据更新，不清空两轮限制。
- 主 SKILL 与 Codex/OpenCode analyzer 同步“登记→消费 owner→停止/修订”分支；不改变两种 harness 的委派方式，不要求 style-validator 修改输出格式。

### 3.4 最小旧包更新：只有现有 process→finalize 接受通路

本计划不引入 `stage2-refresh-display`。在现有 `cache.render[ANALYSIS_MD]` 中保存独立 U1 完成标记，preflight 读取该标记；缺失/落后时，即使原判断可 reuse_all，也改走现有 process，并说明需更新固定证据展示。已有业务来源失效原因仍优先保留，不用展示理由覆盖它们。

process 继续走正式 analyzer 数据准备与 stage2-plan。原分析、freshness、narrative、resolved 缓存按现有合法条件复用；U1 标记本身不改变模型输入指纹、不强迫全量模型重跑，不靠旧 /tmp facts。正常业务确已改变时仍按现有规则处理。来源/元数据不够则明确交数据准备，不能把持久包伪造成完整 facts。

只在正常 finalize 已实际确认并接受当前 body 与 map 后记录 U1 标记；metadata 构造函数不能提前声明展示完成。当前目标标记采用独立 U1 命名空间；#92 的 display_refresh_version=2/3 不构成 U1 已完成，防止错误继承其旧报告行为。未升级包保留原文件和历史校验；新报告需要先完成该受保护更新。更新后 body 未变且业务未变时保留合法原校验状态，因此不会因为加 map 就清轮数。

### 3.5 finalize 的有限接受与旧快照隔离

仅在 `_stage2_finalize.py` 的现有 Stage 2 写入 owner 内收敛一次接受步骤，不建通用框架。普通 finalize 是 U1 唯一正常接受入口；narrative refine 共享 renderer，但保持自己的第一轮→第二轮生命周期，不调用“业务新版本清轮次”分支。

顺序冻结如下：

1. 进入普通 finalize 后、候选方向与 canonical papers 组装前，深复制旧 pack、validator、render 元数据。记录当前受管 body/机器头及合法旧绑定；`_contact_pack.normalize_input_pack` 的 v2 浅复制不提供嵌套隔离，不能代替此步骤。后续所有候选复用条目（包括 split children）从复制件构造。不得把同一可变 dict/list 同时放入新候选和旧比较基线。
2. 完成现有 preflight/proof、resolved acceptance、来源与引用检查；构造完整候选包，尚不写任何接受标记或文件。实际生成候选 body+map，不能因 `stage2_render_state` 投影相等跳过。
3. 分别判断四件事：
   - body 是否等价：仅忽略 renderer 在固定顶部来源行中自行插入的生成时刻片段；该行其余统计文字照常比较。其他行即使含 ` ｜ 数据来源：` 也逐字参与比较。等价时保留原 body 字节和真实 SHA。
   - 机器头是否匹配当前包：即使 body 等价，只要 state_fingerprint 需更新，也用现有受管写入规则更新头，不能冻结整文件。
   - 业务依据是否改变：使用现有 needed_keys、成员语义重建，以及新旧方向的稳定 identity 集合、input_fingerprint/provisional_input_fingerprint、supporting_item_keys/relevant_keys/named_keys 和 accepted resolved 的语义（provisional/resolved ID、resolution_type、split/merge target、增删成员、原始输入指纹）。这些身份/许可按其现有集合或映射语义比较，忽略 applied_at。freshness 源事实改变由现有有效性指纹/needed_keys承接；不以新增派生 candidate 列表自身当作新事实。`stage2_render_state` 只可用于定位展示差异，整个投影不等不能额外成为清轮次理由。仅时间、cache、U1 标记/map、collection_key 或实际正文等价的展示投影变化不作为新业务依据；但 title/year/has_pdf 等已纳入现有 paper_digest，若使真实方向/resolve 输入指纹改变，就仍是业务变化，不能统称“仅展示”。真实输入指纹改变即使 body 等价也算改变；body 实质变化自身也足以使旧文字校验失效。
   - 旧 validator 是否原本有效：在旧快照与旧实际 body 上判断原 pack/render 绑定、合法轮次与 phase，不拿新候选去验证旧记录。业务/body 都未变而旧绑定无效时拒绝接受，不能重绑洗白。存在真实新业务或实质新正文时旧 validator 失效，但人工正文保护始终有效。
4. 写入前完成上述判断及 `managed_conflict`/人工决定处理。没有获准覆盖则返回 needs_decision，不能记 U1 成功。body 等价时用旧 body 同步必要机器头，否则写候选 body；更新实际 body 对应的 map、cache hash 和 U1 标记。
5. 当业务依据和 body 均未变，携带合法 validator 的 round/phase/pending/results，仅按接受的新包更新现有 pack binding；不改变 verdict。任一实质改变则新包不继承旧 validator，下一次真实校验从第一轮开始。生成时间不能成为改变；正常 narrative refine 例外按 §3.3 保留轮次。
6. 按现有顺序保存 pack/freshness cache，不新增跨文件事务；Markdown 已写但 pack 保存失败时不能返回成功或以旧包登记新报告，后续由现有绑定不一致/受管冲突路径要求恢复，绝不能补造 PASS。U1 完成元数据在内存候选中只于接受条件满足后设置，随 accepted pack 一并保存；不得让调用方先持久 stamp 再调用接受步骤。

U5 独立修改同一 finalize 接点。有限共享步骤输入为隔离的旧包/旧渲染快照、完整候选包/实际 body 及调用方已确认的业务依据变化；它负责等价判断、原有冲突处理、必要头更新及普通接受的 validator 继承/失效，不生成模型结果、不判断 U1 owner、不重新决定 resolved acceptance。具体私有函数名不作契约。先落地者完成必要局部实现；后落地者消费同一接受步骤并保留先前行为，不复制两套比较/失效逻辑。U1 无 U5 时完整可实施；U5 无 U1 时也不需此处 owner map 或 U1 标记。

## 4. 替代方案与取舍

- 全文正则清洗/让模型改写固定卡较短，但会误删普通八位文本、破坏原始事实和已有链接，不能满足 U1。
- 仅信 location 行号避开 quote 搜索会删掉现有合法短 location；反过来仅 quote 不查 renderer owner 会把重复文字误归。选择既有唯一 hit 解析后查结构化映射。
- 用渲染后 Markdown 前缀重建 owner 会再次被多行证据、同句混合、仿标题内容破坏。选择生成时字段归属，覆盖最终物理行与片段。
- #92 的 pack-only 双入口刷新可降低一次旧包数据准备成本，但额外需要来源可比较证明与两入口接受同步。本 U1 选择已有 process 通路，代价是旧包首次更新可能需要正常数据准备；不增加模型工作本身的失效理由，避免与 U5 索引刷新捆绑。
- 整文件冻结会留旧机器头；无条件正文重写会因时间使两轮重置。选择保留等价 body、必要更新机器头、独立判断业务依据和旧校验。

## 5. 不变量与代表性反例（静态设计说明）

1. **事实与展示分离**：句中可信 key 转成链接，机器 evidence 不动；作者原句含同一 key 也不参加这四出口的清洗。已正确链接不嵌套，未知普通八位文本不删除，明确引用缺题名先失败。
2. **hit 决定位置、renderer 决定 owner**：短 location=“后续论文依据”且 quote 唯一仍合法；重复 quote 配准确行号可定位；“多处”不猜。多行固定值续行仍 source，narrative 中出现“后续论文依据”前缀仍由实际字段归属决定，不因字样误分类。
3. **同句混合不授予事实改写权**：禁锚卡把 quote、题名、模板、evidence 拼成同一行，命中证据或模板交对应 owner；summary 回退原文不是 narrative；混合固定/narrative blocking 零模型修订。
4. **旧基线不可被候选污染**：仅 collection_key 更新、复用 split child 或嵌套 resolved 写入都不能先改旧 pack，再借“比较没变”保留不合法绑定。
5. **四项独立**：顶部时间变化保 body/轮次；证据行包含来源分隔符但引用变化仍写新 body；摘要输入变而 body 等价时更新必要头并失效旧校验；仅加 map/U1 标记时保留合法轮次，坏旧绑定不洗白。
6. **所有生成入口保映射**：第一轮 narrative 修订后第二轮发现固定卡问题仍可定位登记；refine 的 cache 重建不能抹掉 owner map。旧无 map 包不反解析 Markdown，先按受保护 process 更新。
7. **正常失败可停**：第一轮固定失败不虚报“两轮已尽”，第二轮固定失败不重开；源/模板实际修复后才接受新版本；无变化反复运行不清次数。

这些是方案完整性检查，非新增测试矩阵、Case ID、采集器或过程认证要求。具体必测目标和检查方式见同目录 [测试计划](test-plan.md)。2026-10-20 用户已授权补齐测试计划；实际 recipe 待产品实现后接线，本轮不运行测试。

## 6. 从 #92 至今吸取的设计教训

- “结构化优先”不等于禁止已有合法短 location；结构化归属应建立在现有唯一命中之后，而不是改上游报告契约。
- 修补 Markdown 前缀再修物理行仍是在反推 owner；owner 必须在生成字段时直接给定，包括同句混合及 fallback。
- 两入口各自接受造成正文/版本/轮次分叉；U1 缩到现有唯一正常 finalize 接受，后续有新入口也只消费这一步。
- 把共享 helper 放对位置仍不够；caller 在组装前共享旧 dict 会使旧证据先被污染。旧快照隔离必须早于组装和任何 mutation。
- 整 Markdown 冻结混淆 body 与机器头，时间戳变化混淆展示与业务依据。四者分别判断，既不冻结旧头，也不借生成时间清轮次。
- 已撤回的“独立篡改 header”历史反例不恢复为本计划要求；继续依赖已有正式绑定，拒绝增加防伪矩阵或重复认证设施。
- 不承诺绝对无 bug；通过先冻结真实输入、owner、兼容、失败路径和代表性反例，降低补丁链式返工。审核一次覆盖可判断的完整范围，后续仅处理语义变化及连带影响。

## 7. r3 修订影响与实施交接

r2 已合入的三项设计仍保留：明确业务依据，区分合法区域/事实 owner，旧 reuse 禁锚只从有效 cache 补可得引用元数据。r3 解除未完成拆分假设，将设计落到 main 现有 render/facts/pack/preflight/finalize/validation/base 模块；具体化工厂接线、共享接受与 cache 保留责任，完成标记统一放入 cache.render，避免 U5 刷新或 narrative refine 重建缓存时误丢。业务目标、合法短 location、两轮上限、人工正文保护均未扩张。

需独立复核的影响：P1 当前模块事实和路径；P2 接受步骤的 owner/依赖接线；P3 cache 保留及普通/refine 生命周期；P4 拆分后实施顺序。原 r2 未改动的目标和有限引用决定可由 reviewer 结合上述差异复用旧结论，作者不自行声明复用 PASS。

### 实施顺序及文件边界

1. 保存本完整候选并完成独立计划复核。当前 main 的 Stage 2 拆分条件已满足，无需等待 Stage 3 拆分，也不因单纯模块移动重跑旧业务验证。
2. 产品 owner 在 `_stage2_render.py` 完成有限引用转换和生成时 map；在 `_stage2_finalize.py` 收齐新建/复用分支所需持久 canonical 引用记录，复用 `_stage2_facts.py` 现有 cache 有效性判断与 `_contact_pack.py` 既有 canonical 规范。不得为方便显示扩大成员、引用许可或 facts schema。
3. 同一 U1 实现完成 finalize 组装前旧快照隔离、实际候选接受及 `_stage2_preflight.py` 的 U1 懒更新判定；`contact_state.py` 仅显式接线所需依赖，保持现有 CLI 签名。完成标记只随成功接受落盘，不能只改 renderer 而让旧包永久 reuse_all。
4. `_stage2_validation.py` 消费 map，完成固定失败登记、两 refine 入口的全报告阻挡和 refine 后 map/cache 保留。保留现有 narrative 第一轮→第二轮流转，不调用普通新版本清轮次分支。同步 SKILL 与现有 Codex/OpenCode analyzer 的登记后停止/修订说明，不改委派结构或 style-validator 格式。
5. U1/U5 先落地者建立所需的有限普通接受步骤，后落地者复用而非另写一套；两者在普通接受中对 cache.render 与既有 preflight 元数据按 owned fields 更新，保留另一者仍有效字段。narrative refine 保留原有 preflight 失效/重建语义，不因保留 U1 map 而复制旧 preflight 为有效；只合并同一接受版本仍适用的 render 元数据。无 U5 时 U1 能独立完成；无 U1 时 U5 不需要 owner map 或 U1 完成标记。若 U5 后续已存在，所有重绘须保持 U1 map 与真实 body 一致，不能以空 map 冒充成功。
6. 产品观察入口只为 Markdown 四出口、record-validation 返回/持久 validator、refine jobs/写入结果、preflight/finalize 旧包更新与人工冲突。测试 owner 后续按独立 U1 范围确定必要检查；具体清单见同目录测试计划，实际 recipe 待实现后接线；不要求 U5 通过、整仓回归、真实模型全流程或 #92 历史矩阵。

当前交付（2026-10-20）：执行计划 r3 与测试计划 t1 保持原设计；产品实现与可执行测试 recipe 已接线：初始实现 `2b813fc`，实现符合性复核修复 `3d6c2bc`；实际执行结果记录在同目录 [test-plan §7](test-plan.md#7-执行结果2026-10-20)，复核记录见 [implementation-review-2026-10-20.md](implementation-review-2026-10-20.md)。公开正式审核状态仍以正式审核记录为准，本次不自行授予计划、测试或合并关口结论。计划入库不关闭 #92、不授权合并任何 PR。若后续 main 有语义变化，只分析受影响 owner/接受/兼容决定；仅 SHA 或模块路径变化不重开全部设计。
