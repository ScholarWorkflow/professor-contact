# 迁移命令划分：migrate-v3 的计划与执行（测试执行记录）

## 版本与对象

- 执行计划：`plan/migrate/implementation-plan.md` 第 2 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/migrate/test-plan.md` 第 1 版（第一关审核中）。
- 被测提交：`d5fb458`（`refactor(migrate): move the migrate-v3 commands into a module`，父提交 `2f73c3b` 为计划文档提交，其父为链尾 `2c81bae`）。
- 对照基准：父分支 `refactor-stage4`（#122）的 head `2c81bae`，runner 3204 行。
- 运行目录：`/tmp/pc-stage15/`（`base/` 为父提交导出，`blocks/` 为命令块，`logs/base-<sha12>/` 为失败对照日志）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：16 个 keyword-only 参数（无位置、无默认值）、4 个成员、4 个同名别名、绑定晚于 `apply_ready_entry`、模块源码约束、4 个名字不再在 runner 顶层 |
| T1–T3 | 通过 | 28 条 `OK`（T0 3、T1 9、T2 7、T3 9）、`ALL CHECKS PASS`；`--help` 与父提交逐字节相同 |
| T2 docstring | 通过 | `total=4 with_doc=0 multi=0 clean_equal=0 without_doc=4 missing=0 mismatched=0`（4 个定义在基线里都没有 docstring） |
| T4 迁移命令行为 | 通过 | 6 个 `TestMigrate` 方法（4 个只走 `--plan`、2 个 `--plan` 与 `--apply` 都走）：`Ran 6 tests in 0.655s`、`OK` |
| T5 复制夹具 | 通过 | `Ran 2 tests`、`OK` |
| 失败注入 | 不适用 | 只搬移定义，不改事务、回滚、写入顺序、错误通道或 CLI 参数 |
| 失败对照（未触发） | 通过（块预检） | 单方法 `Ran 1 test`、`OK`，日志在 `/tmp/pc-stage15/logs/base-<sha12>/` |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 CI 运行编号 |

## 文件与接缝

- runner：3013 行，sha256 `4c811fd3c36c44266556f77c1209855f861d48e806bfbc36226bf54208e16883`。
- 新模块：`_migrate_commands.py`，270 行，sha256 `1fddbdb805c3c177635fc0e206047ee3214635d22570f8c39a016bbf6b75297b`。
- diff：`+37 −228`；`git diff --ignore-blank-lines -U0` 共 4 个 hunk。
- 空行：probe 里合并出的 4／6／3 三块收敛为 2；父提交的 6 行块（@2431–2436）保留。

## 说明与偏差

- **T4 只有 6 个方法**：仓库里驱动迁移命令的测试总共 6 个，全部在 `TestMigrate`。没有为了凑数加入不相关的测试；两个命令（`--plan`／`--apply`）都有行为覆盖。
- **`migrate-v3` 的接线**：`set_defaults(func=lambda a: cmd_migrate_plan(a) if a.plan and not a.apply else cmd_migrate_apply(a))` 在 `build_parser()` 时只创建 lambda，真正调用在 `main()`，那时别名已建立。
- **`types` import**：`build()` 返回 `SimpleNamespace` 需要它，不在 4 个定义的自由名里，靠 AST 扫描发现不了——已在计划的风险与步骤里写明。

## 复核入口

- T0：`/tmp/pc-stage15/blocks/blk0.sh`；T1–T3：`blk1.sh`；docstring：`blk2.sh`；T4：`blk3.sh`；T5：`blk4.sh`；失败对照：`blk5.sh`。
