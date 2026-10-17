# Stage 2 固定证据与分析级别测试计划

- Test revision：contact-evidence-level-t30；对应 [执行计划 r4](implementation-plan.md)。
- Requirement revision：2026-10-17 用户授权的 U1/U5 修复；测试资产准备基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`。
- 状态：第一关 PASS（t6 复核记录，T1—T4 范围不变）；t26 定向修正 T2 的修复后重新校验，以及 T4 写前来源变动与人工改动互相干扰的问题；t27 按第二关复核（对照 `0d5606b`）修正 t26 引入的 T4 展示刷新计数断言与 T1 候选引用断言；t28 按其后定向复核（IR-32—IR-34）把前置候选证明绑定到被测缺口、去掉被蕴含的重复断言、并把运行记录改为只声明实际执行到的范围；t29 修正 t28 引入的 `gap_id` 未绑定读取与两处记录指向；t30 按其后定向复核（IR-37—IR-39）改准运行记录的版本指向、删掉被守卫蕴含的重复断言，并在定稿文件上补一次模块运行（见修订记录）。第二关待复核，第三关未执行。最新准备期复核为 7 通过 / 11 业务失败（§5，测试提交 `0d5606b` 加本轮修正），此前记录只按其实际版本引用；审核处置仅适用于各自记录版本（§6、§7）。
- [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 决定范围；附录/步骤不追加清单外检查。

## 1. 唯一必测清单

| 项 | 目标与输入 | 预期结果 | 足够的检查入口 |
|---|---|---|---|
| T1 | 同一既有夹具覆盖固定卡 evidence/completed_part/remaining_gap 及禁锚区 evidence 中已知编号，其中待查证缺口带非空 `candidate_paper_ids`，可信标题/链接已在当前材料；另一个缺可信题名的引用 | 正式 finalize 输出题名/链接，上述机器字段/候选编号与事实不变，其他说明原意、作者 quote/translation、用户笔记不变；缺题名明确失败且不生成伪引用 | 既有 runner CLI 测试夹具，检查 Markdown 与 pack 必要字段 |
| T2 | 当前受管正文上的固定区 blocking 与混合固定/叙事 blocking 原始报告；复用现有用户笔记/论文一览禁止区域报告 | 合法固定区第一轮失败确实登记；禁止区域报告继续拒绝且无 correction jobs；原始报告不改、非通过；refine-plan 无 jobs、明确交源/生成器处理，refine-finalize 不写；同内容重试不能清轮数。源/生成器修正后普通 finalize 产生新正文，旧失败不可直接放行；新正文重新提交校验且记录 PASS 后才能获得新的通过状态，旧原始报告不变 | 既有 Stage2ValidationHandoffTests 的报告/正文夹具和 record/refine/finalize CLI |
| T3 | 纯 narrative 第一次失败→现有合法修订→第二次仍失败（可用第二轮新固定卡阻挡覆盖其归属）；及已绑定报告对应的正文/pack被改 | 纯文字修订仍可完成且第二次终态不继续第三轮；不允许用过期报告改事实或覆盖手改文件 | 复用该模块已有 second_blocking_round_is_terminal、stale_render、changed_input_pack 对应测试；只调整受新登记分类影响的断言 |
| T4 | 复用同一方向的 fulltext、abstract（有分析文件）、未确认（存在旧分析文件，但没有成功分析索引记录，也没有有效级别）及 OCR-only fulltext/facts unavailable 夹具，并将 §2 已有缺 analysis_level 兼容样例归入本项（有分析文件/PDF 仍为未确认，不复制样例）；有完整接受基线且 /tmp facts 已不存在，原正文已有有效绑定 validator PASS，仅 level/render 变更由正式 preflight→展示刷新，同一场景复用 T1 已知引用及正式 pack 中可信题名/链接；复用现有隔离夹具分别检查分析来源新增、删除、换址（含原缺分析路径出现、facts sidecar 保持缺失）及人工修改正文；来源新增只修改新论文的记录/文件，已有论文的分析级别与来源保持预检时状态；删除与人工修改使用互不影响的独立临时目录，并保留旧缺基线情形 | 三类计数/规范包一致，无成功分析索引记录即使残留分析文件、旧记录缺 analysis_level 即使有分析文件/PDF，均归未确认；同一 pack-only 刷新输出的固定卡 evidence/completed_part/remaining_gap 与禁锚区 evidence 均显示可信题名/链接，原始机器字段及候选编号不变；纯展示刷新使正文实质变化后，旧 validator PASS 不再被接受，不运行模型校验；等价重写仍不清轮数。预检后来源变动或受管正文被人工修改时，展示刷新必须分别拒绝写入、保持输入包和正文原样；纯展示后再预检不因过期包完整性摘要误 process，保留 assignment/模型指纹、不重签 proof、不额外生成分析/归属/时效任务；新增/删除/替换、无法比较的旧基线走原 process，不能误当 display-only；复用已有写前漂移/手改保护检查，不写不确定结果 | 既有 BaseEnv/preflight/pack-only 渲染及 guard 夹具，检查分流原因、pack/Markdown及任务记录；只覆盖这些直接反例，不交叉穷举，不跑真实模型 |

T1—T4 是上限。无需真实 Zotero、下载/PDF分析重跑、Nix/APM重装、全教授流程或完整测试模块回归；本次未改安装和模型业务。报告中“四位教授”与“10+1”是缺陷背景，不能强制采集私人材料或追加四次模型验收。

## 2. 测试资产与选择器对照

测试代码全部放在 `.apm/skills/professor-contact/tests/test_stage2_evidence_level.py`，只复用 `test_contact_state.py` 的 `BaseEnv`、`run_cli`、`run_bound_stage2_plan`、`run_bound_stage2_finalize`、`stage2_style_validation_report` 和既有合成夹具，不新建判定框架、不改产品代码、不改写既有用例。

| 项 | 选择器 | 该用例断言的计划行为 |
|---|---|---|
| T1 | `test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_renders_trusted_references_without_touching_machine_fields` | 固定卡 evidence/completed_part/remaining_gap 与禁锚区 evidence 显示可信题名/链接，可见文本不再出现原始编号（由既有的逐槽位 `assertNotIn` 保证）；非空 `candidate_paper_ids`、原始 `evidence`、`gap_id`、quote、翻译、用户笔记逐字不变 |
| T1 | `test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_without_trusted_title_fails_instead_of_inventing_one` | 缺可信题名时受影响生成明确失败，不写伪引用 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job` | 固定区 blocking 第一轮登记为 needs_correction，refine-plan 零 jobs 并交源/生成器，refine-finalize 不写；原始报告字节不变；随后模拟修正题名与来源证据，经普通 stage2-plan/finalize 生成新正文；新报告登记前旧失败不被接受，新报告确认为 PASS 后才接受新正文，轮次按新业务版本重新从第一轮计，原失败报告保持原字节 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_mixed_fixed_and_narrative_blocking_creates_no_rewrite_job` | 混合固定/叙事 blocking 同样零 rewrite jobs，不把固定区交给模型 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_repeating_the_same_fixed_card_report_does_not_clear_the_round` | 同内容重试不能清轮数，也不写入通过结果 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_forbidden_user_note_and_paper_table_keep_their_rejection` | 用户笔记、论文一览仍被拒绝，无 correction jobs，正文与 pack 不变 |
| T2/T3 引文约定 | T2/T3 的 blocking 引文取展示替换后仍存在的片段（`无更晚论文实现该点`、`只做了第一组`），不含 item key，否则 T1 落地后 `find_line` 会找不到行 | 测试文件常量 `FIXED_EVIDENCE_QUOTE`、`COMPLETED_PART_QUOTE` |
| T3 | `test_stage2_evidence_level.NarrativeRoundBoundTests.test_narrative_correction_rounds_stay_bound_and_terminal_state_is_recorded_once` | 纯叙事第一轮→合法修订→第二轮固定卡阻挡登记为 fail_after_2_rounds，不继续第三轮、不再发修订 |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_second_blocking_round_is_terminal` | 既有轮次终止结论继续成立（第二轮终态、第三次 plan 零 jobs） |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_report_for_stale_render_is_rejected_without_pack_write` | 正文被改后旧报告被拒绝且零写入 |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_refinement_rejects_changed_input_pack` | 输入包变化后旧报告被拒绝、无修订任务 |
| T2 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job` | 既有禁止区域报告拒绝与零修订任务断言继续成立 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_counts_follow_the_recorded_analysis_level` | 同一方向集合内三类计数与规范包级别一致；没有成功分析索引记录（即使残留分析文件）计未确认，OCR-only 全文（有分析/OCR 文件、无 facts）仍计全文 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_legacy_records_without_level_count_as_unconfirmed` | 缺 analysis_level 的旧记录即使有分析文件也计未确认 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_display_only_level_change_refreshes_without_model_work` | 完整接受基线下（被统计方向集合已含 OCR-only 论文，刷新后计全文 1、摘要 2）仅 level 变化判为展示刷新；刷新后统计与规范包级别更新、旧 PASS 不再被接受、assignment/叙事/模型指纹保留、validator 记录与 freshness 缓存字节不变、下次预检不误报包完整性 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_source_change_routes_back_to_the_process_path` | 在仅既有论文 AAAA1111 的级别变化使预检允许刷新后，只新增 CCCC3333 的索引/分析文件/关联输入（facts sidecar 仍缺失），AAAA1111、BBBB2222 的级别和来源保持不变；旧预检执行刷新必须拒绝写入，输入包与正文原字节不变；重新预检走原 process |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_deleted_analysis_source_also_routes_back_to_process` | 独立接受基线只删除 CCCC3333 的分析文件与索引记录，不删论文事实目录项，不改其他论文级别，预检应走 process；另用独立临时教授目录在仅 level 变化预检通过后人工修改受管正文，旧预检刷新须拒绝写入，输入包与人工正文原字节不变 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_replaced_analysis_source_routes_back_to_process` | 分析文件换址（索引路径与旧文件同时变化）时走原 process |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only` | 旧包缺可比较业务基线走原 process |

