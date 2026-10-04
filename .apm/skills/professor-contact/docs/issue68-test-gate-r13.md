# Issue #68 测试工程师第十三版记录

记录版本：`issue-68-gate2-r13-2026-10-04`。

本记录只重审 `PC68-R1` 的 Codex 证据来源和相关 Recipe。Gate 1 冻结要求不变，`PC68-D1/P1–P7` 的历史 PASS 不因本次证据来源修正自动失效。第十二版中 `root_thread_read`、`skills-test-fixtures#28` 和 `eval-server#21` 作为当前 `PC68-R1` 前提的部分由本记录取代；第十二版历史执行事实继续保留。自本记录生效起，`run_issue68_stage5_routing_r12_codex.py`（含第十二版记录中的全部执行指令）以及 `run_issue68_stage5_routing_r12.py`、`run_issue68_stage5_routing.py` 的直接调用停止作为 `PC68-R1` 执行指令，仅作历史与管线实现保留；当前唯一正式入口是第 4 节所列 `run_issue68_stage5_routing_r13_codex.py`。

## 1. 当前输入

```text
PR #72 HEAD                 = 96609850a00a73faff9a31d69731bf368c718490（本记录创建前）
Project Consensus           = 2026-10-04 当前版本
Test Engineer Rule          = 2026-10-02 当前版本
skills-test-fixtures master = c738fa2f8bcbb16cd99d741332d5f59b062b6357
fixture adapter             = skills-test-fixtures/codex-eval-adapter@16
fixture source              = skills-test-fixtures#33
eval-server current master  = 3fdfa9387140cfc2e2aa3af415f85015f79706d2
Codex observed runtime      = codex-cli 0.159.0-alpha.12.1
formal host scope           = Codex only
```

`skills-test-fixtures#33` 已合并并完成自己的 Gate 2 / Gate 3，`@16` 同时支持 V1 和当前 V2 formal relation。第 28 号拉取请求的 root-history wrapper 不再属于本用例依赖。

## 2. 发现的测试缺陷

第十二版把 Codex 根线程最终业务结果固定为 `output.root_thread_read` 最后一个 turn 的唯一 `AgentMessage phase=final_answer`。当前 eval 服务本来就把 `rawResponseItem/completed` 保存在 `output.app_server_events`，事件带 `threadId`、`turnId` 和完整 `ResponseItem`；`ResponseItem::Message.phase` 可表示 `final_answer`。因此额外要求 `root_thread_read` 会把已有可归属结构化证据错误判成不可观察，并额外制造 `skills-test-fixtures#28` 与 `eval-server#21` 依赖。

本次修正只改变测试证据来源，不改变产品要求、产品实现或 `PC68-R1` 要证明的业务事实。

## 3. r13 唯一 Codex 最终来源

从一次 `/eval` 响应的 `output.app_server_events[]` 中选择同时满足以下条件的事件：

1. `runtime_generation == output.runtime_generation`；
2. `message.method == "rawResponseItem/completed"`；
3. `message.params.threadId == output.thread_id`；
4. `message.params.turnId == output.turn_id`；
5. `message.params.item.type == "message"`；
6. `message.params.item.role == "assistant"`；
7. `message.params.item.phase == "final_answer"`。

必须恰好一个候选。正文按 Codex 当前源码规则，将该 message 的 `content[]` 中 `type=output_text` 的 `text` 按顺序直接拼接。

判定：

```text
恰好一个合法候选        -> 交给既有 PC68-R1 业务 oracle
0 个候选                -> BLOCKED_OBSERVABILITY / root_final_message_unobservable
多个候选                -> INVALID_EVIDENCE / root_final_message_ambiguous
候选或归属字段损坏      -> INVALID_EVIDENCE
```

不同 `runtime_generation`、child thread、旧 `turnId`、`commentary`、缺失/未知 `phase` 都不能成为最终业务结果来源。

## 4. 版本化资产

```text
tests/runtime/verify_issue68_stage5_routing_r13.py
tests/runtime/run_issue68_stage5_routing_r13.py
tests/runtime/run_issue68_stage5_routing_r13_codex.py
tests/runtime/check_issue68_codex_final_source_r13.py
tests/runtime/issue68-runtime-evidence-contract-r13.json
tests/test_issue68_runtime_r13.py
```

r13 bridge 固定：

