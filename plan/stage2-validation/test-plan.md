# Stage 2 划分第五批：校验报告与 refine 层（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 3 版（`Plan conclusion: APPROVED`）。
- 需求来源：负责人 2026-10-20 的 Stage 2 划分指示；原文与范围见执行计划。
- Target repository revision: 工作分支 `refactor-stage2-validation` 实施后的提交（代码提交 `76f107a`）；对照基准为 `e973ffb4571344157b3c43a151906a24f48c7e4e`（当前 `main`，已含第 1 批 #108）。实施开始时 `origin/main` 为 `0f89ebd`，实施中前进到 `e973ffb` 并重放；14 个函数在两次提交间 AST 相同。
- Test plan revision: 第 3 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要达到的目标与本次直接改变的行为。
- Proposed review status: 待复核（第 2 版第一/二关意见已处理，见修订记录）。
- 执行记录：[test-execution-2026-10-20.md](test-execution-2026-10-20.md)。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 对照基准与工作树身份有效，防止 A/B 空转 | 工作树 `scripts/contact_state.py` 与 `_stage2_validation.py`；基准为 `git archive e973ffb` 的 scripts 目录 | base 与 head 是两个不同文件；base 仍定义 14 个函数；head 一个都不定义 | 对比脚本的 `T0 ...` 行；3 条 `OK` |
| T1 | 14 个函数确实完成划分（R1） | 同上两侧源码与模块文件 | 新模块与 runner 同目录；14 个函数都不再出现在 runner 顶层，都出现在模块 `build()` 内 | 同一脚本的 `T1 ...` 行；29 条 `OK`（模块存在 1 + 14 函数×2） |
| T2 | 搬移没有改变任何函数逻辑（R2） | 同上两侧源码 | 14 个函数的代码 AST 与基准完全相同（脚本忽略 docstring 内容）；docstring 单独核对：9 个函数有 docstring（其中 4 个多行），清洗后与基准同文，5 个函数没有 docstring；runner 其余顶层定义（函数与类）AST 不变；离开 runner 的定义正好是这 14 个、没有新增；14 个函数都有 runner 别名（同一对象） | 同一脚本的 `T2 ...` 行（别名存在）17 条 `OK`；docstring 与别名身份用一次性只读脚本核对：9/9 docstring 同文（4 个多行、5 个无 docstring）、14/14 别名 `is` 模块函数 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 14 个名字在两侧都可调用；`inspect.signature` 字符串两侧相同；直接执行 `contact_state.py --help` 退出码 0 | 同一脚本的 `T3 ...` 行；29 条 `OK`（14 函数×2 + 1 直接执行）；合计 78 条 `OK`、末尾 `ALL CHECKS PASS` |
| T4 | 校验报告解析/渲染、record-validation、refine-plan/finalize 与 later-paper 状态保存/恢复的行为不变（R2） | 10 个既有方法：`test_stage2_style_validation_handoff.Stage2ValidationHandoffTests` 的 `test_stage2_second_blocking_round_is_terminal`、`test_stage2_report_for_stale_render_is_rejected_without_pack_write`、`test_stage2_nonrepairable_user_note_does_not_create_a_correction_job`、`test_stage2_refinement_rejects_changed_input_pack`、`test_repeated_quote_locations_and_ambiguous_report`、`test_business_rerender_and_bounded_correction_lifecycle`；`test_contact_state.TestRunnerBasics` 的 `test_11_stage2_validator_is_persisted_separately`、`test_11a_stage2_validator_pass_with_minor_is_accepted`、`test_13_stage2_validator_rewrite_round_trips_structured_narrative`；`test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_member_reference_persistence_and_refine_sources` | **条件式通过条件**：10 个方法执行后，若落在本批 14 个函数上的断言全部通过，则 T4 通过；若某方法失败，按 traceback 归因——失败在本批 14 个函数相关断言（报告行号解析、报告渲染与落盘、round/terminal/原因码、record-validation 写入、refine job 生成、later-paper 状态保存/恢复、pack 指纹拒绝）则 T4 失败；失败在跨批断言（第 1 批 preflight/plan、第 2/3 批 resolve、第 4 批 finalize/标题 helper、Stage 3 job）则记“无法判断／既有依赖失败”，不判本批失败（这些是测试体内或 setup 的跨批断言，不是本批目标） | 第 2 步命令；读取 10 个方法的执行结果与失败 traceback 并按上述归因 |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R4） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | **条件式通过条件**：复制布局包含 `_stage2_validation.py`，复制后的 runner 无导入/加载错误；两方法整体 `OK` 则 T5 通过。若失败，先看 traceback：导入/加载错误判本批失败；Stage 5 业务断言失败记既有失败或无法判断 | 第 3 步命令；查看复制目录与 traceback |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的分片套件（`shards` 4 片）与聚合 job `test` 由仓库工作流照常执行，结果按运行编号与 head 单独引用；本批不因此扩张或缩减必测清单，也不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-validation` 内进行；临时脚本与运行产物放仓库外 `/tmp` 目录。

1. 准备对照基准与脚本，运行 T0–T3（同一个命令块）：
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-validation
   git status --porcelain
   python3 --version
   uv run --no-project python3 --version
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
   `cp` 是必须的；来源缺失时先从执行记录点名的回退路径 `/tmp/pc-stage2-validation-TTc7wR/compare_stage2_batch.py`（同哈希 `75c151c3…`）取回，两处都缺失或哈希不一致时停止，不重建。脚本 91 行、sha256 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`，复制后核对同一哈希。**`RUN` 不导出；只在第 1 步内使用，第 2、3 步可独立执行**。
   预期：共 78 行 `OK`（T0 3、T1 29、T2 17、T3 29），末尾 `ALL CHECKS PASS`、退出码 0；`git archive`、`cp`、`shasum`、脚本均须退出 0。

