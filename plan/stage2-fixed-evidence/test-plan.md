# Stage 2 U1 测试计划：固定证据展示与真实阻挡归属

- Test plan revision：`stage2-u1-t2`，2026-10-21；本版替代 t1 的执行安排，§7 原样保留 t1 的实际执行记录。
- 唯一正式路径：`plan/stage2-fixed-evidence/test-plan.md`；执行步骤补在本文件，不另建相互补充的测试手册。
- 范围依据：用户 2026-10-20 明确授权 U1/U5 计划及“测试计划也改”；U1 正式目标与保留行为见 [execution plan r3](https://github.com/ScholarWorkflow/professor-contact/blob/9874d8344d55d37b61d12acb0f356c3f4fae6d00/plan/stage2-fixed-evidence/implementation-plan.md) §§1、3。本文不继承 #92 的 t47、审核或测试通过状态。
- 静态核对基线：`ScholarWorkflow/professor-contact@879982abe1d7d811bd9d014c03dce4f5912cc64f`。这是现有模块/测试资产基线，不是已实现 U1 的产品版本。
- 规则：[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)（2026-10-09 20:37 UTC），[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)（2026-10-19 14:02 UTC）。2026-10-20 已重新读取。
- 当前交付（2026-10-21）：按已有审核问题修订六项既定目标的检查方式、执行命令及重试约定，并补齐 U1-A/B/C 三个既有测试方法的断言；上述三个方法尚未执行。§7 记录的 2026-10-20 执行事实继续有效，但不自动证明 t2 的三项补强检查已完成。正式测试关口由对应负责人审核。

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
- 输入/场景：从有效旧 validator 的包出发，最少覆盖三种真实差异：仅固定顶部生成时间/派生展示元数据或 collection key 更新；真正固定证据正文变更；业务输入指纹变化但输出正文等价。前者需要必要机器头更新时仍观察头更新。另在未改业务/正文的旧绑定失效状态与人工改正文状态检查拒绝。用一处正文含来源分隔字样的实际修改确认并非整行或泛分隔符忽略，不扩大文本边界矩阵。
- 预期：仅非业务差异时保留旧 body 字节、合法 round/phase/pending/results，必要头更新与新包绑定一致；候选组装不得先改旧比较基线再错误保留旧状态。实质正文或真实业务变化使旧 validator 不再作为当前通过，历史报告保留。无变化的坏旧绑定不能被重绑洗成有效；人工改正文返回 `needs_decision`、不记展示成功。现有写入/保存若失败不得返回成功或伪造 PASS，不为此新增跨文件事务框架。
- 检查方式：正常 finalize 的返回与受管正文/头、包及 validator 的必要字段。绑定失效用既有 validator/render 状态机制的隔离输入，不恢复已撤回的“任意手改机器 header 防伪”测试。共享接受可复用先落地 U1/U5 已有效的同目标结果；未有结果时由先实现者接线，不要求两个 PR 各执行整组。同入口复用时只补本轮实际改变的 U1 接线/行为，U5 level-only 入口及统计不纳入。

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

1. 六项 U1-A 至 U1-F 是必测上限。使用既有 `test_stage2_fixed_evidence.py`、合成 Stage 2 输入、正式 `contact_state` 命令入口和 `unittest` 断言；无须新增真实模型、Zotero、PDF、安装或双运行环境测试。
2. 2026-10-20 已在产品/测试实现 `3d6c2bc` 执行六项，记录见 §7。与此版本相比，修订前 PR head `087df10` 只改变三份计划/审核文档，相关代码未变；因此原执行记录可依适用性继续使用。
3. t2 仅补足 U1-A/B/C 现有方法对既定目标的判断能力。由本地测试工程师在正式计划步骤获批准后修改这些断言，再按 §6 **只运行受影响的三个方法**；U1-D/E/F 使用原有效结果。新增测试代码若直接影响其他已确认目标，再逐项判断是否需要复验。
4. §7 中 185 项既有测试、1036 项全仓回归及静态编译都是已经发生的补充检查，保留其结果，不再作为 t2 的执行义务或第三关通过条件。现有测试资产按 §3 复用，不要求因测试计划改版而重跑完整测试组。
5. 执行者记录实际提交、测试命令、退出码、逐项结果和运行日志位置；已有有效记录直接引用。正式测试仅在仓库外隔离目录写临时产物；如执行中发现产品业务失败，保留原记录并交产品 owner，不为了得到成功结果修改断言或重复采样。

## 5. 当前状态与下一负责人

- 第一关：必测清单仍为 U1-A 至 U1-F，没有新增范围；是否正式通过以独立关口审核为准。
- 第二关：本版已经明确限定正式执行范围、失败处理、精确命令和结果来源，等待独立审核；文件修订不代表自动批准。
- 第三关：§7 原记录中六个方法均曾成功执行。U1-A/B/C 的断言已按 t2 补齐（2026-10-21，未执行）；补强后的三项结果暂记**待补**；U1-D/E/F 在相关实现未变化时复用 `3d6c2bc` 的有效结果。不得把六项旧测试全绿写成三项补强已经完成。
- 下一负责人：本地测试工程师只补 §3 所列的三个既有断言，并按 §6 保留运行结果；测试计划审核者随后只复核 t2 的改动、实际影响和待补项。合并审核独立进行。

## 6. 可执行步骤（t2，2026-10-21 修订；本版尚未运行）

### 6.1 准备与检查入口

- 从第 107 号 PR 的**目标仓库工作树**执行。先确认工作树提交；本计划修订前的有效 U1 产品基线是 `3d6c2bc`，当前已核实 PR head `087df10` 对此只有文档变更。补断言后以实际新提交为运行版本，并按变更内容核对结果适用性。
- 沿用已具备的 `uv run --no-project python`、`unittest`、`test_contact_state.BaseEnv` 和 `stage2_upstream_fixture`；各测试方法创建、清理自身隔离的合成输入。无需重新安装、配置模型、启动服务或接入个人 Zotero。
- 本轮只补 U1-A、U1-B、U1-C 三个已存在方法的断言。U1-D/E/F 使用 §7 的结果；若未发现直接影响，不为提交编号变化重复执行。
- 将每次尝试的日志放在用 `mktemp -d` 新建的独立 `/tmp` 目录；不可共享同一个可写目录并发执行，不复制或手动修补生产文件。

### 6.2 唯一待补的三个方法

在完成 §3 的三个断言修订、第二关确认后，从目标仓库工作树运行以下命令。命令不使用会遮蔽测试退出码的管道：

```sh
set -eu
REPO_ROOT="$(git rev-parse --show-toplevel)"
RUN_DIR="$(mktemp -d /tmp/pr107-u1-t2.XXXXXX)"
printf 'HEAD=%s\nLOG=%s\n' "$(git -C "$REPO_ROOT" rev-parse HEAD)" "$RUN_DIR/u1-abc.log"
cd "$REPO_ROOT/.apm/skills/professor-contact/tests"
if uv run --no-project python -m unittest -v \
  test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_a_trusted_citation_display_keeps_facts_and_licences \
  test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_b_missing_trusted_metadata_fails_before_write \
  test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_c_report_ownership_uses_real_fragments \
  > "$RUN_DIR/u1-abc.log" 2>&1; then
  cat "$RUN_DIR/u1-abc.log"
else
  result=$?
  cat "$RUN_DIR/u1-abc.log"
  exit "$result"
fi
```

预期：`Ran 3 tests`，三项均为 `ok`，退出码 0，没有 `FAIL`、`ERROR`、`skipped`。检查 U1-A 四个出口、U1-B 定位和写入保护、U1-C 固定输入对应归属的断言实际存在并通过。仅运行旧断言，即使命令成功，也不足以关闭这三项待补。

### 6.3 失败、重试和停止

- 业务断言失败：标记对应必测项失败，保留日志及当次实际版本，停止该项；由产品 owner 处理确认的产品问题。不得因不满意业务结果重复采样、改变预期或换输入求通过。
- 可重试外部故障仅限已确认可恢复的测试启动/依赖中断或临时目录占用冲突，且此前没有已确认的业务失败；原故障原因须已消除、同一代码版本/输入/断言及实际入口保持不变、测试没有非幂等业务副作用，才允许**最多补试一次（总计两次）**。重新创建独立临时目录，复用仍有效的安装与配置；保留两次日志、失败原因及结果，不覆盖首轮。
- 外部故障仍未恢复或第二次仍不能观察到业务结果：停止该项并标记无法判断，不持续完整重试。若修改了测试断言、输入、产品提交或执行入口，应视为修订后针对受影响项的新测试，不得记作同条件重试。
- 发生范围外测试失败时保留事实和影响，不自动扩大 U1 必测清单。已有效通过且未受变化影响的 U1-D/E/F 不重跑。

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

## 8. t2 修订后的证明状态（2026-10-21）

- 本轮先只改正式测试计划，随后补齐 U1-A/B/C 三个既有测试方法的断言；没有修改产品实现、配置、环境或 §7 的历史执行记录，也未执行新测试。§7 所列六项通过、185 项复验、1036 项补充回归及首次临时目录冲突均保留原始事实。
- 修订前核实的 PR head 是 `087df10ea0853b58168076789c8180848d80f63b`；与 `3d6c2bc` 相比只有三份计划/审核文档改动，当前提交的持续集成 `39455636835` 五个作业均成功。文档修订提交本身不改变上述代码适用性。
- **待补结果**：U1-A、U1-B、U1-C 的测试断言已按 §3 补齐（2026-10-21），但补强后的三个方法尚未按 §6.2 执行，因此第三关的这三项目标暂不作完整通过结论。
- **可复用结果**：U1-D、U1-E、U1-F 的 2026-10-20 已有有效结果继续成立，除非后续提交直接影响其受测行为。
- 本版计划修订不自动批准第二关、第三关或合并；后续审核只核实本版改动及待补检查，不重开无关项目。
