# Issue 66 本地测试候选记录

## 计划与候选身份

本记录唯一执行依据是 PR #73 评论 [5991701404](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5991701404) 所附完整计划 `issue-66-test-plan-r19-clarification-r4-2026-10-05`，逐项落实其中第 2–9 节的完整测试、预检、复验和历史要求。审核评论 [6009197999](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-6009197999) 只用于定位该完整计划要求修复的八类测试问题，不替代完整计划。

| 项目 | 固定值或取值方式 |
| --- | --- |
| 仓库 | `ScholarWorkflow/professor-contact` |
| PR 分支 | `codex/issue-66-stage3-per-professor` |
| 产品目标提交 | `dfe430560b6e4d9d85c30b71b8c84bc621da7549` |
| PR 基线 | `03dfd501f5212c86356409f7e011f676384f2633` |
| 夹具树 | `c738fa2f8bcbb16cd99d741332d5f59b062b6357` |
| 适配约定 | `skills-test-fixtures/codex-eval-adapter@16` |
| 测试提交 | 每次运行时执行 `git rev-parse HEAD`，写入该轮证据；不在计划中伪填提交号 |
| 本地运行器 | [issue-66-run.sh](issue-66-run.sh)，修订标记 `issue-66-local-candidate-runner-r19-2026-10-06` |
| 任务辅助脚本 | `.tmp_scripts/2026-10-06_watch_pr73.sh` 保留在工作树；只排除此单一文件，不计入候选摘要 |

候选输入摘要在运行时对运行器固定清单逐文件计算，再对清单计算 SHA-256。运行器在套件前后各算一次；不把摘要写回本记录或运行器。每条命令的完整标准输出、标准错误、退出码和实际命令保存在唯一临时证据目录。每条样例在 `samples.tsv` 保存候选摘要、测试状态、动态源码位置及原始日志指针；判定器样例还关联真实 JSONL 返回、判定器摘要、事件摘要及事件引用。测试提交号和产品目标号分开记录。

固定本地环境为 `uv 0.12.11` 与 Python `3.14.6`，解释器通过 `uv run --no-project --python 3.14.6` 选择，缓存目录为 `/private/tmp/issue66-uv-cache`。运行器捕获实际 `uv`、Python、Bash、`jq`、操作系统、Codex CLI、OpenCode 及可用时的 `shellcheck` 版本。它先核对仓库根、远端、目标提交祖先关系、产品源相对产品目标无差异、工作树变更范围、候选文件摘要和工具版本；测试前后均重新计算候选摘要。

当前字段解析使用 `jq 1.8.2`，安装配置使用 `yq 4.53.3`。结构化运行直接依赖固定文件 `.apm/skills/professor-contact/tests/runtime/issue66_suite_result.py`、`.apm/skills/professor-contact/tests/runtime/issue66_suite_classify.jq` 和回归文件 `.apm/skills/professor-contact/tests/test_issue66_suite_result.py`；三者均纳入候选摘要，不依赖测试日志排版。

## R4 第 2 节完整证明对应

下表覆盖 R4 第 2 节列出的全部要求和用例；本轮复验受影响的确定性用例并准备安装与执行接线，不新增模型隔离运行。精确目标提交的真实 APM 安装已执行；正式评测及服务、存储归属尚未核实。安装、输入及请求预检无需第二关口批准。

