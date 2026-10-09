# 第66号议题／第73号拉取请求测试计划

版本：`issue-66-test-plan-new-rules-r4.14-2026-10-10`。

当前版本链：目标分支基线 `b19e53764ae654113140e3293e90ac49e9ff1d8f`，产品提交 `f053d913afce47abed5abade9bf6e2737179f497`，A、C补充测试提交 `162843c1c843989fbf09b45fd808d5276c92b94d`，校验代理修复提交 `e6a4c19856c841f877fd082a5161cc083290156d`，本次审核输入提交 `65477f1203f08fe2371e0caa8d74f131e6bfc92b`。R4.14取代R4.13成为唯一当前计划；A—E业务范围不变。本版恢复需求、证明、用例和执行步骤的完整对应，修正R4.12管道退出码可能失真的配方，并纳入 `e6a4c19`、`65477f1` 两次输入变化。

## 依据与范围

- 正式需求采用[第一关口第六版](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988663001)，以及验收决定人2026年10月9日删除“校验子代理最终消息与文件逐字节相同”要求的调整。实施依据采用[第十六版完整执行计划](issue-66-implementation-plan.md)。
- 正式状态是教授目录内的 `套磁候选状态.json`，本地候选稿是 `套磁想法候选.md`，总览只是派生展示。凭据和校验交接文件不能替代正式状态。
- 只检查第三阶段及其直接改变的第四阶段读取入口。教授姓名按唯一处理。非 Codex 运行、同名消歧、断电或强制终止恢复、同教授并发写入、其他阶段改造和全仓回归不列入必测。第48号议题不是前提。
- 第一版14项合并为A—E五组。一次真实代理运行只检查代理职责；代码能够确定的输入、保存、修正和轮次计算，不再用模型重复证明。
- 第67号议题进入目标分支后，`refresh_scope=selected` 的唯一选择来源改为调用者通过 `--selection` 明确传入的教授目录内 `套磁选择.json`。缺少 `--selection` 必须以 `invalid_params` 失败，即使项目级旧版 `教授研究/套磁选择.json` 存在也不得回退读取。这一变化只重开A组第四阶段读取和C组显式选择检查。
- 已有且范围外的内容问题须报告，但不直接判为本次流程目标失败。`01b52d1` 上的 `EarlyMachineOutputGateTests.test_every_json_agent_front_loads_single_message_protocol` 失败已由 `e6a4c19` 修复。当前 `65477f1` 的持续集成在979项中的 `test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection` 因两次合法重建的动态渲染时间相差1秒而失败。产品业务行没有差异，因此分类为测试实现及 `RECIPE` 缺陷；现已把该断言改为排除以 `> ` 开头的动态时间行后比较全部业务行，修复后文件对象为 `3d5a38bfdd5dc12d53f3e78c07153f1fca9a94e5`。当前候选尚未执行修复后的正式检查，不得写成通过。

## R4.14重开依据

R4.13的第二关通过声明撤销。重开类别为 `REVIEW_DEFECT` 和 `RECIPE`，并有两次新的输入提交。

1. R4.12展示的命令把 `uv ... | tee ...` 后的 `$?` 当作测试退出码；若测试失败而 `tee` 成功，记录仍可能是0，存在错误通过的具体路径。R4.13虽改成 `if ... | tee`，却在命令前要求产品提交之后只能变化一个测试文件和两份计划文件；`e6a4c19` 已合法修改校验代理，所以该前置条件在当前提交必然失败。
2. R4.13压缩正文时，把R66-6、R66-10旧调用兼容、COMP66-1和D组批量失败清理等已确认要求的直接对应删掉；又声称R4.4—R4.11完整步骤已移入两个历史文件，但这些文件没有R4.11安装、请求和结果记录。执行人无法只依赖唯一当前计划完成复核。
3. `e6a4c19` 改变校验代理正文，直接影响D组旧只读调用兼容和E组安装件完成报告契约；`65477f1` 又改变计划输入。A、B、C的产品入口和既有断言没有变化，已有通过结果仍可按下文逐项复用。
4. R4.12的实际六项输出明确为 `Ran 6 tests`、`OK`，所以退出码配方缺陷没有把该次实际失败误记为通过；六项结果可复用。R4.11的源文件、安装件和真实请求证据也保留。R4.14不授权重新运行正式测试或发送模型请求，只修复当前权威计划并重新进行第二关审核。
5. `65477f1` 的持续集成失败暴露出测试把动态渲染时间当作稳定业务内容。修复只收窄该断言的比较对象，没有改变产品入口或A—E业务要求；B组旧通过结果仍证明产品行为，修复后的当前断言必须在下一次A—D正式检查中重新取得结果。

## 唯一必测清单

| 组 | 业务目标 | 代表场景 | 通过条件 | 检查入口 |
| --- | --- | --- | --- | --- |
| A | 当前教授独立提交；两文件失败恢复；第四阶段读取指定教授 | 合法生成、总览人工改动、第二份文件安装失败、提交后清理失败、自身候选稿冲突、第四阶段指定甲 | 总览和其他教授不阻塞甲；提交前失败恢复旧两文件；提交后清理失败保留新两文件；自身冲突拒绝覆盖；第四阶段只读取甲的正式状态、教授本地选择和邮件输入 | 保存及第四阶段读取的确定性检查，配合必要源码核对 |
| B | 正式状态稳定重建总览；错误时不发布部分内容；旧身份兼容准确 | 甲乙同方向或同组编号、删除总览、一个状态损坏、总览冲突或写入失败、旧身份匹配一项／零项／多项 | 行、链接和排序正确，只使用已提交状态；错误时保留旧总览；唯一匹配只迁移身份，零项或多项在写总览前拒绝 | 重建和兼容入口，核对业务行及旧总览 |
| C | 凭据固定输入；修正只处理点名对象；保留跳过、修正和两轮上限 | 混传来源或摘要、重复准备、两轮结果、问题指向方向／组／文件、教授本地显式选择、缺少选择、旧项目级选择存在 | 同凭据消费原输入；错误不部分提交；修正不扩大；无关候选保留；第二轮后无第三轮；`selected` 只读明确传入的教授本地选择，缺少参数时不写文件 | 凭据、计划、提交和记录入口的确定性检查 |
| D | 固定写入、保存和记录传递同一校验原文；失败不推进状态 | 三种合法结论、特殊字符、单文件／批量映射、错教授／凭据／轮次／摘要、候选稿变化、既有文件、符号链接、写入或读回失败 | 完整对象语义保留；固定写入输出与文件逐字节相同，权限为 `0600`；保存不重排；记录只消费本教授条目；错误不推进状态或覆盖目标 | 正式写入、保存和记录入口；`jq` 核对对象，`cmp` 比较字节 |
| E | 根对话和命名子代理按实际结果推进流程 | 产品同步后的一次正常第三阶段请求，只检查实际通过或修正分支 | 生成子代理保存候选；校验子代理固定写入并只报告写入结果；根依次准备、保存、记录；需要时只修正一次；终态后尽力重建一次总览 | 源文件和安装件报告契约检查，加一次真实评估请求的可见动作和产物 |

