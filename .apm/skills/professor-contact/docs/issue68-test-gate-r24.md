# Issue #68 / PR #72 Gate 2 候选记录 r24 — Test Plan r21 单一权威测试实现

记录版本：`issue68-r24-r21-authoritative-candidate-2026-10-05`。

本文件是**测试实现记录与 Gate 2 候选材料，不是第二关口权威结论**。它按 Test Plan r21（`issue-68-test-plan-r21-2026-10-05`，PR 评论 `5992834520`，取代 r20）与 r23 Gate 2 复审（PR 评论 `5992000966`）处理 4 个阻断项，并把全部内容合并为单一自包含候选。是否通过 Gate 2 由测试审核者决定。

**取代关系**：本记录完整取代 `docs/issue68-test-gate-r19.md`～`issue68-test-gate-r23.md` 的候选地位（旧记录保留审计并已标注被取代）；当前唯一有效测试计划为 **Test Plan r21**（取代 r20；r20 的 G2-1 证据来源先后经评论 `5990445769`、`5991384143` 更正）。

## 0. 版本绑定（r22 复审阻断项 4 / r23 复审阻断项 4 修正：全部固定到真实提交，无占位文字）

| 角色 | 版本 | 说明 / 影响分析 |
| --- | --- | --- |
| 被测产品 | `ScholarWorkflow/professor-contact@a22901229259c4bf7e36fe45f8207ab0b1ef7d72` | 产品 Stage-5 实现完成于 `a229012`；`git diff a229012..HEAD -- scripts agents SKILL.md workflow-reference.md` 为空——其后全部提交只改 `tests/` 与 `docs/`，被测行为、入口、输入输出 contract 无变化（影响分析：无需重验产品事实） |
| 测试实现 / 判定程序（代码） | `ScholarWorkflow/professor-contact@ea3384464eb857210284ddbf68f9d2aec16746b0` | 包含 r23 复审要求的全部 verifier/contract/test 代码修正与 r24 新增（entry 封顶、malformed 回执、gap 延迟归桶） |
| 其后纯文档提交 | `44918c3`（r22 记录）、`e090217`（r23 记录）、`a5143df`（r23 Preflight 补齐）、r24 记录所在提交 | 仅 `docs/` 变更，不影响任何 oracle、命令或判定；逐次影响分析：无 |
| 共享 fixture adapter | `skills-test-fixtures@c738fa2f8bcbb16cd99d741332d5f59b062b6357`（adapter@16） | 未变 |
| eval-server | `3fdfa9387140cfc2e2aa3af415f85015f79706d2`（检出干净） | 未变 |
| 模型/请求 | Project Consensus 默认 `gpt-6-luna`，`build_issue68_codex_request_r12.py` | 未变 |

## 1. 权威输入

```text
Frozen Acceptance Contract:  issue-68-gate1-r3-2026-10-04（PASS + COMPLETE，评论 5981562292）
Canonical Plan:              issue-68-plan-r12-2026-10-04（APPROVED，评论 5981691686）
Test Plan:                   issue-68-test-plan-r21-2026-10-05（评论 5992834520，取代 r20；complete）
Runtime evidence contract:   issue-68-runtime-evidence-r24-2026-10-05（文件名 issue68-runtime-evidence-contract-r19.json，
                             以 revision 字段为准）
Gate 2 相关评论:             5990445769（撤销 agentsStates）、5991384143（冻结回执字段链）、5992000966（r22 复审）、
                             5992834520（r23 复审 + Test Plan r21）
```

## 2. Requirement → proof owner → case（Test Plan r21 §1 完整 mapping）

两个正式 case：`PC68-D1`（producer-local deterministic proof）、`PC68-R1`（Codex supported runtime proof）；不新增第三个 case。

