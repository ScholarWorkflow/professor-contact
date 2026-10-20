# Stage 5 划分第一批：输入发现与候选选择（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage5-input/implementation-plan.md` 第 4 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/stage5-input/test-plan.md` 第 5 版（第一关 PASS、第二关 PASS）。
- 被测提交：`2e89102`（`refactor(stage5): move input discovery and candidate selection into a module`，父提交 `500c8d1` 为计划文档提交，其父为链尾 `f8be30d`）。
- 对照基准：父分支 `refactor-stage3-commands`（#119）的 head `f8be30d`，runner 4712 行；命令里按 `git rev-parse` 动态取值。
- 环境：macOS；`uv run --no-project python` 3.14.6；未新增依赖。
- 运行目录：`/tmp/pc-stage12/`（`base/` 为父提交导出的 scripts，`blocks/blk0.sh`–`blk5.sh` 为从测试计划原文抽出的命令块）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：`build()` 11 个 keyword-only 参数（无位置、无默认值）、13 个成员；13 个同名别名；绑定调用与 13 个别名都早于 `cmd_stage5_plan`；模块不导入 runner（含 from-import 名）、无动态加载、不碰 `sys.path`／`sys.modules`；13 个名字不再在 runner 顶层定义（`/tmp/pc-stage12/t0.log`） |
| T1–T3 结构／AST／接口 | 通过 | 73 条 `OK`（T0 3、T1 27、T2 16、T3 27）、`ALL CHECKS PASS`；`--help` 与父提交逐字节相同（`/tmp/pc-stage12/compare.log`） |
| T2 docstring | 通过 | 整行摘要 `total=13 with_doc=10 multi=10 clean_equal=10 without_doc=3 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS`（`/tmp/pc-stage12/docstring.log`） |
| T4 输入发现与计划路径 | 通过 | 10 个方法（3 个 `stage5-list-inputs`、7 个经 `stage5-plan`，其中 3 个另调 `stage5-finalize`）：`Ran 10 tests in 4.5s`、`OK`（`/tmp/pc-stage12/t4.log`） |
| T5 复制夹具加载 | 通过 | 2 个方法：`Ran 2 tests`、`OK`（`/tmp/pc-stage12/t5.log`） |
| 失败注入 | 不适用 | 本批只搬移定义，不改事务、回滚、写入顺序、错误通道或 CLI 参数 |
| 失败对照（未触发） | 通过（仅块预检） | 单方法 `Ran 1 test`、`OK`，日志按 SHA 建目录、按方法短名 + 时间戳命名 |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 CI 运行编号 |

## 文件与接缝

- 被测 runner：`.apm/skills/professor-contact/scripts/contact_state.py`，4237 行，sha256 `9c0873994b1a294e09319377319f9ee68a84d1d0b492e950fedafd9e4f450c7b`。
- 新模块：`.apm/skills/professor-contact/scripts/_stage5_input.py`，553 行，sha256 `d8c7858301d432226ae3fce73162d31f9fe422d6496885b0345f46405b9ed1b9`（13 个成员，`build()` 11 个 keyword-only 参数）。
- 代码 diff（`f8be30d` → 工作树）：runner `+40 −515`。
- `git diff --ignore-blank-lines -U0` 共 4 个 hunk：加载块、两段定义删除（409–461 与 2386–2846 各一段，后者在 diff 里被拆成两块）、绑定块。
- 空行：删除后合并出的三处（8 行、20 行、3 行）收敛为 2；父提交自带的两处（3 行 @1771–1773、6 行 @3939–3944）保持原尺寸。

## 说明与偏差

- **覆盖限制**：`stage5_partition_pack_spec` 与 `cmd_stage5_partition_choices`（202 行）没有既有行为用例（`grep -rn "stage5-partition-choices" tests` 为空），只有 T1–T3 的结构等价覆盖；要补用例需要验收决定人批准。
- **归属修正**（审核 B1／B2 指出）：`stage5_partition_pack_spec` 只服务本批的 partition 命令，不是 `cmd_stage5_plan`／第二批的依赖；`stage5_output_*` 的使用方是 `cmd_stage5_finalize` 与仍留在 runner 的 `humanized_paths`，`record_validation` 不引用它们。
- **模板文案**：提取器默认生成“Stage-2 helper module”，已改成本批的“Stage-5 helper module”（模块 docstring 与 runner 加载块注释）。
- 无测试跳过；没有改测试、常量值、CLI、入口清单或 Nix 布局（Nix 用 `cp -R` 递归复制 scripts，新模块无需改布局）。

## 复核入口

- T0：`/tmp/pc-stage12/blocks/blk0.sh`
- T1–T3：`/tmp/pc-stage12/blocks/blk1.sh`
- docstring：`/tmp/pc-stage12/blocks/blk2.sh`
- T4：`/tmp/pc-stage12/blocks/blk3.sh`
- T5：`/tmp/pc-stage12/blocks/blk4.sh`
- 失败对照（未触发）：`/tmp/pc-stage12/blocks/blk5.sh`
