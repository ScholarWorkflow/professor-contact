# 共享基础层划分第一批：哈希／时间／文本／方向身份／托管文件（测试执行记录）

## 版本与对象

- 执行计划：`plan/shared-base/implementation-plan.md` 第 3 版。
- 测试计划：`plan/shared-base/test-plan.md` 第 5 版。
- 被测提交：`dec7101`（`refactor(shared): move the common hashing, identity and file helpers into a module`，父提交 `8c5ed21` 为计划文档提交，其父为链尾 `13efd40`）。
- 对照基准：分支链末位 `refactor-stage2-render`（#114）的 head `13efd40441a2bf8683c9da630bdc747248fc8c29`（GitHub 自动 rebase 前的同一提交是 `cf979ab`，两者 `scripts` 子树字节相同），runner 7085 行。
- 环境：macOS；`uv run --no-project python` 3.14.6；仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage8/`（`base/` 是父提交导出的 scripts，`blocks/blk0.sh`–`blk5.sh` 是从测试计划第 5 版原文抽出的命令块）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：`build()` 7 个 keyword-only 参数、40 个成员；40 个同名别名、集合与名字表相等；绑定调用与 40 个别名都早于 `_stage2_facts.build(...)`；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；40 个名字不再在 runner 顶层定义；`py_compile` 与 `--help` 退出码 0（`/tmp/pc-stage8/t0.log`） |
| T1–T3 结构／AST／接口 | 通过 | 208 条 `OK`（T0 3、T1 81、T2 43、T3 81）、`ALL CHECKS PASS`、退出码 0；`--help` 与父提交逐字节相同（`diff -u` 无输出，`/tmp/pc-stage8/compare.log`） |
| T2 docstring | 通过 | `total=40 with_doc=13 multi=9 clean_equal=13 without_doc=27 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS`（`/tmp/pc-stage8/docstring.log`） |
| T4 哈希／文本／方向身份／托管写入 | 通过 | 10 个方法：`Ran 10 tests in 8.453s`、`OK`，无失败、无跳过（`/tmp/pc-stage8/t4.log`） |
| T5 复制夹具加载 | 通过 | 2 个方法：`Ran 2 tests in 0.985s`、`OK`（`/tmp/pc-stage8/t5.log`） |
| 失败注入 | 不适用 | 本批只搬移定义，不改事务、回滚、写入顺序或错误通道；`managed_write` 仍走同一套 `atomic_write`／`fail` |
| 失败对照（父提交，未触发） | 通过 | 12 个方法（T4 10 + T5 2）在父提交上：`Ran 12 tests in 9.508s`、`OK`，退出码 0（`/tmp/pc-stage8/baseline.log`） |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 4 个 `shards` 与聚合 `test` 的运行编号；不作为通过条件 |

## 文件与接缝

- 被测 runner：`.apm/skills/professor-contact/scripts/contact_state.py`，6730 行，sha256 `86cdfa2bbeee9d9a3a542426e140e10fe12e60b402e4ab4458d66d8589c2f356`。
- 新模块：`.apm/skills/professor-contact/scripts/_contact_base.py`，456 行，sha256 `1e1572e098ec97a0a8436e8cf70a646efa040407a48188c21aa3ccf7dfbee6d3`（40 个成员，`build()` 7 个 keyword-only 参数）。
- 代码 diff（`13efd40` → `dec7101`；`13efd40` 的 scripts 子树与 `cf979ab` 相同）：runner `+63 −418`（`git diff --numstat`）；删除侧是 40 个定义 341 行加收敛掉的空行，新增侧是加载块 12 行与绑定块。
- `git diff --ignore-blank-lines -U0` 只剩 3 个 hunk：`@@ -243,0 +244,12 @@`（加载块）、`@@ -354,165 +365,0 @@`（第一段 21 个定义删除）、`@@ -986,254 +833,52 @@`（第二段 19 个定义删除与绑定块 52 行）。
- 空行：重构后自造的 44／38／3 行长空行块收敛为 2 行；父提交自带的 6 处长空行块（6／4／4／10／3／6 行）数量与长度均未变。

## 说明与偏差

- **演练抓到的两个缺陷**：① 模块 import 漏了 `os`（`rel_path` 用 `os.path.relpath`），首轮 T4 十个方法全 `NameError`；用 AST 把 40 个定义引用到的 runner import 全量算出后补齐（`hashlib`／`json`／`os`／`re`／`unicodedata`）。② T0 原脚本用 `save_projections` 的行号做锚点，而该函数本批已搬走，脚本直接 `StopIteration`；改成断言“绑定调用与 40 个别名都早于 `_stage2_facts.build(...)`（第一个消费方）”。
- **工具**：因为插入点后面紧跟的是 `_stage2_facts = …build(` 赋值语句而不是函数定义，原有提取器只支持 `bind_before`，本批用 `extract_batch_v3.py`（141 行，sha256 `1536b8bd5cad8d46800ea2832479f12a959f3b6e0a5dc06bb3e93d760d505d31`，只多 `bind_after`）。对比脚本仍用 `compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`），docstring 用 `check_docstrings_v3.py`（109 行，sha256 `31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a`）。
- **基准指针**：原先的 `cf979ab` 在 GitHub 原生 stacked PR 自动 rebase 后已不在 origin 上；两份提交的 `scripts` 子树字节相同，故测试计划与本文档统一改用 `13efd40`，块 2／5 在任何新克隆上都能直接跑。
- **覆盖说明**：`projection_write`、`load_projections`、`save_projections` 在父提交里只有定义、全仓无调用点，因此没有可观察行为；托管写入的实际覆盖来自 `managed_write`（被 `_stage2_finalize` 与 `_stage2_validation` 的 `build()` 注入），T4 里由 `test_legacy_slow_path_seeds_metadata_for_next_run` 走 `stage2-finalize` 覆盖。
- 无测试跳过；没有改测试、常量值、CLI、入口清单或 Nix 布局。

## 复核入口

- T0：`/tmp/pc-stage8/blocks/blk0.sh`（5 条 `T0 ... OK` + `T0 CHECKS PASS`）。
- T1–T3：`/tmp/pc-stage8/blocks/blk1.sh`（`diff` 无输出 + 208 条 `OK`）。
- docstring：`/tmp/pc-stage8/blocks/blk2.sh`（`DOCSTRING CHECKS PASS`）。
- T4：`/tmp/pc-stage8/blocks/blk3.sh`（`Ran 10 tests`、`OK`）。
- T5：`/tmp/pc-stage8/blocks/blk4.sh`（`Ran 2 tests`、`OK`）。
- 失败对照（未触发）：`/tmp/pc-stage8/blocks/blk5.sh`（12 个方法、`OK`）。
