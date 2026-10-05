# Issue #68 / PR #72 Gate 2 候选记录 r27 — 测试计划第23版 单一权威测试实现

记录版本：`issue68-r27-r23-candidate-2026-10-05`。

本文件是当前单一测试候选记录，测试计划见 [当前测试计划](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-5993806361)。第二关口尚待独立审核；第三关口尚未运行，状态为 NOT READY。

## 0. 版本绑定（全部固定到真实提交）

| 角色 | 版本 | 说明 / 影响分析 |
| --- | --- | --- |
| 被测产品 | `ScholarWorkflow/professor-contact@35f2785b4d13783683860db910a36add2347bd29` | 产品 Stage-5 实现完成于 `a229012`；产品脚本不变；本次仅调整代理说明、测试与文档，实际业务入口及输入输出不变 |
| 测试实现 / 判定程序（代码） | `ScholarWorkflow/professor-contact@4c69b5d555f368c320463917d35424e1c5bda33d` | 当前判定程序、组件映射及非正式解析器回归固定在此代码提交 |
| 当前记录所在提交 | 本文件的后续文档提交 | 仅固定记录；不改变代码、业务说明或证据契约 |
| 共享 fixture adapter | `skills-test-fixtures@c738fa2f8bcbb16cd99d741332d5f59b062b6357`（adapter@16） | 未变 |
| eval-server | `3fdfa9387140cfc2e2aa3af415f85015f79706d2`（检出干净） | 未变 |
| 模型/请求 | Project Consensus 默认 `gpt-6-luna`，`build_issue68_codex_request_r12.py` | 未变 |

## 1. 权威输入

```text
Frozen Acceptance Contract:  第68号议题当前验收约定
Canonical Plan:              issue-68-plan-r12-2026-10-04（APPROVED）
Test Plan:                   issue-68-test-plan-r23-2026-10-05（评论 5993806361）
Runtime evidence contract:   issue-68-runtime-evidence-r26-2026-10-05（文件名 issue68-runtime-evidence-contract-r19.json，
                             以 revision 字段为准）
```

## 2. Requirement → proof owner → case（测试计划第23版 §2 完整 mapping）

两个正式 case：`PC68-D1`、`PC68-R1`；不新增 case。R68-1…R68-8、AD68-1…AD68-5 的负责者与事实沿用测试计划 r23：

| 正式要求 | 证明负责者 | 必须证明的事实 | 实现落点 |
| --- | --- | --- | --- |
| `R68-1` | `PC68-D1/P1` | local `email_pack` 唯一 authority；无 global fallback / dual authority | t68_1 / t68_1b / t68_1c / t68_2 |
| `R68-2` | `PC68-D1/P2` | targeted 只处理目标；无关行不阻断；目标自身 fail closed | t68_3 / t68_4 / unselected_malformed_noise + r11 targeted 过滤 |
| `R68-3` | `PC68-D1/P3` | 无 `--email-id` 只覆盖当前 pack；same-professor batch 整笔语义 | t68_5 + `TestStage5BatchStaysAtomic` |
| `R68-4` | `PC68-D1/P4` | A/B 独立 transaction；B 失败不回滚/阻断合法 A | t68_6 / validation_updates_only |
| `R68-5` | `PC68-D1/P5` | overview 是派生输出，不进 local finalize commit gate | t68_7 + `TestStage5OverviewRebuild` |
| `R68-6` | `PC68-D1/P1` | #68 不新增 migration/global fallback/dual-read/dual-write | P1 组件；随当前完整 PC68-D1 入口执行 |
| `R68-7` | `PC68-D1/P2 + P4` | validator / record-validation 只以当前 professor 本次输出为条件 | P2 targeted 组件 + P4 validation_updates_only |
| `R68-8` | `PC68-D1/P4 + P7`、`PC68-R1` | 当前 owner 实际用于 Stage 5 业务处理的数据只属于当前 professor；sibling 数据不得进入 plan/finalize/validation/state/render/output，也不得影响当前 owner 结果 | P4 transaction/validation 面 + P7 partition/bundle 面 + runtime sibling oracle |
| `AD68-1` | `PC68-R1`（`P5` 辅助） | root 委派 owner，消费各 owner 结果后恰好一次 rebuild overview，并单独报告总览结果 | runtime 回执消费链 + 总览调用及结果报告 oracle |
| `AD68-2` | `implementation_scope: #48` | writer-lock ownership 归 #48；#68 不改 writer ownership / canonical rebuild interface | 无测试组件；触碰接口时才重开 |
| `AD68-3` | `PC68-D1/P6` | standalone discovery 只读；坏 B 不影响合法 A/C | `TestStage5ListInputs` 全类 + scope-emission 负向 oracle + cx7 |
| `AD68-4` | `PC68-D1/P7`、`PC68-R1` | raw multi-professor choices 由 root deterministic partition；每 owner 实际业务调用只消费分配给自己的 rows；legacy ambiguity 不影响无关 owner | P7 partition 全类 + runtime partition oracle + 消费面 sibling oracle |
| `AD68-5` | `PC68-D1/P7`、`PC68-R1` | 当前 owner 实际消费的 canonical `professor_dir`/`email_pack`/`email_id`/choice rows 保持原值；不得转写、重建或错归属 | P7 行保持/隔离 oracle + runtime `canonical_preservation` |

