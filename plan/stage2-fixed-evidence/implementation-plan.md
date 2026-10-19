# Stage 2 U1：固定证据展示与真实阻挡归属

- Plan revision：`stage2-u1-r2`（2026-10-19）；Proposed review status: pending。
- 唯一目标路径：`plan/stage2-fixed-evidence/implementation-plan.md`。本轮只交执行计划，未实施、未运行测试，不沿用 #92 的批准或测试状态作为本计划通过结论。
- Requirement revision：2026-10-17 已确认 U1，2026-10-19 用户明确要求总结 #92 至今经验，将 U1/U5 分成两个 PR 从头设计；保持 main 行为先完成 Stage 2 模块拆分，再分别修复。当前计划可独立入库；产品实施顺序仍遵守该决定。
- Repository baseline：`ScholarWorkflow/professor-contact@d5a4f751fb80de4819d4a1de3ee829db52cea6fc`，2026-10-19 17:42 UTC 复核 main 未变。#92 当前 `10324b8f10ff84080e9f7132bef807926de23279` 的 r11/t47 只作经验与历史事实，不作为代码移植基线。
- Stage 2 拆分尚无已核实 PR/模块落点。以下以当前真实符号和职责指定修改点；拆分合并后，实施者先核对符号的机械迁移并更新路径指针。纯移动不重开设计；若改变行为则只分析受影响决定。本前提是实施排序，不假设未来代码已经存在。
- 规则：[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)（2026-10-19 14:02 UTC）、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)（2026-10-09 20:13 UTC）、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)（2026-10-09 20:37 UTC），本轮重新读取。

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

