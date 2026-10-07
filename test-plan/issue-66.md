# Issue 66 本地测试候选记录（R7）

## 计划与候选身份

本记录采用第七版测试计划 `issue-66-test-plan-r19-clarification-r7-2026-10-07`，取代此前关于产品、测试、夹具、适配器、工具版本、文件摘要及批准锁的执行限制。正式业务证明范围仍按本记录各用例表执行。R6 及更早记录只作历史；不得把历史来源、计数、失败名单或摘要当成本轮门槛。

| 执行时填写的字段 | 取值方式 |
| --- | --- |
| 仓库 | `ScholarWorkflow/professor-contact` |
| PR 分支 | `codex/issue-66-stage3-per-professor`（上下文记录，不作版本门槛） |
| 产品来源 | 由本轮执行参数提供并写入来源记录；允许未提交改动，来源不同不拒绝运行 |
| 测试来源 | 记录实际仓库路径、提交及工作树状态；状态只供定位 |
| 夹具与适配器来源 | 按本轮实际输入和版本记录；不与历史固定值比较 |
| 本地运行器 | [issue-66-run.sh](issue-66-run.sh)，修订标记 `issue-66-local-candidate-runner-r21-2026-10-07` |

每轮在独占证据目录记录产品及测试来源、计划修订号、判定程序来源、夹具与适配器来源、工具实际版本、工作目录、安装命令、模型和运行配置、运行编号。没有提交号的源码按未提交状态记录。日志、标准输出、标准错误、命令、退出码、结构化套件报告、实际测试身份与条目、样例账本及四类候选汇总输入和输出一并保存。软件版本和摘要只用于定位；不因与历史值不同而拒绝，也不把摘要相等作为业务通过条件。

2026-10-07 先在提交 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的工作树上运行完整候选，随后在 PR 当前头提交 `bbe44511e0acf5ae1365eb4727ab34c1b892e33c` 复验。前一轮仍作为历史保留；当前头复验结果见“R7 本地候选实际结果”。来源 `2497dae2fffc02b0a66d33ea33b0405e128a9154` 的有效失败也保留在历史记录。本地入口不提供正式 `/eval` 执行。

结构化运行记录本次实际使用的 `uv`、Python、Bash、`jq`、`rg`、`git`、`shasum` 及可用时的 `codex`、`opencode`、`shellcheck` 版本。套件身份和全部条目来自结构化回调；原始标准输出、标准错误和退出码同时留存，不按日志文本或历史版本作判定。

## R7 测试对应

下表对应当前业务要求及负责用例。原业务证明继续有效；R7 只调整来源记录、版本处理和执行账本。当前候选为 `PASS` 且证据有效；Gate 2 仍未通过，正式评测未执行。

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
| `R66-10` | `S3-HANDOFF-1` | 准备、保存、记录三入口绑定原文和轮次；拒绝无副作用；批量归属及两轮终态。 | `test_issue66_validation_handoff.py` 全套与判定器保存/记录样例；调用窗口内操作记录、同集合字节快照、产品真实返回；包含按调用路径隔离交接目录的回归测试。 |
| `R66-10` | `S3-ASSET-COMPAT-1` | 源技能及代理说明保持有限写权限、未指定输出只读、批量交接字段和各自运行时职责。 | `test_stage3_idea_generator_agent_contract.py`；Codex 正文按 TOML 投影方式解码；本次实际结果以结构化回调为准，不预设失败名称或数量。 |
| `R66-10 / COMP66-1` | `S3-RT-CODEX-1` | 正式安装后原生委派、实际凭据消费、校验者产文、根保存记录、权限、顺序、停止和一次终态重建。 | 需要 Gate 2 完整通过、正式安装与 `/eval` 原始事件。R7 规定由正式评估配置负责独立运行目录，本地不检查服务进程、配置、数据库或日志。本轮未运行 `/eval`，原因是 Gate 2 尚未通过。 |

## R7 来源、运行方式与执行范围

运行器在本仓库根目录执行七个确定性套件，不安装产品、不启动或连接评测服务，不发送 `/eval`。执行证据记录实际来源和配置字段：仓库根目录、来源提交、工作树状态、运行目录、计划修订号、各工具版本、`UV_CACHE_DIR`、每套件实际命令、测试身份与条目、结果、退出码、结构化汇总及运行编号。工作树有未提交内容照实记录，不按干净状态或路径名单拒绝。下节保留提交 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的前一轮结果，并补记 PR 当前头提交 `bbe44511e0acf5ae1365eb4727ab34c1b892e33c` 的复验。来源 `2497dae` 的失败见历史结果表。

