# Issue #68 / PR #72 本地测试工程师实现记录 r21 — 真实 wait/consume 回执面

> **已被取代**：本记录的 Gate 2 候选地位由 `docs/issue68-test-gate-r22.md`（`issue68-r22-frozen-receipt-chain-2026-10-05`，按审核澄清 PR 评论 `5991384143` 固定回执取证字段链并补上 `author == child_agent_path` 绑定）接管；本文件仅保留审计用途，不得作为当前权威候选拼接使用。

记录版本：`issue68-r21-receipt-consumption-2026-10-05`。

本文件是**测试实现记录与 Gate 2 候选材料，不是第二关口权威结论**。它响应 Gate 2 审核更正（PR 评论 `5990445769`）：撤销 r20 的 `agentsStates` 配对要求，按最小 Recipe Preflight 在既有 r15 正式 raw 上证实 root 结果消费的真实事件形状，并据此重写 contract/verifier/回归。本记录完整取代 `docs/issue68-test-gate-r20.md` 的候选地位（r19/r20 记录保留审计）；执行者无需拼接历史评论。

## 1. 输入与版本

```text
Frozen Acceptance Contract:  issue-68-gate1-r3-2026-10-04 (PASS + COMPLETE)
Canonical Plan:              issue-68-plan-r12-2026-10-04 (APPROVED)
Test plan:                   issue-68-test-plan-r20-2026-10-05（评论 5989428845；其 G2-1 证据来源被评论 5990445769 更正）
Gate 2 correction:           PR 评论 5990445769（2026-10-05T07:58:58Z）
Runtime evidence contract:   issue-68-runtime-evidence-r21-2026-10-05（文件名仍为 issue68-runtime-evidence-contract-r19.json，以 revision 字段为准）
Target PR HEAD:              f34aeba2110254e4ba56ea469a1ef4644a8a6016（产品实现未变）
共享 fixture adapter:        skills-test-fixtures@c738fa2…（未变）；eval-server 3fdfa938（未变）
r15 正式归档（characterization 输入）: /tmp/pr72-r1-formal-f230616984/codex/codex-response.json（830 events，2 formal children，未改动）
```

## 2. Preflight characterization — root 结果消费的真实事件形状（Observable）

对 r15 归档只读解析（脚本 `/tmp/pc68-r19-work/1005_wait_consume_characterization.py`，输出见 §6）：

**真实消费面 = root 线程 `rawResponseItem/completed`、`item.type == "agent_message"` 的 FINAL_ANSWER 回执。**

```text
X child：seq 14579  author=/root/stage5_x  recipient=/root
  content text = "Message Type: FINAL_ANSWER\nTask name: /root\nSender: /root/stage5_x\nPayload:\n
                  {\"professor_dir\":\"…/X分野/試験 教授\",\"status\":\"needs_input\",\"reason_code\":\"verify_missing\"}"
Y child：seq 14679  author=/root/stage5_y  同形状
```

满足审核者三项要求的核验：

1. **稳定关联 formal child**：回执 `author`（agentPath）与同 run root 线程 `subAgentActivity` 事件的 `agentThreadId ↔ agentPath` 映射对应（`/root/stage5_x` ↔ 01a106cd-2036…）；且 Payload 行的 `professor_dir` 直接对应 manifest owner——双重机器可判定关联。
2. **携带实际 child result**：回执 `Payload:` 后的 JSON 与该 child 自己线程的最终 assistant 业务消息（X seq 14567 / Y seq 14667）逐字一致。
3. **可机械判定的消费时点**：回执事件的 `runtime_seq`（14579/14679），可用于 aggregate 顺序判定（rebuild 必须晚于全部消费点）。

时序核验（同 run）：child `turn/completed`（14573/14673）→ root `subAgentActivity completed`（14574/14674）→ `collabAgentToolCall` wait completed（14575/14675，`receiverThreadIds` 与 `agentsStates` 均为空）→ `function_call_output`（14576/14676，`{"message":"Wait completed.","timed_out":false}`）→ **agent_message 回执（14579/14679）** → root final answer。

**官方源码佐证**：openai/codex `codex-rs/core/src/tools/handlers/multi_agents_v2/wait.rs`（2026-10-05 读取）——wait 项 started/completed 的 `receiver_thread_ids` 均为 `Vec::new()`、`agents_states` 为空 map；`WaitAgentResult.message` 仅为 `"Wait completed."` / `"Wait interrupted by new input."` / `"Wait timed out."` 状态文本。故 wait 事件不作任何消费证据。

## 3. 重写后的 wait/consume oracle（contract revision `issue-68-runtime-evidence-r21-2026-10-05`）

每 formal child 的消费判定（在既有 owner payload/sibling/canonical 判定之后）：

