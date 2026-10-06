# Issue 66 第二关口本地候选记录

候选编号：issue-66-gate2-candidate-r6-2026-10-06

状态：本地候选 **FAIL**，**Gate2 待批准**。本记录和 runner 只支持本地确定性检查；不代表第二关口通过，也不授权正式运行。

## 权威计划、目标版本与范围

- 冻结计划：`issue-66-test-plan-r19-clarification-r4-2026-10-05`，本地原文 `/private/tmp/issue66-test-plan-r19.md`，SHA-256 `ed55e1226e5f6b4a702884ce69aac71751c77066b9fcf02f770a26211926a84c`；计划来源为 PR 评论 [5991701404](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5991701404)。本记录对照其第 4、5、7、8 节。
- 本轮修订要求：PR 评论 [6009197999](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-6009197999)，要求补齐八类测试侧证据和可复验材料。
- 已批准执行方案：第 13 版，议题评论 [5983011055](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5983011055)，批准记录为 PR 评论 [5983107348](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5983107348)。此批准不等于 Gate2 批准。
- Gate1：第 6 版 PASS，议题评论 [5988663001](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988663001)。
- 仓库与 PR：`ScholarWorkflow/professor-contact`、PR #73、分支 `codex/issue-66-stage3-per-professor`。
- 固定产品目标提交：`112a16cb6aa6c34d9abb5a018436a1735308ad83`；PR 基准提交：`03dfd501f5212c86356409f7e011f676384f2633`。
- 当前工作目录由本记录执行时的 `pwd` 得到：`/Users/rekidunois/.codex/worktrees/7bb3/professor-contact`。runner 从自身路径定位仓库，并用 `git rev-parse --show-toplevel` 核验；不写死或期望其他工作树路径。
- 测试提交号由 runner 每次执行 `git rev-parse HEAD` 取得并写入证据。执行时记录的 SHA 是当时检出提交；若测试文件未提交，测试改动仍以摘要清单表示，不谎称已包含在该提交。
- 共享夹具计划版本：`skills-test-fixtures` 提交 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`；适配器约定：`skills-test-fixtures/codex-eval-adapter@16`。本地套件用测试源码中的合成数据，不检出该共享仓库；runner 核对记录与脚本中的固定针脚，不能据此证明正式夹具服务可用。
- 实测环境基准：`uv 0.12.11 (aarch64-apple-darwin)`、`Python 3.14.6`。每次 runner 执行都重新采集 `uv`、`bash`、Python 版本和完整命令输出。
- 唯一缓存路径：`/private/tmp/issue66-uv-cache`。Python 命令用 `uv run --no-project`，避免同步或安装项目依赖。
- 测试和判定文件的版本以运行时生成的 SHA-256 清单为准；清单摘要运行时计算，不写入自身或本记录，避免自引用。产品目标 SHA、检出 HEAD 和未提交候选摘要分开记录。

## 八项修订与实际断言覆盖

下表依据当前测试函数和断言，不把计划描述或“套件已运行”当作覆盖证据。测试运行只证明这些合成样例的结果；正式事件和评测链路仍未执行。

| 修订 | 实际测试与断言 | 覆盖判断 |
| --- | --- | --- |
| 1. 归属、路由和唯一结论 | `test_issue66_runtime_judge.py`：`test_zero_real_delegation_is_a_product_failure` 断言 `FAIL` 与归属失败；`test_extra_off_root_formal_relation_fails` 断言归属和路由失败；`test_conflicting_formal_owners_for_child_are_invalid` 断言 `INVALID_TEST_EXECUTION`；`test_install_check_status_is_folded_into_unique_verdict`、`test_required_routing_and_install_evidence_cannot_be_omitted` 检查安装/路由纳入结论。 | **明确覆盖合成判定**；真实服务事件关联待正式运行。 |
| 2. 实际凭据与逐轮交接绑定 | `test_consumption_uses_actual_capture_return_path_and_digest` 用捕获返回的路径和摘要替换事件，再检查消费链；`test_credential_value_drift_fails`、`test_credential_file_path_drift_fails`、`test_source_metadata_drift_fails`、`test_missing_first_commit_fails`、`test_handoff_value_drift_fails` 覆盖代表性错值。凭据入口另有 `test_capture_records_parsed_parameters_and_returns_digest` 和 `test_prepare_verifies_the_credential_first`。 | **部分覆盖**：代表性返回值和变化有断言；计划列出的所有轮次元数据、源、保存目标及三项记录参数尚未形成逐字段、逐轮完整矩阵。 |
| 3. 原文生产、保存和消费 | `test_raw_text_blocks_are_concatenated_as_original_utf8_bytes` 比较 UTF-8 原始字节；`test_file_change_event_proves_production_without_command_actions` 去掉 `commandActions` 后仍以文件变化通过；缺少内容、内容不符、无 item 身份、错误轮次分别由 `test_file_change_without_contents_cannot_prove_raw_production`、`test_file_change_with_different_contents_fails_raw_integrity`、`test_message_without_item_identity_cannot_prove_original`、`test_message_from_another_turn_cannot_be_attributed_to_production` 检查。交接文件另由 `test_save_copies_the_exact_source_bytes` 和 `test_record_digests_the_bytes_it_actually_parses` 检查。 | **部分覆盖**：正文、文件变化、线程/轮次相关负例有断言；缺少对完整 `call_id`、事件序号及每轮开始/完成关联的独立反例，真实 `app_server_events` 也未接入本地套件。 |
| 4. 有限写权限 | `test_compound_read_and_allowed_write_then_unauthorized_write_fails`、`test_python_command_with_multiple_write_targets_fails`、`test_proven_unauthorized_write_survives_following_unknown_command`、`test_compound_legal_read_and_single_exclusive_output_write_passes`、`test_pure_unknown_command_is_an_evidence_gap`、`test_actual_file_change_outside_output_fails` 分别检查组合读写、多目标、后续未知命令、合法排他写、证据缺口和实际文件变化。 | **部分覆盖**：列出的解析样例有断言；未覆盖所有命令/程序行为，也没有单独“先改后还原同字节”的测试。实际调用程序的完整写入事实须留给正式原始事件。 |
| 5. 顺序、停止和重建 | `test_correction_dispatch_between_record_start_and_completion_fails`、`test_correction_spawned_before_record_completes_fails`、`test_dispatch_after_terminal_record_fails`、`test_rebuild_before_record_fails`、`test_terminal_round_bookkeeping_fails`、`test_terminal_state_round_count_matches_observed_validator_rounds`、`test_rebuild_after_terminal_record_is_exactly_once`、`test_machine_failure_prefix_blocks` 检查顺序、终局轮数、一次重建和外部失败前缀。`test_first_round_correction_and_second_round_loop`、`test_second_round_fail_is_terminal_after_two_rounds` 检查合法二轮路径。 | **明确覆盖所列确定性样例**；不能替代真实运行中的停止前缀和调用返回。 |
| 6. 拒绝操作无副作用 | `test_credential_rejection_preserves_the_full_committed_artifact_set` 对凭据拒绝前后的提交产物做快照比较；`test_prepare_save_and_record_refusals_preserve_the_same_artifact_set` 对三个交接入口的同一受保护集合比较；`test_damaged_version_digest_and_ownership_fail_before_writes` 覆盖凭据拒绝原因。 | **明确覆盖代表性本地拒绝路径**；正式安装目录和服务状态快照未做。 |
| 7. 读取集合和旧校验记录 | `test_exact_result_read_set_rejects_an_extra_open` 用 `OpenRecorder` 对真实打开做正、负对照；`test_first_round_skip_and_group_request_are_records_not_requests` 和 `test_named_group_is_replaced_and_sibling_group_is_kept` 先记录问题后取基线，比较实际读集、替换集合、未触及结果及状态。后者复制修正后状态、删除未变方向的校验记录，并断言 `assert_validator_after_correction` 能拒绝该状态。 | **明确覆盖本地读集合和记录保持负向控制**；真实服务事件读取仍待正式运行。 |
| 8. 唯一可执行候选 | `issue-66-run.sh` 生成唯一证据目录，核对仓库/产品 SHA/允许变更/固定针脚，运行版本、语法和测试命令，计算候选清单摘要，并逐命令留输出与退出码。此次实际 runner 结果见下文及其证据目录。 | **本地部分落实**；这不是测试断言，也不含正式安装、服务/存储预检或正式判定程序。 |

即使五个套件全部运行，也不表示八项要求都有断言。当前四项有明确的本地确定性断言，四项部分覆盖；实际 Gate2 还缺真实评测链路及表中指出的断言材料。

候选摘要固定纳入全部被测实现、测试输入和直接测试依赖，逐文件 SHA-256 由 runner 在每次执行时写入 `candidate-files.sha256`：

- `.apm/agents/professor-contact-idea-generator.agent.md`
- `.apm/skills/professor-contact/SKILL.md`
- `.apm/skills/professor-contact/scripts/contact_state.py`
- `.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py`
- `.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py`
- `.apm/skills/professor-contact/tests/test_issue66_invocation_credential.py`
- `.apm/skills/professor-contact/tests/test_issue66_validation_handoff.py`
- `.apm/skills/professor-contact/tests/test_issue66_stage3_local_state.py`
- `.apm/skills/professor-contact/tests/test_stage2_resolved_direction.py`
- `.apm/skills/professor-contact/tests/test_stage3_direction_groups.py`
- `.apm/skills/professor-contact/tests/test_stage3_idea_generator_agent_contract.py`
- `test-plan/issue-66.md`
- `test-plan/issue-66-run.sh`

本地允许变更的候选文件是上述清单中的 runner、记录和五份 Issue 66 测试/判定文件。现存任务辅助脚本 `.tmp_scripts/2026-10-06_watch_pr73.sh` 只在变更范围检查中按精确路径排除，不进入候选摘要；任何其他目录外改动都会停止执行。`test_stage3_stage4_caller_contract.py` 属于历史资产契约证据；本轮无对应产品入口或安装说明变更，按第 8 节保留历史结果，不纳入本地重跑。

## 固定本地复验步骤与证据

仓库根目录为 `/Users/rekidunois/.codex/worktrees/7bb3/professor-contact`。执行者先运行 `pwd` 确认位置，再按固定命令运行：

~~~bash
cd /Users/rekidunois/.codex/worktrees/7bb3/professor-contact
./test-plan/issue-66-run.sh local
~~~

runner 从脚本位置取得仓库根目录，不读取 PR 当前 head，也没有正式评测分支。预检依序执行并保存输出与退出码：`uv --version`、`bash --version`、`bash -n test-plan/issue-66-run.sh`；检查 `shellcheck`，若存在则执行 `shellcheck --version` 与 `shellcheck test-plan/issue-66-run.sh`；执行 `uv run --no-project --python 3.14 python --version`；然后记录 `uname -a`、Git 根目录、origin、工作树状态、检出 HEAD、固定产品目标提交解析、目标为 HEAD 祖先的检查、`git diff HEAD --check`、已跟踪和未跟踪变更路径。候选路径外的变更会停止执行。

脚本常量和本文必须同时含共享夹具提交 `c738fa2f8bcbb16cd99d741332d5f59b062b6357` 及适配器 `skills-test-fixtures/codex-eval-adapter@16`。这只是固定版本声明核对；本地运行不检出夹具仓库。五条确定性命令使用 `uv run --no-project --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p <文件名> -v`，顺序固定如下：

1. `test_issue66_runtime_judge.py`
2. `test_issue66_invocation_credential.py`
3. `test_issue66_stage3_local_state.py`
4. `test_issue66_validation_handoff.py`
5. `test_stage3_idea_generator_agent_contract.py`

runner 在 `${TMPDIR}` 下用 `mktemp -d` 创建唯一目录；未设置 `TMPDIR` 时使用 `/tmp`。不会覆盖历史目录。目录中的定位方式如下：

| 文件 | 内容 |
| --- | --- |
| `metadata.txt` | 唯一目录、产品目标 SHA、检出 HEAD、候选摘要、固定针脚、工具和 Gate2/正式评测状态 |
| `commands.tsv` | 每条外部命令的名字、实际退出码、完整命令及 stdout/stderr 文件路径 |
| `commands/<名称>.stdout`、`.stderr` | 对应命令完整标准输出和错误输出；包括五个套件 |
| `commands/<名称>.command` | 逐命令重跑所需的原样参数 |
| `candidate-files.sha256`、`candidate-files.after.sha256` | 运行前后逐文件候选摘要；摘要不同则结果无效 |
| `suites.tsv` | 每个测试文件的实际条目数、退出码、判定和已知失败说明 |
| `outcome.txt` | 唯一候选结论及 runner 完成状态 |

本地已知产品失败会继续运行后续套件并保留输出；符合预期的产品失败使 runner 以退出码 1、`candidate_verdict=FAIL` 完成。命令失败、测试条目数改变、失败特征不符、版本/路径/摘要检查失败均不能判通过；证据格式或候选绑定异常时结论为 `INVALID_TEST_EXECUTION`。本地 `PASS` 也不等于 Gate2 获批。

## 用例版本、依赖、证据来源与复验决定

所有当前套件使用产品目标 `112a16cb6aa6c34d9abb5a018436a1735308ad83`；检出 HEAD、未提交测试内容和每个输入文件的 SHA-256 由本次 `metadata.txt` 与 `candidate-files.sha256` 分别固定。下表的实际输出位置均为本次唯一证据目录下的 `commands/suite-<名称>.stdout`、`.stderr`，退出码见同目录 `commands.tsv`，摘要结论见 `suites.tsv`。

| 套件 | 测试输入与直接依赖 | 环境依赖、证据来源 | 复验决定 |
| --- | --- | --- | --- |
| `judge`：`test_issue66_runtime_judge.py` | 判定程序 `runtime/judge_issue66_stage3_runtime.py`；事件样例由该测试文件构造，两个文件均纳入候选摘要。 | Python 3.14 标准库；本地合成事件，不连评测服务。逐例结果来自 `unittest -v` 原始输出，候选判定版本来自清单 SHA-256。 | 本轮运行。修订了判定与样例，按 r19 §8 重跑相关确定性判定。 |
| `credential`：`test_issue66_invocation_credential.py` | 被测 `contact_state.py`；测试直接依赖 `test_stage2_resolved_direction.py`、`test_stage3_direction_groups.py`、`test_issue66_stage3_local_state.py`；均纳入摘要。 | Python 3.14 标准库、隔离临时文件；实际 CLI 子进程和 `OpenRecorder` 读集合观察；无网络。 | 本轮运行。凭据、修正范围、来源读取和拒绝快照有本轮断言改动。 |
| `local_state`：`test_issue66_stage3_local_state.py` | 被测 `contact_state.py`；直接依赖 `test_stage2_resolved_direction.py`、`test_stage3_direction_groups.py`，均纳入摘要。 | Python 3.14 标准库、隔离临时工作目录；包含教授隔离、提交标记、重建、旧身份迁移、资产契约和 Issue 48 锁依赖样例。 | 本轮随固定套件执行。`S3-ISO-5/6/7`、`S3-DEP-1` 的既有历史仍保留；本次结果只补充当前确定性执行，不覆盖历史版本来源。 |
| `validation_handoff`：`test_issue66_validation_handoff.py` | 被测 `contact_state.py`；直接依赖 `test_stage2_resolved_direction.py`、`test_stage3_direction_groups.py`，均纳入摘要。 | Python 3.14 标准库、隔离临时工作目录；实际 CLI、原文文件字节、保存/记录返回和同一产物快照。 | 本轮运行。交接、拒绝副作用和终局顺序属于本轮修改受影响范围。 |
| `agent_contract`：`test_stage3_idea_generator_agent_contract.py` | 静态读取 `.apm/agents/professor-contact-idea-generator.agent.md` 与 `.apm/skills/professor-contact/SKILL.md`；三份文件均纳入摘要。 | Python 3.14 标准库；不启动 Codex/OpenCode 子代理。原始失败断言见 `suite-agent_contract.stderr`。 | 本轮运行兼容检查，保留现有失败；流程文档仍有旧交接说明，需按当前获批流程更新后复验。 |
| `caller_contract`：`test_stage3_stage4_caller_contract.py` | 历史来源测试提交 `c389f00addaa4e2c1fd1a53a34df00d70c97843b`；其所对应产品版本 `fbda31e30ca71e968170c67df7182aff8e0eda30`。 | 证据来源为 r19 §8 指定的第十五版正文 [评论 5981805377](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5981805377)；不是当前套件输出，也不计入本轮测试数。 | 复用有效历史。按 r19 §8，本轮没有命中其产品入口或直接依赖；若入口、契约、安装投影改变，再运行受影响资产检查。 |
| `S3-RT-CODEX-1` 正式入口 | 目标产品和共享夹具按上方固定版本；当前没有 Gate2 批准评论。 | 没有请求、安装、服务或存储证据；Gate2 阻止正式入口。 | **未运行**。只能在 Gate2 通过并冻结后按批准的新记录执行。 |

测试文件来源与本地结果是两种证据：本地 `unittest` 输出证明的是当前被纳入摘要的代码和合成样例；历史资产结果仍绑定其旧测试/产品版本，不能用本轮 HEAD 替换。

### 冻结计划用例编号对应的复验决定

| 计划用例 | 当前或历史测试材料 | 版本、依赖和证据位置 | 本轮决定 |
| --- | --- | --- | --- |
| `S3-ISO-1`、批量教授隔离 | `test_issue66_stage3_local_state.py::test_s3_iso_1_local_finalize_isolation`、`::test_s3_iso_1_b_anomalies_via_credential_entry`；`test_issue66_validation_handoff.py::test_batch_raw_matches_only_this_professor`、`::test_batch_advances_a_while_b_state_unreadable` | 当前产品目标 `112a16cb6aa6c34d9abb5a018436a1735308ad83`；测试和 CLI 支持文件摘要在本轮目录；输出在 `suite-local_state.*`、`suite-validation_handoff.*`。 | 本轮按完整套件运行；不增加教授损坏注入或批量模型运行。 |
| `S3-ISO-2` | r19 §2 指向既有“其他教授分支”。本地可定位的相关测试为 `test_stage3_direction_groups.py::test_stage4_partial_other_professor_rerun_preserves_existing_selection_and_email`，但它未由本 runner 执行。 | 当前文件只作为候选输入摘要；r19 §8 未提供该单项当前运行输出目录或精确历史测试 SHA。历史有效输出需回到原评论核验。 | 按计划复用未变历史，不在本轮重跑；本记录不把该测试名冒充本轮执行证据。 |
| `S3-ISO-3`、`S3-ISO-4`、`S3-COMP-1` | `test_issue66_stage3_local_state.py::test_s3_iso_3_local_manual_conflict`、`::test_s3_iso_4_commit_marker`、`::test_s3_comp_1_preserved_candidate_contract`；凭据入口另有 `::test_s3_iso_1_b_anomalies_via_credential_entry`、`::test_s3_iso_3_manual_conflict_via_credential_entry`、`::test_s3_iso_4_commit_marker_via_credential_entry`、`::test_s3_comp_1_preserved_contract_via_credential_entry`。 | 当前目标产品 `112a16cb6aa6c34d9abb5a018436a1735308ad83` 与本轮摘要；执行位置 `suite-local_state.stdout/stderr`。 | 本轮运行。凭据变体受本轮入口与拒绝断言影响。 |
| `S3-ISO-5/6/7`、`S3-DEP-1` | `test_s3_iso_5_aggregate_identity_derivation`、`test_s3_iso_6_rebuild_failure_legacy`、`test_s3_iso_7_registry_stage4_source`、`test_s3_dep_1_no_issue48_lock_dependency`。 | r19 §8 的历史来源为 PR 评论 [5981805377](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5981805377)：测试 `c389f00addaa4e2c1fd1a53a34df00d70c97843b`、未变证明产品 `fbda31e30ca71e968170c67df7182aff8e0eda30`；本轮额外输出在 `suite-local_state.*`。 | 历史有效结果继续保留；当前文件属于固定执行套件，随本轮执行，但不替换旧版本证明。 |
| `S3-CREDENTIAL-1`、`S3-CORRECTION-1` | `test_capture_records_parsed_parameters_and_returns_digest`、`test_consumption_uses_actual_capture_return_path_and_digest`、`test_credential_rejection_preserves_the_full_committed_artifact_set`、`test_exact_result_read_set_rejects_an_extra_open`、`test_first_round_skip_and_group_request_are_records_not_requests`、`test_named_group_is_replaced_and_sibling_group_is_kept`、`test_render_text_quote_expands_scopes_under_credential`。 | 当前产品目标 `112a16cb6aa6c34d9abb5a018436a1735308ad83` 与运行时测试 SHA；`suite-credential.stdout/stderr`、`commands.tsv`。 | 本轮运行；凭据、来源和读集输入变化时重跑。 |
| `S3-HANDOFF-1` | `test_new_invocation_can_prepare_round_one_after_prior_terminal_validation`、`test_save_copies_the_exact_source_bytes`、`test_record_digests_the_bytes_it_actually_parses`、`test_prepare_save_and_record_refusals_preserve_the_same_artifact_set`、`test_first_round_correction_and_second_round_loop`、`test_batch_raw_matches_only_this_professor`、`test_second_round_fail_is_terminal_after_two_rounds`。 | 当前产品目标 `112a16cb6aa6c34d9abb5a018436a1735308ad83` 与运行时测试 SHA；`suite-validation_handoff.stdout/stderr`、`commands.tsv`。 | 本轮运行；结果中保留既有碰撞失败。 |
| `S3-ASSET-COMPAT-1` | `test_stage3_stage4_caller_contract.py` 的历史调用方契约断言；当前 agent 文档兼容用例 `test_stage3_idea_generator_agent_contract.py` 单独运行。 | 调用方契约来源绑定 r15 测试 `c389f00addaa4e2c1fd1a53a34df00d70c97843b` 和产品 `fbda31e30ca71e968170c67df7182aff8e0eda30`；当前 agent 检查结果在 `suite-agent_contract.*`，两者不可互换。 | 调用方资产复用历史；agent 文档检查本轮运行并保留失败。 |
| `S3-RT-CODEX-1` | 真实运行样例。 | 需要 Gate2 批准、冻结候选、干净安装、专用服务/存储核验和原始事件；本地证据目录不含这些材料。 | 未运行，当前明确禁止。 |

## 当前确定性结果

下列结果由当前测试实现复跑确认。runner 会再次按固定顺序执行并保存本次完整证据；不能把预期失败当作整组通过。

| 用例文件 | 结果 | 退出码 | 结论 |
| --- | --- | --- | --- |
| test_issue66_runtime_judge.py | 71 项通过 | 0 | PASS |
| test_issue66_invocation_credential.py | 17 项通过 | 0 | PASS |
| test_issue66_stage3_local_state.py | 12 项通过 | 0 | PASS |
| test_issue66_validation_handoff.py | 21 项中 20 项通过、1 项失败 | 1 | 产品 FAIL：test_new_invocation_can_prepare_round_one_after_prior_terminal_validation 在上次终局验证后为新调用准备第一轮时遇到 validation_handoff_collision。 |
| test_stage3_idea_generator_agent_contract.py | 9 项中 8 项通过、1 项测试失败 | 1 | 产品 FAIL：test_opencode_example_and_common_closeout_follow_skill_handoff_chain 的 3 个子断言均失败；OpenCode 示例和共同收尾仍引用旧交接流程，并保留旧的直接记录方式。 |

五份测试结果于 2026-10-06 由本地 runner 按固定顺序复跑。凭据文件实际为 17 项通过；新增的精确读取集合负向检查使旧记录中的 16 项失效。runner 会核对实际条目数、退出码和两项已知失败标记。正式评测没有运行。

候选 runner 草稿首次执行的证据目录为 /var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue66-gate2-candidate.UtY1gZcn。该次原始输出显示凭据文件 17 项通过，但草稿仍期待 16 项，因此被 runner 标为 INVALID_TEST_EXECUTION；该草稿结论无效，目录保留作诊断记录。runner 与本记录的数量已更正，后续完整运行生成新的候选证据目录。

r5 首次执行的证据目录 `/var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue66-gate2-candidate.SBNXgL75` 为 `INVALID_TEST_EXECUTION`，不可复用：执行期间 `test_issue66_invocation_credential.py` 摘要由 `21f27af9938eb697e3a7bafc9e157421f6bf9759ce9a50a2c289c8e239219dc4` 变为 `66fd71fc4c886617df85806d126c406125603bb5bf4eb0ebcd40d139fe25e55c`；`agent_contract` 原始输出为 `Ran 9 tests`、`FAILED (failures=3)`，当时 runner 错误期待 1 个失败，之后已改为期待 3 个失败子测试。该目录保留完整前后清单及所有原始输出。

r5 稳定版本运行的证据目录 `/var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue66-gate2-candidate.5O20S98P` 仍为 `INVALID_TEST_EXECUTION`，不可作为有效候选：`suite-judge.stderr` 显示 71 项全部通过、退出码 0，而 runner 仍期待 63 项，因此错误归类为无效。运行前后候选摘要相同，未发现候选文件变化或证据缺项；r6 已把固定预期修正为 71 项。原始输出、逐命令退出码和摘要清单保留在该目录。

## 已知历史结论

- 第 17 版正式尝试 `r17-132914` 为 FAIL；产品版本 `76c0a7b4b329cf31ac8b99b0535c713044ab51a6`，原因为根线程没有真实委派，来源为议题评论 [5988929075](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988929075)。
- 第 15 版历史正文和测试来源按 r19 §8 保留：PR 评论 [5981805377](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5981805377)，测试文件提交 `c389f00addaa4e2c1fd1a53a34df00d70c97843b`，其未变隔离/依赖产品版本 `fbda31e30ca71e968170c67df7182aff8e0eda30`。这些旧证据只支持计划标明的未变事实。
- 旧的 r15、r15b、r16、r16c、r16d 尝试分别留在评论 [5977978350](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5977978350)、[5978308810](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5978308810)、[5981001106](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5981001106)、[5981959094](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5981959094)、[5982175709](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5982175709)。r19 要求保留各次 FAIL、INVALID 或 BLOCKED 的历史；本地没有逐次原始事件和完整输出，不能在本记录中重新判读或合并成当前结果。
- Gate1 第 6 版为 PASS。
- 先前第二关口候选第 21 版见 PR 评论 [5992605405](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5992605405)，未获批准。旧记录报告过 39 项判定、15 项凭据、12 项本地状态、19 项交接和 8 项流程兼容；该评论指出运行原始材料不足。旧计数只作为历史声明保存，不替代本轮原始输出。
- runner 首次草稿执行目录 `/var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue66-gate2-candidate.UtY1gZcn` 留作诊断记录：凭据套件实际 17 项通过，草稿错误期待 16 项，故该次为 `INVALID_TEST_EXECUTION`，不能作为当前候选结果。
- PR 评论 [6009197999](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-6009197999) 判定 Gate2 NEEDS_MODIFICATION、Gate3 NOT_READY，并要求本记录列出的八类测试侧修订。
- 本地两项产品 FAIL 是确定性回归结果，不是正式运行 S3-RT-CODEX-1 的结论。

## 正式评测状态与停止条件

正式运行 S3-RT-CODEX-1 **未运行**。Gate2 **待批准**，Gate3 尚未开始。本次 runner 只接受 `local` 参数；其他参数在创建运行目录前以退出码 64 拒绝。脚本没有正式评测分支，元数据写入 `formal_eval_mode=DISABLED_UNTIL_GATE2_APPROVAL`。本地套件全部通过也不会自动触发正式评测；脚本不读取 PR 批准、不启动服务、不安装产品、不发请求、不访问评测存储，也不代替原生委派。

冻结计划要求正式阶段使用产品目标提交的干净安装，固定安装投影和输入，识别现存评测服务及其专用存储，使用共享夹具提交和适配器约定，保存同一受保护文件集的请求前后完整快照，并从原始 app_server_events 得到正式归属、调用关系、字节内容、写入范围及调用顺序。服务只能只读检查；不得启动、停止或重启。每个正式入口只运行一次，机器故障时按实际事件前缀停止并保留全部材料。

只有第二关口通过并冻结候选后，才能另行准备正式运行脚本。该脚本必须在任何远程评测动作前要求 PR #73 的 Gate2 批准评论编号，动态读取 PR 当前 head，并核对评论绑定的本候选摘要和当时 PR head；任一条件不匹配就停止。当前本地 runner 不读取 PR，也没有可达的正式运行分支。

若正式阶段遇到以下任一情况，必须停止受影响操作并保留现有证据：没有 Gate2 明确批准；批准针对的候选摘要或 PR head 与当前值不一致；产品安装版本或投影不符；夹具版本不符；服务、数据库或日志的归属无法确认；证据无法按冻结计划关联；真实机器故障发生；或拒绝操作改变了受保护产物。不得将缺失观察记为通过，不得自动重试，不得删除失败材料。

## 结论

本记录是本地确定性候选，不是完整 Gate2 通过材料。当前结果包含两项产品 FAIL，候选总结果为 FAIL；还缺八项覆盖表标出的逐轮字段/事件关联断言、完整写入样例负控、清除旧校验记录负控，以及 Gate2 批准后正式安装、服务/存储归属、真实事件和 `S3-RT-CODEX-1` 证据。处理产品失败和缺少证据后，应按批准方案另行复验。Gate2 尚未批准，正式评测未运行，不得据此报告 Gate2 PASS、Gate3 PASS 或可合并。
