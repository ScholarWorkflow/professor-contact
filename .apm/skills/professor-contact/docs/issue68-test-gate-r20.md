# Issue #68 / PR #72 本地测试工程师实现记录 r20 — owner 入口隔离

记录版本：`issue68-r20-owner-local-test-impl-2026-10-05`。

本文件是**测试实现记录与 Gate 2 候选材料，不是第二关口权威结论**。它按 Test Plan r20（`issue-68-test-plan-r20-2026-10-05`，PR 评论 `5989428845`，完整取代 r19）第 10 节的指派：修正 G2-1、G2-2，补齐 r20 §2 的完整 requirement mapping，并把本记录作为唯一自包含 Gate 2 候选（执行者不需要拼接 r19 候选、修正评论 `5989255322` 或本评论之外的任何材料）。是否重开或通过第二关口由测试审核者决定。

本记录完整取代 `docs/issue68-test-gate-r19.md` 的候选地位；r19 记录与更早版本保留审计用途，不再作为现行 authority。

## 1. 输入与版本

```text
Requirement revision:        2026-09-29 user requirement — per-professor state at every stage
Requirement clarification:   2026-10-04 — Stage 5 owner-local data from entry
Frozen Acceptance Contract:  issue-68-gate1-r3-2026-10-04 (PASS + COMPLETE, Issue #68 评论 5981562292)
Canonical Plan revision:     issue-68-plan-r12-2026-10-04 (APPROVED, PR 评论 5981691686)
Test plan revision:          issue-68-test-plan-r20-2026-10-05 (PR 评论 5989428845；取代 r19，r19 及其实现的审计保留)
Runtime evidence contract:   issue-68-runtime-evidence-r20-2026-10-05（文件 tests/runtime/issue68-runtime-evidence-contract-r19.json，
                             文件名沿用 r19，权威版本以本 revision 字段为准，由正式入口 load_contract 校验）
Target PR HEAD:              e9541be3f998598c8ced78bee33e7c0e63374093（产品实现未变；本记录对应测试实现分支头见 §8）
共享 fixture adapter:        skills-test-fixtures@c738fa2f8bcbb16cd99d741332d5f59b062b6357（未变）
eval-server revision:        3fdfa9387140cfc2e2aa3af415f85015f79706d2（未变，检出干净）
模型/配置:                   Project Consensus 默认（gpt-6-luna，r12 request builder，未改）
```

## 2. Requirement → proof owner → case（r20 §2 完整 mapping）

两个正式 case 不变：`PC68-D1`（producer-local deterministic proof）、`PC68-R1`（Codex supported runtime proof）。不新增第三个 case。

| 正式要求 | 证明负责者 | 必须证明的事实 | 当前实现落点 |
| --- | --- | --- | --- |
| `R68-1` | `PC68-D1/P1` | local `email_pack` 是 Stage 5 authority；无 global fallback / dual authority | `test_contact_state.TestStage5PerProfessorState` t68_1 / t68_1b / t68_1c / t68_2 |
| `R68-2` | `PC68-D1/P2` | targeted 只处理目标；未选中行不阻断；目标自身继续 fail closed | 同类 t68_3 / t68_4 / unselected_malformed_noise + `test_issue68_choices_attribution` r11 targeted 过滤 |
| `R68-3` | `PC68-D1/P3` | 无 `--email-id` 时只覆盖当前 professor pack；same-professor batch 保持整笔校验/提交语义 | t68_5 + `test_issue68_root_partition.TestStage5BatchStaysAtomic`（缺一封 humanized → 整笔 `result_missing`、零部分提交、正例对照） |
| `R68-4` | `PC68-D1/P4` | A/B 独立 transaction；B 失败不回滚或阻断合法 A | t68_6 / validation_updates_only + `test_issue68_root_partition` cx2 + `TestStage5OwnerLocalBundleLoader.test_sibling_explicit_row_in_owner_bundle_fails_closed` |
| `R68-5` | `PC68-D1/P5` | program overview 是派生输出，不进入 local finalize commit gate | t68_7 + `test_stage5_overview.TestStage5OverviewRebuild` 全类 |
| `R68-6` | `PC68-D1/P1` | #68 不新增 global→local migration、global fallback、dual-read、dual-write；#67 migration ownership 是冻结依赖 | 由 P1 组件承载（t68_2 legacy global pack cannot change local result；t68_1c 单教授证明）；随 P1 的复验决定复验 |
| `R68-7` | `PC68-D1/P2 + P4` | validator / record-validation 只以当前 professor 本次输出为条件；targeted selected-output scope 不被 sibling 状态扩大 | P2 的 t68_3/t68_4/r11 targeted 过滤 + P4 的 `test_issue68_validation_updates_only_the_named_local_state` |
| `R68-8` | `PC68-D1/P4 + P7`、`PC68-R1` | deterministic partition/bundle 不含 sibling；运行时 owner 实际取得或实际读取并用于业务调用的数据只属于自己 | P4 cx2/owner-entry 隔离 + P7 partition 全类；runtime evaluator `owner_input_contains_sibling_data` / `owner_bundle_choices_changed` |
| `AD68-1` | `PC68-R1`（`P5` 提供 deterministic 辅助证明） | root 委派各 owner，等待并**消费** owner result 后，顶层 request 最多一次 rebuild overview | runtime wait/consume 配对（见 §4.3）+ `aggregate_precedes_result_consumption` + `multiple_aggregate_rebuilds` |
| `AD68-2` | `implementation_scope: #48` | writer-lock ownership 继续属于 #48；#68 不新增第二套 lock；#68 不改变 writer ownership / canonical rebuild interface，故本项不设独立测试 case，#48 实现状态不是 #68 的 Merge Gate | 无测试组件；仅当 #68 触碰 writer ownership / canonical rebuild interface 时重开 |
| `AD68-3` | `PC68-D1/P6` | standalone discovery 只读；坏 B 只形成 B 的 input-resolution failure，不影响合法 A/C | `TestStage5ListInputs` 全类 + `test_issue68_r19_scope_emission_is_not_supported` + cx7 |
| `AD68-4` | `PC68-D1/P7`、`PC68-R1` | raw multi-professor choices 只在 root deterministic partition；owner 不收到 cross-professor scope；legacy ambiguity 不广播 | P7 `TestStage5RootPartition` 全类（cx1–cx5、cx7、确定性重跑、owner-entry 隔离）+ runtime `root_partition_*` / `owner_input_carries_choices_scope` |
| `AD68-5` | `PC68-D1/P7`、`PC68-R1` | one-professor transport；canonical path/ID 原样；临时 transport 不恢复 sibling 数据 | P7 行保持/重跑一致 + runtime `canonical_preservation`（`試験`→`试验` 判 FAIL）+ `test_r12_owner_bundle_has_no_scope_and_no_sibling_state_paths` |

