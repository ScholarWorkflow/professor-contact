# Issue #68 / PR #72 Gate 2 候选记录 r23 — 单一权威测试实现

记录版本：`issue68-r23-authoritative-candidate-2026-10-05`。

本文件是**测试实现记录与 Gate 2 候选材料，不是第二关口权威结论**。按 r22 第二关口完整复审（PR 评论 `5992000966`）阻断项 2 的最小修改，本记录把 Test Plan r20 的完整 requirement mapping、两个 case 的完整 Recipe、当前 Preflight、parser/evaluator/终态、复验依赖与取代关系合并为单一自包含候选；分别写明被测产品版本与测试实现/判定程序版本。是否通过 Gate 2 由测试审核者决定。

**取代关系**：本记录完整取代 `docs/issue68-test-gate-r19.md`、`issue68-test-gate-r20.md`、`issue68-test-gate-r21.md`、`issue68-test-gate-r22.md` 的候选地位（四份旧记录保留审计，正文已标注被取代）；同时取代 PR 正文与相关记录中"Test Plan r19"等过期指针——当前唯一有效测试计划为 Test Plan r20。

## 0. 双版本绑定（r22 阻断项 2）

| 角色 | 版本 | 影响分析 |
| --- | --- | --- |
| 被测产品（formal acceptance 对象） | `ScholarWorkflow/professor-contact@a22901229259c4bf7e36fe45f8207ab0b1ef7d72` | 产品 Stage-5 数据流在 `a229012` 已完成 plan r12 实现（`37ee473` partition、`8b9a9cb` 分区回归、`cc44247` 文档），此后到当前头 `44918c3` 的提交（`a229012`、`f34aeba`、`44918c3` 本分支 3 个）**只改 `.apm/skills/professor-contact/tests/` 与 `docs/`，`git diff a229012..44918c3 -- scripts agents SKILL.md workflow-reference.md` 为空**，被测行为、入口、输入输出 contract 无变化 |
| 测试实现 / 判定程序 | `ScholarWorkflow/professor-contact@44918c3 + 工作树未提交的 r23 修正（提交后以其 SHA 为准）` | contract revision `issue-68-runtime-evidence-r23-2026-10-05`；测试资产以本记录 §6 清单为准 |
| 共享 fixture adapter | `skills-test-fixtures@c738fa2f8bcbb16cd99d741332d5f59b062b6357`（adapter@16） | 未变 |
| eval-server | `3fdfa9387140cfc2e2aa3af415f85015f79706d2`（检出干净） | 未变 |
| 模型/请求 | Project Consensus 默认：`gpt-6-luna`，`build_issue68_codex_request_r12.py` | 未变 |

Gate 3 正式执行时：`PC68-D1`/`PC68-R1` 的 producer SHA 记为当时 PR 头（若审核者批准后在产品实现上无新提交，即为 `44918c3` 及其后续纯测试提交所在头的父级产品内容——以 `--producer-sha` 实参记录为准），测试实现 SHA 记为当时 PR 头。

## 1. 权威输入

```text
Frozen Acceptance Contract:  issue-68-gate1-r3-2026-10-04（PASS + COMPLETE，Issue #68 评论 5981562292）
Canonical Plan:              issue-68-plan-r12-2026-10-04（APPROVED，PR 评论 5981691686）
Test Plan:                   issue-68-test-plan-r20-2026-10-05（评论 5989428845，取代 r19；G2-1 证据来源经
                             评论 5990445769、5991384143 两次更正后冻结）
本轮复审:                    PR 评论 5992000966（r22 完整复审，4 个阻断项）
Runtime evidence contract:   issue-68-runtime-evidence-r23-2026-10-05（文件名 issue68-runtime-evidence-contract-r19.json，以 revision 字段为准）
```

## 2. Requirement → proof owner → case（Test Plan r20 §2 完整 mapping）

两个正式 case：`PC68-D1`（producer-local deterministic proof）、`PC68-R1`（Codex supported runtime proof）；不新增第三个 case。

