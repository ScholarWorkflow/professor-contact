# Stage 2 固定证据与分析级别测试计划

- Test revision：contact-evidence-level-t7；对应 [执行计划 r4](implementation-plan.md)。
- Requirement revision：2026-10-17 用户授权的 U1/U5 修复；测试资产准备基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`。
- 状态：第一关 PASS（t6 复核记录）；T1—T4 的测试代码与完整命令已落实到本文件 §3，准备期复核在未实现的产品上得到 4 通过 / 9 业务失败（§5），第二关待独立复核，第三关未执行。这里不宣称任何业务修复完成或测试通过。
- [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 决定范围；附录/步骤不追加清单外检查。

## 1. 唯一必测清单

| 项 | 目标与输入 | 预期结果 | 足够的检查入口 |
|---|---|---|---|
| T1 | 同一既有夹具覆盖固定卡 evidence/completed_part/remaining_gap 及禁锚区 evidence 中已知编号，可信标题/链接已在当前材料；另一个缺可信题名的引用 | 正式 finalize 输出题名/链接，上述机器字段/候选编号与事实不变，其他说明原意、作者 quote/translation、用户笔记不变；缺题名明确失败且不生成伪引用 | 既有 runner CLI 测试夹具，检查 Markdown 与 pack 必要字段 |
| T2 | 当前受管正文上的固定区 blocking 与混合固定/叙事 blocking 原始报告；复用现有用户笔记/论文一览禁止区域报告 | 合法固定区第一轮失败确实登记；禁止区域报告继续拒绝且无 correction jobs；原始报告不改、非通过；refine-plan 无 jobs、明确交源/生成器处理，refine-finalize 不写；同内容重试不能清轮数。修复正式生成内容后普通 finalize 产生新正文，旧 PASS/失败不冒充新结果 | 既有 Stage2ValidationHandoffTests 的报告/正文夹具和 record/refine/finalize CLI |
| T3 | 纯 narrative 第一次失败→现有合法修订→第二次仍失败（可用第二轮新固定卡阻挡覆盖其归属）；及已绑定报告对应的正文/pack被改 | 纯文字修订仍可完成且第二次终态不继续第三轮；不允许用过期报告改事实或覆盖手改文件 | 复用该模块已有 second_blocking_round_is_terminal、stale_render、changed_input_pack 对应测试；只调整受新登记分类影响的断言 |
| T4 | 复用同一方向的 fulltext、abstract（有分析文件）、未确认（有 PDF，索引分析状态失败但残留旧 fulltext 级别）及 OCR-only fulltext/facts unavailable 夹具，并将 §2 已有缺 analysis_level 兼容样例归入本项（有分析文件/PDF 仍为未确认，不复制样例）；有完整接受基线且 /tmp facts 已不存在，原正文已有有效绑定 validator PASS，仅 level/render 变更由正式 preflight→展示刷新，同一场景复用 T1 已知引用及正式 pack 中可信题名/链接；在同一来源夹具中依次作新增、删除、替换分析依据（含原缺 facts 路径出现），并保留旧缺基线情形 | 三类计数/规范包一致，失败记录即使残留 fulltext、旧记录缺 analysis_level 即使有分析文件/PDF，均归未确认；同一 pack-only 刷新输出的固定卡 evidence/completed_part/remaining_gap 与禁锚区 evidence 均显示可信题名/链接，原始机器字段及候选编号不变；纯展示刷新使正文实质变化后，旧 validator PASS 不再被接受，不运行模型校验；等价重写仍不清轮数。纯展示后再预检不因过期包完整性摘要误 process，保留 assignment/模型指纹、不重签 proof、不额外生成分析/归属/时效任务；新增/删除/替换、无法比较的旧基线走原 process，不能误当 display-only；复用已有写前漂移/手改保护检查，不写不确定结果 | 既有 BaseEnv/preflight/pack-only 渲染及 guard 夹具，检查分流原因、pack/Markdown及任务记录；只覆盖这些直接反例，不交叉穷举，不跑真实模型 |

T1—T4 是上限。无需真实 Zotero、下载/PDF分析重跑、Nix/APM重装、全教授流程或完整测试模块回归；本次未改安装和模型业务。报告中“四位教授”与“10+1”是缺陷背景，不能强制采集私人材料或追加四次模型验收。

## 2. 测试资产与选择器对照

测试代码全部放在 `.apm/skills/professor-contact/tests/test_stage2_evidence_level.py`，只复用 `test_contact_state.py` 的 `BaseEnv`、`run_cli`、`run_bound_stage2_plan`、`run_bound_stage2_finalize`、`stage2_style_validation_report` 和既有合成夹具，不新建判定框架、不改产品代码、不改写既有用例。

| 项 | 选择器 | 该用例断言的计划行为 |
|---|---|---|
| T1 | `test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_renders_trusted_references_without_touching_machine_fields` | 固定卡 evidence/completed_part/remaining_gap 与禁锚区 evidence 显示可信题名/链接；pack 机器字段、候选编号、quote、用户笔记逐字不变 |
| T1 | `test_stage2_evidence_level.FixedEvidenceDisplayTests.test_fixed_evidence_without_trusted_title_fails_instead_of_inventing_one` | 缺可信题名时受影响生成明确失败，不写伪引用 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job` | 固定区 blocking 第一轮登记为 needs_correction，refine-plan 零 jobs 并交源/生成器，refine-finalize 不写 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_mixed_fixed_and_narrative_blocking_creates_no_rewrite_job` | 混合固定/叙事 blocking 同样零 rewrite jobs，不把固定区交给模型 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_repeating_the_same_fixed_card_report_does_not_clear_the_round` | 同内容重试不能清轮数，也不写入通过结果 |
| T2 | `test_stage2_evidence_level.FixedEvidenceFailureTests.test_forbidden_user_note_and_paper_table_keep_their_rejection` | 用户笔记、论文一览仍被拒绝，无 correction jobs，正文与 pack 不变 |
| T3 | `test_stage2_evidence_level.NarrativeRoundBoundTests.test_narrative_correction_rounds_stay_bound_and_terminal_state_is_recorded_once` | 纯叙事第一轮→合法修订→第二轮固定卡阻挡登记为 fail_after_2_rounds，不继续第三轮、不再发修订 |
| T3 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job` | 既有禁止区域报告拒绝与零修订任务断言继续成立 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_counts_follow_the_recorded_analysis_level` | 全文/摘要/未确认三类计数与规范包级别一致，不从文件存在推断 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_legacy_records_without_level_count_as_unconfirmed` | 缺 analysis_level 的旧记录即使有分析文件也计未确认 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_display_only_level_change_refreshes_without_model_work` | 仅 level 变化由 preflight 判为展示刷新，刷新后统计更新、旧 PASS 不再被接受、下次预检不误报包完整性 |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_source_change_routes_back_to_the_process_path` | 新增分析依据走原 process，不被当作 display-only |
| T4 | `test_stage2_evidence_level.AnalysisLevelTests.test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only` | 旧包缺可比较业务基线走原 process |

## 3. 可执行 recipe

- 执行目录：`<producer checkout>/.apm/skills/professor-contact/tests`（选择器按模块名解析，必须在 tests 目录内运行）。
- Python：仓库现有 `python3`；本次准备基线 Python 3.14.7。
- 输出目录：新建 `/tmp/contact-evidence-level.XXXXXXXX`；日志、退出码和临时数据只放该目录，不入库、不推送。
- 命令（一次运行覆盖 T1—T4 与 T2 既有选择器）：

```bash
mkdir -p <run-root>
cd <producer checkout>/.apm/skills/professor-contact/tests
python3 -m unittest -v \
  test_stage2_evidence_level.FixedEvidenceDisplayTests \
  test_stage2_evidence_level.FixedEvidenceFailureTests \
  test_stage2_evidence_level.NarrativeRoundBoundTests \
  test_stage2_evidence_level.AnalysisLevelTests \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job \
  > <run-root>/recipe.txt 2>&1
