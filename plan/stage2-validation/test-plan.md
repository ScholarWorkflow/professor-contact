# Stage 2 划分第五批：校验报告与 refine 层（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 3 版（`Plan conclusion: APPROVED`）。
- 需求来源：负责人 2026-10-20 的 Stage 2 划分指示；原文与范围见执行计划。
- Target repository revision: 工作分支 `refactor-stage2-validation` 实施后的提交（代码提交 `76f107a17a6e343a0e6aa28b504024d596639647`）；对照基准为 `e973ffb4571344157b3c43a151906a24f48c7e4e`（当前 `main`，PR #108 合入第 1 批后）。实施开始时 `origin/main` 为 `0f89ebd`，实施中 main 前进到 `e973ffb`，本批已重放到新基准；本批 14 个函数在 `0f89ebd..e973ffb` 之间 AST 相同，A/B 与定向测试在重放后重跑。
- Test plan revision: 第 1 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要达到的目标与本次直接改变的行为。
- Proposed review status: 待审核（随本批 PR 提交；执行记录见 [test-execution-2026-10-20.md](test-execution-2026-10-20.md)）。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 对照基准与工作树身份有效，防止 A/B 空转 | 工作树 `scripts/contact_state.py` 与 `_stage2_validation.py`；对照基准为 `git archive e973ffb` 取出的 scripts 目录 | base 与 head 是两个不同文件；base 仍定义 14 个函数；head 一个都不定义 | `/tmp` 对比脚本的 `T0 ...` 行；3 条 `OK` |
| T1 | 14 个函数确实完成划分（R1） | 同上两侧源码与模块文件 | 新模块与 runner 同目录；14 个函数都不再出现在 runner 顶层，都出现在模块 `build()` 内 | 同一对比脚本的 `T1 ...` 行；29 条 `OK`（模块存在 1 + 14 函数×2） |
| T2 | 搬移没有改变任何函数逻辑（R2） | 同上两侧源码 | 14 个函数的代码 AST 与基准完全相同（多行 docstring 续行允许且只允许增加 4 个空格缩进）；runner 其余顶层定义（函数与类）AST 不变；离开 runner 的定义正好是这 14 个、没有新增；14 个函数都有 runner 别名 | 同一对比脚本的 `T2 ...` 行；17 条 `OK`（14 函数 AST + 非搬移定义不变 + 定义集合差 + 别名齐全） |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 14 个名字在两侧都可调用；`inspect.signature` 字符串两侧相同；直接执行 `contact_state.py --help` 退出码 0 | 同一对比脚本的 `T3 ...` 行；29 条 `OK`（14 函数×2 + 1 直接执行）；合计 78 条 `OK`、末尾 `ALL CHECKS PASS` |
| T4 | 校验报告解析/渲染、record-validation、refine-plan/finalize 与 later-paper 渲染/恢复的行为不变（R2） | 既有测试方法：`test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_second_blocking_round_is_terminal`（两轮终止、refine-plan/finalize、later-paper 标题保留）；`...test_stage2_report_for_stale_render_is_rejected_without_pack_write`（旧渲染报告被拒且不写 pack）；`...test_stage2_nonrepairable_user_note_does_not_create_a_correction_job`（不可修问题不生成修正 job）；`...test_stage2_refinement_rejects_changed_input_pack`（pack 变化拒绝 refine）；`...test_repeated_quote_locations_and_ambiguous_report`（三种行号写法解析、歧义报告拒绝、逐行 issue 进入 refine）；`...test_business_rerender_and_bounded_correction_lifecycle`（两轮上限、`validation_correction_required`/`validation_rounds_exhausted` 原因码、refine-plan/finalize、later reference）；`test_contact_state.TestRunnerBasics.test_11_stage2_validator_is_persisted_separately`（record-validation 写入、非法报告拒绝、refine 无 job）；`...test_11a_stage2_validator_pass_with_minor_is_accepted`（minor issue 原样保存）；`...test_13_stage2_validator_rewrite_round_trips_structured_narrative`（record→refine-plan→refine-finalize→第二轮 record 的完整往返）；`test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_member_reference_persistence_and_refine_sources`（facts 与 pack 两个 refine 入口、P 引用可信标题、later-paper 状态保留、事实变化拒绝） | 这 10 个方法全部通过；本批的通过条件只限这些方法自身的既有断言（报告行号解析、报告渲染与落盘、round/terminal/原因码、refine job 生成、later-paper 标题与状态、pack 指纹拒绝）。这些方法的 setup 会调用未搬移的 stage2 plan/finalize 与夹具，属既有测试依赖，不作为本批通过条件 | 第 2 步命令；`Ran 10 tests`、`OK`，无 `FAIL`／`ERROR` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R4） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两个方法通过；复制布局包含 `_stage2_validation.py`，复制后的 runner 能按路径加载它 | 第 3 步命令；`Ran 2 tests`、`OK`，无 `FAIL`／`ERROR` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的分片套件（`shards` 的 4 个分片）与聚合 job `test` 由仓库工作流照常执行，其结果单独引用；本批不因此扩张或缩减必测清单，也不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-validation` 内进行；临时脚本与运行产物放仓库外 `/tmp` 目录。

1. 准备对照基准与脚本，运行 T0–T3（**同一个命令块，`RUN` 在同一 shell 进程内**）：
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-validation
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-stage2-validation-XXXXXX)
   mkdir -p "$RUN/base"
   git archive e973ffb4571344157b3c43a151906a24f48c7e4e \
     .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
   cp /tmp/pc-stage2-tools/compare_stage2_batch.py "$RUN/compare_stage2_batch.py"
   shasum -a 256 "$RUN/compare_stage2_batch.py"
   uv run --no-project "$RUN/compare_stage2_batch.py" \
     "$RUN/base/.apm/skills/professor-contact/scripts" \
     .apm/skills/professor-contact/scripts \
     _stage2_validation _stage2_validation \
     stage2_pack_scope stage2_bound_render stage2_merge_later_paper_source \
     stage2_rendered_later_papers stage2_restore_pack_later_papers \
     stage2_parse_report_location stage2_validation_report \
     stage2_require_recorded_validation stage2_pack_matches_facts \
     stage2_validation_material stage2_refine_context cmd_stage2_refine_plan \
     cmd_stage2_refine_finalize cmd_stage2_record_validation
   ```
   `cp` 是必须的：脚本自带全部检查，不能在临时目录里凭提纲重写；来源缺失时停止并交计划所有人，不重建。脚本参考 sha256 为 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`（91 行），复制后核对同一哈希。**`RUN` 不导出，后续步骤必须在同一 shell 进程内继续执行**。
   预期：每条检查打印一行 `OK  <标签>`，共 78 行——T0 3 行、T1 29 行、T2 17 行、T3 29 行；末尾 `ALL CHECKS PASS`，退出码 0。

2. T4：只跑清单列出的 10 个方法。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-validation/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_second_blocking_round_is_terminal \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_report_for_stale_render_is_rejected_without_pack_write \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_refinement_rejects_changed_input_pack \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_repeated_quote_locations_and_ambiguous_report \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle \
     test_contact_state.TestRunnerBasics.test_11_stage2_validator_is_persisted_separately \
     test_contact_state.TestRunnerBasics.test_11a_stage2_validator_pass_with_minor_is_accepted \
     test_contact_state.TestRunnerBasics.test_13_stage2_validator_rewrite_round_trips_structured_narrative \
     test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_member_reference_persistence_and_refine_sources \
     -v
   ```
   预期：`Ran 10 tests`、全部 `ok`，无 `FAIL`／`ERROR`；若出现跳过项，按未执行记录，不算通过。

