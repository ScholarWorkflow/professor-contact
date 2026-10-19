# Stage 2 划分第四批：finalize 层（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage2-finalize/implementation-plan.md` 第 2 版（`Plan conclusion: APPROVED`）。
- 测试计划：`plan/stage2-finalize/test-plan.md` 第 2 版（待测试计划审核；本记录按该版命令产生）。
- 被测提交：`47f609dc66d1781cbf67d6bfd885cd80cb8d174e`（实现提交；父提交 `e973ffb4571344157b3c43a151906a24f48c7e4e`，即 PR #108 合并后的 `origin/main`）。
- 环境：macOS；`python3 --version` 为 3.14.7（T4/T5），`uv run --no-project` 为 3.14.6（A/B 脚本）；仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage4/`。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 基线有效 | 通过 | 对比脚本 `/tmp/pc-stage2-tools/compare_stage2_batch.py`（91 行，sha256 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`）：T0 3 条 OK。base 与 head 是两个不同目录；base 仍定义 9 个函数；head 顶层一个都不定义。 |
| T1 划分完成 | 通过 | 同一脚本 T1 19 条 OK：模块文件存在；9 个函数全部离开 runner 顶层并进入模块 `build()`。 |
| T2 逻辑不变 | 通过 | 同一脚本 T2 12 条 OK：9 个函数代码 AST 等价（docstring 不参与比较）；非搬移顶层定义不变；离开 runner 的定义正好是这 9 个；9 个别名都在。 |
| T3 旧接口与加载不变 | 通过 | 同一脚本 T3 19 条 OK：9 个名字可调用且签名相同；直接执行 `contact_state.py --help` 退出码 0。合计 **53 条 OK**、`ALL CHECKS PASS`、exit 0（`/tmp/pc-stage4/compare-rebased.log`）。 |
| T4 finalize 行为不变 | 通过 | 测试计划列出的 10 个方法：`Ran 10 tests in 12.345s`、`OK`，无失败、无跳过（`/tmp/pc-stage4/t4-rebased.log`）。 |
| T5 复制夹具加载 | 通过 | 测试计划列出的 2 个方法：`Ran 2 tests in 2.073s`、`OK`，无失败、无跳过（`/tmp/pc-stage4/t5-rebased.log`）。 |
| 既有仓库检查（非必测） | 通过 | PR #110 在 head `99af1e1` 上 run `39314435704`：`shards (shard1..4)` 与聚合 job `test` 全部 pass；`99af1e1` 只新增 plan/test 文档，产品代码同 `47f609d`。 |

T4 实际方法（与测试计划第 2 步逐字对应）：`TestFinalizePreflightWiring` 的 6 个 finalize 预检/漂移方法；`Stage2FinalizeWithResolvedTests` 的 `test_finalize_applies_resolved_directions_to_pack`、`test_finalize_stamps_resolved_subfield_on_unchanged_directions`、`test_finalize_fails_closed_on_stale_resolved_file`；`ResolvedDirectionDownstreamRegressionTests.test_stage2_reuse_keeps_provisional_fingerprint_across_repeated_finalize`。未选主要断言落在第 5 批 validation report/refine 上的方法。

## 重跑记录

- 初次执行在 `0f89ebd` 基线上：A/B 53 条 OK、T4 `Ran 10 tests in 7.730s`、T5 `Ran 2 tests in 1.322s`（`compare.log`、`t4.log`、`t5.log`）。
- 执行期间 PR #108（第 1 批，`_stage2_preflight.py`）合并到 `main`，分支 rebase 到 `e973ffb`；三个测试编号全部按 rebase 后的工作树重跑，上表引用的是重跑结果。两次尝试都保留在同一 `/tmp/pc-stage4/` 目录。

## 接缝与差异检查

`git diff --ignore-blank-lines -U0 e973ffb 47f609d -- .apm/skills/professor-contact/scripts/contact_state.py` 的 hunk 头只有以下 5 个：

```text
@@ -187,0 +188,12 @@ def stage3_render_line_scopes(md_text: str) -> list:
@@ -3920,681 +3932,42 @@ def render_analysis_md(ctx: Stage2Context, pack: dict,
@@ -4602,141 +3975,9 @@ def cmd_stage2_finalize(args) -> None:
@@ -9358,13 +8598,0 @@ def stage2_bound_render(professor_dir: Path, pack: dict) -> tuple[str, str]:
@@ -9439,24 +8666,0 @@ def stage2_restore_pack_later_papers(
```

- 第 1 个 hunk 是 188 行的加载块；在 `stage3_render_line_scopes` 之后、`SCHEMA` 之前，前后各保留原来相邻行的 1 个空行（与第 1、2 批加载块同一写法）。第 1 批的 `_stage2_preflight.py` 加载块仍在 `SCHEMA` 之后，两个块互不改写。
- 第 2、3 个 hunk 是 finalize 定义块的删除与绑定/别名块。绑定块在 `render_analysis_md` 结束之后、`profile_fingerprint` 之前；别名块之后有 2 个空行。
- 第 4、5 个 hunk 是 `stage2_trusted_paper_title`（9358-9370）与 `stage2_require_later_paper_titles`（9439-9462）的删除；`stage2_merge_later_paper_source` 与 `stage2_parse_report_location` 保留，前后各 2 个空行。
- 没有搬移区以外的 hunk，也没有常量、import、CLI、入口清单或其它顶层定义改动。搬移区内的空行变化来自删除函数后遗留的分隔行：已收敛为每个相邻顶层定义之间 2 个空行。
- 行号相对 `d5a4f75` 的参考值有偏移：`#108` 在 finalize 块之前删除了约 804 行，`#105` 在 helper 之前删除了 2 行；按函数名/AST 定位，不用参考行号删改。

## 产物与偏差

- 被测 runner：10292 行，sha256 `d7a2cb9bbd5983b1ec29cd1eed3bda7a65504e1f1a681d323620aa5fb33eda8f`。
- 新模块：918 行，sha256 `47c486a42eb20e60984ba42dfdb18c00978b0d7f2ddae777a5bae31836800111`。
- `git diff --stat e973ffb 47f609d`：新模块 918 行新增；runner 63 行新增、859 行删除（844 行函数体 + 搬移区内 15 个遗留空行）。
- 生成与整理：提取器 `/tmp/pc-stage2-tools/extract_batch.py`（sha256 `e820a3343ca8729720284c0845b52a10222c4b454c87ab36f862b6346209ada9`）按 `/tmp/pc-stage2-tools/spec-b4.json`（sha256 `2fe42f4ee3722cb0c776c35b19616c535189aec95fae64a5039c2ec5f1d40e47`）生成 922 行模块与 11113 行 runner（旧基线）。整理只改格式：删除 spec 带入但 9 个函数未使用的 `import re`（执行计划也写明本批不需要 `re`），模块头空行收敛为 2 个，`SimpleNamespace` 成员缩进改为 8 个空格；随后按接缝检查收敛 runner 的遗留空行。函数体、常量注入和调用关系未改。
- rebase 影响：`#108` 合入后，本批加载块按原 spec 的 `load_anchor=188` 落在 `SCHEMA` 之前，`#108` 的预检加载块保留在 `SCHEMA` 之后；两个模块都只定义函数，没有 import 期依赖，绑定点仍在全部依赖定义之后，无行为变化。T0–T5 已按 rebase 后的树重跑。
- 测试计划第 2 版为待审核状态；本记录不代填审核结论。CI 已在 head `99af1e1` 上通过（run `39314435704`，4 个 shards + 聚合 test）。
