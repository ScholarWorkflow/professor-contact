# Stage 2 U1 测试计划：固定证据展示与真实阻挡归属

- Test plan revision：`stage2-u1-t4`，2026-10-21；唯一正式路径 `plan/stage2-fixed-evidence/test-plan.md`。本版完整取代 t3 的当前设计与 recipe；§7–8 保留旧实际记录，不再作为相互矛盾的现行执行指令。
- 范围依据：用户 2026-10-21 授权“然后按照这个执行计划，再写完备的测试计划”；对应 [execution r4](https://github.com/ScholarWorkflow/professor-contact/blob/a2de7777786acd23aec98eaf770a04548638ff9c/plan/stage2-fixed-evidence/implementation-plan.md) §§1、3、7。保持 U1-A–F，不引入 U5/#92、安装或真实模型回归。
- 核对版本：PR107 分支 `plan/stage2-fixed-evidence-20261019`，head `a2de7777786acd23aec98eaf770a04548638ff9c`（2026-10-21 06:12 UTC）；本 head 仅发布 r4，产品/测试仍为 `cd6387759157c505acb96ed8459e0cc2fbd7f6ba` 的实现。被取代 test-plan blob `56bf20153eb4fd838552031a3914784988058bd4`。
- 规则：[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)（2026-10-09 20:37 UTC）、[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)（2026-10-19 14:02 UTC）。
- 作者状态：设计待独立审核，未自授 APPROVED/PASS。本次只修文档，未修改测试实现或执行测试。r4 三项机制尚未由本版核实实施，新增/修订断言尚未落入代码，不能拿同名旧 selector 的通过当新覆盖。
- 历史正式结论：t3 在 `cd638775` 的 [2026-10-21 04:58 UTC 独立审核](https://github.com/ScholarWorkflow/professor-contact/pull/107#issuecomment-6308427553) 已确认 G1/G2/G3 通过。该结论按原语义保留，不外推 r4；§8 中当时“待审”的记载是历史状态，已由该正式审核完成，不恢复旧阻塞。

## 1. 范围与检查方式

以下六项是本轮必测范围上限，不是要求每项再做单元、集成、真实模型三套证明。优先在既有 Python unittest/合成 Stage 2 夹具中，从现有正式 runner 入口得到返回值、`套磁候选分析.md` 和 `套磁候选输入.json`，用现有断言判断；同一场景可同时满足多项。内部 owner map、完成标记、快照算法和 helper 名称不是额外的产品验收目标，不要求单独认证其内部格式。

真实模型、Zotero 服务、PDF 下载、Codex/OpenCode 运行、安装交付均不属于 U1 改动目标；不为本次引入完整业务 smoke、双 harness 重跑或新设施。SKILL 与两个 analyzer 的停止/修订说明仅静态核对与已确定行为一致，不转成委派身份或执行过程认证。

## 2. 必测清单

### U1-A：四个固定出口等价显示可信引用

- 业务目标：固定卡 `evidence/completed_part/remaining_gap` 和禁锚卡 `evidence` 显示可信题名与 Zotero 链接，不泄漏裸引用、不改证据含义或引用许可。
- 输入/场景：一个正常 Stage 2 合成输入覆盖四个目标字段，引用在结构化候选/完成论文或显式 Zotero 引用中声明；同一正文保留一处已正确链接、一处普通数字/日期/无引用依据的八位文字。新建包及 U1-E 的旧包复用路径共用这些输入，不为每种文字排列另造矩阵。
- 预期：四字段中的实际论文引用为当前可信题名和正确目标，前后证据文字保留，已有链接不嵌套且 URL 不被二次改写；普通文字不变。持久机器证据、作者引文/译文/出处、freshness 结论不因显示转换被改写；仅为展示补 canonical 元数据不扩大 `supporting_item_keys`、`relevant_keys` 或 P/L 使用许可。
- 检查方式：正常 finalize 后分别对照固定输入逐字段比较四个出口的实际 Markdown 引用、可信题名、链接目标及相邻证据文字，并检查包内原始事实与许可集合；仅比较整篇链接出现次数不足以证明四出口均正确。纯包 narrative refine 复用 U1-D 的既有检查，不另跑真实模型。

### U1-B：实际引用缺可信元数据时交源，不编造或静默删文

- 业务目标：当前记录存在即拥有来源裁决权；当前无效题名不能被旧标题掩盖，无法解析的实际引用在写入前失败，给出可处理的数据责任。
- 输入/场景：在 U1-A 的隔离输入上，分别使实际显示引用的当前题名明确为 null（旧包有旧题名，覆盖实际 display-only 复用路径；保留已有空字符串检查），以及一个明确 Zotero 引用没有可信记录；不扩所有 key/标题格式组合。
- 预期：返回定位到 gap、字段和 key 的缺失信息，交数据准备 owner；旧正文/受管包不被接受为新成功，不造题名、不删证据、不沿用旧题名掩盖当前明确无效。当前来源未提供某记录但旧 canonical 仍有效，以及旧禁锚无完整候选列表但实际引用能解析的合法复用，按 U1-E 检查，不能一概阻断。
- 检查方式：正常 finalize 返回信息须足以定位固定输入指定的 gap、字段和 key（机器字段或可理解的错误文字均可），并比较失败前后的受管 Markdown 与输入包，确认未被覆盖或冒充成功。不新增错误码规范、采集器或来源证明。

### U1-C：合法报告按真实片段归属，保留已有定位/排除边界

- 业务目标：固定卡合法 blocking 可登记并给出 source/generator owner；实际 narrative 不因长得像模板而误归固定；原本排除区仍排除。
- 输入/场景：同一正常生成的报告包含可定位的固定源文字与模板文字，包含一个跨行源值中以真实 `## 方向 ` 开头的续行（含中文及 emoji，必须命中该续行而非前一行）、一个模板和值同一行的命中及一个 summary 缺失后回退原句的命中；用短 location 加全文唯一 quote，另用实际物理行号区分重复 quote。保留一处带模板字样的真实 narrative 对照。只选这些直接决定归属的代表性片段，不穷举换行符、字段、方向和 quote 的笛卡尔积。
- 预期：源值/回退原句交 source，确定性模板交 generator，稳定方向/gap/字段正确；允许同句涉及多个固定 owner，不因无法选唯一 owner 拒绝真实失败；真实 narrative 仍沿原权限。短 location 不被强制换成数字。歧义 quote 仍拒绝，不猜位置；用户笔记等既有排除区不变为合法固定报告目标。原 issues/notes/verdict 与原报告文件保留。
- 检查方式：比较 `stage2-record-validation` 返回和持久 validator；归属的方向、gap、字段与 source/generator 责任须对照事先确定的测试输入，不得用返回的 `rows[0]["gap_id"]` 生成自己的预期。复用既有重复 quote/短 location、用户笔记场景中适用的检查，不通过反解析标题制作第二套 owner 判定器。

### U1-D：登记失败不授权模型改事实；narrative 两轮仍可用

- 业务目标：固定 blocking 停自动修订，纯 narrative 保留一次修订、第二轮校验；minor 不升级为阻挡。
- 输入/场景：第一轮合法固定 blocking 与 narrative blocking 混合报告；另一条纯 narrative 第一轮报告完成一次正常 refine 后，第二轮首次出现固定 blocking。复用既有 minor 与 narrative later-title 合法报告场景。固定报告对两个 refine 入口各检查一次，其中使用方向过滤，确保不能绕过整报告阻挡。
- 预期：第一轮登记 `needs_correction`、round=1，明确责任；`stage2-refine-plan` 无 rewrite jobs，`stage2-refine-finalize` 不消费 rewrite 改正文。固定失败不变 pass/skipped。纯 narrative 第一轮仍产生允许修订，refine 后保留第一轮状态并等待第二轮，第二轮固定问题仍能正确定位，终态为 `fail_after_2_rounds` 而非重开轮次。minor 保持非阻挡。原两轮/顺序约束继续适用，不要求穷举非法状态组合。
- 检查方式：两 refine 入口返回、正文与 validator 前后状态；用已存在结构化 narrative rewrite 夹具而非模型生成。核对主 SKILL、Codex/OpenCode analyzer 中本次改动的“登记→交 owner 停止/修订”说明与上述分支相符即可，不加双 harness runtime。

### U1-E：旧包正常使用时更新展示，复用有效工作

- 业务目标：已有报告也得到 U1 修复，且不为展示更新强迫模型重算或引入新命令。
- 输入/场景：一份旧包缺 U1 展示完成信息，以及已有 map、`u1.display_version=1` 的旧包，有仍有效分析/freshness/narrative/resolved 资产；旧禁锚有仍有效 freshness cache 可补引用元数据。再使用同一兼容路径中无完整候选列表、但已持久完成论文/明确引用均可解析的旧包。旧包不要求来自 #92 私有版本。
- 预期：现有 preflight→process→plan→finalize 通路完成更新；仅缺 U1 展示完成信息不产生额外模型 jobs，不改变有效来源判定。有效 cache 可以补实际需要的引用；缺无用候选列表不新增阻挡，无效 cache 不被当来源猜题名。实际引用无法解析只按 U1-B 交源。接受前或冲突/失败时不能标成功；接受后的四出口正确，后续不再仅因缺 U1 信息反复 process。另一有效功能的 render 元数据不被整块抹掉。
- 检查方式：现有 preflight/plan/finalize 返回（含 jobs）、最终正文/包；复用 U1-A 与 U1-F 的观察，不另做历史版本批量迁移测试。不要求 U5 已实现或通过。


### U1-F：普通接受区分正文、业务、绑定和旧校验，保护人工正文

- 业务目标：展示/时间更新不能洗掉两轮限制或救活失效校验；真实改动不能沿用旧通过，人工正文始终受保护。
- 输入/场景：从有效旧 validator 的真实磁盘文件出发，覆盖仅固定顶部时间值变化、真实固定 evidence 变化、业务指纹变但正文等价、旧绑定单独失效、真实行尾字节变化和人工正文保护；同时利用 U1-D 已有第一轮 narrative 状态检查普通接受保留 pending，利用 U1-E 检查旧版更新不洗白状态。各场景单一变化，不组合成排列矩阵。
- 预期：body/业务都未变且旧绑定合法才保留 round/phase/pending/results；仅时间值可忽略，时间以外每个字节都参与比较。必要头更新保留实际旧 body bytes，其 hash/map 对应实际保留内容；旧绑定无效不靠重写头/hash 复活 PASS 或 pending。业务或正文实质变化使旧 validator 失效，报告文件保留。人工修改未授权覆盖时返回 needs_decision，不记录展示成功。正常 narrative refine 保留第一轮并进入第二轮，不走普通接受清轮次分支。
- 检查方式：§6.4 从磁盘 read_bytes 取证，标准 hashlib SHA256 与既有 unittest 断言足够；不以 read_text/splitlines 的规范化字符串比较作为原文件证据。检查正式 finalize、record-validation、两 refine 入口所见的相同文件及状态。只验证本次改变的无损接受链，不造全仓 I/O、来源认证或事务故障矩阵；现有写入失败记录不能误报成功。

## 3. 现有资产、实际缺口和最小映射

[当前测试文件](https://github.com/ScholarWorkflow/professor-contact/blob/a2de7777786acd23aec98eaf770a04548638ff9c/.apm/skills/professor-contact/tests/test_stage2_fixed_evidence.py) 的 `FixedEvidenceBase` 六个方法真实存在：

- A：`test_u1_a_trusted_citation_display_keeps_facts_and_licences`，四出口、相邻文字及许可已逐项检查。原结果复用；统一 resolver 若改变其实际输出，仅该受影响正常入口复核。
- B：`test_u1_b_missing_trusted_metadata_fails_before_write`，现有 title="" 和未知显式 Zotero 引用；缺当前 title=null 与真实 display-only 分支的反例、当前记录真正缺席的合法旧 fallback。按 §6.2 补同一方法，不新增通用 resolver 判定器。
- C：`test_u1_c_report_ownership_uses_real_fragments`，现有续行只是“续行仍由”，并未有真正 `## 方向 ` 源续行；已有生成链接/source 归属、混合片段及短 location 可复用。按 §6.3 替换代表性续行并检查实际字符坐标；不新增上游 schema。
- D：`test_u1_d_narrative_two_rounds_and_fixed_stop`，已覆盖两个 refine 入口固定阻挡、narrative 一次修订及第二轮固定终态、minor。保留有效证据；其正常 narrative 生命周期也是 §6.4 pending/无损读链的共用入口，不另做一套模型测试。
- E：`test_u1_e_old_pack_updates_through_process_to_finalize`，现有缺 map/标记路径，缺已有 map 的 version=1→2 与合法旧状态保留。当前测试中故意删 freshness cache 的分支验证真实缓存失效，不可据此要求所有旧禁锚必须补全候选列表或重跑模型。
- F：`test_u1_f_acceptance_separates_body_business_binding_and_validator`，t3 两个真实输入已落实；但 `document()` 使用 read_text 和 split_frontmatter，既有等价断言不能证明原始换行不被折叠。新覆盖按 §6.4 在同一现有框架用磁盘 bytes，禁止仅测 helper 字符串就关闭该目标。

既有 `test_stage2_style_validation_handoff.py` 的重复 quote/合法短 location/用户笔记排除/narrative later-title 及两轮记录，按未变化部分复用，不要求整文件重跑；`test_contact_state.py` 的 Stage 3 人工编辑用例不冒充 Stage 2 证据。BaseEnv、generate_pack、gap_override、write_report、record、preflight、bind_facts_to_preflight、finalize 和结构化 narrative rewrite 均已有；无须安装新框架。

§6 描述的是目标完整 recipe，尚有待实现的分支断言。上述名字是已有 selector，不声明它们目前已覆盖 r4；本地测试工程师落实后记录实际测试提交与对应方法/分支，独立 G2 检查前不能执行本版正式补测。若需要调整私有 fixture，限已有合成数据准备与标准断言，不创建判定服务、采集器或新矩阵。

## 4. 结果复用与影响边界

- 历史 t3 三关及 §7–8 真实执行保留。A 四出口正常目标、D 原停止/两轮目标、C 已有链接 owner、F 真实 evidence 更新/旧 validator.pack_sha 独立失效等结果，可用于未变行为；它们不证明新增 null、仿方向标题、raw bytes 或 version=1 更新。
- 本轮必需处理 B/C/E/F 中上述 r4 直接影响。D 的实际读写/绑定链改变时仅复核相关生命周期，A 的 resolver/renderer 输出改变时仅复核该正常入口；不因文档 head、helper 名称或评论变化跑全部六项、整个文件、185 项或全仓。
- 同一测试运行可证明多个目标，如 version=1 无业务变化升级保留 pending 同时支撑 E/F，refine 后固定定位同时支撑 C/D；禁止按目标逐层重复安装/运行。已有记录能证明的部分直接引用。
- 结果只标通过、业务失败、无法判断、未执行。保留所有正式尝试；不伪造新测试 PASS，不改输入求通过。临时数据/日志仅在仓库外独立 /tmp，正式可复用代码以后正常入库，本文不授权实施或运行。

## 5. 三关与下一负责人

- G1（完整设计/范围）：t4 作者 PENDING independent review。A–F 目标保持，§6 是 r4 机制的必要落点而非额外验收目标。
- G2（实际可执行 recipe）：t4 PENDING。以下完整步骤须由本地测试工程师落实到既有方法，确认真实 CLI、fixture 和断言映射。既有 selector 存在不等于新分支已实施；没有测试代码提交与映射，不宣布 G2 通过。
- G3（实际结果）：r4 受影响行为未执行/待验证；t3 原正式通过有效但适用边界见 §4。产品机制未实现或出现范围内业务失败均不能以计划完成关闭。
- 下一负责人：产品 owner 按 r4 实施；本地测试工程师仅落实 §6，独立 reviewer 评估 G1/G2；有执行授权后执行工程师按受影响 selector 定向运行，G3 reviewer 采用现有记录及新结果。作者不替审核者授予通过，不自动合并或评论。

## 6. 唯一执行说明（t4 待落实，不是已运行记录）

### 6.1 公共准备与输入边界

1. 在 PR107 实际工作树记录产品与测试提交；确认 r4 对应代码和以下断言已实现、G2 已确认、另有执行授权。沿用现有 uv/Python，不从零安装。读实际分支/工作区，保留他人并发改动。
2. 每个独立场景用现有 `_fresh_env()` 创建合成目录。沿用 `generate_pack(gap_override())`、`facts.json`、`results/freshness-DIR00001.json`、`narrative.json`、合法 preflight proof 和正常 CLI；不使用真实 Zotero、模型、PDF、全局安全配置。
3. 固定预期来源于输入：direction `DIR00001`；gap=`contact_state.quote_id(env.gap_quotes["AAAA1111"])`；实际论文 `CCCC3333`，可信题名 `Unrelated synthetic example`。观察 `套磁候选分析.md`、`套磁候选输入.json`、原始 validation JSON 和方法返回；不从返回 owner/gap 倒推期望。
4. 每次正式调用前保存相关受管文件 read_bytes；只有明确要求正常接受成功的分支才允许写入。JSON 字段断言可解析 JSON；正文完整性使用实际 body bytes。测试可按既有 frontmatter 格式拆出确切 body 边界，以 hashlib.sha256 直接核对；不调用被测等价 helper 来生成期望，不新建解析/认证框架。
5. 旧版合成包的初始化必须在调用前建立内部一致的既有 pack/render/header/map/validator 绑定，使用既有序列化与 fingerprint 工具；这是有限 fixture 准备，不允许在受测调用后补写 hash/头让坏绑定通过。只有 §6.4 的明确坏绑定场景故意不一致。实际历史失败/报告不删。

### 6.2 B：当前存在性裁决，不以新建路径替代展示路径

1. 复用已有新建四出口正常输入与未知显式引用失败检查。保留 title="" 分支。新建正常输出由 A 证明，不新增重复正常生成。
2. 在独立旧包保存合法旧 `CCCC3333` 题名、有效 freshness/narrative；使旧 U1 marker 为 version=1（保留 map），从真实 preflight 得到 process，按其 proof 绑定当前 facts。当前 facts 仍含 `CCCC3333` 记录，只把 title 设为 null，不删除 key、不用空字符串代替。实际引用仍在 evidence/旧禁锚；保持 relevant 成员/方向及有效模型输入，使调用走真实复用方向/display-only 候选，而不是人为调用 resolver 或强迫方向重建。
3. stage2-plan → stage2-finalize 使用同一 proof/results；若实际数据准备导致非展示路径，停止并由测试工程师修正该 fixture/映射后再审 G2，不能拿另一分支的失败冒充覆盖。检查现有 plan/jobs/被引用对象足以确认输入适用，不要求逐调用 trace。
4. finalize 应在任何受管写入前拒绝，错误定位 DIR00001、预定 gap、evidence（或该明确受测固定字段）、CCCC3333 并交元数据 owner；旧题名不能救回 null，不能删证据或记展示完成。MD、pack 与原报告 read_bytes 不变。具体机器错误码沿现有接口，不另造规范。
5. 在同一类但独立合法输入中，当前 papers 集合真正删去 `CCCC3333` 记录，保留已接受有效 canonical、实际显式/完成引用以及有效缓存。这才是合法旧 fallback；正常 process/finalize 成功显示原可信题名，不增 supporting/relevant/P/L，不要求补无用完整候选表。若当前 key 存在但记录无效，设计上同 null 失败，不追加所有格式枚举。纯包 refine 只消费接受的 canonical，由 D 的正常 refine 使用它，不增加 facts 获取。

### 6.3 C：真实仿标题源续行与字符定位

1. 在既有 `_attribution_env` 所用 gap override 中，把 `completed_part` 续行改为精确文本 `## 方向 假方向：中文🙂固定续行`，前一行仍有可信引用。该文本作为 freshness 源值经正常 renderer 写到真实 MD，不直接手改受管 Markdown；expected direction 仍 DIR00001，field=completed_part，owner=source。保留既有模板/源值同行、fallback summary、真实 narrative 对照，不扩大字段排列。
2. 从实际文件共同分行视图取得此唯一续行的物理行（含真实 frontmatter 偏移）；报告用短 location=`固定续行`、quote=`中文🙂固定续行`。record 应登记 needs_correction/round1，对应上述预定归属，不出现 heading 导致的 identity_mismatch，也不新建“假方向”。原报告 issues/notes/verdict 及文件字节保持；实际 pending 与固定责任一致。
3. 中文/emoji 让 UTF-8 字节偏移与字符偏移不同：用实际解码行的标准字符切片直接检查 quote 区间及对应 map 覆盖；禁止以字节下标作字符坐标。期待所有 quote 字符均属同一当前方向；不因首个 fragment 命中就忽略其余字符。此为同一反例的断言，不另做字符编码矩阵。
4. 保留现有合法短 location、重复 quote 指定实际行/歧义拒绝、excluded、生成链接/source 的适用结果。核对新 map-only 路径仍执行整个 quote 覆盖、当前 direction membership 与 excluded/repairable 守卫；现有静态实现检查足够，不为每种 map 损坏加测试。
5. 共享 D 已有正常 narrative refine 后第二轮固定命中检查，确认重绘后 map 仍可定位且不会因 owner=source 把既有 narrative later-title 误当固定区域。两 refine 入口对含固定 blocking 的整个报告保持零 rewrite（含既有方向过滤），不再复制运行。

### 6.4 F：真实 bytes、精确时间豁免、合法生命周期

以下分支在既有 F 方法/现有 D 生命周期内落实，各取一份隔离输入；不与每种状态、入口、换行交叉相乘。

1. 真实固定 evidence 改变：沿 t3 已实现步骤，generate_pack(gap_override()) 后登记空问题 pass，保存原报告 bytes；只将 freshness-DIR00001.json 目标 gap 的 evidence 从“后续由 CCCC3333 完成，日期 2024-05-01，未知 DDDD8888 与 12345678 保留。”改为同句末尾“；新增固定证据对照。”，仅删除该 gap 的隔离 freshness cache。preflight→绑定 facts→plan→finalize 应消费新结果，pack 与固定 MD 字段实际更新、可信链接仍在、旧 validator 失效、原报告 bytes 不变。不能用 user_note 改变替代。既有正式结果适用时复用。
2. 旧绑定独立失效：保留 t3 原分支，合法 pass 包仅 validator.pack_sha256 改为64个0，其余 body/header/facts/results/validator 不动。正常 finalize 拒绝（现有 validation_render_stale），调用前后 MD/pack/facts/原报告 bytes 不变，不能自动重绑。原有效结果复用，不追加独立篡改 header 的认证矩阵。
3. 真正时间差：既有标准 mock/固定时钟让两次正常 renderer 顶部生成时间值确实不同，其他输入不变；不要靠快速连续运行“可能秒数不同”。正常 finalize 成功，旧 body bytes 完全保留、SHA 与实际 body 相等；合法 validator 的 round/phase/pending/results/verdict 保留，必要新 pack binding 正确。若需要头更新，沿既有非业务 metadata 的合法候选变化准备，实际 body 必须仍相同；不能通过把坏旧 validator 头伪造正确证明保留。用 C 的一个固定 quote 在实际保留正文中定位，证明 map 不是只匹配候选时间文本。
4. 精确豁免的反面直接沿用已有顶部非时间来源文字、用户笔记仿生成行变化分支；改后不是等价时间，不得保留旧通过。检查实现只豁免固定顶部时间值而非“首个 ## 前任意来源行”，缺失/格式不符不从别处找替代；无需补所有畸形布局组合。
5. 原始磁盘差异：先 generate_pack 并登记合法 pass，再用 read_bytes/write_bytes 只将 body 的 LF 换为 CRLF，保留 frontmatter 原字节和原 pack/hash/报告，不主动重签。标准 bytes 断言确认确有差异，按相同 UTF-8 文本规范化会相同但这不能成为期望。正常 finalize 必须拒绝沿用旧校验，不能把 header/hash 修复后返回成功；record-validation 对该文件同样不能接受新成功。保存调用前后文件字节，未获人工覆盖时不得写 body 或 v2 成功标记。已有手改保护仍可报告 needs_decision，旧校验绑定失败可报告原绑定错误，均不得冒充 PASS。
6. 不丢末尾字节：另取同类有效包，仅移除最后一个真实 body 换行字节，其余字节不动；通过现有 refine-plan 与 refine-finalize（配合法 narrative 第一轮报告/结构化 rewrite 输入）观察旧绑定被拒绝、零重写、不得转 awaiting_second_validation。此单一代表覆盖另一对实际读取入口及 splitlines 丢末尾问题，不再与 CRLF×所有入口组合。错误输出应区分绑定不一致，不能用根本未登记报告或无结果文件产生的早期错误充当证据。
7. 合法 pending：沿 D 第一轮纯 narrative 报告得到合法 round1/pending，先作无业务/非时间正文变化的普通 finalize，pending/results/phase 原样保留；正常 refine 后仍 round1、awaiting_second_validation，原报告保留；再作等价普通 finalize 不清第二轮等待，不把 pending 移植到新版本。复用同一流程完成 D 的第二轮固定 fail_after_2_rounds。若业务/body 实质变化则按既有接受使旧 validator 失效，不强求其 pending 保留。
8. 对原本内部一致、原始 body 为 CRLF 的兼容 fixture，与新 renderer 的 LF 候选相比较时必须认定非时间正文变化，不能假称 body 相同保旧 PASS；依原有人工冲突/决定处理，未获覆盖不写，获准正常接受也不得继承旧通过。此兼容观察可与 E 的旧版 raw-hash 分支共用，不新增通用换行格式保证或产品输出格式要求。历史规范化 hash 与实际 raw body 不匹配的旧包不得自动更新 hash 留住 PASS/pending，保留旧文件/报告。

### 6.5 E：旧版入口、实际接受与标记

1. 复用既有缺 map/marker 的懒更新，输入保留合法分析/freshness/narrative/resolved；没有来源失效时 plan 无新增模型 jobs。保留有效缓存补实际引用与“缺无用候选表但实际引用合法”的观察，不把模型全跑作为升级步骤。
2. 新的必要兼容输入是已有 map 且 U1 display_version=1 的内部一致旧包；真实 preflight 应 process，理由包含展示更新；真实业务失效理由不得被展示理由覆盖。正常 plan/finalize 接受后才记2，实际 body/hash/map 与文件相符，其他 render 元数据保留。后续 preflight 不再仅因标记落后重复 process。
3. 若正文/业务未变、旧绑定合法，原 validator round/phase/pending/results 保留，直接共用 F 的生命周期结果；若只升级版本但原始绑定无效，拒绝自动重签，旧包/MD/历史报告保留，不记2。F 的 CRLF/末尾变化已足够证明原始绑定失败，不再新造所有旧状态组合。
4. B 元数据拒绝或已有人工冲突时不得提前写完成标记；只在真正 accepted pack 中完成。成功升级不等于校验 PASS。此目标无 U5、Stage3 或其他 PR 前置。

### 6.6 定向运行、证据、失败与停止

本版未运行。落实并经 G2 后，从既有六个真实 selector 中选择实际受影响且无可复用证据者；不发明尚不存在的新 selector。当前预期需要补的 B/C/E/F 对应 §3 的原方法，D/A 只按 §4 连带影响决定；映射未落实先记未执行。每次运行只需标准 unittest 日志、实际产品/测试提交、退出码、所覆盖的上述场景与关键失败/成功断言，不要求逐调用账本。

```sh
set -eu
REPO_ROOT="$(git rev-parse --show-toplevel)"
RUN_DIR="$(mktemp -d /tmp/pr107-u1-t4.XXXXXX)"
printf 'HEAD=%s
' "$(git rev-parse HEAD)" > "$RUN_DIR/version.txt"
cd "$REPO_ROOT/.apm/skills/professor-contact/tests"
# 仅示例已有 B selector；执行者依 G2 的真实映射替换为受影响 selector，
# 一次命令可列多个需测方法，不重复运行同一覆盖。
if uv run --no-project python -m unittest -v   test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_b_missing_trusted_metadata_fails_before_write   > "$RUN_DIR/results.log" 2>&1; then
  cat "$RUN_DIR/results.log"
else
  result=$?
  cat "$RUN_DIR/results.log"
  exit "$result"
fi
```

预期所选方法逐项 ok、退出0且所要求分支断言确已执行；skip/旧方法缺断言不能算通过。不要求固定测试数量。代码尚未实现、fixture 不能到达目标路径、环境问题分别记未执行或无法判断，不以旧 CI 绿替代。业务断言失败保留证据交产品 owner，不改预期重采样；已确认外部启动/依赖/临时目录故障、无业务失败和副作用且条件未变时最多补试一次并保留两次记录。修订输入/代码/配置需重审受影响步骤，不属同条件重试。全部清单取得当前有效结果后结束，不增加合并前全仓回归。

## 7. 执行结果（2026-10-20）

> 历史原文边界：以下 §7–8 保留当时记录；其中“本版”“当前”“§6.3/§6.4/§6.5”等指 [t3 当时版本](https://github.com/ScholarWorkflow/professor-contact/blob/cd6387759157c505acb96ed8459e0cc2fbd7f6ba/plan/stage2-fixed-evidence/test-plan.md)，不是 t4 的执行指令或新结果。当前状态唯一以本版 §4–5 为准；t3 待审已由页首链接正式三关记录完成。

- 产品与测试版本：初始实现 `2b813fc`；IR-U1-1/IR-U1-2 修复后为 `3d6c2bc`（产品代码只改 `_stage2_render.py`，测试只改 `test_stage2_fixed_evidence.py`）。以下按轮次标注；最终六项、既有 185 项与全仓回归均在 `3d6c2bc` 上重跑，日志在 `/tmp/u1-fixed-evidence/`。
- 环境：仓库现有 `uv run --no-project python`（CPython 3.14.6），沿用既有合成夹具；无新增安装、模型调用、Zotero/PDF 下载或双 harness 运行。
- 第 1 步静态编译：退出码 0，无输出（`/tmp/u1-fixed-evidence/u1-af.log` 同轮执行）。
- 第 2 步 U1-A 至 U1-F：`Ran 6 tests in 7.977s`、`OK`；六个方法逐项通过：
  - U1-A `test_u1_a_trusted_citation_display_keeps_facts_and_licences` PASS。
  - U1-B `test_u1_b_missing_trusted_metadata_fails_before_write` PASS。
  - U1-C `test_u1_c_report_ownership_uses_real_fragments` PASS。
  - U1-D `test_u1_d_narrative_two_rounds_and_fixed_stop` PASS。
  - U1-E `test_u1_e_old_pack_updates_through_process_to_finalize` PASS。
  - U1-F `test_u1_f_acceptance_separates_body_business_binding_and_validator` PASS。
- 第 3 步既有适用检查：第一次正式尝试 `Ran 185 tests` 出现 1 个执行错误 `test_contact_state.Issue67ProfessorLocalStage4Tests.test_07_professor_dir_outside_the_program_writes_nothing_anywhere`；该用例使用固定的 `/tmp/issue67-outside` 路径，与同时运行的全仓回归共享目录，错误是 `FileNotFoundError`，不是业务断言失败。保留该次尝试，待全仓回归结束后单独重跑：`Ran 185 tests in 157.472s`、`OK`。受影响范围仅此环境冲突，不改变六项结论。
- 第 4 步全仓回归（补充）：`Ran 1036 tests in 339.171s`、`OK (skipped=1)`，退出码 0；日志 `/tmp/u1-fixed-evidence/full-suite.log`。既有 `test_stage01_caller_contract` 也通过，SKILL/analyzer 文本与调用方约定一致。
- 未执行项：无（六个必测项均已执行）。无法判断项：无；第 3 步首次并发冲突已由同条件单独重跑排除。
- 记录后追加（修复前轮次）：U1-F 增加一条来源行逐字比较断言，同方法随六项重跑 `Ran 6 tests in 11.915s`、`OK`（日志 `/tmp/u1-fixed-evidence/u1-af-rerun.log`）；该轮早于裸 Zotero URI 修复，仅作历史保留。
- CI 合同：新测试模块 `test_stage2_fixed_evidence` 已登记到 `plan/test-grouping/shards.json` 的 shard4（stage2）；`uv run --no-project python scripts/check_test_shards.py` 输出 `OK: 79 test modules across 4 shards`。
- 修复后复验（`3d6c2bc`）：U1-A 至 U1-F `Ran 6 tests in 19.545s`、`OK`（日志 `/tmp/u1-fixed-evidence/u1-af-3d6c2bc.log`），六个方法逐项仍 PASS；相关既有检查 `Ran 185 tests in 125.995s`、`OK`（日志 `/tmp/u1-fixed-evidence/u1-existing-rerun-2.log`）；全仓回归 `Ran 1036 tests in 514.323s`、`OK (skipped=1)`、退出码 0（日志 `/tmp/u1-fixed-evidence/full-suite-2.log`）。
- 实现符合性审核：首次审核 `2b813fc` 结论为部分完成（IR-U1-1 裸 Zotero URI、IR-U1-2 来源行测试证据区分力）；`3d6c2bc` 修复后同一专用代理复核，两项均关闭、未发现新问题，就这两项及直接影响判完整。记录见 [implementation-review-2026-10-20.md](implementation-review-2026-10-20.md)；不代表计划、测试或合并关口批准。
- CI（GitHub Actions run `39454862151`，head `4109bfb`）：shards shard1/shard2/shard3/shard4 均 pass，聚合 job `test` pass；`issue74-formal` 为既有 skipping。
- 复用说明：本次没有可沿用的 U1 产品结果；既有 T4/T5、preflight、resolved-direction 结果只按本候选直接相关的测试方法重跑，不把历史结果外推到新实现。
- 范围说明：本记录只报告测试执行事实，不批准计划或测试关口；计划审核、测试计划审核与合并审核仍由各自负责人给结论。本地执行工程师已同步 `SKILL.md` 与两个 analyzer 的“登记→交 owner→停止/修订”说明，未改委派结构或 style-validator 格式。


## 8. t3 修订后的证明状态（2026-10-21）

- t2 已在原 U1-A/B/C 方法内补齐四出口逐项对照、失败返回的固定 gap/字段定位及不从返回值自造期望归属；实际代码已提交。`1fe59bce356a8c75fe45fe2367cb55690c276081` 的 [CI 第 39466214174 次运行](https://github.com/ScholarWorkflow/professor-contact/actions/runs/39466214174)在第四测试组执行 A/B/C，三项均为 `ok`；同组 D/E/F 旧方法亦 `ok`，组总计 249 项、跳过 1 项，整体成功。这是当前已发生的结果，可以直接复用，不再要求 §6 原 t2 三项单跑。
- 本版确认 U1-F 旧代码中修改 `facts.directions[].user_note` 的分支不能证明固定证据正文变化；把人工文字追加到 Markdown 的分支不能证明业务与正文不变时的旧绑定独立失效。两个既定场景已按 §6.3、§6.4 落入同一方法（`9b8162a`），未改产品代码；A/B/C 不重跑，D/E 复用。U1-F 当前不再记为“待补”，但第三关整体是否通过仍由独立审核确认。
- U1-F 定向执行（2026-10-21，提交 `9b8162a4f78b1f899bec6adf3b2365b232fb5cce`）：在工作树 `.apm/skills/professor-contact/tests` 运行 `uv run --no-project python -m unittest -v test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_f_acceptance_separates_body_business_binding_and_validator`；结果 `Ran 1 test in 3.366s`、`OK`、退出码 0，无 `FAIL/ERROR/skipped`；日志 `/tmp/pr107-u1-t3.BMScab/u1-f.log`。场景一的新固定证据写入受管 Markdown 与包、旧报告字节不变、旧 validator 不再作为当前通过；场景二仅坏旧绑定被 `validation_render_stale` 拒绝且包、Markdown、事实和旧报告字节未变。
- 实现缺陷修复（2026-10-21，`eebbb87`）：用户笔记可渲染出与顶部来源行同形的 `> timestamp ｜ 数据来源：...`；原比较对每行删除日期，导致笔记日期改变被误判正文等价。现将豁免限定在首个 `##` 之前的顶部来源行，其他行逐字比较；同一 U1-F 方法新增该回归场景。`eebbb87` 上 U1-F `Ran 1 test in 8.281s`、`OK`，U1-A 至 U1-F `Ran 6 tests in 22.865s`、`OK`，均退出码 0；日志 `/tmp/pr107-u1-defect.4wUS95/u1-f.log`、`/tmp/pr107-u1-defect.MNtpfD/u1-af.log`。产品代码在 `3d6c2bc` 后新增该修复，最终 head 的实现审核需覆盖 `_stage2_finalize.py` 该分支。
- 实现缺陷修复（2026-10-21，`56486a8`）：固定证据转换原先把题名和自动生成链接整段标为 source。现按片段输出：可信题名保留 source，`[`、`](...)` 及 Zotero 地址为 generator；已有 Markdown 链接保持 source。U1-C 新增缺口证据链接和禁锚证据链接两个回归。`56486a8` 上 U1-C `Ran 1 test in 2.517s`、`OK`，U1-A 至 U1-F `Ran 6 tests in 10.449s`、`OK`，均退出码 0；日志 `/tmp/pr107-u1-owner.ykK9dW/u1-c.log`、`/tmp/pr107-u1-owner.fpMshq/u1-af.log`。
- t3 修改唯一正式测试计划及同一 U1-F 方法的两个场景输入，未改产品、配置或环境；后续 `eebbb87` 只修 `_stage2_finalize.py` 与 U1-F 回归场景，`56486a8` 只修 `_stage2_render.py` 与 U1-C 回归场景。§7 的 2026-10-20 原始尝试、并发临时目录错误、复验与全仓回归记录保持原样，不用后续结论覆盖历史记录；正式第二、第三关及合并仍独立审核。

