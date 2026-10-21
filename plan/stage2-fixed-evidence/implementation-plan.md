# Stage 2 U1：固定证据展示与真实阻挡归属

- Plan revision：`stage2-u1-r4`（2026-10-21）；Plan review status：PENDING independent review。作者未授予 APPROVED/PASS；r3 的既有批准保留为历史记录，不自动覆盖本轮机制修订。
- 唯一执行计划：`plan/stage2-fixed-evidence/implementation-plan.md`。本 r4 完整取代 r3 的执行决定，不另附并行旧方案；同目录 [测试计划](test-plan.md) 的既有记录保留，本次仅修改执行计划，不修改测试计划、产品代码或执行测试。
- Requirement revision：2026-10-17 已确认 U1；2026-10-19 用户要求总结 #92 至今经验，先保持行为拆分 Stage 2，再分别设计 U1/U5；2026-10-20 授权两份计划；2026-10-21 用户要求先看 PR107 与 exam-question-pipeline PR32 的机制如何修复，并授权“分别修改这两个的执行计划”。本轮修复既有 U1 要求的实现机制，不新增业务目标。
- 实施核对基线：`ScholarWorkflow/professor-contact@cd6387759157c505acb96ed8459e0cc2fbd7f6ba`，PR107 分支 `plan/stage2-fixed-evidence-20261019`，2026-10-21 06:00 UTC 读取。被替代计划 blob：`fd85dbdbd0f4d697e5a02c317f895899b3192a88`。该基线只指本轮读取的产品版本，不宣称本次文档修改已修复产品。
- 历史基线：r3 基于 main `879982abe1d7d811bd9d014c03dce4f5912cc64f`（#117）设计；r3 [批准记录](https://github.com/ScholarWorkflow/professor-contact/pull/107#issuecomment-6293465316) 与当前 t3 [正式测试记录](https://github.com/ScholarWorkflow/professor-contact/pull/107#issuecomment-6308427553) 各按原版本保留，不外推为 r4 或产品合并批准。#92 `10324b8f10ff84080e9f7132bef807926de23279` 的 r11/t47 仅作教训，不移植其矩阵。
- Stage 2 拆分已完成；Stage 3 拆分、U5 交付不属于 U1 前置。
- 规则：[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)（2026-10-19 14:02 UTC）、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)（2026-10-09 20:13 UTC）、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)（2026-10-09 20:37 UTC），2026-10-21 06:00 UTC 重新读取。

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

以下事实以本轮 PR head 为准；既有正确部分保留，不能把 r3 实施前的描述继续当作当前缺陷。