正式包装脚本通过 `--product-source` 接收本轮实际产品来源，并将它交给执行器。正式配置记录实际产品、测试、夹具、适配器和工具来源及模型、思考级别、沙箱、工作目录、安装命令和运行编号；软件版本只作记录，不作相等门槛。安装只使用支持的安装命令和新建独占消费者，不比较锁文件提交或安装文件字节。

R7 规定由正式评估配置负责建立独立运行目录。本地测试工程师使用既有评估服务，不启动、停止或重启服务，不检查服务进程、配置、数据库或日志，也不增加服务内部隔离检查。本轮没有运行 `/eval`，原因是 Gate 2 尚未通过；不把未检查服务内部状态记为缺口或阻断。

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
| 8. 执行材料 | 运行器按本次实际条目记录七套件身份、结果和退出码；judge 套件保存每次判定调用 JSONL；样例表保留独立业务预期，并映射到本次返回或直接断言。正式执行只在 Gate 2 完整通过后进行。 |

`fileChange` 样例覆盖 `diff`、`kind.type`、`move_path`、开始与完成事件配对、删除及原文字节语义。过往源码链接仅作协议背景，不代表本轮工具版本或版本门槛。正式材料记录实际工具版本，并按实际事件字段和调用关系判定；Add 事件本身不能证明目标此前不存在或排他创建，Update 差异也不能替代结果文件字节证据。`codex exec --json` 与 `app_server_events` 格式不同，测试入口按计划要求的实际事件来源处理，不混用两种证据。

## 本地候选命令和七个套件

从任意目录执行 `bash /仓库绝对路径/test-plan/issue-66-run.sh local`。运行器记录调用目录，再转到脚本所在仓库根目录；只接受 `local`。它不安装产品、不连接评测服务，也不发送 `/eval`。安装及正式执行接线见[执行说明](issue-66-execution.md)；正式执行须等待第二关口完整通过。

七个计划套件身份须各出现且只出现一次。每项实际测试身份、子测试参数、状态、事件、退出码、标准输出和标准错误均保存。条目数从结构化回调读取，不设固定总数或失败名单；每个套件至少有一条实际执行记录，实际条目数仍按本次执行动态记录，不设固定数量门槛。运行器只检查报告字段之间自洽，包括报告结构、实际条目数与条目数组长度、顺序编号、唯一测试身份、结果字段及退出码；有效产品失败保留在汇总中，测试程序问题按无效执行记录。

```sh
uv run --no-project python -B \
  .apm/skills/professor-contact/tests/runtime/issue66_suite_result.py \
  --directory .apm/skills/professor-contact/tests --pattern '<文件名>' \
  --report '<本轮独占证据目录中的套件报告.json>'
```

| 顺序 | 测试文件 | 负责内容 |
| --- | --- | --- |
| 1 | `test_issue66_runtime_judge.py` | 判定器事实、独立预期与实际判定调用账本 |
| 2 | `test_issue66_execution_wiring.py` | 请求构造、快照、安装及正式接线字段 |
| 3 | `test_issue66_suite_result.py` | 结构化回调、失败身份、解析拒绝和四种候选汇总组合 |
| 4 | `test_issue66_invocation_credential.py` | 凭据输入、提交状态及拒绝副作用 |
| 5 | `test_issue66_stage3_local_state.py` | 教授本地状态隔离与提交行为 |
| 6 | `test_issue66_validation_handoff.py` | 交接、原文字节、保存和记录行为 |
| 7 | `test_stage3_idea_generator_agent_contract.py` | 技能与代理说明中的业务流程和权限约定 |

样例账本逐条核验独立预期、实际分类、负责事实、调用来源、事件引用和原始输入，不从被测结果反推预期。四种候选汇总组合分别检查全通过、有效产品失败、无效材料且有独立失败、无效材料且不能归因失败。实际总数、失败身份和子测试数量只作本次结果记录，不作为通过门槛。

## R5 第五版新增定向检查与统一运行（历史）

停止检查新增四个方法、六条账本样例：`test_internal_generator_failure_reports_once_and_stops` 和 `test_internal_generator_failure_then_dependent_action_fails_stop` 各检查计划、提交入口失败；另两项检查第二条报告及错误后成功报告。唯一同轮结构化错误报告与根接收事件不算继续业务；正确停下的 `F-stop-order` 为通过，但业务未完成仍为 `FAIL`。依赖业务续行的停止事实为失败。实际运行系统故障沿用原失败前缀证据，不假定最终消息一定存在。

