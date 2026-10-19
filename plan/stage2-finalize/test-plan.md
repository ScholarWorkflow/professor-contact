# Stage 2 划分第四批：finalize 层（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版（`Plan conclusion: APPROVED`）。
- 需求来源：负责人 2026-10-20 的 Stage 2 划分指示（“contact_state.py 应收敛为 CLI 分发与确有调用方依赖的兼容入口，每个 stage 主体逻辑拆为单独模块”）；原文与范围见执行计划。
- Target repository revision: 工作分支 `refactor-stage2-finalize` 实施后的提交；对照基准为 `origin/main` `e973ffb4571344157b3c43a151906a24f48c7e4e`（PR #108 合并后的 main）。分支最初从 `0f89ebd370a96cb1e138c6920d1300ed83fd23a3` 切出，PR #108 合并后 rebase 到 `e973ffb`；9 个函数的 AST 与 `d5a4f751fb80de4819d4a1de3ee829db52cea6fc` 相同，只有 Stage 5 与第 1 批改动造成的行号偏移。
- Test plan revision: 第 2 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要达到的目标与本次直接改变的行为。
- Proposed review status: 待审核（第 2 版；执行记录按本版命令产生，审核状态不代填）。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 对照基线有效（R1 的前提） | 用 `git archive e973ffb4571344157b3c43a151906a24f48c7e4e` 取出 `origin/main` 的 scripts 目录作为 base；工作树 scripts 目录作为 head | base 与 head 是两个不同目录；base 仍定义 9 个函数；head 一个都不再在顶层定义 | `/tmp` 对比脚本的 `T0 ...` 行，共 3 条；全部 `OK` |
| T1 | 9 个函数确实完成划分（R1） | base 与 head 的 `contact_state.py`、新模块 `_stage2_finalize.py` | 模块文件在与 runner 同目录；9 个函数离开 runner 顶层、进入模块 `build()` | 同一对比脚本的 `T1 ...` 行，共 19 条（模块存在 1 + 9 函数×2）；全部 `OK` |
| T2 | 搬移没有改变任何函数逻辑（R2） | 两侧源码与模块 `build()` 内的 9 个嵌套函数 | 9 个函数的代码 AST 与基准相同（docstring 不参与比较；多行 docstring 续行只允许增加缩进）；runner 其余顶层定义不变；离开 runner 的定义正好是这 9 个、没有新增；9 个别名都在 | 同一对比脚本的 `T2 ...` 行，共 12 条（9 函数 AST + 非搬移定义 + 定义集合差 + 别名）；全部 `OK` |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 9 个名字在两侧都可调用；`inspect.signature` 字符串两侧相同；直接执行 `contact_state.py --help` 退出码 0 | 同一对比脚本的 `T3 ...` 行，共 19 条（9 名字×2 + 直接执行 1）；全部 `OK`，末尾 `ALL CHECKS PASS` |
| T4 | `stage2-finalize` 命令、预检漂移、渲染状态与解析方向应用不变（R2） | 既有测试方法：`test_stage2_preflight.TestFinalizePreflightWiring.test_finalize_without_preflight_file_is_rejected_without_writing`、`...test_finalize_race_on_target_change_writes_nothing`、`...test_finalize_race_on_stage1_and_papers_changes_writes_nothing`、`...test_finalize_race_on_selection_change_writes_nothing`、`...test_finalize_preflight_file_must_match_professor`、`...test_finalize_preflight_file_must_be_a_preflight_payload`；`test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_applies_resolved_directions_to_pack`、`...test_finalize_stamps_resolved_subfield_on_unchanged_directions`、`...test_finalize_fails_closed_on_stale_resolved_file`；`test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_stage2_reuse_keeps_provisional_fingerprint_across_repeated_finalize` | 这 10 个方法全部通过；本批的通过条件只限这些方法自身的既有断言（缺少预检文件时拒绝且不写入、预检漂移时 `needs_refresh` 且不写入、预检 payload 校验、解析方向应用到 pack、`resolved_direction` 标记、过期 sidecar fail closed、重复 finalize 不破坏 provisional 指纹） | 第 2 步命令；`Ran 10 tests`、`OK`，无跳过项 |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R4、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两个方法通过；复制布局包含 `_stage2_finalize.py`，复制后的 runner 能按路径加载它 | 第 3 步命令；`Ran 2 tests`、`OK`，无跳过项 |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards (shardN)` 与聚合 job `test` 由仓库工作流照常执行，结果按运行编号与所跑 head 单独引用；本批不因此扩张或缩减必测清单，也不在本地把全量套件列为必测步骤。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-finalize` 内进行；临时脚本与运行产物放仓库外 `/tmp` 目录。

