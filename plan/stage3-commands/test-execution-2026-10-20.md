# Stage 3 划分第二批：plan／finalize／overview 命令（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage3-commands/implementation-plan.md` 第 1 版。
- 测试计划：`plan/stage3-commands/test-plan.md` 第 2 版（第一关 PASS、第二关 PASS）。
- 被测提交：`7539240`（`refactor(stage3): move the plan, finalize and overview commands into a module`，父提交 `1bf44d6` 为计划文档提交，其父为链尾 `e303a1c`）。
- 对照基准：父分支 `refactor-stage3-validation`（#118）的 head `e303a1c`，runner 5565 行；命令里按 `git rev-parse` 动态取值。
- 环境：macOS；`uv run --no-project python` 3.14.6；仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage11/`（`base/` 是父提交导出的 scripts，`blocks/blk0.sh`–`blk5.sh` 是从测试计划原文抽出的命令块，`base-<sha12>/` 是失败对照目录）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：`build()` 56 个 keyword-only 参数（无位置、无默认值）、4 个成员；4 个同名别名；绑定调用与 4 个别名都在 `canonical_professor_dir` 之后；模块不导入 runner（含 from-import 名）、无动态加载、不碰 `sys.path`／`sys.modules`；4 个名字不再在 runner 顶层定义；`py_compile` 与 `--help` 退出码 0（`/tmp/pc-stage11/t0.log`） |
| T1–T3 结构／AST／接口 | 通过 | 28 条 `OK`（T0 3、T1 9、T2 7、T3 9）、`ALL CHECKS PASS`、退出码 0；`--help` 与父提交逐字节相同（`diff -u` 无输出，`/tmp/pc-stage11/compare.log`） |
| T2 docstring | 通过 | 整行摘要 `total=4 with_doc=2 multi=2 clean_equal=2 without_doc=2 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS`（`/tmp/pc-stage11/docstring.log`） |
| T4 Stage 3 命令行为 | 通过 | 10 个方法（全部经 CLI 子进程，覆盖 `stage3-plan`／`stage3-finalize`／`stage3-rebuild-overview` 与 `--refresh-scope selected`）：`Ran 10 tests in 6.411s`、`OK`（`/tmp/pc-stage11/t4.log`） |
| T5 复制夹具加载 | 通过 | 2 个方法：`Ran 2 tests`、`OK`（`/tmp/pc-stage11/t5.log`） |
| 失败注入 | 不适用 | 本批只搬移定义，不改事务、回滚、写入顺序或错误通道 |
| 失败对照（未触发） | 通过（仅块预检） | 本轮没有失败方法；块本身按“单方法 + 按 SHA 建目录 + 时间戳日志”实现 |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 4 个 `shards` 与聚合 `test` 的运行编号 |

## 文件与接缝

- 被测 runner：`.apm/skills/professor-contact/scripts/contact_state.py`，4712 行，sha256 `efe616f46d9d76d6baf6e5781be9b898c157169411ded78f6f135b1d91a5c0d0`。
- 新模块：`.apm/skills/professor-contact/scripts/_stage3_commands.py`，1013 行，sha256 `e6538849fd4b454a4376a9cc2551ec177b71c22c4c61a0b1f41891e43d5721e0`（4 个成员，`build()` 56 个 keyword-only 参数）。
- 代码 diff（`e303a1c` → 工作树）：runner `+78 −931`。
- `git diff --ignore-blank-lines -U0` 共 5 个 hunk：加载块、四段定义删除、绑定块。
- 空行：删除后合并出的两处（4 行、7 行）收敛为 2；父提交自带的 3 行（约 1771）与 6 行（约 3939）保持原尺寸。

## 说明与偏差

- **绑定点位置**：`_stage3_selected_scope_keys` 依赖 `canonical_professor_dir`（2624 行，Stage 4 共享 helper），所以绑定块必须放在它之后，位置落在 Stage 4 代码区间内；四个别名在 `main()` 运行前建立即可，不影响行为。等共享层再把 `canonical_professor_dir` 搬走，这个绑定点可以随之前移。
- **56 个注入参数**是本项目最多的一批：Stage 2 六个模块别名、第一批校验管线 9 个别名、仍在 runner 的 6 个 helper。
- **覆盖说明**：`validate_candidate_result`／`validate_cross_result`／`render_candidates_md`／`render_candidates_overview`／`_stage3_args_from_invocation` 仍留在 runner，本批按引用注入，属后续批次。
- 无测试跳过；没有改测试、常量值、CLI、入口清单或 Nix 布局。

## 复核入口

- T0：`/tmp/pc-stage11/blocks/blk0.sh`（5 条 `T0 ... OK` + `T0 CHECKS PASS`）。
- T1–T3：`/tmp/pc-stage11/blocks/blk1.sh`（`diff` 无输出 + 28 条 `OK`）。
- docstring：`/tmp/pc-stage11/blocks/blk2.sh`（整行摘要 + `DOCSTRING CHECKS PASS`）。
- T4：`/tmp/pc-stage11/blocks/blk3.sh`（`Ran 10 tests`、`OK`）。
- T5：`/tmp/pc-stage11/blocks/blk4.sh`（`Ran 2 tests`、`OK`）。
- 失败对照（未触发）：`/tmp/pc-stage11/blocks/blk5.sh`（单方法、按 SHA 建目录）。