## 需求、证明和用例对应

| 第一关要求 | 证明 | 直接用例与检查 | 当前证据 |
| --- | --- | --- | --- |
| R66-1、R66-2、R66-3 | A | `test_issue66_stage3_local_state` 的教授本地提交、成对安装失败恢复、提交后清理失败、自身候选冲突，以及三个第四阶段按方向读取用例 | 42项历史通过；R4.12三个第四阶段用例通过 |
| R66-4、R66-5、R66-6、R66-7、R66-8 | B | 同套件的总览重建、损坏状态拒绝、总览冲突、旧身份唯一／零项／多项匹配；源码核对重建不读写 `_contact_projections.json` | 42项历史通过，入口自产品提交后未变 |
| R66-9 | A、C | `test_issue66_validation_handoff`、`Stage3ValidationIngestTests`、三个显式选择用例；核对固定凭据、摘要、选择来源和零写入 | 42项历史通过；R4.12三个显式选择用例通过 |
| R66-10 | C、D、E | 普通生成、显式修正、跳过、两轮终态；`output_file` 存在时固定写入及不存在时旧只读返回；保存、记录和实际代理顺序 | 42项历史通过；R4.11源文件3项、安装件3项及一次真实请求通过 |
| COMP66-1a 正式状态结构和业务内容 | A、C | `test_issue66_stage3_local_state`、`test_pass_round_records_terminal_result_without_correction`、`test_fail_then_correction_then_pass_terminates_at_round_two` | 42项历史通过；产品入口未变 |
| COMP66-1b 候选、方向及跨方向组机器身份 | A、C | `test_cross_direction_issue_routes_to_the_exact_group_id`、`test_issue_in_second_direction_repairs_only_that_scope`、`test_correction_cannot_skip_or_add_scopes` | 42项历史通过；产品入口未变 |
| COMP66-1c `gap_refs` 和材料指纹 | C | `test_evidence_must_bind_the_current_render`、`test_replay_after_a_replaced_render_fails_closed`、`test_machine_fact_mutation_during_correction_fails_closed`、`test_prose_edit_on_an_unnamed_candidate_fails_closed` | 42项历史通过；产品入口未变 |
| COMP66-1d 输入指纹和既有校验记录 | C、D | `test_source_change_still_needs_refresh_before_correction`、`test_second_validator_round_requires_completed_correction`、`test_record_validation_returns_input_bytes_sha`；后者同时断言返回的观测摘要不写回正式状态或校验正文 | 42项历史通过；输入摘要补证通过 |
| COMP66-1e 凭据和交接信息不成为正式状态 | C、D | `test_fixed_writer_save_and_record_preserve_pass_bytes`、`test_save_copies_noncanonical_utf8_bytes_and_bad_digest_does_not_advance`，并在正式状态中断言无 `invocation_file`、`handoff_file`、`handoff_sha256`、`validation_input_sha256` 字段 | 42项历史通过；产品入口未变 |
| COMP66-1f 普通生成、显式修正和旧只读调用 | C、D | `test_pass_round_records_terminal_result_without_correction`、`test_fail_then_correction_then_pass_terminates_at_round_two`、`test_calls_without_output_file_keep_the_full_read_only_return_contract` | 前两项在42项历史结果内；旧调用须以当前源文件和安装件各3项契约检查重取结果 |

## 检查方法

### A：当前教授提交和第四阶段读取

保存入口在当前教授目录内提交候选稿与状态。总览人工改动不应再阻塞保存；其他教授状态和共享登记不应成为提交前提。第二份正式文件安装失败时返回 `local_pair_commit_failed`，两份文件都恢复旧字节；提交后的临时文件清理失败不能撤销已经提交的新两文件。自身候选稿发生人工冲突时拒绝覆盖。

第四阶段用甲、乙可区分的正式状态和选择检查：明确传入甲教授目录内的选择后，只生成甲的第四阶段产物，不混入乙或项目级旧版选择。该检查只调用对应入口，不运行后续邮件流程。

### B：总览重建和旧身份兼容

重建扫描现存正式状态，不从候选稿或共享登记补造事实。正常场景核对甲乙业务行、链接、编号和稳定排序。任一已扫描状态损坏时，重建必须拒绝且保留旧总览，不能发布缺少该教授的部分内容。源码还须确认重建不读取或写入旧共享登记 `_contact_projections.json`，正式写入目标只有总览文件。

总览冲突、写入失败和旧身份匹配沿用有效确定性结果。一个旧身份匹配只迁移身份并保留候选；零项或多项匹配在写总览前拒绝。源码核对重建唯一正式写入目标是总览。

### C：显式选择、修正范围和两轮上限

建立含两个方向的教授状态、教授本地选择和指向另一方向的项目级旧版选择。不传 `--selection` 调用 `stage3-plan --refresh-scope selected`，预期退出码为1、`reason_code=invalid_params`、不返回任务，候选状态、候选稿、教授本地第四阶段文件和项目级旧文件保持原字节。明确传入教授本地选择后，只产生其选中方向的任务。

同一夹具检查 `stage3-finalize --refresh-scope selected`：省略 `--selection` 必须在提交前以 `invalid_params` 失败；明确传入同一教授本地选择后，只替换选中方向并保留未选方向。计划阶段拒绝由 `test_02_selected_refresh_needs_an_explicit_selection_and_ignores_legacy` 检查；提交阶段拒绝和未选方向保留由 `test_03_scoped_finalize_with_the_local_selection_keeps_other_directions` 检查，两项合计落实本段要求。

固定问题记录检查修正任务集合。来源、渲染或机器事实变化时拒绝且不部分提交。普通生成和旧显式修正调用必须继续可用；首轮通过不修正；首轮失败只修正点名对象；修正通过或第二轮仍失败都进入终态，禁止第三轮。无关方向、组、候选和校验记录保持不变。

### D：校验原文的固定写入、保存和记录

固定写入文件是唯一正式校验原文。输入对象和写入文件用 `jq -e -s 'length == 2 and .[0] == .[1]'` 比较完整 JSON 对象。随后检查：