`PC68-D1` 必须通过完整固定入口执行，不能只运行选定 proof。P1/P5 此前的 PASS 只能作为未改变事实的支持证据，不能替代当前 PC68-D1 完整入口；此前记录不表示当前正式用例已通过。PC68-D1 当前完整入口中的七个 proof 各运行一次。

确定性组件映射唯一归属一个 proof。同一确定性测试只执行一次：P4 仅包含教授间 transaction 与 named-local-validation 两项测试；P7 负责 partition、bundle loader 和选择归属组件，不重复执行 P4 的测试。入口生成的 `proofs.json` 为 P1–P7 各保留 proof 名、组件测试编号、测试数和该组件日志；`unittest.txt` 保留完整入口日志。这样 P4、P7 都有可追溯机器证据，同时不重复运行相同测试。

`PC68-D1` 不证明 native delegation、root 对 child result 的实际消费、aggregate 顺序——只归 `PC68-R1`。

## 3. `PC68-D1` Recipe（完整）

```bash
env UV_CACHE_DIR=/private/tmp/uv-cache-pr72 uv run python .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing.py \
  --case PC68-D1 \
  --producer-root <clean producer checkout> --producer-sha <被测产品 SHA> \
  --output-dir <空目录>
```

从 producer 仓库根目录运行。入口只发现 `test_issue68_stage5_local_state.TestIssue68Stage5LocalState` 的 7 个 `test_stage5_*` 方法（集合精确校验，否则 `INVALID_TEST_EXECUTION/unexpected_test_set`）；组件映射见 §2；skip/非普通结局即失败。解释器由 `uv run` 选择，项目要求 Python ≥3.11。产物 `proofs.json`、`unittest.txt`；全部七项组件在本次完整入口中普通通过才可判 PC68-D1 PASS，否则 FAIL。

## 4. `PC68-R1` Recipe（完整）

### 4.1 fixture（base runner 自动调用）

A（`試験 教授`）/B（`佐藤 花子`）local pack、synthetic template、噪声 legacy row、坏包；对 `canonical-choices.json` 用安装 producer CLI 真实运行一次 `stage5-partition-choices`（证据留存；owner `partition.status=ok` 且 rows 与构造行一致）；per-owner rows 落盘 `owner-{i}-bundle-choices.json`；initial-plan → `needs_recheck:missing`；plan-with-result（带 `--choices` bundle）→ `needs_refresh`（exit 2）。manifest：`owners[i].expected_choices_rows / expected_bundle_file / sibling_exclusions`、顶层 `partition.owners`、无 `expected_scope`、`pre_run_hashes`、`manual_patch:"no"`。prompt：root 一次 partition → one-professor bundle → owner。

### 4.2 正式入口

```bash
env UV_CACHE_DIR=/private/tmp/uv-cache-pr72 uv run python .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r19_codex.py \
  --producer-root <clean producer checkout> --producer-sha <被测产品 SHA> \
  --fixture-root <skills-test-fixtures@c738fa2 clean checkout> \
  --fixture-sha c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root <eval-server@3fdfa938 检出目录> \
  --output-dir <空目录>
```

单次正式请求，不重试。`EVAL_PORT` 只经 `direnv exec <eval-root> printenv EVAL_PORT` 取得（Executable Preflight 已核实 17902；direnv 位于 `/Users/rekidunois/.local/bin/direnv`）；缺失/非法 → `eval_port_unavailable` 拒绝启动。服务 provenance 前后归档，不一致 → `INVALID_TEST_EXECUTION/eval_service_changed_during_execution`。

### 4.3 判定条件（verifier，contract `issue-68-runtime-evidence-r26-2026-10-05`）

