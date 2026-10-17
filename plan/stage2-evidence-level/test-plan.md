# Stage 2 固定证据与分析级别测试计划

- Test revision：contact-evidence-level-t21；对应 [执行计划 r4](implementation-plan.md)。
- Requirement revision：2026-10-17 用户授权的 U1/U5 修复；测试资产准备基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`。
- 状态：第一关 PASS（t6 复核记录）；测试代码与完整命令已落实，实现符合性审核两套编号（外部 CLI 的 IR-01—IR-09 记于 §6，DSH 子代理的 IR-10—IR-21 记于 §7）均已处置，处置后准备期复核在未实现的产品上得到 7 通过 / 11 业务失败（§5）。第二关待复核，第三关未执行；这里不宣称任何业务修复完成或测试通过。
- [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 决定范围；附录/步骤不追加清单外检查。

## 1. 唯一必测清单

| 项 | 目标与输入 | 预期结果 | 足够的检查入口 |
|---|---|---|---|
| T1 | 同一既有夹具覆盖固定卡 evidence/completed_part/remaining_gap 及禁锚区 evidence 中已知编号，可信标题/链接已在当前材料；另一个缺可信题名的引用 | 正式 finalize 输出题名/链接，上述机器字段/候选编号与事实不变，其他说明原意、作者 quote/translation、用户笔记不变；缺题名明确失败且不生成伪引用 | 既有 runner CLI 测试夹具，检查 Markdown 与 pack 必要字段 |
| T2 | 当前受管正文上的固定区 blocking 与混合固定/叙事 blocking 原始报告；复用现有用户笔记/论文一览禁止区域报告 | 合法固定区第一轮失败确实登记；禁止区域报告继续拒绝且无 correction jobs；原始报告不改、非通过；refine-plan 无 jobs、明确交源/生成器处理，refine-finalize 不写；同内容重试不能清轮数。修复正式生成内容后普通 finalize 产生新正文，旧 PASS/失败不冒充新结果 | 既有 Stage2ValidationHandoffTests 的报告/正文夹具和 record/refine/finalize CLI |
| T3 | 纯 narrative 第一次失败→现有合法修订→第二次仍失败（可用第二轮新固定卡阻挡覆盖其归属）；及已绑定报告对应的正文/pack被改 | 纯文字修订仍可完成且第二次终态不继续第三轮；不允许用过期报告改事实或覆盖手改文件 | 复用该模块已有 second_blocking_round_is_terminal、stale_render、changed_input_pack 对应测试；只调整受新登记分类影响的断言 |
| T4 | 复用同一方向的 fulltext、abstract（有分析文件）、未确认（分析失败：记录级别为空，索引里残留旧 fulltext 字符串）及 OCR-only fulltext/facts unavailable 夹具，并将 §2 已有缺 analysis_level 兼容样例归入本项（有分析文件/PDF 仍为未确认，不复制样例）；有完整接受基线且 /tmp facts 已不存在，原正文已有有效绑定 validator PASS，仅 level/render 变更由正式 preflight→展示刷新，同一场景复用 T1 已知引用及正式 pack 中可信题名/链接；在同一来源夹具中依次作新增、删除、替换分析依据（含原缺分析路径出现、facts sidecar 保持缺失），并保留旧缺基线情形 | 三类计数/规范包一致，失败记录即使残留 fulltext、旧记录缺 analysis_level 即使有分析文件/PDF，均归未确认；同一 pack-only 刷新输出的固定卡 evidence/completed_part/remaining_gap 与禁锚区 evidence 均显示可信题名/链接，原始机器字段及候选编号不变；纯展示刷新使正文实质变化后，旧 validator PASS 不再被接受，不运行模型校验；等价重写仍不清轮数。纯展示后再预检不因过期包完整性摘要误 process，保留 assignment/模型指纹、不重签 proof、不额外生成分析/归属/时效任务；新增/删除/替换、无法比较的旧基线走原 process，不能误当 display-only；复用已有写前漂移/手改保护检查，不写不确定结果 | 既有 BaseEnv/preflight/pack-only 渲染及 guard 夹具，检查分流原因、pack/Markdown及任务记录；只覆盖这些直接反例，不交叉穷举，不跑真实模型 |

T1—T4 是上限。无需真实 Zotero、下载/PDF分析重跑、Nix/APM重装、全教授流程或完整测试模块回归；本次未改安装和模型业务。报告中“四位教授”与“10+1”是缺陷背景，不能强制采集私人材料或追加四次模型验收。

## 2. 测试资产与选择器对照

测试代码全部放在 `.apm/skills/professor-contact/tests/test_stage2_evidence_level.py`，只复用 `test_contact_state.py` 的 `BaseEnv`、`run_cli`、`run_bound_stage2_plan`、`run_bound_stage2_finalize`、`stage2_style_validation_report` 和既有合成夹具，不新建判定框架、不改产品代码、不改写既有用例。

| 项 | 选择器 | 该用例断言的计划行为 |
|---|---|---|
| T1 | `test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_renders_trusted_references_without_touching_machine_fields` | 固定卡 evidence/completed_part/remaining_gap 与禁锚区 evidence 显示可信题名/链接；pack 机器字段、候选编号、quote、用户笔记逐字不变 |
| T1 | `test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_without_trusted_title_fails_instead_of_inventing_one` | 缺可信题名时受影响生成明确失败，不写伪引用 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job` | 固定区 blocking 第一轮登记为 needs_correction，refine-plan 零 jobs 并交源/生成器，refine-finalize 不写；原始报告字节不变、失败不写成通过 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_mixed_fixed_and_narrative_blocking_creates_no_rewrite_job` | 混合固定/叙事 blocking 同样零 rewrite jobs，不把固定区交给模型 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_repeating_the_same_fixed_card_report_does_not_clear_the_round` | 同内容重试不能清轮数，也不写入通过结果 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_forbidden_user_note_and_paper_table_keep_their_rejection` | 用户笔记、论文一览仍被拒绝，无 correction jobs，正文与 pack 不变 |
| T2/T3 引文约定 | T2/T3 的 blocking 引文取展示替换后仍存在的片段（`无更晚论文实现该点`、`只做了第一组`），不含 item key，否则 T1 落地后 `find_line` 会找不到行 | 测试文件常量 `FIXED_EVIDENCE_QUOTE`、`COMPLETED_PART_QUOTE` |
| T3 | `test_stage2_evidence_level.NarrativeRoundBoundTests.test_narrative_correction_rounds_stay_bound_and_terminal_state_is_recorded_once` | 纯叙事第一轮→合法修订→第二轮固定卡阻挡登记为 fail_after_2_rounds，不继续第三轮、不再发修订 |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_second_blocking_round_is_terminal` | 既有轮次终止结论继续成立（第二轮终态、第三次 plan 零 jobs） |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_report_for_stale_render_is_rejected_without_pack_write` | 正文被改后旧报告被拒绝且零写入 |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_refinement_rejects_changed_input_pack` | 输入包变化后旧报告被拒绝、无修订任务 |
| T2 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job` | 既有禁止区域报告拒绝与零修订任务断言继续成立 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_counts_follow_the_recorded_analysis_level` | 同一方向集合内三类计数与规范包级别一致；失败分析（文件与索引仍留 fulltext）计未确认，OCR-only 全文（有分析/OCR 文件、无 facts）仍计全文 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_legacy_records_without_level_count_as_unconfirmed` | 缺 analysis_level 的旧记录即使有分析文件也计未确认 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_display_only_level_change_refreshes_without_model_work` | 完整接受基线下（被统计方向集合已含 OCR-only 论文）仅 level 变化判为展示刷新；刷新后统计与规范包级别更新、旧 PASS 不再被接受、assignment/叙事/模型指纹保留、validator 记录与 freshness 缓存字节不变、下次预检不误报包完整性 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_source_change_routes_back_to_the_process_path` | 原缺分析路径出现（facts sidecar 仍缺失）时走原 process |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_deleted_analysis_source_also_routes_back_to_process` | 分析依据被删除时同样走原 process |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_replaced_analysis_source_routes_back_to_process` | 分析文件换址（索引路径与旧文件同时变化）时走原 process |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only` | 旧包缺可比较业务基线走原 process |

