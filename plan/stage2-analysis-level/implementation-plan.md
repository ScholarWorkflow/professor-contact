# U5：实际分析级别贯通与诚实统计执行计划

- Requirement revision：2026-10-19、2026-10-20 用户确认 U1/U5 独立设计与计划维护；2026-10-20 用户针对 #106 反复出现的来源、旧绑定和字节比较问题，明确要求修改执行计划、修正三个机制决定。范围仍为 U5，不增加业务功能。
- Plan revision：`u5-analysis-level-r4`。本正文整体取代 r3；历史正文、评论中的矛盾选择不并行生效。
- Proposed review status：pending。作者未授予 APPROVED/PASS；r3 的计划审核及既有测试记录仅说明旧版，不证明本修订或当前实现满足以下决定。
- 核对基线：PR #106 分支 `plan/u5-analysis-level-redesign`，head `628126ad2db3708d2322eb640ccb65e9370e1240`；原执行计划 blob `0956b3983f922243a027ac6061246e285bc3b05d`；2026-10-20 核实。基线含产品实现，不能再称其为尚未实施的 plan-only PR。
- 唯一执行计划：`plan/stage2-analysis-level/implementation-plan.md`。本次仅修订本文；[测试计划](test-plan.md) 的适用性由测试负责人针对受影响机制另审，不在本文规定 recipe、增加用例义务、执行测试或改产品/测试代码。

## 1. 目标、非目标及完成含义

每篇论文的级别表示当前可确认的成功分析实际使用全文还是摘要；无法确认则为 null。一个相同的判定从正式成功登记，经 facts、canonical papers、fresh/reused/resolved/old 分支贯通到既有方向成员统计。PDF、Markdown 存在和 facts 有效均不单独证明全文；OCR-only 成功全文与 facts unavailable 可以并存。

统计仍使用 `direction_papers(pack, direction)` 对 `supporting_item_keys` 的既有投影。reference/relevant-only 不计入；同篇在两个方向作为成员仍贡献两次，不另去重。三类互斥，合计等于原成员数。展示为“全文级 X 篇 · 摘要级 Y 篇 · 未确认 Z 篇（共 N 篇）”。

不改论文分析范围、成员资格、引用许可、归属、时效、resolved proof、U1 证据展示或 Stage 3/4。独立于 U1 和旧 #92；不引入全局事务、来源认证平台、通用状态机或新的持久成功证明。完成是这三个有限机制在所有既有入口保持同一语义，不是继续增加局部例外或仅消除四条表面错误。计划完成不等于产品或测试通过。

## 2. 已核实现实及依据

固定基线源码入口：