2. T4：跑清单列出的 10 个方法，并按 T4 的条件式归因读取结果。
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
   预期：`Ran 10 tests`、全部 `ok`（全部断言通过，T4 通过）；若失败，按 T4 的归因规则记录；跳过项按未执行记录。

3. T5：跑清单列出的 2 个夹具方法，并查看复制目录与 traceback。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-validation/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
     test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
     -v
   ```
   预期：`Ran 2 tests`、全部 `ok`（T5 通过）；若失败，按 T5 的归因规则记录。

4. 既有仓库检查（不属于本批必测项，也不作为通过条件）：本批不在本地把全量套件列为必测步骤；推 PR 后引用 4 个 `shards (shardN)` 与聚合 job `test` 的运行编号与结论。

5. 失败注入：本批不适用。本批不修改事务／回滚、写入顺序或错误通道实现，业务必测清单里也没有失败注入项。

6. 记录：把命令、实际提交 SHA、逐项结果与必要输出片段写入 `/tmp` 运行目录，并把方法与结果写入 `test-execution-2026-10-20.md`；CI 结果按运行编号与所跑 head 单独记录。

7. 失败处理：
   - T0–T3 任一 `FAIL`：按标签定位到具体函数，判定为搬移缺陷，修正后重跑第 1 步；不得改脚本放宽判据。
   - T4／T5 按各自的归因规则处理；只有本批 14 个函数相关断言失败或复制/加载失败才判本批失败。
   - 既有跳过项按未执行记录；不做无新信息的重复运行。

## 环境与预检

- `python3 --version` 为 3.14.7（T4/T5 使用）；`uv run --no-project python3 --version` 为 3.14.6（第 1 步 A/B 使用）；执行记录同时记录两者。
- 使用仓库既有测试夹具，不新增依赖、不新增判定器或采集器；对比脚本只用标准库。
- `shasum -a 256` 是 macOS 写法；Linux 复跑改用 `sha256sum`，判据不变（脚本 91 行、哈希 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`）。
- 测试只使用合成数据与临时目录；不接触用户业务资料。
- 对照两侧都从 `e973ffb` 与工作树 HEAD 取出；`e973ffb` 已含第 1 批的 `_stage2_preflight.py` 与 pack 指纹别名。
- 第 4 批尚未合并时，`stage2_require_paper_reference_titles`、`stage2_trusted_paper_title`、`stage2_require_later_paper_titles` 仍在 runner 顶层，绑定点在其定义结束之后；两种合并顺序均成立。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 新模块单独的可导入性单测 | 属内部组织；T3 的直接执行与 T5 的复制加载路径已覆盖真实加载方式 |
| 第 1–4 批与第 6 批 | 本批不动，各批另立计划与测试清单 |
| 各函数内部逻辑的逐分支重测 | 本批是原样搬移；T2 的 AST 等价与既有测试已覆盖 |
| 性能／并发检查 | 本次改动不触及并发、事务或性能路径 |

## 自检

① 必测项只引用能证明本批目标的方法：T4 只限落在本批 14 个函数上的断言（跨批断言按归因记录），T5 只限复制/加载；② CI 不在必测清单；③ 对比脚本有来源、回退路径、复制命令与哈希；④ 命令块启用 `set -e`；`RUN` 只在第 1 步内使用；⑤ 失败注入标为“本批不适用”；⑥ 计划文字与执行记录使用同一套编号；⑦ 编号与版本一致（本文件第 3 版，执行记录引用第 3 版）。

## 修订记录

- 第 1 版：首次提交测试计划。
- 第 2 版：按第一轮审核修正 B1–B7 的判据文字。
- 第 3 版：按第二轮复核彻底重写判据与记录：T4/T5 改为条件式通过条件并写明失败归因与 traceback 区分；跨批批次归属改为“第 1 批 preflight/plan、第 2/3 批 resolve、第 4 批 finalize/标题 helper、Stage 3 job”；本批通过条件移出“later-paper 标题”，只保留状态保存/恢复；T2 的 docstring 判据改为“脚本忽略内容 + 单独核对 9 个 docstring（4 个多行）同文、5 个无 docstring”；环境记录两个 Python 版本；删除重复的修订记录/审核状态段；执行记录同步第 3 版。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（B1 T4 范围、B2 CI 记录、B3 版本、B4 docstring 判据、B5 脚本回退、B6 前置退出、B7 T5 范围）。
- 第 2 版：第一关/第二关 NEEDS_MODIFICATION（B2/B5/B6 闭合；B1/B3/B4/B7 与版本同步未闭合）。
- 第 3 版：待第二关复核。