3. T5：只跑清单列出的 2 个夹具方法。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-validation/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
     test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
     -v
   ```
   预期：`Ran 2 tests`、全部 `ok`，无 `FAIL`／`ERROR`；若出现跳过项，按未执行记录，不算通过。

4. 既有仓库检查（不属于本批必测项，也不作为通过条件）：本批不在本地把全量套件列为必测步骤；改动推送到 PR 后，引用 PR 上 4 个 `shards (shardN)` 与聚合 job `test` 的运行编号与结论。若执行者自愿做一次本地 sanity check，必须在自建的临时目录内运行（`SANITY=$(mktemp -d /tmp/pc-stage2-sanity-XXXXXX)`），结果只作为记录，不改变本批结论。

5. 失败注入：本批不适用。本批不修改事务／回滚、写入顺序或错误通道实现，业务必测清单里也没有失败注入项。

6. 记录：把命令、实际提交 SHA、逐项结果与必要输出片段写入 `/tmp` 运行目录，并把方法与结果写入 `test-execution-2026-10-20.md`；CI 结果按运行编号与所跑 head 单独记录。

7. 失败处理：
   - T0–T3 任一 `FAIL`：按标签定位到具体函数，判定为搬移缺陷，交实现负责人修正后重跑第 1 步；不得改脚本放宽判据。
   - T4／T5 方法失败：区分“本次改动引入的回归”“既有失败”“环境问题”；本次回归修正后重跑受影响编号。
   - 既有跳过项按未执行记录，不算失败；不做无新信息的重复运行。
   - 仓库 CI 失败时按合并规则处理，不并入本批必测结论。

## 环境与预检

- 使用仓库现有本地 Python（`python3 --version` 记录为 3.14.7）与既有测试夹具，不新增依赖、不新增判定器或采集器；对比脚本只用标准库。
- 第 1 步的 `shasum -a 256` 是 macOS 写法；若在 Linux 复跑，改用 `sha256sum`，判据不变（脚本 91 行、哈希 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`）。
- 测试只使用合成数据与临时目录；不接触用户业务资料。
- 预检只确认命令可用、工作树状态、基准 scripts 目录能取出；不预先执行业务目标命令求结果。
- 对照两侧都从 `e973ffb` 与工作树 HEAD 取出，避免用不同版本的兄弟模块比较。`e973ffb` 已包含第 1 批的 `_stage2_preflight.py` 与两个 pack 指纹别名；本批通过 runner 别名注入它们，不重复搬移。
- 第 4 批尚未合并时，`stage2_require_paper_reference_titles`、`stage2_trusted_paper_title`、`stage2_require_later_paper_titles` 仍在 runner 顶层，绑定点在 `stage2_require_later_paper_titles` 结束之后，两种合并顺序都不影响本清单。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 新模块单独的可导入性单测 | 属内部组织；T3 的直接执行与 T5 的两条复制加载路径已覆盖真实加载方式 |
| 第 1–4 批与第 6 批（preflight、resolve、finalize、上下文类） | 本批不动，各批另立计划与测试清单 |
| 各函数内部逻辑的逐分支重测 | 本批是原样搬移；T2 的 AST 等价与既有测试已覆盖，不重复枚举 |
| 全仓逐模块回归以外的性能／并发检查 | 本次改动不触及并发、事务或性能路径 |

## 自检

提交审核前逐条核对（与共用清单 `plan/test-plan-checklist.md` 同一口径）：① 必测项只引用能证明本批目标的方法，T4／T5 的通过条件只限列明的方法自身断言；② CI 不在必测清单；③ 对比脚本有确切来源、复制命令与哈希；④ 命令块启用 `set -e` 且 `RUN` 在同一 shell 进程内使用；⑤ 失败注入标为“本批不适用”并说明原因；⑥ 计划文字与执行记录使用同一套编号；⑦ 编号与版本一致。

## 修订记录

- 第 1 版：首次提交测试计划。按 `e973ffb` 基准写 A/B 计数（78 条 `OK`）、10 个 T4 方法与 2 个 T5 方法；记录实施中 main 从 `0f89ebd` 前进到 `e973ffb` 并重放。

## 审核状态

- 测试计划：待审核（第 1 版）。
- 测试执行：已按本计划完成，结果见 [test-execution-2026-10-20.md](test-execution-2026-10-20.md)。
