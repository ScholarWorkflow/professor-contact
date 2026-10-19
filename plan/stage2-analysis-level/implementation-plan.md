# U5：实际分析级别贯通与诚实统计执行计划

- Requirement revision：2026-10-19 用户确认，先保持 main 行为完成 Stage 2 拆分，再把 U1、U5 分别设计为独立修复 PR；本轮仅提交执行计划。U5 继承已确认的实际全文／摘要／未确认统计目标，不扩展论文分析范围。
- Plan revision：u5-analysis-level-r2。r1 完整独立审核仅要求冻结来源资格与早期 lease 接线，本版合并两项修正；其余设计不扩展。
- Proposed review status: pending。本文是待审完整候选，不继承 PR #92 的执行、测试或合并结论。
- Target repository revision：ScholarWorkflow/professor-contact，main `d5a4f751fb80de4819d4a1de3ee829db52cea6fc`（2026-10-19 核实）。最终实施基线为保持行为的 Stage 2 拆分合并后的 main；尚无已确认拆分 PR。拆分完成是实施顺序前提，不是假设已有新模块。
- 唯一目标路径：`plan/stage2-analysis-level/implementation-plan.md`。本 PR 只写该计划及必要范围说明；不修改产品、测试资产或测试计划，不执行测试、不评论或关闭 #92、不合并。

## 1. 需求与边界

每篇论文的分析级别只能表示当前可确认、成功完成的分析实际使用了全文还是摘要；无法确认时显式为未确认。将同一真实值从分析登记贯通到 Stage 2 facts、规范论文记录、复用和 resolved 分支，最后用于现有方向成员的统计。已有 PDF、分析 Markdown 或有效 facts 均不能独自替代级别事实；OCR-only 成功全文分析仍是全文，即使 facts unavailable。

本修复应独立交付：无需先实施 U1、无需合并 #92。只改变级别及直接依赖它的统计、缓存分流和受管展示接受；不修固定证据引文展示、不改失败归属分类，不改全文分析／相关集／gap 范围、成员资格、引用许可、归属判断、时效模型或 Stage 3/4。

统计沿用现有 `direction_papers(pack, direction)` 对各方向 `supporting_item_keys` 的成员投影。一个论文在两个方向作为成员时仍按原两次成员贡献统计；不跨方向再去重，不把 `relevant_keys` 或整个 `papers` map 当成统计集。三类互斥且合计等于既有统计成员数。

## 2. 决策依据：现实与要求分开

以下代码事实全部指向上述 main；行号仅便于定位，冻结的是符号职责。

1. 两种 analyzer 的 Step 5.6/5.7 已按实际 route 登记 `_index.json.papers[key].level`：OCR/PDF 为 fulltext、normalized abstract JSON 为 abstract；成功分析后确认文件落盘再写入。Step 6.1 facts 样例未带 level。决策：沿用这个结构化权威，补传 `analysis_level`，不从 Markdown 反解析。
2. analyzer Step 5.6.7 明确 OCR-only、摘要、legacy、无 PDF handoff 可能 facts unavailable；facts 由 runner 校验且不得为补 facts 重跑全文。决策：分析成功资格和 facts 资格分开，绝不拿 `facts_state` 反推级别。
3. `build_direction_pack`（4404 起）在成员和 reference 两条路径都未保存级别；`cmd_stage2_finalize` 内 `_canonical_record`（5069 起）、`_current_paper_record`（5381 起）与 fresh/resolved/old 优先关系可能直接沿用旧记录。决策：所有当前记录合流后执行一次同规则的级别赋值，null 也覆盖，不能只修 fresh 分支。
4. `render_analysis_md`（4581 起）以 analysis_file 或 pdf_available 算全文，其余一律摘要。决策：renderer 仅按规范级别三分类，不再猜测。
5. `cmd_stage2_preflight`、`stage2_preflight_metadata`、`_artifact_guards_for_keys` 目前有业务输入、已存在载体 guard 和 accepted pack 检查，但没有独立 level 来源投影；未记录缺失候选，故新文件出现不能由旧 present-only guards 完整判断。决策：在 reuse_all 前增一个有限的当前来源/级别投影；只有业务部分完全可比较且不变，才允许零模型级别刷新。
6. `stage2_chatgpt_handoff.py` 已有内部 `acquire_local_lease`（默认 `verify_plan=False`）和 `release_local_lease`，共用教授 lock/lease；只有普通 CLI acquire 强制 exact handoff plan。本次确定性刷新复用内部 API，以自己的当前 preflight/pack/source 检查作为业务绑定，不改 handoff CLI。
7. `cmd_stage2_finalize`（5424–5521）以 render_state 决定渲染，且旧 validator 检查在可能写正文之后；`Stage2PackRefineContext`（1744 起）已有只用持久包的可信渲染上下文。决策：复用现有持久包和受管写入，先隔离并检查旧快照，再接受当前正文；不另造 facts、不恢复已失效认证。