| 正式要求 | 证明负责者 | 必须证明的事实 | 实现落点 |
| --- | --- | --- | --- |
| `R68-1` | `PC68-D1/P1` | local `email_pack` 是 Stage 5 authority；无 global fallback / dual authority | `test_contact_state.TestStage5PerProfessorState` t68_1 / t68_1b / t68_1c / t68_2 |
| `R68-2` | `PC68-D1/P2` | targeted 只处理目标；未选中行不阻断；目标自身继续 fail closed | 同类 t68_3 / t68_4 / unselected_malformed_noise + `test_issue68_choices_attribution` r11 targeted 过滤 |
| `R68-3` | `PC68-D1/P3` | 无 `--email-id` 时只覆盖当前 professor pack；same-professor batch 保持整笔校验/提交语义 | t68_5 + `test_issue68_root_partition.TestStage5BatchStaysAtomic` |
| `R68-4` | `PC68-D1/P4` | A/B 独立 transaction；B 失败不回滚或阻断合法 A | t68_6 / validation_updates_only + `test_issue68_root_partition` cx2 + `TestStage5OwnerLocalBundleLoader.test_sibling_explicit_row_in_owner_bundle_fails_closed` |
| `R68-5` | `PC68-D1/P5` | program overview 是派生输出，不进入 local finalize commit gate | t68_7 + `test_stage5_overview.TestStage5OverviewRebuild` 全类 |
| `R68-6` | `PC68-D1/P1` | #68 不新增 migration/global fallback/dual-read/dual-write；#67 ownership 是冻结依赖 | P1 组件承载（t68_2、t68_1c）；随 P1 复验 |
| `R68-7` | `PC68-D1/P2 + P4` | validator / record-validation 只以当前 professor 本次输出为条件 | P2 的 t68_3/t68_4/r11 targeted + P4 的 validation_updates_only |
| `R68-8` | `PC68-D1/P4 + P7`、`PC68-R1` | partition/bundle 不含 sibling；运行时 owner 实际取得/读取的业务数据只属于自己 | P4 cx2/owner-entry 隔离 + P7 partition 全类；runtime `owner_input_contains_sibling_data` / `owner_bundle_choices_changed` |
| `AD68-1` | `PC68-R1`（`P5` 辅助） | root 委派各 owner，**取得/消费**各 owner result 后最多一次 rebuild overview | runtime 回执消费链（§5）+ `aggregate_precedes_result_consumption` + `multiple_aggregate_rebuilds` |
| `AD68-2` | `implementation_scope: #48` | writer-lock ownership 归 #48；#68 不改 writer ownership / canonical rebuild interface，故无独立 case；#48 状态不是 #68 的 Merge Gate | 无测试组件；#68 触碰上述接口时才重开 |
| `AD68-3` | `PC68-D1/P6` | standalone discovery 只读；坏 B 只成 B row，不影响合法 A/C | `TestStage5ListInputs` 全类 + `test_issue68_r19_scope_emission_is_not_supported` + cx7 |
| `AD68-4` | `PC68-D1/P7`、`PC68-R1` | raw multi-professor choices 只在 root deterministic partition；owner 不收 cross-prof scope；legacy ambiguity 不广播 | P7 `TestStage5RootPartition` 全类 + runtime `root_partition_*` / `owner_input_carries_choices_scope` |
| `AD68-5` | `PC68-D1/P7`、`PC68-R1` | one-professor transport；canonical 原样；临时 transport 不恢复 sibling 数据 | P7 行保持/重跑一致 + runtime `canonical_preservation` + `test_r12_owner_bundle_has_no_scope_and_no_sibling_state_paths` |

`PC68-D1` 不证明 Codex native delegation、真实 child 输入观察、root 对 child result 的实际消费、运行时调用顺序——只归 `PC68-R1`。

## 3. `PC68-D1` Recipe（完整）

正式入口：

```bash
python3 tests/runtime/run_issue68_stage5_routing.py \
  --case PC68-D1 \
  --producer-root <clean producer checkout> --producer-sha <被测产品 SHA> \
  --output-dir <空目录>
```

入口只发现 `test_issue68_stage5_local_state.TestIssue68Stage5LocalState` 的 7 个 `test_stage5_*` 方法（集合精确校验，否则 `INVALID_TEST_EXECUTION/unexpected_test_set`），组件映射见 §2 落点列；skip/非普通结局即失败。运行环境：`"$HOME/.local/share/uv/python/cpython-3.14-macos-aarch64-none/bin/python3"`（≥3.11，tomllib）。产物：`proofs.json`、`unittest.txt`。判定：全部组件普通通过 → 该 case PASS；任何失败/错误 → FAIL。

## 4. `PC68-R1` Recipe（完整）

### 4.1 fixture（`prepare_issue68_stage5_routing.py`，由 base runner 自动调用）

A（`試験 教授`）/B（`佐藤 花子`）local pack（`evidence:none, verified:missing`）、synthetic template、噪声 legacy row、坏包；写 `canonical-choices.json` 后用安装 producer CLI 真实运行一次 `stage5-partition-choices`（stdout/stderr/exit-code 留证；每个 owner `partition.status=ok` 且 rows 与构造行一致，否则 ValueError）；per-owner rows 落盘 `owner-{i}-bundle-choices.json`；initial-plan 预检 → `needs_recheck:missing`；plan-with-result（带 `--choices` bundle）预检 → `needs_refresh`（exit 2）。manifest：`owners[i].expected_choices_rows / expected_bundle_file / sibling_exclusions`、顶层 `partition.owners`、无 `expected_scope`、`pre_run_hashes`、`manual_patch:"no"`。prompt：root 一次 partition → one-professor bundle → owner，禁止广播与模型拆分。

