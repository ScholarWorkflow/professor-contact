# Issue 66 本地测试候选记录

## 计划与候选身份

本记录按 PR #73 评论 [5991701404](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5991701404) 所附完整计划 `issue-66-test-plan-r19-clarification-r4-2026-10-05` 执行，并落实审核评论 [6009197999](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-6009197999) 指出的八类测试侧修订。该计划评论是唯一完整执行依据。

| 项目 | 固定值或取值方式 |
| --- | --- |
| 仓库 | `ScholarWorkflow/professor-contact` |
| PR 分支 | `codex/issue-66-stage3-per-professor` |
| 产品目标提交 | `dfe430560b6e4d9d85c30b71b8c84bc621da7549` |
| PR 基线 | `03dfd501f5212c86356409f7e011f676384f2633` |
| 夹具树 | `c738fa2f8bcbb16cd99d741332d5f59b062b6357` |
| 适配约定 | `skills-test-fixtures/codex-eval-adapter@16` |
| 测试提交 | 每次运行时执行 `git rev-parse HEAD`，写入该轮证据；不在计划中伪填提交号 |
| 本地运行器 | [issue-66-run.sh](issue-66-run.sh)，修订标记 `issue-66-local-candidate-runner-r16-2026-10-06` |
| 任务辅助脚本 | `.tmp_scripts/2026-10-06_watch_pr73.sh` 保留在工作树；只排除此单一文件，不计入候选摘要 |

候选输入摘要在运行时对运行器固定清单逐文件计算，再对清单计算 SHA-256。运行器在套件前后各算一次；不把摘要写回本记录或运行器。每条命令的完整标准输出、标准错误、退出码和实际命令保存在唯一临时证据目录。每条样例在 `samples.tsv` 保存候选摘要、测试状态、动态源码位置及原始日志指针；判定器样例还关联真实 JSONL 返回、判定器摘要、事件摘要及事件引用。测试提交号和产品目标号分开记录。

固定本地环境为 `uv 0.12.11` 与 Python `3.14.6`，解释器通过 `uv run --no-project --python 3.14.6` 选择，缓存目录为 `/private/tmp/issue66-uv-cache`。运行器捕获实际 `uv`、Python、Bash、`jq`、操作系统版本和可用时的 `shellcheck` 版本。它先核对仓库根、远端、目标提交祖先关系、产品源相对产品目标无差异、工作树变更范围、候选文件摘要和工具版本。

## 八项测试侧修订

