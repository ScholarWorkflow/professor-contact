# 独立双计划审核

Reviewer: independent_plan_review（未参与候选编写）
Date: 2026-10-27
Requirement revision: R1
Plan revision: EP1.0
Test plan revision: TP1.0
Target repository: ScholarWorkflow/professor-contact
Target repository revision: a67ca3b630e00941d8c72ad7328a8f7796bda77b

依据：PROJECT_CONSENSUS、Plan Reviewer Rule、Test Engineer Rule 的当前正文及 R1；已只读核对 renderer、validation/refine、source-evidence-repair、style-validator 与相关调用说明。没有运行测试或修改产品。

## 执行计划
P1 Requirement & Reality Grounding: PASS
P2 Solution Validity & Ownership: NEEDS_MODIFICATION
P3 Impact, Safety & Counterexample: NEEDS_MODIFICATION
P4 Executability: NEEDS_MODIFICATION
Gate review completeness: COMPLETE
Critical assumptions: 无外部事实假设；以下为待冻结设计决定。
Unresolved impacts: 旧 terminal 校验与新扫描范围兼容、非文风结构责任的实际入口。
Approved behavior changes: R1 已授权仅生成解释进入文风修订面、缺解释可补及跨标签正确归属；未授权改变黑词规则、事实或 Stage3/5。
Reused prior Plan Gate PASS: N/A

### 必须修订（一次完整审核）
1. **P3/P4，冻结 scope 与旧记录兼容。** EP §冻结方案 3 仅称“带 scope 的报告”绑定 render；§6 仅讨论旧报告与新稿绑定不符。现有 finalize 对仅 metadata/ownership 更新可能保留原正文和终态，而 validation 以现有轮次限制拒绝再记录。这样同一正文上旧误扫的 terminal blocker 未必能正常退出。最小修正：明确新报告是否必须带 scope 版本/绑定、无 scope 的当前报告如何处理，以及正文不变但范围改变时旧记录的受支持刷新/重检路径；不得将旧 fail 静默改 pass，也不得仍锁死在不可修旧终态。负责人：计划作者/Stage2 runner owner。
2. **P2/P4，冻结真实结构问题的实际责任入口。** EP §冻结方案 2 仅提供生成片段，而 §3/TP2 又保留 renderer/source 结构问题交接。规则8的表格标识泄漏和9的表格结构依赖不在片段内的内容；当前计划没有说明谁观察/接收这些问题、如何返回明确 owner。最小修正：明确生产路径上的既有或最小新增检测/接收方式、结果交接及不能授权源改写的边界，不建设通用框架。负责人：计划作者/renderer owner。

可选 summary 槽位不得把缺 summary 本身升级为 blocking；建议交接明确合法 refine 中可补既有 gap 的 summary，不借不存在的摘要内容构造违规。

Plan conclusion: NEEDS_MODIFICATION

## 测试设计 / Gate1
Test design: APPROVED
Gate1 必测清单: PASS
Review completeness: COMPLETE
理由：TP1–5覆盖已批准扫描、错误到修订、缺文案、绑定兼容及生产接线；无真实模型、安装、全仓回归或新判定器要求。上述 EP 修订仅细化这些已列目标，不增加测试义务；若改变目标，按实际影响复核。
Gate2: NOT_REVIEWED（实现后需补准确命令/所选现有方法与输出位置）
Gate3: NOT_EXECUTED
下一步：作者更新唯一 EP 后只复核上述两点及直接连带影响；准确 recipe 另交 Gate2，不因文档 SHA 变化重跑或重审未受影响范围。

## EP1.1 定向复核

Date: 2026-10-27
Plan revision: EP1.1
Requirement revision: R1（未变）
Target repository revision: a67ca3b630e00941d8c72ad7328a8f7796bda77b（未变）

复核范围：首审两项及其对扫描、报告接收、旧状态生命周期和结构 owner 的直接影响。未重新开放未受影响设计或增加测试义务。