### 4.2 正式入口

```bash
python3 tests/runtime/run_issue68_stage5_routing_r19_codex.py \
  --producer-root <clean producer checkout> --producer-sha <被测产品 SHA> \
  --fixture-root <skills-test-fixtures@c738fa2 clean checkout> \
  --fixture-sha c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root <eval-server@3fdfa938 检出目录> \
  --output-dir <空目录>
```

单次正式请求，不重试。`EVAL_PORT` 只按 Project Consensus 用 `direnv exec <eval-root> printenv EVAL_PORT` 取得；direnv 缺失/非法 → `eval_port_unavailable` 拒绝启动（无第二来源）。服务 provenance（lsof/ps 唯一监听者 + 存储隔离）前后各归档一次，不一致 → `INVALID_TEST_EXECUTION/eval_service_changed_during_execution`。请求经 r12 builder（gpt-6-luna）发往共享 eval 服务；evidence 经共享 fixture adapter（`parse_codex_eval_evidence`）产出 `codex-adapter.json` 后交 r23 verifier。

### 4.3 判定条件（verifier，contract `issue-68-runtime-evidence-r23-2026-10-05`）

前提门：adapter 状态门；formal children 恰 2（`spawnAgent` + `sender_thread_id==output.thread_id`）；`runtime_seq` 严格递增；`terminal_precedence`（FAIL → INVALID → BLOCKED）；`termination_reason=completed`；root 最终业务结果 = 唯一当前 root/turn `final_answer`（r13 selector），单层包装（list、`{"results":[…]}`、恰一键 list）可解析，嵌套诊断不递归；identity 字段仅 diagnostics。

per-child 消费判定（消费面 = child 命令文本同时引用 `contact_state.py` 与 stage5 动作词；JSON/Python literal 内嵌）：

| 条件 | 终态 / reason |
| --- | --- |
| >1 个不同可归属对象 | `INVALID_EVIDENCE / owner_business_object_ambiguous` |
| 有消费面无对象 | `BLOCKED_OBSERVABILITY / owner_business_object_unobservable` |
| 无面且无明文兜底 | `BLOCKED_OBSERVABILITY / completed_user_payload_unobservable` |
| `email_pack` 非本次 owner | `FAIL_PRODUCT / unexpected_owner_pack` |
| 对象含 `choices_scope` 键 | `FAIL_PRODUCT / owner_input_carries_choices_scope` |
| 缺 `choices` | `FAIL_PRODUCT / choices_transport_missing` |
| rows ≠ expected（精确相等；`試験`→`试验` 在此 FAIL） | `FAIL_PRODUCT / owner_bundle_choices_changed` |
| 序列化对象含 sibling marker | `FAIL_PRODUCT / owner_input_contains_sibling_data` |
| 带 `email_id` 非本 owner | `FAIL_PRODUCT / owner_target_mismatch` |

**root 结果消费（冻结字段链）**：`subAgentActivity` 的 `agentThreadId -> agentPath` 仅关联键，每 child 映射必须唯一（0 → BLOCKED `root_result_consumption_unobservable`/`missing_agent_path_mapping`；>1 → INVALID `child_agent_path_mapping_ambiguous`）；唯一合法回执 = root 线程当前 turn 的 `agent_message`（`author==child_agent_path`、`recipient=="/root"`、正文严格 `Message Type: FINAL_ANSWER / Task name: /root / Sender: <path> / Payload:\n<JSON>`）；**Payload 只读顶层 `professor_dir/status/reason_code`，不递归嵌套**；判定：无合法回执 → BLOCKED；outcome 歧义 → INVALID `root_result_receipt_ambiguous`；outcome ≠ child 自身返回 → FAIL `root_receipt_payload_changed`；消费点 = 最早合法回执 seq。

root 编排：discovery 恰为 `{A ok, B ok, invalid_pack error}`（严格解析的 discovery 带 `--emit-choices-scope` → FAIL）；root 恰一次成功 `stage5-partition-choices` 且输出与 manifest 一致（`root_partition_not_deterministic` / `multiple_root_partitions` / `root_partition_changed`；child 执行 → `partition_executed_by_owner`）；成功 partition 完成前任何 owner 业务调用开始 → `owner_business_precedes_partition`；严格解析的 plan 禁 `--choices-scope`、`--email-pack` 绑定归属 pack、`--choices` 文件 rows == expected；`stage5-rebuild-overview` ≤1 且 start > max(消费点)；root 终局行每 owner 恰一个一致 outcome 且等于消费 outcome。复合命令（`python3 -c` 等）不提供 flags，flag 级检查仅覆盖严格解析调用；root 复合 ≥2 动作词 → `BLOCKED_OBSERVABILITY/root_orchestration_ambiguous`。

