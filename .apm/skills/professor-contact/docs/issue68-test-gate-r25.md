# Issue #68 / PR #72 Gate 2 候选记录 r25 — Test Plan r22 单一权威测试实现

记录版本：`issue68-r25-r22-authoritative-candidate-2026-10-05`。

本文件是**测试实现记录与 Gate 2 候选材料，不是第二关口权威结论**。它按 Test Plan r22（`issue-68-test-plan-r22-2026-10-05`，PR 评论 `5993806361`，取代 r21 的测试设计）修订：撤销 r21 的 owner-entry transport Observable 要求与 r24 的 PASS 封顶，恢复"formal child 自身 Stage 5 `commandExecution`"为实际业务消费的正式证据面。本记录是单一自包含候选，完整取代 r19–r24 候选地位（旧记录保留审计并已标注被取代）。

**Gate 1 边界（Test Plan r22 §1）**：本轮验收决定与 Gate 1 r3 的 `R68-8 / AD68-4 / AD68-5` 部分文字冲突，Gate 1 需按 `contract change` 更新；**在 Gate 1 新 revision 冻结同一语义前，不据此宣告 Gate 2 PASS**。Gate 1 重冻由验收决定人负责；本候选只声明实现已与 r22 对齐。

## 0. 版本绑定（全部固定到真实提交）

| 角色 | 版本 | 说明 / 影响分析 |
| --- | --- | --- |
| 被测产品 | `ScholarWorkflow/professor-contact@a22901229259c4bf7e36fe45f8207ab0b1ef7d72` | 产品 Stage-5 实现完成于 `a229012`；`git diff a229012..HEAD -- scripts agents SKILL.md workflow-reference.md` 为空——其后全部提交只改 `tests/` 与 `docs/`，被测行为、入口、输入输出 contract 无变化 |
| 测试实现 / 判定程序（代码） | `ScholarWorkflow/professor-contact@2478d244fb0f6a55348a485715dc0f5712856a4a` | 包含 r22 修订（移除 entry 封顶）及此前全部 oracle 修正 |
| 其后纯文档提交 | `44918c3`（r22 记录）、`e090217`（r23 记录）、`a5143df`（r23 Preflight 补齐）、`5dcbbd7`（r24 记录）、r25 记录所在提交 | 仅 `docs/` 变更，不影响任何 oracle、命令或判定；逐次影响分析：无 |
| 共享 fixture adapter | `skills-test-fixtures@c738fa2f8bcbb16cd99d741332d5f59b062b6357`（adapter@16） | 未变 |
| eval-server | `3fdfa9387140cfc2e2aa3af415f85015f79706d2`（检出干净） | 未变 |
| 模型/请求 | Project Consensus 默认 `gpt-6-luna`，`build_issue68_codex_request_r12.py` | 未变 |

## 1. 权威输入

```text
Frozen Acceptance Contract:  issue-68-gate1-r3-2026-10-04（PASS + COMPLETE；R68-8/AD68-4/AD68-5 文字待按
                             contract change 出新 revision）
Canonical Plan:              issue-68-plan-r12-2026-10-04（APPROVED）
Test Plan:                   issue-68-test-plan-r22-2026-10-05（评论 5993806361，取代 r21 测试设计）
Runtime evidence contract:   issue-68-runtime-evidence-r25-2026-10-05（文件名 issue68-runtime-evidence-contract-r19.json，
                             以 revision 字段为准）
```

## 2. Requirement → proof owner → case（Test Plan r22 §2 完整 mapping）

两个正式 case：`PC68-D1`、`PC68-R1`；不新增 case。R68-1…R68-7、AD68-1…AD68-3 的负责者与事实沿用 r20/r21 分工（落点见 r23/r24 记录 §2，本表只列 r22 修订行与未变行）：