定向停止检查共 43 项、退出 0，原始材料为 `pr73-stop-final.jsonl/.log`；修前反例材料 `pr73-stop-before.jsonl/.log` 保留。候选汇总定向检查共 9 项、退出 0；`pr73-candidate-summary-precheck-final` 保存每种组合的输入、原始套件记录、独立预期及实际输出。有效证据加独立产品失败为 `FAIL`；无效账本加独立有效产品失败为 `INVALID_TEST_EXECUTION` 且保留局部失败；产品失败本身依赖无效材料时为 `INVALID_TEST_EXECUTION` 且不归因产品；有效且全通过为 `PASS`。

统一运行写入 `candidate-result.json`，按结构字段提供 `evidence_validity`、`overall`、`local_product_failures`、`gaps` 及各自来源。检查结构化套件记录和账本，再保留可独立成立的产品失败；不能因其他套件失败跳过账本检查。`runner_execution=COMPLETE` 只表示运行器已执行完全部步骤，不表示证据有效、候选完整通过或正式验收通过。四组合原始材料另存本轮 `candidate-combinations`。本段所述旧版运行结果仅属历史。

R5 最终证据目录基名为 `issue66-gate2-candidate.4LPblyY0`，位于本机临时目录，完整路径保存在 `/private/tmp/pr73-r5-final.stdout`。七套件依次为判定 113、接线 10、汇总 9、凭据 17、本地状态 12 项通过，交接 22 项含 1 个既有产品失败，代理说明 9 个方法含 3 个既有失败子测试。128 次判定调用、261 条独立断言（249 条判定相关）、66 行 24 列样例均有效；账本校验 `true`、诊断 `[]`，候选前后摘要相同。整体 `FAIL`、退出 1，`evidence_validity=VALID`、缺口数组为空，独立产品失败为交接碰撞及旧代理说明两项。此结论只代表 R5 的本地确定性候选，不代表 R6 或正式验收。

最终 `candidate-result.json` 的 SHA-256 为 `65c7334031f5c5c1c7bae1320819731afe6ea14e9a59876dc044b71792623c6b`，`judge-samples.jsonl` 为 `440168c6aa37022fef60c36d0459e6c1334d214e4f3e066d97613fefd0c8919e`。该轮记录运行前提交 `481c20c50658d4f150ccf10d7f4ce68841dcd94e` 与实际工作树文件摘要，不能将它写成最终推送提交。最后填报只修改两份说明，不改变程序、样例或产品，复用本轮实际检查；最终报告文件另以 `/private/tmp/pr73-r5-final-manifest.sha256` 冻结，不冒用填报前摘要。

第五版首轮 `issue66-gate2-candidate.Xalmaqxa` 为 `INVALID_TEST_EXECUTION`、退出 2：新增六条调用后，运行器漏同步总调用、分类断言和完整事实断言计数。该轮两项独立产品失败仍保留，原始材料不覆盖。三处计数由 122/118/97 同步为 128/124/103；`/private/tmp/pr73-ledger-count-recheck.BiAfBNZk` 使用同一完整校验函数复判原账本为 `true`、退出 0，随后由上述最终独占轮次重新执行固定入口。

新增定向及诊断证据根为 `/private/tmp`。`pr73-stop-final.jsonl` 的 SHA-256 为 `dafa9129ceeebfd566239d10c246c2a315ea715196c3e5d73cf465cd3ae7679c`，同名 `.log` 为 `2478757b4a2c671c1ebaa2db3416d255f21bdb870236308ded5cfcd4d4c47136`。`pr73-candidate-summary-precheck-final/suite-result.json` 为 `349127814e2e9b2f16c0236ff558921e65e3db53a135ccf98cb48c030f1fd3fa`；其 `candidate-combinations` 内四个方法目录的 `actual.json` 摘要分别为：`test_valid_candidate_with_independent_product_failure`：`1539b3401be64c228f2d6768b67ff12eb3e0e6cfa654a4dcdb5df93bf9e7e776`；`test_invalid_ledger_keeps_independent_product_failure`：`b1caedf0c3e4c869b16bf3c1f9f38cac16260b4ceba21b4594612c736f0309ae`；`test_invalid_material_cannot_attribute_product_failure`：`feb6afaf6bfb429cac36ec29d3c643d28884a9a1f281b5f2217e2985f0a1f073`；`test_valid_candidate_all_checks_pass`：`52f9aedd67a253fcc9f3e8881902dfe48f5c62997f9cbc27839d531c73e2081c`。

## 第四版实际执行结果（历史）