### §1 预期与选择的覆盖关系

| §1 预期 | 覆盖方式 |
|---|---|
| T2 原始报告不改 | `assert_source_owner_handoff` 比较报告字节；`test_repeating_...` 断言重复登记不写通过结果 |
| T2 修复生成内容后普通 finalize 产生新正文、旧 PASS/失败不冒充 | T4 展示刷新用例断言旧 PASS 在验证入口被拒绝（`validator_not_accepted`）；轮次终态不冒充新结果由本 recipe 的既有 `test_stage2_second_blocking_round_is_terminal` 覆盖 |
| T4 等价重写仍不清轮数 | T3 用例断言 `round_retained`、`round == 1`、`phase == awaiting_second_validation` |
| T4 不重签旧 resolved proof | 本夹具无 resolved 方向、无 resolved proof，该项不适用于 T4 场景，按依据不设断言；展示刷新用例改为断言 `validator` 记录与 freshness 缓存不被重写 |
| T4 复用写前漂移/手改保护 | 产品已有的写前漂移与 `managed_write` 手改保护由 `test_stage2_style_validation_handoff` 的 `stale_render`／`changed_input_pack` 选择器覆盖（本 recipe 已纳入），不重复证明 |
| T4 不额外生成分析/归属/时效任务 | 展示刷新用例断言 freshness 缓存字节不变且 validator 记录不变；无新任务记录即无新任务 |

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
  test_stage2_evidence_level.FixedEvidenceFailureTests.test_forbidden_user_note_and_paper_table_keep_their_rejection \
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
echo "exit=$? run_root=$RUN_ROOT"
```

- 上面 18 个选择器与 §2 的选择器表一一对应（T1 两项、T2 四项、T3 一项、T4 七项、既有 T2 一项、既有 T3 三项）；`Ran 18 tests` 是本 recipe 的预期项数。
- 也可按项复跑：把某一行单独取出执行；`-v` 输出逐用例结果。分项结果由这些断言判定，没有额外 JSON oracle。

- 准备顺序：`git status` 确认 checkout 干净 → 进入 tests 目录 → 建 run 目录 → 运行上面命令。没有安装、外部服务、模型或 Zotero 需求；`BaseEnv` 的临时目录已提供隔离。
- 失败处理：产品断言失败原样保留；命令或环境错误记无法判断并只重试受影响命令；未执行不得填 PASS；已确认失败不得被后续清理覆盖。

## 4. 准备记录与接口交接

- 已准备：新建 `test_stage2_evidence_level.py`（T1—T4 共 14 个新增用例）与 T2/T3 既有选择器组成上述 recipe；未改动产品、既有测试和共享夹具，未操作用户教授目录。仓库外材料：`/tmp/contact-evidence-level.pc92prep/` 含 `recipe.txt`（准备期输出）、`reviewer-handoff.md`、`reviewer-verdict.md`、`reviewer-run.log` 和三个只读探针脚本 `probe_current.py`、`probe_round2.py`、`probe_packkeys.py`。
- 接口假设（实现方需对齐，不一致时由测试计划工程师按执行计划调整，不改名迁就；这些假设是执行计划 r4 §3.2、§3.3 的实现接口，不是新增验收要求）：
  1. 仅展示刷新入口取 `stage2-refresh-display --professor-dir <dir> --preflight-file <file>`，成功时 `status=ok` 且 `display_refreshed=true`。
  2. preflight 顶层 `action` 对仅 level 变化返回 `refresh_display`，对来源出现、删除、替换或基线不可比较返回 `process` 并给出具体 `reason_codes`；方向级返回形状不作断言。
  3. 固定区阻挡的责任交接结果里，`reason_code`/`message`/`detail` 至少一处同时写出责任方（源／生成器／生成方／数据准备）与应做的动作（修复／修正／重新生成／处理／补齐等），且不出现 `no_failed_directions`、`awaiting_second_validation`。
  4. 展示刷新后重绘的正文与旧 validator 的 `render_sha256` 绑定不同，旧 PASS 在验证入口被拒绝（预检给出 `validator_not_accepted`）；包内不得出现 `pack_integrity_mismatch`，方向级 `action` 与 validator 的存储形式不作断言。
  5. 接受基线按来源 key 与类型记录路径、存在状态和成功/可用状态，使新增、删除、换址在预检可见；缺可信题名走明确失败结果（`status != ok` 且有 `reason_code`/`message`）。
  6. 固定区阻挡的 `stage2-refine-plan` 以成功结果返回：`status == "ok"`、`jobs == []`、`write_needed == false`，责任说明写在 `reason_code`/`message`/`detail` 之一；`stage2-refine-finalize` 返回零 `rewritten` 且不改动 pack 与正文。
- 未改动范围：U2/U3/U4、Stage 3—5、安装与 Nix/APM、真实模型或教授流程均未纳入，也未借此要求全仓回归。

## 5. 复核与结果

本次确定性测试无自动重试。产品断言失败原样保留；先修产品再复验受影响项。命令/环境错误记无法判断，修正错误后只重试受影响命令，保留此前记录。未执行不得填 PASS；后续清理错误不得覆盖已确认失败。

记录格式保持简单：实际提交、T1—T4逐项通过/业务失败/无法判断/未执行、实际命令与输出位置、复用结果来源、剩余问题及负责人。原始日志和临时数据在仓库外，公开提交仅必要脱敏摘要。

准备期复核（本地测试工程师，非第三关正式执行）：产品提交 `305bc08f8b186672108cffbba0293d249bc8b4b2`（未实现状态），命令为上面 §3 的命令，结果目录 `/tmp/contact-evidence-level.XcpOlvbX`（`recipe.txt`），退出码 1，`Ran 18 tests`、`FAILED (failures=11)`。

- 通过 7 项：T3 四项（`NarrativeRoundBoundTests` 一项与三个既有保护选择器）、T2 两项（既有禁止区域选择器与 `test_forbidden_user_note_and_paper_table_keep_their_rejection`）、T4 一项（缺基线走 process）。
- 业务失败 11 项，按实际失败原因分组：
  - T1 两项：展示用例首个断言失败在固定卡「后续论文依据」行仍含 `AAAA1111`（未做题名/链接替换），禁锚区断言在该次运行中未执行，不据此判断；缺可信题名用例仍返回 `status=ok` 并生成分析文件（未拒绝）。
  - T2 三项：固定区 blocking 的 `record` 返回 `error` / `validation_issue_not_repairable`（产品尚未允许登记），因此 refine 分流无法进行。
  - T4 六项：`test_counts_...` 为 `全文级 3 篇`（按文件存在统计，未按记录级别）；`test_legacy_...` 为 `全文级 2 篇`（同上）；`test_display_only_...` 与三个来源变化用例为 `reuse_all`（未实现展示刷新与来源变化识别）。
- 运行记录对应关系：本节数字来自测试提交 `70e8eef`（`c4afa17` 未改测试代码）、按 §3 逐条 18 个选择器执行的完整运行 `/tmp/contact-evidence-level.XcpOlvbX`（`recipe.txt`）。此前各版记录保留：`/tmp/contact-evidence-level.VgZ9JU6w`（提交 `dca3160`，18 项、7 通过 / 11 失败）、`/tmp/contact-evidence-level.h3SBpUMF`（提交 `3595a2c`，同类）、`/tmp/contact-evidence-level.M5wh17Uv`（提交 `3595a2c`，同类）。夹具在 `c61c26a`、`2d00061`、`10497ff`、`dca3160`、`469aa83` 上只改了展示刷新与来源用例，未受影响选择器按上述记录复用，不重复运行。
- 作废的早期记录：`/tmp/contact-evidence-level.oa4NuJoS` 与 `/tmp/contact-evidence-level.h3SBpUMF` 中因夹具未真正改变预检输入而作废的来源变化项不计入本轮分类，原日志保留。
- 该记录只用于确认选择器可执行、判定 T3 已成立和暴露产品缺口，不替代第三关正式执行，也不作为任何通过结论。

修订边界：t19 按 DSH 子代理的实现符合性审核（IR-10—IR-18）改用展示后仍存在的固定区引文、让计数与展示刷新夹具自洽、保留机器字段与来源元数据，并补齐 §1 覆盖关系与接口假设；t20 按第二轮 DSH 复核（IR-19—IR-21）把 §3 命令改为逐条 18 个选择器、补齐 §2 与 §1 的描述并整理审核记录；t21 按第三轮 DSH 复核（IR-22—IR-26）同步文档标签、删除过期复跑说明并限定 §5 的归因范围。三次修订都不改变 t6 已批准的 T1—T4 范围与预期结果与测试代码语义。执行计划 r4 已获[正式批准](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6228535516)，本次不重开其未受影响关口。

交接：T1/T2/T4 的 11 项业务失败交产品实现负责人修复，实现落地后由本地测试工程师同步受影响选择器并做第二关复核材料，再由本地执行工程师按第三关正式执行；T3 与既有禁止区域结论在当前产品版本已成立，无需重跑。

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

第十一轮审核版本 `7a28bd6`；处置后提交见 PR 分支。第十二轮（对照 `b7b4f6b`，提交 `10497ff` 之后的修正）结论为**完整**，原文见 `/tmp/contact-evidence-level.pc92prep/reviewer-verdict-round12.md`；该系列审核为外部 CLI 逐轮复核，与 §7 的 DSH 子代理审核是两套独立编号。本审核结论不代表第二关、第三关或合并批准。

## 7. DSH 子代理实现符合性审核处置（IR-10—IR-26）

由 DSH 的 `subagent` 以 `implementation_reviewer` 角色完成的审核（首次覆盖全部准备产物）结论为**部分完成**，提出九项；处置如下。此前 §6 记录的 IR-01—IR-09 为外部 CLI 逐轮审核的编号，两套编号不混用。

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