| 修订 | 本地确定性证明及证据来源 |
| --- | --- |
| 1. 正式归属 | `test_issue66_runtime_judge.py` 中 `test_one_round_pass`、`test_named_root_call_with_confirmed_zero_children_fails`、`test_extra_off_root_formal_relation_fails`、`test_nested_foreign_relation_is_product_failure`、`test_conflicting_formal_owners_for_child_are_invalid`。运行时 JSONL 保留独立预期与实际分类；正式根关系不存在、根外关系和冲突分别按计划分类。 |
| 2. 实际返回值绑定 | `test_consumption_uses_actual_capture_return_path_and_digest`、`test_committed_profile_fingerprint_must_match_capture`、`test_damaged_version_digest_and_ownership_fail_before_writes`、`test_credential_return_bound_to_another_professor_fails`、`test_source_metadata_drift_fails`、`test_missing_first_commit_fails`、`test_handoff_value_drift_fails`、`test_prepare_return_for_another_round_fails`。判定器把实际捕获的资料指纹与提交状态绑定；产品入口测试还逐字节核对原始资料、凭据和提交状态中的指纹。 |
| 3. 原始正文与同一字节缓冲区 | `test_legal_whitespace_message_passes`、`test_root_reconstruction_fails`、`test_second_business_message_fails`、`test_complete_run_with_no_validator_production_fails`，以及 `test_issue66_validation_handoff.py::RecordHandoffTests.test_record_parses_the_same_buffer_that_was_digest_checked`。最后一项在摘要校验后将源文件替换为另一份合法 JSON，断言摘要及记录状态来自首次读取的字节。 |
| 4. 有限写权限 | `test_compound_legal_read_and_single_exclusive_output_write_passes`、`test_outside_output_write_fails`、`test_python_command_with_multiple_write_targets_fails`、`test_same_byte_write_then_restore_still_fails_write_scope`、`test_overwrite_existing_candidate_source_fails_write_scope`、`test_pure_unknown_command_is_an_evidence_gap`。合成事件证明判定器分类；它们不冒充正式运行的系统写入跟踪。 |
| 5. 顺序、停止和重建 | `test_machine_failure_prefix_blocks`、`test_failed_prepare_write_and_record_stop_dependent_actions`、`test_failed_save_return_cannot_be_followed_by_record_as_pass`、`test_unsuccessful_capture_return_cannot_bind_credentials`、`test_correction_dispatch_between_record_start_and_completion_fails`、`test_machine_failure_prefix_does_not_hide_prior_product_failure`、`test_unrecognized_failure_text_does_not_hide_zero_child_failure`、`test_rebuild_before_record_fails`、`test_rebuild_started_before_terminal_record_completed_fails`、`test_terminal_round_bookkeeping_fails`、`test_rebuild_without_completion_is_an_evidence_gap`。新增负例分别让准备、验证输出写入、记录失败后仍继续派发、保存或重建；三次实际判定调用均留在 JSONL。 |
| 6. 拒绝副作用 | 凭据入口 `test_credential_rejection_preserves_the_full_committed_artifact_set`；准备、保存和记录入口 `test_prepare_save_and_record_refusals_preserve_the_same_artifact_set`。两项直接比较同一受保护文件集合的调用前后存在性与字节。 |
| 7. 读取集合与沿用 | `test_exact_result_read_set_rejects_an_extra_open` 保存独立预期读取集、真实打开记录、额外打开负例和未变哨兵；`test_named_group_is_replaced_and_sibling_group_is_kept` 检查 `dir_C` 原校验记录保留及删除记录负控。 |
| 8. 固定执行材料 | 运行器固定套件顺序和命令、记录版本及每条退出码；judge 套件保存每次真实判定调用 JSONL；样例表将计划样例映射到真实判定器返回或明确标成直接断言。正式评测门槛见下文。 |

## 固定命令和套件顺序

从任意目录执行 `bash /仓库绝对路径/test-plan/issue-66-run.sh local`。运行器先记录调用时目录，再切换到脚本所属的仓库根目录；仅接受 `local`，任何其他参数在临时证据目录之外拒绝，退出码为 64。它不含正式评测执行分支。

每套件运行同一形式的命令：

```sh
uv run --no-project --python 3.14.6 python -B -m unittest discover \
  -s .apm/skills/professor-contact/tests -p '<文件名>' -v
```

| 顺序 | 测试文件 | 预期条目数 | 本地候选期望 |
| --- | --- | ---: | --- |
| 1 | `test_issue66_runtime_judge.py` | 90 | 全部通过；96 次真实判定调用写入 `judge-samples.jsonl` |
| 2 | `test_issue66_invocation_credential.py` | 17 | 全部通过 |
| 3 | `test_issue66_stage3_local_state.py` | 12 | 全部通过 |
| 4 | `test_issue66_validation_handoff.py` | 22 | 21 项通过；保留一个已知产品失败 |
| 5 | `test_stage3_idea_generator_agent_contract.py` | 9 个方法 | 其余断言通过；保留三个已知子测试失败 |

第 4 套件预期失败必须由原始 `... FAIL` 行精确匹配：`test_new_invocation_can_prepare_round_one_after_prior_terminal_validation (test_issue66_validation_handoff.PrepareHandoffTests.test_new_invocation_can_prepare_round_one_after_prior_terminal_validation) ... FAIL`，行为断言标识为 `validation_handoff_collision`。

第 5 套件预期失败必须是同一方法 `test_opencode_example_and_common_closeout_follow_skill_handoff_chain` 的三个实际失败子测试，分别为 `section='OpenCode 示例'`、`section='共同收尾'`、`section='禁止旧直接记录方式'`。运行器按完整失败状态行匹配，不能只靠方法名或失败总数判断。保留当前断言，不改代理说明来消除这些失败。

