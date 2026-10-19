# Issue #78：同名支持清理的测试计划与执行步骤

- Test plan revision：contact78-t3（2026-10-19）
- Proposed review status: pending
- Requirement：[#78](https://github.com/ScholarWorkflow/professor-contact/issues/78)，当前唯一执行计划 [contact78-r1](implementation-plan.md)（2026-10-19 已获执行计划审核批准）。
- 产品基线：`d5a4f751fb80de4819d4a1de3ee829db52cea6fc`；测试准备提交 `45c30fa8d405d1ef949cdaa308ef39355e420dc0`（本 PR 分支，只改测试与夹具）。产品修改尚未实施，全部必测项未执行；未来受测产品/测试 SHA 在执行时记录。
- [测试规则](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 决定范围；[项目共识](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d) 决定环境与隔离。

## 1. 必测清单

本清单以唯一姓名需求及本次直接修改为上限。目标只有清理同名特例、保留受影响普通行为；不运行同名输入，不新增同名强制拒绝测试。

| 项 | 业务目标 | 输入/场景 | 预期结果与检查方式 |
| --- | --- | --- | --- |
| T1 | 清理 Stage 0 专用分类并保留归属与事务 | 当前教授合法 bootstrap/select/resolve；旧数据含外教授、name/dir/preview 冲突、缺目录及绝对 preview；两位不同姓名教授各自选择和备注。 | 合法操作成功，旧不匹配条目不导入；源旧文件及另一教授状态不变。两份本地 target 与事务路径准确、互不覆盖。复用 `test_contact_targets.py` 的改后 3 项定向用例。清理完整性由 T5 静态核对，不新锁定内部分类字符串。 |
| T2 | Stage 1/2 夹具改名后普通身份保护不丢失 | 两位不同姓名的 preview/papers/target/snapshot；B stale/missing；A 正常 preflight/plan/finalize；合法生成 B proof 后误交 A；已绑定输入的 digest/history 变化。 | 本地状态与交接仍归各自 canonical 目录，错误绑定/变更失败且零写入，正常路径恢复后成功，其他教授与旧聚合不被读取/改写。复用改名方法、共享 helper 的直接消费者与既有 Stage 2 两个测试类。 |
| T3 | Stage 4 fixture 和说明清理不损失事务、ID 或失败隔离 | 不同姓名的双教授本地 pair；各自原三段 email ID；现有隔离 fixture 中一个合法、一个固定坏 candidate-state；无目录名字请求契约。 | 两笔普通事务保持独立；只消费每笔准确本地包。坏教授不写、不阻塞合法教授，历史 pair 不晋升；展示名不能冒充 canonical 目录。现有 CLI/文件断言和 2 项 agent 契约断言足够，不跑模型。 |
| T4 | Stage 5 移除专用拒绝时仍精确过滤、报缺失且只读 | 既有 discovery fixture：合法包与带姓名的越界包；分别无过滤、精确合法名、精确越界包名、一个不存在名字。 | 无过滤逐包独立返回；精确名字只返回对应行，越界包保持自己的错误行；无匹配保持 `needs_input/professor_not_found`；所有操作前后文件路径和字节不变。不创建两个同名教授。复用 `TestStage5ListInputDiscovery` 并补必要过滤断言。 |
| T5 | 当前代码、文案、fixture、安装源与要求一致 | 当前 diff，执行计划 §3 清单，Codex/OpenCode analyzer 的相关段落及实际 source manifests，当前 main/打开 PR。 | 不再存在有效的同名支持/拒绝/验收义务；通用身份 predicate、owner/原 ID、现有 projection source 与受管状态规则不变。静态逐项核对并引用相关现有契约测试；历史记录、不同用途“同名”和独立程序根样例不算残留缺陷。 |

不同姓名相同 `direction_id` / cross-group ID 的 Stage 3 fixture 已采用正确范围，Stage 5 partition 与 `choice_owner_ambiguous` 代码本轮不改。T5 核对其保留即可，不恢复已删除的 Stage 5 attribution 套件、不重复执行未受影响测试。若实际 diff 扩及这些行为，先说明具体影响并修订受影响清单，不能直接扩大执行。

## 2. 测试代码接线（已接线，待产品实现与第二关）

路径均相对 `.apm/skills/professor-contact/tests/`。沿用 `unittest` 和现有临时目录/断言，不新建测试平台或结果转换器。

- T1：保留 `ContactTargetsTests.test_issue64_t3_unattributable_legacy_entries_are_never_imported` 和 `test_issue64_t4_transaction_records_carry_canonical_identity`；原同名双教授用例改名为 `test_issue64_t4_professors_keep_separate_local_targets`，使用 `教授A` 与 `教授研究/other-lab/教授C` 两个不同姓名、不同合法目录。混合负例只去掉纯同名条目，保留 other-professor、path-conflicting、no-dir、absolute-preview 与零误导入断言；可解析但不匹配的条目按通用 `other_professor` 期望（该期望以 §3.1 产品修改为前提）。
- T2：`Stage1CandidateTests` 的两个 `test_issue64_t5_same_display_name_*` 已分别改名为 `test_issue64_t5_professors_keep_separate_snapshot_entries`、`test_issue64_t5_missing_entry_names_its_own_professor_dir`，第三位教授为 `教授C`；原 `same_name_professor` helper 改为姓名必填的 `professor_fixture`。保留 `test_issue65_stage1_professor_local_authority_and_isolation`，改用 `教授甲`/`教授乙`；`test_stage1_handoff_identity.Issue65Gate2Stage1Tests` 的两个 helper 调用同步新名，甲/乙不变。
- T2：`test_contact_state.Issue65Stage2BindingEnv` 默认 `DISPLAY=教授甲`、`B_DISPLAY=教授乙`，署名对照写入两位教授各自的条目；`Issue65Stage2BindingTests`（1 方法）与 `TestIssue64Stage2PlanBinding`（4 方法）落在不同姓名夹具上。sibling-proof 用例先以 B 的名字、B 的 target 生成合法 proof，再断言 A 的 plan 以 `invalid_params`（professor mismatch）拒绝且零写入；原同名下的 `preflight_inputs_changed` 终态不再适用。`test_stage1_handoff_identity` 与 `test_issue65_gate2_r24_regressions` 的既有甲/乙 override 未改。
- T3：`Issue67ProfessorLocalStage4Tests.test_06_two_professors_keep_two_local_states` 的第二位教授改为 `対照 教授`；`Issue67AdjacentStateTests.test_06_email_id_stays_the_three_part_identity_regardless_of_directory` 按每行教授自己的三段公式检查对应 `email_id`，不再假定两名教授同名同编号。
- T3：`tests/runtime/prepare_issue67_stage4_isolation_fixture.py` 为两位教授分别声明 `Alpha Professor` / `Beta Professor`，输入包与 manifest 逐教授写入姓名，顶层共享 `display_name` 字段删除并同步 `verify_issue32_e2e.py` 的只读回显；prompt 删除“显示名相同”指令，保留两个 canonical 目录与显式选择。`Issue67Stage4IsolationHarnessTests` 的四个相关方法改取所属 manifest/spec 的姓名，display-name 目录误绑定负例改用有效教授自己的显示名建立同名目录。
- T3/T5：`Issue67Stage4SelectionContractTests.test_canonical_professor_dir_is_the_per_professor_read_and_map_unit` 与 `Issue67Gate2R3SelectionContractTests.test_no_dir_structured_and_natural_language_inputs_remain_supported_per_request` 的同名正则替换为 canonical 事务边界、`精确(匹配|映射|绑定)` 与 `只结束对应请求` 断言；`Stage2PreflightContractTests.test_issue64_t7_preflight_proof_save_is_per_professor_transaction` 只去掉同名措辞，断言未变。
- T4：复用 `TestStage5ListInputDiscovery` 的合法包/带姓名越界包准备逻辑（提取为 `write_discovery_packs`），新增 `test_exact_professor_filter_preserves_matching_row_and_read_only_state` 与 `test_missing_professor_returns_needs_input_without_writes`；精确过滤与缺失返回都以退出码、结构化返回和文件不变为判据。

上列方法名与 §3.2 命令一致，静态解析核对见 §2.1；只有 T1 的通用分类期望以 §3.1 产品修改为前提，T2 的 sibling 拒绝（现有 `invalid_params`/professor mismatch 分支）与 T3 的文案正则在当前树上即成立，§3.2 修改后须保持匹配。

### 2.1 准备与静态预检记录（本地测试工程师，2026-10-19）

- 准备提交 `45c30fa8d405d1ef949cdaa308ef39355e420dc0`：只含 `.apm/skills/professor-contact/tests/` 下的测试代码、runtime 夹具、prompt 与只读 verifier 回显；未改产品脚本、agent/SKILL 说明或 `nix/`、`apm.yml`。
- 静态预检（未运行任何必测命令，未调用产品入口）：`python3 -m py_compile` 对 10 个 Python 改动文件通过（第 11 个改动文件是 prompt 文本，不属于 Python 源）；`unittest.TestLoader.loadTestsFromName` 解析 §3.2 的 19 个选择器全部命中，另单独解析 T4 的两个新方法，21 条选择器共 26 次加载，去重后 24 个用例（含 `TestIssue64Stage2PlanBinding` 的 4 个与 `TestStage5ListInputDiscovery` 的 3 个），无 `_FailedTest` 伪用例。
- 夹具自检（仓库外 `/tmp/contact78-tests.LftVeG/fixture-check`）：隔离夹具可生成；两位教授姓名互异且都不等于 canonical 目录 basename；逐教授输入包的 `professor`/`professor_dir` 与 manifest 记录一致；恰好一个坏 candidate-state，legacy 程序级包使用有效教授姓名；prompt 含两个 canonical 目录与两个 idea，不含“显示名相同/同名”。同一检查确认两个 Stage 4 文案选择器的新正则仍匹配当前 `professor-contact-selection.agent.md`，即选择器在产品说明修改前也可执行。
- 环境：`/run/current-system/sw/bin/python3` 3.14.7（CI 为 Python 3.12）；用例只用标准库与既有本地夹具，不需要 Nix、APM、Skills 安装、eval、模型、网络、Zotero 或用户资料。
- 运行目录 `/tmp/contact78-tests.LftVeG`（`tmp/`、`preflight.log`、`selectors.log`、`fixture_check.log`），按共识放在仓库外，不入库、不推送。
- 缺项：产品修改未实施，第二关未通过，因此 §3.2 的定向命令未执行（本角色不运行正式用例）；只有 T1 的通用分类期望尚待 §3.1 产品修改后验证，T2 的 sibling 拒绝与 T3 的文案正则在当前树上即成立（产品说明修改后须保持匹配）。

### 2.2 实现符合性审核记录（专用 implementation_reviewer，2026-10-19）

- 首次审核（对象 `45c30fa` + `1818f3e`，只读，未运行测试）：结论**完整**——§2 接线、§3 步骤与预检记录齐备，选择器到达目标业务边界，改名未削弱身份绑定/零写入/单故障/history-only legacy pair/只读发现覆盖，无同名专用分类、拒绝或支持残留，无超范围新增。提出 2 处记录偏差：①§2.1 把 `py_compile` 覆盖写成 11 个文件、把选择器计数写成 21 条/26 个用例；②把 T2 sibling 拒绝与 T3 文案正则写成以产品修改为前提。
- 处置（提交 `75236d8`，只改本文件）：①改为 10 个 Python 改动文件，§3.2 的 19 个选择器全部命中（另单独解析 T4 两个新方法，21 条选择器共 26 次加载、去重后 24 个用例）；②改为只有 T1 的通用分类期望以 §3.1 产品修改为前提，T2 的现有 professor mismatch 拒绝与 T3 的文案正则在当前树上即成立、说明修改后须保持匹配。测试接线仍为 `45c30fa`，未改动。
- 定向复核（对象 `75236d8`，同一审核角色）：问题 1、2 均已处理，未引入新错误，未发现新问题，结论**完整**；未变化的测试接线沿用首轮完整核对结论。
- 该结论只覆盖本角色的测试准备产物，不代表第二关步骤审核通过、第三关结果或合并批准；产品 §3.1/§3.2 仍未实施。

## 3. 有界执行步骤（接线已完成，待第二关确认后使用）

### 3.1 准备与隔离

1. 进入实际 `ScholarWorkflow/professor-contact` checkout，确认目标提交和 diff，只读记录 `git rev-parse HEAD` 与工作树状态。实现版本、测试版本不同则分别记录。不使用别人的未确认修改。
2. 使用仓库现有 Python 环境（CI 为 Python 3.12）；这些用例基于标准库/已有本地 fixture，不需要 Nix、APM、Skills 安装、eval、模型、网络、Zotero 或用户资料。只确认 Python 命令与已有依赖能运行，不做通用环境认证。
3. 创建仓库外唯一目录，例如 `RUN_ROOT=$(mktemp -d /tmp/contact78-tests.XXXXXX)`，`mkdir "$RUN_ROOT/tmp"`，设 `TMPDIR="$RUN_ROOT/tmp"`、`PYTHONDONTWRITEBYTECODE=1`。现有测试自行创建/清理其隔离临时状态；保留下面的日志。记录 checkout、Python 版本、实际 RUN_ROOT 和受测 SHA 即可。
4. 未通过步骤审核、选择器不可解析或 fixture 不自洽时，该项记未执行并交测试工程师；不运行正式命令来猜测接线是否正确。本计划阶段不执行本节。

### 3.2 定向命令

从 `.apm/skills/professor-contact/tests` 运行。每组一次，stdout/stderr 保存到 `$RUN_ROOT/Tn.log`，记录原始退出码；不以 `tee` 的退出码代替测试返回。下列选择器的接线状态见 §2。

```sh
python -m unittest -v \
  test_contact_targets.ContactTargetsTests.test_issue64_t3_unattributable_legacy_entries_are_never_imported \
  test_contact_targets.ContactTargetsTests.test_issue64_t4_professors_keep_separate_local_targets \
  test_contact_targets.ContactTargetsTests.test_issue64_t4_transaction_records_carry_canonical_identity \
  > "$RUN_ROOT/T1.log" 2>&1

python -m unittest -v \
  test_stage1_candidates.Stage1CandidateTests.test_issue64_t5_professors_keep_separate_snapshot_entries \
  test_stage1_candidates.Stage1CandidateTests.test_issue64_t5_missing_entry_names_its_own_professor_dir \
  test_stage1_candidates.Stage1CandidateTests.test_issue65_stage1_professor_local_authority_and_isolation \
  test_stage1_handoff_identity.Issue65Gate2Stage1Tests.test_issue65_stage1_professor_local_authority_and_isolation \
  test_contact_state.Issue65Stage2BindingTests \
  test_contact_state.TestIssue64Stage2PlanBinding \
  > "$RUN_ROOT/T2.log" 2>&1

python -m unittest -v \
  test_contact_state.Issue67ProfessorLocalStage4Tests.test_06_two_professors_keep_two_local_states \
  test_contact_state.Issue67AdjacentStateTests.test_06_email_id_stays_the_three_part_identity_regardless_of_directory \
  test_issue32_e2e_verifier.Issue67Stage4IsolationHarnessTests.test_frozen_prompt_identifies_both_professors_by_canonical_directory \
  test_issue32_e2e_verifier.Issue67Stage4IsolationHarnessTests.test_frozen_fixture_freezes_one_candidate_state_fault_and_history_only_pair \
  test_issue32_e2e_verifier.Issue67Stage4IsolationHarnessTests.test_isolation_checkpoint_passes_the_real_producer_isolation \
  test_issue32_e2e_verifier.Issue67Stage4IsolationHarnessTests.test_pair_bound_to_the_display_name_instead_of_the_directory_is_a_failure \
  test_stage4_selection_agent_contract.Issue67Stage4SelectionContractTests.test_canonical_professor_dir_is_the_per_professor_read_and_map_unit \
  test_issue67_gate2_r3.Issue67Gate2R3SelectionContractTests.test_no_dir_structured_and_natural_language_inputs_remain_supported_per_request \
  > "$RUN_ROOT/T3.log" 2>&1

python -m unittest -v test_contact_state.TestStage5ListInputDiscovery \
  > "$RUN_ROOT/T4.log" 2>&1

python -m unittest -v \
  test_stage1_stage2_contract.Stage2PreflightContractTests.test_issue64_t7_preflight_proof_save_is_per_professor_transaction \
  > "$RUN_ROOT/T5-contract.log" 2>&1
```

T5 其余是一次有界人工静态核对：对照执行计划 §3 检查完整 diff 及必要上下文，确认 `same_name_other_dir` / `professor_ambiguous` 不再是有效实现/要求；中文/英文同名检索仅作定位，逐个区分历史材料、无关同名对象、范围排除和未清理条款。核对两份 analyzer 对应段落以及既有 `apm.yml` / `nix/contact.nix` 来源关系，保留 runtime 特有差别。对当前 main/打开 PR 的相关片段做重引入检查，记录具体结论，不编辑其他 PR 或重新安装。

### 3.3 失败、重试与结果

- 每组结果区分通过、业务失败、无法判断、未执行；缺方法、导入错误、隔离准备错误是测试问题，不冒充业务通过。
- 断言失败先保留日志并定位。产品问题交产品实施者；fixture/步骤偏差交测试工程师修正，独立核对受影响步骤后再跑，不删除保护或放宽预期。
- 不为业务结果不满意而重试。只有已确认、已恢复的临时宿主故障（如进程被宿主中断或临时存储不可用）可原参数重试一次：先确认测试仅用了所属临时目录，再新建同样结构的独占 RUN_ROOT，保留两次日志。恢复未确认或再次失败即停止受影响组，继续可独立执行项。
- 输入、方法、fixture 或断言变化属于修订，不记为同条件重试。只复验受影响目标，未受影响结果在说明适用性后复用；文档/SHA 变化不自动要求重跑。
- 标准 unittest 日志与简短逐项结果足够；不新增统一 JSON、证据账本、固定内部原因码、来源证明或通用 harness 验收。已有 CI 自动运行按仓库规则处理，不再手动重复整仓套件。

## 4. 当前状态与交接

- 测试准备（本地测试工程师，2026-10-19）：§2 的选择器与夹具已在 `45c30fa` 完成接线，静态预检与夹具自检记录见 §2.1。第一关必测清单与第二关步骤仍待独立审核；本计划不自授 PASS。
- 产品/测试代码：产品脚本与说明未修改（待实施者按 contact78-r1 §3.1/§3.2 落地）；T1–T5 未执行，无第三关结果；§3.2 的定向命令尚未运行。
- 下一步：第二关按实际接线复核选择器、fixture 与步骤；产品实现后由本地执行工程师按 §3 定向执行。第三关只审核当前有效结果，未受影响的历史结果按版本复用。

修订说明：t2 按独立审核只修正 T4 错误行过滤输入（使用现有带姓名越界包，不能按姓名过滤解析失败且没有教授名的坏 JSON）与 T5 方法所属类；目标和其他步骤不变。t3 在已批准执行计划下完成 §2 测试代码接线与静态预检，记录实际提交与自检结果，并把 T2 sibling-proof 的终态改准为产品既有的 professor mismatch 拒绝；T1–T5 目标、输入与检查方式不变。t3 的实现符合性审核与两处记录更正见 §2.2（首次审核结论完整，定向复核结论完整）。