1. 准备对照基准与脚本，运行 T0–T3（**同一个命令块，`RUN` 在同一 shell 进程内**）：
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-finalize
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-stage2-finalize-XXXXXX)
   mkdir -p "$RUN/base"
   git archive e973ffb4571344157b3c43a151906a24f48c7e4e \
     .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
   cp /tmp/pc-stage2-tools/compare_stage2_batch.py "$RUN/compare_stage2_batch.py"
   shasum -a 256 "$RUN/compare_stage2_batch.py"
   uv run --no-project "$RUN/compare_stage2_batch.py" \
     "$RUN/base/.apm/skills/professor-contact/scripts" \
     .apm/skills/professor-contact/scripts \
     _stage2_finalize _stage2_finalize \
     stage2_preflight_plan_drift stage2_finalize_preflight_plan \
     stage2_pack_requires_membership_rebuild stage2_old_pack_gap_statuses \
     stage2_render_state stage2_require_paper_reference_titles \
     cmd_stage2_finalize stage2_trusted_paper_title \
     stage2_require_later_paper_titles
   ```
   `cp` 是必须的：脚本自带全部检查，不能在临时目录里凭提纲重写；来源缺失时停止并交计划所有人，不重建。脚本来源 `/tmp/pc-stage2-tools/compare_stage2_batch.py`，91 行，sha256 为 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`；复制后核对同一哈希。**`RUN` 不导出，后续步骤必须在同一 shell 进程内继续执行**。
   预期：每条检查打印一行 `OK  <标签>`，共 53 行——T0 3 行、T1 19 行、T2 12 行、T3 19 行；末尾 `ALL CHECKS PASS`，退出码 0。

2. T4：只跑清单列出的 10 个方法。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-finalize/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage2_preflight.TestFinalizePreflightWiring.test_finalize_without_preflight_file_is_rejected_without_writing \
     test_stage2_preflight.TestFinalizePreflightWiring.test_finalize_race_on_target_change_writes_nothing \
     test_stage2_preflight.TestFinalizePreflightWiring.test_finalize_race_on_stage1_and_papers_changes_writes_nothing \
     test_stage2_preflight.TestFinalizePreflightWiring.test_finalize_race_on_selection_change_writes_nothing \
     test_stage2_preflight.TestFinalizePreflightWiring.test_finalize_preflight_file_must_match_professor \
     test_stage2_preflight.TestFinalizePreflightWiring.test_finalize_preflight_file_must_be_a_preflight_payload \
     test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_applies_resolved_directions_to_pack \
     test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_stamps_resolved_subfield_on_unchanged_directions \
     test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_fails_closed_on_stale_resolved_file \
     test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_stage2_reuse_keeps_provisional_fingerprint_across_repeated_finalize \
     -v
   ```
   预期：`Ran 10 tests`、全部 `ok`，无 `FAIL`／`ERROR`；若出现跳过项，按未执行记录，不算通过。

3. T5：只跑清单列出的 2 个夹具方法。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-finalize/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
     test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
     -v
   ```
   预期：`Ran 2 tests`、全部 `ok`，无 `FAIL`／`ERROR`；若出现跳过项，按未执行记录，不算通过。

