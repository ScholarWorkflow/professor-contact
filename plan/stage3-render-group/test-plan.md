# 第三批：Stage 3 纯渲染组抽成独立模块（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 1 版。
- 需求来源：负责人 2026-10-18 授权的三批要求第 3 批；原文见执行计划。
- Target repository revision: 工作分支 `refactor/stage3-render-group`（从 `ffa91aedf94aaf146f9cf1899f3fe4395cfaddad` 拉出）实施后的提交；对照基准同为 `ffa91aedf94aaf146f9cf1899f3fe4395cfaddad`。
- Test plan revision: 第 2 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要达到的目标与本次直接改变的行为。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | 六个函数搬进新模块后渲染逐字节一致 | 同一组代表性输入：多方向条目（含 credibility 勉强/疑似幻觉、方向级红线、refined 变体、priority）、跨方向候选组（含参与者与 group_id）、候选级红线与去重、gap_refs；分别调用基准修订与改动修订的 `contact_state.render_candidates_md` 与 `contact_state.render_candidates_overview`，两侧都把 `now_utc` 冻结成同一常量；另跑一次 `profile_fp=None` 且无跨方向组的降级调用 | 各次调用的输出字符串**逐字节相同** | 仓库外脚本：从 `git show ffa91ae:...contact_state.py` 取基准 runner 到 `/tmp`，与工作树 runner 在同一进程里各按文件路径加载并比较；判据是每项 `OK`/`FAIL` 行与脚本退出码（全通过时打印 `ALL CHECKS PASS`） |
| T2 | 旧调用接口不变 | 基准修订与改动修订的 `contact_state.render_candidates_md` / `render_candidates_overview` 的签名，以及四个私有 helper 是否仍可按原名取到 | 参数名、顺序、默认值完全一致；两个公开函数与四个私有 helper 都能从 runner 命名空间按原名取到 | 同 T1 脚本内断言（`inspect.signature` 字符串相等 + `callable` 检查） |
| T3 | Stage 3 渲染与校验定位的业务行为不变 | 既有 Stage 3 相关用例：方向分组渲染、校验范围定位与修正轮、教授本地状态与总览重建、可信度警告 | 全部通过，无 `FAIL`/`ERROR` | `python3 -m unittest test_stage3_direction_groups test_stage3_validation_refine test_issue66_stage3_local_state test_issue61_direction_credibility_warning -v` |
| T4 | runner 的两条加载路径与复制夹具都仍可用 | （a）测试按文件路径加载 runner（`spec_from_file_location`）；（b）把 runner 复制进假安装布局的夹具 | （a）加载成功，模块能按路径找到新模块；（b）夹具复制新模块后，涉及 wrapper 与 locator 的用例通过 | `python3 -m unittest test_stage5_immutable test_stage5_dualtarget_contract -v`（两者都会按路径加载或复制 runner） |
| T5 | 未改动区域的既有门禁 | 仓库 CI 对 PR 提交跑全量 `unittest discover` | 全量通过 | 直接引用 PR 的 CI 运行结果，不在本地重复全仓回归 |

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-render-group` 内进行；临时脚本与运行产物放仓库外 `/tmp` 目录（本次用 `mktemp -d /tmp/pc-batch3-XXXXXX`）。

1. 准备：确认工作树只有本批改动、Python 可用，并取出基准修订的 runner 副本。
   ```sh
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-render-group
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-batch3-XXXXXX)
   git show ffa91aedf94aaf146f9cf1899f3fe4395cfaddad:.apm/skills/professor-contact/scripts/contact_state.py > "$RUN/base_contact_state.py"
   ```
2. T1、T2：运行仓库外对比脚本（脚本写在 `$RUN/compare_stage3_render.py`，内容见下节），两个参数依次是基准 runner 文件与工作树 runner：
   ```sh
   uv run --no-project "$RUN/compare_stage3_render.py" "$RUN/base_contact_state.py" \
     .apm/skills/professor-contact/scripts/contact_state.py
   ```
   预期：每一项打印 `OK  <标签>`，共 11 行（2 行前置检查 `runner exposes render_candidates_md` / `render_candidates_overview`、T1 三行、T2 六行），末尾 `ALL CHECKS PASS`，退出码 0；任何 `FAIL` 都会让脚本非 0 退出。
3. T3：在校验范围相关用例上执行。
   ```sh
   cd .apm/skills/professor-contact/tests
   python3 -m unittest test_stage3_direction_groups test_stage3_validation_refine test_issue66_stage3_local_state test_issue61_direction_credibility_warning -v
   ```
   预期：全部 `ok`，无 `FAIL`/`ERROR`。
4. T4：加载路径与复制夹具。
   ```sh
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-render-group/.apm/skills/professor-contact/tests
   python3 -m unittest test_stage5_immutable test_stage5_dualtarget_contract -v
   ```
   预期：全部 `ok`；若夹具漏复制新模块，这两个文件会在导入或运行阶段直接失败。
5. T5：把改动推送到 PR 后引用仓库 CI 的全量结果；CI 未通过时按第 7 步处理。
6. 记录：保存上述命令、实际提交 SHA、逐项结果与必要输出片段到 `/tmp` 运行目录，并把方法与结果写入 `test-execution-<日期>.md`。
7. 失败处理：
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

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 2 版：第 1 版取得第一、二关口 PASS（无 blocker）；本版只落实该轮的非阻断观察，不改变业务目标：T1 增加一次 `profile_fp=None` 且空跨方向组的降级对比、T2 的私有 helper 检查补齐 `_render_idea_block`、第 2 步写出确切调用命令与脚本实际输出标签、第 4 步补全 `cd`。

## 审核状态

测试计划第 2 版为当前唯一版本；第 1 版已取得第一、二关口 PASS（无 blocker），本版仅按审核意见细化检查方式与命令表述，未增删必测项、未改变预期结果。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
