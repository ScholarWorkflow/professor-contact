# 候选与跨方向校验划分：候选结果校验（测试执行记录）

## 版本与对象

- 执行计划：`plan/candidate-validate/implementation-plan.md`（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/candidate-validate/test-plan.md`（第一关 PASS）。
- 被测提交：实现提交 `refactor(validate): move the candidate and cross-direction validation into a module`。
- 对照基准：父分支 `refactor-stage5-helpers`（#124）的 head；命令按 `git rev-parse` 动态取值。
- 运行目录：仓库外的临时目录（下称 `$RUN`），其中 `base/` 为父提交导出的 `scripts`，`blocks/` 为从测试计划原文抽出的命令块，`logs/` 存放失败对照日志。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：`build()` 7 个 keyword-only 参数（无位置参数、无默认值）、5 个成员、5 个同名别名；绑定调用晚于 `_direction_slices`、别名晚于调用且早于 `_stage3_commands` 的工厂；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；5 个名字不再在 runner 顶层定义 |
| T1–T3 结构／AST／接口 | 通过 | 33 条 `OK`（T0 3、T1 11、T2 8、T3 11）、`ALL CHECKS PASS`；`--help` 与父提交逐字节相同 |
| T2 docstring | 通过 | `total=5 with_doc=3 multi=3 clean_equal=3 without_doc=2 missing=0 mismatched=0` |
| T4 候选与跨方向校验 | 通过 | 10 个方法（8 个走 `stage3-finalize`，其中 2 个覆盖跨方向组；2 个走 `stage3-rebuild-overview`）：`Ran 10 tests`、`OK` |
| T5 复制夹具 | 通过 | `Ran 2 tests`、`OK` |
| 失败注入 | 不适用 | 只搬移定义，不改事务、回滚、写入顺序、错误通道或 CLI 参数 |
| 失败对照（未触发） | 通过（块预检） | 单方法 `Ran 1 test`、`OK`，日志写在 `$RUN/logs/base-<sha12>/` 下 |
| 既有仓库检查（非必测） | 引用 CI 运行编号 | 不作为通过条件 |

## 文件与接缝

- runner：2334 行，sha256 `8368cb4fad68f7f93a0f78aeade7bdf66aa3d7ce3dd7018c12d7b9c0caf5edde`。
- 新模块：`_candidate_validate.py`，325 行，sha256 `53ac53ae9c13963a713af0cb9174649bc4d4ebefc7ec66fa5f4cdc840e99d5bc`。
- diff：`+29 −296`；`git diff --ignore-blank-lines -U0` 共 4 个 hunk（加载块、两段定义删除、绑定块）。
- 空行：删除后合并出的三处空行块（3／8／6 行）全部收敛为 2；父提交自带的 6 行块保持原尺寸。

## 说明与偏差

- **覆盖说明**：5 个搬移函数均有行为覆盖——`_validate_candidate_core`／`validate_candidate_result`／`render_candidates_md` 由 8 个 finalize 方法执行，`validate_cross_result` 由其中 2 个跨方向方法执行，`render_candidates_overview` 由 2 个 rebuild 方法执行。`stage3-plan` 与 `migrate-v3` 本身不调用本批函数，因此不列为本批覆盖。
- **绑定位置**：7 个注入名最晚的 `_direction_slices`（890–912）之后、唯一消费方 `_stage3_commands` 的工厂之前，两侧都满足。
- 无测试跳过；没有改测试、常量值、CLI、入口清单或 Nix 布局。

## 复核入口

测试计划第 1–5 步的命令块可直接重跑；日志落在 `$RUN` 下的 `t0.log`、`compare.log`、`docstring.log`、`t4.log`、`t5.log`、`baseline.log`。