| 项目 | 实际结果 |
| --- | --- |
| 运行器 | `issue-66-local-candidate-runner-r19-2026-10-06`；证据目录 `issue66-gate2-candidate.iTkWhAuh`，退出 1，`runner_execution=COMPLETE`。 |
| 历史定位 | 此轮测试提交、候选 SHA-256 和唯一证据目录由运行器写入该轮 `metadata.txt`；不当作第五版候选摘要。 |
| 七套件结果 | 判定器 109、接线 10、结构化记录 5、凭据 17、本地状态 12 项全部通过；交接 22 项含 1 个产品失败，代理约定 9 个方法含 3 个产品失败子测试。实际 JSON 与退出码均保留。 |
| 失败身份 | `test_new_invocation_can_prepare_round_one_after_prior_terminal_validation`；以及 `test_opencode_example_and_common_closeout_follow_skill_handoff_chain` 的 `OpenCode 示例`、`共同收尾`、`禁止旧直接记录方式` 三个子测试。 |
| 判定记录 | 122 条真实调用、245 条独立断言，其中 233 条判定相关断言。分类预期 118 条明确、4 条局部；事实预期 97 条明确、1 条部分、24 条未单独检查。实际返回分布为 `PASS=12`、`FAIL=59`、`INVALID_TEST_EXECUTION=48`、`BLOCKED=3`；负例正确拒绝属于自测通过。 |
| 账本 | 60 行、24 列，无空字段，方法状态全部有效；`sample_ledger_status=VALID_JUDGE_AND_DIRECT_ASSERTION_RECORDS_60_SAMPLES_24_COLUMNS`。判定诊断为 `[]`，账本校验为 `true`、退出 0。 |
| 总结 | 此历史运行整体 `FAIL`，执行及账本有效；失败来自以上两类产品问题。正式评测未运行。 |

每条实际命令、标准输出、标准错误、退出码、原始判定返回、事件摘要、样例行及候选摘要均保存在运行器创建的唯一目录。该目录的原始材料只追加保留，不由本记录改写。

`iTkWhAuh` 绑定第四版候选。第五版改变停止判定、样例和汇总程序，需要对应新运行；不能将旧摘要、计数或通过结果当作第五版完整实测。最终候选由顶层另生成全文件摘要清单冻结；本记录不写入自身最终摘要，避免自引用。

## 第五节样例账本映射

下表保留业务样例及其独立预期，行数和族分布仅供定位，不是运行门槛。实际账本逐条记录观察值、判定依据、计划族、源码方法的动态行号和最小原始证据指针。A–F、I 关联真实判定 JSONL；G、H 及 D5–D7 用 `direct-assertion`，观察状态写作 `assertion-matched`，不伪称判定器结果。计划族与采集器 `sample_family` 分列，不要求两套名称相同。

