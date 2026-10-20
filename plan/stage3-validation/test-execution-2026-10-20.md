# Stage 3 划分第一批：校验与报告管线（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage3-validation/implementation-plan.md` 第 2 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/stage3-validation/test-plan.md` 第 2 版（第一关 PASS、第二关待审核）。
- 被测提交：`90bab60`（`refactor(stage3): move the validation and reporting pipeline into a module`，父提交 `316e6a1` 为计划文档提交，其父为链尾 `6ff8549`）。
- 对照基准：父分支 `refactor-input-pack`（#117）的 head `6ff8549`，runner 6367 行；命令里按 `git rev-parse` 动态取值。
- 环境：macOS；`uv run --no-project python` 3.14.6；仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage10/`（`base/` 是父提交导出的 scripts，`blocks/blk0.sh`–`blk5.sh` 是从测试计划第 2 版原文抽出的命令块，`base-<sha12>/` 是失败对照的基准目录）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：`build()` 36 个 keyword-only 参数、18 个成员；18 个同名别名且集合与成员一致；绑定调用与 18 个别名都早于 `cmd_stage3_plan`；模块不导入 runner（含 from-import 名）、无动态加载、不碰 `sys.path`／`sys.modules`；18 个名字不再在 runner 顶层定义；`py_compile` 与 `--help` 退出码 0（`/tmp/pc-stage10/t0.log`） |
| T1–T3 结构／AST／接口 | 通过 | 98 条 `OK`（T0 3、T1 37、T2 21、T3 37）、`ALL CHECKS PASS`、退出码 0；`--help` 与父提交逐字节相同（`diff -u` 无输出，`/tmp/pc-stage10/compare.log`） |
| T2 docstring | 通过 | 整行摘要 `total=18 with_doc=16 multi=13 clean_equal=16 without_doc=2 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS`（`/tmp/pc-stage10/docstring.log`） |
| T4 校验管线行为 | 通过 | 10 个方法（9 个经 CLI、1 个直接调用 `_stage3_bound_render`）：`Ran 10 tests in 10.250s`、`OK`，无失败、无跳过（`/tmp/pc-stage10/t4.log`） |
| T5 复制夹具加载 | 通过 | 2 个方法：`Ran 2 tests`、`OK`（`/tmp/pc-stage10/t5.log`） |
| 失败注入 | 不适用 | 本批只搬移定义，不改事务、回滚、写入顺序或错误通道 |
| 失败对照（未触发） | 通过（仅块预检） | 本轮没有失败方法，按示例方法验证脚本可执行：`Ran 1 test`、`OK`，日志写在 `/tmp/pc-stage10/base-<父提交 SHA 前 12 位>/` 目录内（与 SHA 绑定、按方法短名 + 时间戳命名） |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 4 个 `shards` 与聚合 `test` 的运行编号；不作为通过条件 |

## 文件与接缝

- 被测 runner：`.apm/skills/professor-contact/scripts/contact_state.py`，5565 行，sha256 `ddf48cdaf6b8aaebbfbebe066eeeccdcdcdc11ff6ceacca861f43b6467d53fb2`。
- 新模块：`.apm/skills/professor-contact/scripts/_stage3_validation.py`，922 行，sha256 `dd7dc863213ea76f3dda515d73152c02b9909833a404864244fcafd0752f6318`（18 个成员，`build()` 36 个 keyword-only 参数；import 只有 `Path`／`Any`／`json`／`os`／`sys`／`tempfile`／`types`）。
- 代码 diff（`6ff8549` → 工作树）：runner `+70 −872`（`git diff --numstat`）。
- `git diff --ignore-blank-lines -U0` 共 8 个 hunk：加载块、六段定义删除、绑定块。
- 空行：删除 18 个定义后合并出两处大块（24 行与 20 行）收敛为 2；删除段外的两处（3 行、6 行）保持原尺寸；删除段内的三处（983–986、1024–1027、1564–1573）随定义进入模块。

## 说明与偏差

- **演练首轮漏测**：初版 T4 只覆盖 `record-validation`，没有触发 `prepare`／`write`／`save-validation`，因此模块缺 `os`／`sys`／`tempfile` 三个 import 也没被发现。第一关指出“T4 覆盖声明与日志不符”后换成 8 个 handoff／recorded-scope 方法，立刻报 `NameError: name 'os' is not defined`；补齐 import 后 T4 全绿。这条已写进两份计划的修订记录。
- **删除范围**：967–1742 不是连续删除区间，里面还夹着第二批判据 `_stage3_selected_scope_keys`（1234–1287）与三个要注入的常量（1175–1176、1177–1178、1328–1331）；实施按 18 个 AST 定义删除、6 个外层分组。
- **工具**：仍用 `extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`）生成、再手工收敛两处合并空行；对比脚本 `compare_stage2_batch_v2.py`（94 行，`1ba8c0f4…`）、docstring 脚本 `check_docstrings_v3.py`（109 行，`31c8b208…`）。v5／v6 的“删除处自动收敛”版本在早前批次吃过 `__main__` 块的亏，本批未用。
- **覆盖限制**：`carry_stage3_validator`、`stage3_current_result`、`require_stage3_correction_invariants`、`_paper_refs`、`_stage3_candidates_entry` 没有直接对应用例，经 record→`stage3_validation_evidence`、plan/finalize 的间接路径覆盖，T2 的 AST 等价作为兜底。
- 无测试跳过；没有改测试、常量值、CLI、入口清单或 Nix 布局。

## 复核入口

- T0：`/tmp/pc-stage10/blocks/blk0.sh`（5 条 `T0 ... OK` + `T0 CHECKS PASS`）。
- T1–T3：`/tmp/pc-stage10/blocks/blk1.sh`（`diff` 无输出 + 98 条 `OK`）。
- docstring：`/tmp/pc-stage10/blocks/blk2.sh`（整行摘要 + `DOCSTRING CHECKS PASS`）。
- T4：`/tmp/pc-stage10/blocks/blk3.sh`（`Ran 10 tests`、`OK`）。
- T5：`/tmp/pc-stage10/blocks/blk4.sh`（`Ran 2 tests`、`OK`）。
- 失败对照（未触发）：`/tmp/pc-stage10/blocks/blk5.sh`（单方法、日志进 `base-<sha12>/`）。
