# Issue #78：同名支持清理的测试计划与执行步骤

- Test plan revision：contact78-t2（2026-10-19）
- Proposed review status: pending
- Requirement：[#78](https://github.com/ScholarWorkflow/professor-contact/issues/78)，当前唯一执行计划 [contact78-r1](implementation-plan.md)。
- 产品基线：`d5a4f751fb80de4819d4a1de3ee829db52cea6fc`；未来受测产品/测试 SHA 在执行时记录，本轮只有文档，全部执行项未执行。
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

## 2. 测试代码接线（尚未实施）

路径均相对 `.apm/skills/professor-contact/tests/`。沿用 `unittest` 和现有临时目录/断言，不新建测试平台或结果转换器。

- T1：保留 `ContactTargetsTests.test_issue64_t3_unattributable_legacy_entries_are_never_imported` 和 `test_issue64_t4_transaction_records_carry_canonical_identity`；把原 `test_issue64_t4_same_display_name_professors_keep_separate_local_targets` 改名为 `test_issue64_t4_professors_keep_separate_local_targets`，使用不同名字/合法目录。混合负例只去掉纯同名条目，不去掉 path-conflicting 与零误导入断言。
- T2：`Stage1CandidateTests` 的两个 `test_issue64_t5_same_display_name_*` 分别改名为 `test_issue64_t5_professors_keep_separate_snapshot_entries`、`test_issue64_t5_missing_entry_names_its_own_professor_dir`。保留 `test_issue65_stage1_professor_local_authority_and_isolation`，同步 helper 显式名字与 `test_stage1_handoff_identity.Issue65Gate2Stage1Tests` 的调用。
- T2：`test_contact_state.Issue65Stage2BindingTests`（1 方法）与 `TestIssue64Stage2PlanBinding`（4 方法）使用不同姓名的默认 fixture。sibling-proof 方法以 B 名字/B target 生成成功 proof，再检验 A plan 拒绝；不得把 fixture 初始化失败当负例成功。`test_stage1_handoff_identity` 和 `test_issue65_gate2_r24_regressions` 的已有甲/乙 override 保持，静态核对其字段与 helper 兼容，不增加重复生命周期运行。
- T3：Stage 4 的原 `test_06_same_display_name_two_directories_keep_two_local_states` 改名为 `test_06_two_professors_keep_two_local_states`；`test_06_email_id_stays_the_three_part_identity_regardless_of_directory` 按每行教授原公式检查对应 ID，不能伪造相同 ID。改变共享 runtime fixture 的消费点时，使用每教授 spec/manifest 中的姓名。
- T3：运行既有 `Issue67Stage4IsolationHarnessTests` 的四个相关方法：prompt、frozen fixture、真实本地 producer 隔离正例、display-name 目录误绑定负例。它们是确定性本地测试，复用既有判定器；不增加 adapter、来源认证、历史重放或新判定逻辑。
- T3/T5：两个现有 Stage 4 文案契约方法只将同名正则替换为 canonical 事务边界、精确绑定和每请求失败隔离断言。analyzer preflight 证明路径方法保留断言，只去掉过时注释。
- T4：复用 `test_contact_state.TestStage5ListInputDiscovery.test_valid_and_escaped_packs_produce_one_json_document` 的合法包/带姓名越界包准备逻辑。新增 `test_exact_professor_filter_preserves_matching_row_and_read_only_state` 与 `test_missing_professor_returns_needs_input_without_writes`。合法过滤与带姓名越界包的精确过滤在首个新方法中以 subTest 检查；缺失检查依据已有正式缺失契约。测试只观察退出/结构化返回与文件不变。

新增/改名的方法名是本候选的接线目标，目前并不存在。实现后由独立审核者只读核对产品路径、fixture、自变量和断言，确认所有选择器可执行；若名称等价变更，更新本文件命令，不运行碰巧存在的替代套件。

## 3. 有界执行步骤（待接线与第二关确认后使用）

### 3.1 准备与隔离

1. 进入实际 `ScholarWorkflow/professor-contact` checkout，确认目标提交和 diff，只读记录 `git rev-parse HEAD` 与工作树状态。实现版本、测试版本不同则分别记录。不使用别人的未确认修改。
2. 使用仓库现有 Python 环境（CI 为 Python 3.12）；这些用例基于标准库/已有本地 fixture，不需要 Nix、APM、Skills 安装、eval、模型、网络、Zotero 或用户资料。只确认 Python 命令与已有依赖能运行，不做通用环境认证。
3. 创建仓库外唯一目录，例如 `RUN_ROOT=$(mktemp -d /tmp/contact78-tests.XXXXXX)`，`mkdir "$RUN_ROOT/tmp"`，设 `TMPDIR="$RUN_ROOT/tmp"`、`PYTHONDONTWRITEBYTECODE=1`。现有测试自行创建/清理其隔离临时状态；保留下面的日志。记录 checkout、Python 版本、实际 RUN_ROOT 和受测 SHA 即可。
4. 未通过步骤审核、选择器未接线或 fixture 不自洽时，该项记未执行并交测试工程师；不运行正式命令来猜测接线是否正确。本计划阶段不执行本节。

### 3.2 定向命令

从 `.apm/skills/professor-contact/tests` 运行。每组一次，stdout/stderr 保存到 `$RUN_ROOT/Tn.log`，记录原始退出码；不以 `tee` 的退出码代替测试返回。下列方法已在 §2 明确现有/待接线状态。

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

- 计划设计、第一关必测清单、第二关步骤：pending，等待独立审核；本候选不自授 PASS。
- 产品/测试代码：本轮未修改。T1–T5：未执行，无第三关结果。
- 下一步：审核者检查完整候选；实施者完成获批变更后，测试工程师补齐 §2 的明确接线，独立只读核对代码及步骤，执行者再按 §3 运行。第三关只审核当前有效结果，不要求重新证明未受影响的安装或历史过程。

修订说明：t2 按独立审核只修正 T4 错误行过滤输入（使用现有带姓名越界包，不能按姓名过滤解析失败且没有教授名的坏 JSON）与 T5 方法所属类；目标和其他步骤不变。