| 族与数量 | 逐样例测试映射 |
| --- | --- |
| A，3 | A1 `test_one_round_pass`；A2 `test_corrected_two_round_pass`；A3 `test_two_round_exhaustion_is_a_legal_pass`。 |
| B，7 | B1 `test_consumption_uses_actual_capture_return_path_and_digest`；B2 `test_credential_return_bound_to_another_professor_fails`；B3 `test_source_metadata_drift_fails`；B4 `test_missing_first_commit_fails`；B5 `test_handoff_value_drift_fails`；B6 `test_prepare_return_for_another_round_fails`；B7 `test_committed_profile_fingerprint_must_match_capture`。 |
| C，5 | C1 `test_one_round_pass`；C2 `test_named_root_call_with_confirmed_zero_children_fails`；C3 `test_nested_foreign_relation_is_product_failure`；C4 `test_conflicting_formal_owners_for_child_are_invalid`；C5 `test_extra_off_root_formal_relation_fails`。C1 与 A1 共用同一个真实调用记录，并在两行分别保留计划样例身份。 |
| D，7 | D1 `test_legal_whitespace_message_passes`；D2 `test_root_reconstruction_fails`；D3 `test_second_business_message_fails`；D4 `test_complete_run_with_no_validator_production_fails`；D5 `RecordHandoffTests.test_record_parses_the_same_buffer_that_was_digest_checked`；D6 `test_file_change_add_diff_preserves_utf8_and_line_endings` 检查真实对象形 `kind` 下，Unicode、CRLF/LF 及有无尾换行均按原字节保留；D7 `test_file_change_protocol_shape_bytes_lifecycle_delete_and_move_target` 检查缺失或非字符串 `diff`、开始/成功完成配对、增加/更新/删除、Add 不能证明排他创建、Update 差异不能证明结果字节、移动目标范围、伪造字段无效及未知类型缺口。 |
| E，8 | E1 `test_compound_legal_read_and_single_exclusive_output_write_passes`；E2 `test_python_command_with_multiple_write_targets_fails`；E3 `test_same_byte_write_then_restore_still_fails_write_scope`；E4 `test_overwrite_existing_candidate_source_fails_write_scope`；E5 `test_outside_output_write_fails`；E6–E8 `test_pure_unknown_command_is_an_evidence_gap` 的未知命令、未调用函数内写操作、不可达分支写操作。后三者都把权限结论留作证据缺口。 |
| F，17 | F1 `test_machine_failure_prefix_blocks`；F2 `test_correction_dispatch_between_record_start_and_completion_fails`；F3 `test_machine_failure_prefix_does_not_hide_prior_product_failure`；F4 `test_rebuild_started_before_terminal_record_completed_fails`；F5 `test_rebuild_without_completion_is_an_evidence_gap`；F6 `test_terminal_round_bookkeeping_fails`；F7 `test_unrecognized_failure_text_does_not_hide_zero_child_failure`；F8–F10 `test_failed_prepare_write_and_record_stop_dependent_actions` 的准备失败、验证写入失败和记录失败三种调用；F11 `test_machine_failure_prefix_does_not_hide_prior_product_failure` 的正式归属冲突仍保留先前已证实的提前重建产品失败；F12–F13 `test_internal_generator_failure_reports_once_and_stops` 的计划、提交失败后唯一错误报告；F14–F15 `test_internal_generator_failure_then_dependent_action_fails_stop` 的相同两种失败后依赖业务续行；F16 `test_internal_generator_failure_does_not_allow_second_report`；F17 `test_internal_generator_failure_does_not_allow_success_report`。 |
| G，2 | G1 `test_credential_rejection_preserves_the_full_committed_artifact_set`；G2 `test_prepare_save_and_record_refusals_preserve_the_same_artifact_set`。 |
| H，4 | H1、H2 `test_exact_result_read_set_rejects_an_extra_open`；H3、H4 `test_named_group_is_replaced_and_sibling_group_is_kept`。每对分别保存正例与负控观察。 |
| I，12 | I1–I5 `test_required_install_sample_and_snapshot_evidence_cannot_be_omitted` 的 `missing=install,fixture,pre,post,routing` 五个调用，按真实调用序号 1–5；I6 `test_truncated_record_output_is_invalid`；I7 `test_unsupported_message_shape_is_invalid`；I8 `test_non_monotonic_event_seq_invalidates_validator_evidence`；I9 `test_mismatched_call_id_cannot_bind_validator_command_completion`；I10 `test_mixed_evidence_set_ids_are_invalid`；I11–I12 同一方法直接调用 `judge.main()`，分别证明顶层评测响应缺失和截断都返回结构化 `INVALID_TEST_EXECUTION`，并把 `F-test-program`、`F-evidence-set` 记为无效。 |

判定 JSONL 采用 `issue66.sample-ledger.v1`，本轮实际调用和断言数量从回调动态记录。每条保留独立断言、真实返回、判定器摘要、夹具摘要、源码调用位置、完整 `raw_app_server_events`、事件数量和事件索引引用。运行器逐条解析原始事件，核对数组长度及引用的序号、方法、线程、轮次、项目类型、项目编号和调用编号；错位使账本失败。部分预期不从实际结果回填，局部检查不冒充整体结论。运行器按断言 `subject` 精确映射到分类、唯一事实或局部返回；未知字段或值不一致使账本失败。`commands/judge-ledger-assertion-diagnostics.stdout` 保存样例编号、预期、观察值和实际判定值，再按测试编号及调用序号关联。G、H、D5–D7 的直接断言有源码状态及日志指针，不伪称独立判定器结果。

## 复验决定和范围

| 用例来源 | 材料和依赖 | 复验决定 |
| --- | --- | --- |
| `S3-ISO-1`、`S3-ISO-3`、`S3-ISO-4`、`S3-COMP-1` | `test_issue66_stage3_local_state.py` 与凭据入口隔离测试；本地七套件的 `suite-local_state.*`、`suite-credential.*`。 | 本轮按七套件运行器执行，结果以结构化报告为准。 |
| `S3-ISO-2` | 既有 `test_stage3_direction_groups.py::test_stage4_partial_other_professor_rerun_preserves_existing_selection_and_email`。 | 该方法不在七套件内，沿用计划指向的历史材料；不得称作本轮执行。 |
| `S3-ISO-5/6/7`、`S3-DEP-1` | 历史测试 `c389f00addaa4e2c1fd1a53a34df00d70c97843b` 与未变证明产品 `fbda31e30ca71e968170c67df7182aff8e0eda30`；本轮本地状态套件另行执行。 | 历史证明按计划保留；本轮结果不替换历史产品版本证明。 |
| `S3-CREDENTIAL-1`、`S3-CORRECTION-1` | `test_issue66_invocation_credential.py` 套件，判定器返回和 `OpenRecorder` 断言。 | 本轮结果照实记录；来源、拒绝副作用或精确读集输入变化时复验。 |
| `S3-HANDOFF-1` | `test_issue66_validation_handoff.py` 套件；原始保存和记录返回、同一缓冲区竞态回归。 | 记录本轮实际结果和失败身份，不预设失败名称或数量。 |
| `S3-ASSET-COMPAT-1` | `test_stage3_idea_generator_agent_contract.py` 当前流程断言；调用方兼容证明仍指向 r15 的历史版本。 | 当前流程断言本轮执行，实际失败按结构化结果记录；历史调用方证明不与之混同。 |
| `S3-RT-CODEX-1` | 需要 Gate 2 审核通过、实际安装、请求前后受保护集合及原始 `app_server_events`。R7 规定独立运行目录由正式评估配置负责，本地不检查服务内部状态。 | 未运行；Gate 2 尚未通过，因此未运行正式 `/eval`。 |