前提门：adapter 状态门；formal children 恰 2（`spawnAgent` + `sender_thread_id`）；`runtime_seq` 严格递增；`terminal_precedence`（FAIL → INVALID → BLOCKED；缺 started 的 commandExecution 记入 observability gaps 延迟归桶，FAIL/INVALID 优先）；`termination_reason=completed`；root final answer = 唯一当前 root/turn `final_answer`（r13 selector；单层包装可解析，嵌套诊断不递归）；identity 字段仅 diagnostics。

per-child 实际业务消费判定（消费面 = child 命令文本同时引用 `contact_state.py` 与 `stage5-plan` 或 `stage5-partition-choices`；JSON/Python literal 内嵌；r22 §5 正式证据面）：`owner_business_object_ambiguous`（INVALID）→ `owner_business_object_unobservable`（BLOCKED）→ `unexpected_owner_pack` / `owner_input_carries_choices_scope` / `choices_transport_missing` / `owner_bundle_choices_changed` / `owner_input_contains_sibling_data` / `owner_target_mismatch`（均 FAIL_PRODUCT）。

**root 结果消费（冻结字段链）**：`subAgentActivity` 的 `agentThreadId -> agentPath` 仅关联键且每 child 唯一（0 → BLOCKED；>1 → INVALID `child_agent_path_mapping_ambiguous`）；唯一合法回执 = root 线程当前 turn 的 `agent_message`（`author==child_agent_path`、`recipient=="/root"`、正文严格 `Message Type: FINAL_ANSWER / Task name: /root / Sender: <path> / Payload:\n<JSON>`）；Payload 只读顶层三字段；`professor_dir` 匹配但缺字段 → `BLOCKED_OBSERVABILITY/root_result_receipt_malformed`；outcome 歧义 → INVALID `root_result_receipt_ambiguous`；outcome ≠ child 自身返回 → FAIL `root_receipt_payload_changed`；消费点 = 最早合法回执 seq。

root 编排：discovery 恰为 `{A ok, B ok, invalid_pack error}`；root 恰一次成功 `stage5-partition-choices` 且输出与 manifest 一致（`root_partition_not_deterministic` / `multiple_root_partitions` / `root_partition_changed` / `partition_executed_by_owner`）；成功 partition 完成前任何 owner 业务调用开始 → `owner_business_precedes_partition`；plan 禁 `--choices-scope`、`--email-pack` 绑定归属、`--choices` 文件 rows == expected；owner 结果须与消费回执一致，每个 owner 目录恰一条且不改写。

**最终总览证据链**：消费完全部教授结果后，root 必须恰好调用一次 `stage5-rebuild-overview`；调用开始时间必须晚于所有结果消费点。该调用的 `aggregatedOutput` 是总览结果的唯一来源，必须能从中识别出恰好一个受支持的结构化结果。最终 root 消息须把这个总览结果作为单独结果原样报告，且与 `aggregatedOutput` 中识别出的对象一致；同时保留每位教授已消费且未改变的结果。缺少重建、重复重建或在结果消费前重建为产品失败；调用输出缺失属于可观察性阻断，格式损坏、冲突或无法唯一归属属于无效证据；最终消息漏报或改写总览结果为产品失败。

总览和教授结果按结果对象本身的字段与形状识别，不依赖 `results`、`overview` 或其他特定包装键。最终当前消息只解析支持范围内的直接结果值与单层整体包装；不递归搜索历史消息、嵌套诊断或其它旧输出来补缺。成功返回形状为 `status:"ok"` 并含 `overview_md`、`professors`、`emails`；成功结果没有 `reason_code` 也有效。失败的 `needs_decision` 或 `error` 结果按调用返回的结构识别并原样单独报告；只要教授结果保持与消费回执一致，这类总览结果仍可通过，不因总览自身失败而改写教授结果。

复合命令不提供 flags，flag 级检查仅覆盖严格解析调用；root 复合 ≥2 动作词 → `BLOCKED_OBSERVABILITY/root_orchestration_ambiguous`。

### 4.4 终态（r22 §5）

`PASS`：r22 全部 required facts 有直接可归属证据；`FAIL_PRODUCT`：有效机器证据直接证明违反 r22 requirement（含消费对象含 sibling 业务数据/`choices_scope`）；`BLOCKED_OBSERVABILITY`：r22 所需事实缺少受支持观察面；`INVALID_EVIDENCE`：证据损坏/冲突/无法唯一归属；`CASE_NOT_STARTED` / `NOT TESTED`。provider/model/access/harness 问题不判产品 FAIL。

## 5. Preflight（r22 §6 四项）

