# Issue #68 / PR #72 本地测试工程师实现记录 r19 — owner 入口隔离

记录版本：`issue68-r19-owner-local-test-impl-2026-10-05`。

本文件是**测试实现记录与 Gate 2 候选材料，不是第二关口权威结论**。它按 Test Plan r19（`issue-68-test-plan-r19-2026-10-04`，PR 评论 `5981582680`）第 10 节的指派，交付可执行的确定性测试、runtime fixture/prompt、证据提取、evaluator、正式入口与 Preflight；是否重开或通过第二关口由测试审核者决定。本记录独立包含全部当前 Recipe、parser/evaluator、Preflight 与 verdict 条件，执行者不需要拼接历史评论。

## 1. 输入与版本

```text
Requirement revision:        2026-09-29 user requirement — per-professor state at every stage
Requirement clarification:   2026-10-04 — Stage 5 owner-local data from entry
Frozen Acceptance Contract:  issue-68-gate1-r3-2026-10-04 (PASS + COMPLETE, Issue #68 评论 5981562292)
Canonical Plan revision:     issue-68-plan-r12-2026-10-04 (APPROVED, PR 评论 5981691686)
Test plan revision:          issue-68-test-plan-r19-2026-10-04 (PR 评论 5981582680)
Target repository revision:  ScholarWorkflow/professor-contact@cc44247599fd10067586626a740591dc4e0f5e31（PR #72 分支头，产品实现已完成）
本实现分支头:                pr72/test-r19@2a25ccd（基于 cc44247，6 个测试实现提交）
Supersedes (测试实现):       r15–r18 中以“完整 choices/scope 广播”为 PASS 条件的实现与 oracle
共享 fixture adapter:        skills-test-fixtures@c738fa2f8bcbb16cd99d741332d5f59b062b6357（未变）
eval-server revision:        3fdfa9387140cfc2e2aa3af415f85015f79706d2（未变，检出干净）
模型/配置:                   Project Consensus 默认（gpt-6-luna，r12 request builder，未改）
```

产品实现（`37ee473` partition、`8b9a9cb` partition 回归、`cc44247` docs）已按 Plan r12 完成；本记录覆盖的只是测试实现。

## 2. 资产清单（全部纳入本仓库版本管理）

新增（r19 当前链路）：

```text
tests/runtime/issue68-runtime-evidence-contract-r19.json   证据 contract（revision issue-68-runtime-evidence-r19-2026-10-05）
tests/runtime/run_issue68_stage5_routing_r19.py            bridge：pin base runner → r12 request builder + r19 verifier
tests/runtime/run_issue68_stage5_routing_r19_codex.py      Codex-only 正式入口（服务来源/隔离归档、单次请求）
tests/runtime/verify_issue68_stage5_routing_r19.py         evaluator（owner-local 消费 + root partition oracle）
tests/test_issue68_runtime_r19.py                          §7 反例矩阵回归 + 三通道声明
```

修改（现行资产按 r19 语义重写）：

```text
tests/runtime/prepare_issue68_stage5_routing.py            fixture：真实运行一次 stage5-partition-choices，产出 per-owner expected bundle；删除 expected_scope
tests/runtime/prompts/issue68-stage5-root.txt              prompt：root 一次 partition → one-professor bundle → owner；禁止广播
tests/test_issue68_runtime_recipe.py                       仅 fixture 断言更新为新 manifest 形状（base verifier 旧 oracle 的历史断言未动）
tests/test_issue68_stage5_local_state.py                   PROOFS 重绑（见 §3）
tests/test_issue68_root_partition.py                       +确定性重跑/行保持/owner entry 隔离 oracle、+batch 零部分提交类
tests/test_issue68_choices_attribution.py                  +discovery 只读负向 oracle（scope emission 已删）
```

历史资产（r11–r18 verifier/contract/bridge 及其测试）原样保留供审计；当前入口、本记录与 contract 均不指向它们作为现行 authority。`tests/test_verify_issue68_stage5_m1.py`、`m2`、`test_issue68_runtime_recipe.py` 中钉死 base verifier 旧 transport oracle 的测试属于历史回归，不在当前链路上。

## 3. Requirement → proof → case 映射（PC68-D1）

PC68-D1 = producer-local deterministic proof。正式入口 `tests/runtime/run_issue68_stage5_routing.py --case PC68-D1` 只发现 `TestIssue68Stage5LocalState` 的 7 个方法；`PROOFS`（`tests/test_issue68_stage5_local_state.py`）给出组件映射：

