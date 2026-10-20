# Stage 2 U1 测试计划：固定证据展示与真实阻挡归属

- Test plan revision：`stage2-u1-t1`，2026-10-20。
- 唯一正式路径：`plan/stage2-fixed-evidence/test-plan.md`；执行步骤补在本文件，不另建相互补充的测试手册。
- 范围依据：用户 2026-10-20 明确授权 U1/U5 计划及“测试计划也改”；U1 正式目标与保留行为见 [execution plan r3](https://github.com/ScholarWorkflow/professor-contact/blob/9874d8344d55d37b61d12acb0f356c3f4fae6d00/plan/stage2-fixed-evidence/implementation-plan.md) §§1、3。本文不继承 #92 的 t47、审核或测试通过状态。
- 静态核对基线：`ScholarWorkflow/professor-contact@879982abe1d7d811bd9d014c03dce4f5912cc64f`。这是现有模块/测试资产基线，不是已实现 U1 的产品版本。
- 规则：[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)（2026-10-09 20:37 UTC），[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)（2026-10-19 14:02 UTC）。2026-10-20 已重新读取。
- 当前交付（2026-10-20）：测试设计候选；本地执行工程师已在本文件 §6 接线可执行步骤并按 §7 执行六项，产品/测试实现提交 `2b813fc`。第一关、第二关和第三关的正式结论仍由对应负责人给出；作者不自授 APPROVED 或测试 PASS。

## 1. 范围与检查方式

以下六项是本轮必测范围上限，不是要求每项再做单元、集成、真实模型三套证明。优先在既有 Python unittest/合成 Stage 2 夹具中，从现有正式 runner 入口得到返回值、`套磁候选分析.md` 和 `套磁候选输入.json`，用现有断言判断；同一场景可同时满足多项。内部 owner map、完成标记、快照算法和 helper 名称不是额外的产品验收目标，不要求单独认证其内部格式。

真实模型、Zotero 服务、PDF 下载、Codex/OpenCode 运行、安装交付均不属于 U1 改动目标；不为本次引入完整业务 smoke、双 harness 重跑或新设施。SKILL 与两个 analyzer 的停止/修订说明仅静态核对与已确定行为一致，不转成委派身份或执行过程认证。

## 2. 必测清单

### U1-A：四个固定出口等价显示可信引用

- 业务目标：固定卡 `evidence/completed_part/remaining_gap` 和禁锚卡 `evidence` 显示可信题名与 Zotero 链接，不泄漏裸引用、不改证据含义或引用许可。
- 输入/场景：一个正常 Stage 2 合成输入覆盖四个目标字段，引用在结构化候选/完成论文或显式 Zotero 引用中声明；同一正文保留一处已正确链接、一处普通数字/日期/无引用依据的八位文字。新建包及 U1-E 的旧包复用路径共用这些输入，不为每种文字排列另造矩阵。
- 预期：四字段中的实际论文引用为当前可信题名和正确目标，前后证据文字保留，已有链接不嵌套且 URL 不被二次改写；普通文字不变。持久机器证据、作者引文/译文/出处、freshness 结论不因显示转换被改写；仅为展示补 canonical 元数据不扩大 `supporting_item_keys`、`relevant_keys` 或 P/L 使用许可。
- 检查方式：正常 finalize 之后直接比较四字段对应 Markdown 与输入语义，并检查包内相关原始字段和许可集合。纯包 narrative refine 在 U1-D 中复用同一显示检查，无需另跑真实模型。

### U1-B：实际引用缺可信元数据时交源，不编造或静默删文

- 业务目标：当前无效题名不能被旧标题掩盖，无法解析的实际引用在写入前失败，给出可处理的数据责任。
- 输入/场景：在 U1-A 的隔离输入上，分别使实际显示引用的当前题名明确为空/无效（旧包有旧题名），以及一个明确 Zotero 引用没有可信记录；不扩所有 key/标题格式组合。
- 预期：返回定位到 gap、字段和 key 的缺失信息，交数据准备 owner；旧正文/受管包不被接受为新成功，不造题名、不删证据、不沿用旧题名掩盖当前明确无效。当前来源未提供某记录但旧 canonical 仍有效，以及旧禁锚无完整候选列表但实际引用能解析的合法复用，按 U1-E 检查，不能一概阻断。
- 检查方式：正常 finalize 返回信息与原目标文件比较。失败输出只要求业务信息可理解，不新设固定错误码、采集器或来源证明。

### U1-C：合法报告按真实片段归属，保留已有定位/排除边界

- 业务目标：固定卡合法 blocking 可登记并给出 source/generator owner；实际 narrative 不因长得像模板而误归固定；原本排除区仍排除。
- 输入/场景：同一正常生成的报告包含可定位的固定源文字与模板文字，包含一个跨行源值的续行、一个模板和值同一行的命中及一个 summary 缺失后回退原句的命中；用短 location 加全文唯一 quote，另用实际物理行号区分重复 quote。保留一处带模板字样的真实 narrative 对照。只选这些直接决定归属的代表性片段，不穷举换行符、字段、方向和 quote 的笛卡尔积。
- 预期：源值/回退原句交 source，确定性模板交 generator，稳定方向/gap/字段正确；允许同句涉及多个固定 owner，不因无法选唯一 owner 拒绝真实失败；真实 narrative 仍沿原权限。短 location 不被强制换成数字。歧义 quote 仍拒绝，不猜位置；用户笔记等既有排除区不变为合法固定报告目标。原 issues/notes/verdict 与原报告文件保留。
- 检查方式：`stage2-record-validation` 返回和持久 validator；复用既有重复 quote/短 location、用户笔记场景中适用的检查，新增仅为固定片段/归属的差异。不通过反解析标题制作第二套 owner 判定器。

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

不要求新增通用 fixture、专用判定器、逐调用记录或来源认证。新 U1 断言和 fixture 的具体方法名/文件位置由本地测试工程师在实际实现后确定；本文不虚构未来命令，也不要求固定测试方法数量。

## 4. 执行 recipe 的交接边界（待接线，不是可执行通过记录）

1. 产品实现 owner 先交实际 U1 实现 revision 及与 r3 的差异；只因文档 SHA 或纯拆分变化，不重开无关目标。先落地另一计划时，记录共享接受的现有位置和适用结果，避免重复实现和重复验证。
2. 本地测试工程师在本文件补实际准备顺序、已有环境/安装复用来源、隔离可变目录、精确测试选择器/命令、所需参数和输出路径。优先现有 unittest 与 runner 合成输入，不增加模型、服务或安装前置。对上述六项目标指出对应已有或新增断言；已有方法仅部分覆盖时不能宣称覆盖完整。
3. 每项目标选择一个足够入口并复用同场景观察；如已有有效结果足以覆盖，引用真实版本/结果与适用原因，不为该计划另跑。没有材料只标待补，不把“现有测试存在”当 PASS。
4. 配置和临时产物在仓库外独立 `/tmp` 目录；正式可复用测试代码正常入库。配置/依赖预检只确认实际命令可运行和状态隔离，复用有效预检，不认证环境来源。
5. 第二关独立审核补齐后的 recipe 是否可执行且只覆盖上述清单，通过后才由获授权执行者执行。确定性的业务失败不重复采样；环境/工具中断先保留结果并停受影响项，恢复后是否重试及次数、清理方式须先写入 recipe。不得临场改输入/断言求通过。
6. 用标准测试报告或简短记录记实际产品/测试 revision、命令、逐项目标的通过/业务失败/无法判断/未执行、必要输出与复用来源。保留所有正式尝试；只复核改动影响目标，不借总数或全绿代替六项覆盖。G3 仅在实际有效结果齐全时给结论。

## 5. 当前状态与下一负责人

- 设计/第一关：完整候选；本文件不自授通过，正式结论仍待独立测试计划审核。
- 第二关：可执行 recipe 已由本地执行工程师补在 §6，正式“可执行且不超范围”的结论仍待独立审核。
- 第三关：六项已按 §6 执行并记录在 §7（产品/测试实现 `2b813fc`）；本记录不宣称正式测试关口通过。没有沿用 #92 或 Stage 2 机械拆分测试声称 U1 已修复。
- 下一步：独立测试计划 reviewer 检查清单、范围与 recipe；测试执行事实见 §7。合并审核按 `Merge Reviewer Rule.md` 单独进行；不自动创建新 PR，不扩大至 U5 业务或 Stage 3—5。

## 6. 执行步骤（2026-10-20 接线）

本节的接线与执行由本地执行工程师完成；正式结果只覆盖第 2 节六个必测项及其直接复用。工作树为 `/Users/rekidunois/code/skill-repos-dev/worktree/pr107-u1-local-execution-20261020`，临时输出统一放仓库外 `/tmp/u1-fixed-evidence`（本次实际使用 `/tmp/u1-full-suite*.log` 保存全量日志）。复用仓库现有 `unittest`、`test_contact_state.BaseEnv`、`stage2_upstream_fixture` 与正常 Stage-2 命令入口；不新增模型调用、Zotero/PDF 下载、安装步骤、双 harness 运行或专用判定器。

1. 静态编译五个 Stage-2 程序文件（不证明业务行为，仅排除语法/接线错误）：

```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktree/pr107-u1-local-execution-20261020
mkdir -p /tmp/u1-fixed-evidence
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage2_render.py \
  .apm/skills/professor-contact/scripts/_stage2_finalize.py \
  .apm/skills/professor-contact/scripts/_stage2_preflight.py \
  .apm/skills/professor-contact/scripts/_stage2_validation.py
```
预期：退出码 0，无输出。

2. U1-A 至 U1-F 六项必测（`test_stage2_fixed_evidence` 的六个方法分别对应 A–F，使用正常 `contact_state` 命令入口与合成夹具）：

```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktree/pr107-u1-local-execution-20261020/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest test_stage2_fixed_evidence -v 2>&1 | tee /tmp/u1-fixed-evidence/u1-af.log
```
预期：`Ran 6 tests`，六个方法 `ok`，无 `FAIL`/`ERROR`/`skipped`。对应关系：`test_u1_a_*`、`test_u1_b_*`、`test_u1_c_*`、`test_u1_d_*`、`test_u1_e_*`、`test_u1_f_*`。

3. 复用既有 Stage-2 检查，只覆盖受本次改动直接影响的目标（不整组照搬历史矩阵）：

```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktree/pr107-u1-local-execution-20261020/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage2_style_validation_handoff \
  test_stage2_preflight \
  test_stage2_narrative_example_contract \
  test_stage2_resolved_direction \
  test_stage2_resolved_direction_acceptance_boundary \
  test_stage2_resolved_direction_downstream_regressions \
  test_stage2_resolved_direction_regressions \
  test_stage2_resolved_direction_fresh_review_regressions \
  test_stage2_resolved_direction_merge_fulltext_regression \
  test_stage2_resolve_fingerprint_scope_regression \
  test_contact_state -v 2>&1 | tee /tmp/u1-fixed-evidence/u1-existing.log
```
预期：全部 `ok`，无 `FAIL`/`ERROR`；`test_stage2_style_validation_handoff` 的 T4/T5、`test_stage2_preflight` 的旧包/复用判定、`test_contact_state` 的 Stage-2 端到端与两轮修订必须通过。旧 T5 夹具中 `_t5_inject_legacy_member` 只增加与自身正文一致的 ownership map，仍保留“旧语义 pack 必须 process”的原场景；不改其断言。

4. 补充的全仓回归（不作为六个必测项的通过条件，只用于发现本次改动对既有命令的连带回归）：

```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktree/pr107-u1-local-execution-20261020/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest discover -s . -p 'test_*.py' > /tmp/u1-fixed-evidence/full-suite.log 2>&1
```
预期：`OK`（允许仓库原有的 `skipped`）；有失败时按第 5 步区分并只复跑受影响方法。

5. 失败处理：保留每次正式尝试的日志与退出码；确定性业务失败不重试，不修改预期、输入或方法求通过；依赖缺失、测试启动失败或环境中断记为无法判断并停止受影响项；产品缺陷按计划修复后只复验受影响目标。`SKILL.md` 与两个 analyzer 的说明只做静态核对，不转成运行时或委派认证。

## 7. 执行结果（2026-10-20）

- 产品与测试版本：`2b813fc`（`feat: render trusted fixed evidence and record real blocker owners`；测试代码与该候选同提交）。本文档结果记录提交只改本文件。
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
- 记录后追加：U1-F 增加一条来源行逐字比较断言（确认只有顶部生成时间可忽略），同方法随六项重跑 `Ran 6 tests in 11.915s`、`OK`（日志 `/tmp/u1-fixed-evidence/u1-af-rerun.log`）；产品实现提交 `2b813fc` 未变。
- CI 合同：新测试模块 `test_stage2_fixed_evidence` 已登记到 `plan/test-grouping/shards.json` 的 shard4（stage2）；`uv run --no-project python scripts/check_test_shards.py` 输出 `OK: 79 test modules across 4 shards`。
- 复用说明：本次没有可沿用的 U1 产品结果；既有 T4/T5、preflight、resolved-direction 结果只按本候选直接相关的测试方法重跑，不把历史结果外推到新实现。
- 范围说明：本记录只报告测试执行事实，不批准计划或测试关口；计划审核、测试计划审核与合并审核仍由各自负责人给结论。本地执行工程师已同步 `SKILL.md` 与两个 analyzer 的“登记→交 owner→停止/修订”说明，未改委派结构或 style-validator 格式。