| 正式要求 | 证明负责者 | 必须证明的事实 | 实现落点 |
| --- | --- | --- | --- |
| `R68-1` | `PC68-D1/P1` | local `email_pack` 是 Stage 5 唯一 authority；无 global fallback / dual authority | `test_contact_state.TestStage5PerProfessorState` t68_1 / t68_1b / t68_1c / t68_2 |
| `R68-2` | `PC68-D1/P2` | targeted 只处理目标；无关行不阻断；目标自身继续 fail closed | 同类 t68_3 / t68_4 / unselected_malformed_noise + `test_issue68_choices_attribution` r11 targeted 过滤 |
| `R68-3` | `PC68-D1/P3` | 无 `--email-id` 时只覆盖当前 professor pack；same-professor batch 保持整笔语义 | t68_5 + `test_issue68_root_partition.TestStage5BatchStaysAtomic` |
| `R68-4` | `PC68-D1/P4` | A/B 独立 transaction；B 失败不回滚或阻断合法 A | t68_6 / validation_updates_only + `test_issue68_root_partition` cx2 + `TestStage5OwnerLocalBundleLoader.test_sibling_explicit_row_in_owner_bundle_fails_closed` |
| `R68-5` | `PC68-D1/P5` | program overview 是派生输出，不进入 local finalize commit gate | t68_7 + `test_stage5_overview.TestStage5OverviewRebuild` 全类 |
| `R68-6` | `PC68-D1/P1` | #68 不新增 migration/global fallback/dual-read/dual-write | P1 组件承载（t68_2、t68_1c）；随 P1 复验 |
| `R68-7` | `PC68-D1/P2 + P4` | validator / record-validation 只以当前 professor 本次输出为条件 | P2 的 t68_3/t68_4/r11 targeted + P4 的 validation_updates_only |
| `R68-8` | `PC68-D1/P4 + P7`、`PC68-R1` | deterministic bundle 不含 sibling；**运行时从 owner invocation 入口开始，实际交给 owner 或 owner 在入口实际读取的完整业务输入中不存在 sibling 数据** | P4/P7 deterministic 面；runtime：`owner_entry_transport_unobservable` 封顶 + 消费面 sibling oracle（见 §5） |
| `AD68-1` | `PC68-R1`（`P5` 辅助） | root 委派 owner，实际取得/消费各 owner result 后最多一次 rebuild overview | runtime 回执消费链 + `aggregate_precedes_result_consumption` + `multiple_aggregate_rebuilds` |
| `AD68-2` | `implementation_scope: #48` | writer-lock ownership 归 #48；#68 不改 writer ownership / canonical rebuild interface | 无测试组件；#68 触碰上述接口时才重开 |
| `AD68-3` | `PC68-D1/P6` | standalone discovery 只读；坏 B 不影响合法 A/C | `TestStage5ListInputs` 全类 + scope-emission 负向 oracle + cx7 |
| `AD68-4` | `PC68-D1/P7`、`PC68-R1` | raw multi-professor choices 只在 root deterministic partition；**owner-entry transport/read 不含 cross-professor scope** | P7 partition 全类 + runtime partition oracle + entry 封顶 |
| `AD68-5` | `PC68-D1/P7`、`PC68-R1` | one-professor transport；canonical 原样；**正式传入 owner 的完整 transport/read 对象本身不得恢复 sibling 数据** | P7 行保持/隔离 oracle + runtime `canonical_preservation` + entry 封顶 |

`PC68-D1` 不证明 native delegation、root→owner 实际运行时传递、root 对 child result 的消费及 aggregate 顺序——只归 `PC68-R1`。

## 3. `PC68-D1` Recipe（完整）

```bash
python3 tests/runtime/run_issue68_stage5_routing.py \
  --case PC68-D1 \
  --producer-root <clean producer checkout> --producer-sha <被测产品 SHA> \
  --output-dir <空目录>
```

入口只发现 `test_issue68_stage5_local_state.TestIssue68Stage5LocalState` 的 7 个 `test_stage5_*` 方法（集合精确校验，否则 `INVALID_TEST_EXECUTION/unexpected_test_set`）；组件映射见 §2 落点列；skip/非普通结局即失败。运行解释器 ≥3.11（`$HOME/.local/share/uv/python/cpython-3.14-macos-aarch64-none/bin/python3`）。产物 `proofs.json`、`unittest.txt`；判定：全部组件普通通过 → PASS，否则 FAIL。

## 4. `PC68-R1` Recipe（完整）

### 4.1 fixture（base runner 自动调用 `prepare_issue68_stage5_routing.py`）

A（`試験 教授`）/B（`佐藤 花子`）local pack、synthetic template、噪声 legacy row、坏包；对 `canonical-choices.json` 用安装 producer CLI 真实运行一次 `stage5-partition-choices`（证据留存；owner `partition.status=ok` 且 rows 与构造行一致，否则 ValueError）；per-owner rows 落盘 `owner-{i}-bundle-choices.json`；initial-plan → `needs_recheck:missing`；plan-with-result（带 `--choices` bundle）→ `needs_refresh`（exit 2）。manifest：`owners[i].expected_choices_rows / expected_bundle_file / sibling_exclusions`、顶层 `partition.owners`、无 `expected_scope`、`pre_run_hashes`、`manual_patch:"no"`。prompt：root 一次 partition → one-professor bundle → owner，禁止广播与模型拆分。

### 4.2 正式入口

```bash
python3 tests/runtime/run_issue68_stage5_routing_r19_codex.py \
  --producer-root <clean producer checkout> --producer-sha <被测产品 SHA> \
  --fixture-root <skills-test-fixtures@c738fa2 clean checkout> \
  --fixture-sha c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root <eval-server@3fdfa938 检出目录> \
  --output-dir <空目录>
```

