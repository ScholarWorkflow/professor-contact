# Stage 2 划分第二批：resolve 计划层（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版（`Plan conclusion: APPROVED`）。
- 需求来源：负责人 2026-10-20 的两条指示（Stage 2 划分；“contact_state.py 收敛为 CLI 分发与兼容入口”）；原文与范围见执行计划。
- Target repository revision: 工作分支 `refactor-stage2-resolve`（从当前 `main` `d5a4f751fb80de4819d4a1de3ee829db52cea6fc` 拉出）实施后的提交；对照基准同为 `d5a4f75`。
- Test plan revision: 第 1 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要达到的目标与本次直接改变的行为。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | 16 个函数与 7 个常量确实完成划分（R1） | 工作树 `scripts/contact_state.py`、新模块 `scripts/_stage2_resolve.py`；对照基准为当前 `main`（`git archive` 取出的 scripts 目录） | `T0`：base 与 head 是两个不同目录、base 仍定义 16 个函数、head 一个都不定义；16 个函数离开 runner 顶层、进入模块 `build()`；7 个常量改由模块定义、runner 只别名 | `/tmp` 对比脚本的 `T0 ...` 与 `T1 ...` 行；全部 `OK`，末尾 `ALL CHECKS PASS` |
| T2 | 搬移没有改变任何函数逻辑或常量（R2） | 同上两侧源码 | 16 个函数的代码 AST 与基准完全相同（多行 docstring 续行允许且只允许增加 4 个空格缩进）；7 个常量的源代码与基准相同（忽略行尾空白）；runner 其余顶层定义 AST 不变，且离开 runner 的定义正好是这 16 个、没有新增 | 同一对比脚本的 `T2 ...` 行；全部 `OK` |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 16 个名字在两侧都可调用；`inspect.signature` 字符串两侧相同；7 个常量值两侧相同；直接执行 `contact_state.py --help` 退出码 0 | 同一对比脚本的 `T3 ...` 行；全部 `OK` |
| T4 | 候选识别、resolve 证据与 `stage2-resolve-plan` 行为不变（R2） | 既有测试方法：`test_stage2_resolved_direction.ResolvedDirectionPlanTests.test_resolve_plan_emits_jobs_for_each_direction`、`...test_resolve_plan_detects_removal_candidates`、`...test_resolve_plan_no_changes_when_all_match`；`test_stage2_resolved_direction.MergeCandidateDetectionTests.test_detect_merge_candidates`；`test_stage2_resolved_direction.CandidateUnionEvidenceTests.test_fingerprint_sensitive_to_candidate_outside_relevant_set`；`test_stage2_resolved_direction.ResolvedReuseTests.test_resolve_plan_reuses_unchanged_directions`、`...test_resolve_plan_reprocesses_when_facts_change`；`test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_addition_candidate_targets_strongest_non_provisional_direction`、`...test_merge_candidate_requires_at_least_two_shared_papers`、`...test_reused_direction_ignores_stale_result_file` | 这 10 个方法全部通过；本批的通过条件只限这些方法自身的既有断言（job 生成与字段、增/删/拆/并候选识别、merge 阈值、证据并集与指纹、复用与 facts 变化后的重算、运行隔离） | 第 2 步命令；`Ran 10 tests`、`OK` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R4） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两个方法通过；复制布局包含 `_stage2_resolve.py`，复制后的 runner 能按路径加载它 | 第 3 步命令；`Ran 2 tests`、`OK` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的分片套件（`shards` 的 4 个分片）与聚合 job `test` 由仓库工作流照常执行，其结果单独引用；本批不因此扩张或缩减必测清单，也不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve` 内进行；临时脚本与运行产物放仓库外 `/tmp` 目录。

1. 准备对照基准与脚本，运行 T0–T3（**同一个命令块，`RUN` 在同一 shell 进程内**）：
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-stage2-resolve-XXXXXX)
   mkdir -p "$RUN/base"
   git archive d5a4f751fb80de4819d4a1de3ee829db52cea6fc \
     .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
   cp /tmp/pc-stage2-r2/compare_stage2_resolve.py "$RUN/compare_stage2_resolve.py"
   shasum -a 256 "$RUN/compare_stage2_resolve.py"
   uv run --no-project "$RUN/compare_stage2_resolve.py" \
     "$RUN/base/.apm/skills/professor-contact/scripts" \
     .apm/skills/professor-contact/scripts
   ```
   `cp` 是必须的：脚本自带全部检查，不能在临时目录里凭提纲重写；来源缺失时停止并交计划所有人，不重建。脚本参考 sha256 为 `52a7c4be7aa005593e9db122e47a5477e70759ea963691930da8b2933302c80f`（196 行），复制后核对同一哈希。**`RUN` 不导出，后续步骤必须在同一 shell 进程内继续执行**。
   预期：每条检查打印一行 `OK  <标签>`，共 131 行——T0 3 行、T1 47 行（模块存在 1 + 16 函数×2 + 7 常量×2）、T2 41 行（16 函数×2 + 7 常量 + 非搬移定义不变 + 定义集合差）、T3 40 行（16 函数×2 + 7 常量 + 1 直接执行）；末尾 `ALL CHECKS PASS`，退出码 0。