| 条件 | 终态 / reason |
| --- | --- |
| root 线程无任何 Payload 行 professor_dir 匹配该 owner 的 agent_message 回执 | `BLOCKED_OBSERVABILITY / root_result_consumption_unobservable` |
| 匹配回执行解析出 >1 个不同 outcome triple | `INVALID_EVIDENCE / root_result_receipt_ambiguous` |
| 回执 seq 早于该 child `turn/completed`（完成点可观察时） | `INVALID_EVIDENCE / root_receipt_precedes_child_completion` |
| 回执 outcome ≠ child 自己最终业务消息的 outcome（root 收到的与 child 返回的不一致） | `FAIL_PRODUCT / root_receipt_payload_changed` |
| 全过 | 消费点 = 最早匹配回执 seq |

`aggregate_precedes_result_consumption` 语义不变、判定基准改为回执消费点（rebuild start ≤ max(消费点) → FAIL）。**删除**：`completion_or_wait_unobservable`、`missing_wait_pairing`、`missing_turn_completion`、`wait_precedes_owner_completion`、PASS 的 `wait_evidence`；`collabAgentToolCall`/`subAgentActivity`/`turn/completed` 降为 diagnostics，不再构成阻断或放行依据。其余 oracle（partition、`owner_business_precedes_partition`、owner payload、sibling、canonical、final source、terminal_precedence）不变。

## 4. Preflight 四项（r21 复核）

```text
Recipe Preflight（2026-10-05，r21）
- executable: NOT satisfied（当前环境）— 与 r20 记录一致：EVAL_PORT 正式来源 direnv 在当前环境缺失，
  正式 PC68-R1 无法从当前环境启动；Recipe 本身无需再改，direnv 可用即满足。
- isolated: supported — 活体快照 /tmp/pc68-r19-work/isolation-now.json（ISOLATION_CONFIRMED）不变。
- observable: supported — §2 的真实回执面由既有正式 raw 直接证实（非合成构造）：稳定关联、
  携带实际 child result、runtime_seq 消费时点三要素齐备；官方 wait.rs 佐证 wait 面不可用。
- discriminating: supported — r21 回归 36 项覆盖三通道：默认合法流程（含真实形状回执）→ PASS；
  无回执 → BLOCKED；回执歧义/早于完成 → INVALID；回执载荷被改 → FAIL_PRODUCT；rebuild 在
  child 完成后、回执前 → FAIL；另有真实数据负例：r15 归档 raw 经 r21 verifier 重判仍为
  FAIL_PRODUCT/owner_input_carries_choices_scope（terminal_precedence，回执面在该 raw 上真实工作）。
- critical assumption gap: 当前环境 direnv 缺失（executable 未满足）为唯一未闭合项。
```

## 5. 资产与版本

```text
tests/runtime/verify_issue68_stage5_routing_r19.py   r21 回执面 verifier（文件名沿用，行为以 contract revision 为准）
tests/runtime/issue68-runtime-evidence-contract-r19.json  revision = issue-68-runtime-evidence-r21-2026-10-05
tests/runtime/run_issue68_stage5_routing_r19_codex.py     CONTRACT_REVISION = r21 串；direnv 唯一端口来源（r20 G2-2 修正保留）
tests/test_issue68_runtime_r19.py                    36 项（真实回执形状反例矩阵 + 三通道声明）
docs/issue68-test-gate-r20.md                        已标注被本记录取代
```

## 6. 本地证据位置

```text
/tmp/pc68-r19-work/1005_wait_consume_characterization.py   r15 raw 事件形状分析脚本（只读）
/tmp/pc68-r19-work/r21-rejudge-real-raw.json               r21 verifier 对 r15 raw 的重判（FAIL_PRODUCT/owner_input_carries_choices_scope）
/tmp/pc68-r19-work/isolation-now.json                      活体隔离快照（ISOLATION_CONFIRMED）
/tmp/pr72-r1-formal-f230616984/                            r15 正式归档（未改动）
```

## 7. 回归与复验

```text
test_issue68_runtime_r19        36 tests OK
r18/recipe/r13/r14/r12_codex    61 tests OK
r15 raw 重判                    FAIL_PRODUCT/owner_input_carries_choices_scope（与 r20 基线逐字一致）
复验依赖                        与 r20 §7 一致：P4/P6/P7、PC68-R1 = EXECUTE_CURRENT；P2/P3、P1/P5 按影响分析可复用
```

## 8. 当前状态

```text
Gate 2: G2-1 证据来源已按审核更正重写为真实回执面，候选材料更新至 r21；等待测试审核者完整复审
Gate 3: NOT_READY（PC68-R1 继续暂停，等 Gate 2 PASS + COMPLETE）
Merge:  NOT_READY
```
