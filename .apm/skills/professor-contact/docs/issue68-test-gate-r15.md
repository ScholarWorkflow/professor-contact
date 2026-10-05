# Issue #68 / PR #72 Test Engineer r15 完整权威记录

记录版本：`issue-68-gate2-r15-2026-10-04`。

本记录是第 68 号问题当前**唯一完整第二关口权威测试方案**。它完整取代 `issue-68-gate2-r14-2026-10-04`、`issue-68-gate2-r13-2026-10-04`、`issue-68-gate2-r12-2026-10-04` 及更早第二关口记录作为后续执行指令。旧记录、旧运行和旧证据继续保留审计价值，但执行者不得再拼接旧 Recipe 决定当前命令、输入、判定或前置条件。

本轮只整理首次 `PASS + COMPLETE` 所要求的单一完整记录，不修改产品代码、测试代码、解析或判定程序，不运行正式验收，不新增产品要求。

## 1. 当前正式输入与冻结版本

| 项目 | 当前权威值 |
| --- | --- |
| Requirement revision | `2026-09-29 user requirement — per-professor state at every stage` + 2026-10-01 独立合并澄清 |
| Frozen Acceptance Contract | `issue-68-gate1-r2-2026-10-02`，`PASS + COMPLETE` |
| Canonical Plan | `issue-68-plan-r11-2026-10-02` |
| Plan approval | `pr72-plan-r11-review-r2-2026-10-02`，P1–P4 `PASS + COMPLETE` |
| Base revision | `2ed4da800a6e2ff557d7b37a36db810ccddd5c7e` |
| 冻结产品与测试实现 revision | `92c4fc624ad4894fa31c8d3c7fed8a5a3568ece0` |
| Codex fixture | `skills-test-fixtures@c738fa2f8bcbb16cd99d741332d5f59b062b6357` |
| fixture contract | `skills-test-fixtures/codex-eval-adapter@16` |
| eval-server revision | `3fdfa9387140cfc2e2aa3af415f85015f79706d2` |
| Codex 正式配置 | `gpt-6-luna`，`model_reasoning_effort="low"`，`workspace-write` |
| 当前运行宿主 | Codex only |
| Merge Gate cases | `PC68-D1`、`PC68-R1` |

本记录发布本身只增加权威说明文件，不改变上表冻结的产品、测试实现、fixture、判定程序或运行输入。因此第三关口的产品与测试实现 revision 固定为 `92c4fc624ad4894fa31c8d3c7fed8a5a3568ece0`。若后续 PR 头部除本权威文档外再出现任何变化，须按第 9 节复验依赖先做影响分析。

## 2. 冻结要求 → 唯一证明负责者

| 冻结要求 | 唯一证明负责者 | 必须直接证明的事实 |
| --- | --- | --- |
| `R68-1`、`R68-6`：教授本地包是 Stage 5 正常事实源，禁止旧程序级包兜底 | `PC68-D1/P1` | 本地包正常；本地包缺失时旧包不能兜底；冲突或损坏旧包不能改变本地结果 |
| `R68-2`：`--email-id` 是严格单邮件范围；未选中邮件及无关选择不得阻断目标；目标自身继续严格拒绝 | `PC68-D1/P2` | 目标先解析；未选中坏邮件行和同教授未选中显式选择行是噪声；目标自身错误仍拒绝 |
| `R68-3`：无 `--email-id` 时只处理当前教授本地批量 | `PC68-D1/P3` | 同教授批量全部通过后才提交；不跨教授；不自动拆成逐邮件部分提交 |
| `R68-4`、`R68-7`：多教授独立事务及本地校验状态隔离 | `PC68-D1/P4` | A 已提交后 B 失败不修改 A；校验记录只修改指定教授本地状态 |
| `R68-5`、`AD68-2`：程序总览是独立派生文件，不成为本地提交条件，不共享 Stage 2/3 投影登记 | `PC68-D1/P5` | finalize 不触碰总览；总览自身哈希、幂等、人工修改保护；不读取或写入 `_contact_projections.json`；坏本地输入和旧程序级包不能污染总览 |
| `AD68-3`：独立 Stage 5 只读发现，本地坏包只影响自身 | `PC68-D1/P6` | `stage5-list-inputs` 独立发现、教授过滤、同名歧义、原因码及零写入 |
| `AD68-4`：选择身份为 `(canonical professor_dir, email_id)`，归属、歧义、重复和 wrapper 原样传递 | `PC68-D1/P7` | 显式目录先归属；旧格式唯一候选必须绑定；多候选排除规则；错误归属不转嫁；scope 校验；wrapper 原样传递 |
| `R68-4` 原生 owner 调用、`AD68-3` 已安装入口、`AD68-4` 原生 choices/scope 转发、`AD68-1` 等待消费及后置总览顺序 | `PC68-R1` | fresh consumer 中恰好两个 root-owned 正式 owner；各自只拿一份本地 `email_pack`，同时拿完整未改 `choices` 与 `choices_scope`；root 等待并消费两份真实结果；总览最多一次且只能在两个结果完成后开始 |
| `R68-6` migration owner、`R68-7` exact-named validator 路由 | 实现范围检查 | 第 68 号不新增 migration；不改变 validator 路由；不复制第 48、59、67 号问题的运行矩阵 |