```text
Recipe Preflight（2026-10-05，r27）
- executable: satisfied — direnv（/Users/rekidunois/.local/bin/direnv）经正式来源解析
  EVAL_PORT 17902（证据 /tmp/pc68-r19-work/executable-preflight/direnv_eval_port.txt）；
  入口经该来源可达 case 边界（load_contract 通过，唯一监听者 = 冻结检出同一实例 PID 40721）。
- isolated: supported — /tmp/pc68-r19-work/isolation-now.json（ISOLATION_CONFIRMED）不变；
  入口保留输出目录非空拒绝、overlaps 检查、前后隔离归档。
- observable: supported（r22 口径）— r22 §4 各事实的受支持证据面齐备：formal topology
  （adapter thread_relations）、实际业务消费（child stage5 commandExecution 明文对象，
  r15 表征 + r24/r25 合成回归）、root 合法回执（root agent_message FINAL_ANSWER，r15 seq
  14579/14679 表征）、partition/aggregate 顺序（runtime_seq + aggregatedOutput）、root final
  （r13 selector）。
- discriminating: supported — 新代码提交 4c69b5d555f368c320463917d35424e1c5bda33d 的
  非正式解析器回归命令：
  env UV_CACHE_DIR=/private/tmp/uv-cache-pr72 uv run python .apm/skills/professor-contact/tests/test_issue68_runtime_r19.py
  结果 49 passed、0 failed；日志 /private/tmp/pr72-runtime-preflight-final-20261005.log。
  该项只验证解析器回归，不是 PC68-D1 或 PC68-R1 正式执行证据。覆盖合法总览结果、
  缺少 reason_code 的成功形状、并列报告的教授与总览结果、任意分组键、失败总览结果
  原样报告，以及缺失、损坏、冲突、未报告和过早/重复调用等反例。
- critical assumption gap: none identified。
```

## 6. 测试资产清单

```text
tests/runtime/issue68-runtime-evidence-contract-r19.json  revision=issue-68-runtime-evidence-r26-2026-10-05
tests/runtime/run_issue68_stage5_routing.py               base runner（PC68-D1 完整入口）
tests/runtime/run_issue68_stage5_routing_r19.py           bridge（r12 builder + r27 verifier pin）
tests/runtime/run_issue68_stage5_routing_r19_codex.py     r27 Codex-only 正式入口
tests/runtime/verify_issue68_stage5_routing_r19.py        r27 verifier
tests/runtime/prepare_issue68_stage5_routing.py           fixture builder
tests/runtime/prompts/issue68-stage5-root.txt             root prompt
tests/test_issue68_runtime_r19.py                         49 项非正式解析器回归 + 三通道声明
tests/test_issue68_stage5_local_state.py / test_issue68_root_partition.py / test_issue68_choices_attribution.py  PC68-D1 资产
历史资产不在当前链路；正式执行结果及原始尝试保留。
```

## 7. 本次检查与历史证据

历史全量单元回归 983 项通过；此前的辅助代码清理后，运行时判定回归 42 项、代理说明回归 15 项再次通过。第68号议题相关回归 154 项通过。离线合成证据确认直接与组合总览命令均不改变合法教授业务的通过结果。

绑定代码提交 `4c69b5d555f368c320463917d35424e1c5bda33d` 的非正式解析器预检已执行：`env UV_CACHE_DIR=/private/tmp/uv-cache-pr72 uv run python .apm/skills/professor-contact/tests/test_issue68_runtime_r19.py`，49 项通过、0 项失败；完整日志为 `/private/tmp/pr72-runtime-preflight-final-20261005.log`。该回归属于测试程序预检，不是正式验收。

以上检查不能代替正式验收。历史正式尝试及其原始判定不改写；当前绑定版本的 PC68-D1 完整入口和 PC68-R1 正式用例尚未运行，不标为 PASS。

## 8. 复验依赖

```text
PC68-D1    = EXECUTE_CURRENT（完整固定入口，七个 proof 一次执行）
P2/P3/P4/P6/P7 = EXECUTE_CURRENT
PC68-R1    = EXECUTE_CURRENT
P1/P5 此前 PASS 仅可作为未改变事实的支持证据，不可替代当前完整 PC68-D1；
       未在当前版本实际执行的用例不得标 PASS
R68-6 随 P1；R68-7 随 P2/P4
fixture、正式入口、实际消费 evidence surface、result-consumption evidence、parser/evaluator 或
Consensus runtime 配置变化时只重开受影响 proof
```

## 9. 当前状态

```text
验收来源：    第68号议题当前验收约定及本轮用户决定
测试计划第23版: COMPLETE（current）
Gate 2:       待独立审核；尚无 PASS+COMPLETE 结论
Gate 3:       NOT_READY（尚未运行 PC68-D1 完整入口及 PC68-R1）
Merge:        NOT_READY
```
