# Issue #78：清理同名教授支持的执行计划

- Plan revision：contact78-r1（2026-10-19）
- Proposed review status: pending
- Requirement revision：[Issue #78](https://github.com/ScholarWorkflow/professor-contact/issues/78) 当前正文，更新时间 2026-10-05T19:02:47Z，2026-10-19 复读时无评论；用户本轮要求先准备执行计划与测试计划。
- Target repository revision：`ScholarWorkflow/professor-contact`，`main@d5a4f751fb80de4819d4a1de3ee829db52cea6fc`。
- Relevant upstream/runtime revision：N/A；本次不改依赖、运行时或安装方式。
- 规则：[项目共识](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[计划规则](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[测试规则](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)，2026-10-19 读取版本。
- 本文件是本任务唯一完整执行计划；测试目标与执行步骤仅见同目录 [test-plan.md](test-plan.md)。本次提交只含计划，不含产品或测试实现，不表示测试通过或允许合并。

## 1. 需求、范围与方案

本仓库以教授姓名唯一为业务前提。移除同名教授专用支持、分类、拒绝要求、说明和夹具，保留正常逐教授身份绑定、状态/事务/失败隔离以及不同姓名教授共享业务编号的能力。

整个 #78 不走快合：`_reliable_candidates` 的不匹配分类与 Stage 5 名字过滤的返回行为会改变，不能将它们视为机械文案修改。

采用“保留通用身份机制，只去掉同名特例；混合测试改用不同姓名”的方案。替代方案是只删文案/夹具，但会留下同名专用分类和拒绝行为，不能完成 #78；按关键词删分支或改用姓名重建全部 key 则会破坏普通路径与归属保护，不采用。

### 不变的正式边界

- Stage 0 的 canonical `professor_dir`、`preview_path`、本地 `target_state` 与事务记录数组保持；不新增程序级索引、不更换 schema、不迁移或重写已有用户数据。
- 目录是状态和提交边界。正常名字入口继续可用，`professor_dir` 不成为用户新增必填项；身份/路径不一致、缺失教授、坏包、目录越界、输入归属无法确定时，保留原有对应范围的失败与零写入保护。
- 不同姓名教授的相同 `email_id`、`direction_id`、cross-group ID 及原值归属不变；`choice_owner_ambiguous`、不广播与单 owner 消费保持。
- 不新增“发现同名就拒绝”的算法，也不为范围外的重复姓名承诺选哪条、合并、恢复或拒绝语义。
- 不动同名文件/字段/agent/论文、同一教授显示名变化、目录别名去重、独立程序根中的测试样例复用。

## 2. 最新基线与关键事实

下述源码路径均相对仓库根，固定在目标 SHA；行号只用于定位，以函数/章节为实施锚点。

| 决策 | 当前事实与准确来源 | 结论 |
| --- | --- | --- |
| 保留完整 canonical 元组比较 | `.apm/skills/professor-contact/scripts/contact_targets.py::_reliable_candidates`（682–710）：只有 `(professor, professor_dir, preview_path)` 全匹配才进入验证；`same_name_other_dir` 只是不匹配时的分类。`tests/test_contact_targets.py::test_issue64_t3_unattributable_legacy_entries_are_never_imported` 的 `path_conflicting` 也进入该分类。 | 只去掉同名分类，不能删不匹配检查。 |
| Stage 5 只去掉同名拒绝 | `scripts/contact_state.py::cmd_stage5_list_inputs`（8818–8838）用 `len(named) != 1` 同时处理缺失与同名；`stage5_list_input_rows` 负责逐包发现、坏包独立行和容器路径校验。 | 保留发现函数和空匹配返回；不按位置任选一条。 |
| Stage 4 继续精确绑定与逐请求失败 | `.apm/agents/professor-contact-selection.agent.md` Step 1.2（60–64）把正常 no-dir 精确名字绑定、读取失败隔离与同名多目录要求写在同一段。 | 重写这一段而非整段删除。 |
| 当前夹具还包含同名假设 | 下节列出的 Stage 0/1/2/4 单测及 Stage 4 runtime fixture；其中 `Issue65Stage2BindingEnv` 被多个测试类继承。 | 同步所有实际消费该假设的位置，不通过删掉普通负例完成清理。 |
| 旧清单不能机械执行 | 当前树中 Stage 3 已使用 `SECOND_PROFESSOR` 与 `_write_two_professors_with_matching_ids`；旧 `build_twin_professor` / `build_same_named_professor` 不再存在。旧 `test_issue68_choices_attribution.py`、`test_issue68_root_partition.py`、`docs/issue68-test-gate.md` 不在目标树。#72/#73 已合并关闭。 | 不恢复旧文件，也不改写已关闭 PR 的审核/测试事实。 |
| 安装投影没有另一份共享业务源 | 根 `.apm/agents/` 与 `.apm/skills/` 是共享源，两份 analyzer 分别位于 `packages/professor-contact-{codex,opencode}/.apm/agents/`；`nix/contact.nix` 直接读取这些源。 | 同步两份 analyzer 的相关业务段落；不用重建安装器或重新安装。 |
| #92 无实施前置依赖 | 复核时唯一打开的产品 PR 为 [#92](https://github.com/ScholarWorkflow/professor-contact/pull/92)，head `b8f1aaa7f1eba04d6cc141c8c97522845bd80376`、base 为本计划基线。它与本任务共享 SKILL、两份 analyzer 和 `contact_state.py`，但修改 Stage 2 展示/证据逻辑，未修改这里的同名特例和夹具。 | 独立推进；任一先合入时按相关片段整合，不能覆盖其 Stage 2 变更或强制先合并 #92。 |

`tests/`、`scripts/`、`docs/` 在下文均指 `.apm/skills/professor-contact/` 下的同名目录，特别注明的根目录路径除外。

## 3. 修改清单与 owner

### 3.1 产品代码：保留校验，只删专用处理

1. `scripts/contact_targets.py::_reliable_candidates`：保留 `_entry_canonical` 与完整元组不匹配分支、立即跳过及后续验证顺序；所有可解析但不匹配的旧条目使用既有通用 `other_professor` 分类，不再输出 `same_name_other_dir`。不可归属仍走原 `identity_unreliable`。bootstrap/migrate 的候选统计、坏数据处理与写入时机不变。
2. `scripts/contact_state.py::cmd_stage5_list_inputs`：仍按请求名字精确过滤 `inputs`；空列表保持 `needs_input/professor_not_found`，非空列表原样交付。删除 `professor_ambiguous` 及仅服务于多个同名结果的基数判断；不加入新检测、排序选首项或自动合并。同步本函数 docstring 与 `build_parser()` 的 `stage5-list-inputs --professor` help。不修改 `stage5_list_input_rows`、partition/choices 算法、写入或邮件编号公式。

以上分别由旧状态归属 owner 和 Stage 5 发现 owner 直接承担，不能在 agent 或 fixture 中绕过产品校验。

### 3.2 当前说明与投影

- 主 `SKILL.md`：Stage 0 事务身份（89）、handoff 说明（198）、Stage 5 独立入口（433）、显式选择续轮（575）、`selection` 输入表（649）。删同名承诺与以同名为理由的映射禁令，继续明确 Stage 0 使用已存在的事务记录形状和真实路径。保留既有 Stage 1/2 调用接口，不借此重构 handoff。
- `docs/workflow-reference.md`：Stage 0（101）与 Stage 5（313）对应说明，保持与产品返回一致。
- `.apm/agents/professor-contact.agent.md`：修订隔离描述（159）与末尾禁止事项（222），只删同名附带承诺。
- `.apm/agents/professor-contact-selection.agent.md` Step 1.2：保留已带可靠目录时只读相关教授、同目录别名归一；无目录时允许候选位置发现，以当前包/状态顶层名字精确匹配和 canonical 目录事实绑定。缺失、读取/解析失败或无法确定归属只结束对应请求，不妨碍其他请求；自然语言选择只在已绑定教授的当前候选中精确映射。删除同名多目录消歧和全程序计数承诺，不改成猜测目录。
- `.apm/agents/professor-contact-email-generator.agent.md` 独立发现说明（124–127）：保留精确名字过滤与缺失返回，删除同名歧义分支文案。
- 两份 analyzer 的 Step 2.6：只删“含同名不同目录的教授”；保留每事务独立临时目录、实际路径交接、TOCTOU 保护和只清理自己目录。Codex/OpenCode 的不同路由规则不互相复制。

### 3.3 普通单测夹具：改名，不减少隔离覆盖

| 文件/锚点 | 最小变更与保留项 |
| --- | --- |
| `tests/test_contact_targets.py` 的 `PROFESSOR_A2_DIR`、G64-T3 unattributable 混合用例、G64-T4 两项 | 移除纯同名旧条目；保留 other-professor、path-conflicting、no-dir、absolute-preview、无误导入及源文件不变。两位教授本地状态/事务用例改为不同姓名和对应目录，保留不同选择、备注、路径及独立 resolve/select。原同名原因码断言调整为通用结果，不新增原因码协议。 |
| `tests/test_stage1_candidates.py::same_name_professor`、两个 `test_issue64_t5_same_display_name_*`、`test_issue65_stage1_professor_local_authority_and_isolation` | helper 改为普通教授构造并显式接收姓名；同步 preview、papers、target、期望姓名/目录和测试名称。保留 stale/missing 各自快照、非最终归属、外教授/旧聚合禁止访问和状态不变。`tests/test_stage1_handoff_identity.py` 的两个 helper 调用同步名称，原甲/乙名字保持。 |
| `tests/test_contact_state.py::Issue65Stage2BindingEnv` 及 `Issue65Stage2BindingTests`、`TestIssue64Stage2PlanBinding` | 默认 A/B 改为两个不同名字，所有 preview/papers/target/snapshot/facts 与署名记录保持自洽。sibling-proof 用例必须用 B 的名字生成 B 的合法 proof，再让 A 的 plan 拒绝错误绑定，不能因 setup 名字不一致提前失败。保留全部 ordinary identity、digest、失效和零写入断言。 |
| 共享 Stage 2 fixture 的既有子类 | `tests/test_stage1_handoff_identity.py::Issue65Gate2Stage2Tests`、`tests/test_issue65_gate2_r24_regressions.py::Issue65Gate2R24Base` 已显式使用甲/乙，保留其语义；仅在 helper 接口确有影响时同步调用。 |
| `tests/test_contact_state.py::Issue67ProfessorLocalStage4Tests.test_06_same_display_name_two_directories_keep_two_local_states` 与 `Issue67AdjacentStateTests.test_06_email_id_stays_the_three_part_identity_regardless_of_directory` | 第二位教授改不同名字，保留两份本地 pair 和本地包精确消费。邮件编号仍按每位教授自己的原三段公式生成，不能为维持旧相等断言伪造包或改产品公式。 |
| `tests/test_stage4_selection_agent_contract.py::Issue67Stage4SelectionContractTests`、`tests/test_issue67_gate2_r3.py::Issue67Gate2R3SelectionContractTests` | 将同名措辞正则换为本来就要求的 canonical 事务边界、精确名字绑定与逐请求失败隔离；其余契约断言不删。 |
| `tests/test_stage1_stage2_contract.py::test_issue64_t7_preflight_proof_save_is_per_professor_transaction` | 只清理同名解释，保留两份 analyzer 的普通证明路径保护断言。 |

`tests/test_stage01_caller_contract.py` 已明确同名问题在范围外；`tests/test_stage2_resolved_direction_downstream_regressions.py` 的同名描述指彼此独立的程序根，不是同程序同名支持，均不为关键词命中而改行为。

### 3.4 仍在使用的 Stage 4 隔离运行夹具

旧 Issue 未列出，但当前仍入库并被测试加载：

- `tests/runtime/prepare_issue67_stage4_isolation_fixture.py`：两条 `PROFESSORS` 记录使用不同展示名，`_input_pack`、manifest 的每教授记录及历史 pair 引用按所属教授取值；取消共享 `DISPLAY_NAME` 表示两人的假设。继续使用 `isolation-alpha` / `isolation-beta` canonical 目录，名字不等于目录 basename 的普通负例仍有效。保留唯一 malformed candidate-state、原方向/idea ID、旧程序级历史 pair、隔离目录和输入字节保护。
- `tests/runtime/prompts/issue67-stage4-isolation.txt`：删除“显示名相同”指令，继续提供两个准确目录及原显式选择，不补写产品业务逻辑。
- `tests/test_issue32_e2e_verifier.py::Issue67Stage4IsolationHarnessTests`：所有共享姓名断言/邮件 ID/错误目录负例改取所属 manifest/spec 的名字，不减弱单故障、有效教授提交、故障教授不写、历史 pair 不晋升和 canonical 路径绑定。
- `tests/runtime/verify_issue32_e2e.py` 目前只把 manifest 顶层 `display_name` 回显为诊断；其业务判定已按每教授记录和目录。保持判定算法及历史记录读取兼容；如移除过时共享诊断字段，仅同步该回显，不新增 manifest schema、collector、判定规则或取证要求。

### 3.5 当前材料与其他分支

当前 `plan/issue-66-{implementation,test}-plan.md`、`plan/issue68-{implementation,test}-plan.md` 已明确姓名唯一，不重新写其范围或历史批准。#78 旧行号清单由本计划的当前清单替代；旧 #72/#73 评论及已归档尝试、结果保持原样，不回写历史。

实施前与合并前各核对一次当前 main 与仍打开的相关分支。对 #92 的共享片段只做冲突与重引入检查；先落地者由后落地者正常整合，不直接修改对方分支、不复制旧文件覆盖新实现。若将来发现其他真正仍生效的同名要求，记录具体来源并在本计划内明确取代；不以旧历史记录存在为未完成。

## 4. 因果链、风险与反例

需求要求不再支持/拒绝同名场景 → 当前实现混有专用分类、基数拒绝、说明与同名 fixture → 在其各自 owner 上移除特例、改普通 fixture → 受支持的唯一姓名流程继续保留原身份/失败保护，不再以同名作为交付义务。

- intended_change / approved_behavior_change：取消同名分类、拒绝分支与支持承诺，依据 #78；普通 canonical 不匹配统一既有分类。
- preserved_behavior：本地事实源、事务数组、精确身份、原 ID、逐教授提交/失败隔离、只读发现、missing/bad-pack 返回及所有当前正确性防护。
- prohibited_side_effect：删完整元组比较、按名字猜路径、改变 owner/邮件 ID/schema、误导入其他教授旧数据、将无匹配当成功、坏包阻塞全批、增加同名探测/迁移、把清理变成通用 runtime 或安装验收。

代表性静态反例：姓名匹配但 preview 指向别的教授必须仍被排除；过滤不存在名字仍需待输入；一个坏包不能让合法发现行消失；Stage 2 的 B proof 必须先合法产生而后因 A/B 绑定错误被拒；两个不同名字即使共享方向/group/邮件编号也不能串 owner；同一 canonical 目录更换显示称呼仍是同一事务。上述安全条件由保留机制承担，不扩大为范围外同名输入测试。

状态、原子性、清理和并发机制不改；没有新持久文件、数据迁移、网络或权限变更。正式观察入口继续是既有 CLI JSON、教授本地文件及事务结果；私有 helper 名称和诊断分类不因本计划获产品 contract 地位。

Critical assumptions：无待实验验证的核心假设。Unresolved impacts：暂无；执行时若基线变化影响上述 owner/机制/保护，暂停受影响项并只修订相应决定。

## 5. 顺序与交接

1. 独立审核固定的 r1 和测试计划候选；作者状态保持 pending。实施核心方案前取得正式执行计划批准。
2. 在当时 main 的独立分支实施 3.1/3.2，并按 3.3/3.4 同步已有测试/夹具。修改前读取当前函数和调用者，不按旧行号或关键词批删。
3. 测试代码接线完成后，先独立只读检查测试是否确实到达目标业务边界、输入自洽且没有弱化断言；按测试规则确认步骤后才执行同目录测试计划中的定向项。本轮不执行。
4. 逐文件审查产品与投影差异、保留项及当前分支重引入风险。现行 CI 自行触发时沿用仓库既有门禁，不额外要求安装、模型或全仓本地重跑。
5. 正常提交与 draft PR 交付，保留当前版本、实际测试结果和未完成项；无强推、自动合并或提前关闭 #78。

下一负责人：计划审核者给出独立结论；批准后由产品实施者和测试工程师按上述清单接线，再由执行者运行已确认步骤。计划批准本身不代表实现正确、测试通过或可合并。
