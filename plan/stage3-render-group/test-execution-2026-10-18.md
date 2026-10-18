# 第三批：Stage 3 纯渲染组抽成独立模块 测试执行记录（2026-10-18）

- 测试计划：[test-plan.md](test-plan.md)，第 1 版。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 1 版（`Plan conclusion: APPROVED`，P1–P4 全 PASS）。
- 对照基准：`ffa91aedf94aaf146f9cf1899f3fe4395cfaddad`（本批从它拉出，含批次二改动）。
- 被测提交：`68647a56eb54d245bc68012d07eb233e1023e411`；执行时 `git status --porcelain` 为空。
- 环境：本地 macOS，Python 3.14.7；只使用标准库与既有夹具，未新增依赖。仓库 CI 使用工作流固定的 Python 3.12。
- 原始输出（仓库外）：`/tmp/pc-batch3-*/`；本文件只记录命令、方法与结果。

## 逐项结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | 对比脚本输出 `T1 render_candidates_md byte-identical -> base=3465B head=3465B`、`T1 render_candidates_overview byte-identical -> base=346B head=346B`，退出码 0 |
| T2 | 通过 | 同一脚本输出两个公开函数的签名一致与三个私有 helper 仍可按原名取到；退出码 0 |
| T3 | 通过 | `Ran 47 tests in 172.558s`，`OK`，退出码 0 |
| T4 | 通过 | `Ran 24 tests in 27.150s`，`OK`，退出码 0 |
| T5 | 通过 | 仓库 CI 在 PR 提交上跑全量 `unittest discover`，检查项 `test` 为 pass（见 PR 检查项） |

## 执行方法与命令

1. 取出基准修订的 runner 到仓库外目录：

   ```sh
   RUN=$(mktemp -d /tmp/pc-batch3-XXXXXX)
   git show ffa91aedf94aaf146f9cf1899f3fe4395cfaddad:.apm/skills/professor-contact/scripts/contact_state.py > "$RUN/base_contact_state.py"
   ```

2. T1/T2：把基准 runner 与改动后的 runner 在同一进程里各按文件路径加载（`importlib.util.spec_from_file_location`，两个不同的模块名，互不共享 `sys.modules` 条目），两侧都把各自的 `now_utc` 换成同一个固定返回值，再用同一组代表性输入调用两个公开渲染器：

   ```sh
   uv run --no-project "$RUN/compare_stage3_render.py" \
     "$RUN/base_contact_state.py" \
     .apm/skills/professor-contact/scripts/contact_state.py
   ```

   输入覆盖：两个方向条目（一个 `verdict: 勉强`）＋方向级红线去重＋`refined` 变体＋`priority`；一个含两名参与者的跨方向组；候选级红线（含空串与重复）＋`gap_refs`（含 `done_by_self`）＋`_pack_papers`（含 `_analysis_rel` 与缺失两种情况）；总览的方向行与跨方向行。两个渲染函数各比较一次完整输出字符串。

3. T3：Stage 3 渲染与校验定位回归。

   ```sh
   cd .apm/skills/professor-contact/tests
   python3 -m unittest test_stage3_direction_groups test_stage3_validation_refine \
     test_issue66_stage3_local_state test_issue61_direction_credibility_warning -v
   ```

4. T4：两条加载路径与复制夹具。

   ```sh
   python3 -m unittest test_stage5_immutable test_stage5_dualtarget_contract -v
   ```

   这两组用例覆盖“测试按文件路径加载 runner”（导入 `test_contact_state` 时执行 runner）与“把 runner 复制进假安装布局再执行 wrapper / 加载 locator”；若夹具漏复制 `_stage3_render.py`，复制出的 runner 会在导入阶段直接失败。

## 搬移范围核对

- 新模块正文与基准修订 7465–7651 行逐行对照：除两个公开渲染器的签名新增关键字注入（`now_utc`；`now_utc, candidates_md`）与总览两处 `{CANDIDATES_MD}` → `{candidates_md}` 标签替换外，其余行逐字节相同；模块不 import runner，也不定义第二份时钟。
- runner 侧只改三处：补 `import importlib.util` 与按路径加载块；被搬走的块换成同名同签名入口与四个私有 helper 别名；其余行不动，两个调用点未改。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在本 PR 提交上运行全量 `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`；结果见 PR 检查项。
- 按 `Test Engineer Rule.md` 第 6 节，本批不在本地重复全仓回归。

## 结论与交接

- T1–T5 对被测提交全部取得通过结果；无未完成项、无需要复验的项。
- 本记录之后如只改动文档（计划、记录、说明），未改产品代码与测试代码时，上述逐项结果继续有效并沿用。
- 依赖顺序：本批基于批次二分支 `refactor/stage5-runner-invocation`（PR #97）；#97 改写时按受影响范围重放并重跑受影响编号。
- 下一负责人：测试计划审核（第一、二关口）与合并审核（按 `Merge Reviewer Rule.md`）；本记录不代替任何关口结论。