`PC68-D1` 不证明 Codex native delegation、真实 child 输入观察、root 对 child result 的实际消费、运行时调用顺序——这些只归 `PC68-R1`。

## 3. 资产清单与自包含引用

当前链路（全部纳入本仓库版本管理）：

```text
tests/runtime/issue68-runtime-evidence-contract-r19.json   证据 contract，revision 字段 = issue-68-runtime-evidence-r20-2026-10-05
tests/runtime/run_issue68_stage5_routing_r19.py            bridge：pin base runner → r12 request builder + r19 文件名 verifier
tests/runtime/run_issue68_stage5_routing_r19_codex.py      Codex-only 正式入口（CONTRACT_REVISION = r20 串；服务来源/隔离归档；单次请求）
tests/runtime/verify_issue68_stage5_routing_r19.py         evaluator（owner-local 消费 + root partition + wait/consume + 聚合顺序）
tests/test_issue68_runtime_r19.py                          r20 反例矩阵回归（35 项，三通道声明）
tests/runtime/prepare_issue68_stage5_routing.py            fixture：真实运行一次 stage5-partition-choices；per-owner expected rows；无 expected_scope
tests/runtime/prompts/issue68-stage5-root.txt              prompt：root 一次 partition → one-professor bundle → owner；禁止广播
tests/test_issue68_stage5_local_state.py                   PC68-D1 PROOFS（7 个 proof 方法，组件映射见 §2）
tests/test_issue68_root_partition.py / test_issue68_choices_attribution.py / test_issue68_runtime_recipe.py
```

说明：runtime 文件名保留 r19 命名，权威 revision 以 contract JSON 的 `revision` 字段为准（`issue-68-runtime-evidence-r20-2026-10-05`），正式入口 `load_contract()` 强制校验；r20 的语义变化（wait/consume 收窄、direnv 唯一端口来源、partition 顺序）已体现在 contract 与入口中。r11–r18 历史文件原样保留供审计，当前链路不引用其判定逻辑。

## 4. `PC68-R1` Recipe 与判定条件

### 4.1 fixture 与 prompt

与 r19 候选一致（本记录自包含复述要点）：构造 A（`試験 教授`）/B（`佐藤 花子`）local pack、synthetic template、噪声 legacy row、坏包；对 `canonical-choices.json` 用安装的 producer CLI 真实运行一次 `stage5-partition-choices`（stdout/stderr/exit-code 留证，校验每个 owner `partition.status=ok` 且 rows 与构造行一致）；每 owner rows 落盘 `owner-{i}-bundle-choices.json`；plan-with-result 预检带 `--choices` bundle，停在 `needs_refresh`（exit 2）。manifest：`owners[i].expected_choices_rows / expected_bundle_file / sibling_exclusions`、顶层 `partition.owners`、无 `expected_scope`。prompt 要求 root 一次 partition → one-professor bundle，禁止广播与模型拆分。

