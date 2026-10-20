# Stage 5 划分第二批：计划、终稿与概览命令（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage5-commands/implementation-plan.md` 第 3 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/stage5-commands/test-plan.md` 第 3 版（第一关 PASS、第二关待审核）。
- 被测提交：`9fe2385`（`refactor(stage5): move the plan, finalize and record commands into a module`，父提交 `78ed422` 为计划文档提交，其父为链尾 `ce46f36`）。
- 对照基准：父分支 `refactor-stage5-input`（#120）的 head `ce46f36`，runner 4237 行。
- 运行目录：`/tmp/pc-stage13/`（`base/` 为父提交导出，`blocks/` 为测试计划命令块，`logs/base-<sha12>/` 为失败对照日志）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：51 个 keyword-only 参数（无位置、无默认值）、5 个成员、5 个同名别名、绑定晚于 `render_fact_check_card`、模块源码约束、5 个名字不再在 runner 顶层 |
| T1–T3 | 通过 | 33 条 `OK`（T0 3、T1 11、T2 8、T3 11）、`ALL CHECKS PASS`；`--help` 与父提交逐字节相同 |
| T2 docstring | 通过 | `total=5 with_doc=2 multi=2 clean_equal=2 without_doc=3 missing=0 mismatched=0` |
| T4 Stage 5 命令行为 | 通过 | 10 个方法（plan 9 个、finalize 8 个、rebuild-overview 2 个、record-validation 2 个覆盖）：`Ran 10 tests in 5.912s`、`OK` |
| T5 复制夹具 | 通过 | `Ran 2 tests`、`OK` |
| 失败注入 | 不适用 | 只搬移定义，不改事务、回滚、写入顺序、错误通道或 CLI 参数 |
| 失败对照（未触发） | 通过（块预检） | 单方法 `Ran 1 test`、`OK`，日志在 `/tmp/pc-stage13/logs/base-<sha12>/` |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 CI 运行编号 |

## 文件与接缝

- runner：3668 行，sha256 `f1a8775b36511600e924ad7cbf04aa6d9a741bba1b6c836b56c8f2c2738c7e8e`。
- 新模块：`_stage5_commands.py`，716 行，sha256 `8485e9ff0de20a357de55fc568a7ccfbb324688076f52eaa13b4fb7baf0ce5e8`。
- diff：`+72 −641`；`git diff --ignore-blank-lines -U0` 共 5 个 hunk。
- 空行：probe 3679 行、合并块 4／4／9，三处收敛为 2（3679−11=3668）；父提交自带的 3 行与 6 行保持原尺寸。

## 说明与偏差

- **`types` 与 `re` 两个 import**：`re` 在 `cmd_stage5_finalize` 里直接使用；`types` 是 `build()` 返回 `SimpleNamespace` 所需、不在被搬定义里，AST 扫描抓不到。演练时先漏 `re`、补上后又漏 `types`，两次都靠 T4 与 `--help` 抓出来。
- **模块 import** 最终为 `from __future__ import annotations`、`Path`、`json`、`re`、`types`。
- **T4 方法替换**：初版 10 个里有 4 个只跑 Stage 3 命令，第一关指出后换成 4 个真正驱动本批命令的方法，并用更新后的命令重跑。
- **失败处理日志**：从 `$BASELINE/logs/` 移到 `$BASELINE` 之外，避免 guard 分支的 `rm -rf` 删掉日志。

## 复核入口

- T0：`/tmp/pc-stage13/blocks/blk0.sh`；T1–T3：`blk1.sh`；docstring：`blk2.sh`；T4：`blk3.sh`；T5：`blk4.sh`；失败对照：`blk5.sh`。
