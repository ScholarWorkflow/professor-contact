# Issue 66 第二关口本地候选记录

候选编号：issue-66-gate2-candidate-r4-2026-10-06

状态：本地候选，**Gate2 待批准**。候选包含测试实现、判定程序、执行记录和本地 runner；不代表第二关口通过，也不授权正式运行。

## 权威计划与目标版本

- 冻结测试计划：第 4 版完整计划 issue-66-test-plan-r19-clarification-r4-2026-10-05，PR 评论 [5991701404](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5991701404)。
- 本次修订依据：PR 评论 [6009197999](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-6009197999)。该评论要求修复八类测试侧缺口，不要求修改产品代码。
- 已批准执行方案：第 13 版，议题评论 [5983011055](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5983011055)，批准记录为 PR 评论 [5983107348](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5983107348)。该批准不是 Gate2 批准。
- Gate1：第 6 版 PASS，议题评论 [5988663001](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988663001)。
- 仓库：ScholarWorkflow/professor-contact；PR：#73；候选分支：codex/issue-66-stage3-per-professor。
- 测试所针对的产品目标提交：112a16cb6aa6c34d9abb5a018436a1735308ad83。该值固定表示本轮开始时的 PR 产品版本。
- PR 基准提交：03dfd501f5212c86356409f7e011f676384f2633。
- 测试提交：不在记录中预填。runner 每次执行时以 git rev-parse HEAD 读取并写入证据目录。当前候选测试文件未提交时，该值就是当时工作树的 HEAD；它与固定产品目标 SHA 分别记录，不能据此声称未提交的测试文件已成为该提交内容。
- 共享夹具仓库提交：c738fa2f8bcbb16cd99d741332d5f59b062b6357。
- 适配器约定：skills-test-fixtures/codex-eval-adapter@16。
- 当前实测工具版本：uv 0.12.11 (aarch64-apple-darwin)；Python 3.14.6。runner 会在每次执行中重新采集完整输出。
- 本轮运行缓存目录：/private/tmp/issue66-uv-cache。
- 判定程序版本由候选文件清单中的 SHA-256 固定；完整候选摘要由 runner 在运行时计算，不写入自身或本记录，避免摘要自引用。

## 本轮落实的八项修订

修改仅限测试与记录文件，没有修改产品实现。

| 项 | 完成内容 |
| --- | --- |
| 1. 归属与路由 | 将路由、安装和快照证据并入唯一总判定。正例需要真实委派关系；已确认无子调用时判 FAIL，观测缺失时记证据缺口，越界关系判 FAIL，所有权冲突判 INVALID。 |
| 2. 凭据与来源绑定 | 将实际返回的调用凭据文件及摘要、教授和来源、每轮元数据、文件、保存与记录参数绑定起来。来源内容和教授状态用实际字节及摘要核对；不存在的可选来源按计划处理。 |
| 3. 原始事件与交接字节 | 从 app_server_events 按线程、轮次、调用编号、事件序号及真实返回关联证据。只接受唯一的子线程 validator 原始正文；文件变化和命令行为以实际事件与返回为证，保存及记录复用同一字节。 |
| 4. 写入范围 | 按实际命令或程序行为识别所有写入目标。已证明的未授权写入判 FAIL；只读与许可范围内的写入可判通过；行为无法证明时记证据缺口。 |
| 5. 停止和重建顺序 | 用前一调用完成时间与下一调用开始时间判断顺序；按真实失败前缀停止，不等待后续阶段证据来覆盖已成立的 FAIL；终局记录后只允许一次程序级重建。 |
| 6. 拒绝无副作用 | 凭据失败以及 prepare、save、record 自身拒绝前后，对同一组完整受保护产物比较存在性、类型和字节；同时覆盖 plan 与 submit 直接入口。 |
| 7. 读取与更正核对 | 预期读取集合独立于实际读取集合；实际读取、返回和替换集合逐项比较，负向对照可识别多读文件。问题记录后才保存基线，并比较完整验证记录及所有未要求改变的字段。 |
| 8. 唯一候选与执行记录 | 更新本记录和 runner，移除旧目标版本、旧工作树地址、旧测试数量和只打印步骤的脚本。runner 支持本地候选执行，动态采集提交和候选摘要，并为每条命令保存输出及退出码。 |

候选摘要所含文件清单：

- .apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py
- .apm/skills/professor-contact/tests/test_issue66_runtime_judge.py
- .apm/skills/professor-contact/tests/test_issue66_invocation_credential.py
- .apm/skills/professor-contact/tests/test_issue66_validation_handoff.py
- .apm/skills/professor-contact/tests/test_issue66_stage3_local_state.py
- test-plan/issue-66.md
- test-plan/issue-66-run.sh

另外运行 test_stage3_idea_generator_agent_contract.py 作为流程兼容检查；该测试文件未纳入本候选改动清单。

## 固定的本地复验命令与证据位置

在仓库根目录运行：

~~~bash
./test-plan/issue-66-run.sh local
~~~

runner 会依次核对 Git 仓库、产品目标提交及祖先关系、允许修改的文件范围、夹具与适配器版本、候选文件摘要和必要命令。随后按以下固定顺序运行整份确定性测试文件：