### 4.2 正式入口与端口来源（G2-2 修正后）

```bash
python3 tests/runtime/run_issue68_stage5_routing_r19_codex.py \
  --producer-root <clean producer checkout at the executed PR head> \
  --producer-sha  <执行时的 PR head SHA> \
  --fixture-root  <skills-test-fixtures clean checkout> \
  --fixture-sha   c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root <eval-server 检出目录> \
  --output-dir    <空目录>
```

`EVAL_PORT` 只按 Project Consensus 用 `direnv exec <eval-root> printenv EVAL_PORT` 取得；direnv 缺失或输出非法 → 入口以 `eval_port_unavailable` 拒绝启动（不再有监听端口扫描 fallback）。服务 provenance（lsof/ps 唯一监听者 + 存储隔离）与隔离归档保留，但只作为隔离证据，不替代端口配置来源。单次正式请求，不重试；服务前后不一致 → `INVALID_TEST_EXECUTION/eval_service_changed_during_execution`。

### 4.3 evaluator 判定条件（r20 收窄后）

前提门不变：adapter 状态、formal children 恰 2（`sender_thread_id`）、`runtime_seq` 严格递增、`terminal_precedence`（FAIL → INVALID → BLOCKED）、`termination_reason=completed`；root 最终业务结果 = 唯一当前 root/当前 turn `final_answer`（r13 selector），单层包装（top-level list、`{"results":[…]}`、恰一键 list 包装）可解析，嵌套诊断不递归；identity 字段仅 diagnostics。

每 child 消费判定（识别面与 r19 一致：child 命令文本同时引用 `contact_state.py` 与任一 stage5 动作词；JSON 或 Python 字面量内嵌）：`owner_business_object_ambiguous`（INVALID，>1）/ `owner_business_object_unobservable`（BLOCKED，有面无对象）/ `completed_user_payload_unobservable`（BLOCKED，无面无兜底）/ `unexpected_owner_pack`、`owner_input_carries_choices_scope`、`choices_transport_missing`、`owner_bundle_choices_changed`（rows 解析后精确相等；`試験`→`试验` 在此 FAIL）、`owner_input_contains_sibling_data`、`owner_target_mismatch`（全部 FAIL_PRODUCT）。

root 编排判定：discovery 恰为 `{A ok, B ok, invalid_pack error}`（严格解析的 discovery 带 `--emit-choices-scope` → FAIL）；root 恰一次成功 partition 且输出与 manifest 一致（`root_partition_not_deterministic` / `multiple_root_partitions` / `root_partition_changed` / child 执行 → `partition_executed_by_owner`）；**r20 顺序事实：成功 partition 完成前任何 owner 业务调用开始 → `FAIL_PRODUCT/owner_business_precedes_partition`**；严格解析的 plan 禁 `--choices-scope`、`--email-pack` 必须等于归属 pack、`--choices` 文件 rows 必须等于 expected；**wait/consume（G2-1 修正后）：root result-consumption 只由 `collabAgentToolCall` wait 的 per-child `agentsStates` 配对证明（status completed + message）；child `turn/completed` 与 root `subAgentActivity kind=completed` 只是 child-completion 证据，绝不替代消费点；缺配对 → `BLOCKED_OBSERVABILITY/completion_or_wait_unobservable`（detail `missing_wait_pairing`），不得借 completion 面 PASS**；wait 点早于 child 完成点 → `wait_precedes_owner_completion`；`stage5-rebuild-overview` ≤1 且晚于全部消费点（`aggregate_precedes_result_consumption`）；root 终局行每 owner 恰一个一致 outcome 且等于消费 outcome。

### 4.4 终态

与 r20 §5 一致：`PASS` / `FAIL_PRODUCT` / `BLOCKED_OBSERVABILITY`（正式入口已到达但受支持观察面缺事实，例如 wait 配对缺失、root result consumption 不可观察）/ `INVALID_EVIDENCE` / `CASE_NOT_STARTED` / `NOT TESTED`。provider/model/access/harness 问题不判产品 FAIL。

## 5. Preflight（Test Plan r20 §6 四项）