### 4.4 终态（r20 §5）

`PASS` / `FAIL_PRODUCT` / `BLOCKED_OBSERVABILITY` / `INVALID_EVIDENCE` / `CASE_NOT_STARTED` / `NOT TESTED`；provider/model/access/harness 问题不判产品 FAIL。

## 5. Preflight（r20 §6 四项；不含正式验收）

```text
Recipe Preflight（2026-10-05，r23）
- executable: NOT satisfied（当前环境）— EVAL_PORT 正式来源 direnv 在当前环境缺失；正式入口按
  G2-2 修正只认 direnv，缺即 eval_port_unavailable 拒绝启动。Recipe 无需再改；在具备 Project
  Consensus 正式环境处补最小 Executable Preflight（保存 direnv printenv 输出 + 入口可达 case
  边界证据）后本项即满足。服务实况（r15 归档同一实例 PID 40721，冻结检出干净）仅作环境证据。
- isolated: supported — /tmp/pc68-r19-work/isolation-now.json（ISOLATION_CONFIRMED；
  CODEX_HOME=/private/tmp/test-codex-home，sqlite/log 均在内）；入口保留输出目录非空拒绝、
  overlaps 检查、前后隔离归档。
- observable: supported — 冻结回执链在 r15 正式 raw 逐项核验（turnId/author/recipient/四段形状/
  Payload 顶层 outcome；agentThreadId 与 formal children 一致）；wait.rs 佐证 wait 项配对字段恒空。
- discriminating: supported — r23 回归 39 项三通道：默认合法 → PASS；sibling/choices_scope/
  载荷改写/canonical 转写/跨 child 正文/嵌套 Payload/冲突 agentPath/回执缺失歧义 → 各对应
  FAIL/INVALID/BLOCKED；真实数据负例：r15 raw 重判 FAIL_PRODUCT/owner_input_carries_choices_scope。
- critical assumption gap: direnv 缺失（executable 未满足）为唯一未闭合项。
```

## 6. 测试资产清单（判定程序版本）

```text
tests/runtime/issue68-runtime-evidence-contract-r19.json  revision=issue-68-runtime-evidence-r23-2026-10-05
tests/runtime/run_issue68_stage5_routing.py               base runner（PC68-D1 入口；未改）
tests/runtime/run_issue68_stage5_routing_r19.py           bridge（r12 builder + r23 verifier pin）
tests/runtime/run_issue68_stage5_routing_r19_codex.py     r23 Codex-only 正式入口
tests/runtime/verify_issue68_stage5_routing_r19.py        r23 verifier
tests/runtime/prepare_issue68_stage5_routing.py           fixture builder（一次真实 partition）
tests/runtime/prompts/issue68-stage5-root.txt             root prompt（一次 partition → one-professor bundle）
tests/test_issue68_runtime_r19.py                         39 项反例矩阵 + 三通道声明
tests/test_issue68_stage5_local_state.py + test_issue68_root_partition.py + test_issue68_choices_attribution.py
                                                          PC68-D1 PROOFS 资产
历史资产（r11–r22 文件）保留审计，不在当前链路。
```

## 7. 回归与真实数据证据

```text
r23 修正后：test_issue68_runtime_r19 39 tests OK；r18/recipe/r13/r14/r12_codex 61 tests OK；
r15 raw 重判 FAIL_PRODUCT/owner_input_carries_choices_scope（/tmp/pc68-r19-work/r23-rejudge-real-raw.json）。
基线口径：全量 973 项中 5 个失败 = 基线 cc44247 既有（issue 32/57 资产清单测试），REGRESSION_DELTA 零新增。
```

## 8. 复验依赖（r20 §7）

```text
P4, P6, P7 = EXECUTE_CURRENT；PC68-R1 = EXECUTE_CURRENT
P2/P3、P1/P5 = 当前 diff 未触及其 declared behavior/oracle，可 REUSE_PRIOR_PASS（记录影响分析）
R68-6 随 P1；R68-7 随 P2/P4；AD68-2 仅在 #68 触碰 writer ownership / canonical rebuild interface 时重开
```

## 9. 当前状态

```text
Gate 2: 阻断项 3、4 已修正，阻断项 2 已由本单一自包含候选闭合；阻断项 1（Executable）待正式
        环境 direnv 可用后补最小 Preflight。等待测试审核者完整复审（本记录不自行宣告 PASS）。
Gate 3: NOT_READY（PC68-R1 继续暂停；PC68-D1 未按本 Recipe 正式执行）
Merge:  NOT_READY
```
