# 独立计划审核记录

- 日期：2026-10-27；Reviewer：独立子代理 `review_direction_materials`，未参与计划编写。
- Requirement R1；当前 EP1.1 / TP1.1；Target baseline `b67dd3ca4d29dfc78f57988564b219c71b582674`。
- 完整首审读取执行/测试审核技能、Notion规则正文、全部候选及固定源码；定向复审只看修正及直接影响。全程只读，未执行测试。
- 作者仅整理独立reviewer真实结论，不自授批准。当前计划正文保留 Proposed review status: pending，正式状态以本记录为准。

## EP1 / TP1 首次完整审核

P1 PASS；P2/P3/P4 NEEDS_MODIFICATION；Gate review completeness: COMPLETE；Plan conclusion: NEEDS_MODIFICATION。TP1设计及Gate1 NEEDS_MODIFICATION。
- B1：live素材与邮件包快照一致不足以阻止“回答A生成→修改为B→Stage4重冻B→提交旧结果”被贴上新source_hash。须将新素材模型结果绑定生成时切片指纹，并在plan-with-result/finalize核对。
- B2：不能把“不阻塞未受影响邮件”扩为Stage5同批partial提交；应沿用既有--email-id与批次失败语义。
- TP T4在既有更新序列补重冻后旧指纹结果拒绝、新结果成功，无新增编号/矩阵/模型运行。

## EP1.1 / TP1.1 定向复审

P1 Requirement & Reality Grounding: PASS（复用EP1，需求和关键事实未变）  
P2 Solution Validity & Ownership: PASS  
P3 Impact, Safety & Counterexample: PASS  
P4 Executability: PASS  
Gate review completeness: COMPLETE  
Critical assumptions: N/A  
Unresolved critical impacts: N/A  
Required modifications: N/A  
Plan conclusion: APPROVED

B1已关闭：plan提供direction_materials_fingerprint，模型结果原样携带，plan-with-result/finalize核当前冻结切片；仅新素材合同适用，不扩历史来源认证。B2已关闭：未受影响邮件可用--email-id单独处理，同请求有过期邮件仍按旧批次失败/零写入，不新增partial。
获批行为变化为R1授权的缺素材补问、独立方向素材、原回答冻结、真实来源及相关指纹；profile/Stage3、跨教授边界不变。

Test design: APPROVED。第一关口（必测清单）：通过。T4直接覆盖B1，T1–T6其余目标/检查/复用边界不变，不额外强制模型eval或全流程回归。
第二关口：待实现及精确recipe后审核。第三关口：未执行。没有新能力测试PASS，没有实现正确性或合并许可。

## 最终文件与基线影响

- EP1.1 SHA256: `438431e85ee1e54343d9f2bc557f4ef8bb69209d5c1d2956a857461ba284a35a`。
- TP1.1 SHA256: `037732673b925b13cd8d0d0255220223a851e539e46f10df0da9eedca94d8506`。
- 首次事实核对为81bd256；发布前main合并PR146到b67dd3c。该差异为Stage2/3追加校验及历史保存，Stage4/5与本功能依赖合同未变；独立reviewer已核相关差异及当前文档：方向身份、Stage4/5输入/来源合同未变；笔误和版本指针更正无语义影响。复用EP1.1 P1–P4 PASS/APPROVED、TP1.1设计批准/Gate1通过；Gate2待recipe、Gate3未执行，不新增测试或重审范围。

## 下一步

产品实现负责人按EP1.1实施；本地测试工程师仅在TP1.1内补齐真实入口、合成输入准备、精确selector及输出位置，再由reviewer确认Gate2、执行人员正式运行、reviewer确认Gate3。本次交付止于docs-only draft PR，不实施产品、不改测试代码、不运行正式测试、不合并。
