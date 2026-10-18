# Stage 2 固定证据与分析级别测试计划

- 测试计划版本：`contact-evidence-level-t37`（T1—T4 的必测清单与 17 个执行选择器未变；t37 只修订 T4 展示刷新用例中与计划冲突的一条断言及其描述）；对应[执行计划第 5 版](implementation-plan.md)。
- 需求版本：2026-10-17 确认的 U1/U5；测试准备时的产品基线为 `305bc08f8b186672108cffbba0293d249bc8b4b2`。
- 当前状态：第一关通过、第二关通过；第三关在合并复审修正后的版本上重新取得 17/17 有效记录（`/tmp/contact-evidence-level.xa9UbsfO/recipe.txt`，全仓 `Ran 1035 tests`、`OK (skipped=1)`）。旧版合并审核（受审 `ac301e1`）的 5 项实现缺陷修复与复验见 §9；执行计划第 5 版的入口对齐见 §10；合并复审（受审 `8fd761a`）的 2 项缺陷与配套 t37 测试步骤修订见 §11 与 t37 记录。修正后的提交尚未取得新的复审结论，拉取请求仍为草稿；本记录不构成合并批准。
- 历史修订记录：t32 按用户授权删除错误提示字符串限制和重复的禁止区域用例（当前 13 个新增用例、17 个执行选择器；此前运行结果只对应旧版本）；t26 定向修正 T2 的修复后重新校验，以及 T4 写前来源变动与人工改动互相干扰的问题；t27 按第二关复核（对照 `0d5606b`）修正 t26 引入的 T4 展示刷新计数断言与 T1 候选引用断言；t28 按其后定向复核（IR-32—IR-34）把前置候选证明绑定到被测缺口、去掉被蕴含的重复断言、并把运行记录改为只声明实际执行到的范围；t29 修正 t28 引入的 `gap_id` 未绑定读取与两处记录指向；t30 按其后定向复核（IR-37—IR-39）改准运行记录的版本指向、删掉被守卫蕴含的重复断言；t31 按第八、九轮复核（IR-37 残留、IR-38 残留、IR-40(a)(b)、IR-41）再改准运行的版本指向，把固定卡比较改为「夹具守卫 + 与渲染前快照比较」、恢复 refine-finalize 的 pack 字节守卫，并删除与辅助函数重复的断言；t33 按第二关意见把「旧包缺可比较基线」用例改为断言顶层 `legacy_pack_no_preflight` 与方向级无 `validator_not_accepted`；t34 把状态行与 §5 的「最新记录」绑定到测试提交 `0fe84ab` 并在该提交上重跑同一组 17 个选择器；t35 在第三关正式执行中修订 T1 译文断言、T1 `gap_notes` 比较形状与 T2 freshness 夹具（见修订记录）。t35 第三关已于产品与测试版本 `8f31296` 正式执行：§3 的 17 个选择器全部通过（`Ran 17 tests`、`OK`，结果目录 `/tmp/contact-evidence-level.OnXaAyhx/recipe.txt`，逐项结论见 §5）；执行中 T1、T2 曾因测试步骤本身不成立被本地执行工程师按 Test Engineer Rule §5 停止并交接，t35 修订后完整复跑通过。§5 的 6 通过 / 11 业务失败只对应测试提交 `0fe84ab`（实现前），不代表当前版本；审核处置仅适用于各自记录版本（§6、§7）。t36 只补充 T1 禁锚区完成论文引用缺可信题名的独立夹具，不新增选择器；该新分支已由本地执行工程师按第 36 版定向审核指定的最小范围执行并通过（`Ran 1 test`、`OK`，退出码 0，日志 `/tmp/contact-evidence-level.Gic8ynUG/recipe-t36.txt`，见 §5），其余 16 个未受影响选择器直接复用 t35 的通过结果。；t37 按合并复审阻断项 1 与执行计划 r5 §3.2／§3.3.5 修订 T4 展示刷新用例的旧认证断言（改为断言旧认证正式失效、新正文可重新登记第一轮），范围与选择器数量不变。
- [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 决定范围；附录/步骤不追加清单外检查。

## 当前测试审核与执行状态（2026-10-18，受审 `6d8f80a`）

- **对象**：第 92 号拉取请求，唯一测试计划 `contact-evidence-level-t36`，已批准的执行计划 `contact-evidence-level-r5`。本次仅同步状态与历史版本指向，不修改业务目标、测试代码或执行步骤。
- **第一关：通过**。沿用已批准的 T1—T4 必测清单，不增加测试义务。
- **第二关：通过**。13 个新增用例与 4 个既有用例共 17 个选择器；第 36 版的 T1 定向审核已通过，最新整合与入口对齐没有修改选择器、断言和预期结果。
- **第三关：通过（采用已有执行记录）**。上游合并与第 5 版入口对齐后的 §3 全部 17 个选择器已在集成版本执行，记录为 `Ran 17 tests`、`OK`、退出码 0，日志 `/tmp/contact-evidence-level.sn3UGj6n/recipe.txt`，详见 §10。旧版第 35/36 版的 17/17 与 1/1 记录保留在 §5，仅作为对应版本的历史依据。
- **补充执行记录**：§10 另记全仓 `Ran 1035 tests`、`OK (skipped=1)`、退出码 0，日志 `/tmp/contact-evidence-level.UiagMtvI/full-suite-merged.txt`。该全仓执行不属于新增必测要求。
- **审核方式**：只读核对正式测试计划、测试代码、相关调用入口及仓库内执行记录；本次未运行测试，未直接取得仓库外 `/tmp` 原始日志，未做独立子代理复核。因本次只改文档，无需重测。
- **合并状态与交接**：此前正式合并审核针对 `ac301e1` 的结论为未就绪；5 项修复记录见 §9，第 5 版入口修订及集成后的执行记录见 §10。受审集成提交 `6d8f80a` 尚待合并复审；下一负责人为合并审核负责人。拉取请求保持草稿，不能以测试通过代替合并审核。

## 历史测试计划审核记录（2026-10-18，受审 `81764b7`）

- **审核对象**：PR #92 的 `81764b7`；唯一测试计划 `contact-evidence-level-t36`；执行计划 `contact-evidence-level-r4`。本次只读核对测试设计、选择器、受影响测试代码和已有执行记录，未运行正式测试，未进行独立子代理复核。
- **第一关：PASS**。T1—T4 继续沿用 t6 已确认的必测清单；无新增测试义务。
- **第二关：PASS**。原 17 个选择器与 §2/§3 对应；t36 新增的禁锚区完成论文缺题名检查复用 T1 既有选择器，输入互相隔离，按原 `stage2-plan`／`stage2-finalize` 检查失败原因和无写入；此前 [t36 定向复核](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6247551078) 已通过，之后只有执行记录的文档变化。未发现需要修订的测试步骤或超范围要求。
- **第三关：PASS（复用既有执行结果）**。产品修订后 t35 的 17/17 通过记录：`/tmp/contact-evidence-level.kB35xlUV/recipe.txt`；t36 变更的 T1 选择器另取得 1/1 通过记录：`/tmp/contact-evidence-level.Gic8ynUG/recipe-t36.txt`；其余 16 项有效结果直接复用。上述版本和命令详见 §5；本次未重跑、未自行核验私有 `/tmp` 原始日志。
- **未完成事项**：测试计划无阻断项；PR 合并审核未进行，仍为草稿。下一负责人为合并审核负责人。本记录不构成合并批准。



## 1. 唯一必测清单

| 项 | 目标与输入 | 预期结果 | 足够的检查入口 |
|---|---|---|---|
| T1 | 同一既有夹具覆盖固定卡 evidence/completed_part/remaining_gap 及禁锚区 evidence 中已知编号，其中待查证缺口带非空 `candidate_paper_ids`，可信标题/链接已在当前材料；在固定卡引用和禁锚区完成论文引用中分别构造缺可信题名的独立场景 | 正式 finalize 输出题名/链接，上述机器字段/候选编号与事实不变，其他说明原意、作者 quote/translation、用户笔记不变；缺题名明确失败且不生成伪引用 | 既有 runner CLI 测试夹具，检查 Markdown 与 pack 必要字段 |
| T2 | 当前受管正文上的固定区 blocking 与混合固定/叙事 blocking 原始报告；复用现有用户笔记/论文一览禁止区域报告 | 合法固定区第一轮失败确实登记；禁止区域报告继续拒绝且无 correction jobs；原始报告不改、非通过；refine-plan 无 jobs、明确交源/生成器处理，refine-finalize 不写；同内容重试不能清轮数。源/生成器修正后普通 finalize 产生新正文，旧失败不可直接放行；新正文重新提交校验且记录 PASS 后才能获得新的通过状态，旧原始报告不变 | 既有 Stage2ValidationHandoffTests 的报告/正文夹具和 record/refine/finalize CLI |
| T3 | 纯 narrative 第一次失败→现有合法修订→第二次仍失败（可用第二轮新固定卡阻挡覆盖其归属）；及已绑定报告对应的正文/pack被改 | 纯文字修订仍可完成且第二次终态不继续第三轮；不允许用过期报告改事实或覆盖手改文件 | 复用该模块已有 second_blocking_round_is_terminal、stale_render、changed_input_pack 对应测试；只调整受新登记分类影响的断言 |
| T4 | 复用同一方向的 fulltext、abstract（有分析文件）、未确认（存在旧分析文件，但没有成功分析索引记录，也没有有效级别）及 OCR-only fulltext/facts unavailable 夹具，并将 §2 已有缺 analysis_level 兼容样例归入本项（有分析文件/PDF 仍为未确认，不复制样例）；有完整接受基线且 /tmp facts 已不存在，原正文已有有效绑定 validator PASS，仅 level/render 变更由正式 preflight→展示刷新，同一场景复用 T1 已知引用及正式 pack 中可信题名/链接；复用现有隔离夹具分别检查分析来源新增、删除、换址（含原缺分析路径出现、facts sidecar 保持缺失）及人工修改正文；来源新增只修改新论文的记录/文件，已有论文的分析级别与来源保持预检时状态；删除与人工修改使用互不影响的独立临时目录，并保留旧缺基线情形 | 三类计数/规范包一致，无成功分析索引记录即使残留分析文件、旧记录缺 analysis_level 即使有分析文件/PDF，均归未确认；同一 pack-only 刷新输出的固定卡 evidence/completed_part/remaining_gap 与禁锚区 evidence 均显示可信题名/链接，原始机器字段及候选编号不变；纯展示刷新使正文实质变化后，旧 validator PASS 不再被接受，不运行模型校验；等价重写仍不清轮数。预检后来源变动或受管正文被人工修改时，展示刷新必须分别拒绝写入、保持输入包和正文原样；纯展示后再预检不因过期包完整性摘要误 process，保留 assignment/模型指纹、不重签 proof、不额外生成分析/归属/时效任务；新增/删除/替换、无法比较的旧基线走原 process，不能误当 display-only；复用已有写前漂移/手改保护检查，不写不确定结果 | 既有 BaseEnv/preflight/pack-only 渲染及 guard 夹具，检查分流原因、pack/Markdown及任务记录；只覆盖这些直接反例，不交叉穷举，不跑真实模型 |

T1—T4 是上限。无需真实 Zotero、下载/PDF分析重跑、Nix/APM重装、全教授流程或完整测试模块回归；本次未改安装和模型业务。报告中“四位教授”与“10+1”是缺陷背景，不能强制采集私人材料或追加四次模型验收。

## 2. 测试资产与选择器对照

测试代码全部放在 `.apm/skills/professor-contact/tests/test_stage2_evidence_level.py`，只复用 `test_contact_state.py` 的 `BaseEnv`、`run_cli`、`run_bound_stage2_plan`、`run_bound_stage2_finalize`、`stage2_style_validation_report` 和既有合成夹具，不新建判定框架、不改产品代码、不改写既有用例。

| 项 | 选择器 | 该用例断言的计划行为 |
|---|---|---|
| T1 | `test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_renders_trusted_references_without_touching_machine_fields` | 固定卡 evidence/completed_part/remaining_gap 与禁锚区 evidence 显示可信题名/链接，可见文本不再出现原始编号（由既有的逐槽位 `assertNotIn` 保证）；非空 `candidate_paper_ids`、原始 `evidence`、`gap_id`、quote、翻译、用户笔记逐字不变 |
| T1 | `test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_without_trusted_title_fails_instead_of_inventing_one` | 固定卡引用与禁锚区完成论文引用分别缺可信题名时，生成明确失败且不写受管分析文档；复用现有选择器和独立临时教授夹具 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job` | 固定区 blocking 第一轮登记为 needs_correction，refine-plan 零 jobs 并交源/生成器，refine-finalize 不写；原始报告字节不变；随后模拟修正题名与来源证据，经普通 stage2-plan/finalize 生成新正文；新报告登记前旧失败不被接受，新报告确认为 PASS 后才接受新正文，轮次按新业务版本重新从第一轮计，原失败报告保持原字节 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_mixed_fixed_and_narrative_blocking_creates_no_rewrite_job` | 混合固定/叙事 blocking 同样零 rewrite jobs，不把固定区交给模型 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_repeating_the_same_fixed_card_report_does_not_clear_the_round` | 同内容重试不能清轮数，也不写入通过结果 |
| T2/T3 引文约定 | T2/T3 的 blocking 引文取展示替换后仍存在的片段（`无更晚论文实现该点`、`只做了第一组`），不含 item key，否则 T1 落地后 `find_line` 会找不到行 | 测试文件常量 `FIXED_EVIDENCE_QUOTE`、`COMPLETED_PART_QUOTE` |
| T3 | `test_stage2_evidence_level.NarrativeRoundBoundTests.test_narrative_correction_rounds_stay_bound_and_terminal_state_is_recorded_once` | 纯叙事第一轮→合法修订→第二轮固定卡阻挡登记为 fail_after_2_rounds，不继续第三轮、不再发修订 |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_second_blocking_round_is_terminal` | 既有轮次终止结论继续成立（第二轮终态、第三次 plan 零 jobs） |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_report_for_stale_render_is_rejected_without_pack_write` | 正文被改后旧报告被拒绝且零写入 |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_refinement_rejects_changed_input_pack` | 输入包变化后旧报告被拒绝、无修订任务 |
| T2 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job` | 既有禁止区域报告拒绝与零修订任务断言继续成立 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_counts_follow_the_recorded_analysis_level` | 同一方向集合内三类计数与规范包级别一致；没有成功分析索引记录（即使残留分析文件）计未确认，OCR-only 全文（有分析/OCR 文件、无 facts）仍计全文 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_legacy_records_without_level_count_as_unconfirmed` | 缺 analysis_level 的旧记录即使有分析文件也计未确认 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_display_only_level_change_refreshes_without_model_work` | 完整接受基线下（被统计方向集合已含 OCR-only 论文，刷新后计全文 1、摘要 2）仅 level 变化判为展示刷新；刷新后统计与规范包级别更新、旧 PASS 不再被接受、assignment/叙事/模型指纹保留、旧认证在正文实质变化时正式失效（刷新后不再携带绑定旧正文的认证，新正文可重新登记第一轮 PASS）、freshness 缓存字节不变、下次预检不误报包完整性 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_source_change_routes_back_to_the_process_path` | 在仅既有论文 AAAA1111 的级别变化使预检允许刷新后，只新增 CCCC3333 的索引/分析文件/关联输入（facts sidecar 仍缺失），AAAA1111、BBBB2222 的级别和来源保持不变；旧预检执行刷新必须拒绝写入，输入包与正文原字节不变；重新预检走原 process |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_deleted_analysis_source_also_routes_back_to_process` | 独立接受基线只删除 CCCC3333 的分析文件与索引记录，不删论文事实目录项，不改其他论文级别，预检应走 process；另用独立临时教授目录在仅 level 变化预检通过后人工修改受管正文，旧预检刷新须拒绝写入，输入包与人工正文原字节不变 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_replaced_analysis_source_routes_back_to_process` | 分析文件换址（索引路径与旧文件同时变化）时走原 process |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only` | 旧包缺可比较业务基线走原 process：顶层 `action=process` 且 `reason_codes` 含 `legacy_pack_no_preflight`，各方向 `reason_codes` 不含 `validator_not_accepted`（夹具只用 `stage2_pack_content_fingerprint` 消除删字段造成的摘要失配，不改产品逻辑与其他通过记录） |

### §1 预期与选择的覆盖关系

| §1 预期 | 覆盖方式 |
|---|---|
| T2 原始报告不改 | `assert_source_owner_handoff` 比较报告字节；`test_repeating_...` 断言重复登记不写通过结果 |
| T2 修复生成内容后普通 finalize 产生新正文、旧 PASS/失败不冒充 | T2 `test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job`：保留首份失败报告字节 → 修正题名和固定证据 → 正常 stage2-plan/finalize 生成不同正文 → 新校验登记之前旧失败不能放行 → 为新正文创建新的 PASS 报告并调用 stage2-record-validation → 确认第一轮 PASS、旧报告仍不变，预检不再提示 validator_not_accepted。仅验证本轮业务修复的恢复路径，不运行真实模型 |
| T4 等价重写仍不清轮数 | T3 用例断言 `round_retained`、`round == 1`、`phase == awaiting_second_validation` |
| T4 不重签旧 resolved proof | 本夹具无 resolved 方向、无 resolved proof，该项不适用于 T4 场景，按依据不设断言；展示刷新用例改为断言 freshness 缓存不被重写，并按 §3.3.5 断言旧认证随正文实质变化正式失效、新正文从第一轮重新登记 |
| T4 复用写前漂移/手改保护 | 来源新增用例：保存仅 level 变化预检 → 只让原本缺失的 CCCC3333 来源出现，保持已有论文级别和来源不变 → 用旧预检刷新，确认拒绝且 pack/正文原字节不变 → 新预检 process。来源删除用例：用独立基线只删除 CCCC3333 的分析文件及索引记录，其他输入不变，确认 process；同一个测试方法再创建全新独立临时教授目录，仅人工修改受管正文，确认旧预检刷新拒绝覆盖。既有 stale_render/changed_input_pack 选择器继续检查原登记与文字修订保护 |
| T4 不额外生成分析/归属/时效任务 | 展示刷新用例断言 freshness 缓存字节不变且刷新步骤不产生模型任务；无新任务记录即无新任务。刷新后新正文重新登记第一轮 PASS 只是校验记录，不是新的分析/归属/时效任务 |

## 3. 可执行 recipe

- 执行目录：`<producer checkout>/.apm/skills/professor-contact/tests`（选择器按模块名解析，必须在 tests 目录内运行）。
- Python：仓库现有 `python3`；本次准备基线 Python 3.14.7。
- 输出目录：新建 `/tmp/contact-evidence-level.XXXXXXXX`；日志、退出码和临时数据只放该目录，不入库、不推送。
- 命令（一次运行覆盖 T1—T4 与 T2/T3 既有选择器）：

```bash
# CHECKOUT 与 RUN_ROOT 是本命令仅有的两个变量，执行者按当前环境赋值。
# CHECKOUT：本次受测的 producer checkout 根目录（其下有 .apm/skills/professor-contact/tests）。
# RUN_ROOT：本次运行独占的仓库外目录，不存在时由下面第一行创建。
CHECKOUT=/path/to/producer-checkout
RUN_ROOT=$(mktemp -d /tmp/contact-evidence-level.XXXXXXXX)
mkdir -p "$RUN_ROOT"
cd "$CHECKOUT/.apm/skills/professor-contact/tests" || exit 2
python3 -m unittest -v \
  test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_renders_trusted_references_without_touching_machine_fields \
  test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_without_trusted_title_fails_instead_of_inventing_one \
  test_stage2_evidence_level.FixedEvidenceFailureTests.test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job \
  test_stage2_evidence_level.FixedEvidenceFailureTests.test_mixed_fixed_and_narrative_blocking_creates_no_rewrite_job \
  test_stage2_evidence_level.FixedEvidenceFailureTests.test_repeating_the_same_fixed_card_report_does_not_clear_the_round \
  test_stage2_evidence_level.NarrativeRoundBoundTests.test_narrative_correction_rounds_stay_bound_and_terminal_state_is_recorded_once \
  test_stage2_evidence_level.AnalysisLevelTests.test_counts_follow_the_recorded_analysis_level \
  test_stage2_evidence_level.AnalysisLevelTests.test_legacy_records_without_level_count_as_unconfirmed \
  test_stage2_evidence_level.AnalysisLevelTests.test_display_only_level_change_refreshes_without_model_work \
  test_stage2_evidence_level.AnalysisLevelTests.test_source_change_routes_back_to_the_process_path \
  test_stage2_evidence_level.AnalysisLevelTests.test_deleted_analysis_source_also_routes_back_to_process \
  test_stage2_evidence_level.AnalysisLevelTests.test_replaced_analysis_source_routes_back_to_process \
  test_stage2_evidence_level.AnalysisLevelTests.test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_second_blocking_round_is_terminal \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_report_for_stale_render_is_rejected_without_pack_write \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_refinement_rejects_changed_input_pack \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job \
  > "$RUN_ROOT/recipe.txt" 2>&1
status=$?
echo "exit=$status run_root=$RUN_ROOT"
exit "$status"
```

- 上面 17 个选择器与 §2 的选择器表一一对应（T1 两项、T2 三项、T3 一项、T4 七项、既有 T2 一项、既有 T3 三项）；`Ran 17 tests` 是本 recipe 的预期项数。t36 的新输入在 T1 原缺题名选择器内串行执行，不增加选择器、外部服务或测试命令。
- 也可按项复跑：把某一行单独取出执行；`-v` 输出逐用例结果。分项结果由这些断言判定，没有额外 JSON oracle。
- 准备顺序：`git status` 确认 checkout 干净 → 进入 tests 目录 → 建 run 目录 → 运行上面命令。没有安装、外部服务、模型或 Zotero 需求；`BaseEnv` 的临时目录已提供隔离。
- 失败处理：产品断言失败原样保留；命令或环境错误记无法判断并只重试受影响命令；未执行不得填 PASS；已确认失败不得被后续清理覆盖。

## 4. 准备记录与接口交接

- 已准备：`test_stage2_evidence_level.py`（T1—T4 当前共 13 个新增用例）与 T2/T3 既有选择器组成上述 recipe；未改动产品、既有测试和共享夹具，未操作用户教授目录。仓库外材料：`/tmp/contact-evidence-level.pc92prep/` 含 `recipe.txt`（准备期输出）、`reviewer-handoff.md`、`reviewer-verdict.md`、`reviewer-run.log` 和三个只读探针脚本 `probe_current.py`、`probe_round2.py`、`probe_packkeys.py`。
- 接口假设（实现方需对齐，不一致时由测试计划工程师按执行计划调整，不改名迁就；这些假设是执行计划 r4 §3.2、§3.3 的实现接口，不是新增验收要求）：
  1. 仅展示刷新入口取 `stage2-refresh-display --professor-dir <dir> --preflight-file <file>`，成功时 `status=ok` 且 `display_refreshed=true`。
  2. preflight 顶层 `action` 对仅 level 变化返回 `refresh_display`，对来源出现、删除、替换或基线不可比较返回 `process` 并给出具体 `reason_codes`；方向级返回形状不作断言。
  3. 固定区阻挡的责任交接结果中，合并阅读 `reason_code`、`message`、`detail` 应能确认责任方（源／生成器／生成方／数据准备）及应做的动作（修复／修正／重新生成／处理／补齐等）；允许分在不同字段，不强制具体字段布局。结果不得误报 `no_failed_directions`、`awaiting_second_validation`。
  4. 展示刷新后重绘的正文与旧 validator 的 `render_sha256` 绑定不同，旧 PASS 在验证入口被拒绝（预检给出 `validator_not_accepted`）；包内不得出现 `pack_integrity_mismatch`，方向级 `action` 与 validator 的存储形式不作断言。t37 按 §3.3.5 只增加行为检查：刷新后 pack 不再携带绑定旧正文的认证，新正文可重新登记第一轮；具体存储形式仍不作断言。
  5. 接受基线按来源 key 与类型记录路径、存在状态和成功/可用状态，使新增、删除、换址在预检可见；缺可信题名走明确失败结果（`status != ok` 且有 `reason_code`/`message`）。
  6. 固定区阻挡的 `stage2-refine-plan` 要返回明确的可处理交接结果：`jobs == []`、不要求写入（`write_needed` 不为 true），责任及动作可分列于返回字段，`status` 的具体字符串不作额外限制；`stage2-refine-finalize` 返回零 `rewritten` 且不改动 pack 与正文。
- 未改动范围：U2/U3/U4、Stage 3—5、安装与 Nix/APM、真实模型或教授流程均未纳入，也未借此要求全仓回归。

## 5. 复核与结果

本次确定性测试无自动重试。产品断言失败原样保留；先修产品再复验受影响项。命令/环境错误记无法判断，修正错误后只重试受影响命令，保留此前记录。未执行不得填 PASS；后续清理错误不得覆盖已确认失败。

记录格式保持简单：实际提交、T1—T4逐项通过/业务失败/无法判断/未执行、实际命令与输出位置、复用结果来源、剩余问题及负责人。原始日志和临时数据在仓库外，公开提交仅必要脱敏摘要。

t35 第三关正式执行记录（2026-10-18，本地执行工程师）：产品与测试版本 `8f31296`（分支 `pr92-local-execution-20261018`；本提交含 `contact_state.py`、`SKILL.md`、两个 analyzer 投影、t35 修订后的测试模块与本节）；命令为 §3 的 17 个选择器原样执行；结果目录 `/tmp/contact-evidence-level.OnXaAyhx/recipe.txt`，退出码 0，`Ran 17 tests`、`OK`。

- 逐项结论：T1 两项通过；T2 四项通过（固定区登记与交源、混合阻挡零修订任务、同报告不清轮数、既有禁止区域保护）；T3 四项通过（两轮终止一项 + 三个既有保护选择器）；T4 七项通过（三类计数、旧记录兼容、仅展示刷新、来源新增/删除/替换分流、旧包缺基线走 process）。17 项全部是当前产品版本的通过结果，没有业务失败、无法判断或未执行项。
- 执行中出现的问题与处置：正式执行时 T1 的两条断言与 T2 的一处夹具被判定为**测试步骤本身不成立**（译文切片末尾空格与侧车 `.strip()` 冲突、`gap_notes` 快照 list 与规范 dict 形状不符、freshness 缓存命中使修正后的来源证据不被消费），按 Test Engineer Rule §5 停止受影响项并交本地测试工程师修订（t35）；修订后按同一 §3 命令完整复跑，17 项通过。原始失败日志保留在 `/tmp/contact-evidence-level.UiagMtvI/`（`recipe-baseline.txt`、`step1.txt`、`step3.txt`、`recipe-wip1.txt`），t35 的中间失败记录在 `/tmp/contact-evidence-level.UyFv3Iyi/recipe-t35.txt`。
- 范围外回归（执行工程师自选的完整性检查，不是必测项）：在产品实现完成、t35 测试修订之前的版本上运行 `python3 -m unittest discover -p "test_*.py"`，`Ran 1028 tests`、`FAILED (failures=2)`，两项正是上面 T1/T2 的测试步骤缺陷，没有其他产品回归；t35 只改测试模块与本节，未再全量复跑。
- 复用来源：无，本轮是对当前产品版本首次执行必测项。
- 实现符合性审核处置后的复验：`implementation_reviewer` 首次审核（受审版本 `165906a`）结论为**完整**，其中 IR-02 按 §3.1 收紧禁锚区完成论文引用（产品改动提交 `cd39c70`；两次复验都在该提交的同一工作树内容上执行，其后 `git status` 无产品差异）后，按同一 §3 命令再跑一次 17 个选择器，结果目录 `/tmp/contact-evidence-level.kB35xlUV/recipe.txt`，`Ran 17 tests`、`OK`；同时运行 `python3 -m unittest discover -p "test_*.py"`，`Ran 1028 tests`、`OK`。上面第一次记录（`OnXaAyhx`）仍是同一必测清单的有效结果，两次结果一致。处置明细见 §8。
- 合并审核处置后的复验（2026-10-18）：5 项实现缺陷修正后，按 §3 的 17 个选择器完整复跑 `/tmp/contact-evidence-level.ojprDR8c/recipe.txt`（`Ran 17 tests`、`OK`）；变基到当前远端 tip（`fc23d6a`）后的提交 `c9c311c` 上再跑一次同一组选择器，`/tmp/contact-evidence-level.Q3dhhdqi/recipe.txt`（`Ran 17 tests`、`OK`），并运行 `python3 -m unittest discover -p "test_*.py"`（`Ran 1028 tests`、`OK`，`/tmp/contact-evidence-level.UiagMtvI/full-suite-mergefix.txt`）；处置明细见 §9。
- t35 未完成项：无。这是 t35 第三关结果，不代表 t36 新场景已经通过或可合并；合并审核按 `Merge Reviewer Rule.md` 由下一负责人执行。

- **t36 变更及第三关执行结果（2026-10-18，本地执行工程师）**：仅原 T1 选择器 `test_fixed_evidence_without_trusted_title_fails_instead_of_inventing_one` 新增独立临时教授输入——固定证据卡所用题名全部保留，只删除禁锚区 `completed_by_item_key` 所指论文的可信题名，正文中的固定证据与禁锚区 evidence 本身均不包含该缺题名编号；检查生成因该完成论文引用缺题名而明确失败、不写受管分析文档。按第 36 版定向审核指定的最小范围只执行该选择器：
  `cd .apm/skills/professor-contact/tests && python3 -m unittest -v test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_without_trusted_title_fails_instead_of_inventing_one`
  产品与测试版本 `bfc9756de85947e8e6c46a85e1d35036f7ad959f`（产品代码与复验版本 `cd39c70` 相同，t36 提交只改测试模块与本节）；退出码 0，`Ran 1 test`、`OK`，仓库外日志 `/tmp/contact-evidence-level.Gic8ynUG/recipe-t36.txt`。其余 16 个未受影响选择器直接复用 t35 记录（`/tmp/contact-evidence-level.OnXaAyhx/recipe.txt`，以及 IR-02 处置后的 `/tmp/contact-evidence-level.kB35xlUV/recipe.txt`，两次均 17/17），未重跑整组配方或全仓测试。至此 t36 的 T1 新分支已取得当前版本的通过结果；没有新增必测编号、专用测试设施或业务验收条件。

准备期复核（非第三关正式执行）：产品提交 `305bc08f8b186672108cffbba0293d249bc8b4b2`（未实现状态），测试提交 `0fe84ab`，命令为 §3 的 17 个选择器，结果目录 `/tmp/contact-evidence-level.p49ZBXq2`（`recipe.txt`），退出码 1，`Ran 17 tests`、`FAILED (failures=11)`。

- 通过 6 项：`NarrativeRoundBoundTests` 一项、三个既有保护选择器、既有禁止区域选择器、以及 `test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only`（该用例在本轮改为断言顶层 `legacy_pack_no_preflight` 与方向级无 `validator_not_accepted` 后，在未实现的产品上即已成立）。
- 业务失败 11 项：T1 两项、T2 三项、T4 六项，原因与下一段的历史分组相同。
- 历史记录（18 个选择器版本，只按其版本引用）：测试提交 `36c630a`（`0d5606b` 加 t27 两处修正），结果目录 `/tmp/contact-evidence-level.kj3p7J2l`（`recipe.txt`），`Ran 18 tests`、`FAILED (failures=11)`、7 通过 / 11 失败。

- 历史分组（18 项版本）：通过 7 项为 T3 四项（`NarrativeRoundBoundTests` 一项与三个既有保护选择器）、T2 两项、T4 一项。
- 业务失败 11 项，按实际失败原因分组：
  - T1 两项：展示用例首个断言失败在固定卡「后续论文依据」行仍含 `AAAA1111`（未做题名/链接替换），禁锚区与候选引用断言在该次运行中未执行，不据此判断；缺可信题名用例仍返回 `status=ok` 并生成分析文件（未拒绝）。
  - T2 三项：三项 `record` 均返回 `status=error`（产品尚未允许登记），其中 `test_repeating_...` 的日志给出 `reason_code=validation_issue_not_repairable`；因此 refine 分流与修复后重新校验无法进行。
  - T4 六项：`test_counts_...` 为 `全文级 3 篇`（按文件存在统计，未按记录级别）；`test_legacy_...` 为 `全文级 2 篇`（同上）；`test_display_only_...` 与三个来源变化用例为 `reuse_all`（未实现展示刷新与来源变化识别）。
- 该记录只用于确认选择器可执行、判定 T3 已成立和暴露产品缺口；本轮两处修改过的断言（T1 候选引用保留、T4 展示刷新计数）在本次运行中未被执行，待产品实现后由第三关首次真正运行。本记录不替代第三关正式执行，也不作为任何通过结论。
- 历史记录（旧测试代码，只按其版本引用）：`/tmp/contact-evidence-level.XcpOlvbX`（提交 `70e8eef`，18 项、7 通过 / 11 失败）、`/tmp/contact-evidence-level.oWwoE7gZ`（提交 `70e8eef`，同类）、`/tmp/contact-evidence-level.VgZ9JU6w`（提交 `dca3160`，同类）、`/tmp/contact-evidence-level.h3SBpUMF` 与 `/tmp/contact-evidence-level.M5wh17Uv`（提交 `3595a2c`，同类）。其中 `oa4NuJoS` 与 `h3SBpUMF` 的来源变化项曾因夹具未真正改变预检输入而作废，原日志保留。

修订边界：t19 按 DSH 子代理的实现符合性审核（IR-10—IR-18）改用展示后仍存在的固定区引文、让计数与展示刷新夹具自洽、保留机器字段与来源元数据，并补齐 §1 覆盖关系与接口假设；t20 按第二轮 DSH 复核（IR-19—IR-21）把 §3 命令改为逐条 18 个选择器、补齐 §2 与 §1 的描述并整理审核记录；t21 按第三轮 DSH 复核（IR-22—IR-26）同步文档标签、删除过期复跑说明并限定 §5 的归因范围；t24 按第六轮 DSH 复核的两项可选观察清理措辞（指明实际失败的断言、§7 第四轮小结指向 §5 说明）并同步 DSH 摘要指针；t22 按第四轮 DSH 复核（IR-27、IR-28）修正状态行编号范围与夹具改动范围的记载，另外采纳三条说明性观察（§5 的 T2 归因限定、补记 `oWwoE7gZ` 运行、DSH 结论摘要落盘并在 §6/§7 指向），并整理 §3 列表排版。四次修订都不改变 t6 已批准的 T1—T4 范围与预期结果与测试代码语义。执行计划 r4 已获[正式批准](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6228535516)，本次不重开其未受影响关口。

交接：T1/T2/T4 的 11 项业务失败交产品实现负责人；t26/t27 修改过的用例已在本轮按 §3 复跑（见上），结果仍为业务失败，未见夹具问题。第二关复核材料由本地测试工程师按本轮记录准备；确认后由本地执行工程师按第三关正式执行。未改变的 T3 与既有禁止区域结论在同一产品版本可复用。

### t25 修订记录

本轮依据第二关反馈，仅修改原有 T1—T4 范围内的测试方法和执行步骤：

1. T4 未确认样例移除自相矛盾的成功 `level=fulltext` 索引记录，保留已存在的分析文件，直接检查“没有成功索引记录不能仅凭文件计全文”。未发明新的分析失败状态字段，也未把 `facts_state` 当分析结果。
2. T2 固定区阻挡用例追加“修正源资料 → 普通 Stage 2 生成新正文 → 旧校验不被接受”的既定要求。责任方和动作分字段检验，避免强制未获批准的返回字段布局。
3. T4 既有来源新增/删除用例内复用已接受包，覆盖“预检后来源变化、人工修改正文 → 展示刷新拒绝写入”；保留现有来源分流测试，不增加选择器。
4. 执行命令保存并向调用方返回单元测试真实退出码；失败日志仍留在独立 `/tmp` 目录。

新增测试数仍为 14，选择器仍为 18，均属于第一关批准的 T1—T4。未改变业务目标、未修改产品代码、未执行本轮正式测试；t24 及之前的审核和准备期运行只按其实际版本引用。第二关待修订复核，第三关未执行。

### t26 定向修订记录

本轮只修正第二关已指出的两项可执行性问题，仍使用 t6 批准的 T1—T4、14 个新增测试和总计 18 个选择器：

1. **T2 修复后验证**：固定区失败报告先登记为第一轮未通过；修改合成题名与证据，走普通 Stage 2 重新生成。先断言旧失败未获接受，再针对新正文创建独立 PASS 报告、通过现有登记入口写入，检查第一轮 PASS、原始失败报告未变和预检不再拒绝校验。这验证“修复后可恢复并重新通过”，不要求模型自动创造正确证据。
2. **T4 写前来源新增**：保存仅 level 变化的有效预检后，新增原本缺失的 CCCC3333 分析来源；AAAA1111 的 `analysis_level` 维持 `abstract`，BBBB2222 维持 `fulltext`，不再回滚已有论文级别或同时更改 CCCC3333 的 PDF 标记。旧预检刷新必须拒绝写入，新的预检必须判原 `process`。
3. **T4 来源删除与人工手改**：删除测试仅移除 CCCC3333 分析文件和索引记录，保留原 facts 目录项及其他论文状态，单独判断 `process`；人工改正文测试使用另一份新建的临时教授目录，完成仅 level 变化预检后修改正文，旧预检刷新必须拒绝且保留人工内容与输入包。两个场景互不污染。
4. 没有新增用例名称、特殊采集器、安装流程、真实模型测试或全仓回归。之前的 7 通过 / 11 失败属于旧测试版本；本轮没有运行测试，没有独立子代理复核，不给第二关或第三关通过结论。

### t27 定向修订记录（第二关复核处置）

依据第二关复核对提交 `0d5606b` 的意见，只修正原 T1—T4 范围内的两处可执行性问题：

1. **T4 展示刷新的计数断言**：`test_display_only_level_change_refreshes_without_model_work` 中，被统计方向集合在刷新后为 AAAA1111 摘要、BBBB2222 摘要、CCCC3333 全文（OCR-only 不因缺 facts 降级），断言由 `全文级 0 篇` 改为 **`全文级 1 篇`**，与执行计划 §3.3.1 的三类计数和图例位置一致。
2. **T1 候选引用断言**：原先用空列表比较，无法发现实现清空非空候选列表。现在夹具给待查证缺口写入**非空** `candidate_paper_ids`（包内论文 CCCC3333，不能引用缺口自身），断言渲染前后逐字保留，并按渲染前的原始记录再比较一次；同时要求可见文本不再出现原始编号。

未新增用例名称、选择器、采集器或运行链；选择器仍为 18，新增用例仍为 14。产品代码与既有测试未改。本轮按 §3 复跑 18 项（`/tmp/contact-evidence-level.kj3p7J2l`，7 通过 / 11 业务失败）。该运行可证明的是：T1 夹具的非空候选写入与渲染前取值被产品校验接受（finalize 返回 `ok`，用例继续执行到固定卡展示断言），失败原因均为产品未实现。**两条被修改的断言在该次运行中未被执行**——T1 展示用例停在固定卡首行断言、T4 展示刷新用例停在 preflight 分流断言，它们要等产品实现后由第三关首次真正运行；现有材料中没有任何这两条断言的执行结果，也不据此判实现错误或通过。该复核结论不代表第二关、第三关或合并批准。

### t28 定向修订记录（IR-32—IR-34 处置）

1. **IR-32 记录措辞**：t27 记录与 §5 改为只声明实际执行范围——该次运行证明 T1 夹具的非空候选写入与渲染前取值通过产品校验（finalize 返回 `ok`、用例继续执行），但两条被修改的断言（T1 候选引用保留、T4 展示刷新计数 全文 1／摘要 2）在本次运行中未被执行，待产品实现后由第三关首次真正运行。
2. **IR-33 重复断言**：删除固定卡循环里被前一行的 `assertNotIn("CCCC3333", visible)` 完全蕴含的可见文本检查；候选相关的检查移到能独立失败的位置——断言语义就是该缺口的原始 `evidence` 文本与 `gap_id` 在渲染后逐字不变。
3. **IR-34 前置证明绑定**：渲染前的候选记录不再取"第一条非空行"，改为先按 `evidence == FIXED_EVIDENCE` 定位被测缺口的 `gap_id`，再取该行并断言其 `evidence`，使前置证明由被测缺口决定。

未新增用例名称、选择器、采集器或运行链；选择器仍 18，新增用例仍 14；产品代码与既有测试未改。本轮模块运行结果目录 `/tmp/contact-evidence-level.aiT3QOLQ`（`module.txt`，命令为在 tests 目录运行 `python3 -m unittest -v test_stage2_evidence_level`），`Ran 14 tests`、3 通过 / 11 业务失败（失败原因与 §5 分组一致）；两条被修改的断言仍未执行到，按 IR-32 的口径记为待第三关首次运行。该复核结论不代表第二关、第三关或合并批准。

## 6. 实现符合性审核处置

独立 `implementation_reviewer`（本地 CLI，只读）对本角色产物首轮结论为**部分完成**，提出 IR-01—IR-08；处置如下。

| 问题 | 处置 |
|---|---|
| IR-01 T3 漏纳入计划指定的既有保护用例 | 已把 §1 T3 要求的三项既有选择器（`second_blocking_round_is_terminal`、`report_for_stale_render_is_rejected_without_pack_write`、`refinement_rejects_changed_input_pack`）补入 §2 与 §3；本轮 4 个既有选择器全部通过，无需改断言 |
| IR-02 T4 多项明列行为没有对应断言 | 已在既有 T4 场景补齐：索引失败残留 fulltext 计未确认、OCR-only fulltext 无 facts 仍计全文、刷新后旧 PASS 不再被接受、assignment/叙事/指纹保留、无新增任务、来源新增与删除分流；§2 描述改为与实际断言一致 |
| IR-03 来源变化用例没有改变 preflight 可见的输入 | `update_sources` 现在同时改写 `facts.json` 与真实 `论文分析/_index.json`（schema 2 记录）并落地分析文件，使新增、删除、换址对预检可见；新增删除场景用例 |
| IR-04 T1 没有检查展示和原文保留 | 三个固定卡行补断言 Zotero 链接与可见文本不含编号，黑名单行补链接断言；用渲染前快照比较 quote、translation、gap_notes、叙事与用户笔记 |
| IR-05 T2 责任交接断言允许无关错误通过 | `assert_source_owner_handoff` 增加语义断言：交接文字必须指明源或生成器责任，且不得是 `no_failed_directions`／`awaiting_second_validation`（已写入 §4 接口假设 3） |
| IR-06 旧基线用例没有要求 `process` | 改为断言 `action == "process"` 且 `reason_codes` 非空 |
| IR-07 recipe 使用未解释的 shell 占位符 | §3 改为可直接复制执行的命令，只保留 `CHECKOUT`、`RUN_ROOT` 两个显式变量并在行内说明来源 |
| IR-08 缺少交接列出的探针脚本 | 三个只读探针脚本已放入 `/tmp/contact-evidence-level.pc92prep/`（`probe_current.py`、`probe_round2.py`、`probe_packkeys.py`），§4 已列出路径 |

首轮审核版本为未提交工作树（`HEAD=f910dbd`）；处置后产物提交为 `79cd8d5` 及其后续修正提交。本审核结论不代表第二关、第三关或合并批准。

### 第二轮定向复核（对照 `48f4a49`）

独立 `implementation_reviewer` 第二轮结论为**部分完成**：IR-06、IR-07、IR-08 已闭合，IR-01—IR-05 与新增 IR-09 需继续修正。处置如下，均为测试资产修正，未改产品。

| 问题 | 处置 |
|---|---|
| IR-01 T2/T3 归属 | 既有禁止区域选择器 `test_stage2_nonrepairable_user_note_...` 在 §2 改归 T2；§5 结果按 T2 归类，T3 只计新增轮次用例与三个既有保护选择器 |
| IR-02 T4 输入与断言 | 计数用例改为真实 OCR-only 输入：`CCCC3333` 有分析文件与 `_ocr` 文件、索引 `level=fulltext`、facts 不可用；失败分析保留分析文件但仍计未确认。pack-only 刷新用例补固定卡三行与黑名单的可信题名/链接断言、旧 PASS 在验证入口被拒绝（`validator_not_accepted`）、assignment/叙事/模型指纹保留与无新增任务 |
| IR-03 来源变化夹具 | `update_sources` 现在真正改动预检可见输入：新增用例给出原本缺失的 facts/分析路径并写入索引，删除用例同时删除索引记录与分析文件，替换用例换分析文件路径；新增替换场景用例 |
| IR-04 T1 快照与黑名单 | 快照改为与 pack 逐项比较叙事文本、gap_notes、用户笔记与 collection_key；黑名单行补「链接之外可见文本不含编号」断言 |
| IR-05 交接语义 | 责任交接断言保留在 §4 接口假设 3：交接文字必须明确写出源或生成器责任；具体字段形式由测试计划工程师在实现前对齐 |
| IR-09 过窄接口断言 | 去掉方向级 `action` 与 validator 逐字段相等的要求，只断言 r4 明列结果：顶层分流、旧 PASS 被拒绝、无包完整性误报、保留业务字段与模型指纹 |

第二轮审核版本 `48f4a49`；处置后提交见 PR 分支。本审核结论不代表第二关、第三关或合并批准。

### 第三轮定向复核（对照 `a1ca141`）

第三轮结论仍为**部分完成**：IR-04、IR-06、IR-07、IR-08 已闭合，IR-01、IR-02、IR-03、IR-05、IR-09 需继续修正。处置如下，仍只改测试资产。

| 问题 | 处置 |
|---|---|
| IR-01 §5 归属 | §5 改为按 §2 归属统计：T3 四项、T2 两项、T4 一项，总计 7 项通过 |
| IR-02 T4 输入与断言 | OCR-only 索引状态改为 `unavailable`（与「无 PDF 同源 facts」一致）；刷新用例补断言规范包 `analysis_level` 已更新并与统计一致；§2 补列替换选择器；新增用例数更正为 14 |
| IR-03 来源变化夹具 | 新增用例先删除索引与文件记录，使该来源在基线中确实缺失后再出现；替换用例把索引 `file` 指向新路径并删除旧文件；`index_entry`/`write_index` 支持调用方指定分析、OCR、facts 路径 |
| IR-05 交接语义 | 责任交接断言要求同时出现责任方与动作词（修复／重新生成等），不再只匹配关键词 |
| IR-09 方向级 action | §4 假设 2 去掉方向级 `action` 要求；用例只断言顶层 `action` 与原因字段，不再对序列化结果作关键词排除 |

第三轮审核版本 `a1ca141`；处置后提交见 PR 分支。本审核结论不代表第二关、第三关或合并批准。

### 第四轮定向复核（对照 `db73fc1`）

第四轮结论为**部分完成**：IR-01、IR-04—IR-09 已闭合；IR-02、IR-03 需继续修正。处置如下。

| 问题 | 处置 |
|---|---|
| IR-02 OCR 输入与统计预期 | `ocr_file` 指向夹具真实写出的 `论文分析/_ocr/<key>.txt`；计数用例把 OCR-only 论文放进同一方向集合（`member_keys`/`relevant_keys`），并按规范包级别预期全文 1、摘要 1、未确认 1；旧记录用例预期该集合两篇未确认；刷新用例预期全文 0、摘要 2 |
| IR-03 新增来源基线 | `accepted_run(indexed=...)` 允许基线不含某篇论文；新增用例的基线索引与文件都没有 CCCC3333，变更阶段才写入索引记录、分析文件与 facts 路径 |
| §2/§5 描述 | 计数与来源用例的描述、失败分类按真实输入与预期更新 |

第四轮审核版本 `db73fc1`；处置后提交见 PR 分支。本审核结论不代表第二关、第三关或合并批准。

### 第五轮定向复核（对照 `3595a2c`）

第五轮结论为**部分完成**：IR-01、IR-03—IR-09 已闭合，IR-02 的计数部分已落实，但展示刷新夹具仍混入来源新增（基线不含 OCR-only 论文的索引记录，更新时又写入该记录），不满足「仅 level 变化」前提。处置：展示刷新用例改用含 CCCC3333 索引记录与文件的完整接受基线，刷新时保持其路径与文件状态不变，只改 AAAA1111、BBBB2222 的级别；§2、§5 描述同步。

第五轮审核版本 `3595a2c`；处置后提交见 PR 分支。本审核结论不代表第二关、第三关或合并批准。

### 第六轮定向复核（对照 `c61c26a`）

第六轮结论为**部分完成**：唯一未闭合项是 IR-02 的展示刷新夹具——`accepted_run()` 建立基线时没有为该论文写 OCR 文件与索引路径，而刷新阶段又新建。处置：`accepted_run(ocr_only=...)` 在写入接受基线时就创建 OCR 文件并记录路径，刷新阶段保持该状态不变；§5 结果分类按实际项数更正（17 项常规项为 7 通过 / 10 业务失败，展示刷新单列待复核）。

第六轮审核版本 `c61c26a`；处置后提交见 PR 分支。本审核结论不代表第二关、第三关或合并批准。

### 第七轮定向复核（对照 `2d00061`）

第七轮结论为**部分完成**：IR-01、IR-03—IR-08 仍闭合；IR-02 只剩两处——刷新阶段 `update_sources` 仍重写 OCR 文件（`mtime_ns`/`ctime_ns` 属于 artifact guard，会让实现合理地判定来源变化），以及 §5 摘要与交接数字未同步。处置：`update_sources` 不再重写任何既有产物文件，OCR 载体只通过索引条目声明；§5 与交接数字同步为 10 项业务失败＋展示刷新单项待复核。

第七轮审核版本 `2d00061`；处置后提交见 PR 分支。本审核结论不代表第二关、第三关或合并批准。

### 第八轮定向复核（对照 `10497ff`）

第八轮结论为**部分完成**：IR-01、IR-03—IR-04、IR-06—IR-09 闭合；IR-02 只剩记录对应关系，IR-05 的交接断言仍可让责任方与动作分处不同字段的结果通过。处置：§5 补清 M5 完整记录与后续三轮单项复核、模块整体运行的关系，并按修正后的夹具把展示刷新归回业务失败（合计 11 项）；交接断言改为要求同一结果字段同时出现责任方与动作词。

第八轮审核版本 `10497ff`；处置后提交见 PR 分支。本审核结论不代表第二关、第三关或合并批准。

### 第九轮定向复核（对照 `dca3160`）

第九轮结论为**部分完成**：IR-01、IR-03—IR-09 闭合，IR-02 只剩 T4 刷新用例的机器字段断言与 §5 记录细节。处置：刷新用例新增固定卡机器字段逐项比较（`status`/`evidence`/`completed_part`/`remaining_gap`/`quote`/`translation_zh`/`confidence`/`evaluated_at`/`candidate_paper_ids`/`item_key`/`gap_id`）、禁锚区完整比较与禁锚区行「链接之外不含编号」断言；§5 补清 14 项模块运行与 18 项完整运行的关系。

第九轮审核版本 `dca3160`；处置后提交见 PR 分支。本审核结论不代表第二关、第三关或合并批准。

### 第十轮定向复核（对照 `469aa83`）

第十轮结论为**部分完成**：IR-01、IR-03—IR-09 闭合，IR-02 只剩三处细节——`gap_shortlist` 用 `zip` 比较但未比较长度；索引声明的 `future_work_state: valid` 与 `facts_state: valid` 没有对应真实文件；§5 有一句重复文字且记录版本指向含糊。处置：补列表长度断言；`accept_run`/`index_entry` 按分析器真实规则记录状态（有效 future-work sidecar 必须落盘，OCR-only 记为 `failed` 且无 sidecar 路径），新增来源用例改为按真实「缺失 facts」状态声明；§5 按提交逐条写明运行记录并删除重复句。

第十轮审核版本 `469aa83`；处置后提交见 PR 分支。本审核结论不代表第二关、第三关或合并批准。

### 第十一轮定向复核（对照 `7a28bd6`）

第十一轮结论为**部分完成**：只剩 IR-02 三处说明性偏差——§1/§2 与测试注释仍写「原缺 facts 路径出现」（夹具实际保持 facts sidecar 缺失）；计数夹具把缺 sidecar 的论文记为 `failed`（分析器规则为 `unavailable`）；§5 把完整运行归到 `469aa83`。处置：三处说明与夹具状态按真实文件与规则更正，§5 运行提交改为 `7a28bd6`。

第十一轮审核版本 `7a28bd6`；处置后提交见 PR 分支。第十二轮（对照 `b7b4f6b`，提交 `10497ff` 之后的修正）结论为**完整**，原文见 `/tmp/contact-evidence-level.pc92prep/reviewer-verdict-cli-round12.md`（该外部 CLI 系列共 12 轮，其结论已被 §7 的 DSH 审核补充）；该系列审核为外部 CLI 逐轮复核，与 §7 的 DSH 子代理审核是两套独立编号。本审核结论不代表第二关、第三关或合并批准。

## 7. DSH 子代理实现符合性审核处置（自 IR-10 起，逐轮见本节）

由 DSH 的 `subagent` 以 `implementation_reviewer` 角色完成的审核（首次覆盖全部准备产物）结论为**部分完成**，提出九项；处置如下。此前 §6 记录的 IR-01—IR-09 为外部 CLI 逐轮审核的编号，两套编号不混用。各轮 DSH 审核的结论要点另存于 `/tmp/contact-evidence-level.pc92prep/` 的 `reviewer-verdict-dsh-round1.md` 起（按轮次编号，含 `…round6.md`）（本地测试工程师整理的结论摘要，完整原文在会话消息中）。

| 问题 | 处置 |
|---|---|
| IR-10（阻断）T2/T3 固定区引文在 T1 落地后不存在 | T2/T3 引文改为展示替换后仍存在的片段（`无更晚论文实现该点`、`只做了第一组`），不含 item key；§2 增列该约定 |
| IR-11（阻断）计数夹具 BBBB2222 级别仍为 None 却期望 abstract | `recorded` 显式写入 `BBBB2222: "abstract"`，与索引和预期计数（全文 1／摘要 1／未确认 1）一致 |
| IR-12（阻断）展示刷新用例的 pack 集合与统计期望冲突 | 该用例的接受基线与刷新阶段都把 OCR-only 论文放进被统计方向集合，pack 与统计都含三篇；补充 pack 论文集合断言 |
| IR-13（阻断）T1 断言 `candidate_paper_ids` 不存在 | 改为断言该字段仍存在且为 `[]`，与「候选编号不变」一致 |
| IR-14（中）来源变化夹具状态不自洽 | `update_sources` 对 `add` 保留原 facts 元数据；新增 `declare_analysis` 让换址场景的新 sidecar 真实落盘并清理旧 sidecar |
| IR-15（中）缺题名用例扫描通用错误词 | 改为断言结果里不出现 `zotero://` 与 `[…](…)` 形式的伪引用，允许失败说明里出现槽位名 |
| IR-16（中）§1 部分预期无选择器 | §2 增「§1 预期与选择的覆盖关系」表：补断言（原始报告字节不变、展示刷新缓存与 validator 不变），并写明由既有选择器覆盖或按依据不适用（本夹具无 resolved proof） |
| IR-17（轻）§5 失败归因与日志不符 | §5 按 T1/T2/T4 分组写明实际失败原因（原始 key 渲染、`validation_issue_not_repairable`、按文件存在统计/`reuse_all`） |
| IR-18（轻）§4 未列 refine-plan 成功形状 | §4 增假设 6：`status == "ok"`、`jobs == []`、`write_needed == false` |

处置后完整 18 项运行：`/tmp/contact-evidence-level.XcpOlvbX`（§3 的 18 个选择器），`Ran 18 tests`、7 通过 / 11 失败，分类与 §5 一致。该审核与本次处置不代表测试关口或合并批准。

### §7 第二轮 DSH 复核（对照 `70e8eef`）

第二轮结论为**部分完成**：IR-10—IR-15、IR-17、IR-18 闭合，IR-16 的断言已落地但描述未同步；另发现 IR-19（阻断）、IR-20、IR-21。处置如下；IR-16 的描述残留由 IR-20（§2 两行）与 IR-21（§1 覆盖表）修正，随本轮一并闭合。

| 问题 | 处置 |
|---|---|
| IR-19（阻断）§3 recipe 未覆盖 §2 全部选择器 | §3 的 `python3 -m unittest -v` 改为逐条列出全部 18 个选择器，并用 `Ran 18 tests` 作为项数校验；已用 `unittest.TestLoader` 验证 18 个名称全部可解析 |
| IR-20（轻）§2 描述未包含新增断言 | T2 行补「原始报告字节不变、失败不写成通过」，T4 刷新行补「validator 记录与 freshness 缓存字节不变」 |
| IR-21（轻）§1 覆盖表缺 T4 不重签 proof | 覆盖表该行补明「本夹具无 resolved 方向与 proof，按依据不适用；改为断言 validator 记录与 freshness 缓存不被重写」 |

本轮改动只涉及测试计划文档；测试代码未变，§5 的准备期结果按 §3 完整命令重跑后仍为 7 通过 / 11 失败（`/tmp/contact-evidence-level.XcpOlvbX`）。本审核结论不代表第二关、第三关或合并批准。

### §7 第三轮 DSH 复核（对照 `c4afa17`）

第三轮结论为**部分完成**：IR-19、IR-20、IR-21 全部闭合（18 条选择器与 §2 一一对应、可由 `unittest` 解析为 18 项；§2/§1 新增描述与断言一致；不适用依据成立），另提出五处文档同步问题 IR-22—IR-26。处置如下。

| 问题 | 处置 |
|---|---|
| IR-22 §7 标题与修订边界标签过期 | §7 标题改为「IR-10—IR-26」；修订边界补齐 t20、t21 的改动范围，并写明三次修订都不改变 T1—T4 范围与测试代码语义 |
| IR-23 §3 复跑说明重复且旧条过期 | 删除仍教人替换类名的那条旧说明，只保留「按 §2 单行取出执行」 |
| IR-24 §7 未记录 IR-16 闭合 | 第二轮小结补明：IR-16 的描述残留由 IR-20（§2 两行）与 IR-21（§1 覆盖表）修正并闭合 |
| IR-25 §5 未写测试提交 | §5 运行记录写明测试提交 `70e8eef`（`c4afa17` 未改测试代码） |
| IR-26 §5 的 T1 归因超出日志可见范围 | T1 归因限定为日志可见内容：展示用例失败在固定卡「后续论文依据」行仍含编号，禁锚区断言在该次运行中未执行；缺题名用例仍返回 `status=ok` |

本轮只改测试计划文档，测试代码与 §5 的准备期结果未变（`/tmp/contact-evidence-level.XcpOlvbX`，7 通过 / 11 失败）。本审核结论不代表第二关、第三关或合并批准。

### §7 第四轮 DSH 复核（对照 `ff0939d`）

第四轮结论为**部分完成**：IR-22—IR-26 的处置全部落实且与代码、日志相符，另有两处文档同步残留 IR-27、IR-28。处置：状态行的编号范围改为「IR-10—IR-26」；§5 的复用说明把 `dca3160` 从「只改展示刷新与来源用例」的列表中移出，注明它另改了 T2 责任交接断言；该断言在执行上的局限见 §5 运行记录说明（该次运行未执行到它）。本轮只改测试计划文档，测试代码与准备期结果未变。

第四轮审核同时确认：`git diff 305bc08..HEAD` 只有新增测试模块与两份计划文档，未改产品与既有测试；配方 18 个选择器与 §2 完全对应、无清单外用例；14 个新增用例共 149 条断言，无空断言。

### §7 第五轮 DSH 复核（对照 `2a5fdca`）

第五轮结论为**部分完成**：IR-28 闭合；未闭合项为 IR-27（范围标签落后一档）与三处轻/极轻标注 IR-29、IR-30、IR-31。处置：范围标签不再写固定编号区间，改为「自 IR-10 起，逐轮见本节」，从根因上避免标签再次落后；§5 说明 `XcpOlvbX` 未执行 `dca3160` 改动的 T2 责任交接断言、T2 分类不依赖它；修订边界补记 t22 的三个文档提交；删除 §3 两条说明之间遗留的空行。文档版本升为 t23，本轮仍未改测试代码、未重跑用例。

### §7 第六轮 DSH 复核（对照 `44183d7`）

第六轮结论为**完整**（就本轮范围）：IR-27、IR-29、IR-30、IR-31 全部闭合，未发现过期标签、归类错误或日志中不可见的推断，未引入超范围检查、空断言或产品／既有测试改动；§3 的 18 个选择器 18/18 可解析且与 §2 完全对应。另有两项可选措辞观察 N1（指明是首次登记断言失败，而非「更早断言处」）与 N2（§7 第四轮小结与 §5 修正后的措辞冲突，加指针消除歧义），本轮一并处理。文档版本升为 t24；本轮未改测试代码、未重跑用例。

该结论只覆盖测试准备产物，不代表第二关、第三关或合并批准。

### t29 定向修订记录（IR-35、IR-36 处置）

1. **IR-35（阻断）**：t28 在 T1 用例里直接读局部名 `gap_id`，产品实现到位后会在该断言抛 `NameError`。现在 `render_fixture` 把该缺口的 `gap_id` 写进渲染前快照，用例改为与 `baseline["gap_id"]` 比较；并清理了因此产生的重复行。静态名称核对确认模块内已无未绑定的读取。
2. **IR-36(a)**：§5 运行记录写明该 18 项记录对应提交 `36c630a`（`0d5606b` 加 t27 两处修正），不再写成当前版本。
3. **IR-36(b) / IR-37**：t28 提到的模块运行补上结果目录 `/tmp/contact-evidence-level.aiT3QOLQ`（`module.txt`）与命令 `python3 -m unittest -v test_stage2_evidence_level`；该次运行用的是 t28 提交后、t29 清理前的文件（比定稿多一行），项数、通过数与失败分组不受影响。另一次模块运行 `/tmp/contact-evidence-level.jhhvqtu4`（`module.txt`）用的是 t30 文件（即删除 IR-39 那两行之后的版本，提交 `a02f5c9`），同样 `Ran 14 tests`、3 通过 / 11 业务失败；t29 定稿文件（`6df795b`）没有对应的模块运行记录。两次运行都没有执行到两条被修改的断言。

未新增用例名称、选择器、采集器或运行链；选择器仍 18，新增用例仍 14；产品代码与既有测试未改。该复核结论不代表第二关、第三关或合并批准。

### t30 定向修订记录（IR-37—IR-39 处置）

1. **IR-37**：t28/t29 记录里的模块运行改为写明版本——`/tmp/contact-evidence-level.aiT3QOLQ`（`module.txt`）用的是 t28 提交后、t29 清理前的文件；另一次 `/tmp/contact-evidence-level.jhhvqtu4`（`module.txt`）用的是 t30 文件（提交 `a02f5c9`），两次都是 `Ran 14 tests`、3 通过 / 11 业务失败，均未执行到两条被修改的断言；t29 定稿文件没有对应运行。
2. **IR-38**：§5 运行记录的提交指向改为 `36c630a`（`0d5606b` 加 t27 两处修正），不再用会随文档版本漂移的措辞。
3. **IR-39**：删除被新守卫蕴含、无法独立失败的 `baseline["candidate_paper_ids"]` 比较；候选引用「可独立失败」由渲染后的 `gap["candidate_paper_ids"]` 断言承担，渲染前的非空前提由 `render_fixture` 的守卫承担。

未新增用例名称、选择器、采集器或运行链；选择器仍 18，新增用例仍 14；产品代码与既有测试未改。该复核结论不代表第二关、第三关或合并批准。

### t31 定向修订记录（IR-37 残留、IR-38 残留、IR-40、IR-41）

1. **IR-37 残留**：`/tmp/contact-evidence-level.jhhvqtu4`（`module.txt`）的 traceback 行号与 t30 文件（`a02f5c9`）逐条相同、与 t29 文件位于被删两行之下的 12 处相差 2 行，说明它跑的是 t30 代码；记录改为写明这一点，并注明 t29 定稿文件（`6df795b`）没有对应运行。第一次 traceback（228 行）在两个版本同为此行，不适用该差值。
2. **IR-38 残留**：状态行不再写「加本轮修正」，直接写测试提交 `36c630a`。
3. **IR-40(a)**：采用「守卫 + 渲染后断言」写法——`render_fixture` 为 `evidence`／`completed_part`／`remaining_gap`／`user_note` 增加显式前置守卫（夹具确实带这些机器文本），T1 用例改为把渲染后的同名字段与渲染前快照比较，不再与夹具常量重复比较；是否保留 `user_note` 同类条目一并处理。
4. **IR-40(b)**：恢复 `assert_source_owner_handoff` 里 refine-finalize 前后的 pack 字节比较（该断言覆盖 §1 T2「refine-finalize 不写」），`rewritten` 零值断言保留；两者并存。
5. **IR-41**：删除具体用例里与辅助函数重复的 `validator` 结果断言，保留 `round == 1` 与正文断言。
6. **N2**：本轮新增或改动的断言（来源新增用例的索引检查、refine-finalize 的 pack 字节比较、T1 的夹具守卫与快照比较）与既有的零 `rewritten` 断言（自 `79cd8d5` 起存在）均记为待第三关首次运行——前者未执行到，后者同样未执行到。
7. **IR-40(a) 收尾**：T1 里同一组机器字段曾被比较两次，现合并为一处与渲染前快照比较（保留该用例中唯一的 `status`、positioning、`gap_notes`、`collection_key` 断言）；测试代码只改断言与快照，选择器仍 18、新增用例仍 14，产品与既有测试未改。定稿文件模块运行 `/tmp/contact-evidence-level.WVDwWZxd`（`module.txt`，`Ran 14 tests`、3 通过 / 11 业务失败）；两条被修改的断言与新增断言仍在首次失败点之后，均未执行到，待第三关首次运行。

该复核结论不代表第二关、第三关或合并批准。

### t32 用户授权的测试精简记录

1. T1 缺可信题名用例只检查明确失败、有原因且不生成受管分析文档；删除扫描整个错误提示是否含 `zotero://` 及占位文字的断言，允许错误消息引用已有的真实链接。
2. 删除与既有 `test_stage2_nonrepairable_user_note_does_not_create_a_correction_job` 重复的新增 T2 用例，保留既有禁止区域检查。移除对应的 §2 行与 §3 选择器。
3. 当前 13 个新增用例、4 个既有选择器，§3 共 17 项；T1—T4 业务目标未变。§5、§6、§7 的 14／18 项与 7 通过／11 失败是旧提交的历史记录，未改写。此次未运行正式测试，第二关复核待完成、第三关未执行；产品与既有测试未改。

### t33 定向修订记录（第二关：旧包缺可比较基线的最小修订）

按第二关复核意见（PR 评论 comment-6245959908），只修订既有 T4 用例 `test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only` 与其在唯一测试计划中的描述：

1. 先用 `accepted_run()` 构造完整且已记录通过的包（该辅助已断言原样预检为 `reuse_all`）。
2. 删除 `pack["cache"]["preflight"]` 模拟旧包；只用现有 `contact_state.stage2_pack_content_fingerprint(pack)` 重算并写回 `pack["validator"]["pack_sha256"]`，消除删字段造成的校验摘要失配——不改产品逻辑、原始正文或其他通过记录。
3. 再调正式 `stage2_preflight()`，断言顶层 `action=process`、顶层 `reason_codes` 含 `legacy_pack_no_preflight`、各方向 `reason_codes` 不含 `validator_not_accepted`，从而证明走的是「旧包缺可比较业务来源基线 → 原 process」，而不是靠失效摘要碰巧触发。

保留原选择器，不新增用例、运行链、证明设施或业务验收要求。修订后用例在未实现的产品基线 `305bc08f8b186672108cffbba0293d249bc8b4b2` 上即通过（新实现须保持该行为）；本轮 17 项运行见 §5。该结论不代表第二关、第三关或合并批准。

### t34 定向修订记录（IR-42、IR-43 处置）

1. **IR-42**：状态行的「最新准备期复核」改为指向 §5 的 17 项记录（6 通过 / 11 业务失败、测试提交 `0fe84ab`、结果目录 `/tmp/contact-evidence-level.p49ZBXq2`）；`36c630a` 的 18 项记录按下文归入历史。
2. **IR-43**：§5 的 17 项记录写明测试代码版本 `0fe84ab`，并去掉「§3 当前的」这类会随时态漂移的措辞；为消除「日志无法区分修订前后」的歧义，本轮在提交 `0fe84ab` 的代码上重新执行了同一组 17 个选择器（结果目录即上条，`Ran 17 tests`、6 通过 / 11 业务失败，通过项与失败分组与上一份记录相同），上一份 `/tmp/contact-evidence-level.NASm842C` 作为同版本的另一份记录保留。

本轮只改测试计划文档与运行记录指向，测试代码未改，产品与既有测试未改。该结论不代表第二关、第三关或合并批准。

### t35 定向修订记录（第三关执行中的测试步骤修订）

第三关正式执行时，唯一测试计划中的 T1、T2 两个必测项各存在测试步骤本身不成立的断言/夹具（T1 两条断言、T2 一处夹具），无法得到有效结果。本地执行工程师按 Test Engineer Rule §5 停止这两项后交接；本轮由本地测试工程师只修订测试步骤，未改产品文件、未改其他测试模块、未新增或删除用例与选择器。

1. **T1 译文断言**（`FixedEvidenceDisplayTests.test_fixed_evidence_renders_trusted_references_without_touching_machine_fields`）：原断言 `assertIn("中译：" + quote[:24], analysis)` 期望的末尾带空格（第 24 个字符是空格），而侧车 `translation_zh`、paper-analysis 与 runner 的 `load_sidecar` 都对其做 `.strip()`，pack 机器值与正文实际是去空格的 `中译：Future work will extend`，任何忠实实现都不可能满足。改为断言正文出现 `- 中译：` 加上该 gap 的机器值 `gap["translation_zh"]`（与 `self.shortlist_gap("AAAA1111")["translation_zh"]` 相同），期望仍是「存储的译文被原样显示」，未删除或弱化。
2. **T1 `gap_notes` 比较形状**（同一选择器）：修好上一条后首次执行到 `assertEqual(baseline[...]["gap_notes"], accepted["narrative"]["gap_notes"])`，发现前者是 `narrative.json` 的原始列表、后者是 runner 规范后的按 `gap_id` 索引的字典，直接比较恒不成立；首次只改第 1 条后的定向运行仍在该比较处失败（`/tmp/contact-evidence-level.UyFv3Iyi/recipe-t35.txt`），据此确认它是另一处测试步骤缺陷，不是产品缺陷。按既有 `validate_narrative` 的规范形状，把渲染前快照按 `gap_id` 归一为 `{summary, explanation}` 后比较，期望内容（summary、explanation 不被展示步骤改写）不变，未放宽。
3. **T2 freshness 夹具**（`FixedEvidenceFailureTests.test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job`）：原夹具只改 facts 题名并把修正后的来源证据写入 `corrected_results/`，但 `gap_fingerprint`（quote/translation/source/page/侧车摘要）与 `candidate_fingerprint`（候选论文 digest）均未变，runner 的 `<教授目录>/论文分析/_freshness_cache.json` 仍命中；`Stage2Context.freshness_entry` 标记 `cache_hit`，`validate_freshness_results` 只对未命中的 gap 读取 results 文件，重绘仍是旧证据。改为在重新生成前删除该 gap 在 `_freshness_cache.json` 中的记录（按该 gap 的 `gap_id`），模拟来源证据被重新判定；仍走普通 `stage2-plan`/`stage2-finalize`。

受影响选择器：T1 的 `test_fixed_evidence_renders_trusted_references_without_touching_machine_fields`、T2 的 `test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job`。范围未变：仍是既有的 13 个新增用例、17 个执行选择器，T1—T4 业务目标、预期结果与 §3 命令不变。

验证：按上述两个选择器运行 `python3 -m unittest -v test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_renders_trusted_references_without_touching_machine_fields test_stage2_evidence_level.FixedEvidenceFailureTests.test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job`，`Ran 2 tests`、`OK`，退出码 0；结果目录 `/tmp/contact-evidence-level.UyFv3Iyi`（`recipe-t35-run2.txt`）。该运行只验证修订后的两条用例可执行且通过，不是第三关完整运行；t35 定稿后本地执行工程师已按 §3 的 17 个选择器完整复跑并全部通过，见 §5。

本轮只改测试代码与测试计划；`scripts/contact_state.py`、`SKILL.md` 与两个 analyzer 投影等产品文件及其他测试模块本轮未改。

### t37 定向修订记录（合并复审阻断项 1：展示刷新后的旧认证失效）

PR #92 合并复审 [issuecomment-6248851590](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6248851590) 对提交 `8fd761a` 给出 NOT_READY，阻断项 1 要求：展示刷新确实改变受管正文与校验依据时，必须正式使旧 `validator` 失效，让新正文能重新登记第一轮；原始报告留在原路径；等价重写不得清零轮次；禁止用重绑定旧通过记录代替重新校验。该要求与执行计划 r5 §3.3.5（“正文/校验依据实质变化按 §3.2 失效旧 validator，不借新绑定沿用旧 PASS；等价重写不清轮数”）及 §3.2（“只有校验依据实质变化才失效旧 validator，并对新业务版本重新开始校验”）原文一致，也与测试计划 §1 T4 的“旧 validator PASS 不再被接受”相符。

本轮发现 T4 展示刷新用例 `AnalysisLevelTests.test_display_only_level_change_refreshes_without_model_work` 末尾的一条断言与上述计划冲突：原 `self.assertEqual(pack_after.get("validator"), pack_before.get("validator"))` 要求刷新后旧 PASS 记录逐字保留并继续随包携带，实际上要求实现保留旧认证；它既违反 §3.3.5，也超出 §4 假设 4 的“validator 的存储形式不作断言”。在本地执行工程师的产品修正上该断言必然失败（`None != {...}`），因此按测试步骤缺陷处理，不改产品、不放宽预期。

修订内容（只动这一个用例的末尾，第 844—854 行）：

1. 删除上述逐字相等断言，改为 `self.assertFalse(pack_after.get("validator"), pack_after.get("validator"))`：展示变化后的 pack 不再携带绑定旧正文的认证；若实现把旧认证重绑到新正文（保留 `validator`），该断言直接失败。
2. 在同一选择器内补一条最小行为检查：用既有的 `self.write_report("pass-after-refresh.json", [], verdict="pass")` 为新正文创建 PASS 报告并调用 `self.record(...)`，断言 `status == "ok"`、`round == 1`。这证明旧认证没有被复用、新正文从第一轮重新登记；若实现保留或重绑旧记录，`stage2-record-validation` 会因已有 schema 2 的终止记录而失败或进入第二轮，该检查随之失败。
3. 注释写明：展示刷新不生成模型任务；展示变化是新校验版本，旧认证在此正式失效，新正文从第一轮重新登记。
4. 原有断言全部保留：刷新前 validator 与正文 `render_sha256` 绑定、freshness 缓存字节不变、预检 `action=process` 且方向级 `validator_not_accepted`、包内无 `pack_integrity_mismatch`、刷新后正文哈希不再等于旧绑定、固定卡/黑名单可信引用、机器字段与 assignment/叙事/模型指纹逐字不变、规范包级别与统计一致。

同步：§2 的 T4 行与 §1 覆盖关系两处原写“validator 记录不变/不被重写”，与新断言冲突，按计划原文改为“旧认证随正文实质变化正式失效、新正文重新登记第一轮；freshness 缓存仍字节不变”；§4 假设 4 补一句行为检查说明（存储形式仍不作断言）；状态行与 Test revision 同步到 t37。

受影响选择器：仅 `test_stage2_evidence_level.AnalysisLevelTests.test_display_only_level_change_refreshes_without_model_work`。范围未变：仍是 13 个新增用例、17 个执行选择器，T1—T4 目标与预期结果、§3 命令不变；未改产品文件（`scripts/contact_state.py`、`SKILL.md`、两个 analyzer 投影）与其他测试模块，未新增/删除用例或选择器。

验证（真实运行，仓库外目录 `/tmp/contact-evidence-level.VUfUAYLu`）：

- 修订前基线（同一选择器）：`python3 -m unittest -v test_stage2_evidence_level.AnalysisLevelTests.test_display_only_level_change_refreshes_without_model_work`，退出码 1，`Ran 1 test`、`FAILED (failures=1)`，失败点即旧断言 `None != {...}`（`baseline-single.txt`）。
- 修订后同一选择器：退出码 0，`Ran 1 test`、`OK`（`after-single.txt`）。
- 整个模块：`python3 -m unittest -v test_stage2_evidence_level`，退出码 0，`Ran 13 tests`、`OK`（`module.txt`）。
- 受影响既有选择器：`python3 -m unittest -v test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_second_blocking_round_is_terminal`，退出码 0，`Ran 1 test`、`OK`（`handoff.txt`）。

以上是受影响选择器的定向复验，不是第三关正式执行；§3 的 17 个选择器完整复跑与 §5 正式记录由本地执行工程师在产品与测试定稿后补，本记录不代写运行结果，也不作为合并批准。

## 8. 本地执行交付的实现符合性审核处置（2026-10-18）

独立 `implementation_reviewer` 对本地执行工程师在计划 r4 下全部应交付产物的**首次实现符合性审核**（受审版本 `165906a`，产品实现 `8f31296`）结论为**完整**；提出两项，处置如下。本节编号属于本轮审核，不与 §6、§7 的 IR 编号混用。

| 问题 | 处置 |
|---|---|
| IR-01（中）同一方向的混合报告里，可修订的叙事阻挡在本轮也失去模型修订机会 | **不改产品。** 执行计划 §3.2 原文即「只要本轮含合法固定证据卡阻挡（**包括混合报告**），refine-plan 返回明确的『需修复源数据或生成器』结果、零 rewrite jobs；refine-finalize 同样拒绝写入。调用方停止自动修订/校验循环」，第二关已批准的 `test_mixed_fixed_and_narrative_blocking_creates_no_rewrite_job` 也断言零 jobs、零写入。混合轮的叙事侧恢复路径与固定区一致：源 owner 修好来源后按正常 Stage 2 重新生成正文，再对新正文重新登记校验。若计划负责人希望把这条恢复路径写成明文，属口径补充，按 Test Engineer Rule §7 交计划负责人裁定；本轮不据此扩大范围。 |
| IR-02（轻）禁锚区「完成论文」引用缺可信题名时仍是软降级 | **已按 §3.1 收紧并复验。** 渲染禁锚区行时，`completed_by_item_key` 存在真实 item key 而 pack／论文事实／`display_references` 都取不到可信题名时，与三个固定槽位一样 `fail("missing_fixed_evidence_title")` 停止生成；只有该 key 本身缺省（既有夹具形态）才保留原「（完成论文见证据）」兜底。复验：`test_stage2_evidence_level` 13 项通过，随后按 §3 完整复跑 17 个选择器（`/tmp/contact-evidence-level.kB35xlUV/recipe.txt`，`Ran 17 tests`、`OK`）并运行全仓 `python3 -m unittest discover -p "test_*.py"`（`Ran 1028 tests`、`OK`）。 |

处理 IR-02 的产品修改后，必测项已按 §3 重新执行并取得当前版本的通过结果（§5 的两份记录结果一致）；未受影响的选择器结果直接复用。本审核结论不代表第二关、第三关最终批准或合并批准；下一步由合并审核负责人按 `Merge Reviewer Rule.md` 执行。

## 9. 合并审核处置（2026-10-18，本地执行工程师）

[合并审核](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6248142152)（受审版本 `ac301e1`）结论 NOT_READY，提出 5 项实现缺陷，均按执行计划 r4 原文在正式路径修正；没有新增锁、认证框架、通用扫描、清单外用例或强制全仓回归。

| 项 | 处置 |
|---|---|
| 1 展示刷新写前缺完整业务输入复核 | 把 preflight 的全部业务判定抽成 `stage2_preflight_assess()`（pack/版本/语义、`accepted_directions_sha256`、参数与年份、Stage-1 输入指纹、论文目录视图、署名视图、resolution evidence guards、方向映射与 accepted/freshness 指纹、artifact guards、validator 验收、分析来源投影），`stage2-preflight` 与 `stage2-refresh-display` 共用同一函数；刷新入口另加与 finalize 同款的 `stage2_preflight_cheap_inputs` 比对。任一不成立 → `needs_refresh/display_refresh_stale` 且零写入；写前在 lease 内再核 pack 指纹与分析来源投影。 |
| 2 展示刷新未进入教授级单写入保护 | `stage2-refresh-display` 的检查—渲染—写入整体放进既有 `stage2_chatgpt_handoff` 教授 writer lease（`stage2_local_writer_scope`，同一 lease 文件与 token 语义）；另一条 Stage-2 写入仍持有时 → `needs_refresh/stage2_writer_busy` 零写入。不新增锁或事务框架。 |
| 3 分析来源投影漏检 | 索引未声明载体时按既有规定从分析文件路径派生 `<analysis>.future_work.json` / `<analysis>.facts.json` 的缺失占位；pack 未收录的候选 key 用已接受投影记录的路径回填，使出现/删除/换址在前后可比；`papers` 非对象不再当空表（判 `invalid`）；索引结构错误或可读性变化一律不可比较 → 原 process。索引两侧都"不存在"时仍可比（载体由 pack 派生路径与已记录路径证明）。 |
| 4 旧版校验记录无法继续第一轮文字修订 | `fixed_evidence_direction_ids` 缺失（修复前的合法 schema 2 记录）按空列表处理；字段存在但类型或方向非法时继续拒绝。 |
| 5 指定单方向可绕过同一轮固定证据阻挡 | refine-plan／refine-finalize 先按**整轮**未解决的合法固定区阻挡判定：存在即整轮零 jobs、零写入并交源/生成器；完全没有时才按 `--direction-id` 选择文字修订。 |

复验：受影响的既有模块（`test_stage2_evidence_level`、`test_stage2_preflight`、`test_stage2_preflight_binding`、`test_resolved_direction_preflight_integration`、`test_build_issue29_stage2_fixture` 等 69 项）通过；§3 的 17 个选择器完整复跑 `Ran 17 tests`、`OK`（`/tmp/contact-evidence-level.ojprDR8c/recipe.txt`）；全仓 `python3 -m unittest discover -p "test_*.py"` 为 `Ran 1028 tests`、`OK`（`/tmp/contact-evidence-level.UiagMtvI/full-suite-mergefix.txt`）。

第 3 项"索引不存在是否等同不可比较"的边界依据（实测）：把索引不存在也当作不可比较后，`test_resolved_direction_preflight_integration` 与 `test_build_issue29_stage2_fixture` 出现 5 failures + 3 errors——这两组既有测试的教授本来就没有 `_index.json`，其被认可的预期是 `reuse_all`。因此保留划分：**索引存在但不可读或结构错误 → 不可比较 → 原 process**；**索引两侧都不存在 → 可比，载体由 pack 派生路径与已投影记录路径证明**，从而"文件后来出现"仍能被发现，同时不回归既有 index-less 行为。

## 10. r5 §3.4 入口对齐的整合与复验（2026-10-18，本地执行工程师）

执行计划 r5 §3.4 已获[正式批准](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6248571193)（`contact-evidence-level-r5`，P1—P4 全 PASS），下一负责人为产品实现者。本轮按该节执行：**先把 PR #93 已合并的同目录入口整合进本分支，再只改三个新增调用点**，并按 r4 §4.1 核对已落地的 PR #91。

### 整合

- `git merge origin/main`（当时 main tip `74bd29b`）把已合并的 PR #91（stage-2 三处修复，含 finalize 的 validator 生命周期与 `Stage2PackRefineContext` 规范化 papers 取值）与 PR #93（七个同目录入口、`_stage2_chatgpt_handoff_impl.py`、文档调用转换、nix/flake）并入本分支。冲突只有 3 处，处置如下：
  1. `SKILL.md` 白话校验段落：保留上游新增的报告位置唯一性规则（`validation_location_ambiguous`、逐处实际行号）**并**保留本 PR 的固定证据卡交源规则，两者不互相替代。
  2. `contact_state.py` `Stage2PackRefineContext.__init__`：采用上游从 pack 规范 `papers` 映射取值的写法（该记录已带 `analysis_level`），删掉本分支同义的按方向补记循环。
  3. `contact_state.py` `cmd_stage2_finalize`：保留上游的 validator 生命周期块，并在 `stage2_preflight_metadata(...)` 调用上保留本 PR 的 `papers_map=papers_map` 参数。
- 合并后 `git diff origin/main..HEAD` 只列本 PR 的 7 个文件；`contact_state.py` 可编译；本 PR 的 U1/U5 符号（`stage2_preflight_assess`、`stage2_local_writer_scope`、`stage2_analysis_projection`、`stage2_projection_recorded_paths`、`stage2_display_text`、`stage2-refresh-display` 等）全部保留。

### §3.4 三个调用点对齐

- codex analyzer Step 2.6、opencode analyzer Step 2.6、SKILL.md 阶段 2 early preflight gate 的刷新入口示例，统一改为 `<professor-contact-skill-dir>/scripts/contact_state stage2-refresh-display --professor-dir <教授目录> --preflight-file <该次 payload>`；参数、事务 payload、成功/错误分支与返回消费一律不变，未加 shell wrapper 或 fallback，未改 runner 实现、业务 schema、lease、managed-write 或两轮限制。已确认三处不再出现 `python3 <…>/scripts/contact_state.py stage2-refresh-display`。
- 入口契约静态核对：PR #93 的 `scripts/contact_state` 用 `os.execv` 把 argv 原样转交相邻 `contact_state.py`，未改写 stdout/stderr/退出码；直接调用该入口执行 `stage2-refresh-display --help` 正常打印该子命令用法（退出码 0），证明新子命令经固定入口可达。

### 复验（合并与对齐后的当前版本）

- 上游产品改动已进入本分支，故按 Test Engineer Rule 对必测项重新取证：§3 的 17 个选择器完整执行 `/tmp/contact-evidence-level.sn3UGj6n/recipe.txt`，`Ran 17 tests`、`OK`、退出码 0。
- 全仓 `python3 -m unittest discover -p "test_*.py"`：`Ran 1035 tests`、`OK (skipped=1)`、退出码 0（`/tmp/contact-evidence-level.UiagMtvI/full-suite-merged.txt`；项数较合并前的 1028 增加，是上游 main 带入的新测试模块）。
- 此前 t35／t36 记录仍按其版本引用；本节是当前版本（合并提交 `3f4d275` 及其后的记录提交）的第三关结果，不代表合并批准。

## 11. 合并复审处置（2026-10-18，本地执行工程师）

[合并复审](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6248851590)（受审 `8fd761a`）结论 NOT_READY，两项阻断性实现缺陷均交产品实现者，已按执行计划 r5 §3.2／§3.3.4—5 原文修正：

| 项 | 处置 |
|---|---|
| 1 展示刷新后旧校验记录使重新校验流程卡住 | `stage2-refresh-display` 现在区分展示是否真的变化：受管正文实质变化时**正式失效旧 `validator`**（不再随包携带、也不重绑），新正文可从第一轮重新登记，原始报告文件不动；无展示变化时（只有未参与渲染的候选 key 级别变化）**不重绘正文**，保留认证与其渲染绑定并只把 `pack_sha256` 重绑到新包内容，轮次不清零；写入前发现受管正文被手改仍返回 `needs_decision/manual_markdown_changed`，不覆盖。 |
| 2 取得写入保护后未再次复核全部业务输入 | 刷新的**全部业务判定与写入都在既有的教授 writer lease 内重做**：持锁后重新读取 target/Stage 1 状态、重跑 `stage2_preflight_assess()`（论文目录与署名视图、方向映射、时效缓存、来源守卫、validator 之外的业务门）与 `stage2_preflight_cheap_inputs()`，并与取得租约前的决定逐项比对；任一变化 → `needs_refresh/display_refresh_stale`（drift `business_inputs_changed`／`target_or_snapshot_changed`）且零写入。未新增锁、通用扫描或证明框架。 |

配套测试步骤修订（t37，见该节）：T4 展示刷新用例原先断言"`pack["validator"]` 逐字保留"，与 §3.3.5 及 §4 假设 4（存储形式不作断言）冲突，已由本地测试工程师改为断言刷新后不再携带绑定旧正文的认证、且新正文可重新登记第一轮；其余断言与范围不变（仍 13 个新增用例、17 个执行选择器）。

复验（当前版本）：

- §3 的 17 个选择器完整复跑：`/tmp/contact-evidence-level.xa9UbsfO/recipe.txt`，`Ran 17 tests`、`OK`、退出码 0；变基到当时远端 tip（`8fd761a`）后的提交 `e55e469` 上再跑一次同一组选择器，`/tmp/contact-evidence-level.QW2xummd/recipe.txt`（`Ran 17 tests`、`OK`、退出码 0）。
- 全仓 `python3 -m unittest discover -p "test_*.py"`：`Ran 1035 tests`、`OK (skipped=1)`、退出码 0（`/tmp/contact-evidence-level.UiagMtvI/full-suite-mergefix2.txt`）。
- 写前复proof 的定向探针（仓库外只读探针，非必测项）：在 T4 夹具上把 `stage2_local_writer_scope` 包一层，在**取得租约之后**改动一个被绑定的业务输入（教授本地 target 的 `user_note`），刷新入口返回 `needs_refresh/display_refresh_stale`、`drift=["business_inputs_changed"]`、退出码 2，且输入包与受管正文字节不变（`/tmp/contact-evidence-level.UiagMtvI/probe_inlease_recheck.py`）。
- t37 的定向记录（测试工程师）另见 `/tmp/contact-evidence-level.VUfUAYLu/`；t35／t36 旧记录仍按其版本引用。
