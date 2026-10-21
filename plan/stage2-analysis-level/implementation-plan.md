# U5：实际分析级别贯通与诚实统计执行计划

- Requirement revision：2026-10-19、2026-10-20 用户确认 U1/U5 独立设计与计划维护；2026-10-21 用户在只读复核后授权修订执行与测试计划，明确冻结消费边界、完整共同观察比较、写前旧态合法性三个机制。范围仍为 U5，不增加业务功能。
- Plan revision：`u5-analysis-level-r5`。本正文整体取代 r4；历史正文、评论中的矛盾选择不并行生效。
- Proposed review status：pending。作者未授予 APPROVED/PASS；r4 的计划审核及 t5/更早测试记录仅说明各自所审版本，不证明本修订或当前实现满足以下决定。
- 核对基线：PR #106 分支 `plan/u5-analysis-level-redesign`，head `d4e096f105805dfefbf2f4d883fc4919d49fce76`；r4 blob `38c71e8d4ec3105b639738086daccfdd360d9d6c`、t5 blob `6243873fb70d3c64e9db4773f04128f6878020be`。2026-10-21 重新读取；该分支已含产品/测试实现，本轮只改两份计划，不改实现、安装、运行测试、评论或合并。
- 唯一执行计划为本文；配套唯一[测试计划 t6](test-plan.md)由本轮同步修订。本文冻结实现机制与正式观察入口，具体 fixture/recipe 属于测试计划。私有载体/字段为本方案内部实现决定，不升级为公开业务 contract。

## 1. 目标、非目标及完成含义

每篇论文的级别表示当前可确认的成功分析实际使用全文还是摘要；无法确认则为 null。一个相同的判定从正式成功登记，经 facts、canonical papers、fresh/reused/resolved/old 分支贯通到既有方向成员统计。PDF、Markdown 存在和 facts 有效均不单独证明全文；OCR-only 成功全文与 facts unavailable 可以并存。

统计仍使用 `direction_papers(pack, direction)` 对 `supporting_item_keys` 的既有投影。reference/relevant-only 不计入；同篇在两个方向作为成员仍贡献两次，不另去重。三类互斥，合计等于原成员数。展示为“全文级 X 篇 · 摘要级 Y 篇 · 未确认 Z 篇（共 N 篇）”。

不改论文分析范围、成员资格、引用许可、归属、时效、resolved proof、U1 证据展示或 Stage 3/4。独立于 U1 和旧 #92；不引入全局事务、来源认证平台、通用状态机或独立的长期成功证明。完成是这三个有限机制在所有既有入口保持同一语义，不是继续增加局部例外或仅消除四条表面错误。计划完成不等于产品或测试通过。

## 2. 已核实现实及依据

以下描述性事实均指上述 `d4e096f`，路径相对仓库；规范要求来自本轮授权、既有正式契约与本节末规则，不能以当前缺陷改写要求。

| 决定 | 已读事实 → 修改 owner/落点 |
|---|---|
| 首次冻结必须在真实读源边界，不能 finalize 后取样 | `.apm/skills/professor-contact/scripts/_stage2_facts.py` 的 `load_papers_with_digests`、`Stage2Context.__init__`、`build_gap_pool` 重读 index/sidecar/cache；analyzer Step 6.1 使用 Step 3/5 已读资料。`_stage2_preflight.cmd_stage2_plan` 输出 freshness/narrative 的 model_input；`_stage2_resolve` 的 `_build_resolve_model_input` 已与 resolve fingerprint 同源。故事实读取 owner 提供冻结材料，analyzer 改消费顺序，plan/resolve owner 绑定 analyzer 实际读取的 job 输入，不能单在 finalize 加时间戳。 |
| 跨轮关联使用私有事务记录 | facts 已有 `stage2_preflight.preflight_id`；resolve 已有 `resolve_run_id`、独占 results_dir 与精确输入 fingerprint；普通模型结果为 schema 1、kind/direction/results 或 directions，未携带来源版本。两个 analyzer Step6.1.5/6.2 由 analyzer 自身阅读 job 材料、判断并写结果，普通 narrative 多个方向共用 narrative.json；`stage2_finalize_preflight_plan` 只验证 cheap_inputs，且 artifact 复核仅在 reuse_all/refresh_level。选择事务临时 companion 文件，复用现有 identity/run 语义，不改这些公开结果 schema。 |
| 完整观察比较只有一份 | `_stage2_preflight` 的 `stage2_program_inputs`、`stage2_resolution_evidence_guards`、逐方向 artifact/source/level、resolved grouping/entries、freshness view 已分清候选全集与方向消费集；`stage2_refresh_evaluate` 缺候选全集与 freshness 校验，写前只查逐方向 guards。将完整既有语义抽出给三个入口，不另建白名单。 |
| 已接受业务基线必须来自原冻结值 | `_stage2_finalize.cmd_stage2_finalize` 在 `stage2_accept_managed_body` 之后调用 `stage2_preflight_metadata`；后者调用 observed_source_projection 与 stat/hash。该现实不能证明本轮消费。改为写前组装候选元数据，源字段只投影已核验的冻结记录，成功提交时不再读源。 |
| 旧态合法性先于所有受管写入 | finalize/refresh 在 managed write 后才检查部分 validator；`stage2_old_managed_render` 不覆盖完整 cache/validator 生命周期。`_stage2_validation.stage2_require_recorded_validation` 已检查 schema、round、phase、pending、correction 范围；`stage2_validator_accepts` 是 terminal 快速复用政策。抽出合法性基础层给接受/校验使用，terminal 限制另留。 |
| 字节/统计/规范化的正确部分保留 | `_contact_base.py`、`_stage2_render.py`、`_contact_pack.py` 与 runner `contact_state.py` 已有无损 I/O、成员投影和 factory 注入落点；不改统计范围。两个 package analyzer 及主 `.apm/skills/professor-contact/SKILL.md` 必须同步新消费顺序。lease 仍归 `stage2_chatgpt_handoff.py`。 |

