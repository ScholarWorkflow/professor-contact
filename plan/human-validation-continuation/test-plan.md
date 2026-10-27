# Human validation continuation — TP1

- Requirement R1 / execution EP1.1; baseline `18fd48d1b6f2e26241c304d6acddb025297f08e4`.
- Proposed review status: pending. Focused test assets and the executable recipe are prepared; no implementation/tests run or PASS claimed. [EP1.1](execution-plan.md) defines the sole intended contract; [review](review.md) records independent decisions.
- Rules: [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253), [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d); versions in EP1.1.

## Required checklist — acceptance ceiling

| Goal / input | Expected result | Sufficient check |
|---|---|---|
| C-A: Stage2 and Stage3 terminal two-round failure, explicit +2 then exhausted +1 grant | Default remains2; effective limit4 then5; actual rounds advance without reset through correction/record; successful later result stops; old failure/report/history retained | Focused product command tests using existing per-stage synthetic fixtures; direct JSON and result assertions. Exercise one cumulative path per stage, not every possible number |
| C-B: No grant, invalid nonpositive grant, repeated grant on reopened state, next-round jump or terminal pass | No automatic extension/restart or extra validation accepted; no failure erased; no mutation on rejected requests | Representative command tests for these directly changed admission rules; existing default2 results reused where unchanged |
| C-C: Continued correction with Stage2 fixed-source block and Stage3 recorded global/scoped findings | Fixed block stays with source/generator owner; only recorded failed scope reopens; untouched machine facts/candidates preserved; current render/input binding remains required | Reuse Stage2 fixed-evidence and Stage3 correction fixtures/assertions in the focused per-stage tests; no new boundary matrix |
| C-D: Legacy no-policy records and real new-cycle transition | Legacy terminal unchanged unless explicitly granted; preserved historical failure; new genuine cycle default2/no inherited grant, no-op correction/rerender does not reset | Direct state lifecycle assertions at existing acceptance/carry boundary, with one actual changed-source/new-generation fixture |
| C-E: Runtime instructions, result readers and Stage5 boundary | Human must choose N for named stage/professor; native delegation/correction contracts retained; extended result recognized by direct Stage2/3 readers; Stage5 unchanged | Static review of affected caller/reader changes plus existing assertions only where directly modified; do not add a Stage5 workflow run |

Each stage needs one integrated command path because it has distinct state consumers. No separate live-model repetition for each limit, no numeric boundary sweep, no default-three migration, statistics, total workflow, installation matrix, credential authenticity tests or new test framework. Human identity is the stated caller trust boundary, not a claim to test cryptographic authorization.

## 可执行 recipe（实现落地后执行；本轮未运行必测用例）

本轮固定以下 selectors。实施负责人须在 Gate2 前记录受测实现的提交与解释器，并确认实现与这些 selectors 一致；EP1.1 允许入口和标志一致重命名，不允许省略语义。若重命名，本节和测试模块须在同一提交内同步修改，不另写第二份手册。

| Selector | 本轮准备值 |
|---|---|
| Stage2 授权入口 | `stage2-continue-validation --professor-dir DIR --additional-rounds N --authorization TEXT --expected-round R --expected-state-sha256 SHA` |
| Stage3 授权入口 | `stage3-continue-validation`（同一组标志） |
| continuation 成功输出 | `status=ok`、`round`、`round_limit`、`remaining` |
| record 成功输出 | `round`、`round_limit`（有效上限在记录轮次后仍可读） |
| 阶段状态文件 | Stage2 `套磁候选输入.json`；Stage3 `套磁候选状态.json` |
| continuation | `validator.continuation = {"version": 1, "base_limit": 2, "grants": [...]}`；每条 grant 含 `old_limit`、`additional_rounds`、`new_limit`、`granted_at`、`authorization`、`exhausted_round`、`expected_state_sha256`；grant 后当前 `validator.results` 保留刚耗尽的失败行，直到下一轮记录替换 |
| 每轮 history | `validator.history[]` 对每个实际记录轮次各留一行（含最终通过轮）；每项含 `round`、`results`、`render_sha256`、`validation_file`、`validation_sha256`；Stage2 另含 `pack_sha256`，Stage3 另含 `input_fingerprints`（每轮的输入绑定）；授权不重复追加已记录轮次 |
| 扩展终态 | 结果行 `result="fail_after_max_rounds"`，带 `rounds` 与 `max_rounds`；未扩展的两轮仍为 `fail_after_2_rounds` |
| 新周期保留 | 状态顶层 `validation_history` 列表保存被替换的旧 validator；无操作 rerender 不改变当前 validator |
| 人类授权示例 | 合成文本 `用户明确要求继续修订合成稿件。`；不读取或提交真实对话 |

未到上限的中间失败轮沿用既有结果标签：Stage2 `needs_correction`、Stage3 `fail`；只有扩展终态改为 `fail_after_max_rounds`，未扩展终态仍为 `fail_after_2_rounds`。

