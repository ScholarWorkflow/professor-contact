# Stage 5 划分第三批：邮件组装与渲染（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage5-email/implementation-plan.md` 第 2 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/stage5-email/test-plan.md` 第 2 版（第一关 PASS）。
- 被测提交：`0abf9d0`（`refactor(stage5): move the email assembly and rendering helpers into a module`，父提交 `060d2ae` 为计划文档提交，其父为链尾 `4a1138a`）。
- 对照基准：父分支 `refactor-migrate`（#123）的 head `4a1138a`，runner 3013 行。
- 运行目录：`/tmp/pc-stage16/`（`base/` 为父提交导出，`blocks/` 为命令块，`logs/base-<sha12>/` 为失败对照日志）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：14 个 keyword-only 参数、22 个成员、22 个同名别名、绑定在 `DEFAULT_ALMA_MATER` 之后且早于 `_stage5_commands` 的 build、模块源码约束、22 个名字不再在 runner 顶层 |
| T1–T3 | 通过 | 118 条 `OK`（T0 3、T1 45、T2 25、T3 45）、`ALL CHECKS PASS`；`--help` 与父提交逐字节相同 |
| T2 docstring | 通过 | `total=22 with_doc=5 multi=2 clean_equal=5 without_doc=17 missing=0 mismatched=0` |
| T4 邮件组装与渲染 | 通过 | 10 个方法（9 个 `TestStage5` + 1 个 `TestStage5TargetedEmailScope`）：`Ran 10 tests in 5.214s`、`OK` |
| T5 复制夹具 | 通过 | `Ran 2 tests`、`OK` |
| 失败注入 | 不适用 | 只搬移定义，不改事务、回滚、写入顺序、错误通道或 CLI 参数 |
| 失败对照（未触发） | 通过（块预检） | 单方法 `Ran 1 test`、`OK`，日志在 `/tmp/pc-stage16/logs/base-<sha12>/` |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 CI 运行编号 |

## 文件与接缝

- runner：2601 行，sha256 `61229bff69b797601b8db45da2b82a8ee1bcecd6e91452239a710b588e0926fd`。
- 新模块：`_stage5_email.py`，506 行，sha256 `ebb1308af8813ecd2e9e13fb37d243a57261b06eab43ab37ccd35972925d5ef3`。
- diff：`+52 −464`；`git diff --ignore-blank-lines -U0` 共 7 个 hunk。
- 空行：probe 里合并出的 4／16／4／16／12 五块收敛为 2；父提交的 6 行块（@2443–2448）保留。

## 说明与偏差

- **依赖环**：本批排除 `compile_email_entry`／`_selection_direction_ids`／`validate_papers_override`／`assemble_followup_draft`。前三个被 `_stage4_commands` 的 build（1664）消费、最后一个被 `_stage5_commands` 的 build（2352）消费，而本模块的 `humanized_paths` 等又依赖那些命令模块产出的别名——一起搬会在导入期 `NameError`（演练已验证：含 `compile_email_entry` 的版本在 1497 行报错）。
- **spec 自动推导**：这批的 spec 由脚本从 AST 推导（函数名 → 自由名 → 参数、import、绑定点取最晚依赖行号），避开手写容易出现的三类错：漏 `types`、带未使用 import、把已搬走的名字写进入参。
- **T4 换方法**：第一关指出 3 个方法在组装/渲染前就结束（template_error、choices 装载、verify 门禁），已换成 `choices_cannot_replace`、`first_allows_missing_initial_sent_date`、`issue59_t59_5`。

## 复核入口

- T0：`/tmp/pc-stage16/blocks/blk0.sh`；T1–T3：`blk1.sh`；docstring：`blk2.sh`；T4：`blk3.sh`；T5：`blk4.sh`；失败对照：`blk5.sh`。