2. T4：只跑清单列出的 10 个方法。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage2_resolved_direction.ResolvedDirectionPlanTests.test_resolve_plan_emits_jobs_for_each_direction \
     test_stage2_resolved_direction.ResolvedDirectionPlanTests.test_resolve_plan_detects_removal_candidates \
     test_stage2_resolved_direction.ResolvedDirectionPlanTests.test_resolve_plan_no_changes_when_all_match \
     test_stage2_resolved_direction.MergeCandidateDetectionTests.test_detect_merge_candidates \
     test_stage2_resolved_direction.CandidateUnionEvidenceTests.test_fingerprint_sensitive_to_candidate_outside_relevant_set \
     test_stage2_resolved_direction.ResolvedReuseTests.test_resolve_plan_reuses_unchanged_directions \
     test_stage2_resolved_direction.ResolvedReuseTests.test_resolve_plan_reprocesses_when_facts_change \
     test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_addition_candidate_targets_strongest_non_provisional_direction \
     test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_merge_candidate_requires_at_least_two_shared_papers \
     test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_reused_direction_ignores_stale_result_file \
     -v
   ```
   预期：`Ran 10 tests`、全部 `ok`，无 `FAIL`／`ERROR`；若出现跳过项，按未执行记录，不算通过。

3. T5：只跑清单列出的 2 个夹具方法。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
     test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
     -v
   ```
   预期：`Ran 2 tests`、全部 `ok`，无 `FAIL`／`ERROR`；若出现跳过项，按未执行记录，不算通过。

4. 既有仓库检查（不属于本批必测项，也不作为通过条件）：本批不在本地把全量套件列为必测步骤；改动推送到 PR 后，引用 PR 上 4 个 `shards (shardN)` 与聚合 job `test` 的运行编号与结论。若执行者自愿做一次本地 sanity check，必须在自建的临时目录内运行（`SANITY=$(mktemp -d /tmp/pc-stage2-sanity-XXXXXX)`），结果只作为记录，不改变本批结论。

5. 失败注入：本批不适用。本批不修改事务／回滚、写入顺序或错误通道实现，业务必测清单里也没有失败注入项。

6. 记录：把命令、实际提交 SHA、逐项结果与必要输出片段写入 `/tmp` 运行目录，并把方法与结果写入 `test-execution-<日期>.md`；CI 结果按运行编号与所跑 head 单独记录。

7. 失败处理：
   - T0–T3 任一 `FAIL`：按标签定位到具体函数／常量，判定为搬移缺陷，交实现负责人修正后重跑第 1 步；不得改脚本放宽判据。
   - T4／T5 方法失败：区分“本次改动引入的回归”“既有失败”“环境问题”；本次回归修正后重跑受影响编号。
   - 既有跳过项按未执行记录，不算失败；不做无新信息的重复运行。
   - 仓库 CI 失败时按合并规则处理，不并入本批必测结论。

## 环境与预检

- 使用仓库现有本地 Python（第 1 步记录 `python3 --version`）与既有测试夹具，不新增依赖、不新增判定器或采集器；对比脚本只用标准库。
- 测试只使用合成数据与临时目录；不接触用户业务资料。
- 预检只确认命令可用、工作树状态、基准 scripts 目录能取出；不预先执行业务目标命令求结果。
- 基准对照的两侧都从同一 `d5a4f75` 与工作树 HEAD 取出，避免用不同版本的兄弟模块比较。
- 第 1 步的 `shasum -a 256` 是 macOS 写法；若在 Linux 复跑，改用 `sha256sum`，判据不变（脚本 196 行、哈希 `52a7c4be7aa005593e9db122e47a5477e70759ea963691930da8b2933302c80f`）。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 新模块单独的可导入性单测 | 属内部组织；T3 的直接执行与 T5 的两条复制加载路径已覆盖真实加载方式 |
| resolve 提交侧（`validate_resolve_results`、finalize/accept）与 finalize/校验/refine | 本批不动，属第 3–5 批 |
| 各函数内部逻辑的逐分支重测 | 本批是原样搬移；T2 的 AST 等价与既有测试已覆盖 |
| 全仓逐模块回归以外的性能／并发检查 | 本次改动不触及并发、事务或性能路径 |

## 自检

提交审核前逐条核对（与共用清单 `plan/test-plan-checklist.md` 同一口径）：① 必测项只引用能证明本批目标的方法，T4／T5 的通过条件只限列明的方法自身断言；② CI 不在必测清单；③ 对比脚本有确切来源、复制命令与哈希；④ 命令块启用 `set -e` 且 `RUN` 在同一 shell 进程内使用；⑤ 失败注入标为“本批不适用”并说明原因；⑥ 计划文字与执行记录使用同一套编号；⑦ 编号与版本一致。

## 修订记录

- 第 1 版：首次提交测试计划审核。
