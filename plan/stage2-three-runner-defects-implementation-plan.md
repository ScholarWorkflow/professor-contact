# Stage 2 运行器三项缺陷修复——实施与测试计划

## 1. 任务、版本与当前状态

- **Requirement revision**：2026-10-16 用户确认《第二阶段运行器问题报告》的三项修复；同日要求进一步明确拆分源方向的正式成员、参考论文的持久保存与读取、每轮归属结果隔离。四项修改是实现这三项原始要求的必要条件，不扩大 Stage 3—5 产品行为。
- **Plan revision**：`stage2-three-runner-defects-r2-2026-10-16`；本文件是本拉取请求唯一有效的完整实施与测试计划。`Proposed review status: pending`。计划作者不自行宣称任何审核关口通过。
- **Target repository / 基线**：`ScholarWorkflow/professor-contact`；计划取证提交 `main@58a2ae7e110f2f75cbd17fe40dca814c2b2d0777`；创建本 PR 时的实际 `main@305bc08f8b186672108cffbba0293d249bc8b4b2`。实施时以最新有效基线工作并记录提交，按源码及正式约定的实际差异定向检查影响。
- **任务依据**：用户提供的《第二阶段运行器问题报告_2026-10-16.md》（本机运行副本的代码、历史回执和诊断）；本仓库上述基线的 [运行器](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py)、[Stage 2 正式技能约定](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/SKILL.md)、[文字校验代理](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/agents/professor-contact-style-validator.agent.md)。
- **项目规则**：[Project Consensus](https://app.notion.com/p/rekidunois/Project-Consensus-3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/rekidunois/Plan-Reviewer-Rule-3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/rekidunois/Test-Engineer-Rule-3d80101a85f380d8a8f5ce528141e253)、[Merge Reviewer Rule](https://app.notion.com/p/rekidunois/Merge-Reviewer-Rule-3ea0101a85f381c2b870e7fdf4b55b19)。
- **本轮主分支变化分析**：在本计划起点之后，`main` 合入 [PR #90](https://github.com/ScholarWorkflow/professor-contact/pull/90)（`305bc08f`），修改 Stage 2 摘要导出路由、其单元测试和 Codex/OpenCode analyzer 的工具调用说明；未修改本计划三项缺陷所在的 `contact_state.py`、style-validator 或直接测试。与本计划交叉的只有两份 analyzer 文件：后续实现同步第 2 阶段校验说明时，必须保留 #90 已合入的 `--zotero-read-skill-dir` 导出调用要求。该提交没有改变本计划对成员、校验位置、缺失结果的核心修复选择；分支后续同步主分支时按此检查冲突。
- **证据边界**：报告记录了先前运行中的结果和运行副本 SHA，但报告本身没有再次执行写状态的复现命令；本次已核对仓库基线源码具有对应分支。没有读取用户机器上的原始回执和本地开发副本，不能以本计划声称真实数据已经修复或回归测试已通过。修复和验收均使用仓库内合成隔离数据。

**`r2` 修订依据**：针对首次计划审核的四个实际问题（拆分校验使用参考集、参考论文资料不能在无临时事实时恢复、旧缓存重算后可能不重绘 Markdown、旧同名结果可冒充本轮输出）补齐实施位置与失败处理。审核状态仍为 `Proposed review status: pending`；实施与测试均未开始。四处源码证据分别见目标 `main@305bc08f` 的 `contact_state.py` 第 2655—2658、1719—1752、4999—5034、2550—2580 行，以及 Codex/OpenCode 两份 analyzer 当前使用的固定临时结果目录。

## 2. 冻结需求与当前原因

| 编号 | 必须达到的结果 | 代码原因及修改责任 |
| --- | --- | --- |
| R1：正式成员与分析参考分离 | 方向的 `supporting_item_keys` 按本方向原 `provisional_member_keys` 和**已接受**的 `papers_to_add/papers_to_remove` 决定；`relevant_keys` 仍可作为分析、未来工作和叙事引用范围，不能自行增加正式成员。报告中的边缘方向为原 6 篇加 `D6XQCHTP`，共 7 篇；`GTQBNPED` 只属于另一方向的获准新增。 | [`build_direction_pack` 第 4314—4361 行附近](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L4314-L4362) 将 `direction_relevant_keys` 全部放入 `supporting_item_keys`；[`cmd_stage2_finalize` 第 4809 行附近](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L4809-L4833) 又在这个底表上应用获准增删。修复责任属于 `contact_state.py` 的组包和成员物化路径。 |
| R2：原始校验报告可准确定位 | 一条阻塞问题必须对应受管正文**唯一的实际行**和正确的 `direction_id`。同一 `quote` 出现三处时，校验器按行分别输出条目，记录器逐条消费；“第57行及多处”不应被当作可唯一定位的记录。不能任意选第一处，也不能让调用方改写原始报告。 | [第 10768—10775 行](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L10768-L10775) 允许任意短位置字符串，[第 10845—10864 行](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L10845-L10864) 只能按纯数字定位，否则引用多行时报 `validation_quote_ambiguous`。修复责任属于第 2 阶段记录器与同仓库 style-validator 的 Stage 2 输出约定。 |
| R3：没有新结果不能伪造接受 | 本轮 `stage2-resolve-plan` **明确发出新任务**、且无可复用的已接受记录和已有待选提案时，缺指定 `resolve-<方向完整编号>.json` 要返回 `result_missing` 并停止写入本轮方向权威状态。错写为 `resolve-edge.json` 等短名不能变成 `acceptance=accepted / resolution_type=unchanged`。 | [第 2304 行附近](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L2300-L2311) 发完整任务文件名；[第 2535—2577 行](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L2535-L2577) 在缺文件时构造 `_unchanged_default()`，保存为 accepted；[第 2871—2934 行](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py#L2871-L2934) 可将此结果写入缓存。责任属于 `validate_resolve_results` 和 `cmd_stage2_resolve_finalize`。 |

上述目标由本次用户修复请求确认；报告中的实际代码行为是缺陷证据，不把错误默认状态升级为正式产品要求。

## 3. 冻结实施方案

### 3.1 R1：建立唯一正式成员集合，持久保存参考范围

1. **正式成员的唯一来源**：`provisional_member_keys` 是原始正式成员；`relevant_keys` 只是可供分析、future-work、gap 与 `{{P:key}}` 叙事引用的论文范围。`build_direction_pack` 按本轮 facts 的 `provisional_member_keys` 去重建立初始 `supporting_item_keys`，禁止从 `relevant_keys/member_keys/named_keys` 兜底补成员。`cmd_stage2_finalize` 仅应用当前有效、已 `accepted` 的 `papers_to_add/papers_to_remove`；用户显式 `--keep-provisional` 时维持原成员。没有合法的初始来源则写盘前报错；未经用户接受的变更不得物化。
2. **拆分的前后两处非空检查**：`validate_resolve_results` 在 `split_from` 下按 `source_members=set(provisional_member_keys)`、`moved=set(papers_to_add)` 验证 `source_members - moved` 非空，替换原本错误的 `direction_relevant_keys - papers_to_add` 检查。`papers_to_add` 中属于教授级候选并集、但非源正式成员的全文救回论文，仍可合法进入新子方向，不算从源方向移出的成员。`cmd_stage2_finalize` 完成拆分物化后再次核对源方向最终 `supporting_item_keys` 非空，失败时 `invalid_resolved_directions` 且零权威写入。合并时源方向本来要消失，不适用该非空条件；原有新增/移除全文事实验证保持不变。
3. **参考资料继续写入同一输入包**：保持 `套磁候选输入.json` 的 schema 2、教授级唯一 `papers[item_key]`，不新增数据库或重复论文实体。每个 `directions[]` 持久保存 `relevant_keys`（引用范围）和 `supporting_item_keys`（正式成员）。`build_direction_pack` 输出两者；`cmd_stage2_finalize` 构造规范 `papers_map` 时按每个最终方向 `supporting_item_keys ∪ relevant_keys` 收集现有规范论文记录（`title/year/authorship/analysis_file/pdf_available/facts_state/facts_error/paper_facts` 等既有字段），以本轮可信 `ctx.papers`/有效事实为优先；旧缓存只可补足经核对的值。合法 `P` 引用若无许可或可信标题必须在写入前报错，不能退化显示 `item_key`，更不能将引用论文加进正式成员。原有 `L` 引用仍由 `narrative_later_papers` 保持，不把它混入本方向正式成员。
4. **脱离临时 facts 的读取**：`Stage2PackRefineContext.__init__` 从 `pack["papers"]` 恢复可信标题/年份/署名/分析路径，从本方向保存的 `relevant_keys` 恢复允许的 `P` 引用范围；`supporting_item_keys` 继续单独供正式成员。使 `stage2_validation_material`、`stage2_validation_report`、`render_analysis_md`、`stage2-refine-plan/finalize` 从输入包得到同一资料和许可。旧包确无 `relevant_keys` 时，仅在纯读取兼容路径以旧 `supporting_item_keys` 为最小许可；涉及错误成员的重建必须从当前 facts 的参考集与原始成员重新建立，不以旧缓存倒推许可。`narrative_later_papers` 的现有读取与标题校验不改。
5. **原有归属与下游权限**：继续按 `refined → split_from → merged_into` 三段应用获批准决定，完整迁移拆分、合并的正式成员和 gap，保留全文救回、合法共享论文与已物化拆分子方向重跑不清空；每个最终方向 `input_fingerprint.final_supporting_keys` 都由最后的权威成员计算。`direction_papers` 和 Stage 3 `_direction_slices` 仍只用本方向 `supporting_item_keys` 与既有 gap 范围授权论文，`papers_map` 新存的参考论文不能因此进入 Stage 3—5 成员或扩大其引用权限。
6. **旧缓存中叙事复用与成员复用分开**：提升 `STAGE2_RESOLUTION_SEMANTICS_VERSION`，旧包不得在 `stage2-preflight` 命中 `reuse_all`。`Stage2Context._prepare_directions` 可能因叙事指纹一致仍设置内部 `reuse`：此时只允许复用合法 narrative/freshness，不得继续沿用旧 `supporting_item_keys`。`cmd_stage2_finalize` 用本轮事实中的原始正式成员重建底表，再物化匹配当前 resolve 指纹且已接受的决定；原始成员或获准依据缺失则写入前拒绝，不能把旧污染数据解释为许可。有效 accepted 仍可按原指纹复用，避免重复询问用户。
7. **成员变化强制重新渲染**：旧实现仅以 `needed_keys || !ctx.pack || display_changed` 判断是否重绘。新增比较旧/新最终方向集合、正式成员与影响分析文档的已验证参考标题；只要展示所依赖的内容发生变化，即使 `needed_keys=[]`、名称未变，也重新 `render_analysis_md`，更新受管 `render_sha256` 并走既有 `managed_conflict/managed_write` 人工修改保护。真正 `reuse_all`、展示内容不变仍不改时间戳。不得生成与 Markdown 不一致的新版权威输入包。
8. **历史数据保护**：只针对本教授受影响的生成物写入，不自动删除或重置历史缓存。发现来源不能证明的旧异常 accepted 时，先备份并按主 `SKILL.md` 原有重置流程交用户决定，不自动认可。原有前置证明、事务顺序、受管 Markdown 保护均须保留。

### 3.2 R2：收敛位置约定与记录器的真实识别能力

1. 只对 `artifact=analysis` 的 Stage 2 校验明确支持：正整数行号、纯 ASCII 十进制行号字符串、精确写法“第N行”；兼容原有短文本 `location` **仅在对应 `quote` 在当前受管正文恰好命中一行时**使用。所有行号均指包含 frontmatter 的当前受管文件实际物理行，按现有 `line_offset` 计算。
2. style-validator 的 Stage 2 指令要求：当同一引文命中多行时，每一处分别生成一条 `issues[]`，`location` 填该处具体行号、`quote` 填所在行的原文逐字片段；不得再输出“第57行及多处”“多处”作为多个位置的统称。该指令仅作用 Stage 2，Stage 3 的位置接口及其结果消费保持原状。
3. `stage2_validation_report` 在 schema 检查与归属计算时使用同一位置规则；“第N行及多处”等含糊行号提示须用明确错误告诉调用方“按实际行号逐条重做校验”，不能自动把一条 issue 展开到任意多处。引用找不到、指向错误行、仍有多处匹配、同一行引用重复，以及不能归入唯一方向，继续安全拒绝。对有效的多条 issue，按实际命中行逐条映射方向和是否可修订。
4. `stage2-record-validation` 仍只消费原生 `result/files/notes` 完整原始报告；保持第一轮记录 → 修订 → 第二轮记录的既有两轮限制、文件与正文摘要绑定、`validator` 独立状态、不可修订区域拒绝和零错误修订。原始报告不能由协调代理手工“修好”再提交。若已保存报告本身位置含糊，只能由校验器在同一受管文本上重新给出合规报告。
5. 同步 `.apm/agents/professor-contact-style-validator.agent.md`、两种安装投影的 `professor-contact-analyzer.agent.md` 中 Stage 2 校验交接说明、主 `SKILL.md` 的位置约定；不改变文字校验标准、阻塞严重度、Stage 3 校验或代理委派方式。

### 3.3 R3：每轮独立结果目录和本轮标识

1. **正式调用者建立独立目录**：同步两种安装投影 `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md` 与 `packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md`。在各教授已有的 `mktemp -d` 事务目录内，每次启动新 `stage2-resolve-plan` 前执行 `mktemp -d "<本教授事务目录>/resolve-run.XXXXXXXX"`，得到本轮独占结果目录；记录真实绝对路径，不再使用固定 `/tmp/<教授名>_stage2_resolve_results`。本轮所有模型结果只能写入此目录，`stage2-resolve-finalize` 也只读取此目录；换轮必须换目录。缺文件后在**同一轮**补齐可直接再次 finalize；若重新发 plan，生成新目录、新标识和新结果，不迁移旧模型输出。
2. **plan/finalize 的同一传递身份**：`stage2-resolve-plan` 新增必填 `--results-dir`；在发出 jobs 前检查目录是既存绝对目录、所有预期结果文件都尚不存在、`jobs[].result_file` 在本轮互不碰撞，错误报 `invalid_params`。建立 `resolve_run_id = sha256_obj({"professor_dir": 规范绝对教授目录, "preflight_id": facts 的本轮前置证明, "results_dir": 规范绝对结果目录})`；plan 在新 jobs 的 `result_schema` 中增加必填 `resolve_run_id`，把其值交给模型原样回填，并把本轮标识返回给调用方。继续使用 `resolve-<filename_component(完整 direction_id)>.json` 文件名；plan/finalize 共用同一文件名生成规则，绝不猜短名。该标识只约束临时 job 输出，禁止纳入 `_build_resolve_model_input`、`_current_resolve_fingerprint` 或已接受缓存，避免无变化时重发工作。
3. **校验新文件来自当前轮**：`stage2-resolve-finalize --facts <facts> --results <本轮目录>` 用同一公式计算预期 `resolve_run_id`，并定位每个必需结果文件。缺文件 → `result_missing` 并附完整预期路径；文件存在则沿既有 UTF-8 JSON、`schema/kind/direction_id/provisional_direction_id` 校验，新增要求 `data.resolve_run_id == expected_run_id`，不符 → `invalid_result_json`。复制上一轮同名文件也必须拒绝；旧结果目录、短名文件和其他教授的文件都不能作为替代。无文件时禁止构造 `_unchanged_default()` 并保存为接受记录。
4. **先处理用户显式沿用**：现在 `cmd_stage2_resolve_finalize` 在 `validate_resolve_results` 之后才处理 `--keep-provisional`；一旦缺文件改为拒绝，会误挡合法用户决定。将明确点名的 `keep_provisional` 方向先在当前指纹上构造 `decision=user_kept_provisional`、`acceptance=accepted`、`resolution_type=unchanged` 的覆盖项，再进行其余方向的文件校验及整批结构检查。被覆盖方向不要求本轮模型文件，但其他方向不能借此免检。保留 `stage2-resolve-accept` 的单独采纳流程，禁止缺文件自动视作用户选择。
5. **其余方向保持三种互斥行为**：① 已有指纹匹配且已接受、plan 未发新任务 → 保留 accepted，忽略残留文件；② 指纹匹配但仍为 `proposed`，新目录没有结果 → 原样保留提案并返回 `needs_user_choice`；③ 本轮需要新文件且不属于前两类 → 严格执行第 3 点，缺失报 `result_missing`，不生成默认 accepted。存在有效新结果时保留既有 `unchanged` 自动接受、`refined/split/merge` 待用户采纳的规则。
6. **整批无副作用失败**：任一必需文件缺失、错误轮次或结构错误，停止写入 `_resolved_directions.json`、正式输入包和新 accepted 缓存；不能部分接受已齐全方向。所有结果验证完毕后才允许写入现有权威状态。历史有效 accepted/pending 缓存不清除；不新建持久运行清单。
7. **接口同步与兼容**：同步 `contact_state.py` 解析器、两个 analyzer 正式调用示例、主 `SKILL.md` 和相应回归测试，确保 plan 使用 `--results-dir`，模型写入 `jobs[].result_file` 并回显 `resolve_run_id`，finalize 用相同目录。省略 `--results-dir` 的旧 plan 调用明确报缺参数，不能回退到固定目录；既有侧车结构、指纹缓存复用、Stage 3—5 产品规则保持不变。

**正式调用示例**（`facts_file` 和教授事务目录已经由原 Stage 2 准备步骤提供）：

```bash
run_dir=$(mktemp -d "<本教授事务目录>/resolve-run.XXXXXXXX")
python3 <professor-contact-skill-dir>/scripts/contact_state.py stage2-resolve-plan \
  --facts "$facts_file" --results-dir "$run_dir"
# 按 jobs[].result_file 写本轮 JSON，并原样回填 jobs[].result_schema.resolve_run_id
python3 <professor-contact-skill-dir>/scripts/contact_state.py stage2-resolve-finalize \
  --facts "$facts_file" --results "$run_dir"
```

## 4. 方案取舍与限制

- **选择**：在现有 `contact_state.py` 的事实/组包、校验和状态写入入口修复根因；对外保留现有 JSON 路径、`direction_id` 身份、受管文件与阶段职责。只在 Stage 2 的实际契约边界同步模型说明。
- **拒绝的替代方式**：由协调代理删除多出的 `supporting_item_keys`、手工改写原始校验 JSON、猜测 `resolve-*.json` 的短名，或在下游 Stage 3 过滤错误成员。这些办法不会修复生产入口，再次运行会复发。另一个方案是让相关论文和正式成员继续共用一个字段、仅修改显示数量；它会继续污染 Stage 3 指纹，因此不采用。
- **intended_change**：正式方向成员仅来自原始成员及被接受的决定，拆分源保留正式成员；合法参考论文存于现有输入包并可在无 facts 时恢复；旧归属变化触发受管文档重绘；重复引文逐条定位或拒绝；缺本轮新结果或旧轮次结果时在落盘前失败。
- **preserved_behavior**：教授身份与 `direction_id`、合法共享论文、经全文验证的跨方向新增、已确认的细化/拆分/合并、有效 accepted/pending 复用和显式沿用 provisional；论文/gap/freshness/叙事输入范围、受管 Markdown 人工保护、Stage 2 校验两轮限制、Stage 3—5 只消费已接受输入包；`papers` 中增加参考记录不能扩大下游正式成员与引用许可。
- **approved_behavior_change**：2026-10-16 用户已授权的三项错误修复及本轮明确要求的拆分非空、参考信息持久化、旧包重绘与结果隔离；`--results-dir` 和新 job 的 `resolve_run_id` 是此次修复必需的 Stage 2 调用接口变化，仅同步本仓库正式调用者。不改 Stage 1、Zotero、论文全文分析规则、Stage 3—5 产品逻辑和其他仓库。
- **prohibited_side_effect**：不得把“相关”当“正式归属”，不自动接受缺席的模型输出，不跳过人工采纳、不将旧报告改写为通过、不使用用户生产目录测试、不增加全仓运行/模型采样/跨仓安装作为本次默认必测项目。
- **故障边界**：本轮缺结果、旧 `resolve_run_id`、原始正式成员证据缺失、旧缓存来源不可证明、校验位置不唯一时，均须在写入本教授权威状态前拒绝；合法 pending、accepted 和用户显式沿用保留；同教授方向仍按现有整批写入边界执行，并发锁及无关缺陷不顺手重构。

## 5. 正式必测清单（测试方案初稿，待测试工程师第一、第二关审核）

每项仅覆盖本次修改的业务结果及直接改变的兼容行为，使用仓库现有 `unittest` 和合成临时教授目录。正式测试入口、准备与断言由本地测试工程师按本节补齐；无新增专用测试服务或通用判定器。

| 业务目标 | 输入或场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- |
| T1：正式成员与参考持久化 | 初始成员 6 篇、参考集多 `GTQBNPED`，仅已接受 `D6XQCHTP` 新增；另方向合法加入 `GTQBNPED`，该参考论文只用于 `{{P:key}}` 且无 gap/后续引用。清除临时 facts 后走 `--professor-dir` 修订读取入口。 | 前方向恰好 7 篇、无 `GTQBNPED`；另方向保留获批成员；`papers[item_key]` 保存参考论文唯一可信标题、`directions[].relevant_keys` 保存引用许可；无 facts 仍能渲染和修订 `P` 引用，Stage 3 成员范围未放宽，最终指纹使用 7 篇正式成员。 | 扩展 `test_stage2_resolved_direction_downstream_regressions.py`，检查最终输入包、受管 Markdown、pack-only 修订正式入口及既有 Stage 3 论文范围。 |
| T2：合法归属保持、拆分源非空 | 合法 `refined/split_from/merged_into`、共享论文、已接受拆分子方向无变化重跑和全文救回；另有源方向唯一正式成员被全部移走，但 `relevant_keys` 仍包含参考论文的拆分提案。 | 合法成员与 gap 迁移、共享身份和 accepted 复用正确；源正式成员将被移空的拆分被拒绝且不写新接受状态，参考论文不能作为剩余成员。 | 复用并定向扩展 `test_stage2_resolved_direction_downstream_regressions.py` 和 `test_stage2_resolved_direction_acceptance_boundary.py` 正式入口断言。 |
| T3：每轮结果隔离、缺失和合法复用 | 同方向连续两轮：第一轮有正确 JSON，第二轮新目录缺文件或只有短名；复制上一轮同名文件到第二轮；最后生成当前 `resolve_run_id` 的正确文件。覆盖同批其他方向已接受、待选提案和显式 `--keep-provisional`。 | 第二轮缺文件报 `result_missing`，旧同名文件的轮次不符报 `invalid_result_json`，失败时整批权威状态不变；补齐正确文件才成功；已有 accepted 直接复用、proposed 仍待选，显式沿用无模型文件仍合法。 | 扩展 `test_stage2_resolved_direction_regressions.py` 和既有接受边界测试，仅核对正式 CLI 回执及权威文件前后差异。 |
| T4：重复引文的定位与拒绝 | 同一阻塞 `quote` 出现在受管正文三个物理行，原始 style-validator 报告对三行分别给出准确行号；另有仅填“第57行及多处”的原始报告副本。 | 三条准确记录逐一归到其真实方向并进入正常修订状态；含糊格式返回可操作的定位错误，不记入校验状态，也不修改正文/输入包；不得选任意单处。 | 扩展 `test_stage2_style_validation_handoff.py` 的 `stage2-record-validation` 正式入口与前后文件检查。 |
| T5：旧包修复后同步重绘 | 旧语义版本输入包被 `relevant_keys` 扩大正式成员；本轮原始成员和有效 accepted 决策可用、旧受管 Markdown 存在，`needed_keys=[]` 且名称未变；对照合法新版本无变化包。 | 旧包预检不能 `reuse_all`；重算正式成员并更新分析 Markdown 与渲染摘要，不能留下新输入包/旧文档；原始成员来源无法证明则零写入拒绝；合法无变化包仍复用。 | 使用现有 `stage2-preflight`、`stage2-plan/finalize` 与受管 Markdown 的检查方式定向扩展预检测试。 |

**测试准备**：每轮 resolve job 在新建独立目录下准备结果，模拟旧轮次结果仅用于验证应拒绝。产品单元测试放在 `.apm/skills/professor-contact/tests/`，沿用仓库中 `BaseEnv`、`ResolvedPipelineMixin` 等合成夹具，在系统独立临时目录中创建教授、方向、论文事实、预检证明与结果目录。只用当前生产 CLI 正式入口，不伪造产物后绕过正式校验。不得连接真实 Zotero、浏览器、教授业务目录或用户缓存。无需引入独立测试仓库、运行模型或修改机器范围的配置。

**拟执行入口**：测试工程师完成第一、第二关后，从仓库根进入现有测试目录，运行相应 `python3 -m unittest -v` 指定模块：`test_stage2_resolved_direction_regressions`、`test_stage2_resolved_direction_downstream_regressions`、`test_stage2_resolved_direction_acceptance_boundary`、`test_stage2_style_validation_handoff`，以及承载 T5 的已有预检测试模块。所需 `uv run --no-project --python python3` 包装、临时输出目录、安装版本和直接可复制命令，由本地测试工程师在此唯一文件中确认后冻结，不以本计划初稿声称已执行。只保留正式业务结果所需字段、退出码和必要错误，不采集完整运行时轨迹。

**失败及复用**：异常业务输出就是业务失败，不以改输入或重试换取通过；环境/外部工具阻断标记无法判断。先排除隔离/权限错误，再仅重测受影响项；未受影响的历史有效通过记录由第三关决定复用。没有授权外部服务正式重试，本次预计无需外部调用。测试工程师不得扩展为整套 0—5 阶段联调或逐个代理行为认证。

## 6. 实施次序、交接与合并条件

1. **计划审核**：由独立审核者在当前基线及必要的目标版本上审 P1—P4，取得正式 `Plan conclusion: APPROVED`。若证据揭示另一个成员归属入口，先把新增关键事实及直接影响修订进本文件再复审；作者不得把此初稿标为批准。
2. **先修 R3 状态与结果入口**：在 `contact_state.py` 加入 `--results-dir`、`resolve_run_id` 和缺文件/错轮次拒绝；在 `validate_resolve_results` 中先处理显式 `--keep-provisional`，其余方向保持 accepted/pending 复用并整批先检查后写盘。同步两份 analyzer 的每轮独立 `mktemp -d` 结果目录与主 `SKILL.md` 调用契约。
3. **修 R1、引用持久化和旧包重绘**：`build_direction_pack` 从 `provisional_member_keys` 建成员并保存 `relevant_keys`；`cmd_stage2_finalize` 保存两类论文、校验拆分非空和最终指纹；`Stage2PackRefineContext`/`stage2_validation_material` 从规范 `papers` 及参考范围恢复标题许可；提升归属语义版本，阻断旧正式成员复用，确保成员变动时受管 Markdown 重绘。
4. **修 R2 并同步调用说明**：更新 Stage 2 原始报告读取与行号定位，调整同仓 style-validator 的 Stage 2 位置要求及 Codex/OpenCode analyzer 交接说明；不改变 Stage 3 校验。
5. **测试工程师关口与实现**：依据第 5 节确认第一关必测清单、补齐第二关可执行方案；在本拉取请求分支提交受影响测试与产品实现，按规定在隔离环境执行并记录第三关结果。只核对该次变更影响到的既有行为。
6. **合并审核**：按 Merge Reviewer Rule 对“正式需求 → 已批准计划 → 本分支实现 → 生产调用路径 → 第三关结果”审核；`READY + COMPLETE` 后再由用户另行决定是否合并。此请求在实现、验证、审核完成前保持 `Draft`。所有后续实施继续提交到**同一个拉取请求分支**；不拆成另一个 PR，也不把计划正文散落在评论中。

## 7. 修订状态与未完成事项

- 本 PR 当前 **仅包含计划文件**；`r2` 依据本轮用户请求更新唯一实施与测试计划，尚未修改运行器、代理技能说明、测试或任何教授业务状态。
- 本轮已将首次审核的四项问题合入 `r2` 候选；尚未取得独立复审批准、测试第一/第二/第三关或合并审核结论，未运行回归测试。当前 `Plan conclusion`、`Test Engineer Gate 3`、`Merge conclusion` 均为 **pending / NOT_READY**，不得宣称方案已被审核批准或产品已修复。
- 没有可供本会话调用的独立子代理复核工具；作者自查不替代独立计划审核。下一责任人为计划审核者，之后为产品实现者和本地测试工程师。
