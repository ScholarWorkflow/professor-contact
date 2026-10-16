# Stage 2 运行器三项缺陷修复——实施与测试计划

## 1. 任务、版本与当前状态

- **Requirement revision**：2026-10-16 用户对《第二阶段运行器问题报告》的三项问题明确要求修复，并要求在草稿拉取请求中保存执行计划；以下预期限定为报告的三项行为和既有正式约定。
- **Plan revision**：`stage2-three-runner-defects-r1-2026-10-16`；本文件是本拉取请求唯一有效的完整实施与测试计划。`Proposed review status: pending`。计划作者不自行宣称任何审核关口通过。
- **Target repository / Base SHA**：`ScholarWorkflow/professor-contact`；`main@58a2ae7e110f2f75cbd17fe40dca814c2b2d0777`（2026-10-16 核对）。实施时记录实际提交，如主分支变化，按改变的源码和正式约定定向检查影响。
- **任务依据**：用户提供的《第二阶段运行器问题报告_2026-10-16.md》（本机运行副本的代码、历史回执和诊断）；本仓库上述基线的 [运行器](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py)、[Stage 2 正式技能约定](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/SKILL.md)、[文字校验代理](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/agents/professor-contact-style-validator.agent.md)。
- **项目规则**：[Project Consensus](https://app.notion.com/p/rekidunois/Project-Consensus-3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/rekidunois/Plan-Reviewer-Rule-3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/rekidunois/Test-Engineer-Rule-3d80101a85f380d8a8f5ce528141e253)、[Merge Reviewer Rule](https://app.notion.com/p/rekidunois/Merge-Reviewer-Rule-3ea0101a85f381c2b870e7fdf4b55b19)。
- **证据边界**：报告记录了先前运行中的结果和运行副本 SHA，但报告本身没有再次执行写状态的复现命令；本次已核对仓库基线源码具有对应分支。没有读取用户机器上的原始回执和本地开发副本，不能以本计划声称真实数据已经修复或回归测试已通过。修复和验收均使用仓库内合成隔离数据。

## 2. 冻结需求与当前原因

| 编号 | 必须达到的结果 | 代码原因及修改责任 |
| --- | --- | --- |
| R1：正式成员与分析参考分离 | 方向的 `supporting_item_keys` 按本方向原 `provisional_member_keys` 和**已接受**的 `papers_to_add/papers_to_remove` 决定；`relevant_keys` 仍可作为分析、未来工作和叙事引用范围，不能自行增加正式成员。报告中的边缘方向为原 6 篇加 `D6XQCHTP`，共 7 篇；`GTQBNPED` 只属于另一方向的获准新增。 | [`build_direction_pack` 第 4314—4361 行附近](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L4314-L4362) 将 `direction_relevant_keys` 全部放入 `supporting_item_keys`；[`cmd_stage2_finalize` 第 4809 行附近](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L4809-L4833) 又在这个底表上应用获准增删。修复责任属于 `contact_state.py` 的组包和成员物化路径。 |
| R2：原始校验报告可准确定位 | 一条阻塞问题必须对应受管正文**唯一的实际行**和正确的 `direction_id`。同一 `quote` 出现三处时，校验器按行分别输出条目，记录器逐条消费；“第57行及多处”不应被当作可唯一定位的记录。不能任意选第一处，也不能让调用方改写原始报告。 | [第 10768—10775 行](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L10768-L10775) 允许任意短位置字符串，[第 10845—10864 行](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L10845-L10864) 只能按纯数字定位，否则引用多行时报 `validation_quote_ambiguous`。修复责任属于第 2 阶段记录器与同仓库 style-validator 的 Stage 2 输出约定。 |
| R3：没有新结果不能伪造接受 | 本轮 `stage2-resolve-plan` **明确发出新任务**、且无可复用的已接受记录和已有待选提案时，缺指定 `resolve-<方向完整编号>.json` 要返回 `result_missing` 并停止写入本轮方向权威状态。错写为 `resolve-edge.json` 等短名不能变成 `acceptance=accepted / resolution_type=unchanged`。 | [第 2304 行附近](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L2300-L2311) 发完整任务文件名；[第 2535—2577 行](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L2535-L2577) 在缺文件时构造 `_unchanged_default()`，保存为 accepted；[第 2871—2934 行](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L2871-L2934) 可将此结果写入缓存。责任属于 `validate_resolve_results` 和 `cmd_stage2_resolve_finalize`。 |

上述目标由本次用户修复请求确认；报告中的实际代码行为是缺陷证据，不把错误默认状态升级为正式产品要求。

## 3. 冻结实施方案

### 3.1 R1：建立唯一权威成员集合，保留相关证据集合

1. 在 `build_direction_pack` 与 `cmd_stage2_finalize` 之间明确分工：`provisional_member_keys` 是初始正式归属；`relevant_keys` 只供论文分析、gap、freshness、叙事与引用。建立 `supporting_item_keys` 时，按固定顺序对初始成员去重，并且只按已通过 `stage2-resolve-accept` 或 `--keep-provisional` 的方向决策执行增删；没有用户确认的变更仍阻断 `stage2-finalize`。绝不使用 `relevant_keys`、`member_keys` 候选并集或 `named_keys` 为成员缺口兜底。
2. `papers_to_remove` 只能从本方向原正式成员移除；`papers_to_add` 仍遵守现有“教授级 candidate union 且全文事实有效”的校验。共享论文可以分别属于两个方向，但每一个归属都要有原始成员或正式接受的依据。保留教授级 `papers[item_key]` 的单条权威记录，方向仍以 `supporting_item_keys` 引用，不能生成重复论文实体。
3. 保留 `relevant_keys` 所允许的 `{{P:key}}` 论文参考、future-work/gap 和叙事事实；如正式成员与参考论文不同，渲染必须仍能从已验证的结构化论文事实取得标题，不得把参考论文补回成员以解决引用问题。修改引用投影时只触及必要的第 2 阶段数据读取或渲染，不改变引用权限、`gap_scope` 或叙事模型判定。
4. 沿既有三段应用顺序兼容 `refined`、`split_from` 和 `merged_into`：细化只应用获准增删；拆分后源方向剔除移往子方向的成员，子方向可使用经过全文验证的教授级候选；合并保留双方真正的正式成员与 gap 引用。继续保留“已接受拆分子方向在无变化重跑时不被清空”及“教授级共享论文不复制”。每个最终方向的 `input_fingerprint.final_supporting_keys` 必须从最终权威成员计算，让 Stage 3 的复用判断感知真实变更。
5. **旧缓存安全**：此修改令相同输入得到不同正式成员，按 `stage2_preflight_versions()` 的现有注释提升 `STAGE2_RESOLUTION_SEMANTICS_VERSION`；旧输入包不可命中 `stage2-preflight` 的 `reuse_all`。同时检查 `Stage2Context._prepare_directions` 内部旧方向复用：即使外层预检决定处理，也不得把旧 `supporting_item_keys` 原封不动作为新归属底表。重算或在正式生成前校验与“provisional + accepted edits + split/merge”一致；不一致时从合法结构化事实重建，缺少必要原始成员或证据则在写盘前报明确错误。不能只提升版本号而继续复用污染的旧方向对象。有效的已接受 resolve 决策仍按原指纹规则复用，不重复要求用户确认。
6. 只针对本教授当前受影响方向写入生成物，维持前置预检证明、受管 Markdown 的人工修改保护和现有确定性写盘规则。**不得自动删除或篡改用户历史缓存**。报告所述异常方向缓存已按既有重置办法修复；其他发现过旧异常接受条目而无法证明来源时，先备份并按技能第 265 行现有重置流程处理，不能擅自把旧 accepted 状态解释为真实用户选择。

### 3.2 R2：收敛位置约定与记录器的真实识别能力

1. 只对 `artifact=analysis` 的 Stage 2 校验明确支持：正整数行号、纯 ASCII 十进制行号字符串、精确写法“第N行”；兼容原有短文本 `location` **仅在对应 `quote` 在当前受管正文恰好命中一行时**使用。所有行号均指包含 frontmatter 的当前受管文件实际物理行，按现有 `line_offset` 计算。
2. style-validator 的 Stage 2 指令要求：当同一引文命中多行时，每一处分别生成一条 `issues[]`，`location` 填该处具体行号、`quote` 填所在行的原文逐字片段；不得再输出“第57行及多处”“多处”作为多个位置的统称。该指令仅作用 Stage 2，Stage 3 的位置接口及其结果消费保持原状。
3. `stage2_validation_report` 在 schema 检查与归属计算时使用同一位置规则；“第N行及多处”等含糊行号提示须用明确错误告诉调用方“按实际行号逐条重做校验”，不能自动把一条 issue 展开到任意多处。引用找不到、指向错误行、仍有多处匹配、同一行引用重复，以及不能归入唯一方向，继续安全拒绝。对有效的多条 issue，按实际命中行逐条映射方向和是否可修订。
4. `stage2-record-validation` 仍只消费原生 `result/files/notes` 完整原始报告；保持第一轮记录 → 修订 → 第二轮记录的既有两轮限制、文件与正文摘要绑定、`validator` 独立状态、不可修订区域拒绝和零错误修订。原始报告不能由协调代理手工“修好”再提交。若已保存报告本身位置含糊，只能由校验器在同一受管文本上重新给出合规报告。
5. 同步 `.apm/agents/professor-contact-style-validator.agent.md`、两种安装投影的 `professor-contact-analyzer.agent.md` 中 Stage 2 校验交接说明、主 `SKILL.md` 的位置约定；不改变文字校验标准、阻塞严重度、Stage 3 校验或代理委派方式。

### 3.3 R3：对发出的新归属任务强制检查结果文件

1. `stage2-resolve-plan` 的 `jobs[].result_file` 是新任务唯一合法文件名，`stage2-resolve-finalize` 用同一规则消费；不扫描猜测短文件名、不自动改名或从其他目录取代。
2. `validate_resolve_results` 逐方向按互斥情形处理：①当前指纹匹配且已接受、未发新任务的既有条目，照常复用并忽略旧目录中的多余结果文件；②当前指纹匹配且仍待用户选择的提案，无新文件时仍保留 `proposed`，继续返回 `needs_user_choice`；③需要新结果且不存在以上两种合法继续依据时，指定文件不存在就返回 `result_missing`，带预期完整路径，禁止生成 `accepted/unchanged` 默认条目。存在但不可读取、非法 JSON 或方向身份不符时沿用原有明确错误。
3. 在产生 `_resolved_directions.json`、正式输入包或任何新 accepted 缓存之前完成所有需要的新结果检查。任一方向缺文件则本次**不写方向权威状态**；不因其他方向文件齐全而保存半批次接受结果。正确补齐文件后，下一次 plan 仍应产生该待处理 job，finalize 能读到它。
4. 继续保留 `stage2-resolve-accept` 的显式批准以及 `--keep-provisional` 对既有待选择提案的合法覆盖；保持已接受缓存只在真实输入指纹匹配时复用，且不让旧结果目录的陈旧文件替代新决定。不要为了修复缺文件而删除任何有效 accepted/pending 条目或废弃既有重置流程。

## 4. 方案取舍与限制

- **选择**：在现有 `contact_state.py` 的事实/组包、校验和状态写入入口修复根因；对外保留现有 JSON 路径、`direction_id` 身份、受管文件与阶段职责。只在 Stage 2 的实际契约边界同步模型说明。
- **拒绝的替代方式**：由协调代理删除多出的 `supporting_item_keys`、手工改写原始校验 JSON、猜测 `resolve-*.json` 的短名，或在下游 Stage 3 过滤错误成员。这些办法不会修复生产入口，再次运行会复发。另一个方案是让相关论文和正式成员继续共用一个字段、仅修改显示数量；它会继续污染 Stage 3 指纹，因此不采用。
- **intended_change**：正式方向成员不被参考范围扩张；重复引文能逐条准确记录或明确拒绝；缺新结果时在落盘前失败；旧错误输入包不能因缓存命中而继续传播。
- **preserved_behavior**：教授身份与 `direction_id`、合法共享论文、经全文验证的跨方向新增、已确认的细化/拆分/合并、有效 accepted/pending 复用和显式“沿用 provisional”；论文/gap/freshness/叙事输入范围、受管 Markdown 的人工保护、Stage 2 校验两轮限制、Stage 3—5 只消费已接受输入包、原有 JSON/错误回执格式中未涉及的字段。
- **approved_behavior_change**：本次用户批准修复三项错误结果及为此必需的第 2 阶段位置约定、缺文件失败处理和缓存失效。没有授权改动 Stage 1 候选生成、外部 Zotero、论文全文分析判定规则、Stage 3—5 产品逻辑或其它仓库。
- **prohibited_side_effect**：不得把“相关”当“正式归属”，不自动接受缺席的模型输出，不跳过人工采纳、不将旧报告改写为通过、不使用用户生产目录测试、不增加全仓运行/模型采样/跨仓安装作为本次默认必测项目。
- **故障边界**：新任务缺文件、本轮指纹不符、位置不唯一时必须拒绝相应提交；同一教授多个方向的状态写入保持既有事务边界。并发锁及非本次问题的其它历史缺陷独立处理，不顺手重构。

## 5. 正式必测清单（测试方案初稿，待测试工程师第一、第二关审核）

每项仅覆盖本次修改的业务结果及直接改变的兼容行为，使用仓库现有 `unittest` 和合成临时教授目录。正式测试入口、准备与断言由本地测试工程师按本节补齐；无新增专用测试服务或通用判定器。

| 业务目标 | 输入或场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- |
| T1：正式成员正确且参考仍可用 | 单方向初始成员 6 篇，`relevant_keys` 多 `GTQBNPED`，已接受 `papers_to_add=[D6XQCHTP]`；另一个方向合法加入 `GTQBNPED`。经正式 `stage2-resolve-plan/finalize`、采纳和带预检凭据的 `stage2-finalize`。 | 前一方向恰好 7 篇，且没有 `GTQBNPED`；第二方向仍可包含该篇；相关论文的合法证据/引用未因排除成员而被删除，最终输入摘要依据这 7 篇成员。 | 扩展既有 `test_stage2_resolved_direction_downstream_regressions.py`，检查最终输入包 `directions[]`、`papers`/叙事引用和最终 `input_fingerprint`。 |
| T2：原有归属决定可继续使用 | 合法 `refined/split_from/merged_into`、共享论文、无变化的已物化拆分子方向，以及来自候选并集但不在 `relevant_keys` 的全文新增。 | 成员转移与 gap 引用仍正确；拆分子方向重跑不丢成员；合法已接受决定不重复变回待选择。 | 复用并按必要范围扩展既有 `test_stage2_resolved_direction_downstream_regressions.py` 和归属接受边界测试；已有有效通过项可直接沿用。 |
| T3：缺失结果明确失败、不能缓存污染 | 新 resolve job 指向完整方向编号文件名，仅在同一结果目录写入 `resolve-edge.json`；随后在原测试隔离数据补写正确文件。 | 第一次返回 `result_missing`，`_resolved_directions.json` 无本轮新 accepted 条目且既有状态不变；下一轮仍发 job，正确文件被读取。已有 accepted 的缓存继续复用并忽略旧文件；已有 proposed 在缺文件时继续保留为待选择。 | 扩展 `test_stage2_resolved_direction_regressions.py` 的正式入口测试，以返回回执和前后方向文件对比判断。 |
| T4：重复引文的定位与拒绝 | 同一阻塞 `quote` 出现在受管正文三个物理行，原始 style-validator 报告对三行分别给出准确行号；另有仅填“第57行及多处”的原始报告副本。 | 三条准确记录逐一归到其真实方向并进入正常修订状态；含糊格式返回可操作的定位错误，不记入校验状态，也不修改正文/输入包；不得选任意单处。 | 扩展 `test_stage2_style_validation_handoff.py` 的 `stage2-record-validation` 正式入口与前后文件检查。 |
| T5：旧错误包不能静默复用 | 具有旧 `cache.preflight.resolution_semantics_version` 且 `supporting_item_keys` 被相关集扩大、原始成员及有效 accepted 侧车可用的合成包；对照合法同版本包。 | 旧包预检不返回 `reuse_all`，重建后成员与批准增删一致；合法新版本无变化包按既有条件复用。 | 用 `stage2-preflight`、`stage2-plan/finalize` 及最终包直接检查；优先复用已有 Stage 2 前置输入与测试辅助方法。 |

**测试准备**：产品单元测试放在 `.apm/skills/professor-contact/tests/`，沿用仓库中 `BaseEnv`、`ResolvedPipelineMixin` 等合成夹具，在系统独立临时目录中创建教授、方向、论文事实、预检证明与结果目录。只用当前生产 CLI 正式入口，不伪造产物后绕过正式校验。不得连接真实 Zotero、浏览器、教授业务目录或用户缓存。无需引入独立测试仓库、运行模型或修改机器范围的配置。

**拟执行入口**：测试工程师完成第一、第二关后，从仓库根进入现有测试目录，运行相应 `python3 -m unittest -v` 指定模块：`test_stage2_resolved_direction_regressions`、`test_stage2_resolved_direction_downstream_regressions`、`test_stage2_resolved_direction_acceptance_boundary`、`test_stage2_style_validation_handoff`，以及承载 T5 的已有预检测试模块。所需 `uv run --no-project --python python3` 包装、临时输出目录、安装版本和直接可复制命令，由本地测试工程师在此唯一文件中确认后冻结，不以本计划初稿声称已执行。只保留正式业务结果所需字段、退出码和必要错误，不采集完整运行时轨迹。

**失败及复用**：异常业务输出就是业务失败，不以改输入或重试换取通过；环境/外部工具阻断标记无法判断。先排除隔离/权限错误，再仅重测受影响项；未受影响的历史有效通过记录由第三关决定复用。没有授权外部服务正式重试，本次预计无需外部调用。测试工程师不得扩展为整套 0—5 阶段联调或逐个代理行为认证。

## 6. 实施次序、交接与合并条件

1. **计划审核**：由独立审核者在当前基线及必要的目标版本上审 P1—P4，取得正式 `Plan conclusion: APPROVED`。若证据揭示另一个成员归属入口，先把新增关键事实及直接影响修订进本文件再复审；作者不得把此初稿标为批准。
2. **先修状态边界 R3**：在 `validate_resolve_results` 去掉新任务缺文件的默认 accepted 路径，保护现有 accepted/pending 复用和 `--keep-provisional`；确保校验完所有方向后才允许写本轮 sidecar。
3. **修 R1 及旧缓存**：在 Stage 2 建包时分离成员和相关集，在正式决议应用后计算最终成员/指纹；处理现有 split/merge/reuse 路径；提升 Stage 2 归属语义版本并阻断污染旧包在内部重用。
4. **修 R2 并同步调用说明**：更新 Stage 2 原始报告读取与行号定位，调整同仓 style-validator 的 Stage 2 位置要求及 Codex/OpenCode analyzer 交接说明；不改变 Stage 3 校验。
5. **测试工程师关口与实现**：依据第 5 节确认第一关必测清单、补齐第二关可执行方案；在本拉取请求分支提交受影响测试与产品实现，按规定在隔离环境执行并记录第三关结果。只核对该次变更影响到的既有行为。
6. **合并审核**：按 Merge Reviewer Rule 对“正式需求 → 已批准计划 → 本分支实现 → 生产调用路径 → 第三关结果”审核；`READY + COMPLETE` 后再由用户另行决定是否合并。此请求在实现、验证、审核完成前保持 `Draft`。所有后续实施继续提交到**同一个拉取请求分支**；不拆成另一个 PR，也不把计划正文散落在评论中。

## 7. 提交时状态和未完成事项

- 本提交 **仅包含计划文件**，未修改运行器、代理技能说明、测试或任何教授业务状态。
- 尚未取得独立的计划批准、测试第一/第二/第三关或合并审核结论；未运行回归测试。当前 `Plan conclusion`、`Test Engineer Gate 3`、`Merge conclusion` 均为 **pending / NOT_READY**，不得宣称实现已修复。
- 没有可供本会话调用的独立子代理复核工具；作者自查不替代独立计划审核。下一责任人为计划审核者，之后为产品实现者和本地测试工程师。