| 要求 | 负责用例 | 本轮负责的事实及实际调用链 | 测试、程序与证据来源 |
| --- | --- | --- | --- |
| `REQ66-P1/P2`、`R66-1` | `S3-ISO-1` | `cmd_stage3_plan` → `cmd_stage3_finalize`；凭据入口共享同一教授调用凭据。另有 `cmd_stage3_prepare_validation` → `cmd_stage3_save_validation` → `cmd_stage3_record_validation` 的交接入口。要求本教授事实可推进，不把其他教授状态、程序总览或共享登记当成本地成功前提。 | `test_issue66_stage3_local_state.py::test_s3_iso_1_local_finalize_isolation`、`::test_s3_iso_1_b_anomalies_via_credential_entry`；凭据入口隔离测试；`SKILL.md` 与 idea-generator 指令的本地事实边界；Codex 安装投影在代理约定测试中按安装格式序列化后复核同一正文。 |
| `R66-2` | `S3-ISO-4` | 普通入口与凭据入口均检查候选稿安装、状态提交、提交前恢复和提交后清理失败处理。 | `test_s3_iso_4_commit_marker`、`test_s3_iso_4_commit_marker_via_credential_entry`；临时文件字节与真实替换操作由本地状态测试记录。 |
| `R66-3` | `S3-ISO-3` | 人工改动当前教授受管稿件时，提交拒绝并保留人工原文。 | `test_s3_iso_3_local_manual_conflict`、`test_s3_iso_3_manual_conflict_via_credential_entry`；调用前后同一文件字节。 |
| `R66-4/5` | `S3-ISO-5` | 检查规范目录身份、派生状态、排序与程序总览重建。 | `test_s3_iso_5_aggregate_identity_derivation`；历史中未受影响的其他证明保留历史来源。 |
| `R66-7/8` | `S3-ISO-6` | 总览失败不回滚教授本地事实；旧身份迁移保持精确。 | `test_s3_iso_6_rebuild_failure_legacy`；拒绝及失败分支比较同一教授状态字节。 |
| `R66-6/9` | `S3-ISO-7` | 共享登记独立；第四阶段只读取明确教授目录事实。 | `test_s3_iso_7_registry_stage4_source`；读取路径和输入来自固定本地夹具。 |
| `REQ66-P3` | `S3-DEP-1` | 第 48 号及程序根锁不是本地提交前提。 | `test_s3_dep_1_no_issue48_lock_dependency`；静态源及确定性入口测试。 |
| `COMP66-1` | `S3-COMP-1` | 候选结构、编号、顺序、引用、指纹、校验沿用；凭据入口也覆盖提交。 | `test_s3_comp_1_preserved_candidate_contract`、`test_s3_comp_1_preserved_contract_via_credential_entry`；结果对象逐字段比较。 |
| `R66-10 / COMP66-1` | `S3-CREDENTIAL-1` | 首轮捕获返回值与后续同一凭据消费；非法凭据和来源漂移在写入前拒绝。 | `test_issue66_runtime_judge.py` 中凭据样例；`test_issue66_invocation_credential.py` 的入口调用、实际返回值与文件观察。 |
| `R66-10 / COMP66-1` | `S3-CORRECTION-1` | 修正集合由已记录问题决定；直接观察实际结果文件读取、返回集合、替换集合及未改校验记录。 | `test_exact_result_read_set_rejects_an_extra_open`、`test_named_group_is_replaced_and_sibling_group_is_kept`；`OpenRecorder` 转发打开调用，正负对照都实际打开文件。 |
| `R66-10` | `S3-HANDOFF-1` | 准备、保存、记录三入口绑定原文和轮次；拒绝无副作用；批量归属及两轮终态。 | `test_issue66_validation_handoff.py` 全套与判定器保存/记录样例；调用窗口内操作记录、同集合字节快照、产品真实返回。 |
| `R66-10` | `S3-ASSET-COMPAT-1` | 源技能及代理说明保持有限写权限、未指定输出只读、批量交接字段和各自运行时职责。 | `test_stage3_idea_generator_agent_contract.py`；Codex 正文按 TOML 投影方式解码；当前代理约定套件保留三项已知产品行为失败。 |
| `R66-10 / COMP66-1` | `S3-RT-CODEX-1` | 正式安装后原生委派、实际凭据消费、校验者产文、根保存记录、权限、顺序、停止和一次终态重建。 | 需要已批准 Gate 2、正式安装与 `/eval` 原始事件；本轮禁止并未执行正式评测，不给此用例判 `PASS`。 |

`S3-ISO-1` 的范围检查只验证已指定本教授输入；不要求读取乙的业务正文，也不增加共享前置检查或持续监视。产品调用位置：`.apm/skills/professor-contact/scripts/contact_state.py` 中 `cmd_stage3_plan`、`cmd_stage3_finalize`、`cmd_stage3_prepare_validation`、`cmd_stage3_save_validation`、`cmd_stage3_record_validation`。说明来源：`.apm/skills/professor-contact/SKILL.md` 的 Stage 3 固定状态转移，以及 `.apm/agents/professor-contact-idea-generator.agent.md` 的 Stage 3 输入与运行时分支。代理约定测试从同一 Markdown 正文生成 Codex TOML 投影并核对教授边界；这不是实际干净安装或 Gate 3 运行的证据。

## 八项测试侧修订

| 修订 | 本地确定性证明及证据来源 |
| --- | --- |
| 1. 正式归属 | `test_issue66_runtime_judge.py` 中 `test_one_round_pass`、`test_named_root_call_with_confirmed_zero_children_fails`、`test_extra_off_root_formal_relation_fails`、`test_nested_foreign_relation_is_product_failure`、`test_conflicting_formal_owners_for_child_are_invalid`。运行时 JSONL 保留独立预期与实际分类；正式根关系不存在、根外关系和冲突分别按计划分类。 |
| 2. 实际返回值绑定 | `test_consumption_uses_actual_capture_return_path_and_digest`、`test_committed_profile_fingerprint_must_match_capture`、`test_damaged_version_digest_and_ownership_fail_before_writes`、`test_credential_return_bound_to_another_professor_fails`、`test_source_metadata_drift_fails`、`test_missing_first_commit_fails`、`test_handoff_value_drift_fails`、`test_prepare_return_for_another_round_fails`。判定器把实际捕获的资料指纹与提交状态绑定；产品入口测试还逐字节核对原始资料、凭据和提交状态中的指纹。 |
| 3. 原始正文与同一字节缓冲区 | `test_legal_whitespace_message_passes`、`test_root_reconstruction_fails`、`test_second_business_message_fails`、`test_complete_run_with_no_validator_production_fails`，以及 `test_issue66_validation_handoff.py::RecordHandoffTests.test_record_parses_the_same_buffer_that_was_digest_checked`。最后一项在摘要校验后将源文件替换为另一份合法 JSON，断言摘要及记录状态来自首次读取的字节。 |
| 4. 有限写权限 | `test_compound_legal_read_and_single_exclusive_output_write_passes`、`test_outside_output_write_fails`、`test_python_command_with_multiple_write_targets_fails`、`test_same_byte_write_then_restore_still_fails_write_scope`、`test_overwrite_existing_candidate_source_fails_write_scope`、`test_pure_unknown_command_is_an_evidence_gap`、`test_file_change_protocol_shape_bytes_lifecycle_delete_and_move_target`。合成事件证明判定器分类；它们不冒充正式运行的系统写入跟踪。 |
| 5. 顺序、停止和重建 | `test_machine_failure_prefix_blocks`、`test_failed_prepare_write_and_record_stop_dependent_actions`、`test_failed_save_return_cannot_be_followed_by_record_as_pass`、`test_unsuccessful_capture_return_cannot_bind_credentials`、`test_correction_dispatch_between_record_start_and_completion_fails`、`test_machine_failure_prefix_does_not_hide_prior_product_failure`、`test_unrecognized_failure_text_does_not_hide_zero_child_failure`、`test_rebuild_before_record_fails`、`test_rebuild_started_before_terminal_record_completed_fails`、`test_terminal_round_bookkeeping_fails`、`test_rebuild_without_completion_is_an_evidence_gap`。新增负例分别让准备、验证输出写入、记录失败后仍继续派发、保存或重建；三次实际判定调用均留在 JSONL。 |
| 6. 拒绝副作用 | 凭据入口 `test_credential_rejection_preserves_the_full_committed_artifact_set`；准备、保存和记录入口 `test_prepare_save_and_record_refusals_preserve_the_same_artifact_set`。两项直接比较同一受保护文件集合的调用前后存在性与字节。 |
| 7. 读取集合与沿用 | `test_exact_result_read_set_rejects_an_extra_open` 保存独立预期读取集、真实打开记录、额外打开负例和未变哨兵；`test_named_group_is_replaced_and_sibling_group_is_kept` 检查 `dir_C` 原校验记录保留及删除记录负控。 |
| 8. 固定执行材料 | 运行器固定套件顺序和命令、记录版本及每条退出码；judge 套件保存每次真实判定调用 JSONL；样例表将计划样例映射到真实判定器返回或明确标成直接断言。正式评测门槛见下文。 |

