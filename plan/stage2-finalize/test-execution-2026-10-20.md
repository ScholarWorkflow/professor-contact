# Stage 2 划分第四批：finalize 层（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage2-finalize/implementation-plan.md` 第 2 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/stage2-finalize/test-plan.md` 第 3 版（第一关 PASS、第二关 PASS；本记录按该版命令产生）。
- 被测提交：`f2fe4930bab6c2295309280e2303dac1a17c5773`（实现提交；父提交 `7a59006c551dc863045fb5221143927357429c83`，即 PR #109 合并后的 `origin/main`）；分支 head `a87735cd8edca895e3ddeefea1edff627bb96f12`。
- 环境：macOS；`python3 --version` 为 3.14.7（T4/T5），`uv run --no-project` 为 3.14.6（A/B 脚本）；仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage4/`。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 基线有效 | 通过 | 对比脚本 `/tmp/pc-stage2-tools/compare_stage2_batch.py`（91 行，sha256 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`）：T0 3 条 OK。base 与 head 是两个不同目录；base 仍定义 9 个函数；head 顶层一个都不定义。 |
| T1 划分完成 | 通过 | 同一脚本 T1 19 条 OK：模块文件存在；9 个函数全部离开 runner 顶层并进入模块 `build()`。 |
| T2 逻辑不变 | 通过 | 同一脚本 T2 12 条 OK：9 个函数代码 AST 等价（docstring 不参与比较）；非搬移顶层定义不变；离开 runner 的定义正好是这 9 个；9 个别名都在。 |
| T3 旧接口与加载不变 | 通过 | 同一脚本 T3 19 条 OK：9 个名字可调用且签名相同；直接执行 `contact_state.py --help` 退出码 0。合计 **53 条 OK**、`ALL CHECKS PASS`、exit 0（`/tmp/pc-stage4/compare-main2.log`）。 |
| T4 finalize 行为不变 | 通过 | 测试计划列出的 10 个方法：`Ran 10 tests in 6.138s`、`OK`，无失败、无跳过（`/tmp/pc-stage4/t4-main2.log`）。 |
| T5 复制夹具加载 | 通过 | 测试计划列出的 2 个方法：`Ran 2 tests in 1.273s`、`OK`，无失败、无跳过（`/tmp/pc-stage4/t5-main2.log`）。 |
| 既有仓库检查（非必测） | 通过 | rebase 前 PR #110 在 head `99af1e1` 上 run `39314435704` 全 pass；rebase 后 head `a87735c` 的 CI 结果以 PR 页面为准（代码提交为 `f2fe493`，文档提交只改 `plan/`）。 |

T4 实际方法（与测试计划第 2 步逐字对应）：`TestFinalizePreflightWiring` 的 6 个 finalize 预检/漂移方法；`Stage2FinalizeWithResolvedTests` 的 `test_finalize_applies_resolved_directions_to_pack`、`test_finalize_stamps_resolved_subfield_on_unchanged_directions`、`test_finalize_fails_closed_on_stale_resolved_file`；`ResolvedDirectionDownstreamRegressionTests.test_stage2_reuse_keeps_provisional_fingerprint_across_repeated_finalize`。未选主要断言落在第 5 批 validation report/refine 上的方法。

## 重跑记录

- 初次执行在 `0f89ebd` 基线上：A/B 53 条 OK、T4 `Ran 10 tests in 7.730s`、T5 `Ran 2 tests in 1.322s`（`compare.log`、`t4.log`、`t5.log`）。
- 第一次 rebase：PR #108（第 1 批，`_stage2_preflight.py`）合并后 rebase 到 `e973ffb`，三个测试编号按该树重跑（`compare-rebased.log`、`t4-rebased.log`、`t5-rebased.log`）。
- 第二次 rebase：PR #109（第 2 批，`_stage2_resolve.py`）合并后 main 前进到 `7a59006`，分支再次 rebase 到该提交；冲突只在加载块与搬移区交界，`_STAGE2_RESOLVE_*` 与 `_STAGE2_FINALIZE_*` 两个加载块都保留，随后按同一测试计划重跑：A/B 53 条 OK（`compare-main2.log`）、T4 `Ran 10 tests in 6.138s`（`t4-main2.log`）、T5 `Ran 2 tests in 1.273s`（`t5-main2.log`）。上表引用的是第二次 rebase 后的结果。

## 接缝与差异检查