执行中若条目数、退出码、失败身份、记录结构、样例映射或前后候选摘要任一不符，整轮记录为 `INVALID_TEST_EXECUTION`。确定性套件按记录如实为已知产品失败且所有执行证据有效时，候选整体为 `FAIL`。这两类本地结果都不是正式评测结论。

## 第五节样例账本映射

运行器生成 52 行 `samples.tsv`。本地样例编号只用于账本定位；每行记录独立预期、观察值、判定依据、计划族、源码方法的动态行号和最小原始证据指针。A–F、I 关联真实判定 JSONL；G、H 及 D5 用 `direct-assertion`，观察状态写作 `assertion-matched`，不伪称判定器结果。计划族与采集器 `sample_family` 分列，不要求两套名称相同。

| 族与数量 | 逐样例测试映射 |
| --- | --- |
| A，3 | A1 `test_one_round_pass`；A2 `test_corrected_two_round_pass`；A3 `test_two_round_exhaustion_is_a_legal_pass`。 |
| B，7 | B1 `test_consumption_uses_actual_capture_return_path_and_digest`；B2 `test_credential_return_bound_to_another_professor_fails`；B3 `test_source_metadata_drift_fails`；B4 `test_missing_first_commit_fails`；B5 `test_handoff_value_drift_fails`；B6 `test_prepare_return_for_another_round_fails`；B7 `test_committed_profile_fingerprint_must_match_capture`。 |
| C，5 | C1 `test_one_round_pass`；C2 `test_named_root_call_with_confirmed_zero_children_fails`；C3 `test_nested_foreign_relation_is_product_failure`；C4 `test_conflicting_formal_owners_for_child_are_invalid`；C5 `test_extra_off_root_formal_relation_fails`。C1 与 A1 共用同一个真实调用记录，并在两行分别保留计划样例身份。 |
| D，5 | D1 `test_legal_whitespace_message_passes`；D2 `test_root_reconstruction_fails`；D3 `test_second_business_message_fails`；D4 `test_complete_run_with_no_validator_production_fails`；D5 `RecordHandoffTests.test_record_parses_the_same_buffer_that_was_digest_checked`。 |
| E，5 | E1 `test_compound_legal_read_and_single_exclusive_output_write_passes`；E2 `test_python_command_with_multiple_write_targets_fails`；E3 `test_same_byte_write_then_restore_still_fails_write_scope`；E4 `test_overwrite_existing_candidate_source_fails_write_scope`；E5 `test_outside_output_write_fails`。 |
| F，10 | F1 `test_machine_failure_prefix_blocks`；F2 `test_correction_dispatch_between_record_start_and_completion_fails`；F3 `test_machine_failure_prefix_does_not_hide_prior_product_failure`；F4 `test_rebuild_started_before_terminal_record_completed_fails`；F5 `test_rebuild_without_completion_is_an_evidence_gap`；F6 `test_terminal_round_bookkeeping_fails`；F7 `test_unrecognized_failure_text_does_not_hide_zero_child_failure`；F8–F10 `test_failed_prepare_write_and_record_stop_dependent_actions` 的准备失败、验证写入失败和记录失败三种调用。 |
| G，2 | G1 `test_credential_rejection_preserves_the_full_committed_artifact_set`；G2 `test_prepare_save_and_record_refusals_preserve_the_same_artifact_set`。 |
| H，4 | H1、H2 `test_exact_result_read_set_rejects_an_extra_open`；H3、H4 `test_named_group_is_replaced_and_sibling_group_is_kept`。每对分别保存正例与负控观察。 |
| I，11 | I1–I6 `test_required_install_sample_storage_and_snapshot_evidence_cannot_be_omitted` 的 `missing=install,fixture,storage,pre,post,routing` 六个调用，按真实调用序号 1–6；I7 `test_truncated_record_output_is_invalid`；I8 `test_unsupported_message_shape_is_invalid`；I9 `test_non_monotonic_event_seq_invalidates_validator_evidence`；I10 `test_mismatched_call_id_cannot_bind_validator_command_completion`；I11 `test_mixed_evidence_set_ids_are_invalid`。 |