| Proof | 正式事实 | 组件 |
| --- | --- | --- |
| P1 | local pack 是唯一事实源，无 global fallback | `test_contact_state.TestStage5PerProfessorState`: t68_1 / t68_1b / t68_1c / t68_2 |
| P2 | targeted 只处理目标；未选中不阻断；X 自身错误 fail closed | 同类: t68_3 / t68_4 / unselected_malformed_noise；`test_issue68_choices_attribution.TestStage5ChoicesAttribution.test_issue68_r11_targeted_run_filters_unselected_explicit_rows` |
| P3 | one-professor batch；自身必须条件失败零部分提交 | 同类: t68_5；`test_issue68_root_partition.TestStage5BatchStaysAtomic`（batch 一封缺 humanized body → 整笔 `result_missing`、`教授研究` 全树快照零变化、无逐邮件 partial；正例对照证明只改被测条件） |
| P4 | A/B 独立 transaction；B 失败不阻止 A；A 输入不含 B（直接检查内容与 pre/post bytes） | 同类: t68_6 / validation_updates_only；`test_issue68_root_partition`: cx2（owner bundle 内容断言 B_ID/B_dir 不在 A）+ `TestStage5OwnerLocalBundleLoader.test_sibling_explicit_row_in_owner_bundle_fails_closed` |
| P5 | overview 是独立派生输出 | 同类: t68_7；`test_stage5_overview.TestStage5OverviewRebuild` 全类 |
| P6 | standalone discovery 只读；坏 B 不移除 A/C；无 scope 产物 | `test_issue68_choices_attribution.TestStage5ListInputs` 全类，含新增 `test_issue68_r19_scope_emission_is_not_supported`（`--emit-choices-scope`/`--choices-scope` 均被拒、scope 文件不创建、零写入、正常输出无 `choices_scope` 字符串） |
| P7 | root 一次确定性 partition；one-professor bundle；canonical 原样；caller 错放 sibling row fail closed | r10 attribution 7 例 + `TestStage5ImmutableWrapperOwnerLocalChoices` + `test_issue68_root_partition.TestStage5RootPartition` 全类（cx1–cx5、cx7，§7.6 caller 错放 sibling row 由 cx2 docstring 声明合并覆盖；`test_r12_partition_preserves_rows_and_reruns_deterministically`：rows 逐字段相等 + 重跑字节一致 + `--out` 等价；`test_r12_owner_bundle_has_no_scope_and_no_sibling_state_paths`：输出无 `choices_scope`、枚举对方真实文件路径逐一 NotIn、身份字节互斥）+ `TestStage5OwnerLocalBundleLoader` 全类 |

## 4. PC68-R1 Recipe（Codex supported runtime proof）

### 4.1 fixture 与 prompt

`prepare_issue68_stage5_routing.py`（由 base runner 的 `codex_host` 自动调用）：

1. 构造 A（`試験 教授`）/B（`佐藤 花子`）两个 professor-local pack（`evidence: none`、`verified: missing`）、synthetic template、噪声 legacy row（`unselected::D::I`，sentinel `noise`）、坏包 `教授研究/Z分野/无效样例/邮件输入.json`；
2. 写 `canonical-choices.json`（A/B explicit rows + sentinel `owner-0`/`owner-1`）后，用**安装的 producer CLI** 真实运行一次 `stage5-partition-choices --program-root … --choices canonical-choices.json --owner <packA> --owner <packB> --out partition-bundles.json`，保存 stdout/stderr/exit-code；断言顶层 `status=ok` 且每个 owner `partition.status=ok`、`choices_rows` 与构造行完全一致，否则 `ValueError` 终止；
3. 每个 owner 的 rows 落盘 `owner-{i}-bundle-choices.json`；plan-with-result 预检带 `--choices <该 bundle 文件>`，仍停在 `needs_refresh`（exit 2）；initial-plan（无 result 无 choices）预检停在 `needs_recheck:missing`；
4. manifest：`owners[i]` 含 `expected_choices_rows`、`expected_bundle_file`、`sibling_exclusions`（sibling pack 路径/professor_dir/email_id/sentinel/字面量 `choices_scope`）；顶层 `partition.owners` 记录期望 partition 输出；无 `expected_scope`；`pre_run_hashes`、`manual_patch: "no"` 保留。

prompt（`prompts/issue68-stage5-root.txt`）要求 root：discovery → 在委派任何 owner 前用受支持确定性 partition 入口对 raw multi-professor choices 恰好 partition 一次 → 每 owner 只拿自己的 bundle；业务输入为 `{email_pack, choices, mode, template, result}`（choices 仅本 owner rows）；禁止转发 raw 多教授 choices、跨教授 scope、sibling 数据，禁止模型自行拆分。验证边界与 raw_results 说明不变。

