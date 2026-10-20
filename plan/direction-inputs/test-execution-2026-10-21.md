# 方向输入助手划分：测试执行记录（2026-10-21）

## 环境与来源

- Test plan: [test-plan.md](test-plan.md)，第 3 版（`sha256 74ee168b1f180112dd1148457ab8242119a3ef14da26f2ad907b3730ae36d10b`）；复核后第 7 步新增常量对照命令时命令块有改动，本记录对应那次完整重跑；其后版本字段与文字说明又改过两轮（`0a666af3…` → `83e88348…` → `41cf8843…`），命令块逐字节未变，未重跑；最后一轮去掉第 91 行块内行尾空格（`git diff --check` 报错），命令语义未变但字节变了，故按当前文件整套重跑一次，本记录对应这次重跑。
- 执行命令来源：把 test-plan.md 的 8 个 `sh` 代码块按顺序抽成脚本 `/tmp/pc-stage20/run-test-plan-v3e.sh`（`sha256 d3c47af73596a1fd12a0ec31616a800ddb231890180ddf68e7ac52d36074c0f1`），逐字执行；执行结束再抽一次，与执行用的脚本逐字节相同（`identical: True`）。
- 解释器：`uv run --no-project python`，Python 3.14.6（CI 为 3.12）。
- 基线：`git rev-parse origin/refactor-email-core` = `972d4fd4b7f827fcac7b7305257f761e09ccc01b`（PR #126 的 head），与计划写死的 `EXPECTED_BASE` 相同。
- 工作树：`/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-direction-inputs`；执行时工作树 HEAD = `972d4fd`（改动尚未提交，与基线同一提交）。
- 整份脚本退出码：`0`。

## 结果

| 编号 | 命令要点 | 实测输出 | 结论 |
| --- | --- | --- | --- |
| T0 | `py_compile` + 工厂契约／依赖注入／模块源码约束检查 | `T0 CHECKS PASS`；`--help` 退出码 0 | 通过 |
| T1 | A/B 脚本 T0／T1 段 | 16 条 `OK`（T0 3、T1 13） | 通过 |
| T2 | A/B 脚本 T2 段 + docstring 工具 | 9 条 `OK`；`total=6 with_doc=3 multi=3 clean_equal=3 without_doc=3 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS` | 通过 |
| T3 | A/B 脚本 T3 段 + `--help` 比对 | 13 条 `OK`；`ALL CHECKS PASS`（整份 38 条 `OK`）；`cmp` 无差异、`HELP IDENTICAL` | 通过 |
| T4 | 4 个方向分组方法（真实 CLI 子进程） | `Ran 4 tests in 3.409s`、`OK` | 通过 |
| T5 | 复制布局加载新模块 | `Ran 1 test in 1.037s`、`OK` | 通过 |
| T6 | 接缝、常量值与尺寸 | `git status --porcelain` 3 条：`M contact_state.py`、`?? _direction_inputs.py`、`?? plan/direction-inputs/`；`git diff --stat`：`1 file changed, 28 insertions(+), 97 deletions(-)`；`-U0` hunk 6 个、默认上下文 2 个；`wc -l`：2085 与 130；顶层字面量赋值 67 个，与父提交同名同值（`CONSTANTS UNCHANGED (67)`） | 通过 |

第 8 步同时记下本批两个文件的摘要：`contact_state.py` 为 `cb9cc4551621ed71749a96c3c45a5e0762a2e3cf86a0140a33c88117180cf088`，`_direction_inputs.py` 为 `d6613ff52bba05d80d15f33d853102c58a799d0475c98ceeb29384ba6859fdb4`。

## 覆盖说明（按命令分发路径，不是调用计数）

T4 的 4 个方法都从 CLI 子进程进入，命令分发把它们接到 stage3 计划与方向分组路径：读 profile 走 `load_profile_text`／`profile_fingerprint`，解析跨组与方向 ID 走 `_parse_cross_groups`／`_parse_direction_id_list`，跨组新鲜度走 `_cross_group_fresh`，岗位切片走 `_direction_slices`。`test_cross_group_input_fail_closed` 的 3 个子用例（`single id`、`unknown id`、`not nested lists`）覆盖 `fail` 的两条 `invalid_params` 分支。

## 未执行或未通过的项

- 无跳过的必测项。
- 仓库 CI（4 个 `shards` + 聚合 job `test`）按测试计划属既有检查，不在本记录内，推送后在 PR 上核对。

## 结论

T0–T6 全部按第 3 版测试计划执行并通过，没有修改输入或预期求通过。复核后命令块有改动（T6 增加常量对照）已整套重跑；最后一次仅去掉块内一处行尾空格，也整套重跑，结果与上一次逐项相同（38 条 `OK`、`CONSTANTS UNCHANGED (67)`、3 条 status、`+28 −97`、hunk 6/2、2085/130）；第 1 步的顺序断言改成集合比较，未放宽任何业务预期。
