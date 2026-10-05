# Issue #68 / PR #72 本地测试工程师实现记录 r22 — 冻结的 root 结果消费字段链

记录版本：`issue68-r22-frozen-receipt-chain-2026-10-05`。

本文件是**测试实现记录与 Gate 2 候选材料，不是第二关口权威结论**。它按第二关口审核澄清（PR 评论 `5991384143`）把 `PC68-R1 / AD68-1` 的 root 结果消费取证方式固定为审核者冻结的字段链，并修正 r21 的具体缺口（回执未验证 `author == child_agent_path`）。本记录完整取代 `docs/issue68-test-gate-r21.md` 的候选地位（r19/r20/r21 保留审计）；执行者无需拼接历史评论。

## 1. 输入与版本

```text
Frozen Acceptance Contract:  issue-68-gate1-r3-2026-10-04 (PASS + COMPLETE)
Canonical Plan:              issue-68-plan-r12-2026-10-04 (APPROVED)
Test plan:                   issue-68-test-plan-r20-2026-10-05（其 G2-1 证据来源经评论 5990445769、5991384143 两次更正后冻结）
Gate 2 clarifications:       PR 评论 5990445769（撤销 agentsStates）、5991384143（冻结字段链）
Runtime evidence contract:   issue-68-runtime-evidence-r22-2026-10-05（文件名仍为 issue68-runtime-evidence-contract-r19.json，以 revision 字段为准）
Target PR HEAD:              a22901229259c4bf7e36fe45f8207ab0b1ef7d72（产品实现未变）
r15 正式归档:                /tmp/pr72-r1-formal-f230616984/（未改动；本记录全部真实数据证据来自它）
```

## 2. 冻结的取证字段链（审核澄清 §1–§4 原文语义）

```text
formal child 归属（不变）
  adapter.dispatch.thread_relations: tool=="spawnAgent" 且 sender_thread_id==output.thread_id
  -> receiver_thread_ids 即 formal children

child_thread_id -> child_agent_path（关联键，不承担 formal ownership）
  任意线程 subAgentActivity 项: item.agentThreadId == child_thread_id -> item.agentPath

root 实际收到 child 最终结果的唯一合法回执，须同时满足：
  runtime_generation == output.runtime_generation
  message.method == "rawResponseItem/completed"
  message.params.threadId == output.thread_id
  message.params.turnId == output.turn_id
  message.params.item.type == "agent_message"
  message.params.item.author == child_agent_path        ← r21 缺口，本轮补上
  message.params.item.recipient == "/root"
  正文（content[*].type=="input_text"）严格为：
    Message Type: FINAL_ANSWER
    Task name: /root
    Sender: <child_agent_path>
    Payload:
    <JSON>        ← 只解析该 JSON；所需字段 professor_dir / status / reason_code

消费时点 = 该回执 runtime_seq
aggregate 顺序 = stage5-rebuild-overview.start_seq > max(all receipt.runtime_seq)，否则
  FAIL_PRODUCT / aggregate_precedes_result_consumption
```

仅诊断、不得补足消费的字段：`collabAgentToolCall`、`receiverThreadIds`、`agentsStates`、`Wait completed.`、`subAgentActivity completed`、child `turn/completed`、`requested_role`、`loaded_identity`。verifier 已删除 child `turn/completed` 的收集与一切判定引用（r21 的 `root_receipt_precedes_child_completion` 检查随之删除）。

## 3. 每 owner 回执判定

| 条件 | 终态 / reason |
| --- | --- |
| 该 child 无 agentPath 映射，或无满足冻结链全部条件的合法回执 | `BLOCKED_OBSERVABILITY / root_result_consumption_unobservable` |
| 合法回执解析出 >1 个不同 outcome triple（professor_dir/status/reason_code） | `INVALID_EVIDENCE / root_result_receipt_ambiguous` |
| 回执 outcome ≠ child 自己最终业务消息的 outcome | `FAIL_PRODUCT / root_receipt_payload_changed` |
| 全过 | 消费点 = 最早合法回执 seq |

找不到唯一可归属回执时不猜测 PASS。其余 oracle（partition、`owner_business_precedes_partition`、owner payload、sibling、canonical、final source、terminal_precedence、`root_changed_owner_result`）不变。

## 4. Preflight 四项（r22 复核）

```text
Recipe Preflight（2026-10-05，r22）
- executable: NOT satisfied（当前环境）— direnv 缺失，与 r20/r21 记录一致；Recipe 无需再改。
- isolated: supported — 活体快照 /tmp/pc68-r19-work/isolation-now.json（ISOLATION_CONFIRMED）不变。
- observable: supported — 冻结字段链在既有 r15 正式 raw 上逐项核验通过（jq 只读核验）：
  output.turn_id = 01a106cc-3f98-…；两条 root 回执（seq 14579 author /root/stage5_x、
  seq 14679 author /root/stage5_y）的 params.turnId 与之相等、recipient=/root、正文为严格
  四段 FINAL_ANSWER 形状、Payload 单行 JSON 的 outcome 与 child 自身返回一致；
  subAgentActivity 的 agentThreadId 与 adapter formal children 完全一致。
- discriminating: supported — r22 回归 37 项：默认合法流程（真实形状回执）→ PASS；
  审核者判别用例 1（A 回执缺失、B author 的合规形状消息正文含 A 结果 → 不得记为 A 的消费，
  BLOCKED）；判别用例 2（非 FINAL_ANSWER 的诊断消息含同一 JSON → 不影响判定，PASS）；
  回执载荷被改 → FAIL；回执歧义 → INVALID；rebuild 在消费点前 → FAIL；
  真实数据负例：r15 raw 经 r22 verifier 重判仍 FAIL_PRODUCT/owner_input_carries_choices_scope。
- critical assumption gap: 当前环境 direnv 缺失（executable 未满足）为唯一未闭合项。
```

## 5. 资产与证据位置

```text
tests/runtime/verify_issue68_stage5_routing_r19.py       r22 冻结链 verifier（文件名沿用，行为以 contract revision 为准）
tests/runtime/issue68-runtime-evidence-contract-r19.json revision = issue-68-runtime-evidence-r22-2026-10-05
tests/runtime/run_issue68_stage5_routing_r19_codex.py    CONTRACT_REVISION = r22 串；direnv 唯一端口来源不变
tests/test_issue68_runtime_r19.py                        37 项（冻结链正反例 + 两个审核者判别用例 + 三通道声明）
/tmp/pc68-r19-work/r22-rejudge-real-raw.json             r15 raw 重判输出（FAIL_PRODUCT/owner_input_carries_choices_scope）
/tmp/pc68-r19-work/1005_wait_consume_characterization.py r15 raw 事件形状分析脚本（只读）
```

## 6. 回归与复验

```text
test_issue68_runtime_r19        37 tests OK
r18/recipe/r13/r14/r12_codex    61 tests OK
复验依赖                        与 r20 §7 一致：P4/P6/P7、PC68-R1 = EXECUTE_CURRENT；P2/P3、P1/P5 按影响分析可复用
```

## 7. 当前状态

```text
Gate 2: 消费取证已按冻结字段链修正并通过真实 raw 核验，候选材料更新至 r22；等待测试审核者完整复审
Gate 3: NOT_READY（PC68-R1 继续暂停）
Merge:  NOT_READY
```