授权后 Stage2 `validator.phase` 为 `needs_correction`，pending 只含已记录失败方向（键为 direction ID）；Stage3 pending 键为 `direction:<id>` 或 `group:<id>`，只由终态失败行恢复，已通过范围不重新打开。

1. 在受测 producer checkout 根目录执行，使用已有 Python 与既有 unittest，不安装依赖，不读取用户教授目录、模型服务或 Zotero。本轮的预检解释器为 `/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3`（Python 3.14.7）；正式执行记录实际使用的解释器和提交，不把本轮预检版本当成受测实现。该 store 路径不存在时改用同一机器上已有的 Python 3.12+ 解释器，并在执行记录中写明实际路径。

2. 正式执行前先确认受测版本包含本模块：记录 `git rev-parse HEAD`，并执行 `git cat-file -e HEAD:.apm/skills/professor-contact/tests/test_human_validation_continuation.py`。随后从同一提交运行第 3 步，记录实际执行提交、`Ran N tests` 数量及每项结果；模块缺失或 0 项测试时停止，记未执行，不记通过。

3. 以下命令从 checkout 根目录运行；`RUN` 为本次唯一隔离目录，临时测试根和 Stage3 handoff 目录通过 `TMPDIR` 落在 `$RUN/tmp`：

```bash
set -o pipefail
RUN=$(mktemp -d /tmp/contact-validation-continuation.XXXXXX)
mkdir -p "$RUN/tmp"
export TMPDIR="$RUN/tmp"
PYTHON=/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3
"$PYTHON" --version 2>&1 | tee "$RUN/python-version.txt"
git rev-parse HEAD 2>&1 | tee "$RUN/tested-commit.txt"
git cat-file -e HEAD:.apm/skills/professor-contact/tests/test_human_validation_continuation.py
"$PYTHON" -B -m unittest discover \
  -s .apm/skills/professor-contact/tests \
  -p 'test_human_validation_continuation.py' -v 2>&1 | tee "$RUN/continuation.out"
```

4. 必测目标到测试方法的唯一映射（模块共 8 项）：

| TP1 目标 | 测试方法 |
|---|---|
| C-A Stage2 | `Stage2ContinuationTests.test_c_a_extended_rounds_accumulate_and_keep_old_failures` |
| C-B Stage2 | `Stage2ContinuationTests.test_c_b_stage2_rejected_requests_leave_the_record_unchanged` |
| C-C Stage2 固定来源阻塞 | `Stage2ContinuationTests.test_c_c_stage2_fixed_source_block_stays_owner_work_after_a_grant` |
| C-D Stage2 旧记录 | `Stage2ContinuationTests.test_c_d_stage2_legacy_record_needs_an_explicit_grant` |
| C-A Stage3 | `Stage3ContinuationTests.test_c_a_extended_rounds_advance_through_the_real_handoff` |
| C-B Stage3 | `Stage3ContinuationTests.test_c_b_stage3_rejected_requests_leave_the_state_unchanged` |
| C-C Stage3 全局与未触碰范围 | `Stage3ContinuationTests.test_c_c_stage3_global_findings_and_untouched_scopes_survive_the_grant` |
| C-D Stage3 新周期 | `Stage3ContinuationTests.test_c_d_stage3_new_cycle_starts_at_two_and_preserves_history` |

单项复跑使用同一解释器，工作目录切到 `.apm/skills/professor-contact/tests`：

```bash
"$PYTHON" -B -m unittest -v \
  test_human_validation_continuation.Stage2ContinuationTests.test_c_a_extended_rounds_accumulate_and_keep_old_failures \
  2>&1 | tee "$RUN/c-a-stage2.out"
```

每阶段的准备输入固定为合成夹具：Stage2 使用单方向 `DIR00001`（论文 `AAAA1111`、`BBBB2222`、`CCCC3333`，两轮合成叙述发现，以及固定卡片引文 `评估时间：`）；Stage3 使用 `dir_A` / `dir_B` 两个方向（各 3 个候选，失败引文 `候选 dir_B_2`，全局前导引文 `本文件不复述`）。测试进程的 tempfile 根和 Stage3 handoff 目录都在 `$RUN/tmp` 下，原始报告、状态和输出不进入仓库。

5. 断言直接读取命令 JSON、阶段状态文件和原始报告字节：实际累计轮次、有效上限、grant 字段、每轮 history、扩展终态标签、旧报告未被覆盖，以及被拒请求前后状态文件字节不变。C-A 每阶段只走一条累计路径（2→4→5，不逐一穷举数字），Stage3 第 3、4、5 轮都走 `prepare → write → save → record`，不退回直接记录；C-B 覆盖 0/负数/空授权/错误轮次/错误摘要/重复授权/跳轮/终态通过/渲染或输入漂移的代表性准入；C-C 复用 Stage2 固定来源和 Stage3 全局发现、修正夹具；C-D 使用一条真实新生成边界和一次无操作 rerender。不增加边界矩阵、完整工作流、Stage5 运行、安装矩阵或新判定框架。

