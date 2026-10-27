# 兴趣段字数不计论文标题 — 执行计划 EP1

- Requirement revision: R1（2026-10-27，用户明确要求除论文标题之外计数，并授权单独小范围双计划 PR）。
- Plan revision: EP1；Proposed review status: pending。
- Target repository revision: `ScholarWorkflow/professor-contact@b67dd3ca4d29dfc78f57988564b219c71b582674`（main）。
- 本 PR 只提交计划和必要审核记录；不修改产品或测试实现，不执行正式测试，不合并。独立于 PR149 方向素材；不修改 PR149。

## 1. 需求与边界

兴趣段仍为三部分；仅其实际引用、与当前邮件包 `papers[].title` 逐字一致的完整论文标题文本不计入字数。外围书名号、引号、标点、连接词及其他正文照常计数。保持当前 Python `len(str)` 字符口径；三字符串分别计数，渲染新增的分隔换行不另计。净正文 >180 警告、>200 拒绝，180 和 200 本身不越各自阈值。

标题真实性、②引用 1–3 篇及共同主题逐篇成立、①真实关注、③宽泛例子、未来志向、source_map、模板与既有邮件保护规则不变。不引入标题缩写、模糊匹配、Unicode 归一化或任意引号内容豁免；不改 Stage 4 邮件包、schema、来源指纹或 profile。不把该计数改动扩为标题语义校验器。

授权依据：本 ChatGPT 对话中用户“最后生成的邮件兴趣段，论文标题能不能不进入字数限制，即除掉论文标题以外的部分才进行限制”及“那没问题，单独走小范围双计划吧”（2026-10-27）。该变化会放行原来因标题过长而拒绝的结果，按常规方案及测试审核，不称快速合并或已实现。

## 2. 事实、因果链与 owner

以下均为上述固定 main 的描述性事实，不自行升级为新需求。路径前缀为 `.apm/skills/professor-contact/`。

| 决定 | 已核事实与固定版本来源 |
| --- | --- |
| 修改 producer 共享计数，而非客户端截标题 | [`scripts/_stage5_email.py#L112-L127`](https://github.com/ScholarWorkflow/professor-contact/blob/b67dd3ca4d29dfc78f57988564b219c71b582674/.apm/skills/professor-contact/scripts/_stage5_email.py#L112-L127) 的 `validate_email_raw(email, raw)` 当前 `sum(len(s) for s in sentences)` 包含标题；`contact_state.py` 的阈值为 180/200。 |
| plan 与 finalize 同口径 | [`scripts/_stage5_commands.py`](https://github.com/ScholarWorkflow/professor-contact/blob/b67dd3ca4d29dfc78f57988564b219c71b582674/.apm/skills/professor-contact/scripts/_stage5_commands.py) 的 plan-with-result 与 finalize 均调用该 validator；finalize 在写入前检查错误。 |
| 不改最终正文 | [`scripts/_stage5_email.py`](https://github.com/ScholarWorkflow/professor-contact/blob/b67dd3ca4d29dfc78f57988564b219c71b582674/.apm/skills/professor-contact/scripts/_stage5_email.py) 的 `assemble_draft` 原样拼接兴趣段；标题列入保护字符串。 |
| 同步生成要求，不新造验证链 | `_stage5_commands.py` 的 `model_input.rules.interest`、`SKILL.md`、`docs/stage5-legacy-contract.md` 明示总长；[email-validator agent](https://github.com/ScholarWorkflow/professor-contact/blob/b67dd3ca4d29dfc78f57988564b219c71b582674/.apm/agents/professor-contact-email-validator.agent.md) Rule 3 已要求标题与包中 title 逐字一致。 |

因果链：标题挤占正文限额 → 共享 validator 当前计全部字符 → 在该 owner 内对可信标题的完整逐字引用免计 → plan/finalize 使用净正文阈值 → 长标题不再挤压正文，但正文限制及标题真实性不变。配置、错误输出和写入生命周期仍由现有 Stage 5 runner 拥有。

## 3. 冻结方案与实施顺序

1. 在 `validate_email_raw` 使用邮件包中非空字符串标题作为唯一豁免来源，对三部分中实际完整逐字引用的标题跨度免计；同一字符跨度不能重复扣除，不跨部分拼出标题。标题之外字符仍按原口径计数。不得通过删除任意引号内容、删除纸面关键词或仅信任模型声明来扣数；不修改原始正文。
2. 复用现有共享 validator、阈值常量及 warning/error 通道，提示中的数字表示免计标题后的正文长度。保留所有现有结构、来源和写入前校验。局部 helper/匹配写法由实现者选择，不建设匹配框架。
3. 同步 `model_input.rules.interest`、`SKILL.md`、`docs/stage5-legacy-contract.md` 中相关字数表述及 email-validator 的计数口径；generator 继续引用正式契约，仅在存在冲突措辞时同步。保留真实标题完整输出与 ② 既有规则。
4. 测试工程师按同目录 TP1 补齐最小针对性检查及实际 selector；实现负责人提交实现后，由独立 reviewer 核对方案符合性，再按适用测试关口取得结果。本文不是实施或测试已完成的证明。

替代方向：直接提高总字数上限不能实现“标题不计、正文仍受原限制”；让模型自行报净字数无法使正式 validator 一致。故选择共享确定性计数，不改模型结果格式。

## 4. 影响与风险

- intended_change / approved_behavior_change：仅净正文长度决定既有 warning/hard rejection；来源为 R1。
- preserved_behavior：既有合法三部分结果仍合法；旧四部分仍拒绝；无引用标题的结果计数不变；标题逐字真实性及 1–3 篇要求不变；模型 JSON、source_map、原文渲染、未来志向与模板不变。
- prohibited_side_effect：不裁剪标题或正文，不把非标题引用文本免计，不改变阈值，不改写已保存邮件，不自动重跑 Stage 2/4，不变更指纹或持久化格式，不混入 PR149。
- invariant：免计集合只能来自本邮件包的实际完整标题引用；其余字符仍受原阈值，正文不因计数而变化。任意带引号长文本不能作为豁免；完整标题中含另一标题时同一跨度不能扣两次。这些用于静态方案核对，不要求边界组合穷举。
- compatibility / failure：只放宽标题占字造成的警告/拒绝；其他拒绝及写前保护保持现状。无迁移、清理或额外并发状态。若产品实现改变以上约定，先修订受影响方案及测试项，不以文档 SHA 变化重跑无关结果。
- Critical assumptions / unresolved critical impacts: 无；未来实际实现 selector 尚未确定仅为执行顺序前提，不是已验证结果。

## 5. 规则与交接

采用 [Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)、[PROJECT_CONSENSUS](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)。执行方案状态仅由独立审核记录给出；作者不自授 APPROVED。下一负责人：方案审核者复核 EP1；测试审核者复核 TP1 清单；获批后产品实现者实施，测试工程师补 recipe，执行者记录结果。
