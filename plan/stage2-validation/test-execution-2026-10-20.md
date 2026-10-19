# Stage 2 划分第五批：校验报告与 refine 层（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage2-validation/implementation-plan.md` 第 3 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/stage2-validation/test-plan.md` 第 5 版（第一关 PASS；第二关按 R3 补第 1b 步后待复核）。
- 被测提交：`b2005f7`（代码提交 `refactor(stage2): move the validation and refine layer into a helper module`，父提交 `a1c018f7e533fd09f07c4cd12f7df4fcf06c14a3`，即 PR #110 分支 head）；分支 head `dcccf16`。其后的文档提交只改本目录，不改变被测代码。
- 对照基准：`a1c018f7e533fd09f07c4cd12f7df4fcf06c14a3`（父分支 `refactor-stage2-finalize` 的 head，已含 #108/#109/#110）。实施开始时 `origin/main` 为 `0f89ebd`，实施中前进到 `e973ffb`（#108），提交前又前进到 `7a59006c551dc863045fb5221143927357429c83`（#109）；本批两次重放到新基准，A/B 与定向测试都在最近一次重放后重跑。
- 环境：macOS；`python3 --version` 3.14.7，`uv run --no-project python3 --version` 3.14.6；仓库既有测试夹具；未新增依赖。
- 运行目录：A/B 基准与脚本在 `/tmp/pc-validation-rebase/`；日志在 `/tmp/pc-stage5/`：`compare-main2.log`、`source-main2.log`、`t4-main2.log`、`t5-main2.log`。早期的 `compare.log`、`t4.log`、`t5.log` 与 `/tmp/pc-stage2-validation-TTc7wR/` 保留作历史证据。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 基线有效 | 通过 | 对比脚本 `/tmp/pc-stage2-validation-TTc7wR/compare_stage2_batch.py`（91 行，sha256 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`）：`T0` 3 条 `OK`（两侧目录不同、base 仍定义 14 个函数、head 一个都不定义），输出 `/tmp/pc-stage5/compare-main2.log`。 |
| T1 划分完成与源码约束（R1、R3） | 通过 | 同一脚本 `T1` 29 条 `OK`：模块文件与 runner 同目录；14 个函数离开 runner 顶层、进入模块 `build()`。第 1b 步源码核对：4 条 `SOURCE ... OK` 与 `SOURCE CHECKS PASS`——模块不导入 runner、不做动态加载、不碰 `sys.path`／`sys.modules`；`build()` 恰好 38 个 keyword-only 参数、返回 14 个成员；runner 按 `Path(__file__).with_name("_stage2_validation.py")` 加载并以同名实参注入同一组 38 项，14 个别名都在绑定调用之后（输出 `/tmp/pc-stage5/source-main2.log`）。 |
| T2 逻辑不变 | 通过 | 同一脚本 `T2` 17 条 `OK`：14 个函数的代码 AST 与基准相同（脚本忽略 docstring 内容）、非搬移顶层定义 AST 不变、runner 正好少了这 14 个定义、14 个别名齐全。补充只读核对：9 个函数有 docstring（其中 4 个多行），`inspect.cleandoc` 后与基准同文；5 个函数没有 docstring；14 个别名与模块函数 `is` 同一对象。 |
| T3 旧接口与加载不变 | 通过 | 同一脚本 `T3` 29 条 `OK`：14 个名字在两侧可调用且 `inspect.signature` 相同、直接执行 `contact_state.py --help` 退出码 0。合计 78 条 `OK`、末尾 `ALL CHECKS PASS`、退出码 0（输出 `/tmp/pc-stage5/compare-main2.log`）。 |
| T4 校验与 refine 行为不变 | 通过 | 计划列出的 10 个方法：`Ran 10 tests in 17.053s`、`OK`，无失败、无跳过（输出 `/tmp/pc-stage5/t4-main2.log`）；本次没有跨批断言失败，因此全部断言通过，T4 按第 4 版条件式判据通过。 |
| T5 复制夹具加载 | 通过 | 计划列出的 2 个方法：`Ran 2 tests in 1.060s`、`OK`，无失败、无跳过（输出 `/tmp/pc-stage5/t5-main2.log`）；复制布局含 `_stage2_validation.py`，复制后的 runner 无导入/加载错误。 |
| 既有仓库检查（非必测） | 待跑 | rebase 后 head 为 `c3f231a`；rebase 前 PR #111 在 head `e42bff1` 上 run `39314679290` 全 SUCCESS（被测代码当时是 `76f107a`）。新 head 的 CI 以 PR 页面为准，不作为本批必测结论。 |

## 文件与接缝

- 被测 runner：`.apm/skills/professor-contact/scripts/contact_state.py`，8782 行，sha256 `62f101ddf3639fed24355844415186fe97230f1ee0003741199227901623a943`。
- 新模块：`.apm/skills/professor-contact/scripts/_stage2_validation.py`，924 行，sha256 `6e6e8c51857390f396f3fdbb850d10a674334e17b2c84e5da179ef26a89ac347`。
- `contact_state.py --help` 退出码 0，输出 40 行；重放前后帮助文本逐字节相同。
- 14 个函数的 `co_freevars` 全部落在 38 个 `build()` 参数与 14 个同批函数名内，没有缺少的注入名；第 1b 步进一步核对了注入契约本身（38 项同名、无多余、别名在调用之后）。
- `git diff --ignore-blank-lines` 只有预期 hunk：加载块（新增 12 行）、14 个定义删除（4 组：`stage2_pack_scope`；`stage2_bound_render`；`stage2_merge_later_paper_source`/`stage2_rendered_later_papers`/`stage2_restore_pack_later_papers`；`stage2_parse_report_location` 起的 9 个函数）、绑定点的新增（绑定调用与 14 个别名）。逐行核对：新增的非空行共 67 行，恰好等于加载块 11 行 + 绑定注释/调用 42 行 + 14 个别名，没有多余新增；删除的非空行共 819 行，恰好等于 14 个函数自身的非空行，没有删到别的定义。
- 顶层定义空行：runner 只有 7 处“定义前不是 2 个空行”的例外（`_stage3_bound_render` 6、`_stage3_candidates_entry` 4、`stage3_validation_evidence` 4、`_write_stage3_invocation` 1、`cmd_stage3_write_validation` 10、`cmd_stage3_finalize` 3、`require_user_choices` 1），与基线的同一组例外逐项相同；新模块 `build()` 前为 2 个空行；模块内嵌套函数之间为 1 个空行（与第 4 批一致；第 1 批为 2 个，属格式差异，不影响行为）。绑定点前后各 2 个空行。

## 说明与偏差

- 分支链：本批改为挂在 `refactor-stage2-finalize`（#110）之上，对照基准随之变为 `a1c018f`，A/B 与定向测试、docstring 全部在新基准上重跑。
- 基准前进两次：实施开始时 `origin/main` 为 `0f89ebd`，先前进到 `e973ffb`（#108），提交前再前进到 `7a59006c551dc863045fb5221143927357429c83`（#109）。本批两次重放，A/B 对照基准最终为 `7a59006c551dc863045fb5221143927357429c83`；14 个函数在 `0f89ebd..7a59006` 之间的 AST 不变。
- 行号变化：执行计划中的旧基准行号（4218-4236、10139-11018）在新基准上变为 3414-3432、9333-10212（第 1 批移走上游函数导致整体前移）。实现与测试均按函数名/AST 定位，未按旧行号删改。
- 加载块位置：`load_anchor=188` 的落点在 `#109` 合并后顺次后移，本批加载块位于 `_STAGE2_RESOLVE_*` 之后、`SCHEMA = 1` 之前；第 1 批的 `_stage2_preflight` 加载块仍在 `SCHEMA = 1` 之后。三个加载块各自按路径加载，互不依赖，符号不重名。
- 跨批依赖：第 1 批（#108）、第 2 批（#109）已合入，`stage2_pack_state_fingerprint`、`stage2_pack_content_fingerprint`、resolve 层各别名都由 runner 注入；第 4 批未合入，`stage2_require_paper_reference_titles`、`stage2_trusted_paper_title`、`stage2_require_later_paper_titles` 仍在 runner 顶层，绑定点在其定义结束之后，导入期无 `NameError`。
- 无测试跳过、无失败注入（本批不适用）；没有改测试、常量值、CLI、入口清单或 Nix 布局。
- 新增第 1b 步：第二关复核指出 T1/T3 只验证“可调用、签名相同、`--help` 成功”，不能证明 R3 的源码约束；补一个只读 AST 核对块，复用同两份源码，不新增脚本、不重跑已通过用例。该块放在 0 缩进，`<<'PY'` 的结束行可按原样执行；实测输出 5 行、退出码 0。

## 复核入口

- A/B：`/tmp/pc-stage5/compare-main2.log`（78 条 `OK`）。
- 源码约束（R3）：`/tmp/pc-stage5/source-main2.log`（4 条 `SOURCE ... OK`、`SOURCE CHECKS PASS`）。
- T4：`/tmp/pc-stage5/t4-main2.log`（`Ran 10 tests`、`OK`）。
- T5：`/tmp/pc-stage5/t5-main2.log`（`Ran 2 tests`、`OK`）。