| 正式要求 | 证明负责者 | r22 必须证明的事实 | 实现落点 |
| --- | --- | --- | --- |
| `R68-1` | `PC68-D1/P1` | local `email_pack` 唯一 authority；无 global fallback / dual authority | t68_1 / t68_1b / t68_1c / t68_2 |
| `R68-2` | `PC68-D1/P2` | targeted 只处理目标；无关行不阻断；目标自身 fail closed | t68_3 / t68_4 / unselected_malformed_noise + r11 targeted 过滤 |
| `R68-3` | `PC68-D1/P3` | 无 `--email-id` 只覆盖当前 pack；same-professor batch 整笔语义 | t68_5 + `TestStage5BatchStaysAtomic` |
| `R68-4` | `PC68-D1/P4` | A/B 独立 transaction；B 失败不回滚/阻断合法 A | t68_6 / validation_updates_only + cx2 + sibling loader fail-closed |
| `R68-5` | `PC68-D1/P5` | overview 是派生输出，不进 local finalize commit gate | t68_7 + `TestStage5OverviewRebuild` |
| `R68-6` | `PC68-D1/P1` | #68 不新增 migration/global fallback/dual-read/dual-write | P1 组件；随 P1 复验 |
| `R68-7` | `PC68-D1/P2 + P4` | validator / record-validation 只以当前 professor 本次输出为条件 | P2 组件 + validation_updates_only |
| `R68-8`（待 Gate 1 新 revision 同步） | `PC68-D1/P4 + P7`、`PC68-R1` | 当前 owner **实际用于 Stage 5 业务处理**的数据只属于当前 professor；sibling 数据不得进入 plan/finalize/validation/state/render/output，也不得影响当前 owner 结果；非业务上下文中未被消费的 sibling 信息本身不是失败 | P4/P7 deterministic 面 + runtime 消费面 sibling oracle |
| `AD68-1` | `PC68-R1`（`P5` 辅助） | root 委派 owner，实际取得/消费各 owner result 后最多一次 rebuild overview | runtime 回执消费链 + 聚合顺序 oracle |
| `AD68-2` | `implementation_scope: #48` | writer-lock ownership 归 #48；#68 不改 writer ownership / canonical rebuild interface | 无测试组件；触碰接口时才重开 |
| `AD68-3` | `PC68-D1/P6` | standalone discovery 只读；坏 B 不影响合法 A/C | `TestStage5ListInputs` 全类 + scope-emission 负向 oracle + cx7 |
| `AD68-4`（待 Gate 1 新 revision 同步） | `PC68-D1/P7`、`PC68-R1` | raw multi-professor choices 由 root deterministic partition；每 owner 实际业务调用只消费分配给自己的 rows；legacy ambiguity 不影响无关 owner；非业务上下文额外 sibling 信息不单独判 FAIL | P7 partition 全类 + runtime partition oracle + 消费面 sibling oracle |
| `AD68-5`（待 Gate 1 新 revision 同步） | `PC68-D1/P7`、`PC68-R1` | 当前 owner 实际消费的 canonical `professor_dir`/`email_pack`/`email_id`/choice rows 保持原值；不得转写、重建或错归属；不要求证明完整 child task payload 是 single-professor | P7 行保持/隔离 oracle + runtime `canonical_preservation` |

`PC68-D1` 不证明 native delegation、root 对 child result 的实际消费、aggregate 顺序——只归 `PC68-R1`；`PC68-D1` 也**不需要**证明 child invocation 的完整 prompt/task payload 不含 sibling 信息（r22 §3）。

## 3. `PC68-D1` Recipe（完整）

```bash
python3 tests/runtime/run_issue68_stage5_routing.py \
  --case PC68-D1 \
  --producer-root <clean producer checkout> --producer-sha <被测产品 SHA> \
  --output-dir <空目录>
```

入口只发现 `test_issue68_stage5_local_state.TestIssue68Stage5LocalState` 的 7 个 `test_stage5_*` 方法（集合精确校验，否则 `INVALID_TEST_EXECUTION/unexpected_test_set`）；组件映射见 §2 落点列；skip/非普通结局即失败。解释器 ≥3.11（`$HOME/.local/share/uv/python/cpython-3.14-macos-aarch64-none/bin/python3`）。产物 `proofs.json`、`unittest.txt`；判定：全部组件普通通过 → PASS，否则 FAIL。

## 4. `PC68-R1` Recipe（完整）

### 4.1 fixture（base runner 自动调用）

A（`試験 教授`）/B（`佐藤 花子`）local pack、synthetic template、噪声 legacy row、坏包；对 `canonical-choices.json` 用安装 producer CLI 真实运行一次 `stage5-partition-choices`（证据留存；owner `partition.status=ok` 且 rows 与构造行一致）；per-owner rows 落盘 `owner-{i}-bundle-choices.json`；initial-plan → `needs_recheck:missing`；plan-with-result（带 `--choices` bundle）→ `needs_refresh`（exit 2）。manifest：`owners[i].expected_choices_rows / expected_bundle_file / sibling_exclusions`、顶层 `partition.owners`、无 `expected_scope`、`pre_run_hashes`、`manual_patch:"no"`。prompt：root 一次 partition → one-professor bundle → owner。

