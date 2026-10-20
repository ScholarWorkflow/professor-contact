# Stage 2 U1 测试计划：固定证据展示与真实阻挡归属

- Test plan revision：`stage2-u1-t3`，2026-10-21；沿用 t2 的六项必测目标，仅明确 U1-F 两个既定场景的字段、输入与步骤；§7 原样保留 2026-10-20 的实际执行记录。
- 唯一正式路径：`plan/stage2-fixed-evidence/test-plan.md`；执行步骤补在本文件，不另建相互补充的测试手册。
- 范围依据：用户 2026-10-20 明确授权 U1/U5 计划及“测试计划也改”；U1 正式目标与保留行为见 [execution plan r3](https://github.com/ScholarWorkflow/professor-contact/blob/9874d8344d55d37b61d12acb0f356c3f4fae6d00/plan/stage2-fixed-evidence/implementation-plan.md) §§1、3。本文不继承 #92 的 t47、审核或测试通过状态。
- 静态核对基线：`ScholarWorkflow/professor-contact@879982abe1d7d811bd9d014c03dce4f5912cc64f`。这是现有模块/测试资产基线，不是已实现 U1 的产品版本。
- 规则：[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)（2026-10-09 20:37 UTC），[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)（2026-10-19 14:02 UTC）。2026-10-20 已重新读取。
- 当前交付（2026-10-21）：U1-A/B/C 的 t2 补充断言已在当前代码提交 `1fe59bce` 的 CI 中逐项通过；U1-D/E 的既有通过结果有效。U1-F 的“固定证据正文实际改变”和“仅旧校验绑定失效”仍缺与目标相符的测试输入，本版明确其具体修改字段、流程和判定，测试代码与补测尚未完成。§7 历史执行记录不改写；正式测试关口仍待独立审核。

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

- 业务目标：当前无效题名不能被旧标题掩盖，无法解析的实际引用在写入前失败，给出可处理的数据责任。
- 输入/场景：在 U1-A 的隔离输入上，分别使实际显示引用的当前题名明确为空/无效（旧包有旧题名），以及一个明确 Zotero 引用没有可信记录；不扩所有 key/标题格式组合。
- 预期：返回定位到 gap、字段和 key 的缺失信息，交数据准备 owner；旧正文/受管包不被接受为新成功，不造题名、不删证据、不沿用旧题名掩盖当前明确无效。当前来源未提供某记录但旧 canonical 仍有效，以及旧禁锚无完整候选列表但实际引用能解析的合法复用，按 U1-E 检查，不能一概阻断。
- 检查方式：正常 finalize 返回信息须足以定位固定输入指定的 gap、字段和 key（机器字段或可理解的错误文字均可），并比较失败前后的受管 Markdown 与输入包，确认未被覆盖或冒充成功。不新增错误码规范、采集器或来源证明。

### U1-C：合法报告按真实片段归属，保留已有定位/排除边界

- 业务目标：固定卡合法 blocking 可登记并给出 source/generator owner；实际 narrative 不因长得像模板而误归固定；原本排除区仍排除。
- 输入/场景：同一正常生成的报告包含可定位的固定源文字与模板文字，包含一个跨行源值的续行、一个模板和值同一行的命中及一个 summary 缺失后回退原句的命中；用短 location 加全文唯一 quote，另用实际物理行号区分重复 quote。保留一处带模板字样的真实 narrative 对照。只选这些直接决定归属的代表性片段，不穷举换行符、字段、方向和 quote 的笛卡尔积。
- 预期：源值/回退原句交 source，确定性模板交 generator，稳定方向/gap/字段正确；允许同句涉及多个固定 owner，不因无法选唯一 owner 拒绝真实失败；真实 narrative 仍沿原权限。短 location 不被强制换成数字。歧义 quote 仍拒绝，不猜位置；用户笔记等既有排除区不变为合法固定报告目标。原 issues/notes/verdict 与原报告文件保留。
- 检查方式：比较 `stage2-record-validation` 返回和持久 validator；归属的方向、gap、字段与 source/generator 责任须对照事先确定的测试输入，不得用返回的 `rows[0]["gap_id"]` 生成自己的预期。复用既有重复 quote/短 location、用户笔记场景中适用的检查，不通过反解析标题制作第二套 owner 判定器。

### U1-D：登记失败不授权模型改事实；narrative 两轮仍可用

- 业务目标：固定 blocking 停自动修订，纯 narrative 保留一次修订、第二轮校验；minor 不升级为阻挡。
- 输入/场景：第一轮合法固定 blocking 与 narrative blocking 混合报告；另一条纯 narrative 第一轮报告完成一次正常 refine 后，第二轮首次出现固定 blocking。复用既有 minor 与 narrative later-title 合法报告场景。固定报告对两个 refine 入口各检查一次，其中使用方向过滤，确保不能绕过整报告阻挡。
- 预期：第一轮登记 `needs_correction`、round=1，明确责任；`stage2-refine-plan` 无 rewrite jobs，`stage2-refine-finalize` 不消费 rewrite 改正文。固定失败不变 pass/skipped。纯 narrative 第一轮仍产生允许修订，refine 后保留第一轮状态并等待第二轮，第二轮固定问题仍能正确定位，终态为 `fail_after_2_rounds` 而非重开轮次。minor 保持非阻挡。原两轮/顺序约束继续适用，不要求穷举非法状态组合。
- 检查方式：两 refine 入口返回、正文与 validator 前后状态；用已存在结构化 narrative rewrite 夹具而非模型生成。核对主 SKILL、Codex/OpenCode analyzer 中本次改动的“登记→交 owner 停止/修订”说明与上述分支相符即可，不加双 harness runtime。

### U1-E：旧包正常使用时更新展示，复用有效工作

- 业务目标：已有报告也得到 U1 修复，且不为展示更新强迫模型重算或引入新命令。
- 输入/场景：一份旧包缺 U1 展示完成信息，有仍有效分析/freshness/narrative/resolved 资产；旧禁锚有仍有效 freshness cache 可补引用元数据。再使用同一兼容路径中无完整候选列表、但已持久完成论文/明确引用均可解析的旧包。旧包不要求来自 #92 私有版本。
- 预期：现有 preflight→process→plan→finalize 通路完成更新；仅缺 U1 展示完成信息不产生额外模型 jobs，不改变有效来源判定。有效 cache 可以补实际需要的引用；缺无用候选列表不新增阻挡，无效 cache 不被当来源猜题名。实际引用无法解析只按 U1-B 交源。接受前或冲突/失败时不能标成功；接受后的四出口正确，后续不再仅因缺 U1 信息反复 process。另一有效功能的 render 元数据不被整块抹掉。
- 检查方式：现有 preflight/plan/finalize 返回（含 jobs）、最终正文/包；复用 U1-A 与 U1-F 的观察，不另做历史版本批量迁移测试。不要求 U5 已实现或通过。


### U1-F：普通接受区分正文、业务、绑定和旧校验，保护人工正文

- 业务目标：展示/时间更新不能洗掉两轮限制或救活失效校验；真实改动不能沿用旧通过，人工正文始终受保护。
- 输入/场景：从有效旧 validator 的包出发，保留已定义的非业务展示/时间差异、业务指纹变但正文等价、顶部来源行非时间文字改变及人工正文冲突检查。以下两个原本已列入 U1-F、但旧测试输入没有真正落实的场景固定为：
  1. **固定证据正文实际改变**：用现有 `generate_pack(gap_override())` 建立已校验通过的报告；只修改模型结果文件 `results/freshness-DIR00001.json` 的 `results[]` 中 `gap_id == contact_state.quote_id(gap_quotes["AAAA1111"])` 那一条的 `evidence`。旧值为“后续由 CCCC3333 完成，日期 2024-05-01，未知 DDDD8888 与 12345678 保留。”；新值为“后续由 CCCC3333 完成，日期 2024-05-01，未知 DDDD8888 与 12345678 保留；新增固定证据对照。”。其他模型结果字段保持不变；从隔离 `_freshness_cache.json` 的 `entries` 中仅删除该 `gap_id` 对应缓存，保证正式通路确实消费新结果。禁止用修改 `facts.directions[].user_note`、已生成的 `套磁候选分析.md` 或已接受包来代替本场景。
  2. **旧校验绑定单独失效**：另起隔离环境用 `generate_pack()` 建立报告，登记空问题报告并确认旧 `validator` 原本有效；保持 `facts.json`、模型结果、包内 `directions/papers/cache`、`套磁候选分析.md`（包括机器头与正文）及原始校验报告不变，只将 `套磁候选输入.json` 中 `validator.pack_sha256` 改为 64 个 `0`，其余 validator 字段不变。此时只存在旧校验对当前包的绑定失效；禁止追加“人工改动”或修改机器头制造失败。
- 预期：仅非业务差异时保留旧 body 字节、合法 round/phase/pending/results，必要头更新与新包绑定一致；候选组装不得先改旧比较基线再错误保留旧状态。场景 1 正式 finalize 必须将新 `evidence` 写入目标 gap 和 Markdown 固定证据字段，正文实际改变、旧 `validator` 不再作为通过结果，原校验报告文件保留。场景 2 在业务与正文未变时必须返回拒绝（现有 `validation_render_stale`），输入包与 Markdown 不被写回或自动重绑，旧通过结果不得被救活。业务指纹真实改变即使正文等价仍使旧校验失效；人工正文冲突返回 `needs_decision`、不记展示成功。现有写入/保存若失败不得返回成功或伪造通过，不新增跨文件事务框架。
- 检查方式：使用既有 `test_u1_f_acceptance_separates_body_business_binding_and_validator` 方法和合成 Stage 2 夹具，只替换原来 `user_note` 变化与追加人工文字充当旧绑定失效的两段输入。两场景的准备、缓存处理、正常 `preflight → stage2-plan → stage2-finalize` 入口与逐项断言在 §6.3、§6.4 固定；对照事先给定的字段值及输出，不以单独观察 `validator` 被删除代替正文更新。其余 U1-F 已有效场景和人工正文保护断言保留。共享接受可复用 U1/U5 已有效的同目标结果，不要求双 PR 重跑或扩大到 U5 范围。

## 3. 已核对的现有资产与缺口

以下路径均在 [.apm/skills/professor-contact/tests](https://github.com/ScholarWorkflow/professor-contact/tree/879982abe1d7d811bd9d014c03dce4f5912cc64f/.apm/skills/professor-contact/tests)。它们是可复用实现/夹具，不是本轮已执行结果，也不要求整文件或全测试类重跑。

- `test_contact_state.py` 的 `BaseEnv`、`write_facts`、`write_stage2_results`、`stage2_run_two_directions` 已提供隔离目录、结构化 facts/freshness/narrative 和正常 finalize；`run_bound_stage2_plan`/`run_bound_stage2_finalize` 来自现有 `stage2_upstream_fixture`，不是可跳过正式 preflight 的替身。U1-A/B/E 可在这些既有资产上补本轮场景。
- `TestRunnerBasics.test_stage2_end_to_end_and_blacklist` 已观察禁锚与 Markdown，未覆盖 U1 四出口可信转换，不能拿现有通过代替 U1-A。
- `TestRunnerBasics.test_11a_stage2_validator_pass_with_minor_is_accepted` 已检查 minor 持久状态与零修订；`test_13_stage2_validator_rewrite_round_trips_structured_narrative` 已有 narrative refine 观察，可按实际影响复用 U1-D。
- `test_stage2_style_validation_handoff.py` 的 `Stage2ValidationHandoffTests` 有 `write_validation_issues`、`record_validation`、`rewrite_direction`；`test_repeated_quote_locations_and_ambiguous_report` 已有物理行号/短文本/歧义，`test_stage2_nonrepairable_user_note_does_not_create_a_correction_job` 已有排除区域，`test_stage2_second_blocking_round_is_terminal` 已包含 narrative later-title 和两轮流转。U1-C/D 复用这些资产并仅接线新增固定行为，不把旧方法中所有历史要求带入清单。
- 同文件 `test_business_rerender_and_bounded_correction_lifecycle` 已有旧包、preflight/plan/finalize、保留旧报告与生命周期观察；它含历史成员迁移等非本轮目的，不能整组照搬为 U1 义务。仅复用适合 U1-E/F 的夹具/观察或有效结果。
- `test_stage2_preflight.py` 中 `TestPreflightDecision.test_a_legacy_pack_falls_back_to_process`、`TestFinalizePreflightWiring.test_legacy_slow_path_seeds_metadata_for_next_run` 提供旧包通路的既有检查思路；U1 的独立完成信息、四出口、固定报告归属及保护行为仍需产品实现后接线。
- `test_contact_state.py::test_08_manual_markdown_edit_needs_decision` 实际检查 Stage 3，不能冒充 U1-F 的 Stage 2 人工保护结果。U1-F 应在现有 Stage 2 夹具里观察本次正常 finalize，而非扩跑 Stage 3。

不要求新增通用 fixture、专用判定器、逐调用记录或来源认证。U1 的六个专用测试方法已入库，保持现有方法与合成夹具；新增检查只填补原定目标的实际断言，不增加业务场景数量或运行时前置。

### t2 对现有测试代码的最小补齐（断言已补齐，尚未执行）

- U1-A：现有 `test_u1_a_trusted_citation_display_keeps_facts_and_licences` 已检查可信链接的总次数、部分原文及许可集合；已在该方法内按四个实际出口分别比较引用及证据文字，避免某个出口遗漏或改写却因总数正确而通过。
- U1-B：现有 `test_u1_b_missing_trusted_metadata_fails_before_write` 已检查失败、论文 key 和文件未写入；已补固定输入对应的 gap、字段定位，确认返回的错误可交数据 owner。无需新设固定错误码。
- U1-C：现有 `test_u1_c_report_ownership_uses_real_fragments` 对 gap 的断言曾使用返回值 `rows[0]["gap_id"]` 自身；现已改为预先确定的输入 gap 预期，其余责任分类沿用既有断言。
- U1-D/E/F：若产品及相关测试行为未变，直接复用 §7 的有效结果；上述 A/B/C 的断言补齐不构成重跑 D/E/F 的理由。


## 4. 执行与结果复用约定

1. 六项 U1-A 至 U1-F 是必测上限。使用既有 `test_stage2_fixed_evidence.py`、合成 Stage 2 输入、正式 `contact_state` 命令入口和 `unittest` 断言；无须真实模型、Zotero、PDF、安装或双运行环境测试。
2. 2026-10-20 `3d6c2bc` 的本地六项执行、185 项既有检查及 1036 项补充全仓回归记录见 §7，保留原始事实，不作为 t3 的重复执行义务。
3. t2 补齐的 U1-A/B/C 三项断言已在当前产品/测试代码 `1fe59bce356a8c75fe45fe2367cb55690c276081` 的 [CI 第 39466214174 次运行](https://github.com/ScholarWorkflow/professor-contact/actions/runs/39466214174)（第四测试组）逐项通过；U1-D/E 亦通过且本轮输入、断言和产品行为未变。直接复用这些结果，不因测试计划更新或提交编号变化重复运行。
4. U1-F 旧测试方法在同一 CI 中显示通过，但 §6.3、§6.4 的两项固定输入尚未写入该方法，不能将原通过外推到这两个场景。本地测试工程师仅修订同一个 U1-F 方法中的两段输入及对应断言；修订后只需按 §6.5 运行该方法一次。其余 U1-F 既有有效检查继续沿用。
5. 执行者记录实际提交、测试命令、退出码、逐项结果和运行日志位置；已有有效记录直接引用。正式测试仅在仓库外隔离目录写临时产物；发现范围内业务失败时保留当次记录并交产品负责人，不修改预期或重复采样求通过。


## 5. 当前状态与下一负责人

- 第一关：必测清单仍为 U1-A 至 U1-F；本版没有新增目标、边界组合或测试设施，原范围结论不因场景细化重开。
- 第二关：t3 已具体写出两个既定场景的输入、检查和运行步骤，等待独立审核；计划入库不自动视为批准。
- 第三关：U1-A/B/C 在 `1fe59bce` 的 CI 已逐项通过，U1-D/E 的适用结果有效。U1-F 既有方法在该 CI 通过，但“固定证据实际改变”和“旧绑定单独失效”尚未得到符合本计划输入的结果，记为**待补**；其余已有效的 U1-F 检查继续复用。§7 是 2026-10-20 的历史记录，不能冒充 t3 补测。
- 下一负责人：本地测试工程师只在既有 U1-F 方法中落实 §6.3、§6.4 两个场景；第二关确认后由本地执行工程师按 §6.5 执行该方法，记录版本和结果；审核者只复核受影响项。合并审核独立进行。


## 6. 可执行步骤（t3，2026-10-21；两个 U1-F 场景尚未补入测试代码、未执行）

### 6.1 准备与已有结果

- 从第 107 号 PR 的目标仓库工作树执行，先确认实际提交。t3 修订前的产品/测试代码为 `1fe59bce356a8c75fe45fe2367cb55690c276081`；本次仅修改测试计划，不改产品代码或现有测试方法。
- 使用现有 `FixedEvidenceBase`、`generate_pack`、`gap_override`、`write_report`、`record`、`preflight`、`bind_facts_to_preflight`、`finalize`；每个场景通过 `_fresh_env()` 得到独立合成目录，不访问用户 Zotero/真实论文或生产配置。
- [CI 第 39466214174 次运行](https://github.com/ScholarWorkflow/professor-contact/actions/runs/39466214174)在 `1fe59bce` 的第四测试组逐项执行 U1-A/B/C/D/E/F，六个方法均显示通过，组结果为 249 项（跳过 1 项）且成功。A/B/C 的 t2 补充断言确已执行；本轮不重复这些方法。该记录对 U1-F 下述缺口不构成通过证明。
- 每次新运行的输出放进单独 `mktemp -d` 创建的仓库外 `/tmp` 目录，不共享可写临时目录并发执行，不复制或修改生产数据。

### 6.2 U1-F 原有可复用检查

原有生成时间/展示变化、必要机器头更新、业务指纹改变但正文等价、顶部来源行非时间文字改变及人工正文冲突检查保留在同一测试方法中；不因以下两处场景输入修订另造新方法或重复其他 U1 必测项。历史通过记录仍可作为对应未受影响行为的依据。

### 6.3 场景一：修改正式固定证据输入并重新接受

1. 在独立环境调用 `generate_pack(gap_override())`，保持既有合成论文 `CCCC3333` 的题名、引用和许可不变。登记 `write_report("u1f-fixed-pass.json", [])` 生成的报告，确认 `record()` 返回 `status=ok`，旧 `validator` 的 `schema=2`、`round=1`、`phase=terminal`，并保存旧正文与原始校验报告内容。
2. 固定目标 `gap_id = contact_state.quote_id(env.gap_quotes["AAAA1111"])`。读取 `results/freshness-DIR00001.json`，找 `results[]` 中恰好一条 `gap_id` 等于该值的记录；先断言旧 `evidence` 完全等于“后续由 CCCC3333 完成，日期 2024-05-01，未知 DDDD8888 与 12345678 保留。”，然后只把该字段写成“后续由 CCCC3333 完成，日期 2024-05-01，未知 DDDD8888 与 12345678 保留；新增固定证据对照。”。`status`、`candidate_paper_ids`、`completed_part`、`remaining_gap`、其他 gap 结果和 `facts.json` 的业务字段均不修改。
3. 读取同一教授隔离目录的 `_freshness_cache.json`，仅从 `entries` 删除上述 `gap_id` 的记录并保存，强制正式处理路径重新消费被修改的 freshness 结果；其余缓存记录保持不变。这是清除受测输入对应的旧缓存，不改变产品算法或业务预期。
4. 运行现有 `stage2-preflight`，确认进入 `process`；将本次返回值写为新预检文件，并用 `bind_facts_to_preflight(facts_path, payload)` 将当前 `preflight_id` 绑定到同一 `facts.json`。调用 `stage2-plan --facts ... --preflight-file ...`，确认正常返回且当前方向确实需要 freshness 结果；沿用已存放在 `results` 的合成结果，不启动模型。
5. 调用正式 `stage2-finalize --facts ... --preflight-file ... --results ...`，确认 `status=ok`。读取新 `套磁候选输入.json`，按事先计算的 `gap_id` 找到对应 `directions[0].gap_shortlist[]`，断言 `evidence` 与步骤 2 新值一致；读取 `套磁候选分析.md`，断言固定卡“后续论文依据”出现“新增固定证据对照”，旧正文与新正文确实不同，可信 `CCCC3333` 链接仍正确。
6. 断言旧 `validator` 不再作为当前包的通过状态（本实现中为不再存在 `validator`），原始 `u1f-fixed-pass.json` 文件字节不变。不能只见 `validator` 被清除就宣布通过：步骤 5 的固定证据新值和正文真实改变都必须成立。失败保留原样并按 §6.6 处理。

### 6.4 场景二：只使旧校验绑定失效

1. 另起 `_fresh_env()`，调用 `generate_pack()`、`write_report("u1f-stale-pass.json", [])` 和 `record()`。确认 `record()` 为 `status=ok`，原包 `validator.schema=2`、`round=1`、`phase=terminal`，且修改前 `validator.pack_sha256 == contact_state.stage2_pack_content_fingerprint(pack)`。
2. 只将此隔离目录中 `套磁候选输入.json` 的 `validator.pack_sha256` 设置成 `"0" * 64`。修改后确认它不等于当前 `stage2_pack_content_fingerprint(pack)`；`validator` 的其他字段、`directions`、`papers`、`cache`、`facts.json`、`results`、完整 `套磁候选分析.md`（包括机器头）及原始校验报告全部不变。**不得**追加人工文字或手改机器头；那会变成不同的手改保护场景。
3. 在调用前保存已修改输入包、完整 Markdown、事实输入文件和原始校验报告的各自字节。沿用 `generate_pack()` 已合法绑定的 `facts_path`、`proof` 和 `results`，直接调用正常 `stage2-finalize`，不重建初始包、不给修复决定文件、不通过额外测试入口。
4. 预期返回 `status=error`，现有原因码为 `validation_render_stale`；调用前后上述四个文件的字节逐一相同，`validator.pack_sha256` 仍是 64 个 `0`，不被自动改为有效值，旧校验不能重新成为通过。只核对这个具体失效和拒绝行为，不另建防篡改或绑定认证测试。
5. 保留现有测试方法末尾的独立人工正文冲突分支：无旧 validator 时人工追加正文，应返回 `needs_decision`。不得用这个分支替代步骤 1—4 的“业务和正文不变、仅旧绑定失效”。

### 6.5 本版唯一待补执行：修订后的 U1-F 方法

由本地测试工程师在现有 `test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_f_acceptance_separates_body_business_binding_and_validator` 中替换两段旧输入与对应断言，保持同一方法名与其他已有效分支不变。第二关确认后，由本地执行工程师从第 107 号 PR 当前工作树运行：

```sh
set -eu
REPO_ROOT="$(git rev-parse --show-toplevel)"
RUN_DIR="$(mktemp -d /tmp/pr107-u1-t3.XXXXXX)"
printf 'HEAD=%s\nLOG=%s\n' "$(git -C "$REPO_ROOT" rev-parse HEAD)" "$RUN_DIR/u1-f.log"
cd "$REPO_ROOT/.apm/skills/professor-contact/tests"
if uv run --no-project python -m unittest -v \
  test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_f_acceptance_separates_body_business_binding_and_validator \
  > "$RUN_DIR/u1-f.log" 2>&1; then
  cat "$RUN_DIR/u1-f.log"
else
  result=$?
  cat "$RUN_DIR/u1-f.log"
  exit "$result"
fi
```

预期 `Ran 1 test`、该方法显示 `ok`、退出码 0、无 `FAIL/ERROR/skipped`，且测试方法内 §6.3、§6.4 的输入与断言均已实际落地。若测试代码未按上述输入修改，原方法继续通过也不能关闭 U1-F 待补项。U1-A/B/C/D/E 不因本方法补齐而重跑。

### 6.6 失败、重试和停止

- 业务断言失败：记录对应 U1-F 场景失败，保留日志及当次实际版本，停止该项；由产品负责人处理已确认的产品问题，不修改断言或输入求通过。
- 可重试外部故障仅限已确认可恢复的启动/依赖中断或临时目录占用冲突，且此前没有确认的业务失败；在原因消除、产品/测试版本及输入和入口不变、没有非幂等业务副作用时，最多补试一次（总计两次），重新创建独立临时目录并保留每次日志。
- 故障未恢复或第二次仍不能判断业务结果：停止并记无法判断。若改变产品提交、测试断言、输入、入口或配置，视为正式修订后复核受影响项，不记作同条件重试。范围外失败只报告事实及影响，不扩 U1 必测清单。

## 7. 执行结果（2026-10-20）

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
- 本版确认 U1-F 旧代码中修改 `facts.directions[].user_note` 的分支不能证明固定证据正文变化；把人工文字追加到 Markdown 的分支不能证明业务与正文不变时的旧绑定独立失效。因此 U1-F 的上述两个既定场景仍**待测试代码修正和一次定向执行**；其余 U1-F 有效结果保留。U1-F 当前整体不作完整通过结论。
- t3 只修改唯一正式测试计划，没有修改产品、测试代码或配置，没有运行测试。§7 的 2026-10-20 原始尝试、并发临时目录错误、复验与全仓回归记录保持原样，不用后续结论覆盖历史记录；正式第二、第三关及合并仍独立审核。



- 本轮先只改正式测试计划，随后补齐 U1-A/B/C 三个既有测试方法的断言；没有修改产品实现、配置、环境或 §7 的历史执行记录，也未执行新测试。§7 所列六项通过、185 项复验、1036 项补充回归及首次临时目录冲突均保留原始事实。
- 修订前核实的 PR head 是 `087df10ea0853b58168076789c8180848d80f63b`；与 `3d6c2bc` 相比只有三份计划/审核文档改动，当前提交的持续集成 `39455636835` 五个作业均成功。文档修订提交本身不改变上述代码适用性。
- **待补结果**：U1-A、U1-B、U1-C 的测试断言已按 §3 补齐（2026-10-21），但补强后的三个方法尚未按 §6.2 执行，因此第三关的这三项目标暂不作完整通过结论。
- **可复用结果**：U1-D、U1-E、U1-F 的 2026-10-20 已有有效结果继续成立，除非后续提交直接影响其受测行为。
- 本版计划修订不自动批准第二关、第三关或合并；后续审核只核实本版改动及待补检查，不重开无关项目。