~~~bash
UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue66_runtime_judge.py -v
UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue66_invocation_credential.py -v
UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue66_stage3_local_state.py -v
UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue66_validation_handoff.py -v
UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_stage3_idea_generator_agent_contract.py -v
~~~

每次执行在 $TMPDIR/issue66-gate2-candidate.<唯一编号>/ 新建目录，不覆盖旧运行。目录内保存候选文件 SHA-256 清单、运行前后摘要、版本和提交元数据、commands.tsv、各命令的完整 stdout 与 stderr、退出码、逐文件测试结论及总结果。实际唯一目录路径由 runner 打印并写入元数据。

本地模式遇到已知产品行为失败时仍会完成后续测试并保存证据，最终以退出码 1 和 candidate_verdict=FAIL 结束；工具、版本、归属或输出结构不符时以 INVALID_TEST_EXECUTION 停止。通过只说明本地候选自检完成，不代表 Gate2 获批。

## 当前确定性结果

下列结果由当前测试实现复跑确认。runner 会再次按固定顺序执行并保存本次完整证据；不能把预期失败当作整组通过。

| 用例文件 | 结果 | 退出码 | 结论 |
| --- | --- | --- | --- |
| test_issue66_runtime_judge.py | 63 项通过 | 0 | PASS |
| test_issue66_invocation_credential.py | 17 项通过 | 0 | PASS |
| test_issue66_stage3_local_state.py | 12 项通过 | 0 | PASS |
| test_issue66_validation_handoff.py | 21 项中 20 项通过、1 项失败 | 1 | 产品 FAIL：test_new_invocation_can_prepare_round_one_after_prior_terminal_validation 在上次终局验证后为新调用准备第一轮时遇到 validation_handoff_collision。 |
| test_stage3_idea_generator_agent_contract.py | 9 项中 8 项通过、1 项测试失败 | 1 | 产品 FAIL：test_opencode_example_and_common_closeout_follow_skill_handoff_chain 的 3 个子断言均失败；OpenCode 示例和共同收尾仍引用旧交接流程，并保留旧的直接记录方式。 |

五份测试结果于 2026-10-06 由本地 runner 按固定顺序复跑。凭据文件实际为 17 项通过；新增的精确读取集合负向检查使旧记录中的 16 项失效。runner 会核对实际条目数、退出码和两项已知失败标记。正式评测没有运行。

候选 runner 草稿首次执行的证据目录为 /var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue66-gate2-candidate.UtY1gZcn。该次原始输出显示凭据文件 17 项通过，但草稿仍期待 16 项，因此被 runner 标为 INVALID_TEST_EXECUTION；该草稿结论无效，目录保留作诊断记录。runner 与本记录的数量已更正，后续完整运行生成新的候选证据目录。

## 已知历史结论

- 第 17 版正式尝试 r17-132914 为 FAIL；记录的产品版本是 76c0a7b4b329cf31ac8b99b0535c713044ab51a6，失败原因为根线程没有真实委派。该历史结果保留，当前候选不覆盖它。
- Gate1 第 6 版为 PASS。
- 先前第二关口候选第 21 版记录于 PR 评论 [5992605405](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5992605405)，未获批准；其测试数量和目标版本已由当前记录取代。
- PR 评论 [6009197999](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-6009197999) 判定 Gate2 NEEDS_MODIFICATION、Gate3 NOT_READY，并要求本记录列出的八类测试侧修订。
- 本地两项产品 FAIL 是确定性回归结果，不是正式运行 S3-RT-CODEX-1 的结论。

## 正式评测状态与停止条件

正式运行 S3-RT-CODEX-1 **未运行**。Gate2 **待批准**，Gate3 尚未开始。本次 runner 没有正式评测模式，不会启动服务、安装产品、发出请求、读取评测数据库或代替原生委派。

冻结计划要求正式阶段使用产品目标提交的干净安装，固定安装投影和输入，识别现存评测服务及其专用存储，使用共享夹具提交和适配器约定，保存同一受保护文件集的请求前后完整快照，并从原始 app_server_events 得到正式归属、调用关系、字节内容、写入范围及调用顺序。服务只能只读检查；不得启动、停止或重启。每个正式入口只运行一次，机器故障时按实际事件前缀停止并保留全部材料。

只有第二关口通过并冻结候选后，才能准备正式运行脚本。该脚本必须在任何远程评测动作前要求 PR #73 的 Gate2 批准评论编号，动态读取 PR 当前 head，并核对评论绑定的本候选摘要和当时 PR head；任一条件不匹配就停止。当前本地 runner 不读取 PR，也不执行该分支。

若正式阶段遇到以下任一情况，必须停止受影响操作并保留现有证据：没有 Gate2 明确批准；批准针对的候选摘要或 PR head 与当前值不一致；产品安装版本或投影不符；夹具版本不符；服务、数据库或日志的归属无法确认；证据无法按冻结计划关联；真实机器故障发生；或拒绝操作改变了受保护产物。不得将缺失观察记为通过，不得自动重试，不得删除失败材料。

## 结论

本记录是可复验的 Gate2 待审候选。当前确定性结果包含两项产品 FAIL，故候选总结果为 FAIL；需要按批准的产品计划处理缺陷后再提交新的测试证据。Gate2 尚未批准，正式 S3-RT-CODEX-1 未运行，不得据此报告 Gate2 PASS、Gate3 PASS 或可合并。