以上源码的固定版本入口：[scripts](https://github.com/ScholarWorkflow/professor-contact/tree/d4e096f105805dfefbf2f4d883fc4919d49fce76/.apm/skills/professor-contact/scripts)、[Codex analyzer](https://github.com/ScholarWorkflow/professor-contact/blob/d4e096f105805dfefbf2f4d883fc4919d49fce76/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md)、[OpenCode analyzer](https://github.com/ScholarWorkflow/professor-contact/blob/d4e096f105805dfefbf2f4d883fc4919d49fce76/packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md)。

历史 t5 [G2/G3 正式通过记录](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6314274110)适用产品 `96a1b11`、文档 `d4e096f`，不由本轮抹除，也不证明新增机制。

规则依据：[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)。[r3 审核](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6293315482)、[既有测试审核](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6297322139) 均不被本文改写为新修订通过。

## 3. 数据 owner 与三种基线

1. 分析 producer/现有成功 import owner 拥有 index 成功登记及所指分析产物。Stage 2 不替它发明失败状态、清空登记或把 PDF/facts 当成功证明。失败升级不制造新成功；旧摘要仍有效则仍为 abstract。
2. `_stage2_facts.py` 拥有当前有限来源读取、私有消费冻结和统一资格解析；正常 facts 是待核对的声明，不是可以压过 index 的第二份权威。`_contact_pack.py` 拥有 canonical 兼容及合法值域，renderer 只消费 canonical。
3. `_stage2_preflight.py` 拥有完整业务比较和分流；`_stage2_finalize.py` 拥有旧态检查、候选接受和刷新。有限的共同判断通过 runner 显式注入复用，不反向 import runner、不复制弱化版本，不新建可插拔接受框架。
4. `_stage2_validation.py` 继续拥有原 round/phase/pending 生命周期；共同的绑定判定只核对有效性，不改校验政策。基础文件 owner 提供 Stage 2 所需无损 I/O，不顺带改变其他 stage。

必须分离：A，磁盘上原始已接受 pack、Markdown、cache、validator 的不可变旧快照；B，正常处理实际消费并在成功接受后保存的来源/业务基线；C，本次当前观测和候选。A 先于兼容补字段保存，深度隔离 directions/papers/resolved；B 不能由当前观测事后补造；C 不能反填 A 来证明旧认证合法。兼容视图不是已接受原始内容。

## 4. 三个机制决定

### 4.1 机制一：跨入口、跨轮次唯一的来源/级别判定

采用同一有限解析结果：`known(fulltext|abstract)`、`unknown(null)`、`unreadable/invalid`。这不是新增持久状态字段。

- known：当前教授/item_key 的 index 可解析，entry 为合法对象，成功登记的 file 可定位且存在，level 为 fulltext/abstract。正常处理另要求其实际选择的 analysis_file 与登记规范路径一致。仅文件存在而无登记不是 known。
- unknown：明确无登记，或合法登记未声明/明确 null 的 level，或登记分析文件已缺失。没有 index 的旧分析文件可按原事实资格被正常消费，但级别仍 null，不能反推成功登记。
- unreadable/invalid：读取错误、坏 JSON/对象结构、非法 level 类型/枚举等。不能把坏输入折叠为可信 unknown；早期转 process，正常入口按既有输入错误终止，不写接受基线。
- 正常入口已声明路径与登记的非空路径不一致，或选择源不足以支持已知级别，按原事实/来源输入错误拒绝，不能静默挑任一来源。缺文件也不因此豁免原 facts 对其实际消费文件的要求。

正常 facts 的 level 必须与上述当前结果一致。显式 null 和新 facts 缺字段均表示未确认声明：当前为 known 时，两者都属于矛盾输入，零接受写入拒绝；不能允许当轮接受 null 后下一轮又从同一登记恢复 known。当前 unknown 时只能接受 null/缺字段；声明 known 必须匹配当前 known 值与来源。不存在“null 比 index 优先”或“index 永远覆盖 facts”的局部规则。

旧 accepted schema 2 的缺字段只在兼容视图显示 null，不是本轮 facts 声明，也不能阻止后来真实成功登记产生 known。旧 facts 在登记已知时缺字段，由本轮 prepare 读取当前登记，analyzer 只消费该次封存视图重新组装 facts，仍复用符合原规则的分析结果，不因此重跑模型；不得从旧 canonical 补级别。

成功、失效和再成功的责任边界：

- 新成功分析/import 由原 owner 正式更新 index/file 后，下一次正常或预检读取即可采用新结果；旧 accepted pack 不否决新登记。
- 若正常工作流认定旧来源失效，必须由该来源的既有 owner 先使正式登记/文件状态反映这一事实；仅有临时失败描述但 index/file 仍合法 known 时，Stage 2 拒绝矛盾 null，不能靠刷新替 owner 清登记。没有可用的既有处理入口时报告来源状态冲突，等待该 owner 修正，不新增 tombstone/失败证明系统。
- 仅全文升级失败而旧摘要仍符合既有复用条件，保留 abstract；facts/future-work 失败也不能冒充分析失效。确已无可确认成功源才接受 null。其后新的真实成功可以再转 known，不留下永久 null 优先权。

正常接受、preflight、锁内刷新都调用此解析；facts 声明比对仅正常入口执行，早期不凭空构造 facts。fresh/reused/resolved/old 的最终 canonical 均显式赋本次核对值，包括 null；禁止 truthy fallback、旧字段存在即跳过。公开 schema 2 不变，analysis_level 可选；v1 同 key 冲突中缺字段与 null 等价，v2 兼容不修改旧原始包。非法旧值不补成成功。

### 4.2 机制一的消费边界与机制二的完整观察契约

#### 4.2.1 唯一载体、首次冻结与跨阶段关联

采用**现有每教授事务临时目录内的一份私有 `stage2-consumption.json` companion**，不写新教授认证文件。runner 的 facts/source owner 创建并封存源段；plan/resolve owner 增加各自的只读输入段，analyzer 读取 runner 保存的完整 plan/model_input 并产生本轮结果，runner 封存结果集合与输入绑定。源/facts/计划与已封存结果版本不可覆盖；允许的唯一结果修复按本节受限 revision 追加，不覆盖原失败版本。同轮追加新阶段使用既有单文件原子写，若读到的 companion 摘要已变先重读核对，不丢其他已封存段。阶段顺序为 sources → facts → resolve（含 accepted reuse/用户选择）→ stage2 jobs → results；无 job 的阶段显式记录空集合与所复用的已接受输入身份。新轮使用新事务目录/run_id，不改写旧轮来求匹配。

必要私有字段（等价命名可调整，含义冻结）：`schema/version`，规范 professor_dir/program_root 与现有 transaction identity，随机本轮 `run_id`、`preflight_id`，`sources`（完整观察、实际供应的源材料及其内容摘要）/`sources_sha256`，封存 facts 原始文件摘要，resolve 的 run_id/plan 摘要/既有逐方向输入 fingerprint/最终 accepted sidecar 摘要，stage2 plan 摘要，以及每个 job 的 `job_id/kind/direction_id/model_input_sha256/result_file`，按结果文件分组的 job/方向映射、结果集合 revision 与每个最终文件原始字节摘要。各阶段摘要包含前阶段 id/摘要，防同教授同 preflight 但不同轮误配。facts 仅在既有私有 `stage2_preflight` 块附 companion 引用、version/run_id/sources_sha256；pack schema 2、facts 业务字段与模型 result schema 1 不变。完整材料仅留临时目录；成功 pack 的 `cache.preflight` 保存有限业务投影及必要私有版本/run 关联，不复制模型输入/结果日志。

首次冻结由 runner facts/source owner 在 **build/import、必要 sidecar 准备结束后，供 analyzer 形成本轮来源相关事实之前**完成。实现一个窄的 `contact_state.py stage2-consumption-prepare` 入口（输入本轮 preflight、事务目录、当前正式本地源路径/元数据声明）；它只读正式来源，返回/保存本轮要消费的准确材料和有限观察，不创建接受基线。沿用 facts/source 的合法路径、资格、sidecar/PDF 验证，不做新归属判定或模型分析。每个源在实际读取前后记录原有 stat；已读 bytes 用同一 bytes 计算已有摘要和解析材料；前后不一致、候选缺失变存在、整个材料构造完的完整复查不等，均停止本轮并回到准备。PDF 只沿现有 facts 验证所需读/摘要，不增加全文 hash 或复制 PDF。

analyzer Step 6.1 目前“来自 Step 3/5 已读数据，零新增读取”须同步修订：源依赖的 facts、相关性/归属输入和引用材料只能从此封存 payload 形成，不能把此前读到的旧文本配上新采样摘要。准备前已作的源依赖判断必须在封存材料上重新形成或核对其精确输入摘要；已有效的 paper-analysis/OCR 结果仍按既有复用规则使用，不要求重新调用全文模型。非文件业务输入（target/Stage1/catalog/ledger/年份参数）也记录本轮实际使用视图。准备后若还需补 sidecar/import 或更换来源，废弃本 run 并重新 prepare，不在旧封存段“刷新”来源。

`Stage2Context` 的 plan、resolve、finalize 模式从封存材料解析所需 index/sidecar/facts/PDF 验证结果和 freshness 读视图；当前文件重读仅作为比较对象，不替换消费视图。组装 facts 后 runner 核对其源字段/候选范围与封存材料并封存 facts 摘要；后续同轮 facts 任何字节改变都不能接收旧结果。`stage2-resolve-plan` 及 `stage2-plan` 用该上下文生成 model_input，同时封存准确 job 输入与计划摘要，复用 resolve 既有 `_build_resolve_model_input`/fingerprint、resolve_run_id/results_dir 隔离；普通 jobs 补同样的私有关联。

真正消费边界沿**当前同一个 analyzer 自身读取计划并判断**的工作流程，不引入独立 job RPC、子模型或新增模型 pass。runner 在输出 jobs 的同一步将完整 plan（含准确 model_input、run/上游摘要关联）写入本事务目录，并把路径/摘要交给 analyzer；analyzer 在 Step6.1.5/6.2 必须完整读取该确切 plan 的相关 model_input，再据这些材料判断并写结果，禁止从当前磁盘另拼输入。tool 输出截断时读取保存文件的完整相关内容，不能只看摘要或缩略说明。来源冻结保证供给材料，plan 摘要保证这次读取指向本 run 的准确任务；结果仍由原 analyzer 产生，不声称存在外部模型调用的回执。私有绑定只能验证准确材料供应和结果关联，单由 analyzer 填一条 receipt **不能独立证明模型实际阅读或内部思考**；两个 analyzer 的正式流程必须明确上述读取边界及结果责任，不能用自填 receipt 代替它。

结果封存按**每个文件的完整聚合结果集合**进行。runner 预先冻结 job→result_file→direction 集合；同轮所有 narrative job 共用的 `narrative.json` 在全部 process 方向 `directions[]` 齐备后才封存一次，freshness/resolve 各文件按各自实际映射加入同一阶段集合。analyzer 完成该阶段全部结果后调用窄的 `stage2-consumption-seal-results` 入口，传本 run、该阶段 plan 与实际 results_dir；runner 读取每个最终文件原 bytes、核对映射并封存结果集合 revision=0。不得每完成一个方向就把尚会继续聚合的同名文件封死；封存后该 revision 文件保持原样，finalize 读取同一 bytes 校验并使用。resolve 的 accepted reuse/用户选择产物仍按既有 lifecycle 绑定，不冒充新模型结果。

保留既有 analyzer Step6.3 **仅一次 `unknown_reference_id` 转录修复**：首次 finalize 的原结果 revision=0 若被该明确原因拒绝，runner 在返回该错误前于同一临时 companion 记录失败版本摘要及一次修复资格（没有接受写入）。analyzer 重新读取同一封存 plan 的相关 ID，保留原结果文件/失败输出，在本事务目录的 `repair-1` results 子目录复制完整原集合，仅修该次拒绝所涉引用 ID、对应 refs/占位符的机械转录；不改判断/叙事语义、其他方向或来源。seal-results 校验同一 sources/facts/plan 摘要、runner 已记录的 unknown_reference_id、原集合仍在，按既有引用字段语义核对差异仅属该次 ID 修复，追加 revision=1/repair_of=原结果摘要并封存新集合。再次 finalize 仍完整校验 F→O 与全部结果，修复失败即返回原错误路径；不允许 revision>1、一般非法结果重写或在源已变化后借修复重绑。本安排只保存已批准的一次失败/修复在既有临时目录中的两个版本，不增加通用重试/事务框架。

普通 process 中源段 F 的文件/业务读视图始终不改；后续 resolve 正式产生的 proposal→accepted 变更属于本轮输出，在用户接受或 keep-provisional 后才封存 accepted sidecar 摘要及方向作用域，作为 finalize 的实际消费段。完整比较使用同一契约但区分读取视图与候选输出：不能拿 prepare 时的旧 resolved sidecar 与本轮合法新 accepted 输出比较而误报来源漂移；finalize 比较其实际消费的已封存 accepted 摘要/作用域与当前文件，旧 B 的 grouping 只用于判断业务是否改变。新 freshness 结果也只构造内存候选，F 的旧 freshness 读视图到写前保持不变，成功 cache.preflight 才写候选接受视图。refresh 没有这些新业务输出，始终直接 B→O。

runner 正式接受前核对完整 job/聚合方向集合、plan/facts/resolve/结果摘要与 run/revision 关联；缺封存段、换目录旧结果、同名任务错轮、被覆盖 facts/plan/已封存结果均按既有输入错误或 needs_refresh 拒绝，零接受写入。确需重新形成输入时另起 run，不能借上述机械修复更新 source 快照。
替代方案及取舍：单在 stage2-plan 前 stat 不能覆盖此前 analyzer 已读材料；单扩展 preflight_id 仍只证明早期决定；finalize 重读会认证未消费版本。复制完整 PDF 或建长期签名平台成本与授权均不成立。选择小型私有 companion + 原 analyzer 准确读计划及 facts/resolve 入口关联，增加有限临时 I/O 和旧轮保守失效，换取消费链闭合；不建立通用任务/认证平台。

#### 4.2.2 观察与比较共用同一有限契约

由 `_stage2_preflight.py` 抽出既有完整观察/比较，facts owner 提供源读取结果，runner 显式注入所有 caller。观察返回可比较值及 invalid/unreadable 原因；比较返回业务相等/变化/不可比较，另列合法 level/统计格式变化与旧校验合法性。**接受基线 B、当轮冻结 F、当前观察 O 是不同对象**；各入口只选不同操作数，不改变字段含义。

| 范围 | 必须保留的已有比较内容 |
|---|---|
| 教授业务输入 | target/selected direction identity、Stage1 professor fingerprint、catalog/candidate union、authorship ledger、年份/有效参数、语义/extractor/generator 版本及已批准业务资格；沿用原视图，忽略 index generated_at/KB id 等管理字段，不 hash 整个 index mtime。 |
| 候选证据全集 E | selected candidate union 的每个 key（含不在任何方向 relevant/gap 集中的候选），按现有 `resolution_evidence_guards` 范围观察分析、facts、future-work、已声明 PDF。先验证 key 集覆盖，再比较每个 guard；缺块/缺 key 不是空证据相等。 |
| 方向实际消费集 D | 保持既有 relevant/gap、后续叙事、resolved grouping 的实际 consumed keys；记录 consumed_sources/pdf_sources、index source_projection、各载体既有 digest/stat。D 不替代 E；来自 E 的未选中候选仍能影响 resolve。 |
| 声明、存在与读取 | index file/facts_sidecar/future_work_sidecar 分清无登记、未声明、显式空、规范路径与坏记录；每个 analysis 的固定 `.facts.json`/`.future_work.json` 候选按原规则记录 present/missing，null 不取消探测；missing→exists、删除、换址都比较。已存在文件覆盖原 size/mtime/ctime 等 guard 和已取得摘要；PDF 沿 facts.pdf_file 与现有验证摘要/stat，不扫孤立 PDF、不查 Zotero、不为比较重读 PDF。 |
| resolved/freshness | provisional→resolved IDs/merged_into、accepted entries/input fingerprint、作用域/accepted proof 与原资格；逐 resolved 输出 gap view 的 `freshness_view_fingerprint`，含原 shortlist/excluded/blacklist 所需缓存，不把一次加载的旧 cache 当当前观察。只比较接受时读视图，不把本轮新计算的候选 freshness 写值当漂移。 |
| 独立 level/display | §4.1 known/unknown/invalid、各实际消费 key 的 level_projection、statistics_version；纯合法 level 改变不污染业务 fingerprint；invalid 先于 null 声明处理，坏 JSON/对象或读取失败不能被 null 绕过。 |

PDF 缺源的离线边界不变：同一本地输入且无新正式声明才能维持无源；不声称验证远程附件。旧私有版本/缺来源冻结关联一律保守 process；合法旧 schema 2 原包仍可读、有效分析/resolve/模型工作仍可按原条件复用，不强制全量重跑。普通成功接受才建立新业务基线；refresh 只读验证并更新 level/display，业务 source/guards/freshness/resolved 基线逐字段保持原冻结值。

### 4.3 机制三：所有受管写入前完成旧态合法性，再决定能否继承

在原 preflight/finalize/validation owners 之间复用分层判定；不能只把名字统一、底层仍分别少验。返回原失败类别及是否可继承，不造第二套认证记录。

在候选构造前抓取 A，合法性判定在任何受管 Markdown/pack/cache 写入前完成；渲染只生成内存候选。判定不能藏在写文件 helper 的写后分支。

第一层，旧文件/包/render 绑定：读取真实旧 pack 和实际文件；拒绝不受管、symlink 或不可读等原不支持状态；核对 managed_by、既有教授标题身份、header.state_fingerprint 对原旧包的既有 state fingerprint、原始 body SHA 对 header.render_sha256 及 cache.render 中对应 SHA。不能先同步 header、补 canonical 字段或改 cache 再声称旧绑定有效。无旧结果是首建，不构造虚假旧绑定。

第二层，旧 validator 绑定（存在记录时）：复用原 validation owner 的 schema 2、round 非 bool 且为 1/2、phase 合法组合、pending 非空问题列表、correction_applied_direction_ids 与 results 的结构/枚举及方向范围检查；needs_correction 须仍有未修方向，awaiting_second_validation 须 round1 且 pending 已修完，terminal 按原终态结果结构判定。不得仅比较 hash 或 schema==2 就继承；非法 validator 容器/版本不能视为“无 validator”。其 pack_sha256 对原始旧包的 content fingerprint（按现有规则排除 validator），render_sha256 对上述实际 body/header/cache，方向作用域按现有契约核对。合法 pending/第一轮状态与合法终态是不同结果；仅字段不存在属于合法无 validator，前提 pack/header/body/cache 本身合法。原始报告的精确摘要核对仍归提供该报告的 record/refine 入口，不为 refresh 新增必需报告路径；pack 未存报告路径不扫描寻找报告。

分类结果固定为：首建（pack 与 Markdown 都不存在；孤立旧文件不能冒充首建）、合法无 validator、合法中间态、合法终态、失效旧态/不可读。合法中间态可在普通 finalize 的业务/正文未变时原样继承 round/phase/pending/results/correction 证据并只改必要 pack 绑定；refine 仍执行原纠正文案→第二轮，不能调用 terminal-only gate。合法终态可保留原结果，但 terminal fail_after_2_rounds 不能 reuse_all。

第三层，仅 reuse_all 额外要求既有 terminal、有效 round 和各方向 pass/skipped；fail_after_2_rounds、未完成/缺结果不满足快速复用。普通 finalize/refine 保留合法 round/phase/pending 的原生命周期，不能因共用判定而强迫所有入口终态通过。

旧合法性、实际 body 变化、业务认证依据变化三个事实分开：

- body 或业务实变：旧认证不再适用，保留原报告供追溯；不得因新 body 恰好相同保留已变业务的旧 PASS。
- 两者均未变且完整旧绑定合法：允许保留原合法 validator 状态，仅同步必要的新 pack 绑定。level 换位但聚合正文等价可落此分支，前提仍是完整守卫与旧绑定都成立。
- 旧绑定无效：任何入口均不得通过修头/重算 hash 自动恢复原通过结论。refresh 即使统计正文将变化也必须停止，沿原证据/人工保护错误零业务写入返回，不能清旧 validator、修头再继续。普通过程若确实产生新业务/正文，只能按原受管冲突/显式覆盖政策接受为新未校验结果，不能继承失效认证；内容未变不能借普通 finalize 把同一失效证据重新签成通过。
- 旧 body 不可读或人工改动，沿既有读取错误/needs_decision；结构或绑定失配沿既有证据错误。不可判定不等于“没有旧内容”。不借 candidate 补旧身份，不自动覆盖人工文件。明确覆盖也不是继承旧 PASS 的授权。

### 4.4 保留的字节契约：从磁盘到 hash、比较和写回全程无损

Stage 2 的接受、preflight 绑定、validator 绑定、managed conflict 与写回共同采用同一无损读取/正文切片语义。使用原始 bytes（或严格 UTF-8 且禁止 newline 转换的等价实现）；不能在任何前置 `read_text()` 默认 universal-newline 转换后才调用“保留字节”比较函数。

frontmatter 解析以原文件分隔符的实际字节偏移取 body。兼容既有 LF/CRLF 文件识别，但不把分隔符、正文换行、尾换行、空格、BOM 等重新拼接或归一化；正文边界只去掉既有格式明确规定的结构分隔，不吞掉任意空白。无法解析或非法编码按既有错误保护，不修复后再称原绑定有效。

hash 对实际 body bytes 计算。算法仍为现有 SHA-256；LF 原文件无语义迁移。由旧换行归一化产生的不匹配记录不能自动续认。renderer 新正文严格编码一次形成候选字节，其他实际字节变化均算变化。

唯一比较豁免是 renderer 固定顶部生成标题位置的生成时间 token。定位依赖该固定结构和位置，仅在比较副本中忽略该 token；同一行统计、换行和其余正文不变。不在任意后续叙事行寻找“第一个看起来像时间”的正则匹配。真实 SHA 从不忽略时间。

若比较等价且旧绑定合法，保留旧实际 body bytes 和真实 SHA；无需变头则不写文件，需要绑定候选时只替换必要机器头并拼接原 body bytes，写入不得再做 text-mode 换行转换。若正文变化则按既有人工保护写候选字节。用同一 Stage 2 专用无损 primitive/显式选项贯穿各消费者，不顺带重构所有 stage 的 I/O，也不引入第二 renderer。

## 5. 完整执行顺序与并发边界

### 5.1 preflight 与普通 process 接受

1. preflight 只读 A/B 与当前 O，验证旧基线私有版本、覆盖集及完整比较；业务变/不可比较优先 process，业务相等且仅合法 level/统计格式变化才 refresh_level，其余只有合法 terminal pass/skipped 才 reuse_all。显式 chatgpt_result/kb_import=true 仍 process 优先。旧 validator 无效不伪装为 source_changed，但不能据此快速复用。
2. 普通 workflow 沿既有 build→import→exact acquire(verify_plan=True)→finally release；必要源准备完后执行 §4.2.1 freeze→facts→resolve→stage2-plan→同一 analyzer 完整读计划并产生结果→结果集合封存，用户选择按既有 accepted policy。lease 不替代冻结或比较。fresh/resolved/reused/old 合流都使用同一 F，不因 jobs=[] 或 preflight.action=process 绕过。
3. finalize 读取原始 A 并分层判旧；校验本 run 的 companion、facts、计划/结果与已接受 resolved 绑定。把 F 与当前 O 按完整契约比较，要求来源、已有消费 level 与业务输入一致。普通 process 的基准是本轮 F，不是已被正常业务更新取代的旧 B；判断新旧业务是否变化仍用 B/A 与新候选。漂移/错轮/丢失返回既有 needs_refresh/preflight_inputs_changed 或原输入错误，接受产物零写入；不重新准备 proof 后自动重试。
4. 深隔离生成 pack、freshness cache 更新和实际 Markdown 候选；核验全部 facts/结果/引用资格及 §4.3 旧态决定。无变化仅合法旧绑定才能继承；真正新业务/正文依原受管冲突和显式 overwrite 政策接受为未校验，失效旧态不能被新 candidate 反向认证。旧态分类已发生，即使允许显式覆盖也不继承旧认证。
5. 渲染后、**首个受管写入前**再次完整观察 O，比较 F→O，并核对 A 的 pack/Markdown/相关 cache 原始内容/存在/stat 未被外部更新。重做旧态检查所依赖的读取若有变化先停止，不能复用旧“合法”结论覆盖新文件。准备阶段所有已知逻辑错误、冲突决策、validator 是否继承、最终内存元数据在此之前确定。
6. 沿原有限顺序提交 Markdown → pack → freshness cache（用原单文件原子工具）；cache 按 owner 字段合并。成功 pack 的 source_projection/consumed_sources/pdf_sources/artifact_guards/resolution_evidence_guards/业务读视图来自 **F 原冻结值**，resolved 输出与候选 freshness 接受视图来自本轮已校验候选，level/statistics/render 元数据来自该次实际接受。纯构造器不得读磁盘；严禁写后 observed_source_projection/stat 创建“消费证明”。中间写失败按既有未完成边界，不伪造成功。

### 5.2 专用级别刷新

1. 使用持久包及当前有限观察，不读取临时 facts/companion、不运行模型/Zotero、不重签 resolved proof。预检 payload 仍只代表分流决定，不能当作锁内通过。
2. 沿现有 acquire_local_lease(professor_dir, 唯一 token, verify_plan=False)；busy 零业务写入。finally 在所有退出路径释放，释放失败如实报告；不伪造 handoff/_latest、另建锁/journal。
3. 获锁后重读 A/B、目标/Stage1 与完整 O，验证 payload 目标/事务身份和 B 版本/覆盖。先完成 §4.3 全部旧态分类，失效旧态无论正文是否变化均零写入退出；合法 pending 可以刷新，不能要求 terminal。随后按同一完整契约 B→O 核对 E、D、resolved/freshness 与全部既有业务条件。变/不可比较退 needs_refresh 并重预检 process；不通过修头/清认证补造 B。
4. 隔离候选仅改当前 level、统计接受元数据及必要 pack/render 绑定；真实渲染并在内存中比较正文、决定保留或过期 validator。保留成员/assignment/原模型结果/resolved proof/无关缓存；缺可信渲染字段退 process。refresh 不写 freshness cache，不更新其业务基线。
5. 渲染后且首次正式写前，再跑完整 O 与 B 比较（包含候选全集 evidence_guards、missing→exists、freshness）；另外比较锁内已见的 level，若再次变化也退回重预检。再核对 A 的原始接受文件与缓存快照、旧态合法性。不能只重查逐方向 analysis stat。所有检查完成后按普通有限提交顺序写 Markdown/pack，复用 B 原业务字段，只更新 level/statistics/render 与合法 validator 的必要绑定；任何逻辑拒绝零业务写入。

教授 lease 只序列化遵守该 lease 的本地 writer/importer，不能冻结外部 PDF、编辑器或远程 Zotero。上述重读和写前检查保证既有 stat/摘要契约下可观察的输入一致，不承诺任意外部并发修改的文件系统快照，也不以此增设全局锁。检查后发生的外部变动由下次既有 guard 拒绝复用；不把“当前已验证”写成永久来源认证。

Markdown 与 pack 是多文件写入，不宣称一次事务原子性。写入中 I/O 失败返回未完成，不补打接受成功/校验通过标记；保留已发生的真实状态，下一次由绑定/来源不一致阻止 reuse。不得自动通过修头或反填缓存掩盖中断；按正常恢复/人工保护处理。沿用现有单文件原子持久工具，不新增自动跨文件回滚承诺。

## 6. 实施落点、兼容和交付顺序

1. facts/source owner 先统一 known/unknown/invalid（坏 index 不论 facts=null/缺字段均拒绝），实现 §4.2.1 的私有冻结读取与窄 prepare 入口；通过 runner factory 注入，Stage2Context 消费冻结材料。两 analyzer 与主 SKILL 同步源准备→冻结→事实组装顺序；旧 facts 缺字段重新组装与旧 accepted 兼容分开。
2. preflight owner 抽取完整 observe/compare，明确 E/D/存在标记与 freshness 读视图；新私有消费版本使缺冻结关联的旧 B 保守 process。保留公开 schema 2、v1 迁移及统计语义，不批量重写旧包。
3. resolve/plan owner 封存准确输入/复用身份；analyzer 准确读取计划、自身判断并产生聚合结果，runner 按最终文件集合关联封存；保留一次 unknown_reference_id 受限修复版本；finalize 接受缺段/错轮/输入摘要不匹配时 fail closed。现有 resolve_run_id、用户 accepted policy 不被 companion 取代。测试 fixture 也须经实际 prepare/plan 接线，不手造接受证明。
4. validation owner 抽出原 schema/round/phase/pending/results/范围合法性层，finalize/preflight/refresh/refine 共用；terminal 快速复用层保留在 preflight。无损 I/O 原语继续贯通 managed/validation/preflight，不顺带重构其他 stage。
5. finalize owner 拆开 candidate generation、全部 validation、commit：旧快照→旧态分类→本轮关联及完整 F→O→隔离候选/渲染→完整写前复查→有限提交。元数据构造改为冻结值纯投影，移除写后采样。refresh 走 B→O、同一合法性及写前复核，只更新 level/display。
6. 产品 owner 完成以上依赖后，独立实现审核检查实际调用接线与已批准行为；测试 owner 按 [t6](test-plan.md)准备受影响步骤。本文与 t6 的新机制/recipe 尚未实现或执行，旧绿结果不得覆盖；不因文档变更重跑 OCR/模型或完整业务回归。

公开 pack schema、facts 业务字段、模型结果 schema 均不改；私有 companion version 与 cache.preflight version 仅限内部。旧/中断/丢失事务材料不能被当前磁盘补造，重新准备本轮，保留历史产物与报告。正常有效分析与可复用模型结果按其原输入身份校验后使用，不能无依据把旧结果绑定到新输入；这不要求一律重跑。

## 7. 影响、限制及审核边界

- 保持：scope、成员/引用身份、resolved 接受政策、facts/future-work 资格、模型复用、人工保护、lease、校验轮次和既有错误通道。
- 纠正：矛盾 null 不再被接受；合法新成功不被旧包压制；完整守卫覆盖普通 process、锁内刷新及正式写前；旧态全检查前置、不能自动续认；真实换行/正文差异不能被吞掉。
- 明确限制：离线源观测不是远程附件查询；stat 不是无限强内容认证；协作 writer lease 不是外部文件锁；单文件原子写不是跨文件事务。来源 owner 未反映失效时拒绝冲突，不擅建状态认证机制。实现必须暴露这些真实限制而非承诺绝对不存在并发窗口。
- 待核实项：r5 是设计候选，当前产品仍存在已定位分叉。共用谓词接线、字节边界和所有入口行为须由后续实现/独立审核核实；本文不声明无风险或全部通过。
- 不扩大：不做完整业务回归/边界矩阵、来源过程认证、全教授扫描或新框架。是否复用既有测试结果由测试 owner 根据行为变化判断，不因文档 SHA 重跑无关项目。

## 8. r4 → r5 取代记录、审核与下一负责人

本轮将“消费后完整比较”从抽象要求改为首次 freeze owner/时点、准确材料供应、facts/resolve/plan/jobs/results companion 关联及成功提交原冻结值的单一机制；将候选证据全集 E 与方向实际消费集 D、freshness/resolved 及 missing 标记纳入同一个 observe/compare；旧态全部合法性及继承决定前置于任何受管写入。取代 r4 模糊的“成功后记录实际消费基线”顺序，不能保留写后重新采样。§4.1 资格与 null 转移、§4.4 真实字节、成员统计、U1 独立与失败/I/O 边界保持。

重新打开受影响 P1–P4 的事实/机制/并发/生命周期/可执行性判断，旧 r4 独立 APPROVED 只属于旧版本；t5 的 55/1085 绿只属于当时样例。独立 reviewer 审核本完整 r5 与 t6，作者状态仍 pending；不授予自己 PASS/APPROVED。审核后产品 owner 按依赖实施，测试工程师准备受影响 recipe，再由执行工程师在另有执行授权时运行。当前仅文档修订，不代表产品修复、测试关口或合并批准。