本地执行环境的实际产品与测试来源、计划及判定程序来源、夹具与适配器来源、工具版本、运行目录、缓存配置、模型与运行配置和运行编号由本轮证据目录记录；同时记录七套件逐项身份、条目、结果、命令原始输出和退出码。Gate 2 尚未通过；不运行正式 `/eval`。

## R7 本地候选实际结果

### PR 当前头提交复验（最新）

2026-10-07 在 PR 当前头提交 `bbe44511e0acf5ae1365eb4727ab34c1b892e33c` 执行 `bash test-plan/issue-66-run.sh local`。证据目录基名为 `issue66-gate2-candidate.Sw2XGr9j`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`。样例账本为 `VALID`，`sample_ledger_exit_code=0`，`combination_check_exit_code=0`。`candidate-result.json` 的 SHA-256 为 `91e23821c5567b4876d6f13cd77e3a8b6692c88818a5c2c85c0ddb50f723bb28`；`suites.jsonl` 的 SHA-256 为 `5369e3b7b2e04a29769532b9b2b9b20ad3d442285692b6f5a47ff5ce6318573b`。七套件均通过且各自证据有效，共 199 项：

| 套件 | 结果 | 证据有效性 | 实际条目数 |
| --- | --- | --- | ---: |
| `judge` | `PASS` | `VALID` | 114 |
| `execution_wiring` | `PASS` | `VALID` | 14 |
| `structured_result` | `PASS` | `VALID` | 11 |
| `credential` | `PASS` | `VALID` | 17 |
| `local_state` | `PASS` | `VALID` | 12 |
| `validation_handoff` | `PASS` | `VALID` | 22 |
| `agent_contract` | `PASS` | `VALID` | 9 |

这是 PR 当前头提交的本地确定性复验。Gate 2 未批准，Gate 3 未运行，正式 `/eval` 未运行；本地候选通过不代表正式验收。R7 规定正式评估配置负责独立运行目录，本地不检查服务内部状态。

### 前一轮候选（历史）

2026-10-07 在基线提交 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的工作树上执行同一候选命令；当时工作树包含预检接线修正，之后随提交 `45b81f3458dbeb5ed3ea5855823cc0cef19ed509` 推送。证据目录基名为 `issue66-gate2-candidate.RGFhzJ3R`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`。样例账本为 `VALID`，`sample_ledger_exit_code=0`，`combination_check_exit_code=0`；七套件通过，共 199 项：`judge` 114、`execution_wiring` 14、`structured_result` 11、`credential` 17、`local_state` 12、`validation_handoff` 22、`agent_contract` 9。该轮只作历史记录，不替代当前头提交复验。

## R7 正式预检结果

本轮正式预检已完成。最新证据集编号为 `issue66-r7-preflight-now-45b81f3`，执行器来源为 PR 提交 `0896243702c959da8e4981bffacfe820b06719b6` 的干净源码归档。`install.json` 记录受支持的安装入口检查通过、退出码 `0`，锁文件解析成功；安装器报告 318 秒内安装 10 个依赖。`preflight.json` 记录 `PREFLIGHT_ONLY`、`formal_request_sent=false`，并确认安装、初始输入、请求构造和运行前快照均已准备。因此正式预检通过；这不代表 Gate 2 获批，也没有发送正式请求或运行 `/eval`。

此前失败轮次保留为历史：最初证据集 `issue66-r7-preflight-2723996424c6485fb61efcb4808a8e55c1d71cdd` 因下载 `ScholarWorkflow/base-skills` 时 HTTPS 连接中断而为 `CASE_NOT_STARTED`；修复预检路径误读 `EVAL_PORT` 后，提交 `45b81f3458dbeb5ed3ea5855823cc0cef19ed509` 的普通 HTTPS 与 HTTP/1.1 重试仍遇到依赖下载中断，证据集分别为 `issue66-r7-preflight-45b81f3458dbeb5ed3ea5855823cc0cef19ed509` 和 `issue66-r7-preflight-45b81f3-http11`。最新独立证据集记录了成功结果；各轮原始命令和输出均保留在各自 `commands` 目录。

