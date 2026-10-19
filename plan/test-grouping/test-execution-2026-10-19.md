# 测试分组与 CI 分片 测试执行记录（2026-10-19）

- 测试计划：[test-plan.md](test-plan.md)，第 5 版。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 4 版（第 2 版取得 `Plan conclusion: APPROVED`；第 3、4 版按审核意见修正归类与分配）。
- 对照基准：`b5621db`（`origin/main`，已含批次三、边界一/二/三与边界四的合并；本批再次改基到此）；最初的分组与计时测量在 `6e624e0` 上完成，改基后模块集合未变（仍 78 个 `test_*.py`）。
- 被测提交：`fd3ea8d`（最初的实现提交）；改基到 `696733f` 后的实现提交为 `3954cbd`（含第二轮审核的四项修正）。改基后复跑：覆盖校验 `OK: 78 test modules across 4 shards, each with a stage`，四片 `Ran` 378+219+188+240 = **1025** 全部 `OK`（`/tmp/pc-tg-final/`，墙钟 218／220／207／202s；更早一次 `/tmp/pc-tg-new/` 为 232／234／220／212s，机器负载较高）。
- 环境：本地 macOS／Python 3.14.7；CI 为 ubuntu-latest／Python 3.12。原始输出（仓库外）：`/tmp/pc-tg-check/`（四片日志 `shard1.log`…`shard4.log`、墙钟 `shards.txt`）；分组测量产物 `/tmp/pc-tg-map.json`、`/tmp/pc-tg-timing.clean.json`。

## 逐项结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | 在新基准上复跑八例，日志 `/tmp/pc-tg-final/t1-injections.log`。正确清单：退出码 0 且 stdout 为 `OK: 78 test modules across 4 shards, each with a stage`；八种坏清单逐例断言错误子串——`missing` → 1／`ERROR: not covered by any shard: test_contact_state`、`duplicate` → 1／`ERROR: test_contact_state listed in both shard1 and shard2`、`nonexistent` → 1／`ERROR: shard3: no such test module: test_does_not_exist.py`、`empty_shard` → 1／`ERROR: shard4 lists no modules`；`no_stage`（去掉 `stage` 字段）→ 1／`carries no stage`；`bad_stage`（改成 `stage9`）→ 1／`unknown stage`；`manifest_extra_shard`（清单加带真实模块的第五片）→ 1／`is not run by the workflow`；`workflow_extra_shard`（工作流把 shard4 换成 shard5）→ 1／`is not run by the workflow` 与 `has no manifest entry` 同时命中；恢复后再次退出 0，`git diff --exit-code -- plan/test-grouping/shards.json .github/workflows/ci.yml` 无输出，`git diff --exit-code -- plan/test-grouping/shards.json` 无输出（日志 `/tmp/pc-tg-final/t1-injections.log`） |
| T2 | 通过 | 按阶段分组驱动的新分配（阶段信号已含兄弟阶段脚本与模块调用，`test_stage1_candidates` 归 `stage1`）：shard1 28 模块／104.1s（non-stage 18、stage1 5、stage3 4、mixed 1）、shard2 14／104.1s、shard3 12／103.8s、shard4 24／104.0s；四片都 `OK`，`Ran` 378+219+188+240 = **1025** = `countTestCases()`，无重复执行；78 个模块**全部**带 `stage`（`non-stage` 显式记录），`signals` 与标签多数一致（例：`test_contact_state` signals `stage3 3550／stage5 3175／stage4 2200／stage2 1575／stage1 25` → `stage3`） |
| T3 | 通过 | 工作流含 `fail-fast: false`、`matrix.shard: [shard1..shard4]`、每片先 `python scripts/check_test_shards.py` 再从 `tests/` 跑本片；分片命令把 `--print` 结果存进 `modules` 变量、**为空即 `exit 1`**（不让空列表退化成无参数 `unittest` 全量 discovery）；聚合任务 `needs: [shards]`、`if: always()`、`needs.shards.result != "success"` 即失败 |
| T4 | 通过 | 四片命令都在本地独立跑通，互不依赖；本轮（机器负载较高，产物 `/tmp/pc-tg-new/`）墙钟 shard1 232s、shard2 234s、shard3 220s、shard4 212s；改基后复跑（`/tmp/pc-tg-final/`）为 218／220／207／202s，与模块耗时之和的比值一致 |
| T5 | 通过 | 改基到 `696733f` 后：CI 运行 `39213109711`（head `ea81d6e`）—— `shards (shard1)` pass 1m38s、`shards (shard2)` pass 2m18s、`shards (shard3)` pass 2m2s、`shards (shard4)` pass 1m18s、聚合 `test` pass 4s。按阶段分组（第一轮修正后）：CI 运行 `39209594905`（head `9bfb066`） —— `shards (shard1)` pass 1m27s、`shards (shard2)` pass 2m10s、`shards (shard3)` pass 2m0s、`shards (shard4)` pass 1m33s、聚合 `test` pass 4s。此前的按耗时分配：CI 运行 `39168161446`：`shards (shard1)` pass 1m27s、`shards (shard2)` pass 2m5s、`shards (shard3)` pass 2m12s、`shards (shard4)` pass 1m27s、聚合 `test` pass 4s。分片在 ubuntu／Python 3.12 下并行生效，聚合任务提供了名为 `test` 的检查；按测试计划这不属本批业务必测项，只作既有检查结果引用 |

