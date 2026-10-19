# 第三批：Stage 3 纯渲染组抽成独立模块 测试执行记录（2026-10-18）

- 测试计划：[test-plan.md](test-plan.md)，第 6 版（第 1 版取得第一、二关口 PASS；第 2 版只按审核意见细化检查方式，未增删编号）。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 1 版（`Plan conclusion: APPROVED`，P1–P4 全 PASS）。
- 对照基准：`ffa91aedf94aaf146f9cf1899f3fe4395cfaddad`（本批从它拉出，含批次二改动）。
- 被测提交：`68647a56eb54d245bc68012d07eb233e1023e411`；执行时 `git status --porcelain` 为空。
- 环境：本地 macOS，Python 3.14.7；只使用标准库与既有夹具，未新增依赖。仓库 CI 使用工作流固定的 Python 3.12。
- 原始输出（仓库外）：`/tmp/pc-batch3-IZjWB0/`（本轮实际目录）；证据文件：对比脚本 `compare_stage3_render.py` 与 `t1t2-refined.log`（T1/T2）、`t3-narrowed.log`（T3）、`t4-narrowed.log`（T4），历史整模块日志 `t3-final.log`、`t4-final.log`。

## 逐项结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | 对比脚本输出 `T1 render_candidates_md byte-identical -> base=3465B head=3465B`、`T1 render_candidates_md without profile byte-identical -> base=2370B head=2370B`、`T1 render_candidates_overview byte-identical -> base=346B head=346B`，退出码 0 |
| T2 | 通过 | 同一脚本输出两个公开函数的签名一致与四个私有 helper 仍可按原名取到；退出码 0 |
| T3 | 通过 | 按第 5 版清单只跑 7 个方法：`Ran 7 tests in 26.222s`，`OK`，退出码 0（head `00f307e`）。更早的整模块运行 `Ran 47 tests in 172.558s` 是这 7 项的超集，保留作历史证据；多出的 40 项属清单外，不作为本批通过条件 |
| T4 | 通过 | 按第 5 版清单只跑 2 个方法：`Ran 2 tests in 2.754s`，`OK`，退出码 0（head `00f307e`）。更早的整模块运行 `Ran 24 tests in 27.150s` 是这 2 项的超集，保留作历史证据 |
| 既有仓库检查 | 通过 | 仓库 CI 在 head `00f307e43ec72e12a8a13080323e43b69630178a` 上跑全量 `unittest discover`：运行 `39152603658`，8m3s，检查项 `test` pass。按第 5 版计划这项不属于本批业务必测项，只作既有检查结果引用；该 head 相对被测提交只多文档提交（`git diff 68647a5 00f307e -- .apm/` 为空） |

## 执行方法与命令

以下命令都在工作树根目录 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-render-group` 执行（第 1、2 步里的相对路径依赖该工作目录），第 3、4 步的块自带 `cd`。

1. 准备本轮运行目录（本轮沿用 `/tmp/pc-batch3-IZjWB0`，对比脚本 `compare_stage3_render.py` 已在其中，不需要再复制；换新目录时按测试计划第 1 步 `cp /tmp/pc-batch3-IZjWB0/compare_stage3_render.py "$RUN/compare_stage3_render.py"`），并取出基准修订的 runner：

   ```sh
   set -e
   RUN=/tmp/pc-batch3-IZjWB0
   test -f "$RUN/compare_stage3_render.py"
   git show ffa91aedf94aaf146f9cf1899f3fe4395cfaddad:.apm/skills/professor-contact/scripts/contact_state.py > "$RUN/base_contact_state.py"
   ```

2. T1/T2：把基准 runner 与改动后的 runner 在同一进程里各按文件路径加载（`importlib.util.spec_from_file_location`，两个不同的模块名，互不共享 `sys.modules` 条目），两侧都把各自的 `now_utc` 换成同一个固定返回值，再用同一组代表性输入调用两个公开渲染器：

   ```sh
   set -e
   uv run --no-project "$RUN/compare_stage3_render.py" \
     "$RUN/base_contact_state.py" \
     .apm/skills/professor-contact/scripts/contact_state.py
   ```

   输入覆盖：两个方向条目（一个 `verdict: 勉强`）＋方向级红线去重＋`refined` 变体＋`priority`；一个含两名参与者的跨方向组；候选级红线（含空串与重复）＋`gap_refs`（含 `done_by_self`）＋`_pack_papers`（含 `_analysis_rel` 与缺失两种情况）；总览的方向行与跨方向行；另一次 `profile_fp=None` 且空跨方向组的降级调用。两个渲染函数各比较一次完整输出字符串，降级调用再比较一次。

3. T3：按第 5 版清单跑 7 个方法；在 head `00f307e` 上重跑得到 `Ran 7 tests in 26.222s`、`OK`，此前的四模块运行（47 项）作为超集证据保留。

   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-render-group/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage3_direction_groups.Stage3DirectionGroupTests.test_ideas_grouped_per_direction_share_paper_identity \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_issue_in_second_direction_repairs_only_that_scope \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_cross_direction_issue_routes_to_the_exact_group_id \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_evidence_must_bind_the_current_render \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_replay_after_a_replaced_render_fails_closed \
     test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection \
     test_issue61_direction_credibility_warning.DirectionCredibilityWarningTests.test_warning_is_part_of_the_sha_bound_render \
     -v
   ```

