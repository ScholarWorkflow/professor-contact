# Stage 2 划分第一批：预检、身份与 plan 命令层（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版（`Plan conclusion: APPROVED`）。
- 需求来源：负责人 2026-10-20 的 Stage 2 划分指示；原文与范围见执行计划。
- Target repository revision: 工作分支 `refactor-stage2-split` 实施后的提交；对照基准为当前 `main` `d5a4f751fb80de4819d4a1de3ee829db52cea6fc`（合并前，`contact_state.py` 与实施基线 `b5621db` 相同）。
- Test plan revision: 第 3 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要达到的目标与本次直接改变的行为。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | 27 个函数与 8 个常量确实完成划分（R1） | 工作树 `scripts/contact_state.py`、新模块 `scripts/_stage2_preflight.py`；对照基准为当前 `main`（`git archive` 取出的 scripts 目录） | `T0`：base 与 head 是两个不同目录、base 仍定义 27 个函数、head 一个都不定义（防止把 head 同时当 base 使 T1–T3 空转）；27 个函数不再出现在 runner 顶层、都出现在模块 `build()` 内；模块文件与 runner 同目录；8 个常量不再由 runner 定义，runner 只保留指向模块的别名 | `/tmp` 对比脚本的 `T0 ...` 与 `T1 ...` 行；全部 `OK`，末尾 `ALL CHECKS PASS` |
| T2 | 搬移没有改变任何函数逻辑或常量（R2） | 同上两侧源码 | 27 个函数的代码 AST 与基准完全相同（多行 docstring 的续行允许且只允许增加 4 个空格缩进）；8 个常量的源代码与基准相同（忽略行尾空白）；runner 其余顶层定义（函数与类）AST 不变，且离开 runner 的定义正好是这 27 个、没有新增 | 同一对比脚本的 `T2 ...` 行；全部 `OK` |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 27 个名字在两侧都可调用；`inspect.signature` 字符串两侧相同；8 个常量值两侧相同；直接执行 `contact_state.py --help` 退出码 0 | 同一对比脚本的 `T3 ...` 行；全部 `OK` |
| T4 | `stage2-preflight` 与 `stage2-plan` 的命令行为不变（R2） | 既有测试方法：`test_stage2_preflight.TestPreflightDecision.test_b_perfect_no_change_reuses_without_pdf_reads`、`...test_c_target_note_change_invalidates_only_that_direction`、`...test_h_papers_catalog_change_blocks_reuse_all`、`...test_n_version_changes_block_reuse`、`...test_p_validator_gate`；`test_stage2_preflight.TestPreflightGuardrails.test_invalid_params_fail_fast`、`...test_preflight_never_constructs_stage2_context_or_reads_analysis_bytes`；`test_stage2_preflight.TestFinalizePreflightWiring.test_legacy_slow_path_seeds_metadata_for_next_run`；`test_contact_state.Issue65Stage2BindingTests.test_issue65_stage2_exact_stage1_binding_lifecycle`；`test_contact_state.TestIssue64Stage2PlanBinding.test_issue64_t6_plan_carries_the_consumed_preflight_proof` | 这 10 个方法全部通过；本批的通过条件只限这些方法自身的既有断言（复用/失效判定、参数校验、preflight 只读 persisted 状态且不打开 analysis/PDF 字节、metadata 播种、preflight→plan 的证明绑定）。注：`test_preflight_never_constructs...` 的名字提到“不构造上下文”，但其断言只跟踪 `Path.open` 与 `.pdf` 读取；本批不把“不构造上下文”当作它证明的事实（函数体未变由 T2 覆盖），`test_legacy_slow_path...` 的 setup 会调用未搬移的 `stage2_finalize`，属既有夹具依赖 | 第 2 步命令；`Ran 10 tests`、`OK` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R4） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两个方法通过；复制布局包含 `_stage2_preflight.py`，复制后的 runner 能按路径加载它 | 第 3 步命令；`Ran 2 tests`、`OK` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的分片套件（`shards` 的 4 个分片）与聚合 job `test` 由仓库工作流照常执行，其结果单独引用；本批不因此扩张或缩减必测清单，也不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-split` 内进行；临时脚本与运行产物放仓库外 `/tmp` 目录。

1. 准备对照基准与脚本，运行 T1–T3（**同一个命令块，`RUN` 在同一 shell 进程内**）：
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-split
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-stage2-split-XXXXXX)
   mkdir -p "$RUN/base"
   git archive d5a4f751fb80de4819d4a1de3ee829db52cea6fc \
     .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
   cp /tmp/pc-stage2-p1/compare_stage2_preflight.py "$RUN/compare_stage2_preflight.py"
   shasum -a 256 "$RUN/compare_stage2_preflight.py"
   uv run --no-project "$RUN/compare_stage2_preflight.py" \
     "$RUN/base/.apm/skills/professor-contact/scripts" \
     .apm/skills/professor-contact/scripts
   ```
   `cp` 是必须的：脚本自带全部检查，不能在临时目录里凭提纲重写；来源缺失时停止并交计划所有人，不重建。脚本参考 sha256 为 `da1639e46a99177c7174c39d0d44a41e9683fd9dc15ef3d2518e3a9503558823`（207 行），复制后核对同一哈希。**`RUN` 不导出，后续步骤必须在同一 shell 进程内继续执行**。
   预期：每条检查打印一行 `OK  <标签>`，共 201 行——T0 3 行（两侧不同、base 定义 27 个、head 不定义）、T1 71 行（模块存在 1 + 27 函数×2 + 8 常量×2）、T2 64 行（27 函数×2 + 8 常量 + 非搬移定义不变 + 定义集合差）、T3 63 行（27 函数×2 + 8 常量 + 1 直接执行）；末尾 `ALL CHECKS PASS`，退出码 0。

