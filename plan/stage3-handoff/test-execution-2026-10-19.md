# 边界二：Stage 3 校验交接原语搬移 测试执行记录（2026-10-19）

- 测试计划：[test-plan.md](test-plan.md)，第 4 版（第 1 版取得第一、二关口 PASS；第 3 版把仓库 CI 移出业务必测清单、补齐驱动脚本复制步骤并启用 `set -e`）。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 3 版（`Plan conclusion: APPROVED`）。
- 对照基准：`779fb692ed5ded163ab0eb5b415aef698135f54e`。
- 被测提交：`fab297d46e07d664450be798f77d2344b88fda5d`；执行期间产品与测试代码处于该提交、未改动（其后的提交只改 `plan/` 下文档，`.apm/` 下字节未变）。
- 环境：本地 macOS，Python 3.14.7；只使用标准库与既有夹具。仓库 CI 使用工作流固定的 Python 3.12。
- 说明：执行时工作树 `git status --porcelain` 为空；`/tmp/pc-bnd2-check/status.txt` 是空文件（状态改由本文件文字记录），每个编号的退出码记录在对应日志与 `diff` 结果里。
- 原始输出（仓库外）：`/tmp/pc-bnd2-check/`（本轮实际目录）；证据文件 `base5.json`／`head5.json`（最终）、`base2.json`／`head2.json`（同构目录复跑）、历史尝试 `base3.json`／`head3.json`、`base4.json`／`head4.json`，日志 `t5-final.log`、`t5-18tests.log`；本文件只记录命令、方法与结果。

## 逐项结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | `base5.json` 与 `head5.json` 逐字段相同：小块与 76800 B 写入的摘要、权限 384（0o600）、无 `.` 残留；对已存在路径写入两侧同为 `FileExistsError` 且原文件摘要不变；身份一致删除、身份不一致保留、None 保留三分支一致。集成失败清理由 T5 的 `test_issue66_validation_handoff` 批量写/回读失败用例覆盖 |
| T2 | 通过 | 同一对比：合法对象解析结果相同、重复键与 `NaN`/`Infinity` 同为 `ValueError`、数组两侧同为列表、坏 UTF-8 异常类型相同 |
| T3 | 通过 | 同一对比：生成态与修正态两种 invocation 参数映射逐字段相同，且 invocation 字典未被改动 |
| T4 | 通过 | 同一对比：五份渲染文档（含同一标记重复出现）的作用域列表逐项相同；`scope_key` 四例相同；路径归一化四类输入结果/错误 JSON/退出码相同；轮次守卫 7 组状态（覆盖 5 个失败分支（4 个不同原因码）与正常 round 2）判定相同；runner 侧 `stage3_render_line_scopes` 的签名两侧都不含 `fail` |
| T5 | 通过 | 按第 4 版清单只跑 18 个目标：`Ran 18 tests in 42.103s`，`OK`，退出码 0（`test_issue66_validation_handoff` 整模块 12 项——该模块每个用例都以被移动的交接原语为主要目的——加 `test_stage3_validation_refine` 的 6 个具名方法）。更早的 `Ran 55 tests in 206.556s`（四个整模块）是本次命令的超集，保留作历史证据 |
| 既有仓库检查 | 通过 | 仓库 CI 在 head `62faf7c` 上跑全量 `unittest discover`：运行 `39151049255`，7m44s，检查项 `test` pass，结论 success。该 head 相对被测提交只多**一个**文档提交，产品与测试字节未变（`git diff fab297d 62faf7c -- .apm/` 为空）。按测试计划第 4 版，这项不属于本批业务必测项，只作既有检查结果引用 |

## 执行方法与命令

