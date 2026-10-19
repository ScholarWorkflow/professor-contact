# 第三批：Stage 3 纯渲染组抽成独立模块（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 1 版。
- 需求来源：负责人 2026-10-18 授权的三批要求第 3 批；原文见执行计划。
- Target repository revision: 工作分支 `refactor/stage3-render-group`（从 `ffa91aedf94aaf146f9cf1899f3fe4395cfaddad` 拉出）实施后的提交；对照基准同为 `ffa91aedf94aaf146f9cf1899f3fe4395cfaddad`。
- Test plan revision: 第 6 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要达到的目标与本次直接改变的行为。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | 六个函数搬进新模块后渲染逐字节一致 | 同一组代表性输入：多方向条目（含 credibility 勉强/疑似幻觉、方向级红线、refined 变体、priority）、跨方向候选组（含参与者与 group_id）、候选级红线与去重、gap_refs；分别调用基准修订与改动修订的 `contact_state.render_candidates_md` 与 `contact_state.render_candidates_overview`，两侧都把 `now_utc` 冻结成同一常量；另跑一次 `profile_fp=None` 且无跨方向组的降级调用 | 各次调用的输出字符串**逐字节相同** | 仓库外脚本：从 `git show ffa91ae:...contact_state.py` 取基准 runner 到 `/tmp`，与工作树 runner 在同一进程里各按文件路径加载并比较；判据是每项 `OK`/`FAIL` 行与脚本退出码（全通过时打印 `ALL CHECKS PASS`） |
| T2 | 旧调用接口不变 | 基准修订与改动修订的 `contact_state.render_candidates_md` / `render_candidates_overview` 的签名，以及四个私有 helper 是否仍可按原名取到 | 参数名、顺序、默认值完全一致；两个公开函数与四个私有 helper 都能从 runner 命名空间按原名取到 | 同 T1 脚本内断言（`inspect.signature` 字符串相等 + `callable` 检查） |
| T3 | 渲染落盘、摘要绑定与标记定位不变（**通过条件只限这三类断言**） | 既有方法中与这三类有关的断言：`test_stage3_direction_groups.Stage3DirectionGroupTests.test_ideas_grouped_per_direction_share_paper_identity` 的**渲染内容部分**（方向 ID 顺序、`candidate_meta` 标记、三处分析链接计数、无跨方向小节）；`test_stage3_validation_refine.Stage3ValidationIngestTests.test_issue_in_second_direction_repairs_only_that_scope` 与 `test_cross_direction_issue_routes_to_the_exact_group_id` 的**标记定位部分**（问题归属到哪个 scope／group）；`test_evidence_must_bind_the_current_render`、`test_replay_after_a_replaced_render_fails_closed`、`test_warning_is_part_of_the_sha_bound_render` 的**摘要绑定部分**；`test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection` 的**总览渲染部分** | 上述三类断言全部成立；已执行的定向 7 项 `OK` 记录作为这些断言的证据保留 | 运行第 2 步列出的 7 个方法，但**只以上述三类断言为本批验收条件**：方法内的其它断言（方向身份与状态版本、纠错任务生成与参数、候选状态更新、总览的状态发现与迁移）不属本批范围，它们若失败按清单外记录并写明失败断言，不改变本批结论 |
| T4 | runner 的两条加载路径与复制夹具都仍可用（**通过条件只限两个加载事实**） | （a）把 runner 复制进假安装布局后执行 wrapper；（b）把 runner 复制进安装布局后按文件路径导入 | 两个加载事实成立：两处复制布局都包含 `_stage3_render.py`，且复制后的 runner 能按路径加载它；已执行的定向 2 项 `OK` 记录作为这两个事实的证据保留 | 运行第 3 步列出的 2 个方法，但**只以“复制布局含新模块”与“按路径加载成功”为本批验收条件**：方法内的其它断言（第五阶段联系方式证据状态、上游检查器定位与返回内容）不属本批范围，失败时按清单外记录 |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的全量 `unittest discover` 由仓库工作流照常执行，其运行结果单独引用，不作为本批业务必测项，也不因本批而扩张或缩减；合并要求继续按仓库规则执行。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-render-group` 内进行；临时脚本与运行产物放仓库外 `/tmp` 目录（复跑时用 `mktemp -d /tmp/pc-batch3-XXXXXX` 新建；本批执行记录沿用 `/tmp/pc-batch3-IZjWB0/` 并已点名，见执行记录第 1 步）。

1. 准备与 T1/T2 对照（**同一个命令块，`RUN` 在同一 shell 进程内**）：确认工作树只有本批改动、Python 可用，取出基准修订的 runner 副本，复制对比脚本，然后运行它。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-render-group
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-batch3-XXXXXX)
   git show ffa91aedf94aaf146f9cf1899f3fe4395cfaddad:.apm/skills/professor-contact/scripts/contact_state.py > "$RUN/base_contact_state.py"
   cp /tmp/pc-batch3-IZjWB0/compare_stage3_render.py "$RUN/compare_stage3_render.py"
   uv run --no-project "$RUN/compare_stage3_render.py" "$RUN/base_contact_state.py" \
     .apm/skills/professor-contact/scripts/contact_state.py
   ```
   `cp` 是必须的：脚本自带输入构造与断言，不能在临时目录里凭提纲重写；来源缺失时按执行记录点名的目录 `/tmp/pc-batch3-IZjWB0/` 找回（记录里同时点名了 `t1t2-refined.log`、`t3-narrowed.log`、`t4-narrowed.log` 三个证据文件），仍找不到就停止并交计划所有人。**`RUN` 不导出，后面各步必须在同一 shell 进程内继续执行**；分两次粘贴到不同终端会取不到该变量。
   预期：每一项打印 `OK  <标签>`，共 11 行（2 行前置检查 `runner exposes render_candidates_md` / `runner exposes render_candidates_overview`、T1 三行、T2 六行），末尾 `ALL CHECKS PASS`，退出码 0；任何 `FAIL` 都会让脚本非 0 退出，`set -e` 随之中止。