1. `stage3-write-validation` 的标准输出与指定输出文件用 `cmp -s` 比较。
2. `stage3-save-validation` 的源文件和交接文件用 `cmp -s` 比较，保存入口不得解析后重排。
3. `stage3-record-validation` 的返回摘要与保存结果一致，教授轮次、问题和终态符合输入；绑定错误或原文缺失时不得推进状态。

三种合法结论都应能写入。写入成功不代表校验通过。批量结果逐教授消费完整对象，不拆成新对象；后一个教授写入失败时，已完成教授的正式文件保持不变，未完成目标不得残留临时文件。既有目标、符号链接、错教授、错凭据、错轮次、错摘要、候选稿变化和写入／读回失败都必须失败且不推进正式状态。不传 `output_file` 的旧调用保留完整只读返回，不产生文件。校验子代理最终消息只报告写入状态，不承担校验正文保存职责，也不与文件比较字节。

### E：实际代理流程

正式流程按仓库中的[技能流程](../.apm/skills/professor-contact/SKILL.md)和[校验代理指令](../.apm/agents/professor-contact-style-validator.agent.md)执行。测试人员只发一次正常第三阶段业务请求，运行后只读检查已有结果，不代替代理补执行遗漏命令。

| 顺序 | 执行者 | 预期动作 |
| --- | --- | --- |
| 1 | 根委派生成子代理 | 命名代理生成并自行调用 `stage3-plan`、`stage3-finalize`，返回本教授凭据 |
| 2 | 根 | 用生成结果中的凭据执行第一轮 `stage3-prepare-validation` |
| 3 | 根委派校验子代理 | 命名代理校验候选稿并对本轮 `output_file` 执行 `stage3-write-validation`；最终消息只含规定的写入报告字段 |
| 4 | 根 | 用同轮交接信息执行 `stage3-save-validation` |
| 5 | 根 | 用保存返回的摘要执行 `stage3-record-validation` |
| 6 | 根按记录结果决定 | 不需修正则停止；需要修正则只委派一次生成修正，再准备并完成第二轮；第二轮后停止 |
| 7 | 根 | 终态后执行一次 `stage3-rebuild-overview` 并如实汇报结果 |

每个入口执行失败时停止依赖动作。合法的 `verdict=fail` 仍须保存和记录，再由 `needs_correction`、`terminal` 决定后续。两轮后 `fail_after_2_rounds` 且没有第三轮，仍可成为流程合格的终态；候选内容结论另行记录。

正式拓扑只认固定证据适配器输出的 `dispatch.thread_relations[]`。一条 `tool=spawnAgent` 的正式关系算一次委派尝试；其 `sender_thread_id` 必须等于本次根线程，具体 `receiver_thread_ids[]` 才是正式子线程身份。`parent_thread_id`、提示词、角色自述及事件文字均不能证明所有权。子线程读取成功且有完成回合，才算该尝试完成。首轮直接终态必须恰有2次已完成委派，即1个生成子线程和1个校验子线程；发生一次修正必须恰有4次已完成委派，即2个生成子线程和2个校验子线程。尝试数、完成数或角色配比任何一项不符都是产品流程失败；适配器无法建立正式所有权或完成性时是证据无效，不能猜测为产品失败。

E组只核对可见动作、返回结果、固定写入文件、教授最终状态和调用顺序，不从根的委派说明推断子代理实际收到的提示词。缺少必要观察时，把对应事实记为无法判断，不再次发送请求求取通过。

## 结果复用与当前影响

| 组 | 当前状态 | 依据 | 当前是否重跑 |
| --- | --- | --- | --- |
| A | 历史未受影响项通过；第四阶段三项通过 | A—D历史42项结果；R4.12三项第四阶段定向结果 | 否；证据缺失时只运行受影响项 |
| B | 历史产品行为通过；当前测试断言已修复，当前执行待定 | 旧结果仍证明产品业务行；`65477f1` 的失败属于动态时间行比较造成的测试实现及 `RECIPE` 缺陷，修复文件对象为 `3d5a38bfdd5dc12d53f3e78c07153f1fca9a94e5` | 是；随下一次A—D完整42项执行一次 |
| C | 历史未受影响项通过；显式选择三项通过 | A—D历史42项结果；R4.12三项显式选择定向结果 | 否；证据缺失时只运行受影响项 |
| D | 产品入口历史通过；当前代理契约待E组前置复核 | 42项历史通过；`e6a4c19` 只改变代理指令，直接触发完成报告和旧只读调用契约复核 | E组执行前运行3项源文件和3项安装件契约检查 |
| E | R4.11历史流程通过；当前提交尚未执行 | `e6a4c19` 改变真实安装代理正文，旧模型运行不能证明当前输入 | 第二关批准后按当前提交执行一次，不复用旧模型结论 |

旧产品提交 `6aa2c8b23f9a723fff1b862851eb49b72a4c9a1d` 重基为产品提交 `f053d913afce47abed5abade9bf6e2737179f497`。第67号议题的变化已由R4.12的A、C六项补证。`e6a4c19` 没有改变A—D的Python产品入口，却改变了E组真实安装并运行的校验代理正文；因此A、C和D组产品入口结果继续复用，D组代理契约与E组真实运行必须以当前安装件重新确认。`65477f1` 后新增两处测试修复：B组排除动态时间行后比较全部业务行，COMP66-1e补充临时凭据字段不得进入正式状态的直接断言。两处都必须随下一次A—D完整42项取得当前结果。

历史证据位置只用于结果追溯：A—D的旧结果见[结果历史](../test-plan/issue-66-results-history.md)，2026年10月7日的运行失败与重试见[运行尝试记录](../test-plan/issue-66-runtime-attempts-20261007.md)。R4.11的完整安装、请求和结果记录就在本文件下文，不能声称已移入上述历史文件。

## R4.14当前执行配方

以下配方是唯一当前入口。R4.14第二关审核本身不运行正式测试。由于本轮修复B组时间断言和COMP66-1e结构化断言，第二关批准后当前执行顺序明确为：先运行A—D完整42项，再运行D组源文件3项和安装件3项契约，最后发送一次E组真实请求。A、C六项只在R4.12证据丢失时补跑，不属于当前必跑。任何准备失败都停止，测试失败仍保存结构化结果、日志和真实退出码。

### A—D完整42项配方