`git diff --ignore-blank-lines -U0 7a59006c551dc863045fb5221143927357429c83 f2fe4930bab6c2295309280e2303dac1a17c5773 -- .apm/skills/professor-contact/scripts/contact_state.py` 的 hunk 头只有以下 5 个：

```text
@@ -200,0 +201,11 @@ _STAGE2_RESOLVE_SPEC.loader.exec_module(_stage2_resolve_module)
@@ -3207,681 +3218,42 @@ def render_analysis_md(ctx: Stage2Context, pack: dict,
@@ -3889,141 +3261,9 @@ def cmd_stage2_finalize(args) -> None:
@@ -8645,13 +7884,0 @@ def stage2_bound_render(professor_dir: Path, pack: dict) -> tuple[str, str]:
@@ -8726,24 +7952,0 @@ def stage2_restore_pack_later_papers(
```

- 第 1 个 hunk 是加载块；第二次 rebase 后它落在 `_STAGE2_RESOLVE_SPEC.loader.exec_module(...)` 之后、`SCHEMA` 之前，前后各保留原来相邻行的 1 个空行。第 2 批的 `_STAGE2_RESOLVE_*` 加载块在它之前、第 1 批的 `_STAGE2_PREFLIGHT_*` 在 `SCHEMA` 之后，三个块互不改写。
- 第 2、3 个 hunk 是 finalize 定义块的删除与绑定/别名块。绑定块 `3220-3259` 在 `render_analysis_md`（`3067`）结束之后、`profile_fingerprint`（`3272`）之前；`stage2_require_later_paper_titles` 别名在 `3269`。
- 第 4、5 个 hunk 是 `stage2_trusted_paper_title` 与 `stage2_require_later_paper_titles` 的删除；`stage2_merge_later_paper_source` 与 `stage2_parse_report_location` 保留，前后各 2 个空行。
- 没有搬移区以外的 hunk，也没有常量、import、CLI、入口清单或其它顶层定义改动。搬移区内的空行变化来自删除函数后遗留的分隔行：已收敛为每个相邻顶层定义之间 2 个空行。
- 行号相对 `d5a4f75` 与第一次 rebase 的参考值都有偏移：`#108` 在 finalize 块之前删除约 804 行、`#109` 再删除约 726 行并新增加载/绑定行；按函数名/AST 定位，不用参考行号删改。

## 产物与偏差

- 被测 runner：9578 行，sha256 `552497ab97cea27a12fb8e9d9efb96a51742a3f6b30ad8e0f8f4a36ee290ea62`。
- 新模块：918 行，sha256 `47c486a42eb20e60984ba42dfdb18c00978b0d7f2ddae777a5bae31836800111`。
- `git diff --numstat 7a59006c551dc863045fb5221143927357429c83 f2fe4930bab6c2295309280e2303dac1a17c5773`：新模块 `+918 −0`；runner `+62 −859`（844 行函数体 + 搬移区内 15 个遗留空行）。
- 生成与整理：提取器 `/tmp/pc-stage2-tools/extract_batch.py`（sha256 `e820a3343ca8729720284c0845b52a10222c4b454c87ab36f862b6346209ada9`）按 `/tmp/pc-stage2-tools/spec-b4.json`（sha256 `2fe42f4ee3722cb0c776c35b19616c535189aec95fae64a5039c2ec5f1d40e47`）生成 922 行模块与 11113 行 runner（旧基线）。整理只改格式：删除 spec 带入但 9 个函数未使用的 `import re`（执行计划也写明本批不需要 `re`），模块头空行收敛为 2 个，`SimpleNamespace` 成员缩进改为 8 个空格；随后按接缝检查收敛 runner 的遗留空行。函数体、常量注入和调用关系未改。
- rebase 影响：`#108`、`#109` 合入后，本批加载块按原 spec 的 `load_anchor=188` 落点顺次后移到 `_STAGE2_RESOLVE_*` 之后、`SCHEMA` 之前；三个模块都只定义函数，没有 import 期依赖，绑定点仍在全部依赖定义之后，无行为变化。T0–T5 已按第二次 rebase 后的树重跑。
- 测试计划第 3 版沿用第 2 版的第一关/第二关结论（本版只同步 rebase 后的基线与行号）；rebase 前 CI 已在 head `99af1e1` 上通过（run `39314435704`，4 个 shards + 聚合 test）。
