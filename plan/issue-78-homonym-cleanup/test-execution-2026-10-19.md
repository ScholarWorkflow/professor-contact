# Issue #78：同名支持清理的测试执行记录（2026-10-19）

- 测试计划：[test-plan.md](test-plan.md)，contact78-t3；执行计划：[implementation-plan.md](implementation-plan.md)，contact78-r1。
- 被测版本：产品与说明提交 `4cd173f`（本分支，包含 contact78-r1 §3.1/§3.2 的产品脚本与说明修改）；测试接线提交 `45c30fa`（未再修改）；共同基线 `d5a4f75`（`origin/main` = `d5a4f751fb80de4819d4a1de3ee829db52cea6fc`）。
- 环境：本地 `/run/current-system/sw/bin/python` 3.14.7（CI 为 Python 3.12）；仓库外运行目录 `RUN_ROOT=/tmp/contact78-tests.GTiSLY`，`TMPDIR=$RUN_ROOT/tmp`、`PYTHONDONTWRITEBYTECODE=1`；用例只用标准库与仓库内夹具，不需要 Nix、APM、Skills 安装、eval、模型、网络、Zotero 或用户资料。
- 命令与分组完全按 test-plan §3.2；每组一次，原始 stdout/stderr 与退出码见 `$RUN_ROOT/Tn.log`。

## 逐项结果

| 项 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | `python -m unittest -v` 三个选择器，退出码 0、`Ran 3 tests`、`OK`（`/tmp/contact78-tests.GTiSLY/T1.log`）。混合负例的 `path_conflicting` 现按通用 `other_professor` 返回（`legacy_skipped` 为 identity_unreliable×2 + other_professor×2），合法条目写入与源文件字节不变断言均通过。 |
| T2 | 通过 | 六个选择器，退出码 0、`Ran 9 tests`、`OK`（`$RUN_ROOT/T2.log`）。两教授异名夹具下 Stage 1 快照归属、缺失条目命名自身目录、B stale/missing 与 A 正常路径、B 的合法 proof 误交 A 时 `invalid_params`（professor mismatch）且零写入均通过。 |
| T3 | 通过 | 八个选择器，退出码 0、`Ran 8 tests`、`OK`（`$RUN_ROOT/T3.log`，2.982s）。两笔 `professor_dir` 独立本地 pair、各自三段 `email_id`、隔离夹具的单坏 candidate-state 与 history-only pair、显示名目录误绑定负例、两项说明契约正则均通过。 |
| T4 | 通过 | `TestStage5ListInputDiscovery` 整类，退出码 0、`Ran 3 tests`、`OK`（`$RUN_ROOT/T4.log`）。无过滤逐包返回、精确合法名与精确越界包名的单行返回、不存在名字的 `needs_input/professor_not_found`（退出码 2）以及前后文件字节不变均通过。 |
| T5 | 通过 | 契约选择器退出码 0、`Ran 1 test`、`OK`（`$RUN_ROOT/T5-contract.log`）；人工静态核对结论见下节。 |

合计 24 个选择器加载的 24 个用例（去重后）全部通过，无失败、无错误、无跳过。

## T5 静态核对

- `same_name_other_dir` / `professor_ambiguous` 在当前产品脚本、说明、代理文档与安装投影中已无出现（全仓检索仅计划文件的历史叙述仍引用旧名）。
- 代码保留：`contact_targets.py` 的 `_entry_canonical` 与完整 `(professor, professor_dir, preview_path)` 元组比较、立即跳过与后续身份校验顺序未变；`stage5_list_input_rows`、partition/choices 算法、写入与邮件编号公式未改。
- 说明保留：Stage 0 的事务记录数组、canonical 路径与真实 `target_state`、逐教授失败隔离、`--professor` 精确匹配、坏包独立行、只读发现与零写入；两份 analyzer 的独立临时目录、preflight 证明关联、TOCTOU 校验与只清理自身目录均保留，只删同名附带条款。
- 安装源关系：`apm.yml` 依赖 `packages/professor-contact-{opencode,codex}`；`nix/contact.nix` 直接读取 `../.apm/` 与 `../packages/professor-contact-codex/.apm/` 源，无第二份业务正文，无需重建或重装。两份 analyzer 已同步同一段修改。
- 重引入检查：当前打开的产品 PR 只有 #92（`plan/stage2-evidence-level-fixes-20261017`）。它的分支仍带步骤 2.6 的旧措辞“含同名不同目录的教授”，并对同一行做了 Stage 2 证据改动；本 PR 不修改它的分支，合并时由后落地者按清理后的措辞整合，避免把该条款带回。

## 本地整仓回归（非正式必测项）

- 目的：确认说明与契约测试的连带影响，避免推送后 CI 变红；不作为第三关必测证据。
- 方法：按 `.github/workflows/ci.yml` 的四个分片模块清单（`scripts/check_test_shards.py --print shardN`）在 `tests/` 下逐片运行 `python -m unittest <modules> -v`。
- 结果：shard1 `Ran 380 tests ... OK`（111.1s）、shard2 `Ran 219 tests ... OK`（110.3s）、shard3 `Ran 188 tests ... OK`（103.9s）、shard4 `Ran 243 tests ... OK (skipped=1)`（100.8s），合计 1030 项；日志 `$RUN_ROOT/shard1.log`…`shard4.log`。
- 额外核对：受影响的说明契约模块合并运行退出码 0、`Ran 172 tests`、`OK`（`$RUN_ROOT/T5-doc-contracts.log`）。

## 仓库 CI（推送 `3024d46` 自动触发）

- 运行 [39258957355](https://github.com/ScholarWorkflow/professor-contact/actions/runs/39258957355)，head `3024d460699a188242787a493311800e8a990c4e`：`shards (shard1)` pass 1m57s、`shards (shard2)` pass 2m8s、`shards (shard3)` pass 1m18s、`shards (shard4)` pass 1m57s、聚合 `test` pass 4s，整体 `success`。
- 该运行由推送自动触发，不是本角色发起的正式执行；本地 T1–T5 结果与上表一致（CI 为 Python 3.12 / ubuntu-latest，本地为 Python 3.14.7 / macOS）。

## 未完成与说明

- test-plan §2.1 记录的“选择器静态预检”与本记录的执行使用同一套 `45c30fa` 测试代码；产品修改落地后选择器无需改动。
- 本轮未执行模型运行、安装重跑、eval、Zotero 或用户资料操作，符合 test-plan §1 的范围上限。
- 测试计划文件仍保留 `Proposed review status: pending`；本记录不自行补写第一关/第二关结论，也不代替合并批准。
- 下一负责人：测试计划审核者按当前文件复核第一、二关口；确认后由合并审核按 `Merge Reviewer Rule.md` 检查该 PR。