```sh
set -eu
set -o pipefail
producer=$(pwd)
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/issue66-pr73-r414-local.XXXXXX")
reviewed_sha='65477f1203f08fe2371e0caa8d74f131e6bfc92b'
git -C "$producer" status --porcelain > "$run_dir/producer-status.txt"
test ! -s "$run_dir/producer-status.txt"
git -C "$producer" merge-base --is-ancestor "$reviewed_sha" HEAD
git -C "$producer" diff --name-only "$reviewed_sha"..HEAD > "$run_dir/reviewed-to-candidate-files.txt"
jq -Rn '[inputs] | sort' < "$run_dir/reviewed-to-candidate-files.txt" > "$run_dir/actual-files.json"
jq -n '[
  ".apm/skills/professor-contact/tests/test_issue66_r12_validation_input_sha.py",
  ".apm/skills/professor-contact/tests/test_issue66_stage3_local_state.py",
  ".apm/skills/professor-contact/tests/runtime/run_selected_unittests.py",
  ".apm/skills/professor-contact/tests/runtime/verify_issue66_stage3_runtime.py",
  ".apm/skills/professor-contact/tests/test_verify_issue66_stage3_runtime.py",
  "plan/issue-66-test-plan-review.md",
  "plan/issue-66-test-plan.md"
] | sort' > "$run_dir/allowed-files.json"
jq -e -s '.[0] == .[1]' "$run_dir/actual-files.json" "$run_dir/allowed-files.json" > /dev/null
git -C "$producer" rev-parse HEAD > "$run_dir/candidate-sha.txt"
printf '%s\n' "$reviewed_sha" > "$run_dir/reviewed-sha.txt"
printf '%s\n' 'issue-66-test-plan-new-rules-r4.14-2026-10-10' > "$run_dir/plan-version.txt"
while IFS=' ' read -r expected file_path; do
  actual=$(git -C "$producer" hash-object "$file_path")
  test "$actual" = "$expected"
  jq -n --arg path "$file_path" --arg expected "$expected" --arg actual "$actual" \
    '{path:$path,expected_blob:$expected,actual_blob:$actual}'
done > "$run_dir/test-objects.jsonl" <<'OBJECTS'
3d5a38bfdd5dc12d53f3e78c07153f1fca9a94e5 .apm/skills/professor-contact/tests/test_issue66_stage3_local_state.py
62c1f8818dcf0fcebb51dd9457db3be2265c1459 .apm/skills/professor-contact/tests/test_issue66_validation_handoff.py
761c68507b0d295ca830bc5c518ab35d0aac6bdf .apm/skills/professor-contact/tests/test_stage3_validation_refine.py
e5d715d389abd2fe2640b7e2cbd36a126d5197bd .apm/skills/professor-contact/tests/test_issue66_r12_validation_input_sha.py
0c4cb72dd987009eefd801cf90686f7062758bdc .apm/skills/professor-contact/tests/runtime/run_selected_unittests.py
dd50ce598effa7f7a0f56fac886a2af3de95309f .apm/skills/professor-contact/tests/runtime/verify_issue66_stage3_runtime.py
c0c7250022cdccca3ef2a4427c49ff2018e07009 .apm/skills/professor-contact/tests/test_verify_issue66_stage3_runtime.py
1a0b07fe8cfaf37765df459892b5bcb589c69a38 .apm/skills/professor-contact/tests/test_contact_state.py
6939e918edadbe7763ebd1db14e3fc2363d391b8 .apm/skills/professor-contact/tests/test_stage3_direction_groups.py
OBJECTS
cd "$producer/.apm/skills/professor-contact/tests"
if UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python \
  runtime/run_selected_unittests.py --expected-count 42 --result "$run_dir/local-result.json" \
  test_issue66_stage3_local_state \
  test_issue66_validation_handoff \
  test_stage3_validation_refine.Stage3ValidationIngestTests \
  test_issue66_r12_validation_input_sha.Issue66RecordValidationInputShaTests \
  test_contact_state.TestRunnerBasics.test_05e_overview_manual_edit_does_not_block_local_finalize \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_ordinary_selection_joins_by_direction_id \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_exactly_migrates_v1_candidate_state_with_pack_mapping_without_stage3_rerun \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_partial_other_professor_rerun_preserves_existing_selection_and_email \
  2>&1 | tee "$run_dir/local-tests.log"; then
  test_exit=0
else
  test_exit=$?
fi
printf '%s\n' "$test_exit" > "$run_dir/local-tests.exit"
test "$test_exit" -eq 0
jq -e '.status == "passed" and .expected_count == 42 and .test_count == 42
  and .failures == 0 and .errors == 0 and .successful == true' \
  "$run_dir/local-result.json" > /dev/null
```

前置条件固定审核提交、干净工作树、恰好七个允许变化文件及九个测试对象；不是包含关系。固定运行器通过 `unittest` 结果对象在执行前核对收集数，执行后写实际运行数、失败数、错误数、跳过数和成功布尔值；配方只读该结构化JSON和进程退出码。该集合直接覆盖本计划A—D的本地状态、总览、凭据、修正、固定写入、批量清理、保存和记录检查。命令错误、数量不为42或任一断言失败时保留证据并停止；不能删减用例、改变输入或重复运行求取通过。

### A、C六项补证配方

配方用于R4.12证据丢失时复核六项补证；候选相对 `65477f1` 只允许本轮两份测试修复、结构化运行器、判定器及其预检和两份计划文件，并固定三个实际测试对象。若有其他文件变化，先重新做影响分析。