没有其它 case 可以替代以上 proof owner。`PC68-R1` 不证明邮件正文、humanizer、网页查询、通用写锁或 migration；这些不属于本用例负责事实。

## 3. `PC68-D1`：确定性证明

### 3.1 固定证明集合

唯一证明入口文件：

```text
.apm/skills/professor-contact/tests/test_issue68_stage5_local_state.py
```

必须发现且只发现以下 7 个外层证明：

```text
test_stage5_local_pack_is_authoritative_and_global_fallback_is_forbidden
test_stage5_email_id_scope_is_local_and_unrelated_local_rows_are_noise
test_stage5_batch_without_email_id_never_crosses_professor_owner
test_stage5_multi_professor_partial_results_keep_owner_state_isolated
test_stage5_rebuild_overview_reads_owner_outputs_only_and_is_idempotent
test_stage5_list_inputs_discovers_local_packs_independently
test_stage5_choices_attribution_uses_canonical_directory_and_email_id
```

每个外层证明按 `PROOFS` 固定清单运行其组成测试。组成测试不得 skip、expected failure、unexpected success 或 error；发现集合变化属于无效执行。

### 3.2 正式入口与证据

若后继变化命中 D1 的复验依赖，固定执行：

```bash
uv run --python 3.12 python \
  .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing.py \
  --case PC68-D1 \
  --execution-kind acceptance \
  --producer-root "$PRODUCER_ROOT" \
  --producer-sha "$PRODUCER_SHA" \
  --output-dir "$D1_OUTPUT_DIR"
```

其中 `$PRODUCER_ROOT` 必须是 `$PRODUCER_SHA` 的干净工作树；`$D1_OUTPUT_DIR` 必须是 producer 外部的新目录。

直接证据：`case-started.json`、`proofs.json`、`unittest.txt`、`final-verdict.json`，以及执行前后 producer SHA / dirty 状态。

唯一判定：

- 恰好 7 个外层证明全部普通执行，全部组成断言成功 → `PASS`；
- 产品断言失败 → `FAIL_PRODUCT / product_assertion_failed`；
- 证明集合变化、skip、expected failure、unexpected success、error、错误 SHA、dirty tree 或执行步骤偏离 → `INVALID_TEST_EXECUTION`；
- `CASE_STARTED` 前无法建立合法前提 → `CASE_NOT_STARTED`。

### 3.3 当前处置：`REUSE_PRIOR_PASS`

当前不重跑 D1。正式 PASS 来源是 `c68740680eb8b853f555237c2419d6d9b93c1c8a` 的第二关口 r10 原始执行：7 个外层证明、30 个组成测试全部普通成功，失败、错误、跳过、预期失败和意外成功均为 0，来源为干净产品工作树且无手工修改。

该 PASS 已经在 r11 通过影响分析延伸到 `d49f587753aed5721b2fe7ddff465e96c0621212`。`d49f587... → 92c4fc...` 的后继差异只增加或修改 r12–r14 的运行测试、运行判定资产和测试说明，没有修改 `contact_state.py`、Stage 5 产品实现、`test_issue68_stage5_local_state.py` 或其组成测试，因此不命中 D1 的被测行为、输入、断言或判定。当前决定继续为 `REUSE_PRIOR_PASS`。

## 4. `PC68-R1`：Codex 原生路由验收

### 4.1 固定测试资产

```text
.apm/skills/professor-contact/tests/runtime/prepare_issue68_stage5_routing.py
.apm/skills/professor-contact/tests/runtime/build_issue68_codex_request_r12.py
.apm/skills/professor-contact/tests/runtime/verify_issue68_stage5_routing.py
.apm/skills/professor-contact/tests/runtime/verify_issue68_stage5_routing_r13.py
.apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r13.py
.apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r14.json
.apm/skills/professor-contact/tests/runtime/issue68_eval_service_isolation_r14.py
.apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r14_codex.py
```