4. T4：按第 5 版清单跑 2 个方法；在 head `00f307e` 上重跑得到 `Ran 2 tests in 2.754s`、`OK`。

   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-render-group/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
     test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
     -v
   ```

   这两组用例覆盖“测试按文件路径加载 runner”（导入 `test_contact_state` 时执行 runner）与“把 runner 复制进假安装布局再执行 wrapper / 加载 locator”；若夹具漏复制 `_stage3_render.py`，复制出的 runner 会在导入阶段直接失败。

## 清单入口与执行日志的对应

测试计划第 6 版把本批的本地通过条件收窄为清单引用的 7 个 T3 方法与 2 个 T4 方法。它们都包含在前面记录的整模块运行里（T3 的 4 文件 47 项、T4 的 2 文件 24 项，均 `OK`）：日志中逐个 `... ok` 的行即可对号。整模块运行中多出的用例（Stage 4 选择、旧状态迁移、其他教授结果保留、写入失败恢复、refined 模式状态语义、跨方向任务生成与缓存、Stage 5 生成器/校验器/技能文档合同等）是本批的清单外检查，**不构成本批的通过条件**，也不要求删除对应测试文件。仓库 CI 的全量结果按测试计划第 5 版单独引用，不计入本批业务必测项。

## 搬移范围核对

- 新模块正文与基准修订 7465–7651 行逐行对照：除两个公开渲染器的签名新增关键字注入（`now_utc`；`now_utc, candidates_md`）与总览两处 `{CANDIDATES_MD}` → `{candidates_md}` 标签替换外，其余行逐字节相同；模块不 import runner，也不定义第二份时钟。
- runner 侧只改三处：补 `import importlib.util` 与按路径加载块；被搬走的块换成同名同签名入口与四个私有 helper 别名；其余行不动，两个调用点未改。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在 head `00f307e` 上运行全量 `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`：运行 `39152603658`，8m3s，检查项 `test` pass。按第 5 版计划这属既有仓库检查、不属于本批业务必测项。
- 按 `Test Engineer Rule.md` 第 6 节，本批不在本地重复全仓回归。

## 结论与交接

- T1–T4 对被测提交 `68647a5` 取得有效通过结果（定向重跑时的 head 为 `00f307e`，此后只有文档提交）：T1/T2 用基准对照脚本，T3/T4 按第 5 版清单在 head `00f307e` 上定向重跑；仓库 CI 作为既有检查单独引用。无未完成项、无需要复验的项。
- 本记录之后如只改动文档（计划、记录、说明），未改产品代码与测试代码时，上述逐项结果继续有效并沿用。
- 依赖顺序：本批基于批次二分支 `refactor/stage5-runner-invocation`（PR #97）；#97 改写时按受影响范围重放并重跑受影响编号。
- 下一负责人：测试计划审核（第一、二关口）与合并审核（按 `Merge Reviewer Rule.md`）；本记录不代替任何关口结论。
