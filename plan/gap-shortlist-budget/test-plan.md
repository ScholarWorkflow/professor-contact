# Stage 2 shortlist 预算分离测试计划

- Requirement R1 / EP2 / Test plan TP2
- 基线：214dbef122d023c20db06fc49654daccc0411b10；实际产品/测试版本执行时记录。
- Review status: TP2 design / Gate 1 approved independently; Gate 2 approved independently (Recipe R2). 见 review.md；未执行不写 PASS。

## 必测清单（验收上限）

|项|目标、输入|预期|唯一检查方式|
|---|---|---|---|
|T1|同一方向>10个gap，含done_by_self；默认预算及full|默认只为前10安排时效，full全部；最终保留全部非done_by_self，原排序不变；未判断为unknown/not_judged，黑名单仍禁锚|现有unittest/合成Stage2 fixture，经plan/finalize读JSON字段断言；同一测试内覆盖默认/full|
|T2|旧语义截断输出，包括refine清空preflight meta情况与已有done_by_self；新语义已有包|旧截断包在正式Stage2重建保留有效narrative/freshness和黑名单并恢复所有合格gap；新包无额外反复重建；少于5不凑数|沿现有old-semantics重建检查入口，以同组现有fixture断言重建结果与复用结果|
|T3|当前共享SKILL及Codex/OpenCode analyzer正式规则|论文<=20全部、>20询问全量/前20；显式max和点名豁免不变；candidateunion全文分析不截；gap默认10/full与最终无限额区分清楚|人工一次阅读修改后的相关段落及完整diff；不建关键词判定器、不调用真实模型|

本次不做安装/Nix/APM/业务整仓回归、外部服务、真实模型风格评测、任意边界组合或过程认证。已有Stage3引用未知保护实现不改，由独立源码审核确认未改变；不重复建立Stage3测试层。

## Recipe R2（第二关已确认）

沿用既有 fixture / 标准 unittest；无新依赖。工作目录 `.apm/skills/professor-contact/tests`；fixture 使用 TemporaryDirectory 与虚构资料，不触及真实用户状态。执行下列一次目标命令，标准输出归档至仓库外 `/tmp/contact-gap-shortlist-tests/attempt-1.log`（后续尝试另号保存）。

```sh
python -B -m unittest -v \
  test_contact_state.TestRunnerBasics.test_01_freshness_budget_does_not_cap_final_shortlist \
  test_resolved_direction_preflight_integration.TestSemanticsVersionBump.test_old_semantics_pack_cannot_reuse_all_and_re_arms_after_one_run \
  test_resolved_direction_preflight_integration.TestSemanticsVersionBump.test_missing_meta_rebuilds_only_legacy_low_rank_projection \
  test_resolved_direction_preflight_integration.TestResolvedSetReuse.test_old_semantics_rebuild_preserves_split_child_blacklist \
  test_stage1_stage2_contract.Stage2ScopeContractTests.test_analyzer_cost_gate_discloses_untruncated_full_analysis_cost \
  test_stage1_stage2_contract.Stage2ScopeContractTests.test_caller_contract_keeps_full_analysis_independent_of_post_scope
```

前一选择器证明 T1；中间三项是 T2 的输出迁移与 meta/refine 兼容检查（同一最小旧包场景；小池不凑数由最终仅保留现有合格项断言证明）。最后两项仅同步已有调用方文案契约检查的20篇阈值断言，不新建关键词判定器；T3 仍由人工阅读共享 SKILL、两个 analyzer 的成本门/参数/输出/失败处理段落和 diff 确认 <=20 全部、>20 询问、显式N/点名与全文并集不变。无真实模型调用。

保留实际命令、版本和标准输出位置，逐项注明通过/业务失败/无法判断/未执行。环境错误不自动重试业务；先诊断，必要修正仅复核受影响步骤；所有正式失败保留，修复后只复跑受影响目标。T3人工阅读记录路径与观察结果。文档SHA变化不重跑未受影响目标。

T2 补充（EP2 受影响复核）：同一旧包 fixture 包含已接受 split 子项的 done_by_self / 已核状态；语义重建后仍处于原子项，证据、置信度和候选身份不丢失，不复活为 unknown 或普通锚点。关联仅限同一 provisional source，不扩 merge 生命周期测试。