judge JSONL 采用 `issue66.sample-ledger.v1`；冻结采集为 96 条真实 `run(fx)` 调用、唯一 `sample_id=test_id#run-N`。每条保留独立断言、真实 `actual.outcome` 和原始 `actual.result`、判定器摘要、夹具摘要、源码调用位置、事件数量和事件引用。预期中有 90 条分类断言、6 条未单独断言分类的调用、77 条事实断言及 1 条事实部分预期；部分预期不从实际判定结果回填。运行器逐条校验必需字段、类型、唯一编号、摘要和事件引用，并按断言 subject 精确映射到 `actual.result.classification` 或唯一对应的 `actual.result.facts[].verdict`；不认识的 subject 或值不一致会使账本失败。`commands/judge-ledger-assertion-diagnostics.stdout` 保留失败的样例编号、subject、预期值、断言观察值和实际判定值，再按测试编号与调用序号关联样例。G、H、D5 的直接断言有源码方法状态和原始测试日志指针，但不声称独立判定器结果。

## 复验决定和范围

| 用例来源 | 固定材料和依赖 | 复验决定 |
| --- | --- | --- |
| `S3-ISO-1`、`S3-ISO-3`、`S3-ISO-4`、`S3-COMP-1` | `test_issue66_stage3_local_state.py` 与凭据入口隔离测试；本地五套件的 `suite-local_state.*`、`suite-credential.*`。 | 本轮按固定命令复验。 |
| `S3-ISO-2` | 既有 `test_stage3_direction_groups.py::test_stage4_partial_other_professor_rerun_preserves_existing_selection_and_email`。 | 该方法不在五套件内，沿用计划指向的历史材料；不得称作本轮执行。 |
| `S3-ISO-5/6/7`、`S3-DEP-1` | 历史测试 `c389f00addaa4e2c1fd1a53a34df00d70c97843b` 与未变证明产品 `fbda31e30ca71e968170c67df7182aff8e0eda30`；本轮本地状态套件另行执行。 | 历史证明按计划保留；本轮结果不替换历史产品版本证明。 |
| `S3-CREDENTIAL-1`、`S3-CORRECTION-1` | `test_issue66_invocation_credential.py` 固定套件，判定器返回和 `OpenRecorder` 断言。 | 本轮复验；来源、拒绝副作用或精确读集输入改变时重跑。 |
| `S3-HANDOFF-1` | `test_issue66_validation_handoff.py` 固定套件；原始保存和记录返回、同一缓冲区竞态回归。 | 本轮复验；保留已知 `validation_handoff_collision` 失败。 |
| `S3-ASSET-COMPAT-1` | `test_stage3_idea_generator_agent_contract.py` 当前流程断言；调用方兼容证明仍指向 r15 的历史版本。 | 当前流程断言本轮执行并保留失败；历史调用方证明不与之混同。 |
| `S3-RT-CODEX-1` | 需要已批准 Gate2、冻结候选、固定版本安装、服务与专用存储归属证明、请求前后受保护集合及原始 `app_server_events`。 | 未运行。当前目录没有正式评测材料。 |

本地执行环境实际版本、测试提交、候选摘要、每条退出码、五套件实际计数和实际失败身份由本轮证据目录记录；候选摘要不写回候选文件，避免自引用。正式 `S3-RT-CODEX-1` 的安装、服务、存储、请求、评测数据及用户进程检查均不属于本地运行器，也未执行。

## 历史结果

以下结果仅保留为历史，不能代替本轮候选材料。

