# Issue #68 / PR #72 Test Engineer r14 权威记录

记录版本：`issue-68-gate2-r14-2026-10-04`。

r14 只修正 r13 Recipe 中“正式请求前后的服务来源与隔离证据没有接入正式入口”的缺口。Gate 1 冻结要求不变；`PC68-D1/P1–P7` 的既有正式 PASS 不重开；r13 的 raw final-answer selector、`gpt-6-luna` 请求、`skills-test-fixtures@c738fa2...` / adapter `@16` 不变。

自 r14 生效起，当前唯一 `PC68-R1` 正式入口为：

```text
.apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r14_codex.py
```

r13 及更早正式入口只保留历史用途，不再作为新执行指令。

## 1. 当前输入

```text
Requirement / Gate 1          = unchanged from issue-68-plan-r11 and prior approved Gate 1
r13 capability Preflight      = pr72-r13-preflight-exec-2026-10-04
r13 capability result         = CAPABILITY_CONFIRMED
r13 Preflight producer        = d6800a6ec12ed25e955c3393b6f91178f59ddc15
r14 Recipe implementation     = through 9084cd637d72270518c328624301e9a228bfd219
fixture                       = c738fa2f8bcbb16cd99d741332d5f59b062b6357
fixture contract              = skills-test-fixtures/codex-eval-adapter@16
eval-server frozen revision   = 3fdfa9387140cfc2e2aa3af415f85015f79706d2
formal host                   = Codex only
```

r13 Preflight 原始响应证明当前正式 profile 的 `output.app_server_events` 中存在且仅存在一个可归属的当前 root/current turn `assistant + phase=final_answer`；该请求使用 `gpt-6-luna`、`low`、`workspace-write`、fresh consumer 和相同 trust 形状。r14 没有修改请求构建器、final-source selector、模型、reasoning、sandbox、fixture adapter、eval-server revision 或观察字段，因此该 `CAPABILITY_CONFIRMED` 按复验依赖继续有效，无须重复模型请求。

## 2. r13 Recipe 缺口

r13 合同已经要求每次正式 `PC68-R1` 在验收请求前归档实际 eval 服务构建来源和隔离依据，但 `run_issue68_stage5_routing_r13_codex.py` 只校验/归档 producer 与 fixture，随后直接进入 `base.codex_host()`。它没有在正式请求前验证：

- 当前 `EVAL_PORT` 唯一监听进程；
- 监听进程 cwd 是否就是冻结的 clean `eval-server@3fdfa938...`；
- 监听 PID / 启动时间 / 命令行；
- 服务是否使用测试专用 `CODEX_HOME`；
- `sqlite_home`、`CODEX_SQLITE_HOME`、`log_dir` 是否落在测试状态目录；
- 请求后服务实例和存储边界是否仍为同一个。

因此 r13 Gate 2 不能仅凭 capability Preflight 转为 `PASS + COMPLETE`。

## 3. r14 修正

### 3.1 服务来源

正式入口在 `CASE_STARTED` 前必须：

1. 校验 producer、fixture、eval-server 三个 checkout 都是固定 revision 且 clean；
2. 用 `direnv exec <eval-root> printenv EVAL_PORT` 解析端口；
3. 用系统进程信息确认该端口只有一个 listener；
4. listener cwd 必须等于冻结 eval-server checkout；
5. listener command 必须是 `eval_server.py` 且端口一致；
6. 归档 PID、启动时间、命令行和 cwd。

任一步失败均为 `CASE_NOT_STARTED`，不得发出正式模型请求。

### 3.2 共享服务存储隔离

`issue68_eval_service_isolation_r14.py` 是唯一存储判定实现，隔离检查和正式入口共同调用它。它直接观察运行中 eval-server 进程的环境及 `$CODEX_HOME/config.toml`：

- `CODEX_HOME` 必须存在，且不能等于用户默认 `~/.codex`；
- `config.sqlite_home`、继承的 `CODEX_SQLITE_HOME`、`config.log_dir` 如存在必须被记录；
- 显式 SQLite / log 路径必须位于测试 `CODEX_HOME` 内；
- 未设置 `sqlite_home` 且未继承 `CODEX_SQLITE_HOME` 时，记录 `CODEX_HOME fallback`；
- 未设置 `log_dir` 时，记录 `CODEX_HOME-derived default`。