### §1 预期与选择的覆盖关系

| §1 预期 | 覆盖方式 |
|---|---|
| T2 原始报告不改 | `assert_source_owner_handoff` 比较报告字节；`test_repeating_...` 断言重复登记不写通过结果 |
| T2 修复生成内容后普通 finalize 产生新正文、旧 PASS/失败不冒充 | T2 `test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job`：保留首份失败报告字节 → 修正题名和固定证据 → 正常 stage2-plan/finalize 生成不同正文 → 新校验登记之前旧失败不能放行 → 为新正文创建新的 PASS 报告并调用 stage2-record-validation → 确认第一轮 PASS、旧报告仍不变，预检不再提示 validator_not_accepted。仅验证本轮业务修复的恢复路径，不运行真实模型 |
| T4 等价重写仍不清轮数 | T3 用例断言 `round_retained`、`round == 1`、`phase == awaiting_second_validation` |
| T4 不重签旧 resolved proof | 本夹具无 resolved 方向、无 resolved proof，该项不适用于 T4 场景，按依据不设断言；展示刷新用例改为断言 `validator` 记录与 freshness 缓存不被重写 |
| T4 复用写前漂移/手改保护 | 来源新增用例：保存仅 level 变化预检 → 只让原本缺失的 CCCC3333 来源出现，保持已有论文级别和来源不变 → 用旧预检刷新，确认拒绝且 pack/正文原字节不变 → 新预检 process。来源删除用例：用独立基线只删除 CCCC3333 的分析文件及索引记录，其他输入不变，确认 process；同一个测试方法再创建全新独立临时教授目录，仅人工修改受管正文，确认旧预检刷新拒绝覆盖。既有 stale_render/changed_input_pack 选择器继续检查原登记与文字修订保护 |
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
status=$?
echo "exit=$status run_root=$RUN_ROOT"
exit "$status"
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
  3. 固定区阻挡的责任交接结果中，合并阅读 `reason_code`、`message`、`detail` 应能确认责任方（源／生成器／生成方／数据准备）及应做的动作（修复／修正／重新生成／处理／补齐等）；允许分在不同字段，不强制具体字段布局。结果不得误报 `no_failed_directions`、`awaiting_second_validation`。
  4. 展示刷新后重绘的正文与旧 validator 的 `render_sha256` 绑定不同，旧 PASS 在验证入口被拒绝（预检给出 `validator_not_accepted`）；包内不得出现 `pack_integrity_mismatch`，方向级 `action` 与 validator 的存储形式不作断言。
  5. 接受基线按来源 key 与类型记录路径、存在状态和成功/可用状态，使新增、删除、换址在预检可见；缺可信题名走明确失败结果（`status != ok` 且有 `reason_code`/`message`）。
  6. 固定区阻挡的 `stage2-refine-plan` 要返回明确的可处理交接结果：`jobs == []`、不要求写入（`write_needed` 不为 true），责任及动作可分列于返回字段，`status` 的具体字符串不作额外限制；`stage2-refine-finalize` 返回零 `rewritten` 且不改动 pack 与正文。
