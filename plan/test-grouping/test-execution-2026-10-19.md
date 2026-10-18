# 测试分组与 CI 分片 测试执行记录（2026-10-19）

- 测试计划：[test-plan.md](test-plan.md)，第 2 版。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 2 版（`Plan conclusion: APPROVED`）。
- 对照基准：`6e624e0`（`origin/main`）。
- 被测提交：`fd3ea8d`（实现提交；其后如仅改文档，产品与测试字节不变）。
- 环境：本地 macOS／Python 3.14.7；CI 为 ubuntu-latest／Python 3.12。原始输出（仓库外）：`/tmp/pc-tg-check/`（四片日志 `shard1.log`…`shard4.log`、墙钟 `shards.txt`）；分组测量产物 `/tmp/pc-tg-map.json`、`/tmp/pc-tg-timing.clean.json`。

## 逐项结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | 正确清单：退出码 0 且 stdout 为 `OK: 78 test modules across 4 shards`；四种坏清单逐例断言错误子串——`missing` → 1／`ERROR: not covered by any shard: test_contact_state`、`duplicate` → 1／`ERROR: test_contact_state listed in both shard1 and shard2`、`nonexistent` → 1／`ERROR: shard3: no such test module: test_does_not_exist.py`、`empty_shard` → 1／`ERROR: shard4 lists no modules`；恢复后再次退出 0，`git diff --exit-code -- plan/test-grouping/shards.json` 无输出（日志 `/tmp/pc-tg-check/t1-injections.log`） |
| T2 | 通过 | 四片各自 `OK`（其中一片 `OK (skipped=1)`）；四片 `Ran` 之和 = **1025**，与 `countTestCases()` 的 1025 一致；无重复执行 |
| T3 | 通过 | 工作流含 `fail-fast: false`、`matrix.shard: [shard1..shard4]`、每片先 `python scripts/check_test_shards.py` 再从 `tests/` 跑本片；聚合任务 `needs: [shards]`、`if: always()`、`needs.shards.result != "success"` 即失败 |
| T4 | 通过 | 四片命令都在本地独立跑通，互不依赖；墙钟 shard1 121s、shard2 129s、shard3 122s、shard4 124s |
| T5 | 待补 | 推送到 PR 后引用 CI 运行编号、所跑 head 与各检查状态（4 个 `shards (shardN)` + 聚合 `test`），不作为本批业务必测项 |

## 执行方法与命令

1. 覆盖校验与四种坏清单注入（片段见测试计划第 2 步，含 `try/finally` 与逐例错误子串断言）：正确 → 0（stdout 含 `OK: 78 test modules across 4 shards`）；漏归类 → 1（`not covered by any shard`）；重复 → 1（`listed in both`）；不存在 → 1（`no such test module`）；空分片 → 1（`lists no modules`）；恢复 → 0。
2. 逐片运行（从 `tests/` 目录，模块列表由 `--print` 提供）：

   ```sh
   set -e
   for shard in shard1 shard2 shard3 shard4; do
     modules=$(python3 scripts/check_test_shards.py --print "$shard")
     start=$(date +%s)
     (cd .apm/skills/professor-contact/tests && python3 -m unittest $modules) | tail -3
     echo "$shard wall=$(( $(date +%s) - start ))s"
   done
   ```

   输出（`/tmp/pc-tg-check/`）：shard1 121s、shard2 129s、shard3 122s、shard4 124s；四片合计 1025 项全过。
3. 工作流结构核对：`grep -n "fail-fast\|matrix\|needs:\|if: always\|needs.shards.result" .github/workflows/ci.yml`。
4. 分组与耗时测量（执行计划事实表的来源，仓库外一次性脚本）：
   - `uv run --no-project <主检出>/.tmp_scripts/1020_test_stage_map2.py <worktree>/.apm/skills/professor-contact/tests` → 156 类 / 1033 方法（stage3 347、无信号 250、stage2 239、stage4 143、stage5 29、stage1 23、混合 2）；
   - `uv run --no-project <主检出>/.tmp_scripts/1020_time_tests.py <worktree>/.apm/skills/professor-contact/tests` → `Ran 1025 tests in 416.2s`、`OK (skipped=1)`；前 5 模块 215s、其余 73 模块 201s；
   - 分片按模块耗时降序贪心装箱，四片各 104.0s。

## 执行中修正的问题（保留记录）

- 第一版测量取自主检出（旧修订 `74bd29b`），与声明的目标 `6e624e0` 不符（计划审核 B1 指出）：在目标修订的 worktree 上重跑两个脚本，数字改为 1025 项 / 416.2s / 156 类 / 1033 方法 / stage5 29，并写明两个计数口径与脚本重名键限制。
- 计时脚本的 stdout 混入了某个用例打印的 JSON，直接 `json.loads` 会失败：改为从最后一个 `{"total_seconds"` 起解析（`/tmp/pc-tg-timing.clean.json`）。
- 测试计划第 1 版审核指出 T1 只比退出码、验不到自己声明的 `ERROR:` 行（任何其它失败也会非零退出）：改为逐例断言错误子串，并补“某片置空”这一注入；重跑后四种注入都命中各自消息。
- 计时口径差异：`shards.json` 的 104.0s 是各模块测试耗时之和，本地分片墙钟 121–129s 还包含 discover/导入开销（最大/最小 ≈ 1.06），两个数字不矛盾。
- 以上属测量与测试资产问题，产品与测试代码未改。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在本 PR 上跑 4 个分片与聚合任务；结果按运行编号与所跑 head 记录。

## 结论与交接

- T1–T4 对被测提交取得有效通过结果；T5（既有仓库检查）待 PR 打开后补运行来源。
- 本记录之后如只改文档，未改工作流、脚本与测试代码时，上述逐项结果继续有效并沿用。
- 依赖顺序：本批从 `main` 拉出，与批次二/三、边界一至四的在途 PR 无依赖关系，可独立合并。
- 下一负责人：测试计划审核（第一、二关口）、第三关口与合并审核；本记录不代替任何关口结论。