### 4.2 正式入口

```bash
python3 tests/runtime/run_issue68_stage5_routing_r19_codex.py \
  --producer-root <clean producer checkout> --producer-sha <被测产品 SHA> \
  --fixture-root <skills-test-fixtures@c738fa2 clean checkout> \
  --fixture-sha c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root <eval-server@3fdfa938 检出目录> \
  --output-dir <空目录>
```

单次正式请求，不重试。`EVAL_PORT` 只经 `direnv exec <eval-root> printenv EVAL_PORT` 取得（Executable Preflight 已核实 17902；direnv 位于 `/Users/rekidunois/.local/bin/direnv`）；缺失/非法 → `eval_port_unavailable` 拒绝启动。服务 provenance 前后归档，不一致 → `INVALID_TEST_EXECUTION/eval_service_changed_during_execution`。

### 4.3 判定条件（verifier，contract `issue-68-runtime-evidence-r25-2026-10-05`）

前提门：adapter 状态门；formal children 恰 2（`spawnAgent` + `sender_thread_id`）；`runtime_seq` 严格递增；`terminal_precedence`（FAIL → INVALID → BLOCKED；缺 started 的 commandExecution 记入 observability gaps 延迟归桶，FAIL/INVALID 优先）；`termination_reason=completed`；root final answer = 唯一当前 root/turn `final_answer`（r13 selector；单层包装可解析，嵌套诊断不递归）；identity 字段仅 diagnostics。

per-child 实际业务消费判定（消费面 = child 命令文本同时引用 `contact_state.py` 与 stage5 动作词；JSON/Python literal 内嵌；r22 §5 正式证据面）：`owner_business_object_ambiguous`（INVALID）→ `owner_business_object_unobservable`（BLOCKED）→ `completed_user_payload_unobservable`（BLOCKED）→ `unexpected_owner_pack` / `owner_input_carries_choices_scope` / `choices_transport_missing` / `owner_bundle_choices_changed` / `owner_input_contains_sibling_data` / `owner_target_mismatch`（均 FAIL_PRODUCT）。

**root 结果消费（冻结字段链）**：`subAgentActivity` 的 `agentThreadId -> agentPath` 仅关联键且每 child 唯一（0 → BLOCKED；>1 → INVALID `child_agent_path_mapping_ambiguous`）；唯一合法回执 = root 线程当前 turn 的 `agent_message`（`author==child_agent_path`、`recipient=="/root"`、正文严格 `Message Type: FINAL_ANSWER / Task name: /root / Sender: <path> / Payload:\n<JSON>`）；**Payload 只读顶层三字段**；`professor_dir` 匹配但缺字段 → `BLOCKED_OBSERVABILITY/root_result_receipt_malformed`；outcome 歧义 → INVALID `root_result_receipt_ambiguous`；outcome ≠ child 自身返回 → FAIL `root_receipt_payload_changed`；消费点 = 最早合法回执 seq。

**r22 变更**：entry NEW_TASK 加密交付（`encrypted_content`）仅为诊断——既非 PASS 条件、也非 BLOCKED 来源；无 `owner_entry_transport_unobservable` 封顶；合法流程直接 PASS。

root 编排：discovery 恰为 `{A ok, B ok, invalid_pack error}`；root 恰一次成功 `stage5-partition-choices` 且输出与 manifest 一致（`root_partition_not_deterministic` / `multiple_root_partitions` / `root_partition_changed` / `partition_executed_by_owner`）；成功 partition 完成前任何 owner 业务调用开始 → `owner_business_precedes_partition`；plan 禁 `--choices-scope`、`--email-pack` 绑定归属、`--choices` 文件 rows == expected；`stage5-rebuild-overview` ≤1 且 start > max(消费点)；root 终局行每 owner 恰一个一致 outcome 且等于消费 outcome。复合命令不提供 flags，flag 级检查仅覆盖严格解析调用；root 复合 ≥2 动作词 → `BLOCKED_OBSERVABILITY/root_orchestration_ambiguous`。

### 4.4 终态（r22 §5）

`PASS`：r22 全部 required facts 有直接可归属证据；`FAIL_PRODUCT`：有效机器证据直接证明违反 r22 requirement（含消费对象含 sibling 业务数据/`choices_scope`）；`BLOCKED_OBSERVABILITY`：r22 所需事实缺少受支持观察面；`INVALID_EVIDENCE`：证据损坏/冲突/无法唯一归属；`CASE_NOT_STARTED` / `NOT TESTED`。provider/model/access/harness 问题不判产品 FAIL。

