# Stage 2 划分第三批：resolve 提交层（测试执行记录）

- 执行日期：2026-10-20
- 测试计划：[test-plan.md](test-plan.md)，第 3 版（第一关 PASS、第二关待复核）。
- 工作分支：`refactor-stage2-resolve-commit`；基线 `3233810`（`origin/refactor-stage2-resolve`，第 2 批分支在实施期间变基到已合并的 `main`，实现提交为 `f07abb0`；任务开始时的旧基线 `2ecdc9c`／`e5b8d4e` 已被替换）。
- 被测代码提交：`c080be04ff7eb831be26077082b34849d6624664`（`refactor(stage2): move the resolve submit layer into the resolve helper`）；测试计划文档提交 `21e1af0`、本记录提交见 PR 最新 head。被测 `scripts/` 目录在两处之间没有变化（`git diff --stat c080be0 21e1af0 -- .apm/skills/professor-contact/scripts` 为空）。
- 环境：Darwin 25.6.0 arm64；`uv run --no-project python` 为 Python 3.14.6（仓库 CI 用 3.12，本记录为本地执行结果）。
- 运行目录：`/tmp/pc-stage3/`；命令块由测试计划原文抽出后逐块执行（抽出脚本与四个 `blockN.sh` 在 `/tmp/pc-stage3/plan-blocks/`），日志 `t0-plan-v3.log`、`plan-block2-raw.log`（第 2 步整块，另按段拆成 `compare-plan-v3.log`、`docstring-plan-v3.log`）、`t4-plan-v3.log`、`t5-plan-v3.log`，脚本哈希 `script-sha.txt`；仓库外临时产物不入库。

## 结果总览

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 | 通过 | 4 条 `T0 ... OK`（14 参数、23 成员、23 同名别名且去重后仍 23、import json）与 `T0 CHECKS PASS`；`py_compile` 与 `--help` 退出码 0 |
| T1–T3 | 通过 | 43 条 `OK`（`T0` 3、`T1` 15、`T2` 10、`T3` 15）；末尾 `ALL CHECKS PASS`；退出码 0 |
| T2 的 docstring 核对 | 通过 | `total=7 with_doc=7 multi=6 clean_equal=7 without_doc=0 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS`、退出码 0 |
| T4 | 通过 | `Ran 7 tests in 4.167s`、`OK`；7 条 `... ok`；无 skip／`FAIL`／`ERROR`；未触发基线对照归因 |
| T5 | 通过 | `Ran 2 tests in 1.209s`、`OK`；无 skip／`FAIL`／`ERROR` |
| 既有仓库 CI | 通过 | PR #112 head `1b08b36` 上 run `39315290639`、head `21e1af0` 上 run `39319465479`，两次的 4 个 `shards (shardN)` 与聚合 job `test` 全部 SUCCESS |

## 逐项结果

### T0：编译、直接执行与工厂契约

命令：测试计划第 1 步（`t0-plan-v3.log`）。结果：

```text
Python 3.14.6
T0 build has exactly the 14 keyword-only parameters OK
T0 build returns 23 members OK
T0 runner has 23 same-name module aliases OK
T0 module imports json OK
T0 CHECKS PASS
```

`uv run --no-project python -m py_compile ...` 无输出、退出码 0；`contact_state.py --help` 无 stderr、退出码 0。检查脚本确认：

- 模块 `build()` 的 keyword-only 参数**精确等于** 14 个名字集合：已移除 `_facts_preflight_proof`、`_load_existing_resolved`，新增 `atomic_json`、`RESOLVED_DIRECTION_SCHEMA`、`now_utc`、`read_json_file`、`direction_provisional_member_keys`；
- `build()` 返回的命名空间有 23 个成员；
- runner 有 23 个 `X = _stage2_resolve.X` 别名（第 2 批 16 个 + 本批 7 个），逐个满足“目标名 == `_stage2_resolve.<同名>`”，且 23 个目标名去重后仍是 23 个（没有重名覆盖）；
- 模块头有 `import json`。

### T1–T3：结构、AST 等价与接口

命令：测试计划第 2 步；对照基准由 `git archive f07abb0 .apm/skills/professor-contact/scripts` 取出，本次重新解包（`compare-plan-v3.log`）。脚本 `/tmp/pc-stage2-tools/compare_stage2_batch.py` 为既有工具，未改写。

脚本 sha256（与计划一致）：

```text
75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7
```

输出 43 条 `OK`，按标签计数：

| 标签 | 条数 | 内容 |
| --- | --- | --- |
| `T0` | 3 | 两侧目录不同；base 仍定义 7 个函数；head 一个都不定义 |
| `T1` | 15 | 模块存在（1）+ 7 个函数“runner 无 / 模块有”（14） |
| `T2` | 10 | 7 个函数代码 AST 不变 + 非搬移顶层定义不变 + 定义集合差 + 每个函数有别名 |
| `T3` | 15 | 7 个函数可调用与签名不变（14）+ runner 直接执行 `--help`（1） |

末尾输出 `ALL CHECKS PASS`，退出码 0。

docstring 单独核对由 `/tmp/pc-stage2-tools/check_docstrings.py` 执行（同一命令块，`docstring-plan-v3.log`）：