- [_stage2_facts.py](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/.apm/skills/professor-contact/scripts/_stage2_facts.py)：正常 `resolve_declared_level` 可以接受与已知登记矛盾的 null；早期 `observed_level_projection` 又只看 index。二者已分叉，不能只修最终赋值。
- [_stage2_preflight.py](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/.apm/skills/professor-contact/scripts/_stage2_preflight.py)：预检包含 artifact guards 与业务条件；刷新所用的来源路径/存在投影不是这些检查的替代品。现有 `stage2_validator_accepts` 是终态复用条件，不能直接替代普通 finalize/refine 的合法中间态绑定检查。
- [_stage2_finalize.py](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/.apm/skills/professor-contact/scripts/_stage2_finalize.py)：刷新锁后核验未覆盖完整 artifact guards；`stage2_old_managed_render` 未验证旧 state_fingerprint 与接受包/cache/validator 的完整关系；`read_text()` 在字节比较前归一化换行。
- [_contact_base.py](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/.apm/skills/professor-contact/scripts/_contact_base.py) 的 managed conflict/write 与 [_stage2_validation.py](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/.apm/skills/professor-contact/scripts/_stage2_validation.py) 的绑定读取也须采用相同字节语义，不能只改一个比较 helper。
- [_contact_pack.py](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/.apm/skills/professor-contact/scripts/_contact_pack.py)、[_stage2_render.py](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/.apm/skills/professor-contact/scripts/_stage2_render.py)、[contact_state.py](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/.apm/skills/professor-contact/scripts/contact_state.py)：保持 canonical、成员投影和显式 factory 注入边界。
- [Codex analyzer](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md) 与 [OpenCode analyzer](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md)：现有成功 route/index 登记 owner；两者必须传相同事实契约。
- [stage2_chatgpt_handoff.py](https://github.com/ScholarWorkflow/professor-contact/blob/628126ad2db3708d2322eb640ccb65e9370e1240/.apm/skills/professor-contact/scripts/stage2_chatgpt_handoff.py)：复用现有教授 writer lease，不改格式、CLI 或另建锁。

规则依据：[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)。[r3 审核](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6293315482)、[既有测试审核](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6297322139) 均不被本文改写为新修订通过。

## 3. 数据 owner 与三种基线

1. 分析 producer/现有成功 import owner 拥有 index 成功登记及所指分析产物。Stage 2 不替它发明失败状态、清空登记或把 PDF/facts 当成功证明。失败升级不制造新成功；旧摘要仍有效则仍为 abstract。
2. `_stage2_facts.py` 拥有当前有限来源读取和统一资格解析；正常 facts 是待核对的声明，不是可以压过 index 的第二份权威。`_contact_pack.py` 拥有 canonical 兼容及合法值域，renderer 只消费 canonical。
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

旧 accepted schema 2 的缺字段只在兼容视图显示 null，不是本轮 facts 声明，也不能阻止后来真实成功登记产生 known。旧 facts 在登记已知时缺字段，由正常 analyzer 重新读取当前登记并组装 facts，仍复用符合原规则的分析结果，不因此重跑模型；不得从旧 canonical 补级别。

成功、失效和再成功的责任边界：

- 新成功分析/import 由原 owner 正式更新 index/file 后，下一次正常或预检读取即可采用新结果；旧 accepted pack 不否决新登记。
- 若正常工作流认定旧来源失效，必须由该来源的既有 owner 先使正式登记/文件状态反映这一事实；仅有临时失败描述但 index/file 仍合法 known 时，Stage 2 拒绝矛盾 null，不能靠刷新替 owner 清登记。没有可用的既有处理入口时报告来源状态冲突，等待该 owner 修正，不新增 tombstone/失败证明系统。
- 仅全文升级失败而旧摘要仍符合既有复用条件，保留 abstract；facts/future-work 失败也不能冒充分析失效。确已无可确认成功源才接受 null。其后新的真实成功可以再转 known，不留下永久 null 优先权。

正常接受、preflight、锁内刷新都调用此解析；facts 声明比对仅正常入口执行，早期不凭空构造 facts。fresh/reused/resolved/old 的最终 canonical 均显式赋本次核对值，包括 null；禁止 truthy fallback、旧字段存在即跳过。公开 schema 2 不变，analysis_level 可选；v1 同 key 冲突中缺字段与 null 等价，v2 兼容不修改旧原始包。非法旧值不补成成功。

### 4.2 机制二（来源侧）：完整共同守卫，不以路径投影代替业务有效性

保留一份有限的完整业务比较，供正常接受检查、preflight 分流及刷新锁内复核使用。它包括当前已有的 target、Stage 1 fingerprint、catalog/candidate union、业务年份及有效参数、分析/归属/时效输入与 resolved 映射/作用域、已有 artifact guards，以及本项来源声明和级别投影。具体字段沿用这些现有 owner 的读取契约；不得在刷新另列一个只含路径、存在和级别的弱白名单。业务指纹不混入 level。

来源范围仅 selected candidate union 及该包实际合法消费的来源：

- index 中 file、future_work_sidecar、facts_sidecar 的声明区分无记录、未声明、显式空、规范路径和坏记录。正常接受核对实际 facts 的 analysis_file/sidecar_file/facts_file；声明、观测与实际消费不可混为一谈。
- 当前 analysis 对应固定 `.facts.json`、`.future_work.json` 候选继续按既有探测规则记录 present/missing；sidecar 字段 null 不取消固定候选探测。missing→present、删除、换址均可改变业务输入。
- 对已存在论文、facts、future-work、PDF 等实际载体同时复核既有 stat guards（包含已有的 size/mtime/ctime 等）和已取得的摘要。路径和存在不变不能证明内容未变。复用既有摘要，不为 U5 新增 PDF 全文 hash/来源认证。
- PDF 使用正常 facts.pdf_file 及其接受 guard，不发明 index PDF 字段、不扫描孤立 PDF、不重新查询 Zotero。离线早期只在相同正式本地输入和完整接受声明下检查该接受路径；新正式路径/删除声明优先 process。原无 PDF 只在同一本地输入且无新声明下维持无源，不声称验证了远程附件。
- index 的 generated_at、KB id 等管理字段不加入业务判等；不要以整个 index mtime 把纯 level 改动变为业务改变。来源资格除独立级别值外的变化不得走 level-only。

比较结果须区分相等、变化、不可比较。业务变化或不可比较首先 process；业务相等，仅 level/本项统计格式待更新才可 refresh_level；两者相等且原终态复用条件成立才可 reuse_all。显式 chatgpt_result、kb_import=true 保持 process 优先。预检只读，不认证新 facts 或写“已经接受”。

旧基线缺失，或由存在 null/known 分叉的 r3 实现建立而不能证明一致时，使用现有私有 preflight 格式修订使其保守失效，下一次 process 建立一致基线；不得依靠当前 index 补造历史消费事实，也不得直接 refresh 修复矛盾。此为懒处理，不批迁移；process 内分析、归属、时效仍分别按原有效性复用，并非全部重跑。只有普通成功接受可建立新业务基线；刷新只验证旧基线仍有效。

### 4.3 机制二（接受侧）：先验证完整旧绑定，再决定能否继承

在原 preflight/finalize/validation owners 之间复用分层判定；不能只把名字统一、底层仍分别少验。返回原失败类别及是否可继承，不造第二套认证记录。

第一层，旧文件/包/render 绑定：读取真实旧 pack 和实际文件；拒绝不受管、symlink 或不可读等原不支持状态；核对 managed_by、既有教授标题身份、header.state_fingerprint 对原旧包的既有 state fingerprint、原始 body SHA 对 header.render_sha256 及 cache.render 中对应 SHA。不能先同步 header、补 canonical 字段或改 cache 再声称旧绑定有效。无旧结果是首建，不构造虚假旧绑定。

第二层，旧 validator 绑定（存在记录时）：按原 schema、合法 round/phase/pending/结果结构核验；其 pack_sha256 对原始旧包的 content fingerprint（按现有规则排除 validator），render_sha256 对上述实际 body/header/cache，方向作用域按现有契约核对。合法 pending/第一轮状态与合法终态是不同结果；没有 validator 表示没有可继承校验结论，不伪造 PASS。

第三层，仅 reuse_all 额外要求既有 terminal、有效 round 和各方向 pass/skipped；fail_after_2_rounds、未完成/缺结果不满足快速复用。普通 finalize/refine 保留合法 round/phase/pending 的原生命周期，不能因共用判定而强迫所有入口终态通过。

旧合法性、实际 body 变化、业务认证依据变化三个事实分开：

- body 或业务实变：旧认证不再适用，保留原报告供追溯；不得因新 body 恰好相同保留已变业务的旧 PASS。
- 两者均未变且完整旧绑定合法：允许保留原合法 validator 状态，仅同步必要的新 pack 绑定。level 换位但聚合正文等价可落此分支，前提仍是完整守卫与旧绑定都成立。
- 旧绑定无效：任何入口均不得通过修头/重算 hash 自动恢复原通过结论。刷新停止并沿原证据/人工保护错误返回，不写“修复后等价”。普通过程若确实产生新业务/正文，只能按原受管冲突/显式覆盖政策接受为新未校验结果，不能继承失效认证；内容未变不能借普通 finalize 把同一失效证据重新签成通过。
- 旧 body 不可读或人工改动，沿既有读取错误/needs_decision；结构或绑定失配沿既有证据错误。不可判定不等于“没有旧内容”。不借 candidate 补旧身份，不自动覆盖人工文件。明确覆盖也不是继承旧 PASS 的授权。

### 4.4 机制三：从磁盘到 hash、比较和写回全程无损

Stage 2 的接受、preflight 绑定、validator 绑定、managed conflict 与写回共同采用同一无损读取/正文切片语义。使用原始 bytes（或严格 UTF-8 且禁止 newline 转换的等价实现）；不能在任何前置 `read_text()` 默认 universal-newline 转换后才调用“保留字节”比较函数。

frontmatter 解析以原文件分隔符的实际字节偏移取 body。兼容既有 LF/CRLF 文件识别，但不把分隔符、正文换行、尾换行、空格、BOM 等重新拼接或归一化；正文边界只去掉既有格式明确规定的结构分隔，不吞掉任意空白。无法解析或非法编码按既有错误保护，不修复后再称原绑定有效。

hash 对实际 body bytes 计算。算法仍为现有 SHA-256；LF 原文件无语义迁移。由旧换行归一化产生的不匹配记录不能自动续认。renderer 新正文严格编码一次形成候选字节，其他实际字节变化均算变化。

唯一比较豁免是 renderer 固定顶部生成标题位置的生成时间 token。定位依赖该固定结构和位置，仅在比较副本中忽略该 token；同一行统计、换行和其余正文不变。不在任意后续叙事行寻找“第一个看起来像时间”的正则匹配。真实 SHA 从不忽略时间。

若比较等价且旧绑定合法，保留旧实际 body bytes 和真实 SHA；无需变头则不写文件，需要绑定候选时只替换必要机器头并拼接原 body bytes，写入不得再做 text-mode 换行转换。若正文变化则按既有人工保护写候选字节。用同一 Stage 2 专用无损 primitive/显式选项贯穿各消费者，不顺带重构所有 stage 的 I/O，也不引入第二 renderer。

## 5. 完整执行顺序与并发边界

### 5.1 普通处理

1. 保持原 analyzer build→import→exact acquire（verify_plan=True）→finally release 流程。读取本轮实际来源，执行 §4.1 声明核对及现有 facts/业务资格；冲突早于接受写入返回。
2. 在任何兼容化/candidate 修改前，取得独立旧快照并执行 §4.3。候选构建的所有 canonical 分支采用 §4.1 当前结果；不共享旧 nested 对象。
3. 按 §4.2 对实际消费和写前当前状态作完整核对；消费后输入漂移则退回正常准备，不能以较新观测覆盖消费基线冒充已经消费。
4. 实际渲染完整候选，按 §4.4 比较与人工保护，按 §4.3 决定认证失效/合法继承。不能用 render_state、level 相等、统计相等或任务数零替代渲染。
5. 已知错误均在写前处理。受管文件接受完成后，按字段 owner 合并 cache，记录真实 render SHA、本项完成标识和实际接受的业务/级别基线，再沿现有持久路径提交 pack。不得清空无关有效缓存/U1 元数据。

### 5.2 专用级别刷新

1. 只使用持久包、当前有限观测和 Stage2PackRefineContext；不读取临时 facts、不运行模型/Zotero、不重签 resolved proof。原 stage2-refresh-level 命令保持窄用途。
2. 使用现有内部 acquire_local_lease(professor_dir, 本调用唯一 token, verify_plan=False)。busy 零业务写入返回；不伪造 handoff/_latest、不另建 lease、重入锁或 journal。
3. 获锁后重读旧 pack/Markdown/cache/validator 及完整 §4.2 当前观测，先校验预检 payload 对本次目标和接受基线的绑定，再重新执行同一个完整业务判断及级别解析。不消费预检缓存的“通过”替代重读。任何漂移/业务变化/不可比较零写入返回既有 needs_refresh，释放后重新预检并走 process；不边写边补基线。
4. 执行完整旧绑定检查、构造仅改当前 level 的隔离候选并真实渲染。缺可信渲染字段退回正常准备，不解析 Markdown 补数据。只允许 level、统计接受元数据及必要包绑定变化，不改成员、原模型结果、assignment、源接受资格和报告。
5. 在正式写入前再次确认本次读取快照未发生既有 guard 可观察的漂移，包含接受文件和完整业务来源，不只重查路径。确认后按普通接受的同一有限顺序写入；刷新不得建立新业务消费基线。旧 validator 若因正文变化失效，由原校验入口处理，刷新不自动启动模型校验。
6. 所有退出 finally 释放本调用 lease；释放失败如实报告，不能宣称已解除。

教授 lease 只序列化遵守该 lease 的本地 writer/importer，不能冻结外部 PDF、编辑器或远程 Zotero。上述重读和写前检查保证既有 stat/摘要契约下可观察的输入一致，不承诺任意外部并发修改的文件系统快照，也不以此增设全局锁。检查后发生的外部变动由下次既有 guard 拒绝复用；不把“当前已验证”写成永久来源认证。

Markdown 与 pack 是多文件写入，不宣称一次事务原子性。写入中 I/O 失败返回未完成，不补打接受成功/校验通过标记；保留已发生的真实状态，下一次由绑定/来源不一致阻止 reuse。不得自动通过修头或反填缓存掩盖中断；按正常恢复/人工保护处理。沿用现有单文件原子持久工具，不新增自动跨文件回滚承诺。

## 6. 实施落点、兼容和交付顺序

1. `_stage2_facts.py` 先收敛当前资格解析和 facts 一致性；两种 analyzer 的事实组装及来源失效处理描述同步。将旧 facts 缺字段重新组装与旧 accepted 包兼容分开。原 producer 成功登记 owner 不转移给 runner。
2. `_stage2_preflight.py` 将完整已有业务守卫抽为可复用的有限判断，与来源/level 读取通过 runner 注入。正常基线与锁内刷新使用同一规则；移除只检查路径/存在的替代 gate。修订原私有缓存版本以拒绝不一致旧基线。
3. 在原文件 owner 提供 Stage 2 无损 body 读取/切片/hash/受保护写入路径；让 preflight、finalize、validation 和 managed-conflict 实际调用它，避免一处修复、另一处重新归一化。
4. 在现有模块边界内收敛分层旧绑定判定和有限接受顺序；先旧快照、后候选，先核验、后写。普通、refresh 和原 refine 使用相同字节/绑定含义，终态复用政策仍只用于 reuse_all。refine 保留第一轮→第二轮及清 preflight 的既有行为，不延长失效基线。
5. 保持 canonical 字段贯通、renderer 三分类及业务 fingerprint 不含 level 的已有正确部分；只调整与新决定冲突处。U1 仍独立；若其先合入，仅适配共享接受 owner 与有效元数据，不再建立第二套接受机制。
6. 实施者先按当前最新 head 对本计划列出的职责做语义定位，不机械恢复旧 main/旧 #92。完成后独立审核关注三个机制是否闭合和既有行为是否保留；不能凭局部 helper 命名或旧测试数量宣称完成。

公开 schema 保持 2；无批量旧文件改写。缺乏历史业务基线触发正常 process 是保守兼容，不是强制重新分析；旧受管文件失效不可自动认证的限制同样适用迁移。正式观察入口仍为 facts/canonical level、原统计标题、preflight 分流及既有受管/校验结果，无新日志账本或认证 API。

## 7. 影响、限制及审核边界

- 保持：scope、成员/引用身份、resolved 接受政策、facts/future-work 资格、模型复用、人工保护、lease、校验轮次和既有错误通道。
- 纠正：矛盾 null 不再被接受；合法新成功不被旧包压制；完整守卫覆盖锁内刷新；旧绑定不能自动续认；真实换行/正文差异不能被吞掉。
- 明确限制：离线源观测不是远程附件查询；stat 不是无限强内容认证；协作 writer lease 不是外部文件锁；单文件原子写不是跨文件事务。来源 owner 未反映失效时拒绝冲突，不擅建状态认证机制。实现必须暴露这些真实限制而非承诺绝对不存在并发窗口。
- 待核实项：r4 是设计候选，当前产品仍存在已定位分叉。共用谓词接线、字节边界和所有入口行为须由后续实现/独立审核核实；本文不声明无风险或全部通过。
- 不扩大：不做完整业务回归/边界矩阵、来源过程认证、全教授扫描或新框架。是否复用既有测试结果由测试 owner 根据行为变化判断，不因文档 SHA 重跑无关项目。

## 8. r3 → r4 取代记录及下一负责人

1. 取代 r3 对“本轮 null 清除，但下轮看成功登记”的含混双权威：统一 known/unknown/invalid，冲突拒绝；来源失效归原 owner；新成功可再转移。旧 accepted 缺字段兼容不等于新 facts null 声明。
2. 将“完整来源检查/合法旧绑定”从原则细化为共同谓词、各入口职责、原始基线、锁内及写前顺序；普通合法 pending 与终态 reuse 条件分层。旧 PASS 不可通过机器头同步恢复。
3. 将“仅忽略生成时间”落实到真实 I/O、frontmatter 切片、hash、比较、冲突检查和写回全链；消除 read_text 前置归一化漏洞，而非继续修正正则一处。
4. 保留 r3 已确认的统计集、U1 独立、无模型强制重跑、无新认证平台/全局事务边界；替换其“无未验证核心假设”和“尚未产品实施”的过期描述。

下一负责人：独立非作者计划 reviewer 对完整 r4 按 P1–P4 复核，重点为上述三个变更及相邻兼容/校验生命周期；作者不继承或自授旧批准。测试负责人审查受影响来源、null 转移、绑定继承和字节语义与现有测试计划/结果的适用关系；本次不改测试计划或运行测试。计划审定后由产品 owner 按唯一正文实施，之后再据实际 diff 和证据审核，不把计划批准当实现或测试完成。