2. T4：只跑清单列出的 10 个方法。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-split/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage2_preflight.TestPreflightDecision.test_b_perfect_no_change_reuses_without_pdf_reads \
     test_stage2_preflight.TestPreflightDecision.test_c_target_note_change_invalidates_only_that_direction \
     test_stage2_preflight.TestPreflightDecision.test_h_papers_catalog_change_blocks_reuse_all \
     test_stage2_preflight.TestPreflightDecision.test_n_version_changes_block_reuse \
     test_stage2_preflight.TestPreflightDecision.test_p_validator_gate \
     test_stage2_preflight.TestPreflightGuardrails.test_invalid_params_fail_fast \
     test_stage2_preflight.TestPreflightGuardrails.test_preflight_never_constructs_stage2_context_or_reads_analysis_bytes \
     test_stage2_preflight.TestFinalizePreflightWiring.test_legacy_slow_path_seeds_metadata_for_next_run \
     test_contact_state.Issue65Stage2BindingTests.test_issue65_stage2_exact_stage1_binding_lifecycle \
     test_contact_state.TestIssue64Stage2PlanBinding.test_issue64_t6_plan_carries_the_consumed_preflight_proof \
     -v
   ```
   预期：`Ran 10 tests`、全部 `ok`，无 `FAIL`／`ERROR`；若出现跳过项，按未执行记录，不算通过。

3. T5：只跑清单列出的 2 个夹具方法。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-split/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
     test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
     -v
   ```
   预期：`Ran 2 tests`、全部 `ok`，无 `FAIL`／`ERROR`；若出现跳过项，按未执行记录，不算通过。

4. 既有仓库检查（不属于本批必测项，也不作为通过条件）：本批不在本地把全量套件列为必测步骤；改动推送到 PR 后，引用仓库 CI 的全量 discover 运行编号与结论。若执行者自愿做一次本地 sanity check，必须在自建的临时目录内运行（`SANITY=$(mktemp -d /tmp/pc-stage2-sanity-XXXXXX)`），结果只作为记录，不改变本批结论。

5. 失败注入：本批不适用。本批不修改事务／回滚、写入顺序或错误通道实现，业务必测清单里也没有失败注入项。

6. 记录：把命令、实际提交 SHA、逐项结果与必要输出片段写入 `/tmp` 运行目录，并把方法与结果写入 `test-execution-<日期>.md`；CI 结果按运行编号与所跑 head 单独记录。