### R5 第 8 节逐用例依赖与复验决定（历史）

以下表格保留 R5 的用例依赖快照；其中“本轮”只指 R5，不代表 R7 当前结果或门槛。

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
| `S3-CREDENTIAL-1` | plan 捕获、finalize 消费和修正入口。 | 同一实际返回路径与摘要、错误教授、来源漂移、缺首次提交。 | 判定器以事件和实际参数解析；产品入口用真实返回和字节观察。 | 记录本轮实际 Python、`uv` 及缓存目录。 | 凭据套件与判定器样例的本轮结果按实记录。 |
| `S3-CORRECTION-1` | 已记录问题到修正任务、结果读取、替换和沿用校验记录。 | 集合内读取正控、集合外读取负控、未改组校验记录正负对照。 | `OpenRecorder` 观察真实 `open`；预期集合独立列出，比较修改前后状态 JSON。 | 临时候选结果与教授目录。 | 凭据套件对应入口本轮复验。 |
| `S3-HANDOFF-1` | prepare、save、record 三入口及批量路径。 | 逐入口拒绝、合法空白原文、完整通过/失败、批量教授归属、两轮终态。 | 真实入口在 `OpenRecorder` 窗口内调用；检查所有受保护文件同集合字节及真实返回。 | 临时交接目录；不需要运行模型。 | 交接套件的本轮实际结果和失败身份按实记录。 |
| `S3-ASSET-COMPAT-1` | 源技能、idea-generator 说明及 Codex 投影格式。 | prepare→指定 `output_file`→save→record 顺序；旧直接记录方式拒绝。 | 源 Markdown 与本轮实际安装 TOML 解码正文比较；静态约定测试逐条断言顺序。 | 记录实际产品来源及安装消费者来源。 | 当前合同套件执行；失败身份和数量从结构化结果记录。 |
| `S3-RT-CODEX-1` | 实际产品安装、Codex 委派、凭据消费、准备/保存/记录、终态重建。 | 必须使用根与子线程真实事件、产品入口参数及返回值完成一条获批完整路径。 | 按本轮实际事件字段、线程、轮次、调用及完成顺序解析 `app_server_events`；保留请求前后受保护文件集合。 | Gate 2 审核通过及正式 `/eval`；R7 规定服务隔离由正式评估配置负责，本地不检查服务内部状态。 | 未运行；Gate 2 尚未通过。 |

更改判定器、证据解析或样例时，只重跑声明依赖这些内容的判定器样例；凭据、交接、拒绝副作用或读取集合的改动重跑对应入口套件及共享准备依赖。正式产品入口、输入、运行环境或证据来源变化时按命中的用例复验。单纯提交 SHA 改变不自动触发全量复验；沿用的历史通过必须保留其产品/测试版本和影响判断。

## R5 与 R6 预检记录（历史）

| 编号 | 计划要求 | 已核对的证据 | 结果 |
| --- | --- | --- | --- |
| 1 | 执行入口、安装和输入可核验 | R5 历史记录：APM 0.29.0 在独占消费者安装，退出 0，耗时 310.1 秒，证据目录 `issue66-install-preflight.p00XRJAK`。`issue66-install-check-fixed-20261006` 的旧锁文件、字节比较及初态结果只说明当时记录；旧失败也保留。R6 曾记录工作树端口读取成功，但不代表 R7 Gate 2 或服务隔离要求已通过。 | **历史记录**；不作 R7 门槛或批准。 |
| 2 | 可信证据核对正式关系、子线程消息、实际工具调用、完成返回字段及关联 | 原始历史探测已可定位并离线重新解析：59 条事件，版本 `codex-cli 0.159.0-alpha.12.1`；21802/21803 共享线程、轮次及消息编号并有相同完整正文，21815 为根接收。`issue66-preflight-20261006/relationship-check.json` 的正式关系及委派对比均为真。原始响应 SHA-256 为 `57ff0300b3e269edbabd11fae6e24e6a62afebabb028dcbd7dca995b6b83ffc8`，原适配器输出为 `46406d63ea382759c958326f12e7ee68d8cd8f6d8168ab8cca89f81c99975316`。原探测未指定业务代理目标、未生产业务文件；不能据此宣称命名代理、生产或权限通过。工具及文件事件格式由固定版本源码、入口确定性证明及判定器反例承担，未增加完整文件监视前提。 | **部分完成**；可信关系及消息能力已复核；当前服务实际事件版本、正式业务生产及权限事实尚未形成。 |
| 3 | 检查合法通过、产品违反、证据无效、外部失败，并确认缺字段不会被默认吞掉 | 第五版最终 `issue66-gate2-candidate.4LPblyY0` 的 113 项判定、128 条调用、66 行映射及前后摘要已核验；四组合检查通过，两个已知产品问题保留。首轮计数缺陷及修正复判见新增检查节。 | **已完成能力检查**；本地整体 `FAIL`，执行及账本有效；不宣称完整环境预检通过。 |