```text
Recipe Preflight（2026-10-05，r20 修正后复核）
- executable: NOT satisfied（当前环境）— EVAL_PORT 的正式来源 `direnv exec .` 在当前环境不可用
  （command -v direnv 为空），r20 修正后入口已无第二来源，正式 PC68-R1 无法从当前环境启动；
  正式入口/bridge/verifier 可导入并通过 --help，contract 绑定由回归断言。共享 eval 服务实况 =
  r15 归档 provenance 同一实例（PID 40721，端口 17902，冻结检出 3fdfa938，检出干净），仅作
  环境证据，不替代端口配置来源。direnv 可用后本项即可满足，Recipe 本身无需再改。
- isolated: supported — 活体快照 /tmp/pc68-r19-work/isolation-now.json：CODEX_HOME=/private/tmp/test-codex-home
  （≠ ~/.codex），config.sqlite_home 与 log_dir 均在测试 CODEX_HOME 内 → ISOLATION_CONFIRMED；
  正式入口保留输出目录非空拒绝、overlaps 检查与前后隔离归档。
- observable: characterized — r15 归档（830 events，2 formal children）证明：child commandExecution
  携带明文 packet（含 python -c 复合形状）、root discovery/partition 输出在 aggregatedOutput、child
  turn/completed 与 root subAgentActivity completed 可观察、root final_answer 经 r13 selector 可选。
  r20 收窄后的关键区分：该归档的 wait 配对字段为空 → 若产品行为全部合法，该类运行按 r20 §4.2
  如实判 BLOCKED_OBSERVABILITY（消费点不可观察），而不是借 completion 面 PASS。
- discriminating: supported — r20 回归 35 项（synthetic，含 §3.2.2 三通道显式声明与互洽断言）：
  有效 owner-local 运行（agentsStates 配对齐全）→ PASS；child 消费 sibling sentinel/choices_scope/
  rows 改写/canonical 转写 → FAIL_PRODUCT；rebuild 位于 child 完成之后、消费点之前 → FAIL；
  owner 业务先于 partition 完成 → FAIL；消费证据缺失 → BLOCKED；歧义 → INVALID。
  真实数据负例：r15 归档 raw 经 r20 verifier 只读重判 → FAIL_PRODUCT/owner_input_carries_choices_scope
  （/tmp/pc68-r19-work/r20-rejudge-real-raw.json；terminal_precedence 保证已证实的产品失败不被
  另一 child 的 missing_wait_pairing blocker 降级）。
- critical assumption gap: 当前环境 direnv 缺失（executable 未满足）为唯一未闭合项，已如实记录；
  其余无已知 gap。
```

r13 capability 证据（`pr72-r13-preflight-exec-2026-10-04`）按 r20 contract `capability_reuse_rule` 复用：r20 未改 request builder、模型、final-source selector、fixture adapter 与 eval-server revision。

## 6. 回归证据

```text
2026-10-05，r20 修复后（工作树内未提交差异 + 已提交基线）：
test_issue68_runtime_r19                                  35 tests OK（含 G2-1/G2-2/partition 顺序新反例）
issue68 全模块（D1 资产 33 + r18/r12/r13/r14/recipe/m1/m2 等）129 tests OK
r15 归档只读重判：FAIL_PRODUCT/owner_input_carries_choices_scope（不因 wait 配对缺失降级）
基线 REGRESSION_DELTA 口径与 r19 候选一致：全量 973 项中仅 5 个失败 = 基线 cc44247 既有
（issue 32/57 资产清单测试），本次零新增回归。
```

## 7. 复验依赖（r20 §7 执行决定建议）

```text
P4, P6, P7 = EXECUTE_CURRENT
PC68-R1    = EXECUTE_CURRENT
P2/P3      = 当前 diff 未改 targeted / same-professor batch 行为、输入或 oracle → 可 REUSE_PRIOR_PASS（记录影响分析）
P1/P5      = 当前 diff 未改 local authority/global fallback 或 overview commit boundary → 可 REUSE_PRIOR_PASS（记录影响分析）
R68-6      = 随 P1；R68-7 = 随 P2/P4；AD68-2 = implementation_scope #48，仅在 #68 触碰 writer ownership
             / canonical rebuild interface 时重开
```

## 8. 本地证据位置与提交

```text
/tmp/pc68-r19-work/r20-rejudge-real-raw.json   r20 verifier 对 r15 归档 raw 的只读重判（FAIL_PRODUCT/owner_input_carries_choices_scope）
/tmp/pc68-r19-work/isolation-now.json          2026-10-05 活体隔离快照（ISOLATION_CONFIRMED，PID 40721）
/tmp/pr72-r1-formal-f230616984/                r15 正式尝试官方归档（未改动）
```

## 9. 当前状态

```text
Test plan revision:      issue-68-test-plan-r20-2026-10-05
Gate 1:                  PASS + COMPLETE
Gate 2:                  G2-1/G2-2/G2-3 修正完成，候选材料已更新到 r20；等待测试审核者完整复审
                         （本记录不自行宣告 PASS/COMPLETE；Preflight executable 项按 r20 §6 如实记录为未满足）
Gate 3:                  NOT_READY（正式执行未开始）
Merge:                   NOT_READY
```