当前唯一正式 `PC68-R1` 入口：

```text
.apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r14_codex.py
```

r13、r12、r11 及通用 runner 的直接调用均不得作为当前 `PC68-R1` 正式执行入口。

### 4.2 固定业务输入与正式入口类别

正式入口在 fresh consumer 中通过受支持的 `apm install https://github.com/ScholarWorkflow/professor-contact.git#<producer_sha> --target codex --trust-transitive-mcp` 安装精确 producer SHA，不允许本地路径、symlink、editable install、复制或手工修补。

固定合成业务输入由 `prepare_issue68_stage5_routing.py` 产生：两个合法教授本地包 A/B、一个非法包 C、完整原始 `choices`、完整 `choices_scope`、固定根提示。执行只覆盖 Stage 5 路由到核验边界，不要求生成真实邮件正文。

Codex 正式请求固定使用 `gpt-6-luna`、`model_reasoning_effort="low"`、`workspace-write`，由现有 eval service 接受一次请求。不得启动、停止或重启 eval service，不得 retry，不得改模型、提示词、sandbox、fixture、断言或业务数据寻找成功结果。

## 5. `PC68-R1` Recipe Preflight

该用例依赖真实 runtime 事件、正式委派、外部 eval service 和自定义判定程序，因此第二关口必须确认 `Executable`、`Isolated`、`Observable`、`Discriminating`。

### 5.1 `Executable` 与 `Observable`：已确认

来源：`pr72-r13-preflight-exec-2026-10-04`，测试工程师已经从原始 `response.json` 独立重判。

固定结果：

```text
status                  = CAPABILITY_CONFIRMED
formal_pc68_r1_allowed  = true
codex                    = codex-cli 0.159.0-alpha.12.1
backend                  = app-server
runtime_generation       = 1
termination_reason       = completed
current root/turn final candidates = 1
selected text            = ok
```

当前唯一根业务终态来源为同一 `/eval` 响应 `output.app_server_events[]` 中同时满足：

1. `runtime_generation == output.runtime_generation`；
2. `message.method == "rawResponseItem/completed"`；
3. `message.params.threadId == output.thread_id`；
4. `message.params.turnId == output.turn_id`；
5. `message.params.item.type == "message"`；
6. `message.params.item.role == "assistant"`；
7. `message.params.item.phase == "final_answer"`。

必须恰好一个候选，其 `content[]` 中 `type=output_text` 的 `text` 按顺序拼接。旧 generation、child thread、旧 turn、commentary、缺失或未知 phase、非 message 项均不得成为终态来源。

r14 没有修改请求构建器、final-source selector、模型、reasoning、sandbox、fixture adapter、eval-server revision 或观察字段，因此该能力检查按声明复验依赖继续有效，不重复模型请求。

### 5.2 `Isolated`：已确认

来源：`pr72-exec-r14-isolation-2026-10-04`，执行恰好一次，不发模型请求，无 retry。

固定结果：

```text
status      = ISOLATION_CONFIRMED
eval_server = 3fdfa9387140cfc2e2aa3af415f85015f79706d2, dirty=no
port        = 17902
pid         = 40721
start       = Sat Oct  3 19:04:39 2026
cwd         = /Users/rekidunois/code/skill-repos-dev/eval-server
CODEX_HOME  = /private/tmp/test-codex-home
SQLite      = /private/tmp/test-codex-home/sqlite (config.sqlite_home)
log         = /private/tmp/test-codex-home/log (config.log_dir)
```

`CODEX_HOME` 不是用户生产 `~/.codex`；显式 SQLite 与日志目录均位于测试 `CODEX_HOME` 内。正式入口在请求前重新取得同类证据，请求后再次取得并要求同一 port、PID、启动时间、cwd、command、storage evidence 和 clean eval-server revision。

### 5.3 `Discriminating`：已确认

`test_issue68_runtime_r13.py` 和现有 verifier 回归已经固定三个判定通道：

- 当前合法终态满足要求 → 可进入业务 oracle 并产生 `PASS`；
- 当前合法终态违反正式要求，例如最终消息改写 owner 结果、owner 数量错误、choices/scope 改写、目录改写或聚合顺序错误 → `FAIL_PRODUCT`；
- 缺支持的正式观察 → `BLOCKED_OBSERVABILITY`，证据损坏或歧义 → `INVALID_EVIDENCE`，外部 runtime/transport 不可用 → `BLOCKED_DEPENDENCY`，Recipe 或运行环境漂移 → `INVALID_TEST_EXECUTION`。