以下是 R5/R6 的预检历史：R5 当时从不在项目 `.envrc` 目录树内的工作树读取端口失败，并曾检查评测服务内部状态；R6 记录端口问题已修正、服务内部检查已删除。R7 规定正式评估配置负责独立运行目录，并禁止本地检查服务进程、配置、数据库和日志。此前的内部检查只是历史记录，不是当前要求；本轮不重复这些检查，也不把它们列为待解决问题。

旧原始诊断文件 `pr73-service-observation-20261007.json` 的摘要仅用于定位 R5 历史材料，不作为 R7 证据或门槛。

R5 的 `issue66-service-preflight-20261006/verdict.json` 曾记录 `CASE_NOT_STARTED`、`formal_request_sent=false`，程序退出 2；其 `direnv exec .` 从当时工作树读取时没有取得项目端口。R6 关于重新读取端口的记录仅属历史。当前 R7 不要求本地检查服务内部状态。

## 历史结果

以下结果仅保留为历史，不能代替本轮候选材料。

| 历史来源 | 结果和用途 |
| --- | --- |
| R7 本地候选，来源 `2497dae2fffc02b0a66d33ea33b0405e128a9154` | 执行 `bash test-plan/issue-66-run.sh local`，证据目录基名 `issue66-gate2-candidate.vno2ISAS`；`evidence_validity=VALID`、`overall=FAIL`、退出码 `1`、`gaps=[]`。judge 114、execution_wiring 13、structured_result 11、credential 17、local_state 12 通过；validation_handoff 22 与 agent_contract 9 为 `PRODUCT_FAIL`。交接失败用例 `test_issue66_validation_handoff.PrepareHandoffTests.test_new_invocation_can_prepare_round_one_after_prior_terminal_validation` 报 `validation_handoff_collision`；只读审核确认交接目录身份缺少计划 14 要求的凭据规范路径，并非旧临时目录残留。代理约定失败用例 `test_stage3_idea_generator_agent_contract.Stage3IdeaGeneratorAgentContractTests.test_opencode_example_and_common_closeout_follow_skill_handoff_chain` 中，OpenCode 示例与共同收尾缺少 `stage3-prepare-validation`、`output_file`、`stage3-save-validation` 及带 `--handoff-file`、`--expected-validation-sha256` 的 `stage3-record-validation`；旧直接记录子测试检测到 `--professor-dir`。这些是该来源的历史失败，不代表当前来源结果。 |
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

历史无效轮次不得合并为一次有效候选。本轮若样例无法唯一关联原始状态、缺判定结果或业务输入被不同运行混合，应按实际证据问题记录；提交号、软件摘要或候选前后摘要不同本身不使记录无效。

## Gate 状态与停止条件

Gate 2 **未通过**，Gate 3 **未运行**。PR 当前头提交 `bbe44511e0acf5ae1365eb4727ab34c1b892e33c` 的本地候选为 `PASS` 且证据有效，但这不会批准 Gate 2，也不会触发正式运行。`local` 运行器只处理确定性检查。准备工作不发送正式请求、不启停服务、不读取服务进程、配置、数据库或日志。

Gate2 状态：未批准；Gate3 状态：未运行。

正式执行材料见[安装与执行接线](issue-66-execution.md)、`issue-66-formal.sh` 及 `issue66_execution.py`。Gate 2 未通过时不得运行正式 `/eval`。R7 规定独立运行目录由正式评估配置负责，并禁止本地检查服务进程、配置、数据库或日志；无需为本地测试补做这些检查。当前未运行 `/eval` 的原因是 Gate 2 尚未通过。不得把本地未检查服务内部状态记为证据缺口或失败；不自动重试，不删除失败证据。

本记录及执行材料说明 R7 的当前测试方式。早期安装与失败预检结果仅作历史；当前本地候选和最新正式预检的工具、配置字段、套件身份及结果均已记录。Gate 2 仍未通过，Gate 3 未运行，正式 `/eval` 不运行。正式运行后的真实生产、保存、记录和停止事实尚未形成。
