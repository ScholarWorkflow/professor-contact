# Stage 2 文风检查与修订范围闭环

Requirement revision: R1 (2026-10-27，用户要求先明确扫描对象、报错后修改入口，并授权云端双计划、完整实现及新 PR 普通审核)。
Plan revision: EP1.1
Target baseline: a67ca3b630e00941d8c72ad7328a8f7796bda77b
Independent review record: review.md（EP1.1 已批准；TP1.1 Gate1–3结论见该记录）

## 需求、范围与非目标
仅修 Stage 2 analysis 的文风扫描到修订闭环。模型生成的 positioning.text/concrete_object/input_example/output_example、gap_notes.summary/explanation，以及 freshness model_evidence/completed_part/remaining_gap 应继续检查并能通过现有入口修订。原始引文、忠实中译、真实论文标题、固定标签、来源与状态不成为文风修改对象。缺 summary 时可以补写 summary；缺 explanation 时必须能定位并补写。不得改变任何来源事实、论文引用身份、freshness 判定、用户笔记、红线、默认轮数及人工追加轮数规则。不得修改 Stage 3/5、PR149/150、黑词规则或降低文风阈值；不新增通用框架。

## 依据与因果
- `_stage2_render.py:750–984` 将可改解释与 source/generator 片段混排；`citation_segments` 还把展开标题与 evidence 归到同一 source 字段。因此仅放开 source 字段会把事实误当措辞。
- `_stage2_validation.py:402–529` 按引用覆盖片段登记全部 owner；`846–862` 任一 fixed blocker 停止全部 narrative job。跨标签引用会附带 label owner，缺省 summary 被当 source。
- `_stage2_render.py:208–228,854–888` 允许空 gap_notes 并不渲染空 explanation；validator 要求引用现存原文，因此缺失解释没有可修定位。
- `_stage2_evidence_repair.py:28–40` 已有三个 freshness 解释字段的受控修复；保留它而不扩大事实写权限。
这些为基线源码事实；正式范围来自 R1，而不是历史 fixed-card 设计。历史“不屏蔽整卡”继续保持：卡内生成解释仍检查。

## 冻结方案与职责
1. renderer 继续产生完整人读稿及既有 ownership。将真实引用标题与模型措辞分开标记；P/L/G 引用和标签不是可改文风。freshness 的非引用解释仍归现有三字段 source repair。
2. 复用 ownership 增加轻量 `stage2-prepare-validation --professor-dir`：核对当前受管稿绑定，输出仅含可修生成片段的 analysis scope（原文件、render SHA、片段文本、原物理行号与字段）。scope 固定为 schema=1、原 file、artifact=analysis、render_sha256、scope_sha256 及 fragments（原行/字符范围/text/field/direction/gap、缺失与必填标记）；scope_sha256 对除自身外的完整 scope 计算。没有复制整个输入包或源 sidecar，不改变业务文件。生产 caller 每轮先 prepare，再把完整 scope 交 validator；analysis validator 只检查 scope 文本，Stage 3 原输入不变。
3. 普通报告继续使用原文件、原物理行号和逐字 quote；所有新 analysis 报告必须带 analysis_scope 的 schema/render_sha256/scope_sha256 三项；record 从当前 ownership 重算核对，缺失或不符零写拒绝。record 仍核对原稿，不通过删除问题把 fail 改 pass。纯来源/标签等不在文风面的报告返回明确 scope 错误要求重新校验，零业务写入；跨标签和可改正文的引文仅按可改正文路由，不附带 label blocker。结构检查与文风面分离：validator 仅为原规则8/9读取原稿做 key 泄漏/表格纪律检查，报告仍原行原引文，不能把其它文风规则用于该原稿。record 仅对规则8/9接受 scope 外结构 finding；固定表结构归 generator、固定来源标识问题归 source，返回 needs_owner_fix，不授权叙事改事实。不会新增结构扫描器或改变 key 判断标准。
4. 缺失 explanation 时 renderer 增加清楚的待补槽位，归 narrative explanation；summary 的来源摘录保留但不扫描，另提供可补 summary 的定位槽位，不把 summary 缺失本身升级为必须失败。prepare 标明两类槽位及其不同要求，validator 仅按已有 explanation 必填要求报告缺失，必要 summary 补写可通过对应合法槽位定位。refine 允许为已存在 gap 新增 gap_notes，仍不得改 gap 源字段。
5. freshness 三字段继续原 repair 授权、旧值/摘要并发校验、refresh 后重校验；不会因标签连带而添加不可修 owner。既有轮次/终态/人工续轮及真实一致性校验保持。
6. 调整 display/ownership 版本使旧布局经现有 preflight→finalize 正常刷新；不手改现有受管产物、不迁移源 sidecar。新版记录要求 scope 绑定，旧报告即使 body SHA 相同也不能重新录用。正常刷新发现旧 scope-less validator 时，将其保留为旧范围历史而从当前 validator 撤下，进入未校验的新范围周期，绝不标 pass；这一迁移仅在 scope 版本升级发生一次，同版刷新不得清空或重置轮次/人工续轮授权。finalize 在 body 等价时也须更新旧 ownership，不复制旧版本 map。

## 替代方案与取舍
只改 prompt 仍可能把不可改文本送进检查并产生死路；扩大 source 白名单破坏证据责任；record 静默删除误报会伪造通过。采用现有 ownership 的小范围 scope 与可补槽位，增加一个只读准备入口，保留原报告定位/修复命令，避免第二套渲染或通用审查框架。

## 影响、不变量与实施顺序
intended_change/approved_behavior_change：扫描输入只含可修解释、缺文本可补、跨标签不产生虚假 generator blocker。preserved_behavior：完整人读来源、引用身份、事实/状态验证、受管稿保护、三字段窄修、轮次及 Stage3/5。prohibited_side_effect：改 sidecar、标题、状态、用户数据、全仓迁移或自动合并。
按 renderer ownership/槽位 → prepare/record/refine 接线 → caller/validator 文档 → 定向测试顺序实施。并发和陈旧报告仍依赖既有 render/pack 摘要保护。来源全误报不能变 pass；真正生成文本失败不能被标签/引用遮掉；缺解释不能被引用不存在文本卡死。无关键未验证假设。审核批准前不实施核心代码，测试 recipe 经 Gate2 后执行。

## EP1.1 修订影响
独立首审要求明确无 scope 报告和同正文旧终态处理，以及结构检查责任入口。本版冻结这些策略；P1–P4须定向复核，TP目标不扩展。summary仍非新增必填；只允许合法既有gap下补写。