已覆盖的关键反例包括：旧 turn 正确但当前 final 违反要求必须判产品失败；当前只有 commentary 或没有 final 必须判观察阻断；当前两个 final 必须判无效证据；selected raw message 或 `turnId` 损坏必须判无效证据。不存在用历史文本替代当前 final 的路径。

因此四项 Preflight 条件均满足，本轮不再增加新的执行前检查。

## 6. `PC68-R1` 正式 Recipe

### 6.1 前提

正式执行前必须同时满足：

- producer 为 `92c4fc624ad4894fa31c8d3c7fed8a5a3568ece0` 的干净工作树；
- fixture 为 `c738fa2f8bcbb16cd99d741332d5f59b062b6357` 的干净工作树；
- eval-server 为 `3fdfa9387140cfc2e2aa3af415f85015f79706d2` 的干净工作树；
- 5.1 的 `CAPABILITY_CONFIRMED` 与 5.2 的 `ISOLATION_CONFIRMED` 仍满足声明复验依赖；
- 输出目录为空且位于 producer、fixture、eval-server 工作树之外。

### 6.2 唯一正式命令

```bash
uv run --python 3.12 python \
  .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r14_codex.py \
  --producer-root "$PRODUCER_ROOT" \
  --producer-sha 92c4fc624ad4894fa31c8d3c7fed8a5a3568ece0 \
  --fixture-root "$FIXTURE_ROOT" \
  --fixture-sha c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root "$EVAL_DIRENV_ROOT" \
  --output-dir "$R1_OUTPUT_DIR"
```

只执行一次。禁止 retry、换服务、换模型、改提示、改断言、改 fixture、改 sandbox 或手工修改 consumer。

### 6.3 必须归档的机器证据

至少保存：

```text
provenance.json
eval-service-provenance.before.json
eval-service-provenance.after.json
codex/install.json
codex/install.stdout.txt
codex/install.stderr.txt
codex/apm.lock.yaml
codex/installed-entrypoint.json
codex/fixture-manifest.json
codex/canonical-choices.json
codex/expected-scope.json
codex/root-prompt.txt
codex/config.toml.before
codex/config.toml.after
codex/codex-request.json
codex/case-started.json
codex/codex-response.json
codex/codex-adapter.json
codex/shared-parser.stdout.txt
codex/shared-parser.stderr.txt
codex-verdict.json
final-verdict.json
```

还须保留 runner 已产生的 owner 输入、初始文件、命令输出和其它本次运行证据；不得只摘录成功字段。

## 7. `PC68-R1` 唯一判定

正式 ownership 只依据 fixture adapter @16 的 formal topology；当前 adapter contract 中以 `sender_thread_id` 判断 root owner 归属。identity diagnostics 只用于诊断，不能创造、修改、升级或降级正式 ownership。

正式业务判定至少直接检查：

- root 有且只有两个 `spawnAgent` formal children；
- 每个 child 恰好对应 A/B 中一份合法 `email_pack`，不能重复或交换；
- 每个 child 的业务 payload 含完整、未改的 `choices` 与 `choices_scope`；
- 每个 child 的完成与 root wait 可观察，wait 不得早于 owner completion；
- owner 返回结果保留原 `professor_dir`，状态为核验边界允许的 `needs_input` / `needs_refresh`，原因非空；
- root 最终消息对每个教授只保留一个与 owner 返回一致的结果，不得改写、丢失或制造冲突；
- discovery 的合法 A/B 和非法 C 集合保持；
- aggregate rebuild 最多一次，且开始时间必须晚于两个 owner 结果完成点。

终态：

| 终态 | 条件 |
| --- | --- |
| `PASS` | 正式执行已开始；正式拓扑、payload、owner result、root consume、discovery 与 aggregate 顺序全部满足；请求前后服务及存储边界完全一致 |
| `FAIL_PRODUCT` | 执行有效且证据完整，但上述任一正式产品要求被违反 |
| `BLOCKED_OBSERVABILITY` | 正式支持的 acceptance fact 无法直接观察，不能唯一判断产品行为 |
| `BLOCKED_DEPENDENCY` | eval transport、runtime 或外部依赖在正式执行中不可用，且无产品归因证据 |
| `INVALID_EVIDENCE` | 原始证据损坏、歧义、归属冲突、shared adapter 无法提供合法结构化证据 |
| `INVALID_TEST_EXECUTION` | Recipe、revision、服务实例、存储边界或执行条件在 `CASE_STARTED` 后漂移；包括请求后服务变化 |
| `CASE_NOT_STARTED` | producer/fixture/eval-server revision、输出目录、监听服务、测试存储或其它 bootstrap 前提在正式请求前不成立 |