| 历史来源 | 结果和用途 |
| --- | --- |
| 本地前置中止 | 唯一目录 `/var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue66-gate2-candidate.mg8BwEmI`。r12 在启动套件前因状态短语检查与本记录用词不一致而退出 64；五套件均未开始，未运行正式评测。r13 改为核对下列完整状态行。 |
| 本地 runner r13 | 测试提交 `000e4d1c42375db63f997acde8368cd51801653b`，候选摘要 `c7d5d1444fc7586bad9d65244fe5b82d35601b0908ae037a1835aa2f22e16a4a`，证据目录 `/var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue66-gate2-candidate.CNcdSfmq`。五套件结果依次为 judge 81/81、credential 17/17、local_state 12/12 通过；handoff 22 项中 `test_new_invocation_can_prepare_round_one_after_prior_terminal_validation` 失败；agent contract 9 个方法中的 `test_opencode_example_and_common_closeout_follow_skill_handoff_chain` 在 `OpenCode 示例`、`共同收尾`、`禁止旧直接记录方式` 三个子测试失败。该轮为 `INVALID_TEST_EXECUTION`：旧验证器没有把 assertion subject 精确映射到 verdict JSON，分类字段、`attribution`/`observed` 字段及 6 个动态 `facts(verdict)[fact]` 断言因此未通过。离线重核 r13 原始材料时，85 条 JSONL ID 唯一，全部 verdict 断言按精确字段映射后匹配；48 行样例表为 24 列、来源方法定位 48/48、九族数量符合记录，候选摘要前后相同。原始套件身份见 `suites.tsv`，完整判定记录见 `judge-samples.jsonl`，样例映射见 `samples.tsv`。修正精确字段验证后的候选使用新证据目录。 |
| PR #73 评论 [5981805377](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5981805377) | r15 测试提交 `c389f00addaa4e2c1fd1a53a34df00d70c97843b`；未变隔离和依赖产品 `fbda31e30ca71e968170c67df7182aff8e0eda30`。只支持计划标明的历史未变事实。 |
| Issue #66 评论 [5988929075](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988929075) | `r17-132914` 为 `FAIL`，当时的根线程没有真实委派。该结果不是本地合成测试结果。 |
| PR #73 评论 [5992605405](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5992605405) | 旧 Gate2 候选未获批准；评论指出原始运行材料不足。旧计数仅作历史声明。 |
| 本地 runner r6 | 当时五套件结果为 judge 71/71、credential 17/17、local state 12/12；handoff 20/21，碰撞失败；agent contract 9 个方法中三个子测试失败。该轮使用旧候选，不能代替当前 81/17/12/22/9。 |
| 本地 runner r7–r10 | 均为 `INVALID_TEST_EXECUTION`，依次暴露状态行解析、失败身份汇总、事实级预期校验、计划族/运行时族映射及 I3–I6 程序路径问题。原始材料按唯一目录保留：`/var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue66-gate2-candidate.qaqT0S9W`、`...CZoWRYBL`、`...Eko0THkD`、`...iuwhGjvD`。 |

历史无效轮次不得合并为一次有效候选。当前运行器若任何样例行无唯一原始状态、缺判定结果、缺摘要或候选前后摘要不一致，也必须保留该轮为 `INVALID_TEST_EXECUTION` 并另开唯一目录重跑。

## Gate 状态与停止条件

Gate2 **未批准**，Gate3 **未运行**。本地候选通过不会批准 Gate2，也不会触发正式运行。当前运行器只处理 `local`，不安装正式产品、不发远程评测请求、不读取或修改评测存储、不启动或重启服务、不检查用户进程、不创建定时任务或后台轮询进程。

Gate2 状态：未批准；Gate3 状态：未运行。

只有后续独立审批明确批准 Gate2 并冻结候选后，才可另行准备正式评测执行材料。正式动作前必须核对批准评论绑定的候选摘要和 PR #73 当前 head；缺少批准、摘要或 head 不匹配、目标安装或夹具版本不符、服务/存储归属不清、证据关联不完整时停止。正式评测受真实机器失败前缀约束；不得把缺失观察记作通过，不自动重试，不删除失败证据。

本记录和运行器提供的是确定性本地候选。尚未提供的正式阶段证据包括：目标版本安装与实际投影、专用评测服务和存储归属、请求前后完整受保护文件集合、正式原始事件中真实的委派/生产/保存/记录顺序和工具写入观察。未有 Gate2 批准前，这些项目不运行、不声称已验证。