### 4.2 正式入口

```bash
python3 tests/runtime/run_issue68_stage5_routing_r19_codex.py \
  --producer-root <clean producer checkout at the executed PR head> \
  --producer-sha  <执行时的 PR head SHA> \
  --fixture-root  <skills-test-fixtures clean checkout> \
  --fixture-sha   c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root /Users/rekidunois/code/skill-repos-dev/eval-server \
  --output-dir    <空目录>
```

单次正式请求，不重试；请求经 r12 builder（gpt-6-luna）发往共享 eval 服务；前后各归档一次服务来源（`direnv` 缺失时回退到唯一通过冻结检出校验的 `eval_server.py` 监听者）与存储隔离，前后不一致 → `INVALID_TEST_EXECUTION/eval_service_changed_during_execution`。

### 4.3 evaluator 判定条件（`verify_issue68_stage5_routing_r19.py`）

前提门：adapter 状态、formal children 恰 2（`sender_thread_id` 归属，诊断字段只作 `identity_diagnostics`）、`runtime_seq` 严格递增、`terminal_precedence`（FAIL → INVALID → BLOCKED）、`termination_reason=completed`。root 最终业务结果 = 唯一当前 root/当前 turn `final_answer`（r13 selector）；单层包装（top-level list、`{"results":[…]}` 或恰一键的 list 包装）可解析，嵌套诊断不递归。

每 child 消费判定（顺序即判定顺序）：

| 条件 | 终态 / reason |
| --- | --- |
| 消费面 = child 命令文本同时引用 `contact_state.py` 与任一 stage5 动作词；对象以 JSON 或 Python 字面量内嵌 | （识别规则） |
| >1 个不同可归属对象 | `INVALID_EVIDENCE / owner_business_object_ambiguous` |
| 有消费面但 0 对象 | `BLOCKED_OBSERVABILITY / owner_business_object_unobservable` |
| 无消费面且无明文 user message 兜底 | `BLOCKED_OBSERVABILITY / completed_user_payload_unobservable` |
| `email_pack` 非本次 owner | `FAIL_PRODUCT / unexpected_owner_pack` |
| 对象含 `choices_scope` 键 | `FAIL_PRODUCT / owner_input_carries_choices_scope` |
| 缺 `choices` | `FAIL_PRODUCT / choices_transport_missing` |
| rows ≠ manifest per-owner expected（解析后精确相等；`試験`→`试验` 在此判失败） | `FAIL_PRODUCT / owner_bundle_choices_changed` |
| 序列化对象含任一 sibling marker | `FAIL_PRODUCT / owner_input_contains_sibling_data` |
| 带 `email_id` 但不属于本 owner | `FAIL_PRODUCT / owner_target_mismatch` |

root 编排判定：discovery 输出恰为 `{A ok, B ok, invalid_pack error}`（严格解析的 discovery 带 `--emit-choices-scope` → `discovery_emits_choices_scope`）；root 恰一次成功 `stage5-partition-choices`，输出与 manifest `partition.owners` 一致（0 次 → `root_partition_not_deterministic`，>1 → `multiple_root_partitions`，rows 不符 → `root_partition_changed`，child 执行 → `partition_executed_by_owner`）；严格解析的 plan 不得带 `--choices-scope`（`owner_plan_carries_choices_scope`）、`--email-pack` 必须等于归属 pack、`--choices` 文件 rows 必须等于 expected；wait/consume：`collabAgentToolCall wait` 的 `agentsStates` 配对优先，字段为空时按同一 run 的 root `subAgentActivity kind=completed` + `agentThreadId` 配对（两面皆无 → `completion_or_wait_unobservable`），wait 点早于 child `turn/completed` → `wait_precedes_owner_completion`；`stage5-rebuild-overview` ≤1 且晚于全部 owner 等待点；root 终局行每 owner 恰一个一致 outcome 且等于消费 outcome（`root_consumed_results_conflict` / `root_changed_owner_result` / `root_consumed_result_unobservable`）。复合命令（`python3 -c` 包装）不提供 flags，flag 级检查仅覆盖严格解析调用；root 复合文本出现 ≥2 个动作词 → `BLOCKED_OBSERVABILITY/root_orchestration_ambiguous`。

### 4.4 判定终态（Test Plan r19 §6）