```sh
set -eu
set -o pipefail
producer=$(pwd)
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/issue66-pr73-r414-affected.XXXXXX")
product_sha='f053d913afce47abed5abade9bf6e2737179f497'
test_sha='162843c1c843989fbf09b45fd808d5276c92b94d'
agent_sha='e6a4c19856c841f877fd082a5161cc083290156d'
reviewed_sha='65477f1203f08fe2371e0caa8d74f131e6bfc92b'
git -C "$producer" status --porcelain > "$run_dir/producer-status.txt"
test ! -s "$run_dir/producer-status.txt"
git -C "$producer" rev-parse HEAD > "$run_dir/pr-sha.txt"
git -C "$producer" merge-base --is-ancestor "$reviewed_sha" HEAD
git -C "$producer" diff --name-only "$reviewed_sha"..HEAD > "$run_dir/reviewed-to-candidate-files.txt"
jq -Rn '[inputs] | sort' < "$run_dir/reviewed-to-candidate-files.txt" > "$run_dir/actual-files.json"
jq -n '[
  ".apm/skills/professor-contact/tests/test_issue66_r12_validation_input_sha.py",
  ".apm/skills/professor-contact/tests/test_issue66_stage3_local_state.py",
  ".apm/skills/professor-contact/tests/runtime/run_selected_unittests.py",
  ".apm/skills/professor-contact/tests/runtime/verify_issue66_stage3_runtime.py",
  ".apm/skills/professor-contact/tests/test_verify_issue66_stage3_runtime.py",
  "plan/issue-66-test-plan-review.md",
  "plan/issue-66-test-plan.md"
] | sort' > "$run_dir/allowed-files.json"
jq -e -s '.[0] == .[1]' "$run_dir/actual-files.json" "$run_dir/allowed-files.json" > /dev/null
printf '%s\n' 'issue-66-test-plan-new-rules-r4.14-2026-10-10' > "$run_dir/plan-version.txt"
git -C "$producer" rev-parse \
  "$test_sha:.apm/skills/professor-contact/tests/test_contact_state.py" \
  > "$run_dir/test-contact-state.expected-blob.txt"
git -C "$producer" hash-object \
  .apm/skills/professor-contact/tests/test_contact_state.py \
  > "$run_dir/test-contact-state.actual-blob.txt"
cmp -s "$run_dir/test-contact-state.expected-blob.txt" \
  "$run_dir/test-contact-state.actual-blob.txt"
git -C "$producer" rev-parse \
  "$product_sha:.apm/skills/professor-contact/tests/test_stage3_direction_groups.py" \
  > "$run_dir/test-stage3-direction-groups.expected-blob.txt"
git -C "$producer" hash-object \
  .apm/skills/professor-contact/tests/test_stage3_direction_groups.py \
  > "$run_dir/test-stage3-direction-groups.actual-blob.txt"
cmp -s "$run_dir/test-stage3-direction-groups.expected-blob.txt" \
  "$run_dir/test-stage3-direction-groups.actual-blob.txt"
git -C "$producer" rev-parse \
  "$agent_sha:.apm/agents/professor-contact-style-validator.agent.md" \
  > "$run_dir/validator-agent.expected-blob.txt"
git -C "$producer" hash-object \
  .apm/agents/professor-contact-style-validator.agent.md \
  > "$run_dir/validator-agent.actual-blob.txt"
cmp -s "$run_dir/validator-agent.expected-blob.txt" \
  "$run_dir/validator-agent.actual-blob.txt"
cd "$producer/.apm/skills/professor-contact/tests"
if UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python \
  runtime/run_selected_unittests.py --expected-count 6 --result "$run_dir/affected-result.json" \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_ordinary_selection_joins_by_direction_id \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_exactly_migrates_v1_candidate_state_with_pack_mapping_without_stage3_rerun \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_partial_other_professor_rerun_preserves_existing_selection_and_email \
  test_contact_state.Issue67AdjacentStateTests.test_01_stage3_selected_refresh_scopes_from_the_professor_local_selection \
  test_contact_state.Issue67AdjacentStateTests.test_02_selected_refresh_needs_an_explicit_selection_and_ignores_legacy \
  test_contact_state.Issue67AdjacentStateTests.test_03_scoped_finalize_with_the_local_selection_keeps_other_directions \
  2>&1 | tee "$run_dir/affected-tests.log"; then
  test_exit=0
else
  test_exit=$?
fi
printf '%s\n' "$test_exit" > "$run_dir/affected-tests.exit"
test "$test_exit" -eq 0
jq -e '.status == "passed" and .expected_count == 6 and .test_count == 6
  and .failures == 0 and .errors == 0 and .successful == true' \
  "$run_dir/affected-result.json" > /dev/null
```

预期为6项、退出码0，并由固定运行器的结构化结果机器核对数量和结果。前置检查要求候选包含 `65477f1`，其后恰好是列出的七个文件变化，并要求 `test_contact_state.py`、`test_stage3_direction_groups.py` 和校验代理文件分别与已审核提交的Git对象一致。任一核对失败都在运行前停止。

### D组代理契约和E组实际代理配方

本配方只在第二关批准后执行一次。产品和代理输入固定为 `65477f1203f08fe2371e0caa8d74f131e6bfc92b`；候选相对此提交只允许两份计划文件、两份测试修复、结构化测试运行器、固定判定器及其预检变化。源文件检查、证据适配器预检、安装或安装件检查失败时不发送请求。