## 5. Preflight（r22 §6 四项）

```text
Recipe Preflight（2026-10-05，r25）
- executable: satisfied — direnv（/Users/rekidunois/.local/bin/direnv）经正式来源解析
  EVAL_PORT 17902（证据 /tmp/pc68-r19-work/executable-preflight/direnv_eval_port.txt）；
  入口经该来源可达 case 边界（load_contract 通过，唯一监听者 = 冻结检出同一实例 PID 40721）。
- isolated: supported — /tmp/pc68-r19-work/isolation-now.json（ISOLATION_CONFIRMED）不变；
  入口保留输出目录非空拒绝、overlaps 检查、前后隔离归档。
- observable: supported（r22 口径）— r22 §4 各事实的受支持证据面齐备：formal topology
  （adapter thread_relations）、实际业务消费（child stage5 commandExecution 明文对象，
  r15 表征 + r24/r25 合成回归）、root 合法回执（root agent_message FINAL_ANSWER，r15 seq
  14579/14679 表征）、partition/aggregate 顺序（runtime_seq + aggregatedOutput）、root final
  （r13 selector）。r21 的入口明文 payload 要求已由 r22 撤销，不再是观察项。
- discriminating: supported — r25 回归 42 项三通道：合法流程 → PASS；sibling/choices_scope/
  载荷改写/canonical 转写/跨 child 正文/嵌套 Payload/缺字段回执/冲突 agentPath/
  rebuild-before-consumption → 各对应 FAIL/INVALID/BLOCKED；真实数据负例：r15 raw 重判
  FAIL_PRODUCT/owner_input_carries_choices_scope。
- critical assumption gap: none identified（按 r22 口径；Gate 1 重冻前不宣告 Gate 2 PASS）。
```

## 6. 测试资产清单

```text
tests/runtime/issue68-runtime-evidence-contract-r19.json  revision=issue-68-runtime-evidence-r25-2026-10-05
tests/runtime/run_issue68_stage5_routing.py               base runner（PC68-D1 入口；未改）
tests/runtime/run_issue68_stage5_routing_r19.py           bridge（r12 builder + r25 verifier pin）
tests/runtime/run_issue68_stage5_routing_r19_codex.py     r25 Codex-only 正式入口
tests/runtime/verify_issue68_stage5_routing_r19.py        r25 verifier
tests/runtime/prepare_issue68_stage5_routing.py           fixture builder
tests/runtime/prompts/issue68-stage5-root.txt             root prompt
tests/test_issue68_runtime_r19.py                         42 项反例矩阵 + 三通道声明
tests/test_issue68_stage5_local_state.py / test_issue68_root_partition.py / test_issue68_choices_attribution.py  PC68-D1 资产
历史资产（r11–r24 文件）保留审计，不在当前链路。
```

## 7. 回归与真实数据证据

```text
r25 修订后：test_issue68_runtime_r19 42 tests OK；r18/recipe/r13/r14/r12_codex 61 tests OK；
r15 raw 重判 FAIL_PRODUCT/owner_input_carries_choices_scope（/tmp/pc68-r19-work/r25-rejudge-real-raw.json）。
表征脚本：/tmp/pc68-r19-work/1005_entry_deliveries_characterization.py、1005_wait_consume_characterization.py。
基线口径：全量 973 项中 5 个失败 = 基线 cc44247 既有，REGRESSION_DELTA 零新增。
```

## 8. 复验依赖（r22 §8）

```text
P4, P6, P7 = EXECUTE_CURRENT
PC68-R1    = EXECUTE_CURRENT（r24 entry 封顶已按 r22 移除；可执行）
P2/P3、P1/P5 = 产品 diff 未改变 targeted/batch 与 local authority/overview boundary，可 REUSE_PRIOR_PASS
R68-6 随 P1；R68-7 随 P2/P4
fixture、正式入口、实际消费 evidence surface、result-consumption evidence、parser/evaluator 或
Consensus runtime 配置变化时只重开受影响 proof
```

## 9. 当前状态

```text
Gate 1 r3:    R68-8/AD68-4/AD68-5 文字与 r22 验收决定冲突，待验收决定人按 contract change 出新 revision
Test Plan r22: COMPLETE（current）
Gate 2:       测试实现已与 r22 对齐（本候选）；Gate 2 结论待 Gate 1 重冻后由测试审核者复审
Gate 3:       NOT_READY
Merge:        NOT_READY
```