- 未改动范围：U2/U3/U4、Stage 3—5、安装与 Nix/APM、真实模型或教授流程均未纳入，也未借此要求全仓回归。

## 5. 复核与结果

本次确定性测试无自动重试。产品断言失败原样保留；先修产品再复验受影响项。命令/环境错误记无法判断，修正错误后只重试受影响命令，保留此前记录。未执行不得填 PASS；后续清理错误不得覆盖已确认失败。

记录格式保持简单：实际提交、T1—T4逐项通过/业务失败/无法判断/未执行、实际命令与输出位置、复用结果来源、剩余问题及负责人。原始日志和临时数据在仓库外，公开提交仅必要脱敏摘要。

准备期复核（非第三关正式执行）：产品提交 `305bc08f8b186672108cffbba0293d249bc8b4b2`（未实现状态），测试提交为 `36c630a`（`0d5606b` 加 t27 两处修正），命令为上面 §3 的 18 个选择器，结果目录 `/tmp/contact-evidence-level.kj3p7J2l`（`recipe.txt`），退出码 1，`Ran 18 tests`、`FAILED (failures=11)`。

- 通过 7 项：T3 四项（`NarrativeRoundBoundTests` 一项与三个既有保护选择器）、T2 两项（既有禁止区域选择器与 `test_forbidden_user_note_and_paper_table_keep_their_rejection`）、T4 一项（缺基线走 process）。
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
3. **IR-36(b) / IR-37**：t28 提到的模块运行补上结果目录 `/tmp/contact-evidence-level.aiT3QOLQ`（`module.txt`）与命令 `python3 -m unittest -v test_stage2_evidence_level`；该次运行用的是 t28 提交后、t29 清理前的文件（比定稿多一行），项数、通过数与失败分组不受影响。t29 定稿文件另跑一次：`/tmp/contact-evidence-level.jhhvqtu4`（`module.txt`），同样 `Ran 14 tests`、3 通过 / 11 业务失败。两次运行都没有执行到两条被修改的断言。