单次正式请求，不重试。`EVAL_PORT` 只经 `direnv exec <eval-root> printenv EVAL_PORT` 取得（正式 Preflight 已核实输出 17902；direnv 位于 `/Users/rekidunois/.local/bin/direnv`）；缺失/非法 → `eval_port_unavailable` 拒绝启动。服务 provenance 前后归档，不一致 → `INVALID_TEST_EXECUTION/eval_service_changed_during_execution`。

### 4.3 判定条件（verifier，contract `issue-68-runtime-evidence-r24-2026-10-05`）

前提门：adapter 状态门；formal children 恰 2（`spawnAgent` + `sender_thread_id`）；`runtime_seq` 严格递增；`terminal_precedence`（FAIL → INVALID → BLOCKED，含 gaps 延迟归桶：缺 started 的 commandExecution 记入 observability gaps 不再早返回，FAIL/INVALID 优先，仅清洁终局被 gap 阻断为 `command_start_unobservable`）；`termination_reason=completed`；root final answer = 唯一当前 root/turn `final_answer`（r13 selector；单层包装可解析，嵌套诊断不递归）；identity 字段仅 diagnostics。

per-child 消费判定（消费面 = child 命令文本同时引用 `contact_state.py` 与 stage5 动作词）：`owner_business_object_ambiguous`（INVALID）→ `owner_business_object_unobservable`（BLOCKED）→ `completed_user_payload_unobservable`（BLOCKED）→ `unexpected_owner_pack` / `owner_input_carries_choices_scope` / `choices_transport_missing` / `owner_bundle_choices_changed` / `owner_input_contains_sibling_data` / `owner_target_mismatch`（均 FAIL_PRODUCT）。

**root 结果消费（冻结字段链，r21/r22 澄清后）**：`subAgentActivity` 的 `agentThreadId -> agentPath` 仅关联键且每 child 必须唯一（0 → BLOCKED `root_result_consumption_unobservable`/missing_agent_path_mapping；>1 → INVALID `child_agent_path_mapping_ambiguous`）；唯一合法回执 = root 线程当前 turn 的 `agent_message`（`author==child_agent_path`、`recipient=="/root"`、正文严格 `Message Type: FINAL_ANSWER / Task name: /root / Sender: <path> / Payload:\n<JSON>`）；**Payload 只读顶层三字段，不递归嵌套**；`professor_dir` 匹配但 `status`/`reason_code` 缺失 → `BLOCKED_OBSERVABILITY/root_result_receipt_malformed`（不再制造 `root_receipt_payload_changed` FAIL）；outcome 歧义 → INVALID；outcome ≠ child 自身返回 → FAIL `root_receipt_payload_changed`；消费点 = 最早合法回执 seq。

**entry transport 封顶（Test Plan r21 §3）**：`owner_entry_evidence_status=NOT_AVAILABLE`（表征：当前 V2 对 owner 的唯一交付是 root→child `agent_message` NEW_TASK，Payload 为 `encrypted_content`，无明文交付、无等价完整入口读取证据）→ 本应 PASS 的终局改判 `BLOCKED_OBSERVABILITY/owner_entry_transport_unobservable`（`capped_from="PASS"`，全部已证 product 事实保留）；FAIL/INVALID 不受封顶影响。合成回归断言封顶而非 PASS；下游 commandExecution 永不替代入口证据。

root 编排：discovery 恰为 `{A ok, B ok, invalid_pack error}`；root 恰一次成功 `stage5-partition-choices` 且输出与 manifest 一致；成功 partition 完成前任何 owner 业务调用开始 → `owner_business_precedes_partition`；plan 禁 `--choices-scope`、`--email-pack` 绑定归属、`--choices` 文件 rows == expected；`stage5-rebuild-overview` ≤1 且 start > max(消费点)；root 终局行每 owner 恰一个一致 outcome 且等于消费 outcome。复合命令不提供 flags，flag 级检查仅覆盖严格解析调用；root 复合 ≥2 动作词 → `BLOCKED_OBSERVABILITY/root_orchestration_ambiguous`。

### 4.4 终态（r21 §4）

`PASS`（当前不可达：entry transport 未满足时封顶 BLOCKED）/ `FAIL_PRODUCT` / `BLOCKED_OBSERVABILITY`（含完整 entry 输入不可观察、`owner_entry_transport_unobservable`、`root_result_receipt_malformed`、`owner_result_consumption_unobservable` 等）/ `INVALID_EVIDENCE` / `CASE_NOT_STARTED` / `NOT TESTED`。provider/model/access/harness 问题不判产品 FAIL。

## 5. Preflight（r21 §6 四项）