任何 `FAIL_PRODUCT` 不得被改写为 blocked/invalid；任何 blocked/invalid 也不得凭模型文字推成产品失败。

## 8. 禁止副作用与执行约束

- 不启动、停止或重启现有 eval service；
- 不使用用户生产 `CODEX_HOME`、SQLite、日志或真实业务资料；
- 不手工修补 consumer、安装产物、fixture、agent、skill、MCP 配置或测试证据；
- 不修改正式 prompt、模型、sandbox、输入、parser、evaluator、断言或 PASS 条件；
- 不执行 OpenCode；当前 `PC68-R1` 只有 Codex；
- 不以端口可达、服务 ready、`tools/list` 或身份自述替代 acceptance evidence；
- 保留全部正式尝试；当前 Recipe 无 retry 条件。

## 9. 复验依赖

### `PC68-D1`

仅当以下任一项变化可能影响对应证明时重开受影响 P1–P7：

- Stage 5 本地包权威、选择解析、finalize、总览、只读发现、validation 本地状态等产品行为；
- `test_issue68_stage5_local_state.py`、其 `PROOFS` 组成测试或断言；
- D1 runner 的发现集合、证据或 verdict 逻辑；
- Gate 1 正式要求或相关上游 contract 发生有效变更。

只改变 `PC68-R1` runtime 证据、Codex 模型配置或 eval service 观察面，不自动重开 D1。

### `PC68-R1`

以下任一变化须先做影响分析，命中时重做相应 Preflight 或正式执行：

- producer 的 Stage 5 root routing、owner agent contract、choices/scope transport、wait/consume 或 aggregate 顺序；
- `prepare_issue68_stage5_routing.py`、根 prompt、request builder、共享 parser、r13 final-source selector、业务 verifier、r14 runner 或 r14 evidence contract；
- fixture revision 或 `codex-eval-adapter@16` formal topology 语义；
- eval-server revision、正式事件字段、服务运行来源或测试存储隔离方式；
- `gpt-6-luna` / low、sandbox、正式 Codex profile 或受支持请求方式；
- Gate 1 正式要求或当前 Canonical Plan 中会改变 R1 负责事实的约束。

仅修改说明文字且不改变以上任何依赖时，不重跑。

## 10. 第二关口完整复审

首次 `PASS + COMPLETE` 前按 Test Engineer Rule §3.3 对完整方案重新检查：

1. `R68-1..R68-7 + AD68-1..AD68-4` 均有唯一 proof owner 或明确的实现范围检查，没有遗漏；
2. 只有 `PC68-D1` 与 `PC68-R1` 两个 Merge Gate case，各自只证明负责事实，没有重复业务运行；
3. 两个 case 的工作目录、命令、输入、fixture、runtime 配置、证据、parser、PASS 和其它终态均已固定；
4. `PC68-R1` 的 `Executable`、`Isolated`、`Observable`、`Discriminating` 均已有当前有效证据；
5. evaluator 的 PASS / FAIL / blocked-invalid 三通道及“产品失败不能被降级”反例已经固定；
6. r12 的 `root_thread_read`、旧 fixture、旧多宿主命令等失效检查不再作为当前执行前提；
7. verdict 可以从当前固定 Recipe 和机器证据机械得出；
8. 当前没有剩余测试设计或执行实现 blocker。

结论：

```text
Test Engineer Gate 1: PASS
Gate 1 review completeness: COMPLETE

Test Engineer Gate 2: PASS
Gate review completeness: COMPLETE
Authoritative Gate 2 revision: issue-68-gate2-r15-2026-10-04

PC68-D1/P1-P7: REUSE_PRIOR_PASS
PC68-R1: EXECUTE_CURRENT
Gate 3: READY
Merge: NOT_READY
```

第二关口通过只表示当前完整测试设计、Recipe、Preflight、证据和判定程序可以冻结，不表示正式 `PC68-R1` 已通过，也不表示 PR 可以合并。

## 11. 下一责任人

下一责任人：**本地执行代理**。

唯一动作：按第 6.2 节命令，对冻结 producer `92c4fc624ad4894fa31c8d3c7fed8a5a3568ece0` 执行一次 `PC68-R1`，完整保留第 6.3 节及 runner 产生的全部证据，不修改任何冻结资产，不 retry。执行结束后把完整结果交给测试计划审核者按第三关口规则审核。