`fileChange` 按 R4 指定的 `codex-cli 0.159.0-alpha.12.1` 核对协议和实现：[App Server JSON 架构](https://github.com/openai/codex/blob/rust-v0.159.0-alpha.12.1/codex-rs/app-server-protocol/schema/json/v2/ThreadStartResponse.json#L528-L545)规定每项 `diff` 是必需字符串、`kind` 是对象；[类型架构](https://github.com/openai/codex/blob/rust-v0.159.0-alpha.12.1/codex-rs/app-server-protocol/schema/json/v2/ThreadStartResponse.json#L1005-L1061)规定 `kind.type` 为 `add`、`delete` 或 `update`，Update 可带 `move_path`。同一版本的[事件投影源码](https://github.com/openai/codex/blob/rust-v0.159.0-alpha.12.1/codex-rs/app-server-protocol/src/protocol/item_builders.rs#L329-L364)显示 Add 的 `diff` 是原内容、Update 的 `diff` 是统一差异；[补丁增加文件源码](https://github.com/openai/codex/blob/rust-v0.159.0-alpha.12.1/codex-rs/apply-patch/src/lib.rs#L474-L500)显示 Add 会先读取目标原内容，再写入新内容，所以 Add 事件本身不能证明目标此前不存在，也不能证明排他创建。判定器必须把这种独占性记为证据缺口，不能当作合法排他写入；[补丁移动源码](https://github.com/openai/codex/blob/rust-v0.159.0-alpha.12.1/codex-rs/apply-patch/src/lib.rs#L562-L682)显示移动会写目标并移除原路径。锁定版本的[真实事件测试](https://github.com/openai/codex/blob/rust-v0.159.0-alpha.12.1/codex-rs/app-server/tests/suite/v2/thread_resume.rs#L5355-L5377)展示 `fileChange` 有 `item/started` 和后续完成事件；判定器须按线程、轮次及项目编号关联开始与成功完成，并校验两边的变更项。`codex exec --json` 是另一种格式，其文件变更只有路径和字符串类型，没有 `diff` 或 `move_path`，见[命令行事件源码](https://github.com/openai/codex/blob/rust-v0.159.0-alpha.12.1/codex-rs/exec/src/exec_events.rs#L156-L184)；本地判定器只按计划要求的 `app_server_events` 处理。相同语义也核对了当前本机报告的 `codex-cli 0.160.1` 对应标签源码；本机版本不证明评测服务实际运行版本。

## 固定命令和套件顺序

从任意目录执行 `bash /仓库绝对路径/test-plan/issue-66-run.sh local`。运行器先记录调用时目录，再切换到脚本所属的仓库根目录；仅接受 `local`，任何其他参数在临时证据目录之外拒绝，退出码为 64。该本地脚本不含正式评测执行分支；完整待审安装、取证及正式接线见同一候选的 [固定执行材料](issue-66-execution.md) 与 `issue-66-formal.sh`。正式分支仅在当前完整测试提交获得第二关口批准并冻结后解锁，必要预检不以批准为前提。

每套件运行同一形式的命令：

```sh
uv run --no-project --python 3.14.6 python -B \
  .apm/skills/professor-contact/tests/runtime/issue66_suite_result.py \
  --directory .apm/skills/professor-contact/tests --pattern '<文件名>' \
  --report '<本轮独占证据目录中的套件报告.json>'
```

| 顺序 | 测试文件 | 预期条目数 | 本地候选期望 |
| --- | --- | ---: | --- |
| 1 | `test_issue66_runtime_judge.py` | 109 | 全部通过；122 次真实判定调用写入 `judge-samples.jsonl` |
| 2 | `test_issue66_execution_wiring.py` | 10 | 请求构造、快照、历史保留、正式归属及独立安装预检接线全部通过；不代替真实环境预检 |
| 3 | `test_issue66_suite_result.py` | 5 | 结构化回调、失败身份及解析拒绝全部通过 |
| 4 | `test_issue66_invocation_credential.py` | 17 | 全部通过 |
| 5 | `test_issue66_stage3_local_state.py` | 12 | 全部通过 |
| 6 | `test_issue66_validation_handoff.py` | 22 | 21 项通过；保留一个已知产品失败 |
| 7 | `test_stage3_idea_generator_agent_contract.py` | 9 个方法 | 其余断言通过；保留三个已知子测试失败 |

第 6 套件失败身份由结构化回调的 `test_id` 精确匹配 `test_issue66_validation_handoff.PrepareHandoffTests.test_new_invocation_can_prepare_round_one_after_prior_terminal_validation`，`status=failure`，行为断言标识为 `validation_handoff_collision`。

第 7 套件失败必须属于同一方法 `test_opencode_example_and_common_closeout_follow_skill_handoff_chain`，三个失败事件的 `params.section` 分别为 `OpenCode 示例`、`共同收尾`、`禁止旧直接记录方式`。运行器通过 `runtime/issue66_suite_result.py` 的测试回调保存 JSON，由 `runtime/issue66_suite_classify.jq` 解析方法身份、事件类型、参数及计数，不凭日志排版、关键词或仅失败总数判断。完整日志仍原样保存；保留当前产品失败断言。

执行中若条目数、退出码、失败身份、记录结构、样例映射或前后候选摘要任一不符，整轮记录为 `INVALID_TEST_EXECUTION`。确定性套件按记录如实为已知产品失败且所有执行证据有效时，候选整体为 `FAIL`。这两类本地结果都不是正式评测结论。

## 本轮实际执行结果

| 项目 | 实际结果 |
| --- | --- |
| 运行器 | `issue-66-local-candidate-runner-r19-2026-10-06`；证据目录 `issue66-gate2-candidate.iTkWhAuh`，退出 1，`runner_execution=COMPLETE`。 |
| 本轮定位 | 每轮测试提交、候选 SHA-256 和唯一证据目录由运行器写入该轮 `metadata.txt`；本记录不内嵌自身摘要或运行目录。 |
| 七套件结果 | 判定器 109、接线 10、结构化记录 5、凭据 17、本地状态 12 项全部通过；交接 22 项含 1 个产品失败，代理约定 9 个方法含 3 个产品失败子测试。实际 JSON 与退出码均保留。 |
| 失败身份 | `test_new_invocation_can_prepare_round_one_after_prior_terminal_validation`；以及 `test_opencode_example_and_common_closeout_follow_skill_handoff_chain` 的 `OpenCode 示例`、`共同收尾`、`禁止旧直接记录方式` 三个子测试。 |
| 判定记录 | 122 条真实调用、245 条独立断言，其中 233 条判定相关断言。分类预期 118 条明确、4 条局部；事实预期 97 条明确、1 条部分、24 条未单独检查。实际返回分布为 `PASS=12`、`FAIL=59`、`INVALID_TEST_EXECUTION=48`、`BLOCKED=3`；负例正确拒绝属于自测通过。 |
| 账本 | 60 行、24 列，无空字段，方法状态全部有效；`sample_ledger_status=VALID_JUDGE_AND_DIRECT_ASSERTION_RECORDS_60_SAMPLES_24_COLUMNS`。判定诊断为 `[]`，账本校验为 `true`、退出 0。 |
| 总结 | 当前运行整体 `FAIL`，执行及账本有效；失败来自以上两类产品问题。正式评测未运行。 |

每条实际命令、标准输出、标准错误、退出码、原始判定返回、事件摘要、样例行及候选摘要均保存在运行器创建的唯一目录。该目录的原始材料只追加保留，不由本记录改写。

本次最后填报只修改两份说明，不修改测试程序、样例或产品。复用 `iTkWhAuh` 中七套件结构化结果、实际程序文件哈希与账本检查；该轮摘要仅绑定填报前的候选，不能当作填报后摘要。最终候选由顶层另生成全文件摘要清单冻结；本记录不写入自身最终摘要，避免自引用。

## 第五节样例账本映射

运行器生成 60 行 `samples.tsv`。本地样例编号只用于账本定位；每行记录独立预期、观察值、判定依据、计划族、源码方法的动态行号和最小原始证据指针。A–F、I 关联真实判定 JSONL；G、H 及 D5–D7 用 `direct-assertion`，观察状态写作 `assertion-matched`，不伪称判定器结果。计划族与采集器 `sample_family` 分列，不要求两套名称相同。

| 族与数量 | 逐样例测试映射 |
| --- | --- |
| A，3 | A1 `test_one_round_pass`；A2 `test_corrected_two_round_pass`；A3 `test_two_round_exhaustion_is_a_legal_pass`。 |
| B，7 | B1 `test_consumption_uses_actual_capture_return_path_and_digest`；B2 `test_credential_return_bound_to_another_professor_fails`；B3 `test_source_metadata_drift_fails`；B4 `test_missing_first_commit_fails`；B5 `test_handoff_value_drift_fails`；B6 `test_prepare_return_for_another_round_fails`；B7 `test_committed_profile_fingerprint_must_match_capture`。 |
| C，5 | C1 `test_one_round_pass`；C2 `test_named_root_call_with_confirmed_zero_children_fails`；C3 `test_nested_foreign_relation_is_product_failure`；C4 `test_conflicting_formal_owners_for_child_are_invalid`；C5 `test_extra_off_root_formal_relation_fails`。C1 与 A1 共用同一个真实调用记录，并在两行分别保留计划样例身份。 |
| D，7 | D1 `test_legal_whitespace_message_passes`；D2 `test_root_reconstruction_fails`；D3 `test_second_business_message_fails`；D4 `test_complete_run_with_no_validator_production_fails`；D5 `RecordHandoffTests.test_record_parses_the_same_buffer_that_was_digest_checked`；D6 `test_file_change_add_diff_preserves_utf8_and_line_endings` 检查真实对象形 `kind` 下，Unicode、CRLF/LF 及有无尾换行均按原字节保留；D7 `test_file_change_protocol_shape_bytes_lifecycle_delete_and_move_target` 检查缺失或非字符串 `diff`、开始/成功完成配对、增加/更新/删除、Add 不能证明排他创建、Update 差异不能证明结果字节、移动目标范围、伪造字段无效及未知类型缺口。 |
| E，8 | E1 `test_compound_legal_read_and_single_exclusive_output_write_passes`；E2 `test_python_command_with_multiple_write_targets_fails`；E3 `test_same_byte_write_then_restore_still_fails_write_scope`；E4 `test_overwrite_existing_candidate_source_fails_write_scope`；E5 `test_outside_output_write_fails`；E6–E8 `test_pure_unknown_command_is_an_evidence_gap` 的未知命令、未调用函数内写操作、不可达分支写操作。后三者都把权限结论留作证据缺口。 |
| F，11 | F1 `test_machine_failure_prefix_blocks`；F2 `test_correction_dispatch_between_record_start_and_completion_fails`；F3 `test_machine_failure_prefix_does_not_hide_prior_product_failure`；F4 `test_rebuild_started_before_terminal_record_completed_fails`；F5 `test_rebuild_without_completion_is_an_evidence_gap`；F6 `test_terminal_round_bookkeeping_fails`；F7 `test_unrecognized_failure_text_does_not_hide_zero_child_failure`；F8–F10 `test_failed_prepare_write_and_record_stop_dependent_actions` 的准备失败、验证写入失败和记录失败三种调用；F11 `test_machine_failure_prefix_does_not_hide_prior_product_failure` 的正式归属冲突仍保留先前已证实的提前重建产品失败。 |
| G，2 | G1 `test_credential_rejection_preserves_the_full_committed_artifact_set`；G2 `test_prepare_save_and_record_refusals_preserve_the_same_artifact_set`。 |
| H，4 | H1、H2 `test_exact_result_read_set_rejects_an_extra_open`；H3、H4 `test_named_group_is_replaced_and_sibling_group_is_kept`。每对分别保存正例与负控观察。 |
| I，13 | I1–I6 `test_required_install_sample_storage_and_snapshot_evidence_cannot_be_omitted` 的 `missing=install,fixture,storage,pre,post,routing` 六个调用，按真实调用序号 1–6；I7 `test_truncated_record_output_is_invalid`；I8 `test_unsupported_message_shape_is_invalid`；I9 `test_non_monotonic_event_seq_invalidates_validator_evidence`；I10 `test_mismatched_call_id_cannot_bind_validator_command_completion`；I11 `test_mixed_evidence_set_ids_are_invalid`；I12–I13 同一方法直接调用 `judge.main()`，分别证明顶层评测响应缺失和截断都返回结构化 `INVALID_TEST_EXECUTION`，并把 `F-test-program`、`F-evidence-input` 记为无效。 |

judge JSONL 采用 `issue66.sample-ledger.v1`；当前采集为 122 条真实判定调用、唯一 `sample_id=test_id#run-N`，保存 245 条独立断言，其中 233 条与判定结果关联。每条保留独立断言、真实返回、判定器摘要、夹具摘要、源码调用位置、完整 `raw_app_server_events`、事件数量和事件索引引用。运行器逐条解析原始事件，核对数组长度，以及每条引用的序号、方法、线程、轮次、项目类型、项目编号和调用编号；任何引用错位都会使账本失败。局部检查不得冒充整体结论，部分预期不从实际判定结果回填。运行器按断言 subject 精确映射到整体分类、唯一对应事实或记录声明的局部返回；不认识的 subject 或值不一致会使账本失败。`commands/judge-ledger-assertion-diagnostics.stdout` 保留失败的样例编号、subject、预期值、断言观察值和实际判定值，再按测试编号与调用序号关联样例。G、H、D5–D7 的直接断言有源码方法状态和原始测试日志指针，但不声称独立判定器结果。

## 复验决定和范围

| 用例来源 | 固定材料和依赖 | 复验决定 |
| --- | --- | --- |
| `S3-ISO-1`、`S3-ISO-3`、`S3-ISO-4`、`S3-COMP-1` | `test_issue66_stage3_local_state.py` 与凭据入口隔离测试；本地七套件的 `suite-local_state.*`、`suite-credential.*`。 | 本轮按固定命令复验。 |
| `S3-ISO-2` | 既有 `test_stage3_direction_groups.py::test_stage4_partial_other_professor_rerun_preserves_existing_selection_and_email`。 | 该方法不在七套件内，沿用计划指向的历史材料；不得称作本轮执行。 |
| `S3-ISO-5/6/7`、`S3-DEP-1` | 历史测试 `c389f00addaa4e2c1fd1a53a34df00d70c97843b` 与未变证明产品 `fbda31e30ca71e968170c67df7182aff8e0eda30`；本轮本地状态套件另行执行。 | 历史证明按计划保留；本轮结果不替换历史产品版本证明。 |
| `S3-CREDENTIAL-1`、`S3-CORRECTION-1` | `test_issue66_invocation_credential.py` 固定套件，判定器返回和 `OpenRecorder` 断言。 | 本轮复验；来源、拒绝副作用或精确读集输入改变时重跑。 |
| `S3-HANDOFF-1` | `test_issue66_validation_handoff.py` 固定套件；原始保存和记录返回、同一缓冲区竞态回归。 | 本轮复验；保留已知 `validation_handoff_collision` 失败。 |
| `S3-ASSET-COMPAT-1` | `test_stage3_idea_generator_agent_contract.py` 当前流程断言；调用方兼容证明仍指向 r15 的历史版本。 | 当前流程断言本轮执行并保留失败；历史调用方证明不与之混同。 |
| `S3-RT-CODEX-1` | 需要已批准 Gate2、冻结候选、固定版本安装、服务与专用存储归属证明、请求前后受保护集合及原始 `app_server_events`。 | 未运行。当前目录没有正式评测材料。 |

本地执行环境实际版本、测试提交、候选摘要、每条退出码、七套件实际计数和实际失败身份由最终本轮证据目录记录；候选摘要不写回候选文件，避免自引用。安装及请求构造预检由独立接线入口完成；正式 `/eval`、服务、存储及线程归属仍未核实。

### R4 第 8 节逐用例依赖与复验决定

| 用例 | 产品依赖 | 样例与断言 | 解析和观察方式 | 环境依赖 | 本轮复验决定 |
| --- | --- | --- | --- | --- | --- |
| `S3-ISO-1` | `contact_state.py` 的 plan/finalize 与凭据入口；Stage 3 技能、idea-generator 源文及 Codex 投影正文。 | 本地 finalize 隔离、凭据入口隔离和保留的异常分支；不新增模型隔离样例。 | 入口参数及状态按 JSON 字段检查；本地真实读写由现有测试观察，实际安装投影由 TOML 解码后的正文检查。 | `uv` 临时夹具目录；独占安装消费者。 | 本轮复验受影响本地状态、凭据与代理约定测试；实际安装核验已完成，不替代正式业务。 |
| `S3-ISO-2` | 第四阶段跨教授选择逻辑，未被本轮改动。 | `test_stage4_partial_other_professor_rerun_preserves_existing_selection_and_email`。 | 既有测试按状态 JSON 与邮件文件比较。 | 原测试夹具；没有本轮正式服务依赖。 | 沿用计划标记的历史有效通过；没有触及它的代码或依赖，不重跑。 |
| `S3-ISO-3` | `cmd_stage3_finalize` 的本地事务和凭据提交路径。 | 当前受管稿被人工改动后拒绝，原文字节保留。 | 操作窗口与调用前后同一稿件字节比较。 | 临时教授目录。 | 两个受影响入口分支本轮复验。 |
| `S3-ISO-4` | `cmd_stage3_finalize` 的候选稿安装、正式状态提交及失败恢复。 | 普通和凭据入口的提交前异常、提交后清理失败。 | `os.replace` 窗口观察、状态与 Markdown 原始字节、事务标记。 | 临时教授目录；不需网络。 | 两个入口分支本轮复验。 |
| `S3-ISO-5` | 总览身份派生和排序。 | 规范目录身份、状态身份及排序结果。 | JSON 结构化字段和排序后的键比较。 | 临时程序根。 | 对应确定性测试本轮复验；其他未变历史事实按原版本保留。 |
| `S3-ISO-6` | `stage3-rebuild-overview` 失败处理与旧身份迁移。 | 总览重建失败不反转本地状态；旧身份精确迁移。 | 同一教授状态前后字节及派生总览字段。 | 临时程序根。 | 对应确定性测试本轮复验。 |
| `S3-ISO-7` | 共享登记及第四阶段来源选择。 | 登记独立，第四阶段只读指定教授目录事实。 | 用 `OpenRecorder` 观察真实打开路径，解析状态 JSON。 | 临时程序根与教授目录。 | 对应确定性测试本轮复验。 |
| `S3-DEP-1` | Stage 3 本地提交入口。 | 不要求 Issue 48 或程序根锁才能提交。 | 固定输入夹具，直接执行入口并解析结构化返回。 | 临时教授目录。 | 对应确定性测试本轮复验。 |
| `S3-COMP-1` | 普通及凭据 finalize 的候选兼容与提交。 | 结构、编号、顺序、引用、指纹、校验和凭据变体。 | JSON 逐字段比对及 Markdown 渲染摘要。 | 临时结果目录和教授目录。 | 两个 finalize 入口本轮复验；仅提交号变化不扩大范围。 |
| `S3-CREDENTIAL-1` | plan 捕获、finalize 消费和修正入口。 | 同一实际返回路径与摘要、错误教授、来源漂移、缺首次提交。 | 判定器以事件和实际参数解析；产品入口用真实返回和字节观察。 | 本地 Python 3.14.6、`uv` 临时缓存。 | 凭据套件与判定器样例本轮复验。 |
| `S3-CORRECTION-1` | 已记录问题到修正任务、结果读取、替换和沿用校验记录。 | 集合内读取正控、集合外读取负控、未改组校验记录正负对照。 | `OpenRecorder` 观察真实 `open`；预期集合独立列出，比较修改前后状态 JSON。 | 临时候选结果与教授目录。 | 凭据套件对应入口本轮复验。 |
| `S3-HANDOFF-1` | prepare、save、record 三入口及批量路径。 | 逐入口拒绝、合法空白原文、完整通过/失败、批量教授归属、两轮终态。 | 真实入口在 `OpenRecorder` 窗口内调用；检查所有受保护文件同集合字节及真实返回。 | 临时交接目录；不需要运行模型。 | 交接套件本轮复验；一项已知碰撞失败如实保留。 |
| `S3-ASSET-COMPAT-1` | 源技能、idea-generator 说明及 Codex 投影格式。 | prepare→指定 `output_file`→save→record 顺序；旧直接记录方式拒绝。 | 源 Markdown 与实际安装 TOML 解码正文比较；静态约定测试另行逐条断言顺序。 | 本地仓库文件及精确目标提交的独占安装消费者。 | 当前合同套件执行；保留三个准确匹配的产品失败。安装核验不消除这些产品失败；调用方历史通过按原版本记录。 |
| `S3-RT-CODEX-1` | 精确产品安装、Codex 委派、凭据消费、准备/保存/记录、终态重建。 | 必须使用根与子线程真实事件、产品入口参数及返回值完成一条获批完整路径。 | 固定适配器按线程、轮次、调用及完成顺序解析 `app_server_events`；保留请求前后受保护文件集合。 | Gate 2 批准、专用评测服务和存储、精确夹具/适配器版本、正式 `/eval`。 | Gate 2 未批准；不执行、不补造证据，状态保持未运行。 |

更改判定器、证据解析或样例时，只重跑声明依赖这些内容的判定器样例；凭据、交接、拒绝副作用或读取集合的改动重跑对应入口套件及共享准备依赖。正式产品入口、输入、运行环境或证据来源变化时按命中的用例复验。单纯提交 SHA 改变不自动触发全量复验；沿用的历史通过必须保留其产品/测试版本和影响判断。

## R4 第七节最小预检记录

| 编号 | 计划要求 | 已核对的证据 | 结果 |
| --- | --- | --- | --- |
| 1 | 执行入口、固定程序、隔离、安装、实际配置及存储归属可核验 | APM 0.29.0 在独占消费者执行精确目标提交安装，退出 0，耗时 310.1 秒，证据目录 `issue66-install-preflight.p00XRJAK`。修正初态构造器路径后，`issue66-install-check-fixed-20261006` 退出 0：锁文件完整目标提交、技能与状态脚本原字节、三个代理 TOML 正文、初态摘要、禁止产物缺席、共识请求及前快照均核验成功，`formal_request_sent=false`。旧安装检查 `issue66-install-check-20261006` 退出 2，因测试构造器路径错误保留为 `CASE_NOT_STARTED`。项目 `direnv exec . printenv EVAL_PORT` 退出 1、未返回端口；共享来源指定的测试专用存储根尚未取得，实际进程配置、数据库与日志归属未核实。 | **部分完成**；安装、初态、请求与前快照已就绪；端口及专用存储来源缺口不能记作通过。 |
| 2 | 可信证据核对正式关系、子线程消息、实际工具调用、完成返回字段及关联 | 原始历史探测已可定位并离线重新解析：59 条事件，版本 `codex-cli 0.159.0-alpha.12.1`；21802/21803 共享线程、轮次及消息编号并有相同完整正文，21815 为根接收。`issue66-preflight-20261006/relationship-check.json` 的正式关系及委派对比均为真。原始响应 SHA-256 为 `57ff0300b3e269edbabd11fae6e24e6a62afebabb028dcbd7dca995b6b83ffc8`，原适配器输出为 `46406d63ea382759c958326f12e7ee68d8cd8f6d8168ab8cca89f81c99975316`。原探测未指定业务代理目标、未生产业务文件；不能据此宣称命名代理、生产或权限通过。工具及文件事件格式由固定版本源码、入口确定性证明及判定器反例承担，未增加完整文件监视前提。 | **部分完成**；可信关系及消息能力已复核；当前服务实际事件版本、正式业务生产及权限事实尚未形成。 |
| 3 | 检查合法通过、产品违反、证据无效、外部失败，并确认缺字段不会被默认吞掉 | `issue66-gate2-candidate.iTkWhAuh` 判定器 109 项通过，122 条调用及独立断言覆盖三种合法完成、产品违反、缺失/截断/不支持/混版证据、外部失败前缀与正式安装入口绑定。七套件的 JSON 状态、60 行映射及前后摘要均已核验；两个已知产品问题如实保留。 | **已完成能力检查**；本地整体为 `FAIL`，执行及账本有效；不宣称完整环境预检通过。 |

预检结论：安装、初态、请求构造、前快照及历史消息关系已核验；服务端口、实际配置及专用存储来源仍缺失。未调用 `/eval`，未连接服务存储，未启动或检查用户进程。当前不是完整预检通过；正式业务生产和运行存储归属由后续冻结运行取得，不能提前填成通过。

固定完整预检实际记录为 `issue66-service-preflight-20261006/verdict.json`：`classification=CASE_NOT_STARTED`、`formal_request_sent=false`，程序退出 2；命令 `12-eval-port` 退出 1、未返回端口，在安装和请求之前停止。专用存储来源尚未取得，不能以任意临时根目录替代。

## 历史结果

以下结果仅保留为历史，不能代替本轮候选材料。

| 历史来源 | 结果和用途 |
| --- | --- |
| 本轮早期 `rC0dBU4U` | `issue66-gate2-candidate.rC0dBU4U` 退出 2、`INVALID_TEST_EXECUTION`。六套件符合预期，但十条新增断言的实际值映射为空，直接 `main()` 断言还错误挂入前一次调用；保留原证据。 |
| 本轮中间 `e0gUD8s9` | `issue66-gate2-candidate.e0gUD8s9` 退出 2、`INVALID_TEST_EXECUTION`。六套件均符合预期，但样例账本元数据仍无效；原始诊断和全部输出保留，不能仅凭套件通过改写整体结论。后续继续修复账本并采用测试回调 JSON 和 `jq` 判断。 |
| 本轮结构化首轮 `RcEiCBSP` | `issue66-gate2-candidate.RcEiCBSP` 外层退出 1、写入 `FAIL`，但元数据样例账本为 `INVALID_TEST_EXECUTION`：移除日志扫描时漏保留原日志指针赋值。不能将此轮称作有效完整候选；原样保留矛盾状态与全部材料，修复后用 `iTkWhAuh` 独立复验。 |
| 本地前置中止 | 唯一目录 `issue66-gate2-candidate.mg8BwEmI`。r12 在启动套件前因状态短语检查与本记录用词不一致而退出 64；五套件均未开始，未运行正式评测。r13 改为核对下列完整状态行。 |
| 本地 runner r13 | 测试提交 `000e4d1c42375db63f997acde8368cd51801653b`，候选摘要 `c7d5d1444fc7586bad9d65244fe5b82d35601b0908ae037a1835aa2f22e16a4a`，证据目录 `issue66-gate2-candidate.CNcdSfmq`。五套件结果依次为 judge 81/81、credential 17/17、local_state 12/12 通过；handoff 22 项中 `test_new_invocation_can_prepare_round_one_after_prior_terminal_validation` 失败；agent contract 9 个方法中的 `test_opencode_example_and_common_closeout_follow_skill_handoff_chain` 在 `OpenCode 示例`、`共同收尾`、`禁止旧直接记录方式` 三个子测试失败。该轮为 `INVALID_TEST_EXECUTION`：旧验证器没有把 assertion subject 精确映射到 verdict JSON，分类字段、`attribution`/`observed` 字段及 6 个动态 `facts(verdict)[fact]` 断言因此未通过。离线重核 r13 原始材料时，85 条 JSONL ID 唯一，全部 verdict 断言按精确字段映射后匹配；48 行样例表为 24 列、来源方法定位 48/48、九族数量符合记录，候选摘要前后相同。原始套件身份见 `suites.tsv`，完整判定记录见 `judge-samples.jsonl`，样例映射见 `samples.tsv`。修正精确字段验证后的候选使用新证据目录。 |
| PR #73 评论 [5981805377](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5981805377) | r15 测试提交 `c389f00addaa4e2c1fd1a53a34df00d70c97843b`；未变隔离和依赖产品 `fbda31e30ca71e968170c67df7182aff8e0eda30`。只支持计划标明的历史未变事实。 |
| PR #73 评论 [5982258530](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5982258530) | 当时记录旧版计划、执行步骤、审批结论及历史结果正文已移除，并列出当时完整实施计划、审批、验收约定和测试证明计划的来源。按 R4 第八节保留此历史指针；不以其中旧版内容作为当前执行依据。 |
| Issue #66 评论 [5988929075](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988929075) | `r17-132914` 为 `FAIL`，产品 `76c0a7b4b329cf31ac8b99b0535c713044ab51a6`，当时的根线程没有真实委派。该结果不是本地合成测试结果。 |
| PR #73 评论 [5992605405](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5992605405) | 旧 Gate2 候选未获批准；评论指出原始运行材料不足。旧计数仅作历史声明。 |
| 本地 runner r6 | 当时五套件结果为 judge 71/71、credential 17/17、local state 12/12；handoff 20/21，碰撞失败；agent contract 9 个方法中三个子测试失败。该轮使用旧候选，不能代替当前候选按 r19 运行器记录的结果。 |
| 本地 runner r7–r10 | 均为 `INVALID_TEST_EXECUTION`，依次暴露状态行解析、失败身份汇总、事实级预期校验、计划族/运行时族映射及 I3–I6 程序路径问题。原始材料按唯一目录保留：`issue66-gate2-candidate.qaqT0S9W`、`...CZoWRYBL`、`...Eko0THkD`、`...iuwhGjvD`。 |

历史无效轮次不得合并为一次有效候选。当前运行器若任何样例行无唯一原始状态、缺判定结果、缺摘要或候选前后摘要不一致，也必须保留该轮为 `INVALID_TEST_EXECUTION` 并另开唯一目录重跑。

## Gate 状态与停止条件

Gate2 **未批准**，Gate3 **未运行**。本地候选通过不会批准 Gate2，也不会触发正式运行。`local` 运行器只处理确定性检查；独立 `installation-check` 已完成真实安装产物核验。测试准备不发正式远程请求，不启停服务，不创建定时任务或后台轮询进程。

Gate2 状态：未批准；Gate3 状态：未运行。

完整正式执行材料已准备在 [安装与执行接线](issue-66-execution.md)、`issue-66-formal.sh` 及 `issue66_execution.py`；准备和必要预检不以 Gate2 批准为前提。只有独立审批明确批准并冻结候选后才执行正式 `/eval`。正式动作前核对批准评论绑定的候选摘要和 PR #73 当前 head；缺少批准、摘要或 head 不匹配、目标安装或夹具版本不符、服务/存储归属不清、证据关联不完整时停止。正式评测受真实机器失败前缀约束；不得把缺失观察记作通过，不自动重试，不删除失败证据。

本记录及固定执行材料共同提供待审候选。目标版本安装、实际投影、初态、请求构造与前快照已预检；安装复验使用已有独占消费者，程序记录 `newly_created=false`，元数据曾误写为真之旧材料保留。未完成项为服务端口、共享来源指定的专用存储根及实际配置归属；正式运行后的快照、存储线程归属及真实生产、保存、记录和停止事实尚未形成。缺失环境前提交测试设计审核者处理，不改产品、不降低证明要求。