6. C-E 只做静态阅读，不运行工作流：以受测提交的实际 diff 为准，核对本次改动的 runtime 说明和读取器。预计涉及的说明文件为 `.apm/skills/professor-contact/SKILL.md`、`.apm/skills/professor-contact/docs/workflow-reference.md`、`.apm/agents/professor-contact.agent.md`、`.apm/agents/professor-contact-idea-generator.agent.md`、`.apm/agents/professor-contact-style-validator.agent.md` 和 `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md`、`packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md`（后两者是实际存在的投影，不假设二者之外的 package agent 文件）。确认必须由人类为指定阶段和教授给出 N、代理不得自增或默认 N、累计轮次与历史可见、Stage2 保留 pack-only 修订、Stage3 沿用原调用凭据和 `prepare → validator → save → record`，Stage5 不变。再核对 `_stage2_preflight.py` 的接受判断、`_stage2_validation.py` 的 round/终态标签校验与生成、`_stage3_validation.py` / `_stage3_handoff.py` 的轮次读取、`_stage3_commands.py` 的直接结果消费者、`contact_state.py` 的 Stage5 `load_validator_results` 和 `_stage5_commands.py` 的 Stage5 校验（`fail_after_2_rounds` 仍要求 `rounds=2`，不接受 `fail_after_max_rounds`），确认扩展终态标签只被 Stage2/3 的合规 continuation 接受，Stage5 契约未改。发现问题按范围交实现负责人，不在本测试中改产品。

7. 结果按通过、业务失败、无法判断、未执行四类记录；首轮失败与后续有理由的复验都保存在 `$RUN`，只提交脱敏摘要。实现尚未落地时命令不存在或 argparse 拒绝，记未执行。缺依赖、导入失败或环境不可用记无法判断。同一未变失败不连续重跑；仅在一次具体外部准备修正后允许同输入重试，改输入、预期或命令视为 recipe 修订并先评估受影响目标。

## 准备与预检记录（2026-10-27）

- 预检版本：`8a4dcc027b1d17c2726679c52f87d8d1b763cecb`（本轮开始时的 PR head）。该提交只有计划，尚无 continuation 实现，不能用于正式执行；正式执行按第 2 步记录受测实现提交。
- 解释器：`/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3`（Python 3.14.7）。
- 交付的测试资产：
  - `.apm/skills/professor-contact/tests/test_human_validation_continuation.py`：上述 8 项 Stage2/Stage3 continuation 命令测试；复用同仓 `BaseEnv` 的 Stage2 fixture 构造、固定来源场景和 `Stage3DirectionGroupBase`，不依赖 PR143/PR145 的未合入测试或改动。
  - `plan/test-grouping/shards.json`：模块登记到 shard4，stage 记为 `mixed:stage2+stage3`；`/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3 scripts/check_test_shards.py` 返回 `OK: 83 test modules across 4 shards, each with a stage`；`totals.modules` 同步改为 83，`seconds` / `tests` 是生成时的历史测量值，未按本轮新模块重算。
- 有限预检（临时目录 `/tmp/pr146-test-prep-20261027`，未调用 `stage2/3-continue-validation`，未执行必测用例）：
  - 解释器可用；`contact_state.py --help` 退出码 0，当前 runner 没有 continuation 子命令（符合实现前状态）。
  - 新模块可导入并收集 8 项测试，`py_compile` 通过。
  - 既有夹具可生成可用输入：Stage2 两轮失败终态（`round=2`、`phase=terminal`、`result=fail_after_2_rounds`、pending `DIR00001`）；Stage2 第二轮命中固定卡片文字得到 `fixed_blocking`（owner `generator`）；Stage3 两轮失败终态（`result=fail_after_2_rounds`）、可捕获 invocation 凭据；Stage3 全局引文被路由到 `direction:dir_A` 与 `direction:dir_B` 两个范围，修正后进入第二轮终态。
  - 夹具准备中观察到两个待实现差异，仅作为准备事实，不是正式测试结论：当前无操作 Stage3 rerender 会把 `validator.round` 归 0；当前真实新生成会直接丢弃旧 validator，没有保留历史字段。
- 未完成：Gate2 未确认（实现未落地、实现 SHA 未记录）；Gate3 未执行；本轮没有正式通过结论。下一负责人：产品实现负责人先落地 EP1.1 与上述 selectors，再由本地执行工程师按 recipe 运行并记录。
- 2026-10-27 复核后修订：Stage3 第 4、5 轮改为完整交接；history 检查覆盖第 1–5 轮（含最终通过轮）的结果、报告路径与摘要；Stage2 C-D 补真实新生成周期断言；C-D 的 Stage3 第 3 轮也走完整交接；旧记录用例只要求保留已有失败结果，不要求补造历史。测试数量仍为 8。

## Review and delivery

Independent reviewer confirms test design/Gate1 and later Gate2 executable wiring. Execution owner records PASS/business failure/unable-to-judge/unexecuted per target; Gate3 reviewer evaluates recorded results without re-certifying source or rerunning unaffected checks. Plan-only commits do not invalidate prior evidence. Implementation and all formal results remain pending at this PR's publication.
