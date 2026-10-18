# Stage 2 固定证据展示、失败登记与分析级别修复

- Requirement revision：2026-10-17 用户要求为此前 U1、U5 两项修复建立独立计划 PR（北京时间）；依据用户提供的《PR91未覆盖问题报告_20261016.md》。报告中的私人实际数据与失败次数不是本计划已复验结果。
- Plan revision：contact-evidence-level-r6；Proposed review status: pending（2026-10-18 七项修复的四块收敛方案待审）。
- 目标：ScholarWorkflow/professor-contact。原 U1/U5 源码基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`；本轮目标基线 `e1e8e48a0f4bee8e5d22acd61813dccd53ac9632`（r5 / t37）。r5 §3.4 已获[批准](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6248571193)并完成入口对齐，见测试计划 §10。当前[正式合并复审](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6250097095)为 NOT_READY，公开列出三项；本轮七项来自用户提供的逐项问题材料，不将其冒称该审核列出七项。用户 2026-10-18 授权更新两份计划；本轮仅修订文档，七项修复尚未实施、未执行测试，旧 PASS 只适用于其记录版本，不能授予 r6 批准或修复后的通过结论。
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
- 已知编号出现在说明句时只做等价引用替换，保留其余文字含义；不改作者 quote、translation、status；completed_part、remaining_gap 和 evidence 仅转换展示引用，其原始机器字段逐字保留，不改结论和原意。仅对上述生成出口作确定性格式化，不做全文清洗，不改用户笔记或作者引文。明确属于论文引用但缺可信题名时不能猜标题/静默删除，明确报告所缺元数据并停止受影响生成，交 Stage 2 数据准备者补齐后重试。普通日期、数字及无引用含义的文字不因匹配八位字符就被当成引用。
- 引用识别和展示同属 Stage 2 固定证据出口：`stage2_referenced_item_keys` / `stage2_collect_display_references` 与 `stage2_display_text` 使用一致的正式引用信息（规范论文映射、候选引用及完成论文引用），不能仅靠 `ITEM_KEY_RE` 判定任意八位文本。先保护经可信元数据核对、题名和目标均正确的已有论文链接，避免替换其地址或产生嵌套链接；裸 key 只有能由上述引用信息确认才转换。明确引用缺题名仍 fail closed，不能因引用收集漏掉它而降为普通文本。只做该出口的兼容修复，不全局修改 `ITEM_KEY_RE`，不改变机器 evidence、schema、freshness cache、Stage 3—5，也不要求模型改成 `{{P:...}}`。
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

1. **级别来源与统计。** Stage 2 analyzer 在正常成功分析/导入后，从教授 `论文分析/_index.json` 的相关论文记录读取实际 level，并在 facts.papers[] 增传 `analysis_level`（fulltext/abstract/null）；失败、未完成、陈旧或缺失级别为 null，非法枚举报输入错误。不从文件存在、PDF 或 facts_state 推断；OCR-only 成功全文仍为 fulltext。保持现有成员规则，按各方向 `supporting_item_keys` 的正式成员统计全文/摘要/未确认三类及合计；引用范围与规范 `papers` 映射不等于统计集合，不新增去重。同步两个 analyzer 和 SKILL。
2. **只保存必要的当前接受基线。** 正常业务处理成功写 pack 时，扩充既有 cache.preflight.resolution_evidence_guards/方向 artifact_guards 的缺失状态，加上有限索引选择状态，保存本次实际消费的分析来源投影，从当前正式 sources 采集并与该 accepted pack 同次成功落盘，不能把进入预检时的旧投影当新接受基线。范围沿用现有 stage2_candidate_universe/selected_candidate_union，即所有被选方向候选并集（覆盖方向相关/缺口及 resolution 来源），不能仅看最终入选论文。每个相关 key 的 analysis/future_work/facts/pdf 类型都明确保存无路径、路径不存在或存在状态；已有路径保留规范路径和现有文件 guard/已得摘要。读取当前索引的对应记录/路径（含 file、future_work_sidecar、facts_sidecar 及关联输入映射），仅记录实际分析/事实证据路径及成功/可用状态；不比较整条索引 JSON，generated_at、kb_entry_id 等管理字段不构成业务变化，纯展示 level 单列。索引解析及既有 Step 6.7 的 analysis_file 派生 .facts.json/.future_work.json 探测规则用于构造当前同一清单（索引未声明 sidecar 字段时，派生路径也保存缺失占位），使新增路径、原缺失路径出现、删除、换址或同址 guard 变化均能被看见。当前来源解析统一区分没有该 key 记录、相关记录为非对象（不可比较）、记录未声明字段、字段明确为空、已声明路径但文件 missing、present。只有无记录或未声明字段时才按既有兼容/派生规则选已确认来源；当前明确空路径不得由旧 pack/accepted projection 路径回填，sidecar 的显式空与未声明也不得混同。`stage2_artifact_guard_reason` 对 missing 路径重新检查是否出现，对 no_path 交同一当前来源投影判断是否出现路径，present 保留既有 stat guard；出现或无法确认均不得放行展示刷新。校验只限本次相关 key，不全库扫描。索引两侧都不存在且旧持久映射完整可比较的既有兼容路径保留；相关记录损坏不能当作无记录。无法由持久输入确定某一来源时标为不可比较，不能省略后当作未变。不遍历无关目录，不读 PDF 正文或新增全文件哈希扫描，不建立通用来源认证系统。
3. **先判业务变化，再判展示变化。** preflight 在 reuse_all 前重读上述当前投影，并比较已接受基线及现有业务 inputs/guards。来源 key/type 集合、存在状态、路径、成功资格/业务字段或文件 guard 任一变化，或旧基线缺失/不完整、当前索引不可读、来源映射不明确，均不能证明事实输入未变，返回原 process 路径并明确原因。未知→fulltext 若伴新增分析或 facts，必须 process；只有完整可比较且业务依据全未变、差异仅 level 或私有 render version 时，才进入仅展示刷新；全部未变才可 reuse_all。原 process 保留既有按实际变化选择处理与复用规则，不要求所有模型无差别重跑。两种 analyzer 同步分流，不得将“旧 validator 未通过”本身当作分析依据变化。
4. **仅展示的正式入口。** 在既有 runner 复用 `Stage2PackRefineContext`、renderer、教授 lease/原子 JSON 与 managed_write，读取已接受 pack 的规范论文、方向、模型结果和引用元数据，以及本次只读索引/预检投影。不依赖旧 /tmp facts，不重建完整历史 facts，不重签旧 resolved proof。只更新 analysis_level、展示/缓存版本与渲染绑定，并同步因这些字段实际受影响的 accepted_directions_sha256 等包完整性摘要，避免下次误报 pack_integrity_mismatch；不调用依赖完整 facts 的 stage2_preflight_metadata 伪造接受元数据。保留 accepted assignment、事实判断、叙事、freshness 结果和模型指纹；不产生新分析/归属/时效任务。成功刷新不能把业务变化的当前来源冒充新的接受基线；业务来源基线仅由正常处理成功建立，展示刷新只保留已验证相等的业务部分并推进展示部分。
5. **写前再核同一输入。** 沿用教授/pack/正文归属、受管摘要和输入漂移检查，重新读取与预检相同的业务来源及 level 投影，确认仍为该 accepted pack、相同业务基线和本轮 level；刷新入口及取得既有 writer lease 后、写入前，都重新读取与正常预检同口径的当前业务年份（当前实现为 `datetime.now().year`），与 payload 年份比较，不复用 payload 年份冒充当前年份。跨年或任一漂移均零写入并要求重新预检，由新预检决定后续分流。手改正文按 managed_write 保护。正常 finalize 与展示刷新共用 renderer 拥有的实际展示语义：比较最终可见内容（包括正式成员聚合计数、实际引用题名等），排除生成时间及非实质受管包装；不比较全 `papers` 或逐论文 level 作为重绘充分条件。旧侧使用已接受快照，不能用当前 ctx 的题名/元数据回填旧快照掩盖变化；新侧使用当前规范记录。仅未展示字段变化，或成员级别交换但最终可见内容/统计等价时，保持正文和校验轮次；可见内容实质变化按 §3.2 失效旧 validator，不借新绑定沿用旧 PASS。展示等价不替代旧报告/正文/包绑定合法性检查：只允许保留本来合法的记录，不能修复或洗白旧失效认证；正常 narrative refine 仍保留既有两轮生命周期。不新增锁、journal 或认证框架。
6. **字段与旧数据。** `_CANONICAL_PAPER_FIELDS`、build_direction_pack、_canonical_record、fresh/reused/resolved records 与 pack-only context 保存级别，同 key 一致合并，当前正式来源不得被旧记录覆盖。在 runner 内集中当前 paper 的构造/更新入口，供 `build_direction_pack` 的正式成员与 relevant 两分支、`_canonical_record` 及 `_current_paper_record` 共用；从旧包取记录也必须经过当前字段更新。当前 `stage2_analysis_level(paper)` 的 null 是有效覆盖值，必须清除旧 fulltext/abstract，不能用 truthy fallback 保留旧级别。仍保持 schema 2、成员资格及引用许可，不新增另一套 paper 模型。`paper_digest` 及 resolve/freshness 模型摘要不加入 level、render version 或展示投影。旧包缺 level 可显示未确认；旧包缺可比较业务基线走原 process，不从历史 Markdown/临时 facts 猜造基线。资料不足导致正常流程不能完成时真实报告停止，保留原数据，不强制所有坏旧包成功。只在受影响的下一次调用按上述分流更新，不批量迁移或为文档 SHA 重跑。


### 3.4 已完成的 PR93 固定入口兼容

r5 的入口对齐已在本轮基线中完成，历史[批准记录](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6248571193)及测试计划 §10 的整合/执行记录保留。Codex/OpenCode analyzer Step 2.6 与主 SKILL 的 `refresh_display` 分支均使用同目录 `scripts/contact_state`，原 `--professor-dir`、`--preflight-file`、payload 与返回消费保持不变。本轮七项不要求再次对齐、重装或重跑入口测试。

保留 PR93 薄入口向相邻 `contact_state.py` 原样转交参数的边界：runner 仍是唯一业务实现，非 Nix 直接 `.py` 调用能力与原解释器选择不变；不改 Nix/runtime/依赖、七入口清单，不新增 wrapper、fallback 或第二份业务正文。已整合 PR91 的位置解析、规范 papers、成员保护与 validator 生命周期继续保留。

## 4. 顺序、安全和替代方案

1. 实现者先核最新基线及 PR91 是否已落地，保留其位置解析/摘要/轮次/成员保护；只整合本计划涉及的交接。
2. 本轮由 runner 产品实现者按四个逻辑步骤修复，不要求拆文件或四个提交：
   - A（问题 1/2）：按 §3.3.6 合并当前 paper 构造/更新职责，贯通新增正式成员及复用记录的当前级别，含 null 覆盖。
   - B（问题 3，依赖 A）：按 §3.3.5 由 renderer 给出共享展示比较语义，普通 finalize 与 refresh 共用，分开处理展示变化和旧绑定合法性。
   - C（问题 4/5/7）：按 §3.3.2—5 收敛相关来源准入，修正 missing/no_path/显式空/坏记录与两处当前年份复核，保留旧无索引兼容和既有 lease。
   - D（问题 6）：按 §3.1 在固定 evidence 引用收集与展示出口完成兼容修复，保留可信已有链接及非引用文本。
3. 替代方案“开放所有固定区给模型改写”会改事实，排除；“只屏蔽校验或直接删除依据”掩盖缺陷，排除；选定方案在 runner 确定性展示、记录器保留失败，原 owner 处理问题。
4. 不新增并发锁或跨文件 journal，沿用已有教授写入 lease、原子 JSON 和 managed_write 保护；不自动覆盖人工文档、不重置用户选择、不改变成员归属。
5. 关键反例：abstract 有分析文件仍不能计 fulltext；OCR fulltext facts unavailable 仍可计全文输入级；旧包无级别应显式未知；固定+叙事混合阻挡不允许模型越权；同一未修复报告不能清轮数；正常 narrative 修订不应重开第一轮。
6. 现实替代是给各分支分别补字段、另写刷新专用 level 比较及正则替换；这样容易再次漏分支、误清轮次或破坏已有链接，因此选择复用上述职责各自的内部入口，而非新增公共 API/框架。代表性反例包括旧 known→当前 null、成员级别交换但聚合未变、仅相关论文级别改变、旧快照题名与当前题名不同、missing 文件出现、显式删除路径、无索引历史包、跨年等待 lease 和 evidence 已带合法链接；这些只用于解释方案边界，不自动转成新增测试矩阵。
7. 版本化依据：本轮 [contact_state.py](https://github.com/ScholarWorkflow/professor-contact/blob/e1e8e48a0f4bee8e5d22acd61813dccd53ac9632/.apm/skills/professor-contact/scripts/contact_state.py) 的 L4982—5019、L5588—5614、L5901—5924 对应 A；L5067—5079、L5376—5436、L5959—5960、L6314—6353 对应 B；L3590—3612、L3627—3723、L6194—6200、L6291—6297 对应 C；L4796—4887 对应 D。上述为实现现状证据，正式目标仍为 §1 U1/U5；内部 helper 名称、状态布局与比较表示不升级为新 contract。
8. r6 只请求复核上述四块及直接连带影响：P1 的当前源码依据，P2 的构造/renderer/来源 owner，P3 的兼容、轮次与失败保护，P4 的修改点与顺序。r4/r5 未受影响的固定区交源、成员归属、入口兼容结论可按影响分析引用历史批准，不由作者自行复制为 r6 PASS。下一负责人为计划审核者；批准并取得实施授权后交产品实现者。测试负责人按唯一测试计划判断已有证据复用及必要最小修订，本轮未修产品、未执行测试、不授予合并批准。

