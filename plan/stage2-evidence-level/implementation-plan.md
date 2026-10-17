# Stage 2 固定证据展示、失败登记与分析级别修复

- Requirement revision：2026-10-17 用户要求为此前 U1、U5 两项修复建立独立计划 PR（北京时间）；依据用户提供的《PR91未覆盖问题报告_20261016.md》。报告中的私人实际数据与失败次数不是本计划已复验结果。
- Plan revision：contact-evidence-level-r4；Proposed review status: pending。
- 目标：ScholarWorkflow/professor-contact，源码基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`。本 PR 当前只提交计划；实现、测试执行和合并均未完成。
- 唯一测试计划：[test-plan.md](test-plan.md)。按 [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)执行。

## 1. 范围与验收目标

U1：固定证据卡正文不泄漏内部论文编号；真实文字阻挡必须能登记，说明处理归属，不能因模型无权改事实而连失败也无法记录。作者原句、译文、出处、时效结论、署名、用户笔记与红线不得被文字修订改写。

U5：全文/摘要统计取实际成功分析的级别，不能用分析文件存在或 PDF 存在代替。级别缺失、失败或不明不能自动冒充全文或摘要。

不包含 U2/U4 分句、U3 跨页 sidecar、成员归属重构、Stage 3—5、新 Nix 安装、全教授业务重跑、额外去重统计。遵守 [Nix 单源边界](https://app.notion.com/p/3fb0101a85f38185b17adb417590e50e)：改正式业务源，不在安装产物或 Nix 层补另一套业务实现。

[PR91](https://github.com/ScholarWorkflow/professor-contact/pull/91) 当前 `b0991da8e0b0f9456acbcdd79dece96c53164dec` 的执行 r3 / test-r3 处理另外三项缺陷，本 PR 不复制它的全套修复与测试。两者若先后落地，只合并重叠的记录器/普通 finalize 生命周期改动；PR91 的“不可修订区域拒绝”在本 PR 的新授权范围内改为“允许记录、禁止模型改写”。不存在必须等待 PR91 全部业务完成的依赖。

## 2. 决策依据（当前源码事实，不替代需求）

下列行号均对应上述基线的 [contact_state.py](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py)。

1. 展示归 runner：L4042–4055 接受非空 model_evidence，L4286–4293 带入 gap，L4481–4518 原样写固定卡 evidence/completed_part/remaining_gap 及禁锚区 evidence；因此模型合法机器结果中的 item key 可泄漏。既有 `redact_item_keys`（L4236–4243）可作局部复用，但其未知编号替换不能冒充已核验引用。
2. 登记与修订权限是两回事：`stage2_validation_report` L10716–10989 已做报告/正文/方向绑定；L10980–10984 把不属于 narrative 的 blocking 拒绝。`stage2_require_recorded_validation` L10992 起又要求先登记，所以固定区阻挡没有处理路径。
3. 仍可保持 fail closed：`stage2_validator_accepts` L3609–3654 仅接受有效绑定的 terminal pass/skipped；`stage2-refine-plan/finalize` L11088–11243 是唯一 narrative 修订入口。新增失败记录不能使通过门槛放宽。
4. 实际分析级别已存在于 Stage 2 写入的索引：Codex analyzer [L339–380](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L339-L380) 明确成功的 pdf/ocr 路由为 fulltext、abstract_json 为 abstract。它的 [L405–430](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L405-L430) facts 示例漏传级别；runner L4323–4334、L4720–4740 规范记录也未保存级别，L4384–4386 错用文件/PDF存在计数。
5. 已有分析级别与 facts 可用性不同：analyzer L263–274 允许 OCR-only fulltext 分析而 facts unavailable。不能用 facts_state 反推分析级别。
6. analyzer 的 [Step 2.6 L142–159](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md#L142-L159) 在 reuse_all 时不进入 facts 准备或 finalize；因此仅在 finalize 比较 level 或增加渲染版本，无法发现同版本下成功分析索引的级别变化。
7. `Stage2PackRefineContext` L1707–1765 已提供临时 facts 过期后的持久包展示上下文，但它不是完整业务 facts；普通 finalize 仍依赖 facts，不能将该上下文伪装成 facts 重验/重签旧 resolved 结果。
8. preflight cheap inputs L3352–3381 不读取分析索引，`_artifact_guards_for_keys` L3411–3444 只登记已有路径且已存在的文件；现状不能仅凭“旧 guards 未变”排除新增分析/sidecar 或索引换址，不能直接据此批准仅展示刷新。
9. 普通 finalize L5020–5080 可能不重绘、继承旧 validator；升级展示和级别后必须只使受影响生成物失效，不能重新绑定旧 PASS。PR91 §3.4.1 已设计实质变化/等价重写区分，可复用同一实现，不另建历史系统。

## 3. 实施方案

### 3.1 固定证据展示

- runner 使用当前可信论文元数据及 `candidate_paper_ids` 解析已知 item key，在固定卡 evidence、completed_part、remaining_gap 及禁锚区 evidence 的既有人读展示出口统一显示题名及 Zotero 链接；编号仅留机器字段或链接目标。保留原 model_evidence 和候选引用列表，不改变 freshness 判定、不删整段依据。
- 已知编号出现在说明句时只做等价引用替换，保留其余文字含义；不改作者 quote、translation、status；completed_part、remaining_gap 和 evidence 仅转换展示引用，其原始机器字段逐字保留，不改结论和原意。仅对上述生成出口作确定性格式化，不做全文清洗，不改用户笔记或作者引文。未知编号或引用缺可信题名不能猜标题/静默删除，明确报告所缺元数据并停止受影响生成，交 Stage 2 数据准备者补齐后重试。
- 固定卡术语需要解释时由已有 narrative.gap_notes.explanation 承担独立说明；不将作者原句/译文变成可自由重写字段。固定模板的措辞缺陷交 runner 实现者，事实或译文错误交其原 producer，用户笔记保持用户所有。
- 新鲜构建和 pack-only 重渲染都从输入包的可信引用元数据取得同样展示。将上述展示出口实际引用的题名/年份持久保存或复用已有可用论文映射；仅有事实关联不扩大 supporting_item_keys 或 narrative 的 P/L 引用许可。缺少旧元数据要求从正式 Stage 2 准备刷新，不能从正文反解析。

### 3.2 真实失败可登记，权限不扩大

- 保留原始报告格式、精确位置/方向归属、当前正文及输入包摘要校验；先完成这些合法性检查，再把 blocking 分为现有 narrative 可修订项与允许校验的固定证据卡项。不得仅把 require_repairable 改成 false 后把全部问题发给模型。
- 报告合法时原样保留 issues/notes/raw verdict，仍在既有 validator schema 2 中按当前合法轮次登记；第一轮 blocking 为 needs_correction。增加最小的固定区阻挡及责任说明字段（字段名称为实现细节），不改原报告、不新增通用状态机/问题库。
- 用户笔记、论文一览等现有明确跳过区域仍不属于合法校验对象，相关报告继续拒绝，不因本修复扩大校验范围。只要本轮含合法固定证据卡阻挡（包括混合报告），refine-plan 返回明确的“需修复源数据或生成器”结果、零 rewrite jobs；refine-finalize 同样拒绝写入。调用方停止自动修订/校验循环，报告具体引文和责任归属，不自动再次运行相同失败。
- 仅 narrative 阻挡仍走现有一次修订→第二次校验。固定区阻挡不被写成 pass/skipped；第一轮发现固定阻挡时仍是第一轮真实未解决失败，不写 fail_after_2_rounds；如果第一轮只有 narrative 问题、合法修订后第二轮首次发现固定卡阻挡，则照常登记 terminal/fail_after_2_rounds 并交源 owner，不降回第一轮、不再发修订。后续直接提交第二轮或伪造修订完成不得越过既有顺序校验。
- 生成器/正式源修复后，通过正常 Stage 2 finalize（业务源变化）或 §3.3 受保护展示刷新（仅展示变化）重建受影响受管正文，旧报告留在原路径。只有校验依据实质变化才失效旧 validator，并对新业务版本重新开始校验；相同正文或仅时间戳变化不能清零两轮限制。正常 narrative refine 的正文变化不属于重开版本，必须保留原第一轮/问题直到第二轮。
- 同步主 SKILL.md、两个 analyzer 安装投影的 Stage 2 分支说明；style-validator 保持现有文字标准，不通过屏蔽固定卡或放宽 C8 求通过。两种 harness 只同步已有业务交接，不新增委派机制。

### 3.3 分析级别贯通、分流与兼容

1. **级别来源与统计。** Stage 2 analyzer 在正常成功分析/导入后，从教授 `论文分析/_index.json` 的相关论文记录读取实际 level，并在 facts.papers[] 增传 `analysis_level`（fulltext/abstract/null）；失败、未完成、陈旧或缺失级别为 null，非法枚举报输入错误。不从文件存在、PDF 或 facts_state 推断；OCR-only 成功全文仍为 fulltext。保持原 projected direction papers 集合，只统计全文/摘要/未确认三类及合计，不新增去重。同步两个 analyzer 和 SKILL。
2. **只保存必要的当前接受基线。** 正常业务处理成功写 pack 时，扩充既有 cache.preflight.resolution_evidence_guards/方向 artifact_guards 的缺失状态，加上有限索引选择状态，保存本次实际消费的分析来源投影，从当前正式 sources 采集并与该 accepted pack 同次成功落盘，不能把进入预检时的旧投影当新接受基线。范围沿用现有 stage2_candidate_universe/selected_candidate_union，即所有被选方向候选并集（覆盖方向相关/缺口及 resolution 来源），不能仅看最终入选论文。每个相关 key 的 analysis/future_work/facts/pdf 类型都明确保存无路径、路径不存在或存在状态；已有路径保留规范路径和现有文件 guard/已得摘要。读取当前索引的对应记录/路径（含 file、future_work_sidecar、facts_sidecar 及关联输入映射），仅记录实际分析/事实证据路径及成功/可用状态；不比较整条索引 JSON，generated_at、kb_entry_id 等管理字段不构成业务变化，纯展示 level 单列。索引解析及既有 Step 6.7 的 analysis_file 派生 .facts.json/.future_work.json 探测规则用于构造当前同一清单（即使索引未填 sidecar，派生路径也保存缺失占位），使新增路径、原缺失路径出现、删除、换址或同址 guard 变化均能被看见。无法由持久输入确定某一来源时标为不可比较，不能省略后当作未变。不遍历无关目录，不读 PDF 正文或新增全文件哈希扫描，不建立通用来源认证系统。
3. **先判业务变化，再判展示变化。** preflight 在 reuse_all 前重读上述当前投影，并比较已接受基线及现有业务 inputs/guards。来源 key/type 集合、存在状态、路径、成功资格/业务字段或文件 guard 任一变化，或旧基线缺失/不完整、当前索引不可读、来源映射不明确，均不能证明事实输入未变，返回原 process 路径并明确原因。未知→fulltext 若伴新增分析或 facts，必须 process；只有完整可比较且业务依据全未变、差异仅 level 或私有 render version 时，才进入仅展示刷新；全部未变才可 reuse_all。原 process 保留既有按实际变化选择处理与复用规则，不要求所有模型无差别重跑。两种 analyzer 同步分流，不得将“旧 validator 未通过”本身当作分析依据变化。
4. **仅展示的正式入口。** 在既有 runner 复用 `Stage2PackRefineContext`、renderer、教授 lease/原子 JSON 与 managed_write，读取已接受 pack 的规范论文、方向、模型结果和引用元数据，以及本次只读索引/预检投影。不依赖旧 /tmp facts，不重建完整历史 facts，不重签旧 resolved proof。只更新 analysis_level、展示/缓存版本与渲染绑定，并同步因这些字段实际受影响的 accepted_directions_sha256 等包完整性摘要，避免下次误报 pack_integrity_mismatch；不调用依赖完整 facts 的 stage2_preflight_metadata 伪造接受元数据。保留 accepted assignment、事实判断、叙事、freshness 结果和模型指纹；不产生新分析/归属/时效任务。成功刷新不能把业务变化的当前来源冒充新的接受基线；业务来源基线仅由正常处理成功建立，展示刷新只保留已验证相等的业务部分并推进展示部分。
5. **写前再核同一输入。** 沿用教授/pack/正文归属、受管摘要和输入漂移检查，重新读取与预检相同的业务来源及 level 投影，确认仍为该 accepted pack、相同业务基线和本轮 level；任一漂移不写并交重新处理。手改正文按 managed_write 保护。正文/校验依据实质变化按 §3.2 失效旧 validator，不借新绑定沿用旧 PASS；等价重写不清轮数。不新增锁、journal 或认证框架。
6. **字段与旧数据。** `_CANONICAL_PAPER_FIELDS`、build_direction_pack、_canonical_record、fresh/reused/resolved records 与 pack-only context 保存级别，同 key 一致合并，当前正式来源不得被旧记录覆盖。`paper_digest` 及 resolve/freshness 模型摘要不加入 level、render version 或展示投影。旧包缺 level 可显示未确认；旧包缺可比较业务基线走原 process，不从历史 Markdown/临时 facts 猜造基线。资料不足导致正常流程不能完成时真实报告停止，保留原数据，不强制所有坏旧包成功。只在受影响的下一次调用按上述分流更新，不批量迁移或为文档 SHA 重跑。


## 4. 顺序、安全和替代方案

1. 实现者先核最新基线及 PR91 是否已落地，保留其位置解析/摘要/轮次/成员保护；只整合本计划涉及的交接。
2. 先贯通可信级别与固定证据引用元数据，补齐现有 guards 的缺失/来源状态及接受基线，再按 §3.3 分流改展示刷新；接着修改登记与 refine 分流，最后同步两个 analyzer、SKILL 及受影响现有测试。
3. 替代方案“开放所有固定区给模型改写”会改事实，排除；“只屏蔽校验或直接删除依据”掩盖缺陷，排除；选定方案在 runner 确定性展示、记录器保留失败，原 owner 处理问题。
4. 不新增并发锁或跨文件 journal，沿用已有教授写入 lease、原子 JSON 和 managed_write 保护；不自动覆盖人工文档、不重置用户选择、不改变成员归属。
5. 关键反例：abstract 有分析文件仍不能计 fulltext；OCR fulltext facts unavailable 仍可计全文输入级；旧包无级别应显式未知；固定+叙事混合阻挡不允许模型越权；同一未修复报告不能清轮数；正常 narrative 修订不应重开第一轮。
6. 实现结束交付实际提交、受影响路径和测试计划对应结果。计划当前未实施，测试关口待审/未执行，不自授 APPROVED 或 PASS。
