# 第 2 阶段文字校验结果与修订任务衔接——实施计划

## 1. 版本、依据与状态

- Requirement revision：2026-10-15 用户确认的缺陷修复目标——第 2 阶段文字校验发现术语未解释等问题后，原始结果应被正式程序接收，生成对应修订任务；不得因结果格式不一致返回 `invalid_validation_json`。本计划只规定这一修复及其直接影响。
- Canonical Plan revision：`stage2-style-validation-handoff-r1-2026-10-15`；唯一正式实施计划为本文件。
- Target repository：`ScholarWorkflow/professor-contact`；核查基线 `main@2a8601facb9f3bec96da6ac22c79586ca79560d7`。
- 外部依赖版本：不修改外部仓库、模型接口、浏览器或 Zotero 协议；实际安装时使用本仓库已有的 Codex / OpenCode 代理投影。
- 规则：[Project Consensus](https://app.notion.com/p/rekidunois/Project-Consensus-3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/rekidunois/Plan-Reviewer-Rule-3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/rekidunois/Test-Engineer-Rule-3d80101a85f380d8a8f5ce528141e253)。
- **计划审核状态**：已于 PR 评论 [#6191759713](https://github.com/ScholarWorkflow/professor-contact/pull/86#issuecomment-6191759713) 获 `Plan conclusion: APPROVED`。实施已提交于 `a1cc974` 与 `45cf751`；正式执行结果记录于同目录测试计划 r9。本项计划审核不代表拉取请求已获合并许可。
- 取证性质：已核对上述代码基线与正式代理说明；尚无用户本机那次“两处术语”校验的原始文件或可复用运行记录。因此只确认可由源码证明的接口冲突，不推定本地那次运行的全部细节。

## 2. 目标、现状与影响范围

### 2.1 已确认目标

1. 第 2 阶段的 `professor-contact-style-validator` 返回原始 `result + files[] + notes`，程序直接接收和解释；调用代理只负责原样保存与传递，不能自行补造 `direction_id`、`results[]` 或 `rounds`。
2. 第一次校验出现可修订的阻断问题时，为实际被指出的研究方向生成 `narrative.positioning` / `narrative.gap_notes` 修订任务；修订后重新校验，**最多两轮校验**。第一轮通过或仅有轻微问题时结束；第二轮仍失败则记录不通过并停止，不生成第三轮任务。
3. 校验结果必须与该教授当前受管 `套磁候选分析.md` 及已接受 `套磁候选输入.json` 中的规范 `direction_id` 一致。证据无效、文件过期、无法确定归属或问题不属于可修订正文时明确报错或报告阻塞，不猜测方向，也不假装已经通过。
4. 继续保留阶段 2 的事实包、逐方向输入指纹、gap/freshness、论文事实、用户原文、受管 Markdown 保护及教授边界；阶段 3～5 的正式输入和状态不变。

### 2.2 源码证据和决定

| 决定 | 现有证据（均为上述目标提交） |
| --- | --- |
| 原始校验对象是正式交接格式 | [style-validator 说明，第 116～134 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/agents/professor-contact-style-validator.agent.md#L116-L134)：输出 `result/files/notes`，明确禁止调用方改写成 `results[]/rounds/direction_id`。 |
| 错误位于产品程序的第 2 阶段接收处 | [contact_state.py，第 10470～10495 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L10470-L10495) 只接受 `results[]`；[第 10546～10552 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L10546-L10552) 修订计划直接调用这一读取器。 |
| 第一轮失败不能靠现有入口进入修订 | [contact_state.py，第 10546～10555 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L10546-L10555) 只挑 `fail_after_2_rounds`，而 [第 10480～10494 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L10480-L10494) 不接受第一轮 `fail`。 |
| 必须保存校验轮次跨越修订提交 | [contact_state.py，第 10663～10673 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L10663-L10673) 修订完成时删去旧 `validator`；[第 10680～10689 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L10680-L10689) 当前记录入口只能接收调用方给定轮次。 |
| 方向归属必须基于真实渲染结构 | [contact_state.py，第 4279～4415 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L4279-L4415) 按输入包方向顺序输出 `## 方向 N`，目前正文标题不带机器 ID。 |
| 原有接受条件需继续生效 | [contact_state.py，第 3590～3606 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L3590-L3606) 只把逐方向 `pass/skipped` 当作已验收；`stage2-refine-finalize` 只改叙事并清理先前预检证明。 |
| 必须同步实际调用说明 | [OpenCode analyzer 第 558～578 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md#L558-L578) 与 [Codex analyzer 第 555～572 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L555-L572) 均将校验结果交给现有修订入口，说明未给出正确的首轮记录、修订、二轮记录顺序。 |
| 现有测试未证明真实交接 | [test_contact_state.py，第 819～831、874～885 行](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/tests/test_contact_state.py#L819-L885) 直接构造 `results[]`，未消费 style-validator 的原始 `files[]`。 |

上表中 style-validator 与产品技能关于原始对象的规定属于正式接口依据；runner、渲染器、测试的当前行为是问题证据，不能因为旧测试通过而变成要求调用方补造数据的依据。

## 3. 修复方案与责任

**故障原因**：校验器产生文件级原始报告 → 第 2 阶段修订入口要求方向级终态报告 → 原始结果读取失败；即使临时伪造 `results[]`，也无法正确推进“第一轮失败 → 修订 → 第二轮记录”。

**负责方**：本仓库的 `contact_state.py` 负责解析、关联方向、计算轮次、持久化状态和生成修订任务；style-validator 只给出被校验文件的观察结论；analyzer 只负责委派、原样传递、等待与处理 runner 决定。禁止把格式转换责任塞回代理提示词或仓库外工具。

### 3.1 校验原文读取与方向定位

- 第 2 阶段的记录、修订计划、修订提交共享同一种 style-validator 原始文件解析规则：`result="ok"`，目标文件恰好一个 `artifact="analysis"` 条目且 `file` 精确指向本教授的受管分析文件；该条目有合法的 `verdict`、计数、`issues[]`，每个问题保留 `rule/severity/location/quote/suggestion`。保持与校验代理已声明的 `pass/pass_with_minor/fail`、`blocking/minor` 含义一致。
- 先验证分析文件仍是输入包所记录的受管渲染版本：正文摘要与 `cache.render`、受管文件头匹配，目标教授目录一致；旧报告不得套用新正文。记录原文文件摘要与当前正文摘要供修订入口校对。
- 对需修订的阻断问题，依据渲染文件中的逐字 `quote` 定位实际行，再用受管 `## 方向 N` 分节及已接受输入包的方向顺序映射为规范 `direction_id`；不依赖显示名称、代理臆造的方向编号或旧 `collection_key`。`location` 是确切行号时可用于确定重复引文的具体命中行，仍须核对该行确实包含 `quote`。
- 只有落在可修改的 `narrative.positioning` 或 `narrative.gap_notes` 解释文字中的问题能生成修订任务；固定表头、引用、用户原文、全局须知等非修订区的问题不得伪装成叙事修复。不能唯一定位、指向无效方向或涉及不可修订区时，保留问题、返回明确阻塞原因，零错误修订；**不扩展为全方向重写**。
- `pass_with_minor` 无阻断时按现有可复用的 `pass` 终态存储，同时保留轻微问题原文以供展示；`fail` 必须确有 blocking，计数必须与问题清单一致。调用方传入的 `results[]` 及自行指定的轮次/归属不得再被当作第 2 阶段原始校验结果；历史已经保存的合法 `validator.results` 仍按既有接受条件读取，不强制迁移。

### 3.2 校验轮次与修订提交

| 当前阶段 | 正式动作 | 下一状态 |
| --- | --- | --- |
| 新稿第一轮 | analyzer 原样保存报告，立即调用 `stage2-record-validation`；runner 校验当前渲染并派生方向与第 1 轮结果 | `pass/pass_with_minor` → 已验收；`fail` → 记录失败方向、原始文件摘要和可修订问题，返回 `needs_correction` |
| 第一轮需要修订 | analyzer 只把**已记录**的同一份报告传给 `stage2-refine-plan`；runner 先对照已记录轮次、文件摘要及正文摘要，再逐失败方向出修订任务 | 对应方向进入一次结构化改写；不得凭另一个报告或过期文件修改 |
| 修订提交 | `stage2-refine-finalize` 仅替换已准许的叙事字段，重渲染并继续清理失效的预检证明；保留已发生的第一轮次数与待复核身份，旧失败结论不可成为新版正文的 `pass` | 新稿需要第二轮校验 |
| 新稿第二轮 | 重新委派 style-validator，原样保存结果，再 `stage2-record-validation` | `pass/pass_with_minor` → 已验收；`fail` → `fail_after_2_rounds` 终态，带问题报告后停止，无第三轮修订 |
| 任一输入或状态不符 | runner 返回明确的错误／陈旧状态；analyzer 停止当前依赖动作 | 不写误归属修订、不覆盖原有事实或手工修改 |

- 新记录继续写本教授 `套磁候选输入.json` 的独立 `validator` 区域；至少保留轮次、所验证正文摘要、原报告摘要、逐规范方向结果及未解决问题。过渡态明确标为待二次校验，不允许预检把它当作通过。保留原有 `validator.results[direction_id].result=pass|skipped` 的接受语义，新增失败过渡态只能走慢路径。
- 修订计划与提交必须对同一个已记录失败集工作；可选 `--direction-id` 只能缩小到该集中的方向；原 `--facts` 与 `--professor-dir` 两种证据来源和 input fingerprint 检查继续可用。新报告、改过的受管正文、改过的包或重复提交不得复用旧修订授权。
- 保持第一轮、第二轮分别只有一次正式记录和最多一次修订；`stage2-refine-finalize` 不得丢失已经发生的轮次，也不得假造第二轮通过。第一轮通过、轻微问题、第二轮失败均不会再派发修订任务。
- 第 2 阶段 `stage2-preflight` 对旧合法已验收记录保持既有命中；对新记录只有当前正文对应的终态 `pass/skipped` 才可命中。不得因为只更新展示文字就修改论文分析或后续阶段事实。

### 3.3 正式调用与文档

- 修改 `packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md`、`packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md` 的 Step 6.5，并同步 `.apm/skills/professor-contact/SKILL.md` 中相关说明：**校验 → 原样保存 → record → 按 `needs_correction` 修订 → 重新校验 → record → 终态**。Codex 与 OpenCode 各自保留原生命名代理委派和等待方式，不新增 shell 替代委派或上游代理。
- style-validator 的原始结果格式与只读责任不改；如果实现发现仅说明缺少明确的第 2 阶段交接文字，才对说明作一致性同步，不改变检测规则。
- 产品代码只修改该第 2 阶段接收、修订和状态路径及必要的直接调用说明。测试代码的更新交由测试工程师按已确认业务目标安排，正式测试计划及运行步骤独立由测试规则管理，不在本实施计划增设额外检查关口或测试设施。

## 4. 影响、选择与禁止副作用

- `intended_change`：第 2 阶段由 runner 自己接收原始校验对象、绑定正文和规范方向、记录真实轮次；第一轮阻断能够进入一次叙事修订，第二轮按结果结束。
- `preserved_behavior`：style-validator 校验准则及原文；教授目录与规范方向 ID；文献/gap/freshness/用户笔记、历史合法已验收记录和预检复用；仅可修改叙事；受管 Markdown 人工冲突保护；`--facts` / `--professor-dir` 修订来源；阶段 3～5 输入和正式状态。
- `approved_behavior_change`：依据本轮用户明确要求，允许第 2 阶段从原始报告进入一次修订，并将第 2 阶段不合契约的调用方自填 `results[]/rounds` 输入改为拒绝；不扩大校验轮次上限。
- `prohibited_side_effect`：不得让代理自行选择/发明方向、编写正式分析 Markdown、降低 blocking 判断、把第二轮失败写成通过、清除用户原文、跳过受管文件校验、额外请求外部模型补跑其他方向、修改 Stage 3/5 校验逻辑或仓库外依赖。
- 方案取舍：选“runner 从原始报告派生方向和轮次”。备选“让 analyzer 自己构造 `results[]`”违反校验器禁止重建原文及 runner 负责状态的正式约定，仍会漏掉首轮失败/丢轮次问题；不采用。也不引入新的校验中间服务。
- 风险控制：多方向重复引文只有证据足以唯一定位时才修订；若来源文件、正文、状态已经变化则在写盘前失败；修订中保留已完成轮次以防绕过两轮限制；原有的教授级写入范围与人工冲突保护继续生效。不存在需要同步修改的上游仓库。并发写锁另有议题，不在本次修复范围。
- 当前无已知必须依赖外部修复的阻断因素。用户本机校验原文未提供，不据此宣称该次具体文本已经可修复；本修复目标可由仓库内正式协议与受管渲染结果判断。

## 5. 实施顺序与审查交接

1. **先审核本计划**：核对第 2、3、4 节的格式责任、方向归属、两轮状态、兼容与失败关闭；获得正式 `Plan conclusion: APPROVED` 后才能实施核心方案。
2. **产品修复**：在 `contact_state.py` 完成原始校验接收、渲染绑定、方向归属、首次失败修订与轮次记录；保留受管文件保护及既有阶段事实源。
3. **调用同步**：修改上述两份 analyzer 安装投影和主技能说明，使实际生产调用顺序消费 runner 的记录结果；两种运行环境仅使用已有的原生委派。
4. **受影响验证**：由测试工程师依据 Test Engineer Rule 冻结本次必测行为并实施必要产品测试；只核对原始报告转修订、一次修订后复核与终态、错误输入不误写以及直接改变的兼容行为，旧的未受影响通过结果按规则复用。既有测试用例如果手工输入 `results[]`，需要改为符合正式校验器输入协议的业务样例。
5. **合并审核**：检查本计划对应的实现、正式调用链及适用的第三关口测试结果。此拉取请求在实施和审核完成前保持草稿，不以“只有计划文件”申请合并。

本计划不自行声明任何计划门槛、测试门槛或合并门槛为通过；修订依照同一 `plan/` 文件进行，避免散落在拉取请求评论中的多份规范方案。