```text
941b2220a583bd849330f863a8ccc9de744d9d158fefb849d228e99be66e9bc3  /tmp/pc-stage2-tools/check_docstrings.py
total=7 with_doc=7 multi=6 clean_equal=7 without_doc=0 missing=0 mismatched=0
DOCSTRING CHECKS PASS
```

即 7 个函数都有 docstring（其中 6 个多行），`inspect.cleandoc` 后与基准同文；实际搬运只增加 4 个空格缩进，函数体未改。

### T4：resolve 提交层既有测试

命令：测试计划第 3 步（`t4-plan-v3.log`）。结果：

```text
Ran 7 tests in 4.167s

OK
```

7 个方法：

1. `ResolvedDirectionFinalizeTests.test_resolve_finalize_rejects_missing_new_result`
2. `ResolvedDirectionFinalizeTests.test_resolve_finalize_applies_removal`
3. `ResolvedDirectionFinalizeTests.test_resolve_finalize_rejects_invalid_removal`
4. `ResolvedDirectionRegressionTests.test_resolve_run_isolation_and_missing_results`
5. `ResolvedDirectionRegressionTests.test_reused_direction_ignores_stale_result_file`（直接调用 `validate_resolve_results`）
6. `ResolveAcceptanceBoundaryTests.test_resolve_accept_command_validates_keys_and_staleness`
7. `UserKeptProvisionalTests.test_user_kept_provisional_still_writes_explicit_resolved_direction`

逐条均为 `ok`，没有 `skipped`。本批通过判据只取落在 7 个函数上的断言：结果文件必需性与本轮身份校验、移除成员规则、`cmd_stage2_resolve_finalize` 应用已接受结果、陈旧指纹与跨教授结果的拒绝、运行隔离、旧 result 文件被忽略、`stage2-resolve-accept` 的 key 与陈旧校验、keep-provisional 的显式写入。7 个方法在准备夹具时还会读写前批产物（plan 文件等），这些路径不属于本批判据；本次没有失败，因此未触发“先在 `f07abb0` 上跑同一方法”的基线对照归因。

### T5：复制夹具

命令：测试计划第 4 步（`t5-plan-v3.log`）。结果：

```text
Ran 2 tests in 1.209s

OK
```

两个方法均为 `ok`：

- `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`
- `test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling`

## 版本与产物

- 被测代码提交：`c080be04ff7eb831be26077082b34849d6624664`。
- runner：`.apm/skills/professor-contact/scripts/contact_state.py`，9784 行，sha256 `e0f519313b588f42a1ac4cc38e3cc593cfec1a3327871653aa65c27a06178d5f`。
- 模块：`.apm/skills/professor-contact/scripts/_stage2_resolve.py`，1409 行，sha256 `fa4cb976dfe5a5160b75380739ec30eb57fd5c715894529d100045a5532fe5c6`；`build()` 内 23 个函数、模块级 7 个常量。
- 代码 diff（`3233810..c080be0`）：runner `+13 −604`，模块 `+606 −3`（`git diff --numstat`）。

## 偏差与观察

1. **基线变基**：实施期间 `origin/refactor-stage2-resolve` 被变基到已合并的 `main` 并重写历史，任务给出的 `2ecdc9c`／`e5b8d4e` 被 `f07abb0`／`3233810` 替换（`git merge-base --is-ancestor 2ecdc9c HEAD` 已不再成立）。第一次实现提交 `38c1555` 按旧基线生成；发现变更后用 `--onto` 重放仍因上游历史重写而冲突，于是以 `3233810` 为新基线重新生成本批同一变换，得到 `c080be0`。T0、T1–T3、T4、T5 均在新基线上重跑。
2. 删除 runner 中两段函数时，除了 585 行函数代码，还收敛了定义交界处共 16 个空行（每处保留 2 个空行）：第一段 12 个、第二段 4 个。原因是按 AST 行区间删除后交界处会留下 14 个和 6 个连续空行；收敛后 runner 为 9784 行（`10375 − 585 − 16 + 10`，10 为 7 个别名与 3 行新增 `build()` 实参的净增）。这只是空行整理，不改变任何语句。
3. runner 绑定点注释仍保留第 2 批的文字（“The submit-side helpers just above stay in the runner for the next batch…”）。执行计划写明追加时不重建第 2 批的常量与注释，且本批只允许删除定义、扩展实参、增加别名，因此未改该注释；它不影响行为，建议由后续文档或清理批次统一处理。
4. 本次按测试计划第 3 版重跑，除新增的别名去重断言和 docstring 脚本外，判据与第 2 版一致；日志按版本另存（`*-plan-v3.log`），旧版 `*-newbase.log` 保留但不再作为本记录证据。
5. 既有仓库检查未在本地运行；合并前以 PR 上 `shards (shard1..4)` 与聚合 job `test` 的结果为准。

## 未完成项

- 测试计划第 3 版已提交第二关复核（第一关 PASS）。
- PR 的 CI：head `1b08b36` 上 run `39315290639`、head `21e1af0` 上 run `39319465479`，4 个 `shards (shard1..4)` 与聚合 job `test` 全部 SUCCESS；CI 不作为本批必测结论。
