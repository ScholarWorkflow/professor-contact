# 第66号议题历史测试结果

本文件只保存旧轮实际结果、样例账本和预检记录，不作为当前测试计划或执行要求。来源为修订前提交 0a6ada41e96be350c6f2ef5fd01ac82e2d08746a 的 test-plan/issue-66.md；旧状态表述均保持历史归属。当前唯一计划见 ../plan/issue-66-test-plan.md。

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

## R7 本地候选实际结果

### 最新本地候选

2026-10-07 在提交 `240dc1236e514344bf61a340cbe1cf89943efd28` 执行 `bash test-plan/issue-66-run.sh local`。证据目录基名为 `issue66-gate2-candidate.KdGywXke`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`。`candidate-summary-input.json` 中 `ledger.validity=VALID`、`sample_ledger_exit_code=0`、`combination_check_exit_code=0`。`candidate-result.json` 的 SHA-256 为 `91e23821c5567b4876d6f13cd77e3a8b6692c88818a5c2c85c0ddb50f723bb28`；`suites.jsonl` 的 SHA-256 为 `871f754314bbb705f903e6b7c757665a5e0991349b3448469eb6b2ea9aa69a3f`。七套件均为 `PASS` 且证据有效，共 212 项：

| 套件 | 结果 | 证据有效性 | 实际条目数 |
| --- | --- | --- | ---: |
| `judge` | `PASS` | `VALID` | 114 |
| `execution_wiring` | `PASS` | `VALID` | 24 |
| `structured_result` | `PASS` | `VALID` | 14 |
| `credential` | `PASS` | `VALID` | 17 |
| `local_state` | `PASS` | `VALID` | 12 |
| `validation_handoff` | `PASS` | `VALID` | 22 |
| `agent_contract` | `PASS` | `VALID` | 9 |

这是提交 `240dc1236e514344bf61a340cbe1cf89943efd28` 的本地确定性候选。Gate 2 未批准，Gate 3 与正式 `/eval` 未运行；本地候选通过不代表正式验收。R7 规定正式评估配置负责独立运行目录，本地不检查服务内部状态。

### 上一轮候选（历史）

2026-10-07 在提交 `2d874c46f8a228ca390a17d2b9ff560db9b75578` 执行同一候选命令。证据目录基名为 `issue66-gate2-candidate.spslDkEj`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`；样例账本为 `VALID`，`sample_ledger_exit_code=0`，`combination_check_exit_code=0`。七套件通过，共 207 项：`judge` 114、`execution_wiring` 19、`structured_result` 14、`credential` 17、`local_state` 12、`validation_handoff` 22、`agent_contract` 9。其摘要为 `candidate-result.json` SHA-256 `91e23821c5567b4876d6f13cd77e3a8b6692c88818a5c2c85c0ddb50f723bb28`、`suites.jsonl` SHA-256 `bc317c11939b6462689bf3a98ac32caa56fb7a6a31b2563f1b07fea4977fb61d`。该轮作为历史保留，不替代最新候选。

### 更早一轮候选（历史）

2026-10-07 在基线提交 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的工作树上执行同一候选命令；当时工作树包含预检接线修正，之后随提交 `45b81f3458dbeb5ed3ea5855823cc0cef19ed509` 推送。证据目录基名为 `issue66-gate2-candidate.RGFhzJ3R`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`。样例账本为 `VALID`，`sample_ledger_exit_code=0`，`combination_check_exit_code=0`；七套件通过，共 199 项：`judge` 114、`execution_wiring` 14、`structured_result` 11、`credential` 17、`local_state` 12、`validation_handoff` 22、`agent_contract` 9。该轮只作历史记录，不替代最新候选。

## R7 正式预检结果

此前预检证据集 `issue66-r7-preflight-now-45b81f3` 的执行器来自 PR 提交 `0896243702c959da8e4981bffacfe820b06719b6` 的干净源码归档。复核原始 `install.json` 发现其 `requested_product_source` 是本地绝对路径，`product_source_kind` 与安装详情均为 `local_project`，安装命令使用 `--root <consumer>`。尽管命令退出码为 `0`、锁文件解析成功且安装器报告装入 10 个依赖，该安装方式违反共识，不是受支持的安装路径；该证据集不能证明预检通过，保留为历史记录。`preflight.json` 仍记录 `PREFLIGHT_ONLY`、`formal_request_sent=false` 和其他准备步骤。

随后针对 PR 提交 `e7d6c7ab4adafddff2aa69f83070892e17d504b6`，使用 APM 远端提交选择器进行了两次预检：`issue66-r7-preflight-pr73-e7d6c7a-20261007-122605` 与 `issue66-r7-preflight-pr73-e7d6c7a-20261007-122605-retry1`。两轮均为 `CASE_NOT_STARTED`、`formal_request_sent=false`。APM 已解析该精确提交并开始安装；依赖仓库克隆遇到 GitHub HTTPS TLS 连接提前结束，安装命令退出码为 `1`，安装事务未提交。两轮均未生成成功的安装或预检记录；原始命令输出和判定保留在各自证据集中。

按用户要求再次重试，第三轮安装命令使用远端选择器 `ScholarWorkflow/professor-contact#e7d6c7ab4adafddff2aa69f83070892e17d504b6`，证据集为 `issue66-r7-preflight-pr73-e7d6c7a-20261007-retry2`。命令在 1200 秒后超时；超时记录没有保存 APM 的提交解析输出，也没有生成成功的安装或预检记录。判定为 `CASE_NOT_STARTED`、`formal_request_sent=false`。这三轮尝试均未完成；当时尚无符合共识的预检结果。第三轮的超时判定与原始输入记录保留在该证据集中。

2026-10-07 针对 PR 当前提交 `7ddd4a6eaaf50e718e40a1099989bded747b0c60` 执行第四轮预检。证据集为 `issue66-r7-preflight-pr73-7ddd4a6-20261007-210516`；`install.json` 记录 APM 远端提交选择器安装通过、退出码 `0`、已安装提交与请求提交一致、消费者为新建且 `manual_patch=no`，锁文件解析通过。`fixture-pre.json` 及运行前快照检查均通过。执行器来源提交为 `d07132f419b2019e243e86a0793800dba0fb5004`。`preflight.json` 记录 `classification=PREFLIGHT_ONLY`、`formal_request_attempted=false`、`formal_request_sent=false`，安装、初始输入、请求构造和运行前快照均已准备。此次远端安装预检完成；没有发送正式请求或运行 `/eval`。

此前失败轮次保留为历史：最初证据集 `issue66-r7-preflight-2723996424c6485fb61efcb4808a8e55c1d71cdd` 因下载 `ScholarWorkflow/base-skills` 时 HTTPS 连接中断而为 `CASE_NOT_STARTED`；修复预检路径误读 `EVAL_PORT` 后，提交 `45b81f3458dbeb5ed3ea5855823cc0cef19ed509` 的普通 HTTPS 与 HTTP/1.1 重试仍遇到依赖下载中断，证据集分别为 `issue66-r7-preflight-45b81f3458dbeb5ed3ea5855823cc0cef19ed509` 和 `issue66-r7-preflight-45b81f3-http11`。此前被误记为成功的本地路径预检也转为历史；各轮原始命令和输出均保留在各自 `commands` 目录。

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