`FAIL_PRODUCT` 仅用于机器证据证明 producer 违反冻结 contract（上表）；`BLOCKED_OBSERVABILITY` 用于正式入口/runtime/受支持观察条件缺失；`INVALID_EVIDENCE` 用于证据损坏、歧义或归属不可唯一；未执行或身份不可证 → `NOT TESTED` / `CASE_NOT_STARTED`。

## 5. Preflight（Test Plan r19 §5；不提前执行完整 PC68-R1）

```text
Recipe Preflight（2026-10-05）
- executable: supported — 正式入口/bridge/verifier 导入并通过 --help；contract 绑定由回归断言；
  共享 eval 服务实况 = r15 归档 provenance 同一实例（PID 40721，端口 17902，启动 2026-10-03 19:04:39，
  cwd = 冻结检出 3fdfa938，检出干净）；direnv 在当前环境缺失，r19 入口已带"唯一冻结监听者"回退并经活体
  验证返回 17902（端口来源记入 provenance）。
- isolated: supported — 活体快照 /tmp/pc68-r19-work/isolation-now.json：CODEX_HOME=/private/tmp/test-codex-home
  （≠ ~/.codex），config.sqlite_home 与 log_dir 均在测试 CODEX_HOME 内 → ISOLATION_CONFIRMED；与 r15 归档
  隔离记录同一实例；正式入口保留输出目录非空拒绝、overlaps 检查与前后隔离归档。
- observable: characterized — r15 归档（830 events，2 formal children）证明：child commandExecution 携带
  明文 packet（含 python -c 复合形状）、root discovery/partition 输出在 aggregatedOutput、child
  turn/completed 与 root subAgentActivity completed（agentThreadId 配对）可观察、root final_answer 经
  r13 selector 可选（r18 实现性重判已得出 verdict）。缺口与处置：wait 事件的 receiverThreadIds/agentsStates
  在真实运行中为空 → 增补 subAgentActivity 回退面；真实 child/root 命令多为复合表达式 → 消费面/编排面按
  "CLI+动作词"识别并对复合唯一动作词取 aggregatedOutput。两处修改都保持冻结事实不变，复核点见 §8。
- Discriminating: supported — 判定程序验证依据：r19 回归 33 项（synthetic，含 §3.2.2 三通道显式声明与互洽断言）：
  有效 owner-local 运行 → PASS；child 消费 sibling sentinel/choices_scope/rows 改写 → FAIL_PRODUCT；
  消费证据缺失 → BLOCKED；歧义 → INVALID；无执行/证据不可读 → 对应终态。
  另有真实数据负例：r15 归档 raw 经 r19 verifier 只读重判 → FAIL_PRODUCT/owner_input_carries_choices_scope
  （/tmp/pc68-r19-work/r19-rejudge-real-raw.json；旧设计运行被正确拒绝，而不是误判 PASS 或阻断）。
- critical assumption gap: none identified（复核点见 §8）
```

r13 capability 证据（`pr72-r13-preflight-exec-2026-10-04`）按 contract `capability_reuse_rule` 复用：r19 未改 request builder、模型、final-source selector、fixture adapter 与 eval-server revision。

## 6. 回归证据（Python 3.14.6，uv-managed CPython）

```text
2026-10-05，本实现分支头 2a25ccd：
test_issue68_stage5_local_state + choices_attribution + root_partition   33 tests OK（PC68-D1 资产）
test_issue68_runtime_r19                                                 33 tests OK（§7 反例矩阵 + 三通道 + 双端口路径）
test_issue68_runtime_r18/r12/r12_codex/r13/r14/recipe/r11_bridge/m1/m2   全部 OK（历史链路未破坏）
全量 discover -s tests -p 'test_*.py'：Ran 973 tests, FAILED (failures=5)
  5 个失败 = test_issue32_e2e_verifier ×2、test_issue32_eval_request ×2、test_issue57_runtime_assets ×1；
  同样 5 个失败在基线 cc44247 干净检出上复现（pr72-p1 worktree 验证）→ 全量回归判定语义 = REGRESSION_DELTA
  （基线 cc44247，比较字段 = 测试标识 + 失败类型），本次改动零新增回归；基线既有失败不属本议题范围。
```

## 7. 禁止副作用检查 → oracle 映射（Test Plan r19 §8）