2. T3：只跑清单列出的 7 个方法（通过条件见 T3 行）。
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
   预期：`Ran 7 tests`、全部 `ok`。此前记录的整模块运行（47 项）是这 7 项的超集，多出的用例属清单外（Stage 4 选择、旧状态迁移、写入失败恢复、refined 模式状态语义、跨方向任务生成与缓存、Stage 5 合同等），不构成本批通过条件，也不要求删除测试文件。
3. T4：只跑清单列出的 2 个方法（通过条件见 T4 行）。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-render-group/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
     test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
     -v
   ```
   预期：`Ran 2 tests`、全部 `ok`。此前记录的整模块运行（24 项）是这 2 项的超集，多出的 22 项属清单外：`test_stage5_immutable` 其余 9 项与 `test_stage5_dualtarget_contract` 其余 13 项检查的是 Stage-5 模板/定向范围、文档契约与定位器细节，不以本批渲染组行为为主要目的，不计入本批结果。
4. 既有仓库检查：把改动推送到 PR 后引用仓库 CI 的全量结果（不属于本批必测项，见上文说明）；CI 未通过时按第 6 步处理。
5. 记录：保存上述命令、实际提交 SHA、逐项结果与必要输出片段到 `/tmp` 运行目录，并把方法与结果写入 `test-execution-<日期>.md`；既有仓库检查的运行结果按运行编号与所跑 head 单独记录。
6. 失败处理：
   - 逐字节对比出现差异：按差异定位到具体函数与行，判定为产品缺陷交实现负责人修正后重跑 T1/T2/T3。
   - 定向用例失败：区分“本次改动引入的回归”“既有失败”“环境问题”；本次引入的回归修正后重跑受影响编号。
   - 既有跳过项按未执行记录，不算失败；不做无新信息的重复运行。

## 对比脚本要点（T1、T2）

- 用 `importlib.util.spec_from_file_location` 分别加载 `"stage3_base"`（`/tmp` 里的基准 runner）与 `"stage3_head"`（工作树 runner），两次加载互不共享 `sys.modules` 名字。
- 两侧都把各自的 `now_utc` 换成同一个固定返回值（`contact_state.now_utc = lambda: "2026-10-18T00:00:00Z"`），再调用各自的 `render_candidates_md` / `render_candidates_overview`；基准修订的函数体直接读模块全局 `now_utc`，改动修订的包装函数在调用点传入同一个全局，因此冻结方式一致。
- 输入构造覆盖：两个方向（一个 credibility 为“勉强”，一个正常）、方向级红线去重、refined 变体与 priority、一个含两名参与者的跨方向组、候选级红线与 `gap_refs`（含 `done_by_self`）、`_pack_papers` 索引（含 `_analysis_rel` 与缺失两种情况）、总览的行与跨方向行；另加一次 `profile_fp=None` 且空跨方向组的降级调用（覆盖“未按个人资料校准”后缀与空组跳过分支）。
- 断言：`render_candidates_md` 两次输出 `==`（含 `profile_fp=None` 那次）；`render_candidates_overview` 两次输出 `==`；两个函数的 `inspect.signature` 字符串 `==`；四个私有 helper（`_red_line_key`、`_candidate_red_lines`、`_render_idea_block`、`_stage3_scope_marker`）在改动修订的 runner 命名空间里仍可按原名取到。

## 环境与预检

- 使用仓库现有的本地 Python（本次准备时 `python3 --version` 记录实际值）与既有测试夹具，不新增依赖、不新增判定器或采集器；对比脚本只用标准库。
- 测试只使用合成数据与临时目录；不接触用户业务资料。
- 预检只确认命令可用、工作树状态、基准 runner 能取出；不预先执行业务目标命令求结果。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 新模块单独的可导入性测试 | 属于内部组织；由 T4 的两条真实加载路径覆盖 |
| `stage3_render_line_scopes` 的独立重写或加固 | 本次未修改该校验器；T3 已覆盖它的定位结果 |
| 全仓本地回归 | 仓库 CI 已在 PR 上执行全量 discover，按 `Test Engineer Rule.md` 第 6 节直接引用，不重复执行 |
| 共享错误通道、事务／回滚、Stage3 提交与校验交接、Stage4/5 证据处理 | 本批不动这些区域，属另行常规审核的范围 |

## 自检

提交审核前逐条核对（与共用清单 `plan/test-plan-checklist.md` 同一口径）：① 必测项只引用能证明本批行为的方法，且 T3／T4 的通过条件只限各自列明的三类／两个断言；② CI 不在必测清单；③ 每个临时脚本都有确切来源与复制命令；④ 命令块启用 `set -e` 且 `RUN` 在同一 shell 进程内使用；⑤ **失败注入：本批不适用**——本批没有修改事务／回滚，业务必测清单里也没有失败注入项（共用清单第 5 条只在必测清单列入失败注入时才检查）；⑥ 计划文字与执行记录用同一套标签；⑦ 编号与版本一致。

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 2 版：第 1 版取得第一、二关口 PASS（无 blocker）；本版只落实该轮的非阻断观察，不改变业务目标：T1 增加一次 `profile_fp=None` 且空跨方向组的降级对比、T2 的私有 helper 检查补齐 `_render_idea_block`、第 2 步写出确切调用命令与脚本实际输出标签、第 4 步补全 `cd`。
- 第 3 版：按正常审核的两项意见修正——① T3、T4 从“4 个文件 47 项 / 2 个文件 24 项全部通过”收窄为清单列出的 9 个与 2 个方法，移除整模块带入的 Stage 4 选择、旧状态迁移、写入失败恢复与 Stage 5 合同等清单外条件，并去掉与 T1 重复的红线去重/可信度警告渲染检查；② 补上 T1、T2 对比脚本的取得位置（上一轮实际使用的 `/tmp/pc-batch3-IZjWB0/compare_stage3_render.py`）与放入本轮临时目录的步骤。收窄后保留的方法都包含在此前 47/24 项通过记录中，不触发重跑；产品与测试代码未变。
- 第 4 版：按测试计划第 3 版复核的三项意见修正——① T3 再收窄为 7 个只断言渲染结果/渲染绑定/标记定位的方法（去掉 `test_refined_mode_requires_3_5_selectable_with_user_refined` 与 `test_explicit_cross_group_generates_separate_job_and_section`，它们分别以 refined 状态语义、跨方向任务生成与缓存复用为通过条件）；② 把仓库 CI 从业务必测清单移出，改为“既有仓库检查”单独引用；③ 第 1 步补 `cp` 复制对比脚本的明确命令，并写明脚本缺失时的找回方式与停止条件。
- 第 5 版：按与边界一/边界二相同的口径整理——第 1–4 步的命令块统一启用 `set -e`（准备步骤失败不再带着空目录继续），第 2 步不再提“按要点重建脚本”（脚本由第 1 步的 `cp` 取得），并新增“自检”小节。需求与必测编号不变。
- 第 6 版：按第 5 版审核的四个问题修正——① T3 的通过条件限定为渲染落盘／摘要绑定／标记定位三类断言，方法内其它断言（方向身份、纠错任务、候选状态、总览状态发现）明确不属本批；② T4 的通过条件限定为“复制布局含 `_stage3_render.py`”与“按路径加载成功”两个事实，方法内的第五阶段证据状态与上游检查器定位断言明确不属本批；③ 第 1、2 步合并为同一个命令块，并写明 `RUN` 不跨 shell 进程；④ 自检第 ⑤ 项标为“本批不适用”，并说明共用清单第 5 条只在必测清单列入失败注入时适用。

## 审核状态

测试计划第 6 版为当前唯一版本；第 1 版已取得第一、二关口 PASS（无 blocker），第 2 版只做检查方式细化，第 3 版按正常审核收窄 T3/T4 的检查入口与通过条件并补齐对比脚本准备说明；第 4 版再收窄 T3 到 7 项、把 CI 移出必测清单、补齐脚本复制命令，必测编号与预期结果未变，本版仅按审核意见细化检查方式与命令表述，未增删必测项、未改变预期结果。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
