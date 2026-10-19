# Stage 2 划分第五批：校验报告与 refine 层（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage2-validation/implementation-plan.md` 第 3 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/stage2-validation/test-plan.md` 第 1 版（待审核，随本批 PR 提交）。
- 被测提交：`76f107a17a6e343a0e6aa28b504024d596639647`（代码提交 `refactor(stage2): move the validation and refine layer into a helper module`，父提交 `e973ffb4571344157b3c43a151906a24f48c7e4e`）。其后的文档提交只改本目录，不改变被测代码。
- 对照基准：`e973ffb4571344157b3c43a151906a24f48c7e4e`（当前 `main`，PR #108 合入第 1 批后）。实施开始时 `origin/main` 为 `0f89ebd`；实施中 main 前进到 `e973ffb`，本批重放到新基准，A/B 与定向测试全部在重放后重跑。
- 环境：macOS，Python 3.14.7（`python3 --version`），仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage2-validation-TTc7wR/`（对照基准、对比脚本、A/B 日志）；T4／T5 日志在 `/tmp/pc-stage5/t4.log`、`/tmp/pc-stage5/t5.log`。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 基线有效 | 通过 | 对比脚本 `/tmp/pc-stage2-validation-TTc7wR/compare_stage2_batch.py`（91 行，sha256 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`）：`T0` 3 条 `OK`（两侧目录不同、base 仍定义 14 个函数、head 一个都不定义）。 |
| T1 划分完成 | 通过 | 同一脚本 `T1` 29 条 `OK`：模块文件与 runner 同目录；14 个函数离开 runner 顶层、进入模块 `build()`。 |
| T2 逻辑不变 | 通过 | 同一脚本 `T2` 17 条 `OK`：14 个函数的代码 AST 与基准相同、非搬移顶层定义 AST 不变、runner 正好少了这 14 个定义、14 个别名齐全。 |
| T3 旧接口与加载不变 | 通过 | 同一脚本 `T3` 29 条 `OK`：14 个名字在两侧可调用且 `inspect.signature` 相同、直接执行 `contact_state.py --help` 退出码 0。合计 78 条 `OK`、末尾 `ALL CHECKS PASS`、退出码 0（输出 `/tmp/pc-stage2-validation-TTc7wR/compare.log`）。 |
| T4 校验与 refine 行为不变 | 通过 | 计划列出的 10 个方法：`Ran 10 tests in 34.270s`、`OK`，无失败、无跳过（输出 `/tmp/pc-stage5/t4.log`）。 |
| T5 复制夹具加载 | 通过 | 计划列出的 2 个方法：`Ran 2 tests in 2.962s`、`OK`，无失败、无跳过（输出 `/tmp/pc-stage5/t5.log`）。 |
| 既有仓库检查（非必测） | 通过 | PR #111 在 head `e42bff1` 上 run `39314679290`：`shards (shard1..4)` 与聚合 job `test` 全部 SUCCESS；被测代码是 `76f107a`，`e42bff1` 只加 plan/test 文档。 |

## 文件与接缝

- 被测 runner：`.apm/skills/professor-contact/scripts/contact_state.py`，10293 行，sha256 `e75593eb092d79e36dd68d18e849eac60c920caf0fcbd744a402ef7e3e8da9a3`。
- 新模块：`.apm/skills/professor-contact/scripts/_stage2_validation.py`，924 行，sha256 `6e6e8c51857390f396f3fdbb850d10a674334e17b2c84e5da179ef26a89ac347`。
- `contact_state.py --help` 退出码 0，输出 40 行；重放前后帮助文本逐字节相同。
- 14 个函数的 `co_freevars` 全部落在 38 个 `build()` 参数与 14 个同批函数名内，没有缺少的注入名。
- `git diff --ignore-blank-lines` 只有预期 hunk：加载块（新增 12 行）、14 个定义删除（3 处：`stage2_pack_scope`、`stage2_bound_render`、`stage2_merge_later_paper_source`/`stage2_rendered_later_papers`/`stage2_restore_pack_later_papers`，以及 `stage2_parse_report_location` 起的 9 个函数）、绑定点的新增（绑定调用与 14 个别名）。逐行核对：新增的非空行共 67 行，恰好等于加载块 11 行 + 绑定注释/调用 40 行 + 14 个别名，没有多余新增；删除的非空行共 819 行，恰好等于 14 个函数自身的非空行，没有删到别的定义。
- 顶层定义空行：runner 只有 7 处“定义前不是 2 个空行”的例外（`_stage3_bound_render` 6、`_stage3_candidates_entry` 4、`stage3_validation_evidence` 4、`_write_stage3_invocation` 1、`cmd_stage3_write_validation` 10、`cmd_stage3_finalize` 3、`require_user_choices` 1），与基线的同一组例外逐项相同；新模块 `build()` 前为 2 个空行，函数之间为 2 个空行。绑定点前后各 2 个空行。

## 说明与偏差

- 基准前进：实施开始时 `origin/main` 为 `0f89ebd`，完成后 main 为 `e973ffb`（PR #108 合入第 1 批）。本批按“HEAD 是 `0f89ebd` 或其后代”的要求重放到 `e973ffb`；14 个函数在 `0f89ebd..e973ffb` 之间的 AST 不变，A/B 对照基准改为 `e973ffb`。
- 行号变化：执行计划中的旧基准行号（4218-4236、10139-11018）在新基准上变为 3414-3432、9333-10212（第 1 批移走上游函数导致整体前移）。实现与测试均按函数名/AST 定位，未按旧行号删改。
- 加载块位置：`load_anchor=188` 在新基准上仍是 `SCHEMA = 1` 所在行，因此本批加载块位于 `SCHEMA = 1` 之前、第 1 批的 `_stage2_preflight` 加载块之前；两个加载块各自按路径加载，互不依赖，符号不重名。
- 跨批依赖：第 1 批已合入，`stage2_pack_state_fingerprint`、`stage2_pack_content_fingerprint` 以 runner 别名注入；第 4 批未合入，`stage2_require_paper_reference_titles`、`stage2_trusted_paper_title`、`stage2_require_later_paper_titles` 仍在 runner 顶层，绑定点在其定义结束之后，导入期无 `NameError`。
- 无测试跳过、无失败注入（本批不适用）；没有改测试、常量值、CLI、入口清单或 Nix 布局。

## 复核入口

- A/B：`/tmp/pc-stage2-validation-TTc7wR/compare.log`（78 条 `OK`）。
- T4：`/tmp/pc-stage5/t4.log`（`Ran 10 tests`、`OK`）。
- T5：`/tmp/pc-stage5/t5.log`（`Ran 2 tests`、`OK`）。
- 帮助：`/tmp/pc-stage5/help-new.out`（40 行，退出码 0）。