未新增用例名称、选择器、采集器或运行链；选择器仍 18，新增用例仍 14；产品代码与既有测试未改。该复核结论不代表第二关、第三关或合并批准。

### t30 定向修订记录（IR-37—IR-39 处置）

1. **IR-37**：t28/t29 记录里的模块运行改为写明版本——`/tmp/contact-evidence-level.aiT3QOLQ`（`module.txt`）用的是 t28 提交后、t29 清理前的文件；t29 定稿文件另跑一次为 `/tmp/contact-evidence-level.jhhvqtu4`（`module.txt`），两次都是 `Ran 14 tests`、3 通过 / 11 业务失败，均未执行到两条被修改的断言。
2. **IR-38**：§5 运行记录的提交指向改为 `36c630a`（`0d5606b` 加 t27 两处修正），不再用会随文档版本漂移的措辞。
3. **IR-39**：删除被新守卫蕴含、无法独立失败的 `baseline["candidate_paper_ids"]` 比较；候选引用「可独立失败」由渲染后的 `gap["candidate_paper_ids"]` 断言承担，渲染前的非空前提由 `render_fixture` 的守卫承担。

未新增用例名称、选择器、采集器或运行链；选择器仍 18，新增用例仍 14；产品代码与既有测试未改。该复核结论不代表第二关、第三关或合并批准。
