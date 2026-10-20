# Stage 4 划分：最终写入与迁移（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage4/implementation-plan.md` 第 2 版。
- 测试计划：`plan/stage4/test-plan.md` 第 2 版（第一关 PASS）。
- 被测提交：`4a425cd`（`refactor(stage4): move the selection commit and migration commands into a module`，父提交 `a722c11` 为计划文档提交，其父为链尾 `8c4b363`）。
- 对照基准：父分支 `refactor-stage5-commands`（#121）的 head `8c4b363`，runner 3668 行。
- 运行目录：`/tmp/pc-stage14/`（`base/` 为父提交导出，`blocks/` 为测试计划命令块，`logs/base-<sha12>/` 为失败对照日志）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：27 个 keyword-only 参数（无位置、无默认值）、10 个成员、10 个同名别名、绑定晚于常量 `STAGE4_MIGRATION_COMMITTED`、模块源码约束、10 个名字不再在 runner 顶层 |
| T1–T3 | 通过 | 58 条 `OK`（T0 3、T1 21、T2 13、T3 21）、`ALL CHECKS PASS`；`--help` 与父提交逐字节相同 |
| T2 docstring | 通过 | `total=10 with_doc=9 multi=6 clean_equal=9 without_doc=1 missing=0 mismatched=0` |
| T4 Stage 4 命令行为 | 通过 | 10 个方法（7 个经 `stage4-finalize`、2 个经 `stage4-migrate-local`、1 个两者都跑）：`Ran 10 tests in 4.662s`、`OK` |
| T5 复制夹具 | 通过 | `Ran 2 tests`、`OK` |
| 失败注入 | 不适用 | 只搬移定义，不改事务、回滚、写入顺序、错误通道或 CLI 参数 |
| 失败对照（未触发） | 通过（块预检） | 单方法 `Ran 1 test`、`OK`，日志在 `/tmp/pc-stage14/logs/base-<sha12>/` |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 CI 运行编号 |

## 文件与接缝

- runner：3204 行，sha256 `862cd90762957782ebd6ba3cdeb73861d8995ee5a3c964de746f975a9a6882a2`。
- 新模块：`_stage4_commands.py`，569 行，sha256 `3ef0449aa9221b2c2b6e4fc2d2706cd379540ede42e56f11f3c8cfdbc91354bf`，import 为 `from __future__ import annotations`、`Path`、`Any`、`sys`、`types`（`json` 未被引用，已去掉）。
- diff：`+53 −517`；`git diff --ignore-blank-lines -U0` 共 5 个 hunk。
- 空行：probe 里合并出的 4／6／13／4 四块与别名块后的 3 行全部收敛为 2；父提交的 6 行块（@2895–2900）保留；父提交的 3 行（@1740–1742）随 `stage4_professor_row` 删除并入 13 行块、未单独保留。
- `STAGE4_MIGRATION_COMMITTED` 因中间定义删除从 2077 重排到 1647，diff 显示为删+增、内容未变。

## 说明与偏差

- **T4 初版有两个问题**：一是 3 个方法不跑 CLI（`build_parser` 断言、两份文档契约），二是没有任何方法覆盖 `stage4-migrate-local`。第一关指出后换成 3 个 `Issue67ProfessorLocalStage4Tests` 方法，覆盖 migrate 的成功与两条失败路径。
- **空行事实修正**：初版计划写“父提交的 3 行 @1740–1742 保持原尺寸”，与演练冲突（它被并入 13 行块后收敛）。已改为按位置而不是按尺寸描述，并注明别把别名块后那块 3 行误当成保留项。
- **取舍**：`canonical_professor_dir` 与 `profile_fingerprint` 是跨 stage 共享 helper，继续按引用注入，不搬进 Stage 4 模块。

## 复核入口

- T0：`/tmp/pc-stage14/blocks/blk0.sh`；T1–T3：`blk1.sh`；docstring：`blk2.sh`；T4：`blk3.sh`；T5：`blk4.sh`；失败对照：`blk5.sh`。