源码入口：[runner](https://github.com/ScholarWorkflow/professor-contact/blob/d5a4f751fb80de4819d4a1de3ee829db52cea6fc/.apm/skills/professor-contact/scripts/contact_state.py)、[Codex analyzer](https://github.com/ScholarWorkflow/professor-contact/blob/d5a4f751fb80de4819d4a1de3ee829db52cea6fc/packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md)、[OpenCode analyzer](https://github.com/ScholarWorkflow/professor-contact/blob/d5a4f751fb80de4819d4a1de3ee829db52cea6fc/packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md)。

lease 接入事实：[现有 handoff/lease owner](https://github.com/ScholarWorkflow/professor-contact/blob/d5a4f751fb80de4819d4a1de3ee829db52cea6fc/.apm/skills/professor-contact/scripts/stage2_chatgpt_handoff.py)，`acquire_local_lease`、`release_local_lease`、`_lease_cli`。

历史教训来源：[92 r11](https://github.com/ScholarWorkflow/professor-contact/blob/10324b8f10ff84080e9f7132bef807926de23279/plan/stage2-evidence-level/implementation-plan.md)、[92 t47](https://github.com/ScholarWorkflow/professor-contact/blob/10324b8f10ff84080e9f7132bef807926de23279/plan/stage2-evidence-level/test-plan.md)。只吸收已暴露的因果问题，不移植其补丁链、私有版本 2→3 恢复或混合 U1 的整体刷新机制：字段遗漏会使分支不一致；null 被 truthy fallback 吞掉；先写后验会丢旧认证依据；新候选回填旧侧会制造假等价；body 等价不等于业务依据相同，机器头也不是 body；测试输入未满足所声称的复用前提不能证明产品结论。旧测试记录不作为本新实现通过证明，本计划不规定新测试配方。

## 3. 选择与 owner

选择“现有权威级别 + 一个规范赋值规则 + 有限来源投影 + 现有写入点的最小更新分支”。analyzer 负责分析结果成功登记；runner 负责资格检查、规范包、分流、统计和接受；renderer 只消费值。保留公开输入包 schema 2，增加可选 `analysis_level: fulltext | abstract | null`；缺字段按 null 兼容。来源投影和级别格式修订标识仅是 `cache.preflight` 私有缓存，不进入公开 schema、`paper_digest`、业务模型输入指纹、resolved proof 或时效 key。

不选仅在 renderer 读文件猜测：既无法区分成功分析与残留文件，也绕过缓存和持久规范包。不选每次级别变化都强制模型重跑：级别本身不改变业务依据。不选从 #92 整体 cherry-pick：混入 U1、旧展示版本恢复和不需要的框架。有限的级别更新需要 analyzer 可调用的确定性 runner 分支，可增加一个专用于此的 `stage2-refresh-level` 命令；它不成为任意字段更新或通用展示刷新 API。

## 4. 核心设计

### 4.1 当前级别及成功资格

只在当前教授、当前 item_key、当前被选分析来源上取值。main 没有统一 `analysis_status` 或 `stale` 字段，本修复不假设存在，也不新增一套状态认证。资格谓词具体为：当前教授 index 可解析、`papers[key]` 是对象，`file` 是可定位且存在的分析文件；正常路径所选 `facts.papers[key].analysis_file` 与它规范路径一致；level 是合法枚举或 null。已有 index 是成功-only 登记，故现存合法记录可作为历史成功分析依据，不另要求新版 success 标记。早期路径的当前选中分析路径只取 index.file，与接受基线的路径比较；不以旧 pack.analysis_file 回填当前缺失/显式空。

正常路径：本轮成功 local route 或成功 external import 已完成后，使用其正式写入的 index；复用按现有 analyzer Step 5.3 的 index entry + 文件存在规则。abstract 且当前已取得 PDF 时仍由原正常流程决定是否实际升级，成功全文分析之前不能把 abstract 改作 fulltext。明确执行失败/未完成的本轮 job 不登记成功，不让它产生新的已知级别；若尚有原先成功且仍符合既有复用规则的分析，保留那份真实历史级别，不能把 future-work 或 facts failed 当作全文分析失败。本轮被正常流程判需替换且失败、旧来源已失效时输出 null；这里“已失效”必须是下一轮仍可按同一谓词观察的文件缺失、路径不符，或正常流程已清除/更新其正式登记，不能只靠本轮瞬时失败说明。仅全文升级失败而原摘要记录和文件仍有效时，保留真实 abstract。不得本轮以瞬时状态置 null、下一轮又用残留 file+level 复活已失效级别；不新增状态认证。早期无法确认资格时交 process，不能先打已知标签。文件缺失、分析路径不符、没有成功-only 登记均不能确认该当前分析的级别。
合法已知 level 为 fulltext/abstract；缺失或明确 null 为未确认。非法枚举/类型在正常 facts 接受入口沿用输入错误处理，预检发现时转 process 而非写入已知值。缺失来源与不可读/坏记录须区分：前者可形成明确未知状态，后者不能证明业务未变。不存在 index 成功记录的旧分析，即使文件和 PDF 都在，也只显示未确认；不为凑已知值增加一次分析。

两种 analyzer 在组装 facts 时传同一资格规则的 `analysis_level`，runner 用当前 index/file 与本轮事实记录核对；本轮失败而已失效来源以当前 facts 的 null 清除，不能用旧 index 已知值救回。除此以外已知值与当前登记冲突时按输入错误处理，不静默采用任一已知值。当前未确认必须写 null。facts 资格仍走原校验；level 不赋予 facts/gap/归属的任何额外资格。level 的 route 映射、成功-only index 写入等已有行为保持，新增部分只负责读取和贯通。

### 4.2 一个赋值规则覆盖全部 pack 构造

在现有规范论文构造职责内集中级别规范化与当前覆盖，供 `build_direction_pack` 的成员/reference 路径及 finalize 的 fresh/reused/resolved/old fallback 合流使用。`_CANONICAL_PAPER_FIELDS` 和规范化保留字段，旧包缺字段转 null；同 key 采用当前已核实来源，不能让旧来源覆盖。

先保存旧 accepted pack 的独立深快照及其原字段，之后才组装 candidate。当前 canonical record 无论主体来自 fresh、old 或 resolved，都在最终加入 map 前明确赋当前 level；不使用 `new_level or old_level`，不以“字段已有”跳过 null。已接受旧包只能补其原有其他允许字段，不能充当当前级别来源。某 key 当前资格无法确认即 null，不从新候选反填旧包用于比较。

renderer 遍历原成员投影：fulltext/abstract 分别累加，缺失/null 为未确认；输出“全文级 X 篇 · 摘要级 Y 篇 · 未确认 Z 篇（共 N 篇）”。引用许可、论文身份和成员顺序全部保持。

### 4.3 只在 reuse_all 前增加必要的来源判断

建立一个 runner 内部读取职责，被正常成功接受、preflight 和级别刷新写前复核共用。范围为现有 selected candidate union 及已被该包合法消费的来源；不扫描全教授库、无关方向或目录。投影分为业务来源部分和级别值部分：

- 业务部分沿用现有业务输入/guard，记录当前 index key/对象形状、`file` 路径及上述资格。analysis 来自 index.file；future-work 声明来自 index.future_work_sidecar，facts 声明来自 index.facts_sidecar；固定候选由当前有效 analysis 路径派生。正常成功接受时同当前事实输入的 analysis_file/sidecar_file/facts_file 核对，保存实际消费的声明与观测状态，不能把 preflight 看到候选当成已消费。
- PDF 不在 index 中发明路径字段。正常接受时来源是 analyzer Step 6.1 的 facts.pdf_file，已有 `_artifact_guards_for_keys` 已保存该路径与 stat；本次随有限基线记录其明确路径或明确无源。早期只沿用现有离线复用契约：当前 target、Stage 1 fingerprint、candidate catalog 视图与既有业务输入均相同，且此前实际接受的 PDF 路径 guard 完整可比较时，检查该接受路径的当前 stat；这不是宣称已重新读取 Zotero 当前附件。已有本地正式输入若声明新路径/删除或对应 fingerprint 变化，优先 process；无完整历史接受声明、仅有旧 pack 的 has_pdf 布尔或散落文件时不能定位 PDF，不补造来源而走 process。原无 PDF 的接受状态只在相同本地输入且无新正式声明时维持无源，不搜索孤立 PDF。因而不扩大 main 本来就允许的离线复用保证，也不把未知当前来源写成确认已知。
- 对既有正常流程必须探测的固定候选（当前 analysis 对应 `.facts.json`、`.future_work.json`）保留 present/missing 状态和规范路径，missing→present 也是来源变化。observed 不等于被正式接受，preflight 不运行 facts 认证、迁移或补齐。
- 区分无记录、字段未声明、显式空、路径、坏记录。当前明确删除/清空不能用旧 pack 路径回填成当前声明；但 analysis 路径仍有效时，facts_sidecar=null 不能取消现有固定 `.facts.json` 探测。不可定位的孤立 PDF 不猜位置、不扫描；无法确定当前候选集合不能判等。
- 只保留影响当前来源的字段，generated_at、KB id 等管理信息不加入业务变化依据。level 单列，不用整个 index 文件 mtime/hash 把纯级别修改变成业务变更；既有业务载体沿用 stat 和已获得摘要，不增加 PDF 全文读取或新认证系统。

分流优先级固定：业务来源/输入/资格变化或不可比较 → process；业务完全可比较且相等、仅 level 或本修复私有统计格式标识待更新 → refresh_level；两部分均相等且既有 reuse 条件成立 → reuse_all。原 validator 门槛保留；它不再通过或待校验时不伪造 reuse_all，也不把它当来源变化。

旧 main 包没有完整新投影时，明确 process 一次建立真实接受基线，不按当前候选补造旧基线。不为此强制所有模型重跑：正常分析、方向、归属、时效仍按各自原有有效性复用。首次普通 finalize 必须实际接受本版统计才能记私有格式标识；不得在 metadata 构造时提前写成功标识。此迁移只在下一次受影响调用懒执行，不批量迁移，不接管未合并 #92 的私有版本。

### 4.4 级别更新与普通 finalize 的最小接受顺序

refresh_level 只用已接受持久包、当前来源投影及 `Stage2PackRefineContext`；无需临时 facts、Zotero、分析／归属／时效／叙事模型任务，不重签 resolved proof。业务变化一律退出交原 process。analyzer Step 2.6 在 preflight 后消费此第三分支；显式 chatgpt_result 或 kb_import=true 仍优先走原 process，不能被刷新吞掉。刷新由专用 runner 自行调用现有 lease owner 的内部 `acquire_local_lease(professor_dir, token, verify_plan=False)`，token 为本调用新生成且不借用他人；不调用需要 handoff ID 的 acquire CLI，不伪造/复用 `_latest`，不构建空 bundle。这个内部 API 已经使用相同教授 lock 检查 busy 并写同一 lease，本次只是新使用者，不新增锁、lease 格式或证明文件。成功取得后按下述自己的 preflight/pack/source 绑定重读比较，所有退出均 finally 调 `release_local_lease`；busy 保持既有 stage2_writer_busy，零业务写入返回，不循环覆盖；比较漂移释放后返回 needs_refresh，调用方重新预检，不拿旧 payload 继续。释放失败如实报告，不谎报已解除 lease。普通 process 的 build→import→exact acquire→finally release 顺序和 CLI verify_plan=True 完全不变。它与普通 finalize 复用现有 renderer、managed write、包/validator 摘要逻辑，仅将下面必要的接受顺序收敛在原写入 owner，不另建可插拔框架或第二份 renderer。

1. 在任何 candidate 组装、ctx.pack 覆盖和文件写入之前，保存原包深快照、受管文件 body/机器头、原实际 body 摘要、原 render binding 和 validator 记录。以原包核验旧绑定、归属与人工保护。无旧包为首建；读不到旧状态不得借新题名/候选记录补成可比较旧侧。
2. 普通 finalize 先完成原业务与 preflight 核验；刷新按上述内部 API 取得现有教授 writer lease 后重读同一 pack/target/Stage 1/当前业务年份/来源和级别，与预检绑定核对。输入漂移零写入返回原 needs_refresh；人工修改沿用原 needs_decision。不新增锁或 journal。
3. 由当前完整 candidate 实际渲染 body。不用 level 相等、统计相等、render_state 相等或任务数为零代替实际正文。缺可信渲染字段时刷新退回正常准备，普通处理沿用数据错误；不解析旧 Markdown 补字段。
4. 比较实际旧 body 和 candidate body，仅忽略 renderer 固定顶部生成标题的生成时间，保留同一行统计全文；其他字节原样比较。正文变化则受保护写入；等价则保留旧 body 原字节及真实 SHA，仅在既有机器头绑定当前候选所需时同步头。机器头同步不是新增认证项目，不重新引入已撤销的独立 header 认证要求。
5. validator 按三个独立事实处理：原绑定是否合法、body 是否实变、业务认证依据是否实变。body 或业务依据变化则旧认证失效，保留原报告；body 等价且业务未变才允许保留原本合法的 round/phase/pending 并同步必要包绑定。原绑定无效且无真实业务变化按既有证据错误处理，不用重绑救回 PASS。正常 narrative refine 保持原第一轮→第二轮生命周期，本修复不提供清轮次入口。
6. 文件接受完成后才在 candidate 登记本版私有统计标识、实际 render SHA、新 level 投影及必要的既有完整性摘要，沿用 atomic_json 等现有持久路径。刷新只更新 level、统计接受缓存及必要绑定；不改成员、模型结果、业务指纹、assignment、源接受资格或原报告。普通成功处理才可建立新业务来源基线。

已可预判的错误先于写入；若 Markdown/机器头写入后持久包 I/O 失败，明确未完成，不冒充跨文件原子回滚，不补打成功标识。下次仍由既有摘要、绑定及来源守卫拒绝直接 reuse。刷新后若统计确变而旧校验失效，按既有校验入口处理，刷新本身不自动启动模型校验。

## 5. 关键不变量与静态反例

- 有分析文件/PDF但无成功级别登记 → 未确认；OCR-only 成功全文且 facts unavailable → 全文。二者直接否定路径/facts 推断。
- fulltext→null 经 fresh、复用或 resolved 来源 → 当前 canonical 统一 null；旧 level 不得复活。
- level 变且来源未变 → 仅确定性统计更新；新增分析/facts、换址、删除、成功资格变化 → process，不借 level-only 绕过正常消费。
- 预检后新 facts 出现或当前来源删除 → 写前拒绝旧刷新；显式空不借旧路径恢复，固定候选仍按现有探测规则检查。
- 两篇互换 level、聚合统计相同 → 如实际 body 等价且业务未变，保留合法认证/轮次；新业务输入但渲染碰巧相同 → 保 body，旧业务认证仍失效，头与当前包一致。
- 旧不可读 body／绑定无效／人工改动 → 不拿 candidate 回填旧侧，不自动覆盖或宣告等价。
- 拆分/合并方向仍只统计最终 supporting 成员；引用论文不混入统计，跨方向共享论文不额外去重。

以上是设计安全条件及代表性静态检查，不是新增必测清单、用例编号、断言、执行命令或证据设施。

## 6. 实施落点、顺序与独立性

1. Stage 2 保持行为的拆分完成后，实施者对上述 main 符号做机械映射，记录实际模块路径和基线。若仅移文件/导入则沿用本设计；若来源契约或生命周期变了，只复核受影响决定，不借机重开整个需求。不得猜造拆分模块名。
2. analyzer 两个安装投影及主 SKILL 的 facts 说明补 level 契约；runner 规范化和当前覆盖先落地，renderer 三类统计随后消费；公开 schema 仍 2。
3. 在现有 preflight/metadata 职责加入有限来源与级别投影，明确旧缓存一次 process；再接专用 refresh_level 分支及两种 analyzer 的调用（明确上述内部 lease API 与 finally 生命周期），更新现有 finalize 接受顺序。
4. 保持 U1 与 U5 独立：U1 所有固定证据转换和失败归属仍由其 own renderer/validation 修改承担。U5 不等待 U1 helper，不复制其字段映射。U1 与 U5 的私有接受标记各自表达本项完成，不互相替代；合并后沿用同一接受步骤一次渲染并按各自完成条件登记。两个 PR 可触及同一 renderer/finalize 文件，但只使用同一现有写入 owner、不可变旧快照、真实 body/业务变化和合法旧认证约定；后合并者仅适配已合并符号，不再追加第二套接受逻辑。
5. 本计划审定后才另行安排产品实现；测试负责人按用户授权与当前测试规则处理受影响行为和观察入口。本次不写测试计划、不跑测试；计划批准不代表实现或测试通过。

正式观察入口为 facts 中的级别、规范包 canonical papers、原统计标题、preflight 分流及原受管/校验结果。无需新增日志账本或认证 API。

## 7. 影响、风险与结束边界

- intended_change：真实级别端到端贯通，未知诚实显示，旧缓存不漏级别更新，纯级别变化不新增模型分析。
- preserved_behavior：现有 scope、成员和引用身份、resolved 接受、事实和 future-work 权威、模型复用、人工保护、writer lease、失败 surface 和校验轮次边界。
- approved_behavior_change：统计由错误二分类变为真实三分类；级别/统计更新在 reuse_all 前处理；授权为本次 U5 修复。内部字段和 helper 不是新增产品要求。
- prohibited_side_effect：以路径或 facts 猜级别、null 复活旧值、把未知变成功、把业务变化当展示刷新、为级别重跑模型、重签 proof、重绑无效 PASS、覆盖人工正文、批量迁移、把 U1 纳入本 PR。
- 风险及控制：缓存兼容通过一次正常 process；来源并发通过既有 lease 内复核；多文件失败保留未完成并拒绝 reuse；旧包信息不足不伪造恢复。无需新增全局事务或独立认证体系。
- Critical assumptions：无以未有行为为依据的方案假设；拆分最终路径仅为实施顺序前提。若拆分实际改变上述行为，先作语义影响分析。
- Unresolved impacts：无已知关键未决项；精确拆分后路径待机械映射，不影响 owner 或核心机制。

下一负责人：独立计划审核者，对完整候选一次审查 P1–P4；作者只按具体受影响决定修订。root 再按用户授权创建 U5 独立 plan-only PR。后续实现与测试须另行安排，不把 #92 历史关口当新实现批准。