```sh
set -eu
set -o pipefail
producer=$(pwd)
reviewed_sha='65477f1203f08fe2371e0caa8d74f131e6bfc92b'
fixture_sha='a96c239cca0e1e07eb142089e4d379baf4072277'
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/issue66-pr73-r414-eval.XXXXXX")
consumer="$run_dir/consumer"
fixture_source="$producer/../skills-test-fixtures"
fixture_repo="$run_dir/skills-test-fixtures"
cleanup_issue66() {
  cleanup_status=ok
  rm -rf "$consumer" || cleanup_status=failed
  if test -d "$fixture_repo"; then
    git -C "$fixture_source" worktree remove --force "$fixture_repo" || cleanup_status=failed
  fi
  printf '%s\n' "$cleanup_status" > "$run_dir/cleanup-status.txt"
}
trap cleanup_issue66 EXIT
git -C "$producer" status --porcelain > "$run_dir/producer-status.txt"
test ! -s "$run_dir/producer-status.txt"
git -C "$producer" merge-base --is-ancestor "$reviewed_sha" HEAD
git -C "$producer" diff --name-only "$reviewed_sha"..HEAD > "$run_dir/reviewed-to-candidate-files.txt"
jq -Rn '[inputs] | sort' < "$run_dir/reviewed-to-candidate-files.txt" > "$run_dir/actual-files.json"
jq -n '[
  ".apm/skills/professor-contact/tests/test_issue66_r12_validation_input_sha.py",
  ".apm/skills/professor-contact/tests/test_issue66_stage3_local_state.py",
  ".apm/skills/professor-contact/tests/runtime/run_selected_unittests.py",
  ".apm/skills/professor-contact/tests/runtime/verify_issue66_stage3_runtime.py",
  ".apm/skills/professor-contact/tests/test_verify_issue66_stage3_runtime.py",
  "plan/issue-66-test-plan-review.md",
  "plan/issue-66-test-plan.md"
] | sort' > "$run_dir/allowed-files.json"
jq -e -s '.[0] == .[1]' "$run_dir/actual-files.json" "$run_dir/allowed-files.json" > /dev/null
git -C "$producer" rev-parse HEAD > "$run_dir/candidate-sha.txt"
printf '%s\n' "$reviewed_sha" > "$run_dir/product-sha.txt"
printf '%s\n' 'issue-66-test-plan-new-rules-r4.14-2026-10-10' > "$run_dir/plan-version.txt"
git -C "$fixture_source" worktree add --detach "$fixture_repo" "$fixture_sha" > "$run_dir/fixture-worktree.log" 2>&1
test "$(git -C "$fixture_repo" rev-parse HEAD)" = "$fixture_sha"
test -z "$(git -C "$fixture_repo" status --porcelain)"
jq -e '.contract_id == "skills-test-fixtures/codex-eval-adapter@15"' \
  "$fixture_repo/configs/codex-eval-adapter-contract.json" > /dev/null
printf '%s\n' "$fixture_sha" > "$run_dir/fixture-repo-sha.txt"
printf '%s\n' 'no' > "$run_dir/fixture-repo-dirty.txt"
printf 'issue66-r414-%s\n' "$(date -u +%Y%m%dT%H%M%SZ)" > "$run_dir/fixture-run-id.txt"
cd "$producer/.apm/skills/professor-contact/tests"
if UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -B \
  runtime/run_selected_unittests.py --expected-count 3 \
  --result "$run_dir/source-contract-result.json" \
  test_issue66_validator_report_contract.Issue66ValidatorReportContractTests.test_output_file_completion_reports_have_exact_fields_and_no_validation_body \
  test_issue66_validator_report_contract.Issue66ValidatorReportContractTests.test_missing_writer_reason_code_defaults_to_validation_write_failed \
  test_issue66_validator_report_contract.Issue66ValidatorReportContractTests.test_calls_without_output_file_keep_the_full_read_only_return_contract \
  2>&1 | tee "$run_dir/source-contract-tests.log"; then
  source_exit=0
else
  source_exit=$?
fi
printf '%s\n' "$source_exit" > "$run_dir/source-contract-tests.exit"
test "$source_exit" -eq 0
jq -e '.status == "passed" and .expected_count == 3 and .test_count == 3
  and .failures == 0 and .errors == 0 and .successful == true' \
  "$run_dir/source-contract-result.json" > /dev/null
mkdir -p "$consumer"
cd "$consumer"
apm --version > "$run_dir/apm-version.txt"
apm install "ScholarWorkflow/professor-contact#$reviewed_sha" --target codex > "$run_dir/apm-install.log" 2>&1
codex --version > "$run_dir/codex-version.txt"
validator_agent="$consumer/.codex/agents/professor-contact-style-validator.toml"
test -f "$validator_agent"
cd "$producer/.apm/skills/professor-contact/tests"
if PROFESSOR_CONTACT_VALIDATOR_AGENT="$validator_agent" \
  UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -B \
  runtime/run_selected_unittests.py --expected-count 3 \
  --result "$run_dir/installed-contract-result.json" \
  test_issue66_validator_report_contract.Issue66ValidatorReportContractTests.test_output_file_completion_reports_have_exact_fields_and_no_validation_body \
  test_issue66_validator_report_contract.Issue66ValidatorReportContractTests.test_missing_writer_reason_code_defaults_to_validation_write_failed \
  test_issue66_validator_report_contract.Issue66ValidatorReportContractTests.test_calls_without_output_file_keep_the_full_read_only_return_contract \
  2>&1 | tee "$run_dir/installed-contract-tests.log"; then
  installed_exit=0
else
  installed_exit=$?
fi
printf '%s\n' "$installed_exit" > "$run_dir/installed-contract-tests.exit"
test "$installed_exit" -eq 0
jq -e '.status == "passed" and .expected_count == 3 and .test_count == 3
  and .failures == 0 and .errors == 0 and .successful == true' \
  "$run_dir/installed-contract-result.json" > /dev/null
if UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -B \
  runtime/run_selected_unittests.py --expected-count 41 \
  --result "$run_dir/evidence-preflight-result.json" \
  test_verify_issue66_stage3_runtime 2>&1 | tee "$run_dir/evidence-preflight.log"; then
  preflight_exit=0
else
  preflight_exit=$?
fi
printf '%s\n' "$preflight_exit" > "$run_dir/evidence-preflight.exit"
test "$preflight_exit" -eq 0
jq -e '.status == "passed" and .expected_count == 41 and .test_count == 41
  and .failures == 0 and .errors == 0 and .successful == true' \
  "$run_dir/evidence-preflight-result.json" > /dev/null
program_root="$consumer/fixture-program"
UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python \
  "$producer/.apm/skills/professor-contact/tests/runtime/prepare_issue55_stage3_fixture.py" \
  --program-root "$program_root" \
  --output "$run_dir/fixture-manifest.json" > "$run_dir/fixture-build.json" 2>&1
test -s "$run_dir/fixture-manifest.json"
UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -c 'import sys; from pathlib import Path; template=Path(sys.argv[1]).read_text(encoding="utf-8"); root=sys.argv[2]; assert template.count("{{PROGRAM_ROOT}}") == 1; Path(sys.argv[3]).write_text(template.replace("{{PROGRAM_ROOT}}", root), encoding="utf-8")' \
  "$producer/.apm/skills/professor-contact/tests/runtime/prompts/issue55-stage3-routing.txt" \
  "$program_root" "$run_dir/eval-prompt.txt"
test -s "$run_dir/eval-prompt.txt"
prompt=$(< "$run_dir/eval-prompt.txt")
command="--model gpt-5.6-luna --config 'model_reasoning_effort=\"low\"' --json --skip-git-repo-check --sandbox workspace-write --cd '$consumer' --config 'projects={\"$consumer\"={trust_level=\"trusted\"}}' -- '$prompt'"
jq -n --arg command "$command" '{command:$command,timeout:1200}' > "$run_dir/eval-request.json"
jq -e '.timeout == 1200
  and (.command | contains("--model gpt-5.6-luna"))
  and (.command | contains("model_reasoning_effort=\\\"low\\\""))' \
  "$run_dir/eval-request.json" > /dev/null
jq -n \
  --arg product_sha "$reviewed_sha" \
  --arg fixture_repo_sha "$fixture_sha" \
  --arg fixture_run_id "$(cat "$run_dir/fixture-run-id.txt")" \
  --arg consumer "$consumer" \
  --arg install_command "apm install ScholarWorkflow/professor-contact#$reviewed_sha --target codex" \
  --argjson generated_artifacts "$(cd "$consumer" && rg --hidden --no-ignore --files -0 | sort -z | xargs -0 shasum -a 256 | jq -Rn '[inputs]')" \
  '{product_sha:$product_sha,fixture_repo_sha:$fixture_repo_sha,fixture_repo_dirty:"no",
    fixture_run_id:$fixture_run_id,consumer:{path:$consumer,newly_created:true,manual_patch:"no",
    install_command:$install_command,generated_artifacts:$generated_artifacts}}' \
  > "$run_dir/run-provenance.json"
```

