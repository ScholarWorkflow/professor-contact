# Stage 2 划分第二批：resolve 计划层（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage2-resolve/implementation-plan.md` 第 2 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/stage2-resolve/test-plan.md` 第 3 版（第一关 PASS、第二关 PASS）。
- 被测提交：`2ecdc9c95e44ab666f871387fff6d2a6d16444b8`（实现提交；父提交 `8a7bc39`，其上为计划/测试计划 docs 提交；实现基线 `d5a4f751fb80de4819d4a1de3ee829db52cea6fc`）。
- 环境：macOS，Python 3.14.7；仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage2-r2/`。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 基线有效 | 通过 | 对比脚本 `/tmp/pc-stage2-r2/compare_stage2_resolve.py`（196 行，sha256 `a7abca43d3034a060baebf9bc1a928f81bf6dc22f3c5fc12141b7577edb97854`）：T0 3 条 OK。 |
| T1 划分完成 | 通过 | 同一脚本 T1 47 条 OK：16 个函数离开 runner 顶层、进入模块 `build()`；7 个常量改由模块定义、runner 只别名。 |
| T2 逻辑与常量不变 | 通过 | 同一脚本 T2 41 条 OK：16 个函数代码 AST 等价（docstring 续行只增加缩进）、7 个常量源码相同、非搬移顶层定义不变。 |
| T3 旧接口与加载不变 | 通过 | 同一脚本 T3 40 条 OK：16 个名字可调用且签名相同、7 个常量值相同、直接执行 `--help` 退出码 0。合计 131 条 OK、`ALL CHECKS PASS`、exit 0。 |
| T4 计划层行为不变 | 通过 | 测试计划列出的 9 个方法：`Ran 9 tests in 3.737s`、`OK`，无失败、无跳过。 |
| T5 复制夹具加载 | 通过 | 测试计划列出的 2 个方法：`Ran 2 tests in 1.356s`、`OK`，无失败、无跳过。 |
| 既有仓库检查（非必测） | 通过 | PR #109 在 head `e5b8d4e` 上 run `39311872947`：`shards (shard1..4)` 全部 pass，聚合 job `test` pass；本地不把全量套件列为必测项。 |

## 重放说明

- 本批最初基于 `d5a4f75`；合并前 main 先合入第 1 批（`e973ffb`，PR #108），本批已重放到 `e973ffb`。
- 重放后重跑：A/B 对比以 `e973ffb` 为基准，131 条 `OK`、`ALL CHECKS PASS`；T4 `Ran 9 tests in 4.925s OK`、T5 `Ran 2 tests in 1.808s OK`。
- 跨批顺序：本批 build 调用在新树 2211 行，第 1 批 build 在 2542 行，本批别名早于第 1 批 build；第 1 批注入的 `_resolve_evidence` 指向本批同一函数对象。

## 说明

- 实现提交的代码内容：runner 11181 行（sha256 `d331b7d6…`）、模块 806 行（sha256 `5384dfb2…`）。
- 按 M2 复核 B1 恢复的 19 个无关空行不属于搬移逻辑；T0–T3 的 AST 对比与 T4/T5 的结果在该修正后重跑，全部通过。
- 无可用的“27 functions”标签残留：脚本已改为“16 functions”。