- scope 绑定已改为全部新 analysis 报告必需；record 按当前 ownership 重算，不接受仅旧 body SHA 的无 scope 报告。旧 scope-less validator 在正常范围迁移中保留为历史、撤下当前资格，进入未校验状态而不是 pass；同版刷新不能重置轮次或续轮授权。等价 body 更新 ownership 的处理已明确，关闭首项。
- 文风与结构的读取面已分开：生成片段用于文风，原稿仅供既有规则8/9；接收端也仅容许这两条结构规则定位 scope 外，明确 generator/source 交接，不授予来源改写。没有新扫描框架或放宽判定标准，关闭第二项。
- summary 缺失不新增必填或失败标准，explanation 保持既有必填；缺字段补写限合法现有 gap，不扩来源字段。

P1 Requirement & Reality Grounding: PASS（复用 EP1.0 的需求及源码依据；本次仅冻结策略）
P2 Solution Validity & Ownership: PASS
P3 Impact, Safety & Counterexample: PASS
P4 Executability: PASS
Gate review completeness: COMPLETE
Critical assumptions: N/A
Unresolved impacts: N/A
Approved behavior changes: R1；旧范围迁移只撤下旧校验资格，保留历史并要求重新校验，不赋予通过。
Required modifications: N/A
Plan conclusion: APPROVED

TP1.0 Test design APPROVED / Gate1 PASS 继续有效：EP1.1细化的scope绑定、旧记录迁移及结构责任均在既有目标1/2/4/5内。Gate2仍待准确recipe审核；Gate3仍未执行。本批准只表示可实施，不是实现正确、测试通过或Merge READY。

## TP1.1 Gate2 首审

Date: 2026-10-27
Test plan revision: TP1.1
Scope: 仅执行步骤及选定测试与生产契约的接线；EP1.1/Gate1 不重审。
Review completeness: COMPLETE
Gate2: NEEDS_MODIFICATION

唯一发现的问题：recipe 选中的 `test_human_validation_continuation.Stage2ContinuationTests.test_c_a_extended_rounds_accumulate_and_keep_old_failures` 使用 `Stage2Fixture.write_report` 自行构造旧格式无 `analysis_scope` 报告。新接收契约要求 scope，当前步骤会在首轮协议错误处停止，不能检查声明的续轮保持目标。最小修正：Stage2Fixture 复用已经更新的 `stage2_style_validation_report` 准备绑定，保持原 issue/verdict 和 Stage3 helper 不变。属于测试实现接线缺口，不是新增测试要求。

其余检查：选择器对应当前方法存在，已查看直接导入的现有 helper；测试只运行 Stage2 范围内选定方法，无 discover 全仓收集；合成临时目录与独立 `/tmp` 日志、失败保留、无自动重试约定足够。准确运行时可用性仍由 recipe 指定最小预检确认。未执行任何测试，未作 Gate3 结果判断。

## TP1.1 Gate2 定向复核

Date: 2026-10-27
Gate2: PASS
Review completeness: COMPLETE

已只读确认 Stage2Fixture.write_report 改为复用现有 `stage2_style_validation_report`，保持原 issues/verdict，Stage3 helper 未改；关闭唯一接线缺口。TP1.1 的准确命令、运行准备、输出与失败处理可用于当前候选执行。新增测试模块登记到现有 shard4 仅为既有 CI 收集接线，不增加本 recipe 的测试义务；CI 实际结果另按事实记录。没有执行测试；Gate3 仍未执行，不能据此称产品 PASS。

## TP1.1 首次失败后的定向复验 Gate2

Date: 2026-10-27
Reviewer: independent_plan_review
Gate2: PASS
Review completeness: COMPLETE

已查看首轮日志 `/tmp/contact-style-scope.Cp156o/unittest.log`，21项中18通过、3失败；不覆盖或抹去首轮结果。三处测试修正均保留原业务断言：
- 中译标签 quote 改为唯一 `- 中译：`，避免合成行内重复字符串先触发歧义，仍要求 scope 拒收及零写入。
- fixed-evidence D 的第二套 round2 与第一套一致使用 C9 模拟结构报告，仍验证 generator owner、终态、轮次及不可叙事改写。
- 旧版迁移 fixture 在改旧 display/ownership 后重绑旧 validator.pack_sha256，模拟自洽的旧快照。fingerprint 包含 cache，首轮 fixture 未重绑导致产品正确拒收；不应为此放宽产品 stale-binding 保护。迁移正文/cache/历史只存一次等预期保持。