上述41项预检使用与 `codex-eval-adapter@15` 相同的 `app_server_events` 驼峰字段和 envelope 形状，固定验证判定器的四个条件：文件可执行且能读取固定输入（可执行）；只读合成对象，不发送请求、不改业务夹具（隔离）；每条分类都输出 `classification` 和 `reason`，`PASS` 总览另含轮次、委派尝试数、完成数和角色数，动作错误的对应理由含 `action` 或 `actions`（可观察）；同一判定器必须区分完整合法证据 `PASS`、完整证据下缺动作／错执行者／动作失败／错交接的产品 `FAIL`、委派或完成证据缺失及实际模型不符的 `INVALID_EVIDENCE`、运行未完成的 `BLOCKED`、请求未进入的 `CASE_NOT_STARTED`。正例覆盖1轮和2轮合法拓扑；反例还证明两轮不能复用首轮子线程、每个正式子线程只能有一个完成回合且只有一条助手消息、首轮固定教授目录、程序根、用户资料路径与摘要、刷新范围必须全部绑定、生成报告凭据必须被提交／准备／修正持续消费、固定教授与方向不能漂移、每轮交接目录和三类文件必须独占且连续、交接和校验摘要不得缺失、记录作用域必须绑定轮次与修正结果、最终状态不得多出方向、组或全局问题、校验子线程只能有一条完成报告、根最终报告必须包含固定夹具的实际重建总览路径、缺少记录动作或额外进入第四阶段都会判产品失败、子线程必须在根线程继续保存前完成。畸形生成报告、根报告及正式receiver只会得到稳定分类，不会使配方崩溃。所有非固定写入入口还同时核对结构化 `status=ok`，防止shell吞掉非零退出码。预检同时固定分类优先关系：运行未完成优先记 `BLOCKED`，适配器或事件序号无效优先记 `INVALID_EVIDENCE`，不能被同一响应中的命令失败覆盖。辅助命令 `echo contact_state.py stage3-plan` 同时含脚本名和子命令也不会被当作产品动作；只认shell解包后由Python解释器或脚本入口实际执行的子命令。任一结果不符即在发送请求前停止。

判定器还把每条产品命令的 `cwd` 与脚本路径解析成绝对路径，要求实际执行本次消费者 `.agents/skills/professor-contact/scripts/contact_state.py`；同名假脚本不能作为已安装产品证据。所有会改变来源、凭据、交接和输出的敏感选项都必须恰好出现一次，禁止判定器核对第一个值而命令行解析器实际消费最后一个值。

保留上述绝对路径 `run_dir`，到已配置的评测服务工作区根目录执行且只执行一次：

```sh
curl_exit=0
http_status=$(direnv exec . sh -c '
  set -eu
  case "${EVAL_PORT:-}" in
    ""|*[!0-9]*) exit 1 ;;
  esac
  curl --silent --show-error --output "$1" --write-out "%{http_code}" \
    -H "Content-Type: application/json" --data-binary @"$2" \
    "http://127.0.0.1:${EVAL_PORT}/eval"
' issue66-r414-eval "$run_dir/eval-response.json" "$run_dir/eval-request.json") || curl_exit=$?
printf '%s\n' "$http_status" > "$run_dir/http-status.txt"
printf '%s\n' "$curl_exit" > "$run_dir/curl-exit.txt"
```

`CASE_STARTED` 的唯一边界是：本次唯一 `/eval` 已返回HTTP 200，响应是有效JSON，并同时含非空根 `thread_id`、非空 `turn_id` 和本次捕获的非空 `events`。边界之前的传输或格式失败记 `CASE_NOT_STARTED`；边界之后运行未正常完成记 `BLOCKED`；证据适配器缺少正式所有权、角色或完成信息记 `INVALID_EVIDENCE`；只有证据完整后缺少必需动作、次数、顺序、文件字节或报告字段才记产品 `FAIL`。五种终态 `PASS`、`FAIL`、`INVALID_EVIDENCE`、`BLOCKED`、`CASE_NOT_STARTED` 互斥，任何一次运行只能记录一种。

HTTP 200且满足 `CASE_STARTED` 后执行固定证据适配器和判定器：

```sh
jq -n --arg model 'gpt-5.6-luna' --arg reasoning 'low' \
  --argjson request "$(cat "$run_dir/eval-request.json")" \
  '{model:$model,reasoning:$reasoning,request:$request}' > "$run_dir/resolved-config-before.json"
if test "$curl_exit" -eq 0 && test "$http_status" = 200 \
  && jq -e '.output.thread_id | type == "string" and length > 0' "$run_dir/eval-response.json" > /dev/null \
  && jq -e '.output.turn_id | type == "string" and length > 0' "$run_dir/eval-response.json" > /dev/null \
  && jq -e '.output.events | type == "array" and length > 0' "$run_dir/eval-response.json" > /dev/null; then
  jq -e '.output as $output
    | [.output.app_server_events[]
       | select(.message.method == "thread/started"
         and .message.params.thread.id == $output.thread_id)
       | {model:.message.params.thread.model,
          reasoning:.message.params.thread.reasoningEffort,
          cli_version:.message.params.thread.cliVersion}]
    | if length == 1 and .[0].model == "gpt-5.6-luna"
         and .[0].reasoning == "low" then .[0]
      else error("resolved model or reasoning mismatch") end' \
    "$run_dir/eval-response.json" > "$run_dir/resolved-config-after.json" || true
  adapter_exit=0
  if UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python \
    "$fixture_repo/scripts/parse_codex_eval_evidence.py" \
    --contract "$fixture_repo/configs/codex-eval-adapter-contract.json" \
    --eval-response "$run_dir/eval-response.json" \
    --expected-agent professor-contact-idea-generator \
    --expected-agent professor-contact-style-validator \
    --output "$run_dir/fixture-evidence.json"; then
    adapter_exit=0
  else
    adapter_exit=$?
    printf '{}\n' > "$run_dir/fixture-evidence.json"
  fi
else
  adapter_exit=1
  printf '{}\n' > "$run_dir/fixture-evidence.json"
  printf '{}\n' > "$run_dir/resolved-config-after.json"
fi
printf '%s\n' "$adapter_exit" > "$run_dir/adapter-exit.txt"
verdict_exit=0
if UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python \
  "$producer/.apm/skills/professor-contact/tests/runtime/verify_issue66_stage3_runtime.py" \
  --response "$run_dir/eval-response.json" \
  --adapter "$run_dir/fixture-evidence.json" \
  --fixture-manifest "$run_dir/fixture-manifest.json" \
  --http-status-file "$run_dir/http-status.txt" \
  --curl-exit-file "$run_dir/curl-exit.txt" \
  --output "$run_dir/issue66-verdict.json"; then
  verdict_exit=0
else
  verdict_exit=$?
fi
printf '%s\n' "$verdict_exit" > "$run_dir/verdict-exit.txt"
jq -e '.classification == "PASS" or .classification == "FAIL"
  or .classification == "INVALID_EVIDENCE" or .classification == "BLOCKED"
  or .classification == "CASE_NOT_STARTED"' "$run_dir/issue66-verdict.json" > /dev/null
jq -e '.classification == "PASS"' "$run_dir/issue66-verdict.json" > /dev/null
```