- **引用来源分叉**：[\_stage2_finalize.py](https://github.com/ScholarWorkflow/professor-contact/blob/cd6387759157c505acb96ed8459e0cc2fbd7f6ba/.apm/skills/professor-contact/scripts/_stage2_finalize.py#L873-L929) 的 `_current_paper_record` 先复制旧 canonical，再只用当前非 None 字段覆盖；展示更新分支会走该逻辑，而新建分支直接消费当前记录。故“当前记录存在但 title=null”会在分支间得到不同结果。根因是来源裁决与字段补全混为一体。§3.1 冻结唯一存在性优先裁决，不靠每个 caller 补空值检查。
- **方向权威分叉**：[\_stage2_validation.py](https://github.com/ScholarWorkflow/professor-contact/blob/cd6387759157c505acb96ed8459e0cc2fbd7f6ba/.apm/skills/professor-contact/scripts/_stage2_validation.py#L340-L418) 在消费 ownership map 前仍从 `## 方向 ` 建立 Markdown sections 并确定 direction。源字段中的仿标题可能先被误归或拒绝。根因是 renderer map 与标题扫描同时拥有方向裁决权。§3.2 移除该前置方向裁决，保留 quote/location 位置查找。
- **字节与坐标混用**：[\_stage2_finalize.py](https://github.com/ScholarWorkflow/professor-contact/blob/cd6387759157c505acb96ed8459e0cc2fbd7f6ba/.apm/skills/professor-contact/scripts/_stage2_finalize.py#L293-L315) 的 body 比较使用丢失行尾的 splitlines，旧文读取处使用 read_text；[\_contact_base.py](https://github.com/ScholarWorkflow/professor-contact/blob/cd6387759157c505acb96ed8459e0cc2fbd7f6ba/.apm/skills/professor-contact/scripts/_contact_base.py) 的受管冲突读取与 validation 绑定读取也需沿同一 U1 接受链核对。根因不是少加一个换行 case，而是文件完整性比较、body hash 与报告字符坐标没有共享无损输入。§3.5–3.6 将二者分开并明确所有消费者。
- **已有正确部分**：当前 finalize 已有旧快照深复制及旧 header.state 绑定检查，不再要求“从无到有”补这两项，也不恢复额外头部来源认证。renderer 已区分可信题名/源文字与自动生成链接语法/目标的 owner；既有 Markdown 链接仍保持源片段语义。cache 已参与现有 pack hash，不把它描述为独立未绑定漏洞。
- **模块职责不变**：`_stage2_render.py` 生成四出口正文及 map；`_stage2_facts.py` 的 Stage2Context/freshness_entry 决定当前事实及缓存适用性，Stage2PackRefineContext 消费持久包；`_contact_pack.py` 规范既有 canonical papers 与冲突守卫；`_stage2_preflight.py` 只决定 reuse_all/process；`_stage2_finalize.py` 拥有普通候选接受；`_stage2_validation.py` 拥有报告、refine 与两轮状态；`_contact_base.py` 保留受管文件保护基础。`contact_state.py` 工厂显式注入所需局部 helper，不反向导入 runner，不建立隐式全局或第二份状态。

历史 #92 的 [r11](https://github.com/ScholarWorkflow/professor-contact/blob/10324b8f10ff84080e9f7132bef807926de23279/plan/stage2-evidence-level/implementation-plan.md) 与 [t47](https://github.com/ScholarWorkflow/professor-contact/blob/10324b8f10ff84080e9f7132bef807926de23279/plan/stage2-evidence-level/test-plan.md) 展示了上述交叉风险及其版本适用性；本计划不复制历史测试矩阵，也不把旧分支通过记录外推到 main 上的新实现。

## 3. 核心方案

### 3.1 有限的可信引用显示

1. 从每个目标字段所属 gap/禁锚项取得结构化 `candidate_paper_ids`、`completed_by_item_key`，结合当前可信 canonical papers/facts 确定可解析 key。字段内显式 Zotero item 引用也声明了引用意图；此时缺元数据是错误，不能降级成普通文字。
2. 已知裸 key 仅按完整 token 边界替换。普通数字、日期及没有结构化引用依据的八位字符串保持不动，不能用通用八位正则当引用 authority。
3. 先识别已有 Markdown 链接与 URL 区间，不在地址里替换、不生成嵌套链接。已正确的题名/目标原样保留；已声明为 Zotero 论文引用但标签不是可信题名时，以该目标的可信题名重绘这一引用，保留其前后文字。普通外部链接不改写。
4. 唯一可信记录裁决先判断当前正式记录集合是否包含该 key，不用 `get(...) is not None`、字段真值或旧记录 merge 代替存在性：
   - 当前存在该 key：整条当前记录是该引用的 authority。当前记录为 null、非合法记录，或题名缺失/null/空/不符合既有可信题名规则，都明确失败，不能从旧 canonical 填回题名，也不能拼成“当前有效”的混合记录。
   - 当前完全没有该 key：才允许使用已接受包中仍符合原有效性/绑定规则的 canonical 记录；旧记录本身无效仍失败。这里“没有记录”不包括“有记录但字段无效”。
   - 新建、旧方向 reuse、展示更新三个普通 finalize 分支，在持久 canonical 候选提交前调用同一私有裁决 helper，renderer 只消费裁决后的记录，不再自行回退。仅处理四出口实际需要的结构化引用，不借机验证全部无关论文。
   - 纯包 refine 没有新的当前 facts，使用本轮已接受的持久 canonical 记录并遵守相同题名有效性规则；不刷新来源、不读过期 /tmp facts，也不能把无法取得当前 facts 宣称为已核验当前不存在。
   缺可信题名/明确引用未知论文时，在任何接受写入前报告具体 direction/gap、字段、key 与元数据错误，交 Stage 2 数据准备 owner；保留原文件与校验，不猜题名、不删引用、不自动扩大模型工作。
5. 正常 finalize 将实际被这四个出口引用的结构化论文元数据并入现有 canonical papers。新建禁锚项从已通过校验的 freshness record 保存 candidate_paper_ids；reuse 的旧禁锚项在复制后的候选组装中，按 gap_id 取既有 freshness cache record，仅在现有 gap_fingerprint/candidate_fingerprint/status 有效性判断确认仍适用该 gap 时补回候选列表，并保留原 completed_by_item_key/evidence。新建与复用分支消费同一可信引用收集逻辑，不依赖仅覆盖 shortlist/excluded 的 stage2_old_pack_gap_statuses。当前该 helper 属于 `_stage2_finalize.py`；复用分支与新建分支都在候选隔离后完成引用收集。此为派生元数据补全，不改 freshness 结果。没有有效 cache record 时不从 evidence 自然语言猜全列表，也不为补无用列表强迫模型重跑：继续使用已有 completed_by_item_key、canonical 记录及明确引用；只有实际显示引用无法解析或缺可信题名时按第4项停止交源。完整候选列表不是所有旧包的新接受门槛。
6. `supporting_item_keys`、`relevant_keys`、P/L 引用许可与被显示引用元数据是不同集合；扩 canonical papers 不自动扩大任何前两者。纯包 refine 使用同一 renderer 和持久元数据，不能依赖已过期 /tmp facts。

### 3.2 renderer 显式生成归属，记录器只消费归属

renderer 输出内部结果 `body + ownership`，外部 Markdown 格式不因映射新增可见标记。写每个片段时同时携带稳定 direction_id、可选 gap_id、字段、事实 owner、区域类型与既有修订权限。区域是否合法与事实由谁拥有是两件事；本次新增合法固定区域只限固定证据卡/禁锚卡，不扩至卡片外。具体分类：

- narrative positioning 的可改文本、gap_notes 的真实 summary/explanation → narrative 区；按当前合法性标记可修订片段。main 已允许的展开 later-paper 题名命中继续属于既有 narrative 报告/修订路径，模型可调整受允许的表达或引用方式，但不能改可信题名事实。其事实 owner 为 source 不会将它变成本次新增固定对象；卡外模板和其他原本不可修订片段继续原限制。
- 固定卡 evidence/completed_part/remaining_gap、作者引文/译文/页码/状态/评估信息，及禁锚卡源字段 → source owner。固定卡的确定性标签/模板/链接排版 → generator owner。
- summary 未提供、回退到作者译文/原句时，回退片段是 source，不是假定为 narrative。
- 用户笔记、论文一览、全局红线等既有排除区 → excluded；不将它们变成新合法报告目标。

映射以最终 body 严格解码后的物理行和该行字符区间描述输出片段。字符区间统一使用 Python Unicode 字符索引，不混入 UTF-8 字节偏移；body 完整性另按 §3.6 的原始字节计算。多行源值、LF/CRLF/裸 CR 及其他 `splitlines` 支持的分隔符按最终输出的同一分行函数累计；一次 append 绝不视为一行。模板与值同一行（尤其禁锚卡、summary+出处）仍有各自片段归属。行号读取使用同一实际文件内容及 frontmatter 偏移，不能混用逻辑 append 数量与物理行号。

内部 map 与当前 body 摘要放在已有 `cache.render[ANALYSIS_MD]` 下；它不含副本事实，只含归属位置。普通 finalize 与 narrative refine 重绘都同时更新 map，等价 body 保留时 map 必须对应实际保留 body。cache 整块替换不得抹掉 map 或 U1 标记。记录器仍验证现有 body/包/机器头绑定，并验证 map 的 body hash 与实际 body 一致；`_stage2_validation.py` 不得为生成 map 反向调用正常 finalize 或触发模型工作；缺 map 的旧包先走 §3.4 更新，绝不从 Markdown 标题/前缀临时猜 owner。

报告处理保持既有 schema、目标、计数、verdict 和原始字节不变：

1. 按现有逻辑从 quote 得到命中行；若 location 是有效结构化行号，按实际文件行号收窄。合法短文本 location 没有可解析行号时，允许 quote 在全文唯一命中。多处位置、quote 多行命中、同一行重复 quote 仍按现有边界拒绝，提示逐项准确定位。
2. 得到唯一 hit 和唯一 quote 字符区间后，直接查 renderer map。不得在此之前或之后用 Markdown heading sections、前缀扫描、字段文字重建方向，也不能要求 hit 先落在标题扫描出的合法 section。方向只能来自 map 的稳定 direction_id，必须存在于当前已绑定包，且整个 quote 区间由该同一方向的合法片段覆盖；映射缺口、越界、方向不一致必须明确拒绝，不猜测。源值即使包含真实的 `## 方向 ...` 文字也只属于 renderer 当时写入的字段，不产生新的结构方向。
   文件行号只通过 §3.6 无损快照的实际 frontmatter 边界换算到 body 行/字符区间，不搜索首个方向标题来决定 body 起点。quote 位置解析不承担方向/owner 权威。
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

只在正常 finalize 已实际确认并接受当前 body 与 map 后记录 U1 标记；metadata 构造函数不能提前声明展示完成。本次实现将既有独立 `u1.display_version` 从 1 提升为 2，表示已按 r4 的统一引用裁决、map 单一方向权威与无损接受生成并接受；不另建版本框架。现有 version=1 包也按上面的 process 通路更新，不因已有 map 就豁免。当前目标标记仍采用独立 U1 命名空间；#92 的 display_refresh_version=2/3 不构成 U1 已完成，防止错误继承其旧报告行为。未升级包保留原文件和历史校验；新报告需要先完成该受保护更新。更新后 body 未变且业务未变时保留合法原校验状态，因此不会因为加 map 就清轮数。

### 3.5 finalize 的有限接受与旧快照隔离

仅在 `_stage2_finalize.py` 的现有 Stage 2 写入 owner 内收敛一次接受步骤，不建通用框架。普通 finalize 是 U1 唯一正常接受入口；narrative refine 共享 renderer，但保持自己的第一轮→第二轮生命周期，不调用“业务新版本清轮次”分支。

顺序冻结如下：

1. 进入普通 finalize 后、候选方向与 canonical papers 组装前，深复制旧 pack、validator、render 元数据。通过 §3.6 一次读取无损受管快照，记录当前原始 body/机器头及旧绑定的实际有效性；`_contact_pack.normalize_input_pack` 的 v2 浅复制不提供嵌套隔离，不能代替此步骤。后续所有候选复用条目（包括 split children）从复制件构造。不得把同一可变 dict/list 同时放入新候选和旧比较基线。
2. 完成现有 preflight/proof、resolved acceptance、来源与引用检查；构造完整候选包，尚不写任何接受标记或文件。实际生成候选 body+map，不能因 `stage2_render_state` 投影相等跳过。
3. 分别判断四件事：
   - body 是否等价：按 §3.6 的原始字节比较，仅允许精确豁免顶部指定生成时间值；时间之外的标签、分隔符、统计文字与每一个换行字节均参与比较。等价时保留原 body 字节和真实 SHA，不能把规范化文本重新编码冒充原字节。
   - 机器头是否匹配当前包：即使 body 等价，只要 state_fingerprint 需更新，也用现有受管写入规则更新头，不能冻结整文件。
   - 业务依据是否改变：使用现有 needed_keys、成员语义重建，以及新旧方向的稳定 identity 集合、input_fingerprint/provisional_input_fingerprint、supporting_item_keys/relevant_keys/named_keys 和 accepted resolved 的语义（provisional/resolved ID、resolution_type、split/merge target、增删成员、原始输入指纹）。这些身份/许可按其现有集合或映射语义比较，忽略 applied_at。freshness 源事实改变由现有有效性指纹/needed_keys承接；不以新增派生 candidate 列表自身当作新事实。`stage2_render_state` 只可用于定位展示差异，整个投影不等不能额外成为清轮次理由。仅时间、cache、U1 标记/map、collection_key 或实际正文等价的展示投影变化不作为新业务依据；但 title/year/has_pdf 等已纳入现有 paper_digest，若使真实方向/resolve 输入指纹改变，就仍是业务变化，不能统称“仅展示”。真实输入指纹改变即使 body 等价也算改变；body 实质变化自身也足以使旧文字校验失效。
   - 旧 validator 是否原本有效：在旧快照与旧实际 body 上判断原 pack/render 绑定、合法轮次与 phase，不拿新候选去验证旧记录。业务/body 都未变而旧绑定无效时拒绝接受，不能重绑洗白。存在真实新业务或实质新正文时旧 validator 失效，但人工正文保护始终有效。
4. 写入前完成上述判断及 `managed_conflict`/人工决定处理。没有获准覆盖则返回 needs_decision，不能记 U1 成功。body 等价时用旧 body 同步必要机器头，否则写候选 body；更新实际 body 对应的 map、原始 body hash 和 U1 标记。若保留旧 body，不能把仅匹配新候选文本/时间长度的 map 写回；须由同一 renderer 的片段输出重建或调整到实际保留 body，并验证全体区间与该 body 一致，不能回头解析 Markdown 猜归属。
5. 当业务依据和 body 均未变，携带合法 validator 的 round/phase/pending/results，仅按接受的新包更新现有 pack binding；不改变 verdict。任一实质改变则新包不继承旧 validator，下一次真实校验从第一轮开始。生成时间不能成为改变；正常 narrative refine 例外按 §3.3 保留轮次。
6. 按现有顺序保存 pack/freshness cache，不新增跨文件事务；Markdown 已写但 pack 保存失败时不能返回成功或以旧包登记新报告，后续由现有绑定不一致/受管冲突路径要求恢复，绝不能补造 PASS。U1 完成元数据在内存候选中只于接受条件满足后设置，随 accepted pack 一并保存；不得让调用方先持久 stamp 再调用接受步骤。

U5 独立修改同一 finalize 接点。有限共享步骤输入为隔离的旧包/旧渲染快照、完整候选包/实际 body 及调用方已确认的业务依据变化；它负责等价判断、原有冲突处理、必要头更新及普通接受的 validator 继承/失效，不生成模型结果、不判断 U1 owner、不重新决定 resolved acceptance。具体私有函数名不作契约。先落地者完成必要局部实现；后落地者消费同一接受步骤并保留先前行为，不复制两套比较/失效逻辑。U1 无 U5 时完整可实施；U5 无 U1 时也不需此处 owner map 或 U1 标记。

### 3.6 无损受管快照：字节完整性与报告字符坐标分离

这是 U1 正常接受与校验链的局部读取契约，不是全仓 I/O 重构，也不新增文件格式/来源认证框架。

1. 从磁盘以 bytes 读取一次旧受管文件，严格按已有 UTF-8 格式解码，保留原始 file bytes、完整 frontmatter 范围/实际结束偏移、原始 body bytes 与必要已解析机器头。无效编码或不能按既有格式拆分时明确失败，不替换坏字符、不猜首个标题、不 strip body。frontmatter/body 边界按真实文件分隔行确定，保留精确行结束符；不得通过在全文 find 重复正文来反推偏移。
2. body hash、人工正文冲突判断、旧 render/validator 绑定和最终写回均使用这份原始 body bytes。字符文本只作为显示和 quote/map 定位视图；需要物理行列表时采用共同的保留行尾分行结果，行号语义沿用既有规则。LF、CRLF、裸 CR 及其他既有支持的分隔符不在完整性比较中折叠。不能使用默认 read_text 的 universal-newline 结果或丢行尾 splitlines 结果作为“原文件”。
3. 时间豁免只作用于 renderer 固定顶部生成信息行中生成时间字段的值区间。由该固定布局识别唯一位置，并要求前后固定字段合法；该值外的所有 bytes，包括前缀、分隔符和行尾，都必须相同。缺失/格式不符时不豁免，不从其他行寻找替代。来源文字中的时间、仿生成行、首个方向标题以及其他 `数据来源` 字样不参与豁免。可用同一渲染布局提供的边界逐段比较，不新增通用 Markdown 解析器或文本归一化层。
4. 仅头部需更新时，使用原始保留 body bytes 写回，不能经过文本读取再重新规范换行。实际 body 的 hash、owner map 与保存到 pack 的 render 记录必须一致。候选改写 LF 而旧 body 是 CRLF 时，非时间字节已变，不能保留旧 PASS；先按原受管人工冲突/决定规则处理，未获准覆盖不写入。
5. 普通 finalize、record-validation 的 bound-render 读取、refine-plan 的绑定读取、refine-finalize 的旧绑定/受管写入，以及这些路径调用的 managed_conflict，共享该有限读取/拆分约定，不各自重开文件取得规范化的第二份“原文”。写入前继续执行既有并发/冲突保护；本决定不建立新的锁/事务系统。Stage 2 工厂显式接线，其他 stage 不被强制迁移。
6. 旧包若只按历史规范化文本留下 hash，且该 hash 不能证明当前原始 body 的既有绑定，就如实判为不匹配。禁止因“看起来一样”自动改 header/hash 并保留旧 PASS 或 pending。依据 §3.5：无实质改变却旧绑定无效则拒绝接受；需按既有恢复/人工决定及正常接受处理，不能凭升级标记重签。原始文件、校验报告与历史记录不删除。

#### 生命周期交接（穷尽本 U1 涉及的入口，不新增产品分支）

- 普通新建/复用/展示更新：统一引用裁决 → 完整 renderer body/map → 无损旧快照接受；业务和 body 均未变且旧 validator 合法，才保留所有 round/phase/results/pending。若当前记录显式无效，停在候选阶段，不覆盖现状。
- narrative refine：只消费已接受 canonical，先验证旧快照与 map、检查全报告固定阻挡，再生成准许的 narrative 改动；更新实际 body/map/绑定而保留第一轮结果，转 awaiting_second_validation，不调用普通接受的清轮次规则。
- pending/awaiting_second_validation 包的普通 finalize：无实质变化时 pending 原样保留；实质正文或业务变化时按既有普通接受使旧 validator 失效，不能把 pending 移植到新版本，也不能凭缓存/时间/标记变化重开第一轮。
- 旧包迁移：仅 §3.4 正常 process 路径；缺 map/版本旧不反解析 owner，无损绑定失败不自动认证。升级成功只代表展示/接受语义就绪，不代表新校验 PASS。

## 4. 替代方案与取舍

- 全文正则清洗/让模型改写固定卡较短，但会误删普通八位文本、破坏原始事实和已有链接，不能满足 U1。
- 仅信 location 行号避开 quote 搜索会删掉现有合法短 location；反过来仅 quote 不查 renderer owner 会把重复文字误归。选择既有唯一 hit 解析后查结构化映射。
- 用渲染后 Markdown 前缀重建 owner 会再次被多行证据、同句混合、仿标题内容破坏。选择生成时字段归属，覆盖最终物理行与片段。
- #92 的 pack-only 双入口刷新可降低一次旧包数据准备成本，但额外需要来源可比较证明与两入口接受同步。本 U1 选择已有 process 通路，代价是旧包首次更新可能需要正常数据准备；不增加模型工作本身的失效理由，避免与 U5 索引刷新捆绑。
- 整文件冻结会留旧机器头；无条件正文重写会因时间使两轮重置。选择保留等价 body、必要更新机器头、独立判断业务依据和旧校验。

## 5. 不变量与代表性反例（静态设计说明）

1. **事实与展示分离**：句中可信 key 转成链接，机器 evidence 不动；作者原句含同一 key 也不参加这四出口的清洗。已正确链接不嵌套，未知普通八位文本不删除，明确引用缺题名先失败；当前 key 存在但 title=null 时旧有效标题也不能救回，只有当前 key 真正缺席才允许合法旧记录回退。
2. **hit 决定位置、renderer 决定 owner**：短 location=“后续论文依据”且 quote 唯一仍合法；重复 quote 配准确行号可定位；“多处”不猜。多行固定值续行仍 source，narrative 中出现“后续论文依据”前缀仍由实际字段归属决定；源字段含 `## 方向` 不建立第二套方向边界，不因字样误分类。
3. **同句混合不授予事实改写权**：禁锚卡把 quote、题名、模板、evidence 拼成同一行，命中证据或模板交对应 owner；summary 回退原文不是 narrative；混合固定/narrative blocking 零模型修订。
4. **旧基线不可被候选污染**：仅 collection_key 更新、复用 split child 或嵌套 resolved 写入都不能先改旧 pack，再借“比较没变”保留不合法绑定。
5. **四项独立**：顶部时间变化保 body/轮次；证据行包含来源分隔符但引用变化仍写新 body；摘要输入变而 body 等价时更新必要头并失效旧校验；仅加 map/U1 标记时保留合法轮次，坏旧绑定不洗白；CRLF/LF 变化、顶部生成时间以外的空白或仿来源行变化都不是时间豁免。
6. **所有生成入口保映射**：第一轮 narrative 修订后第二轮发现固定卡问题仍可定位登记；refine 的 cache 重建不能抹掉 owner map。旧无 map 包不反解析 Markdown，先按受保护 process 更新。
7. **正常失败可停**：第一轮固定失败不虚报“两轮已尽”，第二轮固定失败不重开；源/模板实际修复后才接受新版本；无变化反复运行不清次数。

这些是方案完整性检查，非新增测试矩阵、Case ID、采集器或过程认证要求。具体必测目标和检查方式见同目录 [测试计划](test-plan.md)。现有 t3 recipe 与结果保留其原适用版本；本次不修改测试计划或运行测试。后续只需由测试 owner 对受影响目标/断言的覆盖作对应修订与独立审核，不因文档 SHA 全量重跑。

## 6. 从 #92 至今吸取的设计教训

- “结构化优先”不等于禁止已有合法短 location；结构化归属应建立在现有唯一命中之后，而不是改上游报告契约。
- 修补 Markdown 前缀再修物理行仍是在反推 owner；owner 必须在生成字段时直接给定，包括同句混合及 fallback。
- 两入口各自接受造成正文/版本/轮次分叉；U1 缩到现有唯一正常 finalize 接受，后续有新入口也只消费这一步。
- 把共享 helper 放对位置仍不够；caller 在组装前共享旧 dict 会使旧证据先被污染。旧快照隔离必须早于组装和任何 mutation。
- 整 Markdown 冻结混淆 body 与机器头，时间戳变化混淆展示与业务依据。四者分别判断，既不冻结旧头，也不借生成时间清轮次。
- 已撤回的“独立篡改 header”历史反例不恢复为本计划要求；继续依赖已有正式绑定，拒绝增加防伪矩阵或重复认证设施。
- 不承诺绝对无 bug；通过先冻结真实输入、owner、兼容、失败路径和代表性反例，降低补丁链式返工。审核一次覆盖可判断的完整范围，后续仅处理语义变化及连带影响。

## 7. r4 修订影响与实施交接

### 本次取代决定与不受影响范围

r3 的业务目标、四出口范围、合法短 location、两轮上限、成员/引用许可、人工保护、正常 process 懒更新及 U1/U5 独立交付继续有效。r4 将三项曾写成原则却容许 caller 分叉的决定写成封闭机制：

1. 当前记录存在性先于字段补全，所有普通生成分支调用同一引用裁决，refine 只消费已接受记录；废止“先旧后非 None 覆盖”作为当前引用来源选择。
2. 唯一 quote hit 直接查 renderer map，map 唯一决定方向/区域/owner；废止标题 sections 作为前置方向裁决，并保留 quote/location 原契约。
3. 原始受管 bytes 决定完整性，字符视图仅决定报告坐标；统一 finalize/绑定/refine/冲突消费者，时间只豁免固定字段值，旧版本不以规范化字符串重签。

需独立审核 P1 当前事实、P2 三个权威接点与工厂接线、P3 普通/refine/pending/旧包兼容及失败影响、P4 以下实施顺序。作者状态 PENDING，不继承 r3/t3 的通过结论。未受影响证据可以由独立 reviewer 判定复用；不因纯文档 SHA 要求重跑。

### 实施顺序及责任边界

1. 计划 reviewer 独立复核本完整 r4，作者按问题直接维护唯一正文。产品仍停留在本文固定 head 的实现，不能把计划入库写成缺陷已修复。
2. 产品 owner 在 `_stage2_finalize.py` 收敛 §3.1 当前/旧记录裁决，贯通新建、reuse、展示更新及持久 canonical；render/facts/pack 保留其既有角色。先判断记录存在再验证，而不是只修一个 null 分支。纯包 refine 不新增事实读取。
3. 同一产品 owner 在既有 Stage 2 写入/读取边界建立 §3.6 无损快照，显式接入普通 finalize、validation bound-render、两个 refine 与其 managed_conflict。保留旧深复制/header-state 检查；不全仓改 I/O，不增事务/来源证明。头更新、实际 body hash/map、人工冲突与 validator 继承必须使用同一实际接受内容。
4. `_stage2_validation.py` 删除与 map 竞争的方向 sections 裁决，仅保留现有位置查找后查询 map；完整 quote 覆盖和现有方向 membership 必须检查。renderer 保持同句混合、fallback、多行及既有链接 owner 语义，不因移除 headings 而放松 excluded/卡外权限。
5. `_stage2_preflight.py` 将现有 U1 display_version 1 升为 2；只有成功普通接受保存新标记。旧业务指纹/缓存可复用，不新增模型强制失效理由。所有 cache.render 更新按 owned fields 保留同一接受版本仍有效的元数据；refine 不为保 map 恢复已失效 preflight。U5 若已有共享接受 helper 则消费同一实现，不复制两套无损比较/失效逻辑，也不把 U5 变为前置。
6. 测试 owner 后续将现有 t3 的受影响引用、定位和接受/旧包目标对应到 r4 三项机制与 §3.6 生命周期，写明尚未执行及既有结果的适用边界；不增加整仓回归、真实模型全流程、来源认证或历史 #92 矩阵。本次交付只含执行计划，不能据此声称测试计划已更新或新测试已通过。
7. 实现后由非作者核对完整变更与上述入口，不只看新增 helper；复用仍适用的旧证据，仅受影响关口重审。产品/测试实际执行需按各自授权推进，本文不自动授权运行、评论、合并或关闭 issue。

### 历史结果与当前状态

r3 批准、既有实现/修复与 t3 三关口记录保留为历史事实，链接见页首；它们不能证明本 r4 的引用 authority、方向 authority 和原始字节契约已经实施。当前 r4 是待独立复核的执行计划，本次未改产品、测试计划、测试结果或审核评论。未变需求不重新发明验证标准；后续只处理机制语义及连带影响，不承诺绝对无 bug，不以不断追加边界矩阵替代统一机制。