4. 既有仓库检查（不属于本批必测项，也不作为通过条件）：本批不在本地把全量套件列为必测步骤；改动推送到 PR 后，引用 PR 上 4 个 `shards (shardN)` 与聚合 job `test` 的运行编号与结论。若执行者自愿做一次本地 sanity check，必须在自建的临时目录内运行（`SANITY=$(mktemp -d /tmp/pc-stage2-finalize-sanity-XXXXXX)`），结果只作为记录，不改变本批结论。

5. 失败注入：本批不适用。本批不修改事务／回滚、写入顺序或错误通道实现，业务必测清单里也没有失败注入项。

6. 记录：把命令、实际提交 SHA、逐项结果与必要输出片段写入 `/tmp` 运行目录，并把方法与结果写入 `test-execution-<日期>.md`；CI 结果按运行编号与所跑 head 单独记录。

7. 失败处理：
   - T0–T3 任一 `FAIL`：按标签定位到具体函数或模块，判定为搬移缺陷，交实现负责人修正后重跑第 1 步；不得改脚本放宽判据。
   - T4／T5 方法失败：区分“本次改动引入的回归”“既有失败”“环境问题”；本次回归修正后重跑受影响编号。
   - 既有跳过项按未执行记录，不算失败；不做无新信息的重复运行。
   - 仓库 CI 失败时按合并规则处理，不并入本批必测结论。

## 环境与预检

- 使用仓库现有本地 Python（第 1 步记录 `python3 --version`）与既有测试夹具，不新增依赖、不新增判定器或采集器；对比脚本只用标准库。
- 测试只使用合成数据与临时目录；不接触用户业务资料。
- 预检只确认命令可用、工作树状态、基准 scripts 目录能取出；不预先执行业务目标命令求结果。
- 基准对照的两侧分别从 `e973ffb4571344157b3c43a151906a24f48c7e4e` 与工作树 HEAD 取出，避免用不同版本的兄弟模块比较。
- 第 1 步的 `shasum -a 256` 是 macOS 写法；若在 Linux 复跑，改用 `sha256sum`，判据不变（脚本 91 行、哈希 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`）。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 新模块单独的可导入性单测 | 属内部组织；T3 的直接执行与 T5 的两条复制加载路径已覆盖真实加载方式 |
| resolve 计划／提交、预检身份、校验报告与 refine、两个上下文类 | 本批不动，属第 1–3、5、6 批 |
| 各函数内部逻辑的逐分支重测 | 本批是原样搬移；T2 的 AST 等价与既有测试已覆盖 |
| 全仓逐模块回归以外的性能／并发检查 | 本次改动不触及并发、事务或性能路径 |

## 自检

提交审核前逐条核对（与共用清单 `plan/test-plan-checklist.md` 同一口径）：① 必测项只引用能证明本批目标的方法，T4／T5 的通过条件只限列明的方法自身断言；② CI 不在必测清单；③ 对比脚本有确切来源、复制命令与哈希；④ 命令块启用 `set -e` 且 `RUN` 在同一 shell 进程内使用；⑤ 失败注入标为“本批不适用”并说明原因；⑥ 计划文字与执行记录使用同一套编号；⑦ 编号与版本一致。

## 修订记录

- 第 1 版：首次提交测试计划（对照基线 `0f89ebd`）。
- 第 2 版：PR #108（第 1 批）合并后 rebase 到 `origin/main` `e973ffb`，对照基准、命令与目标 revision 同步；T4/T5 按 rebase 后重跑，判据不变。

## 审核状态

- 第 1 版：待审核；执行记录按该版在 `0f89ebd` 基线上跑过 T4/T5，结果保留在记录中。
- 第 2 版：待审核；rebase 到 `e973ffb` 后按本版重跑 T0–T5，审核结论不预填。
