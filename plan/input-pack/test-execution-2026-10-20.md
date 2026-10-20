# 共享基础层第二批：输入包规范化和候选状态（测试执行记录）

## 版本与对象

- 执行计划：`plan/input-pack/implementation-plan.md` 第 1 版。
- 测试计划：`plan/input-pack/test-plan.md` 第 3 版。
- 被测提交：`e9a30ba`（`refactor(shared): move the input pack and candidate state into a module`，父提交 `c9b1f6a` 为计划文档提交，其父为链尾 `3f590e8`）。
- 对照基准：父分支 `refactor-shared-base`（#116）的 head `3f590e8`（#111 合并后 GitHub 自动 rebase 的链尾；原 `4ff8ff6` 的 `scripts` 子树与之字节相同），runner 6730 行。
- 环境：macOS；`uv run --no-project python` 3.14.6；仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage9/`（`base/` 是父提交导出的 scripts，`blocks/blk0.sh`–`blk5.sh` 是从测试计划第 2 版原文抽出的命令块）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 5 条 `T0 ... OK` + `T0 CHECKS PASS`：`build()` 14 个 keyword-only 参数、11 个成员；11 个同名别名且集合与成员一致；绑定调用与 11 个别名都在 `_contact_base` 最后一个别名之后、`_stage2_facts.build(...)` 之前；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；11 个名字不再在 runner 顶层定义；`py_compile` 与 `--help` 退出码 0（`/tmp/pc-stage9/t0.log`） |
| T1–T3 结构／AST／接口 | 通过 | 63 条 `OK`（T0 3、T1 23、T2 14、T3 23）、`ALL CHECKS PASS`、退出码 0；`--help` 与父提交逐字节相同（`diff -u` 无输出，`/tmp/pc-stage9/compare.log`） |
| T2 docstring | 通过 | 整行摘要 `total=11 with_doc=10 multi=9 clean_equal=10 without_doc=1 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS`（`/tmp/pc-stage9/docstring.log`） |
| T4 输入包规范化／候选状态／迁移 | 通过 | 10 个方法：`Ran 10 tests in 7.092s`、`OK`，无失败、无跳过（`/tmp/pc-stage9/t4.log`） |
| T5 复制夹具加载 | 通过 | 2 个方法：`Ran 2 tests in 0.953s`、`OK`（`/tmp/pc-stage9/t5.log`） |
| 失败注入 | 不适用 | 本批只搬移定义，不改事务、回滚、写入顺序或错误通道 |
| 失败对照（未触发） | 通过 | 第 5 步单方法实跑示例：`Ran 1 test`、`OK`，日志 `baseline-<方法短名>-<时间戳>.log`；基准目录按父分支 SHA 建立，不复用过期缓存 |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 4 个 `shards` 与聚合 `test` 的运行编号；不作为通过条件 |

## 文件与接缝

- 被测 runner：`.apm/skills/professor-contact/scripts/contact_state.py`，6367 行，sha256 `5f1a7773f3c1ce23bba53c6e303323ee43b4c769d8690b9f94921da83389b18b`。
- 新模块：`.apm/skills/professor-contact/scripts/_contact_pack.py`，441 行，sha256 `03741d06e8706fece94c34f0d912ea1065abb3caafe597efdd8660faae360cf4`（11 个成员，`build()` 14 个 keyword-only 参数；模块只 import `Path`／`Any`／`types`）。
- 代码 diff（`4ff8ff6` → 工作树）：runner `+42 −405`（`git diff --numstat`）。
- `git diff --ignore-blank-lines -U0` 只剩 3 个 hunk：`@@ -255,0 +256,12 @@`（加载块）、`@@ -373,405 +384,0 @@`（11 个定义删除）、`@@ -884,0 +492,30 @@`（绑定块与 11 个别名，插在 `save_projections` 884 行之后）。
- 空行：重构后自造的两处空行块（删除处 24 行、绑定块后 3 行）收敛为 2 行；父提交自带的 6 处长空行块（6／4／4／10／3／6 行）数量与长度均未变（只读脚本比对确认）。

## 说明与偏差

- **绑定点依赖上一批**：`read_json_file`／`direction_machine_id`／`cross_group_id` 由 `_contact_base` 在第 852／861／863 行提供，因此本批的绑定块插在 `save_projections = _contact_base.save_projections`（886）之后、`_stage2_facts` 的绑定注释之前；第一个消费方 `_stage2_facts` 只用本批的 `load_input_pack` 一个名字。
- **工具**：插入点前是别名赋值而不是函数定义，`bind_after`（按函数名）用不上，本批用 `extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`，新增 `bind_after_line`）。对比脚本仍是 `compare_stage2_batch_v2.py`（94 行，`1ba8c0f4…`），docstring 用 `check_docstrings_v3.py`（109 行，`31c8b208…`）。
- **覆盖限制**：`_slice_gap_directions` 与 `_migrate_v1_cross_group` 在既有测试里没有行为用例（`grep -rn '"cross_direction":' tests` 为 0），只有 T2 的 AST 等价覆盖；补行为用例需要验收决定人批准，本批不扩范围。
- **T4 方法选择**：第一关指出原先 4 个方法不执行本批定义（两个 migrate 方法走的是迁移命令、一个越界用例在做 containment 时就返回、一个只读 pack），已换成 `test_stage4_exactly_migrates_v1_candidate_state_with_pack_mapping_without_stage3_rerun`、`test_stage4_same_professor_preserved_entry_needs_refresh_is_zero_write`、`test_rebuild_overview_only_migrates_a_unique_legacy_identity`；`test_pack_has_one…` 保留并改称 stage2 输出契约。复核还指出第 3 步的命令没有随表更新，已同步并重跑（`Ran 10 tests in 7.092s`）。
- 无测试跳过；没有改测试、常量值、CLI、入口清单或 Nix 布局。

## 复核入口

- T0：`/tmp/pc-stage9/blocks/blk0.sh`（5 条 `T0 ... OK` + `T0 CHECKS PASS`）。
- T1–T3：`/tmp/pc-stage9/blocks/blk1.sh`（`diff` 无输出 + 63 条 `OK`）。
- docstring：`/tmp/pc-stage9/blocks/blk2.sh`（整行摘要 + `DOCSTRING CHECKS PASS`）。
- T4：`/tmp/pc-stage9/blocks/blk3.sh`（`Ran 10 tests`、`OK`）。
- T5：`/tmp/pc-stage9/blocks/blk4.sh`（`Ran 2 tests`、`OK`）。
- 失败对照（未触发）：`/tmp/pc-stage9/blocks/blk5.sh`（单方法、按 SHA 建基准目录）。