```text
Recipe Preflight（2026-10-05，r24）
- executable: satisfied — direnv（/Users/rekidunois/.local/bin/direnv）经正式来源解析：
  direnv exec <eval-server检出> printenv EVAL_PORT → 17902（证据
  /tmp/pc68-r19-work/executable-preflight/direnv_eval_port.txt）；r23/r24 入口经该来源解析同端口，
  capture_service_instance 确认唯一监听者 = 冻结检出同一实例（PID 40721，检出干净）；load_contract 通过。
  备注：更早记录的"direnv 缺失"是会话 PATH 未含 ~/.local/bin 的误判，非环境缺失。
- isolated: supported — /tmp/pc68-r19-work/isolation-now.json（ISOLATION_CONFIRMED）不变。
- observable: NOT satisfied（如实记录）— 完整 owner-entry transport/read 在当前 V2 不可观察：
  表征显示每 child 唯一入口交付为 root→child agent_message NEW_TASK + encrypted_content
  （X seq 13731、Y seq 13937），无明文交付、无等价完整入口读取证据；downstream
  commandExecution 不能替代（r21 §3 证据边界修正）。后果已实现：PASS 封顶
  BLOCKED_OBSERVABILITY/owner_entry_transport_unobservable；PC68-R1 保持暂停。
- discriminating: supported — r24 回归 43 项三通道：合法流程 → 封顶 BLOCKED（capped_from=PASS，
  product 事实保留）；sibling/choices_scope/载荷改写/跨 child 正文/嵌套 Payload/缺字段回执/
  冲突 agentPath/rebuild-before-consumption → 各对应 FAIL/INVALID；entry 封顶保证缺入口证据不 PASS；
  真实数据负例：r15 raw 重判 FAIL_PRODUCT/owner_input_carries_choices_scope（FAIL 不受封顶影响）。
- critical assumption gap: 完整 owner-entry transport/read 无受支持证据来源（Observable 未满足），
  已如实记录并封顶；这是当前唯一未闭合项，恢复途径需上游 runtime 提供受支持的入口证据或验收
  决定人修订 Test Plan r21。
```

## 6. 测试资产清单

```text
tests/runtime/issue68-runtime-evidence-contract-r19.json  revision=issue-68-runtime-evidence-r24-2026-10-05
tests/runtime/run_issue68_stage5_routing.py               base runner（PC68-D1 入口；未改）
tests/runtime/run_issue68_stage5_routing_r19.py           bridge（r12 builder + r24 verifier pin）
tests/runtime/run_issue68_stage5_routing_r19_codex.py     r24 Codex-only 正式入口
tests/runtime/verify_issue68_stage5_routing_r19.py        r24 verifier
tests/runtime/prepare_issue68_stage5_routing.py           fixture builder
tests/runtime/prompts/issue68-stage5-root.txt             root prompt
tests/test_issue68_runtime_r19.py                         43 项反例矩阵 + 三通道声明
tests/test_issue68_stage5_local_state.py / test_issue68_root_partition.py / test_issue68_choices_attribution.py  PC68-D1 资产
历史资产（r11–r23 文件）保留审计，不在当前链路。
```

## 7. 回归与真实数据证据

```text
r24 修正后：test_issue68_runtime_r19 43 tests OK；r18/recipe/r13/r14/r12_codex 61 tests OK；
r15 raw 重判 FAIL_PRODUCT/owner_input_carries_choices_scope（/tmp/pc68-r19-work/r24-rejudge-real-raw.json，FAIL 不受封顶影响）。
表征脚本：/tmp/pc68-r19-work/1005_entry_deliveries_characterization.py（入口交付加密事实）、
1005_wait_consume_characterization.py（回执面）。
基线口径：全量 973 项中 5 个失败 = 基线 cc44247 既有，REGRESSION_DELTA 零新增。
```

## 8. 复验依赖（r21 §7）

```text
P4, P6, P7 = EXECUTE_CURRENT
PC68-R1    = EXECUTE_CURRENT，但须等 Observable Preflight（当前未满足）与 Gate 2 冻结完成后执行；
             恢复途径：上游 runtime 提供受支持的完整 owner-entry 证据，或验收决定人修订 Test Plan r21
P2/P3、P1/P5 = 产品行为与其 oracle 未变（a229012 以降零产品 diff），可 REUSE_PRIOR_PASS（来源与影响分析见 §0）
R68-8 / AD68-4 / AD68-5 的 runtime proof 因 r21 修订重开；deterministic P4/P7 不因该修订失效
```

## 9. 当前状态

```text
Gate 2: 阻断项 1（Observable）已表征并实现封顶、2（缺字段回执）、3（terminal precedence）、
        4（版本绑定）全部处理；候选材料更新至 r24。Observable 未满足是唯一未闭合事实，
        已如实记录——等待测试审核者完整复审（本记录不自行宣告 PASS）。
Gate 3: NOT_READY（PC68-R1 保持暂停）
Merge:  NOT_READY
```