7. 失败处理：
   - T1/T2/T3 任一 `FAIL`：按标签定位到具体函数／常量，判定为搬移缺陷，交实现负责人修正后重跑第 1 步；不得改脚本放宽判据。
   - T4/T5 方法失败：区分“本次改动引入的回归”“既有失败”“环境问题”；本次回归修正后重跑受影响编号。
   - 既有跳过项按未执行记录，不算失败；不做无新信息的重复运行。
   - 仓库 CI 失败时按合并规则处理，不并入本批必测结论。

## 环境与预检

- 使用仓库现有本地 Python（第 1 步记录 `python3 --version`）与既有测试夹具，不新增依赖、不新增判定器或采集器；对比脚本只用标准库。
- 第 1 步的 `shasum -a 256` 是 macOS 写法；若在 Linux 复跑，改用 `sha256sum`，判据不变（脚本 207 行、哈希 `da1639e46a99177c7174c39d0d44a41e9683fd9dc15ef3d2518e3a9503558823`）。
- 测试只使用合成数据与临时目录；不接触用户业务资料。
- 预检只确认命令可用、工作树状态、基准 scripts 目录能取出；不预先执行业务目标命令求结果。
- 基准对照的两侧都从同一 `b5621db` 与工作树 HEAD 取出，避免用不同版本的兄弟模块比较。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 新模块单独的可导入性单测 | 属内部组织；T3 的直接执行与 T5 的两条复制加载路径已覆盖真实加载方式 |
| 第 2–6 批（resolve／finalize／校验／refine／上下文类） | 本批不动，各批另立计划与测试清单 |
| 各函数内部逻辑的逐分支重测 | 本批是原样搬移；T2 的 AST 等价与既有测试已覆盖，不重复枚举 |
| 全仓逐模块回归以外的性能／并发检查 | 本次改动不触及并发、事务或性能路径 |

## 自检

提交审核前逐条核对（与共用清单 `plan/test-plan-checklist.md` 同一口径）：① 必测项只引用能证明本批目标的方法，T4／T5 的通过条件只限列明的方法自身断言；② CI 不在必测清单；③ 对比脚本有确切来源、复制命令与哈希；④ 命令块启用 `set -e` 且 `RUN` 在同一 shell 进程内使用；⑤ 失败注入标为“本批不适用”并说明原因；⑥ 计划文字与执行记录使用同一套编号；⑦ 编号与版本一致。

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 2 版：按第一轮审核修正——① 删除第 4 步的本地全量套件运行与“与基准 1025 项对照”，改为只引用 PR CI 的既有仓库检查，并明确本地 sanity check 可选、自建临时目录、不改变本批结论（第二关 blocker B1）；② T4／T5 预期补“无 FAIL／ERROR；跳过项按未执行记录”；③ 环境小节注明 `shasum` 与 `sha256sum` 的平台差异。业务目标与必测编号未变。
- 第 3 版：按独立审核的非阻断观测补强证据——① 对比脚本加 T0（base 必须是拆分前 runner、base != head，防止 T1–T3 空转）与非搬移顶层定义的 AST 对比；② T4 的通过条件改成方法自身断言的事实（去掉“不构造上下文”的过度表述，注明 `test_legacy_slow_path...` 的 setup 依赖未搬移的 `stage2_finalize`）；③ 既有仓库检查改为当前 main 的分片 CI 与聚合 job；④ 基线指针更新到 `d5a4f75`。必测编号与业务目标未变。

## 审核状态

- 第 1 版：第一关 PASS；第二关 NEEDS_MODIFICATION（blocker B1：第 4 步本地全量套件超出规则边界）。
- 第 2 版：按 B1 删除本地全量运行、改为只引用 PR CI；T4／T5 补跳过项口径；环境小节补平台差异。
- 第 2 版复核：第二关 NEEDS_MODIFICATION（第 22 行残留“本工作树跑一次全量套件 + 1025 项对照”）；已删除该句，现只引用 PR CI。
- 第 2 版复核（第二次）：第二关 PASS，无 blocker。
- 第 3 版：待第二关复核（对比脚本行数/哈希与 201 行计数变更）。
