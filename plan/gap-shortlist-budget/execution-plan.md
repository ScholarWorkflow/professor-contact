# Stage 2 gap 短名单与时效预算分离

- Requirement revision: R1（2026-10-28 用户本轮确认，含论文询问阈值改为 20）
- Plan revision: EP2
- Target repository revision: `214dbef122d023c20db06fc49654daccc0411b10`
- Review status: EP2 APPROVED by independent reviewer; see review.md
- 唯一有效执行计划；审核结论只见本目录 review.md。

## 需求与非目标

用户要求修改 SHORTLIST_MAX / SHORTLIST_FLOOR 逻辑并走双计划普通审核；随后明确相关论文超过 20 篇才询问是否全部使用。删除无实际作用的 5 条下限；默认 gap 时效检查保留最多 10 条，`freshness_scope=full` 仍检查全部；最终 gap_shortlist 不再因数量截断。相关论文不超过 20 篇直接全部用于 gap/叙事后处理；超过 20 才询问全部或排序前 20。显式 max_relevant_papers、点名论文豁免、candidate union 的全文分析范围不变。

非目标：不改变排序、done_by_self 禁锚、引用/真实性校验、unknown 必须 unverified、Stage 3 同时消费 shortlist/excluded 的接口；不新增参数矩阵、模型评测、安装、浏览器或全仓回归；不自动合并或修改已有用户文件。

## 事实与决策

以下路径均相对目标版本的 `.apm/skills/professor-contact/`：

1. `scripts/contact_state.py` 定义 SHORTLIST_MAX=10、SHORTLIST_FLOOR=5；`scripts/_stage2_facts.py::shortlist_size` 对非负数量等价于 min(10,n)，并被 judge_set 和输出构建共同调用。因此删除 FLOOR，改为只表达默认时效预算的常量；judge_set 保留最多 10/full 语义。
2. `scripts/_stage2_render.py::build_direction_pack` 先将 done_by_self 放 blacklist，再把 anchorable 截断并将尾部写 low_rank excluded。取消这一数量截断，按原排序保留全部 anchorable；blacklist 不变，保留 gaps_excluded 字段及下游读取兼容。
3. `scripts/_stage2_preflight.py::cmd_stage2_plan` 超量 reason_code 只是 status=ok 下的提示，现名 shortlist_over_limit 会继续误指最终上限。保留 reason_code 取值兼容，但文案明确它仅表示默认时效预算外仍有候选，不是错误或强制询问。不得用它阻止输出。
4. 两个 `packages/professor-contact-{codex,opencode}/.apm/agents/professor-contact-analyzer.agent.md` 的 Step 5.2.4 是论文成本询问 owner；仅把 >10 / 前10 改为 >20 / 前20，明确 <=20 全纳入，保留显式范围与全文分析语义。不是把 gap 预算也改为20。
5. `_stage2_preflight.py::stage2_preflight_versions` 规定同输入输出语义变化必须升级 resolution_semantics_version；`_stage2_finalize.py::stage2_pack_requires_membership_rebuild` 与 finalize 已有旧语义重建路径，保留有效 narrative/freshness，不重新生成。升语义3→4并复用该路径；对于 refine 已清除 preflight 元数据的旧产物，以既有 low_rank 排除条目识别仍被数量截断的旧输出，进入相同重建路径，不将所有无元数据包一律当旧版。保留原验证失效与重新验收约定，不伪造 PASS；不改变 direction_fingerprint 触发无关模型重跑。
6. `_stage2_finalize.py::stage2_old_pack_gap_statuses` 当前只恢复 shortlist/excluded、遗漏 completed_gap_blacklist。此次触发旧包重建时必须一并恢复已有 done_by_self 记录（证据、候选论文、置信度、时间），否则会把已禁锚项变成 unknown。恢复时同时读取当前 provisional source 对应的已接受 split 子项（按 resolved_direction.provisional_direction_id 关联），包括其 shortlist/excluded/blacklist；仅接受 resolution_type=split_from 的有效关联；保留父项记录优先级，子项只补缺失 gap_id，不静默覆盖冲突父项，不跨无关方向借用状态。重建后沿用现有 split 物化流程，不丢失已移至子项的已核状态。修正位于同一重建 owner，不增加新推断或重跑模型。
7. `_stage3_commands.py::cmd_stage3_plan` 同时传入 gap_shortlist 与 gaps_excluded，`_direction_inputs.py` 同时建引用索引。继续保持该兼容面；取消截断使 shortlisted 标记变化是本次已批准行为，不把未知时效改成已核实。

## 实施顺序与 owner

执行计划获独立批准后，由产品实现者修改 runner 的预算常量/注入参数、judge_set、build_direction_pack，以及旧语义输出重建；同步共享 SKILL 和两种正式 analyzer 的当前约定，移除“5–10”以及把 shortlist_over_limit 写成错误的误导。

测试实现者依据 TP2 在现有 unittest / fixture 上补受影响断言；测试步骤在执行前经第二关确认。执行者只跑确认的目标，结果保留正式尝试。独立审核者复核结果和最终 diff。普通提交到独立分支、新 Draft PR；提交前刷新远端，expected_sha 保护，不 force，不覆盖并发修改。

## 影响与兼容

- intended_change / approved_behavior_change：所有非 done_by_self gap 按原排序进入最终 shortlist；默认时效预算独立；论文询问门槛20。授权为用户本轮明确修改要求。
- preserved_behavior：身份、排序、source evidence、blacklist、已缓存时效事实、显式max参数、点名豁免、全文分析范围、Stage3未知标记、既有文件保护。
- prohibited_side_effect：不凑候选、不自动扩大 freshness 到 full、不修改历史批准或用户成品、不因文档SHA重测、不把未执行写PASS。
- compatibility：保留 freshness_scope=shortlist/full、gaps_excluded 及 reason_code 字符串；旧 truncated 包在下一次正式 Stage2 重建时采用新语义，复用有效模型结果；新结果必须经过原验证流程。
- 风险/代表性反例：>10合格gap不应消失；done_by_self即使取消数量限制也不得恢复为锚点；meta被refine清除的旧截断包不得永久复用；<=20论文不可因旧文案反复询问；用户显式max仍优先。
- 不涉及存储schema迁移、并发新机制、外部服务或新资源生命周期；Critical assumptions / unresolved impacts: N/A（以上由当前源码路径直接支撑，独立复核须确认）。

## 替代方向

仅增大 SHORTLIST_MAX 会同时扩大时效工作且仍保留任意业务上限，不满足已确认目的；新增独立可配置最终上限增加不必要选项。本方案仅解除最终截断，保留既有预算控制。

## 审核与证据

按 PROJECT_CONSENSUS、Plan Reviewer Rule、Test Engineer Rule 当前原文。规则链接分别为 https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d 、https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c 、https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253 。本计划不自授 APPROVED；结果与下一负责人见 review.md / test-execution.md。