批准使用 TP1.1 相同隔离、日志和失败保存方式，仅将 unittest 选择器缩为以下三个受影响方法：
`test_stage2_style_repair_scope.Stage2StyleRepairScopeTests.test_old_scope_less_record_is_archived_once_on_normal_upgrade`、
`test_stage2_style_repair_scope.Stage2StyleRepairScopeTests.test_source_and_label_style_reports_are_rejected_without_writes`、
`test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_d_narrative_two_rounds_and_fixed_stop`。
其余首轮通过项无需因上述 fixture 修正重跑。两个额外现有 helper（test_stage2_preflight.record_validation、test_stage2_resolved_direction_downstream_regressions._write_blocking_report）已静态核实复用同一 scope helper，原业务断言未变；此接口接线不扩本次手动必测范围。生产 caller 补齐仍属既有目标5，由独立合并审核核对。未执行复验，不作 Gate3 通过结论。

## TP1.1 迁移末尾断言修正后的单项复验 Gate2

Date: 2026-10-27
Reviewer: independent_plan_review
Gate2: PASS
Review completeness: COMPLETE

定向日志 `/tmp/contact-style-scope.OZNIRF/unittest.log` 三项中两项通过；旧范围迁移已成功，唯一失败在后续同版刷新要求整个 validator 字节等值的断言。已核 finalize 的既有 carried-validator 路径会为新 pack metadata 重算 pack_sha256，而不重置周期。修正先验证 current.validator.pack_sha256 等于当前 pack 的真实 fingerprint，再只用新 binding 比较其余完整 validator 与原 active 相同，仍要求 history 长度为1。这样保留轮次、scope、结果及授权不变等保护，不要求合法新 metadata 的摘要不变；无需改产品。

批准相同隔离 recipe 仅复验 `test_stage2_style_repair_scope.Stage2StyleRepairScopeTests.test_old_scope_less_record_is_archived_once_on_normal_upgrade`，其余结果复用。首轮及三项复验失败日志均须保留。本记录仅批准步骤，未执行或授予 Gate3。

## TP1.1 Gate3 独立结果审核

Date: 2026-10-27
Reviewer: independent_plan_review（未编写产品或测试，未执行正式测试）
Requirement: R1；Plan: EP1.1；Test plan: TP1.1
Gate3: PASS
Review completeness: COMPLETE

已按批准方法核对 test-execution.md 与三次完整 unittest 日志：
- `/tmp/contact-style-scope.Cp156o/unittest.log`：21项，18通过、3失败。
- `/tmp/contact-style-scope.OZNIRF/unittest.log`：仅3项复验，2通过、1失败。
- `/tmp/contact-style-scope.bHDzRu/unittest.log`：仅迁移方法复验，1通过（4.984s）。

有效覆盖是18+2+1=原定21项，并非单次全绿。失败原因、两次测试fixture/断言修正以及对应Gate2复核均已保留；没有调整产品阈值、绑定保护或来源事实以求通过。目标1–4均有适用成功结果：生成范围与排除源字段、混合归属与三字段授权、缺文案补写及来源保持、旧范围归档和同版周期保持、现有续轮行为。

目标5复用独立 ordinary merge reviewer 对最终 caller/validator/SKILL diff 的只读核对结论：两 runtime analyzer 的 prepare→analysis_scope→原稿结构检查→record 指示、Return 绑定示例、旧范围一次归档与同版刷新边界已一致，所报源码接线阻断全部关闭。此项为源码观察，不冒称真实模型调用验证。

未完成必测项：无。已知未解决测试问题：无。外部服务、真实模型、用户Mac运行、全仓测试不在获批必测范围，也未执行。本结论只批准本议题既定测试结果；不代替独立合并审核，不意味着已合并。

目标5审核定位补充（independent_merge_review 直接回执）：Codex analyzer `:610–646`、OpenCode analyzer `:613–654`，`.apm/skills/professor-contact/SKILL.md:250–258`，以及 style-validator 的 Input/0/Return sample；详见同目录 merge-review.md 的源码阻断关闭节。