## 执行方法与命令

1. 覆盖校验与六种坏清单注入（片段见测试计划第 2 步，含 `try/finally` 与逐例错误子串断言）：正确 → 0（stdout 含 `OK: 78 test modules across 4 shards, each with a stage`）；漏归类 → 1（`not covered by any shard`）；重复 → 1（`listed in both`）；不存在 → 1（`no such test module`）；空分片 → 1（`lists no modules`）；丢 stage → 1（`carries no stage`）；阶段值非法 → 1（`unknown stage`）；恢复 → 0。
2. 逐片运行（从 `tests/` 目录，模块列表由 `--print` 提供；本轮四片并行执行，故墙钟受机器负载影响）：

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
- 审核的唯一阻塞项（行为分组未落实）：`shards.json` 原先只按耗时分配、README 的“主导阶段”列因键名带 `.py` 与不带 `.py` 不匹配而全为空。已重做——归类结果落进 `shards.json`（每模块 `stage` + 原始 `signals`、每分片 `stages` 构成），分配改为阶段分组驱动，校验脚本增加两条阶段断言，README 逐模块列出真实阶段。
- 第二轮审核四项：① `test_stage1_candidates` 被误标 `non-stage`（该模块按路径加载 `contact_stage1.py` 并调用其函数，我的信号正则只认 runner 的 `stageN_*` 入口）→ 补上“兄弟阶段脚本”与“模块调用”两类信号后归 `stage1`，stage1 方法数 23→86、无信号 250→187，分片统计与 README 同步；② 校验脚本未核对分片名与工作流 → 增加“分片名集合必须与 `matrix.shard` 一致”，工作流在 `--print` 为空时立即失败；③ 计划正文仍是旧分配数字、测试计划/记录指针落后 → 计划升到第 4 版（28／14／12／24 与阶段构成）、测试计划升到第 5 版；④ 合并基准已变 → 本批改基到当前 main 并重跑校验与分片（见下）。
- 以上属测量与测试资产问题，产品与测试代码未改。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在本 PR 上跑 4 个分片与聚合任务；结果按运行编号与所跑 head 记录。

## 结论与交接

- T1–T4 对被测提交取得有效通过结果；T5 的 CI 运行来源已补（见上表）。
- 本记录之后如只改文档，未改工作流、脚本与测试代码时，上述逐项结果继续有效并沿用。
- 依赖顺序：本批从 `main` 拉出，与批次二/三、边界一至四的在途 PR 无依赖关系，可独立合并。
- CI 实测（ubuntu／3.12）：四片作业 1m27s–2m12s（含 checkout 与 setup-python），聚合任务 4s；首次跑完的实测已记入本表，`shards.json` 的模块耗时仍按本地测量，待下次调整分片时一并更新。
- 下一负责人：测试计划审核（第一、二关口）、第三关口与合并审核；本记录不代替任何关口结论。