```text
fixture SHA      = c738fa2f8bcbb16cd99d741332d5f59b062b6357
adapter contract = skills-test-fixtures/codex-eval-adapter@16
model            = gpt-6-luna
reasoning        = low
formal host      = Codex only
```

共享 `parse_codex_eval_evidence.py` 原样使用，不再替换成 root-history wrapper。

## 5. Recipe Preflight

`PC68-R1` 仍依赖真实 runtime 事件，因此 Gate 2 PASS 前需要一次最小 Preflight。只检查当前正式 profile 是否实际返回 r13 所需的 raw final-answer source，不执行 Issue #68 业务、不委派邮件生成 agent、不计作正式 acceptance。

固定入口：

```bash
python .apm/skills/professor-contact/tests/runtime/check_issue68_codex_final_source_r13.py \
  --eval-direnv-root <eval-server-direnv-root> \
  --output-dir <fresh-run-root>
```

入口通过 `direnv exec <root> printenv EVAL_PORT` 使用现有 eval service；请求由 `build_issue68_codex_request_r12.py` 生成，因此 model/reasoning/sandbox/trust 形状与正式 r13 Codex 请求一致，只把业务 prompt 换成固定的 `Reply with the single word ok`，timeout 为 300 秒。

```text
CAPABILITY_CONFIRMED -> Gate 2 的 Observable 前提满足，可进入正式 PC68-R1
CAPABILITY_ABSENT    -> 停在正式 PC68-R1 之前，不重试、不改模型、不改服务
INVALID_EVIDENCE     -> 修证据/判定程序，不执行正式 PC68-R1
CASE_NOT_STARTED     -> 修 bootstrap/transport，不执行正式 PC68-R1
```

该检查不判断 native delegation；正式 delegation 仍由 `skills-test-fixtures@16` 和正式 `PC68-R1` 机器证据判断。

Preflight 只证明观察面。`gate2-r12` 权威记录保留的其余要求继续有效：正式 `PC68-R1` 的每次尝试在验收执行前必须归档实际运行实例的直接构建来源和本次证明依赖的隔离证据，与 r13 证据契约的 `eval_server_revision`（当前冻结 `3fdfa9387140cfc2e2aa3af415f85015f79706d2`，即第 1 节 eval-server current master）与 `eval_server_revision_role` 对齐。缺这两项归档时，即使 Preflight 通过也不得宣布 Gate 2 完成。

## 6. Discriminating 回归

`test_issue68_runtime_r13.py` 固定以下反例：

- 旧 turn 内容冲突、当前 final 正确：PASS；
- 旧 turn 正确、当前 final 违反业务结果：`FAIL_PRODUCT`；
- 当前只有 commentary，旧 turn 或 child 有 final：`BLOCKED_OBSERVABILITY`；
- 完全没有当前 raw final：`BLOCKED_OBSERVABILITY`；
- 当前 turn 有两个 final：`INVALID_EVIDENCE`；
- selected raw message 内容损坏：`INVALID_EVIDENCE`；
- raw event 缺 `turnId`：`INVALID_EVIDENCE`；
- 多个 `output_text` 按 Codex 源码顺序拼接；
- Preflight 与正式 verifier 复用同一 final-source selector；
- bridge 固定 `c738fa2…` 且不替换共享 parser；
- evidence contract 不再出现 `root_thread_read` 或额外 eval-server patch 前提。

## 7. 当前关口

```text
Gate 1: PASS + COMPLETE，未重开
PC68-D1/P1–P7: 历史 PASS 保留；最终合并版本是否需重执行仍按 main 合入后的依赖分析决定
PC68-R1 Gate 2 design: 修正完成
PC68-R1 Recipe Preflight: 未执行
Gate 2: 未完成 / PARTIAL
Gate 3: NOT_READY / PARTIAL
Merge: NOT_READY
```

当前缺少的事实有两项。第一，用当前正式 `gpt-6-luna` profile 对现有 eval service 执行一次 r13 Preflight，确认实际 raw message 带可归属的 `phase=final_answer`；在该结果出现前不得把源码“字段可选存在”直接当作实际环境已可观察。第二，按 `gate2-r12` 权威记录归档实际服务构建来源与隔离依据（见第 5 节与 r13 证据契约的 `eval_server_revision`/`formal_run_archive_requirements`）；Preflight 通过本身不构成该项证据。

下一责任人：本地执行 agent。只执行第 5 节 Preflight，不执行正式 `PC68-R1`；结果交回测试工程师判定 Gate 2。