这只证明测试服务存储隔离，不是产品 PASS。

### 3.3 请求后复核

正式请求完成后，入口再次读取 eval-server revision、端口、PID、启动时间、cwd、command 和 storage evidence。任一变化时最终 verdict 固定为：

```text
INVALID_TEST_EXECUTION / eval_service_changed_during_execution
```

稳定时才保留 `base.codex_host()` 的原始 `PASS` / `FAIL_PRODUCT` / `BLOCKED_*` / `INVALID_*` 结论。

## 4. 当前固定资产

```text
.apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r14.json
.apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r14_codex.py
.apm/skills/professor-contact/tests/runtime/issue68_eval_service_isolation_r14.py
.apm/skills/professor-contact/tests/runtime/check_issue68_eval_service_isolation_r14.py
.apm/skills/professor-contact/tests/test_issue68_runtime_r14.py
```

`check_issue68_codex_final_source_r13.py` 继续作为 capability Preflight 的冻结入口；r14 不重复该模型请求。

## 5. Recipe Preflight

Recipe Preflight 分为两个互不替代的观察：

### 5.1 Final-source capability — `REUSE_PRIOR_PASS`

来源：用户提交的 `pr72-r13-preflight-exec-2026-10-04` 归档。

```text
status                  = CAPABILITY_CONFIRMED
formal_pc68_r1_allowed  = true
codex                    = codex-cli 0.159.0-alpha.12.1
backend                  = app-server
runtime_generation       = 1
termination_reason       = completed
raw current final count  = 1
selected text            = ok
```

该观察的声明依赖在 r14 未变化，因此复用。

### 5.2 Shared-service isolation — `EXECUTE_CURRENT`

该检查不发模型请求：

```bash
python .apm/skills/professor-contact/tests/runtime/check_issue68_eval_service_isolation_r14.py \
  --eval-direnv-root <eval-server-direnv-root> \
  --output-dir <fresh-output-dir>
```

唯一成功结果：

```text
ISOLATION_CONFIRMED
```

`CASE_NOT_STARTED` 表示服务来源、进程环境或存储隔离证据不足；不得执行正式 `PC68-R1`，也不得归因产品失败。无 retry。

## 6. 正式 PC68-R1 Recipe

只有 5.1 `CAPABILITY_CONFIRMED` 且 5.2 `ISOLATION_CONFIRMED` 后才能执行：

```bash
python .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r14_codex.py \
  --producer-root <clean-pr72-worktree> \
  --producer-sha <frozen-pr72-sha> \
  --fixture-root <clean-skills-test-fixtures-c738fa2-checkout> \
  --fixture-sha c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root <clean-eval-server-3fdfa938-checkout> \
  --output-dir <fresh-output-dir>
```

单次正式请求，不重试、不换服务、不换模型、不改断言。正式入口必须在 `provenance.json`、`eval-service-provenance.before.json`、`eval-service-provenance.after.json` 中保存运行版本、服务来源及隔离证据。

## 7. Gate 2 当前状态

当前：

```text
Gate 1                              = PASS + COMPLETE，未重开
PC68-D1/P1–P7                       = prior PASS，不重开
PC68-R1 final-source capability     = REUSE_PRIOR_PASS / CAPABILITY_CONFIRMED
PC68-R1 r14 deterministic tests     = pending CI at current head
PC68-R1 shared-service isolation    = EXECUTE_CURRENT / not run
Gate 2                              = PARTIAL / NOT COMPLETE
Gate 3                              = NOT_READY
Merge                               = NOT_READY
```

Gate 2 只剩两项事实：当前 r14 回归必须通过；本地执行一次 5.2 isolation check 并取得 `ISOLATION_CONFIRMED`。两项满足后测试工程师再做第 3.3 节完整复审；通过后才冻结 r14 并交第三关口执行正式 `PC68-R1`。
