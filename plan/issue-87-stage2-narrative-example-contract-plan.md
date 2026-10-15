# Issue #87：Stage 2 叙事示例引用一致性修复——正式实施与测试计划

## 1. 版本、依据与状态

- Requirement revision：[Issue #87](https://github.com/ScholarWorkflow/professor-contact/issues/87)，截至 2026-10-15T12:04:27Z 的正式需求；本计划不修改需求的业务边界。
- Plan revision：`issue87-narrative-example-contract-r1-2026-10-15`。本文件是该拉取请求的唯一现行实施及直接测试计划，后续语义修订原位更新并提高版本。
- Target repository：`ScholarWorkflow/professor-contact`；取证与分支基线：`main@2a8601facb9f3bec96da6ac22c79586ca79560d7`。
- 适用项目规则：[Project Consensus](https://app.notion.com/p/rekidunois/Project-Consensus-3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/rekidunois/Plan-Reviewer-Rule-3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/rekidunois/Test-Engineer-Rule-3d80101a85f380d8a8f5ce528141e253)。
- Codex 官方资料：[子代理及自定义代理](https://developers.openai.com/codex/subagents)、[命令行参考](https://developers.openai.com/codex/cli/reference)，核对日期 2026-10-15。本改动只涉及仓库维护的代理说明示例和确定性运行器示例，不改变 Codex 原生代理配置、委派方式或命令参数。官方文档不规定产品专用的 `positioning[].text` / `refs` 对应关系；该约束来自本仓库的正式需求和运行器。
- Proposed review status：`pending`。需要正式 Plan Reviewer 对 P1–P4 审核并给出 `Plan conclusion: APPROVED`，随后才开始产品与测试修改。本次计划提交不代表代码修复、测试通过或可合并。
- 本分支关联 Issue #87；合并本拉取请求时关闭议题，后续实现与测试仍在同一拉取请求上提交。

## 2. 已确认需求、现状与来源

### 2.1 冻结目标

1. Codex 分析代理、OpenCode 分析代理及 `stage2-plan` 产生的 `narrative` 工作项 `result_schema`，三处公开示例各自满足：`positioning[].text` 中引用占位符与 `positioning[].refs` 的集合精确相等，且 `refs` 不含重复项。
2. 现有测试必须先检查**提取出的原始示例**，然后才将示例中的说明性标识绑定到合法的合成测试数据；测试不得用现成夹具的完整 `text`/`refs` 覆盖原示例，从而把错误隐藏。
3. 合法合成示例仍须通过现有 `stage2-finalize`，其三个具体例子字段 `concrete_object`、`input_example`、`output_example` 保留并写入输出。
4. `validate_narrative_entry` 的严格校验、允许的 `paper/later/gap` 引用范围、`direction_id` 与 `collection_key` 的兼容、Stage 2 正式输出结构及后续阶段行为不变。
5. 只改第 2 阶段叙事示例和直接测试；不碰另行在 PR #86 修复的文字校验与修订交接，也不改外部仓库。

### 2.2 关键决策及证据（描述现状与正式要求分开）

| 决策 | 正式要求及基线源码证据 |
| --- | --- |
| 引用按占位符种类对应 | [Issue #87](https://github.com/ScholarWorkflow/professor-contact/issues/87) 明确要求集合相等；[运行器常量](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L123-L126) 的 `PLACEHOLDER_RE` 识别 `P/G/L`；[正式校验](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L4042-L4088) 映射 `P→paper`、`L→later`、`G→gap`，拒绝不一致或重复引用。 |
| Codex 代理示例多列一项 | [Codex 示例](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L523-L534)：`text` 有 `{{P:ITEMKEY}}`、`{{G:GAPID}}`，`refs` 还含 `later:ITEMKEY`。 |
| OpenCode 代理示例多列一项 | [OpenCode 示例](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md#L526-L537) 存在同一不一致。 |
| 运行器返回示例少列一项 | [`cmd_stage2_plan` 的 `result_schema`](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L3883-L3906)：`text` 中有 `{{G:GAPID}}`，`refs` 只有 `paper:ITEMKEY`。 |
| 测试遮蔽原样例缺陷 | [原测试](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/tests/test_stage2_narrative_example_contract.py#L15-L58) 在执行 `stage2-finalize` 前，将两个关键字段换成夹具的合法内容；因此不能证明发布的示例本身正确。 |
| 保留两种方向字段的兼容 | [现有 `validate_narrative_entry`](https://github.com/ScholarWorkflow/professor-contact/blob/2a8601facb9f3bec96da6ac22c79586ca79560d7/.apm/skills/professor-contact/scripts/contact_state.py#L4020-L4038) 接受 `direction_id` 或 `collection_key`；本问题没有要求统一这两种示例表示。 |

以上事实均按同一个已确认提交检查；对本次修复不依赖的运行时安装细节不作不存在或不支持的断言。Codex 的 `.apm/agents` 文件是本仓库的代理说明来源；不把它误当成官方定义的 `.codex/agents/*.toml` 原生配置文件。

## 3. 原因、负责方和冻结修复方案

**因果链**：发布的示例自身 `text` 与 `refs` 不一致 → 模型可能按错误示例提交叙事对象 → 第 2 阶段原有校验拒绝结果 → 补正三个示例可让按示例填写的引用契约一致；测试先检查原始示例，才可防止同类示例错误被合法夹具掩盖。

**负责方**：仓库内两份 analyzer 说明分别拥有对应运行环境公开给模型的示例；`contact_state.py` 拥有 `stage2-plan` 返回的示例；`test_stage2_narrative_example_contract.py` 负责检验这三份示例。不得在模型输出处理、外部测试夹具、Codex 原生委派或下游阶段补偿示例错误。

### 3.1 产品修改点（只作以下最小语义变更）

| 位置 | 修改 | 保持不变 |
| --- | --- | --- |
| `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md` 的叙事 JSON 示例 | 从 `refs` 删除多余的 `later:ITEMKEY`，使其仅列 `paper:ITEMKEY`、`gap:GAPID` | 示例的 `text`、三项具体例子字段、其他 Stage 2 说明、委派方式 |
| `packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md` 对应示例 | 同上 | OpenCode 原生委派方式及其他说明 |
| `.apm/skills/professor-contact/scripts/contact_state.py` 的 `cmd_stage2_plan` 叙事 `result_schema` 示例 | 在 `refs` 增加 `gap:GAPID` | `text`、`model_input`、引用池计算、校验器、方向身份与正式输出 |
| `.apm/skills/professor-contact/tests/test_stage2_narrative_example_contract.py` | 先检查原始示例引用，再对原样例做可追溯的合成 ID 绑定，最后通过现有 runner 验证 | 原有 `BaseEnv` 与 Stage 2 正式预检准备、三项具体例子字段的保留检查 |

该选择保留两份代理示例已有的 `P/G` 说明性文本，避免仅为展示第三种引用而扩大样例范围。备选方案是在代理 `text` 新增 `{{L:ITEMKEY}}`；这也可满足集合相等，但必须为后续论文另外选择合法测试标识，且本议题无需示范 `L`。`L→later` 的正式支持继续保留，主文规则仍说明其用法。另一备选“只把测试换成合法夹具”无法检查原示例，拒绝采用。

### 3.2 测试修改的执行约定

1. **原始检查先行**：从 Codex/OpenCode 的 `narrative` 小节现有 JSON 代码块分别解析示例；从 `stage2-plan` 的 `narrative` job 取得第三份 `result_schema`。对每个 `positioning` 块按 `P→paper`、`L→later`、`G→gap` 从其**原始** `text` 提取引用，逐项确认与原始 `refs` 集合相等、`refs` 无重复。不得先覆写示例、放宽检验或修改产品校验器。
2. **反例证明测试会失败**：在测试内以独立拷贝构造代表性错误：一份 `refs` 多出无占位符的 `later` 引用；一份 `text` 有 `G` 占位符而 `refs` 缺少 `gap`。原始检查必须拒绝这些错误；不需以模型或外部代理触发。
3. **只绑定合成标识**：原始检查通过后，对原示例作拷贝，用 `BaseEnv` 中的合法 `item_key` 和真实合成 `gap_id`，分别替换 `text` 内的 `{{P:ITEMKEY}}`、`{{G:GAPID}}` 和 `refs` 中的 `paper:ITEMKEY`、`gap:GAPID`。若当前示例含 `L`，同样只可绑定到 `model_input.later_papers` 的合法标识，不能擅自从其他池借值。保留示例自己的叙事句子和引用对应关系，**绝不将 fixture 的完整 `text` 或 `refs` 复制进示例**。
4. 将示例中的说明性方向字段绑定到合成方向的 `DIR00001`，保留源示例采用的是 `direction_id` 还是 `collection_key`；`gap_notes` 的说明性 `gap_id` 绑定到当前合成 gap；格式占位值 `kind="para|bullet"` 实例化为现有校验认可的 `para`。这一步仅为合法输入实例化，不改变生产示例、业务校验或输出格式。
5. 沿用现有 `run_bound_stage2_plan` / `run_bound_stage2_finalize` 和合成的上游 Stage 0/1/2 预检证明，让正常例子通过 `stage2-finalize`。检查最终 `套磁候选输入.json` 的叙事包含绑定后的引用及原示例的三个具体例子字段。需确认 `status=ok`，不能仅以 JSON 可解析替代 runner 的业务结果。
6. 改测试时维持原测试文件的三个来源入口；可在测试文件内部重组现有 `check_example` 等辅助函数，不要求固定私有辅助函数名，也不新增通用判定程序或单独测试服务。

## 4. 正式测试计划（依据 Test Engineer Rule）

本次唯一必测清单只覆盖 Issue #87 已确认目标与直接改变的行为；测试工程师在本计划内维护执行步骤。不得扩充为 Codex/OpenCode 的完整代理运行、模型输出采样或全仓回归。

| 业务目标 | 输入/场景 | 预期业务结果 | 唯一检查入口 |
| --- | --- | --- | --- |
| 公开示例自身引用对应 | 两份代理说明的原始 JSON、`stage2-plan` 原始 `result_schema` | 三份的每个叙事块都满足占位符集合等于不重复的 `refs` 集合 | 现有 `test_stage2_narrative_example_contract.py` 扩展的原始示例检查 |
| 错误不能被合成夹具掩盖 | 原始检查入口接收“多一个 refs”或“少一个 refs”的合成错误副本 | 检查拒绝错误副本，说明校验发生在绑定合法标识之前 | 同一测试文件中的直接反例检查 |
| 合法示例仍可完成已有业务 | 三份原样例经合法的合成 `paper/gap/方向` 标识绑定，保留三项具体例子字段 | 当前 runner 返回 `status=ok`；产物保留叙事引用、三个字段；两种方向字段写法仍由原校验兼容 | 同一测试文件的现有 `stage2-finalize` 执行与产物检查 |

**本地执行路径**：从目标仓库运行下面命令（该文件以同目录测试辅助模块作导入，不需要启动 Codex、OpenCode、模型、浏览器或 Zotero）：

```bash
cd .apm/skills/professor-contact/tests
python3 -m unittest -v test_stage2_narrative_example_contract
```

以测试工程师当前环境实际执行结果为准；本文件未运行上述命令。此文件内的测试在系统临时目录使用合成教授、论文、gap 与预检状态；不得接入真实用户目录。正式尝试记录当前代码提交、命令、通过/业务失败/无法判断/未执行与必要错误输出，临时运行内容保存在仓库外独立目录，不上传敏感或原始运行资料。

**失败处理**：原始例子集合不一致是本议题内的业务失败，应修正相应发布示例；实例化后出现 `unknown_reference_id`，先检查是否将示例标识绑定到了正确的合成 `papers` / `gaps`；不得放宽正式 `validate_narrative_entry`。如上游预检或本地依赖中断而未形成可判断结果，标记无法判断，修复环境后仅重跑受影响项。没有外部模型请求和带副作用的服务调用，本计划不安排外部故障正式重试；业务失败不以重复采样消除。

## 5. 影响、兼容、风险与反例

- `intended_change`：三处示例引用集合正确；直接测试在替换测试标识前检查原始示例，并能拒绝不一致副本。
- `preserved_behavior`：`PLACEHOLDER_RE` 和 `validate_narrative_entry` 的类型、重复项、合法引用池、错误状态、`direction_id`/`collection_key` 兼容；Stage 2 facts、指纹、预检、写盘、真实输入与渲染输出；Stage 3–5 事实来源与流程；`L` 引用仍被正式支持。
- `approved_behavior_change`：Issue #87 已授权修正说明性示例与直接测试；正式运行时语义、状态和外部接口 **没有获批变更**，所以不得改变。
- `prohibited_side_effect`：不增删三个具体例子字段，不把原示例改成实际论文信息；不改 JSON schema、引用作用域、兜底路径或校验拒绝条件；不引入新依赖、额外原生 Codex 委派检查、跨阶段更改或其他仓库改动。
- `compatibility/identity`：旧 `collection_key` 与新 `direction_id` 在本次保持并存；用于生成合法样例的测试 ID 必须来自同一 `model_input` 范围。P、G 的相同字符串前缀不等于相同引用类别，必须按类别映射。
- `state/lifecycle/concurrency/fallback/cleanup`：产品只改变静态说明示例，不写新状态、不改变重试、并发、fallback 或正式清理行为；测试仅用已有临时目录自动清理。不存在迁移步骤。
- `observability`：保留当前 runner 的 JSON `status/reason_code` 与正式输出文件；只用同一已有测试检查可见结果，不新增跟踪或证据接口。
- **代表性反例**：① `text` 有 `P/G` 但 `refs` 只列 `paper`：原始检查失败。② `refs` 含 `later` 但 `text` 没 `L`：原始检查失败。③ 原示例正确但绑定时取了清单外 ID：现有 runner 保持拒绝，不能改写业务规则迎合测试。④ 两种方向标识写法：保留现有兼容，不要求统一成某一种。⑤ PR #86 后续可能修改 Stage 2 校验交接：若其提交进入基线，只复核两者共同触及的已确认行为，不能合并本议题与 #86 的修复范围。
- `critical unresolved impacts`：当前已核对的基线下无。若实施时发现三份示例之外确有同一发布来源被修改，先记录准确来源、对本目标的直接影响及最小范围，再按 Plan Reviewer Rule 处理修订；不得自行扩大功能要求。

## 6. 本地代理执行次序与交接

1. **计划审核关口**：先由独立审核者按本文件、Issue #87、上述代码基线和三个规则审 P1–P4。计划作者不得自报 `PASS` 或 `APPROVED`。未取得 `Plan conclusion: APPROVED`，只维护本计划，不开始正式产品修改。
2. **确认工作树**：从本 PR 分支继续工作，记录实际 HEAD；若 `main`、PR #86 或上游变动，仅检查会影响上述四个目标文件及约定的语义变化。无关 SHA 变化无需重开已成立结论。
3. **修改两份代理示例**：分别删去那一项 `later` 冗余引用；其余说明保留。两种运行环境的修改必须放在各自本仓库的源文件，不能只改某个本地已安装副本。
4. **修改 runner 示例**：只在对应的 `result_schema.positioning[0].refs` 补入 `gap:GAPID`，不要触碰校验器或任务 `model_input` 的真实业务列表。
5. **改现有测试**：按第 3.2 节先检查原始三份来源，再用原示例做合成标识绑定、调用正式 Stage 2 runner 并检查产物；包含第 4 节两类不一致副本。删除原测试里用夹具整体覆盖 `text`、`refs` 的代码。
6. **运行仅本次必测项**：执行第 4 节的已有测试文件；有业务失败就修复改动范围内的根因，不改期望值求通过。留下脱敏的实际版本、测试命令、结果与尚未完成项目；未执行不得写成已通过。
7. **审查与完成**：提交本 PR 上的产品、测试变更，先完成适用的正式测试关口，再按 Merge Reviewer Rule 审是否可合并。仅审核通过后解除草稿并申请合并。合并本 PR 时由正文的 `Closes #87` 关闭 Issue；不提前手动关闭。

**后续实施者边界**：本次只有一份在 `plan/` 下维护的正式方案；PR 评论仅引用本文件及其版本。此 PR 提交计划之后仍是草稿，后续实现不得转到另一拉取请求，也不得将本计划的审核待定状态冒充通过。
