# 邮件核心划分：邮箱条目编译（测试执行记录）

## 版本与对象

- 执行计划：`plan/email-core/implementation-plan.md`（第 2 版，`Plan conclusion: APPROVED`）。
- 测试计划：`plan/email-core/test-plan.md`（第 3 版，第一关 PASS、第二关 PASS）。
- 被测提交：实现提交 `refactor(email): move the email entry compilation into a module`。
- 对照基准：父提交 `3ffdab0`（PR #125 的 head）；命令按 `git rev-parse origin/refactor-shared-helpers` 动态取值。
- 运行目录：仓库外的临时目录（下称 `$RUN`），其中 `base/` 为父提交导出的 `scripts`，`head/` 为工作树的 `scripts` 副本。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | `T0 CHECKS PASS`：`build()` 5 个 keyword-only 参数（无位置参数、`kw_defaults` 全 `None`）、4 个成员；5 个绑定实参均为同名 `Name` 且定义早于绑定调用；4 个别名都是 `_email_core` 的同名属性且运行时 `is` 成立；`1122 < 1130 < 1227 < 1418`；`_stage5_email.build` 12 个参数、全文 0 处 `email_source_hash`；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；3 个名字不再在 runner 顶层定义 |
| T1–T3 结构／AST／接口 | 通过 | 23 条 `OK`（T0 3、T1 7、T2 6、T3 7）、`ALL CHECKS PASS`；`--help` 与父提交逐字节相同（sha256 `d622b7e6…`） |
| T2 docstring | 通过 | `total=3 with_doc=3 multi=2 clean_equal=3 without_doc=0 missing=0 mismatched=0` |
| T3 `email_source_hash` 专项 | 通过 | 定义体 AST 相同；同一 `entry` 两侧哈希均为 `15948fc9…`；runner 别名与模块命名空间是同一对象；签名相同 |
| T4 邮箱编译与选择解析 | 通过 | 7 个方法：`Ran 7 tests`、`OK`；插桩计数 `_selection_direction_ids` 21、`validate_papers_override` 17、`compile_email_entry` 8（7 次单方向 + 1 次跨方向组）、`email_source_hash` 8 |
| T5 复制夹具 | 通过 | `Ran 1 test`、`OK` |
| 失败注入 | 不适用 | 只搬移定义并修正一个无消费方参数，不改事务、回滚、写入顺序、错误通道或 CLI 参数 |
| 既有仓库检查（非必测） | 本地全绿 | 4 个 shard 本地实跑：380／219／188／243 个测试通过（1 个跳过），退出码均为 0；最终以 PR 的 CI 为准 |

## 文件与接缝

- runner：2154 行（父提交 2334 行），sha256 `aeb3ed6c75fdd468b95147e8c4df81e615d2a353d6b06df9cd73b13e36028d79`。
- 新模块：`_email_core.py`，234 行，sha256 `285bd19333bdaf5be3198decb47a4a06561fa53f22eb332862b55019a942e638`。
- `_stage5_email.py`：499 行，sha256 `db15c7bfc973d26cd15667c84ab32cb80332c3c62cc6f8182aa9f3dee7ca9b70`。
- diff：`+26 −213`（普通 `git diff --stat`，只含 2 个已跟踪文件）；`git diff --ignore-blank-lines -U0` 共 7 个 hunk：runner 4 个（加载块、定义删除含绑定块、`_stage5_email` 关键字删除、旧别名删除），`_stage5_email.py` 3 个（签名、定义删除、返回命名空间项删除）。
- 空行：删除后合并出的 6 行与 3 行两处空行块收敛为 2；父提交自带的 6 行块（当前 1584–1589）保持 6 行。

## 说明与偏差

- **为什么本批多改了一个文件**：`compile_email_entry` 末行调用 `email_source_hash`，而该函数原先由 `_stage5_email.build()`（父提交 1595）产出，晚于本批消费方 `_stage4_commands.build()`（1404）。把 `email_source_hash` 一起移入 `_email_core` 后环解开；`_stage5_email` 因此去掉 2 个参数（14→12），不新增参数——审查确认该文件删掉定义与返回项后 0 处引用，再注入会成为无消费方接口。
- **覆盖说明**：`compile_email_entry` 由 8 次调用覆盖（含 1 次 `group_entry` + `participant_directions` 的跨方向组）；`validate_papers_override` 覆盖重复 key 失败分支（`test_06c`），其余三条失败分支未新增用例，理由见测试计划。
- **入口**：`stage4-finalize` 与 `stage4-migrate-local` 都经 `stage4_professor_transaction → _stage4_professor_commit` 到达本批函数；T4 用 finalize 作为足够入口。
- 无测试跳过（shard 级 1 个跳过来自既有用例）；没有改测试、常量值、CLI、入口清单或 Nix 布局。

## 复核入口

测试计划第 1–7 步的命令可直接重跑；日志落在 `$RUN` 下的 `help-base.txt`、`help-head.txt`、`t1-t3.log`、`t4.log`、`t5.log`，插桩证据在副本 `$RUN/wt3` 的 `calls7.log`（工作树源码不含插桩）。
