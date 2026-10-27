# PR148：自然首句与三部分兴趣段执行计划

- Plan revision: EP1（2026-10-27，本轮补齐并审核，不倒签实施前批准）。
- Requirement revision: 用户 2026-10-27 确认自然首句、删除第四句；12:51 授权精简双计划及普通审核。
- Repository: ScholarWorkflow/professor-contact；PR: https://github.com/ScholarWorkflow/professor-contact/pull/148
- Base: `901fb109701bea61a62239f95c9da865fafb1e4e`；已实现产品版本: `4ea37fa6cb09b5a5bd4df8925a438d98a5f96d72`。
- Proposed review status: pending；实际结论只见 [review.md](review.md)。本目录是本功能唯一完整计划；旧 helper 搬移计划仅为历史背景，不恢复其 CLOSING_RE/四项不变要求，也不重审旧功能。

## 需求与边界

1. 首句从普通发信人的真实接触、有限认识与自然好奇出发。不把论文研究问题白话化后冒充个人兴趣；不固定身份、自定位或「私は」开头，也不固定“听过但没用过”。没有依据不声称听过、用过、读懂，不编具体经历、应用名称、长期兴趣或研究能力。日语简洁礼貌，保持禁恭维及真实背景约束。
2. 删除固定第四句，兴趣段结果改为三个非空字符串，source_map 覆盖①②③及 future。不是仅隐藏渲染文本。
3. 第二、第三部分及未来志向的内容规则不变；兴趣段总长180软上限、200硬上限不变。用户模板、已生成邮件、choices、Stage2–4、联系方式、Nix/安装、外部服务与安全配置不改。

## 原因、owner 与具体修改

| 决定 | 目标版本事实 / 修改点 | 行为与依据 |
| --- | --- | --- |
| 在生成入口传递自然首句规则 | `_stage5_commands.py:125–153` 的 result_schema/model_input.rules；SKILL 与 generator 引用的 `docs/stage5-legacy-contract.md` | 改①引导，而非用 validator 新建文风判定器；profile/笔记/补充仍是事实来源 |
| 整体采用三部分合同 | `_stage5_email.py:112–180` 验证长度与source_map；`contact_state.py` 工厂注入 | 四项改三项，移除固定④正则及注入，拒绝遗留④映射；不修改其他真实性/来源限制 |
| 保持正式路径一致 | `stage5_immutable.py stage5-plan/stage5-finalize` → runner → `_stage5_commands` / `_stage5_email` | 计划输出、校验、确定性组装与来源表一致；同步generator/validator说明、SKILL、工作流图及共享测试夹具 |

上述源码均以产品版本为准：[scripts](https://github.com/ScholarWorkflow/professor-contact/tree/4ea37fa6cb09b5a5bd4df8925a438d98a5f96d72/.apm/skills/professor-contact/scripts)。Owner 为 professor-contact 的 Stage5 producer，不在消费项目、模板、测试框架中补偿。

替代方案：只隐藏第四句会保留四项生成及来源要求，不能真正删除用户不需要的内容；自动截断旧结果会静默改写模型产物。采用显式三项并拒绝旧结果，接口变化明确且可定向检查。

## 兼容、失败与不变量

- 旧四项模型JSON须按新 stage5-plan 重新生成；不自动截断，不伪装旧结果仍符合新合同。保留 schema=1，数量不符给明确错误，不另造迁移框架。
- 三项结果若仍有④source_map也拒绝。其他来源、gap status、论文题名、用户选择和模板保护保持现有行为。
- 无效结果在写出前失败，已有md/txt/状态不重写；合法结果仍经既有 immutable finalize 路径。现有邮件不会因升级被批量改写。
- 不保证规则更新后每封模型输出都自然；真实模型效果未测，不作为新增验收任务。

## 当前状态与收敛步骤

1. 产品改动已在上述版本完成：10文件94行新增/53行删除。本轮只补本目录文档并修PR正文“≤180警告”的笔误（应为>180警告、>200拒绝），不再改产品或测试。
2. 由未编写候选的reviewer核EP1与TP1、实际入口及兼容策略，记录本轮日期与真实结论；不倒签历史批准。
3. 按 [test-plan.md](test-plan.md) 整理已有定向检查及固定SHA CI；独立确认复用有效性。文档SHA变化不自动重跑；后续实质代码变化才分析受影响目标。
4. 正常expected_sha提交文档并读回；完成普通合并审核，未满足门槛如实pending。作者不自授APPROVED，不自动合并。