echo "exit=$?"
```

- 也可按项复跑：把类名单独替换为该项选择器；`-v` 输出逐用例结果。分项结果由这些断言判定，没有额外 JSON oracle。
- 准备顺序：`git status` 确认 checkout 干净 → 进入 tests 目录 → 建 run 目录 → 运行上面命令。没有安装、外部服务、模型或 Zotero 需求；`BaseEnv` 的临时目录已提供隔离。
- 失败处理：产品断言失败原样保留；命令或环境错误记无法判断并只重试受影响命令；未执行不得填 PASS；已确认失败不得被后续清理覆盖。

## 4. 准备记录与接口交接

- 已准备：新建 `test_stage2_evidence_level.py`（T1—T4 共 12 个新增用例）与 T2 既有选择器组成上述 recipe；未改动产品、既有测试和共享夹具，未操作用户教授目录。
- 接口假设（实现方需对齐，不一致时由测试计划工程师按执行计划调整，不改名迁就）：仅展示刷新入口取 `stage2-refresh-display --professor-dir <dir> --preflight-file <file>`，输出 `status`、`display_refreshed`、`pack_path`、`md_sha256`；preflight 对仅 level 变化返回 `action=refresh_display` 及同值的方向级 `action`，无法比较或来源变化时仍返回 `process` 和具体 `reason_codes`；缺可信题名走明确失败结果（`status != ok` 且有 `reason_code`/`message`）。
- 未改动范围：U2/U3/U4、Stage 3—5、安装与 Nix/APM、真实模型或教授流程均未纳入，也未借此要求全仓回归。

## 5. 复核与结果

本次确定性测试无自动重试。产品断言失败原样保留；先修产品再复验受影响项。命令/环境错误记无法判断，修正错误后只重试受影响命令，保留此前记录。未执行不得填 PASS；后续清理错误不得覆盖已确认失败。

记录格式保持简单：实际提交、T1—T4逐项通过/业务失败/无法判断/未执行、实际命令与输出位置、复用结果来源、剩余问题及负责人。原始日志和临时数据在仓库外，公开提交仅必要脱敏摘要。

准备期复核（本地测试工程师，非第三关正式执行）：产品提交 `305bc08f8b186672108cffbba0293d249bc8b4b2`（未实现状态）、测试提交 f910dbd，命令为上面 §3 的命令，日志 `/tmp/contact-evidence-level.pc92prep/recipe.txt`，退出码 1，`Ran 13 tests`、`FAILED (failures=9)`。通过 4 项：T3 的 `NarrativeRoundBoundTests.test_narrative_correction_rounds_stay_bound_and_terminal_state_is_recorded_once`、T2 的 `test_forbidden_user_note_and_paper_table_keep_their_rejection`、T4 的 `test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only`。业务失败 9 项，全部属于待实现的 T1/T2/T4 目标行为：T1 两项、T2 三项、T4 四项。该记录只用于确认选择器可执行、判定 T3 结论和暴露产品缺口，不替代第三关正式执行，也不作为任何通过结论。

修订边界：t7 落实测试代码与完整选择器，不改变 t6 已批准的 T1—T4 范围与预期结果。执行计划 r4 已获[正式批准](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6228535516)，本次不重开其未受影响关口。

交接：T1/T2/T4 的 9 项业务失败交产品实现负责人修复，实现落地后由本地测试工程师同步受影响选择器并做第二关复核材料，再由本地执行工程师按第三关正式执行；T3 与既有禁止区域结论在当前产品版本已成立，无需重跑。
