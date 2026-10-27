# 普通合并独立审核

Reviewer: independent_merge_review（未参与计划、产品或测试实现；只读审核，未执行测试）
Requirement revision: R1
Target repository: ScholarWorkflow/professor-contact
Base SHA: a67ca3b630e00941d8c72ad7328a8f7796bda77b
Head SHA: 尚未发布；本次云端候选工作区，发布后按实际内容差异更新
Canonical Plan revision: EP1.1
Test Engineer Gate 3: pending

## 首轮源码审核（2026-10-27）

已核对本次 renderer、prepare/report/refine、finalize 兼容处理、SKILL、validator、测试修改及两运行时正式 analyzer 的调用段。TP目标5在本轮以源码检查，不新增模型运行或测试义务。

M1 Authority & Baseline: NEEDS_MODIFICATION（待发布 Head 与 Gate3 记录，不代表业务失败）
M2 Implementation Conformance: NEEDS_MODIFICATION
M3 Scope, Regression & Merge Readiness: NEEDS_MODIFICATION（Gate3 待结果）
Review completeness: COMPLETE（本轮可独立判断的源码范围；最终版本及结果待实际形成）
Merge conclusion: NOT_READY

### 已确认唯一源码阻断

**IMPLEMENTATION_DEFECT / M2 / TP目标5**：正式 Stage2 caller 位于本仓 `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md:610–638` 和 OpenCode 对应文件 `:613–646`，不是根 `.apm/agents/`。Codex 现文明确仅传分析文件路径和 `artifact: analysis`；OpenCode Task 模板也是旧输入。当前候选 validator 已要求 `analysis_scope` 且缺失返回 error，runner 也拒绝无绑定报告。只更新共享 SKILL 未消除正式 caller 的相反限制，正常入口不能完成校验。

最小修正：两个 Step6.5 每轮在委派前调用当前 runner 的 `stage2-prepare-validation`，向既有精确 named validator 原样传完整 scope；修订后下一轮重新 prepare，并保留原 runtime 委派、原文保存和 record 顺序。仅此两处生产接线及直接连带描述，无需改 professor-research、扩真实模型测试或改变计划目标。负责人：产品实现者。

### 其余已完成检查

- `style_checkable` 从 renderer 当前所有权生成：六类 narrative 与 evidence/blacklist_evidence（同一 model_evidence 来源）、completed_part、remaining_gap 保留；P/L/G 展开引用、源 quote/中译、标题、标签与状态不成为文风修订权限。
- prepare 是当前受管稿的只读投影，保留原物理行号与片段范围；record 检查当前 render/scope 绑定，纯范围外文风报告零写拒收，不把错误报告降成 pass。混合引文只路由实际可检查文字；规则8/9的纯固定结构问题仍保留 owner。
- 缺 summary 保留来源摘录另给可选槽位；explanation 保留必填要求且有可修槽位。现有 refine 校验合法 gap 身份后仅替换 narrative；原始来源和 freshness 状态仍保持。
- 三字段 source repair 本身未扩大权限；固定结构问题不能借修文风改事实。未改变黑词阈值、Stage3/5、默认两轮或人工续轮命令。
- display/ownership 升级只经正常 acceptance；旧 scope-less cycle 归档而不是 pass。同版同正文保留 validator/轮次；新 ownership 不复制旧版本。无全仓自动迁移。
- 测试 helper scope 接线、目标测试与既有 CI shard 登记均在本次契约直接影响范围；具体实际执行有效性交 Gate3，不由本审核自行声明测试 PASS。

Re-review routes: 仅复核上述两个 caller 接线、发布差异和 Gate3 结果；其余结论在内容未受影响时复用。

直接接口影响补充：`test_stage2_preflight.py:277 record_validation` 与 `test_stage2_resolved_direction_downstream_regressions.py:154 _write_blocking_report` 两个既有 fixture 独立构造无 scope 的 analysis 报告，后续期望成功登记。需与 common helper 一样接入当前 scope，保持原测试业务和断言。这是新增必需报告字段造成的既有测试接线影响，不新增业务测试或全仓手动回归义务；由实现者修正后随现有 CI 验证。

## 定向复核进展

两个正式 analyzer 的 Step6.5 已加入每轮 prepare、完整 scope 输入及原报告绑定，Codex/OpenCode 原生委派保持；validator 返回示例也明确 analysis_scope 必需，Stage3 不增加该字段。两处既有测试独立报告已复用 common scope helper且原断言保留。上述主接线缺口已修。

同两 caller 尾部关于“只有源/生成逻辑真修才失效、仅展示/map更新保留轮次”的旧无例外表述仍需注明本次旧 scope-less 一次升级例外，避免与共享 SKILL 和实现矛盾；这是本项直接连带说明，修复不要求重跑测试。

首轮迁移测试失败所涉 fixture 人工更改 ownership 但未更新既有 validator pack 绑定；合法旧快照应重绑。定向复验后的终点比较亦应允许正常 acceptance 重算 pack_sha256，同时保留其余 validator 字段并断言新绑定真实对应当前 pack。此修正不改变产品失败保护或验收目标；正式结果结论待 Gate3。

## 源码阻断关闭

两 runtime caller 的尾部生命周期说明现已明确旧 scope-less 一次迁移例外，同版本 metadata 保留行为不变。每轮 prepare → 完整 scope 原样交 validator → 原文保存 → record → 仅合法 refine/三字段 repair → 重新 prepare 的正式生产指示已闭合；TP目标5源码观察通过。两处 fixture 接线修正没有改变原业务断言。产品未因测试失败放宽任何绑定或事实保护。

M2 Implementation Conformance: PASS。首轮已确认源码阻断全部关闭；最终 M1/M3 仍等待真实发布 Head 和独立 Gate3 结论。未新增合并前测试要求。