以下源码均为 [main 的 contact_state.py](https://github.com/ScholarWorkflow/professor-contact/blob/d5a4f751fb80de4819d4a1de3ee829db52cea6fc/.apm/skills/professor-contact/scripts/contact_state.py)。

- **展示落在 renderer**：`build_direction_pack` L4409—4572 保留机器证据与候选引用；`render_analysis_md` L4573—4721 把四个目标字段直接插入 Markdown。`redact_item_keys` L4399 附近会替换未知八位字符串，不能直接当可信引用解析器。决定：只在四个出口解析结构化可信引用，原字段不变。
- **引用元数据已有持久 owner**：L4510 附近以及 finalize L5374—5436 使用教授级 canonical `papers`，支持成员与引用范围分离；`Stage2PackRefineContext` L1744 起从持久包恢复，`stage2_trusted_paper_title`/`stage2_require_later_paper_titles` L10164—10268 只接受结构化题名。决定：补齐四出口需要的 canonical 引用元数据，不扩 supporting keys 或 narrative 引用许可，不从 Markdown 标签反推题名。
- **合法短 location 已存在**：`stage2_parse_report_location`/`stage2_validation_report` L10269—10451 接受短位置，先用 quote 找命中，再用结构化行号（若有）收窄；无法唯一定位仍拒绝。决定：保持这个入口语义，owner 查询消费已确定的 hit，不要求上游改成只能报行号。
- **归属当前从 Markdown 反推**：L10402—10567 解析方向标题、固定偏移、列表前缀和文本值来判断 narrative，并在非 repairable 时拒绝。决定：renderer 在输出各字段时直接给归属；记录器不再用标题编号、前缀或全文字符串相等判断字段 owner。
- **登记与修订耦合**：L10938—11020 第一轮调用 `require_repairable`；`stage2_require_recorded_validation`、两个 refine 入口 L10576—10936 要求已登记。决定：合法性与 owner 分类先完成，固定失败可入库，但两个 refine 入口共同禁止固定失败下的任何模型修订。
- **旧包被 reuse_all 绕开**：`cmd_stage2_preflight` L3780—4008 只有 reuse_all/process；本 main 没有 #92 的 `stage2-refresh-display`。决定：U1 使用现有 process 通路完成一次懒更新，不另建展示刷新入口，也不要求 U5 落地。
- **旧对象可能在比较前被污染**：finalize L5038—5053 `reused_entry = old_entry` 后改 collection_key，随后 resolved 操作会改嵌套方向；L5438—5519 比较旧 ctx.pack。决定：进入 finalize、任何候选组装前隔离旧快照，候选复用条目及 carried split children 也必须复制，后续只读旧快照。
- **旧接受分支有明确缺口**：L5438—5465 用投影相等跳过实际渲染；L5490—5519 在 Markdown 写入后才核旧 validator；`managed_write`/`stage2_bound_render` 已区分 body hash 与 state_fingerprint。决定：旧状态检查先于写，实际候选 body 先生成再判断；body 等价不能冻结旧机器头，也不能证明业务依据没变。

历史 #92 的 [r11](https://github.com/ScholarWorkflow/professor-contact/blob/10324b8f10ff84080e9f7132bef807926de23279/plan/stage2-evidence-level/implementation-plan.md) 与 [t47](https://github.com/ScholarWorkflow/professor-contact/blob/10324b8f10ff84080e9f7132bef807926de23279/plan/stage2-evidence-level/test-plan.md) 展示了上述交叉风险及其版本适用性；本计划不复制历史测试矩阵，也不把旧分支通过记录外推到 main 上的新实现。

## 3. 核心方案

### 3.1 有限的可信引用显示

1. 从每个目标字段所属 gap/禁锚项取得结构化 `candidate_paper_ids`、`completed_by_item_key`，结合当前可信 canonical papers/facts 确定可解析 key。字段内显式 Zotero item 引用也声明了引用意图；此时缺元数据是错误，不能降级成普通文字。
2. 已知裸 key 仅按完整 token 边界替换。普通数字、日期及没有结构化引用依据的八位字符串保持不动，不能用通用八位正则当引用 authority。
3. 先识别已有 Markdown 链接与 URL 区间，不在地址里替换、不生成嵌套链接。已正确的题名/目标原样保留；已声明为 Zotero 论文引用但标签不是可信题名时，以该目标的可信题名重绘这一引用，保留其前后文字。普通外部链接不改写。
4. 题名取当前正式结构化记录；当前来源明确给空/无效题名时不拿旧标题遮盖。当前来源没有该条记录时可用已接受包中仍有效的 canonical 记录。缺可信题名/明确引用指向未知论文时，在写入前报告具体 gap、字段、key 及缺失元数据，交 Stage 2 数据准备 owner，保留原文件，不猜题名、不删引用。
5. 正常 finalize 将实际被这四个出口引用的结构化论文元数据并入现有 canonical papers。新建禁锚项从已通过校验的 freshness record 保存 candidate_paper_ids；reuse 的旧禁锚项在复制后的候选组装中，按 gap_id 取既有 freshness cache record，仅在现有 gap_fingerprint/candidate_fingerprint/status 有效性判断确认仍适用该 gap 时补回候选列表，并保留原 completed_by_item_key/evidence。新建与复用分支消费同一可信引用收集逻辑，不依赖仅覆盖 shortlist/excluded 的 stage2_old_pack_gap_statuses。此为派生元数据补全，不改 freshness 结果。没有有效 cache record 时不从 evidence 自然语言猜全列表，也不为补无用列表强迫模型重跑：继续使用已有 completed_by_item_key、canonical 记录及明确引用；只有实际显示引用无法解析或缺可信题名时按第4项停止交源。完整候选列表不是所有旧包的新接受门槛。
6. `supporting_item_keys`、`relevant_keys`、P/L 引用许可与被显示引用元数据是不同集合；扩 canonical papers 不自动扩大任何前两者。纯包 refine 使用同一 renderer 和持久元数据，不能依赖已过期 /tmp facts。

### 3.2 renderer 显式生成归属，记录器只消费归属

renderer 输出内部结果 `body + ownership`，外部 Markdown 格式不因映射新增可见标记。写每个片段时同时携带稳定 direction_id、可选 gap_id、字段、事实 owner、区域类型与既有修订权限。区域是否合法与事实由谁拥有是两件事；本次新增合法固定区域只限固定证据卡/禁锚卡，不扩至卡片外。具体分类：

- narrative positioning 的可改文本、gap_notes 的真实 summary/explanation → narrative 区；按当前合法性标记可修订片段。main 已允许的展开 later-paper 题名命中继续属于既有 narrative 报告/修订路径，模型可调整受允许的表达或引用方式，但不能改可信题名事实。其事实 owner 为 source 不会将它变成本次新增固定对象；卡外模板和其他原本不可修订片段继续原限制。
- 固定卡 evidence/completed_part/remaining_gap、作者引文/译文/页码/状态/评估信息，及禁锚卡源字段 → source owner。固定卡的确定性标签/模板/链接排版 → generator owner。
- summary 未提供、回退到作者译文/原句时，回退片段是 source，不是假定为 narrative。
- 用户笔记、论文一览、全局红线等既有排除区 → excluded；不将它们变成新合法报告目标。

映射以最终 body 的物理行和该行字符区间描述输出片段。多行源值、LF/CRLF/裸 CR 及其他 `splitlines` 支持的分隔符按最终输出的同一分行函数累计；一次 append 绝不视为一行。模板与值同一行（尤其禁锚卡、summary+出处）仍有各自片段归属。行号读取使用同一实际文件内容及 frontmatter 偏移，不能混用逻辑 append 数量与物理行号。

内部 map 与当前 body 摘要放在已有 `cache.render[ANALYSIS_MD]` 下；它不含副本事实，只含归属位置。普通 finalize 与 narrative refine 重绘都同时更新 map，等价 body 保留时 map 必须对应实际保留 body。cache 整块替换不得抹掉 map 或 U1 标记。记录器仍验证现有 body/包/机器头绑定，并验证 map 的 body hash 与实际 body 一致；缺 map 的旧包先走 §3.4 更新，绝不从 Markdown 标题/前缀临时猜 owner。

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

本计划不引入 `stage2-refresh-display`。在已有 preflight 元数据中增加 U1 私有展示修订标记；缺失/落后时，即使原判断可 reuse_all，也改走现有 process，并说明需更新固定证据展示。已有业务来源失效原因仍优先保留，不用展示理由覆盖它们。

process 继续走正式 analyzer 数据准备与 stage2-plan。原分析、freshness、narrative、resolved 缓存按现有合法条件复用；U1 标记本身不改变模型输入指纹、不强迫全量模型重跑，不靠旧 /tmp facts。正常业务确已改变时仍按现有规则处理。来源/元数据不够则明确交数据准备，不能把持久包伪造成完整 facts。

只在正常 finalize 已实际确认并接受当前 body 与 map 后记录 U1 标记；metadata 构造函数不能提前声明展示完成。当前目标标记采用独立 U1 命名空间；#92 的 display_refresh_version=2/3 不构成 U1 已完成，防止错误继承其旧报告行为。未升级包保留原文件和历史校验；新报告需要先完成该受保护更新。更新后 body 未变且业务未变时保留合法原校验状态，因此不会因为加 map 就清轮数。

### 3.5 finalize 的有限接受与旧快照隔离

仅在现有 Stage 2 写入 owner 内收敛一次接受步骤，不建通用框架。普通 finalize 是 U1 唯一正常接受入口；narrative refine 共享 renderer，但保持自己的第一轮→第二轮生命周期，不调用“业务新版本清轮次”分支。

顺序冻结如下：

1. 进入普通 finalize 后、候选方向与 canonical papers 组装前，深复制旧 pack、validator、render 元数据。记录当前受管 body/机器头及合法旧绑定；后续所有候选复用条目（包括 split children）从复制件构造。不得把同一可变 dict/list 同时放入新候选和旧比较基线。
2. 完成现有 preflight/proof、resolved acceptance、来源与引用检查；构造完整候选包，尚不写任何接受标记或文件。实际生成候选 body+map，不能因 `stage2_render_state` 投影相等跳过。
3. 分别判断四件事：
   - body 是否等价：仅忽略 renderer 在固定顶部来源行中自行插入的生成时刻片段；该行其余统计文字照常比较。其他行即使含 ` ｜ 数据来源：` 也逐字参与比较。等价时保留原 body 字节和真实 SHA。
   - 机器头是否匹配当前包：即使 body 等价，只要 state_fingerprint 需更新，也用现有受管写入规则更新头，不能冻结整文件。
   - 业务依据是否改变：使用现有 needed_keys、成员语义重建，以及新旧方向的稳定 identity 集合、input_fingerprint/provisional_input_fingerprint、supporting_item_keys/relevant_keys/named_keys 和 accepted resolved 的语义（provisional/resolved ID、resolution_type、split/merge target、增删成员、原始输入指纹）。这些身份/许可按其现有集合或映射语义比较，忽略 applied_at。freshness 源事实改变由现有有效性指纹/needed_keys承接；不以新增派生 candidate 列表自身当作新事实。`stage2_render_state` 只可用于定位展示差异，整个投影不等不能额外成为清轮次理由。仅时间、cache、U1 标记/map、collection_key 或实际正文等价的展示投影变化不作为新业务依据；但 title/year/has_pdf 等已纳入现有 paper_digest，若使真实方向/resolve 输入指纹改变，就仍是业务变化，不能统称“仅展示”。真实输入指纹改变即使 body 等价也算改变；body 实质变化自身也足以使旧文字校验失效。
   - 旧 validator 是否原本有效：在旧快照与旧实际 body 上判断原 pack/render 绑定、合法轮次与 phase，不拿新候选去验证旧记录。业务/body 都未变而旧绑定无效时拒绝接受，不能重绑洗白。存在真实新业务或实质新正文时旧 validator 失效，但人工正文保护始终有效。
4. 写入前完成上述判断及 `managed_conflict`/人工决定处理。没有获准覆盖则返回 needs_decision，不能记 U1 成功。body 等价时用旧 body 同步必要机器头，否则写候选 body；更新实际 body 对应的 map、cache hash 和 U1 标记。
5. 当业务依据和 body 均未变，携带合法 validator 的 round/phase/pending/results，仅按接受的新包更新现有 pack binding；不改变 verdict。任一实质改变则新包不继承旧 validator，下一次真实校验从第一轮开始。生成时间不能成为改变；正常 narrative refine 例外按 §3.3 保留轮次。
6. 按现有顺序保存 pack/freshness cache，不新增跨文件事务；Markdown 已写但 pack 保存失败时不能返回成功或以旧包登记新报告，后续由现有绑定不一致/受管冲突路径要求恢复，绝不能补造 PASS。此处接受 helper 的返回结果只有成功后才被 caller 用来 stamp 元数据。

U5 可能独立修改同一 finalize 接点。先落地者完成必要局部实现；后落地者消费同一接受步骤并保留先前行为，不复制两套比较/失效逻辑。U1 无 U5 时完整可实施；U5 无 U1 时也不需此处 owner map 或 U1 标记。

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

这些是方案完整性检查，非新增测试矩阵、Case ID、采集器或过程认证要求。具体必测目标/步骤由后续测试计划按当前规则处理，本轮未授权也未编写完整测试计划。

## 6. 从 #92 至今吸取的设计教训

- “结构化优先”不等于禁止已有合法短 location；结构化归属应建立在现有唯一命中之后，而不是改上游报告契约。
- 修补 Markdown 前缀再修物理行仍是在反推 owner；owner 必须在生成字段时直接给定，包括同句混合及 fallback。
- 两入口各自接受造成正文/版本/轮次分叉；U1 缩到现有唯一正常 finalize 接受，后续有新入口也只消费这一步。
- 把共享 helper 放对位置仍不够；caller 在组装前共享旧 dict 会使旧证据先被污染。旧快照隔离必须早于组装和任何 mutation。
- 整 Markdown 冻结混淆 body 与机器头，时间戳变化混淆展示与业务依据。四者分别判断，既不冻结旧头，也不借生成时间清轮次。
- 已撤回的“独立篡改 header”历史反例不恢复为本计划要求；继续依赖已有正式绑定，拒绝增加防伪矩阵或重复认证设施。
- 不承诺绝对无 bug；通过先冻结真实输入、owner、兼容、失败路径和代表性反例，降低补丁链式返工。审核一次覆盖可判断的完整范围，后续仅处理语义变化及连带影响。

## 7. r2 修订影响与实施交接

r1 独立完整审核提出三处需冻结的边界，r2 已合入唯一全文：业务依据不再引用未定义的“render_state 业务投影”；明确合法固定区域与事实 owner 分离、卡外保持原权限；旧 reuse 禁锚从仍有效 freshness cache 补可取得候选，缺无用完整列表不成为新门槛。这三项及连带生命周期由独立 reviewer 定点复核；未改变 U1 业务目标、不新增测试义务，作者仍保留 pending。

### 实施顺序

1. 计划只读独立复核后保存唯一完整文件；当前不标 APPROVED。Stage 2 行为保持拆分先落地后，实施者核对 main 语义与符号映射。
2. 产品 owner 在 renderer/pack 构造落地有限引用转换及字段映射；补齐持久元数据，保持公共 schema 与成员许可。
3. 在同一产品变更中完成普通 finalize 旧快照隔离、实际候选接受、U1 preflight 懒更新标记及 refine map 保留；不能先 stamp 版本再补接受，也不能只改 renderer 而让旧包永久 reuse_all。
4. validator/runner owner 完成合法报告分类与固定失败登记，两个 refine 入口冻结零改写条件；同步 SKILL 与两个 analyzer 停止分支。
5. 受影响的产品观察入口仅为 Markdown 四出口、record-validation 返回和持久 validator 状态、refine jobs/写入结果、preflight/finalize 对旧包的更新与人工冲突结果。测试 owner 后续按独立 U1 范围制定必要检查；不把 U5 通过、整仓重跑、真实模型全流程或 #92 全部历史用例作为 U1 前置。

当前未完成：独立候选审核、正式计划审核、产品实施、测试计划与执行、合并审核。当前无已知 critical unresolved impact；未来拆分如不再是行为保持变更，须针对实际语义差异复核相关决定。计划入库不关闭 #92、不授权合并任何 PR，也不表示 U1 已修复。