| 禁止副作用 | 直接检查 |
| --- | --- |
| A case 不修改 B pack/state/verify/render | P4 t68_6 快照；cx2/owner-entry 隔离测试（真实文件路径枚举 NotIn） |
| standalone discovery 零正式写入 | `TestStage5ListInputs` research_files 快照 + `test_issue68_r19_scope_emission_is_not_supported` |
| 不创建 global email pack 或跨教授 `choices_scope` | partition 输出无 `choices_scope`；`--emit-choices-scope`/`--choices-scope` 负向 oracle；runtime `owner_input_carries_choices_scope` / `discovery_emits_choices_scope` / `owner_plan_carries_choices_scope` |
| overview 未到顺序不写 | `aggregate_precedes_result_consumption`、`multiple_aggregate_rebuilds`、`owner_rebuilds_aggregate` |
| failed owner 不回滚成功 sibling | t68_6、cx5、runtime `wait_precedes_owner_completion`/outcome oracle |

## 8. 交测试审核者复核的实现决定（不改变冻结事实）

1. **wait/consume 归属面**：`collabAgentToolCall.agentsStates` 配对优先，为空时用同一 run 的 root `subAgentActivity(kind=completed, agentThreadId)` + child `turn/completed`。依据：r15 归档中配对字段为空（r18 记录 §7.1 已列为未决事项）；两面皆无才 `completion_or_wait_unobservable`。
2. **消费面与编排面的复合命令容错**：真实运行中 child/root 常用 `python3 -c`/包装器；消费面按"CLI + 动作词"识别（不解析 flags），root 编排对复合唯一动作词取 `aggregatedOutput` 判定，flag 级检查只覆盖严格解析调用。诊断对象排除规则（§7-3）由"非业务命令不进消费面"实现；若诊断对象与真实消费同现于同一条业务命令，机器归属不可唯一 → `INVALID`。
3. **`resolve_eval_port` 回退**：direnv 缺失时用唯一通过冻结检出校验的监听者；共识的 direnv 仍为首选来源。
4. **历史 oracle 的归属**：base verifier 的 `business_payload`/`runtime_checks`（r11/r15 transport oracle）与 m1/m2/recipe 中相应断言保留为历史回归，当前链路不调用；`test_issue68_runtime_recipe.py` 中 fixture 相关断言已更新为新 manifest 形状。
5. **基线既有失败**：issue 32/57 的 5 个资产清单测试在基线 cc44247 已失败，非本次引入，未修复（超出本议题范围）。
6. **contract 键名**：r19 contract 保留 `business_payload` 键名，但其内容仅为 per-owner packet 的五个业务字段名（`email_pack/choices/mode/template/result`，无 scope、无广播含义）；verifier 与入口均不消费该键。如审核者认为键名易误导，可在 Gate 2 修订中更名（属记录格式变更，不影响判定）。

## 9. 复验依赖（Test Plan r19 §9 执行决定建议）

```text
P4, P6, P7 = EXECUTE_CURRENT（映射与组件已按 r19 重绑，当前版本必须执行）
P3 = EXECUTE_CURRENT（新增 TestStage5BatchStaysAtomic 零部分提交组件）
P2 = 按 Gate 3 时最终 diff 判定：本实现未改 targeted/batch loader 的组件映射；产品 diff（37ee473）已改
     stage5_choices_by_id 调用链 → 建议 EXECUTE_CURRENT
P1, P5 = 可 REUSE_PRIOR_PASS，仅当最终 diff 未触及其 declared behavior/dependency path/oracle；
         不能仅因旧版曾通过自动复用
PC68-R1 = EXECUTE_CURRENT（Gate 2 PASS + COMPLETE 后，按 §4.2 Recipe 执行一次，不重试）
```

## 10. 本地证据位置与状态

```text
/tmp/pc68-r19-work/r19-rejudge-real-raw.json   r19 verifier 对 r15 归档 raw 的只读重判（FAIL_PRODUCT/owner_input_carries_choices_scope）
/tmp/pc68-r19-work/r19-rejudge-manifest.json   由归档 manifest + canonical-choices 只读构造的 r19 schema manifest
/tmp/pc68-r19-work/isolation-now.json          2026-10-05 活体隔离快照（ISOLATION_CONFIRMED，PID 40721）
/tmp/pr72-r1-formal-f230616984/                r15 正式尝试官方归档（未改动）
```

## 11. 当前状态

```text
Test plan revision:      issue-68-test-plan-r19-2026-10-04
Gate 1:                  PASS + COMPLETE
Gate 2:                  候选材料齐备，等待测试审核者完整复审（本记录不自行宣告 PASS/COMPLETE）
Gate 3:                  NOT_READY（PC68-R1 未执行；PC68-D1 未按本 Recipe 正式执行）
Merge:                   NOT_READY
```
