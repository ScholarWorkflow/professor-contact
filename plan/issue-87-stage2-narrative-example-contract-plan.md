# Issue #87：Stage 2 叙事示例引用一致性修复——正式实施与测试计划

## 1. 版本、依据与状态

- Requirement revision：[Issue #87](https://github.com/ScholarWorkflow/professor-contact/issues/87)，截至 2026-10-15T12:04:27Z 的正式需求；本计划不修改需求的业务边界。
- Plan revision：`issue87-narrative-example-contract-r7-2026-10-15`。本文件是该拉取请求的唯一现行实施及直接测试计划；本次纳入远端已记录的正式关口依据，并记录本地执行、审核和 rebase 后的提交状态，不改变 r1 已审核通过的业务目标、预期结果或范围。
- Target repository：`ScholarWorkflow/professor-contact`；取证与分支基线：`main@2a8601facb9f3bec96da6ac22c79586ca79560d7`。
- 适用项目规则：[Project Consensus](https://app.notion.com/p/rekidunois/Project-Consensus-3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/rekidunois/Plan-Reviewer-Rule-3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/rekidunois/Test-Engineer-Rule-3d80101a85f380d8a8f5ce528141e253)。
- Codex 官方资料：[子代理及自定义代理](https://developers.openai.com/codex/subagents)、[命令行参考](https://developers.openai.com/codex/cli/reference)，核对日期 2026-10-15。本改动只涉及仓库维护的代理说明示例和确定性运行器示例，不改变 Codex 原生代理配置、委派方式或命令参数。官方文档不规定产品专用的 `positioning[].text` / `refs` 对应关系；该约束来自本仓库的正式需求和运行器。
- 实施计划审核：`APPROVED`（P1–P4），依据 [实施计划审核记录](https://github.com/ScholarWorkflow/professor-contact/pull/88#issuecomment-6192062638)，审核对象为 r1、提交 `82f88e6a11b2aa73d91f72c1a8bcbb4342f4fb33`。
- 测试第一关：`PASS`（必测清单），依据 [测试关口审核记录](https://github.com/ScholarWorkflow/professor-contact/pull/88#issuecomment-6192906371)，审核对象为 r2、提交 `2c594141eb84626479236ed707022e6b1c07e96f`。第二关：`PASS`（r2 执行步骤；同一记录）；r4 经追加的 `uv run` 命令复核后也通过，测试范围未变。第三关：`PASS`（r5 正式结果复核，结论记录于本版）。
- 当前状态：三处产品示例已按批准范围提交；第二、第三关已通过，正式测试 4 项全部通过。合并审核待完成；PR 仍为草稿，不代表已获准合并。
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

1. **先读原样例**：Codex 与 OpenCode 示例从各自说明文件的 `` `narrative:<教授>:<方向>` `` 小节首个 `json` 代码块用标准库 `json` 解析；运行器示例从 `run_bound_stage2_plan` 返回的 `kind="narrative"` 任务记录读取 `result_schema`。在任何标识替换前，对每个 `positioning` 块用 `{{([PLG]):...}}` 提取占位符；`P` 表示论文、`L` 表示后续论文、`G` 表示研究缺口，并据此转成“类型、标识”集合；确认该集合等于 `refs` 集合且 `refs` 列表无重复。不得先覆写 `text`/`refs`、放宽检查或修改产品校验器。
2. **验证检查会拒绝两类错误**：在同一个测试文件里构造一个合法的最小合成样例副本，再分别构造“`refs` 多出无占位符的 `later` 引用”和“`text` 有 `G` 占位符但 `refs` 缺少 `gap`”两个副本；直接调用同一原始契约检查，确认两者都被拒绝。无需运行模型或外部代理。
3. **仅绑定来自同一任务输入的合成标识**：对原始检查通过的样例做深拷贝；从叙事任务记录的 `model_input.papers[0].item_key`、`model_input.gaps[0].gap_id` 取得 `P/G` 的合法值。只有样例实际含 `L` 时，才从 `model_input.later_papers[0].item_key` 绑定 `L`；没有合法值时保留失败，不从其他数据池借值。只替换占位符和 `refs` 中的说明性标识，保留原示例叙事句子，不把合成输入中的完整 `text` 或 `refs` 覆盖进示例。
4. 将示例中的 `direction_id` 或 `collection_key` 绑定到同一任务记录的 `model_input.direction_id`，保留原字段名称；将 `gap_notes[].gap_id` 绑定到该任务记录中的合成研究缺口；仅把格式占位值 `kind="para|bullet"` 实例化为 `para`。不改变产品示例或业务校验。
5. 用 `BaseEnv.write_stage2_results` 建立当前隔离的合成第二阶段输入，再将绑定后的示例写入该临时 `narrative.json`，经既有 `run_bound_stage2_finalize` 执行。检查运行器返回 `status="ok"`，并在 `套磁候选输入.json` 检查保存的 `text`、`refs` 及三个具体例子字段。保留现有第一至第三阶段的预检准备入口，不补造身份或预检证明。
6. 维持既有测试文件和三个来源入口；在该文件中添加检查辅助方法与反例，不新增通用判定程序、服务、依赖或独立脚本。

## 4. 正式测试计划（依据 Test Engineer Rule）

本次唯一必测清单只覆盖 Issue #87 已确认目标与直接改变的行为；测试工程师在本计划内维护执行步骤。不得扩充为 Codex/OpenCode 的完整代理运行、模型输出采样或全仓回归。

| 业务目标 | 输入/场景 | 预期业务结果 | 唯一检查入口 |
| --- | --- | --- | --- |
| 公开示例自身引用对应 | 两份代理说明的原始 JSON、`stage2-plan` 原始 `result_schema` | 三份的每个叙事块都满足占位符集合等于不重复的 `refs` 集合 | 现有 `test_stage2_narrative_example_contract.py` 扩展的原始示例检查 |
| 错误不能被合成夹具掩盖 | 原始检查入口接收“多一个 refs”或“少一个 refs”的合成错误副本 | 检查拒绝错误副本，说明校验发生在绑定合法标识之前 | 同一测试文件中的直接反例检查 |
| 合法示例仍可完成已有业务 | 三份原样例经合法的合成 `paper/gap/方向` 标识绑定，保留三项具体例子字段 | 当前 runner 返回 `status=ok`；产物保留叙事引用、三个字段；两种方向字段写法仍由原校验兼容 | 同一测试文件的现有 `stage2-finalize` 执行与产物检查 |

**准备与环境**：从仓库根目录通过 `UV_CACHE_DIR=/private/tmp/issue87-uv-cache uv run --no-project --python python3 python3 --version` 确认 Python 可用，并确认以下既有文件存在：`.apm/skills/professor-contact/tests/test_contact_state.py`、`.apm/skills/professor-contact/tests/stage2_upstream_fixture.py`、`.apm/skills/professor-contact/tests/gate2_evidence.py`、`.apm/skills/professor-contact/tests/issue64_test_support.py`、`.apm/skills/professor-contact/tests/_stage4_handoff_test_support.py`，以及 `.apm/skills/professor-contact/scripts/contact_state.py`、`.apm/skills/professor-contact/scripts/contact_targets.py`、`.apm/skills/professor-contact/scripts/contact_stage1.py`。测试仅使用 `Python` 标准库和仓库已有模块，无需安装额外依赖、配置模型接口、启动服务或访问真实用户目录。`BaseEnv` 为每个用例创建独立的临时目录；既有预检辅助模块在该目录生成合成输入，测试结束自动清理。

**有限预检命令**：可以运行 `UV_CACHE_DIR=/private/tmp/issue87-uv-cache uv run --no-project --python python3 python3 --version`、`UV_CACHE_DIR=/private/tmp/issue87-uv-cache uv run --no-project --python python3 -m unittest --help`，并用 `ls -l <上述文件路径>` 核对运行时、标准测试框架和本地依赖是否就位。`UV_CACHE_DIR` 将 uv 缓存放在当前允许写入的临时目录。不得用目标测试命令、`run_bound_stage2_plan`、`stage2-finalize` 或其他产品入口作预检。

**正式执行命令**：第二关通过后，在仓库根目录依次执行以下命令。测试结果和每次必要的失败记录写到独立系统临时目录；测试自身的教授、论文、研究缺口、上游状态及产品输出均留在临时目录中。

```bash
cd .apm/skills/professor-contact/tests
run_dir="$(mktemp -d "${TMPDIR:-/tmp}/issue87-narrative-example-contract.XXXXXX")"
set -o pipefail
UV_CACHE_DIR=/private/tmp/issue87-uv-cache uv run --no-project --python python3 -m unittest -v test_stage2_narrative_example_contract 2>&1 | tee "$run_dir/attempt-01.log"
```

执行记录至少写明实际产品提交、测试文件提交、命令、结果分类（通过/业务失败/无法判断/未执行）、必要错误摘要和日志路径；不保存真实个人数据或完整无关输出。本地测试准备阶段**不运行**上面的正式命令。

**有限预检结果（测试执行前）**：`UV_CACHE_DIR=/private/tmp/issue87-uv-cache uv run --no-project --python python3 python3 --version` 返回 `Python 3.14.6`；`UV_CACHE_DIR=/private/tmp/issue87-uv-cache uv run --no-project --python python3 -m unittest --help` 成功显示标准测试框架用法；上述测试辅助模块与三个运行器脚本均存在。首次未指定 `UV_CACHE_DIR` 的 uv 调用因默认缓存目录无写入权限而失败，改用允许写入的临时缓存后，两条有限预检命令均成功。已检查现有 `BaseEnv` 与预检辅助代码使用合成数据及临时目录，不依赖真实用户状态。该预检阶段未运行正式测试、计划运行器或产品入口。缺少输入：无。

**正式测试执行记录**：测试执行时的产品提交为 `030621e3076db6f2ee848c79211200ef1d1afbdf`，测试文件提交为 `2c594141eb84626479236ed707022e6b1c07e96f`。在 rebase 前工作目录 `.apm/skills/professor-contact/tests` 执行 `UV_CACHE_DIR=/private/tmp/issue87-uv-cache uv run --no-project --python python3 -m unittest -v test_stage2_narrative_example_contract`，退出码 `0`，4 项通过（1.418 秒）。日志：`/var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue87-narrative-example-contract.AhteQ2/attempt-01.log`。结果分类：通过；未见失败。rebase 后产品提交为 `f159c0ad3bbc7d8ae315511adfc127996a5ee955`；核对显示三处产品文件及测试文件与执行时版本内容相同，因此复用原结果，无需重跑。**第三关测试结果审核：PASS**；审核确认三项必测目标均由指定测试覆盖并通过，没有未完成测试项或已知失败。合并审核仍待完成。

**失败处理**：原始例子集合不一致是本议题内的业务失败，应修正相应发布示例；实例化后出现 `unknown_reference_id`，先检查是否将示例标识绑定到了同一任务输入的合成论文 `papers` 或研究缺口 `gaps`；不得放宽正式的 `validate_narrative_entry` 校验。如上游预检或本地依赖中断而未形成可判断结果，标记无法判断；修复环境后只运行受影响项，并按该次环境变化记录，不覆盖已确认的业务失败。没有外部模型请求和带副作用的服务调用，本计划不安排外部故障正式重试；业务失败不以重复采样消除。

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

**后续实施者边界**：本次只有一份在 `plan/` 下维护的正式方案；PR 评论仅引用本文件及其版本。此 PR 当前仍是草稿，后续实现不得转到另一拉取请求，也不得将尚未完成的合并审核冒充通过。
