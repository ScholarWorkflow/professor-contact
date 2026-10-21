# Stage 2 U1 测试计划：固定证据展示与真实阻挡归属

- Test plan revision：`stage2-u1-t5`，2026-10-21；唯一正式路径 `plan/stage2-fixed-evidence/test-plan.md`。本版完整取代 t4 与 t3 的当前设计与 recipe；§7–8 保留旧实际记录，不再作为相互矛盾的现行执行指令。
- 范围依据：用户 2026-10-21 授权“然后按照这个执行计划，再写完备的测试计划”；对应 [execution r5](https://github.com/ScholarWorkflow/professor-contact/blob/7c759ac9ea26508d1f130ddd482e55f9694e9957/plan/stage2-fixed-evidence/implementation-plan.md) §§1、3、7。保持 U1-A–F，不引入 U5/#92、安装或真实模型回归。
- 核对版本：PR107 分支 `plan/stage2-fixed-evidence-20261019`，head `7c759ac9ea26508d1f130ddd482e55f9694e9957`（2026-10-21 07:25 UTC）；本 head 已发布 r5，产品/测试仍为 `cd6387759157c505acb96ed8459e0cc2fbd7f6ba` 的实现。被取代 test-plan blob `656463c8568650e45d35c1f35366cb285f5c7d0f`。
- 规则：[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)（2026-10-09 20:37 UTC）、[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)（2026-10-19 14:02 UTC）。
- 作者状态：设计待独立审核，未自授 APPROVED/PASS。本次只修文档，未修改测试实现或执行测试。r5 四项机制尚未由本版核实实施，新增/修订断言尚未落入代码，不能拿同名旧 selector 的通过当新覆盖。
- 历史正式结论：t3 在 `cd638775` 的 [2026-10-21 04:58 UTC 独立审核](https://github.com/ScholarWorkflow/professor-contact/pull/107#issuecomment-6308427553) 已确认 G1/G2/G3 通过。该结论按原语义保留，不外推 r5；§8 中当时“待审”的记载是历史状态，已由该正式审核完成，不恢复旧阻塞。

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
- 输入/场景：从有效旧 validator 的真实磁盘文件出发，覆盖仅固定顶部时间值变化、真实固定 evidence 变化、业务指纹变但正文等价、旧绑定单独失效、真实行尾字节变化、最新标记下预检拒绝错误复用和人工正文保护；同时利用 U1-D 已有第一轮 narrative 状态检查普通接受保留 pending，利用 U1-E 检查旧版更新不洗白状态。各场景单一变化，不组合成排列矩阵。
- 预期：body/业务都未变且旧绑定合法才保留 round/phase/pending/results；仅时间值可忽略，时间以外每个字节都参与比较。必要头更新保留实际旧 body bytes，其 hash/map 对应实际保留内容；旧绑定无效不靠重写头/hash 复活 PASS 或 pending。业务或正文实质变化使旧 validator 失效，报告文件保留。人工修改未授权覆盖时返回 needs_decision，不记录展示成功。正常 narrative refine 保留第一轮并进入第二轮，不走普通接受清轮次分支。
- 检查方式：§6.5 从磁盘 read_bytes 取证，标准 hashlib SHA256 与既有 unittest 断言足够；不以 read_text/splitlines 的规范化字符串比较作为原文件证据。检查真实 preflight（最新标记下的快速复用）、正式 finalize、record-validation、两 refine 入口所见的相同文件及状态。只验证本次改变的无损接受链，不造全仓 I/O、来源认证或事务故障矩阵；现有写入失败记录不能误报成功。

## 3. 现有资产、实际缺口和最小映射

[当前测试文件](https://github.com/ScholarWorkflow/professor-contact/blob/a2de7777786acd23aec98eaf770a04548638ff9c/.apm/skills/professor-contact/tests/test_stage2_fixed_evidence.py) 的 `FixedEvidenceBase` 六个方法真实存在：

- A：`test_u1_a_trusted_citation_display_keeps_facts_and_licences`，四出口、相邻文字及许可已逐项检查。原结果复用；统一 resolver 若改变其实际输出，仅该受影响正常入口复核。
- B：`test_u1_b_missing_trusted_metadata_fails_before_write`，现有 title="" 和未知显式 Zotero 引用；缺当前 title=null 与真实 display-only 分支的反例、当前记录真正缺席的合法旧 fallback。按 §6.2 以不参与成员和模型输入的 EEEE4444 显式引用补当前 null；合法 absent 回退与 D 生命周期合并，不依赖跨方法状态，不新增通用 resolver 判定器。
- C：`test_u1_c_report_ownership_uses_real_fragments`，现有续行只是“续行仍由”，并未有真正 `## 方向 ` 源续行；已有生成链接/source 归属、混合片段及短 location 可复用。按 §6.3 替换代表性续行并检查实际字符坐标；不新增上游 schema。
- D：`test_u1_d_narrative_two_rounds_and_fixed_stop`，已覆盖两个 refine 入口固定阻挡、narrative 一次修订及第二轮固定终态、minor。保留有效证据；其正常 narrative 生命周期也是 §6.4 pending/无损读链的共用入口，新增合法 absent 回退在该方法内独立准备，不另做一套模型测试。
- E：`test_u1_e_old_pack_updates_through_process_to_finalize`，现有缺 map/标记路径，缺已有 map 的 version=1→2 与合法旧状态保留。当前测试中故意删 freshness cache 的分支验证真实缓存失效，不可据此要求所有旧禁锚必须补全候选列表或重跑模型。
- F：`test_u1_f_acceptance_separates_body_business_binding_and_validator`，t3 两个真实输入已落实；但 `document()` 使用 read_text 和 split_frontmatter，既有等价断言不能证明原始换行不被折叠。新覆盖按 §6.5 在同一现有框架用磁盘 bytes，禁止仅测 helper 字符串就关闭该目标。

既有 `test_stage2_style_validation_handoff.py` 的重复 quote/合法短 location/用户笔记排除/narrative later-title 及两轮记录，按未变化部分复用，不要求整文件重跑；`test_contact_state.py` 的 Stage 3 人工编辑用例不冒充 Stage 2 证据。BaseEnv、generate_pack、gap_override、write_report、record、preflight、bind_facts_to_preflight、finalize 和结构化 narrative rewrite 均已有；无须安装新框架。

§6 描述的是目标完整 recipe，尚有待实现的分支断言。上述名字是已有 selector，不声明它们目前已覆盖 r5；本地测试工程师落实后记录实际测试提交与对应方法/分支，独立 G2 检查前不能执行本版正式补测。若需要调整私有 fixture，限已有合成数据准备与标准断言，不创建判定服务、采集器或新矩阵。

## 4. 结果复用与影响边界

- 历史 t3 三关及 §7–8 真实执行保留。A 四出口正常目标、D 原停止/两轮目标、C 已有链接 owner、F 真实 evidence 更新/旧 validator.pack_sha 独立失效等结果，可用于未变行为；它们不证明新增 null、仿方向标题、raw bytes 或 version=1 更新。
- 本轮必需处理 B/C/E/F 中上述 r5 直接影响，并将合法 absent 回退与 D 的 pending/refine 生命周期合并落实；A 的 resolver/renderer 输出改变时仅复核该正常入口；不因文档 head、helper 名称或评论变化跑全部六项、整个文件、185 项或全仓。
- 同一测试运行可证明多个目标，如 version=1 无业务变化升级保留 pending 同时支撑 E/F，refine 后固定定位同时支撑 C/D；禁止按目标逐层重复安装/运行。已有记录能证明的部分直接引用。
- 结果只标通过、业务失败、无法判断、未执行。保留所有正式尝试；不伪造新测试 PASS，不改输入求通过。临时数据/日志仅在仓库外独立 /tmp，正式可复用代码以后正常入库，本文不授权实施或运行。

## 5. 三关与下一负责人

- G1（完整设计/范围）：t5 作者 PENDING independent review。A–F 目标保持，§6 是 r5 机制的必要落点而非额外验收目标。
- G2（实际可执行 recipe）：t5 步骤已由本地测试工程师落入既有方法，初版 `3766eb2`、审核修正 `9735d42`；方法映射、符合性审核和 CI 证据见 §6.7。独立 reviewer 尚未对该修正评估 G2，本计划不自行宣布通过。
- G3（实际结果）：r5 受影响行为未执行/待验证；t3 原正式通过有效但适用边界见 §4。产品机制未实现或出现范围内业务失败均不能以计划完成关闭。
- 下一负责人：产品 owner 按 r5 实施；本地测试工程师已完成 §6 落实（§6.7），独立 reviewer 评估 G1/G2；有执行授权后执行工程师按受影响 selector 定向运行，G3 reviewer 采用现有记录及新结果。作者不替审核者授予通过，不自动合并或评论。

- t5 修订说明：承认 t4 中 B 的 display-only 夹具、F 的时钟/合法旧绑定准备仍是要求而非完整步骤；首轮 record 负例原写法会混入终态拒绝，r5 的最新标记预检快路径尚未覆盖。本版只将这些既定目标补成具体 recipe，取代相应模糊指令，不增加业务范围。r5 正式设计批准见 [2026-10-21 审核](https://github.com/ScholarWorkflow/professor-contact/pull/107#issuecomment-6310235505)，不等于实现或测试通过。

## 6. 唯一执行说明（t5；分支已落入测试代码，尚未正式执行）

本节把每个受影响目标展开为可落实的夹具、调用和断言，不把“测试工程师自行补一个能命中的场景”当作完成。沿用 `test_stage2_fixed_evidence.FixedEvidenceBase` 六个方法和现有辅助函数；本节括号中的 B-null、F-preflight 等只是文档分支名，不是声称已经存在的 unittest selector。测试工程师把步骤放入对应既有方法的隔离 `_fresh_env()` 分支；不新建框架、采集器或产品判定器。实际提交、方法映射与 CI 观察见 §6.7；正式执行仍需执行授权。

### 6.1 公共准备、实际接口与字节观察

1. 当前读取基线为 `7c759ac9ea26508d1f130ddd482e55f9694e9957`，产品仍是 `cd638775` 实现；执行计划已是 r5。本节分支已落入测试代码，提交 `3766eb2` 与审核修正 `9735d42`（§6.7），独立 G2 仍需核对；产品负责人完成 r5 的受影响实现后，执行工程师才进入正式补测。本文步骤未正式执行，也不授予执行权限。沿用现有 uv/Python/unittest、仓库外 `TemporaryDirectory`；无安装、模型、Zotero 或 PDF 请求。
2. 每个标明“独立环境”的分支从 `env = self._fresh_env()` 开始，使用 `env.generate_pack(env.gap_override(), ...)` 返回 `facts_path, results, proof`。目录均由现有 BaseEnv 创建：`env.prof_dir / contact_state.ANALYSIS_MD` 是受管 Markdown，`env.prof_dir / contact_state.INPUT_PACK` 是 JSON 包，`env.prof_dir / contact_state.FRESHNESS_CACHE` 是 freshness cache；`results / 'freshness-DIR00001.json'`、`results / 'narrative.json'` 是合成结果。不得引用真实教授目录。
3. 固定业务预期为 direction `DIR00001`；gap A = `contact_state.quote_id(env.gap_quotes['AAAA1111'])`，gap B 同理取 BBBB2222。正常引用 CCCC3333 的可信题名为 `Unrelated synthetic example`，链接为 `[Unrelated synthetic example](zotero://select/library/items/CCCC3333)`。这些预期来自夹具输入，不从被测返回的 owner/map/gap 反推。
4. 真实入口统一用现有 `run_cli`（它启动子进程）和 `parse`。不在父进程 patch 时钟后假定 CLI 子进程会继承 mock。使用以下已有调用，不私调 resolver 代替用户路径：
   - preflight：`env.preflight()`，其实际参数为 `stage2-preflight --program-root <env.root> --professor '試験 教授' --target-file <prof_dir/套磁目标.json> --paper-analysis relevant --gap-scope selected_direction --freshness-scope shortlist`。
   - 需要新 proof 时：`proof, payload = env.save_preflight('<场景名>-preflight.json')`，随后 `env.bind_facts_to_preflight(facts_path, payload)`；再 `parse(run_cli('stage2-plan', '--facts', facts_path, '--preflight-file', proof))`。
   - 普通接受：`env.finalize(facts_path, proof, results)`，不省略真实 proof、不手写 preflight_id。
   - 报告：`report = env.write_report('<场景名>.json', issues)`；`env.record(report)` 实际调用 `stage2-record-validation --professor-dir ... --validation-file ...`。
   - 纯包修订：`env.refine_plan(report, ...)`、`env.refine_finalize(rewrite_dir, report, ...)`，均用 `--professor-dir`，不需要新 facts。`env.write_narrative_rewrite('纯叙事待改文字', '纯叙事已改文字')` 生成已有合法结构化结果。
5. 本节涉及正文完整性的断言一律直接读取磁盘 bytes，不用现有 `env.document()` 的 read_text 结果。夹具初始文件是现有 renderer 生成的 LF frontmatter：确认 bytes 以 `b'---\n'` 开头；找到其第一个关闭分隔 `b'\n---\n'`（从第 4 字节开始），加上该分隔长度并跳过其后 renderer 固定的一个 `b'\n'`，所得偏移为本夹具 body 起点。保存 `header_bytes` 与 `body_bytes`。后续本节的 CRLF/末尾变动只改这个 body，不改 frontmatter。此有限夹具切片不是另造生产解析器，严禁全文搜索 body 文本推偏移。`hashlib.sha256(body_bytes).hexdigest()` 是独立摘要预期；字符/物理行定位另用 `body_bytes.decode('utf-8').splitlines(keepends=True)`。
6. 每次被测调用前保存 MD、pack、facts、freshness cache 和本分支原始报告（存在者）的 bytes。明确要求零写入时逐个比较，不只比较 body。未创建的目标记录为不存在，调用后仍不得出现。报告的 `issues/notes/verdict` 用原报告 bytes 保留证明，不重建报告使之匹配结果。正常成功只允许既定受管接受写入；模型结果文件、原始报告不得变化。
7. 仅在构造“内部一致历史输入”的明确步骤中，允许准备旧 body/marker 和对应已有 hash。除下面 E-v1 明确保留真实校验的特例外，顺序固定为：先 `generate_pack`（初次生成本来没有 validator，不从已登记包随意删除校验）→ 改指定旧 body 或 marker → 计算实际 body bytes hash → 更新 `cache.render[ANALYSIS_MD].sha256` 和已有 `ownership.body_sha256`（map 的行/字符片段保留，下面变动不改变其正文行/字符坐标）→ 用 `contact_state.render_frontmatter(contact_state.stage2_pack_state_fingerprint(pack), raw_hash).encode('utf-8') + body_bytes` 写盘 → `env.write_pack(pack)` → 如需有效校验，必须通过真实 `env.record(...)` 登记。E-v1 的 marker 历史构造另按 §6.4 的明确顺序，必须保留由真实 record 得到的校验而非重新提交旧版报告。不能直接填一个 PASS validator，不能在受测调用后修 hash，不改 direction fingerprint、freshness fingerprint 或权限集合凑通过。记录完成后的负例只改明确指定对象，其余绑定保持原样。

### 6.2 A/B：四出口及当前记录存在性，明确走到复用分支

**A 正常出口**：保留既有 A 方法完整输入和逐行断言，不再列链接总数替代覆盖。实际期望包含：evidence 的“后续由 [可信链接] 完成，日期 2024-05-01，未知 DDDD8888 与 12345678 保留。”；completed_part 第一行已有正确链接与第二行裸引用各正确显示；remaining_gap 中裸 key 和裸 Zotero URI 各显示一次；BBB 禁锚的 completed_by 与 evidence 各正确显示。前后源文字、作者 quote/translation/source/page/status/confidence、`supporting_item_keys=['AAAA1111','BBBB2222','CCCC3333']`、`relevant_keys=['AAAA1111','BBBB2222']`、空 `narrative_later_papers` 保持。保留现有对机器 evidence 原文的精确比较。新 resolver/renderer 改到这些出口时运行 A；否则引用既有 t3 结果而不额外重跑。

**B-new 已有失败**：保留 B 原 title="" 及未知 Zotero 链接/URI ZZZZ9999 三段真实准备和断言，分别已有受管文件不变/新建目标仍不存在；错误定位 gap A、evidence、实际 key、DIR00001。它们证明普通失败，不冒充下面的 display-only 反例。

**B-null 与 B-absent 使用一个不参与模型输入的实际显示引用**：不能直接删 CCCC3333 再声称 freshness/成员没变。为避免 title 变化造成不同业务分支，B-null 放在既有 B 方法；B-absent 与 D-pending 合并放在既有 D 方法，只运行一次且不依赖 B 方法的执行顺序。两者各自建立隔离环境，按以下确定输入准备：

1. 在 `mutate_facts` 中往 `facts['papers']` 增加 `{'item_key':'EEEE4444','title':'Obsidian atlas archival reference','year':1900,'authors':[],'authorship':'unknown','has_pdf':False}`；不放入任何 direction 的 member/relevant/named 集合，不给 analysis/sidecar/facts 路径。年份早于两条源论文，题名与现有题名不重叠，因此既不是后续 freshness candidate，也不形成版本家族。
2. 只把 `gap_override()['AAAA1111']['evidence']` 设为精确文本 `显示参考 zotero://select/library/items/EEEE4444，证据原句保留。`；`candidate_paper_ids` 仍为 CCCC3333，其他字段和 BBB 结果不变。正常 `generate_pack(overrides, mutate_facts=...)` 成功后断言 pack.papers 含 EEEE4444、四出口实际 evidence 为 `- 后续论文依据：显示参考 [Obsidian atlas archival reference](zotero://select/library/items/EEEE4444)，证据原句保留。`，成员/许可仍与 A 一致。这样 EEEE4444 是显式显示引用，不是假造新业务成员。
3. 把已有 `cache.render[ANALYSIS_MD].u1.display_version` 改为1，保留 ownership 和全部实际正文；尚无 validator，按 §6.1(7) 保存一致旧输入。保存原 direction 的 `input_fingerprint/provisional_input_fingerprint`、narrative、gap_shortlist、completed_gap_blacklist 和 freshness cache bytes。
4. B-null：当前 facts 中 EEEE4444 记录仍存在，只把其 `title` 设 null。B-absent：另一独立环境从 facts.papers 列表删除 EEEE4444 整条记录；保留已接受 canonical。两者都不改 `_index.json`、源论文、候选列表、cache/fingerprint/旧标题。调用真实 save_preflight → bind facts → stage2-plan；断言 preflight 为 process 且含 fixed_evidence_display_update，plan status=ok、jobs=[]、write_needed=false。为明确命中旧方向 reuse，在测试准备中读取已有 `contact_state.Stage2Context(facts_path).direction_plans`，只断言 DIR00001 的 `reuse is True`，其真实 fingerprint 等于旧 provisional（或没有 provisional 时的 input）fingerprint；不改这个值、不收集完整调用轨迹。这是待测复用分支的局部前置断言，不是以实现产生业务预期。
5. B-null 正常 finalize 预期 `missing_paper_reference_title`，direction=DIR00001、gap_id=gap A、field=evidence、item_key=EEEE4444；status不能ok，输出指出无可信题名；pack/MD/facts/cache bytes 不变，旧 marker仍1，旧题名不能成为成功结果。若失败是 preflight drift、fixture/schema错误或缺模型结果，不算本目标通过。
6. B-absent 正常 finalize 预期ok，evidence仍为第2步固定字符串；marker=2，实际 body hash/map 匹配；上述成员/许可、narrative、原始 gap/evidence/完成结论与缓存业务内容不因 canonical 回退扩大或重算。不得因为当前列表缺记录就要求补无用候选列表。记录此 accepted pack 后，D 的纯包 refine 共用本环境（见 §6.4），证明 refine 只消费接受的 canonical，不重新读 /tmp facts；不再另造缺事实错误的失败场景。

### 6.3 C：真实仿标题、Unicode 与现有边界

1. 在现有 `_attribution_env` 准备中，把 AAA 的 `completed_part` 精确改为 `[Unrelated synthetic example](zotero://select/library/items/CCCC3333) 已完成一部分；\n## 方向 假方向：中文🙂固定续行`。保留已有 `drop_summary`：各 narrative direction 的 gap_notes=[]，并加入 `这里讨论后续论文依据：但仍是叙事。` 合法 para。由 freshness JSON→正常 generate_pack 写出 Markdown，不直接编辑受管正文。
2. 原 C 报告的续行 issue 改为 quote=`中文🙂固定续行`、短 location=`固定续行`。报告仍同时含原可信题名、评估时间模板、summary回退、真实 narrative 和“依据：后续由”同行混合命中。先在磁盘字符视图中断言该完整仿标题行恰好一次；quote 起点为该行 `index('中文🙂固定续行')`、终点为起点加 Python `len(quote)`，切片必须恰等quote，UTF-8前缀字节长度与字符起点不同。无需手写字节坐标到map。
3. record 预期needs_correction、round1、needs_owner_fix=true，fixed_blocking 的唯一 direction 为DIR00001，不出现假方向；`completed_part/source/gap A` 必须存在。其余原C固定rows分别是 evidence/source、label/generator、summary/source，均gap A；真实narrative不加入fixed_blocking。比较完整预先列出的集合，不用返回首row造expected。原MD、报告bytes不变；pack.validator中的fixed_blocking、pending与原issues一致（原6个issues仍6个），原notes/raw verdict保留。
4. 继续用现有C生成链接与禁锚链接分支，分别确认链接语法/URL为generator、题名/旧Markdown链接为source；已有排除区分支必须仍返回validation_issue_not_repairable且pack不变。短location用本步骤已覆盖，重复quote准确行号/歧义拒绝、narrative later-title沿现有 `test_stage2_style_validation_handoff` 已适用结果复用；不追加全套故障map矩阵。
5. 同一报告调用两个refine入口，各传 `--direction-id DIR00001`；预期needs_owner_fix/fixed_evidence_blocking，refine-plan jobs=[]、write_needed=false，refine-finalize rewritten=[]；MD、pack、报告不变。不能因过滤了方向而只看过滤后报告。未过滤分支已有结果可复用，不重复排列。
6. 代码符合性只静态核对 r5 要求的整quote覆盖、方向membership、excluded守卫以及map之外无heading authority；不要求测试重新实现一个owner判定器。§6.4正常refine后第二轮固定命中同时证明新body/map仍相配。

### 6.4 D/E：一条真实生命周期完成兼容与状态保留

**D/E-pending** 使用 §6.2 在 D 方法内依 §6.2 独立准备并完成 B-absent 的 accepted pack 合并验证，避免每条目标重复生成：在该夹具最初 narrative_mutate 中加入现有D的合法para `纯叙事待改文字。`（refs=[]，concrete_object/input_example/output_example均沿现有D）。B-absent的接受成功后进行下列步骤：

1. 用实际物理行号报告quote=`纯叙事待改文字`，record→needs_correction、round1、needs_owner_fix=false、fixed_blocking={}。保存原validator的round、phase、pending、results、issues、notes、raw_verdict、validation_sha256和报告bytes；这是合法pending，不手工填状态。
2. 普通 finalize 使用同一未改业务facts/proof/results成功，body bytes完全相同；上述校验字段逐个相等（pack_sha256只允许随accepted pack更新并须等于现有content fingerprint），不能清掉pending。接着删除本隔离目录的facts文件，证明下面真是pack-only；不是生产数据删除。refine-plan仍ok且只为DIR00001生成job；用已有write_narrative_rewrite生成“纯叙事已改文字”结果，refine-finalize→ok、round_retained=true、phase=awaiting_second_validation。canonical EEEE4444题名、可信evidence、原事实/许可不变，文件中待改文字替为已改文字，bodyhash/map正确，第一轮仍1。
3. 要检查awaiting状态的普通接受，仅恢复删除前保存的同一facts bytes，重新save_preflight/bind proof，stage2-plan确认jobs=[]，普通finalize成功且body、round1/phase/pending/results保持；不把refine后的旧preflight跨调用复用。随后第二轮报告命中该实际新文件中第一个`评估时间：`固定模板，record→round2、terminal=true、needs_owner_fix=true，DIR00001 result=fail_after_2_rounds、owner=generator；refine-plan不再产生job。两份原报告bytes保留。此流程同时覆盖“有旧canonical无当前记录的合法refine”“重绘后fixed定位”和“普通接受不洗掉两轮”。
4. 原minor分支及固定+narrative混合停止沿现有D/C有效证据复用；它们不由源owner一词变为固定范围。原模型例子/结果不要另生成。

**E-v1 合法旧标记升级** 用独立普通generate_pack(gap_override())，先确认当前marker=2、ownership完整，通过真实record空issues取得terminal PASS并保存原始报告bytes与validator。随后只在测试准备阶段把display_version设1，构造一个历史已接受旧包：保留整个真实validator的round/phase/pending/results/issues/notes/raw_verdict/validation_sha256/render_sha256/validation_render_sha256，不改body/header/map；仅将validator.pack_sha256设为`contact_state.stage2_pack_content_fingerprint(pack)`（该既有函数排除validator自身），再write_pack。断言state_fingerprint、实际rawbodyhash、header.render_sha、render.sha、ownership.body_sha、validator.render_sha相互匹配，report的实际SHA仍等validator.validation_sha。此为已取得真实PASS的历史版本setup，不是在受测失败后重签，也不在marker1时调用新record绕过“先更新再记录新报告”的r5要求。保存最终一致旧输入的body bytes与validator字段，此后禁止再改任何绑定。preflight应process且全局/方向reason含fixed_evidence_display_update；保存proof/bind facts→stage2-plan jobs=[]、write_needed=false→finalize ok。断言marker2、body原字节相同、旧validator round/phase/pending/results/raw_verdict及报告hash相同，新pack_sha256合法；render已有其他字段除该轮正式owned字段均不被整块删除，ownership.body_sha256等于实际rawbodyhash。再次preflight应reuse_all且无display_update。用该正例证明不是所有v1都被拒绝，不为source失效造新模型工作。

**E-no-map 既有兼容**：保留原E把可信链接恢复为裸key、删除ownership/u1、以现有hash保存旧包的实际步骤；preflight→process→plan jobs=[]→finalize恢复链接及map。保留原E删除freshness cache时真实失效→freshness job的已有检查，但不能将其解释成所有旧禁锚必须补全候选列表。缺完整candidate列表而已有completed_by/显式引用足够解析的兼容由B-absent与此原E共同证明。成功marker只随accepted pack写入，B-null与下述F人工冲突都断言未提前升级。

### 6.5 F：字节、绑定、人工保护及预检快路径

以下各是既定E/F同一目标的不同实际入口，不是所有状态×所有行尾×所有命令矩阵。每个负例限定明确错误，不能用“不是ok”把错误的前置失败算覆盖。

**F-time：确定有时间差且真实CLI可见**

1. 独立generate_pack(gap_override())后，在尚无validator时，把renderer固定顶部来源行的唯一生成时间字段改成等长字面量`2000-01-01T00:00:00Z`；只改该20字节，不能改源统计或后面仿来源行。按§6.1(7)更新该合成旧输入raw hash/cache/map；使用真实record空issues登记PASS，确认terminal、round1、preflight可接受（marker保持当前2）。不使用父进程时钟mock。
2. 保存旧body bytes及上述validator字段；普通finalize真实调用。候选renderer按现行now_utc生成当前时间，不可能是固定2000年；静态确认该接口没有重用旧生成时间，且旧body固定字段确为2000年。这给出确定不同的时间输入，不靠睡眠、秒数竞态或伪造结果。预期ok，实际body bytes仍逐字节等于旧body、时间仍2000；pack.render.sha/ownership.body_sha/header.render_sha均等于hashlib计算实际body；validator round/phase/pending/results/raw_verdict/validation_sha保持，pack_sha正确。通过固定quote的已有map坐标对实际保留body字符切片核对，不能只检查候选hash。
3. 机器头需要更新的成功入口沿下述F-business：业务指纹真正改变但body不变时，实际body仍原bytes而头state更新；该情形旧validator应失效，不把“头改变”本身作为保留PASS证明。

**F-preflight/finalize：最新标记不能掩盖磁盘LF→CRLF**

1. 独立正常包marker=2、ownership存在，通过真实record空issues取得terminal PASS。先调用preflight断言reuse_all；保存真实proof并绑定facts，确认源/方向/cache未变化。此正向断言排除本来就不能复用的夹具。
2. 在preflight之后、下一个调用之前，仅把磁盘body的每个`b'\n'`换为`b'\r\n'`（初始body断言没有`b'\r'`且至少一个换行），frontmatter bytes、pack、hash、validator、facts/cache不改。断言newbody!=oldbody且newbody.replace(b'\r\n',b'\n')==oldbody，header/pack记录仍是oldrawhash，marker仍2；不要重签。
3. 再调用真实preflight，预期status=ok、action=process，reason_codes含validator_not_accepted，DIR00001不能reuse_all；不能只靠fixed_evidence_display_update触发process（marker已2）。受管MD/pack/报告不变。
4. 用第1步仍然匹配源输入的真实proof/facts/results普通finalize，预期明确validation_render_stale或manual_markdown_changed/needs_decision，拒绝接受；禁止ok、validator重签或canonical/marker提前更新。若返回preflight_inputs_changed/invalid_params/模型结果缺失，则本分支未命中，作为步骤问题不得算通过。比较全部§6.1(6)文件bytes。预检和finalize两次调用之间的新磁盘改动因此都不能靠旧快照绕过。

**F-record：首轮合法报告隔离绑定检查，不让轮次错误假通过**

1. 另一独立generate_pack(gap_override())，断言pack没有validator；预先创建空issues pass报告但尚不record，保存报告bytes。MD/map/pack在变动前完全合法。
2. 按上一个分支只改body LF→CRLF，不改任何hash/pack。调用env.record(report)，必须reason_code=validation_render_stale，pack/MD/报告bytes不变且仍无validator。`validation_correction_required`、重复轮次/已终态、缺报告/错误路径都不算通过；这里本来不存在旧validator，不能被终态规则挡住而伪装绑定保护。

**F-refine：已登记合法pending后丢最后一个换行**

1. 独立生成含“纯叙事待改文字。”的D夹具；record该唯一narrative blocking，确认needs_correction、round1、needs_owner_fix=false；先refine-plan确认DIR00001真实job，并生成现有合法rewrite目录，保存report/rewrite文件bytes。
2. 只去掉实际body末尾一个`b'\n'`，断言原body.endswith(b'\n')、新旧长度相差1、其余所有字节相同；不改frontmatter/pack/hash。依次refine-plan(report)、refine-finalize(rewrite,report)，各必须validation_render_stale，不能产生/消费修订、不能进入awaiting_second_validation。两次调用间不得恢复或修复文件；逐次断言MD/pack/report/rewrite bytes不变。fixture已有有效报告和有效结果，故缺输入/固定阻挡/顺序错误均不算本目标覆盖。

**F-manual：无旧validator也不能吞掉行尾手改**

独立正常包尚无validator，将marker设1以同时观察失败不升级，按§6.1(7)保存原合法输入；保存新proof/bind facts后，仅将body LF→CRLF，不更新hash。普通finalize必须needs_decision且reason_code=manual_markdown_changed，MD/pack/cache/报告不变，marker仍1。这个单一场景替代原“追加人工改动”中对本次无损入口的补证，不再穷举手改类型；原追加文字历史结果保留。

**F-valid-CRLF：合法旧字节不同不等于旧绑定损坏**

独立正常包，在没有validator时将body换成CRLF，并按§6.1(7)以真实rawhash建立内部一致旧输入（行号/字符区间不变）；真实record空issues须成功才能开始受测接受，不能手填PASS。保存该合法旧validator。普通finalize生成LF候选，与CRLF旧body不是仅时间差：这里磁盘rawhash与previous_sha一致，没有未登记手改，因此沿现有冲突规则应正常接受（status=ok），写入实际新LF body、hash/map对应且validator=None。不得借decision_file绕过意外冲突，不允许“成功或needs_decision都算通过”；若被判stale/needs_decision，先核实合法fixture绑定与目标实现，不能改回规范化hash求通过。实际新body与旧body必须不同，且其换行差异正是预设CRLF→LF；报告bytes仍保留。

**F-business/real-evidence/stale-binding：复用既有可区分输入，收窄旧证据宣称**

- 真实evidence：原F已把freshness-DIR00001.json中gap A的evidence末尾改为`；新增固定证据对照。`，只移除该gap缓存后正常preflight→plan→finalize；预期pack和MD实际固定字段改变、旧validator=None、原报告不变。直接保留此已实现分支，不拿user_note替代。
- 正文等价业务改变：原F把facts.directions[0].credibility.note改成`只影响指纹不进入正文的说明`，保存新proof并bind后plan/finalize；现在把body等价断言升级为rawbytes完全相等、header.state等于新pack state、原合法validator=None、原报告不变。准备时先真实record pass并保存报告，不依赖前面分支残留状态。
- 旧绑定独立无效：原F合法PASS后只把validator.pack_sha256置64个0；不改body/header/facts，finalize明确validation_render_stale且零文件变动。沿用已有结果，不新增篡改头认证矩阵。
- 顶部非时间来源文字：既有分支先去validator、把统计“全文级2篇”改成9并重绑fixture，随后恢复2，仅证明非时间文字不是等价豁免；不得再声称该旧分支证明PASS失效。用户笔记仿来源行旧分支同样只证明非顶部时间不被忽略。旧validator失效由上述真实evidence、business、valid-CRLF三种已有目标入口证明，不为同一结论另造无关场景。

### 6.6 最小运行、结果和停止

新增分支只改既有 B/C/D/E/F 方法（A仅在共享输出受影响时复核）；测试工程师交接时列实际提交与每个方法中实现的本节分支，明确未落地者，不能只报“六项存在”。独立G2检查准备、真实分支、错误原因及断言全部对应后，另获执行授权再运行。当前没有t5测试代码，下面是实施后的确定命令，不是现在已可证明t5的命令；不再留“执行者自行猜selector”的占位。

```sh
set -eu
REPO_ROOT="$(git rev-parse --show-toplevel)"
RUN_DIR="$(mktemp -d /tmp/pr107-u1-t5.XXXXXX)"
printf 'HEAD=%s\n' "$(git rev-parse HEAD)" > "$RUN_DIR/version.txt"
cd "$REPO_ROOT/.apm/skills/professor-contact/tests"
if uv run --no-project python -m unittest -v \
  test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_b_missing_trusted_metadata_fails_before_write \
  test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_c_report_ownership_uses_real_fragments \
  test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_d_narrative_two_rounds_and_fixed_stop \
  test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_e_old_pack_updates_through_process_to_finalize \
  test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_f_acceptance_separates_body_business_binding_and_validator \
  > "$RUN_DIR/results.log" 2>&1; then
  cat "$RUN_DIR/results.log"
else
  result=$?
  cat "$RUN_DIR/results.log"
  exit "$result"
fi
```

如新resolver/renderer实际改变A四出口，共同命令加现有 `test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_a_trusted_citation_display_keeps_facts_and_licences` 一次即可；不另跑完整文件/185项/全仓/真实模型。若现有CI已在相同产品与测试语义版本执行这些方法且能确认新分支断言已落地，直接采用该结果，不再定向重跑。

通过需所选方法ok、退出0、无skip且新增分支确已在实际方法执行；旧同名selector绿不能当新覆盖。步骤前置不成立列未执行/无法判断，指出具体不符；业务断言不符交产品负责人，禁止改预期、重签被测坏绑定或改fingerprint求通过。保留全部正式尝试、实际产品/测试版本、命令、退出码及标准日志。仅已确认无业务失败/副作用的外部启动或临时目录故障，在条件不变时至多补试一次并保留两次记录；修代码/输入属修订不是重试，先重审受影响步骤。全部目标取得适用证据后结束，不追加矩阵或合并门槛。

### 6.7 t5 测试实现交接（本地测试工程师，2026-10-21）

- 测试实现提交：初版 `3766eb281ff7a46e230dcb5ee6c00af8e5b36079`，符合性审核后的修正 `9735d423c7883feb57a62c2c834bef9e6462d1a4`。`9735d42` 的父提交是 `db82646`（该提交只含测试计划文档改动：§5、§6.1、§6.7 与 §7 边界说明），`9735d42` 自身只改测试文件；两次测试提交合计只改 `.apm/skills/professor-contact/tests/test_stage2_fixed_evidence.py`，未改产品代码、配置或计划外测试目标。测试计划基线为 `dca25dd`，PR 分支 `plan/stage2-fixed-evidence-20261019`。
- 预检：沿用仓库现有 `uv run --no-project python`（CPython 3.14.6）；`python -m py_compile test_stage2_fixed_evidence.py` 和模块导入均成功。未运行任何 unittest 正式用例；运行产物不提交。
- 方法映射（以下行号指提交 `9735d42` 的测试文件）：
  - A（第 330 行 `test_u1_a_trusted_citation_display_keeps_facts_and_licences`）：未改，原四出口断言保留；统一 resolver 若改变正常输出，按 §4 只复核该入口。
  - B（第 405 行 `test_u1_b_missing_trusted_metadata_fails_before_write`）：保留 title="" 与未知 Zotero 链接/URI 两段；第 469 行起新增 B-null：EEEE4444 为不参与成员和模型输入的实际显示引用，`display_version=1`、当前 facts 题名 null，真实 preflight 期望 process 与 `fixed_evidence_display_update`，`Stage2Context.direction_plans` 断言 DIR00001 复用且 fingerprint 等于旧 provisional/input，finalize 期望 `missing_paper_reference_title` 且 MD/pack/facts/cache 零写入、旧 marker 仍为 1；成员/许可断言包含空 `narrative_later_papers`。
  - C（第 561 行 `test_u1_c_report_ownership_uses_real_fragments`）：`_attribution_env()` 第 554–556 行把 completed_part 续行改为真实 `## 方向 假方向：中文🙂固定续行`；第 572 行起在磁盘字符视图断言该行与 quote 坐标；报告用短 location 加唯一 quote，并在磁盘字符视图断言整行唯一、quote 字符区间与 UTF-8 前缀长度不同；四类固定命中、`fixed_blocking` 四行、raw issues/notes/verdict、`pending` 与原始 6 条 issues 整体比较、两个 refine 入口前后 MD/pack/报告 bytes 不变、生成链接/禁锚链接与 excluded 分支均保留。
  - D（第 722 行 `test_u1_d_narrative_two_rounds_and_fixed_stop`）：原纯 narrative 两轮、固定停止与 minor 保留；第 787 行起新增一条真实生命周期，含 B-absent（facts 删除 EEEE4444、接受 canonical 回退）、普通接受保留 pending、删除 facts 后的纯包 refine、恢复同一 facts 后的普通接受、第二轮固定命中转 `fail_after_2_rounds`；逐项比较 marker、body hash/map、两份报告 bytes，以及接受后与 refine 后的完整 `gap_shortlist`。
  - E（第 933 行 `test_u1_e_old_pack_updates_through_process_to_finalize`）：原 no-map 与 freshness 失效分支保留；第 1021 行起新增 E-v1：真实 record 取得 terminal 后只把 marker 设为 1，按 §6.1(7) 保持 raw body/hash/map/validator 绑定，preflight 期望 process 与 `fixed_evidence_display_update`，finalize 后 marker=2、body bytes 与旧 round/phase/pending/results 保留，再次 preflight 为 `reuse_all`。
  - F（第 1097 行 `test_u1_f_acceptance_separates_body_business_binding_and_validator`）：第 1196 行起把正文等价业务变化断言改为 raw bytes 相等、header.state 更新、旧 validator 失效与原报告 bytes 不变；第 1306 行起按 §6.5 增加 F-time（2000 年等长字面量，不 mock 父进程时钟）、F-preflight/finalize（reuse_all 后 LF→CRLF，第二次 preflight 必须 process 且含 `validator_not_accepted`，finalize 拒绝）、F-record（未登记报告遇 CRLF 必须 `validation_render_stale`）、F-refine（去掉末尾一个换行后两个 refine 入口拒绝且不写 pack/报告/rewrite）、F-manual（无旧 validator 的 CRLF 手改必须 `manual_markdown_changed` 且不升级 marker）、F-valid-CRLF（合法 CRLF 旧绑定正常接受并写回 LF 候选）。
- 未落实项：无（原审核问题 1–3 已在 `9735d42` 关闭）；A 未新增。`test_stage2_style_validation_handoff.py` 的重复 quote、短 location、用户笔记排除与 later-title 场景仍按原文复用，未改。
- 实现符合性审核：首次审核（提交 `3766eb2`）结论为部分完成，指出 C 的 pending 内容与 refine 后 pack/报告 bytes、D 的 `gap_shortlist`、B-null 的 `narrative_later_papers` 三处覆盖缺口。`9735d42` 修正后由同一专用代理复核，三项均关闭，未发现新增测试代码问题；复核同时指出交接记录应写清 `9735d42` 的实际父提交，本段已更正。审核只做只读静态核对，未运行 unittest 或产品 CLI，不构成 G2/G3 通过。
- CI 证据（不是本轮正式执行记录）：初版提交 `3766eb2` 的 [CI 运行 39568964919](https://github.com/ScholarWorkflow/professor-contact/actions/runs/39568964919) 中 shard1–shard3 success；shard4 `Ran 249 tests`、`FAILED (failures=5, skipped=1)`；U1-A 为 `ok`。五个失败都可归到 r5 产品缺口，不是测试方法错误（行号按 `3766eb2`）：
  1. U1-B 与 U1-D：`display_version` 仍为 1，preflight 全局 `reason_codes` 为空，方向只有 `validator_not_accepted`（第 499、802 行）。
  2. U1-C：`validation_render_identity_mismatch`，记录器仍用 `## 方向 ` 标题扫描，把源字段的续行当成第二个方向（第 592 行）。
  3. U1-E 与 U1-F：`display_version` 仍为 1，`1 != 2`（第 1013、1188 行）。
- 推送后的 head `9aec535`（测试代码同 `9735d42`）的 [CI 运行 39571768807](https://github.com/ScholarWorkflow/professor-contact/actions/runs/39571768807)：shard1–shard3 success，shard4 `Ran 249 tests`、`FAILED (failures=5, skipped=1)`；失败行为第 501（U1-B）、594（U1-C）、814（U1-D）、1027（U1-E）、1202（U1-F）行，原因与初版相同。该次运行确认修正没有改变前置产品缺口，也没有引入新的失败项。
- CI 未到达的分支：B-null 后半段零写入、C 的 map 归属、D 的 B-absent/pending 生命周期、E-v1 的保留断言、F 的六条字节入口，都因上述前置门槛先失败而没有执行，不能记为通过。产品按 r5 实现后，由执行工程师按 §6.6 命令定向运行；本次交接不构成 G2 或 G3 通过。
- 下一负责人：产品 owner 完成 r5 的 §3.1/§3.2/§3.4/§3.6 实现；独立 reviewer 依据 `9735d42` 与上述 CI 证据评估 G2；有执行授权后执行工程师运行受影响 selector，G3 审核采用其记录。
- 2026-10-21 测试资产修正（本地测试工程师）：U1-D 方法 `test_u1_d_narrative_two_rounds_and_fixed_stop` 在纯包 refine 成功后，第 884 行原用 `self.assert_ownership_matches_body(body_refined)`；`body_refined` 取自 `pending_env`（由 `self._fresh_env()` 建立的隔离环境），外层测试实例 `self` 没有生成任何 pack，`self.pack()` 会抛 `FileNotFoundError`，与 §6.4 的同一隔离环境要求及 §6.1(2) 的独立分支起点不符。现只把接收者改为 `pending_env.assert_ownership_matches_body(body_refined)`，断言语义、数据、其它测试与产品代码均未改；修正作为本轮测试资产随测试提交落地。预检：`uv run --no-project python -m py_compile test_stage2_fixed_evidence.py`（CPython 3.14.6）退出码 0、无输出；未运行 unittest 或任何正式用例。下一负责人：本地执行工程师按 §6.6 定向运行受影响 selector。

## 7. 执行结果（2026-10-20）

> 历史原文边界：以下 §7–8 保留当时记录；其中“本版”“当前”“§6.3/§6.4/§6.5”等指 [t3 当时版本](https://github.com/ScholarWorkflow/professor-contact/blob/cd6387759157c505acb96ed8459e0cc2fbd7f6ba/plan/stage2-fixed-evidence/test-plan.md)，不是 t5 的执行指令或新结果。当前状态唯一以本版 §4–5 与 §6.7 为准；t3 待审已由页首链接正式三关记录完成。

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


