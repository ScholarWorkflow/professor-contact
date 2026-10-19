# Stage 2 划分第一批：预检、身份与 plan 命令层（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage2-split/implementation-plan.md` 第 3 版（`Plan conclusion: APPROVED`，第 1 版审核通过；第 2/3 版只并入非阻断建议、基线指针与兼容面补记，方案未变）。
- 测试计划：`plan/stage2-split/test-plan.md` 第 3 版（第一关 PASS、第二关 PASS）。
- 被测提交：`5d4fbe07d702104c3aea522245bb566b74b950db`（实现提交，父提交 `d5a4f751fb80de4819d4a1de3ee829db52cea6fc`；重放前为 `d905b93`，patch-id 相同）；其上的 `1807ba4` 只改计划文字。
- 对照基准：`d5a4f751fb80de4819d4a1de3ee829db52cea6fc`（当前 `main`）。实施最初基于 `b5621db`；合并前 main 前进到 `d5a4f75`，`git diff b5621db d5a4f75 -- .apm/skills/professor-contact/scripts/` 为空，实现按同一内容重放。
- 环境：macOS，Python 3.14.7（`python3 --version`），仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage2-p1/`（对比脚本、A/B 输出、套件日志）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 基线有效 | 通过 | 对比脚本 `/tmp/pc-stage2-p1/compare_stage2_preflight.py`（207 行，sha256 `da1639e46a99177c7174c39d0d44a41e9683fd9dc15ef3d2518e3a9503558823`）：`T0` 3 条 `OK`（两侧目录不同、base 仍定义 27 个函数、head 一个都不定义）。 |
| T1 划分完成 | 通过 | 同一脚本 `T1` 71 条 `OK`：27 个函数离开 runner 顶层、进入模块 `build()`；8 个常量改由模块定义、runner 只别名。 |
| T2 逻辑与常量不变 | 通过 | 同一脚本 `T2` 64 条 `OK`：27 个函数的代码 AST 与基准相同（多行 docstring 续行只增加 4 个空格缩进）、8 个常量源代码相同、非搬移顶层定义 AST 不变、runner 正好少了这 27 个定义。 |
| T3 旧接口与加载不变 | 通过 | 同一脚本 `T3` 63 条 `OK`：27 个名字在两侧可调用且 `inspect.signature` 相同、8 个常量值相同、直接执行 `contact_state.py --help` 退出码 0。合计 201 条 `OK`、末尾 `ALL CHECKS PASS`、退出码 0（输出 `/tmp/pc-stage2-p1/ab-final.out`）。 |
| T4 两个命令行为不变 | 通过 | 计划列出的 10 个方法：`Ran 10 tests in 3.033s`、`OK`，无失败、无跳过。 |
| T5 复制夹具加载 | 通过 | 计划列出的 2 个方法：`Ran 2 tests in 1.240s`、`OK`，无失败、无跳过。 |
| 既有仓库检查（非必测） | 通过 | 本地全量（仓库检查记录，非通过条件）：`Ran 1028 tests in 619.494s`、`OK (skipped=1)`。比实施基线 `b5621db` 的 1025 项多 3 项，来自 main 上 #104 新增的 `test_stage1_stage2_contract.py`；跳过数一致。CI：PR #108 在 head `1807ba4` 上 run `39304513602`，`shards (shard1..4)` 全部 pass，聚合 job `test` pass。 |

## 说明

- 本地全量套件只作为仓库检查记录，不作为本批必测项或通过条件（测试计划第 3 版第 4 步）。
- 被测提交的代码内容与提交前在 `/tmp/pc-stage2-p1/treat` 的 A/B 探针一致：runner sha256 `1876912f20732c1f6d254d13e821996e74fb61efd56660bccf99e867bacd9cbc`、模块 sha256 `fdca058fecb85ee337939e4cf91ce07a210f44b536253733215cd5d8322812bd`（重放前后相同）。
- 重放保真：`git patch-id` 对重放前 `d905b93` 与重放后 `5d4fbe0` 相同（`dca0c417cb12237b2d1bf3b475ca2f18fb8f064a`）。
- 无失败、无跳过（T0–T5）；仓库全量套件的 1 个跳过为既有环境跳过项，与基线一致。