判定器只消费原始响应、`codex-eval-adapter@15` 的结构化输出、固定夹具清单和仍在本次消费者／交接目录中的文件。它以 `sender_thread_id` 核对根所有权，以正式 `spawnAgent` relation条数计委派尝试，以属于正式子线程的唯一 `turn/completed` 计完成拓扑；`child_thread_reads` 只提供正式线程的持久角色，不能替代完成事件。`@15` 没有冻结relation序号与子线程动作的先后，因此不从relation的 `runtime_seq` 推断这种因果顺序；只用子线程命令、唯一完成回合和根线程下一依赖命令的序号核对实际先后。判定器只从 `item/completed` 的 `commandExecution` 解析由Python解释器或脚本入口实际执行的 `contact_state.py` 子命令，其他子命令也会进入动作序列并使E组失败，说明文字或辅助命令不会冒充产品动作。它核对1轮时2个子线程、修正时4个子线程及生成／校验各半；按 `runtime_seq` 和 `threadId` 核对每轮 `plan → finalize → prepare → write → save → record` 的执行者、全链顺序、轮次、同一调用凭据、固定教授和方向、独占交接目录、三类交接路径及摘要，终态后恰好一次总览重建；比较固定写入标准输出、`validator-output.json` 和保存后的 `validation-result.json` 字节；从生成和校验子线程各自唯一的完成回合检查实际报告，从固定夹具路径检查教授正式状态的轮次、结果、空待处理集合及教授本地与旧程序级第四阶段禁止产物，从根完成回合检查实际重建总览路径已经报告。判定完成后用 `jq` 读取唯一分类，不凭日志关键词人工改判。

三段命令在同一shell内连续执行，使变量和退出清理保持有效；中途任何失败也由 `trap` 删除消费者和临时夹具工作树并记录结果。运行目录保留请求、原始响应、请求前后配置、Codex和APM版本、产品及夹具提交、安装命令、生成文件清单、`newly_created:true`、`manual_patch:"no"`、适配器结果、判定结果、日志、退出码和清理记录，不上传临时目录。

## 当前结果记录

R4.11历史E组在 `/private/tmp/issue66-pr73-r411.ZRrCVc` 执行，固定产品提交为 `6aa2c8b23f9a723fff1b862851eb49b72a4c9a1d`，APM CLI为 `0.29.0`。源文件契约3项通过；首次安装因依赖克隆出现 TLS `unexpected EOF` 失败，用户授权的一次全新目录重试安装成功；安装件契约3项通过。随后只发送一次1200秒的 `/eval` 请求，HTTP为200、`curl`退出码0，响应 `passed=true`、运行退出码0、`termination_reason=completed`，含2016条应用服务事件和4个正式子线程。

该历史运行中，第一轮生成、准备、固定写入、保存和记录成功，记录为 `fail`、3个阻塞问题、`needs_correction=true`、`terminal=false`；只触发一次修正。第二轮按相同顺序成功，记录为 `pass_with_minor`、0个阻塞问题、`needs_correction=false`、`terminal=true`，没有第三轮。两轮完成报告只含规定写入字段；两轮固定写入输出与 `validator-output.json`、以及该文件与保存后的 `validation-result.json` 共4次 `cmp` 都为0。终态后总览只重建一次，最终状态为 `DIR00001=pass`、第2轮、`issues=[]`。历史E组流程通过，内容结论为 `pass_with_minor`。由于 `e6a4c19` 后来改变校验代理正文，该结果不再作为当前E组通过结论。

R4.12在 `/private/tmp/issue66-pr73-r412.OMKPuO` 执行上述同一六项测试。测试实现提交为 `162843c1c843989fbf09b45fd808d5276c92b94d`，产品提交为 `f053d913afce47abed5abade9bf6e2737179f497`。输出为 `Ran 6 tests in 5.703s`、`OK`，退出码0；运行目录保留计划版本、提交 SHA、完整日志、退出码和依赖缓存，临时产物未加入仓库。

A组三项确认第四阶段按方向读取指定教授。C组三项确认：项目级旧版选择存在且指向另一方向时，省略 `--selection` 的计划和提交调用都以 `invalid_params` 拒绝，不生成任务或修改已记录文件；明确传入教授本地选择后只选择 `DIR00001`，提交后保留未选的 `DIR00002` 候选记录。

B及D组产品入口按上表复用。本轮没有运行正式测试，也没有发送模型请求。当前 `65477f1` 的持续集成运行 `37976309086` 共运行979项，1项失败、2项跳过；失败是B组总览测试把动态渲染时间当成稳定内容比较。该项已分类为测试实现及 `RECIPE` 缺陷并修复断言；修复后的当前结果仍待执行，因此不能把PR写成持续集成或B组当前检查通过。

R4.13第二关通过声明因漏审撤销。专用计划审核代理已对R4.14最终文件完成全范围只读复核，结论为计划设计通过、第二关步骤通过、审核完整、必须修改项为零。之后依次执行A—D完整42项、D组源文件3项与安装件3项契约、一次E组真实请求，再提交第三关。本记录不自行批准第三关或合并。

## 失败、重试与完成条件

- 命令启动失败、测试无法收集、运行证据缺少计划版本或提交 SHA，记为测试未执行或证据不足，不记产品失败。
- 断言正常运行后失败，保留日志并记对应业务检查失败。不得修改输入、删减断言或反复运行求取通过。
- R4.11模型请求只算历史结果。R4.14第二关通过后，当前输入先执行A—D完整42项，再执行D组源文件3项与安装件3项契约，前置均通过后才按E组配方发送一次正式请求；外部服务问题不能自行触发重试。
- 第二关口审核必须确认唯一必测清单、检查方法、复用理由、当前命令和失败条件一致。第三关口再核对实际运行对象、退出码和业务结果。
- 第二关完成条件是需求、证明、用例、配方和复用边界一一对应，执行人不需要拼接旧评论或旧计划。第三关完成条件是A—E每组都有通过、失败或无法判断的唯一当前结论，所有复用有提交和影响依据，当前A—D完整42项、D组3+3项契约及E组一次请求都有可追溯日志。持续集成和合并条件由实现及合并审核另行处理。
