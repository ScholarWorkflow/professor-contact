# Stage 2 运行器三项缺陷修复——实施与测试计划

## 1. 任务、版本与当前状态

- **Requirement revision**：2026-10-16 用户确认《第二阶段运行器问题报告》的三项修复；同日要求进一步明确拆分源方向的正式成员、参考论文的持久保存与读取、每轮归属结果隔离。四项修改是实现这三项原始要求的必要条件，不扩大 Stage 3—5 产品行为。
- **Plan revision**：`stage2-three-runner-defects-r3-2026-10-16`；本文件是本拉取请求唯一有效的完整实施与测试计划。执行方案 r3 已获 [正式复审批准](https://github.com/ScholarWorkflow/professor-contact/pull/91#issuecomment-6218616598)（固定提交 `352426a129c5d0b374704f68e637d0ad3cf1a4c2`）；本次只同步第 5 节测试计划 `stage2-three-runner-defects-test-r5-2026-10-17` 与交接状态，不改执行方案。测试第一关已有正式通过记录；第二关待本次修订复核、第三关未执行，作者不自行宣称通过。
- **Target repository / 基线**：`ScholarWorkflow/professor-contact`；计划取证提交 `main@58a2ae7e110f2f75cbd17fe40dca814c2b2d0777`；创建本 PR 时的实际 `main@305bc08f8b186672108cffbba0293d249bc8b4b2`。实施时以最新有效基线工作并记录提交，按源码及正式约定的实际差异定向检查影响。
- **任务依据**：用户提供的《第二阶段运行器问题报告_2026-10-16.md》（本机运行副本的代码、历史回执和诊断）；本仓库上述基线的 [运行器](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/scripts/contact_state.py)、[Stage 2 正式技能约定](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/skills/professor-contact/SKILL.md)、[文字校验代理](https://github.com/ScholarWorkflow/professor-contact/blob/58a2ae7e110f2f75cbd17fe40dca814c2b2d0777/.apm/agents/professor-contact-style-validator.agent.md)。
- **项目规则**：[Project Consensus](https://app.notion.com/p/rekidunois/Project-Consensus-3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/rekidunois/Plan-Reviewer-Rule-3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/rekidunois/Test-Engineer-Rule-3d80101a85f380d8a8f5ce528141e253)、[Merge Reviewer Rule](https://app.notion.com/p/rekidunois/Merge-Reviewer-Rule-3ea0101a85f381c2b870e7fdf4b55b19)。
- **本轮主分支变化分析**：在本计划起点之后，`main` 合入 [PR #90](https://github.com/ScholarWorkflow/professor-contact/pull/90)（`305bc08f`），修改 Stage 2 摘要导出路由、其单元测试和 Codex/OpenCode analyzer 的工具调用说明；未修改本计划三项缺陷所在的 `contact_state.py`、style-validator 或直接测试。与本计划交叉的只有两份 analyzer 文件：后续实现同步第 2 阶段校验说明时，必须保留 #90 已合入的 `--zotero-read-skill-dir` 导出调用要求。该提交没有改变本计划对成员、校验位置、缺失结果的核心修复选择；分支后续同步主分支时按此检查冲突。
- **证据边界**：报告记录了先前运行中的结果和运行副本 SHA，但报告本身没有再次执行写状态的复现命令；本次已核对仓库基线源码具有对应分支。没有读取用户机器上的原始回执和本地开发副本，不能以本计划声称真实数据已经修复或回归测试已通过。修复和验收均使用仓库内合成隔离数据。

**已有修订背景（`r2`）**：针对首次计划审核的四个实际问题（拆分校验使用参考集、参考论文资料不能在无临时事实时恢复、旧缓存重算后可能不重绘 Markdown、旧同名结果可冒充本轮输出）补齐实施位置与失败处理。审核状态仍为 `Proposed review status: pending`；实施与测试均未开始。四处源码证据分别见目标 `main@305bc08f` 的 `contact_state.py` 第 2655—2658、1719—1752、4999—5034、2550—2580 行，以及 Codex/OpenCode 两份 analyzer 当前使用的固定临时结果目录。


**`r3` 修订依据与授权边界**：用户同日要求“那你直接补充，另外，让计划足够完善，别忘了看 nix 共识”，承接补齐三处正常调用链的建议。本轮合并 [r2 审核的三项意见](https://github.com/ScholarWorkflow/professor-contact/pull/91#issuecomment-6217929666)：重绘后的校验生命周期、带 `--facts` 的修订兼容、拆分/合并参考范围。该记录对 `r2@e6096564` 的结论是 `NEEDS_MODIFICATION`（P1 PASS，P2—P4 待修改）；不把旧关口或作者自查移作 r3 批准，也不把计划中的历史授权描述当作独立用户证据。

**Nix 共识适用边界**：已对照 [Nix skill 交付规则](https://app.notion.com/p/rekidunois/Nix-skill-3fb0101a85f38185b17adb417590e50e)（2026-10-16 更新）。本次保持 APM、uv/PEP 723 原入口和单一业务来源，正式命令从实际安装的 skill 根目录取资源，保留 #90 导出接线；同步现有投影不另维护第二份业务实现。不新增 Nix 输出、安装器、配置迁移或跨文件 journal，不把此规则变成本 PR 的新增 Nix 交付/真实安装全业务验收。只检查变更直接影响的入口和场景，适用历史证据可复用；文档或 SHA 改动不触发无关重跑，不宣称未验证平台已就绪。

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
4. **脱离临时 facts 的读取**：`Stage2PackRefineContext.__init__` 从 `pack["papers"]` 恢复可信标题/年份/署名/分析路径，从本方向保存的 `relevant_keys` 恢复允许的 `P` 引用范围；`supporting_item_keys` 继续单独供正式成员。使 `stage2_validation_material`、`stage2_validation_report`、`render_analysis_md`、`stage2-refine-plan/finalize` 从输入包得到同一资料和许可。旧包确无 `relevant_keys` 时，仅在纯读取兼容路径以旧 `supporting_item_keys` 为最小许可；涉及错误成员的重建必须从当前 facts 的参考集与原始成员重新建立，不以旧缓存倒推许可。`narrative_later_papers` 的现有读取与标题校验不改。带 `--facts` 的入口同样必须可用，原事实校验与最终方向修订上下文按第 3.4.2 节分离。
5. **原有归属与下游权限**：继续按 `refined → split_from → merged_into` 三段应用获批准决定，完整迁移拆分、合并的正式成员和 gap，保留全文救回、合法共享论文与已物化拆分子方向重跑不清空；每个最终方向 `input_fingerprint.final_supporting_keys` 都由最后的权威成员计算；参考范围按第 3.4.3 节同步物化，不因成员迁移隐式授权。`direction_papers` 和 Stage 3 `_direction_slices` 仍只用本方向 `supporting_item_keys` 与既有 gap 范围授权论文，`papers_map` 新存的参考论文不能因此进入 Stage 3—5 成员或扩大其引用权限。
6. **旧缓存中叙事复用与成员复用分开**：提升 `STAGE2_RESOLUTION_SEMANTICS_VERSION`，旧包不得在 `stage2-preflight` 命中 `reuse_all`。`Stage2Context._prepare_directions` 可能因叙事指纹一致仍设置内部 `reuse`：此时只允许复用合法 narrative/freshness，不得继续沿用旧 `supporting_item_keys`。`cmd_stage2_finalize` 用本轮事实中的原始正式成员重建底表，再物化匹配当前 resolve 指纹且已接受的决定；原始成员或获准依据缺失则写入前拒绝，不能把旧污染数据解释为许可。有效 accepted 仍可按原指纹复用，避免重复询问用户。
7. **成员变化强制重新渲染**：旧实现仅以 `needed_keys || !ctx.pack || display_changed` 判断是否重绘。新增比较旧/新最终方向集合、正式成员与影响分析文档的已验证参考标题；只要展示所依赖的内容发生变化，即使 `needed_keys=[]`、名称未变，也重新 `render_analysis_md`，更新受管 `render_sha256` 并走既有 `managed_conflict/managed_write` 人工修改保护。真正 `reuse_all`、展示内容不变仍不改时间戳。不得生成与 Markdown 不一致的新版权威输入包；同一事务按第 3.4.1 节处理 validator，不能仅重绘后照搬旧终态。
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


### 3.4 三处正常调用链的完整衔接

以下修改仍归属 R1/R2 的既有组包和修订入口，不建立校验历史系统、引用授权框架或新指纹体系。

#### 3.4.1 普通 finalize 的重绘与两轮文字校验

- **入口区分**：`cmd_stage2_finalize` 是成员/参考/显示等业务状态重新物化；`cmd_stage2_refine_finalize` 是已记录第一轮问题后的文字修订。后者会改变正文但必须保留本轮 `round=1` 和修订证据；通过 `--direction-id` 定向修订后仍有未完成方向时保持 `needs_correction`，全部完成才进入 `awaiting_second_validation`，之后只能记录第二轮；不能采用“正文 hash 变了就清零”的通用规则。
- **普通 finalize 的失效条件**：最终方向、成员、参考许可/可信材料或渲染正文等校验依据有实质变化时，旧 validator 不再复制到新包；由新包的正常第一轮 `stage2-record-validation` 开始一次新业务版本的校验。旧终态（含已用两轮）不得锁死新版本，也不得被当作新版本已通过。先完成资料/许可检查、受管文件保护和新摘要计算，成功写入的包、Markdown、validator 状态必须一致；拒绝/人工冲突时沿用现有失败边界，不先抹掉旧状态。
- **不变时复用**：真正 `reuse_all` 不写时间戳、不重置校验。如果普通 finalize 仅重写生成时间或缓存元数据，且方向映射、校验材料与受管正文未变，先验证旧记录对旧包及实际受管正文的绑定有效（含非终态，不能以仅接受 terminal 的 `stage2_validator_accepts` 代替），再保留原轮次/phase/问题与修订证据（包括尚待修订状态）；旧绑定无效须按现有证据错误拒绝，不可借重写恢复通过。仅对已确认等价的新包更新其现有 `pack_sha256` 绑定，正文摘要仍须与实际文件一致。不能只比较成员数或无新 jobs，更不能重新绑定 hash 来认可实质变化。
- **原始报告保护**：不改写或删除既有原始报告。调用者在新业务版本的事务临时目录保存新的第一/第二轮报告并交给记录器；同一校验周期继续使用现有第一轮→定向修订→第二轮上限，终态与超轮拒绝不变。不额外引入历史数据库、epoch 或持久运行清单。
- **源码交接点**：修改 [普通 finalize 的旧 validator 继承](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py#L5024-L5080)，衔接 [摘要校验](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py#L3604-L3651) 与 [修订后保留轮次、原始报告记录](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py#L11224-L11325)。同步主技能和两份 analyzer 的新版本报告路径/轮次交接说明，不改变文字标准。

#### 3.4.2 两种 refine 入口使用同一个最终输入包

- **先核对来源，后使用最终方向**：将 `stage2_pack_matches_facts` 和 `stage2_refine_context` 列入修改点。传入 `--facts` 时先用 `Stage2Context` 核对教授身份、原始方向集合及事实新旧关系；通过后与 `--professor-dir` 一样构造 accepted pack 的最终方向上下文。`stage2-refine-plan` 的 jobs、`stage2_validation_material`、`stage2-refine-finalize` 的 narrative/gap/P/L 校验与渲染均使用最终方向 ID、最终 gap 和持久化参考资料，不能仍按原始 facts 找拆分子方向或已消失的合并源。
- **比较正确的证据**：未消失的原始方向优先用 `provisional_input_fingerprint` 与当前原事实指纹比较，不再把面向下游的最终 `input_fingerprint` 当原事实指纹。已合并而不再独立存在的源方向不能只用 resolve 指纹替代原事实指纹（后者还包含参考集、红线和论文摘要等）。普通 finalize 在包内既有 `resolved_directions.directions[]` 原始来源→目标映射行增加 `provisional_input_fingerprint`，直接保存本轮原始 `ctx.direction_plans` 中 `plan["fingerprint"]`（可复用已有 `provisional_fingerprints`，但须包含被合并删除的源且值来自本轮原始 plan）；读取时逐个与原始 facts plan 比较，同时核对目标/源关系。没有消失的方向仍用其方向字段，映射中也有值时须一致；不增加新指纹算法或独立来源账本。拆分子方向从其原始源及已有拆分关系核对，不要求 facts 凭空提供子方向。原始方向新增、缺失、指纹变化或映射不能自洽时返回 `needs_refresh/source_fingerprint_changed`，不得静默忽略用户明确提供的 facts。
- **旧包兼容有界**：仅对没有已物化归属、同一原始方向身份且确无 provisional 字段的旧包，允许原公开指纹作原事实指纹比较。已物化归属却缺少可核对的来源证据则要求刷新，不伪造指纹、不从正式成员反推来源。无 facts 的纯 pack 读取继续按原契约工作，不强制保存临时 facts。
- **直接影响**：指纹来源来自 [最终成员指纹与原始来源保存](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py#L4967-L5065)；读取/任务/修订的连续链见 [11042—11145 行](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py#L11042-L11145)。仅修比较和上下文衔接，保留现有 Stage 3 最终成员指纹语义，不新增来源认证层。

#### 3.4.3 最终方向的参考范围继承

- **原始与 refined 方向**：以该方向本轮 facts 的 `relevant_keys` 为参考范围；正式成员增删不自动增删 `P` 引用许可。参考集与正式成员分别去重和校验，不拿教授级 `papers` 的存在当许可。
- **拆分**：源方向保留原参考集，包括已移到子方向但仍可供源方向分析的论文；这不保留其正式成员资格。首次创建子方向时以获准子方向最终正式成员（含合法全文救回）建立子方向参考范围，保持原子方向 pack-only 的最小合法范围，不继承源方向全部参考。已物化子方向无变化重跑保留其有效参考集；源决定变化须按当前批准拆分重新建立，不用过期范围兜底。
- **合并**：目标参考范围为本次参与合并的目标与源方向有效参考集的去重并集，和正式成员/gap 一起在源方向删除前物化；不带入未参与方向。保留既有目标 narrative，不自动拼接源 narrative；后续修订只在该最终范围内引用。
- **读取与资料**：各最终方向均显式保存 `relevant_keys`（空列表也表示空许可），`papers` 只收集正式成员与参考所需的唯一规范记录。读取函数和 `narrative_scope`/validation material 不得用 truthy 判断把显式空列表回退到成员；仅字段确实缺失的旧包采用第 3.1.4 节最小兼容，格式错误仍拒绝。`P` 的可信标题和最终许可在写入前核对；`L`、gap 继续各自现有权限，不以本段扩大。
- **源码交接点**：[拆分创建、合并迁移](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py#L4841-L4965)、[pack-only 上下文](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py#L1710-L1752) 及第 3.1 节组包/论文收集共同实现；禁止只补序列化字段而遗漏真实修订读取。

## 4. 方案取舍与限制

- **选择**：在现有 `contact_state.py` 的事实/组包、校验和状态写入入口修复根因；对外保留现有 JSON 路径、`direction_id` 身份、受管文件与阶段职责。只在 Stage 2 的实际契约边界同步模型说明。
- **拒绝的替代方式**：由协调代理删除多出的 `supporting_item_keys`、手工改写原始校验 JSON、猜测 `resolve-*.json` 的短名，或在下游 Stage 3 过滤错误成员。这些办法不会修复生产入口，再次运行会复发。另一个方案是让相关论文和正式成员继续共用一个字段、仅修改显示数量；它会继续污染 Stage 3 指纹，因此不采用。
- **intended_change**：正式方向成员仅来自原始成员及被接受的决定，拆分源保留正式成员；合法参考论文存于现有输入包并可在无 facts 时恢复；旧归属变化触发受管文档重绘；重复引文逐条定位或拒绝；缺本轮新结果或旧轮次结果时在落盘前失败。
- **preserved_behavior**：教授身份与 `direction_id`、合法共享论文、经全文验证的跨方向新增、已确认的细化/拆分/合并、有效 accepted/pending 复用和显式沿用 provisional；论文/gap/freshness/叙事输入范围、受管 Markdown 人工保护、Stage 2 校验两轮限制、Stage 3—5 只消费已接受输入包；`papers` 中增加参考记录不能扩大下游正式成员与引用许可。
- **approved_behavior_change**：2026-10-16 用户已授权的三项错误修复及本轮明确要求的拆分非空、参考信息持久化、旧包重绘与结果隔离；`--results-dir` 和新 job 的 `resolve_run_id` 是此次修复必需的 Stage 2 调用接口变化，仅同步本仓库正式调用者。不改 Stage 1、Zotero、论文全文分析规则、Stage 3—5 产品逻辑和其他仓库。
- **prohibited_side_effect**：不得把“相关”当“正式归属”，不自动接受缺席的模型输出，不跳过人工采纳、不将旧报告改写为通过、不使用用户生产目录测试、不增加全仓运行/模型采样/跨仓安装作为本次默认必测项目。
- **故障边界**：本轮缺结果、旧 `resolve_run_id`、原始正式成员证据缺失、旧缓存来源不可证明、校验位置不唯一时，均须在写入本教授权威状态前拒绝；合法 pending、accepted 和用户显式沿用保留；同教授方向仍按现有整批写入边界执行，并发锁及无关缺陷不顺手重构。

## 5. 唯一完整测试计划（test-r5，第一关已通过，第二关待复核）

**测试版本**：`stage2-three-runner-defects-test-r5-2026-10-17`，对应已批准的执行方案 r3 第 3.1—3.4 节。2026-10-16 用户要求同步测试计划，2026-10-17 由本地测试工程师在 test-r4 落实测试实现：补齐直接受 `--results-dir`／`resolve_run_id`／缺结果拒绝影响的旧用例和共用准备，实现 T1—T5 的六个测试方法（T3 两个），并把真实选择器、Python 路径、临时目录与完整命令写入第 5.2 节。test-r5 仅澄清 T5 缺失原始成员来源场景的测试准备与拒绝判定，并交接 T4/T5 共用测试环境的初始化修复。保留原 T1—T5 的业务目标、场景和验收标准，不新增测试项。使用现有 `unittest`、CLI 和合成临时教授目录；无新增测试服务或通用判定器。第 5.1 节是唯一 recipe，第 5.2 节是最终选择器及执行交接；没有独立同题测试文件，也不改写已完成 PR #86 的历史测试计划。

| 业务目标 | 输入或场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- |
| T1：正式成员与参考持久化 | 初始成员 6 篇、参考集多 `GTQBNPED`，仅已接受 `D6XQCHTP` 新增；另方向合法加入 `GTQBNPED`，该参考论文只用于 `{{P:key}}` 且无 gap/后续引用。同一已物化包分别经原 facts 校验和无 facts 的 `--professor-dir` 修订入口读取；另给真正变化的原事实。 | 前方向恰好 7 篇、无 `GTQBNPED`；另方向保留获批成员；`papers[item_key]` 保存参考论文唯一可信标题、`directions[].relevant_keys` 保存引用许可；无 facts 仍能渲染和修订 `P` 引用，Stage 3 成员范围未放宽，最终指纹使用 7 篇正式成员；两入口使用相同最终方向和参考资料，原事实未变可修订，真正过期事实仍拒绝。 | 扩展 `test_stage2_resolved_direction_downstream_regressions.py`，检查最终输入包、受管 Markdown、pack-only 修订正式入口及既有 Stage 3 论文范围。 |
| T2：合法归属保持、拆分源非空 | 合法 `refined/split_from/merged_into`、共享论文、已接受拆分子方向无变化重跑和全文救回；另有源方向唯一正式成员被全部移走，但 `relevant_keys` 仍包含参考论文的拆分提案。 | 合法成员与 gap 迁移、共享身份和 accepted 复用正确；源正式成员将被移空的拆分被拒绝且不写新接受状态，参考论文不能作为剩余成员；按 3.4.3 断言源/子/合并目标参考集和可信标题，拆分子方向与合并后目标在两种 refine 入口均可定位，不再要求消失的源为最终方向。 | 复用并定向扩展 `test_stage2_resolved_direction_downstream_regressions.py` 和 `test_stage2_resolved_direction_acceptance_boundary.py` 正式入口断言。 |
| T3：每轮结果隔离、缺失和合法复用 | 同方向连续两轮：第一轮有正确 JSON，第二轮新目录缺文件或只有短名；复制上一轮同名文件到第二轮；最后生成当前 `resolve_run_id` 的正确文件。覆盖同批其他方向已接受、待选提案和显式 `--keep-provisional`。 | 第二轮缺文件报 `result_missing`，旧同名文件的轮次不符报 `invalid_result_json`，失败时整批权威状态不变；补齐正确文件才成功；已有 accepted 直接复用、proposed 仍待选，显式沿用无模型文件仍合法。 | 扩展 `test_stage2_resolved_direction_regressions.py` 和既有接受边界测试，仅核对正式 CLI 回执及权威文件前后差异。 |
| T4：重复引文的定位与拒绝 | 同一阻塞 `quote` 出现在受管正文三个物理行，原始 style-validator 报告对三行分别给出准确行号；另有仅填“第57行及多处”的原始报告副本。 | 三条准确记录逐一归到其真实方向并进入正常修订状态；含糊格式返回可操作的定位错误，不记入校验状态，也不修改正文/输入包；不得选任意单处。 | 扩展 `test_stage2_style_validation_handoff.py` 的 `stage2-record-validation` 正式入口与前后文件检查。 |
| T5：旧包修复后同步重绘 | 旧语义版本输入包被 `relevant_keys` 扩大正式成员；本轮原始成员和有效 accepted 决策可用、旧受管 Markdown 存在，`needed_keys=[]` 且名称未变；旧包含已用两轮的 terminal validator；对照合法新版本无变化包，以及同周期第一轮问题后的文字修订。 | 旧包预检不能 `reuse_all`；重算正式成员并更新分析 Markdown 与渲染摘要，不能留下新输入包/旧文档；原始成员来源无法证明则零写入拒绝；旧校验不能认证新正文，新版本可从第一轮开始且历史报告保留；同周期文字修订仍保留第一轮并受第二轮上限约束；合法无变化包仍复用校验，元数据重写不导致摘要失配或轮次重置。 | 使用现有 `stage2-preflight`、`stage2-plan/finalize` 与受管 Markdown 的检查方式定向扩展预检测试。 |

### 5.1 场景准备、调用顺序与验收点

**共同准备**：沿用 `.apm/skills/professor-contact/tests/` 的 `BaseEnv`、`ResolvedPipelineMixin`、`run_cli` 和现有合成事实/叙事/原始报告构造方式。每个测试的教授目录、facts、结果和报告都在仓库外独立临时目录；只创建该项需要的方向和论文。预检证明由正式 `stage2-preflight` 生成，正式状态由 plan/finalize/accept/record 命令推进；历史兼容输入可用现有合成旧包夹具表示，但不得在被测调用后直接改产物来制造成功。假设用户的接受决定由现有测试输入表达，不运行模型。保留未变的事实、gap、新近性和用户笔记；不得访问真实 Zotero、教授目录或用户缓存。无需 Nix build、重新安装、Codex/OpenCode 实跑或 Stage 0—5 联调。

**修订命令接线**：`stage2-record-validation --professor-dir <教授目录> --validation-file <本轮原始报告>` 先建立校验状态；`stage2-refine-plan` 使用 `--facts <facts>` 或 `--professor-dir <教授目录>` 二选一，并传同一 `--validation-file`。按返回 job 的 `result_file/result_schema` 在本项独立结果目录准备完整合成 rewrite JSON；随后 `stage2-refine-finalize` 使用相同来源参数、`--validation-file <已记录报告>`、`--results <rewrite目录>`，定向分批时 plan/finalize 同传 `--direction-id`。第二轮报告依据修订后的当前正文另行构造并保存为新文件，不能复用旧正文位置。以上由现有测试 helper 调用，不新增外部编排脚本。

**T1 recipe：成员与参考资料，以及两种修订入口**（对应 3.1、3.4.2）

1. 用表中“原 6 篇 + 获准 D6XQCHTP”的方向与另一合法方向准备 facts，`GTQBNPED` 在前方向仅为参考；通过正式 resolve 接受与 `stage2-finalize` 生成包和分析稿。断言前方向正式成员恰为预期 7 篇，参考集独立保存，教授级 `papers` 只有该 key 的一份可信记录，最终下游指纹与成员相符。
2. 从当前正文取得一条可修订的原始阻断报告，使用 `stage2-record-validation` 记录第一轮。对同一未改变状态先分别调用 `stage2-refine-plan --facts <facts> --validation-file <report>` 和 `stage2-refine-plan --professor-dir <professor> --validation-file <report>`；比较 jobs 的最终方向 ID、P 引用范围/真实标题和 gap 范围，不要求两份回执逐字节一致。
3. 两种 `stage2-refine-finalize` 入口都要有正常成功覆盖，但不在所有归属上重复全套：T1 用 `--facts` 完成当前方向修订；T2 用无 facts 入口完成拆分子方向或合并目标修订。合法 `{{P:GTQBNPED}}` 渲染为真实标题，未变正式成员不受影响，`L`/gap 按既有许可保留；Stage 3 的现有范围断言只检查正式成员/已有 gap，不跑完整下游业务。
4. 在独立夹具保留旧已接受包，提供真正变化的 facts（选一个原始方向参考论文事实摘要变化即可），调用带 facts 的 refine 入口应返回 `needs_refresh/source_fingerprint_changed`，不写新包、正文或修订任务；不能静默改用 pack-only。成功路径保留 facts，pack-only 路径不传 facts 且无需其文件存在，不把清理临时文件作为额外验收机制。

**T2 recipe：拆分、合并及最终方向上下文**（对应 3.1.2/5、3.4.2/3）

1. 复用既有合法归属夹具：分别物化已接受的拆分和合并，保留共享论文、全文救回与 gap 迁移的现有断言。拆分源的参考集仍为原范围，即使论文移到子方向也不变成源正式成员；新子方向参考集等于获准最终子成员（含合法全文救回），不继承源的额外参考。合并目标参考集等于参与双方参考并集，正式成员独立计算，不混入第三方向；目标 narrative 不被源 narrative 拼接。
2. 检查包内原始来源映射保存本轮原始指纹：合并源不在最终 directions，却仍在 `resolved_directions.directions[]` 有正确来源值及目标；最终方向的公开指纹继续用于下游。对未变 facts 调用 refine-plan 能找到最终子方向/合并目标，jobs 不要求已消失源或 facts 中不存在的子方向；按 T1 的分配以无 facts 入口完成一次最终方向修订，核对对应 P 引用标题和最终 gap，保持包内成员及来源映射。
3. 为判定来源比较不是误用 resolve 指纹，在上述合并夹具的独立状态中，只改变已消失源的原事实字段（选 `red_lines`，该字段进入原始方向指纹但不由 resolve 指纹完整代表），带 facts 的 refine 入口必须拒绝为需刷新。旧已合并包缺少来源指纹时也明确需刷新，不伪造指纹或反推成员；仅改变这一兼容字段，不穷举所有来源字段。
4. 无变化再次 finalize 后，既有子方向的成员与有效参考范围保持。源唯一正式成员被移空、仅剩参考论文的提案在接受/物化边界拒绝，权威状态不部分更新。纯读取旧包确实缺少 `relevant_keys` 时仅以成员为最小范围；显式 `relevant_keys=[]` 则保持空 P 许可，不能用教授级 papers 或成员兜底。上述为同一参考范围兼容检查，不增加其它格式矩阵。

**T3 recipe：本轮结果、缺失与有效复用**（对应 3.3，保留原 R3）

1. 每次 resolve-plan 前在教授事务目录创建独立 `resolve-run.XXXXXXXX`，传 `--results-dir`，按回执 `jobs[].result_file` 和本轮 `resolve_run_id` 准备合成 JSON；finalize 的 `--results` 使用同一目录。目标方向第一轮只发 plan、生成正确 JSON，不 finalize 接受（模拟中断后重新规划）；第二轮在相同 facts 的新目录重新 plan，确认该方向确有新 job，再检查缺失/旧轮次输出，不能拿已接受且无需 job 的方向制造缺失失败。
2. 第二轮新目录依次保留代表性失败状态：无完整文件/只有短名应 `result_missing`；上一轮同名 JSON 应 `invalid_result_json`。分别检查 `_resolved_directions.json`、输入包及 accepted 缓存未被部分接受；不要求重放全部调用或保留全量 trace。最后在同一第二轮目录补齐当前标识的完整结果，正常 finalize 才能成功。
3. 同批方向分别代表有效 accepted、proposed 和显式 `--keep-provisional`：accepted 不重发任务并忽略残留文件，proposed 无新文件仍 `needs_user_choice`，点名沿用的方向无模型文件仍合法，但不替其它缺结果方向免检。只使用本轮清单的这些状态，不穷举文件名、平台或并发组合。

**T4 recipe：重复引文定位**（对应 3.2，保留原 R2）

1. 用正式生成的受管正文准备同一句 quote 的三处可修订物理行，原始 `result/files/notes` 报告分别给出三个实际行号（含 frontmatter 偏移）。`stage2-record-validation` 后按行核对真实 direction_id 与修订范围，不能把三处都归到第一次命中。
2. 使用相同正文的独立未记录夹具和原始含糊报告“第N行及多处”，调用记录器必须明确拒绝、无新增校验状态且包/正文不变。不得由协调者手工修报告后称原报告通过；合规报告作为另一个正常输入。位置格式仅覆盖 3.2 明确支持的整数、ASCII 数字字符串、“第N行”及唯一命中的旧文本兼容，复用同一定位场景，不扩大为任意字符串模糊测试。

**T5 recipe：业务重绘与同周期两轮限制**（对应 3.1.6/7、3.4.1）

1. 以合成旧语义包表示相关论文误入成员，并有与其正文正确绑定的已完成两轮终态；保留两份旧原始报告文件。当前 facts 和有效 accepted 决定可用、无需新 narrative jobs、名称不变。通过 `stage2-preflight` 及普通 `stage2-plan/finalize` 纠正成员：旧包不能 `reuse_all`，新 Markdown/渲染摘要与新包一致，旧终态不能认证新正文。用新事务路径上的新报告调用 `stage2-record-validation` 应从 round 1 正常记录，而非 rounds_exhausted；旧原始报告内容不变。原始成员依据缺失的独立夹具只从已成功生成包的合法事实中移除 `member_keys` 和 `provisional_member_keys`，其余事实与既有权威产物保持不变；用现有 `stage2-preflight`、`stage2-plan` 对修改后的事实取得有效前置证明和实际所需结果清单，复用该夹具已有的完整 freshness/narrative 结果，只补足本轮实际必需的结果。不得另建仅含 `narrative.json` 的残缺结果目录，使失败提前落在 `result_missing` 等无关问题上。`stage2-finalize` 必须明确因缺少原始正式成员来源而拒绝，且权威输入包、正文零写入；只检查 `status != ok` 或存在任意 `reason_code` 不足以判通过。前置证明不符、结果缺失或结果格式不合法导致的拒绝均不算该项通过；不另外要求完整调用链证明或增加独立测试。
2. 在上述新版本第一轮报告中指出两个方向的可修订问题。按 `--direction-id` 只修第一个后，仍为 round 1/needs_correction，未完成方向继续有任务，提前第二轮记录被拒绝；修完剩余方向后才是 awaiting_second_validation。新第二轮报告记录后进入既有终态；复用原“第二轮仍阻断”场景确认停止、不能开第三轮。每次只断言本次改变的正文、pending/correction IDs、round/phase 与相应绑定；不新建历史校验账本。
3. 对照合法不变包：真正 reuse_all 不写时间戳或重置 validator。再直接调用普通 `stage2-finalize`，传相同 facts、有效归属文件及对应结果目录/预检证明，确保实际执行了无新业务内容的普通 finalize，而非只停在 preflight。其仅重写生成时间/缓存时，在旧绑定有效的前提下保留 round/phase/问题及修订记录，并与新包正确绑定；若实现选择等价状态完全不写，原绑定和状态保持也满足目标，仍须完成该调用。沿用一个已有未完成纠错状态观察即可，不把每个 phase 做排列组合。另一个明确旧绑定已失效的代表输入不得借元数据重写恢复通过，按证据错误拒绝。普通 finalize 不得套用“正文变化即无限清零”，文字修订始终受步骤 2 的两轮限制。

### 5.2 最终测试选择器、执行与结果交接

test-r4 已提交测试实现，test-r5 补充下述两处准备修正：下表五个目标列出**已经写入本分支的选择器**（T3 有两个方法），不是待实现名称，也不是已运行的结果；本次接口迁移处理的旧方法远多于五个，完整清单与命令见本节末尾的“实际执行选择”。选择器与实现位置仍然一一对应；若后续改名，先在本节按同一 T 编号更新真实选择器，不增加目标或重复跑覆盖相同结果的旧方法。

| 目标 | 已实现 unittest 选择器 | 实现位置与复用 |
| --- | --- | --- |
| T1 | `test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_member_reference_persistence_and_refine_sources` | 复用成员/下游指纹夹具，加入 5.1 的两入口对照与正式 refine 成功路径。 |
| T2 | `test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_resolved_reference_inheritance_and_source_mapping` | 复用拆分物化/子方向重跑/合并夹具；非空接受边界可复用 acceptance_boundary 的既有 helper，不要求整模块。 |
| T3 | `test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_resolve_run_isolation_and_missing_results`；`test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_keep_provisional_exempts_only_the_named_direction` | 使用现有正式 CLI/helper，复用 accepted/pending/keep-provisional 准备；不得只测内部函数代替命令结果。 |
| T4 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_repeated_quote_locations_and_ambiguous_report` | 复用原始报告与受管正文夹具及其正式 record CLI。 |
| T5 | `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle` | 复用 preflight、record/refine 及第二轮终态 helper，加入本节的重绘和部分修订观察点。 |

**T4/T5 已实现测试的接线修正（本地测试工程师，属于现有目标）**：

- `test_stage2_style_validation_handoff.py` 的 `_fresh_stage2_env()` 当前以不存在的 `_isolated_stage2_fixture` 初始化 `unittest.TestCase`，运行到该帮助函数会因不存在的方法名报错。改为传本实例已有的 `self._testMethodName` 创建相同类的独立环境，只调用其 `setUp()` 并在外层注册一次 `tearDown()`；不能在帮助函数内执行该实例的测试方法。T4 的含糊位置报告与 T5 的旧包/缺来源/不变包均使用该帮助函数，必须完成这项直接接线修正；不新增测试目标或单独验证测试框架。**（本地测试工程师已按此修正，提交 `0367c78`。）**
- `test_stage2_style_validation_handoff.py` 的 `_t5_assert_missing_member_source_rejected()` 当前另建只含叙事结果的 `gap_free_results`，且只断言有任意错误。按第 5.1 节 T5 第 1 步，保留可用的完整结果及当前事实的前置证明，以原始成员来源缺失对应的明确拒绝和权威文件零写入作为判断；不改变生产保护或用例预期去迎合实现。上述两处由本地测试工程师改现有帮助函数/方法即可，T1—T5 清单及实际选择器不变。**（本地测试工程师已按此修正，提交 `0367c78`。）**

**T3 的既有测试迁移（属于原目标，不新增 T6）**：本地测试工程师须同步调整受 `--results-dir`/`resolve_run_id`/缺失拒绝直接影响的旧用例和共用准备，不能只实现上表新选择器。依据当前 `4aac295265acabbc63b39df4ea6c153285d296f7` 的 `test_stage2_resolved_direction.py`：

- **旧计划调用**：[第 137、181、225 行等](https://github.com/ScholarWorkflow/professor-contact/blob/4aac295265acabbc63b39df4ea6c153285d296f7/.apm/skills/professor-contact/tests/test_stage2_resolved_direction.py#L132-L226) 及同文件其它 `stage2-resolve-plan` 调用须在调用前创建本轮独立绝对结果目录，传入必填 `--results-dir`；即使预期为 accepted 复用、无 jobs，正式 plan 调用也不能省参。连续 plan 用新目录，同轮 finalize 使用对应目录，缺文件补齐重试仍用原轮目录。
- **旧成功结果及失败 fixture**：[第 335—355 行成功结果](https://github.com/ScholarWorkflow/professor-contact/blob/4aac295265acabbc63b39df4ea6c153285d296f7/.apm/skills/professor-contact/tests/test_stage2_resolved_direction.py#L335-L355) 等需先取得本轮 plan，按 job 的 `result_file/result_schema` 写完整结果并回填当前 `resolve_run_id`，不得硬编码旧路径或自行猜标识。验证其它既有拒绝原因的输入也先满足本轮目录/身份前置条件，确保仍在检查原业务原因，而非意外被新格式提前拒绝；专门检查旧轮次/缺文件的 T3 输入则保留其有意不合规之处。合法 accepted/proposed 缓存不补写临时 run ID、不改变缓存指纹。
- **替换冲突断言**：[第 256—296 行 `ResolvedDirectionFinalizeTests.test_resolve_finalize_unchanged_when_no_result`](https://github.com/ScholarWorkflow/professor-contact/blob/4aac295265acabbc63b39df4ea6c153285d296f7/.apm/skills/professor-contact/tests/test_stage2_resolved_direction.py#L256-L296) 改为本轮真实发出新 job、无有效 accepted/pending 复用且未显式 keep-provisional 的缺结果拒绝测试，可重命名为 `test_resolve_finalize_rejects_missing_new_result`；预期 `result_missing`、无默认 accepted/unchanged、权威文件和缓存不部分写入，不再保留 `status=ok / unchanged` 的旧成功断言。合法 unchanged 成功必须提交本轮完整 unchanged JSON，不能靠缺文件实现；显式沿用和有效复用继续采用 5.1 T3 的保留规则。
- **迁移共用 helper 及直接调用者**：[第 471—485 行 `ResolvedPipelineMixin.run_resolve`](https://github.com/ScholarWorkflow/professor-contact/blob/4aac295265acabbc63b39df4ea6c153285d296f7/.apm/skills/professor-contact/tests/test_stage2_resolved_direction.py#L471-L485) 要在 plan 前分配独立目录、保存本轮 job/标识、按返回路径写结果，再把相同目录交 finalize。旧成功夹具传 `{}` 或只列部分方向时，若其它方向仍有新 job，应显式构造该场景所需的合法 unchanged 合成结果，而不能依赖产品的缺文件默认；缺失负例须保留专用缺文件路径，不能被 helper 自动补齐。同步依赖固定 `resolve_results` 路径的直接调用者使用 helper 的本轮目录；只更新受该 helper/接口直接影响的其它测试文件，不扩成全仓测试重构。
- **独立预检测试的结果生成函数**：[`test_resolved_direction_preflight_integration.py` 第 106—128 行](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/tests/test_resolved_direction_preflight_integration.py#L106-L128) 的 `ResolvedPreflightBase` 有独立的 `results_dir`、`write_resolve_result()`、`resolve_finalize()`，没有使用 `ResolvedPipelineMixin.run_resolve`。本地测试工程师必须单独迁移：需要新模型结果的场景先在隔离教授目录完成既有 preflight/facts 绑定，然后为**本轮 resolve** 创建独占绝对目录，调用 `stage2-resolve-plan --facts <facts> --results-dir <本轮目录>`；根据回执 `jobs[].result_file`、`jobs[].result_schema` 和 `resolve_run_id`，由 `write_resolve_result()` 写入对应的**模拟模型归属 JSON**（保留原 `resolved` 决定，只增加本轮必填身份与格式）；`resolve_finalize()` 再以该目录调用 `stage2-resolve-finalize --results`。新一轮重新 plan 须重新分配目录，失败后同轮补齐才复用原目录；不得用原固定 `self.root/results` 的旧文件代替本轮结果，也不要误改普通 `stage2-finalize` 的 freshness/narrative 结果目录。该文件 [第 280、312 行等](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/tests/test_resolved_direction_preflight_integration.py#L278-L315) 直接调用 resolve-plan 的路径也须传独立 `--results-dir`，即使预期没有新 job。保留原 preflight、拆分/合并、复用、证据绑定断言，不把模拟结果来源本身列为额外证明目标。
- **其余未经过共用 helper 的直接调用**：`test_stage2_resolve_fingerprint_scope_regression.py`（[直接 plan 调用](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/tests/test_stage2_resolve_fingerprint_scope_regression.py#L47-L54)）、`test_stage2_resolved_direction_fresh_review_regressions.py`（[直接 plan](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/tests/test_stage2_resolved_direction_fresh_review_regressions.py#L126-L133) 和 [手写结果](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/tests/test_stage2_resolved_direction_fresh_review_regressions.py#L140-L175)）、`test_stage2_resolved_direction_merge_fulltext_regression.py`（[直接 plan](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/tests/test_stage2_resolved_direction_merge_fulltext_regression.py#L46-L54)）、`test_stage2_resolved_direction_downstream_regressions.py`（[手写结果与 finalize](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/tests/test_stage2_resolved_direction_downstream_regressions.py#L189-L228)）及 `test_stage2_resolved_direction_acceptance_boundary.py`（[直接 finalize/显式沿用](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/tests/test_stage2_resolved_direction_acceptance_boundary.py#L96-L114)）均须按各自实际调用迁移。直接 plan 补本轮目录；需要新结果的测试先获得本轮 plan 和完整结果格式，再写本来要检查的业务内容；finalize 指向同一目录。已有 accepted/proposed 或显式沿用场景仍依正式复用条件，不强行补模型文件；检查其它拒绝原因时要先满足本轮目录/身份格式，避免提前在新校验处失败。若直接调用 `validate_resolve_results` 的既有单元测试因实现改动受到签名影响，只修对应参数和原断言。**以上只是旧调用适配新入口**，按原目标定向选择受影响方法，不追加同一行为的重复测试。
- **固定夹具的 plan 参数迁移**：[`test_build_issue29_stage2_fixture.py` 第 196—213 行](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/tests/test_build_issue29_stage2_fixture.py#L196-L213) 的 `test_material_pending_builds_the_canonical_proposed_state` 在第 208 行直接执行 `stage2-resolve-plan --facts ...`，须在调用前创建隔离的绝对结果目录并传入 `--results-dir`，保留原有的 `proposed` 状态与 `process` 动作断言。这是 test-r3 审核点名的漏项，归入 T3 的接口迁移，不另建目标、不要求重跑整文件。

- **实际执行选择（test-r4 定稿）**：下列全名已在本分支实测可被 `unittest` 收集（收集不代表执行）。五个 T 目标各自一条命令；新方法是该目标的主检查，被 `--results-dir`／`resolve_run_id`／缺结果拒绝直接改变的旧方法按业务观察面归入对应目标，复用原业务断言。`test_resolve_finalize_unchanged_when_no_result` 被 `test_resolve_finalize_rejects_missing_new_result` **替换**（不是并存），T3 新方法另外覆盖轮次隔离与合法复用，不重复运行覆盖同一结果的方法。

**T1（正式成员与参考持久化、两种修订入口）**
- 新：`test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_member_reference_persistence_and_refine_sources`
- 迁移后旧方法：同文件 `test_refined_membership_changes_stage3_input_fingerprint`、`test_split_materializes_candidate_outside_relevant_set`、`test_reused_split_preserves_materialized_child_membership`、`test_stage2_reuse_keeps_provisional_fingerprint_across_repeated_finalize`、`test_membership_resolution_requires_valid_fulltext_facts`

**T2（合法归属保持、拆分源非空、参考继承）**
- 新：`test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_resolved_reference_inheritance_and_source_mapping`
- 迁移后旧方法：`test_stage2_resolved_direction.Stage2SplitEndToEndTests.test_split_creates_second_authoritative_direction_and_stage3_jobs`、`…test_merge_keeps_only_target_direction_and_stage3_job`、`…test_merge_chain_is_rejected`、`test_stage2_resolved_direction.Stage2SplitReuseChainTests.test_split_first_apply_then_reuse_then_stage3_jobs`、`test_stage2_resolved_direction.StructuralResolutionEvidenceGateTests.test_merge_resolution_rejected_when_both_directions_lack_valid_fulltext_facts`、`…test_rename_resolution_rejected_without_valid_fulltext_facts`、`test_stage2_resolved_direction.ResolveAcceptanceBoundaryTests.test_finalize_rejects_sidecar_with_unaccepted_material_proposal`、`…test_finalize_rejects_partially_kept_provisional_sidecar`、`…test_resolve_accept_command_validates_keys_and_staleness`、`test_stage2_resolved_direction.MergeCandidateDetectionTests.test_detect_merge_candidates`、`test_stage2_resolved_direction_acceptance_boundary.ResolvedDirectionAcceptanceBoundaryTests.test_stage2_finalize_rejects_unaccepted_material_proposal`、`…test_partial_keep_provisional_does_not_accept_other_pending_direction`、`test_stage2_resolved_direction_merge_fulltext_regression.FullTextMergeRegression.test_disjoint_preview_clusters_can_be_merge_candidates_from_fulltext`

**T3（每轮结果隔离、缺失与合法复用）**
- 新：`test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_resolve_run_isolation_and_missing_results`、`…test_keep_provisional_exempts_only_the_named_direction`
- 迁移后旧方法：`test_stage2_resolved_direction.ResolvedDirectionPlanTests.test_resolve_plan_emits_jobs_for_each_direction`、`…test_resolve_plan_detects_removal_candidates`、`…test_resolve_plan_no_changes_when_all_match`、`test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_rejects_missing_new_result`、`…test_resolve_finalize_applies_removal`、`…test_resolve_finalize_rejects_invalid_removal`、`test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_applies_resolved_directions_to_pack`、`…test_finalize_stamps_resolved_subfield_on_unchanged_directions`、`…test_finalize_fails_closed_on_stale_resolved_file`、`…test_finalize_fails_closed_on_cross_professor_resolved_file`、`…test_finalize_fails_closed_on_missing_direction_entry`、`test_stage2_resolved_direction.ResolvedReuseTests.test_resolve_plan_reuses_unchanged_directions`、`…test_resolve_plan_reprocesses_when_facts_change`、`…test_resolve_finalize_preserves_reused_entries_without_results`、`test_stage2_resolved_direction.UserKeptProvisionalTests.test_user_kept_provisional_still_writes_explicit_resolved_direction`、`…test_user_kept_provisional_is_reused_until_resolve_input_changes`、`test_stage2_resolved_direction.CandidateUnionEvidenceTests.test_fingerprint_sensitive_to_candidate_outside_relevant_set`、`test_stage2_resolve_fingerprint_scope_regression.ResolveFingerprintScopeRegression.test_analysis_markdown_edit_does_not_invalidate_resolved_direction_when_facts_unchanged`、`…test_other_direction_profile_change_invalidates_target_resolution`、`…test_cross_direction_facts_validity_change_invalidates_target_resolution`、`test_stage2_resolved_direction_fresh_review_regressions.FreshResolvedDirectionReviewRegressions.test_cross_cluster_addition_can_cross_disjoint_candidate_sets`、`…test_cross_direction_facts_change_invalidates_target_resolution`、`…test_resolve_finalize_rejects_result_for_wrong_collection_key`、`…test_non_split_resolution_cannot_drift_resolved_id_from_collection_key`、`…test_new_material_resolution_is_not_reused_before_user_acceptance`、`test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_reused_direction_ignores_stale_result_file`、`test_build_issue29_stage2_fixture.BuildIssue29Stage2FixtureTests.test_material_pending_builds_the_canonical_proposed_state`

**T4（重复引文定位与含糊报告拒绝）**
- 新：`test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_repeated_quote_locations_and_ambiguous_report`
- 本目标没有受本次接口变化影响的旧方法；同文件其它方法不在本轮执行范围。

**T5（旧包修复后同步重绘、同周期两轮限制）**
- 新：`test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle`
- 迁移后旧方法：`test_resolved_direction_preflight_integration.TestSemanticsVersionBump.test_old_semantics_pack_cannot_reuse_all_and_re_arms_after_one_run`、`test_resolved_direction_preflight_integration.TestResolvedSetReuse.test_accepted_split_reuses_all_with_identical_stage3_visibility`、`…test_dropping_the_split_child_from_the_pack_blocks_reuse`、`…test_accepted_merge_reuses_all_and_keeps_single_stage3_direction`、`test_resolved_direction_preflight_integration.TestResolutionEvidenceUniverse.test_candidate_fulltext_change_misses_early_gate_and_re_triggers_resolution`、`…test_analysis_markdown_edit_does_not_re_burn_accepted_resolve_jobs`、`test_resolved_direction_preflight_integration.TestResolvedProofBinding.test_accept_refuses_sidecar_from_earlier_generation`、`…test_finalize_refuses_stale_generation_sidecar_with_zero_writes`、`…test_recovery_restamps_sidecar_for_the_new_generation`

**替代与合并关系**：`test_resolve_finalize_unchanged_when_no_result` 改名并改预期为 `test_resolve_finalize_rejects_missing_new_result`（旧 `status=ok / unchanged` 断言按 R3 删除）；`test_stage2_resolved_direction.py` 与预检文件中的旧结果目录 `self.root/resolve_results`、`self.root/results` 全部换成本轮独立目录；`ResolvedPreflightBase.write_resolve_result()/resolve_finalize()` 与 `ResolvedPipelineMixin.run_resolve` 各自完成迁移，后者被 10 个受影响文件里 28 个测试方法复用（`test_stage2_resolved_direction.py` 15 个）。没有受本次接口或共用准备变化影响的历史结果继续复用。

**执行条件、环境与完整命令**：产品和本节的受影响测试实现入库、第一/第二关完成复核后才执行。环境已于 2026-10-17 预检确认：`PYTHON=/run/current-system/sw/bin/python3`（Python 3.14.7，仅标准库；`contact_state.py` 只依赖标准库），备用包装为 `uv run --no-project --python python3`，同一次运行只用其中一种，不新装依赖。工作目录为目标仓库的 `.apm/skills/professor-contact/tests/`；正式执行先建立本次独占的仓库外目录 `/tmp/pc91-tests.XXXXXXXX/`，逐项目标保存标准输出、错误输出与退出码。

下面是 T1—T5 五条可直接复制执行的命令（选择器取自上文已确认的 60 个全名，未新增用例或设施）：

```bash
cd .apm/skills/professor-contact/tests
PYTHON=/run/current-system/sw/bin/python3
RUN_DIR=$(mktemp -d /tmp/pc91-tests.XXXXXXXX)

# T1
"$PYTHON" -m unittest -v \
  test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_member_reference_persistence_and_refine_sources \
  test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_refined_membership_changes_stage3_input_fingerprint \
  test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_split_materializes_candidate_outside_relevant_set \
  test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_reused_split_preserves_materialized_child_membership \
  test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_stage2_reuse_keeps_provisional_fingerprint_across_repeated_finalize \
  test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_membership_resolution_requires_valid_fulltext_facts \
  >"$RUN_DIR/T1.out" 2>"$RUN_DIR/T1.err"; echo $? >"$RUN_DIR/T1.rc"

# T2
"$PYTHON" -m unittest -v \
  test_stage2_resolved_direction_downstream_regressions.ResolvedDirectionDownstreamRegressionTests.test_resolved_reference_inheritance_and_source_mapping \
  test_stage2_resolved_direction.Stage2SplitEndToEndTests.test_split_creates_second_authoritative_direction_and_stage3_jobs \
  test_stage2_resolved_direction.Stage2SplitEndToEndTests.test_merge_keeps_only_target_direction_and_stage3_job \
  test_stage2_resolved_direction.Stage2SplitEndToEndTests.test_merge_chain_is_rejected \
  test_stage2_resolved_direction.Stage2SplitReuseChainTests.test_split_first_apply_then_reuse_then_stage3_jobs \
  test_stage2_resolved_direction.StructuralResolutionEvidenceGateTests.test_merge_resolution_rejected_when_both_directions_lack_valid_fulltext_facts \
  test_stage2_resolved_direction.StructuralResolutionEvidenceGateTests.test_rename_resolution_rejected_without_valid_fulltext_facts \
  test_stage2_resolved_direction.ResolveAcceptanceBoundaryTests.test_finalize_rejects_sidecar_with_unaccepted_material_proposal \
  test_stage2_resolved_direction.ResolveAcceptanceBoundaryTests.test_finalize_rejects_partially_kept_provisional_sidecar \
  test_stage2_resolved_direction.ResolveAcceptanceBoundaryTests.test_resolve_accept_command_validates_keys_and_staleness \
  test_stage2_resolved_direction.MergeCandidateDetectionTests.test_detect_merge_candidates \
  test_stage2_resolved_direction_acceptance_boundary.ResolvedDirectionAcceptanceBoundaryTests.test_stage2_finalize_rejects_unaccepted_material_proposal \
  test_stage2_resolved_direction_acceptance_boundary.ResolvedDirectionAcceptanceBoundaryTests.test_partial_keep_provisional_does_not_accept_other_pending_direction \
  test_stage2_resolved_direction_merge_fulltext_regression.FullTextMergeRegression.test_disjoint_preview_clusters_can_be_merge_candidates_from_fulltext \
  >"$RUN_DIR/T2.out" 2>"$RUN_DIR/T2.err"; echo $? >"$RUN_DIR/T2.rc"

# T3
"$PYTHON" -m unittest -v \
  test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_resolve_run_isolation_and_missing_results \
  test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_keep_provisional_exempts_only_the_named_direction \
  test_stage2_resolved_direction.ResolvedDirectionPlanTests.test_resolve_plan_emits_jobs_for_each_direction \
  test_stage2_resolved_direction.ResolvedDirectionPlanTests.test_resolve_plan_detects_removal_candidates \
  test_stage2_resolved_direction.ResolvedDirectionPlanTests.test_resolve_plan_no_changes_when_all_match \
  test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_rejects_missing_new_result \
  test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_applies_removal \
  test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_rejects_invalid_removal \
  test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_applies_resolved_directions_to_pack \
  test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_stamps_resolved_subfield_on_unchanged_directions \
  test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_fails_closed_on_stale_resolved_file \
  test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_fails_closed_on_cross_professor_resolved_file \
  test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_fails_closed_on_missing_direction_entry \
  test_stage2_resolved_direction.ResolvedReuseTests.test_resolve_plan_reuses_unchanged_directions \
  test_stage2_resolved_direction.ResolvedReuseTests.test_resolve_plan_reprocesses_when_facts_change \
  test_stage2_resolved_direction.ResolvedReuseTests.test_resolve_finalize_preserves_reused_entries_without_results \
  test_stage2_resolved_direction.UserKeptProvisionalTests.test_user_kept_provisional_still_writes_explicit_resolved_direction \
  test_stage2_resolved_direction.UserKeptProvisionalTests.test_user_kept_provisional_is_reused_until_resolve_input_changes \
  test_stage2_resolved_direction.CandidateUnionEvidenceTests.test_fingerprint_sensitive_to_candidate_outside_relevant_set \
  test_stage2_resolve_fingerprint_scope_regression.ResolveFingerprintScopeRegression.test_analysis_markdown_edit_does_not_invalidate_resolved_direction_when_facts_unchanged \
  test_stage2_resolve_fingerprint_scope_regression.ResolveFingerprintScopeRegression.test_other_direction_profile_change_invalidates_target_resolution \
  test_stage2_resolve_fingerprint_scope_regression.ResolveFingerprintScopeRegression.test_cross_direction_facts_validity_change_invalidates_target_resolution \
  test_stage2_resolved_direction_fresh_review_regressions.FreshResolvedDirectionReviewRegressions.test_cross_cluster_addition_can_cross_disjoint_candidate_sets \
  test_stage2_resolved_direction_fresh_review_regressions.FreshResolvedDirectionReviewRegressions.test_cross_direction_facts_change_invalidates_target_resolution \
  test_stage2_resolved_direction_fresh_review_regressions.FreshResolvedDirectionReviewRegressions.test_resolve_finalize_rejects_result_for_wrong_collection_key \
  test_stage2_resolved_direction_fresh_review_regressions.FreshResolvedDirectionReviewRegressions.test_non_split_resolution_cannot_drift_resolved_id_from_collection_key \
  test_stage2_resolved_direction_fresh_review_regressions.FreshResolvedDirectionReviewRegressions.test_new_material_resolution_is_not_reused_before_user_acceptance \
  test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_reused_direction_ignores_stale_result_file \
  test_build_issue29_stage2_fixture.BuildIssue29Stage2FixtureTests.test_material_pending_builds_the_canonical_proposed_state \
  >"$RUN_DIR/T3.out" 2>"$RUN_DIR/T3.err"; echo $? >"$RUN_DIR/T3.rc"

# T4
"$PYTHON" -m unittest -v \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_repeated_quote_locations_and_ambiguous_report \
  >"$RUN_DIR/T4.out" 2>"$RUN_DIR/T4.err"; echo $? >"$RUN_DIR/T4.rc"

# T5
"$PYTHON" -m unittest -v \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle \
  test_resolved_direction_preflight_integration.TestSemanticsVersionBump.test_old_semantics_pack_cannot_reuse_all_and_re_arms_after_one_run \
  test_resolved_direction_preflight_integration.TestResolvedSetReuse.test_accepted_split_reuses_all_with_identical_stage3_visibility \
  test_resolved_direction_preflight_integration.TestResolvedSetReuse.test_dropping_the_split_child_from_the_pack_blocks_reuse \
  test_resolved_direction_preflight_integration.TestResolvedSetReuse.test_accepted_merge_reuses_all_and_keeps_single_stage3_direction \
  test_resolved_direction_preflight_integration.TestResolutionEvidenceUniverse.test_candidate_fulltext_change_misses_early_gate_and_re_triggers_resolution \
  test_resolved_direction_preflight_integration.TestResolutionEvidenceUniverse.test_analysis_markdown_edit_does_not_re_burn_accepted_resolve_jobs \
  test_resolved_direction_preflight_integration.TestResolvedProofBinding.test_accept_refuses_sidecar_from_earlier_generation \
  test_resolved_direction_preflight_integration.TestResolvedProofBinding.test_finalize_refuses_stale_generation_sidecar_with_zero_writes \
  test_resolved_direction_preflight_integration.TestResolvedProofBinding.test_recovery_restamps_sidecar_for_the_new_generation \
  >"$RUN_DIR/T5.out" 2>"$RUN_DIR/T5.err"; echo $? >"$RUN_DIR/T5.rc"
```

`echo $?` 取的是紧跟其前的 `unittest` 退出码；缺方法或依赖属于尚未准备好，不能记业务失败或通过。

**业务产物检查**：在现有 unittest 中以 Python JSON 解析后的必要字段与关系断言；Markdown/报告仅在清单要求保持原样时比较内容或摘要。fixture 文件、报告和必要失败输出留在该项临时目录，运行记录只需版本、命令、T1—T5 逐项结果和未完成原因；不新增判定器、manifest、全环境快照、来源认证或逐调用证据设施。代理说明同步在实现 diff 里静态核对 3.2/3.3/3.4 的实际交接段落，不要求运行两套 harness 或重复安装验收。

**失败、重试与复用**：没有外部服务或模型调用，不安排外部采样重试。确认业务失败后保留失败，交产品负责人；隔离目录/权限/依赖缺失标无法判断，修正实际环境问题后只重试受影响项，不改输入、断言或绕过保护求通过。保留每次正式结果及必要复验记录；已有仍适用的结果按目标复用，不因计划或提交 SHA 改变重跑。方法、输入或预期确需修订时先更新本节并复核直接影响，再执行。超出 T1—T5 的检查须另获用户批准，未修改的候选评分、共享论文阈值、其他阶段、PR #86/#90 已完成验收不重新打开。

**当前交付状态**：测试设计和 recipe 已同步执行方案 r3；[test-r1 正式审核](https://github.com/ScholarWorkflow/professor-contact/pull/91#issuecomment-6219350308) 已确认第一关通过、第二关需修改、第三关未执行。test-r2 补齐主测试文件与共用 helper 的旧接口迁移；test-r3 进一步点明独立预检结果生成函数、直接 plan/finalize 调用文件和需要保留的业务断言；test-r4 由本地测试工程师落实测试实现：10 个测试文件完成旧调用迁移，T1—T5 六个方法已写入，真实选择器、Python 路径与完整命令已补入本节，`test_build_issue29_stage2_fixture.py` 的漏项已补齐。测试资产提交为 `d027de0`（同一 PR 分支，产品代码未改）；test-r5 仅澄清 T5 缺失来源场景并交接 T4/T5 两处测试准备错误；这两处已由本地测试工程师按上文修正并提交 `0367c78`（只改 `test_stage2_style_validation_handoff.py`，T1—T5 清单与选择器不变）。test-r5 第二关审核（2026-10-17，结论 NEEDS_MODIFICATION）提出 5 项，本地测试工程师已按最小范围修正并提交 `c70bd09`：T3 增加仅存在短名结果文件的同轮场景、T4 为两个合成方向补 `provisional_member_keys`、T5 夹具加入一项经正式 resolve/accept 入口接受的成员移除并在重算后检查仍生效、T1/T2 修订夹具复制原叙事全部 `gap_notes`、第 5.2 节改为五条可直接复制执行的完整命令。第一关沿用既有通过结论；第二关待复核（上述准备修正及步骤对产品实现的可执行性仍待确认）；第三关已由本地执行工程师按本节命令执行，执行记录见下条（2026-10-17 本地执行记录），第三关的正式审核结论仍待测试审核者给出；准备资产与静态核对不替代正式执行记录或自授 PASS。

**本地执行记录（2026-10-17，实现与受影响测试）**：产品实现提交 `810977a`（本 PR 分支；此前已把最新 `main@305bc08` 合入分支，提交 `c70df12`），按第 2—4 节完成 R1 正式成员来源与 `relevant_keys` 持久化、R2 报告位置规则、R3 每轮结果目录/`resolve_run_id`、旧语义 pack 重绘与 validator 生命周期，并同步主 `SKILL.md`、两份 analyzer 投影和 style-validator 说明。产品与测试版本：`810977a`、`stage2-three-runner-defects-test-r5-2026-10-17`；环境：`/run/current-system/sw/bin/python3`（Python 3.14.7，仅标准库）。按第 5.2 节五条完整命令执行 T1—T5 共 60 个选择器，产品与测试代码均未在本轮修改后失效；结果目录 `/tmp/pc91-tests.NArnigfE`：T1 6 个 OK、T2 14 个 OK、T3 29 个 OK、T4 1 个 OK、T5 10 个 OK，五项退出码均为 0，无 FAILED/ERROR。上述为本地执行工程师按有效计划得到的正式业务结果；测试计划第二关复核、第三关审核和合并审核仍由相应负责人完成，本记录不代表关口结论或合并批准。

**实现符合性审核与处置（2026-10-17，复核版本 `b036b10`）**：专用 implementation_reviewer 首次审核结论为**部分完成**，提出 3 处实现缺口与 2 处说明/记录问题，并列出 2 项待核实：①文字修订入口写盘前缺少 P 引用许可/可信标题检查；②facts 入口未核对教授身份与 pack 中额外的最终方向/来源映射；③损坏的 `relevant_keys` 被当成缺失字段回退；④三份说明把短名结果文件的错误码写成 `invalid_result_json`（实现与 T3 为 `result_missing`）；⑤第 5.2 节旧状态句与本轮执行记录矛盾；A 旧 validator 绑定无效时静默丢弃；B 复用方向的论文显示字段优先级。处置提交为 `b036b10`：①②③按审核意见修正，④⑤已更正；A 改为在无业务变化且旧绑定无效时以 `validation_render_stale` 拒绝、零写入；B 改为本轮 facts 优先、旧 pack 仅补足 facts 未声明的字段。修正后按第 5.2 节同一组 60 个选择器复验，结果目录 `/tmp/pc91-tests.0a5amS2C`：T1 6、T2 14、T3 29、T4 1、T5 10 全部 OK，退出码均为 0；未新增测试目标或选择器。审核仍为只读、未运行测试；是否完成复核由审核者按原问题编号给出，不构成测试关口或合并批准。

**P6 处置（2026-10-17，复核版本 `254fd06`）**：审核者定向复核确认问题 1—5 与 A/B 均已处理完，另提出 P6（低影响，B 的直接连带）：`_current_paper_record` 会从当前 facts 更新复用的 `pdf_available`，而受管分析头部「全文级/摘要级」计数使用该字段；`stage2_render_state` 未比较它时，pack 会更新而 Markdown 不重绘，旧 validator 也可能被携带。处置：把 `pdf_available` 纳入 `stage2_render_state` 的 papers 比较；未新增测试目标或选择器。修正后按第 5.2 节同一组 60 个选择器复验，结果目录 `/tmp/pc91-tests.1HB8NM3g`：T1 6、T2 14、T3 29、T4 1、T5 10 全部 OK，退出码均为 0。审核者已说明不新增测试义务；T5 旧绑定用例同时接受 ok/error 的判定宽严问题属第二关范围，不列为本角色产品缺口。

**实现符合性审核结论（2026-10-17，复核版本 `2493693`）**：专用 implementation_reviewer 对 P6 定向复核后给出**完整**：上一轮问题 1—5 与 A/B 均已处理完，P6 已按最小修正完成，未发现剩余产品符合性缺口；`pdf_available` 参与重绘比较带来的保守额外重绘/校验失效被视为可接受取舍。产品侧无剩余未完成项；测试计划第二关（含 T5 旧绑定用例判定宽严）、第三关和合并审核仍由相应负责人按正式规则完成。本结论不代表测试关口或合并批准，PR 继续保持 Draft。

**T5 旧绑定断言修正（2026-10-17，test-r5 第二关定向复审）**：按第二关 NEEDS_MODIFICATION 的唯一一项，由本地测试工程师只修改 `test_business_rerender_and_bounded_correction_lifecycle` 中 T5.3c 的 finalize 断言：固定 `status=error`、`reason_code=validation_render_stale`，并在调用前后比较 `套磁候选输入.json` 与已被人工改动的 `套磁候选分析.md` 字节；未新增测试方法、选择器或判定器，未修改产品代码（产品版本仍为 `254fd06`）。有限预检：`py_compile` rc=0、模块导入 rc=0、目标方法可被 `unittest` 收集 rc=0（命令输出与 pyc 在仓库外 `/tmp/pc91-preflight-20261017`；未执行用例）。本地执行工程师按第 5.2 节同一选择器定向执行该受影响方法：结果目录 `/tmp/pc91-t5c.NJBoJloj`，1 个方法 OK，退出码 0；T5 其余 9 个方法与此前结果按未受影响复用。专用 implementation_reviewer 对该测试准备资产定向审核结论为**完整**（版本 `7f300fa`，产品未改，未发现超范围或可让错误通过的断言路径）。测试第二关与第三关的结论由测试计划审核者按本记录复核。

## 6. 实施次序、交接与合并条件

1. **计划审核**：由独立审核者在当前基线及必要的目标版本上审 P1—P4，取得正式 `Plan conclusion: APPROVED`。若证据揭示另一个成员归属入口，先把新增关键事实及直接影响修订进本文件再复审；作者不得把此初稿标为批准。
2. **先修 R3 状态与结果入口**：在 `contact_state.py` 加入 `--results-dir`、`resolve_run_id` 和缺文件/错轮次拒绝；在 `validate_resolve_results` 中先处理显式 `--keep-provisional`，其余方向保持 accepted/pending 复用并整批先检查后写盘。同步两份 analyzer 的每轮独立 `mktemp -d` 结果目录与主 `SKILL.md` 调用契约。
3. **修 R1、引用持久化和旧包重绘**：`build_direction_pack` 从 `provisional_member_keys` 建成员并保存 `relevant_keys`；`cmd_stage2_finalize` 保存两类论文、校验拆分非空和最终指纹；`Stage2PackRefineContext`/`stage2_validation_material` 从规范 `papers` 及参考范围恢复标题许可；提升归属语义版本，阻断旧正式成员复用，确保成员变动时受管 Markdown 重绘；按第 3.4 节一起衔接 validator 生命周期、原事实校验与最终方向上下文、拆分/合并参考范围。
4. **修 R2 并同步调用说明**：更新 Stage 2 原始报告读取与行号定位，调整同仓 style-validator 的 Stage 2 位置要求及 Codex/OpenCode analyzer 交接说明；不改变 Stage 3 校验。
5. **测试工程师关口与实现**：依据第 5 节确认第一关必测清单、补齐第二关可执行方案；在本拉取请求分支提交受影响测试与产品实现，按规定在隔离环境执行并记录第三关结果。只核对该次变更影响到的既有行为。
6. **合并审核**：按 Merge Reviewer Rule 对“正式需求 → 已批准计划 → 本分支实现 → 生产调用路径 → 第三关结果”审核；`READY + COMPLETE` 后再由用户另行决定是否合并。此请求在实现、验证、审核完成前保持 `Draft`。所有后续实施继续提交到**同一个拉取请求分支**；不拆成另一个 PR，也不把计划正文散落在评论中。

## 7. 修订状态与未完成事项

- 执行方案 r3 在 `352426a129c5d0b374704f68e637d0ad3cf1a4c2` 已由 [2026-10-16 正式复审](https://github.com/ScholarWorkflow/professor-contact/pull/91#issuecomment-6218616598) 给出 `Plan conclusion: APPROVED`，取代 r2 的待修改结论。该外部记录只批准执行方案，不代表测试或合并通过；本轮不改第 2—4 节方案。
- 用户随后明确要求同步测试计划，当前唯一文件第 5 节为 `stage2-three-runner-defects-test-r5-2026-10-17`：test-r2 完成旧调用、结果夹具和断言迁移交接，test-r3 补齐第 5.2 节独立结果生成函数与其它直接调用文件的迁移说明，test-r4 由本地测试工程师落实测试实现并把真实选择器、Python 路径、临时目录与完整命令写入第 5.2 节，含 test-r3 点名的 `test_build_issue29_stage2_fixture.py` 漏项。测试资产在提交 `d027de0`；test-r5 补充 T5 缺来源用例应沿用完整有效结果、识别真实拒绝原因，并明确修复 `_fresh_stage2_env()` 的无效测试方法名；不新增用例、命令、证明材料或测试目标。未修改产品代码、教授业务数据或计划第 2—4 节方案，未执行任何正式用例或安装。
- 下一责任人为测试计划审核者、产品实现者与本地测试工程师：本轮第 5.2 节点明的 T4/T5 两处测试准备修正（提交 `0367c78`）与 test-r5 第二关审核的 5 项最小修正（提交 `c70bd09`，含第 5.2 节五条可直接复制的完整命令）均已完成；保留已通过的第一关，测试计划审核者复核第二关的直接受影响步骤（产品实现入库后再核实依赖实现的可执行性）；按第 2—4 节提交产品实现后，本地测试工程师按第 5.2 节核对 `validate_resolve_results` 相关单元测试的签名与断言（只修参数与原断言）并重新收集选择器，本地执行工程师按第 5.2 节命令记录第三关结果，之后单独进行合并审核。未受影响的执行方案批准不因测试文档更新自动作废。PR 保持 Draft，测试与合并状态为 **pending / NOT_READY**。
- **2026-10-17 本地执行交接**：产品实现 `810977a` 与受影响测试执行记录见第 5.2 节“当前交付状态”；T1—T5 共 60 个选择器在 `/tmp/pc91-tests.NArnigfE` 全部通过且退出码为 0。未新增测试目标、命令或证明材料，也未修改第 2—4 节方案。下一责任人：测试计划审核者复核第二关（选择器与命令均已实际执行），测试审核者按当前产品与执行记录完成第三关，之后按 Merge Reviewer Rule 进行合并审核；PR 继续保持 Draft。