1. 准备本轮运行目录（本轮沿用 `/tmp/pc-bnd2-check`，驱动 `handoff_probe.py` 已在其中，不需要再复制；换新目录时按测试计划第 1 步 `cp` 过去），取出基准修订的 runner 及它依赖的两个兄弟模块到 `$RUN/base/`（改动侧直接跑工作树 runner，不需要副本）：

   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-handoff
   git status --porcelain                   # 执行时为空
   RUN=/tmp/pc-bnd2-check
   test -f "$RUN/handoff_probe.py"
   mkdir -p "$RUN/base"
   for name in contact_state _stage3_render _contact_io; do
     git show 779fb692ed5ded163ab0eb5b415aef698135f54e:.apm/skills/professor-contact/scripts/$name.py > "$RUN/base/$name.py"
   done
   ```

2. T1–T4：同一驱动脚本分别以基准副本与工作树 runner 为参数运行（打印前把工作目录前缀替换为 `<WORK>`），再逐字段比较：

   ```sh
   set -e
   uv run --no-project "$RUN/handoff_probe.py" "$RUN/base/contact_state.py" "$RUN/base-work" > "$RUN/base.json"
   uv run --no-project "$RUN/handoff_probe.py" .apm/skills/professor-contact/scripts/contact_state.py "$RUN/head-work" > "$RUN/head.json"
   diff -u "$RUN/base.json" "$RUN/head.json" && echo "T1-T4 IDENTICAL"
   ```

   本文件表格里的证据文件是 `base5.json`／`head5.json`（同一条命令在修正空断言与工作目录归一化后换名重跑，`diff` 同样无输出）；更早的 `base3.json`／`head3.json`（空断言版本）与 `base4.json`／`head4.json`（工作目录未归一化）保留作历史尝试。

   驱动用一个签名适配器（`inspect.signature` 判断是否含 `fail` 参数）让同一份脚本驱动改动前后的 runner；适配器不吞异常、两侧同逻辑。

3. T5：既有 Stage 3 校验交接用例。

   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-handoff/.apm/skills/professor-contact/tests
   python3 -m unittest test_issue66_validation_handoff \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_issue_in_second_direction_repairs_only_that_scope \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_cross_direction_issue_routes_to_the_exact_group_id \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_raw_validator_handoff_fail_closed \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_correction_cannot_skip_or_add_scopes \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_second_validator_round_requires_completed_correction \
     test_stage3_validation_refine.Stage3ValidationIngestTests.test_round_and_terminal_result_are_derived_not_supplied \
     -v
   ```

4. 搬移核对：基准修订 15 个行区间（3 个常量 + 14 个函数）与新模块正文在反向套用 11 处文档化改动（7 处签名加 `fail`、4 处模块内互调传参）后逐字节相同。

## 执行中修正的测试资产问题（保留记录）

- 抽取脚本首次运行被自身的“3 个以上连续空行”护栏中止（脚本假设 runner 里没有这种空行，实际存在）；改为按分段重建并在接缝处只修剪边界空行，未改产品代码。
- 驱动脚本第一版把 `capture(name, *args)` 设计成“按名字查找 runner 属性”，但所有调用点传的都是零参数 lambda，于是 JSON／参数映射／写入／作用域／路径／轮次这些小节全部以同一条 `TypeError: attribute name must be string, not 'function'` 占位——两侧看似一致，实为空断言。发现后把 `capture` 改成接收 thunk，重跑并逐项确认真正产生结果（合法对象返回 dict、重复键抛 `ValueError`、作用域返回列表、相对路径退出码 1 等）。该空断言运行保留在 `/tmp/pc-bnd2-check/base3.json`、`head3.json`。
- 修正后的首次真实运行只剩两处差异，都是两侧工作目录绝对路径不同造成的（路径归一化结果与 `FileExistsError` 消息）；驱动改为打印前把工作目录替换为 `<WORK>`，复跑后逐字段相同。
- 以上三次都属测试资产问题，不是产品缺陷；每次修正后都整体重跑受影响编号。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在本 PR 提交上运行全量 `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`；结果见 PR 检查项，本批不在本地重复全仓回归。

## 结论与交接

- T1–T5 对被测提交 `fab297d` 全部取得有效通过结果；仓库 CI 作为既有检查单独引用（运行编号、所跑 head 与检查状态见上表），产品字节与该提交相同。
- 本记录之后如只改文档，未改产品与测试代码时，上述逐项结果继续有效并沿用。
- 依赖顺序：本批堆叠在边界一分支 `refactor/shared-error-and-commit`（PR #99）之上，合并顺序 #97 → #98 → #99 → 本批。
- 下一负责人：测试计划审核结论的第三关口核对与合并审核；本记录不代替任何关口结论。
